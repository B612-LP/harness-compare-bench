#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""manifest-receipt 生成器（L6-C，2026-10-30）：write-once 清单收据，自动 self-excluded。

用法：
    python3 manifest_receipt.py --out <receipt.json> [--root <repo>] FILE [FILE...]

行为：
  - files_sha256 仅含列出文件（相对 --root 的规范 POSIX 相对路径；不在 root 之下即拒）；
    收据自身路径不入映射，以 self_excluded 字段显式记录
    （AUD-L5-O1：自引哈希逻辑上不可自证，收据不得列入自身）。
  - write-once：--out 已存在（含悬空符号链接）即拒；输入含收据自身路径即拒。
  - 输出带 live_doc_drift: []；不联网、不装包、不写输入文件。
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def build(out_path: Path, root: Path, inputs) -> dict:
    out_resolved = Path(out_path).resolve()
    files = {}
    for raw in inputs:
        p = Path(raw)
        if not p.is_absolute():
            p = root / p
        rp = p.resolve()
        if not rp.is_file():
            raise SystemExit("FAIL-CLOSED: 输入不是常规文件: %s" % raw)
        if rp == out_resolved:
            raise SystemExit("FAIL-CLOSED: 收据不得列入自身（AUD-L5-O1）: %s" % raw)
        try:
            rel = rp.relative_to(root.resolve())
        except ValueError:
            raise SystemExit("FAIL-CLOSED: 输入不在 --root 之下（拒绝非规范路径）: %s" % raw)
        rel_posix = rel.as_posix()
        if rel_posix in files:
            raise SystemExit("FAIL-CLOSED: 重复输入: %s" % raw)
        files[rel_posix] = sha256_of(rp)
    return {"kind": "manifest-receipt",
            "at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "root": str(root),
            "files_sha256": dict(sorted(files.items())),
            "self_excluded": str(out_path),
            "live_doc_drift": []}


def create_write_once(out_path: Path, doc: dict) -> None:
    # 与 C-1 同款纪律：已存在（含悬空符号链接）即拒，原字节不动。
    with Path(out_path).open("x", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")


def selftest() -> int:
    results = []

    def check(name, ok, detail=""):
        results.append({"case": name, "pass": bool(ok), "detail": detail})

    rc_spec = importlib.util.spec_from_file_location(
        "receipt_check_for_manifest", HERE / "receipt_check.py")
    rc = importlib.util.module_from_spec(rc_spec)
    rc_spec.loader.exec_module(rc)

    with tempfile.TemporaryDirectory(prefix="manifest-receipt-test-") as td:
        tmp = Path(td)
        (tmp / "a.txt").write_bytes(b"alpha\n")
        (tmp / "b.txt").write_bytes(b"beta\n")
        out = tmp / "receipt.json"

        doc = build(out, tmp, ["a.txt", "b.txt"])
        check("build_self_excluded", doc["self_excluded"] == str(out)
              and out.name not in doc["files_sha256"]
              and not any(k.endswith("/" + out.name) for k in doc["files_sha256"]),
              json.dumps(sorted(doc["files_sha256"])))
        create_write_once(out, doc)
        check("write_once_created", out.is_file())
        try:
            create_write_once(out, doc)
            check("write_once_refuses", False)
        except FileExistsError:
            check("write_once_refuses", True)

        rep = rc.check_doc(out, tmp, require_drift=True)
        check("receipt_check_passes_self_excluded",
              rep["ok"] is True and rep.get("self_reference", {}).get("found") is False,
              json.dumps(rep.get("self_reference"), ensure_ascii=False))

        bad = tmp / "selfref.json"
        bad.write_text(json.dumps(
            {"kind": "manifest-receipt",
             "files_sha256": dict(doc["files_sha256"], **{str(bad): "0" * 64}),
             "live_doc_drift": []}, ensure_ascii=False), encoding="utf-8")
        rep_bad = rc.check_doc(bad, tmp, require_drift=True)
        check("receipt_check_rejects_self_reference",
              rep_bad["ok"] is False and rep_bad.get("self_reference", {}).get("found") is True,
              json.dumps(rep_bad.get("self_reference"), ensure_ascii=False))

        try:
            build(tmp / "x.json", tmp, ["x.json"])
            check("self_input_refused", False)
        except SystemExit:
            check("self_input_refused", True)

    counts = {"total": len(results), "passed": sum(1 for r in results if r["pass"]),
              "failed": sum(1 for r in results if not r["pass"])}
    print(json.dumps({"kind": "self_test", "tool": "manifest_receipt.py",
                      "at": datetime.now().astimezone().isoformat(timespec="seconds"),
                      "counts": counts, "cases": results},
                     ensure_ascii=False, indent=2))
    print("MANIFEST_RECEIPT_SELFTEST:", "PASS" if counts["failed"] == 0 else "FAIL")
    return 0 if counts["failed"] == 0 else 1


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=None)
    ap.add_argument("--root", default=str(HERE.parents[1]))
    ap.add_argument("inputs", nargs="*")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.out:
        ap.error("--out 必填（生成模式）")
    if not a.inputs:
        ap.error("至少列出一个 FILE（或 --selftest）")
    doc = build(Path(a.out), Path(a.root), a.inputs)
    create_write_once(Path(a.out), doc)
    print(json.dumps({"out": a.out, "files": len(doc["files_sha256"]),
                      "self_excluded": doc["self_excluded"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
