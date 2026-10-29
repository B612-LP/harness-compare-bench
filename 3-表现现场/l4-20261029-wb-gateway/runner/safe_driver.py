#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""safe_driver.py — L4 WB 批次专用 driver 包装（结构性禁用 SIGTERM 分支）。

纪律来源：
- L4 预注册 §3.C：不得为预检/运行终止用户现有会话、改网络配置、注入产品代码；
- lead 2026-10-29 指令：旧 driver ensure_app 的「无端口→SIGTERM 重启」分支必须**结构性**禁用，
  不是"先检查再调用"的竞态补丁；允许 CDP 复用或进程未起时干净启动；进程无端口绝不 kill。

实现方式：
- 导入本轮 pin 的 driver 快照副本（driver-snapshot/workbuddy_driver.py，哈希见 SHA256SUMS.txt）；
- 用模块属性替换（monkey-patch module attribute）把 `ensure_app` 换成 ensure_app_safe、
  把 `_quit_app` 换成 _forbidden_quit——driver 内 new_task(L379) 等所有内部调用点都在
  **调用时**解析模块全局名，因此任何路径到达 kill 逻辑都会先命中替身并响亮失败；
- ensure_app_safe 三分支：
    A. CDP <port> 已就绪            → 复用（连接 + 等 window.wb 桥），零产品影响；
    B. WB 进程不存在（pgrep 为空）  → driver._launch(port)（open -g 干净启动，无 env 注入）；
    C. WB 在跑但无调试端口          → 抛 WBUnsafeState，绝不 SIGTERM（调用方记
                                      infrastructure_not_executed / fail-closed）。
