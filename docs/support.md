# Supported contract

V1 is intentionally strict: local `.usd`, `.usda`, `.usdc` layers with relative sublayers/references/payloads that remain inside the entry directory, stable prim paths, explicit time and variant map, load=`all`. Each revision is a separate immutable bundle with hashes for the dependency closure. A bundle can cover only the declared composition configuration.

Remote URLs, absolute references, path escapes/symlinks/junctions, unverifiable resolver behavior, value clips, asset-valued properties, instancing/prototypes, point instancers and unsupported composition features must be rejected or yield unknown. No automatic rename matching. No proof of a complete scene when a payload/dependency is missing or a parent is inactive. Active/visibility observations carry their limitations. No animation-range claim from a single sample. Same assembly identity is a caller contract.

Authored opinions are compared separately from composed effective values. A property stack difference is evidence of opinion changes, not proof of a human author or intent. Parent propagation groups describe observed transform changes; resetXformStack boundaries stop grouping. Rotation metrics apply only to rigid matrices; scale/shear/reflection/singular matrices are reported without a rotation verdict. Equivalent Euler or quaternion representations must not cause an effective pose false positive.

AABB is only a broad-phase candidate. No confirmed collision verdict in V1. Missing Clash extension or unsupported geometry is unknown. Optional policy checks begin with rigid translation/relative rotation only, with units stated explicitly.

Input files are hashed before/after comparison and all used source layer dirty flags are checked. A changed input invalidates the comparison. Separate revision paths avoid the global layer registry treating two revisions as one file. Mutable remote dependencies cannot form a trusted baseline.

## Precision and snapshot limits

Floating values use an absolute tolerance of 1e-8; integer/boolean values and authored opinions are exact. Relative tolerance is not used for large scene coordinates. Effective attribute type changes and authored layer metadata are reported separately. `equal` describes the supported composed scope at the selected sample; it is not binary equality or a guarantee about unselected variants.

Source files are checked again after all copies. This detects ordinary mutations but is not an atomic filesystem transaction or protection against a malicious concurrent writer changing and restoring bytes. Freeze upstream files while snapshotting; otherwise supply an independently immutable filesystem revision. Snapshots are integrity-checked, not cryptographically signed provenance. Editing files and rewriting the manifest creates a new, untrusted revision identity.

A bundle has to preserve relative directory structure inside the entry directory. External sibling dependencies require preparing a common local root upstream; this tool will not rewrite the original source. Inherits/specializes/relocates, remote/package paths and asset-valued properties are rejected conservatively. Missing Clash support remains an explicit unknown; no AABB or narrow-phase adapter is implemented yet.

## Verified local resolution

The engine does not trust the Python class name of a resolver. Absolute file identifiers, anchored dependency identifiers and their resolved paths must all name the exact expected native local file. Each Sdf source layer's identifier and real path must agree with that file. URI/package identifiers, file-format arguments, relative/drive-relative resolved identifiers, network paths, symlinks and Windows reparse points are refused. Native drive paths use Windows path semantics, including case and slash differences.

Every used composed layer must be a pinned manifest file, except the review's own anonymous session. Extra local files, outside layers and anonymous dependency layers are unknown. Resolution and cached-vs-disk layer contents are checked again on verification, in both the current and stage resolver contexts, so changed mappings cannot reuse a previous verdict. Snapshot creation also rediscovers source dependencies after copying. Failures produce local-contract reasons rather than exposing remote URLs or native exception paths.

This qualifies observed local filesystem behavior in the tested Kit 106.5 environment, not arbitrary custom resolver plugins or remote workflows. It assumes a functioning USD/file-format implementation and a frozen local filesystem; it is not a defense against malicious native plugins or a writer that changes and restores bytes between checks. Full revalidation is synchronous and has not been performance-qualified for production assemblies.

## Dependent variant configurations

Declared parent prim choices are applied before descendants. Choices whose prim/set/option is not yet composed are deferred and retried when another declared choice makes progress; this also supports same-prim dependencies. After all progress, every requested set and option must remain available and its composed selection must equal the request. Invalidated, mutually exclusive or unresolved combinations are unknown. The engine does not search unspecified intermediate choices or solve arbitrary cyclic/redefined variant dependencies. Variant opinions live only in the anonymous session; source layers are not changed. Snapshot `ready` describes copied dependency integrity; the requested configuration is validated when loading/comparing it.

CLI report files are created with exclusive mode, including when a file or symlink appears after initial path checks. JSON and HTML are separate files, not a multi-file atomic transaction; an error creating HTML can leave the newly created JSON report in place without overwriting the conflicting file.

## Experimental viewer boundary

The host owns comparison UI only. Static A/B rendering uses the installed Windows SDK
in an owned child process with its default USD context. Review lighting/navigation
author only into an anonymous session. Worker receipts plus observed exit 0 are required
for a clean close; forced timeout containment is a failure. Full Isaac host normal
shutdown still has an observed native SDK fault and is not qualified. See the current
[validation status](validation.md) and [adapter guide](../exts/mmporong.scene.review/docs/README.md).


## Review display observations

The light review panel shows additive `observed.before/after` effective local/world
matrices and state in comparison JSON. Existing changed fields, propagation and
rigid-only policy semantics are unchanged. Translation deltas require matching finite
positive stage units and up axes. Local translations use each prim's parent coordinates;
they are not world travel distances. Meter conversion uses declared meters-per-unit.
Unavailable/overflowing measurements remain unavailable. Values are rounded to nine
significant digits in the UI; the report retains its original numeric evidence.

Quaternion (w,x,y,z) and shortest rotation angle are displayed only for rigid matrices;
scale, shear, reflection and singular transforms receive no rotation verdict. Orthogonal
positive-basis axis lengths are labelled unsigned magnitudes, not authored signed scale.
Inactive or unobserved transforms are unavailable, not identity transforms.

The isolated viewer temporarily overrides materials in its anonymous session: selected
source geometry is blue in A and orange in B; other geometry is gray. This is review
styling, not original material comparison. Dashed/solid curves show selected world AABB
bounds, not exact edges, clearance or collision. Raw verified snapshots supply bounds
before any helper/light/style opinions. Matching revisions share one union-bounds camera
per selected path; changing selection reframes. Hidden, absent, unloaded, non-geometric
or unsupported-range bounds produce a refusal with prior highlighting cleared. The
previous camera may remain after refusal; no object is highlighted for that selection.
Only one revision is attached/rendered at a time; no simultaneous ghost overlay exists.
The owned panel is light and the demonstrated scene is light neutral; global Kit chrome
and user renderer preferences are not changed.
