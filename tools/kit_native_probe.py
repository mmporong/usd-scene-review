"""Native Kit acceptance runner; loaded only in a fresh synthetic test process."""
import asyncio
import gc
import hashlib
import json
from pathlib import Path
import traceback
import faulthandler
faulthandler.dump_traceback_later(40, repeat=True)

import carb
import omni.ext
import omni.kit.app
import omni.ui as ui
import omni.usd
import omni.timeline
from pxr import Ar, Usd, UsdGeom, UsdLux

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results'


class Probe(omni.ext.IExt):
    def on_startup(self, ext_id):
        self.task = asyncio.ensure_future(self.run())

    async def run(self):
        app = omni.kit.app.get_app()
        result = {'checks': [], 'status': 'running'}
        OUT.mkdir(exist_ok=True)

        def check(label, condition):
            assert condition, label
            result['checks'].append(label)
            print('SCENE_REVIEW_CHECK:', label, flush=True)

        async def updates(count=5):
            for _ in range(count):
                await app.next_update_async()

        async def screenshot(name):
            import omni.kit.renderer.capture
            capture = omni.kit.renderer.capture.acquire_renderer_capture_interface()
            capture.capture_next_frame_swapchain(str(OUT / name))
            await updates(4)
            capture.wait_async_capture()

        try:
            await updates(20)
            import omni.kit.ui_test as ui_test
            manager = app.get_extension_manager()
            manager.set_extension_enabled_immediate('mmporong.scene.review', True)
            await updates()
            from mmporong.scene.review.extension import SceneReviewExtension
            from usd_scene_review import create_snapshot
            ext_id = manager.get_enabled_extension_id('mmporong.scene.review')
            check('packaged extension enabled by native manager', bool(ext_id))
            instances = [obj for obj in gc.get_objects() if isinstance(obj, SceneReviewExtension)]
            check('one actual extension instance', len(instances) == 1)
            owner = instances[0]
            check('native review panel visible', owner._window.visible)
            result['resolver'] = type(Ar.GetUnderlyingResolver()).__name__
            result['usd'] = Usd.GetVersion()
            await screenshot('panel.png')

            # This process owns its default context; it has no user-authored scenes.
            context = omni.usd.get_context()
            await context.new_stage_async()
            stage = context.get_stage()
            UsdGeom.Xform.Define(stage, '/Sentinel')
            context.get_selection().set_selected_prim_paths(['/Sentinel'], False)
            timeline = omni.timeline.get_timeline_interface()
            timeline.stop()
            timeline.set_current_time(7.0)
            await updates(20)
            original = (stage, stage.GetRootLayer().ExportToString(), stage.GetRootLayer().dirty,
                        context.get_selection().get_selected_prim_paths(), timeline.get_current_time())

            for side, offset in (('A', 0), ('B', 2)):
                source = ROOT / ('source-' + side)
                source.mkdir()
                fixture = Usd.Stage.CreateInMemory()
                parent = UsdGeom.Xform.Define(fixture, '/World')
                parent.AddTranslateOp().Set((offset, 0, 0))
                UsdGeom.Cube.Define(fixture, '/World/Box').CreateSizeAttr(1)
                UsdLux.DomeLight.Define(fixture, '/World/Light').CreateIntensityAttr(1000)
                UsdGeom.Cube.Define(fixture, '/World/' + ('Removed' if side == 'A' else 'Added')).AddTranslateOp().Set((0, 3, 0))
                (source / 'scene.usda').write_text(fixture.GetRootLayer().ExportToString(), encoding='utf-8')
                manifest = create_snapshot(source / 'scene.usda', ROOT / ('snapshot-' + side))
                check('native snapshot ' + side + ' is ready', json.loads(manifest.read_text())['status'] == 'ready')
                owner._paths[side].set_value(str(manifest))
            files = [p for side in ('A', 'B') for p in (ROOT / ('snapshot-' + side)).rglob('*') if p.is_file()]
            before_hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
            await updates()
            button = ui_test.find("USD Scene Review//Frame/**/Button[*].text=='Compare'")
            check('Compare button found in native widget tree', button is not None)
            await button.click()
            await updates()
            result['comparison'] = owner._report
            await screenshot('compared.png')
            if owner._report and owner._report['status'] == 'unknown':
                check('custom resolver refused conservatively', any('custom resolver unsupported' in r for r in owner._report['reasons']))
                await ui_test.find("USD Scene Review//Frame/**/Button[*].text=='View A'").click()
                await updates(20)
                check('unknown bundle not attached to viewport', owner._snapshot is None and owner._context.get_stage() is None)
                check('snapshot hashes unchanged after refusal', before_hashes == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
                after = (context.get_stage(), stage.GetRootLayer().ExportToString(), stage.GetRootLayer().dirty, context.get_selection().get_selected_prim_paths(), timeline.get_current_time())
                result['isolation_fields'] = {key: before == current for key, before, current in zip(('stage', 'root_text', 'dirty', 'selection', 'time'), original, after)}
                result['timeline_values'] = [original[-1], after[-1]]
                check('default context unchanged after refusal', original == after)
                context_name = owner._context_name
                manager.set_extension_enabled_immediate(ext_id, False)
                await updates()
                check('native disable cleaned empty owned context', omni.usd.get_context(context_name) is None)
                manager.set_extension_enabled_immediate(ext_id, True)
                await updates()
                check('native panel re-enabled', manager.is_extension_enabled(ext_id) and ui.Workspace.get_window('USD Scene Review').visible)
                manager.set_extension_enabled_immediate(ext_id, False)
                result.update(status='blocked', error='native resolver is not qualified by the strict local bundle engine')
                return
            check('native Compare callback produced changed report', owner._report and owner._report['status'] == 'changed')

            for side in ('A', 'B', 'A', 'B'):
                button = ui_test.find(f"USD Scene Review//Frame/**/Button[*].text=='View {side}'")
                await button.click()
                await updates()
                for _ in range(300):
                    if owner._task and owner._task.done():
                        break
                    await updates(1)
                check('native View ' + side + ' stage attached', owner._snapshot is not None and owner._side == side and owner._context.get_stage() == owner._snapshot.stage)
                result['layer_permissions'] = [{'edit': l.permissionToEdit, 'save': l.permissionToSave, 'dirty': l.dirty, 'original': [e, s, d]} for l, e, s, d in owner._layer_permissions]
                result['viewport_status'] = owner._status.as_string
                check('source permissions protected in ' + side, all(not l.permissionToEdit and not l.permissionToSave and not l.dirty for l, *_ in owner._layer_permissions))
                owner._select(next(c for c in owner._report['changes'] if c['path'] == '/World/Box'))
                check('native framing in ' + side, 'framed' in owner._status.as_string)
                print('SCENE_REVIEW_WAIT: rendered updates after framing ' + side, flush=True)
                await updates(30)
                check('source protections persist after frames in ' + side, all(not l.permissionToEdit and not l.permissionToSave and not l.dirty for l, *_ in owner._layer_permissions))
                print('SCENE_REVIEW_READY: rendered updates after framing ' + side, flush=True)
            await screenshot('review.png')
            from omni.kit.viewport.utility import capture_viewport_to_file
            capture = capture_viewport_to_file(owner._viewport.viewport_api, str(OUT / 'viewport.png'))
            await capture.wait_for_result()
            for _ in range(60):
                if (OUT / 'viewport.png').is_file():
                    break
                await updates(1)
            check('viewport image captured', (OUT / 'viewport.png').is_file())

            # A prim absent in B must never be framed in the wrong revision.
            owner._selected = '/World/Removed'
            owner._frame_selection()
            check('absent prim framing refused', 'absent' in owner._status.as_string)
            await ui_test.find("USD Scene Review//Frame/**/Button[*].text=='Close review'").click()
            await updates()
            check('native Close review detached and destroyed viewport', owner._context.get_stage() is None and owner._viewport is None and owner._snapshot is None and not owner._layer_permissions)
            await ui_test.find("USD Scene Review//Frame/**/Button[*].text=='View A'").click()
            await updates(30)
            for _ in range(300):
                if owner._task and owner._task.done():
                    break
                await updates(1)
            check('native reopen attaches A after close', owner._snapshot is not None and owner._side == 'A' and owner._context.get_stage() == owner._snapshot.stage)
            await ui_test.find("USD Scene Review//Frame/**/Button[*].text=='Close review'").click()
            await updates()
            check('native second close releases resources', owner._snapshot is None and owner._viewport is None and owner._context.get_stage() is None and not owner._release_blocked)

            async def request_view(side):
                await ui_test.find(f"USD Scene Review//Frame/**/Button[*].text=='View {side}'").click()
                await updates(5)
                for _ in range(300):
                    if owner._task and owner._task.done():
                        return
                    await updates(1)
                raise AssertionError('view task did not finish within 300 frames')

            source_layer = ROOT / 'snapshot-A/layers/scene.usda'
            source_bytes = source_layer.read_bytes()
            source_layer.write_bytes(source_bytes + b'\n')
            await request_view('A')
            check('modified bundle refused on switch', owner._snapshot is None and owner._context.get_stage() is None and 'changed' in owner._status.as_string)
            source_layer.write_bytes(source_bytes)
            held = source_layer.with_suffix('.held')
            source_layer.rename(held)
            await request_view('A')
            check('missing bundle refused on switch', owner._snapshot is None and owner._context.get_stage() is None)
            held.rename(source_layer)

            static_paths = {side: model.as_string for side, model in owner._paths.items()}
            for side in ('A', 'B'):
                source = ROOT / ('animated-source-' + side)
                source.mkdir()
                fixture = Usd.Stage.CreateInMemory()
                op = UsdGeom.Xform.Define(fixture, '/Animated').AddTranslateOp()
                op.Set((0, 0, 0), 0)
                op.Set((1, 0, 0), 1)
                (source / 'scene.usda').write_text(fixture.GetRootLayer().ExportToString(), encoding='utf-8')
                manifest = create_snapshot(source / 'scene.usda', ROOT / ('animated-snapshot-' + side), time=0)
                owner._paths[side].set_value(str(manifest))
            await ui_test.find("USD Scene Review//Frame/**/Button[*].text=='Compare'").click()
            await updates()
            check('animated semantic comparison valid at explicit sample', owner._report['status'] == 'equal')
            await request_view('A')
            check('animated viewport refused without timeline change', owner._snapshot is None and 'Animated viewport is unsupported' in owner._status.as_string and timeline.get_current_time() == original[-1])

            for side, path in static_paths.items():
                owner._paths[side].set_value(path)
            await ui_test.find("USD Scene Review//Frame/**/Button[*].text=='Compare'").click()
            await updates()
            await request_view('A')
            check('static view recovers after negative checks', owner._snapshot is not None and owner._side == 'A')
            protected_layers = list(owner._layer_permissions)
            capture = None
            check('snapshot hashes unchanged', before_hashes == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
            after = (context.get_stage(), stage.GetRootLayer().ExportToString(), stage.GetRootLayer().dirty, context.get_selection().get_selected_prim_paths(), timeline.get_current_time())
            result['isolation_fields'] = {key: before == current for key, before, current in zip(('stage', 'root_text', 'dirty', 'selection', 'time'), original, after)}
            result['timeline_values'] = [original[-1], after[-1]]
            result['selection_values'] = [original[-2], after[-2]]
            if original[1] != after[1]:
                result['default_root_texts'] = [original[1], after[1]]
            check('default context selection timeline and dirty state unchanged', original == after)
            context_name = owner._context_name
            manager.set_extension_enabled_immediate(ext_id, False)
            await updates()
            check('native disable cleaned owned context', omni.usd.get_context(context_name) is None)
            check('native disable restored source permissions', all((l.permissionToEdit, l.permissionToSave, l.dirty) == (e, s, d) for l, e, s, d in protected_layers))
            manager.set_extension_enabled_immediate(ext_id, True)
            await updates()
            check('native re-enable succeeded', manager.is_extension_enabled(ext_id))
            manager.set_extension_enabled_immediate(ext_id, False)
            result['status'] = 'passed'
        except Exception as exc:
            result.update(status='failed', error=type(exc).__name__ + ': ' + str(exc))
            traceback.print_exc()
        finally:
            (OUT / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            print('SCENE_REVIEW_RESULT:', result['status'], flush=True)
            app.post_quit(0 if result['status'] == 'passed' else 1)
