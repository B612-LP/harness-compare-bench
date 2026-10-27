#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全量只读重判管线（replay_all）：运行总账全部行 × 现行 checker 重判，输出「重判 vs 总账」对照。

目标
----
一条命令重判 5-评测报告/运行总账-2026-10-24.json 的 runs[] 里所有可重判的行，
输出逐行明细（replay-all-results.json）+ 控制台汇总（可重判 / 一致 / 已知偏移 /
不一致 / 重判失败 / skip），作为阶段报告「证据与复核」维度的常驻证据。
本脚本是 checker-tightening-B2-B8-B12-13-14/replay_2026_10_27.py（3 题 × 24 场收紧批回放）
的泛化版：同一临时副本协议，行集从 3 题扩展到总账全部行。

只读协议（沿用两代先例，历史零写入）
------------------------------------
- bird-q26-并入/replay_2026_10_26.py 定下的临时副本协议：判分一律在 /tmp 临时副本进行
  （canonical inputs 副本 + 历史产物重组），历史 run_dir 零写入。r1028/r1029 等工作区
  仍带 v1.1 字节 questions.json，直接对历史目录重判会误触 input_integrity 守卫。
- 判分对象 = 各 case 现行 2-用例/<case>/checker.py 只读调用；truth / inputs / tests /
  solution 以符号链接或副本引用 canonical 字节，不落任何写操作到仓库与历史目录。
- 每场登记判分产物的 SHA-256（artifact_sha256）与所用 checker 的 SHA-256（可复核性）。

run_dir 解析（总账元数据不全的兜底链，逐行记录所用的解析方式）
------------------------------------------------------------
1. original_fields.run_dir → original_fields.judge.run_dir（~ 展开）；
2. sources[] 路径推断（3-表现现场/… 与 bench-automation/… 两种相对基准，取父目录）；
3. 已存在目录里 judge_result.json 的 run_dir 指针（bench-automation 证据包 → 实际工作区）；
4. 已知批次目录映射：~/bench-workspaces/<batch>/<product>/<case>，
   特例 r1027-isolated → ~/bench-workspaces/r1027/<product>__<case> 拆解。
判分对象取第一个「目录存在且判分产物齐全」的候选；改用非总账 run_dir 的候选时在
artifact_note 标注（先例：收紧批收据 §1 cargo 证据包兜底）。

行分类
------
- skip（重判无意义或不适用，逐行列出）：adjudication=X（含 scoring_status 含
  excluded / not-a-run 的行）；case 无现行 checker（历史用例已归档）；总账未登记
  run_dir 且无法推断；登记路径本机缺失（仓内 = 目录缺失，私有仓 = 其他机器/已清理）。
- error（尝试重判但失败，不中断全局）：判分产物不齐（如现场只留输出不留代码）、
  判分超时（单场 600s）、checker 异常退出。
- verdict（重判成功）：match（reward+weighted 与总账 raw 一致）/ known-offset /
  mismatch。

known-offset 口径（差异 ≠ 翻转）
--------------------------------
bird q26 版本偏移：沿用判卷审计-2026-10-26/bird-q26-并入/README.md §5 的查因结论
（v1.1→v1.2-q26-frpm 金标迁移的逐场旧→新分对照表，内嵌于 KNOWN_Q26_OFFSET；收据对
r1028 系 run_id 用无 runs/ 段的缩写、r1026/r1029 系用全名，两种键都收）。仅当
「总账记载 = 表中旧值 且 重判 = 表中新值」时判 known-offset；数值对不上仍按
mismatch 如实列出。lcb r1029 doubao 一场若复现收紧批收据 §1 已查因的负载超时抖动
签名（reward=1、weighted=75.0、红项 abc389_g），verdict 仍记 mismatch 并附
prior_attribution 既往查因标注，不计入「未查因不一致」；其余 mismatch 如实列出、
不计任何注解。

用法与退出码
------------
    python3 -B 4-打分细则/判卷回归/replay_all.py [输出.json] [--plan-only]

- --plan-only：只做行分类与 run_dir 解析干跑，不判分（验证覆盖率用）。
- 输出默认与本脚本同目录 replay-all-results.json。
- 退出码：0 = 无「未查因不一致」且无重判失败；1 = 存在未查因不一致或 error；
  2 = 环境错误。
