#!/usr/bin/env python3
"""ok 干跑夹具：机械验证 runner→gate 管线（27 分母，计数对齐全，不触真 checker）。"""
import json, sys
from pathlib import Path
ws = Path(sys.argv[1])
ok_file = ws / "inputs" / "ok.txt"
passed = ok_file.is_file() and ok_file.read_text(encoding="utf-8").strip() == "OK"
n = 27
correct = n if passed else 0
print(json.dumps({"reward": correct, "weighted": round(correct / n * 100, 8),
                  "correct": correct, "n_tasks": n,
                  "checks": [{"id": f"q{i}", "pass": passed} for i in range(1, n + 1)],
                  "guards_used": [], "n_checks": n,
                  "checker_sha256": "PLACEHOLDER", "exit_code": 0 if passed else 1}))
sys.exit(0 if passed else 1)
