#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bird-ca-schools-15 判分器 v1.1（2026-10-24，BIRD exec-accuracy + schema 硬门）

用法：
    python3 checker.py <run_dir> [--json]     # 正式判分：最后一行输出一行 JSON
    python3 checker.py --selftest             # 负控制/守卫自测，全过 exit 0，否则 exit 2

判分对象：
    <run_dir>/answers.jsonl   15 行，每行 {"question_id": <int>, "sql": "<单条 SQLite 查询>"}

口径：
    binary：reward = 1 当且仅当「交付契约（15 题齐全、无缺失/多余/重复）+ 输入完整性未被破坏
            + 逐题结果集准确率 ≥ 0.8」；weighted = 准确率 × 100。
    逐题判分 = 执行 gold SQL 与 pred SQL，结果集归一后比对（exec-accuracy）：
            单元格 None→"<NULL>"、float 四舍五入保留 6 位、字符串去首尾空白、按列序成组，
            行排序后逐行比对（行顺序不敏感，重复行敏感）。
    守卫：truth.json 的 input_sha256 / threshold / n_questions / question_id 集合与 checker 常量
            不一致 → ERROR 退出码 2；gold SQL 执行失败或返回空集 → 同视为用例缺陷 → ERROR 退出码 2。
    只读：只读 run_dir 与 checker 同目录文件，不联网、不装包、不写 inputs。

数据来源：BIRD mini_dev（db_id=california_schools），CC BY-SA 4.0，
          官网 https://bird-bench.github.io/ ，读取日期 2026-10-22；题面为中文重写，
          gold SQL 保持官方原样。本判分器为自建实现（非官方脚本移植）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

CASE_ID = "bird-ca-schools-15"
CHECKER_VERSION = "1.1"
BINARY = True
THRESHOLD = 0.8
N_QUESTIONS = 15
# 题序：5 challenging(28/36/62/83/87) + 7 moderate(12/23/24/25/26/27/31) + 3 simple(5/11/17)
EXPECTED_QIDS = ("28", "36", "62", "83", "87",
                 "12", "23", "24", "25", "26", "27", "31",
                 "5", "11", "17")
DB_REL = "inputs/db/california_schools.sqlite"
INPUT_FILES = (DB_REL, "inputs/schema.sql", "inputs/sample_rows.json", "inputs/questions.json")
NULL = "<NULL>"
WRITE_SQL_RE = re.compile(r"^\s*(insert|update|delete|drop|alter|create|replace|attach|detach|"
                          r"pragma|vacuum|reindex)\b", re.IGNORECASE)
HERE = Path(__file__).resolve().parent

_CACHE = {}


# ------------------------------------------------------------------ 基础工具

def sha256_file(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def die(message: str) -> None:
    sys.stderr.write("ERROR: %s\n" % message)
    raise SystemExit(2)


def norm_cell(value):
    """结果集单元格归一：None→"<NULL>"；float 保留 6 位小数；字符串去首尾空白。"""
    if value is None:
        return NULL
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value != value:            # NaN
            return "NaN"
        if value in (float("inf"), float("-inf")):
            return "Inf" if value > 0 else "-Inf"
        return round(value, 6)
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).hex()
    return str(value).strip()


def _row_sort_key(row):
    """数值优先、字符串在后，保证混合类型行可排序。"""
    return tuple((0, cell) if isinstance(cell, (int, float)) and not isinstance(cell, bool)
                 else (1, cell) for cell in row)


def normalize_rows(rows):
    """行归一 + 排序：返回可比较的行列表（多重集口径，重复行敏感）。"""
    normalized = [tuple(norm_cell(value) for value in row) for row in rows]
    return sorted(normalized, key=_row_sort_key)


def open_canonical_db():
    """打开 canonical 输入库（只读守卫：PRAGMA query_only）。"""
    db_path = HERE / DB_REL
    try:
        con = sqlite3.connect(str(db_path))
        con.execute("PRAGMA query_only = ON")
    except sqlite3.Error as exc:  # pragma: no cover - 环境异常
        die("无法打开 canonical 数据库 %s: %s" % (db_path, exc))
    return con


