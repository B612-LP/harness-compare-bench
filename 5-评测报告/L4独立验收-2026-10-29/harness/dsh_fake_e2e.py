#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dsh_fake_e2e.py — judge 独立 L4 DSH runner fake e2e harness（候选 2a378846+）。

方法：受控子进程 import 真实 lab，注入 MOCK_CMD=fake_dsh（桩审计 resolved 证据）、
CASE_ROOT/WS_BASE/STAGING/DISPATCH 重定向到 fixture；哨兵封网；不替换待测函数。
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from l4_fixture import build_fixture, write_sentinel, jdump, sha_file  # noqa: E402

TZ8 = dt.timezone(dt.timedelta(hours=8))
HARNESS = Path(__file__).resolve().parent


def now_iso() -> str:
    return dt.datetime.now(TZ8).isoformat(timespec="seconds")


INPROC = r'''
import importlib.util, json, sys, os
from pathlib import Path
MARK = "@@RESULT@@"
lab_path, slot, fxj, extra_j = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
fx = json.loads(fxj); extra = json.loads(extra_j)
spec = importlib.util.spec_from_file_location("l4dsh", lab_path)
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)
lab.MOCK_CMD = [sys.executable, fx["fake_dsh"]]
lab.MOCK_EXTRA_ENV = dict(os.environ)
lab.CASE_ROOT = Path(fx["CASE"])
lab.WS_BASE = Path(fx["WS_BASE"])
lab.STAGING_ROOT = Path(fx["STAGING"])
lab.DISPATCH_ROOT = Path(fx["DISPATCH"])
audit_path = os.environ.get("FAKE_DSH_AUDIT", "")
if audit_path:
    open(audit_path, "a").close()
n0 = sum(1 for _ in open(audit_path)) if os.path.exists(audit_path) else 0
rc = None
err = None
try:
    rc = lab.main(extra["args"])
except SystemExit as e:
    rc = e.code
except Exception as e:
    err = repr(e)[:400]
n1 = sum(1 for _ in open(audit_path)) if os.path.exists(audit_path) else 0
out = {"rc": rc, "err": err, "audit_delta": n1 - n0,
       "halt": os.path.exists(fx["halt"])}
print(MARK + json.dumps(out, ensure_ascii=False))
'''


def run_inproc(fx, slot, args, env_extra=None, timeout=600):
    write_sentinel(fx["sentinel_lib"])
    log = fx["work"] / "sentinel-dsh.log"
    log.touch()
    env = dict(os.environ, HOME=str(fx["home"]),
               FAKE_DSH_AUDIT=str(fx["work"] / "fake-dsh-audit.jsonl"),
               JUDGE_SENTINEL_LOG=str(log), PYTHONDONTWRITEBYTECODE="1")
    env.update(env_extra or {})
    fx_pub = {"fake_dsh": str(HARNESS / "fake_dsh.py"), "CASE": str(fx["CASE"]),
              "WS_BASE": str(fx["home"] / "bench-workspaces" / "l4-20261029" / "dsh"),
              "STAGING": str(fx["work"] / "staging"),
              "DISPATCH": str(fx["work"] / "dispatch"),
              "halt": str(fx["DSH"] / "halt.json")}
    p = subprocess.run([sys.executable, "-c", INPROC, str(fx["DSH"] / "tools" / "lab.py"),
                        slot, json.dumps(fx_pub), json.dumps({"args": args})],
                       capture_output=True, text=True, env=env, timeout=timeout,
                       cwd=str(fx["REPO"]))
    out = None
    for line in (p.stdout or "").splitlines():
        if line.startswith("@@RESULT@@"):
            out = json.loads(line[10:])
    return {"rc": p.returncode, "stdout_tail": (p.stdout or "")[-900:],
            "stderr_tail": (p.stderr or "")[-1600:], "result": out,
            "sentinel_log": log}


