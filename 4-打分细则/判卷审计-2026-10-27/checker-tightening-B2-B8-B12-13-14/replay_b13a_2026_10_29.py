#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B13a 合同回放（2026-10-29，盲审 D3 补证）：before（收紧前字节）vs after（现行 2-用例 字节）。

与 replay_2026_10_27.py 的关系：协议完整继承（回放对象、只读协议、/tmp 临时副本 canonical
输入重组、逐场 before/after 对照、ledger_match、flip 硬闸门），不改动原脚本与其收据。
唯一实质差异 = after 轨：

- replay_2026_10_27.py 的 after = 本目录 after/<case>/checker.py（2026-10-27 归档字节；
  其中 cargo 为 B13a 并入前字节 70acdbb7…，即盲审 D3 指出的缺陷）；
- 本脚本 after = 现行 REPO/2-用例/<case>/checker.py 字节（bird 994be0b3… / lcb 63845361… /
  cargo d84b1111…，即含 B13a 的现行合同），运行前对三 SHA 前缀自证，不符即拒跑。

行集冻结规则（lead 裁决 B，2026-10-29）：回放行集 = 2026-10-27 19:28 收据 replay-results.json
的 41 行全集（24 replayed + 17 skipped）；排除其后入账行——当前唯一实例
run_id=r20261027-wb-lcb-sandbox/workbuddy/lcb-recent-hard-4（10-27 19:28 后入总账，
eligible 且 run_dir 本机存在）。锚点 = AUDIT.md D3「下一步」原文「用 d84b1111 对同一 24 场重跑」。

禁读边界：本脚本机械复制历史产物与 canonical 输入，不经手 truth.json / solution/ 内容；
checker 只以子进程判分方式调用。

