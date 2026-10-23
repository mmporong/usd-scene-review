# PR and contribution candidates

Research checked: 2026-10-20. This is a draft work list, not a submission record. No external issue, discussion, or pull request has been submitted for these candidates. Read [validation.md](validation.md) for the latest completed test results; terminal worker/minimal-host evidence is recorded there; full Isaac host normal exit remains blocked.

## Own repository

### Current disposition after the approved visual baseline

Items 1-4 below are implemented in draft PR #1, not new implementation candidates.
They now include isolated native review, normalized illumination, readable right-side
evidence, local human metadata and the user-approved green/lime old-pose helper with
an actual right-to-left demo. Historical wording below describes each original scope.
The capture-metrics import defect is fixed and retested without changing those visuals;
current terminal results belong in [validation.md](validation.md).

Item 5 (license) remains a maintainer decision. Items 6-8 are parked external research /
vendor candidates: no new upstream validation, submission, runtime upgrade or repeated
proprietary crash loop is authorized by this stabilization. The full-host baseline
crash remains a support blocker, not an actionable source-code fix identified here.
No current PR comments/reviews or CI results were present at the read-only check.

The next bounded implementation milestone is a minimal-Kit launch preset using the
existing isolated route and a public synthetic A/B example, with one documented local
launch/close smoke check. It should not broaden the renderer/geometry feature set or
claim full Isaac qualification. This milestone is proposed, not started here.

