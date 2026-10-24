#!/usr/bin/env python3
"""ledger-replay 轻量判卷器 v0.1（2026-10-22）

用法：
    python3 checker.py <run_dir> [--json]
    python3 checker.py --selftest

run_dir 约定（见 spec.md）：
    final_state.json    必需产物；也接受 run_dir/output/、run_dir/outputs/ 下同名文件
    anomalies.json      必需产物；同上
    events.jsonl        可选；存在时比对 SHA-256（输入完整性守卫）
    meta.json           可选；产品/版本/操作人等运行元信息，不参与判分

口径：
    headline 为二值 0/1（BINARY=True：全 PASS=1，任一 FAIL=0）。
    逐项权重只用于复核定位与加权参考，不改变二值口径。
    输入副本与 canonical 不一致 → 直接 0（防「改输入再作答」）；
    未附输入副本 → 输入完整性记「未核验」，不因此扣分（证据不足不硬判）。

独立性：
    本文件内嵌一份与 solution/replay.py 互不引用的完整重放实现（第二实现），
    不读 solution/ 目录。启动时以 canonical 输入现算期望，并与 truth.json 的
    golden 交叉校验——用例或实现任一漂移 → 退出码 2（用例自身不一致）。
    金额守恒断言（Σpay − Σrefund == Σ(paid_total − refunded_total)）同样在
    启动守卫中执行：对不上说明两侧实现都算错了钱 → 退出码 2，不给判分。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

CASE_ID = "ledger-replay"
CHECKER_VERSION = "0.1"
BINARY = True
INPUT_NAME = "events.jsonl"
ARTIFACTS = ("final_state.json", "anomalies.json")

ANOMALY_TYPES = ("duplicate_msg_id", "late_cancel", "unacked", "negative_amount")
ORDER_STATES = ("created", "paid", "cancelled", "refunded")
EVENT_FIELDS = ("seq", "msg_id", "ts", "order_id", "op", "amount", "ack")
VALID_OPS = ("create", "pay", "cancel", "refund")

ITEMS = [
    ("artifacts_exist", "产物存在", 10),
    ("input_integrity", "输入完整性（守卫）", 10),
    ("final_state_format", "final_state 结构（数组/字段/整数分/升序）", 10),
    ("final_state_exact", "final_state 逐订单逐字段一致", 30),
    ("anomalies_format", "anomalies 结构（字段/类型枚举/seq 升序）", 5),
    ("anomalies_exact", "anomalies 集合与顺序完全一致", 30),
    ("money_conservation", "金额守恒（Σpaid−Σrefund == 有效 pay−refund）", 5),
]
WEIGHTS = {item[0]: item[2] for item in ITEMS}
TITLES = {item[0]: item[1] for item in ITEMS}

CASE_DIR = Path(__file__).resolve().parent


# ---------------------------------------------------------------- case loading

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _case_error(message):
    """用例自身不一致：truth/输入/守卫对不上 → 退出码 2，不给判分。"""
    print("ERROR: " + message, file=sys.stderr)
    sys.exit(2)


def load_truth():
    path = CASE_DIR / "truth.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _case_error("truth.json 不可读或非法：%s（%s）" % (path, exc))


def canonical_input():
    """读 canonical events.jsonl 并用 truth.json 记录的 SHA-256 校验用例未被改动。"""
    truth = load_truth()
    path = CASE_DIR / "environment" / truth["input_name"]
    try:
        data = path.read_bytes()
    except OSError as exc:
        _case_error("canonical 输入不可读：%s（%s）" % (path, exc))
    actual = sha256_bytes(data)
    if actual != truth["input_sha256"]:
        _case_error("用例 canonical 输入与 truth 记录不一致：%s\n  truth=%s\n  actual=%s"
                    % (path, truth["input_sha256"], actual))
    return truth, data


def parse_events(data):
    """严格解析 canonical 事件日志；坏行属用例自身问题 → 退出码 2。"""
    if b"\r" in data:
        _case_error("canonical 事件日志含 CR（要求纯 LF）")
    events = []
    for lineno, line in enumerate(data.decode("utf-8").split("\n"), 1):
        if line == "":
            continue
        try:
            ev = json.loads(line)
        except ValueError as exc:
            _case_error("canonical 事件日志第 %d 行非法 JSON：%s" % (lineno, exc))
        missing = [k for k in EVENT_FIELDS if k not in ev]
        if missing:
            _case_error("canonical 事件日志第 %d 行缺字段 %s" % (lineno, missing))
        if type(ev["seq"]) is not int or type(ev["amount"]) is not int:
            _case_error("canonical 事件日志第 %d 行 seq/amount 必须为整数" % lineno)
        if not isinstance(ev["ack"], bool) or ev["op"] not in VALID_OPS:
            _case_error("canonical 事件日志第 %d 行 ack/op 非法" % lineno)
        events.append(ev)
    if not events:
        _case_error("canonical 事件日志为空")
    return events


# ------------------------------------------------- independent replay (2nd impl)

def replay(events):
    """按题面规则完整重放（与 solution/replay.py 互为独立实现）。

    顺序 = (seq 升序, msg_id 字典序)；幂等去重 > 负金额拒绝 > unacked(仍生效) >
    状态机（cancel 落在 paid/refunded → late_cancel，状态不变）。
    返回 (orders, anomalies, money)。
    """
    seen = set()
    anomalies = []
    orders = {}
    money = {"pay": 0, "refund": 0}

    def record(kind, ev):
        anomalies.append({"type": kind, "msg_id": ev["msg_id"],
                          "order_id": ev["order_id"], "seq": ev["seq"]})

    for ev in sorted(events, key=lambda e: (e["seq"], e["msg_id"])):
        if ev["msg_id"] in seen:
            record("duplicate_msg_id", ev)          # 幂等：重复 msg_id 只计一次
            continue
        seen.add(ev["msg_id"])
        if ev["amount"] < 0:
            record("negative_amount", ev)           # 拒绝生效
            continue
        if ev["ack"] is False:
            record("unacked", ev)                   # 仍生效
        order = orders.get(ev["order_id"])
        op = ev["op"]
        if op == "create":
            if order is None:
                orders[ev["order_id"]] = {"state": "created", "paid_total": 0,
                                          "refunded_total": 0}
        elif order is not None:                     # 其余 op 都要求订单已存在
            if op == "pay" and order["state"] in ("created", "paid"):
                order["paid_total"] += ev["amount"]
                order["state"] = "paid"
                money["pay"] += ev["amount"]
            elif op == "cancel":
                if order["state"] == "created":
                    order["state"] = "cancelled"
                elif order["state"] in ("paid", "refunded"):
                    record("late_cancel", ev)       # 状态不变
            elif op == "refund" and order["state"] in ("paid", "refunded"):
                order["refunded_total"] += ev["amount"]
                money["refund"] += ev["amount"]
                if order["refunded_total"] >= order["paid_total"]:
                    order["state"] = "refunded"
    anomalies.sort(key=lambda a: (a["seq"], a["msg_id"]))
    final = [{"order_id": oid,
              "state": orders[oid]["state"],
              "paid_total": orders[oid]["paid_total"],
              "refunded_total": orders[oid]["refunded_total"]}
             for oid in sorted(orders)]
    return final, anomalies, money


def verify_case(truth, final, anomalies, money):
    """用例一致性守卫：现算重放 vs truth golden vs 金额守恒，任一不符 → 退出码 2。"""
    expected = truth["expected"]
    if final != expected["final_state"]:
        _case_error("checker 重放与 truth.final_state 不一致（用例或实现漂移）")
    if anomalies != expected["anomalies"]:
        _case_error("checker 重放与 truth.anomalies 不一致（用例或实现漂移）")
    if (money["pay"] != expected["money"]["pay_total"]
            or money["refund"] != expected["money"]["refund_total"]):
        _case_error("checker 重放金额与 truth.money 不一致（用例或实现漂移）")
    delta = sum(row["paid_total"] - row["refunded_total"] for row in final)
    if money["pay"] - money["refund"] != delta:
        _case_error("金额守恒断言失败：Σpay−Σrefund=%d ≠ Σ(paid−refunded)=%d"
                    % (money["pay"] - money["refund"], delta))


# ---------------------------------------------------------------- run_dir I/O

def find_file(run_dir, name):
    for candidate in (run_dir / name, run_dir / "output" / name, run_dir / "outputs" / name):
        if candidate.is_file():
            return candidate
    return None


def find_input(run_dir, name):
    for candidate in (run_dir / name, run_dir / "input" / name, run_dir / "inputs" / name):
        if candidate.is_file():
            return candidate
    return None


class _NonDecimal(Exception):
    """JSON 中出现浮点数 / NaN / Infinity 的信号。"""


def _reject_float(text):
    raise _NonDecimal("浮点数 %s（金额必须为整数分）" % text)


def _reject_constant(name):
    raise _NonDecimal("非常量 %s（金额必须为整数分）" % name)


def parse_json_strict(text):
    return json.loads(text, parse_float=_reject_float, parse_constant=_reject_constant)


# ---------------------------------------------------------------- format checks

def check_final_state_format(payload):
    if not isinstance(payload, list):
        return False, "顶层不是 JSON 数组"
    seen_ids = []
    for index, row in enumerate(payload, 1):
        if not isinstance(row, dict):
            return False, "第 %d 项不是对象" % index
        if set(row.keys()) != {"order_id", "state", "paid_total", "refunded_total"}:
            return False, "第 %d 项字段集不是 {order_id,state,paid_total,refunded_total}" % index
        if not isinstance(row["order_id"], str):
            return False, "第 %d 项 order_id 不是字符串" % index
        if row["state"] not in ORDER_STATES:
            return False, "第 %d 项 state 非法：%r" % (index, row["state"])
        for key in ("paid_total", "refunded_total"):
            if type(row[key]) is not int:
                return False, "第 %d 项 %s 不是整数（禁浮点/布尔）" % (index, key)
        seen_ids.append(row["order_id"])
    if seen_ids != sorted(seen_ids):
        return False, "订单未按 order_id 升序"
    if len(set(seen_ids)) != len(seen_ids):
        return False, "存在重复 order_id"
    return True, ""


def check_anomalies_format(payload):
    if not isinstance(payload, list):
        return False, "顶层不是 JSON 数组"
    keys = []
    for index, row in enumerate(payload, 1):
        if not isinstance(row, dict):
            return False, "第 %d 项不是对象" % index
        if set(row.keys()) != {"type", "msg_id", "order_id", "seq"}:
            return False, "第 %d 项字段集不是 {type,msg_id,order_id,seq}" % index
        if row["type"] not in ANOMALY_TYPES:
            return False, "第 %d 项 type 非法：%r" % (index, row["type"])
        if not isinstance(row["msg_id"], str) or not isinstance(row["order_id"], str):
            return False, "第 %d 项 msg_id/order_id 不是字符串" % index
        if type(row["seq"]) is not int:
            return False, "第 %d 项 seq 不是整数" % index
        keys.append((row["seq"], row["msg_id"]))
    if keys != sorted(keys):
        return False, "未按 (seq, msg_id) 升序"
    return True, ""


def diff_summary(expected, actual, key_field, fields, limit=5):
    """逐元素对比，返回前 limit 条人读差异（无差异返回空串）。"""
    diffs = []
    if len(expected) != len(actual):
        diffs.append("条数：期望 %d，实际 %d" % (len(expected), len(actual)))
    for index in range(min(len(expected), len(actual))):
        exp_row, act_row = expected[index], actual[index]
        if act_row.get(key_field) != exp_row[key_field]:
            diffs.append("第 %d 项 %s：期望 %r，实际 %r"
                         % (index + 1, key_field, exp_row[key_field], act_row.get(key_field)))
            continue
        for field in fields:
            if act_row.get(field) != exp_row[field]:
                diffs.append("%s.%s：期望 %r，实际 %r"
                             % (exp_row[key_field], field, exp_row[field], act_row.get(field)))
        if len(diffs) >= limit:
            break
    return "；".join(diffs[:limit])


# ---------------------------------------------------------------- judge

def judge(run_dir):
    truth, input_bytes = canonical_input()
    events = parse_events(input_bytes)
    expected_final, expected_anoms, money = replay(events)
    verify_case(truth, expected_final, expected_anoms, money)

    items = []
    details = {}

    missing = [name for name in ARTIFACTS if find_file(run_dir, name) is None]
    if missing:
        items.append({"id": "artifacts_exist", "title": TITLES["artifacts_exist"],
                      "weight": WEIGHTS["artifacts_exist"], "status": "fail",
                      "detail": "未找到 %s（run_dir=%s）" % ("、".join(missing), run_dir)})
        for item_id, _, _ in ITEMS[1:]:
            items.append({"id": item_id, "title": TITLES[item_id],
                          "weight": WEIGHTS[item_id], "status": "fail",
                          "detail": "产物缺失，无法检查"})
        return _result(items, run_dir=run_dir, input_integrity="unverified", artifacts={})

    artifacts = {name: find_file(run_dir, name) for name in ARTIFACTS}
    items.append({"id": "artifacts_exist", "title": TITLES["artifacts_exist"],
                  "weight": WEIGHTS["artifacts_exist"], "status": "pass",
                  "detail": "、".join(str(p) for p in artifacts.values())})

    # 输入完整性守卫
    input_path = find_input(run_dir, INPUT_NAME)
    if input_path is None:
        integrity = "unverified"
        items.append({"id": "input_integrity", "title": TITLES["input_integrity"],
                      "weight": WEIGHTS["input_integrity"], "status": "unknown",
                      "detail": "运行目录未附 events.jsonl 副本，无法核对（不扣分，"
                                "但请在运行记录中说明）"})
    else:
        actual_input = input_path.read_bytes()
        details["input_sha256"] = sha256_bytes(actual_input)
        if actual_input == input_bytes:
            integrity = "verified"
            items.append({"id": "input_integrity", "title": TITLES["input_integrity"],
                          "weight": WEIGHTS["input_integrity"], "status": "pass",
                          "detail": "输入副本与 canonical 字节一致"})
        else:
            integrity = "mismatch"
            items.append({"id": "input_integrity", "title": TITLES["input_integrity"],
                          "weight": WEIGHTS["input_integrity"], "status": "fail",
                          "detail": "输入被修改：实际使用输入与 canonical 不一致（判 0）"})

    # 产物解析（浮点金额直接判结构失败）
    payloads = {}
    parse_errors = {}
    for name in ARTIFACTS:
        try:
            payloads[name] = parse_json_strict(artifacts[name].read_text(encoding="utf-8"))
        except (_NonDecimal, ValueError) as exc:
            payloads[name] = None
            parse_errors[name] = str(exc) if isinstance(exc, _NonDecimal) else "非法 JSON：%s" % exc

    # final_state 结构 + 值
    fs_payload = payloads["final_state.json"]
    if fs_payload is None:
        items.append({"id": "final_state_format", "title": TITLES["final_state_format"],
                      "weight": WEIGHTS["final_state_format"], "status": "fail",
                      "detail": parse_errors["final_state.json"]})
        items.append({"id": "final_state_exact", "title": TITLES["final_state_exact"],
                      "weight": WEIGHTS["final_state_exact"], "status": "fail",
                      "detail": "结构非法，无法比对"})
        cand_delta = None
    else:
        ok, reason = check_final_state_format(fs_payload)
        items.append({"id": "final_state_format", "title": TITLES["final_state_format"],
                      "weight": WEIGHTS["final_state_format"],
                      "status": "pass" if ok else "fail",
                      "detail": "通过" if ok else reason})
        exact = fs_payload == expected_final
        items.append({"id": "final_state_exact", "title": TITLES["final_state_exact"],
                      "weight": WEIGHTS["final_state_exact"], "status": "pass" if exact else "fail",
                      "detail": "逐订单逐字段一致" if exact else
                                diff_summary(expected_final, fs_payload, "order_id",
                                             ("state", "paid_total", "refunded_total"))})
        if ok:
            cand_delta = sum(row["paid_total"] - row["refunded_total"] for row in fs_payload)
        else:
            cand_delta = None

    # anomalies 结构 + 值
    an_payload = payloads["anomalies.json"]
    if an_payload is None:
        items.append({"id": "anomalies_format", "title": TITLES["anomalies_format"],
                      "weight": WEIGHTS["anomalies_format"], "status": "fail",
                      "detail": parse_errors["anomalies.json"]})
        items.append({"id": "anomalies_exact", "title": TITLES["anomalies_exact"],
                      "weight": WEIGHTS["anomalies_exact"], "status": "fail",
                      "detail": "结构非法，无法比对"})
    else:
        ok, reason = check_anomalies_format(an_payload)
        items.append({"id": "anomalies_format", "title": TITLES["anomalies_format"],
                      "weight": WEIGHTS["anomalies_format"],
                      "status": "pass" if ok else "fail",
                      "detail": "通过" if ok else reason})
        exact = an_payload == expected_anoms
        items.append({"id": "anomalies_exact", "title": TITLES["anomalies_exact"],
                      "weight": WEIGHTS["anomalies_exact"], "status": "pass" if exact else "fail",
                      "detail": "集合与顺序完全一致（%d 条）" % len(expected_anoms) if exact else
                                diff_summary(expected_anoms, an_payload, "msg_id",
                                             ("type", "order_id", "seq"))})

    # 金额守恒（对候送的产物做诊断性复核；期望侧守恒已在 verify_case 断言）
    expected_delta = money["pay"] - money["refund"]
    if cand_delta is None:
        cons_ok, cons_detail = False, "final_state 不可用，无法复核守恒"
    else:
        cons_ok = cand_delta == expected_delta
        cons_detail = ("Σ(paid−refunded)=%d == 有效流 %d" % (cand_delta, expected_delta)
                       if cons_ok else
                       "Σ(paid−refunded)=%d ≠ 有效流 %d" % (cand_delta, expected_delta))
    items.append({"id": "money_conservation", "title": TITLES["money_conservation"],
                  "weight": WEIGHTS["money_conservation"],
                  "status": "pass" if cons_ok else "fail", "detail": cons_detail})

    details["expected_money"] = money
    return _result(items, run_dir=run_dir, input_integrity=integrity,
                   artifacts={k: str(v) for k, v in artifacts.items()}, details=details)


def _result(items, *, run_dir, input_integrity, artifacts, details=None):
    failed = [item for item in items if item["status"] == "fail"]
    weighted = sum(item["weight"] for item in items if item["status"] == "pass")
    return {
        "case_id": CASE_ID,
        "checker_version": CHECKER_VERSION,
        "binary": BINARY,
        "run_dir": str(run_dir),
        "artifacts": artifacts,
        "items": items,
        "failed": [item["id"] for item in failed],
        "reward": 0 if failed else 1,
        "weighted": weighted,
        "max_weight": sum(item[2] for item in ITEMS),
        "input_integrity": input_integrity,
        **(details or {}),
    }


def render(result):
    lines = ["[%s] checker v%s  artifacts=%s" % (CASE_ID, CHECKER_VERSION,
                                                 ",".join(Path(v).name
                                                          for v in result["artifacts"].values())
                                                 or "-")]
    for item in result["items"]:
        status = {"pass": "PASS", "fail": "FAIL", "unknown": "UNKNOWN"}[item["status"]]
        lines.append("%-7s %-20s %3d/100  %s" % (status, item["id"], item["weight"],
                                                  item["detail"]))
    lines.append("REWARD %d (binary)   WEIGHTED %d/%d   INPUT %s"
                 % (result["reward"], result["weighted"], result["max_weight"],
                    result["input_integrity"]))
    return "\n".join(lines)


# ---------------------------------------------------------------- selftest

def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data, encoding="utf-8")


def _dump(payload):
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def selftest():
    truth, input_bytes = canonical_input()
    events = parse_events(input_bytes)
    expected_final, expected_anoms, money = replay(events)
    verify_case(truth, expected_final, expected_anoms, money)

    final_ok = _dump(expected_final)
    anoms_ok = _dump(expected_anoms)

    late_orders = [a["order_id"] for a in expected_anoms if a["type"] == "late_cancel"]
    neg_anoms = [a for a in expected_anoms if a["type"] == "negative_amount"]
    amount_of = {e["msg_id"]: e["amount"] for e in events}
    collision_orders = []
    for seq in truth["stats"]["seq_collision_groups"]:
        ops = sorted(e["op"] for e in events if e["seq"] == seq)
        oid = events[[i for i, e in enumerate(events) if e["seq"] == seq][0]]["order_id"]
        collision_orders.append((oid, ops))

    def final_mutate(fn):
        import copy
        rows = copy.deepcopy(expected_final)
        fn(rows)
        return _dump(rows)

    def anoms_mutate(keep):
        return _dump([a for a in expected_anoms if keep(a)])

    # 同 seq tie-break 弄反后的「貌似合理」错误终态
    def tie_break_reversed(rows):
        by_id = {r["order_id"]: r for r in rows}
        for oid, ops in collision_orders:
            row = by_id[oid]
            if ops == ["create", "pay"]:          # pay 抢在 create 前 → pay 被忽略
                row["state"], row["paid_total"], row["refunded_total"] = "created", 0, 0
            elif ops == ["pay", "refund"]:        # refund 抢在 pay 前 → refund 被忽略
                row["state"], row["refunded_total"] = "paid", 0

    fixtures = []

    def add(name, expect, *, final=final_ok, anoms=anoms_ok, include_input=True,
            input_data=None):
        fixtures.append((name, expect, final, anoms, include_input, input_data))

    add("golden：规范产物（附输入副本）", 1)
    add("golden：未附输入副本（未核验不扣分）", 1, include_input=False)
    add("缺产物（空目录）", 0, final=None, anoms=None)
    add("漏去重：anomalies 缺 duplicate_msg_id", 0,
        anoms=anoms_mutate(lambda a: a["type"] != "duplicate_msg_id"))
    add("late_cancel 改了状态（naive cancel）", 0,
        final=final_mutate(lambda rows: [r.update(state="cancelled")
                                         for r in rows if r["order_id"] in late_orders]))
    add("漏 unacked 异常", 0, anoms=anoms_mutate(lambda a: a["type"] != "unacked"))
    add("负金额生效（paid_total 吞掉负额）", 0,
        final=final_mutate(lambda rows: [r.update(
            paid_total=r["paid_total"] + amount_of[a["msg_id"]])
            for r in rows for a in neg_anoms if r["order_id"] == a["order_id"]]))
    add("anomalies 按文件序而非 seq 序", 0, anoms=_dump(list(reversed(expected_anoms))))
    add("金额用浮点（尾差陷阱）", 0,
        final=final_mutate(lambda rows: [r.update(paid_total=float(r["paid_total"]))
                                         for r in rows[:1]]))
    add("缺整单", 0, final=_dump(expected_final[1:]))
    add("篡改输入后自洽作答", 0, input_data=_tamper(input_bytes))
    add("同 seq tie-break 弄反（msg_id 降序）", 0,
        final=final_mutate(tie_break_reversed))

    failures = 0
    print("[%s] checker v%s 自测（canonical events sha256=%s…）"
          % (CASE_ID, CHECKER_VERSION, truth["input_sha256"][:12]))
    for name, expect, final, anoms, include_input, input_data in fixtures:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            if final is not None:
                _write(run_dir / "final_state.json", final)
            if anoms is not None:
                _write(run_dir / "anomalies.json", anoms)
            if include_input:
                _write(run_dir / INPUT_NAME, input_data if input_data is not None
                       else input_bytes)
            result = judge(run_dir)
            ok = result["reward"] == expect
            failures += 0 if ok else 1
            print("  %s  %s: reward=%d（期望 %d）%s"
                  % ("PASS" if ok else "FAIL", name, result["reward"], expect,
                     "；失败项=" + ",".join(result["failed"]) if result["failed"] else ""))
    print("负控制自测：%s" % ("通过" if failures == 0 else "%d 项不符合预期" % failures))
    return 0 if failures == 0 else 1


def _tamper(data):
    """构造被篡改的输入副本：把第一条事件的 amount 改成 +1（其余不动）。"""
    lines = data.decode("utf-8").split("\n")
    for index, line in enumerate(lines):
        if line:
            ev = json.loads(line)
            ev["amount"] = 1 if ev["amount"] <= 0 else -ev["amount"]
            lines[index] = json.dumps(ev, ensure_ascii=False)
            break
    return ("\n".join(lines)).encode("utf-8")


def main(argv):
    parser = argparse.ArgumentParser(description="ledger-replay 轻量判卷器 v%s" % CHECKER_VERSION)
    parser.add_argument("run_dir", nargs="?", help="运行目录（含 final_state.json / anomalies.json，"
                                                    "可选 events.jsonl 副本）")
    parser.add_argument("--json", action="store_true", help="只输出 JSON")
    parser.add_argument("--selftest", action="store_true", help="跑负控制/守卫自测")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.run_dir:
        parser.error("缺少 run_dir（或使用 --selftest）")

    result = judge(Path(args.run_dir))
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(render(result))
        print("RESULTS_JSON " + json.dumps(result, ensure_ascii=False))
    return 0 if result["reward"] == 1 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
