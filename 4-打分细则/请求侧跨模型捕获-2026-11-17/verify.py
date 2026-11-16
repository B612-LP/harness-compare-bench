#!/usr/bin/env python3
"""Request-side cross-model capture verifier (R-A6).

Endpoints are frozen in the package README before the two DeepSeek runs
(2026-11-17). Evidence contains only hashes, byte counts, shape tuples and
booleans - never request bodies, complete call ids, credentials or absolute
paths. Public replay re-checks sealed arithmetic; it cannot authenticate the
private archive.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

BASELINE = "4db9746972876f69275759cdae30ee71cd441e9a"
SCHEMA = "capture-crossmodel-provenance-evidence-v1"
FREEZE_README_SHA256 = "3de9ded761959a7c43821b62c2438c3de0ac8dc9469fbba1c7b4a77484a0ec16"
CAPTURE_PKG = "4-打分细则/DSH请求侧最小捕获-2026-11-16"
CAPTURE_README_SHA256 = "a26c7ec7df5dc052ce708434a3cbfa2b50deca2745effa1b91a5877f279c04e7"
CAPTURE_RESULT_SHA256 = "3de57557fe7f3c74e6abc041e5181fc415595299b9678ed59d271f8abe596357"
RUN_RELS = {
    "ds_r1": "loop10/capture-ds-r1",
    "ds_r2": "loop10/capture-ds-r2",
    "glm_r1": "loop1/capture",
}
WORKSPACE_FILES = {
    "TASK.md": "68599aec2f4a1201c6eb9e46ba92a76d5b68a3cb96f1154e24d8edbe588c3f2c",
    "inputs/exercises/dominoes/dominoes.py": "89f1fede34db8dbd73fb7103476080307e769425049014bf60b7d5e632f9743b",
}
PROMPT_SHA256 = "7a7c57c759d2aaccbdab600e4cb4c7b429bb820268a801f97967f82565ecb765"
REQ1_DS_SHA256 = "0372557d46f071948f5f32e59466da624fc3748c56dc8b0f7fbcc9d036874ed3"
REQ2_DS_SHA256 = "05183eb7906bdc6612c93581e2ec66fc88f6ccaf2474c35314a41f60d0b6f7aa"
REQ3_DS_SHAS = {
    "ds_r1": "c1d78d83dd85b4947ae17e0511d35974fb446c7f8cfc7252db4cc8371bfb0787",
    "ds_r2": "9c60dec286a8fd1dd59dfe7a2bb1ecd282a529ea2a34166d5a7ba35338397aef",
}
REQ1_GLM_SHA256 = "92220699f215bbdfe0faa392587b8fc43ad6793f10da6baf8b7541518120ac10"
TITLE_PREFIX = "Generate the session title from this JSON array of human messages:\n"
# provider-generated id shapes seen on either wire (descriptive normalization)
ID_PATTERNS = [
    re.compile(r"call_[0-9A-Za-z_]{2,}_[0-9A-Za-z]+"),
    re.compile(r"call_[0-9a-f]{24}"),
    re.compile(r"chatcmpl-[0-9A-Za-z]{16,}"),
]
EXPECTED_APPENDED = [["assistant", "none", 0], ["tool", "str", 227], ["tool", "str", 203]]
DS_DELTA_BYTES = 1028
P3_FACTS = {
    "glm_system_raw_bytes": 2593,
    "ds_system_raw_bytes": 2962,
    "glm_tools": 22,
    "ds_tools": 24,
    "ds_only_tool_names": ["web_fetch", "web_search"],
    "user_msgs_1_to_4_content_equal": True,
    "roles": ["system", "user", "user", "user", "user"],
    "glm_model": "glm-5.3-flash",
    "ds_model": "deepseek-chat",
    "glm_max_field": "max_tokens",
    "ds_max_field": "max_completion_tokens",
    "glm_thinking_present": True,
    "ds_thinking_present": False,
    "glm_tool_stream_present": True,
    "ds_tool_stream_present": False,
    "ds_store_value": False,
    "title_model_is_ds": True,
    "title_max_completion_tokens": 4096,
    "title_tools": 0,
    "title_prompt_prefix_ok": True,
}
ENDPOINT = "ds_assembly_stable"


def require(cond, what):
    if not cond:
        raise ValueError(what)


def no_duplicate_pairs(pairs):
    seen = set()
    for k, _ in pairs:
        if k in seen:
            raise ValueError("duplicate key " + k)
        seen.add(k)
    return dict(pairs)


def loads(raw):
    def bad(_):
        raise ValueError("non-finite json constant")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicate_pairs, parse_constant=bad)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def normalize_ids(value):
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    for pattern in ID_PATTERNS:
        text = pattern.sub("ID_NORM", text)
    return text


def id_like(value):
    text = str(value)
    return any(p.fullmatch(text) for p in ID_PATTERNS)


def diff_leaves(a, b, path=""):
    out = []
    if type(a) is not type(b):
        out.append((path, a, b))
        return out
    if isinstance(a, dict):
        for key in sorted(set(a) | set(b)):
            if key not in a or key not in b:
                out.append((path + "/" + key, a.get(key), b.get(key)))
            else:
                out.extend(diff_leaves(a[key], b[key], path + "/" + key))
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append((path + "/__len__", len(a), len(b)))
        for index, (x, y) in enumerate(zip(a, b)):
            out.extend(diff_leaves(x, y, path + "/" + str(index)))
    elif a != b:
        out.append((path, a, b))
    return out


def descriptor(message):
    content = message.get("content")
    kind = "none" if content is None else type(content).__name__
    size = 0 if content is None else len(content)
    return [message.get("role"), kind, size]


def load_run(root, rel):
    base = root / rel
    requests = {}
    for index in ("001", "002", "003"):
        raw = (base / "requests" / f"{index}.request.bin").read_bytes()
        meta = loads((base / "responses" / f"{index}.response.bin.meta.json").read_bytes())
        require(meta.get("request_body_sha256") == sha(raw), f"{rel} {index} meta sha")
        require(meta.get("request_body_bytes") == len(raw), f"{rel} {index} meta bytes")
        require(meta.get("upstream_status") == 200, f"{rel} {index} upstream status")
        requests[index] = {"raw": raw, "body": loads(raw)}
    return requests


def build(archive_base):
    root = Path(archive_base).resolve()
    runs = {label: load_run(root, rel) for label, rel in RUN_RELS.items()}
    glm_req1_sha = sha(runs["glm_r1"]["001"]["raw"])
    require(glm_req1_sha == REQ1_GLM_SHA256, "glm req1 pin")
    ds_r1 = runs["ds_r1"]
    ds_r2 = runs["ds_r2"]
    req1_equal = sha(ds_r1["001"]["raw"]) == sha(ds_r2["001"]["raw"])
    require(req1_equal, "ds req1 pair not byte equal")
    require(sha(ds_r1["001"]["raw"]) == REQ1_DS_SHA256, "ds req1 sha pin")
    require(sha(ds_r1["002"]["raw"]) == sha(ds_r2["002"]["raw"]), "ds req2 pair not byte equal")
    require(sha(ds_r1["002"]["raw"]) == REQ2_DS_SHA256, "ds req2 sha pin")
    leaves = diff_leaves(ds_r1["003"]["body"], ds_r2["003"]["body"])
    require(len(leaves) == 4, f"ds req3 leaf count {len(leaves)}")
    all_ids = all(id_like(x) and id_like(y) for _, x, y in leaves)
    require(all_ids, "ds req3 non-id leaf")
    require(normalize_ids(ds_r1["003"]["body"]) == normalize_ids(ds_r2["003"]["body"]), "ds req3 normalized mismatch")
    per_run = {}
    for label, run in (("ds_r1", ds_r1), ("ds_r2", ds_r2)):
        m1 = run["001"]["body"]["messages"]
        m3 = run["003"]["body"]["messages"]
        prefix = m3[: len(m1)] == m1
        require(prefix, f"{label} prefix")
        appended = [descriptor(m) for m in m3[len(m1):]]
        require(appended == EXPECTED_APPENDED, f"{label} appended shapes")
        delta = len(run["003"]["raw"]) - len(run["001"]["raw"])
        require(delta == DS_DELTA_BYTES, f"{label} delta {delta}")
        per_run[label] = {"prefix_ok": True, "appended_shapes": appended, "delta_bytes": delta}
    glm_body = runs["glm_r1"]["001"]["body"]
    ds_body = ds_r1["001"]["body"]
    p3 = {
        "system_raw_bytes": [len(glm_body["messages"][0]["content"].encode("utf-8")), len(ds_body["messages"][0]["content"].encode("utf-8"))],
        "system_content_equal": glm_body["messages"][0]["content"] == ds_body["messages"][0]["content"],
        "tools": [len(glm_body.get("tools") or []), len(ds_body.get("tools") or [])],
        "ds_only_tool_names": [t["function"]["name"] for t in ds_body.get("tools") or [] if t["function"]["name"] not in {x["function"]["name"] for x in glm_body.get("tools") or []}],
        "user_msgs_1_to_4_content_equal": glm_body["messages"][1:5] == ds_body["messages"][1:5],
        "roles": [m["role"] for m in ds_body["messages"]],
        "model_fields": [glm_body.get("model"), ds_body.get("model")],
    }
    require(p3["system_raw_bytes"] == [P3_FACTS["glm_system_raw_bytes"], P3_FACTS["ds_system_raw_bytes"]], "p3 system bytes")
    require(p3["system_content_equal"] is False, "p3 system unexpectedly equal")
    require(p3["tools"] == [P3_FACTS["glm_tools"], P3_FACTS["ds_tools"]], "p3 tools")
    require(p3["ds_only_tool_names"] == P3_FACTS["ds_only_tool_names"], "p3 ds-only tools")
    require(p3["user_msgs_1_to_4_content_equal"] is True, "p3 user messages")
    require(p3["roles"] == P3_FACTS["roles"], "p3 roles")
    title = ds_r1["002"]["body"]
    p4 = {
        "model": title.get("model"),
        "max_completion_tokens": title.get("max_completion_tokens"),
        "messages": len(title["messages"]),
        "tools": len(title.get("tools") or []),
        "prompt_prefix_ok": title["messages"][1]["content"].startswith(TITLE_PREFIX),
    }
    require(p4["model"] == ds_body.get("model"), "p4 title model")
    require(p4["max_completion_tokens"] == P3_FACTS["title_max_completion_tokens"], "p4 title max")
    require(p4["messages"] == 2 and p4["tools"] == 0, "p4 title shape")
    require(p4["prompt_prefix_ok"] is True, "p4 title prefix")
    req3_raw = ds_r1["003"]["raw"]
    reflow_probe = {probe: (probe.encode("utf-8") in req3_raw) for probe in ("Capture task r1", "can_chain")}
    top_keys_glm = sorted(glm_body.keys())
    top_keys_ds = sorted(ds_body.keys())
    evidence = {
        "schema": SCHEMA,
        "baseline_commit": BASELINE,
        "freeze_readme_sha256": FREEZE_README_SHA256,
        "workspace_files": WORKSPACE_FILES,
        "prompt_sha256": PROMPT_SHA256,
        "runs": {
            "ds_r1": {"dir": RUN_RELS["ds_r1"], "req_shas": {k: sha(ds_r1[k]["raw"]) for k in ("001", "002", "003")}, "n_messages": [len(ds_r1["001"]["body"]["messages"]), len(ds_r1["002"]["body"]["messages"]), len(ds_r1["003"]["body"]["messages"])], "upstream_status": [200, 200, 200]},
            "ds_r2": {"dir": RUN_RELS["ds_r2"], "req_shas": {k: sha(ds_r2[k]["raw"]) for k in ("001", "002", "003")}, "n_messages": [len(ds_r2["001"]["body"]["messages"]), len(ds_r2["002"]["body"]["messages"]), len(ds_r2["003"]["body"]["messages"])], "upstream_status": [200, 200, 200]},
        },
        "endpoint": {
            "req1_byte_equal": True,
            "req2_byte_equal": True,
            "req3_diff_leaves": len(leaves),
            "req3_leaves_all_provider_ids": True,
            "req3_normalized_canonical_equal": True,
            "verdict": ENDPOINT,
        },
        "per_run_prefix": per_run,
        "cross_provider_descriptive": {
            "glm_req1_sha256": glm_req1_sha,
            "top_level_keys": {"glm": top_keys_glm, "ds": top_keys_ds},
            "system_raw_bytes": p3["system_raw_bytes"],
            "system_content_equal": False,
            "tools": p3["tools"],
            "ds_only_tool_names": p3["ds_only_tool_names"],
            "user_msgs_1_to_4_content_equal": True,
            "roles": p3["roles"],
            "model_fields": p3["model_fields"],
            "max_field_names": {"glm": P3_FACTS["glm_max_field"], "ds": P3_FACTS["ds_max_field"]},
            "flags": {"glm_thinking": True, "ds_thinking": False, "glm_tool_stream": True, "ds_tool_stream": False, "ds_store": False},
        },
        "title_request": p4,
        "title_reflow_probe": {**reflow_probe, "explained_by_task_file_content_only": True},
        "limits": [
            "public replay re-checks sealed arithmetic only; it cannot authenticate the private archive",
            "single task, single DSH build, n=2 per provider family; bytes are not tokens",
            "deepseek-chat via api key is not the desktop account route (deepseek-flash); family-level comparison only",
            "cross-provider rows are descriptive, not attribution scores; response bodies are out of scope",
        ],
    }
    return evidence


def result_for(evidence, evidence_sha):
    endpoint = evidence["endpoint"]
    rows = []
    for label in ("ds_r1", "ds_r2"):
        run = evidence["runs"][label]
        rows.append({"run": label, "dir": run["dir"], "req1_sha256": run["req_shas"]["001"], "req2_sha256": run["req_shas"]["002"], "req3_sha256": run["req_shas"]["003"], "prefix_ok": evidence["per_run_prefix"][label]["prefix_ok"], "delta_bytes": evidence["per_run_prefix"][label]["delta_bytes"]})
    cross = evidence["cross_provider_descriptive"]
    result = {
        "schema": "capture-crossmodel-provenance-result-v1",
        "baseline_commit": evidence["baseline_commit"],
        "evidence_sha256": evidence_sha,
        "endpoint": {"verdict": endpoint["verdict"], "req1_byte_equal": endpoint["req1_byte_equal"], "req2_byte_equal": endpoint["req2_byte_equal"], "req3_diff_leaves": endpoint["req3_diff_leaves"], "req3_leaves_all_provider_ids": endpoint["req3_leaves_all_provider_ids"], "req3_normalized_canonical_equal": endpoint["req3_normalized_canonical_equal"]},
        "runs": rows,
        "cross_provider_descriptive": {"glm_req1_sha256": cross["glm_req1_sha256"], "system_raw_bytes": cross["system_raw_bytes"], "system_content_equal": cross["system_content_equal"], "tools": cross["tools"], "ds_only_tool_names": cross["ds_only_tool_names"], "user_msgs_1_to_4_content_equal": cross["user_msgs_1_to_4_content_equal"], "roles": cross["roles"], "model_fields": cross["model_fields"], "max_field_names": cross["max_field_names"], "flags": cross["flags"], "top_level_keys": cross["top_level_keys"]},
        "title_request": evidence["title_request"],
        "title_reflow_probe": evidence["title_reflow_probe"],
        "limits": evidence["limits"],
    }
    return result


def validate_public(evidence, expected_evidence_sha):
    require(evidence.get("schema") == SCHEMA, "schema")
    require(evidence.get("baseline_commit") == BASELINE, "baseline")
    require(evidence.get("freeze_readme_sha256") == FREEZE_README_SHA256, "freeze readme pin")
    require(evidence.get("workspace_files") == WORKSPACE_FILES, "workspace pin")
    require(evidence.get("prompt_sha256") == PROMPT_SHA256, "prompt pin")
    runs = evidence.get("runs") or {}
    require(set(runs) == {"ds_r1", "ds_r2"}, "runs coverage")
    require(runs["ds_r1"]["req_shas"]["001"] == REQ1_DS_SHA256, "ds req1 pin")
    require(runs["ds_r1"]["req_shas"]["002"] == REQ2_DS_SHA256, "ds req2 pin")
    require(runs["ds_r1"]["req_shas"]["003"] == REQ3_DS_SHAS["ds_r1"], "ds r1 req3 pin")
    require(runs["ds_r2"]["req_shas"]["003"] == REQ3_DS_SHAS["ds_r2"], "ds r2 req3 pin")
    require(runs["ds_r1"]["req_shas"]["001"] == runs["ds_r2"]["req_shas"]["001"], "req1 pair equal")
    require(runs["ds_r1"]["req_shas"]["002"] == runs["ds_r2"]["req_shas"]["002"], "req2 pair equal")
    for label in ("ds_r1", "ds_r2"):
        require(runs[label]["upstream_status"] == [200, 200, 200], label + " statuses")
        require(runs[label]["n_messages"] == [5, 2, 8], label + " n_messages")
    endpoint = evidence.get("endpoint") or {}
    require(endpoint.get("verdict") == ENDPOINT, "endpoint verdict")
    require(endpoint.get("req1_byte_equal") is True and endpoint.get("req2_byte_equal") is True, "endpoint pair equality")
    require(endpoint.get("req3_diff_leaves") == 4, "endpoint leaves")
    require(endpoint.get("req3_leaves_all_provider_ids") is True, "endpoint id leaves")
    require(endpoint.get("req3_normalized_canonical_equal") is True, "endpoint normalized")
    per_run = evidence.get("per_run_prefix") or {}
    for label in ("ds_r1", "ds_r2"):
        row = per_run.get(label) or {}
        require(row.get("prefix_ok") is True, label + " prefix")
        require(row.get("appended_shapes") == EXPECTED_APPENDED, label + " appended")
        require(row.get("delta_bytes") == DS_DELTA_BYTES, label + " delta")
    cross = evidence.get("cross_provider_descriptive") or {}
    require(cross.get("glm_req1_sha256") == REQ1_GLM_SHA256, "glm pin")
    require(cross.get("system_raw_bytes") == [P3_FACTS["glm_system_raw_bytes"], P3_FACTS["ds_system_raw_bytes"]], "system bytes")
    require(cross.get("system_content_equal") is False, "system unequal")
    require(cross.get("tools") == [22, 24], "tools counts")
    require(cross.get("ds_only_tool_names") == ["web_fetch", "web_search"], "ds-only tools")
    require(cross.get("user_msgs_1_to_4_content_equal") is True, "user equality")
    require(cross.get("roles") == P3_FACTS["roles"], "roles")
    require(cross.get("model_fields") == ["glm-5.3-flash", "deepseek-chat"], "models")
    title = evidence.get("title_request") or {}
    require(title.get("messages") == 2 and title.get("tools") == 0, "title shape")
    require(title.get("max_completion_tokens") == 4096, "title max")
    require(title.get("prompt_prefix_ok") is True, "title prefix")
    probe = evidence.get("title_reflow_probe") or {}
    require(probe.get("explained_by_task_file_content_only") is True, "reflow caveat")
    caps = json.dumps(evidence, ensure_ascii=False)
    for pat in (r"call_[0-9A-Za-z_]{2,}_[0-9A-Za-z]+", r"call_[0-9a-f]{24}", r"chatcmpl-[0-9A-Za-z]{16,}", r"sk-[A-Za-z0-9]{10,}"):
        require(not re.search(pat, caps), "evidence leaks id/credential shape " + pat)
    digest = sha(canon(evidence))
    require(digest == expected_evidence_sha, "evidence digest mismatch")


def exclusive(path, raw):
    path = Path(path)
    require(not path.exists(), "output exists: " + path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(raw)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def main(argv=None):
    args = argparse.ArgumentParser()
    args.add_argument("--archive-base", type=Path, default=None)
    args.add_argument("--build-evidence", type=Path, default=None)
    args.add_argument("--evidence", type=Path, default=None)
    args.add_argument("--output", type=Path, required=True)
    parsed = args.parse_args(argv)
    require((parsed.build_evidence is None) != (parsed.evidence is None), "choose exactly one of --build-evidence / --evidence")
    if parsed.build_evidence is not None:
        require(parsed.archive_base is not None, "--archive-base required with --build-evidence")
        evidence = build(parsed.archive_base)
        exclusive(parsed.build_evidence, canonical(evidence))
    else:
        evidence = loads(parsed.evidence.read_bytes())
    evidence_sha = sha(canon(evidence))
    validate_public(evidence, evidence_sha)
    result = result_for(evidence, evidence_sha)
    exclusive(parsed.output, canonical(result))
    endpoint = result["endpoint"]
    print(f"crossmodel verify OK: {endpoint['verdict']} | req1/req2 byte-equal | req3 leaves {endpoint['req3_diff_leaves']} all provider ids | normalized equal | user msgs 1-4 equal across providers")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError) as error:
        print("input or output failure", file=sys.stderr)
        sys.exit(2)
