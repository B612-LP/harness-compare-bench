#!/usr/bin/env python3
"""机械汇总 tb-cargo-plan 11 轮逐检查项失败谱（派生分析-tb失败项谱-20261109 的数据基线）。

用法: python3 collect-tb-failure-spectrum.py <公开仓根> <可选:私档 launch-r1109 路径>
输出: stdout JSON 谱表（每轮 reward/weighted/FAIL 项 id+note），供人工比对 README.md 谱表。
只读；不判卷、不改判卷、不重放。
"""
import json
import sys
from pathlib import Path


def load_checks(p):
    d = json.loads(Path(p).read_text(encoding="utf-8"))
    if isinstance(d, dict) and isinstance(d.get("result"), dict):
        d = d["result"]
    return {
        "reward": d.get("reward"),
        "weighted": d.get("weighted"),
        "passed": d.get("passed"),
        "total": d.get("total"),
        "fails": [
            {"id": c.get("id"), "note": (c.get("note") or "")[:60]}
            for c in (d.get("checks") or [])
            if not c.get("pass")
        ],
    }


def main():
    repo = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    priv = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    slots = []
    a1 = repo / "3-表现现场" / "r1030-formal-a1" / "runs"
    mech = repo / "3-表现现场" / "r1109-mech-n3" / "runs"
    for prod in ("dsh", "codex"):
        p = a1 / f"{prod}__tb-cargo-plan" / "checker.stdout.json"
        if p.exists():
            slots.append({"slot": f"a1-{prod}", **load_checks(p)})
    for prod in ("dsh", "codex"):
        for rep in (1, 2, 3):
            p = mech / f"{prod}__tb-cargo-plan__r{rep}" / "checker.stdout.json"
            if p.exists():
                slots.append({"slot": f"r1109-cli-{prod}-r{rep}", **load_checks(p)})
    if priv:
        wb = priv / "bw-retest" / "workbuddy" / "evidence-tools" / "grading"
        for rep in (1, 2, 3):
            p = wb / f"tb-cargo-plan__r{rep}" / "execution.json"
            if p.exists():
                slots.append({"slot": f"r1109-wb-r{rep}", **load_checks(p)})
    print(json.dumps({"slots": slots, "count": len(slots)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
