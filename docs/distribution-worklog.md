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

## Intermediate native candidate boundary (superseded)

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

## Cache isolation and reproducibility boundary

- The corrected launcher materializes only the verified project payload in private
  session/runtime. Its native smoke passed and the original package verifies again
  after normal shutdown. No system installation or cache cleanup is needed.
- GitHub CPU CI for implementation commit 34b01ff passed both push/PR events.
- Canonical LF payload serialization now removes Git autocrlf differences. A regression
  builds LF/CRLF variants and requires byte-identical archives. All six distribution
  tests passed after this bounded packaging change.
- Final portable archive identity (supersedes all earlier preview archives):
  `b5e002a139d5bf687ee6a141a816ebb182c8419527511d655802deb70465fd09`,
  66,442 bytes. Independent rebuild is byte-identical. Final native repeated-use
  acceptance remains pending at this checkpoint.

## Final review boundary

- Independent review identified that whole-tree copying could follow an unlisted
  directory link. Replaced it with manifest-file-only copying and a full hash
  verification of the private runtime before native launch. No unlisted directory
  is copied. A regression injects corruption during copy and requires refusal.
- The first new full CPU attempt had one test-fixture root-binding error (117 tests,
  one error, two skips); the explicit verify(ROOT) call fixes it. All seven targeted
  distribution tests then passed. Final full CPU rerun is pending at this boundary.
- Two native sessions from the same earlier canonical package both passed, and its
  post-run original-package verification passed. The manifest-only copy candidate
  also passed native acceptance. The final reviewed archive is now isolated under
  deliverables/reviewed; its exact-byte native acceptance is pending here.
- Final reviewed archive SHA-256:
  `01003fa832166444d4e3278601a4f62f20b87542516ccf09b25b888ed3adf921`,
  size 66,558 bytes. Earlier preview archive identities above are historical.
- Final code follow-up is approved; terminal validation is kept separate from review.

## Completed deliverable

- Final reviewed archive: 66,558 bytes; SHA-256
  `01003fa832166444d4e3278601a4f62f20b87542516ccf09b25b888ed3adf921`.
  A second independent build is byte-identical. The exact final archive's fresh
  extraction passed all 12 native smoke checks; host exit 0, both worker sessions
  exit 0 with preservation confirmed. Post-native original-package verify passes.
- Final Windows CPU rerun: 117 tests, zero failures/errors, two privilege skips.
  The earlier root-binding regression failure is corrected and is not a pending blocker.
- Real native extension regression remains 67 checks, host exit 0, four worker exits 0.
  CPU CI and installed GPU results are separate; CI does not certify native rendering.
- Known failures fixed in this task: Kit cache mutation on original extraction;
  unfinished bootstrap work after shutdown; unlisted-directory whole-tree copying;
  test-only default-root binding. Intermediate attempts remain historical above.
- Never-run/unqualified: human interactive use and manual early-close during GPU
  startup; other SDK/GPU combinations and production assemblies; full Isaac shutdown
  (previous independently reproduced vendor crash, not retried). License choice is
  still pending. These limits remain visible in support and quick starts.
- All newly owned native acceptance processes reached normal terminal outcomes.
  Unrelated existing apps/scenes were left alone. No vendor submission, merge,
  ready-for-review transition, formal release or public archive upload was performed.
- Next milestone: maintainer selects a license, followed by bounded human first-run
  acceptance on the same qualified minimal Kit path before any licensed public release.

## New visual request supersedes prior appearance approval

The completed distribution baseline above is preserved separately. The latest user
feedback requests visible translucent green faces/volume rather than effectively
edge-only 0.2% faces. License remains undecided. Next work compares actual installed
Isaac Sim 4.5 RTX material behavior, retains white background/original surrounding
materials/fixed exposure/camera and old-right/current-left, then updates consistent
image/GIF/package evidence. Previous distribution passes are not claimed for the new
visual revision until revalidated.

## Translucent-face follow-up completed locally

Latest feedback superseded the 0.2% edge-led appearance. Actual installed RTX face-only
controls selected green opacity 0.22 with zero threshold, no texture/emission/specular,
and half-width secondary lines. See translucent-face-validation.md and final matching
image/GIF/close-up metadata. Native controls: 26 checks; production media: 14 checks;
packaged regression: 67 checks; exact rc.2 extraction smoke: 12 checks. Successful
hosts/workers exited 0 and inputs were preserved. Full Windows CPU: 117 tests, two
privilege skips, no failures. Final rc.2 archive: 66,872 bytes; SHA-256
`6ca6c98f694e1a4cf14c42617b67e3a55e38d5665fe155b1e678bd3de6b9a4b6`.

Automatic approval review denied the combined commit/push before execution because
remote mutation was not considered explicitly authorized in the delegated request.
No workaround/retry occurred. Changes and artifact are local and reviewable; rc.2
remote CI has never run. Approval to commit/push the existing draft branch is the
remaining publication action. Prior rc.1 baseline is preserved at commit 219fec5.
License choice is still pending; no MIT/license or formal release was created.

## Publication authorization received

The owner approved committing/pushing the reviewed code, docs and corrected images/GIF
to mmporong/usd-scene-review, fix/factory-review-lifecycle. The prior denied combined
command was confirmed not executed. Remote URL, branch and unchanged baseline 219fec5
were verified read-only before the authorized retry. No material setting is changed.
Exact-SHA CPU CI and public-link verification follow the successful push. Merge,
formal release and license selection remain excluded.
