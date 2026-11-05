#!/usr/bin/env python3
"""Offline tests of trusted public pins AND the unpinned pure semantic layer."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location('native_partition', HERE / 'verify.py')
v = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v)
BAD = (ValueError, KeyError, TypeError)


class SemanticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = v.load_sources(ROOT)

    def requests(self, arm='codex', block=1):
        base = v.SCENE + '/sessions/confirm-b%02d-%s/' % (block, arm)
        paths = [base + f for f in ('01-request.json', '02-request.json')]
        return [v.parse_json(self.raw[p]) for p in paths]

    def split(self, first, second, arm='codex'):
        return v.decompose(first, second, arm,
                           [len(v.canonical(first)), len(v.canonical(second))])

    def test_exact_real_components_and_negative_residuals(self):
        result = v.derive(self.raw)
        expected = [(12021, 4, 142, 196, 401), (1981, 2, 27, 156, 216),
                    (12021, 4, 142, 199, 162), (1981, 2, 27, 153, 360),
                    (12021, 4, 142, 196, 370), (1981, 2, 27, 156, 216)]
        for row, parts in zip(result['rows'], expected):
            self.assertEqual(tuple(row['components'][k] for k in v.COMPONENTS), parts)
            self.assertEqual(sum(parts), row['metric']['delta'])
            self.assertEqual(sum(x['quote_bytes'] for x in row['text_leaves']), parts[1])
            self.assertTrue(all(p['pointer'].endswith('/text') for p in row['text_leaves']))
        self.assertEqual([p['original_difference'] for p in result['pairs']], [10382, 10005, 10351])
        self.assertEqual([p['residual_after_decoded_text_subtraction'] for p in result['pairs']],
                         [342, -35, 311])
        self.assertEqual([p['residual_after_actual_text_scalars_subtraction'] for p in result['pairs']],
                         [225, -152, 194])
        self.assertEqual(result['original_preregistered_result']['threshold_applies_to'],
                         'original_difference_only')

    def test_unicode_quotes_backslashes_and_control_bytes_two_real_leaves(self):
        first, second = self.requests()
        texts = ['汉字"\\\n', 'é\t\r\x00']
        for block, text in zip(second['input'][-1]['output'], texts):
            block['text'] = text
        row = self.split(first, second)
        self.assertEqual(row['components']['decoded_text'], sum(len(t.encode()) for t in texts))
        self.assertEqual(row['components']['text_quotes'], 4)
        # Escapes: quote=1, backslash=1, LF=1, TAB=1, CR=1, NUL=5 extra bytes.
        self.assertEqual(row['components']['text_escape_expansion'], 10)
        self.assertEqual(row['component_sum'], row['metric']['delta'])
        scalar_sum = sum(len(json.dumps(t, ensure_ascii=False).encode()) for t in texts)
        self.assertEqual(sum(x['json_scalar_bytes'] for x in row['text_leaves']), scalar_sum)
        # Concatenating these real leaves would lose a pair of actual JSON quotes.
        self.assertEqual(scalar_sum - len(v.canonical(''.join(texts))), 2)

    def test_dsh_single_string_leaf_and_real_scalar_pointer(self):
        first, second = self.requests('dsh')
        second['messages'][-1]['content'][0]['content'][0]['text'] = '汉"\\\n'
        row = self.split(first, second, 'dsh')
        self.assertEqual(row['components']['text_quotes'], 2)
        self.assertEqual(row['components']['text_escape_expansion'], 3)
        self.assertEqual(row['text_leaves'][0]['pointer'], '/messages/2/content/0/content/0/text')

    def test_empty_prefix_rejected_in_both_protocols(self):
        for arm, field in (('codex', 'input'), ('dsh', 'messages')):
            first, second = self.requests(arm)
            second[field] = second[field][len(first[field]):]
            first[field] = []
            with self.subTest(arm=arm), self.assertRaisesRegex(ValueError, 'nonempty'):
                self.split(first, second, arm)

    def test_prefix_drift_even_when_same_length_or_bool_alias(self):
        first, second = self.requests('dsh')
        leaf = second['messages'][0]['content'][0]
        leaf['text'] = 'X' + leaf['text'][1:]
        with self.assertRaisesRegex(ValueError, 'prefix'):
            self.split(first, second, 'dsh')
        for replacement in ('x', 1, True):
            first, second = self.requests('dsh')
            second['messages'][0]['content'][0]['text'] = replacement
            with self.subTest(value=replacement), self.assertRaisesRegex(ValueError, 'prefix'):
                self.split(first, second, 'dsh')
        first, second = self.requests('dsh')
        first['messages'][0]['flag'] = True
        second['messages'][0]['flag'] = 1
        with self.assertRaisesRegex(ValueError, 'prefix'):
            self.split(first, second, 'dsh')

    def test_selected_field_presence_and_values_cannot_drift(self):
        for arm, key in (('codex', 'instructions'), ('codex', 'tools'),
                         ('dsh', 'system'), ('dsh', 'tools')):
            first, second = self.requests(arm)
            second[key] = 'changed'
            with self.subTest(arm=arm, key=key), self.assertRaises(ValueError):
                self.split(first, second, arm)
        first, second = self.requests()
        second['previous_response_id'] = None  # Absent and null are not equal.
        with self.assertRaisesRegex(ValueError, 'presence'):
            self.split(first, second)

    def test_unselected_controls_mixed_protocol_missing_history(self):
        for change in ('control', 'mixed', 'missing'):
            first, second = self.requests()
            if change == 'control':
                second['model'] = 'other-model'
            elif change == 'mixed':
                second['messages'] = []
            else:
                del second['input']
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.split(first, second)

    def test_assistant_classification_not_generic_extra_history(self):
        for arm, field in (('codex', 'input'), ('dsh', 'messages')):
            for variant in ('role', 'extra', 'duplicate_return'):
                first, second = self.requests(arm)
                index = len(first[field])
                if variant == 'role':
                    second[field][index] = {'role': 'user', 'content': 'not assistant'}
                elif variant == 'extra':
                    second[field].insert(index, {'role': 'assistant', 'content': 'unknown schema'})
                else:
                    second[field].insert(-1, copy.deepcopy(second[field][-1]))
                with self.subTest(arm=arm, variant=variant), self.assertRaises(BAD):
                    self.split(first, second, arm)

    def test_tool_schema_counts_types_and_call_identity(self):
        for arm, field in (('codex', 'input'), ('dsh', 'messages')):
            for variant in ('id', 'text_type', 'more_text', 'return_type', 'call'):
                first, second = self.requests(arm)
                item = second[field][-1]
                if arm == 'codex':
                    leaves = item['output']
                    if variant == 'id': item['call_id'] = 'other-call'
                    if variant == 'return_type': item['type'] = 'message'
                    if variant == 'call': second[field][-2]['name'] = 'other_tool'
                else:
                    tool = item['content'][0]
                    leaves = tool['content']
                    if variant == 'id': tool['tool_use_id'] = 'other-call'
                    if variant == 'return_type': tool['is_error'] = 0
                    if variant == 'call': second[field][-2]['content'][-1]['name'] = 'other_tool'
                if variant == 'text_type': leaves[0]['text'] = ['not-a-scalar']
                if variant == 'more_text': leaves.append(copy.deepcopy(leaves[0]))
                with self.subTest(arm=arm, variant=variant), self.assertRaises(BAD):
                    self.split(first, second, arm)

    def test_real_text_or_assistant_growth_rejects_unchanged_observation(self):
        for arm, field in (('codex', 'input'), ('dsh', 'messages')):
            for target in ('text', 'assistant'):
                first, second = self.requests(arm)
                if target == 'text':
                    block = second[field][-1]['output'][0] if arm == 'codex' else second[field][-1]['content'][0]['content'][0]
                    block['text'] += '额外字节'
                elif arm == 'codex':
                    second[field][len(first[field])]['content'][0]['text'] += 'extra'
                else:
                    second[field][-2]['content'][0]['thinking'] += 'extra'
                row = self.split(first, second, arm)
                run = 'confirm-b01-' + arm
                obs = v.parse_json(self.raw[v.SCENE + '/sessions/' + run + '/observations.json'])
                with self.subTest(arm=arm, target=target), self.assertRaisesRegex(ValueError, 'metric'):
                    v.check_observation(obs, row, run, 1, arm)

    def test_observation_identity_metric_type_and_original_must_match(self):
        first, second = self.requests()
        base = v.SCENE + '/sessions/confirm-b01-codex/'
        obs = v.parse_json(self.raw[base + 'observations.json'])
        row = self.split(first, second)
        for target in ('id', 'block', 'projection', 'original', 'returned'):
            changed = copy.deepcopy(obs)
            if target == 'id': changed['id'] = 'confirm-b01-dsh'
            if target == 'block': changed['block'] = True
            if target == 'projection': changed['projection_metric']['delta'] += 1
            if target == 'original': changed['original_metric']['before'] += 1
            if target == 'returned': changed['original_metric']['returned_bytes'] -= 1
            with self.subTest(target=target), self.assertRaises(ValueError):
                v.check_observation(changed, row, 'confirm-b01-codex', 1, 'codex')

    def test_ledger_coverage_order_and_deltas_not_only_median(self):
        path = v.SCENE + '/ledger.json'
        for variant in ('drop', 'order', 'arm', 'branch', 'count'):
            raw = dict(self.raw)
            ledger = v.parse_json(raw[path])
            if variant == 'drop': ledger['blocks'].pop()
            if variant == 'order': ledger['blocks'][0]['order'].reverse()
            if variant == 'arm': ledger['blocks'][0]['codex_delta'] += 1
            if variant == 'branch': ledger['branch'] = 'residual_passes_4096'
            if variant == 'count': ledger['valid_blocks'] = 3.0
            raw[path] = v.canonical(ledger)
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                v.derive(raw)

    def test_strict_json_and_canonical_types(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError): v.parse_json(raw)
        for a, b in ((True, 1), (1, 1.0), (False, 0), (None, [])):
            with self.subTest(a=a, b=b), self.assertRaises(ValueError): v.same(a, b, 'typed')


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='native-byte-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for relative in list(v.SOURCE_SHA256) + [v.OUTPUT]:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / relative).read_bytes())

    def output(self):
        return v.parse_json((self.root / v.OUTPUT).read_bytes())

    def save_output(self, result):
        (self.root / v.OUTPUT).write_bytes(v.canonical(result))

    def snapshot(self):
        return {str(p.relative_to(self.root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.root.rglob('*') if p.is_file()}

    def test_positive_read_only_no_network_or_execution(self):
        before = self.snapshot()
        original_open = Path.open
        def read_only(path, mode='r', *args, **kwargs):
            if any(flag in mode for flag in ('w', 'a', 'x', '+')):
                raise AssertionError('write attempted')
            return original_open(path, mode, *args, **kwargs)
        with mock.patch.object(Path, 'open', read_only), \
             mock.patch.object(socket, 'socket', side_effect=AssertionError('network')), \
             mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('subprocess')):
            result = v.verify(self.root)
        self.assertEqual(len(result['sources']), 22)
        self.assertEqual(self.snapshot(), before)

    def test_cli_normal_and_optimized_identical(self):
        outputs = []
        for flags in ([], ['-O']):
            proc = subprocess.run([sys.executable, '-I', '-S', '-B', *flags,
                                   str(HERE / 'verify.py'), '--root', str(self.root)],
                                  capture_output=True, check=False)
            self.assertEqual(proc.returncode, 0, proc.stderr.decode())
            outputs.append(proc.stdout)
        self.assertEqual(*outputs)
        self.assertTrue(json.loads(outputs[0])['ok'])

    def test_every_source_pin_including_six_metrics(self):
        for relative in v.SOURCE_SHA256:
            path = self.root / relative
            original = path.read_bytes()
            path.write_bytes(original + b' ')
            with self.subTest(source=relative), self.assertRaisesRegex(ValueError, 'source SHA'):
                v.verify(self.root)
            path.write_bytes(original)

    def test_equal_length_assistant_change_and_resealed_derived_rejected(self):
        relative = v.SCENE + '/sessions/confirm-b01-codex/02-request.json'
        path = self.root / relative
        body = v.parse_json(path.read_bytes())
        item = body['input'][4]['content'][0]
        item['text'] = 'X' + item['text'][1:]
        path.write_bytes(v.canonical(body))
        raw = {p: (self.root / p).read_bytes() for p in v.SOURCE_SHA256}
        # Pure accounting cannot authenticate equal-length, schema-valid text.
        self.save_output(v.derive(raw))
        with self.assertRaisesRegex(ValueError, 'source SHA'): v.verify(self.root)

    def test_metric_source_swap_and_resealed_metric_rejected(self):
        path = self.root / (v.SCENE + '/sessions/confirm-b01-codex/observations.json')
        baseline = self.output()
        original = path.read_bytes()
        for variant in ('changed_record', 'other_slot'):
            if variant == 'changed_record':
                obs = v.parse_json(original)
                obs['endpoint']['head'] = False
                replacement = v.canonical(obs)
            else:
                replacement = (self.root / (v.SCENE + '/sessions/confirm-b03-codex/observations.json')).read_bytes()
            path.write_bytes(replacement)
            result = copy.deepcopy(baseline)
            for source in result['sources']:
                if source['path'].endswith('confirm-b01-codex/observations.json'):
                    source['sha256'] = hashlib.sha256(replacement).hexdigest()
            self.save_output(result)
            with self.subTest(variant=variant), self.assertRaisesRegex(ValueError, 'source SHA'):
                v.verify(self.root)

    def test_component_double_count_missing_and_virtual_concat_rejected(self):
        baseline = self.output()
        for variant in ('double', 'missing', 'virtual', 'residual', 'threshold', 'selfseal'):
            changed = copy.deepcopy(baseline)
            parts = changed['rows'][0]['components']
            if variant == 'double':
                parts['decoded_text'] *= 2
                changed['rows'][0]['component_sum'] = sum(parts.values())
            if variant == 'missing': del parts['text_escape_expansion']
            if variant == 'virtual':
                parts['text_quotes'] -= 2
                parts['return_structure'] += 2  # Closure alone would accept this false partition.
            if variant == 'residual': changed['pairs'][1]['residual_after_decoded_text_subtraction'] = 35
            if variant == 'threshold': changed['original_preregistered_result']['threshold_applies_to'] = 'residual'
            if variant == 'selfseal': changed['self_sha256'] = hashlib.sha256(v.canonical(changed)).hexdigest()
            self.save_output(changed)
            with self.subTest(variant=variant), self.assertRaisesRegex(ValueError, 'derived output'):
                v.verify(self.root)

    def test_output_path_identity_and_bool_numeric_resealing(self):
        baseline = self.output()
        for variant in ('source', 'pointer', 'numeric', 'row_missing', 'row_duplicate'):
            changed = copy.deepcopy(baseline)
            if variant == 'source': changed['rows'][0]['source_refs']['observation'] = changed['rows'][1]['source_refs']['observation']
            if variant == 'pointer': changed['rows'][1]['text_leaves'][0]['pointer'] = '/messages/2/content/0/content'
            if variant == 'numeric': changed['rows'][0]['text_leaves'][0]['quote_bytes'] = 2.0
            if variant == 'row_missing': changed['rows'].pop()
            if variant == 'row_duplicate': changed['rows'].append(copy.deepcopy(changed['rows'][0]))
            self.save_output(changed)
            with self.subTest(variant=variant), self.assertRaises(ValueError): v.verify(self.root)

    def test_missing_source_and_output_duplicate_json(self):
        path = self.root / (v.SCENE + '/sessions/confirm-b01-codex/observations.json')
        path.unlink()
        with self.assertRaisesRegex(ValueError, 'missing source'): v.verify(self.root)
        path.write_bytes((ROOT / path.relative_to(self.root)).read_bytes())
        output = self.root / v.OUTPUT
        output.write_bytes(b'{"x":1,"x":1}')
        with self.assertRaisesRegex(ValueError, 'duplicate JSON'): v.verify(self.root)

    def test_unsafe_paths_and_symlink_even_to_same_content(self):
        for relative in ('../escape', '/absolute', './a', 'a//b', 'a/../b', 'a\\b', ''):
            with self.subTest(path=relative), self.assertRaises(ValueError): v.safe_file(self.root, relative)
        relative = next(iter(v.SOURCE_SHA256))
        path = self.root / relative
        path.unlink()
        path.symlink_to(ROOT / relative)
        with self.assertRaisesRegex(ValueError, 'symlink'): v.verify(self.root)


if __name__ == '__main__':
    unittest.main(verbosity=2)
