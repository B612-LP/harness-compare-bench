#!/usr/bin/env python3
"""R-A3 多轮链捕获 公开验证器（stdlib only）。

公开层只承载形状/哈希/计数/布尔与算术分账；请求与响应原文只存私有归档。
真档重建需要私有 run 目录（--archive-base），公开重放只校验封印与算术（--evidence）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

BASELINE = "76b2226f241e10d54df206983fbe522b7da3dace"
RUN_LABELS = ("t2-r1", "t2-r2")
RUN_RELS = ("loop7/t2-r1", "loop7/t2-r2")
PROTOCOL_SHA256 = "8ad7e80cf7ca2821641c68c04fd2f78b74ee19cb30a85c74ec14a65adf81627f"
PREREG_SHA256 = "fb9a8c4a712566f080b3ecd0453a20c2a844362921a6f4eade7619c7c5a7478e"
CALL_ID_RE = re.compile(r"call_[0-9a-f]{24}")

# 冻结观测常量（作者构建时实测；公开校验按常量硬等）
RAW_REQUEST_SHAS = {
    "t2-r1": [
        "734ae6585f5fa659364fe9ce037e819dd4a61a662e2e18b37b1cd157c6f34ec7",
        "fae7d99ff39e4b65b34ee460738c1dbf7df8af5a7ac5591395c24b670a2b8634",
        "91c0615a6bdbec95b8f090bdf23580f7b851942584ace56a9ff8523a0a76f9dd",
        "e728a9b9228ad1f9cf0bf749447645480e68a28aceb8a10c3fb47f3316535f35",
        "c20f93995d13ec5845df6c672162439c815e9a8f37fd6470ae8766bfd55e06e5",
        "1f42de549500649c5d0144aa20acbfd1ce4beddd011f7b7168157b33198cd148",
        "92964a5551cd2ae8f8e68a88e08be51dae664d03bfa866e7cdc544724e925164",
    ],
    "t2-r2": [
        "734ae6585f5fa659364fe9ce037e819dd4a61a662e2e18b37b1cd157c6f34ec7",
        "fae7d99ff39e4b65b34ee460738c1dbf7df8af5a7ac5591395c24b670a2b8634",
        "3772e002db168bb9c2fa0e8bb8df48b75ad0dacad133027277ac82a652686b9d",
        "631834ec29f29a78291b711dd39843be2a70d961ca5932cf75834135e93ead54",
        "11382ebaa27c38d88761a08da9c45bbe24404d5a18e44d3edb894437e400e57a",
        "8a48e78acc26b43688bed1569d294470627551d9b5021caf489bd338875263b5",
        "9d540c0e2ed00b616031c3f12908a75903fb86a5906acde53b32fad2f68447cb",
    ],
}
MAIN_CHAIN_SIZE = 6
CHAIN_DELTAS = [876, 519, 548, 497, 315]
APPENDED_SHAPES = [
    [{"role": "assistant", "content_kind": "null", "content_bytes": 0}, {"role": "tool", "content_kind": "str", "content_bytes": 564}],
    [{"role": "assistant", "content_kind": "null", "content_bytes": 0}, {"role": "tool", "content_kind": "str", "content_bytes": 201}],
    [{"role": "assistant", "content_kind": "null", "content_bytes": 0}, {"role": "tool", "content_kind": "str", "content_bytes": 235}],
    [{"role": "assistant", "content_kind": "null", "content_bytes": 0}, {"role": "tool", "content_kind": "str", "content_bytes": 182}],
    [{"role": "assistant", "content_kind": "null", "content_bytes": 0}, {"role": "tool", "content_kind": "str", "content_bytes": 4}],
]
REQUESTS_PER_RUN = 7

STEP_CANON_SHAS = {
    "t2-r1": [
        ["4e21a46d483b8a1b5e65b67c179f283e15368ebc73d1d388f4545c132618655c", "8d6e2c3346332463ece4d6efa221b9f67bab3555c136154cd3c381db935c8039"],
        ["8d6e2c3346332463ece4d6efa221b9f67bab3555c136154cd3c381db935c8039", "27f8acbb8015d07f4ea1637444f17051ad4d42f8bf1e1ed1d88efd6481fe9aef"],
        ["27f8acbb8015d07f4ea1637444f17051ad4d42f8bf1e1ed1d88efd6481fe9aef", "6afb9728fb4abe8f45120f8951c07704e7481a869ee0264833a8059c03cbd8cb"],
        ["6afb9728fb4abe8f45120f8951c07704e7481a869ee0264833a8059c03cbd8cb", "e68d751ca588e3f09e90eceee8f1bfc994de718742d6ab0b2c527d483decf7de"],
        ["e68d751ca588e3f09e90eceee8f1bfc994de718742d6ab0b2c527d483decf7de", "c300400338b976b8164cf5b672c11824899c6a85a91857c99211cc9991199953"],
    ],
    "t2-r2": [
        ["4e21a46d483b8a1b5e65b67c179f283e15368ebc73d1d388f4545c132618655c", "dc6f8833d609c722b67e6cbf3f64ab6b3b8b7b07ba3ac29675e92a54f6a10acf"],
        ["dc6f8833d609c722b67e6cbf3f64ab6b3b8b7b07ba3ac29675e92a54f6a10acf", "d2b7b8d2ba84485dd9f5a5bcc8091aa16b76fee314750096050c4192149f2bd2"],
        ["d2b7b8d2ba84485dd9f5a5bcc8091aa16b76fee314750096050c4192149f2bd2", "7e05ea145bde5444db6c9ca953342462a933d9556f524ccda855fd25fd1fb83c"],
        ["7e05ea145bde5444db6c9ca953342462a933d9556f524ccda855fd25fd1fb83c", "a1b74ef4caa22b577165ab46f2de6cfe4fd483689a304d91a9e9428fdb4b9a31"],
        ["a1b74ef4caa22b577165ab46f2de6cfe4fd483689a304d91a9e9428fdb4b9a31", "a8e37da79d72179e7710034ef584887b5b0a99d33b77cf4ff9d12d97562c06ef"],
    ],
}


class Invalid(Exception):
    pass


def require(cond, msg):
    if not cond:
        raise Invalid(msg)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def no_duplicate_keys(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise Invalid(f"duplicate key {k!r}")
        out[k] = v
    return out


def loads(raw: bytes):
    text = raw.decode("utf-8")

    def reject_constant(name):
        raise Invalid(f"non-finite constant {name}")

    value = json.loads(text, object_pairs_hook=no_duplicate_keys,
                       parse_constant=reject_constant)
    _reject_nonfinite(value, "$")
    return value


def _reject_nonfinite(value, path):
    if isinstance(value, float) and not math.isfinite(value):
        raise Invalid(f"non-finite number at {path}")
    if isinstance(value, dict):
        for k, v in value.items():
            _reject_nonfinite(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            _reject_nonfinite(v, f"{path}[{i}]")


def canon(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def pinned(root: Path, rel: str, expected: str) -> None:
    raw = (root / rel).read_bytes()
    require(sha(raw) == expected, f"pin mismatch {rel}")


def normalize_ids(value):
    if isinstance(value, str):
        return CALL_ID_RE.sub("call_<NORMALIZED>", value)
    if isinstance(value, list):
        return [normalize_ids(x) for x in value]
    if isinstance(value, dict):
        return {k: normalize_ids(x) for k, x in value.items()}
    return value


def content_descriptor(msg):
    c = msg.get("content")
    if c is None:
        kind, ln = "null", 0
    elif isinstance(c, str):
        kind, ln = "str", len(c.encode("utf-8"))
    elif isinstance(c, list):
        kind, ln = "blocks", sum(len(json.dumps(b, ensure_ascii=False).encode("utf-8")) for b in c)
    else:
        raise Invalid("unsupported content type")
    return {"role": msg.get("role"), "content_kind": kind, "content_bytes": ln}


def load_run(archive_base: Path, rel: str, label: str):
    run_root = archive_base / rel
    names = sorted((run_root / "requests").glob("*.request.bin"))
    require(len(names) == REQUESTS_PER_RUN, f"{label}: expected {REQUESTS_PER_RUN} requests, got {len(names)}")
    raws = [n.read_bytes() for n in names]
    for i, (raw, expected) in enumerate(zip(raws, RAW_REQUEST_SHAS[label]), 1):
        require(sha(raw) == expected, f"{label}: request {i} sha mismatch")
    bodies = [loads(r) for r in raws]
    for b in bodies:
        require(isinstance(b, dict) and isinstance(b.get("messages"), list), f"{label}: bad request shape")
    return raws, bodies


def is_title_request(body) -> bool:
    return len(body["messages"]) == 2 and not body.get("tools")


def chain_analysis(bodies):
    main = [b for b in bodies if not is_title_request(b)]
    require(len(main) == MAIN_CHAIN_SIZE, f"main chain size {len(main)} != {MAIN_CHAIN_SIZE}")
    steps = []
    for k in range(len(main) - 1):
        prev_msgs, next_msgs = main[k]["messages"], main[k + 1]["messages"]
        prefix_ok = len(next_msgs) > len(prev_msgs) and next_msgs[: len(prev_msgs)] == prev_msgs
        appended = [content_descriptor(m) for m in next_msgs[len(prev_msgs):]]
        prev_raw, next_raw = canon(main[k]), canon(main[k + 1])
        steps.append({
            "k": k + 1,
            "prefix_ok": prefix_ok,
            "appended": appended,
            "prev_canon_bytes": len(prev_raw),
            "next_canon_bytes": len(next_raw),
            "delta_bytes": len(next_raw) - len(prev_raw),
            "prev_canon_sha256": hashlib.sha256(prev_raw).hexdigest(),
            "next_canon_sha256": hashlib.sha256(next_raw).hexdigest(),
        })
    return main, steps


def cross_run_normalized_equal(bodies_a, bodies_b, indices):
    out = []
    for i in indices:
        na, nb = normalize_ids(bodies_a[i]), normalize_ids(bodies_b[i])
        out.append(bool(canon(na) == canon(nb)))
    return out


SCRIPT_DIR = Path(__file__).resolve().parent


def build(archive_base: Path) -> dict:
    pinned(SCRIPT_DIR, "README.md", PROTOCOL_SHA256)
    per_run = {}
    all_bodies = {}
    for label, rel in zip(RUN_LABELS, RUN_RELS):
        raws, bodies = load_run(archive_base, rel, label)
        main, steps = chain_analysis(bodies)
        require(all(s["prefix_ok"] for s in steps), f"{label}: prefix property broken")
        require([s["delta_bytes"] for s in steps] == CHAIN_DELTAS, f"{label}: delta mismatch")
        for s, shape in zip(steps, APPENDED_SHAPES):
            require(s["appended"] == shape, f"{label}: appended shape mismatch at step {s['k']}")
        per_run[label] = {
            "archive_rel": rel,
            "requests_total": REQUESTS_PER_RUN,
            "main_chain_size": MAIN_CHAIN_SIZE,
            "raw_request_sha256": [sha(r) for r in raws],
            "chain_prefix_ok": True,
            "steps": steps,
        }
        all_bodies[label] = bodies
    idx_title = next(i for i, b in enumerate(all_bodies[RUN_LABELS[0]]) if is_title_request(b))
    req1_equal = raws_equal(all_bodies, RAW_REQUEST_SHAS, 0)
    title_equal = raws_equal(all_bodies, RAW_REQUEST_SHAS, idx_title)
    follow = [i for i in range(REQUESTS_PER_RUN) if i != 0 and i != idx_title]
    normalized_equal = cross_run_normalized_equal(all_bodies[RUN_LABELS[0]], all_bodies[RUN_LABELS[1]], follow)
    return {
        "schema": "capture-chain-evidence-v1",
        "baseline_commit": BASELINE,
        "protocol_sha256": PROTOCOL_SHA256,
        "prereg_sha256": PREREG_SHA256,
        "runs": per_run,
        "cross_run": {
            "req1_byte_equal": req1_equal,
            "title_request_byte_equal": title_equal,
            "followup_normalized_equal": normalized_equal,
        },
    }


def raws_equal(all_bodies, raw_shas, idx):
    return raw_shas[RUN_LABELS[0]][idx] == raw_shas[RUN_LABELS[1]][idx]


def _same(value, expected, path):
    if isinstance(expected, dict):
        require(isinstance(value, dict), f"{path}: not object")
        require(set(value) == set(expected), f"{path}: key set mismatch")
        for k in expected:
            _same(value[k], expected[k], f"{path}.{k}")
    elif isinstance(expected, list):
        require(isinstance(value, list) and len(value) == len(expected), f"{path}: list length mismatch")
        for i, (v, e) in enumerate(zip(value, expected)):
            _same(v, e, f"{path}[{i}]")
    else:
        require(value == expected, f"{path}: {value!r} != {expected!r}")


def validate_public(evidence: dict) -> None:
    require(evidence.get("schema") == "capture-chain-evidence-v1", "bad schema")
    require(evidence.get("baseline_commit") == BASELINE, "bad baseline")
    require(evidence.get("protocol_sha256") == PROTOCOL_SHA256, "bad protocol pin")
    require(evidence.get("prereg_sha256") == PREREG_SHA256, "bad prereg pin")
    runs = evidence.get("runs")
    require(isinstance(runs, dict) and set(runs) == set(RUN_LABELS), "runs mismatch")
    for label, rel in zip(RUN_LABELS, RUN_RELS):
        r = runs[label]
        require(r.get("archive_rel") == rel, f"{label}: rel mismatch")
        require(r.get("requests_total") == REQUESTS_PER_RUN, f"{label}: total mismatch")
        require(r.get("main_chain_size") == MAIN_CHAIN_SIZE, f"{label}: chain size mismatch")
        _same(r.get("raw_request_sha256"), RAW_REQUEST_SHAS[label], f"{label}.raw_request_sha256")
        require(r.get("chain_prefix_ok") is True, f"{label}: prefix flag")
        steps = r.get("steps")
        require(isinstance(steps, list) and len(steps) == MAIN_CHAIN_SIZE - 1, f"{label}: steps length")
        for shape_index, (s, shape, delta) in enumerate(zip(steps, APPENDED_SHAPES, CHAIN_DELTAS)):
            require(s.get("prefix_ok") is True, f"{label}: step prefix")
            require(s.get("delta_bytes") == delta, f"{label}: step delta")
            _same(s.get("appended"), shape, f"{label}.appended[{s.get('k')}]")
            expected_pair = STEP_CANON_SHAS[label][shape_index]
            require(s.get("prev_canon_sha256") == expected_pair[0], f"{label}: step {s.get('k')} prev canon sha mismatch")
            require(s.get("next_canon_sha256") == expected_pair[1], f"{label}: step {s.get('k')} next canon sha mismatch")
    cr = evidence.get("cross_run")
    require(isinstance(cr, dict), "cross_run missing")
    require(cr.get("req1_byte_equal") is True, "req1 not equal")
    require(cr.get("title_request_byte_equal") is True, "title not equal")
    fe = cr.get("followup_normalized_equal")
    require(isinstance(fe, list) and len(fe) == REQUESTS_PER_RUN - 2 and all(x is True for x in fe),
            "followup normalized equality")


def result_for(evidence: dict, evidence_sha: str) -> dict:
    validate_public(evidence)
    verdicts = {
        "p1_within_run_prefix": {label: runs_ok(evidence, label) for label in RUN_LABELS},
        "p2_no_truncation_or_reorg_witness": True,
        "p3_cross_run": {
            "req1_byte_equal": evidence["cross_run"]["req1_byte_equal"],
            "title_byte_equal": evidence["cross_run"]["title_request_byte_equal"],
            "followups_normalized_equal_count": sum(evidence["cross_run"]["followup_normalized_equal"]),
            "followups_total": len(evidence["cross_run"]["followup_normalized_equal"]),
            "chain_deltas_identical_across_runs": CHAIN_DELTAS,
        },
    }
    return {
        "schema": "capture-chain-result-v1",
        "evidence_sha256": evidence_sha,
        "baseline_commit": BASELINE,
        "verdicts": verdicts,
        "counts": {
            "runs": len(RUN_LABELS),
            "requests_per_run": REQUESTS_PER_RUN,
            "main_requests_per_run": MAIN_CHAIN_SIZE,
            "appended_steps_per_run": MAIN_CHAIN_SIZE - 1,
            "total_appended_messages_witnessed": 2 * (MAIN_CHAIN_SIZE - 1) * 2,
        },
        "limits": [
            "descriptive evidence: n=2 runs of one task t2, one model (glm-5.3-flash), one day; not generalizable to other tasks/models/sessions",
            "bytes are not tokens or cost; response bodies are outside the endpoints",
            "normalized equality removes call_id-shaped substrings; it does not certify provider-internal behavior",
            "public replay re-checks seals, schema and arithmetic only; authentic re-derivation needs the private run archives",
            "no claim about requests beyond the captured chain or about private archive authenticity",
        ],
    }


def runs_ok(evidence, label):
    return all(s["prefix_ok"] for s in evidence["runs"][label]["steps"])


def exclusive(path: Path, raw: bytes) -> None:
    if path.exists():
        raise Invalid(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "xb") as fh:
        fh.write(raw)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive-base", type=Path)
    ap.add_argument("--build-evidence", type=Path)
    ap.add_argument("--evidence", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args(argv)
    try:
        if a.build_evidence:
            require(a.archive_base is not None, "--archive-base required with --build-evidence")
            evidence = build(a.archive_base)
            exclusive(a.build_evidence, canon(evidence) + b"\n")
        else:
            require(a.evidence is not None, "--evidence required without --build-evidence")
            evidence = loads(a.evidence.read_bytes())
        result = result_for(evidence, sha(canon(evidence)))
        exclusive(a.output, canon(result) + b"\n")
        print("p1", verdicts_summary(result))
        print("p3", json.dumps(result["verdicts"]["p3_cross_run"], ensure_ascii=False))
        return 0
    except (Invalid, OSError, ValueError, KeyError) as exc:
        print(f"input or output failure: {type(exc).__name__}", file=sys.stderr)
        return 2


def verdicts_summary(result):
    v = result["verdicts"]["p1_within_run_prefix"]
    return " ".join(f"{k}={v[k]}" for k in RUN_LABELS)


if __name__ == "__main__":
    sys.exit(main())
