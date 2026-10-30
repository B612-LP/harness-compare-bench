#!/usr/bin/env python3
"""L5 gate v2 (R4) 历史复算影响:L4 冻结 17 行用 v2 复判并程序化比对冻结基线。

预期(唯一允许差异):bird 槽「not_executed 目录含其他文件(疑似虚造证据/空流)」fail
消失且 record_valid False→True;其余 16 槽 fails 与投影字段逐条一致。
零模型、零网络;L4 文件只读。
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
L4_PLAN = ROOT / "1-评测方案/自动循环L4-2026-10-29"
BASE = ROOT / "5-评测报告/L4独立验收-2026-10-29/realdata-product"
HERE = Path(__file__).resolve().parent

spec = importlib.util.spec_from_file_location("l5_gate_v2_hist", ROOT / "1-评测方案/工具链/l5-execution/gate.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

PROJECT = ("formal_admission", "accounting", "fails", "contamination_cleared",
           "evidence_complete", "full_denominator_score_valid", "record_valid")

out = {"generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
       "zero_model_calls": True, "gate": "1-评测方案/工具链/l5-execution/gate.py",
       "gate_sha256": hashlib.sha256((ROOT / "1-评测方案/工具链/l5-execution/gate.py").read_bytes()).hexdigest(),
       "binding": "1-评测方案/自动循环L4-2026-10-29/runtime-binding.json", "products": {}}

PLAN_SLOTS = {s["slot_id"] for s in json.loads(
    (L4_PLAN / "plan.json").read_text(encoding="utf-8"))["product_slots"]}
baseline = {}
skipped_keys = []
for f in sorted(BASE.glob("gate-admission-*.json")):
    doc = json.loads(f.read_text(encoding="utf-8"))
    for key, row in doc.items():
        if not isinstance(row, dict) or "fails" not in row:
            continue  # 主题索引/summary 键(如 'dab'/'summary'),非槽键
        sid = key if key in PLAN_SLOTS else row.get("slot_id")
        if sid not in PLAN_SLOTS:
            skipped_keys.append({"file": f.name, "key": key})
            continue
        baseline[sid] = {"file": f.name,
                         **{k: row.get(k) for k in PROJECT if k != "record_valid"},
                         **({"record_valid": row["record_valid"]} if "record_valid" in row else {})}
out["baseline_keys_skipped"] = skipped_keys

for product in ("codex", "dsh", "workbuddy"):
    rep = mod.gate_admission(str(L4_PLAN / "runtime-binding.json"), product,
                             plan_dir=L4_PLAN)
    rows = {}
    for r in rep["per_slot"]:
        rows[r["slot_id"]] = {k: r.get(k) for k in PROJECT}
    out["products"][product] = {"summary": rep["summary"], "rows": rows}

out["baseline_slots"] = len(baseline)
diffs = []
all_ids = sorted(set(baseline) | {s for p in out["products"].values() for s in p["rows"]})
for sid in all_ids:
    b = baseline.get(sid)
    v2 = next((p["rows"][sid] for p in out["products"].values() if sid in p["rows"]), None)
    if b is None or v2 is None:
        diffs.append({"slot": sid, "kind": "presence-mismatch", "baseline": bool(b), "v2": bool(v2)})
        continue
    d = {}
    for k in PROJECT:
        bv, vv = b.get(k), v2.get(k)
        if k == "record_valid" and bv is None:
            continue  # 基线投影不含该键(仅 wb-dab 特例行含);bird 派生判定由 bird_ok 单独判
        if bv != vv:
            d[k] = {"baseline": bv, "v2": vv}
    if d:
        diffs.append({"slot": sid, "kind": "field-diff", "fields": d})
out["diffs"] = diffs
BIRD = "l4-20261029-wb-gateway-bird-ca-schools-15-r1"
bird = next((p["rows"][BIRD] for p in out["products"].values() if BIRD in p["rows"]), None)
out["bird_v2"] = bird
WL_FAIL = "not_executed 目录含其他文件（疑似虚造证据/空流）：['registrations']"
bird_ok = bool(bird) and baseline.get(BIRD, {}).get("fails") == [WL_FAIL] \
    and bird["fails"] == [] and bird.get("record_valid") is True \
    and baseline.get(BIRD, {}).get("record_valid") in (None, False)
out["bird_whitelist_fail_gone"] = bird_ok
unexpected = [x for x in diffs if x["slot"] != BIRD]
ok = (bird_ok and not unexpected)
# 记录 record_valid 变化作为 bird 派生判定证据(baseline 投影无该键,由 v2 与 L4 sidecar 判定)
out["assertions"] = [
    {"name": "bird 槽:基线恰含白名单 fail,v2 恰为空且 record_valid=True", "pass": bird_ok},
    {"name": "其余槽与冻结基线逐字段一致(零未授权 diff)", "pass": not unexpected},
    {"name": "17 计划槽全覆盖比对", "pass": len(baseline) == len(PLAN_SLOTS)},
    {"name": "唯一允许差异 全部成立", "pass": ok},
]
out["all_pass"] = ok
dest = HERE / "gate-v2-history-recompute-receipt.json"
dest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"all_pass": ok, "baseline_slots": len(baseline), "plan_slots": len(PLAN_SLOTS),
                  "unexpected_diffs": len(unexpected),
                  "receipt": str(dest.relative_to(ROOT))}, ensure_ascii=False))
sys.exit(0 if ok else 1)
