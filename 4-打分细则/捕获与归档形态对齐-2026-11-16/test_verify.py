#!/usr/bin/env python3
"""Adversarial tests for the capture/archived alignment verifier.

Runs against the real packaged pins (read-only) plus synthetic evidence in a
TemporaryDirectory created inside this package directory; every test cleans up
after itself. No product, network, or private-archive access.
"""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import verify  # noqa: E402

REPO = HERE.parents[1]


def canonical(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True) + '\n').encode()


class Common(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(dir=HERE)
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


class LoadsTests(Common):
    def test_duplicate_key_rejected(self):
        with self.assertRaises(ValueError):
            verify.loads(b'{"a": 1, "a": 2}')

    def test_nonfinite_rejected(self):
        for raw in (b'{"a": NaN}', b'{"a": 1e999}', b'{"a": Infinity}'):
            with self.assertRaises(ValueError):
                verify.loads(raw)

    def test_bool_not_integer(self):
        with self.assertRaises(ValueError):
            verify.integer(True)

    def test_negative_integer_rejected(self):
        with self.assertRaises(ValueError):
            verify.integer(-1)


class SlotRowTests(Common):
    def entry(self, sequence=None, sizes=None, total=None):
        sequence = sequence or ['system/message', 'user/message', 'request/header']
        sizes = sizes or [10, 20, 5]
        entry = {'slot': 'dsh__x__r1', 'prior_metrics': {'i_sequence': sequence, 'i_bytes': total or 35},
                 'layers': {'L0': {'event_bytes': sizes}}}
        return entry

    def test_sum_and_harness_only(self):
        row = verify.slot_row(self.entry())
        self.assertEqual(row['system_bytes'], 10)
        self.assertEqual(row['user_bytes'], 20)
        self.assertEqual(row['harness_only_bytes'], 5)
        self.assertEqual(row['n_events'], 3)

    def test_length_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            verify.slot_row(self.entry(sizes=[1, 2]))

    def test_subset_exceeds_total_rejected(self):
        with self.assertRaises(ValueError):
            verify.slot_row(self.entry(total=10))

    def test_bad_slot_name_rejected(self):
        entry = self.entry()
        entry['slot'] = 'codex__x__r1'
        with self.assertRaises(ValueError):
            verify.slot_row(entry)


class CaptureTests(Common):
    def capture(self, roles=None, seq=1, kind='loop', total=None, workspace=None):
        roles = roles if roles is not None else [['system', 'str', 100], ['user', 'str', 200]]
        workspace = workspace if workspace is not None else {
            'TASK.md': {'bytes': 12}, 'inputs/exercises/dominoes/dominoes.py': {'bytes': 5}}
        return {'capture': {'requests': [{'seq': seq, 'kind': kind, 'roles': roles,
                                          'request_bytes': total or 300}]},
                'workspace': workspace,
                'prefix_identity': {'req3_appended_roles': [['assistant', 'none', 0],
                                                            ['tool', 'str', 30], ['tool', 'str', 20]]}}

    def test_capture_values(self):
        values = verify.capture_values(self.capture())
        self.assertEqual(values['system_bytes'], 100)
        self.assertEqual(values['user_bytes'], 200)
        self.assertEqual(values['tool_result_bytes'], [30, 20])

    def test_missing_seq1_rejected(self):
        with self.assertRaises(ValueError):
            verify.capture_values(self.capture(seq=2))

    def test_two_seq1_rejected(self):
        cap = self.capture()
        cap['capture']['requests'].append(dict(cap['capture']['requests'][0]))
        with self.assertRaises(ValueError):
            verify.capture_values(cap)

    def test_aux_kind_rejected(self):
        with self.assertRaises(ValueError):
            verify.capture_values(self.capture(kind='auxiliary'))

    def test_wrong_tool_count_rejected(self):
        cap = self.capture()
        cap['prefix_identity']['req3_appended_roles'] = [['tool', 'str', 1]]
        with self.assertRaises(ValueError):
            verify.capture_values(cap)

    def test_workspace_missing_rejected(self):
        with self.assertRaises(ValueError):
            verify.capture_values(self.capture(workspace={}))

    def test_workspace_wrong_name_rejected(self):
        with self.assertRaises(ValueError):
            verify.capture_values(self.capture(workspace={'TASK.md': {'bytes': 1}, 'other': {'bytes': 2}}))

    def test_subset_exceeds_request_rejected(self):
        with self.assertRaises(ValueError):
            verify.capture_values(self.capture(total=250))


class VerdictTests(Common):
    def test_in_range_and_percentile(self):
        v = verify.verdict(15, [10, 20, 14])
        self.assertEqual(v['verdict'], 'in_range')
        self.assertEqual(v['percentile_below'], 66.7)

    def test_out_of_range_high(self):
        self.assertEqual(verify.verdict(99, [1, 2])['verdict'], 'out_of_range')

    def test_out_of_range_low(self):
        self.assertEqual(verify.verdict(0, [1, 2])['verdict'], 'out_of_range')


class EndpointTests(Common):
    def rows(self, users=(100, 200, 300), systems=(50, 50, 50)):
        return [{'slot': 'dsh__exercism-py-6__r%d' % i, 'user_bytes': u, 'system_bytes': s,
                 'i_bytes_total': u + s + 10, 'harness_only_bytes': 10, 'n_events': 3}
                for i, (u, s) in enumerate(zip(users, systems), 1)]

    def cap(self, users=150, systems=50, tools=(30, 20)):
        return {'user_bytes': users, 'system_bytes': systems, 'request_bytes': users + systems,
                'tool_result_bytes': list(tools),
                'workspace_file_bytes': {'TASK.md': 12, 'inputs/exercises/dominoes/dominoes.py': 5}}

    def test_p4_same_task_missing_rejected(self):
        rows = self.rows()
        for row in rows:
            row['slot'] = 'dsh__other__r1'
        with self.assertRaises(ValueError):
            verify.endpoints(rows, self.cap())

    def test_p5_growth_factors(self):
        out = verify.endpoints(self.rows(), self.cap())
        self.assertEqual(out['p5_tool_result_growth']['growth_factors_pairing_unverified'],
                         [round(30 / 12, 3), round(20 / 5, 3)])

    def test_p3_median_even_count(self):
        rows = self.rows(users=(100, 200, 300), systems=(10, 10, 10))
        for i, user in enumerate((400, 500, 600), 1):
            rows.append({'slot': 'dsh__other__r%d' % i, 'user_bytes': user, 'system_bytes': 10,
                         'i_bytes_total': user + 20, 'harness_only_bytes': 10, 'n_events': 3})
        out = verify.endpoints(rows, self.cap())
        self.assertIn('ratio_vs_median', out['p3_aligned_sum_vs_archived'])


class ValidateTests(Common):
    def real_pair(self):
        evidence, result = build_pair()
        return evidence, result

    def test_tampered_evidence_rejected(self):
        evidence, result = self.real_pair()
        evidence['archived_slots'][0]['user_bytes'] += 1
        with self.assertRaises(ValueError):
            verify.validate_stored(REPO, evidence, result)

    def test_tampered_endpoint_rejected(self):
        evidence, result = self.real_pair()
        result = copy.deepcopy(result)
        result['endpoints']['p1_capture_user_vs_archived']['verdict'] = 'out_of_range'
        with self.assertRaises(ValueError):
            verify.validate_stored(REPO, evidence, result)

    def test_wrong_binding_rejected(self):
        evidence, result = self.real_pair()
        result = copy.deepcopy(result)
        result['evidence_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            verify.validate_stored(REPO, evidence, result)

    def test_missing_binding_rejected(self):
        evidence, result = self.real_pair()
        result = copy.deepcopy(result)
        result.pop('evidence_sha256')
        with self.assertRaises(ValueError):
            verify.validate_stored(REPO, evidence, result)

    def test_valid_pair_passes(self):
        evidence, result = self.real_pair()
        verify.validate_stored(REPO, evidence, result)


class PathTests(Common):
    def test_safe_join_rejects_escape(self):
        with self.assertRaises(ValueError):
            verify.safe_join(HERE, '../AGENTS.md')

    def test_exclusive_rejects_existing(self):
        target = self.tmp / 'out.json'
        target.write_bytes(b'x')
        with self.assertRaises(ValueError):
            verify.exclusive(target, b'y')

    def test_exclusive_rejects_outside_repo(self):
        outside = REPO.parent / 'should-not-be-written.json'
        with self.assertRaises(ValueError):
            verify.exclusive(outside, b'y')
        self.assertFalse(outside.exists())

    def test_exclusive_writes_inside_repo(self):
        target = self.tmp / 'out.json'
        verify.exclusive(target, b'payload')
        self.assertEqual(target.read_bytes(), b'payload')


class PinTests(Common):
    def test_identity_pin_stable(self):
        raw = (REPO / verify.ID_RELPATH).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), verify.ID_SHA)

    def test_capture_pins_stable(self):
        raw = (REPO / verify.CAP_RELPATH).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), verify.CAP_SHA)
        raw = (REPO / verify.CAPRES_RELPATH).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), verify.CAPRES_SHA)


