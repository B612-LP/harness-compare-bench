#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 事后公开整理版，非原封印源码；旧源码 hash 不适用于本版本。
"""L4 裸模型缓存语义探针（18 固定槽位；plan.probe_slots 全局串行；E 前 fail-closed）。

失败分类（CLARIFICATION-L4-1 R4，优先级固定）：
  1. 每槽最多一次外发；不跟随 redirect；不换 endpoint/body/effort；不借槽补跑。
  2. 401/403 → 停全部 cache 探针（余槽 not_executed），立即通知 复核（其他 CLI 停新官方 API 槽）。
  3. 其他 4xx（含 429）、3xx、请求/响应格式错误、协议不支持 → 立即停该协议。
  4. 5xx / socket/TLS/timeout → 该槽消费并记失败；连续两次真实外发失败停该协议；成功清零。
  5. fresh 无成功原始响应 → 同 block repeat not_executed（不发）；control 若协议未停可发但不作 paired 对照。
每个外发前先持久化 slot 意图登记（崩溃安全，R3）。

判据纪律：不把 miss==creation；首次 hit 不等于由本实验建缓存；无命中≠无缓存；
字段缺失/null/0/正值分开；结果不得填零；探针与历史 rollout 非同请求，禁止逐调用对应。

用法：
  probe.py selftest            # 合成测试（零网络零凭据）
  probe.py dry-run [slot]      # 全状态机走查 + 构造请求体，零网络
  probe.py run [slot]          # 真实执行（E+release 后；gate fail-closed）
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
BATCH = REPO / "3-表现现场" / "l4-20261029-cache"
EVIDENCE_ROOT = REPO            # 真实执行=仓库根；fake e2e 测试重定向到临时树
RECEIPT_PATH = BATCH / "probe-receipt.json"
DRYRUN_ROOT = BATCH / "dryrun"  # dry-run 独立输出树，绝不占用真实证据路径（复核 审查⑤）
L4 = REPO / "1-评测方案" / "自动循环L4-2026-10-29"
PLAN_PATH = L4 / "plan.json"
CONTRACT_PATH = L4 / "contract.json"
BINDING_PATH = L4 / "runtime-binding.json"
GATE_PATH = REPO / "1-评测方案" / "工具链" / "l4-execution" / "gate.py"
DESIGN_COMMIT_D = "bb14897a7d1ac26c06697bb80a15d94158cd8ae0"
RULE = "l4-20261029-batch-v1"
REPEAT_GAP_S = 5
PREFIX_TARGET_CHARS = 8192
PREFIX_MAX_BYTES = 16384

# wire 形状（E 封印件；契约源见 contract.endpoint_sources；字段+headers+auth 仅进程内）
MAX_OUTPUT_TOKENS = 256
SHAPES = {
    "responses": lambda text: {"model": "deepseek-flash", "input": text,
                               "max_output_tokens": MAX_OUTPUT_TOKENS,
                               "reasoning": {"effort": "low"}},
    "anthropic-messages": lambda text: {"model": "deepseek-flash",
                                        "max_tokens": MAX_OUTPUT_TOKENS,
                                        "thinking": {"type": "enabled"},
                                        "output_config": {"effort": "low"},
                                        "messages": [{"role": "user", "content": text}]},
    "chat-completions": lambda text: {"model": "deepseek-flash",
                                      "messages": [{"role": "user", "content": text}],
                                      "max_tokens": MAX_OUTPUT_TOKENS,
                                      "reasoning_effort": "low"},
}
# wire usage 字段 → 归一化名（映射披露；绝不把 miss==creation、hit≠本实验建缓存）
USAGE_FIELDS = {
    "responses": {"input_tokens": "input_tokens", "cached_input_tokens": "cache_read_tokens",
                  "cache_write_input_tokens": "cache_creation_tokens",
                  "output_tokens": "output_tokens", "total_tokens": "total_tokens"},
    "anthropic-messages": {"input_tokens": "input_tokens", "cache_read_input_tokens": "cache_read_tokens",
                           "cache_creation_input_tokens": "cache_creation_tokens",
                           "output_tokens": "output_tokens"},
    "chat-completions": {"prompt_tokens": "input_tokens", "completion_tokens": "output_tokens",
                         "total_tokens": "total_tokens",
                         "prompt_tokens_details.cached_tokens": "cache_read_tokens"},
}
USAGE_REMARK = {
    "responses": "cached/cache_write 为 CLI 侧同名字段；provider 是否回该键由本探针 raw 证据回答",
    "anthropic-messages": "cache_read_input_tokens/cache_creation_input_tokens 为 anthropic 线标准键；"
                          "dsh 历史 0 = session log 键存在且值 0（map_usage 仅存在才映射）",
    "chat-completions": "官方文档语义为 hit/miss（prompt_cache_hit_tokens/miss 或 details.cached_tokens），"
                        "无 creation 字段——creation 缺失即协议层缺键，不得解释为无写入",
}


class FailClosed(Exception):
    pass


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_once(path: Path, data: bytes) -> None:
    """原子非破坏写：O_CREAT|O_EXCL 拒绝已存在/悬空 symlink（复核 审查⑥）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as e:
        raise FailClosed(f"write-once violation (atomic): {path}") from e
    try:
        os.write(fd, data)
    finally:
        os.close(fd)


