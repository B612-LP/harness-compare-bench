#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools-judge-agreement.py —— 判卷器可信度一致性计算（L38 主项F，2026-11-03）

用途：读一张标准「测项 × rater」判定表，计算多 rater 一致性指标：
  - Cohen's kappa（逐对，listwise：两 rater 均有效的测项）
  - Fleiss' kappa（全体 rater；仅取全部 rater 均有效的测项；两 rater 时与 Cohen 一致）
  - 百分一致率（逐对）
  - 逐对混淆矩阵（行=左 rater 标签，列=右 rater 标签）
  - 每 rater invalid（null/缺失/非法标签）计数与清单

零发射约束下的本工具自测（--selftest）只用合成数据（解析解已知），不触任何模型/网络/判分器。
不读不写仓库内容；输出收据 write-once（目标已存在则 exit 3 拒写），receipt_sha256=该字段置固定占位串
"PENDING" 后 canonical JSON（sort_keys）的 SHA-256（content-addressed）。

用法：
  python3 tools-judge-agreement.py <table.json> [receipt.json]
  python3 tools-judge-agreement.py --selftest [receipt.json]

输入表格式（JSON）：
  {
    "raters": ["human", "checker", "judgeA"],      # >=2
    "labels": ["pass", "fail", "uncertain"],        # 封闭选项集
    "items": [
      {"item_id": "HJ-001",
       "ratings": {"human": "pass", "checker": "fail", "judgeA": null}}
    ]
  }
rating 值 null/缺失/不在 labels 中 => 该 rater 该测项 invalid（计入披露，不参与 κ）。

退出码：0=计算完成；1=输入校验失败或空表；2=环境/参数错误；3=收据目标已存在拒写。

