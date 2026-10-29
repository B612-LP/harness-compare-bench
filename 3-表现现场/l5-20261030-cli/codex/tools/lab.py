#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L5 Codex 双槽 runner（plan.json 槽位为准；E 前全部真实调用 fail-closed）。

L4 预注册 §3B/§4：whole-execution restart=0（无整 CLI 重启、无 transport retry 重启工作区）；
基础设施错误与能力失败分开；timeout 沿用 plan 槽位值；每场原始证据先持久化母本
（write-once，禁覆盖），再在独立沙箱副本做 legacy/current 双归档反事实投影。

真实运行前置条件（fail-closed，全部满足才发请求）：
  1. 1-评测方案/自动循环L5-2026-10-30/runtime-binding.json 存在且 released_for_model_calls=true；
  2. binding.plan_sha256 / contract_sha256 与本地 plan.json/contract.json 实算一致；
  3. 1-评测方案/工具链/l5-execution/gate.py 的 verify_execution(binding_path) 通过。

用法：
  lab.py preflight                 # 零模型；版本/隔离 CODEX_HOME/隔离断言/checker 冒烟
  lab.py prepare <slot_id>         # 零模型；建仓外工作区+TASK.md+meta 骨架
  lab.py run <slot_id>             # 真实调用（E+release 后）；跑+判分+母本归档+双归档投影
  lab.py judge <slot_id>
  lab.py dual-archive <slot_id>    # 离线重放 legacy/current 两个归档语义（offline_recompute）
  lab.py status
  lab.py selftest                  # 合成测试（零模型、零网络、不读凭据）
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
BATCH = REPO / "3-表现现场" / "l5-20261030-cli" / "codex"
L4 = REPO / "1-评测方案" / "自动循环L5-2026-10-30"
PLAN_PATH = L4 / "plan.json"
CONTRACT_PATH = L4 / "contract.json"
BINDING_PATH = L4 / "runtime-binding.json"
GATE_PATH = REPO / "1-评测方案" / "工具链" / "l5-execution" / "gate.py"
CASE_ROOT = REPO / "2-用例"
WS_ROOT = Path.home() / "bench-workspaces" / "l5-20261030-cli" / "codex"
RUNS = BATCH / "runs"
CODEX_HOME = WS_ROOT / "_codex-home"
STRATUM = "cli_current_sentinel"
CODEX_BIN = "codex"  # mock 注入点：selftest 指向桩脚本，绝不触发真实 CLI
MODEL = "deepseek-flash"
EFFORT = "low"
RULE = "l5-20261030-batch-v1"
DESIGN_COMMIT_D = "8b1043d05c5b9dd9b3ae5aa5982cea4e9e852825"  # lead 2026-10-29 宣布的 D 封印

CODEX_CONFIG = """# l5-20261030 · Codex CLI 隔离 CODEX_HOME · DeepSeek V4.1-Flash · thinking=low
model = "deepseek-flash"
model_provider = "deepseek"
model_reasoning_effort = "low"
approval_policy = "never"
sandbox_mode = "danger-full-access"
web_search = "disabled"

[skills]
include_instructions = false
[skills.bundled]
enabled = false

[model_providers.deepseek]
name = "DeepSeek"
base_url = "https://api.deepseek.com"
env_key = "DEEPSEEK_API_KEY"
wire_api = "responses"
"""

DISCIPLINE = """
---
## 工作纪律（评测方要求，必须遵守）

1. 只在当前工作目录内读写：产物写在目录根下；题目明确允许修改的代码除外。
2. 不要访问这个目录之外的任何本机路径——不要 `ls` / `find` / `grep` 上级目录、家目录或其它项目目录。
3. 不要寻找判分器、参考答案、测试文件或其它用例目录；请按题面自行推导。
4. 不要联网搜索题解、原文或答案；本场按离线环境对待。
5. 需要假设时按题面合理假设，并在最终答复里简短说明。

完成后直接结束，不需要额外解释。
"""

INTEGRITY_PATTERNS = ["2-用例", "truth.json", "checker.py", "reference/", "solution/", "../",
                      "~/Documents", "harness-compare-bench"]


class FailClosed(Exception):
    pass


TRANSPORT_RE = re.compile(r"429|rate.?limit|too many requests|stream disconnected|connection reset"
                          r"|connection refused|temporarily unavailable|bad gateway|502|503"
                          r"|error sending request", re.I)


