#!/usr/bin/env python3
"""token-cause 复算：A 组（CLI×deepseek-flash）token 总量差的三因子算术分解。

只读仓内既有证据（3-表现现场 各场 agent.jsonl、meta.json）与外部消融批目录
（/Users/b612-lp/bench-automation/runs/r20261027-ablation，仅读，不动批产出），
不修改任何既有文件；输出写在本目录（per_run.json / decomposition.md）。
不联网、不 git。

口径（字段语义沿用 复算/2026-10-26/cost-usd/recompute_cost.py，逐调用来源按本批实测细化）：
  codex（真实逐调用在 agent-session/rollout-*.jsonl 的 token_count 事件）：
    payload.info.total_token_usage 为全场累计、last_token_usage 为单次；
    逐调用值 = 相邻累计的差分；call-1 前缀代理 = 第一条累计的 input_tokens；
    输入合计 = 末条累计 input（含缓存命中）；命中 = 末条 cached_input_tokens；
    未命中 = 输入合计 − 命中；输出 = 末条 output_tokens；
    reasoning = 末条 reasoning_output_tokens（输出子集）。
    顶层 agent.jsonl 只含 1 条 turn.completed（末次累计），仅用于交叉校验
    （22/22 场与 rollout 末条累计一致）；rollout 缺失时才回退它（此时
    call-1 前缀代理=全场累计输入，非真首调前缀，usage_source 字段会标注）。
  dsh（agent.jsonl 每条 status/step_end 的 status.usage，逐调用求和）：
    未命中 = Σ inputTokens；命中 = Σ cacheReadTokens；输出 = Σ outputTokens；
    call-1 前缀代理 = 第一条调用的 inputTokens。
    meta.usage 只是最后一次调用的快照，禁止当全场累计用。

分解口径（恒等式拆分，非因果证明）：对同题双 CLI（c=codex，d=dsh），
  Δtotal = total_c − total_d = [结构×编排] + [余项]
  其中 结构×编排 = (prefix_c − prefix_d)×n_d + (n_c − n_d)×prefix_d（题给 counterfactual）
       余项     = Δtotal − 结构×编排 = 交叉项 + 增长差 + 输出差（精确代数）：
       交叉项 (n_c−n_d)(prefix_c−prefix_d)；增长差 G_c−G_d（G_x = input_x − prefix_x）；
       输出差 out_c − out_d。
  另给精确三因子（无交叉项）：Δtotal = (prefix_c−prefix_d) + (G_c−G_d) + (out_c−out_d)。
  「调用数」不单独成项：其效应并入 G（首调之后全部输入 = 多调用对话复利）。

用法：python3 token_decompose.py     # 写 per_run.json / decomposition.md 并打印汇总
"""
from __future__ import annotations

import json
import sys
from itertools import product
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
SITE = REPO / "3-表现现场"
ABLATION = Path("/Users/b612-lp/bench-automation/runs/r20261027-ablation")

# 与 复算/2026-10-26/cost-usd/recompute_cost.py 的 A_RUN_DIRS 逐字一致（44 场 A 组）
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

ABLATION_CASES = ("dabstep-payments-10", "tb-cargo-plan")
ABLATION_ARMS = ("codex-base", "codex-skill", "codex-gpt", "dsh-base", "dsh-skill")


def reduce_cums(cums: list[dict], source: str) -> dict:
    """累计序列 → 逐场指标（两种 codex 格式共用；单调性校验）。"""
    for a, b in zip(cums, cums[1:]):
        for k in ("input", "hit", "out", "reasoning"):
            if b[k] < a[k]:
                raise ValueError(f"cumulative {k} decreased: {a[k]} -> {b[k]}")
    last = cums[-1]
    diffs = []
    prev = {"input": 0, "hit": 0, "out": 0, "reasoning": 0}
    for c in cums:  # 第一条差分 = 第一条累计本身（call-1 即前缀代理）
        diffs.append({k: c[k] - prev[k] for k in prev})
        prev = c
    return {
        "n_calls": len(cums),
        "call1_prefix_tokens": cums[0]["input"],
        "sum_input": last["input"],
        "sum_input_hit": last["hit"],
        "sum_input_miss": last["input"] - last["hit"],
        "sum_output": last["out"],
        "sum_reasoning": last["reasoning"],
        "sum_cache_write": last["cache_write"],
        "total_tokens": last["input"] + last["out"],
        "cum_input_tokens": [c["input"] for c in cums],
        "per_call_input_diff": [d["input"] for d in diffs],
        "usage_source": source,
    }


def extract_codex(agent_jsonl: Path) -> dict:
    """codex：收集全部 turn.completed（全场累计，A 组历史运行格式）。"""
    cums = []
    for line in agent_jsonl.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("type") == "turn.completed" and isinstance(e.get("usage"), dict):
            u = e["usage"]
            cums.append({
                "input": u["input_tokens"],
                "hit": u.get("cached_input_tokens", 0) or 0,
                "cache_write": u.get("cache_write_input_tokens", 0) or 0,
                "out": u["output_tokens"],
                "reasoning": u.get("reasoning_output_tokens", 0) or 0,
            })
    if not cums:
        raise ValueError("no turn.completed usage")
    return reduce_cums(cums, "turn.completed")


