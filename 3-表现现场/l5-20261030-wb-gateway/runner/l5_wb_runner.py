#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""l4_wb_runner.py — L4 WorkBuddy 独立网关正式五题批次运行器（task-6，完整实现）。

层名（展示全称，CLARIFICATION-L4-1 R2）：
  「WB 产品交付态（历史证据指向网关；本批路由状态单列）」

子命令：
  preflight               零模型静态环境预检（不启动 WB、不建会话、不发请求）
  preflight --live        E 释放后的非干扰驱动预检（CDP 复用/空闲启动；绝不 SIGTERM）
  selftest                合成正反例（含 mock 驱动全路径干跑，零真实交互零调用）
  verify-execution PATH   共同 gate 薄适配
  run-slot SLOT [--dry]   单槽执行：真实模式 E 释放前机械拒绝；--dry 用 mock 驱动走
                          完整 send/poll/timeout/trace/archive/checker/accounting 路径
  accounting              汇总 slot-accounting 帧

红线：不改网络/代理/keychain/settings/更新配置；E 前零调用；自动升级停剩余 slot 不补跑；
whole_execution_restarts=0（attempts 恒 1）；不读 2-用例 truth/solution 内容
（仅机械哈希/复制/执行冻结 checker）；不录屏。
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parents[1]
L5 = REPO / "1-评测方案" / "自动循环L5-2026-10-30"
PLAN_PATH = L5 / "plan.json"
CONTRACT_PATH = L5 / "contract.json"
BINDING_PATH = L5 / "runtime-binding.json"
CASE_ROOT = REPO / "2-用例"
WORKSPACE_ROOT = Path.home() / "bench-workspaces" / "l5-20261030-wb-gateway"
WB_APP = Path("/Applications/WorkBuddy.app")
GATE_PATH = REPO / "1-评测方案" / "工具链" / "l5-execution" / "gate.py"
TZ = timezone(timedelta(hours=8))
STRATUM_DISPLAY = "WB 产品交付态（历史证据指向网关；本批路由状态单列）"
R2_EVIDENCE = "1-评测方案/准入预检-2026-10-29/wb-preflight-r2.json"
CONTAMINATION_PATTERNS = ["2-用例", "truth.json", "checker.py", "reference/",
                          "solution/", "../", "~/Documents", "harness-compare-bench"]

sys.path.insert(0, str(HERE / "runner"))
from verify_execution import verify_execution as adapter_verify_execution  # noqa: E402
import safe_driver  # noqa: E402


def sha256_file(p) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def load_json(p: Path):
    return json.load(open(p, encoding="utf-8"))


def write_json_atomic(p: Path, obj) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(p)
    return p


def wb_slots() -> list:
    plan = load_json(PLAN_PATH)
    return [s for s in plan["product_slots"] if s.get("stratum") == "wb_gateway_delivery"]


def binding_gate() -> dict:
    """薄适配：必须过共同 gate（E blob/漂移/manifest/时刻全查），失败即零调用。"""
    return adapter_verify_execution(BINDING_PATH)


def binding_values() -> dict:
    """读取 runtime-binding（仅供 gate 通过后取 registered_at 等字段）。"""
    return load_json(BINDING_PATH)


def detect_upgrade_drift(before: dict, after: dict) -> bool:
    """运行前后版本/asar 哈希比较：任一不一致即漂移（停剩余槽，不补跑）。"""
    return (before.get("app_version") != after.get("app_version")
            or before.get("app_asar_sha256") != after.get("app_asar_sha256"))


def app_state() -> dict:
    v = subprocess.run(["plutil", "-extract", "CFBundleShortVersionString", "raw",
                        str(WB_APP / "Contents" / "Info.plist")],
                       capture_output=True, text=True).stdout.strip()
    return {"app_version": v,
            "app_asar_sha256": sha256_file(WB_APP / "Contents" / "Resources" / "app.asar")}


# ================================================================ R1 记账
def accounting_frame(slot: dict) -> dict:
    """R7 修复：真实解析逐槽记账文件（L4 缺陷=恒 null：未读 evidence_dir）。"""
    cfg = load_json(HERE / "runner" / "runner-config.json")
    frame = {
        "slot_id": slot["slot_id"], "run_id": slot["run_id"],
        "event_id": slot["event_id"], "case": slot["case"], "order": slot["order"],
        "rep": slot["rep"], "stratum": "wb_gateway_delivery",
        "stratum_display": STRATUM_DISPLAY,
        "plan_sha256": sha256_file(PLAN_PATH),
        "design_commit_ref": cfg["design_seal_commit_D"],
        "execution_seal_commit_ref": None,
        "evidence_dir": slot["evidence_dir"],
        "execution_state": None,          # executed | partial | not_executed
        "reason": None, "stop_source": None,
        "started_at": None, "session": None, "usage": None, "score": None,
        "formal_admission": None,         # 恒值语义见 note；解析到记账后按真值填
        "formal_admission_note": "not_executed/infrastructure 恒 false；"
                                 "ok/timeout 由共同 gate --admission 判定（runner 不自行宣布）",
        "timed_out": None,
        "accounting_complete_note": "R1: 完整记账与 formal_admission 是两种判定",
    }
    try:
        ev_dir = HERE / Path(slot["evidence_dir"]).relative_to(
            f"3-表现现场/{HERE.name}")
    except ValueError:
        ev_dir = Path(slot["evidence_dir"])
    ne_p = ev_dir / "notexecuted.json"
    meta_p = ev_dir / "meta.json"
    acc_p = ev_dir / "slot-accounting.json"
    if ne_p.is_file():
        ne = load_json(ne_p)
        frame.update({"execution_state": "not_executed", "reason": ne.get("reason"),
                      "stop_source": ne.get("stop_source"),
                      "formal_admission": False, "score": None})
    elif meta_p.is_file():
        try:
            m = load_json(meta_p)
            frame["started_at"] = m.get("started_at")
            frame["session"] = ((m.get("attempts") or [{}])[0].get("session_id")
                                if m.get("attempts") else None)
            frame["usage"] = m.get("usage")
            frame["timed_out"] = m.get("timed_out")
            frame["score"] = ({"reward": m.get("reward"), "weighted": m.get("weighted")}
                              if m.get("weighted") is not None else None)
            frame["execution_state"] = ("executed" if m.get("status") in ("ok", "timeout")
                                        else "partial")
        except Exception as e:
            frame["execution_state"] = "partial"
            frame["reason"] = f"meta 解析失败: {e}"
    elif acc_p.is_file():
        try:
            a = load_json(acc_p)
            frame.update({"execution_state": a.get("execution_state"),
                          "reason": a.get("reason"),
                          "formal_admission": a.get("formal_admission")})
        except Exception as e:
            frame["reason"] = f"accounting 解析失败: {e}"
    return frame


def acc_not_executed(slot: dict, reason: str, stop_source: str) -> dict:
    f = accounting_frame(slot)
    f.update({"execution_state": "not_executed", "reason": reason,
              "stop_source": stop_source, "formal_admission": False})
    return f


def acc_infrastructure(slot: dict, reason: str, evidence_loc: str, diag_score=None) -> dict:
    f = accounting_frame(slot)
    f.update({"execution_state": "partial", "reason": reason, "score": diag_score,
              "formal_admission": False, "evidence_locator": evidence_loc})
    return f


def acc_executed(slot: dict, score, timed_out: bool, evidence_loc: str,
                 diag: str | None = None) -> dict:
    f = accounting_frame(slot)
    f.update({"execution_state": "executed", "timed_out": timed_out, "score": score,
              "formal_admission": None,  # pending 共同 gate --admission
              "reason": diag or "全执行证据齐备",
              "evidence_locator": evidence_loc})
    return f


# ================================================================ meta
def build_meta_frame(slot: dict, registered_at: str, preregistration_commit: str) -> dict:
    return {
        "batch": "l5-20261030-wb-gateway",
        "rule_version": load_json(CONTRACT_PATH)["rule_version"],
        "preregistration_commit": preregistration_commit,
        "registered_at": registered_at,
        "rep": slot["rep"], "product": slot["product"], "case": slot["case"],
        "form": "desktop-auto-cdp-rpc",
        "slot_id": slot["slot_id"],
        "order": slot["order"],
        "run_id": slot["run_id"], "event_id": slot["event_id"],
        "selection": {"plan_id": load_json(PLAN_PATH)["plan_id"],
                      "slot_id": slot["slot_id"], "order": slot["order"],
                      "kind": "first"},
        "workspace": None,
        "model": "deepseek-v4.1-flash",
        "declared_alias": "deepseek-v4.1-flash",
        "actual_request_model": None,
        "actual_request_model_status": "not_observable_in_this_batch（不可观测≠已证）",
        "alias_evidence": None,
        "reasoning_effort": "low（会话级声明设置；上游解释不可观测→managed unknown）",
        "product_version": None,
        "app_asar_sha256": None,
        "route": {"host": None, "provider_id": "workbuddy-gateway（产品交付态）",
                  "wire_protocol": "unobservable（TLS 端到端）", "endpoint": None,
                  "actual_gateway": "unknown",
                  "declared_alias": "deepseek-v4.1-flash",
                  "alias_evidence": None,
                  "route_verification": "current_not_observed",
                  "validation": "current_not_observed",
                  "r2_history_ref": R2_EVIDENCE},
        "tools": [],
        "soft_constraints": ["离线题解约束（workspace 仅 inputs+TASK）"],
        "permissions": "fullAccess（wb:conversations:create 参数，DB 可核）",
        "skills": "record actual from trace；不可观测项 managed unknown",
        "web_search": "off（未启用；以 trace 审计为准）",
        "prompt_sha256": None,
        "isolation": {"ok": None, "workspace_outside_repo": True},
        "inputs": [],
        "created_at": None, "started_at": None, "finished_at": None, "duration_s": None,
        "status": None, "exit_code": None,
        "attempts": [], "transport_retries": 0, "transport_retry_events": [],
        "stdout_bytes": None, "stderr_bytes": None,
        "stdout_sha256": None, "stderr_sha256": None,
        "stdout_source": "product-native-trace（WB 无 CLI stdout 流；canonical=会话 jsonl）",
        "usage": {"per_call": [], "note": "WB 原生 rawUsage 逐调用落盘；缺失保留 null 不填 0"},
        "reward": None, "weighted": None, "failed": [], "judge": None,
        "integrity": None, "integrity_verdict": None,
        "stratum": "wb_gateway_delivery",
        "stratum_display": STRATUM_DISPLAY,
        "timeout_s": slot["timeout_s"],
        "managed_unknowns": [
            {"item": "gateway_upstream_model",
             "impact": "网关服务端上游模型权重/供应商不可观测；不能参与同模型/同路由因果比较",
             "next_step": "如需闭环向产品方索取披露", "stop_condition": "披露或本批结束即停"},
            {"item": "gateway_host_current",
             "impact": "本批无被动网络取证时 actual_gateway 不可观察",
             "next_step": "route_validation=current_not_observed + r2 历史依据",
             "stop_condition": "本批不主动做网络取证（无干扰纪律）"},
            {"item": "effort_upstream_interpretation",
             "impact": "declared thought_level=low 的上游解释不可观测",
             "next_step": "逐场登记 DB 会话行值", "stop_condition": "本批结束即停"},
            {"item": "internal_tools_skills",
             "impact": "产品内部工具/skills 开关不可见",
             "next_step": "以 trace 可见行为审计为准", "stop_condition": "本批结束即停"},
        ],
        "timed_out": None,
        "stop_info": None,
        "driver": {"snapshot_sha256":
                   sha256_file(HERE / "driver-snapshot" / "workbuddy_driver.py"),
                   "sigterm_branch": "structurally disabled (runner/safe_driver.py)"},
    }


# ================================================================ 驱动 API
class RealDriver:
    """安全 driver 包装（结构性禁用 SIGTERM 分支）的真实实现。"""

    def __init__(self, port: int = 9332):
        self.port = port
        self.wd, self.ensure_safe, self.branch_log = safe_driver.install_safe_driver(port)

    def ensure_app(self) -> str:
        return self.ensure_safe(self.port)

    def new_task(self, **kw):
        return self.wd.new_task(**kw)

    def collect(self, **kw):
        return self.wd.collect(**kw)

    def wait_strict(self, task_id, timeout_s, workspace_dir, on_deadline=None):
        return safe_driver.wait_completion_strict(
            self.wd, task_id, timeout_s, workspace_dir, on_deadline=on_deadline)

    def page_target_ready(self, timeout_s=120, poll_s=2):
        return safe_driver.wait_page_target_ready(self.port, timeout_s, poll_s)

    def cancel(self, conv_id):
        return safe_driver.cancel_session(self.wd, conv_id)


