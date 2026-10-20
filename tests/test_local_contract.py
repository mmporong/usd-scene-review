"""Adversarial resolution checks using real local USD layers and stages."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest
from pxr import Ar, Sdf
from usd_scene_review import compare, load_snapshot, create_snapshot
from usd_scene_review.snapshot import verify
from usd_scene_review.local_contract import local_identifier, require_same_file
import test_review as helpers


class LocalContractTests(unittest.TestCase):
    setUp = helpers.ReviewTests.setUp
    source = helpers.ReviewTests.source
    snapshot = helpers.ReviewTests.snapshot

    def resolver(self, resolve=None, identifier=None):
        actual = Ar.GetResolver()
        return SimpleNamespace(Resolve=resolve or actual.Resolve,
                               CreateIdentifier=identifier or actual.CreateIdentifier)

    def test_matching_local_behavior_needs_no_resolver_type_allowlist(self):
        # A proxy has no DefaultResolver/Resolver type identity; only its observed
        # mapping and actual composed layers may establish the local contract.
        proxy = self.resolver()
        with patch('usd_scene_review.local_contract.Ar.GetResolver', return_value=proxy):
            manifest = self.snapshot({'scene.usda': helpers.pose_scene()})
            self.assertEqual(compare(manifest, manifest)['status'], 'equal')

    def test_absolute_resolution_remap_is_unknown(self):
        outside = self.base / 'outside.usda'
        outside.write_text(helpers.pose_scene((99, 0, 0)))
        proxy = self.resolver(resolve=lambda _: Ar.ResolvedPath(str(outside)))
        with patch('usd_scene_review.local_contract.Ar.GetResolver', return_value=proxy):
            manifest = self.snapshot({'scene.usda': helpers.pose_scene()})
            report = compare(manifest, manifest)
            self.assertEqual(report['status'], 'unknown')
            self.assertTrue(any('remapped' in reason for reason in report['reasons']))

    def test_anchored_dependency_remap_is_unknown(self):
        actual = Ar.GetResolver()
        outside = self.base / 'outside.usda'
        outside.write_text(helpers.pose_scene())
        def identifier(asset, anchor):
            return str(outside) if asset == 'part.usda' else actual.CreateIdentifier(asset, anchor)
        with patch('usd_scene_review.local_contract.Ar.GetResolver', return_value=self.resolver(identifier=identifier)):
            manifest = self.snapshot({'scene.usda': '#usda 1.0\n(subLayers=[@part.usda@])\n', 'part.usda': helpers.pose_scene()})
            self.assertEqual(compare(manifest, manifest)['status'], 'unknown')

    def test_resolution_change_after_load_invalidates_verification(self):
        manifest = self.snapshot({'scene.usda': helpers.pose_scene()})
        snapshot = load_snapshot(manifest)
        self.assertFalse(verify(snapshot))
        outside = self.base / 'outside.usda'
        outside.write_text(helpers.pose_scene())
        with patch('usd_scene_review.local_contract.Ar.GetResolver', return_value=self.resolver(resolve=lambda _: Ar.ResolvedPath(str(outside)))):
            self.assertTrue(any('remapped' in reason for reason in verify(snapshot)))

    def test_actual_composed_layer_escape_is_rejected(self):
        manifest = self.snapshot({'scene.usda': helpers.pose_scene()})
        snapshot = load_snapshot(manifest)
        outside = self.base / 'outside.usda'
        outside.write_text(helpers.pose_scene())
        snapshot.stage.GetSessionLayer().subLayerPaths = [str(outside)]
        reasons = verify(snapshot)
        self.assertTrue(any('unverified composed layer' in reason for reason in reasons), reasons)
        self.assertFalse(snapshot.stage.GetRootLayer().dirty)

    def test_actual_anonymous_composed_layer_is_rejected(self):
        manifest = self.snapshot({'scene.usda': helpers.pose_scene()})
        snapshot = load_snapshot(manifest)
        foreign = Sdf.Layer.CreateAnonymous('foreign')
        snapshot.stage.GetSessionLayer().subLayerPaths = [foreign.identifier]
        self.assertTrue(any('unverified composed layer' in reason for reason in verify(snapshot)))

    def test_unlisted_composed_file_inside_bundle_is_rejected(self):
        manifest = self.snapshot({'scene.usda': helpers.pose_scene()})
        snapshot = load_snapshot(manifest)
        unlisted = manifest.parent / 'layers/unlisted.usda'
        unlisted.write_text(helpers.pose_scene())
        snapshot.stage.GetSessionLayer().subLayerPaths = [str(unlisted)]
        self.assertTrue(any('pinned dependency closure' in reason for reason in verify(snapshot)))

    def test_remote_resolution_is_unknown_without_exposing_its_url(self):
        proxy = self.resolver(resolve=lambda _: Ar.ResolvedPath('https://invalid.example/private.usda'))
        with patch('usd_scene_review.local_contract.Ar.GetResolver', return_value=proxy):
            manifest = self.snapshot({'scene.usda': helpers.pose_scene()})
            report = compare(manifest, manifest)
            self.assertEqual(report['status'], 'unknown')
            self.assertNotIn('invalid.example', str(report))

    def test_remote_package_relative_and_format_identifiers_are_rejected(self):
        for identifier in ('https://host/part.usda', 'omniverse://host/part.usda',
                           'file:///local/part.usda', '//host/share/part.usda',
                           'part.usda', '/tmp/part.usdz[part.usda]',
                           '/tmp/part.usda:SDF_FORMAT_ARGS:key=value', 'C:part.usda'):
            with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                local_identifier(identifier)

    def test_windows_case_and_forward_slashes_identify_same_native_file(self):
        import os
        if os.name != 'nt':
            self.skipTest('Windows identifier normalization')
        manifest = self.snapshot({'scene.usda': helpers.pose_scene()})
        path = manifest.parent / 'layers/scene.usda'
        require_same_file(path.as_posix().swapcase(), path)

    def test_unresolved_absolute_file_is_unknown(self):
        with patch('usd_scene_review.local_contract.Ar.GetResolver', return_value=self.resolver(resolve=lambda _: Ar.ResolvedPath())):
            manifest = self.snapshot({'scene.usda': helpers.pose_scene()})
            self.assertEqual(compare(manifest, manifest)['status'], 'unknown')

    def test_windows_junction_dependency_is_unknown(self):
        import os
        if os.name != 'nt':
            self.skipTest('Windows junction boundary')
        import _winapi
        source = self.source({'scene.usda': '#usda 1.0\n(subLayers=[@parts/part.usda@])\n',
                              'real/part.usda': helpers.pose_scene()})
        _winapi.CreateJunction(str(source.parent / 'real'), str(source.parent / 'parts'))
        manifest = create_snapshot(source, self.base / 'junction-snapshot')
        report = compare(manifest, manifest)
        self.assertEqual(report['status'], 'unknown')
        self.assertTrue(any('symlink' in reason or 'reparse' in reason for reason in report['reasons']), report)
