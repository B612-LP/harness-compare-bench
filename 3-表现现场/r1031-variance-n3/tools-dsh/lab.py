#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r1031-variance-n3：n=3 可重复性批（包A）DSH 侧运行器。

r1030-formal-a1 tools/lab.py 的最小适配：仅跑 DSH × 5 题 × rep{2,3}（共 10 场），
调用方式与 r1030 完全一致（`dsh bench-cli --json -`，prompt 走 stdin，cwd=工作区）。
- 工作区 ~/bench-workspaces/r1031/dsh/<rep>/<case>/，只含 inputs + TASK.md；
- event id `var-n3-dsh-<case>-r<rep>`，run_id `r1031-dsh-<case>-r<rep>`；
- 每场 meta 记 preregistration_commit=be39fc2（预注册封印提交）；
- 随批工程项 a：stdout 归档去除 8192 截断——dsh-headless `--json` 投影的
  maxStringBytes=8192 / maxEventBytes=32768 为代码硬编码（0.2.0-rc.2 无旗标/环境变量
  可覆盖），故 raw CLI stdout 原样落盘（agent.jsonl，meta 记字节数），另从耐久会话
  轨迹（session.v4.jsonl.zstd，无损 commit 事件源）按同一投影语义重建**无截断完整流**
  落盘（agent.jsonl.full），meta 分别记字节数与重建方法；
- 随批工程项 b：逐调用 usage（含 cache_read / cache_creation）入库——从会话轨迹
  assistant/message 的 usage（与投影 step_end 交叉核对）提取 per_call 数组与总量进 meta；
- 判卷一律 freeze-20261029-v2 冻结 checker（preflight 校验 checker 哈希 = v2 config 快照）；
- 纪律：无重试（运行级失败记 selection=null 诊断并继续）；仅传输层错误（429/断连）
  指数退避至多 3 次，属同一逻辑运行，逐次记录 meta.transport_retries。

用法：
    python3 tools/lab.py preflight                       # 无模型接口预检
    python3 tools/lab.py prepare <case> <rep>
    python3 tools/lab.py run <case> <rep>                # 跑 + 判分 + 归档
    python3 tools/lab.py judge <case> <rep>
    python3 tools/lab.py integrity <case> <rep>          # 只读复扫归档产物
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
BATCH = Path(__file__).resolve().parents[1]
OUT_ROOT = BATCH / "dsh"          # 本执行者写界：r1031-variance-n3/dsh/**
RUNS = OUT_ROOT / "runs"
CASE_ROOT = REPO / "2-用例"
V2 = REPO / "4-打分细则" / "可信冻结-2026-10-29-v2"
WS_ROOT = Path.home() / "bench-workspaces" / "r1031" / "dsh"
DSH_PROFILE = "bench-cli"
MODEL = "deepseek-flash"
EFFORT = "low"
RULE = "freeze-20261029-v2"
PREREG_COMMIT = "be39fc2"
BATCH_NAME = "r1031-variance-n3"
PRODUCT = "dsh"
REPS = ("2", "3")
CASES = ("bird-ca-schools-15", "dabstep-payments-10", "exercism-py-6", "lcb-recent-hard-4", "tb-cargo-plan")

TOOL_FACTS = {
    "dsh": {
        "tools": ["builtin shell/read/write 等 bench-cli 基础工具（tool-web/tool-skill/skill-filesystem disabled）"],
        "permissions": "permission preset danger-full-access（approval never，bench-cli cordis.patch.yml）",
        "skills": "off（tool-skill 与 skill-filesystem 均 disabled）",
        "route": {"host": "api.deepseek.com", "provider_id": "deepseek-official", "wire_protocol": "anthropic-messages",
                  "endpoint": None},
    },
}

# freeze-20261029-v2 config.json 的守卫集与全题分母（判分收据用）
GUARDS = {
    "bird-ca-schools-15": {"input_integrity", "answers_file", "answers_schema", "answers_coverage"},
    "dabstep-payments-10": {"answers_format", "input_integrity"},
    "exercism-py-6": {"input_integrity"},
    "lcb-recent-hard-4": {"input_integrity"},
    "tb-cargo-plan": {"input_integrity", "code_rerun", "plan_structure"},
}
TOTALS = dict(zip(CASES, (15, 10, 6, 4, 27)))

DISCIPLINE = """
---
## 工作纪律（评测方要求，必须遵守）

1. 只在当前工作目录内读写：产物写在目录根下；题目明确允许修改的代码除外。
2. 不要访问这个目录之外的任何本机路径——不要 `ls` / `find` / `grep` 上级目录、家目录或其它项目目录。
3. 不要寻找判分器、参考答案、测试文件或其它用例目录；请按题面自行推导。
4. 不要联网搜索题解、原文或答案；本场按离线环境对待。
5. 需要假设时按题面合理假设，并在最终答复里简短说明。

完成后直接结束，不需要额外解释。
"""

INTEGRITY_PATTERNS = ["2-用例", "truth.json", "checker.py", "reference/", "solution/", "../",
                      "~/Documents", "harness-compare-bench"]

