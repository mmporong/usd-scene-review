"""Stateful CPU tests of the product's actual selection/scheduling methods."""
import ast
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock,MagicMock,AsyncMock


def owner():
    path=Path(__file__).resolve().parents[1]/'exts/mmporong.scene.review/mmporong/scene/review/extension.py'
    tree=ast.parse(path.read_text())
    source=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='SceneReviewExtension')
    names={'_schedule','_run','_request_frame','_operation_finished','_select','_select_pair','_update_bounds_overlay','_close_bounds_overlay'}
    node=ast.ClassDef(name='SelectionRouter',bases=[],keywords=[],decorator_list=[],
                      body=[method for method in source.body if isinstance(method,(ast.FunctionDef,ast.AsyncFunctionDef)) and method.name in names])
    env={'asyncio':asyncio,'carb':NS(log_warn=Mock()),'details':lambda change:change['path'],
         'canonical':json.dumps,'pair_rows':lambda report,pair:[]}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(path),'exec'),env)
    result=env['SelectionRouter']()
    result._task=None;result._frame_requested=False;result._shutting_down=False
    result._report={'changes':[]};result._viewer=NS(state='closed');result._in_app=None
    result._bounds_overlay=None
    result._selected=None;result._selected_pair=None;result._selected_change=None
    result._reason=Mock();result._details=Mock();result._load_review=Mock()
    result._selected_label=Mock();result._motion=Mock();result._numeric=MagicMock()
    result.numeric_path=None
    result._render_numeric=lambda change:setattr(result,'numeric_path',change['path'])
    result.messages=[];result._message=result.messages.append
    return result


async def settle(result):
    for _ in range(30):
        await asyncio.sleep(0)
        if result._task is None:return
    raise AssertionError('Selection routing did not settle')


class SelectionFocusQueueTests(unittest.IsolatedAsyncioTestCase):
    async def test_overlay_selection_updates_without_native_viewer_focus(self):
        item=owner();item._frame=AsyncMock()
        item._bounds_overlay=NS(state='open',select=Mock(),caption=NS(text=''))
        item._select({'path':'/OverlayTarget'})
        item._bounds_overlay.select.assert_called_once_with('/OverlayTarget')
        self.assertEqual(item.numeric_path,'/OverlayTarget');item._frame.assert_not_awaited()

    async def test_metadata_selection_without_viewer_never_requests_native_focus(self):
        item=owner();item._frame=AsyncMock()
        item._select({'path':'/EvidenceOnly'})
        await asyncio.sleep(0)
        self.assertEqual(item.numeric_path,'/EvidenceOnly')
        self.assertIsNone(item._task);self.assertFalse(item._frame_requested)
        item._frame.assert_not_awaited()

    async def test_selection_during_open_focuses_latest_without_opening_another_viewer(self):
        item=owner();gate=asyncio.Future();frames=[];opens=[]
        async def opening():
            opens.append('open');await gate;item._viewer.state='running'
        async def frame():frames.append(item._selected)
        item._frame=frame;item._viewer.state='starting';item._schedule(opening())
        await asyncio.sleep(0)
        item._select({'path':'/A'});item._select({'path':'/B'})
        self.assertEqual(item.numeric_path,'/B');self.assertEqual(frames,[])
        gate.set_result(None);await settle(item)
        self.assertEqual(frames,['/B']);self.assertEqual(opens,['open'])
        self.assertFalse(item._frame_requested)

    async def test_rapid_clicks_during_frame_keep_only_latest_followup(self):
        item=owner();item._viewer.state='running';gate=asyncio.Future();frames=[]
        async def frame():
            frames.append(item._selected)
            if len(frames)==1:await gate
        item._frame=frame
        item._select({'path':'/A'});await asyncio.sleep(0)
        item._select({'path':'/B'});item._select({'path':'/C'})
        self.assertEqual(item.numeric_path,'/C');self.assertEqual(frames,['/A'])
        gate.set_result(None);await settle(item)
        self.assertEqual(frames,['/A','/C'])
        self.assertFalse(any('Wait for' in message for message in item.messages))

    async def test_latest_pair_replaces_pending_prim_focus(self):
        item=owner();gate=asyncio.Future();frames=[]
        async def opening():await gate;item._in_app=NS(state='open')
        async def frame():frames.append((item._selected,item._selected_pair['id'] if item._selected_pair else None))
        item._frame=frame;item._schedule(opening());await asyncio.sleep(0)
        item._select({'path':'/Old'})
        item._select_pair({'id':'new-pair','paths':['/Left','/Right']})
        gate.set_result(None);await settle(item)
        self.assertEqual(frames,[(None,'new-pair')])
        item._selected_label.set_value.assert_called_with('/Left / /Right')

    async def test_close_failure_and_shutdown_never_restart_or_frame_closed_viewer(self):
        for ending in ('closed','failed','shutdown','comparison-cleared'):
            with self.subTest(ending=ending):
                item=owner();item._viewer.state='running';gate=asyncio.Future();frames=[]
                async def operation():
                    await gate
                    if ending=='shutdown':item._shutting_down=True
                    elif ending=='comparison-cleared':item._report=None
                    else:item._viewer.state=ending
                async def frame():frames.append(item._selected)
                item._frame=frame;item._schedule(operation());await asyncio.sleep(0)
                item._select({'path':'/Last'});gate.set_result(None);await settle(item)
                self.assertEqual(frames,[]);self.assertFalse(item._frame_requested)

    async def test_older_completion_cannot_clear_new_operation_or_pending_focus(self):
        item=owner();item._viewer.state='running';gate=asyncio.Future();frames=[]
        async def operation():await gate
        async def frame():frames.append(item._selected)
        item._frame=frame;item._schedule(operation());await asyncio.sleep(0)
        current=item._task;item._select({'path':'/Newest'})
        old=asyncio.Future();old.set_result(None);item._operation_finished(old)
        self.assertIs(item._task,current);self.assertTrue(item._frame_requested)
        gate.set_result(None);await settle(item)
        self.assertEqual(frames,['/Newest'])
