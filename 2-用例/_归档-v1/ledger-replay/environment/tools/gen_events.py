#!/usr/bin/env python3
"""gen_events.py — ledger-replay 确定性事件日志生成器（v0.1，2026-10-22）

固定随机种子，可字节级复现 environment/events.jsonl（仅 stdlib，Python 3.9+）。

脏数据配方（题库规格，数字精确锁定）：
  ① 文件物理顺序 ≠ seq 逻辑序：乱序 ≥30 处（实际以 shuffle 后计数为准，stdout 报告）
  ② 3 个重复 msg_id：重放序后到的那条记 duplicate_msg_id，仅计一次
  ③ 2 个 cancel-after-complete：paid 订单上的 cancel → late_cancel，状态不变
  ④ 4 个 ack=false：事件仍生效 → unacked
  ⑤ 2 个负金额：拒绝生效 → negative_amount
  ⑥ 同秒 ts 乱序：每 3 个（构造序）事件共享同一秒 ts；ts 仅展示字段，不参与重放排序

另有 5 组同 seq 事件（3 组 create+pay、2 组 pay+refund），必须按 msg_id 字典序
打破平局；op 名首字母天然保序（c < p < r），故「字典序 = 因果序」。

生成器内置一个按题面规则的 mini 重放器，用于在源头自证：
  mini 重放结果 == 按订单生命周期构造的期望终态（两者任一有错则断言失败）。

用法：
    python3 gen_events.py --out environment/events.jsonl
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

SEED = 20261022
N_ORDERS = 100
BASE_TS = datetime(2026, 10, 20, 9, 0, 0)
EVENT_KEYS = ("seq", "msg_id", "ts", "order_id", "op", "amount", "ack")

# 每单生命周期配方（100 单）：
#   E  = create → pay → cancel(paid 上，late_cancel)          ×2
#   D  = create → cancel                                      ×12
#   B  = create → pay → refund(全额)                          ×20
#   C  = create → pay → refund(部分) → refund(余款)           ×16
#   A2 = create → pay → pay                                   ×30
#   A1 = create → pay                                         ×20（其中 2 单改造为负金额样本）
TYPE_PLAN = ["E"] * 2 + ["D"] * 12 + ["B"] * 20 + ["C"] * 16 + ["A2"] * 30 + ["A1"] * 20


def build():
    """按固定种子构造事件列表（构造序 = 因果序），返回 (events, meta, constructive)。"""
    rng = random.Random(SEED)
    orders = ["ORD%03d" % i for i in range(1, N_ORDERS + 1)]
    types = list(TYPE_PLAN)
    rng.shuffle(types)
    plan = dict(zip(orders, types))

    # --- 特殊订单挑选（同一种子下的固定调用序列，保证可复现） ---
    a1_orders = sorted(o for o, t in plan.items() if t == "A1")
    collide_cp = sorted(rng.sample(a1_orders, 3))            # create+pay 同 seq
    remaining_a1 = [o for o in a1_orders if o not in collide_cp]
    neg_orders = sorted(rng.sample(remaining_a1, 2))         # 负金额样本
    b_orders = sorted(o for o, t in plan.items() if t == "B")
    collide_pr = sorted(rng.sample(b_orders, 2))             # pay+refund 同 seq
    collided_orders = set(collide_cp) | set(collide_pr) | set(neg_orders)

    events = []          # 事件本体（seq/msg_id/ts/order_id/op/amount/ack）
    meta = []            # 与 events 平行的标注：applies/collided/op 类别
    op_k = {}            # (order, op) -> 第几次该 op（msg_id 后缀）
    seq = [0]
    constructive = {}    # 构造视角的期望终态（用于源头自证）

    def emit(order, op, amount, *, ack=True, reuse_seq=False, applies=True, collided=False):
        if not reuse_seq:
            seq[0] += 1
        k = op_k.get((order, op), 0)
        op_k[(order, op)] = k + 1
        events.append({
            "seq": seq[0],
            "msg_id": "m%04d-%s-%s%d" % (seq[0], order.lower(), op, k),
            "ts": None,  # 统一在构造完成后按槽位填
            "order_id": order,
            "op": op,
            "amount": amount,
            "ack": ack,
        })
        meta.append({"applies": applies, "collided": collided, "role": "base"})

    for order in orders:
        t = plan[order]
        if t == "A1":
            a = rng.randint(1500, 90000)
            if order in neg_orders:
                # create → pay(负金额，拒绝) → pay(正常金额)
                x = rng.randint(2000, 9000)
                emit(order, "create", 0, applies=True)
                emit(order, "pay", -x, applies=False)
                emit(order, "pay", a, applies=True)
                constructive[order] = ("paid", a, 0)
            elif order in collide_cp:
                # create 与 pay 共享同一 seq，msg_id 字典序决定因果（c < p）
                emit(order, "create", 0, collided=True)
                emit(order, "pay", a, reuse_seq=True, collided=True)
                constructive[order] = ("paid", a, 0)
            else:
                emit(order, "create", 0)
                emit(order, "pay", a)
                constructive[order] = ("paid", a, 0)
        elif t == "A2":
            a = rng.randint(1500, 90000)
            b = rng.randint(1000, 60000)
            emit(order, "create", 0)
            emit(order, "pay", a)
            emit(order, "pay", b)
            constructive[order] = ("paid", a + b, 0)
        elif t == "B":
            a = rng.randint(1500, 90000)
            if order in collide_pr:
                # pay 与 refund 共享同一 seq（p < r，字典序即因果）
                emit(order, "create", 0)
                emit(order, "pay", a, collided=True)
                emit(order, "refund", a, reuse_seq=True, collided=True)
            else:
                emit(order, "create", 0)
                emit(order, "pay", a)
                emit(order, "refund", a)
            constructive[order] = ("refunded", a, a)
        elif t == "C":
            a = rng.randint(1500, 90000)
            b = rng.randint(1000, 60000)
            total = a + b
            r1 = rng.randint(total // 4, 3 * total // 4)   # total ≥ 2500 → 1 ≤ r1 ≤ total-1
            r2 = total - r1
            emit(order, "create", 0)
            emit(order, "pay", a)
            emit(order, "pay", b)
            emit(order, "refund", r1)
            emit(order, "refund", r2)
            constructive[order] = ("refunded", total, total)
        elif t == "D":
            emit(order, "create", 0)
            emit(order, "cancel", 0)
            constructive[order] = ("cancelled", 0, 0)
        elif t == "E":
            a = rng.randint(1500, 90000)
            emit(order, "create", 0)
            emit(order, "pay", a)
            emit(order, "cancel", 0, applies=False)   # cancel-after-complete
            constructive[order] = ("paid", a, 0)      # 状态不变，仍是 paid
        else:
            raise AssertionError("unknown type %s" % t)

    # --- 3 个重复 msg_id：跨类型各取一条（create / pay / refund），非碰撞订单 ---
    def pool(op):
        return [i for i, e in enumerate(events)
                if e["op"] == op and not meta[i]["collided"] and meta[i]["applies"]]

    dup_sources = []
    for op in ("create", "pay", "refund"):
        pick = rng.sample(pool(op), 1)[0]
        dup_sources.append(pick)
        events.append({
            "seq": 0,  # 占位，下面统一续号
            "msg_id": events[pick]["msg_id"],
            "ts": None,
            "order_id": events[pick]["order_id"],
            "op": events[pick]["op"],
            "amount": events[pick]["amount"],
            "ack": events[pick]["ack"],
        })
        meta.append({"applies": False, "collided": False, "role": "dup"})
    for e in events[len(events) - 3:]:
        seq[0] += 1
        e["seq"] = seq[0]

    # --- 4 个 ack=false：只挑「干净生效、非碰撞、非重复源」的事件，仍生效 ---
    dup_ids = {events[i]["msg_id"] for i in dup_sources}
    eligible = [i for i, e in enumerate(events)
                if meta[i]["role"] == "base" and meta[i]["applies"]
                and not meta[i]["collided"] and e["msg_id"] not in dup_ids]
    unacked_picks = rng.sample(eligible, 4)
    for i in unacked_picks:
        events[i]["ack"] = False

    # --- ts：每 3 个（构造序）事件共享同一秒；仅展示字段 ---
    for i, e in enumerate(events):
        e["ts"] = (BASE_TS + timedelta(seconds=i // 3)).isoformat()

    # 断言：标注不重叠、配方数量精确
    assert len(unacked_picks) == 4 and len(dup_sources) == 3
    assert not (set(unacked_picks) & set(dup_sources))
    assert all(events[i]["ack"] is True for i in dup_sources)
    assert len(events) == 302 + 3, "事件总数应为 305"

    return events, meta, constructive, {
        "collide_cp": collide_cp, "collide_pr": collide_pr, "neg_orders": neg_orders,
        "unacked_picks": unacked_picks, "dup_sources": dup_sources,
    }


def mini_replay(events):
    """按题面规则的独立 mini 重放器（生成侧自证用）。返回 (orders, anomalies, money)。"""
    ordered = sorted(events, key=lambda e: (e["seq"], e["msg_id"]))
    seen = set()
    anomalies = []
    orders = {}
    money = {"pay": 0, "refund": 0}

    def anom(kind, e):
        anomalies.append({"type": kind, "msg_id": e["msg_id"],
                          "order_id": e["order_id"], "seq": e["seq"]})

    for e in ordered:
        if e["msg_id"] in seen:
            anom("duplicate_msg_id", e)
            continue
        seen.add(e["msg_id"])
        if e["amount"] < 0:
            anom("negative_amount", e)      # 拒绝生效
            continue
        if e["ack"] is False:
            anom("unacked", e)              # 仍生效
        o = orders.get(e["order_id"])
        op = e["op"]
        if op == "create":
            if o is None:
                orders[e["order_id"]] = {"state": "created", "paid_total": 0, "refunded_total": 0}
        elif op == "pay":
            if o is not None and o["state"] in ("created", "paid"):
                o["paid_total"] += e["amount"]
                o["state"] = "paid"
                money["pay"] += e["amount"]
        elif op == "cancel":
            if o is not None:
                if o["state"] == "created":
                    o["state"] = "cancelled"
                elif o["state"] in ("paid", "refunded"):
                    anom("late_cancel", e)  # 状态不变
        elif op == "refund":
            if o is not None and o["state"] in ("paid", "refunded"):
                o["refunded_total"] += e["amount"]
                money["refund"] += e["amount"]
                if o["refunded_total"] >= o["paid_total"]:
                    o["state"] = "refunded"
    anomalies.sort(key=lambda a: (a["seq"], a["msg_id"]))
    return orders, anomalies, money


def main(argv):
    parser = argparse.ArgumentParser(description="ledger-replay 确定性事件日志生成器")
    parser.add_argument("--out", required=True, help="输出 events.jsonl 路径")
    args = parser.parse_args(argv)

    events, meta, constructive, picks = build()

    # ① 物理乱序：固定种子 shuffle
    physical = list(events)
    random.Random(SEED).shuffle(physical)

    # ⑦ 源头自证：mini 重放 == 构造终态 == 守恒
    replay_orders, replay_anoms, money = mini_replay(events)
    expect = {oid: {"state": s, "paid_total": p, "refunded_total": r}
              for oid, (s, p, r) in constructive.items()}
    assert replay_orders == expect, "mini 重放与构造终态不一致（生成器自证失败）"
    assert money["pay"] - money["refund"] == sum(
        v["paid_total"] - v["refunded_total"] for v in expect.values()), "金额守恒不成立"

    sorted_by_rule = sorted(events, key=lambda e: (e["seq"], e["msg_id"]))
    out_of_order = sum(1 for a, b in zip(physical, sorted_by_rule)
                       if (a["seq"], a["msg_id"]) != (b["seq"], b["msg_id"]))
    assert out_of_order >= 30, "乱序位置 %d < 30" % out_of_order

    seq_groups = {}
    for e in events:
        seq_groups.setdefault(e["seq"], 0)
        seq_groups[e["seq"]] += 1
    collision_groups = sorted(s for s, n in seq_groups.items() if n > 1)
    assert len(collision_groups) == 5, "同 seq 组应为 5，实际 %s" % collision_groups

    ts_counter = {}
    for e in events:
        ts_counter[e["ts"]] = ts_counter.get(e["ts"], 0) + 1
    same_second_events = sum(n for n in ts_counter.values() if n > 1)

    text = "\n".join(json.dumps({k: e[k] for k in EVENT_KEYS}, ensure_ascii=False)
                     for e in physical) + "\n"
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(text.encode("utf-8"))

    type_counts = {}
    for a in replay_anoms:
        type_counts[a["type"]] = type_counts.get(a["type"], 0) + 1
    stats = {
        "lines": len(physical),
        "orders": len(expect),
        "unique_msg_id": len({e["msg_id"] for e in events}),
        "duplicate_msg_id": type_counts.get("duplicate_msg_id", 0),
        "late_cancel": type_counts.get("late_cancel", 0),
        "unacked": type_counts.get("unacked", 0),
        "negative_amount": type_counts.get("negative_amount", 0),
        "out_of_order_positions": out_of_order,
        "collision_groups": len(collision_groups),
        "collision_seqs": collision_groups,
        "same_second_events": same_second_events,
        "money_pay_total": money["pay"],
        "money_refund_total": money["refund"],
    }
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
