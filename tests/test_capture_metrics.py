import importlib.util
from pathlib import Path
import tempfile
import unittest
from PIL import Image

spec = importlib.util.spec_from_file_location('capture_metrics', Path(__file__).resolve().parents[1] / 'tools/capture_metrics.py')
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)


class CaptureMetricTests(unittest.TestCase):
    def test_real_png_metric_keeps_missed_target_non_gating(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp) / name for name in ('wire.png', 'faint.png', 'opaque.png')]
            for path, value in zip(paths, (0, 50, 100)):
                Image.new('RGB', (8, 8), (value, value, value)).save(path)
            result = metrics.surface_deviation(*paths)
            self.assertEqual(result['ratio'], .5)
            self.assertFalse(result['quarter_target_passed'])
            self.assertFalse(result['acceptance_gate'])

    def test_equal_controls_do_not_invent_ratio(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'same.png'
            Image.new('RGB', (8, 8), (10, 20, 30)).save(path)
            self.assertEqual(metrics.mean_rgb_difference(path, path), 0)
            result = metrics.surface_deviation(path, path, path)
            self.assertIsNone(result['ratio'])
            self.assertFalse(result['quarter_target_passed'])

    def test_mismatched_capture_sizes_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            first, second = Path(tmp) / 'first.png', Path(tmp) / 'second.png'
            Image.new('RGB', (8, 8)).save(first)
            Image.new('RGB', (4, 8)).save(second)
            with self.assertRaisesRegex(ValueError, 'sizes differ'):
                metrics.mean_rgb_difference(first, second)
