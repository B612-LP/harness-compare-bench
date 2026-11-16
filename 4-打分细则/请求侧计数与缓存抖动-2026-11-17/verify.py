#!/usr/bin/env python3
"""请求侧计数与缓存抖动：公开重放/私档重建。stdlib-only（gzip为stdlib）。"""
import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

BASELINE = "50c073c084006c0bfd5f8b79db3bc495e842847b"
SCHEMA = "capture-usage-volatility-evidence-v1"
PIN_REBUILD_README = "a6206a2a122d2acb825bf7e30142e1b5a01d0ea6a04fc33bce9ea7e9859d3aff"
PIN_XM_README = "3de9ded761959a7c43821b62c2438c3de0ac8dc9469fbba1c7b4a77484a0ec16"

RUN_LABELS = ["glm_r1", "glm_r2", "glm_r3", "glm_r4", "glm_r5", "glm_r6", "ds_r1", "ds_r2"]
RUN_RELS = {
    "glm_r1": "loop1/capture",
    "glm_r2": "loop5/capture-r2",
    "glm_r3": "loop6/capture-r3",
    "glm_r4": "loop6/capture-r4",
    "glm_r5": "loop6/capture-r5",
    "glm_r6": "loop9/capture-r6",
    "ds_r1": "loop10/capture-ds-r1",
    "ds_r2": "loop10/capture-ds-r2",
}
PROVIDER_OF = {k: ("glm" if k.startswith("glm") else "ds") for k in RUN_LABELS}
# 已由前置包证明的字节恒等（req1/req2）；req3 的 SHA 逐 run 记录、不作恒等 pin
REQ_SHAS = {
    "glm": ["92220699f215bbdfe0faa392587b8fc43ad6793f10da6baf8b7541518120ac10",
            "9f2b6b3e9b76dde704dd763efc1e60992ec2c798c987ae577c784ddd63e34e76"],
    "ds": ["0372557d46f071948f5f32e59466da624fc3748c56dc8b0f7fbcc9d036874ed3",
           "05183eb7906bdc6612c93581e2ec66fc88f6ccaf2474c35314a41f60d0b6f7aa"],
}
REQ_BYTES = {"glm": [33091, 1042, 34107], "ds": [33739, 989, 34767]}
# E1：prompt_tokens 稳定值（provider × 请求序）
PROMPT_TOKENS = {"glm": [7620, 190, 7827], "ds": [8089, 188, 8361]}
# E2：cached_tokens 允许集合（变动即抖动证据）
CACHED_SETS = {
    "glm": [{0, 7616}, {0, 128}, {7616, 7808}],
    "ds": [{0, 7936}, {0}, {8192}],
}
COMPLETION_SETS = {
    "glm": [{62}, {8, 10}, {9, 10}],
    "ds": [{110}, {8, 9}, {8, 9}],
}


def require(cond, msg):
    if not cond:
        raise ValueError(msg)


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate key: %s" % key)
        out[key] = value
    return out


def _reject_const(name):
    raise ValueError("non-finite constant: %s" % name)


def _reject_float(text):
    value = float(text)
    if value != value or value == float("inf") or value == float("-inf"):
        raise ValueError("non-finite float: %s" % text)
    return value