- 发现「非已知原因的不一致」时本工具不改任何东西，如实列出——这正是工具的价值。

纪律：只读既有证据与历史 run 目录；不改 checker/truth/总账/CHANGELOG；判分超时
单场 600s，失败记 error 不中断全局。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
REPO = SCRIPT_DIR.parents[1]  # <repo>/4-打分细则/判卷回归 -> 仓库根
LEDGER = REPO / "5-评测报告" / "运行总账-2026-10-24.json"
DEFAULT_OUT = SCRIPT_DIR / "replay-all-results.json"
GRADE_TIMEOUT_S = 600  # 单场判分超时（任务纪律）

CURRENT_CASES = ("bird-ca-schools-15", "dabstep-payments-10",
                 "exercism-py-6", "lcb-recent-hard-4", "tb-cargo-plan")

# 各 case 判分时 staged 用例目录需要的 canonical 资产（相对 2-用例/<case>/）。
STAGED_ASSETS = {
    "bird-ca-schools-15": {"symlink": ("truth.json", "inputs")},
    "dabstep-payments-10": {"symlink": ("truth.json", "inputs", "solution")},
    "exercism-py-6": {"symlink": ("truth.json", "inputs", "tests"),
                      "copy": ("trusted_runner.py",)},  # checker 以 HERE/trusted_runner.py 起子进程
    "lcb-recent-hard-4": {"symlink": ("truth.json", "inputs")},
    "tb-cargo-plan": {"symlink": ("truth.json", "inputs")},
}

EXERCISES = ("forth", "poker", "dominoes", "bowling", "zipper", "pov")

# ---------------------------------------------------------------------------
# known-offset 依据：bird q26 版本迁移逐场旧→新分对照（bird-q26-并入/README.md §5）。
# 键 = 归一化 run_id（去掉 "/runs/" 段以对齐收据缩写）；值 = (旧 reward, 旧 weighted,
# 新 reward, 新 weighted)。仅当总账=旧值且重判=新值时判 known-offset。
# ---------------------------------------------------------------------------
KNOWN_Q26_OFFSET = {
    "r1025-candidates/bird-ca-schools-15__codex": (1, 86.67, 1, 93.33),
    "r1025-candidates/bird-ca-schools-15__dsh": (1, 86.67, 1, 93.33),
    "r1026-desktop-15/runs/doubao/bird-ca-schools-15": (0, 60.00, 0, 66.67),
    "r1026-desktop-15/runs/workbuddy/bird-ca-schools-15": (1, 86.67, 1, 93.33),
    "r1028-repeats/codex__bird-ca-schools-15__r2": (1, 86.67, 1, 93.33),
    "r1028-repeats/codex__bird-ca-schools-15__r3": (1, 80.00, 1, 86.67),
    "r1028-repeats/dsh__bird-ca-schools-15__r2": (1, 86.67, 1, 93.33),
    "r1028-repeats/dsh__bird-ca-schools-15__r3": (1, 86.67, 1, 93.33),
    "r1029-desktop-auto/runs/doubao/bird-ca-schools-15": (0, 66.67, 0, 73.33),
    "r1029-desktop-auto/runs/workbuddy/bird-ca-schools-15": (1, 93.33, 1, 86.67),
}
KNOWN_Q26_BASIS = ("判卷审计-2026-10-26/bird-q26-并入/README.md §5：q26 金标 v1.1→v1.2 "
                   "（Free Meal→FRPM）迁移的逐场旧→新分对照；总账 raw 仍记旧合同分，"
                   "重判按现行 v1.2 合同得出新分，差异≠翻转")
LCB_JITTER_RUN = "r1029-desktop-auto/runs/doubao/lcb-recent-hard-4"
LCB_JITTER_SIGNATURE = (1, 75.0)  # 收紧批收据 §1 记录的复现签名：reward=1、weighted=75.0（abc389_g 超时）
LCB_JITTER_NOTE = ("收紧批收据 §1 已查因：abc389_g #3 组在机器负载下 >10s 判 timeout，"
                   "before=after=75.0（登记 100.0），reward 均为 1；lcb spec §5 已披露"
                   "单组 10s 口径（oracle 最慢单组 1.37s），先于收紧批存在")


def offset_key(run_id: str):
    """known-offset 表键匹配：收据对 r1028 系用缩写（无 /runs/ 段），r1026/r1029 系用全名，两者都收。"""
    for k in (run_id, norm_run_id(run_id)):
        if k in KNOWN_Q26_OFFSET:
            return k
    return None

