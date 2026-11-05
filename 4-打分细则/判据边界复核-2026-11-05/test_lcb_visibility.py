"""LCB source-anchor tests plus direct pure-data semantic negatives.

No old checker/solution/candidate is imported or executed. Only setUpClass reads
sources; importing this test file does not load the implementation or run tests.
"""
from pathlib import Path
import copy
import hashlib
import json
import socket
import subprocess
import tempfile
import types
import unittest
from unittest import mock


def load_module():
    path = Path(__file__).with_name('lcb_visibility.py')
    module = types.ModuleType('reviewed_lcb_visibility')
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
    return module


class LCBVisibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()
        cls.root = Path(__file__).resolve().parents[2]
        cls.blobs = {p: (cls.root / p).read_bytes() for p in cls.mod.SOURCE_SHA256}
        cls.truth = cls.mod.strict_json(cls.blobs[cls.mod.CASE + 'truth.json'])
        cls.inputs = cls.mod.strict_json(cls.blobs[cls.mod.CASE + 'inputs/problems.json'])
        cls.config = cls.mod.strict_json(cls.blobs[cls.mod.CASE + 'case.json'])

    def fixtures(self):
        return copy.deepcopy((self.truth, self.inputs, self.config))

    def semantic(self, truth, inputs, config):
        return self.mod.analyze_visibility(truth, inputs, config)

    def reject(self, truth, inputs, config, message):
        with self.assertRaisesRegex(self.mod.VerificationError, message):
            self.semantic(truth, inputs, config)

    def reseal_tests(self, truth, problem='abc387_f'):
        entry = truth['problems'][problem]
        entry['tests_sha256'] = self.mod.sha256(json.dumps(
            entry['tests'], ensure_ascii=False, sort_keys=True).encode('utf-8'))

    def copy_sources(self, root, omit=()):
        for relative, data in self.blobs.items():
            if relative in omit:
                continue
            dest = root / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)

    def test_actual_readonly_derivation_and_limits(self):
        before = {p: hashlib.sha256((self.root / p).read_bytes()).hexdigest()
                  for p in self.mod.SOURCE_SHA256}
        with mock.patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')), \
             mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('process forbidden')):
            result = self.mod.derive(self.root)
        after = {p: hashlib.sha256((self.root / p).read_bytes()).hexdigest()
                 for p in self.mod.SOURCE_SHA256}
        self.assertEqual(before, after)
        self.assertEqual([result[k] for k in ('problem_count', 'canonical_public_samples',
                         'public_audit_source_public', 'public_audit_source_private',
                         'public_audit_total')], [4, 11, 11, 160, 171])
        self.assertEqual([r['public_audit_total'] for r in result['problems']], [43, 43, 42, 43])
        self.assertEqual(result['canonical_private_test_records'], 0)
        self.assertTrue(all(v == 'unknown' for v in result['not_authenticated'].values()))
        self.assertFalse(result['historical_score_or_sample_change'])
        self.assertEqual(len(result['sources']), 6)
        self.assertEqual(result['canonical_input_inventory']['files'],
                         [self.mod.CASE + 'inputs/problems.json'])
        for index, row in enumerate(result['problems']):
            refs = row['source_pointers']
            self.assertEqual(refs['canonical_samples'], '/problems/' + str(index) + '/samples')
            self.assertEqual(len(refs['source_private_indices']), 40)
            self.assertTrue(row['private_bodies_present_in_audit'])

    def test_pure_baseline_without_source_checker(self):
        result = self.semantic(*self.fixtures())
        self.assertEqual(result['public_audit_total'], 171)
        self.assertNotIn('sources', result)

    def test_wrong_case(self):
        truth, inputs, config = self.fixtures()
        inputs['case_id'] = 'different'
        self.reject(truth, inputs, config, 'case identity')

    def test_duplicate_or_reordered_problem(self):
        for mode in ('duplicate', 'reorder'):
            truth, inputs, config = self.fixtures()
            if mode == 'duplicate':
                inputs['problems'][1] = copy.deepcopy(inputs['problems'][0])
            else:
                inputs['problems'].reverse()
            with self.subTest(mode=mode):
                self.reject(truth, inputs, config, 'identity/order')

    def test_wrong_problem_set(self):
        truth, inputs, config = self.fixtures()
        truth['problems']['unexpected'] = truth['problems'].pop('abc389_g')
        self.reject(truth, inputs, config, 'audit problem identities')

    def test_type_confusion_counts(self):
        for key, value in (('n_public', True), ('n_public', 3.0), ('n_private', 40.0)):
            truth, inputs, config = self.fixtures()
            truth['problems']['abc387_f'][key] = value
            with self.subTest(key=key, value=value):
                self.reject(truth, inputs, config, 'invalid audit')

    def test_changed_declared_counts(self):
        truth, inputs, config = self.fixtures()
        inputs['problems'][0]['n_hidden'] = 39
        self.reject(truth, inputs, config, 'canonical hidden count')

    def test_dropped_private_record_even_if_resealed(self):
        truth, inputs, config = self.fixtures()
        truth['problems']['abc387_f']['tests'].pop()
        self.reseal_tests(truth)
        self.reject(truth, inputs, config, 'test denominator')

    def test_relabel_private_as_public_even_if_resealed(self):
        truth, inputs, config = self.fixtures()
        truth['problems']['abc387_f']['tests'][3]['source'] = 'public'
        self.reseal_tests(truth)
        self.reject(truth, inputs, config, 'actual public count')

    def test_unknown_source_label_even_if_resealed(self):
        truth, inputs, config = self.fixtures()
        truth['problems']['abc387_f']['tests'][3]['source'] = 'hidden'
        self.reseal_tests(truth)
        self.reject(truth, inputs, config, 'unknown source label')

    def test_private_body_must_exist_even_if_resealed(self):
        for key, value in (('input', ''), ('output', ' \n'), ('output', None), ('input', 123)):
            truth, inputs, config = self.fixtures()
            truth['problems']['abc387_f']['tests'][3][key] = value
            self.reseal_tests(truth)
            with self.subTest(key=key, value=value):
                self.reject(truth, inputs, config, 'missing test body')

    def test_wrong_test_digest(self):
        truth, inputs, config = self.fixtures()
        truth['problems']['abc387_f']['tests_sha256'] = '0' * 64
        self.reject(truth, inputs, config, 'test-array digest')

    def test_sample_output_mismatch(self):
        truth, inputs, config = self.fixtures()
        inputs['problems'][0]['samples'][0]['output'] = 'not the source sample'
        self.reject(truth, inputs, config, 'samples differ')

    def test_extra_sample_or_source_flag(self):
        for mode in ('extra', 'flag'):
            truth, inputs, config = self.fixtures()
            if mode == 'extra':
                inputs['problems'][0]['samples'].append({'input': '1', 'output': '1'})
            else:
                inputs['problems'][0]['samples'][0]['source'] = 'private'
            with self.subTest(mode=mode):
                self.reject(truth, inputs, config, 'sample denominator|invalid fields')

    def test_extra_private_array_in_canonical_input(self):
        for level in ('root', 'problem'):
            truth, inputs, config = self.fixtures()
            dest = inputs if level == 'root' else inputs['problems'][0]
            dest['tests'] = copy.deepcopy(truth['problems']['abc387_f']['tests'])
            with self.subTest(level=level):
                self.reject(truth, inputs, config, 'canonical input field|canonical problem schema')

    def test_wrong_mapping_or_extra_config(self):
        for mapping in ([['.', 'inputs']], [['inputs', 'inputs'], ['truth.json', 'truth.json']]):
            truth, inputs, config = self.fixtures()
            config['inputs'] = mapping
            with self.subTest(mapping=mapping):
                self.reject(truth, inputs, config, 'configuration changed')

    def test_metadata_mismatch(self):
        truth, inputs, config = self.fixtures()
        inputs['problems'][0]['title'] = 'other case'
        self.reject(truth, inputs, config, 'metadata mismatch')

    def test_strict_json_duplicate_keys_and_nonfinite(self):
        for data in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}',
                     b'{"a":-Infinity}', b'{"a":1e999}', b'{"a":-1e999}', b'\xff'):
            with self.subTest(data=data), self.assertRaises(self.mod.VerificationError):
                self.mod.strict_json(data)

    def test_unsafe_relative_paths(self):
        for relative in ('/absolute', '../truth.json', './truth.json', 'a//b',
                         'a/../b', 'a\\b', ''):
            with self.subTest(relative=relative), self.assertRaises(self.mod.VerificationError):
                self.mod.safe_file(self.root, relative)

    def test_missing_required_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_sources(root, omit=(self.mod.CASE + 'case.json',))
            with self.assertRaisesRegex(self.mod.VerificationError, 'missing source'):
                self.mod.derive(root)

    def test_fixed_pin_rejects_changed_source(self):
        for relative in self.mod.SOURCE_SHA256:
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.copy_sources(root)
                (root / relative).write_bytes(self.blobs[relative] + b'\n')
                with self.assertRaisesRegex(self.mod.VerificationError, 'SHA-256 mismatch'):
                    self.mod.derive(root)

    def test_resealed_truth_digest_does_not_replace_trusted_pin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_sources(root)
            truth = copy.deepcopy(self.truth)
            truth['problems']['abc387_f']['tests'][3]['output'] = 'wrong'
            self.reseal_tests(truth)
            (root / (self.mod.CASE + 'truth.json')).write_text(
                json.dumps(truth, ensure_ascii=False), encoding='utf-8')
            with self.assertRaisesRegex(self.mod.VerificationError, 'SHA-256 mismatch'):
                self.mod.derive(root)

    def test_complete_synthetic_copy_inventory_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_sources(root)
            result = self.mod.derive(root)
            self.assertEqual(result['canonical_input_inventory']['files'],
                             [self.mod.CASE + 'inputs/problems.json'])
            self.assertEqual(result['public_audit_total'], 171)

    def test_extra_canonical_input_file_or_directory_rejected(self):
        for kind in ('file', 'directory'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.copy_sources(root)
                extra = root / (self.mod.CASE + 'inputs/private.json')
                if kind == 'file':
                    extra.write_text('{}', encoding='utf-8')
                else:
                    extra.mkdir()
                with self.assertRaisesRegex(self.mod.VerificationError, 'inputs inventory'):
                    self.mod.derive(root)

    def test_extra_canonical_input_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_sources(root)
            expected = root / (self.mod.CASE + 'inputs/problems.json')
            (expected.parent / 'same-byte-link.json').symlink_to(expected)
            with self.assertRaisesRegex(self.mod.VerificationError, 'inputs inventory'):
                self.mod.derive(root)

    def test_same_byte_canonical_file_symlink_inside_root_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            relative = self.mod.CASE + 'inputs/problems.json'
            self.copy_sources(root, omit=(relative,))
            same_bytes = root / 'same-bytes.json'
            same_bytes.write_bytes(self.blobs[relative])
            expected = root / relative
            expected.parent.mkdir(parents=True, exist_ok=True)
            expected.symlink_to(same_bytes)
            with self.assertRaisesRegex(self.mod.VerificationError, 'symlink'):
                self.mod.derive(root)

    def test_symlink_source_and_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            outside = base / 'outside'
            outside.mkdir()
            (outside / 'file').write_text('test', encoding='utf-8')
            root = base / 'root'
            root.mkdir()
            (root / 'file-link').symlink_to(outside / 'file')
            (root / 'dir-link').symlink_to(outside, target_is_directory=True)
            for relative in ('file-link', 'dir-link/file'):
                with self.subTest(relative=relative), self.assertRaisesRegex(
                        self.mod.VerificationError, 'symlink'):
                    self.mod.safe_file(root, relative)

    def test_symlink_root(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            actual = base / 'actual'
            actual.mkdir()
            alias = base / 'alias'
            alias.symlink_to(actual, target_is_directory=True)
            with self.assertRaisesRegex(self.mod.VerificationError, 'symlink root'):
                self.mod.safe_file(alias, 'file')


if __name__ == '__main__':
    unittest.main()
