# Kit adapter (early implementation)

The Windows target is Isaac Sim 4.5 / Kit 106.5 / Python 3.10 / OpenUSD 22.11.
A self-contained ZIP has passed synthetic static A/B checks in an isolated native Kit
GUI: actual button callbacks, attachment, rendering, selection/framing, repeated
switching, close/reopen, modified/missing inputs, animation refusal and attached-stage
cleanup on disable/re-enable. The minimal test app uses `app.asyncRendering=false`,
matching the installed Isaac base setting. The full Isaac app, asynchronous rendering
and large user assemblies are not certified. The earlier Linux baseline was not rerun
after these Windows changes.

## Install from this checkout

Add the repository's `exts` folder to Kit's extension search paths, then enable
`mmporong.scene.review`. Keep the checkout's `src` folder beside `exts`:
the extension module path points to `../../src` relative to the extension root.
The extension does not install packages or download assets. Alternatively, run
`python tools/package_extension.py <output.zip>` from the repository root, extract
the resulting ZIP and add its extracted extension folder's parent to Kit's extension
search paths. The deterministic package contains the authored engine under `python/`
and rewrites the module path accordingly; it does not contain NVIDIA binaries.

## Review

1. Enter the complete paths of two snapshot `manifest.json` files in A and B.
2. Choose **Compare**. Each result row selects a changed prim and exposes its details.
3. Choose **View A** or **View B** to attach that revision to a separate review viewport.
4. Choose a row to frame its prim in the displayed revision. If absent, inactive or
   unloaded, try the other revision. A deleted prim is never framed in the wrong scene.
5. **Close review** destroys the review viewport and detaches its stage.

Invalid snapshots are refused. Manifests are revalidated on each A/B switch and a
changed report requires another comparison. This is synchronous local comparison;
large production assemblies and responsive background comparison are not validated.

## Read-only boundary and limitations

- The adapter creates a unique named USD context and timeline. It never opens, closes, selects
  prims in, or saves the user's default USD context.
- Snapshot source layers are temporarily non-editable and non-saveable. The edit
  target is an anonymous session, so viewport cameras cannot author into bundle files.
  Kit 106 resets permissions during attachment, so the viewport remains hidden until
  permissions and the anonymous edit target are reestablished and checked after attach.
  In-memory permissions are restored on detach, and source dirty state is checked.
  The extension never calls a USD save/export operation.
- Drag-and-drop USD loading is disabled in the review viewport. No editing commands,
  transform controls, ghost geometry or automatic fixes are supplied.
- **Viewport review supports static stages only.** Any time-sampled attribute causes
  a refusal. The owned context uses its own timeline so attach/close cannot synchronize
  frame range or FPS back into the user's stage. Viewport widgets may still consume
  global timeline time, so animated viewport review is not enabled. Time-specific
  semantic results remain available in the report.
- Native camera/framing, rendering, selection, repeated A/B and ordinary
  close/disable/re-enable passed for synthetic static scenes. Disable during an
  in-flight native attachment and rapid stress cycling still require native testing.
- Close is deferred while a viewport attachment is running. Extension disable hides
  its windows immediately, then an owned asynchronous cleanup waits for the attachment
  task to finish before detaching/destroying its context. It never cancels the native
  attachment's Python await. If Kit stops the event loop before that completion, or an
  external cancellation makes native completion unknown, cleanup remains unconfirmed;
  the context is retained until process exit rather than destroyed during attachment.
- Stage close must return success and the context must no longer hold a stage before
  the adapter erases its cache entry, restores source permissions or drops the snapshot.
  A false return, exception or still-attached stage blocks Compare, A/B, framing and
  Close actions with an error message. Disabling the extension makes one conservative
  cleanup attempt; failed detach retains the owned context and source protections.
  Failed shutdown owners remain strongly referenced until process exit. This boundary
  has GPU-free failure-path tests and native successful-close coverage; injected
  native close failures remain unverified.
- No Clash extension is enabled, downloaded or assumed present by this adapter.

## GUI acceptance checklist

Run with a working GPU driver and an authorized graphical session. Record the exact
Kit/Python/USD/extension versions separately from CPU results.

- Compare the repository's static A/B snapshots and frame moved, added and deleted prims.
- Confirm the user's original context, selection, timeline and layer dirty flags are unchanged.
- Switch A/B repeatedly, close review and disable/re-enable the extension without stale stages.
- Confirm modified/missing bundle files are refused on switch.
- Confirm animated stages are refused rather than displayed at a misleading time.
- Verify source hashes and dirty state before and after review; inspect errors on cleanup.

The listed synthetic checks passed in the Windows test environment. They do not
certify production scenes, arbitrary resolver plugins or in-flight failure cleanup.
See the repository validation report for exact scope and remaining tests.
