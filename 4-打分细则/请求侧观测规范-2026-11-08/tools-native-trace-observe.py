#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools-native-trace-observe.py — 原生轨迹请求侧观测（WorkBuddy span 面 / 豆包会话轨迹面）

loop32（2026-11-08，窗口 until14-20261108）。老师要求②：预先指定请求侧可观测输入大小
指标+自报值仅辅助——在 W（WorkBuddy 原生 trace）与豆包办公（会话 trajectory）两臂落地。
历史原件已于评测私档归档（loop-records/3-表现现场/r20261108-native-trace-archive/），
本工具只对归档目录聚合；公开聚合件零内容字段、零本机路径。

指标：
  WB（T 系列） T1 文件数/字节/行数；T2 事件类型计数(trace_start/span_start/span_end/trace_end)；
              T3 span 类型计数(generation/agent/其他, start/end 分列)；
              T4 请求侧近似=generation+agent span toolInput 字节和（span 工具面近似，非网关 HTTP 请求体）；
              T5 输出侧=toolOutput 字节和；T6 self_reported_ 前缀（trace.totalTokens 终值聚合
              +带 usage 字段 span 计数，auxiliary）；T7 会话时长(ms, trace duration 或 startedAt→endedAt)。
  豆包（D 系列）D1 文件数/字节/行数；D2 role 计数；D3 tool_calls 参数 JSON 字节和（轨迹面近似）；
              D4 tool 结果 content 字节和（输出侧）；D5 usage 字段计数（预期 0=absent 如实输出）；
              D6 会话时长(首末时间戳差 ms；无时间戳则 null=absent)。

纪律：防泄漏断言（聚合输出含 >24 字符源内容串或本机绝对路径→FATAL rc=2 不写出）；
write-once（--out 已存在 rc=3）；确定性（无墙钟时间戳，同输入逐字节同输出）；
--witness 见证=shasum 独立复算归档件 sha256+同输入确定性重放逐字节对比
（机器见证，非真人签名）。

用法（在公开仓根或任意目录运行）：
  python3 tools-native-trace-observe.py --kind workbuddy --archive <WB归档目录> \
      --out <pilot.json> [--receipt <run.json>] [--label <标签>]
  python3 tools-native-trace-observe.py --kind workbuddy --archive <WB归档目录> \
      --witness <pilot.json> --witness-out <w.json>
退出码：0 成功；2 防泄漏断言失败；3 write-once 冲突；1 其他错误。
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

META_KEYS = {"tool", "tool_sha256", "kind", "label", "witness_kind", "receipt",
             "schema", "aggregate_version", "metrics_kind", "limits", "note"}
PATH_RE = re.compile(r"(/Users/|/home/|/tmp/|~/|\b[A-Za-z]:\\)")

def eprint(*a):
    print(*a, file=sys.stderr)

def self_sha():
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in ("tools-native-trace-observe.py",):
        p = os.path.join(here, cand)
        if os.path.exists(p):
            return hashlib.sha256(open(p, "rb").read()).hexdigest()
    return None

def iter_files(root):
    out = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in sorted(filenames):
            if not fn.endswith(".jsonl"):
                continue
            out.append(os.path.join(dirpath, fn))
    return sorted(out)

def rel_label(root, path):
    return os.path.relpath(path, root).replace(os.sep, "/")

def _bytes(s):
    if s is None:
        return 0
    if isinstance(s, (dict, list)):
        s = json.dumps(s, ensure_ascii=False, sort_keys=True)
    return len(str(s).encode("utf-8"))

def _ts_ms(a, b):
    if not a or not b:
        return None
    try:
        from datetime import datetime
        fa = datetime.fromisoformat(a.replace("Z", "+00:00"))
        fb = datetime.fromisoformat(b.replace("Z", "+00:00"))
        return int((fb - fa).total_seconds() * 1000)
    except Exception:
        return None

