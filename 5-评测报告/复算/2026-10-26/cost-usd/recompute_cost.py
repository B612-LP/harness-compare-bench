#!/usr/bin/env python3
"""cost-usd 复算：A 组（CLI×deepseek-flash）每场 token → 官方价目 USD。

只读仓内既有证据（运行总账 JSON、3-表现现场/*/agent.jsonl、meta.json），
不修改任何既有文件；输出写在本目录（cost_table.csv / cost_details.json）。
不联网；费率由调用方保证与 prices.json 一致（2026-10-26 抓自官方价目页）。

口径（沿用 复算/token-recompute.py 已核实的两套字段语义）：
  codex（usage 为单条 turn.completed，全场累计）：
    总输入 = input_tokens（含缓存命中）；命中 = cached_input_tokens（子集）；
    未命中 = input_tokens − cached_input_tokens；输出 = output_tokens
    （reasoning_output_tokens 为输出子集，不重复计费）。
  dsh（agent.jsonl 每次调用的 status.usage，须逐调用求和）：
    未命中 = Σ inputTokens；命中 = Σ cacheReadTokens；输出 = Σ outputTokens
    （meta.usage 只是最后一次调用的快照，不得当全场累计用）。

峰谷：DeepSeek 官方价目分高峰/空闲两档（北京时间周一至周五 9:00–12:00、
14:00–18:00 为高峰，其余含周末节假日为空闲）。轨迹未存逐调用时间戳，
按 meta.started_at + duration_s 判定每场所在时段；本批 44 场均不跨档。

用法：python3 recompute_cost.py            # 写 CSV/JSON 并打印汇总
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timedelta, time as dtime
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
LEDGER = REPO / "5-评测报告" / "运行总账-2026-10-24.json"
SITE = REPO / "3-表现现场"

# DeepSeek 官方 USD 价目（deepseek-flash = DeepSeek-V4.1-Flash-1017），
# 2026-10-26 抓自 https://api-docs.deepseek.com/quick_start/pricing/（见 prices.json）
RATES = {  # USD per 1M tokens: regime -> {hit, miss, out}
    "off-peak": {"hit": 0.003, "miss": 0.15, "out": 0.6},
    "peak": {"hit": 0.006, "miss": 0.30, "out": 1.2},
}

A_RUN_DIRS = (
    [f"r1023-cli-dsf-low/{c}__{a}" for c in
     ["corpus-squeeze", "int-sum-sort", "jielong-fullchain", "ledger-replay", "word-freq-report"]
     for a in ("codex", "dsh")]
    + [f"r1024-probe-区分度/{c}__{a}" for c in
       ["bird-schools15", "dabstep-dev10", "lcb-hard3", "lcb-v6-hard4", "polyglot-py3"]
       for a in ("codex", "dsh")]
    + [f"r1025-candidates/{c}__{a}" for c in
       ["bird-ca-schools-15", "dabstep-payments-10", "exercism-py-6", "lcb-recent-hard-4", "tb-cargo-plan"]
       for a in ("codex", "dsh")]
    + ["r1027-isolated/runs/codex__tb-cargo-plan", "r1027-isolated/runs/dsh__dabstep-payments-10"]
    + [f"r1028-repeats/runs/{a}__{c}__{r}"
       for a in ("codex", "dsh")
       for c in ("bird-ca-schools-15", "dabstep-payments-10", "tb-cargo-plan")
       for r in ("r2", "r3")]
)


def peak_windows() -> list[tuple[dtime, dtime]]:
    return [(dtime(9, 0), dtime(12, 0)), (dtime(14, 0), dtime(18, 0))]


def is_peak(dt: datetime) -> bool:
    # 2026-10-22(周四)/10-23(周五)均为中国工作日、非法定节假日
    return dt.weekday() < 5 and any(a <= dt.time() < b for a, b in peak_windows())


def classify(start: datetime, dur_s: float) -> str:
    end = start + timedelta(seconds=dur_s)
    p_start, p_end = is_peak(start), is_peak(end - timedelta(microseconds=1))
    if p_start and p_end:
        return "peak"
    if not p_start and not p_end:
        return "off-peak"
    return "mixed"


def extract_codex(agent_jsonl: Path) -> dict:
    """codex：取最后一条 turn.completed 的 usage（全场累计）。"""
    usage = None
    for line in agent_jsonl.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("type") == "turn.completed" and isinstance(e.get("usage"), dict):
            usage = e["usage"]
    if usage is None:
        raise ValueError("no turn.completed usage")
    total_in = usage["input_tokens"]
    hit = usage.get("cached_input_tokens", 0) or 0
    return {
        "hit": hit, "miss": total_in - hit,
        "out": usage["output_tokens"],
        "reasoning": usage.get("reasoning_output_tokens", 0) or 0,
        "calls": 1, "raw": usage,
    }


def extract_dsh(agent_jsonl: Path) -> dict:
    """dsh：逐调用求和 status.usage（inputTokens=未命中，cacheReadTokens=命中）。"""
    hit = miss = out = n = 0
    bad_identity = 0
    raw_last = None
    for line in agent_jsonl.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        u = e.get("usage") or (e.get("message") or {}).get("usage")
        if isinstance(u, dict) and "inputTokens" in u:
            n += 1
            m = u.get("inputTokens", 0) or 0
            h = u.get("cacheReadTokens", 0) or 0
            o = u.get("outputTokens", 0) or 0
            w = u.get("cacheWriteTokens", 0) or 0
            miss += m
            hit += h
            out += o
            if u.get("totalTokens") not in (None, m + h + o + w):
                bad_identity += 1
            raw_last = u
    if n == 0:
        raise ValueError("no per-call usage events")
    return {"hit": hit, "miss": miss, "out": out, "reasoning": None,
            "calls": n, "identity_violations": bad_identity, "raw_last": raw_last}


def cost(tok: dict, regime: str) -> float:
    r = RATES[regime]
    return (tok["miss"] / 1e6 * r["miss"] + tok["hit"] / 1e6 * r["hit"]
            + tok["out"] / 1e6 * r["out"])


def main() -> int:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    led_by_id = {r["run_id"]: r for r in ledger["runs"]}

    rows, fails = [], []
    for rel in A_RUN_DIRS:
        run_dir = SITE / rel
        meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
        agent = meta.get("agent") or rel.rsplit("/", 1)[-1].split("__", 1)[0]
        harness = "codex" if agent == "codex" else ("dsh" if agent == "dsh" else None)
        if harness is None:
            fails.append(f"{rel}: 未知 agent {agent!r}")
            continue
        aj = run_dir / "agent.jsonl"
        if not aj.is_file():
            fails.append(f"{rel}: 缺 agent.jsonl")
            continue
        try:
            tok = extract_codex(aj) if harness == "codex" else extract_dsh(aj)
        except ValueError as exc:
            fails.append(f"{rel}: {exc}")
            continue

        run_id = rel if rel.startswith("r1027") or rel.startswith("r1028") else rel
        led = led_by_id.get(run_id, {})
        adjud = led.get("adjudication", "?")

        start = datetime.fromisoformat(meta["started_at"])
        dur = float(meta.get("duration_s") or 0)
        regime = classify(start, dur)

        checks = []
        led_u = (led.get("original_fields") or {}).get("usage")
        if harness == "codex" and led_u:
            checks.append("ledger_usage_match" if led_u == tok["raw"] else "LEDGER_USAGE_MISMATCH")
        if harness == "dsh" and led_u:
            checks.append("ledger_usage_is_last_call_snapshot" if led_u == tok["raw_last"]
                          else "ledger_usage_differs_from_last_call")

        row = {
            "run_id": run_id, "batch": rel.split("/")[0], "harness": harness,
            "case": meta.get("case") or rel.rsplit("__", 1)[0].split("/", -1)[-1].replace(f"{harness}__", "").split("/")[-1],
            "model": meta.get("model"), "reasoning_effort": meta.get("reasoning_effort"),
            "adjudication": adjud,
            "started_at": meta["started_at"], "duration_s": dur, "regime": regime,
            "input_cache_hit_tok": tok["hit"], "input_cache_miss_tok": tok["miss"],
            "output_tok": tok["out"],
            "of_which_reasoning_tok": tok["reasoning"] if tok["reasoning"] is not None else "",
            "api_calls": tok["calls"],
            "cost_usd": cost(tok, regime) if regime in RATES else "",
            "cost_usd_offpeak_bound": cost(tok, "off-peak"),
            "cost_usd_peak_bound": cost(tok, "peak"),
            "checks": ";".join(checks),
        }
        if regime == "mixed":
            fails.append(f"{rel}: 跨峰谷档，仅给界")
        rows.append(row)

    out_dir = Path(__file__).resolve().parent
    with open(out_dir / "cost_table.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    def tot(pred):
        t = {"hit": 0, "miss": 0, "out": 0, "usd": 0.0, "n": 0}
        for r in rows:
            if pred(r):
                t["hit"] += r["input_cache_hit_tok"]
                t["miss"] += r["input_cache_miss_tok"]
                t["out"] += r["output_tok"]
                t["usd"] += float(r["cost_usd"])
                t["n"] += 1
        return t

    summary = {
        "rates_used": RATES,
        "runs_total": len(rows),
        "failures": fails,
        "grand_all": tot(lambda r: True),
        "grand_V_only": tot(lambda r: r["adjudication"] == "V"),
        "by_batch": {b: tot(lambda r, b=b: r["batch"] == b) for b in sorted({r["batch"] for r in rows})},
        "by_harness": {h: tot(lambda r, h=h: r["harness"] == h) for h in ("codex", "dsh")},
        "rows": rows,
    }
    (out_dir / "cost_details.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"runs={len(rows)}  failures={len(fails)}")
    for f in fails:
        print("FAIL", f)
    for label, t in (("all", summary["grand_all"]), ("V-only", summary["grand_V_only"])):
        print(f"{label}: n={t['n']} hit={t['hit']:,} miss={t['miss']:,} out={t['out']:,} usd=${t['usd']:.4f}")
    for h in ("codex", "dsh"):
        t = summary["by_harness"][h]
        print(f"  {h}: n={t['n']} usd=${t['usd']:.4f}")
    mism = [r["run_id"] for r in rows if "MISMATCH" in str(r["checks"])]
    if mism:
        print("LEDGER MISMATCH:", mism)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
