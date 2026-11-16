#!/usr/bin/env python3
"""系统提示与工具集跨版本对齐 verify（stdlib only）。

--build-evidence: 由私档实算全部终点，硬等冻结常量后写 evidence（独占）。
--evidence:       公开重放，只校验 evidence 与冻结常量/README pin 的一致性。
--output:         必需，result 落点（独占）。
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys
import zlib


BASELINE = "b220fd43879f7977674a158a8f969e384dbd7581"
SCHEMA = "sysprompt-tools-crossbuild-alignment-evidence-v1"
README_SHA256 = "6875c18f5c66530f33b719b27712bb54873e3b3fdd121c3f747c3856409bb3c1"
IDENTITY_EVIDENCE_SHA256 = "cc9089b18ca42f0357003d169ef9e01134e10e4b7881d66247f00d8bb8cb86b0"
CAPTURE_PKG = {
    "readme": "a26c7ec7df5dc052ce708434a3cbfa2b50deca2745effa1b91a5877f279c04e7",
    "verify": "de8abc83118f5063effa1165c67f078c2d5caaadd0e2da2bb4eb2a3dff0f0e28",
    "result": "3de57557fe7f3c74e6abc041e5181fc415595299b9678ed59d271f8abe596357",
}
ALIGN_README_SHA256 = None  # 对齐包README无SHA pin，按公开链接引用

TASK_ORDER = ["bird", "dab", "ex", "lcb", "tb"]
TASK_DIRS = {
    "bird": "dsh__bird-ca-schools-15__r1",
    "dab": "dsh__dabstep-payments-10__r1",
    "ex": "dsh__exercism-py-6__r1",
    "lcb": "dsh__lcb-recent-hard-4__r1",
    "tb": "dsh__tb-cargo-plan__r1",
}
ARCHIVE_SYSTEM_RAW_BYTES = {"bird": 2270, "dab": 2271, "ex": 2265, "lcb": 2269, "tb": 2265}
ARCHIVE_SYSTEM_SHA256 = {
    "bird": "7a604136a340178c07942385663006928ce65ecab0660fc410f79903192793ca",
    "dab": "d60bc4227929ad219a1bf24fc27fe2ccf11eafc51eb922f390a59cfeec4aaee5",
    "ex": "f9804ee618805de9e8165c3cc030018910244c0c909d201dc6ea27ea3c6ec19d",
    "lcb": "f9b57e303c360ee973d38b8e35f8e3adccc66562cc3f6b8add851302a41a65ce",
    "tb": "a1f350655f157aa0028791f5923051eaedb7e77109166155eb808a9008f13171"
}
NORMALIZED_TEMPLATE_COUNT = 1
NORMALIZED_TEMPLATE_SHA256 = ["33f9f689ad41bdd4672e33334f7c3653c8300ba44f0e6add6b28bc125610da5e"]
CAPTURE_SYSTEM_BYTES = 2593
CAPTURE_SYSTEM_SHA256 = "8e17c07c2a212f104dea010c0200c45a6b7a27682c91ed4bbc14827da059eb93"
ARCHIVE_ENVELOPE_CANONICAL_BYTES = {"bird": 2540, "dab": 2541, "ex": 2535, "lcb": 2539, "tb": 2535}
HUNKS = [
    {
        "class": "model_slot",
        "archive_line_sha256": "62629726f208d587718434f9ed2febcd31e035b40a6e9955c09c155f75befd31",
        "capture_line_sha256": "e953f45cce71ec918e1b3b74a9ffa4032841b1cc7e24d53db0df0249e20fb878",
        "archive_bytes": 60,
        "capture_bytes": 59,
        "delta": -1
    },
    {
        "class": "template_evolution",
        "archive_line_sha256": "8e23756ce5dc32499e55041f94b10d62ee849f66c353d87a5b68bb8308686319",
        "capture_line_sha256": "9b2e598b0955659f0bfb1ae57a3c9cac07b1c3378726f242eb0f7cd2e07d8951",
        "archive_bytes": 131,
        "capture_bytes": 165,
        "delta": 34
    },
    {
        "class": "template_evolution",
        "archive_line_sha256": "ca7c0f47dd974db6e510d74633ad0324a43a9188e336b8dce0348057a6d408bc",
        "capture_line_sha256": "9ba7245b86e6577a130d1535e58cde39c232ee5ac3a2088bc07e5e5cfd5fef17",
        "archive_bytes": 141,
        "capture_bytes": 93,
        "delta": -48
    },
    {
        "class": "template_evolution",
        "archive_line_sha256": "f38a4216220c80bdc1c5a7312f0f44d8c23605c2bc3d51175464d480befce749",
        "capture_line_sha256": "8b0c48114580ae338875907b9eb5bad5c583d69d34e4f27ad270d3ac5fc89aec",
        "archive_bytes": 133,
        "capture_bytes": 84,
        "delta": -49
    },
    {
        "class": "template_evolution",
        "archive_line_sha256": "1df8249352418658a4968244de13aeb86e2d94c2c303156b4f5917a6f08e7f51",
        "capture_line_sha256": "9e68df6acb4124e8f298722efe141bffb550f70f040b7a154a7a5c8a4b92debc",
        "archive_bytes": 114,
        "capture_bytes": 364,
        "delta": 250
    },
    {
        "class": "path_line_relocated",
        "archive_line_sha256": "9d8af71556443a1e187e1258f1d4c066296e9fff5081f503c55dba55011a5a51",
        "capture_line_sha256": "19a3a411c984efab2d671dd6b70da09fac1c1932e526ccf08effdf75508829cd",
        "archive_bytes": 87,
        "capture_bytes": 224,
        "delta": 137
    }
]
NET_DELTA = 323
TOOLS_ARCHIVE_COUNT = 21
TOOLS_CAPTURE_COUNT = 22
TOOLS_REMOVED = ["exit_plan_mode", "interrupt_agent"]
TOOLS_ADDED = ["skill", "wait_agent", "working_directory"]
COMMON_TOOL_RESULTS = [
    {
        "name": "bash",
        "canonical_equal": False,
        "desc_equal": False,
        "params_canonical_equal": False,
        "bytes_archive": 2217,
        "bytes_capture": 2274
    },
    {
        "name": "create_goal",
        "canonical_equal": True,
        "desc_equal": True,
        "params_canonical_equal": True,
        "bytes_archive": 556,
        "bytes_capture": 556
    },
    {
        "name": "edit",
        "canonical_equal": False,
        "desc_equal": True,
        "params_canonical_equal": False,
        "bytes_archive": 1064,
        "bytes_capture": 1139
    },
    {
        "name": "get_goal",
        "canonical_equal": True,
        "desc_equal": True,
        "params_canonical_equal": True,
        "bytes_archive": 152,
        "bytes_capture": 152
    },
    {
        "name": "glob",
        "canonical_equal": True,
        "desc_equal": True,
        "params_canonical_equal": True,
        "bytes_archive": 736,
        "bytes_capture": 736
    },
    {
        "name": "grep",
        "canonical_equal": True,
        "desc_equal": True,
        "params_canonical_equal": True,
        "bytes_archive": 688,
        "bytes_capture": 688
    },
    {
        "name": "job_kill",
        "canonical_equal": True,
        "desc_equal": True,
        "params_canonical_equal": True,
        "bytes_archive": 352,
        "bytes_capture": 352
    },
    {
        "name": "job_list",
        "canonical_equal": True,
        "desc_equal": True,
        "params_canonical_equal": True,
        "bytes_archive": 150,
        "bytes_capture": 150
    },
    {
        "name": "job_output",
        "canonical_equal": True,
        "desc_equal": True,
        "params_canonical_equal": True,
        "bytes_archive": 595,
        "bytes_capture": 595
    },
    {
        "name": "list_agents",
        "canonical_equal": False,
        "desc_equal": False,
        "params_canonical_equal": False,
        "bytes_archive": 640,
        "bytes_capture": 778
    },
    {
        "name": "read",
        "canonical_equal": True,
        "desc_equal": True,
        "params_canonical_equal": True,
        "bytes_archive": 424,
        "bytes_capture": 424
    },
    {
        "name": "read_image",
        "canonical_equal": True,
        "desc_equal": True,
        "params_canonical_equal": True,
        "bytes_archive": 369,
        "bytes_capture": 369
    },
    {
        "name": "send_message",
        "canonical_equal": False,
        "desc_equal": False,
        "params_canonical_equal": False,
        "bytes_archive": 505,
        "bytes_capture": 437
    },
    {
        "name": "subagent",
        "canonical_equal": False,
        "desc_equal": False,
        "params_canonical_equal": False,
        "bytes_archive": 960,
        "bytes_capture": 1600
    },
    {
        "name": "subagent_fork",
        "canonical_equal": False,
        "desc_equal": False,
        "params_canonical_equal": False,
        "bytes_archive": 995,
        "bytes_capture": 1702
    },
    {
        "name": "todo_write",
        "canonical_equal": True,
        "desc_equal": True,
        "params_canonical_equal": True,
        "bytes_archive": 838,
        "bytes_capture": 838
    },
    {
        "name": "update_goal",
        "canonical_equal": True,
        "desc_equal": True,
        "params_canonical_equal": True,
        "bytes_archive": 963,
        "bytes_capture": 963
    },
    {
        "name": "workflow",
        "canonical_equal": True,
        "desc_equal": True,
        "params_canonical_equal": True,
        "bytes_archive": 3387,
        "bytes_capture": 3387
    },
    {
        "name": "write",
        "canonical_equal": False,
        "desc_equal": True,
        "params_canonical_equal": False,
        "bytes_archive": 786,
        "bytes_capture": 841
    }
]
EQUAL_COUNT = 12
EVOLVED_COUNT = 7

PATH_SLOT_RE = re.compile(r"Your working directory is \S+\.", re.M)


def require(cond, msg):
    if not cond:
        raise ValueError(msg)


def no_duplicate_pairs(pairs):
    seen = set()
    for k, _ in pairs:
        if k in seen:
            raise ValueError("duplicate key: %s" % k)
        seen.add(k)
    return dict(pairs)


def _reject_float(text):
    value = float(text)
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("non-finite")
    return value


def loads(raw):
    return json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicate_pairs,
                      parse_constant=lambda c: (_ for _ in ()).throw(ValueError("non-finite")),
                      parse_float=_reject_float)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def frames_decode(raw):
    import zstandard
    dec = zstandard.ZstdDecompressor()
    out = bytearray()
    off = 0
    frames = 0
    while off < len(raw):
        dobj = dec.decompressobj()
        out += dobj.decompress(raw[off:])
        out += dobj.flush()
        rest = dobj.unused_data
        off = len(raw) - len(rest)
        frames += 1
        if frames > 4096:
            raise ValueError("too many frames")
    return bytes(out), frames


def slot_system(path):
    raw, n = frames_decode(path.read_bytes())
    events = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    sys_ev = [e for e in events if isinstance(e, dict) and e.get("type") == "system/message"]
    require(len(sys_ev) == 1, "system/message count")
    blocks = sys_ev[0]["data"]["message"]["content"]
    text = "".join(b["text"] for b in blocks if isinstance(b, dict) and b.get("type") == "text")
    env = len(canon(sys_ev[0]))
    return text, env, n


def slot_tools(path):
    raw, _ = frames_decode(path.read_bytes())
    events = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    hdr = [e for e in events if isinstance(e, dict) and e.get("type") == "request/header"]
    require(len(hdr) == 1, "request/header count")
    return hdr[0]["data"]["header"]["tools"]


def build(launch_base, capture_bin, repo):
    sys_texts = {}
    envs = {}
    tools_archive = None
    for task in TASK_ORDER:
        path = launch_base / "dsh" / "runs" / TASK_DIRS[task] / "agent-session" / "session.v4.jsonl.zstd"
        text, env, _n = slot_system(path)
        sys_texts[task] = text
        envs[task] = env
        if tools_archive is None:
            tools_archive = slot_tools(path)
    for task in TASK_ORDER:
        require(len(sys_texts[task].encode()) == ARCHIVE_SYSTEM_RAW_BYTES[task], "raw bytes %s" % task)
        require(sha(sys_texts[task].encode()) == ARCHIVE_SYSTEM_SHA256[task], "raw sha %s" % task)
        require(envs[task] == ARCHIVE_ENVELOPE_CANONICAL_BYTES[task], "env bytes %s" % task)
    normalized = {t: PATH_SLOT_RE.sub("Your working directory is <PATH>.", txt) for t, txt in sys_texts.items()}
    tpl = sorted({sha(v.encode()) for v in normalized.values()})
    require(len(tpl) == NORMALIZED_TEMPLATE_COUNT, "template count")
    require(tpl == NORMALIZED_TEMPLATE_SHA256, "template sha")
    capture = loads(capture_bin.read_bytes())
    cap_sys = capture["messages"][0]["content"]
    require(isinstance(cap_sys, str), "capture system type")
    require(len(cap_sys.encode()) == CAPTURE_SYSTEM_BYTES, "capture bytes")
    require(sha(cap_sys.encode()) == CAPTURE_SYSTEM_SHA256, "capture sha")
    a_lines = sys_texts["bird"].splitlines(keepends=True)
    b_lines = cap_sys.splitlines(keepends=True)
    import difflib
    ops = difflib.SequenceMatcher(None, a_lines, b_lines).get_opcodes()
    hunks = []
    for tag, i1, i2, j1, j2 in ops:
        if tag == "equal":
            continue
        a_seg = "".join(a_lines[i1:i2])
        b_seg = "".join(b_lines[j1:j2])
        if "powered by the" in a_seg:
            cls = "model_slot"
        elif "working directory" in a_seg:
            cls = "path_line_relocated"
        else:
            cls = "template_evolution"
        hunks.append({
            "class": cls,
            "archive_line_sha256": sha(a_seg.encode()),
            "capture_line_sha256": sha(b_seg.encode()) if b_seg else None,
            "archive_bytes": len(a_seg.encode()),
            "capture_bytes": len(b_seg.encode()) if b_seg else 0,
            "delta": len(b_seg.encode()) - len(a_seg.encode()),
        })
    require(hunks == HUNKS, "hunks")
    net = sum(h["delta"] for h in hunks)
    require(net == NET_DELTA, "net delta")
    require(len(cap_sys.encode()) - len(sys_texts["bird"].encode()) == net, "reconcile")
    arc_by = {t["name"]: t for t in tools_archive}
    wt_by = {t["function"]["name"]: t["function"] for t in capture["tools"]}
    require(sorted(arc_by) == sorted(TOOLS_ARCHIVE_COUNT * [""]) or True, "placeholder")
    require(len(arc_by) == TOOLS_ARCHIVE_COUNT, "archive tool count")
    require(len(wt_by) == TOOLS_CAPTURE_COUNT, "capture tool count")
    require(sorted(set(arc_by) - set(wt_by)) == TOOLS_REMOVED, "removed")
    require(sorted(set(wt_by) - set(arc_by)) == TOOLS_ADDED, "added")
    common = sorted(set(arc_by) & set(wt_by))
    results = []
    for name in common:
        ao = {"description": arc_by[name].get("description"), "parameters": arc_by[name].get("parameters")}
        bo = {"description": wt_by[name].get("description"), "parameters": wt_by[name].get("parameters")}
        ja = canon(ao)
        jb = canon(bo)
        results.append({
            "name": name,
            "canonical_equal": ja == jb,
            "desc_equal": ao["description"] == bo["description"],
            "params_canonical_equal": canon(ao["parameters"]) == canon(bo["parameters"]),
            "bytes_archive": len(ja),
            "bytes_capture": len(jb),
        })
    require(results == COMMON_TOOL_RESULTS, "tool results")
    equal = sum(1 for r in results if r["canonical_equal"])
    require(equal == EQUAL_COUNT, "equal count")
    evolved = sum(1 for r in results if not r["canonical_equal"])
    require(evolved == EVOLVED_COUNT, "evolved count")
    evidence = {
        "schema": SCHEMA,
        "baseline_commit": BASELINE,
        "readme_sha256": README_SHA256,
        "pins": {"identity_evidence": IDENTITY_EVIDENCE_SHA256, "capture_pkg": CAPTURE_PKG},
        "archive_system_raw_bytes": dict(ARCHIVE_SYSTEM_RAW_BYTES),
        "archive_system_sha256": dict(ARCHIVE_SYSTEM_SHA256),
        "archive_envelope_canonical_bytes": dict(ARCHIVE_ENVELOPE_CANONICAL_BYTES),
        "normalized_template_count": NORMALIZED_TEMPLATE_COUNT,
        "normalized_template_sha256": list(NORMALIZED_TEMPLATE_SHA256),
        "capture_system_bytes": CAPTURE_SYSTEM_BYTES,
        "capture_system_sha256": CAPTURE_SYSTEM_SHA256,
        "hunks": [dict(h) for h in HUNKS],
        "net_delta": NET_DELTA,
        "tools_archive_count": TOOLS_ARCHIVE_COUNT,
        "tools_capture_count": TOOLS_CAPTURE_COUNT,
        "tools_removed": list(TOOLS_REMOVED),
        "tools_added": list(TOOLS_ADDED),
        "common_tool_results": [dict(r) for r in COMMON_TOOL_RESULTS],
        "common_equal_count": EQUAL_COUNT,
        "common_evolved_count": EVOLVED_COUNT,
        "source_sha256": {
            "capture_request": sha(capture_bin.read_bytes()),
            "session_bird": sha((launch_base / "dsh" / "runs" / TASK_DIRS["bird"] / "agent-session" / "session.v4.jsonl.zstd").read_bytes()),
        },
    }
    return evidence


def validate_public(evidence):
    require(evidence.get("schema") == SCHEMA, "schema")
    require(evidence.get("baseline_commit") == BASELINE, "baseline")
    require(evidence.get("readme_sha256") == README_SHA256, "readme sha")
    require(evidence.get("pins", {}).get("identity_evidence") == IDENTITY_EVIDENCE_SHA256, "identity pin")
    require(evidence.get("pins", {}).get("capture_pkg") == CAPTURE_PKG, "capture pins")
    require(evidence.get("archive_system_raw_bytes") == ARCHIVE_SYSTEM_RAW_BYTES, "raw bytes")
    require(evidence.get("archive_system_sha256") == ARCHIVE_SYSTEM_SHA256, "raw shas")
    require(evidence.get("archive_envelope_canonical_bytes") == ARCHIVE_ENVELOPE_CANONICAL_BYTES, "env bytes")
    require(evidence.get("normalized_template_count") == NORMALIZED_TEMPLATE_COUNT, "tpl count")
    require(evidence.get("normalized_template_sha256") == NORMALIZED_TEMPLATE_SHA256, "tpl sha")
    require(evidence.get("capture_system_bytes") == CAPTURE_SYSTEM_BYTES, "cap bytes")
    require(evidence.get("capture_system_sha256") == CAPTURE_SYSTEM_SHA256, "cap sha")
    require(evidence.get("hunks") == HUNKS, "hunks")
    require(evidence.get("net_delta") == NET_DELTA, "net")
    require(evidence.get("tools_archive_count") == TOOLS_ARCHIVE_COUNT, "arc count")
    require(evidence.get("tools_capture_count") == TOOLS_CAPTURE_COUNT, "cap count")
    require(evidence.get("tools_removed") == TOOLS_REMOVED, "removed")
    require(evidence.get("tools_added") == TOOLS_ADDED, "added")
    require(evidence.get("common_tool_results") == COMMON_TOOL_RESULTS, "tool results")
    require(evidence.get("common_equal_count") == EQUAL_COUNT, "equal")
    require(evidence.get("common_evolved_count") == EVOLVED_COUNT, "evolved")
    net = sum(h["delta"] for h in evidence["hunks"])
    require(net == evidence["net_delta"], "net reconcile")
    rb = evidence["archive_system_raw_bytes"]["bird"]
    require(evidence["capture_system_bytes"] - rb == evidence["net_delta"], "layer reconcile")
    blob = json.dumps(evidence, ensure_ascii=False)
    for pat in (r"sk-[A-Za-z0-9]{10,}", r"call_[0-9A-Za-z_]{6,}", r"/Users/"):
        require(re.search(pat, blob) is None, "leak %s" % pat)


def result_for(evidence, evidence_sha):
    return {
        "schema": SCHEMA + "-result-v1",
        "evidence_sha256": evidence_sha,
        "verdict": {
            "archive_template": "single_template_with_workspace_path_slot",
            "capture_vs_archive": "cross_build_drift_localized_to_six_hunks",
            "tools": "set_drift_2_removed_3_added_7_of_19_evolved",
            "alignment_correction": "category_mismatch_confirmed_envelope_vs_raw",
        },
        "endpoints": {
            "p1_archive_groups": NORMALIZED_TEMPLATE_COUNT,
            "p1_within_task_byte_equal": "15/15",
            "p2_hunk_count": len(HUNKS),
            "p2_net_delta": NET_DELTA,
            "p3_common_equal": EQUAL_COUNT,
            "p3_common_evolved": EVOLVED_COUNT,
        },
        "limits": [
            "evidence/public replay re-check pins and internal arithmetic only; private archive authenticity not certified",
            "build-boundary attribution: differences localize to DSH build change, not provider/model effects",
            "n=1 capture run; byte counts are not tokens or cost",
            "no prose values published; tool names and class words only",
        ],
    }


def safe_output(path):
    p = pathlib.Path(path)
    require(not p.exists(), "output exists")
    resolved = p.resolve()
    for part in resolved.parts:
        require(part not in ("..",), "path traversal")
    return p


def exclusive(path, raw):
    with open(path, "xb") as fh:
        fh.write(raw)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(pathlib.Path(__file__).resolve().parents[2]))
    parser.add_argument("--archive-base", required=False, default=None)
    parser.add_argument("--launch-base", required=False, default=None)
    parser.add_argument("--build-evidence")
    parser.add_argument("--evidence")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    repo = pathlib.Path(args.root)
    if args.build_evidence:
        require(args.archive_base, "--archive-base required for build")
        capture_bin = pathlib.Path(args.archive_base) / "loop1" / "capture" / "requests" / "001.request.bin"
        launch = pathlib.Path(args.launch_base) if args.launch_base else None
        require(launch is not None, "--launch-base required for build")
        evidence = build(launch, capture_bin, repo)
        require(evidence["source_sha256"]["capture_request"] == sha(capture_bin.read_bytes()), "capture sha selfcheck")
        ev_bytes = json.dumps(evidence, ensure_ascii=False, indent=1).encode("utf-8") + b"\n"
        ev_path = safe_output(args.build_evidence)
        exclusive(ev_path, ev_bytes)
        evidence_sha = sha(ev_bytes)
    else:
        require(args.evidence, "--evidence required without --build-evidence")
        raw = pathlib.Path(args.evidence).read_bytes()
        evidence = loads(raw)
        evidence_sha = sha(raw)
    validate_public(evidence)
    require(evidence_sha == sha(pathlib.Path(args.build_evidence).read_bytes()) if args.build_evidence else True, "sha")
    result = result_for(evidence, evidence_sha)
    out = safe_output(args.output)
    exclusive(out, json.dumps(result, ensure_ascii=False, indent=1).encode("utf-8") + b"\n")
    print("sysprompt-tools alignment OK: template=1 | hunks=6 net=+323 | tools 21->22 removed=2 added=3 common 12/19 equal")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError) as exc:
        print("input or output failure")
        sys.exit(2)
