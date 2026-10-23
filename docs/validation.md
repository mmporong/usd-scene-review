# Validation status

## Official ownership/reuse assessment, 2026-10-23

No failed teardown control was repeated for this phase. Installed SDK source shows
that the official window owns the same widget/texture path, whereas stage reopening
on one existing widget can reuse its renderer. Sharing an API or combining A/B
roots is not an independent simultaneous revision contract. See the
[API evidence, candidate limits and minimum interaction choice](viewport-reuse-assessment.md).

A synthetic sequential-capture candidate is retained only on the local
`experiment/owned-viewport-reuse` branch. Its CPU suite has 158 cases (156 passed,
two privilege skips), including separate same-path A/B pose/material/light data and
common camera fixtures. Its two-cycle official-window destruction/recreation and
GPU capture checks remain **NOT RUN** because other Kit work resumed. This is not
native acceptance. The executable candidate is not included in main; the product
runtime and its actual-host-verified guard are unchanged. Main receives only the
source-backed assessment and its packaged links from this phase.

## SDK-only teardown reduction, 2026-10-23

Six hypothesis-driven owned controls distinguish the project-free tf.dll shutdown
crash from the released-texture-interface warning. Serial widget destruction does
not avoid the warning. A native-only control with one owned context and two public
textures renders both, then warns inside the second update-stop call before any
UI/stage/context destruction. An async creation request gives the same warning.
An environment-isolated baseline retains `0xc0000005` at `tf.dll+0xec7b`.
See [hypotheses, limits and the minimal reproducer](teardown-investigation.md).

These controls fail qualification and their owned Jobs were contained. The setter
returned and no immediate device loss was observed; the warning alone is not proof
of double-free or universal failure. No failed ordering was applied to product code.
The verified Full Isaac guard remains unchanged. Clean close/reopen/disable and
normal app exit remain unqualified; no native repair is claimed.

Validated tooling changes add child-only Python path isolation, enforce fail-fast
containment for the native-only reproducer and include its diagnosis in packaged
docs. Final Windows CPU: **157 cases, 155 passed, two privilege skips, zero
failures/errors** (71.322 s). Repeated local ZIP builds match byte-for-byte; Python
compilation and packaged document links pass. Raw logs/dumps and SDK assets are
excluded. CPU CI does not qualify native lifecycle behavior.

## Full Isaac follow-up and verified guard, 2026-10-23

The guard correction is validated independently of the still-failing feature lifecycle.
A project-free Full Isaac baseline crashed on normal unload. Its dump and the
previous topology run both report `0xc0000005` at `tf.dll+0xec7b`, providing matched
baseline evidence distinct from the historical navigation-plugin error.

An actual Full Isaac feature attempt passed 27 checks (selection/focus/evidence,
camera synchronization, native Kit UI-test row click, rendered .22 green faces and
opaque control) and captured the real UI, then failed on a released Hydra texture
interface at the first review close. Fail-fast contained only the owned Job. Input
snapshot integrity and source/frozen-copy equality pass after termination; working
stage/settings restoration, repeat open/close, stage switch, active disable and
full feature host exit were not reached. This is not a clean integration pass.

The actual run exposed a filename-only Full-app guard detection defect: the SDK
returns `isaacsim.exp.full` without `.kit`. The correction also checks the enabled
Full experience and covers derived-app cases. Eight actual guard-only checks pass
on code commit `7c2aa00`: disabled button, extension and direct API refusal before
review/native ownership, preserved working stage/session/selection/time, and bypass
setting false. No A/B review was opened. The host still crashed at `tf.dll+0xec7b`
on normal SDK unload and its owned Job was contained; this is not a clean exit.
Serial texture-teardown diagnosis and full feature lifecycle remain incomplete.
No SDK/driver repair was made.

Final CPU: **155 cases, 153 passed, two privilege skips, zero failures/errors**,
73.140 seconds. See [precise evidence and remaining checks](in-app-sdk-diagnosis.md).

## Continuation, 2026-10-23 (CPU only)

Other Factory/Isaac GPU work was confirmed running; no new GPU host was launched
and no other process was changed. Full Isaac acceptance, current project-free
shutdown control, fresh captures and normal-exit qualification remain **NOT RUN**.
The previous three topology render/preservation results remain six functional
passes; their process/native result is still failed.

The previous log also contains released-Hydra-texture-interface warnings during
viewport cleanup, before app shutdown. The latest native crash has not been shown
to match the historical navigation-DLL baseline module/offset. See the corrected
[evidence and prepared baseline control](in-app-sdk-diagnosis.md).