def run_query(sql: str):
    """执行单条查询并返回归一化结果集；写/管理类语句与非单条语句一律报错。"""
    if not isinstance(sql, str) or not sql.strip():
        raise ValueError("sql 为空")
    if WRITE_SQL_RE.match(sql):
        raise ValueError("只允许单条 SELECT/查询语句（检测到写/管理类语句）")
    con = open_canonical_db()
    try:
        cursor = con.execute(sql)
        rows = cursor.fetchall()
    finally:
        con.close()
    return normalize_rows(rows)


# ------------------------------------------------------------ 用例自身守卫

def load_truth():
    path = HERE / "truth.json"
    if not path.is_file():
        die("truth.json 缺失：%s" % path)
    try:
        truth = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        die("truth.json 无法解析: %s" % exc)
    if not isinstance(truth, dict):
        die("truth.json 不是 JSON 对象")
    if truth.get("case_id") != CASE_ID:
        die("checker 常量与 truth 不一致：case_id=%r（期望 %r）" % (truth.get("case_id"), CASE_ID))
    if truth.get("checker_version") != CHECKER_VERSION:
        die("checker 常量与 truth 不一致：checker_version=%r（期望 %r）"
            % (truth.get("checker_version"), CHECKER_VERSION))
    if truth.get("threshold") != THRESHOLD:
        die("checker 常量与 truth 不一致：threshold=%r（期望 %r）"
            % (truth.get("threshold"), THRESHOLD))
    if truth.get("n_questions") != N_QUESTIONS:
        die("checker 常量与 truth 不一致：n_questions=%r（期望 %r）"
            % (truth.get("n_questions"), N_QUESTIONS))
    if truth.get("binary") is not True:
        die("checker 常量与 truth 不一致：binary 必须为 true")
    answers = truth.get("answers")
    if not isinstance(answers, dict) or set(answers) != set(EXPECTED_QIDS):
        die("checker 常量与 truth 不一致：answers 的 question_id 集合与 EXPECTED_QIDS 不符")
    return truth


def verify_canonical_inputs(truth):
    recorded = truth.get("input_sha256")
    if not isinstance(recorded, dict) or set(recorded) != set(INPUT_FILES):
        die("truth.json 的 input_sha256 未覆盖全部 canonical 输入：%s" % (INPUT_FILES,))
    for rel in INPUT_FILES:
        path = HERE / rel
        if not path.is_file():
            die("canonical 输入缺失：%s" % path)
        actual = sha256_file(path)
        if actual != recorded[rel]:
            die("用例自身不一致：%s 实际 SHA-256 与 truth 记录不符\n  truth=%s\n  actual=%s"
                % (rel, recorded[rel], actual))


def compute_gold(truth):
    """执行全部 gold SQL；失败或空结果即用例缺陷 → ERROR exit 2。"""
    gold = {}
    con = open_canonical_db()
    try:
        for qid in EXPECTED_QIDS:
            sql = truth["answers"][qid]["sql"]
            try:
                rows = con.execute(sql).fetchall()
            except Exception as exc:
                die("用例缺陷：gold SQL 执行失败 q%s: %s" % (qid, exc))
            if not rows:
                die("用例缺陷：gold SQL 结果为空 q%s（题目不可区分/数据异常）" % (qid,))
            gold[qid] = normalize_rows(rows)
    finally:
        con.close()
    return gold


def load_case():
    """加载并校验用例（每进程一次）：truth 交叉校验 → 输入 SHA 校验 → gold 执行。"""
    if not _CACHE:
        truth = load_truth()
        verify_canonical_inputs(truth)
        _CACHE["truth"] = truth
        _CACHE["gold"] = compute_gold(truth)
    return _CACHE["truth"], _CACHE["gold"]


# ---------------------------------------------------------------- 判分主体

