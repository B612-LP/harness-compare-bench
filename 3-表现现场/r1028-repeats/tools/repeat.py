#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r1028-repeats：贴线题重复跑（bird / dabstep / tb），每款每格补 2 次 → n=3。

用法：
    python3 tools/repeat.py --agent codex --reps 2,3
    python3 tools/repeat.py --agent dsh   --reps 2,3

- 工作区：~/bench-workspaces/r1028/<agent>/<case>__r<N>/（仓库外，只放 inputs/ + TASK.md）
- 证据：<batch>/runs/<agent>__<case>__r<N>/
        （workspace 产物 / agent.jsonl / agent.stderr.txt / meta.json / checker.stdout.json / agent-session/）
- 判分：2-用例/<case>/checker.py <ws> --json
- 越界扫描：复用 r1027 的规则（lab.scan_integrity）

与 r1027 的区别：每场独立工作区（不复用）、独立证据目录（不覆盖 r1025/r1027 的 n=1 证据）。
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
BATCH = TOOLS.parent
REPO = BATCH.parents[1]
CASE_ROOT = REPO / "2-用例"
WS_ROOT = Path.home() / "bench-workspaces" / "r1028"
RUNS = BATCH / "runs"
CASES = ["bird-ca-schools-15", "dabstep-payments-10", "tb-cargo-plan"]
MODEL = "deepseek-flash"
EFFORT = "low"

spec = importlib.util.spec_from_file_location(
    "lab", REPO / "3-表现现场" / "r1027-isolated" / "tools" / "lab.py")
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)  # type: ignore[union-attr]


def now_iso() -> str:
    import datetime as dt
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def prepare(agent: str, case: str, rep: int, ws: Path) -> dict:
    if ws.exists():
        shutil.rmtree(ws)
    shutil.copytree(CASE_ROOT / case / "inputs", ws / "inputs")
    task = lab.build_task(agent, case, ws, for_gui=False)
    (ws / "TASK.md").write_text(task, encoding="utf-8")
    carried = [{"path": str(p.relative_to(ws)), "sha256": sha(p), "bytes": p.stat().st_size}
               for p in sorted((ws / "inputs").rglob("*")) if p.is_file()]
    meta = {"product": agent, "case": case, "rep": rep, "form": "cli",
            "workspace": str(ws), "created_at": now_iso(), "model": MODEL,
            "reasoning_effort": EFFORT,
            "soft_constraints": ["stay-in-workspace", "no-oracle-hunt", "offline"],
            "prompt_sha256": hashlib.sha256(task.encode()).hexdigest(), "inputs": carried}
    (ws / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                                  encoding="utf-8")
    return meta


def judge(ws: Path, case: str) -> dict:
    p = subprocess.run([sys.executable, str(CASE_ROOT / case / "checker.py"), str(ws), "--json"],
                       capture_output=True, text=True, timeout=1800, cwd=str(REPO))
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        return {"reward": None, "error": (p.stdout + p.stderr)[-2000:]}


def trace_steps(agent: str, log: Path) -> int:
    if not log.exists():
        return 0
    n = 0
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if agent == "codex" and ev.get("type") == "item.started":
            n += 1
        elif agent == "dsh" and ev.get("type") == "tool_call":
            n += 1
    return n


def archive(agent: str, case: str, rep: int, ws: Path, log: Path, err: Path,
            started: str, duration: float, res: dict, meta: dict, extra: dict) -> Path:
    dest = RUNS / ("%s__%s__r%d" % (agent, case, rep))
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "workspace").mkdir(parents=True)
    for p in ws.iterdir():
        if p.name in ("inputs", "agent.jsonl", "agent.stderr.txt"):
            continue
        if p.is_dir():
            shutil.copytree(p, dest / "workspace" / p.name)
        else:
            shutil.copy2(p, dest / "workspace" / p.name)
    if log.exists():
        shutil.copy2(log, dest / "agent.jsonl")
    if err.exists():
        shutil.copy2(err, dest / "agent.stderr.txt")
    integ = lab.scan_integrity(log)
    meta.update({"status": "done", "started_at": started, "duration_s": duration,
                 "steps": trace_steps(agent, log),
                 "reward": res.get("reward"), "weighted": res.get("weighted"),
                 "failed": [c.get("id") for c in res.get("checks", []) if not c.get("pass")],
                 "judge": res, "integrity": integ,
                 "integrity_verdict": "clean" if integ["violations"] == 0 else "violation"})
    meta.update(extra)
    (dest / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                                    encoding="utf-8")
    (dest / "checker.stdout.json").write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n",
                                              encoding="utf-8")
    # 会话轨迹
    sess = dest / "agent-session"
    sess.mkdir(exist_ok=True)
    t0 = time.time() - duration - 30
    if agent == "codex":
        files = [q for q in (lab.CODEX_HOME / "sessions").rglob("*.jsonl")
                 if q.stat().st_mtime >= t0]
        files.sort(key=lambda q: q.stat().st_mtime, reverse=True)
        if files:
            shutil.copy2(files[0], sess / files[0].name)
    else:
        for cand in (Path.home() / ".dsh" / "sessions").iterdir():
            if not cand.is_dir() or not cand.name.endswith("-%s--" % ws.name):
                continue
            for q in cand.rglob("*"):
                if q.is_file() and q.suffix != ".lock":
                    tgt = sess / q.name
                    if not tgt.exists():
                        shutil.copy2(q, tgt)
    return dest


