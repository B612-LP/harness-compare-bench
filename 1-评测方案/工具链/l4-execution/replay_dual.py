#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L4 双归档离线反事实重放（offline_recompute；零模型）。v2——S6 判据诚实化。

设计命题（PREREG §3B / CLARIFICATION §E）：同一份原始证据（母本，只读）复制到两个独立
sandbox 副本，分别按旧/新归档测量语义重放**后处理**，量化"记录留存、可判定性、usage 投影"
差异。等价模拟（equivalent_simulation），非旧/新完整 pipeline 原样复现。

S6 修正（reviewer 对 6900f620 的三项）：
1. current 侧对会话轨迹做 **text/usage 局部投影**（partial_text_usage_projection：
   解析会话轨迹→text/usage 字段实测；scope 明示 reasoning/tool_call/tool_result/turn
   边界事件未含——**非完整流**，不同于 lab.py rebuild_full_stream 的完整事件重建，
   不得以"session 目录存在"冒充；
2. legacy usage 须与"旧 pipeline 读已丢失日志"语义一致——log 已丢 ⇒ usage **unknown**
   （不从会话轨迹补造 legacy 数字）；
3. 分数：本 harness 不运行 checker ⇒ 双侧 score 一律 **not_evaluated/unknown**，
   不作任何"分数不变"声称。适配边界保留；unknown 带 impact/next_step/stop_condition；
   母本前后 sha 对账。

用法：
  python3 replay_dual.py --run <evidence_dir> --case <case> --out <report.json>
  python3 replay_dual.py --selftest
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SPEC = "l4-dual-archive-replay"


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sha_dir_state(p: Path) -> dict:
    out = {}
    for f in sorted(p.rglob("*")):
        if f.is_file():
            out[str(f.relative_to(p))] = hashlib.sha256(f.read_bytes()).hexdigest()
    return out


def session_lines(sess_dir: Path):
    for p in sorted(sess_dir.iterdir()):
        if not p.is_file():
            continue
        if p.suffix == ".zstd":
            out = subprocess.run(["zstd", "-dc", str(p)], capture_output=True, timeout=300)
            text = out.stdout.decode("utf-8", errors="replace")
        elif p.suffix == ".jsonl":
            text = p.read_text(encoding="utf-8", errors="replace")
        else:
            continue
        for line in text.splitlines():
            yield p.name, line


def map_usage(u: dict) -> dict:
    out = {"input_tokens": u.get("inputTokens"), "output_tokens": u.get("outputTokens")}
    if "cacheReadTokens" in u:
        out["cache_read_tokens"] = u.get("cacheReadTokens")
    if "cacheWriteTokens" in u:
        out["cache_creation_tokens"] = u.get("cacheWriteTokens")
    return out


def unknown_usage(reason: str) -> dict:
    return {"status": "unknown", "reason": reason,
            "requests": None, "input_tokens": None, "output_tokens": None,
            "cache_read_tokens": None, "cache_creation_tokens": None, "per_call": None,
            "unknown": {"impact": "旧管线下该场 usage 不可判定，任何非空数字都是补造",
                        "next_step": "以 current 侧会话轨迹投影作参照披露",
                        "stop_condition": "不补造数据；差异仅在投影语义层解释"}}


def legacy_postprocess() -> dict:
    """r1030 语义在副本内的后处理：日志已随输出目录 rmtree 丢失。

    usage/integrity 的数据源即已丢失的 raw log ⇒ usage unknown、integrity vacuous。
    **不从会话轨迹补造 legacy 数字**（旧管线不读会话轨迹）。"""
    return {"raw_stdout": {"status": "lost", "bytes": None, "sha256": None},
            "integrity": {"lines": 0, "violations": 0, "vacuous": True,
                          "basis": "数据源(raw log)已丢失——空流扫描无判定力，不代表无违规",
                          "evidence": []},
            "usage": unknown_usage("legacy pipeline 只读 raw log；log 已随输出目录 rmtree 丢失（r1030#1 在副本内复现）"),
            "score": {"status": "not_evaluated",
                      "reason": "replay harness 不运行 checker；旧管线分数声称不可复现验证",
                      "unknown": {"impact": "无法证实/证伪历史分数等值",
                                  "next_step": "如需分数反事实须在副本内真实重跑冻结 checker（另行设计）",
                                  "stop_condition": "不宣称分数不变"}}}


