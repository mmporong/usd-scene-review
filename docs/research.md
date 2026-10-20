# Prior tools and API basis

The product is a focused read-only revision review integration, not a claim of algorithmic novelty.

- [OpenUSD usdview](https://openusd.org/release/toolset.html): inspect composed scenes, properties and transforms. Layer inspection remains the authority for composition detail.
- [NVIDIA USD Layers](https://docs.omniverse.nvidia.com/extensions/latest/ext_core/ext_layers.html): authoring and layer workflows. This project does not implement layer merging.
- [NVIDIA Clash Detection](https://docs.omniverse.nvidia.com/extensions/latest/ext_clash-detection.html): existing hard/soft, static/dynamic checks, plus query/result and approval/resolution workflows. Reuse through an optional future adapter; do not duplicate or claim these capabilities as new.
- [Clash UI](https://docs.omniverse.nvidia.com/extensions/latest/ext_clash-detection/clash-detection-ui.html): meshes and point clouds, not USD shapes. Current documentation is newer than the local Kit baseline; availability must be checked locally.
- [XformCache](https://openusd.org/24.05/api/class_usd_geom_xform_cache.html): local/world and parent transforms, reset stack.
- [Dependency discovery](https://openusd.org/release/api/dependencies_8h.html): dependencies and unresolved paths. This API alone is not a reproducibility guarantee.
- [Viewport utility](https://docs.omniverse.nvidia.com/kit/docs/omni.kit.viewport.utility/1.0.19/Overview.html): framing and named-context viewports. Installed baseline exports frame_viewport_prims in utility 1.1.2.
- [Isaac Sim 5.1 notes](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/overview/release_notes.html): Kit 107.3.3.

## Licensing boundaries

OpenUSD 24.05 has a Modified Apache 2.0 license: https://github.com/PixarAnimationStudios/OpenUSD/blob/v24.05/LICENSE.txt . Preserve exact package notices if ever distributing it. NVIDIA SDK/Clash redistribution requires checking the exact package agreements; this repository distributes neither. No upstream example implementation or factory-ops-twin asset is copied.
