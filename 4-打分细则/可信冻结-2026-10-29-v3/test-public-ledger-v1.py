#!/usr/bin/env python3
"""Offline projection checks; never promote a summary to private verification."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('public_ledger', HERE / 'verify-public-ledger-v1.py')
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


class ProjectionTests(unittest.TestCase):
    def check_private_unavailable(self, result):
        self.assertEqual(result['private_originals'], 'PRIVATE_UNAVAILABLE')
        self.assertIs(result['all_originals_verified'], False)

    def test_public_summary(self):
        result = verifier.verify(HERE / 'public-ledger-summary-v1.json')
        self.assertEqual(result['public_summary'], 'PUBLIC_SUMMARY_VERIFIED')
        self.check_private_unavailable(result)

    def test_missing_summary(self):
        with tempfile.TemporaryDirectory() as d:
            result = verifier.verify(Path(d) / 'missing.json')
            self.assertEqual(result['public_summary'], 'PUBLIC_SUMMARY_INVALID')
            self.check_private_unavailable(result)

    def test_tampered_summary(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'summary.json'
            p.write_text('{}', encoding='utf-8')
            result = verifier.verify(p)
            self.assertEqual(result['public_summary'], 'PUBLIC_SUMMARY_INVALID')
            self.check_private_unavailable(result)


if __name__ == '__main__':
    unittest.main()
