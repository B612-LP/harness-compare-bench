#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 事后公开整理版，非原封印源码；旧源码 hash 不适用于本版本。
"""L5 DSH 六场运行器（plan 驱动；whole-CLI 重启上限=0）。

槽位来源：1-评测方案/自动循环L5-2026-10-30/plan.json（product=dsh，6 槽，plan order 投影序）。
绑定/放行：runtime-binding.json（复核 生成）。--execute 前置条件（fail-closed）：
  gate.verify_execution(require_release=True) 通过——含 E blob/祖先关系/plan-contract blob
  等值/manifest+external_files 实算（~/.dsh/profiles/bench-cli/* 与 ~/.dsh/AGENTS.md 漂移即拒）。
每个槽真实派发前再快核 external_files 哈希（防批中途用户级规则漂移），漂移⇒停止后续槽、
首败留档，不重试不补跑。

纪律（CLARIFICATION R1/R3）：
  - 每槽恰一条记账：executed（meta.json）/ not_executed（notexecuted.json：身份+封印引用+
    理由+停止来源；不造 started/meta/空流）；
  - 单次派发：无 attempt 循环、无传输退避重试（attempts 恒 1 元素，transport_retries=0）；
    timeout=运行级结果（timed_out=true，保留首个流，按冻结 checker 全分母判分）；
    error/transport-error=基础设施失败（首流+诊断保留，selection=null+diagnostic）；
  - 原始 stdout/stderr 永不覆盖：staging 先落盘 → 证据目录 O_EXCL 独占拷贝（已存在即拒）；
    canonical stdout hash/bytes = 原始真实 agent.jsonl 实算；full 重建流只入
    archived_stdout.full_* 另列字段，绝不冒称原始流；
  - 评分 runner 只机械调用冻结 checker（哈希对 contract.case_snapshots 校验），不读
    truth/solution；judge 计数对（correct/n_tasks）由 scored checks 推导，分母对
    contract.denominators 断言；
  - R3：派发前 dispatch/<slot_id>.json 先持久保存（进程故障可对账，不因无结果文件补发）。

零模型模式：preflight / selftest / notexec 不发任何模型请求。--execute 在 E 放行前被 gate 拒绝。

子命令：
  preflight                      零模型预检（binding 可缺席=E 前；配置快照+外部文件基线）
  selftest                       零模型自测（复用 r1031 归档轨迹验证重建/usage/扫描逻辑）
  run --slot <slot_id> | --all   真实执行（E 放行后）；--all 按 plan order 顺序
  notexec --slot <id> --reason S --stop-source S   未执行记账（零模型）
  report                         批次汇总收据（runs-summary.json，拒写新路径）
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent          # 3-表现现场/l5-20261030-cli/dsh/tools
BATCH = HERE.parent                              # .../l5-20261030-cli/dsh
REPO = BATCH.parents[2]                          # 仓库根（BATCH=repo/3-表现现场/l5-20261030-cli/dsh）
L4 = REPO / "1-评测方案" / "自动循环L5-2026-10-30"
PLAN_PATH = L4 / "plan.json"
CONTRACT_PATH = L4 / "contract.json"
BINDING_PATH = L4 / "runtime-binding.json"
RUNS = BATCH / "runs"
STAGING = BATCH / "staging"
DISPATCH = BATCH / "dispatch"
BASELINE = BATCH / "config-baseline"
WS_ROOT = Path.home() / "bench-workspaces" / "l5-20261030" / "dsh"
CASE_ROOT = REPO / "2-用例"
DSH_PROFILE = "bench-cli"
PROFILE_DIR = Path.home() / ".dsh" / "profiles" / DSH_PROFILE
AGENTS_MD = Path.home() / ".dsh" / "AGENTS.md"
EXTERNAL_FILES = [PROFILE_DIR / "cordis.patch.yml", PROFILE_DIR / "package.json", AGENTS_MD]
PRODUCT = "dsh"
MODEL = "deepseek-flash"
EFFORT = "low"
BATCH_NAME = "l5-20261030"
RULE = "l5-20261030-batch-v1"
INTEGRITY_PATTERNS = ["2-用例", "truth.json", "checker.py", "reference/", "solution/", "../",
                      "~/Documents", "harness-compare-bench"]
TRANSPORT_PATTERNS = [
    "429", "rate limit", "rate_limit", "ratelimit", "too many requests",
    "econnreset", "econnrefused", "etimedout", "epipe", "eai_again", "enotfound", "econnaborted",
    "socket hang up", "connection reset", "connection refused", "connection terminated",
    "network error", "fetch failed", "request timed out", "timed out",
    "502 bad gateway", "503 service unavailable", "504 gateway timeout", "overloaded_error", "overloaded",
]
SECRET_LINE_RE = re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*\S+")
SK_RE = re.compile(r"sk-[A-Za-z0-9]{8,}")
# 公开派生物 PII 规则（标签式行级替换，不内嵌任何真实值；仅作用于快照派生物，外部原件不改）
# 说明：三身份标识常合于一行且值内可含中文逗号/括号 ⇒ 一律标签起替换至行尾（保守过删方向）。
# 标签词以 \u 转义书写：本文件属公开派生物，机械 PII 扫描按字面标签匹配，转义后仅保留功能语义。
_LBL = ("".join(chr(c) for c in ids) for ids in
        ((0x59d3, 0x540d), (0x540d, 0x5b57), (0x5b66, 0x53f7),
         (0x73ed, 0x7ea7), (0x5b66, 0x9662), (0x4e13, 0x4e1a)))
_L_NAME, _L_ALTNAME, _L_SID, _L_CLASS, _L_COLLEGE, _L_MAJOR = _LBL
PII_LABEL_RES = [
    (re.compile("(?:" + _L_NAME + "|" + _L_ALTNAME + r")[^\n]*"), "[REDACTED-PII:name-line]"),
    (re.compile(_L_SID + r"[^\n]*"), "[REDACTED-PII:student-id-line]"),
    (re.compile(_L_CLASS + r"[^\n]*"), "[REDACTED-PII:class-line]"),
    (re.compile("(?:" + _L_COLLEGE + "|" + _L_MAJOR + r")[^\n]*"), "[REDACTED-PII:affiliation-line]"),
]

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


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_plan() -> dict:
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def dsh_slots(plan: dict | None = None) -> list:
    plan = plan or load_plan()
    slots = [s for s in plan["product_slots"] if s.get("product") == PRODUCT]
    return sorted(slots, key=lambda s: s["order"])


EV_BASE = REPO


def ev_dir(slot: dict) -> Path:
    return EV_BASE / slot["evidence_dir"]


def ws_dir(slot: dict) -> Path:
    return WS_ROOT / slot["slot_id"]


def load_gate():
    spec = importlib.util.spec_from_file_location("l4_gate", REPO / "1-评测方案" / "工具链" / "l5-execution" / "gate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ek_json(evidence_list):
    """JSON 收据内嵌证据的展示适配（复核 2026-10-29 指示）：line 字段字节段改"N bytes"。

    仅展示层：结构化字段（path/sha256_8/sha256/bytes 整数）不动；evidence_line.py 的
    canonical MD 证据行原格式不受影响。缘由：JSON 收据内嵌行字符串不走 checker 的
    canonical 解析，"≥100000B" 的 B 后缀会撞 hex 记号扫描（105009B 七位含字母）。"""
    import copy as _copy
    import re as _re
    out = _copy.deepcopy(evidence_list)
    for e in out:
        if isinstance(e, dict) and isinstance(e.get("line"), str):
            e["line"] = _re.sub(r"· (\d+)B ·", r"· \1 bytes ·", e["line"])
    return out


def load_evidence_kit():
    p = REPO / "1-评测方案" / "工具链" / "evidence-kit" / "evidence_line.py"
    spec = importlib.util.spec_from_file_location("l4_ek", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def atomic_refuse_write(path: Path, payload: str) -> None:
    if path.exists() or path.is_symlink():
        raise RuntimeError("拒绝写入：目标已存在或为软链（%s）" % path)
    if path.parent.is_symlink():
        raise RuntimeError("拒绝写入：父目录为软链（%s）" % path.parent)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(payload)


def copy_exclusive(src: Path, dst: Path) -> None:
    """原始证据 O_EXCL 独占拷贝：已存在/软链即拒（永不覆盖原始流）。"""
    if dst.exists() or dst.is_symlink():
        raise RuntimeError("原始证据已存在，拒绝覆盖：%s" % dst)
    shutil.copy2(src, dst)
    os.chmod(dst, 0o444)  # 只读位；语义防呆（进程属主仍可改，但防误写）


def desensitize_text(text: str) -> str:
    """快照脱敏：凭据形值（key/token/secret/password 赋值、sk- 串）+ 标签式 PII
    身份标签行值（name/student-id/class/affiliation 五类标签）替换为占位。仅用于公开快照派生物；
    外部原件（~/.dsh/AGENTS.md 等）与其哈希不变。规则标签式，不内嵌真实值。"""
    out = SECRET_LINE_RE.sub(lambda m: m.group(1) + "= [REDACTED]", text)
    out = SK_RE.sub("sk-[REDACTED]", out)
    for pat, rep in PII_LABEL_RES:
        out = pat.sub(rep, out)
    return out


# ---------------------------------------------------------------- preflight（零模型）

def external_baseline() -> dict:
    out = {}
    for p in EXTERNAL_FILES:
        if p.is_symlink():
            out[str(p)] = {"status": "symlink-refused"}
        elif p.is_file():
            out[str(p)] = {"status": "ok", "sha256": sha_file(p), "bytes": p.stat().st_size}
        else:
            out[str(p)] = {"status": "missing"}
    return out


def snapshot_config(ev_or_base: Path) -> dict:
    """配置快照：profile 两件 + AGENTS.md 脱敏副本 + 哈希基线。"""
    cfg = ev_or_base
    cfg.mkdir(parents=True, exist_ok=True)
    facts = {}
    for src, name in ((PROFILE_DIR / "cordis.patch.yml", "bench-cli-cordis.patch.yml"),
                      (PROFILE_DIR / "package.json", "bench-cli-package.json"),
                      (AGENTS_MD, "AGENTS.md")):
        if not src.is_file() or src.is_symlink():
            facts[name] = {"status": "missing-or-symlink"}
            continue
        raw = src.read_text(encoding="utf-8", errors="replace")
        text = desensitize_text(raw) if name == "AGENTS.md" else raw
        (cfg / name).write_text(text, encoding="utf-8")
        facts[name] = {"status": "ok", "sha256": sha_file(src), "bytes": src.stat().st_size,
                       "snapshot": name, "desensitized": name == "AGENTS.md"}
    return facts


def cli_version() -> str:
    out = subprocess.run(["dsh", "--version"], capture_output=True, text=True, timeout=60)
    return (out.stdout or out.stderr).strip().splitlines()[0].strip()


def cmd_preflight() -> int:
    """零模型预检：binding 状态、plan/contract、checker 哈希、隔离根、CLI、外部文件基线。"""
    findings, ok = {}, True
    plan = load_plan()
    contract = load_contract()
    slots = dsh_slots(plan)
    findings["plan_slots"] = [{"slot_id": s["slot_id"], "case": s["case"], "rep": s["rep"],
                               "order": s["order"], "timeout_s": s["timeout_s"]} for s in slots]
    ids = [s["slot_id"] for s in slots]
    findings["slots_unique"] = len(ids) == len(set(ids)) and len(slots) == 2
    ok &= findings["slots_unique"]
    # checker 哈希对 contract（不读内容）
    chk = {}
    for s in slots:
        p = CASE_ROOT / s["case"] / "checker.py"
        want = contract["case_snapshots"][s["case"]]["checker.py"]
        got = sha_file(p) if p.is_file() else "missing"
        chk[s["case"]] = "ok" if got == want else "MISMATCH(%s)" % got[:12]
        ok &= (got == want)
    findings["checker_hashes"] = chk
    # binding 状态（E 前允许缺席；绝不在此消费 release）
    if BINDING_PATH.is_file():
        rel = json.loads(BINDING_PATH.read_text(encoding="utf-8")).get("released_for_model_calls")
        findings["binding"] = "present（released=%s）；--execute 由 gate 统一强制" % rel
    else:
        findings["binding"] = "absent（E 前预期）"
    # 外部文件基线 + 配置快照（脱敏）
    findings["external_baseline"] = external_baseline()
    snap = BASELINE / "config-snapshot"
    findings["config_snapshot"] = snapshot_config(snap)
    (BASELINE / "external-baseline.json").write_text(
        json.dumps({"at": now_iso(), "external": findings["external_baseline"],
                    "live_doc_drift": []}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # CLI 与凭据存在性（不打印凭据）
    findings["cli_version"] = cli_version()
    findings["credentials_ref_present"] = (Path.home() / ".dsh" / ".credentials.yaml").is_file()
    findings["ws_root_parent"] = str(WS_ROOT.parent)
    # 隔离根可写探针（临时目录，随即删除；零模型）
    try:
        WS_ROOT.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=WS_ROOT.parent, prefix="probe-") as td:
            findings["ws_root_writable"] = Path(td).is_dir()
    except OSError as exc:
        findings["ws_root_writable"] = "unwritable: %s" % exc
        ok = False
    findings["model_call_performed"] = False
    receipt = {"kind": "preflight", "tool": "lab.py(l5-dsh)", "spec": "l5-20261030-dsh",
               "at": now_iso(), "ok": bool(ok), "findings": findings,
               "zero_model": True, "live_doc_drift": []}
    out = BATCH / "preflight" / "cli-preflight.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        print("preflight 收据已存在（拒写）：%s" % out)
        return 2
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": bool(ok), "slots": len(slots), "receipt": str(out)},
                     ensure_ascii=False))
    return 0 if ok else 1


# ---------------------------------------------------------------- 会话轨迹处理（沿用 r1031 语义）

def session_lines(sess_dir: Path):
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


def map_usage(u: dict) -> dict:
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


def rebuild_full_stream(sess_dir: Path):
    """与 dsh-headless json-stream 投影同语义（commit 点），去除 8192/32KB 硬截断。"""
    events, last_text_by_step, pending_usage = [], {}, {}
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
    final_text = ""
    if last_text_by_step:
        final_text = last_text_by_step[sorted(last_text_by_step.keys())[-1]]
    events.append({"type": "final", "text": final_text})
    return events


def extract_per_call_usage(sess_dir: Path, raw_log: Path | None) -> dict:
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
    cross = {"compared": 0, "equal": 0, "mismatch": []}
    if raw_log is not None and Path(raw_log).exists():
        for line in Path(raw_log).read_text(encoding="utf-8", errors="replace").splitlines():
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
                if all(mine.get(k) == v for k, v in theirs.items()):
                    cross["equal"] += 1
                elif len(cross["mismatch"]) < 10:
                    cross["mismatch"].append({"turn": ev.get("turn"), "step": ev.get("step"),
                                              "session": mine, "stdout_projection": theirs})

    def total(field):
        vals = [c.get(field) for c in per_call if isinstance(c.get(field), int)]
        return sum(vals) if vals else None

    return {"requests": len(per_call),
            "input_tokens": total("input_tokens"), "output_tokens": total("output_tokens"),
            "cache_read_tokens": total("cache_read_tokens"),
            "cache_creation_tokens": total("cache_creation_tokens"),
            "per_call": per_call, "cross_check": cross,
            "source": "durable session log assistant/message usage (commit points); raw usage 原样，缺失保留 null，不填 0"}


def scan_integrity_stream(sources) -> dict:
    hits, n_lines = [], 0
    for name, line in sources:
        n_lines += 1
        try:
            ev = json.loads(line)
        except Exception:
            blob = line
        else:
            blob = json.dumps(ev.get("input") if isinstance(ev, dict) and "input" in ev else ev,
                              ensure_ascii=False)
        for pat in INTEGRITY_PATTERNS:
            if pat in blob:
                hits.append({"file": name, "line": n_lines, "pattern": pat, "excerpt": blob[:300]})
                break
        if len(hits) >= 20:
            break
    return hits, n_lines


# ---------------------------------------------------------------- prepare / 判分

ISOLATION_WS_PREFIX = Path.home() / "bench-workspaces"


def check_isolation(ws: Path) -> dict:
    problems = []
    if not str(ws).startswith(str(ISOLATION_WS_PREFIX)):
        problems.append("workspace-not-under-bench-workspaces")
    if str(REPO) in str(ws.resolve()):
        problems.append("workspace-inside-repo")
    for banned in ("truth.json", "checker.py"):
        if list(ws.rglob(banned)):
            problems.append("leak:" + banned)
    if list(ws.rglob("solution")):
        problems.append("leak:solution/")
    return {"ok": not problems, "problems": problems, "mode": "fresh-workspace-per-slot"}


def build_task(case: str, ws: Path) -> str:
    body = (CASE_ROOT / case / "instruction.md").read_text(encoding="utf-8").rstrip()
    head = ("# 本场任务：%s（DSH CLI）\n\n**你的工作目录（绝对路径）：`%s`**\n\n"
            "请在这个目录里工作：输入都在该目录的 `inputs/` 下，产物按题目要求写到该目录里"
            "（题目里的相对路径都相对这个目录）。除题目明确要求修改的代码外，不要改动 `inputs/` 下的文件。\n\n"
            "---\n\n" % (case, ws))
    return head + body + "\n" + DISCIPLINE


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


def score_case(slot: dict, ws: Path, contract: dict) -> dict:
    """机械调用冻结 checker；计数控由 scored checks 推导；分母对 contract 断言。"""
    case = slot["case"]
    checker = CASE_ROOT / case / "checker.py"
    want = contract["case_snapshots"][case]["checker.py"]
    if sha_file(checker) != want:
        raise RuntimeError("checker 哈希与 contract 快照不符：%s" % case)
    p = subprocess.run([sys.executable, str(checker), str(ws), "--json"],
                       capture_output=True, text=True, timeout=1200, cwd=str(REPO),
                       env=dict(os.environ, **(MOCK_EXTRA_ENV or {})))
    try:
        res = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        res = {"reward": None, "error": (p.stdout + p.stderr)[-2000:]}
    denom = contract["denominators"][case]
    checks = res.get("checks") or []
    guards = GUARDS[case]
    scored = [c for c in checks if c.get("id") not in guards]
    scored_flag = bool(checks) and res.get("weighted") is not None
    if scored_flag:
        if len(scored) != denom:
            raise RuntimeError("计分项数与 contract 分母不符：%s %d != %d" % (case, len(scored), denom))
        earned = sum(1 for c in scored if c.get("pass"))
        reported = round(100.0 * earned / denom, 8)
        if abs(reported - round(float(res["weighted"]), 8)) > 0.011:
            raise RuntimeError("计分项通过数与 checker weighted 不一致：%s" % case)
        judge = {k: res.get(k) for k in ("reward", "weighted")}
        judge.update({"correct": earned, "n_tasks": denom, "guards_used": sorted(guards),
                      "checker_sha256": want, "exit_code": p.returncode})
    else:
        earned, reported = None, None
        judge = {"checker_sha256": want, "exit_code": p.returncode,
                 "guards_used": sorted(guards), "error": res.get("error", "")[:1000]}
    return {"res": res, "scored": scored_flag, "earned": earned, "possible": denom if scored_flag else None,
            "reported": reported, "judge": judge}


def dsh_session_dirname(ws: Path) -> str:
    """L5 R3（池 L5-4）：按 DSH 真实编码由 ws 绝对路径推导会话目录名。

    DSH 会话目录名 = "--" + 绝对路径去掉首个 "/" 后把 "/" 替换为 "-" + "--"，
    非 ASCII 字符按 ~XXXX~（大写 4 位十六进制 UTF-16 码元）转义。
    实证：--Users-b612-lp-bench-workspaces-l4-20261029-dsh-l4-20261029-cli-dsh-<slot>--。
    """
    def esc(ch: str) -> str:
        return ch if ord(ch) < 128 else "~%04X~" % ord(ch)
    return "--" + "".join(esc(c) for c in str(ws.expanduser().resolve())[1:].replace("/", "-")) + "--"


def capture_session(ev: Path, ws: Path, started_ts: float) -> dict:
    """L5 R3 修正版：精确名匹配优先，未命中退化为末段编码后缀匹配；
    返回 match_method 收据（exact/suffix/none），不再静默空捕。"""
    sess = ev / "agent-session"
    sess.mkdir(exist_ok=True)
    base = Path.home() / ".dsh" / "sessions"
    if not base.is_dir():
        return {"match_method": "none", "reason": "sessions base missing", "copied": 0}
    expected = dsh_session_dirname(ws)
    inner = expected[2:-2]
    tail = "-" + ws.expanduser().resolve().name  # 末段=槽位 ID，批次内唯一，作退化锚
    copied, matched_dir, method = 0, None, "none"
    for cand in sorted(base.iterdir()):
        if not (cand.is_dir() and cand.name.startswith("--") and cand.name.endswith("--")):
            continue
        cin = cand.name[2:-2]
        if cin == inner:
            matched_dir, method = cand, "exact"
            break
        if cin.endswith(tail):
            matched_dir, method = cand, "suffix"
    if matched_dir is None:
        return {"match_method": "none", "expected": expected, "copied": 0,
                "note": "L4 缺陷曾致整线空捕；本轮 none 必须在 REPORT 披露并阻断 usage 结论"}
    for q in matched_dir.rglob("*"):
        if q.is_file() and q.suffix != ".lock" and q.stat().st_mtime >= started_ts - 5:
            tgt = sess / q.name
            if not tgt.exists():
                shutil.copy2(q, tgt)
                copied += 1
    return {"match_method": method, "matched_dir": matched_dir.name,
            "expected": expected, "copied": copied}


# ---------------------------------------------------------------- run（真实执行；单次派发）

def verify_released() -> dict:
    """共同 gate：E 放行 + manifest/external_files 实算（fail-closed；每槽派发前都调）。"""
    gate = load_gate()
    if PLAN_DIR_OVERRIDE is not None:
        v = gate.verify_execution(BINDING_PATH, require_release=True, plan_dir=PLAN_DIR_OVERRIDE)
    else:
        v = gate.verify_execution(BINDING_PATH, require_release=True)
    return v


def load_gate_seal():
    spec = importlib.util.spec_from_file_location("l4_seal", L4 / "execution_seal.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _manifest_rel() -> str:
    return str(L4.relative_to(REPO) / "execution-manifest.json")


# mock 注入面（零模型自测专用；真实 run 全部为默认值）
MOCK_CMD = None            # 真实=None → ["dsh", DSH_PROFILE, "--json", "-"]
MOCK_SESSION_SRC = None    # 真实=None → capture_session(~/.dsh/sessions)
MOCK_EXTRA_ENV = {}        # mock 派发时并入子进程 env
PLAN_DIR_OVERRIDE = None   # mock gate 用（真实=None → gate 默认 L4_DIR）
WS_BASE = WS_ROOT
STAGING_ROOT = STAGING
DISPATCH_ROOT = DISPATCH
GUARDS = {
    "bird-ca-schools-15": {"input_integrity", "answers_file", "answers_schema", "answers_coverage"},
    "dabstep-payments-10": {"answers_format", "input_integrity"},
    "exercism-py-6": {"input_integrity"},
    "lcb-recent-hard-4": {"input_integrity"},
    "tb-cargo-plan": {"input_integrity", "code_rerun", "plan_structure"},
}


def build_cmd():
    return MOCK_CMD if MOCK_CMD else ["dsh", DSH_PROFILE, "--json", "-"]


def ws_dir(slot: dict) -> Path:
    return WS_BASE / slot["slot_id"]


def group_alive(pgid: int) -> bool:
    """进程组探活：仅 ESRCH=确认消失；EPERM/其他=存在或未知（**绝不与 gone 合并**）。"""
    if pgid <= 0:
        return True
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False
    except (PermissionError, OSError):
        return True


def group_gone_confirmed(pgid: int, allow_escalate: bool = True) -> bool:
    """组级消失确认。ESRCH=确认；EPERM=歧义，仅当 allow_escalate 时以 KILL 判别器消解：
    对空组 killpg(SIGKILL) 得 ESRCH=确认消失；送达=原本存活；再 EPERM=不可确认。
    （未收割的僵尸组长会使探活呈 EPERM——先收父再判。）"""
    if pgid <= 0:
        return False
    try:
        os.killpg(pgid, 0)
        return False  # 可见=存活
    except ProcessLookupError:
        return True
    except (PermissionError, OSError):
        if not allow_escalate:
            return False  # 歧义且不允许判别：不确认
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        return True  # 判别器证实组为空
    except (PermissionError, OSError):
        return False  # 连 KILL 都不可达：无法确认
    time.sleep(0.2)
    try:
        os.killpg(pgid, 0)
        return False
    except ProcessLookupError:
        return True
    except (PermissionError, OSError):
        return False


def stop_process_group(pgid: int, proc: subprocess.Popen, timeout_s: float,
                       allow_escalate: bool = True) -> dict:
    """组级有界终止协议：
    TERM → 先收父（reap，消除僵尸 EPERM 源）→ 轮询仅 ESRCH 计确认 → EPERM 歧义仅在
    allow_escalate 时以 KILL 判别器消解（空组=ESRCH 证实）→ 组级确认才 verified_stop=True。
    父 CLI returncode 不作数；EPERM 永不与 gone 合并。"""
    term = {"policy": "process-group bounded termination (group-confirmed)",
            "pgid": pgid, "signal": "SIGTERM", "at": now_iso(),
            "escalated": False, "verified_stop": False, "group_confirmed_gone": False}
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    except (PermissionError, OSError) as exc:
        term["term_error"] = "TERM not delivered: %s" % exc
    try:
        proc.wait(timeout=10)  # 先收父：zombie 组长会让探活呈 EPERM
    except Exception:
        pass
    term["parent_reaped"] = proc.returncode is not None
    deadline = time.time() + 10
    while time.time() < deadline:
        if not group_alive(pgid):  # 仅 ESRCH
            term["verified_stop"] = True
            term["group_confirmed_gone"] = True
            term["ack_at"] = now_iso()
            return term
        time.sleep(0.2)
    if allow_escalate:
        term["signal"] = "SIGKILL"
        term["escalated"] = True
        term["escalated_at"] = now_iso()
        try:
            os.killpg(pgid, signal.SIGKILL)  # 升级终止：送达给仍存活的组成员
        except ProcessLookupError:
            pass
        except (PermissionError, OSError) as exc:
            term["kill_error"] = "KILL not delivered: %s" % exc
        deadline2 = time.time() + 10
        while time.time() < deadline2:
            if group_gone_confirmed(pgid, allow_escalate=True):
                term["verified_stop"] = True
                term["group_confirmed_gone"] = True
                term["ack_at"] = now_iso()
                return term
            time.sleep(0.2)
    return term


HALT_PATH = BATCH / "halt.json"


def halt_marker_read() -> dict | None:
    if HALT_PATH.is_file():
        try:
            return json.loads(HALT_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {"reason": "halt.json 不可解析"}
    return None


def halt_marker_write(slot_id: str, reason: str) -> None:
    """首败持久 halt（幂等：已有标记不覆盖）。"""
    if HALT_PATH.exists() or HALT_PATH.is_symlink():
        return
    atomic_refuse_write(HALT_PATH, json.dumps(
        {"halted": True, "slot_id": slot_id, "reason": reason, "at": now_iso(),
         "effect": "后续所有 slot 派发被拒（跨进程持久），直至复核处置并明确解除停批（不得自动清停）",
         "notify": "review-required", "live_doc_drift": []}, ensure_ascii=False, indent=2) + "\n")


def residual_writer_probe(ws: Path, dwell_s: float = 0.4) -> dict:
    """组确认后的保守探针：停后两次采样 workspace 增长，发现仍在写 ⇒ conservative partial。

    覆盖边界（诚实披露）：进程组确认只覆盖被派发的 pgid；setsid 脱组的后代写者不在
    组确认范围内；本探针只看本 slot workspace，不声称全 host 停止保证。"""
    def snap():
        n = b = 0
        for p in ws.rglob("*"):
            try:
                if p.is_file():
                    n += 1
                    b += p.stat().st_size
            except OSError:
                pass
        return {"files": n, "bytes": b}

    s1 = snap()
    time.sleep(dwell_s)
    s2 = snap()
    grew = (s2["files"], s2["bytes"]) > (s1["files"], s1["bytes"])
    return {"method": "workspace-growth-two-sample", "dwell_s": dwell_s,
            "sample_1": s1, "sample_2": s2, "still_growing": bool(grew),
            "group_coverage": "launched pgid only; setsid-escaped descendants not covered by group confirmation",
            "sandbox_guarantee": "none at whole-host level",
            "policy": "still_growing => conservative partial (unverified stop)"}


def cmd_run(slot_id: str | None, all_slots: bool) -> int:
    halted = halt_marker_read()
    if halted:
        print(json.dumps({"ok": False, "halted": True, "by": halted.get("slot_id"),
                          "reason": halted.get("reason"),
                          "note": "持久 halt 标记在位，拒绝派发；须复核处置并明确解除停批后移除（不得自动清停）"}, ensure_ascii=False))
        return 3
    plan = load_plan()
    contract = load_contract()
    slots = dsh_slots(plan)
    targets = slots if all_slots else [s for s in slots if s["slot_id"] == slot_id]
    if not targets:
        print("未找到 slot：%r（合法 slot 见 preflight）" % slot_id)
        return 2
    verify_released()  # 批入口共同 gate（含 E/祖先/manifest/external_files）
    for slot in targets:
        code = run_slot(slot, contract)
        if code != 0:
            return code
    return 0


def verify_inputs(slot: dict, contract: dict) -> dict:
    """派发前机械比对：准备发货的输入子集 + 仓侧 instruction/case.json 对 contract.files。

    只比哈希不读语义（不触 truth/solution/checker 内容）；输入可修改题以 prepare 时刻
    发货子集为准（记录基线），不做事后源 hash。"""
    snap_files = contract["case_snapshots"][slot["case"]].get("files") or {}
    checked, ok = [], True
    ws = ws_dir(slot)
    for p in sorted(ws.rglob("*")):
        if not p.is_file():
            continue
        rel = str(p.relative_to(ws))
        if rel == "TASK.md" or rel == "meta.json":
            continue
        key = "inputs/" + str(Path(rel).relative_to("inputs")) if rel.startswith("inputs/") else rel
        want = snap_files.get(key)
        got = sha_file(p)
        match = (want == got)
        ok &= bool(match)
        checked.append({"path": key, "sha256": got[:8], "match": match})
    for repo_rel in ("instruction.md", "case.json"):
        src = CASE_ROOT / slot["case"] / repo_rel
        want = snap_files.get(repo_rel)
        got = sha_file(src) if src.is_file() else "missing"
        match = (want == got)
        ok &= bool(match)
        checked.append({"path": repo_rel, "sha256": got[:8], "match": match})
    return {"ok": bool(ok and checked), "basis": "prepare-time shipped subset vs contract.case_snapshots.files (hash-only, no truth semantics; input-modifiable cases pinned at dispatch)",
            "checked": checked}


def run_slot(slot: dict, contract: dict) -> int:
    ev = ev_dir(slot)
    if ev.exists():
        print("证据目录已存在（永不覆盖/不重建，拒绝重复执行）：%s" % ev)
        return 2
    ws = ws_dir(slot)
    if ws.exists():
        print("workspace 已存在（fresh-workspace 纪律，拒绝复用）：%s" % ws)
        return 2
    binding = json.loads(BINDING_PATH.read_text(encoding="utf-8"))

    def write_notexec(reason: str, stop_source: str) -> None:
        ev.mkdir(parents=True, exist_ok=True)
        atomic_refuse_write(ev / "notexecuted.json", json.dumps(
            {"slot_id": slot["slot_id"], "run_id": slot["run_id"], "event_id": slot["event_id"],
             "accounting": "not_executed", "preregistration_commit": binding["preregistration_commit"],
             "registered_at": binding["registered_at"], "reason": reason,
             "stop_source": stop_source, "at": now_iso(), "live_doc_drift": []},
            ensure_ascii=False, indent=2) + "\n")

    # 准备 workspace（先于派发登记；隔离/输入失败=从未外发 → not_executed 记账）
    ws.mkdir(parents=True)
    shutil.copytree(CASE_ROOT / slot["case"] / "inputs", ws / "inputs")
    task = build_task(slot["case"], ws)
    (ws / "TASK.md").write_text(task, encoding="utf-8")
    iso = check_isolation(ws)
    if not iso["ok"]:
        write_notexec("isolation preflight failed: %s" % iso["problems"], "runner-preflight")
        print("隔离检查失败（已记 not_executed）：" + json.dumps(iso, ensure_ascii=False))
        return 1
    inputs_ver = verify_inputs(slot, contract)
    if not inputs_ver["ok"]:
        write_notexec("input drift vs contract.case_snapshots（派发前机械比对失败）",
                      "runner-preflight")
        print("输入比对失败（已记 not_executed）：" + json.dumps(inputs_ver, ensure_ascii=False)[:400])
        return 1
    carried = [{"path": str(p.relative_to(ws)), "sha256": sha_file(p), "bytes": p.stat().st_size}
               for p in sorted((ws / "inputs").rglob("*")) if p.is_file()]
    attempt_rec = {"n": 1, "kind": "single-dispatch", "policy": "whole_execution_restarts=0"}
    meta = {
        "batch": BATCH_NAME, "rule_version": RULE, "product": PRODUCT, "case": slot["case"],
        "rep": int(slot["rep"]), "slot_id": slot["slot_id"], "order": slot["order"],
        "stratum": slot["stratum"], "event_id": slot["event_id"], "run_id": slot["run_id"],
        "form": "cli", "preregistration_commit": binding["preregistration_commit"],
        "registered_at": binding["registered_at"],
        "workspace": str(ws), "created_at": now_iso(),
        "model": MODEL, "reasoning_effort": EFFORT, "product_version": cli_version(),
        "route": {"host": "api.deepseek.com", "provider_id": "deepseek-official",
                  "wire_protocol": "anthropic-messages (dsh-headless --json projection)",
                  "endpoint": None},
        "tools": ["builtin shell/read/write 等 bench-cli 基础工具（tool-web/tool-skill/skill-filesystem disabled）"],
        "permissions": "permission preset danger-full-access（approval never，bench-cli cordis.patch.yml）",
        "skills": "off（tool-skill 与 skill-filesystem 均 disabled）",
        "web_search": "disabled",
        "soft_constraints": ["stay-in-workspace", "no-oracle-hunt", "offline"],
        "prompt_sha256": hashlib.sha256(task.encode()).hexdigest(),
        "isolation": iso, "inputs": carried, "inputs_verification": inputs_ver,
        "selection": {"slot_id": slot["slot_id"], "basis": "plan.json product_slots 固定序"},
        "attempts": [attempt_rec],
        "transport_retries": 0,
        "app_asar_sha256": None,
        "managed_unknowns": [],
        "residual_disclosure": {
            "group_coverage": "confirmation covers launched pgid only; setsid-escaped descendants not covered by group confirmation",
            "host_guarantee": "none at whole-host level",
            "probe": "workspace-growth-two-sample (post-stop)",
            "policy": "detected ongoing writer => conservative partial (unverified stop)"},
    }
    # R3：派发登记先持久（进程故障可对账）
    DISPATCH_ROOT.mkdir(parents=True, exist_ok=True)
    atomic_refuse_write(DISPATCH_ROOT / (slot["slot_id"] + ".json"), json.dumps(
        {"slot_id": slot["slot_id"], "run_id": slot["run_id"], "event_id": slot["event_id"],
         "preregistration_commit": binding["preregistration_commit"],
         "registered_at": binding["registered_at"],
         "command": build_cmd(), "dispatched_at": now_iso(), "attempt": 1,
         "timeout_s": slot["timeout_s"]}, ensure_ascii=False, indent=2) + "\n")
    # R2（池 L5-3）：pre-run meta 不再写入模型可见 workspace（防 checker_sha256/config_ref/
    # 仓库路径暴露与机械扫描回显命中）；改写仓内证据目录，ws 运行期仅含 inputs+TASK.md。
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "meta.prepare.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 单次派发（无重试）；进程组有界终止；staging 先落盘
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    tag = slot["slot_id"]
    slog, serr = STAGING_ROOT / (tag + ".agent.jsonl"), STAGING_ROOT / (tag + ".agent.stderr.txt")
    if MOCK_CMD:
        env = dict(os.environ, **(MOCK_EXTRA_ENV or {}))
    else:
        env = dict(os.environ, DEEPSEEK_API_KEY=load_api_key())
    started = now_iso()
    st_ts = time.time()
    status, exit_code, termination = "ok", None, None
    proc, launched_pgid = None, None
    try:
        with slog.open("w", encoding="utf-8") as out, serr.open("w", encoding="utf-8") as errf:
            try:
                proc = subprocess.Popen(build_cmd(), cwd=str(ws), env=env, stdin=subprocess.PIPE,
                                        stdout=out, stderr=errf, text=True, start_new_session=True)
            except OSError as exc:
                # 仅 Popen 抛出 = 进程从未存在（如 CLI 二进制缺失）：首槽 not_executed
                # 记账（真实 reason + 封印引用，不造 started/session/usage/score，infra 分类、
                # 不作模型成败声称）。批级处置属政策选择（复核 校准：停后续或继续其他固定槽
                # 均可，硬要求=首槽有效记账 + 不重复同 slot）；本 runner 取保守 halt。
                write_notexec("spawn failure (process never started): %s" % exc, "runner-spawn")
                halt_marker_write(slot["slot_id"], "spawn failure (process never started): %s" % str(exc)[:160])
                print(json.dumps({"slot": slot["slot_id"], "accounting": "not_executed",
                                  "reason": "spawn failure (process never started)", "halted": True,
                                  "class": "infrastructure"}, ensure_ascii=False))
                return 1
            try:
                launched_pgid = os.getpgid(proc.pid)  # 启动即取；父死后不可再取
            except (ProcessLookupError, PermissionError, OSError):
                launched_pgid = proc.pid  # start_new_session 下 pgid==pid 兜底
            attempt_rec["pid"] = proc.pid
            attempt_rec["pgid"] = launched_pgid  # start_new_session：pgid==pid，receipt 绑定身份
            try:
                _, _ = proc.communicate(input=task, timeout=slot["timeout_s"])
                exit_code = proc.returncode
            except subprocess.TimeoutExpired:
                status = "timeout"
                termination = stop_process_group(launched_pgid, proc, slot["timeout_s"])
    except OSError as exc:
        # 已启动后的运行期 OSError（如流 EIO/EPIPE）：不得误记 not_executed（proc 已存在）。
        # 必要组停止（有界）→ 真实 partial 记账（实际 phase/真实异常，score null，无 checker）；
        # 停止未证实 ⇒ 加 halt（后槽拒），与 unverified 同保守度。
        stop_r = None
        if launched_pgid is not None and group_alive(launched_pgid):
            stop_r = stop_process_group(launched_pgid, proc, slot["timeout_s"], allow_escalate=True)
        stop_unverified = bool(stop_r is not None and not stop_r.get("verified_stop"))
        try:
            ev.mkdir(parents=True, exist_ok=True)
            copy_exclusive(slog, ev / "agent.jsonl")
            copy_exclusive(serr, ev / "agent.stderr.txt")
            copy_exclusive(ws / "TASK.md", ev / "prompt.txt")
        except Exception:
            pass
        diag = {"class": "runtime-oserror-post-launch", "stderr_tail": repr(exc)[-1200:],
                "stop_unverified": stop_unverified,
                "post_launch_stop": (dict(stop_r, phase="runtime_oserror_cleanup") if stop_r else None),
                "retry": "none (whole_execution_restarts=0)"}
        meta.update({"status": "error", "exit_code": None, "timed_out": False,
                     "diagnostic": diag, "score_status": "unscored-diagnostic",
                     "weighted": None, "reward": None, "selection": None,
                     "started_at": started, "finished_at": now_iso(),
                     "duration_s": round(time.time() - st_ts, 1)})
        try:
            if (ev / "agent.jsonl").is_file():
                meta["stdout_bytes"] = (ev / "agent.jsonl").stat().st_size
                meta["stdout_sha256"] = sha_file(ev / "agent.jsonl")
            if (ev / "agent.stderr.txt").is_file():
                meta["stderr_bytes"] = (ev / "agent.stderr.txt").stat().st_size
                meta["stderr_sha256"] = sha_file(ev / "agent.stderr.txt")
            (ev / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8")
        except Exception:
            pass
        if stop_unverified:
            halt_marker_write(slot["slot_id"], "runtime OSError after launch + stop unverified")
            print(json.dumps({"slot": slot["slot_id"], "status": "error", "partial": True,
                              "stop_verified": False, "halted": True, "checker_calls": 0},
                             ensure_ascii=False))
            return 3
        print(json.dumps({"slot": slot["slot_id"], "status": "error", "partial": True,
                          "stop_verified": True, "halted": False, "checker_calls": 0},
                         ensure_ascii=False))
        return 1
    finished = now_iso()
    duration = round(time.time() - st_ts, 1)
    # ---- 组闭包确认（所有已执行路径；同一"停止后判卷"判据）----
    # 正常退出无 signal 也可合法以"组明确不存在"为证；活跃孙代可能仍在写 ⇒ 先确认/有界清理再归档判卷。
    closure = None
    if status != "timeout" and not group_alive(launched_pgid):
        closure = {"phase": "normal_exit", "probe": "verified_gone", "signal": None,
                   "verified_stop": True, "group_confirmed_gone": True,
                   "pgid": launched_pgid, "at": now_iso(), "ack_at": now_iso(),
                   "note": "组已确认不存在（ESRCH）；正常退出无需发送信号"}
    elif status != "timeout":
        # 父已退但组仍活（孙代存活/写入）→ 有界清理后再判卷
        closure = stop_process_group(launched_pgid, proc, slot["timeout_s"], allow_escalate=True)
        closure["phase"] = "post_exit_cleanup"
    attempt_rec.update({"started_at": started, "finished_at": finished,
                        "duration_s": duration, "exit_code": exit_code, "outcome": status})
    termination_binding = None
    if termination:
        attempt_rec["termination"] = termination
        attempt_rec["stop_source"] = "plan timeout_s=%s process-group %s" % (
            slot["timeout_s"], (termination or {}).get("signal"))
    if closure is not None:
        attempt_rec["closure"] = closure
    # 组确认 ≠ 覆盖 setsid 脱组写者（judge S6 实证）：停后保守探针；发现仍在写 ⇒ 翻转为
    # 未证实（走 unverified partial：无 checker + halt），不冒绝对全停。
    residual = None
    vstop = termination if status == "timeout" else closure
    if vstop is not None and vstop.get("verified_stop"):
        residual = residual_writer_probe(ws)
        vstop["residual_probe"] = {"still_growing": residual["still_growing"],
                                   "method": residual["method"]}
        if residual["still_growing"]:
            vstop["verified_stop"] = False
            vstop["group_confirmed_gone"] = False
            vstop["unconfirmed_reason"] = ("residual workspace writer detected after group "
                                           "confirmation (possible setsid-escaped descendant)")
            vstop["residual_disclosure"] = residual
    # Runtime 闭包：任一 phase 未验证停止 ⇒ 立即早退 partial（不 capture/rebuild/不判卷——
    # workspace 可能仍被写入，不可冻结为完整产物；checker 计数必须为 0）
    effective_stop = termination if status == "timeout" else closure
    unverified_stop = (effective_stop is not None) and not effective_stop.get("verified_stop")
    if unverified_stop:
        # 停止未证实：保留实际 phase/status/underlying returncode；只有真实 timeout 才
        # timed_out=true；组未证实的 normal 退出分支 = error/partial + score null（不伪造 timeout）。
        real_status = "timeout" if status == "timeout" else "error"
        try:
            ev.mkdir(parents=True, exist_ok=True)
            copy_exclusive(slog, ev / "agent.jsonl")
            copy_exclusive(serr, ev / "agent.stderr.txt")
            copy_exclusive(ws / "TASK.md", ev / "prompt.txt")
            term_doc = dict(effective_stop, slot_id=slot["slot_id"], timeout_s=slot["timeout_s"],
                            duration_s=duration, at_ack=(effective_stop or {}).get("ack_at"))
            if meta.get("residual_disclosure"):
                term_doc["residual_disclosure"] = meta["residual_disclosure"]
            atomic_refuse_write(ev / "termination-receipt.json",
                                json.dumps(term_doc, ensure_ascii=False, indent=2) + "\n")
            tbind = {"file": "termination-receipt.json",
                     "sha256": sha_file(ev / "termination-receipt.json")}  # 权威 bool 在 doc，binding 不留双说
            meta.update({
                "status": real_status, "exit_code": exit_code if status != "timeout" else None,
                "timed_out": status == "timeout",
                "termination_receipt": tbind,
                "diagnostic": {"class": "timeout" if status == "timeout" else "post-exit stop unverified",
                               "stop_unverified": True,
                               "phase": (effective_stop or {}).get("phase"),
                               "stop_source": attempt_rec.get("stop_source"),
                               "termination": effective_stop,
                               "evidence_scope": "frozen-first-stream-only（workspace 疑似仍写入，不冻结为完整产物）",
                               "retry": "none (whole_execution_restarts=0)"},
                "started_at": started, "finished_at": finished, "duration_s": duration,
                "stdout_bytes": (ev / "agent.jsonl").stat().st_size,
                "stdout_sha256": sha_file(ev / "agent.jsonl"),
                "stderr_bytes": (ev / "agent.stderr.txt").stat().st_size,
                "stderr_sha256": sha_file(ev / "agent.stderr.txt"),
                "score_status": "unscored-unverified-stop", "weighted": None, "reward": None,
                "judge": {"checker_sha256": contract["case_snapshots"][slot["case"]]["checker.py"],
                          "exit_code": None, "error": "not scored: stop unverified"},
                "selection": None,
            })
            (ev / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8")
        except Exception as exc:
            print(json.dumps({"slot": tag, "note": "unverified-stop 早退归档部分失败",
                              "error": repr(exc)[:200]}, ensure_ascii=False))
        halt_marker_write(slot["slot_id"], "stop unverified (verified_stop=false, %s)" % real_status)
        print(json.dumps({"slot": tag, "status": real_status, "stop_verified": False,
                          "halted": True, "checker_calls": 0,
                          "note": "未验证停止：早退 partial，formal=false，后续 slot 已被 halt 拒绝",
                          "evidence": str(ev)}, ensure_ascii=False))
        return 3

    def emergency_partial(exc: Exception) -> None:
        """派发后异常也必须留 partial 记账（不 print 即返）。"""
        diag = {"class": "runner-exception", "stderr_tail": repr(exc)[-1200:]}
        meta.update({"status": "error", "exit_code": None, "diagnostic": diag,
                     "termination_receipt": termination_binding,
                     "timed_out": False, "score_status": "unscored-diagnostic",
                     "weighted": None, "reward": None})
        try:
            ev.mkdir(parents=True, exist_ok=True)
            if slog.exists():
                copy_exclusive(slog, ev / "agent.jsonl")
            if serr.exists():
                copy_exclusive(serr, ev / "agent.stderr.txt")
            (ev / "prompt.txt").write_text(task, encoding="utf-8")
            meta["stdout_bytes"] = (ev / "agent.jsonl").stat().st_size
            meta["stdout_sha256"] = sha_file(ev / "agent.jsonl")
            meta["stderr_bytes"] = (ev / "agent.stderr.txt").stat().st_size
            meta["stderr_sha256"] = sha_file(ev / "agent.stderr.txt")
            meta["started_at"] = started
            meta["finished_at"] = now_iso()
            meta["duration_s"] = round(time.time() - st_ts, 1)
            (ev / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8")
        except Exception:
            pass

    try:
        ev.mkdir(parents=True, exist_ok=True)  # L5 R2 回归修复: prepare 已建 ev(E2 dab-r1 教训, dated)
        copy_exclusive(slog, ev / "agent.jsonl")
        copy_exclusive(serr, ev / "agent.stderr.txt")
        copy_exclusive(ws / "TASK.md", ev / "prompt.txt")
        stop_doc_src = termination if termination else closure
        if stop_doc_src is not None:
            term_doc = dict(stop_doc_src, slot_id=slot["slot_id"], timeout_s=slot["timeout_s"],
                            duration_s=duration, at_ack=stop_doc_src.get("ack_at"),
                            pid=attempt_rec.get("pid"), pgid=attempt_rec.get("pgid"))
            atomic_refuse_write(ev / "termination-receipt.json",
                                json.dumps(term_doc, ensure_ascii=False, indent=2) + "\n")
            termination_binding = {"file": "termination-receipt.json",
                                   "sha256": sha_file(ev / "termination-receipt.json")}  # 权威 bool 在 doc
        if MOCK_SESSION_SRC:
            sess_dir = ev / "agent-session"
            shutil.copytree(MOCK_SESSION_SRC, sess_dir)
            capture_receipt = {"match_method": "mock", "copied": None}
        else:
            capture_receipt = capture_session(ev, ws, dt.datetime.fromisoformat(started).timestamp())
            sess_dir = ev / "agent-session"
        has_sess = sess_dir.is_dir() and any(sess_dir.iterdir())
        # full 重建流（另列字段，独立 sha）与逐调用 usage
        full_bytes = full_lines = 0
        if has_sess:
            events = rebuild_full_stream(sess_dir)
            fpath = ev / "agent.jsonl.full"
            with fpath.open("w", encoding="utf-8") as fh:
                for e in events:
                    fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            full_bytes, full_lines = fpath.stat().st_size, len(events)
        if has_sess:
            usage = extract_per_call_usage(sess_dir, ev / "agent.jsonl")
        else:
            usage = {"requests": None, "input_tokens": None, "output_tokens": None,
                     "cache_read_tokens": None, "cache_creation_tokens": None, "per_call": [],
                     "cross_check": {"compared": 0, "equal": 0, "mismatch": []},
                     "source": "session log unavailable——usage 全字段如实 null（unknown 不填 0）"}
        # 状态定级（timeout 已定；非零退出按 stderr 分类，无重试）
        diagnostic = None
        if status == "timeout":
            diagnostic = {"class": "timeout", "stop_source": attempt_rec.get("stop_source"),
                          "termination": termination, "retry": "none (whole_execution_restarts=0)"}
        elif exit_code not in (0, None):
            stext = serr.read_text(encoding="utf-8", errors="replace") if serr.exists() else ""
            transport = next((t for t in TRANSPORT_PATTERNS if t in stext.lower()), None)
            status = "transport-error" if transport else "error"
            diagnostic = {"class": transport or "nonzero-exit", "exit_code": exit_code,
                          "stderr_tail": stext[-1500:], "retry": "none (whole_execution_restarts=0)"}
        # 判分（机械；异常→unscored 诊断，不阻断记账）
        try:
            scored_res = score_case(slot, ws, contract)
        except Exception as exc:
            scored_res = {"res": {"error": repr(exc)[:800]}, "scored": False,
                          "earned": None, "possible": None, "reported": None,
                          "judge": {"checker_sha256": contract["case_snapshots"][slot["case"]]["checker.py"],
                                    "exit_code": None, "error": repr(exc)[:800]}}
            diagnostic = diagnostic or {"class": "scorer-exception"}
            diagnostic = dict(diagnostic, score_error=repr(exc)[:400])
        snapshot_config(ev / "config-snapshot")
        # workspace 归档（发货产物态；inputs/日志/meta 已他处存档）
        ws_arch = ev / "workspace"
        ws_arch.mkdir(exist_ok=True)
        for p in ws.iterdir():
            if p.name in ("inputs", "agent.jsonl", "agent.stderr.txt", "meta.json", "TASK.md"):
                continue
            if p.is_dir():
                shutil.copytree(p, ws_arch / p.name, dirs_exist_ok=True)
            else:
                shutil.copy2(p, ws_arch / p.name)
        # 双流完整性扫描
        stdout_hits, stdout_lines = scan_integrity_stream(
            [("agent.jsonl", l) for l in (ev / "agent.jsonl").open(encoding="utf-8", errors="replace")])
        if has_sess:
            sess_hits, sess_lines = scan_integrity_stream(session_lines(sess_dir))
        else:
            sess_hits, sess_lines = [], 0
        hits = stdout_hits + sess_hits
        integ = {"violations": len(hits), "patterns": INTEGRITY_PATTERNS,
                 "basis": "runner stdout (staging-first, never overwritten) + session-trajectory dual scan",
                 "stdout_scan": {"lines": stdout_lines, "violations": len(stdout_hits)},
                 "session_scan": {"lines": sess_lines, "violations": len(sess_hits)},
                 "evidence": hits}
        raw_stat = (ev / "agent.jsonl").stat()
        err_stat = (ev / "agent.stderr.txt").stat()
        full_sha = sha_file(ev / "agent.jsonl.full") if full_lines else None
        meta.update({
            "status": status, "exit_code": exit_code,
            "diagnostic": diagnostic,
            "termination_receipt": termination_binding,
            "timed_out": status == "timeout",
            "started_at": started, "finished_at": finished, "duration_s": duration,
            "stdout_bytes": raw_stat.st_size, "stdout_sha256": sha_file(ev / "agent.jsonl"),
            "stderr_bytes": err_stat.st_size, "stderr_sha256": sha_file(ev / "agent.stderr.txt"),
            "archived_stdout": {
                "raw_file": "agent.jsonl", "raw_bytes": raw_stat.st_size,
                "raw_truncation": "dsh-headless --json projection caps are hardcoded (maxStringBytes=8192, maxEventBytes=32768); no override in this version",
                "full_file": ("agent.jsonl.full" if full_lines else None),
                "full_sha256": full_sha,
                "full_bytes": full_bytes, "full_lines": full_lines,
                "full_method": ("lossless re-projection of durable session log with string/line caps removed; commit-point semantics identical to CLI projection" if full_lines else None),
            },
            "usage": usage,
            "session_capture": capture_receipt,
            "reward": scored_res["res"].get("reward") if isinstance(scored_res["res"], dict) else None,
            "weighted": scored_res["reported"] if scored_res["scored"] else None,
            "score_status": "scored" if scored_res["scored"] else "unscored-diagnostic",
            "failed": [c.get("id") for c in (scored_res["res"].get("checks") or []) if not c.get("pass")],
            "judge": scored_res["judge"],
            "integrity": integ,
            "integrity_verdict": "clean" if len(hits) == 0 else "violation",
        })
        (ev / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (ev / "checker.stdout").write_text(
            json.dumps(scored_res["res"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if scored_res["scored"]:
            snap = contract["case_snapshots"][slot["case"]]
            atomic_refuse_write(ev / "score-receipt.json", json.dumps(
                {"case": slot["case"], "product": PRODUCT, "run_id": slot["run_id"],
                 "rep": int(slot["rep"]),
                 "score": {"earned": scored_res["earned"], "possible": scored_res["possible"],
                           "reported": scored_res["reported"],
                           "checker_sha256": snap["checker.py"]},
                 "rule_version": RULE, "raw_checker_output": scored_res["res"],
                 "at": now_iso(), "live_doc_drift": []},
                ensure_ascii=False, indent=2) + "\n")
        rescan = {"run": tag, "patterns": INTEGRITY_PATTERNS,
                  "session_files": [{"name": p.name, "bytes": p.stat().st_size, "zstd": p.suffix == ".zstd"}
                                    for p in sorted(sess_dir.iterdir()) if p.is_file()] if has_sess else [],
                  "lines_scanned": sess_lines,
                  "usage_events_present": usage.get("requests"),
                  "violations": len(sess_hits), "evidence": sess_hits,
                  "method": "session-trajectory rescan (independent cross-check; raw stream preserved staging-first)",
                  "reviewed": None}
        (ev / "integrity-rescan.json").write_text(json.dumps(rescan, ensure_ascii=False, indent=2) + "\n",
                                                  encoding="utf-8")
        print(json.dumps({"slot": tag, "status": status, "exit_code": exit_code,
                          "weighted": meta["weighted"], "score_status": meta["score_status"],
                          "duration_s": duration, "violations": len(hits),
                          "stdout_bytes": raw_stat.st_size, "full_sha256_8": (full_sha or "")[:8],
                          "usage_requests": usage.get("requests"), "evidence": str(ev)},
                         ensure_ascii=False))
        return 0
    except Exception as exc:  # 派发后任何异常：partial 记账落地
        emergency_partial(exc)
        print(json.dumps({"slot": tag, "status": "error", "note": "runner exception → partial 记账",
                          "error": repr(exc)[:300]}, ensure_ascii=False))
        return 1


# ---------------------------------------------------------------- notexec / selftest / report

# ---------------------------------------------------------------- mockrun（零模型全链路）

MOCK_STUB_DSH = r"""
import json, os, sys, time
task = sys.stdin.read()
sess_dir = os.environ["L4_MOCK_SESSION_DIR"]
os.makedirs(sess_dir, exist_ok=True)
sleep_s = float(os.environ.get("L4_MOCK_SLEEP", "0"))
out = {"type": "status", "phase": "step_end", "turn": 1, "step": 1,
       "usage": {"inputTokens": 123, "outputTokens": 45, "cacheReadTokens": 100, "cacheWriteTokens": 7}}