def _rebuild_events(sess_dir: Path) -> list:
    """text/usage 局部投影（partial_text_usage_projection 底层）；独立实现避免跨批次依赖。

    不同于 lab.py rebuild_full_stream 的完整事件重建：reasoning/tool_call/tool_result/
    turn 边界事件不投影（见 partial_text_usage_projection.scope）。"""
    events, last_text, pending = [], {}, {}
    for _s, line in session_lines(sess_dir):
        try:
            ev = json.loads(line)
        except Exception:
            continue
        t = ev.get("type")
        if t == "session":
            events.append({"type": "session", "sessionId": ev.get("id")})
        elif t == "assistant/message":
            d = ev["data"]
            if isinstance(d.get("usage"), dict):
                pending[(d.get("turn"), d.get("step"))] = d["usage"]
            for b in d["message"]["content"]:
                if b.get("type") == "text":
                    events.append({"type": "text", "text": b.get("text", "")})
                    last_text[(d.get("turn"), d.get("step"))] = b.get("text", "")
        elif t == "step/end":
            d = ev["data"]
            u = pending.pop((d.get("turn"), d.get("step")), None)
            events.append({"type": "status", "phase": "step_end",
                           **({"usage": map_usage(u)} if u else {})})
    if last_text:
        events.append({"type": "final", "text": last_text[sorted(last_text.keys())[-1]]})
    return events


def current_postprocess(sess_dir: Path | None, raw_file: Path | None) -> dict:
    """L4 语义：staging 保留 raw；会话轨迹做 text/usage **局部投影**（非完整流，
    不同于 lab.py 完整事件重建）；逐调用 usage 实测。"""
    full_rebuild = {"status": "not_attempted", "kind": "partial_text_usage_projection",
                    "events": 0, "bytes": 0, "sha256": None, "reason": "session unavailable"}
    usage = unknown_usage("session log unavailable")
    integrity = {"lines": 0, "violations": 0, "vacuous": True,
                 "basis": "no sources", "evidence": []}
    patterns = ["2-用例", "truth.json", "checker.py", "reference/", "solution/", "../",
                "~/Documents", "harness-compare-bench"]
    if sess_dir is not None and sess_dir.is_dir() and any(sess_dir.iterdir()):
        events = _rebuild_events(sess_dir)
        payload = "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events)
        full_rebuild = {"status": "rebuilt_partial", "kind": "partial_text_usage_projection",
                        "events": len(events), "bytes": len(payload.encode("utf-8")),
                        "sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
                        "scope": "仅 text/usage（assistant/message 文本与 commit-point usage）投影；"
                                 "reasoning/tool_call/tool_result/turn 边界事件未含——**非完整流**，"
                                 "不得称 full_stream（诚实命名 per reviewer）",
                        "method": "actual re-projection of session lines (caps removed; commit-point semantics)"}
        per_call, n_lines = [], 0
        for name, line in session_lines(sess_dir):
            n_lines += 1
            try:
                ev = json.loads(line)
            except Exception:
                continue
            if ev.get("type") == "assistant/message":
                u = ev.get("data", {}).get("usage") or {}
                if isinstance(u, dict) and u:
                    per_call.append({"turn": ev["data"].get("turn"), "step": ev["data"].get("step"),
                                     **map_usage(u)})

        def total(f):
            vals = [c.get(f) for c in per_call if isinstance(c.get(f), int)]
            return sum(vals) if vals else None

        usage = {"status": "measured", "reason": None,
                 "requests": len(per_call),
                 "input_tokens": total("input_tokens"), "output_tokens": total("output_tokens"),
                 "cache_read_tokens": total("cache_read_tokens"),
                 "cache_creation_tokens": total("cache_creation_tokens"),
                 "per_call": per_call,
                 "source": "session assistant/message usage (commit points); 缺失保留 null"}
        sources = []
        if raw_file is not None and raw_file.is_file():
            sources += [("agent.jsonl", l) for l in
                        raw_file.read_text(encoding="utf-8", errors="replace").splitlines()]
        sources += [("session:" + name, l) for name, l in session_lines(sess_dir)]
        hits, n = [], 0
        for name, line in sources:
            n += 1
            for pat in patterns:
                if pat in line:
                    hits.append({"file": name, "line": n, "pattern": pat})
                    break
        integrity = {"lines": n, "violations": len(hits), "vacuous": n == 0,
                     "basis": "raw stdout + session trajectory dual scan (actual lines)",
                     "evidence": hits[:20]}
    return {"raw_stdout": {"status": "preserved" if raw_file is not None and raw_file.is_file() else "absent",
                           "bytes": raw_file.stat().st_size if raw_file is not None and raw_file.is_file() else None,
                           "sha256": hashlib.sha256(raw_file.read_bytes()).hexdigest()
                           if raw_file is not None and raw_file.is_file() else None},
            "partial_text_usage_projection": full_rebuild,
            "integrity": integrity,
            "usage": usage,
            "score": {"status": "not_evaluated",
                      "reason": "replay harness 不运行 checker；不声称分数等值/不变",
                      "unknown": {"impact": "分数反事实不在本 harness 范围",
                                  "next_step": "同 legacy 条目",
                                  "stop_condition": "不宣称分数不变"}}}


