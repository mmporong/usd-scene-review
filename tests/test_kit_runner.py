"""A normal Kit exit is insufficient evidence of completed acceptance."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


class KitRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tools = Path(__file__).resolve().parents[1] / 'tools'
        spec = importlib.util.spec_from_file_location('kit_runner', tools / 'run_kit_validation.py')
        cls.runner = importlib.util.module_from_spec(spec)
        with patch.object(sys, 'path', [str(tools), *sys.path]):
            spec.loader.exec_module(cls.runner)

    def test_missing_result_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(self.runner.completion_status(Path(temp), 0), 2)

    def test_failed_result_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'results').mkdir()
            (root / 'results/result.json').write_text('{"status":"failed"}', encoding='utf-8')
            self.assertEqual(self.runner.completion_status(root, 0), 1)

    def test_pass_requires_successful_process(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'results').mkdir()
            (root / 'results/result.json').write_text('{"status":"passed"}', encoding='utf-8')
            self.assertEqual(self.runner.completion_status(root, 3), 3)
            self.assertEqual(self.runner.completion_status(root, 0), 0)
