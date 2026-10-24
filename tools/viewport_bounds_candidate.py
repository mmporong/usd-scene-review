"""Bounds-only UI callback treatment; never quits or edits the working stage."""
import hashlib
import json
from pathlib import Path
import sys


def check_names(faces=False):
    names={'fresh extracted engine','persistent exclusion solve','navigation exclusions retained','navigation exclusions after disable','Full A/B guard retained','comparison callback completed',
           'extension disabled','working state preserved','inputs preserved'}
    for cycle in range(2):
        names.update(label+str(cycle) for label in ('show empty ','select before/after ',
            'toggle off ','toggle on ','close review ','subscriptions released ','cycle preservation '))
        if faces:names.update(label+str(cycle) for label in ('cube UI faces ','triangle UI faces ','subdivision refused ','removed UI faces ','face toggle clears '))
        if faces:names.update(label+str(cycle) for label in ('quad UI faces ','concave and hole UI faces ','nonplanar refused ','reflected parent UI faces '))
        if faces:names.update(label+str(cycle) for label in ('ready feedback ','unsupported feedback ','pair feedback ','closed feedback '))
        if faces:names.update(label+str(cycle) for label in ('filtered navigation ','navigation boundary '))
    if faces:names.update(('faces screenshot captured','alpha changes rendered pixels','green faces rendered','faces controls preserved','transparent face colors stay green','reselected transparent colors stay green','concave screenshot captured','panel scroll reaches values'))
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


def prepare(root,fixture_data,faces=False):
    """Run in CPU launcher before Kit starts; all authored data is disposable."""
    from pxr import Usd,UsdGeom
    from usd_scene_review import create_snapshot
    root=Path(root);paths={}
    for side in ('A','B'):
        folder=root/('bounds-source-'+side);folder.mkdir()
        source=folder/'scene.usda';source.write_bytes(fixture_data)
        if side=='B' or faces:
            stage=Usd.Stage.Open(str(source))
            if not faces:UsdGeom.Xformable(stage.GetPrimAtPath('/World/Item')).AddTranslateOp().Set((.4,0,0))
            else:
                if side=='A':UsdGeom.Xformable(stage.GetPrimAtPath('/World/Item')).AddTranslateOp().Set((-.4,0,0))
                for name,scheme in (('Triangle','none'),('Subdivision','catmullClark')):
                    mesh=UsdGeom.Mesh.Define(stage,'/World/'+name);mesh.CreateSubdivisionSchemeAttr(scheme)
                    mesh.CreatePointsAttr([(-.5,0,0),(.5,0,0),(0,0,1)])
                    mesh.CreateFaceVertexCountsAttr([3]);mesh.CreateFaceVertexIndicesAttr([0,1,2])
                    mesh.AddTranslateOp().Set((0,0 if side=='A' else .4,0))
                for name in ('Quad','Nonplanar','Concave'):
                    mesh=UsdGeom.Mesh.Define(stage,'/World/'+name);mesh.CreateSubdivisionSchemeAttr('none')
                    points=[(-.5,0,0),(.5,0,0),(.5,.1 if name=='Nonplanar' else 0,1),(-.5,0,1)]
                    counts=[4];indices=[0,1,2,3]
                    if name=='Concave':
                        points=[(-1.5,-1.1,-1.5),(1.5,-1.1,-1.5),(1.5,-1.1,1.5),(.5,-1.1,1.5),(.5,-1.1,-.5),(-.5,-1.1,-.5),(-.5,-1.1,1.5),(-1.5,-1.1,1.5),(-.1,0,0),(.1,0,0),(0,0,.1)]
                        counts=[8,3];indices=list(range(11));mesh.CreateHoleIndicesAttr([1])
                    mesh.CreatePointsAttr(points);mesh.CreateFaceVertexCountsAttr(counts);mesh.CreateFaceVertexIndicesAttr(indices)
                    mesh.AddTranslateOp().Set((0,0 if side=='A' else .4,0))
                parent=UsdGeom.Xform.Define(stage,'/World/Reflected');parent.AddTranslateOp().Set((0 if side=='A' else .4,0,0));parent.AddScaleOp().Set((-1,2,1));parent.AddRotateZOp().Set(25)
                mesh=UsdGeom.Mesh.Define(stage,'/World/Reflected/Quad');mesh.CreateSubdivisionSchemeAttr('none');mesh.CreateOrientationAttr('leftHanded')
                mesh.CreatePointsAttr([(-.5,0,0),(.5,0,0),(.5,0,1),(-.5,0,1)]);mesh.CreateFaceVertexCountsAttr([4]);mesh.CreateFaceVertexIndicesAttr([0,1,2,3])
                if side=='A':UsdGeom.Cube.Define(stage,'/World/Removed').CreateSizeAttr(.5)
            stage.GetRootLayer().Save();stage=None
        paths[side]=str(create_snapshot(source,root/('bounds-'+side)))
    (root/'bounds-inputs.json').write_text(json.dumps(paths))


