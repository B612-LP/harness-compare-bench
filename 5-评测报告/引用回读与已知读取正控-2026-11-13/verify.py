#!/usr/bin/env python3
"""公开复算入口：引用回读与已知读取正控（2026-11-13）。

只读本目录 result.json，重算全部派生统计与常量一致性，输出 JSON 结论。
不改任何文件；无网络；无第三方依赖。

用法：python3 verify.py
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULT = HERE / "result.json"

Z95 = 1.959963984540054  # 双侧 95% 正态分位


def wilson95(k: int, n: int) -> list[float]:
    """Wilson score 区间；n<=0 返回 [None, None]。"""
    if n <= 0:
        return [None, None]
    p = k / n
    z2 = Z95 * Z95
    denom = 1 + z2 / n
    center = p + z2 / (2 * n)
    half = Z95 * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    return [max(0.0, (center - half) / denom), min(1.0, (center + half) / denom)]


def median(values: list[float]) -> float:
    s = sorted(values)
    m = len(s)
    if m == 0:
        raise ValueError("median of empty list")
    if m % 2:
        return float(s[m // 2])
    return (s[m // 2 - 1] + s[m // 2]) / 2


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def verify(data: dict) -> dict:
    checks: dict[str, bool] = {}

    c = data["constants"]
    checks["middle_key_matches_source_string"] = (
        sha256_hex(c["probe_middle_source_string"]) == c["probe_middle_key"]
    )
    checks["fixture_sha256_wellformed"] = (
        len(c["probe_fixture_sha256"]) == 64
        and all(ch in "0123456789abcdef" for ch in c["probe_fixture_sha256"])
    )
    checks["fixture_line_count_consistent"] = (
        422 == c["probe_fixture_lines"] and c["probe_fixture_bytes"] == 35767
    )
    checks["probe_keys_distinct"] = len(
        {c["probe_head_key"], c["probe_tail_key"], c["probe_middle_key"]}
    ) == 3

    r1 = data["ring1_dsh_readback_mechanism"]
    sess = r1["sessions"]
    rb = sess["rb"]
    imk = sess["imk"]
    c1 = sess["c1"]

    checks["rb_n"] = len(rb) == r1["derived"]["rb_n"] == 6
    checks["rb_middle_hits"] = (
        sum(1 for s in rb if s["keys"]["MIDDLE_KEY"]) == r1["derived"]["rb_middle_hits"] == 6
    )
    checks["rb_all_keys_true"] = all(
        all(s["keys"].values()) for s in rb
    )
    checks["rb_single_read_each"] = all(s["read_attempts"] == 1 for s in rb)
    recomputed_wilson = wilson95(r1["derived"]["rb_middle_hits"], r1["derived"]["rb_n"])
    checks["rb_wilson95"] = (
        abs(recomputed_wilson[0] - r1["derived"]["rb_wilson95"][0]) < 1e-12
        and abs(recomputed_wilson[1] - r1["derived"]["rb_wilson95"][1]) < 1e-12
    )
    rb_totals = [sum(s["B_series"]) for s in rb]
    checks["rb_total_median"] = (
        median(rb_totals) == r1["derived"]["rb_session_total_median"] == 12293.0
    )
    imk_finals = [s["B_series"][-1] for s in imk]
    checks["imk_final_median"] = (
        median(imk_finals) == r1["derived"]["imk_final_request_median"] == 38435.0
    )
    delta = r1["derived"]["rb_session_total_median"] - r1["derived"]["imk_final_request_median"]
    checks["delta_median"] = (
        delta == r1["derived"]["rb_total_minus_imk_final_median"] == -26142.0
    )
    ratio = r1["derived"]["rb_session_total_median"] / r1["derived"]["imk_final_request_median"]
    checks["ratio"] = abs(ratio - r1["derived"]["rb_total_over_imk_final_median"]) < 5e-5
    checks["c1_gate_matches_baseline"] = (
        all(s["delta"] == 2382 and s["B_series"] == [1124, 3506] for s in c1)
        and r1["derived"]["c1_delta"] == 2382
        and r1["derived"]["baseline_r20261103_bounded_delta"] == 2382
        and r1["derived"]["c1_matches_20261103_baseline"] is True
    )
    checks["imk_all_keys_true"] = all(all(s["keys"].values()) for s in imk)
    checks["decision_branch"] = r1["derived"]["decision_branch"] == "recovered_via_read"

    r2 = data["ring2_workbuddy_known_read_positive_control"]
    checks["ring2_n3_all_pass"] = (
        r2["n"] == len(r2["sessions"]) == 3
        and all(s["read_calls"] == 1 and s["keys_all_correct"] and s["read_result_chars"] == 38332
                for s in r2["sessions"])
    )
    r3 = data["ring3_doubao_known_read_first_sampling"]
    checks["ring3_n3_all_pass"] = (
        r3["n"] == len(r3["sessions"]) == 3
        and all(s["read_calls"] == 1 and s["keys_all_correct"] and s["read_result_chars"] == 37367
                for s in r3["sessions"])
        and all(s["usage_fields_in_local_trace"] == "none" for s in r3["sessions"])
    )

    r5 = data["ring5_codex_known_read_positive_control"]
    checks["ring5_n3_all_pass"] = (
        r5["n"] == len(r5["sessions"]) == 3
        and all(s["read_result_bytes"] == 35767
                and s["truncation_marker"] is False
                and s["read_form"] == "cat aggregated_output"
                and s["keys_all_correct"]
                and 2 <= s["commands"] <= 3
                for s in r5["sessions"])
    )

    r6 = data["ring6_yuanbao_known_read_first_session"]
    yb = r6["sessions"]
    checks["ring6_interim_shape"] = (
        r6["n"] == len(yb) == 1
        and r6["status"].startswith("interim:")
        and yb[0]["id"] == "yb-01"
        and yb[0]["read_path_reached"] is True
        and len(yb[0]["read_steps"]) == 2
    )
    checks["ring6_partial_2of3"] = (
        yb[0]["keys_correct"] == {"HEAD_KEY": True, "MIDDLE_KEY": True, "TAIL_KEY": False}
        and yb[0]["keys_correct_count"] == 2
        and yb[0]["TAIL_KEY_observed"] != yb[0]["TAIL_KEY_expected"]
        and yb[0]["TAIL_KEY_expected"] == "COBALT-492"
    )

    # ---- ring8 size-threshold (v3) ----
    r8 = data["ring8_size_threshold"]
    arms = r8["codex_cli"], r8["workbuddy"], r8["doubao_work"]
    checks["ring8_three_arms_four_slots"] = (
        r8["product_arms"] == ["codex_cli", "workbuddy", "doubao_work"]
        and all(a["n"] == 4 and len(a["sessions"]) == 4 for a in arms)
        and len(r8["fixtures"]) == 4
        and [f["bytes"] for f in r8["fixtures"]] == [990, 8129, 65504, 262109]
    )
    cx8 = {s["id"]: s for s in r8["codex_cli"]["sessions"]}
    checks["ring8_codex_no_threshold"] = (
        all(cx8[i]["read_form"] == "full_inline" for i in cx8)
        and cx8["cx-256k"]["max_output_chars"] == 276427
        and cx8["cx-256k"]["truncation_marker"] is False
        and all(s["keys_all_correct"] for s in cx8.values())
    )
    wb8 = {s["id"]: s for s in r8["workbuddy"]["sessions"]}
    checks["ring8_wb_64k_persisted_usage"] = (
        wb8["wb2-64k"]["read_form"] == "persisted_preview_display_model_full"
        and wb8["wb2-64k"]["model_side_full_inferred"] is True
        and wb8["wb2-64k"]["keys_correct_count"] == 3
    )
    checks["ring8_wb_256k_cap_refusal"] = (
        wb8["wb2-256k"]["read_form"] == "tool_refused_token_cap"
        and "exceeds maximum allowed tokens (20000)" in wb8["wb2-256k"]["read_tool_error"]
        and wb8["wb2-256k"]["keys_correct_count"] == 3
    )
    db8 = {s["id"]: s for s in r8["doubao_work"]["sessions"]}
    checks["ring8_doubao_64k_full_inline"] = (
        db8["db-64k"]["read_form"] == "full_inline"
        and db8["db-64k"]["tool_chars_total"] == 68504
        and db8["db-64k"]["keys_all_correct"] is True
    )
    checks["ring8_doubao_256k_cap_grep"] = (
        db8["db-256k"]["read_form"] == "tool_refused_token_cap"
        and "exceeds maximum allowed tokens (25000)" in db8["db-256k"]["read_tool_error"]
        and "Grep" in db8["db-256k"]["compensation"]
        and db8["db-256k"]["keys_correct_count"] == 3
    )

    # ---- ring10 spill-cap sweep (v4) ----
    r10 = data["ring10_spill_cap_sweep"]
    arm_names = ["rb-c512", "rb-c2048", "rb-c8192", "rb-c32768", "rb-c131072"]
    checks["ring10_arms_two_slots_each"] = (
        r10["overall_branch"] == "crossover_bracketed"
        and list(r10["arms"]) == arm_names
        and all(
            r10["arms"][a]["n_valid"] == 2
            and r10["arms"][a]["n_planned"] == 2
            and r10["arms"][a]["sessions_all_keys_correct"] == 2
            and r10["arms"][a]["middle_key_hits"] == 2
            for a in arm_names
        )
        and r10["prereg_seal_16"] == "035ac8ca2aea9b21"
    )
    checks["ring10_read_partition"] = (
        r10["arms"]["rb-c512"]["read_attempts_total"] == 2
        and r10["arms"]["rb-c2048"]["read_attempts_total"] == 2
        and r10["arms"]["rb-c8192"]["read_attempts_total"] == 2
        and r10["arms"]["rb-c32768"]["read_attempts_total"] == 0
        and r10["arms"]["rb-c131072"]["read_attempts_total"] == 0
        and r10["arms"]["rb-c512"]["branch"] == "recovered_via_read"
        and r10["arms"]["rb-c32768"]["branch"] == "answered_without_read"
    )
    checks["ring10_crossover_values"] = (
        r10["crossover"]["largest_cap_with_read"] == "rb-c8192"
        and r10["crossover"]["smallest_cap_without_read"] == "rb-c32768"
        and r10["arms"]["rb-c8192"]["request_counts"] == [3, 3]
        and r10["arms"]["rb-c32768"]["request_counts"] == [2, 2]
    )
    med = {a: r10["arms"][a]["B_input_total_median"] for a in arm_names}
    checks["ring10_cost_medians_exact"] = (
        med["rb-c512"] == 13128.5
        and med["rb-c2048"] == 24966.5
        and med["rb-c8192"] == 74846.0
        and med["rb-c32768"] == 40196.5
        and med["rb-c131072"] == 40211.5
    )
    checks["ring10_nonmonotonic_8192_max_512_min"] = (
        max(med, key=med.get) == "rb-c8192" and min(med, key=med.get) == "rb-c512"
    )
    checks["ring10_first_input_identical"] = (
        all(r10["arms"][a]["B_input_first_median"] == 1724.0 for a in arm_names)
        and r10["arms"]["rb-c131072"]["sessions"][0]["B_input_series"][0] == 1724
    )

    # ---- ring12 middle-position control (v5) ----
    r12 = data["ring12_middle_position"]
    near, far = r12["arms"]["mp-near"], r12["arms"]["mp-far"]
    checks["ring12_arms_two_slots_each"] = (
        r12["prereg_seal_12"] == "2eddfd154415be5e"
        and near["n_valid"] == 2 and far["n_valid"] == 2
        and near["read_attempts_total"] == 0 and far["read_attempts_total"] == 0
        and near["middle_key_hits"] == 2 and far["middle_key_hits"] == 2
        and near["sessions_all_keys_correct"] == 2 and far["sessions_all_keys_correct"] == 2
        and all(s["read_attempts"] == 0 and s["keys_all_correct"] and s["requests"] == 2
                for arm in (near, far) for s in arm["sessions"])
    )
    pe = r12["preview_evidence"]
    checks["ring12_preview_evidence"] = (
        pe["tool_result_chars"] == 32700
        and pe["omitted_bytes"] == 3319
        and pe["far_record_in_preview"] is True
        and pe["middle_record_50pct_in_preview"] is False
        and pe["tail_key_in_preview"] is True
        and pe["footer_tail"].startswith("Omitted 3319 bytes.")
        and "Use read with offset/limit" in pe["footer_tail"]
    )
    checks["ring12_branch"] = (
        r12["branch"] == "answer_visible_no_read"
        and r12["interpretation"].startswith("both asked records visible")
        and near["branch"] == "answered_without_read"
        and far["branch"] == "answered_without_read"
    )
    checks["ring12_b_series_exact"] = (
        [s["B_input_series"] for s in near["sessions"]] == [[1724, 35269], [1724, 35187]]
        and [s["B_input_series"] for s in far["sessions"]] == [[1724, 35562], [1724, 35832]]
        and [s["record_position"] for s in near["sessions"]] == ["4.6%", "4.6%"]
        and [s["record_position"] for s in far["sessions"]] == ["96.3%", "96.3%"]
    )

    r14 = data["ring14_spill_boundary"]
    a9216, a16384 = r14["arms"]["rb-c9216"], r14["arms"]["rb-c16384"]
    checks["ring14_arms_two_slots_each"] = (
        r14["prereg_seal_14"] == "bd0bacce4560e456"
        and a9216["cap_tokens"] == 9216 and a16384["cap_tokens"] == 16384
        and len(a9216["slots"]) == 2 and len(a16384["slots"]) == 2
        and a9216["requests_each"] == 2 and a16384["requests_each"] == 2
        and a9216["read_attempts_each"] == 0 and a16384["read_attempts_each"] == 0
        and a9216["keys_all_correct"] is True and a16384["keys_all_correct"] is True
    )
    checks["ring14_no_spill_evidence"] = (
        a9216["spill_footer"] is None and a16384["spill_footer"] is None
        and a9216["middle_record_in_request2"] == [True, True]
        and a16384["middle_record_in_request2"] == [True, True]
        and a9216["B_input_series"] == [[1724, 38425], [1724, 38794]]
        and a16384["B_input_series"] == [[1724, 38491], [1724, 38465]]
        and r14["outcome_vs_prediction"]["rb-c16384"] == "as predicted (no spill, 0 read)"
        and r14["outcome_vs_prediction"]["rb-c9216"].startswith("prediction wrong")
    )
    checks["ring14_branch"] = (
        r14["branch"] == "read_at_no_cap"
        and r14["interpretation"].startswith("E1 answer-visibility gate")
    )

    # ring16: yuanbao known-read completed (n=3, v7)
    if "ring6_yuanbao_known_read_completed" in data:
        r6f = data["ring6_yuanbao_known_read_completed"]
        ss = {s["id"]: s for s in r6f["sessions"]}
        checks["ring6_completed_shape"] = (
            data["schema"] == "knownread-20261113-v8"
            and r6f["n"] == 3 and r6f["n_planned"] == 3
            and r6f["judge_branch"] == "partial"
            and r6f["passed_all_keys"] == 0
            and r6f["read_path_reached_count"] == 1
            and set(ss) == {"yb-01", "yb-02", "yb-03"}
        )
        checks["ring6_keys_pattern"] = (
            all(s["keys_correct"]["HEAD_KEY"] is True for s in ss.values())
            and ss["yb-01"]["read_path_reached"] is True
            and ss["yb-01"]["keys_correct_count"] == 2
            and ss["yb-02"]["read_path_reached"] is False
            and ss["yb-03"]["read_path_reached"] is False
            and ss["yb-02"]["TAIL_KEY_observed"] == "OBSERVATION_TAIL_VALUE"
            and ss["yb-03"]["TAIL_KEY_observed"] == "AMBER-731"
            and ss["yb-01"]["TAIL_KEY_observed"] == "30e506c93"
            and all(s["TAIL_KEY_expected"] == "COBALT-492" for s in ss.values())
        )
        checks["ring6_first_session_marked_superseded"] = (
            "superseded" in data["ring6_yuanbao_known_read_first_session"]["status"]
            and data["ring6_yuanbao_known_read_first_session"]["n"] == 1
        )

    # ---- ring18 boundary precision + ring17 interim (v8) ----
    if "ring18_boundary_precision" in data:
        r18 = data["ring18_boundary_precision"]
        spill = {x["cap_tokens"]: x for x in r18["spill_sessions"]}
        nospill = {x["cap_tokens"]: x for x in r18["nospill_sessions"]}
        checks["ring18_spill_arms"] = (
            set(spill) == {8941, 8942}
            and spill[8941]["omitted_bytes"] == [323, 323]
            and spill[8942]["omitted_bytes"] == [319, 319]
            and spill[8941]["slots"] == 2 and spill[8942]["slots"] == 2
            and spill[8941]["keys_all_correct"] == 2 and spill[8942]["keys_all_correct"] == 2
        )
        checks["ring18_nospill_arms"] = (
            set(nospill) == {9020, 9021, 9022}
            and all(nospill[c]["read_attempts_total"] == 0 for c in nospill)
            and all(nospill[c]["keys_all_correct"] == 1 for c in nospill)
            and all(nospill[c]["middle_record_in_request2"] is True for c in nospill)
        )
        fixture_chars = 35767
        def _omit(cap: int) -> int:
            return fixture_chars - 4 * (cap - 80)
        checks["ring18_truncation_law"] = (
            r18["truncation_law"].startswith("omitted = 35767 - 4*(cap-80); exact at caps 8192/8941/8942")
            and r18["prior_point"]["cap_tokens"] == 8192
            and r18["prior_point"]["omitted_bytes"] == _omit(8192)
            and _omit(8941) == 323 and _omit(8942) == 319
            and r18["boundary"] == "spill-off boundary in [8943, 9020]: cap 8942 spills, cap 9020 does not; sub-interval not point-resolved"
            and "chars/4 estimator" in r18["trigger_criterion"]
        )
        checks["ring18_prediction_honesty"] = (
            "refuted" in r18["prediction_honesty"]
            and r18["branches"]["ring18"] == "read_at_all_caps"
            and r18["branches"]["ring18b"] == "boundary_below_9021"
            and r18["branches"]["ring18c"] == "boundary_above_9020_side"
        )
    if "ring17_yuanbao_size_interim" in data:
        r17 = data["ring17_yuanbao_size_interim"]
        s1 = r17["sessions"][0]
        checks["ring17_interim_shape"] = (
            r17["status"] == "interim"
            and "screen lock" in r17["note"]
            and s1["slot"] == "yb-s-1k"
            and s1["probe_bytes"] == 990
            and s1["fixture_sha256"] == "1355a449c2c71fdf11b6aff4c1381d3585c27e690171a3e3ef1e2af96388c054"
            and s1["keys_all_correct"] is True
            and s1["tail"] == "JADE-104"
        )

    ok = all(checks.values())
    return {"ok": ok, "checks": checks}


def main() -> int:
    data = json.loads(RESULT.read_text(encoding="utf-8"))
    out = verify(data)
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
