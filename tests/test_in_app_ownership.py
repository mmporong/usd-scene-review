"""Failure-injection checks of product lifecycle methods; not native UI proof."""
import ast
import asyncio
import gc
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, AsyncMock


def product_class():
    path=Path(__file__).resolve().parents[1]/'exts/mmporong.scene.review/mmporong/scene/review/in_app.py'
    tree=ast.parse(path.read_text(encoding='utf-8'))
    node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='InAppReview')
    owners=[]
    usd=NS(destroy_context=Mock(return_value=True))
    timeline=NS(destroy_timeline=Mock(return_value=True),get_timeline_interface=Mock())
    env={'asyncio':asyncio,'gc':gc,'_OWNERS':owners,'omni':NS(usd=usd,timeline=timeline),
         'carb':NS(settings=NS(get_settings=Mock())), 'ui':NS(Workspace=NS(restore_workspace=Mock()))}
    logic=Path(__file__).resolve().parents[1]/'src/usd_scene_review/in_app_logic.py'
    # The extracted class uses the same shared product guard explanation.
    constant=next(item for item in ast.parse(logic.read_text()).body if isinstance(item,ast.Assign)
                  and isinstance(item.targets[0],ast.Name) and item.targets[0].id=='FULL_HOST_REVIEW_LIMITATION')
    exec(compile(ast.Module(body=[constant],type_ignores=[]),str(logic),'exec'),env)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),env)
    return env['InAppReview'],owners,usd,timeline


class InAppOwnershipTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancelled_close_keeps_native_drain_alive_until_confirmed(self):
        cls,owners,usd,timeline=product_class();owner=cls(Mock());owner.state='open'
        future=asyncio.get_running_loop().create_future()
        async def render_frames(count):return await future
        owner.resources={'A':{'widget':NS(viewport_api=NS(wait_for_rendered_frames=render_frames))}}
        owner.close_sync=Mock(return_value=True)
        waiter=asyncio.create_task(owner.close());await asyncio.sleep(0);await asyncio.sleep(0)
        waiter.cancel()
        with self.assertRaises(asyncio.CancelledError):await waiter
        self.assertFalse(future.cancelled());self.assertTrue(owner._drain_pending)
        owner.close_sync.assert_not_called()
        future.set_result(None)
        for _ in range(4):await asyncio.sleep(0)
        self.assertFalse(owner._drain_pending);owner.close_sync.assert_called_once()

    async def test_disable_during_pending_binding_quiesces_selection_without_destroying(self):
        cls,owners,usd,timeline=product_class();callback=Mock();owner=cls(Mock(),callback)
        owner.state='open';owner._attach_pending=True
        owner.resources={'A':{'widget':object()}}
        self.assertFalse(owner.close_sync())
        self.assertTrue(owner._closing_requested);self.assertEqual(owner.state,'closing')
        self.assertIsNone(owner.on_select)
        owner.select('/Ignored')
        callback.assert_not_called();usd.destroy_context.assert_not_called()

    async def test_cancelled_viewport_binding_retains_widget_until_native_completion(self):
        cls,owners,usd,timeline=product_class();owner=cls(Mock());owner.state='opening'
        future=asyncio.get_running_loop().create_future();widget=object()
        item={'widget':widget};owner.resources={'A':item}
        waiter=asyncio.create_task(owner._native_wait(item,future));await asyncio.sleep(0)
        waiter.cancel()
        with self.assertRaises(asyncio.CancelledError):await waiter
        self.assertFalse(future.cancelled());self.assertFalse(owner.close_sync())
        self.assertIs(item['widget'],widget);usd.destroy_context.assert_not_called()
        owner.invalidate=Mock();future.set_result(None);await asyncio.sleep(0);await asyncio.sleep(0)
        self.assertFalse(owner._attach_pending);owner.invalidate.assert_called_once()

    async def test_unready_app_is_refused_before_any_native_ownership(self):
        cls,owners,usd,timeline=product_class();owner=cls(Mock())
        env=cls.open.__globals__;env['omni'].kit=NS(app=NS(get_app=lambda:NS(is_app_ready=lambda:False)))
        with self.assertRaisesRegex(RuntimeError,'startup'):await owner.open({}, {})
        self.assertEqual(owner.state,'closed');self.assertFalse(owner.resources);self.assertFalse(owners)

    async def test_known_failed_full_host_is_refused_before_native_ownership(self):
        cls,owners,usd,timeline=product_class();owner=cls(Mock());env=cls.open.__globals__
        env['omni'].kit=NS(app=NS(get_app=lambda:NS(is_app_ready=lambda:True)))
        env['full_host_blocked']=lambda:True
        with self.assertRaisesRegex(RuntimeError,'save-state preservation'):await owner.open({}, {})
        self.assertEqual(owner.state,'closed');self.assertFalse(owner.resources);self.assertFalse(owners)

    async def test_float32_setting_is_restored_using_canonical_written_value(self):
        import struct
        cls,owners,usd,timeline=product_class();owner=cls(Mock());owner.state='open';owner.snapshots={}
        key='exposure';values={}
        settings=NS(get=lambda k:values.get(k),destroy_item=lambda k:values.pop(k,None),
                    set=lambda k,v:values.update({k:struct.unpack('f',struct.pack('f',v))[0]}))
        env=cls.close_sync.__globals__;env['carb'].settings.get_settings.return_value=settings
        env['_RENDER_SETTINGS']={key:.02};owner.settings_before={key:(None,.02)}
        owner._configure_renderer();self.assertNotEqual(values[key],.02)
        self.assertEqual(owner.settings_before[key][1],values[key])
        # Some native subscribers canonicalize only on a later renderer frame.
        owner.settings_before[key]=(None,.02)
        self.assertTrue(owner.close_sync());self.assertNotIn(key,values)

    async def test_renderer_defaults_during_native_close_do_not_erase_baseline_or_external_edit(self):
        for current,expected in ((5,9),(7,7)):
            cls,owners,usd,timeline=product_class();owner=cls(Mock());owner.state='open'
            owner.resources={'A':{'name':'owned','detached':True}};owner.snapshots={}
            values={'key':current};settings=NS(get=lambda k:values.get(k),set=lambda k,v:values.update({k:v}))
            cls.close_sync.__globals__['carb'].settings.get_settings.return_value=settings
            owner.settings_before={'key':(9,5)}
            def native_destroy(name):values['key']=1;return True
            usd.destroy_context.side_effect=native_destroy
            self.assertTrue(owner.close_sync());self.assertEqual(values['key'],expected)

    async def test_renderer_restore_plan_survives_native_reset_then_failed_destruction(self):
        cls,owners,usd,timeline=product_class();owner=cls(Mock());owner.state='open';owner.snapshots={}
        owner.resources={'A':{'name':'owned','detached':True}};values={'key':5}
        settings=NS(get=lambda k:values.get(k),set=lambda k,v:values.update({k:v}))
        cls.close_sync.__globals__['carb'].settings.get_settings.return_value=settings
        owner.settings_before={'key':(9,5)};attempt=[]
        def destroy(name):values['key']=1;attempt.append(1);return len(attempt)>1
        usd.destroy_context.side_effect=destroy
        self.assertFalse(owner.close_sync());self.assertEqual(values['key'],1)
        self.assertTrue(owner.close_sync());self.assertEqual(values['key'],9)

    async def test_failed_render_drain_retains_views_and_blocks_sync_teardown(self):
        cls,owners,usd,timeline=product_class();owner=cls(Mock());owner.state='open';owners.append(owner)
        widget=NS(viewport_api=NS(wait_for_rendered_frames=AsyncMock(side_effect=RuntimeError('render unavailable'))))
        owner.resources={'A':{'name':'owned','widget':widget,'ghost':Mock()}}
        self.assertFalse(await owner.close());self.assertTrue(owner._drain_pending)
        self.assertFalse(owner.close_sync());usd.destroy_context.assert_not_called()
        self.assertIs(owner.resources['A']['widget'],widget)
        with self.assertRaises(RuntimeError):cls(Mock())

    async def test_cancelled_wait_retains_native_attachment_until_confirmed(self):
        cls,owners,usd,timeline=product_class();owner=cls(Mock());owner.state='opening'
        future=asyncio.get_running_loop().create_future()
        async def native_attach(stage):return await future
        item={'ctx':NS(attach_stage_async=native_attach),'stage':object()};owner.resources={'A':item}
        waiter=asyncio.create_task(owner._attach(item));await asyncio.sleep(0)
        waiter.cancel()
        with self.assertRaises(asyncio.CancelledError):await waiter
        self.assertFalse(future.cancelled());self.assertTrue(owner._attach_pending)
        self.assertFalse(owner.close_sync());usd.destroy_context.assert_not_called()
        owner.invalidate=Mock();future.set_result((True,''));await asyncio.sleep(0);await asyncio.sleep(0)
        self.assertFalse(owner._attach_pending);owner.invalidate.assert_called_once()

    async def test_native_attachment_exception_retains_uncertain_owner(self):
        cls,owners,usd,timeline=product_class();owner=cls(Mock());owner.state='opening'
        async def native_attach(stage):raise RuntimeError('native result unavailable')
        owner.resources={'A':{'ctx':NS(attach_stage_async=native_attach),'stage':object()}}
        with self.assertRaises(RuntimeError):await owner._attach(owner.resources['A'])
        await asyncio.sleep(0)
        self.assertTrue(owner._attach_pending);self.assertFalse(owner.close_sync())
        usd.destroy_context.assert_not_called()

    async def test_failed_context_or_timeline_destruction_is_retryable_and_blocks_replacement(self):
        for failure in ('context','timeline'):
            cls,owners,usd,timeline=product_class();owner=cls(Mock());owner.state='open';owners.append(owner)
            owner.resources={'A':{'name':'owned','detached':True}};owner.snapshots={}
            failing=usd.destroy_context if failure=='context' else timeline.destroy_timeline
            failing.side_effect=[False,True]
            self.assertFalse(owner.close_sync());self.assertEqual(owner.state,'failed')
            self.assertEqual(owner.resources['A']['name'],'owned')
            with self.assertRaises(RuntimeError):cls(Mock())
            self.assertTrue(owner.close_sync());self.assertEqual(owner.state,'closed');self.assertFalse(owners)
            self.assertEqual(failing.call_count,2)
            self.assertEqual(usd.destroy_context.call_count,2 if failure=='context' else 1)

    async def test_play_or_stage_change_during_opening_invalidates_before_ui_creation(self):
        cls,owners,usd,timeline=product_class();owner=cls(Mock());stage=object()
        owner.host=NS(get_stage=lambda:stage);owner.host_stage=stage
        playing=NS(is_stopped=Mock(return_value=False));timeline.get_timeline_interface.return_value=playing
        self.assertFalse(owner._opening_current())
        playing.is_stopped.return_value=True;owner.host_stage=object()
        self.assertFalse(owner._opening_current())
        owner.host_stage=stage;self.assertTrue(owner._opening_current())

    async def test_view_destroy_failure_preserves_handle_and_prevents_context_teardown(self):
        for resource in ('widget','scene_view','camera_manipulator'):
            cls,owners,usd,timeline=product_class();owner=cls(Mock());owner.state='open';owners.append(owner)
            handle=Mock();handle.destroy.side_effect=[RuntimeError('destroy failed'),None]
            owner.resources={'A':{'name':'owned','detached':True,resource:handle}};owner.snapshots={}
            self.assertFalse(owner.close_sync());self.assertEqual(owner.state,'failed')
            self.assertIs(owner.resources['A'][resource],handle);usd.destroy_context.assert_not_called()
            with self.assertRaises(RuntimeError):cls(Mock())
            self.assertTrue(owner.close_sync());self.assertEqual(handle.destroy.call_count,2)
            usd.destroy_context.assert_called_once_with('owned')
