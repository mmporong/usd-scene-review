"""CPU fixture semantics only; not proof of SDK resource reuse or cleanup."""
import ast
from pathlib import Path
import unittest
from pxr import Gf,Usd,UsdGeom,UsdLux,UsdShade,Sdf


class ReuseCandidateTests(unittest.TestCase):
    def test_same_paths_remain_independent_with_real_light_material_and_pose_changes(self):
        path=Path(__file__).resolve().parents[1]/'tools/viewport_reuse_candidate.py'
        node=next(n for n in ast.parse(path.read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef) and n.name=='revision_fixture')
        env=dict(Gf=Gf,Usd=Usd,UsdGeom=UsdGeom,UsdLux=UsdLux,UsdShade=UsdShade,Sdf=Sdf)
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),env)
        a,b=[env['revision_fixture'](s) for s in ('A','B')]
        self.assertNotEqual(a.GetRootLayer().identifier,b.GetRootLayer().identifier)
        for stage,side,other,x,light in ((a,'A','B',-2,1000),(b,'B','A',2,500)):
            self.assertTrue(stage.GetPrimAtPath('/World/Only'+side))
            self.assertFalse(stage.GetPrimAtPath('/World/Only'+other))
            self.assertEqual(stage.GetPrimAtPath('/World/Item').GetAttribute('xformOp:translate').Get()[0],x)
            self.assertEqual(stage.GetPrimAtPath('/World/Light').GetAttribute('inputs:intensity').Get(),light)
            self.assertEqual(stage.GetEditTarget().GetLayer(),stage.GetSessionLayer())
        self.assertNotEqual(a.GetPrimAtPath('/World/Looks/Material/Shader').GetAttribute('inputs:diffuseColor').Get(),
                            b.GetPrimAtPath('/World/Looks/Material/Shader').GetAttribute('inputs:diffuseColor').Get())
        self.assertEqual(UsdGeom.Camera(a.GetPrimAtPath('/ReviewCamera')).GetCamera().transform,
                         UsdGeom.Camera(b.GetPrimAtPath('/ReviewCamera')).GetCamera().transform)
        before=a.GetRootLayer().ExportToString()
        b.GetPrimAtPath('/World/Item').GetAttribute('xformOp:translate').Set((9,0,0))
        self.assertEqual(a.GetRootLayer().ExportToString(),before)
        self.assertEqual(a.GetPrimAtPath('/World/Item').GetAttribute('xformOp:translate').Get()[0],-2)
        with self.assertRaises(ValueError):env['revision_fixture']('C')
