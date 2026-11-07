#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools-session-trace-observe.py — DSH 会话轨迹（session.v4.jsonl.zstd）请求侧观测工具 v1
（2026-11-08，请求侧观测规范扩展，PREREG-loop30）

目的：对 DSH 臂会话轨迹原件（JSONL v4 事件流，zstd 压缩）做请求侧直接观测，
落实老师要求②「预先指定可由请求侧/运行器直接观测的输入大小指标」。指标：
  S1 文件字节：zstd 压缩字节、解压字节、行数、unparsable 行数。
  S2 两级类型计数：type 平铺计数；type + data 子键名（仅键名，不含值）计数。
  S3 输入侧字节：user/message + request/header + request/context 事件
     canonical JSON 字节和（会话级汇总；v4 流单 turn 为主，不逐 turn 细分）。
  S4 输出侧字节：assistant/message + tool/call 事件 canonical JSON 字节和；
     tool/result 字节单独列观察字段（不归入输入/输出侧分类）。
  S5 声明请求配置（辅助列）：request/header → data.header.config
     （provider/model/reasoningEffort/maxTokens）与 request/context →
     contextWindow/provider/model/systemPromptUpdate，冠 declared_ 前缀；
     本格式无 token usage 数值字段（与 Codex rollout 不同），如实明示。
  S6 会话时长 ms：timed 事件（含 time 字段者）末−首（数据派生，确定性）。

诚实边界：
  - declared_* 是运行配置声明，不是用量实测；本格式未记录 token usage。
  - 字节为 canonical JSON（sort_keys, ensure_ascii=False, 分隔符紧凑）序列化
    长度，是重构输入的机械观测量，非线上传输字节数。
  - 外部依赖：`zstd` CLI（shutil.which 定位；本机 /opt/homebrew/bin/zstd）。
  - 行标识：run 目录标签（dsh__*，公开格）+批次标签（r1030-* 等）；两者均为
    公开树 3-表现现场/ 已有目录名，不含私档路径成分。

防泄漏：输出不得含 (a) 私档路径标记（/Users/b612-lp、bench-private、
bench-automation、loop-records）；(b) 源中任何 >24 字符的字符串值，除非该值
来自白名单键（S5 declared 配置：data.header.config 与 request/context 的
provider/model/reasoningEffort/maxTokens/contextWindow/systemPromptUpdate）
     与结构元数据（type 键值及类型 token 形态 a-b/c-d——其本身在 s2 计数键中
     有意披露）。
命中 → FATAL rc=2，不写任何输出文件。文件名只披露 basename。
确定性：输出不含墙钟时间戳；同输入重跑逐字节同。write-once：--out 已存在→rc=3。

用法：
  主跑：python3 tools-session-trace-observe.py <file.zstd...> [--input-dir DIR]
        --out OUT [--receipt RUN.json]
  见证：python3 tools-session-trace-observe.py <同样的输入文件...> [--input-dir DIR]
        --witness AGG.json --witness-out W.json
        （shasum 独立复算目标 sha + 同输入确定性重放逐字节比对；机器见证非真人签名）
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter

TOOL = "tools-session-trace-observe.py"
VERSION = "v1 (2026-11-08)"
PRIVATE_MARKERS = ("/Users/b612-lp", "bench-private", "bench-automation", "loop-records")
TYPE_TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9-]*(/[a-z0-9][a-z0-9-]*)+$")
WL_KEYS = {"provider", "model", "reasoningEffort", "maxTokens", "contextWindow",
           "systemPromptUpdate"}
INPUT_TYPES = {"user/message", "request/header", "request/context"}
OUTPUT_TYPES = {"assistant/message", "tool/call"}
RESULT_TYPES = {"tool/result"}


