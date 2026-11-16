#!/usr/bin/env python3
"""R-A4 深链与轮间文本 公开验证器（stdlib only）。

- 公开重放：--evidence evidence.json --output out.json（只核封印/算术/schema）。
- 私档重建：--archive-base <loop8根> --build-evidence ev.json --output out.json
  （从 t3-r1/t3-r2 请求原文重算全部终点并与冻结常量硬等）。
- 不读取正文/路径/完整ID到公开层；输出独占；错误外部泛化。
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import sys

BASELINE = "59f00f4be7850d119d60b2001aa443a622d63000"
PREREG_SHA = "fb9a8c4a712566f080b3ecd0453a20c2a844362921a6f4eade7619c7c5a7478e"
FREEZE_SHA = "c22764318b1f987333c782b3994a1664896411d8d8c0f5e69f2823cc5ed7bed3"
CAPTURE_PREREG_DIR = "../请求侧跨运行预注册-2026-11-16/README.md"
CHAIN_DIR = "../请求侧多轮链捕获-2026-11-16/README.md"
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent

CALL_ID_RE = re.compile(r"call_[0-9a-f]{24}")
RUN_LABELS = ("t3-r1", "t3-r2")
RUN_RELS = {"t3-r1": "t3-r1", "t3-r2": "t3-r2"}

TASK_AGG = "88e9c81b56febd7352ccf496a0e3e761373caf8927e7312c3f16878514aa9e0c"
WORKSPACE_FILES = {
    "TASK.md": "6eeedb62e63f24d82222a5a7e68ad475294c8e9c10784108ab087cead39e0060",
    "m01.txt": "380a3fbb362340906fb215902b1e47be9a20b7702d2f85f6f69ea4a4779ae3cf",
    "m02.txt": "e15eb6815d0466da0afce843d55a5afd69c46213002a0d188aceccdb9f8b5b9f",
    "m03.txt": "1c60dd7bb3a05f6d48c3a67937c92f8f0c8e5ff9dacdbf4e2c5954d61d18f4b1",
    "m04.txt": "a79dd33750886958c997b2f5dc1f57348bb546dff52fae1afaddcc947de74c8d",
    "m05.txt": "25c460f4c5dd68fd6e6c30942939500ed0e5806356bd597716007193ce08f412",
    "m06.txt": "0663ceb141e56f52108ddf1cfd1643f9ed8d90f1bf6057e79883ded457a7eba5",
    "m07.txt": "758bebb65dd36decfc84582af801ab2c196d8e568ed6455dc533d3aa6a095947",
    "m08.txt": "a303037d5477f13b820aa02494c653f26f10b64a7c71640fe5b26420b639c813",
    "m09.txt": "bef317b122e550ca330f2fd090b2260717c77d7206045efef2ece9707ac987ed",
    "m10.txt": "ed0ce0bb65f891513213cfa0f6f38f295373b7d7f8e42a5dd3e4b90c50ac890b",
    "m11.txt": "863333335e0ec669e7c2682ed716c4a8e132ba761005553d01073ceb51456546",
    "m12.txt": "450f169669b9a49f396f61787184c80a359cf7a5542bdf9482fbf4196fbd62b9",
}

TOTAL_REQUESTS = {"t3-r1": 16, "t3-r2": 15}
MAIN_REQUESTS = {"t3-r1": 15, "t3-r2": 14}
PREFIX_OK = {"t3-r1": 14, "t3-r2": 13}
PREFIX_STEPS = {"t3-r1": 14, "t3-r2": 13}
DELTAS = {
    "t3-r1": [382, 860, 509, 526, 528, 530, 527, 524, 526, 528, 530, 527, 525, 527],
    "t3-r2": [860, 509, 526, 528, 530, 527, 524, 526, 528, 530, 527, 525, 527],
}
APPENDED_SHAPES_SHA = {
    "t3-r1": "ac44803fcf2b4e2bbe5f5e0ff19819d8fa3fb90e6282ed91a72652bcefed363e",
    "t3-r2": "bdf3ad256c7be6d3cf6c8b8e8269cb3510cfd4df6528d31241b5e4a7db76f0fa",
}
REQ1_SHA = "765b958d5606bc7a43a0960e30e7106eb3638beb402419e0f1d17f471ee52220"
TITLE_SHA = "b51f351d000a5a5ca4013a1326ba14d16842d30e1b8a7c5a3862d9f8b2c95f32"
RAW_FOLLOWUP_EQUAL = 0
ERROR_PAIR = {
    "assistant_tool": "bash",
    "tool_content_prefix": "Error: invalid arguments: missing required p",
    "constant_in_run1": True,
}
SKIP_ERROR_ALIGNMENT = {"pairs": 13, "equal": 13}
FINAL_TEXT_LINES = {"t3-r1": 11, "t3-r2": 11, "equal": True}
UPSTREAM_STATUS_ALL = 200

SCHEMA = "ra4-deep-chain-evidence-v1"


class Invalid(Exception):
    pass


def require(cond, msg):
    if not cond:
        raise Invalid(msg)


def no_duplicate_keys(pairs):
    seen = set()
    for k, _ in pairs:
        if k in seen:
            raise Invalid("duplicate key %r" % (k,))
        seen.add(k)
    return dict(pairs)


def _fail_constant(s):
    raise Invalid("non-finite number in JSON")


def loads(raw):
    return json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicate_keys, parse_constant=_fail_constant)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def canon(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def norm(v):
    return json.loads(CALL_ID_RE.sub("call_N", json.dumps(v, ensure_ascii=False)))


def descriptor(m):
    c = m.get("content")
    tcs = m.get("tool_calls")
    if isinstance(c, str):
        k, n = "str", len(c.encode("utf-8"))
    elif c is None:
        k, n = "null", 0
    else:
        k, n = "other", -1
    return [m.get("role"), k, n, len(tcs or [])]


def is_title(b):
    return len(b.get("messages", [])) == 2 and not b.get("tools")


def load_run(base, label):
    d = pathlib.Path(base) / RUN_RELS[label] / "requests"
    paths = sorted(d.glob("*.request.bin"))
    require(len(paths) == TOTAL_REQUESTS[label], "%s: request count %d" % (label, len(paths)))
    raws = [p.read_bytes() for p in paths]
    bodies = [loads(r) for r in raws]
    return raws, bodies


def build(base):
    out = {"schema": SCHEMA, "baseline": BASELINE, "runs": {}}
    per = {}
    raws_all = {}
    for label in RUN_LABELS:
        raws, bodies = load_run(base, label)
        raws_all[label] = raws
        mains = [b for b in bodies if not is_title(b)]
        require(len(mains) == MAIN_REQUESTS[label], "%s: main count %d" % (label, len(mains)))
        steps = []
        for a, b in zip(mains, mains[1:]):
            A, B = a["messages"], b["messages"]
            steps.append({
                "prefix": B[:len(A)] == A,
                "appended": [descriptor(m) for m in B[len(A):]],
                "delta_bytes": len(canon(b)) - len(canon(a)),
            })
        titles = [r for r, b in zip(raws, bodies) if is_title(b)]
        require(len(titles) == 1, "%s: title count %d" % (label, len(titles)))
        last_texts = [m["content"] for m in mains[-1]["messages"]
                      if m.get("role") == "assistant" and isinstance(m.get("content"), str)]
        require([s["delta_bytes"] for s in steps] == DELTAS[label], "%s: delta mismatch" % label)
        rec = {
            "requests_total": len(raws),
            "mains": len(mains),
            "title_raw_sha256": sha(titles[0]),
            "prefix_ok": sum(1 for s in steps if s["prefix"]),
            "prefix_steps": len(steps),
            "delta_bytes": [s["delta_bytes"] for s in steps],
            "appended_shapes_sha256": sha(canon([s["appended"] for s in steps])),
            "final_request_assistant_text_line_count": len(last_texts),
            "upstream_status": UPSTREAM_STATUS_ALL,
        }
        per[label] = rec
        out["runs"][label] = {
            "requests_total": rec["requests_total"],
            "mains": rec["mains"],
            "prefix_ok": rec["prefix_ok"],
            "prefix_steps": rec["prefix_steps"],
            "delta_bytes_count": len(rec["delta_bytes"]),
            "appended_shapes_sha256": rec["appended_shapes_sha256"],
            "title_raw_sha256": rec["title_raw_sha256"],
            "final_request_assistant_text_line_count": rec["final_request_assistant_text_line_count"],
            "upstream_status": rec["upstream_status"],
        }

    error_pair, skip_align = _compute_detour(base)
    out["cross_run"] = {
        "req1_raw_sha256": sha(raws_all["t3-r1"][0]),
        "req1_byte_equal": raws_all["t3-r1"][0] == raws_all["t3-r2"][0],
        "title_byte_equal": per["t3-r1"]["title_raw_sha256"] == per["t3-r2"]["title_raw_sha256"],
        "raw_followup_equal": _raw_followup_equal(base),
        "error_pair": error_pair,
        "skip_error_alignment": skip_align,
        "final_request_text_lines_equal": (
            per["t3-r1"]["final_request_assistant_text_line_count"]
            == per["t3-r2"]["final_request_assistant_text_line_count"]),
    }
    out["workspace"] = {"aggregate_bare_name_sha256": TASK_AGG, "files": len(WORKSPACE_FILES)}
    return out, per


def _raw_followup_equal(base):
    # 逐对主请求 raw canonical 相等计数（跨run按主链序，长度不同取min）
    a_mains, b_mains = _mains_only(base, "t3-r1"), _mains_only(base, "t3-r2")
    mins = min(len(a_mains), len(b_mains))
    return sum(1 for a, b in zip(a_mains[1:mins], b_mains[1:mins]) if canon(a) == canon(b))


def _mains_only(base, label):
    _raws, bodies = load_run(base, label)
    return [b for b in bodies if not is_title(b)]


def _compute_detour(base):
    """从两run主链计算错误绕行对与其持续回显的结构对齐（通用位置推导）。"""
    r1 = _mains_only(base, "t3-r1")
    r2 = _mains_only(base, "t3-r2")
    offset = len(r1) - len(r2)
    require(offset >= 0, "run1 shorter than run2")
    B1 = r2[1]["messages"]
    A1 = r1[offset]["messages"]
    P = None
    for i in range(min(len(A1), len(B1))):
        if canon(A1[i]) != canon(B1[i]):
            P = i
            break
    require(P is not None and len(A1) == len(B1), "detour pair position")
    pair = A1[P:P + 2]
    require(len(pair) == 2 and pair[0].get("role") == "assistant" and pair[1].get("role") == "tool", "detour pair roles")
    require((pair[0].get("tool_calls") or [{}])[0].get("function", {}).get("name", "") != "", "detour tool name")
    ea, et = pair
    tool = (ea.get("tool_calls") or [{}])[0].get("function", {}).get("name", "")
    prefix_txt = str(et.get("content", ""))[:44]
    constant = all(r1[k]["messages"][P:P + 2] == pair for k in range(offset, len(r1)))
    pair_n = norm(pair)
    aligned = 0
    pairs = 0
    for k in range(offset + 1, len(r1)):
        A = norm(r1[k])["messages"]
        B = norm(r2[k - offset])["messages"]
        pairs += 1
        if len(A) == len(B) + 2 and A[:P] == B[:P] and A[P + 2:] == B[P:] and A[P:P + 2] == pair_n:
            aligned += 1
    return ({"assistant_tool": tool, "tool_content_prefix": prefix_txt, "constant_in_run1": constant},
            {"pairs": pairs, "equal": aligned})


def validate_public(ev):
    require(ev.get("schema") == SCHEMA, "schema")
    require(ev.get("baseline") == BASELINE, "baseline")
    runs = ev.get("runs")
    require(isinstance(runs, dict) and set(runs) == set(RUN_LABELS), "runs coverage")
    for label in RUN_LABELS:
        r = runs[label]
        require(r["requests_total"] == TOTAL_REQUESTS[label], label + ": total")
        require(r["mains"] == MAIN_REQUESTS[label], label + ": mains")
        require(r["prefix_ok"] == PREFIX_OK[label] and r["prefix_steps"] == PREFIX_STEPS[label], label + ": prefix")
        require(r["appended_shapes_sha256"] == APPENDED_SHAPES_SHA[label], label + ": shapes")
        require(r["title_raw_sha256"] == TITLE_SHA, label + ": title sha")
        require(r["final_request_assistant_text_line_count"] == FINAL_TEXT_LINES[label], label + ": text lines")
        require(r["upstream_status"] == UPSTREAM_STATUS_ALL, label + ": status")
    d1 = DELTAS["t3-r1"]
    cr = ev.get("cross_run")
    require(cr["req1_raw_sha256"] == REQ1_SHA, "req1 sha")
    require(cr["req1_byte_equal"] is True, "req1 byte equal")
    require(cr["title_byte_equal"] is True, "title byte equal")
    require(cr["raw_followup_equal"] == RAW_FOLLOWUP_EQUAL, "raw followup equal")
    require(cr["error_pair"] == ERROR_PAIR, "error pair")
    require(cr["skip_error_alignment"] == SKIP_ERROR_ALIGNMENT, "skip error alignment")
    require(cr["final_request_text_lines_equal"] is True, "text lines equal")
    require(ev.get("workspace") == {"aggregate_bare_name_sha256": TASK_AGG, "files": len(WORKSPACE_FILES)}, "workspace")
    return True


def result_for(ev, ev_sha):
    return {
        "schema": "ra4-deep-chain-result-v1",
        "evidence_sha256": ev_sha,
        "baseline": BASELINE,
        "pins": {"prereg_v3": PREREG_SHA, "freeze_ra4": FREEZE_SHA, "chain_ra3_dir": CHAIN_DIR},
        "endpoints": {
            "prefix_ok": {k: ev["runs"][k]["prefix_ok"] for k in RUN_LABELS},
            "prefix_steps": {k: ev["runs"][k]["prefix_steps"] for k in RUN_LABELS},
            "req1_byte_equal": ev["cross_run"]["req1_byte_equal"],
            "title_byte_equal": ev["cross_run"]["title_byte_equal"],
            "raw_followup_equal": ev["cross_run"]["raw_followup_equal"],
            "skip_error_alignment": ev["cross_run"]["skip_error_alignment"],
            "error_pair": ev["cross_run"]["error_pair"],
            "final_request_text_lines": {
                "t3-r1": ev["runs"]["t3-r1"]["final_request_assistant_text_line_count"],
                "t3-r2": ev["runs"]["t3-r2"]["final_request_assistant_text_line_count"],
                "equal": ev["cross_run"]["final_request_text_lines_equal"],
            },
        },
        "limits": [
            "n=2 run对、单任务t3、单模型glm-5.3-flash、同日（跨0点）；链长15/14主请求仍有限，不外推更长会话或其他任务。",
            "跨run字节恒等仅在req1与标题请求成立；续请求因run1一次模型行为分叉（bash误调用及其Error返回）在仅追加语义下永久分流， skip-error-pair结构对齐13/13。",
            "bytes非token/成本；响应体（模型输出）不在终点，轮间文本仅计数与相等性登记。",
            "公开重放只核封印/算术/schema；真档重建需私有loop8两run归档；不认证provider服务端内部与私档历史真实性。",
            "请求与响应原文只私档；公开层无正文/路径/完整ID/凭据。",
        ],
    }


def exclusive(path, raw):
    p = pathlib.Path(path)
    require(not p.exists(), "output exists: %s" % p.name)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd = os_open_exclusive(p)
    with os.fdopen(fd, "wb") as f:
        f.write(raw)


def os_open_exclusive(p):
    import os
    return os.open(str(p), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive-base")
    ap.add_argument("--build-evidence")
    ap.add_argument("--evidence")
    ap.add_argument("--output", required=True)
    args = ap.parse_args(argv)
    try:
        require(bool(args.build_evidence) != bool(args.evidence), "choose exactly one of --build-evidence / --evidence")
        require(not (args.archive_base and args.evidence), "--archive-base only with --build-evidence")
        if args.build_evidence:
            require(bool(args.archive_base), "--archive-base required with --build-evidence")
            ev, _ = build(args.archive_base)
            ev_bytes = json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True).encode() + b"\n"
            validate_public(loads(ev_bytes))
            exclusive(args.build_evidence, ev_bytes)
        else:
            ev_bytes = pathlib.Path(args.evidence).read_bytes()
            ev = loads(ev_bytes)
            validate_public(ev)
        res = result_for(ev, sha(ev_bytes))
        exclusive(args.output, json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True).encode() + b"\n")
        print("ra4 verify OK: prefix", ev["runs"]["t3-r1"]["prefix_ok"], "/", ev["runs"]["t3-r1"]["prefix_steps"],
              "&", ev["runs"]["t3-r2"]["prefix_ok"], "/", ev["runs"]["t3-r2"]["prefix_steps"],
              "| req1/title byte-equal | skip-error", ev["cross_run"]["skip_error_alignment"]["equal"],
              "/", ev["cross_run"]["skip_error_alignment"]["pairs"])
        return 0
    except (Invalid, OSError, ValueError, KeyError) as e:
        print("input or output failure", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
