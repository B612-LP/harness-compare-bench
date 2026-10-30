#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r1027-isolated：把跑批工作区搬到仓库外 + 题面软约束 + CLI 跑批/判分/归档。

用法：
    python3 tools/lab.py prepare <product> <case>    # 建工作区与题面（workbuddy/doubao/codex/dsh）
    python3 tools/lab.py run <agent> <case>          # 只支持 codex/dsh；跑完判分并归档
    python3 tools/lab.py judge <product> <case>      # 只判分
    python3 tools/lab.py integrity <product> <case>  # 扫轨迹越界痕迹
"""
from __future__ import annotations

import argparse
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
WS_ROOT = Path.home() / "bench-workspaces" / "r1027"
RUNS = BATCH / "runs"
CODEX_HOME = REPO / "3-表现现场" / "r1025-candidates" / "codex-home"
DSH_PROFILE = "bench-cli"
MODEL = "deepseek-flash"
EFFORT = "low"

PRODUCTS = {
    "workbuddy": "WorkBuddy 桌面端",
    "doubao": "豆包 办公",
    "codex": "Codex CLI",
    "dsh": "DSH CLI",
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


def now_iso() -> str:
    import datetime as dt
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def ws_dir(product: str, case: str) -> Path:
    return WS_ROOT / product / case


def run_ev(product: str, case: str) -> Path:
    return RUNS / ("%s__%s" % (product, case))


def build_task(product: str, case: str, run_dir: Path, for_gui: bool) -> str:
    body = (CASE_ROOT / case / "instruction.md").read_text(encoding="utf-8").rstrip()
    label = PRODUCTS[product]
    head = (
        "# 本场任务：%s（%s）\n\n"
        "**你的工作目录（绝对路径）：`%s`**\n\n"
        "请在这个目录里工作：输入都在该目录的 `inputs/` 下，产物按题目要求写到该目录里"
        "（题目里的相对路径都相对这个目录）。除题目明确要求修改的代码外，不要改动 `inputs/` 下的文件。\n\n"
        "---\n\n" % (case, label, run_dir)
    )
    return head + body + "\n" + DISCIPLINE


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cmd_prepare(product: str, case: str) -> int:
    if product not in PRODUCTS:
        print("未知产品：%s（可选：%s）" % (product, ", ".join(PRODUCTS)))
        return 2
    if not (CASE_ROOT / case / "inputs").is_dir():
        print("没有这个用例：%s" % case)
        return 2
    ws = ws_dir(product, case)
    if ws.exists():
        shutil.rmtree(ws)
    (ws / "inputs").parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(CASE_ROOT / case / "inputs", ws / "inputs")
    task = build_task(product, case, ws, for_gui=product in ("workbuddy", "doubao"))
    (ws / "TASK.md").write_text(task, encoding="utf-8")
    carried = [{"path": str(p.relative_to(ws)), "sha256": sha(p), "bytes": p.stat().st_size}
               for p in sorted((ws / "inputs").rglob("*")) if p.is_file()]
    meta = {"product": product, "case": case, "form": "desktop-GUI" if product in ("workbuddy", "doubao") else "cli",
            "workspace": str(ws), "created_at": now_iso(), "model": None if product in ("workbuddy", "doubao") else MODEL,
            "reasoning_effort": None if product in ("workbuddy", "doubao") else EFFORT,
            "soft_constraints": ["stay-in-workspace", "no-oracle-hunt", "offline"],
            "prompt_sha256": hashlib.sha256(task.encode()).hexdigest(), "inputs": carried}
    (ws / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("工作区: %s" % ws)
    print("题面  : %s（%d 字，含工作纪律）" % (ws / "TASK.md", len(task)))
    return 0


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


def judge(product: str, case: str) -> dict:
    ws = ws_dir(product, case)
    p = subprocess.run([sys.executable, str(CASE_ROOT / case / "checker.py"), str(ws), "--json"],
                       capture_output=True, text=True, timeout=1200, cwd=str(REPO))
    try:
        res = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        res = {"reward": None, "error": (p.stdout + p.stderr)[-2000:]}
    return res


def scan_integrity(log: Path) -> dict:
    pats = ["2-用例", "truth.json", "checker.py", "reference/", "solution/", "../", "~/Documents",
            "harness-compare-bench"]
    hits = []
    if log.exists():
        for i, line in enumerate(log.read_text(encoding="utf-8", errors="replace").splitlines()):
            try:
                ev = json.loads(line)
            except Exception:
                continue
            blob = json.dumps(ev.get("input") or ev.get("item") or ev, ensure_ascii=False)
            if any(p in blob for p in pats):
                hits.append({"line": i + 1, "excerpt": blob[:300]})
            if len(hits) >= 20:
                break
    return {"violations": len(hits), "evidence": hits}


def archive(product: str, case: str, log: Path, err: Path, started: str, duration: float,
            res: dict, extra: dict) -> Path:
    ws = ws_dir(product, case)
    ev = run_ev(product, case)
    if ev.exists():
        shutil.rmtree(ev)
    (ev / "workspace").mkdir(parents=True)
    for p in ws.iterdir():
        if p.name in ("inputs", "agent.jsonl", "agent.stderr.txt"):
            continue
        if p.is_dir():
            shutil.copytree(p, ev / "workspace" / p.name)
        else:
            shutil.copy2(p, ev / "workspace" / p.name)
    if log.exists():
        shutil.copy2(log, ev / "agent.jsonl")
    if err.exists():
        shutil.copy2(err, ev / "agent.stderr.txt")
    integ = scan_integrity(log)
    meta = json.loads((ws / "meta.json").read_text(encoding="utf-8"))
    meta.update({"status": "done", "started_at": started, "duration_s": duration,
                 "reward": res.get("reward"), "weighted": res.get("weighted"),
                 "failed": [c.get("id") for c in res.get("checks", []) if not c.get("pass")],
                 "judge": res, "integrity": integ,
                 "integrity_verdict": "clean" if integ["violations"] == 0 else "violation"})
    meta.update(extra)
    (ev / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ev / "checker.stdout.json").write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ev


def cmd_run(agent: str, case: str) -> int:
    if agent not in ("codex", "dsh"):
        print("run 只支持 codex / dsh（桌面端请用 prepare 后手工跑）")
        return 2
    ws = ws_dir(agent, case)
    if not (ws / "TASK.md").exists():
        cmd_prepare(agent, case)
        ws = ws_dir(agent, case)
    prompt = (ws / "TASK.md").read_text(encoding="utf-8")
    key = load_api_key()
    timeout = json.loads((CASE_ROOT / case / "case.json").read_text()).get("timeout_s", 1800) \
        if (CASE_ROOT / case / "case.json").exists() else 1800
    log = BATCH / ("%s__%s.agent.jsonl" % (agent, case))
    err = BATCH / ("%s__%s.agent.stderr.txt" % (agent, case))
    if agent == "codex":
        env = dict(os.environ, CODEX_HOME=str(CODEX_HOME), DEEPSEEK_API_KEY=key, RUST_LOG="warn")
        cmd = ["codex", "exec", "--json", "--skip-git-repo-check", "-C", str(ws), "-m", MODEL,
               "-c", 'model_reasoning_effort="%s"' % EFFORT, "-"]
    else:
        env = dict(os.environ, DEEPSEEK_API_KEY=key)
        cmd = ["dsh", DSH_PROFILE, "--json", "-"]
    started = now_iso()
    t0 = time.time()
    status = "ok"
    with log.open("w", encoding="utf-8") as out, err.open("w", encoding="utf-8") as er:
        try:
            p = subprocess.run(cmd, cwd=str(ws), env=env, input=prompt, text=True,
                               stdout=out, stderr=er, timeout=timeout)
            exit_code = p.returncode
        except subprocess.TimeoutExpired:
            status, exit_code = "timeout", None
    duration = round(time.time() - t0, 1)
    res = judge(agent, case)
    ev = archive(agent, case, log, err, started, duration, res,
                 {"runner_status": status, "exit_code": exit_code, "workspace": str(ws)})
    # 会话轨迹（Codex 在隔离 CODEX_HOME，DSH 在 ~/.dsh/sessions）
    sess = ev / "agent-session"
    sess.mkdir(exist_ok=True)
    if agent == "codex":
        files = sorted((CODEX_HOME / "sessions").rglob("*.jsonl"), key=lambda q: q.stat().st_mtime, reverse=True)
        if files:
            shutil.copy2(files[0], sess / files[0].name)
    else:
        cands = [q for q in (Path.home() / ".dsh" / "sessions").iterdir()
                 if q.is_dir() and q.name.endswith("-%s--" % ws.name)]
        for cand in cands:
            for q in cand.rglob("*"):
                if q.is_file() and q.suffix != ".lock":
                    tgt = sess / q.name
                    if not tgt.exists():
                        shutil.copy2(q, tgt)
    print("[%s / %s] status=%s reward=%s weighted=%s %.0fs 越界痕迹=%d -> %s" % (
        agent, case, status, res.get("reward"), res.get("weighted"), duration,
        meta_violations(ev), ev))
    return 0


def meta_violations(ev: Path) -> int:
    try:
        return json.loads((ev / "meta.json").read_text(encoding="utf-8"))["integrity"]["violations"]
    except Exception:
        return -1


def cmd_judge(product: str, case: str) -> int:
    res = judge(product, case)
    print(json.dumps({k: res.get(k) for k in ("reward", "weighted", "failed")}, ensure_ascii=False))
    return 0


def cmd_integrity(product: str, case: str) -> int:
    ev = run_ev(product, case)
    log = ev / "agent.jsonl"
    integ = scan_integrity(log)
    print(json.dumps(integ, ensure_ascii=False, indent=2)[:4000])
    return 0


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("prepare")
    sp.add_argument("product"); sp.add_argument("case")
    sp.set_defaults(func=lambda a: cmd_prepare(a.product, a.case))
    sp = sub.add_parser("run")
    sp.add_argument("agent"); sp.add_argument("case")
    sp.set_defaults(func=lambda a: cmd_run(a.agent, a.case))
    sp = sub.add_parser("judge")
    sp.add_argument("product"); sp.add_argument("case")
    sp.set_defaults(func=lambda a: cmd_judge(a.product, a.case))
    sp = sub.add_parser("integrity")
    sp.add_argument("product"); sp.add_argument("case")
    sp.set_defaults(func=lambda a: cmd_integrity(a.product, a.case))
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
