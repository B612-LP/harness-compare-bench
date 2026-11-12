#!/usr/bin/env python3
"""verify.py 的单元测试：统计函数、常量校验、篡改检测。

用法：python3 test_verify.py
"""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import verify

HERE = Path(__file__).resolve().parent
RESULT = HERE / "result.json"


class Stats(unittest.TestCase):
    def test_wilson_perfect(self):
        lo, hi = verify.wilson95(6, 6)
        self.assertAlmostEqual(lo, 0.6096657120978346, places=12)
        self.assertEqual(hi, 1.0)

    def test_wilson_zero_and_empty(self):
        lo, hi = verify.wilson95(0, 5)
        self.assertEqual(lo, 0.0)
        self.assertGreater(hi, 0.0)
        self.assertEqual(verify.wilson95(1, 0), [None, None])

    def test_median_even_odd(self):
        self.assertEqual(verify.median([3, 1, 2]), 2.0)
        self.assertEqual(verify.median([4, 1, 3, 2]), 2.5)

    def test_middle_key_constant(self):
        # MIDDLE_KEY 必须等于 sha256("fixture-v1-210")
        self.assertEqual(
            verify.sha256_hex("fixture-v1-210"),
            "59f421aea4171df85721b2fc8e0081cb9bdc4969d81c7e61aa00adf1b8480203",
        )


