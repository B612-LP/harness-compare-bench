#!/usr/bin/env python3
"""Tests for the bird S4 per-round structure decomposition package.

Run under both `python3 test_verify.py` and `python3 -O test_verify.py`; both
modes must pass. Tests that need the real archived true-body traces read the
archive root from the environment variable B_BIRD_S4_ARCHIVE_ROOT; if it is
unset or wrong, those tests FAIL loudly instead of silently passing (no skips,
no approximations).

Only unittest assertion methods are used (no bare `assert` statements), so the
suite behaves identically with and without -O.
"""
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PKG_REL = '4-打分细则/bird交互量结构分解-2026-11-16'
OBS = '3-表现现场/r1109-bw-retest/observe'
BATCH = '3-表现现场/r1109-mech-n3'
V11_REL = '4-打分细则/机制重复口径澄清-2026-11-12'
ARCHIVE_ENV = 'B_BIRD_S4_ARCHIVE_ROOT'
SLOT = 'dsh__bird-ca-schools-15'
SLOTS = (SLOT + '__r1', SLOT + '__r2', SLOT + '__r3')
FROZEN_S4 = {SLOT + '__r1': 551905, SLOT + '__r2': 193745, SLOT + '__r3': 517142}

_spec = importlib.util.spec_from_file_location('bird_s4_verify', HERE / 'verify.py')
RV = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(RV)


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def synth_event(kind, **data):
    event = {'type': kind, 'data': data, 'seq': data.pop('seq', 0), 'time': 0}
    return event


def synth_trace(rounds=2, tool_names=None, assistant_sizes=None, dangling=False,
                missing_name_on=None, outside_assistant=False, outside_tool=False):
    """Synthetic v4-ish event stream with known canonical sizes."""
    events = [{'type': 'session', 'version': 4, 'id': 'synthetic', 'seq': 0, 'time': 0}]
    seq = 1
    tool_names = tool_names or [['bash'], ['read']]
    assistant_sizes = assistant_sizes or [100, 200]
    for step in range(1, rounds + 1):
        events.append(synth_event('step/start', step=step, turn=1, seq=seq))
        seq += 1
        size = assistant_sizes[step - 1] if step - 1 < len(assistant_sizes) else 10
        message = {'role': 'assistant', 'text': 'x' * size}
        events.append(synth_event('assistant/message', step=step, turn=1, seq=seq,
                                  message=message))
        seq += 1
        for name in tool_names[step - 1] if step - 1 < len(tool_names) else ['bash']:
            call = {'name': name, 'arguments': {'n': step}}
            if missing_name_on == (step, name):
                call = {'arguments': {'n': step}}
            events.append(synth_event('tool/call', step=step, turn=1, seq=seq, **call))
            seq += 1
        events.append(synth_event('step/end', step=step, turn=1, seq=seq))
        seq += 1
    if dangling:
        events.append(synth_event('step/start', step=rounds + 1, turn=1, seq=seq))
    if outside_assistant:
        events.append(synth_event('assistant/message', step=1, turn=1, seq=seq,
                                  message={'role': 'assistant', 'text': 'outside'}))
        seq += 1
    if outside_tool:
        events.append(synth_event('tool/call', step=1, turn=1, seq=seq,
                                  name='bash', arguments={'n': 'outside'}))
    return events


