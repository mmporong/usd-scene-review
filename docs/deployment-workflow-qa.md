# Rc.4 clean-package workflow QA

Rc.4 is a project-only evaluation candidate, not a formal release. The primary
[first-use workflow](first-use.md) now matches the stage-free overlay inside the
working Isaac viewport. The minimal worker launcher remains an explicitly separate
legacy option; it was not GPU-retested in this bundle. Rc.3 history/artifacts were
not overwritten. The experiment does not unblock simultaneous live A/B.

## Fixed first-use defects

- The extension-only ZIP now has a root README, first-use guide and public synthetic
  before/after scenes. Its docs landing links resolve inside the archive. The full
  candidate has a matching first-use guide, engine and extension under exts, with
  verified `extension-path`, `sample`, `snapshot` and `compare` commands. Source
  checkout, extension-only and full-candidate layouts are distinguished explicitly.
- Empty/missing A baseline or B revision paths now identify the failing side before
  closing existing review evidence. Surrounding matching quotes are normalized;
  source USD files are refused as manifests. Frozen-bundle validation remains intact.
  An input typo no longer gets an irrelevant failed-worker acknowledgement message.
- Startup status points at working-viewport bounds/faces rather than the guarded
  Full/live A/B button. First-use instructions explain type/path filters, navigation,
  numeric scrolling, geometry refusal, panel close/reopen and extension disable.
- The native QA launcher can use an already built, verified candidate instead of
  silently repackaging repository code. Verified extension bytes are checked after
  copying into the owned host, and again against the archive after execution.

## Artifact and CPU checks

Archive: `usd-scene-review-0.1.0-rc.4-validated.zip`, 101704 bytes, 43 payload files.
SHA256: `b4b6b94a19906e5bec4d940165f52d185d20e541b8a4ad772a246f3047767b26`.
Two builds are byte-identical, with a separate SHA256 sidecar. Only code, docs and
the project-authored synthetic pair are included; no SDK binaries, private factory
assets, raw logs or credentials. The archive is a local deliverable, not a GitHub
release asset. Build it with `python tools/package_candidate.py <new.zip>`.

Tests extract under Windows spaces/Korean path components and actually run the
packaged engine in a separate CPU process, rather than importing repository code.
Final Windows CPU/package suite: 243 cases, 241 passed, two privilege skips,
no failures/errors (60.100s; not a performance benchmark).
Sample creation, JSON/HTML comparison, unchanged package bytes, all packaged Markdown
links, input ownership and tamper rejection pass. Actual existing-SDK CLI commands
verify/doctor/extension-path/sample/snapshot/compare were also exercised from a fresh
Korean/space extraction. The public rack sample is covered by CPU/CLI; the native
treatment below uses its richer synthetic polygon pair. No private asset is used.

## Native workflow and preserved profile

Installed Windows Isaac Sim4.5 (Kit106.5/Python3.10.15/OpenUSD22.11), RTX3060 12GiB,
driver610.62. The canonical shared GPU lease admitted one owned host at a time.
The preserved host-local navigation exclusion/dry-solve profile kept core/recast
absent and schema enabled; no global/SDK file or other process was modified.

The final clean-archive run passed **65 candidate and 18 outer checks**. It covers
activation, assigning A/B, Compare, type/path filtering and selection, old-A green
alpha0.22 UI faces, numeric/status routing, unsupported subdivision/topology reasons,
two show/select/close cycles, panel close, disable/re-enable, and a fresh Compare
after reactivation using quoted manifests. An invalid A path leaves the previous
report/overlay intact. The new instance is resolved after SDK module reload.
All are actual SDK UI API/button callbacks, **not real mouse/hit testing**.

Source/input hashes, root/session contents and dirty flags, pending save state,
selection, camera/view/projection, timeline and renderer settings were preserved.
Public file.close observed CLOSING then CLOSED and native **exit0**. Owned PID/Job
were reaped without containment; the wrapper naturally released the exclusive lease.

SDK errors116/warnings640 remain: three existing exception/wrapper pairs (6 lines),
five Semantics callbacks, five file-menu callbacks and 100 selection callbacks.
The read-only signature audit found no unknown signature or project traceback.
Different menu polling counts do not establish a product-caused error-rate change.
Graphics-object/Fabric history diagnostics remain. Wrapper exit2 and
**strict-clean=false** are retained; exit0 is not a clean-SDK qualification.

## Failed controls retained and corrected

1. A Korean native host-state path logged two kvdb and two capture errors; no PNG
   was produced. The capture path failure is explicit; the kvdb messages do not
   isolate their cause, so a Unicode-cache root cause is not asserted. This is
   distinct from CPU Unicode input/package support. The probe
   failed and its owned Job was contained (exit1), not passed as normal shutdown.
   Diagnostic host state now rejects non-ASCII paths before launching Kit. Capture
   uses an owned ASCII temporary target and Python copies pixels to the evidence
   destination, with explicit failure if the image was not saved. SDK files/settings
   are untouched. If the temporary path itself is non-ASCII, capture fails explicitly.
2. With ASCII host state/capture, the reactivation assertion failed because the
   probe retained an imported getter from the unloaded module. Installed SDK
   `omni.ext._impl._internal` removes extension modules on unload; product shutdown
   clears that old module's active reference. The next startup occurred, but the
   old getter did not query the new module. This probe also failed/was contained
   (exit1, errors0/warnings111). Fresh module lookup and releasing the probe's instance
   reference before disable fixed the harness; a reload regression was added.

Both failed controls preserved fixture bytes, reaped their owned PID/Job and released
the lease. They are not counted as successful native exits. Each corrected run had
a concrete changed hypothesis; the same uninstrumented failure was not repeated.
[Sanitized evidence](../diagnostics/distribution-rc4-qa-v1.json) records these outcomes,
the final checks, runtime hashes and remaining limits without raw paths/logs.

## Remaining release blockers and next priorities

1. Real mouse/hit testing of install/activation, row selection, scrolling, toggles
   and panel reactivation remains unperformed. The current evidence is callbacks.
2. Stock Full app shutdown still has the separate reproduced navigation SDK fault;
   even the reduced profile is strict-clean=false. Live A/B remains guarded.
3. Production/long-session qualification, depth/material-correct general geometry
   ghost and safe working-camera framing are not completed by this bundle. The
   existing bounded polygon support and 30-cycle sample are not widened guarantees.
4. Project license remains undecided. No formal release is created.

Next useful acceptance is real user mouse QA in an owned interactive host, followed
by evidence-driven product fixes. This bundle does not include that separate run.
Additional blind GPU shutdown runs or SDK/driver modifications are not part of it.
