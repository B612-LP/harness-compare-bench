#!/usr/bin/env python3
"""Counterexamples and fail-closed public witness tests. No product runs."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('identity_verify', HERE / 'verify.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def events():
    message = {'role': 'user', 'content': [{'type': 'text', 'text': 'alpha'}], 'id': 'stable-id'}
    data = [
        ('agent/inbox/spliced', {'start': 0, 'target': 'main', 'inserted': [copy.deepcopy(message)]}),
        ('system/message', {'turn': 0, 'step': 0, 'message': dict(message, role='system')}),
        ('user/message', copy.deepcopy(message)),
        ('request/header', {'header': {'tools': [], 'config': {'model': 'm'}}, 'reason': 'initial'}),
        ('request/context', {'model': 'm', 'provider': 'p', 'contextWindow': 1000, 'systemPromptUpdate': 's'}),
    ]
    return [{'seq': i, 'time': 100000, 'type': t, 'data': d} for i, (t, d) in enumerate(data)]


class ProjectionTests(unittest.TestCase):
    def pair(self, a, b):
        at, al = v.project(a); bt, bl = v.project(b)
        return v.pair_record('a', 'b', at, bt, al, bl)

    def test_exact_identity(self):
        e = events()
        self.assertEqual(self.pair(e, copy.deepcopy(e))['equal'], dict.fromkeys(v.LAYERS, True))

    def test_same_length_text_mutation_is_not_identity(self):
        a = events(); b = copy.deepcopy(a)
        b[2]['data']['content'][0]['text'] = 'omega'
        self.assertEqual(sum(len(v.canon(x)) for x in a), sum(len(v.canon(x)) for x in b))
        self.assertEqual(self.pair(a, b)['equal'], dict.fromkeys(v.LAYERS, False))

    def test_event_lengths_can_cancel(self):
        a = events(); b = copy.deepcopy(a)
        b[0]['data']['inserted'][0]['content'][0]['text'] += 'z'
        b[2]['data']['content'][0]['text'] = 'alph'
        self.assertEqual(sum(len(v.canon(x)) for x in a), sum(len(v.canon(x)) for x in b))
        self.assertNotEqual([len(v.canon(x)) for x in a], [len(v.canon(x)) for x in b])
        self.assertFalse(self.pair(a, b)['equal']['L0'])

    def test_same_type_reordering_is_not_identity(self):
        a = events(); a.insert(3, copy.deepcopy(a[2])); a[3]['data']['content'][0]['text'] = 'omega'
        b = copy.deepcopy(a); b[2], b[3] = b[3], b[2]
        self.assertTrue(self.pair(a, b)['aligned'])
        self.assertFalse(self.pair(a, b)['equal']['L2'])

    def test_reordering_types_stops_alignment(self):
        a = events(); b = copy.deepcopy(a); b[0], b[1] = b[1], b[0]
        p = self.pair(a, b)
        self.assertFalse(p['aligned'])
        self.assertTrue(all(not d for d in p['path_differences'].values()))

    def test_envelope_only_change(self):
        a = events(); b = copy.deepcopy(a); b[0]['time'] += 1
        self.assertEqual(self.pair(a, b)['equal'], {'L0': False, 'L1': True, 'L2': True})

    def test_id_only_change(self):
        a = events(); b = copy.deepcopy(a); b[2]['data']['id'] = 'other--id'
        self.assertEqual(self.pair(a, b)['equal'], {'L0': False, 'L1': False, 'L2': True})

    def test_header_fields_not_dropped(self):
        a = events(); b = copy.deepcopy(a); b[3]['data']['reason'] = 'changed'
        self.assertFalse(self.pair(a, b)['equal']['L2'])

    def test_context_fields_not_dropped(self):
        a = events(); b = copy.deepcopy(a); b[4]['data']['provider'] = 'other'
        self.assertFalse(self.pair(a, b)['equal']['L2'])

    def test_missing_data_rejected(self):
        e = events(); del e[0]['data']
        with self.assertRaises(v.Invalid): v.project(e)

    def test_bad_data_rejected(self):
        e = events(); e[0]['data'] = []
        with self.assertRaises(v.Invalid): v.project(e)

    def test_missing_content_rejected(self):
        e = events(); del e[2]['data']['content']
        with self.assertRaises(v.Invalid): v.project(e)

    def test_bad_inserted_rejected(self):
        e = events(); e[0]['data']['inserted'] = 'not a list'
        with self.assertRaises(v.Invalid): v.project(e)

    def test_optional_removed_count_preserved(self):
        e = events(); e[0]['data']['removedCount'] = 3
        self.assertEqual(v.project(e)[1]['L2'][0]['removedCount'], 3)

    def test_boolean_and_number_are_not_equal(self):
        self.assertTrue(v.differences(True, 1))

    def test_dynamic_keys_hashed_without_values(self):
        d = v.differences({'private-sample-key': 'left-secret'}, {'private-sample-key': 'right-secret'})
        encoded = json.dumps(d)
        self.assertNotIn('private-sample-key', encoded)
        self.assertNotIn('left-secret', encoded)
        self.assertNotIn('right-secret', encoded)
        self.assertTrue(d[0]['path'].startswith('/@sha256-'))

    def test_deleted_leaf_registered(self):
        d = v.differences({'text': 'x'}, {})
        self.assertEqual(d[0]['right']['type'], 'missing')

    def test_list_growth_registered(self):
        self.assertEqual(v.differences([], [1])[0]['path'], '/0')

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(v.Invalid): v.load_json('{"a":1,"a":2}')

    def test_nonfinite_json_rejected(self):
        with self.assertRaises(v.Invalid): v.load_json('{"a":NaN}')

    def test_unsafe_source_path_rejected(self):
        with self.assertRaises(v.Invalid): v.safe_path(ROOT, '../outside')
        with self.assertRaises(v.Invalid): v.safe_path(ROOT, '/etc/passwd')

    def test_fingerprint_framing(self):
        fp = v.fingerprint([{'x': '中'}, {'x': 2}])
        v.validate_fp(fp, 2)
        fp['stream_bytes'] += 1
        with self.assertRaises(v.Invalid): v.validate_fp(fp, 2)


class PublicWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v11, cls.v2 = v.source_objects(ROOT)
        cls.evidence = v.load_json((HERE / 'evidence.json').read_bytes())

    def check_invalid(self, change):
        e = copy.deepcopy(self.evidence); change(e)
        with self.assertRaises(v.Invalid): v.analyze(e, self.v11, self.v2)

    def test_full_public_replay(self):
        result = v.analyze(self.evidence, self.v11, self.v2)
        self.assertEqual(result['primary'], {'old_v2_pass_groups': 4, 'L0_identical_groups': 0})
        self.assertEqual(result['coverage'], {'slots': 15, 'groups': 5, 'pairs': 15, 'aligned_pairs': 13})

    def test_result_reproducible(self):
        actual = v.analyze(self.evidence, self.v11, self.v2)
        self.assertEqual(actual, v.load_json((HERE / 'result.json').read_bytes()))

    def test_missing_slot(self):
        self.check_invalid(lambda e: e['slots'].pop())

    def test_duplicate_slot(self):
        self.check_invalid(lambda e: e['slots'].__setitem__(1, e['slots'][0]))

    def test_missing_pair(self):
        self.check_invalid(lambda e: e['pairs'].pop())

    def test_changed_identity(self):
        self.check_invalid(lambda e: e['slots'][0]['identity'].__setitem__('sha256', '0' * 64))

    def test_identifier_value_not_republished(self):
        self.assertTrue(all('id' not in s['identity'] for s in self.evidence['slots']))

    def test_pair_equality_tamper(self):
        self.check_invalid(lambda e: e['pairs'][0]['equal'].__setitem__('L0', True))

    def test_event_hash_tamper(self):
        self.check_invalid(lambda e: e['slots'][0]['layers']['L2']['event_sha256'].__setitem__(0, '0' * 64))

    def test_old_length_tamper(self):
        self.check_invalid(lambda e: e['slots'][0]['layers']['L0']['event_bytes'].__setitem__(0, 999))

    def test_diagnostic_drop(self):
        self.check_invalid(lambda e: e['pairs'][0]['path_differences']['L0'].pop())

    def test_unsafe_path_injection(self):
        def change(e): e['pairs'][0]['path_differences']['L0'][0]['differences'][0]['path'] = '/raw-secret-key'
        self.check_invalid(change)

    def test_no_forced_nonaligned_diagnostics(self):
        def change(e):
            p = next(p for p in e['pairs'] if not p['aligned'])
            p['path_differences']['L0'] = [{'i': 0}]
        self.check_invalid(change)

    def test_bad_source_pin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in v.BINDINGS:
                target = root / relative; target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / relative).read_bytes())
            target.write_bytes(target.read_bytes() + b' ')
            with self.assertRaises(v.Invalid): v.source_objects(root)

    def test_exclusive_output_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'output.json'
            v.write_new(path, {'x': 1})
            with self.assertRaises(FileExistsError): v.write_new(path, {'x': 2})
            self.assertEqual(v.load_json(path.read_bytes()), {'x': 1})


if __name__ == '__main__':
    unittest.main()
