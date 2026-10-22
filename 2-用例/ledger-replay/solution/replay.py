#!/usr/bin/env python3
"""replay.py — ledger-replay 参考重放器（oracle，v0.1，2026-10-22）

独立参考实现：按题面规则完整重放 events.jsonl，产出两份对账产物：
    final_state.json   订单终态（按 order_id 升序）
    anomalies.json     异常流水（按 seq 升序，同 seq 按 msg_id 字典序）

重放规则（与 instruction.md 一致）：
  1. 重放顺序 = (seq 升序, msg_id 字典序)；物理文件顺序与 ts 均不参与排序。
  2. 幂等：msg_id 首次出现才处理；再次出现 → 跳过并记 duplicate_msg_id。
  3. 负金额 → 拒绝生效（状态与金额均不变），记 negative_amount。
  4. ack=false → 事件照常生效，另记 unacked。
  5. 状态机（金额一律整数分）：
       create  仅当订单不存在 → created
       pay     created|paid  → paid_total += amount，state=paid
       cancel  created → cancelled；paid|refunded → late_cancel（状态不变）
       refund  paid|refunded → refunded_total += amount；
               refunded_total ≥ paid_total 时 state=refunded，否则仍 paid
  6. 异常优先级：duplicate > negative_amount > unacked > 状态机（含 late_cancel），
     每条事件至多触发前一条命中的异常即停（本数据集中无叠加样本）。

仅 stdlib，Python 3.9+。不读仓库内任何真值（与 checker.py 互为独立实现）。

用法：
    python3 replay.py <events.jsonl> --outdir <输出目录>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

VALID_OPS = ("create", "pay", "cancel", "refund")


class OrderLedger:
    """订单状态账本：按重放序逐条吸收事件。"""

    def __init__(self):
        self.orders = {}
        self.seen_msg_ids = set()
        self.anomalies = []
        self.money = {"pay": 0, "refund": 0}

    # ---- 异常登记 ----
    def _record(self, kind, ev):
        self.anomalies.append(
            {"type": kind, "msg_id": ev["msg_id"], "order_id": ev["order_id"], "seq": ev["seq"]}
        )

    # ---- 单条事件入账（返回是否生效） ----
    def absorb(self, ev):
        mid = ev["msg_id"]
        if mid in self.seen_msg_ids:                 # 规则 2：幂等去重
            self._record("duplicate_msg_id", ev)
            return False
        self.seen_msg_ids.add(mid)

        amount = ev["amount"]
        if amount < 0:                               # 规则 3：负金额拒绝
            self._record("negative_amount", ev)
            return False
        if ev["ack"] is False:                       # 规则 4：缺 ack 仍生效
            self._record("unacked", ev)

        order_id, op = ev["order_id"], ev["op"]
        state = self.orders.get(order_id)

        if op == "create":
            if state is None:
                self.orders[order_id] = {"state": "created", "paid_total": 0, "refunded_total": 0}
            return True

        if state is None:                            # pay/cancel/refund 落在无单上：忽略
            return False

        if op == "pay":
            if state["state"] in ("created", "paid"):
                state["paid_total"] += amount
                state["state"] = "paid"
                self.money["pay"] += amount
                return True
            return False

        if op == "cancel":
            if state["state"] == "created":
                state["state"] = "cancelled"
                return True
            if state["state"] in ("paid", "refunded"):   # 规则 5：cancel-after-complete
                self._record("late_cancel", ev)
            return False

        if op == "refund":
            if state["state"] in ("paid", "refunded"):
                state["refunded_total"] += amount
                self.money["refund"] += amount
                if state["refunded_total"] >= state["paid_total"]:
                    state["state"] = "refunded"
                return True
            return False

        raise ValueError("unknown op: %r" % op)

    # ---- 产物 ----
    def final_state(self):
        rows = [
            {"order_id": oid, "state": s["state"],
             "paid_total": s["paid_total"], "refunded_total": s["refunded_total"]}
            for oid, s in self.orders.items()
        ]
        rows.sort(key=lambda r: r["order_id"])
        return rows

    def anomaly_report(self):
        rows = sorted(self.anomalies, key=lambda r: (r["seq"], r["msg_id"]))
        return [{"type": r["type"], "msg_id": r["msg_id"],
                 "order_id": r["order_id"], "seq": r["seq"]} for r in rows]


def load_events(path):
    events = []
    raw = Path(path).read_bytes()
    if b"\r" in raw:
        raise SystemExit("ERROR: 事件日志含 CR（要求纯 LF）")
    text = raw.decode("utf-8")
    for lineno, line in enumerate(text.split("\n"), 1):
        if line == "":
            continue
        ev = json.loads(line)
        missing = [k for k in ("seq", "msg_id", "ts", "order_id", "op", "amount", "ack")
                   if k not in ev]
        if missing:
            raise SystemExit("ERROR: 第 %d 行缺字段 %s" % (lineno, missing))
        if ev["op"] not in VALID_OPS:
            raise SystemExit("ERROR: 第 %d 行非法 op %r" % (lineno, ev["op"]))
        if type(ev["amount"]) is not int or type(ev["seq"]) is not int:
            raise SystemExit("ERROR: 第 %d 行 seq/amount 必须为整数" % lineno)
        events.append(ev)
    if not events:
        raise SystemExit("ERROR: 事件日志为空")
    return events


def dump_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv):
    parser = argparse.ArgumentParser(description="ledger-replay 参考重放器")
    parser.add_argument("events", help="events.jsonl 路径")
    parser.add_argument("--outdir", required=True, help="产物输出目录")
    args = parser.parse_args(argv)

    events = load_events(args.events)
    ledger = OrderLedger()
    for ev in sorted(events, key=lambda e: (e["seq"], e["msg_id"])):
        ledger.absorb(ev)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    final_state = ledger.final_state()
    anomalies = ledger.anomaly_report()
    dump_json(outdir / "final_state.json", final_state)
    dump_json(outdir / "anomalies.json", anomalies)

    print(json.dumps({
        "orders": len(final_state),
        "anomalies": len(anomalies),
        "money_pay_total": ledger.money["pay"],
        "money_refund_total": ledger.money["refund"],
        "conserved": ledger.money["pay"] - ledger.money["refund"] ==
                     sum(r["paid_total"] - r["refunded_total"] for r in final_state),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
