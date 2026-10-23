# Review close and working-stage preservation

The product goal is pre-Play collaboration review inside the user's Isaac app.
Closing a review must leave that app and its working stage available. It must not
close/reopen the user's stage, save/discard edits, reset pending state, stop a user's
timeline or quit the user's process. Whole-app shutdown qualification is a separate
result; it cannot substitute for actual review-window lifecycle evidence.

## Independent acceptance results

| Result | Required evidence |
| --- | --- |
| Input preservation | Snapshot/source file hashes, used layer state and permissions preserved; no source save |
| Working content | Same context/stage, root/session and used-layer contents, edit target and dirty flags |
| Working save state | Native pending state preserved independently of layer contents; no new save/discard obligation introduced by review |
| Working interaction | Selection, source camera/view/projection, timeline, renderer settings and workspace preserved |
| Review close | Actual owned windows/widgets, render drain, textures, contexts, timelines, subscriptions/tasks, ghosts and caches released; permissions/settings/layout restored |
| Review reopen/unload | Actual repeated open/close and extension disable/stage transition evidence; hidden retained owners are not confirmed close |
| Whole-app exit | Separately observed natural exit and diagnostics on an owned test host; forced Job cleanup is not normal shutdown |

A native pending change without a hash change is not proof that source geometry or
authored opinions changed. It is also not safe to dismiss as a cosmetic notice.
The [same-version public API](https://docs.omniverse.nvidia.com/kit/docs/omni.usd/1.12.4/omni.usd/omni.usd.UsdContext.html#omni.usd.UsdContext.has_pending_edit)
exposes unsaved-edit status; its manual setter can override layer dirtiness. Installed
USD tests explicitly distinguish layer dirty from this state. The file extension's
prompt_if_unsaved_stage branches on native pending and ignore-unsaved policy, not
on a fresh comparison of layer text. With normal policy it requests a save decision;
other configured policy can save instead. Its post-quit hook can cancel shutdown
and route through that same close/save logic. These are SDK behavior facts, not
evidence of human intent or proof that saving is required for unchanged fixture data.
The extension must neither clear that flag nor choose a save/discard action.

## One grounded minimal/Full-derived pair, 2026-10-23

A task-local diagnostic harness used the same installed/pinned Isaac4.5 SDK,
fixture bytes, independent owned open-copy path, named context/timeline, public
open_stage_async, 60 updates, corrected non-invasive observer and shared GPU lease.
Minimal explicitly loaded UI, USD, file and RTX viewport/window dependencies.
Full-derived used the installed Full app with the previously approved navigation
core/recast exclusions and schema retained. No other extension was randomly disabled.
Both conditionally created a fresh anonymous startup stage only if none existed,
then opened only their owned default fixture. Inventories were recorded rather than
calling the minimal host Full-qualified. No product review window/viewport or Play
was used. Sources and SDK were not patched. The harness stayed local; no new public
observation-only launcher is added by this result.

| Receipt before whole-host teardown | Minimal Kit | Navigation-excluded Full-derived |
| --- | --- | --- |
| Startup extensions | 80 | 426 |
| Open completed by update | 2 | 1 |
| Updates observed | 60 | 60 |
| Default root/session content, stage identity/edit target | Preserved | Preserved |
| Selection, camera/view/projection, time, selected settings/window metadata | Preserved | Preserved |
| Owned stage/context/timeline closed | Yes | Yes |
| Default native pending | False to true; dirty receipt after counter2 | False to true; dirty receipt before counter1 |
| Actual review-window lifecycle | Not tested | Not tested |
| Whole-host quit requested | No, pending barrier | No, pending barrier |
| Owned host ending | Job contained, exit1 | Job contained, exit1 |
| Console errors/warnings before containment | 0 / 5 | 0 / 109 |

Both fixture files were unchanged, owned PIDs were reaped, Jobs empty/closed and
matching leases naturally released. The pending failure appears with common
minimal components too; it cannot be attributed solely to Full's extra extensions.
The pair does not identify a unique native function/shared callback, establish
whether a save would produce different bytes, or establish later crash freedom.
Lower warning counts before forced cleanup are not evidence of a shutdown fix.
These are owned clean-file fixtures, not arbitrary unsaved production stages.
Window title/visibility equality is not actual dock-layout restoration or mouse QA.

## Actual deployment boundary

The later [stage-free working-viewport bounds overlay](viewport-bounds-overlay.md)
uses no named context or owned renderer texture. Actual Full Isaac checks preserve
root/session contents, native pending false-to-false, selection and camera while
drawing A/B bounds and closing/reopening/unloading that UI overlay. This qualifies
only that narrow bounds route; the historical named-context results below and the
live A/B Full guard are unchanged. AABB lines do not fulfill the green mesh ghost.

CPU comparison/snapshot/report features, the narrow stage-free bounds route above
and the retained separate worker's tested static review are available within their
documented limits. The worker
does not fulfill same-app integration. Full in-app A/B remains blocked before native
ownership. Minimal in-app code is a developer experiment, not a generally qualified
working-stage-preserving deployment: this pair reproduced the pending side effect.

Earlier synthetic sequential Widget controls passed 40 checks/two create/destroy
cycles. That is useful local window/resource evidence, not full product UI workflow
qualification. A separate earlier Full feature run failed at its first review close
with a native texture warning; that must not be relabelled as only an app-exit fault.
The project-free Full navigation crash is another independent host-exit limitation.

No safe change to named-context stage operations was established here. Product guard
behavior is retained; its shared UI/API explanation now names save-state preservation
and review cleanup rather than implying whole-app exit is the only gate. Further
work must resolve/qualify the shared pending behavior and then exercise the actual
review window's close/reopen/unload while the working stage remains open.

Final Windows CPU/package regression: 184 cases, 182 passed, two privilege skips,
no failures/errors (43.260s). The existing before-ownership guard regression still
passes with the shared preservation/cleanup explanation. This text-only product
change does not add native UI qualification or alter the guard condition.