class RealDataTests(Common):
    def test_frozen_values_on_real_pins(self):
        evidence, result = build_pair()
        self.assertEqual(len(evidence['archived_slots']), 15)
        cap = evidence['capture_first_loop_request']
        self.assertEqual(cap['system_bytes'], 2593)
        self.assertEqual(cap['user_bytes'], 9529)
        self.assertEqual(cap['request_bytes'], 33091)
        first = evidence['archived_slots'][0]
        self.assertEqual(first['slot'], 'dsh__bird-ca-schools-15__r1')
        self.assertEqual(first['system_bytes'], 2540)
        self.assertEqual(first['user_bytes'], 9653)
        self.assertEqual(result['endpoints']['p1_capture_user_vs_archived']['verdict'], 'in_range')
        self.assertEqual(result['endpoints']['p2_capture_system_vs_archived']['verdict'], 'out_of_range')
        self.assertEqual(result['endpoints']['p4_same_task_user_gap']['ratio_capture_vs_same_task_median'],
                         round(9529 / 7503, 4))
        self.assertEqual(result['endpoints']['p5_tool_result_growth']['growth_factors_pairing_unverified'],
                         [2.671, 5.971])
        self.assertEqual(result['endpoints']['p5_tool_result_growth']['workspace_file_bytes'],
                         {'TASK.md': 85, 'inputs/exercises/dominoes/dominoes.py': 34})

    def test_no_content_values_in_evidence(self):
        evidence, _ = build_pair()
        blob = canonical(evidence)
        self.assertNotIn(b'"content"', blob)
        self.assertNotIn(b'can_chain', blob)


