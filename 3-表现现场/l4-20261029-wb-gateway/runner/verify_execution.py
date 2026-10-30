#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 事后公开整理版，非原封印源码；旧源码 hash 不适用于本版本。
"""verify_execution.py — L4 runtime-binding 释放闸门【薄适配层】。

方向（复核 2026-10-29 指令）：WB runner **必须调用共同 gate**
  1-评测方案/工具链/l4-execution/gate.py 的 verify_execution（含 E blob 等值、
  runtime 源漂移、manifest 全文件复核、registered_at==E git 时刻等全部封印检查），
  而不是共同 gate 调用本模块的弱化副本。本文件只是适配层：

    verify_execution(binding_path) -> {"ok": bool, "reasons": [...], "binding_path": ...}

fail-closed 语义：
- 共同 gate 缺失 / 导入失败 / 抛 GateError / 任何异常 → ok=false（零调用）；
- 本模块自身不做任何本地放行判定（不保留弱化副本逻辑）。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

GATE_PATH = (Path(__file__).resolve().parents[3] / "1-评测方案" / "工具链"
             / "l4-execution" / "gate.py")


def load_common_gate():
    """导入共同 gate 模块；缺失/损坏即抛（调用方 fail-closed）。"""
    if not GATE_PATH.is_file():
        raise FileNotFoundError(f"common gate missing: {GATE_PATH}")
    spec = importlib.util.spec_from_file_location("l4_common_gate", str(GATE_PATH))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "verify_execution"):
        raise AttributeError("common gate has no verify_execution")
    return mod


def verify_execution(binding_path) -> dict:
    try:
        gate = load_common_gate()
    except Exception as e:
        return {"ok": False, "reasons": [f"common gate unavailable: {e}"],
                "binding_path": str(binding_path),
                "rule": "fail-closed: 缺共同 gate 即零调用"}
    try:
        evidence = gate.verify_execution(binding_path, require_release=True)
        return {"ok": True, "reasons": [], "gate_evidence": evidence,
                "binding_path": str(binding_path),
                "rule": "共同 gate 全部封印检查通过（require_release=True）"}
    except TypeError:
        return {"ok": False, "reasons": ["common gate lacks require_release contract (v1)"],
                "binding_path": str(binding_path),
                "rule": "fail-closed: gate 契约版本不符即零调用"}
    except gate.GateError as e:
        return {"ok": False, "reasons": [f"GateError: {e}"],
                "binding_path": str(binding_path),
                "rule": "fail-closed: 任一封印检查失败即零调用"}
    except Exception as e:
        return {"ok": False, "reasons": [f"unexpected: {e}"],
                "binding_path": str(binding_path),
                "rule": "fail-closed: 任何异常即零调用"}
