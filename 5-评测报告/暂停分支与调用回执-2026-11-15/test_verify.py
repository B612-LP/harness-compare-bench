#!/usr/bin/env python3
"""Logical negative-table tests only; never product/native mock or new runs."""
import copy
import json
from pathlib import Path
import unittest
import verify

BASE=Path(__file__).resolve().parent
DATA=json.loads((BASE/'derived.json').read_text(encoding='utf-8'))
RESULT=json.loads((BASE/'result.json').read_text(encoding='utf-8'))

class VerificationTests(unittest.TestCase):
    def data(self):
        return copy.deepcopy(DATA)

    def test_fixed_result(self):
        self.assertEqual(verify.verify(DATA,RESULT)['totals']['unique_pairs'],30)

    def test_fixed_result_cannot_be_replaced_by_claim(self):
        r=copy.deepcopy(RESULT);r['causal_approval_mechanism']='confirmed'
        with self.assertRaises(ValueError):verify.verify(DATA,r)

    def test_bool_is_not_integer_result(self):
        r=copy.deepcopy(RESULT);r['waiting_attempts']=True
        with self.assertRaises(ValueError):verify.verify(DATA,r)

    def test_missing_attempt(self):
        d=self.data();d['attempts'].pop()
        with self.assertRaises(ValueError):verify.analyze(d)

    def test_wrong_attempt_order(self):
        d=self.data();d['attempts'].reverse()
        with self.assertRaises(ValueError):verify.analyze(d)

    def test_unknown_field_rejected(self):
        d=self.data();d['rows'][0]['private_path']='not-permitted'
        with self.assertRaises(ValueError):verify.analyze(d)

    def test_private_path_in_hash_rejected(self):
        d=self.data();d['attempts'][0]['source_hashes']['session-read.json']='/private/example'
        with self.assertRaises(ValueError):verify.analyze(d)

    def test_unknown_cost_not_zero(self):
        d=self.data();d['attempts'][0]['total_cost']=0
        with self.assertRaises(ValueError):verify.analyze(d)

    def test_bool_not_integer_event_index(self):
        d=self.data();d['rows'][0]['item_index']=True
        with self.assertRaises(ValueError):verify.analyze(d)

    def test_byte_char_units_not_interchangeable(self):
        d=self.data();r=next(r for r in d['rows'] if r['kind']=='result');r['display_utf8_bytes']=r['display_chars']-1
        with self.assertRaises(ValueError):verify.analyze(d)

    def test_display_text_field_consistency(self):
        d=self.data();r=next(r for r in d['rows'] if r['kind']=='result');r['display_chars']=None
        with self.assertRaises(ValueError):verify.analyze(d)

    def test_duplicate_item_index_rejected(self):
        d=self.data();d['rows'].insert(0,copy.deepcopy(d['rows'][0]))
        with self.assertRaises(ValueError):verify.analyze(d)

    def test_duplicate_call_not_guessed(self):
        d=self.data();row=copy.deepcopy(d['rows'][0]);row['item_index']-=1;d['rows'].insert(0,row)
        r=verify.analyze(d);a=r['attempts'][0]
        self.assertEqual(a['unique_pairs'],0)
        self.assertIn('duplicate_calls',a['pairing_anomalies'][0]['reasons'])
        self.assertIsNone(r['observed_bash_separation'])
        with self.assertRaises(ValueError):verify.verify(d,RESULT)

    def test_duplicate_result_not_counted_twice(self):
        d=self.data();row=copy.deepcopy(d['rows'][1]);row['item_index']+=1;d['rows'].insert(2,row)
        r=verify.analyze(d);a=r['attempts'][0]
        self.assertEqual(a['unique_pairs'],0)
        self.assertIn('duplicate_results',a['pairing_anomalies'][0]['reasons'])
        self.assertIsNone(r['observed_bash_separation'])

    def test_orphan_result_not_paired_by_position(self):
        d=self.data();d['rows'].pop(0);r=verify.analyze(d)
        self.assertEqual(r['attempts'][0]['unique_pairs'],0)
        self.assertIn('orphan_result',r['attempts'][0]['pairing_anomalies'][0]['reasons'])
        self.assertIsNone(r['observed_bash_separation'])

    def test_missing_key_not_guessed(self):
        d=self.data();d['rows'][0]['callkey']=None;r=verify.analyze(d)
        self.assertEqual(r['attempts'][0]['unique_pairs'],0)
        self.assertIsNone(r['observed_bash_separation'])

    def test_identity_conflict_ineligible(self):
        d=self.data();d['rows'][0]['identity_conflict']=True;r=verify.analyze(d)
        self.assertIsNone(r['observed_bash_separation'])
        self.assertEqual(r['attempts'][0]['unique_pairs'],0)

    def test_name_conflict_not_guessed(self):
        d=self.data();d['rows'][1]['name']='Grep';r=verify.analyze(d)
        self.assertIn('name_conflict',r['attempts'][0]['pairing_anomalies'][0]['reasons'])
        self.assertIsNone(r['observed_bash_separation'])

    def test_missing_name_unknown(self):
        d=self.data();d['rows'][0]['name']=None;r=verify.analyze(d)
        self.assertIn('missing_call_name',r['attempts'][0]['pairing_anomalies'][0]['reasons'])
        self.assertIsNone(r['observed_bash_separation'])

    def test_result_before_call_unknown(self):
        d=self.data();d['rows'][0]['item_index'],d['rows'][1]['item_index']=d['rows'][1]['item_index'],d['rows'][0]['item_index'];d['rows'][:2]=reversed(d['rows'][:2])
        r=verify.analyze(d)
        self.assertIn('result_before_call',r['attempts'][0]['pairing_anomalies'][0]['reasons'])
        self.assertIsNone(r['observed_bash_separation'])

    def test_partial_selected_snapshot_unknown(self):
        d=self.data();d['attempts'][0]['has_more']=True;r=verify.analyze(d)
        self.assertIsNone(r['observed_bash_separation'])
        self.assertIsNone(r['read_refusal_necessary_for_waiting_in_this_table'])

    def test_local_completeness_not_backend_authentication(self):
        r=verify.analyze(DATA)
        self.assertEqual(r['private_source_authenticity'],'not_publicly_verified')
        self.assertEqual(r['action_vs_snapshot'],'unidentified')
        self.assertEqual(r['causal_approval_mechanism'],'unknown')

    def test_provider_output_are_one_result(self):
        r=verify.analyze(DATA)
        self.assertEqual(r['totals']['result_rows'],30)
        self.assertEqual(r['totals']['dual_representation_rows'],30)
        self.assertEqual(r['totals']['differing_representation_rows'],16)
        self.assertEqual(r['totals']['unique_pairs'],30)

    def test_frozen_summary(self):
        r=verify.analyze(DATA)
        self.assertEqual((r['waiting_attempts'],r['completed_attempts']),(4,9))
        self.assertIs(r['observed_bash_separation'],True)
        self.assertIs(r['read_refusal_necessary_for_waiting_in_this_table'],False)

    def test_unknown_completed_status_preserves_counts_and_yields_unknown(self):
        d=self.data();d['attempts'][0]['bridge_status']=None
        r=verify.analyze(d)
        self.assertIs(r['comparison_ready'],False)
        self.assertIsNone(r['observed_bash_separation'])
        self.assertIsNone(r['read_refusal_necessary_for_waiting_in_this_table'])
        self.assertEqual(r['totals'],RESULT['totals'])
        self.assertEqual(r['attempts'][0]['unique_pairs'],1)
        self.assertEqual(r['cross_table'][0],{'bridge_status':None,'bash_unmatched':False,'read_refusal':False,'attempts':1})
        self.assertEqual(r,verify.analyze(d))

    def test_unknown_waiting_status_does_not_strengthen_remaining_separation(self):
        d=self.data();d['attempts'][1]['bridge_status']=None
        r=verify.analyze(d)
        self.assertIs(r['comparison_ready'],False)
        self.assertIsNone(r['observed_bash_separation'])
        self.assertEqual(r['totals'],RESULT['totals'])
        self.assertEqual(r['cross_table'][0],{'bridge_status':None,'bash_unmatched':True,'read_refusal':False,'attempts':1})
        self.assertEqual(r['attempts'][1]['call_rows'],1)
        self.assertEqual(len(r['attempts'][1]['unmatched_calls']),1)

    def test_display_without_any_representation_rejected(self):
        d=self.data();r=next(r for r in d['rows'] if r['kind']=='result')
        r['output_present']=False;r['provider_result_present']=False;r['representations_differ']=None
        with self.assertRaisesRegex(ValueError,'display without any result representation'):verify.analyze(d)

    def test_pair_is_not_success_and_fixed_result_is_only_projection(self):
        d=self.data();r=next(r for r in d['rows'] if r['kind']=='result' and r['status']=='completed');r['status']='failed'
        self.assertEqual(verify.analyze(d),RESULT)
        self.assertEqual(verify.verify(d,RESULT)['totals']['unique_pairs'],30)
        self.assertEqual(verify.verify(d,RESULT)['private_source_authenticity'],'not_publicly_verified')

    def test_same_key_in_different_attempts_is_partitioned(self):
        d=self.data();key=d['rows'][0]['callkey'];original=next(r['callkey'] for r in d['rows'] if r['attempt']=='A03' and r['name']=='Read')
        for r in d['rows']:
            if r['attempt']=='A03' and r['callkey']==original:r['callkey']=key
        result=verify.analyze(d)
        self.assertEqual(result['totals'],RESULT['totals'])
        self.assertEqual(result['attempts'][2]['unique_pairs'],1)
        self.assertIs(result['observed_bash_separation'],True)

    def test_self_consistent_forgery_not_authenticated(self):
        d=self.data();r=next(r for r in d['rows'] if r['kind']=='result');r['display_chars']+=1;r['display_utf8_bytes']+=1
        revised=verify.analyze(d)
        # A changed table + changed result can be logically consistent. This is NOT truth verification.
        self.assertEqual(verify.verify(d,revised)['private_source_authenticity'],'not_publicly_verified')
        with self.assertRaises(ValueError):verify.verify(d,RESULT)

if __name__=='__main__':unittest.main(verbosity=2)
