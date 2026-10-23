# SDK structure and runtime diagnosis

## Actual Full Isaac follow-up, 2026-10-23

After the other Kit host exited, precheck found only a CPU dashboard plus desktop
GPU clients, about 2.4 GiB occupied VRAM and no Kit/Isaac compute host. Two owned,
fresh-profile tests were run sequentially on the merged code. No SDK/driver or other
process was changed. A new Factory host subsequently occupied the GPU, so further
native teardown diagnosis was deferred. The later guard-only check below completed
after GPU work became idle again.

**Project-free baseline:** the review extension was not exposed or enabled and no
extra context/viewport was created. Its two setup checks passed. Normal SDK unload
then crashed after viewport-window extension shutdown; the owned Job was contained,
not a clean exit. The baseline minidump and prior `engine-sequence-01` minidump both
report access violation `0xc0000005` at **`tf.dll+0xec7b`**. Module/exception addresses
were read from the standard minidump module-list and exception streams. This is
concrete matched baseline evidence for that shutdown failure, distinct from the
historical navigation-plugin fault. It does not prove every comparison teardown
failure has the same cause. Sensor UI `_menu_button1` and manipulator-factory Python
errors also appear in this project-free control.

**Full feature attempt:** 27 checks passed, covering two actual in-process views,
translation/rotation/add/delete/parent selection and common focus/projection,
35-degree evidence, camera synchronization, actual Kit UI-test row click,
rendered green surfaces and the .22-versus-opaque control. Actual Full Isaac UI and
viewport captures were produced. The first review close emitted the released
Hydra-texture-interface warning, and fail-fast contained only the owned Job.
Thus the overall run failed. Normal close confirmation, renderer/default-stage
restoration, repeated opening, stage switch, active disable/re-enable and full
feature host shutdown were **not reached**. No desktop mouse QA or Play was run.
Postmortem loading verifies both snapshot manifests/dependencies; both original
synthetic source files still match their frozen copies. Working-stage and renderer
restoration at close cannot be established from this interrupted process.

**Guard defect:** that actual Full host returned false from the former filename-only
guard; the 27-check attempt therefore did not enter its requested test-only override.
Earlier statements that the guard was present were source checks, not native proof
that Full Isaac was correctly recognized. The follow-up branch now accepts filename
with/without `.kit` and also checks the public extension manager for enabled
`isaacsim.exp.full`. This covers renamed/derived Full experiences. The actual
guard-only run confirms the SDK filename is `isaacsim.exp.full` (without `.kit`) and
its Full experience is enabled. All eight checks pass on `7c2aa00`: disabled actual
button, extension and direct API refusal before ownership, unchanged working
stage/session/selection/time and bypass setting false. No experiment was opened
or guard overridden. Normal SDK unload still crashed at `tf.dll+0xec7b`; only the
owned Job was contained. Guard correctness does not establish clean app shutdown.

The disposable feature probe has an explicit `--full-feature-validation` switch,
scoped guard restoration in `finally` and CPU tests for refusal without opt-in and
restoration after success/failure. It is not shipped in the extension. The SDK
topology probe now supports `--verify-full-guard`, records actual app identity and
brackets each viewport destruction plus an update barrier before the next. These
SDK-topology guard/serial-teardown checks have **not run**. The separate guard-only
probe is `tools/in_app_guard_probe.py`; it passed eight actual-host checks without
opening any comparison. No native teardown fix is claimed.

Private run directories are `full-baseline-20261023-01` and
`full-feature-20261023-01`, plus `full-guard-7c2aa00-01`; compact dump evidence is
`shutdown-comparison-20261023.json`. Raw dumps/logs and host paths are not bundled.
Final CPU regression: 155 cases, 153 passed, two privilege skips, no failures/errors
(73.140 s). This includes the new experience-identity and probe-override regressions.

The original structure review was CPU-only. The subsequently authorized narrow
GPU controls below are now complete. Existing user changes, the full-app guard,
SDK and driver remain intact. Topology success is not full feature qualification.

## Follow-up, 2026-10-23: shutdown isolation pending

