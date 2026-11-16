#!/usr/bin/env python3
"""Tests for Codex元数据值语义-2026-11-16 verify.py.

- Synthetic fixtures build a full mini repo (frozen README bytes + synthetic
  ring-7 result.json) and a synthetic 15-slot archive, so every frozen
  behavior is exercised offline without touching the real archive.
- Real-archive end-to-end tests are gated by env CODEX_META_SEM_ARCHIVE_ROOT
  in the form "root1:root2" (os.pathsep-separated independent copies of the
  frozen launch-r1109 archive root); unset => loud FAIL, never a silent skip.

python3 test_verify.py and python3 -O test_verify.py must both stay green:
verify.py uses no asserts, and these tests avoid depending on assert
semantics for the code under test.
"""

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
VERIFY = HERE / 'verify.py'
REAL_README = HERE / 'README.md'
STORED_RESULT = HERE / 'result.json'
ENV_VAR = 'CODEX_META_SEM_ARCHIVE_ROOT'

sys.path.insert(0, str(HERE))
import verify as V  # noqa: E402

FIRST_ISO = '2026-11-09T04:57:04.786Z'
FIRST_EPOCH = 1794200224.786  # epoch seconds of FIRST_ISO (UTC)
TEXT_SENTINELS = ['DEVELOPER-SENTINEL-BODY', 'USER-K0-SENTINEL-BODY',
                  'USER-K1-SENTINEL-BODY']
CASES = V.CASES
REPS = V.REPS
ROLES = V.ROLES


def slot_id(case, rep):
    return 'codex__%s__r%d' % (case, rep)


