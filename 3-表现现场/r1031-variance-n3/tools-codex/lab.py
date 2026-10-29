#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r1031-variance-n3（codex 侧）：n=3 可重复性运行器（rep 2/3；r1030 各场记 rep 1）。

自 r1030-formal-a1/tools/lab.py 最小改动适配，调用方式与 r1030 Codex 完全一致：
- 隔离 CODEX_HOME（base_url=https://api.deepseek.com，wire_api=responses，model_reasoning_effort=low，
  approval_policy=never，sandbox_mode=danger-full-access，web_search/skills off）；
- `codex exec --json --skip-git-repo-check -C <ws> -m deepseek-flash -c model_reasoning_effort="low" -`；
- API key 走 ~/.dsh/.credentials.yaml refs 段 DEEPSEEK_API_KEY，不打印。

适配差异（详见 tools-codex/README.md）：
- workspace 根 ~/bench-workspaces/r1031/codex/<rep>/<case>/；event id `var-n3-codex-<case>-r<rep>`；
- meta 每场写 `preregistration_commit="be39fc2"`；
- 随批工程项 a：stdout/stderr 完整流落盘（无 8192 截断路径），meta 记 bytes+sha256；
  运行日志经 staging 移动（修复 r1030#1 归档缺陷），不再有日志丢失路径；
- 随批工程项 b：逐调用 usage 入库（Codex rollout token_usage_record：cached_input_tokens→cache_read、
  cache_write_input_tokens→cache_creation）；
- 纪律：运行级失败不补跑，记 selection=null 诊断并继续；仅传输层错误（429/断连）指数退避
  ≤3 次（2/8/32s）且属同一逻辑运行。

用法：
    python3 lab.py preflight
    python3 lab.py prepare <case> <rep>
    python3 lab.py run <case> <rep>        # 跑 + 判分（冻结 checker）+ 归档
    python3 lab.py judge <case> <rep>
    python3 lab.py integrity <case> <rep>  # 会话轨迹+stdout 重扫（幂等）
    python3 lab.py receipt <case> <rep>    # score-receipt.json + adjudication.json 草案
    python3 lab.py summary                 # integrity-rescan-summary.json + adjudications.json 草案
    python3 lab.py status                  # 当前矩阵一览
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
BATCH = Path(__file__).resolve().parents[1]          # 3-表现现场/r1031-variance-n3
PRODUCT_ROOT = BATCH / "codex"                        # 本写界：codex/**
CASE_ROOT = REPO / "2-用例"
WS_ROOT = Path.home() / "bench-workspaces" / "r1031" / "codex"
RUNS = PRODUCT_ROOT / "runs"
STAGING = PRODUCT_ROOT / "staging"
CODEX_HOME = WS_ROOT / "_codex-home"
MODEL = "deepseek-flash"
EFFORT = "low"
RULE = "freeze-20261029-v2"
BATCH_NAME = "r1031-variance-n3"
PREREG_COMMIT = "be39fc2"
PLAN_ID = "var-n3-20261029"
CASES = ("bird-ca-schools-15", "dabstep-payments-10", "exercism-py-6", "lcb-recent-hard-4", "tb-cargo-plan")
REPS = (2, 3)
PRODUCT = "codex"

CODEX_CONFIG = """# r1031-variance-n3 · Codex CLI 隔离 CODEX_HOME · DeepSeek V4.1-Flash · thinking=low
model = "deepseek-flash"
model_provider = "deepseek"
model_reasoning_effort = "low"
approval_policy = "never"
sandbox_mode = "danger-full-access"
web_search = "disabled"

[skills]
include_instructions = false
[skills.bundled]
enabled = false

[model_providers.deepseek]
name = "DeepSeek"
base_url = "https://api.deepseek.com"
env_key = "DEEPSEEK_API_KEY"
wire_api = "responses"
"""

TOOL_FACTS = {
    "codex": {
        "tools": ["shell", "apply_patch", "read_files（web_search=disabled，skills=off）"],
        "permissions": "sandbox_mode=danger-full-access; approval_policy=never（隔离 CODEX_HOME 配置）",
        "skills": "off（[skills] include_instructions=false，bundled disabled）",
        "route": {"host": "api.deepseek.com", "provider_id": "deepseek", "wire_protocol": "responses",
                  "endpoint": "https://api.deepseek.com"},
    },
}

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