PRIVATE_ROOTS = (Path.home() / "bench-automation", Path.home() / "bench-workspaces")


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def norm_run_id(run_id: str) -> str:
    """归一化 run_id 以对齐收据缩写：r1028-repeats/runs/x → r1028-repeats/x。"""
    return run_id.replace("/runs/", "/")


def close(a, b, tol=0.005) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return a == b


def same_score(reward, weighted, ledger_reward, ledger_weighted) -> bool:
    return (reward == ledger_reward
            and close(weighted, ledger_weighted))


# ---------------------------------------------------------------------------
# run_dir 解析
# ---------------------------------------------------------------------------
def run_dir_candidates(row: dict) -> list:
    """候选解析链（有序、去重）：总账字段 → sources 推断 → judge_result 指针 → 工作区映射。"""
    of = row.get("original_fields") or {}
    cands = []  # (how, Path)

    def add(how: str, path):
        if path is None:
            return
        try:
            rp = Path(os.path.expanduser(str(path))).resolve()
        except OSError:
            return
        if all(rp != p for _, p in cands):
            cands.append((how, rp))

    add("original_fields.run_dir", of.get("run_dir"))
    add("original_fields.judge.run_dir", (of.get("judge") or {}).get("run_dir"))
    for s in (row.get("sources") or [])[:2]:
        p = s.get("path")
        if not p:
            continue
        if os.path.isabs(p):
            add("sources 路径推断", Path(p).parent)
        else:
            add("sources 路径推断(repo 相对)", (REPO / p).parent)
            add("sources 路径推断(home 相对)", Path.home() / p)
    # judge_result.json 指针：仅采信第一个已存在候选（历史判分自己登记的实际对象）
    for how, path in cands:
        jr = path / "judge_result.json"
        if path.is_dir() and jr.is_file():
            try:
                pointer = (json.loads(jr.read_text(encoding="utf-8")) or {}).get("run_dir")
            except (OSError, ValueError):
                pointer = None
            if pointer:
                add("judge_result.json run_dir 指针", pointer)
            break
    # 已知批次工作区映射
    batch = row.get("batch") or ""
    product = row.get("product") or ""
    case = row.get("case") or ""
    ws_batch = {"r1027-isolated": "r1027"}.get(batch, batch)
    if batch == "r1027-isolated":
        last = (row.get("run_id") or "").split("/")[-1]
        if "__" in last:
            prod, cse = last.split("__", 1)
            add("工作区映射(bench-workspaces/%s/%s)" % (ws_batch, prod),
                Path.home() / "bench-workspaces" / ws_batch / prod / cse)
    if product and case:
        add("工作区映射(bench-workspaces/%s/%s)" % (ws_batch, product),
            Path.home() / "bench-workspaces" / ws_batch / product / case)
    return cands


def is_private(path: Path) -> bool:
    try:
        return any(path == root or root in path.parents for root in PRIVATE_ROOTS)
    except OSError:
        return False


# ---------------------------------------------------------------------------
# 判分产物发现（按 case）
# ---------------------------------------------------------------------------
def _answers_candidates(run_dir: Path):
    return (run_dir / "answers.jsonl", run_dir / "workspace" / "answers.jsonl",
            run_dir / "output" / "answers.jsonl", run_dir / "outputs" / "answers.jsonl")


def discover_answers(run_dir: Path, allow_pkg: bool = True):
    """bird / dab：answers.jsonl（run 根、workspace、output(s)；证据包 artifacts 兜底）。"""
    for cand in _answers_candidates(run_dir):
        if cand.is_file():
            return [cand]
    art = run_dir / "artifacts"
    if allow_pkg and art.is_dir():
        hits = sorted(art.glob("*.answers.jsonl"))
        if hits:
            return hits
    return None


def discover_lcb(run_dir: Path, allow_pkg: bool = True):
    """lcb：solutions/*.py（run 根、workspace；证据包 artifacts/<conv>.abc38x_y.py 兜底）。"""
    for base in (run_dir / "solutions", run_dir / "workspace" / "solutions"):
        if base.is_dir():
            sols = sorted(base.glob("*.py"))
            if sols:
                return sols
    art = run_dir / "artifacts"
    if allow_pkg and art.is_dir():
        sols = sorted(p for p in art.glob("*.py")
                      if p.name.split(".", 1)[-1].startswith(("abc38",)))
        if sols:
            return sols
    return None