class CliTests(Common):
    def test_build_mode_writes_pair_then_refuses_overwrite(self):
        out = self.tmp
        rc = verify.main(['--root', str(REPO), '--build-evidence', str(out / 'e.json'),
                          '--output', str(out / 'r.json')])
        self.assertEqual(rc, 0)
        evidence = json.loads((out / 'e.json').read_bytes())
        result = json.loads((out / 'r.json').read_bytes())
        self.assertEqual(result['evidence_sha256'],
                         hashlib.sha256((out / 'e.json').read_bytes()).hexdigest())
        self.assertIn(result['endpoints']['p1_capture_user_vs_archived']['verdict'],
                      ('in_range', 'out_of_range'))
        rc = verify.main(['--root', str(REPO), '--build-evidence', str(out / 'e.json'),
                          '--output', str(out / 'r2.json')])
        self.assertEqual(rc, 2)
        self.assertFalse((out / 'r2.json').exists())

    def test_validation_mode_reproduces_stored_result(self):
        stored = (HERE / 'result.json').read_bytes()
        out = self.tmp / 'replay.json'
        rc = verify.main(['--root', str(REPO), '--output', str(out)])
        self.assertEqual(rc, 0)
        self.assertEqual(out.read_bytes(), stored)


def build_pair():
    evidence, result = verify.build(REPO)
    result['evidence_sha256'] = hashlib.sha256((HERE / 'evidence.json').read_bytes()).hexdigest()
    return evidence, result


if __name__ == '__main__':
    unittest.main()
