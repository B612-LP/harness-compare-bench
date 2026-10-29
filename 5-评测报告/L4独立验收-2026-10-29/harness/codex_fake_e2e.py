#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""codex_fake_e2e.py — judge 独立 L4 codex runner fake e2e harness（阶段I）。

纪律（lead 2026-10-29 事故后铁律）：
- 绝不用 PATH 桩驱动 run/prepare——在受控子进程内 import 真实 lab 模块并注入
  lab.CODEX_BIN=<fake 绝对路径>；preflight（内部硬编码 ["codex","--version"]）才用
  受限 PATH（无 /opt/homebrew/bin），并记录解析证据。
- 哨兵（python socket）+ 桩 audit 双证：桩记录每次调用 argv/pid/摘要，断言零真实 CLI。
- 不替换待测函数；只注入外部边界（CLI 桩、时间由真实睡眠、无 DB）。
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from l4_fixture import build_fixture, harness_env, jdump, sha_file  # noqa: E402

HARNESS = Path(__file__).resolve().parent


def now_marker() -> str:
    import datetime as dt
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(timespec="seconds")


INPROC = r'''
import importlib.util, json, sys, os
MARK = "@@RESULT@@"
lab_path, slot, fx_json, mode, extra_json = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
fx = json.loads(fx_json)
extra = json.loads(extra_json)
spec = importlib.util.spec_from_file_location("l4lab", lab_path)
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)
audit_path = os.environ["FX_AUDIT"]
open(audit_path, "a").close()  # touch
n0 = sum(1 for _ in open(audit_path)) if os.path.exists(audit_path) else 0
if mode == "set_binding_released":
    pass
# run/prepare 驱动（真实 cmd_run / cmd_prepare / gate 路径）
args = extra.get("args") or ["run", slot]
if extra.get("set_codex_bin", True):
    lab.CODEX_BIN = fx["fake_codex"]
rc = lab.main(args)
n1 = sum(1 for _ in open(audit_path)) if os.path.exists(audit_path) else 0
out = {"rc": rc, "audit_invocations": n1 - n0}
halt = os.path.join(fx["codex_batch"], "halt.json")
out["halt_exists"] = os.path.exists(halt)
print(MARK + json.dumps(out, ensure_ascii=False))
'''


def run_inproc(fx, slot, args, mode="run", env_extra=None, timeout=600):
    """受控子进程：import 真实 lab + CODEX_BIN 注入 + 哨兵 env。"""
    lib = fx["sentinel_lib"]
    from l4_fixture import write_sentinel
    write_sentinel(lib)
    log = lib.parent / "sentinel-codex.log"
    log.touch()
    env = dict(os.environ, HOME=str(fx["home"]),
               FX_AUDIT=str(fx["work"] / "fake-codex-audit.jsonl"),
               JUDGE_SENTINEL_LOG=str(log),
               PYTHONDONTWRITEBYTECODE="1")
    env.update(env_extra or {})
    fx_pub = {"fake_codex": str(fx["bin"] / "codex"),
              "codex_batch": str(fx["CODEX"])}
    p = subprocess.run([sys.executable, "-c", INPROC, str(fx["CODEX"] / "tools" / "lab.py"),
                        slot, json.dumps(fx_pub), mode,
                        json.dumps({"args": args})],
                       capture_output=True, text=True, env=env, timeout=timeout,
                       cwd=str(fx["REPO"]))
    out = None
    for line in (p.stdout or "").splitlines():
        if line.startswith("@@RESULT@@"):
            out = json.loads(line[10:])
    return {"rc": p.returncode, "stdout_tail": (p.stdout or "")[-900:],
            "stderr_tail": (p.stderr or "")[-2000:], "result": out,
            "sentinel_log": log}


def audit_count(fx) -> int:
    a = fx["work"] / "fake-codex-audit.jsonl"
    if not a.exists():
        return 0
    return sum(1 for _ in a.open())


def audit_entries(fx):
    a = fx["work"] / "fake-codex-audit.jsonl"
    if not a.exists():
        return []
    return [json.loads(l) for l in a.read_text().splitlines() if l.strip()]