def discover_cargo(run_dir: Path, allow_pkg: bool = True):
    """cargo：inputs/app/*.py（run 根、workspace；证据包 artifacts/*.py 最后手段）。"""
    for base in (run_dir / "inputs" / "app", run_dir / "workspace" / "inputs" / "app"):
        if (base / "dispatch.py").is_file():
            return sorted(base.glob("*.py"))
    art = run_dir / "artifacts"
    if allow_pkg and art.is_dir():
        code = sorted(art.glob("*.py"))
        if code:
            return code
    return None


def discover_exercism(run_dir: Path, allow_pkg: bool = True):
    """exercism：6 题候选 <ex>.py（附全量 inputs、workspace，或证据包 artifacts/<conv>.<ex>.py）。"""
    for base in (run_dir / "inputs" / "exercises", run_dir / "workspace" / "inputs" / "exercises"):
        if base.is_dir():
            cands = [base / ex / (ex + ".py") for ex in EXERCISES]
            if all(c.is_file() for c in cands):
                return cands
    art = run_dir / "artifacts"
    if allow_pkg and art.is_dir():
        byex = {}
        for p in sorted(art.glob("*.py")):
            suffix = p.name.split(".", 1)[-1]  # "<conv>.<ex>.py" → "<ex>.py"
            ex = suffix[:-3] if suffix.endswith(".py") else suffix
            if ex in EXERCISES:
                byex[ex] = p
        if len(byex) == len(EXERCISES):
            return [byex[ex] for ex in EXERCISES]
    return None


DISCOVER = {
    "bird-ca-schools-15": discover_answers,
    "dabstep-payments-10": discover_answers,
    "exercism-py-6": discover_exercism,
    "lcb-recent-hard-4": discover_lcb,
    "tb-cargo-plan": discover_cargo,
}


def locate(case: str, row: dict):
    """沿候选链两轮找判分对象：先「完整判分对象」，全链落空再退证据包 artifacts 快照。

    artifacts/ 证据包快照是最后手段（收紧批收据 §1：r20261026 的快照 .py 有截断，
    按其重判会得到偏离总账的分）；只有全链都无完整判分对象时才启用。
    返回 (chosen_path, how, artifacts, examined, tier)；找不到 chosen=None。
    """
    examined = []
    for allow_pkg, tier in ((False, "full"), (True, "artifact-package")):
        for how, path in run_dir_candidates(row):
            if tier == "full":
                exists = path.is_dir()
                examined.append({"how": how, "path": str(path), "exists": exists})
            if not path.is_dir():
                continue
            artifacts = DISCOVER[case](path, allow_pkg=allow_pkg)
            if artifacts:
                return path, how, artifacts, examined, tier
    return None, None, None, examined, None


# ---------------------------------------------------------------------------
# 临时副本重组（canonical inputs + 历史产物；历史零写入）
# ---------------------------------------------------------------------------
def _lcb_target_name(p: Path) -> str:
    name = p.name
    if "." in name and name.split(".", 1)[1].startswith("abc"):
        return name.split(".", 1)[1]
    return name


def build_temp_run(case: str, run_dir: Path, artifacts, tmp_root: Path) -> Path:
    run = tmp_root / "run"
    run.mkdir()
    case_dir = REPO / "2-用例" / case
    if case in ("bird-ca-schools-15", "dabstep-payments-10"):
        shutil.copytree(case_dir / "inputs", run / "inputs")
        shutil.copy2(artifacts[0], run / "answers.jsonl")
    elif case == "lcb-recent-hard-4":
        (run / "solutions").mkdir()
        for p in artifacts:
            shutil.copy2(p, run / "solutions" / _lcb_target_name(p))
    elif case == "tb-cargo-plan":
        shutil.copytree(case_dir / "inputs", run / "inputs")
        for p in artifacts:
            shutil.copy2(p, run / "inputs" / "app" / p.name)
    elif case == "exercism-py-6":
        shutil.copytree(case_dir / "inputs", run / "inputs")
        for ex, p in zip(EXERCISES, artifacts):
            shutil.copy2(p, run / "inputs" / "exercises" / ex / (ex + ".py"))
    else:
        raise ValueError(case)
    return run


