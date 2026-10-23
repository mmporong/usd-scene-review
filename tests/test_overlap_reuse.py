"""Pair-loop equivalence goldens captured from the pre-optimization implementation."""
import copy
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from usd_scene_review import compare,create_snapshot,load_snapshot
from usd_scene_review.analysis_config import normalize
from usd_scene_review.snapshot import canonical
from usd_scene_review import overlap_analysis as engine
from pxr import Usd,UsdGeom

ROOT=Path(__file__).resolve().parents[1]


def corpus(partial=False):
    def known(path,lo,hi):return {'path':path,'status':'known','bounds_m':[lo,hi],'bounds_stage':[lo,hi],'point_count':8}
    a={};b={}
    boxes={'/W/A':([-1.,-1.,-1.],[1.,1.,1.]),'/W/A/Child':([-.25]*3,[.25]*3),
           '/W/B':([3.,-1.,-1.],[5.,1.,1.]),'/W/Boundary':([1.,-1.,-1.],[3.,1.,1.]),
           '/W/Far':([1e150]*3,[2e150]*3),'/W/Huge':([-1.7e308,-1.,-1.],[1.7e308,1.,1.]),
           '/W/Huge2':([-1.7e308,-1.,-1.],[1.7e308,1.,1.]),'/W/Tiny':([-1e-300]*3,[1e-300]*3)}
    for path,(lo,hi) in boxes.items():a[path]=known(path,lo,hi);b[path]=copy.deepcopy(a[path])
    b['/W/B']=known('/W/B',[.5,-1.,-1.],[2.5,1.,1.])
    b['/W/Boundary']=known('/W/Boundary',[1.-5e-7,-1.,-1.],[3.-5e-7,1.,1.])
    b['/W/Huge2']=known('/W/Huge2',[-.1]*3,[.1]*3)
    b['/W/Tiny']=known('/W/Tiny',[0.]*3,[0.]*3)
    for path in ('/W/Added','/W/Blocked/Leaf','/W/NonGeometry'):
        b[path]=known(path,[-.1]*3,[.1]*3)
    a['/W/Removed']=known('/W/Removed',[-.1]*3,[.1]*3)
    a['/W/Hidden']={'status':'unknown','reason':'hidden'};b['/W/Hidden']=known('/W/Hidden',[-.1]*3,[.1]*3)
    scans=[]
    for index,records in enumerate((a,b)):
        scans.append({'records':records,'observed_paths':set(records)|({'/W/NonGeometry','/W/Blocked'} if index==0 else set()),
            'blocked':{'/W/Blocked':'unsupported-ancestor'} if index==0 else {},
            'coverage':{'status':'partial' if partial and index==0 else 'complete'}})
    return scans


def scenarios():
    metadata={'meters_per_unit':{'before':1.,'after':1.},'up_axis':{'before':'Z','after':'Z'}}
    result=[]
    for name,partial,pairs,records,tolerance,mismatch in (
        ('complete',False,1000000,20000,1e-6,False),('pairs',False,7,20000,1e-6,False),
        ('records',False,1000000,2,1e-6,False),('partial',True,1000000,20000,1e-6,False),
        ('units',False,1000000,20000,1e-6,True),('tolerance',False,1000000,20000,1e-8,False)):
        config=normalize();config['overlap'].update(max_pairs=pairs,max_records=records,tolerance_m=tolerance)
        meta=copy.deepcopy(metadata)
        if mismatch:meta['up_axis']['after']='Y'
        result.append((name,corpus(partial),meta,config))
    return result


class OverlapReuseTests(unittest.TestCase):
    def test_reference_goldens_keep_ids_budgets_unknowns_focus_and_numeric_edges(self):
        expected=json.loads((ROOT/'tests/fixtures/overlap-reuse-v1.json').read_text())
        for name,scans,metadata,config in scenarios():
            with self.subTest(name=name),patch.object(engine,'_scan',side_effect=lambda snapshot,config:scans[snapshot]):
                result=engine.analyze_overlaps(0,1,metadata,config)
                self.assertEqual(hashlib.sha256(canonical(result).encode()).hexdigest(),expected[name])

    def test_ulp_and_object_work_is_per_path_and_not_reused_between_calls(self):
        metadata={'meters_per_unit':{'before':1.,'after':1.},'up_axis':{'before':'Z','after':'Z'}}
        records={f'/W/C{index}':{'status':'known','bounds_m':[[index*4.,0.,0.],[index*4.+1.,1.,1.]],
            'bounds_stage':[[index*4.,0.,0.],[index*4.+1.,1.,1.]]} for index in range(32)}
        scan={'records':records,'observed_paths':set(records),'blocked':{},'coverage':{'status':'complete'}}
        real_ulp=math.ulp;real_object=engine._object
        with patch.object(engine,'_scan',return_value=scan),patch.object(engine.math,'ulp',wraps=real_ulp) as ulp,patch.object(engine,'_object',wraps=real_object) as obj:
            report=engine.analyze_overlaps(None,None,metadata)
            self.assertEqual(report['coverage']['pairs_examined'],496)
            self.assertLessEqual(ulp.call_count,32*2*6);self.assertLessEqual(obj.call_count,32*2)
        config=normalize();config['overlap']['max_pairs']=1
        with patch.object(engine,'_scan',return_value=scan),patch.object(engine,'_object',wraps=real_object) as obj:
            engine.analyze_overlaps(None,None,metadata,config)
            self.assertLessEqual(obj.call_count,4) # do not prepare the unvisited tail
        records['/W/C1']['bounds_m']=copy.deepcopy(records['/W/C0']['bounds_m'])
        with patch.object(engine,'_scan',return_value=scan):
            self.assertTrue(engine.analyze_overlaps(None,None,metadata)['pairs'])

    def test_frozen_file_mutation_is_still_unknown_on_next_compare(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);paths=[]
            for side in ('A','B'):
                folder=root/side;folder.mkdir();source=folder/'scene.usda';stage=Usd.Stage.CreateNew(str(source))
                UsdGeom.SetStageMetersPerUnit(stage,1);UsdGeom.SetStageUpAxis(stage,'Z')
                UsdGeom.Cube.Define(stage,'/Item');stage.GetRootLayer().Save();stage=None
                paths.append(create_snapshot(source,root/('snapshot-'+side)))
            self.assertEqual(compare(*paths)['status'],'equal')
            frozen=load_snapshot(paths[1]).root;frozen.write_text(frozen.read_text()+'\n# changed bytes\n')
            self.assertEqual(compare(*paths)['status'],'unknown')
