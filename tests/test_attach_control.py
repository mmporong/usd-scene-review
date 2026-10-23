"""CPU contracts for matched no-render attach controls; never starts Kit."""
import ast
import copy
import contextlib
import io
import importlib.util
from pathlib import Path
import unittest
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('attach_policy',ROOT/'tools/shutdown_profile.py')
policy=importlib.util.module_from_spec(spec);spec.loader.exec_module(policy)


class AttachControlTests(unittest.TestCase):
    def test_open_fixture_is_independent_exact_bytes_and_never_overwritten(self):
        spec=importlib.util.spec_from_file_location('owned_open_copy',ROOT/'tools/attach_only_control.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source.usda';destination=Path(tmp)/'owned.usda'
            source.write_bytes(b'owned fixture\r\n')
            digest=module.prepare_open_fixture(source,destination)
            import hashlib
            self.assertEqual(digest,hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(source.read_bytes(),destination.read_bytes())
            with self.assertRaises(FileExistsError):module.prepare_open_fixture(source,destination)
            self.assertEqual(source.read_bytes(),b'owned fixture\r\n')
    def test_unpinned_full_and_combined_candidate_controls_fail_before_admission(self):
        path=ROOT/'tools/run_in_app_validation.py'
        spec=importlib.util.spec_from_file_location('attach_control_launcher',path)
        module=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'package_extension':SimpleNamespace(package=None)}):spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'never-created'
            base=[str(path),'--isaac-root',tmp,'--output',str(output),'--full-app','--baseline',
                  '--shutdown-control','file-close','--fail-fast-native','--attach-control','attach']
            for extra in ([],['--shutdown-profile','matched-full'],
                          ['--shutdown-profile','no-navigation','--shutdown-candidate','viewport-reuse']):
                with patch.object(sys,'argv',base+extra),patch.object(module,'shared_admission') as admission,contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as error:module.main()
                    self.assertEqual(error.exception.code,2);admission.assert_not_called()
                    self.assertFalse(output.exists())

    def test_fixed_update_budget_has_no_viewport_capture_or_pending_mutations(self):
        source=(ROOT/'tools/attach_only_control.py').read_text()
        tree=ast.parse(source)
        attrs={node.func.attr for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)}
        names={node.func.id for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name)}
        self.assertFalse(attrs & {'set_pending_edit','post_quit','post_uncancellable_quit','save','set_selected_prim_paths'})
        self.assertFalse(names & {'ViewportWidget','capture_viewport_to_file','create_viewport_window'})
        assignments={node.targets[0].id:node.value.value for node in tree.body if isinstance(node,ast.Assign)
                     and isinstance(node.targets[0],ast.Name) and isinstance(node.value,ast.Constant)}
        self.assertEqual(assignments['UPDATE_BUDGET'],60)
        self.assertIn('range(UPDATE_BUDGET)',source)
        self.assertIn("if mode=='attach':task=asyncio.ensure_future(ctx.attach_stage_async(stage))",source)

    def test_qualification_requires_matched_budget_and_real_cleanup(self):
        profile,data=policy.load_profile('no-navigation');profile['attach_control']='wait'
        report={'status':'passed','checks':[{'name':name,'passed':True} for name in policy.REQUIRED_CHECKS],
                'fixture_sha256':profile['fixture_sha256'],'file_close_callback':True,'stage_events':['CLOSING','CLOSED'],
                'navigation_control':{'core_enabled':False,'recast_enabled':False,'schema_enabled':True,'core_dll_loaded':False},
                'attach_control':{'mode':'wait','status':'passed','update_budget':60,'updates_completed':60,
                                  'owned_resources_remaining':False,'default_pending_preserved':True,'checks':[{'passed':True}]}}
        process={'process_exit':0,'native_errors':[],'owned_process_reaped':True,'owned_job_empty':True,
                 'owned_job_closed':True,'fixture_bytes_preserved':True,'shared_admission':{'admitted':True}}
        log='\n'.join('[0s] [ext: '+name+'] startup' for name in profile['observation']['startup_extensions'])
        self.assertTrue(policy.assess(report,process,log,profile)['passed'])
        for field,value in (('updates_completed',59),('owned_resources_remaining',True),('mode','attach'),('checks',[]),('default_pending_preserved',False)):
            changed=copy.deepcopy(report);changed['attach_control'][field]=value
            self.assertFalse(policy.assess(changed,process,log,profile)['passed'])
        report['attach_control'].update(mode='attach');profile['attach_control']='attach'
        self.assertFalse(policy.assess(report,process,log,profile)['passed'])
        report['attach_control']['owned_stage_closed']=True
        self.assertTrue(policy.assess(report,process,log,profile)['passed'])
        report['attach_control']['mode']='open';profile['attach_control']='open'
        self.assertFalse(policy.assess(report,process,log,profile)['passed'])
        report['attach_control']['owned_fixture_preserved']=True
        self.assertTrue(policy.assess(report,process,log,profile)['passed'])
