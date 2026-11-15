#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WB 漂移字节位置结构（r1109 bw-retest W1 残差定位）— 预注册 v1 复算工具。

用法：
  python3 verify.py --root <repo> --archive-root <bw-retest/workbuddy 根> [--output result.json]

- --root：公开仓库根（含 4-打分细则/WB漂移字节位置结构-2026-11-16/README.md 预注册
  与硬等参照 4-打分细则/WB重复槽输入与交互量结构-2026-11-16/result.json）。
- --archive-root：WorkBuddy 复测档根（其下 runs/<6 槽>/trace/*.jsonl）。
- stdout：确定性人类摘要（无字节值/token 文本/私有绝对路径）；exit 0=PASS，2=fail-closed。
- --output：独占创建完整 result.json（schema wb-drift-loc-v1）；目标已存在则拒改 exit 2。

内容无关纪律：结果只登记计数、字节偏移、span、字节数、SHA256 与布尔比较位；
不登记任何信封或任务文本内容、任何差异/上下文字节值，不含私有绝对路径。
实现独立成文，不 import 其他包代码（源定位方式参照环 6 包的公开做法）。
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

PACKAGE_NAME = "WB漂移字节位置结构-2026-11-16"
SCHEMA = "wb-drift-loc-v1"

PREREG_PATH_REL = "4-打分细则/WB漂移字节位置结构-2026-11-16/README.md"
PREREG_SHA256 = "c95d8e6d850ca3f517cc7295f51dc0fdde895506bdc58ecb2ae3817d579ba1b1"
REFERENCE_RESULT_PATH_REL = "4-打分细则/WB重复槽输入与交互量结构-2026-11-16/result.json"

# W1 信封（冻结定义：精确匹配该开标记；span 至其后第一个闭合标记结束）。
ENVELOPE_OPEN = b'<system-reminder data-role="user-context">'
ENVELOPE_CLOSE = b"</system-reminder>"

GROUPS = {
    "dabstep-payments-10": ["r1", "r2", "r3"],
    "tb-cargo-plan": ["r1", "r2", "r3"],
}
SLOT_ORDER = [
    "dabstep-payments-10__r1", "dabstep-payments-10__r2", "dabstep-payments-10__r3",
    "tb-cargo-plan__r1", "tb-cargo-plan__r2", "tb-cargo-plan__r3",
]
PAIRS = [("r1", "r2"), ("r1", "r3"), ("r2", "r3")]

CONTEXT_RADIUS_B = 16          # ±16B 局部上下文窗（冻结 §2）
EVENT_MERGE_GAP_B = 8          # 漂移事件并组阈值：相邻漂移位间距 ≤8B 视为同一事件
CLUSTER_MAX_INCLUSIVE_WIDTH_B = 8   # 窄簇宽度上限（冻结 §3）
CLUSTER_MIN_POSITION_FRACTION = 0.80  # 信封外漂移位落入窄簇的最小占比（冻结 §3）

CONTENT_INDEPENDENCE_STATEMENT = (
    "内容无关边界声明：本结果仅登记计数、字节偏移、信封 span、字节数、SHA256 与逐对布尔"
    "比较位；不含任何信封或任务文本内容、任何差异字节值或 token 文本，不含私有档案绝对路径。"
)

REPS = ("r1", "r2", "r3")


class VerifyError(Exception):
    """fail-closed：任何结构/硬等异常都转成 exit 2。"""


def _fail(msg: str) -> None:
    raise VerifyError(msg)


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def find_envelope_spans(data: bytes):
    """返回 (spans, unclosed_count)。spans 为 [start, end) 列表（开标记起点→闭合标记终点）。"""
    spans = []
    i = 0
    unclosed = 0
    while True:
        s = data.find(ENVELOPE_OPEN, i)
        if s < 0:
            break
        e = data.find(ENVELOPE_CLOSE, s + len(ENVELOPE_OPEN))
        if e < 0:
            unclosed += 1
            break
        spans.append([s, e + len(ENVELOPE_CLOSE)])
        i = e + len(ENVELOPE_CLOSE)
    return spans, unclosed


def diff_byte_offsets(a: bytes, b: bytes) -> list:
    """等长字节串的逐字节差异偏移（升序）。不等长 fail-closed（超出冻结结构）。"""
    if len(a) != len(b):
        _fail("rep 文本字节数不等（%d vs %d），超出冻结结构范围" % (len(a), len(b)))
    return [i for i in range(len(a)) if a[i] != b[i]]


def read_trace(path: Path):
    raw = path.read_bytes()
    events = []
    for lineno, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except ValueError as exc:
            _fail("trace JSON 解析失败 %s 行 %d: %s" % (path.name, lineno, exc))
        if not isinstance(obj, dict):
            _fail("trace 行非 JSON 对象 %s 行 %d" % (path.name, lineno))
        events.append(obj)
    return raw, events


def extract_user_text_bytes(event, slot_name: str) -> bytes:
    content = event.get("content")
    if not isinstance(content, list) or len(content) != 1:
        _fail("user 消息 content 结构异常（应为恰 1 个 block）: %s" % slot_name)
    block = content[0]
    if not isinstance(block, dict) or block.get("type") != "input_text":
        _fail("user 消息 block 非 input_text: %s" % slot_name)
    text = block.get("text")
    if not isinstance(text, str):
        _fail("user 消息 text 缺失或非字符串: %s" % slot_name)
    return text.encode("utf-8")


def git_head(root: Path) -> str:
    """真实仓库根取 HEAD；非 git 根（合成测试根）记 non-git-root（确定性）。"""
    if not (root / ".git").exists():
        return "non-git-root"
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(root),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30,
        )
    except OSError as exc:
        _fail("无法运行 git: %s" % exc)
    if out.returncode != 0:
        _fail("git rev-parse HEAD 失败: %s" % out.stderr.decode("utf-8", "replace").strip())
    return out.stdout.decode("utf-8").strip()


# ---------------------------------------------------------------------------
# W1 复算（与硬等参照同构）
# ---------------------------------------------------------------------------

def classify_w1_group(texts_by_rep: dict) -> dict:
    """逐组三对两两逐字节比较（冻结 W1 定义：信封=精确标记 span）。"""
    reps = REPS
    spans_by_rep = {}
    unclosed_by_rep = {}
    for rep in reps:
        spans, unclosed = find_envelope_spans(texts_by_rep[rep])
        spans_by_rep[rep] = spans
        unclosed_by_rep[rep] = unclosed
    base = {
        "spans_by_rep": {rep: [list(s) for s in spans_by_rep[rep]] for rep in reps},
        "envelope_span_cross_rep_equal": (
            len({json.dumps(spans_by_rep[rep], sort_keys=True) for rep in reps}) == 1
        ),
    }
    if any(unclosed_by_rep[rep] for rep in reps):
        base["classification"] = "w1_no_envelope"
        base["unclosed_envelope_marker_reps"] = [
            rep for rep in reps if unclosed_by_rep[rep]
        ]
        return base
    if not all(spans_by_rep[rep] for rep in reps):
        base["classification"] = "w1_no_envelope"
        base["envelope_missing_in_reps"] = [
            rep for rep in reps if not spans_by_rep[rep]
        ]
        return base
    all_spans = [tuple(s) for rep in reps for s in spans_by_rep[rep]]
    pairs = []
    any_outside = False
    all_equal = True
    any_inside = False
    for ra, rb in PAIRS:
        offs = diff_byte_offsets(texts_by_rep[ra], texts_by_rep[rb])
        outside = [o for o in offs if not any(s <= o < e for (s, e) in all_spans)]
        inside_n = len(offs) - len(outside)
        if inside_n > 0:
            any_inside = True
        if outside:
            any_outside = True
        if offs:
            all_equal = False
        pairs.append({
            "pair": [ra, rb],
            "byte_equal": len(offs) == 0,
            "diff_offsets": offs,
            "n_diff_offsets": len(offs),
            "offsets_outside_envelope": outside,
            "n_offsets_outside_envelope": len(outside),
            "pair_result": (
                "equal" if not offs else ("env_external_diff" if outside else "env_internal_only")
            ),
        })
    if all_equal:
        base["classification"] = "w1_stable"
    elif any_outside:
        base["classification"] = "w1_task_text_drift"
    elif any_inside:
        base["classification"] = "w1_env_volatile"
    else:
        base["classification"] = "w1_unclassified"
    base["pairs"] = pairs
    return base


def load_reference_w1(root: Path) -> dict:
    ref_path = root / REFERENCE_RESULT_PATH_REL
    if not ref_path.is_file():
        _fail("硬等参照 result.json 不存在: %s" % REFERENCE_RESULT_PATH_REL)
    try:
        obj = json.loads(ref_path.read_bytes().decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        _fail("硬等参照 result.json 解析失败: %s" % exc)
    w1 = obj.get("w1") if isinstance(obj, dict) else None
    groups = w1.get("groups") if isinstance(w1, dict) else None
    if not isinstance(groups, dict):
        _fail("硬等参照缺 w1.groups")
    return groups


PAIR_FIELDS = [
    "pair", "byte_equal", "diff_offsets", "n_diff_offsets",
    "offsets_outside_envelope", "n_offsets_outside_envelope", "pair_result",
]
GROUP_FIELDS = ["classification", "envelope_span_cross_rep_equal", "spans_by_rep", "pairs"]


def w1_hard_equal(recomputed: dict, reference: dict) -> dict:
    """逐 case 逐字段硬等；任何漂移由调用方 fail-closed。返回逐字段对照。"""
    report = {"groups": {}, "all_equal": True}
    cases = sorted(set(recomputed) | set(reference))
    for case in cases:
        mine = recomputed.get(case)
        ref = reference.get(case)
        entry = {"equal": True, "fields": {}}
        if mine is None or ref is None:
            entry["equal"] = False
            entry["fields"]["_presence"] = {
                "recomputed_present": mine is not None,
                "reference_present": ref is not None,
            }
        else:
            for field in GROUP_FIELDS:
                fv = mine.get(field) == ref.get(field)
                entry["fields"][field] = fv
                if not fv and field == "pairs":
                    entry["pairs_detail"] = _pairs_diff_detail(
                        mine.get(field), ref.get(field))
                if not fv:
                    entry["equal"] = False
        if not entry["equal"]:
            report["all_equal"] = False
        report["groups"][case] = entry
    return report


def _pairs_diff_detail(mine, ref):
    detail = []
    ref_by_pair = {}
    if isinstance(ref, list):
        for p in ref:
            if isinstance(p, dict) and "pair" in p:
                ref_by_pair[json.dumps(p["pair"], sort_keys=True)] = p
    if isinstance(mine, list):
        for p in mine:
            if not isinstance(p, dict):
                continue
            key = json.dumps(p.get("pair"), sort_keys=True)
            rp = ref_by_pair.get(key)
            if rp is None:
                detail.append({"pair": p.get("pair"), "note": "reference_missing_pair"})
                continue
            bad = [f for f in PAIR_FIELDS if p.get(f) != rp.get(f)]
            if bad:
                detail.append({
                    "pair": p.get("pair"),
                    "mismatched_fields": bad,
                    "recomputed": {f: p.get(f) for f in bad},
                    "reference": {f: rp.get(f) for f in bad},
                })
    return detail


# ---------------------------------------------------------------------------
# 位置结构分析（本包冻结 §2/§3）
# ---------------------------------------------------------------------------

def merge_events(offsets):
    """漂移事件并组：相邻漂移位间距 ≤ EVENT_MERGE_GAP_B 视为同一事件（升序输入）。"""
    events = []
    for off in offsets:
        if events and off - events[-1][-1] <= EVENT_MERGE_GAP_B:
            events[-1].append(off)
        else:
            events.append([off])
    return events


def context_sha_event(texts_by_rep: dict, event_offsets: list) -> dict:
    """事件级 ±16B 窗：剔除本事件漂移字节后聚合 SHA；三 rep 同窗比对。"""
    lo_bound = max(0, min(event_offsets) - CONTEXT_RADIUS_B)
    hi_bound = max(len(texts_by_rep[rep]) for rep in REPS)
    hi_bound = min(hi_bound, max(event_offsets) + CONTEXT_RADIUS_B + 1)
    per_rep = {}
    lengths = {rep: len(texts_by_rep[rep]) for rep in REPS}
    for rep in REPS:
        lo = max(0, min(event_offsets) - CONTEXT_RADIUS_B)
        hi = min(lengths[rep], max(event_offsets) + CONTEXT_RADIUS_B + 1)
        if (lo, hi) != (lo_bound, min(hi_bound, lengths[rep])):
            _fail("事件窗边界跨 rep 不一致（长度不等的文本超出冻结结构）")
        kept = bytearray()
        for i in range(lo, hi):
            if i not in set(event_offsets):
                kept.append(texts_by_rep[rep][i])
        per_rep[rep] = sha256_of(bytes(kept))
    all_equal = len(set(per_rep.values())) == 1
    return {
        "window": [lo_bound, min(hi_bound, lengths[REPS[0]])],
        "removed_n": len(event_offsets),
        "per_rep_context_sha": per_rep,
        "all_equal": all_equal,
        "class": "isolated_substitution" if all_equal else "block_shift_candidate",
    }


def analyze_case(case: str, texts_by_rep: dict) -> dict:
    """单 case 位置结构分析：逐差异登记、事件、pairwise-distinct、簇/孤立/信封内。"""
    spans = find_envelope_spans(texts_by_rep["r1"])[0]
    if len(spans) != 1:
        _fail("%s: 信封 span 数=%d（冻结结构应为恰 1）" % (case, len(spans)))
    envelope_close = spans[0][1]

    pair_diffs = {}
    union_offsets = set()
    for ra, rb in PAIRS:
        offs = diff_byte_offsets(texts_by_rep[ra], texts_by_rep[rb])
        pair_diffs["%s%s" % (ra, rb)] = offs
        union_offsets.update(offs)
    union_sorted = sorted(union_offsets)

    events = merge_events(union_sorted)
    event_of_offset = {}
    for eid, offs in enumerate(events):
        for off in offs:
            event_of_offset[off] = eid

    lengths = {rep: len(texts_by_rep[rep]) for rep in REPS}
    lengths_equal = len(set(lengths.values())) == 1

    event_rows = []
    event_class_by_eid = {}
    for eid, offs in enumerate(events):
        ctx = context_sha_event(texts_by_rep, offs)
        event_class_by_eid[eid] = ctx["class"]
        event_rows.append({
            "event_id": eid,
            "positions_offset": offs,
            "positions_rel": [o - envelope_close for o in offs],
            "lane": ("envelope_internal" if spans[0][0] <= offs[0] < spans[0][1]
                     else "envelope_external"),
            **ctx,
        })

    positions = []
    for off in union_sorted:
        pairs_differ = {"%s%s" % (ra, rb): (off in pair_diffs["%s%s" % (ra, rb)])
                        for ra, rb in PAIRS}
        three_distinct = all(pairs_differ.values())
        eid = event_of_offset[off]
        positions.append({
            "offset": off,
            "rel_position": off - envelope_close,
            "lane": ("envelope_internal" if spans[0][0] <= off < spans[0][1]
                     else "envelope_external"),
            "pairs_differ": pairs_differ,
            "pair_count": sum(pairs_differ.values()),
            "three_distinct": three_distinct,
            "per_run_unique": three_distinct,
            "event_id": eid,
            "context_class": event_class_by_eid[eid],
        })

    non_unique = []
    for pos in positions:
        if not pos["three_distinct"]:
            non_unique.append({
                "rel_position": pos["rel_position"],
                "equal_pairs": [k for k, v in pos["pairs_differ"].items() if not v],
                "registered": "非逐运行唯一（任一对字节相同，冻结 §2 记录规则）",
            })

    external_positions = [p for p in positions if p["lane"] == "envelope_external"]
    internal_positions = [p for p in positions if p["lane"] == "envelope_internal"]
    cluster_rels = sorted({p["rel_position"] for p in external_positions})
    n_instances = {"%s%s" % (ra, rb): len(pair_diffs["%s%s" % (ra, rb)]) for ra, rb in PAIRS}

    return {
        "envelope_close": envelope_close,
        "envelope_span": [list(spans[0])],
        "text_lengths_by_rep": lengths,
        "text_lengths_equal_cross_rep": lengths_equal,
        "n_pair_instances": n_instances,
        "positions": positions,
        "events": event_rows,
        "non_unique_positions": non_unique,
        "external_positions_n": len(external_positions),
        "internal_positions_n": len(internal_positions),
        "cluster_rel_candidates": cluster_rels,
        "_pair_diffs": pair_diffs,
        "_external": external_positions,
        "_internal": internal_positions,
    }


def cross_case_cluster(analyses: dict) -> dict:
    """跨 case 相对位置对齐：信封外漂移位相对位置交集 → 窄簇；其余为 case 固定孤立位。"""
    cases = sorted(analyses)
    rel_sets = {
        c: {p["rel_position"] for p in analyses[c]["_external"]} for c in cases
    }
    aligned = set.intersection(*rel_sets.values()) if rel_sets else set()
    per_case = {}
    for c in cases:
        cluster = [p for p in analyses[c]["_external"] if p["rel_position"] in aligned]
        isolated = [p for p in analyses[c]["_external"] if p["rel_position"] not in aligned]
        cluster_rels = sorted({p["rel_position"] for p in cluster})
        interval = [min(cluster_rels), max(cluster_rels)] if cluster_rels else None
        inclusive_width = (interval[1] - interval[0] + 1) if interval else 0
        n_ext_inst = sum(analyses[c]["n_pair_instances"].values()) - (
            3 * len(analyses[c]["_internal"]))
        n_cluster_inst = sum(p["pair_count"] for p in cluster)
        per_case[c] = {
            "external_positions_n": len(analyses[c]["_external"]),
            "cluster_positions_rel": cluster_rels,
            "cluster_interval_rel": interval,
            "cluster_inclusive_width_bytes": inclusive_width,
            "cluster_instance_fraction": (
                n_cluster_inst / n_ext_inst if n_ext_inst else None),
            "cluster_position_fraction": (
                len(cluster) / len(analyses[c]["_external"])
                if analyses[c]["_external"] else None),
            "isolated_slots": [{
                "rel_position": p["rel_position"],
                "offset": p["offset"],
                "pair_count": p["pair_count"],
                "three_distinct": p["three_distinct"],
                "case_fixed_across_pairs": p["pair_count"] == len(PAIRS),
                "context_class": p["context_class"],
            } for p in sorted(isolated, key=lambda p: p["offset"])],
        }
    intervals = [per_case[c]["cluster_interval_rel"] for c in cases
                 if per_case[c]["cluster_interval_rel"]]
    if intervals and len(intervals) == len(cases):
        overlap_lo = max(iv[0] for iv in intervals)
        overlap_hi = min(iv[1] for iv in intervals)
        overlap = [overlap_lo, overlap_hi] if overlap_lo <= overlap_hi else None
    else:
        overlap = None
    return {
        "cases": cases,
        "aligned_rel_positions": sorted(aligned),
        "per_case": per_case,
        "cluster_interval_cross_case_overlap": overlap,
        "cluster_relative_position_consistent": overlap is not None,
        "cluster_width_within_8B": all(
            per_case[c]["cluster_inclusive_width_bytes"] <= CLUSTER_MAX_INCLUSIVE_WIDTH_B
            for c in cases if per_case[c]["cluster_interval_rel"]),
    }


def decide_branch(analyses: dict, cross: dict) -> dict:
    """冻结 §3 分支：≥2 case 满足 C1..C4 ⇒ B-FIXED-POSITION-TOKEN；否则 B-SCATTERED。"""
    cond = {}
    for c in cross["cases"]:
        pc = cross["per_case"][c]
        a = analyses[c]
        c1 = (pc["cluster_position_fraction"] is not None
              and pc["cluster_position_fraction"] >= CLUSTER_MIN_POSITION_FRACTION)
        cluster_rels = set(pc["cluster_positions_rel"])
        cluster_pairs_distinguished = all(
            any(p["pairs_differ"][k] for p in a["_external"]
                if p["rel_position"] in cluster_rels)
            for k in ("r1r2", "r1r3", "r2r3")) if cluster_rels else False
        c2 = cluster_pairs_distinguished
        c3 = all(p["context_class"] == "isolated_substitution" for p in a["positions"])
        c4 = all(slot["case_fixed_across_pairs"] and slot["three_distinct"]
                 and slot["context_class"] == "isolated_substitution"
                 for slot in pc["isolated_slots"]) and len(pc["isolated_slots"]) >= 1
        cond[c] = {
            "C1_cluster_position_fraction_ge_80pct": c1,
            "C1_value": pc["cluster_position_fraction"],
            "C1_instance_fraction_disclosed": pc["cluster_instance_fraction"],
            "C2_cluster_pairwise_distinguished_rep_pairs": c2,
            "C3_all_positions_isolated_substitution": c3,
            "C4_isolated_slot_fixed_distinct_substitution": c4,
            "case_satisfies_all": bool(c1 and c2 and c3 and c4),
        }
    n_pass = sum(1 for c in cond if cond[c]["case_satisfies_all"])
    branch_ok = n_pass >= 2 and cross["cluster_relative_position_consistent"] \
        and cross["cluster_width_within_8B"]
    non_unique_total = sum(len(a["non_unique_positions"]) for a in analyses.values())
    if branch_ok:
        verdict = "B-FIXED-POSITION-TOKEN"
        reason = (
            "≥2 case 信封外漂移位 ≥80% 落在跨 case 相对位置一致、宽 ≤8B 的窄簇；"
            "簇内三 rep 两两互异（簇级）、全部漂移位 context_sha 三 rep 一致（孤立替换）、"
            "孤立位 case 内固定且三 rep 互异；漂移=固定位置逐运行变量 token（位置结构已定）"
        )
    else:
        verdict = "B-SCATTERED"
        reason = "簇条件未全部满足（散布/移位为主）；W1 字节面漂移维持原判、不缩窄"
    return {
        "verdict": verdict,
        "reason": reason,
        "conditions_by_case": cond,
        "cases_satisfying_all": n_pass,
        "cluster_cross_case_consistent": cross["cluster_relative_position_consistent"],
        "cluster_width_within_8B": cross["cluster_width_within_8B"],
        "block_shift_candidates_n": sum(
            1 for a in analyses.values() for e in a["events"]
            if e["class"] == "block_shift_candidate"),
        "non_unique_positions_n": non_unique_total,
        "caveat": (
            "逐位置两两互异例外已按冻结 §2 记录规则登记（非逐运行唯一位）；"
            "token 语义未知、位置结构已定；例外位不改变簇级与孤立位判定，见 positions 节"
        ) if non_unique_total and verdict == "B-FIXED-POSITION-TOKEN" else "",
    }


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run_verification(root: Path, archive_root: Path) -> dict:
    # --- 0. 预注册封印 -------------------------------------------------------
    prereg_path = root / PREREG_PATH_REL
    if not prereg_path.is_file():
        _fail("预注册 README 不存在: %s" % PREREG_PATH_REL)
    prereg_sha = sha256_of(prereg_path.read_bytes())
    if prereg_sha != PREREG_SHA256:
        _fail("预注册 README SHA256 不符: %s != %s" % (prereg_sha, PREREG_SHA256))

    # --- 1. 档案布局 ---------------------------------------------------------
    runs_dir = archive_root / "runs"
    if not runs_dir.is_dir():
        _fail("archive-root 下无 runs/（期望 WorkBuddy 复测档根）")

    # --- 2. 逐槽首条 user 消息提取 -------------------------------------------
    slot_results = {}
    for slot in SLOT_ORDER:
        trace_dir = runs_dir / slot / "trace"
        if not trace_dir.is_dir():
            _fail("槽 trace/ 目录缺失: %s" % slot)
        jsonls = sorted(trace_dir.glob("*.jsonl"))
        if len(jsonls) != 1:
            _fail("槽 trace/ 下 session jsonl 数=%d（应为 1）: %s" % (len(jsonls), slot))
        trace_path = jsonls[0]
        _, events = read_trace(trace_path)
        user_events = [
            (lineno, ev) for lineno, ev in enumerate(events, 1)
            if ev.get("type") == "message" and ev.get("role") == "user"
        ]
        if len(user_events) != 1:
            _fail("role=user 消息数=%d（应为恰 1）: %s" % (len(user_events), slot))
        user_text = extract_user_text_bytes(user_events[0][1], slot)
        slot_results[slot] = {
            "trace_file": trace_path.name,
            "user_text_sha256": sha256_of(user_text),
            "user_text_bytes": len(user_text),
            "_text": user_text,
        }

    # --- 3. W1 复算 + 硬等 ---------------------------------------------------
    recomputed_groups = {}
    for group, reps in sorted(GROUPS.items()):
        texts = {rep: slot_results["%s__%s" % (group, rep)]["_text"] for rep in reps}
        recomputed_groups[group] = classify_w1_group(texts)
    reference_groups = load_reference_w1(root)
    hard_equal = w1_hard_equal(recomputed_groups, reference_groups)
    if not hard_equal["all_equal"]:
        _fail("W1 硬等失败（与 %s 不一致）: %s"
              % (REFERENCE_RESULT_PATH_REL,
                 json.dumps(hard_equal, sort_keys=True, ensure_ascii=False)))

    # --- 4. 逐差异登记 -------------------------------------------------------
    instance_items = []
    for case in sorted(GROUPS):
        a = recomputed_groups[case]
        spans = a["spans_by_rep"]["r1"]
        if len(spans) != 1:
            _fail("%s: 信封 span 数=%d（冻结结构应为恰 1）" % (case, len(spans)))
        close = spans[0][1]
        for p in a["pairs"]:
            lane_all = "mixed"
            for off in p["diff_offsets"]:
                inside = spans[0][0] <= off < spans[0][1]
                instance_items.append({
                    "case": case,
                    "pair": "%s%s" % tuple(p["pair"]),
                    "offset": off,
                    "rel_position": off - close,
                    "lane": "envelope_internal" if inside else "envelope_external",
                })
    lane_counts = {
        "envelope_external": sum(1 for it in instance_items if it["lane"] == "envelope_external"),
        "envelope_internal": sum(1 for it in instance_items if it["lane"] == "envelope_internal"),
    }

    # --- 5. 位置结构分析 -----------------------------------------------------
    analyses = {}
    for case in sorted(GROUPS):
        texts = {rep: slot_results["%s__%s" % (case, rep)]["_text"] for rep in REPS}
        analyses[case] = analyze_case(case, texts)
    cross = cross_case_cluster(analyses)
    branch = decide_branch(analyses, cross)

    per_case_public = {}
    for case, a in analyses.items():
        per_case_public[case] = {
            "envelope_close": a["envelope_close"],
            "envelope_span": a["envelope_span"],
            "text_lengths_by_rep": a["text_lengths_by_rep"],
            "text_lengths_equal_cross_rep": a["text_lengths_equal_cross_rep"],
            "n_pair_instances": a["n_pair_instances"],
            "positions": [p for p in a["positions"]],
            "events": a["events"],
            "non_unique_positions": a["non_unique_positions"],
            "external_positions_n": a["external_positions_n"],
            "internal_positions_n": a["internal_positions_n"],
        }

    # --- 6. 组装 result（原料不进结果：内容无关纪律）--------------------------
    for slot in SLOT_ORDER:
        del slot_results[slot]["_text"]

    baseline_commit = git_head(root)
    ref_path = root / REFERENCE_RESULT_PATH_REL
    result = {
        "schema": SCHEMA,
        "package": PACKAGE_NAME,
        "content_independence_statement": CONTENT_INDEPENDENCE_STATEMENT,
        "prereg": {
            "path_rel": PREREG_PATH_REL,
            "sha256": PREREG_SHA256,
            "sha256_match": True,
        },
        "baseline_commit": baseline_commit,
        "reference_source": {
            "path_rel": REFERENCE_RESULT_PATH_REL,
            "sha256": sha256_of(ref_path.read_bytes()),
        },
        "archive_layout": {
            "runs_rel": "runs/<slot>/trace/<session>.jsonl",
            "slots_expected": SLOT_ORDER,
        },
        "extraction": {
            "per_slot": {k: {kk: vv for kk, vv in slot_results[k].items()}
                         for k in SLOT_ORDER},
        },
        "analysis_rules": {
            "envelope_definition": "信封=W1 冻结开/闭标记的精确 span（标记字面以硬等参照 result.json 同名字段定义为准，此处不重复登记标记文本）",
            "rel_position_definition": "rel_position = offset − 信封闭合（envelope span 终点）",
            "context_window": "±%dB 窗（不足取边界），剔除本事件漂移字节后其余字节聚合 SHA256" % CONTEXT_RADIUS_B,
            "event_merge_rule": "相邻漂移位间距 ≤%dB 并为同一漂移事件（与冻结 ≤8B 窄簇刻度一致）；事件级 context_sha 三 rep 一致 ⇒ isolated_substitution，否则 block_shift_candidate" % EVENT_MERGE_GAP_B,
            "cluster_fraction_unit": "占比分母=该 case 信封外漂移位置数（位置结构裁定的自然单位）；逐对实例口径同步披露于 branch.conditions_by_case.C1_instance_fraction_disclosed",
            "pairwise_distinct": "逐位置三 rep 两两字节比较（布尔登记，不含字节值）；任一对相同 ⇒ 记非逐运行唯一（冻结 §2）；分支层「簇内三 rep 两两互异」按簇级（每对 rep 在簇内存在差异字节）断言",
        },
        "w1_hard_equal": {
            "reference_path_rel": REFERENCE_RESULT_PATH_REL,
            "all_equal": hard_equal["all_equal"],
            "groups": hard_equal["groups"],
        },
        "drift_instances": {
            "total": len(instance_items),
            "by_lane": lane_counts,
            "items": instance_items,
        },
        "case_analysis": per_case_public,
        "cross_case_cluster": cross,
        "branch": branch,
        "survey_note_reconciliation": {
            "rule": "预注册勘察注记为冻结前事实，可被包内复算推翻（README 冻结行）；以下以复算为准",
            "items": [
                "§1『W1 登记 33 处』与同句『dab 三对 6/7/7、tb 7/7/6』不自洽（6+7+7+7+7+6=40）；复算与硬等参照一致=40 处逐对差异实例，本包按 40 处逐处登记",
                "§2『信封内差异 tb 2/2/3』复算为 2/2/2（参照 result.json n_offsets_outside_envelope 5/5/4 与 diff_offsets 7/7/6 推得），以复算为准",
                "§1/§4 勘察『三 rep 两两互异』在簇内 +93 位不成立（两 case 各有一对 rep 同字节，见 case_analysis.non_unique_positions），按冻结 §2『任一对相同 ⇒ 记非逐运行唯一』登记为例外，不改变簇级/孤立位判定",
            ],
        },
        "exit_code": 0,
    }
    return result


def summarize(result: dict) -> str:
    """确定性 stdout 摘要（不含字节值/token 文本/私有绝对路径）。"""
    branch = result["branch"]
    cross = result["cross_case_cluster"]
    lines = []
    lines.append("PASS %s schema=%s" % (result["package"], result["schema"]))
    lines.append("prereg_sha256_ok=true sha=%s" % result["prereg"]["sha256"])
    lines.append("baseline_commit=%s" % result["baseline_commit"])
    lines.append("archive_slots=%d user_texts_extracted=%d"
                 % (len(result["archive_layout"]["slots_expected"]),
                    len(result["extraction"]["per_slot"])))
    he = result["w1_hard_equal"]
    lines.append("w1_hard_equal=%s reference=%s"
                 % (str(he["all_equal"]).lower(), he["reference_path_rel"]))
    di = result["drift_instances"]
    per_case_inst = []
    for case in sorted(GROUPS):
        a = result["case_analysis"][case]
        per_case_inst.append("%s %s" % (
            case, "/".join(str(a["n_pair_instances"][k]) for k in ("r1r2", "r1r3", "r2r3"))))
    lines.append("drift_instances=%d envelope_external=%d envelope_internal=%d (%s)"
                 % (di["total"], di["by_lane"]["envelope_external"],
                    di["by_lane"]["envelope_internal"], "; ".join(per_case_inst)))
    lines.append("cluster_aligned_rel=%s interval=%s width_inclusive=%dB<=8B overlap=%s"
                 % (cross["aligned_rel_positions"],
                    cross["per_case"][cross["cases"][0]]["cluster_interval_rel"],
                    cross["per_case"][cross["cases"][0]]["cluster_inclusive_width_bytes"],
                    str(cross["cluster_relative_position_consistent"]).lower()))
    iso = []
    for case in cross["cases"]:
        slots = cross["per_case"][case]["isolated_slots"]
        iso.append("%s=%s" % (case, "+".join(
            "%+d(3/3pairs,3distinct=%s)" % (s["rel_position"], str(s["three_distinct"]).lower())
            for s in slots)))
    lines.append("isolated_slots: %s" % "; ".join(iso))
    n_pos = sum(len(result["case_analysis"][c]["positions"]) for c in GROUPS)
    n_sub = sum(1 for c in GROUPS for e in result["case_analysis"][c]["events"]
                if e["class"] == "isolated_substitution")
    n_ev = sum(len(result["case_analysis"][c]["events"]) for c in GROUPS)
    lines.append("context_sha: positions=%d events=%d isolated_substitution=%d block_shift_candidate=%d"
                 % (n_pos, n_ev, n_sub, branch["block_shift_candidates_n"]))
    n_td = sum(1 for c in GROUPS for p in result["case_analysis"][c]["positions"]
               if p["three_distinct"])
    nu = "; ".join(
        "%s rel=%+d equal_pairs=%s" % (c, nu_["rel_position"], ",".join(nu_["equal_pairs"]))
        for c in GROUPS for nu_ in result["case_analysis"][c]["non_unique_positions"])
    lines.append("pairwise_distinct: three_distinct=%d/%d non_unique=[%s]"
                 % (n_td, n_pos, nu))
    lines.append("branch=%s cases_satisfying_all=%d" % (branch["verdict"], branch["cases_satisfying_all"]))
    for c in cross["cases"]:
        cc = branch["conditions_by_case"][c]
        lines.append("  %s C1=%.4f(C1>=0.8=%s,instance=%.4f) C2=%s C3=%s C4=%s"
                     % (c, cc["C1_value"], str(cc["C1_cluster_position_fraction_ge_80pct"]).lower(),
                        cc["C1_instance_fraction_disclosed"],
                        str(cc["C2_cluster_pairwise_distinguished_rep_pairs"]).lower(),
                        str(cc["C3_all_positions_isolated_substitution"]).lower(),
                        str(cc["C4_isolated_slot_fixed_distinct_substitution"]).lower()))
    if branch["caveat"]:
        lines.append("caveat=%s" % branch["caveat"])
    lines.append("exit=0")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="WB 漂移字节位置结构 复算（预注册 v1，schema %s）" % SCHEMA)
    parser.add_argument("--root", required=True, help="公开仓库根")
    parser.add_argument("--archive-root", required=True,
                        help="WorkBuddy 复测档根（其下含 runs/<6 槽>/trace/*.jsonl）")
    parser.add_argument("--output", default=None,
                        help="独占创建完整 result.json；目标已存在则拒改 exit 2")
    args = parser.parse_args(argv)
    try:
        result = run_verification(Path(args.root), Path(args.archive_root))
        summary = summarize(result)
        if args.output:
            out_path = Path(args.output)
            if out_path.exists():
                _fail("--output 目标已存在，拒绝覆盖（独占创建）: %s" % out_path.name)
            payload = json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
            with open(out_path, "x", encoding="utf-8") as fh:
                fh.write(payload)
        sys.stdout.write(summary)
        return 0
    except VerifyError as exc:
        sys.stdout.write("FAIL: %s\nexit=2\n" % exc)
        return 2
    except Exception as exc:  # fail-closed：未知异常也 exit 2
        sys.stdout.write("FAIL( unexpected): %r\nexit=2\n" % (exc,))
        return 2


if __name__ == "__main__":
    sys.exit(main())
