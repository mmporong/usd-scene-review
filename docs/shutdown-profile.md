# Reproducible owned shutdown diagnostic profile

`diagnostics/isaac45-shutdown-v1.json` preserves one actual Windows observation:
the SDK Full experience with navigation core/recast excluded, schema retained,
an unchanged synthetic file, public `file.close`, CLOSING/CLOSED, native exit0,
owned PID reaping and natural official shared-lease release. It is a **reduced
configuration**, not a repaired Full Isaac app or accepted A/B viewport product.

The historical run passed 13 fixture/ownership checks but logged **82 error lines
and 824 warning lines**. Many errors were repeated shutdown menu callbacks; the
graphics device reported 36 live references and Fabric one outstanding history.
Those counts are evidence, not a budget, exception, or promise of stability.
The original raw launcher called its native-signature gate passed. The new launcher
instead reports errors/warnings explicitly and refuses to call that clean success.

## What is pinned

- Exact synthetic fixture bytes, UTF-8 with CRLF, SHA256
  `7e91da55105e78d9f34bea389c11009715111737f3fb816280988b4ab1aa9da7`.
  Git attributes preserve the bytes on Windows and Linux.
- Isaac4.5 SDK VERSION, Full/base app files and Kit app plugin hashes, plus selected
  extension versions. Vendor files are read and hashed, never copied or changed.
- The 426 actually started SDK/instrumentation extension IDs. The `matched-full`
  variant requires precisely the same inventory plus core/recast106.4.0.
- Owned portable profile, file-close route, public schema enable, fail-fast native
  containment, 240s host limit, persistent settings off, async rendering off and
  automatic multi-GPU off. These apply only to the owned child process.
- Original Kit series, Python/USD/GPU/driver observations. These fields do not
  constitute a complete native ABI fingerprint or imply other hardware is tested.

## Admission and execution

From a checkout, use the existing installed SDK and existing canonical shared
`$HOME/CodexSignals/Use-GpuLease.ps1`. It is not installed, copied or patched here.

```powershell
./tools/run_shutdown_profile.ps1 -IsaacRoot <existing-sdk> -Output <new-local-output> -DiagnosticProfile no-navigation
```

The outer script uses the official same lock and a maximum 1s acquisition attempt.
Conflict returns73; GPU-probe failure75. No retry, stale-owner overwrite, dummy
lease, force release or detached GPU process is used. An atomic grant is followed
by checks of the running owner/lease/ancestor PIDs, OS exclusive handle, no existing
Kit, idle resource envelope, and no unknown/unmanaged GPU client. Permission-hidden
clients must resolve to known desktop processes or admission fails closed. This is
cooperative process exclusion, not a driver-level GPU reservation.

Every native call to `run_in_app_validation.py` now requires the actual canonical
shared lease before output/host creation and rechecks it before suspended launch.
Calling an internal Python command directly outside that wrapper is refused.
SDK/fixture drift, wrong route, wrong lineage, a completed JSON record, another
Kit, unknown GPU work or an unexpected extension inventory cannot qualify.

The profile probe verifies actual core/recast enable state, core DLL presence or
absence, schema, startup dependencies and inventory before opening the owned file.
Stage event types are compared as integers and raw values are retained. Nothing
saves, clears pending edits, hides a save prompt by policy, or closes a user's app.

For a matched baseline, change **only** `-DiagnosticProfile matched-full` and
use a new output. Its navigation exclusions are empty; schema and other settings
stay fixed. Run only when the official wrapper admits it and no other work exists.
At the first native failure, contain only the owned Job and stop. Do not repeat a
known crash without a new hypothesis. The pending baseline has now been run once
under a verified shared lease; do not repeat it automatically.

| Owned SDK-only control | Checks / startup IDs | Native outcome | Cleanup qualification |
| --- | --- | --- | --- |
| Historical no-navigation | 13 / 426 | exit 0 | Failed strict cleanup: 82 error and 824 warning lines |
| Matched Full, included navigation | 14 / 428 | `0xc0000005` at `omni.anim.navigation.core.plugin.dll+0x18014`; owned Job contained, return 1 | Failed: 6 error and 334 warning lines before containment |

Both used the same fixture bytes, public close, schema and canonical exclusive
wrapper. The actual startup difference is only core/recast. The new Full probe
verified those modules enabled, core DLL loaded, CLOSING/CLOSED, all 14 required
checks, input preservation and empty/closed Job. Wrapper return 1, matching final
lease ID and a read-only post-return lock open confirmed natural release. The
smaller Full log is truncated by the crash, not evidence of better cleanup.

This strengthens navigation-path involvement under verified shared admission in
the matched run. One pair, changed extension ordering and no symbolized native
stack do not prove a unique cause. Review product code was not loaded in either
SDK baseline. Its added viewport texture teardown warning, repeated UI lifecycle
and full review acceptance remain separate issues.

## Results do not hide incomplete cleanup

`process-result.json` separates native exit, all probe checks, fixture preservation,
stage event order, navigation/inventory agreement, actual admission, owned root
reaping, Job emptiness/closure, log categories and strict clean-shutdown status.
Remaining owned descendants are contained, and that is explicitly **not** natural
success. The outer script waits for the foreground launcher/Job cleanup before
the official wrapper releases its handle. Do not cancel the outer lease first.

Exit 0 requires all conditions and no error/warning/traceback or known cleanup leak.
Exit 2 means native exit 0 and conditions met **with diagnostics still present**;
the official wrapper then records a failed child, rather than masking diagnostics.
Other failures return nonzero. Missing receipts and warnings are not suppressed.
The new stricter gate does not retroactively rewrite the historical SDK observation.
Raw logs and machine paths stay local; only synthetic inputs and sanitized facts
belong in this repository.

Windows CPU regression: 171 cases, 169 passed, two privilege skips, zero failures
(47.729s), including a real owned CPU-process Job count/reap check. The new
integrated profile launcher also ran the matched Full SDK control once and
correctly failed/contained its crash. Its reduced variant has **not** been
SDK-executed; that native observation used the earlier local instrumented launcher.
Product Full-host guard, user workspace and SDK remain
unchanged. Product-added viewport teardown, ghost/reopen/disable and full A/B
acceptance remain separate open gates. CPU tests are not GPU acceptance.