def audit_count(fx):
    a = fx["work"] / "fake-dsh-audit.jsonl"
    return sum(1 for _ in a.open()) if a.exists() else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snap", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--only", default=None)
    a = ap.parse_args()
    snap = Path(a.snap).resolve()
    out_dir = Path(a.out) if a.out else (HARNESS / "results" / snap.name)
    work = Path("/tmp/judge-l4/fixture-dsh-" + snap.name.split("-", 1)[-1])
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    fx = build_fixture(snap, work, trees=("dsh",))
    fx["work"] = work
    fx["DSH"] = fx["REPO"] / "3-表现现场" / "l4-20261029-cli" / "dsh"
    for rel in ("runs", "halt.json", "preflight", "selftest"):
        p = fx["DSH"] / rel
        shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
    SLOTS = ["l4-20261029-cli-dsh-dabstep-payments-10-r%d" % i for i in (1, 2, 3)] + \
            ["l4-20261029-cli-dsh-tb-cargo-plan-r%d" % i for i in (1, 2, 3)]
    cases, only = {}, (set(a.only.split(",")) if a.only else None)

    def rec(name, verdict, detail):
        cases[name] = {"verdict": verdict, "detail": detail}

    def run_case(n):
        return (only is None) or (n in only)

    # ---- S1 E-block ----
    if run_case("S1_e_seal_block"):
        fx["binding"](False)
        r = run_inproc(fx, SLOTS[0], ["run", "--slot", SLOTS[0]])
        res = r.get("result") or {}
        disp = list((fx["work"] / "dispatch").glob("*")) if (fx["work"] / "dispatch").exists() else []
        refused = (res.get("rc") not in (0, None)) or bool(res.get("err"))
        rec("S1_e_seal_block", "pass" if refused
            and res.get("audit_delta") == 0 and not disp else "fail",
            {"rc": res.get("rc"), "err": res.get("err"),
             "audit_delta": res.get("audit_delta"), "dispatch_files": len(disp),
             "stdout_tail": r["stdout_tail"][-300:]})

    # ---- S2 happy + S8 gate 正例 ----
    if run_case("S2_happy_full_chain"):
        fx["binding"](True)
        r = run_inproc(fx, SLOTS[0], ["run", "--slot", SLOTS[0]])
        res = r.get("result") or {}
        ev = fx["DSH"] / "runs" / SLOTS[0]
        meta = json.loads((ev / "meta.json").read_text()) if (ev / "meta.json").exists() else {}
        att = (meta.get("attempts") or [{}])[0]
        usage = meta.get("usage") or {}
        sess = ev / "agent-session"
        ok_flags = {
            "rc0": res.get("rc") == 0,
            "status_ok": meta.get("status") == "ok",
            "attempts_identity": isinstance(att.get("pid"), int) and isinstance(att.get("pgid"), int),
            "inputs_ver_ok": (meta.get("inputs_verification") or {}).get("ok") is True,
            "usage_calls": len(usage.get("per_call") or []) >= 1,
            "session_captured": sess.is_dir() and any(sess.iterdir()),
            "dispatch_exists": (fx["work"] / "dispatch" / (SLOTS[0] + ".json")).exists(),
            "reward_int": isinstance(meta.get("reward"), int),
        }
        rec("S2_happy_full_chain", "pass" if all(ok_flags.values()) else "fail",
            dict(ok_flags, meta_status=meta.get("status"),
                 reward=meta.get("reward"), weighted=meta.get("weighted"),
                 registered_at_ok=meta.get("registered_at") == fx["tE"],
                 stderr_tail=r["stderr_tail"][-400:]))

    if run_case("S8_gate_admission_positive"):
        fx["binding"](True)
        adm = run_gate_admission(fx)
        per = [x for x in adm.get("per_slot", []) if x.get("slot_id") == SLOTS[0]]
        per = (per or adm.get("per_slot", [{}]))[0]
        rec("S8_gate_admission_positive", "evidence",
            {"slot": per.get("slot_id"), "formal": per.get("formal_admission"),
             "fails": per.get("fails", []),
             "criterion": "正常 CLI completed（exit0 全证据）应 formal=true；"
                          "fails 即剩余缺口清单"})

    # ---- S3 low-score（checker exit1=能力低分非 infra）----
    if run_case("S3_low_score_admitted"):
        r = run_inproc(fx, SLOTS[1], ["run", "--slot", SLOTS[1]],
                       env_extra={"FAKE_DSH_WRITE": "wrong.txt"})
        res = r.get("result") or {}
        ev = fx["DSH"] / "runs" / SLOTS[1]
        meta = json.loads((ev / "meta.json").read_text()) if (ev / "meta.json").exists() else {}
        rec("S3_low_score_admitted", "pass" if (res.get("rc") == 0
                                                and meta.get("status") == "ok"
                                                and meta.get("reward") == 0
                                                and (meta.get("accounting") or meta).get("status") is not None) else "fail",
            {"rc": res.get("rc"), "status": meta.get("status"),
             "reward": meta.get("reward"),
             "accounting": meta.get("accounting"),
             "stderr_tail": r["stderr_tail"][-300:]})

    # ---- S4 重复 dispatch 零外发 ----
    if run_case("S4_repeat_zero_dispatch"):
        n0 = audit_count(fx)
        r = run_inproc(fx, SLOTS[0], ["run", "--slot", SLOTS[0]])
        res = r.get("result") or {}
        rec("S4_repeat_zero_dispatch", "pass" if (res.get("audit_delta") == 0
                                                  and (res.get("rc") not in (0, None) or res.get("err"))) else "fail",
            {"rc": res.get("rc"), "err": res.get("err"),
             "audit_delta": res.get("audit_delta"),
             "stdout_tail": r["stdout_tail"][-300:]})

    # ---- S5/S6 超时夹具（planF timeout=4s）----
    need_f = run_case("S5_timeout_verified_evidence") or run_case("S6_orphan_detached_writer")
    if need_f:
        planF = copy.deepcopy(json.loads((snap / "plan.json").read_text()))
        for sl in planF["product_slots"]:
            if sl["product"] == "dsh":
                sl["timeout_s"] = 4
        workF = Path("/tmp/judge-l4/fixture-dshF-" + snap.name.split("-", 1)[-1])
        if workF.exists():
            shutil.rmtree(workF)
        workF.mkdir(parents=True)
        fxF = build_fixture(snap, workF, plan_override=planF, trees=("dsh",))
        fxF["work"] = workF
        fxF["DSH"] = fxF["REPO"] / "3-表现现场" / "l4-20261029-cli" / "dsh"
        for rel in ("runs", "halt.json", "preflight", "selftest"):
            pp = fxF["DSH"] / rel
            shutil.rmtree(pp, ignore_errors=True) if pp.is_dir() else pp.unlink(missing_ok=True)
        fxF["binding"](True)

    if run_case("S5_timeout_verified_evidence"):
        r = run_inproc(fxF, SLOTS[2], ["run", "--slot", SLOTS[2]],
                       env_extra={"FAKE_DSH_SLEEP": "30"}, timeout=300)
        res = r.get("result") or {}
        ev = fxF["DSH"] / "runs" / SLOTS[2]
        meta = json.loads((ev / "meta.json").read_text()) if (ev / "meta.json").exists() else {}
        tr = ev / "termination-receipt.json"
        tdoc = json.loads(tr.read_text()) if tr.exists() else {}
        score_null = meta.get("weighted") is None or meta.get("status") == "timeout"
        rec("S5_timeout_verified_evidence", "evidence",
            {"status": meta.get("status"), "timed_out": meta.get("timed_out"),
             "term_verified_stop": tdoc.get("verified_stop"),
             "term_signal": tdoc.get("signal"),
             "term_has_pgid": isinstance(tdoc.get("pgid"), int),
             "scored_despite_timeout": meta.get("weighted") is not None,
             "accounting": meta.get("accounting"),
             "halt": res.get("halt"),
             "criterion": "verified 停止→完整 timeout 判卷可准入；unverified→partial+checker0+halt"})

    if run_case("S6_orphan_detached_writer"):
        # 写者落在 slot workspace 内（runner 探针按设计只看本槽 ws；组外写者须可被双采样看见）
        counter = Path("orphan-detached.txt")  # 相对 Popen cwd=ws
        ws6 = fxF["home"] / "bench-workspaces" / "l4-20261029" / "dsh" / SLOTS[3]
        (ws6 / "orphan-detached.txt").unlink(missing_ok=True)
        r = run_inproc(fxF, SLOTS[3], ["run", "--slot", SLOTS[3]],
                       env_extra={"FAKE_DSH_ORPHAN_COUNTER": str(counter),
                                  "FAKE_DSH_ORPHAN_SETSID": "1"}, timeout=300)
        res = r.get("result") or {}
        time.sleep(0.2)
        n1 = sum(1 for _ in (ws6 / "orphan-detached.txt").open()) if (ws6 / "orphan-detached.txt").exists() else 0
        time.sleep(1.2)
        n2 = sum(1 for _ in (ws6 / "orphan-detached.txt").open()) if (ws6 / "orphan-detached.txt").exists() else 0
        ev = fxF["DSH"] / "runs" / SLOTS[3]
        meta = json.loads((ev / "meta.json").read_text()) if (ev / "meta.json").exists() else {}
        att = (meta.get("attempts") or [{}])[0]
        closure = att.get("closure") or meta.get("closure") or {}
        rp = closure.get("residual_probe") or {}
        rd = closure.get("residual_disclosure") or meta.get("residual_disclosure") or {}
        md = meta.get("residual_disclosure") or rd
        flags = {
            "writer_really_escaped": n2 > n1,
            "detected_by_two_sample": rp.get("still_growing") is True,
            "flipped_verified_stop_false": closure.get("verified_stop") is False,
            "unconfirmed_reason": ("residual workspace writer" in (closure.get("unconfirmed_reason") or "")),
            "pgid_scope_disclosed": ("launched pgid only" in json.dumps(md or closure))
                                     or ("setsid-escaped" in json.dumps(md or closure)),
            "host_guarantee_none": ("none" in json.dumps(md or closure)),
            "partial_not_formal": meta.get("score_status") in ("unscored-unverified-stop",)
                                  or meta.get("reward") is None,
            "no_score_receipt": not (ev / "score-receipt.json").exists(),
            "halt": bool(res.get("halt")),
        }
        rec("S6_orphan_detached_writer", "pass" if all(flags.values()) else "fail",
            dict(flags, status=meta.get("status"),
                 real_status_note=meta.get("diagnostic", {}).get("class") if isinstance(meta.get("diagnostic"), dict) else None,
                 residual_probe=rp, disclosure=(md or {}) if isinstance(md, dict) else {},
                 accounting=meta.get("accounting"),
                 stderr_tail=r["stderr_tail"][-300:],
                 criterion="setsid 脱组写者（judge 反例）须被停后双采样检出→翻转为 partial"
                           "（非 formal），且 metadata 披露 PGID 覆盖边界/host 全机无保证"))

    # ---- S7 输入漂移 ----
    if run_case("S7_input_drift_not_executed"):
        cfile = fx["CASE"] / "tb-cargo-plan" / "inputs" / "answer.txt"
        orig = cfile.read_bytes()
        cfile.write_bytes(orig + b"drift\n")
        r = run_inproc(fx, SLOTS[4], ["run", "--slot", SLOTS[4]])
        cfile.write_bytes(orig)
        res = r.get("result") or {}
        disp = (fx["work"] / "dispatch" / (SLOTS[4] + ".json")).exists()
        rec("S7_input_drift_not_executed", "pass" if (not disp and res.get("audit_delta") == 0) else "fail",
            {"dispatch_exists": disp, "audit_delta": res.get("audit_delta"),
             "rc": res.get("rc"), "stderr_tail": r["stderr_tail"][-300:]})

    slog = fx["work"] / "sentinel-dsh.log"
    non_local = sum(1 for l in slog.read_text().splitlines() if "allowed=False" in l) \
        if slog.exists() else -1
    receipt = {
        "kind": "judge_fake_e2e_receipt", "harness": "dsh_fake_e2e.py",
        "harness_sha256": sha_file(Path(__file__).resolve()),
        "fake_dsh_sha256": sha_file(HARNESS / "fake_dsh.py"),
        "snapshot": str(snap),
        "snapshot_head_shas": {n: sha_file(snap / n) for n in
                               ("src-dsh/tools/lab.py", "plan.json", "contract.json",
                                "gate.py", "execution_seal.py")},
        "fixture_repo": str(fx["REPO"]), "binding_E": fx["E"], "registered_at": fx["tE"],
        "generated_at": now_iso(), "cases": cases,
        "sentinel": {"non_local_attempts": non_local},
        "live_doc_drift": None,
    }
    outp = out_dir / "dsh-fake-e2e-receipt.json"
    if outp.exists():
        outp = out_dir / ("dsh-fake-e2e-receipt.%d.json" % int(time.time()))
    jdump(outp, receipt)
    print(json.dumps({"receipt": str(outp),
                      "verdicts": {k: v["verdict"] for k, v in cases.items()},
                      "sentinel_non_local": non_local}, ensure_ascii=False, indent=1))
    return 0


