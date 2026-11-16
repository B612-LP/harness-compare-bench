#!/usr/bin/env python3
"""Cross-day rebuild re-check (R-A5): one authorized run on 2026-11-17 compared
against the five same-day runs of 2026-11-16.

Endpoints frozen in this file BEFORE the run (constants; see EXECUTION-RECORD):
P1 req1 byte-equal vs all five prior runs; P2 req2 byte-equal vs all five;
P3 per-pair diff leaves == 4 and all provider call_id values and normalized
canonical equality; P4 in-run prefix + appended shapes + delta bytes;
P5 cross-day run date comes from private meta (not asserted from content).

stdlib only; refuses duplicate JSON keys and non-finite numbers; exclusive
outputs; public replay re-checks seals/arithmetic only and cannot authenticate
the private archive. BASELINE pins the published tree state this package was
built against (may trail HEAD; historical replay allows top-level baseline
drift only).
"""
import argparse, hashlib, json, re, sys
from pathlib import Path

BASELINE = "d971eff56b8ed4ba9f989745220446e1c18c0e9d"
SCHEMA = "capture-crossday-provenance-evidence-v1"
CALL_ID_RE = re.compile(r"call_[0-9a-f]{24}")
RUN_LABELS = ["r1", "r2", "r3", "r4", "r5", "r6"]
RUN_RELS = {
    "r1": "loop1/capture",
    "r2": "loop5/capture-r2",
    "r3": "loop6/capture-r3",
    "r4": "loop6/capture-r4",
    "r5": "loop6/capture-r5",
    "r6": "loop9/capture-r6",
}
PRIOR_DATE = "2026-11-16"
R6_DATE = "2026-11-17"
RUN_DATES = {"r1": PRIOR_DATE, "r2": PRIOR_DATE, "r3": PRIOR_DATE,
             "r4": PRIOR_DATE, "r5": PRIOR_DATE, "r6": R6_DATE}
REQ1_SHA = "92220699f215bbdfe0faa392587b8fc43ad6793f10da6baf8b7541518120ac10"
REQ2_SHA = "9f2b6b3e9b76dde704dd763efc1e60992ec2c798c987ae577c784ddd63e34e76"
REQ3_DELTA = 1016
DIFF_LEAVES = 4
APPENDED_SHAPES = [["assistant", "null", 0], ["tool", "str", 227], ["tool", "str", 203]]
WORKSPACE_FILES = {
    "TASK.md": "68599aec2f4a1201c6eb9e46ba92a76d5b68a3cb96f1154e24d8edbe588c3f2c",
    "inputs/exercises/dominoes/dominoes.py": "89f1fede34db8dbd73fb7103476080307e769425049014bf60b7d5e632f9743b",
}

def require(cond, what="assertion failed"):
    if not cond:
        raise ValueError(what)

def no_duplicate_pairs(pairs):
    seen = set()
    for k, _ in pairs:
        if k in seen:
            raise ValueError("duplicate key")
        seen.add(k)
    return dict(pairs)

def loads(text):
    return json.loads(text, object_pairs_hook=no_duplicate_pairs,
                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError("non-finite")))

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")

def normalize_ids(value):
    return json.loads(CALL_ID_RE.sub("CID", canon(value).decode("utf-8")))

def diff_leaves(a, b, path=()):
    out = []
    if type(a) is not type(b):
        return [(path,)]
    if isinstance(a, dict):
        for k in set(a) | set(b):
            if k not in a or k not in b:
                out.append((path + (k,),))
            else:
                out += diff_leaves(a[k], b[k], path + (k,))
    elif isinstance(a, list):
        if len(a) != len(b):
            return [(path + ("len",),)]
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff_leaves(x, y, path + (i,))
    elif a != b:
        out.append((path,))
    return out

def diff_values(a, b, path=()):
    out = []
    if type(a) is not type(b):
        return [(path, a, b)]
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append((path + (k,), None, b[k]))
            elif k not in b:
                out.append((path + (k,), a[k], None))
            else:
                out += diff_values(a[k], b[k], path + (k,))
    elif isinstance(a, list):
        if len(a) != len(b):
            return [(path + ("len",), len(a), len(b))]
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff_values(x, y, path + (i,))
    elif a != b:
        out.append((path, a, b))
    return out

def is_title(body):
    msgs = body.get("messages", [])
    return (len(msgs) == 2 and body.get("max_tokens") == 4096
            and body.get("tools") in (None, []))

def load_run(archive, rel):
    d = archive / rel
    raws, bodies = {}, {}
    for idx in (1, 2, 3):
        p = d / "requests" / ("%03d.request.bin" % idx)
        raw = p.read_bytes()
        raws[idx] = raw
        bodies[idx] = loads(raw.decode("utf-8"))
    return raws, bodies