def extract_codex_rollout(rollout_jsonl: Path) -> dict:
    """codex 原生 rollout（消融批格式）：token_count 事件的 total_token_usage 为全场累计。

    last_token_usage 为单次值，用于交叉校验：total_n 应等于 total_{n-1} + last_n。
    """
    cums, lasts = [], []
    for line in rollout_jsonl.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("type") != "event_msg":
            continue
        p = e.get("payload") or {}
        if p.get("type") != "token_count":
            continue
        info = p.get("info") if isinstance(p.get("info"), dict) else p  # usage 在 payload.info 下
        tot, lst = info.get("total_token_usage"), info.get("last_token_usage")
        if not isinstance(tot, dict) or "input_tokens" not in tot:
            continue
        cums.append({
            "input": tot["input_tokens"],
            "hit": tot.get("cached_input_tokens", 0) or 0,
            "cache_write": tot.get("cache_write_input_tokens", 0) or 0,
            "out": tot["output_tokens"],
            "reasoning": tot.get("reasoning_output_tokens", 0) or 0,
        })
        if isinstance(lst, dict) and "input_tokens" in lst:
            lasts.append(lst)
    if not cums:
        raise ValueError("no token_count total_token_usage")
    # 交叉校验：累计 = 上一累计 + 单次
    for i in range(1, len(cums)):
        if cums[i]["input"] != cums[i - 1]["input"] + lasts[i]["input_tokens"]:
            raise ValueError(f"token_count #{i+1}: total != prev_total + last")
    return reduce_cums(cums, "token_count(total_token_usage)")


def extract_dsh_text(text: str, source: str) -> dict:
    """dsh：逐调用求和 status.usage（inputTokens=未命中，cacheReadTokens=命中）。

    兼容两种容器：旧 agent.jsonl（usage 在事件顶层）与 session.v4
    （usage 在 assistant/message 的 data.usage）；两者字段语义一致。
    """
    per_call = []
    for line in text.splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        u = (e.get("usage") or (e.get("message") or {}).get("usage")
             or (e.get("data") or {}).get("usage"))
        if isinstance(u, dict) and "inputTokens" in u:
            per_call.append({
                "miss": u.get("inputTokens", 0) or 0,
                "hit": u.get("cacheReadTokens", 0) or 0,
                "out": u.get("outputTokens", 0) or 0,
                "cache_write": u.get("cacheWriteTokens", 0) or 0,
            })
    if not per_call:
        raise ValueError("no per-call usage events")
    s = {k: sum(c[k] for c in per_call) for k in ("miss", "hit", "out", "cache_write")}
    return {
        "n_calls": len(per_call),
        "call1_prefix_tokens": per_call[0]["miss"] + per_call[0]["hit"],
        "sum_input": s["miss"] + s["hit"],
        "sum_input_hit": s["hit"],
        "sum_input_miss": s["miss"],
        "sum_output": s["out"],
        "sum_reasoning": None,  # dsh 轨迹无 reasoning 拆分
        "sum_cache_write": s["cache_write"],
        "total_tokens": s["miss"] + s["hit"] + s["out"],
        "per_call_input_tokens": [c["miss"] + c["hit"] for c in per_call],
        "usage_source": source,
    }


def extract_dsh(agent_jsonl: Path) -> dict:
    return extract_dsh_text(agent_jsonl.read_text(encoding="utf-8"),
                            "status.step_end.usage(per_call)")


def parse_session(run_dir: Path, harness: str) -> dict:
    """按 harness 选文件并解析。

    codex：优先 agent-session/rollout-*.jsonl 的 token_count（真实逐调用，全场累计），
    并用顶层 agent.jsonl 的 turn.completed（末次累计）做交叉校验；
    rollout 缺失时才回退 agent.jsonl（此时前缀代理=全场累计输入，非真首调前缀，见 README）。
    dsh：run_dir/agent.jsonl → agent-session/agent.jsonl。
    """
    asj = run_dir / "agent-session"
    if harness == "codex":
        aj = run_dir / "agent.jsonl"
        tc_final = None
        if aj.is_file():
            for line in aj.read_text(encoding="utf-8").splitlines():
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if e.get("type") == "turn.completed" and isinstance(e.get("usage"), dict):
                    tc_final = e["usage"]
        for f in sorted(asj.glob("*.jsonl")) if asj.is_dir() else []:
            text = f.read_text(encoding="utf-8")
            if '"token_count"' not in text:
                continue
            tok = extract_codex_rollout(f)
            if tc_final is None:
                tok["cross_check_turn_completed"] = "absent"
            else:
                ok = (tc_final.get("input_tokens") == tok["sum_input"]
                      and tc_final.get("output_tokens") == tok["sum_output"])
                tok["cross_check_turn_completed"] = ("match" if ok else
                                                     f"MISMATCH(tc_input={tc_final.get('input_tokens')})")
            return tok
        if aj.is_file():
            return extract_codex(aj)  # 回退：仅末次累计，无逐调用（usage_source 已标注）
        raise ValueError("无 rollout 且无 agent.jsonl")
    for f in (run_dir / "agent.jsonl", asj / "agent.jsonl"):
        if f.is_file():
            return extract_dsh(f)
    # v4 压缩会话（消融批 dsh 臂）：usage 在 assistant/message 的 data.usage，内存解压、不落盘
    zst = asj / "session.v4.jsonl.zstd"
    if zst.is_file():
        try:
            import zstandard
        except ImportError as exc:
            raise ValueError(f"需 zstandard 库解压 {zst.name}（pip install zstandard）") from exc
        with zstandard.ZstdDecompressor().stream_reader(open(zst, "rb")) as r:
            text = r.read().decode("utf-8")
        return extract_dsh_text(text, "session.v4(data.usage, zstd 解压)")
    raise ValueError("缺 agent.jsonl 且 agent-session/ 无 agent.jsonl 或 session.v4.jsonl.zstd")


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0


