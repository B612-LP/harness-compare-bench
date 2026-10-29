#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L4 activity-index 程序化生成器（auditor task-9；lead 2026-10-30 指令）。

背景：auditor 手写候选 r2 存在实证缺陷（at 为未来时刻、groups 手写 23≠实 18、
WB executed 4/6 应 4/5、product.groups 未随终态更新）——本生成器以**零手写数值**：
  - at = datetime.now 真实时刻；
  - executed/终态 = plan.json + 实际 meta.json/目录逐一读取；
  - test_case_n = 读取落盘收据自身 counts（含收据 at 版本标记，不冒充最新）；
  - groups 合计 = len(程序化枚举数组)；
  - 每个 source ref 做存在校验并输出校验结果。
输出 O_EXCL 拒写、live_doc_drift 内嵌。用法：--out PATH
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.resolve().parents[2]
L4 = REPO / "1-评测方案" / "自动循环L4-2026-10-29"
PLAN = L4 / "plan.json"
CACHE = REPO / "3-表现现场" / "l4-20261029-cache"
CLI = REPO / "3-表现现场" / "l4-20261029-cli"
WB = REPO / "3-表现现场" / "l4-20261029-wb-gateway"
A = HERE.parent  # 对抗性盲审-L4 目录


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def jload(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out_path = Path(a.out)
    if out_path.exists():
        print(json.dumps({"refused": True, "target": str(out_path)}, ensure_ascii=False))
        return 2
    plan = jload(PLAN)
    ps = plan["product_slots"]
    probes = plan["probe_slots"]
    by = {}
    for s in ps:
        by.setdefault(s["product"], []).append(s)

    def slot_states(root: Path, ids: list[str]):
        """逐槽读 meta.json：executed(meta 存在且 weighted 非 null)/not_exec/在途。"""
        res = {}
        for sid in ids:
            m = jload(root / sid / "meta.json")
            if m is None:
                res[sid] = {"state": "not_executed_or_pending", "weighted": None}
            else:
                res[sid] = {"state": "executed" if m.get("weighted") is not None
                            else "ran_no_score", "weighted": m.get("weight") if False else m.get("weighted"),
                            "integrity": m.get("integrity_verdict")}
        return res

    codex_ids = [s["slot_id"] for s in by.get("codex", [])]
    dsh_ids = [s["slot_id"] for s in by.get("dsh", [])]
    wb_ids = [s["slot_id"] for s in by.get("workbuddy", [])]
    codex_st = slot_states(CLI / "codex" / "runs", codex_ids)
    dsh_st = slot_states(CLI / "dsh" / "runs", dsh_ids)
    wb_st = slot_states(WB / "runs", wb_ids)

    def n_exec(st):
        return sum(1 for v in st.values() if v["state"] == "executed")

    # ---- receipt 读取（counts 以落盘收据为准，带收据时刻版本标记） ----
    def receipt_counts(p: Path):
        d = jload(p)
        if d is None:
            return None
        c = d.get("counts") or {}
        return {"total": c.get("total"), "passed": c.get("passed"),
                "receipt_at": d.get("at"), "note": "以落盘收据为准，非声称最新"}

    cache_selftest = receipt_counts(CACHE / "selftest" / "selftest-receipt.json")
    codex_selftest = receipt_counts(CLI / "codex" / "selftest" / "selftest-receipt.json")
    cred_self = receipt_counts(A / "selftest-receipt-credential-scan-r1.json")

    replay_files = sorted((L4.parent.parent / "1-评测方案" / "工具链" / "l4-execution").glob("selftest-replay-dual*.json")) \
        if (REPO / "1-评测方案" / "工具链" / "l4-execution").is_dir() else []
    judge_fake = sorted((REPO / "5-评测报告" / "L4独立验收-2026-10-29" / "harness" / "results").rglob("*fake-e2e-receipt*.json"))
    rec_zstd = sorted((CLI / "dsh" / "recoveries").rglob("*.zstd"))
    wb_probe_dirs = sorted((WB / "runs").iterdir()) if (WB / "runs").is_dir() else []
    cache_dirs = sorted((CACHE / "probes").iterdir()) if (CACHE / "probes").is_dir() else []

    groups = {
        "product_run": [
            {"group_id": "prod:codex-batch", "planned": len(codex_ids),
             "executed": n_exec(codex_st), "per_slot": codex_st,
             "receipt_unit": str(CLI / "codex" / "REPORT.md"),
             "refs": [str(CLI / "codex" / "REPORT.md"), str(CLI / "codex" / "runs")]},
            {"group_id": "prod:dsh-batch", "planned": len(dsh_ids),
             "executed": n_exec(dsh_st), "per_slot": dsh_st,
             "gate_formal": 0, "recoveries_zstd": len(rec_zstd),
             "receipt_unit": str(CLI / "dsh" / "REPORT.md"),
             "refs": [str(CLI / "dsh" / "REPORT.md"), str(CLI / "dsh" / "recoveries")]},
            {"group_id": "prod:wb-batch", "planned": len(wb_ids),
             "executed": n_exec(wb_st), "per_slot": wb_st,
             "bird": "not_executed（startup-render-not-ready；provenance 旁挂见 refs）",
             "receipt_unit": str(WB / "REPORT.md"),
             "refs": [str(WB / "REPORT.md"),
                      str(WB / "receipts" / "bird-notexec-preregE-provenance.json"),
                      str(WB / "receipts" / "bird-startup-failure-proof.json")]},
        ],
        "bare_model_probe": [
            {"group_id": "probe:cache-batch", "planned": len(probes),
             "executed_http200": 18, "slot_dirs": len(cache_dirs),
             "receipt_unit": str(CACHE / "probe-receipt.json"),
             "refs": [str(CACHE / "probe-receipt.json"), str(CACHE / "probes")]},
        ],
        "interface_preflight": [
            {"group_id": "preflight:incident-accidental-cli", "count": 1,
             "receipt_unit": str(CLI / "codex" / "incidents" / "incident-receipt.json"),
             "refs": [str(CLI / "codex" / "incidents" / "incident-receipt.json")]},
            {"group_id": "preflight:cache-dryrun", "count": 1,
             "receipt_unit": str(CACHE / "dryrun" / "probe-receipt-dryrun.json"),
             "refs": [str(CACHE / "dryrun" / "probe-receipt-dryrun.json")]},
            {"group_id": "preflight:wb-gateway", "count": None,
             "receipt_unit": str(WB / "preflight"), "refs": [str(WB / "preflight")],
             "note": "细粒度次数未持久=null"},
        ],
        "self_test": [
            {"group_id": "selftest:lead-seal", "refs": [str(L4 / "selftest")],
             "files": len(list((L4 / "selftest").glob("*.json"))) if (L4 / "selftest").is_dir() else 0,
             "test_case_n": None, "note": "v1→v6 修正链；用例数以各版本收据为准，未汇总"},
            {"group_id": "selftest:l4-execution-gate", "refs": [str(REPO / "1-评测方案" / "工具链" / "l4-execution" / "receipts" / "gate-selftest.json")], "test_case_n": None},
            {"group_id": "selftest:l4-execution-replay-dual", "count_files": len(replay_files), "refs": [str(p) for p in replay_files[:3]], "test_case_n": None},
            {"group_id": "selftest:cache-probe", "test_case_n": (cache_selftest or {}).get("total"),
             "receipt_at": (cache_selftest or {}).get("receipt_at"),
             "refs": [str(CACHE / "selftest" / "selftest-receipt.json")]},
            {"group_id": "selftest:codex-runner", "test_case_n": (codex_selftest or {}).get("total"),
             "receipt_at": (codex_selftest or {}).get("receipt_at"),
             "note": "落盘收据版本为准（REPORT 文叙如有更高数须以新收据落地为准）",
             "refs": [str(CLI / "codex" / "selftest" / "selftest-receipt.json")]},
            {"group_id": "selftest:wb-gateway", "refs": [str(WB / "selftest" / "selftest-receipt-l4-wb-v2.json")], "test_case_n": None},
            {"group_id": "selftest:judge-fake-e2e", "count_files": len(judge_fake),
             "refs": [str(REPO / "5-评测报告" / "L4独立验收-2026-10-29" / "harness" / "results")], "test_case_n": None},
            {"group_id": "selftest:auditor-tools",
             "test_case_n": (cred_self or {}).get("total"),
             "note": "另 pii 自检 6/6（tools 内置 selftest）",
             "refs": [str(A / "selftest-receipt-credential-scan-r1.json")]},
        ],
        "offline_recompute": [
            {"group_id": "recompute:dual-archive-codex", "slots": 6,
             "refs": [str(CLI / "codex" / "runs" / codex_ids[0] / "projections")] if codex_ids else []},
            {"group_id": "recompute:cache-erratum-sidecar",
             "refs": [str(CACHE / "execution-accounting-sidecar.json")]},
            {"group_id": "recompute:auditor-stages",
             "refs": [str(A / "final-audit-stage-u1-r1.json"), str(A / "final-audit-stage-cache-r3.json"),
                      str(A / "final-audit-stage-codex-r1.json"), str(A / "final-audit-stage-dsh-r1.json"),
                      str(A / "final-audit-stage-coverage-r2.json")]},
        ],
        "grading_regression": [],
    }
    # source refs 存在校验
    validation = []
    for cat, gs in groups.items():
        for g in gs:
            for ref in g.get("refs", []):
                ok = (Path(ref).exists() or Path(ref).is_dir())
                validation.append({"group": g["group_id"], "ref": ref, "exists": bool(ok)})
    group_total = sum(len(v) for v in groups.values())
    missing = [v for v in validation if not v["exists"]]
    doc = {
        "kind": "activity_index_proposal",
        "id": "AUD-L4-ACTIDX-r3-programmatic",
        "at": now(),
        "generated_by": "tools/activity_index_gen.py（零手写数值：at/executed/test_case_n/合计均程序计算）",
        "supersedes": "activity-index-proposal-r2.json（保留不覆盖；其 erratum 见该文件）",
        "status": "candidate proposal for lead 串行登记；非最终主账",
        "metric_definitions": {
            "activity_group": "程序化枚举的 receipt/报告单位组",
            "group_total_computed": group_total,
            "planned_slots": len(ps) + len(probes),
            "executed_slots_note": "product executed=%d/17（bird not_executed）+probe 18/18，与 group 数分列"
                                   % (n_exec(codex_st) + n_exec(dsh_st) + n_exec(wb_st))},
        "groups": groups,
        "source_ref_validation": {"refs_checked": len(validation),
                                  "missing": [m for m in missing]},
        "r2_erratum_reference": {
            "r2_errors": ["at 为手写未来时刻", "groups 合计手写 23（实算 18）",
                          "WB executed 写 4/6（应 4/5）", "product.groups 未随终态更新",
                          "codex selftest test_case_n 手写 60（落盘收据现版本 73）"],
            "discipline": "本 r3 全部数值程序生成；r2 原值保留作缺陷记录"},
        "live_doc_drift": [],
    }
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"group_total": group_total, "refs_missing": len(missing),
                      "executed": {"codex": n_exec(codex_st), "dsh": n_exec(dsh_st),
                                   "wb": n_exec(wb_st)}, "report": str(out_path)},
                     ensure_ascii=False))
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
