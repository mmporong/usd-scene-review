# Local transform / overlap / distribution work

Baseline: 46e88529e7edafe2d51f41da36bb0b224b29f529, clean working tree.
An unrelated FactoryOps Kit process was running and is excluded from this work.
No SDK, driver, approved preview material, lighting or camera changes are planned.

1. Add independent effective transform analysis, retain rigid-only policy, record
   unknown reasons and both-revision reset boundaries; validate common presentation.
2. Add point-derived static Cube/Mesh AABB candidates with explicit classification,
   coverage and bounded work; validate pair IDs and focus without fake changes.
3. Run CPU/native/export/preservation and fresh reproducible rc.3 candidate tests.
   Preserve rc.2. Distinguish test APIs from unavailable desktop mouse QA.

The initial implementation scope excluded publication. After validation the owner
separately authorized a scoped commit/push to the existing review branch. PR title/body
edits, merge, license choice and formal release remain excluded.
Stage findings and terminal results will be appended as they complete.

## Stage 1 checkpoint

Independent transform module/config implemented with no compare/measurements imports.
Rigid policy function AST is unchanged. Five regression groups pass (shortest 350->10,
180, quaternion sign, scale-only, invalid bases/translation, coordinate metadata,
A/B reset transitions and shared JSON/HTML/UI presentation). One initial fixture
assertion confused distinct authored entry filenames with effective motion; using
same-relative-name source layers corrected that test expectation.

Measured prior frozen assembly: all 162 legacy world rigid unknowns remain unknown
under the unchanged policy. Their separate normalized effective orientations are
known (162). Across all changed prims: 180 effective-known and three missing-matrix
unknowns, both local/world. All input bundle bytes were preserved. This is measured
coverage for that fixture, not a general guarantee that scaled matrices are resolvable.
Host save/review/view and worker now pin the same versioned configuration and complete
report digest. Stage 1 full CPU: 122 tests, no failures/errors, two Windows privilege skips.

## Stage 2 checkpoint

Point-derived Cube/Mesh candidates implemented independently of display bounds and
rigid policy. Explicit classifications, purpose/exclusion scope, numeric tolerance and
deterministic budgets are recorded. Pair selection is separate from changed prims;
the worker validates recomputed pair IDs and frames both objects over their A/B union.
Only moving pair members receive old-A ghosts. Shared rows feed JSON-derived HTML,
host UI and worker evidence; custom config/policy and report digests are pinned.

Read-only review found subset/context displacement, compensated parent attribution
and pair-refusal framing gaps. These were fixed with bounded regression coverage.
Normal ghost extraction now shares conservative displacement detection; green opacity,
original material handling, fixed light and camera algorithm are unchanged.

First CPU pass: 126 tests, zero failures/errors, two skips. First actual packaged Kit
run: 81 checks passed, host exit 0 and five worker exits 0, including new pair/ghost,
identity/export/preservation checks. Final reviewed CPU/native runs are tracked next.
These use Kit test APIs, not desktop mouse automation.

Frozen private assembly measurement: 1,228 geometry paths; known bounds A=1,207,
B=1,208; 753,378 pairs examined, 2,500 records, no budget exhaustion. Existing overlap
1,319; boundary/boundary 1,177; unknown/boundary four. No newly introduced overlap was
found in this fixture. A excludes 20 hidden and one unsupported geometry; B excludes
19 hidden and one unsupported. Auxiliary scan complete does not mean all bounds known.
All input bytes were preserved; semantic status changed and clash status unknown.

Public refs rechecked read-only: branch remains 46e88529e7edafe2d51f41da36bb0b224b29f529;
main remains c408fd24d5b3b4f30cf8c851992cc703c0cbcde5. No publication performed.

## Stage 3 terminal checkpoint

Final CPU: 131 cases, 129 passed, two Windows privilege skips, zero failures/errors.
Final packaged native acceptance: 86 checks passed, host exit 0, five worker exits 0.
Final extracted candidate smoke: 12 checks passed, host exit 0, both owned worker
closes normal with preservation receipts. Input/default-stage/dirty/selection/time
isolation, custom-config report identity, pair selection/focus, stale ID refusal,
export, reload, active-viewer host quit and retained .22 appearance were validated.
Two independent extracted CLI runs have byte-identical JSON/HTML.

An extra final boundary fix makes nonfinite stage metadata a serializable explicit
unknown; its real-USD regression passes. Final engine output exactly matches the native
custom-config/policy export. Rigid policy AST is unchanged. Final archive payload matches
current local source after canonical LF conversion and the original extraction verifies
again after native execution. No Kit processes remained after the owned tests.

Rc.3 final archive: 78,732 bytes, 35 payload files plus manifest. SHA-256
bc90862f3ee23844ec0636bf0e2dad8de785e8b9fbe161d48cbd417a4d17aac1.
Repeat build identical. Rc.2 unchanged. Earlier local candidate archives are superseded.

Failed intermediate attempts remain recorded: one renderer-capture teardown timeout
despite a preservation receipt, then one retained test-widget/reload lookup failure.
Native capture reference, pair-row ownership and test-handle/readiness cleanup were
followed by the terminal successful runs. The intermittent native hang's root cause
is not proven. Desktop mouse tests never ran (no native control API); full Isaac normal
shutdown remains a separate unresolved SDK baseline. No SDK/driver/security changes.
See analysis-validation.md for sanitized evidence. Changes were local and uncommitted
at this validation checkpoint, before separate publication authorization.

After the connection interruption, existing terminal receipts and archive hash were
rechecked read-only: native 86 passed (host/five workers 0), extracted smoke 12 passed
(host/worker 0, preserved true), CPU 131 OK/skip2. Matching Kit/validation Python
process count was zero. No validation command was duplicated after reconnection.
