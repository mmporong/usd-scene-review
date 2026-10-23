"""Synthetic same-process two-context lifecycle gate. No user scenes."""
import asyncio
import gc
import json
from pathlib import Path
import traceback
from uuid import uuid4
import carb.settings
import omni.ext
import omni.kit.app
import omni.ui as ui
import omni.usd
import omni.timeline
from omni.kit.widget.viewport import ViewportWidget
from pxr import Gf, Usd, UsdGeom, UsdUtils


class Probe(omni.ext.IExt):
    def on_startup(self,ext_id):self.task=asyncio.ensure_future(self.run())
    async def run(self):
        app=omni.kit.app.get_app()
        root=Path(carb.settings.get_settings().get('/exts/in.app.probe/output'))
        result={'status':'running','checks':[]}
        def check(name,ok):
            result['checks'].append({'name':name,'passed':bool(ok)})
            (root/'checkpoint.json').write_text(json.dumps(result,indent=2))
            print('IN_APP_CHECK',name,bool(ok),flush=True)
            if not ok:raise RuntimeError(name)
        async def updates(n):
            for _ in range(n):await app.next_update_async()
        try:
            await updates(60)
            host=omni.usd.get_context();await host.new_stage_async()
            sentinel=host.get_stage();UsdGeom.Xform.Define(sentinel,'/Sentinel')
            host.get_selection().set_selected_prim_paths(['/Sentinel'],False)
            timeline=omni.timeline.get_timeline_interface();timeline.set_current_time(7)
            await updates(20)
            original=(sentinel,sentinel.GetRootLayer().ExportToString(),sentinel.GetRootLayer().dirty,
                      host.get_selection().get_selected_prim_paths(),timeline.get_current_time())
            for cycle in range(2):
                resources=[]
                for side in ('A','B'):
                    name='review_probe_'+uuid4().hex
                    ctx=omni.usd.create_context(name)
                    own_timeline=omni.timeline.get_timeline_interface(name);ctx.set_timeline(name)
                    stage=Usd.Stage.CreateInMemory();UsdGeom.SetStageUpAxis(stage,'Z')
                    UsdGeom.Cube.Define(stage,'/World/Box').AddTranslateOp().Set((0 if side=='A' else 2,0,0))
                    camera=UsdGeom.Camera.Define(stage,'/ReviewCamera')
                    camera.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(7,-10,7),Gf.Vec3d(1,0,0),Gf.Vec3d(0,0,1)).GetInverse())
                    cache_id=UsdUtils.StageCache.Get().Insert(stage)
                    ok,error=await ctx.attach_stage_async(stage);check(side+' attach '+str(cycle),ok)
                    resources.append(dict(name=name,ctx=ctx,timeline=own_timeline,stage=stage,cache_id=cache_id))
                window=ui.Window('In-App A/B Lifecycle Gate',width=1500,height=800)
                widgets=[]
                with window.frame:
                    with ui.HStack(spacing=5):
                        for item in resources:
                            with ui.VStack():
                                ui.Label(item['name'].split('_')[0],height=22)
                                widgets.append(ViewportWidget(usd_context_name=item['name'],camera_path='/ReviewCamera',resolution=(640,640)))
                await updates(80)
                check('two real viewports same process '+str(cycle),all(w.viewport_api.stage==r['stage'] for w,r in zip(widgets,resources)))
                check('matching camera matrices '+str(cycle),widgets[0].viewport_api.view==widgets[1].viewport_api.view
                      and widgets[0].viewport_api.projection==widgets[1].viewport_api.projection)
                for widget in widgets:widget.viewport_api.updates_enabled=False;widget.destroy()
                widget=None;widgets.clear();window.frame.clear();window.destroy();window=None
                if cycle==0:await updates(10)
                gc.collect()
                for item in resources:
                    check('close owned stage '+str(cycle),item['ctx'].close_stage())
                    omni.usd.release_all_hydra_engines(item['ctx'])
                    UsdUtils.StageCache.Get().Erase(item['cache_id'])
                    item['ctx']=item['timeline']=item['stage']=None
                ctx=stage=camera=own_timeline=None
                if cycle==0:await updates(10)
                gc.collect()
                for item in resources:
                    check('destroy owned context '+str(cycle),omni.usd.destroy_context(item['name']))
                    check('destroy owned timeline '+str(cycle),omni.timeline.destroy_timeline(item['name']))
                resources.clear();await updates(10)
                after=(
                    host.get_stage(),sentinel.GetRootLayer().ExportToString(),sentinel.GetRootLayer().dirty,
                    host.get_selection().get_selected_prim_paths(),timeline.get_current_time())
                result['host_preservation']={key:a==b for key,a,b in zip(('stage','root_text','dirty','selection','time'),original,after)}
                check('host stage selection dirty time preserved '+str(cycle),original==after)
            result['status']='passed'
        except Exception:result.update(status='failed',error=traceback.format_exc());print(result['error'],flush=True)
        (root/'result.json').write_text(json.dumps(result,indent=2))
        app.post_quit(0 if result['status']=='passed' else 1)
