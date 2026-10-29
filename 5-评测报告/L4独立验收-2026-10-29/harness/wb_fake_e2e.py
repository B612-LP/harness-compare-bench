#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_fake_e2e.py — judge 独立 L4 WB runner fake 端到端 harness v2（对 v3.2 candidate）。

v2 变更（lead 指令）：
- 只 stub OS 边界（subprocess/_lsof/DB/jsonl/时间参数），不替换待测入口
  （wait_completion_strict / run_impl / claim_slot / binding_values 原样调用）；
- 新增 W11 binding_values 实调（NameError 闭项）、W12 native_stop 信封 gate 准入正/负对、
  W5 strict-wait 套件（active-idle 不完成 / flap 拒 / trace 增长拒 / lsof 错误拒）、
  W6 stop_capability_failed 保守性、W7 claim O_EXCL 重复与崩溃窗口零外发、
  W8 漂移检测单元+停余键、W2 断言 slot_id 顶层键。
v1（对 20261029T203334 快照的 9 用例）存档：wb_fake_e2e.v1-against-snap203334.py.txt。
"""
from __future__ import annotations

import argparse
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
from l4_fixture import _external_required  # noqa: E402

TZ8 = dt.timezone(dt.timedelta(hours=8))


def now_iso() -> str:
    return dt.datetime.now(TZ8).isoformat(timespec="seconds")


def sha_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def jdump(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                 encoding="utf-8")


def git(*args, cwd, env_extra=None) -> subprocess.CompletedProcess:
    env = dict(os.environ, TZ="Asia/Shanghai")
    env.update(env_extra or {})
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, env=env)


SENTINEL_SITE = r'''
import socket, os as _os
_LOG = _os.environ.get("JUDGE_SENTINEL_LOG")
_orig_connect = socket.socket.connect
_orig_create = socket.create_connection
def _check(addr):
    try:
        host = addr[0]
    except Exception:
        host = str(addr)
    ok = isinstance(host, str) and (host in ("127.0.0.1", "::1", "localhost"))
    if _LOG:
        with open(_LOG, "a") as f:
            f.write("connect %s allowed=%s\n" % (host, ok))
    if not ok:
        raise AssertionError("JUDGE-SENTINEL: non-local connect refused: %r" % (addr,))
def _pc(self, address):
    _check(address); return _orig_connect(self, address)
def _pcc(address, *a, **k):
    _check(address); return _orig_create(address, *a, **k)
socket.socket.connect = _pc
socket.create_connection = _pcc
'''


def write_sentinel(libdir: Path) -> None:
    libdir.mkdir(parents=True, exist_ok=True)
    (libdir / "sitecustomize.py").write_text(SENTINEL_SITE, encoding="utf-8")


def build_fixture(snap: Path, work: Path) -> dict:
    REPO = work / "repo"
    L4 = REPO / "1-评测方案" / "自动循环L4-2026-10-29"
    GATED = REPO / "1-评测方案" / "工具链" / "l4-execution"
    WBG = REPO / "3-表现现场" / "l4-20261029-wb-gateway"
    CASE = REPO / "2-用例"
    for d in (L4, GATED, CASE):
        d.mkdir(parents=True, exist_ok=True)
    real = Path("/Users/b612-lp/Documents/harness-compare-bench")
    shutil.copy2(snap / "plan.json", L4 / "plan.json")
    shutil.copy2(snap / "contract.json", L4 / "contract.json")
    shutil.copy2(snap / "execution_seal.py", L4 / "execution_seal.py")
    for name in ("PREREGISTRATION.md", "CLARIFICATION-L4-1.md", "test_execution_seal.py"):
        src = real / "1-评测方案/自动循环L4-2026-10-29" / name
        if src.is_file():
            shutil.copy2(src, L4 / name)
    shutil.copy2(snap / "gate.py", GATED / "gate.py")
    shutil.copytree(snap / "src-wb", WBG)
    stubs = {
        "3-表现现场/l4-20261029-cli/dsh/tools/lab.py": "# stub dsh (fixture)\n",
        "3-表现现场/l4-20261029-cli/codex/tools/lab.py": "# stub codex (fixture)\n",
        "3-表现现场/l4-20261029-cache/tools/cache_probe.py": "# stub cache (fixture)\n",
        "3-表现现场/r1030-formal-a1/tools/lab.py": "# stub (fixture)\n",
        "3-表现现场/r1031-variance-n3/tools-codex/lab.py": "# stub (fixture)\n",
        "3-表现现场/r1031-variance-n3/tools-dsh/lab.py": "# stub (fixture)\n",
        "3-表现现场/l4-20261029-cli/codex/config/codex-config.toml": "# fixture\n",
        "3-表现现场/l4-20261029-cache/config/probe-config.json": "{}\n",
    }
    for rel, content in stubs.items():
        p = REPO / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    for rel in ("1-评测方案/工具链/runner-schema-v2/validate_runner_meta.py",
                "1-评测方案/工具链/evidence-kit/evidence_line.py",
                "1-评测方案/工具链/evidence-kit/receipt_check.py"):
        src = real / rel
        dst = REPO / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst) if src.is_file() else dst.write_text("# stub\n", encoding="utf-8")
    cdir = CASE / "bird-ca-schools-15"
    (cdir / "inputs").mkdir(parents=True, exist_ok=True)
    (cdir / "inputs" / "answer.txt").write_text("FAKE-INPUT-FOR-HARNESS\n", encoding="utf-8")
    (cdir / "instruction.md").write_text("# FAKE case (judge harness)\n", encoding="utf-8")
    # v3：3 计分项+守卫+guards_used+0-100 标尺（对齐 gate earned/possible 重算与真冻结 dtype）
    (cdir / "checker.py").write_text(
        "#!/usr/bin/env python3\nimport json,sys\nfrom pathlib import Path\n"
        "ws=Path(sys.argv[1])\nok=(ws/'output.txt').is_file()\n"
        "guard_ok=(ws/'inputs'/'answer.txt').is_file()\n"
        "earned=3 if ok else 0\n"
        "checks=[{'id':'input_integrity','pass':bool(guard_ok)}]"
        "+[{'id':'a%d'%i,'pass':bool(ok)} for i in (1,2,3)]\n"
        "print(json.dumps({'reward':int(ok),'weighted':round(100.0*earned/3,2),"
        "'checks':checks,'guards_used':['input_integrity'],"
        "'correct':earned,'n_tasks':3}))\n"
        "raise SystemExit(0 if ok else 1)\n", encoding="utf-8")
    contract = json.loads((L4 / "contract.json").read_text(encoding="utf-8"))
    contract["checker_sha256"]["bird-ca-schools-15"] = sha_file(cdir / "checker.py")
    def _patch_case_face(case, cdir):
        files_map = {}
        for q in sorted(cdir.rglob("*")):
            if q.is_file():
                files_map[str(q.relative_to(cdir))] = sha_file(q)
        snap = contract["case_snapshots"][case]
        snap["files"] = files_map
        snap["checker.py"] = sha_file(cdir / "checker.py")
        contract["denominators"][case] = 3  # fake case：a1–a3 三计分项
        contract["checker_sha256"][case] = sha_file(cdir / "checker.py")
    _patch_case_face("bird-ca-schools-15", cdir)
    cdir_cargo = CASE / "tb-cargo-plan"
    if cdir_cargo.is_dir():
        _patch_case_face("tb-cargo-plan", cdir_cargo)
    (L4 / "contract.json").write_text(
        json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    home = Path(os.path.realpath(work)) / "home"
    (home / ".dsh").mkdir(parents=True, exist_ok=True)
    (home / ".dsh" / ".credentials.yaml").write_text(
        "refs:\n  DEEPSEEK_API_KEY: FAKE-JUDGE-HARNESS-NOT-A-KEY\n", encoding="utf-8")
    (home / ".dsh" / "AGENTS.md").write_text("# fixture stub\n", encoding="utf-8")
    prof = home / ".dsh" / "profiles" / "bench-cli"
    prof.mkdir(parents=True, exist_ok=True)
    (prof / "cordis.patch.yml").write_text("# fixture stub\n", encoding="utf-8")
    (prof / "package.json").write_text("{}\n", encoding="utf-8")
    codex_cfg = home / "bench-workspaces" / "l4-20261029-cli" / "codex" / "_codex-home"
    codex_cfg.mkdir(parents=True, exist_ok=True)
    (codex_cfg / "config.toml").write_text(
        "# fixture codex config (judge harness)\n", encoding="utf-8")
    for rel in ("runs", "receipts/claims", "selftest/dry-run-result.json",
                "selftest/dry-evidence"):
        p = WBG / rel
        shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
    git("init", "-q", "-b", "main", cwd=REPO)
    git("config", "user.email", "judge-fixture@invalid", cwd=REPO)
    git("config", "user.name", "judge-fixture", cwd=REPO)
    t_now = dt.datetime.now(TZ8)
    tD = (t_now - dt.timedelta(minutes=20)).isoformat(timespec="seconds")
    tE = (t_now - dt.timedelta(minutes=10)).isoformat(timespec="seconds")
    denv = lambda t: {"GIT_AUTHOR_DATE": t, "GIT_COMMITTER_DATE": t}
    spec = importlib.util.spec_from_file_location("fx_seal", L4 / "execution_seal.py")
    es = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(es)
    required = sorted(es.required_files())
    manifest = {"schema_version": 1, "design_commit": None, "generated_at": tD,
                "files": {rel: sha_file(REPO / rel) for rel in required},
                "external_files": dict(_external_required(home, codex_cfg / "config.toml", es)),
                "live_doc_drift": []}
    git("add", "-A", cwd=REPO)
    git("commit", "-q", "-m", "D fixture", cwd=REPO, env_extra=denv(tD))
    D = git("rev-parse", "HEAD", cwd=REPO).stdout.strip()
    manifest["design_commit"] = D
    (L4 / "execution-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    git("add", "-A", cwd=REPO)
    git("commit", "-q", "-m", "E fixture", cwd=REPO, env_extra=denv(tE))
    E = git("rev-parse", "HEAD", cwd=REPO).stdout.strip()
    manifest_sha = sha_file(L4 / "execution-manifest.json")
    (REPO / "HEADNOTE.txt").write_text("head after E\n", encoding="utf-8")
    git("add", "-A", cwd=REPO)
    git("commit", "-q", "-m", "post-E", cwd=REPO, env_extra=denv(tE))

    def binding(released: bool) -> Path:
        b = {"schema_version": 1, "design_commit": D, "preregistration_commit": E,
             "execution_seal_commit": E, "registered_at": tE,
             "execution_manifest_sha256": manifest_sha,
             "plan_sha256": sha_file(L4 / "plan.json"),
             "contract_sha256": sha_file(L4 / "contract.json"),
             "released_for_model_calls": bool(released),
             "generated_at": tE, "live_doc_drift": []}
        p = L4 / "runtime-binding.json"
        jdump(p, b)
        return p

    return {"REPO": REPO, "L4": L4, "WBG": WBG, "CASE": CASE, "home": home,
            "D": D, "E": E, "tD": tD, "tE": tE, "binding": binding,
            "sentinel_lib": work / "sentinel-lib", "work": work}


FIXTURE_SESSION = [
    {"type": "session", "timestamp": "2026-10-29T20:00:00+08:00"},
    {"type": "message", "timestamp": "2026-10-29T20:01:00+08:00",
     "rawUsage": {"input_tokens": 100, "output_tokens": 10,
                  "cache_creation_input_tokens": 0, "cache_read_input_tokens": 50}},
    {"type": "message", "timestamp": "2026-10-29T20:02:00+08:00",
     "rawUsage": {"input_tokens": None, "output_tokens": None}},
    {"type": "message", "timestamp": "2026-10-29T20:03:00+08:00"},
]

DRIVER_LIB = r'''
import json, time, datetime as _dt
def now_iso():
    return _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=8))).isoformat(timespec="seconds")
FIXTURE_SESSION = __SESSION__
class RecorderDriver:
    def __init__(self, mode="completed", session_model="deepseek-v4.1-flash"):
        self.mode = mode; self.session_model = session_model
        self.calls = []; self.cancel_attempts = 0
    def ensure_app(self):
        self.calls.append("ensure_app"); return "mock-reused"
    def new_task(self, workspace_dir, prompt_text, model="DeepSeek V4.1-Flash",
                 title=None, port=9332, **kw):
        self.calls.append(["new_task", str(workspace_dir), model])
        if self.mode == "completed":
            # 模拟真实 WorkBuddy 会话在 workspace 产出工作产物（checker 判分对象）
            try:
                (__import__("pathlib").Path(workspace_dir) / "output.txt").write_text(
                    "FX-OUTPUT\n", encoding="utf-8")
            except OSError:
                pass
        return {"id": "mock-session-0001", "started_at": now_iso(),
                "model": self.session_model, "title": title or "harness"}
    def wait_completion(self, task_id, timeout_s, workspace_dir=None, **kw):
        self.calls.append(["wait_completion", task_id, timeout_s])
        if self.mode == "active_idle":
            return {"status": "completed", "ended_at": now_iso(),
                    "evidence": {"db": {"id": task_id, "status": "active"},
                                 "jsonl": {"exists": True}, "stable_s": 20.1}}
        if self.mode == "timeout_writing":
            return {"status": "timeout", "ended_at": now_iso(),
                    "evidence": {"db": {"id": task_id, "status": "active"},
                                 "jsonl": {"exists": True}, "stable_s": 0.0}}
        return {"status": "completed", "ended_at": now_iso(),
                "evidence": {"db": {"id": task_id, "status": "completed",
                                    "model": self.session_model,
                                    "thought_level": "low", "mode": "craft"},
                             "jsonl": {"exists": True}, "waited_s": 0.1}}
    def cancel(self, task_id, workspace_dir=None):
        self.cancel_attempts += 1; self.calls.append(["cancel", task_id])
        return {"stopped": True}
    def wait_strict(self, task_id, timeout_s, workspace_dir=None, on_deadline=None, **kw):
        """与 safe_driver.wait_completion_strict 同契约的驱动侧边界桩。"""
        self.calls.append(["wait_strict", task_id, timeout_s])
        if self.mode in ("active_idle", "timeout_writing"):
            self.cancel_attempts += 1
            self.calls.append(["cancel", task_id])
            return {"status": "timeout", "ended_at": now_iso(),
                    "stop_info": {"stop_verified": False, "cancel_invoked": True,
                                  "post_cancel_db": "active",
                                  "post_cancel_trace_stable": False,
                                  "deadline_reached_at": now_iso()},
                    "evidence": {"db_status": "active"}}
        return {"status": "completed", "ended_at": now_iso(), "stop_info": None,
                "evidence": {"db_status": "completed"}}
    def collect(self, task_id, dest_dir, workspace_dir=None):
        self.calls.append(["collect", task_id, str(dest_dir)])
        dest = __import__("pathlib").Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)
        if self.mode == "no_trace":
            return {"files": []}
        lines = []
        for o in FIXTURE_SESSION:
            o = dict(o)
            if o.get("type") == "session":
                o["model"] = self.session_model
            lines.append(json.dumps(o, ensure_ascii=False))
        (dest / "mock-session-0001.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        (dest / "session-row.json").write_text(json.dumps(
            {"id": task_id,
             "status": "active" if self.mode in ("active_idle", "timeout_writing")
             else "completed",
             "model": self.session_model, "thought_level": "low", "mode": "craft"},
            ensure_ascii=False) + "\n", encoding="utf-8")
        return {"files": [p.name for p in sorted(dest.iterdir())]}
def make_driver(mode):
    if mode == "alias_mismatch":
        return RecorderDriver("completed", session_model="deepseek-v3.2-exp")
    return RecorderDriver(mode)
'''.replace("__SESSION__", repr(FIXTURE_SESSION))


def run_run_impl(fx, mode, ws_root: Path, case_root: Path, slot_idx: int = 0, dry: bool = True):
    runner = fx["WBG"] / "runner" / "l4_wb_runner.py"
    plan = json.loads((fx["L4"] / "plan.json").read_text(encoding="utf-8"))
    slot = [s for s in plan["product_slots"] if s["stratum"] == "wb_gateway_delivery"][slot_idx]
    (fx["work"] / "wb_drivers_v2.py").write_text(DRIVER_LIB, encoding="utf-8")
    code = f"""