def iso_utc(epoch):
    import datetime
    dt = datetime.datetime.fromtimestamp(epoch, tz=datetime.timezone.utc)
    return dt.strftime('%Y-%m-%dT%H:%M:%S.') + '%03dZ' % (dt.microsecond // 1000)


# --- synthetic fixture ---------------------------------------------------------

def rollout_messages(case, rep, *, ct_unit, ct_offset, dup_id=None,
                     mutate_text=None, extra_key=None, equal_ct_role_k=None):
    """Three developer+user message payloads for one synthetic slot."""
    # create_time must differ across reps so the per-slot value-drift union
    # keeps the create_time path (hard equality vs ring-7 requires it).
    ct_value = FIRST_EPOCH + ct_offset + rep * 1.0
    if ct_unit == 'epoch_milliseconds':
        ct_value = (ct_value) * 1000.0
    elif ct_unit == 'iso8601_utc':
        ct_value = iso_utc(FIRST_EPOCH + ct_offset + rep * 1.0)
    turn = 'turn-%s-r%d' % (case, rep)
    specs = [('developer', 0, TEXT_SENTINELS[0]),
             ('user', 0, TEXT_SENTINELS[1]),
             ('user', 1, TEXT_SENTINELS[2])]
    payloads = []
    for role, k, sentinel in specs:
        if mutate_text and mutate_text['slot'] == (case, rep) \
                and mutate_text['role'] == role and mutate_text['k'] == k:
            sentinel = 'TAMPERED-TEXT'
        pid = 'msg-%s-r%d-%s-k%d' % (case, rep, role, k)
        if dup_id and dup_id['slot'] == (case, rep) \
                and dup_id['role'] == role and dup_id['k'] == k:
            src = dup_id['from']  # (case, rep) to copy the id from
            pid = 'msg-%s-r%d-%s-k%d' % (src[0], src[1], role, k)
        payload = {
            'type': 'message',
            'role': role,
            'id': pid,
            'content': [{'type': 'input_text', 'text': sentinel}],
            'internal_chat_message_metadata_passthrough': {
                'content_item_kinds': ['input_text'],
                'create_time': ct_value,
                'turn_id': turn,
            },
        }
        if equal_ct_role_k and equal_ct_role_k[0] == role and equal_ct_role_k[1] == k:
            payload['internal_chat_message_metadata_passthrough']['create_time'] = \
                equal_ct_role_k[2]
        if extra_key and extra_key['slot'] == (case, rep) \
                and extra_key['role'] == role and extra_key['k'] == k:
            payload['extra_key'] = 'extra-%s-r%d' % (case, rep)
        payloads.append(payload)
    return payloads


def write_rollout(path, case, rep, first_iso, messages):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [{'timestamp': first_iso, 'ordinal': 0, 'type': 'session_meta',
              'payload': {'session_id': 'sess-%s-r%d' % (case, rep)}}]
    for ordinal, payload in enumerate(messages, start=1):
        lines.append({'timestamp': first_iso, 'ordinal': ordinal,
                      'type': 'response_item', 'payload': payload})
    raw = '\n'.join(json.dumps(x, ensure_ascii=False, sort_keys=True)
                    for x in lines).encode('utf-8') + b'\n'
    path.write_bytes(raw)
    return raw


def build_fixture(base, *, ct_unit='epoch_seconds', ct_offset=0.05,
                  dup_id=None, mutate_text=None, extra_key=None,
                  equal_ct_role_k=None, upstream_schema=None,
                  upstream_extra_path=None):
    """Full synthetic repo + archive; returns (root, archive)."""
    base = Path(base)
    root = base / 'repo'
    archive = base / 'archive'
    (root / '.git' / 'refs' / 'heads').mkdir(parents=True)
    (root / '.git' / 'HEAD').write_text('ref: refs/heads/main\n', encoding='utf-8')
    (root / '.git' / 'refs' / 'heads' / 'main').write_text(
        '1234567890abcdef1234567890abcdef12345678\n', encoding='utf-8')
    package = root / V.HERE
    package.mkdir(parents=True)
    shutil.copyfile(REAL_README, package / 'README.md')
    upstream_package = root / V.UPSTREAM_PACKAGE
    upstream_package.mkdir(parents=True)

    bindings = []
    for case in CASES:
        for rep in REPS:
            slot = slot_id(case, rep)
            messages = rollout_messages(
                case, rep, ct_unit=ct_unit, ct_offset=ct_offset,
                dup_id=dup_id, mutate_text=mutate_text, extra_key=extra_key,
                equal_ct_role_k=equal_ct_role_k)
            rel = 'codex/runs/%s/agent-session/rollout-%s.jsonl' % (slot, slot)
            raw = write_rollout(archive / rel, case, rep, FIRST_ISO, messages)
            bindings.append({'slot': slot,
                             'file': rel.rsplit('/', 1)[-1],
                             'archive_relative_path': rel,
                             'sha256_verified': V.sha_hex(raw)})

    groups = {}
    for case in CASES:
        unit = {}
        for role in ROLES:
            # Real ring-7 shape: developer contributes one message (k0 only),
            # user contributes two (k0/k1).
            ks = (0,) if role == 'developer' else (0, 1)
            paths_meta = {'payload.id': 'top-level pinned envelope key: id'}
            paths_content = {
                'payload.internal_chat_message_metadata_passthrough.create_time':
                    'ambiguous under the frozen letter; conservative content side',
                'payload.internal_chat_message_metadata_passthrough.turn_id':
                    'ambiguous under the frozen letter; conservative content side',
            }
            if extra_key:
                paths_content['payload.extra_key'] = 'ambiguous key; content side'
            diffs = []
            for k in ks:
                byte_len = 100 if k == 0 else 200
                entries = [{'path': p} for p in sorted(paths_meta)]
                entries += [{'path': p} for p in sorted(paths_content)]
                slot_pairs = []
                names = [slot_id(case, r) for r in REPS]
                for i, j in ((0, 1), (0, 2), (1, 2)):
                    slot_pairs.append({'byte_lengths': {names[i]: byte_len,
                                                        names[j]: byte_len},
                                       'entries': entries})
                diffs.append({'k': k, 'slot_pairs': slot_pairs})
            unit[role] = {'paths_metadata': paths_meta,
                          'paths_content': paths_content,
                          'diffs': diffs}
        groups[case] = unit

    upstream = {'schema': upstream_schema or V.UPSTREAM_SCHEMA,
                'branch': 'B-CONTENT-DRIFT',
                'baseline_commit': '8c5a481ccccf1d0109adf570a1c437db01fc6439',
                'preregistration': {'sha256': '4' * 64},
                'trace_bindings_verified': bindings,
                'groups': groups}
    (upstream_package / 'result.json').write_bytes(
        (json.dumps(upstream, ensure_ascii=False, indent=1, sort_keys=True)
         + '\n').encode('utf-8'))
    return root, archive


def run_cli(root, archive, output=None):
    cmd = [sys.executable, str(VERIFY), '--root', str(root),
           '--archive-root', str(archive)]
    if output is not None:
        cmd += ['--output', str(output)]
    proc = subprocess.run(cmd, capture_output=True)
    return proc.returncode, proc.stdout, proc.stderr


class FixtureTestCase(unittest.TestCase):
    """Base class building one fresh synthetic world per test."""

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix='codexmeta-fixture-'))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.root, self.archive = build_fixture(self.base)

    def analyze(self, root=None, archive=None):
        return V.analyze(root or self.root, archive or self.archive)


