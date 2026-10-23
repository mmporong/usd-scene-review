# Official viewport ownership and reuse assessment

Scope: installed Isaac Sim 4.5 / Kit 106.5, read-only pre-Play comparison. The six
failed teardown controls are not repeated. The product's validated Full-host guard
and existing runtime teardown are unchanged.

## Installed SDK evidence

- `omni.kit.viewport.utility.create_viewport_window` constructs the official
  `ViewportWindow`. Window 107.0.8 owns `ViewportLayers`, which constructs a
  `ViewportWidget`; it does not supply a different native rendering backend.
- `ViewportWindow.destroy` removes its UI/settings/minimize subscriptions, destroys
  owned layers and frames, unregisters the window and clears its active-window
  reference (`window.py:309-342`). Layer destruction calls the widget's public
  `destroy` (`layers.py:208-224`). Two official windows still require two viewport
  render resources; changing wrapper type alone does not remove the known boundary.
- Widget 107.0.7 accepts an existing `ViewportAPI`, but still builds its own display
  and texture objects (`widget.py:95-120`). Shared API state is not an independent
  A/B stage/camera contract or documented ownership transfer for a single texture.
- Reopening a stage on the same widget keeps its existing `ViewportTexture` when
  present (`widget.py:472-500`). The texture reuses its existing native handle when
  available (`impl/texture.py:275-331`). This supplies a source-backed reuse candidate.
- Public `UsdContext.attach_stage_async` and viewport file capture exist. A named
  owned context can attach independent stages sequentially without replacing the
  user's working context. The capture helper is awaitable and releases its native
  capture references on completion.
- The inspected native texture surface exposes its context as a getter, without a
  public context-rebinding setter. RenderProduct selection does not document
  arbitrary scene/light isolation between simultaneous revisions in one context.
  No faithful two-independent-live-scenes/single-native-texture route was found in
  this inspected surface; this is not a claim to have searched every SDK facility.

Merging A/B below two roots, changing global visibility/purpose, or offsetting the
scenes can mix light/material/relationship targets and indirect illumination. Those
approaches are not equivalent to isolated revisions. Hiding or pooling live owners
is not proof of cleanup and is not used as a normal-exit fix.

## Separate candidate gate

The local `experiment/owned-viewport-reuse` branch contains
`tools/in_app_reuse_probe.py` to evaluate **sequential cached A/B**, not a product
adapter or two live panes. This executable prototype is not included in main
pending native verification. Each cycle creates one official viewport window and one
owned context, attaches independent A/B/A stages, captures them, then actually
destroys the window, stage/context, cache entries and timeline. A second cycle
creates fresh resources. It does not retain hidden native owners between cycles.

Fixtures deliberately share prim/material/light paths while differing in pose,
material color, light intensity and revision-only prims. CPU checks confirm those
stages are separate and that authoring B does not affect A. A common fixture camera
provides matching pose/projection. The SDK gate checks actual red/blue/red pixels,
source roots/cameras, one added viewport, its disappearance after destruction, and
working-stage/selection/time preservation. It fails fast on the first known native
failure; missing later lifecycle assertions are not passes.

The candidate has not been connected to the comparison extension. It does not yet
implement change-list refresh/navigation, ghost options, fair exposure control,
full workspace restoration or production snapshot/dependency coverage. No renderer
or global lighting setting is changed in this gate. It is a feasibility test, not
acceptance of the requested product flow. Native results are recorded separately
from CPU fixture semantics.

Local candidate CPU regression: 158 cases, 156 passed, two privilege skips, zero
failures/errors (66.986 s). That count includes the local candidate fixture test;
it does not describe additional main functionality or a GPU pass. No candidate
GPU host was started: other Kit processes appeared during preparation, followed
by a sustained host with roughly 6 GiB occupied VRAM. The prepared native checks,
including actual destruction/recreation and the independent app-exit outcome,
remain **not run**. Resource pooling, leak freedom and successful reuse are not claimed.

## Minimum user-visible change if this candidate becomes viable

A captured pair is refreshed sequentially on selection/common camera changes.
It would preserve separate revision composition and original light changes, but
users would see a refreshed image pair rather than two concurrently live draggable
viewports. Refresh latency and exposure fairness need qualification. That interaction
change needs an explicit user choice before replacing the live-split design.

If supported reuse also fails native lifecycle checks, the external blockers remain
the public native texture stop/release warning and the independent project-free
`tf.dll+0xec7b` shutdown crash. Current approval does not permit an SDK/driver patch,
warning suppression, or treating forced termination as success. Upstream reports
have not been sent; sanitized reproductions stay in this repository only.

An alternative validation-policy choice would be a bounded owned test allowed to
observe beyond this one identified SDK warning while still stopping on crash,
device loss, material or descriptor errors. That is not currently performed or
authorized by this assessment, is not a product safety-gate change, and would not
turn the known whole-app crash into a normal-exit pass.
