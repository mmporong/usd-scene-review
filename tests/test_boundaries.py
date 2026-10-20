"""Regression coverage for strict input and effective value boundaries."""
import json
import io
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch
import unittest
import test_review as helpers
from usd_scene_review import compare, load_snapshot
from usd_scene_review.cli import main


class BoundaryTests(unittest.TestCase):
    setUp = helpers.ReviewTests.setUp
    source = helpers.ReviewTests.source
    snapshot = helpers.ReviewTests.snapshot
    pair = helpers.ReviewTests.pair
    change = staticmethod(helpers.ReviewTests.change)

    def test_nonfinite_manifest_rejected(self):
        a, b = self.pair(helpers.pose_scene(), helpers.pose_scene())
        for path in (a, b):
            manifest = json.loads(path.read_text())
            manifest['config']['time'] = float('nan')
            path.write_text(json.dumps(manifest))
        self.assertTrue(load_snapshot(a).errors)
        report = compare(a, b)
        self.assertEqual(report['status'], 'unknown')
        json.dumps(report, allow_nan=False)

    def test_effective_attribute_type_change(self):
        a, b = self.pair('#usda 1.0\ndef Xform "World" {\n custom float n = 1\n}\n', '#usda 1.0\ndef Xform "World" {\n custom double n = 1\n}\n')
        change = self.change(compare(a, b), '/World')
        self.assertIn('attribute_types', change['fields'])
        self.assertNotEqual(change['provenance'], 'authored-only')

    def test_relationship_opinions_at_explicit_sample(self):
        a, b = self.pair(
            '#usda 1.0\ndef Xform "World" {\n custom rel target = </A>\n}\n',
            '#usda 1.0\ndef Xform "World" {\n custom rel target = </B>\n}\n', time=2.0)
        report = compare(a, b)
        self.assertEqual(report['status'], 'changed', report)
        change = self.change(report, '/World')
        self.assertEqual(change['fields']['attributes']['before']['target'], ['/A'])
        self.assertEqual(change['fields']['attributes']['after']['target'], ['/B'])
        self.assertIn('target', change['authored'])

    def test_large_coordinate_motion_not_relative_tolerance(self):
        a, b = self.pair(helpers.pose_scene((100000000, 0, 0)), helpers.pose_scene((100000000.5, 0, 0)))
        self.assertIn('world', self.change(compare(a, b), '/World')['fields'])

    def test_unknown_rigid_policy_cli_is_not_success(self):
        a, b = self.pair(helpers.pose_scene(scale=(2, 1, 1)), helpers.pose_scene((2, 0, 0), scale=(2, 1, 1)))
        result = main(['compare', str(a), str(b), '--json', str(self.base/'policy.json'), '--max-translation', '1'])
        self.assertEqual(result, 2)

    def test_cli_exclusive_output_rejects_creation_after_precheck(self):
        a, b = self.pair(helpers.pose_scene(), helpers.pose_scene((1, 0, 0)))
        original_open = Path.open
        for kind in ('file', 'symlink', 'html'):
            with self.subTest(kind=kind):
                output = self.base/('race-' + kind + '.json')
                html = self.base/'race.html'
                target = self.base/'sentinel.txt'
                target.write_text('keep')
                if kind == 'symlink':
                    probe = self.base/'symlink-privilege-probe'
                    helpers.symlink_or_skip(self, probe, target)
                    probe.unlink()
                raced = html if kind == 'html' else output
                triggered = []
                def race(path, mode='r', *args, **kwargs):
                    if path == raced and mode == 'x' and not triggered:
                        triggered.append(True)
                        if kind == 'symlink':
                            path.symlink_to(target)
                        else:
                            with original_open(path, 'w') as stream:
                                stream.write('keep')
                    return original_open(path, mode, *args, **kwargs)
                argv = ['compare', str(a), str(b), '--json', str(output)]
                if kind == 'html':
                    argv += ['--html', str(html)]
                with patch.object(Path, 'open', race), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
                    main(argv)
                self.assertEqual(raised.exception.code, 2)
                self.assertTrue(triggered)
                self.assertEqual(raced.read_text(), 'keep')
                self.assertEqual(target.read_text(), 'keep')
