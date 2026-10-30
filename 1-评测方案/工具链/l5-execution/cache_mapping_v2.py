#!/usr/bin/env python3
"""L5 cache 归一化映射 v2(R5,池 L5-5)+ 对 L4 18 probe raw 的只读一致性复算。

v2 语义变更(相对 L4 冻结 cache_probe.py 的 USAGE_FIELDS 预设):
- responses 线增加嵌套路径 input_tokens_details.cached_tokens(L4 erratum 已证的映射缺口);
- 映射条目改按 wire_key 为键(norm 附于条目内),多别名(如 chat 双别名)不再同键互覆;
- normalized 视图按 norm 聚合 state/value 列表,明确【不求和】;
- layer_raw_inventory 语义与 L4 相同(无偏全字段),不因映射变更丢失任何 raw 键。
零模型、零网络;L4 文件只读;输出仅写本修订档案目录。
"""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
L4_PROBES = ROOT / "3-表现现场/l4-20261029-cache/probes"
HERE = Path(__file__).resolve().parent
ERRATUM = ROOT / "5-评测报告/L4独立验收-2026-10-29/realdata-cache/offline-recompute-erratum.json"

USAGE_FIELDS_V2 = {
    "responses": [("input_tokens", "input_tokens"),
                  ("input_tokens_details.cached_tokens", "cache_read_tokens"),
                  ("cached_input_tokens", "cache_read_tokens_flat_legacy"),
                  ("cache_write_input_tokens", "cache_creation_tokens_flat_legacy"),
                  ("output_tokens", "output_tokens"), ("total_tokens", "total_tokens")],
    "anthropic-messages": [("input_tokens", "input_tokens"),
                           ("cache_read_input_tokens", "cache_read_tokens"),
                           ("cache_creation_input_tokens", "cache_creation_tokens"),
                           ("output_tokens", "output_tokens")],
    "chat-completions": [("prompt_tokens", "input_tokens"),
                         ("prompt_tokens_details.cached_tokens", "cache_read_tokens"),
                         ("prompt_cache_hit_tokens", "cache_read_tokens_hit_alias"),
                         ("prompt_cache_miss_tokens", "cache_miss_tokens"),
                         ("completion_tokens", "output_tokens"), ("total_tokens", "total_tokens")],
}