class MockDriver:
    """干跑驱动：零真实交互；trace 来自夹具；记录全部调用参数供自检。"""

    def __init__(self, fixture_session_dir: Path, timeout_unverified: bool = False,
                 timeout_verified: bool = False, page_ready: bool = True):
        self.fixture_session_dir = Path(fixture_session_dir)
        self.timeout_unverified = timeout_unverified
        self.timeout_verified = timeout_verified
        self.page_ready = page_ready
        self.calls = []

    def ensure_app(self) -> str:
        self.calls.append({"api": "ensure_app"})
        return "mock-reused"

    def new_task(self, workspace_dir, prompt_text, model="DeepSeek V4.1-Flash",
                 title=None, port=9332, **kw):
        self.calls.append({"api": "new_task", "workspace_dir": workspace_dir,
                           "model": model, "prompt_chars": len(prompt_text),
                           "thought_level": kw.get("thought_level")})
        return {"id": "mock-session-0001", "started_at": now_iso(),
                "prompt_chars": len(prompt_text), "model": "deepseek-v4.1-flash",
                "title": title or "dry-run", "jsonl": "(mock)"}

    def wait_strict(self, task_id, timeout_s, workspace_dir=None, on_deadline=None):
        self.calls.append({"api": "wait_strict", "task_id": task_id,
                           "timeout_s": timeout_s})
        if self.timeout_verified:
            return {"status": "timeout", "ended_at": now_iso(),
                    "stop_info": {"stop_verified": True, "cancel_invoked": True,
                                  "cancel_at": now_iso(),
                                  "post_cancel_db": "cancelled",
                                  "post_cancel_db_terminal_seen": True,
                                  "post_cancel_db_flapped": False,
                                  "post_cancel_trace_stable": True,
                                  "post_cancel_processes": [],
                                  "deadline_reached_at": now_iso(),
                                  "deadline_snapshot": {"db_status": "active",
                                                        "trace_bytes": 100}},
                    "evidence": {"db_status": "cancelled", "trace_bytes": 100}}
        if self.timeout_unverified:
            return {"status": "timeout", "ended_at": now_iso(),
                    "stop_info": {"stop_verified": False, "cancel_invoked": False,
                                  "post_cancel_db": None,
                                  "post_cancel_db_terminal_seen": False,
                                  "post_cancel_db_flapped": False,
                                  "post_cancel_trace_stable": None,
                                  "post_cancel_processes": ["probe-error"],
                                  "deadline_reached_at": now_iso(),
                                  "deadline_snapshot": {"db_status": "active",
                                                        "trace_bytes": 100}},
                    "evidence": {"db_status": "active", "trace_bytes": 100}}
        return {"status": "completed", "ended_at": now_iso(),
                "stop_info": {"stop_verified": None},
                "evidence": {"db": {"id": task_id, "status": "completed",
                                    "model": "deepseek-v4.1-flash",
                                    "thought_level": "low", "mode": "craft"},
                             "jsonl": {"exists": True}, "waited_s": 0.0}}

    def cancel(self, conv_id):
        self.calls.append({"api": "cancel", "conv_id": conv_id})
        return {"mock": True}

    def page_target_ready(self, timeout_s=120, poll_s=2):
        self.calls.append({"api": "page_target_ready", "ready": self.page_ready})
        return {"ready": self.page_ready, "waited_s": 0.0, "polls": 1,
                "timeout_s": timeout_s, "poll_s": poll_s}

    def collect(self, task_id, dest_dir, workspace_dir=None):
        self.calls.append({"api": "collect", "task_id": task_id, "dest_dir": dest_dir})
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)
        files = []
        for f in sorted(self.fixture_session_dir.iterdir()):
            if f.is_file():
                shutil.copy2(f, dest / f.name)
                files.append(f.name)
        return {"files": files}




# ================================================================ 执行核心
def setup_workspace(case_root: Path, ws: Path) -> dict:
    """inputs 机械复制 + TASK.md 生成（被测 agent 不接触仓库）。已存在即拒绝。"""
    if ws.exists():
        raise RuntimeError(f"workspace 已存在（不覆盖）：{ws}")
    ws.mkdir(parents=True)
    inputs = []
    src_inputs = case_root / "inputs"
    for p in sorted(src_inputs.rglob("*")):
        rel = p.relative_to(src_inputs)
        dst = ws / "inputs" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if p.is_dir():
            dst.mkdir(exist_ok=True)
            continue
        shutil.copy2(p, dst)
        inputs.append({"path": f"inputs/{rel}", "sha256": sha256_file(p),
                       "bytes": p.stat().st_size})
    instruction = (case_root / "instruction.md").read_text(encoding="utf-8").rstrip()
    task = (f"# 本场任务：l5-20261030-wb-gateway（WB 产品交付态）\n\n"
            f"**你的工作目录（绝对路径）：`{ws}`**\n\n"
            "请在这个目录里工作：输入都在该目录的 `inputs/` 下，产物按题目要求写到该目录里"
            "（题目里的相对路径都相对这个目录）。除题目明确要求修改的代码外，"
            "不要改动 `inputs/` 下的文件。\n\n---\n\n" + instruction + "\n")
    (ws / "TASK.md").write_text(task, encoding="utf-8")
    outside_repo = not str(ws).startswith(str(REPO))
    return {"task_text": task, "prompt_sha256": hashlib.sha256(task.encode()).hexdigest(),
            "inputs": inputs,
            "isolation": {"ok": outside_repo and (ws / "TASK.md").is_file(),
                          "workspace_outside_repo": outside_repo}}