import json, sys
sys.path.insert(0, {str(fx['work'])!r})
from wb_drivers_v2 import make_driver
import importlib.util
spec = importlib.util.spec_from_file_location("l4wbr", {str(runner)!r})
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
slot = json.loads({json.dumps(slot, ensure_ascii=False)!r})
drv = make_driver({mode!r})
r = m.run_impl(slot, drv, dry={dry!r}, case_root={str(case_root)!r},
               ws_root={str(ws_root)!r}, registered_at={fx['tE']!r},
               preregistration_commit={fx['E']!r}, execution_seal_commit={fx['E']!r},
               expect_checker_sha=None)
out = {{"status": r.get("status"), "calls": [list(c) if isinstance(c, tuple) else c for c in drv.calls],
        "cancel_attempts": getattr(drv, "cancel_attempts", None),
        "stop_capability_failed": r.get("stop_capability_failed"),
        "evidence_dir": r.get("evidence_dir"),
        "checker_ran": r.get("checker_ran"),
        "partial_stop_unverified": r.get("partial_stop_unverified"),
        "halted": r.get("halted"),
        "claim": r.get("claim"), "meta": r.get("meta"), "accounting": r.get("accounting")}}
print("@@RESULT@@" + json.dumps(out, ensure_ascii=False))
"""
    write_sentinel(fx["sentinel_lib"])
    log = fx["work"] / "sentinel.log"
    log.touch()
    env = dict(os.environ, HOME=str(fx["home"]), PYTHONPATH=str(fx["sentinel_lib"]),
               JUDGE_SENTINEL_LOG=str(log), PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                       env=env, timeout=600)
    raw = None
    for line in (p.stdout or "").splitlines():
        if line.startswith("@@RESULT@@"):
            raw = json.loads(line[10:])
    return {"rc": p.returncode, "stdout_tail": (p.stdout or "")[-1200:],
            "stderr_tail": (p.stderr or "")[-2500:], "result": raw}


SLOT_ID = "l4-20261029-wb-gateway-bird-ca-schools-15-r1"

GATE_ADM_SUB = r"""
import importlib.util, json, sys
from pathlib import Path
MARK = "@@RESULT@@"
gate_p, bp, repo, l4, product = sys.argv[1:6]
spec = importlib.util.spec_from_file_location("g", gate_p)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
try:
    adm = g.gate_admission(bp, product, repo=Path(repo), plan_dir=Path(l4))
    out = {"per_slot": adm.get("per_slot", [])}
