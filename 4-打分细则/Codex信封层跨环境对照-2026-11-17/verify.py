#!/usr/bin/env python3
"""Codex envelope layers cross-home comparison (+DSH cross-session control).

双模式（互斥，fail-closed，错误统一泛化为 input or output failure）：
  raw 重建: verify.py --archive-root <window root> --build-evidence out.json --output out-result.json
  公开重放: verify.py --evidence evidence.json --output out-result.json
公开档只含字节量/sha/角色/计数；不含任何请求正文、路径值或 id。
"""
import argparse, hashlib, json, os, sys

SCHEMA = "codex-envelope-crosshome-evidence-v1"
BASELINE = "7986effb2befe7a08a0d1a3769b6480cdc0ac1ec"
HERE = os.path.dirname(os.path.abspath(__file__))
README_SHA256 = hashlib.sha256(open(os.path.join(HERE, "README.md"), "rb").read()).hexdigest()

FROZEN_ROWS = {
    "loop1/capture": {"items": [["system", "str", 2593, "8e17c07c2a212f104dea010c0200c45a6b7a27682c91ed4bbc14827da059eb93"], ["user", "str", 214, "7a7c57c759d2aaccbdab600e4cb4c7b429bb820268a801f97967f82565ecb765"], ["user", "str", 3111, "da24772569ee4e50dfae041e1fedf2e356c3535ca527bdcea304a870e76a63cf"], ["user", "str", 679, "264120165ce621494f7218e3beb79c9bad9a57ddf75947c1e6c7ba8835bcc7bb"], ["user", "str", 5525, "1ec2cc159dca2c9530274f278d6d4ad874d50f8f074637beda3fdf8a11892ac5"]], "tools_count": 22, "tools_digest": "fa446b06db7e744cc468df41e8ba7de9be883e0ba9b307dc922cdede52dd084e", "requests_in_run": 3, "req1_sha256": "92220699f215bbdfe0faa392587b8fc43ad6793f10da6baf8b7541518120ac10"},
    "loop14/capture-codex-r1": {"items": [["developer", "list", 17374, "4ff4862111abaabad3c25e7d448a748a9db19d073f5d516c245f7ff7aa02e985"], ["developer", "list", 398, "418a09521c6b7bcc4df3d0fd8111c87cecdfdf749c0fda26e1588b72800bb774"], ["user", "list", 453, "7061faeb4515775dc26bb35d1072e8b63669961a6dd5447a8850908c0786d4ee"], ["user", "list", 247, "27737ea7fb0d23036af2e575666cad51a1c0ba15db173f3957d7a228b10348c0"]], "tools_count": 8, "tools_digest": "e327d59a24cc17700122f0b77bd8f6d21644186164f5678658cf4d4b2b0aaecd", "requests_in_run": 3, "req1_sha256": "6a156cdb57c908fc385076e840ef281ca6f75573b5881af10fbeda73fa08ced9"},
    "loop14/capture-codex-r2": {"items": [["developer", "list", 17374, "4ff4862111abaabad3c25e7d448a748a9db19d073f5d516c245f7ff7aa02e985"], ["developer", "list", 398, "418a09521c6b7bcc4df3d0fd8111c87cecdfdf749c0fda26e1588b72800bb774"], ["user", "list", 453, "7061faeb4515775dc26bb35d1072e8b63669961a6dd5447a8850908c0786d4ee"], ["user", "list", 247, "27737ea7fb0d23036af2e575666cad51a1c0ba15db173f3957d7a228b10348c0"]], "tools_count": 8, "tools_digest": "e327d59a24cc17700122f0b77bd8f6d21644186164f5678658cf4d4b2b0aaecd", "requests_in_run": 2, "req1_sha256": "062acfcb4f9dc98ffcb584062a211ef4cb6bdf92d096279a39a0e3f8f17c898c"},
    "loop15/codex-t3-r1": {"items": [["developer", "list", 17374, "4ff4862111abaabad3c25e7d448a748a9db19d073f5d516c245f7ff7aa02e985"], ["developer", "list", 398, "418a09521c6b7bcc4df3d0fd8111c87cecdfdf749c0fda26e1588b72800bb774"], ["user", "list", 453, "f2eac7d9b7e45492de78a5c04b7b02fdc2c8757d02c034d2184f0af6a762f829"], ["user", "list", 93, "6e5eb14bb6fc9384ef54c886c1bcf4e5fa946de5d19671596e350b78ba2bd7c7"]], "tools_count": 8, "tools_digest": "e327d59a24cc17700122f0b77bd8f6d21644186164f5678658cf4d4b2b0aaecd", "requests_in_run": 3, "req1_sha256": "2cf01fa3bb3c8b437926d7cdae9abac17f1e04062dba75ed6189e6c19b26ae7c"},
    "loop15/codex-t3-r2": {"items": [["developer", "list", 17374, "4ff4862111abaabad3c25e7d448a748a9db19d073f5d516c245f7ff7aa02e985"], ["developer", "list", 398, "418a09521c6b7bcc4df3d0fd8111c87cecdfdf749c0fda26e1588b72800bb774"], ["user", "list", 453, "f2eac7d9b7e45492de78a5c04b7b02fdc2c8757d02c034d2184f0af6a762f829"], ["user", "list", 93, "6e5eb14bb6fc9384ef54c886c1bcf4e5fa946de5d19671596e350b78ba2bd7c7"]], "tools_count": 8, "tools_digest": "e327d59a24cc17700122f0b77bd8f6d21644186164f5678658cf4d4b2b0aaecd", "requests_in_run": 3, "req1_sha256": "9a0a4c8286fffa0d5a5c2b7260d095fd234f4b51fbf6ab3c6b210f26e75c1661"},
    "loop7/t2-r1": {"items": [["system", "str", 2593, "8e17c07c2a212f104dea010c0200c45a6b7a27682c91ed4bbc14827da059eb93"], ["user", "str", 113, "db839482cc58767e9b56ca714cbb31f0b8f13c2fcd1e6bdec150b578d42dc54f"], ["user", "str", 3111, "da24772569ee4e50dfae041e1fedf2e356c3535ca527bdcea304a870e76a63cf"], ["user", "str", 679, "b6c355bbdbdc803fdfa12ed7a9defe6124ba1c5e0b0f9a59fc5c238a0aa8c51b"], ["user", "str", 5525, "1ec2cc159dca2c9530274f278d6d4ad874d50f8f074637beda3fdf8a11892ac5"]], "tools_count": 22, "tools_digest": "fa446b06db7e744cc468df41e8ba7de9be883e0ba9b307dc922cdede52dd084e", "requests_in_run": 7, "req1_sha256": "734ae6585f5fa659364fe9ce037e819dd4a61a662e2e18b37b1cd157c6f34ec7"},
    "loop8/t3-r1": {"items": [["system", "str", 2593, "8e17c07c2a212f104dea010c0200c45a6b7a27682c91ed4bbc14827da059eb93"], ["user", "str", 60, "e7fea6df7f205a8c1542bbae3ada653a8e2a8fb09a27efa92547c2e3864153d4"], ["user", "str", 3111, "da24772569ee4e50dfae041e1fedf2e356c3535ca527bdcea304a870e76a63cf"], ["user", "str", 679, "75947b5cd91bb2000796da2b90a23722421d209e8cc7b3f01a9565135eb0c18f"], ["user", "str", 5525, "1ec2cc159dca2c9530274f278d6d4ad874d50f8f074637beda3fdf8a11892ac5"]], "tools_count": 22, "tools_digest": "fa446b06db7e744cc468df41e8ba7de9be883e0ba9b307dc922cdede52dd084e", "requests_in_run": 16, "req1_sha256": "765b958d5606bc7a43a0960e30e7106eb3638beb402419e0f1d17f471ee52220"},
}

