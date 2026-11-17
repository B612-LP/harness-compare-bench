#!/usr/bin/env python3
"""深链错误对请求侧驻留（t3 两 run，0 新运行）——公开验证器。

双模式（互斥，均 fail-closed，错误统一泛化为 input or output failure）：
  原档重建模式（作者/独审，需私档）:
    python3 verify.py --archive-root <loop8根> --build-evidence E.json --output R.json
    解析 t3-r1/t3-r2 全部请求档（与事件层 zstd，依赖系统 zstd CLI），
    逐请求定位错误对两要素（按 sha 锚定，不用启发式），重建 evidence 与
    已发布 evidence.json 逐字节一致后方写 --output。
  公开档重放模式（任何人）:
    python3 verify.py --evidence evidence.json --output result.json
    校验封印链、schema、逐行约束与四终点算术；不读私档。
公开 evidence 只含：位置、布尔、计数、sha256、分类标签；不含原始 id/参数文本/错误文本/任务正文/路径值。
边界：product-archived byte 观测；不认证模型内部/provider/HTTP 服务端；放置恒定性是追加式历史组装
（另见跨 run 重建环）的可推出特例，本包新增测量为全链持久性、跨 run 行为差异与事件层一致计数。
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = "dsh-deeppair-request-side-persistence-evidence-v1"
BASELINE = "63585d1b7f07596f0a6c6ab479cec7e6ff076bbb"
README_SHA256 = "363831393e28b6c22f88fc8f8de44b51f5a20d36ca443b9f08a4f6b54c254295"

def sha(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()

def die(msg):
    print("input or output failure", file=sys.stderr)
    sys.exit(2)

def require(cond, msg=""):
    if not cond:
        die(msg)

def no_duplicate_pairs(pairs):
    keys = set()
    for k, _ in pairs:
        if k in keys:
            die("dup")
        keys.add(k)

def loads(raw, label="json"):
    try:
        return json.loads(raw, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    except Exception:
        die(label)

def pinned(path, expected):
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        die("pin")
    require(sha(data) == expected)

# ---- frozen anchors（sha 锚定，不含原值）----
PAIR_ID_SHA256 = "c06bff59520c53208e88c16014c6da8115b3c49833ca1c68db1358687757b003"
PAIR_ARGS_SHA256 = "40e14c2a8a9fff1d0efadd542ace20571de78dcbad6f673b8afdeecaa0f9329e"
ERR_SHA256 = "1613fe63925b1b7e30fcd8547a706c195a1a18544b2cc601d8a8737bc166860f"
FROZEN_REQUEST_ROWS = 31
# 每请求 n_messages 冻结值（run, seq → n）：描述性字段也纳入公开重放校验（独审 L1）
FROZEN_N_MESSAGES = {
    "t3-r1": {1: 5, 2: 2, 3: 7, 4: 9, 5: 11, 6: 13, 7: 15, 8: 17, 9: 19, 10: 21, 11: 23, 12: 25, 13: 27, 14: 29, 15: 31, 16: 33},
    "t3-r2": {1: 5, 2: 2, 3: 7, 4: 9, 5: 11, 6: 13, 7: 15, 8: 17, 9: 19, 10: 21, 11: 23, 12: 25, 13: 27, 14: 29, 15: 31},
}
RUNS = {
    "t3-r1": {"requests": 16, "title_seq": 2, "first_pair_seq": 3},
    "t3-r2": {"requests": 15, "title_seq": 2, "first_pair_seq": None},
}
# 期望放置（由冻结口径推出，重建时逐请求核对）
EXPECT_R1 = {seq: (5, 6) for seq in range(3, 17)}

def parse_request(path):
    obj = loads(path.read_bytes() if hasattr(path, "read_bytes") else open(path, "rb").read(), "req")
    msgs = obj.get("messages")
    require(isinstance(msgs, list))
    assistant, tool_err = [], []
    for i, m in enumerate(msgs):
        require(isinstance(m, dict))
        role = m.get("role")
        if role == "assistant":
            for tc in m.get("tool_calls") or []:
                fn = tc.get("function") or {}
                if sha((tc.get("id") or "").encode()) == PAIR_ID_SHA256 and sha(
                    (fn.get("arguments") or "").encode()
                ) == PAIR_ARGS_SHA256:
                    assistant.append(i)
        elif role == "tool":
            c = m.get("content")
            if isinstance(c, str) and sha(c.encode()) == ERR_SHA256:
                tool_err.append(i)
    return len(msgs), assistant, tool_err

def decode_event_layer(path):
    """zstd CLI 多帧解包；build 模式专用（公开重放不读私档）。"""
    try:
        proc = subprocess.run(["zstd", "-dc", str(path)], capture_output=True)
    except OSError:
        die("zstd")
    require(proc.returncode == 0 and proc.stdout, "zstd")
    rows = []
    for line in proc.stdout.decode("utf-8").splitlines():
        rows.append(loads(line.encode(), "event"))
    return rows

def event_layer_facts(rows):
    call_args_sha, call_id_sha, err_out_sha, bad_calls, err_results = None, None, None, 0, 0
    for e in rows:
        if e.get("type") == "tool/call":
            d = e.get("data") or {}
            a = d.get("arguments")
            s = a if isinstance(a, str) else json.dumps(a, ensure_ascii=False, separators=(",", ":")) if a is not None else ""
            if sha(s.encode()) == PAIR_ARGS_SHA256:
                bad_calls += 1
                if call_args_sha is None:
                    call_args_sha = sha(s.encode())
                    call_id_sha = sha((d.get("callId") or "").encode())
        elif e.get("type") == "tool/result":
            d = e.get("data") or {}
            o = d.get("output")
            if not isinstance(o, str):
                msg = d.get("message") or {}
                blocks = msg.get("content") or []
                texts = [b.get("text") for b in blocks if isinstance(b, dict) and isinstance(b.get("text"), str)]
                o = "".join(texts) if texts else None
            if isinstance(o, str) and sha(o.encode()) == ERR_SHA256:
                err_results += 1
                if err_out_sha is None:
                    err_out_sha = sha(o.encode())
    return {
        "call_args_sha256": call_args_sha,
        "call_id_sha256": call_id_sha,
        "error_output_sha256": err_out_sha,
        "bad_call_count": bad_calls,
        "error_result_count": err_results,
    }

def build(archive_root):
    root = os.path.abspath(archive_root)
    rows = []
    layer_facts = {}
    for run, spec in RUNS.items():
        rdir = os.path.join(root, run, "requests")
        reqs = sorted(os.listdir(rdir)) if os.path.isdir(rdir) else None
        require(reqs, "run")
        reqs = [n for n in reqs if n.endswith(".request.bin")]
        require(len(reqs) == spec["requests"], "count")
        for name in reqs:
            seq = int(name[:3])
            n, bad, terr = parse_request(os.path.join(rdir, name))
            row = {
                "run": run,
                "seq": seq,
                "kind": "title" if seq == spec["title_seq"] else "main",
                "n_messages": n,
                "pair_assistant_positions": bad,
                "pair_tool_error_positions": terr,
            }
            rows.append(row)
        ev_rel = os.path.join(root, "event-layer-" + run, "session.v4.jsonl.zstd")
        require(os.path.isfile(ev_rel), "ev")
        layer_facts[run] = event_layer_facts(decode_event_layer(ev_rel))
    rows.sort(key=lambda r: (r["run"], r["seq"]))
    evidence = {
        "schema": SCHEMA,
        "baseline_commit": BASELINE,
        "readme_sha256": README_SHA256,
        "anchors": {
            "pair_call_id_sha256": PAIR_ID_SHA256,
            "pair_arguments_sha256": PAIR_ARGS_SHA256,
            "error_text_sha256": ERR_SHA256,
        },
        "runs": RUNS,
        "requests": rows,
        "event_layers": layer_facts,
    }
    return evidence

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)

# ---- 公开档校验 ----
ROW_KEYS = {
    "run",
    "seq",
    "kind",
    "n_messages",
    "pair_assistant_positions",
    "pair_tool_error_positions",
}

def validate_public(ev):
    require(isinstance(ev, dict) and ev.get("schema") == SCHEMA, "schema")
    require(ev.get("baseline_commit") == BASELINE, "baseline")
    require(ev.get("readme_sha256") == README_SHA256, "readme-pin")
    anc = ev.get("anchors") or {}
    require(
        anc.get("pair_call_id_sha256") == PAIR_ID_SHA256
        and anc.get("pair_arguments_sha256") == PAIR_ARGS_SHA256
        and anc.get("error_text_sha256") == ERR_SHA256,
        "anchors",
    )
    runs = ev.get("runs") or {}
    require(runs == RUNS, "runs")
    rows = ev.get("requests") or []
    require(isinstance(rows, list) and len(rows) == RUNS["t3-r1"]["requests"] + RUNS["t3-r2"]["requests"], "rows")
    seen = set()
    by_run = {}
    for r in rows:
        require(isinstance(r, dict) and set(r.keys()) == ROW_KEYS, "row-keys")
        run = r["run"]
        require(run in RUNS, "run")
        seq = r["seq"]
        require(isinstance(seq, int) and not isinstance(seq, bool) and 1 <= seq <= RUNS[run]["requests"], "seq")
        require((run, seq) not in seen, "dup-row")
        seen.add((run, seq))
        require(r["kind"] == ("title" if seq == RUNS[run]["title_seq"] else "main"), "kind")
        require(r["n_messages"] == FROZEN_N_MESSAGES[run][seq], "n-pin")
        for key in ("pair_assistant_positions", "pair_tool_error_positions"):
            v = r[key]
            require(isinstance(v, list) and all(isinstance(x, int) and not isinstance(x, bool) for x in v), "pos")
        for x in r["pair_assistant_positions"] + r["pair_tool_error_positions"]:
            require(0 <= x < r["n_messages"], "pos-range")
        by_run.setdefault(run, []).append(r)
    # 逐行期望（由冻结口径与重建核对）
    for r in by_run["t3-r1"]:
        if 3 <= r["seq"] <= 16:
            require(r["pair_assistant_positions"] == [5], "r1-a")
            require(r["pair_tool_error_positions"] == [6], "r1-t")
        else:
            require(r["pair_assistant_positions"] == [] and r["pair_tool_error_positions"] == [], "r1-empty")
    for r in by_run["t3-r2"]:
        require(r["pair_assistant_positions"] == [] and r["pair_tool_error_positions"] == [], "r2-empty")
    layers = ev.get("event_layers") or {}
    require(set(layers.keys()) == {"t3-r1", "t3-r2"}, "layers")
    l1 = layers["t3-r1"]
    require(
        l1.get("call_args_sha256") == PAIR_ARGS_SHA256
        and l1.get("call_id_sha256") == PAIR_ID_SHA256
        and l1.get("error_output_sha256") == ERR_SHA256
        and l1.get("bad_call_count") == 1
        and l1.get("error_result_count") == 1,
        "layer-r1",
    )
    l2 = layers["t3-r2"]
    require(
        l2.get("call_args_sha256") is None
        and l2.get("call_id_sha256") is None
        and l2.get("error_output_sha256") is None
        and l2.get("bad_call_count") == 0
        and l2.get("error_result_count") == 0,
        "layer-r2",
    )

def endpoints(ev):
    rows = ev["requests"]
    r1 = [r for r in rows if r["run"] == "t3-r1"]
    r2 = [r for r in rows if r["run"] == "t3-r2"]
    follow = [r for r in r1 if 3 <= r["seq"] <= 16]
    d1 = {
        "r1_first_pair_seq": min(r["seq"] for r in follow),
        "r1_present_all_followups": all(r["pair_assistant_positions"] and r["pair_tool_error_positions"] for r in follow),
        "r1_positions_constant": all(r["pair_assistant_positions"] == [5] and r["pair_tool_error_positions"] == [6] for r in follow),
        "r2_pair_absent_all": not any(r["pair_assistant_positions"] or r["pair_tool_error_positions"] for r in r2),
    }
    occ_a = sum(len(r["pair_assistant_positions"]) for r in follow)
    occ_t = sum(len(r["pair_tool_error_positions"]) for r in follow)
    d2 = {
        "r1_assistant_occurrences": occ_a,
        "r1_error_occurrences": occ_t,
        "r1_elements_byte_stable": occ_a == 14 and occ_t == 14,
    }
    d3 = {"classification": "PRESENT_IN_ONE_RUN" if d1["r2_pair_absent_all"] and d1["r1_present_all_followups"] else "OTHER"}
    layers = ev["event_layers"]
    d4 = {
        "r1_event_layer_matches_request_side": layers["t3-r1"]["bad_call_count"] == 1
        and layers["t3-r1"]["error_result_count"] == 1
        and layers["t3-r1"]["call_args_sha256"] == PAIR_ARGS_SHA256,
        "r2_event_layer_has_no_pair": layers["t3-r2"]["bad_call_count"] == 0
        and layers["t3-r2"]["error_result_count"] == 0,
    }
    return {"D1_placement": d1, "D2_byte_identity": d2, "D3_cross_run": d3, "D4_event_layer": d4}

def result_for(ev, evidence_sha):
    ep = endpoints(ev)
    ok = (
        ep["D1_placement"]["r1_first_pair_seq"] == 3
        and ep["D1_placement"]["r1_present_all_followups"]
        and ep["D1_placement"]["r1_positions_constant"]
        and ep["D1_placement"]["r2_pair_absent_all"]
        and ep["D2_byte_identity"]["r1_elements_byte_stable"]
        and ep["D3_cross_run"]["classification"] == "PRESENT_IN_ONE_RUN"
        and ep["D4_event_layer"]["r1_event_layer_matches_request_side"]
        and ep["D4_event_layer"]["r2_event_layer_has_no_pair"]
    )
    return {
        "schema": SCHEMA + "-result",
        "evidence_sha256": evidence_sha,
        "baseline_commit": BASELINE,
        "endpoints": ep,
        "verdict": "wire_pair_persistent_r1_only_byte_stable" if ok else "UNEXPECTED",
        "boundaries": [
            "product-archived byte observation; no model-internal/provider/HTTP-server claims",
            "placement constancy is implied by append-only history assembly; new measurements are full-chain persistence, cross-run behavioral difference, and event-layer consistency counts",
            "single task (t3), two runs, one model channel; no extrapolation",
        ],
    }

def exclusive(path, raw):
    require(not os.path.exists(path), "exists")
    parent = os.path.dirname(os.path.abspath(path))
    require(os.path.isdir(parent), "parent")
    try:
        with open(path, "xb") as fh:
            fh.write(raw)
    except OSError:
        die("write")

def dump(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=1, allow_nan=False) + "\n").encode("utf-8")
    exclusive(path, raw)

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive-root")
    ap.add_argument("--evidence")
    ap.add_argument("--build-evidence")
    ap.add_argument("--output", required=True)
    args = ap.parse_args(argv)
    if bool(args.archive_root) == bool(args.evidence):
        die("flags")
    if args.archive_root:
        ev = build(args.archive_root)
        if args.build_evidence:
            published_path = os.path.join(HERE, "evidence.json")
            is_frozen_shape = len(ev["requests"]) == FROZEN_REQUEST_ROWS
            if os.path.exists(published_path) and is_frozen_shape:
                published = loads(open(published_path, "rb").read(), "published")
                require(canonical(ev) == canonical(published), "rebuild-mismatch")
            dump(args.build_evidence, ev)
        evidence_sha = sha((json.dumps(ev, ensure_ascii=False, indent=1, allow_nan=False) + "\n").encode("utf-8"))
        res = result_for(ev, evidence_sha)
    else:
        try:
            with open(args.evidence, "rb") as fh:
                raw = fh.read()
        except OSError:
            die("evidence")
        pinned(os.path.join(HERE, "README.md"), README_SHA256)
        ev = loads(raw, "evidence")
        validate_public(ev)
        if args.build_evidence:
            die("flags")
        evidence_sha = sha(raw)
        res = result_for(ev, evidence_sha)
    dump(args.output, res)
    print("endpoints", json.dumps(res["endpoints"], ensure_ascii=False)[:220])
    print("verdict", res["verdict"])
    return 0

if __name__ == "__main__":
    sys.exit(main())
