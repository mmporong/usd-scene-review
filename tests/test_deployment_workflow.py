"""Fresh extracted package workflow; no Kit, network or GPU required."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock
from unittest.mock import patch
import zipfile
from usd_scene_review.inputs import manifest_inputs

ROOT=Path(__file__).resolve().parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value


class DeploymentWorkflowTests(unittest.TestCase):
    def test_input_roles_quotes_unicode_and_no_original_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'공백 있는 경로';root.mkdir()
            for side in ('A','B'):
                folder=root/side;folder.mkdir();(folder/'manifest.json').write_text('{}')
            paths=manifest_inputs({'A':' "'+str(root/'A/manifest.json')+'" ',
                                  'B':"'"+str(root/'B/manifest.json')+"'"})
            self.assertEqual(paths['A'],root/'A/manifest.json')
            self.assertEqual((root/'A/manifest.json').read_text(),'{}')
            for bad,reason in [('', 'A baseline/before'),(str(root),'does not exist'),
                               (str(root/'missing'),'does not exist')]:
                with self.assertRaisesRegex(ValueError,reason):manifest_inputs({'A':bad})
            source=root/'source.usda';source.write_text('#usda 1.0')
            with self.assertRaisesRegex(ValueError,'not the source USD'):manifest_inputs({'A':str(source)})
            with self.assertRaisesRegex(ValueError,'B revision/after'):manifest_inputs({'A':str(paths['A'])})

    def test_candidate_readme_links_samples_and_verified_copy(self):
        builder=load('deployment_builder',ROOT/'tools/package_candidate.py')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);archive=root/'candidate.zip';builder.build(archive)
            receipt=builder.extract_for_validation(archive,root)
            package=root/'candidate'
            self.assertEqual(receipt['version'],'0.1.0-rc.4')
            self.assertTrue(receipt['copied_bytes_verified'])
            for relative in ('README.md','docs/first-use.md','review_kit.py',
                             'exts/mmporong.scene.review/config/extension.toml',
                             'examples/synthetic/before.usda','examples/synthetic/after.usda'):
                self.assertTrue((package/relative).is_file(),relative)
            for path in package.rglob('*.md'):
                for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
                    if ':' not in target and not target.startswith('#'):
                        self.assertTrue((path.parent/target.split('#')[0]).is_file(),(path.relative_to(package),target))
            tampered=root/'changed.zip'
            with zipfile.ZipFile(archive) as source,zipfile.ZipFile(tampered,'w') as out:
                for name in source.namelist():out.writestr(name,b'changed' if name=='README.md' else source.read(name))
            other=root/'tampered';other.mkdir()
            with self.assertRaisesRegex(ValueError,'PACKAGE_HASH'):builder.extract_for_validation(tampered,other)
            self.assertFalse((other/'exts').exists())

    def test_unicode_clean_extract_executes_packaged_sample_and_compare(self):
        builder=load('workflow_builder',ROOT/'tools/package_candidate.py')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'배포 후보 공백';root.mkdir()
            archive=root/'candidate.zip';builder.build(archive)
            package=root/'추출 패키지';package.mkdir()
            with zipfile.ZipFile(archive) as z:z.extractall(package)
            env=os.environ.copy();env['PYTHONPATH']=os.pathsep.join([
                str(package/'exts/mmporong.scene.review/python'),
                *[p for p in env.get('PYTHONPATH','').split(os.pathsep) if p and Path(p).resolve()!=ROOT/'src']])
            env['PYTHONDONTWRITEBYTECODE']='1';env['PYTHONUTF8']='1'
            # Keep the existing OpenUSD DLL/runtime environment, replace project source path.
            prior={p.relative_to(package).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in package.rglob('*') if p.is_file()}
            script="import runpy,sys,json,pathlib; m=runpy.run_path(sys.argv[1]); m['verify'](); m['sample'](sys.argv[2]); from usd_scene_review import compare; from usd_scene_review.exports import save_report; p=pathlib.Path(sys.argv[2]); r=compare(p/'snapshot-A/manifest.json',p/'snapshot-B/manifest.json'); save_report(r,sys.argv[3]); assert r['status']=='changed'; m['verify']()"
            result=subprocess.run([sys.executable,'-B','-c',script,str(package/'review_kit.py'),
                                   str(root/'샘플 결과'),str(root/'비교 결과')],env=env,cwd=package,
                                  capture_output=True,text=True,encoding='utf-8',timeout=60)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue((root/'비교 결과/review.html').is_file())
            self.assertEqual(prior,{p.relative_to(package).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in package.rglob('*') if p.is_file()})


class InputOwnershipTests(unittest.IsolatedAsyncioTestCase):
    async def test_reactivation_looks_up_new_module_instead_of_retaining_old_getter(self):
        helper=load('workflow_reactivation',ROOT/'tools/viewport_bounds_candidate.py')
        first=NS(get_active_extension=lambda:'first');second=NS(get_active_extension=lambda:'second')
        with patch.dict(sys.modules,{'mmporong.scene.review.extension':first}):
            self.assertEqual(helper.current_extension(),'first')
            sys.modules['mmporong.scene.review.extension']=second
            self.assertEqual(helper.current_extension(),'second')

    async def test_native_capture_stages_ascii_and_copies_unicode_without_hiding_failure(self):
        helper=load('workflow_capture',ROOT/'tools/viewport_bounds_candidate.py')
        policy=load('workflow_state_policy',ROOT/'tools/shutdown_profile.py')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);destination=root/'한글 캡처.png';captured=[]
            class Recorder:
                def capture_next_frame_swapchain(self,path):captured.append(Path(path))
                def wait_async_capture(self):pass
            async def updates(count):
                self.assertEqual(count,8);captured[-1].write_bytes(b'owned pixels')
            await helper.capture_evidence(Recorder(),destination,updates,temp_parent=root)
            self.assertTrue(str(captured[0]).isascii());self.assertFalse(captured[0].parent.exists())
            self.assertEqual(destination.read_bytes(),b'owned pixels')
            async def missing(count):pass
            with self.assertRaisesRegex(RuntimeError,'SDK_CAPTURE:'):
                await helper.capture_evidence(Recorder(),root/'missing.png',missing,temp_parent=root)
            self.assertFalse((root/'missing.png').exists())
            policy.validate_state_path(root/'ASCII host state')
            with self.assertRaisesRegex(ValueError,'SDK_STATE_PATH'):
                policy.validate_state_path(root/'한글 host')

    async def test_invalid_input_keeps_previous_report_and_owned_display(self):
        path=ROOT/'exts/mmporong.scene.review/mmporong/scene/review/extension.py'
        tree=ast.parse(path.read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef))
        node=ast.ClassDef(name='Owner',bases=[],keywords=[],decorator_list=[],body=[
            n for n in cls.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='_compare_async'])
        env={'manifest_inputs':manifest_inputs}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(path),'exec'),env)
        owner=env['Owner']();owner._paths={'A':NS(as_string=''),'B':NS(as_string='')}
        prior=object();owner._overlay_receipt=prior;owner._report=prior;owner._close_bounds_overlay=Mock()
        with self.assertRaisesRegex(ValueError,'A baseline'):await owner._compare_async()
        self.assertIs(owner._report,prior);self.assertIs(owner._overlay_receipt,prior)
        owner._close_bounds_overlay.assert_not_called()
