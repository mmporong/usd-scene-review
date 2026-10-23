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

Use the installed Python/OpenUSD environment described in the Windows validation
instructions. Example arguments after the existing `with_openusd.py` wrapper:

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

The new three-route controls are **NOT RUN** at preparation time because another
Kit host continued using the GPU. Final Windows CPU regression ran 159 cases:
157 passed, two privilege skips, zero failures/errors (67.331 s). CPU checks verify
the launch restrictions and absence of save/pending-edit mutation calls; they do
not verify the SDK prompt, close callbacks, or clean exit. Previous uncancellable
baseline failures and the 40-check candidate shutdown failure remain unresolved.
No upstream issue was sent, and no SDK, driver or global setting was changed.
