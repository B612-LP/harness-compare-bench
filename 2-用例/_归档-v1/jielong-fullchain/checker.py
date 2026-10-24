#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""jielong-fullchain 轻量判卷器 v0.1（2026-10-22）

用法：
    python3 checker.py <run_dir> [--json]
    python3 checker.py --selftest

run_dir 约定（见 spec.md）：
    resolution.json            必需产物：逐人解析表（也接受 run_dir/output/、run_dir/outputs/ 下同名文件）
    plan.json                  必需产物：逐单分单计划（同上）
    jielong.txt / peers.json / orders.json
                               可选输入副本（run_dir 根、input/、inputs/、environment/ 均可）；
                               附带则与 canonical 比对 SHA-256，任何一件被改 → 直接 0
    meta.json                  可选运行元信息，不参与判分

口径：
    binary：全 PASS=1，任一 FAIL=0；逐项权重仅作加权参考（partial ≤10 换算 weighted/10）。
    输入完整性：三件副本全附且一致 → verified；缺件 → unverified（不扣分）；任一件不一致 → fail（判 0）。
    用例自身一致性：canonical 输入 SHA 与期望值都记录在 truth.json，启动即复算，漂移 → 退出码 2。
"""
import argparse
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path

CASE_ID = "jielong-fullchain"
CHECKER_VERSION = "0.1"
BINARY = True
CASE_DIR = Path(__file__).resolve().parent

INPUT_NAMES = ["jielong.txt", "peers.json", "orders.json"]
SLOT1 = "19:00"
SLOT2 = "20:20"
SLOT_BOTH = [SLOT1, SLOT2]
ROW_KEYS = {"seq", "raw", "sid", "status", "slots", "note"}
PLAN_KEYS = {"orderNo", "add", "skip", "reject", "reason"}
GENERIC_WORD = "朋友"          # 代报名泛称判别词（先于别名映射）
STATUS_SET = {"matched", "unmatched", "conflict"}

ITEMS = [
    ("artifacts_exist", "产物存在（resolution.json + plan.json）", 8),
    ("input_integrity", "输入完整性（守卫，三件输入副本）", 12),
    ("resolution_schema", "resolution.json 结构与字段类型", 10),
    ("resolution_rows", "resolution 行集（seq 唯一升序 + raw 原文）", 8),
    ("resolution_match", "逐人映射 sid+status（含四处不许猜）", 18),
    ("resolution_slots", "逐人场次（9:00 到达 / only 第２场 / 本人空）", 12),
    ("resolution_notes", "note 规则（冲突列候选 / 到达归一时刻 / 待人工非空）", 7),
    ("plan_schema", "plan.json 结构与单序", 6),
    ("plan_assignment", "逐单 add/skip/reject（先A后B / 容量 / 幂等）", 15),
    ("plan_guards", "计划守卫（散场拒收 / 容量上限 / reject 带 reason）", 4),
]
WEIGHT_OF = dict((i[0], i[2]) for i in ITEMS)
TITLE_OF = dict((i[0], i[1]) for i in ITEMS)


# ---------------------------------------------------------------- utilities

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def load_truth(case_dir=CASE_DIR):
    return json.loads((case_dir / "truth.json").read_text(encoding="utf-8"))


def load_case(case_dir=CASE_DIR):
    """读 canonical 输入并用 truth.json 记录的 SHA-256 校验用例自身未被改动。"""
    truth = load_truth(case_dir)
    canonical = {}
    for name in INPUT_NAMES:
        data = (case_dir / "environment" / name).read_bytes()
        actual = sha256_bytes(data)
        if actual != truth["inputs"][name]:
            raise SystemExit(
                "ERROR: 用例 canonical 输入与 truth 记录不一致：%s\n  truth=%s\n  actual=%s"
                % (case_dir / "environment" / name, truth["inputs"][name], actual))
        canonical[name] = data
    return truth, canonical


def find_file(run_dir, name):
    for cand in (run_dir / name, run_dir / "output" / name, run_dir / "outputs" / name):
        if cand.is_file():
            return cand
    return None


def find_input(run_dir, name):
    for cand in (run_dir / name, run_dir / "input" / name,
                 run_dir / "inputs" / name, run_dir / "environment" / name):
        if cand.is_file():
            return cand
    return None


# ------------------------------------------- 规则实现 A（判卷器独立实现）

SEQ_RE = re.compile(r"^\s*(\d{1,3})\s*[.、)）]\s*(.*)$")
DATELINE_RE = re.compile(r"^\s*\d{1,2}[.月]\d{1,2}")       # 「10.19…」形态的日期标题行（含笔误头）
ARRIVE_RE = re.compile(r"(\d{1,2})[:：](\d{2})\s*$")        # 行尾到达时刻
QUAL_RE = re.compile(r"(?:only|只)?\s*第\s*([0-9一二两])\s*场")
CN_DIGIT = {"0": 1, "1": 1, "2": 2, "一": 1, "二": 2, "两": 2}
SLOT_WINDOWS = {SLOT1: (19 * 60, 20 * 60 + 10), SLOT2: (20 * 60 + 20, 21 * 60 + 30)}


def fold_fullwidth(text):
    out = []
    for ch in text:
        code = ord(ch)
        if ch == "\u3000":
            out.append(" ")
        elif 0xFF01 <= code <= 0xFF5E:
            out.append(chr(code - 0xFEE0))
        else:
            out.append(ch)
    return "".join(out)


def _is_emoji_char(ch):
    code = ord(ch)
    return (0x1F000 <= code <= 0x1FAFF or 0x2600 <= code <= 0x27BF
            or 0x2B00 <= code <= 0x2BFF or code == 0xFE0F)


def strip_edge_emoji(text):
    start, end = 0, len(text)
    while start < end and _is_emoji_char(text[start]):
        start += 1
    while end > start and _is_emoji_char(text[end - 1]):
        end -= 1
    return text[start:end]


def normalize_token(text):
    return strip_edge_emoji(fold_fullwidth(text)).strip()


def _match_peers(token, raw, peer_list):
    """匹配 = 原文相同 或 归一后相同（name 与 aliases 两侧同规则归一）。
    token 为去限定语/到达时刻后的昵称原文（保留 emoji），raw 为整段行尾原文兜底。"""
    cands = []
    for p in peer_list:
        for stored in [p.get("name", "")] + list(p.get("aliases", [])):
            if (raw == stored or token == stored
                    or normalize_token(raw) == normalize_token(stored)
                    or normalize_token(token) == normalize_token(stored)):
                cands.append(p)
                break
    return cands


def parse_jielong(raw_text, peers_cfg):
    """解析接龙 → 内部行列表（含供 note 规则使用的内部字段）。"""
    self_id = peers_cfg.get("self_id")
    peer_list = peers_cfg.get("peers", [])
    rows = []
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("——"):
            continue
        if stripped == "参与接龙" or DATELINE_RE.match(stripped):
            continue
        m = SEQ_RE.match(line)
        if not m:
            continue
        seq = int(m.group(1))
        raw = m.group(2).strip()
        work = fold_fullwidth(raw)

        arrival = None
        am = ARRIVE_RE.search(work)
        if am:
            hh, mm = int(am.group(1)), int(am.group(2))
            if hh < 12:
                hh += 12                     # 晚上语境：9:00 → 21:00
            arrival = "%02d:%02d" % (hh, mm)
            work = work[:am.start()].rstrip()

        slots = SLOT_BOTH[:]
        qm = QUAL_RE.search(work)
        if qm:
            number = CN_DIGIT.get(qm.group(1))
            work = (work[:qm.start()] + work[qm.end():]).strip()
            slots = [SLOT1 if number == 1 else SLOT2]

        token = work.strip()
        if arrival:
            minutes = int(arrival[:2]) * 60 + int(arrival[3:])
            lo, hi = SLOT_WINDOWS[SLOT1]
            slots = [SLOT1 if lo <= minutes <= hi else SLOT2]

        row = {"seq": seq, "raw": raw, "token": token, "arrival": arrival,
               "slots": slots, "sid": None, "status": "unmatched",
               "self": False, "generic": False, "candidates": []}

        if GENERIC_WORD in token:            # 泛称：先于别名映射，不许猜
            row["generic"] = True
            rows.append(row)
            continue
        cands = _match_peers(token, raw, peer_list)
        if len(cands) > 1:
            row["status"] = "conflict"
            row["candidates"] = [p["id"] for p in cands]
        elif len(cands) == 1:
            row["status"] = "matched"
            row["sid"] = cands[0]["id"]
            if cands[0]["id"] == self_id:
                row["self"] = True
                row["slots"] = []
        rows.append(row)
    return rows


def build_expected_plan(rows, orders_cfg):
    """分单：每场次按 orders.json 顺序先 A 后 B；每单 现有同伴+新增 ≤ capacity；
    已在单内 → skip（幂等）；散场（blockType≠2）拒收；无处可加按归属记 reject。"""
    capacity = int(orders_cfg.get("capacity_per_order", 7))
    orders = orders_cfg["orders"]
    plan = [{"orderNo": o["orderNo"], "add": [], "skip": [], "reject": [], "reason": ""}
            for o in orders]
    index_by_no = dict((p["orderNo"], i) for i, p in enumerate(plan))
    sessions = []
    for o in orders:
        if o["startTime"] not in sessions:
            sessions.append(o["startTime"])
    for start in sessions:
        session_orders = [o for o in orders if o["startTime"] == start]
        for row in rows:
            if row["status"] != "matched" or row["self"]:
                continue
            sid = row["sid"]
            if start not in row["slots"]:
                continue
            skip_target = None
            for o in session_orders:
                if sid in o["peers"]:
                    skip_target = o
                    break
            if skip_target is not None:
                plan[index_by_no[skip_target["orderNo"]]]["skip"].append(sid)
                continue
            placed = False
            refused = None
            for o in session_orders:
                entry = plan[index_by_no[o["orderNo"]]]
                if int(o.get("blockType", 2)) != 2:
                    if refused is None:
                        refused = o
                    continue
                if len(o["peers"]) + len(entry["add"]) < capacity:
                    entry["add"].append(sid)
                    placed = True
                    break
            if not placed:
                target = refused if refused is not None else session_orders[-1]
                entry = plan[index_by_no[target["orderNo"]]]
                entry["reject"].append(sid)
                if refused is not None:
                    entry["reason"] = "散场订单（blockType≠2）不可加同伴；本场次溢出人员无处可加，待用户决定"
                else:
                    entry["reason"] = "本场次包场单均已满（每单上限 %d 人）；溢出人员待用户决定" % capacity
    for p in plan:
        if p["reject"] and not p["reason"]:
            p["reason"] = "存在被拒收人员，需说明原因"
    return plan


def public_row(row):
    return {"seq": row["seq"], "raw": row["raw"], "sid": row["sid"],
            "status": row["status"], "slots": row["slots"], "note": ""}


def ensure_truth_consistency(truth, rows, exp_plan):
    """truth 交叉校验：判卷器现算期望 vs truth.json 期望，漂移 → 退出码 2。"""
    errors = []
    t_rows = truth.get("expected_resolution", [])
    if len(t_rows) != len(rows):
        errors.append("expected_resolution 行数 %d != 现算 %d" % (len(t_rows), len(rows)))
    else:
        for tr, row in zip(t_rows, rows):
            for key in ("seq", "raw", "sid", "status", "slots"):
                if tr.get(key) != row[key]:
                    errors.append("expected_resolution seq %s 字段 %s：truth=%r 现算=%r"
                                  % (tr.get("seq"), key, tr.get(key), row[key]))
    t_plan = truth.get("expected_plan", [])
    if len(t_plan) != len(exp_plan):
        errors.append("expected_plan 单数 %d != 现算 %d" % (len(t_plan), len(exp_plan)))
    else:
        for tp, ep in zip(t_plan, exp_plan):
            for key in ("orderNo", "add", "skip", "reject"):
                if tp.get(key) != ep[key]:
                    errors.append("expected_plan %s 字段 %s：truth=%r 现算=%r"
                                  % (tp.get("orderNo"), key, tp.get(key), ep[key]))
    if errors:
        raise SystemExit("ERROR: truth.json 与判卷器现算期望不一致（用例自身漂移）：\n  "
                         + "\n  ".join(errors))


# ---------------------------------------------------------------- judging

def _item(item_id, ok, detail):
    return {"id": item_id, "title": TITLE_OF[item_id], "weight": WEIGHT_OF[item_id],
            "status": "pass" if ok else "fail", "detail": detail}


def _unknown_item(item_id, detail):
    return {"id": item_id, "title": TITLE_OF[item_id], "weight": WEIGHT_OF[item_id],
            "status": "unknown", "detail": detail}


def rows_schema_errors(prod_rows, expected_len):
    errs = []
    if not isinstance(prod_rows, list):
        return ["resolution.json 顶层必须是 JSON 数组"]
    if len(prod_rows) != expected_len:
        errs.append("行数 %d != 期望 %d" % (len(prod_rows), expected_len))
    for idx, row in enumerate(prod_rows):
        if not isinstance(row, dict):
            errs.append("第 %d 行不是对象" % (idx + 1))
            continue
        keys = set(row)
        if keys != ROW_KEYS:
            missing = sorted(ROW_KEYS - keys)
            extra = sorted(keys - ROW_KEYS)
            errs.append("第 %d 行字段不符（缺 %s 多 %s）" % (idx + 1, missing, extra))
            continue
        if type(row["seq"]) is not int:
            errs.append("第 %d 行 seq 必须是整数" % (idx + 1))
        if not isinstance(row["raw"], str):
            errs.append("第 %d 行 raw 必须是字符串" % (idx + 1))
        if row["sid"] is not None and not isinstance(row["sid"], str):
            errs.append("第 %d 行 sid 必须是字符串或 null" % (idx + 1))
        if row["status"] not in STATUS_SET:
            errs.append("第 %d 行 status 非法：%r" % (idx + 1, row["status"]))
        if not isinstance(row["slots"], list) or any(not isinstance(s, str) for s in row["slots"]):
            errs.append("第 %d 行 slots 必须是字符串数组" % (idx + 1))
        elif sorted(set(row["slots"])) != sorted(row["slots"]) or any(
                s not in (SLOT1, SLOT2) for s in row["slots"]):
            errs.append("第 %d 行 slots 取值须为 %s/%s 且升序去重" % (idx + 1, SLOT1, SLOT2))
        if not isinstance(row["note"], str):
            errs.append("第 %d 行 note 必须是字符串" % (idx + 1))
    return errs


def judge(run_dir):
    truth, canonical = load_case()
    peers_cfg = json.loads(canonical["peers.json"].decode("utf-8"))
    orders_cfg = json.loads(canonical["orders.json"].decode("utf-8"))
    rows = parse_jielong(canonical["jielong.txt"].decode("utf-8"), peers_cfg)
    exp_rows = [public_row(r) for r in rows]
    exp_plan = build_expected_plan(rows, orders_cfg)
    ensure_truth_consistency(truth, rows, exp_plan)

    items = []
    details = {"people_total": len(rows)}
    details["matched_total"] = sum(1 for r in rows if r["status"] == "matched" and not r["self"])
    details["unmatched_total"] = sum(1 for r in rows if r["status"] == "unmatched")
    details["conflict_total"] = sum(1 for r in rows if r["status"] == "conflict")

    # ① 产物存在
    res_path = find_file(run_dir, "resolution.json")
    plan_path = find_file(run_dir, "plan.json")
    if res_path is None or plan_path is None:
        missing = [n for n, p in (("resolution.json", res_path), ("plan.json", plan_path)) if p is None]
        items.append(_item("artifacts_exist", False, "缺少产物: " + ", ".join(missing)))
        for item_id, _t, _w in ITEMS[1:]:
            items.append(_item(item_id, False, "产物缺失，无法检查"))
        return _result(items, run_dir=run_dir, integrity="unverified", details=details)
    items.append(_item("artifacts_exist", True, "resolution=%s; plan=%s" % (res_path, plan_path)))

    # ② 输入完整性守卫
    mismatched, attached = [], 0
    for name in INPUT_NAMES:
        path = find_input(run_dir, name)
        if path is None:
            continue
        attached += 1
        if sha256_bytes(path.read_bytes()) != truth["inputs"][name]:
            mismatched.append(name)
    if mismatched:
        integrity = "mismatch"
        items.append(_item("input_integrity", False,
                           "输入被修改: %s（判 0）" % ", ".join(mismatched)))
    elif attached == len(INPUT_NAMES):
        integrity = "verified"
        items.append(_item("input_integrity", True, "三件输入副本与 canonical 字节一致"))
    else:
        integrity = "unverified"
        items.append(_unknown_item("input_integrity",
                                   "仅附 %d/3 件输入副本，未核验部分不扣分（请在运行记录中说明）" % attached))

    # ③ resolution.json
    prod_rows = None
    try:
        prod_rows = json.loads(res_path.read_bytes().decode("utf-8"))
    except Exception as exc:
        items.append(_item("resolution_schema", False, "resolution.json 解析失败: %s" % exc))
    if prod_rows is not None:
        errs = rows_schema_errors(prod_rows, len(exp_rows))
        items.append(_item("resolution_schema", not errs, "; ".join(errs[:6]) or "结构与字段类型通过"))

        aligned = (not errs and isinstance(prod_rows, list)
                   and [r.get("seq") for r in prod_rows] == [e["seq"] for e in exp_rows])
        if aligned:
            items.append(_item("resolution_rows", True,
                               "seq 1..%d 升序且 raw 原文逐行一致" % len(exp_rows)))
        else:
            why = []
            if isinstance(prod_rows, list):
                seqs = [r.get("seq") for r in prod_rows if isinstance(r, dict)]
                if seqs != [e["seq"] for e in exp_rows]:
                    why.append("seq 序列 %s != 期望 %s" % (seqs[:15], [e["seq"] for e in exp_rows]))
                raw_bad = [str(r.get("seq")) + ":" + repr(r.get("raw"))
                           for r, e in zip(prod_rows, exp_rows)
                           if isinstance(r, dict) and len(prod_rows) == len(exp_rows) and r.get("raw") != e["raw"]]
                if raw_bad:
                    why.append("raw 不符 → " + "; ".join(raw_bad[:4]))
            items.append(_item("resolution_rows", False, "; ".join(why) or "行结构不齐，无法对齐"))

        # 映射 sid + status
        match_errs, slot_errs, note_errs = [], [], []
        if aligned:
            for prod, internal in zip(prod_rows, rows):
                if prod.get("sid") != internal["sid"] or prod.get("status") != internal["status"]:
                    match_errs.append("seq %s：期望 %s/%s，实际 %s/%s"
                                      % (internal["seq"], internal["status"], internal["sid"],
                                         prod.get("status"), prod.get("sid")))
                if prod.get("slots") != internal["slots"]:
                    slot_errs.append("seq %s：期望 %s，实际 %s"
                                     % (internal["seq"], internal["slots"], prod.get("slots")))
                note = prod.get("note")
                checks = []
                if internal["status"] == "conflict":
                    checks.append(("非空", bool(note)))
                    for cid in internal["candidates"]:
                        checks.append(("列出候选学号 %s" % cid,
                                       isinstance(note, str) and cid in note))
                if internal["status"] == "unmatched":
                    checks.append(("非空（说明待人工原因）", bool(note)))
                if internal["self"]:
                    checks.append(("非空（注明本人跳过）", bool(note)))
                if internal["arrival"]:
                    checks.append(("含归一时刻 %s" % internal["arrival"],
                                   isinstance(note, str) and internal["arrival"] in note))
                for label, ok in checks:
                    if not ok:
                        note_errs.append("seq %s note 未满足：%s" % (internal["seq"], label))
        else:
            match_errs.append("行未对齐，无法逐人比对")
            slot_errs.append("行未对齐，无法逐人比对")
            note_errs.append("行未对齐，无法逐人比对")
        items.append(_item("resolution_match", not match_errs, "; ".join(match_errs[:6]) or "13 人 sid/status 全对"))
        items.append(_item("resolution_slots", not slot_errs, "; ".join(slot_errs[:6]) or "13 人场次全对"))
        items.append(_item("resolution_notes", not note_errs, "; ".join(note_errs[:6]) or "note 规则全满足"))

    # ④ plan.json
    prod_plan = None
    try:
        prod_plan = json.loads(plan_path.read_bytes().decode("utf-8"))
    except Exception as exc:
        items.append(_item("plan_schema", False, "plan.json 解析失败: %s" % exc))
    expected_nos = [o["orderNo"] for o in orders_cfg["orders"]]
    plan_aligned = False
    if prod_plan is not None:
        errs = []
        if not isinstance(prod_plan, list):
            errs.append("plan.json 顶层必须是 JSON 数组")
        elif len(prod_plan) != len(expected_nos):
            errs.append("单数 %d != 期望 %d" % (len(prod_plan), len(expected_nos)))
        else:
            for idx, entry in enumerate(prod_plan):
                if not isinstance(entry, dict):
                    errs.append("第 %d 项不是对象" % (idx + 1))
                    continue
                if set(entry) != PLAN_KEYS:
                    errs.append("第 %d 项字段不符（缺 %s 多 %s）"
                                % (idx + 1, sorted(PLAN_KEYS - set(entry)), sorted(set(entry) - PLAN_KEYS)))
                    continue
                if entry["orderNo"] != expected_nos[idx]:
                    errs.append("第 %d 项 orderNo=%s != 期望 %s（须按 orders.json 顺序）"
                                % (idx + 1, entry["orderNo"], expected_nos[idx]))
                for key in ("add", "skip", "reject"):
                    if not isinstance(entry[key], list) or any(not isinstance(v, str) for v in entry[key]):
                        errs.append("第 %d 项 %s 必须是字符串数组" % (idx + 1, key))
                if not isinstance(entry["reason"], str):
                    errs.append("第 %d 项 reason 必须是字符串" % (idx + 1))
        plan_aligned = not errs
        items.append(_item("plan_schema", plan_aligned, "; ".join(errs[:6]) or "4 单结构、单序、字段类型通过"))

    guard_errs = []
    if prod_plan is not None and plan_aligned:
        for entry, ep in zip(prod_plan, exp_plan):
            for key in ("add", "skip", "reject"):
                if entry[key] != ep[key]:
                    guard_errs.append("%s %s：期望 %s，实际 %s" % (entry["orderNo"], key, ep[key], entry[key]))
        items.append(_item("plan_assignment", not guard_errs,
                           "; ".join(guard_errs[:6]) or "4 单 add/skip/reject 逐项一致"))
    else:
        guard_errs.append("plan 结构不齐")
        items.append(_item("plan_assignment", False, "plan 结构不齐，无法逐单比对"))

    if prod_plan is not None and isinstance(prod_plan, list) and plan_aligned:
        capacity = int(orders_cfg.get("capacity_per_order", 7))
        hard_errs = []
        for entry, o in zip(prod_plan, orders_cfg["orders"]):
            if int(o.get("blockType", 2)) != 2 and entry["add"]:
                hard_errs.append("%s 是散场单（blockType≠2）仍安排 add" % entry["orderNo"])
            if int(o.get("blockType", 2)) == 2 and len(o["peers"]) + len(entry["add"]) > capacity:
                hard_errs.append("%s 超员：现有 %d + 新增 %d > %d"
                                 % (entry["orderNo"], len(o["peers"]), len(entry["add"]), capacity))
            if set(entry["add"]) & set(o["peers"]):
                hard_errs.append("%s add 含已在单内的人（应 skip_existing）" % entry["orderNo"])
            if entry["reject"] and not entry["reason"].strip():
                hard_errs.append("%s reject 非空但 reason 为空" % entry["orderNo"])
        items.append(_item("plan_guards", not hard_errs,
                           "; ".join(hard_errs[:6]) or "散场拒收/容量/reason 守卫通过"))

    details["add_total"] = sum(len(e.get("add", [])) for e in prod_plan) if isinstance(prod_plan, list) else None
    details["skip_total"] = sum(len(e.get("skip", [])) for e in prod_plan) if isinstance(prod_plan, list) else None
    details["reject_total"] = sum(len(e.get("reject", [])) for e in prod_plan) if isinstance(prod_plan, list) else None
    return _result(items, run_dir=run_dir, integrity=integrity, details=details)


def _result(items, *, run_dir, integrity, details=None):
    failed = [i for i in items if i["status"] == "fail"]
    weighted = sum(i["weight"] for i in items if i["status"] == "pass")
    return {
        "case_id": CASE_ID,
        "checker_version": CHECKER_VERSION,
        "binary": BINARY,
        "run_dir": str(run_dir),
        "items": items,
        "failed": [i["id"] for i in failed],
        "reward": 0 if failed else 1,
        "weighted": weighted,
        "max_weight": sum(i[2] for i in ITEMS),
        "input_integrity": integrity,
        **(details or {}),
    }


def render(result):
    lines = ["[%s] checker v%s  run_dir=%s" % (CASE_ID, CHECKER_VERSION, result["run_dir"])]
    for item in result["items"]:
        status = {"pass": "PASS", "fail": "FAIL", "unknown": "UNKNOWN"}[item["status"]]
        lines.append("%-7s %-18s %3d/100  %s" % (status, item["id"], item["weight"], item["detail"]))
    lines.append("REWARD %d (binary)   WEIGHTED %d/%d   INPUT %s"
                 % (result["reward"], result["weighted"], result["max_weight"], result["input_integrity"]))
    return "\n".join(lines)


# ---------------------------------------------------------------- selftest

def golden_note(row):
    if row["status"] == "conflict":
        return "重名候选：" + " / ".join(row["candidates"]) + "，需用户指定"
    if row["status"] == "unmatched":
        return "待人工：泛称或昵称未登记，需回问/补录，不许猜"
    if row["self"]:
        return "本人（发起人），跳过"
    if row["arrival"]:
        return "到达 " + row["arrival"]
    return ""


def build_golden(rows, orders_cfg):
    resolution = []
    for row in rows:
        resolution.append({"seq": row["seq"], "raw": row["raw"], "sid": row["sid"],
                           "status": row["status"], "slots": row["slots"],
                           "note": golden_note(row)})
    plan = build_expected_plan(rows, orders_cfg)
    for entry in plan:
        if not entry["reason"]:
            entry["reason"] = "按先A后B与每单上限 7 人分单"
    return resolution, plan


def selftest():
    truth, canonical = load_case()
    peers_cfg = json.loads(canonical["peers.json"].decode("utf-8"))
    orders_cfg = json.loads(canonical["orders.json"].decode("utf-8"))
    rows = parse_jielong(canonical["jielong.txt"].decode("utf-8"), peers_cfg)
    golden_res, golden_plan = build_golden(rows, orders_cfg)
    ensure_truth_consistency(truth, rows, build_expected_plan(rows, orders_cfg))

    def dumps(obj):
        return (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    def seq_row(resolution, seq):
        for row in resolution:
            if row["seq"] == seq:
                return row
        raise KeyError(seq)

    def plan_entry(plan, order_no):
        for entry in plan:
            if entry["orderNo"] == order_no:
                return entry
        raise KeyError(order_no)

    fixtures = []

    def add(name, expect, res=None, plan=None, tamper=None):
        fixtures.append((name, expect, res if res is not None else golden_res,
                         plan if plan is not None else golden_plan, tamper))

    # 1 golden：必须满分
    add("golden：规范产物（13 人全对 + 4 单全对）", 1)
    # 2 编造学号：零命中的人硬给了一个不存在的 sid
    res = json.loads(json.dumps(golden_res))
    seq_row(res, 13).update({"sid": "2025000999", "status": "matched", "note": ""})
    add("编造学号：海獭🦦 unmatched 被编成 matched/2025000999", 0, res=res)
    # 3 重名猜了：conflict 行擅自选了一个候选学号
    res = json.loads(json.dumps(golden_res))
    seq_row(res, 11).update({"sid": "2025000142", "status": "matched", "note": ""})
    add("重名猜了：小鹿 conflict 被擅自定为 2025000142", 0, res=res)
    # 4 超员硬塞：把 19:00 的 5 个人全塞进只剩 2 位的一单
    plan = json.loads(json.dumps(golden_plan))
    plan_entry(plan, "SZTUODR-20261022-0001")["add"] = [
        "2025000103", "2025000104", "2025000105", "2025000106", "2025000107"]
    plan_entry(plan, "SZTUODR-20261022-0002")["add"] = []
    add("超员硬塞：单0001 塞 5 人（5+5>7）", 0, plan=plan)
    # 5 泛称给了学号
    res = json.loads(json.dumps(golden_res))
    seq_row(res, 8).update({"sid": "2025000106", "status": "matched", "note": ""})
    add("泛称给了学号：朋友帮带 unmatched 被编成 matched", 0, res=res)
    # 6 日期笔误当成两天：整份计划被标题日期带偏成空计划
    plan = json.loads(json.dumps(golden_plan))
    for entry in plan:
        entry.update({"add": [], "skip": [], "reject": [],
                      "reason": "接龙标题日期为10.19，无当日订单，不处理"})
    add("日期笔误当成两天：标题 10.19 带偏成全空计划", 0, plan=plan)
    # 7 skip 的人被重复加
    plan = json.loads(json.dumps(golden_plan))
    plan_entry(plan, "SZTUODR-20261022-0002")["add"] = [
        "2025000101", "2025000105", "2025000106", "2025000107"]
    add("skip 的人被重复加：2025000101 已在单内仍 add", 0, plan=plan)
    # 8 缺 unmatched：直接丢掉解析不出的行
    res = [row for row in json.loads(json.dumps(golden_res)) if row["seq"] != 13]
    add("缺 unmatched：海獭🦦 被静默丢弃（12 行）", 0, res=res)
    # 9 9:00 当成场次
    res = json.loads(json.dumps(golden_res))
    seq_row(res, 2)["slots"] = ["19:00"]
    add("9:00 当成场次：温泉蛋 被排进 19:00", 0, res=res)
    # 10 篡改输入后自洽作答
    add("篡改输入：peers.json 副本被改（守卫判 0）", 0, tamper="peers.json")

    failures = 0
    print("[%s] checker v%s 自测（canonical sha jielong=%s…）"
          % (CASE_ID, CHECKER_VERSION, truth["inputs"]["jielong.txt"][:12]))
    for name, expect, res, plan, tamper in fixtures:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "resolution.json").write_bytes(dumps(res))
            (run_dir / "plan.json").write_bytes(dumps(plan))
            for input_name in INPUT_NAMES:
                data = canonical[input_name]
                if tamper == input_name:
                    data = data + b"\n"     # 追加一个字节即视为被改
                (run_dir / input_name).write_bytes(data)
            result = judge(run_dir)
            ok = result["reward"] == expect
            failures += 0 if ok else 1
            print("  %s  %s: reward=%d（期望 %d）%s"
                  % ("PASS" if ok else "FAIL", name, result["reward"], expect,
                     ("；失败项=" + ",".join(result["failed"])) if result["failed"] else ""))
    print("负控制自测：%s" % ("通过" if failures == 0 else "%d 项不符合预期" % failures))
    return 0 if failures == 0 else 2


def main(argv):
    parser = argparse.ArgumentParser(description="jielong-fullchain 轻量判卷器 v%s" % CHECKER_VERSION)
    parser.add_argument("run_dir", nargs="?", help="运行目录（含 resolution.json / plan.json，可选三件输入副本）")
    parser.add_argument("--json", action="store_true", help="只输出 JSON")
    parser.add_argument("--selftest", action="store_true", help="负控制/守卫自测")
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
