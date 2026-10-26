#!/usr/bin/env python3
"""BIRD q26 并入回放（2026-10-26）：旧合同 v1.1 vs 新合同 v1.2-q26-frpm。

- 旧合同从仓内补充材料包解出（bird-q26/baseline-1.1，源仓 a2234fc 只读快照）；
- 新合同 = 当前正式用例目录 2-用例/bird-ca-schools-15（v1.2-q26-frpm，已并入）；
- 回放对象 = 运行总账-2026-10-24.json 中 case=bird-ca-schools-15 且 adjudication=V 的全部运行；
- 历史答案只读：工作区文件缺失时回退 git HEAD blob；逐场核对总账登记的 SHA-256；
- 判分在 /tmp 临时副本进行（复制对应版本 canonical inputs），不写 3-表现现场 与任何历史产物。

用法：python3 -B 4-打分细则/判卷审计-2026-10-26/bird-q26-并入/replay_2026_10_26.py [输出.json]
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CASE_DIR = REPO / "2-用例" / "bird-ca-schools-15"
ZIP = REPO / "5-评测报告" / "补充材料" / "2026-10-24" / "候选与复核.zip"
LEDGER = REPO / "5-评测报告" / "运行总账-2026-10-24.json"
DEFAULT_OUT = HERE / "replay-results.json"

ANSWERS_RELPATHS = {
    "r1025-candidates/bird-ca-schools-15__codex":
        "3-表现现场/r1025-candidates/bird-ca-schools-15__codex/answers.jsonl",
    "r1025-candidates/bird-ca-schools-15__dsh":
        "3-表现现场/r1025-candidates/bird-ca-schools-15__dsh/answers.jsonl",
    "r1026-desktop-15/runs/doubao/bird-ca-schools-15":
        "3-表现现场/r1026-desktop-15/runs/doubao/bird-ca-schools-15/answers.jsonl",
    "r1026-desktop-15/runs/workbuddy/bird-ca-schools-15":
        "3-表现现场/r1026-desktop-15/runs/workbuddy/bird-ca-schools-15/answers.jsonl",
    "r1028-repeats/runs/codex__bird-ca-schools-15__r2":
        "3-表现现场/r1028-repeats/runs/codex__bird-ca-schools-15__r2/workspace/answers.jsonl",
    "r1028-repeats/runs/codex__bird-ca-schools-15__r3":
        "3-表现现场/r1028-repeats/runs/codex__bird-ca-schools-15__r3/workspace/answers.jsonl",
    "r1028-repeats/runs/dsh__bird-ca-schools-15__r2":
        "3-表现现场/r1028-repeats/runs/dsh__bird-ca-schools-15__r2/workspace/answers.jsonl",
    "r1028-repeats/runs/dsh__bird-ca-schools-15__r3":
        "3-表现现场/r1028-repeats/runs/dsh__bird-ca-schools-15__r3/workspace/answers.jsonl",
    "r1029-desktop-auto/runs/doubao/bird-ca-schools-15":
        "3-表现现场/r1029-desktop-auto/runs/doubao/bird-ca-schools-15/workspace/answers.jsonl",
    "r1029-desktop-auto/runs/workbuddy/bird-ca-schools-15":
        "3-表现现场/r1029-desktop-auto/runs/workbuddy/bird-ca-schools-15/workspace/answers.jsonl",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_bytes(rel: str) -> tuple[bytes, str]:
    phys = REPO / rel
    if phys.is_file():
        return phys.read_bytes(), "worktree"
    proc = subprocess.run(["git", "-C", str(REPO), "show", "HEAD:" + rel],
                          capture_output=True, check=True)
    return proc.stdout, "git-blob"


def grade(case_dir: Path, answers: bytes) -> dict:
    with tempfile.TemporaryDirectory(prefix="bird-q26-replay-") as td:
        run = Path(td) / "run"
        run.mkdir()
        shutil.copytree(case_dir / "inputs", run / "inputs")
        (run / "answers.jsonl").write_bytes(answers)
        proc = subprocess.run([sys.executable, "-B", str(case_dir / "checker.py"),
                               str(run), "--json"], capture_output=True, text=True)
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
        payload["_exit_code"] = proc.returncode
        return payload


def main() -> int:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    rows = []
    ledger_sha = {}
    for row in ledger["runs"]:
        if row.get("case") == "bird-ca-schools-15" and row.get("adjudication") == "V":
            rel = ANSWERS_RELPATHS[row["run_id"]]
            for src in row.get("sources", []):
                if src["path"] == rel:
                    ledger_sha[rel] = src["sha256"]
            rows.append((row["run_id"], rel, row.get("raw_reward"), row.get("raw_weighted")))
    assert len(rows) == 10, "期望 10 场有效 bird 运行，实际 %d" % len(rows)

    with tempfile.TemporaryDirectory(prefix="bird-q26-baseline-") as td:
        with zipfile.ZipFile(ZIP) as zf:
            base = Path(td)
            for name in zf.namelist():
                if name.startswith("bird-q26/baseline-1.1/"):
                    zf.extract(name, base)
            old_case = base / "bird-q26" / "baseline-1.1"

        results, only_q26, binary_ok = [], True, True
        for run_id, rel, led_reward, led_weighted in rows:
            data, origin = load_bytes(rel)
            digest = sha(data)
            sha_ok = ledger_sha.get(rel, digest) == digest
            old = grade(old_case, data)
            new = grade(CASE_DIR, data)
            old_failed = set(old.get("failed_questions", []))
            new_failed = set(new.get("failed_questions", []))
            flipped = sorted(old_failed ^ new_failed)
            if flipped != ["26"]:
                only_q26 = False
            if old["reward"] != new["reward"]:
                binary_ok = False
            results.append({
                "run_id": run_id, "answers_origin": origin, "answers_sha256": digest,
                "ledger_sha256_match": sha_ok,
                "ledger_recorded": {"reward": led_reward, "weighted": led_weighted},
                "old_v1.1": {"checker_version": old["checker_version"], "correct": old["correct"],
                             "weighted": old["weighted"], "reward": old["reward"],
                             "failed_questions": sorted(old_failed)},
                "new_v1.2-q26-frpm": {"checker_version": new["checker_version"],
                                      "contract_status": new.get("contract_status"),
                                      "correct": new["correct"], "weighted": new["weighted"],
                                      "reward": new["reward"], "failed_questions": sorted(new_failed)},
                "flipped_questions": flipped,
            })
            print("%-46s %s old %2d/15 w=%5.2f r=%d -> new %2d/15 w=%5.2f r=%d flip=%s"
                  % (run_id, origin, old["correct"], old["weighted"], old["reward"],
                     new["correct"], new["weighted"], new["reward"], flipped))

    summary = {
        "date": "2026-10-26",
        "old_contract": {"version": "1.1", "source": "候选与复核.zip bird-q26/baseline-1.1（源仓 a2234fc 快照）"},
        "new_contract": {"version": "1.2-q26-frpm", "source": "2-用例/bird-ca-schools-15（已并入正式）"},
        "n_valid_runs": len(results),
        "only_q26_flipped_in_all_runs": only_q26,
        "binary_reward_unchanged_in_all_runs": binary_ok,
        "runs": results,
    }
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("only_q26_flipped:", only_q26, "| binary_unchanged:", binary_ok, "| ->", out.name)
    return 0 if (only_q26 and binary_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
