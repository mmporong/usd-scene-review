"""Same-process, read-only A/B review. Only owned snapshot contexts are edited."""
import asyncio
import builtins
import gc
import hashlib
from types import SimpleNamespace
from uuid import uuid4
import carb.settings
import omni.kit.app
import omni.ui as ui
from omni.ui import scene as sc
import omni.usd
import omni.timeline
from omni.kit.widget.viewport import ViewportWidget
from omni.kit.manipulator.camera import ViewportCameraManipulator
from pxr import Usd, UsdUtils
from usd_scene_review import compare, load_snapshot
from usd_scene_review.snapshot import canonical, verify
from usd_scene_review.display import ReviewDisplay
from usd_scene_review.ghost import GhostOverlay, extract
from usd_scene_review.preview import prepare_lighting
from usd_scene_review.evidence import evidence_rows
from usd_scene_review.in_app_logic import focus_plan, copy_review_camera, pair_light_mode
from usd_scene_review.overlap_analysis import pair_by_id, pair_rows

# Retain uncertain native ownership across extension disable/reload. A failed
# destructor must never disappear merely because a new Python module is loaded.
if not hasattr(builtins, '_usd_scene_review_in_app_owners'):
    builtins._usd_scene_review_in_app_owners=[]
_OWNERS=builtins._usd_scene_review_in_app_owners
_RENDER_SETTINGS={'/rtx/post/histogram/enabled':False,'/rtx/post/tonemap/filmIso':100.0,
                  '/rtx/post/tonemap/exposureTime':.02,'/rtx/post/tonemap/fNumber':5.0,
                  '/rtx/post/tonemap/op':6,'/rtx/ecoMode/enabled':False,
                  '/rtx/raytracing/fractionalCutoutOpacity':True}


def retained_review():
    return next((owner for owner in _OWNERS if owner.state!='closed'),None)


def full_host_blocked():
    app=omni.kit.app.get_app()
    filename=app.get_app_filename().replace('\\','/').rsplit('/',1)[-1].lower()
    # Experience identity is also an enabled extension. Do not rely on the
    # filename including its suffix, or on a derived app retaining that filename.
    return (filename in ('isaacsim.exp.full','isaacsim.exp.full.kit')
            or app.get_extension_manager().is_extension_enabled('isaacsim.exp.full'))


