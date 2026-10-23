# Full Isaac teardown investigation

These owned Windows Isaac Sim 4.5 / Kit 106.5 controls used synthetic anonymous
stages. They did not load user scenes, modify the SDK/driver or change system/user
renderer settings. Other Factory CPU work continued. GPU prechecks found no other
Kit/compute host before each run. Every known native failure contained only the
test's Windows Job; containment is never a normal-exit pass.

The product Full Isaac guard remains enabled. No failed cleanup experiment below
is applied to product teardown. Clean review close/reopen/disable and whole-app
shutdown are still unqualified.

## Hypotheses and results, 2026-10-23

| Control | Hypothesis | Observed result |
| --- | --- | --- |
| Serialized widget destruction | Two update boundaries between destroys avoid a same-frame release race | Rejected: warning occurs inside the second `ViewportWidget.destroy()`, before owned stage/context cleanup. |
| Display delegate first | Presentation resources must be freed before texture destruction | Invalid as a clean control: active render callbacks access the removed provider. The texture warning also remains. This ordering is not used in the product. |
| Isolated child Python environment | CPU OpenUSD search paths inherited by Kit cause the baseline crash | Not sufficient: removing `PYTHONPATH` and `PXR_USD_WINDOWS_DLL_PATH` in the child still gives the baseline `0xc0000005` at `tf.dll+0xec7b`. No parent environment changed. |
| Stop updates, then display/texture destruction | Quiescing first makes display-first cleanup safe | The native interface warning occurs during update stopping, before either display destruction or renderer detachment. Thus UI destruction alone is not required to trigger it. |
| Native textures only | Remove project UI/material/ghost/manipulator ownership from the reproducer | Two native textures each render at least eight frames; the warning appears between the before/after records of the second `IHydraTexture.set_updates_enabled(False)`. No added UI widget or presentation provider exists. No stage/context/texture destruction has begun. |
| Requested native async textures | Texture-local `is_async=True` avoids the synchronous stop path | Same warning at the second native updates-off call. Only the requested flag was recorded in that private variant, so no broader claim about effective renderer internals is made. No global async setting changed. |

The native-only control uses one owned context/timeline, one explicit engine
attachment and two public `create_hydra_texture` calls. There is no widget to
perform a second implicit engine attachment. Both textures receive actual drawable
events before stopping. It excludes project comparison, MDL ghost material,
camera manipulators, image providers and multiple owned contexts as necessary
conditions for this warning in the tested SDK configuration.

This establishes a small public native-API warning boundary that fails this
project's qualification gate, not the private C++ root cause or a proof that every
SDK configuration fails. The setter returned; no immediate device loss was observed.
The message alone does not establish a double-free. It also does not establish
that the texture warning causes the separate project-free shutdown access violation.
The baseline has neither of these added native textures. Historical navigation-DLL
failure remains a different recorded fault.

Reading the local tf.dll export table places the nearest lower exported symbol in
the Tf notice registry, but that is not an unwound/symbolized stack and cannot name
the faulting function. No SDK binary, proprietary source, dump or raw log is bundled.

## Reproduce from the project checkout

Use an existing supported SDK and a new private output directory. Verify other GPU
work is idle first. The launcher refuses this reproducer without `--full-app` and
`--fail-fast-native`. It never attaches to a running user's host.

```powershell
python tools/run_in_app_validation.py --isaac-root <existing-sdk> --output <new-private-dir> --full-app --probe tools/in_app_native_texture_probe.py --fail-fast-native --timeout 180
```

The launcher's Python needs the existing bundled OpenUSD as described by
`tools/with_openusd.py`; this command installs nothing. The native probe is the
byte-identical source used for the synchronous native-only control. Its checkpoint
records render completion and per-texture before/after stop/release phases.
`process-result.json` records actual process outcome independently of functional
checkpoint assertions. Missing later checks mean not reached, not passed.

For the independent environment hypothesis:

```powershell
python tools/run_in_app_validation.py --isaac-root <existing-sdk> --output <another-new-private-dir> --full-app --baseline --isolated-python-environment --fail-fast-native --timeout 180
```

Isolation removes only three Python/USD search variables in the child dictionary:
`PYTHONPATH`, `PYTHONHOME` and `PXR_USD_WINDOWS_DLL_PATH`, when present. Other variables
and the parent process remain unchanged. The receipt lists removed variable names,
never values. The default remains inherited to preserve existing controls.

There is no validated product teardown repair from these controls. Do not suppress
the warning, leak native owners, modify SDK private fields or enable the guarded
Full Isaac route to turn these failures into a pass.
