#!/usr/bin/env python3
"""Tests for the Codex input-face residual localization package.

Covers the frozen classification rule, canonical layout byte accounting,
alignment discipline (count_mismatch registered, tails never guessed),
branch selection, hard-equality tamper detection, CLI behavior (exclusive
--output, fail-closed exits, dual-interpreter determinism, content-free
result) and a real-archive end-to-end test gated by the environment variable
CODEX_RESIDUAL_ARCHIVE_ROOT (unset => loud FAIL, never a silent skip).

Run:  python3 test_verify.py   (and python3 -O test_verify.py; both green)
"""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
ARCHIVE_ENV = 'CODEX_RESIDUAL_ARCHIVE_ROOT'

sys.path.insert(0, str(HERE))
import verify as V  # noqa: E402  (self-contained module, safe to import)

FAKE_HEAD = 'a' * 40


def synth_payload(case, rep, role, k):
    """Synthetic message payload: envelope drifts per rep, content stable.

    The rep index is encoded in the id length ('r'*rep) so slot byte totals
    stay distinct per group for deterministic max/min selection.
    """
    return {
        'type': 'message',
        'role': role,
        'id': 'idx-%s-%s-%s-%d' % (case, 'r' * rep, role, k),
        'content': [{'type': 'input_text',
                     'text': 'SENTINEL-%s-%s-%d task body text' % (case, role, k)}],
        'internal_chat_message_metadata_passthrough': {
            'create_time': 1730000000.0 + rep,
            'turn_id': '00000000-0000-4000-8000-%012d' % (rep,),
            'content_item_kinds': ['text'],
        },
    }


def write_rollout(path, messages):
    lines = [{'type': 'session_meta', 'payload': {'id': 'meta-unused'}}]
    for message in messages:
        lines.append({'type': 'response_item', 'payload': message})
    text = '\n'.join(json.dumps(line, ensure_ascii=False) for line in lines) + '\n'
    path.write_bytes(text.encode('utf-8'))


