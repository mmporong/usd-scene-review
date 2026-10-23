"""Bounds-only UI callback treatment; never quits or edits the working stage."""
import hashlib
import json
from pathlib import Path
import sys


def check_names():
    names={'fresh extracted engine','persistent exclusion solve','navigation exclusions retained','navigation exclusions after disable','Full A/B guard retained','comparison callback completed',
           'extension disabled','working state preserved','inputs preserved'}
    for cycle in range(2):
        names.update(label+str(cycle) for label in ('show empty ','select before/after ',
            'toggle off ','toggle on ','close review ','subscriptions released ','cycle preservation '))
    return names


def navigation_exclusions_retained(manager):
    return (not manager.is_extension_enabled('omni.anim.navigation.core')
        and not manager.is_extension_enabled('omni.anim.navigation.recast')
        and manager.is_extension_enabled('omni.anim.navigation.schema'))


def persist_owned_exclusions(manager,profile):
    """Preflight only: no enable/unload; called only by admitted owned treatment."""
    excluded=['omni.anim.navigation.recast','omni.anim.navigation.core']
    if profile.get('variant')!='no-navigation' or profile.get('exclusions')!=excluded:
        raise ValueError('Only the pinned owned reduced exclusion set is allowed')
    if not navigation_exclusions_retained(manager):
        raise ValueError('Navigation must already be excluded; never force unload')
    if not manager.is_extension_enabled('isaacsim.exp.full') or manager.is_extension_enabled('mmporong.scene.review'):
        raise ValueError('Owned Full-derived baseline required before treatment')
    manager.set_extensions_excluded(excluded)
    ok,solution,_=manager.solve_extensions(['isaacsim.exp.full','mmporong.scene.review'],
        add_enabled=True,return_only_disabled=False)
    # Installed 4.5 Extensions UI reads ext['id']; its stub describes strings.
    # Keep only validated IDs rather than serializing SDK records/private paths.
    ids=[]
    for value in solution:
        identifier=value if isinstance(value,str) else value.get('id') if isinstance(value,dict) else None
        if not isinstance(identifier,str) or not identifier or '/' in identifier or '\\' in identifier:
            raise ValueError('Unexpected excluded solve item; review will not be enabled')
        ids.append(identifier)
    def has(name):return any(value==name or value.startswith(name+'-') for value in ids)
    if (not ok or any(has(name) for name in excluded)
            or not all(has(name) for name in ('isaacsim.exp.full','mmporong.scene.review','omni.anim.navigation.schema'))):
        raise ValueError('Excluded dependency solve failed; review will not be enabled')
    return {'solver_success':True,'excluded':excluded,'solution':ids,
            'navigation_absent':True,'schema_retained':True}


def disable_review(manager,resources_remaining):
    # Kit clears the instance __dict__ after on_shutdown. Pass pre-unload values,
    # never read the unloaded instance to build a receipt.
    manager.set_extension_enabled_immediate('mmporong.scene.review',False)
    return {'owned_resources_remaining':resources_remaining,
            'extension_disabled':not manager.is_extension_enabled('mmporong.scene.review')}


def prepare(root,fixture_data):
    """Run in CPU launcher before Kit starts; all authored data is disposable."""
    from pxr import Usd,UsdGeom
    from usd_scene_review import create_snapshot
    root=Path(root);paths={}
    for side in ('A','B'):
        folder=root/('bounds-source-'+side);folder.mkdir()
        source=folder/'scene.usda';source.write_bytes(fixture_data)
        if side=='B':
            stage=Usd.Stage.Open(str(source))
            UsdGeom.Xformable(stage.GetPrimAtPath('/World/Item')).AddTranslateOp().Set((.4,0,0))
            stage.GetRootLayer().Save();stage=None
        paths[side]=str(create_snapshot(source,root/('bounds-'+side)))
    (root/'bounds-inputs.json').write_text(json.dumps(paths))