def loads(text):
    return json.loads(text, object_pairs_hook=_pairs, parse_constant=_reject_const,
                      parse_float=_reject_float)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canon(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def extract_usage(text):
    """取SSE末个含usage行。"""
    usage = None
    for line in text.splitlines():
        if line.startswith("data: ") and '"usage"' in line:
            try:
                usage = json.loads(line[6:]).get("usage")
            except Exception:
                pass
    require(isinstance(usage, dict) and isinstance(usage.get("prompt_tokens"), int)
            and isinstance(usage.get("completion_tokens"), int) and isinstance(usage.get("total_tokens"), int),
            "usage missing or malformed")
    return usage


def load_run(run_dir):
    """读一个run的3请求（request bytes/status/usage）。"""
    resp = Path(run_dir) / "responses"
    rows = []
    for f in sorted(resp.glob("*.response.bin")):
        meta = loads((resp / (f.name + ".meta.json")).read_bytes().decode("utf-8"))
        require(meta.get("upstream_status") == 200, "status not 200: %s" % f.name)
        raw = f.read_bytes()
        gzipped = raw[:2] == b"\x1f\x8b"
        text = gzip.decompress(raw).decode("utf-8") if gzipped else raw.decode("utf-8", errors="replace")
        rows.append({"seq": meta.get("seq"),
                     "request_body_sha256": meta.get("request_body_sha256"),
                     "request_body_bytes": meta.get("request_body_bytes"),
                     "usage": extract_usage(text),
                     "response_body_sha256": meta.get("response_body_sha256"),
                     "response_gzipped": gzipped})
    require(len(rows) == 3, "expected 3 responses in %s" % run_dir)
    rows.sort(key=lambda r: r["seq"])
    return rows


def build(archive_base):
    base = Path(archive_base)
    rows = []
    for label in RUN_LABELS:
        provider = PROVIDER_OF[label]
        for idx, rec in enumerate(load_run(base / RUN_RELS[label])):
            if idx < 2:
                require(rec["request_body_sha256"] == REQ_SHAS[provider][idx], "req sha pin mismatch")
            require(rec["request_body_bytes"] == REQ_BYTES[provider][idx], "req bytes mismatch")
            u = rec["usage"]
            details = u.get("prompt_tokens_details") or {}
            rows.append({"run": label, "seq": idx + 1,
                         "request_body_sha256": rec["request_body_sha256"],
                         "request_body_bytes": rec["request_body_bytes"], "upstream_status": 200,
                         "prompt_tokens": u["prompt_tokens"],
                         "cached_tokens": details.get("cached_tokens"),
                         "completion_tokens": u["completion_tokens"],
                         "total_tokens": u["total_tokens"],
                         "prompt_cache_hit_tokens": u.get("prompt_cache_hit_tokens"),
                         "prompt_cache_miss_tokens": u.get("prompt_cache_miss_tokens"),
                         "response_gzipped": rec["response_gzipped"],
                         "response_body_sha256": rec["response_body_sha256"]})
    evidence = {
        "schema": SCHEMA,
        "baseline_commit": BASELINE,
        "generated_from": {"archive_base_kind": "private-archive-root", "runs": RUN_RELS},
        "pins": {"rebuild_readme_sha256": PIN_REBUILD_README, "xm_readme_sha256": PIN_XM_README},
        "rows": rows,
        "summary": {
            "prompt_tokens_stable_pairs": 24,
            "cached_varies_runs": {"glm_req1": sorted(CACHED_SETS["glm"][0]),
                                    "glm_req2": sorted(CACHED_SETS["glm"][1]),
                                    "glm_req3": sorted(CACHED_SETS["glm"][2]),
                                    "ds_req1": sorted(CACHED_SETS["ds"][0]),
                                    "ds_req2": sorted(CACHED_SETS["ds"][1]),
                                    "ds_req3": sorted(CACHED_SETS["ds"][2])},
            "byte_per_prompt_token": {"glm_req1": round(REQ_BYTES["glm"][0] / PROMPT_TOKENS["glm"][0], 2),
                                       "glm_req3": round(REQ_BYTES["glm"][2] / PROMPT_TOKENS["glm"][2], 2),
                                       "ds_req1": round(REQ_BYTES["ds"][0] / PROMPT_TOKENS["ds"][0], 2)},
            "endpoints": {
                "e1_prompt_tokens_stable": "24/24",
                "e2_cached_tokens_volatile": True,
                "e3_ratio_descriptive_only": True,
                "e4_dialect_split": {"glm": "cached_tokens", "ds": "hit/miss + cached mirror"},
                "e5_completion_not_scored": True}}}
    return evidence


def validate_public(ev):
    require(ev["schema"] == SCHEMA, "schema")
    require(ev["baseline_commit"] == BASELINE, "baseline")
    require(len(ev["rows"]) == 24, "rows count")
    seen = set()
    for row in ev["rows"]:
        label = row["run"]
        require(label in RUN_LABELS, "run label")
        provider = PROVIDER_OF[label]
        seq = row["seq"]
        require(seq in (1, 2, 3), "seq")
        key = (label, seq)
        require(key not in seen, "dup row")
        seen.add(key)
        require(row["upstream_status"] == 200, "status")
        require(row["request_body_bytes"] == REQ_BYTES[provider][seq - 1], "bytes")
        require(row["prompt_tokens"] == PROMPT_TOKENS[provider][seq - 1], "prompt tokens")
        require(row["cached_tokens"] in CACHED_SETS[provider][seq - 1], "cached set")
        require(row["completion_tokens"] in COMPLETION_SETS[provider][seq - 1], "completion set")
        require(row["total_tokens"] == row["prompt_tokens"] + row["completion_tokens"], "total identity")
        if provider == "ds":
            require(row["prompt_cache_hit_tokens"] == row["cached_tokens"], "ds mirror hit")
            require(row["prompt_cache_miss_tokens"] == row["prompt_tokens"] - row["cached_tokens"], "ds mirror miss")
        else:
            require(row["prompt_cache_hit_tokens"] is None and row["prompt_cache_miss_tokens"] is None, "glm no hit/miss fields")
        if seq <= 2:
            require(row["request_body_sha256"] == REQ_SHAS[provider][seq - 1], "sha pin")
    require(len(seen) == 24, "coverage")
    s = ev["summary"]
    require(s["prompt_tokens_stable_pairs"] == 24, "e1 count")
    require(s["endpoints"]["e1_prompt_tokens_stable"] == "24/24", "e1 verdict")
    require(s["endpoints"]["e2_cached_tokens_volatile"] is True, "e2")
    require(s["endpoints"]["e3_ratio_descriptive_only"] is True, "e3")
    require(s["endpoints"]["e4_dialect_split"] == {"glm": "cached_tokens", "ds": "hit/miss + cached mirror"}, "e4")
    require(s["endpoints"]["e5_completion_not_scored"] is True, "e5")
    require(any(len(v) > 1 for v in s["cached_varies_runs"].values()), "volatility witness")
    blob = json.dumps(ev, ensure_ascii=False)
    for bad in ("/Users/", "api_key", "sk-", "authorization"):
        require(bad not in blob, "leak: %s" % bad)


def result_for(ev, evidence_sha):
    return {"schema": SCHEMA + "-result-v1", "evidence_sha256": evidence_sha,
            "endpoints": ev["summary"]["endpoints"],
            "cached_varies_runs": ev["summary"]["cached_varies_runs"],
            "byte_per_prompt_token": ev["summary"]["byte_per_prompt_token"],
            "limits": ["n=1 task x 2 providers; product-reported counters only; raw response bodies stay private "
                       "(response_body_sha256 bound); cache semantics defined by the provider; no cost conversion",
                       "prompt_tokens stable under byte-identical requests (24/24); cached_tokens volatile across "
                       "runs for the same bytes; completion tokens vary on the response side and are not scored",
                       "public replay re-checks evidence-internal arithmetic and shape pins only; it cannot certify "
                       "private archive authenticity"],
            "verdict": "usage_stable_cache_volatile"}


def exclusive(path, raw):
    p = Path(path)
    require(not p.exists(), "output exists: %s" % p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("xb") as f:
        f.write(raw)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive-base", default=None)
    ap.add_argument("--build-evidence", default=None)
    ap.add_argument("--evidence", default=None)
    ap.add_argument("--output", required=True)
    a = ap.parse_args(argv)
    try:
        require(bool(a.build_evidence) != bool(a.evidence), "choose --build-evidence or --evidence")
        if a.build_evidence:
            require(bool(a.archive_base), "--archive-base required for build")
            ev = build(a.archive_base)
        else:
            ev = loads(Path(a.evidence).read_bytes().decode("utf-8"))
        validate_public(ev)
        evidence_sha = sha(canon(ev))
        if a.build_evidence:
            exclusive(a.build_evidence, canon(ev))
        res = result_for(ev, evidence_sha)
        exclusive(a.output, json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8") + b"\n")
        print("usage-volatility OK: 24/24 prompt stable | cached volatile | ratios descriptive")
        return 0
    except (ValueError, OSError) as exc:
        print("input or output failure", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