def run_gate_admission(fx):
    GATE_ADM = r"""
import importlib.util, json, sys
from pathlib import Path
MARK = "@@RESULT@@"
spec = importlib.util.spec_from_file_location("g", sys.argv[1])
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
try:
    adm = g.gate_admission(sys.argv[2], "dsh", repo=Path(sys.argv[3]), plan_dir=Path(sys.argv[4]))
    print(MARK + json.dumps(adm, ensure_ascii=False, default=str)[:9000])
except Exception as e:
    print(MARK + json.dumps({"error": repr(e)[:500]}))
"""
    write_sentinel(fx["sentinel_lib"])
    env = dict(os.environ, HOME=str(fx["home"]), PYTHONPATH=str(fx["sentinel_lib"]),
               JUDGE_SENTINEL_LOG=str(fx["work"] / "sentinel-adm.log"),
               PYTHONDONTWRITEBYTECODE="1")
    (fx["work"] / "sentinel-adm.log").touch()
    p = subprocess.run([sys.executable, "-c", GATE_ADM,
                        str(fx["REPO"] / "1-评测方案" / "工具链" / "l4-execution" / "gate.py"),
                        str(fx["L4"] / "runtime-binding.json"), str(fx["REPO"]),
                        str(fx["L4"])], capture_output=True, text=True, env=env, timeout=300)
    for line in (p.stdout or "").splitlines():
        if line.startswith("@@RESULT@@"):
            return json.loads(line[10:])
    return {"error": (p.stderr or "")[-400:]}


if __name__ == "__main__":
    sys.exit(main())
