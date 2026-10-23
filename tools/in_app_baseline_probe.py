"""Project-free full-Isaac shutdown control, with no extra stage or viewport."""
import asyncio
import json
from pathlib import Path
import carb.settings
import omni.ext
import omni.kit.app
import omni.usd


class Probe(omni.ext.IExt):
    def on_startup(self,ext_id):self.task=asyncio.ensure_future(self.run())

    async def run(self):
        app=omni.kit.app.get_app()
        root=Path(carb.settings.get_settings().get('/exts/in.app.probe/output'))
        result={'status':'running','control':'project-free baseline','checks':[]}
        try:
            async def ready():
                while not app.is_app_ready():await app.next_update_async()
                from omni.kit.viewport.utility import get_active_viewport,next_viewport_frame_async
                while omni.usd.get_context().get_stage() is None or get_active_viewport() is None:
                    await app.next_update_async()
                await next_viewport_frame_async(get_active_viewport())
            await asyncio.wait_for(ready(),120)
            for _ in range(20):await app.next_update_async()
            enabled=app.get_extension_manager().is_extension_enabled('mmporong.scene.review')
            stage=omni.usd.get_context().get_stage()
            result['checks'].append({'name':'review extension never enabled','passed':not enabled})
            result['checks'].append({'name':'startup stage is anonymous','passed':bool(stage and stage.GetRootLayer().anonymous)})
            result['status']='passed' if all(c['passed'] for c in result['checks']) else 'failed'
        except Exception as exc:
            result.update(status='failed',reason=type(exc).__name__+': '+str(exc))
        (root/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        # Same quit API as the topology control; this still runs normal SDK unload.
        # The launcher reports actual exit/crash independently of these checks.
        if result['status']=='passed':app.post_uncancellable_quit(0)
        else:app.post_quit(1)