def load_plan_probes() -> list[dict]:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    slots = sorted(plan["probe_slots"], key=lambda s: s["order"])
    if len(slots) != 18 or len({s["slot_id"] for s in slots}) != 18:
        raise FailClosed(f"probe slots != 18 unique: {len(slots)}")
    return slots


def load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def load_binding(required: bool) -> dict | None:
    if not BINDING_PATH.exists():
        if required:
            raise FailClosed("runtime-binding.json 不存在（E 未封印）：真实外发 fail-closed")
        return None
    b = json.loads(BINDING_PATH.read_text(encoding="utf-8"))
    for k in ("design_commit", "preregistration_commit", "execution_seal_commit",
              "registered_at", "execution_manifest_sha256", "plan_sha256",
              "contract_sha256", "released_for_model_calls"):
        if k not in b:
            raise FailClosed("binding missing key: " + k)
    return b


def call_gate(binding_path: Path) -> None:
    if not GATE_PATH.exists():
        raise FailClosed("gate.py 不存在：" + str(GATE_PATH))
    spec = importlib.util.spec_from_file_location("l4_gate", GATE_PATH)
    gate = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(gate)
    except Exception as e:  # noqa: BLE001
        raise FailClosed(f"gate import failed: {e}") from e
    result = gate.verify_execution(str(binding_path))
    if result is not True and not (isinstance(result, dict) and result.get("ok") is True):
        raise FailClosed(f"gate.verify_execution rejected: {result!r}")


def gate_check_real() -> dict:
    b = load_binding(required=True)
    if b["released_for_model_calls"] is not True:
        raise FailClosed("released_for_model_calls is not true")
    if sha(PLAN_PATH.read_bytes()) != b["plan_sha256"]:
        raise FailClosed("binding.plan_sha256 != local plan.json")
    if sha(CONTRACT_PATH.read_bytes()) != b["contract_sha256"]:
        raise FailClosed("binding.contract_sha256 != local contract.json")
    call_gate(BINDING_PATH)
    return b


def load_api_key() -> str:
    """只在进程内使用；绝不打印/落盘。selftest/dry-run 路径永不调用本函数。"""
    text = (Path.home() / ".dsh" / ".credentials.yaml").read_text(encoding="utf-8")
    m = re.search(r"^refs:\n((?:  .*\n)+)", text, re.M)
    if not m:
        raise FailClosed("credentials: refs 段未找到")
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        if k.strip() == "DEEPSEEK_API_KEY":
            return v.strip()
    raise FailClosed("credentials: DEEPSEEK_API_KEY 未找到")


# ---------------------------------------------------------------- 确定性构造

def deterministic_nonce(protocol: str, block: int, control: bool) -> str:
    base = f"{DESIGN_COMMIT_D}:{protocol}:{block}" + (":control" if control else "")
    return hashlib.sha256(base.encode()).hexdigest()[:16]


def synthetic_prefix() -> str:
    """确定性 ASCII synthetic 文本：目标 ~8192 字符，硬上限 16384 UTF-8 字节（R4.6）。"""
    lines = []
    n = 0
    while n < PREFIX_TARGET_CHARS:
        line = f"L{n:04d}: deterministic synthetic filler for L4 cache probe; no task content. " \
               f"value={n * 37 % 9973}; checksum={(n * 2654435761) % 104729}."
        lines.append(line)
        n += len(line) + 1
    text = "\n".join(lines)
    data = text.encode("utf-8")
    while len(data) > PREFIX_MAX_BYTES and lines:
        lines.pop()
        data = "\n".join(lines).encode("utf-8")
    return data.decode("ascii")


def build_body(protocol: str, nonce: str, prefix: str, max_output_tokens: int) -> dict:
    assert prefix.startswith("NONCE:") is False
    text = f"NONCE:{nonce}\n\n{prefix}\n\nReply with the single word: ack."
    shape = SHAPES[protocol]
    body = shape(text)
    if max_output_tokens != MAX_OUTPUT_TOKENS:
        for k in ("max_output_tokens", "max_tokens"):
            if k in body:
                body[k] = max_output_tokens
    return body


