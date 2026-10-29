#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L4 最终敌意审计机械检查（auditor task-9；阶段 I 骨架）。

三态语义（与 THREAT-MODEL.md §4 对应）：
  PASS      = 输入齐备且断言全过
  FAIL      = 输入齐备但断言失败（终审发现）
  PENDING-E = 所需输入尚未存在（E 未封/真实数据未回），如实列缺失项，不猜结论

阶段 I（当前）只有 F1/F2 可跑：plan/contract 槽位全集与绑定校验。
其余 stage 为显式 PENDING-E 骨架：定位输入路径、缺什么如实报，不伪造判定。

纪律：零模型、零网络；只读目标；--out 原子拒写；live_doc_drift 内嵌 list；
时间脚本生成；不读 truth/solution 内容（只允许对 case 快照做字节哈希比对）。
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.resolve().parents[2]
L4 = REPO / "1-评测方案" / "自动循环L4-2026-10-29"
PLAN = L4 / "plan.json"
CONTRACT = L4 / "contract.json"
CLI_ROOT = REPO / "3-表现现场" / "l4-20261029-cli"
CACHE_ROOT = REPO / "3-表现现场" / "l4-20261029-cache"
WB_ROOT = REPO / "3-表现现场" / "l4-20261029-wb-gateway"

FROZEN_TIMEOUT = {"dabstep-payments-10": 1800, "tb-cargo-plan": 2400}
PRODUCT_COUNTS = {"codex": 6, "dsh": 6, "workbuddy": 5}
PROBE_PROTOCOLS = {"responses", "anthropic-messages", "chat-completions"}
PROBE_CONDITIONS = {"fresh", "repeat", "nonce-control"}


def now_local() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check(name: str, ok: bool, detail="") -> dict:
    return {"check": name, "status": "PASS" if ok else "FAIL", "detail": str(detail)[:300]}


def pending(name: str, missing: list[str]) -> dict:
    return {"check": name, "status": "PENDING-E",
            "missing_inputs": missing[:20]}


def stage_plan() -> list[dict]:
    out: list[dict] = []
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    ps, pr = plan["product_slots"], plan["probe_slots"]
    # F1 槽位全集
    out.append(check("F1_product_total_17", len(ps) == 17, "actual=%d" % len(ps)))
    by_product: dict[str, int] = {}
    for s in ps:
        by_product[s["product"]] = by_product.get(s["product"], 0) + 1
    out.append(check("F1_product_counts", by_product == PRODUCT_COUNTS, json.dumps(by_product)))
    out.append(check("F1_probe_total_18", len(pr) == 18, "actual=%d" % len(pr)))
    ids = [s["slot_id"] for s in ps] + [s["slot_id"] for s in pr]
    rids = [s["run_id"] for s in ps] + [s["run_id"] for s in pr]
    eids = [s["event_id"] for s in ps if "event_id" in s] + \
           [s["event_id"] for s in pr if "event_id" in s]
    out.append(check("F1_identity_unique",
                     len(set(ids)) == len(ids) and len(set(rids)) == len(rids)
                     and len(set(eids)) == len(eids)))
    orders = [s["order"] for s in ps]
    out.append(check("F1_product_order_dense",
                     sorted(orders) == list(range(1, len(ps) + 1))))
    # CLI rep 结构：rep1 dab→cargo / rep2 cargo→dab / rep3 dab→cargo，两产品各 3 rep
    cli = [s for s in ps if s["product"] in ("codex", "dsh")]
    got = {(s["product"], s["rep"], s["case"]) for s in cli}
    expect = {(p, r, c) for p in ("codex", "dsh") for r, cs in
              ((1, ("dabstep-payments-10", "tb-cargo-plan")),
               (2, ("tb-cargo-plan", "dabstep-payments-10")),
               (3, ("dabstep-payments-10", "tb-cargo-plan"))) for c in cs}
    out.append(check("F1_cli_rep_structure", got == expect and len(cli) == 12,
                     json.dumps(sorted("%s" % (x,) for x in (got ^ expect)))))
    out.append(check("F1_timeouts_frozen",
                     all(s["timeout_s"] == FROZEN_TIMEOUT[s["case"]]
                         for s in cli if s["product"] in ("codex", "dsh"))))
    # F1 probe 结构：3 协议 × 2 block × fresh/repeat/nonce-control
    combos = {(s["protocol"], s["block"], s["condition"]) for s in pr}
    want = {(p, b, c) for p in PROBE_PROTOCOLS for b in (1, 2) for c in PROBE_CONDITIONS}
    out.append(check("F1_probe_grid_3x2x3", combos == want and len(pr) == 18))
    porders = [s["order"] for s in pr]
    out.append(check("F1_probe_order_dense", sorted(porders) == list(range(1, 19))))
    out.append(check("F1_probe_once_per_slot",
                     all(s.get("max_output_tokens") == 256 for s in pr)))
    out.append(check("F1_no_replacements_no_extra",
                     not plan.get("replacements") and not plan.get("result_driven_extra_samples"),
                     "replacements=%r extra=%r" % (plan.get("replacements"),
                                                   plan.get("result_driven_extra_samples"))))
    out.append(check("F1_whole_restarts_zero",
                     plan.get("whole_execution_restarts") in (None, 0, [], {}),
                     repr(plan.get("whole_execution_restarts"))))
    # F2 contract 绑定
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    out.append(check("F2_contract_plan_sha_matches_bytes",
                     contract.get("plan_sha256") == sha256_file(PLAN),
                     "contract=%s actual=%s" % (contract.get("plan_sha256", "")[:8],
                                                sha256_file(PLAN)[:8])))
    out.append(check("F2_denominators_present", bool(contract.get("denominators"))))
    out.append(check("F2_strata_present", bool(contract.get("strata"))))
    out.append(check("F2_case_snapshots_5", len(contract.get("case_snapshots", {})) == 5,
                     "actual=%d" % len(contract.get("case_snapshots", {}))))
    out.append(check("F2_old_contracts_untouched_flag",
                     contract.get("old_contracts_mutated") in (False, None),
                     repr(contract.get("old_contracts_mutated"))))
    return out


