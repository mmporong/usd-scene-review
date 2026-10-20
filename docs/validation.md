# Validation status

## Current context-preserving review follow-up (2026-10-20)

This supersedes the earlier gray-context/material-replacement demo below. The apparent
missing factory context had two confirmed project causes: the display code overrode
all source material bindings with gray/selected colors, and automatic selected-prim
framing replaced the earlier wide overview with a rack close-up. The same saved factory
bundle was used; no geometry/visibility removal or missing asset caused this omission.

The corrected viewer preserves original geometry, material/subset bindings, display
colors, visibility and active state. Only owned outline helpers are blue/dashed before
and orange/solid after. Whole-scene union framing is the default; explicit Focus selected
is optional, with matching A/B camera/lens/clipping. Absent/unbounded selections do not
prevent the default whole-scene camera. A/B are labelled before/after saved scenes,
not error verdicts. Human dispositions and configured rules are separate.

Completed verification:

- Full CPU suite: 100 tests, zero failures/errors, two Windows symlink-privilege skips.
  This includes real-USD policy fail/unknown remaining unchanged after intentional
  records, exact snapshot/change identity invalidation, append history, reason limits,
  Unicode separators, capacity/corrupt/busy-log handling and source preservation.
- After the final IPC read fix, all 13 targeted transport/lifecycle tests passed,
  including transient and persistent read/replace access failures. The full suite was
  not repeated after this narrow read-retry change. Retries are Windows-only, bounded
  to 101 attempts/100 short sleeps, preserving complete old messages; persistent
  failures still propagate. No ACL or security-setting changes were made.
- Both actual factory snapshots have 1,386 original prims, 1,228 source geometry prims
  and 20 materials. Every source geometry binding/color/visibility/active observation
  was unchanged by display styling; source layer text/dirty, bundle bytes and original
  saved-assembly hashes were preserved. Actual wide and focus renderer frames were
  inspected to confirm full factory context and visible original material colors.
- Final actual minimal Kit factory recording: 30 checks passed, host exit 0, worker
  exit 0 with graceful close. Seven genuine UI/viewport capture pairs cover wide A/B,
  explicit focus A/B, actual local/world deltas, parent motion, explicit intentional
  reason save, change to needs-review, reload of both retained events, unchanged
  difference evidence, refusal recovery and restoring the whole-scene camera.
  Native widget actions/model callbacks were used, not mocked UI or invented values.
  Review reasons in the recording explicitly say DEMO; they are not operational approval.
- The extended synthetic multi-worker runner is checked in but was not rerun for this
  follow-up; the earlier 43-check run below belongs to the prior display implementation.
  This recording does not claim fresh coverage of all active-host-quit interleavings.

Earlier correction attempts are failures, not acceptance passes: one probe hit the SDK
zero-window-size input issue; another failed on an ambiguous checkbox query; one reached
all captured feature checks but timed out at 300 seconds before clean close (exit124).
Native Windows atomic-replace and request-read access races were also observed and
corrected with bounded retries. The final recording used a 480-second outer limit and
finished normally. Successful files are the final run only. Private raw logs and review
history are excluded from the repository.

The local review MVP is explicit human metadata, not authenticated approval, automatic
intent inference or policy waiver. Exact A/B manifest hashes plus full prim/change digest
bind each disposition. Changed inputs/evidence do not inherit old decisions; prior events
remain in history. Files are separate from immutable bundles. No multi-user authorization,
tamper-proof audit, collision, AI or operational safety sign-off is claimed.

**Full Isaac host shutdown remains FAILED / BLOCKED** by the independently reproduced
baseline SDK fault below. It was not rerun here. Minimal Kit success does not qualify the
full Isaac app. Runtime stays 4.5; no drivers, security settings, runtime upgrades, user
live scenes or unrelated running applications were changed.


## Current lifecycle investigation (2026-10-20)