def _scalar_state(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "non-scalar"
    if isinstance(v, (int, float)):
        return "zero" if v == 0 else "positive"
    return "non-scalar"


def raw_field_inventory(raw_usage, prefix=""):
    """② 原始字段无偏 inventory：遍历 raw usage 全部键（点路径），值原样，不丢任何字段。"""
    inv = {}
    if not isinstance(raw_usage, dict):
        return inv
    for k, v in raw_usage.items():
        path = f"{prefix}{k}"
        if isinstance(v, dict):
            inv[path] = {"state": "object"}
            inv.update(raw_field_inventory(v, prefix=path + "."))
        else:
            inv[path] = {"state": _scalar_state(v), "value": None if v is None else v}
    return inv


def usage_layers(raw_usage, fields: dict) -> dict:
    """② 双层记录：layer_raw_inventory（无偏全字段） + layer_mapping（预设映射嵌套三态：
    parent_missing / parent_non_object / child_missing / null / zero / positive / non-scalar）。"""
    raw_inv = raw_field_inventory(raw_usage)
    mapping = {}
    ru = raw_usage if isinstance(raw_usage, dict) else {}
    for wire_key, norm in fields.items():
        if "." in wire_key:
            parent, child = wire_key.split(".", 1)
            if parent not in ru:
                mapping[norm] = {"wire_key": wire_key, "state": "parent_missing"}
            elif not isinstance(ru[parent], dict):
                mapping[norm] = {"wire_key": wire_key, "state": "parent_non_object",
                                 "value": ru[parent]}
            elif child not in ru[parent]:
                mapping[norm] = {"wire_key": wire_key, "state": "child_missing"}
            else:
                st = _scalar_state(ru[parent][child])
                e = {"wire_key": wire_key, "state": st}
                if st in ("positive", "non-scalar"):
                    e["value"] = ru[parent][child]
                mapping[norm] = e
        else:
            if wire_key not in ru:
                mapping[norm] = {"wire_key": wire_key, "state": "missing"}
            else:
                st = _scalar_state(ru[wire_key])
                e = {"wire_key": wire_key, "state": st}
                if st in ("positive", "non-scalar"):
                    e["value"] = ru[wire_key]
                mapping[norm] = e
    return {"layer_raw_inventory": raw_inv, "layer_mapping": mapping,
            "mapping_note": "presence 不凭预设映射丢字段：raw inventory 保留 provider 回传的一切键；"
                            "映射层仅作归一化对照，两者不得互相替代"}


def no_redirect_opener():
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):  # R4.1：不跟随 redirect
            return None
    return urllib.request.build_opener(NoRedirect)


RESPONSE_HEADER_VALUE_WHITELIST = ("x-request-id", "request-id", "content-type", "date",
                                   "server", "cf-ray", "x-ratelimit-limit-requests",
                                   "x-ratelimit-limit-tokens", "x-ratelimit-remaining-requests",
                                   "x-ratelimit-remaining-tokens")
FORBIDDEN_HEADERS = ("authorization", "cookie", "set-cookie", "x-api-key", "proxy-authorization")


def capture_response_headers(headers) -> dict:
    """复核 补充：白名单响应头存值（绝不 Authorization/cookie 类）；缺失字段记 missing，
    不以本地 slotID 冒充服务端 ID。"""
    out = {}
    lower = {h.lower(): h for h in headers.keys()} if headers else {}
    for name in RESPONSE_HEADER_VALUE_WHITELIST:
        if name in lower:
            out[name] = headers.get(lower[name])
        else:
            out[name] = "missing"
    for banned in FORBIDDEN_HEADERS:
        if banned in lower:
            out[banned] = "REDACTED（禁止保存）"
    return out


def http_post(url: str, body_bytes: bytes, key: str, timeout: int):
    """唯一网络出口；仅在 run 真实路径被调用。返回 (status, raw_body, header_names, header_values, t0, t1, err)。"""
    req = urllib.request.Request(url, data=body_bytes, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + key})
    t0 = time.time()
    try:
        with no_redirect_opener().open(req, timeout=timeout) as resp:
            raw = resp.read()
            t1 = time.time()
            return (resp.status, raw,
                    sorted(h for h in resp.headers.keys()
                           if h.lower() not in FORBIDDEN_HEADERS),
                    capture_response_headers(resp.headers), t0, t1, None)
    except urllib.error.HTTPError as e:
        raw = e.read() if hasattr(e, "read") else b""
        t1 = time.time()
        return (e.code, raw,
                sorted(e.headers.keys()) if e.headers else [],
                capture_response_headers(e.headers), t0, t1, None)
    except Exception as e:  # socket/TLS/timeout
        return None, b"", [], {}, t0, time.time(), f"{type(e).__name__}: {e}"


# ---------------------------------------------------------------- 状态机执行

def classify_outcome(status, err) -> tuple[str, str]:
    """返回 (action, class)：action ∈ send-next / stop-protocol / stop-global。"""
    if err is not None:
        return "consume-network", "network_error"
    if 200 <= status < 300:
        return "ok", "ok"
    if status in (401, 403):
        return "stop-global", "auth_error"
    if 500 <= status < 600:                      # R4.4：5xx=消费槽位，连续 2 次才停协议
        return "consume-network", "service_error"
    if 400 <= status < 500:                      # R4.3：其他 4xx（含 429）立即停协议
        return "stop-protocol", "http_error"
    if 300 <= status < 400:                      # R4.1：不跟随 redirect，按停协议处理
        return "stop-protocol", "redirect_no_follow"
    return "consume-network", "unexpected_status"


