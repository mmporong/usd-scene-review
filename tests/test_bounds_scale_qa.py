import ast
import copy
import importlib.util
import json
import tempfile
from pathlib import Path
import unittest
from usd_scene_review import compare

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('bounds_scale_qa',ROOT/'tools/viewport_bounds_scale_qa.py')
qa=importlib.util.module_from_spec(spec);spec.loader.exec_module(qa)


class BoundsScaleQaTests(unittest.TestCase):
    def test_native_thirty_cycle_record_keeps_cleanup_and_limits_explicit(self):
        record=json.loads((ROOT/'diagnostics/bounds-stability-30-v1.json').read_text())
        self.assertTrue(qa.stability_metrics_complete(record['scales']))
        self.assertEqual(record['candidate_checks'],len(qa.check_names((2048,),33)))
        self.assertEqual(record['shutdown']['process_exit'],0)
        self.assertTrue(record['shutdown']['profile_conditions_met'])
        self.assertFalse(record['shutdown']['strict_clean_shutdown'])
        self.assertTrue(record['lease']['admitted_exclusively']);self.assertTrue(record['lease']['naturally_released'])
        self.assertFalse(record['shutdown']['descendant_containment_required'])
        self.assertFalse(record['limits']['real_mouse_tested']);self.assertFalse(record['limits']['long_duration_operation_qualified'])
        self.assertFalse(record['limits']['stock_full_shutdown_qualified']);self.assertFalse(record['limits']['live_ab_guard_removed'])

    def test_stability_guard_stops_retention_or_steep_growth_not_allocator_noise(self):
        def sample(value):return {'memory':{'private':value},'live_tracked_scene_views':0,'owned_subscriptions':0,'owned_overlay_cleared':True}
        self.assertIsNone(qa.stability_stop([sample(1000),sample(2000),sample(1500)]))
        self.assertEqual(qa.stability_stop([sample(1),sample(513*1024**2)]),'private-growth-over-512-MiB')
        self.assertEqual(qa.stability_stop([sample((index+1)*30*1024**2) for index in range(6)]),'five-consecutive-increases-over-128-MiB')
        for key,value in (('live_tracked_scene_views',1),('owned_subscriptions',1),('owned_overlay_cleared',False)):
            changed=sample(1000);changed[key]=value
            self.assertEqual(qa.stability_stop([changed]),'owned-resource-retained')

    def test_stability_has_three_warmup_plus_thirty_measured_cycles(self):
        self.assertEqual((qa.STABILITY_WARMUP,qa.STABILITY_CYCLES),(3,30))
        names=qa.check_names((2048,),33)
        self.assertIn('resources cleared 2048/32',names)
        self.assertNotIn('resources cleared 32/0',names)
        rows=[{'count':2048,'selection_ms':[1]*132,'selection_to_two_frames_ms':[2]*132,'open_ms':[3]*33,'close_ms':[1]*33,
            'viewports_expected':1,'cleanup':[{'owned_overlay_cleared':True,'live_tracked_scene_views':0,'viewports':1,
                'memory':{'working_set':1000,'private':2000}} for _ in range(33)]}]
        self.assertTrue(qa.metrics_complete(rows,(2048,),33))
        self.assertFalse(qa.stability_metrics_complete(rows))
        for index,sample in enumerate(rows[0]['cleanup']):
            sample.update(cycle=index,phase='warmup' if index<3 else 'measured',cycle_ms=1000,
                          owned_subscriptions=0,active_owned_subscriptions=2,active_owned_scene_views=1)
        self.assertTrue(qa.stability_metrics_complete(rows))
        rows[0]['cleanup'][20]['owned_subscriptions']=1
        self.assertFalse(qa.stability_metrics_complete(rows))
        rows[0]['cleanup'].pop();self.assertFalse(qa.metrics_complete(rows,(2048,),33))

    def test_measured_record_keeps_mouse_and_deployment_limits_explicit(self):
        record=json.loads((ROOT/'diagnostics/bounds-scale-qa-v1.json').read_text())
        for name in ('before','after'):
            run=record[name]
            self.assertTrue(qa.metrics_complete(run['scales']))
            self.assertEqual((run['candidate_checks'],run['outer_checks']),(37,19))
            self.assertEqual((run['process_exit'],run['wrapper_exit']),(0,2))
            self.assertFalse(run['strict_clean_shutdown']);self.assertFalse(run['manual_mouse_tested'])
            self.assertTrue(run['shared_lock_naturally_released']);self.assertFalse(run['descendant_containment_required'])
        self.assertFalse(record['limits']['production_assets_tested']);self.assertFalse(record['limits']['long_soak_tested'])

    def test_missing_nonfinite_or_retained_resource_metrics_cannot_pass(self):
        rows=[{'count':count,'selection_ms':[1]*12,'selection_to_two_frames_ms':[2]*12,'open_ms':[3]*3,'close_ms':[1]*3,
            'viewports_expected':1,'cleanup':[{'owned_overlay_cleared':True,'live_tracked_scene_views':0,'viewports':1,
                'memory':{'working_set':1000,'private':2000}} for _ in range(3)]} for count in qa.SCALES]
        self.assertTrue(qa.metrics_complete(rows))
        changed=copy.deepcopy(rows);changed[1]['selection_ms'][0]=float('nan');self.assertFalse(qa.metrics_complete(changed))
        changed=copy.deepcopy(rows);changed[1]['cleanup'][0]['live_tracked_scene_views']=1;self.assertFalse(qa.metrics_complete(changed))
        changed=copy.deepcopy(rows);changed[1]['cleanup'].pop();self.assertFalse(qa.metrics_complete(changed))
        self.assertFalse(qa.metrics_complete(rows[:1]))

    def test_source_geometry_is_deterministic_and_only_eight_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);first=qa.build_scale(root/'first',32);qa.build_scale(root/'second',32)
            for side in ('A','B'):
                self.assertEqual((root/'first'/('source-'+side)/'scene.usda').read_bytes(),(root/'second'/('source-'+side)/'scene.usda').read_bytes())
            report=compare(first['paths']['A'],first['paths']['B'])
            self.assertEqual(len(report['changes']),8)
            self.assertEqual((root/'first/working.usda').read_bytes(),(root/'first/source-B/scene.usda').read_bytes())

    def test_fixture_budget_and_latency_summary_do_not_fake_samples(self):
        with tempfile.TemporaryDirectory() as tmp:
            for count in (0,7,2056,32.0):
                with self.assertRaises(ValueError):qa.build_scale(Path(tmp)/str(count),count)
        values=[8,1,4,2];self.assertEqual(qa.latency_summary(values),{'samples':4,'min_ms':1,'median_ms':3,'max_ms':8})
        self.assertEqual(values,[8,1,4,2]);self.assertEqual(qa.SCALES,(32,2048));self.assertEqual(qa.CYCLES,3)

    def test_native_evaluation_never_authors_usd_or_controls_user_selection(self):
        tree=ast.parse((ROOT/'tools/viewport_bounds_scale_qa.py').read_text())
        evaluate=next(node for node in tree.body if isinstance(node,ast.AsyncFunctionDef) and node.name=='evaluate')
        calls={node.func.attr for node in ast.walk(evaluate) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)}
        self.assertFalse(calls & {'Save','DefinePrim','SetEditTarget','set_pending_edit','set_selected_prim_paths','set_current_time','create_context','attach_stage_async','post_quit'})
        self.assertIn('open_stage_async',calls)
