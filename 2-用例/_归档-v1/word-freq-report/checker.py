#!/usr/bin/env python3
"""word-freq-report 轻量判卷器 v0.3（2026-10-21）

用法：
    python3 checker.py <run_dir> [--json]
    python3 checker.py --selftest

run_dir 约定（见 spec.md）：
    report.txt        必需产物；也接受 run_dir/output/ 或 run_dir/outputs/ 下同名文件
    corpus.txt        可选；存在时核对 SHA-256（输入完整性守卫）
    meta.json         可选；运行元信息，不参与判分

口径：
    headline 为二值 0/1（沿用 4-打分细则/打分表.md v0.2：全 PASS=1，任一 FAIL=0）。
    期望值从 canonical corpus 现算，并与 truth.json 交叉校验（防实现漂移、防硬编码）。
    输入副本与 canonical 不一致 → 直接 0；未附输入副本 → 「未核验」，不因此扣分。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

CASE_ID = "word-freq-report"
CHECKER_VERSION = "0.3"
BINARY = True
ARTIFACT = "report.txt"
PUNCT = set(".,;:!?\"'()-")
LINE_RE = re.compile(r"(\S+) ([0-9]+)\Z")

CASE_DIR = Path(__file__).resolve().parent

ITEMS = [
    ("artifact_exists", "产物存在", 10),
    ("input_integrity", "输入完整性（守卫）", 10),
    ("format_strict", "严格格式（7 行/LF/单空格/结尾换行）", 20),
    ("total_line", "第 1 行 = 总 token 数", 15),
    ("distinct_line", "第 2 行 = 去重词数", 15),
    ("top5_block", "第 3-7 行 = Top-5（频次降序 + ASCII 决胜）", 30),
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_truth(case_dir: Path = CASE_DIR) -> dict:
    return json.loads((case_dir / "truth.json").read_text(encoding="utf-8"))


def canonical_corpus(case_dir: Path = CASE_DIR):
    truth = load_truth(case_dir)
    path = case_dir / "environment" / truth["input_name"]
    data = path.read_bytes()
    actual = sha256_bytes(data)
    if actual != truth["input_sha256"]:
        raise SystemExit(f"ERROR: 用例 canonical 语料与 truth 记录不一致：{path}")
    return truth, data


def tokenize(text: str):
    """与 instruction.md / solve.sh 同一规则：按空白切分、去首尾标点、丢含数字、转小写。"""
    for raw in text.split():
        left, right = 0, len(raw)
        while left < right and raw[left] in PUNCT:
            left += 1
        while right > left and raw[right - 1] in PUNCT:
            right -= 1
        token = raw[left:right].lower()
        if not token:
            continue
        if any("0" <= char <= "9" for char in token):
            continue
        yield token


def expected_report(corpus_text: str) -> dict:
    counts = Counter(tokenize(corpus_text))
    top5 = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[:5]
    return {
        "total": sum(counts.values()),
        "distinct": len(counts),
        "top5": [[word, count] for word, count in top5],
    }


def find_file(run_dir: Path, name: str):
    for candidate in (run_dir / name, run_dir / "output" / name, run_dir / "outputs" / name):
        if candidate.is_file():
            return candidate
    return None


def find_input(run_dir: Path, name: str):
    for candidate in (run_dir / name, run_dir / "input" / name, run_dir / "inputs" / name):
        if candidate.is_file():
            return candidate
    return None


def check_structure(raw: bytes):
    """严格结构检查：UTF-8、LF、恰好一个结尾换行、恰好 7 行、行格式 `<word> <count>` 单空格。"""
    if b"\r" in raw:
        return False, "含 CR / CRLF（要求纯 LF）", []
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return False, "不是合法 UTF-8", []
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if not text.endswith("\n"):
        return False, "缺少结尾换行", lines
    if text.endswith("\n\n"):
        return False, "结尾有多余空行", lines
    if len(lines) != 7:
        return False, f"行数 {len(lines)}，要求 7", lines
    for index, line in enumerate(lines, 1):
        if line != line.strip():
            return False, f"第 {index} 行首尾有空白", lines
        if index <= 2:
            if not re.fullmatch(r"0|[1-9][0-9]*", line):
                return False, f"第 {index} 行不是规范十进制整数：{line!r}", lines
        else:
            match = LINE_RE.match(line)
            if not match:
                return False, f"第 {index} 行格式应为 '<word> <count>'（单空格）：{line!r}", lines
            if match.group(2) != str(int(match.group(2))):
                return False, f"第 {index} 行计数不是规范十进制：{line!r}", lines
    return True, "", lines


def _items_pass(items):
    return all(item["status"] != "fail" for item in items)


def judge(run_dir: Path) -> dict:
    truth, corpus_bytes = canonical_corpus()
    expected = expected_report(corpus_bytes.decode("utf-8"))
    if expected != truth["expected"]:
        raise SystemExit(
            "ERROR: checker 现算结果与 truth.json 不一致（用例规则/语料/实现有漂移）\n"
            f"  computed={json.dumps(expected, ensure_ascii=False)}\n"
            f"  truth={json.dumps(truth['expected'], ensure_ascii=False)}"
        )

    items: list[dict] = []
    details: dict = {}
    artifact = find_file(run_dir, ARTIFACT)
    if artifact is None:
        items.append({"id": "artifact_exists", "title": ITEMS[0][1], "weight": ITEMS[0][2],
                      "status": "fail", "detail": f"未找到 {ARTIFACT}（run_dir={run_dir}）"})
        for item_id, title, weight in ITEMS[1:]:
            items.append({"id": item_id, "title": title, "weight": weight,
                          "status": "fail", "detail": "产物缺失，无法检查"})
        return _result(items, run_dir=run_dir, input_integrity="unverified", artifact=None)

    raw = artifact.read_bytes()
    details["artifact_sha256"] = sha256_bytes(raw)
    items.append({"id": "artifact_exists", "title": ITEMS[0][1], "weight": ITEMS[0][2],
                  "status": "pass", "detail": str(artifact)})

    input_path = find_input(run_dir, truth["input_name"])
    if input_path is None:
        integrity = "unverified"
        items.append({"id": "input_integrity", "title": ITEMS[1][1], "weight": ITEMS[1][2],
                      "status": "unknown", "detail": "运行目录未附语料副本，无法核对（不扣分，但请在运行记录中说明）"})
    else:
        actual_corpus = input_path.read_bytes()
        details["input_sha256"] = sha256_bytes(actual_corpus)
        if actual_corpus == corpus_bytes:
            integrity = "verified"
            items.append({"id": "input_integrity", "title": ITEMS[1][1], "weight": ITEMS[1][2],
                          "status": "pass", "detail": "语料副本与 canonical 字节一致"})
        else:
            integrity = "mismatch"
            items.append({"id": "input_integrity", "title": ITEMS[1][1], "weight": ITEMS[1][2],
                          "status": "fail",
                          "detail": "语料被修改：实际使用语料与 canonical 不一致（判 0）"})

    format_ok, format_reason, lines = check_structure(raw)
    items.append({"id": "format_strict", "title": ITEMS[2][1], "weight": ITEMS[2][2],
                  "status": "pass" if format_ok else "fail",
                  "detail": "通过" if format_ok else format_reason})

    actual_total = lines[0] if len(lines) > 0 else None
    actual_distinct = lines[1] if len(lines) > 1 else None
    actual_top5 = []
    for line in lines[2:]:
        match = LINE_RE.match(line)
        actual_top5.append([match.group(1), int(match.group(2))] if match else None)

    weights = {item[0]: item[2] for item in ITEMS}
    titles = {item[0]: item[1] for item in ITEMS}

    def compare(item_id: str, expected_value, actual_value, label: str):
        ok = actual_value == expected_value
        items.append({"id": item_id, "title": titles[item_id], "weight": weights[item_id],
                      "status": "pass" if ok else "fail",
                      "detail": f"{label}：{'一致' if ok else '期望 ' + str(expected_value) + '，实际 ' + str(actual_value)}"})
        return ok

    compare("total_line", str(expected["total"]), actual_total, "第 1 行")
    compare("distinct_line", str(expected["distinct"]), actual_distinct, "第 2 行")
    compare("top5_block", expected["top5"], actual_top5, "第 3-7 行")

    return _result(items, run_dir=run_dir, input_integrity=integrity, artifact=artifact, details=details)


def _result(items, *, run_dir: Path, input_integrity: str, artifact, details=None):
    failed = [item for item in items if item["status"] == "fail"]
    weighted = sum(item["weight"] for item in items if item["status"] == "pass")
    return {
        "case_id": CASE_ID,
        "checker_version": CHECKER_VERSION,
        "binary": BINARY,
        "run_dir": str(run_dir),
        "artifact": str(artifact) if artifact else None,
        "items": items,
        "failed": [item["id"] for item in failed],
        "reward": 0 if failed else 1,
        "weighted": weighted,
        "max_weight": sum(item[2] for item in ITEMS),
        "input_integrity": input_integrity,
        **(details or {}),
    }


def render(result: dict) -> str:
    lines = [f"[{CASE_ID}] checker v{CHECKER_VERSION}  artifact={result.get('artifact')}"]
    for item in result["items"]:
        status = {"pass": "PASS", "fail": "FAIL", "unknown": "UNKNOWN"}[item["status"]]
        lines.append(f"{status:7s} {item['id']:18s} {item['weight']:>3d}/100  {item['detail']}")
    lines.append(f"REWARD {result['reward']} (binary)   WEIGHTED {result['weighted']}/{result['max_weight']}   "
                 f"INPUT {result['input_integrity']}")
    return "\n".join(lines)


# ---------------------------------------------------------------- selftest

def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data, encoding="utf-8")


def report_bytes(total: int, distinct: int, top5) -> bytes:
    lines = [str(total), str(distinct)] + [f"{word} {count}" for word, count in top5]
    return ("\n".join(lines) + "\n").encode("utf-8")


def selftest() -> int:
    truth, corpus_bytes = canonical_corpus()
    expected = expected_report(corpus_bytes.decode("utf-8"))
    top5 = [tuple(pair) for pair in expected["top5"]]
    valid = report_bytes(expected["total"], expected["distinct"], top5)

    wrong_tie = list(top5)
    wrong_tie[4] = ("tests", 5)  # 'a'/'dog'/'tests' 同为 5 次，错误决胜把 tests 排进 Top-5

    fixtures = []

    def add(name, *, expect, output=valid, include_input=True, input_data=None):
        fixtures.append((name, expect, output, include_input, input_data))

    add("golden：规范产物", expect=1)
    add("平票决胜写错（tests 顶掉 dog）", expect=0,
        output=report_bytes(expected["total"], expected["distinct"], wrong_tie))
    add("缺产物", expect=0, output=None)
    add("少一行", expect=0, output=("\n".join(valid.decode().splitlines()[:6]) + "\n").encode())
    add("多一行", expect=0, output=(valid.decode() + "extra\n").encode())
    add("缺结尾换行", expect=0, output=valid[:-1])
    add("结尾多空行", expect=0, output=valid + b"\n")
    add("CRLF 行尾", expect=0, output=valid.replace(b"\n", b"\r\n"))
    add("双空格", expect=0, output=valid.replace(b"a 5", b"a  5"))
    add("篡改语料后自洽作答", expect=0,
        output=b"5\n5\na 1\nb 1\nc 1\nd 1\ne 1\n", input_data=b"a b c d e\n")
    add("未附语料副本（未核验，不扣分）", expect=1, include_input=False)

    failures = 0
    print(f"[{CASE_ID}] checker v{CHECKER_VERSION} 自测（canonical corpus sha256={truth['input_sha256'][:12]}…）")
    print(f"  期望值现算并与 truth 交叉校验通过：total={expected['total']} distinct={expected['distinct']} "
          f"top5={expected['top5']}")
    for name, expect, output, include_input, input_data in fixtures:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            if output is not None:
                _write(run_dir / "report.txt", output)
            if include_input:
                _write(run_dir / "corpus.txt", input_data if input_data is not None else corpus_bytes)
            result = judge(run_dir)
            ok = result["reward"] == expect
            failures += 0 if ok else 1
            print(f"  {'PASS' if ok else 'FAIL'}  {name}: reward={result['reward']}（期望 {expect}）"
                  f"{'；失败项=' + ','.join(result['failed']) if result['failed'] else ''}")
    print(f"负控制自测：{'通过' if failures == 0 else f'{failures} 项不符合预期'}")
    return 0 if failures == 0 else 1


def main(argv) -> int:
    parser = argparse.ArgumentParser(description="word-freq-report 轻量判卷器 v0.3")
    parser.add_argument("run_dir", nargs="?", help="运行目录（含 report.txt，可选 corpus.txt）")
    parser.add_argument("--json", action="store_true", help="只输出 JSON")
    parser.add_argument("--selftest", action="store_true", help="跑负控制/守卫自测")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.run_dir:
        parser.error("缺少 run_dir（或使用 --selftest）")

    result = judge(Path(args.run_dir))
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(render(result))
        print("RESULTS_JSON " + json.dumps(result, ensure_ascii=False))
    return 0 if result["reward"] == 1 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
