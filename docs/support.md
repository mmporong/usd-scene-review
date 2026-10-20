# Supported contract

V1 is intentionally strict: local `.usd`, `.usda`, `.usdc` layers with relative sublayers/references/payloads that remain inside the entry directory, stable prim paths, explicit time and variant map, load=`all`. Each revision is a separate immutable bundle with hashes for the dependency closure. A bundle can cover only the declared composition configuration.

Remote URLs, absolute references, path escapes/symlinks, custom resolvers, value clips, asset-valued properties, instancing/prototypes, point instancers and unsupported composition features must be rejected or yield unknown. No automatic rename matching. No proof of a complete scene when a payload/dependency is missing or a parent is inactive. Active/visibility observations carry their limitations. No animation-range claim from a single sample. Same assembly identity is a caller contract.

Authored opinions are compared separately from composed effective values. A property stack difference is evidence of opinion changes, not proof of a human author or intent. Parent propagation groups describe observed transform changes; resetXformStack boundaries stop grouping. Rotation metrics apply only to rigid matrices; scale/shear/reflection/singular matrices are reported without a rotation verdict. Equivalent Euler or quaternion representations must not cause an effective pose false positive.

AABB is only a broad-phase candidate. No confirmed collision verdict in V1. Missing Clash extension or unsupported geometry is unknown. Optional policy checks begin with rigid translation/relative rotation only, with units stated explicitly.

Input files are hashed before/after comparison and all used source layer dirty flags are checked. A changed input invalidates the comparison. Separate revision paths avoid the global layer registry treating two revisions as one file. Mutable remote dependencies cannot form a trusted baseline.

## Precision and snapshot limits

Floating values use an absolute tolerance of 1e-8; integer/boolean values and authored opinions are exact. Relative tolerance is not used for large scene coordinates. Effective attribute type changes and authored layer metadata are reported separately. `equal` describes the supported composed scope at the selected sample; it is not binary equality or a guarantee about unselected variants.

Source files are checked again after all copies. This detects ordinary mutations but is not an atomic filesystem transaction or protection against a malicious concurrent writer changing and restoring bytes. Freeze upstream files while snapshotting; otherwise supply an independently immutable filesystem revision. Snapshots are integrity-checked, not cryptographically signed provenance. Editing files and rewriting the manifest creates a new, untrusted revision identity.

A bundle has to preserve relative directory structure inside the entry directory. External sibling dependencies require preparing a common local root upstream; this tool will not rewrite the original source. Inherits/specializes/relocates, remote/package paths, asset-valued properties and custom resolvers are rejected conservatively. Missing Clash support remains an explicit unknown; no AABB or narrow-phase adapter is implemented yet.

The engine currently requires `Ar.GetUnderlyingResolver()` to expose DefaultResolver. A Kit app using a custom resolver will receive unknown even for a local bundle until that resolver is separately qualified; the GUI baseline has not established this behavior yet.

## Dependent variant configurations

Declared parent prim choices are applied before descendants. Choices whose prim/set/option is not yet composed are deferred and retried when another declared choice makes progress; this also supports same-prim dependencies. After all progress, every requested set and option must remain available and its composed selection must equal the request. Invalidated, mutually exclusive or unresolved combinations are unknown. The engine does not search unspecified intermediate choices or solve arbitrary cyclic/redefined variant dependencies. Variant opinions live only in the anonymous session; source layers are not changed. Snapshot `ready` describes copied dependency integrity; the requested configuration is validated when loading/comparing it.

CLI report files are created with exclusive mode, including when a file or symlink appears after initial path checks. JSON and HTML are separate files, not a multi-file atomic transaction; an error creating HTML can leave the newly created JSON report in place without overwriting the conflicting file.
