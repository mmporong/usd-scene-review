# Distribution candidate work log

## Plan — 2026-10-20

1. Preserve the approved renderer/UI/media. Build a project-only, versioned candidate
   ZIP with a checksum manifest and an explicit no-license-selected notice.
2. Supply a minimal Kit experience, Windows launch/diagnostic scripts and a standalone
   public synthetic rack A/B fixture (before right, current left). Generate frozen
   snapshots and save deterministic JSON/HTML evidence without editing input scenes.
3. Run the extracted package from a new directory: diagnose, create the sample,
   compare, load the packaged extension, show A/B + ghost, save evidence, close the
   review and host with receipts/exit checks. Never attach to existing user apps.
4. Add CPU CI and regression coverage separately from manual GPU/GUI acceptance.
   Write Korean/English quick starts and support/release boundaries. Inspect ZIP
   contents for private data, logs, assets and vendor binaries; push the candidate
   implementation without merging or publishing a formal release.

## Initial findings

- Existing extension ZIP is deterministic, but lacks an end-user launch experience,
  diagnostics, sample workflow and distribution identity/checksum manifest.
- Current top-level README still gives a full-app acceptance command; the distribution
  quick start must use the qualified minimal Kit route and label full-app limits.
- Full Isaac shutdown fault is a parked vendor baseline issue, not a source fix or
  a reason to retry crash loops. License is not selected and will not be invented.
- This repository's draft PR is internal project review. External IsaacSim contribution
  candidates stay separate and are not a substitute for this distribution deliverable.

## Evidence / blockers

Implementation and terminal results will be appended after each bounded validation.
General open-source redistribution/reuse remains blocked on the maintainer's license
choice. Full Isaac application support remains unqualified independently of this kit.

## Implementation checkpoint

- Added a minimal Kit experience and owned-process launcher; initial diagnostic,
  checksum verification, sample, compare and bounded launch commands are implemented.
- Added a project-authored synthetic rack pair; it is independent of the private
  factory fixture. Added exclusive JSON/HTML export with input-bundle protection.
- Added versioned candidate assembly with payload hashes and a no-license-selected
  notice. Documentation/tests/archive extraction and actual GUI validation are next.
- The new distribution route has not yet been executed at this checkpoint. Existing
  prior GUI/CPU passes are not claimed as new distribution acceptance.
- MIT is awaiting the user's answer; no license has been chosen or included.

## First validation boundary

- Existing Windows SDK: Isaac Sim 4.5.0-rc.36, Kit 106.5.0, Python 3.10.15,
  OpenUSD 22.11, Pillow 11.2.1; RTX 3060 / driver 610.62 health query succeeds.
- CPU suite: 115 tests, zero failures, two Windows symlink privilege skips.
- First candidate extracted into a fresh path containing spaces. Verify, doctor and
  independent sample generation completed. Native distribution smoke: 11 checks,
  real A/B captures, negative Y delta, approved ghost, JSON/HTML export, bundle byte
  preservation; worker exit 0 and host exit 0. Actual pixels inspected.
- Added actual Save results widget coverage to the existing native regression.
  Extended final distribution smoke to quit with a reopened active worker as well.
- Draft PR remains open/draft; remote head was unchanged at 3bb29c0d. No review
  comments or CI checks existed before this work. License decision still pending.

## Regression and review boundary

- Final CPU suite after the shutdown fix: 116 tests, zero failures/errors, two
  Windows symlink privilege skips. The new cancellation regression prevents a
  delayed startup coroutine from overwriting an interrupted run with a false pass.
- Actual packaged-extension UI regression: 67 checks passed, host exit 0, four
  worker exits 0. Includes real Save results widget invocation, matching JSON/HTML,
  A/B switching/rendering, review metadata, close/reopen, disable/re-enable,
  active-viewer host quit, and source/default-stage/time/selection preservation.
- Independent code review approved. Lifecycle review found one pending-task shutdown
  issue; it was fixed, regression-tested, and the follow-up architecture review is CLEAR.
- Final corrected candidate archive: 32 payload files plus checksum manifest,
  66,394 bytes; no SDK/MDL binaries, logs or factory assets. Only the project-authored
  USDA pair is included. Fresh verify, sample and CLI compare already completed.
  The corrected candidate's active-worker host-quit GPU smoke is still running at
  this boundary; it must reach a terminal result before delivery.

## Final native candidate boundary

- Corrected fresh extraction: verify, sample, CLI compare and real minimal Kit smoke
  all passed. Twelve native checks passed, including actual A/B captures, matching
  camera, faint lime helper, before-right/current-left projection, negative Y delta,
  JSON/HTML export, preserved input bytes, close/reopen, then normal host quit with
  an active owned viewer. Host exit 0; both worker sessions closed with exit 0 and
  preservation receipts. No forced timeout/containment was counted as a pass.
- Candidate archive SHA-256:
  `750fbbca921506cd14bef14825164da9f40905fa3e6e4a866e1babd313713ba7`.
  Size: 66,394 bytes. The approved factory GIF remains byte-identical at SHA-256
  `adc50cd1c7ef2c1c17d3efb7ba51865436cda7b5f8c6d75c19714d520a6ba5fe`.
- Native evidence covers automated real UI/renderer workflows, including the actual
  Save results widget in the separate regression. Human interactive use and early
  manual window-close during GPU startup were not run; the early-close cancellation
  case has CPU regression coverage only. No general interactive certification claimed.
- Full Isaac shutdown was never rerun for this candidate. Other SDK/GPUs and production
  assemblies remain unqualified. License selection still blocks a formal licensed
  release. No vendor issue/PR, merge, release or distribution upload was performed.

## Post-run integrity finding

The previous GPU smoke passed render/save/exit, but post-run verify failed because
Kit embedded Python wrote bytecode inside the extracted package despite the process
bytecode environment flag. That archive is superseded, not the final deliverable.
The launcher now copies only the already verified small project payload into private
session/runtime before native launch. Native caches stay there. Final qualification
must include post-run verify and a second run from the unchanged original package.
