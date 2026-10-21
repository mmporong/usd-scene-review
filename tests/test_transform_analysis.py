import json
import math
from pathlib import Path
import tempfile
import unittest
from pxr import Gf, Usd, UsdGeom
from usd_scene_review import compare, create_snapshot
from usd_scene_review.compare import rigid_delta
from usd_scene_review.transform_analysis import analyze, analyze_change, canonical_quaternion
from usd_scene_review.measurements import measurements, detail_rows
from usd_scene_review.cli import render_html


META = {'meters_per_unit': {'before': 1.0, 'after': 1.0},
        'up_axis': {'before': 'Z', 'after': 'Z'}}


def matrix(degrees=0, scale=(1, 1, 1)):
    value = Gf.Matrix4d().SetScale(Gf.Vec3d(*scale)) * Gf.Matrix4d().SetRotate(
        Gf.Rotation(Gf.Vec3d(0, 0, 1), degrees))
    return [list(row) for row in value]


def observation(a, b):
    return {s: {'active': True, 'local': m, 'world': m} for s, m in [('before', a), ('after', b)]}


class TransformAnalysisTests(unittest.TestCase):
    def test_shortest_angles_sign_and_scale_are_effective_only(self):
        for before, after, expected in [(350, 10, 20), (0, 180, 180), (180, -180, 0)]:
            with self.subTest(before=before, after=after):
                a, b = matrix(before, (2, 3, 4)), matrix(after, (2, 3, 4))
                result = analyze_change(observation(a, b), META)
                self.assertAlmostEqual(result['spaces']['world']['orientation_delta']['degrees'], expected, places=5)
                self.assertEqual(rigid_delta(a, b)['status'], 'unknown')
                self.assertEqual(analyze(a)['axis_magnitudes'], [2, 3, 4])
        self.assertEqual(canonical_quaternion([0, 0, 0, -1]), canonical_quaternion([0, 0, 0, 1]))
        result = analyze_change(observation(matrix(30, (2, 3, 4)), matrix(30, (5, 6, 7))), META)
        self.assertEqual(result['spaces']['local']['orientation_delta']['degrees'], 0)

    def test_explicit_refusals_and_translation_validity(self):
        cases = []
        m = matrix(); m[0][1] = .3; cases.append((m, 'shear-or-nonorthogonal-basis'))
        cases.extend([(matrix(scale=(-1, 1, 1)), 'reflection'),
                      (matrix(scale=(0, 1, 1)), 'singular-or-near-zero-axis'),
                      (matrix(scale=(1e-11, 1, 1)), 'ill-conditioned-basis')])
        m = matrix(); m[0][0] = float('nan'); cases.append((m, 'nonfinite-or-nonnumeric-matrix'))
        for m, reason in cases:
            with self.subTest(reason=reason):
                result = analyze(m)
                self.assertEqual(result['orientation']['status'], 'unknown')
                self.assertEqual(result['orientation']['reason'], reason)
                self.assertEqual(result['translation']['status'], 'known')
        m = matrix(); m[0][3] = .1
        self.assertEqual(analyze(m)['translation']['reason'], 'non-affine-matrix')
        m = matrix(); m[3][0] = float('nan')
        self.assertEqual(analyze(m)['translation']['reason'], 'nonfinite-translation')
        self.assertEqual(analyze(m)['orientation']['status'], 'unknown')

    def test_coordinate_metadata_gates_cross_revision_deltas(self):
        for metadata in [dict(META, meters_per_unit={'before': .01, 'after': 1}),
                         dict(META, up_axis={'before': 'Y', 'after': 'Z'}),
                         dict(META, meters_per_unit={'before': 1, 'after': float('nan')})]:
            result = analyze_change(observation(matrix(0), matrix(20)), metadata)
            self.assertEqual(result['spaces']['world']['orientation_delta']['status'], 'unknown')
            self.assertEqual(result['spaces']['world']['translation_delta']['status'], 'unknown')
            self.assertEqual(result['spaces']['world']['before']['orientation']['status'], 'known')

    def test_both_revision_reset_boundaries_and_parent_reset(self):
        for mode in ('child-enables-reset', 'child-disables-reset', 'parent-reset', 'child-stays-reset'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); manifests = []
                for side in ('A', 'B'):
                    source = root / ('source-'+side); source.mkdir()
                    path = source / 'scene.usda'; stage = Usd.Stage.CreateNew(str(path))
                    UsdGeom.SetStageMetersPerUnit(stage, 1); UsdGeom.SetStageUpAxis(stage, 'Z')
                    grand = UsdGeom.Xform.Define(stage, '/Root'); grand.AddTranslateOp().Set((10, 0, 0))
                    parent = UsdGeom.Xform.Define(stage, '/Root/P')
                    parent.AddTranslateOp().Set((2 if mode == 'parent-reset' else (10 if side == 'A' else 20), 0, 0))
                    child = UsdGeom.Cube.Define(stage, '/Root/P/C'); child.AddTranslateOp().Set((1, 0, 0))
                    if mode == 'parent-reset': parent.SetResetXformStack(side == 'A')
                    else: child.SetResetXformStack(mode == 'child-stays-reset' or (side == 'B' if mode == 'child-enables-reset' else side == 'A'))
                    stage.GetRootLayer().Save(); manifests.append(create_snapshot(path, root / side))
                report = compare(*manifests)
                changes = {c['path']: c for c in report['changes']}
                if mode == 'child-stays-reset':
                    self.assertNotIn('/Root/P/C', changes)
                else:
                    child = changes['/Root/P/C']
                    self.assertTrue(child['motion_context']['boundary_changed'])
                    if mode == 'parent-reset':
                        self.assertEqual(child['parent_cause'], '/Root/P')
                        self.assertEqual(child['provenance'], 'parent-propagated')
                    else:
                        self.assertEqual(child['provenance'], 'local')
                        self.assertNotIn('parent_cause', child)

    def test_report_html_and_ui_share_effective_values_without_rigid_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifests = []
            for side, angle in [('A', 350), ('B', 10)]:
                path = root / (side + '.usda'); stage = Usd.Stage.CreateNew(str(path))
                UsdGeom.SetStageMetersPerUnit(stage, 1); UsdGeom.SetStageUpAxis(stage, 'Z')
                cube = UsdGeom.Cube.Define(stage, '/C')
                cube.AddTransformOp().Set(Gf.Matrix4d(*[v for row in matrix(angle, (2, 3, 4)) for v in row]))
                stage.GetRootLayer().Save(); manifests.append(create_snapshot(path, root / side))
            report = compare(*manifests, policy={'max_rotation_degrees': 1})
            change = report['changes'][0]; data = measurements(report, change)['spaces']['world']
            self.assertAlmostEqual(data['effective_rotation_degrees'], 20, places=5)
            self.assertIsNone(data['rotation_degrees'])
            self.assertEqual(report['policy'][0]['status'], 'unknown')
            self.assertEqual(report['clash']['status'], 'unknown')
            self.assertIn('scale-normalized', json.dumps(report))
            self.assertIn('20 deg shortest; scale-normalized, not authored', render_html(report))
            self.assertTrue(any('20 deg shortest; scale-normalized, not authored' in row[-1] for row in detail_rows(report, change)))

    def test_compensated_parent_motion_is_not_world_propagation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); manifests = []
            for side, offset in [('A', 0), ('B', 1)]:
                source = root / ('source-'+side); source.mkdir()
                path = source/'scene.usda'; stage = Usd.Stage.CreateNew(str(path))
                parent = UsdGeom.Xform.Define(stage, '/Parent')
                parent.AddTranslateOp().Set((offset, 0, 0))
                child = UsdGeom.Cube.Define(stage, '/Parent/Child')
                child.AddTranslateOp().Set((-offset, 0, 0))
                stage.GetRootLayer().Save()
                manifests.append(create_snapshot(path, root/side))
            report = compare(*manifests)
            child = next(c for c in report['changes'] if c['path']=='/Parent/Child')
            self.assertNotIn('world', child['fields'])
            self.assertNotIn('parent_cause', child)
            self.assertEqual(child['motion_context']['changed_ancestors'], ['/Parent'])
            self.assertEqual(report['parent_groups'], [])
