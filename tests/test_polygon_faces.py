import math
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from pxr import Usd,UsdGeom
from usd_scene_review import create_snapshot,load_snapshot
from usd_scene_review.scene_faces import old_faces
from usd_scene_review.polygon_faces import triangulate,Budget


def area(points,triangle):
    a,b,c=[points[index] for index in triangle]
    return ((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))/2


class PolygonFacesTests(unittest.TestCase):
    def test_native_record_preserves_support_limits_cleanup_and_honest_diagnostics(self):
        root=Path(__file__).resolve().parents[1];record=json.loads((root/'diagnostics/polygon-ui-faces-v1.json').read_text())
        self.assertEqual((record['native']['candidate_checks'],record['native']['outer_checks']),(48,18))
        self.assertIn('reflected parent UI faces 1',record['native']['checks'])
        self.assertTrue(record['native']['working_stage_preserved']);self.assertFalse(record['native']['owned_resources_remaining'])
        self.assertTrue(record['lease']['naturally_released']);self.assertEqual(record['shutdown']['process_exit'],0)
        self.assertFalse(record['shutdown']['strict_clean_shutdown']);self.assertFalse(record['limits']['actual_mouse_tested'])
        self.assertFalse(record['limits']['live_ab_guard_removed']);self.assertEqual(record['initial_cpu_regression']['failures'],1)
        self.assertEqual(hashlib.sha256((root/'examples/usd-scene-review-polygon-faces.png').read_bytes()).hexdigest(),record['capture']['public_sha256'])

    def test_concave_notch_preserves_area_and_excludes_notch_both_windings(self):
        p=[(0,0,0),(3,0,0),(3,3,0),(2,3,0),(2,1,0),(1,1,0),(1,3,0),(0,3,0)]
        for ring,sign in ((list(range(8)),1),(list(reversed(range(8))),-1)):
            triangles=triangulate(p,ring)
            self.assertEqual(len(triangles),6)
            self.assertEqual(triangles,triangulate(p,ring))
            self.assertAlmostEqual(sum(area(p,tri) for tri in triangles),sign*7)
            for tri in triangles:
                center=[sum(p[index][axis] for index in tri)/3 for axis in range(2)]
                self.assertFalse(1<center[0]<2 and 1<center[1]<3)
                self.assertGreater(sign*area(p,tri),0)

    def test_quads_tilted_planes_scales_and_degenerate_rejections(self):
        for scale in (1e-20,1,1e20):
            p=[(0,0,0),(scale,0,scale),(scale,scale,2*scale),(0,scale,scale)]
            self.assertEqual(len(triangulate(p,[0,1,2,3])),2)
        for p,ring in (([(0,0,0),(1,1,0),(0,1,0),(1,0,0)],[0,1,2,3]),
            ([(0,0,0),(1,0,0),(1,1,.1),(0,1,0)],[0,1,2,3]),
            ([(0,0,0),(1,0,0),(2,0,0),(2,1,0)],[0,1,2,3]),
            ([(0,0,0),(1,0,0),(0,1,0)],[0,1,1]),
            ([(0,0,0),(1,0,0),(0,1,0)],[0,1,4]),
            ([(0,0,0),(1,0,0),(math.nan,1,0)],[0,1,2])):
            with self.subTest(p=p,ring=ring),self.assertRaises(ValueError):triangulate(p,ring)
        with self.assertRaises(ValueError):triangulate([(0,0,0),(1,0,0),(0,1,0)],[0,1,2],Budget(0))
        with self.assertRaises(ValueError):triangulate([(0,0,0)]*257,list(range(257)))
        with self.assertRaisesRegex(ValueError,'self-intersection'):
            triangulate([(0,0,0),(3,0,0),(0,2,0),(3,3,0),(0,3,0)],list(range(5)))

    def test_usd_holes_orientation_negative_scale_parent_and_read_only(self):
        for orientation,sign in (('rightHanded',1),('leftHanded',-1)):
            with self.subTest(orientation=orientation),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);source=root/'scene.usda';stage=Usd.Stage.CreateNew(str(source))
                parent=UsdGeom.Xform.Define(stage,'/Parent');parent.AddTranslateOp().Set((3,4,5));parent.AddScaleOp().Set((-2,3,1))
                mesh=UsdGeom.Mesh.Define(stage,'/Parent/Shape');mesh.CreateSubdivisionSchemeAttr('none');mesh.CreateOrientationAttr(orientation)
                mesh.CreatePointsAttr([(0,0,0),(1,0,0),(1,1,0),(0,1,0),(2,0,0),(3,0,0),(2,1,0)])
                mesh.CreateFaceVertexCountsAttr([4,3]);mesh.CreateFaceVertexIndicesAttr([0,1,2,3,4,5,6]);mesh.CreateHoleIndicesAttr([1])
                stage.GetRootLayer().Save();stage=None;snapshot=load_snapshot(create_snapshot(source,root/'snapshot'))
                before=[layer.ExportToString() for layer in snapshot.stage.GetLayerStack()]
                result=old_faces(snapshot,'/Parent');self.assertEqual(result['status'],'ready');self.assertEqual(result['triangles'],2)
                p=result['meshes'][0]['positions'];self.assertAlmostEqual(sum(area(p,(i,i+1,i+2)) for i in (0,3)),sign*6)
                self.assertEqual(len(result['wires']),8) # source quad perimeter, no diagonal or hole edges
                self.assertEqual(before,[layer.ExportToString() for layer in snapshot.stage.GetLayerStack()])
