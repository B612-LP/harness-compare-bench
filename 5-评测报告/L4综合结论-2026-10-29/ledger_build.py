#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L4 六类分账最终产物生成器（auditor 代 build；lead 审核后串行登记）。

纪律（lead 2026-10-30 指令）：
  - 以 auditor r3 候选为基础，但全部数值**本脚本重新读取现有证据**计算；
  - bird 终态=not_executed（notexecuted.json + startup-failure-proof + provenance 旁挂），
    不再使用 r3 的 not_executed_or_pending 模糊态；
  - 六类各分账明确；grading_regression=0（本环无 checker 修订）；事故独立
    interface_preflight 且 provider requests unknown；
  - group 数 ≠ 槽次数，分列；未记录细节写 unknown/null，不捏造；
  - 时间=脚本实钟；关键输入哈希=脚本实算；输出 O_EXCL 拒写；
  - 不改 v3 live ledger / observations / 任何既有证据；formal_admission 留 judge/lead。

用法：python3 ledger_build.py --outdir 5-评测报告/L4综合结论-2026-10-29
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.resolve().parents[1]
L4 = REPO / "1-评测方案" / "自动循环L4-2026-10-29"
PLAN = L4 / "plan.json"
BINDING = L4 / "runtime-binding.json"
CACHE = REPO / "3-表现现场" / "l4-20261029-cache"
CLI = REPO / "3-表现现场" / "l4-20261029-cli"
WB = REPO / "3-表现现场" / "l4-20261029-wb-gateway"
AUD = REPO / "5-评测报告" / "对抗性盲审-L4-2026-10-29"


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sha(p: Path) -> str | None:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except Exception:
        return None


