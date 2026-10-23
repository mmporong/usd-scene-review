# Matched attach-only and no-attach controls

This is a reduced-profile diagnostic, not a product adapter or a Full-host fix.
It separates named-context stage attachment from viewport/capture work and from
the same number of ordinary application updates. The original Full guard remains.

## Matched procedure

Both arms create one owned named context with its own timeline, import an anonymous
independent copy of the pinned Cube fixture, insert it into the stage cache, then
wait exactly 60 application updates. The same per-update receipts identify default
and owned context/stage, pending state, layer hashes, edit target and camera state.
The attach arm schedules one public attach_stage_async request before the loop;
the wait arm makes no request. Matching update counts is not a claim of identical
wall-clock timing or scheduling. Both destroy their owned resources afterward.
No viewport/capture is created, no prompt is selected and no pending flag is reset.

```powershell
./tools/run_shutdown_profile.ps1 -IsaacRoot <existing-sdk> -Output <new-output> -DiagnosticProfile no-navigation -AttachControl wait
./tools/run_shutdown_profile.ps1 -IsaacRoot <existing-sdk> -Output <another-new-output> -DiagnosticProfile no-navigation -AttachControl attach
```

Each command requires normal exclusive admission through the existing canonical
shared wrapper. Full/unpinned invocation or combining this with a review candidate
is rejected before admission/output. SDK files and global settings are unchanged.

## Actual results, 2026-10-23

| Same pinned reduced configuration | No-attach wait | Attach only |
| --- | --- | --- |
| Updates completed | 60 | 60; attach completed by update 1 |
| Default pending | False throughout control | False before request, true at update 1 and afterward |
| Attached context pending | False; no stage attached | False; distinct stage ID |
| Default root/session hashes and edit target | Preserved | Preserved |
| Extra viewport | None | None |
| Owned context/timeline cleanup | Completed | Completed; owned stage closed |
| Public file.close | Callback and CLOSING/CLOSED | Guard prevented invocation |
| Native process ending | Natural exit 0, launcher exit 2 | Owned Job containment, exit 1; not natural shutdown |
| Console errors / warnings | 7 / 506 | 0 / 109 before containment |

Fixture bytes were unchanged; all owned PIDs/direct children were gone, Jobs empty
and closed, and matching leases naturally released. The wait arm's remaining SDK
errors, tracebacks, graphics leaks and Fabric-history warnings fail strict clean
qualification. Lower counts before forced containment do not indicate improvement.
The attach operation's nested result records procedure completion; top-level
qualification still fails and requires native pending preservation as well.

The differential reproduces the default pending transition without the original
review candidate, material/camera fixture, additional viewport or capture. It
distinguishes attach-associated work from this fixed update-count wait control.
It does not identify a unique native function or Full-app callback as the cause.
The unrelated navigation shutdown fault remains a separate limitation.

## Installed and official API review

Installed omni.usd 1.12.4 `_impl/api.py` inserts the supplied stage into the stage
cache and calls that context's attach_stage_with_callback. Its provided stage-event
tests use attach_stage_async with independent in-memory stages. Our usage follows
that pattern, with a unique context name and separate timeline.

The same-version [official overview](https://docs.omniverse.nvidia.com/kit/docs/omni.usd/1.12.4/Overview.html#how-to-create-another-usdcontext)
supports named contexts and attaching existing stages. The [UsdContext API](https://docs.omniverse.nvidia.com/kit/docs/omni.usd/1.12.4/omni.usd/omni.usd.UsdContext.html#omni.usd.UsdContext.attach_stage_async)
accepts a stage for attachment; the reviewed API exposes no pending-isolation
parameter for that call. The documented manual pending setter overrides dirtiness
and is excluded here. This review found no validated safe configuration correction;
it does not prove that no solution exists elsewhere in the SDK.

Next useful distinctions are a named-context open_stage_async control using an owned
immutable fixture copy, or targeted inspection of default DIRTY_STATE_CHANGED and
Full-app callbacks during attach. Neither is run by these controls. An open-path
success would still need independent revision and lifecycle qualification before
replacing the product adapter. Do not suppress real edits or save prompts to pass.

Final Windows CPU: 183 cases, 181 passed, two privilege skips, no failures/errors
(42.978s). The PowerShell entry parsed successfully. CPU tests enforce the shared
60-update budget, absence of rendering/unsafe mutations, reduced-profile-only
admission, real cleanup and native pending preservation for qualification.
