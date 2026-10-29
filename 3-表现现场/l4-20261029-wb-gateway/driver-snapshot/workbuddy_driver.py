#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""workbuddy_driver.py — WorkBuddy 桌面版零打扰自动化驱动。

原理：给 WorkBuddy(Electron) 带 --remote-debugging-port 启动（open -g 不抢焦点），
通过 CDP WebSocket 进入渲染进程，调用其内部 RPC 桥 window.wb.invoke(...)：
建任务/绑目录/选模型/发题面全程纯 JSON，不碰 DOM、不弹任何窗口、不需要焦点。

接口（编排器契约）：
  ensure_app(port=9332) -> None
  new_task(workspace_dir, prompt_text, model="DeepSeek V4.1-Flash") -> dict
  wait_completion(task_id, timeout_s) -> dict
  collect(task_id, dest_dir) -> dict

零打扰保证：
  - 只用 `open -g`（不激活）/ 已运行进程 SIGTERM（仅 WorkBuddy 自身，允许重启）
  - 不发全局键鼠事件、不写剪贴板、不截屏
  - 文件夹绑定走 RPC，绝不出原生 NSOpenPanel

依赖：系统 python3 + websocket-client（其余全标准库）。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import websocket
except ImportError:  # pragma: no cover
    print("[workbuddy] 缺 websocket-client：pip3 install --user websocket-client", file=sys.stderr)
    raise

APP_PATH = "/Applications/WorkBuddy.app"
HOME = Path.home()
WB_DB = HOME / ".workbuddy" / "workbuddy.db"
WB_PROJECTS = HOME / ".workbuddy" / "projects"
TZ = timezone(timedelta(hours=8))

# 终态（sessions.status）
TERMINAL_STATUS = {"completed", "failed", "error", "cancelled", "stopped"}
# 运行态（等待期继续轮询）
RUNNING_STATUS = {"active", "pending", "planning", "working", "streaming",
                  "waiting_permission", "waiting_confirmation", "queued"}

# UI 模型名 → 内部模型 id（create/sendPrompt 用 id）
MODEL_IDS = {
    "deepseek v4.1-flash": "deepseek-v4.1-flash",
    "deepseek-v4.1-flash": "deepseek-v4.1-flash",
    "deepseek v4-pro": "deepseek-v4-pro",
    "glm-5.3": "glm-5.3",
    "glm-5.3-flash": "glm-5.3-flash",
}
DEFAULT_MODEL_UI = "DeepSeek V4.1-Flash"
DEFAULT_THOUGHT_LEVEL = "low"  # 评测定案：思考档位取最低档


