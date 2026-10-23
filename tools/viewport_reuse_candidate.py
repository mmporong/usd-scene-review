"""Independent stages, one explicit public Widget reused for captures.

This is sequential cached A/B, not two live viewports or a product adapter.
"""
import asyncio
import gc
import json
from pathlib import Path
from uuid import uuid4
import omni.kit.app
import omni.ui as ui
import omni.usd
import omni.timeline
from omni.kit.widget.viewport import ViewportWidget
from omni.kit.viewport.utility import capture_viewport_to_file
from pxr import Gf,Usd,UsdGeom,UsdLux,UsdShade,Sdf,UsdUtils


def revision_fixture(side):
    if side not in ('A','B'):raise ValueError('Expected revision A or B')
    stage=Usd.Stage.CreateInMemory();UsdGeom.SetStageUpAxis(stage,'Z');UsdGeom.SetStageMetersPerUnit(stage,1)
    cube=UsdGeom.Cube.Define(stage,'/World/Item');cube.CreateSizeAttr(2)
    cube.AddTranslateOp().Set((-2 if side=='A' else 2,0,1))
    UsdGeom.Xform.Define(stage,'/World/Only'+side)
    material=UsdShade.Material.Define(stage,'/World/Looks/Material')
    shader=UsdShade.Shader.Define(stage,'/World/Looks/Material/Shader');shader.CreateIdAttr('UsdPreviewSurface')
    shader.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set((.8,.03,.03) if side=='A' else (.03,.03,.8))
    shader.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(.8)
    shader.CreateOutput('surface',Sdf.ValueTypeNames.Token)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(),'surface')
    UsdShade.MaterialBindingAPI.Apply(cube.GetPrim()).Bind(material)
    UsdLux.DomeLight.Define(stage,'/World/Light').CreateIntensityAttr(1000 if side=='A' else 500)
    camera=UsdGeom.Camera.Define(stage,'/ReviewCamera')
    camera.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(6,-14,8),Gf.Vec3d(0,0,1),Gf.Vec3d(0,0,1)).GetInverse())
    stage.SetEditTarget(stage.GetSessionLayer())
    return stage


