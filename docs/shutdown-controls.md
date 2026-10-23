# Owned Full Isaac shutdown controls

These diagnostics distinguish a quit request from a verified clean process exit.
They do not change the review extension, unblock Full Isaac review, or qualify the
local sequential capture candidate as simultaneous live A/B.

## Installed 4.5 API evidence

`omni.kit.window.file` 1.3.57 registers a shutdown hook at
`file_window.py:361-372`. Ordinary `IApp.post_quit()` with pending edits cancels
shutdown and invokes the file close flow. With `fastShutdown=false`, close waits
for `UsdContext.close_stage_async()` and another update before invoking its
callback (`940-972`). `prompt_if_unsaved_stage` offers Save, Don't Save and Cancel
(`1036-1076`). The public `close(on_closed)` wrapper delegates to this flow
(`1294-1303`). An uncancellable quit does not establish those same preconditions.

## Prepared isolated routes

Use the [pinned profile and canonical shared-wrapper entry](shutdown-profile.md)
for the preserved reduced control and its matched Full counterpart. All native
launcher paths require active shared admission; low GPU utilization alone is not
permission to run. A completed/old owner string does not grant a lease.

`tools/run_in_app_validation.py --shutdown-control ROUTE` requires
`--full-app --baseline --fail-fast-native`, before creating any output. Baseline
mode does not package or expose the review extension. The launcher creates one
unchanged synthetic USDA file in the new output directory. The probe first checks
the fresh portable config, anonymous startup stage and disabled review extension;
it may then open only that owned file. It does not add a viewport or stage context.

| Route | Requested action | Stage-close evidence |
| --- | --- | --- |
| `normal` | `app.post_quit(0)` | Record whether SDK emits CLOSING/CLOSED; do not assume it |
| `file-close` | public `omni.kit.window.file.close(callback)`, then `post_quit(0)` | Callback must observe no active stage; record events |
| `uncancellable` | `app.post_uncancellable_quit(0)` on the same fixture | Record events; no equivalent close claim |

Do not run the three routes concurrently. Check other user/Factory Kit processes
and GPU headroom before each host. Run `file-close` first to test the new stage
close hypothesis, then normal and same-fixture uncancellable controls only if no
native failure occurred. At the first known native error the launcher contains
only its owned Job; do not proceed automatically to another GPU control.

The internal arguments below are only for a child already admitted by the official
shared wrapper. They are refused outside that ownership; prefer the profile entry.

```text
tools/run_in_app_validation.py --isaac-root <existing-sdk> --output <new-owned-output> --full-app --baseline --shutdown-control file-close --fail-fast-native --timeout 240
```

The probe never saves, exports, clears pending edits, changes save-dialog policy,
or closes an existing user's app/stage. A root-dirty fixture fails preflight rather
than being silently cleaned. SDK pending edits and session dirty state are recorded
separately. If a save prompt appears, the SDK UI test API may click exactly one
Don't Save button only when the expected save-question label and owned fixture
are confirmed. Unexpected prompts fail or time out; there is no substitute quit.

## Independent receipts and current status

- `result.json`: readiness checks, pending edit state, stage events, public-close
  callback, actual discard interaction and probe unload observation.
- `process-result.json`: actual exit code, native warning/error signatures,
  containment or timeout, owned root PID and whether it was reaped, and fixture
  byte preservation. Root PID reaping does not claim every descendant exited
  naturally; the Job's containment remains active until launcher cleanup.
- A passed probe receipt alone is not a normal-exit pass. Require exit code 0,
  functional checks passed, no known native failures, unchanged fixture, and PID
  reaping. Review the log separately for warnings not in the known failure set.

Later file-close observations: the navigation-included SDK baseline crashed in
navigation core after its close callback (shared GPU exclusion was not verified).
One official-lease navigation-excluded host then reached exit0, CLOSING/CLOSED,
unchanged file and reaping, but retained82 errors/824 warnings. The stricter
[preserved profile](shutdown-profile.md) does not call this clean success. Ordinary
quit and save/discard UI remain unrun. A later lease-controlled matched Full passed
14 checks then crashed at navigation core `+0x18014`; its owned Job and shared lock
were recovered. See the pinned profile for the two-control contrast. Prior
uncancellable failures and the40-check viewport candidate shutdown failure remain
unresolved. CPU checks verify policies, not SDK prompt/cleanup behavior.
No upstream issue was sent, and no SDK, driver or global setting was changed.
