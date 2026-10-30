#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r1028-repeats 汇总：把「首跑（r1025 / r1027 的 n=1 证据）+ r1028 的 r2、r3」合成 n=3 通过率。

用法：
    python3 tools/aggregate.py            # 输出 results.json + 终端表格
    python3 tools/aggregate.py --json     # 只打印 results.json

输出（results.json）：
    cells: 每款 × 贴线题（bird / dabstep / tb）
        samples[]     : 每场的 reward / weighted / steps / failed / 证据目录
        pass_rate     : 达标率（0–1）
        weighted_mean : 半程分均值
        failed_agree  : 各场失败项集合是否完全一致（None=只有 1 场）
        steps_var     : 步数的 min–max（过程成本噪声）
    d3: 每款 D3 稳健分 = 20 × mean(各贴线题 pass_rate)
    note: 首跑来源（canonical n=1 证据）
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
BATCH = TOOLS.parent
REPO = BATCH.parents[1]
RUNS = BATCH / "runs"
CASES = ["bird-ca-schools-15", "dabstep-payments-10", "tb-cargo-plan"]
CANONICAL = REPO / "5-评测报告" / "复算" / "v2-data.json"

# 首跑证据（n=1）按 v2-data.json 的 source 字段定位，读其中 reward/weighted/steps/failed
def load_canonical() -> dict:
    d = json.loads(CANONICAL.read_text(encoding="utf-8"))
    return d


def sample_from_meta(meta: dict, dirname: str) -> dict:
    return {"run": dirname,
            "reward": meta.get("reward"),
            "weighted": meta.get("weighted"),
            "steps": meta.get("steps"),
            "failed": sorted(meta.get("failed") or []),
            "duration_s": meta.get("duration_s"),
            "integrity_violations": (meta.get("integrity") or {}).get("violations")
            if isinstance(meta.get("integrity"), dict) else meta.get("integrity")}


def canonical_sample(canon: dict, product: str, case: str) -> dict | None:
    prods = canon.get("products", {})
    key = {"codex": "codex", "dsh": "dsh", "workbuddy": "workbuddy", "doubao": "doubao"}[product]
    cell = prods.get(key, {}).get("cells", {}).get(case)
    if not cell:
        return None
    return {"run": "n=1（%s）" % cell.get("source", "canonical"),
            "reward": cell.get("reward"),
            "weighted": cell.get("weighted"),
            "steps": cell.get("steps"),
            "failed": sorted(cell.get("failed") or []),
            "duration_s": cell.get("duration_s"),
            "integrity_violations": 0}


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    canon = load_canonical()

    results = {"generated_by": "3-表现现场/r1028-repeats/tools/aggregate.py",
               "cases": CASES, "products": {}, "d3": {}}
    for product in ("codex", "dsh", "workbuddy", "doubao"):
        pdata = {"cells": {}}
        rates = []
        for case in CASES:
            samples = []
            first = canonical_sample(canon, product, case)
            if first:
                samples.append(first)
            for meta_path in sorted(RUNS.glob("%s__%s__r*/meta.json" % (product, case))):
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                samples.append(sample_from_meta(meta, meta_path.parent.name))
            if not samples:
                continue
            rewards = [s["reward"] for s in samples]
            weighted = [s["weighted"] for s in samples if s["weighted"] is not None]
            steps = [s["steps"] for s in samples if s["steps"] is not None]
            failsets = [frozenset(s["failed"]) for s in samples]
            pdata["cells"][case] = {
                "n": len(samples),
                "samples": samples,
                "pass_rate": round(sum(1 for r in rewards if r == 1) / len(rewards), 3),
                "rewards": rewards,
                "weighted_mean": round(statistics.mean(weighted), 2) if weighted else None,
                "failed_agree": (len(set(failsets)) == 1) if len(failsets) > 1 else None,
                "steps_range": [min(steps), max(steps)] if steps else None,
            }
            rates.append(pdata["cells"][case]["pass_rate"])
        if rates:
            pdata["d3"] = round(20 * statistics.mean(rates), 2)
            pdata["d3_basis"] = "n=%s" % ",".join(str(pdata["cells"][c]["n"]) for c in pdata["cells"])
        results["products"][product] = pdata

    out = BATCH / "results.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if a.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    print("| 产品 | 用例 | n | 达标率 | weighted 均值 | 各场达标 | 失败项一致 | 步数范围 |")
    print("|---|---|---|---|---|---|---|---|")
    for product, pdata in results["products"].items():
        for case, c in pdata["cells"].items():
            print("| %s | %s | %d | %.2f | %s | %s | %s | %s |" % (
                product, case, c["n"], c["pass_rate"], c["weighted_mean"],
                "/".join(str(r) for r in c["rewards"]),
                {True: "是", False: "否", None: "—"}[c["failed_agree"]],
                c["steps_range"]))
    print("\nD3 稳健分（20 × 平均达标率）：" + "；".join(
        "%s = %s（%s）" % (p, pdata.get("d3"), pdata.get("d3_basis"))
        for p, pdata in results["products"].items() if pdata.get("d3") is not None))
    print("\n-> %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv[1:]))