class ReuseCandidate:
    async def run(self,parent,root):
        app=omni.kit.app.get_app()
        result={'status':'running','candidate':'sequential captures, one official viewport; not live split','checks':[],'phases':[]}
        self.window=None;self.widget=None;self.pair_window=None;self.resources=[]
        result['ownership']='explicit public Widget in plain UI Window'
        def phase(name):
            result['phases'].append(name);(root/'reuse-checkpoint.json').write_text(json.dumps(result,indent=2))
            observer=getattr(parent,'native_observe',None)
            if observer is not None:observer('candidate:'+name)
            print('REUSE_PHASE',name,flush=True)
        def check(name,value):
            result['checks'].append({'name':name,'passed':bool(value)});phase('check '+name)
            parent.check('reuse: '+name,value)
        async def updates(n):
            for _ in range(n):await app.next_update_async()
        host=omni.usd.get_context();original=None
        def identity():
            stage=host.get_stage()
            return (stage,stage.GetRootLayer().ExportToString(),stage.GetSessionLayer().ExportToString(),stage.GetRootLayer().dirty,
                    host.get_selection().get_selected_prim_paths(),omni.timeline.get_timeline_interface().get_current_time()) if stage else None
        try:
            from omni.kit.viewport.utility import get_active_viewport,next_viewport_frame_async
            async def ready():
                while not app.is_app_ready() or host.get_stage() is None or get_active_viewport() is None:await app.next_update_async()
                await next_viewport_frame_async(get_active_viewport())
            await asyncio.wait_for(ready(),120);await updates(20);original=identity()
            baseline_views=len(list(ViewportWidget.get_instances()))
            for cycle in range(2):
                phase('cycle-'+str(cycle)+'-create-context')
                name='review_reuse_'+uuid4().hex;ctx=omni.usd.create_context(name)
                phase('cycle-'+str(cycle)+'-context-created')
                timeline=omni.timeline.get_timeline_interface(name);ctx.set_timeline(name)
                phase('cycle-'+str(cycle)+'-timeline-created')
                stages={s:revision_fixture(s) for s in ('A','B')}
                phase('cycle-'+str(cycle)+'-fixtures-authored')
                source={s:stage.GetRootLayer().ExportToString() for s,stage in stages.items()}
                cameras={s:UsdGeom.Camera(stage.GetPrimAtPath('/ReviewCamera')).GetCamera().transform for s,stage in stages.items()}
                cache={s:UsdUtils.StageCache.Get().Insert(stage) for s,stage in stages.items()}
                phase('cycle-'+str(cycle)+'-cache-inserted')
                self.resources=[dict(name=name,ctx=ctx,stages=stages,cache=cache,timeline=timeline)]
                matrices=[];captures=[]
                for step,side in enumerate(('A','B','A')):
                    phase('cycle-'+str(cycle)+'-before-attach-'+str(step)+'-'+side)
                    ok,error=await asyncio.wait_for(asyncio.shield(ctx.attach_stage_async(stages[side])),30)
                    check('attach '+str(cycle)+'/'+str(step),ok)
                    stages[side].SetEditTarget(stages[side].GetSessionLayer())
                    if self.window is None:
                        self.window=ui.Window('Single Renderer Reuse Candidate',width=700,height=650)
                        with self.window.frame:
                            self.widget=ViewportWidget(usd_context_name=name,camera_path='/ReviewCamera',
                                viewport_api='reuse_owned_'+uuid4().hex,resolution=(600,600))
                        check('owned viewport created '+str(cycle),self.window is not None)
                    api=self.widget.viewport_api
                    api.camera_path='/ReviewCamera'
                    await asyncio.wait_for(api.wait_for_rendered_frames(32),30)
                    check('one extra viewport only '+str(cycle)+'/'+str(step),len(list(ViewportWidget.get_instances()))==baseline_views+1)
                    other='B' if side=='A' else 'A'
                    check('independent stage namespace '+str(cycle)+'/'+str(step),
                          ctx.get_stage()==stages[side] and bool(api.stage.GetPrimAtPath('/World/Only'+side))
                          and not api.stage.GetPrimAtPath('/World/Only'+other))
                    matrices.append((str(api.view),str(api.projection)))
                    path=root/('cycle-'+str(cycle)+'-'+str(step)+'-'+side+'.png')
                    capture=capture_viewport_to_file(api,str(path));await capture.wait_for_result();capture=None
                    from omni.kit.renderer.capture import acquire_renderer_capture_interface
                    recorder=acquire_renderer_capture_interface();recorder.wait_async_capture();recorder=None
                    captures.append(path);phase('captured '+str(cycle)+'/'+str(step))
                    check('source roots and cameras preserved '+str(cycle)+'/'+str(step),
                          all(stage.GetRootLayer().ExportToString()==source[s]
                              and UsdGeom.Camera(stage.GetPrimAtPath('/ReviewCamera')).GetCamera().transform==cameras[s]
                              for s,stage in stages.items()))
                check('common camera pose/projection '+str(cycle),len(set(matrices))==1)
                from PIL import Image
                colors=[]
                for path in captures:
                    with Image.open(path) as frame:
                        rgb=list(frame.convert('RGB').getdata())
                        colors.append((sum(r>b*1.4 and r>g*1.4 for r,g,b in rgb)/len(rgb),
                                       sum(b>r*1.4 and b>g*1.4 for r,g,b in rgb)/len(rgb)))
                check('actual A/B/A rendered content '+str(cycle),
                      colors[0][0]>.005 and colors[0][0]>colors[0][1]*4
                      and colors[1][1]>.005 and colors[1][1]>colors[1][0]*4
                      and colors[2][0]>.005 and colors[2][0]>colors[2][1]*4)
                result.setdefault('capture_color_fractions',[]).append(colors)
                if cycle==0:
                    self.pair_window=ui.Window('Cached A/B Candidate - not live split',width=1100,height=600)
                    with self.pair_window.frame:
                        with ui.HStack():
                            for side,path in zip(('A BEFORE','B AFTER'),captures[:2]):
                                with ui.VStack():ui.Label(side+' / sequential capture',height=30);ui.Image(str(path))
                    await updates(8)
                    from omni.kit.renderer.capture import acquire_renderer_capture_interface
                    recorder=acquire_renderer_capture_interface();recorder.capture_next_frame_swapchain(str(root/'cached-pair-candidate.png'))
                    await updates(5);recorder.wait_async_capture();recorder=None
                    self.pair_window.frame.clear();self.pair_window.destroy();self.pair_window=None
                api=None;phase('cycle-'+str(cycle)+'-before-window-destroy')
                if self.widget:self.widget.destroy();self.widget=None
                self.window.destroy();self.window=None;gc.collect();await updates(10)
                check('owned viewport actually removed '+str(cycle),len(list(ViewportWidget.get_instances()))==baseline_views)
                phase('cycle-'+str(cycle)+'-before-stage-close')
                check('owned stage closed '+str(cycle),ctx.close_stage() and ctx.get_stage() is None)
                omni.usd.release_all_hydra_engines(ctx)
                for identifier in cache.values():UsdUtils.StageCache.Get().Erase(identifier)
                self.resources[0].clear();self.resources.clear();stages={};cache={};ctx=timeline=stage=None;gc.collect();await updates(10)
                check('owned context destroyed '+str(cycle),omni.usd.destroy_context(name))
                check('owned timeline destroyed '+str(cycle),omni.timeline.destroy_timeline(name))
                check('working stage selection and time preserved '+str(cycle),identity()==original)
            result['status']='passed'
        except Exception as exc:result.update(status='failed',reason=type(exc).__name__+': '+str(exc))
        result['owned_resources_remaining']=bool(self.resources or self.window or self.widget or self.pair_window)
        result['working_stage_preserved']=original is not None and identity()==original
        result['source_commit']='ca940ec67c9eff6f590de62676aa6f9c8efe5c68'
        (root/'reuse-result.json').write_text(json.dumps(result,indent=2))
        if result['status']!='passed' or result['owned_resources_remaining'] or not result['working_stage_preserved']:
            raise RuntimeError('Sequential reuse candidate failed: '+result.get('reason','ownership/preservation'))
        return result


async def evaluate(parent,root):
    # No app quit, default-stage close, product guard bypass or global settings.
    return await ReuseCandidate().run(parent,root)
