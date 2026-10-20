"""Run synthetic GUI acceptance in a fresh, process-isolated installed Kit SDK."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
from package_extension import package


def completion_status(root, returncode):
    if returncode:
        return returncode
    try:
        report = json.loads((root / 'results/result.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        print('Kit exited without a readable acceptance result', file=sys.stderr)
        return 2
    if report.get('status') != 'passed':
        print('Native Kit acceptance did not pass', file=sys.stderr)
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--isaac-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New private output directory; must not exist')
    parser.add_argument('--timeout', type=float, default=180)
    args = parser.parse_args()
    sdk = args.isaac_root.resolve()
    executable = sdk / 'kit' / ('kit.exe' if sys.platform == 'win32' else 'kit')
    if not executable.is_file() or not (sdk / 'extscache').is_dir():
        parser.error('expected an existing Kit executable and extscache; nothing is installed')
    root = args.output.absolute()
    root.mkdir(parents=True, exist_ok=False)
    package(root / 'extension.zip')
    with zipfile.ZipFile(root / 'extension.zip') as archive:
        archive.extractall(root / 'exts/mmporong.scene.review')
    runner = root / 'exts/validation.runner'
    (runner / 'config').mkdir(parents=True)
    (runner / 'config/extension.toml').write_text('''[package]
version="0.1.0"
[dependencies]
"omni.usd"={}
"omni.kit.viewport.window"={}
"omni.kit.viewport.utility"={}
"omni.kit.ui_test"={}
"omni.kit.renderer.capture"={}
[[python.module]]
name="probe"
''', encoding='utf-8')
    shutil.copyfile(Path(__file__).with_name('kit_native_probe.py'), runner / 'probe.py')
    app = root / 'validation.kit'
    app.write_text('''[package]
title="USD Scene Review Isolated Validation"
version="0.1.0"
[dependencies]
"omni.kit.uiapp"={}
"omni.kit.viewport.rtx"={}
"validation.runner"={}
[settings]
app.window.title="USD Scene Review Isolated Validation"
app.window.width=1600
app.window.height=1000
app.settings.persistent=false
app.extensions.registryEnabled=false
app.extensions.syncRegistryOnStartup=false
app.runLoops.main.rateLimitEnabled=true
app.runLoops.main.rateLimitFrequency=60
app.asyncRendering=false
renderer.multiGpu.autoEnable=false
exts."omni.kit.viewport.window".startup.disableWindowOnLoad=true
''', encoding='utf-8')
    command = [str(executable), str(app), '--portable', '--portable-root', str(root / 'state'),
               '--ext-folder', str(sdk / 'extscache'), '--ext-folder', str(sdk / 'exts'),
               '--ext-folder', str(root / 'exts'), '--/log/file=' + str(root / 'kit.log'),
               '--/app/userConfigPath=' + str(root / 'user.config.json'), '--/app/fastShutdown=true']
    with (root / 'console.log').open('w', encoding='utf-8') as log:
        try:
            result = subprocess.run(command, cwd=root, stdout=log, stderr=subprocess.STDOUT, timeout=args.timeout)
        except subprocess.TimeoutExpired:
            print('Kit validation timed out; only the newly launched process was stopped', file=sys.stderr)
            return 124
    print('Native Kit validation process exit:', result.returncode)
    return completion_status(root, result.returncode)


if __name__ == '__main__':
    raise SystemExit(main())