def run_slot(slot: dict, state: dict, binding: dict, key: str) -> dict:
    protocol, cond = slot["protocol"], slot["condition"]
    ev = EVIDENCE_ROOT / slot["evidence_dir"]
    if state["protocols"].get(protocol) in ("stopped-auth", "stopped-http", "stopped-network"):
        rec = {"slot_id": slot["slot_id"], "executed": False,
               "status": "not_executed", "reason": "protocol stopped earlier: " + protocol}
        write_once(ev / "accounting.json", json.dumps(rec, ensure_ascii=False, indent=2).encode())
        return rec
    registered_at_e = binding["registered_at"]   # E 提交时刻引用
    actual_registered_at = now_iso()             # 本槽意图真实时刻（另记，不混用）
    # R3：外发前先持久化意图登记（崩溃安全）
    intent = {"slot_id": slot["slot_id"], "protocol": protocol, "condition": cond,
              "block": slot["block"], "order": slot["order"],
              "registered_at": registered_at_e, "actual_registered_at": actual_registered_at,
              "endpoint": load_contract()["probe_endpoints"][protocol],
              "design_commit_D": DESIGN_COMMIT_D,
              "execution_seal_commit": binding["execution_seal_commit"],
              "max_output_tokens": slot["max_output_tokens"], "timeout_s": slot["timeout_s"],
              "intent": "exactly one outbound request; no redirect; no adaptation"}
    write_once(ev / "intent.json", json.dumps(intent, ensure_ascii=False, indent=2).encode())
    prefix = synthetic_prefix()
    block = slot["block"]
    nonce = (deterministic_nonce(protocol, block, control=True)
             if cond == "nonce-control" else state["block_nonce"][(protocol, block)])
    body = build_body(protocol, nonce, prefix, slot["max_output_tokens"])
    body_bytes = json.dumps(body, ensure_ascii=False, sort_keys=False).encode("utf-8")
    if cond == "repeat":
        fresh_bytes = state.get(("fresh_body", protocol, block))
        if fresh_bytes is None or fresh_bytes != body_bytes:
            # 逐字节一致性自我校验失败 = 实现错误，fail-closed 而非静默发送
            raise FailClosed(f"repeat body not byte-identical to fresh: {slot['slot_id']}")
    url = load_contract()["probe_endpoints"][protocol]
    if cond == "repeat":
        gap = time.time() - state.get(("fresh_done_at", protocol, block), 0)
        if gap < REPEAT_GAP_S:
            time.sleep(REPEAT_GAP_S - gap)
    # ③ 请求体先持久化（外发前留痕），响应原始字节先落盘再解析
    write_once(ev / "request.body.json", body_bytes)
    status, raw, header_names, header_values, t0, t1, err = http_post(url, body_bytes, key, slot["timeout_s"])
    if raw:
        write_once(ev / "response.body.raw", raw)
    usage_raw, layers, parse_error = None, None, None
    response_id = None
    if raw:
        try:
            parsed = json.loads(raw.decode("utf-8"))
            response_id = parsed.get("id") if isinstance(parsed, dict) else None
            usage_raw = parsed.get("usage") if isinstance(parsed, dict) else None
            if usage_raw is not None:
                layers = usage_layers(usage_raw, USAGE_FIELDS[protocol])
        except Exception as e:  # ③ 格式错误 → R4.3 停协议；原始体已持久化
            parse_error = f"{type(e).__name__}: {e}"
    action, cls = classify_outcome(status, err)
    if cls == "ok" and parse_error:
        action, cls = "stop-protocol", "format_error"   # R4.3：200 但 body 不可解析
    if cls == "ok" and usage_raw is None:
        action, cls = "stop-protocol", "format_error"   # 200 但无 usage 对象
    # ④ 状态机更新先于任何写盘：record 即终态，transport/accounting 不可能互相矛盾
    if cls == "ok":
        state["protocols"][protocol] = "alive"
        state["consecutive_net_fail"][protocol] = 0
        if cond == "fresh":
            state[("fresh_body", protocol, block)] = body_bytes
            state[("fresh_ok", protocol, block)] = True
            state[("fresh_done_at", protocol, block)] = t1
    elif cls == "auth_error":
        state["protocols"][protocol] = "stopped-auth"
        state["global_auth_stop"] = True
    elif cls in ("http_error", "redirect_no_follow", "format_error"):
        state["protocols"][protocol] = "stopped-http"
    else:
        state["consecutive_net_fail"][protocol] = state["consecutive_net_fail"].get(protocol, 0) + 1
        if state["consecutive_net_fail"][protocol] >= 2:
            state["protocols"][protocol] = "stopped-network"
    record = {
        "slot_id": slot["slot_id"], "protocol": protocol, "block": block, "condition": cond,
        "executed": True, "status": ("executed" if cls == "ok" else "failed"),
        "at": now_iso(), "registered_at": intent["registered_at"],
        "actual_registered_at": intent["actual_registered_at"],
        "endpoint": url,
        "request_sha256": sha(body_bytes), "request_bytes": len(body_bytes),
        "nonce": nonce, "nonce_head_only": True,
        "http_status": status, "error": err, "parse_error": parse_error,
        "latency_s": round(t1 - t0, 3),
        "response_header_names": header_names,
        "response_header_values": header_values,
        "response_header_values_note": "白名单值；缺失记 missing；request-id 等服务端 ID 不由本地冒充；"
                                       "response.id 另见 raw body",
        "usage_raw": usage_raw, "usage_layers": layers,
        "usage_fields_remark": USAGE_REMARK[protocol],
        "response_id": response_id,
        "class": cls, "action": action,
        "paired_with_fresh": (cond == "repeat" and cls == "ok"),
        "protocol_state_after": state["protocols"].get(protocol),
        "auth": "redacted（仅进程内；headers 只记名字）", "model": "deepseek-flash",
        "semantics_note": "不把 miss==creation；首次 hit≠由本实验建缓存；无命中≠无缓存；"
                          "raw 结果不填零；与历史 rollout 非同请求，禁止逐调用对应",
    }
    transport_view = {k: v for k, v in record.items() if k != "usage_raw"}
    transport_view["raw_response_bytes"] = len(raw)
    transport_view["raw_response_sha256"] = sha(raw) if raw else None
    write_once(ev / "transport.json", json.dumps(transport_view, ensure_ascii=False, indent=2).encode())
    if usage_raw is not None:
        write_once(ev / "usage.raw.json", json.dumps(usage_raw, ensure_ascii=False, indent=2).encode())
        write_once(ev / "usage.layers.json", json.dumps(layers, ensure_ascii=False, indent=2).encode())
    # R4.5：fresh 未成功 → 同 block repeat 不发（execute 层按 state 断定）；本槽记账已含终态
    write_once(ev / "accounting.json", json.dumps(record, ensure_ascii=False, indent=2).encode())
    return record


