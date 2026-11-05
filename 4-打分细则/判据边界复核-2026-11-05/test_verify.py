#!/usr/bin/env python3
"""Explicit local tests only: no discovery, product launches or historical graders."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TEST_FILES = ('test_lcb_visibility.py', 'test_dab_q49.py', 'test_cargo_heading.py')


def load_new(path, name):
    """Load this package's explicitly selected new source bytes, never a pyc loader."""
    raw = path.read_bytes()
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


class AggregateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = load_new(HERE / 'verify.py', 'criteria_boundary_verify_under_test')

    def test_frozen_real_bundle_read_only(self):
        paths = [HERE / 'verify.py', HERE / 'audit.json', ROOT / self.v.REPORT]
        paths += [HERE / name for name in self.v.HELPERS]
        before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        with mock.patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')), \
             mock.patch.object(subprocess, 'run', side_effect=AssertionError('process forbidden')), \
             mock.patch.object(Path, 'write_bytes', side_effect=AssertionError('write forbidden')), \
             mock.patch.object(Path, 'write_text', side_effect=AssertionError('write forbidden')):
            result = self.v.verify(ROOT)
        self.assertTrue(result['ok'])
        self.assertEqual(result['frozen_sources'], 18)
        self.assertEqual(result['new_product_or_model_runs'], 0)
        self.assertFalse(result['historical_regrade'])
        self.assertEqual(before, {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths})

    def test_derived_bundle_retains_non_scoring_and_unknown_boundaries(self):
        value = self.v.strict_json((HERE / 'audit.json').read_bytes())
        self.assertEqual(value['new_product_or_model_runs'], 0)
        self.assertEqual(value['new_formal_admissions'], 0)
        self.assertIs(value['historical_regrade'], False)
        self.assertIs(value['q49_gold_or_attribution_changed'], False)
        self.assertIs(value['cargo_diagnostic_changes_old_scoring'], False)
        self.assertEqual(len(value['frozen_source_sha256']), 18)
        self.assertEqual(set(value['checks']), {'lcb_visibility', 'dab_q49', 'cargo_heading'})
        self.assertEqual(set(value['reviewed_helper_sha256']), set(self.v.HELPERS))
        self.assertTrue(value['report_alignment']['formal_table_cells_and_reasons_equal'])

    def test_tampered_view_rejected_without_hiding_behind_source_hashes(self):
        expected = self.v.strict_json((HERE / 'audit.json').read_bytes())
        mutations = (
            ('new_product_or_model_runs', 1), ('new_formal_admissions', True),
            ('q49_gold_or_attribution_changed', True), ('cargo_diagnostic_changes_old_scoring', True),
            ('limits', []), ('checks', {}),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / self.v.PACKAGE / 'audit.json'
            target.parent.mkdir(parents=True)
            for key, value in mutations:
                actual = copy.deepcopy(expected)
                actual[key] = value
                target.write_text(json.dumps(actual, ensure_ascii=False), encoding='utf-8')
                with self.subTest(key=key), mock.patch.object(self.v, 'derive', return_value=expected):
                    with self.assertRaisesRegex(ValueError, 'derived audit mismatch'):
                        self.v.verify(root)

    def test_unreviewed_helper_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / self.v.PACKAGE / 'lcb_visibility.py'
            target.parent.mkdir(parents=True)
            target.write_text("raise AssertionError('unreviewed code executed')\n", encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'reviewed helper SHA mismatch'):
                self.v.load_reviewed_helpers(root)

    def test_helper_path_symlink_rejected_even_with_reviewed_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / self.v.PACKAGE / 'lcb_visibility.py'
            target.parent.mkdir(parents=True)
            same = root / 'same-bytes.py'
            same.write_bytes((HERE / 'lcb_visibility.py').read_bytes())
            target.symlink_to(same)
            with self.assertRaisesRegex(ValueError, 'symlink package path'):
                self.v.load_reviewed_helpers(root)

    def test_unsafe_and_noncanonical_package_paths(self):
        for path in ('/etc/passwd', '../x', 'a/../x', 'a\\x', './x', 'a//b', ''):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.v.safe_file(ROOT, path)

    def test_json_duplicate_and_nonfinite_rejected(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'[Infinity]', b'[-Infinity]', b'[1e999]'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.v.strict_json(raw)

    def test_canonical_comparison_preserves_json_types(self):
        for left, right in ((True, 1), (False, 0), (2, 2.0), ({'a': True}, {'a': 1})):
            with self.subTest(left=left, right=right):
                self.assertNotEqual(self.v.canonical(left), self.v.canonical(right))

    def test_formal_table_alignment_and_invalid_sections(self):
        old = (ROOT / self.v.OLD_REPORT).read_text(encoding='utf-8')
        new = (ROOT / self.v.REPORT).read_text(encoding='utf-8')
        self.assertEqual(self.v.formal_tables(old), self.v.formal_tables(new))
        synthetic = '## 3. formal\n| case | 1 |\n## 4. conclusions\n'
        self.assertNotEqual(self.v.formal_tables(synthetic), self.v.formal_tables(synthetic.replace('| 1 |', '| 2 |')))
        for broken in ('no tables', synthetic + '\n## 3. duplicate'):
            with self.assertRaises(ValueError):
                self.v.formal_tables(broken)

    def test_verifier_executes_only_explicit_hash_checked_new_helpers(self):
        source = (HERE / 'verify.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        imported = {node.names[0].name.split('.')[0] if isinstance(node, ast.Import) else node.module.split('.')[0]
                    for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))}
        self.assertLessEqual(imported, {'argparse', 'hashlib', 'json', 'math', 'pathlib', 'types'})
        self.assertEqual(set(self.v.HELPERS), {'lcb_visibility.py', 'dab_q49.py', 'cargo_heading.py'})
        self.assertNotIn('importlib', source)
        self.assertNotIn('subprocess', source)
        self.assertNotIn('checker.py', '\n'.join(self.v.HELPERS))
        self.assertIn("exec(compile(raw, str(path), 'exec'), module.__dict__)", source)


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite([loader.loadTestsFromTestCase(AggregateTests)])
    for index, filename in enumerate(TEST_FILES):
        module = load_new(HERE / filename, 'criteria_boundary_explicit_test_' + str(index))
        suite.addTests(loader.loadTestsFromModule(module))
    return not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()


if __name__ == '__main__':
    raise SystemExit(main())