async def evaluate(probe,root):
    import omni.kit.app
    import omni.timeline
    import omni.usd
    from omni.kit.viewport.utility import get_active_viewport_window
    from omni.kit.widget.viewport import ViewportWidget
    root=Path(root);app=omni.kit.app.get_app();ctx=omni.usd.get_context()
    api=get_active_viewport_window().viewport_api
    result={'status':'running','kind':'stage-free bounds; UI callbacks, not mouse input','checks':[]}
    def check(name,passed):
        result['checks'].append({'name':name,'passed':bool(passed)})
        probe.result['candidate']=result;probe.write()
        if not passed:raise RuntimeError('Bounds treatment: '+name)
    async def updates(n=8):
        for _ in range(n):await app.next_update_async()
    def state():
        stage=ctx.get_stage()
        return {'root':stage.GetRootLayer().ExportToString(),'session':stage.GetSessionLayer().ExportToString(),
            'stage':stage.GetRootLayer().identifier,'edit':stage.GetEditTarget().GetLayer().identifier,
            'root_dirty':stage.GetRootLayer().dirty,'session_dirty':stage.GetSessionLayer().dirty,
            'pending':ctx.has_pending_edit(),'selection':list(ctx.get_selection().get_selected_prim_paths()),
            'view':str(api.view),'projection':str(api.projection),'camera':str(api.camera_path),
            'time':omni.timeline.get_timeline_interface().get_current_time(),
            'viewports':len(list(ViewportWidget.get_instances()))}
    def hashes():
        return {str(path.relative_to(root)):hashlib.sha256(path.read_bytes()).hexdigest()
            for name in ('bounds-source-A','bounds-source-B','bounds-A','bounds-B')
            for path in (root/name).rglob('*') if path.is_file()}
    before=state();files=hashes();result['pending_before']=before['pending']
    if before['pending']:raise RuntimeError('Owned baseline already pending; no flag reset permitted')
    package=root/'exts/mmporong.scene.review'
    sys.path.insert(0,str(package/'python'))
    import usd_scene_review
    check('fresh extracted engine',Path(usd_scene_review.__file__).is_relative_to(package/'python'))
    manager=app.get_extension_manager();owner=held=None
    profile=json.loads((root/'shutdown-profile.json').read_text())
    result['activation_mode']='persistent-manager-exclusions-v1'
    result['exclusion_preflight']=persist_owned_exclusions(manager,profile)
    check('persistent exclusion solve',True)
    try:
        manager.set_extension_enabled_immediate('mmporong.scene.review',True);await updates()
        result['navigation_after_enable']={name:manager.is_extension_enabled('omni.anim.navigation.'+name) for name in ('core','recast','schema')}
        check('navigation exclusions retained',navigation_exclusions_retained(manager))
        from mmporong.scene.review.extension import get_active_extension
        owner=get_active_extension()
        check('Full A/B guard retained',owner is not None and owner._in_app_blocked)
        paths=json.loads((root/'bounds-inputs.json').read_text())
        for side in ('A','B'):owner._paths[side].set_value(paths[side])
        owner._compare() # Actual Compare button callback, including scheduler.
        if owner._task:await owner._task
        check('comparison callback completed',owner._report is not None and owner._report['status']!='unknown')
        changed=next(change for change in owner._report['changes'] if change['path']=='/World/Item')
        for cycle in range(2):
            owner._selected=None
            owner._show_bounds_overlay();await updates()
            check('show empty '+str(cycle),owner._bounds_overlay is not None and owner._bounds_overlay.line_count==0)
            owner._select(changed);await updates()
            check('select before/after '+str(cycle),owner._bounds_overlay.line_count==108 and '0.4' in owner._bounds_overlay.caption.text)
            owner._hide_bounds_overlay();await updates()
            check('toggle off '+str(cycle),owner._bounds_overlay is None)
            owner._show_bounds_overlay();await updates()
            check('toggle on '+str(cycle),owner._bounds_overlay is not None and owner._bounds_overlay.line_count==108)
            held=owner._bounds_overlay;owner._close_review();await updates()
            check('close review '+str(cycle),owner._bounds_overlay is None)
            check('subscriptions released '+str(cycle),held.scene_view is None and not held.subscriptions)
            check('cycle preservation '+str(cycle),state()==before)
    finally:
        resources_remaining=bool(owner and getattr(owner,'_bounds_overlay',None))
        owner=held=None
        unload=disable_review(manager,resources_remaining)
        await updates()
    check('extension disabled',unload['extension_disabled'])
    import ctypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetModuleHandleW.argtypes=[ctypes.c_wchar_p];kernel.GetModuleHandleW.restype=ctypes.c_void_p
    result['navigation_after_disable']={name:manager.is_extension_enabled('omni.anim.navigation.'+name) for name in ('core','recast','schema')}
    result['navigation_after_disable']['core_dll_loaded']=bool(kernel.GetModuleHandleW('omni.anim.navigation.core.plugin.dll'))
    check('navigation exclusions after disable',navigation_exclusions_retained(manager) and not result['navigation_after_disable']['core_dll_loaded'])
    result['pending_after']=ctx.has_pending_edit()
    result['working_stage_preserved']=state()==before
    result['owned_resources_remaining']=unload['owned_resources_remaining']
    check('working state preserved',result['working_stage_preserved'])
    check('inputs preserved',hashes()==files)
    if {row['name'] for row in result['checks']}!=check_names():raise RuntimeError('Incomplete bounds treatment')
    result['status']='passed';probe.result['candidate']=result;probe.write()
    return result
