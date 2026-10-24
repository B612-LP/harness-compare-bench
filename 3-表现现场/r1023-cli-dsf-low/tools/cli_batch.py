#!/usr/bin/env python3
"""A 组 CLI 批次（Codex 0.163.0 / DSH 0.2.0-rc.2 × DeepSeek V4.1-Flash × thinking=low）。

协议
----
- 每个 (agent, case) 一个 run_dir：`3-表现现场/r1023-cli-dsf-low/<case>__<agent>/`
- 输入按用例约定复制进 run_dir（`/app/*` 形态用例复制到根目录；`environment/`、`inputs/` 形态保留子目录）
- 任务书 = `2-用例/<case>/instruction.md`，仅把 `/app/` 前缀替换为 run_dir 绝对路径，另加一段环境说明（见 ENV_NOTE）
- agent 的 cwd = run_dir，产物直接落 run_dir
- 判分 = `python3 2-用例/<case>/checker.py <run_dir> --json`（bail-out：reward 只认这个）
- 变量固定：模型 deepseek-flash、思考档位 low、联网关、SKILL 工具关（见 codex-home/config.toml 与 bench-cli patch）

用法
----
python3 tools/cli_batch.py --cases all --agents both        # 10 场全跑
python3 tools/cli_batch.py --cases int-sum-sort --agents codex
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
BATCH = Path(__file__).resolve().parents[1]          # .../r1023-cli-dsf-low
CASES_DIR = REPO / "2-用例"
CODEX_HOME = BATCH / "codex-home"
DSH_PROFILE = "bench-cli"
MODEL = "deepseek-flash"
REASONING = "low"

CASES = {
    "int-sum-sort": {
        "inputs": [("environment/input.txt", "input.txt")],
        "app_style": True,
    },
    "word-freq-report": {
        "inputs": [("environment/corpus.txt", "corpus.txt")],
        "app_style": True,
    },
    "jielong-fullchain": {
        "inputs": [
            ("environment/jielong.txt", "environment/jielong.txt"),
            ("environment/peers.json", "environment/peers.json"),
            ("environment/orders.json", "environment/orders.json"),
        ],
        "app_style": False,
    },
    "ledger-replay": {
        "inputs": [("environment/events.jsonl", "events.jsonl")],
        "app_style": True,
    },
    "corpus-squeeze": {
        "inputs": [("inputs/corpus.txt", "inputs/corpus.txt")],
        "app_style": False,
    },
}

ENV_NOTE = """
---
（评测注入，不改任务本身）当前工作目录即上文的运行目录：{run_dir}
所有读写都在这个目录内完成；不联网。完成后直接结束，不需要额外解释。
---
"""


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
    spec = CASES[case]
    text = (CASES_DIR / case / "instruction.md").read_text(encoding="utf-8")
    if spec["app_style"]:
        text = text.replace("/app/", str(run_dir) + "/")
    return text.rstrip() + "\n" + ENV_NOTE.format(run_dir=run_dir)


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
        "prompt_rewrites": ["/app/ -> run_dir 绝对路径"] if CASES[case]["app_style"] else [],
        "inputs": carried,
        "cwd": str(run_dir),
    }
    (run_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return run_dir


def run_codex(run_dir: Path, prompt: str, key: str, timeout: int):
    env = dict(
        os.environ,
        CODEX_HOME=str(CODEX_HOME),
        DEEPSEEK_API_KEY=key,
        RUST_LOG="warn",
    )
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
    """把 DSH 本场会话文件复制进 run_dir（证据随目录走）."""
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


def parse_usage(log_path: Path) -> dict:
    """从 --json 事件流里拿最后一次 usage / token 统计（尽力而为）."""
    usage = {}
    if not log_path.exists():
        return usage
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
    return usage


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
            "usage": parse_usage(log_path),
        }
    )
    (run_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"[{case} / {agent}] status={status} reward={meta['reward']} "
        f"weighted={meta['weighted']} {duration}s failed={meta['failed']}",
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

    out = BATCH / "batch-results.json"
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
