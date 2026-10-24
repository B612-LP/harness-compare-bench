#!/usr/bin/env python3
"""生成 lcb-hard3 探针用例：从 LiveCodeBench（lite 镜像 parquet）抽 3 道 LeetCode hard，官方测试逐题判分。

数据：`/tmp/lcb0.parquet`（HF `cassanof/livecodebench_lite_filtered`，来源 LiveCodeBench lite，MIT）；
      测试来自题包 `input_output`（inputs/outputs/fn_name），15 组/题。
运行：PYTHONPATH=/tmp/py39 /usr/bin/python3 tools/build_lcb_case.py
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
BATCH = HERE.parent
CASE = BATCH / "cases" / "lcb-hard3"
PICK = ["2879", "3223", "3091"]   # 题包体积小、难度 hard（LeetCode contest Q4 档）


def main() -> int:
    t = pq.read_table("/tmp/lcb0.parquet")
    d = t.to_pydict()
    rows = {str(d["id"][i]): {k: d[k][i] for k in d} for i in range(t.num_rows)}
    if CASE.exists():
        shutil.rmtree(CASE)
    (CASE / "inputs").mkdir(parents=True)

    problems, truth = [], {}
    for pid in PICK:
        r = rows[pid]
        io = json.loads(r["input_output"])
        tests = [{"input": a, "output": b} for a, b in zip(io["inputs"], io["outputs"])]
        problems.append({
            "problem_id": pid,
            "title": r["title"],
            "statement": r["question"],
            "starter_code": r["starter_code"],
            "fn_name": io["fn_name"],
            "n_tests": len(tests),
        })
        truth[pid] = {"fn_name": io["fn_name"], "tests": tests, "title": r["title"]}

    (CASE / "inputs" / "problems.json").write_text(
        json.dumps(problems, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (CASE / "truth.json").write_text(json.dumps(
        {"source": "LiveCodeBench lite (MIT) https://github.com/LiveCodeBench/LiveCodeBench",
         "problems": truth}, ensure_ascii=False) + "\n", encoding="utf-8")

    titles = "\n".join(f"{i+1}. `{p['problem_id']}` —— {p['title']}（{p['n_tests']} 组测试，入口 `Solution.{p['fn_name']}`）"
                       for i, p in enumerate(problems))
    (CASE / "prompt.md").write_text(f"""# lcb-hard3：三道 LeetCode hard 题（LiveCodeBench 题包）

## 任务

`inputs/problems.json` 里有 3 道**竞赛难度**的算法题（题目原文 + 函数签名 + 测试组数）：

{titles}

对每道题，在当前运行目录写一个 Python 文件：

```
solutions/<problem_id>.py
```

文件里必须包含与题面 `starter_code` 一致的 `class Solution`，并实现 `{'(见各题)'}` 对应的方法
（题面 `starter_code` 给了类名与方法签名；判分按 `Solution().<fn_name>(*args)` 调用）。

- 允许 import Python 标准库（`typing` 等）；**不联网**；
- 每个文件是独立模块，只放该题的解法；
- 你可以在本地用 `python3` 自己写测试验证，但最终判分用题包自带测试。

## 判分

每题 15 组测试**全过**才算该题通过；3 题里通过 ≥2 题记 reward=1，加权分按通过题数比例给。
只写产物文件即可，不需要解释。
""", encoding="utf-8")
    (CASE / "case.json").write_text(json.dumps(
        {"inputs": [["inputs", "inputs"]], "timeout_s": 2400}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    (CASE / "checker.py").write_text('''#!/usr/bin/env python3
"""lcb-hard3 判分器：逐题 import 解法、跑 15 组官方测试；通过题数 ≥2 记 reward=1。"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BINARY = True


def eq(a, b) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, float) or isinstance(b, float):
        return abs(float(a) - float(b)) <= 1e-6
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(eq(x, y) for x, y in zip(a, b))
    return a == b


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    run_dir = Path(args.run_dir).resolve()
    truth = json.loads((HERE / "truth.json").read_text(encoding="utf-8"))["problems"]

    checks, passed_problems = [], 0
    for pid, spec in truth.items():
        sol_path = run_dir / "solutions" / f"{pid}.py"
        if not sol_path.exists():
            checks.append({"id": pid, "pass": False, "note": "缺少 solutions/%s.py" % pid})
            continue
        spec_obj = importlib.util.spec_from_file_location(f"sol_{pid}", sol_path)
        mod = importlib.util.module_from_spec(spec_obj)
        try:
            spec_obj.loader.exec_module(mod)
            sol = mod.Solution()
            fn = getattr(sol, spec["fn_name"])
        except Exception as exc:  # noqa: BLE001
            checks.append({"id": pid, "pass": False, "note": f"import/入口失败: {exc}"})
            continue
        ok = 0
        notes = []
        for i, case in enumerate(spec["tests"]):
            try:
                got = fn(*case["input"])
                hit = eq(got, case["output"])
            except Exception as exc:  # noqa: BLE001
                hit = False
                notes.append(f"#{i} exc {exc}"[:120])
            ok += int(hit)
        allpass = ok == len(spec["tests"])
        passed_problems += int(allpass)
        checks.append({"id": pid, "pass": allpass, "note": f"{ok}/{len(spec['tests'])}", "detail": notes[:3]})
    reward = 1 if passed_problems >= 2 else 0
    out = {"case": "lcb-hard3", "reward": reward, "weighted": round(passed_problems / len(truth) * 100, 2),
           "problems_passed": passed_problems, "checks": checks}
    print(json.dumps(out, ensure_ascii=False) if args.json else json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''')
    total = sum(p.stat().st_size for p in CASE.rglob("*") if p.is_file())
    print("built", CASE.name, total // 1024, "KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())