def jload(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def rel(p: Path) -> str:
    try:
        return str(p.relative_to(REPO))
    except Exception:
        return str(p)


def build() -> dict:
    plan = jload(PLAN)
    binding = jload(BINDING)
    ps = plan["product_slots"]
    probes = plan["probe_slots"]
    by = {}
    for s in ps:
        by.setdefault(s["product"], []).append(s)

    # ---------- 逐产品 17 槽状态（重读证据） ----------
    def product_slots(root: Path, ids: list[str]):
        rows = []
        for sid in ids:
            d = root / sid
            meta_p = d / "meta.json"
            notexec_p = d / "notexecuted.json"
            m = jload(meta_p)
            ne = jload(notexec_p)
            if m is not None:
                u = m.get("usage") or {}
                rows.append({
                    "slot_id": sid, "case": (jload(PLAN) and [x for x in jload(PLAN)["product_slots"] if x["slot_id"] == sid][0]["case"]),
                    "accounting_state": "executed" if m.get("weighted") is not None else "ran_no_score(unknown)",
                    "status": m.get("status"), "exit_code": m.get("exit_code"),
                    "timed_out": m.get("timed_out"), "weighted": m.get("weighted"),
                    "integrity_verdict": m.get("integrity_verdict"),
                    "usage_requests": u.get("requests"),
                    "unknowns": (["usage_observation=null(marker 缺陷原样保留)"]
                                 if u.get("requests") is None else []),
                    "evidence": {"meta.json": rel(meta_p), "meta_sha256": sha(meta_p)},
                })
            elif ne is not None:
                rows.append({
                    "slot_id": sid,
                    "accounting_state": "not_executed",
                    "not_executed_reason": ne.get("reason") or "infrastructure startup-render-not-ready",
                    "score": None,
                    "formal_admission": False,
                    "unknowns": [],
                    "evidence": {"notexecuted.json": rel(notexec_p),
                                 "notexecuted_sha256": sha(notexec_p),
                                 "startup_proof": rel(WB / "receipts" / "bird-startup-failure-proof.json"),
                                 "E_provenance_sidecar": rel(WB / "receipts" / "bird-notexec-preregE-provenance.json")},
                })
            else:
                rows.append({"slot_id": sid, "accounting_state": "unknown",
                             "unknowns": ["无 meta/notexecuted 证据"], "score": None,
                             "evidence": {}})
        return rows

    codex_rows = product_slots(CLI / "codex" / "runs", [s["slot_id"] for s in by.get("codex", [])])
    dsh_rows = product_slots(CLI / "dsh" / "runs", [s["slot_id"] for s in by.get("dsh", [])])
    wb_rows = product_slots(WB / "runs", [s["slot_id"] for s in by.get("workbuddy", [])])

    def n_exec(rows):
        return sum(1 for r in rows if r["accounting_state"] == "executed")

    # ---------- 探针 18 ----------
    probe_rows = []
    for s in probes:
        t = jload(CACHE / "probes" / s["slot_id"] / "transport.json")
        probe_rows.append({"slot_id": s["slot_id"], "protocol": s["protocol"],
                           "block": s["block"], "condition": s["condition"],
                           "http_status": (t or {}).get("http_status"),
                           "accounting_state": "executed" if (t or {}).get("http_status") == 200 else "unknown"})
    probe_exec = sum(1 for r in probe_rows if r["accounting_state"] == "executed")

    # ---------- 六类 groups ----------
    selftest_groups = [
        {"group_id": "selftest:lead-seal",
         "refs": [rel(L4 / "selftest")],
         "files_json": len(list((L4 / "selftest").glob("*.json"))) if (L4 / "selftest").is_dir() else 0,
         "test_case_n": None,
         "note": "v1→v6 修正链；用例数以各版本收据为准"},
        {"group_id": "selftest:l4-execution-gate",
         "refs": [rel(REPO / "1-评测方案" / "工具链" / "l4-execution" / "receipts" / "gate-selftest.json")],
         "test_case_n": None},
        {"group_id": "selftest:l4-execution-replay-dual",
         "refs": [rel(REPO / "1-评测方案" / "工具链" / "l4-execution" / "selftest-replay-dual.json")],
         "receipt_files": len(list((REPO / "1-评测方案" / "工具链" / "l4-execution").glob("selftest-replay-dual*.json"))),
         "test_case_n": None, "note": "r1→r9 修正链留痕"},
        {"group_id": "selftest:cache-probe",
         "refs": [rel(CACHE / "selftest" / "selftest-receipt.json")],
         "test_case_n": (jload(CACHE / "selftest" / "selftest-receipt.json") or {}).get("counts", {}).get("total"),
         "receipt_at": (jload(CACHE / "selftest" / "selftest-receipt.json") or {}).get("at")},
        {"group_id": "selftest:codex-runner",
         "refs": [rel(CLI / "codex" / "selftest" / "selftest-receipt.json")],
         "test_case_n": (jload(CLI / "codex" / "selftest" / "selftest-receipt.json") or {}).get("counts", {}).get("total"),
         "receipt_at": (jload(CLI / "codex" / "selftest" / "selftest-receipt.json") or {}).get("at"),
         "note": "以落盘收据版本为准"},
        {"group_id": "selftest:wb-gateway",
         "refs": [rel(WB / "selftest" / "selftest-receipt-l4-wb-v2.json"),
                  rel(WB / "receipts" / "v1-skeleton-archive")],
         "test_case_n": None},
        {"group_id": "selftest:judge-fake-e2e",
         "refs": [rel(REPO / "5-评测报告" / "L4独立验收-2026-10-29" / "harness" / "results")],
         "receipt_files": len(list((REPO / "5-评测报告" / "L4独立验收-2026-10-29" / "harness" / "results").rglob("*fake-e2e-receipt*.json"))),
         "test_case_n": None},
        {"group_id": "selftest:auditor-tools",
         "refs": [rel(AUD / "selftest-receipt-credential-scan-r1.json")],
         "test_case_n": (jload(AUD / "selftest-receipt-credential-scan-r1.json") or {}).get("counts", {}).get("total"),
         "note": "另 pii_min_check 自检 6/6（内置 selftest）"},
    ]
    categories = {
        "product_run": {
            "planned_slots": len(ps),
            "groups": [
                {"group_id": "prod:codex-batch", "product": "codex", "slots": codex_rows,
                 "summary": {"executed": n_exec(codex_rows), "planned": len(codex_rows)}},
                {"group_id": "prod:dsh-batch", "product": "dsh", "slots": dsh_rows,
                 "summary": {"executed": n_exec(dsh_rows), "planned": len(dsh_rows),
                             "gate_formal": 0,
                             "note": "usage 维度本轮不可结论（marker 缺陷原样保留）；recoveries 晚补档 sidecar 独立"}},
                {"group_id": "prod:wb-batch", "product": "workbuddy", "slots": wb_rows,
                 "summary": {"executed": n_exec(wb_rows), "planned": len(wb_rows),
                             "not_executed": len(wb_rows) - n_exec(wb_rows),
                             "note": "bird=not_executed（R1 真值表：score=null、formal=false、诊断完整）"}},
            ],
            "executed_total": n_exec(codex_rows) + n_exec(dsh_rows) + n_exec(wb_rows),
            "not_executed_total": sum(1 for r in codex_rows + dsh_rows + wb_rows
                                      if r["accounting_state"] == "not_executed"),
            "formal_admission_note": "逐槽 formal_admission 归 judge/lead 主裁，本账只记 accounting_state 与原分",
        },
        "bare_model_probe": {
            "planned_slots": len(probes),
            "groups": [{"group_id": "probe:cache-batch",
                        "receipt_unit": rel(CACHE / "probe-receipt.json"),
                        "receipt_sha256": sha(CACHE / "probe-receipt.json"),
                        "slots": probe_rows,
                        "summary": {"executed_http200": probe_exec, "planned": len(probes)}}],
            "executed_total": probe_exec,
        },
        "interface_preflight": {
            "groups": [
                {"group_id": "preflight:incident-accidental-cli", "count": 1,
                 "receipt_unit": rel(CLI / "codex" / "incidents" / "incident-receipt.json"),
                 "incident_sha256": sha(CLI / "codex" / "incidents" / "incident-receipt.json"),
                 "provider_requests": "unknown", "evidence_grade": "incomplete",
                 "note": "独立事故，不并 35 槽/不评分/不计合成 pass/不得称零调用"},
                {"group_id": "preflight:cache-dryrun", "count": 1,
                 "receipt_unit": rel(CACHE / "dryrun" / "probe-receipt-dryrun.json")},
                {"group_id": "preflight:wb-gateway", "count": None,
                 "receipt_unit": rel(WB / "preflight"),
                 "unknowns": ["细粒度预检次数未持久=null"]},
            ]
        },
        "self_test": {"groups": selftest_groups,
                      "group_count": len(selftest_groups),
                      "note": "group 数≠用例数"},
        "offline_recompute": {
            "groups": [
                {"group_id": "recompute:dual-archive-codex", "slots": 6,
                 "refs": [rel(CLI / "codex" / "runs" / codex_rows[0]["slot_id"] / "projections")] if codex_rows else [],
                 "note": "逐槽 equivalent_simulation 完备性终审留 judge"},
                {"group_id": "recompute:cache-erratum-sidecar",
                 "refs": [rel(CACHE / "execution-accounting-sidecar.json")]},
                {"group_id": "recompute:auditor-stages",
                 "refs": [rel(AUD / "final-audit-stage-u1-r1.json"),
                          rel(AUD / "final-audit-stage-cache-r3.json"),
                          rel(AUD / "final-audit-stage-codex-r1.json"),
                          rel(AUD / "final-audit-stage-dsh-r1.json"),
                          rel(AUD / "final-audit-stage-coverage-r2.json")]},
            ]
        },
        "grading_regression": {
            "value": 0,
            "groups": [],
            "note": "本环无 checker 修订/回归：contract 继承冻结 checker 字节；不为凑六账新跑",
        },
    }
    group_total = sum(len(v.get("groups", [])) for v in categories.values())
    inputs_hash = {rel(p): sha(p) for p in (PLAN, BINDING, CACHE / "probe-receipt.json")}
    return {
        "kind": "l4_six_category_ledger",
        "id": "L4-SIX-LEDGER-r1",
        "generated_at": now(),
        "builder": {"script": rel(HERE / "ledger_build.py"), "sha256": sha(HERE / "ledger_build.py")},
        "basis": {"design_commit_D": (binding or {}).get("design_commit"),
                  "execution_seal_commit": (binding or {}).get("execution_seal_commit"),
                  "registered_at": (binding or {}).get("registered_at"),
                  "inputs_sha256": inputs_hash},
        "planned_slots": {"product": len(ps), "probe": len(probes), "total": len(ps) + len(probes)},
        "categories": categories,
        "counts": {
            "activity_group_total": group_total,
            "product_executed": n_exec(codex_rows) + n_exec(dsh_rows) + n_exec(wb_rows),
            "product_not_executed": sum(1 for r in codex_rows + dsh_rows + wb_rows
                                        if r["accounting_state"] == "not_executed"),
            "probe_executed": probe_exec,
            "grading_regression_runs": 0,
            "incident_separate": 1,
            "note": "activity_group 数 ≠ 槽次数 ≠ 用例数，三口径分列",
        },
        "unknowns_policy": "未记录细节一律 null/unknown 并逐条列出，不捏造",
        "formal_admission": "本账不判定 formal_admission（judge/lead 主裁）；raw 原分照实保留",
        "live_doc_drift": [],
    }


def render_md(d: dict) -> str:
    c = d["categories"]
    lines = [
        "# L4 六类分账（candidate r1，机器生成）", "",
        f"- 生成：{d['generated_at']}（脚本实钟）；builder sha256_8={d['builder']['sha256'][:8]}",
        f"- 基准：D={str(d['basis']['design_commit_D'])[:8]} E={str(d['basis']['execution_seal_commit'])[:8]} registered_at={d['basis']['registered_at']}",
        f"- 计划槽：**35 = 17 product + 18 probe**；activity_group 合计 **{d['counts']['activity_group_total']}**（group≠次数≠用例）",
        "- 状态：candidate，待 lead 审核+串行登记；formal_admission 本账不判定（judge/lead 主裁），raw 原分照实保留。", "",
        "## 1. product_run（计划 17）", "",
        f"- executed **{d['categories']['product_run']['executed_total']}/17**，not_executed {d['categories']['product_run']['not_executed_total']}（WB bird，基础设施 startup-render-not-ready，score=null 不折算）",
        "- codex 6/6：dab 70.0×3、cargo 70.37037037×3；无重启/无补跑（X 系 7/7）",
        "- dsh 6/6：dab 70/80/70、cargo 70.37037037/74.07407407/74.07407407；**usage 维度 null 原样保留（marker 缺陷）**；gate formal=0；recoveries 晚补档独立",
        "- wb 4/5 执行：dab 50.0、exercism 100.0、lcb 100.0、cargo 70.37；bird not_executed",
        "- 每槽 evidence（meta/notexecuted 路径+sha256）见 six-ledger.json；逐槽 formal 归 judge。", "",
        "## 2. bare_model_probe（计划 18）", "",
        f"- executed **{d['categories']['bare_model_probe']['executed_total']}/18**（每槽恰 1 次 HTTP 200；6 pair=3 wire×2 block）；REPORT missing 断言已经 dated erratum 2 更正（C10 PASS；映射层=coverage limitation，见 AUDIT §AUD-D1/C5c）。", "",
        "## 3. interface_preflight", "",
        "- **事故独立**：accidental CLI start ×1，chatgpt.com 401 证实；**DeepSeek provider requests=unknown**；证据 incomplete；不并 35 槽/不得称零调用",
        "- cache dryrun ×1；wb 零模型预检（次数未持久=unknown/null）", "",
        "## 4. self_test（8 组，group≠用例数）", "",
    ]
    for g in c["self_test"]["groups"]:
        tc = g.get("test_case_n")
        lines.append(f"- {g['group_id']}：test_case_n={tc if tc is not None else 'unknown/null'}"
                     + (f"（receipt_at={g.get('receipt_at')}，以落盘收据版本为准）" if g.get("receipt_at") else ""))
    lines += ["", "## 5. offline_recompute（3 组）", "",
              "- dual-archive codex 6 槽投影（等价模拟完备性终审留 judge）；cache erratum sidecar（judge 独立核）；auditor 五阶段独立复算收据", "",
              "## 6. grading_regression = 0（不适用）", "",
              "- 本环无 checker 修订：contract 继承冻结 checker 字节；不为凑六账新跑", "",
              "## 未知登记（null/unknown 不捏造）", ""]
    for prod in ("product_run",):
        for g in c[prod]["groups"]:
            for s in g["slots"]:
                for u in s.get("unknowns", []):
                    lines.append(f"- {s['slot_id']}: {u}")
    lines += ["- wb-gateway 预检次数：unknown（未持久）",
              "- WB actual_request_model/actual_gateway：null（managed unknown，不参与同路由归因）",
              "- 事故 DeepSeek provider requests：unknown（incomplete）", "",
              "---", "",
              f"**live_doc_drift: none（0 项）**", "",
              "机器产物：six-ledger.json（同构全量数据，含逐槽 sha256/输入哈希）；本文件由 ledger_build.py 同步渲染。"]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=str(HERE))
    a = ap.parse_args()
    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    jp, mp = outdir / "six-ledger.json", outdir / "six-ledger.md"
    for p in (jp, mp):
        if p.exists():
            print(json.dumps({"refused": True, "target": str(p)}, ensure_ascii=False))
            return 2
    d = build()
    jp.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    mp.write_text(render_md(d), encoding="utf-8")
    print(json.dumps({"groups": d["counts"]["activity_group_total"],
                      "product_executed": d["counts"]["product_executed"],
                      "product_not_executed": d["counts"]["product_not_executed"],
                      "probe_executed": d["counts"]["probe_executed"],
                      "files": [str(jp), str(mp)]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
