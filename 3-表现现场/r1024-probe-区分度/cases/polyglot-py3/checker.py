#!/usr/bin/env python3
"""polyglot-py3 判分器：还原官方测试后逐题跑 unittest；三题全绿 reward=1，weighted=通过题数比例。"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BINARY = True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    run_dir = Path(args.run_dir).resolve()
    meta = json.loads((HERE / "truth.json").read_text(encoding="utf-8"))
    checks, ok = [], 0
    for ex in meta["exercises"]:
        exdir = run_dir / "inputs" / "exercises" / ex
        if not (exdir / f"{ex}.py").exists():
            checks.append({"id": ex, "pass": False, "note": "缺少 exercise 目录或骨架文件"})
            continue
        # 还原官方测试（防改测试作弊）
        shutil.copy2(HERE / "tests" / f"{ex}_test.py", exdir / f"{ex}_test.py")
        try:
            p = subprocess.run(
                [sys.executable, "-m", "unittest", "-q", f"{ex}_test.py"],
                cwd=str(exdir), capture_output=True, text=True, timeout=300,
                env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "HOME": str(run_dir)},
            )
            passed = p.returncode == 0
            note = (p.stderr or p.stdout).strip().splitlines()[-1][:160] if (p.stderr or p.stdout) else ""
        except subprocess.TimeoutExpired:
            passed, note = False, "timeout 300s"
        except Exception as exc:  # noqa: BLE001
            passed, note = False, f"error: {exc}"
        ok += int(passed)
        checks.append({"id": ex, "pass": passed, "note": note})

    acc = ok / len(meta["exercises"])
    reward = 1 if ok == len(meta["exercises"]) else 0
    out = {"case": "polyglot-py3", "reward": reward, "weighted": round(acc * 100, 2), "checks": checks}
    print(json.dumps(out, ensure_ascii=False) if args.json else json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
