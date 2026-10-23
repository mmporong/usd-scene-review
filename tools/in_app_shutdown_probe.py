"""Owned clean-file shutdown controls and explicit reduced-profile treatments.

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
            from shutdown_observation import window_receipts,close_receipt,context_receipt
            initial_stage=ctx.get_stage()
            def native_observe(phase):
                receipt=context_receipt(omni.usd.get_context(),ctx,initial_stage,fixture)
                receipt['phase']=phase
                self.result.setdefault('close_observations',[]).append(receipt)
                self.write()
                return receipt
            self.native_observe=native_observe
            native_observe('startup-before-ready')
            self.check('supported route',route in ('normal','file-close','uncancellable'))
            self.check('owned portable config',Path(settings.get('/app/userConfigPath')).resolve()==self.root/'user.config.json')
            bounds_candidate=settings.get('/exts/in.app.probe/profile') and json.loads((self.root/'shutdown-profile.json').read_text()).get('candidate') in ('viewport-bounds','viewport-bounds-scale','viewport-bounds-stability')
            self.check('review initially disabled' if bounds_candidate else 'review extension never enabled',not app.get_extension_manager().is_extension_enabled('mmporong.scene.review'))
            async def ready():
                from omni.kit.viewport.utility import get_active_viewport,next_viewport_frame_async
                while not app.is_app_ready() or ctx.get_stage() is None or get_active_viewport() is None:
                    await app.next_update_async()
                await next_viewport_frame_async(get_active_viewport())
            await asyncio.wait_for(ready(),120)
            native_observe('startup-after-ready')
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
            native_observe('before-fixture-open')
            opened=await ctx.open_stage_async(str(fixture))
            initial_stage=ctx.get_stage()
            native_observe('fixture-open-returned')
            self.check('owned fixture opened',bool(opened[0]))
            for update in range(20):
                await app.next_update_async()
                if update in (0,1,4,9,19):
                    native_observe('fixture-update-'+str(update+1))
            self.check('only owned fixture active',Path(ctx.get_stage().GetRootLayer().realPath).resolve()==fixture)
            self.check('fixture root is not dirty',not ctx.get_stage().GetRootLayer().dirty)
            self.result['pending_edit_before_quit']=ctx.has_pending_edit()
            self.result['session_dirty_before_quit']=ctx.get_stage().GetSessionLayer().dirty
            self.result['fixture_sha256']=original_hash
            initial_stage=ctx.get_stage()
            early=context_receipt(omni.usd.get_context(),ctx,initial_stage,fixture)
            early['phase']='before-observer-imports'
            self.result.setdefault('close_observations',[]).append(early)
            self.write()
            import importlib
            import omni.ui as ui
            native_observe('after-ui-import')
            import omni.kit.ui_test as ui_test
            native_observe('after-ui-test-import')
            file_impl=importlib.import_module('omni.kit.window.file.file_window')
            native_observe('after-file-implementation-import')
            def observe(phase):
                before_query=context_receipt(omni.usd.get_context(),ctx,initial_stage,fixture)
                file_utility=file_impl._file_util_instance
                prompt=file_utility._unsaved_stage_prompt if file_utility is not None else None
                prompt_title=prompt._title if prompt is not None and prompt.is_visible() else None
                windows=window_receipts(ui.Workspace.get_windows(),ui_test.find_all,prompt_title)
                receipt=close_receipt(omni.usd.get_context(),ctx,initial_stage,fixture,file_impl,windows)
                receipt['before_window_query_pending_edit']=before_query['pending_edit']
                receipt['phase']=phase
                self.result.setdefault('close_observations',[]).append(receipt)
                self.write()
                return receipt
            observe('before-candidate')
            def stage_event(event):
                number=int(event.type)
                self.result.setdefault('raw_stage_events',[]).append(number)
                if number==int(omni.usd.StageEventType.DIRTY_STATE_CHANGED):
                    self.result.setdefault('default_dirty_events',[]).append({
                        'updates_completed':self.result.get('attach_control',{}).get('updates_completed'),
                        'state':context_receipt(ctx,ctx,initial_stage,fixture)})
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
            if profile_name and profile.get('attach_control'):
                self.check('attach control reduced without candidate',profile['variant']=='no-navigation' and not profile.get('candidate'))
                from attach_only_control import evaluate as evaluate_attach
                await evaluate_attach(self,self.root,profile['attach_control'])
            if profile_name and profile.get('candidate'):
                self.check('candidate only on reduced profile',profile['variant']=='no-navigation' and profile['candidate'] in ('viewport-reuse','viewport-bounds','viewport-bounds-scale','viewport-bounds-stability'))
                settings_keys=('/rtx/useViewLightingMode','/rtx/post/tonemap/op','/app/asyncRendering',
                    '/renderer/multiGpu/autoEnable','/app/fastShutdown','/app/settings/persistent')
                before_settings={key:settings.get(key) for key in settings_keys}
                self.result['candidate']={'status':'running','kind':'sequential capture, not live split'}
                self.write()
                if profile['candidate'] in ('viewport-bounds-scale','viewport-bounds-stability'):
                    from viewport_bounds_scale_qa import evaluate
                elif bounds_candidate:
                    from viewport_bounds_candidate import evaluate
                else:
                    from viewport_reuse_candidate import evaluate
                if profile['candidate']=='viewport-bounds-stability':
                    candidate=await evaluate(self,self.root,stability=True)
                else:candidate=await evaluate(self,self.root)
                if profile['candidate'] in ('viewport-bounds-scale','viewport-bounds-stability'):
                    # QA deliberately opens only its own two working files, then
                    # restores the unchanged pinned fixture. Adopt that explicit
                    # setup epoch, never describe setup as product preservation.
                    self.check('QA restored pinned fixture epoch',candidate.get('fixture_epoch_restored') is True and Path(ctx.get_stage().GetRootLayer().realPath).resolve()==fixture)
                    initial_stage=ctx.get_stage()
                if bounds_candidate:self.check('review disabled after candidate',not manager.is_extension_enabled('mmporong.scene.review'))
                observe('after-candidate-cleanup')
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
                before_close=observe('before-public-close')
                self.check('close only unchanged owned stage',before_close['same_context'] and before_close['same_stage'] and before_close['fixture_active'] and not before_close['root_dirty'])
                if before_close['pending_edit'] or before_close['save_prompt_observed']:
                    self.result.update(status='failed',reason='pending edits or save prompt observed; public close not invoked')
                    self.write()
                    return
                def closed():
                    self.result['file_close_callback']=True
                    self.check('public close leaves no stage',ctx.get_stage() is None)
                    app.post_quit(0)
                file_window.close(closed)
                observe('public-close-returned')
            else:
                app.post_quit(0)
            # Observe only. Never select Save/Don't Save or change pending edits.
            for update in range(600):
                await app.next_update_async()
                if update in (0,1,4,19) or (update+1)%60==0:
                    receipt=observe('close-update-'+str(update+1))
                    if receipt['save_prompt_observed']:
                        self.result.update(status='failed',reason='save prompt observed; no dialog action taken')
                        self.write()
                        return
            self.result.update(status='failed',reason='normal shutdown did not finish within 600 updates')
            self.write()
        except Exception as exc:
            self.result.update(status='failed',reason=type(exc).__name__+': '+str(exc))
            self.write()
            # Leave the owned host for launcher timeout/containment on failure;
            # do not substitute another quit API and mislabel the route.
