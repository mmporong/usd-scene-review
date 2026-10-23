import copy
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from usd_scene_review.dispositions import change_identity, record, history, latest


class DispositionTests(unittest.TestCase):
    def test_bound_identity_history_and_independent_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); a = root/'A'; b = root/'B'; a.mkdir(); b.mkdir()
            for folder in (a, b): (folder/'manifest.json').write_text('{}')
            source = {p: p.read_bytes() for folder in (a,b) for p in folder.iterdir()}
            report = {'changes': [{'path':'/World/Part', 'fields':{'world': {'before':1,'after':2}}}],
                      'policy':[{'path':'/World/Part','status':'fail'}, {'path':'/World/Part','status':'unknown'}]}
            unchanged = copy.deepcopy(report)
            hashes = {'A':'a'*64,'B':'b'*64}; identity = change_identity(hashes,report['changes'][0])
            log=root/'review.jsonl'
            record(log, identity, 'intentional', 'Required fixture relocation', forbidden_roots=(a,b))
            self.assertEqual(latest(history(log),identity)['disposition'],'intentional')
            changed=change_identity(dict(hashes,B='c'*64),report['changes'][0])
            self.assertIsNone(latest(history(log),changed))
            changed_record=copy.deepcopy(report['changes'][0]);changed_record['fields']['world']['after']=3
            self.assertIsNone(latest(history(log),change_identity(hashes,changed_record)))
            record(log, identity, 'needs-review', 'Confirm relocation with layout owner', forbidden_roots=(a,b))
            events=history(log); self.assertEqual(len(events),2)
            self.assertEqual(events[0]['disposition'],'intentional')
            self.assertEqual(latest(events,identity)['disposition'],'needs-review')
            self.assertEqual(report,unchanged)
            self.assertEqual([p['status'] for p in report['policy']],['fail','unknown'])
            self.assertEqual(source,{p:p.read_bytes() for p in source})
            with self.assertRaises(ValueError): record(a/'review.jsonl',identity,'intentional','reason',forbidden_roots=(a,b))
            self.assertFalse((a/'review.jsonl').exists())

    def test_unicode_reason_roundtrip_and_preappend_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            log=Path(tmp)/'review.jsonl'; identity=change_identity({'A':'a'*64,'B':'b'*64},{'path':'/Part'})
            reason='User reason: first\u2028second\u2029third\u0085fourth'
            record(log,identity,'intentional',reason)
            self.assertEqual(history(log)[0]['reason'],reason)
            before=log.read_bytes()
            with patch('usd_scene_review.dispositions.MAX_BYTES',len(before)+1):
                with self.assertRaises(ValueError): record(log,identity,'needs-review','Confirm')
            self.assertEqual(log.read_bytes(),before)
            self.assertEqual(len(history(log)),1)

    def test_real_usd_policy_fail_and_unknown_survive_intentional_record(self):
        import hashlib
        from pxr import Usd, UsdGeom
        from usd_scene_review import create_snapshot, compare
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); manifests={}; sources=[]
            for side, offset in (('A',0),('B',2)):
                folder=root/(side+'-source');folder.mkdir();source=folder/'scene.usda'
                stage=Usd.Stage.CreateNew(str(source))
                UsdGeom.Xform.Define(stage,'/World').AddTranslateOp().Set((offset,0,0))
                UsdGeom.Cube.Define(stage,'/World/Scaled').AddScaleOp().Set((2,1,1))
                stage.GetRootLayer().Save();sources.append(source)
                manifests[side]=create_snapshot(source,root/side)
            hashes={side:hashlib.sha256(path.read_bytes()).hexdigest() for side,path in manifests.items()}
            before={path:path.read_bytes() for path in sources}
            report=compare(manifests['A'],manifests['B'],policy={'max_translation':.5})
            unchanged=copy.deepcopy(report)
            self.assertEqual({p['status'] for p in report['policy']},{'fail','unknown'})
            for change in report['changes']:
                record(root/'review.jsonl',change_identity(hashes,change),'intentional','Planned test relocation',
                       forbidden_roots=[path.parent for path in manifests.values()])
            self.assertEqual(report,unchanged)
            self.assertEqual(compare(manifests['A'],manifests['B'],policy={'max_translation':.5}),report)
            self.assertEqual(before,{path:path.read_bytes() for path in sources})

    def test_invalid_or_busy_history_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            log=Path(tmp)/'review.jsonl'; identity=change_identity({'A':'a'*64,'B':'b'*64},{'path':'/Part'})
            with self.assertRaises(ValueError): record(log,identity,'intentional','  ')
            self.assertFalse(log.exists())
            log.write_text('{partial')
            with self.assertRaises(ValueError): record(log,identity,'needs-review','Check')
            self.assertEqual(log.read_text(),'{partial')
            log.with_name(log.name+'.lock').write_text('owned')
            with self.assertRaises(FileExistsError): history(log)
            self.assertEqual(log.with_name(log.name+'.lock').read_text(),'owned')
