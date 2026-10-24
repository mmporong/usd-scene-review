import ast
import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock
from pxr import Gf,Usd,UsdGeom
from usd_scene_review import compare,create_snapshot,load_snapshot
from usd_scene_review.overlay import bounds_plan,overlay_text,ComparisonReceipt,validate_report_reference
from usd_scene_review.snapshot import digest
from unittest.mock import patch
import importlib

ROOT=Path(__file__).resolve().parents[1]


def fixture(root):
    paths={}
    for side in ('A','B'):
        folder=root/('source-'+side);folder.mkdir();path=folder/'scene.usda'
        stage=Usd.Stage.CreateNew(str(path));UsdGeom.SetStageMetersPerUnit(stage,1);UsdGeom.SetStageUpAxis(stage,'Z')
        parent=UsdGeom.Xform.Define(stage,'/World');parent.AddTranslateOp().Set((0 if side=='A' else 50,0,0))
        UsdGeom.Cube.Define(stage,'/World/Inherited').CreateSizeAttr(100)
        moved=UsdGeom.Cube.Define(stage,'/World/Moved');moved.CreateSizeAttr(100)
        moved.AddTranslateOp().Set((0,0 if side=='A' else 80,0))
        UsdGeom.Cube.Define(stage,'/World/'+('Removed' if side=='A' else 'Added')).CreateSizeAttr(80)
        hidden=UsdGeom.Cube.Define(stage,'/World/Hidden');hidden.CreateVisibilityAttr('inherited' if side=='A' else 'invisible')
        stage.GetRootLayer().Save();paths[side]=create_snapshot(path,root/side)
    return paths,compare(paths['A'],paths['B'])


class Scene:
    def __init__(self):self.lines=[];self.meshes=[]
    def clear(self):self.lines.clear();self.meshes.clear()
    def __enter__(self):return self
    def __exit__(self,*args):pass


def adapter(snapshots,report):
    path=ROOT/'exts/mmporong.scene.review/mmporong/scene/review/bounds_overlay.py'
    tree=ast.parse(path.read_text())
    node=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='BoundsOverlay')
    scene=Scene()
    def line(a,b,**kw):scene.lines.append((a,b,kw))
    env={'bounds_plan':bounds_plan,'overlay_text':overlay_text,
         'sc':NS(Line=line,PolygonMesh=lambda *args:scene.meshes.append(args),Matrix44=lambda *values:values),
         'omni':NS(timeline=NS(get_timeline_interface=lambda:NS(is_stopped=lambda:True)))}
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),env)
    owner=env['BoundsOverlay'](Mock());owner.state='open';owner.report=report;owner.snapshots=dict(snapshots)
    owner.scene_view=NS(scene=scene,destroy=Mock(),model=NS());owner.frame=Mock();owner.caption=NS(text='')
    return owner,scene,env


