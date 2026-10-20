# USD Scene Review — distribution candidate 0.1.0-rc.1

Start with [English quick start](docs/quickstart-en.md) or
[한국어 빠른 시작](docs/quickstart-ko.md).

This project-only candidate uses your existing Windows Isaac Sim 4.5 SDK through a
separate minimal Kit app. It installs no runtime or driver and never attaches to an
already running application. Full Isaac app shutdown remains unqualified.

Run `review_kit.py verify` first. Check the archive's separate SHA-256 before extracting.
Payload checksums detect changed files but are not authenticated signatures. Outputs,
logs and user scenes belong outside this extracted package.

Project license is pending the owner's choice. This is an evaluation candidate, not
a formal release or a grant of open-source reuse/redistribution rights. NVIDIA SDK,
MDL source/binaries, private factory assets, credentials and machine logs are excluded.