def parse_answers(path):
    """解析 answers.jsonl；返回 (entries, parse_errors, 行数统计)。"""
    entries, parse_errors, raw_lines = [], 0, 0
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [], 1, "非 UTF-8 文本"
    for line in text.splitlines():
        if not line.strip():
            continue
        raw_lines += 1
        try:
            obj = json.loads(line)
        except Exception:
            parse_errors += 1
            continue
        if not isinstance(obj, dict):
            parse_errors += 1
            continue
        qid, sql = obj.get("question_id"), obj.get("sql")
        if qid is None or not isinstance(sql, str):
            parse_errors += 1
            continue
        entries.append((str(qid).strip(), sql))
    return entries, parse_errors, raw_lines


def judge(run_dir):
    truth, gold = load_case()
    run_dir = Path(run_dir).resolve()
    checks = []

    # ① 输入完整性（run_dir 里若带 inputs 副本，逐件与 canonical SHA-256 比对）
    present = [rel for rel in INPUT_FILES if (run_dir / rel).is_file()]
    integrity = "unverified"
    if present:
        integrity = "verified"
        tampered = None
        for rel in present:
            if sha256_file(run_dir / rel) != truth["input_sha256"][rel]:
                tampered = rel
                break
        if tampered:
            integrity = "fail"
            checks.append({"id": "input_integrity", "pass": False,
                           "note": "输入副本被修改：%s 与 canonical SHA-256 不一致（判 0）" % tampered})
        else:
            checks.append({"id": "input_integrity", "pass": True,
                           "note": "已附输入副本 %d 件，均与 canonical 一致" % len(present)})
    else:
        checks.append({"id": "input_integrity", "pass": True,
                       "note": "未附输入副本（未核验，不扣分）"})

    # ② 产物存在 + 结构
    answers_path = run_dir / "answers.jsonl"
    entries, parse_errors = [], 0
    if not answers_path.is_file():
        checks.append({"id": "answers_file", "pass": False, "note": "answers.jsonl 缺失"})
        checks.append({"id": "answers_schema", "pass": False, "note": "无产物可解析"})
        checks.append({"id": "answers_coverage", "pass": False, "note": "0/15 题"})
    else:
        checks.append({"id": "answers_file", "pass": True, "note": str(answers_path)})
        entries, parse_errors, _ = parse_answers(answers_path)
        checks.append({"id": "answers_schema", "pass": parse_errors == 0,
                       "note": "%d 行可解析，%d 行 JSON/结构异常" % (len(entries), parse_errors)})
        pred = {}
        duplicates = 0
        for qid, sql in entries:
            if qid in pred:
                duplicates += 1
            pred[qid] = sql
        missing = [qid for qid in EXPECTED_QIDS if qid not in pred]
        extra = sorted(set(pred) - set(EXPECTED_QIDS))
        coverage_ok = (len(entries) == N_QUESTIONS and len(pred) == N_QUESTIONS
                       and not missing and not extra)
        checks.append({"id": "answers_coverage", "pass": coverage_ok,
                       "note": "有效行 %d/15；缺失 %s；多余 %s；重复 %d"
                               % (len(entries), "、".join(missing) or "无",
                                  "、".join(extra) or "无", duplicates)})

    # ③ 逐题结果集比对（exec-accuracy）
    pred_sql = {}
    for qid, sql in entries:
        pred_sql[qid] = sql
    correct, failed_qids = 0, []
    for qid in EXPECTED_QIDS:
        meta = truth["answers"][qid]
        sql = pred_sql.get(qid)
        if sql is None:
            checks.append({"id": "q" + qid, "pass": False, "difficulty": meta["difficulty"],
                           "note": "未作答"})
            failed_qids.append(qid)
            continue
        try:
            rows = run_query(sql)
        except Exception as exc:
            checks.append({"id": "q" + qid, "pass": False, "difficulty": meta["difficulty"],
                           "note": "pred SQL 执行失败: %s" % str(exc)[:160].replace("\n", " ")})
            failed_qids.append(qid)
            continue
        hit = rows == gold[qid]
        if hit:
            correct += 1
            note = "行集一致（%d 行）" % len(rows)
        else:
            notes = []
            if len(rows) != len(gold[qid]):
                notes.append("行数 %d vs gold %d" % (len(rows), len(gold[qid])))
            else:
                notes.append("行数同为 %d，行内容/类型不一致" % len(rows))
            note = "；".join(notes)
            failed_qids.append(qid)
        checks.append({"id": "q" + qid, "pass": hit, "difficulty": meta["difficulty"],
                       "note": note})

    accuracy = correct / N_QUESTIONS
    coverage_pass = next(item["pass"] for item in checks if item["id"] == "answers_coverage")
    schema_pass = next(item["pass"] for item in checks if item["id"] == "answers_schema")
    reward = 1 if (schema_pass and coverage_pass and integrity != "fail"
                   and accuracy >= THRESHOLD) else 0
    return {
        "case": CASE_ID,
        "checker_version": CHECKER_VERSION,
        "binary": BINARY,
        "run_dir": str(run_dir),
        "reward": reward,
        "weighted": round(accuracy * 100, 2),
        "accuracy": round(accuracy, 4),
        "correct": correct,
        "n_questions": N_QUESTIONS,
        "threshold": THRESHOLD,
        "input_integrity": integrity,
        "failed_questions": failed_qids,
        "checks": checks,
    }


