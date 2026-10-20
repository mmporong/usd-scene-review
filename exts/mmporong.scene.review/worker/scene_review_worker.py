"""Private viewer: the SDK owns this process's default-context teardown."""
import asyncio
import hashlib
from pathlib import Path
import carb.settings

import omni.ext
import omni.kit.app
import omni.usd
from omni.kit.viewport.window import ViewportWindow
from usd_scene_review.display import ReviewDisplay, world_bounds, camera_spec
from pxr import Sdf, Usd, UsdUtils

from usd_scene_review import load_snapshot, compare
from usd_scene_review.ghost import extract, GhostOverlay
from evidence_panel import EvidencePanel
from usd_scene_review.snapshot import verify
from usd_scene_review.preview import prepare_lighting
from usd_scene_review.worker_client import SCHEMA, read_message, write_message


class ReviewWorker(omni.ext.IExt):
    def on_startup(self, ext_id):
        self.task = asyncio.ensure_future(self.run())

    async def run(self):
        self.root = Path(carb.settings.get_settings().get('/exts/usd.review.viewer/runDirectory'))
        self.config = read_message(self.root / 'config.json')
        self.context = omni.usd.get_context()
        self.viewport = None
        self.snapshot = None
        self.stage_id = None
        self.permissions = []
        self.display = None
        self.camera_cache = {}
        self.focus = False
        self.ghost_enabled = False
        self.normalized = True
        self.review = {}
        self.ghost = None
        self.panel = None
        self.ghost_cache = {}
        self.ghost_material_available = False
        self.display_info = {}
        self.sequence = 0
        try:
            if (not self.config or self.config.get('schema') != SCHEMA
                    or set(self.config.get('manifests', {})) != {'A', 'B'}):
                raise ValueError('Invalid viewer startup configuration')
            # This process starts empty; never replace an unexpected default stage.
            if self.context.get_stage() is not None:
                raise RuntimeError('Viewer default context was not empty')
            self.ghost_material_available = (Path(self.config.get('sdk','')) / 'kit/mdl/core/Base/OmniPBR.mdl').is_file()
            self.report = compare(self.config['manifests']['A']['path'], self.config['manifests']['B']['path'])
            self.panel = EvidencePanel()
            self.respond('ready')
            while True:
                message = read_message(self.root / 'request.json')
                if message and message.get('sequence') != self.sequence:
                    if (message.get('schema') != SCHEMA
                            or message.get('nonce') != self.config['nonce']
                            or message.get('sequence') != self.sequence + 1):
                        raise ValueError('Viewer command identity or sequence mismatch')
                    self.sequence += 1
                    operation = message.get('operation')
                    if operation == 'close':
                        self.release_stage()
                        if self.viewport:
                            self.viewport.destroy()
                            self.viewport = None
                        self.panel.destroy()
                        self.panel = None
                        omni.usd.release_all_hydra_engines(self.context)
                        if self.context.get_attached_hydra_engine_names():
                            raise RuntimeError('Viewer engines did not detach')
                        self.check_manifests()
                        for record in self.config['manifests'].values():
                            if verify(load_snapshot(record['path'])):
                                raise RuntimeError('A/B bundle integrity changed before close')
                        write_message(self.root / 'receipt.json', dict(
                            schema=SCHEMA, nonce=self.config['nonce'], sequence=self.sequence,
                            status='closed', preserved=True))
                        self.respond('closing')
                        # No destroy_context / destroy_timeline call here. Normal SDK shutdown.
                        omni.kit.app.get_app().post_quit(0)
                        return
                    if 'focus' in message:
                        if type(message['focus']) is not bool:
                            raise ValueError('Invalid focus mode')
                        self.focus = message['focus']
                    for key, target in [('ghost', 'ghost_enabled'), ('normalized', 'normalized')]:
                        if key in message:
                            if type(message[key]) is not bool:
                                raise ValueError('Invalid preview option')
                            setattr(self, target, message[key])
                    if 'review' in message:
                        review = message['review']
                        if (not isinstance(review, dict) or set(review) - {'disposition', 'reason'}
                                or review.get('disposition', 'unreviewed') not in ('unreviewed', 'intentional', 'needs-review')
                                or not isinstance(review.get('reason', ''), str) or len(review.get('reason', '')) > 4096):
                            raise ValueError('Invalid human review metadata')
                        self.review = review
                    if operation == 'view':
                        await self.view(message.get('side'))
                        self.frame(message.get('selected'))
                    elif operation == 'frame':
                        self.frame(message.get('selected'))
                    elif operation == 'capture':
                        # Diagnostic output is fixed inside the owned private run,
                        # never an arbitrary destination supplied by the caller.
                        self.check_current()
                        # Advance THIS child's renderer, not the host's UI loop.
                        # Compare real downsampled RGB frames before claiming stable output.
                        from PIL import Image, ImageChops, ImageStat
                        previous = None
                        stable = 0
                        differences = []
                        from omni.kit.viewport.utility import capture_viewport_to_file
                        from omni.kit.renderer.capture import acquire_renderer_capture_interface
                        renderer_capture = acquire_renderer_capture_interface()
                        for batch in range(8):
                            for _ in range(32):
                                await omni.kit.app.get_app().next_update_async()
                            capture = capture_viewport_to_file(self.viewport.viewport_api, str(self.root / 'viewport.png'))
                            await capture.wait_for_result()
                            renderer_capture.wait_async_capture()
                            with Image.open(self.root / 'viewport.png') as frame:
                                current = frame.convert('RGB').resize((320, 180))
                            if previous is not None:
                                difference = sum(ImageStat.Stat(ImageChops.difference(previous, current)).mean) / 3
                                differences.append(difference)
                                stable = stable + 1 if difference <= .5 else 0
                            previous = current
                            if stable >= 2:
                                break
                        capture = None
                        if not (self.root / 'viewport.png').is_file():
                            raise RuntimeError('Viewport capture completed without an image file')
                        self.display_info['capture'] = dict(stable=stable >= 2, renderer_updates=32 * (batch + 1),
                                                           mean_rgb_differences=differences)
                        renderer_capture.capture_next_frame_swapchain(str(self.root / 'review.png'))
                        for _ in range(5):
                            await omni.kit.app.get_app().next_update_async()
                        renderer_capture.wait_async_capture()
                        if not (self.root / 'review.png').is_file():
                            raise RuntimeError('Renderer swapchain capture did not produce an image')
                        self.respond('captured')
                    else:
                        raise ValueError('Unsupported viewer operation')
                await asyncio.sleep(0.05)
        except Exception as exc:
            self.respond('error', type(exc).__name__ + ': ' + str(exc))
            # A failed receipt cannot qualify as graceful close. The parent contains
            # this exact owned job if native shutdown fails.
            write_message(self.root / 'receipt.json', dict(
                schema=SCHEMA, nonce=(self.config or {}).get('nonce'), status='failed', preserved=False))
            omni.kit.app.get_app().post_quit(1)

    def respond(self, status, message=''):
        if self.panel and getattr(self, 'side', None):
            self.panel.update(self.report, self.display_info.get('selected'), self.side,
                              self.review, self.display_info, self.lighting)
        write_message(self.root / 'response.json', dict(
            schema=SCHEMA, nonce=(self.config or {}).get('nonce'), sequence=self.sequence,
            status=status, message=message, side=getattr(self, "side", None),
            display=self.display_info))

    def check_manifests(self):
        for record in self.config['manifests'].values():
            if hashlib.sha256(Path(record['path']).read_bytes()).hexdigest() != record['sha256']:
                raise RuntimeError('Compared manifest changed; compare again')

    def release_stage(self):
        if self.ghost:
            self.ghost.clear()
        self.ghost = None
        self.display = None
        if self.context.get_stage():
            if not self.context.close_stage() or self.context.get_stage():
                raise RuntimeError('Viewer stage close was not confirmed')
        if self.stage_id is not None:
            UsdUtils.StageCache.Get().Erase(self.stage_id)
            self.stage_id = None
        if self.snapshot and verify(self.snapshot):
            raise RuntimeError('Snapshot integrity changed during review')
        for layer, editable, saveable, dirty in self.permissions:
            if layer.dirty != dirty:
                raise RuntimeError('Source dirty state changed; nothing saved')
            layer.SetPermissionToEdit(editable)
            layer.SetPermissionToSave(saveable)
        self.permissions = []
        self.snapshot = None

    async def view(self, side):
        if side not in ('A', 'B'):
            raise ValueError('Unknown revision')
        self.check_manifests()
        self.release_stage()
        if self.viewport:
            self.viewport.visible = False
        snapshot = load_snapshot(self.config['manifests'][side]['path'])
        if snapshot.stage is None or snapshot.errors:
            raise ValueError('Snapshot is unknown; inspect the comparison errors')
        if any(attr.GetNumTimeSamples() for prim in snapshot.stage.TraverseAll()
               for attr in prim.GetAttributes()):
            raise ValueError('Animated viewport is unsupported; inspect the declared-time report')
        stage = snapshot.stage
        session = stage.GetSessionLayer()
        if not session.anonymous:
            raise ValueError('File-backed review session refused')
        stage.SetEditTarget(Usd.EditTarget(session))
        self.lighting = prepare_lighting(stage, normalized=self.normalized)
        settings = carb.settings.get_settings()
        for key, value in {'/rtx/post/histogram/enabled': False, '/rtx/post/tonemap/filmIso': 100.0,
                           '/rtx/post/tonemap/exposureTime': .02, '/rtx/post/tonemap/fNumber': 5.0,
                           '/rtx/post/tonemap/op': 6, '/rtx/ecoMode/enabled': False,
                           '/rtx/raytracing/fractionalCutoutOpacity': True}.items():
            settings.set(key, value)
        self.snapshot = snapshot
        for layer in stage.GetUsedLayers():
            if not layer.anonymous:
                self.permissions.append((layer, layer.permissionToEdit, layer.permissionToSave, layer.dirty))
                layer.SetPermissionToEdit(False)
                layer.SetPermissionToSave(False)
        if self.viewport is None:
            self.viewport = ViewportWindow('USD Scene Review A/B', '', width=1080, height=820,
                                           usd_drop_support=False, visible=False)
            self.viewport.position_x = 10
            self.viewport.position_y = 35
        self.stage_id = UsdUtils.StageCache.Get().Insert(stage)
        success, error = await self.context.attach_stage_async(stage)
        if not success:
            raise RuntimeError('Viewer stage attachment failed: ' + error)
        stage.SetEditTarget(Usd.EditTarget(session))
        for layer, _, _, dirty in self.permissions:
            if layer.dirty != dirty:
                raise RuntimeError('Source dirty state changed during attachment')
            layer.SetPermissionToEdit(False)
            layer.SetPermissionToSave(False)
        await omni.kit.app.get_app().next_update_async()
        self.lighting['renderer_settings'] = {key: settings.get(key) for key in (
            '/rtx/rendermode', '/rtx/post/histogram/enabled', '/rtx/post/tonemap/filmIso',
            '/rtx/post/tonemap/exposureTime', '/rtx/post/tonemap/fNumber', '/rtx/post/tonemap/op',
            '/rtx/raytracing/fractionalCutoutOpacity')}
        self.check_current()
        self.display = ReviewDisplay(stage)
        self.ghost = GhostOverlay(stage, self.display.root)
        self.viewport.visible = True
        self.side = side

    def check_current(self):
        self.check_manifests()
        if not self.snapshot or verify(self.snapshot):
            raise RuntimeError('Snapshot integrity verification failed')
        if (self.snapshot.stage.GetEditTarget().GetLayer() != self.snapshot.stage.GetSessionLayer()
                or any(layer.permissionToEdit or layer.permissionToSave
                       for layer, *_ in self.permissions)):
            raise RuntimeError('Source protection changed during review')

    def camera_for(self, key):
        if key not in self.camera_cache:
            bounds, metadata = {}, []
            from pxr import UsdGeom
            for side, record in self.config['manifests'].items():
                raw = load_snapshot(record['path'])
                if raw.errors or verify(raw):
                    raise RuntimeError('Cannot calculate bounds from verified raw snapshots')
                bounds[side] = world_bounds(raw, key)
                metadata.append((UsdGeom.GetStageMetersPerUnit(raw.stage), str(UsdGeom.GetStageUpAxis(raw.stage))))
            if metadata[0] != metadata[1] or metadata[0][0] <= 0:
                raise ValueError('Synchronized framing requires matching units and up axis')
            self.camera_cache[key] = camera_spec(bounds, metadata[0][1])
        return self.camera_cache[key]

    def frame(self, selected):
        self.check_current()
        self.ghost.clear()
        self.display_info = self.display.style(None, self.side, None)
        self.display_info['ghost'] = {'status': 'off', 'count': 0}
        self.display_info['review'] = dict(self.review)
        self.display_info.update(selected=None, camera_scope='previous camera; selection not framed')
        # Whole-scene context is independent of whether a selected change exists
        # or has geometric bounds in this revision.
        if not self.focus or not selected:
            try:
                spec = self.camera_for('/')
            except ValueError as exc:
                self.respond('refused', self.side + ': scene framing unavailable: ' + str(exc))
                return
            self.display.set_camera(spec, self.viewport.viewport_api)
            self.display_info.update(camera=spec, camera_scope='whole saved scene')
        if not selected:
            self.check_current()
            self.respond('viewing', self.side + ': whole saved scene; original appearance')
            return
        path = Sdf.Path(selected)
        prim = self.snapshot.stage.GetPrimAtPath(path) if path.IsAbsolutePath() and path.IsPrimPath() else None
        if (not prim or not prim.IsActive() or not prim.IsLoaded() or path.HasPrefix(self.display.root)):
            self.respond('refused', self.side + ': selected source prim is absent, inactive or unloaded; scene retained')
            return
        try:
            selected_spec = self.camera_for(selected)
        except ValueError as exc:
            self.respond('refused', self.side + ': selected bounds unavailable; scene retained: ' + str(exc))
            return
        if selected_spec['bounds'][self.side] is None:
            self.respond('refused', self.side + ': selected prim has no visible bounds; scene retained')
            return
        if self.focus:
            self.display.set_camera(selected_spec, self.viewport.viewport_api)
            self.display_info.update(camera=selected_spec, camera_scope='selection focus')
        camera_info = {k: self.display_info[k] for k in ('camera', 'camera_scope')}
        self.display_info = self.display.style(selected, self.side, selected_spec['bounds'][self.side])
        self.display_info.update(selected=selected, **camera_info)
        self.display_info['review'] = dict(self.review)
        self.display_info['ghost'] = {'status': 'off', 'count': 0}
        if self.ghost_enabled and self.side == 'B':
            if not self.ghost_material_available:
                self.display_info['lighting'] = self.lighting
                self.display_info['ghost'] = {'status':'unsupported','count':0,
                    'reason':'Installed SDK OmniPBR template is unavailable; no ghost created'}
                self.respond('framed', self.side + ': current geometry retained; old A material unsupported')
                return
            if selected not in self.ghost_cache:
                old = load_snapshot(self.config['manifests']['A']['path'])
                if old.errors or verify(old):
                    raise RuntimeError('Old A snapshot verification failed')
                # One selection only: overlapping subtrees must not accumulate.
                self.ghost_cache = {selected: extract(old, selected)}
            self.display_info['ghost'] = self.ghost.show(self.ghost_cache[selected])
        self.display_info['lighting'] = self.lighting
        self.check_current()
        label = 'BEFORE saved scene A' if self.side == 'A' else 'AFTER saved scene B'
        self.respond('framed', self.side + ': framed ' + selected + '; ' + label
                     + '; original geometry/materials; ' + self.lighting['label'] + '; '
                     + self.display_info['camera_scope'])
