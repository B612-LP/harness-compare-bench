#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WB 复测漂移 token 的值语义检验（HH:MM 时钟类证实/否证裁定）— 预注册 v1 复算工具。

用法：
  python3 verify.py --root <repo> --archive-root <bw-retest/workbuddy 根> [--output result.json]

- --root：公开仓库根（含本包冻结 README 预注册与两份硬等参照：
  4-打分细则/WB漂移字节位置结构-2026-11-16/result.json（漂移 offsets 全集）、
  4-打分细则/WB漂移token形状-2026-11-16/result.json（run 边界登记））。
- --archive-root：WorkBuddy 复测档根（其下 runs/<6 槽>/trace/*.jsonl 与
  runs/<槽>/collect-meta.json）。
- stdout：确定性人类摘要（不含私有绝对路径）；exit 0=裁定成立，2=fail-closed。
- --output：独占创建完整 result.json（schema wb-token-sem-v1）；目标已存在则拒改 exit 2。

值发布边界（冻结 §2）：本工具读 W1 提取文本与同 run 轨迹消息时间戳字段；发布仅限——
漂移 token 的 5 字节值（4 数字+1 分隔）、分隔字节值、孤立位单数字字节值、消息时间戳的
HH:MM（分钟精度墙钟，秒/毫秒与日期不发布）、字段名与换算规则；字母序列/多字节序列/
信封或任务正文任何切片零发布；结果不含私有档案绝对路径。实现独立成文，不 import
其他包代码（W1 提取方式与环 6/11/15 包公开做法同构：runs/<slot>/trace/*.jsonl、
role=user、content[0].type=input_text）。
"""
import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

PACKAGE_NAME = "WB漂移token值语义-2026-11-16"
SCHEMA = "wb-token-sem-v1"

PREREG_PATH_REL = "4-打分细则/WB漂移token值语义-2026-11-16/README.md"
PREREG_SHA256 = "b2e891a79eba14558b116627110dc4bd1f90db20e52700b0fb1b93f3b78643b6"
REF11_RESULT_PATH_REL = "4-打分细则/WB漂移字节位置结构-2026-11-16/result.json"
REF15_RESULT_PATH_REL = "4-打分细则/WB漂移token形状-2026-11-16/result.json"

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
CLASS_BOF = "bof"

# 冻结 §2 断言
V1_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
V2_MAX_ABS_DELTA_MIN = 1          # 主断言：|token HH:MM − 首消息 HH:MM| ≤ 1 分钟
V2_DIRECTION_WINDOW = (-1, 5)     # 相关方向：token ∈ [首消息 −1min, +5min] 视为构建时刻一致

EXPECTED_INTERNAL_ISOLATED_PER_CASE = 2      # V3：信封内 2
EXPECTED_ISOLATED_EXTERNAL_PER_CASE = 1      # V3：信封外 1
EXPECTED_TOKEN_BYTES = 5                     # 4 漂移数字 + 1 分隔字节

VALUE_PUBLICATION_BOUNDARY = (
    "值发布边界声明：本包读取 W1 提取文本与同 run 轨迹消息时间戳字段；发布仅限——"
    "漂移 token 的 5 字节值（4 数字+1 分隔）、分隔字节值、孤立位单数字字节值、"
    "消息时间戳的 HH:MM（分钟精度墙钟，秒/毫秒与日期不发布）、字段名与换算规则；"
    "字母序列/多字节序列/信封或任务正文任何切片零发布；结果不含私有档案绝对路径。"
)


class VerifyError(Exception):
    """fail-closed：任何结构/硬等异常都转成 exit 2。"""


def _fail(msg: str) -> None:
    raise VerifyError(msg)


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def byte_class(b: int) -> str:
    """单字节类：digit=ASCII 0-9；alpha=ASCII 字母；其余=other。"""
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
# 硬等参照一（环 11 result.json：漂移 offsets 全集 + 信封 span）
# ---------------------------------------------------------------------------

def load_reference_offsets(root: Path):
    ref_path = root / REF11_RESULT_PATH_REL
    if not ref_path.is_file():
        _fail("硬等参照（环 11 offsets）result.json 不存在: %s" % REF11_RESULT_PATH_REL)
    ref_sha = sha256_of(ref_path.read_bytes())
    try:
        obj = json.loads(ref_path.read_bytes().decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        _fail("硬等参照（环 11 offsets）result.json 解析失败: %s" % exc)
    ca = obj.get("case_analysis") if isinstance(obj, dict) else None
    if not isinstance(ca, dict):
        _fail("硬等参照（环 11 offsets）缺 case_analysis")
    offsets_by_case = {}
    span_by_case = {}
    cases = sorted(set(ca) | set(GROUPS))
    for case in cases:
        entry = ca.get(case)
        if not isinstance(entry, dict):
            _fail("硬等参照（环 11 offsets）case_analysis 缺 case: %s" % case)
        events = entry.get("events")
        if not isinstance(events, list) or not events:
            _fail("硬等参照（环 11 offsets）%s 缺 events" % case)
        offs = set()
        for ev in events:
            pos = ev.get("positions_offset") if isinstance(ev, dict) else None
            if not isinstance(pos, list) or not all(isinstance(x, int) for x in pos):
                _fail("硬等参照（环 11 offsets）%s events.positions_offset 缺失或非整数列表" % case)
            offs.update(pos)
        span = entry.get("envelope_span")
        if (not isinstance(span, list) or len(span) != 1
                or not isinstance(span[0], list) or len(span[0]) != 2
                or not all(isinstance(x, int) for x in span[0])):
            _fail("硬等参照（环 11 offsets）%s envelope_span 缺失或非单 span" % case)
        offsets_by_case[case] = sorted(offs)
        span_by_case[case] = list(span[0])
    return offsets_by_case, span_by_case, ref_sha, cases


# ---------------------------------------------------------------------------
# 硬等参照二（环 15 result.json：逐 offset×rep run 边界登记 + 簇角色）
# ---------------------------------------------------------------------------

RUN_FIELDS = ("run_found", "run_start", "run_end", "run_len",
              "drift_index_in_run", "left_neighbor_class")
# 规范键集：参照与复算两侧都投影到同一键集再比较（run_found=false 条目仅带
# drift_byte_class 键形；缺失键投影为 None）。
RUN_FIELDS_CANON = RUN_FIELDS + ("drift_byte_class",)


def load_reference_runs(root: Path):
    ref_path = root / REF15_RESULT_PATH_REL
    if not ref_path.is_file():
        _fail("硬等参照（环 15 run 边界）result.json 不存在: %s" % REF15_RESULT_PATH_REL)
    ref_sha = sha256_of(ref_path.read_bytes())
    try:
        obj = json.loads(ref_path.read_bytes().decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        _fail("硬等参照（环 15 run 边界）result.json 解析失败: %s" % exc)
    rr = obj.get("run_registration") if isinstance(obj, dict) else None
    if not isinstance(rr, dict) or not isinstance(rr.get("cases"), dict):
        _fail("硬等参照（环 15 run 边界）缺 run_registration.cases")
    entries_by_case = {}
    for case in sorted(set(rr["cases"]) | set(GROUPS)):
        entries = rr["cases"].get(case)
        if not isinstance(entries, list) or not entries:
            _fail("硬等参照（环 15 run 边界）缺 case: %s" % case)
        norm = []
        for ent in entries:
            if not isinstance(ent, dict) or not isinstance(ent.get("offset"), int) \
                    or not isinstance(ent.get("cluster_role"), str):
                _fail("硬等参照（环 15 run 边界）%s 条目结构异常" % case)
            by_rep = ent.get("by_rep")
            if not isinstance(by_rep, dict):
                _fail("硬等参照（环 15 run 边界）%s offset=%d 缺 by_rep" % (case, ent["offset"]))
            reps_norm = {}
            for rep in REPS:
                reg = by_rep.get(rep)
                if not isinstance(reg, dict):
                    _fail("硬等参照（环 15 run 边界）%s offset=%d 缺 rep %s"
                          % (case, ent["offset"], rep))
                reps_norm[rep] = {k: reg.get(k) for k in RUN_FIELDS_CANON}
            norm.append({
                "offset": ent["offset"],
                "cluster_role": ent["cluster_role"],
                "by_rep": reps_norm,
            })
        entries_by_case[case] = norm
    return entries_by_case, ref_sha


def register_run(text: bytes, off: int) -> dict:
    """包含 off 的极大数字 run（值面工具，此处返回值供 token/V3 使用）：
    run [起,止)、长、run 内 index、左邻类。off 处非 digit 时 run_found=false。"""
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
# 时间戳（元数据面）：epoch 毫秒 → 固定偏移墙钟 HH:MM
# ---------------------------------------------------------------------------

def offset_string(td: datetime.timedelta) -> str:
    total = int(td.total_seconds())
    sign = "+" if total >= 0 else "-"
    total = abs(total)
    return "%s%02d:%02d" % (sign, total // 3600, (total % 3600) // 60)


def read_collect_meta_offset(runs_dir: Path, slot: str) -> datetime.timedelta:
    """时区偏移从档案自身 trace/collect-meta.json 的 collected_at（ISO-8601 含偏移）派生。"""
    p = runs_dir / slot / "trace" / "collect-meta.json"
    if not p.is_file():
        _fail("槽 trace/collect-meta.json 缺失（时区偏移派生源）: %s" % slot)
    try:
        obj = json.loads(p.read_bytes().decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        _fail("槽 collect-meta.json 解析失败: %s: %s" % (slot, exc))
    if not isinstance(obj, dict) or not isinstance(obj.get("collected_at"), str):
        _fail("槽 collect-meta.json 缺 collected_at 字符串: %s" % slot)
    try:
        dt = datetime.datetime.fromisoformat(obj["collected_at"])
    except ValueError as exc:
        _fail("槽 collected_at 非 ISO-8601: %s: %s" % (slot, exc))
    off = dt.utcoffset()
    if off is None:
        _fail("槽 collected_at 不含 UTC 偏移: %s" % slot)
    return off


def epoch_ms_to_hhmm(ms: int, tz: datetime.timezone) -> str:
    if not isinstance(ms, int) or isinstance(ms, bool):
        _fail("时间戳非 epoch 毫秒整数（实际 schema 以复算为准）")
    return datetime.datetime.fromtimestamp(ms // 1000, tz=tz).strftime("%H:%M")


def register_messages(events, slot: str, tz: datetime.timezone) -> dict:
    """同 run 轨迹消息时间戳登记：首个与末个消息的 HH:MM（仅分钟精度发布）。"""
    msgs = [ev for ev in events if ev.get("type") == "message"]
    if not msgs:
        _fail("轨迹无 type=message 事件: %s" % slot)
    tss = []
    for ev in msgs:
        ts = ev.get("timestamp")
        if not isinstance(ts, int) or isinstance(ts, bool):
            _fail("消息缺 timestamp 整数字段（登记字段名 timestamp）: %s" % slot)
        tss.append(ts)
    for i in range(len(tss) - 1):
        if tss[i] > tss[i + 1]:
            _fail("消息时间戳非单调不减: %s" % slot)
    first_role = msgs[0].get("role")
    if first_role != "user":
        _fail("首消息 role 非 user（W1 构建消息应为首消息）: %s" % slot)
    return {
        "n_messages": len(msgs),
        "first_message_role": first_role,
        "monotonic_non_decreasing": True,
        "first_ts_hhmm": epoch_ms_to_hhmm(tss[0], tz),
        "last_ts_hhmm": epoch_ms_to_hhmm(tss[-1], tz),
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

    # --- 2. 逐槽 W1 提取 + 时间戳登记 ----------------------------------------
    slot_results = {}
    offsets_all = []
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
        offsets_all.append(read_collect_meta_offset(runs_dir, slot))
    if len(set(offsets_all)) != 1:
        _fail("各槽 collect-meta.json collected_at 偏移不一致（时区派生 fail-closed）: %s"
              % sorted({offset_string(o) for o in offsets_all}))
    tz = datetime.timezone(offsets_all[0])
    tz_offset_str = offset_string(offsets_all[0])

    ts_by_slot = {}
    for slot in SLOT_ORDER:
        _, events = read_trace(runs_dir / slot / "trace" / slot_results[slot]["trace_file"])
        ts_by_slot[slot] = register_messages(events, slot, tz)

    # --- 3. 逐 case：长度/信封 span/漂移 offsets 复算 + 硬等（环 11）----------
    ref_offsets, ref_spans, ref11_sha, ref11_cases = load_reference_offsets(root)
    ref_runs, ref15_sha = load_reference_runs(root)
    texts_by_case = {}
    offsets_by_case = {}
    offsets_hard = {}
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
        offsets_hard[case] = {
            "recomputed_sorted": recomputed,
            "reference_sorted": reference,
            "n_offsets": len(recomputed),
            "equal": recomputed == reference,
        }
    offsets_all_equal = (
        sorted(offsets_hard) == sorted(ref11_cases)
        and all(v["equal"] for v in offsets_hard.values())
    )
    if not offsets_all_equal:
        detail = "; ".join(
            "%s equal=%s n=%d" % (c, str(offsets_hard[c]["equal"]).lower(),
                                  offsets_hard[c]["n_offsets"])
            for c in sorted(offsets_hard))
        _fail("漂移 offsets 硬等失败（与 %s 不一致，漂移即 exit2）: %s"
              % (REF11_RESULT_PATH_REL, detail))

    # --- 4. run 边界硬等（环 15，逐 offset×rep 全字段）------------------------
    runs_hard = {}
    runs_all_equal = True
    for case in sorted(GROUPS):
        entries = ref_runs[case]
        ref_entry_offs = sorted(e["offset"] for e in entries)
        if ref_entry_offs != offsets_by_case[case]:
            _fail("%s: 环 15 参照条目 offset 集与复算漂移 offsets 不一致" % case)
        per_entry = []
        case_ok = True
        for ent in entries:
            off = ent["offset"]
            per_rep = {}
            ref_per_rep = {}
            for rep in REPS:
                reg = register_run(texts_by_case[case][rep], off)
                per_rep[rep] = dict(reg)
                ref_per_rep[rep] = ent["by_rep"][rep]
            eq = True
            for rep in REPS:
                a = {k: per_rep[rep].get(k) for k in RUN_FIELDS_CANON}
                b = {k: ref_per_rep[rep].get(k) for k in RUN_FIELDS_CANON}
                if a != b:
                    eq = False
            case_ok = case_ok and eq
            per_entry.append({
                "offset": off,
                "cluster_role": ent["cluster_role"],
                "recomputed_by_rep": per_rep,
                "reference_by_rep": ref_per_rep,
                "equal": eq,
            })
        runs_hard[case] = {"all_equal": case_ok, "n_entries": len(entries),
                           "per_entry": per_entry}
        runs_all_equal = runs_all_equal and case_ok
    if sorted(ref_runs) != sorted(GROUPS):
        _fail("环 15 参照 case 集与预期不一致")
    if not runs_all_equal:
        detail = "; ".join(
            "%s equal=%s entries=%d" % (c, str(runs_hard[c]["all_equal"]).lower(),
                                        runs_hard[c]["n_entries"])
            for c in sorted(runs_hard))
        _fail("run 边界硬等失败（与 %s 不一致，DD?DD 结构漂移即 exit2）: %s"
              % (REF15_RESULT_PATH_REL, detail))

    # --- 5. token 提取（值面）：簇两组 run → 5 字节 token --------------------
    tokens_by_case = {}
    for case in sorted(GROUPS):
        close = span_checks[case]["envelope_close"]
        cluster_entries = [e for e in ref_runs[case] if e["cluster_role"] == "cluster"]
        internal_entries = [e for e in ref_runs[case] if e["cluster_role"] == "internal"]
        iso_ext_entries = [e for e in ref_runs[case]
                           if e["cluster_role"] == "isolated_external"]
        if len(internal_entries) != EXPECTED_INTERNAL_ISOLATED_PER_CASE:
            _fail("%s: 信封内孤立位数=%d（冻结应为 %d）"
                  % (case, len(internal_entries), EXPECTED_INTERNAL_ISOLATED_PER_CASE))
        if len(iso_ext_entries) != EXPECTED_ISOLATED_EXTERNAL_PER_CASE:
            _fail("%s: 信封外孤立位数=%d（冻结应为 %d）"
                  % (case, len(iso_ext_entries), EXPECTED_ISOLATED_EXTERNAL_PER_CASE))
        # 簇 → 两组 run（逐 rep 从参照边界取，已过硬等）
        run_bounds = set()
        for ent in cluster_entries:
            for rep in REPS:
                reg = ent["by_rep"][rep]
                if not reg.get("run_found"):
                    _fail("%s offset=%d %s run_found=false（簇结构破坏）" % (case, ent["offset"], rep))
                run_bounds.add((rep, reg["run_start"], reg["run_end"]))
        by_rep_bounds = {}
        for rep in REPS:
            bounds = sorted({(s, e) for (r, s, e) in run_bounds if r == rep})
            if len(bounds) != 2:
                _fail("%s %s: 簇 run 组数=%d（冻结 DD?DD 应为 2）" % (case, rep, len(bounds)))
            (s1, e1), (s2, e2) = bounds
            if not (e1 < s2):
                _fail("%s %s: 两 run 交叠/逆序" % (case, rep))
            if s2 - e1 != 1:
                _fail("%s %s: 两 run 间隔=%d（应为恰 1 分隔字节）" % (case, rep, s2 - e1))
            by_rep_bounds[rep] = {"run1": [s1, e1], "run2": [s2, e2]}
        case_tokens = {}
        for rep in REPS:
            b = by_rep_bounds[rep]
            text = texts_by_case[case][rep]
            raw = text[b["run1"][0]:b["run2"][1]]
            if len(raw) != EXPECTED_TOKEN_BYTES:
                _fail("%s %s: token 字节数=%d（应为 5）" % (case, rep, len(raw)))
            try:
                token = raw.decode("ascii")
            except UnicodeDecodeError:
                _fail("%s %s: token 含非 ASCII 字节，超出值发布边界（冻结结构应为 4 数字+1 分隔）"
                      % (case, rep))
            sep_off = b["run1"][1]
            sep_char = chr(text[sep_off])
            if not (32 <= text[sep_off] <= 126):
                _fail("%s %s: 分隔字节非可打印 ASCII，超出值发布边界" % (case, rep))
            case_tokens[rep] = {
                "slot": "%s__%s" % (case, rep),
                "token": token,
                "token_len": len(raw),
                "byte_classes": [byte_class(x) for x in raw],
                "run1": list(b["run1"]),
                "run2": list(b["run2"]),
                "separator": {
                    "offset": sep_off,
                    "rel_position": sep_off - close,
                    "value": sep_char,
                },
            }
        tokens_by_case[case] = {
            "cluster_rels": sorted({e["offset"] - close for e in cluster_entries}),
            "by_rep": case_tokens,
        }

    # --- 6. V1：HH:MM 文法 + 分隔字节值 6/6 同一 ------------------------------
    v1_per_token = []
    for case in sorted(GROUPS):
        for rep in REPS:
            t = tokens_by_case[case]["by_rep"][rep]
            v1_per_token.append({
                "case": case, "rep": rep, "token": t["token"],
                "regex_match": bool(V1_PATTERN.match(t["token"])),
            })
    n_regex = sum(1 for x in v1_per_token if x["regex_match"])
    sep_values = [tokens_by_case[c]["by_rep"][r]["separator"]["value"]
                  for c in sorted(GROUPS) for r in REPS]
    sep_same = len(set(sep_values)) == 1
    v1_pass = (n_regex == 6) and sep_same
    v1 = {
        "rule": "V1 = 全部 6 token 匹配 ^([01]\\d|2[0-3]):[0-5]\\d$ 且分隔字节值 6/6 同一",
        "per_token": v1_per_token,
        "regex_match_count": "%d/6" % n_regex,
        "separator_value": sep_values[0] if sep_same else sorted(set(sep_values)),
        "separator_same_count": "%d/6" % sum(1 for v in sep_values if v == sep_values[0]),
        "separator_all_same": sep_same,
        "pass": v1_pass,
    }

    # --- 7. V2：token HH:MM vs 同 run 首消息 HH:MM ----------------------------
    v2_matrix = {}
    n_evaluable = 0
    n_main_pass = 0
    n_dir_pass = 0
    for case in sorted(GROUPS):
        rows = {}
        for rep in REPS:
            t = tokens_by_case[case]["by_rep"][rep]
            slot_ts = ts_by_slot[t["slot"]]
            first_hhmm = slot_ts["first_ts_hhmm"]
            row = {
                "token": t["token"],
                "first_ts_hhmm": first_hhmm,
                "last_ts_hhmm": slot_ts["last_ts_hhmm"],
            }
            if V1_PATTERN.match(t["token"]):
                token_min = int(t["token"][:2]) * 60 + int(t["token"][3:])
                fh, fm = first_hhmm.split(":")
                first_min = int(fh) * 60 + int(fm)
                delta = token_min - first_min
                circ = min(abs(delta), 1440 - abs(delta))
                row.update({
                    "v2_evaluable": True,
                    "delta_minutes_signed": delta,
                    "delta_minutes_abs": abs(delta),
                    "delta_minutes_circular": circ,
                    "main_pass_abs_le_1min": abs(delta) <= V2_MAX_ABS_DELTA_MIN,
                    "direction_window_pass":
                        V2_DIRECTION_WINDOW[0] <= delta <= V2_DIRECTION_WINDOW[1],
                })
                n_evaluable += 1
                if row["main_pass_abs_le_1min"]:
                    n_main_pass += 1
                if row["direction_window_pass"]:
                    n_dir_pass += 1
            else:
                row.update({
                    "v2_evaluable": False,
                    "delta_minutes_signed": None,
                    "delta_minutes_abs": None,
                    "delta_minutes_circular": None,
                    "main_pass_abs_le_1min": False,
                    "direction_window_pass": False,
                })
            rows[rep] = row
        v2_matrix[case] = rows
    v2_pass = (n_evaluable == 6) and (n_main_pass == 6)
    v2 = {
        "rule": "V2 = 逐 rep：token 的 HH:MM 与该 run 首消息 HH:MM 的 naive 分钟差 |Δ|≤1"
                "（逐 rep 登记 signed Δ、|Δ|、午夜循环差、方向窗 [%+d,%+d]min 布尔）；"
                "token 不满足 HH:MM 文法时 v2_evaluable=false、Δ=null；"
                "V2_pass = 6/6 可评且全过" % V2_DIRECTION_WINDOW,
        "matrix": v2_matrix,
        "evaluable_count": "%d/6" % n_evaluable,
        "main_pass_count": "%d/%d" % (n_main_pass, n_evaluable),
        "direction_window_pass_count": "%d/%d" % (n_dir_pass, n_evaluable),
        "pass": v2_pass,
    }

    # --- 8. V3：孤立位单数字值逐 rep 登记（不判语义）--------------------------
    v3_cases = {}
    for case in sorted(GROUPS):
        close = span_checks[case]["envelope_close"]
        rows = []
        for ent in ref_runs[case]:
            if ent["cluster_role"] not in ("internal", "isolated_external"):
                continue
            by_rep_val = {}
            for rep in REPS:
                reg = ent["by_rep"][rep]
                if not reg.get("run_found") or reg.get("run_len") != 1:
                    _fail("%s offset=%d %s: 孤立位非单数字 run（结构破坏）"
                          % (case, ent["offset"], rep))
                b = text_byte_at(texts_by_case[case][rep], ent["offset"])
                if byte_class(b) != CLASS_DIGIT:
                    _fail("%s offset=%d %s: 孤立位字节非数字" % (case, ent["offset"], rep))
                by_rep_val[rep] = chr(b)
            rows.append({
                "offset": ent["offset"],
                "rel_position": ent["offset"] - close,
                "lane": ("envelope_internal" if ent["cluster_role"] == "internal"
                         else "envelope_external"),
                "cluster_role": ent["cluster_role"],
                "digit_by_rep": by_rep_val,
            })
        rows.sort(key=lambda r: r["offset"])
        v3_cases[case] = rows
    v3 = {
        "rule": "V3 = 孤立位（信封内 %d + 信封外 %d，共 6 处）单数字字节值逐 rep 登记，"
                "不判语义；非单数字结构即 fail-closed"
                % (EXPECTED_INTERNAL_ISOLATED_PER_CASE, EXPECTED_ISOLATED_EXTERNAL_PER_CASE),
        "n_positions": sum(len(v) for v in v3_cases.values()),
        "cases": v3_cases,
    }

    # --- 9. 定长同格式登记（§3 第二析支的判定面）------------------------------
    toks = [tokens_by_case[c]["by_rep"][r] for c in sorted(GROUPS) for r in REPS]
    len_set = sorted({t["token_len"] for t in toks})
    class_patterns = {tuple(t["byte_classes"]) for t in toks}
    pattern_str = "".join({"digit": "D", "alpha": "A", "other": "?"}.get(c, "?")
                          for c in sorted(class_patterns)[0]) if len(class_patterns) == 1 else None
    fixed_format = (len(len_set) == 1 and len(class_patterns) == 1 and sep_same)
    fmt = {
        "definition": "定长同格式 = 6 token 字节长度集合单值 ∧ 逐位置字节类序列全体相等 "
                      "∧ 分隔字节值全体相等",
        "token_len_set": len_set,
        "class_pattern_all_equal": len(class_patterns) == 1,
        "class_pattern": list(sorted(class_patterns)[0]) if len(class_patterns) == 1
                         else [list(p) for p in sorted(class_patterns)],
        "class_pattern_signature": pattern_str,
        "separator_values_all_equal": sep_same,
        "fixed_format": fixed_format,
    }

    # --- 10. 分支（冻结 §3 字面）----------------------------------------------
    if v1_pass and v2_pass:
        verdict = "B-CLOCK-CONFIRMED"
        reason = ("V1∧V2 全过：6 token 均为合法 HH:MM 且与同 run 首消息 HH:MM 差 ≤1 分钟"
                  " ⇒ token 为构建时刻时钟注入（§4.36 语义未知面收窄为"
                  "「产品输入构建器在信封中嵌当次时钟」）。")
        exit_code = 0
    elif v1_pass and not v2_pass:
        verdict = "B-COUNTER-OTHER"
        reason = ("V1 全过∧V2 破：定长 HH:MM 文法成立但与轨迹时间戳不相关"
                  " ⇒ 固定格式计数器/编码类，时钟类否证。")
        exit_code = 0
    elif (not v1_pass) and fixed_format:
        verdict = "B-COUNTER-OTHER"
        reason = ("V1 破但 6 token 定长同格式（长度/字节类序列/分隔字节值全体一致）"
                  " ⇒ 登记格式特征，时钟类否证（按冻结 §3 第二析支）。")
        exit_code = 0
    else:
        verdict = "B-INDETERMINATE"
        reason = ("V1 破且 6 token 非定长同格式 ⇒ 无法裁定，登记 unknown（fail-closed）。")
        exit_code = 2
    branch = {
        "verdict": verdict,
        "reason": reason,
        "V1_pass": v1_pass,
        "V2_pass": v2_pass,
        "V3": "registered_no_semantics",
        "fixed_format": fixed_format,
        "exit_code": exit_code,
        "clock_class_note": "时钟类相容在环 15 仅字节类层面成立；本包在值面按冻结判据裁定："
                            "%s" % ("证实" if verdict == "B-CLOCK-CONFIRMED" else
                                    "否证" if verdict == "B-COUNTER-OTHER" else "无法裁定"),
    }

    # --- 11. 超出冻结判据的定性披露（不改变裁定、不发布秒级值；逐项条件化以保证
    #         确定性并兼容合成档案）-------------------------------------------
    all_tokens = [tokens_by_case[c]["by_rep"][r]["token"]
                  for c in sorted(GROUPS) for r in REPS]
    disclosure_items = []
    if verdict == "B-COUNTER-OTHER" and not v1_pass:
        bad = [x for x in v1_per_token if not x["regex_match"]]
        deltas_abs = [abs(row["delta_minutes_signed"])
                      for c in v2_matrix for rep in REPS
                      if (row := v2_matrix[c][rep])["v2_evaluable"]]
        disclosure_items.append(
            "token 值面（%s）：冻结 HH:MM 文法下 %d/6 合法（不合者：%s）；"
            "与首消息 HH:MM 的 |Δ|∈[%d,%d] 分钟（%d 处不可解析，Δ=null）"
            " ⇒ 按冻结判据时钟类否证"
            % ("、".join("'%s'" % t for t in all_tokens), n_regex,
               "、".join("'%s'" % x["token"] for x in bad),
               min(deltas_abs) if deltas_abs else -1,
               max(deltas_abs) if deltas_abs else -1, 6 - n_evaluable))
    incr = all(
        all(tokens_by_case[c]["by_rep"][REPS[i]]["token"]
            < tokens_by_case[c]["by_rep"][REPS[i + 1]]["token"]
            for i in range(len(REPS) - 1))
        for c in sorted(GROUPS))
    if incr:
        disclosure_items.append(
            "定性观察（超出冻结判据，不裁定）：6 token 值逐 rep 字典序严格递增"
            "（%s），与『逐 rep 递增计数/时刻递进』候选相容；其单位语义"
            "（时钟/计数器）按冻结判据裁定见 branch" % "；".join(
                "%s %s" % (c, "→".join("'%s'" % tokens_by_case[c]["by_rep"][r]["token"]
                                       for r in REPS))
                for c in sorted(GROUPS)))
    v3_flat = {}
    for case in sorted(v3_cases):
        for row in v3_cases[case]:
            for rep in REPS:
                v3_flat.setdefault(rep, []).append(row["digit_by_rep"][rep])
    rep_consistent = all(len(set(v3_flat[rep])) == 1 for rep in REPS)
    reps_distinct = len({v3_flat[rep][0] for rep in REPS if v3_flat[rep]}) == len(REPS)
    if rep_consistent and reps_distinct:
        disclosure_items.append(
            "孤立位单数字值呈『逐 rep 相异、同 rep 内 6 处一致』（%s）"
            "——与 rep 序号类标记候选相容；V3 按冻结仅登记不判语义"
            % "、".join("r%d 处处='%s'" % (i + 1, v3_flat["r%d" % (i + 1)][0])
                        for i in range(len(REPS))))

    result = {
        "schema": SCHEMA,
        "package": PACKAGE_NAME,
        "value_publication_boundary": VALUE_PUBLICATION_BOUNDARY,
        "prereg": {
            "path_rel": PREREG_PATH_REL,
            "sha256": PREREG_SHA256,
            "sha256_match": True,
        },
        "baseline_commit": git_head(root),
        "reference_sources": {
            "offsets": {"path_rel": REF11_RESULT_PATH_REL, "sha256": ref11_sha},
            "run_boundaries": {"path_rel": REF15_RESULT_PATH_REL, "sha256": ref15_sha},
        },
        "archive_layout": {
            "runs_rel": "runs/<slot>/trace/<session>.jsonl",
            "slots_expected": SLOT_ORDER,
        },
        "extraction": {
            "rule": "与环 6/11/15 同一 W1 提取：runs/<slot>/trace/*.jsonl（恰 1）、"
                    "type=message 且 role=user（恰 1）、content 恰 1 block 且 type=input_text、"
                    "text 的 UTF-8 字节",
            "per_slot": {k: {kk: vv for kk, vv in slot_results[k].items()
                             if kk != "_text"}
                         for k in SLOT_ORDER},
        },
        "hard_equal": {
            "offsets": {
                "reference_path_rel": REF11_RESULT_PATH_REL,
                "rule": "复算=逐 case 三对逐字节差异并集；硬等=环 11 result.json "
                        "case_analysis.<case>.events[*].positions_offset 全集；不等即 exit2",
                "all_equal": offsets_all_equal,
                "cases": offsets_hard,
            },
            "run_boundaries": {
                "reference_path_rel": REF15_RESULT_PATH_REL,
                "rule": "复算=逐 offset×rep 极大数字 run 全字段（run_found/起/止/长/"
                        "run 内 index/左邻类）；硬等=环 15 result.json "
                        "run_registration.cases.<case> 条目 by_rep 登记全集；不等即 exit2",
                "all_equal": runs_all_equal,
                "cases": {c: {"all_equal": runs_hard[c]["all_equal"],
                              "n_entries": runs_hard[c]["n_entries"],
                              "per_entry_equal": [e["equal"] for e in runs_hard[c]["per_entry"]]}
                          for c in sorted(runs_hard)},
            },
            "envelope_span": {
                "rule": "每 rep 恰 1 span、跨 rep 相等、且与环 11 result.json 登记的 "
                        "envelope_span 一致（lane/rel 派生基准；不符视为数据结构不可信 exit2）",
                "cases": span_checks,
            },
        },
        "timestamp_semantics": {
            "field_name": "timestamp",
            "format": "epoch_milliseconds",
            "survey_note": "预注册勘察注记称『ISO-8601 字符串』；实际 schema 为 epoch 毫秒"
                           "整数（以复算为准，字段名登记如上）",
            "timezone_rule": "固定 UTC 偏移取档案自身 runs/<slot>/collect-meta.json 的 "
                             "collected_at（ISO-8601 含偏移）之 utcoffset；6 槽必须一致，"
                             "否则 fail-closed",
            "timezone_offset": tz_offset_str,
            "timezone_slots_consistent": True,
            "conversion": "HH:MM = fromtimestamp(epoch_ms // 1000, 固定偏移) 取 %H:%M；"
                          "发布仅分钟精度（秒/毫秒与日期不发布）",
            "per_slot": ts_by_slot,
        },
        "tokens": {
            "rule": "token = 环 15 簇两组数字 run 的合并字节段 [run1.start, run2.end)，"
                    "恰 5 字节（4 数字+1 分隔）；分隔字节=两 run 之间恰 1 字节"
                    "（offset=run1.end）；逐 rep 从硬等后的参照边界独立提取",
            "cases": tokens_by_case,
        },
        "v1": v1,
        "v2": v2,
        "v3": v3,
        "format_registration": fmt,
        "branch": branch,
        "post_hoc_semantics_disclosure": {
            "rule": "超出冻结判据的定性披露（不改变分支裁定、不发布秒级值）；"
                    "检验其中任何候选语义须另立预注册",
            "items": disclosure_items,
        },
        "survey_note_reconciliation": {
            "rule": "预注册勘察注记为冻结前事实，可被复算推翻（README 冻结行）；以下以复算为准",
            "items": [
                "勘察注记称时间戳为『ISO-8601 字符串』；复算实际 schema：轨迹 jsonl 消息"
                "事件字段名 timestamp = epoch 毫秒整数（按任务授权以实际 schema 为准，"
                "字段名登记见 timestamp_semantics）；HH:MM 换算采用固定 UTC 偏移，"
                "偏移取档案自身 trace/collect-meta.json 的 collected_at（ISO-8601 含偏移）之 "
                "utcoffset，6 槽一致方有效（任一不一致即 fail-closed）",
                "V2 差值同时登记 naive 分钟差与午夜循环差 min(|Δ|,1440−|Δ|)"
                "（无午夜跨越时两者一致，本包不假设二者相等）；token 不满足 HH:MM 文法时"
                "Δ=null（v2_evaluable=false），不强行按非法时刻求差",
                "首消息=该 run 轨迹第一条 type=message 事件（复算 role=user，逐槽断言）；"
                "消息时间戳逐槽单调不减（逐槽断言）；逐槽消息数见 "
                "timestamp_semantics.per_slot（仅计数，不含内容）",
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
            "token_definition": "见 tokens.rule；token 字节含非 ASCII 即 fail-closed"
                                "（值发布边界：只发布 4 数字+1 分隔的 5 字节值）",
            "fixed_format_definition": fmt["definition"],
            "v1_rule": v1["rule"],
            "v2_rule": v2["rule"],
            "v3_rule": v3["rule"],
            "branch_rule": "冻结 §3 字面：V1∧V2 ⇒ B-CLOCK-CONFIRMED；"
                           "V1 全过∧V2 破 ⇒ B-COUNTER-OTHER；"
                           "V1 破但 6 token 定长同格式 ⇒ B-COUNTER-OTHER；"
                           "否则 ⇒ B-INDETERMINATE / exit2",
            "value_publication_boundary": VALUE_PUBLICATION_BOUNDARY,
            "fail_closed_scope": "预注册封印不符、双硬等（offsets/run 边界）失败、档案布局"
                                 "异常、trace/消息结构异常、时区偏移不一致或缺失、"
                                 "信封 span 数≠1 或与环 11 不符、孤立位非单数字、"
                                 "token 非 5 ASCII 字节 ⇒ exit2 / B-INDETERMINATE",
        },
        "exit_code": exit_code,
    }
    return result


def text_byte_at(text: bytes, off: int) -> int:
    if not (0 <= off < len(text)):
        _fail("offset 越界: %d" % off)
    return text[off]


def _format_signed(v):
    if v is None:
        return "null"
    return "%+d" % v if v > 0 else str(v)


def summarize(result: dict) -> str:
    """确定性 stdout 摘要（无私有绝对路径；发布值仅限冻结值发布边界内）。"""
    lines = []
    lines.append("RESULT %s schema=%s" % (result["package"], result["schema"]))
    lines.append("prereg_sha256_ok=true sha=%s" % result["prereg"]["sha256"])
    lines.append("baseline_commit=%s" % result["baseline_commit"])
    lines.append("archive_slots=%d user_texts_extracted=%d"
                 % (len(result["archive_layout"]["slots_expected"]),
                    len(result["extraction"]["per_slot"])))
    he = result["hard_equal"]["offsets"]
    per_case = " ".join("%s:%d" % (c, he["cases"][c]["n_offsets"])
                        for c in sorted(he["cases"]))
    lines.append("offsets_hard_equal=%s reference=%s offsets(%s)"
                 % (str(he["all_equal"]).lower(), he["reference_path_rel"], per_case))
    rh = result["hard_equal"]["run_boundaries"]
    per_case = " ".join("%s:%d" % (c, rh["cases"][c]["n_entries"])
                        for c in sorted(rh["cases"]))
    lines.append("run_boundary_hard_equal=%s reference=%s entries(%s)"
                 % (str(rh["all_equal"]).lower(), rh["reference_path_rel"], per_case))
    sc = result["hard_equal"]["envelope_span"]["cases"]
    lines.append("envelope_span: matches_reference=%s close(%s)"
                 % (str(all(v["matches_reference"] for v in sc.values())).lower(),
                    " ".join("%s:%d" % (c, sc[c]["envelope_close"])
                             for c in sorted(sc))))
    ts = result["timestamp_semantics"]
    lines.append("timestamp field=%s format=%s timezone=%s source=trace/collect-meta.json:collected_at"
                 " slots_consistent=%s"
                 % (ts["field_name"], ts["format"], ts["timezone_offset"],
                    str(ts["timezone_slots_consistent"]).lower()))
    toks = result["tokens"]["cases"]
    parts = []
    for case in sorted(toks):
        reps = toks[case]["by_rep"]
        parts.append("%s %s sep='%s'" % (
            case,
            " ".join("%s='%s'" % (rep, reps[rep]["token"]) for rep in REPS),
            reps["r1"]["separator"]["value"]))
    lines.append("tokens: %s" % " | ".join(parts))
    v1 = result["v1"]
    lines.append("V1=%s regex=%s separator_same=%s(value=%s)"
                 % (str(v1["pass"]).lower(), v1["regex_match_count"],
                    str(v1["separator_all_same"]).lower(), v1["separator_value"]))
    v2 = result["v2"]
    delta_parts = []
    for case in sorted(v2["matrix"]):
        vals = ",".join(_format_signed(v2["matrix"][case][rep]["delta_minutes_signed"])
                        for rep in REPS)
        delta_parts.append("%s: %s" % (case, vals))
    lines.append("V2=%s evaluable=%s main(|d|<=%dmin)=%s direction_window(%+d..%+dmin)=%s "
                 "deltas_min(%s)"
                 % (str(v2["pass"]).lower(), v2["evaluable_count"], V2_MAX_ABS_DELTA_MIN,
                    v2["main_pass_count"], V2_DIRECTION_WINDOW[0], V2_DIRECTION_WINDOW[1],
                    v2["direction_window_pass_count"], " | ".join(delta_parts)))
    v3 = result["v3"]
    v3_parts = []
    for case in sorted(v3["cases"]):
        for row in v3["cases"][case]:
            digits = "/".join(row["digit_by_rep"][rep] for rep in REPS)
            v3_parts.append("%s %s %d=%s" % (case, row["cluster_role"],
                                             row["offset"], digits))
    lines.append("V3 registered=%d positions digits(%s)"
                 % (v3["n_positions"], " ".join(v3_parts)))
    fmt = result["format_registration"]
    lines.append("fixed_format=%s len=%s class_pattern=%s sep_all_same=%s"
                 % (str(fmt["fixed_format"]).lower(), fmt["token_len_set"],
                    fmt["class_pattern_signature"],
                    str(fmt["separator_values_all_equal"]).lower()))
    fl_parts = []
    for case in sorted(toks):
        reps = toks[case]["by_rep"]
        seg = " ".join("%s=%s/%s" % (rep,
                                     result["timestamp_semantics"]["per_slot"]
                                     [reps[rep]["slot"]]["first_ts_hhmm"],
                                     result["timestamp_semantics"]["per_slot"]
                                     [reps[rep]["slot"]]["last_ts_hhmm"])
                       for rep in REPS)
        fl_parts.append("%s %s" % (case, seg))
    lines.append("first/last_hhmm: %s" % " | ".join(fl_parts))
    b = result["branch"]
    lines.append("branch=%s v1=%s v2=%s fixed_format=%s clock_class=%s"
                 % (b["verdict"], str(b["V1_pass"]).lower(), str(b["V2_pass"]).lower(),
                    str(b["fixed_format"]).lower(), b["clock_class_note"].split("：")[-1]))
    lines.append("survey_reconciliation_items=%d post_hoc_disclosure_items=%d"
                 % (len(result["survey_note_reconciliation"]["items"]),
                    len(result["post_hoc_semantics_disclosure"]["items"])))
    lines.append("exit=%d" % result["exit_code"])
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="WB 复测漂移 token 值语义检验 复算（预注册 v1，schema %s）" % SCHEMA)
    parser.add_argument("--root", required=True, help="公开仓库根")
    parser.add_argument("--archive-root", required=True,
                        help="WorkBuddy 复测档根（其下含 runs/<6 槽>/trace/*.jsonl 与"
                             " runs/<槽>/collect-meta.json）")
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
        return result["exit_code"]
    except VerifyError as exc:
        sys.stdout.write("FAIL: %s\nexit=2\n" % exc)
        return 2
    except Exception as exc:  # fail-closed：未知异常也 exit 2
        sys.stdout.write("FAIL(unexpected): %r\nexit=2\n" % (exc,))
        return 2


if __name__ == "__main__":
    sys.exit(main())
