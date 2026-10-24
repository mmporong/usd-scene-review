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