def _log(msg: str) -> None:
    print(f"[workbuddy {datetime.now(TZ).strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def model_id_of(model: str) -> str:
    key = (model or "").strip().lower()
    if key in MODEL_IDS:
        return MODEL_IDS[key]
    guess = re.sub(r"\s+", "-", key)
    _log(f"模型名 {model!r} 不在已知表，按规则推导 id={guess}")
    return guess


def workspace_slug(workspace_dir: str) -> str:
    """/Users/x/bench-workspaces/_probe/wb → Users-x-bench-workspaces-_probe-wb"""
    p = str(Path(workspace_dir).expanduser().resolve())
    return re.sub(r"^/", "", p).replace("/", "-")


class CDP:
    """极简 CDP 客户端：只做 Runtime.evaluate + 命令调用。"""

    def __init__(self, port: int, timeout: float = 60):
        self.port = port
        self.timeout = timeout
        self._ws = None
        self._id = 0
        self._target_id = None

    # ---------- 连接管理 ----------
    def http(self, path: str):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5) as r:
            return json.load(r)

    def cdp_up(self) -> bool:
        try:
            self.http("/json/version")
            return True
        except Exception:
            return False

    def _page_ws_url(self) -> str:
        targets = self.http("/json/list")
        pages = [t for t in targets if t.get("type") == "page"]
        if not pages:
            raise RuntimeError("CDP 起了但没有 page target（渲染进程未就绪）")
        # 主窗口 target：标题为 WorkBuddy 的那个
        for t in pages:
            if "WorkBuddy" in (t.get("title") or ""):
                return t["webSocketDebuggerUrl"]
        return pages[0]["webSocketDebuggerUrl"]

    def connect(self):
        if self._ws is not None:
            return
        url = self._page_ws_url()
        # Chrome>=111 会校验 Origin：必须 suppress_origin
        self._ws = websocket.create_connection(url, timeout=self.timeout, suppress_origin=True)
        self._id = 0
        # 防后台节流（页面不可见时的定时器/渲染限频）
        self.call("Emulation.setFocusEmulationEnabled", enabled=True)
        self.call("Runtime.enable")
        _ = self._target_id

    def close(self):
        if self._ws is not None:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None

    # ---------- 协议 ----------
    def call(self, method: str, **params):
        self._id += 1
        i = self._id
        self._ws.send(json.dumps({"id": i, "method": method, "params": params}))
        while True:
            msg = json.loads(self._ws.recv())
            if msg.get("id") == i:
                if "error" in msg:
                    raise RuntimeError(f"CDP {method}: {msg['error']}")
                return msg.get("result", {})

    def eval_js(self, expr: str, await_promise: bool = True, timeout_s: float = 120):
        """执行 JS 并返回 {'__ok__': value} 或 {'__err__': ...}。"""
        return self._evaluate(expr, await_promise, timeout_s)

    def _evaluate(self, expr, await_promise, timeout_s):
        self._id += 1
        i = self._id
        self._ws.send(json.dumps({
            "id": i, "method": "Runtime.evaluate",
            "params": {"expression": expr, "awaitPromise": await_promise,
                       "returnByValue": True, "timeout": int(timeout_s * 1000)},
        }))
        while True:
            msg = json.loads(self._ws.recv())
            if msg.get("id") == i:
                if "error" in msg:
                    return {"__err__": f"CDP: {msg['error']}"}
                r = msg.get("result", {})
                if r.get("exceptionDetails"):
                    det = r["exceptionDetails"]
                    return {"__err__": (det.get("exception", {}).get("description")
                                        or det.get("text", ""))[:500]}
                return {"__ok__": r.get("result", {}).get("value")}

    def wb_invoke(self, channel: str, *args, timeout_s: float = 120):
        """调用渲染进程 RPC：window.wb.invoke(channel, ...args)。参数走 JSON 字面量。"""
        args_js = ", ".join(json.dumps(a, ensure_ascii=False) for a in args)
        expr = (
            "(async () => { try {"
            f"  const v = await window.wb.invoke({json.dumps(channel)}{', ' if args_js else ''}{args_js});"
            "   return {ok: v === undefined ? null : v};"
            "} catch(e) { return {err: String(e && e.message || e).slice(0, 400)}; } })()"
        )
        r = self._evaluate(expr, True, timeout_s)
        if "__err__" in r:
            return {"__err__": r["__err__"]}
        v = r.get("__ok__")
        if isinstance(v, dict) and v.get("err"):
            return {"__err__": v["err"]}
        return {"__ok__": (v or {}).get("ok") if isinstance(v, dict) and "ok" in v else v}


# --------------------------------------------------------------------------
# App 生命周期
# --------------------------------------------------------------------------

def _clean_env() -> dict:
    """去掉会让 Electron 退化为 Node 的变量（本机 harness 环境带 ELECTRON_RUN_AS_NODE=1）。"""
    env = dict(os.environ)
    for k in ("ELECTRON_RUN_AS_NODE",):
        env.pop(k, None)
    return env


def _pids() -> list:
    r = subprocess.run(["pgrep", "-f", "WorkBuddy.app/Contents/MacOS/"],
                       capture_output=True, text=True)
    return [int(x) for x in r.stdout.split()]


def _quit_app(timeout_s: float = 20) -> None:
    pids = _pids()
    if not pids:
        return
    for p in pids:
        try:
            os.kill(p, 15)
        except ProcessLookupError:
            pass
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if not _pids():
            return
        time.sleep(0.5)
    _log("SIGTERM 未退出，继续等待（不升级 SIGKILL，避免损伤会话索引）")
    t0 = time.time()
    while time.time() - t0 < 10:
        if not _pids():
            return
        time.sleep(0.5)


def _launch(port: int, timeout_s: float = 45) -> None:
    env = _clean_env()
    # 注意：必须用显式路径。本机上 `open -a WorkBuddy` 会被 LaunchServices 静默丢弃。
    r = subprocess.run(["open", "-g", APP_PATH, "--args", f"--remote-debugging-port={port}"],
                       capture_output=True, text=True, env=env)
    if r.returncode != 0:
        raise RuntimeError(f"open 失败: rc={r.returncode} {r.stderr[:200]}")
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as resp:
                if resp.status == 200:
                    return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError(f"CDP {port} 端口 {timeout_s}s 内未就绪")


