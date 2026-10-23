# Sequential Widget candidate under the pinned reduced profile

This is an owned diagnostic treatment, not a product adapter or simultaneous live
A/B split. The Full-host product guard stays enabled. It transfers the explicit
public Widget path from local commit `ca940ec` without that experiment's standalone
host or uncancellable quit policy. There is no SDK patch or global navigation toggle.

## Feasibility and treatment boundary

The pinned profile opens the same unchanged file and validates its SDK, startup
inventory, navigation exclusions/schema and shared lease. Before the existing
public file.close route, the optional candidate performs the original 40 checks
across two real create/destroy/recreate cycles. Each cycle attaches independent
in-memory A/B/A revisions to one extra owned context and public ViewportWidget in
a plain UI Window. It captures real red/blue/red pixels, checks matching camera
matrices and preserved sources, erases cache entries and destroys actual owners.
It does not pool hidden native windows. A cached image pair is not two live scenes.

Working default stage/session text, selection/time and source camera values are
checked by the transferred candidate. Additional before/after renderer-setting
receipts detect changes rather than silently restoring global state. On success,
the baseline probe invokes its unchanged public file.close, records CLOSING/CLOSED,
then requests ordinary quit. On failure it does not substitute another quit route;
the owner contains its Job and records failure, never normal success.

```powershell
./tools/run_shutdown_profile.ps1 -IsaacRoot <existing-sdk> -Output <new-local-output> -DiagnosticProfile no-navigation -Candidate viewport-reuse
```

The candidate is refused on matched-full or unpinned profiles before admission or
output creation. The canonical wrapper still makes only one maximum 1s acquisition
attempt; another owner or failed probe means no child. No other project is changed.
All 40 named checks, no remaining candidate owners, preserved working stage/settings,
base profile conditions, actual PID/Job cleanup and strict log qualification are
required. Exit 0 alone is insufficient; existing errors/warnings cannot be hidden.

## Current evidence

The earlier standalone explicit-widget experiment passed 40 checks but failed a
Hydra texture warning gate during whole-app shutdown. It used navigation-included
uncancellable quit, unlike this new treatment. The pinned reduced SDK baseline
separately exited 0 with 82 error/824 warning lines. Matched Full reproduced the
navigation crash under exclusive admission. Neither result proves this combined
candidate's exit behavior.

This treatment **ran once on 2026-10-23 and failed the shutdown qualification**.
Earlier acquisitions returned 73 without creating a child. The later single
official wrapper acquired the shared exclusive lock after contention cleared;
admission observed 3% GPU utilization and 1725 MiB used of 12288 MiB. The pinned
426-extension startup inventory matched, navigation core/recast were disabled,
schema remained enabled and the native navigation core module was absent.

All 40 candidate checks passed across both cycles: real red/blue/red captures,
matching camera matrices, independent revision namespaces, source preservation,
actual viewport/context/timeline removal and recreation, and preserved working
stage/selection/time. The additional renderer-settings preservation check passed.
These observations cover this synthetic sequential candidate's rendering and
local teardown only; the combined treatment did not qualify.

After the candidate, the probe invoked public file.close but its callback and
default-stage CLOSING/CLOSED receipts were absent through 600 updates. The probe
reported `normal shutdown did not finish within 600 updates`. The launcher then
contained its owned Job and returned 1; this is **not a natural native exit or a
clean shutdown**. The owned process was reaped, the Job was empty and closed, no
owned PID/direct child remained, fixture bytes matched the pinned hash, and the
official wrapper naturally released the matching lease. No other process was
terminated or lease modified.

The captured console had zero error lines and 715 warning lines, including repeated
UI-query failures to find window `*`. No known native crash signature was detected
before containment. Forced containment means neither later crash freedom nor clean
resource shutdown can be inferred. The installed file extension's public close
wrapper can return without action if its internal singleton is absent; otherwise
it schedules prompt/async stage-close work. This receipt does not trace those
branches, so it cannot distinguish an absent singleton, queued close work or UI
prompt failure. The warnings alone do not establish the cause. This failed
treatment will not be repeated unchanged.

CPU tests verify fixture independence, all-40-check qualification, no independent quit or
official Window menu layers, and refusal on Full. They are not SDK acceptance.
Final Windows CPU regression: 175 cases, 173 passed, two privilege skips, no
failures/errors (55.258s). PowerShell entry syntax also passed.

Any follow-up must first add evidence that distinguishes the public close branches
and state a new hypothesis. It must use normal shared admission and stop at the
first native/functional failure. The observed usable scope is only the reduced
sequential fixture/capture route before shutdown. Product change-list navigation, ghost,
simultaneous live panes, user workspace recovery and original Full support remain
unqualified. Raw local logs/captures are not published by this diagnostic change.

## Instrumented contrast

