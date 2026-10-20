# Kit adapter

Enable `mmporong.scene.review` after adding this checkout's `exts` directory to the
extension search paths. Alternatively generate a project-only ZIP with
`python tools/package_extension.py <new-output.zip>`, extract it into a fresh
extension directory, and add its parent to the search paths. No SDK binary or
third-party asset is included.

Compare two frozen local snapshot manifests. The panel shows direct changes first,
with counts for parent propagation. Search prim paths and enable **Inherited motion**
to reveal inherited-only world movement; mixed authored/effective changes stay visible.
Select a result for evidence and unknown reasons. **View A/B** opens a separate Kit
viewer window and frames the selected path when present. Missing/inactive paths are
refused with a suggestion to try the other revision. Rigid scale/shear unknowns do
not imply a policy pass or collision clearance.

## Runtime and ownership

The comparison panel uses the host's Python/USD libraries but creates no review USD
context, timeline or viewport in that host. Static rendering starts a separate process
from the existing Windows Isaac Sim SDK (`kit/kit.exe`, `extscache`, `exts`). The viewer
is qualified only against the Windows Isaac Sim 4.5 / Kit 106.5 environment listed in
[validation](../../../docs/validation.md). No installation or runtime download occurs.
Other platforms can use the offline engine; their viewer path remains unqualified.
Two rendering processes need additional GPU memory and startup time.

The worker uses only its own default context and normal SDK shutdown. Its sole primary
thread starts suspended, is assigned to an owned Windows Job, then resumes. Descendants
inherit that Job. Private request/result files use a per-run identity and ordered
sequence. Compared manifest hashes are pinned; both bundles and source protections
are rechecked. Review navigation and fallback lighting use only an anonymous session;
file layers cannot be edited/saved while attached. Animated viewport review is refused;
the offline report can still compare its explicitly declared time sample.

**Close review** requires a preservation receipt and observed worker exit code 0.
Extension disable/app shutdown also perform bounded synchronous IPC cleanup, independent
of the host event loop. Native attach is not cancelled in the child. Unconfirmed cleanup
is a failure; timeout containment terminates only the owned Job and blocks another launch
until termination is confirmed and the user acknowledges the failed worker with Close.
Failed private diagnostic folders are retained locally; successful folders are removed.
Closing the viewer's OS window directly is treated as unconfirmed, not a clean close.

A named rendered context in this installed SDK crashed during manual destruction,
including controls without this extension. Retaining it until host shutdown also failed.
Process isolation contains that native boundary; it does not fix NVIDIA's DLL.

## Repeat acceptance

From this checkout, with an existing SDK:

```powershell
python tools/run_kit_validation.py --isaac-root $sdk --output artifacts/new-kit-run --full-app --timeout 360
```

The new output directory contains private logs, result JSON and a viewport image. The
checked-in runner creates synthetic stages, tests actual native buttons, parent filtering,
selection, A/B/A, framing, capture, close/reopen, disable/re-enable, source/default-context
preservation, and host quit with a viewer active. The launcher requires both the result
and normal process exit. See validation.md for completed versus failed/pending results;
mock protocol tests are not rendering evidence. Do not publish private runtime logs/assets.


## Reading the visual difference

Select a changed row, then View A / View B. The persistent legend and actual-view label
identify blue/dashed before and orange/solid after. Selected geometry is recolored in
an anonymous session; context is gray. The same selected path uses an identical camera,
lens and clipping across A/B. Outlines represent world AABB bounds, not mesh edges or
collision. A refusal clears the previous highlight. One revision is rendered at a time.

The light panel's before/after/delta table comes from the compared snapshots, including
unchanged local pose for parent-propagated children. Local coordinates are parent-frame
coordinates; meters use declared stage units. Rotation is rigid-only quaternion plus
shortest angle. Axis magnitudes are unsigned and do not recover authored signed scale.
Raw comparison evidence remains available in the collapsed panel.