TRANSPORT_RE = re.compile(
    r"429|rate.?limit|too many requests|stream disconnected|connection reset|connection refused"
    r"|temporarily unavailable|bad gateway|502|503|error sending request", re.I)
BACKOFF_S = (2, 8, 32)
BOOKKEEPING_CHECK_IDS = {"input_integrity", "answers_file", "answers_schema", "answers_coverage", "artifact"}


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def ws_dir(case: str, rep: int) -> Path:
    return WS_ROOT / str(rep) / case


def run_ev(case: str, rep: int) -> Path:
    return RUNS / ("%s__%s__r%d" % (PRODUCT, case, rep))


def event_id(case: str, rep: int) -> str:
    return "var-n3-codex-%s-r%d" % (case, rep)


def run_id(case: str, rep: int) -> str:
    return "r1031-codex-%s-r%d" % (case, rep)


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
    out = subprocess.run(["codex", "--version"], capture_output=True, text=True, timeout=60)
    return (out.stdout or out.stderr).strip().splitlines()[0].strip()


def build_task(case: str, ws: Path) -> str:
    body = (CASE_ROOT / case / "instruction.md").read_text(encoding="utf-8").rstrip()
    head = (
        "# 本场任务：%s（Codex CLI）\n\n"
        "**你的工作目录（绝对路径）：`%s`**\n\n"
        "请在这个目录里工作：输入都在该目录的 `inputs/` 下，产物按题目要求写到该目录里"
        "（题目里的相对路径都相对这个目录）。除题目明确要求修改的代码外，不要改动 `inputs/` 下的文件。\n\n"
        "---\n\n" % (case, ws)
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


def cmd_preflight() -> int:
    """零模型调用的接口预检（codex 侧）：版本、配置落盘、工作区隔离、判分器可执行。"""
    receipt = {"kind": "interface_preflight", "batch": BATCH_NAME, "side": "codex",
               "model_calls": 0, "at": now_iso(), "rule": RULE,
               "preregistration_commit": PREREG_COMMIT}
    receipt["codex"] = {"version": cli_version()}
    if CODEX_HOME.exists():
        shutil.rmtree(CODEX_HOME)
    CODEX_HOME.mkdir(parents=True)
    (CODEX_HOME / "config.toml").write_text(CODEX_CONFIG, encoding="utf-8")
    receipt["codex"]["config_toml"] = str(CODEX_HOME / "config.toml")
    receipt["codex"]["config_sha256"] = sha(CODEX_HOME / "config.toml")
    # 隔离演练
    ws = WS_ROOT / "_isolation-probe"
    if ws.exists():
        shutil.rmtree(ws)
    ws.mkdir(parents=True)
    (ws / "inputs").mkdir()
    (ws / "inputs" / "dummy.txt").write_text("probe\n", encoding="utf-8")
    receipt["isolation_probe"] = check_isolation(ws)
    shutil.rmtree(ws)
    # 判分器可执行性冒烟（--help，正式判分以冻结 checker 单独执行）
    smoke = {}
    for case in CASES:
        p = subprocess.run([sys.executable, str(CASE_ROOT / case / "checker.py"), "--help"],
                           capture_output=True, text=True, timeout=120)
        smoke[case] = {"exit": p.returncode}
    receipt["checker_smoke"] = smoke
    receipt["ok"] = (receipt["isolation_probe"]["ok"]
                     and all(v["exit"] in (0, 2) for v in smoke.values()))
    out = PRODUCT_ROOT / "preflight" / "cli-preflight.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": receipt["ok"], "receipt": str(out)}, ensure_ascii=False))
    return 0 if receipt["ok"] else 2


def cmd_prepare(case: str, rep: int) -> int:
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
        "batch": BATCH_NAME, "rule_version": RULE, "preregistration_commit": PREREG_COMMIT,
        "rep": rep, "product": PRODUCT, "case": case, "form": "cli",
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


# ---------------------------------------------------------------- usage（工程项 b）

def _iter_rollout_lines(sess_dir: Path):
    for p in sorted(sess_dir.rglob("*.jsonl")):
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            yield p.name, line


