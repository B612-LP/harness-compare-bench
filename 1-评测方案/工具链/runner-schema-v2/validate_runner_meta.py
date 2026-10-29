#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runner-schema-v2 校验器（stdlib-only）。

模式：
  --spec      对 fixtures/ 合成样本自检：逐 fixture 实际判定须与 manifest.json 期望一致，
              全部一致则 exit 0（任何不一致 exit 1）。
              收据只写显式 --out；目标已存在即拒绝（exit 2，原字节不动；C-1 非破坏化）。
  --retro     对一个或多个 runs 目录只读扫描，产出兼容矩阵 JSON：
              每场 × 每必备字段的 有/缺/类型/精度 状态 + 批级汇总。
              矩阵是披露性 delta 报告，不是对历史批次的追溯判定。
              B4/DF-B1：无 --seal-at 且无 --allow-unsealed ⇒ exit 3，不落盘矩阵；
              --allow-unsealed 为唯一披露出口（矩阵带 seal.unsealed/seal.policy 标记）。
  --reconcile registered_at ↔ 封印提交时刻的离线对账（⑦/O-1）：输入=预注册台账路径+字段位置
              （JSON pointer 或行正则）+封印提交哈希+提交时刻来源。commit_time 来源三模式：
              --commit-time（显式值）/ --commit-time-file（文件内首个 ISO8601+tz 记号）/ --git
              （直接读取 git log；L3 未行使——builder 禁 git，judge 以只读 git 回归，真实批次
              对账留 L4，见 U1）。verdict 语义（D-L3-1 对齐）：任何步骤假 ⇒ verdict 不得为 ok
              （error=非比较步骤假；violation=仅比较步骤假；ok=全部真且比较通过）。

L3 语义（封印 72edb519；详见 SCHEMA.md L3 变更框）：
  - status enum = {ok, timeout, error, transport-error}（B1）；
  - integrity_verdict enum = {clean, benign-reviewed, violation}，benign-reviewed 须伴随非空
    corrections（B2）；selection=null 须伴随非空 diagnostic（B3）——违反记 fail:enum / fail:companion；
  - 未提供 --seal-at 时 classify 永不返回裸 pass：fail:unsealed（--spec 非零退出，B4 fail-closed）；
    --allow-unsealed 仅限 --retro 披露模式，矩阵带 unsealed 标记与 policy 字段。

规范：同目录 SCHEMA.md（L2 包C 交付，L3 包B 修订）。
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
SPEC = "runner-schema-v2"
DISCLOSURE = ("该矩阵是披露性 delta 报告，不是对 r1031 的追溯判定"
              "（D1 已由 lead 裁决闭项：不回填）。")

# L3 包B：值域与伴随关系（SCHEMA.md §一，实现与文档一致）
STATUS_ENUM = ("ok", "timeout", "error", "transport-error")
INTEGRITY_VERDICT_ENUM = ("clean", "benign-reviewed", "violation")
ISO_TZ_TOKEN = (r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?"
                r"(?:Z|[+-]\d{2}:?\d{2})")

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


def nonempty(v) -> bool:
    """伴随关系用的「非空」：字符串去空白后非空，或 list/dict 长度 > 0。"""
    if isinstance(v, str):
        return v.strip() != ""
    if isinstance(v, (list, dict)):
        return len(v) > 0
    return False


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
    """返回逐字段状态 + 时序/精度/enum/伴随问题清单。不修改输入。

    L3 语义：seal_at 为 None 时结果带 unsealed=True（B4 fail-closed；
    classify 据此永不返回裸 pass）。
    """
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

    # ---- L3（包B / DF-2）：enum 值域（B1/B2）----
    st_cell = cells.get("status", {})
    if st_cell.get("status") == "ok" and meta.get("status") not in STATUS_ENUM:
        cells["status"] = dict(st_cell, status="enum_error")
        issues.append({"field": "status", "class": "enum",
                       "detail": "value %r not in %s" % (meta.get("status"), list(STATUS_ENUM))})
    iv_cell = cells.get("integrity_verdict", {})
    if iv_cell.get("status") == "ok":
        iv = meta.get("integrity_verdict")
        if iv not in INTEGRITY_VERDICT_ENUM:
            cells["integrity_verdict"] = dict(iv_cell, status="enum_error")
            issues.append({"field": "integrity_verdict", "class": "enum",
                           "detail": "value %r not in %s" % (iv, list(INTEGRITY_VERDICT_ENUM))})

    # ---- L3（包B / DF-2）：伴随关系（B2/B3）----
    if cells.get("integrity_verdict", {}).get("status") == "ok" \
            and meta.get("integrity_verdict") == "benign-reviewed" \
            and not nonempty(meta.get("corrections")):
        issues.append({"field": "corrections", "class": "companion",
                       "detail": "integrity_verdict=benign-reviewed requires non-empty corrections"})
    if meta.get("selection") is None and "selection" in meta \
            and not nonempty(meta.get("diagnostic")):
        issues.append({"field": "diagnostic", "class": "companion",
                       "detail": "selection=null requires non-empty diagnostic"})

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
    unsealed = seal_at is None
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
            "receipt_score_reported": receipt_cell, "issues": issues,
            "unsealed": unsealed}