class WindowAccountingTests(unittest.TestCase):
    """(a) Round-window accounting incl. outside-window bucket, on synthetic bytes."""

    def test_a_round_window_accounting_with_outside_bucket(self):
        events = synth_trace(rounds=2, tool_names=[['bash'], ['read', 'bash']],
                             assistant_sizes=[100, 200],
                             outside_assistant=True, outside_tool=True)
        out = RV.window_rounds(events, 'synthetic-slot')
        self.assertEqual(out['round_order'], [1, 2])
        inside_bytes = {}
        current = None
        for event in events:
            if event['type'] == 'step/start':
                current = event['data']['step']
                inside_bytes[current] = 0
            elif event['type'] == 'step/end':
                current = None
            elif event['type'] in ('assistant/message', 'tool/call') and current is not None:
                inside_bytes[current] += len(canon(event))
        self.assertEqual(out['round_bytes'], [inside_bytes[1], inside_bytes[2]])
        self.assertEqual(out['s4_total'], inside_bytes[1] + inside_bytes[2])
        # outside events are counted, never dropped, and excluded from the total
        self.assertEqual(out['outside_counts'], {'assistant/message': 1, 'tool/call': 1})
        self.assertEqual(out['outside_bytes']['assistant/message'],
                         len(canon(events[-2])))
        self.assertEqual(out['outside_bytes']['tool/call'], len(canon(events[-1])))
        self.assertNotIn(len(canon(events[-2])), [out['round_bytes'][0], out['round_bytes'][1]])
        self.assertEqual(out['name_sequence'], ['bash', 'read', 'bash'])
        self.assertEqual(out['assistant_message_bytes'], inside_bytes[1] + inside_bytes[2] -
                         sum(out['tool_bytes'].values()))

    def test_a_window_misalignment_and_dangling_fail_closed(self):
        with self.assertRaises(RV.Invalid) as caught:
            RV.window_rounds(synth_trace(rounds=1, dangling=True), 'slot')
        self.assertIn('unclosed step window', str(caught.exception))
        events = synth_trace(rounds=1)
        events[-1]['data']['step'] = 2  # step/end says 2, window 1 open
        with self.assertRaises(RV.Invalid) as caught:
            RV.window_rounds(events, 'slot')
        self.assertIn('misalignment', str(caught.exception))
        events = synth_trace(rounds=1)
        events.insert(3, synth_event('step/start', step=2, turn=1, seq=99))  # nested
        with self.assertRaises(RV.Invalid) as caught:
            RV.window_rounds(events, 'slot')
        self.assertIn('nested step/start', str(caught.exception))
        events = synth_trace(rounds=2)
        events[1]['data']['step'] = 2  # first window claims step 2 (non-contiguous)
        with self.assertRaises(RV.Invalid) as caught:
            RV.window_rounds(events, 'slot')
        self.assertIn('non-contiguous', str(caught.exception))
        events = synth_trace(rounds=1)
        events[3]['data']['step'] = 2  # inside event contradicts open window 1
        with self.assertRaises(RV.Invalid) as caught:
            RV.window_rounds(events, 'slot')
        self.assertIn('contradicts open window', str(caught.exception))

    def test_d_tool_call_without_name_stops(self):
        for kwargs in ({}, {'name': None}, {'name': ''}, {'name': 7}):
            events = synth_trace(rounds=1, tool_names=[['bash']])
            target = next(i for i, e in enumerate(events) if e['type'] == 'tool/call')
            for key in ('name',):
                events[target]['data'] = {'step': 1, 'turn': 1, 'arguments': {'n': 1}}
                if kwargs.get('name') is not None:
                    events[target]['data']['name'] = kwargs['name']
            with self.assertRaises(RV.Invalid) as caught:
                RV.window_rounds(events, 'slot')
            self.assertIn('tool/call without name field', str(caught.exception))

    def test_a_session_header_checks(self):
        events = synth_trace(rounds=1)
        events[0]['version'] = 3
        with self.assertRaises(RV.Invalid) as caught:
            RV.window_rounds(events, 'slot')
        self.assertIn('non-v4', str(caught.exception))
        events = synth_trace(rounds=1)
        events.append({'type': 'session', 'version': 4})
        with self.assertRaises(RV.Invalid) as caught:
            RV.window_rounds(events, 'slot')
        self.assertIn('bad session header', str(caught.exception))


