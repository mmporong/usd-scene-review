from pathlib import Path
import tempfile
import unittest
from pxr import Gf, Usd, UsdGeom, UsdLux
from usd_scene_review import compare, create_snapshot, load_snapshot
from usd_scene_review.display import ReviewDisplay
from usd_scene_review.in_app_logic import copy_review_camera, focus_plan, pair_light_mode


class InAppLogicTests(unittest.TestCase):
    def test_move_rotate_add_remove_parent_focus_and_values(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);paths=[]
            for side in ('A','B'):
                source=root/('source-'+side);source.mkdir();file=source/'scene.usda'
                stage=Usd.Stage.CreateNew(str(file));UsdGeom.SetStageMetersPerUnit(stage,1);UsdGeom.SetStageUpAxis(stage,'Z')
                parent=UsdGeom.Xform.Define(stage,'/World');parent.AddTranslateOp().Set((0 if side=='A' else 2,0,0))
                UsdGeom.Cube.Define(stage,'/World/Moved').AddTranslateOp().Set((0,0 if side=='A' else 3,0))
                UsdGeom.Cube.Define(stage,'/World/Rotated').AddRotateZOp().Set(0 if side=='A' else 30)
                UsdGeom.Cube.Define(stage,'/World/Inherited')
                UsdGeom.Cube.Define(stage,'/World/'+('Removed' if side=='A' else 'Added'))
                stage.GetRootLayer().Save();paths.append(create_snapshot(file,root/side))
            report=compare(*paths);snapshots={s:load_snapshot(p) for s,p in zip(('A','B'),paths)}
            from usd_scene_review.measurements import measurements
            changes={c['path']:c for c in report['changes']}
            for name in ('Moved','Rotated','Inherited','Added','Removed'):
                path='/World/'+name
                plan=focus_plan(report,snapshots,path)
                self.assertIsNotNone(plan['camera'])
                self.assertEqual(plan['exists']['A'][path],name!='Added')
                self.assertEqual(plan['exists']['B'][path],name!='Removed')
            self.assertEqual(changes['/World/Inherited']['provenance'],'parent-propagated')
            self.assertAlmostEqual(measurements(report,changes['/World/Rotated'])['spaces']['world']['effective_rotation_degrees'],30)
            with self.assertRaises(ValueError):focus_plan(report,snapshots,'/Invented')

    def test_owned_camera_copy_never_authors_source_camera(self):
        stages=[Usd.Stage.CreateInMemory() for _ in range(2)]
        displays=[]
        for stage in stages:
            UsdGeom.Camera.Define(stage,'/SourceCamera')
            stage.SetEditTarget(stage.GetSessionLayer());displays.append(ReviewDisplay(stage))
        roots=[str(d.root) for d in displays];paths=[r+'/Camera' for r in roots]
        for stage,path in zip(stages,paths):UsdGeom.Camera.Define(stage,path)
        before=[s.GetRootLayer().ExportToString() for s in stages]
        a=UsdGeom.Camera(stages[0].GetPrimAtPath(paths[0]));a.CreateProjectionAttr('orthographic');a.CreateHorizontalApertureAttr(50)
        a.AddTransformOp().Set(Gf.Matrix4d().SetTranslate((2,3,4)))
        copy_review_camera(stages[0],paths[0],stages[1],paths[1],roots)
        b=UsdGeom.Camera(stages[1].GetPrimAtPath(paths[1]))
        self.assertEqual(a.GetCamera().transform,b.GetCamera().transform)
        self.assertEqual(b.GetProjectionAttr().Get(),'orthographic')
        self.assertEqual(b.GetHorizontalApertureAttr().Get(),50)
        self.assertEqual(before,[s.GetRootLayer().ExportToString() for s in stages])
        with self.assertRaises(ValueError):copy_review_camera(stages[0],'/SourceCamera',stages[1],paths[1],roots)

    def test_deleted_light_is_not_silently_replaced(self):
        from types import SimpleNamespace
        snapshots={s:SimpleNamespace(stage=Usd.Stage.CreateInMemory()) for s in ('A','B')}
        self.assertTrue(pair_light_mode(snapshots)['fallback_both'])
        UsdLux.DomeLight.Define(snapshots['A'].stage,'/OriginalLight')
        mode=pair_light_mode(snapshots)
        self.assertFalse(mode['fallback_both']);self.assertEqual(mode['counts'],{'A':1,'B':0})