def _wait_page_ready(cdp: CDP, timeout_s: float = 60) -> None:
    """等 window.wb 桥出现（渲染层加载完成）。"""
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            cdp.close()
            cdp.connect()
            r = cdp._evaluate("typeof window.wb !== 'undefined' && typeof window.wb.invoke === 'function'", False, 10)
            if r.get("__ok__") is True:
                return
        except Exception:
            pass
        time.sleep(2)
    raise RuntimeError("window.wb 桥未就绪（渲染进程加载失败？）")


_GLOBAL = {"cdp": None, "port": None}


def ensure_app(port: int = 9332) -> None:
    """确保 WorkBuddy 带远程调试端口在跑。可重入；必要时重启 App（仅 WorkBuddy 自身）。"""
    cdp = _GLOBAL.get("cdp")
    if cdp is None:
        cdp = CDP(port)
        _GLOBAL["cdp"] = cdp
        _GLOBAL["port"] = port

    if cdp.cdp_up():
        try:
            cdp.close()
            cdp.connect()
            _wait_page_ready(cdp, timeout_s=15)
            _log(f"App 已在跑且 CDP 可用（port={port}）")
            return
        except Exception as e:
            _log(f"CDP 在但页面不可用（{e}），重启 App")
            _quit_app()
            _launch(port)
    else:
        running = bool(_pids())
        if running:
            _log("App 在跑但没有调试端口，重启以带端口")
            _quit_app()
        _launch(port)
    cdp.close()
    cdp.connect()
    _wait_page_ready(cdp)
    _log(f"App 启动完成，CDP port={port}")


# --------------------------------------------------------------------------
# DB / 轨迹文件
# --------------------------------------------------------------------------

def _db_row(session_id: str) -> dict | None:
    if not WB_DB.exists():
        return None
    uri = f"file:{WB_DB}?mode=ro"
    try:
        con = sqlite3.connect(uri, uri=True, timeout=5)
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        con.close()
        return dict(row) if row else None
    except sqlite3.Error as e:
        _log(f"读 DB 失败: {e}")
        return None


def _jsonl_path(workspace_dir: str, session_id: str) -> Path:
    return WB_PROJECTS / workspace_slug(workspace_dir) / f"{session_id}.jsonl"


def _jsonl_stats(p: Path) -> dict:
    try:
        st = p.stat()
        n = 0
        with open(p, "rb") as f:
            for _ in f:
                n += 1
        return {"exists": True, "bytes": st.st_size, "mtime": st.st_mtime, "lines": n}
    except FileNotFoundError:
        return {"exists": False}
    except OSError as e:
        return {"exists": True, "error": str(e)}


def _jsonl_last_event(p: Path) -> dict | None:
    try:
        with open(p, "rb") as f:
            lines = f.readlines()[-3:]
        for raw in reversed(lines):
            try:
                o = json.loads(raw)
                return {"type": o.get("type"), "ts": o.get("timestamp")}
            except Exception:
                continue
    except Exception:
        pass
    return None


# --------------------------------------------------------------------------
# 接口实现
# --------------------------------------------------------------------------

def _check(res: dict, what: str):
    if "__err__" in res:
        raise RuntimeError(f"{what} 失败: {res['__err__']}")
    return res.get("__ok__")