# tuple-normalize frozen items (JSON round-trip yields lists)
FROZEN_ROWS = {k: {**row, "items": [tuple(i) for i in row["items"]]} for k, row in FROZEN_ROWS.items()}

RUNS = [
    ("loop14/capture-codex-r1", "codex"),
    ("loop14/capture-codex-r2", "codex"),
    ("loop15/codex-t3-r1", "codex"),
    ("loop15/codex-t3-r2", "codex"),
    ("loop1/capture", "dsh"),
    ("loop7/t2-r1", "dsh"),
    ("loop8/t3-r1", "dsh"),
]

def die(msg="input or output failure"):
    print(msg, file=sys.stderr)
    sys.exit(2)

def require(cond, what="input or output failure"):
    if not cond:
        die()

def sha(b):
    return hashlib.sha256(b).hexdigest()

def canon(o):
    return json.dumps(o, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def no_duplicate_pairs(pairs):
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys):
        die()
    return dict(pairs)

def _reject_float(_):
    raise ValueError("non-finite float literal")

def loads(raw):
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicate_pairs,
                          parse_constant=_reject_float, parse_float=_reject_float)
    except SystemExit:
        raise
    except Exception:
        die()

def content_of(item):
    """Extract the message content payload of one input item / chat message.

    只返回 canonical bytes 与类型标签，不返回内容本身。"""
    if not isinstance(item, dict):
        die()
    c = item.get("content")
    if isinstance(c, str):
        return "str", c.encode("utf-8")
    if isinstance(c, list):
        return "list", canon(c)
    if c is None:
        return "null", b""
    die()