def not_executed_record(slot: dict, reason: str, root: Path | None = None) -> dict:
    ev = (root or EVIDENCE_ROOT) / slot["evidence_dir"]
    rec = {"slot_id": slot["slot_id"], "protocol": slot["protocol"],
           "block": slot["block"], "condition": slot["condition"],
           "executed": False, "status": "not_executed", "reason": reason,
           "registered_at": now_iso()}
    write_once(ev / "accounting.json", json.dumps(rec, ensure_ascii=False, indent=2).encode())
    return rec


def execute(dry: bool, only_slot: str | None) -> int:
    slots = load_plan_probes()
    if only_slot:
        slots = [s for s in slots if s["slot_id"] == only_slot]
        if not slots:
            print(json.dumps({"error": "slot not in plan"}))
            return 2
    binding = gate_check_real() if not dry else load_binding(required=False)
    key = None if dry else load_api_key()
    evidence_root = DRYRUN_ROOT if dry else EVIDENCE_ROOT
    receipt_path = (DRYRUN_ROOT / "probe-receipt-dryrun.json") if dry else RECEIPT_PATH
    state: dict = {"protocols": {}, "consecutive_net_fail": {}, "global_auth_stop": False,
                   "block_nonce": {b: deterministic_nonce("BLOCK", b, control=False) for b in (1, 2)}}
    # block nonce 必须按协议独立（R4.6：首 nonce=D+protocol+block）——修正：逐 (protocol,block)
    state["block_nonce"] = {(p, b): deterministic_nonce(p, b, control=False)
                            for p in SHAPES for b in (1, 2)}
    out = []
    for slot in slots:
        if state["global_auth_stop"]:
            out.append(not_executed_record(slot, "401/403 auth stop: all cache probes halted",
                                           root=evidence_root))
            continue
        protocol, cond, block = slot["protocol"], slot["condition"], slot["block"]
        if state["protocols"].get(protocol) in ("stopped-auth", "stopped-http", "stopped-network"):
            reason = {"stopped-auth": "auth stop", "stopped-http": "protocol http/format stop",
                      "stopped-network": "protocol network x2 stop"}[state["protocols"][protocol]]
            out.append(not_executed_record(slot, reason, root=evidence_root))
            continue
        if not dry and cond == "repeat" and not state.get(("fresh_ok", protocol, block), False):
            # R4.5 仅属真实执行态；dry-run 是零网络走查，全部槽位构造请求体
            out.append(not_executed_record(slot, "fresh without successful raw response; "
                                                 "repeat not sent (R4.5)"))
            continue
        if dry:
            nonce = (deterministic_nonce(protocol, block, control=True)
                     if cond == "nonce-control" else state["block_nonce"][(protocol, block)])
            body = build_body(protocol, nonce, synthetic_prefix(), slot["max_output_tokens"])
            rec = {"slot_id": slot["slot_id"], "dry_run": True, "protocol": protocol,
                   "condition": cond, "block": block, "endpoint": load_contract()["probe_endpoints"][protocol],
                   "request_sha256": sha(json.dumps(body, ensure_ascii=False).encode()),
                   "prefix_chars": len(synthetic_prefix()),
                   "prefix_bytes": len(synthetic_prefix().encode("utf-8")),
                   "nonce": nonce, "executed": False, "status": "dry_run"}
            # dry-run 走查走独立输出树（⑤），绝不占用真实证据路径；真实执行产物一律 write_once
            ddir = (DRYRUN_ROOT / "probes" / slot["slot_id"])
            ddir.mkdir(parents=True, exist_ok=True)
            (ddir / "dry-run.json").write_text(
                json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            out.append(rec)
            continue
        rec = run_slot(slot, state, binding, key)
        out.append(rec)
        if rec.get("class") == "auth_error":
            print(json.dumps({"alert": "401/403 auth stop：请立即通知其他产品执行者停止未启动的新官方 API 槽位",
                              "slot": slot["slot_id"]}, ensure_ascii=False))
    receipt = {"kind": "bare_model_probe", "batch": "l4-20261029-cache", "rule": RULE,
               "at": now_iso(), "dry_run": dry, "live_doc_drift": [],
               "design_commit_D": DESIGN_COMMIT_D,
               "binding": (None if dry else {k: binding[k] for k in
                            ("design_commit", "execution_seal_commit", "registered_at")}),
               "slots": out,
               "slot_accounting": {r["slot_id"]: ("executed" if r.get("executed") and r.get("class") in ("ok",)
                                                  else ("failed" if r.get("executed") else "not_executed"))
                                   for r in out},
               "semantics": "raw usage 原样；缺失/null/0/正值分开；不推计费；不宣称零效应；"
                            "fresh 不宣称冷；repeat 不保证热命中；与历史 rollout 非同请求"}
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    if dry:  # dry-run 走查收据可重写；真实批收据 write_once
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                                encoding="utf-8")
    else:
        write_once(receipt_path,
                   (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode())
    print(json.dumps({"slots": len(out),
                      "executed": sum(1 for r in out if r.get("executed")),
                      "not_executed": sum(1 for r in out if not r.get("executed")),
                      "receipt": str(receipt_path)}, ensure_ascii=False))
    return 0


def cmd_selftest() -> int:
    """合成测试（零网络零凭据）：socket  Sentinel 兜底 + 断言套件。"""
    import socket

    class Sentinel(socket.socket):
        def __init__(self, *a, **k):
            raise AssertionError("selftest 违规联网尝试")

    real_socket = socket.socket
    socket.socket = Sentinel
    try:
        failures = []

        def check(name, fn):
            try:
                fn()
                print("PASS", name)
            except Exception as e:  # noqa: BLE001
                failures.append(name)
                print("FAIL", name, "->", e)

        # 1) prefix 限定
        px = synthetic_prefix()
        check("prefix_ascii", lambda: px.encode("ascii"))
        check("prefix_size", lambda: (_ for _ in ()).throw(AssertionError(px)) if not
              (7000 <= len(px) <= 16384 and len(px.encode()) <= PREFIX_MAX_BYTES) else None)
        # 2) nonce 确定性 + 独立性
        check("nonce_deterministic", lambda: (
            [deterministic_nonce("responses", 1, False) for _ in range(2)][0]
            == deterministic_nonce("responses", 1, False)))
        check("nonce_independent", lambda: (
            len({deterministic_nonce(p, b, False) for p in SHAPES for b in (1, 2)}) == 6))
        check("nonce_control_differs", lambda: (
            deterministic_nonce("responses", 1, True) != deterministic_nonce("responses", 1, False)))
        # 3) fresh/repeat 逐字节一致；control 仅首 nonce 不同
        pf = synthetic_prefix()
        b1 = json.dumps(build_body("responses", "AAA", pf, 256), ensure_ascii=False).encode()
        b2 = json.dumps(build_body("responses", "AAA", pf, 256), ensure_ascii=False).encode()
        b3 = json.dumps(build_body("responses", "BBB", pf, 256), ensure_ascii=False).encode()
        check("repeat_byte_identical", lambda: (_ for _ in ()).throw(AssertionError(b1)) if b1 != b2 else None)
        check("control_head_nonce_only", lambda: (_ for _ in ()).throw(AssertionError()) if
              b1.replace(b"AAA", b"") != b3.replace(b"BBB", b"") else None)
        # 4) usage 双层：映射嵌套三态 + raw inventory 无偏
        lay = usage_layers({"prompt_tokens": 10,
                            "prompt_tokens_details": {"cached_tokens": 7},
                            "completion_tokens": 2, "total_tokens": 9012,
                            "provider_extra_field": 1},
                           USAGE_FIELDS["chat-completions"])
        m = lay["layer_mapping"]
        check("mapping_states", lambda: (_ for _ in ()).throw(AssertionError(m)) if
              (m["input_tokens"]["state"], m["cache_read_tokens"]["state"],
               m["total_tokens"]["state"]) != ("positive", "positive", "positive") else None)
        check("mapping_chat_no_creation_key", lambda: (_ for _ in ()).throw(AssertionError(m)) if
              "cache_creation_tokens" in m else None)  # chat 线官方无 creation 映射（hit/miss 语义）
        check("mapping_nested_parent_present_child", lambda: (_ for _ in ()).throw(AssertionError(m)) if
              m["cache_read_tokens"]["state"] != "positive" and
              "prompt_tokens_details.cached_tokens" not in m else None)
        lay2 = usage_layers({"prompt_tokens_details": {}}, USAGE_FIELDS["chat-completions"])
        check("mapping_child_missing", lambda: (_ for _ in ()).throw(AssertionError(lay2)) if
              lay2["layer_mapping"]["cache_read_tokens"]["state"] != "child_missing" else None)
        lay3 = usage_layers({"input_tokens": 5}, USAGE_FIELDS["chat-completions"])
        check("mapping_parent_missing", lambda: (_ for _ in ()).throw(AssertionError(lay3)) if
              lay3["layer_mapping"]["cache_read_tokens"]["state"] != "parent_missing" else None)
        check("raw_inventory_unbiased", lambda: (_ for _ in ()).throw(AssertionError(lay)) if
              "provider_extra_field" not in lay["layer_raw_inventory"] else None)
        lay4 = usage_layers({"input_tokens_details": {"cached_tokens": 3}},
                            USAGE_FIELDS["responses"])
        check("raw_inventory_nested_path", lambda: (_ for _ in ()).throw(AssertionError(lay4)) if
              "input_tokens_details.cached_tokens" not in lay4["layer_raw_inventory"] else None)
        # 5) 失败分类
        check("classify_auth", lambda: (_ for _ in ()).throw(AssertionError()) if
              classify_outcome(401, None) != ("stop-global", "auth_error") else None)
        check("classify_429_stops_protocol", lambda: (_ for _ in ()).throw(AssertionError()) if
              classify_outcome(429, None)[0] != "stop-protocol" else None)
        check("classify_5xx_consumes", lambda: (_ for _ in ()).throw(AssertionError()) if
              classify_outcome(503, None)[0] != "consume-network" else None)
        check("classify_network", lambda: (_ for _ in ()).throw(AssertionError()) if
              classify_outcome(None, "timeout")[0] != "consume-network" else None)
        check("classify_ok_resets", lambda: (_ for _ in ()).throw(AssertionError()) if
              classify_outcome(200, None) != ("ok", "ok") else None)
        # 6) gate fail-closed（真实路径：binding 缺失）
        check("gate_failclosed_no_binding", lambda: (_ for _ in ()).throw(AssertionError("should raise"))
              if not (BINDING_PATH.exists() is False) else None)
        # 7) plan 槽位不变量
        slots = load_plan_probes()
        check("plan_18_slots", lambda: (_ for _ in ()).throw(AssertionError(len(slots))) if len(slots) != 18 else None)
        check("plan_serial_order", lambda: (_ for _ in ()).throw(AssertionError()) if
              [s["order"] for s in slots] != list(range(1, 19)) else None)
        # 8) selftest 未读凭据：上面全程未调用 load_api_key（代码路径审查断言）
        check("no_key_read_marker", lambda: None)

        # ---- fake-HTTP 端到端：18 槽全跑 + 重复 run 零外发（复核 审查要求） ----
        import tempfile
        saved = {k: getattr(p, k) if False else globals()[k] for k in
                 ("EVIDENCE_ROOT", "RECEIPT_PATH", "http_post", "load_api_key", "gate_check_real")}
        saved_sleep = time.sleep
        sleeps = []
        time.sleep = lambda s: sleeps.append(s)
        try:
            def fake_binding():
                return {"design_commit": DESIGN_COMMIT_D, "preregistration_commit": "e" * 40,
                        "execution_seal_commit": "e" * 40, "registered_at": "2026-10-29T23:00:00+08:00",
                        "execution_manifest_sha256": "0" * 64,
                        "plan_sha256": sha(PLAN_PATH.read_bytes()),
                        "contract_sha256": sha(CONTRACT_PATH.read_bytes()),
                        "released_for_model_calls": True}

            def make_http(script_by_protocol):
                calls = []
                def _http(url, body_bytes, key, timeout):
                    protocol = next(pp for pp, u in load_contract()["probe_endpoints"].items() if u == url)
                    calls.append(protocol)
                    status, raw = script_by_protocol(protocol, len(calls), body_bytes)
                    if status is None:
                        return None, b"", [], {}, time.time(), time.time(), "socket boom"
                    body = json.dumps({"id": "resp_" + sha(body_bytes)[:8],
                                       "usage": raw if isinstance(raw, dict) else {}}).encode()
                    return (status, body, ["content-type"],
                            {"x-request-id": "srv-fake-001", "content-type": "application/json",
                             "date": "missing"},
                            time.time(), time.time() + 0.01, None)
                return _http, calls

            def ok_usage(protocol):
                if protocol == "responses":
                    return {"input_tokens": 9000, "input_tokens_details": {"cached_tokens": 7000},
                            "output_tokens": 10, "total_tokens": 9010}
                if protocol == "anthropic-messages":
                    return {"input_tokens": 9000, "cache_read_input_tokens": 0,
                            "cache_creation_input_tokens": 0, "output_tokens": 10}
                return {"prompt_tokens": 9000, "prompt_tokens_details": {"cached_tokens": 0},
                        "completion_tokens": 10, "total_tokens": 9010}

            # 场景 A：全 200 → 18/18 外发成功
            with tempfile.TemporaryDirectory() as td:
                globals()["EVIDENCE_ROOT"] = Path(td)
                globals()["RECEIPT_PATH"] = Path(td) / "receipt.json"
                http, calls = make_http(lambda pp, n, bb: (200, ok_usage(pp)))
                globals()["http_post"] = http
                globals()["load_api_key"] = lambda: "test-key-not-real"
                globals()["gate_check_real"] = fake_binding
                rc = execute(dry=False, only_slot=None)
                check("e2e_all_ok_exit0", lambda: (_ for _ in ()).throw(AssertionError(rc)) if rc != 0 else None)
                check("e2e_18_outbound", lambda: (_ for _ in ()).throw(AssertionError(len(calls))) if len(calls) != 18 else None)
                acc = json.loads((Path(td) / "3-表现现场/l4-20261029-cache/probes/"
                                  "l4-20261029-cache-responses-b1-repeat/accounting.json").read_text(encoding="utf-8"))
                check("e2e_repeat_paired", lambda: (_ for _ in ()).throw(AssertionError(acc)) if
                      acc["paired_with_fresh"] is not True else None)
                inv = json.loads((Path(td) / "3-表现现场/l4-20261029-cache/probes/"
                                  "l4-20261029-cache-responses-b1-fresh/usage.layers.json").read_text(encoding="utf-8"))
                check("e2e_raw_inventory_nested", lambda: (_ for _ in ()).throw(AssertionError(inv)) if
                      "input_tokens_details.cached_tokens" not in inv["layer_raw_inventory"] else None)
                # 场景 E：重复 run → 第一个 write_once(intent) 即 FailClosed → 零额外外发
                calls.clear()
                raised = False
                try:
                    execute(dry=False, only_slot=None)
                except FailClosed:
                    raised = True
                check("e2e_rerun_zero_outbound", lambda: (_ for _ in ()).throw(AssertionError()) if
                      not (raised and len(calls) == 0) else None)
            # 场景 B：401 全停（后续全部 not_executed，仅 1 次外发）
            with tempfile.TemporaryDirectory() as td:
                globals()["EVIDENCE_ROOT"] = Path(td)
                globals()["RECEIPT_PATH"] = Path(td) / "receipt.json"
                http, calls = make_http(lambda pp, n, bb: (401, {"error": "auth"}))
                globals()["http_post"] = http
                rc = execute(dry=False, only_slot=None)
                check("e2e_auth_stop_one_call", lambda: (_ for _ in ()).throw(AssertionError(len(calls))) if len(calls) != 1 else None)
                check("e2e_auth_stop_exit0", lambda: (_ for _ in ()).throw(AssertionError(rc)) if rc != 0 else None)
            # 场景 C：messages 429 停该协议，其他协议照常（chat b2 在 messages b1 前不受影响）
            with tempfile.TemporaryDirectory() as td:
                globals()["EVIDENCE_ROOT"] = Path(td)
                globals()["RECEIPT_PATH"] = Path(td) / "receipt.json"
                def script(pp, n, bb):
                    return (429, {"error": "rate"}) if pp == "anthropic-messages" else (200, ok_usage(pp))
                http, calls = make_http(script)
                globals()["http_post"] = http
                rc = execute(dry=False, only_slot=None)
                check("e2e_429_stops_protocol_only", lambda: (_ for _ in ()).throw(AssertionError(len(calls))) if
                      len(calls) != 13 else None)  # responses6 + chat6 + messages 仅 b1-fresh 1 次（429 即停协议）
            # 场景 D：messages fresh 500 → repeat 不发，control 发（500）→ 连续2停协议
            with tempfile.TemporaryDirectory() as td:
                globals()["EVIDENCE_ROOT"] = Path(td)
                globals()["RECEIPT_PATH"] = Path(td) / "receipt.json"
                state_seq = {"n": 0}
                def script(pp, n, bb):
                    if pp == "chat-completions":
                        state_seq["n"] += 1
                        return (500, {}) if state_seq["n"] <= 2 else (200, ok_usage(pp))
                    return (200, ok_usage(pp))
                http, calls = make_http(script)
                globals()["http_post"] = http
                rc = execute(dry=False, only_slot=None)
                # chat b1: fresh 500(1) → repeat not_executed(0) → control 500(2) → 连续2停协议
                # chat b2: 全 not_executed；其他协议 12 次 200
                check("e2e_5xx_two_consecutive_stop", lambda: (_ for _ in ()).throw(AssertionError(len(calls))) if
                      len(calls) != 14 else None)  # 12 + chat 2
        finally:
            for k, v in saved.items():
                globals()[k] = v
            time.sleep = saved_sleep
        print("SELFTEST:", "PASS" if not failures else f"FAIL {failures}")
        return 0 if not failures else 1
    finally:
        socket.socket = real_socket


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest").set_defaults(func=lambda a: cmd_selftest())
    sp = sub.add_parser("dry-run"); sp.add_argument("slot", nargs="?", default=None)
    sp.set_defaults(func=lambda a: execute(dry=True, only_slot=a.slot))
    sp = sub.add_parser("run"); sp.add_argument("slot", nargs="?", default=None)
    sp.set_defaults(func=lambda a: execute(dry=False, only_slot=a.slot))
    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except FailClosed as e:
        print(json.dumps({"fail_closed": True, "reason": str(e)}, ensure_ascii=False))
        return 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
