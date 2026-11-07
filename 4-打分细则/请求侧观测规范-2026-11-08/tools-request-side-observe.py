#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools-request-side-observe.py v1 (2026-11-08)

请求侧用量观测工具（老师要求②：预先指定可由请求侧/运行器直接观测的输入大小指标，
保留产品自报值为辅助；追问②：绕开自报用量的观测量）。

输入：Codex rollout jsonl（会话侧原始事件日志；行 type=session_meta/turn_context/
response_item/*/event_msg/*/token_usage_record/world_state）。
输出：聚合收据 JSON——只含计数/字节/token 数/文件 sha256/输入 basename/字段名；
时间戳、cwd、session uuid、prompt/回复内容零出现。

指标（README 同口径）：
  R1 文件字节/行数
  R2 类型计数（type 与 type/payload.type 两级）
  R3 逐 turn 重构输入字节：上一 token_usage_record 边界之后全部 response_item
     载荷的 canonical JSON 序列化字节和（边界行不计入下一 turn）
  R4 逐 turn 输出侧字节：该边界内 payload.type∈{message,reasoning} 的字节和
  R5 逐 turn 自报 usage 汇总，字段一律冠 self_reported_ 前缀（auxiliary）

防泄漏：源文件所有长度>24 的内容字符串值（payload 中非白名单键的 str 值）逐一
检查不得出现在输出序列化文本，命中即 FATAL rc=2（private path leaked 同罪）。
确定性：输出不含墙钟时间戳；键排序；同输入重放逐字节可复现。
write-once：--out/--receipt/--witness-out 目标已存在则拒绝（rc=3）。

用法：
  主跑   python3 tools-request-side-observe.py --input A.jsonl [--input B.jsonl ...]
             [--input-dir DIR] --out aggregate.json [--receipt run.json]
         文件结构：{"schema","aggregate_sha256"(=canonical agg 文本 sha256),
                   "aggregate":{...}}
  见证   python3 tools-request-side-observe.py --witness aggregate.json
             --witness-out witness.json --input A.jsonl [--input ...|--input-dir DIR]
         见证三步：①shasum(外部实现) 复算 witnessed 文件 sha256；
                  ②同输入重放聚合，canonical sha256 与文件内 aggregate_sha256 对比；
                  ③重放文本与文件内 aggregate 逐字节对比。机器见证，非真人签名。
         --receipt 在见证模式被忽略。

版本史：v1 (2026-11-08) loop28 首发。
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

TOOL_VERSION = "1.0"
META_KEYS = {"type", "id", "turn_id", "root_turn_id", "thread_id", "session_id",
             "response_id", "model", "effort", "summary", "full", "state"}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=1) + "\n"


def collect_inputs(args):
    paths = list(args.input or [])
    if args.input_dir:
        for root, _dirs, files in os.walk(args.input_dir):
            for name in sorted(files):
                if name.endswith(".jsonl"):
                    paths.append(os.path.join(root, name))
    uniq = sorted(set(os.path.abspath(p) for p in paths))
    for p in uniq:
        if not os.path.isfile(p):
            sys.stderr.write("FATAL: input not found: %s\n" % p)
            sys.exit(2)
    if not uniq:
        sys.stderr.write("FATAL: no inputs\n")
        sys.exit(2)
    return uniq


def iter_content_strings(node):
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, str):
                if k not in META_KEYS and len(v) > 24:
                    yield v
            elif isinstance(v, (dict, list)):
                for s in iter_content_strings(v):
                    yield s
    elif isinstance(node, list):
        for v in node:
            if isinstance(v, str):
                if len(v) > 24:
                    yield v
            elif isinstance(v, (dict, list)):
                for s in iter_content_strings(v):
                    yield s


