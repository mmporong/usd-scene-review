# Validation status

Environment audit: Python 3.11.16, OpenUSD 24.05, Kit 107.3.3. Bundled pxr in-memory stage creation and transform calculation succeeded (exit 0). System Python 3.12.3 has no pxr. The inspected Isaac Sim installation has an RC VERSION marker; no public compatibility guarantee follows.

Actual Kit GUI: **BLOCKED / NOT RUN**. NVIDIA kernel driver 580.173.02 versus NVML 580.178 mismatch; execution session has no DISPLAY. No driver modification, reboot or guessed display/session is permitted. CPU tests cannot substitute for GUI validation.

## Product checks

- 50 stdlib unittest cases passed on Python 3.11.16 / OpenUSD 24.05: dependency closure/hash checks, missing and changed inputs, cached-layer mismatch, manifest mutation and invalid NaN, authored/effective and type/metadata changes, inactive versus removed, parent/reset behavior, rotation equivalence, rigid policy limits, deterministic reports, source bytes and dirty preservation, CLI output safety, deterministic extension archive structure.
- Actual CLI subprocesses created both fixture snapshots and JSON/HTML reports. Two separate compare processes produced byte-identical JSON and HTML. The fixture reported two changed prims with the child grouped under its moved parent.
- Python source AST/compile and project/extension TOML parse passed. The extension source was inspected against installed APIs; this does not verify native Kit imports or GUI behavior.
- The unresolved-reference negative test emits OpenUSD warnings by design and verifies unknown; raw machine logs are not published.
- No CI workflow added or claimed. No renderer, interactive Kit GUI, Windows or newer Kit verification performed.
- Local installed `extscache` and `kit/extsPhysics` inspection found no Clash extension. Clash remains an explicit unknown stub; no extension is downloaded or enabled.

## Known pending work

Working GPU/authorized GUI session is required for installation, A/B switching, framing, timeline isolation and cleanup acceptance. Animated viewport review and static-mesh ghost are deferred. Real Clash integration and any geometry conversion require version-specific API and license checks. The project license remains undecided. This is an early implementation, not production-ready software.
