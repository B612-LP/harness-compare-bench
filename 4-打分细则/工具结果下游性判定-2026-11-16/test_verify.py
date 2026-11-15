#!/usr/bin/env python3
"""工具结果下游性判定（2026-11-16）验证器测试。unittest；python3 与 python3 -O 双档全绿。

真档案端到端测试经环境变量 D_DOWNSTREAM_ARCHIVE_ROOT 门控（值=私有档案根
until22-20261109/launch-r1109）：未设置时用 testcase.fail 大声失败，拒绝静默跳过。
本文件只使用 unittest 断言（无裸 assert），保证 -O 档行为一致。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import verify as V  # noqa: E402

ARCHIVE_ENV = 'D_DOWNSTREAM_ARCHIVE_ROOT'
# 真档案锁定预期（源字节钉定 → 分类结果确定）：call_id 跨槽零交集 → 全对全 unlinked。
EXPECTED_UNLINKED = {'exercism_r1vsr2': 24, 'exercism_r1vsr3': 25,
                     'exercism_r2vsr3': 19, 'dabstep_r2vsr3': 78}


def require_archive(testcase):
    """真档案根门控：未设置或无效时 loudly FAIL（绝不静默跳过）。"""
    value = os.environ.get(ARCHIVE_ENV)
    if not value:
        testcase.fail('环境变量 %s 未设置：真档案端到端测试拒绝静默跳过；'
                      '请将其指向 until22-20261109/launch-r1109 档案根后重跑。' % ARCHIVE_ENV)
    path = Path(value)
    if not path.is_dir():
        testcase.fail('%s=%r 不是存在的目录' % (ARCHIVE_ENV, value))
    return path


def run_cli(root, archive_root, output=None, optimize=False):
    """子进程跑包内 verify.py CLI，返回 CompletedProcess（capture stdout/stderr）。"""
    exe = shutil.which('python3') or sys.executable
    cmd = [exe] + (['-O'] if optimize else []) + [str(HERE / 'verify.py'),
                                                   '--root', str(root),
                                                   '--archive-root', str(archive_root)]
    if output is not None:
        cmd += ['--output', str(output)]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300)


def ev_call(cid, name='shell', arguments='{}'):
    return {'type': 'response_item',
            'payload': {'type': 'function_call', 'call_id': cid, 'name': name, 'arguments': arguments}}


def ev_out(cid, output='ok'):
    return {'type': 'response_item',
            'payload': {'type': 'function_call_output', 'call_id': cid, 'output': output}}


def classify_synthetic(events_a, events_b, pair='synthetic'):
    return V.classify_pair(pair, 'slot_a', 'slot_b',
                           V.extract_items(events_a), V.extract_items(events_b))


def assert_pair_invariants(testcase, pair):
    counts = pair['counts']
    total_outputs = pair['output_items']['slot_a'] + pair['output_items']['slot_b']
    testcase.assertEqual(sum(counts.values()) + pair['unlinked'], total_outputs,
                         '每项恰落入三分类或 unlinked 之一')
    testcase.assertEqual(counts['outputs_differ_calls_differ'] + counts['outputs_differ_calls_same'],
                         pair['outputs_differ_total'])
    testcase.assertEqual(pair['linked_units'] * 2 + pair['unlinked'], total_outputs,
                         '联结单元两侧各计一项')


class PreregAndRepoGuards(unittest.TestCase):
    def test_prereg_readme_sha_frozen(self):
        raw = (ROOT / V.HERE / 'README.md').read_bytes()
        self.assertEqual(V.sha(raw), V.PREREG_SHA256, '冻结预注册 README 被改动')

    def test_prereg_readme_tamper_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp)
            pkg = fake / V.HERE
            pkg.mkdir(parents=True)
            (pkg / 'README.md').write_bytes(
                (ROOT / V.HERE / 'README.md').read_bytes() + b'tampered')
            with self.assertRaises(V.Invalid) as ctx:
                V.analyze(fake, None)
            self.assertIn('prereg README SHA mismatch', str(ctx.exception))

    def test_r3_result_file_tamper_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp)
            pkg = fake / V.HERE
            pkg.mkdir(parents=True)
            (pkg / 'README.md').write_bytes((ROOT / V.HERE / 'README.md').read_bytes())
            r3 = fake / V.R3_HERE
            r3.mkdir(parents=True)
            raw = bytearray((ROOT / V.R3_HERE / 'result.json').read_bytes())
            raw[-2] ^= 0x01
            (r3 / 'result.json').write_bytes(bytes(raw))
            (r3 / 'verify.py').write_bytes((ROOT / V.R3_HERE / 'verify.py').read_bytes())
            with self.assertRaises(V.Invalid) as ctx:
                V.analyze(fake, None)
            self.assertIn('R3 result.json SHA mismatch', str(ctx.exception))

    def test_missing_archive_root_fails(self):
        nowhere = Path(tempfile.gettempdir()) / 'downstream-missing-archive-root-xyz'
        with self.assertRaises(V.Invalid) as ctx:
            V.analyze(ROOT, nowhere)
        self.assertIn('archive root not found', str(ctx.exception))


class ClassificationLogic(unittest.TestCase):
    def test_synthetic_calls_same_same_params_diff_outputs(self):
        pair = classify_synthetic(
            [ev_call('X1', 'shell', '{"cmd":"ls"}'), ev_out('X1', 'alpha')],
            [ev_call('X1', 'shell', '{"cmd":"ls"}'), ev_out('X1', 'beta')])
        self.assertEqual(pair['counts'], {'outputs_differ_calls_differ': 0,
                                          'outputs_differ_calls_same': 2, 'outputs_same': 0})
        self.assertEqual(pair['linked_units'], 1)
        self.assertEqual(len(pair['calls_same_items']), 1)
        item = pair['calls_same_items'][0]
        self.assertEqual(item['call_id'], 'X1')
        self.assertEqual(item['function_name'], 'shell')
        self.assertEqual(item['slots'], ['slot_a', 'slot_b'])
        self.assertEqual(item['output_bytes'],
                         [len(V.canon(ev_out('X1', 'alpha')['payload'])),
                          len(V.canon(ev_out('X1', 'beta')['payload']))])
        assert_pair_invariants(self, pair)

    def test_synthetic_downstream_diff_params_diff_outputs(self):
        pair = classify_synthetic(
            [ev_call('X1', 'shell', '{"cmd":"a"}'), ev_out('X1', 'out-a')],
            [ev_call('X1', 'shell', '{"cmd":"b"}'), ev_out('X1', 'out-b')])
        self.assertEqual(pair['counts']['outputs_differ_calls_differ'], 2)
        self.assertEqual(pair['counts']['outputs_differ_calls_same'], 0)
        self.assertEqual(pair['calls_same_items'], [])
        assert_pair_invariants(self, pair)

    def test_synthetic_outputs_same_not_counted(self):
        pair = classify_synthetic(
            [ev_call('X1', 'shell', '{"cmd":"ls"}'), ev_out('X1', 'same')],
            [ev_call('X1', 'shell', '{"cmd":"ls"}'), ev_out('X1', 'same')])
        self.assertEqual(pair['counts'], {'outputs_differ_calls_differ': 0,
                                          'outputs_differ_calls_same': 0, 'outputs_same': 2})
        self.assertEqual(pair['outputs_differ_total'], 0)
        self.assertEqual(pair['calls_same_items'], [])
        assert_pair_invariants(self, pair)

    def test_synthetic_cross_slot_counterpart_missing(self):
        pair = classify_synthetic(
            [ev_call('X1', 'shell', '{}'), ev_out('X1', 'a')],
            [ev_call('Z9', 'shell', '{}'), ev_out('Z9', 'b')])
        self.assertEqual(pair['counts']['outputs_differ_calls_differ'], 0)
        self.assertEqual(pair['unlinked'], 2)
        self.assertEqual(pair['unlinked_reasons'], {'counterpart_missing_other_slot': 2})
        self.assertEqual(pair['linked_units'], 0)
        self.assertEqual(pair['cross_slot_call_id_intersection'], 0)

    def test_synthetic_orphan_output_no_call(self):
        pair = classify_synthetic([ev_out('X1', 'a')], [ev_call('X1', 'shell', '{}'), ev_out('X1', 'b')])
        self.assertEqual(pair['unlinked'], 2)
        self.assertEqual(pair['unlinked_reasons'],
                         {'orphan_output_no_call': 1, 'counterpart_missing_other_slot': 1})
        self.assertEqual(pair['counts']['outputs_differ_calls_differ'], 0)
        self.assertEqual(pair['linked_units'], 0)

    def test_synthetic_ambiguous_one_to_many(self):
        pair = classify_synthetic(
            [ev_call('X1', 'shell', '{}'), ev_out('X1', 'a'), ev_out('X1', 'a2')],
            [ev_call('X1', 'shell', '{}'), ev_out('X1', 'b'), ev_out('X1', 'b2')])
        self.assertEqual(pair['unlinked'], 4)
        self.assertEqual(pair['unlinked_reasons'], {'ambiguous_one_to_many': 4})
        self.assertEqual(pair['linked_units'], 0)

    def test_synthetic_missing_call_id_field(self):
        no_id = {'type': 'response_item',
                 'payload': {'type': 'function_call_output', 'output': 'x'}}
        items = V.extract_items([no_id])
        self.assertFalse(items['call_id_field_present'])
        self.assertEqual(items['outputs_missing_call_id'], 1)
        pair = classify_synthetic([no_id], [no_id])
        self.assertEqual(pair['unlinked'], 2)
        self.assertEqual(pair['unlinked_reasons'], {'missing_call_id_field': 2})
        self.assertEqual(pair['linked_units'], 0)


class VerdictSelection(unittest.TestCase):
    def test_verdict_three_branches(self):
        self.assertEqual(V.select_verdict(
            [{'linked_units': 0, 'counts': {'outputs_differ_calls_same': 0}}]),
            'D-STRUCTURAL-DEGRADED')
        self.assertEqual(V.select_verdict(
            [{'linked_units': 2, 'counts': {'outputs_differ_calls_same': 1}}]),
            'D-TOOL-NONDETERMINISM')
        self.assertEqual(V.select_verdict(
            [{'linked_units': 2, 'counts': {'outputs_differ_calls_same': 0}},
             {'linked_units': 1, 'counts': {'outputs_differ_calls_same': 0}}]),
            'D-ALL-DOWNSTREAM')


class RealArchiveEndToEnd(unittest.TestCase):
    @classmethod
    def analyze_real(cls, testcase):
        return V.analyze(ROOT, require_archive(testcase))

    def test_end_to_end_real_archive(self):
        result = self.analyze_real(self)
        self.assertEqual(result['schema'], 'tool-downstream-judgment-v1')
        self.assertEqual(result['prereg_sha256'], V.PREREG_SHA256)
        self.assertEqual(len(result['slots']), 5)
        self.assertEqual(len(result['pairs']), 4)
        self.assertTrue(all(s['r3_hard_equal'] for s in result['slots']),
                        '五槽 R3 三方硬等必须全过')
        for slot_row, frozen in zip(result['slots'], (V.FROZEN_R3[s] for s in V.SLOTS)):
            self.assertEqual(slot_row['r3_recomputed']['r3_total_bytes'], frozen['r3_total_bytes'])
        for pair in result['pairs']:
            assert_pair_invariants(self, pair)
        self.assertIn(result['verdicts']['branch'],
                      {'D-ALL-DOWNSTREAM', 'D-TOOL-NONDETERMINISM', 'D-STRUCTURAL-DEGRADED'})

    def test_real_archive_locked_classification(self):
        result = self.analyze_real(self)
        for pair in result['pairs']:
            self.assertEqual(pair['unlinked'], EXPECTED_UNLINKED[pair['pair']],
                             '真档案分类漂移（源字节钉定下应锁定）')
            self.assertEqual(pair['cross_slot_call_id_intersection'], 0)
            self.assertEqual(pair['linked_units'], 0)
        self.assertEqual(result['verdicts']['branch'], 'D-STRUCTURAL-DEGRADED')
        self.assertFalse(result['verdicts']['downstream_conclusion_issued'])
        self.assertEqual(result['verdicts']['outputs_differ_calls_same_total'], 0)
        self.assertEqual(result['verdicts']['calls_same_items_all_pairs'], [])

    def test_cli_double_mode_stdout_identical(self):
        archive = require_archive(self)
        plain = run_cli(ROOT, archive)
        optimized = run_cli(ROOT, archive, optimize=True)
        self.assertEqual(plain.returncode, 0, plain.stderr)
        self.assertEqual(optimized.returncode, 0, optimized.stderr)
        self.assertEqual(plain.stdout, optimized.stdout, 'python3 与 python3 -O stdout 必须逐字节一致')
        self.assertEqual(plain.stderr, '')
        self.assertEqual(plain.stdout.count('pair '), 4)
        self.assertIn('verdict: D-STRUCTURAL-DEGRADED', plain.stdout)
        self.assertIn('content-free', plain.stdout)

    def test_fresh_output_matches_stored_result(self):
        archive = require_archive(self)
        stored_path = HERE / 'result.json'
        if not stored_path.is_file():
            self.fail('包内 result.json 不存在：先由 verify.py --output 生成为正式结果')
        with tempfile.TemporaryDirectory() as tmp:
            fresh = Path(tmp) / 'fresh.json'
            proc = run_cli(ROOT, archive, output=fresh)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            if fresh.read_bytes() == stored_path.read_bytes():
                return
            fresh_json = json.loads(fresh.read_bytes())
            stored_json = json.loads(stored_path.read_bytes())
            fresh_json.pop('baseline_commit')
            stored_json.pop('baseline_commit')
            self.assertEqual(fresh_json, stored_json,
                             'fresh 与存储 result.json 除 baseline_commit 外逐键一致')
            self.assertEqual(json.loads(fresh.read_bytes())['baseline_commit'], V.resolve_head(ROOT),
                             'baseline 差异只能来自仓库 HEAD 前进')

    def test_output_refuses_overwrite(self):
        archive = require_archive(self)
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'existing.json'
            target.write_text('KEEP')
            proc = run_cli(ROOT, archive, output=target)
            self.assertEqual(proc.returncode, 2)
            self.assertEqual(target.read_text(), 'KEEP', '已存在 --output 目标必须原样保留')
            self.assertTrue(proc.stderr.startswith('ERROR'))

    def test_missing_trace_fails(self):
        archive = require_archive(self)
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / 'empty-archive'
            empty.mkdir()
            with self.assertRaises(V.Invalid) as ctx:
                V.analyze(ROOT, empty)
            self.assertIn('missing archived trace', str(ctx.exception))

    def test_trace_byte_flip_fails(self):
        archive = require_archive(self)
        flip_slot = 'codex__dabstep-payments-10__r3'
        flip_rel = V.ARCHIVE_SOURCES[flip_slot][0]
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp)
            for slot, (rel, _sha) in V.ARCHIVE_SOURCES.items():
                dest = fake / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                if slot == flip_slot:
                    raw = bytearray((archive / rel).read_bytes())
                    raw[-1] ^= 0x01
                    dest.write_bytes(bytes(raw))
                else:
                    os.link(archive / rel, dest)  # 硬链接：resolve() 不逃出假档案根
            with self.assertRaises(V.Invalid) as ctx:
                V.analyze(ROOT, fake)
            self.assertIn('SHA mismatch', str(ctx.exception))

    def test_r3_injection_tamper_fails(self):
        archive = require_archive(self)
        r3_dict = json.loads((ROOT / V.R3_HERE / 'result.json').read_bytes())
        row = next(r for r in r3_dict['slots'] if r.get('slot') == V.SLOTS[0])
        row['r3_total_bytes'] += 1
        with self.assertRaises(V.Invalid) as ctx:
            V.analyze(ROOT, archive, r3_result=r3_dict)
        self.assertIn('drift', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