# 传输层错误分类（429/断连等；命中才允许指数退避重试，≤3 次，同一逻辑运行）
TRANSPORT_PATTERNS = [
    "429", "rate limit", "rate_limit", "ratelimit", "too many requests",
    "econnreset", "econnrefused", "etimedout", "epipe", "eai_again", "enotfound", "econnaborted",
    "socket hang up", "connection reset", "connection refused", "connection terminated",
    "network error", "fetch failed", "request timed out", "timed out",
    "502 bad gateway", "503 service unavailable", "504 gateway timeout", "overloaded_error", "overloaded",
]


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def event_id(case: str, rep: str) -> str:
    return "var-n3-dsh-%s-r%s" % (case, rep)


def run_id(case: str, rep: str) -> str:
    return "r1031-dsh-%s-r%s" % (case, rep)


def ws_dir(case: str, rep: str) -> Path:
    return WS_ROOT / rep / case


def run_ev(case: str, rep: str) -> Path:
    return RUNS / ("dsh__%s__r%s" % (case, rep))


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_api_key() -> str:
    text = (Path.home() / ".dsh" / ".credentials.yaml").read_text(encoding="utf-8")
    m = re.search(r"^refs:\n((?:  .*\n)+)", text, re.M)
    if not m:
        raise SystemExit("credentials: refs 段未找到")
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        if k.strip() == "DEEPSEEK_API_KEY":
            return v.strip()
    raise SystemExit("credentials: DEEPSEEK_API_KEY 未找到")


def cli_version() -> str:
    out = subprocess.run(["dsh", "--version"], capture_output=True, text=True, timeout=60)
    return (out.stdout or out.stderr).strip().splitlines()[0].strip()


def build_task(case: str, ws: Path) -> str:
    body = (CASE_ROOT / case / "instruction.md").read_text(encoding="utf-8").rstrip()
    label = "DSH CLI"
    head = (
        "# 本场任务：%s（%s）\n\n"
        "**你的工作目录（绝对路径）：`%s`**\n\n"
        "请在这个目录里工作：输入都在该目录的 `inputs/` 下，产物按题目要求写到该目录里"
        "（题目里的相对路径都相对这个目录）。除题目明确要求修改的代码外，不要改动 `inputs/` 下的文件。\n\n"
        "---\n\n" % (case, label, ws)
    )
    return head + body + "\n" + DISCIPLINE


def check_isolation(ws: Path) -> dict:
    """工作区隔离断言：仓库外、无 truth/solution/checker 泄漏。"""
    problems = []
    if not str(ws).startswith(str(Path.home() / "bench-workspaces")):
        problems.append("workspace-not-under-bench-workspaces")
    if str(REPO) in str(ws):
        problems.append("workspace-inside-repo")
    for banned in ("truth.json", "checker.py"):
        if list(ws.rglob(banned)):
            problems.append("leak:" + banned)
    if list(ws.rglob("solution")):
        problems.append("leak:solution/")
    return {"ok": not problems, "problems": problems}


def v2_checker_hashes() -> dict:
    cfg = json.loads((V2 / "config.json").read_text(encoding="utf-8"))
    assert cfg["rule_version"] == RULE
    return {c: cfg["case_snapshots"][c]["checker.py"] for c in CASES}


def cmd_preflight() -> int:
    """零模型调用的接口预检：版本、profile 哈希、冻结 checker 哈希、隔离、判分器可执行。"""
    receipt = {"kind": "interface_preflight", "model_calls": 0, "at": now_iso(), "rule": RULE,
               "batch": BATCH_NAME, "preregistration_commit": PREREG_COMMIT,
               "invocation": "dsh %s --json -（prompt 经 stdin，cwd=工作区；与 r1030 一致）" % DSH_PROFILE}
    receipt["dsh"] = {"version": cli_version()}
    prof = Path.home() / ".dsh" / "profiles" / DSH_PROFILE
    receipt["dsh"]["profile"] = str(prof)
    receipt["dsh"]["profile_sha256"] = {f: sha(prof / f) for f in ("cordis.patch.yml", "package.json")}
    # 冻结 checker 哈希与 v2 config 快照一致性
    want = v2_checker_hashes()
    have = {c: sha(CASE_ROOT / c / "checker.py") for c in CASES}
    receipt["frozen_checker_match"] = {c: (want[c] == have[c]) for c in CASES}
    # 隔离演练
    ws = WS_ROOT / "_isolation-probe"
    if ws.exists():
        shutil.rmtree(ws)
    ws.mkdir(parents=True)
    (ws / "inputs").mkdir()
    (ws / "inputs" / "dummy.txt").write_text("probe\n", encoding="utf-8")
    receipt["isolation_probe"] = check_isolation(ws)
    shutil.rmtree(ws)
    # 判分器可执行性冒烟（--help；正式 selftest 由独立收据登记）
    smoke = {}
    for case in CASES:
        p = subprocess.run([sys.executable, str(CASE_ROOT / case / "checker.py"), "--help"],
                           capture_output=True, text=True, timeout=120)
        smoke[case] = {"exit": p.returncode}
    receipt["checker_smoke"] = smoke
    receipt["ok"] = (receipt["isolation_probe"]["ok"]
                     and all(receipt["frozen_checker_match"].values())
                     and all(v["exit"] in (0, 2) for v in smoke.values()))
    out = OUT_ROOT / "preflight" / "cli-preflight.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": receipt["ok"], "receipt": str(out)}, ensure_ascii=False))
    return 0 if receipt["ok"] else 2


