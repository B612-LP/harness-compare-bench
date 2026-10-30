#!/usr/bin/env python3
"""lcb-hard3 判分器：逐题 import 解法、跑 15 组官方测试；通过题数 ≥2 记 reward=1。"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BINARY = True


def eq(a, b) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, float) or isinstance(b, float):
        return abs(float(a) - float(b)) <= 1e-6
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(eq(x, y) for x, y in zip(a, b))
    return a == b


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    run_dir = Path(args.run_dir).resolve()
    truth = json.loads((HERE / "truth.json").read_text(encoding="utf-8"))["problems"]

    checks, passed_problems = [], 0
    for pid, spec in truth.items():
        sol_path = run_dir / "solutions" / f"{pid}.py"
        if not sol_path.exists():
            checks.append({"id": pid, "pass": False, "note": "缺少 solutions/%s.py" % pid})
            continue
        spec_obj = importlib.util.spec_from_file_location(f"sol_{pid}", sol_path)
        mod = importlib.util.module_from_spec(spec_obj)
        try:
            spec_obj.loader.exec_module(mod)
            sol = mod.Solution()
            fn = getattr(sol, spec["fn_name"])
        except Exception as exc:  # noqa: BLE001
            checks.append({"id": pid, "pass": False, "note": f"import/入口失败: {exc}"})
            continue
        ok = 0
        notes = []
        for i, case in enumerate(spec["tests"]):
            try:
                got = fn(*case["input"])
                hit = eq(got, case["output"])
            except Exception as exc:  # noqa: BLE001
                hit = False
                notes.append(f"#{i} exc {exc}"[:120])
            ok += int(hit)
        allpass = ok == len(spec["tests"])
        passed_problems += int(allpass)
        checks.append({"id": pid, "pass": allpass, "note": f"{ok}/{len(spec['tests'])}", "detail": notes[:3]})
    reward = 1 if passed_problems >= 2 else 0
    out = {"case": "lcb-hard3", "reward": reward, "weighted": round(passed_problems / len(truth) * 100, 2),
           "problems_passed": passed_problems, "checks": checks}
    print(json.dumps(out, ensure_ascii=False) if args.json else json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
