#!/usr/bin/env python3
"""verify.py — 合成联接标签一次交换敏感性：公开派生复算。

改编自 2026-11-28 完成并通过的内部非作者独审独立实现（该独审对全部预注册
计数逐项独立复算吻合，结论 GO）。本脚本从预注册文本与任务口径独立推导，不
读取任何内部收据或作者运行产物；纯合成、纯标准库、无网络、无随机、无墙钟
值（`python3 -B` 与 `python3 -OB` 输出逐字节相同）。仅打印到 stdout，不写
任何文件。

模型（预注册固定）：
  8 行无语义编号；层 1 = 行 0..3，层 2 = 行 4..7。
  行 (0,1) 与行 (4,5) 分别为报告已联接位；报告按行披露已联接行的两个二值轴。
  每层两轴的全量边际已知。每行值 = (a1, a2) ∈ {0,1}^2；真实联合表 = 4^8 = 65536。
  零错误报告键 K = ( 联接对_L1, 残差_L1, 联接对_L2, 残差_L2 )，
  残差 = 该层两个未联接行的两轴 1 计数；键空间 = 16·9·16·9 = 20736。
  错误模式：至多一次交换，且只能在某层的两个已联接位之间交换第二轴披露标签。
  联接对 (p,h),(q,j) 报告交集 ph+qj；交换后 pj+qh；Δ = (p−q)(j−h) ∈ {−1,0,1}。
  真值不变；交换保持两列和，故残差（由已知边际反推）不变。
  统计量：总真实交集 J = Σ_L [ ph+qj + t_L ]，t_L = 该层两未联接行中 (1,1) 的行数。

每键解集比较：
  SolSet0(K)  零错误可达值            = [B+m1−m2, B+M1+M2] 区间（B=联接交集和）
  SolSet1(K)  一次交换预算可达值      = 闭式：SolSet0 平移 {0, Δ1, Δ2} 的并
  SolSetM(K)  仅边际可达值            = 全量边际的 Fréchet 界区间
"""
import hashlib
import itertools
import json
import os
import platform

BITS = (0, 1)
COMBOS = [(a, b) for a in BITS for b in BITS]            # 4 row values
PAIRS = list(itertools.product(COMBOS, repeat=2))        # 16 linked-pair states
RESIDS = [(r, s) for r in (0, 1, 2) for s in (0, 1, 2)]  # 9 residual states


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def key_of(rows):
    """Truth -> zero-error report key."""
    return (
        (rows[0], rows[1]),
        (rows[2][0] + rows[3][0], rows[2][1] + rows[3][1]),
        (rows[4], rows[5]),
        (rows[6][0] + rows[7][0], rows[6][1] + rows[7][1]),
    )


def swap_delta(pair):
    (p, h), (q, j) = pair
    return (p - q) * (j - h)


def linked_inter(pair):
    (p, h), (q, j) = pair
    return p * h + q * j


def unlinked_inter(rows_a, rows_b):
    return sum(1 for r in (rows_a, rows_b) if r == (1, 1))


def recompute_report_J(rows, swap_layer):
    """Simulate the report pipeline: disclosed linked values (optionally
    swapped in one layer's two linked positions, or in both when
    swap_layer == 3 -- used only by the relaxed-budget refutation) plus the
    true unlinked rows; recompute the reported total intersection and the
    residuals the report would derive from known totals minus disclosed
    linked rows. Fully independent of the delta formula."""
    def layer_parts(i0, i1, i2, i3, do_swap):
        p, h = rows[i0]
        q, j = rows[i1]
        if do_swap:
            b = p * j + q * h
            linked = ((p, j), (q, h))
        else:
            b = p * h + q * j
            linked = ((p, h), (q, j))
        t = unlinked_inter(rows[i2], rows[i3])
        R = p + q + rows[i2][0] + rows[i3][0]
        S = h + j + rows[i2][1] + rows[i3][1]
        derived_res = (R - linked[0][0] - linked[1][0],
                       S - linked[0][1] - linked[1][1])
        true_res = (rows[i2][0] + rows[i3][0], rows[i2][1] + rows[i3][1])
        return b + t, derived_res, true_res

    v1 = layer_parts(0, 1, 2, 3, swap_layer in (1, 3))
    v2 = layer_parts(4, 5, 6, 7, swap_layer in (2, 3))
    return v1[0] + v2[0], (v1[1], v2[1]), (v1[2], v2[2])