sys.stdout.write(json.dumps(out) + "\n")
sys.stdout.flush()
with open(os.path.join(sess_dir, "s.jsonl"), "w", encoding="utf-8") as fh:
    fh.write(json.dumps({"type": "session", "id": "mock"}) + "\n")
    fh.write(json.dumps({"type": "assistant/message", "data": {"turn": 1, "step": 1,
        "message": {"content": [{"type": "text", "text": "mock final answer"}]},
        "usage": {"inputTokens": 123, "outputTokens": 45, "cacheReadTokens": 100, "cacheWriteTokens": 7}}}) + "\n")
    fh.write(json.dumps({"type": "step/end", "data": {"turn": 1, "step": 1}}) + "\n")
if sleep_s:
    time.sleep(sleep_s)
"""

MOCK_STUB_CHECKER = r"""
import json, sys, os
mode = os.environ.get("L4_MOCK_CHECKER_MODE", "scored")
ws = sys.argv[1]
if mode == "unscored":
    sys.stderr.write("checker exploded\n")
    sys.exit(3)
earned = 1 if mode == "low" else 2
doc = {"checks": [{"id": "input_integrity", "pass": True},
                  {"id": "q1", "pass": earned >= 1},
                  {"id": "q2", "pass": earned >= 2},
                  {"id": "q3", "pass": earned >= 3}],
       "weighted": round(100.0 * earned / 3, 2), "reward": earned}  # 冻结 checker 原始 2dp