class MetricEdgeTests(unittest.TestCase):
    """(e) top-5 share boundary (>0.5 vs ==0.5 -> H-B side); (f) LCP edges."""

    def test_e_top5_share_strict_greater_than_half(self):
        share, top5 = RV.top5_share([25] * 10)
        self.assertEqual(share, 0.5)
        self.assertEqual(top5, [25] * 5)
        self.assertFalse(share > 0.5, 'share == 0.5 must stay on the H-B diffuse side')
        share, top5 = RV.top5_share([100001] + [99999] * 4 + [99999] * 5)
        self.assertGreater(share, 0.5)
        self.assertEqual(top5, [100001] + [99999] * 4)
        share, _ = RV.top5_share([40, 15, 15, 15, 15])
        self.assertEqual(share, 1.0)
        with self.assertRaises(RV.Invalid):
            RV.top5_share([])
        with self.assertRaises(RV.Invalid):
            RV.top5_share([0, 0])
        with self.assertRaises(RV.Invalid):
            RV.top5_share([10, -1])

    def test_f_lcp_computation_and_empty_edges(self):
        self.assertEqual(RV.longest_common_prefix([[]]), 0)
        self.assertEqual(RV.longest_common_prefix([[], ['bash']]), 0)
        self.assertEqual(RV.longest_common_prefix([['bash'], ['bash'], ['bash']]), 1)
        self.assertEqual(RV.longest_common_prefix([['bash', 'read'], ['bash', 'read'],
                                                   ['bash', 'read']]), 2)
        self.assertEqual(RV.longest_common_prefix([['bash', 'read'], ['bash', 'bash'],
                                                   ['bash', 'read']]), 1)
        self.assertEqual(RV.longest_common_prefix([['bash'], ['bash', 'read'],
                                                   ['bash', 'read', 'read']]), 1,
                         'LCP stops at shortest sequence content, not shortest length')
        with self.assertRaises(RV.Invalid):
            RV.longest_common_prefix([])

    def test_f_lcp_matches_real_name_sequences(self):
        # name sequences captured from the 2026-11-16 dry run of the real archives
        r1 = ['bash', 'read'] + ['bash'] * 27
        r2 = ['bash'] * 16
        r3 = ['bash', 'read', 'read'] + ['bash'] + ['read'] + ['bash'] * 24
        self.assertEqual(len(r1), 29)
        self.assertEqual(len(r2), 16)
        self.assertEqual(len(r3), 29)
        self.assertEqual(RV.longest_common_prefix([r1, r2, r3]), 1)


class TempRootMixin:
    def build_temp_root(self):
        tmp = Path(tempfile.mkdtemp(prefix='bird-s4-root-'))
        needed = [PKG_REL + '/README.md', V11_REL + '/evidence.json',
                  V11_REL + '/result.json',
                  OBS + '/dsh-s3-s4-summary.json'] + \
                 [OBS + '/session-dsh-bird-ca-schools-15__r%d.json' % rep for rep in (1, 2, 3)] + \
                 [OBS + '/session-dsh__bird-ca-schools-15__r2.json'] + \
                 [BATCH + '/runs/' + slot + '/score-receipt.json' for slot in SLOTS]
        for relative in needed:
            source = ROOT / relative
            destination = tmp / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        # resolve_head reads .git files (no subprocess); give the temp root the real
        # repo's HEAD + refs so SHA-tamper tests reach the binding check itself.
        git_tmp = tmp / '.git'
        git_tmp.mkdir()
        shutil.copy2(ROOT / '.git' / 'HEAD', git_tmp / 'HEAD')
        shutil.copytree(ROOT / '.git' / 'refs', git_tmp / 'refs')
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        return tmp

    def archive(self):
        value = os.environ.get(ARCHIVE_ENV)
        if not value:
            self.fail(ARCHIVE_ENV + ' is not set; real archived-trace checks cannot run '
                      'and must not silently pass')
        path = Path(value)
        if not (path / 'dsh' / 'runs' / SLOTS[0] / 'agent-session').is_dir():
            self.fail(ARCHIVE_ENV + ' does not look like the r1109 launch archive root: ' + value)
        return path


