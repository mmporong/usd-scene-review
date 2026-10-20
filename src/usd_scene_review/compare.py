"""Observed semantic changes, separated from authored property-stack evidence."""
from __future__ import annotations

import math
from pathlib import Path
from pxr import Usd, UsdGeom, Sdf
from .snapshot import load_snapshot, verify

EPS = 1e-8


def value(v):
    if v is None or isinstance(v, (str, bool, int)):
        return v
    if isinstance(v, float):
        return v if math.isfinite(v) else str(v)
    if isinstance(v, Sdf.AssetPath):
        return {"asset": v.path}
    if hasattr(v, "GetReal") and hasattr(v, "GetImaginary"):
        return [value(v.GetReal()), *value(v.GetImaginary())]
    if isinstance(v, dict):
        return {str(k): value(x) for k, x in sorted(v.items(), key=lambda item: str(item[0]))}
    try:
        return [value(x) for x in v]
    except TypeError:
        return str(v)


def same(a, b):
    if isinstance(a, (bool, int)) or isinstance(b, (bool, int)):
        return type(a) is type(b) and a == b
    if isinstance(a, float) and isinstance(b, float):
        return math.isclose(a, b, rel_tol=0.0, abs_tol=EPS)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    return a == b


def _opinions(prop, snapshot, time):
    records = []
    # USD 22.11 requires the time argument; use the same sample as effective values.
    for spec in prop.GetPropertyStack(time):
        if spec.layer == snapshot.stage.GetSessionLayer():
            continue
        try:
            layer = Path(spec.layer.realPath).relative_to(snapshot.root.parent).as_posix()
        except ValueError:
            layer = "unsupported-layer"
        records.append({"layer": layer, "path": str(spec.path),
                        "fields": {k: value(spec.GetInfo(k)) for k in sorted(spec.ListInfoKeys())}})
    return records


def _prim_opinions(prim, snapshot):
    records = []
    for spec in prim.GetPrimStack():
        if spec.layer == snapshot.stage.GetSessionLayer():
            continue
        try:
            layer = Path(spec.layer.realPath).relative_to(snapshot.root.parent).as_posix()
        except ValueError:
            layer = "unsupported-layer"
        # Composition/identity metadata. Children and properties are compared separately.
        keys = [k for k in spec.ListInfoKeys() if k not in ("primChildren", "properties", "variantSetChildren")]
        records.append({"layer": layer, "path": str(spec.path), "fields": {k: value(spec.GetInfo(k)) for k in sorted(keys)}})
    return records


def _layer_metadata(snapshot):
    result = {}
    for layer in snapshot.stage.GetUsedLayers():
        if layer == snapshot.stage.GetSessionLayer():
            continue
        rel = Path(layer.realPath).relative_to(snapshot.root.parent).as_posix()
        root = layer.pseudoRoot
        result[rel] = {k: value(root.GetInfo(k)) for k in sorted(root.ListInfoKeys()) if k not in ("primChildren", "subLayerOffsets")}
        result[rel]["subLayerOffsets"] = [{"offset": item.offset, "scale": item.scale} for item in layer.subLayerOffsets]
    return result


def _observe(snapshot):
    stage = snapshot.stage
    t = snapshot.manifest["config"]["time"]
    time = Usd.TimeCode.Default() if t == "default" else Usd.TimeCode(float(t))
    cache = UsdGeom.XformCache(time)
    records = {}
    for prim in stage.TraverseAll():
        path = str(prim.GetPath())
        attrs = {}
        attr_types = {}
        authored = {"@prim": _prim_opinions(prim, snapshot)}
        for prop in prim.GetProperties():
            authored[prop.GetName()] = _opinions(prop, snapshot, time)
            if isinstance(prop, Usd.Attribute):
                attr_types[prop.GetName()] = str(prop.GetTypeName())
                if not prop.GetName().startswith("xformOp:") and prop.GetName() not in ("xformOpOrder", "visibility"):
                    attrs[prop.GetName()] = value(prop.Get(time))
            elif isinstance(prop, Usd.Relationship):
                attrs[prop.GetName()] = [str(x) for x in prop.GetTargets()]
        imageable = UsdGeom.Imageable(prim)
        xformable = UsdGeom.Xformable(prim)
        records[path] = {"active": prim.IsActive(), "type": prim.GetTypeName(), "attributes": attrs, "attribute_types": attr_types,
                         "visibility": str(imageable.ComputeVisibility(time)) if imageable and prim.IsActive() else None,
                         "authored": authored, "local": value(xformable.GetLocalTransformation(time)) if xformable else None,
                         "world": value(cache.GetLocalToWorldTransform(prim)) if xformable else None,
                         "reset": bool(xformable.GetResetXformStack()) if xformable else False}
    return records


