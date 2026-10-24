#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""desk.py — 桌面三端（WorkBuddy / 元宝专家模式 / 豆包办公）× 5 题 的跑批自动化。

设计原则：**目录即契约**。每个 (产品 × 用例) 一个 run_dir，inputs 预置在工作目录里；
被测端把产物写在同一个工作目录里；judge 直接读目录 → 不需要人工搬运/转录。

人的动作压缩到 2~3 个：
  1) 在 App 里开一个新会话，把剪贴板里的开场白粘进去发送（run 已自动放入剪贴板）；
  2) 结束后按一次 Enter（屏幕静默 150s 也会自动收尾）；
  3) 可选：填一个「步数」数字（WorkBuddy 能从本地 trace 自动取，回车可跳过）。

子命令：
  setup            生成/重置 15 个 run_dir（幂等）
  run  <p> <case>  跑一场：计时 + 定时截图 + 自动收尾 + 自动判分 + 写 meta
  judge <dir>      只判分（可重复执行，不改产物）
  judge-all        判所有已有产物的 run_dir
  collect          汇总矩阵 → MATRIX.md / matrix.json
  status           看 15 格进度
  land  <dir>      把 ~/Downloads 里本场之后产生的文件搬进 run_dir（给「只能下载」的端兜底）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

TZ = timezone(timedelta(hours=8))
REPO = Path(__file__).resolve().parents[3]
CASE_ROOT = REPO / "2-用例"
ROOT = REPO / "3-表现现场" / "r1026-desktop-15"
RUNS = ROOT / "runs"

PRODUCTS = {
    "workbuddy": {"label": "WorkBuddy 桌面端", "app": "WorkBuddy"},
    "yuanbao": {"label": "元宝 专家模式", "app": "元宝"},
    "doubao": {"label": "豆包 办公", "app": "Doubao"},
}
CASES = [
    "bird-ca-schools-15",
    "exercism-py-6",
    "dabstep-payments-10",
    "lcb-recent-hard-4",
    "tb-cargo-plan",
]
# 有名字的产物；exercism 只看 inputs/ 内改动，故为 None
ARTIFACTS = {
    "dabstep-payments-10": ["answers.jsonl"],
    "bird-ca-schools-15": ["answers.jsonl"],
    "exercism-py-6": None,
    "lcb-recent-hard-4": ["solutions"],
    "tb-cargo-plan": ["flight_plan.json"],
}
IGNORE_TOP = {"shots", "meta.json", "TASK.md", ".baseline.json", "checker.stdout.txt",
              "checker.stdout.json", "checker.stderr.txt", "storage-diff.json",
              "landed.json", "__pycache__", ".DS_Store"}
CANDIDATE_STORE = [
    "~/Library/Application Support/com.tencent.yuanbao",
    "~/Library/Containers/com.tencent.yuanbao/Data/Library/Users",
    "~/Library/Application Support/Doubao",
    "~/.workbuddy/projects",
    "~/.workbuddy/traces",
    "~/.workbuddy/sessions",
]
SKIP_DIRS = {"Cache", "Code Cache", "GPUCache", "ShaderCache", "GrShaderCache",
             "GraphiteDawnCache", "DawnCache", "Crashpad", "Service Worker",
             "browsermetrics", "BrowserMetrics", "logs", "log", "CrashpadMetrics"}


# ---------------------------------------------------------------- 基础工具
def now() -> datetime:
    return datetime.now(TZ)


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S%z")


