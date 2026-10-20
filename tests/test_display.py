import copy
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from pxr import Gf, Usd, UsdGeom, UsdShade
from usd_scene_review import compare, create_snapshot, load_snapshot
from usd_scene_review.display import ReviewDisplay, camera_spec, world_bounds
from usd_scene_review.measurements import measurements, quaternion, axis_magnitudes


def matrix(value):
    return [[float(x) for x in row] for row in value]


class DisplayTests(unittest.TestCase):
    def test_real_snapshots_propagation_units_and_preservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifests = []
            sources = []
            for side, offset in [('a', 0), ('b', 25)]:
                source = root / (side + '.usda')
                stage = Usd.Stage.CreateNew(str(source))
                UsdGeom.SetStageMetersPerUnit(stage, .01)
                UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
                parent = UsdGeom.Xform.Define(stage, '/World')
                parent.AddTranslateOp().Set(Gf.Vec3d(offset, 0, 0))
                child = UsdGeom.Cube.Define(stage, '/World/Part')
                child.AddTranslateOp().Set(Gf.Vec3d(1, 2, 3))
                stage.GetRootLayer().Save()
                sources.append((source, source.read_bytes(), stage.GetRootLayer().dirty))
                manifests.append(create_snapshot(source, root / side))
            report = compare(*manifests)
            change = next(c for c in report['changes'] if c['path'] == '/World/Part')
            data = measurements(report, change)
            self.assertEqual(change['provenance'], 'parent-propagated')
            self.assertEqual(data['spaces']['local']['delta'], [0, 0, 0])
            self.assertEqual(data['spaces']['world']['delta'], [25, 0, 0])
            self.assertEqual(data['spaces']['world']['delta_meters'], [.25, 0, 0])
            self.assertIn('ANCESTOR', data['motion'])
            for source, contents, dirty in sources:
                self.assertEqual(source.read_bytes(), contents)
                reopened = Usd.Stage.Open(str(source)); self.assertEqual(reopened.GetRootLayer().dirty, dirty)
            changed = copy.deepcopy(report)
            changed['stage_metadata']['meters_per_unit']['after'] = 1
            self.assertIsNone(measurements(changed, change)['spaces']['world']['delta'])
            changed['stage_metadata']['meters_per_unit']['before'] = True
            self.assertFalse(measurements(changed, change)['coordinate_match'])

    def test_tiny_camera_clipping_and_no_geometry(self):
        spec = camera_spec({'A': [[0, 0, 0], [3e-10, 0, 0]]}, 'Z')
        self.assertLess(spec['clipping'][0], spec['clipping'][1])
        with self.assertRaises(ValueError):
            camera_spec({'A': None, 'B': None}, 'Z')

    def test_extreme_finite_values_remain_unavailable(self):
        with self.assertRaises(ValueError):
            camera_spec({'A': [[-1e308, 0, 0], [1e308, 1, 1]]}, 'Z')
        m = matrix(Gf.Matrix4d(1)); m[3][0] = 1e308
        n = matrix(Gf.Matrix4d(1)); n[3][0] = -1e308
        report = {'stage_metadata': {'meters_per_unit': {'before': 100, 'after': 100},
                                    'up_axis': {'before': 'Z', 'after': 'Z'}}}
        change = {'observed': {'before': {'active': True, 'world': m},
                               'after': {'active': True, 'world': n}}}
        data = measurements(report, change)['spaces']['world']
        self.assertIsNone(data['delta']); self.assertIsNone(data['delta_meters'])
        self.assertIsNone(data['meters']['before'])

    def test_rotation_conservative_and_pi_sign(self):
        rotation = matrix(Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0, 0, 1), 180)))
        self.assertEqual(quaternion(rotation), [0, 0, 0, 1])
        for diagonal in [(2, 1, 1), (-1, 1, 1), (0, 1, 1)]:
            m = matrix(Gf.Matrix4d().SetScale(Gf.Vec3d(*diagonal)))
            self.assertIsNone(quaternion(m))
        shear = matrix(Gf.Matrix4d(1)); shear[0][1] = .3
        self.assertIsNone(axis_magnitudes(shear))
        self.assertIsNone(quaternion(shear))
        self.assertEqual(axis_magnitudes(matrix(Gf.Matrix4d().SetScale(Gf.Vec3d(2, 3, 4)))), [2, 3, 4])

    def test_session_material_outline_camera_and_visibility(self):
        stage = Usd.Stage.CreateInMemory()
        UsdGeom.Scope.Define(stage, '/_UsdSceneReviewDisplay')
        cube = UsdGeom.Cube.Define(stage, '/World/Cube')
        other = UsdGeom.Cube.Define(stage, '/World/Other')
        original = UsdShade.Material.Define(stage, '/World/Original')
        UsdShade.MaterialBindingAPI.Apply(stage.GetPrimAtPath('/World')).Bind(original, UsdShade.Tokens.strongerThanDescendants)
        subset = UsdGeom.Subset.Define(stage, '/World/Cube/Subset')
        subset.CreateElementTypeAttr('face'); subset.CreateFamilyNameAttr('materialBind'); subset.CreateIndicesAttr([0])
        UsdShade.MaterialBindingAPI.Apply(subset.GetPrim()).Bind(original)
        hidden = UsdGeom.Cube.Define(stage, '/World/Hidden'); hidden.CreateVisibilityAttr('invisible')
        source = stage.GetRootLayer().ExportToString(); dirty = stage.GetRootLayer().dirty
        raw = SimpleNamespace(stage=stage, manifest={'config': {'time': 'default'}})
        bounds = world_bounds(raw, '/World/Cube')
        self.assertIsNone(world_bounds(raw, '/World/Hidden'))
        self.assertIsNone(world_bounds(raw, '/Missing'))
        spec = camera_spec({'A': bounds, 'B': [[10, -1, -1], [12, 1, 1]]}, 'Z')
        stage.SetEditTarget(stage.GetSessionLayer())
        display = ReviewDisplay(stage)
        self.assertNotEqual(str(display.root), '/_UsdSceneReviewDisplay')
        a = display.style('/World/Cube', 'A', bounds)
        self.assertEqual(a['selected_geometry'], 1)
        self.assertEqual(len(UsdGeom.BasisCurves(stage.GetPrimAtPath(display.root.AppendChild('SelectedWorldBounds'))).GetPointsAttr().Get()), 192)
        for prim in (cube.GetPrim(), subset.GetPrim()):
            self.assertEqual(UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()[0].GetPath(), display.materials['A'].GetPath())
        self.assertEqual(UsdShade.MaterialBindingAPI(other.GetPrim()).ComputeBoundMaterial()[0].GetPath(), display.materials['Context'].GetPath())
        viewport = SimpleNamespace()
        display.set_camera(spec, viewport); display.set_camera(spec, viewport)
        before = UsdGeom.Xformable(stage.GetPrimAtPath(viewport.camera_path)).GetLocalTransformation()
        display.style('/World/Cube', 'B', bounds); display.set_camera(spec, viewport)
        self.assertEqual(before, UsdGeom.Xformable(stage.GetPrimAtPath(viewport.camera_path)).GetLocalTransformation())
        self.assertEqual(len(UsdGeom.BasisCurves(stage.GetPrimAtPath(display.root.AppendChild('SelectedWorldBounds'))).GetPointsAttr().Get()), 24)
        cleared = display.style(None, 'B', None)
        self.assertEqual(cleared['selected_geometry'], 0)
        self.assertFalse(stage.GetPrimAtPath(display.root.AppendChild('SelectedWorldBounds')))
        self.assertEqual(UsdShade.MaterialBindingAPI(cube.GetPrim()).ComputeBoundMaterial()[0].GetPath(), display.materials['Context'].GetPath())
        self.assertEqual(hidden.ComputeVisibility(), 'invisible')
        self.assertEqual(stage.GetRootLayer().ExportToString(), source)
        self.assertEqual(stage.GetRootLayer().dirty, dirty)

if __name__ == '__main__':
    unittest.main()