def cmd_prepare(case: str, rep: str) -> int:
    ws = ws_dir(case, rep)
    if ws.exists():
        shutil.rmtree(ws)
    ws.mkdir(parents=True)
    shutil.copytree(CASE_ROOT / case / "inputs", ws / "inputs")
    task = build_task(case, ws)
    (ws / "TASK.md").write_text(task, encoding="utf-8")
    carried = [{"path": str(p.relative_to(ws)), "sha256": sha(p), "bytes": p.stat().st_size}
               for p in sorted((ws / "inputs").rglob("*")) if p.is_file()]
    iso = check_isolation(ws)
    if not iso["ok"]:
        print("隔离检查失败：" + json.dumps(iso, ensure_ascii=False))
        return 2
    meta = {
        "batch": BATCH_NAME, "rule_version": RULE, "product": PRODUCT, "case": case, "rep": rep,
        "event_id": event_id(case, rep), "form": "cli",
        "preregistration_commit": PREREG_COMMIT,
        "workspace": str(ws), "created_at": now_iso(),
        "model": MODEL, "reasoning_effort": EFFORT,
        "product_version": cli_version(),
        "route": TOOL_FACTS[PRODUCT]["route"],
        "tools": TOOL_FACTS[PRODUCT]["tools"],
        "permissions": TOOL_FACTS[PRODUCT]["permissions"],
        "skills": TOOL_FACTS[PRODUCT]["skills"],
        "web_search": "disabled", "soft_constraints": ["stay-in-workspace", "no-oracle-hunt", "offline"],
        "prompt_sha256": hashlib.sha256(task.encode()).hexdigest(),
        "isolation": iso, "inputs": carried,
    }
    (ws / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("工作区: %s\n题面  : %s（%d 字）" % (ws, ws / "TASK.md", len(task)))
    return 0


# ---------------------------------------------------------------------------
# 会话轨迹 → 无截断完整流重建（工程项 a）与逐调用 usage（工程项 b）
# ---------------------------------------------------------------------------

def session_lines(sess_dir: Path):
    """按序产出 (source_name, line_text)。zstd 会话轨迹为无损 commit 事件源。"""
    for p in sorted(sess_dir.iterdir()):
        if not p.is_file():
            continue
        if p.suffix == ".zstd":
            out = subprocess.run(["zstd", "-dc", str(p)], capture_output=True, timeout=300)
            text = out.stdout.decode("utf-8", errors="replace")
        elif p.suffix == ".jsonl":
            text = p.read_text(encoding="utf-8", errors="replace")
        else:
            continue
        for line in text.splitlines():
            yield p.name, line


def parse_arguments(raw: str):
    """与 dsh-headless 相同的入参解析：空串={}；非法 JSON 保留原文。"""
    if raw == "":
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return raw


def result_text(content) -> str:
    blocks = content if isinstance(content, list) else []
    return "".join(b.get("text", "") for b in blocks
                   if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str))


