"""CPU guard against invalid SDK diagnostic controls; imports no Kit modules."""
import ast
from pathlib import Path
import unittest


class EngineProbePlanTests(unittest.TestCase):
    def test_controls_allocate_exact_context_and_viewport_counts(self):
        source=Path(__file__).resolve().parents[1]/'tools/in_app_engine_probe.py'
        node=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='topology_layout')
        env={};exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),env)
        plan=env['topology_layout']
        for mode,contexts,viewports in (('single',1,1),('shared',1,2),('two-contexts',2,2)):
            layout=plan(mode)
            self.assertEqual(len(set(layout)),contexts)
            self.assertEqual(len(layout),viewports)
            self.assertEqual(set(layout),set(range(contexts)))
        with self.assertRaises(ValueError):plan('invalid')
        calls=[n.func.attr for n in ast.walk(ast.parse(source.read_text()))
               if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
        self.assertNotIn('add_hydra_engine',calls)
        self.assertNotIn('get_or_create_hydra_engine',calls)

    def test_released_texture_interface_is_a_failed_native_outcome(self):
        import importlib.util
        import sys
        from unittest.mock import patch
        from types import SimpleNamespace
        tool=Path(__file__).resolve().parents[1]/'tools/run_in_app_validation.py'
        spec=importlib.util.spec_from_file_location('validation_launcher',tool)
        module=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'package_extension':SimpleNamespace(package=None)}):
            spec.loader.exec_module(module)
        warning='Plugin interface for a client: omni.hydratexture.plugin was already released.'
        self.assertIn('released Hydra texture interface',module.native_failures(warning))
        self.assertEqual(module.native_failures('normal frame delivered'),[])

    def test_baseline_probe_never_creates_or_changes_a_stage_or_viewport(self):
        source=Path(__file__).resolve().parents[1]/'tools/in_app_baseline_probe.py'
        tree=ast.parse(source.read_text())
        attrs={n.func.attr for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)}
        self.assertFalse(attrs & {'create_context','new_stage_async','CreateInMemory','set_current_time','set_selected_prim_paths'})
        names={n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)}
        self.assertNotIn('ViewportWidget',names)