def observe_file(path):
    type_counts = {}
    turns = []
    cur_in_bytes = cur_out_bytes = cur_items = 0
    unparsable = total_lines = 0
    with open(path, "rb") as f:
        for raw in f:
            total_lines += 1
            try:
                o = json.loads(raw.decode("utf-8"))
            except Exception:
                unparsable += 1
                continue
            t = o.get("type", "?")
            payload = o.get("payload") if isinstance(o.get("payload"), dict) else {}
            st = payload.get("type")
            key = "%s/%s" % (t, st) if st else t
            type_counts[key] = type_counts.get(key, 0) + 1
            if t == "response_item":
                b = len(json.dumps(payload, ensure_ascii=False,
                                   sort_keys=True, separators=(",", ":")).encode("utf-8"))
                cur_in_bytes += b
                cur_items += 1
                if st in ("message", "reasoning"):
                    cur_out_bytes += b
            elif t == "token_usage_record":
                u = payload.get("usage") or {}
                turns.append({
                    "response_item_bytes_reconstructed": cur_in_bytes,
                    "output_message_reasoning_bytes": cur_out_bytes,
                    "response_item_count": cur_items,
                    "self_reported_input_tokens": u.get("input_tokens"),
                    "self_reported_cached_input_tokens": u.get("cached_input_tokens"),
                    "self_reported_cache_write_input_tokens": u.get("cache_write_input_tokens"),
                    "self_reported_output_tokens": u.get("output_tokens"),
                    "self_reported_reasoning_output_tokens": u.get("reasoning_output_tokens"),
                    "self_reported_total_tokens": u.get("total_tokens"),
                })
                cur_in_bytes = cur_out_bytes = cur_items = 0
    if cur_items:
        turns.append({
            "response_item_bytes_reconstructed": cur_in_bytes,
            "output_message_reasoning_bytes": cur_out_bytes,
            "response_item_count": cur_items,
            "self_reported_input_tokens": None,
            "self_reported_cached_input_tokens": None,
            "self_reported_cache_write_input_tokens": None,
            "self_reported_output_tokens": None,
            "self_reported_reasoning_output_tokens": None,
            "self_reported_total_tokens": None,
            "note": "tail after last usage boundary; no self-reported usage",
        })
    return {
        "file": os.path.basename(path),
        "sha256": sha256_file(path),
        "bytes": os.path.getsize(path),
        "lines": total_lines,
        "unparsable_lines": unparsable,
        "turns_closed": len([x for x in turns if "note" not in x]),
        "turns": turns,
        "type_counts": dict(sorted(type_counts.items())),
    }


def gather_contents(path):
    out = []
    with open(path, "rb") as f:
        for raw in f:
            try:
                o = json.loads(raw.decode("utf-8"))
            except Exception:
                continue
            payload = o.get("payload")
            if isinstance(payload, dict):
                out.extend(iter_content_strings(payload))
    return out


def aggregate(paths):
    files, all_contents = [], []
    tot = {"bytes": 0, "lines": 0, "turns_closed": 0, "unparsable_lines": 0}
    sr = {k: 0 for k in ("input_tokens", "cached_input_tokens", "cache_write_input_tokens",
                         "output_tokens", "reasoning_output_tokens", "total_tokens")}
    rc_bytes = out_bytes = rc_items = 0
    merged = {}
    for p in paths:
        rec = observe_file(p)
        all_contents.extend(gather_contents(p))
        for k, v in rec.pop("type_counts").items():
            merged[k] = merged.get(k, 0) + v
        for t in rec["turns"]:
            rc_bytes += t["response_item_bytes_reconstructed"]
            out_bytes += t["output_message_reasoning_bytes"]
            rc_items += t["response_item_count"]
            for f5 in sr:
                v = t.get("self_reported_" + f5)
                if isinstance(v, int):
                    sr[f5] += v
        tot["bytes"] += rec["bytes"]
        tot["lines"] += rec["lines"]
        tot["turns_closed"] += rec["turns_closed"]
        tot["unparsable_lines"] += rec["unparsable_lines"]
        files.append(rec)
    agg = {
        "schema": "request-side-observe-v1",
        "auxiliary_note": "all self_reported_* fields are product self-reported usage "
                          "(auxiliary); bytes fields are request-side observables "
                          "recomputed from rollout jsonl",
        "privacy_note": "content strings absent by construction; leak assertion enforced; "
                        "only counters/bytes/tokens/sha256/input basenames published",
        "files": files,
        "totals": {
            "files": len(files),
            "bytes": tot["bytes"],
            "lines": tot["lines"],
            "turns_closed": tot["turns_closed"],
            "unparsable_lines": tot["unparsable_lines"],
            "response_item_bytes_reconstructed_total": rc_bytes,
            "output_message_reasoning_bytes_total": out_bytes,
            "response_item_count_total": rc_items,
            "self_reported_input_tokens_total": sr["input_tokens"],
            "self_reported_cached_input_tokens_total": sr["cached_input_tokens"],
            "self_reported_cache_write_input_tokens_total": sr["cache_write_input_tokens"],
            "self_reported_output_tokens_total": sr["output_tokens"],
            "self_reported_reasoning_output_tokens_total": sr["reasoning_output_tokens"],
            "self_reported_total_tokens_total": sr["total_tokens"],
        },
        "merged_type_counts": dict(sorted(merged.items())),
        "tool_version": TOOL_VERSION,
        "tool_sha256": sha256_file(os.path.abspath(sys.argv[0])),
    }
    return agg, all_contents