def extract_usage(sess_dir: Path) -> dict:
    """逐调用 usage：Codex rollout token_usage_record → per_call 列表 + 汇总。

    映射：cached_input_tokens→cache_read_tokens；cache_write_input_tokens→cache_creation_tokens。
    """
    per_call, seen = [], set()
    thread_final = None
    for fname, line in _iter_rollout_lines(sess_dir):
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if not isinstance(ev, dict) or ev.get("type") != "token_usage_record":
            continue
        pay = ev.get("payload") or {}
        u = pay.get("usage") or {}
        rid = pay.get("response_id")
        if rid and rid in seen:
            continue
        seen.add(rid)
        per_call.append({
            "session_file": fname, "ts": ev.get("timestamp"),
            "response_id": rid, "turn_id": pay.get("turn_id"),
            "input_tokens": int(u.get("input_tokens") or 0),
            "cache_read_tokens": int(u.get("cached_input_tokens") or 0),
            "cache_creation_tokens": int(u.get("cache_write_input_tokens") or 0),
            "output_tokens": int(u.get("output_tokens") or 0),
            "reasoning_output_tokens": int(u.get("reasoning_output_tokens") or 0),
            "total_tokens": int(u.get("total_tokens") or 0),
            "_thread_token_usage": pay.get("thread_token_usage"),
        })
    thread_final = per_call[-1]["_thread_token_usage"] if per_call else None
    for rec in per_call:
        rec.pop("_thread_token_usage", None)
    s = lambda k: sum(r[k] for r in per_call)  # noqa: E731
    return {
        "requests": len(per_call),
        "input_tokens": s("input_tokens"),
        "output_tokens": s("output_tokens"),
        "cache_read_tokens": s("cache_read_tokens"),
        "cache_creation_tokens": s("cache_creation_tokens"),
        "reasoning_output_tokens": s("reasoning_output_tokens"),
        "total_tokens": s("total_tokens"),
        "cumulative_thread_final": thread_final,
        "per_call": per_call,
        "note": ("per-response usage from product session rollout token_usage_record; "
                 "cached_input_tokens→cache_read_tokens, cache_write_input_tokens→cache_creation_tokens; "
                 "absent fields stay 0"),
    }


# ---------------------------------------------------------------- integrity

def _scan_lines(lines, source_name, hits):
    for i, line in enumerate(lines):
        try:
            ev = json.loads(line)
        except Exception:
            continue
        blob = json.dumps(ev, ensure_ascii=False)
        for pat in INTEGRITY_PATTERNS:
            if pat in blob:
                hits.append({"source": source_name, "line": i + 1, "pattern": pat,
                             "excerpt": blob[:300]})
                break
        if len(hits) >= 20:
            return


def scan_integrity(ev_dir: Path, log: Path) -> dict:
    """会话轨迹 + runner stdout 完整流重扫八类越界模式（inline，r1030#1 修复后无日志缺失路径）。"""
    hits, n_lines = [], 0
    sess = ev_dir / "agent-session"
    session_files = []
    if sess.is_dir():
        for p in sorted(sess.rglob("*.jsonl")):
            session_files.append({"name": str(p.relative_to(ev_dir)), "bytes": p.stat().st_size})
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            n_lines += len(lines)
            _scan_lines(lines, p.name, hits)
    stdout_files = []
    for p in [log] + sorted(ev_dir.glob("agent.failed-attempt*.jsonl")):
        if p.exists():
            stdout_files.append({"name": str(p.relative_to(ev_dir)), "bytes": p.stat().st_size})
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            n_lines += len(lines)
            _scan_lines(lines, p.name, hits)
    return {"violations": len(hits), "patterns": INTEGRITY_PATTERNS,
            "session_files": session_files, "stdout_files": stdout_files,
            "lines_scanned": n_lines, "evidence": hits,
            "method": "inline session-trajectory + runner-stdout rescan (r1030#1 fixed: staging move)"}


# ---------------------------------------------------------------- judge / receipt

def judge(case: str, rep: int) -> dict:
    ws = ws_dir(case, rep)
    p = subprocess.run([sys.executable, str(CASE_ROOT / case / "checker.py"), str(ws), "--json"],
                       capture_output=True, text=True, timeout=1200, cwd=str(REPO))
    try:
        res = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        res = {"reward": None, "error": (p.stdout + p.stderr)[-2000:]}
    return res


