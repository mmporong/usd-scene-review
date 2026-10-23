# Effective transforms and static AABB candidate validation

Implementation and local validation began on branch `fix/factory-review-lifecycle` at
`46e88529e7edafe2d51f41da36bb0b224b29f529`. Remote branch and main
(`c408fd24d5b3b4f30cf8c851992cc703c0cbcde5`) were checked read-only.
After validation, the owner separately authorized publication of the reviewed code,
tests and documentation on that existing branch. PR metadata changes, main merge,
license selection and formal release remain outside this work.

Windows 11 Pro 25H2, Isaac Sim 4.5.0-rc.36+release.19112.f59b3005.gl,
Kit 106.5, Python 3.10.15, OpenUSD 22.11, Pillow 11.2.1, RTX 3060 12 GiB,
driver 610.62. Read-only SDK/Python/GPU diagnostics succeeded. SDK, driver,
security configuration and unrelated user scenes/processes were not changed.

## Implemented and checked

`analysis_config` pins deterministic versioned settings. Independent
`transform_analysis` interprets local/world normalized effective orientation and
unsigned axis magnitudes without changing rigid-only policy. Translation validity
is independent; cross-revision deltas require matching valid units/up axes.
Reset-stack dependency boundaries are considered in both revisions, and compensated
parent/child motion is not grouped as world propagation.

`overlap_analysis` uses static Cube vertices / Mesh nonhole face control points,
never authored extent or subtree display bounds. Known disjoint A to overlap B is
distinct from existing/resolved/boundary/added/unknown-baseline cases. Purpose,
exclusions, meter tolerance, budgets and coverage are explicit. Same-parent geometry
pairs remain eligible. Unsupported/deformed/hidden data is not a new collision.
Material displacement is checked on geometry and subsets across material purposes
allPurpose/full/preview and all displacement output contexts; ghost extraction shares
the same conservative detector.

Pairs are separate UI selections, never synthetic changed prims. The worker validates
pair IDs against its recomputed report. Both objects share an A/B union camera from
actual point bounds; unknown bounds refuse focus, retaining whole-scene framing when
available. Stationary members have no fabricated old-A ghost. Shared evidence rows,
custom configuration, policy and the complete report digest agree across host, worker
and JSON/HTML exports. Human intentional decisions do not alter evidence or policy.
Opacity 0.22, approved green faces/edges, original materials and fixed lighting/camera
algorithm are retained.

## Measured frozen assembly coverage

All 162 previous nonrigid world-policy unknowns remain unknown under unchanged rigid
rules. Their independent effective orientations are known for this fixture. Across
changed prims, local/world effective coverage is 180 known and three missing-matrix
unknowns. This does not establish that arbitrary scaled matrices are interpretable.

The auxiliary scan examined 1,228 geometry paths and 753,378 pairs, with no exhausted
budget. Known bounds: A 1,207, B 1,208. A exclusions: 20 hidden, one unsupported type;
B: 19 hidden, one unsupported type. Recorded candidates: 2,500, comprising 1,319
existing overlaps, 1,177 boundary/boundary and four unknown/boundary. No newly
introduced overlap was found in this fixture. Remaining pair outcomes are explicit
disjoint/unknown classifications. Complete scan means work completed within its
declared scope; it does not mean all geometry has known bounds. Semantic status remains
changed, clash status unknown, and every input bundle byte was preserved.

## Regression evidence and limits

The first full CPU runs passed 122, then 126 cases; subsequent reviewed passes reached
130. Two Windows symbolic-link privilege cases are skipped without changing security
settings. New real-USD regressions include 350 to 10 degrees, 180 degrees, quaternion
sign, scale-only, reset/parent compensation, shear/reflection/singular/NaN/ill-conditioned
bases, metadata gates, misleading authored extent, same-parent pairs, missing/hidden
baselines, Mesh topology, material subsets/contexts/purposes, budgets and tolerance.

First actual packaged Kit acceptance: 81 checks passed, host exit 0, five worker exits
0. A later attempt failed normal worker exit: the preservation receipt and close
acknowledgment existed, but process exit timed out with the log stopping during renderer
capture teardown. This is a failed close, not a pass. A retained native capture-interface
reference was subsequently dropped; the root cause of that intermittent native hang is
not proven. The next run closed three workers normally and passed the new feature checks,
but failed the reload widget lookup. Its test retained a pair widget handle and found
two same-named windows. Test handles and owned pair row resources were released, and
bounded widget readiness waiting was added. Final rerun results are recorded below.

Actual native checks use Kit `ui_test`/API input and renderer pixels. Desktop mouse QA
was never run: this execution environment exposes no native desktop control API. The
full Isaac application's independently reproduced baseline shutdown fault remains
unresolved and was not retried. Neither mock tests nor minimal Kit acceptance qualify
that application or a production collision/clearance workflow.

Rc.2 is preserved with SHA-256
`6ca6c98f694e1a4cf14c42617b67e3a55e38d5665fe155b1e678bd3de6b9a4b6`.
Rc.3 is a separate local evaluation candidate, not a formal release. Older intermediate
local archives/runs are diagnostic evidence and are superseded by the final reviewed
candidate. No private factory/SDK assets, paths or raw logs are in the candidate payload.

## Terminal results

- CPU: 131 cases, 129 passed, two Windows symbolic-link privilege skips, no failures or
  errors. The last boundary regression confirms USD accepts NaN meters-per-unit and
  the report still exports explicit serializable unknown JSON/HTML.
- Actual packaged minimal Kit acceptance: 86 checks passed, host exit 0 and five
  worker exits 0. This includes real pair-row selection, custom tolerance/config/policy,
  recomputed report digest, A/B pair union framing, invalid pair on fresh A attachment,
  moved-only ghost, export equality, intentional metadata isolation, reload and shutdown.
  The final engine reproduces that native custom-configuration export exactly.
- Final rc.3 clean extraction: 12 actual smoke checks passed; host exit 0, normal
  worker closes, preservation receipt true. A/B captures settle, camera matches,
  approved green opacity remains 0.22, and source/sample/package integrity is retained.
- Two independent final extracted CLI runs produce identical JSON and HTML bytes.
  JSON SHA-256: `7bdcf5d7d7d425bbf2b20ec310e68968932d8ac9f9fec7d2a8ceaf5d604e5b49`;
  HTML: `691a931890db823671fb06e84dc1b5228c46508a3841be076b777076b7d064da`.
- The final ZIP and a separate repeated build are identical. Version 0.1.0-rc.3,
  78,732 bytes, 35 payload files plus candidate manifest, SHA-256
  `bc90862f3ee23844ec0636bf0e2dad8de785e8b9fbe161d48cbd417a4d17aac1`.
  An audit confirms exact canonical payload equivalence to the final local source,
  unchanged rigid-policy function AST, preserved rc.2 and original extracted-package
  verification after Kit exit. No owned Kit processes remained after validation.

The two intermediate failures above remain failed evidence. Subsequent passes do not
prove the root cause or universal elimination of the intermittent renderer-capture
shutdown hang. Desktop mouse QA remains never run; full Isaac shutdown remains a
separate unresolved baseline limitation. No system repair, runtime install or hidden
reclassification of those limits occurred.

Changed scope: three independent analysis/config modules; compare provenance and
metadata serialization; shared numeric/HTML/evidence presentation; host/worker/client
identity and pair selection; anonymous pair outlines and conservative ghost exclusions;
two new CPU test modules and extended native probe; candidate launcher/version and
support documentation. Public sample geometry, approved opacity/color, lighting and
camera algorithm were not changed.
