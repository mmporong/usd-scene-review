from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade
from usd_scene_review import compare, create_snapshot
from usd_scene_review.analysis_config import normalize
from usd_scene_review.overlap_analysis import pair_by_id, pair_rows
from usd_scene_review.cli import render_html


class OverlapTests(unittest.TestCase):
    def report(self, before=4, after=.5, mutate=None, config=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifests = []
            for side, offset in [('A', before), ('B', after)]:
                folder = root / side
                folder.mkdir()
                source = folder/'scene.usda'
                stage = Usd.Stage.CreateNew(str(source))
                UsdGeom.SetStageMetersPerUnit(stage, 1)
                UsdGeom.SetStageUpAxis(stage, 'Z')
                UsdGeom.Xform.Define(stage, '/World')
                for name, x in [('Moving', offset), ('Static', 0)]:
                    cube = UsdGeom.Cube.Define(stage, '/World/'+name)
                    cube.CreateSizeAttr(2)
                    cube.AddTranslateOp().Set(Gf.Vec3d(x, 0, 0))
                    # Authored extent is deliberately wrong and must be ignored.
                    cube.CreateExtentAttr([Gf.Vec3f(-100), Gf.Vec3f(100)])
                if mutate:
                    mutate(stage, side)
                stage.GetRootLayer().Save()
                stage = None
                manifests.append(create_snapshot(source, root/('snapshot-'+side)))
            return compare(*manifests, analysis_config=config)

    def test_same_parent_new_pair_and_stationary_object(self):
        report = self.report()
        pair, = report['overlap_analysis']['pairs']
        self.assertEqual(pair['classification'], 'newly-introduced-aabb-overlap')
        self.assertEqual(pair['before']['status'], 'disjoint')
        self.assertEqual(pair['after']['status'], 'overlap')
        self.assertEqual(pair['objects']['after'][1]['bounds_stage'], [[-1, -1, -1], [1, 1, 1]])
        self.assertFalse(any(c['path'] == '/World/Static' for c in report['changes']))
        self.assertEqual(report['clash']['status'], 'unknown')
        self.assertEqual(report['status'], 'changed')
        self.assertEqual(pair['focus_bounds_stage'], [[-1, -1, -1], [5, 1, 1]])
        self.assertEqual(pair_by_id(report, pair['id']), pair)
        with self.assertRaisesRegex(ValueError, 'absent'):
            pair_by_id(report, 'stale')
        for row in pair_rows(report, pair):
            self.assertIn(row[1], render_html(report))
        self.assertEqual(report, self.report())

    def test_classifications_do_not_overclaim(self):
        for before, after, kind in [(.5, .6, 'existing-aabb-overlap'),
                                     (.5, 4, 'resolved-aabb-candidate'),
                                     (2, .5, 'boundary-to-overlap'),
                                     (.5, 2, 'overlap-to-boundary')]:
            with self.subTest(kind=kind):
                self.assertEqual(self.report(before, after)['overlap_analysis']['pairs'][0]['classification'], kind)
        for mode, kind in [('missing', 'added-geometry-overlap'), ('hidden', 'baseline-unknown'),
                           ('unsupported', 'baseline-unknown'), ('container', 'baseline-unknown')]:
            def mutate(stage, side):
                if side != 'A': return
                prim = stage.GetPrimAtPath('/World/Moving')
                if mode == 'missing': stage.RemovePrim(prim.GetPath())
                elif mode == 'hidden': UsdGeom.Imageable(prim).CreateVisibilityAttr('invisible')
                else: prim.SetTypeName('Sphere' if mode == 'unsupported' else 'Xform')
            with self.subTest(mode=mode):
                self.assertEqual(self.report(mutate=mutate)['overlap_analysis']['pairs'][0]['classification'], kind)

    def test_mesh_points_transform_and_exclusions(self):
        def mutate(stage, side):
            stage.RemovePrim('/World/Moving')
            mesh = UsdGeom.Mesh.Define(stage, '/World/Moving')
            mesh.CreatePointsAttr([(-1,-1,-1), (1,-1,-1), (1,1,1), (-1,1,1), (999,999,999)])
            mesh.CreateFaceVertexCountsAttr([4])
            mesh.CreateFaceVertexIndicesAttr([0,1,2,3])
            mesh.CreateExtentAttr([Gf.Vec3f(-999), Gf.Vec3f(999)])
            mesh.AddTranslateOp().Set(Gf.Vec3d(4 if side == 'A' else .5, 0, 0))
        pair = self.report(mutate=mutate)['overlap_analysis']['pairs'][0]
        self.assertEqual(pair['classification'], 'newly-introduced-aabb-overlap')
        self.assertEqual(pair['objects']['after'][0]['point_count'], 4)
        self.assertEqual(pair['objects']['after'][0]['bounds_stage'], [[-.5,-1,-1],[1.5,1,1]])
        def animated(stage, side):
            if side == 'A':
                stage.GetPrimAtPath('/World/Moving').GetAttribute('xformOp:translate').Set(Gf.Vec3d(4,0,0), 1)
        self.assertEqual(self.report(mutate=animated)['overlap_analysis']['pairs'][0]['classification'], 'baseline-unknown')

    def test_budgets_and_coordinate_mismatch_are_auxiliary(self):
        for key in ('max_prims', 'max_geometry', 'max_total_points', 'max_points_per_geometry'):
            cfg = normalize(); cfg['overlap'][key] = 1
            report = self.report(config=cfg)
            self.assertEqual(report['overlap_analysis']['coverage']['status'], 'partial', key)
            self.assertEqual(report['status'], 'changed')
        def mismatch(stage, side):
            if side == 'B': UsdGeom.SetStageUpAxis(stage, 'Y')
        report = self.report(mutate=mismatch)
        self.assertEqual(report['status'], 'unknown')
        self.assertFalse(any(p['classification'] == 'newly-introduced-aabb-overlap'
                             for p in report['overlap_analysis']['pairs']))
        cfg = normalize(); cfg['version'] = True
        with self.assertRaises(ValueError): normalize(cfg)

    def test_subset_displacement_never_supplies_baseline_bounds(self):
        def mutate(stage, side):
            if side != 'A': return
            prim = stage.GetPrimAtPath('/World/Moving')
            prim.SetTypeName('Mesh')
            mesh = UsdGeom.Mesh(prim)
            mesh.CreatePointsAttr([(-1,-1,-1), (1,-1,-1), (1,1,1), (-1,1,1)])
            mesh.CreateFaceVertexCountsAttr([4]); mesh.CreateFaceVertexIndicesAttr([0,1,2,3])
            subset = UsdGeom.Subset.Define(stage, '/World/Moving/DisplacedFace')
            subset.CreateElementTypeAttr('face'); subset.CreateFamilyNameAttr('materialBind')
            subset.CreateIndicesAttr([0])
            material = UsdShade.Material.Define(stage, '/Looks/Displaced')
            shader = UsdShade.Shader.Define(stage, '/Looks/Displaced/Shader')
            shader.CreateIdAttr('UsdPreviewSurface')
            shader.CreateOutput('displacement', Sdf.ValueTypeNames.Float)
            material.CreateDisplacementOutput().ConnectToSource(shader.ConnectableAPI(), 'displacement')
            UsdShade.MaterialBindingAPI.Apply(subset.GetPrim()).Bind(material, materialPurpose='full')
            from usd_scene_review.ghost import extract
            ghost = extract(SimpleNamespace(stage=stage,manifest={'config':{'time':'default'}}), '/World/Moving')
            self.assertEqual(ghost['status'], 'unsupported')
            self.assertIn('Material displacement', ghost['reason'])
        pair = self.report(mutate=mutate)['overlap_analysis']['pairs'][0]
        self.assertEqual(pair['classification'], 'baseline-unknown')
        self.assertEqual(pair['objects']['before'][0]['reason'], 'shader-displacement-unsupported')
        cfg = normalize(); cfg['overlap']['purposes'] = [[]]
        with self.assertRaises(ValueError): normalize(cfg)

    def test_pair_record_budgets_tolerance_and_purpose(self):
        def third(stage, side):
            UsdGeom.Cube.Define(stage, '/World/Third').CreateSizeAttr(2)
        for key in ('max_pairs', 'max_records'):
            cfg = normalize(); cfg['overlap'][key] = 1
            result = self.report(before=.1, after=.2, mutate=third, config=cfg)
            coverage = result['overlap_analysis']['coverage']
            self.assertEqual(coverage['status'], 'partial')
            self.assertGreater(coverage['exclusions']['budget-'+key.removeprefix('max_')], 0)
            self.assertEqual(result['status'], 'changed')
        cfg = normalize(); cfg['overlap']['tolerance_m'] = .1
        result = self.report(before=4, after=2.05, config=cfg)
        self.assertEqual(result['overlap_analysis']['pairs'][0]['after']['status'], 'boundary')
        self.assertEqual(result['overlap_analysis']['pairs'][0]['after']['tolerance_m'], .1)
        cfg['overlap']['purposes'] = ['render']
        result = self.report(config=cfg)
        self.assertEqual(result['overlap_analysis']['coverage']['snapshots']['before']['exclusions'], {'excluded-purpose': 2})
        self.assertEqual(result['overlap_analysis']['pairs'], [])

    def test_context_displacement_is_unknown_for_bounds_and_ghost(self):
        def mutate(stage, side):
            if side != 'A': return
            material = UsdShade.Material.Define(stage, '/Looks/ContextDisplaced')
            shader = UsdShade.Shader.Define(stage, '/Looks/ContextDisplaced/Shader')
            shader.CreateOutput('out', Sdf.ValueTypeNames.Token)
            material.CreateDisplacementOutput('mdl').ConnectToSource(shader.ConnectableAPI(), 'out')
            UsdShade.MaterialBindingAPI.Apply(stage.GetPrimAtPath('/World/Moving')).Bind(material, materialPurpose='preview')
            from usd_scene_review.ghost import extract
            ghost = extract(SimpleNamespace(stage=stage,manifest={'config':{'time':'default'}}), '/World/Moving')
            self.assertEqual(ghost['status'], 'unsupported')
        pair = self.report(mutate=mutate)['overlap_analysis']['pairs'][0]
        self.assertEqual(pair['classification'], 'baseline-unknown')

    def test_nonfinite_stage_units_are_serializable_unknown(self):
        import json
        def mutate(stage, side):
            if side == 'B':
                UsdGeom.SetStageMetersPerUnit(stage, float('nan'))
        result = self.report(mutate=mutate)
        self.assertEqual(result['status'], 'unknown')
        self.assertIn('invalid stage metadata: meters_per_unit', result['reasons'])
        self.assertEqual(result['stage_metadata']['meters_per_unit']['after'], 'nan')
        self.assertEqual(result['clash']['status'], 'unknown')
        json.dumps(result, allow_nan=False)
        self.assertIn('unknown', render_html(result))


if __name__ == '__main__':
    unittest.main()
