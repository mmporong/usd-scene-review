"""Use an existing Isaac Sim bundled OpenUSD; never installs packages or starts Kit."""
import argparse
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--isaac-root", required=True, type=Path, help="Existing isaacsim package or SDK directory")
    parser.add_argument("--python", default=sys.executable, help="Python matching the installed OpenUSD ABI (3.10 for Isaac Sim 4.5)")
    parser.add_argument("--timeout", type=float, help="Optional child-process timeout in seconds")
    parser.add_argument("args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    roots = sorted(args.isaac_root.glob("extscache/omni.usd.libs-*"))
    if len(roots) != 1 or not (roots[0] / "pxr").is_dir():
        parser.error("expected one existing omni.usd.libs bundle; configure the OpenUSD environment manually otherwise")
    env = os.environ.copy()
    repo = Path(__file__).resolve().parents[1]
    env["PYTHONPATH"] = os.pathsep.join([str(repo / "src"), str(roots[0]), env.get("PYTHONPATH", "")])
    if os.name == "nt":
        # USD's WindowsImportWrapper passes these directories to add_dll_directory.
        # This also reaches CLI subprocesses without modifying the system PATH.
        env["PXR_USD_WINDOWS_DLL_PATH"] = os.pathsep.join([
            str(roots[0] / "bin"), str(args.isaac_root / "kit"),
            env.get("PXR_USD_WINDOWS_DLL_PATH", env.get("PATH", ""))])
    else:
        env["LD_LIBRARY_PATH"] = os.pathsep.join([str(roots[0] / "bin"), str(args.isaac_root / "kit"), str(Path(args.python).absolute().parent.parent / "lib"), env.get("LD_LIBRARY_PATH", "")])
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    command = args.args[1:] if args.args[:1] == ["--"] else args.args
    if not command:
        parser.error("provide Python arguments after --, for example -m unittest discover -s tests")
    try:
        return subprocess.call([args.python, "-B", *command], env=env, timeout=args.timeout)
    except subprocess.TimeoutExpired:
        print("OpenUSD child process timed out", file=sys.stderr)
        return 124


if __name__ == "__main__":
    raise SystemExit(main())