except Exception as e:
    out = {"error": repr(e)[:500]}
print(MARK + json.dumps(out, ensure_ascii=False)[:8000])
"""

def run_gate_admission(fx, product="workbuddy"):
    write_sentinel(fx["sentinel_lib"])
    env = dict(os.environ, HOME=str(fx["home"]), PYTHONPATH=str(fx["sentinel_lib"]),
               JUDGE_SENTINEL_LOG=str(fx["work"] / "sentinel-adm.log"),
               PYTHONDONTWRITEBYTECODE="1")
    (fx["work"] / "sentinel-adm.log").touch()
    p = subprocess.run([sys.executable, "-c", GATE_ADM_SUB,
                        str(fx["REPO"] / "1-评测方案" / "工具链" / "l4-execution" / "gate.py"),
                        str(fx["L4"] / "runtime-binding.json"), str(fx["REPO"]),
                        str(fx["L4"]), product],
                       capture_output=True, text=True, env=env, timeout=300)
    for line in (p.stdout or "").splitlines():
        if line.startswith("@@RESULT@@"):
            return json.loads(line[10:])
    return {"error": (p.stderr or "")[-400:]}

def publish_dry_to_real(fx, case="bird-ca-schools-15", slot_id=SLOT_ID):
    """把 dry-evidence 证据发布到 gate 扫描的真实 runs 路径（gate 契约视角）。"""
    src = fx["WBG"] / "selftest" / "dry-evidence" / case
    dst = fx["WBG"] / "runs" / slot_id
    shutil.rmtree(dst, ignore_errors=True)
    if src.is_dir():
        shutil.copytree(src, dst)
    return dst


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snap", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--only", default=None)
    a = ap.parse_args()
    snap = Path(a.snap).resolve()
    out_dir = Path(a.out) if a.out else (Path(__file__).resolve().parent / "results" / snap.name)
    work = Path("/tmp/judge-l4/fixture-wb2-" + snap.name.split("-", 1)[-1])
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    fx = build_fixture(snap, work)
    cases, only = {}, (set(a.only.split(",")) if a.only else None)

    def rec(name, verdict, detail):
        cases[name] = {"verdict": verdict, "detail": detail}

    def run_case(n):
        return (only is None) or (n in only)

    case_root = fx["CASE"] / "bird-ca-schools-15"
    ev_slot = fx["WBG"] / "runs" / SLOT_ID

    # ---- W1 E-block（真实 cmd_run_slot 子进程）----
    if run_case("W1_e_seal_block"):
        write_sentinel(fx["sentinel_lib"])
        log = fx["work"] / "sentinel-w1.log"
        log.touch()
        env = dict(os.environ, HOME=str(fx["home"]), PYTHONPATH=str(fx["sentinel_lib"]),
                   JUDGE_SENTINEL_LOG=str(log), PYTHONDONTWRITEBYTECODE="1")
        fx["binding"](False)
        p = subprocess.run([sys.executable, str(fx["WBG"] / "runner" / "l4_wb_runner.py"),
                            "run-slot", SLOT_ID], capture_output=True, text=True,
                           env=env, timeout=300, cwd=str(fx["REPO"]))
        refused = (fx["WBG"] / "receipts" / "release-refused.json")
        rec("W1_e_seal_block", "pass" if (p.returncode == 2 and refused.exists()) else "fail",
            {"rc": p.returncode, "refused_receipt": refused.exists(),
             "stderr_tail": (p.stderr or "")[-300:]})

    # ---- W11 binding_values 实调（NameError 闭项验证）----
    if run_case("W11_binding_values_defined"):
        fx["binding"](True)
        spec = importlib.util.spec_from_file_location(
            "l4wbr_v", fx["WBG"] / "runner" / "l4_wb_runner.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        try:
            bv = m.binding_values()
            ok = isinstance(bv, dict) and all(k in bv for k in
                                              ("registered_at", "preregistration_commit",
                                               "execution_seal_commit"))
            err = None
        except Exception as e:
            bv, ok, err = None, False, repr(e)[:200]
        rec("W11_binding_values_defined", "pass" if ok else "fail",
            {"returns_keys": sorted(bv.keys())[:6] if isinstance(bv, dict) else None,
             "error": err})

    # ---- W2 干跑基线 ----
    if run_case("W2_dry_baseline"):
        fx["binding"](True)
        ws = work / "ws-w2"
        r = run_run_impl(fx, "completed", ws, case_root)
        res = r.get("result") or {}
        meta = (res or {}).get("meta") or {}
        acc = (res or {}).get("accounting") or {}
        ok = (res and res.get("status") == "ok" and acc.get("execution_state") == "executed"
              and meta.get("registered_at") == fx["tE"]
              and len(meta.get("usage", {}).get("per_call", [])) == 2
              and isinstance(meta.get("slot_id"), str))
        rec("W2_dry_baseline", "pass" if ok else "fail",
            {"rc": r["rc"], "status": (res or {}).get("status"),
             "accounting_state": acc.get("execution_state"),
             "usage_per_call_n": len(meta.get("usage", {}).get("per_call", [])),
             "slot_id_top_level": meta.get("slot_id"),
             "managed_unknowns_type": type(meta.get("managed_unknowns")).__name__,
             "stderr_tail": r["stderr_tail"][-400:]})

    # ---- W5 strict-wait 套件（真实默认分支；只 stub _lsof/DB/jsonl）----
    if run_case("W5_strict_wait_suite"):
        code = r'''
import importlib.util, json, sys, types
from pathlib import Path
MARK = "@@RESULT@@"
spec = importlib.util.spec_from_file_location("sd", %r)
sd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sd)
jp = Path(%r)
jp.write_text("{}\n")
class FakeWD:
    """OS 边界桩：DB 行与 trace 尺寸由夹具供；deadline 后按序列回放状态。"""
    def __init__(self):
        self.db = {"status": "active"}
        self.bytes = 3
        self.post_seq = None
        self._GLOBAL = {}
    def _db_row(self, sid):
        if self.post_seq:
            return {"status": self.post_seq.pop(0)}
        return dict(self.db)
    def _jsonl_path(self, w, i):
        return jp
    def _jsonl_stats(self, p):
        return {"exists": True, "bytes": self.bytes, "lines": 3}

def lsof_ok(stdout):
    sd._lsof = lambda args, timeout_s=15: types.SimpleNamespace(
        returncode=0, stdout=stdout)
def lsof_err():
    sd._lsof = lambda args, timeout_s=15: types.SimpleNamespace(
        returncode=1, stdout="")
out = {}
# a) active+静默→deadline 恰一次；取消后 cancelled 稳定+无进程→verified
fake = FakeWD()
n = {"dl": 0}
def cb(sid, snap):
    n["dl"] += 1
    fake.db = {"status": "cancelled"}
    fake.post_seq = ["cancelled"] * 6
    return {"cancel_invoked": True, "cancel_at": "T+0"}
lsof_ok("")
res = sd.wait_completion_strict(fake, "fx", timeout_s=2.5, workspace_dir="/tmp/fake-ws",
                                stable_s=1.0, poll_s=0.2, on_deadline=cb,
                                post_cancel_window_s=1.2)
out["a_active_never_completed"] = (res["status"] != "completed")
out["a_on_deadline_once"] = (n["dl"] == 1)
out["a_stop_verified"] = res["stop_info"].get("stop_verified")
out["a_processes"] = res["stop_info"].get("post_cancel_processes")
# b) 终态后翻转（cancelled→active→cancelled）→ flap 拒
fake2 = FakeWD()
def cb2(sid, snap):
    fake2.db = {"status": "cancelled"}
    fake2.post_seq = ["cancelled", "active", "cancelled", "cancelled"]
res2 = sd.wait_completion_strict(fake2, "fx", timeout_s=1.5, workspace_dir="/tmp/fake-ws",
                                 stable_s=0.8, poll_s=0.2, on_deadline=cb2,
                                 post_cancel_window_s=1.5)
out["b_flap_rejected"] = (res2["stop_info"].get("stop_verified") is False
                          and res2["stop_info"].get("post_cancel_db_flapped") is True)
# c) cancel 后 trace 增长 → 拒
fake3 = FakeWD()
def cb3(sid, snap):
    fake3.db = {"status": "cancelled"}
    fake3.bytes = 99
    fake3.post_seq = ["cancelled"] * 6
res3 = sd.wait_completion_strict(fake3, "fx", timeout_s=1.5, workspace_dir="/tmp/fake-ws",
                                 stable_s=0.8, poll_s=0.2, on_deadline=cb3,
                                 post_cancel_window_s=1.5)
out["c_trace_growth_rejected"] = (res3["stop_info"].get("stop_verified") is False
                                  and res3["stop_info"].get("post_cancel_trace_stable") is False)
# d) lsof 错误 → 拒（错误≠无进程）
fake4 = FakeWD()
n4 = {"dl": 0}
def cb4(sid, snap):
    n4["dl"] += 1
    fake4.db = {"status": "cancelled"}
    fake4.post_seq = ["cancelled"] * 6
lsof_err()
res4 = sd.wait_completion_strict(fake4, "fx", timeout_s=1.5, workspace_dir="/tmp/fake-ws",
                                 stable_s=0.8, poll_s=0.2, on_deadline=cb4,
                                 post_cancel_window_s=1.2)
out["d_lsof_error_rejected"] = (res4["stop_info"].get("stop_verified") is False)
out["d_post_cancel_processes"] = res4["stop_info"].get("post_cancel_processes")
print(MARK + json.dumps(out, ensure_ascii=False))
''' % (str(fx["WBG"] / "runner" / "safe_driver.py"),
        str(work / "fake-trace.jsonl"))
        (work / "fake-trace.jsonl").write_text("{}\n", encoding="utf-8")
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                           env=env, timeout=300)
        out = None
        for line in (p.stdout or "").splitlines():
            if line.startswith("@@RESULT@@"):
                out = json.loads(line[10:])
        ok = bool(out) and all([
            out.get("a_active_never_completed"), out.get("a_on_deadline_once"),
            out.get("a_stop_verified") is True, out.get("b_flap_rejected"),
            out.get("c_trace_growth_rejected"), out.get("d_lsof_error_rejected")])
        rec("W5_strict_wait_suite", "pass" if ok else "fail",
            {"checks": out, "stderr_tail": (p.stderr or "")[-700:]})

    # ---- W9 dry 路径分离 ----
    if run_case("W9_dry_path_separation"):
        ws = work / "ws-w9"
        r = run_run_impl(fx, "completed", ws, case_root)
        dry_into_real = (ev_slot / "meta.json").exists() and \
            "9.9.9-dry" in (ev_slot / "meta.json").read_text(encoding="utf-8")
        dry_ev = fx["WBG"] / "selftest" / "dry-evidence" / "bird-ca-schools-15" / "meta.json"
        rec("W9_dry_path_separation", "pass" if ((not dry_into_real) and dry_ev.exists()
                                                 and "9.9.9-dry" in dry_ev.read_text(encoding="utf-8"))
            else "fail",
            {"dry_wrote_real_evidence_dir": dry_into_real,
             "dry_evidence_positive": dry_ev.exists(),
             "evidence_dir": str(ev_slot)})

    # ---- W3 alias 不匹配 gate 实拒 ----
    if run_case("W3_alias_gate"):
        ws = work / "ws-w3"
        r = run_run_impl(fx, "alias_mismatch", ws, case_root, slot_idx=1)
        res = r.get("result") or {}
        meta = (res or {}).get("meta") or {}
        publish_dry_to_real(fx, case="dabstep-payments-10",
                            slot_id="l4-20261029-wb-gateway-dabstep-payments-10-r1")
        fx["binding"](True)
        adm_out = run_gate_admission(fx, "workbuddy")
        if "error" not in adm_out:
            dab = [x for x in adm_out.get("per_slot", [])
                   if x.get("slot_id", "").endswith("dabstep-payments-10-r1")]
            per = (dab or adm_out.get("per_slot", [{}]))[0]
            adm_out = {"slot": per.get("slot_id"),
                       "formal_admission": per.get("formal_admission"),
                       "fails": per.get("fails", []),
                       "fails_n": len(per.get("fails", []))}
        rec("W3_alias_gate", "evidence",
            {"runner_verdict": (meta.get("alias_evidence") or {}).get("verdict"),
             "accounting_state": ((res or {}).get("accounting") or {}).get("execution_state"),
             "gate": adm_out})

    # ---- W4 空 trace 不冒真 ----
    if run_case("W4_no_trace"):
        ws = work / "ws-w4"
        r = run_run_impl(fx, "no_trace", ws, case_root, slot_idx=2)
        res = r.get("result") or {}
        meta = (res or {}).get("meta") or {}
        empty_sha = hashlib.sha256(b"").hexdigest()
        bad = (meta.get("stdout_sha256") == empty_sha
               and meta.get("integrity_verdict") == "clean"
               and meta.get("status") == "ok"
               and not meta.get("evidence_missing"))
        rec("W4_no_trace", "fail" if bad else "pass",
            {"stdout_sha256_is_empty": meta.get("stdout_sha256") == empty_sha,
             "integrity_verdict": meta.get("integrity_verdict"),
             "status": (res or {}).get("status"),
             "evidence_missing_marker": meta.get("evidence_missing")})

    # ---- W14 真实 verified 超时→gate timeout 真值表正例 ----
    if run_case("W14_timeout_verified_positive"):
        ws = work / "ws-w14"
        slot14_id = SLOT_ID  # bird 槽（fixture 契约面完整：files/checker.py/denominator=3）
        c14 = fx["WBG"] / "receipts" / "claims" / (slot14_id + ".claim")
        c14.unlink(missing_ok=True)
        shutil.rmtree(fx["WBG"] / "runs" / slot14_id, ignore_errors=True)
        r = run_run_impl(fx, "timeout_verified", ws, case_root, slot_idx=0, dry=False)
        res = r.get("result") or {}
        meta = res.get("meta") or {}
        ev = Path(res.get("evidence_dir") or "")
        env_doc = json.loads((ev / "native-stop.json").read_text()) if (ev / "native-stop.json").is_file() else {}
        fx["binding"](True)
        adm = run_gate_admission(fx, "workbuddy")
        per = [x for x in adm.get("per_slot", []) if x.get("slot_id", "") == SLOT_ID]
        per = (per or adm.get("per_slot", [{}]))[0]
        rec("W14_timeout_verified_positive", "evidence",
            {"formal_admission": per.get("formal_admission"), "fails": per.get("fails", []),
             "status": meta.get("status"),
             "envelope_verified_stop": env_doc.get("verified_stop"),
             "envelope_checks": env_doc.get("checks"),
             "runner_native_stop_key": "native_stop" in meta,
             "criterion": "真实 verified 超时（DB 终态+trace 稳定+无 scoped 进程）→"
                          "gate timeout 真值表应 formal=true（R1）"})

    # ---- W6 v3.5 纪律：unverified stop → checker0/judge null/信封 false 原物/HALT/后槽零 send ----
    if run_case("W6_timeout_writing_conservative"):
        ws = work / "ws-w6"
        r = run_run_impl(fx, "timeout_writing", ws, case_root, slot_idx=3, dry=False)
        res = r.get("result") or {}
        meta = res.get("meta") or {}
        ev = Path(res.get("evidence_dir") or "")
        ns = json.loads((ev / "native-stop.json").read_text()) if (ev / "native-stop.json").is_file() else {}
        de = json.loads((ev / "deadline-evidence.json").read_text()) if (ev / "deadline-evidence.json").is_file() else {}
        flags = {
            "status_timeout": res.get("status") == "timeout" or meta.get("status") == "timeout",
            "checker_ran_false": res.get("checker_ran") is False,
            "partial_stop_unverified": res.get("partial_stop_unverified") is True,
            "evidence_dir": str(ev),
            "reward_null": meta.get("reward") is None,
            "weighted_null": meta.get("weighted") is None,
            "judge_null": meta.get("judge") is None,
            "envelope_present_verified_false": ns.get("verified_stop") is False
                                               and ns.get("kind") == "native_stop",
            "envelope_slot": ns.get("slot_id"),
            "deadline_evidence": de.get("timed_out") is True,
            "no_checker_stdout": not (ev / "checker.stdout").exists(),
            "no_score_receipt": not (ev / "score-receipt.json").exists(),
            "halt_persisted": (fx["WBG"] / "receipts" / "HALT.json").is_file(),
        }
        # 后槽零 send：HALT 在位时新槽须拒，driver 零调用
        r2 = run_run_impl(fx, "completed", work / "ws-w6b", case_root, slot_idx=1, dry=False)
        res2 = r2.get("result") or {}
        acc2 = res2.get("accounting") or {}
        flags["next_slot_refused"] = (isinstance(acc2, dict) and acc2.get("execution_state") == "not_executed") or res2.get("claim") is None
        flags["next_slot_zero_send"] = res2.get("calls") == [] or not res2.get("calls")
        rec("W6_timeout_writing_conservative", "evidence",
            dict(flags, accounting=res.get("accounting"),
                 diag=((meta.get("diagnostic") or {}).get("detail") or "")[:160],
                 next_calls=res2.get("calls"),
                 next_accounting=res2.get("accounting"),
                 stderr_tail=r["stderr_tail"][-300:],
                 criterion="W6 纪律：stop 未验证 → 不 collect 不跑 checker 不冻结动态 workspace；"
                           "judge/score null；native-stop false 原物+deadline 快照；持久 HALT；后槽零 send"))
        (fx["WBG"] / "receipts" / "HALT.json").unlink(missing_ok=True)  # 采证后解除，勿连坐后续用例

    # ---- W7 重复/崩溃窗口零外发（claim O_EXCL）----
    if run_case("W7_claim_repeat_crash"):
        ws = work / "ws-w7"
        slot7_id = "l4-20261029-wb-gateway-dabstep-payments-10-r1"
        claim = fx["WBG"] / "receipts" / "claims" / (slot7_id + ".claim")
        r1 = run_run_impl(fx, "completed", ws, case_root, slot_idx=1)
        b1 = claim.read_bytes() if claim.exists() else None
        r2 = run_run_impl(fx, "completed", ws, case_root)
        res2 = r2.get("result") or {}
        sends2 = sum(1 for c in (res2.get("calls") or []) if isinstance(c, list) and c and c[0] == "new_task")
        b2 = claim.read_bytes() if claim.exists() else None
        shutil.rmtree(ws, ignore_errors=True)
        r3 = run_run_impl(fx, "completed", ws, case_root)
        res3 = r3.get("result") or {}
        sends3 = sum(1 for c in (res3.get("calls") or []) if isinstance(c, list) and c and c[0] == "new_task")
        b3 = claim.read_bytes() if claim.exists() else None
        REFUSE = {"claim-refused", "registration-exists-refused", "not_executed"}
        rec("W7_claim_repeat_crash", "pass" if (
            res2.get("status") in REFUSE and sends2 == 0
            and res3.get("status") in REFUSE and sends3 == 0
            and b1 == b2 == b3 and b1) else "fail",
            {"7a_repeat": {"status": res2.get("status"), "sends": sends2},
             "7b_crash_window": {"status": res3.get("status"), "sends": sends3},
             "claim_immutable": b1 == b2 == b3, "claim_bytes": len(b1 or b"")})

    # ---- W8 漂移检测 ----
    if run_case("W8_upgrade_drift"):
        spec = importlib.util.spec_from_file_location(
            "l4wbr_d", fx["WBG"] / "runner" / "l4_wb_runner.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        v1 = {"app_version": "5.9.3", "app_asar_sha256": "a" * 64}
        unit_pos = m.detect_upgrade_drift(v1, {"app_version": "5.9.4", "app_asar_sha256": "a" * 64})
        unit_neg = m.detect_upgrade_drift(v1, dict(v1))
        src = (fx["WBG"] / "runner" / "l4_wb_runner.py").read_text(encoding="utf-8")
        rec("W8_upgrade_drift", "pass" if (unit_pos is True and unit_neg is False
                                           and "upgrade_stop_remaining" in src) else "fail",
            {"unit_detects_change": unit_pos, "unit_same_is_clean": unit_neg,
             "run_impl_stop_remaining_key": "upgrade_stop_remaining" in src,
             "note": "真实模式前后 app_state 比对属 E 后路径；此处验证检测单元与停余标记"})

    # ---- W12 native_stop 信封 gate 准入正/负对 ----
    if run_case("W12_native_stop_gate_pair"):
        base_src = fx["WBG"] / "selftest" / "dry-evidence" / "bird-ca-schools-15"
        if not (base_src / "meta.json").exists():
            rec("W12_native_stop_gate_pair", "evidence",
                {"skipped": "dry-evidence 缺失（前置用例失败），无 base 证据"})
        else:
            dst = publish_dry_to_real(fx)  # bird 槽（未被他用例发布过）
            meta = json.loads((dst / "meta.json").read_text())
            plan = json.loads((fx["L4"] / "plan.json").read_text())
            slot0 = [s for s in plan["product_slots"]
                     if s["stratum"] == "wb_gateway_delivery"][0]
            meta["status"] = "timeout"
            meta["timed_out"] = True
            meta["duration_s"] = slot0["timeout_s"] + 1
            meta["attempts"] = [{"n": 1, "started_at": meta.get("started_at") or fx["tE"],
                                 "outcome": "timeout"}]
            meta["stop_info"] = {"stop_verified": True, "cancel_at": fx["tE"],
                                 "cancel_invoked": True, "post_cancel_db": "cancelled",
                                 "post_cancel_trace_stable": True}
            env_doc = {"kind": "native_stop", "verified_stop": True,
                       "session_id": "mock-session-0001", "at": fx["tE"],
                       "post_cancel_db": "cancelled",
                       "post_cancel_trace_stable": True, "live_doc_drift": []}
            b = json.dumps(env_doc, ensure_ascii=False, indent=2).encode()
            (dst / "native-stop.json").write_bytes(b)
            meta["native_stop"] = {"file": "native-stop.json",
                                   "sha256": hashlib.sha256(b).hexdigest()}
            jdump(dst / "meta.json", meta)
            fx["binding"](True)
            pos = run_gate_admission(fx, "workbuddy")
            (dst / "native-stop.json").unlink(missing_ok=True)
            meta.pop("native_stop", None)
            jdump(dst / "meta.json", meta)
            neg = run_gate_admission(fx, "workbuddy")
            shutil.rmtree(dst, ignore_errors=True)
            def _bird(d):
                per = [x for x in d.get("per_slot", []) if x.get("slot_id") == SLOT_ID]
                return (per or d.get("per_slot", [{}]))[0]
            posn, negn = _bird(pos), _bird(neg)
            pos = {"formal": posn.get("formal_admission"), "fails": posn.get("fails", [])}
            neg = {"formal": negn.get("formal_admission"), "fails": negn.get("fails", [])}
            neg_hit = any("native" in f.lower() for f in neg.get("fails", []))
            pos_ok = not any("native" in f.lower() for f in pos.get("fails", []))
            rec("W12_native_stop_gate_pair", "evidence",
                {"neg_without_envelope": neg, "pos_with_envelope": pos,
                 "neg_rejects_for_missing_envelope": neg_hit,
                 "pos_envelope_accepted_by_gate": pos_ok,
                 "runner_writes_native_stop_key": False,
                 "conclusion": "gate 侧信封契约可用；runner 未产 meta.native_stop 信封 → "
                               "现状 WB 超时保守不准入（正确），不得宣称同构已接通"})

    # ---- W13 正常 completed → 真 gate formal_admission 正例（lead 终局要求）----
    if run_case("W13_normal_completed_admission"):
        # 真链：dry=False（RecorderDriver 正常完成+写 workspace 产物）→ runner 真 collect/
        # checker/judge/score-receipt → 证据落 plan 声明的 runs 路径 → 真 gate 准入
        ws = work / "ws-w13"
        claim13 = fx["WBG"] / "receipts" / "claims" / (SLOT_ID + ".claim")
        claim13.unlink(missing_ok=True)  # 测试卫生：前序用例孤儿 claim 不连坐本正例
        shutil.rmtree(fx["WBG"] / "runs" / SLOT_ID, ignore_errors=True)
        r = run_run_impl(fx, "completed", ws, case_root, slot_idx=0, dry=False)
        res = r.get("result") or {}
        meta = res.get("meta") or {}
        ev_dir = Path(res.get("evidence_dir") or meta.get("evidence_dir") or "")
        sr = ev_dir / "score-receipt.json"
        sr_ok = sr.is_file()
        fx["binding"](True)
        adm = run_gate_admission(fx, "workbuddy")
        per = [x for x in adm.get("per_slot", []) if x.get("slot_id") == SLOT_ID]
        per = (per or adm.get("per_slot", [{}]))[0]
        rec("W13_normal_completed_admission", "evidence",
            {"formal_admission": per.get("formal_admission"),
             "fails": per.get("fails", []),
             "status": meta.get("status"), "reward": meta.get("reward"),
             "weighted": meta.get("weighted"),
             "judge_keys": sorted((meta.get("judge") or {}).keys()),
             "score_receipt_exists": sr_ok,
             "meta_order": meta.get("order"),
             "meta_exit_code": meta.get("exit_code"),
             "evidence_dir": str(ev_dir),
             "stderr_tail": r["stderr_tail"][-300:],
             "criterion": "桌面正常场真实 run_impl 全链（含 checker/judge/score-receipt）"
                          "→ 真 gate formal=True/fails=[]（作者 T19 同构独立复算）"})

    # ---- 哨兵汇总 ----
    sentinel = {}
    for lg in sorted(fx["work"].glob("sentinel*.log")):
        lines = [l for l in lg.read_text().splitlines() if l.strip()]
        sentinel[lg.name] = {"attempts": len(lines),
                             "non_local": sum(1 for l in lines if "allowed=False" in l)}
    receipt = {
        "kind": "judge_fake_e2e_receipt_v2", "harness": "wb_fake_e2e.py",
        "harness_sha256": sha_file(Path(__file__).resolve()),
        "snapshot": str(snap),
        "snapshot_head_shas": {n: sha_file(snap / n) for n in
                               ("src-wb/runner/l4_wb_runner.py", "src-wb/runner/safe_driver.py",
                                "src-wb/runner/verify_execution.py", "plan.json",
                                "contract.json", "gate.py", "execution_seal.py")},
        "fixture_repo": str(fx["REPO"]), "binding_E": fx["E"], "registered_at": fx["tE"],
        "generated_at": now_iso(), "cases": cases, "sentinel": sentinel,
        "live_doc_drift": None,
    }
    outp = out_dir / "wb-fake-e2e-v2-receipt.json"
    if outp.exists():
        outp = out_dir / ("wb-fake-e2e-v2-receipt.%d.json" % int(time.time()))
    jdump(outp, receipt)
    print(json.dumps({"receipt": str(outp),
                      "verdicts": {k: v["verdict"] for k, v in cases.items()}},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