用法：python3 -B 4-打分细则/判卷审计-2026-10-27/checker-tightening-B2-B8-B12-13-14/replay_b13a_2026_10_29.py [输出.json]
"""
from __future__ import annotations

import datetime as dt
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
OLD_RECEIPT = HERE / "replay-results.json"
DEFAULT_OUT = HERE / "replay-b13a-results.json"

CASES = ("bird-ca-schools-15", "lcb-recent-hard-4", "tb-cargo-plan")

# after 轨自证：现行 2-用例/<case>/checker.py 的 SHA-256 前缀（封印前实测，盲审 D3 口径）
AFTER_EXPECTED_PREFIX = {
    "bird-ca-schools-15": "994be0b3",
    "lcb-recent-hard-4": "63845361",
    "tb-cargo-plan": "d84b1111",
}

# 行集冻结：排除 2026-10-27 19:28 收据之后入总账的行（lead 裁决 B；当前唯一实例）
EXCLUDED_ROWSET_RULE = (
    "行集冻结=2026-10-27 19:28 收据 replay-results.json 的 41 行全集（24 replayed + 17 skipped）；"
    "排除其后入账行：当前唯一实例 run_id=r20261027-wb-lcb-sandbox/workbuddy/lcb-recent-hard-4"
    "（eligible 且 run_dir 本机存在，但 10-27 19:28 后才入总账，不在旧收据 41 行内）；"
    "锚点=AUDIT.md D3 下一步原文「用 d84b1111 对同一 24 场重跑」")


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checker_path(stage: str, case: str) -> Path:
    if stage == "after_current":
        return REPO / "2-用例" / case / "checker.py"
    return HERE / stage / case / "checker.py"


def verify_after_track() -> dict:
    """after 轨三 SHA 自证：现行字节前缀必须与封印口径一致，否则拒跑。"""
    check = {}
    for case in CASES:
        p = checker_path("after_current", case)
        h = sha(p.read_bytes())
        check[case] = {"path": str(p), "sha256": h,
                       "expected_prefix": AFTER_EXPECTED_PREFIX[case],
                       "prefix_match": h.startswith(AFTER_EXPECTED_PREFIX[case])}
    if not all(v["prefix_match"] for v in check.values()):
        print("after 轨自证失败，拒跑：" + json.dumps(check, ensure_ascii=False, indent=1))
        sys.exit(2)
    return check


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


def stage_case(checker: Path, stage_label: str, case: str, tmp_root: Path) -> Path:
    """组装临时用例目录：checker 副本 + canonical truth.json / inputs 符号链接（全只读引用）。"""
    case_dir = REPO / "2-用例" / case
    staged = tmp_root / ("case_" + stage_label + "_" + case)
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
    return sorted(c["id"] for c in payload.get("checks", []) if not c.get("pass"))


def main() -> int:
    after_selfcheck = verify_after_track()

    # ---- 行集冻结（lead 裁决 B）：旧收据 41 行全集 ----
    old = json.loads(OLD_RECEIPT.read_text(encoding="utf-8"))
    frozen_rows = list(old["runs"]) + list(old["skipped_rows"])
    frozen_ids = {r["run_id"] for r in frozen_rows}
    old_target_ids = {r["run_id"] for r in old["runs"]}

    # 对照现行总账：同口径合格行与被排除行（收据 corrections 需要的事实）
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    ledger_rows = {r["run_id"]: r for r in ledger["runs"] if r.get("case") in CASES}
    current_targets = set()
    for rid, row in ledger_rows.items():
        run_dir = resolve_run_dir(row)
        if row.get("main_table_eligible") is True and run_dir and run_dir.is_dir():
            current_targets.add(rid)
    excluded_now = sorted(current_targets - frozen_ids)
    missing_frozen = sorted(frozen_ids - set(ledger_rows))

    # 24 个回放目标的 run_dir 必须仍然在本机（环境漂移即中止，不静默 skip）
    targets = []
    for r in old["runs"]:
        run_dir = resolve_run_dir(ledger_rows[r["run_id"]]) if r["run_id"] in ledger_rows else None
        if run_dir is None or not run_dir.is_dir():
            print("冻结行集的 run_dir 不在本机，中止：%s -> %s" % (r["run_id"], run_dir))
            return 2
        targets.append({"run_id": r["run_id"], "case": r["case"], "run_dir": str(run_dir),
                        "main_table_eligible": r.get("main_table_eligible"),
                        "ledger_recorded_old_receipt": r.get("ledger_recorded"),
                        "ledger_recorded_current": {"raw_reward": ledger_rows[r["run_id"]].get("raw_reward"),
                                                     "raw_weighted": ledger_rows[r["run_id"]].get("raw_weighted")}})
    # 总账登记分与旧收据登记分漂移检测（分叉即记 corrections，不静默择一）
    ledger_drift = [t["run_id"] for t in targets
                    if t["ledger_recorded_old_receipt"] != t["ledger_recorded_current"]]
    print("冻结行集回放 %d 场（skip 冻结 %d 行）；现行总账同口径合格行=%d，按冻结规则排除=%d %s"
          % (len(targets), len(old["skipped_rows"]), len(current_targets), len(excluded_now), excluded_now))

    results, n_flip, n_ledger_match = [], 0, 0
    for rec in targets:
        run_dir = Path(rec["run_dir"])
        entry = {"run_id": rec["run_id"], "case": rec["case"], "run_dir": rec["run_dir"],
                 "main_table_eligible": rec["main_table_eligible"],
                 "ledger_recorded": rec["ledger_recorded_current"]}
        entry["artifact_source"] = None
        entry["artifact_sha256"] = {}
        with tempfile.TemporaryDirectory(prefix="b13a-replay-") as td:
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
            before = grade(stage_case(checker_path("before", rec["case"]), "before",
                                      rec["case"], tmp_root), run)
            after = grade(stage_case(checker_path("after_current", rec["case"]), "after_current",
                                     rec["case"], tmp_root), run)
        b_reward, b_weighted = score_of(rec["case"], before)
        a_reward, a_weighted = score_of(rec["case"], after)
        entry["before"] = {"checker": str(checker_path("before", rec["case"])),
                           "checker_version": before.get("checker_version"),
                           "reward": b_reward, "weighted": b_weighted}
        entry["after"] = {"checker": str(checker_path("after_current", rec["case"])),
                          "checker_sha256": after_selfcheck[rec["case"]]["sha256"],
                          "checker_version": after.get("checker_version"),
                          "reward": a_reward, "weighted": a_weighted}
        flipped = (b_reward, b_weighted) != (a_reward, a_weighted)
        entry["flipped"] = flipped
        if flipped:
            entry["after_red_items"] = red_items(rec["case"], after)
            entry["before_red_items"] = red_items(rec["case"], before)
            n_flip += 1
        led = rec["ledger_recorded_current"]
        if (b_reward, b_weighted) == (led.get("raw_reward"), led.get("raw_weighted")):
            entry["ledger_match"] = True
            n_ledger_match += 1
        else:
            entry["ledger_match"] = False
        results.append(entry)
        print("%-52s before r=%s w=%s -> after(current) r=%s w=%s flip=%s ledger_match=%s"
              % (rec["run_id"], b_reward, b_weighted, a_reward, a_weighted,
                 flipped, entry["ledger_match"]))

    corrections = [{
        "id": "b13a-replay-rowset-freeze",
        "at": now_iso(),
        "note": ("行集分歧与裁决：按绑定规范同口径核对现行总账，合格回放对象=25（bird 10 / lcb 5 / cargo 10），"
                 "与验收预期 n_replayed=24 冲突；diff 定位为 %s 于 2026-10-27 19:28 收据刷新后入总账。"
                 "builder 停手问 lead，lead 裁决 B：行集冻结为旧收据 41 行口径（本收据执行口径），"
                 "排除该行且不做第 25 场补充运行（范围纪律）；锚点=AUDIT.md D3 下一步原文「用 d84b1111 对同一 24 场重跑」。"
                 % excluded_now),
        "excluded_rows": excluded_now,
        "exclusion_rule": EXCLUDED_ROWSET_RULE,
    }]
    if missing_frozen:
        corrections.append({"id": "b13a-replay-frozen-rows-not-in-ledger", "at": now_iso(),
                            "note": "冻结行集中以下 run_id 已不在现行总账（如实登记，行集仍按旧收据）：%s" % missing_frozen,
                            "rows": missing_frozen})
    if ledger_drift:
        corrections.append({"id": "b13a-replay-ledger-recorded-drift", "at": now_iso(),
                            "note": "以下行的总账 raw_reward/raw_weighted 与 2026-10-27 收据快照不一致（ledger_match 按现行总账值计算）：%s" % ledger_drift,
                            "rows": ledger_drift})

    summary = {
        "date": "2026-10-29",
        "protocol": ("只读回放：判分在 /tmp 临时副本（canonical inputs + 历史产物重组）；历史 run_dir 零写入"
                     "（先例 bird-q26-并入/replay_2026_10_26.py，协议完整继承 replay_2026_10_27.py）。"
                     "after 轨=现行 2-用例/<case>/checker.py 字节（含 B13a），before 轨=本目录 before/<case>/checker.py"
                     "（与 2026-10-27 收据逐字节相同）。" + EXCLUDED_ROWSET_RULE),
        "rowset_freeze": {"rule": EXCLUDED_ROWSET_RULE,
                          "old_receipt": "replay-results.json (2026-10-27 19:28)",
                          "frozen_rows": len(frozen_ids), "replayed": len(targets),
                          "skipped": len(old["skipped_rows"]),
                          "excluded_current_ledger_rows": excluded_now,
                          "current_ledger_same_criteria_targets": len(current_targets)},
        "before_contract": {c: str(checker_path("before", c)) for c in CASES},
        "after_contract": {c: str(checker_path("after_current", c)) for c in CASES},
        "after_track_selfcheck": {"sha256": {c: after_selfcheck[c]["sha256"] for c in CASES},
                                   "expected_prefix": AFTER_EXPECTED_PREFIX,
                                   "prefix_match": {c: after_selfcheck[c]["prefix_match"] for c in CASES},
                                   "note": "after 轨=现行合同字节自证（盲审 D3 要求）；before 轨见 2026-10-27 收据 §7"},
        "n_replayed": len([r for r in results if "error" not in r]),
        "n_skip": len(old["skipped_rows"]),
        "n_ledger_match": n_ledger_match,
        "n_flipped": n_flip,
        "skipped_rows": old["skipped_rows"],
        "runs": results,
        "corrections": corrections,
        "generated_at": now_iso(),
    }
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("replayed=%d skip=%d ledger_match=%d flipped=%d -> %s"
          % (summary["n_replayed"], summary["n_skip"], n_ledger_match, n_flip, out.name))
    if n_flip > 0:
        print("硬闸门触发：存在 before→after 翻转，立即停手并报 lead（收据已落盘）")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
