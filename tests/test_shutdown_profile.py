"""CPU policy regression, never imports Kit or acquires any shared lease."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch,Mock

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('shutdown_policy',ROOT/'tools/shutdown_profile.py')
policy=importlib.util.module_from_spec(spec);spec.loader.exec_module(policy)


class ShutdownProfileTests(unittest.TestCase):
    def observed(self,variant='no-navigation'):
        profile,data=policy.load_profile(variant)
        nav=variant=='matched-full'
        report={'status':'passed','checks':[{'name':n,'passed':True} for n in policy.REQUIRED_CHECKS],
            'fixture_sha256':hashlib.sha256(data).hexdigest(),'file_close_callback':True,
            'stage_events':['CLOSING','CLOSED'],'navigation_control':{
                'core_enabled':nav,'recast_enabled':nav,'schema_enabled':True,'core_dll_loaded':nav}}
        process={'process_exit':0,'native_errors':[],'owned_process_reaped':True,
            'owned_job_empty':True,'owned_job_closed':True,'fixture_bytes_preserved':True,
            'shared_admission':{'admitted':True}}
        ids=profile['observation']['startup_extensions']+(profile['navigation_extension_ids'] if nav else [])
        log='\n'.join('[0s] [ext: '+name+'] startup' for name in ids)
        return profile,report,process,log

    def test_pinned_fixture_and_single_observation_are_explicit(self):
        profile,data=policy.load_profile('no-navigation')
        self.assertEqual(hashlib.sha256(data).hexdigest(),'7e91da55105e78d9f34bea389c11009715111737f3fb816280988b4ab1aa9da7')
        self.assertIn(b'\r\n',data)
        self.assertEqual(len(profile['observation']['startup_extensions']),426)
        self.assertEqual(profile['observation']['run_count'],1)
        self.assertEqual((profile['observation']['errors'],profile['observation']['warnings']),(82,824))
        self.assertFalse(profile['observation']['strict_clean_shutdown'])
        with self.assertRaises(ValueError):policy.load_profile('other')

    def test_fixture_tamper_fails_before_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'diagnostics').mkdir()
            (root/'diagnostics/isaac45-shutdown-v1.json').write_bytes((ROOT/'diagnostics/isaac45-shutdown-v1.json').read_bytes())
            (root/'diagnostics/shutdown-clean.usda').write_bytes(b'changed')
            with patch.object(policy,'ROOT',root),self.assertRaisesRegex(ValueError,'fixture changed'):
                policy.load_profile('no-navigation')

    def test_sdk_build_and_files_cannot_drift_silently(self):
        profile,_=policy.load_profile('no-navigation')
        with tempfile.TemporaryDirectory() as tmp:
            sdk=Path(tmp)
            files={'VERSION':profile['sdk_version_file'].encode(),
                   'apps/isaacsim.exp.full.kit':b'[package]\nversion="4.5.0"',
                   'apps/isaacsim.exp.base.kit':b'[package]\nversion="4.5.0"',
                   'kit/kit.exe':b'CPU fixture, never executed',
                   'kit/kernel/plugins/omni.kit.app.plugin.dll':b'CPU fixture, never loaded'}
            for name,data in files.items():
                path=sdk/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
            for name,version in profile['sdk_extension_versions'].items():
                path=sdk/'extscache'/(name+'-'+version)/'config/extension.toml'
                path.parent.mkdir(parents=True);path.write_text('[package]\nversion="'+version+'"')
            profile['sdk_files_sha256']={n:hashlib.sha256(files[n]).hexdigest() for n in profile['sdk_files_sha256']}
            policy.validate_sdk(sdk,profile)
            (sdk/'apps/isaacsim.exp.full.kit').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'SDK file differs'):policy.validate_sdk(sdk,profile)

    def test_missing_shared_admission_refuses_before_output_or_child(self):
        import sys
        from types import SimpleNamespace
        tool=ROOT/'tools/run_in_app_validation.py'
        spec=importlib.util.spec_from_file_location('safe_profile_launcher',tool)
        module=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'package_extension':SimpleNamespace(package=None)}):spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'must-not-exist'
            argv=[str(tool),'--isaac-root',tmp,'--output',str(output),'--full-app','--baseline',
                  '--shutdown-control','file-close','--shutdown-profile','no-navigation','--fail-fast-native']
            with patch.object(sys,'argv',argv),patch.object(module,'validate_sdk'),patch.object(module,'shared_admission',side_effect=ValueError('no active lease')),patch.object(module.subprocess,'Popen') as child:
                with self.assertRaisesRegex(ValueError,'no active lease'):module.main()
                child.assert_not_called();self.assertFalse(output.exists())

    def test_historical_errors_and_warnings_never_become_allowed_budget(self):
        profile,report,process,log=self.observed()
        log+='\n'+'\n'.join('[Error] [sdk] callback failure' for _ in range(82))
        log+='\n'+'\n'.join('[Warning] [sdk] cleanup warning' for _ in range(824))
        result=policy.assess(report,process,log,profile)
        self.assertTrue(result['native_exit_ok']);self.assertTrue(result['profile_conditions_met'])
        self.assertFalse(result['passed']);self.assertFalse(result['strict_clean_shutdown'])
        self.assertEqual(result['status'],'exited_with_diagnostics')
        self.assertEqual(result['log_summary']['error_lines'],82)
        self.assertEqual(result['log_summary']['warning_lines'],824)

    def test_each_profile_prerequisite_and_event_order_is_required(self):
        profile,report,process,log=self.observed()
        self.assertTrue(policy.assess(report,process,log,profile)['passed'])
        for field,value in (('fixture_bytes_preserved',False),('owned_process_reaped',False),
                            ('owned_job_empty',False),('owned_job_closed',False),
                            ('descendant_containment_required',True),('shared_admission',{})):
            changed={**process,field:value}
            self.assertFalse(policy.assess(report,changed,log,profile)['passed'],field)
        for events in ([],['CLOSED','CLOSING']):
            self.assertFalse(policy.assess({**report,'stage_events':events},process,log,profile)['passed'])
        missing={**report,'checks':report['checks'][:-1]}
        self.assertFalse(policy.assess(missing,process,log,profile)['passed'])

    def test_navigation_inventory_and_schema_cannot_be_silently_changed(self):
        profile,report,process,log=self.observed('matched-full')
        self.assertTrue(policy.assess(report,process,log,profile)['passed'])
        for key in ('core_enabled','recast_enabled','schema_enabled','core_dll_loaded'):
            changed=copy.deepcopy(report);changed['navigation_control'][key]=False
            self.assertFalse(policy.assess(changed,process,log,profile)['passed'],key)
        self.assertFalse(policy.assess(report,process,log+'\n[1s] [ext: unrelated-1.0] startup',profile)['passed'])

    def test_native_failure_nonzero_and_unstructured_cleanup_are_not_success(self):
        profile,report,process,log=self.observed()
        for changes in ({'process_exit':1},{'native_errors':['native crash']},{'timed_out':True},
                        {'termination':'contained owned Job'}):
            self.assertFalse(policy.assess(report,{**process,**changes},log,profile)['passed'])
        for text in ('Traceback (most recent call last)','Leaking graphics objects',
                     'had 1 outstanding SimStageWithHistory'):
            self.assertFalse(policy.assess(report,process,log+'\n'+text,profile)['passed'])

    def test_lease_requires_active_owned_lineage_lock_and_idle_resources(self):
        metadata={'owner':'USDSceneReview-test','state':'running','leaseId':'test-id','wrapperPid':1,'childPid':2}
        processes=[{'ProcessId':1,'ParentProcessId':0,'Name':'pwsh.exe'},
                   {'ProcessId':2,'ParentProcessId':1,'Name':'python.exe'},
                   {'ProcessId':3,'ParentProcessId':2,'Name':'python.exe'}]
        gpu=[['3','1771','12288']]
        self.assertTrue(policy.validate_admission(metadata,processes,3,True,gpu,[])['admitted'])
        for changes in ({'state':'completed'},{'owner':'RL-other'},{'leaseId':''},{'childPid':99},{'wrapperPid':2}):
            with self.assertRaises(ValueError):policy.validate_admission({**metadata,**changes},processes,3,True,gpu,[])
        for exclusive,resources,blockers,extra in ((False,gpu,[],[]),(True,[['80','1771','12288']],[],[]),
                (True,gpu,[{'pid':9}],[]),(True,gpu,[],[{'ProcessId':9,'ParentProcessId':0,'Name':'kit.exe'}])):
            with self.assertRaises(ValueError):policy.validate_admission(metadata,processes+extra,3,exclusive,resources,blockers)

    def test_unknown_gpu_clients_fail_closed_not_ignored(self):
        rows=[['4','[Insufficient Permissions]'],['9','[Insufficient Permissions]']]
        snapshot=[{'ProcessId':4,'Name':'System'},{'ProcessId':9,'Name':'python.exe'}]
        self.assertEqual(policy.unmanaged_clients(rows,snapshot,3),[{'pid':9,'name':'python.exe'}])
        self.assertEqual(policy.unmanaged_clients([['10','[Insufficient Permissions]']],[],3),[{'pid':10,'name':'unresolved'}])
        with self.assertRaises(ValueError):policy.unmanaged_clients([['bad']],[],3)

    def test_owned_job_descendant_cleanup_is_not_natural_success(self):
        job=Mock()
        with patch.object(policy,'job_count',side_effect=[1,0,0]):result=policy.finish_job(job)
        job.terminate.assert_called_once();job.close.assert_called_once()
        self.assertTrue(result['owned_job_empty']);self.assertTrue(result['descendant_containment_required'])
        job=Mock()
        with patch.object(policy,'job_count',return_value=0):result=policy.finish_job(job)
        job.terminate.assert_not_called();self.assertFalse(result['descendant_containment_required'])

    @unittest.skipUnless(os.name=='nt','Windows Job API CPU integration')
    def test_real_owned_cpu_job_count_and_reap(self):
        import subprocess,sys
        from usd_scene_review.worker_client import WindowsJob,resume_owned_process
        process=subprocess.Popen([sys.executable,'-B','-c','pass'],creationflags=4)
        job=None
        try:
            job=WindowsJob(process)
            self.assertEqual(policy.job_count(job),1)
            resume_owned_process(process)
            self.assertEqual(process.wait(timeout=10),0)
            receipt=policy.finish_job(job)
            self.assertTrue(receipt['owned_job_empty']);self.assertTrue(receipt['owned_job_closed'])
            self.assertFalse(receipt['descendant_containment_required'])
        finally:
            if process.poll() is None:
                if job:job.terminate()
                else:process.kill()
                process.wait(timeout=10)
            if job:job.close()
