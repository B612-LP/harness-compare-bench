#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cache_fake_e2e.py — judge 独立 L4 cache probe fake e2e harness（阶段I）。

双模式：
  subprocess 真实入口（K1 E-block / K2 dry / K8 拒绝代理网络错误 / K9 收据 write-once）；
  module-inject（K3–K7）：monkeypatch http_post 喂对抗脚本，驱动**真实 run_slot/execute
  状态机**；哨兵保证零非本地连接。不信任 builder 自测计数。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from l4_fixture import build_fixture, harness_env, jdump, sha_file  # noqa: E402


def now_marker() -> str:
    import datetime as dt
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(timespec="seconds")


PROTOCOLS = ("responses", "anthropic-messages", "chat-completions")


def usage_for(protocol: str, variant: str) -> dict:
    if protocol == "responses":
        base = {"input_tokens": 120, "cached_input_tokens": 80,
                "cache_write_input_tokens": 0, "output_tokens": 9, "total_tokens": 209}
    elif protocol == "anthropic-messages":
        base = {"input_tokens": 120, "cache_read_input_tokens": 80,
                "cache_creation_input_tokens": 5, "output_tokens": 9}
    else:
        base = {"prompt_tokens": 120, "completion_tokens": 9, "total_tokens": 129,
                "prompt_tokens_details": {"cached_tokens": 80}}
    if variant == "nulls":
        keep = {k: (None if isinstance(v, int) and k != "total_tokens" else v)
                for k, v in base.items() if not isinstance(v, dict)}
        return keep
    if variant == "missing":
        return {k: v for k, v in base.items() if isinstance(v, int) and v not in (80,)}
    return base


def resp_bytes(protocol: str, variant="full", status=200, raw=None) -> bytes:
    if raw is not None:
        return raw
    body = {"id": "resp-%s-%s" % (protocol, variant), "usage": usage_for(protocol, variant)}
    return json.dumps(body).encode("utf-8")


INJECT_SCRIPT = r"""
import importlib.util, json, sys, os
runner = sys.argv[1]; script_name = sys.argv[2]
spec = importlib.util.spec_from_file_location("cacheprobe", runner)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
calls = []
def fake_http_post(url, body_bytes, key, timeout):
    calls.append({"url": url, "body_sha_prefix": __import__("hashlib").sha256(body_bytes).hexdigest()[:16],
                  "key_head": key[:9]})
    sc = SCRIPTS[script_name]
    resp = sc(calls[-1], len(calls))
    return resp
def SCRIPTS(call, n):
    raise RuntimeError("replaced below")
# 由外层 exec 注入 SCRIPT/参数
"""

CACHE_MAIN = r"""
MARK = "@@RESULT@@"
import importlib.util, json, sys, hashlib
runner, mode = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location("cacheprobe", runner)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
calls = []
def make_fake(responder):
    def fake_http_post(url, body_bytes, key, timeout):
        rec = {"url": url, "n": len(calls) + 1,
               "body_sha": hashlib.sha256(body_bytes).hexdigest()}
        calls.append(rec)
        return responder(rec, body_bytes)
    return fake_http_post
m.REPEAT_GAP_S = 0  # harness 注入：消除真实 5s 等待（时序不变量另测）
plan = json.load(open(m.PLAN_PATH))
probes = sorted(plan["probe_slots"], key=lambda s: s["order"])
def slot_by(sid):
    return [s for s in probes if s["slot_id"] == sid][0]
# body_sha → slot（call 序会因 R4.5 跳发而错位，必须按请求体定位）
import hashlib as _h
prefix = m.synthetic_prefix()
BODY2SLOT = {}
for _s in probes:
    _nonce = (m.deterministic_nonce(_s["protocol"], _s["block"], control=True)
              if _s["condition"] == "nonce-control"
              else m.deterministic_nonce(_s["protocol"], _s["block"], control=False))
    _body = json.dumps(m.build_body(_s["protocol"], _nonce, prefix,
                                    _s["max_output_tokens"]), ensure_ascii=False).encode()
    BODY2SLOT[_h.sha256(_body).hexdigest()] = _s
USAGE_BY_SLOT = {s["slot_id"]: USAGE_FOR(s["protocol"],
                 "full" if i % 3 == 0 else ("nulls" if i % 3 == 1 else "missing"))
                 for i, s in enumerate(probes)}
FRESH_OF = {}  # repeat/control 体 → 代表 fresh 槽（同块同协议）
for _s in probes:
    _k = (_s["protocol"], _s["block"])
    FRESH_OF.setdefault(_k, _s)
    FRESH_OF[_k + ("ctl",)] = _s if _s["condition"] == "nonce-control" else FRESH_OF.get(_k + ("ctl",), FRESH_OF[_k])
kind = {"K3": "happy", "K4": "auth401", "K5": "http429",
        "K6": "net5xx", "K7": "badjson"}[mode]
CALL_N = {}  # 同一体可能发两次（fresh→repeat）：按序判别
def ok200(slot):
    import json as _j
    return 200, _j.dumps({"id": "resp", "usage": USAGE_BY_SLOT[slot["slot_id"]]}).encode(), \
        ["content-type", "x-request-id"], 0.0, 0.01, None
def responder(rec, body_bytes):
    n = CALL_N.get(rec["body_sha"], 0) + 1
    CALL_N[rec["body_sha"]] = n
    s = BODY2SLOT[rec["body_sha"]]
    is_repeat_call = (n >= 2)
    if kind == "auth401":
        return 401, b'{"error":"bad key"}', [], 0.0, 0.01, None
    if kind == "http429":
        if (s["protocol"], s["block"]) == ("responses", 1) and is_repeat_call:
            return 429, b'{"error":"rate"}', [], 0.0, 0.01, None
        return ok200(s)
    if kind == "net5xx":
        if s["protocol"] == "anthropic-messages" and s["block"] == 1:
            return 503, b"upstream", [], 0.0, 0.01, None
        return ok200(s)
    if kind == "badjson":
        if (s["protocol"], s["block"], n) == ("responses", 1, 1):
            return 200, b"<html>not json</html>", [], 0.0, 0.01, None
        return ok200(s)
    return ok200(s)
m.http_post = make_fake(responder)
rc = m.execute(False, None)
print(MARK + json.dumps({"rc": rc, "http_calls": calls}, ensure_ascii=False))
"""


