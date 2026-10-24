# SDK shutdown error signature audit

This audit reads existing private logs only; it does not launch GPU work, suppress
errors, patch the SDK or change qualification. It reconciles every error line in
the no-project navigation-excluded baseline, triangle-face run and polygon run.

| Signature/component | No project | Triangle faces | Polygon faces | Polygon minus triangle |
| --- | ---: | ---: | ---: | ---: |
| XRDF editor `GetPrimAtPath` exception + shutdown wrapper | 2 | 2 | 2 | 0 |
| PhysX sensor UI `_menu_button1` exception + wrapper | 2 | 2 | 2 | 0 |
| Manipulator `ManipulatorFactory` NameError + wrapper | 2 | 2 | 2 | 0 |
| Semantics editor missing `_window` menu callback | 13 | 2 | 10 | +8 |
| File menu missing `get_stage_state` | 3 | 0 | 4 | +4 |
| Edit menu missing `get_selection` | 60 | 0 | 80 | +80 |
| **Error lines, including repeated/wrapper lines** | **82** | **8** | **100** | **+92** |

There are no new polygon exception signatures, no unclassified error lines and
no observed project Python traceback frames. The three exceptions and their
wrappers occur once each in all three runs. All extra 92 lines are repetitions of
SDK menu signatures already present without the review extension. The edit-menu
group covers 20 named entries, each logged four times in the polygon run and three
times in baseline. This is not 100 distinct defects or a comparison of error rates.

## Timing and stack evidence

Times below are process-relative log timestamps, not a synchronized external
clock. stdout/stderr buffering limits fine-grained ordering; the gaps establish
the lifecycle phase rather than exact callback latency.

| Marker/range (seconds) | No project | Triangle faces | Polygon faces |
| --- | ---: | ---: | ---: |
| Review extension shutdown | never loaded | 31.734 | 38.135 |
| First non-project extension shutdown | 25.600 | 33.285 | 39.807 |
| First SDK exception | 33.878 | 35.946 | 45.223 |
| `omni.usd` shutdown | 46.815 | 52.557 | 58.162 |
| Semantics editor shutdown | 44.837 | 51.176 | 57.161 |
| Semantics `_window` menu range | 45.246–48.193 | 51.475–51.563 | 57.440–58.697 |
| File-menu stage-state range | 47.783–48.106 | none | 58.519–58.669 |
| Edit-menu selection range | 47.801–48.176 | none | 58.521–58.693 |

All error lines follow SDK shutdown start. In the polygon run they also follow
review-extension shutdown. Selection/stage-state menu errors all follow `omni.usd`
shutdown. Semantics errors can precede it: that editor had already shut down at
57.161s; six of its ten callbacks precede USD shutdown and four follow it.

Stack frames resolve to installed SDK `isaacsim.robot_setup.xrdf_editor`,
`isaacsim.sensors.physx.ui`, `omni.kit.manipulator.prim.core`,
`semantics.schema.editor`, `isaacsim.gui.menu` and `omni.kit.menu.utils`.
The latter calls `get_context().get_selection()` / `get_stage_state()` after
context teardown, or queries an editor window after its owner was unloaded.
No polygon triangulation or face-overlay frame was found in these tracebacks.

This supports existing SDK teardown callbacks as the observed failing sites,
rather than a new polygon exception. It does **not** prove review activity has no
effect on callback frequency: setup, actions and durations differ. No matched
frequency experiment was run, and lifetime/memory causality is not established.

All three processes exited 0; the newer two retain strict-clean=false. The oldest
record predates the structured strict-clean field, so the audit preserves null
instead of manufacturing a retrospective value. Its 82 errors remain explicit.
Graphics/Fabric diagnostics and stock Full/live A/B restrictions remain separate
unresolved limits. Known signatures are still failures for strict-clean assessment.

## Reproducibility

The read-only `tools/classify_shutdown_errors.py:classify` groups recognized
signatures, timestamps, menu entries and SDK-relative frames; unknown errors stay
in an explicit unclassified count. It never produces a passed/clean verdict or
changes `shutdown_profile.assess`. Synthetic tests retain unknown project traces
without private paths and verify repeated lines are counted rather than deduped.

[Sanitized evidence](../diagnostics/shutdown-signature-audit-v1.json) contains
per-signature counts/ranges, frame locations and original log hashes, not raw
logs or machine paths. Those totals match the independently recorded summaries.
The resulting product work is [display feedback and scroll access](review-display-feedback.md),
not an attempt to make the SDK error total smaller.