def stage_case(case: str, tmp_root: Path) -> tuple:
    """staged 用例目录：现行 checker 副本 + canonical 资产符号链接/副本（全只读引用）。"""
    case_dir = REPO / "2-用例" / case
    checker = case_dir / "checker.py"
    staged = tmp_root / ("case_" + case)
    staged.mkdir()
    shutil.copy2(checker, staged / "checker.py")
    assets = STAGED_ASSETS[case]
    for name in assets.get("symlink", ()):
        (staged / name).symlink_to(case_dir / name,
                                   target_is_directory=(case_dir / name).is_dir())
    for name in assets.get("copy", ()):
        shutil.copy2(case_dir / name, staged / name)
    return staged, checker


def grade(staged_case: Path, run: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, "-B", str(staged_case / "checker.py"), str(run), "--json"],
        capture_output=True, text=True, timeout=GRADE_TIMEOUT_S, cwd=str(run))
    lines = [ln for ln in (proc.stdout or "").strip().splitlines() if ln.strip()]
    if not lines:
        return {"error": "checker 无 JSON 输出", "exit_code": proc.returncode,
                "stderr_tail": (proc.stderr or "")[-300:]}
    try:
        payload = json.loads(lines[-1])
    except ValueError:
        return {"error": "checker 末行不是合法 JSON", "exit_code": proc.returncode,
                "stderr_tail": (proc.stderr or "")[-300:]}
    payload["_exit_code"] = proc.returncode
    return payload


def red_items(payload: dict):
    if "error" in payload:
        return ["<checker-error>"]
    return sorted(c.get("id", "?") for c in payload.get("checks", []) if not c.get("pass"))


# ---------------------------------------------------------------------------
# 逐行处理
# ---------------------------------------------------------------------------
def historical_checker_version(row: dict):
    rg = row.get("regrade_2026_10_24") or {}
    if rg.get("checker_version"):
        return "regrade_2026_10_24: %s" % rg["checker_version"]
    jv = ((row.get("original_fields") or {}).get("judge") or {}).get("checker_version")
    if jv:
        return "original_fields.judge: %s" % jv
    return None