class TimeParsingTests(unittest.TestCase):
    """V1/V2 time parsing: epoch seconds, epoch millis, ISO; negatives."""

    def test_parse_epoch_seconds(self):
        epoch, unit = V.parse_any_timestamp(FIRST_EPOCH)
        self.assertEqual(unit, 'epoch_seconds')
        self.assertAlmostEqual(epoch, FIRST_EPOCH, places=3)

    def test_parse_epoch_millis_divides_by_thousand(self):
        epoch, unit = V.parse_any_timestamp(FIRST_EPOCH * 1000.0)
        self.assertEqual(unit, 'epoch_milliseconds')
        self.assertAlmostEqual(epoch, FIRST_EPOCH, places=3)

    def test_parse_iso_z(self):
        epoch, unit = V.parse_any_timestamp(FIRST_ISO)
        self.assertEqual(unit, 'iso8601_utc')
        self.assertAlmostEqual(epoch, FIRST_EPOCH, places=3)

    def test_parse_iso_offset(self):
        epoch, _ = V.parse_any_timestamp('2026-11-09T12:57:04.786+08:00')
        self.assertAlmostEqual(epoch, FIRST_EPOCH, places=3)

    def test_negative_garbage_string(self):
        with self.assertRaises(V.Invalid):
            V.parse_any_timestamp('not-a-timestamp')

    def test_negative_out_of_window_number(self):
        with self.assertRaises(V.Invalid):
            V.parse_any_timestamp(42.0)
        with self.assertRaises(V.Invalid):
            V.parse_any_timestamp(True)


class ClassifyValuesTests(unittest.TestCase):
    """V3 frozen three-way relation."""

    def test_equal(self):
        self.assertEqual(V.classify_values(['a', 'a', 'a']), 'equal')

    def test_increasing_numeric_strings(self):
        self.assertEqual(V.classify_values(['1', '5', '9']), 'increasing')

    def test_all_distinct_non_numeric(self):
        self.assertEqual(V.classify_values(['u1', 'u2', 'u3']), 'all-distinct')


class ConfirmedBranchTests(FixtureTestCase):

    def test_confirmed_branch_and_value_surface(self):
        code, stdout, stderr = run_cli(self.root, self.archive)
        self.assertEqual(code, 0, stderr)
        self.assertEqual(stderr, b'')
        result = self.analyze()
        self.assertEqual(result['schema'], V.RESULT_SCHEMA)
        self.assertEqual(result['branch'], 'B-METADATA-CONFIRMED')
        self.assertTrue(result['v1']['pass'])
        self.assertEqual(result['v1']['registered_formats'],
                         {'epoch_seconds': 45})
        self.assertTrue(result['v2']['pass'])
        self.assertEqual(result['v2']['slots_within_bound'], 15)
        self.assertLess(result['v2']['worst_abs_delta_seconds'], 10.0)
        self.assertTrue(result['v3']['cross_slot_consistent'])
        self.assertEqual(result['v3']['pattern_multiset'], {'equal': 15})
        for across in result['v3']['across_rep'].values():
            self.assertTrue(across['per_rep_turn_id_sets_disjoint'])
        self.assertTrue(result['v4']['pass'])
        self.assertEqual(result['v4']['rate'], 1.0)
        self.assertTrue(result['v5']['supported'])
        self.assertTrue(result['v5']['registrational_only'])
        self.assertTrue(result['hard_equality']['key_paths_vs_ring7']['passed'])
        self.assertTrue(result['hard_equality']['content_text_zero_diff']['passed'])

    def test_stdout_and_result_deterministic(self):
        out1 = Path(self.base / 'r1.json')
        out2 = Path(self.base / 'r2.json')
        code1, so1, se1 = run_cli(self.root, self.archive, out1)
        code2, so2, se2 = run_cli(self.root, self.archive, out2)
        self.assertEqual((code1, code2), (0, 0), (se1, se2))
        self.assertEqual(so1, so2, '双档 stdout 应逐字节一致')
        self.assertEqual(out1.read_bytes(), out2.read_bytes(),
                         'result.json 应逐字节一致')