def decompose(pc: dict, pd: dict) -> dict:
    """双 CLI 同题对：总量差 → 结构×编排 + 余项（恒等式），余项再精确拆三块。"""
    n_c, n_d = pc["n_calls"], pd["n_calls"]
    p_c, p_d = pc["call1_prefix_tokens"], pd["call1_prefix_tokens"]
    d_total = pc["total_tokens"] - pd["total_tokens"]
    structure = (p_c - p_d) * n_d + (n_c - n_d) * p_d
    residual = d_total - structure
    cross = (n_c - n_d) * (p_c - p_d)
    growth_c = pc["sum_input"] - n_c * p_c
    growth_d = pd["sum_input"] - n_d * p_d
    return {
        "delta_total": d_total,
        "structure_x_orchestration": structure,
        "residual_growth_plus_output": residual,
        "residual_cross_term": cross,
        "residual_growth_codex": growth_c,
        "residual_growth_dsh": -growth_d,
        "residual_output_diff": pc["sum_output"] - pd["sum_output"],
    }


def decompose_exact3(pc: dict, pd: dict) -> dict:
    """精确三因子拆分（任意调用数下均精确，无交叉项）：

    total_x = prefix_x + G_x + out_x，G_x = input_x − prefix_x（首调之后全部输入：
    多调用的对话复利 + 新增轮次）。于是
      Δtotal = (prefix_c − prefix_d) + (G_c − G_d) + (out_c − out_d)
    三块相加恰等于 Δtotal；「调用数」不单独成项，其效应并入 G（增长差）。
    """
    prefix_diff = pc["call1_prefix_tokens"] - pd["call1_prefix_tokens"]
    growth_diff = ((pc["sum_input"] - pc["call1_prefix_tokens"])
                   - (pd["sum_input"] - pd["call1_prefix_tokens"]))
    output_diff = pc["sum_output"] - pd["sum_output"]
    assert prefix_diff + growth_diff + output_diff == pc["total_tokens"] - pd["total_tokens"]
    return {"prefix_diff": prefix_diff, "conversation_growth_diff": growth_diff,
            "output_diff": output_diff}


def fmt(x) -> str:
    return f"{x:,}" if isinstance(x, int) else str(x)


