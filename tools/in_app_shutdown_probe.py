"""Owned clean-file shutdown controls; no review extension or added viewport.

The launcher creates the only file this probe may open. It never saves, clears
pending edits, changes global save policy, or connects to an existing host.
"""
import asyncio
import hashlib
import json
import re
from pathlib import Path
import carb.settings
import omni.ext
import omni.kit.app
import omni.usd


class Probe(omni.ext.IExt):
    def on_startup(self, ext_id):
        self.subscriptions=[]
        self.task=asyncio.ensure_future(self.run())

    def write(self):
        (self.root/'result.json').write_text(json.dumps(self.result,indent=2),encoding='utf-8')

    def check(self, name, value):
        self.result['checks'].append({'name':name,'passed':bool(value)})
        if not value:
            self.result['status']='failed'
        self.write()
        if not value:
            raise RuntimeError(name)

    def on_shutdown(self):
        if hasattr(self,'result'):
            self.result['probe_unload_observed']=True
            self.write()
        self.subscriptions.clear()
        if self.task and not self.task.done():
            self.task.cancel()
        self.task=None

    async def run(self):
        app=omni.kit.app.get_app()
        settings=carb.settings.get_settings()
        self.root=Path(settings.get('/exts/in.app.probe/output')).resolve()
        route=settings.get('/exts/in.app.probe/shutdownRoute')
        self.result={'status':'running','control':'unchanged owned file','route':route,
                     'checks':[],'stage_events':[],'quit_events':[],
                     'discard_clicked':False,'file_close_callback':False}
        ctx=omni.usd.get_context()
        fixture=self.root/'shutdown-fixture.usda'
        try:
            self.check('supported route',route in ('normal','file-close','uncancellable'))
            self.check('owned portable config',Path(settings.get('/app/userConfigPath')).resolve()==self.root/'user.config.json')
            self.check('review extension never enabled',not app.get_extension_manager().is_extension_enabled('mmporong.scene.review'))
            async def ready():
                from omni.kit.viewport.utility import get_active_viewport,next_viewport_frame_async
                while not app.is_app_ready() or ctx.get_stage() is None or get_active_viewport() is None:
                    await app.next_update_async()
                await next_viewport_frame_async(get_active_viewport())
            await asyncio.wait_for(ready(),120)
            profile_name=settings.get('/exts/in.app.probe/profile')
            if profile_name:
                profile=json.loads((self.root/'shutdown-profile.json').read_text())
                manager=app.get_extension_manager()
                import ctypes
                kernel=ctypes.WinDLL('kernel32',use_last_error=True)
                kernel.GetModuleHandleW.argtypes=[ctypes.c_wchar_p]
                kernel.GetModuleHandleW.restype=ctypes.c_void_p
                nav={'core_enabled':manager.is_extension_enabled('omni.anim.navigation.core'),
                     'recast_enabled':manager.is_extension_enabled('omni.anim.navigation.recast'),
                     'schema_enabled':manager.is_extension_enabled('omni.anim.navigation.schema'),
                     'core_dll_loaded':bool(kernel.GetModuleHandleW('omni.anim.navigation.core.plugin.dll'))}
                self.result['navigation_control']=nav
                expected=profile['variant']=='matched-full'
                self.check('navigation core matches profile',nav['core_enabled'] is expected)
                self.check('navigation recast matches profile',nav['recast_enabled'] is expected)
                self.check('navigation schema retained',nav['schema_enabled'])
                self.check('native navigation module matches profile',nav['core_dll_loaded'] is expected)
                console=(self.root/'console.log').read_text(encoding='utf-8',errors='replace')
                self.check('no startup dependency failures',not any(s in console for s in ('Failed to resolve extension dependencies','Failed to startup extension','ModuleNotFoundError:','ImportError:')))
                actual=sorted(set(re.findall(r'\[ext: ([A-Za-z0-9_.]+-[^\]]+)\] startup',console)))
                expected_ids=profile['observation']['startup_extensions']+(profile['navigation_extension_ids'] if expected else [])
                self.result['startup_extensions']=actual
                self.check('startup inventory matches pinned profile',actual==sorted(set(expected_ids)))
            self.check('only fresh anonymous startup replaced',ctx.get_stage().GetRootLayer().anonymous)
            original_hash=hashlib.sha256(fixture.read_bytes()).hexdigest()
            opened=await ctx.open_stage_async(str(fixture))
            self.check('owned fixture opened',bool(opened[0]))
            for _ in range(20):
                await app.next_update_async()
            self.check('only owned fixture active',Path(ctx.get_stage().GetRootLayer().realPath).resolve()==fixture)
            self.check('fixture root is not dirty',not ctx.get_stage().GetRootLayer().dirty)
            self.result['pending_edit_before_quit']=ctx.has_pending_edit()
            self.result['session_dirty_before_quit']=ctx.get_stage().GetSessionLayer().dirty
            self.result['fixture_sha256']=original_hash
            def stage_event(event):
                number=int(event.type)
                self.result.setdefault('raw_stage_events',[]).append(number)
                for name in ('CLOSING','CLOSED'):
                    if number==int(getattr(omni.usd.StageEventType,name)):
                        self.result['stage_events'].append(name)
                        self.result['fixture_bytes_preserved']=hashlib.sha256(fixture.read_bytes()).hexdigest()==original_hash
                self.write()
            def quit_event(event):
                self.result['quit_events'].append(int(event.type))
                self.write()
            self.subscriptions.append(ctx.get_stage_event_stream().create_subscription_to_pop(stage_event,name='owned shutdown stage receipt'))
            self.subscriptions.append(app.get_shutdown_event_stream().create_subscription_to_pop(quit_event,name='owned shutdown route receipt',order=-1))
            if profile_name and profile.get('candidate'):
                self.check('candidate only on reduced profile',profile['variant']=='no-navigation' and profile['candidate']=='viewport-reuse')
                settings_keys=('/rtx/useViewLightingMode','/rtx/post/tonemap/op','/app/asyncRendering',
                    '/renderer/multiGpu/autoEnable','/app/fastShutdown','/app/settings/persistent')
                before_settings={key:settings.get(key) for key in settings_keys}
                self.result['candidate']={'status':'running','kind':'sequential capture, not live split'}
                self.write()
                from viewport_reuse_candidate import evaluate
                candidate=await evaluate(self,self.root)
                self.result['candidate']=candidate
                self.result['candidate_settings_preserved']=before_settings=={key:settings.get(key) for key in settings_keys}
                self.check('candidate rendering settings preserved',self.result['candidate_settings_preserved'])
            self.result['status']='passed'
            self.write()
            if route=='uncancellable':
                app.post_uncancellable_quit(0)
                return
            if route=='file-close':
                import omni.kit.window.file as file_window
                def closed():
                    self.result['file_close_callback']=True
                    self.check('public close leaves no stage',ctx.get_stage() is None)
                    app.post_quit(0)
                file_window.close(closed)
            else:
                app.post_quit(0)
            # UI-test events target only the fresh owned host. Never save or
            # bypass a prompt by mutating pending-edit/global settings.
            import omni.kit.ui_test as ui_test
            for _ in range(600):
                await app.next_update_async()
                if not self.result['discard_clicked']:
                    candidates=[]
                    for button in ui_test.find_all('*//Frame/**/Button[*]'):
                        if button.widget.text!="Don't Save":
                            continue
                        scope=button.path.split('//',1)[0]
                        labels=ui_test.find_all(scope+'//Frame/**/Label[*]')
                        if any(label.widget.text=='Would you like to save this stage?' for label in labels):
                            candidates.append(button)
                    if candidates:
                        self.check('one owned save prompt',len(candidates)==1)
                        self.check('discard only owned fixture',ctx.get_stage() is not None and Path(ctx.get_stage().GetRootLayer().realPath).resolve()==fixture)
                        self.result['discard_clicked']=True
                        self.write()
                        await candidates[0].click()
            self.result.update(status='failed',reason='normal shutdown did not finish within 600 updates')
            self.write()
        except Exception as exc:
            self.result.update(status='failed',reason=type(exc).__name__+': '+str(exc))
            self.write()
            # Leave the owned host for launcher timeout/containment on failure;
            # do not substitute another quit API and mislabel the route.