def render(result) -> str:
    lines = ["[%s] checker v%s  run_dir=%s" % (result["case"], result["checker_version"],
                                               result["run_dir"]),
             "  逐题 exec-accuracy：%d/%d 正确（accuracy=%.3f，达标线 %.2f）"
             % (result["correct"], result["n_questions"], result["accuracy"], result["threshold"])]
    for check in result["checks"]:
        mark = "PASS" if check["pass"] else "FAIL"
        lines.append("  %-4s %-18s %s" % (mark, check["id"], check["note"]))
    lines.append("REWARD %d  WEIGHTED %.2f  INPUT %s"
                 % (result["reward"], result["weighted"], result["input_integrity"]))
    return "\n".join(lines)


# ------------------------------------------------------------------ 自测

def _answers_text(pairs) -> str:
    return "".join(json.dumps({"question_id": int(qid), "sql": sql}, ensure_ascii=False) + "\n"
                   for qid, sql in pairs)


def _make_run_dir(root, *, answers_text=None, inputs="link", tamper=None):
    run_dir = Path(root) / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    if answers_text is not None:
        (run_dir / "answers.jsonl").write_text(answers_text, encoding="utf-8")
    if inputs == "link":
        (run_dir / "inputs").symlink_to(HERE / "inputs", target_is_directory=True)
    elif inputs == "db_tampered":
        dst = run_dir / "inputs" / "db" / "california_schools.sqlite"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(HERE / DB_REL, dst)
        blob = bytearray(dst.read_bytes())
        blob[64] ^= 0xFF
        dst.write_bytes(blob)
    elif inputs == "schema_tampered":
        dst = run_dir / "inputs" / "schema.sql"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text((HERE / "inputs/schema.sql").read_text(encoding="utf-8") + "-- tampered\n",
                       encoding="utf-8")
    elif inputs is not None:
        raise ValueError("unknown inputs mode %r" % (inputs,))
    if tamper is not None:  # 供额外篡改用例使用
        tamper(run_dir)
    return run_dir


