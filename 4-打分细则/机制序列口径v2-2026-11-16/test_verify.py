#!/usr/bin/env python3
"""Stdlib regression/negative tests for the v2.1 sequence adjudication.
No products, network, subprocess or historical tools. Runnable under python3 and python3 -O.
"""
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V11_HERE = ROOT / '4-打分细则' / '机制重复口径澄清-2026-11-12'
spec = importlib.util.spec_from_file_location('seqv2_verify', HERE / 'verify.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

FROZEN_I = frozenset(('user/message', 'request/header', 'request/context', 'system/message', 'agent/inbox/spliced'))
FROZEN_K = frozenset(('turn/start', 'turn/end', 'step/start', 'step/end', 'assistant/message', 'tool/call', 'tool/result'))
FROZEN_M = frozenset(('session', 'session/title', 'permission/preset', 'sandbox/mode', 'approval/policy',
                      'session-log-deepseek/delivery-accepted', 'session/title-llm-request', 'subagent/catalog'))
OBSERVED_UNION = {'agent/inbox/spliced': 34, 'approval/policy': 15, 'assistant/message': 338, 'permission/preset': 15,
                  'request/context': 15, 'request/header': 15, 'sandbox/mode': 15, 'session': 15,
                  'session-log-deepseek/delivery-accepted': 347, 'session/title': 24, 'session/title-llm-request': 9,
                  'step/end': 338, 'step/start': 338, 'subagent/catalog': 1, 'system/message': 15,
                  'tool/call': 367, 'tool/result': 367, 'turn/end': 15, 'turn/start': 15, 'user/message': 47}
PINNED_B1_MM = {'bird-ca-schools-15': 0, 'dabstep-payments-10': 956, 'exercism-py-6': 0,
                'lcb-recent-hard-4': 0, 'tb-cargo-plan': 0}
PINNED_K_MM = {'bird-ca-schools-15': 414641, 'dabstep-payments-10': 743691, 'exercism-py-6': 70124,
               'lcb-recent-hard-4': 141600, 'tb-cargo-plan': 939597}
SLOT_KEYS = {'slot', 'case', 'rep', 'status', 'trace_sha256', 'meta_batch_label', 'aggregate_path', 'event_count',
             'type_counts', 's3_bytes', 'i_event_count', 'i_bytes', 'i_sequence', 'i_sequence_sha256',
             'k_event_count', 'k_bytes', 'k_sequence', 'k_sequence_sha256', 'm_event_count', 'm_bytes'}
GROUP_KEYS = {'case', 'arm', 'n', 'rep', 's3_bytes', 'b1_max_minus_min', 'b1_pass', 's1_pass', 'i_sequence_sha256',
              'i_bytes', 'b2_max_minus_min', 'b2_pass', 'gate_v2', 'd_sequence_all_equal', 'k_sequence_sha256',
              'k_bytes', 'k_bytes_max_minus_min', 'k_bytes_max_min_ratio'}
TOP_KEYS = {'schema', 'baseline_commit', 'protocol', 'contract', 'note', 'coverage', 'v11_crosscheck', 'v2_gate',
            'prereg_section3_branches', 'groups', 'slots', 'source_bindings', 'evidence_sha256', 'limitations'}


def synth_row(rep, s3, i_bytes, k_bytes, i_seq, k_seq):
    return {'rep': rep, 's3_bytes': s3, 'i_bytes': i_bytes, 'k_bytes': k_bytes,
            'i_sequence': i_seq, 'i_sequence_sha256': v.sha(v.canon(i_seq)),
            'k_sequence': k_seq, 'k_sequence_sha256': v.sha(v.canon(k_seq))}


def synth_group(s3_values, i_bytes_values, i_seqs=None, k_bytes_values=None):
    i_seqs = i_seqs or [['user/message', 'request/header', 'request/context']] * 3
    k_bytes_values = k_bytes_values or [500, 500, 500]
    k_seq = ['turn/start', 'turn/end']
    return [synth_row(rep, s3, ib, kb, iseq, k_seq)
            for rep, (s3, ib, kb, iseq) in enumerate(
                zip(s3_values, i_bytes_values, k_bytes_values, i_seqs + i_seqs[len(i_bytes_values):]), start=1)]


class SeqV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = v.analyze(ROOT)
        cls.evidence = json.loads((V11_HERE / 'evidence.json').read_bytes())
        cls.v11 = json.loads((V11_HERE / 'result.json').read_bytes())

    def temporary(self):
        return tempfile.TemporaryDirectory(dir=os.environ.get('B_TEST_TMPDIR'))

    # ---- frozen partition constants ----

    def test_01_partition_constants_frozen(self):
        self.assertEqual(v.I_TYPES, FROZEN_I)
        self.assertEqual(v.K_TYPES, FROZEN_K)
        self.assertEqual(v.M_TYPES, FROZEN_M)
        self.assertFalse(v.I_TYPES & v.K_TYPES or v.I_TYPES & v.M_TYPES or v.K_TYPES & v.M_TYPES)
        self.assertTrue(v.S3_TYPES <= v.I_TYPES)
        self.assertEqual(v.PARTITION_TYPES, FROZEN_I | FROZEN_K | FROZEN_M)

    def test_02_real_coverage_complete_and_unknown_free(self):
        self.assertEqual(self.result['coverage']['union_type_counts'], OBSERVED_UNION)
        self.assertEqual(self.result['coverage']['union_size'], 20)
        self.assertEqual(self.result['coverage']['total_events'], 2345)
        self.assertEqual(self.result['coverage']['unknown_types'], [])
        self.assertEqual(set(self.result['coverage']['union_type_counts']), v.PARTITION_TYPES)

    def test_03_real_scope_15_slots_5_groups_n3(self):
        self.assertEqual(len(self.result['slots']), 15)
        self.assertEqual(len(self.result['groups']), 5)
        self.assertEqual([g['n'] for g in self.result['groups']], [3] * 5)
        self.assertTrue(all(g['rep'] == [1, 2, 3] for g in self.result['groups']))
        self.assertEqual({row['slot'] for row in self.result['slots']}, set(v.expected_slots()))

    # ---- synthetic boundary / branch behavior ----

    def test_04_b1_boundary_100_inclusive_pass(self):
        group = v.group_verdict('synth', synth_group([0, 100, 50], [10, 10, 10]))
        self.assertTrue(group['b1_pass'] and group['gate_v2'] == 'pass')

    def test_05_b1_boundary_101_fails(self):
        group = v.group_verdict('synth', synth_group([0, 101, 50], [10, 10, 10]))
        self.assertFalse(group['b1_pass'] and group['gate_v2'] == 'fail')

    def test_06_b2_boundary_100_inclusive_pass(self):
        group = v.group_verdict('synth', synth_group([300, 300, 300], [300, 250, 350]))
        self.assertTrue(group['b2_pass'] and group['b2_max_minus_min'] == 100)

    def test_07_b2_over_100_detected_branch_b1_pass_b2_fail(self):
        group = v.group_verdict('synth', synth_group([300, 300, 300], [300, 300, 401]))
        self.assertFalse(group['b2_pass'])
        self.assertTrue(group['b1_pass'] and group['s1_pass'])
        self.assertEqual(group['gate_v2'], 'fail')

    def test_08_s1_drift_synthetic_detected(self):
        drifted = [['user/message', 'request/header', 'request/context'],
                   ['user/message', 'request/header', 'request/context'],
                   ['user/message', 'user/message', 'request/header', 'request/context']]
        group = v.group_verdict('synth', synth_group([300, 300, 300], [300, 300, 300], i_seqs=drifted))
        self.assertFalse(group['s1_pass'])
        self.assertTrue(group['b1_pass'] and group['b2_pass'])  # README §3 branch 2 shape
        self.assertEqual(group['gate_v2'], 'fail')

    # ---- fail-closed partition enforcement ----

    def test_09_unknown_type_fail_closed_lists_slot_and_type(self):
        with self.assertRaises(v.Invalid) as caught:
            v.measure_slot('dsh__synth-case__r1', [['session', 10, None, 0], ['bogus/type', 5, None, 0]])
        self.assertIn('dsh__synth-case__r1', str(caught.exception))
        self.assertIn('bogus/type', str(caught.exception))

    def test_10_unknown_type_injection_into_real_fixture_rejected(self):
        events = copy.deepcopy(self.evidence['slots'][0]['events'])
        events.append(['mystery/event', 7, None, 0])
        slot = self.evidence['slots'][0]['slot']
        with self.assertRaises(v.Invalid) as caught:
            v.measure_slot(slot, events)
        self.assertIn(slot, str(caught.exception))
        self.assertIn('mystery/event', str(caught.exception))

    def test_11_coverage_check_collects_before_verdicts(self):
        rows = [('dsh__a__r1', [['session', 5, None, 0]]),
                ('dsh__b__r1', [['session/title', 5, None, 0], ['other/thing', 5, None, 0]])]
        with self.assertRaises(v.Invalid) as caught:
            v.check_partition_coverage(rows)
        text = str(caught.exception)
        self.assertIn('dsh__b__r1', text)
        self.assertIn('other/thing', text)
        good = [('dsh__a__r1', [['session', 5, None, 0]]), ('dsh__b__r1', [['subagent/catalog', 5, None, 0]])]
        union = v.check_partition_coverage(good)
        self.assertEqual(union, {'session': 1, 'subagent/catalog': 1})

    def test_12_malformed_projection_rows_rejected(self):
        slot = 'dsh__synth__r1'
        with self.assertRaises(v.Invalid):
            v.measure_slot(slot, [['session', 0, None, 0]])
        with self.assertRaises(v.Invalid):
            v.measure_slot(slot, [['session', 5, 'payload.type', 3]])
        with self.assertRaises(v.Invalid):
            v.measure_slot(slot, [['session', 5, None]])

    # ---- source binding and pinning ----

    def test_13_tampered_source_rejected(self):
        with self.temporary() as directory:
            root = Path(directory)
            (root / 'source.json').write_text('{"x":2}')
            record = {'path': 'source.json', 'sha256': v.sha(b'{"x":1}')}
            with self.assertRaises(v.Invalid):
                v.bound_json(root, record)

    def test_14_missing_source_rejected(self):
        with self.temporary() as directory:
            with self.assertRaises(v.Invalid):
                v.bound_json(Path(directory), {'path': 'missing.json', 'sha256': '0' * 64})

    def test_15_evidence_and_v11_result_sha_pins_enforced(self):
        with patch.object(v, 'EVIDENCE_SHA256', '0' * 64):
            with self.assertRaises(v.Invalid):
                v.analyze(ROOT)
        with patch.object(v, 'V11_RESULT_SHA256', '0' * 64):
            with self.assertRaises(v.Invalid):
                v.analyze(ROOT)

    def test_16_slot_or_group_count_change_rejected(self):
        rows = copy.deepcopy(self.evidence['slots'])
        with self.assertRaises(v.Invalid):
            v.validate_evidence_slots(rows[:-1])
        rows[0]['slot'] = 'dsh__new-case__r1'
        with self.assertRaises(v.Invalid):
            v.validate_evidence_slots(rows)
        scope = [{'slot': s} for s in v.expected_slots()][:-1]
        with self.assertRaises(v.Invalid):
            v.check_scope(scope)
        mixed = [{'slot': 'dsh__new-case__r1'}] + scope[1:]
        with self.assertRaises(v.Invalid):
            v.check_scope(mixed)

    def test_17_b1_crosscheck_mismatch_rejected(self):
        groups = copy.deepcopy(self.result['groups'])
        slots = copy.deepcopy(self.result['slots'])
        v.crosscheck_v11(self.v11, slots, groups)  # sanity: real values pass
        groups[0]['b1_max_minus_min'] = 1
        with self.assertRaises(v.Invalid):
            v.crosscheck_v11(self.v11, slots, groups)
        groups[0]['b1_max_minus_min'] = 0
        slots[0]['s3_bytes'] += 1
        with self.assertRaises(v.Invalid):
            v.crosscheck_v11(self.v11, slots, groups)

    def test_18_identity_negatives_rejected(self):
        slot = 'dsh__bird-ca-schools-15__r1'
        row = next(r for r in self.evidence['slots'] if r['slot'] == slot)
        meta = json.loads((ROOT / v.BATCH / 'runs' / slot / 'meta.public-derived.json').read_bytes())
        account = next(r for r in json.loads(
            (ROOT / v.BATCH / 'observe/trace-accounting-summary.json').read_bytes())['dsh']['incidents']
            if r['slot'] == slot)
        receipt = next(r['identity'] for r in json.loads((ROOT / v.BATCH / 'adjudications.json').read_bytes())
                       if r['identity']['run_id'] == 'r1109-dsh-bird-ca-schools-15-r1')
        v.check_identity(slot, meta, row['identity'], account, receipt)
        wrong_path = copy.deepcopy(row['identity'])
        wrong_path['source_relative_to_archive'] = 'dsh/runs/other/agent-session/session.v4.jsonl.zstd'
        with self.assertRaises(v.Invalid):
            v.check_identity(slot, meta, wrong_path, account, receipt)
        wrong_id = copy.deepcopy(row['identity'])
        wrong_id['id'] = 'not-the-pinned-session-id'
        with self.assertRaises(v.Invalid):
            v.check_identity(slot, meta, wrong_id, account, receipt)
        wrong_meta = copy.deepcopy(meta); wrong_meta['rep'] = '2'
        with self.assertRaises(v.Invalid):
            v.check_identity(slot, wrong_meta, row['identity'], account, receipt)

    def test_19_aggregate_crosscheck_enforced(self):
        slot = self.result['slots'][0]
        aggregate = json.loads((ROOT / slot['aggregate_path']).read_bytes())
        v.check_aggregate(slot['slot'], aggregate, slot)  # sanity: real values pass
        tampered = copy.deepcopy(aggregate)
        tampered['per_file'][0]['s3']['input_bytes'] += 1
        with self.assertRaises(v.Invalid):
            v.check_aggregate(slot['slot'], tampered, slot)
        tampered = copy.deepcopy(aggregate)
        tampered['per_file'][0]['s2']['type_counts'] = {}
        with self.assertRaises(v.Invalid):
            v.check_aggregate(slot['slot'], tampered, slot)

    # ---- real adjudication regression (pinned verdict table) ----

    def test_20_real_b1_equals_v1_1_pinned_values(self):
        for group in self.result['groups']:
            self.assertEqual(group['b1_max_minus_min'], PINNED_B1_MM[group['case']])
        v11_s3 = {row['slot']: row['input_bytes'] for row in self.v11['slots'] if row['arm'] == 'dsh'}
        for row in self.result['slots']:
            self.assertEqual(row['s3_bytes'], v11_s3[row['slot']])

    def test_21_real_gate_4_of_5_with_dabstep_negative_control(self):
        self.assertEqual(self.result['v2_gate']['verdict_by_case'],
                         {'bird-ca-schools-15': 'pass', 'dabstep-payments-10': 'fail',
                          'exercism-py-6': 'pass', 'lcb-recent-hard-4': 'pass', 'tb-cargo-plan': 'pass'})
        self.assertEqual(self.result['v2_gate']['pass_count'], 4)
        dab = next(g for g in self.result['groups'] if g['case'] == 'dabstep-payments-10')
        self.assertFalse(dab['b1_pass'] and dab['s1_pass'] and dab['b2_pass'])
        self.assertEqual((dab['b1_max_minus_min'], dab['b2_max_minus_min']), (956, 2240))
        for group in self.result['groups']:
            if group['case'] != 'dabstep-payments-10':
                self.assertTrue(group['b1_pass'] and group['s1_pass'] and group['b2_pass'])
        self.assertEqual(self.result['prereg_section3_branches'],
                         {'b1_pass_b2_fail': [], 's1_fail_b2_pass': [], 'd_seq_equal_k_bytes_vary': []})

    def test_22_real_dabstep_s1_drift_localized(self):
        dab = sorted([s for s in self.result['slots'] if s['case'] == 'dabstep-payments-10'], key=lambda s: s['rep'])
        self.assertEqual([len(s['i_sequence']) for s in dab], [14, 8, 8])
        self.assertEqual(dab[1]['i_sequence'], dab[2]['i_sequence'])
        self.assertEqual(dab[0]['i_sequence'][:8], dab[1]['i_sequence'])
        self.assertEqual(dab[0]['i_sequence'][8:],
                         ['agent/inbox/spliced', 'agent/inbox/spliced', 'user/message',
                          'agent/inbox/spliced', 'agent/inbox/spliced', 'user/message'])

    def test_23_real_d_descriptive_k_bytes(self):
        for group in self.result['groups']:
            self.assertFalse(group['d_sequence_all_equal'])
            self.assertEqual(group['k_bytes_max_minus_min'], PINNED_K_MM[group['case']])
            self.assertGreater(group['k_bytes_max_min_ratio'], 1.0)

    # ---- content-free hygiene ----

    def test_24_projection_is_content_free(self):
        self.assertEqual(set(self.result), TOP_KEYS)
        for row in self.result['slots']:
            self.assertEqual(set(row), SLOT_KEYS)
            self.assertTrue(set(row['type_counts']) <= v.PARTITION_TYPES)
            self.assertTrue(set(row['i_sequence']) <= v.I_TYPES)
            self.assertTrue(set(row['k_sequence']) <= v.K_TYPES)
        for group in self.result['groups']:
            self.assertEqual(set(group), GROUP_KEYS)

    # ---- determinism and CLI ----

    def test_25_stored_result_and_deterministic_replay(self):
        self.assertEqual(self.result, json.loads((HERE / 'result.json').read_bytes()))
        self.assertEqual(v.canon(self.result), v.canon(v.analyze(ROOT)))
        self.assertEqual(v.canon(v.analyze(ROOT)), v.canon(v.analyze(ROOT)))

    def test_26_cli_stdout_and_write_once(self):
        expected = json.dumps(self.result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n'
        out = io.StringIO()
        with patch('sys.stdout', out):
            self.assertEqual(v.main(['--root', str(ROOT)]), 0)
        self.assertEqual(out.getvalue(), expected)
        with self.temporary() as directory:
            path = Path(directory) / 'new.json'
            self.assertEqual(v.main(['--root', str(ROOT), '--output', str(path)]), 0)
            before = path.read_bytes()
            with patch('sys.stderr', io.StringIO()):
                self.assertEqual(v.main(['--root', str(ROOT), '--output', str(path)]), 2)
            self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
