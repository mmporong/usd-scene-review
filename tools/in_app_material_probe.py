"""Single owned native host: ghost-off/on frames, then active disable. Synthetic only."""
import asyncio
import json
from pathlib import Path
import traceback
import carb.settings
import omni.ext
import omni.kit.app
import omni.usd
from pxr import Usd, UsdGeom


class Probe(omni.ext.IExt):
    def on_startup(self,ext_id):self.task=asyncio.ensure_future(self.run())
    async def run(self):
        app=omni.kit.app.get_app();root=Path(carb.settings.get_settings().get('/exts/in.app.probe/output'))
        result={'status':'running','checks':[]};owner=None;review=None
        def check(name,ok):
            result['checks'].append({'name':name,'passed':bool(ok)})
            (root/'checkpoint.json').write_text(json.dumps(result,indent=2))
            print('MATERIAL_CHECK',name,bool(ok),flush=True)
        async def updates(n):
            for _ in range(n):await app.next_update_async()
        try:
            await updates(60)
            manager=app.get_extension_manager();manager.set_extension_enabled_immediate('mmporong.scene.review',True)
            from mmporong.scene.review.extension import get_active_extension
            from usd_scene_review import create_snapshot
            owner=get_active_extension();host=omni.usd.get_context();await host.new_stage_async()
            sentinel=host.get_stage();UsdGeom.Xform.Define(sentinel,'/Sentinel');original=sentinel.GetRootLayer().ExportToString()
            for side,y in (('A',0),('B',2)):
                source=root/('source-'+side);source.mkdir();file=source/'scene.usda'
                stage=Usd.Stage.CreateNew(str(file));UsdGeom.SetStageUpAxis(stage,'Z');UsdGeom.SetStageMetersPerUnit(stage,1)
                cube=UsdGeom.Cube.Define(stage,'/Box');cube.CreateSizeAttr(1);cube.AddTranslateOp().Set((0,y,0))
                floor=UsdGeom.Cube.Define(stage,'/Floor');floor.CreateSizeAttr(1)
                floor.AddTranslateOp().Set((0,0,-.7));floor.AddScaleOp().Set((8,8,.1))
                stage.GetRootLayer().Save();stage=cube=floor=None
                owner._paths[side].set_value(str(create_snapshot(file,root/('snapshot-'+side))))
            await owner._compare_async();await owner._open_in_app()
            review=owner._in_app
            change=next(c for c in owner._report['changes'] if c['path']=='/Box')
            owner._select(change);await owner._task;await updates(96)
            from omni.kit.viewport.utility import capture_viewport_to_file
            from omni.kit.renderer.capture import acquire_renderer_capture_interface
            capture_api=acquire_renderer_capture_interface()
            async def capture(name):
                item=owner._in_app.resources['B'];task=capture_viewport_to_file(item['widget'].viewport_api,str(root/(name+'.png')))
                await task.wait_for_result();capture_api.wait_async_capture()
            await capture('ghost-off')
            owner._ghost.set_value(True)
            for i in range(3):
                await updates(64);await capture('ghost-on-'+str(i))
            from PIL import Image, ImageChops
            with Image.open(root/'ghost-off.png') as a,Image.open(root/'ghost-on-2.png') as b:
                rgb=b.convert('RGB');pixels=list(rgb.getdata())
                green=sum(g>40 and g>r*1.12 and g>bl*1.12 for r,g,bl in pixels)
                result['green_fraction']=green/len(pixels)
                result['changed_bbox']=ImageChops.difference(a.convert('RGB'),rgb).getbbox()
                check('green area exceeds thin-edge-only threshold',result['green_fraction']>.005)
                check('ghost affects rendered pixels',result['changed_bbox'] is not None)
            capture_api.capture_next_frame_swapchain(str(root/'in-app-material.png'));await updates(5)
            capture_api.wait_async_capture();capture_api=None
            check('single owned split review remains open',owner._in_app.state=='open')
            # No reopen loop: isolate active extension disable from prior engine churn.
            manager.set_extension_enabled_immediate(manager.get_enabled_extension_id('mmporong.scene.review'),False)
            await updates(15)
            check('active extension disable confirmed',review.state=='closed' and review.last_close['preserved'])
            check('working stage preserved',host.get_stage()==sentinel and sentinel.GetRootLayer().ExportToString()==original)
            result['status']='passed' if all(c['passed'] for c in result['checks']) else 'failed'
        except Exception:
            result.update(status='failed',error=traceback.format_exc());print(result['error'],flush=True)
            if review:review.close_sync()
        (root/'result.json').write_text(json.dumps(result,indent=2))
        app.post_quit(0 if result['status']=='passed' else 1)