class V2BoundaryTests(FixtureTestCase):
    """Frozen bound: |Δ| <= 120s passes, 121s fails the slot."""

    def test_delta_120_seconds_passes(self):
        code, _so, stderr = run_cli(self.root, self.archive)
        self.assertEqual(code, 0, stderr)
        result = self.analyze()
        self.assertEqual(result['branch'], 'B-METADATA-CONFIRMED')

        # Rebuild with offsets straddling the bound: rep deltas are 118/119/120
        # seconds, so the worst slot sits exactly on the inclusive 120s bound.
        base2 = Path(tempfile.mkdtemp(prefix='codexmeta-b120-'))
        self.addCleanup(shutil.rmtree, base2, True)
        root2, archive2 = build_fixture(base2, ct_offset=117.0)
        result2 = V.analyze(root2, archive2)
        self.assertTrue(result2['v2']['pass'])
        self.assertEqual(result2['v2']['slots_within_bound'], 15)
        self.assertAlmostEqual(result2['v2']['worst_abs_delta_seconds'], 120.0,
                               places=6)
        self.assertEqual(result2['branch'], 'B-METADATA-CONFIRMED')

    def test_delta_121_seconds_fails_bound_and_downgrades_branch(self):
        base = Path(tempfile.mkdtemp(prefix='codexmeta-b121-'))
        self.addCleanup(shutil.rmtree, base, True)
        # rep deltas 119.5/120.5/121.5: rep1 inside, rep2/rep3 over 120s, so
        # every slot has at least one failing rep -> slots_within_bound == 0.
        root, archive = build_fixture(base, ct_offset=118.5)
        code, _so, stderr = run_cli(root, archive)
        self.assertEqual(code, 0, stderr)
        result = V.analyze(root, archive)
        self.assertFalse(result['v2']['pass'])
        # r1 slots (119.5s) pass whole-slot; r2 (120.5s) / r3 (121.5s) fail.
        self.assertEqual(result['v2']['slots_within_bound'], 5)
        self.assertAlmostEqual(result['v2']['worst_abs_delta_seconds'], 121.5,
                               places=6)
        self.assertEqual(result['branch'], 'B-MIXED')
        self.assertFalse(result['per_key_verdict'][V.PATH_CREATE_TIME]['v2'])

    def test_millisecond_create_time_units_aligned(self):
        base = Path(tempfile.mkdtemp(prefix='codexmeta-ms-'))
        self.addCleanup(shutil.rmtree, base, True)
        root, archive = build_fixture(base, ct_unit='epoch_milliseconds',
                                      ct_offset=0.05)
        code, _so, stderr = run_cli(root, archive)
        self.assertEqual(code, 0, stderr)
        result = V.analyze(root, archive)
        self.assertEqual(result['v1']['registered_formats'],
                         {'epoch_milliseconds': 45})
        self.assertTrue(result['v2']['pass'], '毫秒需与首事件单位对齐后仍有界')
        self.assertLess(result['v2']['worst_abs_delta_seconds'], 10.0)
        self.assertEqual(result['branch'], 'B-METADATA-CONFIRMED')


