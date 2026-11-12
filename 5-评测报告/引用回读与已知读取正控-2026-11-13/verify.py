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
            data["schema"] == "knownread-20261113-v16"
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
    # ---- ring20 sizegen (v9) ----
    if "ring20_sizegen" in data:
        r20 = data["ring20_sizegen"]
        p = r20["probes"]
        checks["ring20_shape"] = (
            set(p) == {"dsh-1k", "dsh-8k", "dsh-64k", "dsh-256k"}
            and r20["cap_tokens"] == 8192 and r20["budget_chars"] == 32448
            and p["dsh-1k"]["measured_omitted"] is None and p["dsh-8k"]["measured_omitted"] is None
            and p["dsh-64k"]["measured_omitted"] == 33056 == p["dsh-64k"]["predicted_omitted"]
            and p["dsh-256k"]["measured_omitted"] == 229665
            and p["dsh-256k"]["predicted_omitted"] == 229661
            and all(x["keys_all_correct"] is True for x in p.values())
            and all(x["read_attempts"] == (1 if x["spill"] else 0) for x in p.values())
            and p["dsh-256k"]["b_series"] == [1736, 35430, 36993]
        )
        checks["ring20_law_break_honesty"] = (
            p["dsh-256k"]["as_predicted"] is False
            and r20["overall_branch"] == "truncation_ratio_differs"
            and "approximation" in r20["law_status"]
            and "+4" in r20["law_status"]
            and r20["qualitative_generalization"] is True
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

    # ---- ring23 cost crossover + ring24 read unbounded (v10) ----
    if "ring23_cost_crossover" in data:
        r23 = data["ring23_cost_crossover"]
        checks["ring23_crossover_shape"] = (
            r23["kind"].startswith("derived-only")
            and r23["inline_overhead_estimate"] == 2668.0
            and r23["rb_minus_inline"]["probe_64k"] == 5411.0
            and r23["rb_minus_inline"]["probe_256k"] == -190618.0
            and r23["crossover_probe_chars"] == 71491.0
            and r23["preview_r2_identical_in_r3"] == [True, True]
            and r23["read_targeted_windows_bytes"] == [85, 850]
            and "loss_zone" in r23["regimes"]
        )
    if "ring24_read_unbounded" in data:
        r24 = data["ring24_read_unbounded"]
        checks["ring24_unbounded_shape"] = (
            r24["prereg_seal_24"] == "cd1f2ac5d8f0cbed"
            and r24["r2_omitted"] == [33056, 33056]
            and r24["r3_read_bounded"] == [False, False]
            and r24["r3_read_omitted_matches_prediction"] == [False, False]
            and r24["middle_visible_via_read"] == [True, True]
            and r24["read_attempts_total"] == 2
            and r24["sessions_all_keys_correct"] == 2
            and r24["branch"] == "read_result_unbounded"
            and "first-layer" in r24["finding"]
        )

    # ---- ring26/27/28/29/30 fuel-map (v11) ----
    if "ring26_usage_unit" in data:
        r = data["ring26_usage_unit"]
        checks["ring26_usage_unit_shape"] = (
            r["source_seal_26"] == "9c5d9242b026a2ee"
            and r["rho_chars_per_token_422"] == 1.8529
            and r["spill_regression_slope_tokens_per_cap"] == 2.1497
            and r["chars_per_4_prediction"] == 2.159
            and r["token_aligned_prediction"] == 1.0
            and r["verdict"] == "budget_unit_char_proxy"
            and r["cross_shape_delta_at_cap_8192"]["422-line"] == 17611
        )
    if "ring27_codex_usage" in data:
        r = data["ring27_codex_usage"]
        checks["ring27_codex_usage_shape"] = (
            r["input_tokens_by_probe"]["64k"] == 29074
            and r["input_tokens_by_probe"]["256k"] == 30055
            and r["delta_64k_minus_1k"] == 16841
            and "superseded" in r["correction_by_ring28"]
            and r["verdict"] == "client_record_exceeds_ingest"
        )
    if "ring28_codex_bracket" in data:
        r = data["ring28_codex_bracket"]
        checks["ring28_codex_bracket_shape"] = (
            r["prereg_seal_28"] == "fd0acae77084bace"
            and r["ingest_est_tokens"] == {"80k": 17149, "112k": 16234, "192k": 16682}
            and r["cap_char_bracket_superseded"] == [65589, 66795]
            and r["cap_char_bracket_corrected"] == [29300, 31000]
            and r["silent_clip"] is True
            and "no truncation marker" in r["silent_clip_evidence"]
            and r["verdict"] == "ingest_cap_plateau"
        )
    if "ring29_doubao_bracket" in data:
        r = data["ring29_doubao_bracket"]
        checks["ring29_doubao_bracket_shape"] = (
            r["prereg_seal_29"] == "9c102bbd5fa9f75e"
            and "exceeds maximum allowed tokens (25000)" in r["refusal_text_112k"]
            and r["estimator_chars_per_token_exact"] is True
            and "MIDDLE judgment VOID" in r["keys"]["80k"]
            and "fixture defect" in r["incident"]
            and r["tool_output_clip"]["kept_chars"] == 6438
            and r["tool_output_clip"]["independent_of_token_refusal"] is True
            and r["verdict"] == "dual_mechanism_refusal_plus_clip"
        )
    if "ring30_wb_bracket" in data:
        r = data["ring30_wb_bracket"]
        checks["ring30_wb_bracket_shape"] = (
            r["prereg_seal_30"] == "59724333ed7f333f"
            and r["wb_80k"]["keys"] == "3/3"
            and "80,034" in r["wb_80k"]["model_side"]
            and r["wb_112k_wb_192k"]["status"] == "waiting_user"
            and "cannot be excluded" in r["wb_112k_wb_192k"]["confound"]
            and "not real tokens" in r["cross_product_conclusion"]
            and r["verdict"] == "gate_on_estimate_not_reality_partial_bracket"
        )

    # ring32/33/34 (v12)
    if "ring32_codex_cjk_unit" in data:
        r = data["ring32_codex_cjk_unit"]
        checks["ring32_cjk_shape"] = (
            r["prereg_seal_32"] == "7e9c353e31d749dd" and r["rev3_seal"] == "1f1a680449fd64bf"
            and r["sessions"] == 5
            and r["prereg_branch"] == "mixed_or_invalid (both preregistered bands missed; honest label)"
            and "CLI-own-tokenizer" in r["refined_finding"]
            and "third documented separation" in r["rollout_vs_model_face"]
        )
    if "ring33_rho_calibration" in data:
        r = data["ring33_rho_calibration"]
        checks["ring33_rho_shape"] = (
            r["prereg_seal_33"] == "d3ffe898ae4d78b7"
            and r["cal_01"]["verdict"] == "anomalous_session_excluded"
            and r["cal_02"]["verdict"] == "rho_measured"
            and abs(r["rho_cjk_measured"] - 2.072) < 1e-9
            and r["expected_band"] == [1.5, 2.2]
        )
    if "ring34_calibrated_bracket" in data:
        r = data["ring34_calibrated_bracket"]
        checks["ring34_shape"] = (
            r["prereg_seal_34"] == "17c63dae1031b219" and len(r["results"]) == 4
            and "CHAR-BASED CAP REFUTED" in r["behavioral_verdict"]
            and r["prereg_branch"].startswith("mixed_or_invalid")
            and "fallible instrument" in r["instrument_caveat"]
            and len(r["corrections"]) == 3
        )
        slots = {x["slot"]: x for x in r["results"]}
        checks["ring34_arms"] = (
            slots["a-full-01"]["rg_middle_compensation"] is True
            and slots["a-full-02"]["ingest_est_tokens"] == 16653
            and slots["c-full-01"]["rg_middle_compensation"] is True
            and slots["c-full-02"]["keys"] == "2/3"
        )
    # corrections present (v12 explicit-supersede discipline)
    _r27 = data["ring27_codex_usage"]
    _c = _r27.get("correction", {}) if isinstance(_r27.get("correction"), dict) else {}
    checks["ring27_correction_present"] = (
        _r27.get("status") in ("partially_superseded_by_ring34", "fully_superseded_by_ring39_for_byte_derived_numbers")
        and (abs(_c.get("rho_ascii_corrected", 0) - 1.807) < 1e-9 or "ring39" in _r27.get("correction_note_v13", ""))
        and ("rg" in _c.get("evidence", "") or "collapsed" in _r27.get("correction_note_v13", ""))
    )
    checks["ring28_bracket_superseded"] = (
        data["ring28_codex_bracket"]["cap_char_bracket_superseded"] == [65589, 66795]
        and data["ring28_codex_bracket"]["cap_char_bracket_corrected"] == [29300, 31000]
        and "recomputed" in data["ring28_codex_bracket"]["correction_note"]
    )

    # ring36/39 (v13)
    if "ring36_law_panel" in data:
        r = data["ring36_law_panel"]
        checks["ring36_shape"] = (
            r["prereg_seal_36"] == "613734c39b7feaf1"
            and r["rows_total"] == 101 and r["spill_rows"] == 76 and r["no_spill_rows"] == 25
            and r["max_deviation_chars"] == 4
            and r["branch"] == "law_holds_full_panel"
            and "9 executors" in r["finding"]
        )
    if "ring39_codex_collapse" in data:
        r = data["ring39_codex_collapse"]
        fl = r["fold_layout"]
        checks["ring39_shape"] = (
            r["prereg_seal_39_rev2"] == "9f688f251c1218ac"
            and r["sessions"] == 6 and r["all_keys_correct"] == 6
            and all(v == {"head_kept": 5000, "tail_kept": 5000} for v in fl.values()) and len(fl) == 3
            and r["request_invariance"]["r1_bytes"] == 30486
            and "input_tokens" in r["usage_semantics"]
            and r["relay_bodies_sealed"] is True
            and len(r["supersedes"]) == 4
        )
        checks["ring2728_superseded_by_ring39"] = (
            data["ring27_codex_usage"]["status"] == "fully_superseded_by_ring39_for_byte_derived_numbers"
            and data["ring28_codex_bracket"]["status"] == "superseded_by_ring39"
        )

    # ring41 + ring39 correction (v14)
    if "ring41_foldrefine" in data:
        r = data["ring41_foldrefine"]
        ss = {s["slot"]: s for s in r["sessions"]}
        cf = ss["cjkfold-01"]
        checks["ring41_shape"] = (
            r["prereg_seal_41"] == "6b2b6337e94f5a31"
            and len(r["sessions"]) == 4 and r["all_keys_correct"] is True
            and r["fold_trigger_threshold_bracket_bytes"] == "(10000, 12000]"
            and ss["b10k-01"]["folded"] is False
            and ss["b12k-01"]["folded"] is True
            and ss["b12k-01"]["head_bytes"] == 5000 and ss["b12k-01"]["tail_bytes"] == 5000
            and cf["head_bytes"] == 5000 and cf["tail_bytes"] == 5000
            and cf["head_chars"] == 2920 and cf["tail_chars"] == 2866
            and cf["probe_bytes"] == 20634 and cf["probe_chars"] == 12000
            and cf["declared_original_tokens"] == 5159
            and ss["rglarge-01"]["folded"] is True
            and r["grep_output_folded_too"] is True
            and r["anatomy"]["retention_unit"] == "bytes (5000 per side)"
            and r["anatomy"]["marker_unit"] == "chars"
            and "bytes/4" in r["anatomy"]["declared_tokens_unit"]
            and r["anatomy"]["fold_carried_verbatim_in_later_requests"] is True
        )
        checks["ring41_bracket_honesty"] = (
            "both preregistered branches" in r["prereg_branch_honesty"]
        )
    # ring43/44/45 + corrections (v15)
    if "ring43_fold_gate" in data:
        r = data["ring43_fold_gate"]
        ss = {x["slot"]: x for x in r["sessions"]}
        checks["ring43_shape"] = (
            r["prereg_seal_43"] == "693cc80847f36bd1"
            and len(r["sessions"]) == 2
            and ss["fg-10k04-01"]["bytes"] == 10004 and ss["fg-10k04-01"]["folded"] is True
            and ss["fg-10k04-01"]["marker_chars_truncated"] == 4
            and ss["fg-10k512-01"]["bytes"] == 10512 and ss["fg-10k512-01"]["folded"] is True
            and r["branch"] == "fold_gate_at_10004"
            and "refuted" in r["finding"]
        )

    if "ring44_wb_retry" in data:
        r = data["ring44_wb_retry"]
        ss = {x["slot"]: x for x in r["sessions"]}
        checks["ring44_shape"] = (
            r["prereg_seal_44"] == "3081c832267de6ed"
            and len(r["sessions"]) == 2
            and ss["wb-r-112k"]["refusal_est_tokens"] == 28000
            and ss["wb-r-112k"]["refusal_cap_tokens"] == 20000
            and ss["wb-r-192k"]["refusal_est_tokens"] == 42465
            and ss["wb-r-192k"]["keys_correct_count"] == 3
            and r["branch"] == "pause_not_deterministic_transients"
            and r["findings"]["pause_not_deterministic"] == "Ring 30 waiting_user pauses are transient occurrences, not deterministic size gates; Ring 30 behaviour cell corrected"
        )

    if "ring45_doubao_80k_clean" in data:
        r = data["ring45_doubao_80k_clean"]
        ssn = r["session"]
        checks["ring45_shape"] = (
            r["prereg_seal_45"] == "2645a291e4e0d988"
            and ssn["slot"] == "db-80kc"
            and ssn["keys_correct"] == "3/3"
            and ssn["truncation_marker"] is True and ssn["refusal"] is False
            and ssn["middle_value"] == "ae13b824f05b5766a6eb027a0d667089e5c8e3499a80640f366b415607c7f3a2"
            and r["branch"] == "compensated_3of3"
        )
        checks["ring2945_corrections_present"] = (
            data["ring29_doubao_bracket"].get("correction_v15", {}).get("void_cell_closed_by_ring_45", "") != ""
            and data["ring30_wb_bracket"].get("correction_v15", {}).get("waiting_user_transient", "") != ""
        )

    if "ring47_estimator_map" in data:
        r = data["ring47_estimator_map"]
        ws = {x["slot"]: x for x in r["wb_sessions"]}
        checks["ring47_shape"] = (
            r["prereg_seal_47"] == "d374de4af726889c"
            and r["branch"] == "wb_estimator_diverges_at_wb-e-224k"
            and len(r["wb_sessions"]) == 4
            and ws["wb-e-96k"]["est_tokens"] == 24000
            and ws["wb-e-160k"]["est_tokens"] == 40000
            and ws["wb-e-224k"]["est_tokens"] == 42465
            and r["doubao_branch"] == "db_estimator_not_observable_at_128k_model_avoided_full_read"
        )

    if "ring47b_estsat" in data:
        r = data["ring47b_estsat"]
        ss = {x["slot"]: x for x in r["sessions"]}
        checks["ring47b_shape"] = (
            r["prereg_seal_47b"] == "aaee74ca6419f100"
            and r["branch"] == "other_all_three_prereg_hypotheses_refuted"
            and ss["wb-e2-192k-alt"]["est_tokens"] == 28978
            and ss["wb-e2-176k"]["est_tokens"] == 42464
            and "refuted" in r["branch"]
        )

    checks["ring44_estimator_update_v16"] = (
        "saturation" in data.get("ring44_wb_retry", {}).get("estimator_update_v16", {}).get("content_dependent_claim_refined", "")
    )

    if "ring39_codex_collapse" in data and "ring41_foldrefine" in data:
        c = data["ring39_codex_collapse"].get("correction_v14", {})
        checks["ring39_correction_v14"] = (
            c.get("silent_claim_withdrawn") is True
            and c.get("retention_unit_corrected_chars_to_bytes") is True
            and "no file path" in c.get("actual_behavior", "")
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
