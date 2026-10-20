"""Native acceptance in a fresh process, with synthetic source fixtures only."""
import asyncio
import copy
import gc
import hashlib
import json
from pathlib import Path
import shutil
import time
import traceback

import omni.ext
import omni.kit.app
import omni.timeline
import omni.usd
from pxr import Usd, UsdGeom, Sdf

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results'


class Probe(omni.ext.IExt):
    def on_startup(self, ext_id):
        self.result = None
        self.client = None
        self.task = asyncio.ensure_future(self.run())

    def on_shutdown(self):
        if self.result and self.result.get('status') == 'passed':
            client = self.client
            clean = (client.state == 'closed' and client.process is None
                     and client.last_exit == 0 and client.last_receipt.get('preserved') is True)
            self.result['checks'].append(dict(name='active viewer closed by host shutdown', passed=clean))
            self.result['worker_exits'].append(client.last_exit)
            self.result['status'] = 'passed' if clean else 'failed'
            (OUT / 'result.json').write_text(json.dumps(self.result, indent=2))

    async def run(self):
        app = omni.kit.app.get_app()
        OUT.mkdir(exist_ok=True)
        result = {'status': 'running', 'checks': [], 'worker_exits': []}
        owner = None
        client = None

        def check(label, condition):
            result['checks'].append({'name': label, 'passed': bool(condition)})
            (OUT / 'checkpoint.json').write_text(json.dumps(result, indent=2))
            print('SCENE_REVIEW_CHECK', label, bool(condition), flush=True)
            assert condition, label

        async def updates(n=10):
            for _ in range(n):
                await app.next_update_async()

        async def done(task, seconds=140):
            start = time.monotonic()
            while not task.done():
                if time.monotonic() - start > seconds:
                    raise TimeoutError('Native acceptance operation exceeded its deadline')
                await updates(1)
            await task

        async def click(label):
            import omni.kit.ui_test as ui_test
            button = ui_test.find("USD Scene Review//Frame/**/Button[*].text=='" + label + "'")
            check(label + ' actual widget found', button is not None)
            import omni.ui as ui
            if ui.Workspace.get_main_window_width() <= 0 or ui.Workspace.get_main_window_height() <= 0:
                button.widget.call_clicked_fn()
                result.setdefault('input_modes', []).append('native callback: '+label)
            else:
                await button.click()
            await updates(2)
            await done(owner._task)

        try:
            await updates(100)
            manager = app.get_extension_manager()
            manager.set_extension_enabled_immediate('mmporong.scene.review', True)
            await updates(10)
            from mmporong.scene.review.extension import SceneReviewExtension
            from usd_scene_review import create_snapshot
            from usd_scene_review.presentation import visible_changes
            owners = [o for o in gc.get_objects() if isinstance(o, SceneReviewExtension)]
            check('one actual packaged extension', len(owners) == 1)
            owner = owners[0]
            client = owner._viewer
            self.client = client
            context = omni.usd.get_context()
            await context.new_stage_async()
            stage = context.get_stage()
            UsdGeom.Xform.Define(stage, '/Sentinel')
            context.get_selection().set_selected_prim_paths(['/Sentinel'], False)
            timeline = omni.timeline.get_timeline_interface()
            timeline.stop()
            timeline.set_current_time(7)
            await updates(20)
            original = (stage, stage.GetRootLayer().ExportToString(), stage.GetRootLayer().dirty,
                        context.get_selection().get_selected_prim_paths(), timeline.get_current_time())
            # A private full-app harness may provide manifests from a bounded saved
            # assembly; the checked-in runner creates only its own synthetic data.
            supplied = ROOT / 'acceptance-inputs.json'
            if supplied.is_file():
                inputs = json.loads(supplied.read_text())
                paths = inputs['manifests']
                target = inputs['target']
                result['fixture'] = 'private saved static assembly'
            else:
                paths = {}
                for side, offset in (('A', 0), ('B', 2)):
                    source = ROOT / ('source-' + side)
                    source.mkdir()
                    fixture = Usd.Stage.CreateInMemory()
                    parent = UsdGeom.Xform.Define(fixture, '/World')
                    fixture.SetDefaultPrim(parent.GetPrim())
                    parent.AddTranslateOp().Set((offset, 0, 0))
                    UsdGeom.Cube.Define(fixture, '/World/Box')
                    UsdGeom.Scope.Define(fixture, '/NonGeometry').GetPrim().CreateAttribute(
                        'reviewValue', Sdf.ValueTypeNames.Int).Set(offset)
                    UsdGeom.Cube.Define(fixture, '/World/' + ('Removed' if side == 'A' else 'Added'))
                    source_file = source / 'scene.usda'
                    source_file.write_text(fixture.GetRootLayer().ExportToString())
                    paths[side] = str(create_snapshot(source_file, ROOT / ('snapshot-' + side)))
                target = '/World/Box'
                result['fixture'] = 'synthetic unlit cubes'
            for side in ('A', 'B'):
                owner._paths[side].set_value(paths[side])
            files = [p for manifest in paths.values() for p in Path(manifest).parent.rglob('*') if p.is_file()]
            before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
            await click('Compare')
            check('Compare changed report', owner._report and owner._report['status'] == 'changed')
            result['changed_prims'] = len(owner._report['changes'])
            result['direct_rows'] = len(visible_changes(owner._report))
            check('inherited motion collapsed', len(visible_changes(owner._report)) < len(owner._report['changes']))
            owner._inherited.set_value(True)
            owner._query.set_value(target)
            check('path search reveals target', any(c['path'] == target for c in visible_changes(owner._report, target, True)))
            # Select the actual row through the native widget, then switch A/B/A.
            import omni.kit.ui_test as ui_test
            row_text = 'modified  ' + target
            row = ui_test.find("USD Scene Review//Frame/**/Button[*].text=='" + row_text + "'")
            if row is None:
                row = ui_test.find("USD Scene Review//Frame/**/Button[*].text=='" + row_text + ' (+' +
                                   str(next(len(g['affected']) for g in owner._report['parent_groups'] if g['parent'] == target)) + " descendants)'")
            check('search result actual row found', row is not None)
            await row.click()
            await updates(5)
            check('actual row selected stable path', owner._selected == target)
            fixed_camera = None
            for side in ('A', 'B', 'A'):
                await click('View ' + side)
                check(side + ' worker running and framed', client.state == 'running' and 'framed' in owner._status.as_string)
                check('host owns no review context', not hasattr(owner, '_context'))
                visual = await client.frame(target)
                check(side + ' whole scene and original appearance', visual['display']['camera_scope']=='whole saved scene'
                      and visual['display']['appearance']=='original')
                check(side + ' selected geometry and bounds style', visual['display']['selected_geometry'] > 0
                      and visual['display']['outline'] == ('dashed' if side == 'A' else 'solid'))
                if fixed_camera is None:
                    fixed_camera = visual['display']['camera']
                check(side + ' fixed A/B camera', visual['display']['camera'] == fixed_camera)
            frozen_report = copy.deepcopy(owner._report)
            owner._review_frame.collapsed = False
            owner._review_path.set_value(str(OUT / 'review-history.jsonl'))
            owner._reason.set_value('Synthetic GUI test: intentional fixture relocation')
            await updates(5)
            await click('Mark intentional')
            check('native intentional decision recorded', 'Human-marked intentional' in owner._disposition.as_string)
            owner._reason.set_value('Synthetic GUI test: confirm independently')
            await click('Needs review')
            await click('Reload review')
            from usd_scene_review.dispositions import history
            review_events = history(OUT / 'review-history.jsonl')
            check('native review reload preserves history and evidence', len(review_events)==2
                  and review_events[0]['disposition']=='intentional'
                  and review_events[1]['disposition']=='needs-review' and owner._report==frozen_report)
            owner._review_frame.collapsed = True
            reply = await client._request('capture')
            check('real worker viewport capture', reply['status'] == 'captured' and (client.directory / 'viewport.png').stat().st_size > 1000)
            shutil.copyfile(client.directory / 'viewport.png', OUT / 'viewport.png')
            reply = await client.frame('/MissingReviewPrim')
            check('absent prim refused without dropping worker', reply['status'] == 'refused' and client.state == 'running')
            check('refusal preserves whole scene camera', reply['display']['camera_scope']=='whole saved scene'
                  and reply['display']['camera']==fixed_camera)
            check('refusal clears prior highlight', reply['display']['selected'] is None
                  and reply['display']['selected_geometry'] == 0)
            if not supplied.is_file():
                reply = await client.frame('/NonGeometry')
                check('non-geometric framing refused without worker exit', reply['status'] == 'refused'
                      and client.state == 'running' and reply['display']['selected'] is None)
            reply = await client.frame(target)
            check('framing recovers after refusal', reply['status'] == 'framed')
            focus = await client.frame(target, focus=True)
            check('explicit selected focus', focus['display']['camera_scope']=='selection focus')
            missing = await client.frame('/MissingReviewPrim', focus=False)
            check('focus off with missing selection restores overview', missing['status']=='refused'
                  and missing['display']['camera']==fixed_camera)
            await click('Close review')
            check('graceful close plus worker exit zero', client.state == 'closed' and client.last_exit == 0 and client.process is None)
            result['worker_exits'].append(client.last_exit)
            if supplied.is_file() and inputs.get('shutdown_while_starting'):
                await ui_test.find("USD Scene Review//Frame/**/Button[*].text=='View B'").click()
                await updates(1)
                check('worker starting before disable', client.process is not None and client.state == 'starting')
            else:
                await click('View B')
                check('viewer reopened', client.state == 'running')
            ext_id = manager.get_enabled_extension_id('mmporong.scene.review')
            manager.set_extension_enabled_immediate(ext_id, False)
            check('attached disable graceful worker exit', client.state == 'closed' and client.last_exit == 0 and client.process is None)
            result['worker_exits'].append(client.last_exit)
            owner = None
            owners = None
            row = None
            gc.collect()
            await updates(10)
            manager.set_extension_enabled_immediate('mmporong.scene.review', True)
            await updates(10)
            from mmporong.scene.review.extension import SceneReviewExtension as Reloaded
            owners = [o for o in gc.get_objects() if isinstance(o, Reloaded)]
            check('re-enabled extension shares durable process owner', len(owners) == 1 and owners[0]._viewer is client)
            owner = owners[0]
            for side in ('A', 'B'):
                owner._paths[side].set_value(paths[side])
            await click('Compare')
            await click('View A')
            check('re-enabled View A running', client.state == 'running')
            await click('Close review')
            check('re-enabled worker exit zero', client.last_exit == 0 and client.process is None)
            result['worker_exits'].append(client.last_exit)
            after = (context.get_stage(), stage.GetRootLayer().ExportToString(), stage.GetRootLayer().dirty,
                     context.get_selection().get_selected_prim_paths(), timeline.get_current_time())
            check('host default stage text dirty selection time preserved', original == after)
            check('all snapshot bytes preserved', before == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
            await click('View A')
            check('normal host quit starts with active viewer', client.process is not None and client.state == 'running')
            result['status'] = 'passed'
        except Exception:
            result.update(status='failed', error=traceback.format_exc())
            print(result['error'], flush=True)
        finally:
            if result['status'] != 'passed' and client and client.process is not None:
                await client.close()
            # Only this test's sentinel stage; avoid full-app save/close cancellation.
            if omni.usd.get_context().get_stage():
                omni.usd.get_context().close_stage()
                await updates(20)
            self.result = result
            (OUT / 'result.json').write_text(json.dumps(result, indent=2))
            app.post_quit(0 if result['status'] == 'passed' else 1)
