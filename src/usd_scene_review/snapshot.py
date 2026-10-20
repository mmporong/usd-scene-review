"""Strict local dependency bundles. No source layer is exported or saved."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import shutil
from pxr import Ar, Sdf, Usd, UsdUtils


def canonical(value):
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _relative(path, base):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("symlink dependency unsupported")
    resolved = path.resolve()
    resolved.relative_to(base)
    # Reject symlink components, including ones resolving inside the directory.
    for component in (path, *path.parents):
        if component == base.parent:
            break
        if component.is_symlink():
            raise ValueError("symlink dependency unsupported")
    return resolved


def _discover(entry):
    base = entry.parent.resolve()
    if type(Ar.GetUnderlyingResolver()).__name__ != "DefaultResolver":
        return {}, ["custom resolver unsupported"]
    pending, found, reasons = [entry], {}, []
    while pending:
        candidate = pending.pop()
        try:
            path = _relative(candidate, base)
        except ValueError:
            reasons.append("dependency escapes root or uses symlink")
            continue
        rel = path.relative_to(base).as_posix()
        if rel in found:
            continue
        if not path.is_file():
            reasons.append("missing dependency: " + rel)
            continue
        if path.suffix.lower() not in (".usd", ".usda", ".usdc"):
            reasons.append("unsupported dependency type: " + rel)
            continue
        found[rel] = digest(path)
        try:
            layer = Sdf.Layer.FindOrOpen(str(path))
            if not layer:
                raise ValueError("cannot open layer")
            if layer.dirty:
                reasons.append("dirty source layer: " + rel)
            fresh = Sdf.Layer.OpenAsAnonymous(str(path))
            if not fresh or fresh.ExportToString() != layer.ExportToString():
                reasons.append("cached layer differs from disk: " + rel)
            def inspect(specpath):
                spec = layer.GetObjectAtPath(specpath)
                if isinstance(spec, Sdf.AttributeSpec) and spec.typeName in (Sdf.ValueTypeNames.Asset, Sdf.ValueTypeNames.AssetArray):
                    reasons.append("asset-valued property unsupported: " + rel)
                if isinstance(spec, Sdf.PrimSpec):
                    if any(spec.HasInfo(k) for k in ("inheritPaths", "specializes", "relocates")):
                        reasons.append("inheritance, specialization or relocates unsupported: " + rel)
                    if spec.HasInfo("clips"):
                        reasons.append("value clips unsupported: " + rel)
                    if spec.HasInfo("instanceable") and spec.GetInfo("instanceable"):
                        reasons.append("instancing unsupported: " + rel)
                    if str(spec.typeName) == "PointInstancer":
                        reasons.append("point instancer unsupported: " + rel)
            layer.Traverse(Sdf.Path.absoluteRootPath, inspect)
            groups = UsdUtils.ExtractExternalReferences(str(path))
            for ref in sorted(set(x for group in groups for x in group)):
                if not ref:
                    continue
                if ":" in ref or Path(ref).is_absolute() or "[" in ref:
                    reasons.append("non-local or package dependency unsupported: " + rel)
                else:
                    pending.append(path.parent / ref)
        except Exception:
            reasons.append("unreadable USD layer: " + rel)
    return found, sorted(set(reasons))


def create_snapshot(entry, destination, *, time="default", variants=None, load="all"):
    entry = Path(entry).absolute()
    destination = Path(destination).absolute()
    if destination.exists():
        raise ValueError("snapshot destination must not exist")
    if not entry.is_file():
        raise ValueError("entry must be a local USD file")
    if load != "all":
        raise ValueError("only load=all is supported")
    if time != "default":
        time = float(time)
        canonical(time)  # rejects NaN/infinity
    if variants is not None and not isinstance(variants, dict):
        raise ValueError("variants must be a JSON object")
    variants = dict(sorted((variants or {}).items()))
    for key, value in variants.items():
        if not isinstance(key, str) or ":" not in key or not isinstance(value, str):
            raise ValueError("variants require /Prim:variantSet -> selection")
    files, reasons = _discover(entry)
    destination.mkdir(parents=True)
    for rel, expected in sorted(files.items()):
        source, target = entry.parent / rel, destination / "layers" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if digest(source) != expected or digest(target) != expected:
            reasons.append("input changed while snapshotting: " + rel)
    for rel, expected in sorted(files.items()):
        try:
            if digest(entry.parent / rel) != expected:
                reasons.append("input changed while snapshotting: " + rel)
        except OSError:
            reasons.append("input missing while snapshotting: " + rel)
    manifest = {"schema": 1, "entry": entry.name, "config": {"time": time, "variants": variants, "load": load},
                "files": files, "status": "unknown" if reasons else "ready", "reasons": sorted(set(reasons))}
    (destination / "manifest.json").write_text(canonical(manifest), encoding="utf-8")
    return destination / "manifest.json"


@dataclass
class Snapshot:
    stage: object
    manifest: dict
    root: Path
    errors: list[str]
    manifest_path: Path | None = None
    manifest_hash: str = ""


def verify(snapshot):
    errors = list(snapshot.errors)
    if snapshot.manifest_path is not None:
        try:
            if digest(snapshot.manifest_path) != snapshot.manifest_hash:
                errors.append("snapshot manifest changed")
        except OSError:
            errors.append("snapshot manifest missing")
    for rel, expected in snapshot.manifest.get("files", {}).items():
        try:
            path = _relative(snapshot.root.parent / rel, snapshot.root.parent.resolve())
            if digest(path) != expected:
                errors.append("bundle hash mismatch: " + rel)
        except (ValueError, OSError):
            errors.append("missing or unsafe bundle dependency: " + rel)
    if snapshot.stage:
        for layer in snapshot.stage.GetUsedLayers():
            if layer != snapshot.stage.GetSessionLayer() and layer.dirty:
                errors.append("source layer dirty")
    return sorted(set(errors))


def _reject_constant(_text):
    raise ValueError("non-finite JSON constant")


def _apply_variants(stage, variants):
    """Resolve declared choices as sets become available; never invent prims.

    Parent paths run first, and unavailable same-prim dependencies are retried.
    No search through unspecified intermediate selections is performed. Every
    requested set must still exist and match after all recomposition completes.
    """
    ordered = []
    for key, choice in variants.items():
        primpath, name = key.rsplit(":", 1)
        path = Sdf.Path(primpath)
        if not path.IsAbsolutePath() or not path.IsPrimPath() or path.ContainsPrimVariantSelection() or not name:
            return ["invalid variant key: " + key]
        ordered.append((primpath.count("/"), key, primpath, name, choice))
    ordered.sort()
    pending = list(ordered)
    errors = []
    while pending:
        deferred = []
        for item in pending:
            _, key, primpath, name, choice = item
            prim = stage.GetPrimAtPath(primpath)
            if not prim or not prim.IsActive() or name not in prim.GetVariantSets().GetNames():
                deferred.append(item)
                continue
            variant = prim.GetVariantSet(name)
            if choice not in variant.GetVariantNames():
                deferred.append(item)
                continue
            if not variant.SetVariantSelection(choice):
                errors.append("variant selection rejected: " + key)
        if len(deferred) == len(pending):
            break
        pending = deferred
    for _, key, primpath, name, choice in ordered:
        prim = stage.GetPrimAtPath(primpath)
        if not prim or not prim.IsActive() or name not in prim.GetVariantSets().GetNames():
            errors.append("variant configuration unresolved or mutually exclusive: " + key)
            continue
        variant = prim.GetVariantSet(name)
        if choice not in variant.GetVariantNames() or variant.GetVariantSelection() != choice:
            errors.append("variant configuration unresolved or mutually exclusive: " + key)
    return sorted(set(errors))


def load_snapshot(manifest_path):
    p = Path(manifest_path).resolve()
    try:
        raw_manifest = p.read_bytes()
        manifest = json.loads(raw_manifest.decode("utf-8"), parse_constant=_reject_constant)
        if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), dict):
            raise ValueError("manifest object required")
        if not all(isinstance(k, str) and isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v) for k, v in manifest["files"].items()):
            raise ValueError("invalid file digest")
        if not isinstance(manifest.get("reasons"), list) or not all(isinstance(v, str) for v in manifest["reasons"]):
            raise ValueError("invalid reasons")
        root = p.parent / "layers" / manifest["entry"]
        errors = list(manifest.get("reasons", []))
        if manifest.get("schema") != 1 or manifest.get("status") != "ready":
            errors.append("snapshot not ready")
        config = manifest["config"]
        t = config["time"]
        if t != "default" and (isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t)):
            raise ValueError("invalid time")
        variants = config["variants"]
        if not isinstance(variants, dict) or not all(isinstance(k, str) and ":" in k and isinstance(v, str) for k, v in variants.items()):
            raise ValueError("invalid variants")
        if config.get("load") != "all" or set(config) != {"time", "variants", "load"}:
            errors.append("unsupported composition configuration")
        if Path(manifest["entry"]).name != manifest["entry"] or manifest["entry"] not in manifest["files"]:
            errors.append("invalid snapshot entry")
        snapshot = Snapshot(None, manifest, root, errors, p, hashlib.sha256(raw_manifest).hexdigest())
        if errors:
            return snapshot
        snapshot.errors = verify(snapshot)
        if snapshot.errors:
            return snapshot
        # Re-discover to catch omitted files in a hand-edited manifest.
        files, reasons = _discover(root)
        if files != manifest["files"] or reasons:
            snapshot.errors.extend(reasons or ["dependency manifest incomplete"])
            return snapshot
        layer = Sdf.Layer.FindOrOpen(str(root))
        session = Sdf.Layer.CreateAnonymous("scene-review-session")
        stage = Usd.Stage.Open(layer, session, Usd.Stage.LoadAll)
        stage.SetEditTarget(session)
        snapshot.errors.extend(_apply_variants(stage, config["variants"]))
        if any(prim.GetPrimIndex().localErrors for prim in stage.TraverseAll()):
            snapshot.errors.append("USD composition errors")
        if any(prim.HasPayload() and prim.IsActive() and not prim.IsLoaded() for prim in stage.TraverseAll()):
            snapshot.errors.append("unloaded payload")
        snapshot.stage = stage
        snapshot.errors = verify(snapshot)
        return snapshot
    except Exception:
        return Snapshot(None, {}, p.parent / "layers" / "invalid", ["invalid or unreadable snapshot manifest"])
