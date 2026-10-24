#!/usr/bin/env python3
"""区分度探针批次（Codex 0.163.0 / DSH 0.2.0-rc.2 × DeepSeek V4.1-Flash × thinking=low）。

目的：新题库选型前，对候选题做「小样本实测」——同一道题在 A 组两款 CLI 上跑一遍，
      记录 reward / 耗时 / 工具调用，用来判断该题是否落在 30%~75% 的区分度目标区。

协议
----
- 每个候选题一个目录：`cases/<case>/`，含
    prompt.md     任务书（自包含；可用 {run_dir} 占位）
    checker.py    判分器（`python3 checker.py <run_dir> --json`，reward 0/1）
    case.json     {"inputs": [["srcrel", "dstdirrel"], ...], "timeout_s": 1800}
    inputs/...    随题素材（按 case.json 拷进 run_dir）
- 每个 (case, agent) 一个 run_dir：`<BATCH>/<case>__<agent>/`
- 变量固定：deepseek-flash / thinking=low / 联网关 / SKILL 关（与 r1023 批次一致）

用法
----
python3 tools/probe.py --cases all --agents both
python3 tools/probe.py --cases lcb-hard --agents codex --force
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

REPO = Path(__file__).resolve().parents[3]          # .../harness-compare-bench
BATCH = Path(__file__).resolve().parents[1]          # .../r1024-probe-区分度
CASES_DIR = BATCH / "cases"
CODEX_HOME = BATCH / "codex-home"
DSH_PROFILE = "bench-cli"
MODEL = "deepseek-flash"
REASONING = "low"

ENV_NOTE = """
---
（评测注入，不改任务本身）当前工作目录即上文的运行目录：{run_dir}
所有读写都在这个目录内完成；不联网。完成后直接结束，不需要额外解释。
---
"""


def discover_cases() -> dict:
    cases = {}
    if not CASES_DIR.exists():
        return cases
    for d in sorted(CASES_DIR.iterdir()):
        meta = d / "case.json"
        if not (d.is_dir() and meta.exists()):
            continue
        spec = json.loads(meta.read_text(encoding="utf-8"))
        cases[d.name] = {
            "inputs": [tuple(x) for x in spec.get("inputs", [])],
            "timeout_s": spec.get("timeout_s", 1800),
        }
    return cases


CASES = discover_cases()


def load_api_key() -> str:
    """从 DSH 凭据库读取 DeepSeek key（只进内存与子进程 env，绝不落盘）."""
    cred = Path.home() / ".dsh" / ".credentials.yaml"
    text = cred.read_text(encoding="utf-8")
    m = re.search(r"^refs:\n((?:  .*\n)+)", text, re.M)
    if not m:
        raise SystemExit("credentials: refs 段未找到")
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        if k.strip() == "DEEPSEEK_API_KEY":
            return v.strip()
    raise SystemExit("credentials: DEEPSEEK_API_KEY 未找到")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_prompt(case: str, run_dir: Path) -> str:
    prompt_path = CASES_DIR / case / "prompt.md"
    if not prompt_path.exists():
        prompt_path = CASES_DIR / case / "instruction.md"
    text = prompt_path.read_text(encoding="utf-8")
    return text.replace("{run_dir}", str(run_dir)).rstrip() + "\n" + ENV_NOTE.format(run_dir=run_dir)


def prepare(case: str, agent: str, force: bool) -> Path:
    run_dir = BATCH / f"{case}__{agent}"
    if run_dir.exists():
        if not force:
            raise SystemExit(f"{run_dir} 已存在（用 --force 覆盖）")
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True)

    carried = []
    for src_rel, dst_rel in CASES[case]["inputs"]:
        src = CASES_DIR / case / src_rel
        dst = run_dir / dst_rel
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
            for p in sorted(dst.rglob("*")):
                if p.is_file():
                    carried.append({"path": str(p.relative_to(run_dir)), "sha256": sha(p), "bytes": p.stat().st_size})
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            carried.append({"path": dst_rel, "sha256": sha(dst), "bytes": dst.stat().st_size})

    prompt = build_prompt(case, run_dir)
    (run_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    meta = {
        "case": case,
        "agent": agent,
        "model": MODEL,
        "reasoning_effort": REASONING,
        "started_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "inputs": carried,
        "cwd": str(run_dir),
    }
    (run_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return run_dir


def run_codex(run_dir: Path, prompt: str, key: str, timeout: int):
    env = dict(os.environ, CODEX_HOME=str(CODEX_HOME), DEEPSEEK_API_KEY=key, RUST_LOG="warn")
    cmd = [
        "codex", "exec", "--json", "--skip-git-repo-check",
        "-C", str(run_dir), "-m", MODEL,
        "-c", f'model_reasoning_effort="{REASONING}"',
        "-",
    ]
    return cmd, env, prompt


def run_dsh(run_dir: Path, prompt: str, key: str, timeout: int):
    env = dict(os.environ, DEEPSEEK_API_KEY=key)
    cmd = ["dsh", DSH_PROFILE, "--json", "-"]
    return cmd, env, prompt


def collect_dsh_session(run_dir: Path) -> None:
    sess_root = Path.home() / ".dsh" / "sessions"
    suffix = f"-{run_dir.name}--"
    cands = [p for p in sess_root.iterdir() if p.is_dir() and p.name.endswith(suffix)] if sess_root.exists() else []
    if not cands:
        return
    dst = run_dir / "agent-session"
    dst.mkdir(exist_ok=True)
    for cand in cands:
        for p in sorted(cand.rglob("*")):
            if p.is_file() and p.suffix != ".lock":
                target = dst / p.name
                if not target.exists():
                    shutil.copy2(p, target)


def collect_codex_session(run_dir: Path) -> None:
    sess = CODEX_HOME / "sessions"
    if not sess.exists():
        return
    dst = run_dir / "agent-session"
    dst.mkdir(exist_ok=True)
    files = sorted(sess.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if files:
        shutil.copy2(files[0], dst / files[0].name)


def judge(case: str, run_dir: Path) -> dict:
    checker = CASES_DIR / case / "checker.py"
    p = subprocess.run(
        [sys.executable, str(checker), str(run_dir), "--json"],
        capture_output=True, text=True, timeout=600,
    )
    (run_dir / "checker.stdout.txt").write_text(p.stdout + p.stderr, encoding="utf-8")
    try:
        res = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        res = {"reward": None, "error": "checker output unparsable", "exit": p.returncode}
    return res


def parse_events(log_path: Path) -> dict:
    """从 --json 事件流里拿 usage / 工具调用统计（尽力而为）."""
    usage, by_tool, steps = {}, {}, 0
    if not log_path.exists():
        return {"usage": usage, "tool_calls": 0, "by_tool": by_tool, "steps": 0}
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        u = ev.get("usage") or (ev.get("message") or {}).get("usage")
        if isinstance(u, dict):
            usage = u
        t = ev.get("type") or ev.get("event")
        if t in ("tool_call", "tool_use", "function_call", "tool_call_begin", "item.started"):
            steps += 1
            def _name(v):
                if isinstance(v, dict):
                    return v.get("name")
                return v if isinstance(v, str) else None

            name = _name(ev.get("name")) or _name(ev.get("tool")) or _name(ev.get("item")) or "?"
            by_tool[name] = by_tool.get(name, 0) + 1
    return {"usage": usage, "tool_calls": steps, "by_tool": by_tool, "steps": steps}


def run_one(case: str, agent: str, key: str, timeout: int, force: bool) -> dict:
    t0 = time.time()
    run_dir = prepare(case, agent, force)
    prompt = (run_dir / "prompt.txt").read_text(encoding="utf-8")
    cmd, env, stdin_text = (run_codex if agent == "codex" else run_dsh)(run_dir, prompt, key, timeout)

    log_path = run_dir / "agent.jsonl"
    err_path = run_dir / "agent.stderr.txt"
    status, exit_code = "ok", None
    try:
        with log_path.open("w", encoding="utf-8") as out, err_path.open("w", encoding="utf-8") as err:
            p = subprocess.run(
                cmd, cwd=str(run_dir), env=env, input=stdin_text,
                stdout=out, stderr=err, text=True, timeout=timeout,
            )
        exit_code = p.returncode
    except subprocess.TimeoutExpired:
        status = "timeout"
    except Exception as exc:  # noqa: BLE001
        status = f"error: {exc}"

    if agent == "dsh":
        collect_dsh_session(run_dir)
    else:
        collect_codex_session(run_dir)

    res = judge(case, run_dir)
    duration = round(time.time() - t0, 1)
    meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
    meta.update(
        {
            "status": status,
            "exit_code": exit_code,
            "duration_s": duration,
            "reward": res.get("reward"),
            "weighted": res.get("weighted"),
            "failed": [c.get("id") for c in res.get("checks", []) if not c.get("pass")],
            "checker": {k: v for k, v in res.items() if k not in ("checks",)},
        }
    )
    meta.update(parse_events(log_path))
    (run_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"[{case} / {agent}] status={status} reward={meta['reward']} "
        f"weighted={meta['weighted']} {duration}s tools={meta['tool_calls']} failed={meta['failed']}",
        flush=True,
    )
    return meta


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default="all")
    ap.add_argument("--agents", default="both", choices=["codex", "dsh", "both"])
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    if not CASES:
        raise SystemExit(f"没有找到候选题：{CASES_DIR}/<case>/case.json 不存在")
    cases = list(CASES) if args.cases == "all" else [c.strip() for c in args.cases.split(",")]
    agents = ["codex", "dsh"] if args.agents == "both" else [args.agents]
    key = load_api_key()

    results = []
    for case in cases:
        for agent in agents:
            try:
                results.append(run_one(case, agent, key, args.timeout, args.force))
            except SystemExit as exc:
                print(f"[{case} / {agent}] SKIP: {exc}", flush=True)

    out = BATCH / "probe-results.json"
    prev = []
    if out.exists():
        try:
            prev = json.loads(out.read_text(encoding="utf-8"))
        except Exception:
            prev = []
    keep = {(r["case"], r["agent"]): r for r in prev}
    for r in results:
        keep[(r["case"], r["agent"])] = r
    merged = sorted(keep.values(), key=lambda r: (r["case"], r["agent"]))
    out.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"--- wrote {out} ({len(merged)} runs) ---", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))