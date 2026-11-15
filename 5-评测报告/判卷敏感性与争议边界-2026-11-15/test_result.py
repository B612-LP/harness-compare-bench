#!/usr/bin/env python3
"""Read-only checks of the published projection and scorer examples."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('checker_under_test', ROOT / '2-用例/dabstep-payments-10/checker.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
result = json.loads((HERE / 'result.json').read_text(encoding='utf-8'))

class TestPublishedProjection(unittest.TestCase):
    def test_candidate_grid(self):
        rows = result['rows']
        keys = {(r['capture'], r['multi'], r['fraud_mode'], tuple(r['flags'].values())) for r in rows}
        self.assertEqual(len(keys), 216)
        self.assertEqual(sum(len(r['all_candidate_compat']) for r in rows), 1296)
        for row in rows:
            self.assertEqual(set(row['fees']), set('ABCDEF'))
            for a, value in row['fees'].items():
                self.assertEqual(row['all_candidate_compat'][a], checker.question_scorer(f'{a}:{value:.2f}', 'E:13.57'))
        self.assertEqual(result['all_candidate_compat_count'], 0)
        self.assertFalse(any(any(r['all_candidate_compat'].values()) for r in rows))
        self.assertEqual(sum(list(r['fees'].values()).count(min(r['fees'].values())) > 1 for r in rows), 162)
        self.assertAlmostEqual(result['min_abs_E_gap'], 3.06)
        self.assertAlmostEqual(result['min_abs_any_candidate_gap'], 0.92)

    def test_numeric_and_strict_contrast(self):
        for pred in ('E:13.57', 'NexPay:13.57', 'E:-13.57', 'E:13.6', 'E:13.60'):
            self.assertTrue(checker.question_scorer(pred, 'E:13.57'), pred)
        for pred in ('E:13.56', 'E:13.58', 'E:16.63'):
            self.assertFalse(checker.question_scorer(pred, 'E:13.57'), pred)
        self.assertTrue(checker.strict_question_scorer('2697', 'E:13.57', 'E:13.57'))
        for pred in ('NexPay:13.57', 'E:-13.57', 'E:13.60'):
            self.assertFalse(checker.strict_question_scorer('2697', pred, 'E:13.57'), pred)

    def test_receipt_counterfactuals(self):
        expected = {'codex': (7,6), 'dsh': (7,7)}
        for product, scores in expected.items():
            receipt = result['receipts'][product]
            self.assertEqual(receipt['gates'], {'answers_format': True, 'input_integrity': True})
            for mode, correct in zip(('official_compat','strict_contract'), scores):
                m = receipt['modes'][mode]
                self.assertEqual((m['correct'], m['out_of'], m['q2697_pass'], m['original_reward']), (correct,10,False,0))
                self.assertAlmostEqual(m['omit_q2697_rate'], correct/9)
                self.assertEqual(m['omit_rate_threshold_pass'], correct/9 >= .8)
                self.assertAlmostEqual(m['hypothetical_q2697_pass_rate'], (correct+1)/10)
                self.assertEqual(m['hypothetical_rate_threshold_pass'], (correct+1)/10 >= .8)

if __name__ == '__main__':
    unittest.main()