def _scalar_state(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "non-scalar"
    if isinstance(v, (int, float)):
        return "positive" if v > 0 else "zero"
    return "non-scalar"


def raw_field_inventory(raw_usage):
    inv = {}
    ru = raw_usage if isinstance(raw_usage, dict) else {}

    def walk(prefix, obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk("%s.%s" % (prefix, k) if prefix else k, v)
        else:
            inv[prefix] = {"state": _scalar_state(obj),
                           "value": None if obj is None else obj}
    walk("", ru)
    return inv


def usage_layers_v2(raw_usage, fields):
    ru = raw_usage if isinstance(raw_usage, dict) else {}
    mapping = {}
    for wire_key, norm in fields:
        cur = ru
        parts = wire_key.split(".")
        for part in parts[:-1]:
            if part not in cur:
                mapping[wire_key] = {"norm": norm, "state": "parent_missing"}
                break
            if not isinstance(cur[part], dict):
                mapping[wire_key] = {"norm": norm, "state": "parent_non_object",
                                     "value": cur[part]}
                break
            cur = cur[part]
        else:
            leaf = parts[-1]
            if leaf not in cur:
                mapping[wire_key] = {"norm": norm, "state": "child_missing"}
            else:
                st = _scalar_state(cur[leaf])
                e = {"norm": norm, "state": st}
                if st in ("positive", "non-scalar"):
                    e["value"] = cur[leaf]
                mapping[wire_key] = e
    normalized = {}
    for wire_key, e in mapping.items():
        normalized.setdefault(e["norm"], {"wire_keys": [], "states": [], "values": []})
        normalized[e["norm"]]["wire_keys"].append(wire_key)
        normalized[e["norm"]]["states"].append(e["state"])
        if "value" in e:
            normalized[e["norm"]]["values"].append(e["value"])
    for norm, agg in normalized.items():
        agg["distinct_values"] = sorted(set(agg["values"]))
        agg["note"] = "多别名不求和;distinct_values 仅列出不同取值"
    return {"layer_raw_inventory": raw_field_inventory(raw_usage),
            "layer_mapping_v2": mapping, "normalized": normalized}


def unit_selftest():
    checks = []
    m = usage_layers_v2({"a": {"b": 5}}, [("a.b", "x")])["layer_mapping_v2"]
    checks.append(("nested positive", m["a.b"] == {"norm": "x", "state": "positive", "value": 5}))
    m = usage_layers_v2({"a": {"b": 0}}, [("a.b", "x")])["layer_mapping_v2"]
    checks.append(("nested zero", m["a.b"]["state"] == "zero"))
    m = usage_layers_v2({}, [("a.b", "x")])["layer_mapping_v2"]
    checks.append(("parent_missing", m["a.b"]["state"] == "parent_missing"))
    m = usage_layers_v2({"a": 1}, [("a.b", "x")])["layer_mapping_v2"]
    checks.append(("parent_non_object", m["a.b"]["state"] == "parent_non_object"))
    m = usage_layers_v2({"a": {}}, [("a.b", "x")])["layer_mapping_v2"]
    checks.append(("child_missing", m["a.b"]["state"] == "child_missing"))
    lay = usage_layers_v2({"h": 2048, "d": {"c": 2048}},
                          [("d.c", "read"), ("h", "read_hit")])
    checks.append(("alias no-sum", lay["normalized"]["read"]["distinct_values"] == [2048]
                   and lay["normalized"]["read_hit"]["distinct_values"] == [2048]))
    return checks


def main():
    out = {"generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
           "zero_model_calls": True, "scope": str(L4_PROBES) + " 只读",
           "mapping_version": "cache-mapping-v2",
           "erratum_ref": "5-评测报告/L4独立验收-2026-10-29/realdata-cache/offline-recompute-erratum.json"}
    st = unit_selftest()
    out["unit_selftest"] = [{"case": n, "pass": bool(p)} for n, p in st]
    slots = sorted(p.name for p in L4_PROBES.iterdir() if p.is_dir())
    out["slot_count"] = len(slots)
    rows = {}
    for sid in slots:
        proto = sid.split("l4-20261029-cache-")[1].rsplit("-b", 1)[0]
        raw = json.loads((L4_PROBES / sid / "usage.raw.json").read_text(encoding="utf-8"))
        rows[sid] = usage_layers_v2(raw, USAGE_FIELDS_V2[proto])
    out["recompute"] = rows

    def mv(sid, wire):
        return rows[sid]["layer_mapping_v2"].get(wire, {})

    A = []
    for b in ("b1", "b2"):
        A.append(("responses %s repeat nested=2048" % b,
                  mv("l4-20261029-cache-responses-%s-repeat" % b,
                     "input_tokens_details.cached_tokens").get("state") == "positive"
                  and mv("l4-20261029-cache-responses-%s-repeat" % b,
                         "input_tokens_details.cached_tokens").get("value") == 2048))
        for cond in ("fresh", "nonce-control"):
            A.append(("responses %s %s nested=0" % (b, cond),
                      mv("l4-20261029-cache-responses-%s-%s" % (b, cond),
                         "input_tokens_details.cached_tokens").get("state") == "zero"))
        A.append(("responses %s flat legacy 键 raw/mapping 双缺" % b,
                  mv("l4-20261029-cache-responses-%s-repeat" % b,
                     "cached_input_tokens").get("state") in ("missing", "child_missing", "parent_missing")))
        A.append(("messages %s repeat read=2048" % b,
                  mv("l4-20261029-cache-anthropic-messages-%s-repeat" % b,
                     "cache_read_input_tokens").get("value") == 2048))
        for cond in ("fresh", "nonce-control", "repeat"):
            A.append(("messages %s %s creation 显式 0" % (b, cond),
                      mv("l4-20261029-cache-anthropic-messages-%s-%s" % (b, cond),
                         "cache_creation_input_tokens").get("state") == "zero"))
        hit = mv("l4-20261029-cache-chat-completions-%s-repeat" % b, "prompt_cache_hit_tokens")
        det = mv("l4-20261029-cache-chat-completions-%s-repeat" % b,
                 "prompt_tokens_details.cached_tokens")
        A.append(("chat %s 双别名一致 2048 且不求和" % b,
                  hit.get("value") == 2048 and det.get("value") == 2048
                  and rows["l4-20261029-cache-chat-completions-%s-repeat" % b]
                  ["normalized"]["cache_read_tokens"]["distinct_values"] == [2048]))
        for cond in ("fresh", "nonce-control"):
            A.append(("chat %s %s read=0" % (b, cond),
                      mv("l4-20261029-cache-chat-completions-%s-%s" % (b, cond),
                         "prompt_cache_hit_tokens").get("state") == "zero"))
    # 与 erratum 表 values_by_slot 逐值一致(responses 6 槽)
    err = json.loads(ERRATUM.read_text(encoding="utf-8"))
    for sid, want in err["erratum_2_responses_mapping_gap"]["values_by_slot"].items():
        got = mv(sid, "input_tokens_details.cached_tokens")
        got_v = got.get("value", 0) if got.get("state") in ("positive", "zero") else None
        A.append(("erratum 一致 %s=%s" % (sid.split("cache-")[1], want), got_v == want))
    out["assertions"] = [{"name": n, "pass": bool(p)} for n, p in A]
    out["all_pass"] = all(a["pass"] for a in out["assertions"]) and all(c["pass"] for c in out["unit_selftest"])
    dest = HERE / "cache-mapping-v2-recompute-receipt.json"
    out["receipt"] = dest.name
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"all_pass": out["all_pass"], "slots": len(slots),
                      "assertions": len(A), "receipt": str(dest.relative_to(ROOT))},
                     ensure_ascii=False))
    sys.exit(0 if out["all_pass"] else 1)


if __name__ == "__main__":
    main()
