"""Compact presentation of evidence, without changing comparison semantics."""
from collections import Counter


def inherited_only(change):
    return (change.get('provenance') == 'parent-propagated'
            and set(change.get('fields', {})) == {'world'} and not change.get('authored'))


CHANGE_KINDS = ('all', 'modified', 'added', 'removed', 'unobserved')


def visible_changes(report, query='', include_inherited=False, kind='all'):
    if kind not in CHANGE_KINDS:
        raise ValueError('Unknown change type filter')
    query = query.casefold().strip()
    return [c for c in report.get('changes', [])
            if (include_inherited or not inherited_only(c))
            and (kind == 'all' or c.get('kind') == kind)
            and (not query or query in c.get('path', '').casefold())]


def adjacent_change(changes, selected_path, direction):
    """Navigate only visible evidence, without wrapping or mutating its order."""
    if direction not in (-1, 1):
        raise ValueError('Navigation direction must be -1 or 1')
    if not changes:
        return None
    index = next((i for i, c in enumerate(changes) if c['path'] == selected_path), None)
    if index is None:
        return changes[0 if direction == 1 else -1]
    target = index + direction
    return changes[target] if 0 <= target < len(changes) else None


def summary(report):
    changes = report.get('changes', [])
    inherited = sum(inherited_only(c) for c in changes)
    verdicts = Counter(v.get('status', 'unknown') for v in report.get('policy', []))
    lines = [f"{report.get('status', 'unknown')}: {len(changes)} changed prims; "
             f"{inherited} inherited-only; {len(report.get('parent_groups', []))} parent groups."]
    if verdicts:
        lines.append('Rigid policy: ' + ', '.join(f'{n} {s}' for s, n in sorted(verdicts.items())))
    if report.get('reasons'):
        lines.append('Incomplete evidence: ' + '; '.join(report['reasons']))
    lines.append('Expand inherited motion or search a prim path. Select a row for evidence; View A/B opens a separate window.')
    lines.append('Unknown scale/shear: rigid limits do not establish clearance. Clash is unavailable.')
    return '\n'.join(lines)


def details(change):
    import json
    hints = []
    if change.get('parent_cause'):
        hints.append('Parent motion: ' + change['parent_cause'])
    for name in ('world_delta', 'local_delta'):
        delta = change.get(name, {})
        if delta.get('status') == 'unknown':
            hints.append(name + ': ' + delta.get('reason', 'incomplete evidence')
                         + '. Inspect authored transforms; no rigid pass is implied.')
    if change.get('kind') == 'unobserved':
        hints.append('Inactive subtree: try the other revision. Hidden descendants are not proven removed.')
    return '\n'.join(hints) + '\n' + json.dumps(change, indent=2, ensure_ascii=False)