def rebuild_full_stream(sess_dir: Path):
    """从耐久会话轨迹按 dsh-headless 投影语义重建无截断事件流。

    与 json-stream 投影一致：session / status(turn_start,step_start,step_end,turn_end) /
    thinking / text / tool_call / tool_result(surfaceOp=append) / final（末条 committed
    assistant/message 的 text 块）。唯一差异：字符串与整行不加 8192/32KB 截断（工程项 a）。
    逐 step usage 优先取 step/end 的 attempts 累计语义不可行（attempt 流不入耐久日志），
    故 step_end.usage 取同 step 已提交 assistant/message 的 usage（commit 点，无损），
    与 raw stdout 中投影 step_end 事件交叉核对（见 extract_per_call_usage）。
    """
    events = []
    last_text_by_step = {}
    pending_usage = {}   # step key -> usage（来自 assistant/message）
    for _src, line in session_lines(sess_dir):
        try:
            ev = json.loads(line)
        except Exception:
            continue
        t = ev.get("type")
        if t == "session":
            events.append({"type": "session", "sessionId": ev.get("id"), "cwd": ev.get("cwd")})
        elif t == "turn/start":
            events.append({"type": "status", "phase": "turn_start", "turn": ev["data"]["turn"]})
        elif t == "step/start":
            events.append({"type": "status", "phase": "step_start", "turn": ev["data"]["turn"],
                           "step": ev["data"]["step"]})
        elif t == "assistant/message":
            d = ev["data"]
            key = (d["turn"], d["step"])
            if isinstance(d.get("usage"), dict):
                pending_usage[key] = d["usage"]
            for block in d["message"]["content"]:
                if block.get("type") == "reasoning":
                    events.append({"type": "thinking", "text": block.get("text", "")})
                elif block.get("type") == "text":
                    events.append({"type": "text", "text": block.get("text", "")})
                    last_text_by_step[key] = block.get("text", "")
        elif t == "tool/call":
            d = ev["data"]
            events.append({"type": "tool_call", "callId": d["callId"], "tool": d["name"],
                           "input": parse_arguments(d.get("arguments", ""))})
        elif t == "tool/result":
            if ev.get("surfaceOp") not in (None, "append"):
                continue
            msg = ev["data"]["message"]
            events.append({"type": "tool_result", "callId": msg["toolCallId"],
                           "status": "error" if msg.get("isError") is True else "completed",
                           "result": result_text(msg.get("content"))})
        elif t == "step/end":
            d = ev["data"]
            usage = pending_usage.pop((d["turn"], d["step"]), None)
            events.append({"type": "status", "phase": "step_end", "turn": d["turn"], "step": d["step"],
                           **({"usage": map_usage(usage)} if usage else {})})
        elif t == "turn/end":
            d = ev["data"]
            events.append({"type": "status", "phase": "turn_end", "turn": d["turn"],
                           "reason": (d.get("reason") or {}).get("kind")})
    # final：headless 语义为 lossless 最终答复 = 末条 committed text
    final_text = ""
    if last_text_by_step:
        last_key = sorted(last_text_by_step.keys())[-1]
        final_text = last_text_by_step[last_key]
    events.append({"type": "final", "text": final_text})
    return events


def map_usage(u: dict) -> dict:
    """投影 usage 字段 → 入库字段（cache_read / cache_creation 显式命名）。"""
    out = {"input_tokens": u.get("inputTokens"), "output_tokens": u.get("outputTokens")}
    if "totalTokens" in u:
        out["total_tokens"] = u.get("totalTokens")
    if "cacheReadTokens" in u:
        out["cache_read_tokens"] = u.get("cacheReadTokens")
    if "cacheWriteTokens" in u:
        out["cache_creation_tokens"] = u.get("cacheWriteTokens")
    if "reasoningTokens" in u:
        out["reasoning_tokens"] = u.get("reasoningTokens")
    return out


def extract_per_call_usage(sess_dir: Path, raw_log: Path | None) -> dict:
    """工程项 b：逐调用 usage（含 cache_read/cache_creation）。

    来源：耐久会话轨迹 assistant/message.usage（commit 点）。交叉核对：raw stdout 投影
    step_end.usage（含 attempt 累计语义），逐 step 全等则一致；不一致如实记 mismatch。
    """
    per_call = []
    for _src, line in session_lines(sess_dir):
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("type") != "assistant/message":
            continue
        d = ev["data"]
        if not isinstance(d.get("usage"), dict):
            continue
        per_call.append({"turn": d["turn"], "step": d["step"], **map_usage(d["usage"])})

    # 交叉核对：raw stdout 的 step_end usage（若可用）
    cross = {"compared": 0, "equal": 0, "mismatch": []}
    if raw_log is not None and raw_log.exists():
        for line in raw_log.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                ev = json.loads(line)
            except Exception:
                continue
            if ev.get("type") == "status" and ev.get("phase") == "step_end" and isinstance(ev.get("usage"), dict):
                mine = next((c for c in per_call if c["turn"] == ev.get("turn") and c["step"] == ev.get("step")), None)
                if mine is None:
                    continue
                cross["compared"] += 1
                theirs = map_usage(ev["usage"])
                same = all(mine.get(k) == v for k, v in theirs.items())
                if same:
                    cross["equal"] += 1
                elif len(cross["mismatch"]) < 10:
                    cross["mismatch"].append({"turn": ev.get("turn"), "step": ev.get("step"),
                                              "session": mine, "stdout_projection": theirs})

    def total(field):
        vals = [c.get(field) for c in per_call if isinstance(c.get(field), int)]
        return sum(vals) if vals else None

    summary = {
        "requests": len(per_call),
        "input_tokens": total("input_tokens"),
        "output_tokens": total("output_tokens"),
        "cache_read_tokens": total("cache_read_tokens"),
        "cache_creation_tokens": total("cache_creation_tokens"),
        "per_call": per_call,
        "cross_check": cross,
        "source": "durable session log assistant/message usage (commit points); cache_read_tokens=cacheReadTokens, cache_creation_tokens=cacheWriteTokens (anthropic-messages 语义)",
    }
    return summary


def scan_integrity_stream(sources) -> dict:
    """对 (name, line) 流做八类越界模式扫描。"""
    hits = []
    n_lines = 0
    for name, line in sources:
        n_lines += 1
        try:
            ev = json.loads(line)
        except Exception:
            blob = line
        else:
            blob = json.dumps(ev.get("input") if isinstance(ev, dict) and "input" in ev else ev, ensure_ascii=False)
        for pat in INTEGRITY_PATTERNS:
            if pat in blob:
                hits.append({"file": name, "line": n_lines, "pattern": pat, "excerpt": blob[:300]})
                break
        if len(hits) >= 20:
            break
    return hits, n_lines


