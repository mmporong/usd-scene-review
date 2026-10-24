import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('signatures',ROOT/'tools/classify_shutdown_errors.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


class SignatureTests(unittest.TestCase):
    def test_saved_audit_reconciles_all_errors_and_baseline_signatures(self):
        record=json.loads((ROOT/'diagnostics/shutdown-signature-audit-v1.json').read_text())
        self.assertEqual([record['runs'][name]['error_lines'] for name in ('no_project_baseline','triangle_faces','polygon_faces')],[82,8,100])
        self.assertEqual(sum(record['polygon_minus_triangle'].values()),92)
        self.assertFalse(record['polygon_signatures_absent_from_no_project_baseline'])
        self.assertFalse(record['runs']['no_project_baseline']['review_startup_observed'])
        for run in record['runs'].values():
            self.assertEqual(sum(row['count'] for row in run['signatures'].values()),run['error_lines'])
            self.assertEqual(run['unclassified_errors'],0);self.assertEqual(run['source_project_frames'],0)
            self.assertTrue(all(row['after_shutdown_begin']==row['count'] for row in run['signatures'].values()))
        self.assertFalse(record['runs']['polygon_faces']['strict_clean_shutdown'])

    def test_repeated_menu_errors_count_separately_and_known_does_not_mean_clean(self):
        text='[1.000s] [ext: mmporong.scene.review-0.1.0] shutdown\n[2.000s] [ext: omni.usd-1.12.4] shutdown\n'
        text+="2026-10-24 00:00:00 [2,100ms] [Error] [omni.kit.menu.utils.app_menu] Error 'NoneType' object has no attribute 'get_selection' creating menu <MenuItemDescription name:'Group'>\n"*4
        text+='  File "C:/SDK/isaac-sim-4.5.0/exts/isaacsim.gui.menu/edit_menu.py", line 4, in prim_selected\n'
        result=audit.classify(text);row=result['signatures']['menu.none_selection']
        self.assertEqual(result['error_lines'],4);self.assertEqual(row['count'],4)
        self.assertEqual(row['after_usd_shutdown'],4);self.assertEqual(row['menu_items'],{'Group':4})
        self.assertIn('exts/isaacsim.gui.menu/edit_menu.py :: prim_selected',row['frames'])
        self.assertNotIn('passed',result);self.assertNotIn('strict_clean_shutdown',result)

    def test_unclassified_project_trace_is_retained_without_private_paths(self):
        text='2026-10-24 00:00:00 [1ms] [Error] [app] Unexpected failure\n  File "C:/Private/repo/usd_scene_review/polygon_faces.py", line 9, in triangulate\n'
        result=audit.classify(text);self.assertEqual(result['unclassified_errors'],1)
        self.assertTrue(result['signatures']['unclassified']['project_frame_observed'])
        self.assertNotIn('Private',str(result));self.assertNotIn('Unexpected failure',str(result))
        sdk=text.replace('C:/Private/repo','C:/SDK/isaac-sim-4.5.0/exts/example/python')
        self.assertTrue(audit.classify(sdk)['signatures']['unclassified']['project_frame_observed'])