def replay(run_dir: Path, case: str, work_root: Path) -> dict:
    master = Path(run_dir)
    master_before = sha_dir_state(master)
    sess_src = master / "agent-session"
    raw_src = master / "agent.jsonl"

    # --- legacy 副本：日志写入输出目录 → 顶部 rmtree（r1030#1 在副本内复现）---
    legacy = work_root / "legacy"
    (legacy / "archive").mkdir(parents=True)
    if raw_src.is_file():
        shutil.copy2(raw_src, legacy / "archive" / "agent.jsonl")
    shutil.rmtree(legacy / "archive")  # r1030#1：archive() 顶部 rmtree 先于日志移动
    (legacy / "archive").mkdir()
    legacy_lost = not (legacy / "archive" / "agent.jsonl").exists()
    legacy_out = legacy_postprocess()

    # --- current 副本：staging 先行，母本不动 ---
    current = work_root / "current"
    staging = current / "staging"
    staging.mkdir(parents=True)
    cur_out = current / "archive"
    cur_out.mkdir(parents=True)
    if raw_src.is_file():
        shutil.copy2(raw_src, staging / "agent.jsonl")
        shutil.copy2(staging / "agent.jsonl", cur_out / "agent.jsonl")
    if sess_src.is_dir():
        shutil.copytree(sess_src, cur_out / "agent-session")
    cur = current_postprocess(cur_out / "agent-session" if (cur_out / "agent-session").is_dir() else None,
                              cur_out / "agent.jsonl")

    master_after = sha_dir_state(master)
    diffs = [
        {"dimension": "raw_stdout_preserved", "legacy": not legacy_lost,
         "current": cur["raw_stdout"]["status"] == "preserved",
         "interpretation": "r1030#1 在 legacy 副本内复现" if legacy_lost else "无差异"},
        {"dimension": "partial_text_usage_projection", "legacy": "not_attempted",
         "current": cur["partial_text_usage_projection"]["status"] + (
             "(%d events / %d bytes)" % (cur["partial_text_usage_projection"]["events"],
                                         cur["partial_text_usage_projection"]["bytes"])
             if cur["partial_text_usage_projection"]["status"] == "rebuilt_partial" else ""),
         "interpretation": "current 侧为部分投影（text/usage），非完整流；legacy 无任何重建；"
                           "截断字段不可恢复"},
        {"dimension": "integrity_basis", "legacy": "vacuous(lost source)",
         "current": "%d lines scanned" % cur["integrity"]["lines"],
         "interpretation": "vacuous 无判定力 ≠ 无违规（unknown 保留）"},
        {"dimension": "usage_projection", "legacy": legacy_out["usage"]["status"],
         "current": cur["usage"]["status"],
         "interpretation": "legacy usage 不可判定（源已丢）；current 实测。差异=测量语义差，非服务端事实差"},
        {"dimension": "score", "legacy": "not_evaluated", "current": "not_evaluated",
         "interpretation": "harness 未运行 checker——不作任何分数等值/不变声称（S6-3）"},
    ]
    return {"kind": "dual_archive_replay", "spec": SPEC, "case": case, "at": now_iso(),
            "equivalent_simulation": True,
            "adaptation_disclosure": "两副本均为等价模拟：legacy 以相同 rmtree 顺序复现 r1030#1，"
                                     "其后处理按'读已丢失日志'的旧语义推演（usage/integrity unknown，不从会话补造）；"
                                     "current 侧为 staging 保留+text/usage 局部投影（非完整流）+实测扫描。未原样调用历史 pipeline，"
                                     "推断边界=归档语义级而非进程级；分数维度双侧 not_evaluated。",
            "master": {"path": str(master), "state_before": master_before,
                       "state_after": master_after, "untouched": master_before == master_after},
            "sandbox": {"legacy": {"root": str(legacy), "raw_stdout_lost": legacy_lost,
                                   "postprocess": legacy_out},
                        "current": {"root": str(current), "postprocess": cur}},
            "differences": diffs,
            "unknowns": [
                {"item": "legacy usage（源丢失）", "impact": "不可判定",
                 "next_step": "以 current 投影为参照披露", "stop_condition": "不补造"},
                {"item": "双侧 score 反事实", "impact": "分数等值性不可判",
                 "next_step": "须真实重跑 checker 的另行设计", "stop_condition": "不宣称分数不变"},
            ],
            "live_doc_drift": []}


