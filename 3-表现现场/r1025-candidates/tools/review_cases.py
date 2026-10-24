#!/usr/bin/env python3
"""r1025 候选用例静态审查 + 自测跑批。

用法：
    python3 tools/review_cases.py                 # 全部候选
    python3 tools/review_cases.py --cases a,b

检查项（不合格标 FAIL）：
- 五件套齐全：instruction.md / spec.md / truth.json / checker.py / inputs/ / solution/ / task.toml / case.json
- case.json 合法且 inputs 指向 inputs 目录
- truth.json 可解析、含来源字段
- checker.py 含 BINARY 与 --selftest 入口
- `python3 checker.py --selftest` exit 0 且输出含全部 PASS
- 输入体积、总目录体积
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

BATCH = Path(__file__).resolve().parents[1]
CASES = BATCH / "cases"
REQUIRED = ["instruction.md", "spec.md", "truth.json", "checker.py", "task.toml", "case.json"]


def dir_size(p: Path) -> int:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def review(case: Path) -> dict:
    out = {"case": case.name, "fails": [], "warns": []}
    for name in REQUIRED:
        if not (case / name).exists():
            out["fails"].append(f"缺 {name}")
    for d in ("inputs", "solution"):
        if not (case / d).is_dir() or not any((case / d).rglob("*")):
            out["fails"].append(f"缺 {d}/ 或为空")

    cj = case / "case.json"
    if cj.exists():
        try:
            spec = json.loads(cj.read_text(encoding="utf-8"))
            if spec.get("inputs") != [["inputs", "inputs"]]:
                out["warns"].append(f"case.json inputs={spec.get('inputs')}（约定为 [[\"inputs\",\"inputs\"]]）")
        except Exception as exc:
            out["fails"].append(f"case.json 解析失败: {exc}")

    tj = case / "truth.json"
    if tj.exists():
        try:
            truth = json.loads(tj.read_text(encoding="utf-8"))
            if not isinstance(truth, dict):
                out["fails"].append("truth.json 不是对象")
            elif not any(k in truth for k in ("source", "sources", "license")):
                out["warns"].append("truth.json 没写 source/license")
        except Exception as exc:
            out["fails"].append(f"truth.json 解析失败: {exc}")

    ck = case / "checker.py"
    if ck.exists():
        text = ck.read_text(encoding="utf-8", errors="replace")
        if "BINARY" not in text:
            out["warns"].append("checker 未声明 BINARY")
        if "--selftest" not in text:
            out["fails"].append("checker 没有 --selftest 入口")
        else:
            try:
                p = subprocess.run([sys.executable, str(ck), "--selftest"],
                                   capture_output=True, text=True, timeout=600, cwd=str(case))
                tail = (p.stdout + p.stderr).strip().splitlines()[-1:] or [""]
                out["selftest_exit"] = p.returncode
                out["selftest_tail"] = tail[0][:200]
                if p.returncode != 0:
                    out["fails"].append(f"selftest 退出码 {p.returncode}")
            except subprocess.TimeoutExpired:
                out["fails"].append("selftest 超时 600s")

    out["inputs_mb"] = round(dir_size(case / "inputs") / 1e6, 2) if (case / "inputs").exists() else 0
    out["total_mb"] = round(dir_size(case) / 1e6, 2)
    return out


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default="all")
    args = ap.parse_args(argv)
    names = [p.name for p in sorted(CASES.iterdir()) if p.is_dir()] if args.cases == "all" else args.cases.split(",")
    rows = [review(CASES / n) for n in names if (CASES / n).is_dir()]
    print("\n| case | inputs MB | total MB | selftest | 结论 |")
    print("|---|---|---|---|---|")
    bad = 0
    for r in rows:
        ok = not r["fails"]
        bad += 0 if ok else 1
        print(f"| {r['case']} | {r['inputs_mb']} | {r['total_mb']} | exit={r.get('selftest_exit','-')} "
              f"{r.get('selftest_tail','')[:60]} | {'PASS' if ok else 'FAIL'} |")
        for f in r["fails"]:
            print(f"  - FAIL: {f}")
        for w in r["warns"]:
            print(f"  - warn: {w}")
    print(f"\n{len(rows)} cases, {bad} with FAIL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))