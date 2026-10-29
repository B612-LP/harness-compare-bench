#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fake_dsh.py — judge harness 的 dsh CLI 桩（经 lab.MOCK_CMD 注入，同 builder 契约形状）。

stdin=task；stdout=状态行（usage）；写 HOME/.dsh/sessions/l4-dsh-<ws.parent>-<ws.name>--<pid>/s.jsonl
（runner capture_session 按目录名 marker 匹配）。绝不联网。
env：FAKE_DSH_AUDIT（审计）、FAKE_DSH_WRITE（output.txt|wrong.txt）、FAKE_DSH_SLEEP、
FAKE_DSH_ORPHAN_COUNTER（同组或 setsid 孙进程持续写）、FAKE_DSH_ORPHAN_SETSID=1。
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

audit_path = os.environ.get("FAKE_DSH_AUDIT")
stdin_task = sys.stdin.read()


def audit(extra):
    if not audit_path:
        return
    e = dict(extra)
    e.update({"at": datetime.now().astimezone().isoformat(timespec="milliseconds"),
              "pid": os.getpid(), "pgid": os.getpgid(0)})
    with open(audit_path, "a") as f:
        f.write(json.dumps(e, ensure_ascii=False, default=str) + "\n")


args = sys.argv[1:]
# runner 调用形状：[python, fake_dsh.py, "bench-cli", "--json", "-"]（MOCK_CMD 可自定义）
ws = os.environ.get("FAKE_DSH_WS") or os.getcwd()
home = Path(os.environ["HOME"])
marker = "-dsh-%s-%s--" % (Path(ws).parent.name, Path(ws).name)
sess_dir = home / ".dsh" / "sessions" / ("l4%s%d" % (marker, os.getpid()))
sess_dir.mkdir(parents=True, exist_ok=True)

usage_full = {"inputTokens": 120, "outputTokens": 9,
              "cacheReadTokens": 80, "cacheWriteTokens": 0, "totalTokens": 209}
usage_nulls = {"inputTokens": None, "outputTokens": None,
               "cacheReadTokens": None, "cacheWriteTokens": None, "totalTokens": 0}
lines = [
    json.dumps({"type": "session", "id": "fx-dsh-%d" % os.getpid(),
                "cwd": ws, "version": "fake-dsh-0.0.1"}),
    json.dumps({"type": "assistant/message", "data": {"turn": 1, "step": 1,
               "message": {"content": [{"type": "text", "text": "fx answer"}]},
                           "usage": usage_full}}),
    json.dumps({"type": "assistant/message", "data": {"turn": 1, "step": 2,
               "message": {"content": [{"type": "text", "text": "fx answer2"}]},
                           "usage": usage_nulls}}),
    json.dumps({"type": "step/end", "data": {"turn": 1, "step": 1}}),
]
(sess_dir / "s.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
sys.stdout.write(json.dumps({"type": "status", "phase": "step_end", "turn": 1, "step": 1,
                             "usage": usage_full}) + "\n")
sys.stdout.flush()

mode = os.environ.get("FAKE_DSH_WRITE", "output.txt")
wsp = Path(ws)
(wsp / mode).write_text("WRONG" if mode == "wrong.txt" else "FAKE-OUTPUT\n", encoding="utf-8")

orph = os.environ.get("FAKE_DSH_ORPHAN_COUNTER")
if orph:
    child_code = (
        "import os,signal,time,sys,json,datetime\n"
        "p=%r\n"
        "if os.environ.get('FAKE_DSH_ORPHAN_SETSID')=='1':\n"
        "    pass\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "open(p+'.meta','w').write(json.dumps({'pid':os.getpid(),'pgid':os.getpgid(0)}))\n"
        "end=time.time()+40\nf=open(p,'a')\ni=0\n"
        "while time.time()<end:\n"
        "    f.write('%%d\\n'%%i); f.flush(); i+=1; time.sleep(0.25)\n"
        "f.close()\n" % orph)
    kw = {}
    if os.environ.get("FAKE_DSH_ORPHAN_SETSID") == "1":
        kw["start_new_session"] = True
    subprocess.Popen([sys.executable, "-c", child_code], **kw)
    time.sleep(0.3)

sleep_s = float(os.environ.get("FAKE_DSH_SLEEP", "0"))
audit({"args": args, "mode": mode, "sleep": sleep_s,
       "orphan": bool(orph), "session": str(sess_dir)})
if sleep_s:
    time.sleep(sleep_s)
sys.exit(int(os.environ.get("FAKE_DSH_EXIT", "0")))
