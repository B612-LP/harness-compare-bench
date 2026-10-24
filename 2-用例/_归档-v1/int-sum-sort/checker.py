#!/usr/bin/env python3
"""int-sum-sort 轻量判卷器 v0.3（2026-10-21）

用法：
    python3 checker.py <run_dir> [--json]
    python3 checker.py --selftest

run_dir 约定（见 spec.md）：
    output.txt        必需产物；也接受 run_dir/output/ 或 run_dir/outputs/ 下同名文件
    input.txt         可选；存在时核对 SHA-256（输入完整性守卫）
    meta.json         可选；产品/版本/操作人等运行元信息，不参与判分

口径：
    headline 为二值 0/1（沿用 4-打分细则/打分表.md v0.2：全 PASS=1，任一 FAIL=0）。
    逐项权重只用于复核定位与加权参考，不改变二值口径。
    输入副本与 canonical 不一致 → 直接 0（防「改输入再作答」）；
    未附输入副本 → 输入完整性记「未核验」，不因此扣分（证据不足不硬判）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path

CASE_ID = "int-sum-sort"
CHECKER_VERSION = "0.3"
BINARY = True
ARTIFACT = "output.txt"

CASE_DIR = Path(__file__).resolve().parent
INT_RE = re.compile(r"-?(?:0|[1-9][0-9]*)\Z")

ITEMS = [
    ("artifact_exists", "产物存在", 10),
    ("input_integrity", "输入完整性（守卫）", 10),
    ("format_strict", "严格格式（行数/LF/结尾换行/规范整数）", 20),
    ("sum_line", "第 1 行 = 输入总和", 20),
    ("count_line", "第 2 行 = 输入个数", 20),
    ("sorted_block", "其余行 = 升序整数", 20),
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_truth(case_dir: Path = CASE_DIR) -> dict:
    return json.loads((case_dir / "truth.json").read_text(encoding="utf-8"))


def canonical_input(case_dir: Path = CASE_DIR):
    """读取用例 canonical 输入，并用 truth.json 记录的 SHA-256 校验用例自身未被改动。"""
    truth = load_truth(case_dir)
    path = case_dir / "environment" / truth["input_name"]
    data = path.read_bytes()
    actual = sha256_bytes(data)
    if actual != truth["input_sha256"]:
        raise SystemExit(f"ERROR: 用例 canonical 输入与 truth 记录不一致：{path}\n  truth={truth['input_sha256']}\n  actual={actual}")
    return truth, data


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


def check_structure(raw: bytes, expected_count: int):
    """严格结构检查：UTF-8、LF、恰好一个结尾换行、每行一个规范十进制整数。"""
    lines = []
    if b"\r" in raw:
        return False, "含 CR / CRLF（要求纯 LF）", lines
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return False, "不是合法 UTF-8", lines
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if not text.endswith("\n"):
        return False, "缺少结尾换行", lines
    if text.endswith("\n\n"):
        return False, "结尾有多余空行", lines
    if len(lines) != expected_count:
        return False, f"行数 {len(lines)}，要求 {expected_count}", lines
    for index, line in enumerate(lines, 1):
        if line != line.strip():
            return False, f"第 {index} 行首尾有空白", lines
        if not INT_RE.match(line):
            return False, f"第 {index} 行不是规范十进制整数：{line!r}", lines
    return True, "", lines


def judge(run_dir: Path) -> dict:
    truth, input_bytes = canonical_input()
    values = [int(token) for token in input_bytes.decode("utf-8").split()]
    expected_lines = [str(sum(values)), str(len(values))] + [str(value) for value in sorted(values)]

    items = []
    details = {}

    artifact = find_file(run_dir, ARTIFACT)
    if artifact is None:
        items.append({"id": "artifact_exists", "title": ITEMS[0][1], "weight": ITEMS[0][2],
                      "status": "fail", "detail": f"未找到 {ARTIFACT}（run_dir={run_dir}）"})
        for item_id, title, weight in ITEMS[1:]:
            items.append({"id": item_id, "title": title, "weight": weight, "status": "fail",
                          "detail": "产物缺失，无法检查"})
        return _result(items, run_dir=run_dir, input_integrity="unverified", artifact=None)

    raw = artifact.read_bytes()
    details["artifact_sha256"] = sha256_bytes(raw)
    items.append({"id": "artifact_exists", "title": ITEMS[0][1], "weight": ITEMS[0][2],
                  "status": "pass", "detail": str(artifact)})

    # 输入完整性守卫
    input_path = find_input(run_dir, truth["input_name"])
    if input_path is None:
        integrity = "unverified"
        items.append({"id": "input_integrity", "title": ITEMS[1][1], "weight": ITEMS[1][2],
                      "status": "unknown", "detail": "运行目录未附输入副本，无法核对（不扣分，但请在运行记录中说明）"})
    else:
        actual_input = input_path.read_bytes()
        details["input_sha256"] = sha256_bytes(actual_input)
        if actual_input == input_bytes:
            integrity = "verified"
            items.append({"id": "input_integrity", "title": ITEMS[1][1], "weight": ITEMS[1][2],
                          "status": "pass", "detail": "输入副本与 canonical 字节一致"})
        else:
            integrity = "mismatch"
            items.append({"id": "input_integrity", "title": ITEMS[1][1], "weight": ITEMS[1][2],
                          "status": "fail",
                          "detail": "输入被修改：实际使用输入与 canonical 不一致（判 0）"})

    format_ok, format_reason, lines = check_structure(raw, len(expected_lines))
    items.append({"id": "format_strict", "title": ITEMS[2][1], "weight": ITEMS[2][2],
                  "status": "pass" if format_ok else "fail",
                  "detail": "通过" if format_ok else format_reason})

    def compare(item_id: str, expected, actual, label: str):
        ok = actual == expected
        items.append({"id": item_id, "title": dict((i[0], i[1]) for i in ITEMS)[item_id],
                      "weight": dict((i[0], i[2]) for i in ITEMS)[item_id],
                      "status": "pass" if ok else "fail",
                      "detail": f"{label}：{'一致' if ok else '期望 ' + repr(expected) + '，实际 ' + repr(actual)}"})
        return ok

    compare("sum_line", expected_lines[0], lines[0] if len(lines) > 0 else None, "第 1 行")
    compare("count_line", expected_lines[1], lines[1] if len(lines) > 1 else None, "第 2 行")
    compare("sorted_block", expected_lines[2:], lines[2:] if len(lines) > 2 else None, "其余行")

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


def selftest() -> int:
    truth, input_bytes = canonical_input()
    values = [int(token) for token in input_bytes.decode("utf-8").split()]
    expected = [str(sum(values)), str(len(values))] + [str(value) for value in sorted(values)]
    valid = ("\n".join(expected) + "\n").encode("utf-8")

    fixtures = []

    def add(name, *, expect, output=valid, include_input=True, input_data=None):
        fixtures.append((name, expect, output, include_input, input_data))

    add("golden：规范产物", expect=1)
    add("缺产物", expect=0, output=None)
    add("排序块折叠成一行（违反每行一个）", expect=0,
        output=("\n".join(expected[:2]) + "\n" + " ".join(expected[2:]) + "\n").encode("utf-8"))
    add("中间插空行", expect=0, output=("\n".join(expected[:2] + [""] + expected[2:]) + "\n").encode("utf-8"))
    add("缺结尾换行", expect=0, output=("\n".join(expected)).encode("utf-8"))
    add("结尾多一个空行", expect=0, output=("\n".join(expected) + "\n\n").encode("utf-8"))
    add("CRLF 行尾", expect=0, output=("\r\n".join(expected) + "\r\n").encode("utf-8"))
    add("行首空格", expect=0, output=(" " + valid.decode("utf-8")).encode("utf-8"))
    add("多一行", expect=0, output=(valid.decode("utf-8") + "0\n").encode("utf-8"))
    add("篡改输入后自洽作答", expect=0,
        output=b"5\n1\n5\n", input_data=b"5\n")
    add("未附输入副本（未核验，不扣分）", expect=1, include_input=False)

    failures = 0
    print(f"[{CASE_ID}] checker v{CHECKER_VERSION} 自测（canonical input sha256={truth['input_sha256'][:12]}…）")
    for name, expect, output, include_input, input_data in fixtures:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            _write(run_dir / "output.txt", output) if output is not None else None
            if include_input:
                _write(run_dir / "input.txt", input_data if input_data is not None else input_bytes)
            result = judge(run_dir)
            ok = result["reward"] == expect
            failures += 0 if ok else 1
            print(f"  {'PASS' if ok else 'FAIL'}  {name}: reward={result['reward']}（期望 {expect}）"
                  f"{'；失败项=' + ','.join(result['failed']) if result['failed'] else ''}")
    print(f"负控制自测：{'通过' if failures == 0 else f'{failures} 项不符合预期'}")
    return 0 if failures == 0 else 1


def main(argv) -> int:
    parser = argparse.ArgumentParser(description="int-sum-sort 轻量判卷器 v0.3")
    parser.add_argument("run_dir", nargs="?", help="运行目录（含 output.txt，可选 input.txt）")
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
