"""Owned, isolated installed-Kit test host; never attaches to an existing app."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile
from package_extension import package
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


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--isaac-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--probe',type=Path,default=Path(__file__).with_name('in_app_lifecycle_probe.py'))
    parser.add_argument('--timeout',type=float,default=180)
    parser.add_argument('--full-app',action='store_true',help='Use the existing full Isaac app in a fresh portable profile')
    parser.add_argument('--baseline',action='store_true',help='Project-free full-app control; does not package or expose the review extension')
    parser.add_argument('--fail-fast-native',action='store_true',help='Contain the owned Job at the first known native graphics failure')
    parser.add_argument('--topology',choices=('single','shared','two-contexts','sequence'),default='shared',
                        help='SDK-only engine probe control; unused by product acceptance probes')
    args=parser.parse_args();sdk=args.isaac_root.resolve();root=args.output.resolve()
    if args.baseline and not args.full_app:parser.error('--baseline requires --full-app')
    root.mkdir(parents=True,exist_ok=False)
    if not args.baseline:
        package(root/'extension.zip')
        with zipfile.ZipFile(root/'extension.zip') as archive:
            archive.extractall(root/'exts/mmporong.scene.review')
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
    probe=Path(__file__).with_name('in_app_baseline_probe.py') if args.baseline else args.probe
    shutil.copyfile(probe,runner/'probe.py')
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
             '--/exts/in.app.probe/topology='+args.topology,
             '--/app/fastShutdown=false','--/app/settings/persistent=false',
             '--/app/extensions/registryEnabled=false','--/app/extensions/syncRegistryOnStartup=false',
             '--/renderer/multiGpu/autoEnable=false','--/app/asyncRendering=false',
             '--/app/window/width=1600','--/app/window/height=900']
    process=job=None
    try:
        with (root/'console.log').open('w',encoding='utf-8') as log:
            process=subprocess.Popen(command,cwd=sdk,stdout=log,stderr=subprocess.STDOUT,creationflags=4)
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
                            (root/'process-result.json').write_text(json.dumps(result,indent=2))
                            print(json.dumps(result));return 1
                    remaining=deadline-time.monotonic()
                    if remaining<=0:raise subprocess.TimeoutExpired(command,args.timeout)
                    try:process.wait(timeout=min(.5,remaining))
                    except subprocess.TimeoutExpired:pass
                code=process.returncode
            except subprocess.TimeoutExpired:
                job.terminate();process.wait(timeout=15)
                result=dict(process_exit=process.returncode,passed=False,timed_out=True,
                            termination='owned Windows Job terminated; not a clean shutdown')
                (root/'process-result.json').write_text(json.dumps(result,indent=2))
                print(json.dumps(result));return 1
        report=json.loads((root/'result.json').read_text()) if (root/'result.json').exists() else {}
        failures=native_failures((root/'console.log').read_text(encoding='utf-8',errors='replace'))
        result=dict(process_exit=code,functional_checks_passed=report.get('status')=='passed',native_errors=failures,
                    passed=code==0 and report.get('status')=='passed' and not failures)
        (root/'process-result.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result));return 0 if result['passed'] else 1
    finally:
        if process and process.poll() is None:
            if job:job.terminate()
            else:process.kill()
            process.wait(timeout=15)
        if job:job.close()


if __name__=='__main__':raise SystemExit(main())