def ev_dir(fx, slot_id):
    return fx["CODEX"] / "runs" / slot_id


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snap", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--only", default=None)
    a = ap.parse_args()
    snap = Path(a.snap).resolve()
    out_dir = Path(a.out) if a.out else (HARNESS / "results" / snap.name)
    work = Path("/tmp/judge-l4/fixture-codex-" + snap.name.split("-", 1)[-1])
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    fx = build_fixture(snap, work, trees=("codex",))
    fx["work"] = work
    for rel in ("preflight/codex-preflight.json", "halt.json", "runs"):
        p = fx["CODEX"] / rel
        shutil.rmtree(p, ignore_errors=True) if p.is_dir() else (
            p.unlink(missing_ok=True))
    SLOTS = ["l4-20261029-cli-codex-dabstep-payments-10-r%d" % i for i in (1, 2, 3)] + \
            ["l4-20261029-cli-codex-tb-cargo-plan-r%d" % i for i in (1, 2, 3)]
    cases, only = {}, (set(a.only.split(",")) if a.only else None)

    def rec(name, verdict, detail):
        cases[name] = {"verdict": verdict, "detail": detail}

    def run_case(n):
        return (only is None) or (n in only)

    # ---- CX1 E-block ----
    if run_case("CX1_e_seal_block"):
        fx["binding"](False)
        r = run_inproc(fx, SLOTS[0], ["run", SLOTS[0]])
        res = r.get("result") or {}
        rec("CX1_e_seal_block", "pass" if (res.get("rc") in (2, 3)
                                           and res.get("audit_invocations") == 0
                                           and not (ev_dir(fx, SLOTS[0]) / "claim.json").exists())
            else "fail",
            {"lab_rc": res.get("rc"), "audit_invocations": res.get("audit_invocations"),
             "stdout_tail": r["stdout_tail"][-200:]})

    # ---- CX2 happy 全链 ----
    if run_case("CX2_happy_full_chain"):
        fx["binding"](True)
        r0 = run_inproc(fx, SLOTS[0], ["prepare", SLOTS[0]])
        # live CODEX_HOME/config.toml = 封存快照字节（preflight 的机械职责，harness 代行）
        sealed = fx["CODEX"] / "config" / "codex-config.toml"
        live = fx["home"] / "bench-workspaces" / "l4-20261029-cli" / "codex" / "_codex-home" / "config.toml"
        live.parent.mkdir(parents=True, exist_ok=True)
        import shutil as _sh
        _sh.copyfile(sealed, live)
        r = run_inproc(fx, SLOTS[0], ["run", SLOTS[0]])
        res = r.get("result") or {}
        ev = ev_dir(fx, SLOTS[0])
        meta = json.loads((ev / "meta.json").read_text()) if (ev / "meta.json").exists() else {}
        need = ["claim.json", "prompt.txt", "agent.jsonl", "agent.jsonl.sha256",
                "agent.stderr.txt", "session-capture.json", "score-receipt.json",
                "checker.stdout", "meta.json", "termination.json", "config-snapshot",
                "dual-archive.status.json"]
        missing = [f for f in need if not (ev / f).exists()]
        cap = json.loads((ev / "session-capture.json").read_text()) if (ev / "session-capture.json").exists() else {}
        usage = meta.get("usage") or {}
        per = usage.get("per_call") or []
        presence_states = set()
        for c in per:
            for st in (c.get("usage_presence") or {}).values():
                presence_states.add(st)
        ents = audit_entries(fx)
        all_fake = all(str(e.get("resolved_self", "")).endswith("/bin/codex") for e in ents)
        rec("CX2_happy_full_chain", "pass" if (r["rc"] == 0 and res.get("rc") == 0
                                               and meta.get("status") == "ok"
                                               and meta.get("registered_at") == fx["tE"]
                                               and not missing and len(per) == 3
                                               and cap.get("matched_by") == "session_meta.cwd==workspace"
                                               and len(cap.get("matched", [])) == 1
                                               and all_fake
                                               and isinstance(meta.get("reward"), int)) else "fail",
            {"prepare_rc": r0.get("result", {}).get("rc"), "run_rc": res.get("rc"),
             "status": meta.get("status"), "registered_at_ok": meta.get("registered_at") == fx["tE"],
             "missing_evidence": missing, "usage_calls": len(per),
             "presence_states": sorted(presence_states),
             "capture_matched": len(cap.get("matched", [])),
             "reward": meta.get("reward"), "reward_is_int": isinstance(meta.get("reward"), int),
             "attempts_identity": (meta.get("attempts") or [{}])[0],
             "all_invocations_fake": all_fake, "audit_n": len(ents),
             "formal_eligible": meta.get("runner_formal_eligible"),
             "stderr_tail": r["stderr_tail"][-1200:]})

    # ---- CX3 重复 run 零 dispatch ----
    if run_case("CX3_repeat_zero_dispatch"):
        n0 = audit_count(fx)
        r = run_inproc(fx, SLOTS[0], ["run", SLOTS[0]])
        res = r.get("result") or {}
        rec("CX3_repeat_zero_dispatch", "pass" if (r["rc"] != 0
                                                   and audit_count(fx) == n0) else "fail",
            {"rc": r["rc"], "audit_before": n0, "audit_after": audit_count(fx),
             "stderr_tail": r["stderr_tail"][-300:]})

    # ---- CX4 崩溃 claim 拒绝 ----
    if run_case("CX4_crash_claim_refuse"):
        ev2 = ev_dir(fx, SLOTS[1])
        ev2.mkdir(parents=True, exist_ok=True)
        (ev2 / "claim.json").write_text('{"crashed": true, "note": "judge fixture"}\n')
        n0 = audit_count(fx)
        r = run_inproc(fx, SLOTS[1], ["run", SLOTS[1]])
        rec("CX4_crash_claim_refuse", "pass" if (r["rc"] != 0
                                                 and audit_count(fx) == n0) else "fail",
            {"rc": r["rc"], "audit_after": audit_count(fx),
             "stderr_tail": r["stderr_tail"][-300:]})

    # ---- CX5 配置漂移 ----
    if run_case("CX5_config_drift"):
        cfg = fx["home"] / "bench-workspaces" / "l4-20261029-cli" / "codex" / "_codex-home" / "config.toml"
        orig = cfg.read_bytes()
        cfg.write_bytes(orig + b"\n# tampered by judge\n")
        n0 = audit_count(fx)
        claim_p = ev_dir(fx, SLOTS[1]) / "claim.json"
        claim_inode = claim_p.stat().st_ino if claim_p.exists() else None
        r = run_inproc(fx, SLOTS[1], ["run", SLOTS[1]])
        cfg.write_bytes(orig)
        claim_now = claim_p.stat().st_ino if claim_p.exists() else None
        claim_untouched = claim_inode == claim_now  # 前序 happy 场合法 claim 允许在位；本次不得新建/改写
        res5 = r.get("result") or {}
        refused = (res5.get("rc") not in (0, None)) or ("GateError" in (r["stderr_tail"] or ""))
        rec("CX5_config_drift", "pass" if (refused and audit_count(fx) == n0
                                           and claim_untouched) else "fail",
            {"lab_rc": res5.get("rc"), "audit_after": audit_count(fx),
             "audit_delta": audit_count(fx) - n0, "claim_untouched": claim_untouched,
             "proc_rc": r["rc"], "gate_error_in_stderr": "GateError" in (r["stderr_tail"] or ""),
             "note": "fail-closed 拒绝即达标；未捕获 GateError→rc=1 traceback 属 runner 抛错面 polishing 项",
             "stdout_tail": r["stdout_tail"][-300:], "stderr_tail": r["stderr_tail"][-400:]})

    # ---- CX6/CX7 超时夹具（真实 plan 时限 1800/2400s 不可等待；synthetic planF=4s）----
    if run_case("CX6_timeout_verified") or run_case("CX7_term_ignore_sigkill_chain"):
        import copy as _copy
        planF = _copy.deepcopy(json.loads((snap / "plan.json").read_text()))
        for sl in planF["product_slots"]:
            if sl["product"] == "codex":
                sl["timeout_s"] = 4
        workF = Path("/tmp/judge-l4/fixture-codexF-" + snap.name.split("-", 1)[-1])
        if workF.exists():
            shutil.rmtree(workF)
        workF.mkdir(parents=True)
        fxF = build_fixture(snap, workF, plan_override=planF, trees=("codex",))
        for rel in ("preflight/codex-preflight.json", "halt.json", "runs"):
            pp = fxF["CODEX"] / rel
            shutil.rmtree(pp, ignore_errors=True) if pp.is_dir() else pp.unlink(missing_ok=True)
        (workF / "fake-codex-audit.jsonl").touch()
        fxF["work"] = workF
        sealed = fxF["CODEX"] / "config" / "codex-config.toml"
        live = fxF["home"] / "bench-workspaces" / "l4-20261029-cli" / "codex" / "_codex-home" / "config.toml"
        live.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(sealed, live)

    if run_case("CX6_timeout_verified"):
        fxF["binding"](True)
        run_inproc(fxF, SLOTS[2], ["prepare", SLOTS[2]])
        r = run_inproc(fxF, SLOTS[2], ["run", SLOTS[2]],
                       env_extra={"FX_MODE": "sleep"}, timeout=180)
        res = r.get("result") or {}
        ev = ev_dir(fxF, SLOTS[2])
        meta = json.loads((ev / "meta.json").read_text()) if (ev / "meta.json").exists() else {}
        term = meta.get("termination") or {}
        stdout_raw = ev / "stdout.raw"
        rec("CX6_timeout_verified", "pass" if (meta.get("status") == "timeout"
                                               and term.get("phase") == "timeout"
                                               and meta.get("timed_out") is True
                                               and meta.get("runner_formal_eligible") is False
                                               and (fxF["CODEX"] / "halt.json").exists()) else "fail",
            {"status": meta.get("status"), "term_phase": term.get("phase"),
             "term_delivery": term.get("term_delivery"), "probe": term.get("probe"),
             "verified": term.get("verified"), "formal": meta.get("runner_formal_eligible"),
             "judge_role": meta.get("judge_role"),
             "checker_ran_despite_unverified": bool(meta.get("judge")),
             "criterion_note": "lead 纪律：unverified 停止 → formal=false+停批；"
                               "checker 是否应 0 调用=待 builder 修（b3 现先判后标）",
             "rc": r["rc"], "res": res,
             "stdout_tail": r["stdout_tail"][-400:], "stderr_tail": r["stderr_tail"][-600:],
             "stdout_raw_bytes": stdout_raw.stat().st_size if stdout_raw.exists() else 0})

    # ---- CX7 TERM-忽略 → SIGKILL 升级链 ----
    if run_case("CX7_term_ignore_sigkill_chain"):
        (fxF["CODEX"] / "halt.json").unlink(missing_ok=True)  # CX6 的停批解除（lead 处置模拟）
        run_inproc(fxF, SLOTS[0], ["prepare", SLOTS[0]])
        r = run_inproc(fxF, SLOTS[0], ["run", SLOTS[0]],
                       env_extra={"FX_MODE": "trap"}, timeout=180)
        res = r.get("result") or {}
        ev = ev_dir(fxF, SLOTS[0])
        meta = json.loads((ev / "meta.json").read_text()) if (ev / "meta.json").exists() else {}
        term = meta.get("termination") or {}
        sigkill_up = str(term.get("term_delivery", "")).endswith("SIGKILL")
        rec("CX7_term_ignore_sigkill_chain", "pass" if (meta.get("status") == "timeout"
                                                        and sigkill_up
                                                        and meta.get("runner_formal_eligible") is False
                                                        and (fxF["CODEX"] / "halt.json").exists()) else "fail",
            {"status": meta.get("status"), "term_delivery": term.get("term_delivery"),
             "probe": term.get("probe"), "verified": term.get("verified"),
             "formal": meta.get("runner_formal_eligible"),
             "rc": r["rc"], "res": res,
             "stdout_tail": r["stdout_tail"][-400:], "stderr_tail": r["stderr_tail"][-600:],
             "probe_race_note": "probe=still_alive_after_kill：SIGKILL 后立即 killpg(0) 竞态"
                                "（异步终止未及收割）→ 保守 verified=false；建议 kill 后短 settle 再探",
             "note": "TERM→grace→SIGKILL→探活；verified=false 保守拒 formal 正确方向"})

    # ---- CX8 halt 停批 gate ----
    if run_case("CX8_halt_gate_blocks_next"):
        jdump(fx["CODEX"] / "halt.json", {"slot": SLOTS[3], "at": now_marker(),
                                          "reason": "judge fixture: simulate unverified-stop halt"})
        n0 = audit_count(fx)
        r = run_inproc(fx, SLOTS[4], ["run", SLOTS[4]])
        (fx["CODEX"] / "halt.json").unlink(missing_ok=True)
        res8 = r.get("result") or {}
        rec("CX8_halt_gate_blocks_next", "pass" if (res8.get("rc") not in (0, None)
                                                    and audit_count(fx) == n0
                                                    and (fx["CODEX"] / "halt.json").exists() is False) else "fail",
            {"lab_rc": res8.get("rc"), "audit_delta": audit_count(fx) - n0,
             "stdout_tail": r["stdout_tail"][-400:],
             "stderr_tail": r["stderr_tail"][-400:]})

    # ---- CX9 停批解除后续槽正常 ----
    if run_case("CX9_resume_after_halt_cleared"):
        r = run_inproc(fx, SLOTS[4], ["prepare", SLOTS[4]])
        r = run_inproc(fx, SLOTS[4], ["run", SLOTS[4]])
        res = r.get("result") or {}
        meta_p = ev_dir(fx, SLOTS[4]) / "meta.json"
        meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
        rec("CX9_resume_after_halt_cleared", "pass" if (res.get("rc") == 0
                                                        and meta.get("status") == "ok") else "fail",
            {"rc": res.get("rc"), "status": meta.get("status"),
             "stdout_tail": r["stdout_tail"][-300:], "stderr_tail": r["stderr_tail"][-500:]})

    # ---- CX10 admission 组件（诊断）----
    if run_case("CX10_admission_diagnostic"):
        r = run_inproc(fx, SLOTS[5], ["prepare", SLOTS[5]])
        script = r'''
import importlib.util, json, sys
gate_p, bp, repo, l4 = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
spec = importlib.util.spec_from_file_location("g", gate_p)
g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
try:
    adm = g.gate_admission(bp, "codex", repo=__import__("pathlib").Path(repo),
                           plan_dir=__import__("pathlib").Path(l4))
    print("@@RESULT@@" + json.dumps(adm, ensure_ascii=False, default=str)[:6000])
except Exception as e:
    print("@@RESULT@@" + json.dumps({"error": repr(e)[:800]}))
'''
        from l4_fixture import write_sentinel
        write_sentinel(fx["sentinel_lib"])
        env = dict(os.environ, HOME=str(fx["home"]), PYTHONPATH=str(fx["sentinel_lib"]),
                   PYTHONDONTWRITEBYTECODE="1")
        p = subprocess.run([sys.executable, "-c", script, str(fx["sentinel_lib"].parent.parent / "repo" / "1-评测方案" / "工具链" / "l4-execution" / "gate.py"),
                            str(fx["L4"] / "runtime-binding.json"), str(fx["REPO"]), str(fx["L4"])],
                           capture_output=True, text=True, env=env, timeout=300)
        adm = None
        for line in (p.stdout or "").splitlines():
            if line.startswith("@@RESULT@@"):
                adm = json.loads(line[10:])
        rec("CX10_admission_diagnostic", "evidence", {"gate_admission": adm,
                                                      "note": "诊断性：fake 会话/桩证据下逐项 fails 全量留档，不判 pass/fail"})

    # ---- CX11 orphan：父正常退出+同组子忽略TERM持续写（lead 指定回归）----
    if run_case("CX11_orphan_samegroup_counter"):
        counter = work / "orphan-counter.txt"
        counter.unlink(missing_ok=True)
        (fx["CODEX"] / "halt.json").unlink(missing_ok=True)
        r = run_inproc(fx, SLOTS[5], ["prepare", SLOTS[5]])
        r = run_inproc(fx, SLOTS[5], ["run", SLOTS[5]],
                       env_extra={"FX_MODE": "orphan",
                                  "FX_ORPHAN_COUNTER": str(counter)}, timeout=300)
        res = r.get("result") or {}
        ev = ev_dir(fx, SLOTS[5])
        meta = json.loads((ev / "meta.json").read_text()) if (ev / "meta.json").exists() else {}
        term = meta.get("termination") or {}
        term_file = None
        for cand in ("termination-receipt.json", "termination.json"):
            if (ev / cand).exists():
                term_file = json.loads((ev / cand).read_text())
                break
        time.sleep(1.5)
        lines_now = sum(1 for _ in counter.open()) if counter.exists() else 0
        time.sleep(2.0)
        lines_late = sum(1 for _ in counter.open()) if counter.exists() else 0
        still_writing = lines_late > lines_now
        child_meta = {}
        cm = Path(str(counter) + ".meta")
        if cm.exists():
            child_meta = json.loads(cm.read_text())
        ents = [e for e in audit_entries(fx) if e.get("mode") == "orphan"]
        spawn_pgid = ents[-1]["spawn_pgid"] if ents else None
        saved = term.get("saved_pgid") or (term_file or {}).get("saved_pgid")
        same_group = (saved == spawn_pgid) if (saved and spawn_pgid) else None
        verdict = "evidence"
        detail = {"status": meta.get("status"),
                  "termination_phase": term.get("phase"),
                  "termination_verified": term.get("verified"),
                  "probe": term.get("probe"),
                  "term_delivery": term.get("term_delivery"),
                  "saved_pgid": saved, "spawn_pgid": spawn_pgid,
                  "same_group": same_group,
                  "formal_eligible": meta.get("runner_formal_eligible"),
                  "child_meta": child_meta,
                  "counter_lines_now": lines_now, "counter_lines_late": lines_late,
                  "child_still_writing_after_run": still_writing,
                  "halt_written": (fx["CODEX"] / "halt.json").exists(),
                  "criterion": "组仍存活（counter 增长）时 verified 不得为 true；"
                               "saved_pgid 须与 spawn 同组；是否 formal/停批按 lead 纪律"}
        if still_writing and term.get("verified") is True:
            verdict = "fail"
        rec("CX11_orphan_samegroup_counter", verdict, detail)

    # ---- 哨兵/audit 汇总 ----
    slog = fx["sentinel_lib"].parent / "sentinel-codex.log"
    non_local = sum(1 for l in slog.read_text().splitlines() if "allowed=False" in l) \
        if slog.exists() else -1
    ents = audit_entries(fx)
    receipt = {
        "kind": "judge_fake_e2e_receipt", "harness": "codex_fake_e2e.py",
        "harness_sha256": sha_file(HARNESS / "codex_fake_e2e.py"),
        "fake_codex_sha256": sha_file(HARNESS / "fake_codex.py"),
        "snapshot": str(snap),
        "snapshot_head_shas": {n: sha_file(snap / n) for n in
                               ("src-codex/tools/lab.py", "plan.json", "contract.json",
                                "gate.py", "execution_seal.py")},
        "fixture_repo": str(fx["REPO"]), "binding_E": fx["E"], "registered_at": fx["tE"],
        "generated_at": now_marker(), "cases": cases,
        "zero_real_cli_evidence": {"audit_entries": len(ents),
                                   "all_argv_fake": all(str(e.get("resolved_self", "")).endswith("/bin/codex")
                                                        for e in ents),
                                   "sentinel_non_local_attempts": non_local,
                                   "method": "lab.CODEX_BIN 绝对路径注入；preflight 类仅受限 PATH"
                                             "（无 /opt/homebrew/bin）；真实 codex 在"
                                             " /opt/homebrew/bin/codex 存在（事故向量）——全程未触"},
        "live_doc_drift": None,
    }
    outp = out_dir / "codex-fake-e2e-receipt.json"
    if outp.exists():
        outp = out_dir / ("codex-fake-e2e-receipt.%d.json" % int(time.time()))
    jdump(outp, receipt)
    print(json.dumps({"receipt": str(outp),
                      "verdicts": {k: v["verdict"] for k, v in cases.items()},
                      "zero_real_cli": receipt["zero_real_cli_evidence"]},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
