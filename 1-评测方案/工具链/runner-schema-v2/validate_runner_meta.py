#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runner-schema-v2 校验器（stdlib-only）。

模式：
  --spec   对 fixtures/ 合成样本自检：逐 fixture 实际判定须与 manifest.json 期望一致，
           全部一致则 exit 0（任何不一致 exit 1）。
  --retro  对一个或多个 runs 目录只读扫描，产出兼容矩阵 JSON：
           每场 × 每必备字段的 有/缺/类型/精度 状态 + 批级汇总。
           矩阵是披露性 delta 报告，不是对历史批次的追溯判定。

规范：同目录 SCHEMA.md（L2 包C，封印 commit ae36f67）。
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = "runner-schema-v2"
DISCLOSURE = ("该矩阵是披露性 delta 报告，不是对 r1031 的追溯判定"
              "（D1 已由 lead 裁决闭项：不回填）。")

# 必备字段集：(字段名, 类型 kind)。类型语义见 check_kind。
REQUIRED_FIELDS = [
    ("batch", "str"), ("rule_version", "str"), ("preregistration_commit", "hex_commit"),
    ("registered_at", "iso_tz"), ("rep", "int"), ("product", "str"), ("case", "str"),
    ("form", "str"), ("run_id", "str"), ("event_id", "str"), ("selection", "dict_null"),
    ("workspace", "str"), ("model", "str"), ("reasoning_effort", "str"),
    ("product_version", "str"), ("route", "dict"), ("tools", "list"),
    ("permissions", "str"), ("skills", "str"), ("web_search", "str"),
    ("soft_constraints", "list"), ("prompt_sha256", "hex64"), ("isolation", "dict"),
    ("inputs", "list"), ("status", "str"), ("exit_code", "int_null"),
    ("created_at", "iso_tz"), ("started_at", "iso_tz"), ("finished_at", "iso_tz"),
    ("duration_s", "num"), ("attempts", "list"), ("transport_retries", "int"),
    ("stdout_bytes", "int_nonneg"), ("stdout_sha256", "hex64"),
    ("stderr_bytes", "int_nonneg"), ("stderr_sha256", "hex64"),
    ("usage", "dict"), ("reward", "int_null"), ("weighted", "score8"),
    ("failed", "list"), ("judge", "dict"), ("integrity", "dict"),
    ("integrity_verdict", "str"),
]

JUDGE_COUNT_PAIRS = [("correct", "n_questions"), ("correct", "n_tasks"),
                     ("passed_problems", "total_problems"), ("passed", "total")]


# ---------------------------------------------------------------- 基础检查

def check_kind(kind: str, v) -> bool:
    if kind == "str":
        return isinstance(v, str) and v != ""
    if kind == "int":
        return isinstance(v, int) and not isinstance(v, bool)
    if kind == "int_nonneg":
        return isinstance(v, int) and not isinstance(v, bool) and v >= 0
    if kind == "int_null":
        return v is None or (isinstance(v, int) and not isinstance(v, bool))
    if kind == "num":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    if kind == "dict":
        return isinstance(v, dict)
    if kind == "dict_null":
        return v is None or isinstance(v, dict)
    if kind == "list":
        return isinstance(v, list)
    if kind == "hex64":
        return isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v) is not None
    if kind == "hex_commit":
        return isinstance(v, str) and re.fullmatch(r"[0-9a-f]{7,40}", v) is not None
    if kind == "iso_tz":
        if not isinstance(v, str):
            return False
        try:
            d = dt.datetime.fromisoformat(v)
        except ValueError:
            return False
        return d.tzinfo is not None
    if kind == "score8":
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return False
        return abs(float(v) - round(float(v), 8)) < 1e-9
    raise ValueError("unknown kind: %s" % kind)


def parse_iso(v: str):
    return dt.datetime.fromisoformat(v)


def expected_score8(judge: dict):
    """judge 计数可导出时返回 round(earned/possible*100,8)，否则 None。"""
    if not isinstance(judge, dict):
        return None
    for a, b in JUDGE_COUNT_PAIRS:
        ea, pb = judge.get(a), judge.get(b)
        if isinstance(ea, int) and isinstance(pb, int) and not isinstance(ea, bool) \
                and not isinstance(pb, bool) and pb > 0:
            return round(ea / pb * 100, 8)
    return None


# ---------------------------------------------------------------- 单场校验

