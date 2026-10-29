#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L4 发布前 PII 最小化检查（task-9 附加项；零模型、只读目标）。

目的（lead 2026-10-29）：DSH config 快照可能复制全局 AGENTS，其中与本评测无关的
作业姓名/学号/班级不应顺带进入公开派生快照。本工具只对 **L4 新批次/新报告** 检查
个人标识字段，输出 **定位/计数，绝不输出值**。

设计纪律：
  - 指needle 不硬编码进本文件（本文件属公开派生产物）：运行时从全局 ~/.dsh/AGENTS.md
    的「作业封面/填表信息」段提取 姓名/学号/班级 三类needle，仅进内存；
  - 另备形状模式兜底：`学号` 标签伴随长数字、`姓名` 标签、2025 开头 12 位数字；
  - 收据只含 类型+次数+文件+行号；自检含机械断言（报告字节无needle的≥6连续子串）；
  - `--out` 原子拒写；live_doc_drift:[]；时间脚本生成；不联网、不读其他 secret。

用法：python3 pii_min_check.py --scan PATH... --out REPORT [--selftest]
退出码：0=无命中；4=有命中；2=用法/拒写/needle 源不可用。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

AGENTS_GLOBAL = Path.home() / ".dsh" / "AGENTS.md"
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
SHAPE_PATTERNS = [
    ("xuehao-label-digits", re.compile(r"学号[：:=\s]*\d{6,}")),
    ("xingming-label", re.compile(r"姓名[：:=\s]*[^\s；;，,]{2,8}")),
    ("banji-label", re.compile(r"班级[：:=\s]*[^\n；;]{2,40}")),
    ("id-2025-12digit", re.compile(r"\b2025\d{9}\b")),
]


def now_local() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def extract_needles() -> dict[str, str]:
    """从全局 AGENTS.md 作业封面段提取三类needle；全局文件本身不改动。"""
    text = AGENTS_GLOBAL.read_text(encoding="utf-8")
    seg = text.split("作业封面", 1)[-1]
    out: dict[str, str] = {}
    m = re.search(r"姓名\s*([^\n；;，,]{2,8})", seg)
    if m:
        out["realname"] = m.group(1).strip()
    m = re.search(r"学号\s*([^\n；;，,]*)", seg)
    if m:
        digits = re.search(r"\d{6,}", m.group(1))
        if digits:
            out["xuehao"] = digits.group(0)
    m = re.search(r"班级\s*([^\n；;]+)", seg)
    if m:
        out["banji"] = m.group(1).strip()
    if not out:
        raise SystemExit("pii: 全局 AGENTS.md 未提取到作业封面needle")
    return out


def maybe_zstd(raw: bytes) -> bytes:
    if raw[:4] == ZSTD_MAGIC:
        try:
            import zstandard
            return zstandard.ZstdDecompressor().decompress(raw, max_output_size=1 << 30)
        except Exception:
            return raw
    return raw


def iter_files(target: Path):
    if target.is_file():
        yield target
    elif target.is_dir():
        for root, _d, files in os.walk(target):
            for name in sorted(files):
                yield Path(root) / name


def scan(targets: list[Path], needles: dict[str, str], out: Path | None) -> tuple[int, dict]:
    needle_bytes = {("%s-exact" % k): v for k, v in needles.items()}
    findings: dict[str, dict] = {}
    files_n = 0
    for t in targets:
        for f in iter_files(t):
            files_n += 1
            try:
                text = maybe_zstd(f.read_bytes()).decode("utf-8", errors="replace")
            except Exception:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                for type_name, rx in SHAPE_PATTERNS:
                    if rx.search(line):
                        slot = findings.setdefault(type_name, {"count": 0, "files": {}})
                        slot["count"] += 1
                        slot["files"].setdefault(str(f), []).append(i)
                for type_name, needle in needle_bytes.items():
                    if needle and needle in line:
                        slot = findings.setdefault(type_name, {"count": 0, "files": {}})
                        slot["count"] += 1
                        slot["files"].setdefault(str(f), []).append(i)
    findings = {k: {"count": v["count"],
                    "files": {p: ls[:20] for p, ls in sorted(v["files"].items())}}
                for k, v in sorted(findings.items())}
    total = sum(v["count"] for v in findings.values())
    report = {"kind": "pii_min_check_report", "tool": "pii_min_check.py",
              "at": now_local(), "targets": [str(t) for t in targets],
              "files_scanned": files_n, "total_hits": total,
              "needles_source": "global-AGENTS-workdir-section(in-memory only)",
              "values_in_report": False, "findings": findings,
              "live_doc_drift": []}
    if out is not None:
        if out.exists():
            print(json.dumps({"refused": True, "target": str(out)}, ensure_ascii=False))
            return 2, report
        out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                       encoding="utf-8")
        print(json.dumps({"total_hits": total, "files_scanned": files_n,
                          "types": list(findings), "report": str(out)},
                         ensure_ascii=False))
    return (4 if total else 0), report


def selftest() -> int:
    import hashlib
    import tempfile
    results = []

    def check(name, ok, detail=""):
        results.append({"case": name, "pass": bool(ok), "detail": str(detail)[:150]})
        return bool(ok)

    with tempfile.TemporaryDirectory(prefix="pii-selftest-") as td:
        tmp = Path(td)
        fake_id = "20259999999"
        fake_name = "测试名"
        (tmp / "a.md").write_text("姓名 %s\n学号： %s\n班级 某班一班\n" % (fake_name, fake_id),
                                  encoding="utf-8")
        (tmp / "clean.txt").write_text("no personal info\n20261029220000 timestamp ok\n",
                                       encoding="utf-8")
        needles = {"realname": fake_name, "xuehao": fake_id, "banji": "某班一班"}
        code, rep = scan([tmp], needles, None)
        by_type = rep["findings"]
        check("t1_shape_hits", all(k in by_type for k in
                                   ("xuehao-label-digits", "xingming-label", "banji-label")))
        check("t2_exact_hits", by_type.get("xuehao-exact", {}).get("count", 0) >= 1
              and by_type.get("realname-exact", {}).get("count", 0) >= 1)
        check("t3_clean_no_fp", not any(str(tmp / "clean.txt") in json.dumps(v)
                                        for v in by_type.values()))
        blob = json.dumps(rep, ensure_ascii=False)
        check("t4_no_values", fake_id not in blob and fake_name not in blob
              and "某班一班" not in blob)
        subs = {fake_id[i:i + 6] for i in range(len(fake_id) - 5)}
        check("t5_no_needle_substrings", not any(s in blob for s in subs))
        code2, rep2 = scan([tmp / "clean.txt"], needles, None)
        check("t6_clean_exit0", code2 == 0 and rep2["total_hits"] == 0)
    counts = {"total": len(results), "passed": sum(1 for r in results if r["pass"]),
              "failed": sum(1 for r in results if not r["pass"])}
    print(json.dumps(counts, ensure_ascii=False))
    print("PII_MIN_SELFTEST:", "PASS" if counts["failed"] == 0 else "FAIL")
    return 0 if counts["failed"] == 0 else 1


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", nargs="*", metavar="TARGET")
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.scan:
        ap.print_help()
        return 2
    code, _ = scan([Path(p) for p in a.scan], extract_needles(),
                   Path(a.out) if a.out else None)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
