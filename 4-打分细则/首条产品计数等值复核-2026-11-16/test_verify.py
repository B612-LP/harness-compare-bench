#!/usr/bin/env python3
"""Adversarial offline tests; fixture identities are synthetic, never archived IDs.
USAGE_TEST_ROOT selects an explicitly supplied repository only for tests staged
outside the public package. Installed tests default to this file's parents[2].
"""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get('USAGE_TEST_ROOT', str(Path(__file__).resolve().parents[2])))
spec = importlib.util.spec_from_file_location('usage_verify_test_target', HERE / 'verify.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def good():
    return dict(zip(v.FIELDS, (10, 4, 0, 3, 1, 13)))


def native_events():
    records = []
    total = dict.fromkeys(v.FIELDS, 0)
    for index in (1, 2):
        one = good()
        total = v.plus(total, one)
        records.append({'type': 'token_usage_record', 'payload': {'usage': one, 'turn_token_usage': dict(total), 'thread_token_usage': dict(total), 'response_id': 'fixture-response-' + str(index), 'turn_id': 'fixture-turn', 'thread_id': 'fixture-thread', 'root_turn_id': 'fixture-root'}})
        records.append({'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {'last_token_usage': dict(one), 'total_token_usage': dict(total), 'model_context_window': 100}}})
    records.append({'type': 'event_msg', 'payload': {'type': 'task_complete', 'turn_id': 'fixture-turn', 'root_turn_id': 'fixture-root'}})
    return records


def native(value):
    return v.analyze_native(value, v.projection(value))


def mapped(value, identity='fixture-response-1'):
    return dict({v.PUBLIC_MAP[field]: value[field] for field in v.FIELDS}, response_id=identity)


def meta_fixture():
    terminal = v.plus(good(), good())
    rows = [mapped(good(), 'fixture-response-1'), mapped(good(), 'fixture-response-2')]
    result = {v.PUBLIC_MAP[field]: terminal[field] for field in v.FIELDS}
    result.update(requests=2, per_call=rows, cumulative_thread_final=terminal)
    return result


class Common(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=str(HERE), prefix='.test-usage-')
        self.directory = Path(self.tmp.name).resolve()
        self.assertEqual(self.directory.parent, HERE.resolve())

    def tearDown(self):
        self.assertEqual(Path(self.tmp.name).resolve().parent, HERE.resolve())
        self.tmp.cleanup()

    def rejected(self, function, *args):
        with self.assertRaises(v.Invalid):
            function(*args)


class VectorTests(Common):
    def test_explicit_zero_is_preserved(self):
        self.assertEqual(v.vector(good())['cache_write_input_tokens'], 0)

    def test_all_six_explicit_zeros_valid(self):
        self.assertEqual(v.vector(dict.fromkeys(v.FIELDS, 0)), dict.fromkeys(v.FIELDS, 0))

    def test_public_mapping(self):
        self.assertEqual(v.public_vector(mapped(good())), good())

    def test_missing_public_field(self):
        value = mapped(good()); del value['cache_creation_tokens']
        self.rejected(v.public_vector, value)

    def test_null_public_field(self):
        value = mapped(good()); value['cache_creation_tokens'] = None
        self.rejected(v.public_vector, value)


def add_vector_test(name, mutate):
    def test(self):
        value = good(); mutate(value)
        self.rejected(v.vector, value)
    setattr(VectorTests, 'test_' + name, test)


for name, mutate in (
    ('missing_field', lambda x: x.pop('cache_write_input_tokens')),
    ('extra_field', lambda x: x.update(extra=0)),
    ('null', lambda x: x.update(cache_write_input_tokens=None)),
    ('bool', lambda x: x.update(cache_write_input_tokens=False)),
    ('float', lambda x: x.update(cache_write_input_tokens=0.0)),
    ('negative', lambda x: x.update(cache_write_input_tokens=-1)),
    ('total_conflict', lambda x: x.update(total_tokens=14)),
    ('cache_subset', lambda x: x.update(cached_input_tokens=11)),
    ('reasoning_subset', lambda x: x.update(reasoning_output_tokens=4)),
):
    add_vector_test(name, mutate)


class JsonPathTests(Common):
    def test_json_finite(self):
        self.assertEqual(v.loads('{"a":1.2}'), {'a': 1.2})

    def test_new_output(self):
        path = self.directory / 'new.json'
        v.output_path(path); v.exclusive(path, b'{}')
        self.assertEqual(path.read_bytes(), b'{}')

    def test_output_existing(self):
        path = self.directory / 'old.json'; path.write_bytes(b'unchanged')
        self.rejected(v.output_path, path)
        self.assertEqual(path.read_bytes(), b'unchanged')

    def test_output_parent_missing(self):
        self.rejected(v.output_path, self.directory / 'missing' / 'out.json')

    def test_output_dotdot(self):
        self.rejected(v.output_path, self.directory / '..' / 'new.json')

    def test_relative_input(self):
        self.assertEqual(v.safe_path(self.directory, 'a.json'), self.directory / 'a.json')

    def test_input_absolute(self):
        self.rejected(v.safe_path, self.directory, str(self.directory / 'a.json'))

    def test_input_dotdot(self):
        self.rejected(v.safe_path, self.directory, '../a.json')

    def test_input_root_itself(self):
        self.rejected(v.safe_path, self.directory, '.')

    def test_symlink_escape(self):
        path = self.directory / 'outside'; path.symlink_to(HERE, target_is_directory=True)
        self.rejected(v.safe_path, self.directory, 'outside/README.md')

    def test_output_symlink(self):
        path = self.directory / 'linked.json'; path.symlink_to(self.directory / 'not-created')
        self.rejected(v.output_path, path)

    def test_wrong_pin(self):
        path = self.directory / 'fixture.json'; path.write_bytes(b'{}')
        self.rejected(v.pinned, path, '0' * 64)

    def test_jsonl_blank_record(self):
        self.rejected(v.trace, b'{"type":"x"}\n\n')

    def test_jsonl_separator_inside_string(self):
        events = v.trace('{"type":"x","value":"a\u2028b"}\n'.encode())
        self.assertEqual(len(events), 1)

    def test_nested_origin_paths_no_values(self):
        value = {'nested': [{'provider': 'fixture-secret-value', 'estimated': False}], 'origin': None}
        self.assertEqual(v.origin_paths(value), ['/nested/*/provider', '/nested/*/estimated', '/origin'])
        self.assertNotIn('fixture-secret-value', json.dumps(v.schema_paths(value)))


for index, raw in enumerate(('{"a":1,"a":2}', '{"a":{"b":1,"b":2}}', 'NaN', 'Infinity', '-Infinity', '1e9999', '{bad}', '{"type":"x","type":"y"}')):
    def test(self, value=raw):
        self.rejected(v.loads, value)
    setattr(JsonPathTests, 'test_invalid_json_' + str(index + 1), test)


class NativeTests(Common):
    def test_valid_prefixes_and_mirrors(self):
        result, ids = native(native_events())
        self.assertEqual(result['terminal_cumulative'], v.plus(good(), good()))
        self.assertEqual(len(ids), 2)
        self.assertEqual(result['coverage']['uncovered_response_items'], 0)

    def test_projection_independent_gate(self):
        events = native_events(); projected = v.projection(events)
        projected[0][1] += 1
        self.rejected(v.analyze_native, events, projected)

    def test_complete_provenance_schema_scan(self):
        events = native_events()
        events[0]['source'] = {'provider': 'fixture-value', 'estimated': True}
        result, _ = native(events)
        self.assertEqual(result['provenance_field_paths']['/native_event/source/provider'], 1)
        self.assertNotIn('fixture-value', json.dumps(result))


def add_native_test(name, mutate):
    def test(self):
        value = native_events(); mutate(value)
        self.rejected(native, value)
    setattr(NativeTests, 'test_' + name, test)


for name, mutate in (
    ('duplicate_response', lambda x: x[2]['payload'].update(response_id='fixture-response-1')),
    ('missing_response', lambda x: x[0]['payload'].pop('response_id')),
    ('empty_response', lambda x: x[0]['payload'].update(response_id='')),
    ('different_thread', lambda x: x[2]['payload'].update(thread_id='fixture-other')),
    ('different_turn', lambda x: x[2]['payload'].update(turn_id='fixture-other')),
    ('different_root', lambda x: x[2]['payload'].update(root_turn_id='fixture-other')),
    ('reset', lambda x: x[2]['payload'].update(turn_token_usage=good())),
    ('thread_conflict', lambda x: x[2]['payload'].update(thread_token_usage=good())),
    ('missing_mirror', lambda x: x.pop(1)),
    ('duplicate_mirror', lambda x: x.insert(2, copy.deepcopy(x[1]))),
    ('mirror_before_usage', lambda x: x.insert(0, x.pop(1))),
    ('mirror_last_differs', lambda x: x[1]['payload']['info'].update(last_token_usage=v.plus(good(), good()))),
    ('mirror_total_differs', lambda x: x[3]['payload']['info'].update(total_token_usage=good())),
    ('context_bool', lambda x: x[1]['payload']['info'].update(model_context_window=True)),
    ('tail_response_uncovered', lambda x: x.append({'type': 'response_item', 'payload': {'type': 'message'}})),
    ('no_completion', lambda x: x.pop()),
    ('duplicate_completion', lambda x: x.append(copy.deepcopy(x[-1]))),
    ('completion_wrong_turn', lambda x: x[-1]['payload'].update(turn_id='fixture-other')),
    ('completion_wrong_root', lambda x: x[-1]['payload'].update(root_turn_id='fixture-other')),
    ('completion_before_final_mirror', lambda x: x.insert(3, x.pop())),
):
    add_native_test(name, mutate)


class CliMetaEndpointTests(Common):
    def test_cli_total_not_provided(self):
        terminal = v.plus(good(), good())
        value = {f: terminal[f] for f in v.FIELDS if f != 'total_tokens'}
        result = v.analyze_cli([{'type': 'turn.completed', 'usage': value}], terminal)
        self.assertEqual(result['total_tokens'], {'availability': 'NOT_PROVIDED', 'value': None})

    def test_meta_full_scope_valid(self):
        value = meta_fixture()
        result, prefix = v.analyze_meta(value, [good(), good()], ['fixture-response-1', 'fixture-response-2'], v.plus(good(), good()))
        self.assertEqual(result['extra_prefix_count'], 0)
        self.assertEqual(prefix, ([], []))

    def test_equal_endpoint(self):
        self.assertEqual(v.endpoint([4, 4, 4], True)['status'], 'EQUAL')

    def test_unequal_endpoint(self):
        self.assertEqual(v.endpoint([4, 5, 5], True)['status'], 'NOT_EQUAL')

    def test_unknown_not_unequal_zero(self):
        self.assertEqual(v.endpoint([4, 5, 5], False), {'status': 'UNKNOWN', 'values': None, 'equal': None})

    def test_endpoint_bool_value(self):
        self.rejected(v.endpoint, [True, 1, 1], True)

    def test_endpoint_nonbool_eligibility(self):
        self.rejected(v.endpoint, [1, 1, 1], None)

    def test_endpoint_missing_rep(self):
        self.rejected(v.endpoint, [1, 1], True)

    def test_meta_own_suffix_not_first_row(self):
        own = [good()]
        prefix = dict(zip(v.FIELDS, (20, 8, 0, 6, 2, 26)))
        aggregate = v.plus(prefix, good())
        value = {v.PUBLIC_MAP[f]: aggregate[f] for f in v.FIELDS}
        value.update(requests=2, per_call=[mapped(prefix, 'fixture-other'), mapped(good())], cumulative_thread_final=good())
        result, extra = v.analyze_meta(value, own, ['fixture-response-1'], good())
        self.assertEqual(result['extra_prefix_count'], 1)
        self.assertEqual(extra[0], [prefix])
        self.assertNotEqual(result['reported_aggregate'], good())


def add_cli_test(name, mutate):
    def test(self):
        terminal = v.plus(good(), good())
        events = [{'type': 'turn.completed', 'usage': {f: terminal[f] for f in v.FIELDS if f != 'total_tokens'}}]
        mutate(events)
        self.rejected(v.analyze_cli, events, terminal)
    setattr(CliMetaEndpointTests, 'test_cli_' + name, test)


for name, mutate in (
    ('tail_event', lambda x: x.append({'type': 'item.completed'})),
    ('duplicate_completion', lambda x: x.append(copy.deepcopy(x[0]))),
    ('extra_total', lambda x: x[0]['usage'].update(total_tokens=26)),
    ('bool', lambda x: x[0]['usage'].update(cache_write_input_tokens=False)),
    ('null', lambda x: x[0]['usage'].update(cache_write_input_tokens=None)),
    ('missing', lambda x: x[0]['usage'].pop('cache_write_input_tokens')),
    ('different_value', lambda x: x[0]['usage'].update(cached_input_tokens=1)),
):
    add_cli_test(name, mutate)


def add_meta_test(name, mutate):
    def test(self):
        value = meta_fixture(); mutate(value)
        self.rejected(v.analyze_meta, value, [good(), good()], ['fixture-response-1', 'fixture-response-2'], v.plus(good(), good()))
    setattr(CliMetaEndpointTests, 'test_meta_' + name, test)


for name, mutate in (
    ('wrong_identity', lambda x: x['per_call'][0].update(response_id='fixture-other')),
    ('missing_identity', lambda x: x['per_call'][0].pop('response_id')),
    ('missing_numeric', lambda x: x['per_call'][0].pop('cache_creation_tokens')),
    ('null_numeric', lambda x: x['per_call'][0].update(cache_creation_tokens=None)),
    ('bool_numeric', lambda x: x['per_call'][0].update(cache_creation_tokens=False)),
    ('requests_bool', lambda x: x.update(requests=True)),
    ('requests_count', lambda x: x.update(requests=3)),
    ('aggregate_differs', lambda x: x.update(cache_read_tokens=1)),
    ('terminal_differs', lambda x: x.update(cumulative_thread_final=good())),
):
    add_meta_test(name, mutate)


class EvidenceTests(Common):
    @classmethod
    def setUpClass(cls):
        cls.sources, cls.selected, cls.dependencies = v.references(ROOT)
        cls.evidence = v.loads((HERE / 'evidence.json').read_bytes())

    def test_sealed_evidence_public_arithmetic(self):
        self.assertEqual(v.sha((HERE / 'evidence.json').read_bytes()), v.EVIDENCE_SHA256)
        v.validate_evidence(self.evidence, self.sources, self.selected)

    def test_unknown_group_not_in_denominator(self):
        value = copy.deepcopy(self.evidence)
        value['slots'][0]['native']['coverage']['critical_gates_valid'] = False
        result = v.result_for(value, v.EVIDENCE_SHA256)
        self.assertEqual(result['endpoints']['first_cached']['unknown_groups'], 1)
        self.assertEqual(result['endpoints']['first_cached']['eligible_groups'], 4)
        self.assertEqual(result['endpoints']['first_cached']['not_equal_groups'], 4)

    def test_public_vs_raw_capability_boundary(self):
        self.assertIn('neither authenticates historical originals', ' '.join(v.result_for(self.evidence, v.EVIDENCE_SHA256)['limits']))

    def test_fixed_baseline_not_dynamic_head(self):
        self.assertEqual(self.evidence['baseline_commit'], '50c073c084006c0bfd5f8b79db3bc495e842847b')
        self.assertEqual(v.DEFAULT_ROOT, Path(v.__file__).resolve().parents[2])

    def test_schema_privacy_no_unlisted_keys(self):
        value = copy.deepcopy(self.evidence)
        value['slots'][0]['raw_content'] = 'fixture-secret-value'
        self.rejected(v.validate_evidence, value, self.sources, self.selected)

    def test_cli_public_replay_normal_and_optimized(self):
        outputs = []
        for index, mode in enumerate(([], ['-O'])):
            output = self.directory / ('result-' + str(index) + '.json')
            command = [sys.executable, '-B'] + mode + [str(HERE / 'verify.py'), '--root', str(ROOT), '--output', str(output)]
            run = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(run.returncode, 0, run.stderr.decode())
            summary = json.loads(run.stdout)
            self.assertEqual(summary['status'], 'PASS')
            self.assertNotIn('slot_accounting', summary)
            outputs.append(output.read_bytes())
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[0], (HERE / 'result.json').read_bytes())

    def test_cli_existing_output_does_not_change(self):
        output = self.directory / 'existing.json'; output.write_bytes(b'fixture')
        run = subprocess.run([sys.executable, '-B', str(HERE / 'verify.py'), '--root', str(ROOT), '--output', str(output)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(output.read_bytes(), b'fixture')


def add_evidence_test(name, mutate):
    def test(self):
        value = copy.deepcopy(self.evidence); mutate(value)
        self.rejected(v.validate_evidence, value, self.sources, self.selected)
    setattr(EvidenceTests, 'test_' + name, test)


for name, mutate in (
    ('slot_missing', lambda x: x['slots'].pop()),
    ('slot_reordered', lambda x: x['slots'].reverse()),
    ('wrong_source_pin', lambda x: x['slots'][0]['sources'].update(raw_trace_sha256='0' * 64)),
    ('wrong_baseline', lambda x: x.update(baseline_commit='0' * 40)),
    ('missing_field', lambda x: x['slots'][0]['native']['records'][0]['usage'].pop('cache_write_input_tokens')),
    ('null_not_zero', lambda x: x['slots'][0]['native']['records'][0]['usage'].update(cache_write_input_tokens=None)),
    ('bool_not_zero', lambda x: x['slots'][0]['native']['records'][0]['usage'].update(cache_write_input_tokens=False)),
    ('false_thread_count', lambda x: x['slots'][0]['native']['coverage'].update(threads=True)),
    ('bool_difference', lambda x: x['slots'][0]['public_meta']['aggregate_minus_own_terminal'].update(cache_write_input_tokens=False)),
    ('bad_cumulative', lambda x: x['slots'][0]['native']['records'][1].update(cumulative=good())),
    ('missing_record', lambda x: x['slots'][0]['native']['records'].pop(0)),
    ('duplicate_record', lambda x: x['slots'][0]['native']['records'].append(copy.deepcopy(x['slots'][0]['native']['records'][0]))),
    ('invalid_gate_hard_failure', lambda x: x['slots'][0]['native']['coverage'].update(critical_gates_valid=False)),
    ('unsafe_schema_value', lambda x: x['slots'][0]['native']['schema_signatures'][0]['paths'].append(['/fixture value', 'str'])),
    ('bad_cli_missing_total_not_zero', lambda x: x['slots'][0]['cli']['total_tokens'].update(value=0)),
    ('meta_prefix_label_invented', lambda x: x['slots'][0]['public_meta'].update(prefix_scope='KNOWN_SLOT_PREFIX')),
    ('meta_suffix_identity_changed', lambda x: x['slots'][0]['public_meta']['per_call'][-1].update(response_id_sha256='0' * 64)),
):
    add_evidence_test(name, mutate)


if __name__ == '__main__':
    unittest.main(verbosity=2)
