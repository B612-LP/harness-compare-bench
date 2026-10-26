#!/usr/bin/env python3
"""q27 金标口径独立复核（2026-10-26，只读）。

验证冻结 gold（raw-key LEFT JOIN）是否自洽：
1. SQL 年份过滤与 Python 独立日期筛选的人群完全一致；
2. gold 输出行数 = 人群学校数，每校恰一行（无扇出、无遗漏）；
3. 缺 SAT 记录 / NULL 分数统计；4. INNER 对照规模；5. 前导零容错的额外匹配规模。
只读打开 canonical db（mode=ro + query_only），不写任何文件（stdout 除外）。
"""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB = HERE.parents[2] / "2-用例" / "bird-ca-schools-15" / "inputs" / "db" / "california_schools.sqlite"

GOLD = ("SELECT T2.CDSCode, T2.School, T1.AvgScrWrite, T2.Phone FROM schools AS T2 "
        "LEFT JOIN satscores AS T1 ON T2.CDSCode = T1.cds "
        "WHERE strftime('%Y', T2.OpenDate) > '1991' OR strftime('%Y', T2.ClosedDate) < '2000'")
GOLD_PROJECTION_NOTE = "带 CDSCode 仅为逐校身份核对；正式 gold 投影为 School/AvgScrWrite/Phone 三列"


def main() -> int:
    con = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
    con.execute("PRAGMA query_only=ON")
    cur = con.cursor()

    gold_rows = cur.execute(GOLD).fetchall()
    per_school = Counter(r[0] for r in gold_rows)
    sql_pop = set(x[0] for x in cur.execute(
        "SELECT CDSCode FROM schools WHERE strftime('%Y', OpenDate) > '1991' "
        "OR strftime('%Y', ClosedDate) < '2000'"))

    # Python 独立日期筛选（仅取年份前 4 位比较，与 strftime('%Y') 同口径）
    py_pop = set()
    for cds, od, cd_ in cur.execute("SELECT CDSCode, OpenDate, ClosedDate FROM schools"):
        oy = int(od[:4]) if od else None
        cy = int(cd_[:4]) if cd_ else None
        if (oy is not None and oy > 1991) or (cy is not None and cy < 2000):
            py_pop.add(cds)

    sat = dict(cur.execute("SELECT cds, AvgScrWrite FROM satscores"))
    no_record = sum(1 for c in sql_pop if c not in sat)
    null_score = sum(1 for c in sql_pop if c not in sat or sat[c] is None)
    inner_n = cur.execute(
        "SELECT COUNT(*) FROM schools AS T2 INNER JOIN satscores AS T1 ON T2.CDSCode = T1.cds "
        "WHERE strftime('%Y', T2.OpenDate) > '1991' OR strftime('%Y', T2.ClosedDate) < '2000'").fetchone()[0]
    lead0 = cur.execute(
        "SELECT COUNT(*) FROM schools T2 JOIN satscores T1 ON T2.CDSCode='0'||T1.cds "
        "WHERE strftime('%Y',T2.OpenDate)>'1991' OR strftime('%Y',T2.ClosedDate)<'2000'").fetchone()[0]
    lead0_also_raw = cur.execute(
        "SELECT COUNT(*) FROM schools T2 JOIN satscores T1 ON T2.CDSCode='0'||T1.cds "
        "JOIN satscores T3 ON T2.CDSCode=T3.cds").fetchone()[0]
    dup_proj = Counter((s, sc, ph) for _, s, sc, ph in gold_rows)
    dup_groups = {k: v for k, v in dup_proj.items() if v > 1}
    n_schools, n_sat_rows, n_sat_keys = (cur.execute("SELECT COUNT(*), 0 FROM schools").fetchone()[0],) + \
        cur.execute("SELECT COUNT(*), COUNT(DISTINCT cds) FROM satscores").fetchone()

    checks = {
        "population_sql_equals_python": sql_pop == py_pop,
        "gold_rows_equal_population": len(gold_rows) == len(sql_pop),
        "every_school_exactly_one_row": per_school == Counter({c: 1 for c in sql_pop}),
        "join_key_unique_both_sides": n_schools == len(set(
            x[0] for x in cur.execute("SELECT CDSCode FROM schools"))) and n_sat_rows == n_sat_keys,
    }
    out = {
        "date": "2026-10-26",
        "question": "q27",
        "gold_sql": GOLD,
        "population_schools": len(sql_pop),
        "gold_rows": len(gold_rows),
        "distinct_projected_tuples": len(set((s, sc, ph) for _, s, sc, ph in gold_rows)),
        "population_missing_sat_record": no_record,
        "population_null_score_total": null_score,
        "population_with_score": len(sql_pop) - null_score,
        "inner_join_rows_for_contrast": inner_n,
        "leading_zero_extra_matches": lead0,
        "leading_zero_also_raw_matched": lead0_also_raw,
        "duplicate_projection_groups": len(dup_groups),
        "duplicate_extra_rows": sum(v - 1 for v in dup_groups.values()),
        "checks": checks,
        "verdict": "gold 口径自洽（人群=日期命中的全部学校，LEFT 保留缺 SAT 学校，NULL 分数；"
                   "键两侧唯一、无扇出）。INNER/前导零/去重均属更强解释跳跃，金标不动，登记已知尖角。",
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