def score_fields(j: dict) -> dict:
    """从 checker 输出机械提取 earned/possible（不同 case 字段名不同）。"""
    pairs = [("correct", "n_questions"), ("correct", "n_tasks"),
             ("passed_problems", "total_problems"), ("passed", "total")]
    for a, b in pairs:
        if isinstance(j.get(a), int) and isinstance(j.get(b), int):
            return j[a], j[b]
    checks = [c for c in (j.get("checks") or []) if c.get("id") not in BOOKKEEPING_CHECK_IDS
              and isinstance(c.get("pass"), bool)]
    if checks:
        return sum(1 for c in checks if c["pass"]), len(checks)
    return None, None


def write_receipt(case: str, rep: int) -> dict:
    ev = run_ev(case, rep)
    meta = json.loads((ev / "meta.json").read_text(encoding="utf-8"))
    j = meta.get("judge") or {}
    earned, possible = score_fields(j)
    receipt = {
        "case": case, "product": PRODUCT, "rep": rep, "run_id": meta["run_id"],
        "score": {"earned": earned, "possible": possible,
                  "assessed": possible, "reported": j.get("weighted"),
                  "reward": j.get("reward"), "rule_version": RULE,
                  "checker_sha256": sha(CASE_ROOT / case / "checker.py")},
        "raw_checker_output": j,
    }
    (ev / "score-receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                                           encoding="utf-8")
    return receipt


def adjudicate(case: str, rep: int) -> dict:
    """机械映射裁定草案（draft=true；语义裁定权在 lead，复核后翻转 draft）。"""
    ev = run_ev(case, rep)
    meta = json.loads((ev / "meta.json").read_text(encoding="utf-8"))
    ok_run = meta.get("status") == "ok" and meta.get("exit_code") == 0
    verd = meta.get("integrity_verdict")
    clean = verd in ("clean", "clean-reviewed")
    scored = isinstance(meta.get("judge"), dict) and "checks" in meta["judge"]
    out = {"event_id": event_id(case, rep), "run_id": meta["run_id"], "batch": BATCH_NAME,
           "rep": rep, "preregistration_commit": PREREG_COMMIT, "draft": True,
           "adjudicator": "builder-codex（机械草案，语义裁定权在 lead，待复核确认）"}
    if ok_run and clean and scored:
        out.update({
            "final_adjudication": "valid", "evidence_grade": "original-contemporaneous-full",
            "gates": {g: True for g in ("rules_frozen", "case_valid", "scoring_reviewable",
                                        "evidence_valid", "contamination_free")},
            "basis": ("规则: %s，预注册 commit %s 先于运行；题面: v2 冻结 manifest；"
                      "评分: 冻结 checker 收据+raw 输出双源；"
                      "证据: meta/会话轨迹/判分/配置快照/stdout 完整流（%d 字节）当场归档"
                      "（r1030#1 修复：staging 移动，无日志丢失路径）；"
                      "无污染: 工作区仓库外+隔离断言+会话与 stdout 八类模式重扫，verdict=%s。"
                      ) % (RULE, PREREG_COMMIT, meta.get("stdout_bytes", -1), verd)})
    elif meta.get("status") == "timeout":
        out.update({
            "final_adjudication": "valid", "evidence_grade": "original-contemporaneous-full",
            "gates": {g: True for g in ("rules_frozen", "case_valid", "scoring_reviewable",
                                        "evidence_valid", "contamination_free")},
            "basis": ("按 case.json timeout_s 合同超时截停；checker 对现有产物全量评估，按合同记结果。"
                      "无污染: 会话+stdout 轨迹重扫 %d 命中；证据当场全量归档（stdout %d 字节）。"
                      ) % (meta.get("integrity", {}).get("violations", -1), meta.get("stdout_bytes", -1))})
    else:
        diag = meta.get("diagnostic") or ("status=%s exit=%s" % (meta.get("status"), meta.get("exit_code")))
        out.update({
            "final_adjudication": "infrastructure_invalid",
            "evidence_grade": "original-contemporaneous-partial",
            "selection": None,
            "diagnostic": diag,
            "gates": {g: (g in ("rules_frozen", "case_valid")) for g in (
                "rules_frozen", "case_valid", "scoring_reviewable", "evidence_valid", "contamination_free")},
            "basis": ("selection=null 诊断事件：status=%s exit=%s integrity=%s——运行级失败不补跑，"
                      "如实保留诊断，不进 primary。") % (
                meta.get("status"), meta.get("exit_code"), meta.get("integrity_verdict"))})
    (ev / "adjudication.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8")
    return out


# ---------------------------------------------------------------- run

def capture_session(ev: Path, started_iso: str) -> None:
    sess = ev / "agent-session"
    sess.mkdir(exist_ok=True)
    sdir = CODEX_HOME / "sessions"
    if sdir.is_dir():
        st = dt.datetime.fromisoformat(started_iso).timestamp()
        files = [q for q in sdir.rglob("*.jsonl") if q.stat().st_mtime >= st - 5]
        files.sort(key=lambda q: q.stat().st_mtime, reverse=True)
        for q in files:
            shutil.copy2(q, sess / q.name)


def _finalize_attempt_paths(files: dict) -> tuple[Path, Path]:
    log, err = files["log"], files["err"]
    log_final, err_final = log.parent / "agent.jsonl", log.parent / "agent.stderr.txt"
    for src, dst in ((log, log_final), (err, err_final)):
        if src.exists():
            if dst.exists():
                dst.unlink()
            shutil.move(str(src), str(dst))
    return log_final, err_final


def cmd_run(case: str, rep: int) -> int:
    ws = ws_dir(case, rep)
    if not (ws / "TASK.md").exists():
        cmd_prepare(case, rep)
    prompt = (ws / "TASK.md").read_text(encoding="utf-8")
    key = load_api_key()
    cj = CASE_ROOT / case / "case.json"
    timeout = json.loads(cj.read_text()).get("timeout_s", 1800) if cj.exists() else 1800
    ev_dir = run_ev(case, rep)
    ev_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, CODEX_HOME=str(CODEX_HOME), DEEPSEEK_API_KEY=key, RUST_LOG="warn")
    cmd = ["codex", "exec", "--json", "--skip-git-repo-check", "-C", str(ws), "-m", MODEL,
           "-c", 'model_reasoning_effort="%s"' % EFFORT, "-"]
    attempts, transport_retries = [], 0
    status, exit_code, diagnostic = "ok", None, None
    log = err = None
    while True:
        n = len(attempts) + 1
        alog = ev_dir / ("agent.attempt%d.jsonl" % n)
        aerr = ev_dir / ("agent.attempt%d.stderr.txt" % n)
        started, st_ts = now_iso(), time.time()
        a_status, a_exit = "ok", None
        with alog.open("w", encoding="utf-8") as out, aerr.open("w", encoding="utf-8") as er:
            try:
                p = subprocess.run(cmd, cwd=str(ws), env=env, input=prompt, text=True,
                                   stdout=out, stderr=er, timeout=timeout)
                a_exit = p.returncode
            except subprocess.TimeoutExpired:
                a_status, a_exit = "timeout", None
        dur = round(time.time() - st_ts, 1)
        if a_status == "timeout":
            status, exit_code = "timeout", None
            attempts.append({"n": n, "started_at": started, "duration_s": dur,
                             "exit_code": None, "outcome": "timeout"})
            log, err = alog, aerr
            break
        if a_exit == 0:
            status, exit_code = "ok", 0
            attempts.append({"n": n, "started_at": started, "duration_s": dur,
                             "exit_code": 0, "outcome": "ok"})
            log, err = alog, aerr
            break
        err_text = aerr.read_text(encoding="utf-8", errors="replace") if aerr.exists() else ""
        is_transport = bool(TRANSPORT_RE.search(err_text))
        attempts.append({"n": n, "started_at": started, "duration_s": dur,
                         "exit_code": a_exit, "outcome": "transport-error" if is_transport else "error",
                         "stderr_excerpt": err_text[-400:]})
        if is_transport and transport_retries < len(BACKOFF_S):
            time.sleep(BACKOFF_S[transport_retries])
            transport_retries += 1
            continue  # 同一逻辑运行，仅传输层错误，指数退避 ≤3 次
        status, exit_code = ("transport-error" if is_transport else "error"), a_exit
        diagnostic = ("transport error after %d retry(ies): %s" % (transport_retries, err_text[-300:])
                      if is_transport else "non-transport run failure (no retry per prereg 总则2): %s"
                      % err_text[-300:])
        log, err = alog, aerr
        break
    log_final, err_final = _finalize_attempt_paths({"log": log, "err": err})
    finished = now_iso()
    duration = round(sum(a["duration_s"] for a in attempts), 1)
    res = judge(case, rep)
    # 归档：workspace 产物 → config 快照 → 会话轨迹（日志已由 staging 移动路径保全，r1030#1 修复）
    (ev_dir / "workspace").mkdir(exist_ok=True)
    for p in ws.iterdir():
        if p.name in ("inputs", "agent.jsonl", "agent.stderr.txt", "meta.json"):
            continue
        dst = ev_dir / "workspace" / p.name
        if p.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(p, dst)
        else:
            shutil.copy2(p, dst)
    cfg = ev_dir / "config-snapshot"
    cfg.mkdir(exist_ok=True)
    shutil.copy2(CODEX_HOME / "config.toml", cfg / "codex-config.toml")
    capture_session(ev_dir, attempts[0]["started_at"])
    meta = json.loads((ws / "meta.json").read_text(encoding="utf-8"))
    usage = extract_usage(ev_dir / "agent-session")
    integ = scan_integrity(ev_dir, log_final)
    meta.update({
        "status": status, "exit_code": exit_code,
        "started_at": attempts[0]["started_at"], "finished_at": finished, "duration_s": duration,
        "attempts": attempts, "transport_retries": transport_retries,
        "stdout_bytes": log_final.stat().st_size, "stderr_bytes": err_final.stat().st_size,
        "stdout_sha256": sha(log_final), "stderr_sha256": sha(err_final),
        "stdout_archive_note": "runner 侧完整 stdout 事件流落盘，无 8192 截断路径（工程项 a）；"
                               "CLI 显示层对大输出的约 8192 字符前缀截断属产品行为，完整工具输出由会话轨迹佐证",
        "usage": usage,
        "reward": res.get("reward"), "weighted": res.get("weighted"),
        "failed": [c.get("id") for c in res.get("checks", []) if c.get("pass") is False],
        "judge": res,
        "integrity": {"violations": integ["violations"], "patterns": integ["patterns"],
                      "basis": "inline session-trajectory + runner-stdout rescan; see integrity-rescan.json",
                      "evidence": integ["evidence"]},
        "integrity_verdict": "clean" if integ["violations"] == 0 else "violation",
        "run_id": run_id(case, rep), "event_id": event_id(case, rep),
        "selection": ({"plan_id": PLAN_ID, "slot_id": event_id(case, rep), "order": rep, "kind": "rep"}
                      if status == "ok" else None),
    })
    if diagnostic:
        meta["diagnostic"] = diagnostic
    (ev_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ev_dir / "integrity-rescan.json").write_text(json.dumps(integ, ensure_ascii=False, indent=2) + "\n",
                                                  encoding="utf-8")
    (ev_dir / "checker.stdout.json").write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n",
                                                encoding="utf-8")
    write_receipt(case, rep)
    adj = adjudicate(case, rep)
    # 追加批级运行日志
    rl = {"run_id": meta["run_id"], "event_id": meta["event_id"], "case": case, "rep": rep,
          "status": status, "exit_code": exit_code, "reward": res.get("reward"),
          "weighted": res.get("weighted"), "duration_s": duration,
          "violations": integ["violations"], "stdout_bytes": meta["stdout_bytes"],
          "usage_requests": usage["requests"], "selection": meta["selection"],
          "final_adjudication_draft": adj["final_adjudication"]}
    if diagnostic:
        rl["diagnostic"] = diagnostic
    with (PRODUCT_ROOT / "run-log.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rl, ensure_ascii=False) + "\n")
    print(json.dumps({"case": case, "rep": rep, "status": status, "exit_code": exit_code,
                      "reward": res.get("reward"), "weighted": res.get("weighted"),
                      "duration_s": duration, "violations": integ["violations"],
                      "stdout_bytes": meta["stdout_bytes"], "usage_requests": usage["requests"],
                      "usage_cache_read": usage["cache_read_tokens"],
                      "usage_cache_creation": usage["cache_creation_tokens"],
                      "evidence": str(ev_dir)}, ensure_ascii=False))
    return 0


def cmd_judge(case: str, rep: int) -> int:
    print(json.dumps(judge(case, rep), ensure_ascii=False)[:2000])
    return 0


def cmd_integrity(case: str, rep: int) -> int:
    ev = run_ev(case, rep)
    log = ev / "agent.jsonl"
    integ = scan_integrity(ev, log)
    (ev / "integrity-rescan.json").write_text(json.dumps(integ, ensure_ascii=False, indent=2) + "\n",
                                              encoding="utf-8")
    meta_p = ev / "meta.json"
    meta = json.loads(meta_p.read_text(encoding="utf-8"))
    meta["integrity"] = {"violations": integ["violations"], "patterns": integ["patterns"],
                         "basis": "session-trajectory + runner-stdout rescan; see integrity-rescan.json",
                         "evidence": integ["evidence"]}
    meta["integrity_verdict"] = "clean" if integ["violations"] == 0 else "violation"
    meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"run": "%s__%s__r%d" % (PRODUCT, case, rep),
                      "violations": integ["violations"], "lines_scanned": integ["lines_scanned"]},
                     ensure_ascii=False))
    return 0


