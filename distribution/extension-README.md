# USD Scene Review extension candidate

Start with [installation and the complete first-use workflow](docs/first-use.md).
This extension-only ZIP includes the engine, Kit adapter and public synthetic USD
pair under examples/synthetic. It does not include the candidate's review_kit.py
CLI; use the guide's extension-only Python Console instructions for that archive.

The primary workflow is a stage-free overlay in the existing Isaac Sim 4.5 working
viewport: compare frozen baseline/revision manifests, filter/select changes, inspect
blue A/orange B bounds, optional old-A green UI faces at alpha0.22, and numeric
evidence/refusal reasons. Working camera/selection and source/session are preserved.
Camera framing/restore is unavailable under that preservation contract.

Experimental live A/B remains guarded in Full Isaac. UI faces have no scene depth
or original material rendering, and geometry support is bounded. Real mouse QA and
production use are unqualified. Reduced-host natural exit0 does not mean clean SDK
shutdown: errors/warnings remain and strict-clean=false. No SDK, driver or system
changes are made. This is an evaluation candidate, not a formal release; project
license selection remains pending.