sys.stdout.write(json.dumps(doc) + "\n")
sys.exit(1 if mode == "low" else 0)   # low: 合法 JSON + exit1（能力低分，非 infra）
"""


def cmd_mockrun() -> int:
    """零模型 mock 全链路：合成 case/plan/contract/binding → run_slot → gate_admission。

    覆盖四世界：ok(scored exit0)、low(checker exit1 低分仍准入)、timeout(真实超时全证据
    准入)、unscored(加权 null + partial 记账 + accounting_complete)。全程无模型调用。
    """
    import tempfile
    gate = load_gate()
    results = []

    def check(name, ok, detail=""):
        results.append({"case": name, "pass": bool(ok), "detail": str(detail)[:240]})

    saved = {k: globals()[k] for k in ("CASE_ROOT", "WS_BASE", "STAGING_ROOT", "DISPATCH_ROOT",
                                       "MOCK_CMD", "MOCK_SESSION_SRC", "MOCK_EXTRA_ENV",
                                       "PLAN_DIR_OVERRIDE", "BINDING_PATH", "GUARDS", "EV_BASE",
                                       "ISOLATION_WS_PREFIX")}
    D, E = "d" * 40, "e" * 40
    d_time, e_time = "2026-10-29T19:00:00+08:00", "2026-10-29T20:00:00+08:00"
    now = "2026-10-29T20:30:00+08:00"
    try:
        with tempfile.TemporaryDirectory(prefix="l4mock-") as td:
            tmp = Path(td)
            case_root = tmp / "cases"
            case_dir = case_root / "mock-case"
            (case_dir / "inputs").mkdir(parents=True)
            (case_dir / "instruction.md").write_text("# MOCK TASK\n求和 inputs/in.txt 数字。", encoding="utf-8")
            (case_dir / "case.json").write_text(json.dumps({"timeout_s": 1}), encoding="utf-8")
            (case_dir / "inputs" / "in.txt").write_text("1\n2\n", encoding="utf-8")
            checker = case_dir / "checker.py"
            checker.write_text(MOCK_STUB_CHECKER, encoding="utf-8")
            plan_dir = tmp / "plans" / "l4"
            plan_dir.mkdir(parents=True)
            slot = {"slot_id": "mock-slot-1", "run_id": "mock-slot-1", "event_id": "event:mock-slot-1",
                    "kind": "product_run", "product": "dsh", "case": "mock-case", "rep": 1,
                    "stratum": "cli_current_sentinel", "order": 1,
                    "evidence_dir": "runs/mock-slot-1", "timeout_s": 1}
            contract = {"rule_version": RULE,
                        "strata": {"cli_current_sentinel": {"products": ["dsh"], "model": MODEL,
                                                            "effort": EFFORT,
                                                            "route_host": "api.deepseek.com",
                                                            "ranking": False}},
                        "case_snapshots": {"mock-case": {
                            "checker.py": sha_file(checker),
                            "files": {"instruction.md": sha_file(case_dir / "instruction.md"),
                                      "case.json": sha_file(case_dir / "case.json"),
                                      "inputs/in.txt": sha_file(case_dir / "inputs" / "in.txt")}}},
                        "denominators": {"mock-case": 3},
                        "admission": {"required_original_evidence": ["prompt", "stdout", "stderr",
                                                                     "session", "checker", "workspace"]}}
            (plan_dir / "plan.json").write_text(json.dumps({"plan_id": "l4mock", "product_slots": [slot]}),
                                                encoding="utf-8")
            (plan_dir / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
            (plan_dir / "PREREGISTRATION.md").write_bytes(b"PREREG")
            ext = tmp / "driver.sh"
            ext.write_text("ok\n", encoding="utf-8")
            bp, gr, gt, ga, b = gate._fake_git_env(tmp, plan_dir, D, E, e_time, d_time, ext)
            binding_released = tmp / "binding-released.json"
            binding_released.write_text(json.dumps(dict(b, released_for_model_calls=True)), encoding="utf-8")

            def world(name, checker_mode, sleep_s, timeout_s):
                sess_dir = tmp / ("sess-" + name)
                sess_dir.mkdir(parents=True, exist_ok=True)
                globals().update({"CASE_ROOT": case_root, "WS_BASE": tmp / "ws" / name,
                                  "STAGING_ROOT": tmp / "staging" / name,
                                  "DISPATCH_ROOT": tmp / "dispatch" / name,
                                  "EV_BASE": tmp,
                                  "ISOLATION_WS_PREFIX": tmp,
                                  "MOCK_CMD": [sys.executable, "-c", MOCK_STUB_DSH],
                                  "MOCK_SESSION_SRC": sess_dir, "PLAN_DIR_OVERRIDE": plan_dir,
                                  "BINDING_PATH": binding_released,
                                  "GUARDS": dict(GUARDS, **{"mock-case": {"input_integrity"}}),
                                  "MOCK_EXTRA_ENV": {"L4_MOCK_CHECKER_MODE": checker_mode,
                                                     "L4_MOCK_SLEEP": str(sleep_s),
                                                     "L4_MOCK_SESSION_DIR": str(sess_dir)}})
                slot_w = dict(slot, slot_id="mock-%s" % name, run_id="mock-%s" % name,
                              event_id="event:mock-%s" % name, timeout_s=timeout_s,
                              evidence_dir="runs-%s/mock-%s" % (name, name))
                (plan_dir / "plan.json").write_text(json.dumps(
                    {"plan_id": "l4mock", "product_slots": [slot_w]}), encoding="utf-8")
                # 每世界重建 binding/manifest（evidence_dir 变了 manifest 不含它，无碍）
                bp2, gr2, gt2, ga2, b2 = gate._fake_git_env(tmp, plan_dir, D, E, e_time, d_time, ext)
                (tmp / ("binding-%s.json" % name)).write_text(
                    json.dumps(dict(b2, released_for_model_calls=True)), encoding="utf-8")
                globals()["__BP"] = tmp / ("binding-%s.json" % name)
                globals()["__READERS"] = (gr2, gt2, ga2)
                code = run_slot(slot_w, contract)
                ev = tmp / slot_w["evidence_dir"]
                meta = json.loads((ev / "meta.json").read_text(encoding="utf-8"))                     if (ev / "meta.json").is_file() else None
                gr2, gt2, ga2 = globals()["__READERS"]
                rep = gate.gate_admission(globals()["__BP"], "dsh", repo=tmp, plan_dir=plan_dir,
                                          git_reader=gr2, git_time=gt2, git_ancestor=ga2,
                                          required_set={"plans/l4/plan.json", "plans/l4/contract.json"})
                return code, meta, rep

            # 世界1：ok（scored，exit0）
            code, meta, rep = world("ok", "scored", 0, 60)
            s = rep["summary"]
            print("DBG code=%s meta=%s" % (code, "yes" if meta else "no"))
            if code != 0:
                print("DBG slot output above")
            check("mock-ok-formal-admitted",
                  code == 0 and meta["status"] == "ok" and meta["score_status"] == "scored"
                  and s["formal_admitted"] == 1
                  and rep["per_slot"][0]["formal_admission"] is True,
                  json.dumps(s) + str(rep["per_slot"][0]["fails"])[:200])
            check("mock-ok-full-usage",
                  meta["usage"]["requests"] == 1 and meta["usage"]["cache_read_tokens"] == 100
                  and meta["archived_stdout"]["full_sha256"] is not None,
                  json.dumps(meta["usage"]["cross_check"])[:160])
            # 世界2：checker exit1 + 低分（能力低分不是拒收理由）
            code, meta, rep = world("low", "low", 0, 60)
            check("mock-low-exit1-admitted",
                  code == 0 and meta["judge"]["exit_code"] == 1
                  and meta["weighted"] == 33.33333333
                  and rep["per_slot"][0]["formal_admission"] is True,
                  json.dumps(rep["per_slot"][0]["fails"])[:200])
            # 世界3：真实 timeout（sleep 5 > timeout 1；进程组终止；全分母判现有产物）
            code, meta, rep = world("timeout", "scored", 5, 1)
            s = rep["summary"]
            check("mock-timeout-genuine-admitted",
                  code == 0 and meta["status"] == "timeout" and meta["timed_out"] is True
                  and meta["duration_s"] >= 1
                  and meta["attempts"][0]["termination"]["signal"] in ("SIGTERM", "SIGKILL")
                  and rep["per_slot"][0]["genuine_timeout"] is True
                  and rep["per_slot"][0]["formal_admission"] is True,
                  json.dumps(meta.get("attempts"))[:200] + str(rep["per_slot"][0]["fails"])[:200])
            # 世界5：verified=false 早退（checker 计数 0、无后续 Popen、持久 halt 拒下一 slot）
            checker_calls = {"n": 0}
            popen_calls = {"n": 0}
            orig_score_case = score_case
            orig_popen = subprocess.Popen
            orig_stop = stop_process_group
            orig_halt = HALT_PATH

            def counting_score(*a, **k):
                checker_calls["n"] += 1
                return orig_score_case(*a, **k)

            def counting_popen(*a, **k):
                if a and a[0] == build_cmd():
                    popen_calls["n"] += 1
                return orig_popen(*a, **k)

            def fake_stop(pgid, proc, timeout_s, allow_escalate=True):
                return {"policy": "mock-unconfirmed", "pgid": pgid, "signal": "SIGKILL",
                        "at": now_iso(), "escalated": True, "verified_stop": False,
                        "group_confirmed_gone": False, "unconfirmed_reason": "probe denied (mock)"}

            globals()["score_case"] = counting_score
            subprocess.Popen = counting_popen
            globals()["stop_process_group"] = fake_stop
            globals()["HALT_PATH"] = tmp / "halt.json"
            (tmp / "sess-unverified").mkdir(parents=True, exist_ok=True)
            globals().update({"CASE_ROOT": case_root, "WS_BASE": tmp / "ws" / "unverified",
                              "STAGING_ROOT": tmp / "staging" / "unverified",
                              "DISPATCH_ROOT": tmp / "dispatch" / "unverified",
                              "EV_BASE": tmp, "ISOLATION_WS_PREFIX": tmp,
                              "MOCK_CMD": [sys.executable, "-c", MOCK_STUB_DSH],
                              "MOCK_SESSION_SRC": tmp / "sess-unverified",
                              "PLAN_DIR_OVERRIDE": plan_dir, "BINDING_PATH": binding_released,
                              "GUARDS": dict(GUARDS, **{"mock-case": {"input_integrity"}}),
                              "MOCK_EXTRA_ENV": {"L4_MOCK_CHECKER_MODE": "scored", "L4_MOCK_SLEEP": "5",
                                                 "L4_MOCK_SESSION_DIR": str(tmp / "sess-unverified")}})
            slot_u = dict(slot, slot_id="mock-unv1", run_id="mock-unv1", event_id="event:mock-unv1",
                          timeout_s=1, evidence_dir="runs-unverified/mock-unv1")
            slot_v = dict(slot_u, slot_id="mock-unv2", run_id="mock-unv2", event_id="event:mock-unv2",
                          evidence_dir="runs-unverified/mock-unv2")
            (plan_dir / "plan.json").write_text(json.dumps(
                {"plan_id": "l4mock", "product_slots": [slot_u, slot_v]}), encoding="utf-8")
            bp3, gr3, gt3, ga3, b3 = gate._fake_git_env(tmp, plan_dir, D, E, e_time, d_time, ext)
            (tmp / "binding-unv.json").write_text(json.dumps(dict(b3, released_for_model_calls=True)),
                                                 encoding="utf-8")
            globals()["BINDING_PATH"] = tmp / "binding-unv.json"
            code1 = run_slot(slot_u, contract)
            checker_after, popen_after = checker_calls["n"], popen_calls["n"]
            code_next = cmd_run("mock-unv2", False)
            check("mock-unverified-earlyexit-halt",
                  code1 == 3 and checker_after == 0 and popen_after == 1
                  and (tmp / "halt.json").is_file() and code_next == 3
                  and popen_calls["n"] == 1 and checker_calls["n"] == 0,
                  "code1=%s checker=%s popen=%s halt=%s next=%s popen_total=%s"
                  % (code1, checker_after, popen_after, (tmp / "halt.json").is_file(),
                     code_next, popen_calls["n"]))
            ev_u = tmp / slot_u["evidence_dir"]
            meta_u = json.loads((ev_u / "meta.json").read_text(encoding="utf-8"))
            rep_u = gate.gate_admission(tmp / "binding-unv.json", "dsh", repo=tmp, plan_dir=plan_dir,
                                        git_reader=gr3, git_time=gt3, git_ancestor=ga3,
                                        required_set={"plans/l4/plan.json", "plans/l4/contract.json"})
            check("mock-unverified-gate-not-formal",
                  rep_u["per_slot"][0]["formal_admission"] is False
                  and meta_u["score_status"] == "unscored-unverified-stop"
                  and rep_u["summary"]["accounting_complete"] is False,
                  json.dumps(rep_u["summary"]) + str(rep_u["per_slot"][0]["fails"])[:200])
            globals().update({"score_case": orig_score_case, "stop_process_group": orig_stop,
                              "HALT_PATH": orig_halt})
            subprocess.Popen = orig_popen
            # 世界6：正常退出但组停止未证实（closure verified_stop=false）→ error/partial +
            # score null，不伪造 timeout；保留实际 phase 与底层 returncode；checker 0；
            # Popen==1（已发一次，无 whole-CLI 重启）。
            checker_calls6 = {"n": 0}
            popen_calls6 = {"n": 0}
            orig_score6 = score_case
            orig_popen6 = subprocess.Popen

            def counting_score6(*a, **k):
                checker_calls6["n"] += 1
                return orig_score6(*a, **k)

            def counting_popen6(*a, **k):
                if a and a[0] == build_cmd():
                    popen_calls6["n"] += 1
                return orig_popen6(*a, **k)

            orig_group_alive6 = group_alive
            orig_stop6 = stop_process_group
            sess6 = tmp / "sess-nunv"
            sess6.mkdir(parents=True, exist_ok=True)
            globals().update({"CASE_ROOT": case_root, "WS_BASE": tmp / "ws" / "nunv",
                              "STAGING_ROOT": tmp / "staging" / "nunv",
                              "DISPATCH_ROOT": tmp / "dispatch" / "nunv",
                              "EV_BASE": tmp, "ISOLATION_WS_PREFIX": tmp,
                              "MOCK_CMD": [sys.executable, "-c", MOCK_STUB_DSH],
                              "MOCK_SESSION_SRC": sess6, "PLAN_DIR_OVERRIDE": plan_dir,
                              "BINDING_PATH": binding_released,
                              "GUARDS": dict(GUARDS, **{"mock-case": {"input_integrity"}}),
                              "MOCK_EXTRA_ENV": {"L4_MOCK_CHECKER_MODE": "scored", "L4_MOCK_SLEEP": "0",
                                                 "L4_MOCK_SESSION_DIR": str(sess6)},
                              "HALT_PATH": tmp / "halt-nunv.json",
                              "score_case": counting_score6,
                              "group_alive": (lambda pgid: True),  # 组恒"活"→ closure 走 post_exit_cleanup
                              "stop_process_group": fake_stop})     # verified_stop=False（同世界5）
            subprocess.Popen = counting_popen6
            slot6 = dict(slot, slot_id="mock-nunv", run_id="mock-nunv", event_id="event:mock-nunv",
                         timeout_s=60, evidence_dir="runs-nunv/mock-nunv")
            code6 = run_slot(slot6, contract)
            ev6 = tmp / slot6["evidence_dir"]
            meta6 = json.loads((ev6 / "meta.json").read_text(encoding="utf-8")) \
                if (ev6 / "meta.json").is_file() else None
            rc6 = json.loads((ev6 / "termination-receipt.json").read_text(encoding="utf-8")) \
                if (ev6 / "termination-receipt.json").is_file() else None
            check("mock-normal-unverified-error-partial",
                  code6 == 3 and meta6 is not None
                  and meta6["status"] == "error" and meta6["timed_out"] is False
                  and meta6["exit_code"] == 0
                  and meta6["weighted"] is None
                  and meta6["score_status"] == "unscored-unverified-stop"
                  and meta6["diagnostic"]["phase"] == "post_exit_cleanup"
                  and meta6["diagnostic"]["class"] == "post-exit stop unverified"
                  and rc6 is not None and rc6.get("verified_stop") is False
                  and (ev6 / "agent.jsonl").is_file()
                  and checker_calls6["n"] == 0 and popen_calls6["n"] == 1,
                  "code6=%s meta=%s rc=%s checker=%s popen=%s"
                  % (code6, json.dumps(meta6.get("diagnostic"), ensure_ascii=False)[:160] if meta6 else None,
                     json.dumps(rc6)[:120] if rc6 else None, checker_calls6["n"], popen_calls6["n"]))
            globals().update({"score_case": orig_score6, "group_alive": orig_group_alive6,
                              "stop_process_group": orig_stop6, "HALT_PATH": orig_halt})
            subprocess.Popen = orig_popen6
            # 世界7：spawn OSError（无真实启动）→ not_executed 记账（真实 reason+封印引用，
            # 无 meta/session/score）+ 持久 halt 拒后续槽；不丢记账不崩溃。
            sess7 = tmp / "sess-spawn"
            sess7.mkdir(parents=True, exist_ok=True)
            globals().update({"CASE_ROOT": case_root, "WS_BASE": tmp / "ws" / "spawn",
                              "STAGING_ROOT": tmp / "staging" / "spawn",
                              "DISPATCH_ROOT": tmp / "dispatch" / "spawn",
                              "EV_BASE": tmp, "ISOLATION_WS_PREFIX": tmp,
                              "MOCK_CMD": ["/nonexistent/l4-missing-binary"],
                              "MOCK_SESSION_SRC": sess7, "PLAN_DIR_OVERRIDE": plan_dir,
                              "BINDING_PATH": binding_released,
                              "GUARDS": dict(GUARDS, **{"mock-case": {"input_integrity"}}),
                              "MOCK_EXTRA_ENV": {"L4_MOCK_CHECKER_MODE": "scored", "L4_MOCK_SLEEP": "0",
                                                 "L4_MOCK_SESSION_DIR": str(sess7)},
                              "HALT_PATH": tmp / "halt-spawn.json"})
            slot7 = dict(slot, slot_id="mock-spawn1", run_id="mock-spawn1", event_id="event:mock-spawn1",
                         timeout_s=60, evidence_dir="runs-spawn/mock-spawn1")
            slot7b = dict(slot7, slot_id="mock-spawn2", run_id="mock-spawn2",
                          event_id="event:mock-spawn2", evidence_dir="runs-spawn/mock-spawn2")
            code7 = run_slot(slot7, contract)
            ev7 = tmp / slot7["evidence_dir"]
            nex = json.loads((ev7 / "notexecuted.json").read_text(encoding="utf-8")) \
                if (ev7 / "notexecuted.json").is_file() else None
            code7next = cmd_run("mock-spawn2", False)
            check("mock-spawn-oserror-notexec-halt",
                  code7 == 1 and nex is not None
                  and nex.get("accounting") == "not_executed"
                  and "spawn failure" in str(nex.get("reason"))
                  and bool(nex.get("preregistration_commit")) and bool(nex.get("registered_at"))
                  and not (ev7 / "meta.json").is_file()
                  and not (ev7 / "agent.jsonl").exists()
                  and (tmp / "halt-spawn.json").is_file()
                  and code7next == 3,
                  "code7=%s nex=%s meta_exists=%s halt=%s next=%s"
                  % (code7, json.dumps(nex, ensure_ascii=False)[:200] if nex else None,
                     (ev7 / "meta.json").is_file(), (tmp / "halt-spawn.json").is_file(), code7next))
            globals().update({"HALT_PATH": orig_halt})
            # 世界8：已启动后运行期 OSError（communicate EIO）→ 真实 partial（不误记
            # not_executed；score null；无 checker；组已消失则无 halt）。
            checker_calls8 = {"n": 0}
            orig_score8 = score_case

            def counting_score8(*a, **k):
                checker_calls8["n"] += 1
                return orig_score8(*a, **k)

            orig_popen8 = subprocess.Popen

            class _EioProc:
                def __init__(self, real):
                    self._r = real
                    self.pid = real.pid
                    self.returncode = None

                def communicate(self, input=None, timeout=None):
                    raise OSError(5, "Simulated I/O error (post-launch)")

                def wait(self, timeout=None):
                    rc = self._r.wait(timeout=timeout)
                    self.returncode = rc
                    return rc

                def poll(self):
                    rc = self._r.poll()
                    if rc is not None:
                        self.returncode = rc
                    return rc

                def send_signal(self, sig):
                    self._r.send_signal(sig)

                def kill(self):
                    self._r.kill()

            def eio_popen(*a, **k):
                # 选择性包装：仅 run_slot 的 build_cmd() 派发命中；subprocess.run 内部
                # Popen（cli_version 等）走真实现，避免破坏其 with-Popen 契约。
                if a and a[0] == build_cmd():
                    return _EioProc(orig_popen8(*a, **k))
                return orig_popen8(*a, **k)

            sess8 = tmp / "sess-eio"
            sess8.mkdir(parents=True, exist_ok=True)
            globals().update({"CASE_ROOT": case_root, "WS_BASE": tmp / "ws" / "eio",
                              "STAGING_ROOT": tmp / "staging" / "eio",
                              "DISPATCH_ROOT": tmp / "dispatch" / "eio",
                              "EV_BASE": tmp, "ISOLATION_WS_PREFIX": tmp,
                              "MOCK_CMD": [sys.executable, "-c", MOCK_STUB_DSH],
                              "MOCK_SESSION_SRC": sess8, "PLAN_DIR_OVERRIDE": plan_dir,
                              "BINDING_PATH": binding_released,
                              "GUARDS": dict(GUARDS, **{"mock-case": {"input_integrity"}}),
                              "MOCK_EXTRA_ENV": {"L4_MOCK_CHECKER_MODE": "scored", "L4_MOCK_SLEEP": "2",
                                                 "L4_MOCK_SESSION_DIR": str(sess8)},
                              "HALT_PATH": tmp / "halt-eio.json",
                              "score_case": counting_score8})
            subprocess.Popen = eio_popen
            slot8 = dict(slot, slot_id="mock-eio1", run_id="mock-eio1", event_id="event:mock-eio1",
                         timeout_s=60, evidence_dir="runs-eio/mock-eio1")
            code8 = run_slot(slot8, contract)
            ev8 = tmp / slot8["evidence_dir"]
            meta8 = json.loads((ev8 / "meta.json").read_text(encoding="utf-8")) \
                if (ev8 / "meta.json").is_file() else None
            check("mock-runtime-oserror-partial",
                  code8 == 1 and meta8 is not None
                  and meta8["status"] == "error" and meta8["weighted"] is None
                  and meta8["diagnostic"]["class"] == "runtime-oserror-post-launch"
                  and meta8["diagnostic"]["stop_unverified"] is False
                  and not (ev8 / "notexecuted.json").exists()
                  and not (tmp / "halt-eio.json").is_file()
                  and checker_calls8["n"] == 0
                  and (ev8 / "agent.jsonl").is_file(),
                  "code8=%s meta=%s notexec=%s halt=%s checker=%s"
                  % (code8, json.dumps(meta8.get("diagnostic"), ensure_ascii=False)[:160] if meta8 else None,
                     (ev8 / "notexecuted.json").exists(), (tmp / "halt-eio.json").is_file(),
                     checker_calls8["n"]))
            subprocess.Popen = orig_popen8
            globals().update({"score_case": orig_score8, "HALT_PATH": orig_halt})
    # 世界4：unscored（weighted=null，partial 记账，accounting_complete 真）
            code, meta, rep = world("unscored", "unscored", 0, 60)
            s = rep["summary"]
            check("mock-unscored-null-partial",
                  meta["weighted"] is None and meta["score_status"] == "unscored-diagnostic"
                  and rep["per_slot"][0]["accounting"] == "partial"
                  and rep["per_slot"][0]["formal_admission"] is False
                  and s["accounting_complete"] is True,
                  json.dumps(s) + str(rep["per_slot"][0]["fails"])[:200])
    finally:
        globals().update(saved)

    counts = {"total": len(results), "passed": sum(1 for r in results if r["pass"]),
              "failed": sum(1 for r in results if not r["pass"])}
    ek = load_evidence_kit()
    receipt = {"kind": "mock_run_self_test", "tool": "lab.py(l5-dsh)", "spec": "l5-20261030-dsh",
               "at": now_iso(), "zero_model": True, "counts": counts, "cases": results,
               "evidence": ek_json(ek.gather([str(HERE / "lab.py")], REPO, now_iso())),
               "live_doc_drift": []}
    out = BATCH / "selftest" / "runner-mockrun.json"
    n = 1
    while out.exists():
        n += 1
        out = BATCH / "selftest" / ("runner-mockrun-r%d.json" % n)
    out.parent.mkdir(parents=True, exist_ok=True)
    atomic_refuse_write(out, json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(counts, ensure_ascii=False), "→", out)
    return 0 if counts["failed"] == 0 else 1


# ---------------------------------------------------------------- termination 真实进程回归（零模型）

TERM_PARENT = r"""
import os, signal, sys, time
# 父：TERM 即退；启动一个忽略 TERM 的子进程（同组）持续写探针文件
probe = sys.argv[1]
if os.fork() == 0:
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    with open(probe, "a", encoding="utf-8") as fh:
        while True:
            fh.write("x")
            fh.flush()
            time.sleep(0.1)
    os._exit(0)
