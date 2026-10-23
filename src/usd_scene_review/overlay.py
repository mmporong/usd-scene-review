"""Snapshot bounds for UI-scene drawing only; never creates USD display prims."""
from .display import COLORS,outline_points,world_bounds
from .measurements import detail_rows,motion_label
from .snapshot import verify
from .transform_analysis import coordinates
from dataclasses import dataclass
import hashlib
from pathlib import Path
from .snapshot import canonical,digest


@dataclass(frozen=True)
class ComparisonReceipt:
    """Pins an already computed UI report; holds no stages/native resources.

    Capture only after compare and its before/after manifest checks complete.
    This never replaces load_snapshot/verify for current file/resolver integrity.
    """
    paths: tuple
    manifests: tuple
    report_digest: str

    @classmethod
    def capture(cls,paths,report,expected_hashes):
        names=tuple(str(Path(paths[side]).resolve()) for side in ('A','B'))
        hashes=tuple(digest(Path(name)) for name in names)
        if hashes!=tuple(expected_hashes[side] for side in ('A','B')):
            raise ValueError('Manifests changed before report receipt')
        return cls(names,hashes,hashlib.sha256(canonical(report).encode('utf-8')).hexdigest())

    def matches(self,paths,report):
        try:
            names=tuple(str(Path(paths[side]).resolve()) for side in ('A','B'))
            return (names==self.paths and tuple(digest(Path(name)) for name in names)==self.manifests
                and hashlib.sha256(canonical(report).encode('utf-8')).hexdigest()==self.report_digest)
        except (OSError,ValueError,TypeError,KeyError):return False


def validate_report_reference(paths,report,receipt=None):
    if receipt is None:
        from .compare import compare
        valid=compare(paths['A'],paths['B'],analysis_config=report['analysis_config'],policy=report['policy_config'])==report
    else:valid=isinstance(receipt,ComparisonReceipt) and receipt.matches(paths,report)
    if not valid:raise ValueError('Inputs or report changed; compare again before overlay')


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
