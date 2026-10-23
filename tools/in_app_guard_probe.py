"""Private guard-only native check. Never bypasses or opens experimental review."""
import asyncio
import json
from pathlib import Path
import carb.settings
import omni.ext
import omni.kit.app
import omni.usd
import omni.timeline


class Probe(omni.ext.IExt):
    def on_startup(self,ext_id):self.task=asyncio.ensure_future(self.run())

    async def run(self):
        app=omni.kit.app.get_app();settings=carb.settings.get_settings()
        root=Path(settings.get('/exts/in.app.probe/output'))
        result={'status':'running','control':'Full guard only; no bypass','checks':[]}
        def check(name,value):
            result['checks'].append({'name':name,'passed':bool(value)})
            (root/'checkpoint.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            print('GUARD_CHECK',name,bool(value),flush=True)
            if not value:raise RuntimeError(name)
        host=omni.usd.get_context();original=None
        def identity():
            stage=host.get_stage()
            return (stage,stage.GetRootLayer().ExportToString(),stage.GetSessionLayer().ExportToString(),
                stage.GetRootLayer().dirty,host.get_selection().get_selected_prim_paths(),
                omni.timeline.get_timeline_interface().get_current_time()) if stage else None
        try:
            from omni.kit.viewport.utility import get_active_viewport,next_viewport_frame_async
            async def ready():
                while not app.is_app_ready() or host.get_stage() is None or get_active_viewport() is None:
                    await app.next_update_async()
                await next_viewport_frame_async(get_active_viewport())
            await asyncio.wait_for(ready(),120)
            for _ in range(20):await app.next_update_async()
            original=identity();manager=app.get_extension_manager()
            result['app_identity']={'filename':app.get_app_filename(),'name':app.get_app_name(),
                'full_experience_enabled':manager.is_extension_enabled('isaacsim.exp.full')}
            check('actual Full experience enabled',result['app_identity']['full_experience_enabled'])
            manager.set_extension_enabled_immediate('mmporong.scene.review',True)
            for _ in range(5):await app.next_update_async()
            from mmporong.scene.review.extension import get_active_extension
            from mmporong.scene.review.in_app import InAppReview,full_host_blocked,retained_review
            owner=get_active_extension()
            check('packaged Full-host guard returns true',full_host_blocked())
            check('extension UI state is blocked',owner is not None and owner._in_app_blocked)
            import omni.kit.ui_test as ui_test
            button=ui_test.find("USD Scene Review//Frame/**/Button[*].text=='Open A/B in Isaac'")
            check('actual Open A/B button is disabled',button is not None and not button.widget.enabled)
            button=None
            refused=False
            try:await owner._open_in_app()
            except RuntimeError as exc:refused='Full Isaac' in str(exc)
            check('extension API refuses before review ownership',refused and owner._in_app is None)
            review=InAppReview(lambda message:None);refused=False
            try:await review.open({}, {})
            except RuntimeError as exc:refused='Full Isaac' in str(exc)
            check('direct review API refuses before native ownership',
                  refused and review.state=='closed' and not review.resources and retained_review() is None)
            review=None
            check('working stage session selection and time preserved',identity()==original)
            check('probe bypass setting remains false',not settings.get('/exts/in.app.probe/fullFeatureValidation'))
            result['status']='passed'
        except Exception as exc:
            result.update(status='failed',reason=type(exc).__name__+': '+str(exc))
        (root/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        safe=(original is not None and identity()==original and host.get_stage().GetRootLayer().anonymous)
        if safe:app.post_uncancellable_quit(0 if result['status']=='passed' else 1)
        else:app.post_quit(1)
