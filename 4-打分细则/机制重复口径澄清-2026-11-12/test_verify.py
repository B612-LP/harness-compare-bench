#!/usr/bin/env python3
"""Stdlib regression/negative tests. No products, network or historical tools."""
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
spec = importlib.util.spec_from_file_location('clarify_verify', HERE / 'verify.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def controls():
    return [{'type': 'response_item', 'payload': {'type': 'message', 'role': role, 'content': [{'text': text}]}}
            for role, text in [('developer', 'permissions'), ('user', '<environment_context>environment</environment_context>'), ('user', 'TASK: solve this')]]


class VerifyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = v.analyze(ROOT)
        cls.evidence = json.loads((HERE / 'evidence.json').read_bytes())

    def temporary(self):
        return tempfile.TemporaryDirectory(dir=os.environ.get('B_TEST_TMPDIR'))

    def test_01_boundary_100_inclusive(self):
        self.assertEqual(v.historical_gate([0, 100, 50], True)['historical_AND_status'], 'pass')

    def test_02_boundary_101_fails(self):
        self.assertEqual(v.historical_gate([0, 101, 50], True)['historical_AND_status'], 'fail')

    def test_03_AND_sequence_false(self):
        self.assertEqual(v.historical_gate([50, 50, 50], False)['historical_AND_status'], 'fail')

    def test_04_AND_unknown_not_pass(self):
        self.assertEqual(v.historical_gate([50, 50, 50], None)['historical_AND_status'], 'unverifiable')

    def test_05_failed_bytes_suffice_even_unknown_sequence(self):
        self.assertEqual(v.historical_gate([0, 101, 50], None)['historical_AND_status'], 'fail')

    def test_06_session_only_degenerate(self):
        sequence = v.legacy_sequence(['session', 'turn/start', 'tool/call', 'turn/end'])
        self.assertEqual(sequence, ['session'])
        self.assertFalse(v.sufficient_legacy_sequence(sequence))

    def test_07_turn_only_equal_not_full_sequence(self):
        one = ['turn/start', 'step/start', 'tool/call', 'step/end', 'turn/end']
        two = ['turn/start', 'step/start', 'tool/call', 'tool/call', 'step/end', 'turn/end']
        self.assertEqual([x for x in one if x in v.BOUNDARY_TYPES], [x for x in two if x in v.BOUNDARY_TYPES])
        self.assertNotEqual([x for x in one if x in v.STEP_TYPES], [x for x in two if x in v.STEP_TYPES])

    def test_08_first_user_is_environment_not_task(self):
        events = controls()
        out = v.select_controls(events)
        self.assertEqual(out['task_content_sha256'], v.sha(v.canon(events[2]['payload']['content'])))
        self.assertNotEqual(out['task_content_sha256'], v.sha(v.canon(events[1]['payload']['content'])))

    def test_09_swapped_environment_and_task_rejected(self):
        events = controls()
        events[1], events[2] = events[2], events[1]
        with self.assertRaises(v.Invalid):
            v.select_controls(events)

    def test_10_payload_and_wrapper_are_distinct(self):
        events = [{'type': 'session_meta', 'payload': {}}] + controls() + [{'type': 'token_usage_record', 'payload': {'usage': {'input_tokens': 999999999}}}]
        measured = v.measure(v.project_events(events, 'codex'), 'codex')
        payload_bytes = sum(len(v.canon(e['payload'])) for e in events if e['type'] == 'response_item')
        self.assertEqual(measured['input_bytes'], payload_bytes)
        self.assertGreater(measured['event_wrapper_canonical_bytes'], payload_bytes)
        self.assertNotEqual(measured['input_bytes'], 999999999)

    def test_11_missing_slot_rejected(self):
        with self.assertRaises(v.Invalid):
            v.validate_slots(self.evidence['slots'][:-1])

    def test_12_duplicate_slot_rejected(self):
        with self.assertRaises(v.Invalid):
            v.validate_slots(self.evidence['slots'] + self.evidence['slots'][:1])

    def test_13_mixed_slot_rejected(self):
        rows = copy.deepcopy(self.evidence['slots'])
        rows[0]['slot'] = 'dsh__new-case__r1'
        with self.assertRaises(v.Invalid):
            v.validate_slots(rows)

    def test_14_tampered_source_rejected(self):
        with self.temporary() as directory:
            root = Path(directory)
            (root / 'source.json').write_text('{"x":2}')
            record = {'path': 'source.json', 'sha256': v.sha(b'{"x":1}')}
            with self.assertRaises(v.Invalid):
                v.bound_json(root, record)

    def test_15_missing_source_rejected(self):
        with self.temporary() as directory:
            with self.assertRaises(v.Invalid):
                v.bound_json(Path(directory), {'path': 'missing.json', 'sha256': '0' * 64})

    def test_16_bad_json_schema_rejected(self):
        with self.assertRaises(v.Invalid):
            v.project_events([{'payload': {}}], 'codex')
        with self.assertRaises(v.Invalid):
            v.project_events([{'type': 'response_item'}], 'codex')
        with self.assertRaises(v.Invalid):
            v.measure([['session', 0, None, 0]], 'dsh')

    def test_17_reference_summary_not_metric_substitute(self):
        with self.assertRaises(v.Invalid):
            v.check_metric_claim(60064, 62854, 'R3')
        self.assertEqual(self.result['canonical_codex_R3_range'], [60064, 789813])

    def test_18_trace_SHA_mismatch_rejected(self):
        slot = 'dsh__bird-ca-schools-15__r2'
        row = next(r for r in self.evidence['slots'] if r['slot'] == slot)
        meta = json.loads((ROOT / v.BATCH / 'runs' / slot / 'meta.public-derived.json').read_bytes())
        accounts = json.loads((ROOT / v.BATCH / 'observe/trace-accounting-summary.json').read_bytes())['dsh']['incidents']
        account = next(r for r in accounts if r['slot'] == slot)
        receipts = json.loads((ROOT / v.BATCH / 'adjudications.json').read_bytes())
        receipt = next(r['identity'] for r in receipts if r['identity']['run_id'] == 'r1109-dsh-bird-ca-schools-15-r2')
        wrong = copy.deepcopy(row['identity']); wrong['sha256'] = '0' * 64
        with self.assertRaises(v.Invalid):
            v.check_identity(slot, meta, wrong, account, receipt)

    def test_19_identity_reconciliation(self):
        slot = 'dsh__bird-ca-schools-15__r1'
        row = self.evidence['slots'][0]
        meta = json.loads((ROOT / v.BATCH / 'runs' / slot / 'meta.public-derived.json').read_bytes())
        account = json.loads((ROOT / v.BATCH / 'observe/trace-accounting-summary.json').read_bytes())['dsh']['incidents'][0]
        receipt = json.loads((ROOT / v.BATCH / 'adjudications.json').read_bytes())[0]['identity']
        v.check_identity(slot, meta, row['identity'], account, receipt)
        wrong = copy.deepcopy(meta); wrong['rep'] = '2'
        with self.assertRaises(v.Invalid):
            v.check_identity(slot, wrong, row['identity'], account, receipt)
        wrong_receipt = copy.deepcopy(receipt); wrong_receipt['run_id'] = 'r1030-dsh-bird-ca-schools-15-r1'
        with self.assertRaises(v.Invalid):
            v.check_identity(slot, meta, row['identity'], account, wrong_receipt)
        wrong_source = copy.deepcopy(row['identity'])
        wrong_source['source_relative_to_archive'] = wrong_source['source_relative_to_archive'].replace('__r1/', '__r2/')
        with self.assertRaises(v.Invalid):
            v.check_identity(slot, meta, wrong_source, account, receipt)

    def test_20_contract_threshold_or_groups_change_rejected(self):
        for key, value in [('groups', 9), ('byte_threshold', 101), ('operator', 'OR')]:
            evidence = copy.deepcopy(self.evidence); evidence['contract'][key] = value
            data = v.canon(evidence)
            with self.temporary() as directory:
                root = Path(directory); folder = root / v.HERE; folder.mkdir(parents=True)
                (folder / 'evidence.json').write_bytes(data)
                with patch.object(v, 'EVIDENCE_SHA256', v.sha(data)):
                    with self.assertRaises(v.Invalid):
                        v.analyze(root)

    def test_21_real_slots_groups_and_old_AND_status(self):
        self.assertEqual(len(self.result['slots']), 30)
        self.assertEqual(len(self.result['groups']), 10)
        self.assertEqual(self.result['byte_subgate_pass_counts'], {'dsh': 4, 'codex': 0})
        self.assertEqual(self.result['historical_AND_status_counts'], {'fail': 6, 'unverifiable': 4})
        self.assertFalse(self.result['historical_upgrade_10_of_10'])
        self.assertFalse(self.result['M1_inline_spill_effect_identified'])

    def test_22_real_dsh_sequence_diagnostics(self):
        groups = [g for g in self.result['groups'] if g['arm'] == 'dsh']
        self.assertTrue(all(g['legacy_all_session_only'] and g['narrow_boundary_equal_diagnostic'] for g in groups))
        self.assertFalse(any(g['step_tool_assistant_equal_diagnostic'] for g in groups))

    def test_23_real_bird_S4_correction(self):
        bird = self.result['groups'][0]
        self.assertEqual(bird['output_bytes'], [551905, 193745, 517142])
        self.assertAlmostEqual(bird['S4_max_min_ratio'], 2.848615448140597)

    def test_24_stored_result_and_deterministic_replay(self):
        self.assertEqual(self.result, json.loads((HERE / 'result.json').read_bytes()))
        self.assertEqual(v.canon(self.result), v.canon(v.analyze(ROOT)))

    def test_25_cli_stdout_and_write_once(self):
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

    def test_26_projection_tamper_rejected(self):
        with self.temporary() as directory:
            root = Path(directory); folder = root / v.HERE; folder.mkdir(parents=True)
            (folder / 'evidence.json').write_bytes((HERE / 'evidence.json').read_bytes() + b' ')
            with self.assertRaises(v.Invalid):
                v.analyze(root)

    def test_27_archive_controls_are_secondary_only(self):
        groups = [g for g in self.result['groups'] if g['arm'] == 'codex']
        self.assertTrue(all(g['leading_role_content_equal_secondary'] and g['task_content_equal_secondary'] for g in groups))
        self.assertTrue(all(g['historical_AND_status'] == 'fail' for g in groups))

    def test_28_tail_and_boundary_accounting(self):
        events = [{'type': 'session_meta', 'payload': {}}] + controls()
        tail = v.measure(v.project_events(events, 'codex'), 'codex')
        closed = v.measure(v.project_events(events + [{'type': 'token_usage_record', 'payload': {}}], 'codex'), 'codex')
        self.assertEqual(tail['input_bytes'], closed['input_bytes'])
        self.assertEqual(tail['closed_turns'], 0)
        self.assertEqual(closed['closed_turns'], 1)


if __name__ == '__main__':
    unittest.main()