def main() -> int:
    fails = []
    runs = []

    # ── 1) A 组 44 场历史运行 ──────────────────────────────────────────────
    for rel in A_RUN_DIRS:
        run_dir = SITE / rel
        try:
            meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
            agent = meta.get("agent") or rel.rsplit("/", 1)[-1].split("__", 1)[0]
            harness = "codex" if agent == "codex" else ("dsh" if agent == "dsh" else None)
            if harness is None:
                raise ValueError(f"未知 agent {agent!r}")
            tok = parse_session(run_dir, harness)
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            fails.append(f"{rel}: {exc}")
            continue
        runs.append({
            "run": rel,
            "batch": rel.split("/")[0],
            "harness": harness,
            "case": meta.get("case"),
            "model": meta.get("model"),
            "n_calls": tok["n_calls"],
            "call1_prefix_tokens": tok["call1_prefix_tokens"],
            "sum_input_miss": tok["sum_input_miss"],
            "sum_input_hit": tok["sum_input_hit"],
            "sum_input": tok["sum_input"],
            "sum_output": tok["sum_output"],
            "sum_reasoning": tok["sum_reasoning"],
            "total_tokens": tok["total_tokens"],
            "sum_cache_write": tok["sum_cache_write"],
            "per_call_input": tok.get("cum_input_tokens") or tok.get("per_call_input_tokens"),
            # codex 该数组是累计值（差分得逐调用），dsh 是逐调用值本身
            "per_call_input_semantic": ("cumulative_turn.completed" if harness == "codex"
                                        else "per_call_step_end"),
            "usage_source": tok["usage_source"],
            "cross_check_turn_completed": tok.get("cross_check_turn_completed"),
        })

    # ── 2) 消融批（部分可能还在跑：只处理已有 result.json 的格） ────────────
    ablation_cells, ablation_missing = [], []
    for case, arm in product(ABLATION_CASES, ABLATION_ARMS):
        cell_rel = f"{case}__{arm}"
        cell_dir = ABLATION / cell_rel
        cell = {"cell": cell_rel, "case": case, "arm": arm,
                "dir_exists": cell_dir.is_dir(),
                "has_result_json": (cell_dir / "result.json").is_file()}
        base = {"codex": arm.startswith("codex"), "dsh": arm.startswith("dsh")}
        harness = "codex" if base["codex"] else "dsh"
        if cell["has_result_json"]:
            try:
                tok = parse_session(cell_dir, harness)
                cell.update({k: tok[k] for k in (
                    "n_calls", "call1_prefix_tokens", "sum_input_miss", "sum_input_hit",
                    "sum_input", "sum_output", "sum_reasoning", "total_tokens")})
                cell["usage_source"] = tok["usage_source"]
                try:
                    rj = json.loads((cell_dir / "result.json").read_text(encoding="utf-8"))
                    cell["result_status"] = rj.get("status")
                    cell["reward"] = rj.get("reward")
                except (OSError, json.JSONDecodeError):
                    pass
            except (OSError, ValueError, KeyError) as exc:
                cell["error"] = str(exc)
                ablation_missing.append(f"{cell_rel}: 有 result.json 但轨迹解析失败（{exc}），待补算")
        else:
            ablation_missing.append(f"{cell_rel}: 批未完成，待补算（无 result.json）")
        ablation_cells.append(cell)

    out_dir = Path(__file__).resolve().parent

    # ── 3) per_run.json ───────────────────────────────────────────────────
    per_run = {
        "说明": "token-cause 逐场明细；A 组 44 场 + 消融批。字段口径见 README.md。",
        "a_group_runs": runs,
        "ablation_cells": ablation_cells,
        "ablation_missing": ablation_missing,
        "failures": fails,
    }
    (out_dir / "per_run.json").write_text(
        json.dumps(per_run, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 4) 汇总与分解 ─────────────────────────────────────────────────────
    by = {}
    for r in runs:
        by.setdefault((r["batch"], r["harness"]), []).append(r)
    core = "r1025-candidates"

    import re as _re

    def rep_tag(run: str) -> str:
        """重复轮次标签（r1028 形如 ...__r2/__r3）；配对时同轮次才可比。"""
        m = _re.search(r"__r(\d+)$", run)
        return f"r{m.group(1)}" if m else ""

    pairs = []  # (batch, case, codex_row, dsh_row)
    for r in runs:
        if r["harness"] != "codex":
            continue
        key = (r["batch"], r["case"], rep_tag(r["run"]))
        twin = [d for d in runs if d["harness"] == "dsh"
                and (d["batch"], d["case"], rep_tag(d["run"])) == key]
        if twin:
            pairs.append((r["batch"], r["case"], r, twin[0]))
    unpaired = [r["run"] for r in runs if r["harness"] == "codex"
                and (r["batch"], r["case"], rep_tag(r["run"])) not in
                {(b, c, rep_tag(p["run"])) for b, c, p, _ in pairs}]

    def agg(rs):
        return {
            "n": len(rs),
            "prefix_mean": round(mean(r["call1_prefix_tokens"] for r in rs)),
            "ncalls_mean": round(mean(r["n_calls"] for r in rs), 1),
            "total_sum": sum(r["total_tokens"] for r in rs),
            "total_mean": round(mean(r["total_tokens"] for r in rs)),
            "input_sum": sum(r["sum_input"] for r in rs),
            "out_sum": sum(r["sum_output"] for r in rs),
        }

    codex_all = agg([r for r in runs if r["harness"] == "codex"])
    dsh_all = agg([r for r in runs if r["harness"] == "dsh"])

    # 逐批配对分解（r1027 两场不同题，无配对，单列说明）
    batch_order = []
    for b, _ in by:
        if b not in batch_order:
            batch_order.append(b)

    md = []
    md.append("# token-cause：A 组两 CLI token 总量差的三因子算术分解（2026-10-27）\n")
    md.append("数据源：`per_run.json`（本目录，`token_decompose.py` 生成）。"
              "所有数字为对逐场会话轨迹（codex：agent-session rollout；dsh：agent.jsonl）"
              "解析的算术结果；分解是**恒等式拆分，不是因果证明**。\n")
    md.append(f"- 解析成功 **{len(runs)}/44** 场" + (f"，失败 {len(fails)} 场" if fails else "") + "。\n")

    md.append("## 1. A 组核心 5 题（r1025-candidates）双 CLI 对照\n")
    md.append("| case | harness | run（per_run.json 键） | call1_prefix | n_calls | 总量 total | 总输入 | 输出 |")
    md.append("|---|---|---|---:|---:|---:|---:|---:|")
    core_pairs = [(c, p, d) for b, c, p, d in pairs if b == core]
    for case, p, d in core_pairs:
        for r in (p, d):
            md.append(f"| {case} | {r['harness']} | `{r['run']}` | {fmt(r['call1_prefix_tokens'])} "
                      f"| {r['n_calls']} | {fmt(r['total_tokens'])} | {fmt(r['sum_input'])} "
                      f"| {fmt(r['sum_output'])} |")
    cp, dp = agg([p for _, p, _ in core_pairs]), agg([d for _, _, d in core_pairs])
    md.append(f"| **5 题合计/均值** | codex | `r1025-candidates/*__codex` | {fmt(cp['prefix_mean'])}（均值） "
              f"| {cp['ncalls_mean']} | {fmt(cp['total_sum'])} | {fmt(cp['input_sum'])} | {fmt(cp['out_sum'])} |")
    md.append(f"| **5 题合计/均值** | dsh | `r1025-candidates/*__dsh` | {fmt(dp['prefix_mean'])}（均值） "
              f"| {dp['ncalls_mean']} | {fmt(dp['total_sum'])} | {fmt(dp['input_sum'])} | {fmt(dp['out_sum'])} |")
    md.append(f"\n5 题总量比 codex/dsh = **{cp['total_sum']/dp['total_sum']:.2f}×**；"
              f"call-1 前缀均值比 = {cp['prefix_mean']/dp['prefix_mean']:.2f}×；"
              f"调用数均值 codex={cp['ncalls_mean']} vs dsh={dp['ncalls_mean']}。\n")

    md.append("## 2. 全 44 场按批汇总（均值/合计，溯源见 per_run.json 的 batch 键）\n")
    md.append("| batch | harness | 场数 | call1_prefix 均值 | n_calls 均值 | total 均值 | total 合计 |")
    md.append("|---|---|---:|---:|---:|---:|---:|")
    for b in batch_order:
        for h in ("codex", "dsh"):
            rs = by.get((b, h))
            if not rs:
                continue
            a = agg(rs)
            md.append(f"| {b} | {h} | {a['n']} | {fmt(a['prefix_mean'])} | {a['ncalls_mean']} "
                      f"| {fmt(a['total_mean'])} | {fmt(a['total_sum'])} |")
    md.append(f"| **全部** | codex | {codex_all['n']} | {fmt(codex_all['prefix_mean'])} "
              f"| {codex_all['ncalls_mean']} | {fmt(codex_all['total_mean'])} | {fmt(codex_all['total_sum'])} |")
    md.append(f"| **全部** | dsh | {dsh_all['n']} | {fmt(dsh_all['prefix_mean'])} "
              f"| {dsh_all['ncalls_mean']} | {fmt(dsh_all['total_mean'])} | {fmt(dsh_all['total_sum'])} |")
    md.append(f"\n44 场合计总量比 codex/dsh = **{codex_all['total_sum']/dsh_all['total_sum']:.2f}×**。\n")

    md.append("## 3. 总量差因子分解（恒等式拆分，c=codex、d=dsh，逐题配对）\n")
    md.append("定义：`Δtotal = total_c − total_d`；"
              "`结构×编排 = (prefix_c−prefix_d)×n_d + (n_c−n_d)×prefix_d`；"
              "`余项 = Δtotal − 结构×编排`（= 交叉项 + 对话增长 + 输出差，见下）。"
              "**这是代数恒等式，不是因果证明。**\n")

    def decomp_table(sel, title):
        rows = [(b, c, p, d, decompose(p, d)) for b, c, p, d in pairs if sel(b)]
        if not rows:
            return
        md.append(f"### {title}\n")
        md.append("| case | Δtotal | 结构×编排 | 余项 | ├ 交叉项 | ├ 对话增长(c−d) | ├ 输出差(c−d) | runs |")
        md.append("|---|---:|---:|---:|---:|---:|---:|---|")
        t = {"d": 0, "s": 0, "r": 0, "x": 0, "g": 0, "o": 0}
        for b, case, p, d, dec in rows:
            g = dec["residual_growth_codex"] + dec["residual_growth_dsh"]
            md.append(f"| {case} | {fmt(dec['delta_total'])} | {fmt(dec['structure_x_orchestration'])} "
                      f"| {fmt(dec['residual_growth_plus_output'])} | {fmt(dec['residual_cross_term'])} "
                      f"| {fmt(g)} | {fmt(dec['residual_output_diff'])} "
                      f"| `{p['run']}`+`{d['run']}` |")
            for k, v in (("d", dec["delta_total"]), ("s", dec["structure_x_orchestration"]),
                         ("r", dec["residual_growth_plus_output"]), ("x", dec["residual_cross_term"]),
                         ("g", g), ("o", dec["residual_output_diff"])):
                t[k] += v
        n = len(rows)
        md.append(f"| **合计({n} 对)** | {fmt(t['d'])} | {fmt(t['s'])} | {fmt(t['r'])} "
                  f"| {fmt(t['x'])} | {fmt(t['g'])} | {fmt(t['o'])} | — |")
        if t["d"]:
            md.append(f"\n占比（对 Δtotal={fmt(t['d'])}）：结构×编排 **{t['s']/t['d']*100:.0f}%**，"
                      f"余项 **{t['r']/t['d']*100:.0f}%**"
                      f"（交叉项 {t['x']/t['d']*100:.0f}%、对话增长 {t['g']/t['d']*100:.0f}%、"
                      f"输出差 {t['o']/t['d']*100:.0f}%；四块相加=100%，符号可负）。\n")

    decomp_table(lambda b: b == core, "r1025-candidates（A 组核心 5 题）")
    decomp_table(lambda b: b in ("r1023-cli-dsf-low", "r1024-probe-区分度"), "r1023 + r1024（各 5 题）")
    decomp_table(lambda b: b == "r1028-repeats", "r1028-repeats（3 题 × r2/r3）")
    md.append("注：同题配对键 = (batch, case, 重复轮次)；"
              + (f"未配对场（不进分解表，仅入 per_run.json）：{'、'.join(f'`{u}`' for u in unpaired)}。"
                 if unpaired else "全部 codex 场均有配对。") + "\n")
    n_match = sum(1 for r in runs if r["harness"] == "codex"
                  and r.get("cross_check_turn_completed") == "match")
    n_codex_runs = sum(1 for r in runs if r["harness"] == "codex")
    md.append(f"**口径说明**：A 组 codex 顶层 `agent.jsonl` 只含 1 条 `turn.completed`"
              f"（末次全场累计），真实逐调用取自 `agent-session/rollout-*.jsonl` 的 "
              f"`token_count`（`total_token_usage` 为全场累计、`last_token_usage` 为单次）；"
              f"两来源末次累计一致性 **{n_match}/{n_codex_runs} 场 match**"
              f"（字段 `cross_check_turn_completed`）。dsh 无 rollout，逐调用来自 "
              f"`agent.jsonl` 的 `status/step_end.usage`。题给两因子公式的交叉项 "
              f"`(n_c−n_d)(prefix_c−prefix_d)` 在 n_c≈n_d 时数值有限，公式可用；"
              f"解读仍推荐下表精确三因子。\n")

    # ── 精确三因子（total = prefix + G + out 对两侧恒成立，无交叉项） ──
    md.append("### 3-sup. 精确三因子拆分（三块相加恰等于 Δtotal）\n")
    md.append("对任一会话 `total = prefix + G + out`（G = 输入合计 − call-1 前缀，"
              "即首调之后的全部输入：多调用对话复利 + 新增轮次）。于是 "
              "`Δtotal = (prefix_c−prefix_d) + (G_c−G_d) + (out_c−out_d)` 恒等成立。"
              "「调用数」不单独成项：其效应并入增长差 G。②为负 = dsh 增长更快（抵消 codex 前缀差）。\n")
    md.append("| 范围 | Δtotal | ① call-1 前缀差 | ② 对话增长差(c−d) | ③ 输出差 | 占比 ①/②/③ |")
    md.append("|---|---:|---:|---:|---:|---|")

    def exact3_rows(sel):
        return [(b, c, p, d, decompose_exact3(p, d)) for b, c, p, d in pairs if sel(b)]

    def exact3_line(label, rows):
        s = {k: sum(r[k] for *_, r in rows) for k in
             ("prefix_diff", "conversation_growth_diff", "output_diff")}
        dt = s["prefix_diff"] + s["conversation_growth_diff"] + s["output_diff"]
        pct = (f"{s['prefix_diff']/dt*100:.0f}% / {s['conversation_growth_diff']/dt*100:.0f}%"
               f" / {s['output_diff']/dt*100:.0f}%") if dt else "—"
        md.append(f"| {label} | {fmt(dt)} | {fmt(s['prefix_diff'])} | {fmt(s['conversation_growth_diff'])} "
                  f"| {fmt(s['output_diff'])} | {pct} |")
        return s

    core3 = exact3_rows(lambda b: b == core)
    for _, case, p, d, e3 in core3:
        dt3 = e3["prefix_diff"] + e3["conversation_growth_diff"] + e3["output_diff"]
        pct = (f"{e3['prefix_diff']/dt3*100:.0f}% / {e3['conversation_growth_diff']/dt3*100:.0f}%"
               f" / {e3['output_diff']/dt3*100:.0f}%") if dt3 else "—"
        md.append(f"| r1025 {case} | {fmt(dt3)} | {fmt(e3['prefix_diff'])} "
                  f"| {fmt(e3['conversation_growth_diff'])} | {fmt(e3['output_diff'])} | {pct} |")
    agg3 = {}
    for label, sel in (("r1023 5 题合计", lambda b: b == "r1023-cli-dsf-low"),
                       ("r1024 5 题合计", lambda b: b == "r1024-probe-区分度"),
                       ("r1025 5 题合计", lambda b: b == core),
                       ("r1028 6 场合计", lambda b: b == "r1028-repeats")):
        rows = exact3_rows(sel)
        if rows:
            agg3[label] = exact3_line(label, rows)
    all3 = exact3_rows(lambda b: True)
    agg3[f"全部配对（{len(all3)} 对）"] = exact3_line(f"全部配对（{len(all3)} 对）", all3)
    md.append("")

    # 全部配对的逐对比率区间（供结论草案引用）
    ratios = [(p["total_tokens"] / d["total_tokens"], p["run"], d["run"])
              for _, _, p, d in pairs]
    ratios.sort()

    md.append("## 4. 消融批（r20261027-ablation，外部目录只读）\n")
    md.append("| cell | result.json | call1_prefix | n_calls | total | 状态 |")
    md.append("|---|---|---:|---:|---:|---|")
    for c in ablation_cells:
        if "call1_prefix_tokens" in c:
            md.append(f"| {c['cell']} | ✓ | {fmt(c['call1_prefix_tokens'])} | {c['n_calls']} "
                      f"| {fmt(c['total_tokens'])} | 已解析 |")
        else:
            md.append(f"| {c['cell']} | {'✓' if c['has_result_json'] else '✗'} | — | — | — "
                      f"| {'解析失败' if c.get('error') else '批未完成，待补算'} |")
    base_by_case = {c: next((x for x in ablation_cells if x["case"] == c and x["arm"] == "codex-base"
                             and "call1_prefix_tokens" in x), None) for c in ABLATION_CASES}
    for c in ABLATION_CASES:
        b = base_by_case[c]
        if not b:
            continue
        for arm, label in (("codex-skill", "技能注入体积（codex-skill − codex-base）"),
                           ("codex-gpt", "原生模型前缀差（codex-gpt − codex-base）")):
            x = next((y for y in ablation_cells if y["cell"] == f"{c}__{arm}"), None)
            if x and "call1_prefix_tokens" in x:
                md.append(f"- {c} {label}：**{fmt(x['call1_prefix_tokens'] - b['call1_prefix_tokens'])}** tokens"
                          f"（{fmt(x['call1_prefix_tokens'])} − {fmt(b['call1_prefix_tokens'])}）。\n")
    if ablation_missing:
        md.append("\n**待补算清单**（重跑本脚本自动更新）：\n")
        for m in ablation_missing:
            md.append(f"- {m}")
    md.append("")

    # ── 结论草案（全部由上方数字直接推出；恒等式拆分≠因果证明） ─────────────
    hit_share = {
        h: (sum(r["sum_input_hit"] for r in runs if r["harness"] == h),
            sum(r["sum_input"] for r in runs if r["harness"] == h))
        for h in ("codex", "dsh")}
    md.append("## 5. 结论草案（待更多轮次验证；数字溯源见各表 run 列与 per_run.json）\n")
    md.append(f"1. **形态**：两 CLI 都是「小前缀起步、多调用滚动增长」。真实调用数均值 codex "
              f"{codex_all['ncalls_mean']} vs dsh {dsh_all['ncalls_mean']}（dsh 略多但同量级）；"
              f"call-1 前缀均值 codex {fmt(codex_all['prefix_mean'])} vs dsh "
              f"{fmt(dsh_all['prefix_mean'])}（codex 首调多约 "
              f"{codex_all['prefix_mean']-dsh_all['prefix_mean']:,} tok，"
              f"主要为系统提示+工具模式差异）。A 组 codex 顶层 agent.jsonl 只存末次累计"
              f"（turn.completed×1），逐调用真值在 agent-session rollout 的 token_count，"
              f"两来源末次累计 {n_match}/{n_codex_runs} 场一致。\n")
    md.append(f"2. **体量**：总量比全 44 场合计 "
              f"{codex_all['total_sum']/dsh_all['total_sum']:.2f}×、r1025 核心 5 题 "
              f"{cp['total_sum']/dp['total_sum']:.2f}×；同题配对比值区间 "
              f"{ratios[0][0]:.2f}×–{ratios[-1][0]:.2f}×（最小 {ratios[0][1]}，最大 {ratios[-1][1]}）；"
              f"单场均值 codex {fmt(codex_all['total_mean'])} vs dsh {fmt(dsh_all['total_mean'])}。\n")
    if all3:
        s = {k: sum(r[k] for *_, r in all3) for k in
             ("prefix_diff", "conversation_growth_diff", "output_diff")}
        dt = s["prefix_diff"] + s["conversation_growth_diff"] + s["output_diff"]
        dom = max(s, key=lambda k: abs(s[k]))
        dom_label = {"prefix_diff": "① call-1 前缀差",
                     "conversation_growth_diff": "② 对话增长差",
                     "output_diff": "③ 输出差"}[dom]
        md.append(f"3. **三因子占比（全部 {len(all3)} 对配对，Δtotal={fmt(dt)}）**：前缀差 "
                  f"{fmt(s['prefix_diff'])}（{s['prefix_diff']/dt*100:.0f}%）、对话增长差 "
                  f"{fmt(s['conversation_growth_diff'])}（{s['conversation_growth_diff']/dt*100:.0f}%）、"
                  f"输出差 {fmt(s['output_diff'])}（{s['output_diff']/dt*100:.0f}%）。"
                  f"主导项是**{dom_label}**；输出两侧几乎相当，总量差基本是输入侧"
                  f"（前缀结构 + 对话增长斜率）之争。\n")
        nc = sum(r["n_calls"] for r in runs if r["harness"] == "codex")
        nd = sum(r["n_calls"] for r in runs if r["harness"] == "dsh")
        ic = sum(r["sum_input"] for r in runs if r["harness"] == "codex")
        idl = sum(r["sum_input"] for r in runs if r["harness"] == "dsh")
        rc = sum(r["sum_reasoning"] or 0 for r in runs if r["harness"] == "codex")
        md.append(f"   斜率佐证：单次调用平均输入 codex {fmt(round(ic/nc))} vs dsh "
                  f"{fmt(round(idl/nd))} tok（调用总数 {nc} vs {nd}，几乎相同）。"
                  f"即多出来的量是 codex 每次调用回放的上下文更大；"
                  f"codex reasoning_output_tokens 合计 {fmt(rc)} tok"
                  f"（dsh 轨迹无 reasoning 拆分，无法对齐比较）——"
                  f"「codex 将 reasoning 项回放进后续调用上下文」是待验证假设，非本文结论。\n")
        if "r1025 5 题合计" in agg3:
            r = agg3["r1025 5 题合计"]
            dtr = r["prefix_diff"] + r["conversation_growth_diff"] + r["output_diff"]
            md.append(f"   r1025 核心 5 题（Δtotal={fmt(dtr)}）：前缀差 "
                      f"{r['prefix_diff']/dtr*100:.0f}% / 对话增长差 {r['conversation_growth_diff']/dtr*100:.0f}% "
                      f"/ 输出差 {r['output_diff']/dtr*100:.0f}%。\n")
    md.append(f"4. **缓存命中结构**：输入中命中占比 codex "
              f"{hit_share['codex'][0]/hit_share['codex'][1]*100:.1f}% vs dsh "
              f"{hit_share['dsh'][0]/hit_share['dsh'][1]*100:.1f}%。两 CLI 均高度依赖缓存读，"
              "总量差主要发生在「未命中」与「输出」的绝对量上，而非缓存策略差异。\n")
    md.append("5. **边界**：以上为恒等式/会计拆分，不构成因果证明；n=1/格，不排除单场波动"
              "（r1028 r2/r3 同题重跑间 codex 调用数与前缀即有明显波动）；"
              "call-1 前缀代理含首条用户消息，跨题不可比，仅同题同款内可比；"
              "codex 首调前缀略高于 dsh 的解释（系统提示/工具模式）是假设，"
              "待消融批补齐后用 codex-skill−codex-base、codex-gpt−codex-base 验证。\n")
    md.append("")

    (out_dir / "decomposition.md").write_text("\n".join(md), encoding="utf-8")

    # ── 5) 控制台汇总 ─────────────────────────────────────────────────────
    print(f"a_runs={len(runs)}/44  failures={len(fails)}  ablation_complete="
          f"{sum(1 for c in ablation_cells if 'call1_prefix_tokens' in c)}/{len(ablation_cells)}")
    for f in fails:
        print("FAIL", f)
    print(f"codex: prefix_mean={fmt(codex_all['prefix_mean'])} ncalls_mean={codex_all['ncalls_mean']} "
          f"total_sum={fmt(codex_all['total_sum'])}")
    print(f"dsh  : prefix_mean={fmt(dsh_all['prefix_mean'])} ncalls_mean={dsh_all['ncalls_mean']} "
          f"total_sum={fmt(dsh_all['total_sum'])}")
    print(f"total ratio codex/dsh = {codex_all['total_sum']/dsh_all['total_sum']:.2f}x "
          f"(r1025 core: {cp['total_sum']/dp['total_sum']:.2f}x)")
    if core_pairs:
        s = sum(decompose(p, d)["structure_x_orchestration"] for _, p, d in core_pairs)
        dt = sum(decompose(p, d)["delta_total"] for _, p, d in core_pairs)
        print(f"r1025 two-factor: structure={fmt(s)} ({s/dt*100:.0f}%) residual={fmt(dt-s)} ({(dt-s)/dt*100:.0f}%)")
    if all3:
        s3 = {k: sum(r[k] for *_, r in all3) for k in
              ("prefix_diff", "conversation_growth_diff", "output_diff")}
        dt3 = sum(s3.values())
        print(f"all-pairs exact3: delta={fmt(dt3)} prefix={fmt(s3['prefix_diff'])}"
              f" ({s3['prefix_diff']/dt3*100:.0f}%) growth={fmt(s3['conversation_growth_diff'])}"
              f" ({s3['conversation_growth_diff']/dt3*100:.0f}%) output={fmt(s3['output_diff'])}"
              f" ({s3['output_diff']/dt3*100:.0f}%)")
        print(f"pair ratio range: {ratios[0][0]:.2f}x ({ratios[0][1]}) .. "
              f"{ratios[-1][0]:.2f}x ({ratios[-1][1]})")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
