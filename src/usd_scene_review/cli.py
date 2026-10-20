"""Offline JSON/HTML CLI. No renderer, network or AI service."""
import argparse
import html
import json
from pathlib import Path
from . import compare, create_snapshot
from .snapshot import canonical


def render_html(report):
    payload = html.escape(canonical(report))
    return '<!doctype html><html lang="en"><meta charset="utf-8"><title>USD Scene Review</title><style>body{font:16px system-ui;max-width:1000px;margin:2rem auto;padding:1rem;color:#18212a;background:#fff}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>USD Scene Review</h1><p>Status: ' + html.escape(report['status']) + '</p><p>Single configured sample. Collision evidence is unknown. No source files were edited.</p><pre>' + payload + '</pre></html>\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    snap = sub.add_parser("snapshot")
    snap.add_argument("entry"); snap.add_argument("destination")
    snap.add_argument("--time", default="default")
    snap.add_argument("--variants", default="{}", help='JSON map: {"/World:layout":"A"}')
    diff = sub.add_parser("compare")
    diff.add_argument("before"); diff.add_argument("after")
    diff.add_argument("--json", required=True); diff.add_argument("--html")
    diff.add_argument("--max-translation", type=float); diff.add_argument("--max-rotation-degrees", type=float)
    args = parser.parse_args(argv)
    try:
        if args.command == "snapshot":
            manifest = create_snapshot(args.entry, args.destination, time=args.time, variants=json.loads(args.variants))
            state = json.loads(manifest.read_text())["status"]
            print(canonical({"status": state}), end="")
            return 2 if state == "unknown" else 0
        policy = {k: v for k, v in {"max_translation": args.max_translation, "max_rotation_degrees": args.max_rotation_degrees}.items() if v is not None}
        report = compare(args.before, args.after, policy=policy)
        outputs = [Path(args.json)] + ([Path(args.html)] if args.html else [])
        # Reports must not overwrite any existing input or artifact.
        if len({p.resolve() for p in outputs}) != len(outputs) or any(p.exists() or p.is_symlink() for p in outputs):
            raise ValueError("report destinations must be distinct new files")
        Path(args.json).write_text(canonical(report), encoding="utf-8")
        if args.html:
            Path(args.html).write_text(render_html(report), encoding="utf-8")
        return 2 if report["status"] == "unknown" or any(x["status"] == "unknown" for x in report["policy"]) else 3 if any(x["status"] == "fail" for x in report["policy"]) else 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, "Error: " + str(exc) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
