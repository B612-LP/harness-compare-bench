#!/usr/bin/env python3
"""Software counterexamples, not additional product/model observations."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('char_boundary_verify', HERE / 'verify.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def framed(head='abc', tail='xyz', n='4', total=True, warning=True):
    return (('Warning: truncated output (original token count: 99)\n' if warning else '') +
            ('Total output lines: 3\n\n' if total else '') + head + '…' + str(n) + ' chars truncated…' + tail)


class Grammar(unittest.TestCase):
    def test_exact(self):
        self.assertEqual(v.classify('文本😀\n', '文本😀\n')['kind'], 'EXACT')

    def test_empty_exact(self):
        self.assertEqual(v.classify('', '')['kind'], 'EXACT')

    def test_boundary(self):
        r = v.classify(framed(), 'abc1234xyz')
        self.assertEqual(r['kind'], v.KINDS[1])
        self.assertEqual(r['witness']['deleted'], v.describe('1234'))

    def test_optional_total(self):
        self.assertEqual(v.classify(framed(total=False), 'abc1234xyz')['kind'], v.KINDS[1])

    def test_header_unknown(self):
        self.assertEqual(v.classify(None, 'abc')['reason'], 'HEADER-UNKNOWN')

    def test_warning_required(self):
        self.assertEqual(v.classify(framed(warning=False), 'abc1234xyz')['reason'], 'WARNING-MISMATCH')

    def test_ascii_marker_unknown(self):
        self.assertEqual(v.classify(framed().replace('…', '...'), 'abc1234xyz')['reason'], 'NO-MARKER')

    def test_token_marker_unknown(self):
        self.assertEqual(v.classify(framed().replace('chars truncated', 'tokens truncated'), 'abc1234xyz')['reason'], 'NO-MARKER')

    def test_multiple_marker_unknown(self):
        self.assertEqual(v.classify(framed(head='abc…1 chars truncated…'), 'abc1234xyz')['reason'], 'MULTIPLE-MARKERS')

    def test_empty_head_unknown(self):
        self.assertEqual(v.classify(framed(head=''), '1234xyz')['reason'], 'EMPTY-RETAIN')

    def test_empty_tail_unknown(self):
        self.assertEqual(v.classify(framed(tail=''), 'abc1234')['reason'], 'EMPTY-RETAIN')

    def test_wrong_prefix(self):
        self.assertEqual(v.classify(framed(head='abd'), 'abc1234xyz')['reason'], 'BOUNDARY-MISMATCH')

    def test_wrong_suffix(self):
        self.assertEqual(v.classify(framed(tail='xyq'), 'abc1234xyz')['reason'], 'BOUNDARY-MISMATCH')

    def test_no_deletion(self):
        self.assertEqual(v.classify(framed(n='0'), 'abcxyz')['reason'], 'OVERLAP-OR-NO-DELETION')

    def test_overlap(self):
        self.assertEqual(v.classify(framed(head='ab', tail='bc'), 'abc')['reason'], 'OVERLAP-OR-NO-DELETION')

    def test_preserve_whitespace(self):
        self.assertEqual(v.classify(framed(head=' abc'), 'abc1234xyz')['reason'], 'BOUNDARY-MISMATCH')

    def test_crlf_not_normalized(self):
        self.assertEqual(v.classify(framed().replace('\n', '\r\n'), 'abc1234xyz')['reason'], 'WARNING-MISMATCH')

    def test_bad_total_not_silently_removed(self):
        self.assertEqual(v.classify(framed().replace('lines: 3', 'lines: three'), 'abc1234xyz')['reason'], 'BOUNDARY-MISMATCH')

    def test_equal_length_wrong_text_not_exact(self):
        self.assertEqual(v.classify('abc', 'abd')['kind'], 'UNEXPLAINED')

    def test_wrong_N_is_label_not_truth(self):
        r = v.classify(framed(n='999'), 'abc1234xyz')
        self.assertEqual(r['kind'], v.KINDS[1])
        self.assertFalse(any(r['witness']['unit_matches'].values()))

    def test_leading_zero_label_preserved(self):
        r = v.classify(framed(n='0004'), 'abc1234xyz')
        self.assertEqual(r['witness']['marker_digit_count'], 4)
        self.assertEqual(r['witness']['marker_declared_N'], 4)

    def test_all_unit_discrimination(self):
        r = v.classify(framed(n='2'), 'abc中😀xyz')
        self.assertEqual(r['witness']['deleted'], v.describe('中😀'))
        self.assertEqual(r['witness']['unit_matches'], {'bytes': False, 'codepoints': True, 'utf16_units': False})
        self.assertEqual(r['witness']['source_intervals']['utf16_units']['deleted'], [3, 6])

    def test_bad_input_type(self):
        with self.assertRaises(ValueError):
            v.classify({}, 'abc')

    def test_unknown_terms_are_not_zero(self):
        self.assertIsNone(v.record_terms({'kind': 'UNEXPLAINED'}))

    def test_unit_descriptor(self):
        d = v.describe('中😀')
        self.assertEqual((d['bytes'], d['codepoints'], d['utf16_units']), (7, 2, 3))
        v.check_desc(d)

    def test_json_duplicate_and_nonfinite(self):
        for raw in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', '{"x":1e999}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                v.loads(raw)

    def test_empty_descriptor_cannot_fake_hash(self):
        d = v.describe(''); d['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            v.check_desc(d)

    def test_bool_is_not_integer(self):
        with self.assertRaises(ValueError):
            v.integer(True)

    def test_escape_and_symlink(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as outside:
            root = Path(d)
            for path in ('../elsewhere', '/tmp/elsewhere'):
                with self.assertRaises(ValueError):
                    v.safe_path(root, path)
            (root / 'link').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                v.safe_path(root, 'link/x')

    def test_exclusive_write(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'out'
            v.exclusive(path, b'first')
            with self.assertRaises(FileExistsError):
                v.exclusive(path, b'second')
            self.assertEqual(path.read_bytes(), b'first')


class PublicEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cls.previous, cls.prior_result, cls.bindings, _ = v.sources(v.ROOT)
        cls.raw = (HERE / 'evidence.json').read_bytes()
        cls.evidence = v.loads(cls.raw)
        cls.marked_index = next(i for i, r in enumerate(cls.evidence['records']) if r['kind'] == v.KINDS[1])

    def validate(self, evidence):
        v.validate(evidence, self.previous, self.bindings)

    def test_published_replay(self):
        self.validate(self.evidence)
        result = v.result_for(self.evidence, self.previous, self.prior_result, v.sha(self.raw))
        self.assertEqual(v.document(result), (HERE / 'result.json').read_bytes())

    def test_primary_and_old_classifications(self):
        counts = {kind: sum(r['prior_kind'] == kind for r in self.evidence['records']) for kind in ('EXACT', 'MARKED-BOUNDARY-CROP-WITNESS', 'UNEXPLAINED')}
        self.assertEqual(counts, {'EXACT': 93, 'MARKED-BOUNDARY-CROP-WITNESS': 0, 'UNEXPLAINED': 19})
        result = v.result_for(self.evidence, self.previous, self.prior_result, v.sha(self.raw))
        self.assertEqual(result['primary'], {'prior_unexplained': 19, 'new_boundary_witnesses_in_prior_unexplained': 19})
        self.assertEqual(result['primary_comparison']['new_terms_delta_bytes'], {'F': 208, 'D': -32809})

    def test_opaque_prefix_digest_is_not_authentication(self):
        e = copy.deepcopy(self.evidence)
        e['records'][self.marked_index]['witness']['prefix']['sha256'] = '0' * 64
        self.validate(e)  # Explicit capability limit: no plaintext in public projection.
        self.assertNotEqual(v.sha(v.document(e)), v.EVIDENCE_SHA)  # Sealed CLI still rejects it.

    def test_cli_result_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / 'result.json'
            cmd = [sys.executable, '-I', '-S', '-B'] + (['-O'] if sys.flags.optimize else []) + [str(HERE / 'verify.py'), '--output', str(dest)]
            first = subprocess.run(cmd, capture_output=True, timeout=20)
            self.assertEqual(first.returncode, 0, first.stderr.decode())
            self.assertEqual(dest.read_bytes(), (HERE / 'result.json').read_bytes())
            second = subprocess.run(cmd, capture_output=True, timeout=20)
            self.assertEqual(second.returncode, 2)
            self.assertEqual(dest.read_bytes(), (HERE / 'result.json').read_bytes())

    def test_cli_tamper_seal(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'bad.json'
            e = copy.deepcopy(self.evidence); e['records'].pop()
            path.write_bytes(v.document(e))
            run = subprocess.run([sys.executable, '-I', '-S', '-B', str(HERE / 'verify.py'), '--evidence', str(path)], capture_output=True, timeout=20)
            self.assertEqual(run.returncode, 2)


def evidence_mutation_test(name, mutate):
    def check(self):
        evidence = copy.deepcopy(self.evidence)
        mutate(evidence, self.marked_index)
        with self.assertRaises((ValueError, KeyError, TypeError)):
            self.validate(evidence)
    check.__name__ = 'test_reject_' + name
    return check


MUTATIONS = (
    ('missing_record', lambda e, i: e['records'].pop()),
    ('duplicate_record', lambda e, i: e['records'].__setitem__(1, copy.deepcopy(e['records'][0]))),
    ('reordered_records', lambda e, i: e['records'].reverse()),
    ('wrong_schema', lambda e, i: e.__setitem__('schema', 'other')),
    ('wrong_protocol', lambda e, i: e.__setitem__('protocol_sha256', '0' * 64)),
    ('wrong_source_pin', lambda e, i: e['public_sources'].__setitem__('extra', '0' * 64)),
    ('source_path', lambda e, i: e['records'][0]['source'].__setitem__('archive_relative_path', '../x')),
    ('source_line', lambda e, i: e['records'][0]['lines'].__setitem__('output', 0)),
    ('record_commitment', lambda e, i: e['records'][0].__setitem__('prior_record_sha256', '0' * 64)),
    ('old_classification', lambda e, i: e['records'][i].__setitem__('prior_kind', 'EXACT')),
    ('bool_occurrence', lambda e, i: e['records'][0].__setitem__('occurrence', True)),
    ('impossible_utf16', lambda e, i: e['records'][i]['utf16_units'].__setitem__('A', 0)),
    ('wrong_marker', lambda e, i: e['records'][i]['witness']['marker'].__setitem__('sha256', '0' * 64)),
    ('wrong_N', lambda e, i: e['records'][i]['witness'].__setitem__('marker_declared_N', 99999999)),
    ('wrong_units', lambda e, i: e['records'][i]['witness']['unit_matches'].__setitem__('bytes', 1)),
    ('bool_interval', lambda e, i: e['records'][i]['witness']['source_intervals']['bytes']['head'].__setitem__(0, False)),
    ('wrong_interval', lambda e, i: e['records'][i]['witness']['source_intervals']['bytes']['deleted'].__setitem__(0, 0)),
    ('deleted_length', lambda e, i: e['records'][i]['witness']['deleted'].__setitem__('bytes', 1)),
    ('impossible_descriptor', lambda e, i: e['records'][i]['witness']['prefix'].__setitem__('utf16_units', 999999999)),
    ('fake_exact', lambda e, i: e['records'][i].__setitem__('kind', 'EXACT')),
    ('unknown_with_witness', lambda e, i: e['records'][i].__setitem__('kind', 'UNEXPLAINED')),
    ('extra_raw_field', lambda e, i: e['records'][i]['witness'].__setitem__('raw', 'not allowed')),
)
for name, mutate in MUTATIONS:
    setattr(PublicEvidence, 'test_reject_' + name, evidence_mutation_test(name, mutate))


if __name__ == '__main__':
    unittest.main(verbosity=2)