- 本模块不做任何网络/代理/keychain/settings/更新配置改动，无 hook、无 env 注入。
"""
from __future__ import annotations

import importlib.util
import subprocess
import urllib.request
from pathlib import Path

SNAPSHOT = Path(__file__).resolve().parent.parent / "driver-snapshot" / "workbuddy_driver.py"


def load_pinned_driver():
    """从本轮 pin 的快照导入 driver 模块（绝不 import 仓外活文件）。"""
    spec = importlib.util.spec_from_file_location("l4_wb_driver_snapshot", str(SNAPSHOT))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class WBUnsafeState(RuntimeError):
    """WB 在跑但无调试端口：非干扰接入不可得（禁止 SIGTERM 分支）。"""


def _cdp_up(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def _wb_running() -> bool:
    r = subprocess.run(["pgrep", "-f", "WorkBuddy.app/Contents/MacOS/"],
                       capture_output=True, text=True)
    return bool(r.stdout.strip())


def install_safe_driver(port: int = 9332):
    """加载快照 driver 并完成结构性替换；返回 (driver_mod, ensure_app_safe)。"""
    wd = load_pinned_driver()

    call_log = []

    def ensure_app_safe(p: int = port) -> str:
        """替代 driver.ensure_app。只允许复用或干净启动；绝不 kill。"""
        if _cdp_up(p):
            call_log.append({"branch": "reuse", "port": p})
            cdp = wd.CDP(p)
            wd._GLOBAL["cdp"] = cdp
            wd._GLOBAL["port"] = p
            try:
                cdp.close()
                cdp.connect()
                wd._wait_page_ready(cdp, timeout_s=20)
            except Exception as e:
                raise WBUnsafeState(
                    f"CDP {p} 在但页面/桥不可用：{e}；L4 禁止重启，记 infrastructure")
            return "reused"
        if not _wb_running():
            call_log.append({"branch": "clean-launch", "port": p})
            wd._launch(p)
            cdp = wd.CDP(p)
            wd._GLOBAL["cdp"] = cdp
            wd._GLOBAL["port"] = p
            cdp.close()
            cdp.connect()
            wd._wait_page_ready(cdp)
            return "launched"
        call_log.append({"branch": "unsafe-state", "port": p})
        raise WBUnsafeState(
            "WorkBuddy 在跑但无调试端口：非干扰接入不可得；"
            "L4 结构性禁用 SIGTERM 分支，本轮该槽记 infrastructure_not_executed")

    def _forbidden_quit(*_a, **_k):
        raise RuntimeError(
            "L4 structural prohibition: driver._quit_app/SIGTERM 在 wb-gateway 批次被禁用")

    # 结构性替换（调用时解析模块全局名 → 所有内部路径命中替身）
    wd.ensure_app = ensure_app_safe
    wd._quit_app = _forbidden_quit
    return wd, ensure_app_safe, call_log


# ---------------------------------------------------------------------------
# 严格完成判定 + 可验证停止（lead 2026-10-29 阻断修复）
#
# 依据（对 5.9.3 shipped asar 的 r2 只读解包副本静态定位，REA 范围）：
#   `wb:conversations:cancel` —— resources/extensions/edge-sync/server/index.cjs
#   @4532764（localConversationMethod 注册表，arg0=conversationId，与 fork/sendPrompt
#   并列）与 @4535903（sendPreparationGate.cancel(conversationId)，与 sendPrompt.begin
#   成对）。渲染层存在「停止生成」(stopGeneration) 动作；DB 终态含 cancelled/stopped。
# 调用链（静态已证部分）：
#   wb:conversations:cancel（edge-sync 原样转发）→ app 桥分发【压缩 bundle 未定位到
#   字面路由行，属数据驱动，记为边界】→ main/server.js SessionManager.cancel(e) →
#   cancelSessionRun(e,{kind:"user",reason:"cancelled"})：requestProcessingStop(r) +
#   **await r.backend.cancel(t)（转发运行中会话后端/kernel）** +
#   finalizeStaleToolCallsForDetachedCancel(r)（产品显式建模「取消后工具调用可能
#   detach 存活」）→ turn_completed/onProcessingStopped("interrupted")。
# 止步边界（不越证据）：backend.cancel 对已 spawn 工具**进程**的终止效果静态不可证
#   （acp requestCancelled 语义=协作式 abort；stale-tool finalize 的存在正是为此）。
# 纪律：stop_verified 必须三重验证——①DB 终态（cancelled/stopped）②trace 自 cancel
#   起零增长 ③本 workspace 作用域内仍可见 codebuddy 进程为空；任一不成立 →
#   stop_verified=false，不得视为已安全停止（timeout formal=false + 停后续槽）。
# 本模块不修改快照原件；对用户既有会话绝不发 cancel（仅限本批自建 session）。
# ---------------------------------------------------------------------------
import time as _time  # noqa: E402
import os
import subprocess as _subprocess  # noqa: E402


def _lsof(args, timeout_s=15):
    """lsof 间接层：自测在此层 mock，绝不替换探针函数本体。"""
    return _subprocess.run(args, capture_output=True, text=True, timeout=timeout_s)

TERMINAL_STATUSES = {"completed", "failed", "error", "cancelled", "stopped"}
POST_CANCEL_WINDOW_S = 15.0


def workspace_processes_still_active(workspace_dir: str) -> list:
    """本 workspace（含全部子目录）作用域内仍存活的进程（按 cwd 判定，全进程扫描）。

    保守语义：lsof 非零退出/超时/权限错误/输出不可解析 → 返回 ["probe-error"]，
    绝不当空列表（无法排除即拒 verified）。排除 runner 自身 pid。
    """
    ws = str(workspace_dir).rstrip("/")
    try:
        r = _lsof(["lsof", "-a", "-d", "cwd", "-Fn"])
        if r.returncode != 0:
            return ["probe-error"]
    except Exception:
        return ["probe-error"]
    alive, cur_pid = [], None
    for line in (r.stdout or "").splitlines():
        if line.startswith("p"):
            cur_pid = line[1:]
        elif line.startswith("n") and cur_pid:
            cwd = line[1:]
            if cwd == ws or cwd.startswith(ws + "/"):
                if cur_pid and cur_pid != str(os.getpid()) and cur_pid not in alive:
                    alive.append(cur_pid)
                cur_pid = None
    return alive


def cancel_session(wd, conv_id: str) -> dict:
    """对本批自建 session 调产品原生 cancel 通道（严禁用于用户既有会话）。"""
    cdp = wd._GLOBAL.get("cdp")
    if cdp is None:
        raise RuntimeError("CDP 未连接；cancel 不可用")
    r = cdp.wb_invoke("wb:conversations:cancel", conv_id, timeout_s=30)
    return r if isinstance(r, dict) else {"result": str(r)[:200]}


def wait_completion_strict(wd, task_id: str, timeout_s: float, workspace_dir: str,
                           stable_s: float = 15.0, poll_s: float = 3.0,
                           on_deadline=None,
                           process_probe=None,
                           post_cancel_window_s: float = POST_CANCEL_WINDOW_S) -> dict:
    """严格完成判定（替代 driver.wait_completion，不使用其 idle-stable 兜底）：

    - 完成仅认 DB 终态（completed/failed/error/cancelled/stopped）**且** trace 尺寸
      连续 stable_s 无增长；
    - DB active + trace 静默 ≠ 完成（思考停顿不误判）；
    - 到达 deadline：调用 on_deadline(task_id, snapshot)（runner 在此冻结 deadline
      证据并调用 cancel_session），随后 POST_CANCEL_WINDOW_S 内继续观察 DB 终态与
      trace 稳定，产出 stop_verified 判定；
    - 返回 {status, ended_at, stop_info, evidence}；status ∈ DB 终态值 或 "timeout"。
    """
    deadline_at = _time.time() + float(timeout_s)
    jp = wd._jsonl_path(workspace_dir, task_id)
    last_size, last_change = -1, _time.time()
    row = wd._db_row(task_id) or {}
    stop_info = {"stop_verified": None, "cancel_at": None, "post_cancel_db": None,
                 "post_cancel_trace_stable": None}
    while True:
        row = wd._db_row(task_id) or row
        stats = wd._jsonl_stats(jp)
        cur = stats.get("bytes", 0)
        if cur != last_size:
            last_size, last_change = cur, _time.time()
        db_status = (row.get("status") or "").lower()
        now = _time.time()
        if db_status in TERMINAL_STATUSES and (now - last_change) >= stable_s:
            return {"status": db_status, "ended_at": datetime_now_iso(),
                    "stop_info": stop_info,
                    "evidence": {"db_status": db_status, "trace_bytes": cur,
                                 "stable_s": round(now - last_change, 1)}}
        if now >= deadline_at:
            stop_info["deadline_reached_at"] = datetime_now_iso()
            stop_info["deadline_snapshot"] = {"db_status": db_status, "trace_bytes": cur}
            cancel_trace_bytes = cur
            if on_deadline is not None:
                stop_info.update(on_deadline(task_id, stop_info["deadline_snapshot"]) or {})
            # 全有界窗口观测：不在首次终态提前 break（与"连续稳定"声明一致）
            window_end = _time.time() + float(post_cancel_window_s)
            statuses, max_bytes = [], cur
            while _time.time() < window_end:
                row2 = wd._db_row(task_id) or row
                st2 = wd._jsonl_stats(jp)
                db2 = (row2.get("status") or "").lower()
                statuses.append(db2)
                max_bytes = max(max_bytes, st2.get("bytes", 0))
                _time.sleep(poll_s)
            stop_info["post_cancel_statuses"] = statuses
            stop_info["post_cancel_db"] = statuses[-1] if statuses else None
            saw_terminal, db_flapped = False, False
            for x in statuses:
                if x in ("cancelled", "stopped"):
                    saw_terminal = True
                elif saw_terminal:
                    db_flapped = True  # 终态后再现非终态＝翻转（保守拒）
            stop_info["post_cancel_db_terminal_seen"] = saw_terminal
            stop_info["post_cancel_db_flapped"] = db_flapped
            stop_info["post_cancel_trace_stable"] = (max_bytes == cancel_trace_bytes)
            probe_fn = process_probe or workspace_processes_still_active
            stop_info["post_cancel_processes"] = probe_fn(workspace_dir)
            stop_info["stop_verified"] = (
                saw_terminal and not db_flapped
                and stop_info["post_cancel_trace_stable"] is True
                and not stop_info["post_cancel_processes"])
            return {"status": "timeout", "ended_at": datetime_now_iso(),
                    "stop_info": stop_info,
                    "evidence": {"db_status": db_status, "trace_bytes": cur}}
        _time.sleep(poll_s)


def datetime_now_iso() -> str:
    from datetime import datetime, timezone, timedelta
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