class FullResult(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(RESULT.read_text(encoding="utf-8"))

    def test_published_result_passes(self):
        out = verify.verify(self.data)
        self.assertTrue(out["ok"], msg=out["checks"])

    def test_tampered_middle_key_detected(self):
        bad = copy.deepcopy(self.data)
        bad["constants"]["probe_middle_key"] = "0" * 64
        self.assertFalse(verify.verify(bad)["checks"]["middle_key_matches_source_string"])

    def test_tampered_rb_total_detected(self):
        bad = copy.deepcopy(self.data)
        bad["ring1_dsh_readback_mechanism"]["derived"]["rb_session_total_median"] = 99999.0
        self.assertFalse(verify.verify(bad)["checks"]["rb_total_median"])

    def test_tampered_c1_delta_detected(self):
        bad = copy.deepcopy(self.data)
        bad["ring1_dsh_readback_mechanism"]["sessions"]["c1"][0]["delta"] = 2383
        self.assertFalse(verify.verify(bad)["checks"]["c1_gate_matches_baseline"])

    def test_tampered_wilson_detected(self):
        bad = copy.deepcopy(self.data)
        bad["ring1_dsh_readback_mechanism"]["derived"]["rb_wilson95"] = [0.0, 1.0]
        self.assertFalse(verify.verify(bad)["checks"]["rb_wilson95"])

    def test_tampered_positive_control_detected(self):
        bad = copy.deepcopy(self.data)
        bad["ring2_workbuddy_known_read_positive_control"]["sessions"][1]["keys_all_correct"] = False
        self.assertFalse(verify.verify(bad)["checks"]["ring2_n3_all_pass"])
        bad = copy.deepcopy(self.data)
        bad["ring3_doubao_known_read_first_sampling"]["sessions"][2]["read_result_chars"] = 123
        self.assertFalse(verify.verify(bad)["checks"]["ring3_n3_all_pass"])

    def test_tampered_ring5_detected(self):
        bad = copy.deepcopy(self.data)
        bad["ring5_codex_known_read_positive_control"]["sessions"][0]["read_result_bytes"] = 100
        self.assertFalse(verify.verify(bad)["checks"]["ring5_n3_all_pass"])
        bad = copy.deepcopy(self.data)
        bad["ring5_codex_known_read_positive_control"]["sessions"][1]["truncation_marker"] = True
        self.assertFalse(verify.verify(bad)["checks"]["ring5_n3_all_pass"])
        bad = copy.deepcopy(self.data)
        bad["ring5_codex_known_read_positive_control"]["sessions"][2]["keys_all_correct"] = False
        self.assertFalse(verify.verify(bad)["checks"]["ring5_n3_all_pass"])

    def test_tampered_ring6_detected(self):
        # 中期口径被改成立"全对"必须被拒
        bad = copy.deepcopy(self.data)
        bad["ring6_yuanbao_known_read_first_session"]["sessions"][0]["keys_correct"]["TAIL_KEY"] = True
        self.assertFalse(verify.verify(bad)["checks"]["ring6_partial_2of3"])
        bad = copy.deepcopy(self.data)
        bad["ring6_yuanbao_known_read_first_session"]["sessions"][0]["keys_correct_count"] = 3
        self.assertFalse(verify.verify(bad)["checks"]["ring6_partial_2of3"])
        # 中期状态标记被移除必须被拒
        bad = copy.deepcopy(self.data)
        bad["ring6_yuanbao_known_read_first_session"]["status"] = "final"
        self.assertFalse(verify.verify(bad)["checks"]["ring6_interim_shape"])

    def test_tampered_ring8_detected(self):
        r8 = "ring8_size_threshold"
        # 豆包 64k 全内联字符量被改必须被拒
        bad = copy.deepcopy(self.data)
        bad[r8]["doubao_work"]["sessions"][2]["tool_chars_total"] = 100
        self.assertFalse(verify.verify(bad)["checks"]["ring8_doubao_64k_full_inline"])
        # 256k 拒绝形态被改成"未拒绝"必须被拒（token 上限证据缺失）
        bad = copy.deepcopy(self.data)
        bad[r8]["doubao_work"]["sessions"][3]["read_form"] = "full_inline"
        self.assertFalse(verify.verify(bad)["checks"]["ring8_doubao_256k_cap_grep"])
        # WB 256k 上限消息被改必须被拒
        bad = copy.deepcopy(self.data)
        bad[r8]["workbuddy"]["sessions"][3]["read_tool_error"] = "no error"
        self.assertFalse(verify.verify(bad)["checks"]["ring8_wb_256k_cap_refusal"])
        # WB 64k 模型侧全文摄入推断被抹掉必须被拒
        bad = copy.deepcopy(self.data)
        bad[r8]["workbuddy"]["sessions"][2]["model_side_full_inferred"] = None
        self.assertFalse(verify.verify(bad)["checks"]["ring8_wb_64k_persisted_usage"])
        # Codex 256k 全量携带被改小必须被拒
        bad = copy.deepcopy(self.data)
        bad[r8]["codex_cli"]["sessions"][3]["max_output_chars"] = 1000
        self.assertFalse(verify.verify(bad)["checks"]["ring8_codex_no_threshold"])
        # 夹具尺寸阶梯被改必须被拒
        bad = copy.deepcopy(self.data)
        bad[r8]["fixtures"][3]["bytes"] = 131072
        self.assertFalse(verify.verify(bad)["checks"]["ring8_three_arms_four_slots"])

    def test_tampered_ring10_detected(self):
        r10 = "ring10_spill_cap_sweep"
        # c32768 分支被改成 recovered_via_read（零 read 却宣称经读恢复）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r10]["arms"]["rb-c32768"]["branch"] = "recovered_via_read"
        self.assertFalse(verify.verify(bad)["checks"]["ring10_read_partition"])
        # c32768 读次数被改成 2 必须被拒
        bad = copy.deepcopy(self.data)
        bad[r10]["arms"]["rb-c32768"]["read_attempts_total"] = 2
        self.assertFalse(verify.verify(bad)["checks"]["ring10_read_partition"])
        # 成本中位数被改必须被拒
        bad = copy.deepcopy(self.data)
        bad[r10]["arms"]["rb-c8192"]["B_input_total_median"] = 1000.0
        self.assertFalse(verify.verify(bad)["checks"]["ring10_cost_medians_exact"])
        self.assertFalse(verify.verify(bad)["checks"]["ring10_nonmonotonic_8192_max_512_min"])
        # 交叉点被改必须被拒
        bad = copy.deepcopy(self.data)
        bad[r10]["crossover"]["smallest_cap_without_read"] = "rb-c131072"
        self.assertFalse(verify.verify(bad)["checks"]["ring10_crossover_values"])
        # 预注册印记被换必须被拒
        bad = copy.deepcopy(self.data)
        bad[r10]["prereg_seal_16"] = "deadbeefdeadbeef"
        self.assertFalse(verify.verify(bad)["checks"]["ring10_arms_two_slots_each"])
        # 键命中被改少必须被拒
        bad = copy.deepcopy(self.data)
        bad[r10]["arms"]["rb-c2048"]["sessions_all_keys_correct"] = 1
        self.assertFalse(verify.verify(bad)["checks"]["ring10_arms_two_slots_each"])

    def test_tampered_ring14_detected(self):
        r14 = "ring14_spill_boundary"
        # read 次数改成 1（零 read 是本环核心证据）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r14]["arms"]["rb-c9216"]["read_attempts_each"] = 1
        self.assertFalse(verify.verify(bad)["checks"]["ring14_arms_two_slots_each"])
        # 无外溢证据被翻转（spill_footer 假装存在）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r14]["arms"]["rb-c16384"]["spill_footer"] = "Omitted 0 bytes."
        self.assertFalse(verify.verify(bad)["checks"]["ring14_no_spill_evidence"])
        # B 系列被改值必须被拒
        bad = copy.deepcopy(self.data)
        bad[r14]["arms"]["rb-c9216"]["B_input_series"][0][1] = 3506
        self.assertFalse(verify.verify(bad)["checks"]["ring14_no_spill_evidence"])
        # 9216 预测错误被改写成"as predicted"必须被拒
        bad = copy.deepcopy(self.data)
        bad[r14]["outcome_vs_prediction"]["rb-c9216"] = "as predicted (no spill, 0 read)"
        self.assertFalse(verify.verify(bad)["checks"]["ring14_no_spill_evidence"])
        # 分支被换掉必须被拒
        bad = copy.deepcopy(self.data)
        bad[r14]["branch"] = "answered_without_read"
        self.assertFalse(verify.verify(bad)["checks"]["ring14_branch"])


    def test_tampered_ring16_detected(self):
        r6 = "ring6_yuanbao_known_read_completed"
        # branch 翻成 positive_control_passed（伪造正控通过）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r6]["judge_branch"] = "positive_control_passed"
        bad[r6]["passed_all_keys"] = 3
        self.assertFalse(verify.verify(bad)["checks"]["ring6_completed_shape"])
        # yb-01 的读取路径到达被抹掉（动摇"可达性"结论）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r6]["sessions"][0]["read_path_reached"] = False
        bad[r6]["read_path_reached_count"] = 0
        self.assertFalse(verify.verify(bad)["checks"]["ring6_keys_pattern"])
        # TAIL 伪造观测值被改成正确值（把 partial 洗成全对）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r6]["sessions"][2]["TAIL_KEY_observed"] = "COBALT-492"
        self.assertFalse(verify.verify(bad)["checks"]["ring6_keys_pattern"])
        # 中期记录的 superseded 标记被删（历史口径回活）必须被拒
        bad = copy.deepcopy(self.data)
        bad["ring6_yuanbao_known_read_first_session"]["status"] = "interim: session 1 of 3"
        self.assertFalse(verify.verify(bad)["checks"]["ring6_first_session_marked_superseded"])

    def test_tampered_ring12_detected(self):
        r12 = "ring12_middle_position"
        # read 次数被改成 1（零 read 是本环核心证据）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r12]["arms"]["mp-far"]["sessions"][0]["read_attempts"] = 1
        self.assertFalse(verify.verify(bad)["checks"]["ring12_arms_two_slots_each"])
        bad = copy.deepcopy(self.data)
        bad[r12]["arms"]["mp-far"]["read_attempts_total"] = 2
        self.assertFalse(verify.verify(bad)["checks"]["ring12_arms_two_slots_each"])
        # 省略字节数被改成 0（头尾预览证据消失）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r12]["preview_evidence"]["omitted_bytes"] = 0
        self.assertFalse(verify.verify(bad)["checks"]["ring12_preview_evidence"])
        # far 记录在预览内可见被翻转（动摇 answer-visibility 结论）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r12]["preview_evidence"]["far_record_in_preview"] = False
        self.assertFalse(verify.verify(bad)["checks"]["ring12_preview_evidence"])
        # 分支被换成 preview_estimate_wrong 必须被拒
        bad = copy.deepcopy(self.data)
        bad[r12]["branch"] = "preview_estimate_wrong"
        self.assertFalse(verify.verify(bad)["checks"]["ring12_branch"])
        # B 系列被改值必须被拒
        bad = copy.deepcopy(self.data)
        bad[r12]["arms"]["mp-near"]["sessions"][0]["B_input_series"] = [1724, 40000]
        self.assertFalse(verify.verify(bad)["checks"]["ring12_b_series_exact"])
        # 预注册印记被换必须被拒
        bad = copy.deepcopy(self.data)
        bad[r12]["prereg_seal_12"] = "deadbeefdeadbeef"
        self.assertFalse(verify.verify(bad)["checks"]["ring12_arms_two_slots_each"])

    def test_tampered_ring18_detected(self):
        r18 = "ring18_boundary_precision"
        # 8942 的省略字节数被洗成无外溢（截断量律证据消失）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r18]["spill_sessions"][1]["omitted_bytes"] = [0, 0]
        self.assertFalse(verify.verify(bad)["checks"]["ring18_spill_arms"])
        # 无外溢臂的 read 次数被改成 1（零 read 是边界证据核心）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r18]["nospill_sessions"][0]["read_attempts_total"] = 1
        self.assertFalse(verify.verify(bad)["checks"]["ring18_nospill_arms"])
        # 截断量律公式常数被改（-80 -> -100）使 8941 数据不再吻合必须被拒
        bad = copy.deepcopy(self.data)
        bad[r18]["truncation_law"] = "omitted = 35767 - 4*(cap-100); exact at caps 8192/8941/8942"
        self.assertFalse(verify.verify(bad)["checks"]["ring18_truncation_law"])
        # 边界声明被改成单点精解（掩盖 [8943,9020] 未逐点定位）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r18]["boundary"] = "spill-off boundary exactly at cap 9020"
        self.assertFalse(verify.verify(bad)["checks"]["ring18_truncation_law"])
        # 被否证预测被洗成已验证（预测诚实性抹除）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r18]["prediction_honesty"] = "all prereg predictions held"
        self.assertFalse(verify.verify(bad)["checks"]["ring18_prediction_honesty"])

    def test_tampered_ring20_detected(self):
        orig=json.loads(RESULT.read_text(encoding='utf-8'))
        bad=json.loads(json.dumps(orig))
        bad['ring20_sizegen']['probes']['dsh-256k']['as_predicted']=True  # whitewash the +4 law break
        r=verify.verify(bad)
        self.assertFalse(r['ok'])
        self.assertFalse(r['checks']['ring20_law_break_honesty'])
        bad2=json.loads(json.dumps(orig))
        bad2['ring20_sizegen']['probes']['dsh-64k']['measured_omitted']=33057  # not the law-exact value
        r2=verify.verify(bad2)
        self.assertFalse(r2['ok'])
        self.assertFalse(r2['checks']['ring20_shape'])

    def test_tampered_ring17_detected(self):
        r17 = "ring17_yuanbao_size_interim"
        # 1k 点三键全对被改成 false（正控结论翻转）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r17]["sessions"][0]["keys_all_correct"] = False
        self.assertFalse(verify.verify(bad)["checks"]["ring17_interim_shape"])
        # interim 状态被洗成 completed（阻塞事实抹除）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r17]["status"] = "completed"
        self.assertFalse(verify.verify(bad)["checks"]["ring17_interim_shape"])
        # probe 字节数被改（夹具身份漂移）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r17]["sessions"][0]["probe_bytes"] = 1024
        self.assertFalse(verify.verify(bad)["checks"]["ring17_interim_shape"])

    def test_tampered_ring23_detected(self):
        r23 = "ring23_cost_crossover"
        # 交叉点被洗成 0（吃亏区消失）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r23]["crossover_probe_chars"] = 0
        self.assertFalse(verify.verify(bad)["checks"]["ring23_crossover_shape"])
        # 256k 增量被洗成 0（节省被抹平）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r23]["rb_minus_inline"]["probe_256k"] = 0
        self.assertFalse(verify.verify(bad)["checks"]["ring23_crossover_shape"])
        # r2 预览原样保留标志被洗成 False（无历史压缩观测抹除）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r23]["preview_r2_identical_in_r3"] = [False, False]
        self.assertFalse(verify.verify(bad)["checks"]["ring23_crossover_shape"])

    def test_tampered_ring24_detected(self):
        r24 = "ring24_read_unbounded"
        # read 有界标志被洗成 True（嵌套外溢白嫖成立）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r24]["r3_read_bounded"] = [True, True]
        self.assertFalse(verify.verify(bad)["checks"]["ring24_unbounded_shape"])
        # 分支被换成 nested_spill_confirmed（P1 否证被翻转）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r24]["branch"] = "nested_spill_confirmed"
        self.assertFalse(verify.verify(bad)["checks"]["ring24_unbounded_shape"])
        # 三键全对计数被洗成 0 必须被拒
        bad = copy.deepcopy(self.data)
        bad[r24]["sessions_all_keys_correct"] = 0
        self.assertFalse(verify.verify(bad)["checks"]["ring24_unbounded_shape"])

    def test_tampered_ring28_silent_clip_detected(self):
        r28 = "ring28_codex_bracket"
        # 静默削顶被洗成 False（信号面分类抹除）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r28]["silent_clip"] = False
        self.assertFalse(verify.verify(bad)["checks"]["ring28_codex_bracket_shape"])
        # 修正后帽 bracket 被改宽（精度虚报）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r28]["cap_char_bracket_corrected"] = [29300, 34000]
        self.assertFalse(verify.verify(bad)["checks"]["ring28_codex_bracket_shape"])
        bad = copy.deepcopy(self.data)
        bad[r28]["cap_char_bracket_superseded"] = [100, 200]
        self.assertFalse(verify.verify(bad)["checks"]["ring28_codex_bracket_shape"])

    def test_tampered_ring29_incident_honesty(self):
        r29 = "ring29_doubao_bracket"
        # 事故被洗成正常键全对（夹具缺陷隐瞒）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r29]["keys"]["80k"] = "3/3"
        self.assertFalse(verify.verify(bad)["checks"]["ring29_doubao_bracket_shape"])
        # chars/4 自估精确性被翻转（跨产品收敛结论失效）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r29]["estimator_chars_per_token_exact"] = False
        self.assertFalse(verify.verify(bad)["checks"]["ring29_doubao_bracket_shape"])

    def test_tampered_ring30_waiting_user_honesty(self):
        r30 = "ring30_wb_bracket"
        # waiting_user 不可判被洗成 completed 3/3（暂停事实抹除）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r30]["wb_112k_wb_192k"]["status"] = "completed"
        self.assertFalse(verify.verify(bad)["checks"]["ring30_wb_bracket_shape"])
        # 闸门作用面结论被翻转（chars/4 收敛失效）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r30]["cross_product_conclusion"] = "gate acts on real tokens"
        self.assertFalse(verify.verify(bad)["checks"]["ring30_wb_bracket_shape"])


    def test_tampered_ring34_char_cap_refusal_hidden(self):
        r34 = "ring34_calibrated_bracket"
        # 字符帽否证结论被洗掉（行为面裁定抹除）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r34]["behavioral_verdict"] = "char-based cap confirmed"
        self.assertFalse(verify.verify(bad)["checks"]["ring34_shape"])
        # usage 仪器异常被隐瞒（仪器边界抹除）必须被拒
        bad = copy.deepcopy(self.data)
        bad[r34]["instrument_caveat"] = "usage readings are always reliable"
        self.assertFalse(verify.verify(bad)["checks"]["ring34_shape"])
        # rg 补偿证据被洗掉（削顶事实抹除）必须被拒
        bad = copy.deepcopy(self.data)
        for row in bad[r34]["results"]:
            row["rg_middle_compensation"] = False
        self.assertFalse(verify.verify(bad)["checks"]["ring34_arms"])

    def test_tampered_ring27_correction_dropped(self):
        # ρ 修正字段被删除（修正链抹除）必须被拒
        bad = copy.deepcopy(self.data)
        del bad["ring27_codex_usage"]["correction"]["rho_ascii_corrected"]
        self.assertFalse(verify.verify(bad)["checks"]["ring27_correction_present"])
        # 修正后的 ρ 被改回错误值必须被拒
        bad = copy.deepcopy(self.data)
        bad["ring27_codex_usage"]["correction"]["rho_ascii_corrected"] = 3.895
        self.assertFalse(verify.verify(bad)["checks"]["ring27_correction_present"])

    def test_tampered_ring28_bracket_unsuperseded(self):
        # 旧字符 bracket 恢复为有效值（修正被回滚）必须被拒
        bad = copy.deepcopy(self.data)
        r28 = bad["ring28_codex_bracket"]
        r28["cap_char_bracket_corrected"] = [65589, 66795]
        self.assertFalse(verify.verify(bad)["checks"]["ring28_bracket_superseded"])
        # 33 环实测 ρ 被篡改必须被拒
        bad = copy.deepcopy(self.data)
        bad["ring33_rho_calibration"]["rho_cjk_measured"] = 3.9
        self.assertFalse(verify.verify(bad)["checks"]["ring33_rho_shape"])


    def test_tampered_ring36_detected(self):
        bad = copy.deepcopy(self.data)
        bad["ring36_law_panel"]["max_deviation_chars"] = 0
        self.assertFalse(verify.verify(bad)["checks"]["ring36_shape"])
        bad = copy.deepcopy(self.data)
        bad["ring36_law_panel"]["branch"] = "law_holds_everywhere_exact"
        self.assertFalse(verify.verify(bad)["checks"]["ring36_shape"])

    def test_tampered_ring39_detected(self):
        # 折叠保留量被洗成全量保留必须被拒
        bad = copy.deepcopy(self.data)
        bad["ring39_codex_collapse"]["fold_layout"]["probe-256k-262109ch"] = {"head_kept": 262109, "tail_kept": 262109}
        self.assertFalse(verify.verify(bad)["checks"]["ring39_shape"])
        # r1 字节不变性数字被改必须被拒
        bad = copy.deepcopy(self.data)
        bad["ring39_codex_collapse"]["request_invariance"]["r1_bytes"] = 30000
        self.assertFalse(verify.verify(bad)["checks"]["ring39_shape"])
        # superseded 链被回滚必须被拒
        bad = copy.deepcopy(self.data)
        bad["ring28_codex_bracket"]["status"] = "cap_bracket_valid"
        self.assertFalse(verify.verify(bad)["checks"]["ring2728_superseded_by_ring39"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
