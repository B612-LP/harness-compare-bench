#!/usr/bin/env python3
"""Codex cross-time-of-day request-side stability (loop23, 2026-11-17).

Public replay needs only this file + evidence.json/result.json (stdlib only).
Archive rebuild additionally needs the private evening capture directory
(loop23/capture-codex-e1) and the sealed morning capture (until14, SHA-pinned).
"""
import argparse, copy, hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.dirname(os.path.dirname(HERE))  # package parent = 4-打分细则

BASELINE = "d88e9d3d0807575110482c26cbaefbebf86813d3"
SCHEMA = "codex-timeofday-stability-evidence-v1"

MORNING = {
    "req1": {"sha256": "6a156cdb57c908fc385076e840ef281ca6f75573b5881af10fbeda73fa08ced9", "bytes": 37568},
    "req2": {"sha256": "b6fd7749006818d405baae558c75d9f206e9c840393049eb7ea8a7d28f2c6901", "bytes": 39102},
    "req3": {"sha256": "2bae0e381ad8765fe3bbb6a7b5565e8b2cc0e1959e7626f26cb4364c2212f836", "bytes": 39984},
    "rel_root": "until14-20261117/loop14/capture-codex-r1/requests",
}
ID_NORMALIZED_CANONICAL_SHA256 = "351bc9383e483c876fdeafb7e73fd5f45da4eb40b53512cc5fe2066f02476d4e"
DIFF_LEAVES_EXPECT = 11
DIFF_FIELDS_EXPECT = {"client_metadata": 6, "input_item_id": 4, "prompt_cache_key": 1}
EVENING = {
    "e1_req1": {"file": "001", "sha256": "55db3139fa5fc4c0eb4164966f830615943c63f7c03488f2ca09227a22c9255f", "bytes": 37568},
    "e1_req2": {"file": "002", "sha256": "ca93052affacc3ea8fd3c9f43e9565f2458ef1f7c116d3b4519047519c3890ab", "bytes": 39266},
    "e2_req1": {"file": "003", "sha256": "be9a5ab68fb648325da217f22398ab76a77950205f5318d987d64b9516f53d84", "bytes": 37568},
    "e2_req2": {"file": "004", "sha256": "0c6800804c2dcef3e494e954da8e7d810e82a56bb760f6b9a51722399f9faf9d", "bytes": 38653},
}
PROMPT = {"sha256": "7a7c57c759d2aaccbdab600e4cb4c7b429bb820268a801f97967f82565ecb765", "bytes": 214}
WORKSPACE_FILES = {
    "TASK.md": "68599aec2f4a1201c6eb9e46ba92a76d5b68a3cb96f1154e24d8edbe588c3f2c",
    "dominoes.py": "89f1fede34db8dbd73fb7103476080307e769425049014bf60b7d5e632f9743b",
}
APP_VERSION = "codex-cli 0.163.0"
PROXY = {"listen": "127.0.0.1:8800", "upstream": "https://api.deepseek.com:443"}
CLASSIFICATION = "codex_timeofday_stable_ids_generated"


class Invalid(Exception):
    pass


def require(cond, msg):
    if not cond:
        raise Invalid(msg)


def _reject_float(x):
    raise Invalid("non-finite number")


def loads(raw):
    try:
        return json.loads(raw.decode("utf-8"), parse_float=_reject_float,
                          parse_constant=lambda c: (_ for _ in ()).throw(Invalid("non-finite constant")))
    except Invalid:
        raise
    except Exception as e:
        raise Invalid("bad json: %s" % e.__class__.__name__)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def no_dupes(pairs):
    ks = [k for k, _ in pairs]
    require(len(ks) == len(set(ks)), "duplicate key")
    return dict(pairs)


def strict_loads(raw):
    return json.loads(raw.decode("utf-8"), object_pairs_hook=no_dupes, parse_float=_reject_float,
                      parse_constant=lambda c: (_ for _ in ()).throw(Invalid("non-finite constant")))


