#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r1030-formal-a1：首批正式准入批次运行器。

在冻结规则 freeze-20261029-v2 下运行 A 组 Codex CLI / DSH CLI × 5 题（各 order=1 first）：
- 工作区在仓库外 ~/bench-workspaces/r1030/<product>/<case>/，只含 inputs + TASK.md；
- Codex 用全新隔离 CODEX_HOME（base_url=api.deepseek.com，wire_api=responses）；
- DSH 用既有最小 bench-cli profile（provider deepseek-official，deepseek-flash，low）；
- 每场记录 product_version/route/tools/permissions/skills/started_at/finished_at，
  并做轨迹越界扫描（integrity）；产物、轨迹、判分、会话归档进本目录。

用法：
    python3 tools/lab.py preflight                 # 无模型接口预检（版本/配置/工作区隔离）
    python3 tools/lab.py prepare <product> <case>
    python3 tools/lab.py run <product> <case>      # codex/dsh：跑 + 判分 + 归档
    python3 tools/lab.py judge <product> <case>
    python3 tools/lab.py integrity <product> <case>
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
CASE_ROOT = REPO / "2-用例"
WS_ROOT = Path.home() / "bench-workspaces" / "r1030"
RUNS = BATCH / "runs"
CODEX_HOME = WS_ROOT / "_codex-home"
DSH_PROFILE = "bench-cli"
MODEL = "deepseek-flash"
EFFORT = "low"
RULE = "freeze-20261029-v2"
CASES = ("bird-ca-schools-15", "dabstep-payments-10", "exercism-py-6", "lcb-recent-hard-4", "tb-cargo-plan")
PRODUCTS = ("codex", "dsh")

