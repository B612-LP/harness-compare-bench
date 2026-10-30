#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L6-A 判卷修订验收：历史复算 + gate 口径近似错误例（零模型、只读历史现场）。

断言组：
  A. 修前 checker 复跑冻结工作区 == 冻结 checker.stdout（证据可复现性）
  B. 修后 vs 修前：全部判分字段逐值相等（0 翻转）；输出键集恰增 {n_tasks, guards_used}
  C. gate 重算口径（gate.py:747-770 同构）：未篡改文档 → possible_raw==分母 15、
     earned_raw==correct、n_tasks==possible_raw、exp8==reported8
  D. 近似错误例 (a)：篡改 n_tasks=14 → judge.n_tasks ≠ possible_raw（gate 必拒）
  E. 近似错误例 (b)：guards_used 漏一项 → possible_raw=16 ≠ 分母 15（gate 必拒）
"""
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path("/Users/b612-lp/Documents/harness-compare-bench")
ARCHIVE = ROOT / "5-评测报告" / "L6判卷修订-2026-10-30"
CHECKER = ROOT / "2-用例" / "bird-ca-schools-15" / "checker.py"
PRE_REV = "79cebe0:2-用例/bird-ca-schools-15/checker.py"   # D1 与 L5 终点同字节（D1 未触 checker）
GUARDS = ["input_integrity", "answers_file", "answers_schema", "answers_coverage"]
DENOM = 15
SOURCES = {
    "l5-e3-wb-bird": ROOT / "3-表现现场/l5-20261030-wb-gateway/runs/l5-20261030-wb-gateway-bird-ca-schools-15-r1",
    "e2-aborted-wb-bird": ROOT / "3-表现现场/中止重封档案E2-20261030T0207/wb__bird-r1",
}
SCORE_FIELDS = ["reward", "weighted", "accuracy", "correct", "failed_questions",
                "checks", "n_questions", "threshold", "input_integrity"]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run_checker(checker_path: Path, ws: Path) -> dict:
    proc = subprocess.run([sys.executable, str(checker_path), str(ws), "--json"],
                          capture_output=True, text=True, timeout=600)
    for line in reversed([l for l in proc.stdout.splitlines() if l.strip().startswith("{")]):
        try:
            return json.loads(line)
        except Exception:
            continue
    raise SystemExit("checker 无 JSON 输出: %s" % (proc.stderr[-300:],))


def frozen_raw(run_dir: Path) -> dict:
    text = (run_dir / "checker.stdout").read_text(encoding="utf-8")
    for line in reversed([l for l in text.splitlines() if l.strip().startswith("{")]):
        try:
            return json.loads(line)
        except Exception:
            continue
    raise SystemExit("冻结 checker.stdout 无 JSON")


def normalize(doc: dict) -> dict:
    """比对口径归一：answers_file 的 note 内嵌 run_dir 绝对路径（冻结现场为仓外
    bench-workspaces 原路径，复跑为归档路径），路径本身非判分语义，置占位后比对。
    2026-10-30 r1 收据（13/15）即因未归一该路径产生的比对伪差，已废止留档。"""
    out = json.loads(json.dumps(doc))
    for c in out.get("checks", []):
        if isinstance(c, dict) and c.get("id") == "answers_file":
            c["note"] = "<answers_path>"
    return out


def gate_recompute(doc: dict, judge: dict):
    """gate.py:747-770 同构重算：guards_used 内 id 为守卫项，其余按 pass 计数。"""
    checks = doc["checks"]
    gset = set(judge.get("guards_used") or [])
    scored = [c for c in checks if c.get("id") not in gset]
    earned = sum(1 for c in scored if c.get("pass") is True)
    possible = len(scored)
    exp8 = round(100.0 * earned / possible, 8) if possible else None
    return {"earned_raw": earned, "possible_raw": possible, "exp8": exp8,
            "count_match": judge.get("correct") == earned and judge.get("n_tasks") == possible,
            "denom_match": possible == DENOM}


def main() -> int:
    results, all_ok = [], True

    def check(name, ok, detail=""):
        nonlocal all_ok
        results.append({"assert": name, "pass": bool(ok), "detail": detail})
        all_ok = all_ok and bool(ok)

    with tempfile.TemporaryDirectory() as td:
        # 修前 checker 需在含 truth/inputs 的用例目录结构内运行（HERE 解析）：
        # 临时用例目录 = 修前字节为 checker.py + 符号链接冻结 truth/solution/inputs。
        case_td = Path(td) / "case-pre-l6"
        case_td.mkdir()
        pre = case_td / "checker.py"
        pre.write_bytes(subprocess.run(["git", "-C", str(ROOT), "show", PRE_REV],
                                       capture_output=True, check=True).stdout)
        case_src = CHECKER.parent
        for rel in ("truth.json", "solution"):
            (case_td / rel).symlink_to(case_src / rel)
        (case_td / "inputs").symlink_to(case_src / "inputs")
        check("pre_checker_extracted", pre.is_file(),
              "sha256=" + sha256_file(pre)[:16])

        for label, run_dir in SOURCES.items():
            ws = run_dir / "workspace"
            frozen = normalize(frozen_raw(run_dir))
            rp = run_checker(pre, ws)
            check("A:%s 冻结证据可复现" % label,
                  all(normalize(frozen).get(k) == normalize(rp).get(k) for k in SCORE_FIELDS),
                  "reward frozen=%s rerun=%s" % (frozen.get("reward"), rp.get("reward")))
            rq = run_checker(CHECKER, ws)
            check("B:%s 修后判分零翻转" % label,
                  all(normalize(rq).get(k) == normalize(rp).get(k) for k in SCORE_FIELDS),
                  "reward pre=%s post=%s weighted pre=%s post=%s"
                  % (rp.get("reward"), rq.get("reward"), rp.get("weighted"), rq.get("weighted")))
            new_keys = set(rq) - set(rp)
            check("B:%s 键集恰增两键" % label,
                  new_keys == {"n_tasks", "guards_used"},
                  "new=%s" % sorted(new_keys))
            check("B:%s 新键值正确" % label,
                  rq.get("n_tasks") == DENOM and rq.get("guards_used") == GUARDS,
                  "n_tasks=%r guards=%r" % (rq.get("n_tasks"), rq.get("guards_used")))
            g = gate_recompute(rq, rq)
            check("C:%s gate 重算调和" % label,
                  g["denom_match"] and g["count_match"] and g["exp8"] == round(rq["weighted"], 8),
                  json.dumps(g, ensure_ascii=False))
            tam_a = json.loads(json.dumps(rq))
            tam_a["n_tasks"] = 14
            ga = gate_recompute(tam_a, tam_a)
            check("D:%s 篡改 n_tasks=14 被拒" % label,
                  not ga["count_match"], json.dumps(ga, ensure_ascii=False))
            tam_b = json.loads(json.dumps(rq))
            tam_b["guards_used"] = [x for x in GUARDS if x != "answers_schema"]
            gb = gate_recompute(tam_b, tam_b)
            check("E:%s guards_used 漏项被拒" % label,
                  not gb["denom_match"], json.dumps(gb, ensure_ascii=False))

    receipt = {"kind": "l6-judge-revision-acceptance", "tool": "l6_meta_recompute.py",
               "at": datetime.now().astimezone().isoformat(timespec="seconds"),
               "pre_revision_source": PRE_REV,
               "pre_checker_sha256": None,
               "post_checker_sha256": sha256_file(CHECKER),
               "counts": {"total": len(results), "passed": sum(1 for r in results if r["pass"]),
                          "failed": sum(1 for r in results if not r["pass"])},
               "assertions": results, "all_ok": all_ok, "live_doc_drift": []}
    out = ARCHIVE / "l6-meta-recompute-receipt.json"
    if out.exists():
        raise SystemExit("拒绝写入：收据已存在（write-once）")
    # pre 校验器字节在临时目录，直接从 git 现算哈希入档
    pre_bytes = subprocess.run(["git", "-C", str(ROOT), "show", PRE_REV],
                               capture_output=True, check=True).stdout
    receipt["pre_checker_sha256"] = hashlib.sha256(pre_bytes).hexdigest()
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"all_ok": all_ok, "counts": receipt["counts"], "receipt": str(out)},
                     ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
