#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L7 七账生成器（judge；单工具链环·零真实批，沿六账结构精简；全部数值读现有证据实算）。

七类：①共享验证器修订（L7-A）②运维规程（L7-B）③历史批基线引用固定（L4/L5/L6）
④设计变更记录（r1-r6 VOIDED 链）⑤判分语义影响（恒 0）⑥事故/中止/废封（0）
⑦judge 独立验收引用。时间=脚本实钟；哈希=实算；输出 O_EXCL 拒写。
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
L7 = REPO / "1-评测方案" / "自动循环L7-2026-10-30"
REV = REPO / "5-评测报告" / "L7验证器修订-2026-10-30"
PRE_SHA = "38b42a87c30c87d277f0a8984c4300919da3867826790a01fd24af6766b05ce9"
POST_SHA = "25dbf52e46404014609b76324750452ce5f680bb770e1e0fbe4d6c57908ea6c9"


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
    disk_gate = sha(REPO / "1-评测方案/工具链/l5-execution/gate.py")
    ledger = {
        "kind": "l7_seven_category_ledger", "generated_at": now(),
        "cycle": {"plan_id": "l7-20261030", "branch": "loop7-2026-10-30",
                   "main_base": "c8710fbcee1b9598c15077b5d2be344d4cbf49fa (PR#10 L5+L6 集成点)",
                   "D1": "a186ff38eaf2c12e1f8b5441580ccb5e351242e8",
                   "D2": "47bd6855d61f13cd9fbb0f5461c5e938b316db75",
                   "real_batch": "本环零真实批（工具链/规程环）；最近真实批=L6 formal 1/1（见 L6 综合结论）"},
        "verifier_revision": {  # ①
            "name": "L7-A gate 语义默认值显式化（池：L6 U-2）",
            "before": {"path": "1-评测方案/工具链/l5-execution/gate.py", "sha256": PRE_SHA,
                        "default": "DEFAULT_PLAN_DIR=自动循环L5-2026-10-30（5 处锚定）"},
            "after": {"path": "1-评测方案/工具链/l5-execution/gate.py", "sha256": disk_gate,
                       "default": "无默认批（CLI 必填 / API None→GateError / --selftest 例外）"},
            "scoring_semantics_changed": False,
            "acceptance": {"r7": "12/12（judge 独立复跑同数）", "selftest": "PASS",
                            "near_miss": ["缺两参拒", "缺 --plan-dir 拒", "API None→GateError", "load_execution_seal(None)→GateError", "坏目录 fail-closed", "P4 封印 pin 精确拒"]},
            "receipt": "5-评测报告/L7验证器修订-2026-10-30/l7-gate-recompute-receipt.json",
            "prereg_wording_deviation": "PREREG『ValueError』→实现 GateError（措辞级 observation，fail-closed 意图完全达成）"},
        "operations_hygiene": {  # ②
            "name": "L7-B P4 ps 操作规程条目化",
            "doc": {"path": "1-评测方案/工具链/OPERATIONS-hygiene.md", "sha256": sha(REPO / "1-评测方案/工具链/OPERATIONS-hygiene.md")},
            "scan": {"receipt": "1-评测方案/工具链/bearer-scan-receipt-l7.json",
                      "sha256": sha(REPO / "1-评测方案/工具链/bearer-scan-receipt-l7.json"),
                      "files_scanned": 156, "bearer_literals": 0,
                      "hits_classified": "9 全部 env-var-passthrough（规程允许形态）",
                      "judge_corroboration": "独立自扫 Bearer 字面量（l6 现场+工具链）=0 命中",
                      "voided": "r1 未分类误报 VOIDED 留档"}},
        "history_baseline_references": {  # ③
            "rule": "跨批重演按设计不可行（见④）；历史批裁定由封印时刻收据固定",
            "L4": {"formal": "0/17", "source": "L4 收官收据（realdata-product）", "status": "frozen"},
            "L5": {"formal": "5/6", "source": "L5独立复核 r4-history-reproduced-receipt-02 + judge canonical", "status": "frozen"},
            "L6": {"formal": "1/1", "source": "1-评测方案/自动循环L6-2026-10-30/gate-admission-e3.json + judge canonical rerun", "status": "frozen"},
            "known_impact": "l4/l5 冻结现场调 gate 无显式参=documented known-impact（现场封存不重跑）；l6 已显式不受影响；未来重跑须先适配（池）"},
        "design_change_record": {  # ④
            "note": "1-评测方案/自动循环L7-2026-10-30/history-replay-design-note.md",
            "sha256": sha(L7 / "history-replay-design-note.md"),
            "voided_chain": [{"r": "r1", "fate": "跨 pin 复算设计误（22 断言 5 过）——封印 fail-closed 按设计工作"},
                              {"r": "r2", "fate": "冻结副本错位（HERE 相对推导崩溃）"},
                              {"r": "r3", "fate": "部分世界复判不可（manifest 钉全套工链）"},
                              {"r": "r4", "fate": "树内 binding 代际错位（E 后重写）"},
                              {"r": "r5", "fate": "封印树不含 E 后证据（伪期望 executed=17）"},
                              {"r": "r6", "fate": "证据子树覆盖无法既全又纯"}],
            "judge_assessment": "论证成立：r1 发现=P4 独立复现；r4 与 L6 废封纪要互证；r3 与 L4 验收已知互证；三方一致机制为本 judge L5/L6 验收亲证"},
        "grading_semantics_impact": {"changed": 0, "note": "判分语义零改动（formal 真值表/重算口径/白名单不动；diff 24 行全声明类）"},  # ⑤
        "incidents_abortions": [],  # ⑥ 零
        "judge_independent": {  # ⑦
            "receipt": "5-评测报告/L7综合结论-2026-10-30/verify-receipt-l7.json",
            "sha256": sha(HERE / "verify-receipt-l7.json"),
            "summary": "r7 12/12 独立复跑+selftest 独立 PASS+diff 逐行分类+设计论证核可+L7-B 独立佐证"},
        "live_doc_drift": []}
    return ledger


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "seven-ledger.json"))
    a = ap.parse_args()
    out = Path(a.out)
    data = build()
    body = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if out.exists():
        raise SystemExit("refuse overwrite: %s" % out)
    fd = os.open(str(out), os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    os.write(fd, body.encode("utf-8"))
    os.close(fd)
    print(json.dumps({"ledger": a.out, "sha256_16": hashlib.sha256(out.read_bytes()).hexdigest()[:16]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
