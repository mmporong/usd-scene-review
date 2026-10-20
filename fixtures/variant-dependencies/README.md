# Variant dependency fixtures

Newly authored synthetic USD layers generated through OpenUSD's in-memory authoring API. No external assets.

- `nested.usda`: the default `layout=A` has no Part. Selecting `/World:layout=B` exposes `/World/Part:color`, which can then select `blue`.
- `same-prim.usda`: the default `zLayout=A` has no aColor set. Selecting `/World:zLayout=B` exposes `/World:aColor=blue` on the same prim, despite its earlier alphabetical name.

The tests also verify that a later choice hiding an already selected set is unknown, and that input map insertion order has no effect. Combinations requiring unspecified intermediate choices or mutually exclusive final sets are intentionally unsupported.
