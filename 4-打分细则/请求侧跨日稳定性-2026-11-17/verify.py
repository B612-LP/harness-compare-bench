#!/usr/bin/env python3
"""Cross-day request-side stability + credential-surface attribution (2026-11-17).

Two real runs, same app build / profile / workspace / prompt bytes:
  runA (attempt4): env WITH DEEPSEEK_API_KEY -> req1 drifts vs 2026-11-16
  runB (attempt5): env WITHOUT DEEPSEEK_API_KEY -> req1/aux byte-identical to prior
Preregistered expectation (FREEZE-AMENDMENT-2): req1(B) == prior req1 SHA;
falsifier = still differs.

Private rebuild (--archive-root) reads loop22/capture; public replay re-checks
pins and structure only. Prior anchors are the published SHAs of
DSH请求侧最小捕获-2026-11-16. Stdlib only; fail-closed (exit 2 on Invalid).
"""
import argparse, hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASELINE = "7b0353b2389121ef5d46dd0eea23fa32d11c09aa"
SCHEMA = "crossday-stability-evidence-v1"

PRIOR = {
    "req1": {"sha256": "92220699f215bbdfe0faa392587b8fc43ad6793f10da6baf8b7541518120ac10", "bytes": 33091},
    "aux":  {"sha256": "9f2b6b3e9b76dde704dd763efc1e60992ec2c798c987ae577c784ddd63e34e76", "bytes": 1042},
    "req3": {"sha256": "19e98d96ebfb3ade2dac6315b2f61f8fe45d50dcc9dca9fb8c888213cf06b8b4", "bytes": 34107},
}
PROMPT_SHA = "7a7c57c759d2aaccbdab600e4cb4c7b429bb820268a801f97967f82565ecb765"
PROMPT_BYTES = 214
WORKSPACE_FILES = {
    "TASK.md": "68599aec2f4a1201c6eb9e46ba92a76d5b68a3cb96f1154e24d8edbe588c3f2c",
    "inputs/exercises/dominoes/dominoes.py": "89f1fede34db8dbd73fb7103476080307e769425049014bf60b7d5e632f9743b",
}
PRIOR_REQ1_SHA = PRIOR["req1"]["sha256"]
ADDED_TOOLS = ["web_fetch", "web_search"]
SYS_ADDED_LINE_BYTES = [215, 150]
EXPECTED_DIFF_LEAVES_RUNB_REQ3 = [
    ["/messages/5/tool_calls/0/id", "value"],
    ["/messages/5/tool_calls/1/id", "value"],
    ["/messages/6/tool_call_id", "value"],
    ["/messages/7/tool_call_id", "value"],
]
RUNS = {
    "runA": {"env_deepseek_key": True, "seqs": [1, 2, 3], "rows": ["001", "002", "003"]},
    "runB": {"env_deepseek_key": False, "seqs": [4, 5, 6], "rows": ["004", "005", "006"]},
}
FROZEN_META = {
    "asar_mtime": "2026-11-13 15:31:48",
    "app_version": "0.2.2-rc.3",
    "upstream": "https://open.bigmodel.cn:443",
    "profile": "capture-r1",
    "proxy_listen": "127.0.0.1:8791",
}
CLASSIFICATION = "cross_day_drift_attributed_to_credential_conditional_web_tool_surface"


class Invalid(Exception):
    pass


def require(cond, msg):
    if not cond:
        raise Invalid(msg)


def no_duplicate_keys(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise Invalid("duplicate key %r" % (k,))
        out[k] = v
    return out


def _reject(s):
    raise Invalid("non-finite constant")


def _reject_float(s):
    raise Invalid("non-finite float")


def loads(raw):
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicate_keys, parse_constant=_reject, parse_float=_reject_float)
    except Invalid:
        raise
    except Exception as e:
        raise Invalid("bad json: %s" % e)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def integer(value, minimum=0):
    require(isinstance(value, int) and not isinstance(value, bool) and value >= minimum, "bad integer")
    return value


def safe_path(root, relative):
    root = os.path.realpath(root)
    path = os.path.realpath(os.path.join(root, relative))
    require(path == root or path.startswith(root + os.sep), "path escape")
    return path


def exclusive(path, raw):
    require(not os.path.exists(path), "output exists: %s" % path)
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        os.write(fd, raw)
    finally:
        os.close(fd)


