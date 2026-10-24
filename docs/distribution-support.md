> rc.4 primary workflow: [stage-free review inside Isaac](first-use.md).
> The minimal Kit launcher below is the optional legacy worker route, not live in-app A/B.

# Candidate support and release boundary

Candidate 0.1.0-rc.3 is a project-only archive for Windows and a separately installed
Isaac Sim 4.5 SDK. The qualified machine uses Kit 106.5, SDK Python 3.10.15,
OpenUSD 22.11 and an RTX 3060. Other SDK/ABI combinations are rejected rather than
silently mixed. Doctor checks imports and read-only GPU health; native smoke provides
separate render/interaction/save/exit evidence. No network service, AI or Clash adapter
is required. No runtime, driver, security policy, registry or system PATH is changed.

The launcher copies the verified project payload into the new private session runtime
folder, isolating Kit-generated Python caches from the original package. The minimal
host starts in that new portable state directory. It owns one isolated review
worker and a Windows process job; it never attaches to an existing app or unsaved scene.
Normal host/worker exit plus preservation is required. Timeouts/Ctrl+C are failed
containment runs. Source snapshots remain immutable; exports require a new folder
outside them. Keep all outputs outside the package, which is checksum-verified on use.

Checksums detect accidental changes, not malicious re-signing or publisher identity.
The ZIP contains only this project's Python/config/docs and an independently authored
USDA pair. It excludes NVIDIA binaries/MDL sources, factory originals, local logs and
secrets. Runtime-generated reports/logs can contain local paths and remain private.

The white review style, translucent green helper and right evidence panel are retained.
The independent sample is intentionally smaller than the approved factory GIF; the GIF
and factory source assets are not bundled. Geometry limits and unknown/policy/human
distinctions still apply. This is not production assembly, collision or safety approval.

## CPU CI versus installed GUI verification

CPU CI runs deterministic packaging/integrity/export/core tests on a pinned public
OpenUSD Python runtime. It does not install or run NVIDIA Kit, inspect a GPU, render,
or validate full Isaac shutdown. Local GPU checks must record the exact SDK, fresh
extraction directory, command, captures, preservation receipt and real process exit.
See repository validation/work-log records for completed versus failed/pending runs.

## Unresolved release decisions

The full Isaac app's reproduced baseline shutdown fault remains unqualified; this
candidate does not fix it. No driver/runtime upgrade or repeated vendor crash loop is
part of this workflow. The project license is still **pending**, including MIT approval.
The archive has a notice, not an invented LICENSE. It is not a formal release or a
general open-source reuse/redistribution grant.

For the owner to consider: [MIT](https://opensource.org/license/mit) is the simpler
permissive candidate with notice retention. [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0)
adds an explicit patent grant/termination and more notice/change conditions. This is a
decision summary, not a selected license; NVIDIA SDK terms remain separate either way.

The repository's draft PR is an internal review mechanism. External IsaacSim/source
contribution candidates remain a separate researched list, not completed contributions
and not a replacement for this candidate's implementation/testing. No upstream issue,
PR or vendor report is submitted by the distribution workflow.

The rc.3 helper retains visible translucent green faces at OmniPBR fractional opacity
0.22, zero opacity threshold and half-width secondary edge cues. Face-only actual
RTX comparisons preserve recognizable original geometry behind the helper. This
changes anonymous preview helpers only; source material networks stay unchanged.

Rc.3 adds separate scale-normalized effective orientation for positive orthogonal
nonuniform scales. It does not change rigid-only policy checks or infer authored rotation.
Static AABB candidates use actual Cube vertices and Mesh nonhole face points transformed
to world coordinates. Authored extent and subtree bounds are excluded from this analysis.
Only known disjoint A to overlapping B is newly introduced; existing, resolved, boundary,
added-geometry and unknown-baseline cases remain separate. Hidden/animated/deformed,
displaced (including subset/render-context and allPurpose/full/preview material bindings)
and unsupported geometry is unknown.
The report includes the versioned configuration, meter tolerance, budgets and exclusions;
budget exhaustion is auxiliary partial coverage and does not rewrite semantic status.
Collision/clearance remains unknown. Candidate selection frames both objects with a
common A/B union; unknown bounds refuse focus. Intentional marks grant no policy waiver.
The worker independently recomputes the pinned report and validates candidate IDs.
