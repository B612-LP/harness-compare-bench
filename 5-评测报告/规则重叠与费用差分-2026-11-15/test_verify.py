"""Counterexamples for the new offline recomputation; no product/runner execution."""
import copy
import csv
import importlib.util
import io
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('fee_verify', HERE/'verify.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
D = Decimal


class VerifyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.actual = v.recompute()
        cls.src = {p: (v.ROOT/p).read_text(encoding='utf-8') for p in v.SOURCES}
        cls.rules = v.parse_json(cls.src[v.CASE+'inputs/fees.json'])
        cls.merchants = v.parse_json(cls.src[v.CASE+'inputs/merchant_data.json'])
        cls.row = next(csv.DictReader(io.StringIO(cls.src[v.CASE+'inputs/payments.csv'])))
        cls.names = v.validate_merchants(cls.merchants)

    def csv_text(self, rows, header=None):
        out = io.StringIO(newline='')
        writer = csv.writer(out)
        header = v.CSV_FIELDS if header is None else header
        writer.writerow(header)
        for row in rows:
            writer.writerow([row[k] for k in header])
        return out.getvalue()

    def bad_rule(self, key, value):
        rule = copy.deepcopy(self.rules[0])
        rule[key] = value
        with self.assertRaises(v.EvidenceError):
            v.validate_rules([rule])

    def test_actual_exact_partition(self):
        a = self.actual['analysis']
        self.assertEqual((a['affected_count'], a['affected_amount_eur']), (12, '729.31'))
        self.assertEqual(a['groups'], [dict(denominator=1, count=8, amount_eur='615.80'),
                                      dict(denominator=2, count=4, amount_eur='113.51')])
        for p in a['payments']:
            self.assertEqual(p['matching_rule_ids'], [384] if p['aci'] == 'C' else [231, 384])
        self.assertEqual((D(a['delta_sum_eur']), D(a['delta_mean_eur']), D(a['mean_minus_sum_eur'])),
                         (D('-.948103'), D('-.8743215'), D('.0737815')))
        self.assertEqual(a['january_volume_eur'], '113260.42')
        self.assertEqual(a['january_fraud_volume_eur'], '11680.62')
        self.assertEqual([r['ID'] for r in a['relevant_rules']], [95, 231, 384, 471, 603, 804, 870])
        self.assertEqual(a['empty_reject_target_support_count'], 0)
        self.assertEqual(a['empty_unknown_target_support_count'], 12)

    def test_committed_result_exact(self):
        expected = v.parse_json((HERE/'result.json').read_text(encoding='utf-8'))
        v.verify_result(expected, self.actual)

    def test_nonoverlap_sum_mean_identical(self):
        _, summed, mean = v.local_deltas([dict(amount_eur='100.00', denominator=1)], 14, 1)
        self.assertEqual((summed, mean), (D('-.13'), D('-.13')))

    def test_overlap_denominator_not_target_count(self):
        _, summed, mean = v.local_deltas([dict(amount_eur='100.00', denominator=2)], 14, 1)
        self.assertEqual((summed, mean), (D('-.13'), D('-.065')))
        # Changing only rule384 leaves every fixed fee and rule231 contribution cancelled.
        old = (D('.05')+14*D(100)/10000 + D('.02')+25*D(100)/10000)/2
        new = (D('.05')+1*D(100)/10000 + D('.02')+25*D(100)/10000)/2
        self.assertEqual(new-old, mean)
        self.assertNotEqual(summed, mean)

    def test_unaffected_payment_not_in_delta_support(self):
        target = next(r for r in self.rules if r['ID'] == 384)
        values = dict(card_scheme='NexPay', account_type='R', capture_delay='<3',
                      monthly_fraud_level='>8.3%', monthly_volume='100k-1m',
                      merchant_category_code=5942, is_credit=True, aci='A', intracountry=D(1))
        self.assertFalse(v.matches(target, values))
        values['aci'] = 'B'
        ids = sorted(r['ID'] for r in self.rules if v.matches(r, values))
        self.assertEqual(ids, [231, 384])
        self.assertEqual(sorted(r['ID'] for r in reversed(self.rules) if v.matches(r, values)), ids)
        values['aci'] = 'C'
        self.assertEqual([r['ID'] for r in self.rules if v.matches(r, values)], [384])

    def test_context_really_excludes_additional_rules(self):
        values = dict(card_scheme='NexPay', account_type='R', capture_delay='<3',
                      monthly_fraud_level='>8.3%', monthly_volume='100k-1m',
                      merchant_category_code=5942, is_credit=True, aci='B', intracountry=D(0))
        self.assertFalse(v.matches(next(r for r in self.rules if r['ID'] == 471), values))
        values['monthly_fraud_level'] = '<7.2%'
        self.assertTrue(v.matches(next(r for r in self.rules if r['ID'] == 471), values))
        self.assertEqual(len([r for r in self.rules if v.matches(r, values)]), 3)

    def test_empty_list_unknown_not_automatic_wildcard(self):
        self.assertIsNone(v.accepts([], 'R', 'unknown'))
        self.assertTrue(v.accepts([], 'R', 'wildcard'))
        self.assertFalse(v.accepts([], 'R', 'reject'))
        self.assertTrue(v.accepts(None, 'R', 'unknown'))
        self.assertFalse(v.accepts(['S'], 'R', 'unknown'))
        with self.assertRaises(v.EvidenceError):
            v.accepts([], 'R', 'made-up')

    def test_duplicate_and_nonfinite_json(self):
        for text in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}'):
            with self.subTest(text=text), self.assertRaises(v.EvidenceError):
                v.parse_json(text)
        with self.assertRaises(v.EvidenceError):
            v.finite_tree({'nested': [D('NaN')]})

    def test_rule_ids_reject_bool_string_duplicate(self):
        for value in (True, '384', D(384), 0, -1):
            self.bad_rule('ID', value)
        with self.assertRaises(v.EvidenceError):
            v.validate_rules([self.rules[0], self.rules[0]])

    def test_rule_fields_and_types_strict(self):
        for key, value in [('is_credit', 1), ('is_credit', 'True'), ('account_type', 'R'),
                           ('merchant_category_code', [True]), ('rate', True), ('rate', D(14)),
                           ('fixed_amount', D('Infinity')), ('fixed_amount', 1),
                           ('intracountry', True), ('intracountry', D(2)),
                           ('monthly_volume', 'guess'), ('aci', ['B', 'B'])]:
            with self.subTest(key=key, value=value):
                self.bad_rule(key, value)
        for change in ('extra', 'missing'):
            rule = copy.deepcopy(self.rules[0])
            if change == 'extra':
                rule['extra'] = None
            else:
                rule.pop('rate')
            with self.assertRaises(v.EvidenceError):
                v.validate_rules([rule])

    def test_csv_boolean_and_id_fail_closed(self):
        for key, value in [('is_credit', 'False '), ('is_credit', '0'),
                           ('has_fraudulent_dispute', 'false'), ('year', '2023.0'),
                           ('day_of_year', '366'), ('eur_amount', 'NaN'),
                           ('eur_amount', '1.001'), ('eur_amount', '-1'), ('aci', 'AA')]:
            row = dict(self.row, **{key: value})
            with self.subTest(key=key, value=value), self.assertRaises(v.EvidenceError):
                list(v.payments(self.csv_text([row]), self.names))
        with self.assertRaises(v.EvidenceError):
            list(v.payments(self.csv_text([self.row, self.row]), self.names))
        with self.assertRaises(v.EvidenceError):
            list(v.payments(self.csv_text([self.row], v.CSV_FIELDS[:-1]), self.names))
        self.assertFalse(v.csv_bool('False'))  # bool('False') would be incorrect.

    def test_natural_month_and_leap_dates(self):
        rows = [dict(self.row, psp_reference=str(i), year=y, day_of_year=d)
                for i, (y, d) in enumerate([('2023','31'), ('2023','32'), ('2024','60'), ('2024','61')], 1)]
        dates = [r['_date'].isoformat() for r in v.payments(self.csv_text(rows), self.names)]
        self.assertEqual(dates, ['2023-01-31', '2023-02-01', '2024-02-29', '2024-03-01'])
        row = dict(self.row, day_of_year='0')
        with self.assertRaises(v.EvidenceError):
            list(v.payments(self.csv_text([row]), self.names))

    def test_merchant_id_and_schema_strict(self):
        with self.assertRaises(v.EvidenceError):
            v.validate_merchants([self.merchants[0], self.merchants[0]])
        row = copy.deepcopy(self.merchants[0])
        row['merchant_category_code'] = True
        with self.assertRaises(v.EvidenceError):
            v.validate_merchants([row])

    def test_bad_denominator_and_decimal(self):
        for value in (0, -1, True, '2', D(2)):
            with self.subTest(value=value), self.assertRaises(v.EvidenceError):
                v.local_deltas([dict(amount_eur='10', denominator=value)], 14, 1)
        for value in ('Infinity', 'NaN', '1e309', '', ' 1', True):
            with self.subTest(value=value), self.assertRaises(v.EvidenceError):
                v.decimal_text(value)

    def test_answer_ids_fields_and_types(self):
        good = v.json_lines(self.src[v.RUN+'artifacts/answers.jsonl'])
        for change in ('duplicate', 'integer', 'extra', 'missing'):
            rows = copy.deepcopy(good)
            if change == 'duplicate': rows[8]['task_id'] = rows[7]['task_id']
            if change == 'integer': rows[8]['task_id'] = 1871
            if change == 'extra': rows[8]['unused'] = 'x'
            if change == 'missing': rows.pop()
            with self.subTest(change=change), self.assertRaises(v.EvidenceError):
                v.validate_task_rows(rows, ['task_id', 'answer'])

    def test_source_hash_checked_before_parsing(self):
        with tempfile.TemporaryDirectory(prefix='fee-source-check-') as temp:
            root = Path(temp)
            first = next(iter(v.SOURCES))
            (root/first).parent.mkdir(parents=True)
            (root/first).write_text('{}', encoding='utf-8')
            with self.assertRaisesRegex(v.EvidenceError, 'source hash mismatch'):
                v.recompute(root)

    def test_result_extra_missing_bool_not_int(self):
        for change in ('extra', 'missing', 'bool', 'delta', 'norm'):
            result = copy.deepcopy(self.actual)
            if change == 'extra': result['unbound'] = True
            if change == 'missing': result.pop('sources_sha256')
            if change == 'bool': result['analysis']['groups'][0]['denominator'] = True
            if change == 'delta': result['analysis']['delta_mean_eur'] = '-0.948103'
            if change == 'norm': result['evidence_binding']['aggregation_norm'] = 'sum'
            with self.subTest(change=change), self.assertRaises(v.EvidenceError):
                v.verify_result(result, self.actual)

    def test_trace_parent_choice_and_receipt_mutations(self):
        for change in ('parent', 'choice', 'receipt', 'duplicate_receipt', 'reward_bool', 'receipt_extra_id', 'answer'):
            src = dict(self.src)
            if change in ('parent', 'choice'):
                rows = v.json_lines(src[v.RUN+'trace.public-derived.jsonl'])
                if change == 'parent': rows[54]['parentId'] = 'wrong'
                else: rows[54]['rawContent'] = []
                src[v.RUN+'trace.public-derived.jsonl'] = '\n'.join(json.dumps(v.json_safe(r)) for r in rows)
            elif change in ('receipt', 'duplicate_receipt', 'reward_bool', 'receipt_extra_id'):
                receipt = json.loads(src[v.RUN+'checker.stdout.json'])
                check = next(c for c in receipt['official_compat']['checks'] if c['id'] == 'q1871')
                if change == 'receipt': check['pass'] = True
                if change == 'duplicate_receipt': receipt['official_compat']['checks'].append(check)
                if change == 'reward_bool': receipt['official_compat']['reward'] = False
                if change == 'receipt_extra_id': receipt['official_compat']['checks'].append(dict(id='qunknown'))
                src[v.RUN+'checker.stdout.json'] = json.dumps(receipt)
            else:
                rows = v.json_lines(src[v.RUN+'artifacts/answers.jsonl'])
                rows[8]['answer'] = '-0.948103'
                src[v.RUN+'artifacts/answers.jsonl'] = '\n'.join(json.dumps(r) for r in rows)
            with self.subTest(change=change), self.assertRaises(v.EvidenceError):
                v.bind_evidence(src, self.actual['analysis'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
