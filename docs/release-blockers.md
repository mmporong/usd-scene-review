# Rc.4 release decision and remaining external evidence

**Do not promote rc.4 to a stable/general Full Isaac release.** The bounded
stage-free overlay remains an evaluation candidate with the documented callback
acceptance. This investigation changes no runtime, guard, error gate, SDK/driver
or global setting. It launches no Kit/GPU host. The rc.4 archive hash is unchanged.
See [workflow acceptance](deployment-workflow-qa.md), [sanitized evidence](../diagnostics/release-blockers-v1.json)
and the [manual acceptance checklist](manual-acceptance.md).

## One mouse-tool recheck

The exposed UI entry point `mcp__cua_repl.js` was called once with `cua.getState()`.
It failed before selecting an app or sending input: `failed to write kernel assets`,
Windows path-not-found `os error 3`. The tool did not return the affected asset path.
This is a tool-runtime failure, not an Isaac UI result or a permission denial.
No click, retry/reset, custom input helper or user-window manipulation was attempted.
The bundled Windows sky skill also requires node_repl, which was not exposed.
Actual mouse acceptance remains NOT RUN. A working UI runtime or a human operator
is required; callback validation is not a substitute.

## Rc.4 kvdb audit: facts and limits

The audit read 67 existing `console.log` files. Exactly one contained kvdb errors;
matching `kit.log` copies were not double-counted. Its two exact error messages are
`Unexpected key-value database error`, component `omni.kvdb.plugin`:

| Event in that process | Milliseconds |
| --- | ---: |
| kvdb error 1 | 13119 |
| kvdb error 2 | 24758 |
| First project extension startup | 25788 |
| Separate renderer PNG save failures | 37831, 38202 |

Both kvdb errors precede review activation. Detailed Kit logging places each near
PhysX initialization messages (`Using CUDA device ordinal 0`), not a project Python
traceback. Adjacency is not a call stack or proof that a PhysX operation caused it;
these initialization messages do not establish that Play or simulation was run.
No database filename, failing operation, native error code, lock owner or thread is
reported. The renderer's explicit PNG-path failures are a different signature.

The original project-free reduced baseline and the matched Full baseline both
started kvdb106.5.7 without this error. Earlier project-free Full and no-attach
controls also contain no kvdb error. Thus it is **not** a signature already present
in those baseline logs; it must not be dismissed as baseline noise. Absence in this
finite corpus is not proof the SDK never produces it elsewhere.

All three rc.4 controls used archive SHA256
`b4b6b94a19906e5bec4d940165f52d185d20e541b8a4ad772a246f3047767b26`,
located under the same Korean/space package path. Only the Korean **host-state**
control contains the two errors; both later ASCII host-state controls contain zero.
Portable state, local extension/fixture/output paths and timing changed together,
and the capture/getter harness corrections were separate differences. There was no
isolated cache-path-only A/B experiment. Unicode host-state handling is a plausible
correlation, not a demonstrated kvdb root cause. This does not invalidate the
separately passed CPU Unicode package/snapshot/report workflow.

All three rc.4 admissions recorded the canonical OS-exclusive GPU lease, no unmanaged
Kit/compute blocker, and 2099MiB used VRAM. Sampled GPU utilization was 7%, 6%, 4%.
These receipts weaken an explanation based on overlapping cooperating GPU tests.
They do not provide historical file-handle ownership, prove absence of other CPU
clients or exclude DB contention, permissions, disk or native initialization faults.
Current process state cannot reconstruct lock ownership at those past error times.

### Installed SDK surface

Installed relative files show this dependency chain:
`omni.physx.cooking -> omni.localcache106.5.7 -> omni.kvdb106.5.7`.
Kvdb's manifest marks it Internal. Its Python extension acquires/releases the native
interface; its supplied binding stub exposes no database operations or error/path
diagnostics. The native implementation is compiled, and the supplied changelog is
version bumps. No matching public error-code explanation or supported Python
diagnostic switch was established. This is the boundary of the inspected surface,
not proof that vendor diagnostic facilities do not exist.

No cache was deleted, interface unloaded, private binding patched, diagnostic error
reclassified as allowed, or SDK option guessed. A vendor trace that includes the
failed DB operation/path/error is needed to distinguish Unicode initialization from
contention or another cause. No upstream report has been sent.

## Full exit and live A/B are separate unresolved boundaries

| Boundary | Strongest existing evidence | What remains unknown |
| --- | --- | --- |
| Full baseline exit | Project-free matched Full under exclusive lease, public close and CLOSING/CLOSED crashes at navigation core DLL+0x18014; reduced core/recast-excluded control exits0 with diagnostics. | Unique native cause; a warning-free Full fix. The older tf.dll+0xec7b fault is a different recorded address, not a symbolized cause. |
| Named-context save-state preservation | Wait already creates the context/timeline but does not attach; pending stays false. Attach/open of a distinct owned stage changes default pending without root/session text changes. Minimal and reduced Full-derived hosts both reproduce it. | Native/shared callback ownership and whether the transition is intended; safe public isolation preserving a working user's save state. |
| Added native textures | Two SDK-only textures render; warning begins at the second updates-off call without added UI/ghost/material logic. | Private native lifetime cause and a safe supported close/reopen path. It is not proven to cause the unrelated baseline exit crash. |

Same-version official [named-context documentation](https://docs.omniverse.nvidia.com/kit/docs/omni.usd/1.12.4/Overview.html#how-to-create-another-usdcontext)
supports multiple contexts. The [UsdContext API](https://docs.omniverse.nvidia.com/kit/docs/omni.usd/1.12.4/omni.usd/omni.usd.UsdContext.html#omni.usd.UsdContext.has_pending_edit)
exposes pending save state and a setter; neither is a documented permission to reset
a user's state to make a test pass. Public API existence does not establish this
integration's preservation or cleanup. Current UI/API Full guard stays enabled.

## Experiment decision and handoff

No new GPU experiment was selected. Context-without-attach, attach versus open,
minimal versus Full-derived, normal/public close, navigation exclusion, delayed
texture teardown and native-only textures already have distinct controls. Repeating
them without a new discriminating observation would not remove a release gate.
The kvdb log has no DB identifier to target through its inspected Python surface;
randomly disabling internal/cache extensions or suppressing pending/errors is not a
safe product correction. No new project runtime defect was established here.

For a vendor-directed follow-up, reuse the existing [pinned profile and lease](shutdown-profile.md),
[attach/open controls](attach-only-control.md) and [native-texture reproducer](teardown-investigation.md).
Do not run the known crashing Full baseline simply to reconfirm it. Obtain a concrete
vendor-supported diagnostic request first, then use one owned synthetic host and
canonical admission; stop at the first native failure and retain normal-vs-contained
outcomes. Share only reviewed source/fixture and sanitized receipts, never raw
machine logs, SDK DLLs/dumps or user assets. Upstream contact remains unperformed.

The actionable next acceptance is the manual checklist, after a human-controlled
owned host is available. Whole-app clean shutdown and general live A/B additionally
need SDK clarification/remediation. License and production qualification remain
separate blockers; no version upgrade or security/driver change is authorized here.
