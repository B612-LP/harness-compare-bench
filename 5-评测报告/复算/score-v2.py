#!/usr/bin/env python3
"""评分方案 v2.1：四维评分 + D3 稳健性（n=3 已并入 CLI，桌面按 n=1 初值标 provisional）。python3 score-v2.py

数据：v2-data.json 的每格字段
  pass_rate     达标率（n 场里 reward=1 的占比）
  weighted_mean 半程分均值
  steps_mean    工具调用次数均值
  n             样本数（1 = 未重复，用首跑）

维度
  D1 结果     40 = 20 × 平均达标率 + 20 × 平均加权分/100
  D2 过程成本 20 = 20 × Σ(达标率×同题最小步数/本款步数) ÷ Σ达标率（只算做对的题）
  D3 稳健性   20 = 20 × 平均达标率（只算重复格；无重复格的产品按三个贴线题 n=1 初值标注 provisional）
  D4 取证能力 20 = 4 项 × 5 分（轨迹完整 / 元信息可核 / 产物归档 / 脚本化重跑）
"""
import json
import statistics
from pathlib import Path

DATA = Path(__file__).with_name("v2-data.json")
REPEAT_CASES = ["bird-ca-schools-15", "dabstep-payments-10", "tb-cargo-plan"]
D = json.loads(DATA.read_text(encoding="utf-8"))
CASES = D["cases"]
PRODS = D["products"]
PIDS = list(PRODS)


def pct(x):
    return round(x, 2)


def cell(prod, case, overrides=None):
    c = PRODS[prod]["cells"][case]
    return dict(c, **overrides[(prod, case)]) if overrides and (prod, case) in overrides else c


def d4(prod):
    return 20 if PRODS[prod]["form"] == "cli" else 17


def evaluate(overrides=None, d4_flat=False, d1_mode="base", drop_d3=False):
    cells = {(p, c): cell(p, c, overrides) for p in PIDS for c in CASES}
    # 同题最小步数（只取该题达标率 > 0 的产品）
    mins = {}
    for c in CASES:
        cand = [cells[(p, c)]["steps_mean"] for p in PIDS if cells[(p, c)]["pass_rate"] > 0]
        if cand:
            mins[c] = min(cand)
    out = {}
    for p in PIDS:
        prs = [cells[(p, c)]["pass_rate"] for c in CASES]
        wms = [cells[(p, c)]["weighted_mean"] for c in CASES]
        if d1_mode == "base":
            d1 = 20 * statistics.mean(prs) + 20 * statistics.mean(wms) / 100
        elif d1_mode == "weighted":
            d1 = 40 * statistics.mean(wms) / 100
        else:  # pass only
            d1 = 40 * statistics.mean(prs)
        num = den = 0.0
        for c in CASES:
            pr = cells[(p, c)]["pass_rate"]
            if pr > 0:
                num += pr * (mins[c] / cells[(p, c)]["steps_mean"])
                den += pr
        d2 = 20 * num / den if den else 0.0
        rep = [c for c in CASES if cells[(p, c)]["n"] > 1]
        if rep:
            d3 = 20 * statistics.mean(cells[(p, c)]["pass_rate"] for c in rep)
            d3_basis = "n=%s" % ",".join(str(cells[(p, c)]["n"]) for c in rep)
            provisional = False
        else:
            d3 = 20 * statistics.mean(cells[(p, c)]["pass_rate"] for c in REPEAT_CASES)
            d3_basis = "provisional n=1"
            provisional = True
        d4v = 20 if d4_flat else d4(p)
        if drop_d3:
            total = d1 + d2 + d4v
            scale = 100 / 80
        else:
            total = d1 + d2 + d3 + d4v
            scale = 1.0
        out[p] = {"pass": statistics.mean(prs), "wm": statistics.mean(wms),
                  "D1": d1, "D2": d2, "D3": d3, "D4": d4v,
                  "d3_basis": d3_basis, "d3_provisional": provisional,
                  "total": total, "scale": scale, "total100": total * scale}
    return out


BASE = evaluate()
ORDER = sorted(PIDS, key=lambda p: -BASE[p]["total100"])

print("=== 主表（四维）===")
print("| 顺序 | 产品 | 形态 | 平均达标 | 平均加权 | D1 结果/40 | D2 过程/20 | D3 稳健/20 | D4 取证/20 | 折算/100 |")
print("|---|---|---|---|---|---|---|---|---|---|")
for i, p in enumerate(ORDER, 1):
    r = BASE[p]
    print(f"| {i} | {PRODS[p]['label']} | {PRODS[p]['form']} | {pct(r['pass'])} | {pct(r['wm'])} | "
          f"{pct(r['D1'])} | {pct(r['D2'])} | {pct(r['D3'])}{'*' if r['d3_provisional'] else ''} | "
          f"{pct(r['D4'])} | **{pct(r['total100'])}** |")
print("\n* = D3 为 n=1 初值（桌面未重复）；CLI 的 D3 来自三个贴线题 n=3。")

print("\n=== 逐格明细（n / 达标率 / 加权均值 / 步数均值）===")
print("| 用例 | " + " | ".join(PRODS[p]["label"] for p in PIDS) + " |")
print("|---|---|---|---|---|")
for c in CASES:
    row = []
    for p in PIDS:
        x = PRODS[p]["cells"][c]
        row.append(f"{x['n']}场 · {pct(x['pass_rate'])} · {pct(x['weighted_mean'])} · {pct(x['steps_mean'])}步")
    print(f"| {c} | " + " | ".join(row) + " |")

print("\n=== 稳健性（重复格逐场）===")
R = json.loads((Path(__file__).parents[2] / "3-表现现场" / "r1028-repeats" / "results.json").read_text(encoding="utf-8"))
for p in PIDS:
    for c in REPEAT_CASES:
        cc = R["products"].get(p, {}).get("cells", {}).get(c)
        if cc and cc["n"] > 1:
            print(f"  {p} / {c}: rewards={cc['rewards']} weighted={[s['weighted'] for s in cc['samples']]} "
                  f"failed_sets_same={cc['failed_agree']} steps={cc['steps_range']}")

print("\n=== 敏感性（每个变体完整重算）===")

def show(name, res):
    order = sorted(PIDS, key=lambda p: -res[p]["total100"])
    print(f"{name}: " + " > ".join(f"{PRODS[p]['label']}({pct(res[p]['total100'])})" for p in order))


show("基准 v2.1", BASE)
show("D4 取证全给满分", evaluate(d4_flat=True))
show("D1 只用加权分", evaluate(d1_mode="weighted"))
show("D1 只用达标率", evaluate(d1_mode="pass"))
show("D3 不计（=方案 A 口径，80 分制折算）", evaluate(drop_d3=True))
show("WB×lcb 判无效", evaluate(overrides={("workbuddy", "lcb-recent-hard-4"): {"pass_rate": 0.0, "weighted_mean": 0.0}}))

print("\n=== 组内差距 ===")
a = ["codex", "dsh", "workbuddy"]
print("A 组 D1: " + " / ".join(f"{p} {pct(BASE[p]['D1'])}" for p in a))
print("A 组 D2: " + " / ".join(f"{p} {pct(BASE[p]['D2'])}" for p in a))
print("A 组 D3: " + " / ".join(f"{p} {pct(BASE[p]['D3'])}" for p in a))
print(f"A 组总分极差 {pct(max(BASE[p]['total100'] for p in a) - min(BASE[p]['total100'] for p in a))}；"
      f"豆包与 A 组最好差 {pct(max(BASE[p]['total100'] for p in a) - BASE['doubao']['total100'])}")