class BoundsOverlayTests(unittest.TestCase):
    def test_optional_faces_are_real_geometry_clear_on_toggle_and_reselection(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths,report=fixture(Path(tmp));owner,scene,_=adapter({s:load_snapshot(p) for s,p in paths.items()},report)
            owner.show_faces=True;owner.select('/World/Inherited')
            self.assertEqual(owner.face_count,12);self.assertEqual(len(scene.meshes),1)
            self.assertEqual(len(scene.lines),120) # 108 A/B bounds + 12 Cube edges
            self.assertTrue(all(color[3]==.22 for color in scene.meshes[0][1]))
            owner.select('/World/Added');self.assertEqual(owner.face_count,0);self.assertFalse(scene.meshes)
            self.assertIn('absent',owner.caption.text)
            owner.select('/World/Removed');self.assertEqual(owner.face_count,12)
            owner.show_faces=False;owner.select('/World/Removed');self.assertEqual(owner.face_count,0)
            self.assertFalse(scene.meshes);owner.show_faces=True;owner.select(None);self.assertFalse(scene.meshes)

    def test_pinned_report_avoids_reanalysis_without_accepting_changed_report_or_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths,report=fixture(Path(tmp));hashes={side:digest(path) for side,path in paths.items()}
            receipt=ComparisonReceipt.capture(paths,report,hashes)
            module=importlib.import_module('usd_scene_review.compare')
            with patch.object(module,'compare',wraps=module.compare) as engine:
                validate_report_reference(paths,report,receipt);engine.assert_not_called()
                validate_report_reference(paths,report);engine.assert_called_once()
            changed=copy.deepcopy(report);changed['analysis_config']['overlap']['tolerance_m']*=2
            with self.assertRaises(ValueError):validate_report_reference(paths,changed,receipt)
            with self.assertRaises(ValueError):validate_report_reference(paths,report,object())
            paths['A'].write_text('{}')
            self.assertFalse(receipt.matches(paths,report))
            with self.assertRaises(ValueError):ComparisonReceipt.capture(paths,report,hashes)

    def test_receipt_never_replaces_current_bundle_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths,report=fixture(Path(tmp));receipt=ComparisonReceipt.capture(paths,report,{s:digest(p) for s,p in paths.items()})
            snapshots={s:load_snapshot(p) for s,p in paths.items()}
            snapshot=snapshots['A'];snapshot.root.write_text(snapshot.root.read_text()+'\n# mutated\n')
            self.assertTrue(receipt.matches(paths,report)) # manifest/report still pinned
            with self.assertRaises(ValueError):bounds_plan(report,snapshots,'/World/Moved')
            with self.assertRaises(ValueError):bounds_plan(report,snapshots,'/World/Moved',show_faces=True)

    def test_move_parent_delete_hidden_none_and_source_layers_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths,report=fixture(Path(tmp));snapshots={s:load_snapshot(p) for s,p in paths.items()}
            before={s:(snapshot.stage.GetRootLayer().ExportToString(),snapshot.stage.GetSessionLayer().ExportToString()) for s,snapshot in snapshots.items()}
            plan=bounds_plan(report,snapshots,'/World/Inherited')
            self.assertEqual([box['side'] for box in plan['boxes']],['A','B'])
            self.assertEqual([len(box['points'])//2 for box in plan['boxes']],[96,12])
            self.assertEqual(plan['boxes'][1]['bounds'][0][0]-plan['boxes'][0]['bounds'][0][0],50)
            self.assertIn('ANCESTOR',overlay_text(plan))
            self.assertEqual(bounds_plan(report,snapshots,'/World/Removed')['presence']['B'],'absent')
            self.assertEqual(bounds_plan(report,snapshots,'/World/Added')['presence']['A'],'absent')
            self.assertEqual(len(bounds_plan(report,snapshots,'/World/Hidden')['boxes']),1)
            self.assertEqual(bounds_plan(report,snapshots,None)['boxes'],[])
            self.assertEqual(before,{s:(snapshot.stage.GetRootLayer().ExportToString(),snapshot.stage.GetSessionLayer().ExportToString()) for s,snapshot in snapshots.items()})

    def test_reselection_invalid_path_and_none_clear_old_geometry(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths,report=fixture(Path(tmp));owner,scene,_=adapter({s:load_snapshot(p) for s,p in paths.items()},report)
            owner.select('/World/Moved');self.assertEqual(len(scene.lines),108)
            owner.select('/World/Removed');self.assertEqual(len(scene.lines),96)
            owner.select('/World/Added');self.assertEqual(len(scene.lines),12)
            owner.select(None);self.assertFalse(scene.lines)
            owner.select('/World/Moved')
            with self.assertRaises(ValueError):owner.select('/NotInReport')
            self.assertFalse(scene.lines);self.assertEqual(owner.line_count,0);self.assertIsNone(owner.last_plan)

    def test_coordinate_mismatch_and_tampered_snapshot_refuse_display(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths,report=fixture(Path(tmp));snapshots={s:load_snapshot(p) for s,p in paths.items()}
            changed=copy.deepcopy(report);changed['stage_metadata']['meters_per_unit']['after']=.01
            with self.assertRaises(ValueError):bounds_plan(changed,snapshots,None)
            paths['A'].write_text('{}')
            with self.assertRaises(ValueError):bounds_plan(report,snapshots,'/World/Moved')

    def test_close_releases_subscriptions_scene_and_references(self):
        owner,scene,_=adapter({},{});subscriptions=[Mock(),Mock()];owner.subscriptions=list(subscriptions)
        widget=owner.scene_view;frame=owner.frame
        owner.close();owner.close()
        for subscription in subscriptions:subscription.unsubscribe.assert_called_once()
        widget.destroy.assert_called_once();frame.clear.assert_called_once()
        self.assertFalse(frame.visible);self.assertFalse(owner.subscriptions);self.assertFalse(owner.snapshots)
        self.assertIsNone(owner.scene_view);self.assertIsNone(owner.api)

    def test_camera_copy_targets_ui_model_and_hidden_viewport_closes(self):
        owner,scene,env=adapter({},{});stage=object()
        owner.stage=stage;owner.host=NS(get_stage=lambda:stage);owner.window=NS(visible=True)
        view=Gf.Matrix4d().SetTranslate((1,2,3));projection=Gf.Matrix4d(2)
        owner.api=NS(view=view,projection=projection)
        owner._tick()
        self.assertEqual(owner.scene_view.model.view,tuple(value for row in view for value in row))
        self.assertEqual(owner.api.view,view)
        owner.window.visible=False;owner._tick();self.assertEqual(owner.state,'closed')

    def test_stage_change_and_play_close_without_controlling_stage_or_timeline(self):
        for condition in ('stage','play'):
            owner,scene,env=adapter({},{});owner.stage=object();owner.window=NS(visible=True)
            owner.host=NS(get_stage=lambda:object() if condition=='stage' else owner.stage)
            env['omni'].timeline.get_timeline_interface=lambda:NS(is_stopped=lambda:condition!='play')
            owner._tick();self.assertEqual(owner.state,'closed')

    def test_adapter_has_no_usd_authoring_context_or_viewport_creation(self):
        path=ROOT/'exts/mmporong.scene.review/mmporong/scene/review/bounds_overlay.py'
        tree=ast.parse(path.read_text())
        attrs={node.func.attr for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)}
        self.assertFalse(attrs & {'create_context','open_stage_async','attach_stage_async','DefinePrim','SetEditTarget',
                                 'SetFromCamera','set_pending_edit','set_selected_prim_paths','set_current_time','add_scene_view'})
        self.assertIn('SceneView',attrs);self.assertNotIn('ViewportWidget',attrs)
