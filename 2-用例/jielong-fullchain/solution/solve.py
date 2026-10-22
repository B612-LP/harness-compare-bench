#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""jielong-fullchain 参考解（oracle）v0.1

这是与 checker.py 互相独立的第二套实现：从 environment/ 三件输入计算
golden 的 resolution.json + plan.json，落到指定运行目录，供 oracle 回归使用。

用法：
    python3 solve.py <out_dir>     # 生成 golden run_dir（含三件输入副本与 meta.json）
    python3 solve.py --verify      # 现算并与 truth.json 期望比对（三方互证之一）
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

CASE_DIR = Path(__file__).resolve().parent
CASE_ROOT = CASE_DIR.parent
ENV_DIR = CASE_ROOT / "environment"
INPUT_NAMES = ["jielong.txt", "peers.json", "orders.json"]
SLOT_A, SLOT_B = "19:00", "20:20"
WINDOW = {SLOT_A: (1140, 1210), SLOT_B: (1220, 1290)}   # 19:00-20:10 / 20:20-21:30（分钟）

LINE_NUM = re.compile(r"(?P<seq>\d{1,3})\s*[.、)）]\s*(?P<body>.*)", re.X)
DATEY = re.compile(r"\d{1,2}[.月]\d{1,2}")
TAIL_CLOCK = re.compile(r"(?P<h>\d{1,2})[:：](?P<m>\d{2})$")
QUALIFIER = re.compile(r"(?P<mark>only|只)?\s*第\s*(?P<n>[0-9一二两])\s*场")
NUM_MAP = {"0": 1, "1": 1, "2": 2, "一": 1, "二": 2, "两": 2}

# 全角→半角折叠表（translate 实现路径，区别于 checker 的逐字符分支）
_FOLD = {0x3000: 0x0020}
_FOLD.update({c: c - 0xFEE0 for c in range(0xFF01, 0xFF5F)})
FOLD_TABLE = dict(_FOLD)

_EMOJI_EDGE = set()
for _lo, _hi in ((0x1F000, 0x1FAFF), (0x2600, 0x27BF), (0x2B00, 0x2BFF)):
    _EMOJI_EDGE.update(range(_lo, _hi + 1))
_EMOJI_EDGE.add(0xFE0F)


def canon(text):
    """归一：全角折叠 → 去首尾 emoji → 收紧空白。"""
    folded = text.translate(FOLD_TABLE)
    lo, hi = 0, len(folded)
    while lo < hi and ord(folded[lo]) in _EMOJI_EDGE:
        lo += 1
    while hi > lo and ord(folded[hi - 1]) in _EMOJI_EDGE:
        hi -= 1
    return " ".join(folded[lo:hi].split())


def load_env():
    blobs = {name: (ENV_DIR / name).read_bytes() for name in INPUT_NAMES}
    return blobs


def resolve_token(body, peers):
    """一行 body（已去行号）→ dict(raw/token/arrival/slots/sid/status/self/candidates)"""
    raw = " ".join(body.split())
    work = raw.translate(FOLD_TABLE)

    arrival = None
    clock = TAIL_CLOCK.search(work)
    if clock:
        hh, mm = int(clock.group("h")), int(clock.group("m"))
        hh = hh + 12 if hh < 12 else hh          # 晚上语境
        arrival = "%02d:%02d" % (hh, mm)
        work = work[:clock.start()]

    slots = [SLOT_A, SLOT_B]
    qual = QUALIFIER.search(work)
    if qual:
        slots = [SLOT_A if NUM_MAP[qual.group("n")] == 1 else SLOT_B]
        work = work[:qual.start()] + work[qual.end():]
    token = " ".join(work.split())

    if arrival:
        hh, mm = int(arrival[:2]), int(arrival[3:])
        mins = hh * 60 + mm
        slots = [SLOT_A if WINDOW[SLOT_A][0] <= mins <= WINDOW[SLOT_A][1] else SLOT_B]

    out = {"raw": raw, "token": token, "arrival": arrival, "slots": slots,
           "sid": None, "status": "unmatched", "self": False, "candidates": []}
    if "朋友" in token:
        return out
    hits = []
    for p in peers["peers"]:
        forms = [p["name"]] + list(p.get("aliases", []))
        if any(raw == f or token == f or canon(raw) == canon(f) or canon(token) == canon(f)
               for f in forms):
            hits.append(p)
    if len(hits) == 1:
        out["status"], out["sid"] = "matched", hits[0]["id"]
        if hits[0]["id"] == peers.get("self_id"):
            out["self"], out["slots"] = True, []
    elif len(hits) > 1:
        out["status"] = "conflict"
        out["candidates"] = [p["id"] for p in hits]
    return out