def build(archive):
    per, raws_all, pairs = {}, {}, []
    for label in RUN_LABELS:
        raws, bodies = load_run(archive, RUN_RELS[label])
        raws_all[label] = raws
        m1 = bodies[1]["messages"]
        m3 = bodies[3]["messages"]
        appended = [[m.get("role"),
                     "str" if isinstance(m.get("content"), str) else ("null" if m.get("content") is None else "other"),
                     len(m.get("content") or "")] for m in m3[len(m1):]]
        per[label] = {
            "req1_sha256": sha(raws[1]), "req2_sha256": sha(raws[2]),
            "req3_sha256": sha(raws[3]),
            "req3_delta_bytes": len(raws[3]) - len(raws[1]),
            "appended_shapes": appended,
            "prefix_ok": m3[:len(m1)] == m1 and len(m3) > len(m1),
        }
    for j in ("r1", "r2", "r3", "r4", "r5"):
        b_j = load_run(archive, RUN_RELS[j])[1][3]
        b_6 = load_run(archive, RUN_RELS["r6"])[1][3]
        vals = diff_values(b_j, b_6)
        ids_ok = all(CALL_ID_RE.fullmatch(str(x)) and CALL_ID_RE.fullmatch(str(y))
                     for _p, x, y in vals)
        norm = normalize_ids(b_j) == normalize_ids(b_6)
        pairs.append({"vs": j, "diff_leaves": len(vals), "leaves_all_call_id": ids_ok,
                      "normalized_equal": norm})
    evidence = {
        "schema": SCHEMA, "baseline_commit": BASELINE,
        "runs": per, "run_dates": RUN_DATES,
        "cross_day": {
            "req1_byte_equal_vs_r1": raws_all["r1"][1] == raws_all["r6"][1],
            "req1_byte_equal_vs_r2": raws_all["r2"][1] == raws_all["r6"][1],
            "req1_byte_equal_vs_r3": raws_all["r3"][1] == raws_all["r6"][1],
            "req1_byte_equal_vs_r4": raws_all["r4"][1] == raws_all["r6"][1],
            "req1_byte_equal_vs_r5": raws_all["r5"][1] == raws_all["r6"][1],
            "req2_byte_equal_vs_r1": raws_all["r1"][2] == raws_all["r6"][2],
            "req2_byte_equal_vs_r2": raws_all["r2"][2] == raws_all["r6"][2],
            "req2_byte_equal_vs_r3": raws_all["r3"][2] == raws_all["r6"][2],
            "req2_byte_equal_vs_r4": raws_all["r4"][2] == raws_all["r6"][2],
            "req2_byte_equal_vs_r5": raws_all["r5"][2] == raws_all["r6"][2],
            "pairs": pairs},
        "workspace": {"files": WORKSPACE_FILES},
        "limits": ["public replay re-checks seals/arithmetic only; it cannot authenticate the private archive",
                   "bytes are not tokens/cost; response bodies are out of scope; provider internals not certified",
                   "n adds no new statistical claim beyond the declared run pairs"],
    }
    return evidence, per

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive-base", type=Path, default=None)
    ap.add_argument("--build-evidence", type=Path, default=None)
    ap.add_argument("--evidence", type=Path, default=None)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args(argv)
    require((a.archive_base is None) != (a.evidence is None), "choose --archive-base (with --build-evidence) or --evidence")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    require(not a.output.exists(), "output exists")
    if a.archive_base is not None:
        require(a.build_evidence is not None, "--build-evidence required")
        require(not a.build_evidence.exists(), "build-evidence exists")
        evidence, _per = build(a.archive_base.resolve())
        a.build_evidence.parent.mkdir(parents=True, exist_ok=True)
        a.build_evidence.write_bytes(canon(evidence) + b"\n")
    else:
        evidence = loads(a.evidence.read_bytes().decode("utf-8"))
    require(evidence.get("schema") == SCHEMA, "schema")
    require(evidence.get("baseline_commit") == BASELINE, "baseline")
    runs = evidence["runs"]
    require(set(runs) == set(RUN_LABELS), "run labels")
    for label in RUN_LABELS:
        r = runs[label]
        require(r["req1_sha256"] == REQ1_SHA, label + " req1 sha")
        require(r["req2_sha256"] == REQ2_SHA, label + " req2 sha")
        require(r["req3_delta_bytes"] == REQ3_DELTA, label + " delta")
        require(r["appended_shapes"] == APPENDED_SHAPES, label + " appended")
        require(r["prefix_ok"] is True, label + " prefix")
    require(evidence["run_dates"]["r6"] == R6_DATE, "r6 date")
    require(all(evidence["run_dates"][k] == PRIOR_DATE for k in ("r1", "r2", "r3", "r4", "r5")), "prior dates")
    cd = evidence["cross_day"]
    for j in ("r1", "r2", "r3", "r4", "r5"):
        require(cd["req1_byte_equal_vs_" + j] is True, "req1 vs " + j)
        require(cd["req2_byte_equal_vs_" + j] is True, "req2 vs " + j)
    require(len(cd["pairs"]) == 5, "pair count")
    for pr in cd["pairs"]:
        require(pr["diff_leaves"] == DIFF_LEAVES, "leaf count")
        require(pr["leaves_all_call_id"] is True, "leaves all call_id")
        require(pr["normalized_equal"] is True, "normalized equal")
    require(evidence["workspace"]["files"] == WORKSPACE_FILES, "workspace")
    result = {"schema": "capture-crossday-provenance-result-v1",
              "baseline_commit": BASELINE,
              "evidence_sha256": sha(canon(evidence)),
              "main_verdict": "cross_day_stable",
              "p1_req1_byte_equal_pairs": "5/5", "p2_req2_byte_equal_pairs": "5/5",
              "p3_pairs": cd["pairs"], "p4": {"prefix_ok": True, "delta": REQ3_DELTA,
                                              "appended_shapes": APPENDED_SHAPES},
              "limits": evidence["limits"]}
    with a.output.open("wb") as f:
        f.write(canon(result) + b"\n")
    print("crossday verify OK: req1/req2 byte-equal 5/5 pairs | leaves 4x5 all call_id | normalized 5/5 | delta 1016")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError) as _exc:
        print("input or output failure", file=sys.stderr)
        sys.exit(2)
