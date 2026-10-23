"""Bounded broad-phase candidates from static geometry points, not authored extents.

This module deliberately has no dependency on comparison, display or measurements.
Control-point AABBs are conservative candidates, never collision/clearance verdicts.
"""
from collections import Counter
import hashlib
import json
import math
from pxr import Gf, Sdf, Usd, UsdGeom
from .analysis_config import normalize
from .transform_analysis import coordinates, finite_affine


def union_bounds(bounds):
    values = [v for v in bounds if v is not None]
    if not values:
        return None
    return [[min(v[0][i] for v in values) for i in range(3)],
            [max(v[1][i] for v in values) for i in range(3)]]


def _static_reason(prim):
    current = prim
    while current and not current.IsPseudoRoot():
        if not current.IsActive():
            return 'inactive-ancestor'
        if not current.IsLoaded():
            return 'unloaded-ancestor'
        if current.IsInstance() or current.IsInstanceProxy():
            return 'instancing-unsupported'
        if any(a.GetNumTimeSamples() for a in current.GetAttributes()):
            return 'animated-geometry-or-ancestor'
        if (any('Skel' in str(s) or 'Deform' in str(s) for s in current.GetAppliedSchemas())
                or any('skel:' in p.GetName().lower() or 'deform' in p.GetName().lower()
                       for p in current.GetProperties())):
            return 'skeletal-deformation-unsupported'
        current = current.GetParent()
    return None


