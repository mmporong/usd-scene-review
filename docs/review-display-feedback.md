# Review display feedback and values access

The selected object now has a dedicated read-only display-status field in the
review panel, separate from general operation messages. It shows the selected
path, whether old A faces are shown/off/unavailable, an explicit refusal reason,
and A/B presence. Subdivision, nonplanar/unsafe geometry, missing A and budget
limits therefore cannot leave a stale generic "shown" message as the only panel
feedback. The viewport caption and shared before/after values remain available.

The support text beside the face checkbox states that only static Cube and simple
planar linear Mesh are supported. Refusing faces does not silently substitute a
filled box, change comparison evidence, infer intent or waive independent policy.
Compare first, select a row, then Show snapshot bounds. To inspect direct versus
ancestor effects, use the motion-evidence line and the shared local/world numeric
table. Values retain their stage-unit/meter and unsigned-axis explanations.

The entire review panel is scrollable as well as its change list and numeric
table. Small windows can reach the numeric evidence instead of clipping everything
below the fixed controls. Wide tables can require horizontal scrolling; the
camera and USD selection do not move when the review UI scrolls.

Pair selection now explicitly says it is pair evidence and clears single-object
overlay geometry. It no longer claims the camera framed both objects when no
viewer focus occurred. Select an individual change row to restore object display.
Optional legacy/A-B viewer focus is separate and existing guards remain.

Closing/hiding the panel, clearing display, a stage/lifetime event, Play or input
verification failure updates the status or clears owned display. Source/session,
hash/manifest/resolver checks and comparison semantics are unchanged. This is UI
feedback, not current-stage verification, collision evidence or SDK shutdown repair.

The [existing-log audit](shutdown-signature-audit.md) explains the 8→100 error-line
comparison without a new GPU run. A separate minimal owned-host regression is
used for these actual status/scroll changes; callback/API interaction is never
described as mouse testing. Strict-clean conditions are not relaxed.

## Actual UI regression

One owned native regression used the unchanged small polygon fixtures, preserved
navigation-excluded profile and canonical exclusive GPU lease for the UX fixes.
It passed 57 candidate and 18 outer checks: per-object ready/refusal status,
subdivision reason, pair evidence without false framing, display-off state,
scroll access, existing face rendering/toggles and source preservation. The real
panel scroll moved to its 490-pixel maximum and was restored. This is UI API and
callback validation, not mouse/hit testing.

Working USD/session, camera, selection, pending, time, renderer settings and input
bytes were preserved. Public file.close reached natural exit 0. Owned PID/Job were
reaped without containment and the lease naturally released. SDK diagnostics
remain: 32 errors, 263 warnings, tracebacks and graphics/Fabric markers. Wrapper
exit 2 and strict-clean=false remain. The 32 lines classify as the same baseline
signatures: three exception/wrapper pairs (6), Semantics window (5), file menu (1)
and 20 edit-menu selection callbacks. Their lower count is not an SDK improvement
claim. No unknown error signature or project traceback was observed.

[Sanitized QA evidence](../diagnostics/review-feedback-qa-v1.json) keeps those
results and the separate audit of this already captured follow-up log. The first
CPU preflight exposed an outdated extracted-method SelectionRouter test fixture
that lacked the new method/model (10 errors). Updating that fixture preserved
its assertions; all seven focused queue tests then passed. No product timeout,
shutdown success condition or error filter was relaxed. Stock Full/live A/B and
long-session/mouse limits remain.

Final Windows CPU/package suite: 234 cases, 232 passed and two privilege skips,
no failures/errors (67.728s). Geometry and integrity code were not changed by the
UI work; final runtime files match the actual owned-host regression copies.

## Filtered change navigation

Use Path search, Change type (all/modified/added/removed/unobserved), and Inherited
motion together. Previous change and Next change select only matching rows, in
report order. They update the same numeric evidence and, when enabled, snapshot
bounds/old-A faces as clicking a row. They do not change working USD selection or
camera. An optional already-open isolated legacy viewer retains its existing focus
behavior; this is separate from the working viewport.

At either end navigation stops without wrapping. With no selected matching row,
Next starts at the first match and Previous at the last. No matches leaves current
evidence intact with an explicit status. Changing a filter alone never silently
selects a different object or clears existing evidence. Human review metadata,
comparison identity, integrity checks and geometry support are unchanged.

### Working-camera framing remains unavailable

The installed 4.5 `omni.kit.widget.viewport` 107.0.7 API exposes `view`, `transform`
and `projection` as read-only properties. In `omni.kit.viewport.utility` 1.0.18,
`__frame_viewport_objects` resolves the active USD camera or look-through target
and calls `FramePrimsCommand(prim_to_move=..., usd_context_name=...)` inside an undo
group. This is not a stage-free view override. Saving/restoring those prim values
afterwards would still author transient stage/session edits and could overwrite
intervening user edits. Switching to or creating a session camera also conflicts
with this product's current session/pending preservation contract.

No validated public working-render-camera override satisfying that contract was
found in those installed APIs. Consequently this version offers no working-camera
"view change area" or "restore view" command and invokes no framing API. This is
a limitation of the verified integration path, not a claim that every SDK renderer
option is impossible. The separate UI SceneView camera only affects helper shapes;
moving it would misalign them with the working scene. It is not a substitute.
Since framing is refused before any action, no A/B bounds, units/up-axis or large-
bounds camera calculation is performed or claimed validated by this change.

### Navigation regression, 2026-10-24

Windows CPU suite: 237 cases, 235 passed, two privilege skips, no failures/errors
(125.844s under shared CPU load; not a performance benchmark). Added regression
checks cover composing path/type/inherited filters, all four change kinds, report
immutability, stable order, hidden/no selection, both endpoints, empty results,
and the actual product navigation callback. Existing frozen-input tamper rejection
and package tests remain enabled.

One isolated native run used the same synthetic polygon fixtures, installed Isaac
Sim 4.5/Kit106.5/Python3.10.15, RTX3060/driver610.62, canonical shared GPU lease and
preserved navigation-excluded Full-derived profile. All 61 candidate and 18 outer
checks passed. Across two cycles the actual type model/path filter and Next callback
selected the removed object, cleared pair evidence, updated the same bounds/value
path, and retained selection at the boundary. Working USD/session, pending, camera,
selection, time, rendering settings and input bytes remained unchanged. This is
callback/UI API validation, not real mouse/hit testing. Existing alpha0.22 face,
polygon, support-message, toggle and cleanup checks also passed.

Public file.close observed CLOSING/CLOSED and natural process exit0. Owned PID/Job
were reaped, with no containment, and the wrapper naturally released the lease.
The log still contains 166 errors and 546 warnings; wrapper exit2 and
strict-clean=false are preserved. Signature counts are six existing SDK exception/
wrapper lines, 13 Semantics window callbacks, seven file-menu callbacks and 140
selection callbacks (20 menu items repeated seven times). All error lines follow
review shutdown and SDK shutdown start; all file/selection errors follow USD
shutdown. No unclassified signature or project traceback was observed. Differences
in repeated menu polling are not evidence of an SDK error-rate improvement or
regression caused by navigation. Graphics/Fabric shutdown diagnostics remain.
Stock Full/live A/B, real mouse and long-session qualification are unchanged.
