"""Effective basis observations, never authored rotation or rigid policy verdicts.

USD uses row vectors: basis rows carry unsigned lengths and row 3 translation.
No imports from compare/measurements/ghost; auxiliary analysis cannot change policy.
"""
from collections import Counter
import math
from pxr import Gf
from .analysis_config import normalize


def _shape(matrix):
    try:
        return len(matrix) == 4 and all(len(row) == 4 for row in matrix)
    except TypeError:
        return False


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def finite_affine(matrix, tolerance=1e-8):
    return (_shape(matrix) and all(_finite(x) for row in matrix for x in row)
            and all(abs(matrix[i][3] - float(i == 3)) <= tolerance for i in range(4)))


def coordinates(metadata):
    units, axes = metadata.get('meters_per_unit', {}), metadata.get('up_axis', {})
    valid = {s: _finite(units.get(s)) and units[s] > 0 and axes.get(s) in ('Y', 'Z')
             for s in ('before', 'after')}
    match = (all(valid.values()) and units['before'] == units['after']
             and axes['before'] == axes['after'])
    return {'status': 'known' if match else 'unknown',
            'reason': None if match else 'invalid-or-mismatched-units-or-up-axis',
            'valid': valid}


def canonical_quaternion(values):
    length = math.hypot(*values)
    if not math.isfinite(length) or length == 0:
        return None
    q = [v / length for v in values]
    sign = next((1 if v > 0 else -1 for v in q if abs(v) > 1e-12), 1)
    return [0.0 if abs(v) < 1e-12 else sign * v for v in q]


def analyze(matrix, config=None):
    cfg = normalize(config)['transform']
    result = {'translation': {'status': 'unknown', 'value': None, 'reason': 'missing-matrix'},
              'orientation': {'status': 'unknown', 'quaternion': None, 'reason': 'missing-matrix',
                              'interpretation': 'scale-normalized effective orientation; not authored rotation'},
              'axis_magnitudes': None, 'basis_row_lengths': None}
    def fail(reason):
        result['orientation']['reason'] = reason
        return result
    if matrix is None:
        return result
    if not _shape(matrix):
        result['translation']['reason'] = 'invalid-matrix-shape'
        return fail('invalid-matrix-shape')
    if (not all(_finite(matrix[i][3]) for i in range(4))
            or any(abs(matrix[i][3] - float(i == 3)) > cfg['affine_tolerance'] for i in range(4))):
        result['translation']['reason'] = 'non-affine-matrix'
        return fail('non-affine-matrix')
    position = list(matrix[3][:3])
    result['translation'] = ({'status': 'known', 'value': position, 'reason': None}
                             if all(_finite(v) for v in position) else
                             {'status': 'unknown', 'value': None, 'reason': 'nonfinite-translation'})
    if not all(_finite(v) for row in matrix for v in row):
        return fail('nonfinite-or-nonnumeric-matrix')
    lengths = [math.hypot(*row[:3]) for row in matrix[:3]]
    if not all(math.isfinite(v) for v in lengths):
        return fail('nonfinite-basis-magnitude')
    result['basis_row_lengths'] = lengths
    if min(lengths) <= cfg['min_axis']:
        return fail('singular-or-near-zero-axis')
    if max(lengths) / min(lengths) > cfg['max_condition']:
        return fail('ill-conditioned-basis')
    rows = [[v / lengths[i] for v in matrix[i][:3]] for i in range(3)]
    if any(abs(sum(rows[i][k] * rows[j][k] for k in range(3))) > cfg['orthogonality_tolerance']
           for i in range(3) for j in range(i)):
        return fail('shear-or-nonorthogonal-basis')
    determinant = (rows[0][0]*(rows[1][1]*rows[2][2]-rows[1][2]*rows[2][1])
                   - rows[0][1]*(rows[1][0]*rows[2][2]-rows[1][2]*rows[2][0])
                   + rows[0][2]*(rows[1][0]*rows[2][1]-rows[1][1]*rows[2][0]))
    if determinant < 0:
        return fail('reflection')
    if abs(determinant - 1) > 4 * cfg['orthogonality_tolerance']:
        return fail('singular-or-invalid-normalized-basis')
    rotation = Gf.Matrix4d(*[rows[i][j] if i < 3 and j < 3 else float(i == j)
                             for i in range(4) for j in range(4)]).ExtractRotationQuat()
    q = canonical_quaternion([float(rotation.GetReal()), *map(float, rotation.GetImaginary())])
    result['axis_magnitudes'] = lengths
    result['orientation'].update(status='known', quaternion=q, reason=None)
    return result


def analyze_change(observed, metadata, config=None):
    config = normalize(config)
    frame = coordinates(metadata)
    result = {'version': config['version'], 'config': config, 'coordinates': frame, 'spaces': {}}
    for space in ('local', 'world'):
        sides = {s: analyze((observed.get(s) or {}).get(space)
                           if (observed.get(s) or {}).get('active') is True else None, config)
                 for s in ('before', 'after')}
        positions = [sides[s]['translation']['value'] for s in ('before', 'after')]
        translation = {'status': 'unknown', 'value': None, 'meters': None,
                       'reason': frame['reason'] or 'translation-unavailable'}
        rotation = {'status': 'unknown', 'degrees': None,
                    'reason': frame['reason'] or 'orientation-unavailable'}
        if frame['status'] == 'known':
            if all(p is not None for p in positions):
                delta = [b-a for a, b in zip(*positions)]
                meters = [v*metadata['meters_per_unit']['before'] for v in delta]
                if all(math.isfinite(v) for v in delta + meters):
                    translation.update(status='known', value=delta, meters=meters, reason=None)
                else:
                    translation['reason'] = 'nonfinite-translation-delta'
            q = [sides[s]['orientation']['quaternion'] for s in ('before', 'after')]
            if all(v is not None for v in q):
                dot = min(1.0, abs(sum(a*b for a, b in zip(*q))))
                angle = 2*math.degrees(math.acos(dot))
                rotation.update(status='known', degrees=0.0 if abs(1-dot) < 1e-15 else angle, reason=None)
            else:
                rotation['reason'] = '; '.join(s + ': ' + sides[s]['orientation']['reason']
                                               for s in ('before', 'after') if sides[s]['orientation']['status'] != 'known')
        result['spaces'][space] = {'before': sides['before'], 'after': sides['after'],
                                   'translation_delta': translation, 'orientation_delta': rotation}
    return result


def coverage(changes):
    result = {}
    for space in ('local', 'world'):
        counts = Counter()
        for change in changes:
            delta = change['transform_analysis']['spaces'][space]['orientation_delta']
            counts['known' if delta['status'] == 'known' else delta['reason']] += 1
        result[space] = dict(sorted(counts.items()))
    return result
