# Validation status

## Windows Isaac Sim 4.5

The selected Windows target was checked on Windows 11 Pro 25H2, build 26200.9457,
Ryzen 7 5800X (8 cores / 16 threads), about 80 GiB RAM, RTX 3060 with 12 GiB VRAM,
driver 610.62. NVML and the native Kit graphics startup succeeded; the earlier Linux
driver mismatch does not describe this machine. No runtime installation, driver repair,
reboot or security setting change was performed.

Installed versions: Isaac Sim `4.5.0-rc.36+release.19112.f59b3005.gl`, Kit
`106.5.0+release.162521.d02c707b.gl.windows-x86_64.release`, Python 3.10.15,
USD 22.11, `omni.ui` 2.26.5, viewport window 107.0.8, viewport utility 1.0.18,
project extension 0.1.0. The extension version is distinct from the Kit version.

Implemented compatibility boundaries:

- USD 22.11 requires the time argument to `UsdProperty.GetPropertyStack`; the engine
  passes the declared sample. Window styles use `window.frame.set_style`.
- The helper uses process-local Windows DLL directories. Python 3.10 is accepted;
  its TOML test parser is already in the SDK. No package was downloaded.
- Resolver class-name checks were replaced by an explicit local contract. Absolute
  and anchored identifiers, Resolve results and actual Sdf layer paths must agree with
  the pinned files. Every composed layer must belong to that closure, except the owned
  anonymous session. Both current and stage resolver contexts are revalidated.
- URI/package/format-argument identifiers, changed mappings, unlisted/outside/anonymous
  dependency layers and symlinks/reparse points are refused. A real Windows junction
  regression caught `stat` following the target; checks now use `lstat`.
- Native attach resets source permissions in Kit 106. The viewport remains hidden
  until the anonymous edit target and read-only permissions are reestablished and
  verified. Camera opinions remain in the anonymous session; source files are not saved.
- A shared timeline caused native attach/close to rewrite the default stage's frame
  range/FPS metadata. Each owned context now has a named timeline, destroyed after
  context cleanup. The fix was verified against the complete original stage text,
  dirty flag, selection and nonzero paused time, rather than time alone.

CPU and command-line results:

- Final suite: 80 tests, zero failures/errors, two symlink-specific cases skipped for
  Windows privilege error 1314. The Windows junction case passed without security
  changes. Twelve resolver-boundary tests include real composed-layer injection and
  mocked resolution changes; mocks are not counted as native GUI evidence.
- Restricted execution stalled in Python's `socket._fallback_socketpair` during
  Proactor event-loop creation. A timed traceback identified it; tests completed in
  a normal process outside that sandbox. No OS setting was changed.
- Four actual CLI subprocesses created both fixture snapshots and two repeated
  comparisons: JSON and HTML were byte-identical, two changed prims and the parent
  group were correct, and source hashes remained unchanged.

Native acceptance:

A project ZIP was extracted into a new private extension folder and loaded by a
separate Kit process, using only synthetic Cube/DomeLight stages. The app uses
`app.asyncRendering=false` (also present in the installed Isaac base configuration)
and disables automatic multi-GPU selection. Thirty-eight native checks passed:

- Actual Compare/View button callbacks; A/B/A/B attachment; source permissions and
  anonymous edit targets; selection/framing; lit geometry rendering and PNG capture.
- Close, reopen and close again; changed/missing bundle refusal; valid semantic
  animation comparison at an explicit sample while animated viewport attachment is
  refused; recovery to static review after those negative checks.
- Unchanged snapshot hashes and default context/stage text/dirty flag/selection/time;
  cleanup of an attached stage on disable, restored source permissions and re-enable.

Private screenshots, machine logs and full native result JSON remain local. No user
scene or unrelated process was opened, edited, saved or stopped. Native test-held
adapter references can generate Kit leak-check warnings; owned context removal and
permission restoration are checked separately.

