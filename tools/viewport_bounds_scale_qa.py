"""Deterministic owned two-scale QA; metrics never enter semantic identities."""
import gc
import asyncio
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import time
import weakref

SCALES=(32,2048)
CYCLES=3


def check_names():
    names={'persistent exclusion solve','navigation exclusions retained','fresh extracted engine',
           'extension disabled','navigation exclusions after disable','pinned fixture epoch restored','inputs preserved'}
    for count in SCALES:
        names.update(name+str(count) for name in ('owned working geometry ','comparison ','case preservation '))
        for cycle in range(CYCLES):
            names.update(name+str(count)+'/'+str(cycle) for name in ('selection ','panel close/reopen ','resources cleared ','working state '))
    return names


def build_scale(root,count):
    from pxr import Usd,UsdGeom
    from usd_scene_review import create_snapshot
    if type(count) is not int or not 8<=count<=2048 or count%8:raise ValueError('Bounded multiple-of-eight fixture required')
    root=Path(root);root.mkdir();paths={};changed=set(range(0,count,count//8))
    for side in ('A','B'):
        source_folder=root/('source-'+side);source_folder.mkdir()
        source=source_folder/'scene.usda';stage=Usd.Stage.CreateNew(str(source))
        UsdGeom.SetStageMetersPerUnit(stage,1);UsdGeom.SetStageUpAxis(stage,'Z')
        UsdGeom.Xform.Define(stage,'/World')
        for index in range(count):
            cube=UsdGeom.Cube.Define(stage,'/World/Cell'+str(index).zfill(5));cube.CreateSizeAttr(.5)
            cube.AddTranslateOp().Set((2*(index%64)+(.125 if side=='B' and index in changed else 0),2*(index//64),.5))
        stage.GetRootLayer().Save();stage=None
        paths[side]=str(create_snapshot(source,root/side))
    working=root/'working.usda';working.write_bytes((root/'source-B/scene.usda').read_bytes())
    return {'count':count,'paths':paths,'working':str(working),'changed':len(changed)}


def prepare(root,fixture_data):
    root=Path(root)
    cases=[build_scale(root/('scale-'+str(count)),count) for count in SCALES]
    (root/'bounds-scales.json').write_text(json.dumps(cases))


def memory_bytes():
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in
            ('peak_working_set','working_set','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile','private')]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True);psapi=ctypes.WinDLL('psapi',use_last_error=True)
    kernel.GetCurrentProcess.restype=wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
    value=Counters();value.cb=ctypes.sizeof(value)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(value),value.cb):raise ctypes.WinError(ctypes.get_last_error())
    return {'working_set':value.working_set,'private':value.private}


def latency_summary(values):
    return {'samples':len(values),'min_ms':min(values),'median_ms':statistics.median(values),'max_ms':max(values)}


def metrics_complete(rows):
    if [row.get('count') for row in rows]!=list(SCALES):return False
    for row in rows:
        for key,length in (('selection_ms',12),('selection_to_two_frames_ms',12),('open_ms',3),('close_ms',3)):
            values=row.get(key,[])
            if len(values)!=length or any(type(value) not in (int,float) or not math.isfinite(value) or value<0 for value in values):return False
        cleanup=row.get('cleanup',[])
        if len(cleanup)!=CYCLES:return False
        for sample in cleanup:
            if (sample.get('owned_overlay_cleared') is not True or sample.get('live_tracked_scene_views')!=0
                    or sample.get('viewports')!=row.get('viewports_expected')):return False
            if any(type(sample.get('memory',{}).get(key)) is not int or sample['memory'][key]<=0 for key in ('working_set','private')):return False
    return True


async def evaluate(probe,root):
    import omni.kit.app
    import omni.usd
    import omni.timeline
    from omni.kit.viewport.utility import get_active_viewport_window
    from omni.kit.widget.viewport import ViewportWidget
    from pxr import UsdGeom
    from viewport_bounds_candidate import persist_owned_exclusions,navigation_exclusions_retained,disable_review
    root=Path(root);app=omni.kit.app.get_app();ctx=omni.usd.get_context();manager=app.get_extension_manager()
    result={'status':'running','kind':'two-scale owned stage QA','checks':[],'scales':[],
            'manual_mouse_tested':False,'activation_mode':'persistent-manager-exclusions-v1',
            'selection_metric':'synchronous actual UI callback wall time; excludes later frames',
            'settle_metric':'callback start to two rendered frames',
            'memory_metric':'own Windows process bytes; after 20 updates and explicit Python gc; not a leak verdict'}
    def check(name,passed):
        result['checks'].append({'name':name,'passed':bool(passed)});probe.result['candidate']=result;probe.write()
        if not passed:raise RuntimeError('Scale QA: '+name)
    async def updates(n=20):
        for _ in range(n):await app.next_update_async()
    def hashes():
        return {str(path.relative_to(root)):hashlib.sha256(path.read_bytes()).hexdigest()
            for count in SCALES for path in (root/('scale-'+str(count))).rglob('*') if path.is_file()}
    files=hashes();fixture=root/'shutdown-fixture.usda';fixture_hash=hashlib.sha256(fixture.read_bytes()).hexdigest()
    profile=json.loads((root/'shutdown-profile.json').read_text())
    result['exclusion_preflight']=persist_owned_exclusions(manager,profile);check('persistent exclusion solve',True)
    package=root/'exts/mmporong.scene.review';sys.path.insert(0,str(package/'python'))
    import usd_scene_review
    check('fresh extracted engine',Path(usd_scene_review.__file__).is_relative_to(package/'python'))
    owner=overlay=None
    try:
        manager.set_extension_enabled_immediate('mmporong.scene.review',True);await updates()
        check('navigation exclusions retained',navigation_exclusions_retained(manager))
        from mmporong.scene.review.extension import get_active_extension
        owner=get_active_extension()
        if owner is None or not owner._in_app_blocked:raise RuntimeError('Full guard not retained')
        cases=json.loads((root/'bounds-scales.json').read_text())
        if [case.get('count') for case in cases]!=list(SCALES):raise ValueError('Expected only the two owned QA scales')
        for case in cases:
            count=case['count'];working=(root/('scale-'+str(count))/'working.usda').resolve()
            if Path(case['working']).resolve()!=working:raise ValueError('Only owned generated working fixtures may open')
            opened=await ctx.open_stage_async(str(working));await updates(40)
            stage=ctx.get_stage();api=get_active_viewport_window().viewport_api
            check('owned working geometry '+str(count),bool(opened[0]) and sum(prim.IsA(UsdGeom.Cube) for prim in stage.Traverse())==count)
            def state():
                return {'root':stage.GetRootLayer().ExportToString(),'session':stage.GetSessionLayer().ExportToString(),
                    'same_stage':ctx.get_stage()==stage,'pending':ctx.has_pending_edit(),'root_dirty':stage.GetRootLayer().dirty,
                    'session_dirty':stage.GetSessionLayer().dirty,'edit':stage.GetEditTarget().GetLayer().identifier,
                    'selection':list(ctx.get_selection().get_selected_prim_paths()),'camera':str(api.camera_path),
                    'view':str(api.view),'projection':str(api.projection),'time':omni.timeline.get_timeline_interface().get_current_time()}
            before=state()
            if before['pending']:raise RuntimeError('Owned scale setup pending; no flag reset permitted')
            metrics={'count':count,'changes_expected':case['changed'],'memory_before_compare':memory_bytes(),
                     'selection_ms':[],'selection_to_two_frames_ms':[],'open_ms':[],'close_ms':[],'cleanup':[]}
            result['scales'].append(metrics)
            for side in ('A','B'):owner._paths[side].set_value(case['paths'][side])
            start=time.perf_counter();owner._compare()
            if owner._task:await owner._task
            metrics['compare_ms']=(time.perf_counter()-start)*1000
            check('comparison '+str(count),owner._report is not None and len(owner._report['changes'])==case['changed'])
            metrics['auxiliary_coverage']=owner._report.get('overlap_analysis',{}).get('coverage',{})
            changes=sorted(owner._report['changes'],key=lambda row:row['path'])
            targets=[changes[0],changes[len(changes)//2],changes[-1],changes[0]]
            weak_views=[];widget_count=len(list(ViewportWidget.get_instances()))
            metrics['viewports_expected']=widget_count
            for cycle in range(CYCLES):
                owner._window.visible=True;start=time.perf_counter();owner._show_bounds_overlay()
                metrics['open_ms'].append((time.perf_counter()-start)*1000)
                if owner._bounds_overlay is None:raise RuntimeError('Overlay failed to open')
                weak_views.append(weakref.ref(owner._bounds_overlay.scene_view))
                for change in targets:
                    start=time.perf_counter();owner._select(change)
                    metrics['selection_ms'].append((time.perf_counter()-start)*1000)
                    await asyncio.wait_for(api.wait_for_rendered_frames(2),20)
                    metrics['selection_to_two_frames_ms'].append((time.perf_counter()-start)*1000)
                check('selection '+str(count)+'/'+str(cycle),owner._bounds_overlay.line_count==108 and owner._bounds_overlay.last_plan['path']==targets[-1]['path'])
                owner._hide_bounds_overlay();owner._show_bounds_overlay()
                weak_views.append(weakref.ref(owner._bounds_overlay.scene_view))
                owner._window.visible=False;await updates(4)
                hidden=owner._bounds_overlay is None;owner._window.visible=True;owner._show_bounds_overlay()
                check('panel close/reopen '+str(count)+'/'+str(cycle),hidden and owner._bounds_overlay is not None)
                weak_views.append(weakref.ref(owner._bounds_overlay.scene_view))
                overlay=owner._bounds_overlay;start=time.perf_counter();owner._close_review()
                metrics['close_ms'].append((time.perf_counter()-start)*1000)
                clear=overlay.scene_view is None and not overlay.subscriptions and not overlay.snapshots
                overlay=None;await updates();gc.collect()
                metrics['cleanup'].append({'cycle':cycle,'memory':memory_bytes(),'live_tracked_scene_views':sum(ref() is not None for ref in weak_views),
                    'viewports':len(list(ViewportWidget.get_instances())),'owned_overlay_cleared':clear})
                check('resources cleared '+str(count)+'/'+str(cycle),clear and owner._bounds_overlay is None and len(list(ViewportWidget.get_instances()))==widget_count and not any(ref() is not None for ref in weak_views))
                check('working state '+str(count)+'/'+str(cycle),state()==before)
            metrics['selection_summary']=latency_summary(metrics['selection_ms'])
            metrics['settle_summary']=latency_summary(metrics['selection_to_two_frames_ms'])
            metrics['memory_cleanup_private_delta']=metrics['cleanup'][-1]['memory']['private']-metrics['cleanup'][0]['memory']['private']
            check('case preservation '+str(count),state()==before)
    finally:
        remaining=bool(owner and getattr(owner,'_bounds_overlay',None));owner=overlay=None
        unload=disable_review(manager,remaining);await updates()
    check('extension disabled',unload['extension_disabled'])
    check('navigation exclusions after disable',navigation_exclusions_retained(manager))
    restored=await ctx.open_stage_async(str(fixture));await updates(40)
    result['fixture_epoch_restored']=bool(restored[0]) and not ctx.has_pending_edit() and not ctx.get_stage().GetRootLayer().dirty and hashlib.sha256(fixture.read_bytes()).hexdigest()==fixture_hash
    check('pinned fixture epoch restored',result['fixture_epoch_restored'])
    check('inputs preserved',hashes()==files)
    result.update(working_stage_preserved=True,owned_resources_remaining=remaining,
                  pending_before=False,pending_after=ctx.has_pending_edit(),status='passed')
    if not metrics_complete(result['scales']):raise RuntimeError('Incomplete measured scale receipts')
    if {row['name'] for row in result['checks']}!=check_names():raise RuntimeError('Incomplete scale QA')
    probe.result['candidate']=result;probe.write();return result
