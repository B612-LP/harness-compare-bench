#!/usr/bin/env python3
"""Explicit-file tests: only the reviewed NEW verifier is compiled, deferred.
Semantic mutations call validate_index directly; snapshot mutations test pins.
Temporary fixtures contain only seven document copies, never old executable code.
"""
import ast
import copy
from contextlib import contextmanager
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import types
import unittest
from unittest import mock

EXPECTED_VERIFY_SHA = '692d2725ea7e24e267f151996da7cf374844a8bd69a3dc37831af453c0f632d8'


def load_reviewed_new_module():
    path = Path(__file__).resolve().with_name('verify.py')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED_VERIFY_SHA:
        raise ValueError('new verifier differs from reviewed bytes')
    module = types.ModuleType('reviewed_source_index_verifier')
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module, raw


class SemanticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v, cls.code = load_reviewed_new_module()

    def rejected(self, path, value):
        index = copy.deepcopy(self.v.EXPECTED_INDEX)
        current = index
        for key in path[:-1]:
            current = current[key]
        current[path[-1]] = value
        with self.assertRaises(ValueError):
            self.v.validate_index(index)

    def test_positive_contract(self):
        result = self.v.validate_index(copy.deepcopy(self.v.EXPECTED_INDEX))
        self.assertEqual(result['case_count'], 5)
        self.assertFalse(result['new_license_granted'])
        self.assertFalse(result['legal_compliance_certified'])
        self.assertEqual(result['original_asset_license_status'], 'not_selected')
        self.assertEqual(result['case_ids'], ['bird-ca-schools-15', 'dabstep-payments-10',
                         'exercism-py-6', 'lcb-recent-hard-4', 'tb-cargo-plan'])

    def test_no_unified_mit_or_new_grant(self):
        for path, value in [
            (['license_grant', 'new_license_granted'], True),
            (['license_grant', 'legal_compliance_certified'], True),
            (['original_assets', 'license'], 'MIT'),
            (['original_assets', 'license_status'], 'MIT'),
            (['original_assets', 'decision_by'], 'agent'),
            (['original_assets', 'decision_status'], 'completed'),
            (['original_assets', 'third_party_excluded'], False),
        ]:
            with self.subTest(path=path):
                self.rejected(path, value)

    def test_atcoder_not_covered_by_project_mit(self):
        case = self.v.EXPECTED_INDEX['cases'][3]
        self.assertGreaterEqual(len(case['source_parts']), 2)
        atcoder = [i for i, part in enumerate(case['source_parts'])
                   if part['role']=='original_problem_source']
        self.assertEqual(len(atcoder), 1)
        self.assertEqual(case['source_parts'][atcoder[0]]['declared_license'],
                         'not_established_by_cited_material')
        self.rejected(['cases', 3, 'source_parts', atcoder[0], 'declared_license'], 'MIT')
        self.rejected(['cases', 3, 'source_parts', atcoder[0], 'license_scope'], 'all_repository_material')

    def test_distinct_case_license_declarations_preserved(self):
        for i, wrong in [(0,'MIT'), (1,'CC-BY-SA-4.0'), (2,'Apache-2.0'), (4,'MIT')]:
            with self.subTest(case=i):
                self.rejected(['cases', i, 'source_parts', 0, 'declared_license'], wrong)

    def test_unknown_cannot_be_promoted_to_verified(self):
        for i in range(5):
            for path, value in [
                (['cases',i,'upstream_version','status'], 'verified'),
                (['cases',i,'upstream_version','value'], 'main'),
                (['cases',i,'upstream_terms','status'], 'verified'),
                (['cases',i,'upstream_terms','original_license_url'], 'https://example.org/LICENSE'),
                (['cases',i,'upstream_terms','local_copy'], 'LICENSE'),
                (['cases',i,'upstream_terms','sha256'], '0'*64),
                (['cases',i,'upstream_terms','notice_status'], 'verified'),
                (['cases',i,'upstream_terms','notice_local_copy'], 'NOTICE'),
                (['cases',i,'upstream_terms','notice_sha256'], '0'*64),
            ]:
                with self.subTest(path=path):
                    self.rejected(path, value)

    def test_missing_duplicate_reordered_and_extra_case(self):
        cases = self.v.EXPECTED_INDEX['cases']
        for bad in [cases[:-1], cases+[cases[0]], [cases[0]]+cases[:-1], list(reversed(cases))]:
            with self.subTest(count=len(bad)):
                self.rejected(['cases'], bad)

    def test_wrong_evidence_not_hidden_by_source_hash_layer(self):
        self.rejected(['cases',0,'evidence',0,'path'], self.v.EXPECTED_INDEX['cases'][1]['evidence'][0]['path'])
        self.rejected(['cases',0,'evidence',0,'line_start'], 1)
        self.rejected(['cases',0,'evidence',0,'line_end'], 999999)
        self.rejected(['cases',0,'evidence',0,'sha256'], '0'*64)
        self.rejected(['cases',0,'evidence',0,'quote'], 'All materials are MIT licensed.')
        self.rejected(['cases',0,'evidence'], [])

    def test_types_boolean_integer_float_and_narrative(self):
        for path, value in [
            (['license_grant','new_license_granted'], 0),
            (['license_grant','legal_compliance_certified'], 0.0),
            (['cases',0,'evidence',0,'line_start'], True),
            (['cases',0,'evidence',0,'line_end'], float(self.v.EXPECTED_INDEX['cases'][0]['evidence'][0]['line_end'])),
            (['cases',0,'source_parts'], {}),
            (['cases',0,'reuse_summary'], 'All copied material is now MIT.'),
            (['cases',0,'remaining_boundaries'], []),
            (['limits'], []),
            (['date'], 20261105),
        ]:
            with self.subTest(path=path):
                self.rejected(path, value)
        index = copy.deepcopy(self.v.EXPECTED_INDEX)
        index['unified_license'] = 'MIT'
        with self.assertRaises(ValueError):
            self.v.validate_index(index)
        del index['unified_license']
        del index['schema']
        with self.assertRaises(ValueError):
            self.v.validate_index(index)

    def test_strict_json_and_nonfinite(self):
        for raw in [b'{"a":1,"a":2}', b'{"a":{"b":1,"b":2}}', b'NaN',
                    b'Infinity', b'-Infinity', b'{"a":1e999}', b'\xff']:
            with self.subTest(raw=raw):
                with self.assertRaises((ValueError, UnicodeError)):
                    self.v.parse_json(raw)
        self.assertEqual(self.v.parse_json(b'{"a":2}'), {'a':2})
        with self.assertRaises(ValueError):
            self.v.same({'a':2.0}, {'a':2})
        with self.assertRaises(ValueError):
            self.v.same(False, 0)

    def test_production_import_and_execution_boundary(self):
        tree = ast.parse(self.code)
        allowed = {'argparse','hashlib','json','math','pathlib'}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(all(alias.name in allowed for alias in node.names))
            elif isinstance(node, ast.ImportFrom):
                self.assertIn(node.module, allowed)
                self.assertEqual(node.level, 0)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, {'eval','exec','compile','__import__'})


class SnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v, _ = load_reviewed_new_module()
        cls.repo = Path(__file__).resolve().parents[2]
        cls.seed = {name:(cls.repo/name).read_bytes()
                    for name in list(cls.v.DOCUMENT_PINS)+list(cls.v.SOURCE_PINS)}

    @contextmanager
    def fixture(self):
        with tempfile.TemporaryDirectory(prefix='source-index-test-') as temporary:
            root = Path(temporary).resolve()
            for name, raw in self.seed.items():
                target = root/name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
            yield root

    def test_positive_readonly_no_code_process_or_network(self):
        def blocked(*args, **kwargs):
            raise AssertionError('forbidden side effect')
        real_io, real_open = io.open, open
        def readonly(original):
            def guarded(file, mode='r', *args, **kwargs):
                if any(flag in mode for flag in 'wax+'):
                    blocked()
                return original(file, mode, *args, **kwargs)
            return guarded
        with self.fixture() as root:
            before = {name:(root/name).read_bytes() for name in self.seed}
            with mock.patch('io.open', readonly(real_io)), mock.patch('builtins.open', readonly(real_open)), \
                 mock.patch.object(Path,'write_bytes',blocked), mock.patch.object(Path,'write_text',blocked), \
                 mock.patch.object(subprocess,'run',blocked), mock.patch.object(subprocess,'Popen',blocked), \
                 mock.patch.object(socket,'socket',blocked), mock.patch.object(os,'system',blocked), \
                 mock.patch('builtins.exec',blocked), mock.patch('builtins.eval',blocked):
                result = self.v.derive(root)
            self.assertEqual(result['case_count'], 5)
            self.assertEqual(result['pinned_document_count'], 7)
            self.assertFalse(result['legal_compliance_certified'])
            self.assertEqual(before, {name:(root/name).read_bytes() for name in self.seed})

    def test_new_documents_pinned_before_semantics(self):
        with self.fixture() as root:
            path = root/(self.v.BASE+'sources.json')
            index = self.v.parse_json(path.read_bytes())
            index['license_grant']['new_license_granted'] = True
            path.write_text(json.dumps(index),encoding='utf-8')
            with mock.patch.object(self.v,'validate_index',side_effect=AssertionError('semantic layer entered')):
                with self.assertRaisesRegex(ValueError, 'document hash mismatch'):
                    self.v.derive(root)
        with self.fixture() as root:
            path = root/(self.v.BASE+'README.md')
            path.write_bytes(path.read_bytes()+b'\nMIT\n')
            with self.assertRaisesRegex(ValueError, 'document hash mismatch'):
                self.v.derive(root)

    def test_missing_and_tampered_existing_evidence_source(self):
        name = next(iter(self.v.SOURCE_PINS))
        for operation in ('missing','tampered'):
            with self.subTest(operation=operation), self.fixture() as root:
                path = root/name
                if operation=='missing':
                    path.unlink()
                else:
                    path.write_bytes(path.read_bytes()+b'\n')
                with self.assertRaisesRegex(ValueError, 'missing regular file|source hash mismatch'):
                    self.v.derive(root)

    def test_evidence_quotes_recomputed_from_actual_lines(self):
        sources = {name:self.seed[name] for name in self.v.SOURCE_PINS}
        self.v.check_evidence(self.v.EXPECTED_INDEX, sources)
        bad = copy.deepcopy(self.v.EXPECTED_INDEX)
        bad['cases'][0]['evidence'][0]['quote'] += 'X'
        with self.assertRaisesRegex(ValueError, 'evidence quote'):
            self.v.check_evidence(bad, sources)
        bad['cases'][0]['evidence'][0]['line_start'] = True
        with self.assertRaisesRegex(ValueError, 'invalid evidence line'):
            self.v.check_evidence(bad, sources)

    def test_canonical_paths_and_missing_files(self):
        with self.fixture() as root:
            for path in ('/etc/passwd','../outside','a/../b','a//b','a/./b','a\\b','a/','',True,3):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    self.v.safe_file(root,path)
            with self.assertRaisesRegex(ValueError, 'missing regular file'):
                self.v.safe_file(root,'not-present')

    def test_descendant_and_leaf_symlinks_even_same_bytes(self):
        with self.fixture() as root:
            (root/'real').mkdir()
            (root/'real'/'file').write_bytes(b'same')
            (root/'alias').symlink_to(root/'real',target_is_directory=True)
            (root/'leaf').symlink_to(root/'real'/'file')
            for path in ('alias/file','leaf'):
                with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'symlink'):
                    self.v.safe_file(root,path)
        with self.fixture() as root:
            name = next(iter(self.v.SOURCE_PINS))
            actual = root/name
            other = root/'same-evidence'
            other.write_bytes(actual.read_bytes())
            actual.unlink()
            actual.symlink_to(other)
            with self.assertRaisesRegex(ValueError, 'symlink'):
                self.v.derive(root)

    def test_root_symlink_and_source_byte_budget(self):
        with self.fixture() as root:
            alias = root/'root-alias'
            alias.symlink_to(root,target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'invalid root'):
                self.v.safe_file(alias,next(iter(self.v.SOURCE_PINS)))
            raw = b'x'*(self.v.MAX_BYTES+1)
            (root/'oversize').write_bytes(raw)
            with self.assertRaisesRegex(ValueError, 'byte budget'):
                self.v.read_pinned(root,'oversize',hashlib.sha256(raw).hexdigest(),'document')


if __name__=='__main__':
    unittest.main()
