"""Regression and adversarial checks for the public, offline replay."""

from pathlib import Path
import unittest
from unittest.mock import patch

import recompute as r

ROOT = Path(__file__).resolve().parents[2]


def synthetic_usage(marker_at=5):
    rows = [['session_meta', 110, None, 0],
            ['response_item', 160, 'message', 100], ['response_item', 140, 'message', 80],
            ['response_item', 120, 'message', 60], ['response_item', 66, 'reasoning', 42],
            ['response_item', 50, 'message', 30], ['response_item', 190, 'function_call', 150],
            ['response_item', 310, 'function_call_output', 270]]
    if marker_at is not None:
        rows.insert(marker_at, ['token_usage_record', 100, None, 0])
    return rows


def fixture(marker_at=5):
    measured = r.measure(synthetic_usage(marker_at), 'codex')
    controls = {'roles': ['developer', 'user', 'user'], 'first_user_is_environment': True,
                'leading_role_content_sha256': 'a' * 64, 'task_content_sha256': 'b' * 64}
    roles = {k: measured[k] for k in ('event_count', 'response_item_count', 'closed_turns', 'per_type_bytes')}
    roles.update({key: controls[key] for key in r.CONTROLS}, r3_total_bytes=732,
                 message_by_role_bytes={'assistant': 30, 'developer': 100, 'user': 140},
                 family_bytes={'m_star': 222, 'environment': 510})
    return measured, controls, roles


class DiagnosticTests(unittest.TestCase):
    def test_inclusive_100_and_tied_endpoints(self):
        on = r.compare([10, 110, 110])
        self.assertEqual((on['range_b'], on['status'], r.endpoints(on)), (100, 'pass', ([1], [2, 3])))
        self.assertEqual(r.compare([10, 111, 110])['status'], 'fail')
        self.assertEqual(r.endpoints(r.compare([8, 8, 8])), ([1, 2, 3], [1, 2, 3]))

    def test_subtracted_projection_must_reselect_endpoints(self):
        before, after = [500, 501, 900], [300, 450, 300]
        self.assertEqual(r.endpoints(r.compare(before)), ([1], [3]))
        self.assertEqual(abs(after[2] - after[0]), 0)  # Wrong shortcut at old endpoints.
        result = r.compare(after)
        self.assertEqual((result['range_b'], result['status'], r.endpoints(result)),
                         (150, 'fail', ([1, 3], [2])))

    def test_less_per_slot_can_raise_group_spread(self):
        self.assertEqual(r.compare([350, 350, 350])['status'], 'pass')
        self.assertEqual(r.compare([200, 320, 320])['status'], 'fail')

    def test_unknown_slot_does_not_pass_or_fail_group(self):
        partial = r.compare([100, None, 600])
        self.assertEqual((partial['status'], partial['range_b'], r.endpoints(partial)),
                         ('unknown', None, ([], [])))

    def test_reject_wrong_repetition_count_boolean_and_negative(self):
        for values in ([100, 100], [100, True, 100], [100, -1, 100]):
            with self.subTest(values=values), self.assertRaises(r.Invalid):
                r.compare(values)