def request_roles(body):
    roles = []
    for m in body["messages"]:
        c = m.get("content")
        n = len(c.encode("utf-8")) if isinstance(c, str) else 0
        roles.append([m.get("role"), n])
    return roles


def project_request(raw, seq, summary_row):
    body = loads(raw)
    require(isinstance(body, dict), "request not object")
    thinking = (body.get("thinking") or {}).get("type")
    tools = body.get("tools", [])
    require(summary_row["request_body_bytes"] == len(raw), "summary bytes mismatch")
    require(summary_row["upstream_status"] == 200, "non-200")
    require(summary_row["method"] == "POST", "method")
    return {
        "seq": seq,
        "bytes": len(raw),
        "sha256": sha(raw),
        "roles": request_roles(body),
        "n_messages": len(body["messages"]),
        "tools_count": len(tools),
        "tools_digest": digest(tools),
        "thinking_type": thinking,
        "max_tokens": integer(body.get("max_tokens"), 1),
        "params_other_digest": digest({k: body[k] for k in sorted(body.keys()) if k not in ("messages", "tools")}),
    }


def parse_summary(root):
    rows = {}
    for line in open(safe_path(root, "summary.jsonl"), "rb").read().decode("utf-8").splitlines():
        if not line.strip():
            continue
        r = loads(line.encode("utf-8"))
        require(isinstance(r, dict) and isinstance(r.get("seq"), int), "bad summary row")
        rows[r["seq"]] = r
    return rows


def run_projection(root, spec, summary):
    reqs = []
    for row, seq in zip(spec["rows"], spec["seqs"]):
        raw = open(safe_path(root, "requests/%s.request.bin" % row), "rb").read()
        s = summary.get(seq)
        require(s is not None, "summary missing seq %s" % seq)
        reqs.append(project_request(raw, seq, s))
    b0 = loads(open(safe_path(root, "requests/%s.request.bin" % spec["rows"][0]), "rb").read())
    b2 = loads(open(safe_path(root, "requests/%s.request.bin" % spec["rows"][2]), "rb").read())
    l0 = len(b0["messages"])
    return {
        "env_deepseek_key": spec["env_deepseek_key"],
        "requests": reqs,
        "prefix": {
            "prefix_messages_equal": b0["messages"] == b2["messages"][:l0],
            "appended_messages": len(b2["messages"]) - l0,
            "non_message_keys_equal": {k: v for k, v in b0.items() if k != "messages"} == {k: v for k, v in b2.items() if k != "messages"},
            "delta_bytes": reqs[2]["bytes"] - reqs[0]["bytes"],
        },
    }


