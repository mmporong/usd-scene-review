# Synthetic fixtures

All USD scenes in this directory are newly authored for this project. They contain basic USD schema geometry only; no NVIDIA or third-party model data is included.

`dependency-change/before` and `dependency-change/after` have byte-identical root layers. Only `parts.usda` changes: the assembly translates one metre along X while the child keeps its local pose. Expected result: assembly local/world change, child world change grouped under `/World`.

The unit suite generates additional tiny temporary scenes for incomplete dependencies, configuration mismatches, inactive subtrees, hidden authored opinions, equivalent rotations and nonrigid matrices. Temporary inputs and outputs are removed after each test.

`variant-dependencies/` contains nested-prim and same-prim variant selection dependencies, including final-configuration rejection tests.