def frechet2(r, s):
    return (max(0, r + s - 2), min(r, s))


def main():
    script_path = os.path.abspath(__file__)

    # ---------------- delta space over the 16 linked-pair states ----------------
    delta_of = {}
    d_pos = d_neg = d_zero = 0
    for pair in PAIRS:
        d = swap_delta(pair)
        delta_of[pair] = d
        if d > 0:
            d_pos += 1
        elif d < 0:
            d_neg += 1
        else:
            d_zero += 1
    delta_range_ok = all(d in (-1, 0, 1) for d in delta_of.values())

    # delta formula validated by direct recomputation over all 16 pair states
    # with a placeholder unlinked intersection 0:
    formula_ok = 0
    for (p, h), (q, j) in PAIRS:
        rows = [(p, h), (q, j), (0, 0), (0, 0), (0, 0), (0, 0), (0, 0), (0, 0)]
        v_no, _, _ = recompute_report_J(rows, 0)
        v_sw, _, _ = recompute_report_J(rows, 1)
        if v_sw - v_no == swap_delta(((p, h), (q, j))):
            formula_ok += 1

    # ---------------- truth enumeration: 4^8 = 65536 ----------------
    sol0 = {}   # key -> set of zero-error values
    sol1 = {}   # key -> set of budget values (<=1 swap)
    sigJ = {}   # (R1,S1,R2,S2) -> set of true J (marginals-only, brute)
    key_count = {}
    per_truth_ok = 0
    residual_invariance_ok = 0
    n_truths = 0
    for rows in itertools.product(COMBOS, repeat=8):
        n_truths += 1
        k = key_of(rows)
        j_no, der_res, true_res = recompute_report_J(rows, 0)
        j_sw1, der1, _ = recompute_report_J(rows, 1)
        j_sw2, der2, _ = recompute_report_J(rows, 2)
        if der1 == true_res and der2 == true_res:
            residual_invariance_ok += 1
        d1 = swap_delta(k[0])
        d2 = swap_delta(k[2])
        if set([j_no, j_sw1, j_sw2]) == set([j_no, j_no + d1, j_no + d2]) \
                and j_no == linked_inter(k[0]) + unlinked_inter(rows[2], rows[3]) \
                + linked_inter(k[2]) + unlinked_inter(rows[6], rows[7]):
            per_truth_ok += 1
        sol0.setdefault(k, set()).add(j_no)
        s = sol1.setdefault(k, set())
        s.add(j_no)
        s.add(j_sw1)
        s.add(j_sw2)
        sig = (rows[0][0] + rows[1][0] + rows[2][0] + rows[3][0],
               rows[0][1] + rows[1][1] + rows[2][1] + rows[3][1],
               rows[4][0] + rows[5][0] + rows[6][0] + rows[7][0],
               rows[4][1] + rows[5][1] + rows[6][1] + rows[7][1])
        sigJ.setdefault(sig, set()).add(j_no)
        key_count[k] = key_count.get(k, 0) + 1

    # ---------------- direct full key space: 16*9*16*9 = 20736 ----------------
    keys_all = set(itertools.product(PAIRS, RESIDS, PAIRS, RESIDS))
    realized = set(sol1.keys())
    n_keys_direct = len(keys_all)
    n_keys_realized = len(realized)
    keys_identity = (keys_all == realized)
    truths_accounted = sum(key_count.values())

    # ---------------- closed forms + per-key agreement ----------------
    eq1_fail = 0
    eq0_fail = 0
    nohole_fail = 0
    subsetM_fail = 0
    budget_zero_fail = 0
    counts = {
        "M1_widened": 0,
        "M2_lose_origin_primary": 0,
        "M2_alt_widen_not_from_truth_ambiguity": 0,
        "M2_alt_no_residual00": 0,
        "M2_alt_exactly_one_degenerate": 0,
        "M3_both_ends": 0,
        "M4_narrower_than_marginals_primary": 0,
        "M4_alt_zero_error_narrower": 0,
    }
    aux = {
        "solset1_eq_solset0": 0,
        "solset1_eq_solsetM": 0,
        "width1_gt_widthM": 0,
    }
    ext_hist = {}
    gap_hist = {}
    for k in sorted(keys_all):
        pair1, res1, pair2, res2 = k
        d1 = swap_delta(pair1)
        d2 = swap_delta(pair2)
        m1, M1 = frechet2(*res1)
        m2, M2 = frechet2(*res2)
        b1 = linked_inter(pair1)
        b2 = linked_inter(pair2)
        B = b1 + b2
        tlo = m1 + m2
        thi = M1 + M2
        width0 = thi - tlo
        ext_lo = min(0, d1, d2)
        ext_hi = max(0, d1, d2)
        width1 = width0 + ext_hi - ext_lo
        R1 = pair1[0][0] + pair1[1][0] + res1[0]
        S1 = pair1[0][1] + pair1[1][1] + res1[1]
        R2 = pair2[0][0] + pair2[1][0] + res2[0]
        S2 = pair2[0][1] + pair2[1][1] + res2[1]
        mlo = max(0, R1 + S1 - 4) + max(0, R2 + S2 - 4)
        mhi = min(R1, S1) + min(R2, S2)
        widthM = mhi - mlo

        lo1 = B + tlo + ext_lo
        hi1 = B + thi + ext_hi
        closed1 = set(range(lo1, hi1 + 1))
        closed0 = set(range(B + tlo, B + thi + 1))
        closedM = set(range(mlo, mhi + 1))
        # no-hole claim: union of <=3 unit-shifted copies is one interval
        shifted = set(closed0)
        if d1 != 0:
            shifted |= set(range(B + tlo + d1, B + thi + d1 + 1))
        if d2 != 0:
            shifted |= set(range(B + tlo + d2, B + thi + d2 + 1))

        brute1 = sol1[k]
        brute0 = sol0[k]
        if brute1 != closed1:
            eq1_fail += 1
        if brute0 != closed0:
            eq0_fail += 1
        if shifted != closed1 or len(closed1) != hi1 - lo1 + 1:
            nohole_fail += 1
        if not (lo1 >= mlo and hi1 <= mhi and brute1 <= closedM):
            subsetM_fail += 1
        if 0 not in (0, d1, d2):
            budget_zero_fail += 1

        if width1 > width0:
            counts["M1_widened"] += 1
        if not (d1 == 0 and d2 == 0) and width0 >= 1:
            counts["M2_lose_origin_primary"] += 1
        if not (d1 == 0 and d2 == 0) and width0 == 0:
            counts["M2_alt_widen_not_from_truth_ambiguity"] += 1
        if not (d1 == 0 and d2 == 0) and res1 != (0, 0) and res2 != (0, 0):
            counts["M2_alt_no_residual00"] += 1
        w1deg = (M1 == m1)
        w2deg = (M2 == m2)
        if w1deg != w2deg:
            counts["M2_alt_exactly_one_degenerate"] += 1
        if min(d1, d2) < 0 < max(d1, d2):
            counts["M3_both_ends"] += 1
        if width1 < widthM:
            counts["M4_narrower_than_marginals_primary"] += 1
        if width0 < widthM:
            counts["M4_alt_zero_error_narrower"] += 1
        if width1 == width0:
            aux["solset1_eq_solset0"] += 1
        if closed1 == closedM:
            aux["solset1_eq_solsetM"] += 1
        if width1 > widthM:
            aux["width1_gt_widthM"] += 1
        ext_hist[ext_hi - ext_lo] = ext_hist.get(ext_hi - ext_lo, 0) + 1
        gap = widthM - width1
        gap_hist[gap] = gap_hist.get(gap, 0) + 1

    # marginals-only brute vs closed form, over marginal signatures
    sig_fail = 0
    for sig in sorted(sigJ.keys()):
        R1, S1, R2, S2 = sig
        mlo = max(0, R1 + S1 - 4) + max(0, R2 + S2 - 4)
        mhi = min(R1, S1) + min(R2, S2)
        if sigJ[sig] != set(range(mlo, mhi + 1)):
            sig_fail += 1

    # ---------------- witness example ----------------
    w_rows1 = [(0, 0), (1, 1), (0, 0), (0, 0)]
    w_rows2 = [(0, 1), (1, 0), (0, 0), (0, 0)]
    w_rows = tuple(w_rows1 + w_rows2)
    w_j0, w_der, w_tres = recompute_report_J(w_rows, 0)
    w_j1, _, _ = recompute_report_J(w_rows, 1)
    w_j2, _, _ = recompute_report_J(w_rows, 2)
    w_R1 = w_rows[0][0] + w_rows[1][0] + w_rows[2][0] + w_rows[3][0]
    w_S1 = w_rows[0][1] + w_rows[1][1] + w_rows[2][1] + w_rows[3][1]
    w_R2 = w_rows[4][0] + w_rows[5][0] + w_rows[6][0] + w_rows[7][0]
    w_S2 = w_rows[4][1] + w_rows[5][1] + w_rows[6][1] + w_rows[7][1]
    w_key = key_of(w_rows)
    witness = {
        "rows_layer1": [list(r) for r in w_rows1],
        "rows_layer2": [list(r) for r in w_rows2],
        "layer1_marginals_R_S": [w_R1, w_S1],
        "layer2_marginals_R_S": [w_R2, w_S2],
        "marginals_each_1_1": (w_R1 == 1 and w_S1 == 1 and w_R2 == 1 and w_S2 == 1),
        "J_zero_error": w_j0,
        "J_swap_layer1": w_j1,
        "J_swap_layer2": w_j2,
        "claim_J0_eq_1": (w_j0 == 1),
        "claim_swap1_eq_0": (w_j1 == 0),
        "claim_swap2_eq_2": (w_j2 == 2),
        "derived_residuals_equal_truth": (w_der == w_tres),
        "key_in_space": (w_key in keys_all),
        "key_brute_reachable_set": sorted(sol1.get(w_key, set())),
    }

    # ---------------- refutation E1: relaxed budget (compose both swaps) ----------------
    comp_extra_fail_keys = 0
    comp_nohole_fail = 0
    comp_example_key = None
    comp_example_sets = None
    for k in sorted(keys_all):
        pair1, res1, pair2, res2 = k
        d1 = swap_delta(pair1)
        d2 = swap_delta(pair2)
        m1, M1 = frechet2(*res1)
        m2, M2 = frechet2(*res2)
        B = linked_inter(pair1) + linked_inter(pair2)
        tlo = m1 + m2
        thi = M1 + M2
        single = set(range(B + tlo + min(0, d1, d2), B + thi + max(0, d1, d2) + 1))
        composed = set()
        for dd in set([0, d1, d2, d1 + d2]):
            composed |= set(range(B + tlo + dd, B + thi + dd + 1))
        if composed != single:
            comp_extra_fail_keys += 1
            if comp_example_key is None:
                comp_example_key = [list(map(list, pair1)), list(res1),
                                    list(map(list, pair2)), list(res2)]
                comp_example_sets = {
                    "deltas": [d1, d2],
                    "single_swap_reachable": sorted(single),
                    "composed_reachable": sorted(composed),
                }
        if len(composed) != max(composed) - min(composed) + 1:
            comp_nohole_fail += 1
    # explicit concrete counterexample key (hand-picked, delta +1 in both layers)
    star = ((((1, 0), (0, 1)), (0, 0)), (((1, 0), (0, 1)), (0, 0)))
    star_key = (star[0][0], star[0][1], star[1][0], star[1][1])
    star_in_space = star_key in keys_all
    star_brute = sorted(sol1.get(star_key, set()))
    star_rows = [(1, 0), (0, 1), (0, 0), (0, 0), (1, 0), (0, 1), (0, 0), (0, 0)]
    star_j0, _, _ = recompute_report_J(star_rows, 0)
    star_j1, _, _ = recompute_report_J(star_rows, 1)
    star_j2, _, _ = recompute_report_J(star_rows, 2)
    star_j_both, sder, strut = recompute_report_J(star_rows, 3)
    star_res_ok = (sder == strut)
    refutation = {
        "relaxed_budget": "swap allowed independently in BOTH layers (deltas compose)",
        "keys_where_composed_set_differs": comp_extra_fail_keys,
        "no_hole_violations_under_composition": comp_nohole_fail,
        "first_differing_key": comp_example_key,
        "first_differing_sets": comp_example_sets,
        "counterexample_key_star": {
            "key": [list(map(list, star_key[0])), list(star_key[1]),
                    list(map(list, star_key[2])), list(star_key[3])],
            "in_key_space": star_in_space,
            "deltas": [swap_delta(star_key[0]), swap_delta(star_key[2])],
            "J_zero_error": star_j0,
            "J_swap_layer1": star_j1,
            "J_swap_layer2": star_j2,
            "J_swap_both_layers_recomputed": star_j_both,
            "both_swap_residual_invariance": star_res_ok,
            "single_swap_budget_set": star_brute,
            "composed_budget_set": sorted(set([star_j0, star_j1, star_j2, star_j_both])),
            "extra_value_outside_claimed_budget": star_j_both not in set([star_j0, star_j1, star_j2]),
            "budget_set_claim_broken": sorted(set([star_j0, star_j1, star_j2, star_j_both])) != sorted(set([star_j0, star_j1, star_j2])),
            "no_hole_still_holds_for_star": (
                len(set([star_j0, star_j1, star_j2, star_j_both])) ==
                max(star_j0, star_j1, star_j2, star_j_both) - min(star_j0, star_j1, star_j2, star_j_both) + 1),
        },
    }

    result = {
        "page": "合成联接标签一次交换敏感性-2026-11-28 公开派生复算",
        "derivation_note": "adapted from the independent non-author audit implementation that "
                           "reproduced every prereg count on 2026-11-28; no internal receipts "
                           "or author run artifacts are read; pure synthetic domain",
        "python_version": platform.python_version(),
        "script_sha256": sha256_file(script_path),
        "layer_delta_space": {
            "pairs_checked": len(PAIRS),
            "delta_in_minus1_0_1": delta_range_ok,
            "delta_positive": d_pos,
            "delta_negative": d_neg,
            "delta_zero": d_zero,
            "formula_validated_by_recompute": formula_ok,
        },
        "enumeration": {
            "n_truths": n_truths,
            "claim_n_truths_65536": (n_truths == 65536),
            "n_keys_direct": n_keys_direct,
            "claim_n_keys_20736": (n_keys_direct == 20736),
            "n_keys_realized": n_keys_realized,
            "keys_direct_eq_realized": keys_identity,
            "truths_accounted": truths_accounted,
            "no_double_count": (truths_accounted == n_truths),
            "n_marginal_signatures": len(sigJ),
            "marginals_brute_eq_closedform_failures": sig_fail,
        },
        "per_truth_checks": {
            "achievable_eq_shift_set": per_truth_ok,
            "achievable_check_failures": n_truths - per_truth_ok,
            "budget_set_is_0_delta1_delta2": per_truth_ok == n_truths,
            "residual_invariance_under_swap": residual_invariance_ok,
            "residual_invariance_failures": n_truths - residual_invariance_ok,
        },
        "per_key_agreement": {
            "keys_compared": n_keys_direct,
            "solset1_brute_neq_closedform": eq1_fail,
            "claim_per_key_equal": (eq1_fail == 0),
            "solset0_brute_neq_closedform": eq0_fail,
            "no_hole_violations": nohole_fail,
            "claim_no_holes": (nohole_fail == 0),
            "budget_lacks_zero": budget_zero_fail,
            "solset1_not_subset_solsetM": subsetM_fail,
        },
        "counts": counts,
        "claims_under_test": {
            "note": "author-level result counts from 2026-11-27; this page recomputes them "
                    "independently in the same synthetic domain",
            "n_truths_claimed": 65536,
            "n_keys_claimed": 20736,
            "M1_widened_claimed": 9072,
            "M2_lose_origin_claimed": 7168,
            "M3_both_ends_claimed": 648,
            "M4_narrower_claimed": 12920,
        },
        "aux_counts": aux,
        "distributions": {
            "ext_histogram": {str(k2): ext_hist[k2] for k2 in sorted(ext_hist)},
            "widthM_minus_width1_histogram": {str(k2): gap_hist[k2] for k2 in sorted(gap_hist)},
        },
        "witness": witness,
        "refutation": refutation,
    }

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
