#!/usr/bin/env python3
"""C 组裸模型基线批次（deepseek-flash × 5 用例）。

协议对齐老 infra/bare_model.py（r1016x 现场同款）：
- 请求体 {"model", "input": 任务书原文}，POST {BASE}/responses；
- 无系统提示、无工具、单轮；模型看不到输入文件；
- 答案文本按各用例约定落盘为产物，再交该用例 checker.py <run_dir> 判分。

用法：
  DEEPSEEK_API_KEY=sk-... python3 bare_run.py            # 跑全部 5 题
  DEEPSEEK_API_KEY=sk-... python3 bare_run.py --only int-sum-sort

Key 只从环境变量读取，绝不写入任何文件。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]  # 3-表现现场/r1022-.../tools -> repo
HERE = Path(__file__).resolve().parent.parent  # 批次目录
BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-flash"
TIMEOUT = 240

CASES = [
    {
        "slug": "int-sum-sort",
        "inputs": ["environment/input.txt"],
        "artifacts": [{"path": "output.txt", "mode": "whole"}],
    },
    {
        "slug": "word-freq-report",
        "inputs": ["environment/corpus.txt"],
        "artifacts": [{"path": "report.txt", "mode": "whole"}],
    },
    {
        "slug": "jielong-fullchain",
        "inputs": ["environment/jielong.txt", "environment/peers.json", "environment/orders.json"],
        "artifacts": [
            {"path": "resolution.json", "mode": "fenced-json", "label": "resolution.json"},
            {"path": "plan.json", "mode": "fenced-json", "label": "plan.json"},
        ],
    },
    {
        "slug": "ledger-replay",
        "inputs": ["environment/events.jsonl"],
        "artifacts": [
            {"path": "final_state.json", "mode": "fenced-json", "label": "final_state.json"},
            {"path": "anomalies.json", "mode": "fenced-json", "label": "anomalies.json"},
        ],
    },
    {
        "slug": "corpus-squeeze",
        "inputs": ["inputs/corpus.txt"],
        "artifacts": [{"path": "decompress.py", "mode": "fenced-code"}],
    },
]


def call_api(instruction: str, key: str) -> tuple[dict, str]:
    body = json.dumps({"model": MODEL, "input": instruction}, ensure_ascii=False).encode()
    last_err = None
    for use_proxy in (False, True):
        req = urllib.request.Request(
            BASE_URL + "/responses",
            data=body,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        if use_proxy:
            req.set_proxy("127.0.0.1:7897", "https")
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read().decode()), ("direct" if not use_proxy else "proxy")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:500]
            raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
        except Exception as exc:  # 网络类错误换通道重试
            last_err = exc
    raise RuntimeError(f"网络失败（直连与代理均不通）: {last_err}")


def extract_text(response: dict) -> str:
    text = response.get("output_text")
    if isinstance(text, str) and text.strip():
        return text
    parts = []
    for item in response.get("output") or []:
        if isinstance(item, dict) and item.get("type") == "message":
            for block in item.get("content") or []:
                if isinstance(block, dict) and isinstance(block.get("text"), str):
                    parts.append(block["text"])
    return "\n".join(parts)


FENCED = re.compile(r"```([A-Za-z0-9_+-]*)[ \t]*\n(.*?)```", re.S)


def extract_artifacts(answer: str, specs: list[dict], run_dir: Path) -> dict:
    """按用例约定把答案文本落盘为产物，返回抽取注记。"""
    notes = {}
    blocks = [(m.group(1).lower(), m.group(2)) for m in FENCED.finditer(answer)]
    if len(specs) == 1 and specs[0]["mode"] == "whole":
        (run_dir / specs[0]["path"]).write_text(answer, encoding="utf-8")
        notes[specs[0]["path"]] = "whole answer"
        return notes
    remaining = list(specs)
    used = set()
    # 先按「围栏前两行内提到文件名」精确配对
    spans = [(m.start(), m.group(1).lower(), m.group(2)) for m in FENCED.finditer(answer)]
    for idx, (path_pos, lang, body) in enumerate(spans):
        context = answer[max(0, path_pos - 120):path_pos].lower()
        for spec in remaining:
            if spec["path"] in context:
                (run_dir / spec["path"]).write_text(body, encoding="utf-8")
                notes[spec["path"]] = f"fenced#{idx}（文件名精确配对）"
                used.add(idx)
                remaining.remove(spec)
                break
    # 其余按顺序填充
    for idx, (path_pos, lang, body) in enumerate(spans):
        if idx in used or not remaining:
            break
        spec = remaining.pop(0)
        (run_dir / spec["path"]).write_text(body, encoding="utf-8")
        notes[spec["path"]] = f"fenced#{idx}（顺序兜底）"
        used.add(idx)
    # 兜底：还没落盘的 → 第一个写整段答案（checker 会诚实判 0）
    for spec in remaining:
        if spec["mode"] == "fenced-code" and not list(run_dir.glob(spec["path"])):
            notes[spec["path"]] = "未抽取到（缺产物，交 checker 判）"
            continue
        if not (run_dir / spec["path"]).exists():
            (run_dir / spec["path"]).write_text(answer, encoding="utf-8")
            notes[spec["path"]] = "整段答案兜底（预期判 0）"
    return notes


def run_case(case: dict, key: str) -> dict:
    slug = case["slug"]
    case_dir = REPO / "2-用例" / slug
    instruction = (case_dir / "instruction.md").read_text(encoding="utf-8")
    run_dir = HERE / f"{slug}__bare1"
    n = 1
    while run_dir.exists():
        n += 1
        run_dir = HERE / f"{slug}__bare{n}"
    run_dir.mkdir(parents=True)

    started = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    response, channel = call_api(instruction, key)
    (run_dir / "bare-request.json").write_text(
        json.dumps({"model": MODEL, "input": instruction}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (run_dir / "bare-response.json").write_text(
        json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    answer = extract_text(response)
    notes = extract_artifacts(answer, case["artifacts"], run_dir)

    for rel in case["inputs"]:
        src = case_dir / rel
        if src.exists():
            (run_dir / Path(rel).name).write_bytes(src.read_bytes())

    usage = response.get("usage") or {}
    meta = {
        "run_id": run_dir.name,
        "case": slug,
        "group": "C-bare（裸模型基线，无系统提示/无工具/单轮）",
        "model": response.get("model") or MODEL,
        "endpoint": BASE_URL + "/responses",
        "channel": channel,
        "protocol": {
            "instruction_verbatim": True,
            "model_sees_input_files": False,
            "answer_to_artifacts": notes,
        },
        "thinking": "未显式控制（模型默认档）——记 unknown",
        "usage": usage,
        "started": started,
        "finished": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    (run_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    checker = subprocess.run(
        [sys.executable, str(case_dir / "checker.py"), str(run_dir), "--json"],
        capture_output=True, text=True, timeout=300,
    )
    results = None
    try:
        results = json.loads(checker.stdout)
    except json.JSONDecodeError:
        (run_dir / "checker-stderr.txt").write_text(checker.stderr[-2000:], encoding="utf-8")
    if results:
        (run_dir / "RESULTS_JSON" / "result.json").parent.mkdir(parents=True, exist_ok=True)
        (run_dir / "RESULTS_JSON").mkdir(exist_ok=True)
        (run_dir / "RESULTS_JSON" / "result.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return {
        "case": slug,
        "run_id": run_dir.name,
        "reward": (results or {}).get("reward"),
        "weighted": (results or {}).get("weighted"),
        "failed": (results or {}).get("failed"),
        "usage": usage,
        "exit": checker.returncode,
    }


def main() -> None:
    key = os_env = __import__("os").environ.get("DEEPSEEK_API_KEY", "")
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default=None)
    args = parser.parse_args()
    if not key:
        print("缺少 DEEPSEEK_API_KEY 环境变量", file=sys.stderr)
        sys.exit(2)
    todo = [c for c in CASES if not args.only or c["slug"] == args.only]
    rows = []
    for case in todo:
        print(f"== run {case['slug']} ==", flush=True)
        try:
            rows.append(run_case(case, key))
        except Exception as exc:
            rows.append({"case": case["slug"], "error": str(exc)[:300]})
        print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
    (HERE / "batch-results.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("\n=== 汇总 ===")
    for r in rows:
        print(r.get("case"), "reward=", r.get("reward"), "weighted=", r.get("weighted"),
              "failed=", r.get("failed"), r.get("error", ""))


if __name__ == "__main__":
    main()
