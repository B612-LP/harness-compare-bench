#!/usr/bin/env python3
"""请求侧跨运行重建验证：R-A 第二次捕获执行报告的复算器。

协议：同目录 README.md（执行报告）+ ../请求侧跨运行预注册-2026-11-16/README.md（v3 预注册）。
run1 私档 = DSH请求侧最小捕获包的 capture 目录（requests/001-003.request.bin）。
run2 私档 = capture-r2 私档（同结构）。公开证据不含请求正文。
"""
import argparse
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.dirname(os.path.dirname(HERE))
BASELINE = "6eec2ace862a41f03d2b0bfebfd387a48e08d0cd"
SCHEMA = "req-side-rebuild-evidence-v1"
PREREG_SHA = "fb9a8c4a712566f080b3ecd0453a20c2a844362921a6f4eade7619c7c5a7478e"
CAPTURE_README_SHA = "a26c7ec7df5dc052ce708434a3cbfa2b50deca2745effa1b91a5877f279c04e7"
CAPTURE_RESULT_SHA = "3de57557fe7f3c74e6abc041e5181fc415595299b9678ed59d271f8abe596357"
CAPTURE_VERIFY_SHA = "de8abc83118f5063effa1165c67f078c2d5caaadd0e2da2bb4eb2a3dff0f0e28"
REQ1_SHA = "92220699f215bbdfe0faa392587b8fc43ad6793f10da6baf8b7541518120ac10"
REQ2_SHA = "9f2b6b3e9b76dde704dd763efc1e60992ec2c798c987ae577c784ddd63e34e76"
REQ3_R1_SHA = "19e98d96ebfb3ade2dac6315b2f61f8fe45d50dcc9dca9fb8c888213cf06b8b4"
REQ3_R2_SHA = "e14ff634dc415fc31ec9bdb387afdb4e2139bfd3ed475c895af84256b777bf67"
REQ_SHAS = {"run1": [REQ1_SHA, REQ2_SHA, REQ3_R1_SHA], "run2": [REQ1_SHA, REQ2_SHA, REQ3_R2_SHA]}
EXPECTED_STATUSES = [200, 200, 200]
CALL_ID_RE = re.compile(r"^call_[0-9a-f]{24}$")
DIFF_LEAVES_EXPECTED = 4
REQ3_APPEND_DELTA = 1016
LIMITS = [
    "n=1 run pair; same task/workspace/profile-chain/model only; no generalization",
    "bytes not tokens; response bodies are model outputs and out of scope",
    "public evidence carries SHA pins and structure only, not request bodies",
    "byte identity of req1/req2 recorded as equal-SHA fact; bodies stay private",
]


def require(cond, msg):
    if not cond:
        raise ValueError(msg)


def _reject_const(text):
    raise ValueError("non-finite number in JSON: %s" % text[:32])


def loads(raw):
    def no_dup(pairs):
        seen = {}
        for k, v in pairs:
            require(k not in seen, "duplicate JSON key: %s" % k)
            seen[k] = v
        return seen
    return json.loads(raw.decode("utf-8"), object_pairs_hook=no_dup, parse_constant=_reject_const)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_pinned(path, expected):
    raw = open(path, "rb").read()
    require(sha(raw) == expected, "pinned file hash mismatch: %s" % os.path.basename(path))
    return raw


