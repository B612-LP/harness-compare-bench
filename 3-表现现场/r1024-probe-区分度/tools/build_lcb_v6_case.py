#!/usr/bin/env python3
"""生成 lcb-v6-hard4 探针用例：从官方 LiveCodeBench v6 抽 4 道近期 hard（AtCoder F/G），含 private tests。

数据：`/tmp/lcb_recent.jsonl`（由 /tmp/scan_lcb.py 从 HF livecodebench/code_generation_lite test6.jsonl 流式抽取）
       private tests = base64(zlib(pickle(json string)))
运行：PYTHONPATH=/tmp/py39 /usr/bin/python3 tools/build_lcb_v6_case.py
"""
from __future__ import annotations

import base64
import json
import pickle
import shutil
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
BATCH = HERE.parent
CASE = BATCH / "cases" / "lcb-v6-hard4"
PICK = ["abc387_f", "abc388_f", "abc388_g", "abc389_g"]


def decode_tests(raw: str) -> list:
    obj = pickle.loads(zlib.decompress(base64.b64decode(raw)))
    return json.loads(obj) if isinstance(obj, str) else obj


def main() -> int:
    rows = {}
    for line in Path("/tmp/lcb_recent.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        rows[r["id"]] = r
    missing = [p for p in PICK if p not in rows]
    if missing:
        raise SystemExit(f"缺少题：{missing}（重跑 /tmp/scan_lcb.py 增大 need）")

    if CASE.exists():
        shutil.rmtree(CASE)
    (CASE / "inputs").mkdir(parents=True)

    problems, truth = [], {}
    for pid in PICK:
        r = rows[pid]
        tests = decode_tests(r["private_encoded"])
        public = json.loads(r["public"]) if isinstance(r["public"], str) else r["public"]
        # 只保留 stdin 型（AtCoder）
        priv = [t for t in tests if t.get("testtype", "stdin") == "stdin"]
        pub = [t for t in public if t.get("testtype", "stdin") == "stdin"]
        problems.append({
            "problem_id": pid,
            "title": r["title"],
            "date": r["date"],
            "statement": r["question"],
            "n_public": len(pub),
            "n_private": len(priv),
        })
        truth[pid] = {"title": r["title"], "tests": pub + priv}
    (CASE / "inputs" / "problems.json").write_text(
        json.dumps(problems, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (CASE / "truth.json").write_text(json.dumps(
        {"source": "LiveCodeBench v6 (MIT) https://github.com/LiveCodeBench/LiveCodeBench",
         "problems": truth}, ensure_ascii=False) + "\n", encoding="utf-8")

    listing = "\n".join(
        f"{i+1}. `{p['problem_id']}` —— {p['title']}（{p['date'][:10]}；公开 {p['n_public']} 组 + 私有 {p['n_private']} 组测试）"
        for i, p in enumerate(problems))
    (CASE / "prompt.md").write_text(f"""# lcb-v6-hard4：四道近期竞赛难题（LiveCodeBench v6）

## 任务

`inputs/problems.json` 里有 4 道**近期竞赛难题**（题目原文；AtCoder 风格，读标准输入、写标准输出）：

{listing}

对每道题，在当前运行目录写一个 Python 程序：

```
solutions/<problem_id>.py
```

- 程序从 **stdin** 读输入、向 **stdout** 写输出（与题目输入输出格式严格一致）；
- 只允许 Python 标准库；不联网；
- 每题独立文件；可以在本地自己造小数据测试，但判分用题目自带公开 + 私有测试。

## 判分

每题全部测试通过才算该题通过；4 题里通过 ≥2 题记 reward=1，加权分按通过题数比例给。
只写产物文件即可，不需要解释。
""", encoding="utf-8")
    (CASE / "case.json").write_text(json.dumps(
        {"inputs": [["inputs", "inputs"]], "timeout_s": 3000}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    (CASE / "checker.py").write_text('''#!/usr/bin/env python3
"""lcb-v6-hard4 判分器：逐题跑 stdin/stdout 测试（公开+私有）；通过 ≥2 题记 reward=1。"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BINARY = True
TEST_TIMEOUT = 10


def norm(s: str) -> str:
    return "\\n".join(line.rstrip() for line in s.strip().splitlines())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    run_dir = Path(args.run_dir).resolve()
    truth = json.loads((HERE / "truth.json").read_text(encoding="utf-8"))["problems"]

    checks, passed = [], 0
    for pid, spec in truth.items():
        path = run_dir / "solutions" / f"{pid}.py"
        if not path.exists():
            checks.append({"id": pid, "pass": False, "note": f"缺少 solutions/{pid}.py"})
            continue
        ok, first_fail = 0, ""
        for i, case in enumerate(spec["tests"]):
            try:
                p = subprocess.run([sys.executable, str(path)], input=case["input"],
                                   capture_output=True, text=True, timeout=TEST_TIMEOUT)
                hit = p.returncode == 0 and norm(p.stdout) == norm(case["output"])
            except subprocess.TimeoutExpired:
                hit = False
                first_fail = f"#{i} timeout"
            except Exception as exc:  # noqa: BLE001
                hit = False
                first_fail = f"#{i} {exc}"[:80]
            if not hit and not first_fail:
                first_fail = f"#{i} wrong"
            ok += int(hit)
        allpass = ok == len(spec["tests"])
        passed += int(allpass)
        checks.append({"id": pid, "pass": allpass, "note": f"{ok}/{len(spec['tests'])}", "first_fail": first_fail})
    reward = 1 if passed >= 2 else 0
    out = {"case": "lcb-v6-hard4", "reward": reward, "weighted": round(passed / len(truth) * 100, 2),
           "problems_passed": passed, "checks": checks}
    print(json.dumps(out, ensure_ascii=False) if args.json else json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''')
    print("built", CASE.name, sum(p.stat().st_size for p in CASE.rglob("*") if p.is_file()) // 1024, "KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())