def aggregate_workbuddy(root):
    files = iter_files(root)
    t1_files = 0; t1_bytes = 0; t1_lines = 0
    t2 = {"trace_start": 0, "span_start": 0, "span_end": 0, "trace_end": 0, "unparsable_lines": 0}
    span_start_types = {}; span_end_types = {}
    t4_request_side_bytes = 0; t4_spans = 0
    t5_output_side_bytes = 0; t5_spans = 0
    total_tokens_final = 0; traces_with_tokens = 0
    spans_with_usage = 0
    durations = []
    unparsable_files = 0
    for path in files:
        t1_files += 1
        started = ended = None; duration = None; tokens_start = None; tokens_end = None
        try:
            raw = open(path, "rb").read()
        except OSError:
            unparsable_files += 1
            continue
        t1_bytes += len(raw)
        for line in raw.splitlines():
            if not line.strip():
                continue
            t1_lines += 1
            try:
                d = json.loads(line.decode("utf-8"))
            except Exception:
                t2["unparsable_lines"] += 1
                continue
            typ = d.get("type")
            if typ in t2:
                t2[typ] += 1
            if typ == "trace_start":
                tr = d.get("trace") or {}
                started = tr.get("startedAt"); tokens_start = tr.get("totalTokens")
            elif typ == "trace_end":
                tr = d.get("trace") or {}
                ended = tr.get("endedAt"); duration = tr.get("duration")
                tokens_end = tr.get("totalTokens")
            elif typ == "span_start":
                sp = d.get("span") or {}
                name = str(sp.get("type") or "unknown")
                span_start_types[name] = span_start_types.get(name, 0) + 1
            elif typ == "span_end":
                sp = d.get("span") or {}
                name = str(sp.get("type") or "unknown")
                span_end_types[name] = span_end_types.get(name, 0) + 1
                if name in ("generation", "agent"):
                    ti = sp.get("toolInput")
                    if ti is not None:
                        t4_request_side_bytes += _bytes(ti); t4_spans += 1
                    to = sp.get("toolOutput")
                    if to is not None:
                        t5_output_side_bytes += _bytes(to); t5_spans += 1
                if "usage" in sp:
                    spans_with_usage += 1
        final_tokens = tokens_end if tokens_end is not None else tokens_start
        if final_tokens:
            total_tokens_final += int(final_tokens); traces_with_tokens += 1
        if duration is None:
            duration = _ts_ms(started, ended)
        if duration is not None:
            durations.append(int(duration))
    metrics = {
        "t1": {"files": t1_files, "bytes": t1_bytes, "lines": t1_lines, "unparsable_files": unparsable_files},
        "t2_event_types": t2,
        "t3_span_types": {"start": span_start_types, "end": span_end_types},
        "t4_request_side_tool_input": {"bytes": t4_request_side_bytes, "spans": t4_spans,
                                       "note": "generation/agent span toolInput 字节和；span 工具面近似，非网关 HTTP 请求体"},
        "t5_output_side_tool_output": {"bytes": t5_output_side_bytes, "spans": t5_spans},
        "t6_self_reported": {"total_tokens_sum": total_tokens_final, "traces_with_total_tokens": traces_with_tokens,
                             "spans_with_usage": spans_with_usage, "note": "应用自报值，auxiliary"},
        "t7_duration_ms": {"sum": sum(durations), "traces": len(durations)},
    }
    return metrics

def _usage_count(obj):
    n = 0
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "usage":
                n += 1
            n += _usage_count(v)
    elif isinstance(obj, list):
        for v in obj:
            n += _usage_count(v)
    return n

