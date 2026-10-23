"""SDK-only: one owned context, two public native textures, no UI widgets."""
import asyncio
import gc
import json
from pathlib import Path
from uuid import uuid4
import carb.settings
import omni.ext
import omni.kit.app
import omni.usd
import omni.timeline
from omni.kit.hydra_texture import create_hydra_texture,EVENT_TYPE_DRAWABLE_CHANGED
from pxr import Usd,UsdGeom,UsdUtils,Gf


class Probe(omni.ext.IExt):
    def on_startup(self,ext_id):self.task=asyncio.ensure_future(self.run())

    async def run(self):
        app=omni.kit.app.get_app();root=Path(carb.settings.get_settings().get('/exts/in.app.probe/output'))
        result={'status':'running','control':'one context, two native textures, zero added UI widgets','checks':[],'phases':[]}
        self.textures=[];self.subscriptions=[];self.frames=[0,0]
        def phase(name):
            result['phases'].append(name)
            (root/'checkpoint.json').write_text(json.dumps(result,indent=2))
            print('TEXTURE_PHASE',name,flush=True)
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
            name='direct_texture_probe_'+uuid4().hex;ctx=omni.usd.create_context(name)
            own_timeline=omni.timeline.get_timeline_interface(name);ctx.set_timeline(name)
            stage=Usd.Stage.CreateInMemory();UsdGeom.SetStageUpAxis(stage,'Z')
            UsdGeom.Cube.Define(stage,'/Cube')
            camera=UsdGeom.Camera.Define(stage,'/ReviewCamera')
            camera.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(5,-7,5),Gf.Vec3d(0),Gf.Vec3d(0,0,1)).GetInverse())
            cache=UsdUtils.StageCache.Get().Insert(stage)
            ok,error=await ctx.attach_stage_async(stage)
            if not ok:raise RuntimeError('owned stage attach failed')
            # Direct factory control only: exactly one explicit engine attachment,
            # with no widget present to perform a second implicit attachment.
            omni.usd.add_hydra_engine('rtx',ctx);await updates(4)
            for index in range(2):
                phase('before-create-native-texture-'+str(index))
                texture=create_hydra_texture(name='direct_texture_'+uuid4().hex,width=500,height=500,
                    usd_context_name=name,usd_camera_path='/ReviewCamera',hydra_engine_name='rtx',is_async=False)
                self.textures.append(texture)
                def frame(event,i=index):
                    if event.type==EVENT_TYPE_DRAWABLE_CHANGED:self.frames[i]+=1
                self.subscriptions.append(texture.get_event_stream().create_subscription_to_push(frame))
                async def rendered(i=index):
                    while self.frames[i]<8:await app.next_update_async()
                await asyncio.wait_for(rendered(),30)
                phase('rendered-native-texture-'+str(index))
            texture=None
            result['checks'].append({'name':'two native textures render with no added UI','passed':all(n>=8 for n in self.frames)})
            for index,texture in enumerate(self.textures):
                phase('before-native-updates-off-'+str(index))
                texture.set_updates_enabled(False)
                phase('after-native-updates-off-'+str(index));await updates(4)
            texture=None;self.subscriptions.clear()
            for index in range(len(self.textures)):
                phase('before-native-texture-release-'+str(index))
                self.textures[index]=None;gc.collect();await updates(4)
                phase('after-native-texture-release-'+str(index))
            self.textures.clear();phase('before-owned-stage-close')
            if not ctx.close_stage():raise RuntimeError('owned stage close unconfirmed')
            omni.usd.release_all_hydra_engines(ctx);UsdUtils.StageCache.Get().Erase(cache)
            ctx=stage=camera=own_timeline=None;gc.collect();await updates(10)
            if not omni.usd.destroy_context(name):raise RuntimeError('owned context destruction unconfirmed')
            if not omni.timeline.destroy_timeline(name):raise RuntimeError('owned timeline destruction unconfirmed')
            result['checks'].append({'name':'default stage selection and time preserved','passed':identity()==original})
            result['status']='passed' if all(c['passed'] for c in result['checks']) else 'failed'
        except Exception as exc:result.update(status='failed',reason=type(exc).__name__+': '+str(exc))
        (root/'result.json').write_text(json.dumps(result,indent=2))
        safe=result['status']=='passed' and original is not None and identity()==original and host.get_stage().GetRootLayer().anonymous
        if safe:app.post_uncancellable_quit(0)
        else:app.post_quit(1)
