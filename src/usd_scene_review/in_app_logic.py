"""Pure USD selection/camera rules shared by in-app UI and CPU regression."""
from pxr import Sdf, Usd, UsdGeom, UsdLux
from .display import camera_spec, world_bounds
from .overlap_analysis import pair_by_id
from .transform_analysis import coordinates


def focus_plan(report, snapshots, selected=None, pair_id=None):
    if coordinates(report.get('stage_metadata', {}))['status'] != 'known':
        raise ValueError('Matching valid stage units and up axes are required')
    if pair_id is not None:
        pair=pair_by_id(report,pair_id)
        if pair['focus_bounds_stage'] is None:
            raise ValueError('Pair has unknown bounds; no fabricated focus')
        bounds={s:pair['focus_bounds_stage'] for s in ('A','B')}
        paths=list(pair['paths'])
    else:
        if selected is not None and not any(c['path']==selected for c in report['changes']):
            raise ValueError('Selection is absent from this comparison')
        paths=[selected] if selected else []
        bounds={s:world_bounds(snapshot,selected or '/') for s,snapshot in snapshots.items()}
    spec=camera_spec(bounds,report['stage_metadata']['up_axis']['before'])
    existence={s:{p:bool(snapshot.stage.GetPrimAtPath(p)) for p in paths} for s,snapshot in snapshots.items()}
    return dict(paths=paths,bounds=bounds,camera=spec,exists=existence,pair_id=pair_id)


def copy_review_camera(source_stage, source_path, target_stage, target_path, roots):
    """Never point this helper at a source camera, even if its layer is editable."""
    for stage,path,root in zip((source_stage,target_stage),(source_path,target_path),roots):
        if (not Sdf.Path(path).HasPrefix(Sdf.Path(root)) or Sdf.Path(path)==Sdf.Path(root)
                or not stage.GetSessionLayer().anonymous
                or stage.GetEditTarget().GetLayer()!=stage.GetSessionLayer()):
            raise ValueError('Camera synchronization requires owned anonymous review cameras')
    source=UsdGeom.Camera(source_stage.GetPrimAtPath(source_path))
    target=UsdGeom.Camera(target_stage.GetPrimAtPath(target_path))
    if not source or not target:raise ValueError('Review camera unavailable')
    camera=source.GetCamera(Usd.TimeCode.Default())
    with Usd.EditContext(target_stage,target_stage.GetSessionLayer()):
        target.SetFromCamera(camera,Usd.TimeCode.Default())


def pair_light_mode(snapshots):
    counts={s:sum(bool(UsdLux.LightAPI(p)) for p in item.stage.Traverse()) for s,item in snapshots.items()}
    return {'counts':counts,'fallback_both':not any(counts.values()),
            'label':'Equal fallback domes: neither revision has lights' if not any(counts.values())
                    else 'Original A/B lights retained, including actual lighting differences'}