def canon(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def safe_path(root, relative):
    root = os.path.realpath(root)
    p = os.path.realpath(os.path.join(root, relative))
    require(p == root or p.startswith(root + os.sep), "path escape")
    return p


def pinned(root, relative, expected):
    p = safe_path(root, relative)
    raw = open(p, "rb").read()
    require(sha(raw) == expected, "pin mismatch: %s" % relative)
    return raw


def normalize_ids(req):
    d = copy.deepcopy(req)
    d["client_metadata"] = "NORMALIZED"
    d["prompt_cache_key"] = "NORMALIZED"
    for it in d.get("input", []):
        if isinstance(it, dict) and "id" in it:
            it["id"] = "NORMALIZED"
    return d


def diff_leaves(a, b, path=""):
    out = []
    if type(a) is not type(b):
        out.append([path, "type"])
        return out
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append([path + "/" + k, "side_only"])
            else:
                out += diff_leaves(a[k], b[k], path + "/" + k)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append([path, "len"])
        for i, (u, v) in enumerate(zip(a, b)):
            out += diff_leaves(u, v, "%s/%d" % (path, i))
    elif a != b:
        out.append([path, "value"])
    return out


def classify_field(path):
    tail = path.rsplit("/", 1)[-1]
    if tail == "prompt_cache_key":
        return "prompt_cache_key"
    if "client_metadata" in path.split("/"):
        return "client_metadata"
    if tail == "id" and path.startswith("/input/"):
        return "input_item_id"
    return "other"


def build(root):
    proxy = loads(open(safe_path(root, "PROXY-START.json"), "rb").read())
    require(proxy.get("listen") == PROXY["listen"], "proxy listen changed")
    require(proxy.get("upstream") == PROXY["upstream"], "upstream changed")

    bodies = {}
    for key, spec in EVENING.items():
        raw = pinned(root, "requests/%s.request.bin" % spec["file"], spec["sha256"])
        require(len(raw) == spec["bytes"], "bytes mismatch %s" % key)
        bodies[key] = strict_loads(raw)

    priv = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(root))))
    prior_req1_path = os.path.join(priv, MORNING["rel_root"], "001.request.bin")
    require(os.path.isfile(prior_req1_path), "morning capture missing")
    prior_raw = open(prior_req1_path, "rb").read()
    require(sha(prior_raw) == MORNING["req1"]["sha256"], "morning req1 sha mismatch")
    prior_req1 = loads(prior_raw)

    lv_e1 = diff_leaves(bodies["e1_req1"], prior_req1)
    lv_e2 = diff_leaves(bodies["e2_req1"], prior_req1)
    lv_pair = diff_leaves(bodies["e2_req1"], bodies["e1_req1"])

    def classify(lv):
        fields = {}
        other = []
        for p, kind in lv:
            f = classify_field(p)
            fields[f] = fields.get(f, 0) + 1
            if f == "other":
                other.append([p, kind])
        return {"leaves": len(lv), "fields": fields, "other": other}

    c_e1, c_e2, c_pair = classify(lv_e1), classify(lv_e2), classify(lv_pair)
    norm_e1 = sha(canon(normalize_ids(bodies["e1_req1"])))
    norm_e2 = sha(canon(normalize_ids(bodies["e2_req1"])))
    norm_morning = sha(canon(normalize_ids(prior_req1)))

    def prefix(a_key, b_key):
        a, b = bodies[a_key]["input"], bodies[b_key]["input"]
        l0 = len(a)
        return {"prefix_equal": a == b[:l0], "appended": len(b) - l0}

    return {
        "schema": SCHEMA,
        "baseline_head": BASELINE,
        "meta": {
            "app_version": APP_VERSION,
            "proxy_listen": proxy.get("listen"),
            "upstream": proxy.get("upstream"),
            "prompt_sha256": PROMPT["sha256"],
            "prompt_bytes": PROMPT["bytes"],
            "workspace_files": WORKSPACE_FILES,
            "morning_req1_sha256": MORNING["req1"]["sha256"],
        },
        "e1_timeofday_req1": {
            "evening_sha256": EVENING["e1_req1"]["sha256"],
            "evening_bytes": EVENING["e1_req1"]["bytes"],
            "same_bytes_as_morning": EVENING["e1_req1"]["bytes"] == MORNING["req1"]["bytes"],
            "diff": c_e1,
        },
        "e1b_timeofday_req1_run2": {
            "evening_sha256": EVENING["e2_req1"]["sha256"],
            "diff": c_e2,
            "pair_diff": c_pair,
        },
        "e2_normalized_identity": {
            "id_normalized_canonical_sha256": ID_NORMALIZED_CANONICAL_SHA256,
            "evening_run1": norm_e1,
            "evening_run2": norm_e2,
            "morning": norm_morning,
            "all_equal": norm_e1 == norm_e2 == norm_morning == ID_NORMALIZED_CANONICAL_SHA256,
        },
        "e3_inrun_prefix": {
            "e1": prefix("e1_req1", "e1_req2"),
            "e2": prefix("e2_req1", "e2_req2"),
        },
        "e3b_second_main_request_bytes": {
            "e1": EVENING["e1_req2"]["bytes"],
            "e2": EVENING["e2_req2"]["bytes"],
            "morning": MORNING["req2"]["bytes"],
            "note": "second-main shapes vary run-to-run (model freedom); descriptive only, not pinned as identity",
        },
        "attribution": {
            "expectation_met": c_e1["leaves"] == DIFF_LEAVES_EXPECT and c_e1["fields"] == DIFF_FIELDS_EXPECT and norm_e1 == ID_NORMALIZED_CANONICAL_SHA256,
            "falsifier_triggered": bool(c_e1["other"]) or c_e1["leaves"] != DIFF_LEAVES_EXPECT,
            "classification": CLASSIFICATION,
        },
        "boundaries": ["time-of-day within one day, not cross-day", "n=1 per arm",
                       "bytes are transport-level, not tokens",
                       "identity does not prove model behavior unchanged",
                       "second-main request shapes are model freedom and not scored"],
    }


