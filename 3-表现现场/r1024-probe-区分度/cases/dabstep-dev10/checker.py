#!/usr/bin/env python3
"""dabstep-dev10 判分器：官方 DABstep scorer 逐题二值，通过率 ≥ 0.8 记 headline=1。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from scorer import question_scorer  # noqa: E402  官方 scorer（CC-BY-4.0）

BINARY = True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    run_dir = Path(args.run_dir).resolve()
    truth = json.loads((HERE / "truth.json").read_text(encoding="utf-8"))
    gold = truth["answers"]
    threshold = truth["threshold"]

    checks, got = [], {}
    path = run_dir / "answers.jsonl"
    if not path.exists():
        checks.append({"id": "answers_jsonl", "pass": False, "note": "answers.jsonl 缺失"})
        acc = 0.0
    else:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict) and "task_id" in obj:
                got[str(obj["task_id"])] = str(obj.get("answer", ""))
        checks.append({"id": "answers_jsonl", "pass": len(got) == len(gold),
                       "note": f"{len(got)}/{len(gold)} 行可解析"})
        ok = 0
        for tid, want in gold.items():
            pred = got.get(tid, "")
            hit = bool(pred) and question_scorer(pred, want)
            ok += int(hit)
            checks.append({"id": f"q{tid}", "pass": hit, "got": pred[:80], "want": want[:80]})
        acc = ok / len(gold)

    reward = 1 if acc >= threshold else 0
    out = {"case": "dabstep-dev10", "reward": reward, "weighted": round(acc * 100, 2),
           "accuracy": round(acc, 4), "threshold": threshold, "checks": checks}
    if args.json:
        print(json.dumps(out, ensure_ascii=False))
    else:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