def scan_session_integrity(sess_dir: Path) -> dict:
    hits, n_lines = scan_integrity_stream(session_lines(sess_dir))
    return hits, n_lines


def judge(case: str, ws: Path) -> dict:
    p = subprocess.run([sys.executable, str(CASE_ROOT / case / "checker.py"), str(ws), "--json"],
                       capture_output=True, text=True, timeout=1200, cwd=str(REPO))
    try:
        res = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        res = {"reward": None, "error": (p.stdout + p.stderr)[-2000:]}
    return res


def build_score_receipt(case: str, res: dict) -> dict:
    """判分收据（schema 同 r1030，构建逻辑移植自 r1030 tools/build_import.py）。"""
    cfg = json.loads((V2 / "config.json").read_text(encoding="utf-8"))
    checks = res.get("checks") or []
    guards = GUARDS[case]
    scored = [c for c in checks if c.get("id") not in guards]
    possible = len(scored)
    if possible != TOTALS[case]:
        raise SystemExit("计分项数与全题分母不符：%s %d != %d（守卫集 %s）" % (case, possible, TOTALS[case], sorted(guards)))
    earned = sum(1 for c in scored if c.get("pass"))
    if abs(round(100.0 * earned / possible, 2) - float(res.get("weighted"))) > 0.011:
        raise SystemExit("计分项通过数与 checker weighted 不一致：%s earned=%d" % (case, earned))
    return {"earned": earned, "possible": possible, "assessed": possible,
            "reported": round(100.0 * earned / possible, 8),
            "reward": res.get("reward"), "rule_version": RULE,
            "checker_sha256": cfg["case_snapshots"][case]["checker.py"]}


def capture_session_dsh(ev: Path, ws: Path, started: float) -> None:
    """归档本场 DSH 会话轨迹（~/.dsh/sessions 下目录名含 -dsh-<rep>-<case>--，mtime 过滤）。"""
    sess = ev / "agent-session"
    sess.mkdir(exist_ok=True)
    base = Path.home() / ".dsh" / "sessions"
    if not base.is_dir():
        return
    marker = "-dsh-%s-%s--" % (ws.parent.name, ws.name)
    for cand in base.iterdir():
        if cand.is_dir() and marker in cand.name:
            for q in cand.rglob("*"):
                if q.is_file() and q.suffix != ".lock" and q.stat().st_mtime >= started - 5:
                    tgt = sess / q.name
                    if not tgt.exists():
                        shutil.copy2(q, tgt)