class ExitDisciplineTests(TempRootMixin, unittest.TestCase):
    """(b) S4 mismatch -> 2; (c) skeleton mismatch -> 2; pinned-source tamper -> 2."""

    def test_b_s4_hard_equal_mismatch_trips(self):
        archive = self.archive()
        wrong = {slot: value + 1 for slot, value in FROZEN_S4.items()}
        with self.assertRaises(RV.Invalid) as caught:
            RV.analyze(ROOT, archive, expected_s4=wrong)
        message = str(caught.exception)
        self.assertIn('S4 hard-equal mismatch', message)
        self.assertIn(str(FROZEN_S4[SLOTS[0]]), message)

    def test_b_corrected_r2_s4_pin_mismatch_via_inject(self):
        # Tampering the file would trip the earlier source-SHA binding; the inject
        # hook replaces the parsed object after SHA binding, so this targets the
        # corrected-r2 S4 pin check specifically (analyze raises; main maps any
        # Invalid to exit 2, proven by test_b_tampered_pinned_source_exit_2).
        archive = self.archive()
        aggregate = json.loads((ROOT / OBS / 'session-dsh__bird-ca-schools-15__r2.json')
                               .read_text(encoding='utf-8'))
        aggregate['per_file'][0]['s4']['output_bytes'] = 193746
        inject = {OBS + '/session-dsh__bird-ca-schools-15__r2.json': aggregate}
        with self.assertRaises(RV.Invalid) as caught:
            RV.analyze(ROOT, archive, inject=inject)
        self.assertIn('corrected r2 aggregate S4 pin mismatch', str(caught.exception))

    def test_c_public_skeleton_mismatch_trips(self):
        archive = self.archive()
        aggregate = json.loads((ROOT / OBS / 'session-dsh-bird-ca-schools-15__r1.json')
                               .read_text(encoding='utf-8'))
        aggregate['per_file'][0]['s2']['type_counts']['assistant/message'] = 28
        inject = {OBS + '/session-dsh-bird-ca-schools-15__r1.json': aggregate}
        with self.assertRaises(RV.Invalid) as caught:
            RV.analyze(ROOT, archive, inject=inject)
        message = str(caught.exception)
        self.assertIn('public skeleton mismatch', message)
        self.assertIn('assistant/message', message)

    def test_b_tampered_pinned_source_exit_2(self):
        tmp = self.build_temp_root()
        target = tmp / OBS / 'dsh-s3-s4-summary.json'
        data = bytearray(target.read_bytes())
        self.assertGreater(len(data), 0, 'pinned source unexpectedly empty')
        data[0] ^= 0x01
        target.write_bytes(bytes(data))
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = RV.main(['--root', str(tmp), '--archive-root', str(ROOT)])
        self.assertEqual(code, 2, 'tampered pinned source must produce exit code 2')
        self.assertIn('source SHA mismatch', stderr.getvalue())

    def test_b_missing_score_receipt_field_stops(self):
        archive = self.archive()
        receipt = json.loads((ROOT / BATCH / 'runs' / SLOTS[2] / 'score-receipt.json')
                             .read_text(encoding='utf-8'))
        del receipt['reward']
        inject = {BATCH + '/runs/' + SLOTS[2] + '/score-receipt.json': receipt}
        with self.assertRaises(RV.Invalid) as caught:
            RV.analyze(ROOT, archive, inject=inject)
        self.assertIn('score receipt missing field reward', str(caught.exception))


