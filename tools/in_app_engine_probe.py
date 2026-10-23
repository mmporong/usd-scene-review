"""Owned SDK topology controls; use the fail-fast launcher. No renderer globals."""
import asyncio
import gc
import json
from pathlib import Path
from uuid import uuid4
import carb.settings
import omni.ext
import omni.kit.app
import omni.timeline
import omni.ui as ui
import omni.usd
from omni.kit.widget.viewport import ViewportWidget
from pxr import Gf, Usd, UsdGeom, UsdUtils


def topology_layout(topology):
    """Context index per viewport, independent of SDK imports in CPU tests."""
    layouts={'single':(0,), 'shared':(0,0), 'two-contexts':(0,1)}
    if topology not in layouts:raise ValueError('Unknown diagnostic topology')
    return layouts[topology]


class Probe(omni.ext.IExt):
    def on_startup(self,ext_id):self.task=asyncio.ensure_future(self.run())

    async def run(self):
        app=omni.kit.app.get_app();settings=carb.settings.get_settings()
        root=Path(settings.get('/exts/in.app.probe/output'))
        topology=settings.get('/exts/in.app.probe/topology') or 'shared'
        modes=('single','shared','two-contexts') if topology=='sequence' else (topology,)
        result={'status':'running','topology':topology,'checks':[],'phases':[]}
        self.resources=[];self.widgets=[];self.window=None;current='startup'
        def phase(operation,ctx=None,**details):
            result['phases'].append(dict(control=current,operation=operation,
                context=ctx.get_name() if ctx else None,
                attached_engines=list(ctx.get_attached_hydra_engine_names()) if ctx else [],**details))
            (root/'checkpoint.json').write_text(json.dumps(result,indent=2))
            print('ENGINE_PHASE',json.dumps(result['phases'][-1]),flush=True)
        async def updates(n):
            for _ in range(n):await app.next_update_async()
        host=omni.usd.get_context();original=None
        def host_identity():
            stage=host.get_stage()
            return (stage,stage.GetRootLayer().ExportToString(),stage.GetSessionLayer().ExportToString(),
                    stage.GetRootLayer().dirty,host.get_selection().get_selected_prim_paths(),
                    omni.timeline.get_timeline_interface().get_current_time()) if stage else None
        try:
            async def ready():
                while not app.is_app_ready():await app.next_update_async()
            await asyncio.wait_for(ready(),120);phase('app-ready')
            if app.get_extension_manager().is_extension_enabled('isaacsim.app.setup'):
                from omni.kit.viewport.utility import get_active_viewport,next_viewport_frame_async
                async def initial_frame():
                    while host.get_stage() is None or get_active_viewport() is None:await app.next_update_async()
                    await next_viewport_frame_async(get_active_viewport())
                await asyncio.wait_for(initial_frame(),60);await updates(20)
                phase('default-viewport-frame-ready')
            original=host_identity()
            result['app_identity']={'filename':app.get_app_filename(),'name':app.get_app_name(),
                'full_experience_enabled':app.get_extension_manager().is_extension_enabled('isaacsim.exp.full')}
            if settings.get('/exts/in.app.probe/verifyFullGuard'):
                manager=app.get_extension_manager()
                manager.set_extension_enabled_immediate('mmporong.scene.review',True)
                from mmporong.scene.review.extension import get_active_extension
                from mmporong.scene.review.in_app import full_host_blocked
                owner=get_active_extension();refused=False
                try:await owner._open_in_app()
                except RuntimeError as exc:refused='Full Isaac' in str(exc)
                guarded=bool(full_host_blocked() and owner._in_app_blocked and refused and owner._in_app is None)
                result['checks'].append(dict(name='Full product refuses before review ownership',passed=guarded))
                if not guarded:raise RuntimeError('Product full-host guard failed')
                phase('full-product-guard-confirmed')
            for current in modes:
                layout=topology_layout(current)
                for index in range(max(layout)+1):
                    name='review_engine_probe_'+uuid4().hex
                    phase('before-create-context');ctx=omni.usd.create_context(name);phase('after-create-context',ctx)
                    timeline=omni.timeline.get_timeline_interface(name);ctx.set_timeline(name)
                    stage=Usd.Stage.CreateInMemory();UsdGeom.SetStageUpAxis(stage,'Z')
                    UsdGeom.Cube.Define(stage,'/Box').CreateSizeAttr(1+index)
                    camera=UsdGeom.Camera.Define(stage,'/ReviewCamera')
                    camera.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(5,-7,5),Gf.Vec3d(0),Gf.Vec3d(0,0,1)).GetInverse())
                    item=dict(name=name,ctx=ctx,timeline=timeline,stage=stage,cache=UsdUtils.StageCache.Get().Insert(stage))
                    self.resources.append(item);phase('before-attach-stage',ctx)
                    ok,error=await asyncio.shield(ctx.attach_stage_async(stage));phase('after-attach-stage',ctx)
                    if not ok:raise RuntimeError('Stage attachment unconfirmed')
                self.window=ui.Window('SDK Engine Topology Diagnostic',width=1250,height=700)
                frames=[]
                with self.window.frame:
                    with ui.HStack():
                        for _ in layout:frames.append(ui.Frame())
                # Wait for each real texture binding before requesting the next.
                # No extra engine calls are made solely for instrumentation.
                for index,context_index in enumerate(layout):
                    item=self.resources[context_index];phase('before-viewport-'+str(index),item['ctx'])
                    with frames[index]:
                        widget=ViewportWidget(usd_context_name=item['name'],camera_path='/ReviewCamera',
                                              resolution=(500,500),hd_engine='rtx')
                    self.widgets.append(widget);phase('after-viewport-'+str(index),item['ctx'])
                    await asyncio.wait_for(widget.viewport_api.wait_for_rendered_frames(8),30)
                    info=widget.viewport_api.frame_info
                    phase('rendered-viewport-'+str(index),item['ctx'],viewport_engine=widget.viewport_api.hydra_engine,
                          frame_identifiers={k:v for k,v in info.items() if ('handle' in k.lower() or 'engine' in k.lower())
                                             and isinstance(v,(str,int,float,bool))})
                rendered=all(w.viewport_api.stage==self.resources[layout[i]]['stage']
                             and bool(w.viewport_api.frame_info) for i,w in enumerate(self.widgets))
                result['checks'].append(dict(name=current+' renders intended stage(s)',passed=rendered))
                if not rendered:raise RuntimeError('Rendered stage mismatch')
                for index,widget in enumerate(self.widgets):
                    phase('before-destroy-viewport-'+str(index),self.resources[layout[index]]['ctx'])
                    widget.destroy()
                    phase('after-destroy-viewport-'+str(index),self.resources[layout[index]]['ctx'])
                    # Isolate asynchronous texture release from the next widget
                    # destruction before attributing failures to context close.
                    await updates(2)
                    phase('after-destroy-frame-barrier-'+str(index),self.resources[layout[index]]['ctx'])
                widget=None;self.widgets.clear();frames.clear();self.window.frame.clear();self.window.destroy();self.window=None
                await updates(10)
                for item in self.resources:
                    phase('before-stage-cleanup',item['ctx'])
                    if not item['ctx'].close_stage():raise RuntimeError('Stage close unconfirmed')
                    phase('after-close-stage',item['ctx'])
                    omni.usd.release_all_hydra_engines(item['ctx'])
                    phase('after-release-engines',item['ctx'])
                    UsdUtils.StageCache.Get().Erase(item['cache'])
                    item['ctx']=item['stage']=item['timeline']=None
                ctx=stage=camera=timeline=None;gc.collect();await updates(10)
                for item in self.resources:
                    if not omni.usd.destroy_context(item['name']):raise RuntimeError('Context destruction unconfirmed')
                    if not omni.timeline.destroy_timeline(item['name']):raise RuntimeError('Timeline destruction unconfirmed')
                self.resources.clear();phase('cleanup-confirmed')
                preserved=host_identity()==original
                result['checks'].append(dict(name=current+' preserves default stage/selection/time',passed=preserved))
                if not preserved:raise RuntimeError('Default stage changed')
            result['status']='passed'
        except Exception as exc:
            result.update(status='failed',reason=type(exc).__name__+': '+str(exc))
        (root/'result.json').write_text(json.dumps(result,indent=2))
        # Only the fresh, owned host's unchanged anonymous startup stage qualifies
        # for an uncancellable normal quit; no user save preference is changed.
        safe_quit=(result['status']=='passed' and not self.resources and not self.widgets
                   and original is not None and host_identity()==original
                   and host.get_stage().GetRootLayer().anonymous)
        if safe_quit:app.post_uncancellable_quit(0)
        else:app.post_quit(1)