class ProjectionTests(unittest.TestCase):
    def test_role_aware_exclusion_is_not_subtracting_r4(self):
        measured, controls, roles = fixture()
        slot = r.codex_layers(measured, controls, roles, 'synthetic')
        self.assertEqual(measured['output_bytes'], 312)
        self.assertEqual(slot['values'], {'r3': 732, 'without_model': 510, 'without_tool_results': 462,
                                         'startup_core': 240, 'without_both': 240, 'first_usage_segment': 282})
        self.assertEqual(slot['first_usage_model_lower_bound_b'], 42)
        self.assertEqual(slot['trailing_unclosed_b'], 450)
        self.assertNotEqual(732 - 312, slot['values']['without_model'])

    def test_no_usage_still_counts_all_r3_but_segment_unknown(self):
        slot = r.codex_layers(*fixture(marker_at=None), 'synthetic')
        self.assertEqual(slot['values']['r3'], 732)
        self.assertEqual(slot['trailing_unclosed_b'], 732)
        self.assertEqual(slot['values']['startup_core'], 240)
        self.assertIsNone(slot['values']['first_usage_segment'])
        self.assertIsNone(slot['first_usage_model_lower_bound_b'])

    def test_early_empty_usage_cannot_be_replaced_by_later_segment(self):
        rows = synthetic_usage(marker_at=1)
        rows.append(['token_usage_record', 100, None, 0])
        _, controls, roles = fixture()
        measured = r.measure(rows, 'codex')
        roles['event_count'] += 1
        roles['closed_turns'] = 2
        slot = r.codex_layers(measured, controls, roles, 'synthetic')
        self.assertEqual((slot['values']['startup_core'], slot['values']['r3']), (240, 732))
        self.assertIsNone(slot['values']['first_usage_segment'])

    def test_reject_unmapped_subtype_and_non_response_payload(self):
        for row in (['response_item', 81, 'another_type', 42], ['other', 81, None, 42]):
            with self.subTest(row=row), self.assertRaises(r.Invalid):
                r.measure(synthetic_usage() + [row], 'codex')

    def test_missing_control_only_removes_anchor_dependent_projections(self):
        measured, controls, roles = fixture()
        del roles['task_content_sha256']
        slot = r.codex_layers(measured, controls, roles, 'synthetic')
        self.assertEqual(slot['values']['without_both'], 240)
        self.assertIsNone(slot['values']['startup_core'])
        self.assertIsNone(slot['values']['first_usage_segment'])

    def test_same_lengths_with_different_valid_controls_is_not_shared_core(self):
        measured, controls, roles = fixture()
        first = r.codex_layers(measured, controls, roles, 'synthetic')
        controls['task_content_sha256'] = roles['task_content_sha256'] = 'c' * 64
        other = r.codex_layers(measured, controls, roles, 'synthetic')
        self.assertEqual(first['values'], other['values'])
        result = r.codex_group([first, other, first])
        self.assertFalse(result['shared_startup_control'])
        self.assertIsNone(result['without_both_equals_startup_all_slots'])
        self.assertEqual(result['layers']['startup_core']['status'], 'unknown')
        self.assertEqual(result['layers']['without_both']['status'], 'pass')

    def test_conflicting_role_source_control_does_not_compute(self):
        measured, controls, roles = fixture()
        roles['task_content_sha256'] = 'c' * 64
        with self.assertRaisesRegex(r.Invalid, 'conflicting control binding'):
            r.codex_layers(measured, controls, roles, 'synthetic')

    def test_inconsistent_role_accounting_does_not_compute(self):
        measured, controls, roles = fixture()
        roles['message_by_role_bytes']['assistant'] += 1
        with self.assertRaisesRegex(r.Invalid, 'role totals do not reconcile'):
            r.codex_layers(measured, controls, roles, 'synthetic')


class BindingTests(unittest.TestCase):
    def test_reject_duplicate_missing_and_mixed_identities(self):
        for actual, error in ((['a', 'a'], 'duplicate'), (['a'], 'missing'), (['a', 'c'], 'mixed')):
            with self.subTest(actual=actual), self.assertRaisesRegex(r.Invalid, error):
                r.unique_index(actual, lambda value: value, {'a', 'b'}, 'fixture')

    def test_unpinned_bytes_do_not_reach_parser(self):
        with patch.object(Path, 'read_bytes', return_value=b'not JSON'), patch.object(r.json, 'loads') as loads:
            with self.assertRaisesRegex(r.Invalid, 'SHA-256 mismatch'):
                r.read_pinned(ROOT, *r.FILES['events'])
        loads.assert_not_called()

    def test_unavailable_input_is_not_an_empty_measurement(self):
        with patch.object(Path, 'read_bytes', side_effect=FileNotFoundError):
            with self.assertRaisesRegex(r.Invalid, 'input unavailable'):
                r.read_pinned(ROOT, *r.FILES['events'])


class FixedPublicReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = {key: r.read_pinned(ROOT, *binding) for key, binding in r.FILES.items()}
        cls.result = r.analyze(cls.data['events'], cls.data['old_gate'], cls.data['roles'])

    def test_reject_cross_slot_trace_binding_even_with_same_byte_values(self):
        old = self.data['old_gate']
        a, b, *rest = old['slots']
        broken = dict(old, slots=[dict(a, trace_sha256=b['trace_sha256']), b, *rest])
        with self.assertRaisesRegex(r.Invalid, 'trace_sha256 mismatch'):
            r.analyze(self.data['events'], broken, self.data['roles'])

    def test_historical_gate_is_not_upgraded_by_new_layers(self):
        self.assertEqual(self.result['n_slots'], 30)
        self.assertEqual(self.result['old_and_counts'], {'pass': 0, 'fail': 6, 'unverifiable': 4})
        self.assertFalse(self.result['old_and_upgraded'])
        self.assertTrue(all(g['old_sequence'] is None for arm in r.ARMS for g in self.result[arm]))

    def test_six_new_layer_diagnostics_over_five_groups(self):
        expected = [[154301, 9725, 144576, 0, 0, 2726], [296848, 49682, 247167, 1, 1, 1893],
                    [31431, 27407, 4025, 1, 1, 895], [165538, 9223, 156314, 1, 1, 1305],
                    [471897, 49972, 421925, 1, 1, 2306]]
        self.assertEqual([[g['layers'][layer]['range_b'] for layer in r.LAYERS]
                          for g in self.result['codex']], expected)
        for layer in r.LAYERS:
            n = 5 if layer in ('startup_core', 'without_both') else 0
            self.assertEqual(self.result['codex_aux_counts'][layer], {'pass': n, 'fail': 5 - n, 'unknown': 0})
        for group in self.result['codex']:
            self.assertTrue(group['shared_startup_control'])
            self.assertTrue(group['without_both_equals_startup_all_slots'])
            for layer in ('without_model', 'without_tool_results'):
                self.assertFalse(group['layers'][layer]['endpoints_changed_from_r3'])
            for layer in ('startup_core', 'without_both', 'first_usage_segment'):
                self.assertTrue(group['layers'][layer]['endpoints_changed_from_r3'])

    def test_actual_bird_old_endpoints_would_reverse_diagnostic(self):
        layers = self.result['codex'][0]['layers']
        first = layers['first_usage_segment']
        self.assertEqual(r.endpoints(layers['r3']), ([1], [2]))
        self.assertEqual(first['values_b'], [8164, 8102, 10828])
        self.assertEqual(abs(first['values_b'][1] - first['values_b'][0]), 62)
        self.assertEqual((r.endpoints(first), first['range_b'], first['status']), (([2], [3]), 2726, 'fail'))

    def test_earliest_usage_segment_includes_generated_payload_not_first_request(self):
        lower = [b for g in self.result['codex'] for b in g['first_usage_model_lower_bound_b']]
        self.assertEqual((len(lower), min(lower), max(lower)), (15, 739, 3390))
        for key in ('first_request_body', 'actual_backend_ingestion', 'controlled_harness_effect'):
            self.assertEqual(self.result[key], 'unknown')

    def test_dsh_localizes_s3_without_reopening_the_sequence_gate(self):
        groups = self.result['dsh']
        self.assertEqual([g['s3']['range_b'] for g in groups], [0, 956, 0, 0, 0])
        self.assertTrue(all(g['legacy_session_only'] and g['narrow_boundary_equal'] and
                            not g['step_tool_assistant_equal'] for g in groups))
        dab = groups[1]
        self.assertEqual(dab['old_and'], 'fail')
        self.assertEqual([v['user/message'] for v in dab['s3_by_type']],
                         [{'bytes': 9977, 'events': 5}, {'bytes': 9021, 'events': 3}, {'bytes': 9021, 'events': 3}])
        self.assertTrue(all(v['request/header'] == {'bytes': 17906, 'events': 1} and
                            v['request/context'] == {'bytes': 179, 'events': 1} for v in dab['s3_by_type']))


if __name__ == '__main__':
    unittest.main()
