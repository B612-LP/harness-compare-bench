#!/usr/bin/env python3
"""token-cause 交付校验：读本目录 per_run.json / decomposition.md，核对输出契约。

契约（对齐任务题面）：
  per_run.json.a_group_runs：44 条；每条必含
    run, harness, case, n_calls, call1_prefix_tokens, sum_input_miss,
    sum_input_hit, sum_output, sum_reasoning, total_tokens；
    整数字段为 int、run 全仓唯一；恒等式 total = miss+hit+out 逐条成立。
  decomposition.md：存在且非空。
  ablation_cells：10 格（2 case × 5 arm）逐格在册；缺格必须出现在 ablation_missing。

用法：python3 validate.py    # 全部通过打印 OK，否则打印 FAIL 并以非零码退出
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REQUIRED = ["run", "harness", "case", "n_calls", "call1_prefix_tokens",
            "sum_input_miss", "sum_input_hit", "sum_output", "sum_reasoning",
            "total_tokens"]
INT_FIELDS = [k for k in REQUIRED if k not in ("run", "harness", "case", "sum_reasoning")]
ARMS = {"codex-base", "codex-skill", "codex-gpt", "dsh-base", "dsh-skill"}
CASES = {"dabstep-payments-10", "tb-cargo-plan"}


def main() -> int:
    bad = []
    pr = json.loads((HERE / "per_run.json").read_text(encoding="utf-8"))
    runs = pr["a_group_runs"]
    if len(runs) != 44:
        bad.append(f"a_group_runs 行数 {len(runs)} != 44")
    seen = set()
    for r in runs:
        tag = r.get("run", "?")
        for k in REQUIRED:
            if k not in r:
                bad.append(f"{tag}: 缺字段 {k}")
        for k in INT_FIELDS:
            if k in r and not isinstance(r[k], int):
                bad.append(f"{tag}: {k} 非 int（{r[k]!r}）")
        if r.get("harness") not in ("codex", "dsh"):
            bad.append(f"{tag}: harness 非法 {r.get('harness')!r}")
        if r["run"] in seen:
            bad.append(f"{tag}: run 重复")
        seen.add(r["run"])
        if {"sum_input_miss", "sum_input_hit", "sum_output", "total_tokens"} <= set(r):
            if r["total_tokens"] != r["sum_input_miss"] + r["sum_input_hit"] + r["sum_output"]:
                bad.append(f"{tag}: total != miss+hit+out")
        if r.get("harness") == "codex" and r.get("cross_check_turn_completed") not in (
                "match", "absent") and not str(r.get("cross_check_turn_completed", "")).startswith("MISMATCH"):
            bad.append(f"{tag}: cross_check 值异常 {r.get('cross_check_turn_completed')!r}")
    cells = pr["ablation_cells"]
    want = {f"{c}__{a}" for c in CASES for a in ARMS}
    got = {c["cell"] for c in cells}
    if got != want:
        bad.append(f"ablation 格集合不符：缺 {sorted(want-got)} 多 {sorted(got-want)}")
    for c in cells:
        if "call1_prefix_tokens" not in c and not any(c["cell"] in m for m in pr["ablation_missing"]):
            bad.append(f"{c['cell']}: 未解析但未列入 ablation_missing")
    md = (HERE / "decomposition.md")
    if not md.is_file() or md.stat().st_size == 0:
        bad.append("decomposition.md 缺失或为空")
    if bad:
        print("FAIL")
        for b in bad:
            print(" -", b)
        return 1
    print(f"OK: a_group_runs=44 唯一且字段/类型/恒等式全过；ablation 格 {len(cells)}/10 在册；"
          f"待补算 {len(pr['ablation_missing'])} 格均已披露；decomposition.md 非空。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