def validate_public(doc):
    require(strict_loads(canon(doc)) or True, "unused")
    require(doc.get("schema") == SCHEMA, "schema")
    require(doc.get("baseline_head") == BASELINE, "baseline")
    m = doc.get("meta") or {}
    require(m.get("app_version") == APP_VERSION, "app version pin")
    require(m.get("proxy_listen") == PROXY["listen"], "proxy pin")
    require(m.get("upstream") == PROXY["upstream"], "upstream pin")
    require(m.get("prompt_sha256") == PROMPT["sha256"], "prompt pin")
    require(m.get("prompt_bytes") == PROMPT["bytes"], "prompt bytes")
    require(m.get("workspace_files") == WORKSPACE_FILES, "workspace pin")
    require(m.get("morning_req1_sha256") == MORNING["req1"]["sha256"], "morning pin")
    e1 = doc.get("e1_timeofday_req1") or {}
    require(e1.get("evening_sha256") == EVENING["e1_req1"]["sha256"], "e1 pin")
    require(e1.get("evening_bytes") == EVENING["e1_req1"]["bytes"], "e1 bytes")
    require(e1.get("same_bytes_as_morning") is True, "e1 same bytes flag")
    d = e1.get("diff") or {}
    require(d.get("leaves") == DIFF_LEAVES_EXPECT, "e1 diff leaves pin")
    require(d.get("fields") == DIFF_FIELDS_EXPECT, "e1 diff fields pin")
    require(d.get("other") == [], "e1 diff other pin")
    e1b = doc.get("e1b_timeofday_req1_run2") or {}
    require(e1b.get("evening_sha256") == EVENING["e2_req1"]["sha256"], "e1b pin")
    d2 = e1b.get("diff") or {}
    require(d2.get("leaves") == DIFF_LEAVES_EXPECT, "e1b leaves pin")
    require(d2.get("fields") == DIFF_FIELDS_EXPECT, "e1b fields pin")
    dp = e1b.get("pair_diff") or {}
    require(dp.get("leaves") == DIFF_LEAVES_EXPECT, "pair leaves pin")
    e2n = doc.get("e2_normalized_identity") or {}
    require(e2n.get("id_normalized_canonical_sha256") == ID_NORMALIZED_CANONICAL_SHA256, "norm pin")
    require(e2n.get("evening_run1") == ID_NORMALIZED_CANONICAL_SHA256, "norm e1")
    require(e2n.get("evening_run2") == ID_NORMALIZED_CANONICAL_SHA256, "norm e2")
    require(e2n.get("morning") == ID_NORMALIZED_CANONICAL_SHA256, "norm morning")
    require(e2n.get("all_equal") is True, "norm flag")
    e3 = doc.get("e3_inrun_prefix") or {}
    for k in ("e1", "e2"):
        s = e3.get(k) or {}
        require(s.get("prefix_equal") is True, "prefix %s" % k)
        require(isinstance(s.get("appended"), int) and s.get("appended") > 0, "appended %s" % k)
    e3b = doc.get("e3b_second_main_request_bytes") or {}
    require(e3b.get("e1") == EVENING["e1_req2"]["bytes"], "e3b e1")
    require(e3b.get("e2") == EVENING["e2_req2"]["bytes"], "e3b e2")
    require(e3b.get("morning") == MORNING["req2"]["bytes"], "e3b morning")
    att = doc.get("attribution") or {}
    require(att.get("expectation_met") is True, "expectation flag")
    require(att.get("falsifier_triggered") is False, "falsifier flag")
    require(att.get("classification") == CLASSIFICATION, "classification pin")
    require(isinstance(doc.get("boundaries"), list) and len(doc.get("boundaries")) >= 4, "boundaries")


