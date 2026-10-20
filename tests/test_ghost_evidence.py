import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdPhysics
from usd_scene_review import create_snapshot, load_snapshot, compare
from usd_scene_review.ghost import extract, GhostOverlay
from usd_scene_review.evidence import evidence_rows
from usd_scene_review.preview import prepare_lighting


class GhostEvidenceTests(unittest.TestCase):
    def test_complete_world_transform_reset_and_no_physics(self):
        stage = Usd.Stage.CreateInMemory()
        parent = UsdGeom.Xform.Define(stage, '/Parent')
        parent.AddTranslateOp().Set((10, 20, 30))
        parent.AddRotateXYZOp().Set((20, 30, 40))
        parent.AddScaleOp().Set((2, 3, 4))
        cube = UsdGeom.Cube.Define(stage, '/Parent/Cube')
        cube.AddTranslateOp().Set((1, 2, 3))
        UsdPhysics.CollisionAPI.Apply(cube.GetPrim())
        reset = UsdGeom.Cube.Define(stage, '/Parent/Reset')
        reset.AddTranslateOp().Set((4, 5, 6)); reset.SetResetXformStack(True)
        before = stage.GetRootLayer().ExportToString()
        snapshot = SimpleNamespace(stage=stage, manifest={'config': {'time': 'default'}})
        data = extract(snapshot, '/Parent')
        self.assertEqual(data['status'], 'ready')
        stage.SetEditTarget(stage.GetSessionLayer())
        overlay = GhostOverlay(stage, Sdf.Path('/Review'))
        self.assertEqual(overlay.show(data)['count'], 2)
        for i, item in enumerate(data['geometry']):
            ghost = stage.GetPrimAtPath('/Review/OldPoseGhost/Geometry_' + str(i))
            expected = UsdGeom.XformCache().GetLocalToWorldTransform(stage.GetPrimAtPath(item['source_path']))
            actual = UsdGeom.XformCache().GetLocalToWorldTransform(ghost)
            self.assertTrue(Gf.IsClose(expected, actual, 1e-8))
            self.assertFalse(ghost.HasAPI(UsdPhysics.CollisionAPI))
            self.assertFalse(ghost.GetReferences().GetPrim().HasAuthoredReferences())
        overlay.clear()
        self.assertFalse(stage.GetPrimAtPath('/Review/OldPoseGhost'))
        self.assertEqual(stage.GetRootLayer().ExportToString(), before)

    def test_unsupported_and_limits_fail_closed(self):
        stage = Usd.Stage.CreateInMemory()
        cube = UsdGeom.Cube.Define(stage, '/C')
        snap = SimpleNamespace(stage=stage, manifest={'config': {'time': 'default'}})
        self.assertEqual(extract(snap, '/C', max_prims=0)['status'], 'unsupported')
        cube.GetSizeAttr().Set(float('nan'))
        self.assertEqual(extract(snap, '/C')['status'], 'unsupported')
        UsdGeom.Sphere.Define(stage, '/Sphere')
        self.assertEqual(extract(snap, '/Sphere')['status'], 'unsupported')
        cube.GetSizeAttr().Set(2)
        cube.AddTranslateOp().Set((1, 0, 0), 1)
        self.assertEqual(extract(snap, '/C')['status'], 'unsupported')

    def test_inherited_guide_and_skeleton_are_not_fabricated(self):
        from pxr import UsdSkel
        stage = Usd.Stage.CreateInMemory()
        parent = UsdGeom.Xform.Define(stage, '/Parent')
        UsdGeom.Cube.Define(stage, '/Parent/Cube')
        snap = SimpleNamespace(stage=stage, manifest={'config': {'time': 'default'}})
        parent.CreatePurposeAttr('guide')
        self.assertEqual(extract(snap, '/Parent')['status'], 'unsupported')
        parent.GetPurposeAttr().Clear()
        UsdSkel.BindingAPI.Apply(parent.GetPrim()).CreateSkeletonRel().SetTargets(['/Skeleton'])
        self.assertEqual(extract(snap, '/Parent')['status'], 'unsupported')

    def test_mesh_shape_attributes_and_normalized_light_preserve_source(self):
        stage = Usd.Stage.CreateInMemory()
        mesh = UsdGeom.Mesh.Define(stage, '/Mesh')
        mesh.CreatePointsAttr([(0, 0, 0), (1, 0, 0), (0, 1, 0)])
        mesh.CreateFaceVertexCountsAttr([3]); mesh.CreateFaceVertexIndicesAttr([0, 1, 2])
        mesh.CreateSubdivisionSchemeAttr('none'); mesh.CreateOrientationAttr('leftHanded')
        mesh.CreateNormalsAttr([(0, 0, 1)]); mesh.SetNormalsInterpolation('constant')
        light = UsdLux.DomeLight.Define(stage, '/Light'); light.CreateIntensityAttr(23)
        original = stage.GetRootLayer().ExportToString()
        data = extract(SimpleNamespace(stage=stage, manifest={'config': {'time': 'default'}}), '/Mesh')
        stage.SetEditTarget(stage.GetSessionLayer())
        overlay = GhostOverlay(stage, Sdf.Path('/Review')); overlay.show(data)
        copied = UsdGeom.Mesh(stage.GetPrimAtPath('/Review/OldPoseGhost/Geometry_0'))
        self.assertEqual(copied.GetNormalsInterpolation(), 'constant')
        self.assertEqual(copied.GetOrientationAttr().Get(), 'leftHanded')
        prepare_lighting(stage, normalized=True)
        self.assertEqual(light.GetIntensityAttr().Get(), 0)
        self.assertEqual(stage.GetPrimAtPath('/_UsdSceneReviewLight').GetAttribute('inputs:intensity').Get(), 1000)
        self.assertEqual(stage.GetRootLayer().ExportToString(), original)

    def test_comparator_evidence_human_decision_cannot_waive_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); manifests = []
            for side, y in [('A', 0), ('B', .2)]:
                source = root / (side + '.usda'); stage = Usd.Stage.CreateNew(str(source))
                UsdGeom.SetStageMetersPerUnit(stage, 1)
                UsdGeom.SetStageUpAxis(stage, 'Z')
                parent = UsdGeom.Xform.Define(stage, '/P'); parent.AddTranslateOp().Set((0, y, 0))
                UsdGeom.Cube.Define(stage, '/P/C')
                stage.GetRootLayer().Save(); manifests.append(create_snapshot(source, root / side))
            report = compare(*manifests, policy={'max_translation': .1})
            change = next(c for c in report['changes'] if c['path'] == '/P/C')
            rows = dict(evidence_rows(report, change, {'disposition': 'intentional', 'reason': 'planned move'}))
            self.assertEqual(rows['World delta [m]'], '(0, 0.2, 0)')
            self.assertEqual(rows['Local delta [stage units]'], '(0, 0, 0)')
            self.assertIn('ANCESTOR', rows['Motion'])
            self.assertIn('FAIL', rows['Independent policy'])
            self.assertIn('UNKNOWN', rows['Clash'])
            self.assertIn('INTENTIONAL', rows['Human review'])
            self.assertIn('no policy waiver', rows['Human review'])
