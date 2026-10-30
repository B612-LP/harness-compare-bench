#!/usr/bin/env python3
"""轻量判卷器模板 v0.1（2026-10-21）

用法（复制到 2-用例/<题>/checker.py 后使用）：
    python3 checker.py <run_dir> [--json]
    python3 checker.py --selftest

复制后按 TODO 改 5 处：
  1. CASE_ID / ARTIFACT / BINARY（binary 还是 partial 模式）
  2. ITEMS 权重（必须与同目录 spec.md 的观察项表一致，权重和 = 100）
  3. load_truth() 与 canonical_input()（truth.json 里放 canonical 输入 SHA-256）
  4. judge() 里的 check_* 实现（本模板用 demo：answer.txt 必须恰好是 "OK\\n42\\n"）
  5. selftest() 的 fixtures（≥6 组负例：缺产物/格式违规/错值/CRLF/篡改输入/未附输入副本）

三条纪律（见 ../README.md）：
  1. 验外部产物，不验自述
  2. 负控制必须能变红（--selftest 固化）
  3. 测真实产物路径 + 输入完整性守卫 + truth 交叉校验
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------- TODO 1
CASE_ID = "demo-case"
CHECKER_VERSION = "0.1"
BINARY = True                 # True=全 PASS 才 1；False=按权重给部分分
ARTIFACT = "answer.txt"

CASE_DIR = Path(__file__).resolve().parent
ITEMS = [                     # ------------------------------------------------- TODO 2
    ("artifact_exists", "产物存在", 20),
    ("input_integrity", "输入完整性（守卫）", 20),
    ("format_strict", "严格格式（恰好 2 行、LF、单结尾换行）", 20),
    ("content", "内容 = 'OK' + 42", 40),
]
EXPECTED_LINES = ["OK", "42"]     # demo 期望产物行；改题时替换
INPUT_NAME = "input.txt"
INPUT_BYTES = b"demo input\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_truth(case_dir: Path = CASE_DIR) -> dict:
    return json.loads((case_dir / "truth.json").read_text(encoding="utf-8"))


def canonical_input(case_dir: Path = CASE_DIR):
    """读取 canonical 输入并校验 truth.json 记录的 SHA-256；不一致说明用例被改动。"""
    truth = load_truth(case_dir)
    path = case_dir / "environment" / truth["input_name"]
    data = path.read_bytes()
    if sha256_bytes(data) != truth["input_sha256"]:
        raise SystemExit(f"ERROR: canonical 输入与 truth 记录不一致：{path}")
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
    """demo：恰好 expected_count 行、纯 LF、恰好一个结尾换行、无首尾空白。"""
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
    if len(lines) != expected_count:
        return False, f"行数 {len(lines)}，要求 {expected_count}", lines
    for index, line in enumerate(lines, 1):
        if line != line.strip():
            return False, f"第 {index} 行首尾有空白", lines
    return True, "", lines


def judge(run_dir: Path, case_dir: Path = CASE_DIR) -> dict:
    """返回：items / reward / weighted / input_integrity。TODO 4：替换检查逻辑。"""
    truth, input_bytes = canonical_input(case_dir)   # truth 交叉校验在此发生
    items = []

    artifact = find_file(run_dir, ARTIFACT)
    if artifact is None:
        for item_id, title, weight in ITEMS:
            items.append({"id": item_id, "title": title, "weight": weight,
                          "status": "fail", "detail": "产物缺失"})
        return _result(items, run_dir=run_dir, input_integrity="unverified", artifact=None)

    raw = artifact.read_bytes()
    items.append({"id": "artifact_exists", "title": "产物存在", "weight": 20,
                  "status": "pass", "detail": str(artifact)})

    input_path = find_input(run_dir, truth["input_name"])
    if input_path is None:
        integrity = "unverified"
        items.append({"id": "input_integrity", "title": "输入完整性（守卫）", "weight": 20,
                      "status": "unknown", "detail": "未附输入副本（不扣分，但需在运行记录中说明）"})
    elif input_path.read_bytes() == input_bytes:
        integrity = "verified"
        items.append({"id": "input_integrity", "title": "输入完整性（守卫）", "weight": 20,
                      "status": "pass", "detail": "输入副本与 canonical 一致"})
    else:
        integrity = "mismatch"
        items.append({"id": "input_integrity", "title": "输入完整性（守卫）", "weight": 20,
                      "status": "fail", "detail": "输入被修改（判 0）"})

    ok, reason, lines = check_structure(raw, len(EXPECTED_LINES))
    items.append({"id": "format_strict", "title": "严格格式", "weight": 20,
                  "status": "pass" if ok else "fail", "detail": "通过" if ok else reason})
    content_ok = lines == EXPECTED_LINES
    items.append({"id": "content", "title": "内容", "weight": 40,
                  "status": "pass" if content_ok else "fail",
                  "detail": "一致" if content_ok else f"期望 {EXPECTED_LINES!r}，实际 {lines!r}"})

    return _result(items, run_dir=run_dir, input_integrity=integrity, artifact=artifact)


def _result(items, *, run_dir: Path, input_integrity: str, artifact):
    failed = [item for item in items if item["status"] == "fail"]
    weighted = sum(item["weight"] for item in items if item["status"] == "pass")
    reward = (1 if not failed else 0) if BINARY else round(weighted / 100, 4)
    return {
        "case_id": CASE_ID, "checker_version": CHECKER_VERSION, "binary": BINARY,
        "run_dir": str(run_dir), "artifact": str(artifact) if artifact else None,
        "items": items, "failed": [item["id"] for item in failed],
        "reward": reward, "weighted": weighted, "max_weight": 100,
        "input_integrity": input_integrity,
    }


def render(result: dict) -> str:
    lines = [f"[{result['case_id']}] checker v{result['checker_version']}  artifact={result['artifact']}"]
    for item in result["items"]:
        status = {"pass": "PASS", "fail": "FAIL", "unknown": "UNKNOWN"}[item["status"]]
        lines.append(f"{status:7s} {item['id']:18s} {item['weight']:>3d}/100  {item['detail']}")
    lines.append(f"REWARD {result['reward']}  WEIGHTED {result['weighted']}/100  INPUT {result['input_integrity']}")
    return "\n".join(lines)


# ---------------------------------------------------------------- selftest（TODO 5）

def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data) if isinstance(data, bytes) else path.write_text(data, encoding="utf-8")


def selftest() -> int:
    """自测在临时目录里造一个迷你 case，不往仓库写文件。"""
    valid = ("\n".join(EXPECTED_LINES) + "\n").encode("utf-8")
    fixtures = [
        ("golden：规范产物", 1, valid, True, None),
        ("缺产物", 0, None, True, None),
        ("内容错", 0, b"OK\n41\n", True, None),
        ("缺结尾换行", 0, valid[:-1], True, None),
        ("多一行", 0, valid + b"extra\n", True, None),
        ("CRLF", 0, valid.replace(b"\n", b"\r\n"), True, None),
        ("篡改输入后自洽作答", 0, valid, True, b"tampered\n"),
        ("未附输入副本（未核验，不扣分）", 1, valid, False, None),
    ]
    failures = 0
    with tempfile.TemporaryDirectory() as case_tmp:
        case_dir = Path(case_tmp)
        _write(case_dir / "environment" / INPUT_NAME, INPUT_BYTES)
        _write(case_dir / "truth.json", json.dumps({
            "case_id": CASE_ID, "checker_version": CHECKER_VERSION,
            "input_name": INPUT_NAME, "input_sha256": sha256_bytes(INPUT_BYTES),
            "expected_lines": EXPECTED_LINES,
        }, ensure_ascii=False, indent=2) + "\n")
        for name, expect, output, include_input, input_data in fixtures:
            with tempfile.TemporaryDirectory() as tmp:
                run_dir = Path(tmp)
                if output is not None:
                    _write(run_dir / ARTIFACT, output)
                if include_input:
                    _write(run_dir / INPUT_NAME, input_data if input_data is not None else INPUT_BYTES)
                result = judge(run_dir, case_dir)
                ok = result["reward"] == expect
                failures += 0 if ok else 1
                print(f"  {'PASS' if ok else 'FAIL'}  {name}: reward={result['reward']}（期望 {expect}）")
    print(f"负控制自测：{'通过' if failures == 0 else f'{failures} 项不符合预期'}")
    return 0 if failures == 0 else 1


def main(argv) -> int:
    parser = argparse.ArgumentParser(description="轻量判卷器模板 v0.1")
    parser.add_argument("run_dir", nargs="?")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.run_dir:
        parser.error("缺少 run_dir（或使用 --selftest）")
    result = judge(Path(args.run_dir))
    print(json.dumps(result, ensure_ascii=False) if args.json else render(result))
    return 0 if result["reward"] == 1 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
