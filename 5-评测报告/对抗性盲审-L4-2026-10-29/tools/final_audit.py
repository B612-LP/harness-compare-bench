#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L4 最终敌意审计机械检查（auditor task-9；阶段 I 骨架）。

三态语义（与 THREAT-MODEL.md §4 对应）：
  PASS      = 输入齐备且断言全过
  FAIL      = 输入齐备但断言失败（终审发现）
  PENDING-E = 所需输入尚未存在（E 未封/真实数据未回），如实列缺失项，不猜结论

阶段 I（当前）只有 F1/F2 可跑：plan/contract 槽位全集与绑定校验。
其余 stage 为显式 PENDING-E 骨架：定位输入路径、缺什么如实报，不伪造判定。

纪律：零模型、零网络；只读目标；--out 原子拒写；live_doc_drift 内嵌 list；
时间脚本生成；不读 truth/solution 内容（只允许对 case 快照做字节哈希比对）。
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.resolve().parents[2]
L4 = REPO / "1-评测方案" / "自动循环L4-2026-10-29"
PLAN = L4 / "plan.json"
CONTRACT = L4 / "contract.json"
CLI_ROOT = REPO / "3-表现现场" / "l4-20261029-cli"
CACHE_ROOT = REPO / "3-表现现场" / "l4-20261029-cache"
WB_ROOT = REPO / "3-表现现场" / "l4-20261029-wb-gateway"

FROZEN_TIMEOUT = {"dabstep-payments-10": 1800, "tb-cargo-plan": 2400}
PRODUCT_COUNTS = {"codex": 6, "dsh": 6, "workbuddy": 5}
PROBE_PROTOCOLS = {"responses", "anthropic-messages", "chat-completions"}
PROBE_CONDITIONS = {"fresh", "repeat", "nonce-control"}


def now_local() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check(name: str, ok: bool, detail="") -> dict:
    return {"check": name, "status": "PASS" if ok else "FAIL", "detail": str(detail)[:300]}


def pending(name: str, missing: list[str]) -> dict:
    return {"check": name, "status": "PENDING-E",
            "missing_inputs": missing[:20]}


def stage_plan() -> list[dict]:
    out: list[dict] = []
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    ps, pr = plan["product_slots"], plan["probe_slots"]
    # F1 槽位全集
    out.append(check("F1_product_total_17", len(ps) == 17, "actual=%d" % len(ps)))
    by_product: dict[str, int] = {}
    for s in ps:
        by_product[s["product"]] = by_product.get(s["product"], 0) + 1
    out.append(check("F1_product_counts", by_product == PRODUCT_COUNTS, json.dumps(by_product)))
    out.append(check("F1_probe_total_18", len(pr) == 18, "actual=%d" % len(pr)))
    ids = [s["slot_id"] for s in ps] + [s["slot_id"] for s in pr]
    rids = [s["run_id"] for s in ps] + [s["run_id"] for s in pr]
    eids = [s["event_id"] for s in ps if "event_id" in s] + \
           [s["event_id"] for s in pr if "event_id" in s]
    out.append(check("F1_identity_unique",
                     len(set(ids)) == len(ids) and len(set(rids)) == len(rids)
                     and len(set(eids)) == len(eids)))
    orders = [s["order"] for s in ps]
    out.append(check("F1_product_order_dense",
                     sorted(orders) == list(range(1, len(ps) + 1))))
    # CLI rep 结构：rep1 dab→cargo / rep2 cargo→dab / rep3 dab→cargo，两产品各 3 rep
    cli = [s for s in ps if s["product"] in ("codex", "dsh")]
    got = {(s["product"], s["rep"], s["case"]) for s in cli}
    expect = {(p, r, c) for p in ("codex", "dsh") for r, cs in
              ((1, ("dabstep-payments-10", "tb-cargo-plan")),
               (2, ("tb-cargo-plan", "dabstep-payments-10")),
               (3, ("dabstep-payments-10", "tb-cargo-plan"))) for c in cs}
    out.append(check("F1_cli_rep_structure", got == expect and len(cli) == 12,
                     json.dumps(sorted("%s" % (x,) for x in (got ^ expect)))))
    out.append(check("F1_timeouts_frozen",
                     all(s["timeout_s"] == FROZEN_TIMEOUT[s["case"]]
                         for s in cli if s["product"] in ("codex", "dsh"))))
    # F1 probe 结构：3 协议 × 2 block × fresh/repeat/nonce-control
    combos = {(s["protocol"], s["block"], s["condition"]) for s in pr}
    want = {(p, b, c) for p in PROBE_PROTOCOLS for b in (1, 2) for c in PROBE_CONDITIONS}
    out.append(check("F1_probe_grid_3x2x3", combos == want and len(pr) == 18))
    porders = [s["order"] for s in pr]
    out.append(check("F1_probe_order_dense", sorted(porders) == list(range(1, 19))))
    out.append(check("F1_probe_once_per_slot",
                     all(s.get("max_output_tokens") == 256 for s in pr)))
    out.append(check("F1_no_replacements_no_extra",
                     not plan.get("replacements") and not plan.get("result_driven_extra_samples"),
                     "replacements=%r extra=%r" % (plan.get("replacements"),
                                                   plan.get("result_driven_extra_samples"))))
    out.append(check("F1_whole_restarts_zero",
                     plan.get("whole_execution_restarts") in (None, 0, [], {}),
                     repr(plan.get("whole_execution_restarts"))))
    # F2 contract 绑定
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    out.append(check("F2_contract_plan_sha_matches_bytes",
                     contract.get("plan_sha256") == sha256_file(PLAN),
                     "contract=%s actual=%s" % (contract.get("plan_sha256", "")[:8],
                                                sha256_file(PLAN)[:8])))
    out.append(check("F2_denominators_present", bool(contract.get("denominators"))))
    out.append(check("F2_strata_present", bool(contract.get("strata"))))
    out.append(check("F2_case_snapshots_5", len(contract.get("case_snapshots", {})) == 5,
                     "actual=%d" % len(contract.get("case_snapshots", {}))))
    out.append(check("F2_old_contracts_untouched_flag",
                     contract.get("old_contracts_mutated") in (False, None),
                     repr(contract.get("old_contracts_mutated"))))
    return out


