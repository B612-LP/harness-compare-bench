#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""evidence-kit 收据规范检查器（L3 包C / C2，⑧b）。

对收据/审计文档做**机械**核验（只读，绝不回改任何输入文件）：

1. `live_doc_drift` 状态行：文档须含至少一行 live_doc_drift 状态
   （文本行含 `live_doc_drift` 且带状态记号 none/空/非空/N 项/[]；JSON 则递归查键，
   值须为 null 或 list）。缺状态行 → fail（`--no-drift-require` 可只查哈希行）。
2. 哈希行合规：任何含 hex 记号的行，其 hex 记号须为**小写**且长度 ∈ {7,8,40,64}；
   大写/混写/怪长 hex 记号逐条记 violation（手打哈希的典型形态）。
3. 证据行复算（claimed vs recomputed）：凡匹配 evidence_line.py 标准格式
   `<路径> · <sha8> · <N>B · <时刻>` 的行，按 `--root` 解析文件并**重算** sha8/字节数
   比对；不一致 → fail。对账不到的文件（不存在/仓库外）如实记 unverified，不计 pass。

退出码：全部必需检查通过 exit 0；否则 exit 1；用法错误 exit 2。
报告写 `--out`（目标已存在即拒绝，同 C-1 纪律）；无 `--out` 只打印不落盘。

用法：
    python3 receipt_check.py <doc> [<doc> ...] [--root <repo-root>] [--out <report.json>]
                             [--no-drift-require]
    python3 receipt_check.py --selftest
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
EVIDENCE_LINE_RE = (r"^(?P<path>.+?) · (?P<sha8>[0-9a-f]{8}) · (?P<bytes>\d+)B · "
                    r"(?P<at>" + ISO_TZ_TOKEN + r")$")
HEX_TOKEN_RE = re.compile(r"\b([0-9a-fA-F]{7,64})\b")
VALID_HEX_LEN = {7, 8, 40, 64}
DRIFT_STATUS_RE = re.compile(r"live_doc_drift", re.I)
DRIFT_STATE_RE = re.compile(r"(none|非空|空|\[\]|\d+\s*项)", re.I)


def now_local() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def iter_json_strings(node):
    if isinstance(node, dict):
        for k, v in node.items():
            yield k, v
            yield from iter_json_strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from iter_json_strings(v)


def check_doc(path: Path, root: Path, require_drift: bool) -> dict:
    rep = {"file": str(path), "exists": path.is_file(),
           "live_doc_drift": {"required": require_drift, "found": False, "lines": []},
           "hash_lines": {"scanned": 0, "tokens": 0, "violations": []},
           "evidence_lines": {"total": 0, "verified_ok": 0, "verified_bad": 0,
                               "unverified": 0, "details": []},
           "ok": False}
    if not path.is_file():
        rep["hash_lines"]["violations"].append({"line": None, "reason": "file unreadable"})
        return rep
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")

    # ---- 1) live_doc_drift 状态 ----
    is_json = False
    try:
        doc = json.loads(text)
        is_json = isinstance(doc, (dict, list))
    except Exception:
        doc = None
    if is_json:
        for k, v in iter_json_strings(doc):
            if k == "live_doc_drift":
                wellformed = v is None or isinstance(v, list)
                rep["live_doc_drift"]["found"] = True
                rep["live_doc_drift"]["lines"].append(
                    {"kind": "json-key", "wellformed": wellformed, "value_kind": type(v).__name__,
                     "length": len(v) if isinstance(v, list) else None})
    else:
        for i, line in enumerate(text.splitlines(), 1):
            if DRIFT_STATUS_RE.search(line):
                state = bool(DRIFT_STATE_RE.search(line))
                rep["live_doc_drift"]["lines"].append(
                    {"kind": "text-line", "line": i, "has_state_token": state,
                     "excerpt": line[:160]})
                if state:
                    rep["live_doc_drift"]["found"] = True
    if require_drift and not rep["live_doc_drift"]["found"]:
        rep["hash_lines"]["violations"].append(
            {"line": None, "reason": "live_doc_drift 状态行缺失"})

    # ---- 2) 哈希行合规 + 3) 证据行复算 ----
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(EVIDENCE_LINE_RE, line.strip())
        if m:
            rep["evidence_lines"]["total"] += 1
            target = Path(m.group("path"))
            if not target.is_absolute():
                target = root / target
            detail = {"line": i, "claimed": {"path": m.group("path"),
                                             "sha256_8": m.group("sha8"),
                                             "bytes": int(m.group("bytes"))}}
            if target.is_file():
                digest = sha256_of(target)
                actual = {"sha256_8": digest[:8], "bytes": target.stat().st_size}
                match = (actual["sha256_8"] == detail["claimed"]["sha256_8"]
                         and actual["bytes"] == detail["claimed"]["bytes"])
                detail.update({"verified": True, "match": match, "actual": actual})
                rep["evidence_lines"]["verified_ok" if match else "verified_bad"] += 1
            else:
                detail.update({"verified": False, "reason": "文件不可达（unverified，不计 pass）"})
                rep["evidence_lines"]["unverified"] += 1
            rep["evidence_lines"]["details"].append(detail)
            continue
        tokens = HEX_TOKEN_RE.findall(line)
        if not tokens:
            continue
        rep["hash_lines"]["scanned"] += 1
        bad = []
        for t in tokens:
            if not re.search(r"[a-fA-F]", t):
                continue  # 纯数字（日期/计数等）不是 hex 记号，跳过
            if t.lower() != t or len(t) not in VALID_HEX_LEN:
                bad.append({"token": t, "reason": "hex 记号（含字母）须小写且长度 ∈ {7,8,40,64}"})
        rep["hash_lines"]["tokens"] += len(tokens)
        if bad:
            rep["hash_lines"]["violations"].append({"line": i, "issues": bad,
                                                    "excerpt": line[:160]})

    drift_ok = (rep["live_doc_drift"]["found"] or not require_drift)
    rep["ok"] = bool(drift_ok
                     and not rep["hash_lines"]["violations"]
                     and rep["evidence_lines"]["verified_bad"] == 0)
    return rep


