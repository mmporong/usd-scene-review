# First use: stage-free review inside Isaac Sim 4.5

This is the primary rc.4 evaluation workflow. Keep Play stopped. The existing SDK
provides Python3.10/OpenUSD22.11; system Python alone is insufficient. The package
contains only project code/docs and two independent synthetic USD scenes, no SDK,
factory assets or runtime installer. Spaces and Korean path components are supported
by the tested CPU file workflow. Never replace or close someone else's working app.

## Candidate ZIP: verify, prepare inputs and locate the extension

Build with `python tools/package_candidate.py <new-rc.4.zip>` from the source checkout.
Compare the archive's SHA256 with its sidecar, then extract to a new folder. Run these
commands in that extracted root. Choose an existing writable output parent **outside**
the package; sample/snapshot/report/session destinations must be new.

```powershell
$sdk = '<existing Isaac Sim 4.5 SDK>'
$python = Join-Path $sdk 'kit/python/python.exe'
$parent = '<existing writable output parent>'
& $python -B .\review_kit.py verify
& $python -B .\review_kit.py --sdk $sdk doctor
& $python -B .\review_kit.py extension-path
$sample = Join-Path $parent 'review sample'
& $python -B .\review_kit.py --sdk $sdk sample --workspace $sample
```

Doctor is read-only; it does not certify rendering or install/repair anything. The
sample creates snapshot-A/manifest.json, snapshot-B/manifest.json and offline reports.
For your own **saved files**, freeze baseline and revision separately:

```powershell
& $python -B .\review_kit.py --sdk $sdk snapshot --source '<saved before.usda>' --workspace "$parent/baseline snapshot"
& $python -B .\review_kit.py --sdk $sdk snapshot --source '<saved after.usda>' --workspace "$parent/revision snapshot"
```

This compares saved file contents, not unsaved edits in an already-open app. Copying
dependencies can fail if a resolver or asset is unavailable; stop and inspect the
reported reason rather than substituting another scene. Preserve both frozen bundles.

## Install/activate and review

In the existing Isaac Extensions UI, add the extension search directory printed by
extension-path (the extracted candidate's **exts** directory), refresh and enable
`mmporong.scene.review`. For an extension-only ZIP, see below. Do not alter SDK files
or global renderer/navigation settings. Enabling creates the review panel, not another
USD context. Disabling removes the panel and its owned overlay/subscriptions.

For a disposable first run, use a separate owned host and open the generated
`review sample/sources/after.usda` as its working stage. Do not replace a user's stage
to try the sample. In an existing real working stage, the snapshots must share its
metersPerUnit/upAxis and align to the same world coordinates; the tool refuses an
axis/unit mismatch and cannot prove that arbitrary files correspond to that stage.

1. Enter A baseline/before **manifest.json** and B revision/after **manifest.json**.
   The source USD path or a snapshot directory is not the manifest. Surrounding
   matching quotes copied from a shell are accepted. Empty/missing inputs identify
   the side that needs correction and leave prior review evidence intact.
2. Click Compare. If status is unknown, inspect the reason and restore/recreate valid
   frozen bundles before trying the viewport. Do not edit manifests to bypass hashes.
3. Click **Show snapshot bounds in working viewport**, then select a changed path.
   Path search, Change type and Inherited motion compose; Previous/Next follow matching
   rows without wrapping. Selecting a row alone does not open a renderer or move the
   working camera/selection. The optional legacy viewer has its own focus controls.
4. Inspect blue dashed A/orange B bounds and before/after/delta values, including
   direct/parent evidence. Scroll the panel to numeric rows. Check **Old A green UI
   faces** for supported static Cubes/planar polygon Meshes at alpha0.22. The per-object
   status says shown or not shown and why (for example subdivision, animation, unsafe
   topology or budget). Missing/deleted B can still have old-A evidence. UI faces are
   always-on-top helpers, without source materials or scene depth; not collision proof.
5. **Clear bounds overlay** removes shapes; **Close review** also clears owned review
   resources. The panel stays available: Show snapshot bounds reopens the overlay for
   the retained comparison. Closing the panel also clears the overlay. To reopen the
   panel, disable/re-enable this extension and enter the manifests again; no saved
   panel-toggle menu or automatic input persistence is claimed.
6. Disable the extension and verify your working stage, selection, camera, session
   and save state remain. Save/discard your own edits only by an explicit user action.

Changing stages, hiding the working viewport or starting Play clears the helper.
The helper never writes source/session layers. Working-camera frame/restore remains
unavailable because the inspected SDK framing command edits the active camera prim.
Experimental Full/live A/B remains guarded; do not use a diagnostic flag to bypass it.

## Extension-only ZIP

Extract under a new directory named `mmporong.scene.review`; add **its parent** to
Isaac's extension search paths. Enable the extension. This archive includes root
README.md, docs/first-use.md, python engine and examples/synthetic/before.usda and
after.usda. It has no review_kit.py CLI. In the existing Isaac Python Console, after
activation, freeze the included public pair into new external folders:

```python
from usd_scene_review import create_snapshot
a = create_snapshot(r'<extension folder>/examples/synthetic/before.usda', r'<new external baseline folder>')
b = create_snapshot(r'<extension folder>/examples/synthetic/after.usda', r'<new external revision folder>')
print(a, b)  # paste these manifest paths in the review panel
```

## Failures and qualification limits

Missing SDK/ABI: choose the existing 4.5 SDK, not system packages. Package hash/files
failure: extract a fresh verified copy and keep outputs elsewhere. Input error: fix
the named A/B manifest path; no worker acknowledgement is needed unless an actual
worker is failed. Unknown comparison: inspect frozen dependencies/configuration.
Overlay refusal: keep Play stopped, use the default working viewport, match units/
axis and inspect per-object support. No SDK/driver/security-setting repair is part
of this workflow.

Whole-app shutdown has a separate SDK limit. Stock Full navigation shutdown can
crash even without this extension. An owned diagnostic Full-derived host with core/
recast excluded and schema retained reached natural exit0, but errors/warnings and
graphics/Fabric diagnostics remain: **strict-clean=false**. This is not a recommendation
to disable navigation globally or a claim that Full shutdown is solved. Use the
preserved host-local profile and canonical exclusive lease for developer GPU tests;
never run alongside another user's GPU job. Forced containment is not normal exit.

The legacy minimal-Kit launcher in quickstart-en/ko is a separate worker route;
it does not complete simultaneous live A/B inside the working Isaac viewport.
Actual mouse/hit testing, production/long-session use and general mesh ghost remain
unqualified. License is pending; this is not a formal release or an open-source
reuse/redistribution license grant.
