#!/usr/bin/env python3
"""验收框架负对照；只操作临时合成JSON，不运行产品或候选解答。"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

PAGE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('wire_verify', PAGE / 'verify2.py')
v = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v)


class CoverageTests(unittest.TestCase):
    def tearDown(self):
        v.FAILS.clear()
        v.SKIPS.clear()

    def test_exact_set_allows_reordered_output(self):
        self.assertEqual(v.validate_verdicts(['a', 'b'], [
            {'id': 'b', 'verdict': 'parse_error'}, {'id': 'a', 'verdict': 'match'}]),
            {'b': 'parse_error', 'a': 'match'})

    def test_empty_output_rejected(self):
        with self.assertRaisesRegex(ValueError, 'coverage mismatch'):
            v.validate_verdicts(['a'], [])

    def test_empty_expected_rejected(self):
        with self.assertRaisesRegex(ValueError, 'empty or duplicate'):
            v.validate_verdicts([], [])

    def test_missing_rejected(self):
        with self.assertRaisesRegex(ValueError, 'coverage mismatch'):
            v.validate_verdicts(['a', 'b'], [{'id': 'a', 'verdict': 'match'}])

    def test_extra_rejected(self):
        with self.assertRaisesRegex(ValueError, 'coverage mismatch'):
            v.validate_verdicts(['a'], [{'id': 'a', 'verdict': 'match'},
                                      {'id': 'b', 'verdict': 'match'}])

    def test_duplicate_output_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate result'):
            v.validate_verdicts(['a'], [{'id': 'a', 'verdict': 'match'}] * 2)

    def test_duplicate_expected_rejected(self):
        with self.assertRaisesRegex(ValueError, 'empty or duplicate'):
            v.validate_verdicts(['a', 'a'], [{'id': 'a', 'verdict': 'match'}])

    def test_invalid_verdict_rejected(self):
        with self.assertRaisesRegex(ValueError, 'invalid verdict'):
            v.validate_verdicts(['a'], [{'id': 'a', 'verdict': 'PASS'}])

    def test_fake_empty_node_output_rejected_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            corpus, out = d / 'corpus.jsonl', d / 'out.jsonl'
            corpus.write_text(json.dumps({'id': 'a', 'canon_sha256': '0' * 64}) + '\n')
            out.write_text('')
            with patch.object(v.shutil, 'which', return_value='node'), \
                 patch.object(v.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)):
                with self.assertRaisesRegex(ValueError, 'coverage mismatch'):
                    v.run_crossparse(d, corpus, out, 'typed')

    def test_timeout_is_bounded_and_propagated(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            corpus = d / 'corpus.jsonl'
            corpus.write_text(json.dumps({'id': 'a', 'canon_sha256': '0' * 64}) + '\n')
            with patch.object(v.shutil, 'which', return_value='node'), \
                 patch.object(v.subprocess, 'run', side_effect=subprocess.TimeoutExpired('node', 60)) as run:
                with self.assertRaises(subprocess.TimeoutExpired):
                    v.run_crossparse(d, corpus, d / 'out', 'typed')
                self.assertEqual(run.call_args.kwargs['timeout'], 60)

    def test_node_missing_is_incomplete_not_all_pass(self):
        stdout = io.StringIO()
        with patch.object(v.shutil, 'which', return_value=None), contextlib.redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as exc:
                v.main()
        self.assertEqual(exc.exception.code, 2)
        self.assertIn('INCOMPLETE', stdout.getvalue())
        self.assertNotIn('ALL EXPECTED CHECKS PASS', stdout.getvalue())

    def test_source_pin_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            raw = d / 'raw.jsonl'
            raw.write_text('{}\n')
            with patch.object(v, 'SOURCES', [('fake', raw, 1, '0' * 64)]), \
                 contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(ValueError, 'source hash mismatch'):
                    v.part_b(d)


class RawAndCanonicalTests(unittest.TestCase):
    def test_unicode_line_separators_not_jsonl_delimiters(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'raw.jsonl'
            text = json.dumps({'x': chr(0x2028) + chr(0x2029)}, ensure_ascii=False)
            p.write_bytes((text + '\n{}\n').encode('utf-8'))
            rows = v.load_jsonl(p)
            self.assertEqual(len(rows), 2)
            self.assertEqual([ord(c) for c in rows[0]['x']], [0x2028, 0x2029])

    def test_strict_duplicate_rejected(self):
        with self.assertRaisesRegex(ValueError, 'DUP_KEY'):
            v.strict_load('{"__proto__":1,"__proto__":2}')

    def test_strict_non_finite_rejected(self):
        for raw in ('NaN', 'Infinity', '-Infinity', '1e999'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                v.strict_load(raw)

    def test_lone_surrogate_not_canonicalized(self):
        with self.assertRaises(UnicodeEncodeError):
            v.strict_load('"' + chr(0xD800) + '"')

    def test_integer_precision_preserved_by_python_reference(self):
        self.assertEqual(v.canon(v.strict_load('{"v":9007199254740993}')),
                         b'{"v":9007199254740993}')

    def test_float_tie_reference_is_not_rounded_up(self):
        self.assertEqual(v.canon(v.strict_load('{"v":1000000000000000.2}')),
                         b'{"v":1000000000000000.2}')


if __name__ == '__main__':
    unittest.main()
