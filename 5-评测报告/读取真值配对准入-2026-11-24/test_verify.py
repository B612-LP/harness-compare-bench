"""Standard-library regression tests; mutations are in-memory, never real reads of a fixture."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

# Isolated mode omits the script's directory; use the resolved local sibling only.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify as v


class AdmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = v.read_inputs()['fixture']
        cls.report = v.run()

    def local(self, change=None, clock=True):
        row, target = deepcopy(self.fixture['pairs'][0]), self.fixture['target']
        if change is not None:
            change(row)
        return row, v.fixture_pair(row, target, clock)

    def test_inventory_and_identity_scopes(self):
        groups = self.report['product_groups']
        nine = groups['product-11-19']
        self.assertEqual((nine['registered'], nine['complete']), (9, 8))
        self.assertEqual(nine['object_evidence'], {'different_assignment': 8, 'unknown': 1})
        self.assertEqual(self.report['older_11_19_direction_control_only'], {'count': 2, 'complete_denominator': 8})
        cli, desk = groups['cli-11-20']['strata'], groups['desktop-11-20']['strata']
        self.assertEqual(cli['DSH']['object_evidence'], {'different_key': 4, 'unknown': 1})
        self.assertEqual(cli['Codex CLI']['object_evidence'], {'same_key': 5})
        self.assertEqual(desk['WorkBuddy']['object_evidence'], {'same_key': 8, 'unknown': 2})
        db = desk['豆包工作']
        self.assertEqual(db['available_outer'], {'disjoint': 5})
        self.assertEqual(db['full_outer'], {'unanchored': 5})
        self.assertEqual(db['object_evidence'], {'unknown': 5})
        total = self.report['product_inventory_sum']
        self.assertEqual((total['registered'], total['complete']), (34, 33))
        self.assertEqual(total['available_outer'], {'disjoint': 33, 'unknown': 1})
        self.assertEqual(total['full_outer'], {'disjoint': 28, 'unanchored': 5, 'unknown': 1})
        self.assertEqual(total['object_evidence'], {'same_key': 13, 'different_key': 4, 'different_assignment': 8, 'unknown': 9})
        self.assertTrue(all(g['admitted'] == g['certified_independent_content_pairs'] == 0 for g in groups.values()))

    def test_direction_control_requires_each_arm_to_avoid_its_other_target(self):
        nov19 = v.read_inputs()['nov19']
        row = next(r for r in nov19['pairs'] if r['old_hit_direction_control'])
        self.assertEqual(v.historical_nine(nov19)[1], 2)
        nov19['runs'][row['positive_arm']]['fd_hits']['b'] += 1
        self.assertEqual(v.historical_nine(nov19)[1], 1)

    def test_every_one_or_two_axis_assumption(self):
        groups = self.report['product_groups']
        keys = {'C', 'W', 'O', 'T', 'C+W', 'C+O', 'C+T', 'W+O', 'W+T', 'O+T'}
        for name, expected in [('product-11-19', 0), ('cli-11-20', 5), ('desktop-11-20', 8), ('sum', 13)]:
            row = self.report['product_inventory_sum'] if name == 'sum' else groups[name]
            grids = row['upper_ceiling_by_perfected_axes']
            self.assertEqual(set(grids), set(v.MODES))
            for mode, grid in grids.items():
                with self.subTest(name=name, mode=mode):
                    self.assertEqual(set(grid), keys)
                    ceiling = expected if mode == 'archive_key_relaxed_replacement' else 0
                    self.assertEqual(grid, {k: ceiling if k == 'W+T' else 0 for k in keys})

    def test_historical_evidence_cannot_reverse_refuted_axis(self):
        bound = v.ProductBlock(1, True, 'disjoint', 'disjoint', 'same_key')
        self.assertEqual(v.scenario([bound], ('W', 'O', 'T'), v.MODES[1]), 1)
        self.assertEqual(v.scenario([bound], ('W', 'O', 'T'), v.MODES[2]), 0)
        unfired = v.ProductBlock(1, False, v.UNKNOWN, v.UNKNOWN, v.UNKNOWN)
        self.assertEqual(v.scenario([unfired], v.AXES, v.MODES[1]), 1)
        self.assertEqual(v.scenario([unfired], v.AXES, v.MODES[2]), 0)

    def test_pinned_non_product_replay(self):
        control = self.report['non_product_control']
        self.assertEqual(control['long']['observation'], 'same_fd_visibility')
        self.assertEqual(control['long']['axes'], dict.fromkeys(v.AXES, v.PASSED))
        self.assertTrue(control['long']['admitted'])
        short = control['short']
        self.assertFalse(short['admitted'])
        self.assertEqual(short['observation'], v.UNKNOWN)
        self.assertEqual(short['axes'], {'C': v.PASSED, 'O': v.PASSED, 'T': v.PASSED, 'W': v.REFUTED})
        self.assertIn('not_both_open_before_action', short['window_notes'])
        self.assertIn('whole_capture_not_contained', short['window_notes'])
        self.assertIn('capture_unusable', short['window_notes'])

    def assert_expected_window_failure(self, result, reason):
        self.assertFalse(result['admitted'])
        self.assertEqual(result['axes'], {'C': v.PASSED, 'W': v.REFUTED, 'O': v.PASSED, 'T': v.PASSED})
        self.assertIn(reason, result['window_notes'])

    @staticmethod
    def broad_window(row):
        return v.interval_relation(*(tuple(a[k] for k in ('open_start_ns', 'close_end_ns')) for a in row['arms']))

    def test_wide_outer_intersection_does_not_put_both_arms_in_action_phase(self):
        row, result = self.local(lambda r: r['arms'][0].update(action_start_ns=4_000_000, action_end_ns=4_010_000,
                                                               post_fstat_ns=4_020_000))
        self.assertEqual(self.broad_window(row), 'positive_overlap')
        self.assert_expected_window_failure(result, 'not_both_open_before_action')
        self.assertNotIn('whole_capture_not_contained', result['window_notes'])

    def test_capture_straddles_narrow_right_boundary_with_broad_overlap(self):
        row, result = self.local(lambda r: r['sample'].update(end_ns=r['planned_hold_ns'] + 1))
        self.assertEqual(self.broad_window(row), 'positive_overlap')
        self.assert_expected_window_failure(result, 'whole_capture_not_contained')
        self.assertEqual(result['window_notes'], ['whole_capture_not_contained'])

    def test_exit_failure_and_unanchored_clock_keep_object_and_truth(self):
        _, failed = self.local(lambda r: r['sample'].update(exit=1))
        _, unanchored = self.local(clock=False)
        for item, code in [(failed, 'capture_unusable'), (unanchored, 'unanchored_clock')]:
            self.assertEqual(item['axes'], {'C': v.PASSED, 'W': v.UNKNOWN, 'O': v.PASSED, 'T': v.PASSED})
            self.assertEqual(item['window_notes'], [code])
            self.assertFalse(item['admitted'])

    def test_same_lexical_path_can_be_different_objects(self):
        path, p_key, n_key = 'same/fixture', v.ObjectKey('mount+trial', (2, 9)), v.ObjectKey('mount+trial', (2, 10))
        anchor = v.Anchor('synthetic', 'p/n', 'p', 'n', path, 'sampled_phase')
        local_identity = v.same_object(p_key, n_key, p_key)
        axes = v.joint_axes(anchor, [v.Fact(anchor, a, local_identity if a == 'O' else v.PASSED) for a in v.AXES])
        self.assertEqual(axes, {'C': v.PASSED, 'W': v.PASSED, 'O': v.REFUTED, 'T': v.PASSED})
        self.assertFalse(v.admitted(axes))
        self.assertEqual(v.same_object(p_key, v.ObjectKey('other_mount', p_key.token), p_key), v.UNKNOWN)

    def test_valid_axes_from_other_bindings_cannot_be_pooled(self):
        anchor = v.Anchor('synthetic', 'same-label', 'positive', 'negative', 'target', 'linked_phase')
        other_arm = replace(anchor, positive_arm='different_positive')
        other_target = replace(anchor, target='different_target')
        other_phase = replace(anchor, window='different_phase_with_same_arms_and_target')
        facts = [v.Fact(anchor, 'C', v.PASSED), v.Fact(anchor, 'W', v.PASSED),
                 v.Fact(other_arm, 'O', v.PASSED), v.Fact(other_target, 'T', v.PASSED),
                 v.Fact(other_phase, 'O', v.PASSED), v.Fact(other_phase, 'T', v.PASSED)]
        self.assertEqual({f.axis for f in facts if f.state == v.PASSED}, set(v.AXES))  # A pooled AND would pass.
        self.assertFalse(any(v.admitted(v.joint_axes(a, facts)) for a in (anchor, other_arm, other_target, other_phase)))
        self.assertEqual(v.joint_axes(anchor, facts), {'C': v.PASSED, 'W': v.PASSED, 'O': v.UNKNOWN, 'T': v.UNKNOWN})
        self.assertEqual(v.joint_axes(other_arm, facts)['O'], v.PASSED)
        self.assertEqual(v.joint_axes(other_target, facts)['T'], v.PASSED)
        self.assertEqual(v.joint_axes(other_phase, facts), {'C': v.UNKNOWN, 'W': v.UNKNOWN, 'O': v.PASSED, 'T': v.PASSED})

    def test_fd_flags_or_stored_labels_do_not_make_action_truth(self):
        _, bad_truth = self.local(lambda r: r['arms'][1].update(action='unverified_branch'))
        self.assertEqual(bad_truth['axes'], {'C': v.PASSED, 'W': v.PASSED, 'O': v.PASSED, 'T': v.UNKNOWN})
        self.assertFalse(bad_truth['admitted'])
        _, without_hit = self.local(lambda r: r['sample'].update(exact_FD_target_matches_read_then_open_only=[True, False]))
        self.assertTrue(without_hit['admitted'])
        self.assertEqual(without_hit['observation'], v.UNKNOWN)
        _, old_label = self.local(lambda r: r.update(decision='unknown', truth_pair_qualified=False))
        self.assertTrue(old_label['admitted'])

    def test_touch_is_not_positive_overlap_and_zero_capture_refuses(self):
        self.assertEqual(v.interval_relation((1, 10), (10, 11)), 'touch_only')
        self.assertEqual(v.interval_relation((1, 10), (11, 12)), 'disjoint')
        _, result = self.local(lambda r: r['sample'].update(end_ns=r['sample']['start_ns']))
        self.assert_expected_window_failure(result, 'whole_capture_not_contained')

    def test_source_hash_mismatch_is_explicit_even_without_assertions(self):
        path, _ = v.SOURCES['fixture']
        with patch.dict(v.SOURCES, {'fixture': (path, '0' * 64)}), self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
            v.read_inputs()


if __name__ == '__main__':
    unittest.main()