Windows 11 Pro 25H2 / RTX 3060 12 GiB / driver 610.62 is healthy at read-only
startup checks. Existing Isaac Sim 4.5.0-rc.36, Kit 106.5.0, Python 3.10.15,
OpenUSD 22.11 were used. No driver/runtime installation, reboot or security change.

The earlier named review-context design failed real full-app teardown with
`0xc0000005` at `omni.usd.dll+0x86d60`. Project-free controls also failed after
engine release, reference cleanup and delayed updates. Retaining that context until
normal application shutdown also failed. Those results supersede any historical
claim below that successful buttons alone establish safe cleanup.

The candidate architecture keeps the host comparison UI and creates **no host review
context/timeline/viewport**. A separate Kit process owns its default context. It starts
suspended, joins an owned Windows Job, then resumes; IPC pins compared hashes and
requires ordered commands, a preservation receipt and actual exit code 0. Host disable
and quit use bounded synchronous cleanup, so host event-loop progress is unnecessary.
Kit 106 shader lookup also requires the SDK working directory; mutable run data remains
in a separate private directory supplied explicitly. Missing shader errors and a
Python import-scope startup error were detected and corrected during integration.

Completed checks:

- CPU: 89 tests run, zero failures/errors, two symlink privilege-related skips. Real
  Windows tests confirm immediate descendant containment, failed Job assignment
  retaining ownership, and synchronous graceful shutdown without host asyncio.
  Protocol tests cover stale identities, timeout/nonzero exit, failure acknowledgement,
  manifest pinning and unconfirmed termination retaining the owner. These are not GUI proof.
- Four actual CLI processes created two synthetic snapshots and repeated comparisons.
  JSON/HTML were byte-identical, two changes/one parent group matched, source hashes
  were unchanged. Project-only ZIP tests passed and include worker/engine sources.
- Two early standalone default-context worker prototypes rendered/closed cycles and
  exited 0 with `fastShutdown=false`; one switched the saved assembly A/B/A and framed
  its rack. These prototypes were not integrated extension acceptance.
- The final synthetic **full Isaac app** feature run passed actual native Compare,
  row filtering/search/selection, A/B/A framing, real captured lit geometry, close/reopen,
  disable/re-enable, default stage text/dirty/selection/time and snapshot preservation.
  Four integrated workers, including one closed by host shutdown while active, each
  produced preservation receipts and exited 0 normally. The synthetic image was
  inspected locally. A framing response alone was not treated as render evidence.

**FAILED / blocked:** after those checks and worker exits, the full Isaac host crashed
in `omni.anim.navigation.core.plugin.dll+0x18014` (`0xc0000005`) during normal SDK
shutdown. This is a different module from the named-context fault. The overall full-app
run is **failed**, even though its feature-check JSON says passed. Two normal integrated
full-app exits have **not** been achieved. A project-free full-host control, with the review extension never enabled, also
crashed at the same module/offset. This establishes a baseline SDK-host failure in
this installed build; it does not identify the DLL's internal cause. See the terminal
qualification note below. No fast-shutdown setting masks the outcome.

Earlier integration attempts are failures: missing capture output, startup timeout from
an import-scope error, and absent SDK-relative RTX shaders. They are not clean-exit or
render passes. Dedicated failed test processes/report dialogs were ownership-checked
before being stopped. Crash report dialogs had upload disabled; local raw dumps/logs
and private assembly images are not published.

**Not qualified:** production stress, arbitrary assemblies/resolvers, renderer modes
other than the tested synchronous mode, live robot/ROS sessions, host shutdown in every
native attach/frame/close interleaving, newer SDKs, animation viewport, clash, ghost or
AI-agent behavior. Source bundles must remain frozen. Full-application normal-exit
failure remains a merge/readiness blocker; code-review approval is not runtime approval.

See [contribution candidates](contribution-candidates.md) for draft own-repo work,
conditional Apache-licensed source contributions, and separate proprietary SDK reports.
No external issue or PR was submitted.

