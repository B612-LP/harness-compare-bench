#!/usr/bin/env python3
"""lcb-v6-hard4 判分器：逐题跑 stdin/stdout 测试（公开+私有）；通过 ≥2 题记 reward=1。"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BINARY = True
TEST_TIMEOUT = 10


def norm(s: str) -> str:
    return "\n".join(line.rstrip() for line in s.strip().splitlines())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    run_dir = Path(args.run_dir).resolve()
    truth = json.loads((HERE / "truth.json").read_text(encoding="utf-8"))["problems"]

    checks, passed = [], 0
    for pid, spec in truth.items():
        path = run_dir / "solutions" / f"{pid}.py"
        if not path.exists():
            checks.append({"id": pid, "pass": False, "note": f"缺少 solutions/{pid}.py"})
            continue
        ok, first_fail = 0, ""
        for i, case in enumerate(spec["tests"]):
            try:
                p = subprocess.run([sys.executable, str(path)], input=case["input"],
                                   capture_output=True, text=True, timeout=TEST_TIMEOUT)
                hit = p.returncode == 0 and norm(p.stdout) == norm(case["output"])
            except subprocess.TimeoutExpired:
                hit = False
                first_fail = f"#{i} timeout"
            except Exception as exc:  # noqa: BLE001
                hit = False
                first_fail = f"#{i} {exc}"[:80]
            if not hit and not first_fail:
                first_fail = f"#{i} wrong"
            ok += int(hit)
        allpass = ok == len(spec["tests"])
        passed += int(allpass)
        checks.append({"id": pid, "pass": allpass, "note": f"{ok}/{len(spec['tests'])}", "first_fail": first_fail})
    reward = 1 if passed >= 2 else 0
    out = {"case": "lcb-v6-hard4", "reward": reward, "weighted": round(passed / len(truth) * 100, 2),
           "problems_passed": passed, "checks": checks}
    print(json.dumps(out, ensure_ascii=False) if args.json else json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
