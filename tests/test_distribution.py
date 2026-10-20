import asyncio
import sys
import types
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from usd_scene_review import create_snapshot, compare
from usd_scene_review.exports import save_report

ROOT=Path(__file__).resolve().parents[1]


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value


builder=module('candidate_builder',ROOT/'tools/package_candidate.py')
launcher=module('candidate_launcher',ROOT/'distribution/review_kit.py')


class DistributionTests(unittest.TestCase):
    def test_deterministic_archive_extract_verify_and_tamper(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);first=root/'first.zip';second=root/'second.zip'
            one=builder.build(first);two=builder.build(second)
            self.assertEqual(first.read_bytes(),second.read_bytes())
            self.assertEqual(one['sha256'],two['sha256'])
            payload=builder.payload()
            crlf={name:data.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n') for name,data in payload.items()}
            with patch.object(builder,'payload',return_value=crlf):
                builder.build(root/'crlf.zip')
            self.assertEqual(first.read_bytes(),(root/'crlf.zip').read_bytes())
            self.assertEqual(builder.VERSION,launcher.VERSION)
            extracted=root/'clean extracted path';extracted.mkdir()
            with zipfile.ZipFile(first) as archive:
                self.assertTrue(all(not name.endswith(('.dll','.exe','.mdl','.log')) for name in archive.namelist()))
                archive.extractall(extracted)
            manifest=launcher.verify(extracted)
            self.assertEqual(manifest['version'],builder.VERSION)
            (extracted/'README.md').write_text('changed',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'PACKAGE_HASH'):launcher.verify(extracted)

    def test_manifest_path_escape_and_extra_files_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);archive=root/'candidate.zip';builder.build(archive)
            extracted=root/'fresh';extracted.mkdir()
            with zipfile.ZipFile(archive) as z:z.extractall(extracted)
            (extracted/'unexpected.txt').write_text('unexpected')
            with self.assertRaisesRegex(ValueError,'PACKAGE_FILES'):launcher.verify(extracted)
            (extracted/'unexpected.txt').unlink()
            manifest=json.loads((extracted/'candidate.json').read_text())
            manifest['files']['../escape.py']='0'*64
            (extracted/'candidate.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'PACKAGE_PATH'):launcher.verify(extracted)

    def test_packager_refuses_private_paths_vendor_assets_and_overwrite(self):
        for files in ({'notes.txt':b'C:\\Users\\private\\file'},
                      {'engine.dll':b'not allowed'}, {'examples/private.usda':b'#usda 1.0'}):
            with self.assertRaises(ValueError):builder.inspect(files)
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)/'existing.zip';target.write_bytes(b'keep')
            with self.assertRaises(ValueError):builder.build(target)
            self.assertEqual(target.read_bytes(),b'keep')

    def test_public_sample_signed_delta_export_and_source_preservation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);manifests=[];source=ROOT/'distribution/examples/synthetic'
            hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob('*.usda')}
            for name in ('before','after'):
                manifests.append(create_snapshot(source/(name+'.usda'),root/name))
            report=compare(*manifests)
            self.assertEqual(report['status'],'changed')
            from usd_scene_review.evidence import evidence_rows
            change=next(c for c in report['changes'] if c['path']=='/World/Rack')
            self.assertEqual(dict(evidence_rows(report,change))['World delta [m]'],'(0, -0.2, 0)')
            output=save_report(report,root/'evidence',forbidden_roots=[p.parent for p in manifests])
            self.assertEqual(json.loads((output/'review.json').read_text()),report)
            self.assertIn('unknown',(output/'review.html').read_text())
            with self.assertRaises(FileExistsError):save_report(report,output)
            with self.assertRaises(ValueError):save_report(report,manifests[0].parent/'forbidden',forbidden_roots=[manifests[0].parent])
            self.assertEqual(hashes,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob('*.usda')})

    def test_package_workspace_refused_and_missing_sdk_has_guidance(self):
        with patch.object(launcher,'ROOT',ROOT/'distribution'):
            with self.assertRaisesRegex(ValueError,'WORKSPACE_LOCATION'):
                launcher.outside_package(ROOT/'distribution/output')
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError,'SDK_REQUIRED|WINDOWS_REQUIRED'):
                launcher.environment(temp)


class BootstrapLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_early_host_close_cancels_pending_work_and_cannot_report_pass(self):
        omni=types.ModuleType('omni');omni.ext=types.ModuleType('omni.ext')
        omni.ext.IExt=object;omni.kit=types.ModuleType('omni.kit')
        omni.kit.app=types.ModuleType('omni.kit.app')
        carb=types.ModuleType('carb');carb.settings=types.ModuleType('carb.settings')
        modules={'omni':omni,'omni.ext':omni.ext,'omni.kit':omni.kit,
                 'omni.kit.app':omni.kit.app,'carb':carb,'carb.settings':carb.settings}
        with patch.dict(sys.modules,modules):
            bootstrap=module('distribution_lifecycle',ROOT/'distribution/exts/usd.review.distribution/distribution_bootstrap.py')
        with tempfile.TemporaryDirectory() as temp:
            owner=bootstrap.DistributionBootstrap();owner.root=Path(temp)
            owner.client=None;owner.result={'status':'starting','checks':[]}
            async def delayed_success():
                await asyncio.sleep(10)
                owner.result['status']='passed'
            owner.task=asyncio.create_task(delayed_success())
            await asyncio.sleep(0)
            owner.on_shutdown()
            await asyncio.gather(owner.task,return_exceptions=True)
            self.assertTrue(owner.task.cancelled())
            self.assertEqual(owner.result['status'],'failed')
            self.assertEqual(json.loads((owner.root/'session-result.json').read_text())['status'],'failed')