def run_one(agent: str, case: str, rep: int) -> dict:
    ws = WS_ROOT / agent / ("%s__r%d" % (case, rep))
    meta = prepare(agent, case, rep, ws)
    prompt = (ws / "TASK.md").read_text(encoding="utf-8")
    key = lab.load_api_key()
    cj = CASE_ROOT / case / "case.json"
    timeout = json.loads(cj.read_text()).get("timeout_s", 2400) if cj.exists() else 2400
    log = BATCH / (".tmp-%s__%s__r%d.agent.jsonl" % (agent, case, rep))
    err = BATCH / (".tmp-%s__%s__r%d.agent.stderr.txt" % (agent, case, rep))
    if agent == "codex":
        env = dict(os.environ, CODEX_HOME=str(lab.CODEX_HOME),
                   DEEPSEEK_API_KEY=key, RUST_LOG="warn")
        cmd = ["codex", "exec", "--json", "--skip-git-repo-check", "-C", str(ws),
               "-m", MODEL, "-c", 'model_reasoning_effort="%s"' % EFFORT, "-"]
    else:
        env = dict(os.environ, DEEPSEEK_API_KEY=key)
        cmd = ["dsh", "bench-cli", "--json", "-"]
    started = now_iso()
    t0 = time.time()
    status, exit_code = "ok", None
    with log.open("w", encoding="utf-8") as out, err.open("w", encoding="utf-8") as er:
        try:
            p = subprocess.run(cmd, cwd=str(ws), env=env, input=prompt, text=True,
                               stdout=out, stderr=er, timeout=timeout)
            exit_code = p.returncode
        except subprocess.TimeoutExpired:
            status, exit_code = "timeout", None
    duration = round(time.time() - t0, 1)
    res = judge(ws, case)
    dest = archive(agent, case, rep, ws, log, err, started, duration, res, meta,
                   {"runner_status": status, "exit_code": exit_code,
                    "workspace": str(ws), "batch": "r1028-repeats"})
    for tmp in (log, err):
        tmp.unlink(missing_ok=True)
    row = {"agent": agent, "case": case, "rep": rep, "reward": res.get("reward"),
           "weighted": res.get("weighted"), "duration_s": duration,
           "steps": json.loads((dest / "meta.json").read_text())["steps"],
           "failed": [c.get("id") for c in res.get("checks", []) if not c.get("pass")],
           "integrity_violations": json.loads((dest / "meta.json").read_text())
           ["integrity"]["violations"], "runner_status": status, "run_dir": str(dest)}
    with (BATCH / ("results-%s.jsonl" % agent)).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print("[%s / %s / r%d] status=%s reward=%s weighted=%s %ss steps=%s 越界=%d -> %s" % (
        agent, case, rep, status, res.get("reward"), res.get("weighted"), duration,
        int(row["steps"]), row["integrity_violations"], dest), flush=True)
    return row


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True, choices=["codex", "dsh"])
    ap.add_argument("--reps", default="2,3")
    ap.add_argument("--cases", default=",".join(CASES))
    a = ap.parse_args(argv)
    reps = [int(x) for x in a.reps.split(",") if x.strip()]
    cases = [x.strip() for x in a.cases.split(",") if x.strip()]
    print("batch=%s agent=%s cases=%s reps=%s" % (BATCH, a.agent, cases, reps), flush=True)
    for case in cases:
        for rep in reps:
            try:
                run_one(a.agent, case, rep)
            except Exception as e:  # 单场失败不阻断整条 lane
                print("!! run failed %s/%s/r%d: %r" % (a.agent, case, rep, e), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
