"""Packaged same-process A/B acceptance with synthetic static fixtures only."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import traceback
import carb.settings
import omni.ext
import omni.kit.app
import omni.ui as ui
import omni.usd
import omni.timeline
from pxr import Gf, Usd, UsdGeom


class Probe(omni.ext.IExt):
    def on_startup(self,ext_id):
        self.result=None;self.owner=None;self.review=None;self.task=asyncio.ensure_future(self.run())
    def on_shutdown(self):
        # Product can shut down after this probe. The product shutdown observer
        # installed below writes the final receipt after actual cleanup.
        pass
    async def run(self):
        app=omni.kit.app.get_app();self.root=Path(carb.settings.get_settings().get('/exts/in.app.probe/output'))
        root=self.root;result={'status':'running','pid':os.getpid(),'checks':[]}
        def check(name,ok):
            result['checks'].append({'name':name,'passed':bool(ok)})
            (root/'checkpoint.json').write_text(json.dumps(result,indent=2));print('IN_APP_CHECK',name,bool(ok),flush=True)
            if not ok:raise RuntimeError(name)
        async def updates(n=10):
            for _ in range(n):await app.next_update_async()
        def matrices_equal(a,b):return max(abs(a[i][j]-b[i][j]) for i in range(4) for j in range(4))<1e-6
        try:
            async def ready():
                while not app.is_app_ready():await app.next_update_async()
            await asyncio.wait_for(ready(),timeout=120)
            if app.get_extension_manager().is_extension_enabled('isaacsim.app.setup'):
                from omni.kit.viewport.utility import get_active_viewport,next_viewport_frame_async
                async def first_frame():
                    while omni.usd.get_context().get_stage() is None or get_active_viewport() is None:
                        await app.next_update_async()
                    await next_viewport_frame_async(get_active_viewport())
                await asyncio.wait_for(first_frame(),60)
            await updates(60)
            check('app reports ready before review setup',app.is_app_ready())
            manager=app.get_extension_manager();manager.set_extension_enabled_immediate('mmporong.scene.review',True)
            await updates()
            from mmporong.scene.review.extension import get_active_extension
            from usd_scene_review import create_snapshot
            self.owner=owner=get_active_extension();check('actual packaged extension loaded',owner is not None)
            from mmporong.scene.review import in_app
            async def open_review():
                # This explicit switch exists only in the disposable validation
                # probe, never in the distributed product. Keep the public button
                # and guard blocked before/after every test-only opening.
                if not in_app.full_host_blocked():return await owner._open_in_app()
                if not carb.settings.get_settings().get('/exts/in.app.probe/fullFeatureValidation'):
                    raise RuntimeError('Full-host feature probe requires explicit owned-host validation opt-in')
                check('product full-app guard remains enabled before test-only opening',owner._in_app_blocked)
                blocked=in_app.full_host_blocked
                owner._in_app_blocked=False;in_app.full_host_blocked=lambda:False
                try:await owner._open_in_app()
                finally:owner._in_app_blocked=True;in_app.full_host_blocked=blocked
                check('product full-app guard restored after test-only opening',in_app.full_host_blocked() and owner._in_app_blocked)
            host=omni.usd.get_context();await host.new_stage_async();stage=host.get_stage()
            self.fixture_stages=[stage]
            UsdGeom.Xform.Define(stage,'/Sentinel');UsdGeom.Camera.Define(stage,'/Sentinel/SourceCamera')
            host.get_selection().set_selected_prim_paths(['/Sentinel'],False)
            timeline=omni.timeline.get_timeline_interface();timeline.set_current_time(7);await updates(20)
            original=(stage,stage.GetRootLayer().ExportToString(),stage.GetSessionLayer().ExportToString(),stage.GetRootLayer().dirty,
                      host.get_selection().get_selected_prim_paths(),timeline.get_current_time())
            paths={}
            for side in ('A','B'):
                source=root/('source-'+side);source.mkdir();file=source/'scene.usda'
                fixture=Usd.Stage.CreateNew(str(file));UsdGeom.SetStageUpAxis(fixture,'Z');UsdGeom.SetStageMetersPerUnit(fixture,1)
                for name,xyz in [('Translated',(-3,0 if side=='A' else 2,0)),('Rotated',(0,0,0)),
                                 ('Removed' if side=='A' else 'Added',(3,-2 if side=='A' else 1,0))]:
                    cube=UsdGeom.Cube.Define(fixture,'/World/'+name);cube.CreateSizeAttr(1)
                    cube.AddTranslateOp().Set(xyz)
                    if name=='Rotated':cube.AddRotateZOp().Set(0 if side=='A' else 35)
                parent=UsdGeom.Xform.Define(fixture,'/World/Parent');parent.AddTranslateOp().Set((0 if side=='A' else 1,3,0))
                UsdGeom.Cube.Define(fixture,'/World/Parent/Child').CreateSizeAttr(1)
                floor=UsdGeom.Cube.Define(fixture,'/Floor');floor.CreateSizeAttr(1)
                floor.AddScaleOp().Set((14,12,.1));floor.AddTranslateOp().Set((0,0,-8))
                fixture.GetRootLayer().Save();fixture=None
                paths[side]=str(create_snapshot(file,root/('snapshot-'+side)))
            files=[p for name in ('source-A','source-B','snapshot-A','snapshot-B') for p in (root/name).rglob('*') if p.is_file()]
            hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
            for s,p in paths.items():owner._paths[s].set_value(p)
            await owner._compare_async();check('comparison complete',owner._report['status']=='changed')
            settings=carb.settings.get_settings()
            exposure_keys=('/rtx/post/histogram/enabled','/rtx/post/tonemap/filmIso',
                           '/rtx/post/tonemap/exposureTime','/rtx/post/tonemap/fNumber',
                           '/rtx/post/tonemap/op','/rtx/ecoMode/enabled','/rtx/raytracing/fractionalCutoutOpacity')
            settings_before={key:settings.get(key) for key in exposure_keys}
            await open_review();review=owner._in_app;await updates(60)
            check('two in-process viewports without worker',review.state=='open' and len(review.resources)==2 and owner._viewer.process is None)
            changes={c['path']:c for c in owner._report['changes']}
            for path in ('/World/Translated','/World/Rotated','/World/Added','/World/Removed','/World/Parent/Child'):
                owner._select(changes[path]);await owner._task;await updates(12)
                a,b=[review.resources[s]['widget'].viewport_api for s in ('A','B')]
                check('same focus/projection '+path,matrices_equal(a.view,b.view) and matrices_equal(a.projection,b.projection))
                check('selected evidence '+path,review.selected==path and owner._selected==path)
                if path.endswith('Added'):check('added object absent A explicitly labelled','Absent' in review.labels['A'].as_string)
                if path.endswith('Removed'):check('removed object absent B explicitly labelled','Absent' in review.labels['B'].as_string)
            check('parent influence is observed not guessed',changes['/World/Parent/Child']['provenance']=='parent-propagated')
            from usd_scene_review.measurements import measurements
            check('rotation evidence 35 degrees',abs(measurements(owner._report,changes['/World/Rotated'])['spaces']['world']['effective_rotation_degrees']-35)<1e-6)
            a,b=review.resources['A'],review.resources['B']
            camera=UsdGeom.Camera(a['stage'].GetPrimAtPath(a['display'].root.AppendChild('Camera')))
            transform=camera.GetCamera().transform;transform.SetTranslateOnly(Gf.Vec3d(9,-8,7))
            UsdGeom.Xformable(camera).MakeMatrixXform().Set(transform);await updates(20)
            check('camera navigation synchronizes both viewports',matrices_equal(a['widget'].viewport_api.view,b['widget'].viewport_api.view))
            owner._select(changes['/World/Translated']);await owner._task;owner._ghost.set_value(True);await updates(30)
            check('ghost authored opacity metadata .22; rendered appearance requires inspection',review.display_info['ghost']['status']=='shown' and review.display_info['ghost']['opacity']==.22)
            # Native UI test API: click an actual row in the in-app evidence pane.
            import omni.kit.ui_test as ui_test
            row=ui_test.find("USD Scene Review A/B//Frame/**/Button[*].text=='modified /World/Translated'")
            check('actual in-app change row exists',row is not None)
            await row.click();row=None;await updates(5)
            if owner._task:await owner._task
            check('native row click updates selected evidence',review.selected=='/World/Translated')
            # MDL compilation is asynchronous; a handful of UI updates captured
            # the white fallback rather than the final material in earlier runs.
            await updates(128)
            from omni.kit.viewport.utility import capture_viewport_to_file
            from omni.kit.renderer.capture import acquire_renderer_capture_interface
            capture_api=acquire_renderer_capture_interface()
            for side,item in review.resources.items():
                capture=capture_viewport_to_file(item['widget'].viewport_api,str(root/('viewport-'+side+'.png')))
                await capture.wait_for_result();capture_api.wait_async_capture();capture=None
                from PIL import Image
                with Image.open(root/('viewport-'+side+'.png')) as frame:
                    check(side+' real rendered nonempty image',len(frame.convert('RGB').resize((100,100)).getcolors(10001) or [])>8)
                    if side=='B':
                        pixels=list(frame.convert('RGB').getdata())
                        fraction=sum(g>40 and g>r*1.12 and g>bl*1.12 for r,g,bl in pixels)/len(pixels)
                        check('rendered green faces exceed edge-only area',fraction>.005)
            item=None
            # A rendered opaque control catches a green-but-opaque fallback.
            ghost=review.resources['B']['ghost']
            opacity=ghost.stage.GetPrimAtPath(ghost.material_root.AppendChild('Surface')).GetAttribute('inputs:opacity_constant')
            opacity.Set(1.0);await updates(64)
            control=capture_viewport_to_file(review.resources['B']['widget'].viewport_api,str(root/'ghost-opaque-control.png'))
            await control.wait_for_result();capture_api.wait_async_capture();control=None
            opacity.Set(.22);opacity=ghost=None;await updates(64)
            from PIL import ImageChops, ImageStat
            with Image.open(root/'viewport-B.png') as faint,Image.open(root/'ghost-opaque-control.png') as opaque:
                difference=sum(ImageStat.Stat(ImageChops.difference(faint.convert('RGB'),opaque.convert('RGB'))).mean)/3
                check('rendered .22 faces differ from opaque control',difference>.1)
            capture_api.capture_next_frame_swapchain(str(root/'in-app-review.png'));await updates(5);capture_api.wait_async_capture();capture_api=None
            check('real A/B UI screenshot captured',(root/'in-app-review.png').stat().st_size>1000)
            a=b=camera=transform=capture=item=None
            await owner._close();await updates(20)
            check('normal in-app close confirmed',review.state=='closed' and review.last_close['preserved'])
            result['renderer_settings']={'before':settings_before,'after':{key:settings.get(key) for key in exposure_keys}}
            check('temporary renderer settings restored',settings_before=={key:settings.get(key) for key in exposure_keys})
            after=(host.get_stage(),stage.GetRootLayer().ExportToString(),stage.GetSessionLayer().ExportToString(),stage.GetRootLayer().dirty,
                   host.get_selection().get_selected_prim_paths(),timeline.get_current_time())
            check('working stage source camera session selection dirty timeline preserved',original==after)
            for cycle in range(2):
                await open_review();await updates(20);await owner._close();await updates(10)
                check('repeat close '+str(cycle),owner._in_app.state=='closed')
            await open_review();await updates(15)
            await host.new_stage_async();await updates(20)
            self.fixture_stages.append(host.get_stage())
            if owner._in_app._close_task:await owner._in_app._close_task
            check('working stage switch clears review',owner._in_app.state=='closed')
            await open_review();await updates(15)
            disabled_review=owner._in_app
            manager.set_extension_enabled_immediate(manager.get_enabled_extension_id('mmporong.scene.review'),False)
            await updates(15);check('extension disable clears owned contexts',disabled_review.state=='closed')
            owner=None;self.owner=None;gc=None
            manager.set_extension_enabled_immediate('mmporong.scene.review',True);await updates(15)
            from mmporong.scene.review.extension import get_active_extension as active
            self.owner=owner=active()
            for s,p in paths.items():owner._paths[s].set_value(p)
            await owner._compare_async();await open_review();await updates(15)
            self.review=owner._in_app
            check('re-enabled extension opens internal viewports',owner._in_app.state=='open')
            check('all original file bytes preserved',hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
            review=self.review;original_shutdown=owner.on_shutdown
            def observed_shutdown():
                try:original_shutdown()
                finally:
                    ok=review.state=='closed' and bool(review.last_close and review.last_close['preserved'])
                    result['checks'].append({'name':'active in-app comparison closes on host shutdown','passed':ok})
                    result['status']='passed' if ok else 'failed'
                    (root/'result.json').write_text(json.dumps(result,indent=2))
            owner.on_shutdown=observed_shutdown
            result['status']='awaiting_shutdown'
        except Exception:
            result.update(status='failed',error=traceback.format_exc());print(result['error'],flush=True)
            if self.owner and getattr(self.owner,'_in_app',None):self.owner._in_app.close_sync()
        self.result=result;(root/'result.json').write_text(json.dumps(result,indent=2))
        code=0 if result['status'] in ('passed','awaiting_shutdown') else 1
        private_host=bool(carb.settings.get_settings().get('/exts/in.app.probe/fullFeatureValidation'))
        stage=omni.usd.get_context().get_stage()
        if private_host and stage in getattr(self,'fixture_stages',[]) and stage.GetRootLayer().anonymous:
            app.post_uncancellable_quit(code)
        else:app.post_quit(code)
