#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mutation-negatives 执行器（判卷审计 2026-10-26）。

职责：读取 negatives-manifest.json，用真实命令逐组调用五个案例的 canonical
`checker.py` 判分负例产物，采集原始 stdout/stderr 日志与结果 JSON，和预期
对照后汇总 results.json。

原则：
  - 判卷器 = 2-用例/<case>/checker.py 原样调用（不修改、不 import 复用）；
  - 数字一律来自真实执行输出；命令行原文写入 results.json 与 commands.log；
  - 只写本目录（logs/ 与 results.json）；2-用例 与仓库其他目录只读。

用法：python3 run_negatives.py [--only case_substring]
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[2]
CASES = REPO / "2-用例"
NEG = OUT / "negatives"
LOGS = OUT / "logs"
MANIFEST = OUT / "negatives-manifest.json"
RESULTS = OUT / "results.json"
COMMANDS_LOG = OUT / "commands.log"

CASE_CHECKER = {
    "bird-ca-schools-15": "bird-ca-schools-15/checker.py",
    "dabstep-payments-10": "dabstep-payments-10/checker.py",
    "exercism-py-6": "exercism-py-6/checker.py",
    "lcb-recent-hard-4": "lcb-recent-hard-4/checker.py",
    "tb-cargo-plan": "tb-cargo-plan/checker.py",
}
CASE_TRACKS = {
    "dabstep-payments-10": ["official-compat", "strict-contract"],
}


def red_ids(case: str, payload: dict) -> list[str]:
    """按各判卷器结果结构提取「判红的观察项 id」（checks 里的 id 即判卷器口径）。"""
    checks = payload.get("checks") or []
    return sorted(c["id"] for c in checks if not c.get("pass"))


def summarize(case: str, payload: dict) -> dict:
    """提取统一字段 + 各判卷器特有字段（原样保留，不加工）。"""
    extra = {}
    if case == "bird-ca-schools-15":
        extra = {k: payload.get(k) for k in
                 ("accuracy", "correct", "failed_questions", "input_integrity")}
    elif case == "dabstep-payments-10":
        extra = {k: payload.get(k) for k in ("correct", "score_rate", "gates", "failed")}
    elif case == "exercism-py-6":
        extra = {"per_exercise": {c["id"]: bool(c.get("pass"))
                                  for c in payload["checks"] if c["id"] != "input_integrity"}}
    elif case == "lcb-recent-hard-4":
        extra = {"passed_problems": payload.get("passed_problems"),
                 "fail_kinds": {c["id"]: c.get("fail_kind") for c in payload["checks"]
                                if c["id"] != "input_integrity" and not c.get("pass")}}
    elif case == "tb-cargo-plan":
        extra = {"passed": payload.get("passed"), "total": payload.get("total"),
                 "critical_ok": payload.get("critical_ok")}
    return {"reward": payload.get("reward"), "weighted": payload.get("weighted"),
            "red_ids": red_ids(case, payload), "extra": extra}


def check_expectation(case: str, expect: dict, run: dict) -> tuple[bool, list[str]]:
    problems = []
    want_reward = expect.get("reward")
    if isinstance(want_reward, dict):  # dab 双轨
        want_reward = want_reward.get(run.get("track"))
    if want_reward is not None and run["reward"] != want_reward:
        problems.append("reward=%r 期望 %r" % (run["reward"], want_reward))
    red = set(run["red_ids"])

    def norm_prefix(ids: list[str]) -> list[str]:
        # bird 的预期 id 用 "q28"，checks 里也是 "q28"，无需转换；保险起见原样比对
        return list(ids)

    for rid in norm_prefix(expect.get("item_red", []) or []):
        if rid not in red:
            problems.append("预期红但未红: %s" % rid)
    for gid in norm_prefix(expect.get("item_green", []) or []):
        if gid in red:
            problems.append("预期绿但变红: %s" % gid)
    for rid in (expect.get("item_red_contains") or []):
        if rid not in red:
            problems.append("预期红但未红: %s" % rid)
    if (expect.get("item_red_contains") == [] and want_reward == 1
            and case == "tb-cargo-plan" and run["red_ids"]):
        problems.append("预期全绿但出现红项: %s" % ",".join(run["red_ids"]))
    return (not problems), problems


def parse_payload(stdout: str) -> dict | None:
    lines = [l for l in stdout.strip().splitlines() if l.strip()]
    if not lines:
        return None
    for line in reversed(lines[-3:]):  # 末行优先，容错带前缀输出
        candidate = line
        if candidate.startswith("RESULTS_JSON "):
            candidate = candidate[len("RESULTS_JSON "):]
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except Exception:
            continue
    return None