def flatten(obj, path=""):
    out = {}
    if isinstance(obj, dict):
        for k in obj:
            out.update(flatten(obj[k], "%s.%s" % (path, k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, "%s[%d]" % (path, i)))
    else:
        out[path] = obj
    return out


def content_descriptor(message):
    content = message.get("content")
    if content is None:
        return [message.get("role"), "none", 0]
    if isinstance(content, str):
        return [message.get("role"), "str", len(content.encode("utf-8"))]
    return [message.get("role"), type(content).__name__, -1]


def load_run(root, label):
    bodies = []
    for i in (1, 2, 3):
        p = os.path.join(root, "requests", "00%d.request.bin" % i)
        raw = open(p, "rb").read()
        require(sha(raw) == REQ_SHAS[label][i - 1], "%s request %d byte hash mismatch" % (label, i))
        bodies.append(raw)
    parsed = [loads(b) for b in bodies]
    summary_path = os.path.join(root, "summary.jsonl")
    statuses = []
    if os.path.exists(summary_path):
        for line in open(summary_path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            require(row["method"] == "POST", "unexpected method in summary")
            require(row["upstream_status"] == 200, "non-200 upstream status in summary")
            statuses.append(row["upstream_status"])
    return {"bodies": bodies, "parsed": parsed, "statuses": statuses}


def diff_leaves(a, b):
    fa, fb = flatten(a), flatten(b)
    keys = sorted(set(fa) | set(fb))
    out = []
    for k in keys:
        if k not in fa or k not in fb:
            out.append(k)
        elif fa[k] != fb[k]:
            out.append(k)
    return out, fa, fb


def classify_leaf(path, value_a, value_b):
    tail = path.rsplit(".", 1)[-1]
    is_call_id_path = tail in ("id", "tool_call_id")
    vals_ok = CALL_ID_RE.match(str(value_a)) and CALL_ID_RE.match(str(value_b))
    if is_call_id_path and vals_ok:
        return "provider_call_id"
    return "UNEXPECTED"


def build(root, run1_root, run2_root):
    readme_path = os.path.join(root, "4-打分细则", "请求侧跨运行重建验证-2026-11-16", "README.md")
    readme_sha = sha(read_pinned(readme_path, sha(open(readme_path, "rb").read())))
    for rel, expected in [
        ("4-打分细则/请求侧跨运行预注册-2026-11-16/README.md", PREREG_SHA),
        ("4-打分细则/DSH请求侧最小捕获-2026-11-16/README.md", CAPTURE_README_SHA),
        ("4-打分细则/DSH请求侧最小捕获-2026-11-16/result.json", CAPTURE_RESULT_SHA),
        ("4-打分细则/DSH请求侧最小捕获-2026-11-16/verify.py", CAPTURE_VERIFY_SHA),
    ]:
        read_pinned(os.path.join(root, rel), expected)
    r1 = load_run(run1_root, "run1")
    r2 = load_run(run2_root, "run2")
    endpoints = {
        "req1": {"equal": REQ1_SHA == REQ1_SHA, "sha": REQ1_SHA},
        "req2": {"equal": True, "sha": REQ2_SHA},
        "req3": {"equal": False, "sha_run1": REQ3_R1_SHA, "sha_run2": REQ3_R2_SHA},
    }
    leaves, fa, fb = diff_leaves(r1["parsed"][2], r2["parsed"][2])
    require(len(leaves) == DIFF_LEAVES_EXPECTED, "req3 diff leaf count %d != %d" % (len(leaves), DIFF_LEAVES_EXPECTED))
    leaf_rows = []
    classes = set()
    for p in leaves:
        cls = classify_leaf(p, fa.get(p), fb.get(p))
        classes.add(cls)
        leaf_rows.append({
            "path": p,
            "class": cls,
            "sha_run1_value": sha(json.dumps(fa.get(p), ensure_ascii=False, sort_keys=True).encode("utf-8")) if p in fa else None,
            "sha_run2_value": sha(json.dumps(fb.get(p), ensure_ascii=False, sort_keys=True).encode("utf-8")) if p in fb else None,
        })
    require(classes == {"provider_call_id"}, "unexpected diff classes: %s" % sorted(classes))
    prefix_identity = r2["parsed"][2]["messages"][: len(r2["parsed"][0]["messages"])] == r2["parsed"][0]["messages"]
    require(prefix_identity, "run2 req1 not content-level prefix of run2 req3")
    appended = [content_descriptor(m) for m in r2["parsed"][2]["messages"][len(r2["parsed"][0]["messages"]):]]
    appended_r1 = [content_descriptor(m) for m in r1["parsed"][2]["messages"][len(r1["parsed"][0]["messages"]):]]
    require(appended == appended_r1, "appended message descriptors differ across runs")
    delta_r1 = len(r1["bodies"][2]) - len(r1["bodies"][0])
    delta_r2 = len(r2["bodies"][2]) - len(r2["bodies"][0])
    require(delta_r1 == delta_r2 == REQ3_APPEND_DELTA, "append byte delta mismatch: %d/%d" % (delta_r1, delta_r2))
    statuses = r2["statuses"]
    require(statuses == EXPECTED_STATUSES, "run2 statuses %s != %s" % (statuses, EXPECTED_STATUSES))
    evidence = {
        "schema": SCHEMA,
        "baseline": BASELINE,
        "readme_sha256": readme_sha,
        "pins": {
            "prereg_readme_sha256": PREREG_SHA,
            "capture_readme_sha256": CAPTURE_README_SHA,
            "capture_result_sha256": CAPTURE_RESULT_SHA,
            "capture_verify_sha256": CAPTURE_VERIFY_SHA,
            "req_sha256": {"run1": REQ_SHAS["run1"], "run2": REQ_SHAS["run2"]},
        },
        "endpoints": endpoints,
        "req3_diff": {"leaf_count": len(leaves), "leaf_rows": leaf_rows},
        "run2_prefix_identity": prefix_identity,
        "appended_descriptors": appended,
        "append_byte_delta": {"run1": delta_r1, "run2": delta_r2},
        "run2_statuses": statuses,
        "limits": LIMITS,
    }
    return evidence


def validate_public(evidence):
    require(evidence.get("schema") == SCHEMA, "bad schema")
    require(evidence.get("baseline") == BASELINE, "baseline mismatch")
    pins = evidence["pins"]
    require(pins["prereg_readme_sha256"] == PREREG_SHA, "prereg pin mismatch")
    require(pins["capture_result_sha256"] == CAPTURE_RESULT_SHA, "capture result pin mismatch")
    require(pins["req_sha256"]["run1"][0] == pins["req_sha256"]["run2"][0], "req1 equality broken in pins")
    require(pins["req_sha256"]["run1"][1] == pins["req_sha256"]["run2"][1], "req2 equality broken in pins")
    require(pins["req_sha256"]["run1"][2] != pins["req_sha256"]["run2"][2], "req3 must differ")
    rd = evidence["req3_diff"]
    require(rd["leaf_count"] == DIFF_LEAVES_EXPECTED, "leaf count mismatch")
    for row in rd["leaf_rows"]:
        require(row["class"] == "provider_call_id", "unexpected leaf class: %s" % row["class"])
        require(row["sha_run1_value"] != row["sha_run2_value"], "diff leaf values identical")
    require(evidence["run2_prefix_identity"] is True, "prefix identity must be true")
    require(evidence["append_byte_delta"] == {"run1": REQ3_APPEND_DELTA, "run2": REQ3_APPEND_DELTA}, "delta mismatch")
    require(evidence["run2_statuses"] == EXPECTED_STATUSES, "status mismatch")
    require(evidence["limits"] == LIMITS, "limits text changed")
    return True


def result_for(evidence, evidence_sha):
    validate_public(evidence)
    return {
        "schema": "req-side-rebuild-result-v1",
        "evidence_sha256": evidence_sha,
        "readme_sha256": evidence["readme_sha256"],
        "baseline": BASELINE,
        "primary_verdict": "identity_assembly_stable",
        "req1": {"equal": True, "sha256": REQ1_SHA},
        "req2": {"equal": True, "sha256": REQ2_SHA},
        "req3": {"equal": False, "sha256_run1": REQ3_R1_SHA, "sha256_run2": REQ3_R2_SHA,
                 "diff_leaf_count": evidence["req3_diff"]["leaf_count"],
                 "diff_class": "provider_call_id_only"},
        "run2_prefix_identity": True,
        "appended_descriptors": evidence["appended_descriptors"],
        "append_byte_delta": evidence["append_byte_delta"],
        "run2_statuses": evidence["run2_statuses"],
        "limits": LIMITS,
    }


def exclusive(path, raw):
    full = os.path.abspath(path)
    require(not os.path.exists(full), "output path already exists: %s" % path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    fd = os.open(full, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        os.write(fd, raw)
    finally:
        os.close(fd)


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--run1-root", help="capture-1 private capture dir")
    ap.add_argument("--run2-root", help="capture-r2 private capture dir")
    ap.add_argument("--build-evidence")
    ap.add_argument("--evidence")
    ap.add_argument("--output", required=True)
    args = ap.parse_args(argv)
    try:
        if args.build_evidence:
            require(args.run1_root and args.run2_root, "--build-evidence needs --run1-root and --run2-root")
            evidence = build(args.root, args.run1_root, args.run2_root)
            e_raw = canonical(evidence)
            result = result_for(evidence, sha(e_raw))
            exclusive(args.build_evidence, e_raw + b"\n")
            exclusive(args.output, json.dumps(result, ensure_ascii=False, indent=1).encode("utf-8") + b"\n")
            print("built evidence=%s primary=%s req3_diff=%d" % (
                sha(e_raw)[:16], result["primary_verdict"], result["req3"]["diff_leaf_count"]))
        else:
            require(args.evidence, "either --build-evidence or --evidence is required")
            evidence = loads(open(args.evidence, "rb").read())
            result = result_for(evidence, sha(open(args.evidence, "rb").read().rstrip(b"\n")))
            exclusive(args.output, json.dumps(result, ensure_ascii=False, indent=1).encode("utf-8") + b"\n")
            print("public replay ok primary=%s" % result["primary_verdict"])
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print("error: input or output failure", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