An inspected, synthetic-only [viewport screenshot](../examples/windows45-viewport.png)
is included as visual evidence. It contains no machine paths, user scenes or runtime binaries.

Limits: this establishes the listed synthetic path in the isolated Kit app, not the
full Isaac application, arbitrary custom resolvers, asynchronous rendering, production
assemblies, in-flight attachment disable/failure injection, or startup/stress stability.
A repeated native process run spent over 40 seconds in a native frame/attachment wait
with no Python frame, then completed all 38 checks and exited successfully at about
90 seconds. Startup latency and stress stability remain unqualified. No driver repair,
global renderer setting or user timeline workaround was used.

## Earlier Linux baseline (historical)

The results below predate the Windows edits and were not rerun after them.

Environment audit: Python 3.11.16, OpenUSD 24.05, Kit 107.3.3. Bundled pxr in-memory stage creation and transform calculation succeeded (exit 0). System Python 3.12.3 has no pxr. The inspected Isaac Sim installation has an RC VERSION marker; no public compatibility guarantee follows.

Actual Kit GUI: **BLOCKED / NOT RUN**. NVIDIA kernel driver 580.173.02 versus NVML 580.178 mismatch; execution session has no DISPLAY. No driver modification, reboot or guessed display/session is permitted. CPU tests cannot substitute for GUI validation.

## Historical product checks

- 63 stdlib unittest cases passed on Python 3.11.16 / OpenUSD 24.05: dependency closure/hash checks, missing and changed inputs, cached-layer mismatch, manifest mutation and invalid NaN, authored/effective and type/metadata changes, inactive versus removed, parent/reset behavior, rotation equivalence, rigid policy limits, deterministic reports, source bytes and dirty preservation, CLI output safety, deterministic extension archive structure.
- Actual CLI subprocesses created both fixture snapshots and JSON/HTML reports. Two separate compare processes produced byte-identical JSON and HTML. The fixture reported two changed prims with the child grouped under its moved parent.
- Python source AST/compile and project/extension TOML parse passed. The extension source was inspected against installed APIs; this does not verify native Kit imports or GUI behavior.
- The unresolved-reference negative test emits OpenUSD warnings by design and verifies unknown; raw machine logs are not published.
- No CI workflow added or claimed. No renderer, interactive Kit GUI, Windows or newer Kit verification performed.
- Local installed `extscache` and `kit/extsPhysics` inspection found no Clash extension. Clash remains an explicit unknown stub; no extension is downloaded or enabled.

## Historical pending work

Working GPU/authorized GUI session is required for installation, A/B switching, framing, timeline isolation and cleanup acceptance. Animated viewport review and static-mesh ghost are deferred. Real Clash integration and any geometry conversion require version-specific API and license checks. The project license remains undecided. This is an early implementation, not production-ready software.

## Historical post-review fixes

- Reproduced valid nested-prim and same-prim variant dependencies that alphabetical selection rejected. Parent-first/deferred selection now validates every requested set again after final composition. Mutually exclusive or unresolved configurations remain unknown; arbitrary cyclic choice search is unsupported.
- Stage close false/exception or a still-attached stage retains cache ownership, snapshot handles and layer protections. Compare/A-B/Close/framing are blocked, and shutdown does not destroy an unconfirmed context. Seven tests run the actual Python lifecycle methods with GPU-free boundary stubs; they do not verify NVIDIA native behavior.
- JSON/HTML creation uses exclusive mode. A regression test introduces a file or symlink after prechecks and verifies that it is not overwritten.
- Full 63-test suite passed again. Real CLI subprocesses accepted nested and same-prim variant configurations, produced byte-identical repeated JSON/HTML, and preserved the published dependency-only example bytes. The updated self-contained extension ZIP and source/TOML checks passed.
- GPU/GUI blocker and all pending GUI acceptance criteria above remain unchanged. System settings and existing source USD files were not modified.
