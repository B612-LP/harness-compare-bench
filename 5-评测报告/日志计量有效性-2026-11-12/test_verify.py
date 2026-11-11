#!/usr/bin/env python3
"""Independent bad-input and arithmetic tests; safe with Python -O.
Fixtures copy only the fixed public source set into a temporary root.
"""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
spec = importlib.util.spec_from_file_location('log_measurement_verify', HERE / 'verify.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


class VerifyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (HERE / 'evidence.json').read_bytes()
        cls.evidence = v.strict_json(cls.raw)
        cls.prior = v.strict_json((REPO / v.PRIOR).read_bytes())
        cls.temp = tempfile.TemporaryDirectory(prefix='log-measurement-tests-')
        cls.root = Path(cls.temp.name).resolve()
        for rel in [v.PRIOR, v.HERE + '/evidence.json'] + [s['path'] for s in cls.prior['public_sources']]:
            target = cls.root / rel
            v.require(cls.root in target.resolve().parents, 'unsafe fixture target')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / rel, target)
        cls.actual = v.analyze(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def rows(self, arm):
        slot = next(s for s in self.evidence['slots'] if s['slot'].startswith(arm + '__'))
        prior = next(s for s in self.prior['slots'] if s['slot'] == slot['slot'])
        return copy.deepcopy(slot['events']), prior['events']

    def fail_projection(self, change):
        data = copy.deepcopy(self.evidence)
        change(data)
        path = self.root / v.HERE / 'evidence.json'
        raw = v.canon(data)
        path.write_bytes(raw)
        try:
            # Bypass only the outer fixed hash to exercise deeper schema gates.
            with mock.patch.object(v, 'EVIDENCE_SHA256', v.sha(raw)):
                with self.assertRaises((v.Invalid, KeyError, TypeError)):
                    v.analyze(self.root)
        finally:
            path.write_bytes(self.raw)

    def cli(self, *args, optimize=False):
        flags = ['-I', '-S', '-B'] + (['-O'] if optimize else [])
        return subprocess.run([sys.executable] + flags + [str(HERE / 'verify.py')] + list(args), capture_output=True, check=False)

    def test_actual_counts(self):
        r = self.actual
        self.assertEqual((r['public_sources_checked'], r['private_source_bindings_checked'], r['projected_events']), (69, 30, 5863))
        self.assertEqual((r['dsh']['S3_bytes'], r['dsh']['static_declaration_bytes'], r['codex']['R3_bytes'], r['codex']['R4_bytes']), (396065, 271275, 4325070, 2359347))
        self.assertEqual((r['codex']['R3_min'], r['codex']['R3_max']), (60064, 789813))

    def test_actual_result_byte_identical(self):
        self.assertEqual(v.render(self.actual), (HERE / 'result.json').read_bytes())

    def test_default_stdout(self):
        p = self.cli()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout, v.render(self.actual))

    def test_optimized_stdout(self):
        p = self.cli('--root', str(self.root), optimize=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout, v.render(self.actual))

    def test_output_new_and_no_overwrite(self):
        target = self.root / 'new-result.json'
        p = self.cli('--root', str(self.root), '--output', str(target))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(target.read_bytes(), v.render(self.actual))
        p = self.cli('--root', str(self.root), '--output', str(target), optimize=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(target.read_bytes(), v.render(self.actual))
        self.assertEqual(p.stdout, b'')

    def test_missing_source(self):
        rel = self.prior['public_sources'][0]['path']
        path = self.root / rel
        raw = path.read_bytes()
        # A missing path is requested, without deleting any repository file.
        original = v.bound_bytes
        with mock.patch.object(v, 'bound_bytes', wraps=original) as reader:
            def missing(root, relative, expected):
                return original(root, 'not-present/source.json' if relative == rel else relative, expected)
            reader.side_effect = missing
            with self.assertRaises(v.Invalid):
                v.analyze(self.root)
        self.assertEqual(path.read_bytes(), raw)

    def test_changed_source_bytes(self):
        path = self.root / self.prior['public_sources'][0]['path']
        raw = path.read_bytes(); path.write_bytes(raw + b' ')
        try:
            with self.assertRaises(v.Invalid):
                v.analyze(self.root)
        finally:
            path.write_bytes(raw)

    def test_missing_root(self):
        p = self.cli('--root', str(self.root / 'not-present'))
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(p.stdout, b'')

    def test_evidence_hash_changed(self):
        path = self.root / v.HERE / 'evidence.json'
        path.write_bytes(self.raw + b' ')
        try:
            with self.assertRaises(v.Invalid):
                v.analyze(self.root)
        finally:
            path.write_bytes(self.raw)

    def test_bad_schema(self):
        self.fail_projection(lambda x: x.update(schema='wrong'))

    def test_unknown_top_level(self):
        self.fail_projection(lambda x: x.update(extra=1))

    def test_column_changed(self):
        self.fail_projection(lambda x: x['columns'].__setitem__(0, 'other'))

    def test_normalization_changed(self):
        self.fail_projection(lambda x: x['stripped_payload_keys'].append('content'))

    def test_missing_slot(self):
        self.fail_projection(lambda x: x['slots'].pop())

    def test_duplicate_slot(self):
        self.fail_projection(lambda x: x['slots'].__setitem__(0, x['slots'][1]))

    def test_mixed_slot(self):
        self.fail_projection(lambda x: x['slots'][0].update(slot='codex__bird-ca-schools-15__r1'))

    def test_bad_source_binding(self):
        self.fail_projection(lambda x: x['slots'][0].update(source_sha256='0' * 64))

    def test_wrong_boolean_integer(self):
        rows, old = self.rows('dsh'); rows[0][1] = True
        with self.assertRaises(v.Invalid):
            v.validate_rows(rows, 'dsh', old)
        with self.assertRaises(v.Invalid):
            v.integer(True)

    def test_negative_integer(self):
        with self.assertRaises(v.Invalid):
            v.integer(-1)

    def test_noninteger(self):
        for value in (1.0, '1', None, [], {}):
            with self.assertRaises(v.Invalid):
                v.integer(value)

    def test_wrong_four_columns(self):
        rows, old = self.rows('codex'); rows[0][1] += 1
        with self.assertRaises(v.Invalid):
            v.validate_rows(rows, 'codex', old)

    def test_wrong_row_length(self):
        rows, old = self.rows('dsh'); rows[0].pop()
        with self.assertRaises(v.Invalid):
            v.validate_rows(rows, 'dsh', old)

    def test_bad_digest(self):
        rows, old = self.rows('dsh'); rows[0][6] = 'a' * 63
        with self.assertRaises(v.Invalid):
            v.validate_rows(rows, 'dsh', old)

    def test_wrong_role(self):
        rows, old = self.rows('codex')
        next(r for r in rows if r[0] == 'response_item' and r[2] == 'message')[4] = 'system'
        with self.assertRaises(v.Invalid):
            v.validate_rows(rows, 'codex', old)

    def test_wrong_user_source_kind(self):
        rows, old = self.rows('dsh')
        next(r for r in rows if r[0] == 'user/message')[5] = 'invented'
        with self.assertRaises(v.Invalid):
            v.validate_rows(rows, 'dsh', old)

    def test_negative_user_overhead(self):
        rows, old = self.rows('dsh')
        row = next(r for r in rows if r[0] == 'user/message')
        row[11]['parts']['content'][0] = row[1] + 1
        with self.assertRaises(v.Invalid):
            v.validate_rows(rows, 'dsh', old)

    def test_negative_header_overhead(self):
        rows, old = self.rows('dsh')
        row = next(r for r in rows if r[0] == 'request/header')
        row[11]['parts']['tools'][0] = row[1] + 1
        with self.assertRaises(v.Invalid):
            v.validate_rows(rows, 'dsh', old)

    def test_unknown_detail(self):
        rows, old = self.rows('dsh'); rows[0][11]['parts']['unknown'] = [1, 'a' * 64]
        with self.assertRaises(v.Invalid):
            v.validate_rows(rows, 'dsh', old)

    def test_duplicate_json_key(self):
        with self.assertRaises(v.Invalid):
            v.strict_json(b'{"x":1,"x":2}')

    def test_nonfinite_json(self):
        for value in (b'NaN', b'Infinity', b'-Infinity'):
            with self.assertRaises(v.Invalid):
                v.strict_json(value)

    def test_invalid_utf8(self):
        with self.assertRaises(v.Invalid):
            v.strict_json(b'\xff')

    def test_path_escape(self):
        for rel in ('../escape.json', '/absolute.json'):
            with self.assertRaises(v.Invalid):
                v.bound_bytes(self.root, rel, '0' * 64)

    def test_tail_is_preserved(self):
        rows, _ = self.rows('codex')
        leading = [r for r in rows if r[0] == 'response_item'][:3]
        meta = next(r for r in rows if r[0] == 'session_meta')
        r = v.codex_measure([meta] + leading)
        self.assertEqual((r['usage_markers'], r['unclosed_tail_segments']), (0, 1))
        self.assertEqual(r['R3_bytes'], sum(x[3] for x in leading))
        self.assertEqual(r['R3_bytes'], r['segments'][0]['R3_bytes'])

    def test_empty_usage_segment_is_preserved(self):
        rows, _ = self.rows('codex')
        leading = [r for r in rows if r[0] == 'response_item'][:3]
        meta = next(r for r in rows if r[0] == 'session_meta')
        usage = next(r for r in rows if r[0] == 'token_usage_record')
        r = v.codex_measure([meta] + leading + [usage, usage])
        self.assertEqual((r['usage_markers'], r['empty_closed_segments'], r['unclosed_tail_segments']), (2, 1, 0))
        self.assertEqual(sum(s['R3_bytes'] for s in r['segments']), r['R3_bytes'])

    def test_output_before_call_rejected(self):
        rows, _ = self.rows('codex')
        call = next(i for i, r in enumerate(rows) if r[0] == 'response_item' and r[2] == 'function_call')
        output = next(i for i, r in enumerate(rows) if r[0] == 'response_item' and r[2] == 'function_call_output' and r[10] == rows[call][10])
        rows[call], rows[output] = rows[output], rows[call]
        with self.assertRaises(v.Invalid):
            v.codex_measure(rows)

    def test_duplicate_output_identity_rejected(self):
        rows, _ = self.rows('codex')
        outputs = [r for r in rows if r[0] == 'response_item' and r[2] == 'function_call_output']
        outputs[1][10] = outputs[0][10]
        with self.assertRaises(v.Invalid):
            v.codex_measure(rows)

    def test_normalized_duplicates_not_exact_duplicates(self):
        self.assertEqual(self.actual['codex']['exact_payload_excess_duplicates'], 0)
        self.assertEqual(self.actual['codex']['stripped_metadata_excess_duplicates'], 3)
        self.assertEqual(self.actual['codex']['duplicate_item_ids'], 0)
        self.assertEqual(self.actual['codex']['later_control_matches'], 0)

    def test_async_difference_closes(self):
        d = self.actual['dsh']['users_by_source_kind']
        self.assertEqual(d['tool-jobs']['event_bytes'] + d['subagent-settled']['event_bytes'], 956)
        ds = {s['slot']: s for s in self.actual['per_slot'] if s['slot'].startswith('dsh__dabstep')}
        self.assertEqual(ds['dsh__dabstep-payments-10__r1']['S3_bytes'] - ds['dsh__dabstep-payments-10__r2']['S3_bytes'], 956)

    def test_readme_tables_match_actual_result(self):
        text = (HERE / 'README.md').read_text(encoding='utf-8')
        for r in self.actual['per_slot']:
            if r['slot'].startswith('dsh__'):
                label = r['slot'][5:]
                t = r['excluded_from_S3']['tool/result']
                expected = f"| {label} | {r['S3_bytes']} | {r['S4_bytes']} | {t['count']} | {t['bytes']} |"
            else:
                label = r['slot'][7:]
                t = r['by_payload_type']
                values = [r['R3_bytes'], r['R4_bytes']] + [t[k]['bytes'] for k in ('message', 'reasoning', 'function_call', 'function_call_output')] + [r['usage_markers']]
                expected = '| ' + label + ' | ' + ' | '.join(str(x) for x in values) + ' |'
            self.assertIn(expected, text)
        for kind, r in self.actual['dsh']['users_by_source_kind'].items():
            values = [r[k] for k in ('count', 'event_bytes', 'content_canonical_bytes', 'source_canonical_bytes', 'event_other_bytes', 'text_utf8_bytes')]
            self.assertIn('| ' + kind + ' | ' + ' | '.join(str(x) for x in values) + ' |', text)
        for key in ('dsh', 'codex'):
            field = 'excluded_from_S3' if key == 'dsh' else 'excluded_event_types'
            for kind, r in self.actual[key][field].items():
                self.assertIn(f"| {kind} | {r['count']} | {r['bytes']} |", text)
        for kind, r in self.actual['codex']['by_payload_type'].items():
            r4 = r['bytes'] if kind in ('message', 'reasoning') else 0
            self.assertIn(f"| {kind} | {r['count']} | {r['bytes']} | {r4} |", text)
        for role, r in self.actual['codex']['message_by_role'].items():
            self.assertIn(f"| {role} | {r['count']} | {r['bytes']} |", text)

    def test_all_accounting_identities(self):
        for r in self.actual['per_slot']:
            if r['slot'].startswith('dsh__'):
                self.assertEqual(r['S3_bytes'], sum(x['bytes'] for x in r['S3_by_type'].values()))
                for x in r['users_by_source_kind'].values():
                    self.assertEqual(x['event_bytes'], x['content_canonical_bytes'] + x['source_canonical_bytes'] + x['event_other_bytes'])
            else:
                self.assertEqual(r['R3_bytes'], sum(x['bytes'] for x in r['by_payload_type'].values()))
                self.assertEqual(r['R4_bytes'], sum(r['by_payload_type'].get(k, {'bytes': 0})['bytes'] for k in ('message', 'reasoning')))
                self.assertEqual(r['R3_bytes'], sum(s['R3_bytes'] for s in r['segments']))
                self.assertEqual(r['R4_bytes'], sum(s['R4_bytes'] for s in r['segments']))
                self.assertEqual(r['by_payload_type']['message']['bytes'], sum(x['bytes'] for x in r['message_by_role'].values()))


if __name__ == '__main__':
    unittest.main()
