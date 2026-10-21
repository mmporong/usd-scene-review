"""Comparison UI. Native review resources belong only to a separate Kit process."""
import asyncio
from functools import partial
import hashlib
from pathlib import Path
import sys
import weakref

import carb
import omni.ext
import omni.ui as ui

from usd_scene_review import compare
from usd_scene_review.presentation import details, summary, visible_changes
from usd_scene_review.measurements import detail_rows, measurements
from usd_scene_review.dispositions import change_identity, record, history, latest
from usd_scene_review.worker_client import get_viewer_client
from usd_scene_review.exports import save_report
from usd_scene_review.snapshot import canonical
from usd_scene_review.overlap_analysis import pair_rows

_active = None


def get_active_extension():
    return _active() if _active else None


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
        self._selected_change = None
        self._selected_pair = None
        self._review_path = ui.SimpleStringModel()
        self._reason = ui.SimpleStringModel()
        self._disposition = ui.SimpleStringModel('Human review: unreviewed. This does not change independent rule verdicts.')
        self._paths = {s: ui.SimpleStringModel() for s in ('A', 'B')}
        self._query = ui.SimpleStringModel()
        self._inherited = ui.SimpleBoolModel(False)
        self._focus = ui.SimpleBoolModel(False)
        self._ghost = ui.SimpleBoolModel(False)
        self._normalized = ui.SimpleBoolModel(True)
        self._review_event = {}
        self._export_path = ui.SimpleStringModel()
        self._status = ui.SimpleStringModel('Choose two local snapshot manifests. Viewer starts only on View A/B.')
        self._details = ui.SimpleStringModel('No comparison loaded.')
        self._revision = ui.SimpleStringModel('No saved scene attached')
        self._selected_label = ui.SimpleStringModel('Select a changed prim to inspect before / after / delta')
        self._motion = ui.SimpleStringModel('Local deltas use parent coordinates. Bounds are not collision evidence.')
        self._window = ui.Window('USD Scene Review', width=1000, height=900)
        self._window.frame.set_style({
            'Window': {'background_color': 0xFFF8F7F5},
            'Frame': {'background_color': 0xFFF8F7F5},
            'Label': {'color': 0xFF302218, 'font_size': 18},
            'Button': {'background_color': 0xFFECE8E2, 'color': 0xFF302218, 'font_size': 18},
            'Button.Label': {'color': 0xFF302218, 'font_size': 18},
            'Field': {'background_color': 0xFFFFFFFF, 'color': 0xFF302218, 'font_size': 18},
            'StringField': {'background_color': 0xFFFFFFFF, 'color': 0xFF302218, 'font_size': 18},
            'ScrollingFrame': {'background_color': 0xFFF8F7F5},
        })
        with self._window.frame:
            with ui.VStack(spacing=4):
                ui.Label('USD SCENE REVIEW  |  static revision comparison', height=26)
                ui.Label('A = BEFORE saved scene | B = AFTER saved scene. A change may be intentional.', height=24)
                for side in ('A', 'B'):
                    with ui.HStack(height=26):
                        ui.Label(side + ' manifest', width=90)
                        ui.StringField(model=self._paths[side])
                with ui.HStack(height=30, spacing=6):
                    ui.Button('Compare', clicked_fn=self._compare)
                    ui.Button('View A', clicked_fn=partial(self._schedule_view, 'A'))
                    ui.Button('View B', clicked_fn=partial(self._schedule_view, 'B'))
                    ui.Button('Close review', clicked_fn=self._close_review)
                    ui.Button('Save results', clicked_fn=lambda: self._schedule(self._save_results()))
                with ui.HStack(height=26):
                    ui.Label('New output folder', width=150)
                    ui.StringField(model=self._export_path)
                ui.StringField(model=self._status, read_only=True, multiline=True, height=52)
                with ui.HStack(height=26):
                    ui.Label('Path search', width=85)
                    ui.StringField(model=self._query)
                    ui.CheckBox(model=self._inherited, width=20)
                    ui.Label('Inherited motion', width=130)
                with ui.HStack(height=30):
                    ui.Label('BEFORE A | BLUE / dashed bounds', style={'color': 0xFFBC5D0C})
                    ui.Label('AFTER B | ORANGE / solid bounds', style={'color': 0xFF0754C0})
                ui.Label('Original geometry/materials retained. Color marks selected bounds only; not an error verdict.', height=25)
                with ui.HStack(height=24):
                    ui.CheckBox(model=self._focus, width=20)
                    ui.Label('Focus selected (optional; default shows whole saved scene)')
                with ui.HStack(height=24):
                    ui.CheckBox(model=self._ghost, width=20)
                    ui.Label('Show old A: translucent green faces + subtle edges in B',style={'color':0xFF18752D})
                    ui.CheckBox(model=self._normalized, width=20)
                    ui.Label('Fixed preview illumination (on next View A/B)')
                ui.StringField(model=self._revision, read_only=True, height=30)
                with ui.ScrollingFrame(height=90):
                    self._rows = ui.VStack(spacing=3)
                with ui.CollapsableFrame('Static AABB candidates (collision unknown)', collapsed=True) as pair_frame:
                    self._pair_frame = pair_frame
                    with ui.ScrollingFrame(height=100):
                        self._pair_rows = ui.VStack(spacing=3)
                ui.StringField(model=self._selected_label, read_only=True, height=30)
                ui.StringField(model=self._motion, read_only=True, multiline=True, height=52)
                with ui.CollapsableFrame('Human review metadata (separate from evidence)', collapsed=True) as review_frame:
                    self._review_frame = review_frame
                    with ui.VStack(spacing=3):
                        with ui.HStack(height=24):
                            ui.Label('Review log .jsonl', width=150)
                            ui.StringField(model=self._review_path)
                            ui.Button('Reload review', width=140, clicked_fn=self._reload_review)
                        with ui.HStack(height=26):
                            ui.StringField(model=self._reason)
                            ui.Button('Mark intentional', width=160, clicked_fn=partial(self._record_review, 'intentional'))
                            ui.Button('Needs review', width=140, clicked_fn=partial(self._record_review, 'needs-review'))
                        ui.StringField(model=self._disposition, read_only=True, multiline=True, height=40)
                with ui.ScrollingFrame(height=255):
                    self._numeric = ui.VStack(spacing=3)
                ui.Label('Translation: stage units + meters. q: rigid and scale-normalized effective orientation; shortest angle.', height=22,
                         style={'font_size': 16})
                ui.Label('Axis magnitudes are unsigned, not authored signed scale. Values rounded to 9 digits.', height=22,
                         style={'font_size': 16})
                with ui.CollapsableFrame('Raw comparison evidence', collapsed=True):
                    ui.StringField(model=self._details, read_only=True, multiline=True, height=120)
        self._render_numeric(None)
        self._query_callback = self._query.add_value_changed_fn(lambda _: self._render_rows())
        self._focus_callback = self._focus.add_value_changed_fn(
            lambda _: self._schedule(self._frame()) if self._viewer.state == 'running' else None)
        self._ghost_callback = self._ghost.add_value_changed_fn(
            lambda _: self._schedule(self._frame()) if self._viewer.state == 'running' else None)
        self._inherited_callback = self._inherited.add_value_changed_fn(lambda _: self._render_rows())
        global _active
        _active = weakref.ref(self)

    async def _save_results(self):
        if not self._report:
            raise ValueError('Compare snapshots before saving results')
        if not self._export_path.as_string.strip():
            raise ValueError('Enter a new output folder with an existing parent')
        if compare(self._comparison_paths['A'], self._comparison_paths['B'], analysis_config=self._report.get('analysis_config'), policy=self._report.get('policy_config')) != self._report:
            raise ValueError('Inputs changed since comparison; compare again before saving')
        actual = {s: hashlib.sha256(p.read_bytes()).hexdigest() for s, p in self._comparison_paths.items()}
        if actual != self._comparison_hashes:
            raise ValueError('Compared manifests changed; compare again before saving')
        target = save_report(self._report, self._export_path.as_string,
                             forbidden_roots=[p.parent for p in self._comparison_paths.values()])
        self._message('Saved review.json and review.html: ' + str(target))
        return target

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
        self._selected_change = None
        self._selected_pair = None
        self._review_event = {}
        self._disposition.set_value('Human review: no changed prim selected')
        self._render_numeric(None)
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
        self._render_pairs()
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
        self._selected_pair = None
        self._selected = change.get('path')
        self._selected_change = change
        self._reason.set_value('')
        self._load_review()
        self._details.set_value(details(change))
        self._render_numeric(change)
        if self._viewer.state == 'running':
            self._schedule(self._frame())

    def _render_pairs(self):
        self._pair_rows.clear()
        analysis = self._report.get('overlap_analysis', {})
        pairs = sorted(analysis.get('pairs', []), key=lambda p: (p['classification'] != 'newly-introduced-aabb-overlap', p['paths']))
        with self._pair_rows:
            ui.Label(str(len(pairs))+' recorded pairs; coverage '+analysis.get('coverage', {}).get('status', 'unknown')+'; first 100 shown', height=22)
            for pair in pairs[:100]:
                ui.Button(pair['classification']+'  '+' / '.join(pair['paths']), height=24,
                          clicked_fn=partial(self._select_pair, pair))

    def _select_pair(self, pair):
        self._selected = self._selected_change = None
        self._selected_pair = pair
        self._reason.set_value('')
        self._load_review()
        self._selected_label.set_value(' / '.join(pair['paths']))
        self._motion.set_value('AABB candidate only. Both objects framed with A/B union. Collision / clearance UNKNOWN.')
        self._details.set_value(canonical(pair))
        self._numeric.clear()
        with self._numeric:
            for name, value in pair_rows(self._report, pair):
                with ui.HStack(height=26):
                    ui.Label(name, width=220)
                    ui.Label(value, word_wrap=True)
        if self._viewer.state == 'running':
            self._schedule(self._frame())

    def _review_identity(self):
        if not self._report or not (self._selected_change or self._selected_pair):
            raise ValueError('Compare and select a changed prim or AABB pair first')
        actual = {s: hashlib.sha256(p.read_bytes()).hexdigest() for s, p in self._comparison_paths.items()}
        if actual != self._comparison_hashes or compare(self._comparison_paths['A'], self._comparison_paths['B'], analysis_config=self._report.get('analysis_config'), policy=self._report.get('policy_config')) != self._report:
            raise ValueError('Inputs changed; compare again. Prior dispositions do not apply.')
        if {s: hashlib.sha256(p.read_bytes()).hexdigest() for s, p in self._comparison_paths.items()} != actual:
            raise ValueError('Manifests changed during review verification; compare again.')
        selection = self._selected_change or {'path': 'pair:'+self._selected_pair['id'],
                                              'pair': self._selected_pair,
                                              'analysis_config': self._report['analysis_config']}
        return change_identity(self._comparison_hashes, selection)

    def _show_review(self, event):
        self._review_event = {k: event[k] for k in ('disposition', 'reason')} if event else {}
        self._disposition.set_value(('Human-marked ' + event['disposition'] + ': ' + event['reason']
                                    if event else 'Human review: unreviewed for this exact comparison/change')
                                   + '\nIndependent policy/unknown verdicts and observed differences remain unchanged.')

    def _load_review(self):
        try:
            if not self._review_path.as_string.strip() or not (self._selected_change or self._selected_pair):
                self._show_review(None)
                return
            identity = self._review_identity()
            events = history(self._review_path.as_string,
                             forbidden_roots=[p.parent for p in self._comparison_paths.values()])
            self._show_review(latest(events, identity))
        except Exception as exc:
            self._review_event = {}
            self._disposition.set_value('Review not applied: ' + str(exc))

    def _reload_review(self):
        self._load_review()
        if self._viewer.state == 'running':
            self._schedule(self._frame())

    def _record_review(self, disposition):
        try:
            identity = self._review_identity()
            if not self._review_path.as_string.strip():
                raise ValueError('Choose a separate review log .jsonl path first')
            event = record(self._review_path.as_string, identity, disposition, self._reason.as_string,
                           forbidden_roots=[p.parent for p in self._comparison_paths.values()])
            self._show_review(event)
            if self._viewer.state == 'running':
                self._schedule(self._frame())
        except Exception as exc:
            self._disposition.set_value('Review not saved: ' + str(exc))

    def _render_numeric(self, change):
        self._numeric.clear()
        if change is None:
            self._selected_label.set_value('Select a changed prim to inspect before / after / delta')
            return
        data = measurements(self._report, change)
        self._selected_label.set_value(change['path'])
        units = data['units']
        policy = [p for p in self._report.get('policy', []) if p.get('path') == change['path']]
        verdict = ', '.join(p.get('status', 'unknown') for p in policy) if policy else 'not evaluated'
        self._motion.set_value('OBSERVED CHANGE (not a defect verdict); policy: ' + verdict
                               + '\n' + data['motion'] + '; meters / stage unit: A=' + str(units.get('before'))
                               + ', B=' + str(units.get('after')))
        with self._numeric:
            for index, row in enumerate([('OBSERVATION', 'BEFORE A', 'AFTER B', 'DELTA / interpretation')]
                                        + detail_rows(self._report, change)):
                with ui.HStack(height=23, spacing=4):
                    for column, (text, width) in enumerate(zip(row, (215, 220, 220, 325))):
                        color = 0xFFBC5D0C if column == 1 else 0xFF0754C0 if column == 2 else 0xFF302218
                        ui.Label(text, width=width, word_wrap=True,
                                 style={'color': color, 'font_size': 17 if index else 18})

    async def _frame(self):
        reply = await self._viewer.frame(self._selected, focus=self._focus.as_bool,
                                         ghost=self._ghost.as_bool, review=self._review_event,
                                         pair_id=self._selected_pair['id'] if self._selected_pair else None)
        self._accept_reply(reply)

    def _accept_reply(self, reply):
        if reply.get('status') == 'error':
            raise RuntimeError(reply.get('message', 'Viewer failed'))
        self._message(reply.get('message', reply.get('status', 'unknown')))
        if reply.get('side') in ('A', 'B'):
            self._revision.set_value('ACTUAL VIEW: ' + ('BEFORE saved scene A | BLUE dashed bounds' if reply['side'] == 'A'
                                                       else 'AFTER saved scene B | ORANGE solid bounds'))

    def _schedule_view(self, side):
        self._schedule(self._view(side))

    async def _view(self, side):
        if not self._report:
            self._message('Compare manifests before opening A/B review.')
            return
        if self._report.get('status') == 'unknown':
            self._message('Incomplete comparison: inspect the reasons and repair or recreate the snapshot bundles.')
            return
        if compare(self._comparison_paths['A'], self._comparison_paths['B'], analysis_config=self._report.get('analysis_config'), policy=self._report.get('policy_config')) != self._report:
            self._message('Inputs changed since comparison. Compare again.')
            return
        worker = Path(__file__).resolve().parents[3] / 'worker'
        reply = await self._viewer.view(self._comparison_paths, side, self._selected,
                                        sdk=installed_sdk(), worker_module=worker,
                                        expected_hashes=self._comparison_hashes, focus=self._focus.as_bool,
                                        ghost=self._ghost.as_bool, normalized=self._normalized.as_bool,
                                        review=self._review_event, analysis_config=self._report.get('analysis_config'),
                                        policy=self._report.get('policy_config'),
                                          pair_id=self._selected_pair['id'] if self._selected_pair else None,
                                        expected_report_hash=hashlib.sha256(canonical(self._report).encode('utf-8')).hexdigest())
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
        global _active
        if get_active_extension() is self:
            _active = None
        self._shutting_down = True
        self._query.remove_value_changed_fn(self._query_callback)
        self._inherited.remove_value_changed_fn(self._inherited_callback)
        self._focus.remove_value_changed_fn(self._focus_callback)
        self._ghost.remove_value_changed_fn(self._ghost_callback)
        self._rows.clear()
        self._rows = None
        self._pair_rows.clear()
        self._pair_rows = None
        self._pair_frame = None
        self._numeric.clear()
        self._numeric = None
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
