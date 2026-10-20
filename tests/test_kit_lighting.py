"""Real USD session lighting without Kit imports or external rig references."""
import ast
from pathlib import Path
import unittest
from pxr import Usd, UsdGeom, UsdLux


class ReviewLightingTests(unittest.TestCase):
    from usd_scene_review.preview import prepare_lighting
    prepare = staticmethod(prepare_lighting)

    def test_unlit_stage_gets_only_owned_session_light(self):
        stage = Usd.Stage.CreateInMemory()
        world = UsdGeom.Xform.Define(stage, '/World').GetPrim()
        stage.SetDefaultPrim(world)
        UsdGeom.Cube.Define(stage, '/World/_UsdSceneReviewLight')
        original = stage.GetRootLayer().ExportToString()
        self.prepare(stage)
        light = stage.GetPrimAtPath('/World/_UsdSceneReviewLight_')
        self.assertTrue(UsdLux.LightAPI(light))
        self.assertEqual(light.GetPrimStack()[0].layer, stage.GetSessionLayer())
        self.assertEqual(stage.GetRootLayer().ExportToString(), original)
        self.assertEqual(set(stage.GetUsedLayers()), {stage.GetRootLayer(), stage.GetSessionLayer()})
        session = stage.GetSessionLayer().ExportToString()
        self.prepare(stage)
        self.assertEqual(stage.GetSessionLayer().ExportToString(), session)

    def test_existing_authored_light_is_preserved(self):
        stage = Usd.Stage.CreateInMemory()
        UsdLux.DomeLight.Define(stage, '/Existing').CreateIntensityAttr(250)
        original = stage.GetRootLayer().ExportToString()
        session = stage.GetSessionLayer().ExportToString()
        self.prepare(stage)
        self.assertEqual(stage.GetRootLayer().ExportToString(), original)
        self.assertEqual(stage.GetSessionLayer().ExportToString(), session)
