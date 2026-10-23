"""Test-only guard access must not escape the disposable host's operation."""
import ast
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock


class ProbeGuardTests(unittest.IsolatedAsyncioTestCase):
    def helper(self,opt_in):
        path=Path(__file__).resolve().parents[1]/'tools/in_app_integration_probe.py'
        tree=ast.parse(path.read_text(encoding='utf-8'))
        node=next(n for n in ast.walk(tree) if isinstance(n,ast.AsyncFunctionDef) and n.name=='open_review')
        blocked=lambda:True
        module=NS(full_host_blocked=blocked)
        owner=NS(_in_app_blocked=True,_open_in_app=AsyncMock())
        def check(name,ok):self.assertTrue(ok,name)
        env={'owner':owner,'in_app':module,'check':check,
             'carb':NS(settings=NS(get_settings=lambda:NS(get=lambda key:opt_in)))}
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),env)
        return env['open_review'],owner,module,blocked

    async def test_full_host_refused_without_explicit_probe_opt_in(self):
        helper,owner,module,blocked=self.helper(False)
        with self.assertRaisesRegex(RuntimeError,'opt-in'):await helper()
        owner._open_in_app.assert_not_awaited()
        self.assertTrue(owner._in_app_blocked);self.assertIs(module.full_host_blocked,blocked)

    async def test_guard_restored_after_success_or_failed_test_opening(self):
        for failure in (False,True):
            helper,owner,module,blocked=self.helper(True)
            async def opening():
                self.assertFalse(owner._in_app_blocked);self.assertFalse(module.full_host_blocked())
                if failure:raise ValueError('fixture failed')
            owner._open_in_app.side_effect=opening
            if failure:
                with self.assertRaises(ValueError):await helper()
            else:await helper()
            owner._open_in_app.assert_awaited_once()
            self.assertTrue(owner._in_app_blocked);self.assertIs(module.full_host_blocked,blocked)


class FullHostIdentityTests(unittest.TestCase):
    def test_filename_suffix_and_enabled_full_experience_are_guarded(self):
        path=Path(__file__).resolve().parents[1]/'exts/mmporong.scene.review/mmporong/scene/review/in_app.py'
        node=next(n for n in ast.parse(path.read_text(encoding='utf-8')).body
                  if isinstance(n,ast.FunctionDef) and n.name=='full_host_blocked')
        for filename,full,expected in [('isaacsim.exp.full',False,True),
                ('E:/apps/ISAACSIM.EXP.FULL.KIT',False,True),
                ('derived-review.kit',True,True),('minimal.kit',False,False)]:
            app=NS(get_app_filename=lambda:filename,
                   get_extension_manager=lambda:NS(is_extension_enabled=lambda name:full))
            env={'omni':NS(kit=NS(app=NS(get_app=lambda:app)))}
            exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),env)
            self.assertEqual(env['full_host_blocked'](),expected)