def build(root):
    proxy = loads(open(safe_path(root, "PROXY-START.json"), "rb").read())
    require(proxy.get("upstream") == FROZEN_META["upstream"], "upstream changed")
    require(proxy.get("listen") == FROZEN_META["proxy_listen"], "proxy listen changed")
    summary = parse_summary(root)
    runs = {name: run_projection(root, spec, summary) for name, spec in RUNS.items()}
    bodyA = loads(open(safe_path(root, "requests/001.request.bin"), "rb").read())
    bodyB = loads(open(safe_path(root, "requests/004.request.bin"), "rb").read())
    toolsA = bodyA.get("tools", [])
    tool_names_new = sorted(t["function"]["name"] for t in toolsA)
    sysA = bodyA["messages"][0]["content"].splitlines()
    sysB = bodyB["messages"][0]["content"].splitlines()
    sys_line_deltas = [["added", len(l.encode("utf-8"))] for l in sysA if l not in sysB]
    removed = [l for l in sysB if l not in sysA]
    n = min(len(bodyA["messages"]), len(bodyB["messages"]))
    user_same = n >= 5 and all(bodyA["messages"][i] == bodyB["messages"][i] for i in range(1, 5))
    b_req1 = runs["runB"]["requests"][0]
    b_aux = runs["runB"]["requests"][1]
    b_req3 = runs["runB"]["requests"][2]
    ident_req1 = b_req1["sha256"] == PRIOR_REQ1_SHA and b_req1["bytes"] == PRIOR["req1"]["bytes"]
    ident_aux = b_aux["sha256"] == PRIOR["aux"]["sha256"] and b_aux["bytes"] == PRIOR["aux"]["bytes"]
    same_bytes_req3 = b_req3["bytes"] == PRIOR["req3"]["bytes"]
    diff_leaves = []
    _priv = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(root))))
    prior_path = os.path.join(_priv, "until14-20261117", "loop1", "capture", "requests", "003.request.bin")
    bodyB3 = loads(open(safe_path(root, "requests/006.request.bin"), "rb").read())
    if os.path.isfile(prior_path):
        prior_raw = open(prior_path, "rb").read()
        # Content is trusted only after SHA-pin verification against the published prior.
        if sha(prior_raw) != PRIOR["req3"]["sha256"]:
            raise Invalid("prior req3 sha mismatch")
        prior_body = loads(prior_raw)
    else:
        raise Invalid("prior archive file missing")

    def walk(x, y, path):
        if type(x) is not type(y):
            diff_leaves.append([path, "type"])
            return
        if isinstance(x, dict):
            for k in sorted(set(x) | set(y)):
                if k not in x or k not in y:
                    diff_leaves.append([path + "/" + k, "side_only"])
                else:
                    walk(x[k], y[k], path + "/" + k)
        elif isinstance(x, list):
            if len(x) != len(y):
                diff_leaves.append([path, "len"])
            for i, (u, v) in enumerate(zip(x, y)):
                walk(u, v, "%s/%d" % (path, i))
        elif x != y:
            diff_leaves.append([path, "value"])
    walk(prior_body, bodyB3, "")
    return {
        "schema": SCHEMA,
        "baseline_head": BASELINE,
        "meta": {
            "app_asar_mtime": FROZEN_META["asar_mtime"],
            "app_version": FROZEN_META["app_version"],
            "upstream": FROZEN_META["upstream"],
            "profile": FROZEN_META["profile"],
            "proxy_listen": proxy.get("listen"),
            "prompt_sha256": PROMPT_SHA,
            "prompt_bytes": PROMPT_BYTES,
            "workspace_files": WORKSPACE_FILES,
            "prior_req1_sha256": PRIOR_REQ1_SHA,
        },
        "runs": runs,
        "e1_crossday_with_credentials": {
            "req1_sha256": runs["runA"]["requests"][0]["sha256"],
            "req1_bytes": runs["runA"]["requests"][0]["bytes"],
            "identical_to_prior": runs["runA"]["requests"][0]["sha256"] == PRIOR_REQ1_SHA,
            "tools_count": [22, len(toolsA)],
            "tool_names_added": [x for x in tool_names_new if x in ADDED_TOOLS],
            "system_added_line_bytes": sys_line_deltas,
            "system_removed_lines": len(removed),
            "user_messages_1_to_4_identical": user_same,
            "params_non_message_identical": {k: v for k, v in bodyA.items() if k not in ("messages", "tools")} == {k: v for k, v in bodyB.items() if k not in ("messages", "tools")},
        },
        "e1b_crossday_fixed_credential": {
            "req1_identical": ident_req1,
            "aux_identical": ident_aux,
            "req3_same_bytes": same_bytes_req3,
            "req3_diff_leaves": diff_leaves,
        },
        "attribution": {
            "expectation_met": ident_req1 and ident_aux,
            "falsifier_triggered": ident_req1 is False,
            "classification": CLASSIFICATION,
        },
        "boundaries": ["n=1 per arm", "bytes are transport-level, not tokens",
                       "identity does not prove model behavior unchanged",
                       "web tools present != web tools used"],
    }


