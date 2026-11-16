#!/usr/bin/env python3
"""Offline adversarial tests: only this package's verifier is executed.
Synthetic commands/IDs are inert strings, never submitted to a product or shell.
"""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('render_verify', HERE / 'verify.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
HEAD = 'Chunk ID: fixture\nWall time: 0.1 seconds\nProcess exited with code 0\nOriginal token count: 1\nOutput:\n'


def trace_events(body='a', aggregate='a'):
    return [
        {'type': 'response_item', 'payload': {'type': 'function_call', 'name': 'fixture', 'arguments': '{}', 'call_id': 'fixture-id'}},
        {'type': 'event_msg', 'payload': {'type': 'item_completed', 'item': {'type': 'CommandExecution', 'id': 'fixture-id', 'aggregated_output': aggregate}}},
        {'type': 'response_item', 'payload': {'type': 'function_call_output', 'call_id': 'fixture-id', 'output': HEAD + body}},
    ]


def raw_events(events):
    return b''.join(v.canon(e) + b'\n' for e in events)


def project(events):
    raw = raw_events(events)
    return v.project_slot(raw, 'fixture', 'fixture.jsonl', v.sha(raw))


class ClassifierTests(unittest.TestCase):
    def test_exact_before_marker_rules(self):
        text = '…9 tokens truncated…'
        self.assertEqual(v.classify(text, text)['kind'], 'EXACT')

    def test_equal_length_not_equal_value(self):
        result = v.classify('ab', 'cd')
        self.assertEqual(result['kind'], 'UNEXPLAINED')
        self.assertEqual(result['reason'], 'NO-MARKER')

    def test_unmarked_boundary_removal_not_crop(self):
        self.assertEqual(v.classify('abef', 'abcdef')['kind'], 'UNEXPLAINED')

    def test_unicode_marker_witness(self):
        result = v.classify('a…3 tokens truncated…f', 'abcdef')
        self.assertEqual(result['kind'], 'MARKED-BOUNDARY-CROP-WITNESS')
        self.assertEqual(result['witness']['deleted'], v.describe('bcde'))

    def test_ascii_marker_witness(self):
        result = v.classify('a...3 tokens truncated...f', 'abcdef')
        self.assertEqual(result['kind'], 'MARKED-BOUNDARY-CROP-WITNESS')
        self.assertEqual(result['witness']['format'], 'ascii-dots')

    def test_no_spaces_added_to_frozen_marker(self):
        self.assertEqual(v.classify('a… 3 tokens truncated …f', 'abcdef')['reason'], 'NO-MARKER')

    def test_mixed_marker_delimiters_not_accepted(self):
        self.assertEqual(v.classify('a…3 tokens truncated...f', 'abcdef')['reason'], 'NO-MARKER')

    def test_fake_marker_boundary_mismatch(self):
        self.assertEqual(v.classify('x…3 tokens truncated…f', 'abcdef')['reason'], 'BOUNDARY-MISMATCH')

    def test_multiple_markers_not_witness(self):
        self.assertEqual(v.classify('a…3 tokens truncated……4 tokens truncated…f', 'abcdef')['reason'], 'MULTIPLE-MARKERS')

    def test_no_deletion_rejected(self):
        self.assertEqual(v.classify('a…0 tokens truncated…b', 'ab')['reason'], 'NO-DELETION')

    def test_overlap_rejected(self):
        self.assertEqual(v.classify('ab…3 tokens truncated…bc', 'abc')['reason'], 'OVERLAP-OR-EMPTY-RETAIN')

    def test_no_retained_character_rejected(self):
        self.assertEqual(v.classify('…3 tokens truncated…', 'abc')['reason'], 'OVERLAP-OR-EMPTY-RETAIN')

    def test_prefix_only_witness(self):
        self.assertEqual(v.classify('a…2 tokens truncated…', 'abc')['witness']['suffix'], v.describe(''))

    def test_suffix_only_witness(self):
        self.assertEqual(v.classify('…2 tokens truncated…c', 'abc')['witness']['prefix'], v.describe(''))

    def test_utf8_character_boundary(self):
        result = v.classify('甲…2 tokens truncated…🙂', '甲乙丙🙂')
        self.assertEqual(result['kind'], 'MARKED-BOUNDARY-CROP-WITNESS')
        self.assertEqual(result['witness']['deleted']['characters'], 2)
        self.assertEqual(result['witness']['deleted']['bytes'], 6)
        self.assertEqual(result['witness']['suffix']['characters'], 1)
        self.assertEqual(result['witness']['suffix']['bytes'], 4)

    def test_unicode_not_normalized(self):
        self.assertEqual(v.classify('é', 'e\u0301')['kind'], 'UNEXPLAINED')

    def test_exact_optional_line_wrapper(self):
        result = v.classify('Total output lines: 6\n\na…3 tokens truncated…f', 'abcdef')
        self.assertEqual(result['kind'], 'MARKED-BOUNDARY-CROP-WITNESS')
        self.assertEqual(result['witness']['added_wrapper'], v.describe('Total output lines: 6\n\n'))

    def test_second_line_wrapper_not_removed(self):
        result = v.classify('Total output lines: 6\n\nTotal output lines: 6\n\na…3 tokens truncated…f', 'abcdef')
        self.assertEqual(result['kind'], 'UNEXPLAINED')

    def test_line_wrapper_alone_not_explanation(self):
        self.assertEqual(v.classify('Total output lines: 1\n\na', 'a')['kind'], 'UNEXPLAINED')

    def test_diagnostic_not_crop(self):
        result = v.classify('abef', 'abcdef')
        self.assertIsNotNone(result['diagnostic'])
        self.assertIsNone(result['witness'])
        self.assertEqual(result['kind'], 'UNEXPLAINED')

    def test_positive_and_negative_T(self):
        _, positive = project(trace_events('a…1 tokens truncated…c', 'abc'))
        _, negative = project(trace_events('ac', 'a' + 'b' * 100 + 'c'))
        self.assertGreater(positive[0]['components']['T'], 0)
        self.assertLess(negative[0]['components']['T'], 0)
        for row in (positive[0], negative[0]):
            self.assertEqual(row['planes']['P']['bytes'], sum(row['components'].values()))


class HeaderTests(unittest.TestCase):
    def test_header_preserves_newline_and_unicode(self):
        self.assertEqual(v.split_header(HEAD + '甲\r\n'), (HEAD, '甲\r\n'))

    def test_running_header_optional_token_count(self):
        head = 'Chunk ID: fixture\nWall time: 0 seconds\nProcess running with session ID fixture\nOutput:\n'
        self.assertEqual(v.split_header(head + 'a'), (head, 'a'))

    def test_signed_exit_code(self):
        self.assertEqual(v.split_header(HEAD.replace('code 0', 'code +1') + 'a')[1], 'a')

    def test_unknown_header_no_fabricated_body(self):
        self.assertEqual(v.split_header('Output:\na'), (None, None))
        self.assertEqual(v.classify(None, 'a')['reason'], 'HEADER-UNRECOGNIZED')

    def test_malformed_decimal_not_accepted(self):
        self.assertEqual(v.split_header(HEAD.replace('0.1 seconds', '0..1 seconds') + 'a'), (None, None))

    def test_prefix_not_trimmed(self):
        self.assertEqual(v.split_header('\n' + HEAD + 'a'), (None, None))

    def test_nonstring_output_rejected(self):
        with self.assertRaises(v.Invalid):
            v.split_header(None)


class ParserAndLinkTests(unittest.TestCase):
    def test_duplicate_json_keys_nested(self):
        for text in ('{"a":1,"a":2}', '{"a":{"b":1,"b":2}}'):
            with self.subTest(text=text), self.assertRaises(v.Invalid):
                v.loads(text)

    def test_nonfinite_and_overflow_rejected(self):
        for text in ('NaN', 'Infinity', '-Infinity', '1e9999'):
            with self.subTest(text=text), self.assertRaises(v.Invalid):
                v.loads(text)

    def test_boolean_not_integer(self):
        with self.assertRaises(v.Invalid):
            v.integer(True, 0)

    def test_invalid_utf8_rejected(self):
        with self.assertRaises(v.Invalid):
            v.parse_trace(b'\xff')

    def test_blank_line_rejected(self):
        with self.assertRaises(v.Invalid):
            v.parse_trace(b'{}\n\n')

    def test_unicode_line_separator_is_not_record_separator(self):
        raw = v.canon({'type': 'fixture', 'value': 'a\u2028b'}) + b'\n'
        self.assertEqual(len(v.parse_trace(raw)), 1)

    def test_wrong_source_pin(self):
        with self.assertRaises(v.Invalid):
            v.project_slot(raw_events(trace_events()), 'fixture', 'fixture.jsonl', '0' * 64)

    def test_valid_three_way_join(self):
        source, records = project(trace_events())
        self.assertEqual(source['output_count'], 1)
        self.assertEqual(records[0]['lines'], {'call': 1, 'execution': 2, 'output': 3})

    def test_missing_any_join_partner(self):
        for removed in range(3):
            with self.subTest(removed=removed), self.assertRaises(v.Invalid):
                project([e for i, e in enumerate(trace_events()) if i != removed])

    def test_duplicate_any_join_partner(self):
        for index in range(3):
            events = trace_events()
            events.insert(index, copy.deepcopy(events[index]))
            with self.subTest(index=index), self.assertRaises(v.Invalid):
                project(events)

    def test_missing_call_id(self):
        events = trace_events()
        del events[0]['payload']['call_id']
        with self.assertRaises(v.Invalid):
            project(events)

    def test_nonstring_aggregate(self):
        events = trace_events()
        events[1]['payload']['item']['aggregated_output'] = None
        with self.assertRaises(v.Invalid):
            project(events)

    def test_execution_before_call(self):
        events = trace_events()
        events[0], events[1] = events[1], events[0]
        with self.assertRaises(v.Invalid):
            project(events)

    def test_bad_response_schema(self):
        with self.assertRaises(v.Invalid):
            project([{'type': 'response_item', 'payload': {}}])

    def test_bad_json_in_call_arguments(self):
        events = trace_events()
        events[0]['payload']['arguments'] = '{"x":1,"x":2}'
        with self.assertRaises(v.Invalid):
            project(events)

    def test_archive_path_escape(self):
        with self.assertRaises(v.Invalid):
            v.archive_path(HERE, '../escape')


class PublicReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.references = v.references()
        cls.evidence = v.loads((HERE / 'evidence.json').read_bytes())

    def changed(self, change):
        evidence = copy.deepcopy(self.evidence)
        change(evidence)
        with self.assertRaises(v.Invalid):
            v.validate_evidence(evidence, self.references)

    def test_current_evidence_valid(self):
        self.assertEqual(v.sha((HERE / 'evidence.json').read_bytes()), v.EVIDENCE_SHA256)
        v.validate_evidence(self.evidence, self.references)

    def test_published_result_exact_replay(self):
        result = v.result_for(self.evidence, v.EVIDENCE_SHA256)
        self.assertEqual(v.document(result), (HERE / 'result.json').read_bytes())

    def test_known_baseline_not_dynamic_HEAD(self):
        self.assertEqual(v.BASELINE, '50c073c084006c0bfd5f8b79db3bc495e842847b')
        self.assertNotIn('resolve_head', (HERE / 'verify.py').read_text())

    def test_missing_record(self):
        self.changed(lambda e: e['records'].pop())

    def test_duplicate_record(self):
        self.changed(lambda e: e['records'].append(copy.deepcopy(e['records'][0])))

    def test_duplicate_source(self):
        self.changed(lambda e: e['sources'].append(copy.deepcopy(e['sources'][0])))

    def test_wrong_public_pin(self):
        self.changed(lambda e: e['sources'][0].__setitem__('sha256', '0' * 64))

    def test_wrong_old_R3_bytes(self):
        self.changed(lambda e: e['sources'][0].__setitem__('r3_total_bytes', 1))

    def test_extra_raw_field_rejected(self):
        self.changed(lambda e: e['records'][0].__setitem__('command', 'fixture'))

    def test_wrong_component(self):
        self.changed(lambda e: e['records'][0]['components'].__setitem__('J', 0))

    def test_wrong_body_header_sum(self):
        self.changed(lambda e: e['records'][0]['header'].__setitem__('bytes', 1))

    def test_equal_lengths_not_enough_for_exact(self):
        self.changed(lambda e: e['records'][0]['planes']['B'].__setitem__('sha256', '0' * 64))

    def test_wrong_record_line(self):
        self.changed(lambda e: e['records'][0]['lines'].__setitem__('call', True))

    def test_relabel_unexplained_as_crop_without_witness(self):
        def change(e):
            row = next(r for r in e['records'] if r['conversion']['kind'] == 'UNEXPLAINED')
            row['conversion']['kind'] = 'MARKED-BOUNDARY-CROP-WITNESS'
        self.changed(change)

    def test_bad_diagnostic_sum(self):
        def change(e):
            row = next(r for r in e['records'] if r['conversion']['kind'] == 'UNEXPLAINED')
            row['conversion']['diagnostic']['prefix']['bytes'] += 1
        self.changed(change)

    def test_public_CLI_normal_and_optimized_same(self):
        args = [str(HERE / 'verify.py')]
        normal = subprocess.run([sys.executable, '-B', *args], capture_output=True, check=False)
        optimized = subprocess.run([sys.executable, '-B', '-O', *args], capture_output=True, check=False)
        self.assertEqual(normal.returncode, 0, normal.stderr)
        self.assertEqual(optimized.returncode, 0, optimized.stderr)
        self.assertEqual(normal.stdout, optimized.stdout)
        self.assertEqual(normal.stdout, (HERE / 'result.json').read_bytes())

    def test_exclusive_output_does_not_overwrite(self):
        with tempfile.TemporaryDirectory(dir=HERE, prefix='.test-render-') as folder:
            path = Path(folder) / 'result.json'
            path.write_bytes(b'fixture-existing')
            completed = subprocess.run([sys.executable, '-B', str(HERE / 'verify.py'), '--output', str(path)], capture_output=True, check=False)
            self.assertEqual(completed.returncode, 2)
            self.assertEqual(path.read_bytes(), b'fixture-existing')

    def test_corrupt_evidence_seal_rejected(self):
        with tempfile.TemporaryDirectory(dir=HERE, prefix='.test-render-') as folder:
            path = Path(folder) / 'evidence.json'
            path.write_bytes(v.document(self.evidence) + b' ')
            completed = subprocess.run([sys.executable, '-B', str(HERE / 'verify.py'), '--evidence', str(path)], capture_output=True, check=False)
            self.assertEqual(completed.returncode, 2)
            self.assertEqual(completed.stdout, b'')

    def test_build_requires_archive_root(self):
        with tempfile.TemporaryDirectory(dir=HERE, prefix='.test-render-') as folder:
            target = Path(folder) / 'evidence.json'
            completed = subprocess.run([sys.executable, '-B', str(HERE / 'verify.py'), '--build-evidence', str(target)], capture_output=True, check=False)
            self.assertEqual(completed.returncode, 2)
            self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