def _hidden(path, records):
    parent = Sdf.Path(path).GetParentPath()
    while parent != Sdf.Path.absoluteRootPath:
        record = records.get(str(parent))
        if record and not record["active"]:
            return True
        parent = parent.GetParentPath()
    return False


def rigid_delta(a, b):
    """Row-vector affine matrices; no scale/shear/reflection rotation verdict."""
    if a is None or b is None:
        return {"status": "unknown", "reason": "not xformable"}
    for matrix in (a, b):
        if not same([matrix[i][3] for i in range(4)], [0.0, 0.0, 0.0, 1.0]):
            return {"status": "unknown", "reason": "non-affine matrix"}
        r = [row[:3] for row in matrix[:3]]
        if any(not math.isclose(sum(r[i][k] * r[j][k] for k in range(3)), float(i == j), abs_tol=EPS) for i in range(3) for j in range(3)):
            return {"status": "unknown", "reason": "scale, shear or singular matrix"}
        det = (r[0][0]*(r[1][1]*r[2][2]-r[1][2]*r[2][1]) - r[0][1]*(r[1][0]*r[2][2]-r[1][2]*r[2][0]) + r[0][2]*(r[1][0]*r[2][1]-r[1][1]*r[2][0]))
        if det < 0:
            return {"status": "unknown", "reason": "reflection"}
    # trace(Ra^T Rb) yields the same shortest relative angle as |qa dot qb|.
    trace = sum(a[i][j] * b[i][j] for i in range(3) for j in range(3))
    angle = math.degrees(math.acos(max(-1.0, min(1.0, (trace - 1.0) / 2.0))))
    return {"status": "known", "translation_stage_units": math.dist(a[3][:3], b[3][:3]), "rotation_degrees": angle}