def inject_env(fx, log):
    return harness_env(fx, log_name=log)


def usage_json_for(protocol, variant):
    return usage_for(protocol, variant)


# 让 INJECT 主脚本可用 USAGE_FOR（注入为全局）
CACHE_MAIN = CACHE_MAIN.replace("USAGE_FOR(", "__USAGE_FOR__(")
USAGE_HELPER = "\nimport functools\n" + \
    "def __USAGE_FOR__(protocol, variant):\n" + \
    "    return json.loads(%r)(protocol, variant)\n"


def run_inject(fx, mode: str) -> dict:
    """module-inject 模式：真实 execute 状态机 + 对抗 http_post。"""
    runner = fx["CACHE"] / "tools" / "cache_probe.py"
    env = inject_env(fx, "sentinel-inject.log")
    helper = (
        "def USAGE_FOR(protocol, variant):\n"
        "    import json as _j\n"
        "    base = {\n"
        "     'responses': {'input_tokens':120,'cached_input_tokens':80,'cache_write_input_tokens':0,'output_tokens':9,'total_tokens':209},\n"
        "     'anthropic-messages': {'input_tokens':120,'cache_read_input_tokens':80,'cache_creation_input_tokens':5,'output_tokens':9},\n"
        "     'chat-completions': {'prompt_tokens':120,'completion_tokens':9,'total_tokens':129,'prompt_tokens_details':{'cached_tokens':80}},\n"
        "    }[protocol]\n"
        "    if variant=='nulls':\n"
        "        return {k:(None if isinstance(v,int) and k!='total_tokens' else v) for k,v in base.items() if not isinstance(v,dict)}\n"
        "    if variant=='missing':\n"
        "        return {k:v for k,v in base.items() if isinstance(v,int) and v!=80}\n"
        "    return dict(base)\n")
    script = CACHE_MAIN.replace("__USAGE_FOR__", "USAGE_FOR")
    code = helper + script
    p = subprocess.run([sys.executable, "-c", code, str(runner), mode],
                       capture_output=True, text=True, env=env, timeout=600,
                       cwd=str(fx["REPO"]))
    out = None
    for line in (p.stdout or "").splitlines():
        if line.startswith("@@RESULT@@"):
            out = json.loads(line[10:])
    return {"rc": p.returncode, "stdout_tail": (p.stdout or "")[-800:],
            "stderr_tail": (p.stderr or "")[-2000:], "result": out}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snap", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--only", default=None)
    a = ap.parse_args()
    snap = Path(a.snap).resolve()
    out_dir = Path(a.out) if a.out else (Path(__file__).resolve().parent / "results" / snap.name)
    work_root = Path("/tmp/judge-l4/fixture-cache-" + snap.name.split("-", 1)[-1])
    if work_root.exists():
        shutil.rmtree(work_root)
    work_root.mkdir(parents=True)
    fx = build_fixture(snap, work_root, trees=("cache",))
    # 清理快照自带的既往产物（收据/证据/dry 树），保证 write-once 语义可测
    for rel in ("probe-receipt.json", "probe-receipt-dryrun.json", "dryrun", "probes"):
        p = fx["CACHE"] / rel
        shutil.rmtree(p, ignore_errors=True) if p.is_dir() else (
            p.unlink(missing_ok=True))
    cases, only = {}, (set(a.only.split(",")) if a.only else None)

    def rec(name, verdict, detail):
        cases[name] = {"verdict": verdict, "detail": detail}

    def run_case(n):
        return (only is None) or (n in only)

    PROBES_DIR = fx["CACHE"] / "probes"
    DRY_DIR = fx["CACHE"] / "dryrun"
    RECEIPT = fx["CACHE"] / "probe-receipt.json"
    RUNNER = fx["CACHE"] / "tools" / "cache_probe.py"
    SLOT_PREFIX = "l4-20261029-cache-"

    def slot_ids():
        plan = json.loads((fx["L4"] / "plan.json").read_text(encoding="utf-8"))
        return [s["slot_id"] for s in sorted(plan["probe_slots"], key=lambda x: x["order"])]

    # ---- K1 E-block ----
    if run_case("K1_e_seal_block"):
        env = harness_env(fx, log_name="sentinel-k1.log")
        fx["binding"](False)
        p = subprocess.run([sys.executable, str(RUNNER), "run"],
                           capture_output=True, text=True, env=env, timeout=300,
                           cwd=str(fx["REPO"]))
        rec("K1_e_seal_block", "pass" if (p.returncode != 0 and not RECEIPT.exists()
                                          and not PROBES_DIR.exists()) else "fail",
            {"rc": p.returncode, "stderr_tail": (p.stderr or "")[-400:],
             "receipt_absent": not RECEIPT.exists(),
             "probes_absent": not PROBES_DIR.exists()})

    # ---- K2 dry-run 全 18 槽 + 不变式 ----
    if run_case("K2_dry_run_invariants"):
        fx["binding"](False)
        env = harness_env(fx, log_name="sentinel-k2.log")
        p = subprocess.run([sys.executable, str(RUNNER), "dry-run"],
                           capture_output=True, text=True, env=env, timeout=300,
                           cwd=str(fx["REPO"]))
        drys = {}
        for sid in slot_ids():
            f = DRY_DIR / "probes" / sid / "dry-run.json"
            drys[sid] = json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
        D = "bb14897a7d1ac26c06697bb80a15d94158cd8ae0"
        problems = []
        if not all(drys.values()):
            problems.append("missing dry files")
        for proto in PROTOCOLS:
            for b in (1, 2):
                fresh = drys.get("%s%s-b%d-fresh" % (SLOT_PREFIX, proto, b))
                rep = drys.get("%s%s-b%d-repeat" % (SLOT_PREFIX, proto, b))
                ctl = drys.get("%s%s-b%d-nonce-control" % (SLOT_PREFIX, proto, b))
                if not (fresh and rep and ctl):
                    continue
                if fresh["request_sha256"] != rep["request_sha256"]:
                    problems.append("fresh!=repeat %s b%d" % (proto, b))
                if ctl["request_sha256"] == fresh["request_sha256"]:
                    problems.append("control==fresh %s b%d" % (proto, b))
                want = hashlib.sha256(("%s:%s:%d" % (D, proto, b)).encode()).hexdigest()[:16]
                if fresh["nonce"] != want:
                    problems.append("nonce mismatch %s b%d" % (proto, b))
                if not (0 < fresh["prefix_bytes"] <= 16384):
                    problems.append("prefix bytes %s" % proto)
        dry_not_in_real = not PROBES_DIR.exists()
        rec("K2_dry_run_invariants", "pass" if (p.returncode == 0 and not problems
                                                and dry_not_in_real) else "fail",
            {"rc": p.returncode, "problems": problems,
             "dry_files": sum(1 for v in drys.values() if v),
             "dry_receipt": (DRY_DIR / "probe-receipt-dryrun.json").exists(),
             "real_probes_dir_absent": dry_not_in_real,
             "stderr_tail": (p.stderr or "")[-400:]})

    # ---- K3–K7 module-inject ----
    fx["binding"](True)
    if run_case("K3_happy_all_ok"):
        shutil.rmtree(PROBES_DIR, ignore_errors=True)
        r = run_inject(fx, "K3")
        res = r.get("result") or {}
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8")) if RECEIPT.exists() else {}
        acc = receipt.get("slot_accounting", {})
        n_ok = sum(1 for v in acc.values() if v == "executed")
        # usage 三态抽查：responses-b1-fresh raw 存在且 layer 含 positive/zero
        f = PROBES_DIR / (SLOT_PREFIX + "responses-b1-fresh")
        layers = json.loads((f / "usage.layers.json").read_text()) if (f / "usage.layers.json").exists() else {}
        states = set()
        for e in (layers.get("layer_mapping") or {}).values():
            states.add(e.get("state"))
        f_ctl = PROBES_DIR / (SLOT_PREFIX + "responses-b1-nonce-control")
        states_ctl = set()
        if (f_ctl / "usage.layers.json").exists():
            for e in json.loads((f_ctl / "usage.layers.json").read_text()).get("layer_mapping", {}).values():
                states_ctl.add(e.get("state"))
        rec("K3_happy_all_ok", "pass" if (res and res.get("rc") == 0 and n_ok == 18
                                          and len(res.get("http_calls", [])) == 18
                                          and {"positive", "zero"} <= states_ctl
                                          and "null" in states) else "fail",
            {"rc": r["rc"], "executed": n_ok, "http_calls": len(res.get("http_calls", [])),
             "layer_states_responses_b1_ctl": sorted(states_ctl),
             "layer_states_responses_b1_fresh": sorted(states),
             "raw_saved": (f / "usage.raw.json").exists(),
             "stderr_tail": r["stderr_tail"][-600:]})

    if run_case("K4_auth401_global_stop"):
        for rel in ("probes", "probe-receipt.json"):
            p = fx["CACHE"] / rel
            shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
        r = run_inject(fx, "K4")
        res = r.get("result") or {}
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8")) if RECEIPT.exists() else {}
        acc = receipt.get("slot_accounting", {})
        executed = [k for k, v in acc.items() if v == "executed"]
        fresh_sid = SLOT_PREFIX + "responses-b1-fresh"
        failed = sorted(k for k, v in acc.items() if v == "failed")
        rec("K4_auth401_global_stop", "pass" if (failed == [fresh_sid]
                                                 and len(res.get("http_calls", [])) == 1) else "fail",
            {"failed": failed, "http_calls": len(res.get("http_calls", [])),
             "not_executed_n": sum(1 for v in acc.values() if v == "not_executed"),
             "stderr_tail": r["stderr_tail"][-400:]})

    if run_case("K5_http429_protocol_stop"):
        for rel in ("probes", "probe-receipt.json"):
            p = fx["CACHE"] / rel
            shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
        r = run_inject(fx, "K5")
        res = r.get("result") or {}
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8")) if RECEIPT.exists() else {}
        acc = receipt.get("slot_accounting", {})
        executed = sorted(k for k, v in acc.items() if v == "executed")
        responses_pending = [k for k in executed if "responses" in k]
        others = [k for k in executed if "responses" not in k]
        rec("K5_http429_protocol_stop", "pass" if (len(responses_pending) == 1 and len(others) == 12
                                                   and len(res.get("http_calls", [])) == 14) else "fail",
            {"responses_executed_ok": responses_pending, "other_executed_ok_n": len(others),
             "http_calls": len(res.get("http_calls", [])),
             "stderr_tail": r["stderr_tail"][-400:]})

    if run_case("K6_net5xx_two_strike"):
        for rel in ("probes", "probe-receipt.json"):
            p = fx["CACHE"] / rel
            shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
        r = run_inject(fx, "K6")
        res = r.get("result") or {}
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8")) if RECEIPT.exists() else {}
        acc = receipt.get("slot_accounting", {})
        executed = sorted(k for k, v in acc.items() if v == "executed")
        anthro = [k for k in executed if "anthropic" in k]
        anthro_failed = [k for k, v in acc.items() if v == "failed" and "anthropic" in k]
        rec("K6_net5xx_two_strike", "pass" if (len(anthro) == 0 and len(anthro_failed) == 2 and
                                               len(res.get("http_calls", [])) == 14) else "fail",
            {"anthropic_executed_ok": anthro, "anthropic_failed": anthro_failed,
             "http_calls": len(res.get("http_calls", [])),
             "note": "5xx 消费 2 槽后该协议停；其余协议不受影响（12+2=14 次外发）",
             "stderr_tail": r["stderr_tail"][-400:]})

    if run_case("K7_badjson_raw_preserved"):
        for rel in ("probes", "probe-receipt.json"):
            p = fx["CACHE"] / rel
            shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
        r = run_inject(fx, "K7")
        res = r.get("result") or {}
        f = PROBES_DIR / (SLOT_PREFIX + "responses-b1-fresh")
        raw_p = f / "response.body.raw"
        raw = raw_p.read_bytes() if raw_p.exists() else b""
        transport = json.loads((f / "transport.json").read_text()) if (f / "transport.json").exists() else {}
        rec("K7_badjson_raw_preserved", "pass" if (raw == b"<html>not json</html>"
                                                   and transport.get("parse_error")
                                                   and "usage_raw" not in transport) else "fail",
            {"raw_bytes": raw[:60].decode(errors="replace"),
             "parse_error": transport.get("parse_error"),
             "transport_has_usage_raw": "usage_raw" in transport,
             "raw_response_sha256": transport.get("raw_response_sha256")})

    # ---- K8 真实 socket：拒绝代理 → 网络错误路径 ----
    if run_case("K8_real_socket_refused_proxy"):
        for rel in ("probes", "probe-receipt.json"):
            p = fx["CACHE"] / rel
            shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
        env = harness_env(fx, log_name="sentinel-k8.log",
                          extra={"HTTPS_PROXY": "http://127.0.0.1:1",
                                 "HTTP_PROXY": "http://127.0.0.1:1",
                                 "NO_PROXY": ""})
        fx["binding"](True)
        p = subprocess.run([sys.executable, str(RUNNER), "run"],
                           capture_output=True, text=True, env=env, timeout=600,
                           cwd=str(fx["REPO"]))
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8")) if RECEIPT.exists() else {}
        acc = receipt.get("slot_accounting", {})
        executed = sorted(k for k, v in acc.items() if v == "failed")
        intents = sorted(str(q.parent.name) for q in PROBES_DIR.rglob("intent.json"))
        responses = list(PROBES_DIR.rglob("response.body.raw"))
        slog = (fx["sentinel_lib"].parent / "sentinel-k8.log")
        non_local = sum(1 for l in slog.read_text().splitlines() if "allowed=False" in l) \
            if slog.exists() else -1
        rec("K8_real_socket_refused_proxy", "pass" if (len(executed) == 6 and len(intents) == 6
                                                       and not responses and non_local == 6) else "fail",
            {"rc": p.returncode, "failed_executed_slots": executed,
             "intent_files": len(intents), "response_raw_files": len(responses),
             "sentinel_non_local_attempts": non_local,
             "criterion_note": "6 次外发尝试全部非本地直连且被哨兵拒绝=零真实请求完成；"
                               "每槽恰 1 次（无重试）；2 击停协议×3",
             "stderr_tail": (p.stderr or "")[-400:]})

    # ---- K9 收据 write-once（重复真实 run 拒绝）----
    if run_case("K9_receipt_write_once"):
        before = len(list(PROBES_DIR.rglob("intent.json"))) if PROBES_DIR.exists() else 0
        env = harness_env(fx, log_name="sentinel-k9.log",
                          extra={"HTTPS_PROXY": "http://127.0.0.1:1"})
        p = subprocess.run([sys.executable, str(RUNNER), "run"],
                           capture_output=True, text=True, env=env, timeout=300,
                           cwd=str(fx["REPO"]))
        after = len(list(PROBES_DIR.rglob("intent.json"))) if PROBES_DIR.exists() else 0
        rec("K9_receipt_write_once", "pass" if (p.returncode != 0 and after == before) else "fail",
            {"rc": p.returncode, "intents_before": before, "intents_after": after,
             "stderr_tail": (p.stderr or "")[-500:]})

    receipt = {
        "kind": "judge_fake_e2e_receipt", "harness": "cache_fake_e2e.py",
        "harness_sha256": sha_file(Path(__file__).resolve()),
        "fixture_sha": sha_file(Path(__file__).resolve().parent / "l4_fixture.py"),
        "snapshot": str(snap),
        "snapshot_head_shas": {n: sha_file(snap / n) for n in
                               ("src-cache/tools/cache_probe.py", "plan.json",
                                "contract.json", "gate.py", "execution_seal.py")},
        "fixture_repo": str(fx["REPO"]), "binding_E": fx["E"], "registered_at": fx["tE"],
        "generated_at": now_marker(), "cases": cases, "live_doc_drift": None,
    }
    outp = out_dir / "cache-fake-e2e-receipt.json"
    if outp.exists():
        outp = out_dir / ("cache-fake-e2e-receipt.%d.json" % int(time.time()))
    jdump(outp, receipt)
    print(json.dumps({"receipt": str(outp),
                      "verdicts": {k: v["verdict"] for k, v in cases.items()}},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
