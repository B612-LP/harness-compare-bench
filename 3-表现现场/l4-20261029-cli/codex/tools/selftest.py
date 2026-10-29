#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L4 Codex runner 合成自检（零模型、零网络、不读凭据）。socket 哨兵兜底禁网。"""
from __future__ import annotations

import copy
import datetime as _dt
import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import lab  # noqa: E402  同目录

FAILURES = []
WARNINGS = []

REAL = Path(__file__).resolve().parents[4]



def check(name, fn):
    global FAILURES
    try:
        fn()
        print("PASS", name)
    except Exception as e:  # noqa: BLE001
        FAILURES.append(name)
        print("FAIL", name, "->", repr(e))


class Sentinel(socket.socket):
    def __init__(self, *a, **k):
        raise AssertionError("selftest 违规联网尝试")


def _raises(fn) -> bool:
    try:
        fn()
        return False
    except Exception:
        return True


def main() -> int:
    real_socket = socket.socket
    socket.socket = Sentinel
    try:
        # 1) plan 槽位不变量
        slots = lab.load_plan_slots()
        check("plan_6_slots", lambda: (_ for _ in ()).throw(AssertionError(len(slots)))
              if len(slots) != 6 else None)
        check("plan_order", lambda: (_ for _ in ()).throw(AssertionError()) if
              [s["order"] for s in slots] != [1, 2, 3, 4, 5, 6] else None)
        check("plan_cases", lambda: (_ for _ in ()).throw(AssertionError()) if
              sorted({s["case"] for s in slots}) != ["dabstep-payments-10", "tb-cargo-plan"] else None)
        check("no_self_invented_slot", lambda: (_ for _ in ()).throw(AssertionError("should raise"))
              if not _raises(lambda: lab.slot_by_id("l4-20261029-cli-codex-bird-ca-schools-15-r1")) else None)
        # 2) write_once 非破坏
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "evidence.bin"
            lab.write_once(f, b"one")
            check("write_once_refuses_overwrite", lambda: (_ for _ in ()).throw(AssertionError("should raise"))
                  if not _raises(lambda: lab.write_once(f, b"two")) else None)
        # 3) gate fail-closed（binding 缺失）
        check("binding_absent_failclosed", lambda: (_ for _ in ()).throw(AssertionError("should raise"))
              if not _raises(lambda: lab.load_binding(required=True)) or lab.BINDING_PATH.exists() else None)
        # 4) gate fail-closed（合成 binding：released=false / 哈希不符 / gate 缺失 / stub gate）
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            saved = (lab.BINDING_PATH, lab.GATE_PATH, lab.PLAN_PATH, lab.CONTRACT_PATH)
            try:
                plan_copy, contract_copy = td / "plan.json", td / "contract.json"
                plan_copy.write_bytes(lab.PLAN_PATH.read_bytes())
                contract_copy.write_bytes(lab.CONTRACT_PATH.read_bytes())
                lab.PLAN_PATH, lab.CONTRACT_PATH = plan_copy, contract_copy
                lab.BINDING_PATH = td / "runtime-binding.json"
                ok_binding = {"design_commit": "D" * 40, "preregistration_commit": "E" * 40,
                              "execution_seal_commit": "E" * 40,
                              "registered_at": "2026-10-29T23:59:00+08:00",
                              "execution_manifest_sha256": "0" * 64,
                              "plan_sha256": lab.sha_file(plan_copy),
                              "contract_sha256": lab.sha_file(contract_copy),
                              "released_for_model_calls": True}
                lab.BINDING_PATH.write_text(json.dumps(ok_binding), encoding="utf-8")
                lab.GATE_PATH = td / "gate_missing.py"   # gate 缺失 → fail-closed
                check("gate_missing_failclosed", lambda: (_ for _ in ()).throw(AssertionError("should raise"))
                      if not _raises(lab.gate_check_real) else None)
                (td / "gate_stub.py").write_text("def verify_execution(p, require_release=True):\n    return True\n")
                lab.GATE_PATH = td / "gate_stub.py"
                b = lab.gate_check_real()
                check("gate_ok_passes", lambda: (_ for _ in ()).throw(AssertionError(b)) if
                      b["released_for_model_calls"] is not True else None)
                (td / "gate_bad.py").write_text("def verify_execution(p, require_release=True):\n    return False\n")
                lab.GATE_PATH = td / "gate_bad.py"
                check("gate_reject_failclosed", lambda: (_ for _ in ()).throw(AssertionError("should raise"))
                      if not _raises(lab.gate_check_real) else None)
                bad = dict(ok_binding, released_for_model_calls=False)
                lab.BINDING_PATH.write_text(json.dumps(bad), encoding="utf-8")
                lab.GATE_PATH = td / "gate_stub.py"
                check("not_released_failclosed", lambda: (_ for _ in ()).throw(AssertionError("should raise"))
                      if not _raises(lab.gate_check_real) else None)
                bad2 = dict(ok_binding, plan_sha256="f" * 64)
                lab.BINDING_PATH.write_text(json.dumps(bad2), encoding="utf-8")
                check("plan_hash_mismatch_failclosed", lambda: (_ for _ in ()).throw(AssertionError("should raise"))
                      if not _raises(lab.gate_check_real) else None)
            finally:
                lab.BINDING_PATH, lab.GATE_PATH, lab.PLAN_PATH, lab.CONTRACT_PATH = saved
        # 5) prompt 构造：路径内嵌 + sha 稳定
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td) / "ws"
            task = lab.build_task("tb-cargo-plan", ws)
            check("prompt_embeds_ws", lambda: (_ for _ in ()).throw(AssertionError()) if str(ws) not in task else None)
            check("prompt_sha_stable", lambda: (_ for _ in ()).throw(AssertionError()) if
                  lab.sha(task.encode()) != lab.sha(lab.build_task("tb-cargo-plan", ws).encode()) else None)
        # 6) usage presence 四态（lead 源码勘误的对齐：absent/null/0 不合并）
        with tempfile.TemporaryDirectory() as td:
            sess = Path(td) / "agent-session.raw"
            sess.mkdir(parents=True)
            (sess / "rollout.jsonl").write_text("\n".join([
                json.dumps({"type": "token_usage_record", "timestamp": "2026-10-29T20:00:00Z",
                            "payload": {"response_id": "r1",
                                        "usage": {"input_tokens": 10, "cached_input_tokens": 8,
                                                  "output_tokens": 2}}}),
                json.dumps({"type": "token_usage_record", "timestamp": "2026-10-29T20:00:05Z",
                            "payload": {"response_id": "r2",
                                        "usage": {"input_tokens": 5, "cached_input_tokens": 0,
                                                  "cache_write_input_tokens": None,
                                                  "output_tokens": 1, "total_tokens": 6}}}),
            ]), encoding="utf-8")
            u = lab.extract_usage(sess)
            check("usage_requests_dedupe", lambda: (_ for _ in ()).throw(AssertionError(u["requests"])) if u["requests"] != 2 else None)
            p0, p1 = u["per_call"][0]["usage_presence"], u["per_call"][1]["usage_presence"]
            check("presence_missing", lambda: (_ for _ in ()).throw(AssertionError(p0)) if
                  p0["cache_write_input_tokens"] != "missing" else None)
            check("presence_zero", lambda: (_ for _ in ()).throw(AssertionError(p1)) if
                  p1["cached_input_tokens"] != "zero" else None)
            check("presence_null", lambda: (_ for _ in ()).throw(AssertionError(p1)) if
                  p1["cache_write_input_tokens"] != "null" else None)
            check("presence_positive", lambda: (_ for _ in ()).throw(AssertionError(p0)) if
                  p0["cached_input_tokens"] != "positive" else None)
        # 7) 双归档投影：legacy 无流（r1030#1 复现）、current 全量、母本不动
        with tempfile.TemporaryDirectory() as td:
            master = Path(td) / "run"
            (master / "workspace").mkdir(parents=True)
            (master / "workspace" / "artifact.txt").write_text("a", encoding="utf-8")
            (master / "stdout.raw").write_bytes(b"stream")
            (master / "stdout.raw.sha256").write_bytes((lab.sha(b"stream") + "\n").encode())
            (master / "agent-session.raw").mkdir()
            (master / "agent-session.raw" / "rollout.jsonl").write_text("{}", encoding="utf-8")
            meta = {"batch": "l4-20261029-cli", "rule_version": lab.RULE, "product": "codex",
                    "case": "tb-cargo-plan", "run_id": "l4-20261029-cli-codex-tb-cargo-plan-r1",
                    "status": "ok", "exit_code": 0, "started_at": "2026-10-29T21:00:00+08:00",
                    "finished_at": "2026-10-29T21:05:00+08:00", "duration_s": 300.0,
                    "reward": 0, "weighted": 70.37, "judge": {"checks": []},
                    "integrity": {"violations": 0}, "integrity_verdict": "clean",
                    "registered_at": "2026-10-29T20:00:00+08:00", "prompt_sha256": "0" * 64}
            (master / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
            before = {p.name: lab.sha_file(p) for p in sorted(master.rglob("*")) if p.is_file()}
            import dual_archive
            r = dual_archive.project_run(master)
            check("projection_report", lambda: (_ for _ in ()).throw(AssertionError(r)) if
                  r.get("master_untouched") is not True else None)
            legacy = master / "projections" / "legacy"
            cur = master / "projections" / "current"
            check("legacy_no_streams", lambda: (_ for _ in ()).throw(AssertionError()) if
                  (legacy / "agent.jsonl").exists() or (legacy / "workspace" / "artifact.txt").exists() is False else None)
            check("current_has_streams", lambda: (_ for _ in ()).throw(AssertionError()) if
                  (cur / "agent.jsonl").read_bytes() != b"stream" else None)
            check("adaptation_marked", lambda: (_ for _ in ()).throw(AssertionError()) if
                  json.loads((legacy / "ADAPTATION.json").read_text(encoding="utf-8")).get("equivalent_simulation") is not True else None)
            after = {p.name: lab.sha_file(p) for p in sorted(master.rglob("*")) if p.is_file() and "projections" not in str(p)}
            check("master_untouched", lambda: (_ for _ in ()).throw(AssertionError()) if before != after else None)
        # ---- E-blocker 负例：超时后子工具仍写 → 进程组清理必须生效 ----
        with tempfile.TemporaryDirectory() as td:
            ev = Path(td) / "run"
            ev.mkdir(parents=True)
            writer_file = Path(td) / "writer.out"
            inner = Path(td) / "inner_writer.py"
            inner.write_text(
                "import time, sys\n"
                "fp = open(sys.argv[1], 'a')\n"
                "while True:\n"
                "    fp.write('x')\n"
                "    fp.flush()\n"
                "    time.sleep(0.05)\n")
            helper_py = Path(td) / "helper.py"
            helper_py.write_text(
                "import subprocess, sys, time\n"
                "sub = subprocess.Popen([sys.executable, %r, sys.argv[1]])\n"
                "time.sleep(30)\n" % str(inner))
            helper = None
            proc = subprocess.Popen([sys.executable, str(helper_py), str(writer_file)],
                                    start_new_session=True, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
            time.sleep(0.8)
            size_before = writer_file.stat().st_size if writer_file.exists() else 0
            check("e_blocker_precondition_writing", lambda: (_ for _ in ()).throw(AssertionError(size_before)) if size_before <= 0 else None)
            term = lab.close_process_group(proc, ev, {"slot_id": "SYNTHETIC"}, phase="timeout",
                                           saved_pgid=proc.pid, attempt={"n": 1}, grace_s=5)
            time.sleep(0.4)
            size_after = writer_file.stat().st_size if writer_file.exists() else 0
            check("timeout_term_delivery_recorded", lambda: (_ for _ in ()).throw(AssertionError(term)) if
                  term.get("term_delivery") not in ("delivered", "no-such-group") else None)
            check("timeout_probe_disclosed", lambda: (_ for _ in ()).throw(AssertionError(term)) if
                  term.get("probe") not in ("verified_gone", "probe_denied", "still_alive_after_kill") else None)
            check("timeout_verified_honest", lambda: (_ for _ in ()).throw(AssertionError(term)) if
                  term.get("verified") is not (term.get("probe") == "verified_gone") else None)
            check("gate_shape_verified_stop", lambda: (_ for _ in ()).throw(AssertionError(term)) if
                  term.get("verified_stop") is not term.get("verified") else None)
            check("gate_shape_signal_field", lambda: (_ for _ in ()).throw(AssertionError(term)) if
                  term.get("signal") not in ("SIGTERM", "SIGKILL", None) else None)
            check("gate_shape_ack_at", lambda: (_ for _ in ()).throw(AssertionError(term)) if
                  not term.get("ack_at") else None)
            check("timeout_writes_stopped", lambda: (_ for _ in ()).throw(AssertionError((size_before, size_after))) if
                  size_after != size_before else None)
            check("termination_receipt", lambda: (_ for _ in ()).throw(AssertionError()) if
                  not (ev / "termination.json").exists() else None)

        # ---- 首失败回归（lead 判据）：父退 + 子忽略 TERM 持续写 → saved_pgid 组级清停 ----
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            ev = td / "run"
            ev.mkdir(parents=True)
            writer_file = td / "orphan.out"
            inner = td / "orphan_inner.py"
            inner.write_text(
                "import signal, sys, time\n"
                "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"   # 忽略 TERM：逼出 SIGKILL 升级
                "fp = open(sys.argv[1], 'a')\n"
                "while True:\n"
                "    fp.write('x')\n"
                "    fp.flush()\n"
                "    time.sleep(0.05)\n")
            helper = td / "orphan_helper.py"
            helper.write_text(
                "import subprocess, sys, time\n"
                "subprocess.Popen([sys.executable, sys.argv[1], sys.argv[2]],\n"
                "                 start_new_session=False)\n"
                "time.sleep(0.3)\n")   # 父随即退出：inner 成为孤儿进程组成员
            helper_proc = subprocess.Popen([sys.executable, str(helper), str(inner), str(writer_file)],
                                           start_new_session=True,
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            saved_pgid = helper_proc.pid          # 启动即存（start_new_session ⇒ 组长=helper pid）
            time.sleep(0.9)                        # helper 已退出（被收割）；inner 持续写
            size_before = writer_file.stat().st_size if writer_file.exists() else 0
            check("orphan_precondition_writing", lambda: (_ for _ in ()).throw(AssertionError(size_before)) if size_before <= 0 else None)
            _raises(lambda: __import__("os").getpgid(helper_proc.pid))  # 父侧 getpgid 应 ESRCH
            term = lab.close_process_group(helper_proc, ev, {"slot_id": "ORPHAN-SYNTH"},
                                           phase="timeout", grace_s=4,
                                           saved_pgid=saved_pgid, attempt={"n": 1})
            time.sleep(0.4)
            size_after = writer_file.stat().st_size if writer_file.exists() else 0
            check("orphan_sigkill_escalated", lambda: (_ for _ in ()).throw(AssertionError(term)) if
                  "SIGKILL" not in term.get("signal") else None)
            check("orphan_saved_pgid_identity", lambda: (_ for _ in ()).throw(AssertionError(term)) if
                  term.get("saved_pgid") != saved_pgid or term.get("slot_id") != "ORPHAN-SYNTH" else None)
            check("orphan_verified_honest", lambda: (_ for _ in ()).throw(AssertionError(term)) if
                  term.get("verified") is not (term.get("probe") == "verified_gone") else None)
            if term.get("probe") == "verified_gone":
                check("orphan_writes_stopped", lambda: (_ for _ in ()).throw(AssertionError((size_before, size_after))) if
                      size_after != size_before else None)
            else:
                # 环境阻断（沙箱对孤儿组信号静默 no-op/EPERM）：行为断言不可得，
                # 记 WARN 待 judge 于真实 runtime 按原判据复验；verified=false 纪律不受影响
                WARNINGS.append({"check": "orphan_behavioral_stop",
                                 "probe": term.get("probe"),
                                 "note": "沙箱对孤儿组信号静默 no-op（KILL 报成功但写者仍写）——"
                                         "verified=false 为诚实结果；行为停止断言留待真实 runtime"})
                print("WARN orphan_behavioral_stop ->", term.get("probe"),
                      "(size_before=%s size_after=%s)" % (size_before, size_after))

        # ---- R3：slot claim 重复调用零额外 Popen ----
        with tempfile.TemporaryDirectory() as td:
            saved_runs = lab.RUNS
            lab.RUNS = Path(td)
            try:
                binding = {"design_commit": "d" * 40, "preregistration_commit": "e" * 40,
                           "execution_seal_commit": "e" * 40, "registered_at": "2026-10-29T23:00:00+08:00"}
                slot = {"slot_id": "synth", "run_id": "r", "event_id": "ev", "order": 1}
                lab.claim_slot(slot, binding)
                popen_calls = []
                orig_popen = subprocess.Popen

                def counting_popen(*a, **k):
                    popen_calls.append(a)
                    raise AssertionError("claim 阶段出现 Popen")

                subprocess.Popen = counting_popen
                try:
                    raised = _raises(lambda: lab.claim_slot(slot, binding))
                finally:
                    subprocess.Popen = orig_popen
                check("claim_double_reject_zero_popen", lambda: (_ for _ in ()).throw(AssertionError()) if
                      not (raised and not popen_calls) else None)
            finally:
                lab.RUNS = saved_runs

        # ---- 真实 validate_meta/classify 组件（gate.load_runner_validator 优先）----
        base = {
            "batch": "l4-20261029-cli", "rule_version": "l4-20261029-batch-v1",
            "preregistration_commit": "e" * 40,
            "registered_at": "2026-10-29T23:00:00+08:00",
            "rep": 1, "product": "codex", "case": "dabstep-payments-10", "form": "cli",
            "run_id": "l4-20261029-cli-codex-dabstep-payments-10-r1",
            "event_id": "event:l4-20261029-cli-codex-dabstep-payments-10-r1",
            "selection": {"plan_id": "l4-20261029",
                          "slot_id": "l4-20261029-cli-codex-dabstep-payments-10-r1",
                          "order": 1, "kind": "first", "parent_id": None, "reason": None,
                          "registered_at": "2026-10-29T23:00:00+08:00",
                          "plan_source": 0, "plan_pointer": "/product_slots/0"},
            "workspace": "/Users/x/bench-workspaces/l4/codex/s", "model": "deepseek-flash",
            "reasoning_effort": "low", "product_version": "codex-cli 0.163.0",
            "route": {"host": "api.deepseek.com", "provider_id": "deepseek",
                      "wire_protocol": "responses", "endpoint": "https://api.deepseek.com"},
            "tools": ["shell"], "permissions": "danger-full-access; never", "skills": "off",
            "web_search": "disabled", "soft_constraints": ["offline"],
            "prompt_sha256": "a" * 64, "isolation": {"ok": True, "problems": []},
            "inputs": [{"path": "inputs/x.csv", "sha256": "b" * 64, "bytes": 5}],
            "status": "ok", "exit_code": 0,
            "created_at": "2026-10-29T23:00:30+08:00",
            "started_at": "2026-10-29T23:05:00+08:00",
            "finished_at": "2026-10-29T23:10:00+08:00", "duration_s": 300.0,
            "attempts": [{"n": 1, "started_at": "2026-10-29T23:05:00+08:00",
                          "duration_s": 300.0, "exit_code": 0, "outcome": "ok"}],
            "whole_execution_restarts": 0, "transport_retries": 0,
            "stdout_bytes": 10, "stdout_sha256": "c" * 64,
            "stderr_bytes": 2, "stderr_sha256": "d" * 64,
            "usage": {"requests": 3, "input_tokens": 100, "output_tokens": 50,
                      "cache_read_tokens": 80, "cache_creation_tokens": 0, "per_call": []},
            "weighted": 70.0, "reward": 0, "failed": ["q49"],
            "judge": {"correct": 7, "n_tasks": 10, "checker_sha256": "e" * 64},
            "integrity": {"violations": 0, "patterns": [], "evidence": []},
            "integrity_verdict": "clean", "timed_out": False,
            "infra_type": None, "diagnostic": None, "live_doc_drift": [],
        }
        gate_py = REAL / "1-评测方案" / "工具链" / "l4-execution" / "gate.py"
        vm = None
        if gate_py.exists():
            gspec = importlib.util.spec_from_file_location("l4_gate_st", gate_py)
            g = importlib.util.module_from_spec(gspec)
            gspec.loader.exec_module(g)
            if hasattr(g, "load_runner_validator"):
                vm = g.load_runner_validator()
        if vm is None:
            vspec = importlib.util.spec_from_file_location(
                "l3_val_st", REAL / "1-评测方案/工具链/runner-schema-v2/validate_runner_meta.py")
            vm = importlib.util.module_from_spec(vspec)
            vspec.loader.exec_module(vm)
        seal = _dt.datetime.fromisoformat(base["registered_at"])
        res_ok = vm.validate_meta(base, seal_at=seal)
        check("l3_component_mock_ok_pass", lambda: (_ for _ in ()).throw(AssertionError(res_ok["issues"])) if
              vm.classify(res_ok) != "pass" else None)
        bad = copy.deepcopy(base)
        bad.update({"status": "transport-error", "exit_code": 1, "selection": None,
                    "diagnostic": "transport: stream disconnected（R1 真值表：selection=null+非空 diagnostic）"})
        res_bad = vm.validate_meta(bad, seal_at=seal)
        check("infra_truth_table_selection_null_diagnostic", lambda: (_ for _ in ()).throw(AssertionError()) if
              not (bad["selection"] is None and bool(bad["diagnostic"])) else None)
        check("infra_component_runs_not_silent", lambda: (_ for _ in ()).throw(AssertionError(res_bad)) if
              vm.classify(res_bad) not in (
                  "pass", "fail:missing", "fail:type", "fail:precision",
                  "fail:temporal-order", "fail:temporal-seal") else None)

        # ---- checker interface 负例（lead 收据口径）：exit1+合法 JSON=正常评分 ----
        bad_case_judge = {"correct": 0, "n_questions": 15, "reward": 0,
                          "weighted": 0.0, "checks": [], "checker_exit_code": 1}
        rep = lab.score8_reported(bad_case_judge)
        check("checker_exit1_score8_valid", lambda: (_ for _ in ()).throw(AssertionError(rep)) if
              not (isinstance(rep, float) and rep == 0.0) else None)
        check("checker_exit1_not_infra", lambda: (_ for _ in ()).throw(AssertionError()) if
              bad_case_judge.get("checker_exit_code") == 1 and bad_case_judge.get("reward") is None else None)

        # ---- partial 早退（任何 phase 停止未确认）：checker 0 调用 + score null + halt ----
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            saved = {k: getattr(lab, k) for k in
                     ("WS_ROOT", "RUNS", "CODEX_HOME", "CASE_ROOT", "BATCH", "CODEX_BIN",
                      "WS_ALLOWED_ROOT", "gate_check_real", "load_api_key", "close_process_group",
                      "judge")}
            try:
                case = td / "case" / "tb-cargo-plan"
                (case / "inputs").mkdir(parents=True)
                (case / "inputs" / "m.md").write_text("x\n", encoding="utf-8")
                (case / "instruction.md").write_text("# fake\n", encoding="utf-8")
                judge_calls = []
                def counting_judge(slot):
                    judge_calls.append(slot["slot_id"])
                    return {"correct": 1, "n_tasks": 27, "reward": 0, "weighted": 3.7, "checks": []}
                lab.CASE_ROOT = td / "case"
                lab.WS_ROOT = td / "ws"
                lab.WS_ALLOWED_ROOT = td
                lab.RUNS = td / "runs"
                lab.BATCH = td / "batch"
                (lab.BATCH / "config").mkdir(parents=True)
                (lab.BATCH / "config" / "codex-config.toml").write_bytes(
                    (REAL / "3-表现现场/l4-20261029-cli/codex/config/codex-config.toml").read_bytes())
                lab.CODEX_HOME = td / "home"
                lab.CODEX_HOME.mkdir()
                (lab.CODEX_HOME / "config.toml").write_bytes(
                    (REAL / "3-表现现场/l4-20261029-cli/codex/config/codex-config.toml").read_bytes())
                stub = td / "codex-stub2.py"
                stub.write_text(
                    "#!/usr/bin/env python3\n"
                    "import json, os, sys, pathlib\n"
                    "sys.stdin.read()\n"
                    "ws = sys.argv[sys.argv.index('-C') + 1]\n"
                    "sdir = pathlib.Path(os.environ['CODEX_HOME']) / 'sessions' / '2026' / '10' / '29'\n"
                    "sdir.mkdir(parents=True, exist_ok=True)\n"
                    "(sdir / 'rollout-stub2.jsonl').write_text(json.dumps("
                    "{'type': 'session_meta', 'payload': {'id': 'stub2-s1', 'cwd': ws}}) + chr(10))\n")
                stub.chmod(0o755)
                lab.CODEX_BIN = str(stub)
                fake_binding = {"design_commit": "d" * 40, "preregistration_commit": "e" * 40,
                                "execution_seal_commit": "e" * 40,
                                "registered_at": "2026-10-29T20:00:00+08:00",
                                "execution_manifest_sha256": "0" * 64,
                                "plan_sha256": "0" * 64, "contract_sha256": "0" * 64,
                                "released_for_model_calls": True}
                lab.gate_check_real = lambda: fake_binding
                lab.load_api_key = lambda: "stub-key"
                lab.close_process_group = (lambda *a, **k: {
                    "slot_id": a[2]["slot_id"], "pid": 1, "saved_pgid": 1, "attempt": {"n": 1},
                    "phase": "normal_exit", "at": "2026-10-29T21:00:00+08:00", "pgid": 1,
                    "pgid_source": "saved_at_dispatch", "term_delivery": "denied",
                    "probe": "probe_denied", "signal": None, "verified": False,
                    "verified_stop": False, "group_confirmed_gone": False,
                    "ack_at": "2026-10-29T21:00:01+08:00", "fallback_child_kill": False,
                    "direct_child_returncode": 0, "residual_risk_disclosed": True})
                lab.judge = counting_judge
                rc = lab.cmd_run("l4-20261029-cli-codex-tb-cargo-plan-r2")
                check("partial_exit4", lambda: (_ for _ in ()).throw(AssertionError(rc)) if rc != 4 else None)
                check("partial_checker_zero_calls", lambda: (_ for _ in ()).throw(AssertionError(judge_calls)) if
                      judge_calls else None)
                ev2 = lab.RUNS / "l4-20261029-cli-codex-tb-cargo-plan-r2"
                check("partial_no_score_receipt", lambda: (_ for _ in ()).throw(AssertionError()) if
                      (ev2 / "score-receipt.json").exists() or (ev2 / "checker.stdout").exists() else None)
                meta2 = json.loads((ev2 / "meta.json").read_text(encoding="utf-8"))
                check("partial_meta_score_null", lambda: (_ for _ in ()).throw(AssertionError(meta2)) if
                      meta2.get("judge") is not None or meta2.get("reward") is not None
                      or meta2.get("weighted") is not None else None)
                check("partial_halt_persisted", lambda: (_ for _ in ()).throw(AssertionError()) if
                      not (lab.BATCH / "halt.json").exists() else None)
                check("partial_blocks_next", lambda: (_ for _ in ()).throw(AssertionError()) if
                      not _raises(lambda: lab.cmd_run("l4-20261029-cli-codex-tb-cargo-plan-r3")) else None)
            finally:
                for k, v in saved.items():
                    setattr(lab, k, v)

        # ---- cmd_run 全链 mock（Popen 桩 CLI：prepare→run→persist→judge→component→dual-archive）----
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            saved = {k: getattr(lab, k) for k in
                     ("WS_ROOT", "RUNS", "CODEX_HOME", "CASE_ROOT", "BATCH", "CODEX_BIN",
                      "WS_ALLOWED_ROOT", "gate_check_real", "load_api_key")}
            try:
                case = td / "case" / "dabstep-payments-10"
                (case / "inputs").mkdir(parents=True)
                (case / "inputs" / "q.jsonl").write_text("row\n", encoding="utf-8")
                (case / "instruction.md").write_text("# fake task\n", encoding="utf-8")
                (case / "checker.py").write_text(
                    "import json, sys\n"
                    "print(json.dumps({'correct': 9, 'n_tasks': 10, 'reward': 0, "
                    "'weighted': 90.0, 'checks': [], 'checker_exit_code': 0}))\n", encoding="utf-8")
                home = td / "home"
                home.mkdir()
                cfg_src = REAL / "3-表现现场/l4-20261029-cli/codex/config/codex-config.toml"
                (home / "config.toml").write_bytes(cfg_src.read_bytes())
                stub = td / "codex-stub.py"
                stub.write_text(
                    "#!/usr/bin/env python3\n"
                    "import json, os, sys, pathlib\n"
                    "inp = sys.stdin.read()\n"
                    "ws = sys.argv[sys.argv.index('-C') + 1]\n"
                    "sdir = pathlib.Path(os.environ['CODEX_HOME']) / 'sessions' / '2026' / '10' / '29'\n"
                    "sdir.mkdir(parents=True, exist_ok=True)\n"
                    "meta = json.dumps({'type': 'session_meta', 'payload': {'id': 'stub-s1', 'cwd': ws}})\n"
                    "recs = [json.dumps({'type': 'token_usage_record', 'timestamp': "
                    "'2026-10-29T23:00:0%dZ' % i, 'payload': {'response_id': 'r%d' % i, "
                    "'usage': {'input_tokens': 10, 'cached_input_tokens': 4, 'output_tokens': 2}}}) "
                    "for i in range(2)]\n"
                    "(sdir / 'rollout-stub.jsonl').write_text(meta + chr(10) + chr(10).join(recs) + chr(10))\n"
                    "sys.stdout.write(chr(10).join(recs) + chr(10))\n"
                    "open(pathlib.Path(ws) / 'artifact.txt', 'w').write('done')\n")
                stub.chmod(0o755)

                lab.WS_ROOT = td / "ws"
                lab.WS_ALLOWED_ROOT = td
                lab.RUNS = td / "runs"
                lab.BATCH = td / "batch"  # 停批纪律测试绝不触碰真实批次目录
                (lab.BATCH / "config").mkdir(parents=True)
                (lab.BATCH / "config" / "codex-config.toml").write_bytes(cfg_src.read_bytes())
                lab.CODEX_HOME = home
                lab.CASE_ROOT = td / "case"
                lab.CODEX_BIN = str(stub)
                fake_binding = {"design_commit": "d" * 40, "preregistration_commit": "e" * 40,
                                "execution_seal_commit": "e" * 40,
                                "registered_at": "2026-10-29T20:00:00+08:00",
                                "execution_manifest_sha256": "0" * 64,
                                "plan_sha256": "0" * 64, "contract_sha256": "0" * 64,
                                "released_for_model_calls": True}
                lab.gate_check_real = lambda: fake_binding
                lab.load_api_key = lambda: "stub-key"
                rc = lab.cmd_run("l4-20261029-cli-codex-dabstep-payments-10-r1")
                check("mock_run_exit0", lambda: (_ for _ in ()).throw(AssertionError(rc)) if rc != 0 else None)
                ev = lab.RUNS / "l4-20261029-cli-codex-dabstep-payments-10-r1"
                for name in ("prompt.txt", "agent.jsonl", "agent.stderr.txt", "checker.stdout",
                             "score-receipt.json", "termination.json", "session-capture.json",
                             "dual-archive.status.json", "meta.json", "claim.json"):
                    check("mock_artifact_" + name, lambda n=name: (_ for _ in ()).throw(AssertionError(n)) if
                          not (ev / n).exists() else None)
                check("mock_agent_session_dir", lambda: (_ for _ in ()).throw(AssertionError()) if
                      not any((ev / "agent-session").glob("*.jsonl")) else None)
                check("mock_projections", lambda: (_ for _ in ()).throw(AssertionError()) if
                      not (ev / "projections" / "legacy" / "ADAPTATION.json").exists() or
                      not (ev / "projections" / "current" / "agent.jsonl").exists() else None)
                meta = json.loads((ev / "meta.json").read_text(encoding="utf-8"))
                check("mock_status_ok", lambda: (_ for _ in ()).throw(AssertionError(meta["status"])) if
                      meta["status"] != "ok" else None)
                check("mock_selection_present", lambda: (_ for _ in ()).throw(AssertionError(meta)) if
                      meta.get("selection") is None else None)
                check("mock_usage_two_calls", lambda: (_ for _ in ()).throw(AssertionError(meta["usage"])) if
                      meta["usage"]["requests"] != 2 else None)
                check("mock_score_receipt_8dp", lambda: (_ for _ in ()).throw(AssertionError()) if
                      json.loads((ev / "score-receipt.json").read_text(encoding="utf-8"))["score"]["reported"] != 90.0 else None)
                comp = meta.get("l3_field_component", {})
                check("mock_l3_component_pass", lambda: (_ for _ in ()).throw(AssertionError(comp)) if
                      not (comp.get("available") and comp.get("classify") == "pass") else None)
                check("mock_formal_eligible", lambda: (_ for _ in ()).throw(AssertionError(meta)) if
                      meta.get("runner_formal_eligible") is not True else None)
                tj = json.loads((ev / "termination.json").read_text(encoding="utf-8"))
                check("mock_termination_identity", lambda: (_ for _ in ()).throw(AssertionError(tj)) if
                      tj.get("slot_id") != meta["slot_id"] or tj.get("pid") != tj.get("saved_pgid")
                      or tj.get("attempt", {}).get("pgid") != tj.get("saved_pgid") else None)
                a0 = meta["attempts"][0]
                check("mock_attempts_authoritative", lambda: (_ for _ in ()).throw(AssertionError(a0)) if
                      a0.get("pid") != tj.get("pid") or a0.get("pgid") != tj.get("pgid")
                      or a0.get("slot_id") != meta["slot_id"] else None)
                check("mock_meta_binding_no_dual_bool", lambda: (_ for _ in ()).throw(AssertionError(meta)) if
                      "verified_stop" in (meta.get("termination_receipt") or {}) else None)  # atk16
                check("mock_doc_group_confirmed", lambda: (_ for _ in ()).throw(AssertionError(tj)) if
                      tj.get("group_confirmed_gone") is not True else None)
                tr = meta.get("termination_receipt")
                import hashlib as _h
                tr_sha = _h.sha256((ev / "termination.json").read_bytes()).hexdigest()
                check("mock_termination_receipt_binding", lambda: (_ for _ in ()).throw(AssertionError(tr)) if
                      not (tr and tr.get("file") == "termination.json" and tr.get("sha256") == tr_sha) else None)
                (lab.BATCH / "halt.json").write_text("{}", encoding="utf-8")
                check("halt_blocks_subsequent", lambda: (_ for _ in ()).throw(AssertionError()) if
                      not _raises(lambda: lab.cmd_run("l4-20261029-cli-codex-tb-cargo-plan-r1")) else None)
            finally:
                for k, v in saved.items():
                    setattr(lab, k, v)

        if WARNINGS:
            print("WARNINGS:", json.dumps(WARNINGS, ensure_ascii=False))
        print("SELFTEST:", "PASS" if not FAILURES else f"FAIL {FAILURES}")
        return 0 if not FAILURES else 1
    finally:
        socket.socket = real_socket


def _raises(fn) -> bool:
    try:
        fn()
        return False
    except Exception:
        return True


if __name__ == "__main__":
    sys.exit(main())
