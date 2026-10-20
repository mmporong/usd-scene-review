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

A is the saved scene before the change; B is the saved scene after it. A change can be
intentional. Default framing retains the whole factory and its original geometry and
material context. Blue dashed A / orange solid B outlines identify selected world
AABB bounds only. Focus selected is an explicit optional close-up; switching it off
restores whole-scene context even for absent/unbounded selections. One revision is
rendered at a time, with matching A/B camera/lens/clipping within the chosen mode.

The light panel's before/after/delta table comes from the compared snapshots, including
unchanged local pose for parent-propagated children. Local coordinates are parent-frame
coordinates; meters use declared stage units. Rotation is rigid-only quaternion plus
shortest angle. Axis magnitudes are unsigned and do not recover authored signed scale.

Expand Human review metadata to choose a separate `.jsonl` log and explicitly save an
intentional/needs-review disposition with a reason. Reload review restores exact-match
history. Decisions bind A/B hashes and full change identity and never alter/hide evidence,
policy failures or unknowns. Default UI policy is not evaluated; this local unverified
metadata is not authorization or operational safety approval. See support.md for limits.

The isolated child also shows a concise right evidence panel with the selected path,
before/after/delta, motion cause, policy/unknown and separate human status. Reload review
refreshes the child status. Enable **Show old A** to place the selected static Cube/Mesh
subtree at its old complete world transform as faint lime visual-only helpers in B.
Unsupported geometry produces a reason instead of a partial overlay. Helpers are cleared
on selection/toggle/revision/close and have no copied physics or source composition.

**Fixed preview illumination** is enabled by default and applies on the next View A/B.
It uses a labelled normalized white dome and manual exposure in the owned child only.
Source visibility/material differences stay visible and disclosed. Diagnostic captures
advance the child renderer and expose a bounded `stable` flag; PNG existence alone is
not render-convergence evidence. See support.md for limits and validation.md for results.