def first_request(rel, root):
    d = os.path.join(root, rel, "requests")
    names = sorted(n for n in os.listdir(d) if n.endswith(".request.bin")) if os.path.isdir(d) else None
    require(names)
    raw = open(os.path.join(d, names[0]), "rb").read()
    return raw, len(names)

def build_codex(raw):
    body = loads(raw)
    require("input" in body)
    items = body["input"]
    require(isinstance(items, list) and len(items) >= 2)
    entries = []
    for it in items:
        kind, b = content_of(it)
        role = it.get("role")
        require(isinstance(role, str))
        entries.append({"role": role, "kind": kind, "bytes": len(b), "sha256": sha(b)})
    tools = body.get("tools", [])
    digests = sorted(sha(canon(t)) for t in tools)
    return {
        "shape": "responses",
        "n_input_items": len(items),
        "items": entries,
        "task_item_index": len(items) - 1,
        "instructions_field_present": "instructions" in body,
        "tools_count": len(tools),
        "tools_digest": sha(canon(digests)),
        "req1_sha256": sha(raw),
        "requests_in_run": None,
    }

def build_dsh(raw):
    body = loads(raw)
    ms = body.get("messages")
    require(isinstance(ms, list) and len(ms) >= 3)
    entries = []
    for m in ms:
        kind, b = content_of(m)
        role = m.get("role")
        require(isinstance(role, str))
        entries.append({"role": role, "kind": kind, "bytes": len(b), "sha256": sha(b)})
    require(entries[0]["role"] == "system")
    tools = body.get("tools", [])
    digests = sorted(sha(canon(t)) for t in tools)
    return {
        "shape": "chat",
        "n_messages": len(ms),
        "items": entries,
        "task_item_index": 1,
        "tools_count": len(tools),
        "tools_digest": sha(canon(digests)),
        "req1_sha256": sha(raw),
        "requests_in_run": None,
    }

def build(root):
    rows = {}
    for rel, kind in RUNS:
        raw, total = first_request(rel, root)
        row = build_codex(raw) if kind == "codex" else build_dsh(raw)
        row["requests_in_run"] = total
        rows[rel] = row
    evidence = {
        "schema": SCHEMA,
        "baseline_commit": BASELINE,
        "readme_sha256": README_SHA256,
        "runs": rows,
    }
    return evidence

