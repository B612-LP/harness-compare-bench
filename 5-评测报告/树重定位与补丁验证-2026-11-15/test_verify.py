#!/usr/bin/env python3
"""Tests for derived logic and experiment infrastructure, not a simulated product."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest

BASE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('pov_verify',BASE/'verify.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
w=v.load_worker(BASE)
OPTIMIZE=0

class VerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixed=json.loads((BASE/'result.json').read_text())
        cls.actual=v.recompute(BASE,OPTIMIZE)

    def with_copy(self,mutate):
        with tempfile.TemporaryDirectory(prefix='pov-test-') as t:
            p=Path(t)
            for name in v.PAYLOADS+('sources.json','result.json','verify.py'):
                shutil.copyfile(BASE/name,p/name)
            mutate(p)

    def test_real_recompute_matches_fixed(self):
        self.assertEqual(v.encoded(self.actual),v.encoded(self.fixed))
    def test_claims_partial_not_complete(self):
        self.assertEqual(self.actual['claims'],{'repair_complete':False,'partial_topology_repair':True,'historical_failed_test_ids':None,'harness_cause':None})
    def test_canonical_before_after_reference(self):
        self.assertEqual([r['canonical']['successes'] for r in self.actual['versions']],[5,12,15])
        self.assertTrue(all(r['canonical']['tests_run']==15 and not r['canonical']['errors'] for r in self.actual['versions']))
    def test_after_exact_current_failure_ids(self):
        self.assertEqual(self.actual['versions'][1]['canonical']['failures'],['test_can_find_path_to_cousin','test_can_reroot_a_complex_tree_with_cousins','test_can_reroot_a_tree_with_new_root_deeply_nested_in_tree'])
    def test_reference_not_assumed(self):
        r=self.actual['versions'][2]
        self.assertEqual(r['oracle']['summary'],{'error_checked':12,'error_passed':12,'original_immutable':True,'path_checked':90,'path_passed':90,'reroot_checked':16,'reroot_passed':16})
    def test_independent_bfs_known_chain(self):
        g=w.graph(w.FIXTURES['chain3'])
        self.assertEqual(w.bfs(g,'C','A'),['C','B','A'])
        self.assertEqual(w.edges(g),[['A','B'],['B','C']])
    def test_independent_bfs_known_cousins(self):
        self.assertEqual(w.bfs(w.graph(w.FIXTURES['branched']),'G','F'),['G','D','B','A','C','F'])
    def test_bfs_missing_is_unknown(self):
        self.assertIsNone(w.bfs(w.graph(w.FIXTURES['chain3']),'MISSING','A'))
    def test_duplicate_label_rejected(self):
        with self.assertRaisesRegex(ValueError,'duplicate label'):
            w.graph(['A',[['A',[]]]])
    def test_cycle_rejected(self):
        node=types.SimpleNamespace(label='A',children=[]);node.children.append(node)
        with self.assertRaisesRegex(ValueError,'cycle'):
            w.snapshot(node)
    def test_after_chain_changes_specific_edge(self):
        r=next(r for r in self.actual['versions'][1]['oracle']['reroot_rows'] if r['fixture']=='chain3' and r['target']=='C')
        self.assertTrue(r['root_ok']);self.assertFalse(r['edges_ok'])
        self.assertEqual(r['expected_edges'],[['A','B'],['B','C']])
        self.assertEqual(r['actual_edges'],[['A','C'],['B','C']])
    def test_before_chain_preserves_edges_but_wrong_root(self):
        r=next(r for r in self.actual['versions'][0]['oracle']['reroot_rows'] if r['fixture']=='chain3' and r['target']=='C')
        self.assertTrue(r['edges_ok']);self.assertFalse(r['root_ok'])
    def test_shallow_controls_pass_only_after(self):
        rows=[r for r in self.actual['versions'][1]['oracle']['reroot_rows'] if r['depth']<=1]
        self.assertTrue(all(r['root_ok'] and r['edges_ok'] for r in rows))
        self.assertTrue(any(not r['root_ok'] for r in self.actual['versions'][0]['oracle']['reroot_rows'] if r['depth']==1))
    def test_immutability_observed_for_all(self):
        self.assertTrue(all(r['oracle']['summary']['original_immutable'] for r in self.actual['versions']))
    def test_error_type_and_messages_all_checked(self):
        self.assertTrue(all(r['oracle']['summary']['error_passed']==12 for r in self.actual['versions']))
    def test_timeout_remains_unknown_no_zero(self):
        def timeout(*args,**kwargs):raise subprocess.TimeoutExpired(args[0],1)
        r=v.execute(BASE,'after',OPTIMIZE,runner=timeout)
        self.assertEqual(r['status'],'unknown');self.assertIsNone(r['canonical']);self.assertIsNone(r['oracle'])
        values=copy.deepcopy(self.actual['versions']);values[1]=r
        self.assertIsNone(v.claims(values)['partial_topology_repair'])
    def test_nonzero_remains_unknown(self):
        def fail(*args,**kwargs):return types.SimpleNamespace(returncode=7,stdout='')
        self.assertEqual(v.execute(BASE,'after',OPTIMIZE,runner=fail)['reason'],'child_nonzero')
    def test_invalid_json_remains_unknown(self):
        def fail(*args,**kwargs):return types.SimpleNamespace(returncode=0,stdout='no-json')
        self.assertEqual(v.execute(BASE,'after',OPTIMIZE,runner=fail)['reason'],'child_invalid_json')
    def test_explicit_child_optimization_mismatch_rejected(self):
        def mismatch(*args,**kwargs):return types.SimpleNamespace(returncode=0,stdout=json.dumps({'optimize':1-OPTIMIZE,'result':{'variant':'after'}}))
        with self.assertRaisesRegex(ValueError,'optimization identity'):
            v.execute(BASE,'after',OPTIMIZE,runner=mismatch)
    def test_boolean_optimization_rejected(self):
        with self.assertRaisesRegex(ValueError,'explicit optimize'):
            v.execute(BASE,'after',True)
    def test_source_byte_near_miss_rejected(self):
        def check(p):
            x=p/'after.py';x.write_bytes(x.read_bytes().replace(b'list(rebuilt.children)',b'list(parent_node.children)'))
            with self.assertRaisesRegex(ValueError,'payload identity mismatch'):
                v.validate_sources(p)
        self.with_copy(check)
    def test_swap_before_after_rejected(self):
        def check(p):
            (p/'after.py').write_bytes((p/'before.py').read_bytes())
            with self.assertRaisesRegex(ValueError,'payload identity mismatch'):
                v.validate_sources(p)
        self.with_copy(check)
    def test_test_payload_change_rejected(self):
        def check(p):
            x=p/'canonical_test.py';x.write_bytes(x.read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError,'payload identity mismatch'):
                v.validate_sources(p)
        self.with_copy(check)
    def test_source_bytes_bool_rejected(self):
        def check(p):
            x=p/'sources.json';s=json.loads(x.read_text());s['payloads']['after.py']['bytes']=True;x.write_text(json.dumps(s))
            with self.assertRaisesRegex(ValueError,'payload bytes'):
                v.validate_sources(p)
        self.with_copy(check)
    def test_historical_identity_false_not_zero(self):
        def check(p):
            x=p/'sources.json';s=json.loads(x.read_text());s['historical_summary']['identities_match']=0;x.write_text(json.dumps(s))
            with self.assertRaisesRegex(ValueError,'historical boundary'):
                v.validate_sources(p)
        self.with_copy(check)
    def test_snapshot_unknown_not_false(self):
        def check(p):
            x=p/'sources.json';s=json.loads(x.read_text());s['snapshot']['backend_continuation']=False;x.write_text(json.dumps(s))
            with self.assertRaisesRegex(ValueError,'snapshot boundary'):
                v.validate_sources(p)
        self.with_copy(check)
    def test_result_type_sensitive(self):
        bad=copy.deepcopy(self.fixed);bad['claims']['repair_complete']=0
        self.assertNotEqual(v.encoded(bad),v.encoded(self.fixed))
    def test_changed_fixed_result_no_pass(self):
        def check(p):
            x=p/'result.json';s=json.loads(x.read_text());s['versions'][1]['canonical']['successes']=15;x.write_text(json.dumps(s))
            with self.assertRaisesRegex(ValueError,'fixed result mismatch'):
                v.verify(p,OPTIMIZE)
        self.with_copy(check)
    def test_failed_reference_blocks_claims(self):
        data=copy.deepcopy(self.actual['versions']);data[2]['canonical']['successes']=14
        self.assertIsNone(v.claims(data)['partial_topology_repair'])
    def test_oracle_truth_uses_no_candidate_path_helpers(self):
        import inspect
        for fn in (w.graph,w.bfs,w.edges):
            self.assertNotIn('_find_path',inspect.getsource(fn));self.assertNotIn('from_pov',inspect.getsource(fn))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--optimize',type=int,choices=(0,1),required=True)
    args=parser.parse_args();OPTIMIZE=args.optimize
    unittest.main(argv=[sys.argv[0]],verbosity=2)