def claim_slot(slot: dict, binding: dict) -> Path:
    """R3 原子槽位 claim：任何 load_api_key/Popen 之前持久登记；已有 claim 一律拒绝
    （重复调用/崩溃恢复零额外外发）。O_EXCL 原子创建。"""
    ev = RUNS / slot["slot_id"]
    ev.mkdir(parents=True, exist_ok=True)
    claim = ev / "claim.json"
    payload = dump_obj({
        "slot_id": slot["slot_id"], "run_id": slot["run_id"], "event_id": slot["event_id"],
        "claimed_at": now_iso(), "design_commit_D": DESIGN_COMMIT_D,
        "execution_seal_commit": binding["execution_seal_commit"],
        "registered_at": binding["registered_at"],
        "note": "exactly one whole-execution attempt; restart cap 0（重复调用/崩溃后禁止补发）"})
    fd = os.open(str(claim), os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    try:
        os.write(fd, payload)
    finally:
        os.close(fd)
    return claim


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(p: Path) -> str:
    return sha(p.read_bytes())


def write_once(path: Path, data: bytes) -> None:
    """证据非破坏写：目标已存在即拒绝（绝不覆盖母本）。"""
    if path.exists():
        raise FailClosed(f"write-once violation: {path} already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def dump_obj(obj) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def load_plan_slots() -> list[dict]:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    slots = sorted((s for s in plan["product_slots"] if s["product"] == "codex"),
                   key=lambda s: s["order"])
    if len(slots) != 2 or len({s["slot_id"] for s in slots}) != 2:
        raise FailClosed(f"plan codex slots != 2 unique: {len(slots)}")
    for s in slots:
        if s["stratum"] != STRATUM or s["kind"] != "product_run":
            raise FailClosed("unexpected slot stratum/kind: " + s["slot_id"])
    return slots


def slot_by_id(slot_id: str) -> dict:
    for s in load_plan_slots():
        if s["slot_id"] == slot_id:
            return s
    raise FailClosed("slot not in plan (self-invented slots forbidden): " + slot_id)


def load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def load_binding(required: bool) -> dict | None:
    if not BINDING_PATH.exists():
        if required:
            raise FailClosed("runtime-binding.json 不存在（E 未封印）：真实调用 fail-closed")
        return None
    b = json.loads(BINDING_PATH.read_text(encoding="utf-8"))
    for k in ("design_commit", "preregistration_commit", "execution_seal_commit",
              "registered_at", "execution_manifest_sha256", "plan_sha256",
              "contract_sha256", "released_for_model_calls"):
        if k not in b:
            raise FailClosed("binding missing key: " + k)
    return b


def call_gate(binding_path: Path) -> None:
    """builder-dsh 的 gate.verify_execution；gate 缺失/异常一律 fail-closed。"""
    if not GATE_PATH.exists():
        raise FailClosed("gate.py 不存在（1-评测方案/工具链/l5-execution）：" + str(GATE_PATH))
    spec = importlib.util.spec_from_file_location("l4_gate", GATE_PATH)
    gate = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(gate)
    except Exception as e:  # noqa: BLE001
        raise FailClosed(f"gate import failed: {e}") from e
    if not hasattr(gate, "verify_execution"):
        raise FailClosed("gate.verify_execution missing")
    result = gate.verify_execution(str(binding_path), require_release=True)
    if result is not True and not (isinstance(result, dict) and result.get("ok") is True):
        raise FailClosed(f"gate.verify_execution rejected: {result!r}")


def gate_check_real() -> dict:
    """真实调用前三重 fail-closed 检查，返回 binding。"""
    b = load_binding(required=True)
    if b["released_for_model_calls"] is not True:
        raise FailClosed("released_for_model_calls is not true（lead 未释放 E）")
    if sha_file(PLAN_PATH) != b["plan_sha256"]:
        raise FailClosed("binding.plan_sha256 != local plan.json")
    if sha_file(CONTRACT_PATH) != b["contract_sha256"]:
        raise FailClosed("binding.contract_sha256 != local contract.json")
    if b["preregistration_commit"] != b["execution_seal_commit"]:
        raise FailClosed("binding: preregistration_commit != execution_seal_commit（lead E-blocker）")
    call_gate(BINDING_PATH)
    return b


def load_api_key() -> str:
    text = (Path.home() / ".dsh" / ".credentials.yaml").read_text(encoding="utf-8")
    m = re.search(r"^refs:\n((?:  .*\n)+)", text, re.M)
    if not m:
        raise FailClosed("credentials: refs 段未找到")
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        if k.strip() == "DEEPSEEK_API_KEY":
            return v.strip()
    raise FailClosed("credentials: DEEPSEEK_API_KEY 未找到")


def cli_version() -> str:
    out = subprocess.run(["codex", "--version"], capture_output=True, text=True, timeout=60)
    return (out.stdout or out.stderr).strip().splitlines()[0].strip()


def ws_dir(slot: dict) -> Path:
    return WS_ROOT / slot["slot_id"]


def build_task(case: str, ws: Path) -> str:
    body = (CASE_ROOT / case / "instruction.md").read_text(encoding="utf-8").rstrip()
    head = (
        "# 本场任务：%s（Codex CLI）\n\n"
        "**你的工作目录（绝对路径）：`%s`**\n\n"
        "请在这个目录里工作：输入都在该目录的 `inputs/` 下，产物按题目要求写到该目录里"
        "（题目里的相对路径都相对这个目录）。除题目明确要求修改的代码外，不要改动 `inputs/` 下的文件。\n\n"
        "---\n\n" % (case, ws)
    )
    return head + body + "\n" + DISCIPLINE


WS_ALLOWED_ROOT = Path.home() / "bench-workspaces"


def check_isolation(ws: Path) -> dict:
    problems = []
    if not str(ws).startswith(str(WS_ALLOWED_ROOT)):
        problems.append("workspace-not-under-bench-workspaces")
    if str(REPO) in str(ws):
        problems.append("workspace-inside-repo")
    for banned in ("truth.json", "checker.py"):
        if list(ws.rglob(banned)):
            problems.append("leak:" + banned)
    if list(ws.rglob("solution")):
        problems.append("leak:solution/")
    return {"ok": not problems, "problems": problems}


# ---------------------------------------------------------------- 命令

def cmd_preflight() -> int:
    """零模型预检：版本/隔离 CODEX_HOME/工作区隔离/checker 冒烟。不要求 binding。"""
    receipt = {"kind": "interface_preflight", "batch": "l5-20261030-cli-codex",
               "model_calls": 0, "at": now_iso(), "rule": RULE, "live_doc_drift": [],
               "design_commit_D": DESIGN_COMMIT_D, "codex": {"version": cli_version()}}
    if CODEX_HOME.exists():
        shutil.rmtree(CODEX_HOME)
    CODEX_HOME.mkdir(parents=True)
    write_once(CODEX_HOME / "config.toml", CODEX_CONFIG.encode("utf-8"))
    receipt["codex"]["config"] = {"path": str(CODEX_HOME / "config.toml"),
                                  "sha256": sha_file(CODEX_HOME / "config.toml"),
                                  "repo_snapshot": str(BATCH / "config" / "codex-config.toml"),
                                  "note": "E 封印快照同件：BATCH/config/codex-config.toml；E 后不许改；"
                                          "零模型阶段已生成可 hash（受控配置不含 key）"}
    sealed_cfg = BATCH / "config" / "codex-config.toml"
    if not sealed_cfg.exists():
        write_once(sealed_cfg, CODEX_CONFIG.encode("utf-8"))
    if sha_file(sealed_cfg) != sha_file(CODEX_HOME / "config.toml"):
        raise FailClosed("config snapshot drift")
    # lead 补充：配置闭包=零模型阶段生成+清单；CLI 全局上下文引用记录
    inventory = [{"path": str(q.relative_to(CODEX_HOME)), "sha256": sha_file(q)}
                 for q in sorted(CODEX_HOME.rglob("*")) if q.is_file()]
    receipt["codex"]["codex_home_inventory"] = inventory
    receipt["codex"]["global_context_note"] = (
        "隔离 CODEX_HOME 仅含 config.toml，无 AGENTS.md/全局指令文件（全局上下文引用=空）；"
        "工作区为非 git 目录（--skip-git-repo-check），repo 内 AGENTS.md 不会被发现；"
        "工作区 prompt 因绝对路径不同的混杂已在 meta.prompt_path_confound 显式诊断")
    receipt["e_external_files_suggestion"] = [
        {"path": str(BATCH / "config" / "codex-config.toml"),
         "sha256": sha_file(sealed_cfg),
         "use": "真实调用时逐字节比较（lab.py run 时 CODEX_HOME/config.toml == 本快照）"}]
    ws = WS_ROOT / "_isolation-probe"
    if ws.exists():
        shutil.rmtree(ws)
    ws.mkdir(parents=True)
    (ws / "inputs").mkdir()
    (ws / "inputs" / "dummy.txt").write_text("probe\n", encoding="utf-8")
    receipt["isolation_probe"] = check_isolation(ws)
    shutil.rmtree(ws)
    contract = load_contract()
    smoke = {}
    for case in sorted({s["case"] for s in load_plan_slots()}):
        if sha_file(CASE_ROOT / case / "checker.py") != contract["checker_sha256"][case]:
            raise FailClosed("checker drift vs contract: " + case)
        p = subprocess.run([sys.executable, str(CASE_ROOT / case / "checker.py"), "--help"],
                           capture_output=True, text=True, timeout=120)
        smoke[case] = {"exit": p.returncode}
    receipt["checker_smoke"] = smoke
    receipt["binding_state"] = "absent" if not BINDING_PATH.exists() else "present"
    receipt["ok"] = (receipt["isolation_probe"]["ok"]
                     and all(v["exit"] in (0, 2) for v in smoke.values()))
    out = BATCH / "preflight" / "codex-preflight.json"
    write_once(out, dump_obj(receipt))
    print(json.dumps({"ok": receipt["ok"], "receipt": str(out)}, ensure_ascii=False))
    return 0 if receipt["ok"] else 2


def cmd_prepare(slot_id: str) -> int:
    slot = slot_by_id(slot_id)
    ws = ws_dir(slot)
    if ws.exists():
        raise FailClosed("workspace already exists（换槽重跑禁止；如需诊断请人工检查）: " + str(ws))
    ws.mkdir(parents=True)
    shutil.copytree(CASE_ROOT / slot["case"] / "inputs", ws / "inputs")
    task = build_task(slot["case"], ws)
    write_once(ws / "TASK.md", task.encode("utf-8"))
    contract = load_contract()
    sealed_cfg = BATCH / "config" / "codex-config.toml"
    if not sealed_cfg.exists():
        write_once(sealed_cfg, CODEX_CONFIG.encode("utf-8"))
    config_ref = {"path": str(sealed_cfg), "sha256": sha_file(sealed_cfg),
                  "compare_at_run": "CODEX_HOME/config.toml 必须与该快照逐字节一致；不一致=配置漂移停槽",
                  "contains_key": False}
    meta = {
        "batch": "l5-20261030-cli", "rule_version": RULE,
        "design_commit_D": DESIGN_COMMIT_D,
        "preregistration_commit": None, "registered_at": None,  # run 时由 binding 填
        "slot_id": slot["slot_id"], "run_id": slot["run_id"], "event_id": slot["event_id"],
        "rep": slot["rep"], "order": slot["order"], "stratum": slot["stratum"],
        "product": "codex", "case": slot["case"], "form": "cli",
        "workspace": str(ws), "created_at": now_iso(),
        "model": MODEL, "reasoning_effort": EFFORT, "product_version": cli_version(),
        "timeout_s": slot["timeout_s"],
        "route": {"host": "api.deepseek.com", "provider_id": "deepseek",
                  "wire_protocol": "responses", "endpoint": "https://api.deepseek.com"},
        "tools": ["shell", "apply_patch", "read_files（web_search=disabled，skills=off）"],
        "permissions": "sandbox_mode=danger-full-access; approval_policy=never（隔离 CODEX_HOME）",
        "skills": "off", "web_search": "disabled",
        "soft_constraints": ["stay-in-workspace", "no-oracle-hunt", "offline"],
        "prompt_sha256": hashlib.sha256(task.encode()).hexdigest(),
        "prompt_path_confound": "workspace 绝对路径内嵌于 prompt；跨槽路径不同为设计内显式保留混杂",
        "whole_execution_restarts": 0, "replacements": 0,
        "isolation": check_isolation(ws),
        "inputs": [{"path": str(p.relative_to(ws)), "sha256": sha_file(p), "bytes": p.stat().st_size}
                   for p in sorted((ws / "inputs").rglob("*")) if p.is_file()],
        "inputs_verification": verify_inputs(ws, slot["case"]),
        "checker_sha256": contract["checker_sha256"][slot["case"]],
        "config_ref": config_ref,
    }
    if not meta["isolation"]["ok"]:
        print(json.dumps(meta["isolation"], ensure_ascii=False))
        return 2
    # R2（池 L5-3）：pre-run meta 不再写入模型可见 workspace（防 checker_sha256/config_ref/
    # 仓库绝对路径暴露与机械扫描回显命中）；改写仓内证据目录，ws 运行期仅含 inputs+TASK.md。
    ev = RUNS / slot["slot_id"]
    ev.mkdir(parents=True, exist_ok=True)
    write_once(ev / "meta.prepare.json", dump_obj(meta))
    print(json.dumps({"prepared": slot_id, "workspace": str(ws),
                      "prompt_sha256": meta["prompt_sha256"][:12]}, ensure_ascii=False))
    return 0


CANON_STREAMS = {"stdout": "agent.jsonl", "stderr": "agent.stderr.txt"}


def _persist_master(ev: Path, ws: Path, stream_files: dict[str, Path], meta: dict, prompt: str) -> None:
    """原始证据母本先落盘（write-once）：契约 C 规范名 prompt.txt/agent.jsonl/agent.stderr.txt/
    agent-session//workspace//checker.stdout + meta.json + config-snapshot/。"""
    (ev / "workspace").mkdir(parents=True, exist_ok=True)
    for p in ws.iterdir():
        if p.name in ("inputs", "meta.json") or p.name in stream_files.values():
            continue
        dst = ev / "workspace" / p.name
        if p.is_dir():
            shutil.copytree(p, dst, dirs_exist_ok=False)
        else:
            write_once(dst, p.read_bytes())
    write_once(ev / "prompt.txt", prompt.encode("utf-8"))
    for name, src_path in stream_files.items():
        final = CANON_STREAMS[name]
        if src_path.exists():
            data = src_path.read_bytes()
            write_once(ev / final, data)
            write_once(ev / (final + ".sha256"), (sha(data) + "\n").encode())
            write_once(ev / (final + ".bytes"), str(len(data)).encode())
    write_once(ev / "meta.partial.json", dump_obj(meta))  # 崩溃标记；终件 meta.json 最后一次写
    cfg = ev / "config-snapshot"
    cfg.mkdir(parents=True, exist_ok=True)
    write_once(cfg / "codex-config.toml", Path(CODEX_HOME / "config.toml").read_bytes())


USAGE_FIELDS = ("input_tokens", "cached_input_tokens", "cache_write_input_tokens",
                "output_tokens", "reasoning_output_tokens", "total_tokens")


def presence(v):
    """L4 §2A：缺失/null/0/正值 四态分开，绝不合并（lead 源码勘误：r1031 提取层 `or 0`
    曾把 absent/null/0 合并，历史 creation=0 不能统一归因 SDK 默认值）。"""
    if isinstance(v, dict) or isinstance(v, list):
        return "non-scalar"
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "non-scalar"
    if isinstance(v, (int, float)):
        return "zero" if v == 0 else "positive"
    if isinstance(v, str):
        return "string"
    return "missing"


def extract_usage(sess_dir: Path) -> dict:
    """usage 提取（L4 修正版）：usage_raw 逐 response 原样保存 + 逐字段 presence；
    数值视图（lossy，absent→0）仅用于跨场求和，权威以 usage_raw/presence 为准。
    本探针结果与历史 rollout 非同请求，禁止逐调用一一对应。"""
    per_call, seen = [], set()
    for p in sorted(sess_dir.rglob("*.jsonl")):
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                ev = json.loads(line)
            except Exception:
                continue
            if not isinstance(ev, dict) or ev.get("type") != "token_usage_record":
                continue
            pay = ev.get("payload") or {}
            u = pay.get("usage") or {}
            rid = pay.get("response_id")
            if rid and rid in seen:
                continue
            seen.add(rid)
            per_call.append({
                "ts": ev.get("timestamp"), "response_id": rid, "turn_id": pay.get("turn_id"),
                "usage_raw": pay.get("usage"),
                "usage_presence": {k: ("missing" if k not in u else presence(u[k]))
                                   for k in USAGE_FIELDS},
                "input_tokens": int(u.get("input_tokens") or 0),
                "cache_read_tokens": int(u.get("cached_input_tokens") or 0),
                "cache_creation_tokens": int(u.get("cache_write_input_tokens") or 0),
                "output_tokens": int(u.get("output_tokens") or 0),
                "reasoning_output_tokens": int(u.get("reasoning_output_tokens") or 0),
                "total_tokens": int(u.get("total_tokens") or 0),
            })
    s = lambda k: sum(r[k] for r in per_call)  # noqa: E731
    pres = {k: {} for k in USAGE_FIELDS}
    for r in per_call:
        for k, st in r["usage_presence"].items():
            pres[k][st] = pres[k].get(st, 0) + 1
    return {"requests": len(per_call), "input_tokens": s("input_tokens"),
            "output_tokens": s("output_tokens"), "cache_read_tokens": s("cache_read_tokens"),
            "cache_creation_tokens": s("cache_creation_tokens"),
            "reasoning_output_tokens": s("reasoning_output_tokens"),
            "total_tokens": s("total_tokens"), "per_call": per_call,
            "presence_summary": pres,
            "semantics_note": ("数值列为 lossy 投影（缺失→0 仅为求和 convenience）；字段缺失/null/0/正值 "
                               "四态以 usage_raw+usage_presence 为准；cache_creation_tokens 的历史 0 "
                               "在 codex 侧不能区分 absent/null/0（r1031 提取层 or 0 合并），dsh 侧为 "
                               "session log 键存在且值 0——两产品字段源层不同，报告须分开陈述"),
            "source": "session rollout token_usage_record（母本 agent-session/）；"
                      "与历史 rollout 非同请求，不做逐调用对应"}


def scan_integrity(ev: Path) -> dict:
    hits, n = [], 0
    for p in list(sorted(ev.rglob("agent-session.raw/**"))) + [ev / "stdout.raw"]:
        pass
    hits = []
    files = list((ev / "agent-session").rglob("*.jsonl")) if (ev / "agent-session").is_dir() else []
    if (ev / "agent.jsonl").exists():
        files.append(ev / "agent.jsonl")
    for p in files:
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines()):
            n += 1
            try:
                blob = json.dumps(json.loads(line), ensure_ascii=False)
            except Exception:
                blob = line
            for pat in INTEGRITY_PATTERNS:
                if pat in blob:
                    hits.append({"file": str(p.relative_to(ev)), "line": i + 1,
                                 "pattern": pat, "excerpt": blob[:300]})
                    break
            if len(hits) >= 20:
                break
    return {"violations": len(hits), "patterns": INTEGRITY_PATTERNS,
            "lines_scanned": n, "evidence": hits,
            "method": "session + runner-stdout rescan（母本只读）", "live_doc_drift": []}