def register_call(slot: dict, reg_dir: Path, refs: dict) -> Path:
    """R3：调用登记先持久，后发送。"""
    reg = {"slot_id": slot["slot_id"], "run_id": slot["run_id"],
           "event_id": slot["event_id"], "case": slot["case"], "order": slot["order"],
           "kind": "first", "stratum": "wb_gateway_delivery",
           "registered_at": now_iso(),
           "design_commit_ref": refs.get("design_commit"),
           "execution_seal_commit_ref": refs.get("execution_seal_commit"),
           "plan_sha256": sha256_file(PLAN_PATH),
           "intent": "single-send, no retry, whole_execution_restarts=0"}
    reg_dir = Path(reg_dir)
    reg_dir.mkdir(parents=True, exist_ok=True)
    rp = reg_dir / f"{slot['run_id']}.registration.json"
    payload = json.dumps(reg, ensure_ascii=False, indent=2) + "\n"
    fd = os.open(rp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    with os.fdopen(fd, "w") as f:
        f.write(payload)
    return rp


def scan_contamination(trace_dir: Path) -> list:
    hits = []
    for p in sorted(trace_dir.rglob("*")):
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for pat in CONTAMINATION_PATTERNS:
            if pat in text:
                hits.append({"file": p.name, "pattern": pat})
    return hits


def parse_usage(jsonl_path: Path) -> list:
    per_call = []
    if not jsonl_path.is_file():
        return per_call
    for line in jsonl_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if "rawUsage" not in line or not line.startswith("{"):
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        found = {}

        def walk(x):
            if isinstance(x, dict):
                for k, v in x.items():
                    if k == "rawUsage" and isinstance(v, dict):
                        found.update(v)
                    else:
                        walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
        walk(o)
        if found:
            found["ts"] = o.get("timestamp")
            found["model_in_record"] = o.get("model") or (
                o.get("providerData") or {}).get("requestModelId")
            per_call.append(found)
    return per_call


def run_checker(checker_path: Path, ws: Path, expect_sha: str | None) -> dict:
    got = sha256_file(checker_path)
    if expect_sha is not None and got != expect_sha:
        raise RuntimeError(f"checker sha mismatch: want={expect_sha} got={got}")
    r = subprocess.run([sys.executable, str(checker_path), str(ws), "--json"],
                       capture_output=True, text=True)
    raw = r.stdout
    res = None
    for line in reversed([l for l in raw.splitlines() if l.strip().startswith("{")]):
        try:
            res = json.loads(line)
            break
        except Exception:
            continue
    weighted8 = None
    if res and isinstance(res.get("weighted"), (int, float)):
        weighted8 = round(float(res["weighted"]), 8)
    return {"ok": res is not None, "exit_code": r.returncode, "checker_sha256": got,
            "raw": raw, "reward": (res or {}).get("reward"), "weighted": weighted8,
            "failed": [c.get("id") for c in (res or {}).get("checks", [])
                       if isinstance(c, dict) and not c.get("pass")],
            "judge": res}


def claim_slot(slot: dict) -> Path:
    """固定 path 独占 claim（O_EXCL|O_NOFOLLOW）：重入即拒，不做时间戳幂等。"""
    claims = HERE / "receipts" / "claims"
    claims.mkdir(parents=True, exist_ok=True)
    claim = claims / f"{slot['slot_id']}.claim"
    payload = json.dumps({"slot_id": slot["slot_id"], "run_id": slot["run_id"],
                          "event_id": slot["event_id"], "claimed_at": now_iso(),
                          "pid": os.getpid(),
                          "design_commit_ref": load_json(
                              HERE / "runner" / "runner-config.json")["design_seal_commit_D"]},
                         ensure_ascii=False, indent=2) + "\n"
    fd = os.open(claim, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    with os.fdopen(fd, "w") as f:
        f.write(payload)
    return claim


def persist_halt(origin_slot: dict, reason: str) -> Path:
    """批级 halt（O_EXCL）：先序槽 stop 未验证时持久化，后续槽零 send。"""
    halt = HERE / "receipts" / "HALT.json"
    doc = {"kind": "batch_halt", "origin_slot_id": origin_slot["slot_id"],
           "origin_run_id": origin_slot["run_id"], "reason": reason,
           "at": now_iso(), "live_doc_drift": []}
    try:
        fd = os.open(halt, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
        with os.fdopen(fd, "w") as f:
            f.write(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    except FileExistsError:
        pass
    return halt


def validate_native_stop_binding(doc: dict, slot: dict, conversation_id: str,
                                 workspace: str) -> None:
    """native-stop 收据跨槽/跨 session 绑定校验：任一不符即拒绝（不得借用他槽原物）。"""
    if doc.get("slot_id") != slot["slot_id"]:
        raise RuntimeError(f"native_stop 绑定不符 slot_id: {doc.get('slot_id')!r}")
    if doc.get("run_id") != slot["run_id"]:
        raise RuntimeError(f"native_stop 绑定不符 run_id: {doc.get('run_id')!r}")
    if doc.get("conversation_id") != conversation_id:
        raise RuntimeError(f"native_stop 绑定不符 conversation_id: {doc.get('conversation_id')!r}")
    if doc.get("workspace") != workspace:
        raise RuntimeError(f"native_stop 绑定不符 workspace: {doc.get('workspace')!r}")
    if not isinstance(doc.get("verified_stop"), bool):
        raise RuntimeError("native_stop verified_stop 非 bool")


def derive_guards(judge: dict) -> dict:
    """R1（池 L5-1）：由 checker 原始 checks 推导 guards_used。
    k=len(checks)-n_tasks（非任务检查数）；guard 通过数=npass-correct；
    按 checks 原序枚举组合，首个和==guard_passes 即取；无解发 conflict 标记。"""
    checks = (judge or {}).get("checks") or []
    n_tasks = (judge or {}).get("n_tasks")
    correct = (judge or {}).get("correct")
    if (not isinstance(checks, list) or not isinstance(n_tasks, int)
            or not isinstance(correct, int)):
        return {"guards_used": None, "method": "insufficient_fields",
                "candidates": 0, "conflict": None}
    k = len(checks) - n_tasks
    npass = sum(1 for c in checks if c.get("pass") is True)
    guard_passes = npass - correct
    if k < 0 or guard_passes < 0 or guard_passes > k:
        return {"guards_used": None, "method": "conflict", "candidates": 0,
                "conflict": f"k={k} guard_passes={guard_passes}"}
    if k == 0:
        return {"guards_used": [], "method": "no_guards", "candidates": 1,
                "conflict": None}
    from itertools import combinations
    cands = 0
    for combo in combinations(range(len(checks)), k):
        cands += 1
        if sum(1 for i in combo if checks[i].get("pass") is True) == guard_passes:
            return {"guards_used": [checks[i].get("id", f"#{i}") for i in combo],
                    "method": "first_reconciling_in_order", "candidates": cands,
                    "conflict": None}
    return {"guards_used": None, "method": "conflict", "candidates": cands,
            "conflict": "no combination reconciles"}


def write_json_once(path: Path, obj):
    """R7 receipts write-once：目标已存在 ⇒ 拒写，另存带时间戳副本（不覆盖）。"""
    path = Path(path)
    if path.exists():
        ts = now_iso().replace(":", "").replace("+", "").replace("-", "")
        alt = path.with_name(f"{path.stem}-{ts}{path.suffix}")
        return write_json_atomic(alt, obj)
    return write_json_atomic(path, obj)


def persist_not_executed(ev_dir: Path, acc: dict) -> Path:
    """§E：not_executed → evidence_dir/notexecuted.json，目录内不得有其他文件。"""
    try:
        _E = load_json(BINDING_PATH).get("preregistration_commit")
    except Exception:
        _E = None
    ne = {"slot_id": acc["slot_id"], "run_id": acc["run_id"], "event_id": acc["event_id"],
          "preregistration_commit": _E, "reason": acc["reason"],
          "stop_source": acc.get("stop_source"), "at": now_iso(),
          "live_doc_drift": []}
    return write_json_atomic(Path(ev_dir) / "notexecuted.json", ne)


def run_impl(slot: dict, driver_api, *, dry: bool = False, case_root: Path = None,
             ws_root: Path = None, registered_at: str = None,
             preregistration_commit: str = None, execution_seal_commit: str = None,
             expect_checker_sha=None, evidence_root: Path = None) -> dict:
    """完整单槽执行：claim→setup→登记→ensure→send→严格poll/超时(cancel+验证)→
    collect→scan→usage→checker→meta→accounting（R1 真值表）。dry=True 零真实交互。"""
    contract = load_json(CONTRACT_PATH)
    case = slot["case"]
    case_root = Path(case_root) if case_root else (CASE_ROOT / case)
    ws_root = Path(ws_root) if ws_root else WORKSPACE_ROOT
    if dry:
        ev_dir = (Path(evidence_root) if evidence_root
                  else HERE / "selftest" / "dry-evidence") / case
    else:
        ev_dir = HERE / Path(slot["evidence_dir"]).relative_to(
            "3-表现现场/l5-20261030-wb-gateway")
    result = {"slot_id": slot["slot_id"], "dry": dry, "evidence_dir": str(ev_dir)}

    # 0-) 批级 halt：先序槽 stop 未验证 ⇒ 本槽零 send，持久 not_executed 记账
    halt_p = HERE / "receipts" / "HALT.json"
    if halt_p.exists():
        reason = ""
        try:
            reason = str(load_json(halt_p).get("reason"))[:200]
        except Exception:
            pass
        acc_h = acc_not_executed(slot, f"批级 halt 生效（先序槽 stop 未验证，零 send）：{reason}",
                                 "HALT.json")
        ev_dir.mkdir(parents=True, exist_ok=True)
        if dry:
            write_json_atomic(ev_dir / "slot-accounting.json", acc_h)
        else:
            persist_not_executed(ev_dir, acc_h)
        result["status"] = "halted"
        return result

    # 0) 固定 path 独占 claim（重入即拒；拒时不写任何槽内文件）
    try:
        claim_path = claim_slot(slot)
        result["claim"] = str(claim_path)
    except FileExistsError:
        result["status"] = "claim-refused"
        return result
    ev_dir.mkdir(parents=True, exist_ok=True)
    meta = build_meta_frame(slot, registered_at or "", preregistration_commit or "")

    # 0) 运行前产品状态（漂移→停剩余槽）
    if not dry:
        st = app_state()
        meta["product_version"], meta["app_asar_sha256"] = st["app_version"], st["app_asar_sha256"]
    else:
        meta["product_version"], meta["app_asar_sha256"] = "9.9.9-dry", "e" * 64

    # 1) workspace
    ws = Path(ws_root) / case
    try:
        setup_res = setup_workspace(case_root, ws)
    except Exception as e:
        acc2 = acc_not_executed(slot, f"workspace setup failed: {e}", "runner")
        if not dry:
            persist_not_executed(ev_dir, acc2)
        else:
            write_json_atomic(ev_dir / "slot-accounting.json", acc2)
        return {**result, "accounting": acc2, "status": "not_executed"}
    meta["workspace"] = str(ws)
    meta["prompt_sha256"] = setup_res["prompt_sha256"]
    meta["inputs"] = setup_res["inputs"]
    meta["isolation"] = setup_res["isolation"]
    if dry:
        meta["inputs_verification"] = {"ok": True, "checked": len(setup_res["inputs"]),
                                       "method": "fixture（干跑）"}
    else:
        want = (contract.get("case_snapshots") or {}).get(case, {}).get("files") or {}
        ok_all = bool(setup_res["inputs"]) and all(
            want.get(i["path"]) == i["sha256"] for i in setup_res["inputs"])
        meta["inputs_verification"] = {"ok": ok_all, "checked": len(setup_res["inputs"]),
                                       "method": "sha256 vs contract.case_snapshots.files（机械比对）"}

    # 2) 调用登记先持久（R3）
    cfg = load_json(HERE / "runner" / "runner-config.json")
    try:
        reg = register_call(slot, ev_dir / "registrations",
                            {"design_commit": cfg["design_seal_commit_D"],
                             "execution_seal_commit": execution_seal_commit})
    except FileExistsError:
        # 注册已存在＝先前 attempt 已登记；绝不二次 new_task 外发
        result["status"] = "registration-exists-refused"
        return result

    # 3) ensure（安全三分支）
    try:
        result["ensure"] = driver_api.ensure_app()
    except safe_driver.WBUnsafeState as e:
        acc2 = acc_not_executed(slot, f"非干扰接入不可得：{e}", "safe_driver struct")
        if not dry:
            persist_not_executed(ev_dir, acc2)
        else:
            write_json_atomic(ev_dir / "slot-accounting.json", acc2)
        return {**result, "accounting": acc2, "status": "not_executed"}

    # R6（池 L5-2）：发送前非生成式就绪轮询；超时 ⇒ not_executed，不重试不兜跑
    ready = driver_api.page_target_ready(
        timeout_s=cfg.get("renderer_ready_timeout_s", 120),
        poll_s=cfg.get("renderer_ready_poll_s", 2))
    meta["renderer_ready"] = {"ready": ready.get("ready"),
                              "waited_s": ready.get("waited_s"),
                              "polls": ready.get("polls"),
                              "timeout_s": cfg.get("renderer_ready_timeout_s", 120),
                              "poll_s": cfg.get("renderer_ready_poll_s", 2)}
    if not ready.get("ready"):
        acc2 = acc_not_executed(
            slot,
            f"R6 renderer-ready 超时（{cfg.get('renderer_ready_timeout_s', 120)}s 内无"
            f"可 attach page target）；发送前失败，不重试不兜跑",
            "safe_driver.wait_page_target_ready")
        if dry:
            write_json_atomic(ev_dir / "slot-accounting.json", acc2)
        else:
            persist_not_executed(ev_dir, acc2)
        result.update({"status": "not_executed", "renderer_ready": ready})
        return result

    # 4) 发送（attempts 恒 1）
    attempt_start = now_iso()
    task, send_exc = None, None
    try:
        task = driver_api.new_task(workspace_dir=str(ws),
                                   prompt_text=setup_res["task_text"],
                                   model="DeepSeek V4.1-Flash",
                                   title=f"l4 {case}", port=9332,
                                   thought_level="low")
    except Exception as e:
        send_exc = e
    meta["attempts"] = [{"n": 1, "started_at": attempt_start, "exit_code": None,
                         "outcome": "sent" if task else f"send-failed: {send_exc}"}]
    if task is None:
        acc2 = acc_infrastructure(slot, f"new_task failed: {send_exc}", str(reg))
        meta["status"] = "error"
        write_json_atomic(ev_dir / "meta.json", meta)
        write_json_atomic(ev_dir / "slot-accounting.json", acc2)
        return {**result, "accounting": acc2, "meta": meta, "status": "error"}

    # 5) 别名选择证据（R2）
    meta["alias_evidence"] = {
        "driver_create_model_param": "DeepSeek V4.1-Flash",
        "session_db_model_field": task.get("model"),
        "note": "collect 后以 session-row/jsonl requestModelId 复核；"
                "不可观察或非 deepseek-v4.1-flash → 停槽诊断"}

    # 6) 严格 poll/timeout（DB 终态+trace 稳定才算完成；active-idle 不算；
    #    到限先 cancel（产品原生通道）再验证停止，再冻结 deadline 证据）
    def _on_deadline(tid, snap):
        # 先冻结 deadline 证据（此刻即落盘，非事后补写），再发 cancel
        write_json_atomic(ev_dir / "deadline-evidence.json",
                          {"kind": "deadline_evidence", "run_id": slot["run_id"],
                           "timed_out": True, "deadline_reached_at": now_iso(),
                           "pre_cancel_snapshot": snap, "live_doc_drift": []})
        try:
            cres = driver_api.cancel(tid)
            return {"cancel_invoked": True, "cancel_at": now_iso(),
                    "cancel_result": json.dumps(cres, ensure_ascii=False,
                                                default=str)[:200]}
        except Exception as e:
            return {"cancel_invoked": False, "cancel_error": str(e)[:200]}

    wait = driver_api.wait_strict(task["id"], timeout_s=slot["timeout_s"],
                                  workspace_dir=str(ws),
                                  on_deadline=None if dry else _on_deadline)
    status_raw = wait.get("status", "timeout")
    meta["status"] = {"completed": "ok", "timeout": "timeout"}.get(status_raw, "error")
    meta["timed_out"] = meta["status"] == "timeout"
    meta["started_at"] = task.get("started_at")
    meta["created_at"] = task.get("started_at")
    meta["finished_at"] = wait.get("ended_at") or now_iso()
    meta["exit_code"] = None
    try:
        if meta["started_at"]:
            meta["duration_s"] = round(
                (datetime.fromisoformat(meta["finished_at"])
                 - datetime.fromisoformat(meta["started_at"])).total_seconds(), 3)
    except Exception:
        meta["duration_s"] = None

    # 6b) W6 纪律：stop 未验证 ⇒ 不 collect 不跑 checker 不冻结动态 workspace；
    #     native-stop 原物 verified_stop=false + 早退 partial（score=null）+ 持久 halt
    if meta["status"] == "timeout":
        si0 = wait.get("stop_info") or {}
        stop_verified0 = si0.get("stop_verified") is True
        if meta["attempts"]:
            meta["attempts"][0]["outcome"] = "timeout"
        checks0 = {"db_terminal": si0.get("post_cancel_db_terminal_seen") is True
                   and not si0.get("post_cancel_db_flapped"),
                   "trace_stable": si0.get("post_cancel_trace_stable") is True,
                   "no_scoped_processes": not si0.get("post_cancel_processes")}
        native_doc = {"kind": "native_stop", "slot_id": slot["slot_id"],
                      "run_id": slot["run_id"], "event_id": slot["event_id"],
                      "conversation_id": task["id"], "workspace": str(ws),
                      "verified_stop": stop_verified0,
                      "stop_kind": "wb:conversations:cancel",
                      "verified_at": now_iso() if stop_verified0 else None,
                      "cancel_invoked_at": si0.get("cancel_at"),
                      "deadline_reached_at": si0.get("deadline_reached_at"),
                      "checks": checks0,
                      "at": now_iso(), "live_doc_drift": []}
        validate_native_stop_binding(native_doc, slot, task["id"], str(ws))
        write_json_atomic(ev_dir / "native-stop.json", native_doc)
        meta["native_stop"] = {"file": "native-stop.json",
                               "sha256": sha256_file(ev_dir / "native-stop.json")}
        meta["stop_info"] = {k: si0.get(k) for k in
                             ("stop_verified", "cancel_at", "cancel_invoked",
                              "deadline_reached_at")}
        if not stop_verified0:
            # deadline 证据兜底（真实模式已在 on_deadline 先冻结；此处仅 dry/缺失时补记并如实标注）
            if not (ev_dir / "deadline-evidence.json").exists():
                write_json_atomic(ev_dir / "deadline-evidence.json",
                                  {"kind": "deadline_evidence", "run_id": slot["run_id"],
                                   "timed_out": True,
                                   "deadline_reached_at": si0.get("deadline_reached_at"),
                                   "pre_cancel_snapshot": si0.get("deadline_snapshot"),
                                   "backfilled": "非 on_deadline 实时冻结（dry/缺失兜底）",
                                   "live_doc_drift": []})
            persist_halt(slot, "stop_unverified: cancel 请求信号未获 DB 终态+trace 稳定"
                               "+无作用域进程三重验证证实")
            meta["selection"] = None
            meta["diagnostic"] = {"class": "stop_unverified",
                                  "detail": "cancel 未获三重验证证实——不得视为已安全停止；"
                                            "W6：不跑 checker 不评分；动态 workspace 不冻结归档",
                                  "checks": checks0}
            for k in ("reward", "weighted", "failed", "judge"):
                meta[k] = None
            write_json_atomic(ev_dir / "meta.json", meta)
            acc_w6 = acc_infrastructure(slot, "stop 未验证（W6）：checker 未调用、评分 null；"
                                             "动态 workspace 未冻结归档；halt 后续槽零 send",
                                        str(ev_dir))
            write_json_atomic(ev_dir / "slot-accounting.json", acc_w6)
            result.update({"status": "timeout", "checker_ran": False,
                           "partial_stop_unverified": True})
            return result

    # 7) collect + 证据布局（§C 默认名或 evidence_paths）+ 污染扫描 + usage
    trace_dir = ev_dir / "trace"
    if trace_dir.exists():
        shutil.rmtree(trace_dir)  # 防陈旧 trace 冒充本次 canonical
    driver_api.collect(task_id=task["id"], dest_dir=str(trace_dir), workspace_dir=str(ws))
    (ev_dir / "agent-session").mkdir(exist_ok=True)
    for f in ("session-row.json", "collect-meta.json"):
        src = trace_dir / f
        if src.exists():
            shutil.copy2(src, ev_dir / "agent-session" / f)
    (ev_dir / "prompt.txt").write_text(setup_res["task_text"], encoding="utf-8")
    (ev_dir / "agent.stderr.txt").write_text("", encoding="utf-8")  # 桌面形态无 stderr 流（0 字节事实）
    ws_snap = ev_dir / "workspace"
    if not ws_snap.exists():
        shutil.copytree(ws, ws_snap)
    jsonls = sorted(trace_dir.glob("*.jsonl"))
    canonical = jsonls[0] if jsonls else None
    meta["evidence_paths"] = {"prompt": "prompt.txt",
                              "stdout": f"trace/{canonical.name}" if canonical else None,
                              "stderr": "agent.stderr.txt",
                              "session": "agent-session", "workspace": "workspace"}
    meta["stdout_bytes"] = canonical.stat().st_size if canonical else 0
    meta["stdout_sha256"] = (sha256_file(canonical) if canonical
                             else hashlib.sha256(b"").hexdigest())
    meta["stderr_bytes"] = 0
    meta["stderr_sha256"] = hashlib.sha256(b"").hexdigest()
    hits = scan_contamination(trace_dir)
    meta["integrity"] = {"contamination_hits": hits, "scan_patterns": CONTAMINATION_PATTERNS,
                         "missing_trace": canonical is None}
    meta["integrity_verdict"] = "violation" if (hits or canonical is None) else "clean"
    meta["usage"]["per_call"] = parse_usage(canonical) if canonical else []
    if canonical is None:
        # 无原始 trace＝不冒充真实证据：状态降为 error（基础设施），不跑 checker 评分
        meta["status"] = "error"
        meta["integrity"]["diagnostic"] = ("canonical trace 缺失（collect 无 jsonl）；"
                                           "不产生 clean/ok 假象")
    session_row = trace_dir / "session-row.json"
    if session_row.is_file():
        row = load_json(session_row)
        meta["alias_evidence"]["session_db_model_field"] = row.get("model")
        meta["alias_evidence"]["session_db_thought_level"] = row.get("thought_level")
        meta["alias_evidence"]["source_records"] = {
            "session_row": "trace/session-row.json",
            "jsonl": [p.name for p in jsonls]}
        meta["route"]["alias_evidence"] = "agent-session/session-row.json"

    # 8) checker
    checker_path = case_root / "checker.py"
    expect = None
    if not dry:
        expect = contract["checker_sha256"][case]
    elif isinstance(expect_checker_sha, str):
        expect = expect_checker_sha
    jr = {"ok": False, "error": None}
    try:
        jr = run_checker(checker_path, ws, expect)
        meta["reward"] = jr["reward"]
        meta["weighted"] = jr["weighted"]
        meta["failed"] = jr["failed"]
        judge_obj = dict(jr["judge"] or {})
        judge_obj["checker_sha256"] = jr["checker_sha256"]
        judge_obj["exit_code"] = jr["exit_code"]
        judge_obj["raw_stdout_head"] = jr["raw"][:500]
        _g = derive_guards(jr["judge"] or {})
        judge_obj["guards_used"] = _g["guards_used"]
        judge_obj["guards_method"] = _g["method"]
        judge_obj["guards_candidates"] = _g["candidates"]
        if _g.get("conflict"):
            judge_obj["guards_conflict"] = _g["conflict"]
        meta["judge"] = judge_obj
        meta["weighted"] = (round(meta["weighted"], 8)
                            if isinstance(meta.get("weighted"), (int, float))
                            else meta.get("weighted"))
        # 原始 checker stdout 全文落盘（gate：evidence checker.stdout 必须存在且可解析，
        # 并与 receipt.raw_checker_output 逐字一致）
        (ev_dir / "checker.stdout").write_text(jr["raw"], encoding="utf-8")
        earned = jr["reward"] if isinstance(jr["reward"], (int, float)) else 0
        write_json_atomic(ev_dir / "score-receipt.json",
                          {"case": slot["case"], "product": slot["product"],
                           "run_id": slot["run_id"], "rep": slot["rep"],
                           "score": {"earned": earned,
                                     "possible": contract["denominators"][slot["case"]],
                                     "reported": round(jr["weighted"], 8),
                                     "checker_sha256": jr["checker_sha256"]},
                           "rule_version": contract["rule_version"],
                           "checker_sha256": jr["checker_sha256"],
                           "raw_checker_output": jr["judge"],
                           "at": now_iso(), "live_doc_drift": []})
    except Exception as e:
        meta["judge"] = {"error": str(e)}

    # 8a) 正常终态：native_terminal 原物（completed 才 formal；failed/error 如实记录待拒）
    if meta["status"] == "ok":
        nt_doc = {"kind": "native_terminal", "slot_id": slot["slot_id"],
                  "run_id": slot["run_id"], "event_id": slot["event_id"],
                  "conversation_id": task["id"], "workspace": str(ws),
                  "terminal": True, "state": "completed",
                  "verified_at": now_iso(),
                  "evidence": {"db_status": (wait.get("evidence") or {}).get("db_status"),
                               "trace_bytes": (wait.get("evidence") or {}).get("trace_bytes"),
                               "stable_s": (wait.get("evidence") or {}).get("stable_s")},
                  "live_doc_drift": []}
        nt_path = ev_dir / "native-terminal.json"
        fd = os.open(nt_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
        with os.fdopen(fd, "w") as f:
            f.write(json.dumps(nt_doc, ensure_ascii=False, indent=2) + "\n")
        meta["native_terminal"] = {"file": "native-terminal.json",
                                   "sha256": sha256_file(nt_path)}
    elif meta["status"] == "error" and (wait.get("evidence") or {}).get("db_status"):
        db_term = (wait.get("evidence") or {}).get("db_status")
        if db_term in ("failed", "error", "cancelled", "stopped"):
            nt_doc = {"kind": "native_terminal", "slot_id": slot["slot_id"],
                      "run_id": slot["run_id"], "event_id": slot["event_id"],
                      "conversation_id": task["id"], "workspace": str(ws),
                      "terminal": True, "state": db_term,
                      "verified_at": now_iso(), "live_doc_drift": []}
            write_json_atomic(ev_dir / "native-terminal.json", nt_doc)
            meta["native_terminal"] = {"file": "native-terminal.json",
                                       "sha256": sha256_file(ev_dir / "native-terminal.json")}

    # 9) accounting（R1 真值表）
    score_blk = ({"reported": meta["weighted"], "reward": meta["reward"]}
                 if meta["weighted"] is not None else None)
    if meta["status"] == "ok":
        acc = acc_executed(slot, score_blk, False, str(ev_dir))
    elif meta["status"] == "timeout":
        # 仅 stop_verified 路径可达（未验证已在 6b 早退 partial）
        acc = acc_executed(slot, score_blk, True, str(ev_dir),
                           diag="真实开始并达到事先题目时限；cancel 已发且三重验证通过"
                                "（DB 终态+trace 稳定+无作用域进程）；未完成任务按冻结 checker 处理")
    else:
        acc = acc_infrastructure(slot, f"status={meta['status']}", str(ev_dir),
                                 diag_score=score_blk)

    # 10) alias 复核（R2）
    db_model = (meta["alias_evidence"] or {}).get("session_db_model_field")
    if db_model != "deepseek-v4.1-flash":
        meta["alias_evidence"]["verdict"] = (
            f"alias 不可观察或非声明值（{db_model}）→ 停该槽，仅诊断")

    # 10b) 版本漂移比较（真实模式）：漂移即标记停剩余槽并记入 accounting
    if not dry:
        st_after = app_state()
        meta["app_asar_sha256_after"] = st_after["app_asar_sha256"]
        meta["app_version_after"] = st_after["app_version"]
        if detect_upgrade_drift(
                {"app_version": meta["product_version"],
                 "app_asar_sha256": meta["app_asar_sha256"]}, st_after):
            meta["upgrade_drift"] = True
            result["upgrade_stop_remaining"] = True
            acc["reason"] = (acc.get("reason") or "") +                 "；【版本漂移】运行前后 app 版本/asar 哈希不一致 → 停剩余槽，不补跑"
    else:
        meta["upgrade_drift"] = False

    # 11) 落盘
    write_json_atomic(ev_dir / "meta.json", meta)
    write_json_atomic(ev_dir / "slot-accounting.json", acc)
    result.update({"status": meta["status"], "meta": meta, "accounting": acc,
                   "task_id": task["id"]})
    return result


# ================================================================ preflight
def cmd_preflight(live: bool = False) -> int:
    checks = []
    ok = True

    def check(name, passed, detail):
        nonlocal ok
        ok = ok and bool(passed)
        checks.append({"check": name, "pass": bool(passed), "detail": str(detail)})

    contract = load_json(CONTRACT_PATH)
    actual_plan = sha256_file(PLAN_PATH)
    check("plan_sha256_matches_contract", actual_plan == contract["plan_sha256"],
          f"actual={actual_plan} contract={contract['plan_sha256']}")
    check("contract_file_readable", bool(sha256_file(CONTRACT_PATH)),
          sha256_file(CONTRACT_PATH))

    slots = wb_slots()
    plan = load_json(PLAN_PATH)
    # L5 批次形状：WB 仅 2 槽（PREREGISTRATION §3 固定），order 5/6
    check("wb_slot_count_is_2", len(slots) == 2, f"n={len(slots)}")
    check("wb_slot_order_5_6", [s["order"] for s in slots] == [5, 6],
          str([s["order"] for s in slots]))
    expect_cases = ["bird-ca-schools-15", "dabstep-payments-10"]
    check("wb_case_sequence", [s["case"] for s in slots] == expect_cases,
          str([s["case"] for s in slots]))
    expect_timeouts = {"bird-ca-schools-15": 1800, "dabstep-payments-10": 1800}
    check("wb_timeouts_match_plan",
          all(s["timeout_s"] == expect_timeouts[s["case"]] for s in slots),
          json.dumps({s["case"]: s["timeout_s"] for s in slots}))
    ids = [s["run_id"] for s in slots]
    check("wb_run_ids_unique", len(set(ids)) == 2, f"{len(set(ids))} unique")
    check("namespace_not_r1030_r1031",
          all(not rid.startswith(("r1030", "r1031")) for rid in ids),
          "prefix l5-20261030-wb-gateway")
    all_pids = [s["slot_id"] for s in plan["product_slots"]] + \
               [p["slot_id"] for p in plan.get("probe_slots", [])]
    check("all_plan_slot_ids_unique_repo_wide", len(set(all_pids)) == len(all_pids),
          f"n={len(all_pids)}")
    check("stratum_display_name", STRATUM_DISPLAY ==
          "WB 产品交付态（历史证据指向网关；本批路由状态单列）", STRATUM_DISPLAY)

    for s in slots:
        c = s["case"]
        p = CASE_ROOT / c / "checker.py"
        want = contract["checker_sha256"][c]
        got = sha256_file(p) if p.is_file() else None
        check(f"checker_sha256[{c}]", got == want, f"want={want} got={got}")

    sums = {}
    for line in (HERE / "driver-snapshot" / "SHA256SUMS.txt").read_text().strip().splitlines():
        h, rel = line.split(maxsplit=1)
        sums[rel.strip()] = h
    for rel, want in sums.items():
        got = sha256_file(HERE / rel)
        check(f"driver_snapshot[{rel}]", got == want, got)

    try:
        st = app_state()
        check("app_version_recorded", bool(st["app_version"]), st["app_version"])
        check("app_asar_sha256_recorded", len(st["app_asar_sha256"]) == 64,
              st["app_asar_sha256"])
    except Exception as e:
        check("app_version_recorded", False, str(e))

    wb_proj = Path.home() / ".workbuddy" / "projects"
    wb_db = Path.home() / ".workbuddy" / "workbuddy.db"
    check("trace_paths_exist", wb_proj.is_dir() and wb_db.is_file(),
          f"{wb_proj} | {wb_db}")
    du = subprocess.run(["df", "-k", str(Path.home())], capture_output=True, text=True).stdout
    free_kb = int(du.strip().splitlines()[-1].split()[3]) if du else -1
    check("home_disk_free_gt_5GB", free_kb > 5 * 1024 * 1024,
          f"free={free_kb // 1024 // 1024}GB")
    check("workspace_root_outside_repo",
          not str(WORKSPACE_ROOT).startswith(str(REPO)), str(WORKSPACE_ROOT))

    forbidden = ["network" + "setup", "scu" + "til", "security add-" + "trusted",
                 "http." + "proxy", "NODE_" + "OPTIONS", "HTTPS_" + "PROXY"]
    scan_targets = [Path(__file__), HERE / "runner" / "safe_driver.py",
                    HERE / "runner" / "verify_execution.py"]
    scan_src = "\n".join(p.read_text(encoding="utf-8") for p in scan_targets)
    for token in forbidden:
        check(f"no_forbidden_api[{token}]", token not in scan_src, "absent in runner sources")
    check("common_gate_present", GATE_PATH.is_file(), str(GATE_PATH))

    receipt = {"kind": "interface_preflight", "batch": "l5-20261030-wb-gateway",
               "stratum_display": STRATUM_DISPLAY,
               "mode": "static-zero-model" if not live else "live-noninterference",
               "at": now_iso(), "model_calls": 0, "all_pass": ok, "checks": checks,
               "live_doc_drift": [],
               "notes": ["live 驱动预检留待 E 释放后执行；本阶段不启动 WB、不建会话、不发请求",
                         "actual_gateway 本批默认 route_verification=current_not_observed，"
                         f"历史依据={R2_EVIDENCE}（CLARIFICATION-L4-1 R2）"]}
    out = write_json_once(HERE / "preflight" /
                          ("preflight-static.json" if not live else "preflight-live.json"),
                          receipt)
    print(f"[preflight] all_pass={ok} receipt={out}")
    return 0 if ok else 1


# ================================================================ selftest
class _FakeCDP:
    def __init__(self, port, timeout=60): pass
    def close(self): pass
    def connect(self): pass


def _raises(fn):
    try:
        fn()
        return False
    except Exception:
        return True


def cmd_selftest() -> int:
    import shutil as _sh
    results = []
    skipped = []
    ok = True
    GATE_PRESENT = GATE_PATH.exists()  # gate v2 由 freeze-engineer 并行在建；未就位则相关用例诚实跳过

    def t(name, passed, detail=""):
        nonlocal ok
        ok = ok and bool(passed)
        results.append({"test": name, "pass": bool(passed), "detail": str(detail)[:200]})

    def skip(name, reason):
        skipped.append({"test": name, "reason": reason})

    # ---- 自测资产清理（selftest 自有夹具，可重置；真实批次路径绝不触碰） ----
    import glob as _glob
    for d in ([HERE / "receipts" / "claims"]
              + [Path(x) for x in _glob.glob(str(HERE / "selftest" / "dry-*"))]):
        if d.is_dir():
            _sh.rmtree(d)
        elif d.exists():
            d.unlink()

    SLOT_A = wb_slots()[0]  # bird（order 5）
    SLOT_B = wb_slots()[1]  # dab（order 6）

    def reset_evidence_only(slot):
        ev = HERE / "selftest" / "dry-evidence" / slot["case"]
        if ev.exists():
            _sh.rmtree(ev)

    def reset_slot(slot):
        """自测夹具重置（仅自测自有 dry 路径）：claim/evidence/ws 清零，支持 2 槽复用。"""
        try:
            (HERE / "receipts" / "claims" / f"{slot['slot_id']}.claim").unlink()
        except FileNotFoundError:
            pass
        ev = HERE / "selftest" / "dry-evidence" / slot["case"]
        if ev.exists():
            _sh.rmtree(ev)
        ws = HERE / "selftest" / "dry-ws" / slot["case"]
        if ws.exists():
            _sh.rmtree(ws)

    # ---- T1 safe_driver 结构性禁用（全 stub，零真实交互） ----
    wd, ensure_safe, log = safe_driver.install_safe_driver(9332)
    t("T1.quit_app_structurally_forbidden", _raises(wd._quit_app), "replaced by raiser")
    orig = (safe_driver._wb_running, wd._launch, safe_driver._cdp_up,
            wd.CDP, wd._wait_page_ready)
    try:
        wd.CDP = _FakeCDP
        wd._wait_page_ready = lambda cdp, timeout_s=60: None
        safe_driver._cdp_up = lambda p: True
        wd._launch = lambda p: (_ for _ in ()).throw(AssertionError("launch must not run"))
        t("T1a.reuse_when_cdp_up", ensure_safe(9332) == "reused", "")
        safe_driver._cdp_up = lambda p: False
        safe_driver._wb_running = lambda: False
        wd._launch = lambda p: None
        t("T1b.clean_launch_when_not_running", ensure_safe(9332) == "launched", "")
        safe_driver._wb_running = lambda: True
        raised = False
        try:
            ensure_safe(9332)
        except safe_driver.WBUnsafeState:
            raised = True
        t("T1c.unsafe_state_raises_no_kill", raised, "WBUnsafeState; no SIGTERM path")
    finally:
        (safe_driver._wb_running, wd._launch, safe_driver._cdp_up,
         wd.CDP, wd._wait_page_ready) = orig

    # ---- T2 共同 gate 薄适配 fail-closed ----
    r = adapter_verify_execution(HERE / "selftest" / "no-such-binding.json")
    t("T2a.missing_binding_fail_closed", r["ok"] is False, r["reasons"][:1])
    if GATE_PRESENT:
        gr = subprocess.run([sys.executable, str(GATE_PATH), "--selftest"],
                            capture_output=True, text=True)
        import json as _json
        selftest_state = "unparsed"
        try:
            dec = _json.JSONDecoder()
            idx, last = 0, None
            txt = gr.stdout or ""
            while idx < len(txt):
                while idx < len(txt) and txt[idx] in " \n\r\t":
                    idx += 1
                if idx >= len(txt):
                    break
                obj, end = dec.raw_decode(txt, idx)
                last = obj
                idx = end
            res = (last or {}).get("results") or []
            fails_n = sum(1 for c in res if not c.get("pass", c.get("ok", True)))
            selftest_state = f"rc={gr.returncode} cases={len(res)} fails={fails_n}"
        except Exception as e:
            selftest_state = f"rc={gr.returncode} parse-error {e}"
        t("T2c.common_gate_selftest_executed", gr.returncode in (0, 1), selftest_state)
    else:
        skip("T2c.common_gate_selftest_executed", "l5 gate v2 未就位（并行在建）")

    # ---- T10 严格等待/停止验证（stub DB+trace，零真实交互） ----
    class _FakeWB:
        pass
    fwb = _FakeWB()
    state = {"db": "active"}
    fwb._db_row = lambda tid: {"status": state["db"]}
    fwb._jsonl_stats = lambda jp: {"bytes": 100, "exists": True}
    fwb._jsonl_path = lambda ws, tid: "/tmp/fake.jsonl"
    # (a) active+trace 静默 ≠ 完成：直到 deadline 不早判 completed；
    #     on_deadline 发 cancel 且 DB 转 cancelled → stop_verified=True
    def _on_dl(tid, snap):
        state["db"] = "cancelled"
        return {"cancel_invoked": True, "cancel_at": now_iso()}
    r10a = safe_driver.wait_completion_strict(fwb, "t", timeout_s=1.0, workspace_dir="w",
                                              stable_s=0.2, poll_s=0.05,
                                              on_deadline=_on_dl,
                                              process_probe=lambda ws: [])
    t("T10a.active_idle_never_completes_and_stop_verified",
      r10a["status"] == "timeout" and r10a["stop_info"]["stop_verified"] is True,
      f"status={r10a['status']} stop={r10a['stop_info'].get('stop_verified')}")
    # (b) DB 终态 + 稳定 → completed
    state["db"] = "completed"
    r10b = safe_driver.wait_completion_strict(fwb, "t", timeout_s=2.0, workspace_dir="w",
                                              stable_s=0.2, poll_s=0.05)
    t("T10b.terminal_plus_stable_completes", r10b["status"] == "completed", r10b["status"])
    # (c) cancel 未获 DB 终态证实 → stop_verified=False（不得视为已安全停止）
    state["db"] = "active"
    r10c = safe_driver.wait_completion_strict(fwb, "t", timeout_s=0.5, workspace_dir="w",
                                              stable_s=0.2, poll_s=0.05,
                                              on_deadline=lambda tid, snap: {"cancel_invoked": False},
                                              process_probe=lambda ws: [])
    t("T10c.unverified_stop_flagged",
      r10c["status"] == "timeout" and r10c["stop_info"]["stop_verified"] is False,
      str(r10c["stop_info"].get("stop_verified")))
    # (d) cancel 后 DB 转终态但 workspace 仍有可见 kernel 进程 → 拒 verified
    state["db"] = "active"

    def _on_dl_proc(tid, snap):
        state["db"] = "cancelled"
        return {"cancel_invoked": True}
    r10d = safe_driver.wait_completion_strict(fwb, "t", timeout_s=0.5, workspace_dir="w",
                                              stable_s=0.2, poll_s=0.05,
                                              on_deadline=_on_dl_proc,
                                              process_probe=lambda ws: [4321])
    t("T10d.visible_process_refuses_verified",
      r10d["status"] == "timeout" and r10d["stop_info"]["stop_verified"] is False
      and r10d["stop_info"]["post_cancel_processes"] == [4321],
      str(r10d["stop_info"].get("post_cancel_processes")))

    # ---- T16 默认探针全 deadline 路径（不传 process_probe；mock _lsof 层而非替换函数） ----
    ws_probe = str(HERE / "selftest" / "fake-ws-probe")
    class _FakeRet:
        def __init__(self, rc, out): self.returncode, self.stdout = rc, out
    saved_lsof = safe_driver._lsof
    try:
        # (a) 子目录 cwd 也计入作用域 → 拒 verified
        safe_driver._lsof = lambda args, timeout_s=15: _FakeRet(
            0, f"p1234\nn{ws_probe}/sub\n")
        state["db"] = "active"
        r16a = safe_driver.wait_completion_strict(
            fwb, "t", timeout_s=0.3, workspace_dir=ws_probe, stable_s=0.1,
            poll_s=0.05, on_deadline=lambda tid, snap: {"cancel_invoked": True},
            post_cancel_window_s=0.3)
        t("T16a.default_probe_subdir_cwd_refuses",
          r16a["status"] == "timeout" and r16a["stop_info"]["stop_verified"] is False
          and r16a["stop_info"]["post_cancel_processes"] == ["1234"],
          str(r16a["stop_info"].get("post_cancel_processes")))
        # (b) lsof 非零退出 → probe-error → 拒 verified（错误不当空列表）
        safe_driver._lsof = lambda args, timeout_s=15: _FakeRet(1, "")
        state["db"] = "active"
        r16b = safe_driver.wait_completion_strict(
            fwb, "t", timeout_s=0.3, workspace_dir=ws_probe, stable_s=0.1,
            poll_s=0.05, on_deadline=lambda tid, snap: {"cancel_invoked": True},
            post_cancel_window_s=0.3)
        t("T16b.probe_error_refuses",
          r16b["stop_info"]["post_cancel_processes"] == ["probe-error"]
          and r16b["stop_info"]["stop_verified"] is False,
          str(r16b["stop_info"].get("post_cancel_processes")))
        # (c) 干净输出（他人 cwd 不匹配）→ verified=True（默认探针入口，原 NameError 回归）
        safe_driver._lsof = lambda args, timeout_s=15: _FakeRet(
            0, "p999\n/Users/someone-else\n")
        state["db"] = "active"
        def _on_dl_clean(tid, snap):
            state["db"] = "cancelled"
            return {"cancel_invoked": True}
        r16c = safe_driver.wait_completion_strict(
            fwb, "t", timeout_s=0.3, workspace_dir=ws_probe, stable_s=0.1,
            poll_s=0.05, on_deadline=_on_dl_clean,
            post_cancel_window_s=0.3)
        t("T16c.default_probe_clean_verifies",
          r16c["status"] == "timeout" and r16c["stop_info"]["stop_verified"] is True
          and r16c["stop_info"]["post_cancel_processes"] == [],
          str(r16c["stop_info"].get("post_cancel_processes")))
        # (d) 全窗观测：DB 在窗内翻回非终态 → 拒 verified
        flap_phase = {"post": False}
        def _flap(tid, snap):
            flap_phase["post"] = True
            return {"cancel_invoked": True}
        state["db"] = "active"
        # 窗内翻转：deadline 前恒 active；deadline 后在 cancelled/active 间交替
        seq = {"n": 0}
        real_row = fwb._db_row
        def _row_flap(tid):
            if not flap_phase["post"]:
                return {"status": "active"}
            seq["n"] += 1
            return {"status": "cancelled" if seq["n"] % 2 else "active"}
        fwb._db_row = _row_flap
        r16d = safe_driver.wait_completion_strict(
            fwb, "t", timeout_s=0.3, workspace_dir=ws_probe, stable_s=0.1,
            poll_s=0.05, on_deadline=_flap, process_probe=lambda ws: [],
            post_cancel_window_s=0.4)
        fwb._db_row = real_row
        t("T16d.db_flap_refuses_verified",
          r16d["status"] == "timeout" and r16d["stop_info"]["stop_verified"] is False
          and r16d["stop_info"]["post_cancel_db_flapped"] is True,
          str(r16d["stop_info"].get("post_cancel_statuses")[-3:]))
        # (e) trace 在 cancel 后增长 → 拒 verified
        state["db"] = "active"
        bytes_state = {"v": 100}
        real_stats = fwb._jsonl_stats
        def _stats_grow(jp):
            bytes_state["v"] += 50
            return {"bytes": bytes_state["v"], "exists": True}
        fwb._jsonl_stats = _stats_grow
        r16e = safe_driver.wait_completion_strict(
            fwb, "t", timeout_s=0.3, workspace_dir=ws_probe, stable_s=0.1,
            poll_s=0.05, on_deadline=lambda tid, snap: {"cancel_invoked": True},
            process_probe=lambda ws: [], post_cancel_window_s=0.3)
        fwb._jsonl_stats = real_stats
        t("T16e.trace_growth_refuses_verified",
          r16e["status"] == "timeout" and r16e["stop_info"]["stop_verified"] is False
          and r16e["stop_info"]["post_cancel_trace_stable"] is False,
          str(r16e["stop_info"].get("post_cancel_trace_stable")))
    finally:
        safe_driver._lsof = saved_lsof

    # ---- T7 mock 驱动全路径干跑（固定 dry 根 + 独占 claim） ----
    fixture_case = HERE / "selftest" / "fixtures" / "fake-case"
    fixture_session = HERE / "selftest" / "fixtures" / "mock-session"
    slot = SLOT_A
    r = run_impl(slot, MockDriver(fixture_session), dry=True,
                 case_root=fixture_case, ws_root=HERE / "selftest" / "dry-ws",
                 registered_at="2026-10-29T20:00:00+08:00",
                 preregistration_commit="a" * 40,
                 execution_seal_commit="c" * 40,
                 expect_checker_sha=sha256_file(fixture_case / "checker.py"))
    meta = r.get("meta") or {}
    if not meta:
        t("T7a.dry_run_status_ok", False,
          f"early-return: status={r.get('status')} acc={json.dumps(r.get('accounting'), ensure_ascii=False)[:160]}")
        receipt = {"kind": "self_test", "batch": "l5-20261030-wb-gateway",
                   "at": now_iso(), "model_calls": 0, "all_pass": False,
                   "results": results, "live_doc_drift": []}
        out = write_json_once(HERE / "selftest" / "selftest-receipt-l5-wb-v1.json", receipt)
        print(f"[selftest] all_pass=False receipt={out}")
        return 1
    t("T7a.dry_run_status_ok", r.get("status") == "ok", str(r.get("status")))
    t("T7b.attempts_exactly_1", len(meta.get("attempts", [])) == 1,
      "whole_execution_restarts=0")
    t("T7c.weighted_8dp", isinstance(meta.get("weighted"), float)
      and round(meta["weighted"], 8) == meta["weighted"], str(meta.get("weighted")))
    t("T7d.usage_parsed_from_trace", len(meta["usage"]["per_call"]) >= 1,
      f"n={len(meta['usage']['per_call'])}")
    t("T7e.registration_persisted",
      (Path(r["evidence_dir"]) / "registrations").is_dir()
      and any((Path(r["evidence_dir"]) / "registrations").glob("*.json")), "R3")
    t("T7f.integrity_clean", meta.get("integrity_verdict") == "clean", "fake trace")
    t("T7k.timed_out_false_on_ok", meta.get("timed_out") is False, "§E timeout 语义分离")
    t("T7l.checker_exit1_still_scored",
      meta.get("reward") == 0 and meta.get("weighted") == 0.0
      and meta.get("status") == "ok"
      and (meta.get("judge") or {}).get("exit_code") == 1,
      "checker exit1=合法低分，非基础设施错误")
    # §C 证据布局 + route/未知字段
    evp = meta.get("evidence_paths") or {}
    t("T7i1.evidence_layout_defaults",
      (Path(r["evidence_dir"]) / "prompt.txt").is_file()
      and (Path(r["evidence_dir"]) / "agent-session" / "session-row.json").is_file()
      and (Path(r["evidence_dir"]) / "agent.stderr.txt").is_file()
      and (Path(r["evidence_dir"]) / "workspace").is_dir()
      and evp.get("prompt") == "prompt.txt" and evp.get("session") == "agent-session",
      str(evp))
    rt = meta.get("route") or {}
    t("T7i2.route_gate_fields",
      rt.get("declared_alias") == "deepseek-v4.1-flash"
      and isinstance(rt.get("alias_evidence"), str)
      and (Path(r["evidence_dir"]) / rt["alias_evidence"]).is_file()
      and rt.get("validation") == "current_not_observed"
      and rt.get("route_verification") == "current_not_observed"
      and rt.get("r2_history_ref") == R2_EVIDENCE, "§C")
    mu = meta.get("managed_unknowns")
    t("T7i3.managed_unknowns_list_items",
      isinstance(mu, list) and all(
          isinstance(x, dict) and x.get("item") and x.get("impact")
          and x.get("next_step") and x.get("stop_condition") for x in mu)
      and len(mu) == 4, "§C")
    sr = load_json(Path(r["evidence_dir"]) / "score-receipt.json")
    contract = load_json(CONTRACT_PATH)
    t("T7j.score_receipt_D_shape",
      sr.get("case") == slot["case"] and sr.get("product") == "workbuddy"
      and isinstance(sr.get("score", {}).get("earned"), int)
      and sr["score"]["possible"] == contract["denominators"][slot["case"]]
      and isinstance(sr["score"]["reported"], float)
      and isinstance(sr.get("raw_checker_output"), dict)
      and isinstance(sr.get("live_doc_drift"), list), "§D")
    # 共同 gate validator：无 seal → fail:unsealed；带 seal → pass
    if not GATE_PRESENT:
        skip("T7g.validator_wired_unsealed_fail", "l5 gate v2 未就位")
        skip("T7h.validator_meta_pass_with_seal", "l5 gate v2 未就位")
    else:
        import importlib.util as _ilu
        from datetime import datetime as _dt
        spec = _ilu.spec_from_file_location("l5_gate_validator", str(GATE_PATH))
        gmod = _ilu.module_from_spec(spec)
        spec.loader.exec_module(gmod)
        vmod = gmod.load_runner_validator()
        res_unsealed = vmod.validate_meta(meta)
        cls_unsealed = vmod.classify(res_unsealed)
        t("T7g.validator_wired_unsealed_fail", cls_unsealed == "fail:unsealed", cls_unsealed)
        try:
            seal_dt = _dt.fromisoformat(meta["registered_at"])
            res_sealed = vmod.validate_meta(meta, seal_at=seal_dt)
            cls_sealed = vmod.classify(res_sealed)
            issue_classes = sorted({i["class"] for i in res_sealed.get("issues", [])})
            t("T7h.validator_meta_pass_with_seal",
              cls_sealed == "pass" and not issue_classes,
              f"class={cls_sealed} issue_classes={issue_classes}")
        except Exception as e:
            t("T7h.validator_meta_pass_with_seal", False, str(e))

    # ---- T11 固定 path claim 独占：重入即拒（不产生新文件） ----
    ev_before = sorted(x.name for x in Path(r["evidence_dir"]).iterdir())
    r2 = run_impl(slot, MockDriver(fixture_session), dry=True,
                  case_root=fixture_case, ws_root=HERE / "selftest" / "dry-ws",
                  registered_at="2026-10-29T20:00:00+08:00",
                  preregistration_commit="a" * 40,
                  expect_checker_sha=sha256_file(fixture_case / "checker.py"))
    ev_after = sorted(x.name for x in Path(r["evidence_dir"]).iterdir())
    t("T11.claim_refuses_reentry",
      r2.get("status") == "claim-refused" and ev_before == ev_after,
      f"status={r2.get('status')} dir_unchanged={ev_before == ev_after}")

    # ---- T12 setup 失败也持久 accounting（另一 slot，预占 ws 目录） ----
    slot2 = SLOT_B
    blocker = HERE / "selftest" / "dry-ws" / slot2["case"]
    blocker.mkdir(parents=True, exist_ok=True)
    r3 = run_impl(slot2, MockDriver(fixture_session), dry=True,
                  case_root=fixture_case, ws_root=HERE / "selftest" / "dry-ws",
                  registered_at="2026-10-29T20:00:00+08:00",
                  preregistration_commit="a" * 40,
                  expect_checker_sha=sha256_file(fixture_case / "checker.py"))
    acc_file = Path(r3["evidence_dir"]) / "slot-accounting.json"
    t("T12.setup_failure_accounting_persisted",
      r3.get("status") == "not_executed" and acc_file.is_file()
      and load_json(acc_file)["execution_state"] == "not_executed",
      f"status={r3.get('status')}")

    # ---- T13 canonical trace 缺失 → violation + error（不冒充 clean+ok） ----
    empty_session = HERE / "selftest" / "fixtures" / "empty-session"
    if empty_session.exists():
        shutil.rmtree(empty_session)
    empty_session.mkdir(parents=True)
    (empty_session / "collect-meta.json").write_text("{}", encoding="utf-8")
    slot3 = SLOT_A
    reset_slot(slot3)
    r4 = run_impl(slot3, MockDriver(empty_session), dry=True,
                  case_root=fixture_case, ws_root=HERE / "selftest" / "dry-ws",
                  registered_at="2026-10-29T20:00:00+08:00",
                  preregistration_commit="a" * 40,
                  expect_checker_sha=sha256_file(fixture_case / "checker.py"))
    m4 = r4.get("meta") or {}
    t("T13.missing_trace_violation_not_ok",
      m4.get("status") == "error" and m4.get("integrity_verdict") == "violation"
      and (m4.get("integrity") or {}).get("missing_trace") is True
      and r4.get("accounting", {}).get("formal_admission") is False,
      f"status={r4.get('status')} verdict={m4.get('integrity_verdict')}")

    # ---- T14 自测不触碰真实 runs 目录 ----
    real_runs = HERE / "runs"
    t("T14.real_runs_untouched_by_selftest",
      not real_runs.exists() or not any(real_runs.iterdir()),
      "dry 全部落在 selftest/dry-*（首跑前 runs/ 可尚未创建）")

    # ---- T15 版本漂移比较 ----
    t("T15.upgrade_drift_detected",
      detect_upgrade_drift({"app_version": "5.9.3", "app_asar_sha256": "a" * 64},
                           {"app_version": "5.9.4", "app_asar_sha256": "a" * 64})
      and detect_upgrade_drift({"app_version": "5.9.3", "app_asar_sha256": "a" * 64},
                               {"app_version": "5.9.3", "app_asar_sha256": "b" * 64})
      and not detect_upgrade_drift({"app_version": "5.9.3", "app_asar_sha256": "a" * 64},
                                   {"app_version": "5.9.3", "app_asar_sha256": "a" * 64}),
      "版本或 asar 任一变化即漂移")

    # ---- T17 端到端真 gate：native verified timeout 准入 / 未 verified 拒绝 ----
    import tempfile as _tf
    import importlib.util as _ilu2
    g2 = None
    if GATE_PRESENT:
        spec2 = _ilu2.spec_from_file_location("l5_gate2", str(GATE_PATH))
        g2 = _ilu2.module_from_spec(spec2); spec2.loader.exec_module(g2)
    else:
        skip("T17.e2e_gate_positive_negative", "l5 gate v2 未就位（worlds 依赖 gate.py）")
        skip("T18.foreign_binding_producer_refuses", "随 T17 依赖 gate harness")
        skip("T18b.foreign_conversation_producer_refuses", "随 T17 依赖 gate harness")
        skip("T19a.ok_run_impl_complete", "T19 world 依赖 gate harness（E 后补跑）")
        skip("T19b.checker_stdout_file_bound", "T19 world 依赖 gate harness（E 后补跑）")
        skip("T19c.gate_all_other_fails_clear", "T19 world 依赖 gate harness（E 后补跑）")
        skip("T19d.gate_full_formal_admission", "l5 gate v2 未就位")
    if g2 is not None:
        D_, E_ = "d" * 40, "e" * 40
        d_time_, e_time_ = "2026-10-29T19:00:00+08:00", "2026-10-29T20:00:00+08:00"

        def _wb_timeout_world(tmp, verified_stop, with_envelope=True, foreign_doc=False,
                              checks_mut=None):
            contract = {"rule_version": "l5-20261030-batch-v1",
                        "strata": {"wb_gateway_delivery": {"products": ["workbuddy"],
                                                           "declared_model_alias": "deepseek-v4.1-flash",
                                                           "gateway": "www.workbuddy.cn",
                                                           "ranking": False}},
                        "case_snapshots": {"bird-ca-schools-15": {"checker.py": "c" * 64}},
                        "denominators": {"bird-ca-schools-15": 15},
                        "admission": {"required_original_evidence":
                                      ["prompt", "stdout", "stderr", "session", "checker",
                                       "workspace"]}}
            sid = "l5-20261030-wb-gateway-bird-ca-schools-15-r1"
            slot_wb = {"slot_id": sid, "run_id": sid, "event_id": "event:" + sid,
                       "kind": "product_run", "product": "workbuddy",
                       "case": "bird-ca-schools-15", "rep": 1,
                       "stratum": "wb_gateway_delivery", "order": 13,
                       "evidence_dir": "runs/" + sid, "timeout_s": 1800}
            plan_dir = tmp / "plans" / "l4"
            plan_dir.mkdir(parents=True, exist_ok=True)
            (plan_dir / "plan.json").write_text(json.dumps(
                {"plan_id": "l5-20261030", "product_slots": [slot_wb]}), encoding="utf-8")
            (plan_dir / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
            (plan_dir / "PREREGISTRATION.md").write_bytes(b"PREREG")
            ext = tmp / "driver.sh"; ext.write_text("ok\n", encoding="utf-8")
            bp, gr, gt, ga, b = g2._fake_git_env(tmp, plan_dir, D_, E_, e_time_, d_time_, ext)
            bp2 = tmp / "binding-released.json"
            bp2.write_text(json.dumps(dict(b, released_for_model_calls=True)), encoding="utf-8")
            # 证据目录（§C 布局）
            ev = tmp / slot_wb["evidence_dir"]; ev.mkdir(parents=True, exist_ok=True)
            raw = b"x" * 100
            (ev / "agent.jsonl").write_bytes(raw)
            (ev / "agent.stderr.txt").write_bytes(b"")
            (ev / "prompt.txt").write_bytes(b"p")
            (ev / "checker.stdout").write_text(json.dumps(
                {"reward": 0, "weighted": 0.0, "correct": 0, "n_tasks": 15,
                 "checks": [{"id": f"q{i}", "pass": False} for i in range(1, 16)],
                 "guards_used": [], "checker_sha256": "c" * 64, "exit_code": 1}),
                encoding="utf-8")
            (ev / "agent-session").mkdir(exist_ok=True)
            (ev / "agent-session" / "session-row.json").write_text("{}", encoding="utf-8")
            (ev / "workspace").mkdir(exist_ok=True)
            (ev / "workspace" / "out.txt").write_text("w")
            (ev / "alias-proof.jsonl").write_text("{}\n", encoding="utf-8")
            checks_ok = {"db_terminal": True, "trace_stable": True,
                         "no_scoped_processes": True}
            if checks_mut:
                checks_ok.update(checks_mut)
            ns = {"kind": "native_stop", "slot_id": slot_wb["slot_id"],
                  "run_id": slot_wb["run_id"], "event_id": slot_wb["event_id"],
                  "conversation_id": "conv-" + sid[:12], "workspace": "/tmp/ws",
                  "verified_stop": verified_stop,
                  "stop_kind": "wb:conversations:cancel",
                  "verified_at": e_time_ if verified_stop else None,
                  "cancel_invoked_at": e_time_, "deadline_reached_at": e_time_,
                  "checks": checks_ok,
                  "at": e_time_, "live_doc_drift": []}
            if foreign_doc:
                ns["slot_id"] = "l5-20261030-wb-gateway-dabstep-payments-10-r1"
                ns["conversation_id"] = "conv-OTHER"
            (ev / "native-stop.json").write_text(json.dumps(ns), encoding="utf-8")
            judge = {"reward": 0, "weighted": 0.0, "correct": 0, "n_tasks": 15,
                     "checks": [{"id": f"q{i}", "pass": False} for i in range(1, 16)],
                     "guards_used": [], "checker_sha256": "c" * 64, "exit_code": 1}
            meta = {"batch": "l5-20261030-wb-gateway", "rule_version": "l5-20261030-batch-v1",
                    "preregistration_commit": E_, "registered_at": e_time_, "rep": 1,
                    "product": "workbuddy", "case": "bird-ca-schools-15",
                    "form": "desktop-auto-cdp-rpc", "run_id": slot_wb["run_id"],
                    "event_id": slot_wb["event_id"], "slot_id": slot_wb["slot_id"],
                    "order": 13, "stratum": "wb_gateway_delivery",
                    "selection": {"slot_id": slot_wb["slot_id"]}, "diagnostic": None,
                    "workspace": "/tmp/ws", "model": "deepseek-v4.1-flash",
                    "reasoning_effort": "low", "product_version": "5.9.3",
                    "app_asar_sha256": "a" * 64,
                    "route": {"declared_alias": "deepseek-v4.1-flash",
                              "alias_evidence": "alias-proof.jsonl",
                              "actual_gateway": "unknown",
                              "route_verification": "current_not_observed",
                              "validation": "current_not_observed",
                              "r2_history_ref": "r2/history.md"},
                    "tools": [], "permissions": "fullAccess", "skills": "unobservable",
                    "web_search": "off", "soft_constraints": ["offline"],
                    "prompt_sha256": hashlib.sha256(b"p").hexdigest(),
                    "isolation": {"ok": True}, "inputs": ["TASK.md"],
                    "status": "timeout", "timed_out": True, "exit_code": None,
                    "created_at": "2026-10-29T20:00:00+08:00",
                    "started_at": "2026-10-29T20:01:00+08:00",
                    "finished_at": "2026-10-29T20:31:00+08:00", "duration_s": 1800.0,
                    "attempts": [{"n": 1, "outcome": "timeout"}], "transport_retries": 0,
                    "stdout_bytes": 100, "stdout_sha256": hashlib.sha256(raw).hexdigest(),
                    "stderr_bytes": 0, "stderr_sha256": hashlib.sha256(b"").hexdigest(),
                    "usage": {"per_call": []}, "reward": 0,
                    "weighted": round(0 / 15 * 100, 8), "failed": [], "judge": judge,
                    "integrity": {"scanned": True}, "integrity_verdict": "clean",
                    "managed_unknowns": [{"item": "gateway_upstream_model",
                                          "impact": "i", "next_step": "n",
                                          "stop_condition": "s"}],
                    "native_stop": ({"file": "native-stop.json",
                                     "sha256": hashlib.sha256(
                                         (ev / "native-stop.json").read_bytes()).hexdigest()}
                                    if with_envelope else None),
                    "inputs_verification": {"ok": True, "method": "fixture"}}
            (ev / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
            (ev / "score-receipt.json").write_text(json.dumps(
                {"case": "bird-ca-schools-15", "product": "workbuddy",
                 "run_id": slot_wb["run_id"], "rep": 1,
                 "score": {"earned": 0, "possible": 15, "reported": 0.0,
                           "checker_sha256": "c" * 64},
                 "rule_version": "l5-20261030-batch-v1", "checker_sha256": "c" * 64,
                 "raw_checker_output": judge,
                 "at": e_time_, "live_doc_drift": []}), encoding="utf-8")
            RS2 = {"plans/l4/plan.json", "plans/l4/contract.json"}
            rep = g2.gate_admission(bp2, "workbuddy", repo=tmp, plan_dir=plan_dir,
                                    git_reader=gr, git_time=gt, git_ancestor=ga,
                                    required_set=RS2)
            return rep

        try:
            with _tf.TemporaryDirectory(prefix="l4wb-e2e-pos-") as td:
                rep = _wb_timeout_world(Path(td), verified_stop=True)
                ps = rep["per_slot"][0]
                stop_fails = [f for f in ps.get("fails", []) if "native stop" in f or "native_stop" in f]
                t("T17a.native_verified_timeout_full_admission",
                  not stop_fails and ps.get("formal_admission") is True
                  and ps.get("genuine_timeout") is True,
                  f"formal={ps.get('formal_admission')} genuine={ps.get('genuine_timeout')} "
                  f"fails={json.dumps(ps.get('fails', []), ensure_ascii=False)[:400]}")
            with _tf.TemporaryDirectory(prefix="l4wb-e2e-neg-") as td:
                rep = _wb_timeout_world(Path(td), verified_stop=False)
                ps = rep["per_slot"][0]
                t("T17b.native_unverified_rejected",
                  ps.get("formal_admission") is False
                  and any("verified_stop" in f for f in ps.get("fails", [])),
                  json.dumps(ps.get("fails", []))[:200])
            with _tf.TemporaryDirectory(prefix="l4wb-e2e-checks-") as td:
                rep = _wb_timeout_world(Path(td), verified_stop=True,
                                        checks_mut={"trace_stable": False})
                ps = rep["per_slot"][0]
                t("T17d.checks_partial_true_rejected",
                  ps.get("formal_admission") is False,
                  json.dumps(ps.get("fails", []))[:200])
            with _tf.TemporaryDirectory(prefix="l4wb-e2e-missing-") as td:
                rep = _wb_timeout_world(Path(td), verified_stop=True, with_envelope=False)
                ps = rep["per_slot"][0]
                t("T17c.missing_envelope_rejected",
                  ps.get("formal_admission") is False
                  and any("native_stop" in f for f in ps.get("fails", [])),
                  json.dumps(ps.get("fails", []))[:200])
            # T18 跨槽/跨 session 借用：gate b76208cf 已核 doc.slot_id（不符即拒），
            # 生产者侧再保留同构守卫（双保险；本断言针对 producer 助手）
            foreign = {"slot_id": "l5-20261030-wb-gateway-dabstep-payments-10-r1",
                       "run_id": "l5-20261030-wb-gateway-dabstep-payments-10-r1",
                       "conversation_id": "conv-OTHER", "workspace": "/tmp/ws",
                       "verified_stop": True}
            refused = None
            try:
                validate_native_stop_binding(foreign, slot, "conv-mine", "/tmp/ws")
            except RuntimeError as e:
                refused = str(e)
            t("T18.foreign_binding_producer_refuses",
              refused is not None and "slot_id" in refused, str(refused)[:120])
            wrong_conv = dict(foreign, slot_id=slot["slot_id"], run_id=slot["run_id"])
            refused2 = None
            try:
                validate_native_stop_binding(wrong_conv, slot, "conv-mine", "/tmp/ws")
            except RuntimeError as e:
                refused2 = str(e)
            t("T18b.foreign_conversation_producer_refuses",
              refused2 is not None and "conversation_id" in refused2, str(refused2)[:120])
        except Exception as e:
            t("T17.e2e_harness_error", False, str(e)[:200])

        # ---- T19 正常 completed：真 run_impl 产物 → 最新共同 gate 全门正例 ----
        import tempfile as _tf2
        fixture_ok = HERE / "selftest" / "fixtures" / "fake-case-ok"
        slot5 = dict(SLOT_B, run_id=f"l5-20261030-wb-gateway-{SLOT_B['case']}-r{SLOT_B['rep']}",
                     event_id=f"event:l5-20261030-wb-gateway-{SLOT_B['case']}-r{SLOT_B['rep']}")
        reset_evidence_only(slot5)
        try:
            (HERE / "receipts" / "claims" / f"{slot5['slot_id']}.claim").unlink()
        except FileNotFoundError:
            pass
        with _tf2.TemporaryDirectory(prefix="l4wb-t19-") as td:
            tmp = Path(td)
            contract19 = {"rule_version": "l5-20261030-batch-v1",
                          "strata": {"wb_gateway_delivery": {
                              "products": ["workbuddy"],
                              "declared_model_alias": "deepseek-v4.1-flash",
                              "gateway": "www.workbuddy.cn", "ranking": False}},
                          "case_snapshots": {slot5["case"]: {
                              "checker.py": sha256_file(fixture_ok / "checker.py")}},
                          "denominators": {slot5["case"]: 27},
                          "admission": {"required_original_evidence":
                                        ["prompt", "stdout", "stderr", "session",
                                         "checker", "workspace"]}}
            sid19 = f"l5-20261030-wb-gateway-{slot5['case']}-r{slot5['rep']}"
            slot19 = dict(slot5, run_id=sid19, event_id="event:" + sid19,
                          evidence_dir=slot5["case"])  # gate 以 repo/evidence_dir 解析
            plan_dir = tmp / "plans" / "l4"; plan_dir.mkdir(parents=True)
            (plan_dir / "plan.json").write_text(json.dumps(
                {"plan_id": "l5-20261030", "product_slots": [slot19]}), encoding="utf-8")
            (plan_dir / "contract.json").write_text(json.dumps(contract19), encoding="utf-8")
            (plan_dir / "PREREGISTRATION.md").write_bytes(b"PREREG")
            ext = tmp / "driver.sh"; ext.write_text("ok\n", encoding="utf-8")
            bp, gr, gt, ga, b = g2._fake_git_env(tmp, plan_dir, "d" * 40, "e" * 40,
                                                 e_time_, d_time_, ext)
            bp2 = tmp / "binding-released.json"
            bp2.write_text(json.dumps(dict(b, released_for_model_calls=True)), encoding="utf-8")
            ws19 = Path(td) / "ws-root"  # 仓外（isolation.ok 事实要求）
            r19 = run_impl(slot19, MockDriver(fixture_session), dry=True,
                           case_root=fixture_ok, ws_root=ws19,
                           registered_at=e_time_, preregistration_commit="e" * 40,
                           execution_seal_commit="e" * 40,
                           expect_checker_sha=sha256_file(fixture_ok / "checker.py"),
                           evidence_root=tmp)
            m19 = r19.get("meta") or {}
            t("T19a.ok_run_impl_complete", r19.get("status") == "ok"
              and m19.get("weighted") == 100.0 and m19.get("order") == slot19["order"],
              f"status={r19.get('status')} weighted={m19.get('weighted')}")
            _sr19 = load_json(Path(r19["evidence_dir"]) / "score-receipt.json")
            t("T19b.checker_stdout_file_bound",
              (Path(r19["evidence_dir"]) / "checker.stdout").is_file()
              and json.loads((Path(r19["evidence_dir"]) / "checker.stdout").read_text())
              == _sr19.get("raw_checker_output"),
              "raw 全文落盘且与 receipt.raw_checker_output 逐字一致")
            rep19 = g2.gate_admission(bp2, "workbuddy", repo=tmp, plan_dir=plan_dir,
                                      git_reader=gr, git_time=gt, git_ancestor=ga,
                                      required_set={"plans/l4/plan.json",
                                                    "plans/l4/contract.json"})
            ps19 = rep19["per_slot"][0]
            exitcode_fails = [f for f in ps19.get("fails", [])
                              if "exit_code" in f]
            other_fails = [f for f in ps19.get("fails", []) if "exit_code" not in f]
            t("T19c.gate_all_other_fails_clear", not other_fails,
              json.dumps(other_fails, ensure_ascii=False)[:400])
            t("T19d.gate_full_formal_admission",
              ps19.get("formal_admission") is True and not ps19.get("fails"),
              f"formal={ps19.get('formal_admission')} "
              f"fails={json.dumps(ps19.get('fails', []), ensure_ascii=False)[:400]}")

    # ---- T20 W6：stop 未验证 ⇒ checker 0 次 + partial + halt 后槽零 send（真 run_impl 分支） ----
    slot_lc = SLOT_A
    reset_slot(slot_lc)
    try:
        (HERE / "receipts" / "claims" / f"{slot_lc['slot_id']}.claim").unlink()
    except FileNotFoundError:
        pass
    (HERE / "receipts" / "HALT.json").unlink(missing_ok=True)
    md20 = MockDriver(fixture_session, timeout_unverified=True)
    r20 = run_impl(slot_lc, md20, dry=True, case_root=fixture_case,
                   ws_root=HERE / "selftest" / "dry-ws",
                   registered_at="2026-10-29T20:00:00+08:00",
                   preregistration_commit="a" * 40,
                   expect_checker_sha=sha256_file(fixture_case / "checker.py"))
    ev20 = Path(r20["evidence_dir"])
    t("T20a.stop_unverified_partial_no_checker",
      r20.get("status") == "timeout" and r20.get("checker_ran") is False
      and not (ev20 / "checker.stdout").exists()
      and not (ev20 / "score-receipt.json").exists()
      and not (ev20 / "trace").exists() and not (ev20 / "workspace").exists(),
      f"status={r20.get('status')} checker_ran={r20.get('checker_ran')}")
    acc20 = load_json(ev20 / "slot-accounting.json")
    ns20 = load_json(ev20 / "native-stop.json")
    m20 = load_json(ev20 / "meta.json")
    t("T20b.partial_score_null_native_false",
      acc20.get("execution_state") == "partial" and acc20.get("score") is None
      and acc20.get("formal_admission") is False
      and ns20.get("verified_stop") is False
      and m20.get("weighted") is None and m20.get("reward") is None
      and m20.get("selection") is None
      and (m20.get("diagnostic") or {}).get("class") == "stop_unverified",
      f"state={acc20.get('execution_state')} vs={ns20.get('verified_stop')}")
    t("T20c.deadline_evidence_present",
      (ev20 / "deadline-evidence.json").is_file(), "冻结文件存在")
    t("T20d.halt_persisted",
      (HERE / "receipts" / "HALT.json").is_file(), "批级 halt")
    slot_cg = SLOT_B
    reset_slot(slot_cg)
    try:
        (HERE / "receipts" / "claims" / f"{slot_cg['slot_id']}.claim").unlink()
    except FileNotFoundError:
        pass
    md20b = MockDriver(fixture_session)
    r20b = run_impl(slot_cg, md20b, dry=True, case_root=fixture_case,
                    ws_root=HERE / "selftest" / "dry-ws",
                    registered_at="2026-10-29T20:00:00+08:00",
                    preregistration_commit="a" * 40,
                    expect_checker_sha=sha256_file(fixture_case / "checker.py"))
    acc20b = load_json(Path(r20b["evidence_dir"]) / "slot-accounting.json")
    t("T20e.successor_halted_zero_send",
      r20b.get("status") == "halted" and md20b.calls == []
      and acc20b.get("execution_state") == "not_executed",
      f"status={r20b.get('status')} driver_calls={len(md20b.calls)}")
    (HERE / "receipts" / "HALT.json").unlink(missing_ok=True)

    # ---- T20f verified-timeout 分支（真 run_impl）：评分管线完整走通 ----
    try:
        (HERE / "receipts" / "claims" / f"{slot_lc['slot_id']}.claim").unlink()
    except FileNotFoundError:
        pass
    md20v = MockDriver(fixture_session, timeout_verified=True)
    r20v = run_impl(slot_lc, md20v, dry=True, case_root=fixture_case,
                    ws_root=HERE / "selftest" / "dry-ws-v",  # r20 的动态 ws 保留不动（W6 语义）
                    registered_at="2026-10-29T20:00:00+08:00",
                    preregistration_commit="a" * 40,
                    expect_checker_sha=sha256_file(fixture_case / "checker.py"),
                    evidence_root=HERE / "selftest" / "dry-evidence-v20f")
    ev20v = Path(r20v["evidence_dir"])
    m20v = r20v.get("meta") or {}
    acc20v = load_json(ev20v / "slot-accounting.json")
    ns20v = load_json(ev20v / "native-stop.json")
    t("T20f.verified_timeout_scored_executed",
      r20v.get("status") == "timeout" and m20v.get("timed_out") is True
      and m20v.get("weighted") is not None
      and (ev20v / "checker.stdout").is_file()
      and (ev20v / "score-receipt.json").is_file()
      and ns20v.get("verified_stop") is True
      and acc20v.get("execution_state") == "executed"
      and acc20v.get("timed_out") is True
      and (m20v.get("attempts") or [{}])[0].get("outcome") == "timeout",
      f"status={r20v.get('status')} weighted={m20v.get('weighted')} "
      f"state={acc20v.get('execution_state')}")

    # ---- T21 R6：非生成式就绪轮询（mock transport，零真实 app） ----
    seq = {"calls": 0}
    def _fetch_delayed():
        seq["calls"] += 1
        return [] if seq["calls"] < 3 else [{"type": "page", "webSocketDebuggerUrl": "ws://x"}]
    r21a = safe_driver.wait_page_target_ready(9332, timeout_s=5, poll_s=0.05,
                                              fetch_fn=_fetch_delayed)
    t("T21a.delayed_ready_captured", r21a["ready"] is True and r21a["polls"] >= 3,
      str(r21a))
    r21b = safe_driver.wait_page_target_ready(9332, timeout_s=0.3, poll_s=0.05,
                                              fetch_fn=lambda: [])
    t("T21b.timeout_returns_not_ready",
      r21b["ready"] is False and r21b["transport_alive"] is True, str(r21b))
    slot_nr = SLOT_A
    reset_slot(slot_nr)
    def md20_like_send_absent(driver):
        return not any(c.get("api") in ("new_task", "sendPrompt") for c in driver.calls)
    md_nr = MockDriver(fixture_session, page_ready=False)
    r21c = run_impl(slot_nr, md_nr, dry=True, case_root=fixture_case,
                    ws_root=HERE / "selftest" / "dry-ws",
                    registered_at="2026-10-30T01:00:00+08:00",
                    preregistration_commit="a" * 40,
                    expect_checker_sha=sha256_file(fixture_case / "checker.py"))
    acc21 = load_json(Path(r21c["evidence_dir"]) / "slot-accounting.json")
    t("T21c.ready_timeout_lands_not_executed",
      r21c.get("status") == "not_executed"
      and acc21.get("execution_state") == "not_executed"
      and "renderer-ready" in str(acc21.get("reason"))
      and md_nr.calls and md20_like_send_absent(md_nr),
      f"status={r21c.get('status')} reason={str(acc21.get('reason'))[:80]}")

    # ---- T22 R7：write-once 与 frame 解析 ----
    tmp22 = HERE / "selftest" / "dry-frame-probe.json"
    if tmp22.exists():
        tmp22.unlink()
    p1 = write_json_once(tmp22, {"v": 1})
    p2 = write_json_once(tmp22, {"v": 2})
    t("T22a.write_once_refuses_and_sidecopies",
      p1 == tmp22 and p2 != tmp22 and json.load(open(p1))["v"] == 1
      and json.load(open(p2))["v"] == 2 and json.load(open(tmp22))["v"] == 1,
      f"p2={p2.name}")
    slot_f = SLOT_A
    ev_f = HERE / "selftest" / "dry-frame" / slot_f["case"]
    if ev_f.exists():
        _sh.rmtree(ev_f)
    ev_f.mkdir(parents=True)
    fslot = dict(slot_f, evidence_dir=f"3-表现现场/{HERE.name}/selftest/dry-frame/{slot_f['case']}")
    (ev_f / "notexecuted.json").write_text(json.dumps(
        {"slot_id": slot_f["slot_id"], "run_id": slot_f["run_id"],
         "event_id": slot_f["event_id"], "preregistration_commit": "a" * 40,
         "reason": "R7 frame 测试", "stop_source": "t22", "at": now_iso(),
         "live_doc_drift": []}), encoding="utf-8")
    fr1 = accounting_frame(fslot)
    (ev_f / "notexecuted.json").unlink()
    (ev_f / "meta.json").write_text(json.dumps(
        {"status": "ok", "timed_out": False, "started_at": "2026-10-30T01:00:00+08:00",
         "attempts": [{"n": 1, "session_id": "s-1"}],
         "usage": {"per_call": [1]}, "reward": 1, "weighted": 100.0}), encoding="utf-8")
    fr2 = accounting_frame(fslot)
    t("T22b.frame_parses_notexecuted",
      fr1["execution_state"] == "not_executed" and fr1["formal_admission"] is False
      and fr1["reason"] == "R7 frame 测试", str(fr1["execution_state"]))
    t("T22c.frame_parses_meta",
      fr2["execution_state"] == "executed" and fr2["score"] == {"reward": 1, "weighted": 100.0}
      and fr2["session"] == "s-1" and fr2["timed_out"] is False, str(fr2["execution_state"]))
    t("T22d.frame_identity_fields",
      fr1["slot_id"] == slot_f["slot_id"] and fr1["order"] == slot_f["order"]
      and fr1["design_commit_ref"] == "8b1043d05c5b9dd9b3ae5aa5982cea4e9e852825",
      "身份与封印引用")

    # ---- T23 R1：guards_used 推导与 inputs checked ----
    g1 = derive_guards({"checks": [
        {"id": "t1", "pass": True}, {"id": "t2", "pass": False},
        {"id": "g1", "pass": True}, {"id": "g2", "pass": False}],
        "n_tasks": 2, "correct": 1})
    # k=2, npass=2, guard_passes=1 → 原序首个和为 1 的二元组合
    t("T23a.guards_first_reconciling",
      g1["method"] == "first_reconciling_in_order" and g1["guards_used"] is not None
      and g1["conflict"] is None and g1["candidates"] >= 1, str(g1))
    g2c = derive_guards({"checks": [{"id": "x", "pass": True}],
                         "n_tasks": 2, "correct": 1})
    t("T23b.guards_conflict_marked",
      g2c["guards_used"] is None and g2c["method"] == "conflict", str(g2c))
    g3 = derive_guards({"checks": [{"id": "t1", "pass": True}], "n_tasks": 1,
                        "correct": 1})
    t("T23c.guards_k0_no_guards",
      g3["guards_used"] == [] and g3["method"] == "no_guards", str(g3))
    t("T23d.inputs_checked_emitted",
      (m19 if False else (meta or {})).get("inputs_verification", {}).get("checked") is not None
      or (meta or {}).get("inputs_verification", {}).get("checked") == 1,
      str((meta or {}).get("inputs_verification")))

    # ---- T24 R2 原则：ws 归档无 meta（模型可见域=inputs+TASK） ----
    ev7 = Path(r["evidence_dir"]) / "workspace"
    ws7 = HERE / "selftest" / "dry-ws" / slot["case"]
    t("T24.ws_contains_no_meta",
      not (ev7 / "meta.json").exists() and not (ws7 / "meta.json").exists()
      and (ws7 / "TASK.md").is_file(), "ws 仅 inputs+TASK")

    # ---- T8 R1 真值表（四态） ----
    s0 = SLOT_A
    acc_ne = acc_not_executed(s0, "E 未释放（合成）", "selftest")
    t("T8a.not_executed_nulls_and_false",
      acc_ne["score"] is None and acc_ne["started_at"] is None
      and acc_ne["session"] is None and acc_ne["usage"] is None
      and acc_ne["formal_admission"] is False, "null 非 0")
    acc_inf = acc_infrastructure(s0, "合成", "loc", diag_score=None)
    t("T8b.infrastructure_admission_false", acc_inf["formal_admission"] is False,
      "不按能力失败记零")
    acc_to = acc_executed(s0, {"reported": 0.0, "reward": 0}, True, "loc",
                          diag="合成超时帧")
    t("T8c.timeout_timed_out_pending_admission",
      acc_to["timed_out"] is True and acc_to["formal_admission"] is None,
      "限时真实分；准入由共同 gate 判定")
    acc_ok = acc_executed(s0, {"reported": 100.0, "reward": 1}, False, "loc")
    t("T8d.ok_pending_admission",
      acc_ok["timed_out"] is False and acc_ok["formal_admission"] is None,
      "能力低分不是拒收理由；准入由 gate 判定")

    # ---- T9 meta 帧语义 ----
    frame = build_meta_frame(SLOT_B, "2026-10-29T20:00:00+08:00", "a" * 40)
    t("T9a.tools_is_list", isinstance(frame["tools"], list), str(type(frame["tools"])))
    t("T9b.alias_not_actual",
      frame["declared_alias"] == "deepseek-v4.1-flash"
      and frame["actual_request_model"] is None
      and "not_observable" in frame["actual_request_model_status"], "R2")
    t("T9c.route_current_not_observed",
      frame["route"]["validation"] == "current_not_observed"
      and frame["route"]["route_verification"] == "current_not_observed"
      and frame["route"]["r2_history_ref"] == R2_EVIDENCE, "R2/§C")
    t("T9d.managed_unknowns_whitelist",
      [x["item"] for x in frame["managed_unknowns"]] ==
      ["gateway_upstream_model", "gateway_host_current",
       "effort_upstream_interpretation", "internal_tools_skills"], "R2 白名单")

    receipt = {"kind": "self_test", "batch": "l5-20261030-wb-gateway",
               "at": now_iso(), "model_calls": 0, "all_pass": ok, "results": results,
               "skipped": skipped,
               "skipped_note": "gate v2 未就位期间的诚实跳过（E 后补跑归零）",
               "live_doc_drift": []}
    out = write_json_once(HERE / "selftest" / "selftest-receipt-l5-wb-v1.json", receipt)
    rc = subprocess.run([sys.executable,
                         str(REPO / "1-评测方案/工具链/evidence-kit/receipt_check.py"), str(out)],
                        capture_output=True, text=True)
    t("T6.receipt_check_pass", rc.returncode == 0,
      f"receipt_check rc={rc.returncode}（细节不入收据）")
    receipt["all_pass"] = ok
    receipt["results"] = results
    write_json_atomic(out, receipt)
    print(f"[selftest] all_pass={ok} receipt={out}")
    for r in results:
        if not r["pass"]:
            print("  FAIL:", r["test"], r["detail"])
    return 0 if ok else 1


# ================================================================ CLI
def cmd_run_slot(slot_id: str, dry: bool = False) -> int:
    slots = {s["slot_id"]: s for s in wb_slots()}
    if slot_id not in slots:
        print(f"[run-slot] unknown slot {slot_id}")
        return 2
    if dry:
        fixture_case = HERE / "selftest" / "fixtures" / "fake-case"
        fixture_session = HERE / "selftest" / "fixtures" / "mock-session"
        driver_api = MockDriver(fixture_session)
        r = run_impl(slots[slot_id], driver_api, dry=True,
                     case_root=fixture_case,
                 ws_root=HERE / "selftest" / "dry-ws",
                     registered_at="2026-10-29T20:00:00+08:00",
                     preregistration_commit="a" * 40,
                     execution_seal_commit="c" * 40,
                     expect_checker_sha=sha256_file(fixture_case / "checker.py"))
        out = write_json_atomic(HERE / "selftest" / "dry-run-result.json",
                                {"kind": "dry_run", "at": now_iso(), "slot_id": slot_id,
                                 "mock_driver_calls": driver_api.calls,
                                 "status": r["status"], "accounting": r["accounting"],
                                 "live_doc_drift": []})
        print(f"[run-slot --dry] status={r['status']} result={out}")
        return 0
    gate = binding_gate()
    if not gate["ok"]:
        write_json_atomic(HERE / "receipts" / "release-refused.json",
                          {"kind": "release_refused", "at": now_iso(), "gate": gate,
                           "live_doc_drift": []})
        print("[run-slot] REFUSED: 共同 gate 未通过（fail-closed，零调用）")
        for rsn in gate["reasons"]:
            print("   -", rsn)
        return 2
    bv = binding_values()
    drv = RealDriver(9332)
    r = run_impl(slots[slot_id], drv, dry=False,
                 registered_at=bv.get("registered_at"),
                 preregistration_commit=bv.get("preregistration_commit"),
                 execution_seal_commit=bv.get("execution_seal_commit"))
    print(f"[run-slot] status={r['status']} evidence={r['evidence_dir']}")
    if r.get("meta", {}).get("product_version"):
        pass
    return 0 if r["status"] == "ok" else 1


def main(argv) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd, *rest = argv
    if cmd == "preflight":
        return cmd_preflight(live="--live" in rest)
    if cmd == "selftest":
        return cmd_selftest()
    if cmd == "verify-execution":
        r = adapter_verify_execution(rest[0])
        print(json.dumps({k: v for k, v in r.items() if k != "gate_evidence"},
                         ensure_ascii=False, indent=2))
        return 0 if r["ok"] else 1
    if cmd == "run-slot":
        return cmd_run_slot(rest[0], dry="--dry" in rest[1:])
    if cmd == "accounting":
        frames = [accounting_frame(s) for s in wb_slots()]
        out = write_json_atomic(HERE / "receipts" / "slot-accounting-frame.json",
                                {"kind": "slot_accounting_frame", "at": now_iso(),
                                 "slots": frames, "live_doc_drift": []})
        print(f"[accounting] frame={out}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