class BranchDegradationTests(FixtureTestCase):
    """Per-key degradation: V4 dup / V1 unparseable / all-fail => REFUTED."""

    def test_v4_duplicate_id_gives_mixed(self):
        base = Path(tempfile.mkdtemp(prefix='codexmeta-dup-'))
        self.addCleanup(shutil.rmtree, base, True)
        # r2 developer k0 carries r1's id: paths union keeps payload.id (r3
        # still differs), hard equality passes, V4 drops below 100%.
        root, archive = build_fixture(
            base, dup_id={'slot': (CASES[0], 2), 'role': 'developer', 'k': 0,
                          'from': (CASES[0], 1)})
        code, _so, stderr = run_cli(root, archive)
        self.assertEqual(code, 0, stderr)
        result = V.analyze(root, archive)
        self.assertTrue(result['hard_equality']['key_paths_vs_ring7']['passed'])
        self.assertFalse(result['v4']['pass'])
        self.assertLess(result['v4']['rate'], 1.0)
        self.assertEqual(result['branch'], 'B-MIXED')
        self.assertFalse(result['per_key_verdict'][V.PATH_ID]['v4'])
        self.assertTrue(result['v1']['pass'])
        self.assertTrue(result['v2']['pass'])

    def test_v1_unparseable_create_time_is_registered_not_fatal(self):
        base = Path(tempfile.mkdtemp(prefix='codexmeta-badct-'))
        self.addCleanup(shutil.rmtree, base, True)
        root, archive = build_fixture(base)
        # Corrupt one slot's create_time value in place (same bytes-ish shape).
        slot_dir = archive / 'codex' / 'runs' / slot_id(CASES[0], 1) / 'agent-session'
        rollout = next(slot_dir.glob('rollout-*.jsonl'))
        lines = rollout.read_bytes().decode('utf-8').splitlines()
        fixed = []
        for line in lines:
            event = json.loads(line)
            payload = event.get('payload') or {}
            meta = payload.get('internal_chat_message_metadata_passthrough')
            if isinstance(meta, dict) and 'create_time' in meta:
                meta['create_time'] = 'when-the-town-sleeps'
            fixed.append(json.dumps(event, ensure_ascii=False, sort_keys=True))
        rollout.write_bytes(('\n'.join(fixed) + '\n').encode('utf-8'))
        # Refresh the binding SHA so only the value semantics are under test.
        self.refresh_binding_sha(archive, root)
        code, stdout_raw, stderr = run_cli(root, archive)
        self.assertEqual(code, 0, stderr)
        result = V.analyze(root, archive)
        self.assertFalse(result['v1']['pass'])
        self.assertEqual(result['v1']['parseable_values'],
                         result['v1']['total_values'] - 3)
        # The broken slot fails as a whole; V2's frozen tolerance (>=14/15)
        # still holds, so V2 passes while V1 fails -> B-MIXED, and the raw
        # unparseable string never leaks into the released result.
        self.assertTrue(result['v2']['pass'])
        self.assertEqual(result['v2']['slots_within_bound'], 14)
        self.assertEqual(result['branch'], 'B-MIXED')
        self.assertFalse(result['per_key_verdict'][V.PATH_CREATE_TIME]['v1'])
        # The raw unparseable value is registrable in value_matrix (key values
        # are releasable metadata), but the stdout summary must stay aggregate.
        self.assertNotIn(b'when-the-town-sleeps', stdout_raw)

    def test_all_keys_fail_gives_refuted(self):
        base = Path(tempfile.mkdtemp(prefix='codexmeta-refuted-'))
        self.addCleanup(shutil.rmtree, base, True)
        root, archive = build_fixture(base)
        # Break V4 for every group (r2 inherits r1 ids) and V1/V2 for one case,
        # so V1 fails, V2 fails and V4 fails simultaneously.
        for case in CASES:
            for role in ('developer', 'user'):
                for k in (0, 1):
                    pass
        for case in CASES:
            for rep in (2,):
                slot_dir = archive / 'codex' / 'runs' / slot_id(case, rep) / 'agent-session'
                rollout = next(slot_dir.glob('rollout-*.jsonl'))
                lines = rollout.read_bytes().decode('utf-8').splitlines()
                fixed = []
                for line in lines:
                    event = json.loads(line)
                    payload = event.get('payload') or {}
                    meta = payload.get('internal_chat_message_metadata_passthrough')
                    if isinstance(meta, dict):
                        src = 'msg-%s-r1-%s-k%%d' % (case, payload.get('role'))
                        if payload.get('role') == 'developer':
                            payload['id'] = src % 0
                        else:
                            payload['id'] = src % (payload.get('k') or 0)
                        meta['create_time'] = 'broken-clock'
                    fixed.append(json.dumps(event, ensure_ascii=False, sort_keys=True))
                rollout.write_bytes(('\n'.join(fixed) + '\n').encode('utf-8'))
        self.refresh_binding_sha(archive, root)
        code, _so, stderr = run_cli(root, archive)
        self.assertEqual(code, 0, stderr)
        result = V.analyze(root, archive)
        self.assertTrue(result['hard_equality']['key_paths_vs_ring7']['passed'])
        self.assertFalse(result['v1']['pass'])
        self.assertFalse(result['v2']['pass'])
        self.assertFalse(result['v4']['pass'])
        self.assertEqual(result['branch'], 'B-REFUTED')

    def refresh_binding_sha(self, archive, root):
        upstream_path = root / V.UPSTREAM_RESULT_REL
        upstream = json.loads(upstream_path.read_bytes().decode('utf-8'))
        for binding in upstream['trace_bindings_verified']:
            raw = (archive / binding['archive_relative_path']).read_bytes()
            binding['sha256_verified'] = V.sha_hex(raw)
        upstream_path.write_bytes(
            (json.dumps(upstream, ensure_ascii=False, indent=1, sort_keys=True)
             + '\n').encode('utf-8'))


