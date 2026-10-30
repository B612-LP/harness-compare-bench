#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""evidence-kit 收据规范检查器（L3 包C / C2，⑧b）。

对收据/审计文档做**机械**核验（只读，绝不回改任何输入文件）：

1. `live_doc_drift` 状态行：文档须含至少一行 live_doc_drift 状态
   （文本行含 `live_doc_drift` 且带状态记号 none/空/非空/N 项/[]；JSON 则递归查键，
   值须为 null 或 list——**字符串等其它值记 violation 并判 fail**，DF-C2）。
   缺状态行 → fail（`--no-drift-require` 可只查哈希行）。
2. 哈希行合规：任何含 hex 记号的行，其 hex 记号须为**小写**且长度 ∈ {7,8,40,64}；
   hex 形似串（含字母）长度越界（含 >64 超长）一律记 violation（DF-C1：显式环视匹配，
   CJK 前贴/后贴均命中；纯数字串视作日期/计数不查）。
3. 证据行复算（claimed vs recomputed）：凡匹配 evidence_line.py 标准格式
   `<路径> · <sha8> · <N>B · <时刻>` 的行，按 `--root` 解析文件并**重算** sha8/字节数
   比对；不一致 → fail。对账不到的文件（不存在/仓库外）如实记 unverified，不计 pass。
4. 废止链机器可读（L8-A，2026-10-30，AUD-L7-O1→supersedes 后向指针设计）：
   JSON 收据含可选 `supersedes` 字段时，每项须恰为 {file, sha256}（64 位小写全哈希）；
   file 相对收据父目录解析、必须存在、sha256 与实算一致、文件名须含 `VOIDED`；
   禁自引、禁重复条目、沿链上行深度 ≤16 不得成环；任一违反 → fail。
   **无该字段行为逐字节不变**（历史收据零改动原则，不追溯补写）。

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
# DF-C1 修复：显式环视替代 \b（\b 为 Unicode 词边界，CJK 与 hex 同为词字符 →
# 中文前贴哈希 0 命中）；下界 {7,} 捕获任意长串，长度 ∉ {7,8,40,64}（含 >64 超长）
# 一律记违规。
HEX_TOKEN_RE = re.compile(r"(?<![0-9A-Za-z])([0-9a-fA-F]{7,})(?![0-9A-Za-z])")
VALID_HEX_LEN = {7, 8, 40, 64}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SUPERSEDES_MAX_DEPTH = 16
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