def compare(a_manifest_path, b_manifest_path, *, policy=None):
    a, b = load_snapshot(a_manifest_path), load_snapshot(b_manifest_path)
    result = {"schema": 1, "status": "unknown", "config": a.manifest.get("config"), "reasons": [], "changes": [], "parent_groups": [], "layer_changes": [],
              "revision_files": {"A": a.manifest.get("files", {}), "B": b.manifest.get("files", {})},
              "policy": [], "clash": {"status": "unknown", "reason": "Clash adapter not available in V1"}}
    reasons = ["A: " + x for x in verify(a)] + ["B: " + x for x in verify(b)]
    if a.manifest.get("config") != b.manifest.get("config"):
        reasons.append("composition configuration mismatch")
    if reasons or a.stage is None or b.stage is None:
        result["reasons"] = sorted(set(reasons or ["stage unavailable"]))
        return result
    if policy:
        if any(k not in ("max_translation", "max_rotation_degrees") for k in policy) or any(not isinstance(v, (float, int)) or not math.isfinite(v) or v < 0 for v in policy.values()):
            raise ValueError("policy thresholds must be finite nonnegative numbers")
    before = {"A": {str(l.identifier): l.dirty for l in a.stage.GetUsedLayers()}, "B": {str(l.identifier): l.dirty for l in b.stage.GetUsedLayers()}}
    try:
        aa, bb = _observe(a), _observe(b)
        layer_a, layer_b = _layer_metadata(a), _layer_metadata(b)
        result["layer_changes"] = [{"layer": k, "before": layer_a.get(k), "after": layer_b.get(k)} for k in sorted(layer_a.keys() | layer_b.keys()) if layer_a.get(k) != layer_b.get(k)]
        for path in sorted(aa.keys() | bb.keys()):
            if any(path in records and not records[path]["active"] for records in (aa, bb)):
                reasons.append("inactive subtree limits comparison: " + path)
        metadata = {}
        for name, getter in (("meters_per_unit", UsdGeom.GetStageMetersPerUnit), ("up_axis", lambda s: str(UsdGeom.GetStageUpAxis(s))), ("time_codes_per_second", lambda s: s.GetTimeCodesPerSecond()), ("frames_per_second", lambda s: s.GetFramesPerSecond())):
            va, vb = getter(a.stage), getter(b.stage)
            if va != vb:
                reasons.append("stage metadata mismatch: " + name)
            metadata[name] = {"before": va, "after": vb}
        result["stage_metadata"] = metadata
        for path in sorted(aa.keys() | bb.keys()):
            av, bv = aa.get(path), bb.get(path)
            if av is None or bv is None:
                hidden = _hidden(path, aa if av is None else bb)
                result["changes"].append({"path": path, "kind": "unobserved" if hidden else ("added" if av is None else "removed"),
                                          "fields": {}, "reason": "inactive ancestor" if hidden else "composed path existence", "provenance": "unknown" if hidden else "composition"})
                if hidden:
                    reasons.append("inactive subtree limits comparison: " + path)
                continue
            fields = {}
            for name in ("active", "type", "visibility", "attributes", "attribute_types", "local", "world", "reset"):
                if not same(av[name], bv[name]):
                    fields[name] = {"before": av[name], "after": bv[name]}
            authored = {k: {"before": av["authored"].get(k), "after": bv["authored"].get(k)} for k in sorted(av["authored"].keys() | bv["authored"].keys()) if av["authored"].get(k) != bv["authored"].get(k)}
            if not fields and not authored:
                continue
            provenance = "local" if "local" in fields else "authored-only" if not fields else "effective"
            ancestor = Sdf.Path(path).GetParentPath()
            parent = None
            if "world" in fields and not bv["reset"]:
                while ancestor != Sdf.Path.absoluteRootPath:
                    ap = str(ancestor)
                    if ap in aa and ap in bb and not same(aa[ap]["local"], bb[ap]["local"]):
                        parent = ap
                        break
                    if ap in bb and bb[ap]["reset"]:
                        break
                    ancestor = ancestor.GetParentPath()
                if parent:
                    provenance = "local-and-parent" if "local" in fields else "parent-propagated"
            record = {"path": path, "kind": "modified", "fields": fields, "authored": authored, "provenance": provenance}
            if parent:
                record["parent_cause"] = parent
            if "world" in fields:
                record["world_delta"] = rigid_delta(av["world"], bv["world"])
            if "local" in fields:
                record["local_delta"] = rigid_delta(av["local"], bv["local"])
            result["changes"].append(record)
            if policy and "world" in fields:
                delta = record["world_delta"]
                verdict = {"path": path, "status": "unknown", "scope": "world rigid pose"}
                if delta["status"] == "known" and not reasons:
                    violations = []
                    if delta["translation_stage_units"] > policy.get("max_translation", float("inf")):
                        violations.append("translation exceeds threshold in stage units")
                    if delta["rotation_degrees"] > policy.get("max_rotation_degrees", float("inf")):
                        violations.append("rotation exceeds threshold")
                    verdict.update(status="fail" if violations else "pass", violations=violations)
                else:
                    verdict["reason"] = delta.get("reason", "incomplete evidence")
                result["policy"].append(verdict)
        groups = {}
        for change in result["changes"]:
            if change.get("parent_cause"):
                groups.setdefault(change["parent_cause"], []).append(change["path"])
        result["parent_groups"] = [{"parent": p, "affected": paths} for p, paths in sorted(groups.items())]
    except Exception:
        reasons.append("unsupported or unreadable scene data")
    for label, snapshot in (("A", a), ("B", b)):
        reasons.extend(label + ": " + x for x in verify(snapshot))
        after = {str(l.identifier): l.dirty for l in snapshot.stage.GetUsedLayers()}
        if after != before[label]:
            reasons.append(label + ": layer dirty state changed")
    result["reasons"] = sorted(set(reasons))
    result["status"] = "unknown" if reasons else "changed" if result["changes"] or result["layer_changes"] else "equal"
    if reasons:
        for verdict in result["policy"]:
            verdict.update(status="unknown", reason="comparison evidence incomplete")
    return result
