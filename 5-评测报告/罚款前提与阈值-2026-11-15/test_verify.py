#!/usr/bin/env python3
"""In-memory negative checks; no temporary files or recorded commands."""
import copy
import io
import unittest
from unittest.mock import patch
import verify


class VerifyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = verify.jsonl(verify.ROLLOUT)

    def test_event_chain(self):
        self.assertEqual(verify.verify_events(self.events), [29,37,49,55,207,210])

    def test_duplicate_call_rejected(self):
        events = copy.deepcopy(self.events)
        events.append(copy.deepcopy(events[28]))
        with self.assertRaises(ValueError):
            verify.verify_events(events)

    def test_missing_output_rejected(self):
        events = copy.deepcopy(self.events)
        events[54]['payload']['call_id'] = 'wrong'
        with self.assertRaises(ValueError):
            verify.verify_events(events)

    def test_failed_output_rejected(self):
        events = copy.deepcopy(self.events)
        events[209]['payload']['output'] = events[209]['payload']['output'].replace('exited with code 0', 'exited with code 1')
        with self.assertRaises(ValueError):
            verify.verify_events(events)

    def test_truncation_rejected(self):
        events = copy.deepcopy(self.events)
        events[36]['payload']['output'] += '\nWarning: truncated output'
        with self.assertRaises(ValueError):
            verify.verify_events(events)

    def test_timestamp_order_rejected(self):
        events = copy.deepcopy(self.events)
        events[54]['timestamp'] = '2020-01-01T00:00:00Z'
        with self.assertRaises(ValueError):
            verify.verify_events(events)

    def test_invalid_timestamp_rejected(self):
        events = copy.deepcopy(self.events)
        events[54]['timestamp'] = '2026-99-99T18:15:52Z'
        with self.assertRaises(ValueError):
            verify.verify_events(events)

    def test_date_only_utc_rejected(self):
        events = copy.deepcopy(self.events)
        for day, index in enumerate((28, 36, 48, 54, 206, 209), 1):
            events[index]['timestamp'] = f'2026-10-{day:02d}Z'
        with self.assertRaises(ValueError):
            verify.verify_events(events)

    def test_non_utc_timestamp_rejected(self):
        events = copy.deepcopy(self.events)
        events[54]['timestamp'] = '2026-10-28T18:15:52+00:00'
        with self.assertRaises(ValueError):
            verify.verify_events(events)

    def test_threshold_change_rejected(self):
        events = copy.deepcopy(self.events)
        payload = events[206]['payload']
        payload['arguments'] = payload['arguments'].replace('0.083', '0.08')
        with self.assertRaises(ValueError):
            verify.verify_events(events)

    def test_blank_jsonl_rejected(self):
        with patch.object(verify.Path, 'open', return_value=io.StringIO('{}\n\n{}\n')):
            with self.assertRaises(ValueError):
                verify.jsonl('unused')

    def test_nonunique_or_wrong_hash_rejected(self):
        with self.assertRaises(ValueError):
            verify.only([1,2], 'test')
        path = next(iter(verify.SOURCES))
        with patch.object(verify, 'SOURCES', {path: '0'*64}):
            with self.assertRaises(ValueError):
                verify.main()

    def test_decimal_monthly_and_total(self):
        months, total = verify.aggregates(verify.ROOT / verify.CASE / 'inputs/payments.csv')
        self.assertEqual(len(months), 12)
        self.assertEqual((total[0], total[1], str(total[2]), str(total[3])), (13805,1105,'1260227.18','115108.53'))
        self.assertGreater(total[3], total[2]*verify.Decimal('0.083'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
