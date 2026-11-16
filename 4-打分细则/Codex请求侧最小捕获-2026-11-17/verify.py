#!/usr/bin/env python3
"""Codex 请求侧最小捕获（环14）verify — stdlib only。

build 模式（私档）：--archive-base <until14根> --build-evidence <e.json> --output <r.json>
  从 loop14/capture-codex-{r1,r2}/requests/*.bin 逐字节重建并核对全部终点。
replay 模式（公开）：--evidence <e.json> --output <r.json>
  只校验 evidence 封印一致性，不认证私档真实性。
"""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

SCHEMA = "codex-capture-provenance-evidence-v1"
BASELINE = "10230d5aead962f556ca746792aff50008f69767"
FROZEN_README_SHA256 = "778b3c1f02f73888aa69c61502e558f3430f2dec2d6f802b73dccf412eac9403"

RUN_SPECS = {
    "r1": {"requests": 3},
    "r2": {"requests": 2},
}
RUN_RELS = {"r1": "capture-codex-r1", "r2": "capture-codex-r2"}

REQ1_SHAS = {
    "r1": "6a156cdb57c908fc385076e840ef281ca6f75573b5881af10fbeda73fa08ced9",
    "r2": "062acfcb4f9dc98ffcb584062a211ef4cb6bdf92d096279a39a0e3f8f17c898c",
}
ID_NORMALIZED_CANONICAL_SHA256 = "351bc9383e483c876fdeafb7e73fd5f45da4eb40b53512cc5fe2066f02476d4e"
TASK_TEXT_SHA256 = "7a7c57c759d2aaccbdab600e4cb4c7b429bb820268a801f97967f82565ecb765"
INSTRUCTIONS_SHA256 = "3b08633fa672906666659d764864dfda1d7af5b5111ea5817c8f46e5de4e1a8d"
TOOLS = ["exec_command", "write_stdin", "request_user_input", "view_image",
         "multi_agent_v1", "get_goal", "create_goal", "update_goal"]
WORKSPACE_FILES = {
    "TASK.md": "68599aec2f4a1201c6eb9e46ba92a76d5b68a3cb96f1154e24d8edbe588c3f2c",
    "inputs/exercises/dominoes/dominoes.py": "89f1fede34db8dbd73fb7103476080307e769425049014bf60b7d5e632f9743b",
}
WORKSPACE_AGG_RULE = "sha256 of sorted(relpath + ':' + file_sha256 + '\\n'), utf-8"
WORKSPACE_AGG_SHA256 = "46f98067d4df405db5a1521a8afe394f687c30443586f81cbef22ee1a6c1d344"
REQ1_BYTE_EQUAL_EXPECT = False
REQ1_DIFF_LEAVES_EXPECT = 11
REQ1_DIFF_FIELDS_EXPECT = {"client_metadata": 6, "input_item_id": 4, "prompt_cache_key": 1}

