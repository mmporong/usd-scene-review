# Stage-free overlay deployment QA

Real mouse testing was **unavailable**: no screen/mouse-control tool was exposed.
The results below exercise actual Isaac UI callbacks and rendering, not mouse hit
testing, drag/navigation input or a claim of complete deployment qualification.

## Environment and reproducible method

Windows 11 Pro, AMD Ryzen 7 5800X, about 80 GiB visible RAM, RTX3060 12 GiB,
driver610.62; installed Isaac Sim4.5.0-rc.36, Kit106.5, Python3.10.15, USD22.11.
Each code version used one fresh owned Full-derived host with persistent host-local
navigation exclusions/dry-solve and the canonical exclusive GPU lease. No user app,
factory asset, SDK, driver or global setting was changed. CPU regression suites
were not run concurrently with timed native measurement.

The CPU launcher creates deterministic independent A/B bundles and working B copies.
There are 32 or 2,048 static half-unit Cubes on a two-unit grid, plus their World
Xform. Exactly eight Cubes move +0.125 in X. Source bytes match across the before
and after runs. Both scales are actually opened as owned working stages; each has
its own preservation baseline after setup settles. These deliberate test stage
changes are not described as product preservation. The unchanged pinned close
fixture is restored as a new setup epoch before public close/quit.

Small runs first, then large, in each host. Each scale runs three open/close cycles,
with four selections per cycle (first/middle/last/first changed path), toggle off/on,
panel hide/reopen and Close review. Native selection/camera/time, root/session
contents/flags, source bytes and settings are preserved during product operations.
There is no auto framing: some large-scene targets are off screen. Only eight change
rows are tested; this does not stress thousands of visible list rows or complex
meshes/materials, animation, instances, payloads or production lighting.

Panel reopen here sets the owned window's visibility. Actual menu discovery,
mouse close/reopen and pointer-event pass-through remain unverified.

Selection timing is synchronous callback wall time, not input-to-photon latency.
A second timer waits for two subsequent rendered frames. Compare is measured once;
primary overlay open and Close review are sampled three times. Memory is the whole
owned Windows process's working set/private bytes, sampled after 20 updates and
explicit Python GC, without OS working-set trimming. Nine created SceneViews per
scale are tracked by weak references; empty fixed SDK frames are reused.

```powershell
tools/run_shutdown_profile.ps1 -IsaacRoot <existing-sdk> -Output <new-dir> -DiagnosticProfile no-navigation -Candidate viewport-bounds-scale
```

This explicit owned QA has a 600-second host deadline. The baseline record's
original deadline is unchanged. Missing/nonfinite measurements, changed working
state, retained tracked views or extra viewports cannot pass the QA receipt.

## Measured response and bounded fix

The old overlay re-ran the full comparison on every open. At 2,048 Cubes that made
each open block for about 41 seconds. The UI now pins its already-computed report
after Compare's before/after manifest checks. Reopen validates the immutable path,
manifest and complete canonical report/config/policy digests instead of repeating
analysis. Snapshot loading and every bounds selection still verify current frozen
files, resolution and composed layers. Changed report/config/manifest or corrupted
bundle inputs refuse display; direct API callers without a receipt still recompute.
The receipt has no USD/native references and is invalidated on Compare and unload.
Save/identity/worker verification and report identities are unchanged. Timing and
memory data exist only in this diagnostic record.

| Cubes | Compare, after fix | Open median before / after (3) | Selection median / max after (12) | Callback to two frames median after |
| --- | --- | --- | --- | --- |
| 32 | 0.566 s | 0.833 / 0.345 s | 123 / 138 ms | 135 ms |
| 2,048 | 40.019 s | 40.974 / 1.549 s | 488 / 500 ms | 497 ms |

The initial Compare still blocks the UI for about 40 seconds in the larger fixture;
selection remains about half a second. The fix addresses repeated open cost, not
these remaining delays. Large auxiliary AABB coverage is explicitly **partial**:
all 2,048 bounds are known, but the one-million-pair budget stops full pair coverage.
Semantic change results and collision-unknown status are not promoted by this QA.

## Cleanup and host outcome

After-fix private usage after cycles1/2/3 was 8,768.7 / 8,722.5 / 8,724.4 MiB for
32 Cubes and 8,345.2 / 8,346.2 / 8,352.2 MiB for 2,048. The larger case grew about
**6.96 MiB** between its first and third cleanup samples (before fix: 5.53 MiB).
This includes all Isaac allocators/caches; the small-case decrease is not proof of
memory improvement. Three cycles do not establish a leak rate or long-session
stability. All tracked SceneViews were gone, owned subscriptions/snapshots cleared,
and the viewport count stayed one after every cycle in both runs.

Each native run passed 37 candidate and 19 outer checks, restored the pinned fixture,
and exited naturally0 through public file.close. Owned PIDs were reaped, Jobs empty
and closed without containment, and shared leases naturally released. Before-fix
shutdown logged 72 errors/668 warnings; after-fix logged 16/342, naming SDK shutdown
callbacks/menu failures and retaining graphics/Fabric diagnostics. Those counts are
single-run observations, not an SDK improvement or proof every diagnostic is unrelated
to the project. Both wrappers returned2 and strict-clean remained false. Stock Full
shutdown and the existing live A/B guard are unchanged.

The [sanitized raw samples and fixture/code digests](../diagnostics/bounds-scale-qa-v1.json)
preserve both runs. These are two single-machine runs in fixed small-to-large order,
with warm caches and no controlled background-CPU/clock experiment. They are not
general performance guarantees. Raw SDK logs, machine paths and private scenes are
excluded from public artifacts.

Final Windows CPU/package regression: 213 cases, 211 passed, two privilege skips,
no failures/errors (50.059s). Native measurement was completed before that suite.

## Remaining deployment limits

1. Large initial Compare and selection are synchronous; responsive large-assembly
   use is not qualified by the faster reopen path.
2. Real mouse/navigation input and long-session memory behavior remain untested.
3. Complex production scenes and the stock Full SDK shutdown remain unqualified.
   The guarded live A/B and green mesh ghost are separate work; this is AABB-only.