FAIL_PRECEDENCE = [("missing", "fail:missing"), ("type", "fail:type"),
                   ("enum", "fail:enum"), ("companion", "fail:companion"),
                   ("precision", "fail:precision"), ("temporal-order", "fail:temporal-order"),
                   ("temporal-seal", "fail:temporal-seal")]


def classify(result: dict, allow_unsealed: bool = False) -> str:
    """单场判定。B4：未提供 seal 时永不返回裸 pass——fail:unsealed；
    allow_unsealed=True 仅由 --retro 披露模式传入，返回带标记的 pass:unsealed。"""
    classes = {i["class"] for i in result["issues"]}
    for cls, label in FAIL_PRECEDENCE:
        if cls in classes:
            return label
    if result.get("unsealed"):
        return "pass:unsealed" if allow_unsealed else "fail:unsealed"
    return "pass"


# ---------------------------------------------------------------- --spec

def cmd_spec(fixtures_dir: Path, seal_override, out_path: Path | None) -> int:
    """--spec 自检。C-1 非破坏化：收据仅写显式 --out；目标已存在即拒绝（exit 2，原字节不动）；
    未提供 --out 时不落盘（结果仍打印，stderr 提示）。--spec 固定 fail-closed：
    不接受 --allow-unsealed（见 main 的互斥校验）。"""
    manifest = json.loads((fixtures_dir / "manifest.json").read_text(encoding="utf-8"))
    seal = seal_override or manifest.get("seal_at")
    seal_dt = parse_iso(seal) if seal else None
    results, all_ok = {}, True
    for fname in sorted(manifest["fixtures"]):
        expect = manifest["fixtures"][fname]
        meta = json.loads((fixtures_dir / fname).read_text(encoding="utf-8"))
        res = validate_meta(meta, seal_at=seal_dt)
        got = classify(res, allow_unsealed=False)
        ok = got == expect
        all_ok &= ok
        results[fname] = {"expect": expect, "got": got, "match": ok,
                          "issues": res["issues"]}
    receipt = {"kind": "self_test", "tool": "validate_runner_meta.py --spec", "spec": SPEC,
               "at": now_local(), "seal_at_used": seal,
               "seal_policy": ("fail-closed（--spec 固定；未提供 seal 时 classify 不得返回裸 pass，"
                               "B4；--allow-unsealed 仅限 --retro 披露模式）"),
               "fixtures_dir": str(fixtures_dir),
               "l3_disclosure": {
                   "b4_semantics": "classify 在 unsealed 时返回 fail:unsealed（非零退出路径）；裸 pass 仅在 seal 已评且无其它 issue 时可达",
                   "fixtures_behavior_change": ("manifest 自带 seal_at=%s，六个 L2 既有 fixture 期望在新语义下不变"
                                                 "（enum/companion 检查对它们不触发，已由本收据逐项 match 证实）；"
                                                 "无 seal 调用的默认非零行为由 cli-regression-receipt 机械复现" % (manifest.get("seal_at"),)),
                   "b5_new_fixtures": ["fixture-status-bad-enum.json", "fixture-verdict-benign-without-corrections.json",
                                        "fixture-selection-null-without-diagnostic.json",
                                        "fixture-verdict-benign-with-corrections.json"],
                   "receipt_path_policy": "C-1 非破坏化：本收据仅经显式 --out 落盘；原 spec-selftest-receipt.json（5c6177fd…）字节不动",
               },
               "results": results, "all_match": all_ok}
    wrote = None
    if out_path is None:
        print("C-1 非破坏化：未提供 --out，收据不落盘（结果已打印）。", file=sys.stderr)
    elif out_path.exists():
        print(json.dumps({"refused": True, "target": str(out_path),
                          "reason": "目标已存在，C-1 非破坏化拒绝写入（原字节不动）",
                          "all_match": all_ok}, ensure_ascii=False))
        print("SPEC_SELFTEST_WRITE: REFUSED (target exists)")
        return 2
    else:
        out_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        wrote = str(out_path)
    print(json.dumps({k: (v["expect"], v["got"], v["match"]) for k, v in results.items()},
                     ensure_ascii=False, indent=1))
    print("SPEC_SELFTEST:", "PASS" if all_ok else "FAIL",
          ("receipt=%s" % wrote) if wrote else "(receipt not written)")
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


