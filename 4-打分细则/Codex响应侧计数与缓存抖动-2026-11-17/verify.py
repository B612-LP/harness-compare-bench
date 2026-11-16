#!/usr/bin/env python3
"""Codex 响应侧计数与缓存抖动（2026-11-17）公开验证器。

两种模式：
  公档重放：--root <repo> --output <r> [--evidence <e>]
      核本 README / 环14·环15 公开 evidence 的文件 SHA pin；核 11 行 usage 记录的
      schema、整数域、请求 SHA 与已发布 req_sha256 列表的位置/字节一致；重算 E1/E2/E3。
  私档重建：--root <repo> --archive-root <capture-parent> --build-evidence <e> --output <r>
      从 loop14/loop15 捕获目录重建 usage 行（SSE/JSON 解析），再走同一公档校验。
退出码：0 通过；2 参数/校验失败（fail-closed，不写成功输出）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASELINE = "b40ce6e346597846c6b451f7e1296128ae9a3247"
SCHEMA = "codex-usage-rows-v1"
RESULT_SCHEMA = "codex-usage-result-v1"

T1_EVIDENCE_REL = "4-打分细则/Codex请求侧最小捕获-2026-11-17/evidence.json"
T3_EVIDENCE_REL = "4-打分细则/Codex深链与加密推理回放-2026-11-17/evidence.json"
PIN_T1 = "332f9f827c650af08571cc16dfa6666a9c2f05c10b5cf89ee03c81a273ce1a16"
PIN_T3 = "8f7aa8a15e542bf3c1c307341de7a1567d655ef5bbbc2466d7611455b6b4ab6a"
README_SHA = "9818fc013d127c54021cd64e9068923297bd36568f754cd1e953caaf87328ab0"
PIN_EVIDENCE = "2bddde198863d965fd551b34d07267225095226796bf3796b662b9d3f5b19ce7"

TASK_RUNS = {"codex-t1": ["r1", "r2"], "codex-t3": ["r1", "r2"]}
EXPECT_ROWS = 11  # 3 + 2 + 3 + 3
CAPTURE_DIRS = {  # 相对 archive-root（私档父目录）
    ("codex-t1", "r1"): "loop14/capture-codex-r1",
    ("codex-t1", "r2"): "loop14/capture-codex-r2",
    ("codex-t3", "r1"): "loop15/codex-t3-r1",
    ("codex-t3", "r2"): "loop15/codex-t3-r2",
}


class Invalid(Exception):
    pass


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise Invalid(msg)


def no_duplicate_keys(pairs):
    seen = set()
    for k, _ in pairs:
        if k in seen:
            raise Invalid("duplicate key: %s" % k)
        seen.add(k)
    return dict(pairs)


def _reject_const(name):
    raise Invalid("non-finite constant: %s" % name)


def loads(raw: bytes):
    require(isinstance(raw, (bytes, bytearray)), "payload not bytes")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicate_keys,
                          parse_constant=_reject_const)
    except Invalid:
        raise
    except Exception as exc:
        raise Invalid("bad json: %s" % exc)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def pinned(root: str, rel: str, expected: str) -> bytes:
    path = os.path.join(root, rel)
    require(os.path.isfile(path), "missing pinned file: %s" % rel)
    raw = open(path, "rb").read()
    require(sha(raw) == expected, "pin mismatch: %s" % rel)
    return raw


def integer(value, minimum: int = 0, label: str = "int") -> int:
    require(isinstance(value, int) and not isinstance(value, bool), "%s not int" % label)
    require(value >= minimum, "%s below minimum" % label)
    return value


def opt_integer(value, label: str):
    if value is None:
        return None
    return integer(value, 0, label)


def usage_of_response(raw: bytes):
    """从响应字节提取最终 usage（JSON 对象或 SSE 事件流）。"""
    if raw[:1] in (b"{", b"["):
        doc = loads(bytes(raw))
        require(isinstance(doc, dict), "json response not object")
        return doc.get("usage")
    usage = None
    for line in raw.decode("utf-8", "replace").splitlines():
        if not line.startswith("data: "):
            continue
        try:
            ev = loads(line[6:].encode("utf-8"))
        except Invalid:
            continue
        if not isinstance(ev, dict):
            continue
        resp = ev.get("response")
        if isinstance(resp, dict) and isinstance(resp.get("usage"), dict):
            usage = resp["usage"]
        if ev.get("type") == "response.completed" and isinstance(ev.get("usage"), dict):
            usage = ev["usage"]
    return usage


def safe_join(root: str, rel: str) -> str:
    require(not os.path.isabs(rel), "absolute path")
    parts = [p for p in rel.split("/") if p not in ("", ".")]
    require(all(p != ".." for p in parts), "path traversal")
    path = os.path.realpath(os.path.join(root, *parts))
    require(path.startswith(os.path.realpath(root) + os.sep), "escape root")
    return path


def exclusive(path: str, raw: bytes) -> None:
    require(not os.path.exists(path), "refusing to overwrite: %s" % path)
    parent = os.path.dirname(os.path.abspath(path))
    require(os.path.isdir(parent), "missing parent")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        os.write(fd, raw)
    finally:
        os.close(fd)


def build_rows(archive_root: str, published: dict) -> list:
    rows = []
    for (task, run), rel in CAPTURE_DIRS.items():
        base = safe_join(archive_root, rel)
        reqs = sorted(f for f in os.listdir(os.path.join(base, "requests")) if f.endswith(".bin"))
        resps = sorted(f for f in os.listdir(os.path.join(base, "responses")) if f.endswith(".bin"))
        require(len(reqs) == len(resps) and len(reqs) > 0, "capture pair mismatch: %s" % rel)
        for i, (rq, rs) in enumerate(zip(reqs, resps), 1):
            rsha = sha(open(os.path.join(base, "requests", rq), "rb").read())
            lst = published[task][run]["req_sha256"]
            require(rsha in lst, "request sha not published: %s %s" % (rel, rsha[:12]))
            require(lst.index(rsha) == i - 1, "request position mismatch: %s" % rel)
            usage = usage_of_response(open(os.path.join(base, "responses", rs), "rb").read())
            require(isinstance(usage, dict), "no usage: %s/%s" % (rel, rs))
            details_in = usage.get("input_tokens_details") or {}
            details_out = usage.get("output_tokens_details") or {}
            rows.append({
                "task": task, "run": run, "seq": i,
                "request_sha256": rsha,
                "request_bytes": integer(os.path.getsize(os.path.join(base, "requests", rq)), 1),
                "response_sha256": sha(open(os.path.join(base, "responses", rs), "rb").read()),
                "input_tokens": integer(usage.get("input_tokens")),
                "output_tokens": integer(usage.get("output_tokens")),
                "total_tokens": integer(usage.get("total_tokens")),
                "cached_tokens": opt_integer(details_in.get("cached_tokens"), "cached"),
                "reasoning_tokens": opt_integer(details_out.get("reasoning_tokens"), "reasoning"),
            })
    require(len(rows) == EXPECT_ROWS, "row count %d" % len(rows))
    return rows


def expected_rows_order(rows: list) -> None:
    order = []
    for task in ("codex-t1", "codex-t3"):
        for run in TASK_RUNS[task]:
            for row in rows:
                if row["task"] == task and row["run"] == run:
                    order.append((task, run, row["seq"]))
    seqs = {}
    for task, run, seq in order:
        seqs.setdefault((task, run), []).append(seq)
    for key, vals in seqs.items():
        require(vals == list(range(1, len(vals) + 1)), "seq order %s" % (key,))


def endpoints(rows: list, published: dict) -> dict:
    e1_pairs = []
    e2_pairs = []
    for task in TASK_RUNS:
        rs = TASK_RUNS[task]
        require(set(rs) == {"r1", "r2"}, "runs %s" % task)
        by = {r["run"]: r for r in rows if r["task"] == task and r["seq"] == 1}
        require(set(by) == {"r1", "r2"}, "first rows %s" % task)
        a, b = by["r1"], by["r2"]
        pub = published[task]
        require(len(pub["r1"]["req_sha256"]) >= 1 and len(pub["r2"]["req_sha256"]) >= 1, "pub lists")
        la = pub["r1"]["req_bytes"][0]
        lb = pub["r2"]["req_bytes"][0]
        require(a["request_bytes"] == la and b["request_bytes"] == lb, "byte pin %s" % task)
        e1_pairs.append({"task": task, "equal": a["input_tokens"] == b["input_tokens"],
                         "values": [a["input_tokens"], b["input_tokens"]]})
        e2_pairs.append({"task": task, "differ": a["cached_tokens"] != b["cached_tokens"],
                         "values": [a["cached_tokens"], b["cached_tokens"]]})
    e1 = sum(1 for p in e1_pairs if p["equal"])
    e2 = sum(1 for p in e2_pairs if p["differ"])
    deltas = []
    for task in TASK_RUNS:
        for run in TASK_RUNS[task]:
            seqrows = sorted((r for r in rows if r["task"] == task and r["run"] == run),
                             key=lambda r: r["seq"])
            for x, y in zip(seqrows, seqrows[1:]):
                deltas.append({"task": task, "run": run, "from_seq": x["seq"], "to_seq": y["seq"],
                               "delta_request_bytes": y["request_bytes"] - x["request_bytes"],
                               "delta_input_tokens": y["input_tokens"] - x["input_tokens"]})
    first_cached = {("%s/%s" % (r["task"], r["run"])): r["cached_tokens"]
                    for r in rows if r["seq"] == 1}
    return {"e1_input_equal_pairs": e1, "e1_total": 2, "e1_pairs": e1_pairs,
            "e2_cached_differ_pairs": e2, "e2_total": 2, "e2_pairs": e2_pairs,
            "first_request_cached_tokens": first_cached, "chain_deltas": deltas}


def verdict_for(endpoints: dict) -> str:
    if endpoints["e1_input_equal_pairs"] == 2 and endpoints["e2_cached_differ_pairs"] == 2:
        return "usage_stable_cache_volatile_codex_side"
    return "usage_pattern_divergent_from_dsh_side"


def validate_rows(rows, published) -> None:
    require(isinstance(rows, list) and len(rows) == EXPECT_ROWS, "rows length")
    seen = set()
    for row in rows:
        require(isinstance(row, dict), "row not object")
        require(set(row.keys()) == {"task", "run", "seq", "request_sha256", "request_bytes",
                                    "response_sha256", "input_tokens", "output_tokens",
                                    "total_tokens", "cached_tokens", "reasoning_tokens"},
                "row keys %s" % sorted(row.keys()))
        require(row["task"] in TASK_RUNS and row["run"] in TASK_RUNS[row["task"]], "task/run")
        integer(row["seq"], 1, "seq")
        key = (row["task"], row["run"], row["seq"])
        require(key not in seen, "duplicate row %s" % (key,))
        seen.add(key)
        for f in ("request_sha256", "response_sha256"):
            v = row[f]
            require(isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v),
                    "%s not sha256" % f)
        integer(row["request_bytes"], 1, "request_bytes")
        for f in ("input_tokens", "output_tokens", "total_tokens"):
            integer(row[f], 0, f)
        opt_integer(row["cached_tokens"], "cached_tokens")
        opt_integer(row["reasoning_tokens"], "reasoning_tokens")
    expected_rows_order(rows)
    for row in rows:
        pub = published[row["task"]][row["run"]]
        idx = row["seq"] - 1
        require(idx < len(pub["req_sha256"]), "row beyond published chain %s" % (row,))
        require(pub["req_sha256"][idx] == row["request_sha256"], "request sha binding %s" % (row,))
        require(pub["req_bytes"][idx] == row["request_bytes"], "request bytes binding %s" % (row,))


def build(root: str, archive_root: str):
    t1_raw = pinned(root, T1_EVIDENCE_REL, PIN_T1)
    t3_raw = pinned(root, T3_EVIDENCE_REL, PIN_T3)
    published = {"codex-t1": loads(t1_raw)["runs"], "codex-t3": loads(t3_raw)["runs"]}
    for task, runs in published.items():
        require(sorted(runs.keys()) == ["r1", "r2"], "published runs %s" % task)
        for rk, rv in runs.items():
            require(isinstance(rv.get("req_sha256"), list) and isinstance(rv.get("req_bytes"), list),
                    "published lists %s/%s" % (task, rk))
    rows = build_rows(archive_root, published)
    evidence = {
        "schema": SCHEMA, "baseline": BASELINE,
        "frozen_readme_sha256": README_SHA,
        "bindings": {"t1_evidence_sha256": PIN_T1, "t3_evidence_sha256": PIN_T3,
                     "t1_evidence_rel": T1_EVIDENCE_REL, "t3_evidence_rel": T3_EVIDENCE_REL},
        "rows": rows,
        "limits": [
            "product-reported counters only; no billing/kv-reuse/cache-mechanism claim",
            "codex req1 pairs are equal-length + id-normalized identical, weaker than dsh same-byte pairs",
            "bytes are not tokens; chain deltas are registered, not modeled",
            "usage rows bind to published request sha lists; response bodies remain private",
        ],
    }
    raw = json.dumps(evidence, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8") + b"\n"
    return evidence, raw


def validate_public(payload: bytes, root: str) -> dict:
    ev = loads(payload)
    require(ev.get("schema") == SCHEMA, "schema")
    require(ev.get("baseline") == BASELINE, "baseline")
    require(ev.get("frozen_readme_sha256") == README_SHA, "readme pin")
    b = ev.get("bindings") or {}
    require(b.get("t1_evidence_sha256") == PIN_T1 and b.get("t3_evidence_sha256") == PIN_T3, "bindings")
    pinned(root, b.get("t1_evidence_rel") or "", PIN_T1)
    pinned(root, b.get("t3_evidence_rel") or "", PIN_T3)
    published = {"codex-t1": loads(pinned(root, T1_EVIDENCE_REL, PIN_T1))["runs"],
                 "codex-t3": loads(pinned(root, T3_EVIDENCE_REL, PIN_T3))["runs"]}
    rows = ev.get("rows")
    require(isinstance(ev.get("limits"), list) and len(ev["limits"]) >= 4, "limits")
    validate_rows(rows, published)
    eps = endpoints(rows, published)
    result = {
        "schema": RESULT_SCHEMA, "baseline": BASELINE,
        "evidence_sha256": sha(payload),
        "verdict": verdict_for(eps),
        "endpoints": eps,
        "rows_count": len(rows),
        "limits": ev["limits"] + [
            "public replay re-checks arithmetic and bindings only; private responses not authenticated",
            "dual-output writes are sequential, not transactional",
        ],
    }
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    ap.add_argument("--archive-root", default=None)
    ap.add_argument("--build-evidence", default=None)
    ap.add_argument("--evidence", default=None)
    ap.add_argument("--output", required=True)
    args = ap.parse_args(argv)
    root = args.root or os.path.dirname(os.path.dirname(HERE))  # HERE=包目录；两层上=仓库根
    try:
        if args.build_evidence:
            require(args.archive_root, "--build-evidence requires --archive-root")
            evidence, raw = build(root, args.archive_root)
            exclusive(args.build_evidence, raw)
            payload = raw
        else:
            if args.evidence:
                require(os.path.isfile(args.evidence), "evidence not found")
                payload = open(args.evidence, "rb").read()
                require(sha(payload) == PIN_EVIDENCE,
                        "--evidence must be the sealed evidence bytes")
            else:
                payload = pinned(HERE, "evidence.json", PIN_EVIDENCE)
        result = validate_public(payload, root)
        raw = json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8") + b"\n"
        exclusive(args.output, raw)
        print("verdict=%s e1=%d/2 e2=%d/2 rows=%d" % (
            result["verdict"], result["endpoints"]["e1_input_equal_pairs"],
            result["endpoints"]["e2_cached_differ_pairs"], result["rows_count"]))
        return 0
    except Invalid as exc:
        print("invalid: %s" % exc, file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print("input or output failure", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
