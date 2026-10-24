"""The installable archive contains only authored source and configuration."""
import importlib.util
import json
from pathlib import Path
import tempfile
try:
    import tomllib
except ModuleNotFoundError:
    import toml as tomllib  # Already bundled in Isaac Sim 4.5's pip archive.
import unittest
import zipfile


class PackageTests(unittest.TestCase):
    def test_self_contained_deterministic_archive(self):
        repo = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location('package_extension', repo / 'tools/package_extension.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            a, b = Path(temp)/'a.zip', Path(temp)/'b.zip'
            module.package(a); module.package(b)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            with zipfile.ZipFile(a) as archive:
                config = tomllib.loads(archive.read('config/extension.toml').decode())
                self.assertEqual(config['python']['module'][0]['path'], 'python')
                self.assertIn('python/usd_scene_review/compare.py', archive.namelist())
                self.assertIn('mmporong/scene/review/extension.py', archive.namelist())
                self.assertIn('worker/scene_review_worker.py', archive.namelist())
                self.assertIn('python/usd_scene_review/worker_client.py', archive.namelist())
                self.assertIn('mmporong/scene/review/in_app.py',archive.namelist())
                self.assertIn('python/usd_scene_review/in_app_logic.py',archive.namelist())
                self.assertIn('docs/in-app-review.md',archive.namelist())
                self.assertIn('docs/teardown-investigation.md',archive.namelist())
                self.assertIn('docs/viewport-reuse-assessment.md',archive.namelist())
                self.assertIn('docs/scene-ui-faces.md',archive.namelist())
                faces=json.loads(archive.read('diagnostics/scene-ui-faces-v1.json'))
                self.assertFalse(faces['limits']['general_mesh_ghost_complete'])
                self.assertEqual(faces['after']['shutdown']['process_exit'],0)
                self.assertIn('examples/usd-scene-review-in-app.png',archive.namelist())
                self.assertIn(b'(in-app-review.md)',archive.read('docs/README.md'))
                observation=json.loads(archive.read('diagnostics/bounds-persistent-exclusions-v1.json').decode('utf-8-sig'))
                self.assertEqual(observation['process_exit'],0)
                self.assertFalse(observation['strict_clean_shutdown'])
                self.assertFalse(observation['stock_full_app_shutdown_qualified'])
                scale=json.loads(archive.read('diagnostics/bounds-scale-qa-v1.json'))
                self.assertFalse(scale['limits']['real_mouse_tested'])
                stability=json.loads(archive.read('diagnostics/bounds-stability-30-v1.json'))
                self.assertEqual(stability['method']['measured_cycles'],30)
                self.assertFalse(stability['shutdown']['strict_clean_shutdown'])
                self.assertIn('docs/bounds-deployment-qa.md',archive.namelist())
                self.assertIn('docs/cpu-bottleneck-analysis.md',archive.namelist())
                cpu=json.loads(archive.read('diagnostics/cpu-bottleneck-v1.json'))
                self.assertEqual([case['count'] for case in cpu['cases']],[32,2048])
                self.assertTrue(all(case['identical_json_and_html'] for case in cpu['cases']))
                self.assertFalse(cpu['limits']['native_ui_remeasured'])
                self.assertFalse(any(n.endswith(('.so', '.dll', '.pyc')) for n in archive.namelist()))
            with self.assertRaises(ValueError):
                module.package(a)
