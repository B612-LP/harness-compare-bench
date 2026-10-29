#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fake_codex.py — judge harness 的 codex CLI 桩（经 lab.CODEX_BIN 绝对路径注入）。

行为：读 stdin prompt；写 audit（argv/时刻/pid/stdio 摘要）；按 $CODEX_HOME/sessions/
YYYY/MM/DD/rollout-*.jsonl 写 session_meta(cwd=-C 参数) + token_usage_record 四态变体；
stdout 打 --json 风格事件行。绝不联网、绝不派生外部进程（除 FX_MODE 指定）。

FX_MODE: ok（默认）| sleep（睡满 60s，默认 TERM 即死）| trap（忽略 TERM 后睡 60s，
逼 runner 走 grace+SIGKILL 链）| residual（正常退出前派生 setsid 孙进程写文件）
FX_EXIT: 退出码（默认 0）；FX_NO_SESSION=1 则不写 session（capture 缺证据负例）
"""
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

audit_path = os.environ.get("FX_AUDIT")
args = sys.argv[1:]
stdin_bytes = sys.stdin.buffer.read() if not sys.stdin.isatty() else b""
entry = {"argv": args, "at": datetime.now().astimezone().isoformat(timespec="milliseconds"),
         "pid": os.getpid(), "pgid": os.getpgid(0),
         "stdin_sha256": hashlib.sha256(stdin_bytes).hexdigest()[:16],
         "codex_home": os.environ.get("CODEX_HOME"),
         "resolved_self": Path(__file__).resolve()}
try:
    entry["exe"] = os.readlink("/proc/%d/exe" % os.getpid())
except Exception:
    entry["exe"] = "darwin-no-procfs"


def audit(extra):
    if not audit_path:
        return
    entry2 = dict(entry)
    entry2.update(extra)
    entry2["at_end"] = datetime.now().astimezone().isoformat(timespec="milliseconds")
    with open(audit_path, "a") as f:
        f.write(json.dumps(entry2, ensure_ascii=False, default=str) + "\n")


def ws_from_args():
    if "-C" in args:
        return args[args.index("-C") + 1]
    return os.getcwd()


def write_session(ws):
    if os.environ.get("FX_NO_SESSION") == "1":
        return
    home = Path(os.environ["CODEX_HOME"])
    day = datetime.now().strftime("%Y/%m/%d")
    d = home / "sessions" / day
    d.mkdir(parents=True, exist_ok=True)
    p = d / ("rollout-%d.jsonl" % os.getpid())
    lines = [
        json.dumps({"type": "session_meta", "payload": {
            "id": "fx-session-%d" % os.getpid(), "cwd": ws,
            "cli_version": "fake-codex-0.0.1", "originator": "judge-harness"}},
            ensure_ascii=False),
    ]
    variants = [
        {"input_tokens": 120, "cached_input_tokens": 80, "cache_write_input_tokens": 0,
         "output_tokens": 9, "total_tokens": 209},
        {"input_tokens": None, "output_tokens": None, "total_tokens": 0},
        {},
    ]
    for i, u in enumerate(variants):
        lines.append(json.dumps({"type": "token_usage_record", "timestamp":
                      datetime.now().astimezone().isoformat(timespec="seconds"),
                      "payload": {"response_id": "resp-fx-%d-%d" % (os.getpid(), i),
                                  "turn_id": "t%d" % i, "usage": u}}, ensure_ascii=False))
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


mode = os.environ.get("FX_MODE", "ok")
ws = ws_from_args()
print(json.dumps({"type": "session_configured", "cwd": ws, "model": "deepseek-flash"}))
if mode in ("sleep", "trap"):
    if mode == "trap":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    write_session(ws)
    print(json.dumps({"type": "item.started", "note": "long generation"}), flush=True)
    audit({"mode": mode, "outcome": "sleeping"})
    time.sleep(60)
    audit({"mode": mode, "outcome": "slept-through"})
    sys.exit(0)
if mode == "orphan":
    # lead 指定回归：父正常退出；同组（不 setsid）子进程忽略 TERM 持续写 counter。
    # 审计项：spawn 时 PGID、子自身 pid/pgid（供与 runner saved_pgid 对组）。
    counter = os.environ.get("FX_ORPHAN_COUNTER", "/tmp/judge-l4/orphan-counter.txt")
    spawn_pgid = os.getpgid(0)
    child_code = (
        "import os,signal,time,sys,json,datetime\n"
        "p=%r\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "me={'pid':os.getpid(),'pgid':os.getpgid(0),'ppid':os.getppid()}\n"
        "open(p+'.meta','w').write(json.dumps(me))\n"
        "end=time.time()+40\n"
        "f=open(p,'a')\n"
        "i=0\n"
        "while time.time()<end:\n"
        "    f.write('%%d %%s\\n'%%(i,datetime.datetime.now().isoformat(timespec='milliseconds')))\n"
        "    f.flush(); i+=1; time.sleep(0.25)\n"
        "f.write('done\\n'); f.close()\n" % counter)
    subprocess.Popen([sys.executable, "-c", child_code])  # 同组：不 start_new_session
    time.sleep(0.4)  # 让子先落 meta
    write_session(ws)
    print(json.dumps({"type": "item.completed", "note": "parent exits, orphan child writing"}))
    try:
        (ws_path if False else Path(ws) / "output.txt").write_text("FAKE-OUTPUT\n",
                                                                   encoding="utf-8")
    except Exception:
        pass
    audit({"mode": "orphan", "outcome": "parent-exit", "spawn_pgid": spawn_pgid,
           "counter": counter})
    sys.exit(0)

if mode == "residual":
    child = Path(os.environ.get("FX_RESIDUAL_FILE", "/tmp/judge-l4/residual-probe.txt"))
    subprocess.Popen([sys.executable, "-c",
                      "import time,sys,pathlib;"
                      "p=pathlib.Path(%r);f=open(p,'a');"
                      "[ (f.write('g %%i\\n'%%i),f.flush(),time.sleep(0.5)) for i in range(40)];"
                      "f.close()" % str(child)],
                     start_new_session=True)
    time.sleep(0.3)
write_session(ws)
print(json.dumps({"type": "item.completed", "role": "assistant",
                  "text": "output.txt written"}))
ws_path = Path(ws)
(ws_path / "output.txt").write_text("FAKE-OUTPUT\n", encoding="utf-8")
audit({"mode": mode, "outcome": "completed", "session_written": True})
sys.exit(int(os.environ.get("FX_EXIT", "0")))
