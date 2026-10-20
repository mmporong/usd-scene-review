# USD Scene Review

Read-only semantic review of two local OpenUSD scene revisions, with a separate Python engine and NVIDIA Omniverse Kit interface.

**Early development. Kit GUI validation is blocked on the development host.** This integrates existing OpenUSD and NVIDIA APIs; it does not claim a new collision algorithm or the first review/approval workflow.

## First supported baseline

Kit 107.3.3 / Python 3.11 / OpenUSD 24.05. The inspected Isaac Sim package is 5.1.0.0 with an installed `5.1.0-rc.19` VERSION marker. This is an environment observation, not an Isaac Sim compatibility certification. System Python alone does not provide `pxr`.

## Scope

Fixed local dependency bundles; stable prim paths within the same assembly; explicit time, variant and load configuration; authored versus effective changes; local/world transforms; active and visibility changes; parent movement groups; deterministic JSON and offline HTML reports. Missing evidence produces `unknown`. Input files are never edited. No AI, automatic fixes or general merge.

See [support](docs/support.md), [plan](docs/plan.md), [prior tools](docs/research.md), [validation](docs/validation.md) and [한국어 안내](docs/ko.md).

## License status

No project license has been selected yet. Do not assume permission to redistribute this project's code until a license is added. This repository contains newly authored code, documentation and synthetic fixtures only. NVIDIA binaries and third-party assets are not bundled. OpenUSD and NVIDIA components retain their own license terms.
