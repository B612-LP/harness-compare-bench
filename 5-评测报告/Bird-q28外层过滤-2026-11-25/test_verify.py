#!/usr/bin/env python3
"""Fixed-source and synthetic near-miss tests; no historical SQL is executed."""
import copy
from pathlib import Path
import unittest
from unittest import mock
import verify

class TestQ28(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.actual=verify.calculate()

    def test_fixed_projection_and_receipts(self):
        verify.verify_expected(self.actual)
        self.assertEqual(self.actual['projection_type_counts'],{'null_text':45,'text_text':9941})
        self.assertEqual(self.actual['threshold_counterexample'],{'greater_or_equal_17_local_rows':57,'normalized_multiset_same':True,'same_keys':True})
        self.assertEqual(self.actual['joined']['schools_unmatched'],7700)
        self.assertEqual([r['note'] for r in self.actual['historical_q28']],['行数 2541 vs gold 57','行集一致（57 行）','行集一致（57 行）'])

    def test_missing_source_rejected(self):
        with mock.patch.object(Path,'is_file',return_value=False):
            with self.assertRaisesRegex(ValueError,'missing input'):
                verify.verify_pins()

    def test_incorrect_binding_rejected(self):
        with mock.patch.object(verify,'digest',return_value='0'*64):
            with self.assertRaisesRegex(ValueError,'SHA mismatch'):
                verify.verify_pins()

    def test_sidecars_rejected(self):
        for target in ('-wal','-shm','-journal'):
            with self.subTest(sidecar=target), mock.patch.object(Path,'exists',autospec=True,side_effect=lambda p: p.name.endswith(target)):
                with self.assertRaisesRegex(ValueError,'sidecar present'):
                    verify.ensure_no_sidecars(Path('/not-read/d.sqlite'))

    def test_corrupted_aggregate_rejected(self):
        changed=copy.deepcopy(self.actual)
        changed['outer']['removed_funding']['SQL NULL']=0
        with self.assertRaisesRegex(ValueError,'removed_funding'):
            verify.verify_expected(changed)

    def test_every_result_leaf_mutation_rejected(self):
        def leaves(value,path=()):
            if isinstance(value,dict):
                for key,child in value.items():
                    yield from leaves(child,path+(key,))
            elif isinstance(value,list):
                for i,child in enumerate(value):
                    yield from leaves(child,path+(i,))
            else:
                yield path,value
        count=0
        for path,value in leaves(self.actual):
            with self.subTest(path=path):
                changed=copy.deepcopy(self.actual)
                parent=changed
                for key in path[:-1]: parent=parent[key]
                if type(value) is bool: replacement=not value
                elif type(value) in (int,float): replacement=value+1
                elif type(value) is str: replacement=value+'!'
                else: self.fail('unexpected result leaf type')
                parent[path[-1]]=replacement
                with self.assertRaises(ValueError): verify.verify_expected(changed)
                count+=1
        self.assertGreaterEqual(count,35)

    def test_result_schema_and_float_near_misses(self):
        for mutation in ('missing','extra','bool_as_int','nan','infinity','mean_outside_tolerance'):
            changed=copy.deepcopy(self.actual)
            if mutation=='missing': del changed['joined']['frpm_unmatched']
            elif mutation=='extra': changed['joined']['extra']=0
            elif mutation=='bool_as_int': changed['threshold_counterexample']['same_keys']=1
            elif mutation=='nan': changed['means']['local']=float('nan')
            elif mutation=='infinity': changed['means']['local']=float('inf')
            else: changed['means']['local']+=1e-9
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                verify.verify_expected(changed)
        close=copy.deepcopy(self.actual)
        close['means']['local']+=5e-13
        verify.verify_expected(close)

    def test_projection_types_and_collision(self):
        self.assertEqual(verify.project(None),verify.project(' <NULL> '))
        for v in (b'hello',True,1,1.5,float('nan'),float('inf')):
            with self.subTest(value=repr(v)):
                with self.assertRaises(ValueError): verify.project(v)

    def test_multiset_not_just_size_or_set(self):
        a=[('k','A','x'),('k','A','x'),('k','B','y')]
        b=[('k','A','x'),('k','B','y'),('k','B','y')]
        ca,cb=verify.multiset(a),verify.multiset(b)
        self.assertEqual(sum(ca.values()),sum(cb.values()))
        self.assertEqual(set(ca),set(cb))
        self.assertNotEqual(ca,cb)

    def test_means_can_change_local_membership(self):
        local=[0,10]; population=[0,10,100]
        lm=sum(local)/len(local); am=sum(population)/len(population)
        self.assertEqual([x for x in local if x>lm],[10])
        self.assertEqual([x for x in local if x>am],[])

    def test_null_is_unknown_not_nonlocal(self):
        funding=[None,'Directly funded','Locally funded']
        excluded=[x for x in funding if x!='Locally funded']
        self.assertEqual(excluded,[None,'Directly funded'])
        self.assertEqual(sum(x is None for x in excluded),1)

if __name__=='__main__':
    unittest.main()
