#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WB 复测漂移 token 的 mm:ss 时钟同一性确认 — 预注册 v1 复算工具。

用法：
  python3 verify.py --root <repo> --archive-root <bw-retest/workbuddy 根> [--output result.json]

- --root：公开仓库根（含本包冻结 README 预注册与两份硬等参照：
  4-打分细则/WB漂移字节位置结构-2026-11-16/result.json（漂移 offsets 全集）、
  4-打分细则/WB漂移token形状-2026-11-16/result.json（run 边界登记））。
- --archive-root：WorkBuddy 复测档根（其下 runs/<6 槽>/trace/*.jsonl 与
  runs/<槽>/trace/collect-meta.json）。
- stdout：确定性人类摘要（不含私有绝对路径）；exit 0=CONFIRMED-POSTHOC/PARTIAL，
  2=fail-closed 或 B-MMSS-REFUTED（冻结 §3：REFUTED/硬等失败 ⇒ exit2）。
- --output：独占创建完整 result.json（schema wb-token-clock-v1）；目标已存在则拒改 exit 2。

值发布边界（冻结 §2）：本包读 W1 提取文本与同 run 轨迹消息时间戳字段；发布仅限——
漂移 token 的 5 字节值（两组各 2 位数字 + 1 分隔字节）、逐处秒差整数、逐槽首/末消息
时刻的 HH:MM:SS（元数据面，秒精度墙钟；毫秒与日期不发布）、结构登记（offset/run
边界/字节类/字段名）；任务正文、字母序列、多字节切片、消息文本、毫秒级时刻、日期、
私有绝对路径零发布。实现独立成文，不 import 其他包代码（W1 提取方式与环 6/11/15/17
包公开做法同构：runs/<slot>/trace/*.jsonl、role=user、content[0].type=input_text）。

事后假设声明（冻结 §诚实披露）：本包假设源于环 17 Lead 验证期观察（token 前 2 位=
首消息「分」6/6、全 token=「分:秒」4/6 精确、2/6 秒位差 1），非独立预测；本包将其
转为显式冻结判据并在同一归档上确认/否证，证据等级=事后确认，弱于事前预测。
声明照实写入 result.json（post_hoc_declaration）。
"""
import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

PACKAGE_NAME = "WB漂移token毫秒钟确认-2026-11-16"
SCHEMA = "wb-token-clock-v1"

PREREG_PATH_REL = "4-打分细则/WB漂移token毫秒钟确认-2026-11-16/README.md"
PREREG_SHA256 = "b28942fa8943a55f4eddba5434a88f92387fd5bf8c69a80b921418b6f610e27d"
REF11_RESULT_PATH_REL = "4-打分细则/WB漂移字节位置结构-2026-11-16/result.json"
REF15_RESULT_PATH_REL = "4-打分细则/WB漂移token形状-2026-11-16/result.json"

# W1 信封（环 6/11/15/17 同一冻结定义：精确匹配该开标记；span 至其后第一个
# 闭合标记结束；标记文本不在 result 中重复登记）。
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

# 冻结 §2 断言（本包判据；V1′ 与环 17 旧正则 ^([01]\d|2[0-3]):[0-5]\d$ 的差异点：
# 本正则首字段为「分」(00-59)，合法 mm:ss 如 25:55/59:59 均通过）。
V1P_PATTERN = re.compile(r"^([0-5]\d):([0-5]\d)$")
V2P_MAX_ABS_DELTA_S = 1          # 主断言：|token mm:ss − 首消息 mm:ss| ≤ 1 秒，全 6
V3P_N = 6                        # 冗余核验：token 前 2 位 = 首消息「分」，6/6

EXPECTED_TOKEN_BYTES = 5                     # 两组各 2 位数字 + 1 分隔字节
EXPECTED_CLUSTER_RUN_LEN = 2                 # 冻结：两组 run 各长 2
EXPECTED_INTERNAL_ISOLATED_PER_CASE = 2      # 信封内孤立位（环 15 结构）
EXPECTED_ISOLATED_EXTERNAL_PER_CASE = 1      # 信封外孤立位（环 15 结构）

VALUE_PUBLICATION_BOUNDARY = (
    "值发布边界声明（冻结 §2）：本包发布——漂移 token 的 5 字节值（两组各 2 位数字"
    "+1 分隔字节）、逐处秒差整数、逐槽首/末消息时刻的 HH:MM:SS（元数据面，秒精度"
    "墙钟，毫秒与日期不发布）、结构登记（offset/run 边界/字节类/字段名）；任务正文、"
    "字母序列、多字节切片、消息文本、毫秒级时刻、日期、私有绝对路径零发布。"
)

POST_HOC_DECLARATION = {
    "hypothesis_source": "环 17 Lead 验证期观察",
    "source_observations": [
        "token 前 2 位 = 首消息「分」6/6",
        "全 token = 「分:秒」4/6 精确",
        "2/6 秒位差 1",
    ],
    "independent_prediction": False,
    "evidence_grade": "事后确认（post-hoc），弱于事前预测，登记照实",
    "statement": "本包假设源于环 17 Lead 验证期观察（token 前 2 位=首消息「分」6/6、"
                 "全 token=「分:秒」4/6 精确、2/6 秒位差 1），非独立预测；本包将其转为"
                 "显式冻结判据（V1′/V2′/V3′）并在同一归档上确认/否证，证据等级=事后确认。",
    "declared_in_prereg": True,
}


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
                _fail("硬等参照（环 15 run 边界）%s offset=%d 缺 by_rep"
                      % (case, ent["offset"]))
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
    """包含 off 的极大数字 run（值面工具，此处返回值供 token/V 断言使用）：
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
# 时间戳（元数据面）：epoch 毫秒 → 固定偏移墙钟 HH:MM:SS
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


def epoch_ms_to_hhmmss(ms: int, tz: datetime.timezone) -> str:
    if not isinstance(ms, int) or isinstance(ms, bool):
        _fail("时间戳非 epoch 毫秒整数（实际 schema 以复算为准）")
    # 秒精度墙钟：epoch 毫秒先向整秒截断（floor），再取固定偏移本地 %H:%M:%S；
    # 毫秒余数与日期不发布（值发布边界）。
    return datetime.datetime.fromtimestamp(ms // 1000, tz=tz).strftime("%H:%M:%S")


def register_messages(events, slot: str, tz: datetime.timezone) -> dict:
    """同 run 轨迹消息时间戳登记：首个与末个消息的 HH:MM:SS（仅秒精度发布）。"""
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
        "first_ts_hhmmss": epoch_ms_to_hhmmss(tss[0], tz),
        "last_ts_hhmmss": epoch_ms_to_hhmmss(tss[-1], tz),
    }


def mmss_to_seconds_of_hour(mmss: str) -> int:
    """「分:秒」→ 当小时内秒数（mm*60+ss）。仅接受 V1′ 文法合法串。"""
    m = V1P_PATTERN.match(mmss)
    if not m:
        _fail("mmss_to_seconds_of_hour 收到非法 mm:ss 串: %r" % mmss)
    return int(m.group(1)) * 60 + int(m.group(2))


def first_mmss_of(hhmmss: str) -> str:
    """HH:MM:SS 的「分:秒」两位字段（当小时内墙钟，忽略小时）。"""
    if not re.match(r"^\d{2}:\d{2}:\d{2}$", hhmmss):
        _fail("首消息时刻非 HH:MM:SS: %r" % hhmmss)
    return hhmmss[3:8]


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

    # --- 5. token 提取：簇两组 run（各长 2）+ 中间 1 分隔字节 = 5 字节 ---------
    tokens_by_case = {}
    for case in sorted(GROUPS):
        close = span_checks[case]["envelope_close"]
        cluster_entries = [e for e in ref_runs[case] if e["cluster_role"] == "cluster"]
        internal_entries = [e for e in ref_runs[case] if e["cluster_role"] == "internal"]
        iso_ext_entries = [e for e in ref_runs[case]
                           if e["cluster_role"] == "isolated_external"]
        if len(internal_entries) != EXPECTED_INTERNAL_ISOLATED_PER_CASE:
            _fail("%s: 信封内孤立位数=%d（环 15 冻结结构应为 %d）"
                  % (case, len(internal_entries), EXPECTED_INTERNAL_ISOLATED_PER_CASE))
        if len(iso_ext_entries) != EXPECTED_ISOLATED_EXTERNAL_PER_CASE:
            _fail("%s: 信封外孤立位数=%d（环 15 冻结结构应为 %d）"
                  % (case, len(iso_ext_entries), EXPECTED_ISOLATED_EXTERNAL_PER_CASE))
        # 簇 → 两组 run（逐 rep 从硬等后的参照边界取，并独立复核各长 2、间隔 1）
        run_bounds = set()
        for ent in cluster_entries:
            for rep in REPS:
                reg = ent["by_rep"][rep]
                if not reg.get("run_found"):
                    _fail("%s offset=%d %s run_found=false（簇结构破坏）"
                          % (case, ent["offset"], rep))
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
            if (e1 - s1) != EXPECTED_CLUSTER_RUN_LEN or (e2 - s2) != EXPECTED_CLUSTER_RUN_LEN:
                _fail("%s %s: 簇 run 长=%d/%d（冻结应为各长 %d）"
                      % (case, rep, e1 - s1, e2 - s2, EXPECTED_CLUSTER_RUN_LEN))
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
                _fail("%s %s: token 含非 ASCII 字节，超出值发布边界（冻结结构应为"
                      " 2 数字+分隔+2 数字）" % (case, rep))
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

    # --- 6. V1′：mm:ss 文法（分:秒，两字段均 ≤59）+ 分隔字节值 6/6 同一 --------
    v1p_per_token = []
    for case in sorted(GROUPS):
        for rep in REPS:
            t = tokens_by_case[case]["by_rep"][rep]
            v1p_per_token.append({
                "case": case, "rep": rep, "token": t["token"],
                "regex_pattern": V1P_PATTERN.pattern,
                "regex_match": bool(V1P_PATTERN.match(t["token"])),
            })
    n_regex = sum(1 for x in v1p_per_token if x["regex_match"])
    sep_values = [tokens_by_case[c]["by_rep"][r]["separator"]["value"]
                  for c in sorted(GROUPS) for r in REPS]
    sep_same = len(set(sep_values)) == 1
    v1p_pass = (n_regex == 6) and sep_same
    v1p = {
        "rule": "V1′ = 全部 6 token 匹配 %s（两位:两位、两字段均 ≤59；即「分:秒」，"
                "区别环 17 旧正则 ^([01]\\d|2[0-3]):[0-5]\\d$）且分隔字节值 6/6 同一"
                % V1P_PATTERN.pattern,
        "per_token": v1p_per_token,
        "regex_match_count": "%d/6" % n_regex,
        "separator_value": sep_values[0] if sep_same else sorted(set(sep_values)),
        "separator_same_count": "%d/6" % sum(1 for v in sep_values if v == sep_values[0]),
        "separator_all_same": sep_same,
        "pass": v1p_pass,
    }

    # --- 7. V2′：token mm:ss vs 同 run 首消息时刻 mm:ss（秒差，全 6 |Δ|≤1s）----
    v2p_matrix = {}
    n_evaluable = 0
    n_pass = 0
    for case in sorted(GROUPS):
        rows = {}
        for rep in REPS:
            t = tokens_by_case[case]["by_rep"][rep]
            slot_ts = ts_by_slot[t["slot"]]
            first_hhmmss = slot_ts["first_ts_hhmmss"]
            row = {
                "token": t["token"],
                "first_ts_hhmmss": first_hhmmss,
                "last_ts_hhmmss": slot_ts["last_ts_hhmmss"],
            }
            if V1P_PATTERN.match(t["token"]):
                tok_s = mmss_to_seconds_of_hour(t["token"])
                first_s = mmss_to_seconds_of_hour(first_mmss_of(first_hhmmss))
                delta = tok_s - first_s
                if delta == 0:
                    boundary = "exact_0s"
                elif delta == V2P_MAX_ABS_DELTA_S:
                    boundary = "boundary_+1s"
                elif delta == -V2P_MAX_ABS_DELTA_S:
                    boundary = "boundary_-1s"
                else:
                    boundary = "outside_±1s"
                row.update({
                    "v2_evaluable": True,
                    "token_seconds_of_hour": tok_s,
                    "first_mmss_seconds_of_hour": first_s,
                    "delta_seconds_signed": delta,
                    "delta_seconds_abs": abs(delta),
                    "boundary_attribution": boundary,
                    "pass_abs_le_1s": abs(delta) <= V2P_MAX_ABS_DELTA_S,
                })
                n_evaluable += 1
                if row["pass_abs_le_1s"]:
                    n_pass += 1
            else:
                row.update({
                    "v2_evaluable": False,
                    "token_seconds_of_hour": None,
                    "first_mmss_seconds_of_hour": None,
                    "delta_seconds_signed": None,
                    "delta_seconds_abs": None,
                    "boundary_attribution": None,
                    "pass_abs_le_1s": False,
                })
            rows[rep] = row
        v2p_matrix[case] = rows
    v2p_pass = (n_evaluable == 6) and (n_pass == 6)
    v2p = {
        "rule": "V2′ = 逐 rep：|token(mm:ss) − 首消息时刻(mm:ss)| ≤ %d 秒全 6 处成立"
                "（首消息时刻取该 run 轨迹首消息 timestamp（epoch 毫秒）秒精度墙钟 "
                "HH:MM:SS 的「分:秒」字段；逐处登记精确秒差 signed/|Δ|/±1s 边界归属）；"
                "token 不满足 mm:ss 文法时 v2_evaluable=false、Δ=null"
                % V2P_MAX_ABS_DELTA_S,
        "matrix": v2p_matrix,
        "evaluable_count": "%d/6" % n_evaluable,
        "pass_count": "%d/%d" % (n_pass, n_evaluable),
        "delta_seconds_matrix": {c: [v2p_matrix[c][r]["delta_seconds_signed"]
                                     for r in REPS] for c in sorted(v2p_matrix)},
        "pass": v2p_pass,
    }

    # --- 8. V3′：token 前 2 位 = 首消息「分」（冗余核验，6/6）------------------
    v3p_per_token = []
    n_minute = 0
    for case in sorted(GROUPS):
        for rep in REPS:
            t = tokens_by_case[case]["by_rep"][rep]
            first_hhmmss = ts_by_slot[t["slot"]]["first_ts_hhmmss"]
            first2 = t["token"][:2]
            minute = first_hhmmss[3:5]
            eq = first2 == minute
            n_minute += 1 if eq else 0
            v3p_per_token.append({
                "case": case, "rep": rep,
                "token_first2": first2,
                "first_message_minute": minute,
                "equal": eq,
            })
    v3p_pass = (n_minute == V3P_N) and (n_evaluable == 6)
    v3p = {
        "rule": "V3′ = token 前 2 位 = 首消息「分」（HH:MM:SS 的分字段两位串）6/6"
                "（与 V2′ 同前源的冗余核验）",
        "per_token": v3p_per_token,
        "match_count": "%d/6" % n_minute,
        "pass": v3p_pass,
    }

    # --- 9. 分支（冻结 §3 字面）----------------------------------------------
    if v1p_pass and v2p_pass and v3p_pass:
        verdict = "B-MMSS-CONFIRMED-POSTHOC"
        reason = ("V1′∧V2′∧V3′ 全过：6 token 均为合法 mm:ss 且逐处与首消息时刻秒差 "
                  "|Δ|≤1s、前 2 位=首消息「分」⇒ 环 15/16「数字 token」语义收口：输入"
                  "信封嵌入构建时刻 mm:ss（逐运行变化、位置固定）。环 17 "
                  "B-COUNTER-OTHER 冻结判据字面结果不改写，本包登记语义层修正"
                  "（证据等级=事后确认）。")
        exit_code = 0
    elif v1p_pass and (4 <= n_pass <= 5):
        verdict = "B-MMSS-PARTIAL"
        reason = ("V1′ 全过∧V2′ %d/6：6 token 均为合法 mm:ss 且多数与首消息时刻一致，"
                  "登记逐处秒差明细，判定「与首消息时刻一致但存在秒级偏差源未定位」"
                  "（±1s 偏差源不判，冻结 §5）。" % n_pass)
        exit_code = 0
    else:
        verdict = "B-MMSS-REFUTED"
        reason = ("V1′ 未全过（%s）或 V2′ 通过数=%d 不在 [4,6] 或 V3′ 破且 V2′ 非 4–5/6"
                  " ⇒ mm:ss 时钟同一性假设按冻结 §3 否证（exit2）。"
                  % (v1p["regex_match_count"] + ("/分隔不同一" if not sep_same else ""),
                     n_pass))
        exit_code = 2
    branch = {
        "verdict": verdict,
        "reason": reason,
        "V1_prime_pass": v1p_pass,
        "V2_prime_pass": v2p_pass,
        "V2_prime_pass_count": "%d/6" % n_pass,
        "V3_prime_pass": v3p_pass,
        "exit_code": exit_code,
        "round17_note": "环 17 B-COUNTER-OTHER 保持不动（其冻结判据字面结果不改写）；"
                        "本包为语义层修正登记，旧正则 ^([01]\\d|2[0-3]):[0-5]\\d$ 将合法"
                        " mm:ss（如 25:55）误判非法。",
    }

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
            "rule": "与环 6/11/15/17 同一 W1 提取：runs/<slot>/trace/*.jsonl（恰 1）、"
                    "type=message 且 role=user（恰 1）、content 恰 1 block 且 "
                    "type=input_text、text 的 UTF-8 字节",
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
                        "envelope_span 一致（close 为簇 rel 基准；不符视为数据结构"
                        "不可信 exit2）",
                "cases": span_checks,
            },
        },
        "timestamp_semantics": {
            "field_name": "timestamp",
            "format": "epoch_milliseconds",
            "timezone_rule": "固定 UTC 偏移取档案自身 runs/<slot>/trace/collect-meta.json "
                             "的 collected_at（ISO-8601 含偏移）之 utcoffset；6 槽必须一致，"
                             "否则 fail-closed",
            "timezone_offset": tz_offset_str,
            "timezone_slots_consistent": True,
            "conversion": "HH:MM:SS = fromtimestamp(epoch_ms // 1000, 固定偏移) 取 %H:%M:%S"
                          "（毫秒向整秒截断 floor）；发布仅秒精度墙钟，毫秒与日期不发布",
            "per_slot": ts_by_slot,
        },
        "tokens": {
            "rule": "token = 环 15 簇两组数字 run 的合并字节段 [run1.start, run2.end)，"
                    "恰 5 字节 = 两组 run（各长 2）+ 中间 1 分隔字节；分隔字节="
                    "两 run 之间恰 1 字节（offset=run1.end）；逐 rep 从硬等后的参照"
                    "边界独立提取",
            "cases": tokens_by_case,
        },
        "v1_prime": v1p,
        "v2_prime": v2p,
        "v3_prime": v3p,
        "branch": branch,
        "post_hoc_declaration": POST_HOC_DECLARATION,
        "analysis_rules": {
            "byte_class_definition": "digit=ASCII 0-9；alpha=ASCII A-Z/a-z；"
                                     "other=其余全部字节（含 UTF-8 多字节序列、标点等）；"
                                     "bof=run 起点为文本首（无左邻，结构性取值）",
            "run_definition": "极大数字 run=文本中 byte_class==digit 的极大连续段 [起,止)；"
                              "逐 offset×rep 独立计算",
            "envelope_definition": "信封=W1 冻结开/闭标记的精确 span（标记字面以环 11 包 "
                                   "analysis_rules 同名定义为准，此处不重复登记标记文本）",
            "rel_position_definition": "rel_position = offset − 信封闭合（envelope span 终点）",
            "token_definition": "见 tokens.rule；两组 run 各长 2、间隔恰 1、合计 5 ASCII"
                                "字节，否则 fail-closed（值发布边界：只发布 5 字节值）",
            "v1_prime_rule": v1p["rule"],
            "v2_prime_rule": v2p["rule"],
            "v3_prime_rule": v3p["rule"],
            "delta_definition": "秒差 = token「分:秒」当小时内秒数 − 首消息时刻 HH:MM:SS"
                                "「分:秒」当小时内秒数（同小时 naive 口径，逐处登记 "
                                "signed 整数与 ±1s 边界归属；跨小时/午夜情形不在冻结"
                                "判据内，不引入循环差）",
            "branch_rule": "冻结 §3 字面：V1′∧V2′∧V3′ 全过 ⇒ B-MMSS-CONFIRMED-POSTHOC；"
                           "V1′ 全过∧V2′ 4–5/6 ⇒ B-MMSS-PARTIAL；否则/硬等失败 ⇒ "
                           "B-MMSS-REFUTED / exit2",
            "value_publication_boundary": VALUE_PUBLICATION_BOUNDARY,
            "fail_closed_scope": "预注册封印不符、双硬等（offsets/run 边界）失败、档案布局"
                                 "异常、trace/消息结构异常、时区偏移不一致或缺失、"
                                 "信封 span 数≠1 或与环 11 不符、孤立位数不符环 15 结构、"
                                 "簇 run 组数≠2 或各长≠2 或间隔≠1、token 非 5 ASCII 字节"
                                 " ⇒ exit2",
        },
        "exit_code": exit_code,
    }
    return result


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
    lines.append("posthoc_declared=true source=%s independent_prediction=%s"
                 % (result["post_hoc_declaration"]["hypothesis_source"],
                    str(result["post_hoc_declaration"]["independent_prediction"]).lower()))
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
    v1p = result["v1_prime"]
    lines.append("V1p=%s match=%s separator_same=%s(value=%s pattern=%s)"
                 % (str(v1p["pass"]).lower(), v1p["regex_match_count"],
                    str(v1p["separator_all_same"]).lower(), v1p["separator_value"],
                    v1p["per_token"][0]["regex_pattern"]))
    v2p = result["v2_prime"]
    delta_parts = []
    for case in sorted(v2p["delta_seconds_matrix"]):
        vals = ",".join(_format_signed(v) for v in v2p["delta_seconds_matrix"][case])
        delta_parts.append("%s: %s" % (case, vals))
    lines.append("V2p=%s evaluable=%s pass(|d|<=%ds)=%s deltas_s(%s)"
                 % (str(v2p["pass"]).lower(), v2p["evaluable_count"],
                    V2P_MAX_ABS_DELTA_S, v2p["pass_count"], " | ".join(delta_parts)))
    bound_parts = []
    for case in sorted(v2p["matrix"]):
        for rep in REPS:
            row = v2p["matrix"][case][rep]
            bound_parts.append("%s %s=%s" % (case, rep, row["boundary_attribution"]))
    lines.append("V2p_boundary(%s)" % " ".join(bound_parts))
    v3p = result["v3_prime"]
    lines.append("V3p=%s minute_match=%s"
                 % (str(v3p["pass"]).lower(), v3p["match_count"]))
    fl_parts = []
    for case in sorted(toks):
        reps = toks[case]["by_rep"]
        seg = " ".join("%s=%s/%s" % (rep,
                                     result["timestamp_semantics"]["per_slot"]
                                     [reps[rep]["slot"]]["first_ts_hhmmss"],
                                     result["timestamp_semantics"]["per_slot"]
                                     [reps[rep]["slot"]]["last_ts_hhmmss"])
                       for rep in REPS)
        fl_parts.append("%s %s" % (case, seg))
    lines.append("first/last_hhmmss: %s" % " | ".join(fl_parts))
    b = result["branch"]
    lines.append("branch=%s v1p=%s v2p=%s(%s) v3p=%s"
                 % (b["verdict"], str(b["V1_prime_pass"]).lower(),
                    str(b["V2_prime_pass"]).lower(), b["V2_prime_pass_count"],
                    str(b["V3_prime_pass"]).lower()))
    lines.append("exit=%d" % result["exit_code"])
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="WB 复测漂移 token mm:ss 时钟同一性确认 复算（预注册 v1，schema %s）"
                    % SCHEMA)
    parser.add_argument("--root", required=True, help="公开仓库根")
    parser.add_argument("--archive-root", required=True,
                        help="WorkBuddy 复测档根（其下含 runs/<6 槽>/trace/*.jsonl 与"
                             " runs/<槽>/trace/collect-meta.json）")
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