VALIDATOR_PATH = REPO / "1-评测方案" / "工具链" / "runner-schema-v2" / "validate_runner_meta.py"


def l3_field_component(meta: dict, seal_at_iso: str | None):
    """真实调用 L3 validate_meta/classify（非 fieldnames 覆盖）；组件失败保留诊断不静默。"""
    if not VALIDATOR_PATH.exists():
        return {"available": False, "reason": "validator missing"}
    spec = importlib.util.spec_from_file_location("l3_validator", VALIDATOR_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    seal = mod.parse_iso(seal_at_iso) if seal_at_iso else None
    res = mod.validate_meta(meta, seal_at=seal)
    return {"available": True, "classify": mod.classify(res), "issues": res["issues"],
            "note": "L3 组件仅 field-compliance；formal_admission 另由 gate_admission 语义门判定"}


def verify_inputs(ws: Path, case: str) -> dict:
    """R1（池 L5-1）：派发前把 ws 实际输入对 contract.case_snapshots.files 的 inputs/* 子集
    机械比对（SHA256+集合等值），发射 meta.inputs_verification。"""
    contract = load_contract()
    want = {k: v for k, v in (contract["case_snapshots"][case].get("files") or {}).items()
            if k.startswith("inputs/")}
    got = {"inputs/" + str(p.relative_to(ws / "inputs")): sha_file(p)
           for p in sorted((ws / "inputs").rglob("*")) if p.is_file()}
    mismatches = [k for k in sorted(want) if got.get(k) != want[k]]
    unexpected = [k for k in sorted(got) if k not in want]
    return {"ok": bool(want) and not mismatches and not unexpected, "checked": len(want),
            "mismatches": mismatches, "unexpected": unexpected,
            "method": "sha256 ws/inputs vs contract.case_snapshots.files[inputs/*]"}


def judge_counts(res: dict):
    """checker 自报计数的规范别名序（与 L4 score8_reported 同序）。"""
    for a, b in (("correct", "n_questions"), ("correct", "n_tasks"),
                 ("passed_problems", "total_problems"), ("passed", "total")):
        if isinstance(res.get(a), int) and isinstance(res.get(b), int) and res.get(b):
            return res[a], res[b]
    return None, None


def derive_guards(res: dict, denominator: int) -> dict:
    """R1：guards_used=「索引序字典序首个 reconciling 组合」机械推导。

    k=len(checks)-possible，guard 通过数=npass-correct；按 checks 原序 combinations(k)
    找首个满足集，记录 candidates 总数与 method；无解发 conflict 让 gate 必 fail，
    禁止静默乱选。已验证：cargo guards=[input_integrity,code_rerun,plan_structure]，
    dab guards=[answers_format,input_integrity]。"""
    checks = [c for c in (res.get("checks") or []) if isinstance(c, dict) and c.get("id")]
    earned, possible = judge_counts(res)
    if possible is None:
        possible = denominator
    n = len(checks)
    k = n - possible
    out = {"guards_used": None, "guards_candidates": 0,
           "guards_method": "canonical_first_reconciliation", "guards_conflict": True}
    if earned is None or not (0 <= k <= n):
        return out
    from itertools import combinations
    candidates = 0
    first = None
    for combo in combinations(range(n), k):
        scored = [c for i, c in enumerate(checks) if i not in combo]
        if len(scored) == possible and sum(1 for c in scored if c.get("pass") is True) == earned:
            candidates += 1
            if first is None:
                first = [checks[i]["id"] for i in combo]
    out["guards_used"], out["guards_candidates"], out["guards_conflict"] = first, candidates, first is None
    return out


def judge_block(slot: dict, res) -> dict:
    """R1：gate 契约的 meta.judge 结构块；raw checker 输出只留在 checker.stdout 与
    score-receipt.raw_checker_output，不再整体并入 meta。"""
    contract = load_contract()
    chk = sha_file(CASE_ROOT / slot["case"] / "checker.py")
    if not isinstance(res, dict):
        return {"checker_sha256": chk, "guards_used": None, "guards_candidates": 0,
                "guards_method": "canonical_first_reconciliation", "guards_conflict": True,
                "correct": None, "n_tasks": None, "weighted": None, "exit_code": None,
                "raw_output_ref": None, "note": "no parseable checker output"}
    g = derive_guards(res, contract["denominators"][slot["case"]])
    earned, possible = judge_counts(res)
    return {"checker_sha256": chk, "guards_used": g["guards_used"],
            "guards_candidates": g["guards_candidates"], "guards_method": g["guards_method"],
            "guards_conflict": g["guards_conflict"],
            "correct": earned, "n_tasks": possible,
            "weighted": score8_reported(res), "exit_code": 0,
            "raw_output_ref": "checker.stdout"}


def score8_reported(j: dict):
    earned, possible = None, None
    for a, b in (("correct", "n_questions"), ("correct", "n_tasks"),
                 ("passed_problems", "total_problems"), ("passed", "total")):
        if isinstance(j.get(a), int) and isinstance(j.get(b), int) and j.get(b):
            earned, possible = j[a], j[b]
            break
    if earned is None:
        return None
    return round(earned / possible * 100, 8)


def score_receipt(slot: dict, res: dict, meta: dict) -> dict:
    contract = load_contract()
    reported = score8_reported(res)
    receipt = {
        "case": slot["case"], "product": "codex", "slot_id": slot["slot_id"],
        "run_id": meta["run_id"], "live_doc_drift": [],
        "score": {"earned": res.get("correct", res.get("passed")),
                  "possible": res.get("n_questions", res.get("n_tasks", res.get("total_problems", res.get("total")))),
                  "reported": reported, "reward": res.get("reward"),
                  "rule_version": RULE,
                  "denominator": contract["denominators"][slot["case"]],
                  "checker_sha256": sha_file(CASE_ROOT / slot["case"] / "checker.py")},
        "raw_checker_output": res,
    }
    return receipt


def judge(slot: dict) -> dict:
    ws = ws_dir(slot)
    p = subprocess.run([sys.executable, str(CASE_ROOT / slot["case"] / "checker.py"), str(ws), "--json"],
                       capture_output=True, text=True, timeout=1200, cwd=str(REPO))
    # lead 勘误：checker exit1 + 合法评分 JSON = 正常评分（能力低分照收），绝不混为 CLI 基础设施失败；
    # 仅当 stdout 无可解析评分结构才视为 judge 失败（reward=None → diagnostic 路径）。
    try:
        res = json.loads(p.stdout.strip().splitlines()[-1])
        if isinstance(res, dict):
            res["checker_exit_code"] = p.returncode
            res["judge_note"] = ("checker exit1 + 合法评分 JSON 属正常评分路径；"
                                 "评分器退出码不并入 CLI status/infra 分类")
        return res
    except Exception:
        return {"reward": None, "checker_exit_code": p.returncode,
                "error": (p.stdout + p.stderr)[-2000:]}


def identify_rollout(q: Path, ws: Path) -> dict | None:
    """从 rollout 头部读 session_meta：session/thread id 与 cwd 精确证据。"""
    try:
        with q.open("r", encoding="utf-8", errors="replace") as fh:
            for _ in range(20):
                line = fh.readline()
                if not line:
                    break
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                if isinstance(ev, dict) and ev.get("type") == "session_meta":
                    pay = ev.get("payload") or {}
                    return {"session_id": pay.get("id") or pay.get("session_id"),
                            "thread_id": pay.get("thread_id"),
                            "cwd": pay.get("cwd"),
                            "cli_version": pay.get("cli_version")}
    except OSError:
        pass
    return None


def capture_session(ev: Path, ws: Path, started_iso: str) -> dict:
    """会话捕获：以 session_meta.cwd==ws 精确匹配（mtime 仅作次级弱信号，不单独采用），
    防止混入上一场会话；识别证据落 session-capture.json。"""
    sdir = CODEX_HOME / "sessions"
    sess = ev / "agent-session"
    sess.mkdir(parents=True, exist_ok=True)
    st = dt.datetime.fromisoformat(started_iso).timestamp()
    matched, rejected = [], []
    if sdir.is_dir():
        for q in sorted(sdir.rglob("*.jsonl")):
            ident = identify_rollout(q, ws) or {}
            if ident.get("cwd") == str(ws):
                write_once(sess / q.name, q.read_bytes())
                matched.append({"file": q.name, **ident})
            else:
                rejected.append({"file": q.name, "cwd": ident.get("cwd"),
                                 "mtime_in_window": q.stat().st_mtime >= st - 5})
    cap = {"matched_by": "session_meta.cwd==workspace", "matched": matched,
           "rejected": rejected, "workspace": str(ws),
           "started_at": started_iso,
           "note": "mtime-only 采纳已废除（lead 审查：可能混入上一场）；无匹配=0 文件并如实报告"}
    write_once(ev / "session-capture.json", dump_obj(cap))
    if not matched:
        raise FailClosed("session capture: no rollout matched workspace cwd —— 会话证据缺失，如实报错")
    return cap


def close_process_group(proc, ev: Path, slot: dict, phase: str, grace_s: float = 10.0,
                        saved_pgid: int | None = None, attempt: dict | None = None) -> dict:
    """父运行器停止保障（lead fail-closed 纪律 + 首失败修正）：
    · saved_pgid 为权威组身份：Popen(start_new_session) 时子进程即组长，调用方必须在启动时
      保存 proc.pid 并传入；父侧 os.getpgid 失败（父已被收割→ESRCH）**不得**推断组消失——
      孤儿孙代仍可活跃写（首失败 FIRST-FAILURE-close-process-group-esrch）。
    · term_delivery 与 probe 分开记录：SIGTERM 送达 ≠ 已验证组消失；
    · verified 仅在探活确认组消失时为 true；探活被拒/宽限后仍存活/无组身份 → verified=false；
    · verified=false（timeout 路径）→ runner_formal_eligible=false + 停批 + 通知 lead（cmd_run 处理）；
    · 正常退出同样检查组闭合；探活不可行 → residual_risk_disclosed=true 强制披露；
    · 不以「写入暂时不变」冒充进程全停；回退杀直接子进程不改变 verified。"""
    import signal
    receipt = {"slot_id": slot["slot_id"], "run_id": slot.get("run_id"),
               "event_id": slot.get("event_id"),
               "pid": proc.pid, "saved_pgid": saved_pgid,
               "attempt": attempt or {}, "phase": phase, "at": now_iso()}
    pgid = saved_pgid
    if pgid is not None:
        receipt["pgid_source"] = "saved_at_dispatch"
    else:
        # 未保存组身份：仅允许一次 fallback 尝试，且其结果不作为 verified 依据（如实标注）
        try:
            pgid = os.getpgid(proc.pid)
            receipt["pgid_source"] = "fallback_getpgid_unsaved(weaker)"
        except (ProcessLookupError, PermissionError):
            pgid = None
            receipt["pgid_source"] = "unavailable"
    receipt["pgid"] = pgid
    delivery, probe = "skipped", "not_attempted"
    if pgid is None:
        # 无组身份 → 无法组级操作也无法验证；绝不当作「组必已消失」
        delivery, probe = "skipped-no-group-identity", "no_group_identity"
    else:
        if phase == "timeout":
            try:
                os.killpg(pgid, signal.SIGTERM)
                delivery = "delivered"
            except ProcessLookupError:
                delivery = "no-such-group"
            except PermissionError:
                delivery = "denied"
        deadline = time.time() + grace_s
        while True:
            try:
                os.killpg(pgid, 0)
            except ProcessLookupError:
                probe = "verified_gone"
                break
            except PermissionError:
                probe = "probe_denied"
                break
            if time.time() >= deadline:
                probe = "still_alive_after_grace"
                break
            time.sleep(0.2)
        if delivery == "delivered" and probe == "still_alive_after_grace":
            try:
                os.killpg(pgid, signal.SIGKILL)
                delivery += "+SIGKILL"
            except PermissionError:
                delivery += "+SIGKILL:denied"
            except ProcessLookupError:
                pass
            try:
                os.killpg(pgid, 0)
                probe = "still_alive_after_kill"
            except ProcessLookupError:
                probe = "verified_gone"
            except PermissionError:
                probe = "probe_denied"
    if phase == "normal_exit" and probe in ("still_alive_after_grace", "probe_denied"):
        # lead：正常退出组仍活 → 同样有界清理/核实，不能只披露后准入
        try:
            os.killpg(pgid, signal.SIGTERM)
            delivery += "+normal-exit:SIGTERM"
        except (ProcessLookupError, PermissionError):
            delivery += "+normal-exit:SIGTERM:failed"
        deadline = time.time() + grace_s
        while time.time() < deadline:
            try:
                os.killpg(pgid, 0)
            except ProcessLookupError:
                probe = "verified_gone"
                break
            except PermissionError:
                probe = "probe_denied"
                break
            time.sleep(0.2)
        else:
            probe = "still_alive_after_grace"
        if probe == "still_alive_after_grace":
            try:
                os.killpg(pgid, signal.SIGKILL)
                delivery += "+normal-exit:SIGKILL"
            except (ProcessLookupError, PermissionError):
                delivery += "+normal-exit:SIGKILL:failed"
            try:
                os.killpg(pgid, 0)
                probe = "still_alive_after_kill"
            except ProcessLookupError:
                probe = "verified_gone"
            except PermissionError:
                probe = "probe_denied"
    receipt["term_delivery"] = delivery
    receipt["probe"] = probe
    receipt["signal"] = ("SIGKILL" if delivery.endswith("+SIGKILL")
                         else "SIGTERM" if delivery.startswith(("delivered", "no-such-group"))
                         else None)
    verified = probe == "verified_gone"
    fallback = False
    if phase == "timeout" and not verified and proc.poll() is None:
        try:  # 回退只停直接 CLI；绝不因回退成功而宣称组已停
            proc.terminate()
            try:
                proc.wait(timeout=grace_s)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=grace_s)
            fallback = True
        except ProcessLookupError:
            pass
    receipt["verified"] = verified
    receipt["verified_stop"] = verified      # gate 权威 bool 仅在 doc 原物（契约⑥）
    receipt["group_confirmed_gone"] = verified   # atk14–16 契约：组级确认消失
    receipt["ack_at"] = now_iso()            # 停止流程完成时点
    receipt["fallback_child_kill"] = fallback
    receipt["direct_child_returncode"] = proc.poll()
    if pgid is None:
        receipt["limitation"] = ("无已存 PGID 且父侧 getpgid 不可得：组身份未知，verified=false；"
                                 "孤儿孙代存活风险如实披露（首失败修正语义）")
    elif probe == "probe_denied":
        receipt["residual_risk_disclosed"] = True
        receipt["limitation"] = ("探活被环境拒绝（EPERM）：无法验证组内孙代是否全停；"
                                 "SIGTERM 送达状态见 term_delivery；行为学观察仅作辅助证据，"
                                 "不作为 verified 依据")
    write_once(ev / "termination.json", dump_obj(receipt))
    return receipt