v1（L38 预注册）：首版。演进须修前副本+双 sha256+INTERNAL-TOOLS 同步。
"""

import hashlib
import json
import sys
from itertools import combinations

SCHEMA_VERSION = "judge-agreement-v1"


def canonical_sha256(obj):
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_table(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return None


def validate(table):
    """返回 (raters, labels, items, errors)。errors 非空即 exit 1。"""
    errors = []
    if not isinstance(table, dict):
        return [], [], [], ["table 不是 JSON 对象"]
    raters = table.get("raters")
    labels = table.get("labels")
    items = table.get("items")
    if not isinstance(raters, list) or len(raters) < 2:
        errors.append("raters 需为 >=2 的数组")
    if not isinstance(labels, list) or not labels:
        errors.append("labels 需为非空数组")
    if not isinstance(items, list):
        errors.append("items 需为数组")
    if errors:
        return [], [], [], errors
    if len(set(raters)) != len(raters):
        errors.append("raters 存在重复")
    if len(set(labels)) != len(labels):
        errors.append("labels 存在重复")
    if errors:
        return [], [], [], errors
    seen_ids = set()
    for idx, it in enumerate(items):
        if not isinstance(it, dict) or "ratings" not in it or not isinstance(it["ratings"], dict):
            errors.append(f"items[{idx}] 缺 item_id/ratings 或形态非法")
            continue
        iid = it.get("item_id", f"item-{idx}")
        if iid in seen_ids:
            errors.append(f"item_id 重复: {iid}")
        seen_ids.add(iid)
        for r, v in it["ratings"].items():
            if r not in raters:
                errors.append(f"{iid}: 未知 rater {r}")
            elif v is not None and v not in labels:
                errors.append(f"{iid}: rater {r} 标签 {v!r} 不在封闭选项集")
    if errors:
        return [], [], [], errors
    return raters, labels, items, []


def cohen_kappa(pairs):
    """pairs: [(label_a, label_b)] 均有效。返回 (kappa, po, pe, n)。"""
    n = len(pairs)
    if n == 0:
        return None, None, None, 0
    labels = sorted({x for p in pairs for x in p})
    match = sum(1 for a, b in pairs if a == b)
    po = match / n
    from collections import Counter
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum((ca[k] / n) * (cb.get(k, 0) / n) for k in labels)
    kappa = (po - pe) / (1 - pe) if pe < 1 else (1.0 if po >= 1 else None)
    return kappa, po, pe, n


def fleiss_kappa(ratings_matrix, labels):
    """ratings_matrix: item -> [label per rater]（全有效）。标准 Fleiss。"""
    n_items = len(ratings_matrix)
    if n_items == 0:
        return None
    n_raters = len(ratings_matrix[0])
    if n_raters < 2:
        return None
    total = n_items * n_raters
    p_k = {}
    for lab in labels:
        cnt = sum(row.count(lab) for row in ratings_matrix)
        p_k[lab] = cnt / total
    p_bar = 0.0
    for row in ratings_matrix:
        from collections import Counter
        c = Counter(row)
        p_i = (sum(v * (v - 1) for v in c.values())) / (n_raters * (n_raters - 1))
        p_bar += p_i
    p_bar /= n_items
    p_e = sum(v * v for v in p_k.values())
    if p_e >= 1:
        return 1.0 if p_bar >= 1 else None
    return (p_bar - p_e) / (1 - p_e)


def compute(table):
    raters, labels, items, errors = validate(table)
    if errors:
        return {"errors": errors}, 1
    if not items:
        return {"errors": ["items 为空表（无测项可算）"]}, 1
    # 每 rater 的有效/无效
    valid = {}      # (item_id, rater) -> label
    invalid = {r: [] for r in raters}
    for it in items:
        iid = it.get("item_id", "item")
        for r in raters:
            v = it["ratings"].get(r)
            if v is None or v not in labels:
                invalid[r].append(iid)
            else:
                valid[(iid, r)] = v
    pairwise = {}
    for a, b in combinations(raters, 2):
        pairs = [(valid[(it.get("item_id"), a)], valid[(it.get("item_id"), b)])
                 for it in items
                 if (it.get("item_id"), a) in valid and (it.get("item_id"), b) in valid]
        kappa, po, pe, n = cohen_kappa(pairs)
        # 混淆矩阵
        conf = {la: {lb: 0 for lb in labels} for la in labels}
        for la, lb in pairs:
            conf[la][lb] += 1
        pairwise[f"{a} vs {b}"] = {
            "n_common_valid": n,
            "percent_agreement": round(po, 6) if po is not None else None,
            "p_e": round(pe, 6) if pe is not None else None,
            "cohen_kappa": round(kappa, 6) if kappa is not None else None,
            "confusion_matrix": conf,
        }
    # Fleiss：全 rater 均有效的测项
    fleiss_items = []
    excluded_fleiss = []
    for it in items:
        iid = it.get("item_id", "item")
        row = [valid.get((iid, r)) for r in raters]
        if all(v is not None for v in row):
            fleiss_items.append(row)
        else:
            excluded_fleiss.append(iid)
    fk = fleiss_kappa(fleiss_items, labels)
    payload = {
        "tool": "tools-judge-agreement.py",
        "schema_version": SCHEMA_VERSION,
        "n_items": len(items),
        "n_raters": len(raters),
        "labels": labels,
        "raters": raters,
        "invalid_counts": {r: len(v) for r, v in invalid.items()},
        "invalid_items": {r: v for r, v in invalid.items() if v},
        "pairwise": pairwise,
        "fleiss_kappa": round(fk, 6) if fk is not None else None,
        "fleiss_items_n": len(fleiss_items),
        "fleiss_excluded_items": excluded_fleiss,
        "errors": [],
    }
    return payload, 0


def selftest():
    """合成数据自测：解析解已知。返回 (payload, exit_code)。"""
    checks = []

    def check(name, got, want, tol=1e-6):
        ok = (got is not None and abs(got - want) <= tol) if isinstance(want, float) else (got == want)
        checks.append({"name": name, "got": got, "want": want, "ok": bool(ok)})

    def mk(pairs_ab, labels=("pass", "fail")):
        return {"raters": ["A", "B"], "labels": list(labels),
                "items": [{"item_id": f"i{i}", "ratings": {"A": a, "B": b}}
                          for i, (a, b) in enumerate(pairs_ab)]}

    # T1 完全一致：κ=1.0
    t1 = mk([("pass", "pass")] * 5 + [("fail", "fail")] * 5)
    r1, c1 = compute(t1)
    check("T1 cohen A-B", r1["pairwise"]["A vs B"]["cohen_kappa"], 1.0)
    check("T1 fleiss", r1["fleiss_kappa"], 1.0)
    check("T1 exit", c1, 0)

    # T2 κ=0 解析解 [[25,25],[25,25]]：po=0.5, pe=0.5
    t2 = mk([("pass", "pass")] * 25 + [("pass", "fail")] * 25 +
            [("fail", "pass")] * 25 + [("fail", "fail")] * 25)
    r2, _ = compute(t2)
    check("T2 cohen A-B", r2["pairwise"]["A vs B"]["cohen_kappa"], 0.0)
    check("T2 fleiss(=cohen,n=2)", r2["fleiss_kappa"], 0.0)

    # T3 负 κ：[[10,40],[40,10]] → po=0.2, pe=0.5, κ=-0.6
    t3 = mk([("pass", "pass")] * 10 + [("pass", "fail")] * 40 +
            [("fail", "pass")] * 40 + [("fail", "fail")] * 10)
    r3, _ = compute(t3)
    check("T3 cohen A-B", r3["pairwise"]["A vs B"]["cohen_kappa"], -0.6)

    # T4 三 rater Fleiss 非平凡解析解（构造后手工求值）：
    # 3 rater × 4 items，每 item 分裂 [2 同 + 1 异] → P_i = (2*1)/(3*2)=1/3 → P̄=1/3
    # 边际：每 item 标签占 2/3、1/3 → p_k 合计对 2 标签 = 0.5/0.5 → Pe=0.5 → κ=(1/3-0.5)/0.5=-1/3
    t4 = {"raters": ["A", "B", "C"], "labels": ["pass", "fail"],
          "items": [
              {"item_id": "x1", "ratings": {"A": "pass", "B": "pass", "C": "fail"}},
              {"item_id": "x2", "ratings": {"A": "pass", "B": "pass", "C": "fail"}},
              {"item_id": "x3", "ratings": {"A": "fail", "B": "fail", "C": "pass"}},
              {"item_id": "x4", "ratings": {"A": "fail", "B": "fail", "C": "pass"}},
          ]}
    r4, _ = compute(t4)
    check("T4 fleiss 三 rater", r4["fleiss_kappa"], -1.0 / 3.0)

    # T5 含 invalid：A 缺 1 项 → pairwise n_common_valid=1（设 2 项表），invalid_counts.A=1
    t5 = {"raters": ["A", "B"], "labels": ["pass", "fail"],
          "items": [{"item_id": "a", "ratings": {"A": "pass", "B": "pass"}},
                    {"item_id": "b", "ratings": {"A": None, "B": "fail"}}]}
    r5, _ = compute(t5)
    check("T5 invalid A", r5["invalid_counts"]["A"], 1)
    check("T5 pairwise n", r5["pairwise"]["A vs B"]["n_common_valid"], 1)
    check("T5 fleiss excluded", len(r5["fleiss_excluded_items"]), 1)

    # T6 空表 → exit 1
    r6, c6 = compute({"raters": ["A", "B"], "labels": ["pass"], "items": []})
    check("T6 exit empty", c6, 1)

    # T7 非法标签 → exit 1
    r7, c7 = compute(mk([("maybe", "pass")], labels=("pass", "fail")))
    check("T7 exit bad-label", c7, 1)

    fails = [c for c in checks if not c["ok"]]
    payload = {
        "tool": "tools-judge-agreement.py --selftest",
        "schema_version": SCHEMA_VERSION,
        "fixture": "synthetic analytic-solution suite (T1-T7)",
        "checks_total": len(checks),
        "fail_count": len(fails),
        "fails": fails,
        "errors": [],
    }
    return payload, (0 if not fails else 1)


def write_receipt(path, payload):
    payload = dict(payload)
    payload["receipt_sha256"] = "PENDING"
    payload["receipt_sha256"] = canonical_sha256(payload)
    with open(path, "x", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1, sort_keys=True)
    return payload["receipt_sha256"]


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    selftest_mode = argv[1] == "--selftest"
    if selftest_mode:
        payload, code = selftest()
    else:
        table = load_table(argv[1])
        if table is None:
            print(f"ERROR: 无法读取输入表 {argv[1]}", file=sys.stderr)
            return 2
        payload, code = compute(table)
        if code == 1:
            print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
            return 1
    if len(argv) > 2:
        try:
            receipt_sha = write_receipt(argv[2], payload)
        except FileExistsError:
            print(f"receipt-write-refused: {argv[2]} 已存在", file=sys.stderr)
            return 3
        payload["receipt_sha256"] = receipt_sha
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