def selftest() -> int:
    results = []

    def check(name, ok, detail=""):
        results.append({"case": name, "pass": bool(ok), "detail": detail})
        return bool(ok)

    with tempfile.TemporaryDirectory(prefix="evidence-kit-check-") as td:
        tmp = Path(td)
        target = tmp / "payload.txt"
        target.write_bytes(b"receipt checker fixture\n")
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        good_line = "payload.txt · %s · %dB · 2026-10-29T18:00:00+08:00" % (digest[:8], 24)

        good = tmp / "good-receipt.md"
        good.write_text("# 收据\n\nlive_doc_drift: none（0 项）\n\n%s\n" % good_line,
                        encoding="utf-8")
        r1 = check_doc(good, tmp, require_drift=True)
        check("good_doc_ok", r1["ok"] is True, json.dumps(r1["evidence_lines"]))
        check("good_evidence_recomputed", r1["evidence_lines"]["verified_ok"] == 1)
        check("good_drift_found", r1["live_doc_drift"]["found"] is True)

        bad = tmp / "bad-receipt.md"
        bad.write_text("哈希：ABCDEF123（大写手打）\n另一条：0Xf00dfeed（怪长）\n",
                       encoding="utf-8")
        r2 = check_doc(bad, tmp, require_drift=True)
        check("bad_doc_fails", r2["ok"] is False)
        check("bad_hash_violations", len(r2["hash_lines"]["violations"]) >= 2,
              str(r2["hash_lines"]["violations"]))
        check("bad_drift_missing", r2["live_doc_drift"]["found"] is False)

        r3 = check_doc(bad, tmp, require_drift=False)
        check("no_drift_require_still_fails_on_hash", r3["ok"] is False)

        stale = tmp / "stale-receipt.md"
        stale.write_text("live_doc_drift: 非（示例）\n%s\n" %
                         ("payload.txt · 00000000 · 24B · 2026-10-29T18:00:00+08:00"),
                         encoding="utf-8")
        r4 = check_doc(stale, tmp, require_drift=True)
        check("stale_evidence_detected", r4["evidence_lines"]["verified_bad"] == 1
              and r4["ok"] is False)

        jr = tmp / "ledger.json"
        jr.write_text(json.dumps({"live_doc_drift": [], "note": "ok"}), encoding="utf-8")
        r5 = check_doc(jr, tmp, require_drift=True)
        check("json_drift_key_ok", r5["live_doc_drift"]["found"] is True and r5["ok"] is True)

        missing = tmp / "nope.md"
        r6 = check_doc(missing, tmp, require_drift=True)
        check("missing_file_not_ok", r6["ok"] is False and r6["exists"] is False)

    counts = {"total": len(results), "passed": sum(1 for r in results if r["pass"]),
              "failed": sum(1 for r in results if not r["pass"])}
    print(json.dumps({"kind": "self_test", "tool": "receipt_check.py",
                      "at": now_local(), "counts": counts, "cases": results},
                     ensure_ascii=False, indent=2))
    print("RECEIPT_CHECK_SELFTEST:", "PASS" if counts["failed"] == 0 else "FAIL")
    return 0 if counts["failed"] == 0 else 1


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("docs", nargs="*", metavar="DOC")
    ap.add_argument("--root", default=str(REPO))
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-drift-require", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.docs:
        ap.print_help()
        return 2
    reports = [check_doc(Path(d), Path(a.root), not a.no_drift_require) for d in a.docs]
    report = {"kind": "receipt_check_report", "tool": "receipt_check.py",
              "at": now_local(), "root": a.root,
              "require_drift": not a.no_drift_require,
              "docs": reports,
              "all_ok": all(r["ok"] for r in reports)}
    print(json.dumps({"all_ok": report["all_ok"],
                      "per_doc": [{"file": r["file"], "ok": r["ok"],
                                   "drift_found": r["live_doc_drift"]["found"],
                                   "hash_violations": len(r["hash_lines"]["violations"]),
                                   "evidence_bad": r["evidence_lines"]["verified_bad"],
                                   "evidence_unverified": r["evidence_lines"]["unverified"]}
                                  for r in reports]}, ensure_ascii=False, indent=1))
    if a.out:
        out = Path(a.out)
        if out.exists():
            print("拒绝写入：目标已存在（C-1 同款纪律），原字节不动。", file=sys.stderr)
            return 2
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("REPORT:", out)
    return 0 if report["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
