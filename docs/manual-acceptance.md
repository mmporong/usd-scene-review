# Manual rc.4 acceptance checklist — NOT RUN

This is a handoff checklist, not a record of mouse tests. Current automation reached
65 SDK callback checks and natural reduced-host exit0, with strict-clean=false.
The UI tool's one connection check failed before app selection (kernel assets path
missing, os error3). No test below may be marked PASS from those callback results.
See [first use](first-use.md) for exact package paths and commands and
[release decision](release-blockers.md) for the independent SDK limits.

## Operator prerequisites

- Verify rc.4 ZIP/sidecar SHA256. Extract fresh and keep outputs elsewhere. Use the
  included synthetic pair or newly generated sample, never private factory scenes.
- An operator must provide a **dedicated owned interactive test host**, with Play
  stopped and no unsaved user work. Do not switch, close or overwrite a working
  Factory/robotics app. If such a host is unavailable, leave the checklist PENDING.
- For any new GPU host, retain the canonical shared lease for the entire host
  lifetime and check unmanaged work after acquiring it. On conflict, do not launch.
  Do not force-release another lease or stop another project. The owned portable
  diagnostic state must have an ASCII path. Do not disable navigation globally.
- Whole-app exit acceptance requires the preserved host-local reduced profile,
  startup inventory and exclusion/dry-solve receipts, as in shutdown-profile.md.
  An arbitrary interactive Full app is not equivalent. The existing automated
  profile runner completes callbacks and exits; it is **not** an interactive hold
  launcher. Do not race manual input against its timed checks. Interactive host
  setup/coordination is a prerequisite, not a completed deliverable of this checklist.
- Record installed SDK/Kit/Python/USD/GPU/driver and archive hash privately. Keep
  before/after hashes for both synthetic source files and frozen bundles. If API
  receipts for root/session/pending/camera/selection/settings are unavailable in
  the interactive host, mark that preservation row NOT VERIFIED; a visible save
  indicator or screenshot alone does not prove the complete preservation contract.

## Actual clicks to record

Use PASS / FAIL / NOT RUN and a private evidence reference for every row. All rows
start **NOT RUN**. The expected result is an acceptance requirement, not an observation.

| Step | Operator action | Expected result |
| --- | --- | --- |
| Installation | Add candidate ext directory through Extensions UI; enable project. | Panel is readable; no replacement stage, new viewport or save obligation. |
| Input recovery | Click Compare with empty A, then a missing B, then valid quoted A/B paths. | Correct side-specific error; valid comparison succeeds; a typo retains previous evidence. |
| Filtering | Type path search; select each applicable type; toggle inherited motion. | Visible rows match criteria; direct/mixed and inherited cases are not confused. |
| Selection | Click a changed row, added/deleted row and parent-motion row. | Path, A/B bounds and before/after/delta/provenance agree; working camera and USD selection remain unchanged. |
| Navigation | Click Previous/Next with a filter and at both endpoints. | Only matching changes selected, no wrap; empty results are explicit. |
| Old shape | Click old-A face toggle on/off, supported polygon and unsupported subdivision. | Green/lime faces alpha0.22 where supported; correct refusal reason otherwise, with no stale prior geometry. |
| Readability | Scroll from controls to numeric evidence and back. | Legend, units, direct/parent evidence and refusal text remain accessible at normal display scaling. |
| Pair evidence | Select an AABB candidate, then an individual change. | No false collision verdict or claim that working camera framed the pair; old single-object geometry clears appropriately. |
| Overlay close | Click Clear bounds, Show snapshot bounds, Close review and Show again. | Owned helpers close/reopen, retained comparison stays usable, source/session and view unchanged. |
| Panel lifecycle | Close panel, then disable/re-enable extension; re-enter A/B. | Helpers and subscriptions removed; fresh panel compares again, no duplicate panel/overlay. |
| Stage lifecycle | In the owned host only, switch between two disposable unchanged stages. | Helper clears; no original stage is reopened or saved by the extension. |
| Guard | Inspect experimental Full/live A/B control. | Still disabled/refused before native review ownership. Do not bypass it. |
| Preservation | Compare hashes and available before/after API receipts. | Input bytes, root/session/edit target/dirty/pending, camera, selection, timeline/settings preserved. Missing receipt is NOT VERIFIED. |
| Exit | Operator closes only the owned host using normal UI, with no dirty fixture. | Record stage close, natural process exit, warnings, Job/PID cleanup and natural lease release separately. Never hide containment or dialogs. |

If a Save/Don't Save dialog appears unexpectedly, **do not auto-select it**. Record
its exact title, active owned context/fixture, pending and dirty state if available,
then stop that acceptance row. A real user's edited stage requires that user's own
decision; do not clear pending, save over an input or discard edits to get a pass.

Record natural exit0 separately from strict-clean. Errors, tracebacks or known
graphics/Fabric diagnostics keep strict-clean=false. A Full navigation crash is an
SDK boundary, not a reason to bypass protection or describe the review as stable.
Containment, if needed, applies only to the owned test Job after observing the
failure; release the canonical wrapper only after its children are reaped.

## Report back

Return the completed status table, candidate hash, versions, exact unexpected UI
behavior and private evidence locations. Public screenshots must show only synthetic
assets with private paths removed; do not publish raw logs or SDK dumps. Keep
mouse observations separate from API receipts and automatic checks. A human signoff
cannot resolve the separate native Full exit/live A/B issues without their required
SDK evidence. Project license selection is still an independent release decision.
