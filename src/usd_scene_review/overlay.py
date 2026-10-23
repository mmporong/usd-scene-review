"""Snapshot bounds for UI-scene drawing only; never creates USD display prims."""
from .display import COLORS,outline_points,world_bounds
from .measurements import detail_rows,motion_label
from .snapshot import verify
from .transform_analysis import coordinates


def bounds_plan(report,snapshots,selected):
    if coordinates(report.get('stage_metadata',{}))['status']!='known':
        raise ValueError('Matching snapshot units and up axis are required for bounds overlay')
    if any(verify(snapshot) for snapshot in snapshots.values()):
        raise ValueError('Snapshot changed or incomplete; compare again before overlay')
    result={'path':selected,'boxes':[],'presence':{},'rows':[],
            'title':'SNAPSHOT WORLD BOUNDS ONLY | A blue dashed BEFORE / B orange solid AFTER',
            'motion':'Select a changed prim; no camera or selection is moved.'}
    if selected is None:return result
    change=next((change for change in report.get('changes',[]) if change['path']==selected),None)
    if change is None:raise ValueError('Selected path is absent from this comparison')
    for side in ('A','B'):
        prim=snapshots[side].stage.GetPrimAtPath(selected)
        bounds=world_bounds(snapshots[side],selected)
        result['presence'][side]='absent' if not prim else ('visible bounds' if bounds else 'hidden/inactive/no finite bounds')
        if bounds:
            result['boxes'].append({'side':side,'bounds':bounds,'points':outline_points(bounds,side=='A'),
                                    'color':(*COLORS[side],1.0),'dashed':side=='A'})
    result['motion']=motion_label(change)
    result['rows']=detail_rows(report,change)
    return result


def overlay_text(plan):
    lines=[plan['title'],plan['path'] or 'No changed prim selected',plan['motion']]
    if plan['presence']:
        lines.append('A: '+plan['presence']['A']+' | B: '+plan['presence']['B'])
    for name,before,after,delta in plan['rows']:
        if name in ('World position [stage u]','World effective q'):
            lines.append(name+': A '+before+' | B '+after+' | '+delta)
    lines.append('Display AABBs, not mesh/green ghost, collision or current-stage verification.')
    return '\n'.join(lines)