class V5RegistrationalTests(FixtureTestCase):

    def test_equal_value_on_stable_pair_registered_without_branch_break(self):
        base = Path(tempfile.mkdtemp(prefix='codexmeta-v5-'))
        self.addCleanup(shutil.rmtree, base, True)
        root, archive = build_fixture(base)
        # Make lcb-recent-hard-4 r1|r2 developer create_time identical (both
        # equal r2's original value): the stable pair keeps equal byte
        # lengths, V5 registers the equality, the branch must NOT break
        # (registrational only), and r1|r3 still differ so the per-slot
        # drift-path union keeps create_time.
        equal_ct = FIRST_EPOCH + 0.05 + 2 * 1.0
        for rep in (1, 2):
            slot_dir = archive / 'codex' / 'runs' / slot_id('lcb-recent-hard-4', rep) / 'agent-session'
            rollout = next(slot_dir.glob('rollout-*.jsonl'))
            lines = rollout.read_bytes().decode('utf-8').splitlines()
            fixed = []
            for line in lines:
                event = json.loads(line)
                payload = event.get('payload') or {}
                meta = payload.get('internal_chat_message_metadata_passthrough')
                if isinstance(meta, dict) and payload.get('role') == 'developer':
                    meta['create_time'] = equal_ct
                fixed.append(json.dumps(event, ensure_ascii=False, sort_keys=True))
            rollout.write_bytes(('\n'.join(fixed) + '\n').encode('utf-8'))
        self.refresh_binding_sha(archive, root)
        code, _so, stderr = run_cli(root, archive)
        self.assertEqual(code, 0, stderr)
        result = V.analyze(root, archive)
        self.assertTrue(result['hard_equality']['key_paths_vs_ring7']['passed'],
                        '单元并集仍含 create_time 差（r1|r3 对），硬等应通过')
        self.assertFalse(result['v5']['supported'])
        self.assertTrue(result['v5']['registrational_only'])
        self.assertTrue(result['v5']['per_pair_keys'])
        self.assertEqual(result['branch'], 'B-METADATA-CONFIRMED')

    def refresh_binding_sha(self, archive, root):
        upstream_path = root / V.UPSTREAM_RESULT_REL
        upstream = json.loads(upstream_path.read_bytes().decode('utf-8'))
        for binding in upstream['trace_bindings_verified']:
            raw = (archive / binding['archive_relative_path']).read_bytes()
            binding['sha256_verified'] = V.sha_hex(raw)
        upstream_path.write_bytes(
            (json.dumps(upstream, ensure_ascii=False, indent=1, sort_keys=True)
             + '\n').encode('utf-8'))