Local changes shield pending render drains from cancellation, quiesce selection
on disable during pending attachment, and add granular teardown probe phases.
A project-free baseline mode is prepared, and a released texture interface now
fails native validation even if the process would otherwise exit zero. The full
app guard stays enabled. Final CPU regression: **152 tests, 150 passed, 2 skipped,
zero failures/errors** (69.955 s). An earlier invocation had one package-test import
error because the existing SDK toml archive was absent from that process path; the
final run supplied that bundled path without installing anything.
No SDK/driver/global settings, source scenes, public commits or pushes changed.
The fresh local unqualified extension ZIP is reproducible (438,822 bytes, SHA-256
`edbeb6222bfc88d746776687e6b62c81731f3a25ca6d9bf64473a206e8d85235`).
Extracted Python compilation, comparison of the public synthetic pair, integrity
checks and focus plans for 22 report paths passed. No native smoke is implied.

## Local in-app candidate (2026-10-22)

See [in-app review validation](in-app-review.md#actual-validation-2026-10-22) for the
new same-process split mode. Settled green surfaces and 36 functional minimal-Kit
checks passed with exit 0, but material/descriptor teardown errors remain. Full SDK
topology controls now render after first-frame/serialized-binding correction; full
host shutdown crashes and its product split route remains guarded pending acceptance.
Final serial CPU regression: 148 tests, 146 passed and 2 skipped. Full integration,
native teardown, exact layout restoration and desktop mouse QA remain unqualified. The prior worker
results below do not qualify this new route.

## Stabilization of the approved visual baseline (2026-10-20)

The user-approved green/lime helper, right-to-left demo, right evidence panel and
published GIF remain unchanged. The GIF SHA-256 remains
`adc50cd1c7ef2c1c17d3efb7ba51865436cda7b5f8c6d75c19714d520a6ba5fe`.

The auxiliary recorder's missing Image import is resolved by a shared
`tools/capture_metrics.py`, imported before measurement and copied beside the native
probe by the launcher. Both the checked-in probe and repaired factory recorder use it.
It rejects image-size mismatches, handles zero opaque baselines without inventing a
ratio, closes image handles, and records the exploratory quarter target as explicitly
non-gating. Pillow is declared only in the optional test extra; the qualified installed
SDK already provides it. No packages or runtimes were installed or upgraded.

Final-code results:

- 110 CPU tests: zero failures/errors; two Windows symlink-privilege skips.
- Checked-in packaged GUI acceptance: 65 checks passed, host exit 0 and four worker
  exits 0, including active-viewer host quit and source/default-stage preservation.
- Repaired auxiliary factory recorder: 23 checks passed, host/worker exit 0. Actual
  off/faint/wire-only/opaque images, right-to-left projection, negative delta,
  camera equality, review-summary refresh, snapshot preservation and graceful close
  completed end-to-end. This supersedes the previous missing-import probe failure;
  the historical failure below remains recorded.
- Whole-frame contrast ratio was 0.457802 (faint deviation 1.263760 byte, opaque
  2.760496). The exploratory 25% target remains unmet, recorded as false with
  `acceptance_gate=false`. The approved look was not altered to chase that metric.
- Read-only PR inspection found no comments, reviews or CI checks. Independent code
  and architecture reviews approved this scoped tooling change. No product renderer,
  UI, source scene or approved media changed; original saved-scene hashes still match.

Release boundaries remain: full Isaac normal shutdown is unqualified because of the
previously reproduced vendor baseline fault, and the project license is undecided.
No vendor issue was submitted and no full-host crash loop, runtime/driver upgrade or
security change was attempted. The contrast target is a disclosed measurement, not
a release blocker. Candidate disposition is reconciled in contribution-candidates.md.

Earlier entries below retain their historical results and limitations.

## Current green/lime hologram and reversed demo (2026-10-20)

The dense blue/transmission helper is superseded by 0.2% single-sided lime fractional
cutout faces and thin green Cube/Mesh control-cage edges, with emission/specular off.
The installed SDK supplies OmniPBR; no vendor template files are distributed. The
owned viewer's cutout setting is identical across A/B and off/control captures.

Private copies reverse the actual previous snapshot roles: old A is on the RIGHT at
(0, 0.2, 0)m, current B is LEFT at (0, 0, 0)m; delta (0, -0.2, 0)m. Selected geometry
centers project horizontally to +0.011854 and -0.012199 in the same camera. Geometry,
manifest/change identity and comparison values agree; no pixel mirroring/relabeling.

- Final CPU: 107 tests, zero failures/errors, two symlink-privilege skips.
- Final packaged GUI acceptance: 65 checks passed, host exit 0 and four worker exits
  0. Actual green pixels, cutout readback, bounded wire cues, A/B/camera, review-panel
  metadata, close/reopen, disable/re-enable, active-viewer host quit and host-stage /
  snapshot preservation passed. Original materials remain; original hashes match.
- Five factory UI/viewport pairs include off, faint faces, wire-only and opaque
  controls, all with stable capture flags. The auxiliary recorder passed 12 checks
  before a missing Image import in post-capture statistics ended it with exit 1.
  That probe is FAILED, not a native SDK crash or an overall acceptance pass. A
  separate saved-frame/OpenUSD check verified all five captures, signed values,
  camera projection, snapshot/private-copy bytes and original saved-scene hashes.
- Actual and decoded images were inspected: current/context materials remain visible,
  old-position cues are thin green, and evidence text is readable. The GIF has three
  native states (A, B off, B plus ghost), 30 frames / six seconds at 1560x860. Only
  outer desktop margin is cropped; private paths/assets/logs are excluded.

The exploratory quarter-of-opaque whole-frame deviation target was NOT met. Against
wire-only, faint-face mean RGB deviation is 1.28583 byte versus opaque 2.77168, ratio
0.463916. This metric is not shader alpha and does not isolate temporal lighting/edge
effects. No 25% contrast-reduction, photometric or shadow-free claim follows. Earlier
candidate controls failed bounded settling/combined-edge checks; they are not passes.
Declared face opacity is 0.002; thin edge cues deliberately remain opaque with depth
occlusion. This is a visual review style, not a physical transparency measurement.

The supplied Library reference could not be materialized: its supported helper needs
unavailable Windows extended attributes, and no local file was created. Previously
published GIF pixels were inspected instead, as permitted. Full Isaac baseline shutdown
remains separately FAILED/BLOCKED and was not rerun. No drivers, security settings,
runtimes, original scenes or unrelated apps changed. Earlier sections are historical.

## Current old-A overlay, evidence panel and illumination (2026-10-20)

Windows 11 / RTX 3060 / installed Isaac Sim 4.5, Kit 106.5.0, Python 3.10.15,
OpenUSD 22.11. No runtime, driver, security-setting or source-scene changes.

- CPU suite: 107 tests, no failures/errors, two Windows symlink-privilege skips.
  New real-USD cases cover complete ancestor/nonuniform-scale/reset transforms,
  mesh normals/orientation, no copied physics/references, helper removal, source text
  preservation, unsupported geometry/animation/guide/skeleton, session lighting and
  ancestor local-zero/world-motion evidence with an intentional human decision while
  independent policy still fails and clash stays unknown.
- Actual packaged-extension minimal Kit acceptance: 63 checks passed, host exit 0,
  four worker exits 0. This includes real A/B/A, fixed camera, ghost off/on rendered
  pixels, stable captures, the actual right evidence panel, human metadata reload,
  refusal recovery, close/reopen, disable/re-enable, active-viewer host quit and
  host default-stage text/dirty/selection/time plus snapshot-byte preservation.
- Additional actual synthetic/factory capture run: 28 checks passed, host exit 0,
  both worker sessions closed normally with exit 0. The factory old-A overlay has
  162 shapes, matching A/B camera and stable child frames. Standalone Reload review
  clears child metadata. Actual delta is (0, 0.2, 0) m; source appearance changes are
  disclosed. A real opaque control confirms background contribution through the
  translucent helper in 5,368 qualifying pixels (not just an opacity attribute).
- Both original factory snapshot bundles and all three original saved-scene files
  retain their verified hashes. The public GIF is six seconds, 30 decoded frames,
  two actual native A/B states at 1560 x 860. Only the outer desktop margin is
  cropped; the complete viewport and right evidence window remain. No generated
  scene pixels, substituted numbers, private paths, assets or logs are included.
- Failed attempts are not passes: the first recorder copied a swapchain PNG before
  asynchronous capture had completed; the completion wait now verifies the file.
  One full acceptance run launched concurrently with the recorder timed out during
  child RTX shader compilation (the log was still waiting after 70 seconds). The
  subsequent standalone acceptance completed all 63 checks with normal exits.
- The earlier full Isaac host normal-shutdown baseline native fault remains separately
  FAILED / BLOCKED; it was not rerun or repaired. Minimal Kit success does not certify
  the full app or production/animated assemblies. License remains undecided.

Illumination diagnosis used eight actual matched-camera viewport captures at early
and settled child-frame counts plus effective settings and raw source observations.
Both revisions had no authored lights and the same fallback white dome. Auto exposure
was already false; renderer was RaytracedLighting, ISO 100, exposure 0.02, f/5, ACES.
The persistent background difference is authored: WestWall visibility changes from
inherited to invisible; shared Steel roughness changes from about 0.32 to 0.42.
Initial frames also changed before settling (the earlier helper waited host frames,
not child renderer updates). This does not establish an exposure bug or justify
undoing source edits. The normalized preview locks illumination/exposure and settles
actual child captures, while retaining/disclosing source appearance changes.

Earlier entries below are historical and describe their stated implementation/run.


## Concise comparison media edit (2026-10-20)

This media-only edit replaces the seven-state demo with the two genuine selected-rack
close-up captures (source indices 3/4) from the successful 30-check minimal Kit run below.
It starts directly before A → after B, fixed camera, full original viewport/materials,
and an enlarged actual-UI world-position before/after/delta strip. Duration is 6 seconds,
30 frames at 1440 x 960. Every encoded frame was decoded and representative A/B frames
were inspected. No application code or functionality changed, and no new Kit run was
claimed for this edit: the reused source run has observed host/worker exit 0. Original
saved assembly and immutable snapshot hashes were rechecked after editing.

Removed storyboard scenes 1–3 were the distant whole-factory A/B views. Old scene 6
selected the lower FrontBeam_0 child to show local-zero / ancestor-propagated world
movement. Its orange horizontal shape was the selected beam's world AABB outline.
Old scene 7 showed separate human disposition/reason save/reload. These app features
remain implemented; they are omitted from the concise comparison media.

The old lower dark UI strip came from a crop extending below the actual 900px window
into background/shadow (the overflow frame height was used). The thin full-width footer
line was explicitly drawn by the encoder. Neither was a timeline/progress indicator.
The concise edit removes these and nonessential controls/path bands without altering
actual scene pixels or numeric evidence. Runtime/support limitations below remain.


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


## Distribution candidate 0.1.0-rc.1 (2026-10-20)

The versioned project-only candidate adds existing-SDK diagnostics, checksum verification,
new-workspace public synthetic sample generation, compare/export, a minimal Kit launcher,
and English/Korean quick starts. No runtime or vendor assets are bundled or installed.

- Windows SDK CPU: 117 tests, zero failures, two symlink privilege skips.
- Packaged native extension regression: 67 checks, host exit 0, four worker exits 0,
  including actual Save results widget, source/default-context isolation and lifecycle.
- Fresh extracted candidate: 12 actual native smoke checks, A/B render captures,
  before-right/current-left projection and negative delta, unchanged snapshot bytes,
  matching JSON/HTML, close/reopen and normal host quit with an active owned worker.
  Host exit 0 and both worker sessions exit 0 with preservation confirmed.
- The final archive verifies again after native exit; repeated native launches from
  the unchanged package also passed. Runtime copying uses a validated file allowlist
  and rechecks hashes before launch. LF/CRLF checkout differences are normalized.
- Two same-toolchain builds are byte-identical; archive privacy/type audit excludes
  SDK binaries, MDL sources, private assets and raw logs. Existing approved GIF unchanged.
- GPU smoke is separate from CPU CI. Human interactive/early manual window close,
  other SDK/GPUs, production assemblies and full Isaac normal shutdown are unqualified.
  Early startup cancellation has a CPU regression; it is not a claimed native pass.

See [distribution work log](distribution-worklog.md) for review findings and archive
identity. License selection remains pending; this is not a formal release. No system
or driver/security settings, unrelated apps, scenes or unsaved work were changed.


## Visible translucent faces, rc.2 (2026-10-20)

The latest feedback replaces the edge-led 0.2% surface setting. Actual installed
RTX face-only controls selected 22% green fractional opacity with background geometry
still visible, and half-width secondary lines. The final image/GIF/close-up use the
same production-default captures. See [material evidence](translucent-face-validation.md).

CPU: 117 tests, no failures/errors, two Windows privilege skips. Actual native checks:
26 material controls, 14 final media, 67 packaged UI regression and 12 exact rc.2
extraction smoke; successful host/worker exits 0 and source bytes preserved. The
extracted original package verifies again after Kit exit. Archive SHA-256 is
`6ca6c98f694e1a4cf14c42617b67e3a55e38d5665fe155b1e678bd3de6b9a4b6`,
66,872 bytes. Known failed/incomplete intermediate attempts and their limits are
recorded in the material evidence; they are not acceptance passes.

The initial commit/push was denied before execution while authorization was pending.
The exact repository/branch/code/docs/media publication was subsequently authorized.
CPU CI is checked at the exact published SHA and reported with its terminal receipt;
it does not qualify native GPU behavior. License and full Isaac shutdown limits remain.

## Local effective-transform / static-AABB rc.3 validation (2026-10-21)

The separate local analysis work is documented in [analysis validation](analysis-validation.md).
Terminal evidence: CPU 131 cases (129 pass, two privilege skips), actual packaged Kit
86 checks with host/five workers exit 0, final fresh rc.3 extraction smoke 12 checks
with normal shutdown and preserved inputs/package, deterministic CLI JSON/HTML and
reproducible ZIP. Rigid policy stays unchanged, auxiliary AABB candidates are not
collision confirmation, and unknown/partial scope is explicit. Two intermediate failures
are retained in that record; desktop mouse QA never ran and full Isaac shutdown remains
unresolved. Rc.2 is preserved. The reviewed code/tests/docs were subsequently authorized
for the existing public review branch; main merge and formal release remain excluded.
