"""Comparison UI. Native review resources belong only to a separate Kit process."""
import asyncio
from functools import partial
import hashlib
from pathlib import Path
import sys

import carb
import omni.ext
import omni.ui as ui

from usd_scene_review import compare
from usd_scene_review.presentation import details, summary, visible_changes
from usd_scene_review.worker_client import get_viewer_client


def installed_sdk():
    import carb.tokens
    candidates = [Path(carb.tokens.get_tokens_interface().resolve('${kit}')).parent,
                  Path(sys.executable).resolve().parent.parent]
    for root in candidates:
        if (root / 'kit/kit.exe').is_file() and (root / 'extscache').is_dir():
            return root
    raise RuntimeError('Existing Windows Isaac Sim SDK not found; inspect docs/support.md')


class SceneReviewExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        self._viewer = get_viewer_client()
        self._task = None
        self._shutting_down = False
        self._report = None
        self._selected = None
        self._paths = {s: ui.SimpleStringModel() for s in ('A', 'B')}
        self._query = ui.SimpleStringModel()
        self._inherited = ui.SimpleBoolModel(False)
        self._status = ui.SimpleStringModel('Choose two local snapshot manifests. Viewer starts only on View A/B.')
        self._details = ui.SimpleStringModel('No comparison loaded.')
        self._window = ui.Window('USD Scene Review', width=680, height=720)
        with self._window.frame:
            with ui.VStack(spacing=6):
                ui.Label('Local snapshots: semantic revision review', height=24)
                ui.Label('Experimental. Static viewer requires existing Windows Isaac Sim 4.5.', height=24)
                for side in ('A', 'B'):
                    with ui.HStack(height=26):
                        ui.Label(side + ' manifest', width=90)
                        ui.StringField(model=self._paths[side])
                with ui.HStack(height=30, spacing=6):
                    ui.Button('Compare', clicked_fn=self._compare)
                    ui.Button('View A', clicked_fn=partial(self._schedule_view, 'A'))
                    ui.Button('View B', clicked_fn=partial(self._schedule_view, 'B'))
                    ui.Button('Close review', clicked_fn=self._close_review)
                ui.StringField(model=self._status, read_only=True, multiline=True, height=52)
                with ui.HStack(height=26):
                    ui.Label('Path search', width=85)
                    ui.StringField(model=self._query)
                    ui.CheckBox(model=self._inherited, width=20)
                    ui.Label('Inherited motion', width=130)
                with ui.ScrollingFrame(height=220):
                    self._rows = ui.VStack(spacing=3)
                ui.StringField(model=self._details, read_only=True, multiline=True)
        self._query_callback = self._query.add_value_changed_fn(lambda _: self._render_rows())
        self._inherited_callback = self._inherited.add_value_changed_fn(lambda _: self._render_rows())

    def _message(self, text):
        if self._window:
            self._status.set_value(text)

    def _schedule(self, operation):
        if self._shutting_down or (self._task and not self._task.done()):
            operation.close()
            self._message('Wait for the current viewer operation to complete.')
            return
        self._task = asyncio.ensure_future(self._run(operation))

    async def _run(self, operation):
        try:
            await operation
        except Exception as exc:
            self._message(type(exc).__name__ + ': ' + str(exc)
                          + ' Close review to acknowledge a stopped failed worker, then retry.')
            carb.log_warn('USD Scene Review operation failed: ' + type(exc).__name__)

    def _compare(self):
        self._schedule(self._compare_async())

    async def _compare_async(self):
        if not await self._viewer.close():
            self._message('Viewer cleanup unconfirmed. Close review before comparing again.')
            return
        self._report = None
        self._selected = None
        self._rows.clear()
        paths = {s: Path(model.as_string).expanduser().resolve() for s, model in self._paths.items()}
        hashes = {s: hashlib.sha256(p.read_bytes()).hexdigest() for s, p in paths.items()}
        report = compare(paths['A'], paths['B'])
        if hashes != {s: hashlib.sha256(p.read_bytes()).hexdigest() for s, p in paths.items()}:
            raise RuntimeError('Manifests changed during comparison; recreate frozen bundles')
        self._report = report
        self._comparison_paths = paths
        self._comparison_hashes = hashes
        self._details.set_value(summary(self._report))
        self._render_rows()
        self._message(summary(self._report).splitlines()[0])

    def _render_rows(self):
        if not self._report or not self._window:
            return
        changes = visible_changes(self._report, self._query.as_string, self._inherited.as_bool)
        groups = {g['parent']: len(g['affected']) for g in self._report.get('parent_groups', [])}
        self._rows.clear()
        with self._rows:
            ui.Label(f'{len(changes)} visible / {len(self._report.get("changes", []))} total', height=22)
            for change in changes:
                suffix = f' (+{groups[change["path"]]} descendants)' if change['path'] in groups else ''
                ui.Button(change.get('kind', 'change') + '  ' + change['path'] + suffix,
                          height=24, clicked_fn=partial(self._select, change))

    def _select(self, change):
        self._selected = change.get('path')
        self._details.set_value(details(change))
        if self._viewer.state == 'running':
            self._schedule(self._frame())

    async def _frame(self):
        reply = await self._viewer.frame(self._selected)
        self._accept_reply(reply)

    def _accept_reply(self, reply):
        if reply.get('status') == 'error':
            raise RuntimeError(reply.get('message', 'Viewer failed'))
        self._message(reply.get('message', reply.get('status', 'unknown')))

    def _schedule_view(self, side):
        self._schedule(self._view(side))

    async def _view(self, side):
        if not self._report:
            self._message('Compare manifests before opening A/B review.')
            return
        if self._report.get('status') == 'unknown':
            self._message('Incomplete comparison: inspect the reasons and repair or recreate the snapshot bundles.')
            return
        if compare(self._comparison_paths['A'], self._comparison_paths['B']) != self._report:
            self._message('Inputs changed since comparison. Compare again.')
            return
        worker = Path(__file__).resolve().parents[3] / 'worker'
        reply = await self._viewer.view(self._comparison_paths, side, self._selected,
                                        sdk=installed_sdk(), worker_module=worker,
                                        expected_hashes=self._comparison_hashes)
        self._accept_reply(reply)

    def _close_review(self):
        self._schedule(self._close())

    async def _close(self):
        if self._viewer.state == 'closed' and self._viewer.process is None:
            self._message('Review viewer is already closed.')
        elif self._viewer.state == 'failed' and self._viewer.process is None:
            self._viewer.acknowledge_failure()
            self._message('Failed worker stopped; private diagnostic files retained. Retry View A/B.')
        elif await self._viewer.close():
            self._message('Review closed: graceful receipt and worker exit 0 confirmed.')
        else:
            self._message('Review cleanup failed: ' + self._viewer.error)

    def on_shutdown(self):
        self._shutting_down = True
        self._query.remove_value_changed_fn(self._query_callback)
        self._inherited.remove_value_changed_fn(self._inherited_callback)
        self._rows.clear()
        self._rows = None
        if self._window:
            self._window.destroy()
            self._window = None
        # Kit can stop advancing asyncio during app shutdown. The child runs its
        # own loop, so bounded synchronous IPC confirms its normal exit first.
        if not self._viewer.shutdown_sync():
            carb.log_error('USD Scene Review shutdown failed: ' + self._viewer.error)
        # Native work is entirely in the child and now closed or contained. Do
        # not let stale host waiters mutate the durable manager after reload.
        if self._task and not self._task.done():
            self._task.cancel()
