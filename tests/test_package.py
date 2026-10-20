"""The installable archive contains only authored source and configuration."""
import importlib.util
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
                self.assertFalse(any(n.endswith(('.so', '.dll', '.pyc')) for n in archive.namelist()))
            with self.assertRaises(ValueError):
                module.package(a)
