#!/usr/bin/env python3
"""Pure software checks; not independent science audit or new product samples.
Python stdlib only. Temporary files are confined to the explicit --scratch root.
"""
import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('first_state_verify', HERE / 'verify.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
SCRATCH = None


def synthetic():
    events = [{'type': 'session', 'version': 4, 'id': 'synthetic'}]
    events += [{'type': 'step/start', 'seq': i, 'data': {}} for i in range(27)]
    for n, seq in enumerate((19, 25)):
        args = {'command': 'synthetic-read-only-' + str(n)}
        cid = 'synthetic-' + str(n)
        events[seq] = {'type': 'assistant/message', 'seq': seq - 1,
                       'data': {'message': {'content': [{'type': 'tool-call', 'id': cid,
                                'name': 'bash', 'arguments': args}]}}}
        events[seq + 1] = {'type': 'tool/call', 'seq': seq,
                          'data': {'callId': cid, 'name': 'bash', 'arguments': args}}
        text = 'listing' if n == 0 else '===== dominoes skeleton =====\nabc\n===== bowling README =====\nend'
        events[seq + 2] = {'type': 'tool/result', 'seq': seq + 1,
                          'data': {'message': {'toolCallId': cid, 'source': {'callId': cid},
                                   'isError': False, 'content': [{'type': 'text', 'text': text}]}},
                          'sourceEventSeqs': [seq]}
    return events


class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(os.environ.get('STATE_TEST_ROOT', str(HERE.parents[1]))).resolve()
        cls.source, cls.legacy, cls.nominal = v.public_sources(cls.root)
        cls.evidence = v.load((HERE / 'evidence.json').read_bytes())

    def reject(self, fn, *args):
        with self.assertRaises((v.Invalid, OSError)):
            fn(*args)

    def mutated(self, change):
        evidence = copy.deepcopy(self.evidence)
        change(evidence)
        self.reject(v.validate, evidence, self.source, self.legacy, self.nominal)

    def test_01_public_complete(self):
        result = v.validate(self.evidence, self.source, self.legacy, self.nominal)
        self.assertEqual(result['observed_same_pairs'], 0)
        self.assertEqual(result['first_observed']['bytes'], 2010)
        self.assertEqual(result['second_observed']['bytes'], 2000)
        self.assertEqual(result['conclusion'], 'different_and_edit_compatible')

    def test_02_duplicate_json(self):
        self.reject(v.load, '{"a":1,"a":2}')

    def test_03_nonfinite_json(self):
        for raw in ('NaN', 'Infinity', '-Infinity', '1e999', '-1e999'):
            with self.subTest(raw=raw):
                self.reject(v.load, raw)

    def test_04_boolean_not_integer(self):
        self.reject(v.integer, True)
        self.mutated(lambda e: e['replacement'].__setitem__('occurrences_in_r2', True))
        self.mutated(lambda e: e['slots'][0].__setitem__('event_count', True))

    def test_05_slot_missing_or_order(self):
        self.mutated(lambda e: e['slots'].pop())
        self.mutated(lambda e: e['slots'].reverse())

    def test_06_projection_binding(self):
        self.mutated(lambda e: e['slots'][0].__setitem__('event_projection_sha256', '0' * 64))

    def test_07_call_order_and_hash(self):
        self.mutated(lambda e: e['slots'][0]['first_calls'].reverse())
        self.mutated(lambda e: e['slots'][0]['first_calls'][1].__setitem__('arguments_sha256', '0' * 64))

    def test_08_failed_edit_promoted(self):
        self.mutated(lambda e: e['r2_edit_attempts'][0].__setitem__('is_error', False))
        self.mutated(lambda e: e['r2_edit_attempts'][2].__setitem__('is_error', True))

    def test_09_boundary_arithmetic(self):
        self.mutated(lambda e: e['slots'][0]['boundary'].__setitem__('end', 1))
        self.mutated(lambda e: e['slots'][0]['boundary'].__setitem__('start', True))

    def test_10_prediction_relation(self):
        self.mutated(lambda e: e['replacement']['predicted'].__setitem__('sha256', '0' * 64))
        self.mutated(lambda e: e['replacement']['new'].__setitem__('bytes', 88))

    def test_11_multiple_replacement(self):
        self.reject(v.exact_replace, b'old old', b'old', b'new')
        self.reject(v.exact_replace, b'absent', b'old', b'new')
        self.assertEqual(v.exact_replace(b'one old\r\n', b'old', b'new'), b'one new\r\n')

    def test_12_boundary_exact_bytes(self):
        raw = b'head\nSTART\na\r\nb\n===== bowling README =====\ntail'
        state, bounds = v.slice_state(raw, 'START\n', '===== bowling README =====\n')
        self.assertEqual(state, b'a\r\nb\n')
        self.assertEqual(bounds['end'] - bounds['start'], len(state))

    def test_13_boundary_duplicate_truncated(self):
        for raw in (b'START\nx\nSTART\ny\nEND\n', b'START\nx\nEND\ny\nEND\n',
                    b'START\nx\nEN', b'END\nx\nSTART\n'):
            self.reject(v.slice_state, raw, 'START\n', 'END\n')

    def test_14_next_boundary(self):
        self.reject(v.slice_state, b'START\nx\n===== other README =====\ny\nEND\n', 'START\n', 'END\n')

    def test_15_real_id_link(self):
        events = synthetic()
        calls, results = v.link_events(events)
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(results), 2)
        events[27]['data']['message']['toolCallId'] = 'wrong'
        self.reject(v.link_events, events)

    def test_16_duplicate_result_missing_call(self):
        events = synthetic()
        events[27]['data']['message']['toolCallId'] = 'synthetic-0'
        self.reject(v.link_events, events)
        events = synthetic(); events[27]['type'] = 'step/end'
        self.reject(v.link_events, events)

    def test_17_result_provenance(self):
        events = synthetic(); events[27]['sourceEventSeqs'] = [19]
        self.reject(v.link_events, events)
        events = synthetic(); events[27]['data']['message']['source']['callId'] = 'wrong'
        self.reject(v.link_events, events)

    def test_18_sequence_missing_reordered(self):
        events = synthetic(); events.pop(5)
        self.reject(v.link_events, events)
        events = synthetic(); events[5], events[6] = events[6], events[5]
        self.reject(v.link_events, events)

    def test_19_assistant_prefix(self):
        events = synthetic(); calls, results = v.link_events(events)
        self.assertEqual(len(v.prefix_check(events, calls, 26)), 2)
        events[25]['data']['message']['content'][0]['id'] = 'wrong'
        self.reject(v.prefix_check, events, calls, 26)

    def test_20_text_block_order_status(self):
        msg = {'isError': False, 'content': [{'type': 'text', 'text': 'a\n'},
                                          {'type': 'other'}, {'type': 'text', 'text': 'b\r\n'}]}
        self.assertEqual(v.message_text(msg), b'a\nb\r\n')
        del msg['isError']; self.reject(v.message_text, msg)

    def test_21_relative_escape_symlink(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            root = Path(tmp) / 'root'; root.mkdir()
            for value in ('../outside', '/absolute', 'a/../../b', 'a\\b', './a'):
                self.reject(v.safe, root, value)
            (root / 'link').symlink_to(Path(tmp))
            self.reject(v.safe, root, 'link/outside')

    def test_22_exclusive_output(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            path = Path(tmp) / 'receipt.json'
            v.exclusive(path, {'ok': True})
            before = path.read_bytes()
            self.reject(v.exclusive, path, {'ok': False})
            self.assertEqual(path.read_bytes(), before)
            self.reject(v.exclusive, Path(tmp) / 'new.json', {}, (Path(tmp),))

    def test_23_unknown_private_fields_rejected(self):
        self.mutated(lambda e: e.__setitem__('cwd', 'not-a-real-path'))
        self.mutated(lambda e: e['slots'][0].__setitem__('id', 'not-a-real-id'))
        self.mutated(lambda e: e['slots'][0]['observed'].__setitem__('text', 'not-real-content'))

    def test_24_sealed_equal_length_change(self):
        raw = (HERE / 'evidence.json').read_bytes()
        changed = raw.replace(b'b0bcc111', b'a0bcc111', 1)
        self.assertEqual(len(raw), len(changed))
        self.assertNotEqual(v.sha(changed), v.EVIDENCE_SHA)
        self.assertEqual(v.sha(raw), v.EVIDENCE_SHA)

    def test_25_comparison_branches(self):
        changed = copy.deepcopy(self.evidence)
        changed['replacement']['predicted']['sha256'] = '0' * 64
        changed['replacement']['predicted_equals_r3'] = False
        result = v.validate(changed, self.source, self.legacy, self.nominal)
        self.assertEqual(result['conclusion'], 'different_observed_states')

    def test_26_source_pins(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            root = Path(tmp); (root / 'a').write_bytes(b'abc')
            self.assertEqual(v.bound(root, 'a', v.sha(b'abc')), b'abc')
            self.reject(v.bound, root, 'a', v.sha(b'abd'))
            self.reject(v.bound, root, 'missing', v.sha(b'abc'))

    def test_27_build_evidence_cannot_write_either_source_root(self):
        # Only private synthetic directories; mock source loading, not the CLI
        # output wiring or exclusive writer. The original root omission returns
        # success and creates both files, so this specifically catches R1.
        for target_name in ('repo', 'archive'):
            with self.subTest(target=target_name), tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
                base = Path(tmp)
                source_root = base / 'repo'; source_root.mkdir()
                archive_root = base / 'archive'; archive_root.mkdir()
                evidence_path = base / target_name / 'must-not-create.json'
                output_path = base / 'result.json'
                with mock.patch.object(v, 'public_sources', return_value=(self.source, self.legacy, self.nominal)), \
                     mock.patch.object(v, 'build', return_value=copy.deepcopy(self.evidence)):
                    status = v.main(['--root', str(source_root), '--archive-root', str(archive_root),
                                     '--build-evidence', str(evidence_path), '--output', str(output_path)])
                self.assertNotEqual(status, 0)
                self.assertFalse(evidence_path.exists())
                self.assertFalse(output_path.exists())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scratch', type=Path, required=True, help='existing private temporary-output parent')
    args, remaining = parser.parse_known_args()
    SCRATCH = args.scratch.resolve()
    if not SCRATCH.is_dir():
        parser.error('scratch directory must exist')
    unittest.main(argv=[sys.argv[0]] + remaining)