def validate_public(doc):
    require(isinstance(doc, dict), "not object")
    require(doc.get("schema") == SCHEMA, "schema")
    require(doc.get("baseline_head") == BASELINE, "baseline")
    meta = doc["meta"]
    require(meta["app_asar_mtime"] == FROZEN_META["asar_mtime"], "asar mtime pin")
    require(meta["app_version"] == FROZEN_META["app_version"], "version pin")
    require(meta["upstream"] == FROZEN_META["upstream"], "upstream pin")
    require(meta["profile"] == FROZEN_META["profile"], "profile pin")
    require(meta["proxy_listen"] == FROZEN_META["proxy_listen"], "proxy pin")
    require(meta["prompt_sha256"] == PROMPT_SHA and meta["prompt_bytes"] == PROMPT_BYTES, "prompt pin")
    require(meta["workspace_files"] == WORKSPACE_FILES, "workspace pin")
    require(meta["prior_req1_sha256"] == PRIOR_REQ1_SHA, "prior anchor pin")
    runs = doc["runs"]
    require(sorted(runs) == ["runA", "runB"], "runs")
    require(runs["runA"]["env_deepseek_key"] is True and runs["runB"]["env_deepseek_key"] is False, "env flags")
    for name, spec in RUNS.items():
        rs = runs[name]["requests"]
        require(len(rs) == 3, "three requests")
        for r, seq in zip(rs, spec["seqs"]):
            require(r["seq"] == seq, "seq order")
            integer(r["bytes"], 1)
            require(len(r["sha256"]) == 64, "sha shape")
            require(r["thinking_type"] in ("disabled", "enabled"), "thinking")
            require(r["tools_count"] in (0, 22, 24), "tool count")
        px = runs[name]["prefix"]
        require(px["appended_messages"] == 3 and px["delta_bytes"] > 0, "prefix shape")
        require(px["prefix_messages_equal"] is True and px["non_message_keys_equal"] is True, "prefix identity")
    e1 = doc["e1_crossday_with_credentials"]
    require(e1["identical_to_prior"] is False, "runA drift fact")
    require(e1["tools_count"] == [22, 24], "tools count pair")
    require(e1["tool_names_added"] == ADDED_TOOLS, "added tools pin")
    require(e1["user_messages_1_to_4_identical"] is True, "user messages identical fact")
    require(sorted(b for tag, b in e1["system_added_line_bytes"] if tag == "added") == sorted(SYS_ADDED_LINE_BYTES),
            "system added line bytes pin")
    require(e1["params_non_message_identical"] is True, "params identical fact")
    e1b = doc["e1b_crossday_fixed_credential"]
    require(e1b["req1_identical"] is True and e1b["aux_identical"] is True, "runB identity facts")
    require(e1b["req3_same_bytes"] is True, "req3 same bytes")
    require(e1b["req3_diff_leaves"] == EXPECTED_DIFF_LEAVES_RUNB_REQ3, "req3 diff leaves pin")
    att = doc["attribution"]
    require(att["expectation_met"] is True and att["falsifier_triggered"] is False, "attribution facts")
    require(att["classification"] == CLASSIFICATION, "classification pin")
    text = json.dumps(doc, ensure_ascii=False, sort_keys=True)
    require("/Users/" not in text, "private path leak")
    return True


def result_for(doc, evidence_sha):
    return {
        "schema": "crossday-stability-result-v1",
        "baseline_head": BASELINE,
        "evidence_sha256": evidence_sha,
        "verdicts": {
            "e1_with_credentials": "cross_day_drift_vs_prior",
            "e1b_fixed_credential": "cross_day_runtime_stable",
            "attribution": "drift_attributed_to_credential_conditional_web_tool_surface",
            "falsifier": "not_triggered",
        },
        "classification": doc["attribution"]["classification"],
        "boundaries": doc["boundaries"],
        "limits": ["public replay re-checks pins and structure only; content-level comparisons were computed at build time from private archives",
                   "result-only fields are not covered by the evidence seal"],
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive-root")
    ap.add_argument("--evidence")
    ap.add_argument("--build-evidence")
    ap.add_argument("--output", required=True)
    args = ap.parse_args(argv)
    if args.build_evidence:
        require(args.archive_root, "--archive-root required for build")
        doc = build(args.archive_root)
        evidence_bytes = json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8") + b"\n"
        doc = loads(evidence_bytes)
        validate_public(doc)
        exclusive(args.build_evidence, evidence_bytes)
    elif args.evidence:
        evidence_bytes = open(args.evidence, "rb").read()
        doc = loads(evidence_bytes)
    else:
        sealed = os.path.join(HERE, "evidence.json")
        require(os.path.isfile(sealed), "missing sealed evidence; pass --evidence or --build-evidence")
        evidence_bytes = open(sealed, "rb").read()
        doc = loads(evidence_bytes)
    validate_public(doc)
    res = result_for(doc, sha(evidence_bytes))
    out = json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8") + b"\n"
    exclusive(args.output, out)
    print("ok attribution=%s e1b_req1_identical=%s" % (res["verdicts"]["attribution"], doc["e1b_crossday_fixed_credential"]["req1_identical"]))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Invalid as e:
        print("invalid: %s" % e, file=sys.stderr)
        sys.exit(2)