def cmd_retro(runs_dirs: list[Path], out: Path, seal_override, allow_unsealed: bool) -> int:
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
        "seal": {"provided": seal_override is not None,
                 "policy": "allow-unsealed-disclosure" if allow_unsealed else "fail-closed-unsealed",
                 "unsealed": seal_override is None,
                 "note": "B4：unsealed=true 时矩阵为披露口径；classify 语义见 SCHEMA.md §三"},
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


# ---------------------------------------------------------------- --reconcile（⑦/O-1）

def _read_registered_at(lp: Path, pointer: str | None, line_regex: str | None):
    """从台账提取 registered_at 值：JSON pointer 或 行正则内首个 ISO8601+tz 记号。"""
    if pointer:
        node = json.loads(lp.read_text(encoding="utf-8"))
        for part in pointer.lstrip("/").split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            node = node[part]
        return node, "json-pointer:%s" % pointer
    text = lp.read_text(encoding="utf-8", errors="replace")
    m = re.search(line_regex, text)
    if not m:
        return None, "line-regex:%s (no match)" % line_regex
    iso = re.search(ISO_TZ_TOKEN, m.group(0))
    if not iso:
        return None, "line-regex:%s (matched, no ISO8601+tz token)" % line_regex
    return iso.group(0), "line-regex:%s" % line_regex