def parse_iso(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S%z")


def sh(cmd: list, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def run_dir(p: str, c: str) -> Path:
    return RUNS / p / c


def load_case(case: str) -> dict:
    p = CASE_ROOT / case / "case.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"timeout_s": 1800}


def app_version(app: str) -> str | None:
    info = Path("/Applications") / (app + ".app") / "Contents" / "Info.plist"
    if not info.exists():
        return None
    r = sh(["plutil", "-extract", "CFBundleShortVersionString", "raw", str(info)])
    return r.stdout.strip() or None


def task_text(product: str, case: str, rd: Path) -> str:
    body = (CASE_ROOT / case / "instruction.md").read_text(encoding="utf-8").rstrip()
    head = (
        "# 本场任务：%s（%s）\n\n"
        "**你的工作目录（绝对路径）：`%s`**\n\n"
        "请在这个目录里工作：输入都在该目录的 `inputs/` 下，产物按题目要求写到该目录里"
        "（题目里的相对路径都相对这个目录）。除题目明确要求修改的代码外，不要改动 `inputs/` 下的文件。\n\n"
        "---\n\n" % (case, PRODUCTS[product]["label"], rd)
    )
    return head + body + "\n"


def file_state(rd: Path) -> dict:
    """run_dir 内除忽略项外的文件 → (size, mtime)。用于判断「有没有动过」。"""
    st = {}
    for p in rd.rglob("*"):
        rel = p.relative_to(rd)
        if rel.parts and rel.parts[0] in IGNORE_TOP:
            continue
        if p.is_file():
            try:
                s = p.stat()
            except OSError:
                continue
            st[str(rel)] = (s.st_size, int(s.st_mtime))
    return st


def has_artifacts(case: str, rd: Path, baseline: dict) -> bool:
    wanted = ARTIFACTS.get(case)
    if wanted:
        for w in wanted:
            q = rd / w
            if q.is_dir() and any(q.iterdir()):
                return True
            if q.is_file() and q.stat().st_size > 0:
                return True
    cur = file_state(rd)
    for rel, v in cur.items():
        if baseline.get(rel) != v:
            return True
    return False


def artifact_list(rd: Path, baseline: dict) -> list:
    cur = file_state(rd)
    out = [{"path": rel, "size": v[0], "new": rel not in baseline}
           for rel, v in sorted(cur.items()) if baseline.get(rel) != v]
    return out


# ---------------------------------------------------------------- setup
def cmd_setup(args) -> int:
    total_bytes = 0
    for p in PRODUCTS:
        for c in CASES:
            rd = run_dir(p, c)
            if rd.exists() and not args.force:
                if (rd / "TASK.md").exists():
                    continue
            if rd.exists():
                shutil.rmtree(rd)
            (rd / "inputs").mkdir(parents=True)
            src = CASE_ROOT / c / "inputs"
            for item in src.iterdir():
                dst = rd / "inputs" / item.name
                if item.is_dir():
                    shutil.copytree(item, dst)
                else:
                    shutil.copy2(item, dst)
                    total_bytes += item.stat().st_size
            (rd / "shots").mkdir()
            (rd / "TASK.md").write_text(task_text(p, c, rd), encoding="utf-8")
            (rd / ".baseline.json").write_text(
                json.dumps(file_state(rd), ensure_ascii=False) + "\n", encoding="utf-8")
            meta = {
                "product": p, "product_label": PRODUCTS[p]["label"],
                "app_version": app_version(PRODUCTS[p]["app"]),
                "case": c, "run_dir": str(rd), "form": "desktop-GUI",
                "status": "pending", "created_at": iso(now()),
            }
            (rd / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8")
    print("setup 完成：%d 个 run_dir（%s）" % (len(PRODUCTS) * len(CASES), RUNS))
    return 0


# ---------------------------------------------------------------- 截图 / 落地
def _win_id(app_name: str) -> int:
    """取该 App 的 CGWindowID（layer 0 中面积最大的窗口）。

    用途：截图只抓被测 App 的窗口，不抓整屏（整屏会拍到操作者的其它窗口）。
    走 CoreGraphics 的 ctypes 调用，不依赖 PyObjC / Quartz。
    """
    try:
        import ctypes
        cg = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
        cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        cg.CGWindowListCopyWindowInfo.restype = ctypes.c_void_p
        cg.CGWindowListCopyWindowInfo.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
        cf.CFArrayGetCount.restype = ctypes.c_long
        cf.CFArrayGetCount.argtypes = [ctypes.c_void_p]
        cf.CFArrayGetValueAtIndex.restype = ctypes.c_void_p
        cf.CFArrayGetValueAtIndex.argtypes = [ctypes.c_void_p, ctypes.c_long]
        cf.CFDictionaryGetValue.restype = ctypes.c_void_p
        cf.CFDictionaryGetValue.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        cf.CFStringCreateWithCString.restype = ctypes.c_void_p
        cf.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
        cf.CFStringGetCString.restype = ctypes.c_bool
        cf.CFStringGetCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
        cf.CFNumberGetValue.restype = ctypes.c_bool
        cf.CFNumberGetValue.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]

        def ks(name: str):
            return cf.CFStringCreateWithCString(None, name.encode(), 0x08000100)

        def cstr(ref) -> str:
            if not ref:
                return ""
            buf = ctypes.create_string_buffer(512)
            ok = cf.CFStringGetCString(ref, buf, 512, 0x08000100)
            return buf.value.decode("utf-8", "ignore") if ok else ""

        def cnum(ref) -> int:
            v = ctypes.c_int(0)
            if ref:
                cf.CFNumberGetValue(ref, 9, ctypes.byref(v))
            return v.value

        arr = cg.CGWindowListCopyWindowInfo(0, 0)  # 全部窗口（含不在当前 Space 的）
        best, best_area = 0, 0
        for i in range(cf.CFArrayGetCount(arr)):
            d = cf.CFArrayGetValueAtIndex(arr, i)
            owner = cstr(cf.CFDictionaryGetValue(d, ks("kCGWindowOwnerName")))
            if app_name not in owner:
                continue
            if cnum(cf.CFDictionaryGetValue(d, ks("kCGWindowLayer"))) != 0:
                continue
            b = cf.CFDictionaryGetValue(d, ks("kCGWindowBounds"))
            w = cnum(cf.CFDictionaryGetValue(b, ks("Width"))) if b else 0
            h = cnum(cf.CFDictionaryGetValue(b, ks("Height"))) if b else 0
            if w * h > best_area:
                best_area, best = w * h, cnum(cf.CFDictionaryGetValue(d, ks("kCGWindowNumber")))
        return best
    except Exception:
        return 0


def snap(path: Path, app: str | None = None) -> bool:
    """截一张图。给了 app 就**只截该 App 的窗口**（不抓整屏）；找不到窗口则放弃这一张。"""
    cmd = ["screencapture", "-x", "-t", "png"]
    if app:
        wid = _win_id(app)
        if not wid:
            return False
        cmd += ["-o", "-l%d" % wid]
    cmd.append(str(path))
    r = sh(cmd)
    return r.returncode == 0 and path.exists() and path.stat().st_size > 0


def prune_shots(rd: Path, keep: int) -> int:
    """留 keep 张（均匀取），统一降采样成 jpg，删其余。返回保留张数。"""
    pngs = sorted((rd / "shots").glob("*.png"))
    if not pngs:
        return 0
    if keep and len(pngs) > keep:
        idx = {round(i * (len(pngs) - 1) / max(keep - 1, 1)) for i in range(keep)}
        keepers = [pngs[i] for i in sorted(idx)]
    else:
        keepers = pngs
    for p in pngs:
        if p not in keepers:
            p.unlink(missing_ok=True)
    n = 0
    for p in keepers:
        jpg = p.with_suffix(".jpg")
        r = sh(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "72",
                "-Z", "1400", str(p), "--out", str(jpg)])
        if r.returncode == 0 and jpg.exists():
            p.unlink(missing_ok=True)
            n += 1
    return n


def land_downloads(rd: Path, since: float) -> list:
    """把 ~/Downloads 里 since 之后出现的文件搬进 run_dir（给只能下载的端兜底）。"""
    dl = Path.home() / "Downloads"
    moved = []
    if not dl.is_dir():
        return moved
    for f in dl.iterdir():
        try:
            if not f.is_file() or f.name.startswith(".") or f.suffix in (".crdownload", ".download"):
                continue
            if f.stat().st_mtime < since - 1:
                continue
            dst = rd / f.name
            if dst.exists():
                dst = rd / (f.stem + "-" + str(int(time.time())) + f.suffix)
            shutil.move(str(f), str(dst))
            moved.append({"from": str(f), "to": dst.name,
                          "size": dst.stat().st_size})
        except OSError:
            continue
    if moved:
        (rd / "landed.json").write_text(
            json.dumps(moved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return moved


# ---------------------------------------------------------------- 判分
def judge(rd: Path) -> dict:
    case = rd.name
    checker = CASE_ROOT / case / "checker.py"
    t0 = time.time()
    r = sh([sys.executable, str(checker), str(rd), "--json"])
    (rd / "checker.stdout.txt").write_text(r.stdout, encoding="utf-8")
    (rd / "checker.stderr.txt").write_text(r.stderr, encoding="utf-8")
    res = None
    for line in reversed([l for l in r.stdout.splitlines() if l.strip().startswith("{")]):
        try:
            res = json.loads(line)
            break
        except Exception:
            continue
    out = {"ok": res is not None, "exit_code": r.returncode,
           "judge_seconds": round(time.time() - t0, 1)}
    if res:
        out.update({
            "reward": res.get("reward"), "weighted": res.get("weighted"),
            "failed": [c.get("id") for c in res.get("checks", []) if not c.get("pass")],
            "n_checks": len(res.get("checks", [])),
            "raw": {k: v for k, v in res.items() if k != "checks"},
        })
        (rd / "checker.stdout.json").write_text(
            json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        out["stderr_tail"] = r.stderr.strip().splitlines()[-3:]
    return out


# ---------------------------------------------------------------- WorkBuddy trace
def _wb_transcript(rd: Path, start: datetime, end: datetime) -> dict:
    """WorkBuddy 把每个 workspace 的完整会话写在 ~/.workbuddy/projects/<slug>/*.jsonl。
    记录里带 cwd（=workspace 路径）/ timestamp(ms) / type=function_call / name。
    cwd 是强标识：本 run_dir 是新目录，命中即本场；再按文件 mtime 取最新一份。"""
    root = Path.home() / ".workbuddy" / "projects"
    out = {"steps": None, "by_tool": {}, "source": None, "files": [], "session": None}
    if not root.is_dir():
        return out
    want = os.path.realpath(str(rd))
    cands = []
    for f in root.glob("*/*.jsonl"):
        if "rollback" in f.name:
            continue
        try:
            mtime = f.stat().st_mtime
        except OSError:
            continue
        recs = []
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            cwd = o.get("cwd")
            if not cwd or os.path.realpath(cwd) != want:
                continue
            recs.append(o)
        if recs:
            cands.append((mtime, f, recs))
    if not cands:
        return out
    mtime, f, recs = max(cands, key=lambda c: c[0])
    steps, by, ts, sids = 0, {}, [], set()
    for o in recs:
        t = o.get("timestamp")
        if isinstance(t, (int, float)) and t > 1e12:
            ts.append(t / 1000.0)
        if o.get("type") == "function_call":
            steps += 1
            nm = o.get("name") or "?"
            by[nm] = by.get(nm, 0) + 1
        if o.get("sessionId"):
            sids.add(o["sessionId"])
    out.update({"steps": steps or None, "by_tool": by,
                "source": "workbuddy-transcript" if steps else None,
                "files": [f.name], "session": (sorted(sids)[-1] if sids else None),
                "file_mtime": iso(datetime.fromtimestamp(mtime, TZ))})
    if ts:
        out.update({"conv_duration_s": round(max(ts) - min(ts), 1),
                    "conv_n_events": len(recs)})
    return out


def _wb_trace(start: datetime, end: datetime) -> dict:
    root = Path.home() / ".workbuddy" / "traces"
    out = {"steps": None, "by_tool": {}, "source": None, "files": []}
    if not root.is_dir():
        return out
    lo, hi = start.timestamp() - 120, end.timestamp() + 120
    files = []
    for f in root.glob("*/*.jsonl"):
        try:
            if lo <= f.stat().st_mtime <= hi:
                files.append(f)
        except OSError:
            continue
    if not files:
        return out
    steps, by = 0, {}
    for f in files:
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            sp = o.get("span") or {}
            if o.get("type") == "span_start" and sp.get("type") == "function":
                steps += 1
                nm = sp.get("toolName") or sp.get("name") or "?"
                by[nm] = by.get(nm, 0) + 1
    out.update({"steps": steps or None, "by_tool": by, "files": [f.name for f in files],
                "source": "workbuddy-trace" if steps else None})
    return out


def extract_workbuddy(rd: Path, start: datetime, end: datetime) -> dict:
    conv = _wb_transcript(rd, start, end)
    if conv.get("steps"):
        return conv
    tr = _wb_trace(start, end)
    if tr.get("steps"):
        return tr
    return {"steps": None, "source": None, "by_tool": {}}


# ---------------------------------------------------------------- 存储探针
def store_snapshot() -> dict:
    snap = {}
    for root in CANDIDATE_STORE:
        base = Path(os.path.expanduser(root))
        if not base.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            if dirpath.count(os.sep) - str(base).count(os.sep) > 4:
                dirnames[:] = []
                continue
            for fn in filenames:
                p = Path(dirpath) / fn
                try:
                    s = p.stat()
                except OSError:
                    continue
                snap[str(p)] = [s.st_size, int(s.st_mtime)]
            if len(snap) > 60000:
                return snap
    return snap


def store_diff(before: dict, after: dict, rd: Path) -> dict:
    changed = {k: v for k, v in after.items() if before.get(k) != v}
    out = {"n_before": len(before), "n_after": len(after), "n_changed": len(changed),
           "changed": sorted(changed)[:400]}
    (rd / "storage-diff.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def paste_send(app: str) -> bool:
    """把剪贴板内容粘到最前窗口并回车（需要辅助功能权限）。"""
    try:
        subprocess.run(["open", "-a", app], capture_output=True)
        time.sleep(1.2)
        r1 = subprocess.run(["osascript", "-e",
                             'tell application "System Events" to keystroke "v" using command down'],
                            capture_output=True, text=True)
        time.sleep(0.8)
        r2 = subprocess.run(["osascript", "-e",
                             'tell application "System Events" to key code 36'],
                            capture_output=True, text=True)
        return r1.returncode == 0 and r2.returncode == 0
    except Exception:
        return False


# ---------------------------------------------------------------- run
def fmt_clock(s: float) -> str:
    return "%d:%02d" % (s // 60, s % 60)


def ask_line(prompt: str, timeout: float) -> str | None:
    """带超时的单行输入；超时/非 tty 返回 None。"""
    import select
    sys.stdout.write(prompt)
    sys.stdout.flush()
    r, _, _ = select.select([sys.stdin], [], [], timeout)
    if not r:
        sys.stdout.write("\n")
        return None
    line = sys.stdin.readline()
    return line.strip() if line else ""


def cmd_run(args) -> int:
    p, c = args.product, args.case
    if p not in PRODUCTS:
        print("未知产品：%s（可选：%s）" % (p, ", ".join(PRODUCTS)))
        return 2
    if c not in CASES:
        print("未知用例：%s（可选：%s）" % (c, ", ".join(CASES)))
        return 2
    rd = run_dir(p, c)
    if not (rd / "inputs").exists():
        print("run_dir 未初始化，先跑：desk.py setup")
        return 2
    bp = rd / ".baseline.json"
    pristine = ({k: tuple(v) for k, v in json.loads(bp.read_text(encoding="utf-8")).items()}
                if bp.exists() else None)
    if pristine is None:
        pristine = file_state(rd)
        bp.write_text(json.dumps(pristine, ensure_ascii=False) + "\n", encoding="utf-8")
    cur = file_state(rd)
    changed = [r for r in cur if pristine.get(r) != cur[r]]
    if changed and not args.force:
        print("这个格子已经有产物（%d 个改动文件，如 %s）。要重跑加 --force。" %
              (len(changed), ", ".join(changed[:3])))
        return 2
    if args.force:
        for f in rd.iterdir():
            if f.name in ("inputs", "TASK.md", "meta.json", ".baseline.json"):
                continue
            shutil.rmtree(f) if f.is_dir() else f.unlink()
        # inputs 必须恢复成出厂状态，否则上一轮的改动会污染重跑
        shutil.rmtree(rd / "inputs", ignore_errors=True)
        shutil.copytree(CASE_ROOT / c / "inputs", rd / "inputs")
        (rd / ".baseline.json").write_text(
            json.dumps(file_state(rd), ensure_ascii=False) + "\n", encoding="utf-8")
    base = file_state(rd)

    # 开场白进剪贴板
    task = (rd / "TASK.md").read_text(encoding="utf-8")
    subprocess.run(["pbcopy"], input=task, text=True)

    mp = rd / "meta.json"
    meta = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {
        "product": p, "product_label": PRODUCTS[p]["label"],
        "app_version": app_version(PRODUCTS[p]["app"]),
        "case": c, "run_dir": str(rd), "form": "desktop-GUI",
        "created_at": iso(now()),
    }
    timeout_s = int(load_case(c)["timeout_s"])
    if args.max_minutes:
        timeout_s = min(timeout_s, args.max_minutes * 60)
    app = PRODUCTS[p]["app"]

    print("\n" + "=" * 62)
    print("【%s × %s】" % (PRODUCTS[p]["label"], c))
    print("① 在 App 里开一个新会话，把光标点进输入框")
    if args.paste == "auto":
        print("② 回到终端按一次 Enter —— 我自动粘贴开场白并回车发送")
    else:
        print("② 回到终端按一次 Enter —— 然后自己 Cmd+V 粘贴（%d 字）并回车发送" % len(task))
    print("③ 跑完按 Enter 收尾；屏幕静默 %ds 自动收尾" % args.idle_s)
    print("   计时/截图/判分/建档全自动，你不用掐表也不用记分数。")
    print("=" * 62)
    if not args.no_open:
        subprocess.run(["open", "-a", app], capture_output=True)
    # 等人开好新会话：按 Enter 后再发（计时从发送那一刻开始，更公平）
    import select as _sel
    while True:
        r, _, _ = _sel.select([sys.stdin], [], [], 1.0)
        if r or not sys.stdin.isatty():
            if r:
                sys.stdin.readline()
            break
    if args.paste == "auto" and sys.stdin.isatty():
        # 等待期间剪贴板可能被其它程序覆盖（截图工具等）→ 发送前重写并校验
        got = subprocess.run(["pbpaste"], capture_output=True, text=True).stdout
        if got.strip() != task.strip():
            print("【剪贴板被覆盖（当前不是开场白文本），已重写】")
            subprocess.run(["pbcopy"], input=task, text=True)
        okp = paste_send(app)
        print("自动粘贴%s" % ("完成，已发送。" if okp else "失败 —— 请手动 Cmd+V + 回车，然后按 Enter 继续。"))
        if not okp:
            while True:
                r, _, _ = _sel.select([sys.stdin], [], [], 1.0)
                if r:
                    sys.stdin.readline()
                    break
    start = now()
    meta.update({"status": "running", "started_at": iso(start), "input_mode": args.paste,
                 "finish_reason": None, "landed": [], "shots": 0})
    (rd / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                                  encoding="utf-8")

    shots_dir = rd / "shots"
    shots_dir.mkdir(exist_ok=True)
    store_before = store_snapshot() if p != "workbuddy" or args.probe else None
    t0 = time.time()
    shot_n, last_shot, last_screen = 0, 0.0, None
    last_activity = t0
    prev_state = dict(base)
    finish_reason = None
    try:
        import select
        while True:
            el = time.time() - t0
            # 键盘
            r, _, _ = select.select([sys.stdin], [], [], 1.0)
            if r:
                sys.stdin.readline()
                finish_reason = "human"
                break
            # 文件活动
            cur = file_state(rd)
            if cur != prev_state:
                prev_state = cur
                last_activity = time.time()
            art = has_artifacts(c, rd, base)
            # 截图 + 屏幕活动
            if args.shot_every and time.time() - last_shot >= args.shot_every:
                png = shots_dir / ("%04d.png" % (shot_n + 1))
                if snap(png, app):
                    shot_fail = 0
                    shot_n += 1
                    h = hashlib.md5(png.read_bytes()).hexdigest()
                    if h != last_screen:
                        last_screen, last_activity = h, time.time()
                    if len(list(shots_dir.glob("*.png"))) > 400:
                        args.shot_every = 0  # 兜底：太多就停
                else:
                    # 窗口不可用（最小化/锁屏/切了桌面）或没有屏幕录制权限：跳过本张，
                    # 连续失败 10 次才停（一次瞬时失败不该让整场没有截图）。
                    shot_fail += 1
                    if shot_fail == 1:
                        print("\n[截图失败：被测窗口不可用（最小化/锁屏）或缺屏幕录制权限，本张跳过]")
                    elif shot_fail >= 10:
                        print("\n[连续 10 次截图失败，停止截图]")
                        args.shot_every = 0
            # 进度行
            if int(el) % 30 < 2:
                idle = time.time() - last_activity
                print("\r[%s] 产物=%s 文件=%d 屏静默=%ds" %
                      (fmt_clock(el), "有" if art else "无", len(cur), int(idle)),
                      end="", flush=True)
            # 自动收尾
            idle = time.time() - last_activity
            if args.auto and art and idle >= args.idle_s:
                finish_reason = "idle"
                break
            if el >= timeout_s:
                finish_reason = "timeout"
                break
    except KeyboardInterrupt:
        finish_reason = "ctrl-c"
    end = now()
    dur = round(time.time() - t0, 1)
    print("\n收尾（%s），本场计时 %.1fs" % (finish_reason, dur))

    moved = land_downloads(rd, t0) if args.land else []
    if moved:
        print("从 ~/Downloads 搬进 %d 个文件（端只能下载时的兜底）" % len(moved))
    jr = judge(rd)
    steps = None
    steps_src = None
    if p == "workbuddy":
        tr = extract_workbuddy(rd, start, end)
        if tr.get("steps"):
            steps, steps_src = tr["steps"], "workbuddy-trace"
            print("WorkBuddy 本地 trace：%d 步（%s）" % (steps, tr.get("by_tool")))
        meta["trace"] = tr
    if steps is None and sys.stdin.isatty():
        v = ask_line("步数（App 界面上的执行步数，回车跳过）：", 20)
        if v:
            try:
                steps, steps_src = int(v), "manual"
            except ValueError:
                steps, steps_src = None, None
    kept = prune_shots(rd, args.keep_shots)
    meta.update({
        "status": "done" if jr.get("ok") else "judge-failed",
        "ended_at": iso(end), "duration_s": dur, "finish_reason": finish_reason,
        "shots": kept, "artifacts": artifact_list(rd, base),
        "shot_mode": "app-window" if args.shot_every else "none",
        "steps": steps, "steps_source": steps_src,
        "reward": jr.get("reward"), "weighted": jr.get("weighted"),
        "failed": jr.get("failed", []), "judge": jr,
        "landed": moved,
        "notes": args.note or "",
    })
    if store_before is not None:
        meta["storage_diff"] = store_diff(store_before, store_snapshot(), rd)
    (rd / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                                  encoding="utf-8")
    print("\n—— 本场结果 ——")
    print("  reward=%s  weighted=%s  耗时=%.1fs  步数=%s  产物=%d 个  截图=%d 张" % (
        meta["reward"], meta["weighted"], dur, steps, len(meta["artifacts"]), kept))
    if meta.get("failed"):
        print("  未过项：%s" % ", ".join(meta["failed"][:12]))
    nxt = _next_run(p, c)
    if nxt:
        print("\n下一场：./tools/run.sh %s %s" % nxt)
    return 0 if jr.get("ok") else 1


def _next_run(p: str, c: str):
    order = [(pp, cc) for pp in PRODUCTS for cc in CASES]
    idx = order.index((p, c)) if (p, c) in order else -1
    for pp, cc in order[idx + 1:]:
        rd = run_dir(pp, cc)
        meta = rd / "meta.json"
        if meta.exists():
            try:
                if json.loads(meta.read_text(encoding="utf-8")).get("status") in ("pending",):
                    return pp, cc
            except Exception:
                pass
        else:
            return pp, cc
    return None


# ---------------------------------------------------------------- judge / collect / status
def _all_runs() -> list:
    out = []
    for p in PRODUCTS:
        for c in CASES:
            out.append(run_dir(p, c))
    return out


def cmd_judge(args) -> int:
    rd = Path(args.run_dir).resolve()
    if not rd.is_dir():
        print("没有这个目录：%s" % rd)
        return 2
    jr = judge(rd)
    meta_p = rd / "meta.json"
    if meta_p.exists():
        meta = json.loads(meta_p.read_text(encoding="utf-8"))
        meta.update({"reward": jr.get("reward"), "weighted": jr.get("weighted"),
                     "failed": jr.get("failed", []), "judge": jr,
                     "judge_rechecked_at": iso(now())})
        meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: jr.get(k) for k in ("ok", "reward", "weighted", "failed", "exit_code")},
                     ensure_ascii=False))
    return 0 if jr.get("ok") else 1


def cmd_judge_all(args) -> int:
    n = 0
    for rd in _all_runs():
        if not rd.exists() or not file_state(rd):
            continue
        jr = judge(rd)
        meta_p = rd / "meta.json"
        meta = json.loads(meta_p.read_text(encoding="utf-8")) if meta_p.exists() else {}
        meta.update({"reward": jr.get("reward"), "weighted": jr.get("weighted"),
                     "failed": jr.get("failed", []), "judge": jr,
                     "judge_rechecked_at": iso(now())})
        meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("%-11s %-20s reward=%s weighted=%s" % (rd.parts[-2], rd.name,
                                                     jr.get("reward"), jr.get("weighted")))
        n += 1
    print("共复判 %d 场" % n)
    return 0


def cmd_collect(args) -> int:
    rows = {}
    for p in PRODUCTS:
        for c in CASES:
            rd = run_dir(p, c)
            meta = {}
            if (rd / "meta.json").exists():
                try:
                    meta = json.loads((rd / "meta.json").read_text(encoding="utf-8"))
                except Exception:
                    meta = {}
            rows[(p, c)] = meta

    def cell(m):
        if not m or m.get("status") in (None, "pending"):
            return "—"
        r = m.get("reward")
        w = m.get("weighted")
        d = m.get("duration_s")
        s = m.get("steps")
        flag = "✅" if r == 1 else ("❌" if r == 0 else "?")
        # 完整性标记：integrity=invalid 的格不可用于结论；suspect 需披露
        integ = m.get("integrity")
        if integ == "invalid":
            flag = "⛔"
        elif integ in ("suspect", "note"):
            flag = flag + "⚠"
        return "%s %s / %s / %s / %s" % (
            flag, r, ("%.2f" % w) if isinstance(w, (int, float)) else "—",
            ("%.0fs" % d) if isinstance(d, (int, float)) else "—",
            s if s is not None else "—")

    lines = ["# 桌面三端 × 5 题 汇总（自动生成）", "",
             "> 每格：达标/奖励 · 半程分 · 耗时 · 步数。`—` 表示未跑。",
             "> ⛔ = 该格轨迹确认访问过答案/规格（结论作废）；⚠ = 有污染渠道需披露。", ""]
    head = "| 用例 | " + " | ".join(PRODUCTS[p]["label"] for p in PRODUCTS) + " |"
    lines += [head, "|---|" + "---|" * len(PRODUCTS)]
    for c in CASES:
        lines.append("| `%s` | %s |" % (c, " | ".join(cell(rows[(p, c)]) for p in PRODUCTS)))
    lines += ["", "## 汇总", "",
              "| 口径 | " + " | ".join(PRODUCTS[p]["label"] for p in PRODUCTS) + " |",
              "|---|" + "---|" * len(PRODUCTS)]
    agg = {}
    for p in PRODUCTS:
        ms = [rows[(p, c)] for c in CASES if rows[(p, c)].get("status") == "done"]
        done = len([m for m in ms if m.get("reward") is not None])
        head_n = sum(1 for m in ms if m.get("reward") == 1)
        wsum = sum(m.get("weighted") or 0 for m in ms)
        dur = sum(m.get("duration_s") or 0 for m in ms)
        steps = sum(m.get("steps") or 0 for m in ms)
        nstep = len([m for m in ms if m.get("steps") is not None])
        agg[p] = dict(done=done, headline=head_n, weighted=wsum, duration=dur,
                      steps=steps, nstep=nstep)
    lines.append("| 已跑场次 | " + " | ".join(str(agg[p]["done"]) for p in PRODUCTS) + " |")
    lines.append("| headline 达标 | " + " | ".join(
        "%d/5" % agg[p]["headline"] if agg[p]["done"] else "—" for p in PRODUCTS) + " |")
    lines.append("| weighted 合计 | " + " | ".join(
        "%.2f" % agg[p]["weighted"] if agg[p]["done"] else "—" for p in PRODUCTS) + " |")
    lines.append("| 总耗时 | " + " | ".join(
        "%.1fs" % agg[p]["duration"] if agg[p]["done"] else "—" for p in PRODUCTS) + " |")
    lines.append("| 总步数 | " + " | ".join(
        ("%d（%d 场有数）" % (agg[p]["steps"], agg[p]["nstep"])) if agg[p]["nstep"] else "—"
        for p in PRODUCTS) + " |")
    md = "\n".join(lines) + "\n"
    (ROOT / "MATRIX.md").write_text(md, encoding="utf-8")
    (ROOT / "matrix.json").write_text(json.dumps(
        {"rows": [{"product": p, "case": c, **{k: rows[(p, c)].get(k) for k in
                  ("status", "reward", "weighted", "duration_s", "steps", "finish_reason")}}
                  for p in PRODUCTS for c in CASES], "agg": agg},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(md)
    return 0


def cmd_status(args) -> int:
    print("%-11s %-20s %-9s %s" % ("产品", "用例", "状态", "结果"))
    for p in PRODUCTS:
        for c in CASES:
            rd = run_dir(p, c)
            meta = {}
            if (rd / "meta.json").exists():
                try:
                    meta = json.loads((rd / "meta.json").read_text(encoding="utf-8"))
                except Exception:
                    pass
            st = meta.get("status", "missing")
            info = ""
            if meta.get("reward") is not None:
                info = "reward=%s weighted=%s %.0fs steps=%s" % (
                    meta.get("reward"), meta.get("weighted"),
                    meta.get("duration_s") or 0, meta.get("steps"))
            print("%-11s %-20s %-9s %s" % (p, c, st, info))
    return 0


def cmd_land(args) -> int:
    rd = Path(args.run_dir).resolve()
    meta = json.loads((rd / "meta.json").read_text(encoding="utf-8")) \
        if (rd / "meta.json").exists() else {}
    since = parse_iso(meta["started_at"]).timestamp() if meta.get("started_at") else 0
    moved = land_downloads(rd, since)
    print("搬进 %d 个文件：%s" % (len(moved), [m["to"] for m in moved]))
    return 0


# ---------------------------------------------------------------- main
def main(argv) -> int:
    ap = argparse.ArgumentParser(description="桌面三端 × 5 题 跑批自动化")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("setup", help="生成 15 个 run_dir")
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(func=cmd_setup)

    sp = sub.add_parser("run", help="跑一场")
    sp.add_argument("product")
    sp.add_argument("case")
    sp.add_argument("--force", action="store_true", help="已有产物也重跑")
    sp.add_argument("--auto", action="store_true", default=True, help="屏幕静默自动收尾（默认开）")
    sp.add_argument("--idle-s", type=int, default=150, help="静默多少秒算跑完")
    sp.add_argument("--shot-every", type=int, default=20, help="截图间隔秒；0=不截图")
    sp.add_argument("--keep-shots", type=int, default=6)
    sp.add_argument("--max-minutes", type=int, default=0)
    sp.add_argument("--land", action="store_true", help="收尾时把 ~/Downloads 新文件搬进来")
    sp.add_argument("--probe", action="store_true", help="抓本场前后 App 本地存储差异")
    sp.add_argument("--no-open", action="store_true", help="不自动激活 App（测试用）")
    sp.add_argument("--paste", choices=["auto", "manual"], default="auto",
                    help="auto=自动粘贴并回车（默认）；manual=自己粘")
    sp.add_argument("--note", default="")
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser("judge", help="判一个 run_dir")
    sp.add_argument("run_dir")
    sp.set_defaults(func=cmd_judge)

    sp = sub.add_parser("judge-all", help="判所有已有产物的 run_dir")
    sp.set_defaults(func=cmd_judge_all)

    sp = sub.add_parser("collect", help="汇总矩阵")
    sp.set_defaults(func=cmd_collect)

    sp = sub.add_parser("status", help="看进度")
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser("land", help="从 ~/Downloads 搬产物进来")
    sp.add_argument("run_dir")
    sp.set_defaults(func=cmd_land)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))