async def evaluate(probe,root,faces=False):
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
        if faces:
            # Only our newly created review panel in the disposable test host;
            # expose the working viewport for swapchain inspection.
            owner._window.width=580;owner._window.height=800
            owner._window.position_x=1000;owner._window.position_y=70
        paths=json.loads((root/'bounds-inputs.json').read_text())
        for side in ('A','B'):owner._paths[side].set_value(paths[side])
        owner._compare() # Actual Compare button callback, including scheduler.
        if owner._task:await owner._task
        check('comparison callback completed',owner._report is not None and owner._report['status']!='unknown')
        changed=next(change for change in owner._report['changes'] if change['path']=='/World/Item')
        changes={change['path']:change for change in owner._report['changes']}
        for cycle in range(2):
            owner._selected=None
            owner._show_bounds_overlay();await updates()
            check('show empty '+str(cycle),owner._bounds_overlay is not None and owner._bounds_overlay.line_count==0)
            owner._select(changed);await updates()
            check('select before/after '+str(cycle),owner._bounds_overlay.line_count==108 and '0.4' in owner._bounds_overlay.caption.text)
            if faces:
                owner._bounds_faces.set_value(True);await updates()
                check('cube UI faces '+str(cycle),owner._bounds_overlay.face_count==12 and owner._bounds_overlay.line_count==108
                      and owner._bounds_overlay.last_plan['old_faces']['status']=='ready')
                check('ready feedback '+str(cycle),'/World/Item' in owner._display_feedback.as_string and '12 triangles' in owner._display_feedback.as_string)
                owner._select(changes['/World/Triangle']);await updates()
                check('triangle UI faces '+str(cycle),owner._bounds_overlay.face_count==1)
                owner._select(changes['/World/Quad']);await updates()
                check('quad UI faces '+str(cycle),owner._bounds_overlay.face_count==2)
                owner._select(changes['/World/Concave']);await updates()
                check('concave and hole UI faces '+str(cycle),owner._bounds_overlay.face_count==6 and len(owner._bounds_overlay.last_plan['old_faces']['wires'])==16)
                owner._select(changes['/World/Nonplanar']);await updates()
                check('nonplanar refused '+str(cycle),owner._bounds_overlay.face_count==0 and 'nonplanar' in owner._bounds_overlay.caption.text)
                owner._select(changes['/World/Reflected']);await updates()
                from pxr import Gf,UsdGeom
                vertices=owner._bounds_overlay.last_plan['old_faces']['meshes'][0]['positions']
                normal=Gf.Cross(Gf.Vec3d(*vertices[1])-Gf.Vec3d(*vertices[0]),Gf.Vec3d(*vertices[2])-Gf.Vec3d(*vertices[0]))
                source=owner._bounds_overlay.snapshots['A'].stage.GetPrimAtPath('/World/Reflected/Quad')
                matrix=UsdGeom.XformCache().GetLocalToWorldTransform(source)
                expected=matrix.GetInverse().GetTranspose().TransformDir(Gf.Vec3d(0,1,0)) # leftHanded XZ quad
                check('reflected parent UI faces '+str(cycle),owner._bounds_overlay.face_count==2 and Gf.Dot(normal,expected)>0)
                owner._select(changes['/World/Subdivision']);await updates()
                check('subdivision refused '+str(cycle),owner._bounds_overlay.face_count==0 and 'linear Mesh' in owner._bounds_overlay.caption.text)
                feedback=' '.join(owner._display_feedback.as_string.split())
                check('unsupported feedback '+str(cycle),'/World/Subdivision' in feedback and 'not shown' in feedback and 'linear Mesh' in feedback)
                owner._select(changes['/World/Removed']);await updates()
                check('removed UI faces '+str(cycle),owner._bounds_overlay.face_count==12)
                owner._bounds_faces.set_value(False);await updates()
                check('face toggle clears '+str(cycle),owner._bounds_overlay.face_count==0)
                pair=owner._report['overlap_analysis']['pairs'][0];owner._select_pair(pair);await updates()
                feedback=' '.join(owner._display_feedback.as_string.split())
                check('pair feedback '+str(cycle),owner._bounds_overlay.line_count==0 and 'Pair evidence' in feedback and 'geometry is cleared' in feedback and 'framed' not in owner._motion.as_string)
                from usd_scene_review.presentation import CHANGE_KINDS
                owner._query.set_value('removed')
                owner._kind_filter.model.get_item_value_model().set_value(CHANGE_KINDS.index('removed'))
                owner._navigate_change(1);await updates()
                check('filtered navigation '+str(cycle),owner._selected=='/World/Removed'
                      and owner._selected_pair is None and owner._bounds_overlay.face_count==0
                      and len(owner._visible_changes())==1 and state()==before)
                owner._navigate_change(1);await updates()
                check('navigation boundary '+str(cycle),owner._selected=='/World/Removed'
                      and 'No wrap' in owner._status.as_string and state()==before)
                owner._query.set_value('')
                owner._kind_filter.model.get_item_value_model().set_value(0)
                owner._select(changed)
            owner._hide_bounds_overlay();await updates()
            check('toggle off '+str(cycle),owner._bounds_overlay is None)
            owner._show_bounds_overlay();await updates()
            check('toggle on '+str(cycle),owner._bounds_overlay is not None and owner._bounds_overlay.line_count==108)
            held=owner._bounds_overlay;owner._close_review();await updates()
            check('close review '+str(cycle),owner._bounds_overlay is None)
            if faces:check('closed feedback '+str(cycle),'display off' in owner._display_feedback.as_string)
            check('subscriptions released '+str(cycle),held.scene_view is None and not held.subscriptions)
            check('cycle preservation '+str(cycle),state()==before)
        if faces:
            from omni.kit.renderer.capture import acquire_renderer_capture_interface
            from PIL import Image,ImageChops,ImageStat
            recorder=acquire_renderer_capture_interface()
            await updates(20);maximum=owner._panel_scroll.scroll_y_max
            owner._panel_scroll.scroll_y=maximum;await updates()
            result['panel_scroll']={'max_y':maximum,'observed_y':owner._panel_scroll.scroll_y}
            check('panel scroll reaches values',maximum>0 and owner._panel_scroll.scroll_y>0)
            owner._panel_scroll.scroll_y=0;await updates()
            owner._show_bounds_overlay();owner._select(changed);owner._bounds_faces.set_value(True);await updates(20)
            async def capture(name):
                recorder.capture_next_frame_swapchain(str(root/name));await updates(8);recorder.wait_async_capture()
            await capture('ui-faces-alpha22.png')
            # Owned UI primitives only: opacity control does not touch USD/session or renderer settings.
            mesh_data=owner._bounds_overlay.last_plan['old_faces']['meshes']
            scene=owner._bounds_overlay.scene_view.scene;scene.clear()
            from omni.ui import scene as sc
            with scene:
                for mesh in mesh_data:
                    sc.PolygonMesh(mesh['positions'],[[.12,.95,.22,1.] for _ in mesh['positions']],mesh['vertex_counts'],mesh['vertex_indices'])
                plan=owner._bounds_overlay.last_plan;old=plan['old_faces']
                for index in range(0,len(old['wires']),2):
                    sc.Line(old['wires'][index],old['wires'][index+1],color=old['wire_color'],thickness=1.)
                for box in plan['boxes']:
                    for index in range(0,len(box['points']),2):
                        sc.Line(box['points'][index],box['points'][index+1],color=box['color'],thickness=2.5)
            await updates(20);await capture('ui-faces-opaque-control.png')
            with Image.open(root/'ui-faces-alpha22.png') as first,Image.open(root/'ui-faces-opaque-control.png') as second:
                difference=sum(ImageStat.Stat(ImageChops.difference(first.convert('RGB'),second.convert('RGB'))).mean)
                green=sum(1 for r,g,b in first.convert('RGB').getdata() if g>r+20 and g>b+20)
                faint=list(first.convert('RGB').crop((70,140,950,580)).getdata())
                opaque=list(second.convert('RGB').crop((70,140,950,580)).getdata())
                mask=[index for index,(r,g,b) in enumerate(opaque) if g>r+50 and g>b+50]
                matching=sum(1 for index in mask if faint[index][1]>faint[index][0]+5 and faint[index][1]>faint[index][2]+5)
                result['face_pixels']={'alpha_opaque_difference_mean_sum':difference,'green_pixels':green,
                    'opaque_green_mask_pixels':len(mask),'faint_green_mask_matches':matching,'faint_green_match_ratio':matching/max(1,len(mask))}
            check('alpha changes rendered pixels',difference>.1)
            check('green faces rendered',green>100)
            check('transparent face colors stay green',len(mask)>1000 and matching/len(mask)>.95)
            owner._bounds_overlay.select(owner._selected);await updates(20)
            await capture('ui-faces-review.png');recorder=None
            with Image.open(root/'ui-faces-review.png') as frame:
                pixels=list(frame.convert('RGB').crop((70,140,950,580)).getdata())
                matching=sum(1 for index in mask if pixels[index][1]>pixels[index][0]+5 and pixels[index][1]>pixels[index][2]+5)
                result['face_pixels']['reselected_green_match_ratio']=matching/max(1,len(mask))
            check('reselected transparent colors stay green',len(mask)>1000 and matching/len(mask)>.95)
            owner._select(changes['/World/Concave']);await updates(20)
            recorder=acquire_renderer_capture_interface();await capture('ui-concave-review.png');recorder=None
            check('concave screenshot captured',(root/'ui-concave-review.png').stat().st_size>1000)
            check('faces screenshot captured',(root/'ui-faces-review.png').stat().st_size>1000)
            owner._hide_bounds_overlay();owner._bounds_faces.set_value(False)
            check('faces controls preserved',state()==before)
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
    if {row['name'] for row in result['checks']}!=check_names(faces):raise RuntimeError('Incomplete bounds treatment')
    result['status']='passed';probe.result['candidate']=result;probe.write()
    return result
