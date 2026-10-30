#!/usr/bin/env python3
"""token 计价口径统一复算（阶段报告 v1.0 §5.2 的可复跑证据）。

背景：Codex 的 `n_input_tokens` 含缓存读，DSH 的 `n_input_tokens` 不含（cached 单列）。
直接比较两个原始字段会得到「6–20 倍」的假象；本脚本按统一口径重算：

    Codex 统一输入 = n_input_tokens            （cached 已含在内）
    Codex 未缓存   = n_input_tokens - n_cache_tokens
    DSH   统一输入 = n_input_tokens + n_cache_tokens
    DSH   未缓存   = n_input_tokens

并顺带验证归一化假设（trajectory.final_metrics 恒等式）：
    Codex: total_tokens == total_prompt_tokens + total_completion_tokens
    DSH:   total_tokens == total_prompt_tokens + total_completion_tokens + total_cached_tokens

用法：
    python3 5-评测报告/复算/token-recompute.py            # 打印 Markdown 表 + 恒等式检查
    python3 5-评测报告/复算/token-recompute.py --json     # 机器可读
    python3 5-评测报告/复算/token-recompute.py --selftest # 断言 4 组比值与恒等式，必须全 PASS

退出码：0 通过 / 1 数据缺失或比值不符 / 2 用法错误。
只读本地仓内文件，不联网、不依赖 Docker。
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SITE_DIR = REPO_ROOT / "3-表现现场"

# 阶段报告 §5.2 表内断言值（含缓存比, 未缓存比），来自 2026-10-21 复算
EXPECTED = {
    ("glm-5.3-flash", "int-sum-sort"): (2.09, 2.88),
    ("glm-5.3-flash", "word-freq-report"): (1.18, 1.76),
    ("mimo-v2.6-flash", "int-sum-sort"): (1.66, 1.62),
    ("mimo-v2.6-flash", "word-freq-report"): (1.64, 0.78),
}


def load_runs() -> list[dict]:
    """收集 A 组（codex / dsh）产品运行的 token 账。"""
    runs: list[dict] = []
    for job in sorted(glob.glob(str(SITE_DIR / "r1016*"))):
        if not os.path.isdir(job):
            continue
        for trial in sorted(glob.glob(os.path.join(job, "*", ""))):
            result_path = os.path.join(trial, "result.json")
            if not os.path.isfile(result_path):
                continue
            data = json.load(open(result_path, encoding="utf-8"))
            cfg_path = os.path.join(trial, "config.json")
            cfg = json.load(open(cfg_path, encoding="utf-8")) if os.path.isfile(cfg_path) else {}
            agent = (cfg.get("agent") or {}).get("name") or ""
            if agent not in ("codex", "dsh_agent:Dsh"):
                continue  # 跳过 nop / oracle / bare
            ar = data.get("agent_result") or {}
            runs.append(
                {
                    "job": os.path.basename(job),
                    "trial_dir": trial,
                    "task": data.get("task_name"),
                    "harness": "codex" if agent == "codex" else "dsh",
                    "model": (cfg.get("agent") or {}).get("model_name"),
                    "n_input": ar.get("n_input_tokens"),
                    "n_cache": ar.get("n_cache_tokens") or 0,
                    "n_output": ar.get("n_output_tokens"),
                }
            )
    return runs


def normalize(run: dict) -> tuple[int, int]:
    """返回（统一输入, 未缓存输入）。"""
    n_in, n_cache = run["n_input"], run["n_cache"]
    if run["harness"] == "codex":
        return n_in, n_in - n_cache
    return n_in + n_cache, n_in


def identity_check(run: dict) -> tuple[bool, str]:
    tj = os.path.join(run["trial_dir"], "agent", "trajectory.json")
    if not os.path.isfile(tj):
        return False, f"{run['job']}: 缺 trajectory.json"
    fm = (json.load(open(tj, encoding="utf-8")) or {}).get("final_metrics") or {}
    prompt = fm.get("total_prompt_tokens")
    comp = fm.get("total_completion_tokens")
    cache = fm.get("total_cached_tokens") or 0
    total = (fm.get("extra") or {}).get("total_tokens")
    if None in (prompt, comp, total):
        return False, f"{run['job']}: final_metrics 字段缺失"
    expected = prompt + comp if run["harness"] == "codex" else prompt + comp + cache
    ok = expected == total
    return ok, f"{run['job']}: {'✓' if ok else '✗'} {prompt}+{comp}{'+cached' if run['harness']=='dsh' else ''}={expected} vs total={total}"


def compute() -> tuple[list[dict], list[str]]:
    runs = load_runs()
    errors: list[str] = []
    if len(runs) != 8:
        errors.append(f"预期 8 场 A 组运行（两批 × 两产品 × 两用例），实得 {len(runs)}")

    for run in runs:
        ok, msg = identity_check(run)
        if not ok:
            errors.append(msg)

    groups: dict[tuple[str, str], dict[str, dict]] = {}
    for run in runs:
        groups.setdefault((run["model"], run["task"]), {})[run["harness"]] = run

    rows: list[dict] = []
    for (model, task), pair in sorted(groups.items()):
        if set(pair) != {"codex", "dsh"}:
            errors.append(f"{model}/{task} 缺少 codex 或 dsh 现场")
            continue
        c_total, c_uncached = normalize(pair["codex"])
        d_total, d_uncached = normalize(pair["dsh"])
        rows.append(
            {
                "model": model,
                "task": task,
                "codex_total": c_total,
                "dsh_total": d_total,
                "ratio_total": round(c_total / d_total, 2),
                "ratio_uncached": round(c_uncached / d_uncached, 2),
                "codex_uncached": c_uncached,
                "dsh_uncached": d_uncached,
            }
        )
    return rows, errors


def render_table(rows: list[dict]) -> str:
    out = [
        "| 模型 | 用例 | Codex 统一输入 | DSH 统一输入 | 含缓存比 | 未缓存比 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for r in rows:
        out.append(
            f"| {r['model']} | {r['task']} | {r['codex_total']:,} | {r['dsh_total']:,} "
            f"| {r['ratio_total']:.2f}× | {r['ratio_uncached']:.2f}× |"
        )
    return "\n".join(out)


def selftest() -> int:
    rows, errors = compute()
    failed = 0
    for err in errors:
        failed += 1
        print(f"FAIL  identity/count: {err}")
    if not errors:
        print("PASS  identity: 8/8 场 final_metrics 恒等式成立")

    got = {(r["model"], r["task"]): (r["ratio_total"], r["ratio_uncached"]) for r in rows}
    for key, (exp_total, exp_uncached) in EXPECTED.items():
        actual = got.get(key)
        ok = actual is not None and abs(actual[0] - exp_total) <= 0.005 and abs(actual[1] - exp_uncached) <= 0.005
        failed += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'}  ratio/{key[0]}/{key[1]}  expected=({exp_total}, {exp_uncached}) got={actual}")

    total = len(EXPECTED) + (1 if not errors else len(errors))
    print(f"\nselftest: {total - failed}/{total} PASS")
    return 0 if failed == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="token 计价口径统一复算")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--selftest", action="store_true", help="断言报告值 + 恒等式")
    args = parser.parse_args()

    if args.selftest:
        return selftest()

    rows, errors = compute()
    if errors and not args.json:
        for err in errors:
            print(f"WARN  {err}", file=sys.stderr)
    if args.json:
        print(json.dumps({"rows": rows, "errors": errors}, ensure_ascii=False, indent=2))
    else:
        print("口径：Codex 统一输入 = n_input（cached 已含）；DSH 统一输入 = n_input + cached。")
        print("未缓存：Codex = n_input − cached；DSH = n_input。\n")
        print(render_table(rows))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
