# Implementation plan and acceptance

Current status: the core, isolated minimal-Kit review, static green/lime old-pose helper,
right-side evidence and local human metadata are implemented and tested. The visual
baseline is user-approved. The current bounded work stabilizes capture tooling and
reconciles evidence; it does not redesign visuals or add features. Full Isaac normal
shutdown remains blocked by the reproduced baseline SDK fault; license is undecided.
See [validation.md](validation.md) and the current disposition in
[contribution-candidates.md](contribution-candidates.md). The initial outcome below is
historical, not the latest GUI status.

1. Establish this scope, prior-art links and validation boundaries before implementation.
2. Implement strict local snapshot bundles and manifest integrity validation. Root-equal/dependency-different, missing dependency and changed bundle must be tested.
3. Implement authored/effective comparison, transform/active/visibility observations and parent movement grouping. Test masked opinions, inactive versus removed, reset stacks, equivalent rotation and configuration mismatch.
4. Add deterministic CLI JSON/HTML, synthetic USDA fixtures and CPU tests. Assert source hashes/dirty flags unchanged and repeatable reports. HTML must escape scene strings.
5. Add isolated Kit A/B review contexts, result selection and framing. Validate extension loading, switching, framing and cleanup in a real GUI before claiming support. Ghost follows static-mesh validation only.
6. Inspect local Clash API availability; retain unknown when absent. Policy and Clash adapter follow core correctness.
7. Review public files for secrets, personal paths and external assets; push only newly authored deliverables. No CI initially: local Python/OpenUSD checks are sufficient for this baseline; GUI remains separate.

## First implementation outcome

Core snapshot/compare, authored/effective reporting, simple rigid policy checks, CLI JSON/HTML, synthetic fixtures, CPU tests and a minimal Kit adapter are implemented. An extension packaging helper creates an archive using only this repository's code. CPU checks pass; real Kit GUI acceptance and actual Clash integration remain pending. See validation.md for the exact boundary. Initial documentation was committed before implementation.