CODEX_CONFIG = """# r1030-formal-a1 · Codex CLI 隔离 CODEX_HOME · DeepSeek V4.1-Flash · thinking=low
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
    "dsh": {
        "tools": ["builtin shell/read/write 等 bench-cli 基础工具（tool-web/tool-skill/skill-filesystem disabled）"],
        "permissions": "permission preset danger-full-access（approval never，bench-cli cordis.patch.yml）",
        "skills": "off（tool-skill 与 skill-filesystem 均 disabled）",
        "route": {"host": "api.deepseek.com", "provider_id": "deepseek-official", "wire_protocol": "anthropic-messages",
                  "endpoint": None},
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


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def ws_dir(product: str, case: str) -> Path:
    return WS_ROOT / product / case


def run_ev(product: str, case: str) -> Path:
    return RUNS / ("%s__%s" % (product, case))


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


def cli_version(product: str) -> str:
    out = subprocess.run([product if product == "codex" else "dsh", "--version"],
                         capture_output=True, text=True, timeout=60)
    return (out.stdout or out.stderr).strip().splitlines()[0].strip()


def build_task(product: str, case: str, run_dir: Path) -> str:
    body = (CASE_ROOT / case / "instruction.md").read_text(encoding="utf-8").rstrip()
    label = "Codex CLI" if product == "codex" else "DSH CLI"
    head = (
        "# 本场任务：%s（%s）\n\n"
        "**你的工作目录（绝对路径）：`%s`**\n\n"
        "请在这个目录里工作：输入都在该目录的 `inputs/` 下，产物按题目要求写到该目录里"
        "（题目里的相对路径都相对这个目录）。除题目明确要求修改的代码外，不要改动 `inputs/` 下的文件。\n\n"
        "---\n\n" % (case, label, run_dir)
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
    """零模型调用的接口预检：版本、配置落盘、工作区隔离、判分器可执行。"""
    receipt = {"kind": "interface_preflight", "model_calls": 0, "at": now_iso(), "rule": RULE}
    for product in PRODUCTS:
        v = cli_version(product)
        receipt[product] = {"version": v}
    # Codex：全新隔离 CODEX_HOME
    if CODEX_HOME.exists():
        shutil.rmtree(CODEX_HOME)
    CODEX_HOME.mkdir(parents=True)
    (CODEX_HOME / "config.toml").write_text(CODEX_CONFIG, encoding="utf-8")
    receipt["codex"]["config_toml"] = str(CODEX_HOME / "config.toml")
    receipt["codex"]["config_sha256"] = sha(CODEX_HOME / "config.toml")
    # DSH：bench-cli profile 配置副本
    prof = Path.home() / ".dsh" / "profiles" / DSH_PROFILE / "cordis.patch.yml"
    receipt["dsh"]["profile"] = str(prof)
    receipt["dsh"]["profile_sha256"] = sha(prof)
    # 隔离演练：为一个假 case 建工作区并断言
    ws = WS_ROOT / "_isolation-probe"
    if ws.exists():
        shutil.rmtree(ws)
    ws.mkdir(parents=True)
    (ws / "inputs").mkdir()
    (ws / "inputs" / "dummy.txt").write_text("probe\n", encoding="utf-8")
    receipt["isolation_probe"] = check_isolation(ws)
    shutil.rmtree(ws)
    # 判分器可执行性：五个 checker --help 式冒烟（--selftest 由正式 selftest 收据单独登记）
    smoke = {}
    for case in CASES:
        p = subprocess.run([sys.executable, str(CASE_ROOT / case / "checker.py"), "--help"],
                           capture_output=True, text=True, timeout=120)
        smoke[case] = {"exit": p.returncode}
    receipt["checker_smoke"] = smoke
    receipt["ok"] = (receipt["isolation_probe"]["ok"]
                     and all(v["exit"] in (0, 2) for v in smoke.values()))
    out = BATCH / "preflight" / "cli-preflight.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": receipt["ok"], "receipt": str(out)}, ensure_ascii=False))
    return 0 if receipt["ok"] else 2


def cmd_prepare(product: str, case: str) -> int:
    ws = ws_dir(product, case)
    if ws.exists():
        shutil.rmtree(ws)
    ws.mkdir(parents=True)
    shutil.copytree(CASE_ROOT / case / "inputs", ws / "inputs")
    task = build_task(product, case, ws)
    (ws / "TASK.md").write_text(task, encoding="utf-8")
    carried = [{"path": str(p.relative_to(ws)), "sha256": sha(p), "bytes": p.stat().st_size}
               for p in sorted((ws / "inputs").rglob("*")) if p.is_file()]
    iso = check_isolation(ws)
    if not iso["ok"]:
        print("隔离检查失败：" + json.dumps(iso, ensure_ascii=False))
        return 2
    meta = {
        "batch": "r1030-formal-a1", "rule_version": RULE, "product": product, "case": case,
        "form": "cli", "workspace": str(ws), "created_at": now_iso(),
        "model": MODEL, "reasoning_effort": EFFORT,
        "product_version": cli_version(product),
        "route": TOOL_FACTS[product]["route"],
        "tools": TOOL_FACTS[product]["tools"],
        "permissions": TOOL_FACTS[product]["permissions"],
        "skills": TOOL_FACTS[product]["skills"],
        "web_search": "disabled", "soft_constraints": ["stay-in-workspace", "no-oracle-hunt", "offline"],
        "prompt_sha256": hashlib.sha256(task.encode()).hexdigest(),
        "isolation": iso, "inputs": carried,
    }
    (ws / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("工作区: %s\n题面  : %s（%d 字）" % (ws, ws / "TASK.md", len(task)))
    return 0


def extract_usage(log: Path) -> dict:
    """从 agent.jsonl 提取 usage 汇总（如有）。"""
    req = n_in = n_out = 0
    if log.exists():
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                ev = json.loads(line)
            except Exception:
                continue
            u = (ev.get("usage") or {}) if isinstance(ev, dict) else {}
            if isinstance(u, dict) and u.get("requests") and isinstance(u.get("inputTokens"), int):
                req += u.get("requests", 0)
                n_in += u.get("inputTokens", 0)
                n_out += u.get("outputTokens", 0)
    return {"requests": req, "input_tokens": n_in, "output_tokens": n_out,
            "note": "runner-side extraction of product-reported usage when present; absent fields stay 0/absent"}


def scan_integrity(log: Path) -> dict:
    hits = []
    if log.exists():
        for i, line in enumerate(log.read_text(encoding="utf-8", errors="replace").splitlines()):
            try:
                ev = json.loads(line)
            except Exception:
                continue
            blob = json.dumps(ev.get("input") or ev.get("item") or ev, ensure_ascii=False)
            for pat in INTEGRITY_PATTERNS:
                if pat in blob:
                    hits.append({"line": i + 1, "pattern": pat, "excerpt": blob[:300]})
                    break
            if len(hits) >= 20:
                break
    return {"violations": len(hits), "patterns": INTEGRITY_PATTERNS, "evidence": hits}


def judge(product: str, case: str) -> dict:
    ws = ws_dir(product, case)
    p = subprocess.run([sys.executable, str(CASE_ROOT / case / "checker.py"), str(ws), "--json"],
                       capture_output=True, text=True, timeout=1200, cwd=str(REPO))
    try:
        res = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        res = {"reward": None, "error": (p.stdout + p.stderr)[-2000:]}
    return res



def capture_session_dsh(ev: Path, ws: Path, started: float) -> None:
    sess = ev / "agent-session"
    sess.mkdir(exist_ok=True)
    base = Path.home() / ".dsh" / "sessions"
    if not base.is_dir():
        return
    for cand in base.iterdir():
        if cand.is_dir() and ("-%s--" % ws.name) in cand.name:
            for q in cand.rglob("*"):
                if q.is_file() and q.suffix != ".lock" and q.stat().st_mtime >= started - 5:
                    tgt = sess / q.name
                    if not tgt.exists():
                        shutil.copy2(q, tgt)


def archive(product: str, case: str, log: Path, err: Path, started: str, finished: str,
            duration: float, res: dict, exit_code, status: str) -> Path:
    ws = ws_dir(product, case)
    ev = run_ev(product, case)
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
    # 日志先移入 staging 再拷贝，避免 rmtree(ev) 连带删除运行日志
    staging = BATCH / "staging"
    staging.mkdir(exist_ok=True)
    log_snap = staging / ("%s__%s.agent.jsonl" % (product, case))
    err_snap = staging / ("%s__%s.agent.stderr.txt" % (product, case))
    if log.exists():
        shutil.move(str(log), str(log_snap))
        shutil.copy2(log_snap, ev / "agent.jsonl")
    if err.exists():
        shutil.move(str(err), str(err_snap))
        shutil.copy2(err_snap, ev / "agent.stderr.txt")
    # 配置快照（路由/权限佐证）
    cfg = ev / "config-snapshot"
    cfg.mkdir(exist_ok=True)
    if product == "codex":
        shutil.copy2(CODEX_HOME / "config.toml", cfg / "codex-config.toml")
    else:
        prof = Path.home() / ".dsh" / "profiles" / DSH_PROFILE
        shutil.copy2(prof / "cordis.patch.yml", cfg / "bench-cli-cordis.patch.yml")
        shutil.copy2(prof / "package.json", cfg / "bench-cli-package.json")
    integ = scan_integrity(log)
    meta = json.loads((ws / "meta.json").read_text(encoding="utf-8"))
    meta.update({
        "status": status, "exit_code": exit_code,
        "started_at": started, "finished_at": finished, "duration_s": duration,
        "usage": extract_usage(log),
        "reward": res.get("reward"), "weighted": res.get("weighted"),
        "failed": [c.get("id") for c in res.get("checks", []) if not c.get("pass")],
        "judge": res,
        "integrity": integ,
        "integrity_verdict": "clean" if integ["violations"] == 0 else "violation",
        "run_id": "r1030-%s-%s" % (product, case),
    })
    (ev / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ev / "checker.stdout.json").write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # 会话轨迹
    st = dt.datetime.fromisoformat(started).timestamp()
    if product == "codex":
        sess = ev / "agent-session"
        sess.mkdir(exist_ok=True)
        sdir = CODEX_HOME / "sessions"
        if sdir.is_dir():
            files = [q for q in sdir.rglob("*.jsonl") if q.stat().st_mtime >= st - 5]
            files.sort(key=lambda q: q.stat().st_mtime, reverse=True)
            for q in files:
                shutil.copy2(q, sess / q.name)
    else:
        capture_session_dsh(ev, ws, st)
    return ev


def cmd_run(product: str, case: str) -> int:
    if product not in PRODUCTS:
        print("run 只支持 codex / dsh")
        return 2
    ws = ws_dir(product, case)
    if not (ws / "TASK.md").exists():
        cmd_prepare(product, case)
    prompt = (ws / "TASK.md").read_text(encoding="utf-8")
    key = load_api_key()
    cj = CASE_ROOT / case / "case.json"
    timeout = json.loads(cj.read_text()).get("timeout_s", 1800) if cj.exists() else 1800
    ev_dir = run_ev(product, case)
    log = ev_dir / "agent.jsonl"
    err = ev_dir / "agent.stderr.txt"
    ev_dir.mkdir(parents=True, exist_ok=True)
    if product == "codex":
        env = dict(os.environ, CODEX_HOME=str(CODEX_HOME), DEEPSEEK_API_KEY=key, RUST_LOG="warn")
        cmd = ["codex", "exec", "--json", "--skip-git-repo-check", "-C", str(ws), "-m", MODEL,
               "-c", 'model_reasoning_effort="%s"' % EFFORT, "-"]
    else:
        env = dict(os.environ, DEEPSEEK_API_KEY=key)
        cmd = ["dsh", DSH_PROFILE, "--json", "-"]
    started = now_iso()
    st_ts = time.time()
    status, exit_code = "ok", None
    with log.open("w", encoding="utf-8") as out, err.open("w", encoding="utf-8") as er:
        try:
            p = subprocess.run(cmd, cwd=str(ws), env=env, input=prompt, text=True,
                               stdout=out, stderr=er, timeout=timeout)
            exit_code = p.returncode
        except subprocess.TimeoutExpired:
            status, exit_code = "timeout", None
    finished = now_iso()
    duration = round(time.time() - st_ts, 1)
    res = judge(product, case)
    ev = archive(product, case, log, err, started, finished, duration, res, exit_code, status)
    meta = json.loads((ev / "meta.json").read_text(encoding="utf-8"))
    print(json.dumps({"product": product, "case": case, "status": status, "exit_code": exit_code,
                      "reward": res.get("reward"), "weighted": res.get("weighted"),
                      "duration_s": duration, "violations": meta["integrity"]["violations"],
                      "evidence": str(ev)}, ensure_ascii=False))
    return 0


def cmd_judge(product: str, case: str) -> int:
    print(json.dumps(judge(product, case), ensure_ascii=False)[:2000])
    return 0


def cmd_integrity(product: str, case: str) -> int:
    print(json.dumps(scan_integrity(run_ev(product, case) / "agent.jsonl"), ensure_ascii=False, indent=2)[:4000])
    return 0


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("preflight").set_defaults(func=lambda a: cmd_preflight())
    sp = sub.add_parser("prepare"); sp.add_argument("product"); sp.add_argument("case")
    sp.set_defaults(func=lambda a: cmd_prepare(a.product, a.case))
    sp = sub.add_parser("run"); sp.add_argument("product"); sp.add_argument("case")
    sp.set_defaults(func=lambda a: cmd_run(a.product, a.case))
    sp = sub.add_parser("judge"); sp.add_argument("product"); sp.add_argument("case")
    sp.set_defaults(func=lambda a: cmd_judge(a.product, a.case))
    sp = sub.add_parser("integrity"); sp.add_argument("product"); sp.add_argument("case")
    sp.set_defaults(func=lambda a: cmd_integrity(a.product, a.case))
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