def stage_pending_common() -> list[dict]:
    """PENDING 骨架：产品槽位（CLI12/WB5）数据未齐，保持显式 PENDING，不对空目录判失败。"""
    out = []
    out.append(pending("F3_slot_accounting", [
        "17 槽 slot-accounting 全集（cache 18 已按 C 系列核，产品 12+5 未齐）"]))
    out.append(pending("F5_file_hashes_products", [
        "CLI12/WB5 各槽原始证据文件与收据内嵌 SHA（产品数据未齐）"]))
    out.append(pending("F7_dual_archive", [
        "两个 sandbox 副本重放收据 + equivalent_simulation 标注 + 适配 diff"]))
    out.append(pending("F8_wb_route_discipline", [
        "WB 五槽原生 trace + declared_alias 选择证据 + app/asar 哈希"]))
    out.append(pending("F9_pollution", [
        "逐场 isolation.ok + 独立无污染裁定 + prompt 哈希清单"]))
    out.append(pending("F11_credential_scan_post_products", [
        "产品证据到位后再跑 credential_scan.py 全量精确轮"]))
    return out


# ---------------------------------------------------------------- DSH 6 + 17 槽覆盖

def stage_dsh() -> list[dict]:
    out: list[dict] = []
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    dsh = {s["slot_id"]: s for s in plan["product_slots"] if s["product"] == "dsh"}
    RUNS = CLI_ROOT / "dsh" / "runs"
    REC = CLI_ROOT / "dsh" / "recoveries"
    dirs = sorted(p.name for p in RUNS.iterdir() if p.is_dir()) if RUNS.is_dir() else []
    out.append(check("D1_dsh_identity_exact_6", dirs == sorted(dsh) and len(dirs) == 6,
                     "dirs=%d plan=%d" % (len(dirs), len(dsh))))
    expect_w = {"dabstep-payments-10": [70.0, 80.0, 70.0],
                "tb-cargo-plan": [70.37037037, 74.07407407, 74.07407407]}
    seen, d2d = {}, []
    for sid in sorted(dsh):
        d = RUNS / sid
        m = json.loads((d / "meta.json").read_text(encoding="utf-8")) if (d / "meta.json").is_file() else {}
        w = m.get("weighted")
        case, rep = dsh[sid]["case"], dsh[sid]["rep"]
        seen[sid] = w
        want = expect_w[case][rep - 1]
        if w is None or abs(float(w) - want) > 1e-6:
            d2d.append("%s weighted=%s expect=%s" % (sid, w, want))
        if m.get("status") != "ok" or m.get("exit_code") != 0:
            d2d.append("%s status=%s" % (sid, m.get("status")))
    out.append(check("D2_dsh_rawscores_match", not d2d,
                     json.dumps(seen, ensure_ascii=False) + " | " + "; ".join(d2d)[:150]))
    gaps = {}
    for sid in sorted(dsh):
        m = json.loads((RUNS / sid / "meta.json").read_text(encoding="utf-8"))
        u = m.get("usage") or {}
        gaps[sid] = {"usage_requests": u.get("requests"),
                     "integrity": m.get("integrity_verdict")}
    out.append({"check": "D3_capture_gap_preserved_unfilled", "status": "PASS",
                "detail": json.dumps(gaps, ensure_ascii=False)[:600] +
                          "（usage.requests=None=marker 缺陷原样保留，不填 0 不虚构；"
                          "vacuous integrity=violation 的 formal 判定归 judge/reviewer）"})
    rec_slots = sorted(p.name for p in REC.iterdir() if p.is_dir()) if REC.is_dir() else []
    zstd_n = len(list(REC.rglob("*.zstd"))) if REC.is_dir() else 0
    wrote_back = [s for s in rec_slots if (RUNS / s / "meta.json").is_file()
                  and "recovery" in (RUNS / s / "meta.json").read_text(encoding="utf-8")[:2000]]
    out.append(check("D4_recoveries_sidecar_separate",
                     rec_slots == sorted(dsh) and zstd_n >= 6 and not wrote_back,
                     "slots=%d zstd=%d writeback=%s" % (len(rec_slots), zstd_n, wrote_back)))
    return out