def stage_pending_common() -> list[dict]:
    """PENDING-E 骨架：如实列出各 stage 等待的输入。"""
    out = []
    runs_cli = sorted(str(p) for p in CLI_ROOT.glob("*/runs")) if CLI_ROOT.exists() else []
    probes = sorted(str(p) for p in CACHE_ROOT.glob("probes/*")) if CACHE_ROOT.exists() else []
    wb = sorted(str(p) for p in WB_ROOT.glob("*")) if WB_ROOT.exists() else []
    has_executed_evidence = bool(runs_cli) or len(probes) > 0 or len(wb) > 0
    out.append(pending("F3_slot_accounting", [
        "builder REPORT.md + slot-accounting 记录（executed/partial/not_executed 全集）",
        "位置: 各批次目录 REPORT/收据"] if not has_executed_evidence else []))
    out.append(pending("F4_u1_e_registration", [
        "E 提交 ID + execution-manifest.json + runtime-binding.json（lead 封印后）",
        "真实 meta.registered_at 与 started_at"]))
    out.append(pending("F5_file_hashes", [
        "各槽原始证据文件（母本+副本）与收据内嵌 SHA 清单"]))
    out.append(pending("F6_cache_raw_fields", [
        "18 槽原始 body/SSE + usage 原字段（missing/null/0/正值四态）"]))
    out.append(pending("F7_dual_archive", [
        "两个 sandbox 副本的重放收据 + equivalent_simulation 标注 + 适配 diff"]))
    out.append(pending("F8_wb_route_discipline", [
        "WB 五槽原生 trace + declared_alias 选择证据 + app/asar 哈希"]))
    out.append(pending("F9_pollution", [
        "逐场 isolation.ok + 独立无污染裁定 + prompt 哈希清单"]))
    out.append(pending("F10_stop_semantics", [
        "逐槽停止事件记录（401/4xx/5xx 分类与余槽 not_executed 清单）"]))
    out.append(pending("F11_credential_scan_post_e", [
        "E 后对真实证据重跑 credential_scan.py（含 zstd 会话）"]))
    return out


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all",
                    choices=["all", "plan", "pending"])
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    results: list[dict] = []
    if a.stage in ("all", "plan"):
        results += stage_plan()
    if a.stage in ("all", "pending"):
        results += stage_pending_common()
    counts = {"PASS": sum(1 for r in results if r["status"] == "PASS"),
              "FAIL": sum(1 for r in results if r["status"] == "FAIL"),
              "PENDING-E": sum(1 for r in results if r["status"] == "PENDING-E")}
    receipt = {"kind": "final_audit_stage_report", "tool": "final_audit.py",
               "at": now_local(), "stage": a.stage, "counts": counts,
               "results": results, "live_doc_drift": [],
               "note": "PENDING-E=输入未到，非通过也非失败；FAIL=终审发现"}
    exit_code = 1 if counts["FAIL"] else 0
    if a.out:
        out = Path(a.out)
        if out.exists():
            print(json.dumps({"refused": True, "target": str(out)}, ensure_ascii=False))
            return 2
        out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + "\n",
                       encoding="utf-8")
        print("REPORT:", out)
    print(json.dumps(counts, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
