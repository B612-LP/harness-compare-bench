#!/usr/bin/env python3
"""校验运行记录里的「行为分 JSON（schema v1）」。

用法：
    python3 validate_run.py <运行记录.md> [--strict-evidence] [--json]
    python3 validate_run.py --selftest

退出码：
    0 = 校验通过
    1 = 校验失败（结构/取值/证据不合法）
    2 = 用法错误，或 --selftest 有样例不符合预期

设计对应「判卷器也要被测试」：--selftest 内置正例 + 5 类负例，
正例必须过，负例必须被拒；改本脚本后先跑 --selftest。

schema v1 字段见 `运行记录模板.md` §5.1。规则：
- status ∈ {valid, failed, invalid, unknown}；unknown 不允许写成 0/满分。
- behavior[].score ∈ {0,1,2,3} 或字符串 "N/A"；N/A 必须给 reason。
- evidence 为相对运行记录文件所在目录的路径；--strict-evidence 下必须存在。
- unknowns[]（可为空）每项必须有 item/impact/next_step/stop_condition。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

SCHEMA_VERSION = 1
STATUSES = {"valid", "failed", "invalid", "unknown"}
BEHAVIOR_ITEMS = {"交付完整性", "回传说明", "异常/边界处理"}
UNKNOWN_KEYS = ("item", "impact", "next_step", "stop_condition")


def find_json_block(text: str) -> tuple[dict | None, str | None]:
    """取第一个含 schema_version 的 ```json 块。"""
    blocks = re.findall(r"```json\s*\n(.*?)\n```", text, flags=re.DOTALL)
    for block in blocks:
        if '"schema_version"' in block:
            try:
                return json.loads(block), None
            except json.JSONDecodeError as exc:
                return None, f"JSON 解析失败：{exc}"
    return None, "未找到含 \"schema_version\" 的 ```json 块（见模板 §5.1）"


def validate(record: dict, record_dir: Path, strict_evidence: bool) -> list[str]:
    errors: list[str] = []

    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version 必须为 {SCHEMA_VERSION}")

    for key in ("run_id", "case", "spec_version"):
        value = record.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{key} 必须是非空字符串")

    product = record.get("product")
    if not isinstance(product, dict):
        errors.append("product 必须是对象")
    else:
        for key in ("name", "version", "model_shown", "form"):
            value = product.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"product.{key} 必须是非空字符串")
        if isinstance(product.get("form"), str) and product["form"] not in {"GUI", "CLI", "其他"}:
            errors.append("product.form 只能是 GUI / CLI / 其他")

    if record.get("status") not in STATUSES:
        errors.append(f"status 必须是 {sorted(STATUSES)} 之一")

    behavior = record.get("behavior")
    if not isinstance(behavior, list) or not behavior:
        errors.append("behavior 必须是非空数组")
    else:
        seen: list[str] = []
        for idx, entry in enumerate(behavior):
            where = f"behavior[{idx}]"
            if not isinstance(entry, dict):
                errors.append(f"{where} 必须是对象")
                continue
            item = entry.get("item")
            if not isinstance(item, str) or not item.strip():
                errors.append(f"{where}.item 必须是非空字符串")
            else:
                seen.append(item)
            score = entry.get("score")
            is_na = score == "N/A"
            if not (is_na or (isinstance(score, int) and not isinstance(score, bool) and 0 <= score <= 3)):
                errors.append(f"{where}.score 只能是 0–3 整数或 \"N/A\"，实为 {score!r}")
            reason = entry.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                errors.append(f"{where}.reason 必须是非空字符串（N/A 也要写原因）")
            evidence = entry.get("evidence")
            if not isinstance(evidence, list) or any(not isinstance(p, str) or not p.strip() for p in evidence):
                errors.append(f"{where}.evidence 必须是字符串数组")
                continue
            if strict_evidence:
                for path in evidence:
                    if path.startswith(("http://", "https://")):
                        errors.append(f"{where}.evidence 应为仓内相对路径，不接受外部链接：{path}")
                    elif not (record_dir / path).exists():
                        errors.append(f"{where}.evidence 路径不存在：{path}")
        missing = BEHAVIOR_ITEMS - set(seen)
        if missing:
            errors.append(f"behavior 缺少观察项：{sorted(missing)}")

    unknowns = record.get("unknowns")
    if unknowns is not None:
        if not isinstance(unknowns, list):
            errors.append("unknowns 必须是数组（没有未知写 []）")
        else:
            for idx, entry in enumerate(unknowns):
                where = f"unknowns[{idx}]"
                if not isinstance(entry, dict):
                    errors.append(f"{where} 必须是对象")
                    continue
                for key in UNKNOWN_KEYS:
                    value = entry.get(key)
                    if not isinstance(value, str) or not value.strip():
                        errors.append(f"{where}.{key} 必须是非空字符串")
    return errors


