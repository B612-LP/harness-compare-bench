#!/usr/bin/env python3
"""build_truth.py — 用 golden 产物重建 truth.json（建题/复核用，v0.1，2026-10-22）

checker.py 运行时不调用本脚本；仅在重建输入或重算 golden 后刷新 truth.json。

流程（见 spec.md §6）：
    python3 environment/tools/gen_events.py --out environment/events.jsonl
    python3 solution/replay.py environment/events.jsonl --outdir <golden_dir>
    python3 environment/tools/build_truth.py --events environment/events.jsonl \
        --golden <golden_dir> --out truth.json

truth.json 内容：
    input_sha256            canonical events.jsonl 的 SHA-256（输入完整性守卫基准）
    expected.final_state    golden 订单终态（checker 启动时与自身重放交叉校验）
    expected.anomalies      golden 异常流水
    expected.money          金额合计（= golden 终态的 Σpaid / Σrefund）
    stats                   结构性统计（供人工复核，不参与判分）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path


def main(argv):
    parser = argparse.ArgumentParser(description="ledger-replay truth.json 重建工具")
    parser.add_argument("--events", required=True, help="canonical events.jsonl 路径")
    parser.add_argument("--golden", required=True, help="solution/replay.py 产物目录")
    parser.add_argument("--out", required=True, help="truth.json 输出路径")
    args = parser.parse_args(argv)

    events_path = Path(args.events)
    golden = Path(args.golden)
    raw = events_path.read_bytes()
    input_sha = hashlib.sha256(raw).hexdigest()

    final_state = json.loads((golden / "final_state.json").read_text(encoding="utf-8"))
    anomalies = json.loads((golden / "anomalies.json").read_text(encoding="utf-8"))
    if [r["order_id"] for r in final_state] != sorted(r["order_id"] for r in final_state):
        raise SystemExit("ERROR: golden final_state 未按 order_id 升序")
    if [(r["seq"], r["msg_id"]) for r in anomalies] != sorted(
            (r["seq"], r["msg_id"]) for r in anomalies):
        raise SystemExit("ERROR: golden anomalies 未按 (seq, msg_id) 升序")

    events = [json.loads(line) for line in raw.decode("utf-8").split("\n") if line]
    unique_msg = {e["msg_id"] for e in events}
    replay_sorted = sorted(events, key=lambda e: (e["seq"], e["msg_id"]))
    out_of_order = sum(1 for a, b in zip(events, replay_sorted)
                       if (a["seq"], a["msg_id"]) != (b["seq"], b["msg_id"]))
    seq_groups = Counter(e["seq"] for e in events)
    ts_groups = Counter(e["ts"] for e in events)
    pay_total = sum(r["paid_total"] for r in final_state)
    refund_total = sum(r["refunded_total"] for r in final_state)

    truth = {
        "case_id": "ledger-replay",
        "checker_version": "0.1",
        "input_name": "events.jsonl",
        "input_sha256": input_sha,
        "expected": {
            "final_state": final_state,
            "anomalies": anomalies,
            "money": {"pay_total": pay_total, "refund_total": refund_total},
        },
        "stats": {
            "line_count": len(events),
            "order_count": len(final_state),
            "unique_msg_id": len(unique_msg),
            "anomaly_count": len(anomalies),
            "anomaly_types": dict(sorted(Counter(a["type"] for a in anomalies).items())),
            "out_of_order_positions": out_of_order,
            "seq_collision_groups": sorted(s for s, n in seq_groups.items() if n > 1),
            "same_second_events": sum(n for n in ts_groups.values() if n > 1),
            "money_pay_total": pay_total,
            "money_refund_total": refund_total,
        },
        "note": (
            "expected 为建题时 solution/replay.py（oracle）的重放结果；checker.py 从 canonical "
            "events.jsonl 独立重放并与 expected 交叉校验，任一方漂移即退出码 2。"
            "stats 仅供人工复核，不参与判分。"
        ),
    }
    Path(args.out).write_text(
        json.dumps(truth, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("truth.json written: sha256=%s orders=%d anomalies=%d pay=%d refund=%d" % (
        input_sha[:12], len(final_state), len(anomalies), pay_total, refund_total))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
