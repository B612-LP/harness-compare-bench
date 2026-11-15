#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""豆包输出侧结构分解 verify.py（预注册：豆包输出侧结构分解-2026-11-16，schema doubao-struct-v1）

输出侧结构分解（早期分岔 vs 后期收敛）：豆包 bw-retest tb-cargo-plan 三重复。

用法：
    python3 verify.py --root <repo根> --archive-root <bw-retest/doubao 根> [--output <path>]

- --root：公开仓库根（定位预注册 README 与硬等参照 复测登记-r1109.md，读 baseline commit）。
- --archive-root：档案根，语义 = .../bw-retest/doubao；其下
  runs/tb-cargo-plan__r{1,2,3}/trace/session/agents/*/system/trajectory.jsonl（每槽恰一，多则 exit2）。
- --output：独占创建（已存在即拒绝，exit2）；仅全部检查通过（exit0）时写出。

内容无关（预注册 §2）：function.arguments 与 tool content 值一律不读取落盘，只计字节数；
工具名与 'T' 为可登记标识符（同 bird §4.34 先例）。stdout/result 不含绝对路径与时间戳，
保证双档（同一档案的两份副本）stdout 逐字节一致、CLI 重跑逐字节一致。

fail-closed：任何校验失败（缺文件、多轨迹、schema 违例、硬等漂移/解析失败、数据不足）
打印原因到 stderr 并 exit 2，不写 --output。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

SCHEMA = "doubao-struct-v1"
EXPECTED_PREREG_SHA256 = "aabe1f09ab2710e6a95d7efa4e9a497c3ccc40ba09df78b4e24075a0e187ec5e"
PREREG_PACKAGE_REL = os.path.join("4-打分细则", "豆包输出侧结构分解-2026-11-16", "README.md")
HARDEQUAL_DOC_REL = os.path.join("4-打分细则", "预注册复测选题-2026-11-08", "复测登记-r1109.md")
SLOTS = ("r1", "r2", "r3")
RUN_PREFIX = "tb-cargo-plan__"
TRAJ_GLOB = os.path.join("runs", RUN_PREFIX + "{slot}", "trace", "session", "agents", "*", "system", "trajectory.jsonl")

EXPECTED_REWARD = [Decimal("0"), Decimal("0"), Decimal("0")]
EXPECTED_WEIGHTED = [Decimal("81.48"), Decimal("70.37"), Decimal("81.48")]

EXIT_OK = 0
EXIT_FAIL = 2

CONTENT_AGNOSTIC_DECLARATION = (
    "内容无关验证：tool_call function.arguments 与 tool/assistant content 的值一律不读取、"
    "不落盘；stdout 与 result 仅含计数、字节数与可登记标识符（工具名、'T'、槽位名、"
    "<agent> 占位）。字节口径逐项声明：tool_call function canonical JSON 字节 = "
    "json.dumps(function, sort_keys=True, ensure_ascii=False, separators=(',',':')) 的 UTF-8 字节数；"
    "tool_result content 字节 = str 按 UTF-8 字节数，非 str 按 canonical JSON 字节并登记类型。"
)


class VerifyError(Exception):
    """fail-closed：携带面向 stderr 的原因，统一 exit 2。"""


# ---------------------------------------------------------------- 单元函数 --

def canonical_json_bytes(obj) -> int:
    """canonical JSON 字节：sort_keys=True, ensure_ascii=False, separators=(',',':')。"""
    return len(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                          separators=(",", ":")).encode("utf-8"))


def content_bytes(value) -> tuple[int, str]:
    """tool_result content 字节：str 按 UTF-8；非 str 按 canonical JSON，返回 (字节数, 类型名)。"""
    if isinstance(value, str):
        return len(value.encode("utf-8")), "str"
    return canonical_json_bytes(value), type(value).__name__


def lcp_len(a: list, b: list) -> int:
    """两序列最长公共前缀长度。"""
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def three_way_lcp(seqs: list[list]) -> int:
    """三方 LCP：逐位置三方相等的最长前缀。"""
    if not seqs:
        return 0
    n = min(len(s) for s in seqs)
    i = 0
    while i < n and seqs[0][i] == seqs[1][i] == seqs[2][i]:
        i += 1
    return i


def classify(three_way: int, min_len: int) -> str:
    """预注册 §3 分支：三方 LCP < min(序列长)/2 ⇒ H-EARLY-DIVERGENCE；≥ ⇒ H-LATE-CONVERGENCE。"""
    return "H-EARLY-DIVERGENCE" if three_way < min_len / 2 else "H-LATE-CONVERGENCE"


def parse_hard_equal(doc_text: str) -> dict:
    """从 复测登记-r1109.md §③ 解析 豆包×tb 行的 reward / weighted。

    解析失败或值漂移（≠ 预注册期望）抛 VerifyError。只解析数字 token，不读其他内容值。
    """
    m = re.search(r"^### ③[^\n]*$", doc_text, flags=re.M)
    if not m:
        raise VerifyError("硬等参照解析失败：未找到 §③ 标题（### ③）")
    section = doc_text[m.end():]
    nxt = re.search(r"^#{2,3}[^\n]*$", section, flags=re.M)  # 截到下一个标题，不读入后续章节
    cut = nxt.start() if nxt else len(section)
    section = section[:cut]
    lines = [ln for ln in section.splitlines() if re.search(r"豆包\s*×\s*tb", ln)]
    if len(lines) != 1:
        raise VerifyError(f"硬等参照解析失败：§③ 内 豆包×tb 行应有恰 1 条，实得 {len(lines)}")
    line = lines[0]
    m_rw = re.search(r"reward\s*(?:\*\*)?\[([^\]]+)\]", line)
    m_wd = re.search(r"weighted\s*\[([^\]]+)\]", line)
    if not m_rw or not m_wd:
        raise VerifyError("硬等参照解析失败：豆包×tb 行缺 reward/weighted 数组")
    def tokens(raw: str) -> list[str]:
        parts = [p.strip() for p in raw.split(",")]
        if len(parts) != 3 or any(not p for p in parts):
            raise VerifyError(f"硬等参照解析失败：数组应为 3 个数值，实得 {raw!r}")
        return parts
    def decimals(parts: list[str]) -> list[Decimal]:
        try:
            return [Decimal(p) for p in parts]
        except InvalidOperation:
            raise VerifyError(f"硬等参照解析失败：非数值 token {parts!r}")
    reward_t, weighted_t = tokens(m_rw.group(1)), tokens(m_wd.group(1))
    reward, weighted = decimals(reward_t), decimals(weighted_t)
    if reward != EXPECTED_REWARD:
        raise VerifyError(
            f"硬等漂移：reward 解析 {reward_t} ≠ 期望 [0, 0, 0]")
    if weighted != EXPECTED_WEIGHTED:
        raise VerifyError(
            f"硬等漂移：weighted 解析 {weighted_t} ≠ 期望 [81.48, 70.37, 81.48]")
    return {
        "source": "复测登记-r1109.md §③ 豆包×tb 行",
        "reward": reward_t,
        "weighted": weighted_t,
        "expected_reward": ["0", "0", "0"],
        "expected_weighted": ["81.48", "70.37", "81.48"],
        "passed": True,
    }


# ---------------------------------------------------------------- 轨迹读取 --

def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise VerifyError(msg)


def load_trajectory(path: Path, slot: str, agent_placeholder: str) -> dict:
    """读取单个 trajectory.jsonl，做 fail-closed schema 校验并登记结构统计（内容无关）。"""
    try:
        raw = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise VerifyError(f"{slot}: trajectory 不可读/非 UTF-8：{e}")
    n_assistant = n_tool = n_calls = n_pure = 0
    result_bytes = 0
    content_types: dict[str, int] = {}
    call_counts: dict[str, int] = {}
    func_bytes: dict[str, int] = {}
    sequence: list[str] = []
    for lineno, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            raise VerifyError(f"{slot}: 第 {lineno} 行非合法 JSON：{e}")
        _require(isinstance(row, dict), f"{slot}: 第 {lineno} 行非对象")
        role = row.get("role")
        keys = set(row.keys())
        if role == "assistant":
            n_assistant += 1
            _require(keys <= {"role", "tool_calls", "content"},
                     f"{slot}: 第 {lineno} 行 assistant 出现未登记键 {sorted(keys - {'role', 'tool_calls', 'content'})}")
            tcs = row.get("tool_calls")
            if tcs is None:
                n_pure += 1  # 纯 assistant 轮：无 tool_calls 的 assistant 行（值不读取）
                continue
            _require(isinstance(tcs, list), f"{slot}: 第 {lineno} 行 tool_calls 非数组")
            for ci, tc in enumerate(tcs):
                _require(isinstance(tc, dict) and set(tc.keys()) == {"function", "id", "type"},
                         f"{slot}: 第 {lineno} 行第 {ci} 个 tool_call 键应为 {{function,id,type}}")
                fn = tc["function"]
                _require(isinstance(fn, dict) and set(fn.keys()) <= {"name", "arguments"} and "name" in fn
                         and isinstance(fn.get("name"), str),
                         f"{slot}: 第 {lineno} 行第 {ci} 个 function 键应为 {{name[,arguments]}} 且 name 为字符串")
                name = fn["name"]
                n_calls += 1
                call_counts[name] = call_counts.get(name, 0) + 1
                func_bytes[name] = func_bytes.get(name, 0) + canonical_json_bytes(fn)
                sequence.append(name)  # assistant 行按 tool_calls 顺序展开工具名
        elif role == "tool":
            n_tool += 1
            _require(keys == {"role", "content", "tool_call_id"},
                     f"{slot}: 第 {lineno} 行 tool 键应为 {{role,content,tool_call_id}}，实得 {sorted(keys)}")
            nb, tname = content_bytes(row["content"])
            result_bytes += nb
            content_types[tname] = content_types.get(tname, 0) + 1
            sequence.append("T")  # tool 行记 'T'
        else:
            raise VerifyError(f"{slot}: 第 {lineno} 行出现未登记 role={role!r}")
    return {
        "trajectory": f"runs/{RUN_PREFIX}{slot}/trace/session/agents/{agent_placeholder}/system/trajectory.jsonl",
        "n_lines": n_assistant + n_tool,
        "n_assistant_lines": n_assistant,
        "n_tool_lines": n_tool,
        "n_tool_calls": n_calls,
        "n_pure_assistant_turns": n_pure,
        "tool_call_counts": dict(sorted(call_counts.items())),
        "function_canonical_bytes_by_name": dict(sorted(func_bytes.items())),
        "function_canonical_bytes_total": sum(func_bytes.values()),
        "tool_result_content_bytes_total": result_bytes,
        "tool_result_content_types": dict(sorted(content_types.items())),
        "tool_name_sequence": sequence,
    }


def load_archive(archive_root: Path) -> dict:
    """逐槽加载；每槽恰一 trajectory，多则 exit2；出现预注册外槽位亦 exit2。"""
    runs_dir = archive_root / "runs"
    _require(runs_dir.is_dir(), f"档案根缺 runs/ 目录：{archive_root.name}")
    observed = sorted(p.name for p in runs_dir.iterdir() if p.is_dir() and p.name.startswith(RUN_PREFIX))
    expected = sorted(RUN_PREFIX + s for s in SLOTS)
    _require(observed == expected,
             f"槽位与预注册不符：期望 {expected}，实得 {observed or '（无）'}")
    reps: dict[str, dict] = {}
    for slot in SLOTS:
        pattern = TRAJ_GLOB.format(slot=slot)
        hits = sorted(archive_root.glob(pattern))
        _require(len(hits) == 1,
                 f"{slot}: 每槽应恰 1 个 trajectory.jsonl，实得 {len(hits)}")
        reps[slot] = load_trajectory(hits[0], slot, "<agent>")
    return reps


# ---------------------------------------------------------------- 仓库侧 --

def verify_prereg_readme(root: Path) -> str:
    """校验包内冻结 README SHA256；返回（必等于冻结常量的）sha256。"""
    p = root / PREREG_PACKAGE_REL
    if not p.is_file():
        raise VerifyError(f"预注册 README 缺失：{PREREG_PACKAGE_REL}")
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    if digest != EXPECTED_PREREG_SHA256:
        raise VerifyError(f"预注册 README SHA256 防篡改失败：{digest} ≠ {EXPECTED_PREREG_SHA256}")
    return digest


def hard_equal_doc_path(root: Path) -> Path:
    p = root / HARDEQUAL_DOC_REL
    _require(p.is_file(), f"硬等参照缺失：{HARDEQUAL_DOC_REL}")
    return p


def baseline_commit(root: Path) -> str:
    """只读查询 --root 的 HEAD commit（不做任何写/git 变更操作）。失败 exit2。"""
    try:
        out = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                             capture_output=True, check=True, timeout=30)
        return out.stdout.decode("ascii").strip()
    except (subprocess.SubprocessError, OSError) as e:
        raise VerifyError(f"baseline commit 读取失败（--root 需为 git 仓库）：{e}")


# ---------------------------------------------------------------- 主流程 --

def run_verification(root: Path, archive_root: Path) -> dict:
    """全部校验；任何失败抛 VerifyError（调用方 exit2，不写 output）。"""
    prereg_sha = verify_prereg_readme(root)
    with open(hard_equal_doc_path(root), "r", encoding="utf-8") as fh:
        hard_equal = parse_hard_equal(fh.read())
    reps = load_archive(archive_root)

    seqs = {s: reps[s]["tool_name_sequence"] for s in SLOTS}
    min_len = min(len(seqs[s]) for s in SLOTS)
    pairwise = {
        "r1-r2": lcp_len(seqs["r1"], seqs["r2"]),
        "r1-r3": lcp_len(seqs["r1"], seqs["r3"]),
        "r2-r3": lcp_len(seqs["r2"], seqs["r3"]),
    }
    three_way = three_way_lcp([seqs[s] for s in SLOTS])
    div_idx = three_way  # 首分岔 index = 三方 LCP（该位置起三方不再全等）
    _require(min_len > 0, "数据不足：存在空工具名序列，无法分类")
    # 某 rep 序列恰终止于 LCP 边界（是其余序列的前缀）时，该侧无分岔元素，
    # 以结构哨兵 <END> 登记（标识符层面，不读值）。
    divergence_elements = {s: (seqs[s][div_idx] if div_idx < len(seqs[s]) else "<END>")
                           for s in SLOTS}
    verdict = classify(three_way, min_len)

    return {
        "schema": SCHEMA,
        "prereg_sha256": prereg_sha,
        "prereg_package": PREREG_PACKAGE_REL,
        "baseline_commit": baseline_commit(root),
        "task": {"product": "doubao", "run": "bw-retest", "task_id": "tb-cargo-plan",
                 "reps": list(SLOTS)},
        "content_agnostic": {
            "declaration": CONTENT_AGNOSTIC_DECLARATION,
            "registered_identifiers": ["tool names", "'T' markers", "slot names", "<agent> placeholder"],
            "excluded_values": ["tool_call function.arguments", "tool content", "assistant content"],
        },
        "units": {
            "行数/assistant/tool/tool_call/纯assistant轮/逐工具计数": "计数（条/个）",
            "function_canonical_bytes_*": "canonical JSON UTF-8 字节（sort_keys=True, ensure_ascii=False, separators=(',',':')）",
            "tool_result_content_bytes_*": "str 按 UTF-8 字节；非 str 按 canonical JSON 字节并登记类型名",
            "序列": "元素 = 工具名标识符或 'T'（tool 行）；分母 = 各 rep 序列元素个数",
        },
        "per_rep": {s: reps[s] for s in SLOTS},
        "sequence_comparison": {
            "sequence_lengths": {s: len(seqs[s]) for s in SLOTS},
            "pairwise_lcp": pairwise,
            "three_way_lcp": three_way,
            "first_divergence_index": div_idx,
            "first_divergence_elements": divergence_elements,
            "min_sequence_length": min_len,
            "threshold_min_half": min_len / 2,
            "rule": "三方 LCP < min(序列长)/2 ⇒ H-EARLY-DIVERGENCE；≥ ⇒ H-LATE-CONVERGENCE",
        },
        "hard_equal": hard_equal,
        "branch": {
            "verdict": verdict,
            "isomorphism_note": (
                "与 bird §4.34 同判据形式的同型性观察（如为 EARLY-DIVERGENCE）：非因果、"
                "非跨产品规律；n=3 单 case 单产品描述性登记。"),
            "indeterminate_conditions": "硬等失败或数据不足 ⇒ exit2 / H-INDETERMINATE（本结果未触发）",
        },
        "notes": {
            "app_version_facts_not_judged": "豆包 app 2.34.12→2.35.19、DB tb r1 到达 2400s driver 超时帽（复测登记-r1109 §环境与披露）：仅注记，不参与判定。",
            "interpretation_boundary": "不外推产品行为规律、不横比 B 组分数面、不构成判卷差异来源分析（checker 未变）；正式 25 行与 bw-retest 判分不变。",
        },
    }


def render_stdout(result: dict) -> str:
    """确定性 stdout 摘要：无路径、无时间戳，双档逐字节一致。"""
    L: list[str] = []
    L.append(f"== 豆包输出侧结构分解 verify（{SCHEMA}）==")
    L.append(f"prereg_sha256: {result['prereg_sha256']}")
    L.append(f"baseline_commit: {result['baseline_commit']}")
    t = result["task"]
    L.append(f"task: {t['product']} {t['run']} {t['task_id']} reps={','.join(t['reps'])}")
    for s in SLOTS:
        r = result["per_rep"][s]
        L.append(
            f"[{s}] lines={r['n_lines']} assistant={r['n_assistant_lines']} tool={r['n_tool_lines']} "
            f"tool_calls={r['n_tool_calls']} pure_assistant={r['n_pure_assistant_turns']} "
            f"result_content_bytes={r['tool_result_content_bytes_total']} "
            f"content_types={json.dumps(r['tool_result_content_types'], sort_keys=True, ensure_ascii=False)}")
        L.append(f"[{s}] tool_calls_by_name: "
                 f"{json.dumps(r['tool_call_counts'], sort_keys=True, ensure_ascii=False)}")
        L.append(f"[{s}] function_canonical_bytes_by_name: "
                 f"{json.dumps(r['function_canonical_bytes_by_name'], sort_keys=True, ensure_ascii=False)} "
                 f"total={r['function_canonical_bytes_total']}")
        L.append(f"[{s}] sequence_len={len(r['tool_name_sequence'])}")
    for s in SLOTS:
        L.append(f"sequence_{s}: "
                 f"{json.dumps(result['per_rep'][s]['tool_name_sequence'], ensure_ascii=False)}")
    sc = result["sequence_comparison"]
    L.append(f"pairwise_lcp: {json.dumps(sc['pairwise_lcp'], sort_keys=True)}")
    L.append(f"three_way_lcp: {sc['three_way_lcp']} first_divergence_index: {sc['first_divergence_index']} "
             f"elements_at_divergence: {json.dumps(sc['first_divergence_elements'], sort_keys=True, ensure_ascii=False)}")
    L.append(f"min_sequence_length: {sc['min_sequence_length']} threshold(min/2): {sc['threshold_min_half']}")
    he = result["hard_equal"]
    L.append(f"hard_equal: reward={json.dumps(he['reward'])} weighted={json.dumps(he['weighted'])} "
             f"source={he['source']} PASSED")
    b = result["branch"]
    L.append(f"branch: {b['verdict']} "
             f"(three_way_lcp {sc['three_way_lcp']} {'<' if b['verdict'] == 'H-EARLY-DIVERGENCE' else '≥'} {sc['threshold_min_half']})")
    L.append("content_agnostic: arguments/content 值未读取未落盘，仅字节计数；工具名/'T'=标识符")
    L.append("verdict: OK")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="豆包输出侧结构分解（bw-retest tb-cargo-plan 三重复）预注册验证")
    ap.add_argument("--root", required=True, help="公开仓库根（预注册 README 与硬等参照所在）")
    ap.add_argument("--archive-root", required=True,
                    help="档案根，语义 = bw-retest/doubao（其下 runs/tb-cargo-plan__r{1,2,3}/...）")
    ap.add_argument("--output", default=None,
                    help="结果 JSON 独占创建路径；已存在则拒绝（exit2）；仅 exit0 时写出")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    archive_root = Path(args.archive_root).resolve()
    try:
        _require(root.is_dir(), f"--root 不是目录：{args.root}")
        _require(archive_root.is_dir(), f"--archive-root 不是目录：{args.archive_root}")
        result = run_verification(root, archive_root)
    except VerifyError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return EXIT_FAIL
    out_text = render_stdout(result)
    sys.stdout.buffer.write(out_text.encode("utf-8"))
    sys.stdout.buffer.flush()
    if args.output is not None:
        out_path = Path(args.output)
        if out_path.exists():
            print(f"FAIL: --output 已存在，拒绝覆盖（独占创建）：{args.output}", file=sys.stderr)
            return EXIT_FAIL
        try:
            fd = os.open(str(out_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2) + "\n")
        except OSError as e:
            print(f"FAIL: --output 写出失败：{e}", file=sys.stderr)
            return EXIT_FAIL
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