def validate_supersession(field, receipt_path: Path) -> dict:
    """L8-A（2026-10-30）：废止链机器可读校验（AUD-L7-O1→supersedes 后向指针）。

    语义：存续收据声明「我取代这些已废止收据」。方向选择见 L8 PREREG：O1 原文的
    前向指针（superseded_by）在终局收据文件名不可预知的链上（L7 实证）要么事后改
    已定稿字节、要么存空哈希；后向指针单次 write-once、全哈希锚定、可机械验证
    被指文件名含 VOIDED。返回 {"found","entries","violations"}（violations 空=过）。
    """
    v: list = []
    entries: list = []
    if not isinstance(field, list):
        return {"found": True, "entries": [], "violations":
                ["supersedes 须为 list，实测 %s" % type(field).__name__]}
    seen = set()
    targets = []
    for i, ent in enumerate(field):
        where = "supersedes[%d]" % i
        if not isinstance(ent, dict):
            v.append("%s: 须为 object，实测 %s" % (where, type(ent).__name__))
            continue
        if set(ent.keys()) != {"file", "sha256"}:
            v.append("%s: 键须恰为 {file, sha256}，实测 %s"
                     % (where, sorted(map(str, ent.keys()))))
            continue
        f, s = ent["file"], ent["sha256"]
        if not isinstance(f, str) or not f:
            v.append("%s.file: 须为非空字符串" % where)
            continue
        if not isinstance(s, str) or not SHA256_RE.match(s):
            v.append("%s.sha256: 须为 64 位小写 hex" % where)
            continue
        key = (f, s)
        if key in seen:
            v.append("%s: 重复条目 (%s)" % (where, f))
            continue
        seen.add(key)
        t_self = Path(f)
        if not t_self.is_absolute():
            t_self = receipt_path.parent / t_self
        if t_self.resolve() == receipt_path.resolve():
            v.append("%s: 自引（收据不得 supersedes 自身）" % where)
            continue
        if "VOIDED" not in Path(f).name:
            v.append("%s: 被指文件名须含 VOIDED（人机双载体）: %s" % (where, f))
            continue
        target = Path(f)
        if not target.is_absolute():
            target = receipt_path.parent / target
        if not target.is_file():
            v.append("%s: 被指文件不存在: %s" % (where, f))
            continue
        actual = sha256_of(target)
        if actual != s:
            v.append("%s: sha256 不符 want=%s… actual=%s…" % (where, s[:8], actual[:8]))
            continue
        entries.append({"file": f, "sha256": s, "verified": True})
        targets.append(target)

    def walk(p: Path, stack: frozenset, depth: int) -> bool:
        """沿被指收据自身的 supersedes 上行；回到出发收据=环。"""
        if p.resolve() == receipt_path.resolve():
            return True
        if depth >= SUPERSEDES_MAX_DEPTH or p.resolve() in stack:
            return False
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return False
        if not (isinstance(d, dict) and isinstance(d.get("supersedes"), list)):
            return False
        for ent in d["supersedes"]:
            if not (isinstance(ent, dict) and isinstance(ent.get("file"), str)):
                continue
            child = Path(ent["file"])
            if not child.is_absolute():
                child = p.parent / child
            if child.is_file() and walk(child, stack | {p.resolve()}, depth + 1):
                return True
        return False

    for t in targets:
        if walk(t, frozenset(), 0):
            v.append("supersedes 链成环（经 %s 回到收据自身）" % t.name)
            break
    return {"found": True, "entries": entries, "violations": v}


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
                # DF-C2 修复：wellformed 必须参与判定——字符串等糊弄值记 violation
                if not wellformed:
                    rep["hash_lines"]["violations"].append(
                        {"line": None, "reason": "JSON live_doc_drift 值须为 null 或 list，实测 %s"
                                                 % type(v).__name__})
        # L6-C（2026-10-30）：收据自引排除（AUD-L5-O1 wart 类）——JSON 收据含 dict 型
        # files_sha256 映射时，其键不得含收据自身路径/文件名：自引哈希逻辑上不可自证
        #（列示值只能是定稿前某版本，违「哈希即终态」直觉）。manifest-receipt 生成器
        # （manifest_receipt.py）以 self_excluded 字段显式声明排除。
        if isinstance(doc, dict) and isinstance(doc.get("files_sha256"), dict):
            own_names = {path.name, str(path)}
            self_refs = sorted({k for k in doc["files_sha256"]
                                if isinstance(k, str) and (k in own_names
                                                           or k.endswith("/" + path.name))})
            rep["self_reference"] = {"found": bool(self_refs), "keys": self_refs}
            if self_refs:
                rep["hash_lines"]["violations"].append(
                    {"line": None,
                     "reason": "self-referenced hash entry（AUD-L5-O1：收据不得列入自身）: %s"
                               % ", ".join(self_refs)})
        # L8-A（2026-10-30）：废止链机器可读（AUD-L7-O1→supersedes 后向指针设计，
        # PREREG 已声明方向偏离）。无该字段=行为逐字节不变（历史收据零改动原则）。
        if isinstance(doc, dict) and "supersedes" in doc:
            sup = validate_supersession(doc["supersedes"], path)
            rep["supersession"] = sup
            for reason in sup["violations"]:
                rep["hash_lines"]["violations"].append(
                    {"line": None, "reason": "supersession(L8-A): " + reason})
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

        # ---- DF-C1 修复用例：CJK 前贴 / 超长串（修复前 0 命中）----
        full64 = "5c6177fd68a74ab9" + "0123456789abcdef" * 3  # 64 位小写（16+48）
        assert len(full64) == 64
        cjk_ok = tmp / "cjk-ok.md"
        cjk_ok.write_text("哈希%s（前贴中文无空格，合规 64 位小写）\n" % full64, encoding="utf-8")
        r7 = check_doc(cjk_ok, tmp, require_drift=False)
        check("cjk_prefixed_64hex_captured",
              r7["hash_lines"]["tokens"] >= 1 and not r7["hash_lines"]["violations"],
              json.dumps(r7["hash_lines"], ensure_ascii=False)[:200])
        cjk_bad = tmp / "cjk-bad.md"
        cjk_bad.write_text("假哈希deadbeefdead（12 位，前贴中文）\n"
                           "超长%s（70 位）\n" % ("deadbeef" * 8 + "cafe",),
                           encoding="utf-8")
        r8 = check_doc(cjk_bad, tmp, require_drift=False)
        bad_lens = sorted(i["token"] for v in r8["hash_lines"]["violations"]
                          for i in v.get("issues", []))
        check("cjk_prefixed_short_flagged", any("deadbeefdead" in t for t in bad_lens),
              str(bad_lens))
        check("overlong_hex_flagged", any(len(t) > 64 for t in bad_lens), str(bad_lens))

        # ---- DF-C2 修复用例：JSON 字符串值糊弄必须 fail ----
        js = tmp / "drift-string.json"
        js.write_text(json.dumps({"live_doc_drift": "none", "note": "糊弄值"}, ensure_ascii=False),
                      encoding="utf-8")
        r9 = check_doc(js, tmp, require_drift=True)
        check("json_drift_string_value_fails",
              r9["ok"] is False and r9["live_doc_drift"]["found"] is True,
              json.dumps(r9["hash_lines"]["violations"], ensure_ascii=False)[:200])

        # ---- L6-C（2026-10-30）收据自引排除：正例 self-excluded / 负例自引必拒 ----
        selfok = tmp / "manifest-receipt-ok.json"
        selfok.write_text(json.dumps(
            {"kind": "manifest-receipt", "at": "2026-10-30T11:00:00+08:00",
             "files_sha256": {"payload.txt": digest},
             "self_excluded": str(selfok), "live_doc_drift": []},
            ensure_ascii=False), encoding="utf-8")
        r10 = check_doc(selfok, tmp, require_drift=True)
        check("self_excluded_receipt_ok",
              r10["ok"] is True and r10.get("self_reference", {}).get("found") is False,
              json.dumps(r10.get("self_reference"), ensure_ascii=False))
        selfbad = tmp / "manifest-receipt-selfref.json"
        full64 = "5c6177fd68a74ab9" + "0123456789abcdef" * 3
        selfbad.write_text(json.dumps(
            {"kind": "manifest-receipt",
             "files_sha256": {"payload.txt": digest, str(selfbad): full64},
             "live_doc_drift": []},
            ensure_ascii=False), encoding="utf-8")
        r11 = check_doc(selfbad, tmp, require_drift=True)
        check("self_referenced_receipt_rejected",
              r11["ok"] is False and r11.get("self_reference", {}).get("found") is True,
              json.dumps(r11.get("self_reference"), ensure_ascii=False))

        # ---- L8-A（2026-10-30）废止链 supersedes：正例 + 负例组 + 链环 ----
        prev = tmp / "prev-attempt-VOIDED-设计误.json"
        prev.write_text(json.dumps({"kind": "demo-prev", "live_doc_drift": []},
                                   ensure_ascii=False), encoding="utf-8")
        prev_sha = hashlib.sha256(prev.read_bytes()).hexdigest()
        ok_sup = tmp / "final-supersedes-ok.json"
        ok_sup.write_text(json.dumps(
            {"kind": "demo-final",
             "supersedes": [{"file": prev.name, "sha256": prev_sha}],
             "live_doc_drift": []}, ensure_ascii=False), encoding="utf-8")
        r12 = check_doc(ok_sup, tmp, require_drift=True)
        check("supersedes_positive_ok",
              r12["ok"] is True and r12["supersession"]["violations"] == []
              and len(r12["supersession"]["entries"]) == 1,
              json.dumps(r12.get("supersession"), ensure_ascii=False)[:200])

        def neg_sup(name, field, needle):
            p = tmp / name
            p.write_text(json.dumps({"kind": "demo-neg", "supersedes": field,
                                     "live_doc_drift": []}, ensure_ascii=False),
                         encoding="utf-8")
            r = check_doc(p, tmp, require_drift=False)
            reasons = " | ".join(
                x.get("reason", "") or " ".join(i.get("reason", "")
                                                for i in x.get("issues", []))
                for x in r["hash_lines"]["violations"])
            check(name, r["ok"] is False and needle in reasons, reasons[:200])

        neg_sup("sup_bad_sha.json", [{"file": prev.name, "sha256": "0" * 64}],
                "sha256 不符")
        neg_sup("sup_missing_file.json",
                [{"file": "nope-VOIDED-x.json", "sha256": prev_sha}], "不存在")
        plain = tmp / "plain-prev.json"
        plain.write_text("{}\n", encoding="utf-8")
        neg_sup("sup_not_voided_name.json",
                [{"file": plain.name,
                  "sha256": hashlib.sha256(plain.read_bytes()).hexdigest()}],
                "VOIDED")
        neg_sup("sup_selfref.json", [{"file": "sup_selfref.json",
                                      "sha256": prev_sha}], "自引")
        neg_sup("sup_extra_key.json",
                [{"file": prev.name, "sha256": prev_sha, "note": "x"}], "键须恰为")
        neg_sup("sup_bad_sha_format.json",
                [{"file": prev.name, "sha256": prev_sha.upper()}], "64 位小写")
        neg_sup("sup_not_list.json", {"file": prev.name}, "须为 list")

        # 链环：cyc-a → cyc-b → cyc-a（walk 不校验被指收据自身条目，只沿链跟随）
        cyc_b = tmp / "cyc-b-VOIDED.json"
        cyc_a = tmp / "cyc-a-VOIDED.json"
        cyc_b.write_text(json.dumps({"kind": "cyc-b", "supersedes": [
            {"file": "cyc-a-VOIDED.json", "sha256": "0" * 64}],
            "live_doc_drift": []}, ensure_ascii=False), encoding="utf-8")
        cyc_a.write_text(json.dumps({"kind": "cyc-a", "supersedes": [
            {"file": cyc_b.name,
             "sha256": hashlib.sha256(cyc_b.read_bytes()).hexdigest()}],
            "live_doc_drift": []}, ensure_ascii=False), encoding="utf-8")
        rc = check_doc(cyc_a, tmp, require_drift=False)
        rc_reasons = " | ".join(x["reason"] for x in rc["hash_lines"]["violations"])
        check("supersedes_cycle_detected", rc["ok"] is False and "成环" in rc_reasons,
              rc_reasons[:200])

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
