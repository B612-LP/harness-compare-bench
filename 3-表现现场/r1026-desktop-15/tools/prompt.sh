#!/bin/bash
# 手工跑批的「题面换页器」：把某一场的 TASK.md 塞进剪贴板，不碰 GUI。
# 用法：
#   ./tools/prompt.sh list                     # 看每个产品还剩哪些题
#   ./tools/prompt.sh workbuddy                # 自动取该产品下一个没产物的题
#   ./tools/prompt.sh workbuddy exercism-py-6  # 指定题
set -u
cd "$(dirname "$0")/.." || exit 1
exec python3 - "$@" <<'PY'
import json, subprocess, sys
from pathlib import Path

ROOT = Path.cwd()
CASES = ["bird-ca-schools-15", "exercism-py-6", "dabstep-payments-10",
         "lcb-recent-hard-4", "tb-cargo-plan"]
PRODUCTS = {"workbuddy": "WorkBuddy 桌面端", "yuanbao": "元宝 专家模式",
            "doubao": "豆包 办公"}
# 各题「有产物」判据（与 desk.py 的 ARTIFACTS 对齐；exercism/tb 看 inputs 内改动）
ARTIFACTS = {
    "bird-ca-schools-15": ["answers.jsonl"],
    "dabstep-payments-10": ["answers.jsonl"],
    "lcb-recent-hard-4": ["solutions"],
    "tb-cargo-plan": ["flight_plan.json"],
    "exercism-py-6": [],
}
IGNORE = {"TASK.md", "meta.json", ".baseline.json", "checker.stdout.json",
          "checker.stdout.txt", "checker.stderr.txt", "storage-diff.json",
          "landed.json"}
IGNORE_TOP = {"shots", "trace", "inputs", "__pycache__", ".DS_Store", "solutions"}


def has_product(p: str, c: str) -> bool:
    rd = ROOT / "runs" / p / c
    for name in ARTIFACTS[c]:
        q = rd / name
        if q.is_dir() and any(q.iterdir()):
            return True
        if q.is_file() and q.stat().st_size > 0:
            return True
    if c == "exercism-py-6":
        base = json.loads((rd / ".baseline.json").read_text(encoding="utf-8"))
        for f in (rd / "inputs").rglob("*"):
            if f.is_file():
                rel = str(f.relative_to(rd))
                v = base.get(rel)
                if v is None or [f.stat().st_size, int(f.stat().st_mtime)] != v:
                    return True
    return False


def pending(p: str):
    return [c for c in CASES if not has_product(p, c)]


args = sys.argv[1:]
if not args or args[0] == "list":
    for p in PRODUCTS:
        todo = pending(p)
        print("%-10s 待跑 %d 题：%s" % (p, len(todo), "  ".join(todo) if todo else "（全部有产物）"))
    sys.exit(0)

p = args[0]
if p not in PRODUCTS:
    sys.exit("未知产品：%s（可选：%s）" % (p, ", ".join(PRODUCTS)))
c = args[1] if len(args) > 1 else None
if c is None:
    todo = pending(p)
    if not todo:
        sys.exit("%s 五题都已有产物了。" % PRODUCTS[p])
    c = todo[0]
if c not in CASES:
    sys.exit("未知用例：%s（可选：%s）" % (c, ", ".join(CASES)))
todo_now = pending(p)
tid = todo_now.index(c) + 1 if c in todo_now else 0

task = (ROOT / "runs" / p / c / "TASK.md").read_text(encoding="utf-8")
subprocess.run(["pbcopy"], input=task, text=True, check=True)
title = next((l for l in task.splitlines() if l.startswith("# ")), c)
print("产品  :", PRODUCTS[p])
print("用例  :", c, ("（该产品待跑第 %d/%d 题）" % (tid, len(todo_now))) if tid else "（重跑）")
print("标题  :", title.replace("# ", "", 1))
print("题面  : %d 字，已放进剪贴板 —— App 里新建任务后直接 Cmd+V 发送" % len(task))
print("工作目录:", ROOT / "runs" / p / c)
left = [x for x in pending(p) if x != c]
print("该产品还差:", "  ".join(left) if left else "无")
PY