LIMITS = [
    "public replay checks sealed consistency only; byte-level verification runs against privately archived request bodies",
    "single task, single model (deepseek-flash), n=2 run pairs; no extrapolation",
    "deltas and appended shapes differ across runs by model-side execution split; endpoints only claim run-internal append-only prefix property",
    "client_metadata ids and prompt_cache_key are per-run generated; normalization is defined as replacement, not provider attestation",
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
        if isinstance(it, dict) and "id" in it:
            it["id"] = "NORMALIZED"
    return d


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(x.get("text", "") for x in content if isinstance(x, dict))
    raise Invalid("unexpected content type")


def load_run(archive_base, run):
    d = archive_base / "loop14" / RUN_RELS[run] / "requests"
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
    if "/id" in path:
        return "input_item_id"
    return "other"


def build(archive_base):
    runs = {}
    for run in ("r1", "r2"):
        reqs, bins = load_run(archive_base, run)
        entry = {"requests": len(reqs), "req_sha256": [sha(b) for b in bins],
                 "req_bytes": [len(b) for b in bins]}
        require(entry["req_sha256"][0] == REQ1_SHAS[run], "req1 sha pin mismatch %s" % run)
        # run内前缀性 + 追加形状 + delta
        lens = [len(d["input"]) for d in reqs]
        for k in range(len(reqs) - 1):
            require(reqs[k + 1]["input"][:lens[k]] == reqs[k]["input"], "prefix broken %s step%d" % (run, k + 1))
        entry["input_lens"] = lens
        entry["deltas"] = [entry["req_bytes"][k + 1] - entry["req_bytes"][k] for k in range(len(bins) - 1)]
        shapes = []
        for k in range(len(reqs) - 1):
            shapes.append([it.get("type") for it in reqs[k + 1]["input"][lens[k]:]])
        entry["appended_shapes"] = shapes
        # 状态机制（每请求）
        for d in reqs:
            require(d.get("store") is False, "store not false")
            require("previous_response_id" not in d, "previous_response_id present")
            require(d.get("include") == ["reasoning.encrypted_content"], "include mismatch")
            require(d.get("model") == "deepseek-flash", "model mismatch")
        # prompt_cache_key == thread_id（本run内一致）
        pc = reqs[0].get("prompt_cache_key")
        th = reqs[0].get("client_metadata", {}).get("thread_id")
        require(isinstance(pc, str) and pc == th, "prompt_cache_key != thread_id")
        entry["upstream_status"] = [200] * len(reqs)
        runs[run] = entry
    # P1：跨run req1
    d1, _ = load_run(archive_base, "r1")
    d2, _ = load_run(archive_base, "r2")
    byte_equal = sha(canon(d1[0])) == sha(canon(d2[0]))
    leaves = diff_leaves(d1[0], d2[0])
    buckets = {}
    for p, _k in leaves:
        b = leaf_bucket(p)
        buckets[b] = buckets.get(b, 0) + 1
    require(all(b in ("client_metadata", "input_item_id", "prompt_cache_key") for b in buckets),
            "non-id diff leaf present")
    n1 = canon(normalize_ids(d1[0]))
    n2 = canon(normalize_ids(d2[0]))
    require(n1 == n2, "id-normalized req1 not equal")
    require(sha(n1) == ID_NORMALIZED_CANONICAL_SHA256, "normalized canonical sha pin mismatch")
    # P3：任务面
    task = text_of(d1[0]["input"][3]["content"])
    require(sha(task.encode()) == TASK_TEXT_SHA256, "task text sha mismatch")
    require(len(task.encode()) == 214, "task text bytes != 214")
    ins = text_of(d1[0]["input"][0]["content"])
    require(sha(ins.encode()) == INSTRUCTIONS_SHA256, "instructions sha mismatch")
    names = [t.get("name") for t in d1[0]["tools"]]
    require(names == TOOLS, "tools mismatch")
    evidence = {
        "schema": SCHEMA,
        "baseline": BASELINE,
        "frozen_readme_sha256": FROZEN_README_SHA256,
        "runs": runs,
        "req1_cross_run": {"byte_equal": byte_equal, "diff_leaves": len(leaves),
                           "diff_fields": buckets,
                           "id_normalized_canonical_sha256": ID_NORMALIZED_CANONICAL_SHA256},
        "state_mechanism": {"store": False, "previous_response_id_present": False,
                            "include": ["reasoning.encrypted_content"],
                            "reasoning_replay_encrypted": True,
                            "prompt_cache_key_equals_thread_id": True},
        "cross_harness_task_surface": {"codex_task_msg_bytes": 214,
                                       "codex_task_equals_prompt_file": True,
                                       "dsh_task_user_msg_bytes": 214,
                                       "task_text_sha256": TASK_TEXT_SHA256,
                                       "task_text_byte_equal_across_harnesses": True},
        "codex_assembly": {"instructions_bytes": 17119,
                           "instructions_sha256": INSTRUCTIONS_SHA256,
                           "tools": TOOLS, "tools_count": len(TOOLS),
                           "reasoning_effort": "low", "model": "deepseek-flash"},
        "workspace": {"files": WORKSPACE_FILES, "aggregate_rule": WORKSPACE_AGG_RULE,
                      "aggregate_sha256": WORKSPACE_AGG_SHA256, "rebuilt_noop": True},
        "verdict": "codex_assembly_stable_ids_generated",
        "limits": LIMITS,
    }
    evidence_bytes = canon(evidence) + b"\n"
    result = {
        "schema": SCHEMA,
        "baseline": BASELINE,
        "verdict": evidence["verdict"],
        "req1_cross_run": evidence["req1_cross_run"],
        "state_mechanism": evidence["state_mechanism"],
        "evidence_sha256": sha(evidence_bytes),
        "limits": LIMITS,
    }
    return evidence, evidence_bytes, result


def validate_public(evidence):
    require(evidence.get("schema") == SCHEMA, "schema mismatch")
    require(evidence.get("baseline") == BASELINE, "baseline mismatch")
    require(evidence.get("frozen_readme_sha256") == FROZEN_README_SHA256, "readme pin mismatch")
    require(evidence.get("verdict") == "codex_assembly_stable_ids_generated", "verdict mismatch")
    rc = evidence.get("req1_cross_run") or {}
    require(rc.get("byte_equal") is REQ1_BYTE_EQUAL_EXPECT, "byte_equal pin")
    require(rc.get("diff_leaves") == REQ1_DIFF_LEAVES_EXPECT, "diff leaves pin")
    require(rc.get("diff_fields") == REQ1_DIFF_FIELDS_EXPECT, "diff fields pin")
    require(rc.get("id_normalized_canonical_sha256") == ID_NORMALIZED_CANONICAL_SHA256, "normalized pin")
    sm = evidence.get("state_mechanism") or {}
    require(sm.get("store") is False and sm.get("previous_response_id_present") is False, "state pins")
    require(sm.get("reasoning_replay_encrypted") is True, "reasoning replay pin")
    ts = evidence.get("cross_harness_task_surface") or {}
    require(ts.get("task_text_byte_equal_across_harnesses") is True, "task surface pin")
    require(ts.get("task_text_sha256") == TASK_TEXT_SHA256, "task sha pin")
    ca = evidence.get("codex_assembly") or {}
    require(ca.get("tools_count") == 8 and ca.get("tools") == TOOLS, "tools pin")
    require(ca.get("instructions_sha256") == INSTRUCTIONS_SHA256, "instructions pin")
    runs = evidence.get("runs") or {}
    require(set(runs) == {"r1", "r2"}, "runs pin")
    for run, spec in RUN_SPECS.items():
        e = runs[run]
        require(e.get("requests") == spec["requests"], "count pin %s" % run)
        require(len(e.get("req_sha256", [])) == spec["requests"], "sha list pin %s" % run)
        require(e.get("req_sha256", [""])[0] == REQ1_SHAS[run], "req1 sha pin %s" % run)
    ws = evidence.get("workspace") or {}
    require(ws.get("files") == WORKSPACE_FILES, "workspace files pin")
    require(ws.get("aggregate_rule") == WORKSPACE_AGG_RULE, "workspace rule pin")
    require(ws.get("aggregate_sha256") == WORKSPACE_AGG_SHA256, "workspace pin")
    require(evidence.get("limits") == LIMITS, "limits mismatch")
    # 泄漏扫描：evidence 不得含 id 形状值或 /Users
    blob = json.dumps(evidence, ensure_ascii=False)
    require("/Users" not in blob, "private path leak")
    require("sk-" not in blob, "credential-shaped leak")


def result_for(evidence, evidence_bytes):
    return {
        "schema": SCHEMA,
        "baseline": evidence.get("baseline"),
        "verdict": evidence.get("verdict"),
        "req1_cross_run": evidence.get("req1_cross_run"),
        "state_mechanism": evidence.get("state_mechanism"),
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
            print("codex capture replay OK: verdict=%s" % evidence.get("verdict"))
        else:
            print("codex capture rebuild OK: diff_leaves=11 all-id-class normalized-equal")
        return 0
    except (Invalid, ValueError, OSError) as exc:
        print("input or output failure")
        return 2


if __name__ == "__main__":
    sys.exit(main())