class FailClosedTests(FixtureTestCase):
    """Every anti-tamper path must exit 2 and never write --output."""

    def run_expect_exit2(self, root=None, archive=None, output=None):
        code, _so, stderr = run_cli(root or self.root, archive or self.archive,
                                    output)
        self.assertEqual(code, 2, stderr)
        self.assertIn(b'FAIL-CLOSED', stderr)
        return stderr

    def refresh_binding_sha(self):
        upstream_path = self.root / V.UPSTREAM_RESULT_REL
        upstream = json.loads(upstream_path.read_bytes().decode('utf-8'))
        for binding in upstream['trace_bindings_verified']:
            raw = (self.archive / binding['archive_relative_path']).read_bytes()
            binding['sha256_verified'] = V.sha_hex(raw)
        upstream_path.write_bytes(
            (json.dumps(upstream, ensure_ascii=False, indent=1, sort_keys=True)
             + '\n').encode('utf-8'))

    def rewrite_rollout(self, case, rep, transform):
        slot_dir = self.archive / 'codex' / 'runs' / slot_id(case, rep) / 'agent-session'
        rollout = next(slot_dir.glob('rollout-*.jsonl'))
        lines = rollout.read_bytes().decode('utf-8').splitlines()
        fixed = []
        for line in lines:
            event = json.loads(line)
            transform(event)
            fixed.append(json.dumps(event, ensure_ascii=False, sort_keys=True))
        rollout.write_bytes(('\n'.join(fixed) + '\n').encode('utf-8'))

    def test_keypath_drift_exit2(self):
        # Collapse the payload.id difference across all three reps of one
        # unit: the re-extracted union loses payload.id while ring-7 still
        # registers it -> exit 2.
        def collapse(event):
            payload = event.get('payload') if isinstance(event.get('payload'), dict) else None
            if payload and payload.get('role') == 'developer':
                payload['id'] = 'msg-%s-collapsed' % CASES[0]
        self.rewrite_rollout(CASES[0], 1, collapse)
        self.rewrite_rollout(CASES[0], 2, collapse)
        self.rewrite_rollout(CASES[0], 3, collapse)
        self.refresh_binding_sha()
        self.run_expect_exit2()

    def test_text_tamper_exit2(self):
        self.rewrite_rollout(CASES[1], 2,
                             lambda e: e['payload']['content'][0].update(
                                 text='TAMPERED-TEXT')
                             if isinstance(e.get('payload'), dict)
                             and e['payload'].get('role') == 'user' else None)
        self.refresh_binding_sha()
        self.run_expect_exit2()

    def test_extra_diff_key_exit2(self):
        self.rewrite_rollout(CASES[2], 1,
                             lambda e: e['payload'].update(
                                 surprise='extra-%d' % 1)
                             if isinstance(e.get('payload'), dict)
                             and e['payload'].get('role') == 'developer' else None)
        self.refresh_binding_sha()
        self.run_expect_exit2()

    def test_trace_sha_tamper_exit2(self):
        rollout = self.archive / 'codex' / 'runs' / slot_id(CASES[3], 2) / 'agent-session'
        target = next(rollout.glob('rollout-*.jsonl'))
        target.write_bytes(target.read_bytes() + b'{"timestamp":"2026-11-09T05:00:00.000Z","ordinal":999}\n')
        self.run_expect_exit2()

    def test_readme_sha_tamper_exit2(self):
        readme = self.root / V.HERE / 'README.md'
        readme.write_bytes(readme.read_bytes() + b'\n')
        self.run_expect_exit2()

    def test_upstream_schema_tamper_exit2(self):
        path = self.root / V.UPSTREAM_RESULT_REL
        upstream = json.loads(path.read_bytes().decode('utf-8'))
        upstream['schema'] = 'some-other-schema'
        path.write_bytes(json.dumps(upstream).encode('utf-8'))
        self.run_expect_exit2()

    def test_upstream_registered_paths_tamper_exit2(self):
        path = self.root / V.UPSTREAM_RESULT_REL
        upstream = json.loads(path.read_bytes().decode('utf-8'))
        upstream['groups'][CASES[4]]['user']['paths_metadata']['payload.bogus'] = 'x'
        path.write_bytes(json.dumps(upstream).encode('utf-8'))
        self.run_expect_exit2()

    def test_output_refuses_overwrite(self):
        out = self.base / 'result.json'
        code1, _so, se1 = run_cli(self.root, self.archive, out)
        self.assertEqual(code1, 0, se1)
        first = out.read_bytes()
        code2, _so, se2 = run_cli(self.root, self.archive, out)
        self.assertEqual(code2, 2)
        self.assertIn(b'refuses to overwrite', se2)
        self.assertEqual(out.read_bytes(), first, '已存在文件必须零字节变动')

    def test_release_boundary_no_content_values(self):
        out = self.base / 'result.json'
        code, stdout, _se = run_cli(self.root, self.archive, out)
        self.assertEqual(code, 0)
        result_bytes = out.read_bytes()
        for blob, name in ((result_bytes, 'result'), (stdout, 'stdout')):
            text = blob.decode('utf-8')
            for sentinel in TEXT_SENTINELS + ['TAMPERED']:
                self.assertNotIn(sentinel, text, (name, sentinel))
            self.assertNotIn('/Users/', text, name)
            self.assertNotIn(str(self.archive), text, name)
            self.assertNotIn('bench-private', text, name)
        obj = json.loads(result_bytes.decode('utf-8'))
        self.assertIn('release_boundary_statement', obj)
        self.assertIn('evidence_grade', obj)
        self.assertEqual(obj['inputs']['archive_root_marker'], 'launch-r1109')


# --- real-archive end-to-end (dual-root gated) --------------------------------

