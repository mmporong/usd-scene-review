"""Small review UI; all stage operations target an extension-owned USD context."""

import asyncio
from functools import partial
import json
from pathlib import Path
from uuid import uuid4

import carb
import omni.ext
import omni.kit.app
from omni.kit.viewport.utility import frame_viewport_prims
from omni.kit.viewport.window import ViewportWindow
import omni.ui as ui
import omni.usd
from pxr import Usd, UsdUtils

from usd_scene_review import compare, load_snapshot
from usd_scene_review.snapshot import verify


# Keep deferred shutdown owners alive after Kit releases the IExt instance.
_CLEANUP_TASKS = set()
_RETAINED_OWNERS = set()


class SceneReviewExtension(omni.ext.IExt):
    """Expose semantic results and a separate, static A/B review viewport."""

    def on_startup(self, ext_id):
        self._context_name = "usd_scene_review_" + uuid4().hex
        self._context = omni.usd.create_context(self._context_name)
        self._viewport = None
        self._snapshot = None
        self._stage_id = None
        self._layer_permissions = []
        self._task = None
        self._cleanup_task = None
        self._shutting_down = False
        self._attachment_pending = False
        self._release_blocked = False
        self._release_error = ""
        self._report = None
        self._selected = None
        self._side = None
        self._paths = {"A": ui.SimpleStringModel(), "B": ui.SimpleStringModel()}
        self._status = ui.SimpleStringModel("Choose two local snapshot manifest files.")
        self._details = ui.SimpleStringModel("No comparison loaded.")
        self._window = ui.Window("USD Scene Review", width=600, height=640)
        self._window.set_style({
            "Window": {"background_color": 0xFFF7F7F7},
            "Label": {"color": 0xFF202020},
            "Button": {"background_color": 0xFFE7E7E7, "color": 0xFF202020},
            "StringField": {"background_color": 0xFFFFFFFF, "color": 0xFF202020},
        })
        with self._window.frame:
            with ui.VStack(spacing=8):
                ui.Label("Local snapshots · semantic revision review", height=24)
                ui.Label("Early implementation. Kit GUI verification is pending.", height=22)
                for side in ("A", "B"):
                    with ui.HStack(height=26):
                        ui.Label(side + " manifest", width=90)
                        ui.StringField(model=self._paths[side])
                with ui.HStack(height=30, spacing=6):
                    ui.Button("Compare", clicked_fn=self._compare)
                    ui.Button("View A", clicked_fn=partial(self._schedule_view, "A"))
                    ui.Button("View B", clicked_fn=partial(self._schedule_view, "B"))
                    ui.Button("Close review", clicked_fn=self._close_review)
                ui.StringField(model=self._status, read_only=True, height=48, multiline=True)
                ui.Label("Changes — choose a row, then switch A/B", height=22)
                with ui.ScrollingFrame(height=210):
                    self._rows = ui.VStack(spacing=3)
                ui.Label("Selected result / comparison details", height=22)
                ui.StringField(model=self._details, read_only=True, multiline=True)

    def _message(self, text):
        if self._window:
            self._status.set_value(text)

    def _compare(self):
        if self._shutting_down:
            return
        if self._release_blocked:
            self._message(self._release_error)
            return
        if self._attachment_pending or (self._task and not self._task.done()):
            self._message("Wait for the current viewport attachment before comparing again.")
            return
        self._task = None
        if not self._release_stage():
            return
        self._report = None
        self._selected = None
        self._side = None
        self._rows.clear()
        try:
            paths = {side: Path(model.as_string).expanduser().resolve()
                     for side, model in self._paths.items()}
            self._report = compare(paths["A"], paths["B"])
            self._comparison_paths = paths
            self._details.set_value(json.dumps(self._report, indent=2, ensure_ascii=False))
            changes = self._report.get("changes", [])
            with self._rows:
                for change in changes:
                    ui.Button(
                        str(change.get("kind", "change")) + "  " + change.get("path", ""),
                        height=24, clicked_fn=partial(self._select, change),
                    )
            self._message(f"{self._report.get('status', 'unknown')} · {len(changes)} changed prims. "
                          "A/B viewport supports static stages only.")
        except Exception as exc:
            self._message("Comparison failed: " + str(exc))
            carb.log_warn("USD Scene Review comparison failed: " + type(exc).__name__)

    def _select(self, change):
        self._selected = change.get("path")
        self._details.set_value(json.dumps(change, indent=2, ensure_ascii=False))
        self._frame_selection()

    def _frame_selection(self):
        if self._release_blocked:
            self._message(self._release_error)
            return
        if self._shutting_down or self._attachment_pending:
            self._message("Wait for viewport attachment before framing.")
            return
        if not self._selected or not self._snapshot or not self._viewport:
            return
        if verify(self._snapshot):
            if self._release_stage():
                self._message("Snapshot changed or source dirty state is invalid. Compare again.")
            return
        prim = self._snapshot.stage.GetPrimAtPath(self._selected)
        if not prim or not prim.IsActive() or not prim.IsLoaded():
            self._message(f"{self._side}: {self._selected} is absent, inactive or unloaded. "
                          "Try the other revision; no original stage was changed.")
            return
        self._context.get_selection().set_selected_prim_paths([self._selected], False)
        framed = frame_viewport_prims(self._viewport.viewport_api, prims=[self._selected])
        self._message(f"{self._side}: " + (f"framed {self._selected}" if framed
                                          else "camera/framing is not available yet."))

    def _schedule_view(self, side):
        if self._shutting_down:
            return
        if self._release_blocked:
            self._message(self._release_error)
            return
        if not self._report:
            self._message("Compare manifests before opening A/B review.")
            return
        if self._attachment_pending or (self._task and not self._task.done()):
            self._message("A viewport switch is in progress; wait before switching again.")
            return
        self._task = asyncio.ensure_future(self._view(side))

    async def _view(self, side):
        if self._shutting_down or self._release_blocked:
            return
        if not self._release_stage():
            return
        try:
            if compare(self._comparison_paths["A"], self._comparison_paths["B"]) != self._report:
                self._message("Inputs changed since comparison. Compare again before viewing.")
                return
            # Reload and validate the bundle at every switch; do not trust stale UI results.
            snapshot = load_snapshot(self._comparison_paths[side])
            if snapshot.stage is None or getattr(snapshot, "errors", []):
                self._message(side + ": snapshot is unknown; viewport was not attached.")
                return
            if any(attr.GetNumTimeSamples() for prim in snapshot.stage.TraverseAll()
                   for attr in prim.GetAttributes()):
                self._message("Animated viewport is unsupported: use the report at the "
                              "declared time. The user's timeline was not changed.")
                return
            # Cameras/viewport navigation may author opinions, but only in this anonymous session.
            session = snapshot.stage.GetSessionLayer()
            if not session.anonymous:
                self._message("Refusing a review stage with a file-backed session layer.")
                return
            snapshot.stage.SetEditTarget(Usd.EditTarget(session))
            self._snapshot = snapshot
            self._side = side
            for layer in snapshot.stage.GetUsedLayers():
                if not layer.anonymous:
                    self._layer_permissions.append((
                        layer, layer.permissionToEdit, layer.permissionToSave, layer.dirty,
                    ))
                    layer.SetPermissionToEdit(False)
                    layer.SetPermissionToSave(False)
            if self._viewport is None:
                self._viewport = ViewportWindow(
                    "USD Scene Review A/B", self._context_name,
                    width=960, height=640, usd_drop_support=False,
                )
            self._stage_id = UsdUtils.StageCache.Get().Insert(snapshot.stage)
            self._attachment_pending = True
            success, error = await self._context.attach_stage_async(snapshot.stage)
            self._attachment_pending = False
            if not success:
                raise RuntimeError("Review stage attachment failed: " + error)
            if self._shutting_down:
                return
            await omni.kit.app.get_app().next_update_async()
            if self._shutting_down:
                return
            if verify(snapshot):
                raise RuntimeError("Snapshot integrity changed during attachment")
            self._message(side + ": static snapshot in a dedicated review viewport.")
            self._frame_selection()
        except asyncio.CancelledError:
            # Cancelling the Python await does not cancel the native Kit attachment.
            # Retain its context and layers if native completion is unknown.
            if self._attachment_pending:
                carb.log_error("USD Scene Review: native attachment completion is unknown; "
                               "owned context retained rather than destroyed.")
            raise
        except Exception as exc:
            if not self._attachment_pending and not self._release_stage():
                return
            self._message("Viewport failed: " + str(exc))
            carb.log_warn("USD Scene Review viewport failed: " + type(exc).__name__)

    def _block_release(self, reason):
        self._release_blocked = True
        self._release_error = ("Review cleanup is unconfirmed: " + reason
                               + " Compare, A/B and Close are blocked. Disable the extension "
                               "to retry owned cleanup; source protections remain retained.")
        carb.log_error("USD Scene Review: " + self._release_error)
        self._message(self._release_error)
        return False

    def _release_stage(self):
        if self._attachment_pending:
            raise RuntimeError("Cannot release a stage before native attachment completion")
        try:
            if self._context and self._context.get_stage():
                if not self._context.close_stage():
                    return self._block_release("stage close returned false.")
                if self._context.get_stage():
                    return self._block_release("context still holds a stage after close.")
        except Exception as exc:
            return self._block_release("stage close raised " + type(exc).__name__ + ".")
        # Ownership and source protections may be released only after confirmed detach.
        if self._stage_id is not None:
            try:
                UsdUtils.StageCache.Get().Erase(self._stage_id)
            except Exception as exc:
                return self._block_release("stage cache cleanup raised " + type(exc).__name__ + ".")
            else:
                self._stage_id = None
        remaining = []
        for layer, editable, saveable, was_dirty in self._layer_permissions:
            try:
                if layer.dirty != was_dirty:
                    carb.log_error("USD Scene Review: source layer dirty state changed; nothing saved.")
                try:
                    layer.SetPermissionToEdit(editable)
                finally:
                    layer.SetPermissionToSave(saveable)
            except Exception as exc:
                remaining.append((layer, editable, saveable, was_dirty))
                carb.log_error("USD Scene Review: source permission restoration failed: "
                               + type(exc).__name__)
        self._layer_permissions = remaining
        if remaining:
            return self._block_release("source permission restoration failed.")
        self._snapshot = None
        self._side = None
        self._release_blocked = False
        self._release_error = ""
        return True

    def _close_review(self):
        if self._shutting_down:
            return
        if self._release_blocked:
            self._message(self._release_error)
            return
        if self._attachment_pending or (self._task and not self._task.done()):
            self._message("Viewport attachment is in progress; close after it completes.")
            return
        self._task = None
        if self._dispose_review():
            self._message("Review viewport closed. Original context was not opened or closed.")

    def _dispose_review(self):
        if not self._release_stage():
            return False
        if self._viewport:
            try:
                self._viewport.destroy()
            except Exception as exc:
                return self._block_release("viewport cleanup raised " + type(exc).__name__ + ".")
            else:
                self._viewport = None
        return True

    def on_shutdown(self):
        if self._shutting_down:
            return
        self._shutting_down = True
        if self._window:
            try:
                self._window.destroy()
            except Exception as exc:
                carb.log_error("USD Scene Review: panel cleanup failed: " + type(exc).__name__)
            finally:
                self._window = None
        if self._viewport:
            try:
                self._viewport.visible = False
            except Exception as exc:
                carb.log_error("USD Scene Review: viewport hide failed: " + type(exc).__name__)
        task = self._task
        if task and not task.done():
            # IExt.on_shutdown is synchronous. Do not cancel the native attach await:
            # wait for it in an owned coroutine, then release only our resources.
            self._cleanup_task = asyncio.ensure_future(self._shutdown_after(task))
            _CLEANUP_TASKS.add(self._cleanup_task)
            self._cleanup_task.add_done_callback(_CLEANUP_TASKS.discard)
            carb.log_warn("USD Scene Review: shutdown cleanup is pending native attachment completion.")
        else:
            self._finish_shutdown()

    async def _shutdown_after(self, task):
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            _RETAINED_OWNERS.add(self)
            carb.log_error("USD Scene Review: deferred shutdown was interrupted; "
                           "cleanup is unconfirmed.")
            return
        except Exception as exc:
            carb.log_error("USD Scene Review: attachment task failed during shutdown: "
                           + type(exc).__name__)
        self._finish_shutdown()

    def _finish_shutdown(self):
        if self._attachment_pending:
            _RETAINED_OWNERS.add(self)
            carb.log_error("USD Scene Review: native attachment completion is unknown; "
                           "context cleanup deferred until process exit.")
            return
        try:
            if not self._dispose_review():
                _RETAINED_OWNERS.add(self)
                return
        except Exception as exc:
            carb.log_error("USD Scene Review: resource cleanup failed: " + type(exc).__name__)
            _RETAINED_OWNERS.add(self)
            return
        if self._context:
            try:
                if omni.usd.destroy_context(self._context_name):
                    self._context = None
                else:
                    carb.log_error("USD Scene Review: context destruction was not confirmed.")
                    _RETAINED_OWNERS.add(self)
                    return
            except Exception as exc:
                carb.log_error("USD Scene Review: context destruction failed: " + type(exc).__name__)
                _RETAINED_OWNERS.add(self)
                return
        self._task = None
        _RETAINED_OWNERS.discard(self)