def write_adjudication(ev: Path, meta: dict, scored: bool) -> None:
    """逐场裁定草案（schema 同 r1030；语义 benign 复核留 lead，草案不越权改判）。"""
    verd = meta.get("integrity_verdict")
    ok_run = meta.get("status") == "ok" and meta.get("exit_code") == 0
    clean = verd == "clean"
    gates = {g: (g in ("rules_frozen", "case_valid")) for g in
             ("rules_frozen", "case_valid", "scoring_reviewable", "evidence_valid", "contamination_free")}
    retries = meta.get("transport_retries") or []
    if ok_run and clean and scored:
        adjudication, grade = "valid", "original-contemporaneous-full"
        gates = {g: True for g in gates}
        basis = ("规则: freeze-20261029-v2 预注册封印于运行前提交(commit %s)，注册早于开始；"
                 "题面: v2 config 冻结 manifest 未漂移（preflight 校验 checker 哈希一致）；"
                 "评分: 全分母 checker 收据+raw 输出双源；证据: meta/raw stdout 完整流/会话轨迹/判分/配置快照当场归档；"
                 "无污染: 工作区仓库外+隔离断言+stdout 与会话轨迹八类模式扫描 0 命中。") % PREREG_COMMIT
        if retries:
            basis += " 同一逻辑运行内传输层重试 %d 次（429/断连，指数退避≤3，逐次记录 meta.transport_retries）。" % len(retries)
    elif meta.get("status") == "timeout":
        adjudication, grade = "valid", "original-contemporaneous-full"
        gates = {g: True for g in gates}
        basis = ("按 case.json timeout_s 合同超时截停；checker 对现有产物全量评估，按合同记结果。"
                 "无污染: 双流扫描 %d 命中；证据当场全量归档。") % meta.get("integrity", {}).get("violations", -1)
    elif ok_run and scored and not clean:
        # 命中存在但运行完好：草案不做语义 benign 裁定（r1030 由 lead 复核）
        adjudication, grade = "pending-review", "original-contemporaneous-full"
        gates["scoring_reviewable"] = True
        gates["evidence_valid"] = True
        basis = ("运行完好、评分可复核，但八类模式扫描 %d 命中；builder 不做语义裁定，"
                 "待 lead 按 r1030 同一标准复核 benign（预期为运行时注入的用户级 AGENTS.md 文本命中 ~/Documents）。"
                 "逐条证据见 meta.integrity 与 integrity-rescan.json。") % meta.get("integrity", {}).get("violations", -1)
    else:
        adjudication, grade = "infrastructure_invalid", "original-contemporaneous-partial"
        basis = ("status=%s exit=%s integrity=%s——启动/传输/工具基础设施问题或证据不全，"
                 "不进 primary；selection=null 诊断事件已登记（run-failures.json），如实保留诊断。") % (
            meta.get("status"), meta.get("exit_code"), verd)
    receipt = {
        "event_id": meta["event_id"], "run_id": meta["run_id"],
        "identity": {"event_id": meta["event_id"], "run_id": meta["run_id"], "category": "product_run",
                     "product": PRODUCT, "group": "A_same_model", "experiment": False, "case_id": meta["case"],
                     "rep": meta["rep"]},
        "evidence_grade": grade, "final_adjudication": adjudication,
        "gates": gates, "adjudicated_at": now_iso(),
        "adjudicator": "builder-dsh（草案；语义裁定信任边界在 lead，benign 命中待复核）",
        "basis": basis,
    }
    (ev / "adjudication.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt


def record_failure(case: str, rep: str, meta: dict) -> None:
    """selection=null 诊断事件（运行级失败，不补跑）。"""
    failures = OUT_ROOT / "run-failures.json"
    data = json.loads(failures.read_text(encoding="utf-8")) if failures.exists() else {"failures": []}
    data["failures"].append({
        "event_id": event_id(case, rep), "run_id": run_id(case, rep), "batch": BATCH_NAME,
        "selection": None, "at": now_iso(),
        "diagnostics": {"status": meta.get("status"), "exit_code": meta.get("exit_code"),
                        "stderr_tail": meta.get("failure_diagnostics", {}).get("stderr_tail", ""),
                        "transport_retries": meta.get("transport_retries", []),
                        "workspace": str(ws_dir(case, rep))},
        "policy": "无重试；该 rep 记 failed，不补跑、不替换（PREREGISTRATION 总则 2）",
    })
    failures.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def classify_transport_error(stderr_text: str, exit_code) -> str | None:
    blob = (stderr_text or "").lower()
    for pat in TRANSPORT_PATTERNS:
        if pat in blob:
            return pat
    return None


def archive(case: str, rep: str, log: Path, err: Path, started: str, finished: str,
            duration: float, res: dict, exit_code, status: str, retries: list) -> Path:
    ws = ws_dir(case, rep)
    ev = run_ev(case, rep)
    if ev.exists():
        shutil.rmtree(ev)
    (ev / "workspace").mkdir(parents=True)
    for p in ws.iterdir():
        if p.name in ("inputs", "agent.jsonl", "agent.stderr.txt", "meta.json"):
            continue
        if p.is_dir():
            shutil.copytree(p, ev / "workspace" / p.name)
        else:
            shutil.copy2(p, ev / "workspace" / p.name)
    # 日志源即 staging 快照（写入阶段就避开 ev 目录，根除 r1030#1）；末次 attempt
    # 落为 agent.jsonl / agent.stderr.txt，被传输退避替换的此前 attempt 流一并列档。
    if log.exists():
        shutil.copy2(log, ev / "agent.jsonl")
    if err.exists():
        shutil.copy2(err, ev / "agent.stderr.txt")
    for r in retries:
        n = r.get("attempt")
        src_l = OUT_ROOT / "staging" / ("dsh__%s__r%s.a%d.agent.jsonl" % (case, rep, n))
        src_e = OUT_ROOT / "staging" / ("dsh__%s__r%s.a%d.agent.stderr.txt" % (case, rep, n))
        if src_l.exists():
            shutil.copy2(src_l, ev / ("agent.attempt%d.jsonl" % n))
        if src_e.exists():
            shutil.copy2(src_e, ev / ("agent.attempt%d.stderr.txt" % n))
    # 会话轨迹归档（先于重建使用）
    st = dt.datetime.fromisoformat(started).timestamp()
    capture_session_dsh(ev, ws, st)
    # 工程项 a：raw stdout 记字节数；从会话轨迹重建无截断完整流落盘
    raw_bytes = (ev / "agent.jsonl").stat().st_size if (ev / "agent.jsonl").exists() else 0
    raw_lines = sum(1 for _ in (ev / "agent.jsonl").open(encoding="utf-8", errors="replace")) if raw_bytes else 0
    full_bytes = full_lines = 0
    sess_dir = ev / "agent-session"
    if sess_dir.is_dir() and any(sess_dir.iterdir()):
        events = rebuild_full_stream(sess_dir)
        full_path = ev / "agent.jsonl.full"
        with full_path.open("w", encoding="utf-8") as fh:
            for e in events:
                fh.write(json.dumps(e, ensure_ascii=False) + "\n")
        full_bytes = full_path.stat().st_size
        full_lines = len(events)
    # 工程项 b：逐调用 usage（会话轨迹 commit 点 + raw stdout 投影交叉核对）
    usage = extract_per_call_usage(sess_dir, ev / "agent.jsonl") if full_lines else {
        "requests": 0, "input_tokens": None, "output_tokens": None,
        "cache_read_tokens": None, "cache_creation_tokens": None, "per_call": [],
        "cross_check": {"compared": 0, "equal": 0, "mismatch": []},
        "source": "session log unavailable", "note": "无会话轨迹归档；usage 不可提取，如实记空"}
    # 配置快照（路由/权限佐证）
    cfg = ev / "config-snapshot"
    cfg.mkdir(exist_ok=True)
    prof = Path.home() / ".dsh" / "profiles" / DSH_PROFILE
    shutil.copy2(prof / "cordis.patch.yml", cfg / "bench-cli-cordis.patch.yml")
    shutil.copy2(prof / "package.json", cfg / "bench-cli-package.json")
    # 双流完整性扫描：raw stdout + 会话轨迹
    stdout_hits, stdout_lines = scan_integrity_stream(
        [("agent.jsonl", l) for l in (ev / "agent.jsonl").open(encoding="utf-8", errors="replace")]) if raw_bytes else ([], 0)
    sess_hits, sess_lines = scan_session_integrity(sess_dir) if full_lines else ([], 0)
    hits = stdout_hits + sess_hits
    integ = {"violations": len(hits), "patterns": INTEGRITY_PATTERNS,
             "basis": "runner stdout stream (preserved via staging, r1030#1 fixed) + session-trajectory dual scan",
             "stdout_scan": {"lines": stdout_lines, "violations": len(stdout_hits)},
             "session_scan": {"lines": sess_lines, "violations": len(sess_hits)},
             "evidence": hits}
    meta = json.loads((ws / "meta.json").read_text(encoding="utf-8"))
    meta.update({
        "status": status, "exit_code": exit_code,
        "started_at": started, "finished_at": finished, "duration_s": duration,
        "transport_retries": retries,
        "archived_stdout": {
            "raw_bytes": raw_bytes, "raw_lines": raw_lines,
            "raw_file": "agent.jsonl",
            "raw_truncation": "dsh-headless 0.2.0-rc.2 --json projection caps are hardcoded (maxStringBytes=8192, maxEventBytes=32768); no flag/env override exists in this version",
            "full_bytes": full_bytes, "full_lines": full_lines,
            "full_file": "agent.jsonl.full",
            "full_method": "lossless re-projection of durable session log (agent-session/*.jsonl.zstd) with string/line caps removed; same commit-point semantics as the CLI projection",
        },
        "usage": usage,
        "reward": res.get("reward"), "weighted": res.get("weighted"),
        "failed": [c.get("id") for c in res.get("checks", []) if not c.get("pass")],
        "judge": res,
        "integrity": integ,
        "integrity_verdict": "clean" if len(hits) == 0 else "violation",
        "run_id": run_id(case, rep),
    })
    (ev / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ev / "checker.stdout.json").write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # 判分收据（schema 同 r1030）
    scored = isinstance(res, dict) and "checks" in res and res.get("weighted") is not None
    if scored:
        score = build_score_receipt(case, res)
        (ev / "score-receipt.json").write_text(json.dumps(
            {"case": case, "product": PRODUCT, "run_id": run_id(case, rep),
             "rep": rep, "score": score, "raw_checker_output": res,
             "note": "composite transcription; raw checker output packaged alongside"},
            ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # 逐场独立会话轨迹重扫收据（对 runner 扫描的二次核验）
    tag = "dsh__%s__r%s" % (case, rep)
    rescan = {"run": tag, "patterns": INTEGRITY_PATTERNS,
              "session_files": [{"name": p.name, "bytes": p.stat().st_size, "zstd": p.suffix == ".zstd"}
                                for p in sorted(sess_dir.iterdir()) if p.is_file()] if full_lines else [],
              "lines_scanned": sess_lines, "usage_events_present": usage.get("requests", 0),
              "violations": len(sess_hits), "evidence": sess_hits,
              "method": "session-trajectory rescan (independent cross-check; runner stdout stream preserved, no r1030#1 defect)",
              "reviewed": None}
    (ev / "integrity-rescan.json").write_text(json.dumps(rescan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_adjudication(ev, meta, scored)
    if status != "ok" or exit_code != 0:
        record_failure(case, rep, meta)
    return ev


def cmd_run(case: str, rep: str) -> int:
    if case not in CASES or rep not in REPS:
        print("run 仅支持 case ∈ 5 题 × rep ∈ {2,3}（dsh 侧）")
        return 2
    ws = ws_dir(case, rep)
    if not (ws / "TASK.md").exists():
        cmd_prepare(case, rep)
    prompt = (ws / "TASK.md").read_text(encoding="utf-8")
    key = load_api_key()
    cj = CASE_ROOT / case / "case.json"
    timeout = json.loads(cj.read_text()).get("timeout_s", 1800) if cj.exists() else 1800
    ev_dir = run_ev(case, rep)
    ev_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, DEEPSEEK_API_KEY=key)
    cmd = ["dsh", DSH_PROFILE, "--json", "-"]
    started = now_iso()
    st_ts = time.time()
    status, exit_code = "ok", None
    retries: list = []
    # 日志一律先写 staging（证据目录外）：r1030#1 缺陷（archive 顶部 rmtree 连带删除
    # 写在 ev 目录内的日志）在 r1030 侧"staging 修复"中依然存在（rmtree 先于移动），
    # 本运行器从写入位置上根除；传输层退避时按 attempt 分档保留每次的完整流。
    staging = OUT_ROOT / "staging"
    staging.mkdir(exist_ok=True)
    tag = "dsh__%s__r%s" % (case, rep)
    # 传输层错误（429/断连）指数退避 ≤3 次；属同一逻辑运行。运行级其它失败不重试。
    for attempt in range(1, 5):  # 1 次首发 + 最多 3 次传输退避
        a_log = staging / ("%s.a%d.agent.jsonl" % (tag, attempt))
        a_err = staging / ("%s.a%d.agent.stderr.txt" % (tag, attempt))
        with a_log.open("w", encoding="utf-8") as out, a_err.open("w", encoding="utf-8") as er:
            try:
                p = subprocess.run(cmd, cwd=str(ws), env=env, input=prompt, text=True,
                                   stdout=out, stderr=er, timeout=timeout)
                exit_code = p.returncode
                status = "ok"
            except subprocess.TimeoutExpired:
                status, exit_code = "timeout", None
        if status == "timeout":
            break  # 超时是运行级结果，按合同截停判分，不重试
        stderr_text = a_err.read_text(encoding="utf-8", errors="replace") if a_err.exists() else ""
        transport = classify_transport_error(stderr_text, exit_code) if exit_code not in (0, None) else None
        if transport is None or attempt > 3:
            break
        backoff = 5 * (3 ** (attempt - 1))  # 5s / 15s / 45s
        retries.append({"attempt": attempt, "error_class": transport,
                        "stderr_tail": stderr_text[-800:], "backoff_ms": backoff * 1000,
                        "attempt_stdout": "agent.attempt%d.jsonl" % attempt,
                        "attempt_stderr": "agent.attempt%d.stderr.txt" % attempt})
        print(json.dumps({"note": "transport retry", "attempt": attempt, "error_class": transport,
                          "backoff_ms": backoff * 1000}, ensure_ascii=False))
        time.sleep(backoff)
    # 末次 attempt 即本场正式流（archive 以 staging 快照为源，ev 目录可安全重建）
    log = staging / ("%s.agent.jsonl" % tag)
    err = staging / ("%s.agent.stderr.txt" % tag)
    shutil.copy2(staging / ("%s.a%d.agent.jsonl" % (tag, attempt)), log)
    shutil.copy2(staging / ("%s.a%d.agent.stderr.txt" % (tag, attempt)), err)
    finished = now_iso()
    duration = round(time.time() - st_ts, 1)
    res = judge(case, ws)
    ev = archive(case, rep, log, err, started, finished, duration, res, exit_code, status, retries)
    meta = json.loads((ev / "meta.json").read_text(encoding="utf-8"))
    print(json.dumps({"case": case, "rep": rep, "status": status, "exit_code": exit_code,
                      "reward": res.get("reward"), "weighted": res.get("weighted"),
                      "duration_s": duration, "violations": meta["integrity"]["violations"],
                      "transport_retries": len(retries),
                      "usage_requests": (meta.get("usage") or {}).get("requests"),
                      "archived_stdout_bytes": (meta.get("archived_stdout") or {}).get("raw_bytes"),
                      "full_stream_bytes": (meta.get("archived_stdout") or {}).get("full_bytes"),
                      "evidence": str(ev)}, ensure_ascii=False))
    return 0


def cmd_judge(case: str, rep: str) -> int:
    ws = ws_dir(case, rep)
    print(json.dumps(judge(case, ws), ensure_ascii=False)[:2000])
    return 0


def cmd_integrity(case: str, rep: str) -> int:
    ev = run_ev(case, rep)
    p = ev / "integrity-rescan.json"
    if not p.exists():
        print("integrity-rescan.json 不存在：%s" % ev)
        return 2
    print(p.read_text(encoding="utf-8")[:4000])
    return 0


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("preflight").set_defaults(func=lambda a: cmd_preflight())
    sp = sub.add_parser("prepare"); sp.add_argument("case"); sp.add_argument("rep")
    sp.set_defaults(func=lambda a: cmd_prepare(a.case, a.rep))
    sp = sub.add_parser("run"); sp.add_argument("case"); sp.add_argument("rep")
    sp.set_defaults(func=lambda a: cmd_run(a.case, a.rep))
    sp = sub.add_parser("judge"); sp.add_argument("case"); sp.add_argument("rep")
    sp.set_defaults(func=lambda a: cmd_judge(a.case, a.rep))
    sp = sub.add_parser("integrity"); sp.add_argument("case"); sp.add_argument("rep")
    sp.set_defaults(func=lambda a: cmd_integrity(a.case, a.rep))
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
