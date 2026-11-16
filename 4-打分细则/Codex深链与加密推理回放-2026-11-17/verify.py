#!/usr/bin/env python3
"""Codex 深链与加密推理回放（环15）verify — stdlib only。

build（私档）：--archive-base <until14根> --build-evidence <e.json> --output <r.json>
replay（公开）：--evidence <e.json> --output <r.json>
"""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

SCHEMA = "codex-chain-encrypted-replay-evidence-v1"
BASELINE = "0f3eef0"
FROZEN_README_SHA256 = "bdc748817b10a6c3b0553850afdee72693007c0c3f8d6b26da6a97ede5968336"

RUN_SPECS = {"r1": {"requests": 3}, "r2": {"requests": 3}}
RUN_RELS = {"r1": "codex-t3-r1", "r2": "codex-t3-r2"}
REQ1_SHAS = {
    "r1": "2cf01fa3bb3c8b437926d7cdae9abac17f1e04062dba75ed6189e6c19b26ae7c",
    "r2": "9a0a4c8286fffa0d5a5c2b7260d095fd234f4b51fbf6ab3c6b210f26e75c1661",
}
LENS_EXPECT = {"r1": [4, 7, 10], "r2": [4, 10, 13]}
SHAPES_EXPECT = {
    "r1": [["reasoning", "function_call", "function_call_output"],
           ["reasoning", "function_call", "function_call_output"]],
    "r2": [["reasoning", "message", "function_call", "function_call", "function_call_output", "function_call_output"],
           ["reasoning", "function_call", "function_call_output"]],
}
REQ1_DIFF_LEAVES_EXPECT = 11
REQ1_DIFF_FIELDS_EXPECT = {"client_metadata": 6, "input_item_id": 4, "prompt_cache_key": 1}
REQ1_NORM_SHA = "1dadb193a1462a31849237a68f891020b8bcb3014ce270dafcf65c7a97848b5a"
ENCRYPTED_STABILITY_EXPECT = {
    "req2": [{"reasoning_index": 1, "encrypted_equal": False, "summary_equal": True}],
    "req3": [{"reasoning_index": 1, "encrypted_equal": False, "summary_equal": True},
             {"reasoning_index": 2, "encrypted_equal": False, "summary_equal": True}],
}
TASK_TEXT_SHA256 = "e7fea6df7f205a8c1542bbae3ada653a8e2a8fb09a27efa92547c2e3864153d4"
WORKSPACE_AGG_SHA256 = "282e86ecbec0d448dadbc8db52a533b2126684044a868cd6f6721ea4fc3d1329"
WORKSPACE_AGG_RULE = "sha256 of UTF-8 lines 'relpath:filesha256\\n' over sorted workspace files (13 files)"

LIMITS = [
    "public replay checks sealed consistency only; byte-level verification runs against privately archived request bodies",
    "single task, single model (deepseek-flash), n=2 run pairs; no extrapolation",
    "execution split (step count / message emission) differs across runs by model-side freedom; shape deltas are registered, not scored",
    "id normalization and encrypted_content normalization are comparison definitions, not provider attestation",
    "response bodies (model output) are not part of any endpoint",
]


class Invalid(ValueError):
    pass


def require(cond, msg):
    if not cond:
        raise Invalid(msg)


def _pairs(pairs):
    d = {}
    for k, v in pairs:
        require(k not in d, "duplicate key %s" % k)
        d[k] = v
    return d


def _reject_const(name):
    raise Invalid("non-finite number %s" % name)


def _reject_float(text):
    raise Invalid("non-integer number %s" % text)


def loads(raw):
    require(isinstance(raw, (bytes, bytearray)), "payload not bytes")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                      parse_constant=_reject_const, parse_float=_reject_float)


def sha(x):
    return hashlib.sha256(x).hexdigest()


