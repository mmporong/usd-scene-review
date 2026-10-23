"""A stage-free UI SceneView in the existing default working viewport."""
import weakref
import omni.kit.app
import omni.timeline
import omni.usd
import omni.ui as ui
from omni.ui import scene as sc
from pxr import UsdGeom
from usd_scene_review import load_snapshot
from usd_scene_review.overlay import bounds_plan,overlay_text,validate_report_reference

FRAME_NAME='mmporong.scene.review.snapshot-bounds'


class BoundsOverlay:
    def __init__(self,message):
        self.message=message;self.state='closed';self.frame=None;self.scene_view=None
        self.subscriptions=[];self.snapshots={};self.report=None;self.last_plan=None
        self.window=self.api=self.host=self.stage=self.caption=None
        self.line_count=0;self._matrices=None

    def open(self,paths,report,selected=None,comparison_receipt=None):
        self.close()
        if report.get('status')=='unknown':raise ValueError('Compare complete frozen snapshots before overlay')
        if not omni.timeline.get_timeline_interface().is_stopped():raise ValueError('Bounds overlay requires stopped timeline')
        validate_report_reference(paths,report,comparison_receipt)
        from omni.kit.viewport.utility import get_active_viewport_window
        window=get_active_viewport_window()
        if window is None:raise ValueError('An existing working viewport is required')
        api=window.viewport_api
        if api.usd_context_name!='':raise ValueError('Bounds overlay supports the existing default working viewport only')
        host=api.usd_context;stage=host.get_stage()
        if stage is None:raise ValueError('Working stage is unavailable')
        metadata=report['stage_metadata']
        if (UsdGeom.GetStageMetersPerUnit(stage)!=metadata['meters_per_unit']['before']
                or str(UsdGeom.GetStageUpAxis(stage))!=metadata['up_axis']['before']):
            raise ValueError('Working viewport units/up axis differ from snapshots; no alignment is guessed')
        self.snapshots={side:load_snapshot(paths[side]) for side in ('A','B')}
        self.report=report;self.window=window;self.api=api;self.host=host;self.stage=stage
        try:
            self.frame=window.get_frame(FRAME_NAME)
            self.frame.clear();self.frame.visible=True
            with self.frame:
                with ui.ZStack():
                    self.scene_view=sc.SceneView(aspect_ratio_policy=sc.AspectRatioPolicy.STRETCH,
                                                child_windows_input=False,opaque_for_mouse_events=False)
                    with ui.HStack():
                        ui.Spacer(width=32)
                        with ui.VStack():
                            ui.Spacer(height=32)
                            self.caption=ui.Label('',height=150,word_wrap=True,
                                style={'font_size':14,'color':0xFFFFFFFF,'background_color':0xA0303030})
                            ui.Spacer()
            self.state='open';self.select(selected)
            reference=weakref.ref(self)
            def tick(*unused):
                owner=reference()
                if owner is not None:owner._tick()
            def stage_event(event):
                owner=reference()
                if owner is not None and event.type in (int(omni.usd.StageEventType.OPENING),int(omni.usd.StageEventType.CLOSING)):
                    owner.close('Working stage changed; bounds overlay cleared')
            self.subscriptions=[omni.kit.app.get_app().get_update_event_stream().create_subscription_to_pop(tick,name='USD review bounds camera reader'),
                host.get_stage_event_stream().create_subscription_to_pop(stage_event,name='USD review bounds stage lifetime')]
            self._tick()
        except BaseException:
            self.close();raise

    def _tick(self):
        if self.state!='open':return
        try:
            if (not self.window.visible or self.host.get_stage()!=self.stage
                    or not omni.timeline.get_timeline_interface().is_stopped()):
                self.close('Viewport hidden, stage changed or Play started; bounds overlay cleared');return
            values=tuple(float(value) for matrix in (self.api.view,self.api.projection) for row in matrix for value in row)
            if values!=self._matrices:
                # Copy into our independent UI camera model, never the viewport's
                # shared SceneCameraModel or the source USD camera.
                self.scene_view.model.view=sc.Matrix44(*values[:16])
                self.scene_view.model.projection=sc.Matrix44(*values[16:])
                self._matrices=values
        except (ReferenceError,RuntimeError):
            self.close('Working viewport unavailable; bounds overlay cleared')

    def select(self,path):
        if self.state!='open':return
        try:plan=bounds_plan(self.report,self.snapshots,path)
        except Exception:
            self.scene_view.scene.clear();self.line_count=0;self.last_plan=None
            self.caption.text='Bounds overlay cleared: comparison selection/input unavailable'
            raise
        self.scene_view.scene.clear();self.line_count=0
        with self.scene_view.scene:
            for box in plan['boxes']:
                for index in range(0,len(box['points']),2):
                    sc.Line(box['points'][index],box['points'][index+1],color=box['color'],thickness=2.5)
                    self.line_count+=1
        self.caption.text=overlay_text(plan);self.last_plan=plan

    def close(self,reason=None):
        self.state='closed'
        for subscription in self.subscriptions:subscription.unsubscribe()
        self.subscriptions.clear()
        if self.scene_view is not None:
            self.scene_view.scene.clear();self.scene_view.destroy();self.scene_view=None
        if self.frame is not None:
            # get_frame caches one SDK-owned container per fixed key. Reuse that
            # empty frame on reopen; do not leave destroyed children or callbacks.
            self.frame.clear();self.frame.visible=False;self.frame=None
        self.snapshots.clear();self.report=self.last_plan=None;self.line_count=0;self._matrices=None
        self.window=self.api=self.host=self.stage=self.caption=None
        if reason:self.message(reason)
        return True