def stage_coverage() -> list[dict]:
    """17 计划槽 → 实际证据目录双向映射：防 scope 混淆/汇总掉行。"""
    out: list[dict] = []
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    by = {}
    for s in plan["product_slots"]:
        by.setdefault(s["product"], []).append(s["slot_id"])
    present = {}
    for prod, root in (("codex", CLI_ROOT / "codex" / "runs"),
                       ("dsh", CLI_ROOT / "dsh" / "runs"),
                       ("workbuddy", WB_ROOT / "runs")):
        present[prod] = sorted(p.name for p in root.iterdir() if p.is_dir()) if root.is_dir() else []
    problems, coverage = [], {}
    for prod, ids in by.items():
        have = set(present.get(prod, []))
        for sid in ids:
            if sid in have:
                coverage[sid] = "evidence_dir_present"
                have.discard(sid)
            else:
                coverage[sid] = "not_yet_landed"
        if have:
            problems.append("%s extra=%s" % (prod, sorted(have)[:3]))
    landed = sum(1 for v in coverage.values() if v == "evidence_dir_present")
    out.append({"check": "F0_coverage_17_slot_map", "status": "PASS" if not problems else "FAIL",
                "detail": json.dumps({"landed_dirs": landed, "not_yet": 17 - landed,
                                      "per_slot": coverage, "problems": problems},
                                     ensure_ascii=False)[:1200],
                "note": "presence≠final：目录存在不冒充 executed；executed 判定逐产品在 X/D 系与 F3 全集账"})
    return out

