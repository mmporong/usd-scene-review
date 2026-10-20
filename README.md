# USD Scene Review

Read-only semantic review of two local OpenUSD scene revisions, with a separate Python engine and NVIDIA Omniverse Kit interface.

**Early development. Windows static review features are tested, but full Isaac app normal shutdown remains blocked by a native SDK fault.** This integrates existing OpenUSD and NVIDIA APIs; it does not claim a new collision algorithm or the first review/approval workflow.

## Demonstration

![Actual static A/B switching, changed-rack selection and framing](examples/usd-scene-review-demo.gif)

Actual light review-panel and isolated-viewport captures from minimal Kit using the
existing Windows Isaac Sim 4.5 SDK. **A means the saved scene before the change;
B means the saved scene after the change. A difference is not automatically a defect.**

The demo starts with the whole factory and retains its original geometry and material
colors. Blue dashed bounds mark the selected object in A; orange solid bounds mark it
in B. Only the anonymous helper outlines are colored. Optional **Focus selected** moves
the camera closer; the default retains the whole saved scene, even if a selected object
is absent in one version. A/B use matching cameras within either mode.

The actual panel shows before/after/delta positions in stage units and meters,
rigid quaternion/angle, unsigned axis magnitudes, active/visibility, and direct versus
ancestor-propagated movement. The rack moves 0.2 m; a descendant keeps its local pose
while its world position changes by 0.2 m. The final demo review entry is explicitly
marked as a demonstration, not operational approval.