def leak_check(obj, contents):
    text = canonical(obj)
    return text, [c for c in contents if c in text]


def write_once(path, text):
    if os.path.exists(path):
        sys.stderr.write("FATAL: write-once target exists: %s\n" % path)
        sys.exit(3)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    ap = argparse.ArgumentParser(description="request-side observability over rollout jsonl")
    ap.add_argument("--input", action="append")
    ap.add_argument("--input-dir")
    ap.add_argument("--out")
    ap.add_argument("--receipt")
    ap.add_argument("--witness")
    ap.add_argument("--witness-out")
    args = ap.parse_args()

    if args.witness:
        if not args.witness_out:
            sys.stderr.write("FATAL: --witness requires --witness-out\n")
            sys.exit(2)
        target = json.load(open(args.witness, encoding="utf-8"))
        declared = target.get("aggregate_sha256")
        if not declared:
            sys.stderr.write("FATAL: witness target lacks aggregate_sha256\n")
            sys.exit(2)
        file_sha = subprocess.run(["shasum", "-a", "256", args.witness],
                                  capture_output=True, text=True).stdout.split()[0]
        replay_paths = collect_inputs(args)
        agg, contents = aggregate(replay_paths)
        text, leaked = leak_check(agg, contents)
        if leaked:
            sys.stderr.write("FATAL: content string(s) in replayed aggregate\n")
            sys.exit(2)
        replay_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        replay_identical = text == canonical(target.get("aggregate"))
        rep = {
            "schema": "request-side-observe-witness-v1",
            "witnessed_file": os.path.basename(args.witness),
            "witnessed_file_sha256_shasum": file_sha,
            "target_aggregate_sha256_declared": declared,
            "replay_aggregate_sha256": replay_sha,
            "sha_match": replay_sha == declared,
            "deterministic_replay": replay_identical,
            "replay_input_count": len(replay_paths),
            "all_ok": (replay_sha == declared) and replay_identical,
            "note": "machine witness (shasum independent implementation + deterministic "
                    "replay); not a human signature",
            "tool_version": TOOL_VERSION,
            "tool_sha256": sha256_file(os.path.abspath(sys.argv[0])),
        }
        write_once(args.witness_out, canonical(rep))
        if args.receipt:
            sys.stderr.write("note: --receipt ignored in witness mode\n")
        print("WITNESS all_ok=%s target=%s replay=%s" % (rep["all_ok"], declared, replay_sha))
        sys.exit(0)

    paths = collect_inputs(args)
    if not args.out:
        sys.stderr.write("FATAL: --out required\n")
        sys.exit(2)
    agg, contents = aggregate(paths)
    text, leaked = leak_check(agg, contents)
    if leaked:
        sys.stderr.write("FATAL: content string(s) in output (%d matches)\n" % len(leaked))
        sys.exit(2)
    doc = {"schema": "request-side-observe-v1+sha",
           "aggregate_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
           "aggregate": agg}
    text2, leaked2 = leak_check(doc, contents)
    if leaked2:
        sys.stderr.write("FATAL: content string(s) in final output\n")
        sys.exit(2)
    write_once(args.out, text2)
    if args.receipt:
        rec = {
            "tool": "tools-request-side-observe.py v%s (loop28-20261108)" % TOOL_VERSION,
            "mode": "main",
            "rc": 0,
            "inputs": [os.path.basename(p) for p in paths],
            "out": os.path.basename(args.out),
            "out_sha256": sha256_file(args.out),
            "aggregate_sha256": doc["aggregate_sha256"],
            "tool_sha256": agg["tool_sha256"],
        }
        write_once(args.receipt, canonical(rec))
    print("OK files=%d bytes=%d turns=%d aggregate_sha256=%s" % (
        len(paths), agg["totals"]["bytes"], agg["totals"]["turns_closed"],
        doc["aggregate_sha256"]))


if __name__ == "__main__":
    main()