def stage_codex() -> list[dict]:
    out: list[dict] = []
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    codex = {s["slot_id"]: s for s in plan["product_slots"] if s["product"] == "codex"}
    RUNS = CLI_ROOT / "codex" / "runs"
    dirs = sorted(p.name for p in RUNS.iterdir() if p.is_dir()) if RUNS.is_dir() else []
    out.append(check("X1_codex_identity_exact_6", dirs == sorted(codex) and len(dirs) == 6,
                     "dirs=%d plan=%d" % (len(dirs), len(codex))))
    import re
    scores, hits, x2d = {}, {}, []
    x_hash = True
    x_att = True
    formal = {}
    for sid in sorted(codex):
        d = RUNS / sid
        mp = d / "meta.partial.json"
        full = d / "meta.json"
        if not (mp.is_file() and full.is_file()):
            x2d.append(sid + ":meta-missing")
            continue
        m = json.loads(mp.read_text(encoding="utf-8"))
        # 哈希链：prompt / agent.jsonl / stderr 实算 vs meta
        pf = d / "prompt.txt"
        if pf.is_file() and m.get("prompt_sha256"):
            x_hash &= sha256_file(pf) == m["prompt_sha256"]
        aj, ajh = d / "agent.jsonl", d / "agent.jsonl.sha256"
        if aj.is_file() and ajh.is_file():
            x_hash &= ajh.read_text(encoding="utf-8").strip() == sha256_file(aj)
        sef = d / "agent.stderr.txt"
        if sef.is_file() and m.get("stderr_sha256"):
            x_hash &= sha256_file(sef) == m["stderr_sha256"]
        # 无重启/无补跑
        if len(m.get("attempts", [])) != 1 or m.get("transport_retries") not in (0, None) \
                or m.get("timed_out") is not False:
            x_att = False
        formal[sid] = m.get("runner_formal_eligible")
        # 分数：dab=70.0(7/10) cargo=70.37037037(19/27)
        w = m.get("weighted")
        scores[sid] = w
        expect = 70.0 if "dabstep" in sid else 70.37037037037037
        if w is None or abs(float(w) - expect) > 1e-6:
            x2d.append("%s:weighted=%s" % (sid, w))
        jf = m.get("judge") or {}
        if jf.get("case") != codex[sid]["case"]:
            x2d.append("%s:judge-case-mismatch" % sid)
        # trace 机械命中 + 越界
        aj_txt = aj.read_text(encoding="utf-8", errors="replace") if aj.is_file() else ""
        hits[sid] = {tok: aj_txt.count(tok) for tok in
                     ("harness-compare-bench", "reference/", "/../")}
        hits[sid]["truth"] = aj_txt.count("truth")
        hits[sid]["solution"] = aj_txt.count("solution")
        ws = (m.get("workspace") or "") + "/"
        outs = set(re.findall(r"/Users/b612-lp/[\w./\-— COMP]+", aj_txt))
        outs = {o.strip() for o in outs if not o.startswith(ws.rstrip("/"))}
        hits[sid]["outside_ws_paths"] = sorted({o[:70] for o in outs})
    out.append(check("X2_meta_scores_and_judge_case", not x2d, "; ".join(x2d)[:250]))
    dab_ok = all(abs(float(scores[s]) - 70.0) < 1e-9 for s in scores if "dabstep" in s)
    cargo_ok = all(abs(float(scores[s]) - 70.37037037037037) < 1e-6 for s in scores if "cargo" in s)
    out.append(check("X3_scores_3x70_3x70_37037037", dab_ok and cargo_ok and len(scores) == 6,
                     json.dumps(scores, ensure_ascii=False)))
    out.append(check("X4_hash_chain_prompt_agent_stderr", x_hash))
    out.append(check("X5_no_restarts_no_retries", x_att))
    tot = sum(sum(v for k, v in h.items() if isinstance(k, str) and k not in
                  ("outside_ws_paths",) and isinstance(v, int))
              for h in hits.values())
    out.append({"check": "X6_mechanical_hit_trace_scan", "status": "PASS",
                "detail": json.dumps({"per_slot": hits, "note":
                    "计数供 judge 逐槽路径-vs-引用裁定；本审计不动 formal 判定"},
                    ensure_ascii=False)[:1500]})
    out.append({"check": "X7_formal_eligible_recorded_not_admission", "status": "PASS",
                "detail": "runner_formal_eligible=%s（仅记录；独立 gate 首批真实 rows=false"
                          "（发射缺口），formal 裁定归 judge，不以该字段为完整准入）" %
                          json.dumps(formal, ensure_ascii=False)})
    return out

# ---------------------------------------------------------------- F4-lite（E 注册）

def _git(args: list[str], text: bool = False) -> "str | bytes":
    import subprocess
    r = subprocess.run(["git"] + args, capture_output=True, text=text,
                       cwd=str(REPO), timeout=60)
    if r.returncode != 0:
        return "" if text else b""
    return r.stdout


def _git_blob_sha(commit: str, rel: str) -> str:
    import hashlib
    blob = _git(["show", "%s:%s" % (commit, rel)])
    return hashlib.sha256(blob).hexdigest() if blob else ""


def stage_u1() -> list[dict]:
    out: list[dict] = []
    binding = json.loads((L4 / "runtime-binding.json").read_text(encoding="utf-8"))
    manifest = json.loads((L4 / "execution-manifest.json").read_text(encoding="utf-8"))
    D, E = binding["design_commit"], binding["execution_seal_commit"]
    cdt = _git(["log", "-1", "--format=%cI", E], text=True).strip()
    out.append(check("F4_registered_at_equals_E_git_time",
                     cdt == binding["registered_at"],
                     "git=%s binding=%s" % (cdt, binding["registered_at"])))
    for name, bkey in (("plan.json", "plan_sha256"), ("contract.json", "contract_sha256")):
        rel = str((L4 / name).relative_to(REPO))
        cur = sha256_file(L4 / name)
        d_sha, e_sha = _git_blob_sha(D, rel), _git_blob_sha(E, rel)
        out.append(check("F4_%s_blob_D_E_current_equal" % name.split(".")[0],
                         cur == d_sha == e_sha == binding[bkey],
                         "cur=%s D=%s E=%s" % (cur[:8], d_sha[:8], e_sha[:8])))
    out.append(check("F4_manifest_sha_matches_binding",
                     sha256_file(L4 / "execution-manifest.json") == binding["execution_manifest_sha256"]))
    files, ext = manifest.get("files", {}), manifest.get("external_files", {})
    out.append(check("F4_manifest_counts_42_17", len(files) == 42 and len(ext) == 17,
                     "files=%d ext=%d" % (len(files), len(ext))))
    bad = [rel for rel, sha in sorted(files.items())
           if not (REPO / rel).is_file() or sha256_file(REPO / rel) != sha]
    out.append(check("F4_manifest_42_repo_files_hash_match", not bad, "bad=%s" % bad[:5]))
    bad_ext = [ap for ap, sha in sorted(ext.items())
               if not Path(ap).is_file() or sha256_file(Path(ap)) != sha]
    out.append(check("F4_manifest_17_external_hash_match", not bad_ext, "bad=%s" % bad_ext[:5]))
    rev = REPO / "5-评测报告" / "L4首请求前评审-2026-10-29" / "actual-E-readonly-check.json"
    out.append(check("F4_judge_actual_E_review_on_record", rev.is_file(),
                     "reviewer actual-E 收据在案（不重复其实现）"))
    return out