def run_one(argv: list[str], log_path: Path) -> dict:
    t0 = time.monotonic()
    proc = subprocess.run(argv, capture_output=True, text=True, cwd=str(REPO), timeout=1800)
    duration = round(time.monotonic() - t0, 2)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path = None
    if proc.stderr.strip():
        stderr_path = log_path.with_suffix(".stderr.txt")
        stderr_path.write_text(proc.stderr, encoding="utf-8")
    payload = parse_payload(proc.stdout)
    return {
        "exit_code": proc.returncode,
        "duration_s": duration,
        "payload": payload,
        "stdout_log": str(log_path.relative_to(OUT)),
        "stderr_log": str(stderr_path.relative_to(OUT)) if stderr_path else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="只跑 case/id 包含该子串的条目")
    args = ap.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    # 正对照：直接扫描 negatives/ 下 _oracle 目录
    controls = []
    for case in CASE_CHECKER:
        oracle_dir = NEG / case / "_oracle"
        if oracle_dir.is_dir():
            controls.append({"case": case, "id": "_oracle", "family": "正对照",
                             "desc": "solution/ 原样（环境正控制）",
                             "target": "none", "expect": {"reward": 1, "item_red": []},
                             "run_dir": str(oracle_dir.relative_to(OUT))})

    all_rows = controls + manifest["negatives"]
    results = []
    cmd_log_lines = []
    for row in all_rows:
        case = row["case"]
        if args.only and args.only not in case and args.only not in row["id"]:
            continue
        run_dir = OUT / row["run_dir"]
        checker = CASES / CASE_CHECKER[case]
        tracks = CASE_TRACKS.get(case, [None])
        entry = {"case": case, "id": row["id"], "family": row["family"],
                 "desc": row["desc"], "target": row.get("target"),
                 "expect_note": row.get("expect_note"),
                 "expect": row.get("expect"), "runs": []}
        for track in tracks:
            argv = [sys.executable, str(checker), str(run_dir), "--json"]
            if track:
                argv += ["--scoring", track]
            log_name = row["id"] + (("." + track) if track else "") + ".stdout.txt"
            log_path = LOGS / case / log_name
            cmd_text = " ".join([argv[0].split("/")[-1], "checker.py", str(run_dir), "--json"]
                                + (["--scoring", track] if track else []))
            cmd_log_lines.append("%s\n  # cwd=%s" % (" ".join(argv), REPO))
            try:
                run = run_one(argv, log_path)
            except subprocess.TimeoutExpired:
                entry["runs"].append({"track": track, "cmd": argv, "timeout": True})
                continue
            run["track"] = track
            run["cmd"] = argv
            payload = run.pop("payload")
            if payload is None:
                run["parse_error"] = "stdout 末行无法解析为 JSON"
                run["matches_expectation"] = None
            else:
                run.update(summarize(case, payload))
                ok, problems = check_expectation(case, row.get("expect") or {}, run)
                run["matches_expectation"] = ok
                run["expectation_problems"] = problems
            entry["runs"].append(run)
        results.append(entry)

    # 汇总打印
    n_bad = 0
    for entry in results:
        for run in entry["runs"]:
            flag = "?"
            if run.get("matches_expectation") is True:
                flag = "OK"
            elif run.get("matches_expectation") is False:
                flag = "UNEXPECTED"
                n_bad += 1
            print("%-22s %-36s %-16s exit=%-3s reward=%-4s weighted=%-6s %s %s"
                  % (entry["case"], entry["id"], run.get("track") or "-",
                     run.get("exit_code"), run.get("reward"), run.get("weighted"),
                     flag, "; ".join(run.get("expectation_problems") or [])))

    git_head = None
    try:
        git_head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(REPO),
                                  capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        pass
    RESULTS.write_text(json.dumps({
        "meta": {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "repo": str(REPO),
            "git_head": git_head,
            "python": platform.python_version(),
            "checkers": {c: str(CASES / p) for c, p in CASE_CHECKER.items()},
            "note": "所有数字来自对 canonical checker.py 的真实调用；stdout 原文在 logs/<case>/",
            "unexpected_count": n_bad,
        },
        "results": results,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    COMMANDS_LOG.write_text("\n".join(cmd_log_lines) + "\n", encoding="utf-8")
    print("\nresults.json / commands.log 已写入；UNEXPECTED=%d" % n_bad)
    return 0


if __name__ == "__main__":
    sys.exit(main())
