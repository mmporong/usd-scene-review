from pathlib import Path
import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch
from pxr import Gf,Usd,UsdGeom
from usd_scene_review import create_snapshot,load_snapshot
from usd_scene_review.scene_faces import old_faces


class SceneFacesTests(unittest.TestCase):
    def test_native_record_retains_failed_visual_baseline_color_checks_and_limits(self):
        root=Path(__file__).resolve().parents[1]
        record=json.loads((root/'diagnostics/scene-ui-faces-v1.json').read_text())
        self.assertIn('failed',record['before']['visual_inspection'])
        self.assertEqual(record['after']['candidate_checks'],39)
        self.assertGreater(record['after']['face_pixels']['faint_green_match_ratio'],.95)
        self.assertGreater(record['after']['face_pixels']['reselected_green_match_ratio'],.95)
        self.assertTrue(record['after']['working_stage_preserved'])
        self.assertFalse(record['after']['owned_resources_remaining'])
        self.assertEqual(record['after']['shutdown']['process_exit'],0)
        self.assertFalse(record['after']['shutdown']['strict_clean_shutdown'])
        self.assertTrue(record['after']['lease']['naturally_released'])
        self.assertFalse(record['limits']['real_mouse_tested'])
        self.assertFalse(record['limits']['general_mesh_ghost_complete'])
        self.assertFalse(record['limits']['live_ab_guard_removed'])
        self.assertEqual(hashlib.sha256((root/'examples/usd-scene-review-scene-ui-faces.png').read_bytes()).hexdigest(),record['capture']['public_sha256'])

    def build(self,root,kind='triangle',hole=False):
        stage=Usd.Stage.CreateNew(str(root/'scene.usda'))
        parent=UsdGeom.Xform.Define(stage,'/Root');parent.AddTranslateOp().Set((3,4,5))
        parent.AddRotateZOp().Set(90)
        if kind=='cube':UsdGeom.Cube.Define(stage,'/Root/Shape').CreateSizeAttr(2)
        else:
            mesh=UsdGeom.Mesh.Define(stage,'/Root/Shape');mesh.CreateSubdivisionSchemeAttr('none')
            mesh.CreatePointsAttr([(0,0,0),(1,0,0),(0,1,0),(1,1,0)])
            mesh.CreateFaceVertexCountsAttr([3,3]);mesh.CreateFaceVertexIndicesAttr([0,1,2,1,3,2])
            if kind=='subdiv':mesh.GetSubdivisionSchemeAttr().Set('catmullClark')
            if kind=='quad':mesh.GetFaceVertexCountsAttr().Set([4]);mesh.GetFaceVertexIndicesAttr().Set([0,1,3,2])
            if kind=='animated':mesh.GetPointsAttr().Set([(0,0,0)]*4,1)
            if hole:mesh.CreateHoleIndicesAttr([1])
        stage.GetRootLayer().Save();stage=None
        return load_snapshot(create_snapshot(root/'scene.usda',root/'snapshot'))

    def test_world_faces_holes_alpha_and_read_only_layers(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot=self.build(Path(tmp),hole=True)
            before=[layer.ExportToString() for layer in snapshot.stage.GetLayerStack()]
            plan=old_faces(snapshot,'/Root');self.assertEqual(plan['status'],'ready')
            self.assertEqual(plan['triangles'],1);self.assertEqual(len(plan['wires']),6)
            mesh=plan['meshes'][0]
            self.assertEqual(mesh['vertex_indices'],[0,1,2]);self.assertEqual(mesh['positions'][0],[3,4,5])
            self.assertAlmostEqual(mesh['positions'][1][0],3);self.assertAlmostEqual(mesh['positions'][1][1],5)
            self.assertTrue(all(color==[.12,.95,.22,.22] for color in mesh['colors']))
            self.assertEqual(before,[layer.ExportToString() for layer in snapshot.stage.GetLayerStack()])

    def test_subdivision_polygons_animation_missing_and_budget_fail_explicitly(self):
        for kind in ('subdiv','animated'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as tmp:
                result=old_faces(self.build(Path(tmp),kind),'/Root')
                self.assertEqual(result['status'],'unsupported');self.assertFalse(result['meshes'])
        with tempfile.TemporaryDirectory() as tmp:
            snapshot=self.build(Path(tmp),'cube')
            self.assertEqual(old_faces(snapshot,'/Missing')['status'],'unsupported')
            result=old_faces(snapshot,'/Root');self.assertEqual(result['triangles'],12);self.assertEqual(len(result['wires']),24)
            self.assertEqual(result['meshes'][0]['vertex_indices'],list(range(36)))
            self.assertEqual(len(result['meshes'][0]['colors']),36)
            with patch('usd_scene_review.scene_faces.MAX_TRIANGLES',0):
                self.assertEqual(old_faces(snapshot,'/Root')['status'],'unsupported')
