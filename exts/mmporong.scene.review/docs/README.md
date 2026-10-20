# Kit adapter (early implementation)

The adapter targets the inspected Kit 107.3.3 / Python 3.11 / OpenUSD 24.05 API.
It has **not been run in a Kit GUI**. Source compilation and installed API inspection
are not GUI validation or compatibility certification. The inspected Isaac Sim
installation also has an RC build marker.

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

- The adapter creates a unique named USD context. It never opens, closes, selects
  prims in, or saves the user's default USD context.
- Snapshot source layers are temporarily non-editable and non-saveable. The edit
  target is an anonymous session, so viewport cameras cannot author into bundle files.
  In-memory permissions are restored on detach, and source dirty state is checked.
  The extension never calls a USD save/export operation.
- Drag-and-drop USD loading is disabled in the review viewport. No editing commands,
  transform controls, ghost geometry or automatic fixes are supplied.
- **Viewport review supports static stages only.** Any time-sampled attribute causes
  a refusal. Kit 107's `ViewportWindow` consumes the global timeline even with a named
  context; changing the user's timeline to match the comparison time would violate
  the isolation boundary. Time-specific semantic results remain available in the report.
- The default viewport camera/framing appearance, render startup, selection, renderer
  cleanup and rapid enable/disable behavior still require actual Kit GUI validation.
- Close is deferred while a viewport attachment is running. Extension disable hides
  its windows immediately, then an owned asynchronous cleanup waits for the attachment
  task to finish before detaching/destroying its context. It never cancels the native
  attachment's Python await. If Kit stops the event loop before that completion, or an
  external cancellation makes native completion unknown, cleanup remains unconfirmed;
  the context is retained until process exit rather than destroyed during attachment.
- No Clash extension is enabled, downloaded or assumed present by this adapter.

## Pending GUI acceptance checklist

Run with a working GPU driver and an authorized graphical session. Record the exact
Kit/Python/USD/extension versions separately from CPU results.

- Compare the repository's static A/B snapshots and frame moved, added and deleted prims.
- Confirm the user's original context, selection, timeline and layer dirty flags are unchanged.
- Switch A/B repeatedly, close review and disable/re-enable the extension without stale stages.
- Confirm modified/missing bundle files are refused on switch.
- Confirm animated stages are refused rather than displayed at a misleading time.
- Verify source hashes and dirty state before and after review; inspect errors on cleanup.

These checks are pending; no pass result is claimed.
