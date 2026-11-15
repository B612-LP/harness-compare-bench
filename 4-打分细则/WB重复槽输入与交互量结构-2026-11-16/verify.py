#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify.py — WB重复槽输入与交互量结构-2026-11-16 预注册验证器。

预注册：4-打分细则/WB重复槽输入与交互量结构-2026-11-16/README.md（冻结，
SHA256=2957a69b066d6c4c73c66372e2661244ebf80f93436a9f2c6cc99712096b3584）。

纯事后结构分析：对 r1109-bw-retest 的 WorkBuddy 六个复测槽
（dabstep-payments-10、tb-cargo-plan 各 r1–r3）做：
  W1 输入侧首条 user 消息跨重复字节稳定性（逐组三对两两）；
  W2 交互量事件结构登记（描述性，不设门）；
  W3 判分值与已发布公开页常量逐槽硬等（锚定已判分槽位）。

内容无关纪律：结果只含计数、字节偏移、span、字节数、SHA256；
不含任何信封或任务文本内容、差异字节值、私档绝对路径。

fail-closed 常量（trace SHA/字节数、user 文本 SHA/字节数、判分值等）
由建包人于 2026-11-16 从私有档案读定后钉入本文件 DEFAULT_PINS，
不由预注册页预置（设计要求）。

