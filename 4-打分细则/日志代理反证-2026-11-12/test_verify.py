# -*- coding: utf-8 -*-
import ast
import copy
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('new_logproof', HERE / 'verify.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


class LogProofTests(unittest.TestCase):
    def base(self):
        return v.fixed_source_log()

    def item(self, log, kind, call_id=None):
        return next(x['payload'] for x in log if x['type'] == 'response_item' and
                    x['payload']['type'] == kind and
                    (call_id is None or x['payload'].get('call_id') == call_id))

    def copied_root(self, temporary):
        root = Path(temporary) / 'snapshot'
        root.mkdir()
        for relative in v.PINS:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / relative).read_bytes())
        return root

    def test_actual_source_pins(self):
        bindings = v.source_bindings(ROOT)
        self.assertEqual(len(bindings), 2)
        self.assertEqual({x['sha256'] for x in bindings}, set(v.PINS.values()))

    def test_all_models_run_and_limits(self):
        result = v.analyze(ROOT)
        self.assertEqual(len(result['cases']), 8)
        self.assertEqual(result['limits']['new_product_requests'], 0)
        self.assertFalse(result['limits']['actual_http_identified'])
        self.assertFalse(result['limits']['all_future_evidence_permanently_unidentifiable'])
        self.assertFalse(result['model_assumptions']['same_actual_model_outputs_proven'])
        self.assertFalse(result['model_assumptions']['official_api_conformance_proven'])

    def test_same_s3_is_not_same_full_log(self):
        case = v.run_models()['s3_excludes_tool_return']
        self.assertEqual(*case['selected_s3_bytes'])
        self.assertFalse(case['same_full_log'])
        self.assertNotEqual(*case['body_bytes'])
        self.assertEqual(case['body_bytes'][1] - case['body_bytes'][0], 792)

    def test_same_source_log_and_fixed_prefixes(self):
        log = self.base()
        rows = [v.render_sequence(log, policy) for policy in v.POLICIES]
        self.assertEqual(len({tuple(x['body_bytes'] for x in rows_) for rows_ in rows}), 3)
        self.assertEqual(len({tuple(x['source_prefix_sha256'] for x in rows_) for rows_ in rows}), 1)
        for sequence in rows:
            self.assertEqual([x['source_item_cut'] for x in sequence], [2, 4, 6])
            for row in sequence:
                v.validate_request(row['body'])
                self.assertEqual(row['body_bytes'], len(v.canon(row['body'])))
                self.assertEqual(row['body_sha256'], v.sha(v.canon(row['body'])))

    def test_renderers_do_not_modify_source_even_in_reverse_order(self):
        log = self.base()
        before = v.canon(log)
        forward = {p: v.render_sequence(log, p) for p in v.POLICIES}
        backward = {p: v.render_sequence(log, p) for p in reversed(v.POLICIES)}
        self.assertEqual(v.canon(log), before)
        self.assertEqual(forward, backward)

    def test_no_future_tool_output_leaks_into_earlier_cuts(self):
        log = self.base()
        changed = copy.deepcopy(log)
        self.item(changed, 'function_call_output', 'c2')['output'] = 'FUTURE' * 50
        a = v.render_sequence(log, 'full_history')
        b = v.render_sequence(changed, 'full_history')
        self.assertEqual(a[:2], b[:2])
        self.assertNotEqual(a[2]['body_sha256'], b[2]['body_sha256'])

    def test_terminal_reply_is_after_all_fixed_cuts(self):
        log = self.base()
        changed = copy.deepcopy(log)
        [x for x in changed if x['type'] == 'response_item'][-1]['payload']['content'][0]['text'] = 'LATER'
        self.assertEqual(v.render_sequence(log, 'full_history'),
                         v.render_sequence(changed, 'full_history'))

    def test_drop_removes_both_old_call_and_output(self):
        row = v.render_sequence(self.base(), 'drop_complete_old_exchange')[-1]
        ids = [x['call_id'] for x in row['body']['input'] if 'call_id' in x]
        self.assertEqual(ids, ['c2', 'c2'])
        v.validate_request(row['body'])

    def test_no_universal_drop_saving_without_old_exchange(self):
        log = self.base()
        full = v.render_sequence(log, 'full_history')
        drop = v.render_sequence(log, 'drop_complete_old_exchange')
        self.assertEqual(full[:2], drop[:2])
        self.assertNotEqual(full[2]['body_bytes'], drop[2]['body_bytes'])

    def test_reference_of_short_output_can_increase_bytes(self):
        log = self.base()
        self.item(log, 'function_call_output', 'c1')['output'] = 'x'
        full = v.render_sequence(log, 'full_history')[1]
        reference = v.render_sequence(log, 'reference_results')[1]
        self.assertGreater(reference['body_bytes'], full['body_bytes'])

    def test_reference_is_not_readback(self):
        case = v.run_models()['same_source_log_different_renderers']
        self.assertIsNone(case['reference_readback'])
        self.assertFalse(case['semantic_equivalence_claimed'])
        self.assertIn('pre-serialization', case['log_semantics'])

    def test_output_before_call_is_rejected(self):
        prefix = v.response_payloads(self.base())[:4]
        prefix[2], prefix[3] = prefix[3], prefix[2]
        with self.assertRaises(v.ProofError):
            v.render_request(prefix, 'full_history')

    def test_duplicate_id_even_when_each_pair_is_closed(self):
        prefix = v.response_payloads(self.base())[:6]
        prefix[4]['call_id'] = prefix[5]['call_id'] = 'c1'
        with self.assertRaises(v.ProofError):
            v.render_request(prefix, 'full_history')

    def test_duplicate_output_rejected(self):
        prefix = v.response_payloads(self.base())[:4]
        prefix.append(copy.deepcopy(prefix[-1]))
        with self.assertRaises(v.ProofError):
            v.render_request(prefix, 'full_history')

    def test_output_id_cannot_silently_change(self):
        prefix = v.response_payloads(self.base())[:4]
        prefix[-1]['call_id'] = 'c2'
        with self.assertRaises(v.ProofError):
            v.render_request(prefix, 'full_history')

    def test_dangling_call_rejected(self):
        with self.assertRaises(v.ProofError):
            v.render_request(v.response_payloads(self.base())[:3], 'full_history')

    def test_new_message_cannot_skip_pending_output(self):
        prefix = v.response_payloads(self.base())[:3]
        prefix.append(v.source_message('user', 'Next'))
        with self.assertRaises(v.ProofError):
            v.render_request(prefix, 'full_history')

    def test_wrong_registered_name_or_argument_shape_rejected(self):
        for field, value in [('name', 'other'), ('arguments', '[]'),
                             ('arguments', '{"key":false}'),
                             ('arguments', '{"key":"x","n":NaN}'),
                             ('arguments', '{"key":"x","key":"y"}'),
                             ('arguments', '{"key":"x","metadata":{"id":1,"id":2}}')]:
            prefix = v.response_payloads(self.base())[:4]
            prefix[2][field] = value
            with self.assertRaises((v.ProofError, ValueError)):
                v.render_request(prefix, 'full_history')

    def test_scalar_types_not_conflated(self):
        prefix = v.response_payloads(self.base())[:4]
        prefix[3]['output'] = True
        with self.assertRaises(v.ProofError):
            v.render_request(prefix, 'full_history')
        body = v.render_request(v.response_payloads(self.base())[:2], 'full_history')
        body['tools'][0]['strict'] = 0
        with self.assertRaises(v.ProofError):
            v.validate_request(body)

    def test_unknown_payload_fields_are_not_silently_dropped(self):
        prefix = v.response_payloads(self.base())[:2]
        prefix[1]['undeclared_business'] = 'data'
        with self.assertRaises(v.ProofError):
            v.render_request(prefix, 'full_history')

    def test_only_whitelisted_top_level_metadata_is_dropped(self):
        prefix = v.response_payloads(self.base())[:4]
        prefix[2]['id'] = 'opaque-log-id'
        prefix[2]['arguments'] = '{"key":"alpha","id":"business","metadata":{"id":"keep"}}'
        prefix[3]['output'] = '{"id":"business-result","metadata":"keep"}'
        body = v.render_request(prefix, 'full_history')
        self.assertNotIn('id', body['input'][2])
        self.assertEqual(body['input'][2]['arguments'], prefix[2]['arguments'])
        self.assertEqual(body['input'][3]['output'], prefix[3]['output'])

    def test_business_field_change_is_not_metadata_invariance(self):
        prefix = v.response_payloads(self.base())[:4]
        changed = copy.deepcopy(prefix)
        prefix[2]['arguments'] = '{"key":"alpha","id":"A"}'
        changed[2]['arguments'] = '{"key":"alpha","id":"B"}'
        a, b = v.canon(v.render_request(prefix, 'full_history')), v.canon(v.render_request(changed, 'full_history'))
        self.assertEqual(len(a), len(b))
        self.assertNotEqual(a, b)
        self.assertNotEqual(v.sha(a), v.sha(b))

    def test_utf8_bytes_not_characters(self):
        self.assertEqual(len('中😀'), 2)
        self.assertEqual(len('中😀'.encode('utf-8')), 7)
        self.assertEqual(v.canon('中😀'), '"中😀"'.encode('utf-8'))

    def test_leaf_split_changes_r3_not_declared_joining_sender(self):
        case = v.run_models()['r3_leaf_packaging']
        self.assertNotEqual(*case['r3_bytes'])
        self.assertTrue(case['same_ordered_text'])
        self.assertTrue(case['same_body_under_declared_joining_sender'])
        self.assertIsNone(case['semantic_equivalence_of_actual_model'])

    def test_s3_logging_nuisance_is_not_body_change(self):
        case = v.run_models()['s3_logging_metadata_only']
        self.assertNotEqual(*case['s3_bytes'])
        self.assertEqual(*case['body_sha256'])

    def test_usage_boundaries_are_not_sender_cuts(self):
        case = v.run_models()['usage_is_not_a_send_cut']
        self.assertEqual(case['r3_before']['bytes'], case['r3_after']['bytes'])
        self.assertNotEqual(case['r3_before']['segments'], case['r3_after']['segments'])
        self.assertTrue(case['same_sender_cuts_and_bodies'])

    def test_r3_unclosed_tail_is_not_lost(self):
        events = [{'type': 'response_item', 'payload': {'type': 'uninterpreted', 'x': 'tail'}}]
        measured = v.codex_r3(events)
        self.assertEqual(measured['bytes'], len(v.canon(events[0]['payload'])))
        self.assertEqual(measured['unclosed_tail_bytes'], measured['bytes'])
        self.assertEqual(measured['segments'], [measured['bytes']])

    def test_bad_or_future_cut_schedules_rejected(self):
        for cuts in [(True,), (0,), (100,), (2, 2), (4, 2), (), (2, 3)]:
            with self.assertRaises(v.ProofError):
                v.render_sequence(self.base(), 'full_history', cuts)

    def test_changed_cut_does_not_match_receipt(self):
        normal = v.render_sequence(self.base(), 'full_history')
        changed = v.render_sequence(self.base(), 'full_history', (2, 6))
        self.assertFalse(v.compatible(changed, v.receipts_for(normal, ['q2'])))

    def test_body_observations_can_remove_nonidentifiability(self):
        rows = {policy: v.render_sequence(self.base(), policy) for policy in v.POLICIES}
        self.assertEqual(v.candidate_status(rows, [])['count'], 3)
        self.assertEqual(v.candidate_status(rows, v.receipts_for(rows['full_history'], ['q1']))['count'], 3)
        self.assertEqual(v.candidate_status(rows, v.receipts_for(rows['full_history'], ['q2']))['count'], 2)
        result = v.candidate_status(rows, v.receipts_for(rows['full_history'], ['q3']))
        self.assertEqual(result['count'], 1)
        self.assertIn('within_declared_renderer_class', result['state'])

    def test_wrong_receipt_is_inconsistent_not_identified(self):
        rows = {policy: v.render_sequence(self.base(), policy) for policy in v.POLICIES}
        receipt = v.receipts_for(rows['full_history'], ['q3'])
        receipt[0]['body_sha256'] = 'f' * 64
        self.assertEqual(v.candidate_status(rows, receipt)['state'], 'inconsistent')

    def test_bad_receipt_scalar_duplicate_or_hash_rejected(self):
        rows = v.render_sequence(self.base(), 'full_history')
        for field, value in [('source_item_cut', True), ('body_bytes', False),
                             ('body_sha256', 'not-a-sha'), ('request_id', '')]:
            receipt = v.receipts_for(rows, ['q3'])
            receipt[0][field] = value
            with self.assertRaises(v.ProofError):
                v.compatible(rows, receipt)
        receipt = v.receipts_for(rows, ['q3']) * 2
        with self.assertRaises(v.ProofError):
            v.compatible(rows, receipt)

    def test_malformed_later_receipt_not_hidden_by_first_mismatch(self):
        rows = v.render_sequence(self.base(), 'full_history')
        receipt = v.receipts_for(rows, ['q2', 'q3'])
        receipt[0]['request_id'] = 'unknown-request'
        receipt[1]['body_bytes'] = True
        with self.assertRaises(v.ProofError):
            v.compatible(rows, receipt)

    def test_rendered_body_cannot_reuse_stale_fingerprint(self):
        rows = v.render_sequence(self.base(), 'full_history')
        receipt = v.receipts_for(rows, ['q3'])
        rows[-1]['body']['input'][1]['content'][0]['text'] = 'MODIFIED'
        with self.assertRaises(v.ProofError):
            v.compatible(rows, receipt)

    def test_source_tamper_and_missing_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.copied_root(temporary)
            relative = next(iter(v.PINS))
            path = root / relative
            path.write_bytes(path.read_bytes() + b' ')
            with self.assertRaises(v.ProofError):
                v.source_bindings(root)
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(OSError):
                v.source_bindings(Path(temporary))

    def test_source_symlink_rejected_before_read(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            relative = next(iter(v.PINS))
            target = root / relative
            target.parent.mkdir(parents=True)
            target.symlink_to(ROOT / relative)
            with self.assertRaises(v.ProofError):
                v.source_bindings(root)

    def test_no_assert_or_product_network_dynamic_execution_imports(self):
        tree = ast.parse((HERE / 'verify.py').read_text(encoding='utf-8'))
        self.assertFalse(any(isinstance(node, ast.Assert) for node in ast.walk(tree)))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add(node.module.split('.')[0])
        self.assertLessEqual(imports, {'argparse', 'copy', 'hashlib', 'json', 'pathlib', 'sys'})
        with patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')):
            self.assertEqual(v.analyze(ROOT)['status'], 'PASS_CONDITIONAL_LOG_PROXY_COUNTERMODELS')

    def test_real_cli_deterministic_and_no_overwrite(self):
        expected = json.dumps(v.analyze(ROOT), ensure_ascii=False, sort_keys=True,
                              indent=2, allow_nan=False) + '\n'
        command = [sys.executable, '-I', '-S', '-B', str(HERE / 'verify.py'), '--root', str(ROOT)]
        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(process.stdout.decode('utf-8'), expected)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'new.json'
            first = subprocess.run(command + ['--output', str(output)], capture_output=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(output.read_text(encoding='utf-8'), expected)
            before = output.read_bytes()
            second = subprocess.run(command + ['--output', str(output)], capture_output=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(output.read_bytes(), before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