class RealArchiveTests(TempRootMixin, unittest.TestCase):
    """(g) determinism; (h) real-archive end-to-end; stored result.json agreement."""

    def test_h_real_archive_end_to_end(self):
        archive = self.archive()
        result = RV.analyze(ROOT, archive)
        self.assertEqual(result['schema'], 'bird-s4-structure-projection-v1')
        self.assertEqual([row['rep'] for row in result['reps']], ['r1', 'r2', 'r3'])
        for row in result['reps']:
            self.assertTrue(row['s4_hard_equal_ok'])
            self.assertEqual(row['s4_total'], FROZEN_S4[row['slot']])
            self.assertEqual(row['outside_window_events'], {},
                             'real true-body traces have no outside-window S4 events')
        self.assertEqual([row['round_count'] for row in result['reps']], [29, 9, 27])
        self.assertEqual(result['verdicts']['concentrated_reps'], ['r2'])
        self.assertEqual(result['verdicts']['diffuse_reps'], ['r1', 'r3'])
        self.assertIn('mixed', result['verdicts']['concentration_verdict'])
        self.assertEqual(result['cross_rep']['lcp_three_way'], 1)
        self.assertEqual(result['cross_rep']['first_divergence']['call_index'], 1)
        self.assertEqual(result['verdicts']['structure_verdict'], 'early-divergence')
        self.assertEqual(result['public_skeleton_check']['ok'], True)
        self.assertEqual(result['corrected_r2_aggregate_check']['ok'], True)
        self.assertEqual(result['stale_record']['stale_r2_value_recorded'], 551905)

    def test_h_result_json_privacy_shape(self):
        archive = self.archive()
        result = RV.analyze(ROOT, archive)
        text = json.dumps(result, ensure_ascii=False, sort_keys=True)
        for marker in ('/Users/', 'bench-private'):
            self.assertNotIn(marker, text, 'privacy marker leaked into result.json: ' + marker)

        def keys_of(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    yield key
                    yield from keys_of(value)
            elif isinstance(node, list):
                for value in node:
                    yield from keys_of(value)
        for key in keys_of(result):
            self.assertNotEqual(key, 'arguments',
                                'tool-argument payload leaked into result.json')
        for row in result['reps']:
            self.assertFalse(row['archive_relative_path'].startswith('/'),
                             'absolute path leaked into result.json')
            self.assertTrue(row['archive_relative_path'].startswith('dsh/runs/'))

    def test_g_determinism_two_inprocess_runs(self):
        archive = self.archive()
        first = json.dumps(RV.analyze(ROOT, archive), ensure_ascii=False, sort_keys=True,
                           indent=2, allow_nan=False)
        second = json.dumps(RV.analyze(ROOT, archive), ensure_ascii=False, sort_keys=True,
                            indent=2, allow_nan=False)
        self.assertEqual(first, second, 'two in-process runs must be byte-identical')

    def test_g_cli_determinism_and_minus_o_identical(self):
        archive = self.archive()
        stdouts = []
        outputs = []
        for interpreter in (sys.executable,):
            for flags in ([], ['-O']):
                with tempfile.TemporaryDirectory() as tmp:
                    out_path = Path(tmp) / 'result.json'
                    proc = subprocess.run([interpreter] + flags + [str(HERE / 'verify.py'),
                                                                  '--root', str(ROOT),
                                                                  '--archive-root', str(archive),
                                                                  '--output', str(out_path)],
                                          capture_output=True, text=True)
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    stdouts.append(proc.stdout)
                    outputs.append(out_path.read_bytes())
        self.assertEqual(len(set(stdouts)), 1, 'stdout must be identical across -O modes')
        self.assertEqual(len(set(outputs)), 1, '--output bytes must be identical across -O modes')
        stored = (HERE / 'result.json').read_bytes()
        self.assertEqual(outputs[0], stored, 'CLI output must equal the stored result.json')

    def test_h_stored_result_matches_recomputed(self):
        archive = self.archive()
        stored = json.loads((HERE / 'result.json').read_text(encoding='utf-8'))
        recomputed = RV.analyze(ROOT, archive)
        self.assertEqual(stored, recomputed)

    def test_h_untampered_temp_root_reproduces_result(self):
        archive = self.archive()
        tmp = self.build_temp_root()
        original = RV.resolve_head
        baseline = original(ROOT)
        RV.resolve_head = lambda root: baseline
        try:
            relocated = RV.analyze(tmp, archive)
        finally:
            RV.resolve_head = original
        self.assertEqual(relocated, RV.analyze(ROOT, archive))


if __name__ == '__main__':
    unittest.main(verbosity=2)
