"""Filtered evidence navigation never owns the viewport or changes report data."""
import ast
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock
from usd_scene_review.presentation import visible_changes, adjacent_change, CHANGE_KINDS


class ChangeNavigationTests(unittest.TestCase):
    def setUp(self):
        self.report = {'changes': [
            {'path':'/World/A','kind':'added'},
            {'path':'/World/Old','kind':'removed'},
            {'path':'/World/Child','kind':'modified','provenance':'parent-propagated',
             'fields':{'world':{}},'authored':{}},
            {'path':'/World/Unknown','kind':'unobserved'},
            {'path':'/World/Moved','kind':'modified'}]}

    def test_filters_compose_without_reordering_or_mutation(self):
        original = deepcopy(self.report)
        self.assertEqual([c['path'] for c in visible_changes(self.report,' WORLD/ ',True,'modified')],
                         ['/World/Child','/World/Moved'])
        self.assertEqual([c['path'] for c in visible_changes(self.report,'world',False,'modified')],['/World/Moved'])
        for kind in CHANGE_KINDS[1:]:
            self.assertTrue(all(c['kind']==kind for c in visible_changes(self.report,include_inherited=True,kind=kind)))
        self.assertEqual(visible_changes(self.report,'absent'),[])
        self.assertEqual(self.report,original)
        with self.assertRaises(ValueError):visible_changes(self.report,kind='typo')

    def test_edges_hidden_selection_and_no_wrap(self):
        changes=visible_changes(self.report)
        self.assertIs(adjacent_change(changes,None,1),changes[0])
        self.assertIs(adjacent_change(changes,'/Hidden',-1),changes[-1])
        self.assertIsNone(adjacent_change(changes,changes[0]['path'],-1))
        self.assertIsNone(adjacent_change(changes,changes[-1]['path'],1))
        self.assertIs(adjacent_change(changes,changes[0]['path'],1),changes[1])
        self.assertIsNone(adjacent_change([],None,1))
        with self.assertRaises(ValueError):adjacent_change(changes,None,0)

    def test_actual_callback_routes_only_matching_rows_and_retains_at_boundary(self):
        path=Path(__file__).resolve().parents[1]/'exts/mmporong.scene.review/mmporong/scene/review/extension.py'
        tree=ast.parse(path.read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef))
        node=ast.ClassDef(name='Router',bases=[],keywords=[],decorator_list=[],body=[
            n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in ('_visible_changes','_navigate_change')])
        env=dict(visible_changes=visible_changes,adjacent_change=adjacent_change,CHANGE_KINDS=CHANGE_KINDS)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(path),'exec'),env)
        item=env['Router']();item._report=self.report;item._shutting_down=False;item._selected=None
        index=NS(as_int=CHANGE_KINDS.index('modified'))
        item._kind_filter=NS(model=NS(get_item_value_model=lambda:index))
        item._query=NS(as_string='');item._inherited=NS(as_bool=False)
        item._message=Mock();item._select=Mock(side_effect=lambda c:setattr(item,'_selected',c['path']))
        item._navigate_change(1)
        self.assertEqual(item._selected,'/World/Moved')
        item._navigate_change(1);self.assertEqual(item._select.call_count,1)
        self.assertIn('No wrap',item._message.call_args.args[0])
        item._query.as_string='missing';item._navigate_change(-1)
        self.assertEqual(item._select.call_count,1)
        self.assertEqual(item._message.call_args.args[0],'No matching changes.')
        item._report=None;item._navigate_change(1)
        self.assertEqual(item._select.call_count,1)