def build_fixture(base):
    """Synthetic repo + archive mirroring the real layout; returns (root, archive)."""
    root = base / 'repo'
    archive = base / 'archive'
    pkg = root / '4-打分细则' / 'Codex输入面残差定位-2026-11-16'
    pkg.mkdir(parents=True)
    (root / '.git').mkdir()
    (root / '.git' / 'HEAD').write_text(FAKE_HEAD + '\n', encoding='utf-8')
    (pkg / 'README.md').write_bytes((HERE / 'README.md').read_bytes())
    r3_dir = root / '4-打分细则' / 'R3不稳定来源分解-2026-11-16'
    r3_dir.mkdir(parents=True)
    sums = {}
    bindings = []
    slots = []
    for case in V.CASES:
        for rep in V.REPS:
            slot = V.slot_id(case, rep)
            messages = {}
            for role in V.ROLES_COMPARED:
                count = 1 if role == 'developer' else 2
                messages[role] = [synth_payload(case, rep, role, k) for k in range(count)]
            rel = 'codex/runs/%s/agent-session/rollout-fake-%s.jsonl' % (slot, slot)
            path = archive / rel
            path.parent.mkdir(parents=True)
            ordered = messages['user'] + messages['developer']
            write_rollout(path, ordered)
            raw = path.read_bytes()
            bindings.append({'slot': slot, 'archive_relative_path': rel,
                             'sha256': hashlib.sha256(raw).hexdigest(), 'file': path.name})
            sums[slot] = {role: sum(len(V.canon(m)) for m in messages[role])
                          for role in V.ROLES_COMPARED}
            slots.append({'slot': slot, 'message_by_role_bytes': dict(sums[slot])})
    totals = {slot: sum(by_role.values()) for slot, by_role in sums.items()}
    for case in V.CASES:
        case_totals = [totals[V.slot_id(case, rep)] for rep in V.REPS]
        if len(set(case_totals)) != 3:
            raise AssertionError('fixture totals must be distinct within group %s' % case)
    groups = []
    for case in V.CASES:
        names = [V.slot_id(case, rep) for rep in V.REPS]
        max_slot = max(names, key=lambda s: totals[s])
        min_slot = min(names, key=lambda s: totals[s])
        groups.append({'group': case, 'arm': 'codex', 'max_slot': max_slot, 'min_slot': min_slot,
                       'message_by_role_max_slot': dict(sums[max_slot]),
                       'message_by_role_min_slot': dict(sums[min_slot])})
    r3 = {'schema': V.R3_SCHEMA, 'prereg_sha256': 'b' * 64, 'slots': slots,
          'trace_bindings': bindings, 'groups': groups, 'baseline_commit': 'c' * 40}
    (r3_dir / 'result.json').write_bytes(
        (json.dumps(r3, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8'))
    return root, archive


def run_cli(root, archive, output=None, opt=False):
    cmd = [sys.executable] + (['-O'] if opt else []) + [str(HERE / 'verify.py'),
                                                        '--root', str(root),
                                                        '--archive-root', str(archive)]
    if output is not None:
        cmd += ['--output', str(output)]
    return subprocess.run(cmd, capture_output=True)


class ClassificationRuleTests(unittest.TestCase):
    """Frozen merged rule: content keys, envelope keys, conservative tie-break."""

    def test_envelope_keys_are_metadata(self):
        for key in ('id', 'call_id', 'name', 'role', 'type'):
            side, reason = V.classify_path((key,))
            self.assertEqual(side, 'metadata', key)
            self.assertIn(key, reason)

    def test_top_level_timestamp_keys_are_metadata(self):
        for key in ('create_time', 'updated_at', 'received_at', 'ts'):
            side, _reason = V.classify_path((key,))
            self.assertEqual(side, 'metadata', key)

    def test_content_keys_at_any_depth_are_content(self):
        for segments in (('text',), ('content',), ('arguments',),
                         ('content', '[0]', 'text'), ('wrapper', 'text')):
            side, reason = V.classify_path(segments)
            self.assertEqual(side, 'content', segments)
            self.assertIn('content key', reason)

    def test_ambiguous_keys_fall_to_content_side(self):
        # Nested timestamp/uuid under a passthrough object: NOT top-level -> content.
        side, reason = V.classify_path(('internal_chat_message_metadata_passthrough', 'create_time'))
        self.assertEqual(side, 'content')
        self.assertIn('ambiguous', reason)
        # Unknown keys anywhere -> content (conservative).
        self.assertEqual(V.classify_path(('unknown_key',))[0], 'content')
        self.assertEqual(V.classify_path(('deep', 'nested', 'unknown'))[0], 'content')
        # An envelope key name nested one level down is no longer top-level metadata.
        self.assertEqual(V.classify_path(('obj', 'id'))[0], 'content')


class CanonicalLayoutTests(unittest.TestCase):

    def test_layout_spans_point_at_value_bytes(self):
        payload = {'id': 'abc', 'create_time': 1730000000.5,
                   'content': [{'type': 'input_text', 'text': '值'}],
                   'nested': {'turn_id': 'u', 'empty_list': []}}
        raw, spans = V.layout_spans(payload)
        self.assertEqual(spans[()], (0, len(raw)))
        self.assertEqual(raw[spans[('id',)][0]:spans[('id',)][1]], b'"abc"')
        self.assertEqual(raw[spans[('content', '[0]', 'text',)][0]:spans[('content', '[0]', 'text')][1]],
                         '"值"'.encode('utf-8'))
        self.assertEqual(raw[spans[('nested',)][0]:spans[('nested',)][1]],
                         b'{"empty_list":[],"turn_id":"u"}')
        self.assertEqual(raw[spans[('nested', 'empty_list')][0]:spans[('nested', 'empty_list')][1]],
                         b'[]')
        # Layout covers the entire canonical byte range exactly once.
        end, entries = V.canonical_layout(payload)
        self.assertEqual(end, len(raw))
        covered = bytearray(len(raw))
        for start, stop, _path in entries:
            for position in range(start, stop):
                covered[position] = 1
        self.assertTrue(all(covered))


def trio(payloads):
    return [list(items) for items in payloads]


class CompareRoleAcrossSlotsTests(unittest.TestCase):

    def base_payload(self, text='shared body'):
        return {'type': 'message', 'role': 'user', 'id': 'same-id',
                'content': [{'type': 'input_text', 'text': text}]}

    def test_identical_trio(self):
        payload = self.base_payload()
        record = V.compare_role_across_slots(trio(([payload], [payload], [payload])),
                                             ['s1', 's2', 's3'])
        self.assertEqual(record['classification'], 'identical')
        self.assertFalse(record['count_mismatch'])
        self.assertEqual(record['identical_ks'], [0])
        self.assertEqual(record['differing_ks'], [])
        self.assertEqual(record['paths_metadata'], {})
        self.assertEqual(record['paths_content'], {})

    def test_metadata_only_trio(self):
        def payload(slot):
            item = self.base_payload()
            item['id'] = 'id-' + slot
            return item
        record = V.compare_role_across_slots(
            trio(([payload('s1')], [payload('s2')], [payload('s3')])), ['s1', 's2', 's3'])
        self.assertEqual(record['classification'], 'metadata_drift')
        self.assertIn('payload.id', record['paths_metadata'])
        self.assertEqual(record['paths_content'], {})
        self.assertEqual(record['differing_ks'], [0])
        entry = record['diffs'][0]['slot_pairs'][0]['entries'][0]
        self.assertEqual(entry['kind'], 'value')
        self.assertEqual(entry['side'], 'metadata')
        self.assertIsNotNone(entry['byte_offsets']['s1']['length'])

    def test_content_drift_trio(self):
        def payload(text):
            item = self.base_payload()
            item['content'][0]['text'] = text
            return item
        record = V.compare_role_across_slots(
            trio(([payload('a')], [payload('b')], [payload('c')])), ['s1', 's2', 's3'])
        self.assertEqual(record['classification'], 'content_drift')
        self.assertIn('payload.content[0].text', record['paths_content'])
        self.assertEqual(record['paths_metadata'], {})

    def test_count_mismatch_registers_without_guessing(self):
        aligned = self.base_payload('stable aligned body')
        tail_guess_bait = self.base_payload('tail that must not be matched')
        slot_payloads = [[aligned, aligned],
                         [aligned, aligned],
                         [aligned, aligned, tail_guess_bait]]
        record = V.compare_role_across_slots(slot_payloads, ['s1', 's2', 's3'])
        self.assertTrue(record['count_mismatch'])
        self.assertEqual(record['counts'], {'s1': 2, 's2': 2, 's3': 3})
        self.assertEqual(record['aligned_ks'], 2)
        # Aligned prefix identical -> no diff at all; the tail is only registered.
        self.assertEqual(record['classification'], 'identical')
        self.assertEqual(record['differing_ks'], [])
        self.assertEqual(record['excluded_tails']['s3'],
                         {'registered_range': [2, 2], 'registered_count': 1})
        self.assertNotIn('s1', record['excluded_tails'])
        # No diff entry may reference the excluded tail index k=2.
        for diff in record['diffs']:
            self.assertLess(diff['k'], 2)

    def test_count_mismatch_with_aligned_drift_still_classifies_prefix(self):
        def payload(tag):
            item = self.base_payload('stable aligned body')
            item['id'] = 'id-' + tag
            return item
        slot_payloads = [[payload('a'), payload('p')],
                         [payload('b'), payload('q')],
                         [payload('c'), payload('r'), self.base_payload('bait tail')]]
        record = V.compare_role_across_slots(slot_payloads, ['s1', 's2', 's3'])
        self.assertTrue(record['count_mismatch'])
        self.assertEqual(record['classification'], 'metadata_drift')
        self.assertEqual(sorted(record['differing_ks']), [0, 1])
        self.assertIn('payload.id', record['paths_metadata'])


class SelectBranchTests(unittest.TestCase):

    def test_metadata_only_requires_all_localized_and_no_content(self):
        self.assertEqual(
            V.select_branch(['localized_metadata'] * 3, content_anywhere=False),
            'B-METADATA-ONLY')
        self.assertEqual(
            V.select_branch(['localized_metadata'] * 3, content_anywhere=True),
            'B-CONTENT-DRIFT')

    def test_any_localized_content_gives_content_drift(self):
        self.assertEqual(
            V.select_branch(['localized_content', 'localized_metadata', 'localized_metadata'],
                            content_anywhere=False),
            'B-CONTENT-DRIFT')
        self.assertEqual(
            V.select_branch(['localized_metadata'] * 2 + ['localized_content'],
                            content_anywhere=True),
            'B-CONTENT-DRIFT')

    def test_blocked_targets_give_count_mismatch(self):
        self.assertEqual(
            V.select_branch(['blocked', 'blocked', 'blocked'], content_anywhere=False),
            'B-COUNT-MISMATCH')
        # Partial block without any content anywhere: degraded -> count mismatch.
        self.assertEqual(
            V.select_branch(['blocked', 'localized_metadata', 'localized_metadata'],
                            content_anywhere=False),
            'B-COUNT-MISMATCH')
        # Partial block with aligned-part content: content branch wins.
        self.assertEqual(
            V.select_branch(['blocked', 'localized_content', 'localized_metadata'],
                            content_anywhere=True),
            'B-CONTENT-DRIFT')


class FixtureCliTests(unittest.TestCase):
    """End-to-end CLI behavior over a synthetic repo + archive in a temp dir."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix='codex-residual-test-')
        base = Path(self._tmp.name)
        self.root, self.archive = build_fixture(base)
        self.addCleanup(self._tmp.cleanup)

    def test_cli_end_to_end_fixture(self):
        output = Path(self._tmp.name) / 'result.json'
        proc = run_cli(self.root, self.archive, output=output)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode('utf-8'))
        result = json.loads(output.read_bytes().decode('utf-8'))
        self.assertEqual(result['schema'], V.RESULT_SCHEMA)
        self.assertEqual(result['baseline_commit'], FAKE_HEAD)
        self.assertTrue(result['hard_equality']['passed'])
        self.assertEqual(result['branch'], 'B-CONTENT-DRIFT')
        self.assertEqual(result['hard_equality']['checks_total'], 50)
        self.assertEqual(len(result['trace_bindings_verified']), 15)
        for case in V.CASES:
            for role in V.ROLES_COMPARED:
                record = result['groups'][case][role]
                self.assertFalse(record['count_mismatch'])
                self.assertEqual(record['classification'], 'content_drift')
        stdout = proc.stdout.decode('utf-8')
        self.assertIn('全局分支：B-CONTENT-DRIFT', stdout)
        self.assertIn('硬等校验：50/50 通过', stdout)

    def test_output_refuses_overwrite(self):
        output = Path(self._tmp.name) / 'result.json'
        first = run_cli(self.root, self.archive, output=output)
        self.assertEqual(first.returncode, 0)
        original = output.read_bytes()
        second = run_cli(self.root, self.archive, output=output)
        self.assertEqual(second.returncode, 2)
        self.assertIn('refuses to overwrite', second.stderr.decode('utf-8'))
        self.assertEqual(output.read_bytes(), original)

    def test_hard_equality_tamper_fails_closed(self):
        r3_path = (self.root / '4-打分细则' / 'R3不稳定来源分解-2026-11-16' / 'result.json')
        r3 = json.loads(r3_path.read_bytes().decode('utf-8'))
        r3['groups'][0]['message_by_role_min_slot']['user'] += 1
        r3_path.write_bytes((json.dumps(r3, ensure_ascii=False, indent=2, sort_keys=True)
                             + '\n').encode('utf-8'))
        proc = run_cli(self.root, self.archive)
        self.assertEqual(proc.returncode, 2)
        self.assertIn('FAIL-CLOSED', proc.stderr.decode('utf-8'))

    def test_prereg_readme_tamper_fails_closed(self):
        readme = self.root / '4-打分细则' / 'Codex输入面残差定位-2026-11-16' / 'README.md'
        readme.write_bytes(readme.read_bytes() + b'\n')
        proc = run_cli(self.root, self.archive)
        self.assertEqual(proc.returncode, 2)
        self.assertIn('README SHA mismatch', proc.stderr.decode('utf-8'))

    def test_trace_tamper_fails_closed(self):
        slot = V.slot_id(V.CASES[0], 1)
        path = self.archive / 'codex' / 'runs' / slot / 'agent-session' / ('rollout-fake-%s.jsonl' % slot)
        path.write_bytes(path.read_bytes() + b'\n')
        proc = run_cli(self.root, self.archive)
        self.assertEqual(proc.returncode, 2)
        self.assertIn('trace SHA mismatch', proc.stderr.decode('utf-8'))

    def test_dual_interpreter_stdout_and_result_identical(self):
        out_plain = Path(self._tmp.name) / 'r_plain.json'
        out_opt = Path(self._tmp.name) / 'r_opt.json'
        plain = run_cli(self.root, self.archive, output=out_plain)
        opt = run_cli(self.root, self.archive, output=out_opt, opt=True)
        self.assertEqual(plain.returncode, 0, plain.stderr.decode('utf-8'))
        self.assertEqual(opt.returncode, 0, opt.stderr.decode('utf-8'))
        self.assertEqual(plain.stdout, opt.stdout)
        self.assertEqual(out_plain.read_bytes(), out_opt.read_bytes())
        # Re-run determinism: a third plain run reproduces the same bytes.
        out_again = Path(self._tmp.name) / 'r_again.json'
        again = run_cli(self.root, self.archive, output=out_again)
        self.assertEqual(again.returncode, 0)
        self.assertEqual(out_again.read_bytes(), out_plain.read_bytes())

    def test_result_is_content_free(self):
        output = Path(self._tmp.name) / 'result.json'
        proc = run_cli(self.root, self.archive, output=output)
        self.assertEqual(proc.returncode, 0)
        result_text = output.read_bytes().decode('utf-8')
        stdout_text = proc.stdout.decode('utf-8')
        for secret in ('SENTINEL', 'task body text', str(self.archive), str(self.root),
                       '1730000000', '00000000-0000-4000-8000', '/Users/'):
            self.assertNotIn(secret, result_text, secret)
            self.assertNotIn(secret, stdout_text, secret)
        self.assertIn(V.CONTENT_FREE_STATEMENT[:24], result_text)


class RealArchiveTests(unittest.TestCase):
    """Gated by CODEX_RESIDUAL_ARCHIVE_ROOT; unset => loud FAIL, never a silent skip."""

    def setUp(self):
        self.archive = os.environ.get(ARCHIVE_ENV)
        if not self.archive:
            self.fail('环境变量 %s 未设置：真实档案端到端测试拒绝静默跳过。'
                      '请将其指向私有档案根 launch-r1109 后重跑测试套件。' % ARCHIVE_ENV)

    def test_real_archive_end_to_end(self):
        result = V.analyze(REPO_ROOT, self.archive)
        self.assertTrue(result['hard_equality']['passed'])
        self.assertEqual(result['hard_equality']['checks_total'], 50)
        self.assertEqual(len(result['trace_bindings_verified']), 15)
        self.assertEqual(result['branch'], 'B-CONTENT-DRIFT')
        self.assertEqual(result['classification_counts'], {'content_drift': 10})
        expected_paths = {'metadata': {'payload.id'},
                          'content': {'payload.internal_chat_message_metadata_passthrough.create_time',
                                      'payload.internal_chat_message_metadata_passthrough.turn_id'}}
        for case in V.CASES:
            for role in V.ROLES_COMPARED:
                record = result['groups'][case][role]
                self.assertFalse(record['count_mismatch'], (case, role))
                self.assertEqual(set(record['counts'].values()), {1 if role == 'developer' else 2})
                self.assertEqual(set(record['paths_metadata']), expected_paths['metadata'])
                self.assertEqual(set(record['paths_content']), expected_paths['content'])
        for target in result['target_residuals']:
            self.assertEqual(target['status'], 'localized_content', target['group'])
            deltas = set(target['slot_pair_deltas'].values())
            self.assertTrue(deltas <= {-1, 0, 1}, target)
            self.assertIn(-1, deltas, target['group'])
        dumped = V.dump_result(result).decode('utf-8')
        self.assertNotIn(str(self.archive), dumped)
        self.assertNotIn('/Users/', dumped)

    def test_stored_package_result_matches_fresh_analysis(self):
        result = V.analyze(REPO_ROOT, self.archive)
        stored_path = HERE / 'result.json'
        self.assertTrue(stored_path.is_file(),
                        '包内正式 result.json 缺失：应由 verify.py --output 生成后存入')
        stored = json.loads(stored_path.read_bytes().decode('utf-8'))
        self.assertEqual(stored.get('schema'), V.RESULT_SCHEMA)
        fresh = dict(result)
        stored_copy = dict(stored)
        # baseline_commit tracks the moving HEAD; every other byte-level field must match.
        fresh.pop('baseline_commit')
        stored_copy.pop('baseline_commit')
        self.assertEqual(json.dumps(fresh, sort_keys=True),
                         json.dumps(stored_copy, sort_keys=True))
        self.assertRegex(stored.get('baseline_commit', ''), r'[0-9a-f]{40}')


if __name__ == '__main__':
    unittest.main(verbosity=2)
