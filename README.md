# USD Scene Review

Read-only semantic review of two local OpenUSD scene revisions, with a separate Python engine and NVIDIA Omniverse Kit interface.

**Early development. Kit GUI validation is blocked on the development host.** This integrates existing OpenUSD and NVIDIA APIs; it does not claim a new collision algorithm or the first review/approval workflow.

## First supported baseline

Kit 107.3.3 / Python 3.11 / OpenUSD 24.05. The inspected Isaac Sim package is 5.1.0.0 with an installed `5.1.0-rc.19` VERSION marker. This is an environment observation, not an Isaac Sim compatibility certification. System Python alone does not provide `pxr`.

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

For an existing Isaac Sim pip installation whose bundled `pxr` is not on the Python path, run the matching Python 3.11 with the helper (Linux baseline only):

```bash
python tools/with_openusd.py --isaac-root "$ISAACSIM_ROOT" -- -m unittest discover -s tests -v
```

`ISAACSIM_ROOT` is the existing `isaacsim` package directory containing `extscache` and `kit`. The helper never installs packages or launches Kit. For CLI commands, replace the test arguments after `--` with `-m usd_scene_review.cli ...`.

Optional policy flags are `--max-translation` (stage units) and `--max-rotation-degrees`. They apply to changed world rigid poses only, not collision, animation trajectories or application safety. Exit codes: `0` observed equal/changed, `2` unknown comparison/policy or invalid input, `3` observed policy violation. A clash status of unknown is always present; code 0 is never a collision clearance certificate. Destinations must be new paths.

See the generated [JSON example](examples/dependency-change.json) and [offline HTML example](examples/dependency-change.html). Root files are identical in this example; a dependency moves a parent and its child.

## Kit adapter

Add this checkout's `exts` directory to Kit extension search paths and enable `mmporong.scene.review`. See the [adapter guide and pending GUI checks](exts/mmporong.scene.review/docs/README.md). The UI provides comparison rows and an isolated static A/B viewport; it rejects animated viewport review instead of changing the user's timeline. Semantic reports can evaluate an explicitly configured time.

A self-contained extension ZIP can also be generated from this project's code:

```bash
python tools/package_extension.py artifacts/mmporong.scene.review.zip
```

Extract it into a fresh extension directory and add its parent to Kit's extension search paths. The package structure is checked; actual GUI installation/loading remains unverified. No NVIDIA binary or third-party asset is included.

See [support](docs/support.md), [plan](docs/plan.md), [prior tools](docs/research.md), [validation](docs/validation.md) and [한국어 안내](docs/ko.md).

## License status

No project license has been selected yet. Do not assume permission to redistribute this project's code until a license is added. This repository contains newly authored code, documentation and synthetic fixtures only. NVIDIA binaries and third-party assets are not bundled. OpenUSD and NVIDIA components retain their own license terms.
