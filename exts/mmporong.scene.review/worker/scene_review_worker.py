"""Private viewer: the SDK owns this process's default-context teardown."""
import asyncio
import hashlib
from pathlib import Path
import carb.settings

import omni.ext
import omni.kit.app
import omni.usd
from omni.kit.viewport.window import ViewportWindow
from omni.kit.viewport.utility import frame_viewport_prims
from pxr import Sdf, Usd, UsdUtils

from usd_scene_review import load_snapshot
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
        self.sequence = 0
        try:
            if (not self.config or self.config.get('schema') != SCHEMA
                    or set(self.config.get('manifests', {})) != {'A', 'B'}):
                raise ValueError('Invalid viewer startup configuration')
            # This process starts empty; never replace an unexpected default stage.
            if self.context.get_stage() is not None:
                raise RuntimeError('Viewer default context was not empty')
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
                    if operation == 'view':
                        await self.view(message.get('side'))
                        self.frame(message.get('selected'))
                    elif operation == 'frame':
                        self.frame(message.get('selected'))
                    elif operation == 'capture':
                        # Diagnostic output is fixed inside the owned private run,
                        # never an arbitrary destination supplied by the caller.
                        self.check_current()
                        from omni.kit.viewport.utility import capture_viewport_to_file
                        capture = capture_viewport_to_file(
                            self.viewport.viewport_api, str(self.root / 'viewport.png'))
                        await capture.wait_for_result()
                        from omni.kit.renderer.capture import acquire_renderer_capture_interface
                        acquire_renderer_capture_interface().wait_async_capture()
                        capture = None
                        if not (self.root / 'viewport.png').is_file():
                            raise RuntimeError('Viewport capture completed without an image file')
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
        write_message(self.root / 'response.json', dict(
            schema=SCHEMA, nonce=(self.config or {}).get('nonce'), sequence=self.sequence,
            status=status, message=message))

    def check_manifests(self):
        for record in self.config['manifests'].values():
            if hashlib.sha256(Path(record['path']).read_bytes()).hexdigest() != record['sha256']:
                raise RuntimeError('Compared manifest changed; compare again')

    def release_stage(self):
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
        prepare_lighting(stage)
        self.snapshot = snapshot
        for layer in stage.GetUsedLayers():
            if not layer.anonymous:
                self.permissions.append((layer, layer.permissionToEdit, layer.permissionToSave, layer.dirty))
                layer.SetPermissionToEdit(False)
                layer.SetPermissionToSave(False)
        if self.viewport is None:
            self.viewport = ViewportWindow('USD Scene Review A/B', '', width=960, height=640,
                                           usd_drop_support=False, visible=False)
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
        self.check_current()
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

    def frame(self, selected):
        self.check_current()
        if not selected:
            self.respond('viewing', self.side + ': static review in separate viewer window')
            return
        path = Sdf.Path(selected)
        if not path.IsAbsolutePath() or not path.IsPrimPath():
            self.respond('refused', 'Choose an absolute prim path from the comparison')
            return
        prim = self.snapshot.stage.GetPrimAtPath(path)
        if not prim or not prim.IsActive() or not prim.IsLoaded():
            self.respond('refused', self.side + ': selected prim is absent, inactive or unloaded; try the other revision')
            return
        self.context.get_selection().set_selected_prim_paths([selected], False)
        framed = frame_viewport_prims(self.viewport.viewport_api, prims=[selected])
        self.respond('framed' if framed else 'refused', self.side + ': ' + (
            'framed ' + selected if framed else 'camera is not available yet; retry framing'))