No new GPU host was started: the precheck identified a running Kit host belonging
to the separate Factory runtime, several Factory Python processes and about
5.9 GiB occupied VRAM. They were left untouched. The baseline and full-feature
tests below remain unrun, not denied and not passed.

Re-reading the previous sequence's console log corrects an important ambiguity:
the released `omni.hydratexture.plugin` interface warning appeared at 37.628 s
and 51.852 s, after the shared/two-context rendered frames and before their
`before-stage-cleanup` records. It appeared again at 70.040 s during viewport-window
extension shutdown, immediately before the native crash. Thus the warning was
not confined to whole-app shutdown. The earlier probe lacked per-widget destroy
records, so these lines do not prove the exact native release call responsible.
The revised probe brackets each widget destruction, stage close and engine release.

The installed widget's public `destroy()` clears its engine/API texture, destroys
its display delegate and texture, and drops its API reference (`widget.py:158-175,
435-442`). The texture clears capture/drawable/settings subscriptions before
dropping its native texture (`impl/texture.py:67-84`). The product calls this public
path after removing its camera callbacks/manipulators; no private SDK patch is used.
A return from `destroy_context` remains a Python lifecycle receipt, not proof that
every GPU/native reference is released.

The historical project-free navigation-DLL failure at `+0x18014` documents another
baseline failure. The latest crash has no matching module/offset established here;
the sensor UI/manipulator errors do not establish identical native causality.
Do not classify the latest shutdown failure as that baseline fault without a
matched current control. Likewise, all three topology render successes remain valid.

A project-free control is prepared as `--full-app --baseline`: no review package
is extracted or exposed to its host, no additional stage/context/viewport is created,
and it waits for the same default first-frame barrier and uses the same normal
uncancellable quit API as the topology sequence. It retains the launcher's common
probe dependencies/settings. Baseline checks and actual process exit/native errors
are separate. It has not run. When GPU use is safe, run this once before the
topology/product controls; compare warning phase and crash module/stack, not just
the generic word "crash". Released texture interfaces now fail native validation
and trigger fail-fast containment of the owned Job.

The bounded product fix shields render-drain futures from caller cancellation and
retains ownership until their actual completion. Disabling during an outstanding
attachment now quiesces selection entry points immediately instead of leaving the
review state `open`. CPU failure-injection covers both cases; it does not prove
that either caused the native crash. The full-app guard remains enabled. A fresh
full-feature capture and normal shutdown qualification are still required.
Final CPU regression: 152 cases, 150 passed, two privilege skips, no failures/errors;
14 lifecycle ownership cases pass. No new native execution is implied.

## Authorized topology results

Precheck found no competing Kit/Isaac/Python/Factory GPU task, about 10.5 GiB free
VRAM and roughly 11% desktop GPU use. The corrected sequence used one fresh owned
full-Isaac host. It never changed the user's renderer settings or manipulated
another process. No physics Play was started.

| Control | Actual rendered binding | Cleanup and default-stage preservation |
| --- | --- | --- |
| 1 owned context / 1 viewport | `rtx`, context-local viewport handle 0 | Passed |
| 1 owned context / 2 viewports | Same context `rtx`, handles 0 and 1 | Passed |
| 2 owned contexts / 2 viewports | Each context attached to `rtx`, handle 0 in each | Passed |

All six rendering/preservation checks passed in `engine-sequence-01/result.json`.
Phase records correlate context name, requested/attached renderer and actual
viewport handle. The handle is context-local, not a global engine index. The
inspected public API exposes no numeric native HydraEngineIndex getter; no ID was
invented and no extra engine was created solely to obtain an identifier.

After all controls and their cleanup completed, full-app shutdown reported sensor
UI/manipulator extension shutdown errors, an already-released Hydra texture
interface and a native crash. Fail-fast containment terminated only that Job.
Thus process/runtime qualification failed despite six functional passes. Startup
also reported an asset-browser import failure; the SDK profile was not globally
error-free, and no dependency/runtime repair was attempted. This trace must not be
silently attributed to the earlier navigation-plugin baseline fault.

Two diagnostic defects were corrected before the sequence: the first instrumented
run explicitly attached an engine and then let the widget attempt attachment again;
that confounded its command-fence failure. Also, `single` initially allocated an
unused second context in the prepared code; the CPU control-count test now prevents
that. These failed controls do not establish an SDK multi-context limit.