def run(record_path: Path, strict_evidence: bool, as_json: bool) -> int:
    errors = _validate_file(record_path, strict_evidence)
    if as_json:
        print(json.dumps({"ok": not errors, "record": str(record_path), "errors": errors}, ensure_ascii=False))
    else:
        if errors:
            print(f"FAIL  {record_path}")
            for err in errors:
                print(f"  - {err}")
        else:
            print(f"PASS  {record_path}  （行为分 JSON schema v{SCHEMA_VERSION} 校验通过）")
    return 0 if not errors else 1


def _validate_file(record_path: Path, strict_evidence: bool) -> list[str]:
    try:
        text = record_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"读取失败：{exc}"]
    record, err = find_json_block(text)
    if err:
        return [err]
    return validate(record, record_path.parent, strict_evidence)


# ---------------------------------------------------------------- selftest

GOOD_JSON = {
    "schema_version": 1,
    "run_id": "demo-case-demo-product-run1",
    "case": "demo-case",
    "spec_version": "v0.1",
    "product": {"name": "demo", "version": "1.0", "model_shown": "未知", "form": "GUI"},
    "status": "valid",
    "behavior": [
        {"item": "交付完整性", "score": 2, "reason": "产物正确", "evidence": ["artifact.txt"]},
        {"item": "回传说明", "score": 1, "reason": "只说完成", "evidence": ["artifact.txt"]},
        {"item": "异常/边界处理", "score": "N/A", "reason": "自动批跑无观察", "evidence": []},
    ],
    "unknowns": [
        {"item": "模型版本", "impact": "无法归因到模型层", "next_step": "补日志", "stop_condition": "产品不提供即保持 unknown"}
    ],
}


def _wrap(record: dict) -> str:
    return "# 运行记录 · demo\n\n## 5. 行为分\n\n```json\n" + json.dumps(record, ensure_ascii=False, indent=2) + "\n```\n"


def selftest() -> int:
    cases: list[tuple[str, str, bool, int]] = []

    def add(name: str, record: dict, strict: bool, expected: int) -> None:
        cases.append((name, _wrap(record), strict, expected))

    good = json.loads(json.dumps(GOOD_JSON))  # deep copy
    add("正例", good, True, 0)

    missing = json.loads(json.dumps(GOOD_JSON))
    del missing["case"]
    add("缺必填字段", missing, False, 1)

    bad_score = json.loads(json.dumps(GOOD_JSON))
    bad_score["behavior"][0]["score"] = 4
    add("档位越界", bad_score, False, 1)

    bad_status = json.loads(json.dumps(GOOD_JSON))
    bad_status["status"] = "pass"
    add("状态非法", bad_status, False, 1)

    missing_stop = json.loads(json.dumps(GOOD_JSON))
    missing_stop["unknowns"][0]["stop_condition"] = ""
    add("未知项缺停止条件", missing_stop, False, 1)

    cases.append(("证据路径不存在（strict）", _wrap(GOOD_JSON), True, 1))

    failed = 0
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        (tmpdir / "artifact.txt").write_text("ok\n", encoding="utf-8")
        for idx, (name, text, strict, expected) in enumerate(cases):
            path = tmpdir / f"case{idx}.md"
            if name == "证据路径不存在（strict）":
                text = text.replace("artifact.txt", "missing.png")
            path.write_text(text, encoding="utf-8")
            errors = _validate_file(path, strict)
            got = 0 if not errors else 1
            ok = got == expected
            failed += 0 if ok else 1
            print(f"{'PASS' if ok else 'FAIL'}  selftest/{name}  expected={expected} got={got}")
            if not ok:
                print(f"      errors={errors}")

        no_json_path = tmpdir / "nojson.md"
        no_json_path.write_text("# 运行记录 · demo\n\n## 5. 行为分\n\n没有 JSON 块\n", encoding="utf-8")
        errors = _validate_file(no_json_path, False)
        ok = bool(errors)
        failed += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'}  selftest/无 JSON 块  expected=1 got={1 if errors else 0}")

    total = len(cases) + 1
    print(f"\nselftest: {total - failed}/{total} PASS")
    return 0 if failed == 0 else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="校验运行记录的行为分 JSON（schema v1）")
    parser.add_argument("record", nargs="?", help="运行记录 Markdown 路径")
    parser.add_argument("--strict-evidence", action="store_true", help="额外校验证据路径存在（相对记录文件目录）")
    parser.add_argument("--json", action="store_true", help="只输出 JSON 结果")
    parser.add_argument("--selftest", action="store_true", help="跑内置正/负例自测")
    args = parser.parse_args()

    if args.selftest:
        return selftest()
    if not args.record:
        parser.print_help()
        return 2
    path = Path(args.record).expanduser()
    if not path.is_file():
        print(f"ERROR 文件不存在：{path}", file=sys.stderr)
        return 2
    return run(path, args.strict_evidence, args.json)


if __name__ == "__main__":
    sys.exit(main())
