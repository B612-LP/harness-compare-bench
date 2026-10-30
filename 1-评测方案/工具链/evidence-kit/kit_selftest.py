#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""evidence-kit 联合自测（L3 包C / C4）：子进程机械运行 C1/C2 的 --selftest，
汇总计数与退出码为一份收据（哈希/时刻脚本生成；--out 已存在即拒绝，C-1 同款纪律）。

用法：python3 kit_selftest.py [--out selftest-receipt-l3-20261029.json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = [("evidence_line", HERE / "evidence_line.py"),
         ("receipt_check", HERE / "receipt_check.py")]
DEFAULT_OUT = HERE / "selftest-receipt-l3-20261029.json"


def now_local() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def counts_from_stdout(text: str) -> dict | None:
    """selftest 输出 = 一个 JSON 文档 + 一行 PASS/FAIL 结论；取 JSON 文档部分解析 counts。"""
    cut = re.split(r"(?:EVIDENCE_LINE_SELFTEST|RECEIPT_CHECK_SELFTEST):", text, maxsplit=1)[0]
    try:
        doc = json.loads(cut)
    except Exception:
        return None
    c = doc.get("counts") if isinstance(doc, dict) else None
    return c if isinstance(c, dict) and {"total", "passed", "failed"} <= set(c) else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    a = ap.parse_args()
    out_path = Path(a.out)
    runs = {}
    for name, script in TOOLS:
        p = subprocess.run([sys.executable, "-B", str(script), "--selftest"],
                           capture_output=True, text=True, timeout=300)
        runs[name] = {"script": script.name,
                      "script_sha256_8": sha256_of(script)[:8],
                      "exit": p.returncode,
                      "counts": counts_from_stdout(p.stdout),
                      "verdict_line": [l for l in p.stdout.splitlines()
                                       if l.startswith(("EVIDENCE_LINE_SELFTEST",
                                                        "RECEIPT_CHECK_SELFTEST"))]}
    all_pass = all(r["exit"] == 0 and r["verdict_line"]
                   and r["verdict_line"][0].endswith("PASS")
                   and isinstance(r["counts"], dict)
                   and r["counts"].get("failed") == 0 for r in runs.values())
    receipt = {"kind": "self_test", "tool": "kit_selftest.py",
               "spec": "evidence-kit", "at": now_local(),
               "tools": runs,
               "counts": {"tools": len(runs),
                          "passed": sum(1 for r in runs.values()
                                        if r["exit"] == 0 and r["verdict_line"]
                                        and r["verdict_line"][0].endswith("PASS")),
                          "failed": sum(1 for r in runs.values() if not (
                              r["exit"] == 0 and r["verdict_line"]
                              and r["verdict_line"][0].endswith("PASS")))},
               "all_pass": all_pass}
    if out_path.exists():
        print(json.dumps({"refused": True, "target": str(out_path),
                          "reason": "目标已存在（C-1 同款纪律）"}, ensure_ascii=False))
        return 2
    out_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt["counts"], ensure_ascii=False))
    print("KIT_SELFTEST:", "PASS" if all_pass else "FAIL", "->", out_path.name)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