The SDK's `isaacsim.app.setup.__new_stage` waits for the initial default viewport
frame before printing "App is loaded". `is_app_ready()` alone precedes that barrier.
The corrected sequence used that same frame barrier and awaited each new viewport's
actual rendered binding before constructing the next. This combination rendered
all three topologies without command-fence, invalid-engine-index, MDL-unload or
descriptor-allocation failures during the controls. Individual causality between
the startup and serialization changes was not separately isolated.

The minimum product change is prepared in `in_app.py`: first-frame readiness,
separate placeholder frames and serialized A/B binding, with shielded ownership
while binding is pending. Cancellation tests cover the new pending-widget boundary.
The full-app guard remains on. These product changes have CPU coverage only; no
high-level ghost/selection/full-app regression was run after the shutdown crash.

## Traced creation path

The current product uses public Python entry points:

1. `InAppReview.open` creates unique A/B contexts with `omni.usd.create_context`.
2. `_attach` calls `UsdContext.attach_stage_async` for each static snapshot stage.
3. Each `ViewportWidget(usd_context_name=..., camera_path=..., resolution=...)`
   constructs its own `ViewportAPI` and `ViewportTexture`.
4. In installed `omni.kit.widget.viewport` 107.0.7, `impl/texture.py:374`,
   `__enable_hydra_engine` checks the context's attached engine names and calls
   `omni.usd.add_hydra_engine` only when the requested engine name is absent.
5. `__set_hd_engine` at line 436 calls that helper, then `create_hydra_texture`
   at line 500, passing context name, camera path and renderer name. The wrapper
   returns through the native hydra-texture factory. The code at line 526 explicitly
   assumes the requested change succeeded before native application is complete.
6. Native `omni.usd.add_hydra_engine` and `get_or_create_hydra_engine` are declared
   in installed `omni.usd` 1.12.4 `_usd.pyi:789,809`. Their C++ implementation is not
   supplied as readable source here. The exact invalid-index branch cannot be
   established from these declarations or the existing logs.

Thus the product does not directly construct a private renderer object, but the
standard widget path can implicitly attach/create an engine for its named context.
Changing `ViewportWidget` to `ViewportWindow` alone does not avoid this: installed
`omni.kit.viewport.window` 107.0.8 `layers.py:133` constructs `ViewportWidget` too.

The factory signature exposes renderer **name** and USD context name, not an
existing opaque engine handle. The name `rtx` is not proof that two contexts share
one native engine instance. `engine_creation_flags`, `device_mask` and low-latency
options are documented Private/Internal in `_hydra_texture.pyi:318-332`; guessing
flags or changing global renderer settings is not a supported fix.

## What existing failures establish

The second full-app run logged app readiness, then the full-app loaded message,
then `invalid HydraEngineIndex 1` at 30.569 seconds. It was contained on that first
native failure. Waiting for the public readiness signal did not prevent failure;
an additional asynchronous renderer-startup race remains an unproven hypothesis.
The index is an internal Hydra index; it is not evidence of GPU device 1, nor does
the log identify which A/B context requested it. Existing logs do not distinguish
failure during stage attachment, engine registration or asynchronous texture setup.

Minimal Kit could render the same public path. Its later MDL unload and descriptor
allocation errors are additional lifetime symptoms, not proof of the full-app index
error's root cause. No DLL patch, driver diagnosis or universal "Kit cannot do
multiple viewports" conclusion follows from these observations.

The installed full app depends on `isaacsim.exp.base`; that base declares
`app.asyncRendering=false` and `asyncRenderingLowLatency=false` at lines 204-205,
matching the launcher's synchronous mode. It also enables MDL warm-up at line 154.
These facts do not justify changing renderer globals or private engine flags.
The current evidence is a reproducible failure of the tested configuration, not a
proof that every supported full-Isaac multi-context configuration is impossible.

## Same-engine isolation alternatives

