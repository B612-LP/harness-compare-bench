#!/usr/bin/env python3
"""自报 usage 分离账复算器测试：正常模式 + 近错对照（缺字段/非整数/负数/错绑/累计陷阱）。"""
import json, copy, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import recompute as R

HERE = Path(__file__).resolve().parent
LED = json.loads((HERE / 'usage-ledger.json').read_bytes())

class TestRecompute(unittest.TestCase):
    def test_normal_run(self):
        r = R.recompute()
        self.assertEqual(r['n_dsh'], 338)
        self.assertEqual(r['n_codex'], 406)
        self.assertEqual(r['dsh_rel'].get('in+out+cr+cw'), 338)
        self.assertEqual(r['codex_rel'].get('in+out'), 406)
        self.assertEqual(r['p6']['cross_case_spread'], 1.7)
        for c, v in r['dsh_first'].items():
            self.assertLess(v['spread_pct'], 1.0, c)
        for c, v in r['codex_first'].items():
            self.assertTrue(v['input_identical'], c)
        for k, d in r['three_run_distinct'].items():
            self.assertEqual(d, 3, k)
        for slot, v in r['codex_seq'].items():
            self.assertTrue(v['impossible_cum'], slot)
        for slot, fs in r['dsh_seq'].items():
            self.assertFalse(fs['inputTokens']['nondec'], slot)

    def test_near_miss_missing_field(self):
        u = copy.deepcopy(LED['dsh']['dsh__bird-ca-schools-15__r1']['records'][0]['usage'])
        u.pop('cacheWriteTokens')
        with self.assertRaises(R.Invalid):
            R.struct_check(u, R.DSH_F)

    def test_near_miss_non_int_and_negative(self):
        base = copy.deepcopy(LED['dsh']['dsh__bird-ca-schools-15__r1']['records'][0]['usage'])
        for bad, why in ((1.5, 'non-int'), (-5, 'negative')):
            u = copy.deepcopy(base); u['cacheWriteTokens'] = bad
            with self.assertRaises(R.Invalid):
                R.struct_check(u, R.DSH_F)

    def test_near_miss_wrong_binding(self):
        # 错绑形态一：非十六进制 SHA → 载入即拒
        led2 = copy.deepcopy(LED)
        led2['dsh']['dsh__bird-ca-schools-15__r1']['archive_sha256'] = 'g' * 64
        with self.assertRaises(R.Invalid):
            R.load_ledger(led2)
        # 错绑形态二：换槽记录（bird 槽放 dabstep 记录）→ 复算结果必须敏感变化
        led3 = copy.deepcopy(LED)
        led3['dsh']['dsh__bird-ca-schools-15__r1']['records'] = \
            copy.deepcopy(LED['dsh']['dsh__dabstep-payments-10__r1']['records'])
        with self.assertRaises(R.Invalid):
            R.load_ledger(led3)  # n 与记录数不符 → 换槽绑定被拒

    def test_near_miss_cumulative_trap(self):
        """同一累计口径记录的增量误读 vs 累计正读必须分叉（口径必须显式）。"""
        seq = [r['usage']['inputTokens'] for r in LED['dsh']['dsh__bird-ca-schools-15__r1']['records'][:6]]
        prefix = []
        s = 0
        for v in seq:
            s += v
            prefix.append(s)
        self.assertNotEqual(sum(prefix), prefix[-1])
        # 旧名称仅表示不等式成立，不能排除累计；真实累计序列也可满足。
        cseq = [r['usage']['input_tokens'] for r in LED['codex']['codex__bird-ca-schools-15__r1']['records']]
        self.assertTrue(R.is_cumulative_impossible(cseq))
        self.assertTrue(R.is_cumulative_impossible([10, 11]))  # 有效累计反例

    def test_thread_closure_normal_and_near_miss(self):
        """独审 N1：会话级闭合正常载入 + 两类破坏必须被拒。"""
        self.assertEqual(R.load_closure()['codex'].__len__(), 15)
        tc = json.loads((HERE / 'thread-closure.json').read_bytes())
        # 形态一：闭合被破坏（sum != thread）→ 拒
        bad = copy.deepcopy(tc)
        slot0 = next(iter(bad['codex']))
        bad['codex'][slot0]['components']['total_tokens']['sum_per_record'] += 1
        with self.assertRaises(R.Invalid):
            R.load_closure(bad)
        # 形态二：all_equal 翻 false → 拒
        bad2 = copy.deepcopy(tc)
        bad2['codex'][slot0]['all_equal'] = False
        with self.assertRaises(R.Invalid):
            R.load_closure(bad2)
        # 形态三：id_free 缺失 → 拒（账本不得携带 id 的承诺同样约束闭合件）
        bad3 = copy.deepcopy(tc)
        bad3.pop('id_free')
        with self.assertRaises(R.Invalid):
            R.load_closure(bad3)

if __name__ == '__main__':
    unittest.main()