# ---------------------------------------------------------------- 合成自测

def selftest() -> int:
    cases = []
    with tempfile.TemporaryDirectory(prefix="l4dual-") as td:
        tmp = Path(td)
        run = tmp / "master" / "runs" / "synthetic-r1"
        (run / "agent-session").mkdir(parents=True)
        sess_lines = [
            {"type": "session", "id": "syn-1"},
            {"type": "step/start", "data": {"turn": 1, "step": 1}},
            {"type": "assistant/message", "data": {"turn": 1, "step": 1,
                                                  "message": {"content": [{"type": "text", "text": "hello " * 5000}]},
                                                  "usage": {"inputTokens": 100, "outputTokens": 10,
                                                            "cacheReadTokens": 90, "cacheWriteTokens": 5}}},
            {"type": "tool/call", "data": {"callId": "c1", "name": "read", "arguments": "{}"}},
            {"type": "tool/result", "data": {"message": {"toolCallId": "c1", "content": []}}},
            {"type": "step/end", "data": {"turn": 1, "step": 1}},
            {"type": "turn/end", "data": {"turn": 1, "reason": {"kind": "end_turn"}}},
        ]
        for ev in sess_lines:
            with (run / "agent-session" / "s.jsonl").open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
        (run / "agent.jsonl").write_text(json.dumps(
            {"type": "text", "text": "truncated " * 2000})[:8192] + "\n", encoding="utf-8")
        (run / "workspace").mkdir()
        (run / "workspace" / "out.txt").write_text("w", encoding="utf-8")
        rep = replay(run, "synthetic-case", tmp / "work")
        leg = rep["sandbox"]["legacy"]["postprocess"]
        cur = rep["sandbox"]["current"]["postprocess"]
        cases.append({"case": "master-untouched", "pass": rep["master"]["untouched"]})
        cases.append({"case": "legacy-raw-lost", "pass": rep["sandbox"]["legacy"]["raw_stdout_lost"]})
        cases.append({"case": "legacy-usage-unknown-not-fabricated",
                      "pass": leg["usage"]["status"] == "unknown"
                      and leg["usage"]["requests"] is None
                      and leg["usage"]["per_call"] is None})
        cases.append({"case": "legacy-integrity-vacuous", "pass": leg["integrity"]["vacuous"]})
        cases.append({"case": "current-partial-projection-honest",
                      "pass": cur["partial_text_usage_projection"]["status"] == "rebuilt_partial"
                      and cur["partial_text_usage_projection"]["kind"] == "partial_text_usage_projection"
                      and cur["partial_text_usage_projection"]["events"] > 0
                      and cur["partial_text_usage_projection"]["bytes"] > 0
                      and len(cur["partial_text_usage_projection"]["sha256"]) == 64
                      and "非完整流" in cur["partial_text_usage_projection"]["scope"]})
        cases.append({"case": "current-usage-measured",
                      "pass": cur["usage"]["status"] == "measured"
                      and cur["usage"]["requests"] == 1
                      and cur["usage"]["cache_read_tokens"] == 90})
        cases.append({"case": "current-integrity-actually-scanned",
                      "pass": cur["integrity"]["lines"] > 0})
        diffs_blob = json.dumps(rep["differences"], ensure_ascii=False)
        cases.append({"case": "no-score-equality-claims",
                      "pass": leg["score"]["status"] == "not_evaluated"
                      and cur["score"]["status"] == "not_evaluated"
                      and "分数不变" not in diffs_blob
                      and "score unchanged" not in diffs_blob})
        cases.append({"case": "equivalent-sim-flagged", "pass": rep["equivalent_simulation"] is True})
        out = tmp / "report.json"
        out.write_text(json.dumps(rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        cases.append({"case": "report-writable", "pass": out.is_file()})
    counts = {"total": len(cases), "passed": sum(1 for c in cases if c["pass"]),
              "failed": sum(1 for c in cases if not c["pass"])}
    receipt = {"kind": "self_test", "tool": "replay_dual.py", "spec": SPEC,
               "at": now_iso(), "counts": counts, "cases": cases,
               "zero_model": True, "live_doc_drift": []}
    base = HERE / "selftest-replay-dual.json"
    n = 1
    while base.exists():
        n += 1
        base = HERE / ("selftest-replay-dual-r%d.json" % n)
    base.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(counts, ensure_ascii=False), "→", base)
    return 0 if counts["failed"] == 0 else 1


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run")
    ap.add_argument("--case", default="unknown-case")
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.run:
        ap.print_help()
        return 2
    with tempfile.TemporaryDirectory(prefix="l4dual-run-") as td:
        rep = replay(Path(a.run), a.case, Path(td))
    body = json.dumps(rep, ensure_ascii=False, indent=2) + "\n"
    print(json.dumps({"equivalent_simulation": True,
                      "master_untouched": rep["master"]["untouched"],
                      "legacy_raw_lost": rep["sandbox"]["legacy"]["raw_stdout_lost"],
                      "current_projection": rep["sandbox"]["current"]["postprocess"]["partial_text_usage_projection"]["status"],
                      "legacy_usage": rep["sandbox"]["legacy"]["postprocess"]["usage"]["status"],
                      "score": "not_evaluated(both sides)"},
                     ensure_ascii=False))
    if a.out:
        p = Path(a.out)
        if p.exists() or p.is_symlink():
            print("拒绝写入：已存在 %s" % p, file=sys.stderr)
            return 2
        p.write_text(body, encoding="utf-8")
        print("REPORT:", p)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