| Approach | Confirmed API / limitation | Assessment |
| --- | --- | --- |
| Two viewports, same existing context | Widget checks attached engine names and reuses that context's engine path | Supported construction path; both viewports see the same current stage. Two independent A/B stages are not isolated by camera alone. |
| One owned context, sequential A/B stages and cached images | `attach_stage_async`, owned cameras and viewport capture exist | Smallest plausible in-app alternative: render A then B using one owned context and show cached images side by side. One extra context may still hit the full-app restriction; stage/material swaps still need native qualification. This is a cached comparison, not two simultaneously live viewports. |
| One temporary stage, A/B under separate roots | USD composition and named roots exist | Root namespaces alone do not isolate rendering. Cross-root references, bindings, collections and source camera/light targets need complete remapping. Added/deleted paths need an explicit revision path map. Not ready for implementation as an equivalent renderer. |
| Camera clip planes or spatially separated roots | Camera projection/clipping exist | Other revision geometry can still contribute shadows, reflections, GI or environment lighting. Spatial camera offsets also cease to represent identical world coordinates without compensation. Reject as a faithful isolation shortcut. |
| Per-viewport scene roots/visibility masks | Not found in the inspected public ViewportAPI/HydraTexture surface | `render_product_path` exists at `api.py:306-317`, but selecting a RenderProduct is not documented here as excluding arbitrary scene roots or light/GI contributions. Do not invent renderer-specific collection attributes. |
| Global prim visibility / purpose | USD visibility/purpose are stage opinions | Shared by both views; cannot independently select A and B simultaneously. Reusing source purposes can suppress actual source differences. Sequential switching is possible only in an owned stage and needs cache invalidation/settling. |
| Background scene delegates | Installed `omni.hydra.scene_api` exports add/remove/root-transform functions | Its manifest marks it Internal, and no per-viewport delegate filter was found. Root transforms do not establish light/material isolation. Not selected as a supported workaround. |
| Swap the user's default context stage | Stage attachment exists | Rejected: stage events can alter other extensions, selection, timeline and unsaved workspace state even if the original pointer is restored. |

For a combined temporary stage, original files could remain untouched, but that
does not establish visual equivalence. Absolute relationship/connection targets,
material inheritance, collection membership and global lights can cross revision
boundaries. Dome/environment lights and indirect illumination especially cannot be
assumed isolated by a namespace or camera. Unsupported remapping would need an
explicit unknown/refusal. There is no confirmed faithful simultaneous-root solution
in the inspected API set, so no speculative renderer replacement was wired in.

## Reproducer and remaining validation

`tools/in_app_engine_probe.py` is an SDK-only reproducer with three controls:

| Topology | Owned contexts | Viewport textures | Purpose |
| --- | --- | --- | --- |
| `single` | 1 | 1 | Does the first additional context/texture already fail? |
| `shared` | 1 | 2, same stage | Does a second texture on one context fail? Not A/B isolation. |
| `two-contexts` | 2 | 2 | Does the second independent context change the result? |

It waits for app readiness and the initial default viewport frame, creates only anonymous Cube/camera fixtures, leaves the
default context untouched and records before/after context creation, stage attachment
and each widget, with context name and attached engine names. The launcher accepts
`--topology` and can contain its owned Job at the first known native error. This
should identify the failing phase instead of attributing index 1 to a guessed side.
Its CPU checks verify control counts and absence of extra engine-attachment calls.
The GPU sequence used `--topology sequence` and did not enable the product or bypass
its full-app guard.

The authorized sequence ran all three controls in one owned host and stopped at
the first native shutdown crash. It is not an unattended repeat loop. Reproduction
requires separately resuming GPU validation. Example for that future step only:

```powershell
python tools/run_in_app_validation.py --isaac-root $sdk --output <new-private-dir> --probe tools/in_app_engine_probe.py --full-app --topology sequence --fail-fast-native --timeout 180
```

Because all three controls rendered, retain the current independent snapshot/context
design and validate the prepared lifecycle correction first. A cached one-context
adapter or merged-root stage is not currently necessary. Full feature acceptance
must still cover row selection, values, ghost warm-up, navigation, repeated teardown
and app shutdown. Full-app shutdown remains a concrete unresolved boundary.

The existing safe full-app guard remains enabled. No public commit/push or SDK/global
renderer setting change was made in this diagnosis phase.