def classify_row(row: dict):
    """skip 预分类（按序先到先得）。返回 (None, reason, note) 或 (case, None, None)。"""
    if "not-a-run" in (row.get("scoring_status") or ""):
        return None, "not-a-run", "scoring_status 含 not-a-run（非运行行，重判无意义）"
    if row.get("adjudication") == "X":
        return None, "adjudication-X", ("判定 X（excluded/pending-fixed 等无效行），"
                                        "按口径默认跳过、重判无意义")
    case = row.get("case")
    if case not in CURRENT_CASES:
        return None, "archived-case", ("历史用例 %s 已归档（2-用例/_归档-v1），无现行 checker" % case)
    return case, None, None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="全量只读重判：运行总账全部行 × 现行 checker 对照（临时副本协议）")
    parser.add_argument("output", nargs="?", default=str(DEFAULT_OUT),
                        help="结果 JSON 输出路径（默认：脚本同目录 replay-all-results.json）")
    parser.add_argument("--plan-only", action="store_true",
                        help="只做行分类与 run_dir 解析干跑，不判分")
    args = parser.parse_args()

    if not LEDGER.is_file():
        print("[FATAL] 未找到运行总账：%s" % LEDGER, file=sys.stderr)
        return 2
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    rows = ledger.get("runs") or []

    checkers = {}
    for case in CURRENT_CASES:
        c = REPO / "2-用例" / case / "checker.py"
        if not c.is_file():
            print("[FATAL] 缺现行 checker：%s" % c, file=sys.stderr)
            return 2
        checkers[case] = {"path": str(c), "sha256": sha_file(c)}
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    results, n = [], {"rejudged": 0, "match": 0, "known-offset": 0,
                      "mismatch": 0, "unexplained-mismatch": 0,
                      "error": 0, "skip": 0}
    skip_by_reason = {}

    for row in rows:
        run_id = row.get("run_id", "?")
        case, skip_reason, skip_note = classify_row(row)
        base = {"run_id": run_id, "case": row.get("case"), "batch": row.get("batch"),
                "product": row.get("product"), "role": row.get("role"),
                "adjudication": row.get("adjudication"),
                "main_table_eligible": row.get("main_table_eligible"),
                "scoring_status": row.get("scoring_status")}
        if skip_reason:
            n["skip"] += 1
            skip_by_reason[skip_reason] = skip_by_reason.get(skip_reason, 0) + 1
            results.append(dict(base, status="skipped", skip_reason=skip_reason,
                                skip_note=skip_note))
            continue

        chosen, how, artifacts, examined, tier = locate(case, row)
        entry = dict(base, status="error", run_dir_candidates=examined)
        if chosen is None:
            existing = [c for c in examined if c["exists"]]
            if not existing and not examined:
                reason, note = "no-run-dir-field", "总账未登记 run_dir 且 sources 无法推断"
            elif not existing:
                private = any(is_private(Path(c["path"])) for c in examined)
                reason = "private-run-dir-absent" if private else "run-dir-missing"
                note = ("登记的 run_dir 在私有仓路径且本机不存在（其他机器或已清理）"
                        if private else "登记的 run_dir 本机缺失")
            else:
                reason, note = "artifact-missing", ("候选目录存在但判分产物不齐（尝试 %s 个候选）"
                                                    % len(examined))
            n["skip"] += 1
            skip_by_reason[reason] = skip_by_reason.get(reason, 0) + 1
            results.append(dict(base, status="skipped", skip_reason=reason, skip_note=note,
                                run_dir_candidates=examined))
            continue

        entry["run_dir_resolved"] = str(chosen)
        entry["run_dir_how"] = how
        entry["artifact_tier"] = tier
        primary = examined[0] if examined else None
        if tier == "artifact-package":
            entry["artifact_note"] = ("全部候选均无完整判分产物，退用证据包 artifacts 快照"
                                      "（可能不完整，先例：收紧批收据 §1 r20261026 快照截断）：%s"
                                      % chosen)
        elif primary and Path(primary["path"]).resolve() != chosen:
            entry["artifact_note"] = ("总账首选候选无完整判分产物，改以 %s 为判分对象：%s"
                                      % (how, chosen))
        entry["artifact_source"] = str(artifacts[0].parent)
        entry["artifact_sha256"] = {p.name: sha_file(p) for p in artifacts}
        ledger_recorded = {"raw_reward": row.get("raw_reward"),
                           "raw_weighted": row.get("raw_weighted")}
        hist_ver = historical_checker_version(row)
        if hist_ver:
            ledger_recorded["historical_checker_version"] = hist_ver

        if args.plan_only:
            entry.update(status="planned", ledger_recorded=ledger_recorded)
            results.append(entry)
            continue

        started = time.monotonic()
        try:
            with tempfile.TemporaryDirectory(prefix="replay-all-") as td:
                tmp_root = Path(td)
                run = build_temp_run(case, chosen, artifacts, tmp_root)
                staged, checker_path = stage_case(case, tmp_root)
                payload = grade(staged, run)
        except subprocess.TimeoutExpired:
            payload = {"error": "判分超时（>%ds）" % GRADE_TIMEOUT_S}
        except (OSError, ValueError) as exc:
            payload = {"error": "临时副本重组失败：%s" % exc}
        entry["duration_ms"] = int((time.monotonic() - started) * 1000)

        if "error" in payload:
            n["error"] += 1
            entry.update(status="error", error_class=("grade-timeout" if "超时" in payload["error"]
                                                      else "grade-error"),
                         error=payload["error"],
                         stderr_tail=payload.get("stderr_tail"),
                         ledger_recorded=ledger_recorded)
            results.append(entry)
            print("%-58s ERROR %s" % (run_id, payload["error"]))
            continue

        replay = {"checker": checkers[case]["path"],
                  "checker_sha256": checkers[case]["sha256"],
                  "checker_version": payload.get("checker_version"),
                  "reward": payload.get("reward"), "weighted": payload.get("weighted")}
        entry.update(status="rejudged", ledger_recorded=ledger_recorded,
                     replay=replay)

        if same_score(replay["reward"], replay["weighted"],
                      ledger_recorded["raw_reward"], ledger_recorded["raw_weighted"]):
            entry["verdict"] = "match"
            n["match"] += 1
        elif (case == "bird-ca-schools-15"
              and offset_key(run_id) is not None
              and same_score(ledger_recorded["raw_reward"], ledger_recorded["raw_weighted"],
                             *KNOWN_Q26_OFFSET[offset_key(run_id)][:2])
              and same_score(replay["reward"], replay["weighted"],
                             *KNOWN_Q26_OFFSET[offset_key(run_id)][2:])):
            entry["verdict"] = "known-offset"
            entry["known_offset_basis"] = KNOWN_Q26_BASIS
            n["known-offset"] += 1
        else:
            entry["verdict"] = "mismatch"
            entry["red_items"] = red_items(payload)
            if (norm_run_id(run_id) == norm_run_id(LCB_JITTER_RUN)
                    and replay["reward"] == ledger_recorded["raw_reward"]
                    and same_score(replay["reward"], replay["weighted"], *LCB_JITTER_SIGNATURE)):
                entry["prior_attribution"] = LCB_JITTER_NOTE  # 已按既往查因签名复现，不计未查因
            else:
                n["unexplained-mismatch"] += 1
            n["mismatch"] += 1
        n["rejudged"] += 1
        results.append(entry)
        print("%-58s r=%s w=%s (总账 %s/%s) %s%s" % (
            run_id, replay["reward"], replay["weighted"],
            ledger_recorded["raw_reward"], ledger_recorded["raw_weighted"],
            entry["verdict"],
            "" if entry["verdict"] == "match"
            else "  <- %s" % (entry.get("known_offset_basis") or
                              entry.get("prior_attribution") or "需查因")[:52]))

    mismatches = [r for r in results if r.get("verdict") == "mismatch"]
    unexplained = [r for r in mismatches if not r.get("prior_attribution")]
    summary = {
        "n_rows_total": len(rows),
        "n_rejudged": n["rejudged"],
        "n_match": n["match"],
        "n_known_offset": n["known-offset"],
        "n_mismatch": n["mismatch"],
        "n_unexplained_mismatch": len(unexplained),
        "n_error": n["error"],
        "n_skip": n["skip"],
        "skip_by_reason": skip_by_reason,
        "mismatch_run_ids": [r["run_id"] for r in mismatches],
        "unexplained_mismatch_run_ids": [r["run_id"] for r in unexplained],
        "error_run_ids": [r["run_id"] for r in results if r.get("status") == "error"],
    }
    out = {
        "tool": "4-打分细则/判卷回归/replay_all.py",
        "schema_version": 1,
        "generated_at": now,
        "plan_only": bool(args.plan_only),
        "ledger": str(LEDGER),
        "protocol": ("只读全量重判：判分在 /tmp 临时副本（canonical inputs + 历史产物重组，"
                     "先例 bird-q26-并入/replay_2026_10_26.py 与收紧批 replay_2026_10_27.py）；"
                     "历史 run_dir 零写入；known-offset 仅认 bird-q26 收据 §5 对照表"),
        "checkers": checkers,
        "summary": summary,
        "rows": results,
    }
    out_path = Path(args.output)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    if args.plan_only:
        print("== plan-only：可重判 %d / skip %d ==" % (
            sum(1 for r in results if r.get("status") == "planned"), n["skip"]))
    else:
        print("== 可重判 %d：一致 %d / 已知偏移 %d / 不一致 %d（其中既往查因复现 %d）"
              "｜ 重判失败 %d ｜ skip %d ==" % (
                  n["rejudged"], n["match"], n["known-offset"], n["mismatch"],
                  n["mismatch"] - len(unexplained), n["error"], n["skip"]))
        for r in mismatches:
            rep = r.get("replay") or {}
            led = r.get("ledger_recorded") or {}
            print("  不一致 %s (%s)：总账 %s/%s → 重判 %s/%s ｜ 现行 checker v%s sha=%s…%s" % (
                r["run_id"], r["case"], led.get("raw_reward"), led.get("raw_weighted"),
                rep.get("reward"), rep.get("weighted"), rep.get("checker_version"),
                (rep.get("checker_sha256") or "")[:8],
                ("｜既往查因：%s" % r["prior_attribution"][:40]) if r.get("prior_attribution") else ""))
    print("skip 按原因：%s" % json.dumps(skip_by_reason, ensure_ascii=False))
    print("结果已写入：%s" % out_path)
    # 退出码：0 = 无「未查因不一致」且无重判失败；既往查因的已知抖动复现仍逐行列出但不判翻转
    return 0 if (len(unexplained) == 0 and n["error"] == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
