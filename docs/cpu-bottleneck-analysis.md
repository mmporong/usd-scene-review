# Compare and selection CPU bottlenecks

The same saved synthetic inputs used in the [native two-scale QA](bounds-deployment-qa.md)
were measured with standalone SDK Python. At 2,048 Cubes, unprofiled Compare falls
from **34.65s to 16.81s** (51.5% less time, 2.06x). Canonical JSON and rendered HTML
SHA256 match before/after at both scales. This is CPU engine evidence, not a new
Isaac UI responsiveness measurement.

| Cubes | Compare before / after | Selection median before / after |
| --- | --- | --- |
| 32 | 427 / 433 ms | 92.9 / 96.1 ms |
| 2,048 | 34,649 / 16,812 ms | 459.0 / 466.7 ms |

One unprofiled Compare per size/version and 12 selections (first/middle/last/first
changed path, repeated three times) were timed. Separate cProfile calls establish
cost attribution; their overhead is excluded from this table. Baseline is main
3ddf0ff. Each version ran in a fresh process, small then large, using the same
existing bundles, SDK Python3.10.15/OpenUSD22.11 on Windows11 Pro, Ryzen7 5800X,
about 80GiB RAM. No Kit host or new GPU run was started. Cache/background CPU/clock
conditions were not controlled; these samples do not establish a general guarantee.

## Proven duplicate work

The original large Compare profile spent 47.94 of 53.41 profiled seconds in
`analyze_overlaps`: about 90%. It visits the same one-million-pair budget in the
same sorted order on both revisions. Repeated per-pair Sdf.Path construction,
object lookup and coordinate ULP calculation dominate that cost.

The fix lazily prepares each visited path once per invocation: its Sdf.Path, two
scan-object references and each finite known bound's maximum ULP. The original
per-pair relation arithmetic, ancestor exclusion, tolerance, classification,
IDs, ordering, record limits and coverage remain. Tiny pair budgets do not prepare
the unvisited tail. Unknown/nonfinite records retain the original fallback path;
recorded missing/blocked objects retain their original materialization behavior.
There is no persistent cache and no snapshot, resolver or file verification change.

On the measured large disjoint fixture, `_object` calls fall from 4,000,000 to
4,096 and coordinate ULP calls from 24,000,000 to 24,576. Pair relations still run
2,000,000 times. Coverage is still partial at the configured pair budget; AABB
overlap remains a candidate and collision/clearance remains unknown.

Selection is a different bottleneck: 12 profiled plans call verify 24 times and
resolution discovery 48 times. Fresh layer/structural/resolver checks dominate,
not the bounds drawing or file hash calculation. Removing or retaining their
results across selections could miss changed files or resolver state. These checks
are retained, so no selection-speed improvement is claimed.

## Reproduction and regression contract

`tools/viewport_bounds_scale_qa.py:build_scale` deterministically creates 32/2,048
half-unit Cubes with eight translations. To reproduce CPU attribution, create
each pair once, reuse those snapshot manifests in separate before/after processes,
time `compare(A, B)`, then profile a separate call with `cProfile.Profile.runcall`.
Load snapshots, select sorted changed paths at first/middle/last/first three times,
and time/profile `bounds_plan` plus shared `overlay_text` separately. Compare
`canonical(report)` and `render_html(report)` bytes across versions. Do not include
fixture creation or profiler overhead in unprofiled timings. Local raw profiles
may contain machine paths and must not be published.

The [sanitized measurements](../diagnostics/cpu-bottleneck-v1.json) retain samples,
profile attribution, source/code digests and output hashes. Reference goldens in
`tests/fixtures/overlap-reuse-v1.json` were captured from the original implementation:
they cover ancestor pairs, record/pair budgets, unknown/hidden/missing geometry,
metadata mismatch, numeric overflow and tolerance boundaries. Tests also mutate a
frozen file and demand unknown on the next Compare, and mutate per-call scan data
to reject stale reuse. Existing manifest/resolver tamper regressions remain active.

Final Windows CPU/package suite: 216 cases, 214 passed and two privilege skips,
no failures/errors (50.874s). It includes deterministic ZIP packaging and the
unchanged snapshot validation contracts.

Native UI timing, actual mouse input and long-session memory QA remain unmeasured
by this CPU follow-up. Previous strict-clean=false SDK shutdown diagnostics and the
Full/live A/B guard remain. This change does not qualify green mesh ghost or live
split review in the working Full app.