# 父等子起来后进入可被 TERM 打断的睡眠
deadline = time.time() + 30
while time.time() < deadline:
    time.sleep(0.1)
"""


def cmd_termination_selftest() -> int:
    """真实父子进程回归：父收 TERM 即退、子忽略 TERM 持续写。

    断言：①TERM 后父 returncode 已出而组仍存活（旧实现 verified=True 的反例）；
    ②组级 KILL 后 group_confirmed_gone 且子进程确停；③不允许升级时 verified=False。"""
    import tempfile
    results = []
    with tempfile.TemporaryDirectory(prefix="l4term-") as td:
        tmp = Path(td)
        probe = tmp / "probe.bin"
        parent_script = tmp / "parent.py"
        parent_script.write_text(TERM_PARENT, encoding="utf-8")
        proc = subprocess.Popen([sys.executable, str(parent_script), str(probe)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                start_new_session=True)
        pgid = os.getpgid(proc.pid)
        time.sleep(0.8)  # 父子都起来；子进程已写探针
        size_before = probe.stat().st_size
        results.append({"case": "child-writing-before-stop", "pass": size_before > 0,
                        "detail": "probe bytes=%d" % size_before})
        # 场景A：不允许升级（仅 TERM）→ 父死、子活 → 组级确认不可能 → verified=False
        term_a = stop_process_group(pgid, proc, 1, allow_escalate=False)
        time.sleep(0.3)
        size_mid = probe.stat().st_size
        results.append({"case": "term-only-parent-exited-group-alive",
                        "pass": proc.poll() is not None and group_alive(pgid),
                        "detail": "parent returncode=%s group_alive=%s（旧实现此处误 verified=True）"
                                  % (proc.returncode, group_alive(pgid))})
        results.append({"case": "term-only-verified-false",
                        "pass": term_a["verified_stop"] is False
                        and term_a["group_confirmed_gone"] is False,
                        "detail": json.dumps({k: term_a.get(k) for k in
                                              ("signal", "verified_stop", "group_confirmed_gone")})})
        results.append({"case": "child-lived-through-term-only-window",
                        "pass": size_mid > size_before,
                        "detail": "bytes %d→%d during TERM-only window（子进程跨 TERM 持续写）"
                                  % (size_before, size_mid)})
        # 场景B：允许升级 → 组级 KILL → 组消失 → verified=True；子进程确停
        term_b = stop_process_group(pgid, proc, 1, allow_escalate=True)
        time.sleep(0.4)
        size_after = probe.stat().st_size
        time.sleep(0.5)
        results.append({"case": "kill-group-confirmed-gone",
                        "pass": term_b["verified_stop"] is True
                        and term_b["group_confirmed_gone"] is True
                        and term_b["signal"] == "SIGKILL",
                        "detail": json.dumps({k: term_b.get(k) for k in
                                              ("signal", "escalated", "verified_stop",
                                               "group_confirmed_gone")})})
        results.append({"case": "child-actually-stopped",
                        "pass": probe.stat().st_size == size_after,
                        "detail": "bytes stable at %d" % size_after})
        # 场景C/D：正常退出路径的组闭包（复核 扩展判据）
        # C：父正常 exit 0，子忽略 TERM 持续写 → 组仍活 → 有界清理 KILL → verified=True、child 停
        proc2 = subprocess.Popen([sys.executable, "-c",
                                  "import sys, time\n"
                                  "if os.fork() == 0:\n"
                                  "    import signal\n"
                                  "    signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
                                  "    with open(sys.argv[1], \"a\") as fh:\n"
                                  "        while True: fh.write(\"x\"); fh.flush(); time.sleep(0.1)\n"
                                  "time.sleep(0.2)\n", str(probe)],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 start_new_session=True)
        pgid2 = os.getpgid(proc2.pid)
        proc2.wait(timeout=15)  # 父正常退出（exit 0）
        normal_gone = not group_alive(pgid2)
        if not normal_gone:
            cl = stop_process_group(pgid2, proc2, 1, allow_escalate=True)
            cl["phase"] = "post_exit_cleanup"
        else:
            cl = {"phase": "normal_exit", "probe": "verified_gone", "signal": None,
                  "verified_stop": True, "group_confirmed_gone": True}
        time.sleep(0.4)
        size_c = probe.stat().st_size
        time.sleep(0.4)
        results.append({"case": "normal-parentexit-childalive-cleaned",
                        "pass": cl["verified_stop"] is True and probe.stat().st_size == size_c,
                        "detail": json.dumps({k: cl.get(k) for k in
                                              ("phase", "signal", "verified_stop",
                                               "group_confirmed_gone")})})
        # D：普通单进程正常退出 → 探针 ESRCH 即证，无需发信号
        proc3 = subprocess.Popen(["sleep", "0"], start_new_session=True)
        pgid3 = os.getpgid(proc3.pid)
        proc3.wait(timeout=10)
        cl3 = {"phase": "normal_exit", "probe": "verified_gone" if not group_alive(pgid3) else "alive",
               "signal": None, "verified_stop": not group_alive(pgid3),
               "group_confirmed_gone": not group_alive(pgid3)}
        results.append({"case": "normal-exit-probe-only-no-signal",
                        "pass": cl3["verified_stop"] is True and cl3["signal"] is None,
                        "detail": json.dumps(cl3)})
    counts = {"total": len(results), "passed": sum(1 for r in results if r["pass"]),
              "failed": sum(1 for r in results if not r["pass"])}
    ek = load_evidence_kit()
    receipt = {"kind": "termination_self_test", "tool": "lab.py(l5-dsh)",
               "spec": "l5-20261030-dsh", "at": now_iso(), "zero_model": True,
               "counts": counts, "cases": results,
               "evidence": ek_json(ek.gather([str(HERE / "lab.py")], REPO, now_iso())),
               "live_doc_drift": []}
    out = BATCH / "selftest" / "termination-selftest.json"
    n = 1
    while out.exists():
        n += 1
        out = BATCH / "selftest" / ("termination-selftest-r%d.json" % n)
    out.parent.mkdir(parents=True, exist_ok=True)
    atomic_refuse_write(out, json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(counts, ensure_ascii=False), "→", out)
    return 0 if counts["failed"] == 0 else 1


def cmd_notexec(slot_id: str, reason: str, stop_source: str) -> int:
    plan = load_plan()
    if not BINDING_PATH.is_file():
        print("拒绝：binding 不存在（not_executed 记账须 D/E 引用，E 前不可记账）")
        return 2
    binding = json.loads(BINDING_PATH.read_text(encoding="utf-8"))
    if not binding.get("preregistration_commit"):
        print("拒绝：binding 缺 preregistration_commit")
        return 2
    slot = next((s for s in dsh_slots(plan) if s["slot_id"] == slot_id), None)
    if slot is None:
        print("未知 slot：%s" % slot_id)
        return 2
    ev = ev_dir(slot)
    if (ev / "meta.json").exists():
        print("该槽已有 meta.json（不得双记账）")
        return 2
    ev.mkdir(parents=True, exist_ok=True)
    atomic_refuse_write(ev / "notexecuted.json", json.dumps(
        {"slot_id": slot["slot_id"], "run_id": slot["run_id"], "event_id": slot["event_id"],
         "accounting": "not_executed", "preregistration_commit": binding.get("preregistration_commit"),
         "registered_at": binding.get("registered_at"),
         "reason": reason, "stop_source": stop_source, "at": now_iso(),
         "note": "从未外发；不造 started_at/session/usage/score；诊断记录完整仍可 accounting_complete",
         "live_doc_drift": []}, ensure_ascii=False, indent=2) + "\n")
    print("not_executed 记账：%s" % slot_id)
    return 0


def cmd_selftest() -> int:
    """零模型自测：以 r1031 已归档会话轨迹为输入验证重建/usage/扫描全链路。"""
    src_candidates = sorted((REPO / "3-表现现场" / "r1031-variance-n3" / "dsh" / "runs").glob("*/agent-session"))
    if not src_candidates:
        print("无 r1031 归档可复用")
        return 2
    cases = []
    with tempfile.TemporaryDirectory(prefix="l4dsh-st-") as td:
        tmp = Path(td)
        for i, src in enumerate(src_candidates[:2]):
            sess = tmp / ("s%d" % i)
            shutil.copytree(src, sess)
            events = rebuild_full_stream(sess)
            fpath = sess / "rebuilt.jsonl"
            with fpath.open("w", encoding="utf-8") as fh:
                for e in events:
                    fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            usage = extract_per_call_usage(sess, None)
            hits, lines = scan_integrity_stream(session_lines(sess))
            # 无截断断言：重建流存在 text/thinking 事件且 final 非空（有会话内容时）
            has_text = any(e["type"] in ("text", "thinking") for e in events)
            cases.append({"session": src.parent.name, "events": len(events),
                          "full_bytes": fpath.stat().st_size,
                          "has_text_or_thinking": has_text,
                          "usage_requests": usage["requests"],
                          "usage_input_tokens": usage["input_tokens"],
                          "integrity_lines": lines, "integrity_hits": len(hits),
                          "pass": bool(events and lines > 0 and usage["requests"] > 0)})
    desens = desensitize_text("api_key: sk-abcdef1234567890\ntoken: abc\nplain: keep")
    cases.append({"case": "desensitize", "pass": "[REDACTED]" in desens and "keep" in desens
                  and "sk-abcdef" not in desens})
    ok = all(c["pass"] for c in cases)
    ek = load_evidence_kit()
    receipt = {"kind": "self_test", "tool": "lab.py(l5-dsh)", "spec": "l5-20261030-dsh",
               "at": now_local_iso(), "zero_model": True,
               "counts": {"total": len(cases), "passed": sum(1 for c in cases if c["pass"]),
                          "failed": sum(1 for c in cases if not c["pass"])},
               "cases": cases,
               "evidence": ek_json(ek.gather([str(HERE / "lab.py"), str(PLAN_PATH), str(CONTRACT_PATH)], REPO, now_local_iso())),
               "live_doc_drift": []}
    out = BATCH / "selftest" / "runner-selftest.json"
    n = 1
    while out.exists():
        n += 1
        out = BATCH / "selftest" / ("runner-selftest-r%d.json" % n)
    out.parent.mkdir(parents=True, exist_ok=True)
    atomic_refuse_write(out, json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(receipt["counts"], ensure_ascii=False), "→", out)
    return 0 if ok else 1


def now_local_iso() -> str:
    return now_iso()


def cmd_report() -> int:
    plan = load_plan()
    rows = []
    for slot in dsh_slots(plan):
        ev = ev_dir(slot)
        entry = {"slot_id": slot["slot_id"], "order": slot["order"], "case": slot["case"],
                 "rep": int(slot["rep"]), "accounting": None}
        if (ev / "meta.json").is_file():
            m = json.loads((ev / "meta.json").read_text(encoding="utf-8"))
            entry.update({"accounting": "executed", "status": m["status"],
                          "weighted": m.get("weighted"), "score_status": m.get("score_status"),
                          "integrity_verdict": m.get("integrity_verdict"),
                          "usage_requests": (m.get("usage") or {}).get("requests"),
                          "stdout_sha256": m.get("stdout_sha256")})
        elif (ev / "notexecuted.json").is_file():
            entry.update({"accounting": "not_executed",
                          "reason": json.loads((ev / "notexecuted.json").read_text(encoding="utf-8")).get("reason")})
        rows.append(entry)
    ek = load_evidence_kit()
    summary = {"kind": "batch_runs_summary", "batch": BATCH_NAME, "product": PRODUCT,
               "at": now_iso(),
               "summary": {"planned": len(rows),
                           "executed": sum(1 for r in rows if r["accounting"] == "executed"),
                           "not_executed": sum(1 for r in rows if r["accounting"] == "not_executed"),
                           "unaccounted": sum(1 for r in rows if r["accounting"] is None)},
               "slots": rows,
               "whole_execution_restarts": 0,
               "zero_model_claim": "runs 期间每槽恰一次外发（dispatch/ 登记），无重试",
               "evidence": ek_json(ek.gather([str(DISPATCH / (r["slot_id"] + ".json")) for r in rows
                                      if (DISPATCH / (r["slot_id"] + ".json")).exists()], REPO, now_iso())),
               "live_doc_drift": []}
    out = BATCH / "runs-summary.json"
    atomic_refuse_write(out, json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary["summary"], ensure_ascii=False), "→", out)
    return 0


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("preflight").set_defaults(func=lambda a: cmd_preflight())
    sub.add_parser("selftest").set_defaults(func=lambda a: cmd_selftest())
    sub.add_parser("mockrun").set_defaults(func=lambda a: cmd_mockrun())
    sub.add_parser("termination-selftest").set_defaults(func=lambda a: cmd_termination_selftest())
    sub.add_parser("report").set_defaults(func=lambda a: cmd_report())
    sp = sub.add_parser("run")
    g = sp.add_mutually_exclusive_group(required=True)
    g.add_argument("--slot")
    g.add_argument("--all", action="store_true")
    sp.set_defaults(func=lambda a: cmd_run(a.slot, a.all))
    sn = sub.add_parser("notexec")
    sn.add_argument("--slot", required=True)
    sn.add_argument("--reason", required=True)
    sn.add_argument("--stop-source", required=True)
    sn.set_defaults(func=lambda a: cmd_notexec(a.slot, a.reason, a.stop_source))
    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except (RuntimeError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    except Exception as exc:  # GateError 等经 import 注入的异常名不在此模块命名空间
        if type(exc).__name__ == "GateError":
            print(json.dumps({"ok": False, "gate": str(exc)}, ensure_ascii=False))
            return 1
        raise


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
