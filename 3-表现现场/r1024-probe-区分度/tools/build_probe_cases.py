#!/usr/bin/env python3
"""生成区分度探针用例（从 scout 拉下来的原始基准数据 → 五件套最小版）。

数据来源（2026-10-22 scout 实拉，见 5-学习笔记/题库调研-2026-10-22-区分度/）：
- DABstep dev 10：HF adyen/DABstep，CC-BY-4.0，官方 scorer 由 scout 取到 /tmp/tb-probe/dabstep_grader/scorer.py
- BIRD mini_dev 切片：HF birdsql/bird_mini_dev（CC BY-SA 4.0），库 birdsql/bird-critic-1.0-sqlite
- Aider polyglot Python：github Aider-AI/polyglot-benchmark（Exercism 题，MIT/attribution）

用法：python3 tools/build_probe_cases.py
产物：cases/<name>/{prompt.md,case.json,checker.py,truth.json,inputs/}
"""
from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
BATCH = HERE.parent
CASES = BATCH / "cases"
SRC = Path("/tmp/tb-probe")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def case_meta(case: str, inputs, timeout_s: int = 1800) -> None:
    write(
        CASES / case / "case.json",
        json.dumps({"inputs": inputs, "timeout_s": timeout_s}, ensure_ascii=False, indent=2) + "\n",
    )