def canon(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def normalize_ids(req):
    d = copy.deepcopy(req)
    d["client_metadata"] = "NORMALIZED"
    d["prompt_cache_key"] = "NORMALIZED"
    for it in d.get("input", []):
        if isinstance(it, dict):
            if "id" in it:
                it["id"] = "NORMALIZED"
            if "encrypted_content" in it:
                it["encrypted_content"] = "NORMALIZED"
    return d


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(x.get("text", "") for x in content if isinstance(x, dict))
    raise Invalid("unexpected content type")


def load_run(archive_base, run):
    d = archive_base / "loop15" / RUN_RELS[run] / "requests"
    bins = []
    n = RUN_SPECS[run]["requests"]
    for i in range(1, n + 1):
        p = d / ("00%d.request.bin" % i)
        require(p.is_file(), "missing request %s" % p)
        bins.append(p.read_bytes())
    return [loads(b) for b in bins], bins


def diff_leaves(a, b, path="", out=None):
    if out is None:
        out = []
    if type(a) is not type(b):
        out.append((path, "type"))
    elif isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append((path + "/" + k, "only-b"))
            elif k not in b:
                out.append((path + "/" + k, "only-a"))
            else:
                diff_leaves(a[k], b[k], path + "/" + k, out)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append((path, "len"))
        else:
            for j, (u, v) in enumerate(zip(a, b)):
                diff_leaves(u, v, "%s[%d]" % (path, j), out)
    elif a != b:
        out.append((path, "val"))
    return out


def leaf_bucket(path):
    if path.startswith("/client_metadata"):
        return "client_metadata"
    if path.startswith("/prompt_cache_key"):
        return "prompt_cache_key"
    if path.endswith("/id"):
        return "input_item_id"
    return "other"


def reasoning_stability(r1_req, r2_req, req_name):
    r1 = [it for it in r1_req["input"] if it.get("type") == "reasoning"]
    r2 = [it for it in r2_req["input"] if it.get("type") == "reasoning"]
    require(len(r1) == len(r2), "reasoning count mismatch in %s" % req_name)
    rows = []
    for k, (it1, it2) in enumerate(zip(r1, r2), 1):
        rows.append({"reasoning_index": k,
                     "encrypted_equal": it1.get("encrypted_content") == it2.get("encrypted_content"),
                     "summary_equal": it1.get("summary") == it2.get("summary")})
    expect = ENCRYPTED_STABILITY_EXPECT[req_name]
    require(rows == expect, "encrypted stability pin mismatch in %s" % req_name)
    return rows


def build(archive_base):
    runs = {}
    data = {}
    for run in ("r1", "r2"):
        reqs, bins = load_run(archive_base, run)
        data[run] = reqs
        lens = [len(d["input"]) for d in reqs]
        require(lens == LENS_EXPECT[run], "input lens pin mismatch %s" % run)
        for k in range(len(reqs) - 1):
            require(reqs[k + 1]["input"][:lens[k]] == reqs[k]["input"], "prefix broken %s step%d" % (run, k + 1))
        shapes = [[it.get("type") for it in reqs[k + 1]["input"][lens[k]:]] for k in range(len(reqs) - 1)]
        require(shapes == SHAPES_EXPECT[run], "appended shapes pin mismatch %s" % run)
        deltas = [len(bins[k + 1]) - len(bins[k]) for k in range(len(bins) - 1)]
        entry = {"requests": len(reqs),
                 "req_sha256": [sha(b) for b in bins],
                 "req_bytes": [len(b) for b in bins],
                 "input_lens": lens,
                 "appended_shapes": shapes,
                 "deltas": deltas,
                 "upstream_status": [200] * len(reqs)}
        require(entry["req_sha256"][0] == REQ1_SHAS[run], "req1 sha pin mismatch %s" % run)
        for d in reqs:
            require(d.get("store") is False, "store not false")
            require("previous_response_id" not in d, "previous_response_id present")
            require(d.get("include") == ["reasoning.encrypted_content"], "include mismatch")
            require(d.get("model") == "deepseek-flash", "model mismatch")
            require(d.get("prompt_cache_key") == d.get("client_metadata", {}).get("thread_id"),
                    "prompt_cache_key != thread_id")
        runs[run] = entry
    # P2：req1 跨 run
    a, b = data["r1"][0], data["r2"][0]
    byte_equal = canon(a) == canon(b)
    leaves = diff_leaves(a, b)
    buckets = {}
    for p, _k in leaves:
        bb = leaf_bucket(p)
        buckets[bb] = buckets.get(bb, 0) + 1
    require(all(bb in ("client_metadata", "input_item_id", "prompt_cache_key") for bb in buckets),
            "non-id diff leaf in req1")
    require(len(leaves) == REQ1_DIFF_LEAVES_EXPECT, "req1 diff leaves pin mismatch")
    require(buckets == REQ1_DIFF_FIELDS_EXPECT, "req1 diff fields pin mismatch")
    n1, n2 = canon(normalize_ids(a)), canon(normalize_ids(b))
    require(n1 == n2, "req1 normalized not equal")
    require(sha(n1) == REQ1_NORM_SHA, "req1 normalized sha pin mismatch")
    # P3：加密推理回放稳定性
    enc = {"req2": reasoning_stability(data["r1"][1], data["r2"][1], "req2"),
           "req3": reasoning_stability(data["r1"][2], data["r2"][2], "req3")}
    # 任务面：input[3] 为用户任务消息（60B prompt）
    task = text_of(a["input"][3]["content"])
    require(sha(task.encode()) == TASK_TEXT_SHA256, "task text sha mismatch")
    require(len(task.encode()) == 60, "task text bytes != 60")
    evidence = {
        "schema": SCHEMA,
        "baseline": BASELINE,
        "frozen_readme_sha256": FROZEN_README_SHA256,
        "runs": runs,
        "req1_cross_run": {"byte_equal": byte_equal, "diff_leaves": len(leaves),
                           "diff_fields": buckets,
                           "id_normalized_canonical_sha256": REQ1_NORM_SHA},
        "encrypted_replay_stability": enc,
        "workspace": {"aggregate_sha256": WORKSPACE_AGG_SHA256,
                      "aggregate_rule": WORKSPACE_AGG_RULE,
                      "rebuilt_noop": True},
        "task_surface": {"task_text_sha256": TASK_TEXT_SHA256, "task_text_bytes": 60},
        "verdict": "chain_append_stable_encrypted_per_run",
        "limits": LIMITS,
    }
    evidence_bytes = canon(evidence) + b"\n"
    result = {
        "schema": SCHEMA,
        "baseline": evidence["baseline"],
        "verdict": evidence["verdict"],
        "req1_cross_run": evidence["req1_cross_run"],
        "encrypted_replay_stability": evidence["encrypted_replay_stability"],
        "evidence_sha256": sha(evidence_bytes),
        "limits": LIMITS,
    }
    return evidence, evidence_bytes, result


def validate_public(evidence):
    require(evidence.get("schema") == SCHEMA, "schema mismatch")
    require(evidence.get("baseline") == BASELINE, "baseline mismatch")
    require(evidence.get("frozen_readme_sha256") == FROZEN_README_SHA256, "readme pin mismatch")
    require(evidence.get("verdict") == "chain_append_stable_encrypted_per_run", "verdict mismatch")
    rc = evidence.get("req1_cross_run") or {}
    require(rc.get("byte_equal") is False, "byte_equal pin")
    require(rc.get("diff_leaves") == REQ1_DIFF_LEAVES_EXPECT, "diff leaves pin")
    require(rc.get("diff_fields") == REQ1_DIFF_FIELDS_EXPECT, "diff fields pin")
    require(rc.get("id_normalized_canonical_sha256") == REQ1_NORM_SHA, "normalized pin")
    require(evidence.get("encrypted_replay_stability") == ENCRYPTED_STABILITY_EXPECT, "encrypted pin")
    ts = evidence.get("task_surface") or {}
    require(ts.get("task_text_sha256") == TASK_TEXT_SHA256 and ts.get("task_text_bytes") == 60, "task pin")
    ws = evidence.get("workspace") or {}
    require(ws.get("aggregate_sha256") == WORKSPACE_AGG_SHA256, "workspace pin")
    require(ws.get("aggregate_rule") == WORKSPACE_AGG_RULE, "workspace rule pin")
    require(ws.get("rebuilt_noop") is True, "noop pin")
    runs = evidence.get("runs") or {}
    require(set(runs) == {"r1", "r2"}, "runs pin")
    for run, spec in RUN_SPECS.items():
        e = runs[run]
        require(e.get("requests") == spec["requests"], "count pin %s" % run)
        require(len(e.get("req_sha256", [])) == spec["requests"], "sha list pin %s" % run)
        require(e.get("req_sha256", [""])[0] == REQ1_SHAS[run], "req1 sha pin %s" % run)
        require(e.get("input_lens") == LENS_EXPECT[run], "lens pin %s" % run)
        require(e.get("appended_shapes") == SHAPES_EXPECT[run], "shapes pin %s" % run)
    require(evidence.get("limits") == LIMITS, "limits mismatch")
    blob = json.dumps(evidence, ensure_ascii=False)
    require("/Users" not in blob, "private path leak")
    require("sk-" not in blob, "credential-shaped leak")


def result_for(evidence, evidence_bytes):
    return {
        "schema": SCHEMA,
        "baseline": evidence.get("baseline"),
        "verdict": evidence.get("verdict"),
        "req1_cross_run": evidence.get("req1_cross_run"),
        "encrypted_replay_stability": evidence.get("encrypted_replay_stability"),
        "evidence_sha256": sha(evidence_bytes),
        "limits": LIMITS,
    }


def exclusive(path, raw):
    p = Path(path)
    require(not p.exists(), "output exists")
    require(".." not in str(p), "path traversal")
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "xb") as f:
        f.write(raw)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive-base")
    parser.add_argument("--build-evidence")
    parser.add_argument("--evidence")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.evidence:
            require(args.archive_base is None and args.build_evidence is None,
                    "replay takes only --evidence/--output")
            evidence_bytes = Path(args.evidence).read_bytes()
            evidence = loads(evidence_bytes)
            validate_public(evidence)
            result = result_for(evidence, evidence_bytes)
        else:
            require(args.archive_base and args.build_evidence, "build needs --archive-base/--build-evidence")
            evidence, evidence_bytes, result = build(Path(args.archive_base))
            exclusive(args.build_evidence, evidence_bytes)
        exclusive(args.output, canon(result) + b"\n")
        if args.evidence:
            print("codex chain replay OK: verdict=%s" % evidence.get("verdict"))
        else:
            print("codex chain rebuild OK: prefix ok | req1 11 id-class leaves normalized-equal | encrypted per-run")
        return 0
    except (Invalid, ValueError, OSError, TypeError, KeyError):
        print("input or output failure")
        return 2


if __name__ == "__main__":
    sys.exit(main())
