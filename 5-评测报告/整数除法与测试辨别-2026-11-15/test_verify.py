#!/usr/bin/env python3
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import verify


class ForthEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result=verify.compute()

    def value(self, label, probe):
        data=self.result['selected_sources'][label]
        self.assertEqual(data['state'],'complete')
        row=next(x for x in data['current_copy']['probes'] if x['id']==probe)
        self.assertEqual(row['state'],'returned')
        return row['value']

    def test_checked_in_result_reproduces(self):
        self.assertEqual(self.result,json.loads(Path(__file__).with_name('result.json').read_text()))

    def test_canonical_coverage(self):
        rows=self.result['canonical_division_calls']
        self.assertEqual(len(rows),7)
        self.assertEqual({tuple(x['programs']) for x in rows},{('12 3 /',),('8 3 /',),('4 0 /',),('/',),('1 /',),('1 12 3 /',),('2 4 * 3 /',)})
        for label,data in self.result['selected_sources'].items():
            self.assertEqual(data['state'],'complete',label)
            self.assertEqual(data['current_copy']['tests_run'],54,label)
            self.assertEqual(data['current_copy']['errors'],[],label)
            self.assertEqual(data['current_copy']['skipped'],[],label)
            self.assertEqual(data['current_copy']['successful'],label!='bare_r1',label)
        self.assertEqual(len(self.result['selected_sources']['bare_r1']['current_copy']['failures']),2)

    def test_equal_canonical_pass_does_not_identify_signed_rounding(self):
        self.assertTrue(self.result['historical_receipts']['bare_r2']['forth_pass'])
        self.assertTrue(self.result['historical_receipts']['bare_r3']['forth_pass'])
        for probe in ['negative_numerator','negative_denominator']:
            self.assertEqual(self.value('bare_r2',probe),[-3])
            self.assertEqual(self.value('bare_r3',probe),[-2])
        for label in verify.SOURCES:
            self.assertEqual(self.value(label,'both_negative'),[2])

    def test_large_positive_precision_and_small_literal_construction(self):
        for label in verify.SOURCES:
            expected=9007199254740992 if label in {'bare_r1','wb_legacy_archive'} else 9007199254740993
            for probe in ['positive_large_identity','constructed_large_identity']:
                self.assertEqual(self.value(label,probe),[expected])
            self.assertEqual(self.value(label,'positive_large_remainder'),[3002399751580331])
        # Near-miss counterexample: not every above-2**53 division is wrong.
        self.assertTrue(self.result['selected_sources']['wb_legacy_archive']['current_copy']['successful'])

    def test_historical_headline_is_not_all_tests_correct(self):
        r1=self.result['historical_receipts']['bare_r1']
        self.assertEqual(r1['case_reward'],1)
        self.assertFalse(r1['forth_pass'])
        self.assertEqual(r1['forth_completion']['succeeded'],52)
        self.assertEqual(self.result['real_product_runs'],0)

    def test_integer_oracle_has_independent_algebraic_certificate(self):
        for a in range(-100,101):
            for b in [*range(-9,0),*range(1,10)]:
                q=verify.trunc_div(a,b)
                remainder=a-q*b
                self.assertLess(abs(remainder),abs(b))
                self.assertTrue(remainder==0 or (remainder>0)==(a>0))
                self.assertEqual(q*b+remainder,a)
        self.assertEqual(verify.trunc_div(9007199254740993,1),9007199254740993)

    def test_modified_source_identity_fails_closed(self):
        with patch.dict(verify.PINS,{verify.TEST:'0'*64}):
            with self.assertRaisesRegex(ValueError,'source pin mismatch'):
                verify.check_pins()


if __name__=='__main__':
    unittest.main()