# ---------------------------------------------------------------- DABstep
def build_dabstep() -> None:
    case = "dabstep-dev10"
    cdir = CASES / case
    if cdir.exists():
        shutil.rmtree(cdir)
    src = SRC / "dabstep"
    ctx = ["payments.csv", "fees.json", "manual.md", "merchant_data.json",
           "merchant_category_codes.csv", "acquirer_countries.csv"]
    (cdir / "inputs").mkdir(parents=True, exist_ok=True)
    for name in ctx:
        shutil.copy2(src / name, cdir / "inputs" / name)
    shutil.copy2(SRC / "dabstep_grader" / "scorer.py", cdir / "scorer.py")

    rows = [json.loads(line) for line in (src / "dev.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    write(
        cdir / "inputs" / "questions.jsonl",
        "\n".join(json.dumps({k: r[k] for k in ("task_id", "question", "guidelines")}, ensure_ascii=False) for r in rows) + "\n",
    )
    truth = {r["task_id"]: r["answer"] for r in rows}
    write(cdir / "truth.json", json.dumps({"source": "DABstep dev (CC-BY-4.0) https://huggingface.co/datasets/adyen/DABstep",
                                           "threshold": 0.8, "answers": truth}, ensure_ascii=False, indent=2) + "\n")

    write(cdir / "prompt.md", """# dabstep-dev10：支付数据分析问答（DABstep dev 子集）

## 任务

`inputs/` 下是一份真实支付业务数据湖（Adyen 公开的 DABstep 数据）：

| 文件 | 内容 |
|---|---|
| `inputs/payments.csv` | 逐笔交易流水（约 23.5 MB，含时间、金额、币种、发卡国、IP 国、收单国、商户、设备、欺诈标记等列） |
| `inputs/fees.json` | 费率表（按支付方式/卡组织/档位） |
| `inputs/manual.md` | 业务手册（费率公式、口径定义，**做题必须读**） |
| `inputs/merchant_data.json` | 商户资料 |
| `inputs/merchant_category_codes.csv` | 商户类别码表 |
| `inputs/acquirer_countries.csv` | 收单国表 |

`inputs/questions.jsonl` 有 **10 道题**，每行一个 JSON：`task_id` / `question` / `guidelines`（该题的答案格式要求）。

## 产物

在当前运行目录写 `answers.jsonl`，**每行一个 JSON**，恰好 10 行，每题一行：

```json
{"task_id": "5", "answer": "NL"}
```

- `task_id` 必须是字符串，与题目一一对应，不允许多、少或重复；
- `answer` 严格按该题 `guidelines` 的要求书写（格式、单位、小数位、选项字母都要对；信息不足时按 guidelines 给 `Not Applicable`）；
- 只输出答案值本身，不要解释。

## 环境

- 当前目录即可读写；`inputs/` 不要修改。
- 可用 `python3`（3.9，标准库）自行统计；不联网。
- 建议先读 `inputs/manual.md` 再动手，多道题的口径（费率、欺诈率、top-N 的分母）都在里面。

完成后结束，不需要额外解释。
""")
    case_meta(case, [["inputs", "inputs"]])

    write(cdir / "checker.py", '''#!/usr/bin/env python3
"""dabstep-dev10 判分器：官方 DABstep scorer 逐题二值，通过率 ≥ 0.8 记 headline=1。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from scorer import question_scorer  # noqa: E402  官方 scorer（CC-BY-4.0）

BINARY = True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    run_dir = Path(args.run_dir).resolve()
    truth = json.loads((HERE / "truth.json").read_text(encoding="utf-8"))
    gold = truth["answers"]
    threshold = truth["threshold"]

    checks, got = [], {}
    path = run_dir / "answers.jsonl"
    if not path.exists():
        checks.append({"id": "answers_jsonl", "pass": False, "note": "answers.jsonl 缺失"})
        acc = 0.0
    else:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict) and "task_id" in obj:
                got[str(obj["task_id"])] = str(obj.get("answer", ""))
        checks.append({"id": "answers_jsonl", "pass": len(got) == len(gold),
                       "note": f"{len(got)}/{len(gold)} 行可解析"})
        ok = 0
        for tid, want in gold.items():
            pred = got.get(tid, "")
            hit = bool(pred) and question_scorer(pred, want)
            ok += int(hit)
            checks.append({"id": f"q{tid}", "pass": hit, "got": pred[:80], "want": want[:80]})
        acc = ok / len(gold)

    reward = 1 if acc >= threshold else 0
    out = {"case": "dabstep-dev10", "reward": reward, "weighted": round(acc * 100, 2),
           "accuracy": round(acc, 4), "threshold": threshold, "checks": checks}
    if args.json:
        print(json.dumps(out, ensure_ascii=False))
    else:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''')


# ---------------------------------------------------------------- BIRD
def build_bird() -> None:
    case = "bird-schools15"
    cdir = CASES / case
    if cdir.exists():
        shutil.rmtree(cdir)
    rows = [r for r in json.loads((SRC / "bird" / "mini_dev.json").read_text(encoding="utf-8"))
            if r["db_id"] == "california_schools"]
    by_diff = {"challenging": [], "moderate": [], "simple": []}
    for r in rows:
        by_diff[r["difficulty"]].append(r)
    picked = by_diff["challenging"] + by_diff["moderate"][:7] + by_diff["simple"][:3]
    assert len(picked) == 15, len(picked)

    db_src = SRC / "bird" / "db" / "california_schools.sqlite"
    (cdir / "inputs" / "db").mkdir(parents=True, exist_ok=True)
    shutil.copy2(db_src, cdir / "inputs" / "db" / "california_schools.sqlite")

    con = sqlite3.connect(db_src)
    tables = [t[0] for t in con.execute("select name from sqlite_master where type='table'")]
    schema = "\n\n".join(con.execute("select sql from sqlite_master where type='table' and name=?", (t,)).fetchone()[0] for t in tables)
    write(cdir / "inputs" / "schema.sql", schema + "\n")
    samples = {}
    for t in tables:
        cur = con.execute(f'select * from "{t}" limit 3')
        cols = [d[0] for d in cur.description]
        samples[t] = {"columns": cols, "rows": [[str(v) for v in row] for row in cur.fetchall()]}
    write(cdir / "inputs" / "sample_rows.json", json.dumps(samples, ensure_ascii=False, indent=2) + "\n")
    con.close()

    write(cdir / "inputs" / "questions.json",
          json.dumps([{"question_id": r["question_id"], "question": r["question"],
                       "evidence": r.get("evidence", ""), "difficulty": r["difficulty"]} for r in picked],
                     ensure_ascii=False, indent=2) + "\n")
    truth = {str(r["question_id"]): {"sql": r["SQL"], "difficulty": r["difficulty"]} for r in picked}
    write(cdir / "truth.json", json.dumps({"source": "BIRD mini_dev california_schools (CC BY-SA 4.0) https://bird-bench.github.io/",
                                           "threshold": 0.8, "db": "inputs/db/california_schools.sqlite", "answers": truth},
                                          ensure_ascii=False, indent=2) + "\n")

    write(cdir / "prompt.md", """# bird-schools15：Text-to-SQL（BIRD mini_dev 切片）

## 任务

`inputs/` 给了一个 SQLite 数据库切片（加州学校数据，`california_schools`）与 15 道自然语言问题：

| 文件 | 内容 |
|---|---|
| `inputs/db/california_schools.sqlite` | 三张表 `frpm` / `satscores` / `schools` 的完整 SQLite 库（约 11 MB） |
| `inputs/schema.sql` | 建表语句（列名、类型） |
| `inputs/sample_rows.json` | 每张表前 3 行样例（列名 + 值），便于不便连库时判读字段 |
| `inputs/questions.json` | 15 道题：`question_id` / `question` / `evidence`（官方口径提示）/ `difficulty` |

## 产物

在当前运行目录写 `answers.jsonl`，**每行一个 JSON**，恰好 15 行：

```json
{"question_id": 1471, "sql": "SELECT ... FROM ..."}
```

- `sql` 必须是能在该库上直接执行的单条 SQLite 查询（不要包含分号结尾之外的多语句、不要建表/改数据）；
- 列名、聚合口径、过滤条件按题面与 `evidence` 的要求写；返回列的顺序不敏感，但**返回的列集合与行内容要正确**；
- 允许你先在 `inputs/db/...` 上跑 SQL 自测，但**不要修改** `inputs/` 下任何文件。

## 环境

- 可用 `python3`（3.9，标准库含 `sqlite3`）；不联网。
- 也可以只用题面 + `schema.sql` + `sample_rows.json` 直接写 SQL，不必真的连库。

完成后结束，不需要额外解释。
""")
    case_meta(case, [["inputs", "inputs"]])

    write(cdir / "checker.py", '''#!/usr/bin/env python3
"""bird-schools15 判分器：逐题执行 gold SQL 与 pred SQL，结果集比对（exec-accuracy），通过率 ≥ 0.8 记 headline=1。"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BINARY = True


def normalize(rows):
    """把结果集归一成可比较的多重集：数字保留 6 位、None 记常量、行内保列序。"""
    out = []
    for row in rows:
        cells = []
        for v in row:
            if v is None:
                cells.append("<NULL>")
            elif isinstance(v, (int, float)):
                cells.append(f"{float(v):.6f}" if isinstance(v, float) else str(v))
            else:
                cells.append(str(v).strip())
        out.append(tuple(cells))
    return sorted(out)


def run_sql(db: Path, sql: str):
    con = sqlite3.connect(str(db))
    try:
        cur = con.execute(sql)
        return normalize(cur.fetchall()), [d[0] for d in cur.description or []]
    finally:
        con.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    run_dir = Path(args.run_dir).resolve()

    truth = json.loads((HERE / "truth.json").read_text(encoding="utf-8"))
    db = HERE / truth["db"]
    threshold = truth["threshold"]

    got = {}
    path = run_dir / "answers.jsonl"
    checks = []
    if not path.exists():
        checks.append({"id": "answers_jsonl", "pass": False, "note": "answers.jsonl 缺失"})
    else:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                got[str(obj["question_id"])] = str(obj.get("sql", ""))
            except Exception:
                continue
        checks.append({"id": "answers_jsonl", "pass": len(got) == len(truth["answers"]),
                       "note": f"{len(got)}/{len(truth['answers'])} 行可解析"})

    ok = 0
    for qid, meta in truth["answers"].items():
        pred = got.get(qid, "")
        hit, note = False, ""
        if pred:
            try:
                gold_rows, _ = run_sql(db, meta["sql"])
            except Exception as exc:  # gold 本身应可执行，出错即用例缺陷
                note = f"gold SQL error: {exc}"
                checks.append({"id": f"q{qid}", "pass": False, "note": note})
                continue
            try:
                pred_rows, _ = run_sql(db, pred)
                hit = pred_rows == gold_rows
                note = f"rows {len(pred_rows)} vs {len(gold_rows)}"
            except Exception as exc:
                note = f"sql error: {exc}"
        checks.append({"id": f"q{qid}", "pass": hit, "note": note, "difficulty": meta["difficulty"]})
        ok += int(hit)

    acc = ok / len(truth["answers"])
    reward = 1 if acc >= threshold else 0
    out = {"case": "bird-schools15", "reward": reward, "weighted": round(acc * 100, 2),
           "accuracy": round(acc, 4), "threshold": threshold, "checks": checks}
    print(json.dumps(out, ensure_ascii=False) if args.json else json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''')


# ---------------------------------------------------------------- polyglot
POLY = ["forth", "poker", "dominoes"]


def build_polyglot() -> None:
    case = "polyglot-py3"
    cdir = CASES / case
    if cdir.exists():
        shutil.rmtree(cdir)
    src = SRC / "polyglot-benchmark" / "python" / "exercises" / "practice"
    (cdir / "inputs" / "exercises").mkdir(parents=True, exist_ok=True)
    (cdir / "tests").mkdir(parents=True, exist_ok=True)
    for ex in POLY:
        shutil.copytree(src / ex, cdir / "inputs" / "exercises" / ex)
        shutil.copy2(src / ex / f"{ex}_test.py", cdir / "tests" / f"{ex}_test.py")
    write(cdir / "inputs" / "README.md", """# 三个练习题（Exercism Python 赛道）

`exercises/<name>/` 目录内各有：

- `<name>.py` —— 待实现的骨架（函数签名已给，函数体是 `pass`）；
- `<name>_test.py` —— 官方验收测试（**规格以测试为准**，请逐条读测试反推行为）。

请只实现 `<name>.py`；测试文件会在判分前被还原成原版，改测试没有用。
""")
    write(cdir / "prompt.md", """# polyglot-py3：三题连做（Exercism Python 赛道，测试驱动）

## 任务

`inputs/exercises/` 下有 3 个 Python 练习题，每题一个目录：

1. `forth/` —— 小型 Forth 解释器（数字、算术、栈操作、自定义词定义与调用、错误处理）
2. `poker/` —— 扑克牌型比较（同花顺/四条/葫芦/同花/顺子/三条/两对/一对/高牌，含平票规则）
3. `dominoes/` —— 多米诺骨牌链成环（把一组骨牌拼成能闭合的链）

每个目录里：`<name>.py` 是函数体为 `pass` 的骨架，`<name>_test.py` 是官方验收测试。
**规格以测试为准**：请读测试用例（含错误类型与错误消息）反推并实现。

## 产物

直接在本目录改代码：把 `inputs/exercises/<name>/<name>.py` 实现完（允许在同目录新增辅助模块，但不要动测试文件）。
判分前会把 3 个测试文件还原成官方原版，并在各目录内运行 `python3 -m unittest -q <name>_test.py`。

## 环境

- 可用 `python3`（3.9，标准库）；不联网。
- 你可以随时自己跑测试验证：`cd inputs/exercises/<name> && python3 -m unittest -q <name>_test.py`。

三题全部测试通过才算达标（reward=1）。完成后结束，不需要额外解释。
""")
    case_meta(case, [["inputs", "inputs"]], timeout_s=2400)
    write(cdir / "truth.json", json.dumps({"source": "Aider polyglot benchmark / Exercism (MIT, attribution)",
                                           "exercises": POLY}, ensure_ascii=False, indent=2) + "\n")

    write(cdir / "checker.py", '''#!/usr/bin/env python3
"""polyglot-py3 判分器：还原官方测试后逐题跑 unittest；三题全绿 reward=1，weighted=通过题数比例。"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BINARY = True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    run_dir = Path(args.run_dir).resolve()
    meta = json.loads((HERE / "truth.json").read_text(encoding="utf-8"))
    checks, ok = [], 0
    for ex in meta["exercises"]:
        exdir = run_dir / "inputs" / "exercises" / ex
        if not (exdir / f"{ex}.py").exists():
            checks.append({"id": ex, "pass": False, "note": "缺少 exercise 目录或骨架文件"})
            continue
        # 还原官方测试（防改测试作弊）
        shutil.copy2(HERE / "tests" / f"{ex}_test.py", exdir / f"{ex}_test.py")
        try:
            p = subprocess.run(
                [sys.executable, "-m", "unittest", "-q", f"{ex}_test.py"],
                cwd=str(exdir), capture_output=True, text=True, timeout=300,
                env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "HOME": str(run_dir)},
            )
            passed = p.returncode == 0
            note = (p.stderr or p.stdout).strip().splitlines()[-1][:160] if (p.stderr or p.stdout) else ""
        except subprocess.TimeoutExpired:
            passed, note = False, "timeout 300s"
        except Exception as exc:  # noqa: BLE001
            passed, note = False, f"error: {exc}"
        ok += int(passed)
        checks.append({"id": ex, "pass": passed, "note": note})

    acc = ok / len(meta["exercises"])
    reward = 1 if ok == len(meta["exercises"]) else 0
    out = {"case": "polyglot-py3", "reward": reward, "weighted": round(acc * 100, 2), "checks": checks}
    print(json.dumps(out, ensure_ascii=False) if args.json else json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''')


def main() -> int:
    if not SRC.exists():
        raise SystemExit(f"缺少原始数据目录 {SRC}（scout 拉取目录），无法生成")
    CASES.mkdir(parents=True, exist_ok=True)
    build_dabstep()
    build_bird()
    build_polyglot()
    for d in sorted(CASES.iterdir()):
        if d.is_dir():
            print("built", d.name, sum(p.stat().st_size for p in d.rglob("*") if p.is_file()) // 1024, "KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())