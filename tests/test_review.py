"""Behavioral checks using newly authored, small local USD scenes."""
from contextlib import redirect_stderr, redirect_stdout
import io
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from pxr import Sdf, Usd, UsdGeom, Gf
from usd_scene_review import create_snapshot, load_snapshot, compare
from usd_scene_review.cli import main, render_html
from usd_scene_review.snapshot import canonical


HEADER = '#usda 1.0\n'


def symlink_or_skip(test, link, target):
    try:
        link.symlink_to(target)
    except OSError as error:
        if getattr(error, 'winerror', None) == 1314:
            test.skipTest('Windows account lacks symbolic-link privilege; no security settings changed')
        raise


def pose_scene(translation=(0, 0, 0), rotation=0, scale=None, child=True, reset=False, child_translation=(0, 1, 0)):
    stage = Usd.Stage.CreateInMemory()
    parent = UsdGeom.Xform.Define(stage, '/World')
    parent.AddTranslateOp().Set(Gf.Vec3d(*translation))
    parent.AddRotateZOp().Set(rotation)
    if scale is not None:
        parent.AddScaleOp().Set(Gf.Vec3f(*scale))
    if child:
        c = UsdGeom.Xform.Define(stage, '/World/Part')
        c.AddTranslateOp().Set(Gf.Vec3d(*child_translation))
        if reset:
            c.SetResetXformStack(True)
    return stage.GetRootLayer().ExportToString()


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='usd-review-test-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.serial = 0

    def source(self, files):
        self.serial += 1
        root = self.base / ('source-' + str(self.serial))
        root.mkdir()
        for name, text in files.items():
            p = root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding='utf-8')
        return root / 'scene.usda'

    def snapshot(self, files, **config):
        source = self.source(files)
        return create_snapshot(source, self.base / ('snapshot-' + str(self.serial)), **config)

    def pair(self, a, b, **config):
        return self.snapshot({'scene.usda': a}, **config), self.snapshot({'scene.usda': b}, **config)

    @staticmethod
    def change(report, path):
        return next(c for c in report['changes'] if c['path'] == path)

    @staticmethod
    def rewrite_manifest(path, mutate):
        manifest = json.loads(path.read_text())
        mutate(manifest)
        path.write_text(canonical(manifest))

    def test_equal_snapshots_are_equal_and_deterministic(self):
        a, b = self.pair(pose_scene(), pose_scene())
        one = compare(a, b)
        self.assertEqual(one['status'], 'equal', one)
        self.assertEqual(one['changes'], [])
        self.assertEqual(canonical(one), canonical(compare(a, b)))
        self.assertEqual(one['clash']['status'], 'unknown')

    def test_unverifiable_resolver_remains_unknown(self):
        with mock.patch('usd_scene_review.local_contract.Ar.GetResolver', return_value=object()):
            manifest = self.snapshot({'scene.usda': pose_scene()})
            snapshot = load_snapshot(manifest)
            self.assertIsNone(snapshot.stage)
            self.assertTrue(any('resolver API' in error for error in snapshot.errors))

    def test_root_equal_dependency_only_change_is_observed(self):
        root = HEADER + '(subLayers = [@part.usda@])\n'
        a = self.snapshot({'scene.usda': root, 'part.usda': pose_scene()})
        b = self.snapshot({'scene.usda': root, 'part.usda': pose_scene((2, 0, 0))})
        ma, mb = (json.loads(p.read_text()) for p in (a, b))
        self.assertEqual(ma['files']['scene.usda'], mb['files']['scene.usda'])
        self.assertNotEqual(ma['files']['part.usda'], mb['files']['part.usda'])
        report = compare(a, b)
        self.assertEqual(report['status'], 'changed', report)
        self.assertIn('world', self.change(report, '/World')['fields'])

    def test_missing_dependency_never_passes(self):
        a = self.snapshot({'scene.usda': HEADER + '(subLayers = [@missing.usda@])\n'})
        report = compare(a, a)
        self.assertEqual(report['status'], 'unknown')
        self.assertTrue(report['reasons'])

    def test_changed_bundle_is_unknown(self):
        a, b = self.pair(pose_scene(), pose_scene())
        (b.parent / 'layers/scene.usda').write_text(pose_scene((5, 0, 0)))
        self.assertEqual(compare(a, b)['status'], 'unknown')

    def test_omitted_dependency_manifest_is_unknown(self):
        a = self.snapshot({'scene.usda': HEADER + '(subLayers = [@part.usda@])\n', 'part.usda': pose_scene()})
        self.rewrite_manifest(a, lambda m: m['files'].pop('part.usda'))
        self.assertEqual(compare(a, a)['status'], 'unknown')

    def test_deleted_bundle_dependency_is_unknown(self):
        a = self.snapshot({'scene.usda': HEADER + '(subLayers = [@part.usda@])\n', 'part.usda': pose_scene()})
        (a.parent / 'layers/part.usda').unlink()
        self.assertEqual(compare(a, a)['status'], 'unknown')

    def test_unsafe_manifest_entry_is_unknown(self):
        a = self.snapshot({'scene.usda': pose_scene()})
        self.rewrite_manifest(a, lambda m: m.update(entry='../outside.usda'))
        self.assertEqual(compare(a, a)['status'], 'unknown')

    def test_reference_escape_is_not_copied(self):
        outside = self.base / 'outside.usda'
        outside.write_text(pose_scene())
        a = self.snapshot({'scene.usda': HEADER + '(subLayers = [@../outside.usda@])\n'})
        self.assertEqual(compare(a, a)['status'], 'unknown')
        self.assertFalse((a.parent / 'outside.usda').exists())

    def test_absolute_reference_is_unknown(self):
        outside = self.base / 'outside.usda'
        outside.write_text(pose_scene())
        a = self.snapshot({'scene.usda': HEADER + '(subLayers = [@' + outside.as_posix() + '@])\n'})
        self.assertEqual(compare(a, a)['status'], 'unknown')

    def test_reference_layer_change_is_observed(self):
        root = HEADER + 'def Xform "World" (prepend references = @part.usda@</World>) {}\n'
        a = self.snapshot({'scene.usda': root, 'part.usda': pose_scene()})
        b = self.snapshot({'scene.usda': root, 'part.usda': pose_scene((3, 0, 0))})
        report = compare(a, b)
        self.assertEqual(report['status'], 'changed', report)
        self.assertIn('world', self.change(report, '/World')['fields'])

    def test_payload_dependency_is_pinned_and_loaded(self):
        root = HEADER + 'def Xform "World" (prepend payload = @part.usda@</World>) {}\n'
        a = self.snapshot({'scene.usda': root, 'part.usda': pose_scene()})
        b = self.snapshot({'scene.usda': root, 'part.usda': pose_scene((3, 0, 0))})
        self.assertIn('part.usda', json.loads(a.read_text())['files'])
        report = compare(a, b)
        self.assertEqual(report['status'], 'changed', report)
        self.assertEqual(self.change(report, '/World/Part')['provenance'], 'parent-propagated')

    def test_invalid_reference_target_is_unknown(self):
        root = HEADER + 'def Xform "World" (prepend references = @part.usda@</Missing>) {}\n'
        a = self.snapshot({'scene.usda': root, 'part.usda': pose_scene()})
        self.assertEqual(compare(a, a)['status'], 'unknown')

    def test_symlink_dependency_is_unknown(self):
        source = self.source({'scene.usda': HEADER + '(subLayers = [@part.usda@])\n', 'real.usda': pose_scene()})
        symlink_or_skip(self, source.parent / 'part.usda', 'real.usda')
        a = create_snapshot(source, self.base / 'symlink-bundle')
        self.assertEqual(compare(a, a)['status'], 'unknown')

    def test_stage_units_mismatch_is_unknown(self):
        a = HEADER + '(metersPerUnit = 1)\ndef Xform "World" {}\n'
        b = HEADER + '(metersPerUnit = 0.01)\ndef Xform "World" {}\n'
        pa, pb = self.pair(a, b)
        self.assertEqual(compare(pa, pb)['status'], 'unknown')

    def test_stale_cached_layer_is_unknown_and_not_reloaded(self):
        source = self.source({'scene.usda': pose_scene()})
        cached = Sdf.Layer.FindOrOpen(str(source))
        cached_text = cached.ExportToString()
        source.write_text(pose_scene((4, 0, 0)))
        manifest = create_snapshot(source, self.base / 'stale-source')
        report = compare(manifest, manifest)
        self.assertEqual(report['status'], 'unknown')
        self.assertTrue(any('cached layer differs from disk' in x for x in report['reasons']))
        self.assertEqual(cached.ExportToString(), cached_text)
        self.assertFalse(cached.dirty)

    def test_both_inactive_subtrees_do_not_prove_equal(self):
        text = HEADER + 'def Xform "World" (active = false) {\n def Xform "Part" {}\n}\n'
        a, b = self.pair(text, text)
        report = compare(a, b)
        self.assertEqual(report['status'], 'unknown', report)
        self.assertTrue(any('inactive' in reason for reason in report['reasons']))

    def test_local_and_parent_movement_are_both_identified(self):
        a, b = self.pair(pose_scene(), pose_scene((2, 0, 0), child_translation=(0, 3, 0)))
        report = compare(a, b)
        child = self.change(report, '/World/Part')
        self.assertEqual(child['provenance'], 'local-and-parent')
        self.assertEqual(child['parent_cause'], '/World')
        self.assertIn('local', child['fields'])
        self.assertIn('world', child['fields'])

    def test_unsupported_asset_property_is_unknown(self):
        stage = Usd.Stage.CreateInMemory()
        prim = stage.DefinePrim('/World', 'Xform')
        prim.CreateAttribute('texture', Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath('not-shipped.png'))
        a = self.snapshot({'scene.usda': stage.GetRootLayer().ExportToString()})
        report = compare(a, a)
        self.assertEqual(report['status'], 'unknown')
        self.assertTrue(any('asset-valued property unsupported' in x for x in report['reasons']))

    def test_unsupported_instancing_is_unknown(self):
        stage = Usd.Stage.CreateInMemory()
        stage.DefinePrim('/World', 'Xform').SetInstanceable(True)
        a = self.snapshot({'scene.usda': stage.GetRootLayer().ExportToString()})
        report = compare(a, a)
        self.assertEqual(report['status'], 'unknown')
        self.assertTrue(any('instancing unsupported' in x for x in report['reasons']))

    def test_unsupported_value_clips_are_unknown(self):
        stage = Usd.Stage.CreateInMemory()
        stage.DefinePrim('/World', 'Xform').SetMetadata('clips', {'default': {'assetPaths': [Sdf.AssetPath('clip.usda')]}})
        a = self.snapshot({'scene.usda': stage.GetRootLayer().ExportToString(), 'clip.usda': pose_scene()})
        report = compare(a, a)
        self.assertEqual(report['status'], 'unknown')
        self.assertTrue(any('value clips unsupported' in x for x in report['reasons']))

    def test_corrupt_layer_is_unknown(self):
        a = self.snapshot({'scene.usda': '#usda 1.0\ndef Xform "World" { broken!\n'})
        report = compare(a, a)
        self.assertEqual(report['status'], 'unknown')
        self.assertTrue(any('unreadable USD layer' in x for x in report['reasons']))

    def test_malformed_manifest_is_unknown(self):
        a = self.snapshot({'scene.usda': pose_scene()})
        a.write_text('{not valid JSON')
        self.assertEqual(compare(a, a)['status'], 'unknown')

    def test_input_mutation_during_observation_invalidates_result(self):
        a, b = self.pair(pose_scene(), pose_scene((2, 0, 0)))
        module = importlib.import_module('usd_scene_review.compare')
        observe = module._observe
        first = True
        def changing_input(snapshot):
            nonlocal first
            result = observe(snapshot)
            if first:
                first = False
                (b.parent / 'layers/scene.usda').write_text(pose_scene((99, 0, 0)))
            return result
        with mock.patch.object(module, '_observe', side_effect=changing_input):
            report = compare(a, b, policy={'max_translation': 3})
        self.assertEqual(report['status'], 'unknown')
        self.assertTrue(any('hash mismatch' in x for x in report['reasons']))
        self.assertTrue(all(p['status'] == 'unknown' for p in report['policy']))

    def test_manifest_mutation_during_observation_is_unknown(self):
        a, b = self.pair(pose_scene(), pose_scene((2, 0, 0)))
        module = importlib.import_module('usd_scene_review.compare')
        observe = module._observe
        first = True
        def changing_manifest(snapshot):
            nonlocal first
            record = observe(snapshot)
            if first:
                first = False
                self.rewrite_manifest(b, lambda manifest: manifest['config'].update(time=9))
            return record
        with mock.patch.object(module, '_observe', side_effect=changing_manifest):
            report = compare(a, b)
        self.assertEqual(report['status'], 'unknown', report)
        self.assertTrue(any('snapshot manifest changed' in reason for reason in report['reasons']))

    def test_default_prim_metadata_only_change_is_reported(self):
        stage = Usd.Stage.CreateInMemory()
        stage.DefinePrim('/World', 'Xform')
        stage.DefinePrim('/Other', 'Xform')
        stage.SetDefaultPrim(stage.GetPrimAtPath('/World'))
        before = stage.GetRootLayer().ExportToString()
        stage.SetDefaultPrim(stage.GetPrimAtPath('/Other'))
        after = stage.GetRootLayer().ExportToString()
        a, b = self.pair(before, after)
        report = compare(a, b)
        self.assertEqual(report['status'], 'changed', report)
        self.assertEqual(report['changes'], [])
        layer = next(change for change in report['layer_changes'] if change['layer'] == 'scene.usda')
        self.assertEqual(layer['before']['defaultPrim'], 'World')
        self.assertEqual(layer['after']['defaultPrim'], 'Other')

    def test_large_integer_attribute_delta_is_effective(self):
        def text(integer):
            stage = Usd.Stage.CreateInMemory()
            stage.DefinePrim('/World', 'Xform').CreateAttribute('count', Sdf.ValueTypeNames.Int).Set(integer)
            return stage.GetRootLayer().ExportToString()
        a, b = self.pair(text(100000000), text(100000001))
        report = compare(a, b)
        self.assertEqual(report['status'], 'changed', report)
        attributes = self.change(report, '/World')['fields']['attributes']
        self.assertEqual(attributes['before']['count'], 100000000)
        self.assertEqual(attributes['after']['count'], 100000001)

    def test_earlier_source_mutation_during_last_copy_is_unknown(self):
        source = self.source({'scene.usda': HEADER + '(subLayers = [@part.usda@])\n', 'part.usda': pose_scene()})
        module = importlib.import_module('usd_scene_review.snapshot')
        copyfile = module.shutil.copyfile
        copied = []
        def copying_then_mutating(src, dst):
            result = copyfile(src, dst)
            copied.append(Path(src).name)
            if Path(src).name == 'scene.usda':
                (source.parent / 'part.usda').write_text(pose_scene((7, 0, 0)))
            return result
        with mock.patch.object(module.shutil, 'copyfile', side_effect=copying_then_mutating):
            manifest_path = create_snapshot(source, self.base / 'changed-during-copy')
        self.assertEqual(copied, ['part.usda', 'scene.usda'])
        manifest = json.loads(manifest_path.read_text())
        self.assertEqual(manifest['status'], 'unknown', manifest)
        self.assertTrue(any('input changed while snapshotting: part.usda' in reason for reason in manifest['reasons']))

    def test_time_mismatch_is_unknown(self):
        a = self.snapshot({'scene.usda': pose_scene()}, time=1)
        b = self.snapshot({'scene.usda': pose_scene()}, time=2)
        self.assertEqual(compare(a, b)['status'], 'unknown')

    def test_unsupported_load_is_rejected_and_tamper_is_unknown(self):
        source = self.source({'scene.usda': pose_scene()})
        with self.assertRaises(ValueError):
            create_snapshot(source, self.base / 'load-none', load='none')
        a = create_snapshot(source, self.base / 'load-all')
        self.rewrite_manifest(a, lambda m: m['config'].update(load='none'))
        self.assertEqual(compare(a, a)['status'], 'unknown')

    def test_variant_mismatch_is_unknown(self):
        text = HEADER + '''def Xform "World" (
    prepend variantSets = "layout"
    variants = { string layout = "A" }
) {
    variantSet "layout" = {
        "A" {
            custom int choice = 1
        }
        "B" {
            custom int choice = 2
        }
    }
}
'''
        a = self.snapshot({'scene.usda': text}, variants={'/World:layout': 'A'})
        b = self.snapshot({'scene.usda': text}, variants={'/World:layout': 'B'})
        self.assertFalse(load_snapshot(a).errors)
        self.assertEqual(compare(a, b)['status'], 'unknown')

    def test_masked_weak_opinion_is_authored_only(self):
        strong = HEADER + '''(subLayers = [@weak.usda@])
over "World" {
    custom float value = 42
}
'''
        weak = lambda n: HEADER + 'def Xform "World" {\n custom float value = ' + str(n) + '\n}\n'
        a = self.snapshot({'scene.usda': strong, 'weak.usda': weak(1)})
        b = self.snapshot({'scene.usda': strong, 'weak.usda': weak(2)})
        report = compare(a, b)
        self.assertEqual(report['status'], 'changed', report)
        change = self.change(report, '/World')
        self.assertEqual(change['fields'], {})
        self.assertEqual(change['provenance'], 'authored-only')
        self.assertIn('value', change['authored'])

    def test_parent_movement_groups_child_effect(self):
        a, b = self.pair(pose_scene(), pose_scene((2, 0, 0)))
        report = compare(a, b)
        child = self.change(report, '/World/Part')
        self.assertNotIn('local', child['fields'])
        self.assertEqual(child['provenance'], 'parent-propagated')
        self.assertEqual(report['parent_groups'], [{'parent': '/World', 'affected': ['/World/Part']}])

    def test_reset_stack_stops_parent_propagation(self):
        a, b = self.pair(pose_scene(reset=True), pose_scene((2, 0, 0), reset=True))
        report = compare(a, b)
        self.assertEqual(report['status'], 'changed', report)
        self.assertFalse(any(c['path'] == '/World/Part' for c in report['changes']))
        self.assertEqual(report['parent_groups'], [])

    def test_inactive_descendant_is_unobserved_not_deleted(self):
        before = HEADER + 'def Xform "World" {\n def Xform "Part" {}\n}\n'
        after = HEADER + 'def Xform "World" (active = false) {\n def Xform "Part" {}\n}\n'
        a, b = self.pair(before, after)
        report = compare(a, b)
        self.assertEqual(report['status'], 'unknown', report)
        self.assertEqual(self.change(report, '/World/Part')['kind'], 'unobserved')
        self.assertIn('active', self.change(report, '/World')['fields'])

    def test_actual_deletion_is_removed(self):
        a, b = self.pair(pose_scene(), pose_scene(child=False))
        report = compare(a, b)
        self.assertEqual(report['status'], 'changed', report)
        self.assertEqual(self.change(report, '/World/Part')['kind'], 'removed')

    def test_inherited_visibility_is_observed(self):
        a = HEADER + 'def Xform "World" {\n token visibility = "inherited"\n def Xform "Part" {}\n}\n'
        b = HEADER + 'def Xform "World" {\n token visibility = "invisible"\n def Xform "Part" {}\n}\n'
        pa, pb = self.pair(a, b)
        report = compare(pa, pb)
        self.assertEqual(self.change(report, '/World/Part')['fields']['visibility']['after'], 'invisible')

    def test_equivalent_euler_pose_has_no_effective_motion(self):
        a, b = self.pair(pose_scene(rotation=0), pose_scene(rotation=360))
        report = compare(a, b)
        self.assertEqual(report['status'], 'changed', report)
        for change in report['changes']:
            self.assertNotIn('local', change['fields'])
            self.assertNotIn('world', change['fields'])
        self.assertEqual(self.change(report, '/World')['provenance'], 'authored-only')

    def test_equivalent_quaternion_sign_has_no_effective_motion(self):
        def text(sign):
            stage = Usd.Stage.CreateInMemory()
            x = UsdGeom.Xform.Define(stage, '/World')
            x.AddOrientOp().Set(Gf.Quatf(sign, Gf.Vec3f(0, 0, 0)))
            return stage.GetRootLayer().ExportToString()
        a, b = self.pair(text(1), text(-1))
        report = compare(a, b)
        self.assertEqual(report['status'], 'changed', report)
        self.assertNotIn('world', self.change(report, '/World')['fields'])
        self.assertNotIn('local', self.change(report, '/World')['fields'])

    def test_policy_uses_shortest_relative_rotation(self):
        a, b = self.pair(pose_scene(rotation=350), pose_scene(rotation=10))
        report = compare(a, b, policy={'max_rotation_degrees': 21})
        root = self.change(report, '/World')
        self.assertAlmostEqual(root['world_delta']['rotation_degrees'], 20, places=5)
        self.assertTrue(all(p['status'] == 'pass' for p in report['policy']))
        self.assertTrue(all(p['status'] == 'fail' for p in compare(a, b, policy={'max_rotation_degrees': 19})['policy']))

    def test_nonrigid_policy_is_unknown(self):
        for scale in ((2, 1, 1), (-1, 1, 1), (0, 1, 1)):
            with self.subTest(scale=scale):
                a, b = self.pair(pose_scene(scale=scale), pose_scene((2, 0, 0), scale=scale))
                report = compare(a, b, policy={'max_translation': 0.1})
                self.assertEqual(self.change(report, '/World')['world_delta']['status'], 'unknown')
                self.assertTrue(all(p['status'] == 'unknown' for p in report['policy']))

    def test_source_bytes_and_layer_dirty_flags_are_preserved(self):
        source_a = self.source({'scene.usda': pose_scene()})
        source_b = self.source({'scene.usda': pose_scene((2, 0, 0))})
        sources = [source_a, source_b]
        source_layers = [Sdf.Layer.FindOrOpen(str(p)) for p in sources]
        before = [(p.read_bytes(), layer.dirty) for p, layer in zip(sources, source_layers)]
        a = create_snapshot(source_a, self.base / 'a')
        b = create_snapshot(source_b, self.base / 'b')
        sa, sb = load_snapshot(a), load_snapshot(b)
        layer_states = [(l, l.dirty) for snap in (sa, sb) for l in snap.stage.GetUsedLayers()]
        bundle_bytes = {p: p.read_bytes() for snap in (a, b) for p in snap.parent.rglob('*') if p.is_file()}
        report = compare(a, b)
        self.assertEqual(report['status'], 'changed', report)
        self.assertEqual(before, [(p.read_bytes(), layer.dirty) for p, layer in zip(sources, source_layers)])
        self.assertTrue(all(l.dirty == state for l, state in layer_states))
        self.assertEqual(bundle_bytes, {p: p.read_bytes() for p in bundle_bytes})

    def test_dirty_source_is_not_silently_snapshotted(self):
        source = self.source({'scene.usda': pose_scene()})
        stage = Usd.Stage.Open(str(source))
        stage.GetPrimAtPath('/World').CreateAttribute('unsaved', Sdf.ValueTypeNames.Int).Set(1)
        self.assertTrue(stage.GetRootLayer().dirty)
        manifest = create_snapshot(source, self.base / 'dirty')
        self.assertEqual(compare(manifest, manifest)['status'], 'unknown')
        self.assertTrue(stage.GetRootLayer().dirty)

    def test_cli_json_html_exit_codes_and_no_overwrite(self):
        a, b = self.pair(pose_scene(), pose_scene((2, 0, 0)))
        output, page = self.base / 'report.json', self.base / 'report.html'
        self.assertEqual(main(['compare', str(a), str(b), '--json', str(output), '--html', str(page)]), 0)
        self.assertEqual(json.loads(output.read_text())['status'], 'changed')
        self.assertIn('<!doctype html>', page.read_text())
        original = output.read_bytes()
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            main(['compare', str(a), str(b), '--json', str(output)])
        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(output.read_bytes(), original)
        self.assertEqual(main(['compare', str(a), str(b), '--json', str(self.base/'failed.json'), '--max-translation', '1']), 3)
        (b.parent / 'layers/scene.usda').unlink()
        self.assertEqual(main(['compare', str(a), str(b), '--json', str(self.base/'unknown.json')]), 2)

    def test_html_escapes_untrusted_scene_strings(self):
        payload = '<script>alert("scene")</script>&'
        page = render_html({'status': 'changed', 'payload': payload})
        self.assertNotIn(payload, page)
        self.assertIn('&lt;script&gt;', page)
        self.assertIn('&amp;', page)

    def test_snapshot_cli_records_explicit_config(self):
        source = self.source({'scene.usda': pose_scene()})
        destination = self.base / 'cli-snapshot'
        with redirect_stdout(io.StringIO()):
            code = main(['snapshot', str(source), str(destination), '--time', '4'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads((destination/'manifest.json').read_text())['config']['time'], 4)


if __name__ == '__main__':
    unittest.main()
