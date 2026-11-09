#!/usr/bin/env python3
"""豆包 lcb 失分谱派生分析（环22，零发射只读）。

只读私档 doubao-n3-20261101/evidence-tools/grading/lcb-recent-hard-4__r*/checker.stdout.txt
（判分回执：检查项 id/note/通过计数），输出逐槽逐检查项谱 JSON。
用法: python3 collect-doubao-lcb-failure-spectrum.py <输出.json> <私档批根>
"""
import json
import sys
from pathlib import Path

out_path = Path(sys.argv[1])
batch_root = Path(sys.argv[2])
grading = batch_root / "evidence-tools" / "grading"
CASE = "lcb-recent-hard-4"
slots = ["r1", "r2", "r3"]

slots_out = []
for rep in slots:
    stdout_path = grading / f"{CASE}__{rep}" / "checker.stdout.txt"
    text = stdout_path.read_text(encoding="utf-8")
    payload = json.loads(text[text.index("{"):])
    checks = [
        {
            "id": c["id"],
            "pass": c["pass"],
            "note": c.get("note", ""),
            "passed_tests": c.get("passed_tests"),
            "total_tests": c.get("total_tests"),
            "first_fail_index": c.get("first_fail_index"),
            "fail_kind": c.get("fail_kind", ""),
        }
        for c in payload.get("checks", [])
    ]
    slots_out.append(
        {
            "slot": f"{CASE}__{rep}",
            "reward": payload.get("reward"),
            "weighted": payload.get("weighted"),
            "passed_problems": payload.get("passed_problems"),
            "total_problems": payload.get("total_problems"),
            "checks": checks,
        }
    )

doc = {
    "batch": "doubao-n3-20261101",
    "case": CASE,
    "slots": slots_out,
    "note": "只读判分回执 id/note/计数层；不读取解法代码与会话内容。",
}
out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("slots=", len(slots_out), "sha256=", __import__("hashlib").sha256(out_path.read_bytes()).hexdigest())