def result_for(doc, evidence_sha):
    return {
        "schema": "codex-timeofday-stability-result-v1",
        "baseline_head": BASELINE,
        "evidence_sha256": evidence_sha,
        "verdict": CLASSIFICATION,
        "expectation_met": (doc.get("attribution") or {}).get("expectation_met"),
        "falsifier_triggered": (doc.get("attribution") or {}).get("falsifier_triggered"),
        "req1_diff_leaves": (doc.get("e1_timeofday_req1") or {}).get("diff", {}).get("leaves"),
        "req1_diff_fields": (doc.get("e1_timeofday_req1") or {}).get("diff", {}).get("fields"),
        "id_normalized_all_equal": (doc.get("e2_normalized_identity") or {}).get("all_equal"),
        "inrun_prefix": {k: (doc.get("e3_inrun_prefix") or {}).get(k, {}).get("prefix_equal") for k in ("e1", "e2")},
        "boundaries": doc.get("boundaries"),
        "limits": ["public replay re-checks frozen pins only; original bytes live in the private archive",
                   "evidence/result are sequential outputs, not atomic"],
    }


def exclusive(path, raw):
    p = os.path.realpath(path)
    require(not os.path.exists(p), "output exists: %s" % path)
    open(p, "wb").write(raw)


def dump(path, obj):
    exclusive(path, json.dumps(obj, indent=1, ensure_ascii=False).encode("utf-8") + b"\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--archive-root", default=None)
    ap.add_argument("--evidence", default=None)
    ap.add_argument("--build-evidence", default=None)
    ap.add_argument("--output", required=True)
    a = ap.parse_args(argv)
    try:
        if a.build_evidence:
            require(a.archive_root, "--build-evidence requires --archive-root")
            doc = build(a.archive_root)
            validate_public(doc)
            edoc = dict(doc)
            edoc["readme_sha256"] = sha(open(os.path.join(HERE, "README.md"), "rb").read())
            eb = json.dumps(edoc, indent=1, ensure_ascii=False).encode("utf-8") + b"\n"
            exclusive(a.build_evidence, eb)
            res = result_for(edoc, sha(eb))
        else:
            require(a.evidence, "replay requires --evidence (or --build-evidence)")
            edoc = strict_loads(open(a.evidence, "rb").read())
            require(isinstance(edoc, dict), "evidence must be a JSON object")
            require(edoc.get("readme_sha256") == sha(open(os.path.join(HERE, "README.md"), "rb").read()), "readme pin")
            validate_public(edoc)
            res = result_for(edoc, sha(open(a.evidence, "rb").read()))
        exclusive(a.output, json.dumps(res, indent=1, ensure_ascii=False).encode("utf-8") + b"\n")
        print("ok verdict=%s normalized_equal=%s" % (res["verdict"], res["id_normalized_all_equal"]))
        return 0
    except Invalid as e:
        print("invalid: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