The shutdown probe enumerates `omni.ui.Workspace.get_windows()` titles and queries
labels only for an existing visible file save prompt's exact title. Installed UI query matches window titles exactly;
the old `*//...` query never searched all windows. Prompt actions have been removed.
The observer reads default context/stage identity, native pending/can-close state,
root/session dirty flags, file utility/task state and visible save-prompt labels.
Internal file utility/task fields are version-specific read-only diagnostics, not
a supported replacement for public close. Pending edits or a save prompt prevent
close invocation so an SDK save branch cannot be triggered by this diagnostic.

One instrumented reduced-profile run passed all 40 candidate checks and two cycles.
Its three observations (before candidate, after cleanup, before close) had the
same default context and stage ID, clean fixture root, dirty session, native pending
edits true, can-close true, a present file utility and no file task or observed save
prompt. The guard therefore did **not invoke file.close**. It returned failure and
the owner contained the Job. Fixture preservation, PID recovery, empty/closed Job
and natural matching lease release were verified. Console: zero errors, 131
warnings. This result does not establish native crash freedom or normal shutdown.

The earlier immediate pending sample in this run was false, whereas the first
full observation was true before candidate execution. Imports and UI enumeration
occurred between those samples. Neither a candidate-induced pending edit nor the
exact effect of observation is proven. The final observer adds a native receipt
before SDK observer imports and native pending samples before/after window queries
to isolate that gap. Those extra sampling points have CPU regression coverage but
have **not** received another native run. No unchanged treatment was repeated.
The next distinct question is whether imports, UI queries or other startup work
change native pending state before the candidate. No pending reset, automatic
dialog action or save-policy override is an acceptable diagnostic correction.

## Pending transition localization and observer correction

Further native controls separated two effects. The pinned file contains only a
Cube and no authored camera. Installed viewport utility creates its default cameras
in a session edit scope, then restores the previous edit target. In both new paths,
fixture open returned with a clean root, dirty session, four default cameras,
root edit target and native pending false. That state remained unchanged through
20 updates and observer imports. Session dirty alone therefore does not establish
the pending state that blocked close.

The broad exact-title label observer changed pending false to true in a candidate-free
baseline, between pre-query and post-query samples, with unchanged root/session
hashes, edit target and camera paths. Installed UI query accesses window frames and
descendants; the exact callback responsible is not established. General editor UI
must not be traversed for prompt detection. An attempted modal-flag filter failed
because Workspace returns WindowHandle objects without a flags attribute; it was
contained and corrected rather than counted as a lifecycle result.

The final observer reads title/visible metadata only for general windows. It queries
labels only when the installed file utility already owns a visible unsaved-stage
Prompt, using that prompt's actual title. This SDK-specific prompt reference is
read-only; it does not construct, show, hide or select the prompt. CPU regression
uses handle-shaped objects without flags and proves that absent prompts never
trigger editor-tree queries.

| Distinct reduced-profile control | Observed outcome | Console errors / warnings |
| --- | --- | --- |
| Broad exact-title observer, no candidate | Pending false to true during UI query; close blocked, owned Job contained | 0 / 116 |
| Modal filter attempt | WindowHandle flags AttributeError before close; owned Job contained | 0 / 109 |
| Existing-prompt-only observer, no candidate | Pending stays false; public close callback, CLOSING/CLOSED, native exit 0, launcher exit 2 | 28 / 798 |
| Same observer with candidate | 40 checks/two cycles pass; pending false before candidate and true after; close blocked, owned Job contained | 0 / 115 |
| Same candidate with phase receipts | 40 checks/two cycles pass; first observed pending transition spans first attach_stage_async(A); close blocked, owned Job contained | 0 / 115 |

The phase receipts remain false through context/timeline creation, revision fixture
authoring and cache registration. They become true after the first attach completes,
before the added viewport is created. Default context/stage identity, root/session
hashes, root edit target and default camera list remain unchanged. This localizes the
interval, not a unique native function or callback cause; asynchronous attach also
allows other host work. No save prompt was observed or selected in these runs.
All controls retained fixture hashes, reaped owned PIDs, emptied/closed their Jobs
and naturally released their matching shared leases. Containment is not native exit.

The corrected baseline has a genuine native exit 0 without forced cleanup, but SDK
shutdown errors, graphics leaks and Fabric-history warnings still fail strict clean
qualification. It does not qualify original Full or the candidate's shutdown.
The candidate preservation contract must include native pending state, not only USD
text. No safe correction for the attach interval is established. The subsequent
[matched attach-only control](attach-only-control.md) reproduced the transition
without viewport/capture and separated it from 60 no-attach updates. Further
investigation must distinguish native/context event callbacks. Do not clear pending, dismiss
save prompts, patch SDK or reinterpret the blocked candidate as successful shutdown.
Final Windows CPU regression: 180 cases, 178 passed, two privilege skips, no
failures/errors (44.028s). These CPU checks do not qualify native Full support.
