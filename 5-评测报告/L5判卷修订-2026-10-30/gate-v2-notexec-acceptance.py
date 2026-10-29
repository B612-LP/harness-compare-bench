#!/usr/bin/env python3
"""L5 gate v2 (R4) not_executed 白名单正/近似错误例验收。

对同一合成世界分别跑 gate v2(l5-execution)与冻结 L4 gate(l4-execution,只读 import):
- 正例:notexecuted.json + registrations/(R3 强制 pre-run 登记目录)
- 近似错误例:registrations 拼写变体仍 fail;registrations 与其他 extra 并存仍 fail;
  纯虚造 extra 仍 fail。
合成 git 环境(gate 模块内 _fake_git_env),零 git 写、零网络、零模型。
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


V2 = load("l5_gate_v2", ROOT / "1-评测方案/工具链/l5-execution/gate.py")
V4 = load("l4_gate_frozen", ROOT / "1-评测方案/工具链/l4-execution/gate.py")

D, E = "d" * 40, "e" * 40
D_TIME, E_TIME = "2026-10-29T19:00:00+08:00", "2026-10-29T20:00:00+08:00"
CASE = "dabstep-payments-10"
CONTRACT = {
    "strata": {"cli_current_sentinel": {"products": ["dsh"], "model": "deepseek-flash",
                                        "effort": "low", "route_host": "api.deepseek.com",
                                        "ranking": False}},
    "case_snapshots": {CASE: {"checker.py": "c" * 64}},
    "denominators": {CASE: 10},
    "admission": {"required_original_evidence": ["prompt", "stdout", "stderr",
                                                 "session", "checker", "workspace"]}}
REQUIRED = {"plans/l4/plan.json", "plans/l4/contract.json"}


def mkslot(i, tag):
    sid = "l5-ne-%s-r%d" % (tag, i)
    return {"slot_id": sid, "run_id": sid, "event_id": "event:" + sid, "kind": "product_run",
            "product": "dsh", "case": CASE, "rep": i, "stratum": "cli_current_sentinel",
            "order": i, "evidence_dir": "runs/" + sid, "timeout_s": 1800}


def mknotexec(ev: Path, s, extras=()):
    ev.mkdir(parents=True, exist_ok=True)
    rec = {"slot_id": s["slot_id"], "run_id": s["run_id"], "event_id": s["event_id"],
           "preregistration_commit": E, "reason": "wb renderer not ready", "stop_source": "R6",
           "live_doc_drift": []}
    (ev / "notexecuted.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    for name, files in extras:
        p = ev / name
        if files is None:  # plain file
            p.write_text("x", encoding="utf-8")
        else:
            p.mkdir(parents=True, exist_ok=True)
            for fn, content in files:
                fp = p / fn
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_text(content, encoding="utf-8")


def run_world(mod, tag_sets):
    with tempfile.TemporaryDirectory(prefix="l5-gate-v2-acc-") as td:
        tmp = Path(td)
        plan_dir = tmp / "plans" / "l4"
        plan_dir.mkdir(parents=True)
        slots = [mkslot(i + 1, tag) for i, (tag, _) in enumerate(tag_sets)]
        (plan_dir / "plan.json").write_text(json.dumps(
            {"plan_id": "l5-acc", "product_slots": slots}), encoding="utf-8")
        (plan_dir / "contract.json").write_text(json.dumps(CONTRACT), encoding="utf-8")
        ext = tmp / "driver.sh"
        ext.write_text("ok\n", encoding="utf-8")
        bp, gr, gt, ga, _b = mod._fake_git_env(tmp, plan_dir, D, E, E_TIME, D_TIME, ext)
        bp2 = tmp / "binding-released.json"
        bp2.write_text(json.dumps(dict(json.loads(bp.read_text()),
                                       released_for_model_calls=True)), encoding="utf-8")
        for s, (_, extras) in zip(slots, tag_sets):
            mknotexec(tmp / s["evidence_dir"], s, extras)
        rep = mod.gate_admission(bp2, "dsh", repo=tmp, plan_dir=plan_dir,
                                 git_reader=gr, git_time=gt, git_ancestor=ga,
                                 required_set=REQUIRED)
        return [{"slot": s["slot_id"], "fails": r["fails"], "record_valid": r["record_valid"],
                 "whitelisted_entries": r.get("whitelisted_entries")}
                for s, r in zip(slots, rep["per_slot"])]


REG_FILES = [("reg-01.json", "{\"task\":\"bird-ca-schools-15\",\"declared_at\":\"2026-10-30T00:00:00+08:00\"}"),
             ("inputs/manifest.json", "{\"files\":3}")]
WORLDS = [
    ("plain", ()),
    ("registrations-dir", (("registrations", REG_FILES),)),
    ("typo-variant", (("registrations.json", None),)),
    ("reg-plus-extra", (("registrations", REG_FILES), ("another_extra.txt", None))),
    ("fabricated-extra", (("fabricated_evidence.jsonl", None),)),
]

out = {"generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
       "zero_model_calls": True, "worlds": [w[0] for w in WORLDS]}
ok = True
for mod, label in ((V2, "v2"), (V4, "v4-frozen")):
    rows = run_world(mod, WORLDS)
    out[label] = rows
    for (tag, _), row in zip(WORLDS, rows):
        wl_fail = [f for f in row["fails"] if "not_executed 目录含其他文件" in f]
        out.setdefault("checks", []).append(
            {"world": tag, "gate": label, "whitelist_fail": wl_fail,
             "record_valid": row["record_valid"], "whitelisted_entries": row["whitelisted_entries"]})

def has_wl_fail(gate, world):
    return [c for c in out["checks"] if c["gate"] == gate and c["world"] == world][0]["whitelist_fail"]

EXPECT = [
    ("v2 正例 registrations/ 无 fail", lambda: not has_wl_fail("v2", "registrations-dir")),
    ("v2 正例 record_valid=True", lambda: [c for c in out["checks"] if c["gate"] == "v2" and c["world"] == "registrations-dir"][0]["record_valid"] is True),
    ("v2 正例 whitelisted_entries 记录 2 文件 SHA", lambda: len([c for c in out["checks"] if c["gate"] == "v2" and c["world"] == "registrations-dir"][0]["whitelisted_entries"]) == 2),
    ("v2 拼写变体仍 fail", lambda: bool(has_wl_fail("v2", "typo-variant"))),
    ("v2 registrations+extra 并存仍 fail", lambda: bool(has_wl_fail("v2", "reg-plus-extra"))),
    ("v2 纯虚造 extra 仍 fail", lambda: bool(has_wl_fail("v2", "fabricated-extra"))),
    ("v4 冻结版对 registrations/ 仍 fail(原行为保持)", lambda: bool(has_wl_fail("v4-frozen", "registrations-dir"))),
    ("v4 冻结版对其余三个负例均 fail", lambda: all(bool(has_wl_fail("v4-frozen", w)) for w in ("typo-variant", "reg-plus-extra", "fabricated-extra"))),
]
out["assertions"] = []
for name, fn in EXPECT:
    r = bool(fn())
    out["assertions"].append({"name": name, "pass": r})
    ok = ok and r
out["all_pass"] = ok
dest = Path(__file__).resolve().parent / "gate-v2-acceptance-receipt.json"
dest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"all_pass": ok, "receipt": str(dest.relative_to(ROOT))}, ensure_ascii=False))
sys.exit(0 if ok else 1)
