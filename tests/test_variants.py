"""Variant selection order must respect composed dependency availability."""
from pathlib import Path
import unittest
import test_review as helpers
from usd_scene_review import compare, create_snapshot, load_snapshot


class VariantTests(unittest.TestCase):
    setUp = helpers.ReviewTests.setUp

    def bundle(self, name, variants):
        fixture = Path(__file__).resolve().parents[1]/'fixtures/variant-dependencies'/name
        self.serial += 1
        return create_snapshot(fixture, self.base/str(self.serial), variants=variants)

    def test_parent_choice_exposes_child_variant(self):
        manifest = self.bundle('nested.usda', {'/World/Part:color': 'blue', '/World:layout': 'B'})
        snapshot = load_snapshot(manifest)
        self.assertFalse(snapshot.errors, snapshot.errors)
        self.assertEqual(snapshot.stage.GetPrimAtPath('/World/Part').GetAttribute('tint').Get(), 'blue')
        self.assertEqual(compare(manifest, manifest)['status'], 'equal')

    def test_same_prim_dependency_retries_unavailable_set(self):
        manifest = self.bundle('same-prim.usda', {'/World:aColor': 'blue', '/World:zLayout': 'B'})
        snapshot = load_snapshot(manifest)
        self.assertFalse(snapshot.errors, snapshot.errors)
        self.assertEqual(snapshot.stage.GetPrimAtPath('/World').GetAttribute('tint').Get(), 'blue')

    def test_final_configuration_requires_every_requested_set(self):
        manifest = self.bundle('nested.usda', {'/World/Part:color': 'blue', '/World:layout': 'A'})
        self.assertTrue(load_snapshot(manifest).errors)
        self.assertEqual(compare(manifest, manifest)['status'], 'unknown')

    def test_later_choice_hiding_applied_set_is_unknown(self):
        fixture = Path(__file__).resolve().parents[1]/'fixtures/variant-dependencies/same-prim.usda'
        source = self.base/'same.usda'
        source.write_text(fixture.read_text().replace('string zLayout = "A"', 'string zLayout = "B"'))
        manifest = create_snapshot(source, self.base/'snapshot', variants={'/World:aColor': 'blue', '/World:zLayout': 'A'})
        snapshot = load_snapshot(manifest)
        self.assertTrue(any('unresolved or mutually exclusive' in reason for reason in snapshot.errors), snapshot.errors)
        self.assertEqual(compare(manifest, manifest)['status'], 'unknown')

    def test_variant_input_order_does_not_change_configuration(self):
        a = self.bundle('same-prim.usda', {'/World:aColor': 'blue', '/World:zLayout': 'B'})
        b = self.bundle('same-prim.usda', {'/World:zLayout': 'B', '/World:aColor': 'blue'})
        self.assertEqual(compare(a, b)['status'], 'equal')