def aggregate_doubao(root):
    files = iter_files(root)
    d1_files = 0; d1_bytes = 0; d1_lines = 0
    roles = {}
    d3_args_bytes = 0; d3_calls = 0
    d4_content_bytes = 0; d4_results = 0
    usage_fields = 0
    first_ts = last_ts = None
    unparsable_files = 0
    for path in files:
        d1_files += 1
        try:
            raw = open(path, "rb").read()
        except OSError:
            unparsable_files += 1
            continue
        d1_bytes += len(raw)
        for line in raw.splitlines():
            if not line.strip():
                continue
            d1_lines += 1
            try:
                d = json.loads(line.decode("utf-8"))
            except Exception:
                roles["<unparsable>"] = roles.get("<unparsable>", 0) + 1
                continue
            role = str(d.get("role") or "<none>")
            roles[role] = roles.get(role, 0) + 1
            usage_fields += _usage_count(d)
            ts = d.get("timestamp") or d.get("time") or d.get("created_at")
            if isinstance(ts, str) and ts:
                if first_ts is None:
                    first_ts = ts
                last_ts = ts
            if role == "assistant":
                for call in (d.get("tool_calls") or []):
                    fn = call.get("function") or {}
                    args = fn.get("arguments")
                    if args is not None:
                        d3_args_bytes += _bytes(args); d3_calls += 1
            elif role == "tool":
                content = d.get("content")
                if content is not None:
                    d4_content_bytes += _bytes(content); d4_results += 1
    metrics = {
        "d1": {"files": d1_files, "bytes": d1_bytes, "lines": d1_lines, "unparsable_files": unparsable_files},
        "d2_roles": roles,
        "d3_request_side_tool_args": {"bytes": d3_args_bytes, "calls": d3_calls,
                                      "note": "assistant tool_calls.function.arguments 规范 JSON 字节和；会话轨迹面近似"},
        "d4_output_side_tool_results": {"bytes": d4_content_bytes, "results": d4_results},
        "d5_usage_fields": {"count": usage_fields, "note": "轨迹未见 token usage 字段则如实为 0（absent），不虚构"},
        "d6_duration_ms": {"first_timestamp": None if first_ts is None else "<absent-or-redacted>",
                           "duration_available": bool(first_ts and last_ts)},
    }
    return metrics