class RealArchiveTests(unittest.TestCase):
    """Gated by CODEX_META_SEM_ARCHIVE_ROOT="root1:root2"; unset => loud FAIL."""

    def _roots(self):
        raw = os.environ.get(ENV_VAR)
        if not raw:
            self.fail('%s 未设置：真档案端到端用例拒绝静默跳过。'
                      '应设为 "root1%sroot2" 形式（os.pathsep 分隔的冻结档案根'
                      ' launch-r1109 的两个独立副本）。' % (ENV_VAR, os.pathsep))
        parts = [p for p in raw.split(os.pathsep) if p]
        if len(parts) != 2:
            self.fail('%s 应含恰 2 个根（%s 分隔），实得 %d 个'
                      % (ENV_VAR, os.pathsep, len(parts)))
        roots = [Path(p) for p in parts]
        for r in roots:
            if not (r / 'codex' / 'runs').is_dir():
                self.fail('真档案根下无 codex/runs/: %s' % r)
        return roots

    def test_real_archive_dual_roots_byte_identical(self):
        roots = self._roots()
        tmp = Path(tempfile.mkdtemp(prefix='codexmeta-real-'))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        stdouts, results = [], []
        for i, root in enumerate(roots):
            out = tmp / ('result-%d.json' % i)
            code, so, se = run_cli(REPO_ROOT, root, out)
            self.assertEqual(se, b'', 'stderr 应为空: %s' % se)
            self.assertEqual(code, 0, so)
            stdouts.append(so)
            results.append(out.read_bytes())
        self.assertEqual(stdouts[0], stdouts[1], '双根 stdout 应逐字节一致')
        self.assertEqual(results[0], results[1], '双根 result.json 应逐字节一致')
        if not STORED_RESULT.is_file():
            self.fail('包内 result.json 缺失（应由 --output 生成后入库）')
        self.assertEqual(results[0], STORED_RESULT.read_bytes(),
                         'fresh --output 应与存储 result.json 逐字节一致')
        text = results[0].decode('utf-8')
        self.assertNotIn('/Users/', text)
        self.assertNotIn('bench-private', text)
        obj = json.loads(text)
        self.assertEqual(obj['schema'], V.RESULT_SCHEMA)
        self.assertEqual(obj['branch'], 'B-METADATA-CONFIRMED')
        self.assertTrue(obj['preregistration']['sha256_verified'])
        self.assertEqual(obj['preregistration']['sha256'], V.PREREG_SHA256)
        self.assertTrue(obj['hard_equality']['key_paths_vs_ring7']['passed'])
        self.assertTrue(obj['hard_equality']['content_text_zero_diff']['passed'])
        self.assertEqual(obj['inputs']['archive_root_marker'], 'launch-r1109')
        self.assertEqual(obj['inputs']['upstream_branch'], 'B-CONTENT-DRIFT')

    def test_real_archive_value_surface_numbers(self):
        roots = self._roots()
        result = V.analyze(REPO_ROOT, roots[0])
        self.assertEqual(result['v1']['total_values'], 45)
        self.assertEqual(result['v1']['parseable_values'], 45)
        self.assertEqual(result['v1']['registered_formats'], {'epoch_seconds': 45})
        self.assertTrue(result['v2']['pass'])
        self.assertEqual(result['v2']['slots_within_bound'], 15)
        self.assertLess(result['v2']['worst_abs_delta_seconds'], 120.0)
        self.assertEqual(result['v3']['pattern_multiset'], {'equal': 15})
        self.assertTrue(result['v3']['cross_slot_consistent'])
        self.assertTrue(all(a['per_rep_turn_id_sets_disjoint']
                            for a in result['v3']['across_rep'].values()))
        self.assertEqual(result['v4']['all_distinct_groups'],
                         result['v4']['total_groups'])
        self.assertEqual(result['v4']['rate'], 1.0)
        self.assertEqual(result['v5']['stable_pairs'], 37)
        self.assertEqual(result['v5']['checks'], 111)
        self.assertTrue(result['v5']['supported'])
        self.assertEqual(len(result['hard_equality']['key_paths_vs_ring7']['per_unit']), 10)
        self.assertEqual(len(result['hard_equality']['trace_bindings_verified']), 15)
        self.assertEqual(result['evidence_grade'], V.EVIDENCE_GRADE)
        self.assertEqual(result['release_boundary_statement'],
                         V.RELEASE_BOUNDARY_STATEMENT)

    def test_real_archive_stored_result_matches_fresh_analysis(self):
        roots = self._roots()
        fresh = V.analyze(REPO_ROOT, roots[0])
        dumped = V.dump_result(fresh)
        if not STORED_RESULT.is_file():
            self.fail('包内 result.json 缺失（应由 --output 生成后入库）')
        self.assertEqual(dumped, STORED_RESULT.read_bytes(),
                         'fresh 分析应与存储 result.json 逐字节一致')
        obj = json.loads(dumped.decode('utf-8'))
        self.assertNotIn(str(roots[0]), dumped.decode('utf-8'))
        self.assertNotIn('/Users/', dumped.decode('utf-8'))
        self.assertEqual(obj['branch'], 'B-METADATA-CONFIRMED')


if __name__ == '__main__':
    unittest.main(verbosity=2)