def new_task(workspace_dir: str, prompt_text: str,
             model: str = DEFAULT_MODEL_UI, *, title: str | None = None,
             thought_level: str = DEFAULT_THOUGHT_LEVEL,
             disabled_tools: list[str] | None = None,
             session_settings: dict | None = None,
             port: int = 9332) -> dict:
    """新建任务：绑目录 + 设模型 + 发题面。返回 {"id","started_at",...}。

    两种会话级禁工具注入通道（2026-10-27 探针实测）：
    - disabled_tools: create 顶层 `disabledTools` 参数 → 探针#1 实测被丢弃
      （session_settings 落库为空、工具表 43 全量），此通道无效；
    - session_settings: create 顶层 `sessionSettings` 对象，静态复核文档结构为
      {"workbuddy.claw.runtime": {"disabledTools": [...]}}；
    任何通道是否 runtime 生效，必须以 DB session_settings + daemon.log
    toolsCount/--tools= + 会话 jsonl 行为三方实测为准，不得静态推断。
    """
    ensure_app(port)
    cdp: CDP = _GLOBAL["cdp"]
    ws_dir = str(Path(workspace_dir).expanduser().resolve())
    Path(ws_dir).mkdir(parents=True, exist_ok=True)

    # 1) 刷新会话路由缓存（关键：否则后续 ensureRuntime 报 conversation not found）
    _check(cdp.wb_invoke("wb:conversations.local:list", {"page": 1, "size": 50}), "local:list")

    # 2) 建会话（绑 cwd、模型、权限、思考档位）
    if title is None:
        m = re.search(r"^[#＃\s]*([^\n]{4,60})", prompt_text.strip())
        title = (m.group(1).strip() if m else "bench-task")[:60]
    params = {
        "title": title,
        "cwd": ws_dir,
        "welcomeMode": "work",
        "mode": "craft",
        "model": model_id_of(model),
        "permissionMode": "fullAccess",
        "useSandboxCLI": False,
        "thoughtLevel": thought_level,
    }
    if disabled_tools:
        params["disabledTools"] = [str(x) for x in disabled_tools]
    if session_settings:
        params["sessionSettings"] = session_settings
    created = _check(cdp.wb_invoke("wb:conversations:create", params, timeout_s=60), "create")
    if not isinstance(created, dict) or not created.get("info", {}).get("id"):
        raise RuntimeError(f"create 返回异常: {json.dumps(created, ensure_ascii=False)[:300]}")
    conv_id = created["info"]["id"]
    started = datetime.now(TZ).isoformat(timespec="seconds")
    _log(f"会话已建: {conv_id} cwd={ws_dir} model={params['model']}"
         + (f" disabledTools={params.get('disabledTools')}" if disabled_tools else "")
         + (" sessionSettings=<inject>" if session_settings else ""))

    # 3) 再次刷缓存（让新会话对路由可见）+ 设思考档位 + 确保运行时
    _check(cdp.wb_invoke("wb:conversations.local:list", {"page": 1, "size": 50}), "local:list(2)")
    _check(cdp.wb_invoke("wb:conversations:configSetThoughtLevel", conv_id, thought_level),
           "configSetThoughtLevel")
    _check(cdp.wb_invoke("wb:conversations:ensureRuntime", conv_id, timeout_s=90), "ensureRuntime")
    time.sleep(2)

    # 4) 发题面（纯 JSON，长文本零丢失）
    send = _check(cdp.wb_invoke("wb:conversations:sendPrompt", conv_id,
                                [{"type": "text", "text": prompt_text}],
                                {"mode": "craft"}, timeout_s=180), "sendPrompt")
    _log(f"题面已发送（{len(prompt_text)} 字），send 返回: "
         f"{json.dumps(send, ensure_ascii=False)[:120] if send is not None else 'void'}")

    # 5) 落盘确认：jsonl 出现（或 DB 行 last_activity 更新）
    jp = _jsonl_path(ws_dir, conv_id)
    t0 = time.time()
    while time.time() - t0 < 90:
        if jp.exists():
            break
        row = _db_row(conv_id)
        if row and row.get("status") in ("completed",):
            break
        time.sleep(2)
    return {
        "id": conv_id,
        "started_at": started,
        "workspace_dir": ws_dir,
        "model": params["model"],
        "thought_level": thought_level,
        "disabled_tools": params.get("disabledTools"),
        "session_settings": params.get("sessionSettings"),
        "title": title,
        "jsonl": str(jp),
        "prompt_chars": len(prompt_text),
    }