def _temp_case(root, mutate_truth):
    """造一份临时 case 目录（checker + truth[被改] + inputs 符号链接），用于守卫子进程测试。"""
    case = Path(root) / "case"
    (case / "inputs" / "db").mkdir(parents=True, exist_ok=True)
    shutil.copy2(HERE / "checker.py", case / "checker.py")
    for rel in INPUT_FILES:
        target = case / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(HERE / rel)
    truth = json.loads((HERE / "truth.json").read_text(encoding="utf-8"))
    mutate_truth(truth)
    (case / "truth.json").write_text(json.dumps(truth, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    run_dir = Path(root) / "run"
    run_dir.mkdir()
    return case, run_dir


def _guard_expect_error(name, mutate_truth) -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        case, run_dir = _temp_case(tmp, mutate_truth)
        proc = subprocess.run([sys.executable, str(case / "checker.py"), str(run_dir), "--json"],
                              capture_output=True, text=True, timeout=180, cwd=str(case))
        ok = proc.returncode == 2 and "ERROR" in (proc.stdout + proc.stderr)
        detail = (proc.stdout + proc.stderr).strip().splitlines()
        print("  %-4s %-46s exit=%d（期望 2）%s"
              % ("PASS" if ok else "FAIL", name, proc.returncode,
                 "  " + detail[-1][:90] if detail else ""))
        return ok


def selftest() -> int:
    truth, gold = load_case()
    order = list(EXPECTED_QIDS)
    gold_sql = {qid: truth["answers"][qid]["sql"] for qid in order}
    oracle_pairs = [(qid, gold_sql[qid]) for qid in order]
    oracle_text = _answers_text(oracle_pairs)
    failed = 0

    def mutate(**empty):
        raise ValueError("placeholder")

    # 系统性缺陷用 SQL（负例共用）
    miss_join = {                      # 少 JOIN 条件：把 ON 谓词退化成 1=1（笛卡尔积），限行防爆
        "11": "SELECT T2.CDSCode FROM schools AS T1 INNER JOIN frpm AS T2 ON 1=1 "
              "WHERE T2.`Enrollment (K-12)` + T2.`Enrollment (Ages 5-17)` > 500 LIMIT 50",
        "23": "SELECT T1.School, T1.Street FROM schools AS T1 INNER JOIN frpm AS T2 ON 1=1 "
              "WHERE T2.`Enrollment (K-12)` - T2.`Enrollment (Ages 5-17)` > 30 LIMIT 50",
        "24": "SELECT T2.`School Name` FROM satscores AS T1 INNER JOIN frpm AS T2 ON 1=1 "
              "WHERE CAST(T2.`Free Meal Count (K-12)` AS REAL) / T2.`Enrollment (K-12)` > 0.1 "
              "AND T1.NumGE1500 > 0 LIMIT 50",
        "26": "SELECT T1.`School Name`, T2.Street, T2.City, T2.State, T2.Zip "
              "FROM frpm AS T1 INNER JOIN schools AS T2 ON 1=1 "
              "WHERE T2.County = 'Monterey' AND T1.`Free Meal Count (Ages 5-17)` > 800 "
              "AND T1.`School Type` = 'High Schools (Public)' LIMIT 50",
        "27": "SELECT T2.School, T1.AvgScrWrite, T2.Phone FROM schools AS T2 "
              "LEFT JOIN satscores AS T1 ON 1=1 "
              "WHERE strftime('%Y', T2.OpenDate) > '1991' OR strftime('%Y', T2.ClosedDate) < '2000' "
              "LIMIT 50",
    }
    near_miss = {                      # 近正确但口径错一处的替换 SQL
        "62": gold_sql["62"].replace(
            "* 100 / T1.`Enrollment (K-12)` < 0.18", "/ T1.`Enrollment (K-12)` < 0.18"),
        "31": gold_sql["31"].replace("LIMIT 9, 2", "LIMIT 7, 2"),
        "23": gold_sql["23"].replace("> 30", "> 31"),
        "26": gold_sql["26"].replace("> 800", "> 900"),
    }
    dedup = {qid: "SELECT * FROM (%s) UNION ALL SELECT * FROM (%s)" % (gold_sql[qid], gold_sql[qid])
             for qid in ("11", "23", "24", "26", "27")}

    def variant(pairs, replacement):
        out = []
        for qid, sql in pairs:
            out.append((qid, replacement.get(qid, sql)))
        return out

    fixtures = []  # (name, expect_reward, answers_text|None, inputs_mode, must_fail, must_pass)

    fixtures.append(("nop（空运行目录，无产物）", 0, None, "link", ("answers_file",), ()))
    fixtures.append(("oracle（solution/answers.jsonl 原样）", 1,
                     (HERE / "solution" / "answers.jsonl").read_text(encoding="utf-8"),
                     "link", (), ("answers_file", "answers_schema", "answers_coverage",
                                  "input_integrity")))
    fixtures.append(("漏 1 题（删掉 q36 一行）", 0,
                     _answers_text([(q, s) for q, s in oracle_pairs if q != "36"]), "link",
                     ("answers_coverage",), ()))
    fixtures.append(("多 1 题（追加 question_id=9999）", 0,
                     oracle_text + _answers_text([("9999", "SELECT 1")]), "link",
                     ("answers_coverage",), ()))
    fixtures.append(("重复 question_id（q28 写两遍，共 16 行）", 0,
                     oracle_text + _answers_text([("28", gold_sql["28"])]), "link",
                     ("answers_coverage",), ()))
    fixtures.append(("无效 SQL（6 题查不存在的表）", 0,
                     _answers_text(variant(oracle_pairs,
                                           {q: "SELECT * FROM __no_such_table__"
                                            for q in ("28", "36", "62", "83", "87", "12")})),
                     "link", tuple("q" + q for q in ("28", "36", "62", "83", "87", "12")),
                     ("answers_coverage",)))
    fixtures.append(("空结果集（6 题改成 SELECT 1 WHERE 0）", 0,
                     _answers_text(variant(oracle_pairs,
                                           {q: "SELECT 1 WHERE 0"
                                            for q in ("28", "36", "62", "83", "87", "12")})),
                     "link", tuple("q" + q for q in ("28", "36", "62", "83", "87", "12")),
                     ("answers_coverage", "answers_schema")))
    fixtures.append(("少 JOIN 条件（5 题 ON 1=1 笛卡尔积）", 0,
                     _answers_text(variant(oracle_pairs, miss_join)), "link",
                     tuple("q" + q for q in miss_join), ("answers_coverage",)))
    fixtures.append(("少 DISTINCT/未去重（5 题多行结果翻倍）", 0,
                     _answers_text(variant(oracle_pairs, dedup)), "link",
                     tuple("q" + q for q in dedup), ("answers_coverage",)))
    fixtures.append(("近正确负例（4 题口径差一处：删 *100 / 偏移 / 阈值）", 0,
                     _answers_text(variant(oracle_pairs, near_miss)), "link",
                     tuple("q" + q for q in near_miss), ("answers_coverage",)))
    fixtures.append(("追加非法行（15 题全对但 schema 必须否决）", 0,
                     oracle_text + "not-json\n", "link", ("answers_schema",),
                     ("answers_coverage",)))
    fixtures.append(("追加非对象 JSON（15 题全对但 schema 必须否决）", 0,
                     oracle_text + "[]\n", "link", ("answers_schema",),
                     ("answers_coverage",)))
    fixtures.append(("格式错（首行不是 JSON）", 0,
                     "not-a-json-line\n" + _answers_text(oracle_pairs[1:]), "link",
                     ("answers_coverage", "answers_schema"), ()))
    fixtures.append(("改输入库（run_dir 内 db 副本翻 1 字节）", 0, oracle_text, "db_tampered",
                     ("input_integrity",), ("answers_coverage",)))
    fixtures.append(("改输入文件（run_dir 内 schema.sql 被追加内容）", 0, oracle_text,
                     "schema_tampered", ("input_integrity",), ("answers_coverage",)))
    fixtures.append(("阈值边界正例（3 题错 → 12/15=0.8，应判过）", 1,
                     _answers_text(variant(oracle_pairs,
                                           {q: near_miss[q] for q in ("62", "31", "26")})),
                     "link", (), ("answers_coverage",)))
    fixtures.append(("等价答案正例（q5 去掉 DISTINCT，结果不变）", 1,
                     _answers_text(variant(oracle_pairs, {
                         "5": gold_sql["5"].replace("COUNT(DISTINCT T2.School)",
                                                    "COUNT(T2.School)")})),
                     "link", (), ("q5",)))

    print("[%s] checker v%s 自测（%d 题：challenging 5 / moderate 7 / simple 3；"
          "threshold=%.2f）" % (CASE_ID, CHECKER_VERSION, N_QUESTIONS, THRESHOLD))
    print("  用例自身校验通过：输入 SHA-256 全一致，gold 全部可执行且非空")
    for name, expect, answers_text, inputs_mode, must_fail, must_pass in fixtures:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _make_run_dir(tmp, answers_text=answers_text, inputs=inputs_mode)
            result = judge(run_dir)
        failed_ids = {item["id"] for item in result["checks"] if not item["pass"]}
        problems = []
        if result["reward"] != expect:
            problems.append("reward=%d（期望 %d）" % (result["reward"], expect))
        missing_fail = [item for item in must_fail if item not in failed_ids]
        if missing_fail:
            problems.append("未红: %s" % ",".join(missing_fail))
        missing_pass = [item for item in must_pass
                        if any(c["id"] == item and not c["pass"] for c in result["checks"])]
        if missing_pass:
            problems.append("误红: %s" % ",".join(missing_pass))
        ok = not problems
        failed += 0 if ok else 1
        print("  %-4s %-46s reward=%d（期望 %d，accuracy=%.3f）%s"
              % ("PASS" if ok else "FAIL", name, result["reward"], expect,
                 result["accuracy"], "" if ok else "  ← " + "；".join(problems)))

    # 守卫：用例自身漂移必须 ERROR exit 2（子进程，走真实启动路径）
    print("  守卫自测（期望 ERROR exit 2）：")
    guards = []

    def break_gold(t):
        t["answers"]["28"]["sql"] = "SELECT * FROM __broken_gold_table__"

    def drift_sha(t):
        t["input_sha256"]["inputs/schema.sql"] = "0" * 64

    def drift_threshold(t):
        t["threshold"] = 0.5

    for name, mutator in (("gold SQL 执行失败（truth 注入坏 gold）", break_gold),
                          ("truth 的输入 SHA-256 与实际 inputs 不符", drift_sha),
                          ("threshold 与 checker 常量不一致", drift_threshold)):
        guards.append(_guard_expect_error(name, mutator))
    failed += sum(0 if ok else 1 for ok in guards)

    # 自测收尾：确认 canonical 输入未被判分过程改动
    untouched = True
    for rel in INPUT_FILES:
        if sha256_file(HERE / rel) != truth["input_sha256"][rel]:
            untouched = False
    print("  %-4s %s" % ("PASS" if untouched else "FAIL", "canonical 输入在自测前后未被改动"))
    failed += 0 if untouched else 1

    total = len(fixtures) + len(guards) + 1
    print("自测%s：%d/%d 项符合预期" % ("通过" if failed == 0 else "失败",
                                        total - failed, total))
    return 0 if failed == 0 else 2


# ------------------------------------------------------------------ 入口

def main(argv) -> int:
    parser = argparse.ArgumentParser(description="bird-ca-schools-15 判分器 v%s" % CHECKER_VERSION)
    parser.add_argument("run_dir", nargs="?", help="运行目录（含 answers.jsonl；可带 inputs 副本）")
    parser.add_argument("--json", action="store_true", help="只输出一行 JSON")
    parser.add_argument("--selftest", action="store_true", help="跑负控制/守卫自测")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.run_dir:
        parser.error("缺少 run_dir（或使用 --selftest）")

    result = judge(Path(args.run_dir))
    payload = json.dumps(result, ensure_ascii=False)
    if args.json:
        print(payload)
    else:
        print(render(result))
        print(payload)
    return 0 if result["reward"] == 1 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))