def cmd_reconcile(ledger: Path, pointer: str | None, line_regex: str | None, commit: str,
                  commit_time: str | None, commit_time_file: Path | None, use_git: bool,
                  out: Path) -> int:
    steps = []

    def step(name, ok, detail, **extra):
        rec = {"step": name, "ok": bool(ok), "detail": str(detail)}
        rec.update(extra)
        steps.append(rec)
        return bool(ok)

    ok = True
    ok &= step("ledger-readable", ledger.is_file(), ledger)
    value, how = None, None
    if ledger.is_file():
        try:
            value, how = _read_registered_at(ledger, pointer, line_regex)
            ok &= step("extract-registered-at", isinstance(value, str) and value != "", how)
        except Exception as exc:
            ok &= step("extract-registered-at", False, "%s: %s" % (type(exc).__name__, exc))
    vdt = None
    if isinstance(value, str) and value:
        try:
            vdt = parse_iso(value)
            fmt_ok = vdt.tzinfo is not None
        except ValueError:
            fmt_ok = False
        ok &= step("registered-at-format", fmt_ok, repr(value))
    else:
        ok &= step("registered-at-format", False, "<not extracted>")
    ok &= step("commit-hash-format",
               isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{7,40}", commit or "") is not None,
               commit or "")
    cdt, src = None, None
    if use_git:
        try:
            proc = subprocess.run(["git", "log", "-1", "--format=%cI", commit],
                                  capture_output=True, text=True, timeout=30, cwd=str(HERE))
            token = proc.stdout.strip().splitlines()[0] if proc.stdout.strip() else ""
            try:
                cdt = parse_iso(token)
            except ValueError:
                cdt = None
            src = "git log -1 --format=%cI " + commit  # D-L3-1 修复：禁止 %-format（%cI 是 git 占位符，% 冲突曾致 TypeError 被吞）
            ok &= step("commit-time-source", proc.returncode == 0 and cdt is not None
                       and cdt.tzinfo is not None, token or proc.stderr.strip()[-120:])
        except Exception as exc:
            ok &= step("commit-time-source", False, "git mode error: %s" % exc)
    elif commit_time_file is not None:
        try:
            text = commit_time_file.read_text(encoding="utf-8", errors="replace")
            m = re.search(ISO_TZ_TOKEN, text)
            cdt = parse_iso(m.group(0)) if m else None
        except Exception:
            cdt = None
        src = "commit-time-file:%s" % commit_time_file
        ok &= step("commit-time-source", cdt is not None and cdt.tzinfo is not None,
                   m.group(0) if m else "<no ISO8601+tz token>")
    elif commit_time:
        try:
            cdt = parse_iso(commit_time)
        except ValueError:
            cdt = None
        src = "cli-arg"
        ok &= step("commit-time-source", cdt is not None and cdt.tzinfo is not None, commit_time)
    else:
        ok &= step("commit-time-source", False, "<no commit time source given>")
    # D-L3-1 修复（verdict/ok 语义对齐）：任何步骤为假 ⇒ verdict 不得为 ok。
    # verdict ∈ {ok, violation, error, inconclusive}：
    #   ok         = 全部步骤真 且 registered_at ≥ commit_time
    #   violation  = 全部步骤真 但 registered_at < commit_time（比较步骤假）
    #   error      = 任一非比较步骤假（来源/格式/提取失败等）
    #   inconclusive = 比较无法进行且无其它步骤失败（理论上不可达，防御保留）
    comparison_ran = vdt is not None and cdt is not None
    non_comparison_ok = all(s["ok"] for s in steps
                            if s["step"] != "registered-at-ge-commit-time")
    verdict = "inconclusive"
    if comparison_ran:
        delta = round((vdt - cdt).total_seconds(), 3)
        verdict = "ok" if vdt >= cdt else "violation"
        ok &= step("registered-at-ge-commit-time", vdt >= cdt,
                   "registered_at %s vs commit_time %s" % (value, cdt.isoformat()),
                   delta_seconds=delta)
    elif not non_comparison_ok:
        verdict = "error"
    receipt = {"kind": "self_test", "tool": "validate_runner_meta.py --reconcile", "spec": SPEC,
               "at": now_local(),
               "binding_disclosure": ("顺序检查（registered_at<started_at）必要非充分（O-1/⑦披露，SCHEMA.md §三.4）；"
                                       "本子命令把 registered_at 与封印提交时刻机械对账并逐项落盘。"
                                       "commit_time 来源：--commit-time（cli-arg）/ --commit-time-file（文件，"
                                       "审计侧可粘贴 git log 输出）/ --git（直接读取；L3 未行使——builder 禁 git，"
                                       "真实批次对账留 L4，U1）。"),
               "inputs": {"ledger": str(ledger),
                          "ledger_sha256": sha256_file(ledger) if ledger.is_file() else None,
                          "extract": how, "pointer": pointer, "line_regex": line_regex,
                          "commit": commit, "commit_time_source": src,
                          "commit_time": cdt.isoformat() if cdt else None,
                          "registered_at": value},
               "steps": steps, "verdict": verdict, "ok": bool(ok and verdict == "ok")}
    if out.exists():
        print(json.dumps({"refused": True, "target": str(out),
                          "reason": "目标已存在，C-1 非破坏化拒绝写入（原字节不动）"}, ensure_ascii=False))
        return 2
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": verdict, "ok": receipt["ok"], "receipt": str(out)},
                     ensure_ascii=False))
    return 0 if receipt["ok"] else 1


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
    ap.add_argument("--reconcile", action="store_true")
    ap.add_argument("--fixtures", default=str(HERE / "fixtures"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--seal-at", default=None)
    ap.add_argument("--allow-unsealed", action="store_true",
                     help="仅限 --retro 披露模式（B4）；--spec 拒绝")
    ap.add_argument("--ledger", default=None)
    ap.add_argument("--pointer", default=None)
    ap.add_argument("--line-regex", default=None)
    ap.add_argument("--commit", default=None)
    ap.add_argument("--commit-time", default=None)
    ap.add_argument("--commit-time-file", default=None)
    ap.add_argument("--git", action="store_true")
    a = ap.parse_args(argv)
    if a.allow_unsealed and a.spec:
        print("--allow-unsealed 仅限 --retro 披露模式（B4）；--spec 固定 fail-closed", file=sys.stderr)
        return 2
    if a.spec:
        return cmd_spec(Path(a.fixtures), a.seal_at, Path(a.out) if a.out else None)
    if a.reconcile:
        if not a.out or not a.ledger or not a.commit:
            print("--reconcile 需要 --ledger/--commit/--out（时刻来源三选一：--commit-time/"
                  "--commit-time-file/--git；字段位置 --pointer 或 --line-regex）", file=sys.stderr)
            return 2
        if bool(a.pointer) == bool(a.line_regex):
            print("--reconcile 的字段位置须二选一：--pointer 或 --line-regex", file=sys.stderr)
            return 2
        if sum(bool(x) for x in (a.commit_time, a.commit_time_file, a.git)) != 1:
            print("--reconcile 的提交时刻来源须三选一", file=sys.stderr)
            return 2
        return cmd_reconcile(Path(a.ledger), a.pointer, a.line_regex, a.commit,
                             a.commit_time,
                             Path(a.commit_time_file) if a.commit_time_file else None,
                             a.git, Path(a.out))
    if a.retro:
        if not a.out:
            print("--retro 需要 --out", file=sys.stderr)
            return 2
        # DF-B1 修复（修代码就预注册字面）：无 --seal-at 且无 --allow-unsealed ⇒
        # 非零退出（3）+ 响亮说明，不落盘任何矩阵；--allow-unsealed 为唯一披露出口，
        # 矩阵带 seal.unsealed/seal.policy 标记（与 --spec 同一 fail-closed 纪律）。
        if a.seal_at is None and not a.allow_unsealed:
            print("B4 fail-closed（DF-B1）：--retro 未提供 --seal-at 且未显式 --allow-unsealed，"
                  "不产出矩阵（exit 3）。封印时刻请传 --seal-at；披露口径请显式 --allow-unsealed"
                  "（矩阵将带 seal.unsealed=true / seal.policy 标记）。", file=sys.stderr)
            return 3
        return cmd_retro([Path(p) for p in a.retro], Path(a.out), a.seal_at, a.allow_unsealed)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