Human reviewers can mark **intentional** or **needs review**, with a required reason.
These decisions append to a separately chosen local `.jsonl` log, bound to exact A/B
manifest hashes and the prim's full change evidence. Input/change differences do not
inherit prior approval. Detected differences, independent policy failures and unknowns
remain visible and unchanged. This is local unverified review metadata, not multi-user
authorization or a safety sign-off; see [support](docs/support.md#local-human-review-metadata).

Genuine UI/viewport capture pairs are arranged side by side on a light canvas; private
input paths are omitted, and outer empty viewport margins are cropped in overview pairs.
No scene pixels or numeric results are generated or replaced. Only one saved scene is
rendered at a time. No ghost overlay, collision verdict or AI is claimed. Outlines are
world AABB bounds, not exact mesh edges. Source assets and private logs are excluded.
Full Isaac host normal shutdown remains blocked; see [validation](docs/validation.md).

## Target and checked environments

The Windows target is Isaac Sim 4.5: installed Kit 106.5.0 / Python 3.10.15 / OpenUSD 22.11. CPU/CLI and actual packaged-extension tests use its bundled runtime. Native GUI checks cover static A/B attachment, rendering, selection/framing, repeated switching, close/reopen, negative inputs and source/default-context isolation. Tests use a separate minimal Kit app with synchronous rendering, as configured in the installed Isaac base app; the full Isaac application and production assemblies are not certified. See [Windows validation](docs/validation.md#windows-isaac-sim-45).

The earlier Linux CPU baseline was Kit 107.3.3 / Python 3.11 / OpenUSD 24.05, from an Isaac Sim 5.1 installation with an RC marker. It was not rerun after these Windows changes and is not an upgrade requirement. System Python alone does not provide `pxr`.

## Scope

Fixed local dependency bundles; stable prim paths within the same assembly; explicit time, variant and load configuration; authored versus effective changes; local/world transforms; active and visibility changes; parent movement groups; deterministic JSON and offline HTML reports. Missing evidence produces `unknown`. Input files are never edited. No AI, automatic fixes or general merge.

## Run with an existing OpenUSD Python environment

No package installation is required: set `PYTHONPATH` to this checkout's `src` and use a Python environment that can already import `pxr`.

```bash
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
python -m unittest discover -s tests -v
mkdir -p artifacts
python -m usd_scene_review.cli snapshot fixtures/dependency-change/before/scene.usda artifacts/before
python -m usd_scene_review.cli snapshot fixtures/dependency-change/after/scene.usda artifacts/after
python -m usd_scene_review.cli compare artifacts/before/manifest.json artifacts/after/manifest.json --json artifacts/review.json --html artifacts/review.html
```

For an existing Isaac Sim installation whose bundled `pxr` is not on the Python path, use a Python matching its USD ABI with the helper (3.10 for Isaac Sim 4.5; 3.11 for the earlier Kit 107 baseline):

```bash
python tools/with_openusd.py --isaac-root "$ISAACSIM_ROOT" -- -m unittest discover -s tests -v
```

`ISAACSIM_ROOT` is the existing `isaacsim` package directory containing `extscache` and `kit`. The helper never installs packages or launches Kit. For CLI commands, replace the test arguments after `--` with `-m usd_scene_review.cli ...`.

Windows PowerShell, from this checkout, using only an existing 4.5 SDK:

```powershell
$sdk = '<existing Isaac Sim 4.5 SDK directory>'
$python = Join-Path $sdk 'kit/python/python.exe'
# Python 3.10's packaging test needs toml, already bundled in this SDK.
$archive = @(Get-ChildItem (Join-Path $sdk 'extscache/omni.kit.pip_archive-*') -Directory)
if ($archive.Count -ne 1) { throw 'Select the matching installed pip archive explicitly.' }
$env:PYTHONPATH = (Join-Path $archive[0].FullName 'pip_prebundle') + [IO.Path]::PathSeparator + $env:PYTHONPATH
& $python -B tools/with_openusd.py --isaac-root $sdk --timeout 180 -- -m unittest discover -s tests -v
```

The optional `test` extra declares the TOML test dependency for Python 3.10; the engine has no added dependency. The helper sets process-local Windows USD DLL directories. It does not change system environment settings. A restricted execution sandbox may prevent asyncio's local socketpair initialization; run tests in a normal local terminal rather than changing security settings. Symlink-specific tests explicitly skip when Windows reports missing privilege.

To repeat the native Windows acceptance in a new private directory:

```powershell
python tools/run_kit_validation.py --isaac-root $sdk --output artifacts/new-kit-run --full-app --timeout 360
```

This builds and extracts a project-only ZIP, launches a separate installed full Isaac app,
and uses synthetic stages. It does not attach to running user apps. Logs and screenshots
stay in the selected output directory; do not publish raw machine logs.

Optional policy flags are `--max-translation` (stage units) and `--max-rotation-degrees`. They apply to changed world rigid poses only, not collision, animation trajectories or application safety. Exit codes: `0` observed equal/changed, `2` unknown comparison/policy or invalid input, `3` observed policy violation. A clash status of unknown is always present; code 0 is never a collision clearance certificate. Destinations must be new paths.

See the generated [JSON example](examples/dependency-change.json) and [offline HTML example](examples/dependency-change.html). Root files are identical in this example; a dependency moves a parent and its child.

## Kit adapter

Add this checkout's `exts` directory to Kit extension search paths and enable `mmporong.scene.review`. See the [adapter guide and pending GUI checks](exts/mmporong.scene.review/docs/README.md). The UI provides searchable rows, inherited-motion filtering and a separate static A/B viewer process; it rejects animated viewport review instead of changing the user's timeline. Semantic reports can evaluate an explicitly configured time.

A self-contained extension ZIP can also be generated from this project's code:

```bash
python tools/package_extension.py artifacts/mmporong.scene.review.zip
```

Extract it into a fresh extension directory and add its parent to Kit's extension search paths. Native extraction/loading and synthetic static A/B review were checked in an isolated Windows Kit process. No NVIDIA binary or third-party asset is included.

See [PR/contribution candidates](docs/contribution-candidates.md), [support](docs/support.md), [plan](docs/plan.md), [prior tools](docs/research.md), [validation](docs/validation.md) and [한국어 안내](docs/ko.md).

## License status

No project license has been selected yet. Do not assume permission to redistribute this project's code until a license is added. This repository contains newly authored code, documentation and synthetic fixtures only. NVIDIA binaries and third-party assets are not bundled. OpenUSD and NVIDIA components retain their own license terms.
