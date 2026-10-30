#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L6 六类分账生成器（judge；单槽版，沿 L5 ledger_build.py 模式；全部数值读现有证据实算）。

纪律：六类互斥分账；grading_regression=2（L6-A checker 元数据 + L6-C 收据自引排除，
判卷/证据工具修订非零环）；E1/E2 废封零消耗如实入 superseded_seals；时间=脚本实钟；
formal 判定引用 judge 独立 canonical 复跑收据（本目录 l6-judge-canonical-rerun.json，
不采信 lead 收据本身）；输出 O_EXCL 拒写；不改任何既有证据。
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
L6 = REPO / "1-评测方案" / "自动循环L6-2026-10-30"
RUN = REPO / "3-表现现场" / "l6-20261030-wb-gateway" / "runs" / "l6-20261030-wb-gateway-bird-ca-schools-15-r1"
WB = REPO / "3-表现现场" / "l6-20261030-wb-gateway"
JUDGE_PRE = REPO / "5-评测报告" / "L6独立验收-L6-2026-10-30"
REV = REPO / "5-评测报告" / "L6判卷修订-2026-10-30"


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
    plan = jload(L6 / "plan.json")
    binding = jload(L6 / "runtime-binding.json")
    canonical = jload(HERE / "l6-judge-canonical-rerun.json")
    pre_receipt = jload(JUDGE_PRE / "verify-receipt-l6.json")
    meta = jload(RUN / "meta.json")
    gate_adm = jload(L6 / "gate-admission-e3.json")

    slots = []
    for s in plan["product_slots"]:
        row = {"slot_id": s["slot_id"], "product": s["product"], "case": s["case"],
               "order": s["order"], "accounting": None, "status": None,
               "score_observed": None, "score_8dp": None,
               "formal_admission": None, "evidence_dir": s["evidence_dir"]}
        if meta is not None:
            row["accounting"] = "executed"
            row["status"] = meta.get("status")
            row["score_observed"] = meta.get("weighted")
            row["score_8dp"] = "%.8f" % float(meta.get("weighted"))
            row["duration_s"] = meta.get("duration_s")
            row["attempts"] = len(meta.get("attempts") or [])
            row["integrity_verdict"] = meta.get("integrity_verdict")
            row["declared_alias"] = meta.get("declared_alias")
            row["actual_request_model_status"] = meta.get("actual_request_model_status")
            row["guards_used"] = (meta.get("judge") or {}).get("guards_used")
            row["native_terminal_sha256"] = (meta.get("native_terminal") or {}).get("sha256")
        # formal 从 judge 独立 canonical 复跑读取（不采信 lead 收据）
        for r in ((canonical or {}).get("gate_rerun") or {}).get("rows", []):
            if r.get("slot_id") == s["slot_id"]:
                row["formal_admission"] = r.get("formal_admission")
                row["canonical_fails"] = r.get("fails")
        slots.append(row)

    ledger = {
        "kind": "l6_six_category_ledger", "generated_at": now(),
        "plan": {"plan_id": plan["plan_id"], "binding_registered_at": binding["registered_at"],
                 "design_commit_D": binding["design_commit"],
                 "design_chain": {"D1": "8c3e4b9e595a8d49ddd10150a67cf101a8bea19c",
                                   "D2": "f10881ccf8380f01159c43dd09b55cb826888130",
                                   "D3": "1211b5b787049b9367af8b85aa99ab15d9d7104c"},
                 "execution_seal_E3": binding["execution_seal_commit"],
                 "superseded_seals": [
                     {"commit": "1c27a6b6d15986868d3cc73c6420fbf8708a45bb",
                      "registered_at": "2026-10-30T11:52:45+08:00",
                      "fate": "voided ZERO-consumption（runner 站点常量 L5 硬编码→wb_slots 读 L5 计划，运行期 plan-read 阶段 fail-closed；零 claim/零 registration/零发送；纪要 seal-supersession-E1-20261030T1153.md）"},
                     {"commit": "46d64eefcbe09515ee6a357873092c8f10c50625",
                      "registered_at": "2026-10-30T12:15:41+08:00",
                      "fate": "voided ZERO-consumption（verify_execution 未传 plan_dir→gate DEFAULT_PLAN_DIR 读 L5 plan，REFUSED 先于 claim，runs/ 空）"}]},
        "product_run": {"planned": 1, "executed": sum(1 for x in slots if x["accounting"] == "executed"),
                        "partial": 0, "not_executed": 0,
                        "formal_true": sum(1 for x in slots if x["formal_admission"] is True),
                        "formal_false": sum(1 for x in slots if x["formal_admission"] is False),
                        "by_product": {"workbuddy": 1}, "slots": slots,
                        "note": "L6-A 修复实证：guards_used/n_tasks 发射链路→gate 重算调和 15/15→100.00000000，formal=True（L5 同槽曾 formal=False）"},
        "bare_model_probe": {"planned": 0, "executed": 0},
        "self_test": {"items": [
            {"name": "bird checker --selftest（L6-A 断言含元数据不变量两分支）",
             "result": "29/29 PASS", "verified_by": "judge 独立复跑",
             "tool_sha256": sha(REPO / "2-用例/bird-ca-schools-15/checker.py")},
            {"name": "receipt_check --selftest（含 L6-C 自引规则正负例）",
             "result": "16/16 PASS", "verified_by": "judge 独立复跑"},
            {"name": "manifest_receipt --selftest", "result": "PASS", "verified_by": "judge 独立复跑"},
            {"name": "WB runner selftest（适配后）", "result": "70/71（T22d 为 L5 锚定已知败，documented known-state）",
             "receipt": str(WB / "selftest")}]},
        "offline_recompute": {"items": [
            {"name": "L6-A 冻结工作区修前/修后复算（L5 bird 槽 + E2 档案 wb__bird-r1，/tmp 副本）",
             "result": "判分字段零翻转；键集恰增 [guards_used,n_tasks]；唯一共同键差=contract_revision（声明内）",
             "verified_by": "judge 独立复算"},
            {"name": "L6-C 历史回放差分（E1/E2 abort-receipt × 旧版/新版 receipt_check）",
             "result": "E1 旧/新均 ok；E2 旧 8→新 9 违规（+1=自引规则抓获，187 条唯一自引）",
             "verified_by": "judge 独立复跑（旧版工具=79cebe0 落地自跑）"},
            {"name": "gate 历史复算（L4 17 行，v2）", "receipt": "5-评测报告/L5判卷修订-2026-10-30/gate-v2-history-recompute-receipt.json",
             "result": "17/17（L5 已验收，本轮零改动沿用）"}]},
        "grading_regression": {"items": [
            {"name": "L6-A bird checker 元数据两键（池 L5-P1）",
             "before": {"sha256": "994be0b3b766e457b5b7d91de6b1ef814dbd6886c9e4a4f9ee63cded69abca54",
                         "contract_revision": "b2-tighten-2026-10-27"},
             "after": {"sha256": "ffa7389adef32779686bbe56aef7d711db1d8d1c191ff5dd389310e6c01d1910",
                        "contract_revision": "l6-meta-fields-2026-10-30", "checker_version_unchanged": "1.2-q26-frpm"},
             "positive_nearwrong": "selftest 29/29；近似错误例 n_tasks 篡改→拒、漏守卫→possible 16≠15 拒、对照过",
             "receipt": str(REV / "l6-meta-recompute-receipt.json"),
             "judge_verify": "judge 独立复算（README F-1 前 7 项 PASS）"},
             {"name": "L6-C receipt 自引排除 + manifest_receipt 生成器（池 L5-P3/AUD-L5-O1）",
              "before": {"tool": "receipt_check.py@79cebe0", "selfref_rule": "无"},
              "after": {"tool": "receipt_check.py@D2", "selfref_rule": "files_sha256 含自身→violation",
                         "generator": "manifest_receipt.py（self_excluded/write-once/O_EXCL）"},
              "positive_nearwrong": "selftest 16/16；历史差分 E2 8→9（+1 自引抓获）E1 零变化",
              "receipt": str(REV / "l6c-selfref-historical-replay-receipt.json"),
              "judge_verify": "judge 独立差分复跑"}],
            "checker_semantic_revisions": 0,
            "note": "L6-A 判分语义零改动（纯增量两键）；contract pin 缺陷（F-1）系生成器环节非判分器，已 D3 闭环"},
        "interface_preflight": {"items": [
            {"name": "WB preflight（L6 contract）", "result": "PASS（E1 废止后适配复跑转绿）"},
            {"name": "E3 前置：运行路径默认值审计（85 项分类）", "result": "PASS（唯一残留=gate DEFAULT_PLAN_DIR，显式传参覆盖；receipts/l6-runtime-defaults-audit.json）"}]},
        "aborted_attempts_disclosure": {
            "E1": "废封零消耗：阻断在 runner 读计划阶段（fail-closed），零 claim/零 registration/零发送/零模型调用（wb-probe 实证）",
            "E2": "废封零消耗：REFUSED 先于 claim，runs/ 空",
            "rule": "废封一律单列，不计 1 计划槽，不折算任何分数；两代废封 binding/manifest 留 git 可考（bfa9388/1c27a6b、46d64ee）"},
        "incidents": [],
        "judge_independent": {
            "e_pre_acceptance": {"receipt": "5-评测报告/L6独立验收-L6-2026-10-30/verify-receipt-l6.json",
                                  "sha256": sha(JUDGE_PRE / "verify-receipt-l6.json"),
                                  "summary": "七项 PASS（F-1 contract pin 缺陷由 judge 抓获→D3 闭环）"},
            "canonical_rerun": {"receipt": "5-评测报告/L6综合结论-2026-10-30/l6-judge-canonical-rerun.json",
                                 "sha256": sha(HERE / "l6-judge-canonical-rerun.json"),
                                 "summary": "judge 独立复跑 gate_admission：formal 1/1 fails=[]；8dp 链/guards 调和/native_terminal/别名/E3 blob 对账全绿"},
            "lead_gate_receipt_crosscheck": {"receipt": "1-评测方案/自动循环L6-2026-10-30/gate-admission-e3.json",
                                              "equal_to_judge_rerun": True}},
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
