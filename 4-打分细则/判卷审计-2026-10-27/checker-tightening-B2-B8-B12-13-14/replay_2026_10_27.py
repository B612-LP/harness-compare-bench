#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""checker 收紧批回放（2026-10-27）：before（现行 checker）vs after（收紧后 checker）。

- 回放对象 = 运行总账-2026-10-24.json 中 case ∈ {bird-ca-schools-15, lcb-recent-hard-4,
  tb-cargo-plan} 且 main_table_eligible=true 且 run_dir（original_fields.run_dir 或
  original_fields.judge.run_dir，~ 展开）在本机存在的行；其余行记 skip。
- 历史现场只读：只从 run_dir 读取判分产物（answers.jsonl / solutions/*.py / inputs/app/*.py），
  判分一律在 /tmp 临时副本进行（canonical inputs + 历史产物重组），不写任何历史目录
  （先例：判卷审计-2026-10-26/bird-q26-并入/replay_2026_10_26.py 的临时副本协议——
  r1028/r1029 工作区仍带 v1.1 字节 questions.json，直接对历史目录重判会误触
  input_integrity 守卫，故必须用 canonical 输入重组）。
- before = 本目录 before/<case>/checker.py（收紧前字节）；after = after/<case>/checker.py。
- 硬闸门证据：任一历史行 before→after 的 reward 或 weighted 变化即记 flipped=true，
  并附 after 判红项（用于定位触发翻转的收紧子项）。

用法：python3 -B 4-打分细则/判卷审计-2026-10-27/checker-tightening-B2-B8-B12-13-14/replay_2026_10_27.py [输出.json]
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
LEDGER = REPO / "5-评测报告" / "运行总账-2026-10-24.json"
DEFAULT_OUT = HERE / "replay-results.json"

CASES = ("bird-ca-schools-15", "lcb-recent-hard-4", "tb-cargo-plan")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checker_path(stage: str, case: str) -> Path:
    return HERE / stage / case / "checker.py"


def resolve_run_dir(row: dict):
    """run_dir 解析：original_fields.run_dir → original_fields.judge.run_dir（~ 展开）。"""
    of = row.get("original_fields") or {}
    for cand in (of.get("run_dir"), (of.get("judge") or {}).get("run_dir")):
        if cand:
            return Path(os.path.expanduser(cand))
    return None


def find_bird_answers(run_dir: Path):
    for cand in (run_dir / "answers.jsonl", run_dir / "workspace" / "answers.jsonl"):
        if cand.is_file():
            return cand
    art = run_dir / "artifacts"
    if art.is_dir():
        hits = sorted(art.glob("*.answers.jsonl"))
        if hits:
            return hits[0]
    return None


def find_lcb_solutions(run_dir: Path):
    for cand in (run_dir / "solutions", run_dir / "workspace" / "solutions"):
        if cand.is_dir():
            return sorted(cand.glob("*.py"))
    art = run_dir / "artifacts"
    if art.is_dir():
        return sorted(p for p in art.glob("*.py")
                      if p.name.split(".", 1)[-1].startswith(("abc38",)))
    return []


def cargo_workspace_fallback(run_id: str) -> Path:
    """证据包 artifacts/ 是部分快照时的兜底：同批次同产品的工作区目录（其 inputs/app 完整，
    即历史判分实际对象）。仅当该目录存在且含 inputs/app/dispatch.py 时返回。"""
    parts = run_id.split("/")
    if len(parts) < 3:
        return None
    ws = Path.home() / "bench-workspaces" / parts[0] / parts[1] / parts[2]
    if (ws / "inputs" / "app" / "dispatch.py").is_file():
        return ws
    return None


def build_temp_run(case: str, run_id: str, run_dir: Path, tmp_root: Path):
    """按先例协议重组 run_dir：canonical inputs 副本 + 历史产物。不触碰历史目录。

    返回 (run_dir, artifact_paths, note)：artifact_paths 仅用于收据登记 SHA-256。
    """
    run = tmp_root / "run"
    run.mkdir()
    case_dir = REPO / "2-用例" / case
    artifacts, note = [], None
    if case == "bird-ca-schools-15":
        answers = find_bird_answers(run_dir)
        if answers is None:
            raise FileNotFoundError("未找到 answers.jsonl：%s" % run_dir)
        shutil.copytree(case_dir / "inputs", run / "inputs")
        shutil.copy2(answers, run / "answers.jsonl")
        artifacts = [answers]
    elif case == "lcb-recent-hard-4":
        sols = find_lcb_solutions(run_dir)
        if not sols:
            raise FileNotFoundError("未找到 solutions/*.py：%s" % run_dir)
        (run / "solutions").mkdir()
        for p in sols:
            shutil.copy2(p, run / "solutions" / _lcb_target_name(p))
        artifacts = sols
    elif case == "tb-cargo-plan":
        # 判分对象取历史判分的实际对象，优先级：run_dir/inputs/app → run_dir/workspace/inputs/app
        # → 同批次工作区（bench-workspaces/<batch>/<product>/<case>，其 inputs/app 完整）
        # → 证据包 artifacts/*.py（最后手段）。
        app = None
        for cand in (run_dir / "inputs" / "app", run_dir / "workspace" / "inputs" / "app"):
            if (cand / "dispatch.py").is_file():
                app = cand
                break
        if app is None:
            ws = cargo_workspace_fallback(run_id)
            if ws is not None:
                note = ("ledger run_dir 仅带证据包（artifacts/ 为导出快照），"
                        "改以同批次工作区为判分对象（历史判分的实际对象，复算与总账一致）：%s" % ws)
                run_dir = ws
                app = ws / "inputs" / "app"
        if app is not None:
            code = sorted(app.glob("*.py"))
        else:
            art = run_dir / "artifacts"
            code = sorted(art.glob("*.py")) if art.is_dir() else []
        if not code:
            raise FileNotFoundError("未找到 inputs/app/*.py：%s" % run_dir)
        shutil.copytree(case_dir / "inputs", run / "inputs")
        for p in code:
            shutil.copy2(p, run / "inputs" / "app" / p.name)
        artifacts = code
    else:
        raise ValueError(case)
    return run, artifacts, note


def _lcb_target_name(p: Path) -> str:
    """artifacts/<id>.abc387_f.py → abc387_f.py；solutions/abc387_f.py → 原名。"""
    name = p.name
    if "." in name and name.split(".", 1)[1].startswith("abc"):
        return name.split(".", 1)[1]
    return name


def stage_case(checker: Path, case: str, tmp_root: Path) -> Path:
    """组装临时用例目录：checker 副本 + canonical truth.json / inputs 符号链接（全只读引用）。"""
    case_dir = REPO / "2-用例" / case
    staged = tmp_root / ("case_" + checker.parent.parent.name + "_" + case)
    staged.mkdir()
    shutil.copy2(checker, staged / "checker.py")
    (staged / "truth.json").symlink_to(case_dir / "truth.json")
    (staged / "inputs").symlink_to(case_dir / "inputs", target_is_directory=True)
    return staged


def grade(staged_case: Path, run: Path) -> dict:
    proc = subprocess.run([sys.executable, "-B", str(staged_case / "checker.py"),
                           str(run), "--json"],
                          capture_output=True, text=True, timeout=900, cwd=str(run))
    lines = [ln for ln in (proc.stdout or "").strip().splitlines() if ln.strip()]
    if not lines:
        return {"error": "checker 无 JSON 输出", "exit_code": proc.returncode,
                "stderr_tail": (proc.stderr or "")[-200:]}
    payload = json.loads(lines[-1])
    payload["_exit_code"] = proc.returncode
    return payload


def score_of(case: str, payload: dict):
    if "error" in payload:
        return None, None
    return payload.get("reward"), payload.get("weighted")


def red_items(case: str, payload: dict):
    if "error" in payload:
        return ["<checker-error>"]
    if case == "bird-ca-schools-15":
        return sorted(c["id"] for c in payload.get("checks", []) if not c.get("pass"))
    if case == "lcb-recent-hard-4":
        return sorted(c["id"] for c in payload.get("checks", []) if not c.get("pass"))
    return sorted(c["id"] for c in payload.get("checks", []) if not c.get("pass"))


def main() -> int:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    rows = [r for r in ledger["runs"] if r.get("case") in CASES]
    targets, skips = [], []
    for row in rows:
        run_dir = resolve_run_dir(row)
        exists = bool(run_dir) and run_dir.is_dir()
        rec = {"run_id": row["run_id"], "case": row["case"],
               "run_dir": str(run_dir) if run_dir else None,
               "main_table_eligible": row.get("main_table_eligible"),
               "ledger_recorded": {"raw_reward": row.get("raw_reward"),
                                   "raw_weighted": row.get("raw_weighted")}}
        (targets if (row.get("main_table_eligible") is True and exists) else skips).append(rec)
    print("回放 %d 场 / skip %d 行" % (len(targets), len(skips)))

    results, n_flip, n_ledger_match = [], 0, 0
    for rec in targets:
        run_dir = Path(rec["run_dir"])
        entry = dict(rec)
        entry["artifact_source"] = None
        entry["artifact_sha256"] = {}
        with tempfile.TemporaryDirectory(prefix="tighten-replay-") as td:
            tmp_root = Path(td)
            try:
                run, artifacts, ws_note = build_temp_run(rec["case"], rec["run_id"],
                                                         run_dir, tmp_root)
            except FileNotFoundError as exc:
                entry["error"] = str(exc)
                results.append(entry)
                print("%-52s ERROR %s" % (rec["run_id"], exc))
                continue
            if ws_note:
                entry["artifact_note"] = ws_note
            if artifacts:
                entry["artifact_source"] = str(artifacts[0].parent)
                for p in artifacts:
                    entry["artifact_sha256"][p.name] = sha(p.read_bytes())
            before = grade(stage_case(checker_path("before", rec["case"]), rec["case"], tmp_root), run)
            after = grade(stage_case(checker_path("after", rec["case"]), rec["case"], tmp_root), run)
        b_reward, b_weighted = score_of(rec["case"], before)
        a_reward, a_weighted = score_of(rec["case"], after)
        entry["before"] = {"checker": str(checker_path("before", rec["case"])),
                           "checker_version": before.get("checker_version"),
                           "reward": b_reward, "weighted": b_weighted}
        entry["after"] = {"checker": str(checker_path("after", rec["case"])),
                          "checker_version": after.get("checker_version"),
                          "reward": a_reward, "weighted": a_weighted}
        flipped = (b_reward, b_weighted) != (a_reward, a_weighted)
        entry["flipped"] = flipped
        if flipped:
            entry["after_red_items"] = red_items(rec["case"], after)
            entry["before_red_items"] = red_items(rec["case"], before)
            n_flip += 1
        led = rec["ledger_recorded"]
        if (b_reward, b_weighted) == (led.get("raw_reward"), led.get("raw_weighted")):
            entry["ledger_match"] = True
            n_ledger_match += 1
        else:
            entry["ledger_match"] = False
        results.append(entry)
        print("%-52s before r=%s w=%s -> after r=%s w=%s flip=%s ledger_match=%s"
              % (rec["run_id"], b_reward, b_weighted, a_reward, a_weighted,
                 flipped, entry["ledger_match"]))

    summary = {
        "date": "2026-10-27",
        "protocol": "只读回放：判分在 /tmp 临时副本（canonical inputs + 历史产物重组）；"
                    "历史 run_dir 零写入（先例 bird-q26-并入/replay_2026_10_26.py）",
        "before_contract": {c: str(checker_path("before", c)) for c in CASES},
        "after_contract": {c: str(checker_path("after", c)) for c in CASES},
        "n_replayed": len([r for r in results if "error" not in r]),
        "n_skip": len(skips),
        "n_ledger_match": n_ledger_match,
        "n_flipped": n_flip,
        "skipped_rows": skips,
        "runs": results,
    }
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("replayed=%d skip=%d ledger_match=%d flipped=%d -> %s"
          % (summary["n_replayed"], len(skips), n_ledger_match, n_flip, out.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