### Terminal qualification

The final saved static assembly run used the same 4.5/106.5 SDK in a **minimal Kit
host**, not the full Isaac app. It exercised 183 changed prims with 174 inherited-only
rows collapsed to 9 direct rows, actual row selection and A/B/A rack framing, a real
captured rack image inspected locally, absent-prim refusal, disable while the worker
was still starting, re-enable and host quit with a viewer active. The host exited 0
normally and all four workers had matching preservation receipts and exit 0. Original
three source files and all A/B/control/active bundle file hashes remained unchanged.
The private assembly image and raw machine data remain local. The public screenshot
is synthetic geometry only.

A second independent minimal synthetic run also passed: 34 acceptance checks, host
exit 0 and four worker exits 0, with `fastShutdown=false`. The factory run passed
33 checks. Both independent minimal runs reached terminal process outcomes; no
validation Kit process or crash-report dialog remained at the final process audit. Minimal-host
results do not turn the full Isaac host failure into a pass. Full app normal-exit
qualification remains blocked by the extension-free baseline fault. SDK graphics-object
reference warnings can occur even on exit 0; leak freedom and stress stability are not
claimed. Startup/attach/frame/close shutdown interleavings beyond the listed cases are
not exhaustively tested.

## Historical Windows baseline before full-app lifecycle investigation

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


## Light visual difference follow-up (2026-10-20)

The owned panel now uses a light background/dark text, persistent blue-before /
orange-after legend, actual attached revision label, and comparison-derived
before/after/delta observations. Actual selected geometry uses blue/dashed world
AABB bounds in A and orange/solid bounds in B; context is gray. A/B reuse an identical
union-bounds camera, lens and clipping. The viewer still renders one revision at a time.

- CPU: 94 tests, zero failures/errors, two symlink-privilege skips. Five new real-USD
  tests cover parent motion/local zero with centimeter-to-meter conversion, rigid pi
  quaternion sign and nonrigid refusal, anonymous material/subset overrides, source
  text/dirty preservation, outline reset, repeat camera, tiny clipping and finite
  overflow-to-unavailable. Existing policy semantics remain unchanged.
- Actual minimal Kit synthetic acceptance: 43 checks passed; host exit 0; four
  worker exits 0 with preservation receipts. Native buttons, A/B/A fixed camera and
  selected bounds styles, real viewport capture, absent/non-geometric refusal and
  recovery, close/reopen, disable/re-enable, active-viewer host quit and default
  stage text/dirty/selection/time preservation passed.
- Actual rendered saved-assembly recording: 23 checks passed, host/worker exit 0,
  six genuine UI/viewport capture pairs. The rack shows (0,0,0) to (0,0.2,0) m; a
  descendant shows local delta zero and world delta (0,0.2,0) m, with nonrigid rotation
  unavailable. Snapshot bytes and original saved assembly hashes remained unchanged.
- Visual inspection confirmed readable light panel, blue dashed/orange solid selected
  rack, gray context and matching A/B camera. The GIF is 1920 x 1000, 70 frames /
  14 seconds; private input paths are cropped. Global Kit chrome is unchanged.

Two earlier recording attempts failed in probe-only widget lookup APIs, and another
failed the probe's label query; they are not acceptance passes. The completed recording
and acceptance runs above use the final implementation. No AI or replacement scene
frames were used. Outlines are AABBs, not mesh edges or clash/clearance evidence.
Independent code review approved; architecture review is CLEAR after finite-range,
stale-highlight, tiny-clipping and non-geometric-refusal fixes.

Full Isaac host normal shutdown remains **FAILED / BLOCKED** by the independently
reproduced baseline SDK fault described above. It was not rerun for this UI follow-up;
minimal Kit success does not qualify the full application. No driver/runtime/security
changes, installations, reboots or unrelated live scene access occurred.
