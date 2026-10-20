"""Display observations. Policy remains defined solely by compare.rigid_delta."""
import math
from pxr import Gf
from .compare import EPS, rigid_delta


def affine(matrix):
    try:
        return (len(matrix) == 4 and all(len(row) == 4 for row in matrix)
                and all(isinstance(x, (int, float)) and math.isfinite(x) for row in matrix for x in row)
                and all(abs(matrix[i][3] - float(i == 3)) <= EPS for i in range(4)))
    except (TypeError, ValueError):
        return False


def axis_magnitudes(matrix):
    """Unsigned orthogonal basis lengths; never infer authored signed scale."""
    if not affine(matrix):
        return None
    rows = [r[:3] for r in matrix[:3]]
    lengths = [math.hypot(*row) for row in rows]
    if any(not math.isfinite(length) or length <= EPS for length in lengths):
        return None
    unit = [[x / lengths[i] for x in row] for i, row in enumerate(rows)]
    if any(abs(sum(unit[i][k]*unit[j][k] for k in range(3))) > EPS
           for i in range(3) for j in range(i)):
        return None
    determinant = (unit[0][0]*(unit[1][1]*unit[2][2]-unit[1][2]*unit[2][1])
                   - unit[0][1]*(unit[1][0]*unit[2][2]-unit[1][2]*unit[2][0])
                   + unit[0][2]*(unit[1][0]*unit[2][1]-unit[1][1]*unit[2][0]))
    return lengths if determinant > 0 else None


def quaternion(matrix):
    if not affine(matrix) or rigid_delta(matrix, matrix)['status'] != 'known':
        return None
    q = Gf.Matrix4d(*[x for row in matrix for x in row]).ExtractRotationQuat()
    values = [float(q.GetReal()), *[float(v) for v in q.GetImaginary()]]
    length = math.sqrt(sum(x*x for x in values))
    values = [x / length for x in values]
    # q and -q represent the same rotation. Stable sign, including pi rotations.
    sign = next((1 if x > 0 else -1 for x in values if abs(x) > 1e-12), 1)
    return [0.0 if abs(x) < 1e-12 else sign*x for x in values]


def motion_label(change):
    provenance = change.get('provenance')
    if provenance == 'parent-propagated':
        return 'ANCESTOR MOTION from ' + change.get('parent_cause', '?') + '; local transform unchanged'
    if provenance == 'local-and-parent':
        return 'DIRECT LOCAL + ANCESTOR MOTION from ' + change.get('parent_cause', '?')
    if provenance == 'local':
        return 'DIRECT LOCAL TRANSFORM; authored opinions are separate evidence'
    return {'authored-only': 'AUTHORED OPINIONS ONLY; effective pose unchanged',
            'composition': 'COMPOSITION / path existence',
            'unknown': 'INCOMPLETE EVIDENCE'}.get(provenance, 'EFFECTIVE STATE CHANGE')


def finite_vector(values):
    return values if values is not None and all(math.isfinite(x) for x in values) else None


def measurements(report, change):
    metadata = report.get('stage_metadata', {})
    units = metadata.get('meters_per_unit', {})
    valid_units = all(type(units.get(s)) in (int, float) and math.isfinite(units[s])
                      and units[s] > 0 for s in ('before', 'after'))
    coordinate_match = (valid_units and units['before'] == units['after']
                        and metadata.get('up_axis', {}).get('before') in ('Y', 'Z')
                        and metadata.get('up_axis', {}).get('before') == metadata.get('up_axis', {}).get('after'))
    observed = change.get('observed', {})
    result = {'units': units, 'coordinate_match': coordinate_match, 'spaces': {},
              'motion': motion_label(change), 'active': {}, 'visibility': {}}
    for key in ('active', 'visibility'):
        result[key] = {s: (observed.get(s) or {}).get(key) for s in ('before', 'after')}
    for space in ('local', 'world'):
        matrices = {s: (observed.get(s) or {}).get(space) if result['active'][s] is True else None
                    for s in ('before', 'after')}
        positions = {s: list(m[3][:3]) if affine(m) else None for s, m in matrices.items()}
        delta = ([positions['after'][i] - positions['before'][i] for i in range(3)]
                 if coordinate_match and all(p is not None for p in positions.values()) else None)
        delta = finite_vector(delta)
        rotations = {s: quaternion(m) for s, m in matrices.items()}
        angle = None
        if coordinate_match and all(q is not None for q in rotations.values()):
            # Preserve the engine's rigid-only verdict and shortest relative angle.
            angle = rigid_delta(matrices['before'], matrices['after'])['rotation_degrees']
        result['spaces'][space] = dict(
            translation=positions, delta=delta,
            meters={s: (finite_vector([x*units[s] for x in p]) if valid_units and p is not None else None)
                    for s, p in positions.items()},
            delta_meters=finite_vector([x*units['before'] for x in delta]) if delta is not None else None,
            axis_magnitudes={s: axis_magnitudes(m) for s, m in matrices.items()},
            quaternion=rotations, rotation_degrees=angle)
    return result


def number(value):
    return format(0.0 if abs(value) < 1e-12 else value, '.9g')


def vector(value):
    return '(' + ', '.join(number(x) for x in value) + ')' if value is not None else 'unavailable'


def detail_rows(report, change):
    data = measurements(report, change)
    rows = []
    for space in ('local', 'world'):
        r = data['spaces'][space]
        label = 'Local' if space == 'local' else 'World'
        rows.append((label+' position [stage u]', vector(r['translation']['before']),
                     vector(r['translation']['after']), vector(r['delta'])))
        if space == 'world':
            rows.append(('World position [m]', vector(r['meters']['before']),
                         vector(r['meters']['after']), vector(r['delta_meters'])))
        rows.append((label+' axis magnitudes', vector(r['axis_magnitudes']['before']),
                     vector(r['axis_magnitudes']['after']), 'unsigned; not signed scale'))
        rows.append((label+' rigid q (w,x,y,z)', vector(r['quaternion']['before']),
                     vector(r['quaternion']['after']),
                     (number(r['rotation_degrees'])+' deg shortest' if r['rotation_degrees'] is not None
                      else 'unknown: non-rigid / unavailable')))
    for key in ('active', 'visibility'):
        r = data[key]
        rows.append((key.title(), str(r['before']) if r['before'] is not None else 'unobserved', str(r['after']) if r['after'] is not None else 'unobserved',
                     'changed' if r['before'] != r['after'] else 'unchanged'))
    return rows
