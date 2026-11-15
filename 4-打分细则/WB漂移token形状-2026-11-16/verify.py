#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WB 漂移 token 的字节形状（r1109 bw-retest W1 数字 run 形状裁定）— 预注册 v1 复算工具。

用法：
  python3 verify.py --root <repo> --archive-root <bw-retest/workbuddy 根> [--output result.json]

- --root：公开仓库根（含本包冻结 README 预注册与硬等参照
  4-打分细则/WB漂移字节位置结构-2026-11-16/result.json）。
- --archive-root：WorkBuddy 复测档根（其下 runs/<6 槽>/trace/*.jsonl）。
- stdout：确定性人类摘要（无字节值/token 文本/私有绝对路径）；exit 0=PASS，2=fail-closed。
- --output：独占创建完整 result.json（schema wb-token-shape-v1）；目标已存在则拒改 exit 2。

值无关纪律：结果只登记 run 边界（起/止/长）、漂移字节在 run 内 index、字节类
（digit/alpha/other；bof=run 起点为文本首无左邻）、offset/rel、计数、SHA256 与布尔
比较位；不读不登记任何字节值，不比对分隔字节/漂移字节跨 rep 是否同值，
不含私有绝对路径。实现独立成文，不 import 其他包代码
（W1 提取方式与环 6/11 包公开做法同构：runs/<slot>/trace/*.jsonl、role=user、
content[0].type=input_text）。
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

PACKAGE_NAME = "WB漂移token形状-2026-11-16"
SCHEMA = "wb-token-shape-v1"

PREREG_PATH_REL = "4-打分细则/WB漂移token形状-2026-11-16/README.md"
PREREG_SHA256 = "c7fee55520d54ee24ba99a9c0a7c6f35018864511085b0ec02e30f377a9a8ee8"
REFERENCE_RESULT_PATH_REL = "4-打分细则/WB漂移字节位置结构-2026-11-16/result.json"

# W1 信封（冻结定义：精确匹配该开标记；span 至其后第一个闭合标记结束；
# 标记文本不在 result 中重复登记）。
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
REPS = ("r1", "r2", "r3")
PAIRS = [("r1", "r2"), ("r1", "r3"), ("r2", "r3")]

CLASS_DIGIT = "digit"
CLASS_ALPHA = "alpha"
CLASS_OTHER = "other"
CLASS_BOF = "bof"          # run 起点为文本首（无左邻字节），结构性取值
CLASS_VOCAB = [CLASS_DIGIT, CLASS_ALPHA, CLASS_OTHER, CLASS_BOF]

VALUE_INDEPENDENCE_STATEMENT = (
    "值无关边界声明：本结果只登记 run 边界（起/止/长）、漂移字节在 run 内 index、"
    "字节类（digit/alpha/other/bof）、offset/rel_position、计数、SHA256 与布尔比较位；"
    "不读不登记任何漂移字节或分隔字节的字节值，不比对分隔字节/漂移字节跨 rep 是否同值，"
    "不含信封或任务文本内容、不含私有档案绝对路径。"
)


class VerifyError(Exception):
    """fail-closed：任何结构/硬等异常都转成 exit 2。"""


def _fail(msg: str) -> None:
    raise VerifyError(msg)


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def byte_class(b: int) -> str:
    """单字节类（只返回类，不返回值）：digit=ASCII 0-9；alpha=ASCII 字母；其余=other。"""
    if 48 <= b <= 57:
        return CLASS_DIGIT
    if 65 <= b <= 90 or 97 <= b <= 122:
        return CLASS_ALPHA
    return CLASS_OTHER


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
# 硬等参照（环 11 result.json：case_analysis.<case>.events[*].positions_offset 全集
# 与 case_analysis.<case>.envelope_span）
# ---------------------------------------------------------------------------

def load_reference_shape(root: Path):
    ref_path = root / REFERENCE_RESULT_PATH_REL
    if not ref_path.is_file():
        _fail("硬等参照 result.json 不存在: %s" % REFERENCE_RESULT_PATH_REL)
    ref_sha = sha256_of(ref_path.read_bytes())
    try:
        obj = json.loads(ref_path.read_bytes().decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        _fail("硬等参照 result.json 解析失败: %s" % exc)
    ca = obj.get("case_analysis") if isinstance(obj, dict) else None
    if not isinstance(ca, dict):
        _fail("硬等参照缺 case_analysis")
    offsets_by_case = {}
    span_by_case = {}
    cases = sorted(set(ca) | set(GROUPS))
    for case in cases:
        entry = ca.get(case)
        if not isinstance(entry, dict):
            _fail("硬等参照 case_analysis 缺 case: %s" % case)
        events = entry.get("events")
        if not isinstance(events, list) or not events:
            _fail("硬等参照 %s 缺 events" % case)
        offs = set()
        for ev in events:
            pos = ev.get("positions_offset") if isinstance(ev, dict) else None
            if not isinstance(pos, list) or not all(isinstance(x, int) for x in pos):
                _fail("硬等参照 %s events.positions_offset 缺失或非整数列表" % case)
            offs.update(pos)
        span = entry.get("envelope_span")
        if (not isinstance(span, list) or len(span) != 1
                or not isinstance(span[0], list) or len(span[0]) != 2
                or not all(isinstance(x, int) for x in span[0])):
            _fail("硬等参照 %s envelope_span 缺失或非单 span" % case)
        offsets_by_case[case] = sorted(offs)
        span_by_case[case] = list(span[0])
    return offsets_by_case, span_by_case, ref_sha, cases


# ---------------------------------------------------------------------------
# 值无关 run 登记（冻结 §2）
# ---------------------------------------------------------------------------

def register_run(text: bytes, off: int) -> dict:
    """包含 off 的极大数字 run 登记（值无关）：run [起,止)、长、run 内 index、左邻类。
    off 处字节非 digit 时无包含 run：run_found=false，只登记该字节类。"""
    cls = byte_class(text[off])
    if cls != CLASS_DIGIT:
        return {"run_found": False, "drift_byte_class": cls}
    s = off
    while s > 0 and byte_class(text[s - 1]) == CLASS_DIGIT:
        s -= 1
    e = off + 1
    while e < len(text) and byte_class(text[e]) == CLASS_DIGIT:
        e += 1
    return {
        "run_found": True,
        "run_start": s,
        "run_end": e,
        "run_len": e - s,
        "drift_index_in_run": off - s,
        "left_neighbor_class": byte_class(text[s - 1]) if s > 0 else CLASS_BOF,
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
            ev for ev in events
            if ev.get("type") == "message" and ev.get("role") == "user"
        ]
        if len(user_events) != 1:
            _fail("role=user 消息数=%d（应为恰 1）: %s" % (len(user_events), slot))
        user_text = extract_user_text_bytes(user_events[0], slot)
        slot_results[slot] = {
            "trace_file": trace_path.name,
            "user_text_sha256": sha256_of(user_text),
            "user_text_bytes": len(user_text),
            "_text": user_text,
        }

    # --- 3. 逐 case：长度/信封 span/漂移 offsets 复算 + 硬等 ------------------
    ref_offsets, ref_spans, ref_sha, ref_cases = load_reference_shape(root)
    texts_by_case = {}
    offsets_by_case = {}
    hard_equal_cases = {}
    span_checks = {}
    for case in sorted(GROUPS):
        texts = {rep: slot_results["%s__%s" % (case, rep)]["_text"] for rep in REPS}
        texts_by_case[case] = texts
        lengths = {rep: len(texts[rep]) for rep in REPS}
        if len(set(lengths.values())) != 1:
            _fail("%s: rep 文本字节数不等 %s，超出冻结结构范围"
                  % (case, sorted(lengths.values())))
        spans_by_rep = {}
        for rep in REPS:
            sp, unc = find_envelope_spans(texts[rep])
            if unc:
                _fail("%s %s: 存在未闭合信封标记" % (case, rep))
            if len(sp) != 1:
                _fail("%s %s: 信封 span 数=%d（冻结结构应为恰 1）" % (case, rep, len(sp)))
            spans_by_rep[rep] = list(sp[0])
        if len({tuple(v) for v in spans_by_rep.values()}) != 1:
            _fail("%s: 信封 span 跨 rep 不一致" % case)
        span = spans_by_rep["r1"]
        ref_span = ref_spans[case]
        span_checks[case] = {
            "recomputed_by_rep": {rep: spans_by_rep[rep] for rep in REPS},
            "cross_rep_equal": True,
            "reference_span": [list(ref_span)],
            "matches_reference": list(span) == list(ref_span),
            "envelope_close": span[1],
        }
        if not span_checks[case]["matches_reference"]:
            _fail("%s: 信封 span 复算与环 11 result.json 登记不符（数据结构不可信）" % case)

        union = set()
        for ra, rb in PAIRS:
            union.update(diff_byte_offsets(texts[ra], texts[rb]))
        recomputed = sorted(union)
        reference = ref_offsets[case]
        offsets_by_case[case] = recomputed
        hard_equal_cases[case] = {
            "recomputed_sorted": recomputed,
            "reference_sorted": reference,
            "n_offsets": len(recomputed),
            "equal": recomputed == reference,
        }
    hard_all_equal = (
        sorted(hard_equal_cases) == sorted(ref_cases)
        and all(v["equal"] for v in hard_equal_cases.values())
    )
    if not hard_all_equal:
        detail = "; ".join(
            "%s equal=%s n=%d" % (c, str(hard_equal_cases[c]["equal"]).lower(),
                                  hard_equal_cases[c]["n_offsets"])
            for c in sorted(hard_equal_cases))
        _fail("漂移 offsets 硬等失败（与 %s 不一致，漂移即 exit2）: %s"
              % (REFERENCE_RESULT_PATH_REL, detail))

    # --- 4. lane / 簇-孤立分类（簇=信封外 rel_position 跨 case 对齐，沿用环 11）--
    cluster_rels_aligned = None
    ext_rels_by_case = {}
    for case in sorted(GROUPS):
        close = span_checks[case]["envelope_close"]
        span = span_checks[case]["recomputed_by_rep"]["r1"]
        ext_rels = sorted({off - close for off in offsets_by_case[case]
                           if not (span[0] <= off < span[1])})
        ext_rels_by_case[case] = ext_rels
    aligned = set(ext_rels_by_case[sorted(GROUPS)[0]])
    for case in sorted(GROUPS)[1:]:
        aligned &= set(ext_rels_by_case[case])
    cluster_rels_aligned = sorted(aligned)

    roles_by_case = {}
    for case in sorted(GROUPS):
        close = span_checks[case]["envelope_close"]
        span = span_checks[case]["recomputed_by_rep"]["r1"]
        roles = {}
        for off in offsets_by_case[case]:
            if span[0] <= off < span[1]:
                roles[off] = "internal"
            elif (off - close) in aligned:
                roles[off] = "cluster"
            else:
                roles[off] = "isolated_external"
        roles_by_case[case] = roles

    # --- 5. 逐 offset×rep run 登记（值无关）----------------------------------
    regs_by_case = {}
    entries_total = 0
    n_no_run = 0
    for case in sorted(GROUPS):
        texts = texts_by_case[case]
        entries = []
        for off in offsets_by_case[case]:
            by_rep = {}
            for rep in REPS:
                reg = register_run(texts[rep], off)
                by_rep[rep] = reg
                entries_total += 1
                if not reg["run_found"]:
                    n_no_run += 1
            entries.append({
                "offset": off,
                "rel_position": off - span_checks[case]["envelope_close"],
                "lane": ("envelope_internal"
                         if roles_by_case[case][off] == "internal"
                         else "envelope_external"),
                "cluster_role": roles_by_case[case][off],
                "by_rep": by_rep,
            })
        regs_by_case[case] = entries

    # --- 6. S2：全部漂移 run 边界三 rep 相等 ---------------------------------
    s2_cases = {}
    s2_all = True
    n_checked = 0
    for case in sorted(GROUPS):
        per_offset = []
        case_ok = True
        for entry in regs_by_case[case]:
            bounds = {}
            for rep in REPS:
                reg = entry["by_rep"][rep]
                bounds[rep] = ([reg["run_start"], reg["run_end"], reg["run_len"]]
                               if reg["run_found"] else None)
            n_checked += 1
            eq = all(reg["run_found"] for reg in entry["by_rep"].values()) and \
                len({tuple(b) for b in bounds.values()}) == 1
            case_ok = case_ok and eq
            per_offset.append({
                "offset": entry["offset"],
                "cluster_role": entry["cluster_role"],
                "boundaries_by_rep": bounds,
                "cross_rep_equal": eq,
            })
        s2_cases[case] = {"all_equal": case_ok, "per_offset": per_offset}
        s2_all = s2_all and case_ok

    # --- 7. S1：信封外簇恰两组 run、各长 2、隔恰 1 非数字字节、两 case 同构 ----
    def eval_s1_rep(text: bytes, cluster_offs: list) -> dict:
        runs = []
        no_run = []
        seen = set()
        for off in cluster_offs:
            reg = register_run(text, off)
            if not reg["run_found"]:
                no_run.append(off)
                continue
            key = (reg["run_start"], reg["run_end"])
            if key not in seen:
                seen.add(key)
                runs.append({"run": [reg["run_start"], reg["run_end"]],
                             "len": reg["run_len"]})
        runs.sort(key=lambda r: (r["run"][0], r["run"][1]))
        run_bytes = sorted(b for r in runs for b in range(r["run"][0], r["run"][1]))
        n_runs = len(runs)
        gap_width = (runs[1]["run"][0] - runs[0]["run"][1]) if n_runs == 2 else None
        gap_class = (byte_class(text[runs[0]["run"][1]]) if n_runs == 2 else None)
        checks = {
            "n_runs": n_runs,
            "run_lens": [r["len"] for r in runs],
            "gap_width_bytes": gap_width,
            "gap_byte_class": gap_class,
            "no_run_offsets": no_run,
            "cluster_offsets_covered_exact": (
                n_runs >= 1 and run_bytes == list(cluster_offs)),
            "shape_ok": (
                n_runs == 2
                and all(r["len"] == 2 for r in runs)
                and gap_width == 1
                and gap_class is not None and gap_class != CLASS_DIGIT
                and not no_run
                and run_bytes == list(cluster_offs)),
        }
        checks["shape_signature"] = "DD?DD" if checks["shape_ok"] else (
            "VARIABLE(n_runs=%d,lens=%s,gap=%s,no_run=%d)"
            % (n_runs, checks["run_lens"], gap_width, len(no_run)))
        return checks

    s1_cases = {}
    s1_all = True
    for case in sorted(GROUPS):
        cluster_offs = [e["offset"] for e in regs_by_case[case]
                        if e["cluster_role"] == "cluster"]
        per_rep = {rep: eval_s1_rep(texts_by_case[case][rep], cluster_offs)
                   for rep in REPS}
        reps_ok = all(per_rep[rep]["shape_ok"] for rep in REPS)
        sigs = {per_rep[rep]["shape_signature"] for rep in REPS}
        s1_cases[case] = {
            "pass": reps_ok and len(sigs) == 1,
            "shape_signature": sorted(sigs)[0] if len(sigs) == 1 else "VARIABLE",
            "cluster_offsets": cluster_offs,
            "per_rep": per_rep,
        }
        s1_all = s1_all and s1_cases[case]["pass"]
    struct_tuples = {}
    for case in sorted(GROUPS):
        rr = s1_cases[case]["per_rep"]["r1"]
        struct_tuples[case] = (rr["n_runs"], tuple(rr["run_lens"]),
                               rr["gap_width_bytes"], rr["gap_byte_class"],
                               rr["cluster_offsets_covered_exact"])
    isomorphic = (s1_all
                  and len(set(struct_tuples.values())) == 1
                  and all(s1_cases[c]["pass"] for c in s1_cases))

    # --- 8. S3：信封内孤立位 run 长=1 且左邻=alpha ---------------------------
    s3_cases = {}
    s3_all = True
    for case in sorted(GROUPS):
        close = span_checks[case]["envelope_close"]
        details = []
        case_ok = True
        for entry in regs_by_case[case]:
            if entry["cluster_role"] != "internal":
                continue
            per_rep_pass = []
            for rep in REPS:
                reg = entry["by_rep"][rep]
                per_rep_pass.append(bool(
                    reg["run_found"] and reg["run_len"] == 1
                    and reg["left_neighbor_class"] == CLASS_ALPHA))
            ok = all(per_rep_pass)
            case_ok = case_ok and ok
            details.append({
                "offset": entry["offset"],
                "rel_position": entry["rel_position"],
                "run_len_by_rep": {rep: (entry["by_rep"][rep]["run_len"]
                                         if entry["by_rep"][rep]["run_found"] else None)
                                   for rep in REPS},
                "left_neighbor_class_by_rep": {
                    rep: (entry["by_rep"][rep].get("left_neighbor_class")
                          if entry["by_rep"][rep]["run_found"]
                          else entry["by_rep"][rep].get("drift_byte_class"))
                    for rep in REPS},
                "per_rep_pass": per_rep_pass,
                "pass": ok,
            })
        s3_cases[case] = {"pass": case_ok, "n_internal": len(details),
                          "details": details}
        s3_all = s3_all and case_ok

    # --- 9. 分支（冻结 §3 字面）----------------------------------------------
    if s1_all and s2_all and s3_all:
        verdict = "B-DIGIT-RUN-FIXED-SHAPE"
        reason = ("S1∧S2∧S3 全过：信封外漂移簇为定长 DD?DD 形状（两组长 2 数字 run、"
                  "隔恰 1 非数字字节、gap 字节类=other），两 case 同构；全部漂移 run "
                  "边界三 rep 相等；信封内孤立位为字母邻接单个数字。排除跨 rep 长度可变 "
                  "id 类候选；与秒/分时钟类相容性仅在字节类层面登记（? 为 other 类），"
                  "语义不判定。")
    else:
        verdict = "B-SHAPE-VARIABLE"
        broken = []
        if not s1_all:
            broken.append("S1")
        if not s2_all:
            broken.append("S2")
        if not s3_all:
            broken.append("S3")
        reason = "形状断言破（%s）⇒ 形状可变；差异明细见 assertions 与 run_registration" % (
            "∧".join(broken),)

    branch = {
        "verdict": verdict,
        "reason": reason,
        "S1_pass": s1_all,
        "S2_pass": s2_all,
        "S3_pass": s3_all,
        "clock_compat_note": (
            "DD?DD 的 ? 字节类=other：冒号类分隔与该形状在字节类层面相容；"
            "token 语义（时钟/序号/编码片段等）不判定"),
    }

    # --- 10. 孤立位（跨 lane）形状披露 + 勘察注记对账 -------------------------
    isolated_disclosure = {}
    for case in sorted(GROUPS):
        rows = []
        for entry in regs_by_case[case]:
            if entry["cluster_role"] != "cluster":
                reg = entry["by_rep"]["r1"]
                rows.append({
                    "offset": entry["offset"],
                    "rel_position": entry["rel_position"],
                    "cluster_role": entry["cluster_role"],
                    "run_len_by_rep": {rep: (entry["by_rep"][rep]["run_len"]
                                             if entry["by_rep"][rep]["run_found"] else None)
                                       for rep in REPS},
                    "left_neighbor_class_by_rep": {
                        rep: (entry["by_rep"][rep].get("left_neighbor_class")
                              if entry["by_rep"][rep]["run_found"]
                              else entry["by_rep"][rep].get("drift_byte_class"))
                        for rep in REPS},
                    "run_boundaries_cross_rep_equal": next(
                        p["cross_rep_equal"] for p in s2_cases[case]["per_offset"]
                        if p["offset"] == entry["offset"]),
                })
        isolated_disclosure[case] = rows

    cluster_counts = {
        case: {
            "cluster": sum(1 for e in regs_by_case[case] if e["cluster_role"] == "cluster"),
            "internal": sum(1 for e in regs_by_case[case] if e["cluster_role"] == "internal"),
            "isolated_external": sum(1 for e in regs_by_case[case]
                                     if e["cluster_role"] == "isolated_external"),
        } for case in sorted(GROUPS)
    }

    result = {
        "schema": SCHEMA,
        "package": PACKAGE_NAME,
        "value_independence_statement": VALUE_INDEPENDENCE_STATEMENT,
        "prereg": {
            "path_rel": PREREG_PATH_REL,
            "sha256": PREREG_SHA256,
            "sha256_match": True,
        },
        "baseline_commit": git_head(root),
        "reference_source": {
            "path_rel": REFERENCE_RESULT_PATH_REL,
            "sha256": ref_sha,
        },
        "archive_layout": {
            "runs_rel": "runs/<slot>/trace/<session>.jsonl",
            "slots_expected": SLOT_ORDER,
        },
        "extraction": {
            "rule": "与环 6/11 同一 W1 提取：runs/<slot>/trace/*.jsonl（恰 1）、"
                    "type=message 且 role=user（恰 1）、content 恰 1 block 且 type=input_text、"
                    "text 的 UTF-8 字节",
            "per_slot": {k: {kk: vv for kk, vv in slot_results[k].items()
                             if kk != "_text"}
                         for k in SLOT_ORDER},
        },
        "offsets_hard_equal": {
            "reference_path_rel": REFERENCE_RESULT_PATH_REL,
            "rule": "复算=逐 case 三对逐字节差异并集；硬等=环 11 result.json "
                    "case_analysis.<case>.events[*].positions_offset 全集；不等即 exit2",
            "all_equal": hard_all_equal,
            "cases": hard_equal_cases,
        },
        "envelope_span_check": {
            "rule": "每 rep 恰 1 span、跨 rep 相等、且与环 11 result.json 登记的 "
                    "envelope_span 一致（lane/rel 派生基准；不符视为数据结构不可信 exit2）",
            "cases": span_checks,
        },
        "cluster_classification": {
            "rule": "簇=信封外漂移位中 rel_position（offset−信封闭合）跨 case 对齐（交集）者"
                    "（沿用环 11 cross-case 对齐规则，无阈值）；信封外其余=isolated_external；"
                    "信封内=internal",
            "aligned_rels": cluster_rels_aligned,
            "roles_count_by_case": cluster_counts,
        },
        "run_registration": {
            "rule": "逐 offset×rep：包含该漂移字节的极大数字 run（byte_class==digit 的极大"
                    "连续段）之 [起,止)、长、漂移字节在 run 内 index、run 左邻字节类"
                    "（digit/alpha/other；bof=文本首）；漂移字节非 digit 时 run_found=false "
                    "只登记该字节类；分隔字节只登记类不登记值",
            "class_vocab": CLASS_VOCAB,
            "offsets_total": sum(len(v) for v in offsets_by_case.values()),
            "entries_total": entries_total,
            "run_found_false_n": n_no_run,
            "cases": regs_by_case,
        },
        "assertions": {
            "S1": {
                "rule": "信封外簇恰为两组 run、各长 2、run 字节与簇 offsets 恰合、"
                        "中间隔恰 1 个非数字字节（DD?DD）、两 case 同构（逐 rep 断言）",
                "pass": s1_all,
                "cross_case_isomorphic": isomorphic,
                "cases": s1_cases,
            },
            "S2": {
                "rule": "全部漂移 run 的边界三 rep 相等（起点/止点/长度）",
                "pass": s2_all,
                "n_offsets_checked": n_checked,
                "cases": s2_cases,
            },
            "S3": {
                "rule": "信封内孤立位 run 长=1 且左邻=alpha（逐 rep）",
                "pass": s3_all,
                "cases": s3_cases,
            },
        },
        "isolated_positions_disclosure": {
            "rule": "信封内/外孤立位（非簇）逐位形状登记（冻结 S3 只断言信封内；"
                    "信封外孤立位形状如实披露供复核）",
            "cases": isolated_disclosure,
        },
        "branch": branch,
        "survey_note_reconciliation": {
            "rule": "预注册勘察注记为冻结前事实，可被复算推翻（README 冻结行）；以下以复算为准",
            "items": [
                "勘察注记称『信封内 3 孤立位（dab 181/5558/6660、tb 175/5540/6604）』；"
                "复算信封 span（dab [0,6330)、tb [0,6286)，与环 11 result.json 登记一致）"
                "下 6660/6604 为信封外（rel +330/+318，与环 11 positions 登记的 "
                "rel_position 一致）；信封内孤立位实为每 case 2 处（dab 181/5558、"
                "tb 175/5540）。按冻结行以复算 lane 为准；S3 按复算信封内集合断言"
                "（2×2 处全过）；孤立位形状（run 长 1、左邻 alpha）在全部 3+3 处成立，"
                "形状结论不受 lane 标注差异影响",
                "簇形状复现：dab [6423,6425)+[6426,6428)、tb [6379,6381)+[6382,6384)，"
                "各两组长 2 数字 run、隔恰 1 非数字字节（类=other），与勘察注记一致",
                "三 rep run 边界逐字节一致复现（全部漂移 offset 的 run 起/止/长三 rep 相等）",
            ],
        },
        "analysis_rules": {
            "byte_class_definition": "digit=ASCII 0-9；alpha=ASCII A-Z/a-z；"
                                     "other=其余全部字节（含 UTF-8 多字节序列、标点等）；"
                                     "bof=run 起点为文本首（无左邻，结构性取值）",
            "run_definition": "极大数字 run=文本中 byte_class==digit 的极大连续段 [起,止)；"
                              "逐 offset×rep 独立计算",
            "envelope_definition": "信封=W1 冻结开/闭标记的精确 span（标记字面以环 11 包 "
                                   "analysis_rules 同名定义为准，此处不重复登记标记文本）",
            "rel_position_definition": "rel_position = offset − 信封闭合（envelope span 终点）",
            "cluster_caliper_disclosure": "『信封外簇』按勘察注记自身用法与环 11 簇定义取"
                                          "跨 case rel 对齐口径（DD?DD 群）；信封外孤立位"
                                          "（每 case 1 处）不属于簇、无 S 断言绑定但逐位登记。"
                                          "敏感性：若采『信封外簇=全部信封外漂移位』替代口径，"
                                          "信封外孤立位（run 长 1）将令 S1 破而翻为 "
                                          "B-SHAPE-VARIABLE；该口径差异如实披露，"
                                          "最终口径裁定权在预注册文本",
            "value_independence_boundary": "分隔字节与漂移字节值一律不读不登记；跨 rep 只比较 "
                                           "run 边界（起/止/长），不比较任何字节值是否相同",
            "fail_closed_scope": "硬等失败、档案布局异常、trace/消息结构异常、rep 文本长度"
                                 "不等、信封 span 数≠1 或跨 rep 不等或与环 11 登记不符 "
                                 "⇒ exit2 / B-INDETERMINATE（fail-closed）",
        },
        "exit_code": 0,
    }
    return result


def summarize(result: dict) -> str:
    """确定性 stdout 摘要（无字节值/token 文本/私有绝对路径）。"""
    lines = []
    lines.append("PASS %s schema=%s" % (result["package"], result["schema"]))
    lines.append("prereg_sha256_ok=true sha=%s" % result["prereg"]["sha256"])
    lines.append("baseline_commit=%s" % result["baseline_commit"])
    lines.append("archive_slots=%d user_texts_extracted=%d"
                 % (len(result["archive_layout"]["slots_expected"]),
                    len(result["extraction"]["per_slot"])))
    he = result["offsets_hard_equal"]
    per_case = " ".join("%s:%d" % (c, he["cases"][c]["n_offsets"])
                        for c in sorted(he["cases"]))
    lines.append("offsets_hard_equal=%s reference=%s offsets(%s)"
                 % (str(he["all_equal"]).lower(), he["reference_path_rel"], per_case))
    sc = result["envelope_span_check"]["cases"]
    lines.append("envelope_span: cross_rep_equal=%s matches_reference=%s close(%s)"
                 % (str(all(v["cross_rep_equal"] for v in sc.values())).lower(),
                    str(all(v["matches_reference"] for v in sc.values())).lower(),
                    " ".join("%s:%d" % (c, sc[c]["envelope_close"])
                             for c in sorted(sc))))
    rr = result["run_registration"]
    lines.append("run_registration: offsets=%d entries=%d run_found_false=%d"
                 % (rr["offsets_total"], rr["entries_total"], rr["run_found_false_n"]))
    cc = result["cluster_classification"]
    roles = " ; ".join(
        "%s cluster=%d internal=%d isolated_external=%d"
        % (c, cc["roles_count_by_case"][c]["cluster"],
           cc["roles_count_by_case"][c]["internal"],
           cc["roles_count_by_case"][c]["isolated_external"])
        for c in sorted(cc["roles_count_by_case"]))
    lines.append("cluster_aligned_rel=%s roles: %s"
                 % (cc["aligned_rels"], roles))
    a = result["assertions"]
    s1_first = a["S1"]["cases"][sorted(a["S1"]["cases"])[0]]["per_rep"]["r1"]
    lines.append("S1=%s shape=%s n_runs=%d lens=%s gap=%sB(gap_class=%s) coverage=exact "
                 "isomorphic=%s"
                 % (str(a["S1"]["pass"]).lower(), s1_first["shape_signature"],
                    s1_first["n_runs"], s1_first["run_lens"],
                    s1_first["gap_width_bytes"], s1_first["gap_byte_class"],
                    str(a["S1"]["cross_case_isomorphic"]).lower()))
    lines.append("S2=%s offsets_checked=%d cross_rep_equal_all=%s"
                 % (str(a["S2"]["pass"]).lower(), a["S2"]["n_offsets_checked"],
                    str(all(v["all_equal"] for v in a["S2"]["cases"].values())).lower()))
    s3 = a["S3"]
    s3_detail = " ".join("%s:%d" % (c, s3["cases"][c]["n_internal"])
                         for c in sorted(s3["cases"]))
    lines.append("S3=%s internal(%s) all_len1_left_alpha=%s"
                 % (str(s3["pass"]).lower(), s3_detail,
                    str(s3["pass"]).lower()))
    iso = []
    for case in sorted(result["isolated_positions_disclosure"]["cases"]):
        for row in result["isolated_positions_disclosure"]["cases"][case]:
            iso.append("%s rel=%+d role=%s run_len=%s left=%s"
                       % (case, row["rel_position"], row["cluster_role"],
                          row["run_len_by_rep"]["r1"],
                          row["left_neighbor_class_by_rep"]["r1"]))
    lines.append("isolated_shapes(non-cluster): %s"
                 % (" ; ".join(iso) if iso else "none"))
    b = result["branch"]
    lines.append("branch=%s s1=%s s2=%s s3=%s"
                 % (b["verdict"], str(b["S1_pass"]).lower(),
                    str(b["S2_pass"]).lower(), str(b["S3_pass"]).lower()))
    lines.append("survey_reconciliation_items=%d"
                 % len(result["survey_note_reconciliation"]["items"]))
    lines.append("exit=0")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="WB 漂移 token 字节形状 复算（预注册 v1，schema %s）" % SCHEMA)
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
        sys.stdout.write("FAIL(unexpected): %r\nexit=2\n" % (exc,))
        return 2


if __name__ == "__main__":
    sys.exit(main())