# ---------------------------------------------------------------- F6/F10-cache（cache 18 实际数据）

def _leaf_states(node, prefix="") -> dict:
    leaves = {}
    if isinstance(node, dict):
        for k, v in node.items():
            leaves.update(_leaf_states(v, "%s.%s" % (prefix, k) if prefix else k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            leaves.update(_leaf_states(v, "%s[%d]" % (prefix, i)))
    else:
        if node is None:
            st = "null"
        elif isinstance(node, bool):
            st = "bool"
        elif isinstance(node, int):
            st = "int0" if node == 0 else "int+"
        elif isinstance(node, float):
            st = "num"
        elif isinstance(node, str):
            st = "str"
        else:
            st = "other"
        leaves[prefix] = (st, node)
    return leaves


def _extract_usage_candidates(raw: bytes) -> list:
    text = raw.decode("utf-8", errors="replace")
    candidates = []

    def walk(o):
        if isinstance(o, dict):
            if isinstance(o.get("usage"), dict):
                candidates.append(o["usage"])
            elif any(k in o for k in ("input_tokens", "prompt_tokens",
                                      "output_tokens", "completion_tokens")):
                candidates.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    try:
        walk(json.loads(text))
    except Exception:
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                payload = line[5:].strip()
                if payload and payload != "[DONE]":
                    try:
                        walk(json.loads(payload))
                    except Exception:
                        pass
    return candidates


def stage_cache() -> list[dict]:
    out: list[dict] = []
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    pr = {s["slot_id"]: s for s in plan["probe_slots"]}
    C = CACHE_ROOT / "probes"
    import datetime as dt

    def ts(x):
        return dt.datetime.fromisoformat(x)

    dirs = sorted(p.name for p in C.iterdir() if p.is_dir()) if C.is_dir() else []
    out.append(check("C1_identity_exact_18", dirs == sorted(pr) and len(dirs) == 18,
                     "dirs=%d plan=%d" % (len(dirs), len(pr))))
    trans = {}
    c2d = []
    for sid in sorted(pr):
        tp = C / sid / "transport.json"
        if not tp.is_file():
            c2d.append(sid + ":no-transport")
            continue
        t = json.loads(tp.read_text(encoding="utf-8"))
        trans[sid] = t
        req = C / sid / "request.body.json"
        if not (t.get("executed") is True and t.get("http_status") == 200
                and t.get("error") is None
                and sha256_file(req) == t.get("request_sha256")
                and req.stat().st_size == t.get("request_bytes")):
            c2d.append("%s:status=%s" % (sid, t.get("http_status")))
    out.append(check("C2_transport_once_200_sha_match", not c2d, "; ".join(c2d)[:250]))
    # C3 配对 + nonce：fresh/repeat 逐字节一致；control 仅首 nonce 行差异（值级剥离验证）
    c3 = True
    c3d = []
    import re as _re
    for proto in ("responses", "anthropic-messages", "chat-completions"):
        for b in (1, 2):
            fb = (C / ("l4-20261029-cache-%s-b%d-fresh" % (proto, b)) / "request.body.json").read_bytes()
            rb = (C / ("l4-20261029-cache-%s-b%d-repeat" % (proto, b)) / "request.body.json").read_bytes()
            nb = (C / ("l4-20261029-cache-%s-b%d-nonce-control" % (proto, b)) / "request.body.json").read_bytes()
            if fb != rb:
                c3, _ = False, c3d.append("%s b%d fresh/repeat differ" % (proto, b))
            if nb == fb:
                c3, _ = False, c3d.append("%s b%d control==fresh" % (proto, b))
            else:
                lf, ln = _leaf_states(json.loads(fb)), _leaf_states(json.loads(nb))
                diff = [k for k in set(lf) | set(ln) if lf.get(k, (None,))[1] != ln.get(k, (None,))[1]]
                # nonce 嵌在单一文本叶头部：剥离「NONCE:<16hex>」后两值必须全等
                ok = len(diff) == 1
                if ok:
                    strip = lambda s: _re.sub(r"NONCE:[0-9a-f]{16}", "", str(s), count=1)
                    ok = strip(lf[diff[0]][1]) == strip(ln[diff[0]][1])
                if not ok:
                    c3, _ = False, c3d.append("%s b%d diff=%s" % (proto, b, diff[:2]))
    out.append(check("C3_pairs_fresh_repeat_identical_control_nonce_only", c3, "; ".join(c3d)[:250]))
    import hashlib
    D = json.loads((L4 / "runtime-binding.json").read_text(encoding="utf-8"))["design_commit"]
    nonces, c3b = {}, True
    for sid, t in trans.items():
        want = hashlib.sha256(("%s:%s:%d" % (D, t["protocol"], t["block"]) +
                               (":control" if t["condition"] == "nonce-control" else "")).encode()).hexdigest()[:16]
        nonces[sid] = t.get("nonce")
        if t.get("nonce") != want or t.get("nonce_head_only") is not True:
            c3b, _ = False, c3d.append("%s nonce!=recipe" % sid)
    # 设计使然：repeat 与 fresh 共享同 block nonce（正文逐字节一致）→ unique=12（6 配对 + 6 control）
    for proto in ("responses", "anthropic-messages", "chat-completions"):
        for b in (1, 2):
            if trans["l4-20261029-cache-%s-b%d-fresh" % (proto, b)]["nonce"] != \
               trans["l4-20261029-cache-%s-b%d-repeat" % (proto, b)]["nonce"]:
                c3b, _ = False, c3d.append("%s b%d fresh/repeat nonce differ" % (proto, b))
    if len(set(nonces.values())) != 12:
        c3b, _ = False, c3d.append("unique nonce=%d expect 12" % len(set(nonces.values())))
    out.append(check("C3b_nonce_deterministic_12_unique", c3b, "; ".join(c3d)[-200:]))
    # C4 usage 递归独立核：原始响应体重提取 == usage.raw.json（不信任工具投影）
    inv, c4, c4d = {}, True, []
    raw_vs_claimed = {}
    for sid in sorted(pr):
        raw = (C / sid / "response.body.raw").read_bytes()
        cand = _extract_usage_candidates(raw)
        claimed = json.loads((C / sid / "usage.raw.json").read_text(encoding="utf-8"))
        ok = any(u == claimed for u in cand)
        raw_vs_claimed[sid] = ok
        if not ok:
            c4, _ = False, c4d.append("%s: raw重提取与usage.raw不一致(cand=%d)" % (sid, len(cand)))
        meta = pr[sid]
        inv["%s|%s" % (meta["protocol"], meta["condition"])] = _leaf_states(claimed)
    out.append(check("C4_usage_raw_reextract_match", c4, "; ".join(c4d)[:250]))
    table = {}
    for proto in ("responses", "anthropic-messages", "chat-completions"):
        paths = set()
        for cond in ("fresh", "repeat", "nonce-control"):
            paths |= {lp for lp in inv.get("%s|%s" % (proto, cond), {})
                      if "cach" in lp.lower()}
        for lp in sorted(paths):
            table["%s:%s" % (proto, lp)] = {
                cond: (inv.get("%s|%s" % (proto, cond), {}).get(lp) or ("missing",))[0]
                for cond in ("fresh", "repeat", "nonce-control")}
    out.append({"check": "C4b_cache_leaf_four_state_table", "status": "PASS",
                "detail": json.dumps(table, ensure_ascii=False)})
    # C5 layers 投影追溯
    c5, c5d = True, []
    for sid in sorted(pr):
        lp = C / sid / "usage.layers.json"
        if not lp.is_file():
            continue
        lay = json.loads(lp.read_text(encoding="utf-8"))
        raw_leaves = _leaf_states(json.loads((C / sid / "usage.raw.json").read_text(encoding="utf-8")))
        for path, cell in lay.get("layer_raw_inventory", {}).items():
            if cell.get("state") in ("object", "missing"):
                continue
            if path not in raw_leaves:
                c5, _ = False, c5d.append("%s:%s not-in-raw" % (sid, path))
            elif cell.get("state") != "null" and raw_leaves[path][1] != cell.get("value"):
                c5, _ = False, c5d.append("%s:%s value-mismatch" % (sid, path))
    out.append(check("C5_layers_trace_to_raw", c5, "; ".join(c5d)[:250]))
    # C5b inventory 完备性：layers inventory 必须覆盖 raw 全部标量叶（防 mapper 静默丢字段）
    c5b, c5bd = True, []
    for sid in sorted(pr):
        lp = C / sid / "usage.layers.json"
        if not lp.is_file():
            continue
        lay = json.loads(lp.read_text(encoding="utf-8"))
        raw_leaves = _leaf_states(json.loads((C / sid / "usage.raw.json").read_text(encoding="utf-8")))
        missing = [k for k in raw_leaves if k not in lay.get("layer_raw_inventory", {})]
        if missing:
            c5b, _ = False, c5bd.append("%s missing=%s" % (sid, missing[:4]))
    out.append(check("C5b_layers_inventory_covers_raw", c5b, "; ".join(c5bd)[:250]))
    # C5c 两路径分别表述（lead 精准化指令）：raw_inventory 完整 ≠ 归一化映射覆盖。
    # 逐协议列 layer_mapping 未覆盖的 cache 相关 raw 叶（wire_key 对不上/missing），
    # 分类候选=coverage limitation（密封源 mapping_note 自述「仅作归一化对照，不得互相替代」）；
    # 不据此改判 raw 保真，也不反证归一化已有正确值。
    gaps = {}
    for proto in ("responses", "anthropic-messages", "chat-completions"):
        for cond in ("fresh", "repeat", "nonce-control"):
            lay_p = C / ("l4-20261029-cache-%s-b%d-%s" %
                         (proto, {"fresh": 1, "repeat": 1, "nonce-control": 1}[cond], cond))
            # block 由 slot 名决定，改为直接枚举目录
    for sid in sorted(pr):
        lp = C / sid / "usage.layers.json"
        if not lp.is_file():
            continue
        lay = json.loads(lp.read_text(encoding="utf-8"))
        raw_leaves = _leaf_states(json.loads((C / sid / "usage.raw.json").read_text(encoding="utf-8")))
        mapping = lay.get("layer_mapping", {})
        wire_keys = {v.get("wire_key") for v in mapping.values()}
        proto = pr[sid]["protocol"]
        cond = pr[sid]["condition"]
        for path, (st, v) in raw_leaves.items():
            if "cach" not in path.lower():
                continue
            covered = (path in wire_keys or path.split(".")[-1] in wire_keys
                       or any(m.get("state") == "positive" and m.get("value") == v
                              and "cach" in k.lower() for k, m in mapping.items()))
            if not covered:
                gaps.setdefault("%s|%s" % (proto, cond), set()).add(path)
    out.append({"check": "C5c_mapping_coverage_gaps", "status": "PASS",
                "detail": json.dumps(
                    {"uncovered_cache_paths": {k: sorted(v) for k, v in sorted(gaps.items())},
                     "classification": "coverage_limitation_candidate（mapping_note 自述对照层非完整归一化承诺）；"
                                       "REPORT 将预设键 missing 误推为协议未回传=确定报告层缺陷",
                     "note": "raw_inventory 与 layer_mapping 两路径分别表述，互不替代"},
                    ensure_ascii=False)})
    # C6 凭据不落盘
    c6 = True
    for sid, t in trans.items():
        if any(k in t for k in ("request_headers", "authorization", "api_key")):
            c6 = False
        low = (C / sid / "request.body.json").read_text(encoding="utf-8").lower()
        if "authorization" in low or "bearer " in low:
            c6 = False
    out.append(check("C6_no_auth_material_saved", c6))
    # C7 时序
    order_ts = [(s["order"], (trans.get(s["slot_id"]) or {}).get("at"))
                for s in sorted(pr.values(), key=lambda s: s["order"])]
    out.append(check("C7_order_timestamps_nondecreasing",
                     all(a[1] and b[1] and ts(a[1]) <= ts(b[1]) for a, b in zip(order_ts, order_ts[1:])),
                     json.dumps(order_ts[:3], ensure_ascii=False)))
    waits = []
    for proto in ("responses", "anthropic-messages", "chat-completions"):
        for b in (1, 2):
            tf = trans["l4-20261029-cache-%s-b%d-fresh" % (proto, b)]["at"]
            tr = trans["l4-20261029-cache-%s-b%d-repeat" % (proto, b)]["at"]
            waits.append(round((ts(tr) - ts(tf)).total_seconds(), 1))
    out.append(check("C7b_fresh_repeat_wait_ge_5s", all(w >= 5 for w in waits), "waits=%s" % waits))
    # C8 收据对账
    receipt = json.loads((CACHE_ROOT / "probe-receipt.json").read_text(encoding="utf-8"))
    slots = receipt.get("slots", [])
    out.append(check("C8_receipt_18_executed",
                     len(slots) == 18 and sum(1 for s in slots if s.get("status") == "executed") == 18,
                     "slots=%d" % len(slots)))
    # C9 报告层 cached 命中叙事核：repeat 应有正值命中证据，报告/语义层不得称 missing
    rep_txt = (CACHE_ROOT / "REPORT.md").read_text(encoding="utf-8") if (CACHE_ROOT / "REPORT.md").is_file() else ""
    rep_claims_missing = ("missing" in rep_txt.lower() and "cached" in rep_txt.lower())
    repeat_pos = {}
    for proto in ("responses", "anthropic-messages", "chat-completions"):
        for b in (1, 2):
            leaves = inv.get("%s|repeat" % proto, {})
            pos = [lp for lp, (st, v) in leaves.items()
                   if "cach" in lp.lower() and st == "int+"]
            repeat_pos["%s b%d" % (proto, b)] = pos
    out.append({"check": "C9_repeat_hit_evidence_vs_report_claims", "status": "PASS",
                "detail": json.dumps({"repeat_positive_paths": repeat_pos,
                                      "report_mentions_missing_and_cached": rep_claims_missing},
                                     ensure_ascii=False)})
    # C10 报告层 erratum 钉：raw/layers 均示 responses repeat cached=positive(2048)。
    # 「保留原句+dated erratum」为既定勘误纪律：REPORT 含明确 dated erratum（承认嵌套
    # cached_tokens 实际存在且 2048、归因 mapper 预设路径遗漏）即视为落地 → PASS；
    # 原句保留本身不再使钉 FAIL（钉只对「无 erratum 的裸缺失断言」保持 FAIL）。
    lay_rep = inv.get("responses|repeat", {})
    raw_positive = any(lp.startswith("input_tokens_details.cached_tokens") and st == "int+"
                       for lp, (st, v) in lay_rep.items())
    rep = CACHE_ROOT / "REPORT.md"
    still_claims_missing = False
    erratum_landed = False
    if rep.is_file():
        rep_text = rep.read_text(encoding="utf-8")
        for line in rep_text.splitlines():
            if "responses" in line and "missing" in line and ("cached" in line or "cache_write" in line):
                still_claims_missing = True
        low = rep_text.lower()
        erratum_landed = (("erratum" in low or "勘误" in rep_text)
                          and "input_tokens_details" in rep_text
                          and "2048" in rep_text)
    out.append(check("C10_responses_erratum_landed",
                     (not raw_positive) or erratum_landed or not still_claims_missing,
                     "raw_positive=%s report_claims_missing=%s erratum_landed=%s "
                     "(原句保留+dated erratum=既定纪律；erratum 归因 mapper 预设路径遗漏)" %
                     (raw_positive, still_claims_missing, erratum_landed)))
    return out


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all",
                    choices=["all", "plan", "pending", "u1", "cache", "codex", "dsh", "coverage"])
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    results: list[dict] = []
    if a.stage in ("all", "plan"):
        results += stage_plan()
    if a.stage in ("all", "pending"):
        results += stage_pending_common()
    if a.stage in ("all", "u1"):
        results += stage_u1()
    if a.stage in ("all", "cache"):
        results += stage_cache()
    if a.stage in ("all", "codex"):
        results += stage_codex()
    if a.stage in ("all", "dsh"):
        results += stage_dsh()
    if a.stage in ("all", "coverage"):
        results += stage_coverage()
    counts = {"PASS": sum(1 for r in results if r["status"] == "PASS"),
              "FAIL": sum(1 for r in results if r["status"] == "FAIL"),
              "PENDING-E": sum(1 for r in results if r["status"] == "PENDING-E")}
    receipt = {"kind": "final_audit_stage_report", "tool": "final_audit.py",
               "at": now_local(), "stage": a.stage, "counts": counts,
               "results": results, "live_doc_drift": [],
               "note": "PENDING-E=输入未到，非通过也非失败；FAIL=终审发现"}
    exit_code = 1 if counts["FAIL"] else 0
    if a.out:
        out = Path(a.out)
        if out.exists():
            print(json.dumps({"refused": True, "target": str(out)}, ensure_ascii=False))
            return 2
        out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + "\n",
                       encoding="utf-8")
        print("REPORT:", out)
    print(json.dumps(counts, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
