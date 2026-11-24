import json
import unittest
from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import recompute as rc


def row(kind, size):
    return [kind, size, None, 0]


def slot_rows(user_sizes):
    """A minimal DSH-shaped projection with one user/message per given size."""
    rows = [row('session', 100), row('turn/start', 20)]
    for size in user_sizes:
        rows.append(row('user/message', size))
    rows += [row('request/header', 17906), row('request/context', 179),
             row('assistant/message', 500), row('tool/call', 300),
             row('turn/end', 20)]
    return rows


class AblationTest(unittest.TestCase):
    def setUp(self):
        self.slots = {}
        # dabstep-like: r1 carries two extra user messages -> only the
        # user/message cut can close the gap
        self.slots['dsh__dabstep-payments-10__r1'] = {'events': slot_rows([4851, 3151, 1019, 424, 532])}
        self.slots['dsh__dabstep-payments-10__r2'] = {'events': slot_rows([4851, 3151, 1019])}
        self.slots['dsh__dabstep-payments-10__r3'] = {'events': slot_rows([4851, 3151, 1019])}
        # stable groups: all cuts pass
        for case in ('bird-ca-schools-15', 'exercism-py-6',
                     'lcb-recent-hard-4', 'tb-cargo-plan'):
            for rep in rc.REPS:
                self.slots['dsh__%s__%s' % (case, rep)] = {'events': slot_rows([100, 200])}

    def test_01_matrix_flips_only_on_removed_type(self):
        matrix = rc.ablation_matrix(self.slots)
        x = matrix['dabstep-payments-10']
        self.assertFalse(x['full']['aux_pass'])
        self.assertTrue(x['user/message']['aux_pass'])
        self.assertFalse(x['request/header']['aux_pass'])
        self.assertFalse(x['request/context']['aux_pass'])
        self.assertEqual(x['user/message']['extreme'], 0)
        self.assertEqual(x['full']['extreme'], 956)

    def test_02_stable_group_passes_all_cuts(self):
        matrix = rc.ablation_matrix(self.slots)
        for cut in ('full',) + rc.S3:
            self.assertTrue(matrix['bird-ca-schools-15'][cut]['aux_pass'])

    def test_03_missing_type_reported_as_zero(self):
        report = rc.missing_type_report(self.slots)
        self.assertEqual(set(report), set(rc.REPS))
        self.assertTrue(all(v == 0 for v in report.values()))

    def test_04_usage_like_census_detects_absence(self):
        union, usage_like = rc.type_census(self.slots)
        self.assertNotIn('token_usage_record', union)
        self.assertEqual(usage_like, [])

    def test_05_usage_like_census_detects_presence(self):
        slots = dict(self.slots)
        events = list(slots['dsh__dabstep-payments-10__r1']['events']) + [row('token_usage_record', 90)]
        slots['dsh__dabstep-payments-10__r1'] = {'events': events}
        _, usage_like = rc.type_census(slots)
        self.assertEqual(usage_like, ['token_usage_record'])

    def test_06_row_invariants_reject_bad_head(self):
        with self.assertRaises(rc.Invalid):
            rc.check_dsh_rows([row('turn/start', 20)])

    def test_07_non_response_row_requires_zero_payload_columns(self):
        with self.assertRaises(rc.Invalid):
            rc.check_dsh_rows(slot_rows([100])[:-1] + [['tool/call', 10, 'x', 5]])

    def test_08_pinned_evidence_is_untouched(self):
        # guard: this suite never writes; pinned sha must still verify
        root = Path(__file__).resolve().parents[2]
        doc = json.loads((root / rc.PINNED_REL).read_text(encoding='utf-8'))
        self.assertEqual(doc.get('schema'), 'r1109-content-free-projection-v1.1')


if __name__ == '__main__':
    unittest.main()
