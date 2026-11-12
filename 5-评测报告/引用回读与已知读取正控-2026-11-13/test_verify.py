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


if __name__ == "__main__":
    unittest.main(verbosity=2)
