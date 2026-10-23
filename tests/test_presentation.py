from usd_scene_review.presentation import inherited_only, visible_changes, summary, details
import unittest


class PresentationTests(unittest.TestCase):
    def test_only_pure_inherited_motion_is_collapsed(self):
        inherited = dict(path='/World/Child', provenance='parent-propagated', fields={'world': {}}, authored={})
        own = dict(inherited, path='/World/Mixed', fields={'world': {}, 'visibility': {}})
        authored = dict(inherited, path='/World/Authored', authored={'x': {}})
        report = {'changes': [inherited, own, authored]}
        self.assertTrue(inherited_only(inherited))
        self.assertEqual(visible_changes(report), [own, authored])
        self.assertEqual(visible_changes(report, 'child', True), [inherited])
        self.assertEqual(len(visible_changes(report, include_inherited=True)), 3)

    def test_summary_and_unknown_have_actions_without_clearance_claim(self):
        report = dict(status='unknown', changes=[], reasons=['bundle hash mismatch'], policy=[])
        self.assertIn('bundle hash mismatch', summary(report))
        self.assertIn('Clash is unavailable', summary(report))
        result = details(dict(kind='unobserved', world_delta=dict(status='unknown', reason='scale/shear')))
        self.assertIn('try the other revision', result)
        self.assertIn('no rigid pass', result)