def _points(prim, time, cfg):
    if prim.IsA(UsdGeom.Cube):
        size = UsdGeom.Cube(prim).GetSizeAttr().Get(time)
        if size is None or not math.isfinite(size) or size <= 0:
            raise ValueError('invalid-cube-size')
        h = size / 2
        return [Gf.Vec3d(x*h, y*h, z*h) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    mesh = UsdGeom.Mesh(prim)
    points = mesh.GetPointsAttr().Get(time)
    if points is None or len(points) == 0:
        raise ValueError('missing-mesh-points')
    if len(points) > cfg['max_points_per_geometry']:
        raise ValueError('budget-points-per-geometry')
    counts, indices = mesh.GetFaceVertexCountsAttr().Get(time), mesh.GetFaceVertexIndicesAttr().Get(time)
    if counts is None or indices is None or len(counts) == 0:
        raise ValueError('missing-mesh-topology')
    if len(indices) > cfg['max_face_vertices_per_geometry'] or len(counts) > cfg['max_face_vertices_per_geometry']:
        raise ValueError('budget-face-vertices-per-geometry')
    if any(n < 3 for n in counts) or sum(counts) != len(indices):
        raise ValueError('invalid-mesh-topology')
    holes = set(mesh.GetHoleIndicesAttr().Get(time) or [])
    if any(h < 0 or h >= len(counts) for h in holes):
        raise ValueError('invalid-mesh-holes')
    used, offset = set(), 0
    for face, count in enumerate(counts):
        face_indices = indices[offset:offset+count]
        if any(i < 0 or i >= len(points) for i in face_indices):
            raise ValueError('invalid-mesh-indices')
        if face not in holes:
            used.update(face_indices)
        offset += count
    if not used:
        raise ValueError('no-nonhole-mesh-faces')
    return [Gf.Vec3d(points[i]) for i in sorted(used)]


def has_displacement(prim, max_subsets):
    from pxr import UsdShade
    targets = [prim]
    for child in prim.GetChildren():
        if child.IsA(UsdGeom.Subset):
            if len(targets) > max_subsets:
                raise ValueError('budget-material-subsets')
            targets.append(child)
    for target in targets:
        for purpose in ('', 'full', 'preview'):
            material, _ = UsdShade.MaterialBindingAPI(target).ComputeBoundMaterial(materialPurpose=purpose)
            if material and any(out.HasConnectedSource() for out in UsdShade.Material(material).GetDisplacementOutputs()):
                return True
    return False


def _scan(snapshot, config):
    cfg = config['overlap']
    stage = snapshot.stage
    sample = snapshot.manifest['config']['time']
    time = Usd.TimeCode.Default() if sample == 'default' else Usd.TimeCode(float(sample))
    cache = UsdGeom.XformCache(time)
    units = UsdGeom.GetStageMetersPerUnit(stage)
    records, blocked, reasons, observed_paths = {}, {}, Counter(), []
    scanned = total_points = targets = 0
    partial = False
    for prim in stage.TraverseAll():
        scanned += 1
        if scanned > cfg['max_prims']:
            scanned -= 1
            reasons['budget-prims'] += 1
            partial = True
            break
        path = str(prim.GetPath())
        observed_paths.append(path)
        reason = _static_reason(prim)
        if reason:
            blocked[path] = reason
        if not prim.IsA(UsdGeom.Gprim):
            continue
        targets += 1
        if targets > cfg['max_geometry']:
            reasons['budget-geometry'] += 1
            partial = True
            # No unbounded tail traversal: missing paths must be unknown below.
            break
        item = {'status': 'unknown', 'reason': reason, 'type': prim.GetTypeName(),
                'purpose': str(UsdGeom.Imageable(prim).ComputePurpose())}
        records[path] = item
        try:
            if reason:
                raise ValueError(reason)
            if not (prim.IsA(UsdGeom.Cube) or prim.IsA(UsdGeom.Mesh)):
                raise ValueError('unsupported-geometry-type')
            if UsdGeom.Imageable(prim).ComputeVisibility(time) == UsdGeom.Tokens.invisible:
                raise ValueError('hidden-geometry')
            if item['purpose'] not in cfg['purposes']:
                raise ValueError('excluded-purpose')
            # Shader displacement and skeletal/binding-driven deformation are not sampled.
            if prim.GetRelationship('skel:skeleton') or prim.GetAttribute('primvars:skel:jointIndices'):
                raise ValueError('skeletal-deformation-unsupported')
            if has_displacement(prim, cfg['max_prims']):
                raise ValueError('shader-displacement-unsupported')
            if not math.isfinite(units) or units <= 0:
                raise ValueError('invalid-stage-units')
            points = _points(prim, time, cfg)
            if len(points) > cfg['max_points_per_geometry']:
                raise ValueError('budget-points-per-geometry')
            if total_points + len(points) > cfg['max_total_points']:
                raise ValueError('budget-total-points')
            total_points += len(points)
            matrix = cache.GetLocalToWorldTransform(prim)
            if not finite_affine([list(row) for row in matrix], config['transform']['affine_tolerance']):
                raise ValueError('nonfinite-or-nonaffine-world-matrix')
            world = [matrix.Transform(p) for p in points]
            if not all(math.isfinite(v) for p in world for v in p):
                raise ValueError('nonfinite-world-points')
            bounds = [[min(p[i] for p in world) for i in range(3)],
                      [max(p[i] for p in world) for i in range(3)]]
            meters = [[v*units for v in row] for row in bounds]
            if not all(math.isfinite(v) for row in meters for v in row):
                raise ValueError('nonfinite-meter-bounds')
            item.update(status='known', reason=None, bounds_stage=bounds,
                        bounds_m=meters, point_count=len(points))
        except ValueError as exc:
            item['reason'] = str(exc)
            reasons[str(exc)] += 1
            partial |= str(exc).startswith('budget-')
        except Exception:
            item['reason'] = 'unreadable-or-unsupported-geometry'
            reasons[item['reason']] += 1
    return {'records': records, 'blocked': blocked, 'observed_paths': set(observed_paths), 'coverage': {
        'status': 'partial' if partial else 'complete', 'scanned_prims': scanned,
        'geometry_examined': len(records), 'known_bounds': sum(v['status'] == 'known' for v in records.values()),
        'points_transformed': total_points, 'exclusions': dict(sorted(reasons.items()))}}


def _object(scan, path):
    if path in scan['records']:
        return scan['records'][path]
    if scan['coverage']['status'] == 'partial':
        return {'status': 'unknown', 'reason': 'incomplete-scan'}
    if path in scan['observed_paths']:
        return {'status': 'unknown', 'reason': 'existing-nongeometry-path'}
    ancestor = Sdf.Path(path)
    while ancestor != Sdf.Path.absoluteRootPath:
        if str(ancestor) in scan['blocked']:
            return {'status': 'unknown', 'reason': scan['blocked'][str(ancestor)]}
        ancestor = ancestor.GetParentPath()
    return {'status': 'missing', 'reason': 'no-supported-geometry-at-path'}


def relation(objects, tolerance):
    if any(v['status'] == 'unknown' for v in objects):
        return {'status': 'unknown', 'reason': '; '.join(sorted(set(v['reason'] for v in objects if v['status'] == 'unknown')))}
    if any(v['status'] == 'missing' for v in objects):
        return {'status': 'missing', 'reason': 'geometry-absent'}
    a, b = [v['bounds_m'] for v in objects]
    tol = max(tolerance, 8*max(math.ulp(v) for bounds in (a, b) for row in bounds for v in row))
    depths = [min(a[1][i], b[1][i])-max(a[0][i], b[0][i]) for i in range(3)]
    if not math.isfinite(tol) or not all(math.isfinite(v) for v in depths):
        return {'status': 'unknown', 'reason': 'numeric-range-exceeded'}
    state = 'disjoint' if any(d < -tol for d in depths) else 'overlap' if all(d > tol for d in depths) else 'boundary'
    return {'status': state, 'depths_m': depths, 'tolerance_m': tol}


def _classification(a, b):
    return {('disjoint', 'overlap'): 'newly-introduced-aabb-overlap',
            ('overlap', 'overlap'): 'existing-aabb-overlap',
            ('overlap', 'disjoint'): 'resolved-aabb-candidate',
            ('boundary', 'overlap'): 'boundary-to-overlap',
            ('missing', 'overlap'): 'added-geometry-overlap',
            ('unknown', 'overlap'): 'baseline-unknown',
            ('overlap', 'unknown'): 'after-unknown',
            ('overlap', 'missing'): 'removed-geometry',
            ('overlap', 'boundary'): 'overlap-to-boundary'}.get((a, b), a+'-to-'+b)


def analyze_overlaps(a, b, metadata, config=None):
    config = normalize(config)
    cfg = config['overlap']
    scans = [_scan(snapshot, config) for snapshot in (a, b)]
    paths = sorted(set(scans[0]['records']) | set(scans[1]['records']))
    pairs, counts, excluded = [], Counter(), Counter()
    checked = 0
    partial = any(s['coverage']['status'] == 'partial' for s in scans)
    coordinate = coordinates(metadata)
    stop = False
    for i, first in enumerate(paths):
        if stop:
            break
        for second in paths[i+1:]:
            if checked >= cfg['max_pairs']:
                partial = stop = True
                excluded['budget-pairs'] += 1
                break
            checked += 1
            if Sdf.Path(second).HasPrefix(Sdf.Path(first)) or Sdf.Path(first).HasPrefix(Sdf.Path(second)):
                excluded['ancestor-descendant-geometry-pair'] += 1
                continue
            objects = [[_object(scan, p) for p in (first, second)] for scan in scans]
            relations = [relation(v, cfg['tolerance_m']) for v in objects]
            states = [r['status'] for r in relations]
            kind = _classification(*states) if coordinate['status'] == 'known' else 'coordinate-metadata-unknown'
            counts[kind] += 1
            if not any(s in ('overlap', 'boundary') for s in states):
                continue
            if len(pairs) >= cfg['max_records']:
                partial = True
                excluded['budget-records'] += 1
                continue
            identity = json.dumps({'paths': [first, second], 'config': config}, sort_keys=True, separators=(',', ':'))
            pairs.append({'id': hashlib.sha256(identity.encode()).hexdigest(), 'paths': [first, second],
                          'classification': kind, 'before': relations[0], 'after': relations[1],
                          'objects': {'before': objects[0], 'after': objects[1]},
                          'focus_bounds_stage': union_bounds([v.get('bounds_stage') for side in objects for v in side])
                          if coordinate['status'] == 'known' and all(v['status'] == 'known' for side in objects for v in side) else None})
    return {'version': config['version'], 'method': 'static Cube vertices / Mesh nonhole face control points transformed to world AABBs',
            'meaning': 'broad-phase candidates only; not collision or clearance confirmation',
            'scope': 'visible active static Cube/Mesh; no aggregate bounds or authored extents',
            'config': cfg, 'coordinates': coordinate,
            'coverage': {'status': 'partial' if partial else 'complete', 'snapshots': {
                'before': scans[0]['coverage'], 'after': scans[1]['coverage']},
                'eligible_paths': len(paths), 'pairs_examined': checked,
                'classifications': dict(sorted(counts.items())), 'exclusions': dict(sorted(excluded.items()))},
            'pairs': pairs}


def pair_by_id(report, pair_id):
    pair = next((p for p in report.get('overlap_analysis', {}).get('pairs', []) if p['id'] == pair_id), None)
    if pair is None:
        raise ValueError('pair ID absent from recomputed analysis')
    return pair


def pair_rows(report, pair):
    return [('AABB pair', ' / '.join(pair['paths'])), ('Classification', pair['classification']),
            ('A / B relation', pair['before']['status']+' / '+pair['after']['status']),
            ('Tolerance (m)', format(report['analysis_config']['overlap']['tolerance_m'], '.9g')),
            ('Analysis coverage', report['overlap_analysis']['coverage']['status']),
            ('Collision / clearance', 'unknown; AABB candidate only')]