class InAppReview:
    def __init__(self, message, on_select=None, ghost_model=None):
        if any(owner.state!='closed' for owner in _OWNERS):
            raise RuntimeError('Existing in-app native ownership is unconfirmed; close it before reopening')
        self.message=message;self.state='closed';self.resources={};self.permissions={}
        self.on_select=on_select;self.external_ghost_model=ghost_model
        self.window=None;self.subscriptions=[];self.layout=None;self.settings_before={}
        self._syncing=False;self._closing_requested=False;self._attach_pending=False
        self._drain_pending=False
        self._drain_task=None
        self.last_close=None;self.selected=None;self.display_info={}
        self._settings_restore=None
        self._close_task=None

    def invalidate(self, reason):
        if self.state in ('closed','failed'):return
        self._closing_requested=True
        if self.window:self.window.visible=False
        self.message(reason+'; review hidden and closing')
        if not self._attach_pending and (self._close_task is None or self._close_task.done()):
            # Never destroy UsdContexts inside a stage/timeline event callback.
            self._close_task=asyncio.ensure_future(self.close())

    async def open(self, paths, report):
        if self.state!='closed':raise RuntimeError('Close the existing in-app review first')
        if not omni.kit.app.get_app().is_app_ready():
            raise RuntimeError('Isaac app startup is not complete; wait before opening review')
        if full_host_blocked():
            raise RuntimeError('Full Isaac 4.5 in-app A/B remains blocked until the corrected Hydra lifecycle passes full feature acceptance; Compare/export and the legacy worker remain available')
        await self._await_host_frame()
        timeline=omni.timeline.get_timeline_interface()
        if not timeline.is_stopped():raise ValueError('In-app review requires stopped timeline; Play is not controlled by this tool')
        self.state='opening';self.paths=dict(paths);self.report=report
        self.report_hash=hashlib.sha256(canonical(report).encode()).hexdigest()
        if compare(paths['A'],paths['B'],analysis_config=report['analysis_config'],policy=report['policy_config'])!=report:
            self.state='closed';raise ValueError('Inputs changed; compare again')
        self.host=omni.usd.get_context();self.host_stage=self.host.get_stage()
        self.layout=ui.Workspace.dump_workspace()
        settings=carb.settings.get_settings()
        # Attaching a named context can itself load renderer defaults. Capture
        # the working app's values before the first native attachment.
        self.settings_before={key:(settings.get(key),value) for key,value in _RENDER_SETTINGS.items()}
        self._closing_requested=False
        _OWNERS.append(self)
        self.host_events=self.host.get_stage_event_stream().create_subscription_to_pop(self._host_event,name='Review working-stage lifetime')
        self.timeline_events=timeline.get_timeline_event_stream().create_subscription_to_pop(self._timeline_event,name='Review stops before playback')
        try:
            self.snapshots={s:load_snapshot(p) for s,p in paths.items()}
            host_layers={l.identifier for l in self.host_stage.GetUsedLayers()} if self.host_stage else set()
            for snapshot in self.snapshots.values():
                if snapshot.errors or verify(snapshot):raise ValueError('Verified static snapshot required')
                if any(a.GetNumTimeSamples() for p in snapshot.stage.TraverseAll() for a in p.GetAttributes()):
                    raise ValueError('Animated review is unsupported; no timeline changes were made')
                for layer in snapshot.stage.GetUsedLayers():
                    if not layer.anonymous:
                        if layer.identifier in host_layers:raise ValueError('Snapshot shares source layers with working stage; use independent frozen bundles')
                        self.permissions.setdefault(layer.identifier,(layer,layer.permissionToEdit,layer.permissionToSave,layer.dirty))
            self.initial_plan=focus_plan(report,self.snapshots)
            self.light_mode=pair_light_mode(self.snapshots)
            for side,snapshot in self.snapshots.items():
                name='usd_review_in_app_'+uuid4().hex
                ctx=omni.usd.create_context(name)
                own_timeline=omni.timeline.get_timeline_interface(name);ctx.set_timeline(name)
                stage=snapshot.stage;stage.SetEditTarget(stage.GetSessionLayer())
                item=dict(name=name,ctx=ctx,timeline=own_timeline,stage=stage,
                          cache_id=UsdUtils.StageCache.Get().Insert(stage))
                self.resources[side]=item
                ok,error=await self._attach(item)
                if not ok:raise RuntimeError('Owned review attachment failed: '+error)
                stage.SetEditTarget(stage.GetSessionLayer())
                for layer,_,_,dirty in self.permissions.values():
                    if layer.dirty!=dirty:raise RuntimeError('Source dirty state changed during attachment')
                    layer.SetPermissionToEdit(False);layer.SetPermissionToSave(False)
                if not self._opening_current():
                    self._closing_requested=True
                if self._closing_requested:
                    self.close_sync();return
                if self.light_mode['fallback_both']:prepare_lighting(stage,normalized=False)
                item['display']=ReviewDisplay(stage)
                item['ghost']=GhostOverlay(stage,item['display'].root,persistent_material=True)
                item['display'].set_camera(self.initial_plan['camera'],SimpleNamespace(camera_path=None))
            # Temporary shared comparison exposure; never modifies source light/camera opinions.
            self._configure_renderer()
            self.window=ui.Window('USD Scene Review A/B',width=1600,height=900)
            self.labels={s:ui.SimpleStringModel(s) for s in ('A','B')}
            self.ghost_model=self.external_ghost_model or ui.SimpleBoolModel(False)
            with self.window.frame:
                with ui.VStack(spacing=4):
                    with ui.HStack(height=28):
                        ui.Label('READ-ONLY / PRE-PLAY | synchronized review cameras | source lights retained')
                        ui.CheckBox(model=self.ghost_model,width=20)
                        ui.Label('Old A green faces in B',width=220)
                        ui.Button('Close comparison',width=180,clicked_fn=lambda:self.invalidate('Closed by user'))
                    with ui.HStack(spacing=6):
                        for side,item in self.resources.items():
                            with ui.VStack():
                                ui.StringField(model=self.labels[side],read_only=True,height=30)
                                item['viewport_frame']=ui.Frame()
                        with ui.VStack(width=350):
                            ui.Label('Observed changes / not intent or collision verdict',height=40,word_wrap=True)
                            ui.Label(self.light_mode['label']+'; matched temporary exposure',height=55,word_wrap=True)
                            with ui.ScrollingFrame(height=160):
                                with ui.VStack():
                                    for change in report['changes']:
                                        ui.Button(change['kind']+' '+change['path'],height=25,
                                            clicked_fn=lambda c=change:self.on_select(c) if self.on_select else self.select(c['path']))
                            with ui.ScrollingFrame():self.evidence=ui.VStack(spacing=4)
            # SDK engine attachment is asynchronous. Bind A completely before
            # constructing B; a requested renderer name is not a bound engine.
            for side,item in self.resources.items():
                self._attach_pending=True
                with item['viewport_frame']:
                    with ui.ZStack():
                        item['widget']=ViewportWidget(usd_context_name=item['name'],
                            camera_path=str(item['display'].root.AppendChild('Camera')),resolution=(600,600))
                        item['scene_view']=sc.SceneView()
                        item['scene_view'].child_windows_input=False
                        item['widget'].viewport_api.add_scene_view(item['scene_view'])
                        with item['scene_view'].scene:
                            item['camera_manipulator']=ViewportCameraManipulator(item['widget'].viewport_api)
                await asyncio.wait_for(self._native_wait(item,item['widget'].viewport_api.wait_for_rendered_frames(8)),30)
                if not self._opening_current():self._closing_requested=True
                if self._closing_requested:
                    await self.close();return
            from omni.kit.viewport.utility import get_active_viewport_window
            active=get_active_viewport_window()
            if active and active.title!=self.window.title:
                self.window.deferred_dock_in(active.title,ui.DockPolicy.CURRENT_WINDOW_IS_ACTIVE)
            for side,item in self.resources.items():
                self.subscriptions.append(item['widget'].viewport_api.subscribe_to_view_change(lambda api,s=side:self.sync_camera(s)))
            self._ghost_callback=self.ghost_model.add_value_changed_fn(lambda _:self.select(self.selected,ghost=self.ghost_model.as_bool,pair_id=getattr(self,'pair_id',None)))
            self.window.set_visibility_changed_fn(lambda visible:self.invalidate('Comparison window hidden') if not visible else None)
            self.state='open';self.select(None)
            self.message('In-app A/B opened; working stage preserved; no worker process')
        except BaseException:
            if not self._attach_pending:self.close_sync()
            else:
                self._closing_requested=True
                if self.window:self.window.visible=False
            raise

    def _opening_current(self):
        return omni.timeline.get_timeline_interface().is_stopped() and self.host.get_stage()==self.host_stage

    async def _await_host_frame(self):
        app=omni.kit.app.get_app()
        if app.get_extension_manager().is_extension_enabled('isaacsim.app.setup'):
            # Match the installed Isaac setup's first-frame readiness barrier.
            from omni.kit.viewport.utility import get_active_viewport,next_viewport_frame_async
            viewport=get_active_viewport()
            if viewport is None:raise RuntimeError('Working viewport is not ready')
            await asyncio.wait_for(next_viewport_frame_async(viewport),30)
            await app.next_update_async()

    def _configure_renderer(self):
        settings=carb.settings.get_settings()
        for key,value in _RENDER_SETTINGS.items():
            before=self.settings_before[key][0]
            settings.set(key,value)
            # Carb may store float32 (e.g. .02 -> .01999999955). Compare
            # with the canonical value actually written, not Python's.
            self.settings_before[key]=(before,settings.get(key))

    @staticmethod
    def _same_setting(current,ours):
        # Renderer subscribers may canonicalize to float32 on a later frame.
        if (not isinstance(current,bool) and not isinstance(ours,bool)
                and isinstance(current,(int,float)) and isinstance(ours,(int,float))):
            return abs(current-ours)<=max(1e-10,abs(ours)*1e-7)
        return current==ours

    async def _attach(self,item):
        return await self._native_wait(item,item['ctx'].attach_stage_async(item['stage']))

    async def _native_wait(self,item,operation):
        self._attach_pending=True
        task=item['attach_task']=asyncio.ensure_future(operation)
        try:
            result=await asyncio.shield(task)
        except BaseException:
            self._closing_requested=True
            task.add_done_callback(self._attachment_finished)
            raise
        item.pop('attach_task');self._attach_pending=False
        return result

    def _attachment_finished(self, task):
        # Cancellation/exception of the native wrapper is not proof of detach.
        if task.cancelled() or task.exception() is not None:
            self.message('Native operation outcome unconfirmed; context retained until host exit')
            return
        for item in self.resources.values():
            if item.get('attach_task') is task:item.pop('attach_task')
        self._attach_pending=False
        self.invalidate('Interrupted native operation completed')

    def _host_event(self,event):
        if event.type in (int(omni.usd.StageEventType.CLOSING),int(omni.usd.StageEventType.OPENED)):
            self.invalidate('Working stage changed')

    def _timeline_event(self,event):
        if event.type==int(omni.timeline.TimelineEventType.PLAY):self.invalidate('Playback started')

    def check_current(self):
        if not omni.timeline.get_timeline_interface().is_stopped():
            self.invalidate('Playback started');raise RuntimeError('Review requires stopped timeline')
        if self.host.get_stage()!=self.host_stage:
            self.invalidate('Working stage changed');raise RuntimeError('Review no longer matches working-stage lifetime')
        if any(verify(s) for s in self.snapshots.values()):
            self.invalidate('Snapshot integrity changed');raise RuntimeError('Frozen inputs changed')
        for layer,_,_,dirty in self.permissions.values():
            if layer.dirty!=dirty or layer.permissionToEdit or layer.permissionToSave:
                raise RuntimeError('Read-only source protection changed')

    def sync_camera(self,side):
        if self.state!='open' or self._syncing:return
        self._syncing=True
        try:
            other='B' if side=='A' else 'A'
            a,b=self.resources[side],self.resources[other]
            copy_review_camera(a['stage'],str(a['display'].root.AppendChild('Camera')),
                               b['stage'],str(b['display'].root.AppendChild('Camera')),
                               (str(a['display'].root),str(b['display'].root)))
        finally:self._syncing=False

    def select(self,selected,*,ghost=None,pair_id=None):
        if self.state!='open':return
        self.check_current();self.selected=selected;self.pair_id=pair_id
        plan=self.initial_plan if selected is None and pair_id is None else focus_plan(self.report,self.snapshots,selected,pair_id)
        self._syncing=True
        try:
            for side,item in self.resources.items():
                item['ghost'].clear()
                item['display'].set_camera(plan['camera'],item['widget'].viewport_api)
                if pair_id:
                    item['display'].style_pair(pair_by_id(self.report,pair_id),side)
                else:item['display'].style(selected,side,plan['bounds'][side])
                present=[p for p in plan['paths'] if plan['exists'][side][p]]
                # Owned geometry cues distinguish A/B; native selection outlines
                # would paint both revisions orange and obscure that distinction.
                self.labels[side].set_value(side+(' BEFORE' if side=='A' else ' AFTER')+' | '+
                                           (', '.join(present) if present else 'Absent in this revision' if selected else 'Whole saved scene'))
            show=self.ghost_model.as_bool if ghost is None else ghost
            ghost_info={'status':'off','count':0}
            if show and selected:
                ghost_info=self.resources['B']['ghost'].show(extract(self.snapshots['A'],selected))
            self.display_info=dict(plan=plan,ghost=ghost_info,report_sha256=self.report_hash)
            change=next((c for c in self.report['changes'] if c['path']==selected),None)
            rows=pair_rows(self.report,pair_by_id(self.report,pair_id)) if pair_id else evidence_rows(self.report,change)
            self.evidence.clear()
            with self.evidence:
                for name,value in rows:
                    ui.Label(name,height=18,style={'font_size':14})
                    ui.Label(value,height=max(24,min(80,20*((len(value)//42)+1))),word_wrap=True)
                ui.Label('Ghost: '+ghost_info['status']+'; green faces opacity 0.22',height=40,word_wrap=True)
        finally:self._syncing=False

    async def close(self):
        if self.state=='closed':return True
        if self._attach_pending or self._drain_pending:
            self._closing_requested=True;return False
        # Drain scene changes while Hydra is still connected, before destroying
        # widgets/engines. Synchronous app shutdown uses the bounded fallback.
        self._closing_requested=True;self.state='closing'
        for item in self.resources.values():
            if item.get('ghost'):item['ghost'].clear()
        try:
            # UI updates alone do not prove Hydra consumed the removed helpers.
            waits=[item['widget'].viewport_api.wait_for_rendered_frames(64)
                   for item in self.resources.values() if item.get('widget')]
            if waits:
                self._drain_pending=True
                self._drain_task=asyncio.gather(*waits)
                await asyncio.wait_for(asyncio.shield(self._drain_task),timeout=10)
                self._drain_pending=False
                self._drain_task=None
        except BaseException as exc:
            self.state='failed';self.last_close={'preserved':False,'reason':'Review render drain unconfirmed'}
            if self._drain_task:
                self._drain_task.add_done_callback(self._drain_finished)
            self.message('Render drain unconfirmed; owned contexts retained: '+type(exc).__name__)
            if isinstance(exc,asyncio.CancelledError):raise
            return False
        return self.close_sync()

    def _drain_finished(self,task):
        # A cancelled Python caller is not a cancelled native render operation.
        # Release only once the shielded operation actually confirms completion.
        if task.cancelled() or task.exception() is not None:return
        self._drain_pending=False;self._drain_task=None
        self.close_sync()

    def _destroy_views(self):
        for sub in list(self.subscriptions):
            if hasattr(sub,'destroy'):sub.destroy()
            self.subscriptions.remove(sub)
        if hasattr(self,'ghost_model') and hasattr(self,'_ghost_callback'):
            self.ghost_model.remove_value_changed_fn(self._ghost_callback)
            del self._ghost_callback
        for item in self.resources.values():
            if item.get('camera_manipulator'):
                item['camera_manipulator'].destroy();item.pop('camera_manipulator')
            if item.get('scene_view'):
                scene=item['scene_view']
                if item.get('widget') and not item.get('scene_removed'):
                    item['widget'].viewport_api.remove_scene_view(scene);item['scene_removed']=True
                scene.scene.clear();scene.destroy();item.pop('scene_view');scene=None
            if item.get('widget'):
                widget=item['widget'];widget.viewport_api.updates_enabled=False
                widget.destroy();item.pop('widget');widget=None
        if self.window:
            self.window.set_visibility_changed_fn(None);self.window.frame.clear();self.window.destroy();self.window=None
        for item in self.resources.values():item.pop('viewport_frame',None)
        if hasattr(self,'evidence'):self.evidence=None

    def close_sync(self):
        if self.state=='closed':return True
        # Disable/reload can arrive while native attachment or drain is pending.
        # Quiesce UI entry points even when native ownership must be retained.
        self._closing_requested=True
        self.on_select=None
        self.state='closing'
        if self._attach_pending or self._drain_pending:
            return False
        self.state='closing';self.host_events=self.timeline_events=None
        try:
            settings=carb.settings.get_settings()
            if self._settings_restore is None:
                self._settings_restore={key:(before if self._same_setting(settings.get(key),ours) else settings.get(key))
                                        for key,(before,ours) in self.settings_before.items()}
            self._destroy_views()
            for item in self.resources.values():
                if not item.get('detached'):
                    ctx=item['ctx']
                    if ctx.get_stage() and (not ctx.close_stage() or ctx.get_stage()):
                        raise RuntimeError('Owned stage close unconfirmed; context retained')
                    omni.usd.release_all_hydra_engines(ctx)
                    UsdUtils.StageCache.Get().Erase(item['cache_id'])
                    item['detached']=True
                    for key in ('ctx','timeline','stage','display','ghost','cache_id'):item.pop(key,None)
            ctx=item=None;self.snapshots={};gc.collect()
            for item in self.resources.values():
                name=item['name']
                if not item.get('context_destroyed'):
                    if not omni.usd.destroy_context(name):raise RuntimeError('Owned context destruction unconfirmed: '+name)
                    item['context_destroyed']=True
                if not item.get('timeline_destroyed'):
                    if not omni.timeline.destroy_timeline(name):raise RuntimeError('Owned timeline destruction unconfirmed: '+name)
                    item['timeline_destroyed']=True
            for layer,editable,saveable,dirty in self.permissions.values():
                if layer.dirty!=dirty:raise RuntimeError('Source dirty state changed; nothing saved')
                layer.SetPermissionToEdit(editable);layer.SetPermissionToSave(saveable)
            self.permissions.clear()
            for key,target in self._settings_restore.items():
                # Native context close may reset renderer values. Eligibility
                # is measured before teardown, while external edits are visible.
                if target is None:settings.destroy_item(key)
                else:settings.set(key,target)
            self.settings_before.clear()
            self._settings_restore=None
            if self.layout:ui.Workspace.restore_workspace(self.layout,keep_windows_open=True)
            self.layout=None;self.host=self.host_stage=None
            self.last_close={'preserved':True,'contexts_destroyed':True}
            self.resources.clear();self.state='closed'
            if self in _OWNERS:_OWNERS.remove(self)
            return True
        except Exception as exc:
            self.state='failed';self.last_close={'preserved':False,'reason':str(exc)}
            self.message('In-app cleanup unconfirmed: '+str(exc));return False
