#!/usr/bin/env python3
"""L5 CLI runner 修复专项验收（task-11；零模型、零网络、零真实 CLI 调用）。

R1 发射：judge_block/derive_guards 对 L4 真实 cargo/dab checker 输出的推导正例 +
计数篡改负例（conflict 必现）。
R2 ws-meta：mock prepare 后 ws 仅含 inputs+TASK.md，meta 落 ev/meta.prepare.json；
负例=ws 出现 meta.json 必被本扫描检出。
R3 capture marker：对 ~/.dsh/sessions 真实 L4 会话目录名回放，6/6 命中（exact 或 suffix），
旧 marker 构造作为对照组应 0/6（缺陷复现证据）。
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
BATCH = HERE.parent
REPO = BATCH.parents[1]
sys.path.insert(0, str(REPO))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CODEX = load("l5_codex_lab", BATCH / "codex/tools/lab.py")
DSH = load("l5_dsh_lab", BATCH / "dsh/tools/lab.py")

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append({"case": name, "pass": bool(ok), "detail": str(detail)[:260]})


# ---------- R1: guards derivation on real L4 checker outputs ----------
def r1_checks():
    l4runs = REPO / "3-表现现场/l4-20261029-cli/codex/runs"
    cargo = json.loads((l4runs / "l4-20261029-cli-codex-tb-cargo-plan-r1/checker.stdout").read_text(encoding="utf-8"))
    dab = json.loads((l4runs / "l4-20261029-cli-codex-dabstep-payments-10-r1/checker.stdout").read_text(encoding="utf-8"))
    gc = CODEX.derive_guards(cargo, 27)
    check("r1_cargo_guards", gc["guards_used"] == ["input_integrity", "code_rerun", "plan_structure"]
          and gc["guards_conflict"] is False and gc["guards_candidates"] >= 1, json.dumps(gc, ensure_ascii=False))
    gd = CODEX.derive_guards(dab, 10)
    check("r1_dab_guards", gd["guards_used"] == ["answers_format", "input_integrity"]
          and gd["guards_conflict"] is False, json.dumps(gd, ensure_ascii=False))
    tampered = json.loads(json.dumps(cargo))
    # 负例：earned 篡改至物理不可达（总通过 22，任去 3 项最多剩 22 通过 < 25）→ 必无
    # reconciling 组合 → conflict；注：+1 小篡改仍可被其他调和集吸收（1800+ 候选），
    # 推导保证的是内部一致性而非防篡改——防篡改由 gate 对 raw checks 独立重算承担。
    tampered["passed"] = 25
    gt = CODEX.derive_guards(tampered, 27)
    check("r1_impossible_counts_conflict", gt["guards_conflict"] is True and gt["guards_used"] is None,
          json.dumps(gt, ensure_ascii=False))
    jb = CODEX.judge_block({"case": "tb-cargo-plan"}, cargo)
    check("r1_judge_block_8dp", jb["correct"] == 19 and jb["n_tasks"] == 27
          and jb["weighted"] == round(100 * 19 / 27, 8) and jb["guards_conflict"] is False,
          json.dumps(jb, ensure_ascii=False))


# ---------- R2: mock prepare → ws 无 meta,meta.prepare.json 在 ev ----------
def r2_checks():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        saved = {k: getattr(CODEX, k) for k in ("WS_ROOT", "RUNS", "BATCH", "CASE_ROOT",
                                                "WS_ALLOWED_ROOT", "load_contract", "cli_version")}
        try:
            case = td / "case" / "dabstep-payments-10"
            (case / "inputs").mkdir(parents=True)
            (case / "inputs" / "q.jsonl").write_text("row\n", encoding="utf-8")
            (case / "instruction.md").write_text("# fake task\n", encoding="utf-8")
            qsha = hashlib.sha256((case / "inputs" / "q.jsonl").read_bytes()).hexdigest()
            CODEX.CASE_ROOT = td / "case"
            CODEX.WS_ROOT = td / "ws"
            CODEX.WS_ALLOWED_ROOT = td
            CODEX.RUNS = td / "runs"
            CODEX.BATCH = td / "batch"
            CODEX.cli_version = lambda: "stub-codex 0.0.0"
            CODEX.load_contract = lambda: {
                "rule_version": "l5-20261030-batch-v1",
                "checker_sha256": {"dabstep-payments-10": "c" * 64},
                "denominators": {"dabstep-payments-10": 10},
                "case_snapshots": {"dabstep-payments-10": {
                    "checker.py": "c" * 64,
                    "files": {"inputs/q.jsonl": qsha, "instruction.md": hashlib.sha256((case / "instruction.md").read_bytes()).hexdigest()}}},
            }
            rc = CODEX.cmd_prepare("l5-20261030-cli-codex-dabstep-payments-10-r1")
            check("r2_prepare_rc0", rc == 0, "rc=%s" % rc)
            ws = CODEX.WS_ROOT / "l5-20261030-cli-codex-dabstep-payments-10-r1"
            names = sorted(p.name for p in ws.iterdir())
            check("r2_ws_only_inputs_task", names == ["TASK.md", "inputs"], str(names))
            ev = CODEX.RUNS / "l5-20261030-cli-codex-dabstep-payments-10-r1"
            mp = ev / "meta.prepare.json"
            check("r2_meta_prepare_in_ev", mp.is_file(), str(mp))
            meta = json.loads(mp.read_text(encoding="utf-8")) if mp.is_file() else {}
            iv = meta.get("inputs_verification") or {}
            check("r2_inputs_verification_ok", iv.get("ok") is True and iv.get("checked") == 1,
                  json.dumps(iv, ensure_ascii=False)[:200])
            # 负例：ws 出现 meta.json 必须被 R2 扫描口径检出
            (ws / "meta.json").write_text("{}", encoding="utf-8")
            leaked = [p.name for p in ws.rglob("meta.json")]
            check("r2_negative_ws_meta_detected", leaked == ["meta.json"], str(leaked))
        finally:
            for k, v in saved.items():
                setattr(CODEX, k, v)


# ---------- R3: capture marker against real L4 session dir names ----------
def r3_checks():
    base = Path.home() / ".dsh" / "sessions"
    l4_slots = ["l4-20261029-cli-dsh-dabstep-payments-10-r%d" % i for i in (1, 2, 3)] + \
               ["l4-20261029-cli-dsh-tb-cargo-plan-r%d" % i for i in (1, 2, 3)]
    if not base.is_dir():
        check("r3_sessions_base", False, "missing ~/.dsh/sessions")
        return
    real_names = {p.name for p in base.iterdir() if p.is_dir()}
    hit_new = hit_old = 0
    for sid in l4_slots:
        ws = Path.home() / "bench-workspaces" / "l4-20261029" / "dsh" / sid
        expected = DSH.dsh_session_dirname(ws)
        inner = expected[2:-2]
        tail = "-" + ws.name
        if any(n == expected for n in real_names):
            hit_new += 1
        elif any(n.startswith("--") and n.endswith("--") and n[2:-2].endswith(tail) for n in real_names):
            hit_new += 1
        old_marker = "-dsh-%s-%s--" % (ws.parent.name, ws.name)
        if any(old_marker in n for n in real_names):
            hit_old += 1
    check("r3_new_matcher_6of6", hit_new == 6, "hit=%d/6" % hit_new)
    check("r3_old_marker_0of6_defect_reproduced", hit_old == 0, "hit=%d/6（L4 缺陷复现）" % hit_old)


r1_checks()
r2_checks()
r3_checks()
out = {"kind": "l5_runner_repair_acceptance", "zero_model": True, "zero_network": True,
       "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
       "checks": RESULTS, "live_doc_drift": [],
       "summary": {"total": len(RESULTS), "passed": sum(1 for r in RESULTS if r["pass"])},
       "evidence": [{"path": str(BATCH / "codex/tools/lab.py"),
                     "sha256": hashlib.sha256((BATCH / "codex/tools/lab.py").read_bytes()).hexdigest()},
                    {"path": str(BATCH / "dsh/tools/lab.py"),
                     "sha256": hashlib.sha256((BATCH / "dsh/tools/lab.py").read_bytes()).hexdigest()}]}
out["all_pass"] = out["summary"]["passed"] == out["summary"]["total"]
dest = HERE / "l5-runner-acceptance-receipt.json"
dest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(out["summary"], ensure_ascii=False), "→", dest)
sys.exit(0 if out["all_pass"] else 1)