def classify(a, b):
    if a is None or b is None:
        return "absent"
    return "identical" if a == b else "differs"

def compare_codex(ra, rb):
    require(ra["shape"] == "responses" and rb["shape"] == "responses")
    n_env = min(ra["task_item_index"], rb["task_item_index"])
    require(ra["n_input_items"] == rb["n_input_items"])
    layers = []
    for i in range(n_env):
        x, y = ra["items"][i], rb["items"][i]
        same = (x["role"], x["kind"], x["bytes"], x["sha256"]) == (y["role"], y["kind"], y["bytes"], y["sha256"])
        layers.append({"index": i, "role_a": x["role"], "role_b": y["role"],
                       "classification": "identical" if same else "differs"})
    tools = classify(ra["tools_digest"], rb["tools_digest"])
    ins = "absent" if not (ra["instructions_field_present"] or rb["instructions_field_present"]) else (
        "identical" if ra["instructions_field_present"] == rb["instructions_field_present"] else "differs")
    return {"layers": layers, "tools": tools, "instructions_field": ins}

def result_for(ev, evidence_sha):
    rows = ev["runs"]
    codex = [r for r in RUNS if r[1] == "codex"]
    dsh = [r for r in RUNS if r[1] == "dsh"]
    e2 = compare_codex(rows[codex[0][0]], rows[codex[2][0]])
    e3 = [compare_codex(rows[codex[0][0]], rows[codex[1][0]]),
          compare_codex(rows[codex[2][0]], rows[codex[3][0]])]
    e4 = []
    for i in range(len(dsh)):
        for j in range(i + 1, len(dsh)):
            a, b = rows[dsh[i][0]], rows[dsh[j][0]]
            e4.append({"pair": [dsh[i][0], dsh[j][0]],
                       "system": classify((a["items"][0]["role"], a["items"][0]["bytes"], a["items"][0]["sha256"]),
                                          (b["items"][0]["role"], b["items"][0]["bytes"], b["items"][0]["sha256"])),
                       "tools": classify(a["tools_digest"], b["tools_digest"])})
    def codex_summary(cmp_list):
        keys = set()
        for c in cmp_list:
            for l in c["layers"]:
                keys.add(l["classification"])
        return "stable" if keys == {"identical"} else ("mixed" if "identical" in keys else "varying")
    verdict = ("codex_inputenv_%s_tools_%s__dsh_sys_%s_tools_%s" % (
        codex_summary([e2] + e3),
        "stable" if {x["tools"] for x in [e2] + e3} == {"identical"} else "varying",
        "stable" if {x["system"] for x in e4} == {"identical"} else "varying",
        "stable" if {x["tools"] for x in e4} == {"identical"} else "varying"))
    return {
        "schema": SCHEMA + ":result",
        "evidence_sha256": evidence_sha,
        "readme_sha256": ev["readme_sha256"],
        "baseline_commit": ev["baseline_commit"],
        "endpoints": {
            "E2_cross_home": {"pair": [codex[0][0], codex[2][0]], **e2},
            "E3_within_home": [{"pair": [codex[0][0], codex[1][0]], **e3[0]},
                               {"pair": [codex[2][0], codex[3][0]], **e3[1]}],
            "E4_dsh_cross_session": e4,
        },
        "verdict": verdict,
        "boundaries": [
            "product-archived wire bytes only; no model/provider/HTTP/server authentication",
            "stable means byte-identical; varying does not locate the changing field",
            "task message excluded by structural rule (last item / messages[1]); layout mismatch would surface as classification failure",
            "single task faces and single model channel; no extrapolation",
        ],
    }

