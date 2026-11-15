#!/usr/bin/env python3
"""对固定公开材料及合成篡改做离线回归；不会执行历史 SQL。"""
import contextlib
import copy
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import verify


class VerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql, cls.trace = verify.check_sources(verify.ROOT)
        folder = verify.ROOT / verify.CODEX / 'agent-session'
        sessions = [p.read_bytes() for p in folder.glob('*.jsonl') if verify.digest(p.read_bytes()) == verify.SESSION_SHA]
        cls.records = verify.json_lines(verify.one(sessions, '测试会话'))
        cls.probe = next(i for i, r in enumerate(cls.records) if r.get('type') == 'response_item' and r.get('payload', {}).get('type') == 'function_call' and "Q27 date boundary years" in json.loads(r['payload']['arguments']).get('cmd', ''))
        cid = cls.records[cls.probe]['payload']['call_id']
        cls.ret = next(i for i, r in enumerate(cls.records) if r.get('type') == 'response_item' and r.get('payload', {}).get('type') == 'function_call_output' and r['payload'].get('call_id') == cid)
        cls.patch = next(i for i, r in enumerate(cls.records) if r.get('type') == 'response_item' and r.get('payload', {}).get('type') == 'function_call' and '*** Add File: answers.jsonl' in json.loads(r['payload']['arguments']).get('cmd', ''))

    def check_bad_trace(self, records):
        with self.assertRaises(verify.VerificationError):
            verify.check_trace(records, self.sql['codex'])

    def test_real_sources_and_sequence(self):
        self.assertTrue(self.trace['probe_and_contrast_return_before_final_write'])
        self.assertEqual(self.trace['visible_q27_rows'], 16317)
        self.assertEqual(self.trace['closed_year_probe_rows'], 0)
        self.assertEqual(verify.check_trace(self.records, self.sql['codex']), self.trace)

    def test_mismatched_call_return(self):
        records = copy.deepcopy(self.records)
        records[self.ret]['payload']['call_id'] = 'mismatched'
        self.check_bad_trace(records)

    def test_duplicate_return(self):
        records = copy.deepcopy(self.records)
        records.insert(self.ret + 1, copy.deepcopy(records[self.ret]))
        self.check_bad_trace(records)

    def test_timestamp_and_order(self):
        records = copy.deepcopy(self.records)
        records[self.ret]['timestamp'] = '2000-01-01T00:00:00Z'
        self.check_bad_trace(records)
        records = copy.deepcopy(self.records)
        records[self.ret], records[self.patch] = records[self.patch], records[self.ret]
        self.check_bad_trace(records)

    def test_probe_output_and_final_answer(self):
        records = copy.deepcopy(self.records)
        args = json.loads(records[self.probe]['payload']['arguments'])
        args['cmd'] = args['cmd'].replace("ClosedDate<'2000'", "ClosedDate<'1990'")
        records[self.probe]['payload']['arguments'] = json.dumps(args)
        self.check_bad_trace(records)
        records = copy.deepcopy(self.records)
        records[self.ret]['payload']['output'] = records[self.ret]['payload']['output'].replace('-- Q27 closed years before 2000\n\n', '-- Q27 closed years before 2000\nnonempty\n')
        self.check_bad_trace(records)
        with self.assertRaises(verify.VerificationError):
            verify.check_trace(self.records, self.sql['codex'] + ' altered')

    def test_date_contrast_output_and_pairing(self):
        records = copy.deepcopy(self.records)
        idx = next(i for i, r in enumerate(records) if r.get('type') == 'response_item' and r.get('payload', {}).get('type') == 'function_call' and 'CAST(OpenDate AS TEXT)' in json.loads(r['payload']['arguments']).get('cmd', ''))
        cid = records[idx]['payload']['call_id']
        ret = next(i for i, r in enumerate(records) if r.get('type') == 'response_item' and r.get('payload', {}).get('type') == 'function_call_output' and r['payload'].get('call_id') == cid)
        records[ret]['payload']['output'] = records[ret]['payload']['output'].replace("('1989-06-30', 1, 0)", "('1989-06-30', 0, 0)")
        self.check_bad_trace(records)
        for old, new in (("OpenDate > '1991',OpenDate > '1991-12-31'", "OpenDate < '1991',OpenDate < '1991-12-31'"), ("OpenDate>'1991-12-31'", "OpenDate<'1991-12-31'")):
            records = copy.deepcopy(self.records)
            args = json.loads(records[idx]['payload']['arguments'])
            self.assertIn(old, args['cmd'])
            args['cmd'] = args['cmd'].replace(old, new)
            records[idx]['payload']['arguments'] = json.dumps(args)
            self.check_bad_trace(records)
        records = copy.deepcopy(self.records)
        records[ret]['payload']['call_id'] = 'not-paired'
        self.check_bad_trace(records)
        records = copy.deepcopy(self.records)
        records.insert(ret + 1, copy.deepcopy(records[ret]))
        self.check_bad_trace(records)
        records = copy.deepcopy(self.records)
        out = records[ret]['payload']['output']
        out = out.replace('(5083,)', '(TEMP,)', 1).replace('(16317,)', '(5083,)', 1).replace('(TEMP,)', '(16317,)', 1)
        records[ret]['payload']['output'] = out
        self.check_bad_trace(records)
        records = copy.deepcopy(self.records)
        out = records[ret]['payload']['output']
        section = "\n SELECT count(*) FROM schools WHERE OpenDate<'1991-01-01'\n(11097,)\n"
        self.assertEqual(out.count(section), 1)
        records[ret]['payload']['output'] = out.replace(section, '', 1) + section
        self.check_bad_trace(records)
        records = copy.deepcopy(self.records)
        records[ret]['timestamp'] = '2000-01-01T00:00:00Z'
        self.check_bad_trace(records)
        records = copy.deepcopy(self.records)
        records[ret], records[self.patch] = records[self.patch], records[ret]
        self.check_bad_trace(records)

    def test_changed_source_fails_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rel, _ = verify.SOURCES['questions']
            dest = root / rel
            dest.parent.mkdir(parents=True)
            dest.write_bytes(verify.checked_bytes(verify.ROOT, 'questions') + b' ')
            with self.assertRaises(verify.VerificationError):
                verify.checked_bytes(root, 'questions')

    def test_sidecar_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / verify.SOURCES['database'][0]
            db.parent.mkdir(parents=True)
            Path(str(db) + '-wal').touch()
            with self.assertRaises(verify.VerificationError):
                verify.database_report(root)

    def test_input_and_error_redaction(self):
        secret = 'private-dynamic-path-not-for-error-output'
        for argv in (['--root', '/absent/' + secret], ['--unexpected', secret], ['--root']):
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(verify.main(argv), 1)
            self.assertNotIn(secret, stderr.getvalue())
        with self.assertRaises(verify.VerificationError):
            verify.answer(b'{"question_id":27,"sql":"anything"}\n')
        with self.assertRaises((ValueError, verify.VerificationError)):
            verify.json_lines(b'not json\n')

    def test_readonly_fixed_predicates_and_types(self):
        data = verify.database_report(verify.ROOT)
        self.assertEqual(data['schools_total'], 17686)
        self.assertEqual(data['predicate_counts'], {'year': 8574, 'full_date': 8574, 'bare_year': 16317, 'open_year': 5083, 'open_full': 5083, 'open_bare': 16317, 'closed_year': 3600, 'closed_full': 3600, 'closed_bare': 0})
        self.assertEqual(data['primary_key_differences']['year_minus_full_date'], 0)
        self.assertEqual(data['primary_key_differences']['full_date_minus_year'], 0)
        self.assertEqual(data['primary_key_differences']['year_minus_bare_year'], 0)
        self.assertEqual(data['primary_key_differences']['bare_year_minus_year'], 7743)
        self.assertEqual(data['storage_types_and_null'], {'OpenDate': {'null': 1369, 'text': 16317}, 'ClosedDate': {'null': 11992, 'text': 5694}})
        fixture = verify.fixture_report()
        rows = {r[0]: r for r in fixture['rows']}
        self.assertEqual(rows['old'][3:6], (1, 0, 0))
        self.assertEqual(rows['boundary'][6:12], (0, 0, 1, 1, 0, 1))
        self.assertEqual(rows['number_text'][1:3], ('integer', 'text'))
        self.assertEqual(rows['number_int'][3:6], (1, 1, 0))
        self.assertIsNone(rows['null'][9])
        self.assertIsNone(rows['invalid_date'][6])
        self.assertEqual(rows['invalid_date'][7], 1)

    def test_command_normal_and_optimized(self):
        script = Path(verify.__file__)
        for flags in (['-B'], ['-B', '-O']):
            proc = subprocess.run([sys.executable, *flags, str(script)], capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            out = json.loads(proc.stdout)
            self.assertEqual(out['canonical_database']['primary_key_differences']['bare_year_minus_year'], 7743)
            self.assertTrue(out['source_sha_verified'])

if __name__ == '__main__':
    unittest.main()