用法：
  python3 verify.py --root <repo> --archive-root <archive> [--output result.json]

  --root         公开仓库根（用于 prereg README 校验与 baseline_commit）。
  --archive-root WorkBuddy 复测档根：其下须恰有 runs/<6 槽>/trace/*.jsonl
                 与 evidence-tools/grading/<6 槽>/execution.json。
  --output       独占创建写完整 result.json（已存在则拒改，exit 2）。

退出码：0 = 全部检查通过；2 = 任一 fail-closed 条件失败（含 CLI 参数错误）。
python3 与 python3 -O 双档 stdout 逐字节一致（本文件不使用 assert 控制行为）。
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 冻结常量（预注册钉定）
# ---------------------------------------------------------------------------

PREREG_SHA256 = "2957a69b066d6c4c73c66372e2661244ebf80f93436a9f2c6cc99712096b3584"
PREREG_PATH_REL = Path("4-打分细则") / "WB重复槽输入与交互量结构-2026-11-16" / "README.md"
PACKAGE_NAME = "WB重复槽输入与交互量结构-2026-11-16"

PUBLIC_PAGE_PATH_REL = "3-表现现场/r1109-bw-retest/README.md"
# 公开页表格行（reward / weighted 顺序，rep 顺序 r1..r3），建包时核对，作 W3 钉等来源出处。
PUBLIC_PAGE_ROWS = {
    "dabstep-payments-10": ["0 / 50.0", "0 / 70.0", "0 / 70.0"],
    "tb-cargo-plan": ["0 / 0.0", "0 / 70.37", "0 / 70.37"],
}

GROUPS = {
    "dabstep-payments-10": ["r1", "r2", "r3"],
    "tb-cargo-plan": ["r1", "r2", "r3"],
}
SLOT_ORDER = [
    "dabstep-payments-10__r1",
    "dabstep-payments-10__r2",
    "dabstep-payments-10__r3",
    "tb-cargo-plan__r1",
    "tb-cargo-plan__r2",
    "tb-cargo-plan__r3",
]

KNOWN_EVENT_TYPES = {
    "session-meta",
    "message",
    "file-history-snapshot",
    "ai-title",
    "function_call",
    "function_call_result",
    "reasoning",
}

# W1 信封（冻结定义：精确匹配该开标记；span 至其后第一个闭合标记结束）。
ENVELOPE_OPEN = b'<system-reminder data-role="user-context">'
ENVELOPE_CLOSE = b"</system-reminder>"

# W2 canonical 投影：顶层剔除的逐会话易变外层元数据键（以实际档案核实：
# id/parentId/callId/messageId=事件与会话级标识；sessionId=会话标识；
# timestamp=毫秒时间戳；cwd=逐会话本地绝对路径；_meta=traceparent/baggage
# 追踪元数据；__codebuddyLocal=本地审查标记；providerData=请求级 provider
# 元数据信封，内含 conversationRequestId/messageId/traceId/stepSeq）。
STRIPPED_TOP_LEVEL_KEYS = [
    "__codebuddyLocal",
    "_meta",
    "callId",
    "cwd",
    "id",
    "messageId",
    "parentId",
    "providerData",
    "sessionId",
    "timestamp",
]
CANONICAL_JSON_OPTS = "sort_keys=True, ensure_ascii=False, separators=(',', ':')"

# ---------------------------------------------------------------------------
# fail-closed 钉定常量（建包时从私有档案读定，2026-11-16）
# ---------------------------------------------------------------------------

DEFAULT_PINS = {
    "slots": {
        "dabstep-payments-10__r1": {
            "trace_file": "b363e658-08b1-4ff9-84c8-468e7744b02d.jsonl",
            "trace_sha256": "4ad625f691446c416f98ae094d483d271d45a961a12d85ff2e8f07bbf3747ea3",
            "trace_bytes": 490524,
            "session_id": "b363e658-08b1-4ff9-84c8-468e7744b02d",
            "user_text_sha256": "0ae6064db57b71bcb5d4b584b0d713e1f1235f2230204240537c64a3d775a945",
            "user_text_bytes": 10959,
            "grading_sha256": "9c23b531e2bb8d61e5637a0fbb815116af52926a657ec8ffdee0aea26c12dd4a",
            "reward": 0,
            "weighted": 50.0,
        },
        "dabstep-payments-10__r2": {
            "trace_file": "66e68d87-dfc8-41ff-9c39-00da7e109a5a.jsonl",
            "trace_sha256": "8ebff581736ae6cf24c7cc5335c5a5b06bf3e4f1f7bac2026b61db9a00454da5",
            "trace_bytes": 485980,
            "session_id": "66e68d87-dfc8-41ff-9c39-00da7e109a5a",
            "user_text_sha256": "85a633abf987bdb2b9a8a67007a66e41cc5487c0e1d1bd6a031a26424c8e2835",
            "user_text_bytes": 10959,
            "grading_sha256": "d2bb228aaeabf084fdac3e4a92ccc6be6391b57ca6978c4eb245f3b5909d6b6d",
            "reward": 0,
            "weighted": 70.0,
        },
        "dabstep-payments-10__r3": {
            "trace_file": "16a4dc87-780e-4b1b-9874-50a1a5e5ccd4.jsonl",
            "trace_sha256": "63fb382e73c0e48c0f355efa13fb33b8f6347b98f075684cd54458a5c4a310d0",
            "trace_bytes": 388833,
            "session_id": "16a4dc87-780e-4b1b-9874-50a1a5e5ccd4",
            "user_text_sha256": "13cfe2b00c327078b9eb257a4bd3d53d8517c523a74da37499f2a4874be23cd6",
            "user_text_bytes": 10959,
            "grading_sha256": "6e09f774ca94de47a4882612979661a6059cfe8bf37f5b92072fd3aeaf5efd0d",
            "reward": 0,
            "weighted": 70.0,
        },
        "tb-cargo-plan__r1": {
            "trace_file": "b70e9bf1-687b-47c7-b546-a5d120c69aeb.jsonl",
            "trace_sha256": "379b8b52ba904fe927f3585f346ea9ee303dd5d02e51a8f5cf0e3db48191d0c7",
            "trace_bytes": 518523,
            "session_id": "b70e9bf1-687b-47c7-b546-a5d120c69aeb",
            "user_text_sha256": "6c75e82b29f79b47c61f9ba4e7aaaa24040eaca461c1403242d2951609cb1c7a",
            "user_text_bytes": 9273,
            "grading_sha256": "0300bdfd4bc79bd208dc325b6af8531b2cb6b1ae41454054da2d71455c54d9b7",
            "reward": 0,
            "weighted": 0.0,
        },
        "tb-cargo-plan__r2": {
            "trace_file": "3a7c16b2-54e8-4080-b41c-82c21b95b354.jsonl",
            "trace_sha256": "4c0c9c83ea8e09d661efca137519e3bee5354dc8b87c328add2cb25cd2f603d9",
            "trace_bytes": 419694,
            "session_id": "3a7c16b2-54e8-4080-b41c-82c21b95b354",
            "user_text_sha256": "f07b3dffa44bc1f872f6085d9d7125a308cc09c2e9f09b18e6028fb71cbe3dfe",
            "user_text_bytes": 9273,
            "grading_sha256": "e9714e5ff2c0a033cd6cc8232cf2b23257e64c705f32ac72fd20d0c3a5b5b15a",
            "reward": 0,
            "weighted": 70.37,
        },
        "tb-cargo-plan__r3": {
            "trace_file": "61c4c10c-bcd6-41a2-a6bc-2d28e47ecd9c.jsonl",
            "trace_sha256": "7b2cb21a0c6f6a7555e4e17a22604159716b1531649c677638dc9349758c180b",
            "trace_bytes": 603325,
            "session_id": "61c4c10c-bcd6-41a2-a6bc-2d28e47ecd9c",
            "user_text_sha256": "056db0afc11f63bd418316827edbae8f8bd9a60873588d122f5d4471073f571d",
            "user_text_bytes": 9273,
            "grading_sha256": "5f74d744c08e6de778cce9b667cd3cb4321ebe8a6667c7fda0d52c5ab313add7",
            "reward": 0,
            "weighted": 70.37,
        },
    }
}

CONTENT_INDEPENDENCE_STATEMENT = (
    "内容无关边界声明：本结果仅登记计数、字节偏移、信封 span、字节数与 SHA256；"
    "不含任何信封或任务文本内容、差异字节值，不含私有档案绝对路径。"
)


class VerifyError(Exception):
    """fail-closed 条件失败；统一 exit 2。"""


def _fail(msg: str) -> None:
    raise VerifyError(msg)


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def strict_num_equal(archived, pinned) -> bool:
    """W3 硬等：类型与数值都必须一致（bool 视为非数值）。"""
    if isinstance(archived, bool) or isinstance(pinned, bool):
        return False
    if type(archived) is not type(pinned):
        return False
    return archived == pinned


# ---------------------------------------------------------------------------
# W1 纯函数（可独立单元测试）
# ---------------------------------------------------------------------------

def find_envelope_spans(data: bytes):
    """返回 (spans, open_without_close_count)。

    spans 为 [start, end) 列表（开标记起点 → 其后第一个闭合标记终点）。
    """
    spans = []
    unclosed = 0
    pos = 0
    while True:
        s = data.find(ENVELOPE_OPEN, pos)
        if s < 0:
            break
        e = data.find(ENVELOPE_CLOSE, s + len(ENVELOPE_OPEN))
        if e < 0:
            unclosed += 1
            break
        spans.append([s, e + len(ENVELOPE_CLOSE)])
        pos = e + len(ENVELOPE_CLOSE)
    return spans, unclosed


def diff_byte_offsets(a: bytes, b: bytes):
    """逐差异字节偏移（不含差异字节值）；长度不同时长出尾部一并计为差异。"""
    if a == b:
        return []
    n = min(len(a), len(b))
    offs = [i for i in range(n) if a[i] != b[i]]
    if len(a) != len(b):
        offs.extend(range(n, max(len(a), len(b))))
    return offs


def classify_w1_group(texts_by_rep):
    """对一组（3 rep 的 user text bytes）做 W1 分类（冻结定义 §2）。

    返回 dict：classification（w1_stable / w1_env_volatile / w1_task_text_drift /
    w1_no_envelope / None=结构登记）、spans_by_rep、pairs 等，不含任何文本内容。
    """
    reps = sorted(texts_by_rep.keys())
    spans_by_rep = {}
    unclosed_by_rep = {}
    missing_by_rep = []
    for rep in reps:
        spans, unclosed = find_envelope_spans(texts_by_rep[rep])
        spans_by_rep[rep] = spans
        if not spans:
            missing_by_rep.append(rep)
        if unclosed:
            unclosed_by_rep[rep] = unclosed

    base = {
        "spans_by_rep": {rep: [list(s) for s in spans_by_rep[rep]] for rep in reps},
        "envelope_span_cross_rep_equal": (
            len({json.dumps(spans_by_rep[rep], sort_keys=True) for rep in reps}) == 1
        ),
    }

    # 冻结定义顺序：全同 → w1_stable（信封定位仅在「有差异」时才参与）。
    pre_pairs = []
    all_equal = True
    for i in range(len(reps)):
        for j in range(i + 1, len(reps)):
            ra, rb = reps[i], reps[j]
            offs = diff_byte_offsets(texts_by_rep[ra], texts_by_rep[rb])
            all_equal = all_equal and (offs == [])
            pre_pairs.append([ra, rb, offs])
    if all_equal:
        base["classification"] = "w1_stable"
        base["pairs"] = [{
            "pair": [ra, rb], "byte_equal": True, "n_diff_offsets": 0,
            "diff_offsets": [], "n_offsets_outside_envelope": 0,
            "offsets_outside_envelope": [], "pair_result": "equal",
        } for ra, rb, _ in pre_pairs]
        return base
    # 有差异时：信封结构异常只登记、不归类（fail-closed；未闭合优先于缺失）。
    if unclosed_by_rep:
        base["classification"] = None
        base["classification_reason"] = "unclosed_envelope_marker"
        base["unclosed_in_reps"] = sorted(unclosed_by_rep.keys())
        base["pairs"] = []
        return base
    if missing_by_rep:
        base["classification"] = "w1_no_envelope"
        base["envelope_missing_in_reps"] = missing_by_rep
        base["pairs"] = []
        return base

    all_spans = [tuple(s) for rep in reps for s in spans_by_rep[rep]]
    pairs = []
    classifications = []
    for ra, rb, offs in pre_pairs:
        outside = [o for o in offs if not any(s <= o < e for (s, e) in all_spans)]
        if outside:
            pair_cls = "env_external_diff"
        else:
            pair_cls = "env_internal_diff"
        classifications.append(pair_cls)
        pairs.append({
            "pair": [ra, rb],
            "byte_equal": False,
            "n_diff_offsets": len(offs),
            "diff_offsets": offs,
            "n_offsets_outside_envelope": len(outside),
            "offsets_outside_envelope": outside,
            "pair_result": pair_cls,
        })

    if any(c == "env_external_diff" for c in classifications):
        base["classification"] = "w1_task_text_drift"
    else:
        base["classification"] = "w1_env_volatile"
    base["pairs"] = pairs
    return base


def decide_global_branch(group_classification):
    """反证分支（冻结 §3）：TASK-DRIFT > STABLE > ENV-VOLATILE，不确定则 None。"""
    vals = list(group_classification.values())
    if "w1_task_text_drift" in vals:
        return "B-W1-TASK-DRIFT", "任一组出现信封外差异（预注册 §3 最重发现分支）"
    if vals and all(v == "w1_stable" for v in vals):
        return "B-W1-STABLE", "两组全 stable"
    if vals and all(v == "w1_env_volatile" for v in vals):
        return "B-W1-ENV-VOLATILE", "两组差异全部限信封内"
    return None, "分支条件不满足（存在未归类/结构登记组），只登记不判定"


# ---------------------------------------------------------------------------
# W2 canonical 投影
# ---------------------------------------------------------------------------

def canonicalize_event(event):
    """顶层剔除逐会话易变外层键后 sort_keys 紧凑 JSON 的字节数（确定性）。"""
    trimmed = {k: v for k, v in event.items() if k not in set(STRIPPED_TOP_LEVEL_KEYS)}
    return json.dumps(trimmed, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


# ---------------------------------------------------------------------------
# 档案读取与校验
# ---------------------------------------------------------------------------

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


def run_verification(root: Path, archive_root: Path, pins=None) -> dict:
    if pins is None:
        pins = DEFAULT_PINS
    slot_pins = pins["slots"]

    # --- 0. 预注册 README 封印 -------------------------------------------
    prereg_path = root / PREREG_PATH_REL
    if not prereg_path.is_file():
        _fail("预注册 README 不存在: %s" % PREREG_PATH_REL)
    prereg_bytes = prereg_path.read_bytes()
    prereg_sha = sha256_of(prereg_bytes)
    if prereg_sha != PREREG_SHA256:
        _fail("预注册 README SHA256 不符: %s != %s" % (prereg_sha, PREREG_SHA256))

    # --- 1. 档案布局 -------------------------------------------------------
    runs_dir = archive_root / "runs"
    grading_root = archive_root / "evidence-tools" / "grading"
    if not runs_dir.is_dir():
        _fail("archive-root 下无 runs/（期望 WorkBuddy 复测档根，其下含 runs/ 与 evidence-tools/grading/）")
    if not grading_root.is_dir():
        _fail("archive-root 下无 evidence-tools/grading/")

    # --- 2/3. 逐槽 trace + user text（W1 输入侧原料）------------------------
    slot_results = {}
    for slot in SLOT_ORDER:
        pin = slot_pins.get(slot)
        if pin is None:
            _fail("槽缺少钉定常量: %s" % slot)
        slot_dir = runs_dir / slot
        trace_dir = slot_dir / "trace"
        if not trace_dir.is_dir():
            _fail("槽 trace/ 目录缺失: %s" % slot)
        jsonls = sorted(trace_dir.glob("*.jsonl"))
        if len(jsonls) != 1:
            _fail("槽 trace/ 下 session jsonl 数=%d（应为 1）: %s" % (len(jsonls), slot))
        trace_path = jsonls[0]
        raw, events = read_trace(trace_path)

        if trace_path.name != pin["trace_file"]:
            _fail("trace 文件名与钉定常量不符: %s: %s != %s"
                  % (slot, trace_path.name, pin["trace_file"]))
        if trace_path.stem != pin["session_id"]:
            _fail("trace 文件名 stem 与钉定 session_id 不符: %s" % slot)
        trace_sha = sha256_of(raw)
        if trace_sha != pin["trace_sha256"]:
            _fail("trace SHA256 不符: %s: %s != %s" % (slot, trace_sha, pin["trace_sha256"]))
        if len(raw) != pin["trace_bytes"]:
            _fail("trace 字节数不符: %s: %d != %d" % (slot, len(raw), pin["trace_bytes"]))

        counts = {t: 0 for t in sorted(KNOWN_EVENT_TYPES)}
        message_roles = {}
        canonical_bytes_by_type = {t: 0 for t in sorted(KNOWN_EVENT_TYPES)}
        user_events = []
        for lineno, ev in enumerate(events, 1):
            etype = ev.get("type")
            if etype not in KNOWN_EVENT_TYPES:
                _fail("未知事件型 %r（%s 行 %d）——结构异常" % (etype, slot, lineno))
            counts[etype] += 1
            canonical_bytes_by_type[etype] += len(canonicalize_event(ev))
            if "sessionId" in ev and ev["sessionId"] != pin["session_id"]:
                _fail("事件 sessionId 与钉定不符: %s 行 %d" % (slot, lineno))
            if etype == "message":
                role = ev.get("role")
                message_roles[role] = message_roles.get(role, 0) + 1
                if role == "user":
                    user_events.append((lineno, ev))

        if len(user_events) != 1:
            _fail("role=user 消息数=%d（应为恰 1）: %s" % (len(user_events), slot))
        user_text = extract_user_text_bytes(user_events[0][1], slot)
        ut_sha = sha256_of(user_text)
        if ut_sha != pin["user_text_sha256"]:
            _fail("user 文本 SHA256 不符: %s: %s != %s" % (slot, ut_sha, pin["user_text_sha256"]))
        if len(user_text) != pin["user_text_bytes"]:
            _fail("user 文本字节数不符: %s: %d != %d" % (slot, len(user_text), pin["user_text_bytes"]))

        slot_results[slot] = {
            "trace_file": trace_path.name,
            "trace_sha256": trace_sha,
            "trace_bytes": len(raw),
            "user_text_sha256": ut_sha,
            "user_text_bytes": len(user_text),
            "counts": counts,
            "message_roles": message_roles,
            "canonical_bytes_by_type": canonical_bytes_by_type,
            "canonical_total_bytes": sum(canonical_bytes_by_type.values()),
            "fc_fcr_count_equal": counts["function_call"] == counts["function_call_result"],
            "user_text": user_text,
        }

    # --- W1 ----------------------------------------------------------------
    w1_groups = {}
    for group, reps in sorted(GROUPS.items()):
        texts = {rep: slot_results["%s__%s" % (group, rep)]["user_text"] for rep in reps}
        w1_groups[group] = classify_w1_group(texts)
    for slot in SLOT_ORDER:
        del slot_results[slot]["user_text"]  # 原料不进结果（内容无关纪律）
    global_branch, branch_reason = decide_global_branch(
        {g: w1_groups[g]["classification"] for g in w1_groups})

    # --- W2 组内跨重复对比（描述性）-----------------------------------------
    w2_groups = {}
    for group, reps in sorted(GROUPS.items()):
        per_type = {}
        for etype in sorted(KNOWN_EVENT_TYPES):
            vals = [slot_results["%s__%s" % (group, rep)]["canonical_bytes_by_type"][etype]
                    for rep in reps]
            per_type[etype] = {
                "canonical_bytes": vals,
                "all_equal": len(set(vals)) == 1,
                "max_abs_delta": (max(vals) - min(vals)) if vals else 0,
            }
        w2_groups[group] = {
            "canonical_bytes_by_type_cross_rep": per_type,
            "counts_cross_rep_equal_note": "逐槽计数表见 w2.slots；本节仅登记，不设门",
        }

    # --- W3 ----------------------------------------------------------------
    w3_slots = {}
    for slot in SLOT_ORDER:
        pin = slot_pins[slot]
        gpath = grading_root / slot / "execution.json"
        if not gpath.is_file():
            _fail("grading execution.json 缺失: %s" % slot)
        graw = gpath.read_bytes()
        gsha = sha256_of(graw)
        if gsha != pin["grading_sha256"]:
            _fail("grading 文件 SHA256 与钉定不符: %s: %s != %s" % (slot, gsha, pin["grading_sha256"]))
        try:
            gobj = json.loads(graw.decode("utf-8"))
        except ValueError as exc:
            _fail("grading JSON 解析失败: %s: %s" % (slot, exc))
        res = gobj.get("result")
        if not isinstance(res, dict):
            _fail("grading 缺 result 对象: %s" % slot)
        case_name, _, rep_name = slot.rpartition("__")
        if gobj.get("case") != case_name:
            _fail("grading case 字段与槽名不符: %s" % slot)
        if gobj.get("rep") != int(rep_name[1:]):
            _fail("grading rep 字段与槽名不符: %s" % slot)
        if gobj.get("session_id") != pin["session_id"]:
            _fail("grading session_id 与钉定不符: %s" % slot)
        a_reward = res.get("reward")
        a_weighted = res.get("weighted")
        reward_ok = strict_num_equal(a_reward, pin["reward"])
        weighted_ok = strict_num_equal(a_weighted, pin["weighted"])
        if not reward_ok or not weighted_ok:
            _fail("W3 硬等失败: %s: archived=(%r, %r) pinned=(%r, %r)"
                  % (slot, a_reward, a_weighted, pin["reward"], pin["weighted"]))
        w3_slots[slot] = {
            "grading_file_rel": "evidence-tools/grading/%s/execution.json" % slot,
            "grading_sha256": gsha,
            "archived_reward": a_reward,
            "archived_weighted": a_weighted,
            "pinned_reward": pin["reward"],
            "pinned_weighted": pin["weighted"],
            "reward_hard_equal": reward_ok,
            "weighted_hard_equal": weighted_ok,
        }

    # --- baseline ------------------------------------------------------------
    baseline_commit = git_head(root)

    result = {
        "package": PACKAGE_NAME,
        "content_independence_statement": CONTENT_INDEPENDENCE_STATEMENT,
        "prereg": {
            "path_rel": str(PREREG_PATH_REL),
            "sha256": PREREG_SHA256,
            "sha256_match": True,
        },
        "baseline_commit": baseline_commit,
        "archive_layout": {
            "runs_rel": "runs/<slot>/trace/<session>.jsonl",
            "grading_rel": "evidence-tools/grading/<slot>/execution.json",
            "slots_expected": SLOT_ORDER,
        },
        "canonical_projection": {
            "stripped_top_level_keys": STRIPPED_TOP_LEVEL_KEYS,
            "stripped_keys_rationale": (
                "id/parentId/callId/messageId/sessionId=标识；timestamp=时间戳；"
                "cwd=逐会话本地路径；_meta=traceparent/baggage；__codebuddyLocal=本地标记；"
                "providerData=请求级 provider 元数据信封（conversationRequestId/"
                "messageId/traceId/stepSeq 等）；均属逐会话易变外层元数据"
            ),
            "json_options": CANONICAL_JSON_OPTS,
            "scope": "逐事件投影字节数，按事件型合计",
        },
        "public_page_source": {
            "path_rel": PUBLIC_PAGE_PATH_REL,
            "rows_reward_weighted_r1_r2_r3": PUBLIC_PAGE_ROWS,
        },
        "w1": {
            "definition_note": "信封=精确标记 <system-reminder data-role=\"user-context\"> 的 span；逐组三对两两逐字节比较",
            "groups": w1_groups,
            "global_branch": global_branch,
            "global_branch_reason": branch_reason,
        },
        "w2": {
            "descriptive_only": True,
            "slots": {
                slot: {
                    k: v for k, v in slot_results[slot].items()
                }
                for slot in SLOT_ORDER
            },
            "groups": w2_groups,
        },
        "w3": {
            "hard_equality": True,
            "slots": w3_slots,
            "all_passed": True,
        },
        "verdict": {
            "all_checks_passed": True,
            "w1_global_branch": global_branch,
        },
    }
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def render_summary(result: dict) -> str:
    lines = []
    lines.append("== %s verify ==" % result["package"])
    lines.append("prereg README sha256: OK (%s)" % result["prereg"]["sha256"])
    lines.append("baseline_commit: %s" % result["baseline_commit"])
    lines.append("archive layout: OK (%d slots, 1 trace jsonl each)" % len(SLOT_ORDER))
    lines.append("")
    lines.append("W1 global branch: %s" % result["w1"]["global_branch"])
    for group in sorted(result["w1"]["groups"].keys()):
        g = result["w1"]["groups"][group]
        lines.append("  group %s: %s" % (group, g["classification"]))
        for pair in g.get("pairs", []):
            lines.append(
                "    pair %s~%s: diff_offsets=%d outside_envelope=%d (%s)"
                % (pair["pair"][0], pair["pair"][1], pair["n_diff_offsets"],
                   pair["n_offsets_outside_envelope"], pair["pair_result"]))
    lines.append("")
    lines.append("W2 (descriptive, no gate):")
    for slot in SLOT_ORDER:
        s = result["w2"]["slots"][slot]
        c = s["counts"]
        roles = s["message_roles"]
        lines.append(
            "  %s: fc=%d fcr=%d reasoning=%d msg(u=%d,a=%d) fhs=%d ai-title=%d session-meta=%d canon_total=%d fc==fcr:%s"
            % (slot, c["function_call"], c["function_call_result"], c["reasoning"],
               roles.get("user", 0), roles.get("assistant", 0),
               c["file-history-snapshot"], c["ai-title"], c["session-meta"],
               s["canonical_total_bytes"], s["fc_fcr_count_equal"]))
    lines.append("")
    lines.append("W3 hard-equal vs published constants: %d/%d OK"
                 % (len(result["w3"]["slots"]), len(SLOT_ORDER)))
    for slot in SLOT_ORDER:
        w = result["w3"]["slots"][slot]
        lines.append("  %s: reward %r==%r weighted %r==%r OK"
                     % (slot, w["archived_reward"], w["pinned_reward"],
                        w["archived_weighted"], w["pinned_weighted"]))
    lines.append("")
    lines.append("RESULT: PASS")
    return "\n".join(lines) + "\n"


def main(argv=None, pins=None) -> int:
    """pins 仅供测试注入合成常量；CLI 路径恒用冻结的 DEFAULT_PINS。"""
    parser = argparse.ArgumentParser(
        description="WB重复槽输入与交互量结构-2026-11-16 验证器（fail-closed）")
    parser.add_argument("--root", required=True, help="公开仓库根目录")
    parser.add_argument("--archive-root", required=True, dest="archive_root",
                        help="WorkBuddy 复测档根（其下含 runs/ 与 evidence-tools/grading/）")
    parser.add_argument("--output", default=None,
                        help="独占创建写完整 result.json（已存在则拒改 exit 2）")
    args = parser.parse_args(argv)

    out_path = Path(args.output) if args.output else None
    if out_path is not None and out_path.exists():
        sys.stderr.write("REFUSE: --output 已存在，拒改: %s\n" % out_path.name)
        return 2

    root = Path(args.root)
    archive_root = Path(args.archive_root)
    try:
        result = run_verification(root, archive_root, pins=pins)
    except VerifyError as exc:
        sys.stderr.write("FAIL(exit 2): %s\n" % exc)
        return 2

    summary = render_summary(result)
    sys.stdout.write(summary)

    if out_path is not None:
        payload = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        try:
            with open(out_path, "x", encoding="utf-8", newline="\n") as fh:
                fh.write(payload)
        except OSError as exc:
            sys.stderr.write("FAIL(exit 2): --output 写入失败: %s\n" % exc)
            return 2
        sys.stdout.write("result.json written: %s\n" % out_path.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