def validate_meta(meta: dict, seal_at=None, receipt: dict | None = None) -> dict:
    """返回逐字段状态 + 时序/精度问题清单。不修改输入。"""
    cells, issues = {}, []
    for name, kind in REQUIRED_FIELDS:
        if name not in meta:
            cells[name] = {"present": False, "status": "missing"}
            issues.append({"field": name, "class": "missing", "detail": "required field absent"})
            continue
        v = meta[name]
        cell = {"present": True, "value_type": type(v).__name__}
        if not check_kind(kind, v):
            cell["status"] = "type_error"
            issues.append({"field": name, "class": "type",
                           "detail": "expect %s got %s" % (kind, type(v).__name__)})
        else:
            cell["status"] = "ok"
            if kind == "score8":
                exp = expected_score8(meta.get("judge"))
                if exp is not None:
                    cell["expected_8dp"] = exp
                    if float(v) != exp:
                        cell["status"] = "precision_error"
                        issues.append({"field": name, "class": "precision",
                                       "detail": "value=%r expected 8dp=%r" % (v, exp)})
                    else:
                        cell["precision"] = "ok"
                else:
                    cell["precision"] = "representable_only"
        cells[name] = cell
    # registered_at 时序（仅当类型已 ok）
    ra = cells.get("registered_at", {})
    temporal = {"order": "not_evaluable", "seal": "not_evaluable"}
    if ra.get("status") == "ok":
        radt = parse_iso(meta["registered_at"])
        sat = meta.get("started_at")
        if isinstance(sat, str):
            try:
                sdt = parse_iso(sat)
                temporal["order"] = "ok" if radt < sdt else "violation"
                if radt >= sdt:
                    issues.append({"field": "registered_at", "class": "temporal-order",
                                   "detail": "registered_at %s >= started_at %s"
                                             % (meta["registered_at"], sat)})
            except ValueError:
                pass
        if seal_at is not None:
            temporal["seal"] = "ok" if radt >= seal_at else "violation"
            if radt < seal_at:
                issues.append({"field": "registered_at", "class": "temporal-seal",
                               "detail": "registered_at %s < seal_at %s"
                                         % (meta["registered_at"], seal_at.isoformat())})
    elif ra.get("status") in ("type_error", "missing"):
        temporal = {"order": "not_evaluable", "seal": "not_evaluable",
                    "reason": "registered_at %s" % ra.get("status")}
    # 收据 canonical 层（D2 主锚点）
    receipt_cell = None
    if receipt is not None:
        rep = (receipt.get("score") or {}).get("reported") if isinstance(receipt.get("score"), dict) else None
        receipt_cell = {"present": rep is not None, "value_type": type(rep).__name__ if rep is not None else None}
        if rep is None:
            receipt_cell["status"] = "missing"
        elif isinstance(rep, bool) or not isinstance(rep, (int, float)):
            receipt_cell["status"] = "type_error"
            issues.append({"field": "score-receipt:score.reported", "class": "type",
                           "detail": "got %s" % type(rep).__name__})
        else:
            exp = expected_score8(meta.get("judge")) or expected_score8(
                (receipt.get("raw_checker_output") or {}))
            receipt_cell["status"] = "ok"
            if exp is not None:
                receipt_cell["expected_8dp"] = exp
                if float(rep) != exp:
                    receipt_cell["status"] = "precision_error"
                    issues.append({"field": "score-receipt:score.reported", "class": "precision",
                                   "detail": "value=%r expected 8dp=%r" % (rep, exp)})
                else:
                    receipt_cell["precision"] = "ok"
            else:
                receipt_cell["precision"] = "representable_only"
    return {"fields": cells, "registered_at_temporal": temporal,
            "receipt_score_reported": receipt_cell, "issues": issues}


FAIL_PRECEDENCE = [("missing", "fail:missing"), ("type", "fail:type"),
                   ("precision", "fail:precision"), ("temporal-order", "fail:temporal-order"),
                   ("temporal-seal", "fail:temporal-seal")]


def classify(result: dict) -> str:
    classes = {i["class"] for i in result["issues"]}
    if "missing" in classes:
        return "fail:missing"
    if "type" in classes:
        return "fail:type"
    if "precision" in classes:
        return "fail:precision"
    if "temporal-order" in classes:
        return "fail:temporal-order"
    if "temporal-seal" in classes:
        return "fail:temporal-seal"
    return "pass"


# ---------------------------------------------------------------- --spec

