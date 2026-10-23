"""Windows candidate launcher. Uses an existing SDK; never installs or repairs it."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
VERSION = '0.1.0-rc.3'


def verify(root=ROOT):
    root = Path(root).resolve()
    manifest = json.loads((root/'candidate.json').read_text(encoding='utf-8'))
    if not isinstance(manifest, dict) or manifest.get('version') != VERSION or manifest.get('schema') != 1:
        raise ValueError('PACKAGE_VERSION: unsupported candidate manifest')
    expected = manifest['files']
    if not isinstance(expected,dict) or not expected or any(not isinstance(name,str)
            or not isinstance(digest,str) or len(digest)!=64 for name,digest in expected.items()):
        raise ValueError('PACKAGE_MANIFEST: invalid payload digest table')
    for name, digest in expected.items():
        rel = PurePosixPath(name)
        if rel.is_absolute() or '..' in rel.parts or '\\' in name or ':' in name:
            raise ValueError('PACKAGE_PATH: unsafe manifest path')
        path = root.joinpath(*rel.parts)
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('PACKAGE_PATH: linked payload refused')
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('PACKAGE_HASH: changed or incomplete file: '+name)
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if actual != set(expected) | {'candidate.json'}:
        raise ValueError('PACKAGE_FILES: unexpected or missing files; extract a fresh copy')
    return manifest


def environment(sdk, root=ROOT):
    sdk = Path(sdk).expanduser().resolve()
    if os.name != 'nt':
        raise ValueError('WINDOWS_REQUIRED: GUI candidate supports Windows with existing Isaac Sim 4.5 only')
    required = ['kit/kit.exe','kit/python/python.exe','VERSION','kit/mdl/core/Base/OmniPBR.mdl']
    if any(not (sdk/p).is_file() for p in required):
        raise ValueError('SDK_REQUIRED: select an existing Isaac Sim 4.5 SDK containing kit, Python and OmniPBR; nothing was installed')
    version = (sdk/'VERSION').read_text(encoding='utf-8').strip()
    if not version.startswith('4.5.'):
        raise ValueError('SDK_VERSION: candidate is qualified for 4.5; other SDK versions are unsupported, not upgraded automatically')
    bundles = sorted((sdk/'extscache').glob('omni.usd.libs-*'))
    if len(bundles)!=1 or not (bundles[0]/'pxr').is_dir():
        raise ValueError('USD_BUNDLE: expected one installed omni.usd.libs bundle; select the matching SDK')
    archives = sorted((sdk/'extscache').glob('omni.kit.pip_archive-*'))
    if len(archives)!=1:
        raise ValueError('PYTHON_BUNDLE: expected one installed pip archive; select the matching SDK')
    env = os.environ.copy()
    env['PYTHONPATH'] = os.pathsep.join([str(root/'exts/mmporong.scene.review/python'),
                                      str(bundles[0]),str(archives[0]/'pip_prebundle')])
    env['PXR_USD_WINDOWS_DLL_PATH'] = os.pathsep.join([str(bundles[0]/'bin'),str(sdk/'kit'),env.get('PATH','')])
    env['PYTHONDONTWRITEBYTECODE']='1'
    env['PYTHONUTF8']='1'
    return sdk, version, env


def doctor(sdk):
    sdk, version, env = environment(sdk)
    probe = subprocess.run([str(sdk/'kit/python/python.exe'),'-B','-c',
        'import json,sys;from pxr import Usd;import PIL;print(json.dumps(dict(python=list(sys.version_info[:3]),usd=list(Usd.GetVersion()),pillow=PIL.__version__)))'],
        env=env, cwd=sdk, capture_output=True, text=True, timeout=30)
    if probe.returncode:
        raise ValueError('PYTHON_IMPORT: SDK Python could not import OpenUSD/Pillow; inspect the selected installation without changing system Python')
    runtime = json.loads(probe.stdout.strip().splitlines()[-1])
    if runtime['python'][:2] != [3,10] or runtime['usd'] != [0,22,11]:
        raise ValueError('ABI_UNQUALIFIED: expected SDK Python 3.10 / OpenUSD 22.11; no mixed system packages are supported')
    smi = shutil.which('nvidia-smi')
    if not smi:
        raise ValueError('GPU_DIAGNOSTIC: nvidia-smi not found; verify NVIDIA GPU access manually; this tool never repairs drivers')
    gpu = subprocess.run([smi,'--query-gpu=name,driver_version,memory.total','--format=csv,noheader'],
                         capture_output=True,text=True,timeout=15)
    if gpu.returncode or not gpu.stdout.strip():
        raise ValueError('GPU_DIAGNOSTIC: NVIDIA read-only health query failed; do not assume rendering is qualified')
    return dict(candidate=VERSION, os=platform.platform(), sdk_version=version,
                runtime=runtime, gpu=gpu.stdout.strip().splitlines(),
                scope='minimal Kit only; full Isaac application shutdown remains unqualified',
                license='not selected; this is not an open-source license grant')


def outside_package(path):
    path = Path(path).expanduser().resolve()
    if path.is_relative_to(ROOT):
        raise ValueError('WORKSPACE_LOCATION: choose a new workspace outside the extracted package')
    return path


def sample(output):
    from usd_scene_review import create_snapshot, compare
    from usd_scene_review.exports import save_report
    output = outside_package(output)
    output.mkdir(exist_ok=False)
    source = output/'sources'
    source.mkdir()
    manifests = {}
    for side, filename in [('A','before.usda'),('B','after.usda')]:
        shutil.copyfile(ROOT/'examples/synthetic'/filename,source/filename)
        manifests[side] = create_snapshot(source/filename,output/('snapshot-'+side))
    report = compare(manifests['A'],manifests['B'])
    if report['status']!='changed':
        raise ValueError('SAMPLE_COMPARE: synthetic comparison did not complete')
    save_report(report,output/'reports',forbidden_roots=[p.parent for p in manifests.values()])
    (output/'sample.json').write_text(json.dumps({'schema':1,'A':'snapshot-A/manifest.json',
        'B':'snapshot-B/manifest.json','selected':'/World/Rack'},indent=2),encoding='utf-8')
    print('Sample ready; JSON/HTML saved in '+str(output/'reports'))


def materialize_runtime(state):
    manifest = verify(ROOT)
    runtime = state/'runtime'
    runtime.mkdir(exist_ok=False)
    # Copy the verified file allowlist only; never follow unlisted directory links.
    for name in sorted(set(manifest['files']) | {'candidate.json'}):
        target = runtime/name
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,target)
    verify(runtime)
    return runtime


def launch(args, sdk, env):
    from usd_scene_review.worker_client import WindowsJob, resume_owned_process
    state = outside_package(args.workspace)
    state.mkdir(exist_ok=False)
    # Kit's embedded Python may ignore PYTHONDONTWRITEBYTECODE. Materialize the
    # verified payload in private state so native caches never mutate the package.
    runtime = materialize_runtime(state)
    env = env.copy()
    env['PYTHONPATH'] = env['PYTHONPATH'].replace(
        str(ROOT/'exts/mmporong.scene.review/python'),
        str(runtime/'exts/mmporong.scene.review/python'))
    data = Path(args.data).expanduser().resolve()
    descriptor = json.loads((data/'sample.json').read_text(encoding='utf-8'))
    manifests = {}
    for side in ('A','B'):
        path = (data/descriptor[side]).resolve()
        if not path.is_relative_to(data) or not path.is_file():
            raise ValueError('SAMPLE_PATH: expected manifests inside the chosen sample directory')
        manifests[side] = str(path)
    config = state/'launch.json'
    config.write_text(json.dumps(dict(state=str(state),manifests=manifests,smoke=args.smoke)),encoding='utf-8')
    command = [str(sdk/'kit/kit.exe'),str(runtime/'apps/scene-review.kit'),
        '--portable','--portable-root',str(state/'portable'),
        '--ext-folder',str(sdk/'extscache'),'--ext-folder',str(sdk/'exts'),
        '--ext-folder',str(runtime/'exts'),'--/log/file='+str(state/'host.log'),
        '--/app/userConfigPath='+str(state/'user.config.json'),
        '--/exts/usd.review.distribution/config='+str(config)]
    process = None
    job = None
    try:
        with (state/'console.log').open('w',encoding='utf-8') as stream:
            process = subprocess.Popen(command,cwd=sdk,env=env,stdout=stream,stderr=subprocess.STDOUT,
                                       creationflags=0x00000004)  # assign owned job before resume
            job = WindowsJob(process)
            resume_owned_process(process)
            code = process.wait(timeout=args.timeout)
        result_path = state/'session-result.json'
        result = json.loads(result_path.read_text(encoding='utf-8')) if result_path.is_file() else {}
        clean = code==0 and result.get('status') in ('passed','closed') and result.get('preserved') is True
        (state/'process-result.json').write_text(json.dumps(dict(process_exit=code,clean=clean),indent=2),encoding='utf-8')
        if not clean:
            raise ValueError('KIT_EXIT: normal exit/preservation was not confirmed; inspect private workspace logs, not a running user app')
        print('Review completed normally. Saved reports: '+str(state/'reports'))
        return 0
    finally:
        if process and process.poll() is None:
            if job:
                job.terminate()
            else:
                process.kill()  # still suspended; no descendants were allowed to start
            process.wait(timeout=15)
        if job:
            job.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk',type=Path,help='Existing Windows Isaac Sim 4.5 SDK')
    parser.add_argument('--_prepared',action='store_true',help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest='command',required=True)
    sub.add_parser('verify')
    sub.add_parser('doctor')
    create = sub.add_parser('sample');create.add_argument('--workspace',required=True)
    diff = sub.add_parser('compare');diff.add_argument('--before',required=True);diff.add_argument('--after',required=True);diff.add_argument('--workspace',required=True)
    view = sub.add_parser('launch');view.add_argument('--data',required=True);view.add_argument('--workspace',required=True)
    view.add_argument('--smoke',action='store_true');view.add_argument('--timeout',type=float,default=14400)
    args = parser.parse_args(argv)
    try:
        verify()
        if args.command=='verify':
            print('Candidate payload checksums verified (not an authenticated signature).');return 0
        if not args.sdk:
            raise ValueError('SDK_REQUIRED: pass --sdk with your existing SDK directory')
        if args.command=='doctor':
            print(json.dumps(doctor(args.sdk),indent=2));return 0
        sdk, version, env = environment(args.sdk)
        if not args._prepared:
            # Use one matching SDK Python process; do not mix ABI/system packages.
            raw = list(sys.argv[1:] if argv is None else argv)
            return subprocess.call([str(sdk/'kit/python/python.exe'),'-B',str(ROOT/'review_kit.py'),
                                    '--_prepared',*raw],env=env)
        if args.command=='sample':
            sample(args.workspace);return 0
        if args.command=='compare':
            from usd_scene_review import compare
            from usd_scene_review.exports import save_report
            before,after = Path(args.before).resolve(),Path(args.after).resolve()
            report = compare(before,after)
            save_report(report,outside_package(args.workspace),forbidden_roots=[before.parent,after.parent])
            print('Comparison saved; status='+report['status']);return 2 if report['status']=='unknown' else 0
        if not 0 < args.timeout <= 86400:
            raise ValueError('TIMEOUT: choose a positive bound of at most 86400 seconds')
        doctor(sdk)
        return launch(args,sdk,env)
    except (OSError,ValueError,KeyError,RuntimeError,subprocess.SubprocessError,KeyboardInterrupt) as exc:
        print('Review kit error: '+str(exc)+'\nSee docs/quickstart-en.md or docs/quickstart-ko.md. No installation or driver changes were attempted.',file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