def cmd_summary() -> int:
    summary, adjs = {}, {}
    for rep in REPS:
        for case in CASES:
            ev = run_ev(case, rep)
            if not (ev / "meta.json").exists():
                continue
            meta = json.loads((ev / "meta.json").read_text(encoding="utf-8"))
            summary[meta["run_id"]] = {"violations": meta["integrity"]["violations"],
                                       "lines_scanned": (ev / "integrity-rescan.json").exists()
                                       and json.loads((ev / "integrity-rescan.json")
                                                      .read_text(encoding="utf-8"))["lines_scanned"],
                                       "stdout_bytes": meta.get("stdout_bytes"),
                                       "status": meta.get("status"),
                                       "reward": meta.get("reward"), "weighted": meta.get("weighted")}
            adj_p = ev / "adjudication.json"
            if adj_p.exists():
                a = json.loads(adj_p.read_text(encoding="utf-8"))
                adjs[a["event_id"]] = a
    (PRODUCT_ROOT / "integrity-rescan-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (PRODUCT_ROOT / "adjudications.json").write_text(
        json.dumps({"draft": True, "note": "builder-codex 机械草案；语义裁定权在 lead，复核后定稿",
                    "preregistration_commit": PREREG_COMMIT, "adjudications": adjs},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v["violations"] for k, v in summary.items()}, ensure_ascii=False, indent=1))
    return 0