def validate_public(ev, readme_sha):
    require(isinstance(ev, dict))
    require(ev.get("schema") == SCHEMA)
    require(ev.get("baseline_commit") == BASELINE)
    require(ev.get("readme_sha256") == readme_sha)
    require(set(ev.keys()) == {"schema", "baseline_commit", "readme_sha256", "runs"})
    require(set(ev["runs"].keys()) == {r[0] for r in RUNS})
    for rel, kind in RUNS:
        row = ev["runs"][rel]
        req_keys = {"shape", "n_input_items", "items", "task_item_index", "instructions_field_present",
                    "tools_count", "tools_digest", "req1_sha256", "requests_in_run"} if kind == "codex" else \
                   {"shape", "n_messages", "items", "task_item_index", "tools_count", "tools_digest",
                    "req1_sha256", "requests_in_run"}
        require(set(row.keys()) == req_keys)
        require(row["shape"] == ("responses" if kind == "codex" else "chat"))
        require(isinstance(row["req1_sha256"], str) and len(row["req1_sha256"]) == 64)
        require(isinstance(row["tools_digest"], str) and len(row["tools_digest"]) == 64)
        frozen = FROZEN_ROWS[rel]
        got_items = [(it["role"], it["kind"], it["bytes"], it["sha256"]) for it in row["items"]]
        require(got_items == frozen["items"])
        require(row["tools_count"] == frozen["tools_count"])
        require(row["tools_digest"] == frozen["tools_digest"])
        require(row["req1_sha256"] == frozen["req1_sha256"])
        require(row["requests_in_run"] == frozen["requests_in_run"])
        if kind == "codex":
            require(row["instructions_field_present"] is False)
        expect_n = 4 if kind == "codex" else 5
        got = row["n_input_items"] if kind == "codex" else row["n_messages"]
        require(got == expect_n)
        require(len(row["items"]) == got)
        require(row["task_item_index"] == got - 1 if kind == "codex" else row["task_item_index"] == 1)
        for it in row["items"]:
            require(set(it.keys()) == {"role", "kind", "bytes", "sha256"})
            require(it["role"] in ("system", "user", "developer", "assistant", "tool"))
            require(it["kind"] in ("str", "list", "null"))
            require(isinstance(it["bytes"], int) and not isinstance(it["bytes"], bool) and it["bytes"] >= 0)
            require(isinstance(it["sha256"], str) and len(it["sha256"]) == 64)
        require(row["items"][0]["role"] == ("developer" if kind == "codex" else "system"))

def output_path(p):
    if os.path.exists(p) or os.path.isdir(os.path.dirname(os.path.abspath(p)) or ".") is False:
        pass
    ap = os.path.abspath(p)
    if os.path.exists(ap):
        die()
    return ap

def dump(path, obj):
    ap = output_path(path)
    base = os.path.dirname(ap)
    real_root = os.path.realpath(base) if os.path.exists(base) else None
    with open(ap, "x", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, sort_keys=True, indent=1)
        f.write("\n")

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive-root")
    ap.add_argument("--build-evidence")
    ap.add_argument("--evidence")
    ap.add_argument("--output", required=True)
    a = ap.parse_args(argv)
    if bool(a.archive_root) != bool(a.build_evidence):
        die()
    if a.archive_root and a.evidence:
        die()
    if not a.archive_root and not a.evidence:
        die()
    try:
        if a.archive_root:
            readme = open(os.path.join(HERE, "README.md"), "rb").read()
            readme_sha = sha(readme)
            ev = build(a.archive_root)
            evidence_bytes = json.dumps(ev, ensure_ascii=False, sort_keys=True, indent=1).encode("utf-8") + b"\n"
            dump(a.build_evidence, ev)
            res = result_for(ev, sha(evidence_bytes))
        else:
            ev_raw = open(a.evidence, "rb").read()
            ev = loads(ev_raw)
            validate_public(ev, README_SHA256)
            require(ev.get("readme_sha256") == README_SHA256)
            res = result_for(ev, sha(ev_raw))
        dump(a.output, res)
    except SystemExit:
        raise
    except Exception:
        die()
    print("runs=%d verdict=%s" % (len(RUNS), res["verdict"]))
    return 0

if __name__ == "__main__":
    sys.exit(main())