def cmd_spec(fixtures_dir: Path, seal_override) -> int:
    manifest = json.loads((fixtures_dir / "manifest.json").read_text(encoding="utf-8"))
    seal = seal_override or manifest.get("seal_at")
    seal_dt = parse_iso(seal) if seal else None
    results, all_ok = {}, True
    for fname in sorted(manifest["fixtures"]):
        expect = manifest["fixtures"][fname]
        meta = json.loads((fixtures_dir / fname).read_text(encoding="utf-8"))
        res = validate_meta(meta, seal_at=seal_dt)
        got = classify(res)
        ok = got == expect
        all_ok &= ok
        results[fname] = {"expect": expect, "got": got, "match": ok,
                          "issues": res["issues"]}
    receipt = {"kind": "self_test", "tool": "validate_runner_meta.py --spec", "spec": SPEC,
               "at": now_local(), "seal_at_used": seal,
               "fixtures_dir": str(fixtures_dir), "results": results, "all_match": all_ok}
    (HERE / "spec-selftest-receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: (v["expect"], v["got"], v["match"]) for k, v in results.items()},
                     ensure_ascii=False, indent=1))
    print("SPEC_SELFTEST:", "PASS" if all_ok else "FAIL")
    return 0 if all_ok else 1


# ---------------------------------------------------------------- --retro

def scan_runs_dir(runs_dir: Path):
    for d in sorted(runs_dir.iterdir()):
        meta_p = d / "meta.json"
        if not d.is_dir() or not meta_p.exists():
            continue
        receipt_p = d / "score-receipt.json"
        receipt = json.loads(receipt_p.read_text(encoding="utf-8")) if receipt_p.exists() else None
        yield d.name, json.loads(meta_p.read_text(encoding="utf-8")), receipt


def cmd_retro(runs_dirs: list[Path], out: Path, seal_override) -> int:
    seal_dt = parse_iso(seal_override) if seal_override else None
    runs, missing = {}, {}
    type_err, prec_receipt, prec_meta = {}, [], []
    for rd in runs_dirs:
        for dname, meta, receipt in scan_runs_dir(rd):
            res = validate_meta(meta, seal_at=seal_dt, receipt=receipt)
            rid = meta.get("run_id", dname)
            product = meta.get("product", "unknown")
            row = {"evidence_dir": str(rd / dname), "product": product,
                   "registered_at_temporal": res["registered_at_temporal"],
                   "receipt_score_reported": res["receipt_score_reported"]}
            if (meta.get("archived_stdout") or None) is not None:
                row["dsh_archived_stdout_map"] = {
                    "full_bytes": (meta["archived_stdout"] or {}).get("full_bytes"),
                    "full_file": (meta["archived_stdout"] or {}).get("full_file")}
            for name, cell in res["fields"].items():
                row[name] = cell
                st = cell.get("status")
                if st == "missing":
                    missing.setdefault(name, {}).setdefault(product, []).append(rid)
                elif st == "type_error":
                    type_err.setdefault(name, {}).setdefault(product, []).append(rid)
                elif st == "precision_error":
                    prec_meta.append({"run": rid, "product": product, "field": name,
                                      "detail": next(i["detail"] for i in res["issues"]
                                                     if i["field"] == name and i["class"] == "precision")})
            if res["receipt_score_reported"] and res["receipt_score_reported"]["status"] == "precision_error":
                prec_receipt.append({"run": rid, "product": product,
                                     "detail": next(i["detail"] for i in res["issues"]
                                                    if i["field"] == "score-receipt:score.reported")})
            runs[rid] = row
    tool_sha = sha256_file(Path(__file__))
    matrix = {
        "schema": "runner-meta-v2-compat-matrix", "spec": SPEC,
        "generated_at": now_local(),
        "disclosure": DISCLOSURE,
        "seal_at_provided": seal_override,
        "targets": [str(p) for p in runs_dirs],
        "required_fields": [n for n, _ in REQUIRED_FIELDS],
        "tool_sha256": tool_sha,
        "runs": runs,
        "summary": {
            "n_runs": len(runs),
            "missing_by_field_by_product": {k: {p: len(v) for p, v in vv.items()}
                                            for k, vv in sorted(missing.items())},
            "type_error_by_field_by_product": {k: {p: len(v) for p, v in vv.items()}
                                               for k, vv in sorted(type_err.items())},
            "precision_receipt_reported_runs": prec_receipt,
            "precision_meta_weighted_runs": prec_meta,
        },
    }
    out.write_text(json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(matrix["summary"], ensure_ascii=False, indent=1)[:4000])
    print("RETRO_MATRIX:", out)
    return 0


# ---------------------------------------------------------------- util

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def now_local() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", action="store_true")
    ap.add_argument("--retro", action="append", default=[], metavar="RUNS_DIR")
    ap.add_argument("--fixtures", default=str(HERE / "fixtures"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--seal-at", default=None)
    a = ap.parse_args(argv)
    if a.spec:
        return cmd_spec(Path(a.fixtures), a.seal_at)
    if a.retro:
        if not a.out:
            print("--retro 需要 --out", file=sys.stderr)
            return 2
        return cmd_retro([Path(p) for p in a.retro], Path(a.out), a.seal_at)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