def cmd_status() -> int:
    rows = []
    rl = PRODUCT_ROOT / "run-log.jsonl"
    if rl.exists():
        for line in rl.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    print(json.dumps({"runs_done": len(rows), "runs": rows}, ensure_ascii=False, indent=1))
    return 0


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("preflight").set_defaults(func=lambda a: cmd_preflight())
    sp = sub.add_parser("prepare"); sp.add_argument("case"); sp.add_argument("rep", type=int)
    sp.set_defaults(func=lambda a: cmd_prepare(a.case, a.rep))
    sp = sub.add_parser("run"); sp.add_argument("case"); sp.add_argument("rep", type=int)
    sp.set_defaults(func=lambda a: cmd_run(a.case, a.rep))
    sp = sub.add_parser("judge"); sp.add_argument("case"); sp.add_argument("rep", type=int)
    sp.set_defaults(func=lambda a: cmd_judge(a.case, a.rep))
    sp = sub.add_parser("integrity"); sp.add_argument("case"); sp.add_argument("rep", type=int)
    sp.set_defaults(func=lambda a: cmd_integrity(a.case, a.rep))
    sp = sub.add_parser("receipt"); sp.add_argument("case"); sp.add_argument("rep", type=int)

    def _receipt(a):
        write_receipt(a.case, a.rep)
        adjudicate(a.case, a.rep)
        return 0
    sp.set_defaults(func=_receipt)
    sub.add_parser("summary").set_defaults(func=lambda a: cmd_summary())
    sub.add_parser("status").set_defaults(func=lambda a: cmd_status())
    args = ap.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
