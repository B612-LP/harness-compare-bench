#!/usr/bin/env python3
"""bird-schools15 判分器：逐题执行 gold SQL 与 pred SQL，结果集比对（exec-accuracy），通过率 ≥ 0.8 记 headline=1。"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BINARY = True


def normalize(rows):
    """把结果集归一成可比较的多重集：数字保留 6 位、None 记常量、行内保列序。"""
    out = []
    for row in rows:
        cells = []
        for v in row:
            if v is None:
                cells.append("<NULL>")
            elif isinstance(v, (int, float)):
                cells.append(f"{float(v):.6f}" if isinstance(v, float) else str(v))
            else:
                cells.append(str(v).strip())
        out.append(tuple(cells))
    return sorted(out)


def run_sql(db: Path, sql: str):
    con = sqlite3.connect(str(db))
    try:
        cur = con.execute(sql)
        return normalize(cur.fetchall()), [d[0] for d in cur.description or []]
    finally:
        con.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    run_dir = Path(args.run_dir).resolve()

    truth = json.loads((HERE / "truth.json").read_text(encoding="utf-8"))
    db = HERE / truth["db"]
    threshold = truth["threshold"]

    got = {}
    path = run_dir / "answers.jsonl"
    checks = []
    if not path.exists():
        checks.append({"id": "answers_jsonl", "pass": False, "note": "answers.jsonl 缺失"})
    else:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                got[str(obj["question_id"])] = str(obj.get("sql", ""))
            except Exception:
                continue
        checks.append({"id": "answers_jsonl", "pass": len(got) == len(truth["answers"]),
                       "note": f"{len(got)}/{len(truth['answers'])} 行可解析"})

    ok = 0
    for qid, meta in truth["answers"].items():
        pred = got.get(qid, "")
        hit, note = False, ""
        if pred:
            try:
                gold_rows, _ = run_sql(db, meta["sql"])
            except Exception as exc:  # gold 本身应可执行，出错即用例缺陷
                note = f"gold SQL error: {exc}"
                checks.append({"id": f"q{qid}", "pass": False, "note": note})
                continue
            try:
                pred_rows, _ = run_sql(db, pred)
                hit = pred_rows == gold_rows
                note = f"rows {len(pred_rows)} vs {len(gold_rows)}"
            except Exception as exc:
                note = f"sql error: {exc}"
        checks.append({"id": f"q{qid}", "pass": hit, "note": note, "difficulty": meta["difficulty"]})
        ok += int(hit)

    acc = ok / len(truth["answers"])
    reward = 1 if acc >= threshold else 0
    out = {"case": "bird-schools15", "reward": reward, "weighted": round(acc * 100, 2),
           "accuracy": round(acc, 4), "threshold": threshold, "checks": checks}
    print(json.dumps(out, ensure_ascii=False) if args.json else json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
