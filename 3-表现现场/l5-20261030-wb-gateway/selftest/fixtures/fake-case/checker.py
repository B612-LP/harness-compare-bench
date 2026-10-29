#!/usr/bin/env python3
"""dry-run 夹具 checker：错答时 exit 1 但仍输出合法评分 JSON（对齐 lead 语义：
checker exit1 ≠ 基础设施错误，是正常低分）。仅验证 runner 调用管线。"""
import json, sys
from pathlib import Path
ws = Path(sys.argv[1])
ok_file = ws / "ok.txt"
passed = ok_file.is_file() and ok_file.read_text(encoding="utf-8").strip() == "OK"
print(json.dumps({"reward": 1 if passed else 0,
                  "weighted": 100.0 if passed else 0.0,
                  "checks": [{"id": "ok-file", "pass": passed}],
                  "n_checks": 1}))
sys.exit(0 if passed else 1)