def wait_completion(task_id: str, timeout_s: int, workspace_dir: str | None = None,
                    stable_s: float = 20.0, poll_s: float = 3.0) -> dict:
    """双保险完成判定：DB 终态 + jsonl 稳定。返回 {"status","ended_at","evidence"}。"""
    row = _db_row(task_id)
    if row is None:
        raise RuntimeError(f"DB 中无此会话: {task_id}")
    if workspace_dir is None:
        workspace_dir = row["cwd"]
    jp = _jsonl_path(workspace_dir, task_id)

    t0 = time.time()
    last_size = -1
    last_change = time.time()
    ended_at = None
    status = "timeout"
    while time.time() - t0 < timeout_s:
        row = _db_row(task_id) or row
        stats = _jsonl_stats(jp)
        cur = stats.get("bytes", 0)
        if cur != last_size:
            last_size, last_change = cur, time.time()
        db_status = (row.get("status") or "").lower()
        idle_stable = (stats.get("exists") and db_status in ("active", "")
                       and time.time() - last_change >= stable_s)
        if db_status in TERMINAL_STATUS or idle_stable:
            status = "completed" if db_status in ("completed",) or idle_stable else db_status
            ended_at = datetime.now(TZ).isoformat(timespec="seconds")
            break
        time.sleep(poll_s)
    else:
        ended_at = datetime.now(TZ).isoformat(timespec="seconds")

    stats = _jsonl_stats(jp)
    evidence = {
        "db": {
            "id": row.get("id"), "cwd": row.get("cwd"), "title": row.get("title"),
            "status": row.get("status"), "model": row.get("model"),
            "thought_level": row.get("thought_level"), "mode": row.get("mode"),
            "created_at": row.get("created_at"), "updated_at": row.get("updated_at"),
            "last_activity_at": row.get("last_activity_at"),
        },
        "jsonl": {
            "path": str(jp), "exists": stats.get("exists", False),
            "bytes": stats.get("bytes"), "lines": stats.get("lines"),
            "last_event": _jsonl_last_event(jp) if stats.get("exists") else None,
        },
        "stable_s": round(time.time() - last_change, 1),
        "waited_s": round(time.time() - t0, 1),
    }
    return {"status": status, "ended_at": ended_at, "evidence": evidence}


def collect(task_id: str, dest_dir: str, workspace_dir: str | None = None) -> dict:
    """收轨迹：jsonl(+rollback) + DB 行导出 + meta。返回 {"files":[相对路径...]}。"""
    row = _db_row(task_id)
    if row is None:
        raise RuntimeError(f"DB 中无此会话: {task_id}")
    if workspace_dir is None:
        workspace_dir = row["cwd"]
    dest = Path(dest_dir).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)
    files = []

    jp = _jsonl_path(workspace_dir, task_id)
    rollback = jp.parent / f"{task_id}.file-rollback.ndjson"
    for src in (jp, rollback):
        if src.exists():
            shutil.copy2(src, dest / src.name)
            files.append(src.name)

    (dest / "session-row.json").write_text(
        json.dumps(row, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    files.append("session-row.json")

    meta = {
        "task_id": task_id,
        "workspace_dir": workspace_dir,
        "collected_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "db_status": row.get("status"),
        "model": row.get("model"),
    }
    (dest / "collect-meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    files.append("collect-meta.json")
    _log(f"collect 完成 → {dest}（{len(files)} 个文件）")
    return {"files": files}


# --------------------------------------------------------------------------
# CLI 自测
# --------------------------------------------------------------------------

def _cli() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="WorkBuddy 零打扰驱动")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("ensure", help="确保 App+CDP")
    sp.add_argument("--port", type=int, default=9332)
    sp = sub.add_parser("probe", help="端到端探针")
    sp.add_argument("--workspace", default=str(HOME / "bench-workspaces/_probe/wb"))
    sp.add_argument("--port", type=int, default=9332)
    sp.add_argument("--timeout", type=int, default=600)
    sp.add_argument("--dest", default=None)
    args = ap.parse_args()

    if args.cmd == "ensure":
        ensure_app(args.port)
        return 0

    prompt = (
        "请在你的当前工作目录（workspace 根目录）下创建 answer.txt，"
        "内容严格为两行文本：第一行是 WORKBUDDY-CDP-PROBE，第二行是今天的日期 2026-10-25。"
        "创建完成后简短确认即可，不要做别的事情。\n"
        "（本条为自动化链路探针，验证长文本/换行可完整送达：\n"
        "第二段：包含「中文引号」、english words、path /tmp/x、反斜杠 \\ 与 emoji 🎯。）"
    )
    t = new_task(args.workspace, prompt, port=args.port)
    print(json.dumps(t, ensure_ascii=False, indent=1))
    r = wait_completion(t["id"], args.timeout, workspace_dir=args.workspace)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    c = collect(t["id"], args.dest or str(Path(__file__).parent / "probe-out"))
    print(json.dumps(c, ensure_ascii=False, indent=1))
    ans = Path(args.workspace) / "answer.txt"
    if ans.exists():
        print("answer.txt =>", repr(ans.read_text(encoding="utf-8")))
    return 0 if r["status"] == "completed" else 1


if __name__ == "__main__":
    sys.exit(_cli())
