"""Owned, isolated installed-Kit test host; never attaches to an existing app."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parent))
from package_extension import package
from shutdown_profile import PROFILES,load_profile,validate_sdk,shared_admission,finish_job,assess
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from usd_scene_review.worker_client import WindowsJob, resume_owned_process

NATIVE_FAILURES={
    'material teardown failure':'RTX Renderer Material Snapshot not unloaded properly',
    'descriptor allocation failure':'Unable to allocate descriptor sets',
    'invalid Hydra engine':'invalid HydraEngineIndex',
    'GPU command fence failure':'make sure to wait for cmdlist completion',
    'GPU device lost':'GPU crash. Device is lost or reset',
    'native crash':'[crash] A crash has occurred',
    'released Hydra texture interface':'Plugin interface for a client: omni.hydratexture.plugin was already released.',
}

def native_failures(log):
    return [name for name,signature in NATIVE_FAILURES.items() if signature in log]


def kit_environment(parent,isolated_python=False):
    """Diagnostic child-only isolation; never mutate parent/system settings."""
    env=dict(parent)
    if isolated_python:
        for key in ('PYTHONPATH','PYTHONHOME','PXR_USD_WINDOWS_DLL_PATH'):
            env.pop(key,None)
    return env


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--isaac-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--probe',type=Path,default=Path(__file__).with_name('in_app_lifecycle_probe.py'))
    parser.add_argument('--timeout',type=float,default=180)
    parser.add_argument('--full-app',action='store_true',help='Use the existing full Isaac app in a fresh portable profile')
    parser.add_argument('--baseline',action='store_true',help='Project-free full-app control unless an explicit reduced-profile treatment is selected')
    parser.add_argument('--shutdown-control',choices=('normal','file-close','uncancellable'),
                        help='Owned unchanged-fixture shutdown route; requires --baseline and containment')
    parser.add_argument('--shutdown-profile',choices=PROFILES,help='Pinned owned baseline only; requires official shared wrapper')
    parser.add_argument('--shutdown-candidate',choices=('viewport-reuse','viewport-bounds'),help='Explicit project treatment, no-navigation profile only')
    parser.add_argument('--attach-control',choices=('wait','attach','open'),help='Matched 60-update no-viewport control, reduced profile only')
    parser.add_argument('--full-feature-validation',action='store_true',help='Explicit owned-host probe-only access behind the unchanged full-app product guard')
    parser.add_argument('--verify-full-guard',action='store_true',help='SDK topology probe also checks product Full Isaac refusal before native review ownership')
    parser.add_argument('--fail-fast-native',action='store_true',help='Contain the owned Job at the first known native graphics failure')
    parser.add_argument('--isolated-python-environment',action='store_true',help='Diagnostic control: Kit bootstraps its own Python/USD paths in the owned child only')
    parser.add_argument('--topology',choices=('single','shared','two-contexts','sequence'),default='shared',
                        help='SDK-only engine probe control; unused by product acceptance probes')
    args=parser.parse_args();sdk=args.isaac_root.resolve();root=args.output.resolve()
    if args.probe.name=='in_app_native_texture_probe.py' and (not args.full_app or not args.fail_fast_native):
        parser.error('native texture reproducer requires --full-app and --fail-fast-native')
    if args.baseline and not args.full_app:parser.error('--baseline requires --full-app')
    if args.shutdown_control and (not args.baseline or not args.fail_fast_native):
        parser.error('--shutdown-control requires --baseline --full-app --fail-fast-native')
    if args.full_feature_validation and (not args.full_app or args.baseline):
        parser.error('--full-feature-validation requires --full-app without --baseline')
    if args.verify_full_guard and (not args.full_app or args.baseline):
        parser.error('--verify-full-guard requires --full-app without --baseline')
    if args.shutdown_profile and not (args.full_app and args.baseline and args.shutdown_control=='file-close' and args.fail_fast_native):
        parser.error('--shutdown-profile requires --full-app --baseline --shutdown-control file-close --fail-fast-native')
    if args.shutdown_candidate and args.shutdown_profile!='no-navigation':
        parser.error('--shutdown-candidate requires the pinned no-navigation profile')
    if args.attach_control and (args.shutdown_profile!='no-navigation' or args.shutdown_candidate):
        parser.error('--attach-control requires no-navigation without a candidate')
    profile=fixture_data=None
    if args.shutdown_profile:
        profile,fixture_data=load_profile(args.shutdown_profile)
        profile['candidate']=args.shutdown_candidate
        profile['attach_control']=args.attach_control
        validate_sdk(sdk,profile)
    # Every native diagnostic now requires real canonical lease ownership, not
    # an idle snapshot or a completed/old JSON owner string.
    admission=shared_admission(profile['owner'] if profile else None)
    root.mkdir(parents=True,exist_ok=False)
    if profile:(root/'shutdown-profile.json').write_text(json.dumps(profile,indent=2))
    fixture=root/'shutdown-fixture.usda'
    if fixture_data is not None:
        fixture.write_bytes(fixture_data)
    elif args.shutdown_control:
        fixture.write_text('#usda 1.0\n(\n    upAxis = "Z"\n    metersPerUnit = 1\n)\ndef Xform "World" {\n    def Cube "Item" {\n        double size = 2\n    }\n}\n',encoding='utf-8')
    fixture_hash=hashlib.sha256(fixture.read_bytes()).hexdigest() if args.shutdown_control else None
    if not args.baseline or args.shutdown_candidate=='viewport-bounds':
        package(root/'extension.zip')
        with zipfile.ZipFile(root/'extension.zip') as archive:
            archive.extractall(root/'exts/mmporong.scene.review')
    if args.shutdown_candidate=='viewport-bounds':
        from viewport_bounds_candidate import prepare
        prepare(root,fixture_data)
    runner=root/'exts/in.app.probe';(runner/'config').mkdir(parents=True)
    (runner/'config/extension.toml').write_text('''[package]
version="0.1.0"
[dependencies]
"omni.usd"={}
"omni.timeline"={}
"omni.kit.widget.viewport"={}
"omni.kit.viewport.utility"={}
"omni.kit.ui_test"={}
"omni.kit.renderer.capture"={}
[[python.module]]
name="probe"
''',encoding='utf-8')
    probe=Path(__file__).with_name('in_app_shutdown_probe.py') if args.shutdown_control else (
        Path(__file__).with_name('in_app_baseline_probe.py') if args.baseline else args.probe)
    shutil.copyfile(probe,runner/'probe.py')
    if args.shutdown_control:
        shutil.copyfile(Path(__file__).with_name('shutdown_observation.py'),runner/'shutdown_observation.py')
    if args.attach_control:
        shutil.copyfile(Path(__file__).with_name('attach_only_control.py'),runner/'attach_only_control.py')
    if args.shutdown_candidate:
        name='viewport_bounds_candidate.py' if args.shutdown_candidate=='viewport-bounds' else 'viewport_reuse_candidate.py'
        shutil.copyfile(Path(__file__).with_name(name),runner/name)
    app=root/'in-app.kit'
    app.write_text('''[package]
title="USD Review In-App Validation"
[dependencies]
"omni.kit.uiapp"={}
"omni.kit.viewport.rtx"={}
"in.app.probe"={}
[settings]
app.window.width=1600
app.window.height=900
app.asyncRendering=false
app.fastShutdown=false
app.settings.persistent=false
app.extensions.registryEnabled=false
app.extensions.syncRegistryOnStartup=false
renderer.multiGpu.autoEnable=false
exts."omni.kit.viewport.window".startup.disableWindowOnLoad=true
''',encoding='utf-8')
    selected=sdk/'apps/isaacsim.exp.full.kit' if args.full_app else app
    command=[str(sdk/'kit/kit.exe'),str(selected),'--portable','--portable-root',str(root/'state'),
             '--ext-folder',str(sdk/'apps'),'--enable','in.app.probe',
             '--ext-folder',str(sdk/'extscache'),'--ext-folder',str(sdk/'exts'),
             '--ext-folder',str(root/'exts'),'--/log/file='+str(root/'kit.log'),
             '--/app/userConfigPath='+str(root/'user.config.json'),
             '--/exts/in.app.probe/output='+str(root),
             '--/exts/in.app.probe/shutdownRoute='+str(args.shutdown_control or ''),
             '--/exts/in.app.probe/profile='+('shutdown-profile.json' if profile else ''),
             '--/exts/in.app.probe/topology='+args.topology,
             '--/exts/in.app.probe/fullFeatureValidation='+str(args.full_feature_validation).lower(),
             '--/exts/in.app.probe/verifyFullGuard='+str(args.verify_full_guard).lower(),
             '--/app/fastShutdown=false','--/app/settings/persistent=false',
             '--/app/extensions/registryEnabled=false','--/app/extensions/syncRegistryOnStartup=false',
             '--/renderer/multiGpu/autoEnable=false','--/app/asyncRendering=false',
             '--/app/window/width=1600','--/app/window/height=900']
    if profile:
        command+=['--/app/extensions/excluded/'+str(i)+'='+name for i,name in enumerate(profile['exclusions'])]
        command+=['--enable',profile['required_schema']]
    process=job=None
    def receipt(result):
        nonlocal job
        result.update(owned_pid=process.pid,owned_process_reaped=process.poll() is not None)
        result['shared_admission']=admission
        if job:
            try:result.update(finish_job(job))
            except Exception as exc:
                result.update(owned_job_empty=False,owned_job_cleanup_error=type(exc).__name__)
            finally:
                job.close();job=None
        result['owned_job_closed']=True
        if fixture_hash is not None:
            result['fixture_bytes_preserved']=fixture.is_file() and hashlib.sha256(fixture.read_bytes()).hexdigest()==fixture_hash
        report=json.loads((root/'result.json').read_text()) if (root/'result.json').exists() else {}
        result.update(assess(report,result,(root/'console.log').read_text(encoding='utf-8',errors='replace'),profile))
        (root/'process-result.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result))
    parent_env=dict(os.environ)
    env=kit_environment(parent_env,args.isolated_python_environment)
    (root/'launch-environment.json').write_text(json.dumps({
        'isolated_python':args.isolated_python_environment,
        'removed_variable_names':sorted(set(parent_env)-set(env))},indent=2))
    try:
        confirmed=shared_admission(profile['owner'] if profile else None)
        if confirmed['lease_id']!=admission['lease_id']:
            raise RuntimeError('Shared lease changed before suspended host creation')
        with (root/'console.log').open('w',encoding='utf-8') as log:
            process=subprocess.Popen(command,cwd=sdk,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=4)
            job=WindowsJob(process);resume_owned_process(process)
            try:
                deadline=time.monotonic()+args.timeout
                while process.poll() is None:
                    if args.fail_fast_native:
                        failures=native_failures((root/'console.log').read_text(encoding='utf-8',errors='replace'))
                        if failures:
                            job.terminate();process.wait(timeout=15)
                            result=dict(process_exit=process.returncode,passed=False,native_errors=failures,
                                        termination='owned Job contained after native failure; not a clean shutdown')
                            receipt(result);return 1
                    if profile:
                        try:
                            probe_report=json.loads((root/'result.json').read_text())
                        except (FileNotFoundError,PermissionError,json.JSONDecodeError):
                            probe_report={}
                        if probe_report.get('status')=='failed':
                            job.terminate();process.wait(timeout=15)
                            result=dict(process_exit=process.returncode,passed=False,native_errors=[],
                                termination='owned Job contained after failed probe; not a clean shutdown')
                            receipt(result);return 1
                    remaining=deadline-time.monotonic()
                    if remaining<=0:raise subprocess.TimeoutExpired(command,args.timeout)
                    try:process.wait(timeout=min(.5,remaining))
                    except subprocess.TimeoutExpired:pass
                code=process.returncode
            except subprocess.TimeoutExpired:
                job.terminate();process.wait(timeout=15)
                result=dict(process_exit=process.returncode,passed=False,timed_out=True,
                            termination='owned Windows Job terminated; not a clean shutdown')
                receipt(result);return 1
        report=json.loads((root/'result.json').read_text()) if (root/'result.json').exists() else {}
        failures=native_failures((root/'console.log').read_text(encoding='utf-8',errors='replace'))
        result=dict(process_exit=code,functional_checks_passed=report.get('status')=='passed',native_errors=failures,
                    passed=code==0 and report.get('status')=='passed' and not failures)
        receipt(result)
        return 0 if result['passed'] else (2 if result['native_exit_ok'] and result['profile_conditions_met'] else 1)
    finally:
        if process and process.poll() is None:
            if job:job.terminate()
            else:process.kill()
            process.wait(timeout=15)
        if job:job.close()


if __name__=='__main__':raise SystemExit(main())
