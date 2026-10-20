# Validation status

Environment audit: Python 3.11.16, OpenUSD 24.05, Kit 107.3.3. Bundled pxr in-memory stage creation and transform calculation succeeded (exit 0). System Python 3.12.3 has no pxr. The inspected Isaac Sim installation has an RC VERSION marker; no public compatibility guarantee follows.

Actual Kit GUI: **BLOCKED / NOT RUN**. NVIDIA kernel driver 580.173.02 versus NVML 580.178 mismatch; execution session has no DISPLAY. No driver modification, reboot or guessed display/session is permitted. CPU tests cannot substitute for GUI validation.

## Product checks

- 63 stdlib unittest cases passed on Python 3.11.16 / OpenUSD 24.05: dependency closure/hash checks, missing and changed inputs, cached-layer mismatch, manifest mutation and invalid NaN, authored/effective and type/metadata changes, inactive versus removed, parent/reset behavior, rotation equivalence, rigid policy limits, deterministic reports, source bytes and dirty preservation, CLI output safety, deterministic extension archive structure.
- Actual CLI subprocesses created both fixture snapshots and JSON/HTML reports. Two separate compare processes produced byte-identical JSON and HTML. The fixture reported two changed prims with the child grouped under its moved parent.
- Python source AST/compile and project/extension TOML parse passed. The extension source was inspected against installed APIs; this does not verify native Kit imports or GUI behavior.
- The unresolved-reference negative test emits OpenUSD warnings by design and verifies unknown; raw machine logs are not published.
- No CI workflow added or claimed. No renderer, interactive Kit GUI, Windows or newer Kit verification performed.
- Local installed `extscache` and `kit/extsPhysics` inspection found no Clash extension. Clash remains an explicit unknown stub; no extension is downloaded or enabled.

## Known pending work

Working GPU/authorized GUI session is required for installation, A/B switching, framing, timeline isolation and cleanup acceptance. Animated viewport review and static-mesh ghost are deferred. Real Clash integration and any geometry conversion require version-specific API and license checks. The project license remains undecided. This is an early implementation, not production-ready software.

## Post-review fixes

- Reproduced valid nested-prim and same-prim variant dependencies that alphabetical selection rejected. Parent-first/deferred selection now validates every requested set again after final composition. Mutually exclusive or unresolved configurations remain unknown; arbitrary cyclic choice search is unsupported.
- Stage close false/exception or a still-attached stage retains cache ownership, snapshot handles and layer protections. Compare/A-B/Close/framing are blocked, and shutdown does not destroy an unconfirmed context. Seven tests run the actual Python lifecycle methods with GPU-free boundary stubs; they do not verify NVIDIA native behavior.
- JSON/HTML creation uses exclusive mode. A regression test introduces a file or symlink after prechecks and verifies that it is not overwritten.
- Full 63-test suite passed again. Real CLI subprocesses accepted nested and same-prim variant configurations, produced byte-identical repeated JSON/HTML, and preserved the published dependency-only example bytes. The updated self-contained extension ZIP and source/TOML checks passed.
- GPU/GUI blocker and all pending GUI acceptance criteria above remain unchanged. System settings and existing source USD files were not modified.