def solve(blobs):
    peers = json.loads(blobs["peers.json"].decode("utf-8"))
    orders_cfg = json.loads(blobs["orders.json"].decode("utf-8"))
    entries = []
    for line in blobs["jielong.txt"].decode("utf-8").splitlines():
        s = line.strip()
        if (not s or s.startswith("#") or s.startswith("——")
                or s == "参与接龙" or DATEY.match(s)):
            continue
        m = LINE_NUM.match(s)
        if not m:
            continue
        info = resolve_token(m.group("body"), peers)
        info["seq"] = int(m.group("seq"))
        entries.append(info)

    def note_for(info):
        if info["status"] == "conflict":
            return "重名歧义：候选 %s，需用户指定，不许猜" % " / ".join(info["candidates"])
        if info["status"] == "unmatched":
            return "泛称或昵称未登记（零命中），需回问/补录，不许猜"
        if info["self"]:
            return "本人（发起人），跳过不加"
        if info["arrival"]:
            return "到达备注 %s（晚上语境归一），归入 %s" % (info["arrival"], info["slots"][0])
        return "命中别名表，两场都加" if len(info["slots"]) == 2 else "命中别名表"

    resolution = [{"seq": e["seq"], "raw": e["raw"], "sid": e["sid"], "status": e["status"],
                   "slots": e["slots"], "note": note_for(e)} for e in entries]

    capacity = int(orders_cfg["capacity_per_order"])
    orders = orders_cfg["orders"]
    state = {o["orderNo"]: {"add": [], "skip": [], "reject": []} for o in orders}
    for start in dict.fromkeys(o["startTime"] for o in orders):
        here = [o for o in orders if o["startTime"] == start]
        for e in entries:
            if e["status"] != "matched" or e["self"] or start not in e["slots"]:
                continue
            dup = next((o for o in here if e["sid"] in o["peers"]), None)
            if dup is not None:
                state[dup["orderNo"]]["skip"].append(e["sid"])
                continue
            rest = [o for o in here if o["blockType"] == 2
                    and len(o["peers"]) + len(state[o["orderNo"]]["add"]) < capacity]
            if rest:
                state[rest[0]["orderNo"]]["add"].append(e["sid"])
                continue
            bad = next((o for o in here if o["blockType"] != 2), here[-1])
            state[bad["orderNo"]]["reject"].append(e["sid"])

    plan = []
    for o in orders:
        st = state[o["orderNo"]]
        if st["reject"]:
            reason = ("散场订单（blockType≠2）不可加同伴；本场次溢出人员无处可加，待用户决定"
                      if o["blockType"] != 2 else
                      "本场次包场单均已满（每单上限 %d 人）；溢出人员待用户决定" % capacity)
        else:
            reason = "按先A后B与每单上限 %d 人分单" % capacity
        plan.append({"orderNo": o["orderNo"], "reason": reason, **st})
    return resolution, plan


def project(rows, plan):
    return ([{k: r[k] for k in ("seq", "raw", "sid", "status", "slots")} for r in rows],
            [{k: p[k] for k in ("orderNo", "add", "skip", "reject")} for p in plan])


def verify():
    truth = json.loads((CASE_ROOT / "truth.json").read_text(encoding="utf-8"))
    rows, plan = solve(load_env())
    exp_rows, exp_plan = project(rows, plan)
    bad = []
    if exp_rows != truth["expected_resolution"]:
        for i, (a, b) in enumerate(zip(exp_rows, truth["expected_resolution"])):
            if a != b:
                bad.append("resolution[%d]: solve=%r truth=%r" % (i, a, b))
    if exp_plan != truth["expected_plan"]:
        for i, (a, b) in enumerate(zip(exp_plan, truth["expected_plan"])):
            if a != b:
                bad.append("plan[%d]: solve=%r truth=%r" % (i, a, b))
    for name in INPUT_NAMES:
        digest = hashlib.sha256((ENV_DIR / name).read_bytes()).hexdigest()
        if digest != truth["inputs"][name]:
            bad.append("input %s sha drift" % name)
    if bad:
        print("VERIFY FAIL\n  " + "\n  ".join(bad[:10]))
        return 1
    print("VERIFY OK：solve.py 现算与 truth.json 完全一致（%d 行 / %d 单）"
          % (len(exp_rows), len(exp_plan)))
    return 0


def main(argv):
    parser = argparse.ArgumentParser(description="jielong-fullchain 参考解（oracle）")
    parser.add_argument("out_dir", nargs="?", help="golden 运行目录输出位置")
    parser.add_argument("--verify", action="store_true", help="与 truth.json 互证后退出")
    args = parser.parse_args(argv)
    if args.verify:
        return verify()
    if not args.out_dir:
        parser.error("缺少 out_dir（或使用 --verify）")
    blobs = load_env()
    resolution, plan = solve(blobs)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "resolution.json").write_bytes(
        (json.dumps(resolution, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    (out / "plan.json").write_bytes(
        (json.dumps(plan, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    for name in INPUT_NAMES:
        shutil.copyfile(ENV_DIR / name, out / name)
    (out / "meta.json").write_text(json.dumps({
        "case_id": "jielong-fullchain",
        "product": "solution/solve.py（oracle 参考解）",
        "version": "0.1",
        "note": "参考解生成的 golden 运行目录",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("golden 已生成：%s（resolution %d 行 / plan %d 单）" % (out, len(resolution), len(plan)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