def cmd_run(slot_id: str) -> int:
    halt = BATCH / "halt.json"
    if halt.exists():
        raise FailClosed("批次已因未验证终止停批（halt.json）；待 lead 处置，不得续槽")
    slot = slot_by_id(slot_id)
    binding = gate_check_real()  # fail-closed：E 未封印/未释放/哈希不符/gate 拒绝 → 不发请求
    sealed_cfg = BATCH / "config" / "codex-config.toml"
    live_cfg = CODEX_HOME / "config.toml"
    if not sealed_cfg.exists() or not live_cfg.exists() \
            or sha_file(sealed_cfg) != sha_file(live_cfg):
        raise FailClosed("配置漂移：CODEX_HOME/config.toml != E 候选快照（停槽，首次失败保存）")
    claim = claim_slot(slot, binding)  # R3：原子 claim，先于 load_api_key/Popen；重复调用在此拒绝
    ws = ws_dir(slot)
    if not (ws / "TASK.md").exists():
        if cmd_prepare(slot_id) != 0:
            raise FailClosed("prepare 失败（isolation 不通过），不得进入 run")
    ev_pre = RUNS / slot["slot_id"]
    if not (ev_pre / "meta.prepare.json").is_file():
        raise FailClosed("prepare 未落 meta.prepare.json（R2：ws 不再承载 meta）: " + str(ev_pre))
    meta = json.loads((ev_pre / "meta.prepare.json").read_text(encoding="utf-8"))
    meta["preregistration_commit"] = binding["preregistration_commit"]
    meta["registered_at"] = binding["registered_at"]  # == E 提交时刻，< started_at 断言于收据
    prompt = (ws / "TASK.md").read_text(encoding="utf-8")
    key = load_api_key()
    env = dict(os.environ, CODEX_HOME=str(CODEX_HOME), DEEPSEEK_API_KEY=key, RUST_LOG="warn")
    cmd = [CODEX_BIN, "exec", "--json", "--skip-git-repo-check", "-C", str(ws), "-m", MODEL,
           "-c", 'model_reasoning_effort="%s"' % EFFORT, "-"]
    ev = RUNS / slot["slot_id"]
    ev.mkdir(parents=True, exist_ok=True)
    stream_files = {"stdout": ev / "_live_stdout.jsonl", "stderr": ev / "_live_stderr.txt"}
    started, t0 = now_iso(), time.time()
    status, exit_code, infra_type = "ok", None, None
    termination = None
    attempt_identity = {"n": 1, "started_at": started, "slot_id": slot["slot_id"]}
    with stream_files["stdout"].open("wb") as out, stream_files["stderr"].open("wb") as err:
        proc = subprocess.Popen(cmd, cwd=str(ws), env=env, stdin=subprocess.PIPE,
                                stdout=out, stderr=err, text=True,
                                start_new_session=True)  # 独立进程组：子即组长
        # dsh 契约升级：Popen 后立即 getpgid（此刻必可得，父尚未收割）；作为权威 pgid
        saved_pgid = os.getpgid(proc.pid)
        attempt_identity["pid"] = proc.pid
        attempt_identity["pgid"] = saved_pgid
        try:
            _, _ = proc.communicate(prompt, timeout=slot["timeout_s"])
            exit_code = proc.returncode
            if exit_code != 0:  # 无重试：whole-execution restarts=0
                err_text = stream_files["stderr"].read_text(encoding="utf-8", errors="replace")
                if TRANSPORT_RE.search(err_text):
                    status, infra_type = "transport-error", "transport"
                else:
                    status, infra_type = "error", "process"
        except subprocess.TimeoutExpired:
            termination = close_process_group(proc, ev, slot, phase="timeout",
                                              saved_pgid=saved_pgid, attempt=attempt_identity)
            status, exit_code, infra_type = "timeout", None, "timeout"
        else:
            # 正常退出同样检查组闭合（遗留后台工具风险探活/披露，不只 timeout 路径）
            termination = close_process_group(proc, ev, slot, phase="normal_exit", grace_s=3.0,
                                              saved_pgid=saved_pgid, attempt=attempt_identity)
    finished, dur = now_iso(), round(time.time() - t0, 1)
    # lead 阻断修复：任何 phase 停止未确认 → 早退 partial（score=null），checker 0 调用
    formal_eligible = bool(termination and termination.get("verified") is True)
    res = None
    if formal_eligible:
        res = judge(slot)  # 仅停止已组级确认后才在 workspace 运行冻结 checker
    session_capture = capture_session(ev, ws, started)
    if not formal_eligible:
        reported8 = None
        selection = None
        diagnostic = ("stop unconfirmed（phase=%s probe=%s delivery=%s）：R1 partial；"
                      "checker 0 调用；score=null；批根 halt 已写，后槽不得启动"
                      % (termination.get("phase"), termination.get("probe"),
                         termination.get("term_delivery")) if termination else "no termination receipt")
    else:
        reported8 = score8_reported(res)
        if status in ("ok", "timeout"):
            selection = {"plan_id": "l5-20261030", "slot_id": slot["slot_id"],
                         "order": slot["order"], "kind": "first", "parent_id": None,
                         "reason": None, "registered_at": binding["registered_at"],
                         "plan_source": 0, "plan_pointer": "/product_slots/%d" % (slot["order"] - 1)}
            diagnostic = None
        else:  # error / transport-error → R1 真值表：selection=null + 非空 diagnostic
            selection = None
            err_head = (stream_files["stderr"].read_text(encoding="utf-8", errors="replace")[-300:]
                        if stream_files["stderr"].exists() else "")
            diagnostic = ("status=%s exit=%s infra_type=%s; stderr_tail=%s"
                          % (status, exit_code, infra_type, err_head.replace("\n", " ")[:280]))
    if formal_eligible:
        res_reward = res.get("reward")
        res_weighted = reported8 if reported8 is not None else res.get("weighted")
        res_failed = [c.get("id") for c in res.get("checks", []) if c.get("pass") is False]
        capability_failure = (status == "ok" and res.get("reward") is None)
    else:
        res_reward = res_weighted = None
        res_failed = []
        capability_failure = None
    meta.update({
        "status": status, "exit_code": exit_code, "infra_type": infra_type,
        "timed_out": status == "timeout",
        "started_at": started, "finished_at": finished, "duration_s": dur,
        "attempts": [dict(attempt_identity, duration_s=dur, exit_code=exit_code, outcome=status)],
        "termination": termination,
        # dsh 契约 atk16：meta 绑定仅 {file,sha256}；权威 bool 只在 doc 原物
        "termination_receipt": ({"file": "termination.json",
                                 "sha256": sha_file(ev / "termination.json")}
                                if termination and (ev / "termination.json").exists() else None),
        "runner_formal_eligible": formal_eligible,
        "judge_role": ("partial_no_checker" if not formal_eligible else "formal_candidate"),
        "whole_execution_restarts": 0, "transport_retries": 0,
        "retry_note": "L4 §3B：whole-execution restart 上限 0；无 transport-retry 重启；"
                      "CLI 进程内部不可观察重试如存在则披露为不可观察",
        "execution_binding": {"design_commit": binding["design_commit"],
                              "execution_seal_commit": binding["execution_seal_commit"],
                              "execution_manifest_sha256": binding["execution_manifest_sha256"]},
        "selection": selection, "diagnostic": diagnostic,
        "usage": extract_usage(ev / "agent-session"),
        "weighted": res_weighted,
        "reward": res_reward,
        "failed": res_failed,
        "judge": (judge_block(slot, res) if formal_eligible else None),
        "capability_failure": capability_failure,
        "live_doc_drift": [],
    })
    meta["stdout_sha256"] = sha_file(stream_files["stdout"]) if stream_files["stdout"].exists() else None
    meta["stderr_sha256"] = sha_file(stream_files["stderr"]) if stream_files["stderr"].exists() else None
    meta["stdout_bytes"] = stream_files["stdout"].stat().st_size if stream_files["stdout"].exists() else 0
    meta["stderr_bytes"] = stream_files["stderr"].stat().st_size if stream_files["stderr"].exists() else 0
    _persist_master(ev, ws, stream_files, meta, prompt)
    integ = scan_integrity(ev)
    meta["integrity"] = integ
    meta["integrity_verdict"] = "clean" if integ["violations"] == 0 else "violation"
    if formal_eligible:
        write_once(ev / "checker.stdout", dump_obj(res))
        sr = score_receipt(slot, res, meta)
        write_once(ev / "score-receipt.json", dump_obj(sr))
        meta["l3_field_component"] = l3_field_component(meta, binding["registered_at"])
    # partial：无 checker.stdout/score-receipt/L3 组件（checker 0 调用，score=null）
    write_once(ev / "meta.json", dump_obj(meta))  # 唯一一次终写
    # 双归档反事实投影（offline_recompute；母本不动）——进程内调用，失败必须留完整诊断
    try:
        spec = importlib.util.spec_from_file_location(
            "l4dual", Path(__file__).resolve().parent / "dual_archive.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        da = mod.project_run(ev)
        da_status = {"ok": True, **da}
    except Exception as e:  # noqa: BLE001
        da_status = {"ok": False, "error": f"{type(e).__name__}: {e}",
                     "diagnostic": "dual-archive 失败不静默（lead 审查⑤）；母本未受影响"}
    write_once(ev / "dual-archive.status.json", dump_obj(da_status))
    if not formal_eligible:
        write_once(BATCH / "halt.json", dump_obj({
            "slot_id": slot_id, "at": now_iso(),
            "reason": "termination 未组级确认（probe=%s）：R1 partial，formal=false，"
                      "checker 0 调用；停后续槽待 lead 处置" % termination.get("probe")
                      if termination else "termination receipt 缺失"}))
        print(json.dumps({"alert": "停止未确认：partial 早退（checker 0 调用），已停后续槽并写批根 halt",
                          "slot_id": slot_id, "probe": termination.get("probe")}, ensure_ascii=False))
    print(json.dumps({"slot": slot_id, "status": status, "exit_code": exit_code,
                      "reward": res_reward, "weighted": res_weighted,
                      "duration_s": dur, "violations": integ["violations"],
                      "runner_formal_eligible": formal_eligible,
                      "evidence": str(ev)}, ensure_ascii=False))
    return 0 if formal_eligible else 4


def cmd_judge(slot_id: str) -> int:
    print(json.dumps(judge(slot_by_id(slot_id)), ensure_ascii=False)[:2000])
    return 0


def cmd_notexecuted(slot_id: str, reason: str, stop_source: str) -> int:
    slot = slot_by_id(slot_id)
    binding = load_binding(required=True)  # E/binding 缺席 → 禁止记账（builder-dsh 契约 E）
    ev = RUNS / slot["slot_id"]
    existing = [q.name for q in ev.iterdir()] if ev.exists() else []
    extra = [q for q in existing if q != "notexecuted.json"]
    if extra:
        raise FailClosed(f"notexecuted 目录含其他文件（虚造证据防线）：{extra}")
    rec = {"slot_id": slot["slot_id"], "run_id": slot["run_id"], "event_id": slot["event_id"],
           "preregistration_commit": binding["preregistration_commit"],
           "reason": reason, "stop_source": stop_source,
           "at": now_iso(), "live_doc_drift": []}
    write_once(ev / "notexecuted.json", dump_obj(rec))
    print(json.dumps({"notexecuted": slot_id}, ensure_ascii=False))
    return 0


def cmd_status() -> int:
    rows = []
    for s in load_plan_slots():
        ws, ev = ws_dir(s), RUNS / s["slot_id"]
        state = "prepared" if (ws / "TASK.md").exists() else "unprepared"
        if (ev / "meta.json").exists():
            m = json.loads((ev / "meta.json").read_text(encoding="utf-8"))
            state = m.get("status", "archived")
        rows.append({"slot": s["slot_id"], "state": state})
    print(json.dumps({"slots": rows}, ensure_ascii=False, indent=1))
    return 0


def cmd_selftest() -> int:
    """合成测试入口（零模型、零网络、不读凭据）；实现见 selftest.py。"""
    spec = importlib.util.spec_from_file_location("l4codex_selftest",
                                                  Path(__file__).with_name("selftest.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.main()


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("preflight").set_defaults(func=lambda a: cmd_preflight())
    sp = sub.add_parser("prepare"); sp.add_argument("slot")
    sp.set_defaults(func=lambda a: cmd_prepare(a.slot))
    sp = sub.add_parser("run"); sp.add_argument("slot")
    sp.set_defaults(func=lambda a: cmd_run(a.slot))
    sp = sub.add_parser("judge"); sp.add_argument("slot")
    sp.set_defaults(func=lambda a: cmd_judge(a.slot))
    sub.add_parser("status").set_defaults(func=lambda a: cmd_status())
    sub.add_parser("selftest").set_defaults(func=lambda a: cmd_selftest())
    sp = sub.add_parser("dual-archive"); sp.add_argument("slot")
    sp.set_defaults(func=lambda a: _dual_archive_entry(a.slot))
    sp = sub.add_parser("notexecuted"); sp.add_argument("slot")
    sp.add_argument("reason"); sp.add_argument("stop_source")
    sp.set_defaults(func=lambda a: cmd_notexecuted(a.slot, a.reason, a.stop_source))
    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except FailClosed as e:
        print(json.dumps({"fail_closed": True, "reason": str(e)}, ensure_ascii=False))
        return 3


def _dual_archive_entry(slot_id: str) -> int:
    spec = importlib.util.spec_from_file_location("l4dual", BATCH / "tools" / "dual_archive.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.main([slot_by_id(slot_id)])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
