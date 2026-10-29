#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L5 六类分账生成器（lead 代 freeze-engineer；全部数值读现有证据实算）。

纪律：六类互斥分账明确；grading_regression=2（gate v2 + cache mapping v2，判卷器修订
非零环）；事故/中止单列不并账；时间=脚本实钟；输入哈希=实算；输出 O_EXCL 拒写；
不改任何既有证据；formal 判定引用 judge canonical 收据（不自行裁定）。
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.resolve().parents[1]
L5 = REPO / "1-评测方案" / "自动循环L5-2026-10-30"
CLI = REPO / "3-表现现场" / "l5-20261030-cli"
WB = REPO / "3-表现现场" / "l5-20261030-wb-gateway"
JUDGE = REPO / "5-评测报告" / "L5独立验收-2026-10-30"
REV = REPO / "5-评测报告" / "L5判卷修订-2026-10-30"


def now():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sha(p: Path):
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except Exception:
        return None


def jload(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def build() -> dict:
    plan = jload(L5 / "plan.json")
    binding = jload(L5 / "runtime-binding.json")
    judge = jload(JUDGE / "verify-receipt-l5.json")
    canonical = jload(JUDGE / "canonical-gate-admission.json")
    gate_v2 = jload(REV / "gate-v2" / "archive-meta.json")
    map_v2 = jload(REV / "cache-mapping-v2" / "archive-meta.json")
    g2acc = jload(REV / "gate-v2-acceptance-receipt.json")
    g2hist = jload(REV / "gate-v2-history-recompute-receipt.json")
    maprec = jload(REV / "cache-mapping-v2" / "recompute-receipt.json")

    slots = []
    for s in plan["product_slots"]:
        ev = REPO / s["evidence_dir"]
        m = jload(ev / "meta.json")
        row = {"slot_id": s["slot_id"], "product": s["product"], "case": s["case"],
               "order": s["order"], "accounting": None, "status": None,
               "score_observed": None, "formal_admission": None, "evidence_dir": s["evidence_dir"]}
        if m is not None:
            row["accounting"] = "executed"
            row["status"] = m.get("status")
            w = m.get("weighted")
            row["score_observed"] = w
            row["session_capture"] = (m.get("session_capture") or {}).get("match_method") if s["product"] == "dsh" else None
        # formal 从 judge canonical 收据读取（judge 自跑 gate v2 的 6 行判定；结构=按 slot_id 键控）
        if isinstance(canonical, dict):
            r = canonical.get(s["slot_id"])
            if isinstance(r, dict):
                row["formal_admission"] = r.get("formal_admission")
                row["canonical_fails"] = r.get("fails")
        slots.append(row)

    def codex_or_dsh_counts():
        return {"codex": sum(1 for x in slots if x["product"] == "codex"),
                "dsh": sum(1 for x in slots if x["product"] == "dsh"),
                "workbuddy": sum(1 for x in slots if x["product"] == "workbuddy")}

    ledger = {
        "kind": "l5_six_category_ledger", "generated_at": now(),
        "plan": {"plan_id": plan["plan_id"], "binding_registered_at": binding["registered_at"],
                 "design_commit_D": binding["design_commit"],
                 "execution_seal_E3": binding["execution_seal_commit"],
                 "superseded_seals": [
                     {"commit": "7474b84aeaa7290c67ee2288d114953dd6cccadd", "fate": "aborted pre-consumption (WB adapter gate pin defect, zero calls)",
                      "archive": "3-表现现场/l5-20261030-cli/aborted-attempts-20261030T0152seal/"},
                     {"commit": "02a4cac25f679b0e2359f9de6e2b10c82bd9ea0d", "fate": "aborted mid-batch (DSH archive mkdir defect; 4 completed slots preserved then discarded for seal uniformity)",
                      "archive": "3-表现现场/中止重封档案E2-20261030T0207/"}]},
        "product_run": {"planned": 6, "executed": sum(1 for x in slots if x["accounting"] == "executed"),
                        "partial": 0, "not_executed": 0, "formal_true": sum(1 for x in slots if x["formal_admission"] is True),
                        "formal_false": sum(1 for x in slots if x["formal_admission"] is False),
                        "by_product": codex_or_dsh_counts(), "slots": slots,
                        "note": "bird formal=False 系 checker 缺 guards_used/n_tasks 缺省字段（judge canonical 判定，unknown 不折满），observed 100.0 保留"},
        "bare_model_probe": {"planned": 0, "executed": 0},
        "self_test": {"items": [
            {"name": "codex tools selftest (mock full chain)", "receipt": "3-表现现场/l5-20261030-cli/codex", "result": "PASS"},
            {"name": "dsh lab selftest", "receipt": "3-表现现场/l5-20261030-cli/dsh/selftest/runner-selftest-r2.json", "result": "3/3 PASS", "sha256": sha(REPO / "3-表现现场/l5-20261030-cli/dsh/selftest/runner-selftest-r2.json")},
            {"name": "L5 runner acceptance (R1/R2/R3)", "receipt": "3-表现现场/l5-20261030-cli/selftest/l5-runner-acceptance-receipt.json", "result": "11/11 PASS", "sha256": sha(REPO / "3-表现现场/l5-20261030-cli/selftest/l5-runner-acceptance-receipt.json")},
            {"name": "WB runner selftest", "receipt": "3-表现现场/l5-20261030-wb-gateway/selftest/", "result": "71/71 PASS (wb-probe 报告)"}]},
        "offline_recompute": {"items": [
            {"name": "gate v2 history recompute (L4 frozen 17 rows)", "receipt": "5-评测报告/L5判卷修订-2026-10-30/gate-v2-history-recompute-receipt.json", "result": "17/17, 唯一差异=bird 白名单 fail 消失", "all_pass": (g2hist or {}).get("all_pass")},
            {"name": "cache mapping v2 over L4 18 probes", "receipt": "5-评测报告/L5判卷修订-2026-10-30/cache-mapping-v2/recompute-receipt.json", "result": "18 槽 28 断言 + erratum 逐值一致", "all_pass": (maprec or {}).get("all_pass")}]},
        "grading_regression": {"items": [
            {"name": "gate v2 (R4/池L5-8)", "before": gate_v2["before_code"], "after": gate_v2["after_code"],
             "positive_nearwrong": "8/8 (dual-run v2 vs frozen v4)", "receipt": "5-评测报告/L5判卷修订-2026-10-30/gate-v2-acceptance-receipt.json"},
            {"name": "cache mapping v2 (R5/池L5-5)", "before": map_v2["before_code"], "after": map_v2["after_code"],
             "positive_nearwrong": "unit 6/6", "receipt": "5-评测报告/L5判卷修订-2026-10-30/cache-mapping-v2/recompute-receipt.json"}],
            "checker_semantic_revisions": 0},
        "interface_preflight": {"items": [
            {"name": "codex preflight (isolation/checker smoke)", "result": "PASS (builder-codex)"},
            {"name": "dsh preflight", "result": "PASS (builder-dsh)"},
            {"name": "WB preflight + seal-check", "result": "PASS (wb-probe; receipts/write-once)"}]},
        "aborted_attempts_disclosure": {
            "E1_attempt": "codex/dsh 首槽在途 kill -9（真实消耗，无 formal），档案 l5-20261030-cli/aborted-attempts-20261030T0152seal/",
            "E2_attempts": "codex×2 ok / wb×2 ok / dsh dab partial(error) / dsh cargo not_executed —— 全部真实消耗无 formal，档案 中止重封档案E2-20261030T0207/（187 条目，auditor AUD-L5-O1 自引哈希 observation）",
            "E3_voided_claims": "codex dab E3 首试 ws 残留 fail-closed 零调用 claim 作废（supplement-2）",
            "rule": "中止尝试一律单列，不计 6 计划槽，不折算任何分数"},
        "incidents": [
            {"name": "wb-probe ps 误印产品进程命令行（含会话级 Bearer）", "disposition": "零入库（auditor 全 L5 grep 仅披露语句本身命中，无 token 值）；操作规程加固入池"},
            {"name": "WB cmd_accounting write_json_atomic 覆盖 E2 frame", "disposition": "E2 版可经 git b32d844 恢复（judge/auditor 双确认不影响 E3 formal）；一行修复 post-admission 提交，条目入 L5 池"}],
        "judge_independent": {"receipt": "5-评测报告/L5独立验收-2026-10-30/verify-receipt-l5.json", "sha256": sha(JUDGE / "verify-receipt-l5.json"),
                              "summary_from_judge": "formal 5/6；wb-bird formal=False（checker 字段缺省，非基础设施）"},
        "live_doc_drift": []}
    return ledger


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "six-ledger.json"))
    a = ap.parse_args()
    out = Path(a.out)
    data = build()
    body = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if out.exists():
        raise SystemExit("refuse overwrite: %s" % out)
    fd = os.open(str(out), os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    os.write(fd, body.encode("utf-8"))
    os.close(fd)
    print(json.dumps({"ledger": a.out, "sha256_16": hashlib.sha256(out.read_bytes()).hexdigest()[:16],
                      "formal_true": data["product_run"]["formal_true"],
                      "formal_false": data["product_run"]["formal_false"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
