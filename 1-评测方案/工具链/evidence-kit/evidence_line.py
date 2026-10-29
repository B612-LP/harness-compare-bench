#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""evidence-kit 证据行生成器（L3 包C / C1）。

把文件事实转成报告标准证据行，杜绝叙述文本手打哈希/时刻：

    <相对路径> · <sha256 前 8 位> · <字节数>B · <生成时刻 ISO8601+tz>

- 相对路径相对 --root（默认仓库根）；仓库外文件保留绝对路径。
- 时刻由脚本生成（now_local），禁止手打。
- 多文件按命令行顺序逐行输出；任一文件不可读即整批失败（exit 2，不产半截行）。
- --json 输出结构化数组（字段同上）；--selftest 自检（计数实报）。

用法：
    python3 evidence_line.py <path> [<path> ...] [--root <repo-root>] [--json]
    python3 evidence_line.py --selftest
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ISO_TZ_TOKEN = (r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?"
                r"(?:Z|[+-]\d{2}:?\d{2})")


def now_local() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def display_path(p: Path, root: Path) -> str:
    try:
        return str(p.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(p.resolve())


def evidence_line(p: Path, root: Path, at: str) -> dict:
    data = p.read_bytes()
    digest = sha256_of(p)
    return {"path": display_path(p, root), "sha256_8": digest[:8],
            "sha256": digest, "bytes": len(data), "at": at,
            "line": "%s · %s · %dB · %s" % (display_path(p, root), digest[:8],
                                             len(data), at)}


def gather(paths: list[str], root: Path, at: str) -> list[dict]:
    out = []
    for raw in paths:
        p = Path(raw)
        if not p.is_file():
            raise FileNotFoundError(raw)
        out.append(evidence_line(p, root, at))
    return out


def selftest() -> int:
    results = []

    def check(name, ok, detail=""):
        results.append({"case": name, "pass": bool(ok), "detail": detail})
        return bool(ok)

    with tempfile.TemporaryDirectory(prefix="evidence-kit-") as td:
        tmp = Path(td)
        f1 = tmp / "a.txt"
        f1.write_bytes(b"hello evidence\n")
        f2 = tmp / "sub" / "b.bin"
        f2.parent.mkdir()
        f2.write_bytes(bytes(range(256)) * 3)
        fixed_at = "2026-10-29T18:00:00+08:00"

        e1 = evidence_line(f1, tmp, fixed_at)
        import hashlib as _h
        want = _h.sha256(b"hello evidence\n").hexdigest()
        check("sha256_8_prefix", e1["sha256_8"] == want[:8], e1["sha256_8"])
        check("bytes_exact", e1["bytes"] == 15, str(e1["bytes"]))
        check("iso_tz_format", re.fullmatch(ISO_TZ_TOKEN, e1["at"]) is not None, e1["at"])
        check("relative_path", e1["path"] == "a.txt", e1["path"])
        check("line_format", e1["line"].count(" · ") == 3, e1["line"])

        e2 = evidence_line(f2, tmp, fixed_at)
        check("nested_relative_path", e2["path"] == "sub/b.bin", e2["path"])
        check("nested_bytes", e2["bytes"] == 768, str(e2["bytes"]))

        outside = evidence_line(Path(__file__), REPO, fixed_at)
        check("outside_root_abs_or_rel", outside["path"] in
              (str(Path(__file__).resolve()),
               str(Path(__file__).resolve().relative_to(REPO.resolve()))),
              outside["path"])

        many = gather([str(f2), str(f1)], tmp, fixed_at)
        check("multi_file_order_kept", [e["path"] for e in many] == ["sub/b.bin", "a.txt"],
              str([e["path"] for e in many]))

        try:
            gather([str(tmp / "missing.txt")], tmp, fixed_at)
            check("missing_file_fails", False, "no exception")
        except FileNotFoundError:
            check("missing_file_fails", True, "FileNotFoundError")

        # 时刻非手打：两次调用产生脚本时刻（单调不回退）
        t1, t2 = now_local(), now_local()
        check("now_monotonic", parse_iso(t2) >= parse_iso(t1), "%s -> %s" % (t1, t2))

    counts = {"total": len(results), "passed": sum(1 for r in results if r["pass"]),
              "failed": sum(1 for r in results if not r["pass"])}
    print(json.dumps({"kind": "self_test", "tool": "evidence_line.py",
                      "at": now_local(), "counts": counts, "cases": results},
                     ensure_ascii=False, indent=2))
    print("EVIDENCE_LINE_SELFTEST:", "PASS" if counts["failed"] == 0 else "FAIL")
    return 0 if counts["failed"] == 0 else 1


def parse_iso(v: str) -> dt.datetime:
    return dt.datetime.fromisoformat(v)


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", metavar="PATH")
    ap.add_argument("--root", default=str(REPO))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.paths:
        ap.print_help()
        return 2
    at = now_local()  # 同批共用一个脚本时刻
    try:
        rows = gather(a.paths, Path(a.root), at)
    except FileNotFoundError as exc:
        print("整批失败（不产半截行）：文件不可读 %s" % exc, file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps({"kind": "evidence_lines", "at": at, "root": a.root,
                          "items": rows}, ensure_ascii=False, indent=2))
    else:
        for r in rows:
            print(r["line"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
