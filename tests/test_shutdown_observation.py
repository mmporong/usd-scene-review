"""CPU regression for exact window scopes and non-destructive close evidence."""
import ast
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('shutdown_observation',ROOT/'tools/shutdown_observation.py')
observation=importlib.util.module_from_spec(spec);spec.loader.exec_module(observation)


class ShutdownObservationTests(unittest.TestCase):
    def test_actual_titles_are_exact_scopes_and_prompt_is_observed_only(self):
        windows=[SimpleNamespace(title='Stage',visible=True),
                 SimpleNamespace(title='Warning glyph',visible=True),
                 SimpleNamespace(title='Hidden',visible=False),
                 SimpleNamespace(title='unsafe//scope',visible=True)]
        def query(scope):
            return [SimpleNamespace(widget=SimpleNamespace(text=observation.SAVE_PROMPT))] if scope.startswith('Warning glyph//') else []
        find=Mock(side_effect=query)
        receipts=observation.window_receipts(windows,find,'Warning glyph')
        self.assertEqual([call.args[0] for call in find.call_args_list],
                         ['Warning glyph//Frame/**/Label[*]'])
        self.assertEqual([row['save_prompt'] for row in receipts],[False,True,False,False])
        find.reset_mock()
        observation.window_receipts(windows,find)
        find.assert_not_called()

    def test_native_pending_state_is_separate_from_unchanged_dirty_layers(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture=Path(tmp)/'fixture.usda'
            root=SimpleNamespace(realPath=str(fixture),dirty=False)
            root.ExportToString=lambda:'root'
            stage=Mock();stage.GetRootLayer.return_value=root
            stage.GetSessionLayer.return_value=SimpleNamespace(dirty=True,ExportToString=lambda:'session')
            stage.GetEditTarget.return_value.GetLayer.return_value=root
            stage.Traverse.return_value=[]
            ctx=Mock();ctx.get_stage.return_value=stage;ctx.get_name.return_value=''
            ctx.get_stage_id.return_value=42;ctx.can_close_stage.return_value=True
            ctx.has_pending_edit.return_value=False
            impl=SimpleNamespace(_file_util_instance=None)
            before=observation.close_receipt(ctx,ctx,stage,fixture,impl,[])
            ctx.has_pending_edit.return_value=True
            after=observation.close_receipt(ctx,ctx,stage,fixture,impl,[])
            self.assertFalse(before['pending_edit']);self.assertTrue(after['pending_edit'])
            self.assertEqual(before['stage_id'],after['stage_id'])
            self.assertTrue(after['same_stage']);self.assertTrue(after['fixture_active'])
            self.assertFalse(after['root_dirty']);self.assertTrue(after['session_dirty'])
            self.assertFalse(after['file_utility_present'])
            self.assertEqual(after['edit_target'],'root')
            self.assertNotEqual(after['root_text_sha256'],after['session_text_sha256'])
            self.assertEqual(after['camera_prims'],[])

    def test_native_observer_records_transition_inside_read_sequence(self):
        ctx=Mock();ctx.get_stage.return_value=None;ctx.get_stage_id.return_value=0
        ctx.get_name.return_value='';ctx.has_pending_edit.side_effect=[False,False,True]
        ctx.can_close_stage.return_value=False
        receipt=observation.context_receipt(ctx,ctx,None,Path('unused'))
        self.assertFalse(receipt['pending_at_entry'])
        self.assertFalse(receipt['pending_edit'])
        self.assertTrue(receipt['pending_after_native_observation'])

    def test_file_task_error_is_receipted_without_running_or_cancelling_task(self):
        ctx=Mock();ctx.get_stage.return_value=None;ctx.get_stage_id.return_value=0
        ctx.get_name.return_value='';ctx.has_pending_edit.return_value=False
        ctx.can_close_stage.return_value=False
        task=Mock();task.cancelled.return_value=False;task.done.return_value=True
        task.exception.return_value=RuntimeError('close failed')
        receipt=observation.close_receipt(ctx,ctx,None,Path('unused'),SimpleNamespace(
            _file_util_instance=SimpleNamespace(_task=task)),[])
        self.assertEqual(receipt['file_task_state'],'done')
        self.assertEqual(receipt['file_task_error'],'RuntimeError: close failed')
        self.assertFalse(receipt['stage_present']);task.cancel.assert_not_called()

    def test_probe_cannot_select_prompt_or_clear_pending_edits(self):
        source=(ROOT/'tools/in_app_shutdown_probe.py').read_text()
        attrs={node.func.attr for node in ast.walk(ast.parse(source))
               if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)}
        self.assertFalse(attrs & {'click','set_pending_edit','save','save_as'})
        self.assertNotIn("'*//",source)
        for phase in ('before-observer-imports','before-candidate','after-candidate-cleanup','before-public-close','public-close-returned'):
            self.assertIn(phase,source)
        self.assertLess(source.index("early=context_receipt"),source.index('import omni.kit.ui_test'))
        self.assertLess(source.index('before_query=context_receipt'),source.index('windows=window_receipts'))