Target: [mmporong/usd-scene-review](https://github.com/mmporong/usd-scene-review). Proposed items can share a focused compatibility PR where their tests and ownership changes belong together. No merge readiness is implied.

### 1. Isolate native rendering from the host application

- **Problem:** destroying a previously rendered named USD context can crash the native SDK. Retaining it until application shutdown also failed normal shutdown, so retaining contexts indefinitely is not a qualified fix.
- **Evidence:** on Windows with Isaac Sim 4.5.0-rc.36 / Kit 106.5.0 / Python 3.10.15 / OpenUSD 22.11, named-context teardown produced `0xc0000005` at `omni.usd.dll+0x86d60`, including project-free SDK controls. Releasing engines, dropping references, and waiting for updates did not resolve it. Two minimal separate workers using their process-owned default context exited normally with `fastShutdown=false` and exit code 0; one exercised A→B→A and framing. Final integration later passed 33 factory and 34 synthetic checks in two normally exiting minimal hosts, with eight normal worker exits; the full host still has the separate baseline fault below.
- **Proposed change / target:** keep comparison and result UI in the host; move the native review viewport to a bounded child Kit process. Pin snapshot hashes, validate command sequencing, and require both a graceful shutdown receipt and the actual process exit result. Own only the spawned process and its descendants. Do not create another worker until termination is confirmed.
- **Tests:** integrate repeated Compare / A→B→A / frame / close cycles, extension disable and re-enable, normal host exit, worker failure and timeout paths, and source/default-context/selection/timeline preservation. Verify a real viewport, not just mocks. Check no worker remains after close.
- **Status / blocker:** implemented; CPU and integrated worker exits passed, but full Isaac host normal exit failed in a different native module. Keep the own-repo PR draft until the host blocker is resolved. This contains the SDK failure boundary; it does not repair `omni.usd.dll`.

### 2. Keep preview lighting inside the pinned review closure

- **Problem:** full-app automatic lighting can introduce an external SDK lighting layer into an unlit review stage, violating the pinned dependency contract.
- **Evidence:** the full application introduced `Default.usda` through the session. An owned anonymous, reference-free fallback light avoided that extra file; real USD lighting checks passed before worker integration.
- **Proposed change / target:** use anonymous preview-only lighting when needed, preserve authored lights, and keep all source layers unchanged. Relevant local coverage: [test_kit_lighting.py](../tests/test_kit_lighting.py).
- **Tests:** lit and unlit synthetic bundles, repeated A/B switches, closure verification, unchanged source hashes/dirty flags, and native worker render validation.
- **Status / blocker:** implemented; actual synthetic integrated worker image was captured and inspected. Full host shutdown remains blocked separately. Do not label cleanup or lighting changes as a native crash fix.

### 3. Make large change sets navigable and unknowns actionable

- **Problem:** a moved parent produces many descendant rows; nonrigid matrices or incomplete evidence can make a rule unknown even when an observed transform change is clear.
- **Evidence:** a bounded saved static assembly produced 183 changed paths, including 174 propagated descendants of one moved parent. Its semantic checks matched the expected paths; 162 configured policy results were unknown because the matrices were nonrigid/scaled. These are limitations to explain, not passing clearance checks.
- **Proposed change / target:** group parent propagation, add search and inherited-motion filtering, and show a concise summary with row navigation. Keep observed differences separate from rule verdicts, with specific unknown reasons. Preserve reset-transform boundaries and stable prim-path selection.
- **Tests:** synthetic parent/child and reset-transform cases, search/filter visibility, row selection and native framing, nonrigid/active-state unknown messages, deterministic offline reports, and no-change input.
- **Status / blocker:** implemented; actual native search/filter/result selection and A/B framing passed. Production-scale usability remains unqualified. The separate bounded static ghost is now implemented; collision, intent inference and AI agents remain absent. See [support.md](support.md).

### 4. Publish reproducible validation evidence with the compatibility change

- **Problem:** earlier CPU and synthetic checks did not establish safe full-app teardown. A visually successful session is insufficient when close or exit crashes.
- **Evidence:** 20 full-app interaction/preservation checks passed before the named-context teardown failure; clean exit and repeated disable/re-enable were not qualified. The pre-worker CPU run completed 84 tests without failures/errors, with two symlink-specific skips reported across a test and a subtest. These are historical results, not final worker results.
- **Proposed change / target:** update [validation.md](validation.md), the lifecycle/runner tests, and package checks with distinct passed, failed, skipped, and never-run results. Include runtime versions, bounded synthetic reproduction instructions, receipts and process outcomes; exclude private paths, assets, screenshots, raw dumps, and logs.
- **Tests:** documented CPU suite, deterministic JSON/HTML checks, ZIP contents/import checks, native extension load, actual row navigation, repeated lifecycle, normal host/worker exit, and preservation assertions on the final revision.
- **Status / blocker:** CPU/CLI and integrated native feature evidence recorded; independent code review approved. Full-app normal exit remains blocked, including an extension-free control. A packaged extension or mock test alone cannot establish that the native UI works.

### 5. Decide the project license

- **Problem / evidence:** this public repository has not selected a project license; public visibility does not itself grant open-source reuse rights. The [README](../README.md) records that limitation.
- **Proposed change / target:** maintainer chooses the intended license and checks ownership/third-party notices before a separate license/documentation change. Do not bundle NVIDIA SDK binaries or assets.
- **Tests:** review package inventory and notices against the selected terms after the decision.
- **Status / blocker:** maintainer decision required; no license is added by this candidate list. Keep this separate from the bounded compatibility fixes.

## Genuine open-source contribution candidate

### 6. IsaacSim source-side lifecycle regression coverage

- **Target / license:** [isaac-sim/IsaacSim](https://github.com/isaac-sim/IsaacSim), public `develop`. Its [LICENSE](https://raw.githubusercontent.com/isaac-sim/IsaacSim/develop/LICENSE) covers repository software under Apache 2.0 while distinguishing separately licensed SDK/assets.
- **Problem / evidence:** native viewport/context lifecycle failures can escape tests that only check load or frame output. Our reproduction is confined to installed Isaac Sim 4.5.0 / Kit 106.5.0. No current `develop` build or latest release reproduction has been performed, and no defect in an existing upstream Python module has been identified.
- **Proposed contribution:** after current-branch reproduction and maintainer scope confirmation, propose a small source-side regression test or lifecycle documentation in an appropriate existing extension. Author synthetic geometry from scratch, cover render → switch → close → normal exit, and distinguish application-owned default contexts from explicitly owned named contexts. Do not propose a binary patch or copy vendor implementation code. The exact extension/test module remains to be selected from current source with maintainers.
- **Policy:** the verified [external path policy](https://raw.githubusercontent.com/isaac-sim/IsaacSim/develop/CONTRIBUTING_PATHS.md) permits selected text source/document suffixes only under `source/extensions/`; manifests, infrastructure, assets, and binaries are excluded. The [contribution guide](https://raw.githubusercontent.com/isaac-sim/IsaacSim/develop/CONTRIBUTING.md) requires DCO sign-off, appropriate attribution, formatting, affected-extension tests, and targeting `develop`. A feature or public API proposal needs public maintainer scope confirmation before implementation.
- **Tests / status / blockers:** research candidate, not implemented or submitted. First reproduce on current supported source/runtime, identify a concrete allowed source target, agree scope where required, and run its Windows formatter/test launcher. A test that merely demonstrates a proprietary SDK crash may belong only in the vendor report below; it is not automatically an acceptable upstream source change.

## Vendor SDK report; not an open-source PR

### 7. Rendered named-context teardown access violation

- **Target:** NVIDIA Omniverse Kit SDK / `omni.usd` support, through the vendor's appropriate reporting channel. Related public API references: [destroy_context](https://docs.omniverse.nvidia.com/kit/docs/omni.usd/latest/omni.usd/omni.usd.destroy_context.html) and [release_all_hydra_engines](https://docs.omniverse.nvidia.com/kit/docs/omni.usd/latest/omni.usd/omni.usd.release_all_hydra_engines.html). These latest API pages do not establish a safe teardown ordering for the tested older build.
- **Problem / evidence:** the Windows 4.5/106.5 named-context pattern above fails in `omni.usd.dll`, including project-free controls. Empty engine enumeration, reference cleanup, and delayed updates did not prevent the fault. Application-lifetime retention survived repeated review cycles but still crashed during normal application shutdown. Default-context separate-worker prototypes exited normally; that does not establish the cause inside the binary or prove newer SDKs are affected.
- **Proposed report:** prepare a minimal synthetic script using a named context/timeline and viewport, render a simple local stage, close the stage and viewport, release owned engines, then destroy the named context and observe subsequent updates/normal shutdown. Include exact runtime versions, sanitized exception signature, ownership/ordering variants tried, and expected versus actual exit. Reduce and verify that standalone repro before submission; never attach the private assembly or raw dump by default.
- **Tests / status / blockers:** observed old-runtime failure; report draft only. A compact shareable synthetic repro and current-runtime comparison remain pending. Vendor confirmation is needed for supported ordering or a binary correction. No claim that an Apache-licensed IsaacSim source patch can repair this DLL.

### Public source is not necessarily open source

[NVIDIA-Omniverse/kit-app-template](https://github.com/NVIDIA-Omniverse/kit-app-template) is a possible vendor sample/documentation venue only after a concrete relevant defect is established. Its checked [LICENSE](https://raw.githubusercontent.com/NVIDIA-Omniverse/kit-app-template/main/LICENSE) references the NVIDIA Software License Agreement. Do not list it as an Apache 2.0 or OSI open-source contribution target, and do not invent an upstream defect from our application-specific workaround.

### 8. Full Isaac app baseline shutdown fault

- **Target:** proprietary NVIDIA SDK support, separate from any open-source PR.
- **Evidence:** the integrated synthetic feature run completed 33 native checks and
  four normally exiting review workers, then the full Isaac host failed normal
  shutdown with `0xc0000005` in `omni.anim.navigation.core.plugin.dll+0x18014`.
  A clean full-host control with this review extension never enabled reproduced
  the same module/offset. No user scene or original assembly was involved.
- **Proposed report:** a clean portable full-app startup/normal-exit script, exact
  installed versions, sanitized exception signature, and the control distinction.
  The fault occurs in a vendor DLL; its internal root cause is unknown.
- **Status / tests / blockers:** reproduced in installed 4.5/106.5 build; no external
  report submitted. Vendor-supported correction or independently qualified runtime
  is required before two clean full-host exits can be claimed. No upgrade or driver
  change was attempted. Raw dumps, machine paths and private assets stay local.
