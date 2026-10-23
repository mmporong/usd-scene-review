"""Versioned, deterministic auxiliary-analysis contract, independent of compare."""
import copy
import math

DEFAULT = {
    'version': 1,
    'transform': {'affine_tolerance': 1e-8, 'orthogonality_tolerance': 1e-7,
                  'min_axis': 1e-12, 'max_condition': 1e8},
    'overlap': {'tolerance_m': 1e-6, 'purposes': ['default', 'render', 'proxy'],
                'max_prims': 20000, 'max_face_vertices_per_geometry': 1000000,
                'max_geometry': 2048, 'max_points_per_geometry': 200000,
                'max_total_points': 1000000, 'max_pairs': 1000000,
                'max_records': 20000},
}


def normalize(config=None):
    value = copy.deepcopy(DEFAULT if config is None else config)
    if (not isinstance(value, dict) or set(value) != set(DEFAULT)
            or type(value['version']) is not int or value['version'] != 1):
        raise ValueError('Unsupported analysis configuration/version')
    for section in ('transform', 'overlap'):
        if not isinstance(value[section], dict) or set(value[section]) != set(DEFAULT[section]):
            raise ValueError('Incomplete analysis configuration: ' + section)
        for key, item in value[section].items():
            if key == 'purposes':
                if (not isinstance(item, list) or not item
                        or any(type(p) is not str or p not in ('default', 'render', 'proxy') for p in item)
                        or len(set(item)) != len(item)):
                    raise ValueError('Invalid analysis purposes')
                value[section][key] = sorted(item)
            elif key.startswith('max_') and key != 'max_condition':
                if type(item) is not int or not 1 <= item <= 2000000:
                    raise ValueError('Invalid bounded analysis budget: ' + key)
            elif type(item) not in (int, float) or not math.isfinite(item) or item <= 0:
                raise ValueError('Invalid finite positive analysis setting: ' + key)
    if value['transform']['max_condition'] < 1:
        raise ValueError('Analysis condition limit must be at least one')
    return value
