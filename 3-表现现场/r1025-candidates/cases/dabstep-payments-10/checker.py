#!/usr/bin/env python3
"""dabstep-payments-10 轻量判卷器 v0.1（2026-10-22）

用法：
    python3 checker.py <run_dir> [--json]
    python3 checker.py --selftest

数据与判分口径来源（CC-BY-4.0）：
    DABstep: Data Agent Benchmark for Multi-Step Reasoning（Adyen + Hugging Face）
    数据集      https://huggingface.co/datasets/adyen/DABstep
    官方判分器  https://huggingface.co/spaces/adyen/DABstep 的 dabstep_benchmark/evaluation/scorer.py
    许可证      CC-BY-4.0（https://creativecommons.org/licenses/by/4.0/）
    读取日期    2026-10-22
本文件中的 is_numeric_with_commas / question_scorer / extract_numeric /
compare_numeric / compare_strings / compare_lists 移植自上述官方 scorer（CC-BY-4.0），
判定语义保持一致；其余部分（产物解析、输入守卫、自测）为本仓自写。

判分口径：
    headline 二值（BINARY=True）。reward = 1 当且仅当三条件同时成立：
      ① answers_format：产物 answers.jsonl 结构合法——10 个 task_id 各恰好一行，
         answer 必须是 JSON 字符串（可为空字符串，但不得缺失/null/数字/对象）；
      ② input_integrity：运行目录附带的输入副本（如果有）与 canonical 输入逐一
         SHA-256 相同；未附副本 → 记为「未核验」，不扣分；
      ③ 得分率 = 10 题逐题二值（官方 question_scorer 判定 pred 与 gold 等价）/10
         ≥ THRESHOLD（0.8）。
    weighted = 得分率 × 100（保留 1 位小数）。
    ①、② 是否决项：任一不成立则 reward=0（weighted 仍按得分率给出，用于定位）。
    answers.jsonl 只从运行目录读取；不采信任何自述/日志/中间产物。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import sys
import tempfile
from difflib import SequenceMatcher
from pathlib import Path

CASE_ID = "dabstep-payments-10"
CHECKER_VERSION = "0.1"
BINARY = True
THRESHOLD = 0.8          # 得分率达标线；须与 truth.json 一致（守卫）
N_TASKS = 10             # 题数；须与 truth.json 一致（守卫）
MAX_ARTIFACT_BYTES = 2 * 1024 * 1024

ARTIFACT = "answers.jsonl"
INPUT_FILES = [
    "acquirer_countries.csv",
    "fees.json",
    "manual.md",
    "merchant_category_codes.csv",
    "merchant_data.json",
    "payments.csv",
    "questions.jsonl",
]

CASE_DIR = Path(__file__).resolve().parent


class CaseError(Exception):
    """用例自身不一致（truth 漂移 / canonical 输入被改 / solution 漂移）→ 退出码 2。"""


# ---------------------------------------------------------------------------
# 官方 scorer 移植（DABstep src/scorer.py，CC-BY-4.0；语义未改）
# ---------------------------------------------------------------------------

def is_numeric_with_commas(value: str) -> bool:
    """
    True for strings that are either
      - numbers using comma thousands‑separators (at least one comma),
        with optional dot‑decimal, e.g.  "1,000"  or  "12,345.67"
    OR
      - pure decimals (no separators) with a decimal point or comma,
        e.g. "0.99" or "0,99"
    Plain ints without commas (e.g. "64") are rejected.
    """
    v = value.strip()
    pattern = r'''
      ^\$?                                  # optional dollar sign
      (?:                                   # two alternate groups:
         \d{1,3}(?:,\d{3})+(?:\.\d+)?       # 1) at least one comma‑group + optional .decimal
       | \d+[.,]\d+                         # 2) or plain decimal with . or ,
      )
      $                                     # end of string
    '''
    return bool(re.match(pattern, v, re.VERBOSE))


def question_scorer(input1: str, input2: str) -> bool:
    # Remove leading/trailing whitespace and convert to lowercase
    input1 = input1.strip().lower()
    input2 = input2.strip().lower()

    # Check if inputs are numeric with commas
    if is_numeric_with_commas(input1) or is_numeric_with_commas(input2):
        num1 = extract_numeric(input1)
        num2 = extract_numeric(input2)
        return compare_numeric(num1, num2) if num1 is not None and num2 is not None else False

    # Check for list match
    if ';' in input1 or ';' in input2 or ',' in input1 or ',' in input2:
        return compare_lists(input1, input2)

    # Extract numeric values if present
    num1 = extract_numeric(input1)
    num2 = extract_numeric(input2)

    # If both inputs have numeric values, compare them
    if num1 is not None and num2 is not None:
        return compare_numeric(num1, num2)

    # Check for string match or subset
    return compare_strings(input1, input2)


def extract_numeric(value: str):
    # Remove commas and currency symbols from the value string
    value = value.replace(',', '').replace('$', '')

    # Extract the first occurrence of a numeric value (including percentages and leading decimal point)
    match = re.search(r'(\d*\.\d+|\d+\.?\d*)%?', value)
    if match:
        num_str = match.group(1)
        try:
            return float(num_str)
        except ValueError:
            return None
    return None


def compare_numeric(num1: float, num2: float) -> bool:
    # Check for exact equality first
    if num1 == num2:
        return True

    # For percentages and small numbers, use a more lenient comparison
    if num1 < 1 and num2 < 1:
        return math.isclose(num1, num2, rel_tol=1e-4, abs_tol=1e-4)

    # For larger numbers, use the original comparison method
    dec_places1 = len(str(num1).split('.')[-1]) if '.' in str(num1) else 0
    dec_places2 = len(str(num2).split('.')[-1]) if '.' in str(num2) else 0
    round_to = min(dec_places1, dec_places2)
    rounded1 = round(num1, round_to)
    rounded2 = round(num2, round_to)

    if rounded1 == rounded2:
        return True

    return math.isclose(num1, num2, rel_tol=1e-4, abs_tol=1e-4)


def compare_strings(str1: str, str2: str) -> bool:
    # Remove all whitespace and punctuation
    clean1 = re.sub(r'[^\w]', '', str1)
    clean2 = re.sub(r'[^\w]', '', str2)

    if clean1 == clean2:
        return True

    words1 = re.findall(r'\b\w+\b', str1.lower())
    words2 = re.findall(r'\b\w+\b', str2.lower())

    # Only do subset comparison if neither list is empty
    if (len(words1) == 1 or len(words2) == 1) and words1 and words2:
        return set(words1).issubset(set(words2)) or set(words2).issubset(set(words1))

    # Debugging: Log similarity score
    similarity = SequenceMatcher(None, str1, str2).ratio()

    return similarity > 0.95


def compare_lists(list1: str, list2: str) -> bool:
    # Normalize list representations by removing brackets
    list1 = re.sub(r'^\[|\]$', '', list1.strip())
    list2 = re.sub(r'^\[|\]$', '', list2.strip())

    # Split the lists and remove whitespace
    items1 = [item.strip() for item in re.split(r'[,;]', list1) if item.strip()]
    items2 = [item.strip() for item in re.split(r'[,;]', list2) if item.strip()]

    # Sort the items to handle different order
    items1.sort()
    items2.sort()

    # Check if the lists are identical
    if items1 == items2:
        return True

    # If lists are not identical, compare each item
    if len(items1) != len(items2):
        return False

    for item1, item2 in zip(items1, items2):
        if not question_scorer(item1, item2):
            return False

    return True


# ---------------------------------------------------------------------------
# truth / canonical 输入守卫
# ---------------------------------------------------------------------------

_HASH_CACHE = {}


def sha256_file(path: Path) -> str:
    key = str(path)
    stat = path.stat()
    cached = _HASH_CACHE.get(key)
    if cached and cached[0] == stat.st_size and cached[1] == stat.st_mtime_ns:
        return cached[2]
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    value = digest.hexdigest()
    _HASH_CACHE[key] = (stat.st_size, stat.st_mtime_ns, value)
    return value


def load_truth(case_dir: Path = CASE_DIR) -> dict:
    path = case_dir / "truth.json"
    if not path.is_file():
        raise CaseError("缺失 truth.json：%s" % path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise CaseError("truth.json 不是合法 JSON：%s" % exc)


def load_jsonl(path: Path):
    rows = []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CaseError("无法读取 %s：%s" % (path, exc))
    for lineno, raw in enumerate(text.splitlines(), 1):
        raw = raw.strip()
        if not raw:
            continue
        try:
            rows.append(json.loads(raw))
        except ValueError as exc:
            raise CaseError("%s 第 %d 行不是合法 JSON：%s" % (path.name, lineno, exc))
    return rows


def load_and_guard(case_dir: Path = CASE_DIR):
    """校验用例自身一致性，返回 (truth, gold, questions)。

    三重守卫：
      ① truth 常量与 checker 常量一致（case_id / version / threshold / n_tasks / 文件清单）；
      ② truth.input_sha256 与实际 inputs/ 逐一相符（canonical 输入被改 → ERROR）；
      ③ truth.gold 与 solution/answers.jsonl 经官方 scorer 逐一等价（oracle 漂移 → ERROR）。
    """
    truth = load_truth(case_dir)

    if truth.get("case_id") != CASE_ID:
        raise CaseError("truth case_id=%r 与 checker CASE_ID=%r 不一致"
                        % (truth.get("case_id"), CASE_ID))
    if truth.get("checker_version") != CHECKER_VERSION:
        raise CaseError("truth checker_version=%r 与 checker CHECKER_VERSION=%r 不一致"
                        % (truth.get("checker_version"), CHECKER_VERSION))
    if abs(float(truth.get("threshold", -1)) - THRESHOLD) > 1e-12:
        raise CaseError("truth threshold=%r 与 checker THRESHOLD=%r 不一致"
                        % (truth.get("threshold"), THRESHOLD))
    if int(truth.get("n_tasks", -1)) != N_TASKS:
        raise CaseError("truth n_tasks=%r 与 checker N_TASKS=%r 不一致"
                        % (truth.get("n_tasks"), N_TASKS))
    if sorted(truth.get("input_sha256") or {}) != sorted(INPUT_FILES):
        raise CaseError("truth input_sha256 文件清单与 checker INPUT_FILES 不一致：%r"
                        % (sorted(truth.get("input_sha256") or {}),))

    gold = truth.get("gold") or {}
    if len(gold) != N_TASKS:
        raise CaseError("truth gold 题数 %d 与 N_TASKS=%d 不一致" % (len(gold), N_TASKS))

    inputs_dir = case_dir / "inputs"
    for name in INPUT_FILES:
        path = inputs_dir / name
        if not path.is_file():
            raise CaseError("canonical 输入缺失：%s" % path)
        actual = sha256_file(path)
        expected = truth["input_sha256"][name]
        if actual != expected:
            raise CaseError("canonical 输入与 truth 记录不一致：%s\n  truth=%s\n  actual=%s"
                            % (path, expected, actual))
        expected_bytes = (truth.get("input_bytes") or {}).get(name)
        if expected_bytes is not None and path.stat().st_size != int(expected_bytes):
            raise CaseError("canonical 输入长度漂移：%s %d != truth %d"
                            % (path, path.stat().st_size, int(expected_bytes)))

    questions = load_jsonl(inputs_dir / "questions.jsonl")
    qids = [str(q.get("task_id")) for q in questions if isinstance(q, dict)]
    if len(questions) != N_TASKS or len(set(qids)) != N_TASKS:
        raise CaseError("questions.jsonl 题数/唯一性异常：%d 行，%d 个唯一 task_id"
                        % (len(questions), len(set(qids))))
    if sorted(qids) != sorted(gold):
        raise CaseError("questions.jsonl 的 task_id 集合与 truth gold 不一致")

    solution_path = case_dir / "solution" / "answers.jsonl"
    if not solution_path.is_file():
        raise CaseError("缺失 oracle 产物：%s" % solution_path)
    sol_rows = load_jsonl(solution_path)
    sol = {}
    for row in sol_rows:
        if not isinstance(row, dict) or "task_id" not in row or "answer" not in row:
            raise CaseError("solution/answers.jsonl 存在不合规行：%r" % (row,))
        sol[str(row["task_id"]).strip()] = str(row["answer"]).strip()
    if sorted(sol) != sorted(gold):
        raise CaseError("solution/answers.jsonl 的 task_id 集合与 truth gold 不一致")
    for tid in sorted(gold, key=int):
        if not question_scorer(sol[tid], gold[tid]):
            raise CaseError("solution 与 truth.gold 不一致（task_id=%s）：pred=%r gold=%r"
                            % (tid, sol[tid], gold[tid]))

    return truth, gold, questions


# ---------------------------------------------------------------------------
# run_dir 产物解析
# ---------------------------------------------------------------------------

def _candidates(run_dir: Path, name: str):
    return (run_dir / name,
            run_dir / "inputs" / name,
            run_dir / "input" / name,
            run_dir / "output" / name,
            run_dir / "outputs" / name)


def find_artifact(run_dir: Path):
    for candidate in (run_dir / ARTIFACT,
                      run_dir / "output" / ARTIFACT,
                      run_dir / "outputs" / ARTIFACT):
        if candidate.is_file():
            return candidate
    return None


def find_input_copy(run_dir: Path, name: str):
    for candidate in _candidates(run_dir, name):
        if candidate.is_file():
            return candidate
    return None


def parse_answers(raw_text: str):
    """解析 answers.jsonl。返回 (entries, errors, line_count)。

    entries: task_id -> answer（首个出现的记录；重复/未知 task_id 记 error）
    errors:  结构违规说明列表（非空 → answers_format 否决）
    """
    entries = {}
    errors = []
    seen = 0
    for lineno, raw in enumerate(raw_text.splitlines(), 1):
        if not raw.strip():
            continue
        seen += 1
        try:
            obj = json.loads(raw)
        except ValueError as exc:
            errors.append("第 %d 行不是合法 JSON（%s）" % (lineno, str(exc)[:60]))
            continue
        if not isinstance(obj, dict):
            errors.append("第 %d 行不是 JSON 对象" % lineno)
            continue
        if "task_id" not in obj:
            errors.append("第 %d 行缺 task_id" % lineno)
            continue
        if "answer" not in obj:
            errors.append("第 %d 行缺 answer 字段" % lineno)
            continue
        tid = obj["task_id"]
        if isinstance(tid, bool):
            errors.append("第 %d 行 task_id 类型非法（bool）" % lineno)
            continue
        if isinstance(tid, int):
            tid = str(tid)
        if not isinstance(tid, str) or not tid.strip():
            errors.append("第 %d 行 task_id 不是非空字符串" % lineno)
            continue
        tid = tid.strip()
        answer = obj["answer"]
        if not isinstance(answer, str):
            errors.append("第 %d 行 answer 不是 JSON 字符串（实际 %s）"
                          % (lineno, type(answer).__name__))
            continue
        if tid in entries:
            errors.append("task_id=%s 重复出现（第 %d 行）" % (tid, lineno))
            continue
        entries[tid] = answer
    return entries, errors, seen


# ---------------------------------------------------------------------------
# 判分
# ---------------------------------------------------------------------------

def _brief(text, limit=90) -> str:
    text = str(text)
    return text if len(text) <= limit else text[:limit] + "…"


def judge(run_dir: Path, case_dir: Path = CASE_DIR) -> dict:
    truth, gold, questions = load_and_guard(case_dir)
    order = [str(q["task_id"]) for q in questions]
    checks = []

    # ---- 产物
    artifact = find_artifact(run_dir)
    entries = {}
    format_ok = False
    if artifact is None:
        format_note = "缺失 %s（约定位置：run_dir/、run_dir/output/、run_dir/outputs/）" % ARTIFACT
        checks.append({"id": "answers_format", "pass": False, "note": format_note})
        format_ok = False
    else:
        size = artifact.stat().st_size
        if size > MAX_ARTIFACT_BYTES:
            format_note = "%s 体积 %d 字节 > 上限 %d（疑似非答案文件）" % (
                ARTIFACT, size, MAX_ARTIFACT_BYTES)
            checks.append({"id": "answers_format", "pass": False, "note": format_note})
        else:
            try:
                raw_text = artifact.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                raw_text = ""
                entries = {}
                parse_errors = ["文件不是合法 UTF-8：%s" % str(exc)[:60]]
                seen = 0
            else:
                entries, parse_errors, seen = parse_answers(raw_text)
            unknown = sorted(set(entries) - set(gold))
            missing = [tid for tid in order if tid not in entries]
            if unknown:
                parse_errors.append("出现未知 task_id：%s" % ", ".join(unknown[:5]))
            if missing:
                parse_errors.append("缺少 %d 题未作答：%s" % (len(missing), ", ".join(missing)))
            if seen != len(order) and not missing and not unknown:
                parse_errors.append("有效行数 %d != 题数 %d" % (seen, len(order)))
            format_ok = not parse_errors
            if format_ok:
                format_note = "%s 结构合法：%d 题各一行，answer 均为 JSON 字符串" % (
                    ARTIFACT, len(entries))
            else:
                format_note = "结构违规：%s" % "；".join(parse_errors[:3])
            checks.append({"id": "answers_format", "pass": format_ok, "note": format_note})

    # ---- 输入完整性守卫
    mismatched = []
    verified = 0
    for name in INPUT_FILES:
        copy = find_input_copy(run_dir, name)
        if copy is None:
            continue
        verified += 1
        if sha256_file(copy) != truth["input_sha256"][name]:
            mismatched.append(name)
    integrity_ok = not mismatched
    if mismatched:
        integrity_note = "输入副本被修改：%s（canonical SHA-256 不符）" % ", ".join(mismatched)
    elif verified == 0:
        integrity_note = "运行目录未附输入副本 → 未核验（不扣分）"
    else:
        integrity_note = "已核验 %d/%d 个输入副本，SHA-256 全部一致" % (verified, len(INPUT_FILES))
    checks.append({"id": "input_integrity", "pass": integrity_ok, "note": integrity_note})

    # ---- 逐题
    correct = 0
    for tid in order:
        gold_answer = gold[tid]
        if tid in entries:
            passed = question_scorer(entries[tid], gold_answer)
            note = "pred=%r ｜ gold=%r" % (_brief(entries[tid]), _brief(gold_answer))
        else:
            passed = False
            note = "未回答（gold=%r）" % _brief(gold_answer)
        correct += 1 if passed else 0
        checks.append({
            "id": "q%s" % tid,
            "pass": bool(passed),
            "note": note,
            "task_id": tid,
            "level": next((q.get("level") for q in questions
                           if str(q.get("task_id")) == tid), None),
        })

    rate = correct / float(N_TASKS)
    weighted = round(rate * 100.0, 1)
    reward = 1 if (format_ok and integrity_ok and rate >= THRESHOLD) else 0
    failed = [item["id"] for item in checks if not item["pass"]]

    return {
        "case": CASE_ID,
        "case_id": CASE_ID,
        "checker_version": CHECKER_VERSION,
        "binary": BINARY,
        "run_dir": str(run_dir),
        "artifact": str(artifact) if artifact else None,
        "reward": reward,
        "weighted": weighted,
        "score_rate": round(rate, 4),
        "threshold": THRESHOLD,
        "correct": correct,
        "n_tasks": N_TASKS,
        "gates": {"answers_format": format_ok, "input_integrity": integrity_ok},
        "input_integrity": "FAIL" if mismatched else ("verified" if verified else "not_provided"),
        "checks": checks,
        "failed": failed,
    }


def render(result: dict) -> str:
    lines = ["[%s] checker v%s  artifact=%s"
             % (CASE_ID, CHECKER_VERSION, result.get("artifact"))]
    for item in result["checks"]:
        status = "PASS" if item["pass"] else "FAIL"
        lines.append("%-5s %-16s %s" % (status, item["id"], item["note"]))
    lines.append("REWARD %d (binary)   WEIGHTED %.1f/100 (score rate %.1f%%, threshold %.0f%%)   "
                 "correct %d/%d   GATES format=%s integrity=%s"
                 % (result["reward"], result["weighted"], result["score_rate"] * 100,
                    result["threshold"] * 100, result["correct"], result["n_tasks"],
                    result["gates"]["answers_format"], result["gates"]["input_integrity"]))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# selftest
# ---------------------------------------------------------------------------

def _write_answers(path: Path, answers: dict, order) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for tid in order:
            if tid in answers:
                fh.write(json.dumps({"task_id": tid, "answer": answers[tid]},
                                    ensure_ascii=False) + "\n")


def _copy_canonical_inputs(run_dir: Path) -> None:
    target = run_dir / "inputs"
    target.mkdir(parents=True, exist_ok=True)
    for name in INPUT_FILES:
        shutil.copyfile(CASE_DIR / "inputs" / name, target / name)


def _temp_case_with_patch():
    """建立一份可篡改的用例副本（inputs 用符号链接），用于守卫 ERROR 自测。"""
    tmp = tempfile.TemporaryDirectory()
    case = Path(tmp.name) / "case"
    (case / "inputs").mkdir(parents=True)
    (case / "solution").mkdir(parents=True)
    shutil.copyfile(CASE_DIR / "truth.json", case / "truth.json")
    shutil.copyfile(CASE_DIR / "solution" / "answers.jsonl", case / "solution" / "answers.jsonl")
    for name in INPUT_FILES:
        os.symlink(CASE_DIR / "inputs" / name, case / "inputs" / name)
    return tmp, case


def _guard_error_fixture(kind: str):
    """返回 (ok, detail)：期望 load_and_guard 抛 CaseError。"""
    tmp, case = _temp_case_with_patch()
    try:
        if kind == "tampered_input":
            (case / "inputs" / "payments.csv").unlink()
            (case / "inputs" / "payments.csv").write_bytes(b"psp_reference,merchant\n1,fake\n")
        elif kind == "threshold_drift":
            truth = json.loads((case / "truth.json").read_text(encoding="utf-8"))
            truth["threshold"] = 0.9
            (case / "truth.json").write_text(json.dumps(truth, ensure_ascii=False), encoding="utf-8")
        elif kind == "sha_drift":
            truth = json.loads((case / "truth.json").read_text(encoding="utf-8"))
            truth["input_sha256"]["manual.md"] = "0" * 64
            (case / "truth.json").write_text(json.dumps(truth, ensure_ascii=False), encoding="utf-8")
        elif kind == "solution_drift":
            sol = case / "solution" / "answers.jsonl"
            rows = [json.loads(line) for line in sol.read_text(encoding="utf-8").splitlines()
                    if line.strip()]
            rows[0]["answer"] = "___definitely_wrong___"
            sol.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                           encoding="utf-8")
        else:
            raise AssertionError("未知 fixture: %s" % kind)
        try:
            load_and_guard(case)
        except CaseError as exc:
            return True, str(exc).splitlines()[0][:120]
        return False, "未抛 CaseError"
    finally:
        tmp.cleanup()


def selftest() -> int:
    truth, gold, questions = load_and_guard()
    order = [str(q["task_id"]) for q in questions]
    oracle = {tid: gold[tid] for tid in order}

    def variant():
        """合法但写法不同的答案：空白/大小写/列表乱序/数字补零。"""
        data = dict(oracle)
        data["5"] = "  nl  "
        data["49"] = "b.be"
        items = [x.strip() for x in gold["1464"].split(",")]
        data["1464"] = ", ".join(reversed(items))
        data["1871"] = "-0.948103000000170"
        return data

    def drop(tid):
        data = dict(oracle)
        data.pop(tid)
        return data

    def wrong(n, mapping):
        data = dict(oracle)
        data.update(mapping)
        return data

    def raw_lines(lines):
        return lines

    fixtures = []  # (name, expect_reward, setup(run_dir)->None, check_fn)

    def add(name, expect, setup, check=None):
        fixtures.append((name, expect, setup, check))

    def setup_answers(data):
        return lambda run_dir: _write_answers(run_dir / ARTIFACT, data, order)

    def setup_raw(text):
        return lambda run_dir: (run_dir / ARTIFACT).write_text(text, encoding="utf-8")

    # 正对照
    add("oracle：solution/answers.jsonl 原样", 1, setup_answers(oracle))
    add("oracle＋canonical 输入副本（运行器拷贝形态）", 1,
        lambda run_dir: (setup_answers(oracle)(run_dir), _copy_canonical_inputs(run_dir)),
        check=lambda r: r["gates"]["input_integrity"] and r["input_integrity"] == "verified")
    add("oracle 等价写法（空白/大小写/列表乱序/数字补零）", 1, setup_answers(variant()),
        check=lambda r: r["reward"] == 1 and r["correct"] == N_TASKS)
    add("容错边界：仅 q49 答错（9/10=0.9 过线）", 1,
        setup_answers(wrong(1, {"49": "A. NL"})),
        check=lambda r: r["reward"] == 1 and r["correct"] == 9 and "q49" in r["failed"])
    add("达标线边界：10 题错 2（8/10=0.8，恰好过线）", 1,
        setup_answers(wrong(2, {"49": "A. NL", "70": "yes"})),
        check=lambda r: r["reward"] == 1 and r["correct"] == 8)

    # 负对照（结构否决）
    add("nop：空运行目录", 0,
        lambda run_dir: None,
        check=lambda r: r["reward"] == 0 and r["weighted"] == 0.0
        and r["failed"][0] == "answers_format")
    add("漏答 1 题（9 行，得分率 0.9 但结构否决）", 0,
        setup_answers(drop("1871")),
        check=lambda r: r["reward"] == 0 and r["failed"] == ["answers_format", "q1871"])
    add("多答 1 题（11 行，出现未知 task_id=9999）", 0,
        setup_raw("\n".join(
            [json.dumps({"task_id": tid, "answer": oracle[tid]}, ensure_ascii=False)
             for tid in order]
            + [json.dumps({"task_id": "9999", "answer": "extra"}, ensure_ascii=False)]) + "\n"),
        check=lambda r: r["reward"] == 0 and "answers_format" in r["failed"])
    add("格式错：某行缺 answer 字段", 0,
        setup_raw("\n".join(
            [json.dumps({"task_id": tid, "answer": oracle[tid]}, ensure_ascii=False)
             if tid != "5" else json.dumps({"task_id": "5"}) for tid in order]) + "\n"),
        check=lambda r: r["reward"] == 0 and "answers_format" in r["failed"])
    add("格式错：answer 为 null（非字符串）", 0,
        setup_raw("\n".join(
            [json.dumps({"task_id": tid, "answer": oracle[tid]}, ensure_ascii=False)
             if tid != "5" else json.dumps({"task_id": "5", "answer": None}) for tid in order]) + "\n"),
        check=lambda r: r["reward"] == 0 and "answers_format" in r["failed"])
    add("格式错：第 3 行非法 JSON（尾随逗号）", 0,
        setup_raw("\n".join(
            [json.dumps({"task_id": tid, "answer": oracle[tid]}, ensure_ascii=False)
             for tid in order[:2]])
        + "\n" + '{"task_id": "70", "answer": "Not Applicable",}\n'),
        check=lambda r: r["reward"] == 0 and "answers_format" in r["failed"])
    add("重复 task_id（10 行，q2697 被写成 q1871）", 0,
        setup_raw("\n".join(
            [json.dumps({"task_id": "1871" if tid == "2697" else tid,
                         "answer": oracle[tid]}, ensure_ascii=False) for tid in order]) + "\n"),
        check=lambda r: r["reward"] == 0 and "answers_format" in r["failed"])

    # 近正确负例（得分率不足）
    add("近正确：q49/q1273/q1464 三题答错（0.7 < 0.8）", 0,
        setup_answers(wrong(3, {"49": "A. NL", "1273": "0.130000", "1464": "1, 2, 5"})),
        check=lambda r: r["reward"] == 0 and r["correct"] == 7 and r["weighted"] == 70.0)
    add("近正确：N/A 题（q70）硬答 yes 且另 2 题错（0.7）", 0,
        setup_answers(wrong(3, {"70": "yes", "1273": "0.130000", "1871": "-0.5"})),
        check=lambda r: r["reward"] == 0 and r["correct"] == 7)

    # 守卫否决（run_dir 附带输入副本被改）
    add("守卫：附篡改的 inputs/payments.csv（答案全对）", 0,
        lambda run_dir: (setup_answers(oracle)(run_dir),
                         (run_dir / "inputs").mkdir(exist_ok=True),
                         (run_dir / "inputs" / "payments.csv").write_bytes(b"tampered\n")),
        check=lambda r: r["reward"] == 0 and r["failed"] == ["input_integrity"])
    add("守卫：附篡改的 inputs/questions.jsonl（答案全对）", 0,
        lambda run_dir: (setup_answers(oracle)(run_dir),
                         (run_dir / "inputs").mkdir(exist_ok=True),
                         (run_dir / "inputs" / "questions.jsonl").write_bytes(b"{}\n")),
        check=lambda r: r["reward"] == 0 and r["failed"] == ["input_integrity"])

    print("[%s] checker v%s 自测（canonical inputs sha256[payments.csv]=%s…，"
          "TASKS=%d，THRESHOLD=%.2f）"
          % (CASE_ID, CHECKER_VERSION, truth["input_sha256"]["payments.csv"][:12],
             N_TASKS, THRESHOLD))

    failures = 0
    for name, expect, setup, check in fixtures:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()
            setup(run_dir)
            result = judge(run_dir)
            ok = result["reward"] == expect
            if ok and check is not None:
                try:
                    ok = bool(check(result))
                except AssertionError:
                    ok = False
            failures += 0 if ok else 1
            extra = "" if ok else "；reward=%d failed=%s" % (
                result["reward"], ",".join(result["failed"])[:120])
            print("  %s  %-52s reward=%d（期望 %d）%s"
                  % ("PASS" if ok else "FAIL", name, result["reward"], expect, extra))

    # 守卫 ERROR 自测（退出码 2 语义：canonical/truth/solution 漂移）
    for kind, label in (("tampered_input", "canonical inputs/payments.csv 被改"),
                        ("threshold_drift", "truth.threshold 漂移（0.8→0.9）"),
                        ("sha_drift", "truth.input_sha256 漂移"),
                        ("solution_drift", "solution oracle 漂移")):
        ok, detail = _guard_error_fixture(kind)
        failures += 0 if ok else 1
        print("  %s  %-52s ERROR=%s（期望 ERROR）%s"
              % ("PASS" if ok else "FAIL", "守卫：" + label, ok,
                 "" if ok else "；" + detail))

    total = len(fixtures) + 4
    print("负控制自测：%s（%d 组，含 %d 组近正确负例）"
          % ("通过" if failures == 0 else "%d 项不符合预期" % failures,
             total, len([f for f in fixtures if f[1] == 0])))
    return 0 if failures == 0 else 1


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv) -> int:
    parser = argparse.ArgumentParser(
        description="dabstep-payments-10 轻量判卷器 v%s" % CHECKER_VERSION)
    parser.add_argument("run_dir", nargs="?", help="运行目录（含 answers.jsonl，可选 inputs/ 副本）")
    parser.add_argument("--json", action="store_true", help="只输出一行 JSON")
    parser.add_argument("--selftest", action="store_true", help="跑正/负控制与守卫自测")
    args = parser.parse_args(argv)

    if args.selftest:
        try:
            return selftest()
        except CaseError as exc:
            print("ERROR: %s" % exc, file=sys.stderr)
            return 2
    if not args.run_dir:
        parser.error("缺少 run_dir（或使用 --selftest）")
    try:
        result = judge(Path(args.run_dir))
    except CaseError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(render(result))
        print("RESULTS_JSON " + json.dumps(result, ensure_ascii=False))
    return 0 if result["reward"] == 1 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))