def _walk_strings(obj, out):
    if isinstance(obj, str):
        if len(obj) > 24:
            out.append(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and len(k) > 24:
                out.append(k)
            _walk_strings(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk_strings(v, out)

def collect_candidates(root):
    """泄漏断言候选：逐行 JSON 解析后收集所有 >24 字符的字符串键/值（每文件上限 16 个）；非 JSON 行整行入候选。
    豁免：文件 basename/去扩展名/相对路径标识（run 标识按纪律允许出现在 inputs.files）。"""
    excludes = set()
    for path in iter_files(root):
        base = os.path.basename(path)
        excludes.add(base); excludes.add(base[:-6] if base.endswith(".jsonl") else base)
        excludes.add(rel_label(root, path))
    cands = []
    for path in iter_files(root):
        n = 0
        try:
            fh = open(path, "r", encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in fh:
            if n >= 16:
                break
            s = line.strip()
            if not s:
                continue
            try:
                d = json.loads(s)
            except Exception:
                if len(s) > 24:
                    cands.append(s[:200]); n += 1
                continue
            vals = []
            _walk_strings(d, vals)
            for v in vals:
                if n >= 16:
                    break
                if any(v == e or v in e for e in excludes):
                    continue
                cands.append(v[:200]); n += 1
        fh.close()
    return cands

def leak_check(text, candidates):
    hits = [c for c in candidates if c in text]
    if hits:
        eprint("FATAL: private path leaked" if PATH_RE.search(text) else "FATAL: source content leaked")
        eprint("leak hits: %d (lengths %s)" % (len(hits), sorted({len(h) for h in hits})))
        return False
    if PATH_RE.search(text):
        eprint("FATAL: private path leaked")
        return False
    return True

def canonical(agg):
    return json.dumps(agg, ensure_ascii=False, sort_keys=True, indent=1) + "\n"

def build_aggregate(args, archive_root):
    kind = args.kind
    metrics = aggregate_workbuddy(archive_root) if kind == "workbuddy" else aggregate_doubao(archive_root)
    files = []
    for path in iter_files(archive_root):
        b = open(path, "rb").read()
        files.append({"path": rel_label(archive_root, path), "bytes": len(b),
                      "sha256": hashlib.sha256(b).hexdigest()})
    limits = [
        "原生轨迹观测面=应用 span/会话轨迹，非网关 HTTP 请求体；与 Codex rollout/DSH 会话轨迹口径不同，不做跨轨字节等值比较",
        "usage/totalTokens 为应用自报值（auxiliary）；豆包轨迹未见 usage 字段则如实 absent",
        "聚合件零内容字段、零本机路径；原件存评测私档归档，公开件可由归档原件复算",
    ]
    agg = {
        "schema": "native-trace-observe-v1",
        "tool": "tools-native-trace-observe.py",
        "tool_sha256": self_sha(),
        "kind": kind,
        "label": args.label or "",
        "inputs": {"archive_file_count": len(files), "files": files},
        "metrics": metrics,
        "limits": limits,
    }
    return agg

def write_receipt(path, payload):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, sort_keys=True, indent=1)
        fh.write("\n")

def main(argv=None):
    ap = argparse.ArgumentParser(description="原生轨迹请求侧观测（WB/豆包）")
    ap.add_argument("--kind", choices=("workbuddy", "doubao"))
    ap.add_argument("--archive", help="归档目录（只读）")
    ap.add_argument("--out", help="聚合输出 JSON（write-once）")
    ap.add_argument("--receipt", help="运行收据（私档，可选）")
    ap.add_argument("--label", default="")
    ap.add_argument("--witness", help="见证目标 pilot.json")
    ap.add_argument("--witness-out", help="见证输出 JSON")
    args = ap.parse_args(argv)

    receipt = {"tool": "tools-native-trace-observe.py", "tool_sha256": self_sha()}

    if args.witness:
        if not (args.kind and args.archive and args.witness_out):
            eprint("witness mode requires --kind/--archive/--witness-out")
            return 1
        try:
            pilot_text = open(args.witness, "r", encoding="utf-8").read()
        except OSError as exc:
            eprint("cannot read witness target: %s" % exc)
            return 1
        files = iter_files(args.archive)
        shasum_ok = True
        files_checked = 0
        for path in files:
            try:
                out = subprocess.run(["shasum", "-a", "256", path], capture_output=True, text=True)
                got = out.stdout.split()[0] if out.returncode == 0 else None
            except OSError:
                got = None
            want = hashlib.sha256(open(path, "rb").read()).hexdigest()
            if got != want:
                shasum_ok = False
            files_checked += 1
        pilot = json.loads(pilot_text)
        listed = {f["path"]: f for f in pilot.get("inputs", {}).get("files", [])}
        list_match = set(listed) == {rel_label(args.archive, p) for p in files}
        if not args.label:
            args.label = pilot.get("label", "") or ""
        agg = build_aggregate(args, args.archive)
        replay = canonical(agg)
        replay_identical = (replay == pilot_text)
        wit = {
            "witness_kind": "native-trace-observe",
            "target": os.path.basename(args.witness),
            "target_sha256": hashlib.sha256(pilot_text.encode("utf-8")).hexdigest(),
            "files_checked": files_checked,
            "shasum_match": shasum_ok,
            "file_list_match": list_match,
            "deterministic_replay": replay_identical,
            "all_ok": bool(shasum_ok and list_match and replay_identical),
            "tool": "tools-native-trace-observe.py",
            "tool_sha256": self_sha(),
            "note": "机器见证（shasum 独立实现复算+同输入确定性重放），非真人签名",
        }
        if os.path.exists(args.witness_out):
            eprint("write-once conflict: %s exists" % args.witness_out)
            return 3
        text = canonical(wit)
        with open(args.witness_out, "w", encoding="utf-8") as fh:
            fh.write(text)
        receipt.update({"mode": "witness", "witness_out": args.witness_out, "all_ok": wit["all_ok"],
                        "target": args.witness})
        if args.receipt:
            write_receipt(args.receipt, receipt)
        print("witness all_ok=%s files=%d replay_identical=%s" % (wit["all_ok"], files_checked, replay_identical))
        return 0

    if not (args.kind and args.archive and args.out):
        eprint("main mode requires --kind/--archive/--out")
        return 1
    if os.path.exists(args.out):
        eprint("write-once conflict: %s exists" % args.out)
        return 3
    agg = build_aggregate(args, args.archive)
    text = canonical(agg)
    if not leak_check(text, collect_candidates(args.archive)):
        return 2
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(text)
    receipt.update({"mode": "aggregate", "kind": args.kind, "archive_file_count": len(agg["inputs"]["files"]),
                    "out": args.out, "out_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()})
    if args.receipt:
        write_receipt(args.receipt, receipt)
    print("aggregate written kind=%s files=%d bytes=%d" % (
        args.kind, len(agg["inputs"]["files"]), agg["metrics"]["t1" if args.kind == "workbuddy" else "d1"]["bytes"]))
    return 0

if __name__ == "__main__":
    sys.exit(main())