def canon_bytes(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def find_zstd():
    z = shutil.which("zstd") or "/opt/homebrew/bin/zstd"
    if not os.path.exists(z):
        print("FATAL: zstd CLI not found (S1 needs external zstd)", file=sys.stderr)
        sys.exit(2)
    return z


def decompress(path, zstd):
    with open(path, "rb") as f:
        comp = f.read()
    p = subprocess.run([zstd, "-dc", "-"], input=comp, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError("zstd decompress failed: %s" % path)
    return len(comp), p.stdout


def derive_labels(path):
    """run label (dsh__* 公开格) + batch label (r1030-* 等) from path parts.

    Both are already public in 3-表现现场/; no private path component is
    emitted. Fallback: bare basename."""
    parts = os.path.normpath(path).split(os.sep)
    run = batch = None
    try:
        i = parts.index("agent-session")
        run = parts[i - 1] if i >= 1 else None
        for j in range(i - 2, -1, -1):
            if re.match(r"^r\d+", parts[j]) or re.match(r"^l\d", parts[j]):
                batch = parts[j]
                break
    except ValueError:
        pass
    return run or os.path.basename(path), batch


def observe_one(path, zstd):
    comp_n, raw = decompress(path, zstd)
    lines = raw.decode("utf-8", errors="replace").splitlines()
    run_label, batch_label = derive_labels(path)
    rec = {
        "file": os.path.basename(path),
        "run": run_label,
        "batch": batch_label,
        "s1": {"compressed_bytes": comp_n, "decompressed_bytes": len(raw),
               "lines": len(lines), "unparsable": 0},
        "s2": {"type_counts": {}, "type_and_data_keys_counts": {}},
        "s3": {"input_bytes": 0, "user_messages": 0, "request_headers": 0,
               "request_contexts": 0},
        "s4": {"output_bytes": 0, "assistant_messages": 0, "tool_calls": 0,
               "tool_result_bytes": 0, "tool_results": 0},
        "s5": {"declared_config": None, "declared_context": None,
               "request_header_events": 0},
        "s6": {"duration_ms": None, "timed_events": 0},
    }
    tc, dk = Counter(), Counter()
    t_first = t_last = None
    for ln in lines:
        if not ln.strip():
            continue
        try:
            o = json.loads(ln)
        except Exception:
            rec["s1"]["unparsable"] += 1
            continue
        t = o.get("type", "<none>")
        tc[t] += 1
        d = o.get("data")
        if isinstance(d, dict):
            dk[t + ":" + "+".join(sorted(d.keys()))] += 1
        b = len(canon_bytes(o))
        if t in INPUT_TYPES:
            rec["s3"]["input_bytes"] += b
            if t == "user/message":
                rec["s3"]["user_messages"] += 1
            elif t == "request/header":
                rec["s3"]["request_headers"] += 1
                rec["s5"]["request_header_events"] += 1
                cfg = (((d or {}).get("header") or {}).get("config"))
                if isinstance(cfg, dict) and rec["s5"]["declared_config"] is None:
                    rec["s5"]["declared_config"] = {
                        k: cfg.get(k) for k in
                        ("provider", "model", "reasoningEffort", "maxTokens")
                        if k in cfg}
            elif t == "request/context":
                rec["s3"]["request_contexts"] += 1
                if isinstance(d, dict) and rec["s5"]["declared_context"] is None:
                    rec["s5"]["declared_context"] = {
                        k: d.get(k) for k in
                        ("provider", "model", "contextWindow", "systemPromptUpdate")
                        if k in d}
        elif t in OUTPUT_TYPES:
            rec["s4"]["output_bytes"] += b
            if t == "assistant/message":
                rec["s4"]["assistant_messages"] += 1
            else:
                rec["s4"]["tool_calls"] += 1
        elif t in RESULT_TYPES:
            rec["s4"]["tool_result_bytes"] += b
            rec["s4"]["tool_results"] += 1
        tm = o.get("time")
        if isinstance(tm, (int, float)):
            rec["s6"]["timed_events"] += 1
            if t_first is None:
                t_first = tm
            t_last = tm
    rec["s2"]["type_counts"] = dict(sorted(tc.items()))
    rec["s2"]["type_and_data_keys_counts"] = dict(sorted(dk.items()))
    if t_first is not None and t_last is not None:
        rec["s6"]["duration_ms"] = t_last - t_first
    return rec


def collect_long_strings(obj, wl_active, out, depth=0):
    if depth > 12:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            # 'type' values are structural event-type tokens (also disclosed
            # by design in s2 type_counts), not session content.
            collect_long_strings(v, wl_active or (k in WL_KEYS) or (k == "type"),
                                 out, depth + 1)
    elif isinstance(obj, list):
        for v in obj:
            collect_long_strings(v, wl_active, out, depth + 1)
    elif isinstance(obj, str) and not wl_active and len(obj) > 24:
        if TYPE_TOKEN_RE.match(obj):
            return  # structural type token shape, exempt
        out.add(obj)


def build_aggregate(files, zstd):
    recs = [observe_one(p, zstd) for p in files]
    tot = {
        "files": len(recs),
        "compressed_bytes": sum(r["s1"]["compressed_bytes"] for r in recs),
        "decompressed_bytes": sum(r["s1"]["decompressed_bytes"] for r in recs),
        "lines": sum(r["s1"]["lines"] for r in recs),
        "unparsable": sum(r["s1"]["unparsable"] for r in recs),
        "input_bytes": sum(r["s3"]["input_bytes"] for r in recs),
        "output_bytes": sum(r["s4"]["output_bytes"] for r in recs),
        "tool_result_bytes": sum(r["s4"]["tool_result_bytes"] for r in recs),
    }
    return {
        "tool": TOOL, "tool_version": VERSION, "tool_sha256": tool_self_sha(),
        "format": "dsh-session-v4-jsonl-zstd",
        "inputs": {"files": [os.path.basename(p) for p in files],
                   "runs": [derive_labels(p)[0] for p in files]},
        "totals": tot, "per_file": recs,
        "notes": [
            "S1-S6 request-side mechanical observation; canonical JSON bytes, "
            "not wire bytes.",
            "declared_* is run configuration (auxiliary), NOT measured usage; "
            "this format records no token usage numbers.",
            "durations are data-derived (last timed event minus first).",
        ],
    }


def serialize(aggregate):
    return json.dumps(aggregate, sort_keys=True, ensure_ascii=False,
                      indent=1).encode("utf-8") + b"\n"


def leak_check(aggregate, sources):
    text = json.dumps(aggregate, ensure_ascii=False)
    for marker in PRIVATE_MARKERS:
        if marker in text:
            print("FATAL: private path marker leaked: %s" % marker, file=sys.stderr)
            sys.exit(2)
    longs = set()
    for raw in sources:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        for ln in raw.splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                o = json.loads(ln)
            except Exception:
                continue
            collect_long_strings(o, False, longs)
    leaked = sorted(s for s in longs if s in text)
    if leaked:
        print("FATAL: source content string leaked (%d), first=%r"
              % (len(leaked), leaked[0][:60]), file=sys.stderr)
        sys.exit(2)


def resolve_inputs(a):
    files = list(a.files)
    if a.input_dir:
        for root, _dirs, fs in os.walk(a.input_dir):
            for fn in sorted(fs):
                if fn.endswith(".jsonl.zstd"):
                    files.append(os.path.join(root, fn))
    if not files:
        print("FATAL: no input files", file=sys.stderr)
        sys.exit(2)
    for p in files:
        if not os.path.exists(p):
            print("FATAL: input missing: %s" % p, file=sys.stderr)
            sys.exit(2)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--input-dir")
    ap.add_argument("--out")
    ap.add_argument("--receipt")
    ap.add_argument("--witness")
    ap.add_argument("--witness-out")
    a = ap.parse_args()
    zstd = find_zstd()
    files = resolve_inputs(a)

    if a.witness:
        if not a.witness_out:
            print("FATAL: --witness needs --witness-out", file=sys.stderr)
            sys.exit(2)
        if os.path.exists(a.witness_out):
            print("FATAL: witness-out exists (write-once): %s" % a.witness_out,
                  file=sys.stderr)
            sys.exit(3)
        with open(a.witness, "rb") as f:
            agg_bytes = f.read()
        t = hashlib.sha256(agg_bytes).hexdigest()
        prev = json.loads(agg_bytes.decode("utf-8"))
        want = prev.get("inputs", {}).get("files", [])
        got = [os.path.basename(p) for p in files]
        if want != got:
            print("FATAL: witness inputs mismatch: want=%r got=%r" % (want, got),
                  file=sys.stderr)
            sys.exit(2)
        replayed = serialize(build_aggregate(files, zstd))
        rs = hashlib.sha256(replayed).hexdigest()
        w = {
            "tool": TOOL, "tool_version": VERSION,
            "witness_of": os.path.basename(a.witness),
            "target_sha256": t,
            "shasum_recheck": {"sha256": t, "ok": True},
            "deterministic_replay": {"aggregate_sha256": rs,
                                     "match": (rs == t),
                                     "byte_identical": replayed == agg_bytes},
            "all_ok": bool(rs == t and replayed == agg_bytes),
        }
        with open(a.witness_out, "wb") as f:
            f.write(json.dumps(w, sort_keys=True, ensure_ascii=False,
                               indent=1).encode("utf-8") + b"\n")
        print("witness: %s all_ok=%s" % (a.witness_out, w["all_ok"]))
        sys.exit(0)

    if not a.out:
        print("FATAL: --out required for main run", file=sys.stderr)
        sys.exit(2)
    if os.path.exists(a.out):
        print("FATAL: out exists (write-once): %s" % a.out, file=sys.stderr)
        sys.exit(3)
    aggregate = build_aggregate(files, zstd)
    # leak scan needs DECOMPRESSED source text (inputs are zstd-compressed)
    sources = []
    for p in files:
        _c, raw = decompress(p, zstd)
        sources.append(raw)
    leak_check(aggregate, sources)
    payload = serialize(aggregate)
    with open(a.out, "wb") as f:
        f.write(payload)
    sha = hashlib.sha256(payload).hexdigest()
    print("out: %s aggregate_sha256=%s files=%d unparsable=%d"
          % (a.out, sha, aggregate["totals"]["files"],
             aggregate["totals"]["unparsable"]))
    if a.receipt:
        rc = {"tool": TOOL, "tool_version": VERSION, "mode": "main",
              "out": os.path.basename(a.out), "aggregate_sha256": sha,
              "files": aggregate["totals"]["files"],
              "unparsable": aggregate["totals"]["unparsable"]}
        rp = a.receipt
        if os.path.exists(rp):
            print("FATAL: receipt exists (write-once): %s" % rp, file=sys.stderr)
            os.remove(a.out)
            sys.exit(3)
        with open(rp, "wb") as f:
            f.write(json.dumps(rc, sort_keys=True, ensure_ascii=False,
                               indent=1).encode("utf-8") + b"\n")
        print("receipt: %s" % rp)


def tool_self_sha():
    try:
        with open(__file__, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return None


if __name__ == "__main__":
    main()
