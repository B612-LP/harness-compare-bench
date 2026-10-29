#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_drivers.py — judge harness 对抗性 driver 工厂（由 wb_fake_e2e.py 子进程导入）。

模式：
  completed       正常完成（终态 completed，DB model=声明 alias）
  alias_mismatch  终态 completed 但 DB model=deepseek-v3.2-exp（≠ 声明）
  no_trace        完成但 collect 零文件（trace 缺失负例）
  timeout_writing 达到时限、DB 仍 active、会话仍在写（cancel 竞态负例）
  active_idle     DB active + jsonl 停滞 ≥stable_s（假 completed 负例）
"""
from __future__ import annotations

import json
import time
from pathlib import Path


def now_iso() -> str:
    import datetime as dt
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(timespec="seconds")


FIXTURE_SESSION = [
    {"type": "session", "timestamp": "2026-10-29T20:00:00+08:00"},
    {"type": "message", "timestamp": "2026-10-29T20:01:00+08:00",
     "rawUsage": {"input_tokens": 100, "output_tokens": 10,
                  "cache_creation_input_tokens": 0, "cache_read_input_tokens": 50}},
    {"type": "message", "timestamp": "2026-10-29T20:02:00+08:00",
     "rawUsage": {"input_tokens": None, "output_tokens": None}},
    {"type": "message", "timestamp": "2026-10-29T20:03:00+08:00"},
]


class RecorderDriver:
    def __init__(self, mode="completed", session_model="deepseek-v4.1-flash"):
        self.mode = mode
        self.session_model = session_model
        self.calls = []
        self.cancel_attempts = 0

    def ensure_app(self):
        self.calls.append("ensure_app")
        return "mock-reused"

    def new_task(self, workspace_dir, prompt_text, model="DeepSeek V4.1-Flash",
                 title=None, port=9332, **kw):
        self.calls.append(["new_task", str(workspace_dir), model])
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
        """被 pin driver 目前没有 cancel API；本方法仅用于验证 wrapper 是否尝试。"""
        self.cancel_attempts += 1
        self.calls.append(["cancel", task_id])
        return {"stopped": True}

    def collect(self, task_id, dest_dir, workspace_dir=None):
        self.calls.append(["collect", task_id, str(dest_dir)])
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)
        if self.mode == "no_trace":
            return {"files": []}
        lines = []
        for o in FIXTURE_SESSION:
            o = dict(o)
            if o.get("type") == "session":
                o["model"] = self.session_model
            lines.append(json.dumps(o, ensure_ascii=False))
        (dest / "mock-session-0001.jsonl").write_text(
            "\n".join(lines) + "\n", encoding="utf-8")
        (dest / "session-row.json").write_text(json.dumps(
            {"id": task_id,
             "status": "active" if self.mode in ("active_idle", "timeout_writing")
             else "completed",
             "model": self.session_model, "thought_level": "low", "mode": "craft"},
            ensure_ascii=False) + "\n", encoding="utf-8")
        return {"files": [p.name for p in sorted(dest.iterdir())]}


def make_driver(mode: str) -> RecorderDriver:
    if mode == "alias_mismatch":
        return RecorderDriver("completed", session_model="deepseek-v3.2-exp")
    return RecorderDriver(mode)
