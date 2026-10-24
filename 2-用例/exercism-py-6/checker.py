#!/usr/bin/env python3
"""exercism-py-6 判分器（Exercism Python 赛道 6 题连做）。

判分逻辑
--------
1. 三重守卫：
   ① truth.json 里的 input/test SHA-256 与实际 inputs/、tests/ 不符 → ERROR（退出码 2）；
   ② 运行目录里附带的官方测试文件缺失或被改动 → input_integrity fail，reward 直接 0；
   ③ truth.json 与 checker 常量（题目列表/达标线/超时/二值）不一致 → ERROR（退出码 2）。
2. 仅在临时副本用 `tests/<ex>_test.py` 还原官方测试，不写回运行目录。
3. 逐题用 `-I -S -B trusted_runner.py`（超时 120s），要求正常返回且完成回执、
   canonical 全量测试身份与计数及成功回调均一致；仅返回码 0 不足以通过。
   此机制非任意敌意代码沙箱，仍需外层 OS 隔离来保护判卷主机。
4. 6 题中通过数 ≥ 5 → reward=1；weighted = 通过数 / 6 × 100。

来源与许可
----------
题目骨架与官方测试来自 Aider polyglot-benchmark（https://github.com/Aider-AI/polyglot-benchmark，
packaging: MIT），上游为 Exercism Python track（https://github.com/exercism/python，
MIT License），读取日期 2026-10-22；官方测试文件原样保留、未改写。
本判分器与参考解为本题库新写代码，仅使用 Python 标准库。

用法
----
    python3 checker.py <run_dir> [--json]   # 正式判分：最后一行是结果 JSON
    python3 checker.py --selftest           # 自测：nop/oracle/负例/守卫，全过退出 0，否则 2
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUTS_DIR = HERE / "inputs"
TESTS_DIR = HERE / "tests"
TRUTH_PATH = HERE / "truth.json"
SOLUTION_DIR = HERE / "solution"

CASE_ID = "exercism-py-6"
CHECKER_VERSION = "1.1"
EXPECTED_TEST_COUNTS = {"forth": 54, "poker": 37, "dominoes": 13, "bowling": 31, "zipper": 14, "pov": 15}
BINARY = True
EXERCISES = ("forth", "poker", "dominoes", "bowling", "zipper", "pov")
PASS_THRESHOLD = 5  # 通过题数达标线：≥5/6 → reward=1
TIMEOUT_S = 120

TRIVIAL_TEST = """import unittest


class PlaceholderTest(unittest.TestCase):
    def test_placeholder(self):
        self.assertTrue(True)
"""

BROKEN_BOWLING = """class BowlingGame:
    def __init__(self):
        self.total = 0

    def roll(self, pins):
        self.total += pins

    def score(self):
        return 0
"""


# --------------------------------------------------------------------------- #
# 基础工具
# --------------------------------------------------------------------------- #
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_truth() -> dict:
    return json.loads(TRUTH_PATH.read_text(encoding="utf-8"))


def canonical_problems(meta: dict) -> list:
    """守卫 ①③：inputs/tests 与 truth 一致、truth 与 checker 常量一致。"""
    problems = []
    expected_inputs = meta.get("input_sha256") or {}
    if not expected_inputs:
        problems.append("truth.json 缺少 input_sha256")
    for rel, digest in sorted(expected_inputs.items()):
        path = INPUTS_DIR / rel
        if not path.is_file():
            problems.append("缺少输入文件 inputs/{}".format(rel))
        elif sha256_file(path) != digest:
            problems.append("输入文件与 truth 不一致 inputs/{}".format(rel))
    expected_tests = meta.get("test_sha256") or {}
    for ex in EXERCISES:
        path = TESTS_DIR / "{}_test.py".format(ex)
        if not path.is_file():
            problems.append("缺少官方测试 tests/{}_test.py".format(ex))
        elif expected_tests.get(path.name) != sha256_file(path):
            problems.append("官方测试与 truth 不一致 tests/{}".format(path.name))
    if meta.get("case_id") != CASE_ID:
        problems.append("truth.case_id 与 checker 常量不一致")
    if meta.get("exercises") != list(EXERCISES):
        problems.append("truth.exercises 与 checker 常量不一致")
    if meta.get("reward_threshold") != PASS_THRESHOLD:
        problems.append("truth.reward_threshold 与 checker 常量不一致")
    if meta.get("timeout_s") != TIMEOUT_S:
        problems.append("truth.timeout_s 与 checker 常量不一致")
    if meta.get("binary") is not True:
        problems.append("truth.binary 应为 true")
    if meta.get("checker_version") != CHECKER_VERSION:
        problems.append("truth.checker_version 与 checker 常量不一致")
    if meta.get("expected_test_counts") != EXPECTED_TEST_COUNTS:
        problems.append("truth.expected_test_counts 与 checker 常量不一致")
    return problems


def check_run_inputs(run_dir: Path, meta: dict):
    """守卫 ②：运行目录附带的官方测试必须原样（骨架允许被改；缺整个 inputs/ 视为未核验）。"""
    exercise_root = run_dir / "inputs" / "exercises"
    if not exercise_root.is_dir():
        return False, []
    problems = []
    expected = meta.get("input_sha256") or {}
    for ex in EXERCISES:
        rel = "exercises/{}/{}_test.py".format(ex, ex)
        path = run_dir / "inputs" / rel
        if not path.is_file():
            problems.append("inputs/{} 缺失".format(rel))
        elif expected.get(rel) and sha256_file(path) != expected[rel]:
            problems.append("inputs/{} 被改动".format(rel))
    return True, problems


def expected_test_ids(ex: str) -> list:
    """Read canonical test identities without importing candidate code."""
    tree = ast.parse((TESTS_DIR / (ex + "_test.py")).read_text(encoding="utf-8"))
    return sorted(ex + "_test." + cls.name + "." + fn.name
                  for cls in tree.body if isinstance(cls, ast.ClassDef)
                  for fn in cls.body if isinstance(fn, ast.FunctionDef) and fn.name.startswith("test_"))


def run_unittest(exdir: Path):
    """Run checker-owned accounting in an isolated interpreter, on a temporary copy.

    Completion evidence rejects ordinary early exits, forged console summaries,
    empty suites, skips and missing test callbacks. This is NOT an OS sandbox:
    arbitrary same-process/same-UID malicious Python can still tamper or escape.
    """
    ex = exdir.name
    expected_ids = expected_test_ids(ex)
    evidence = {"complete": False, "expected": EXPECTED_TEST_COUNTS[ex], "tests_run": 0}
    env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}
    with tempfile.TemporaryDirectory(prefix="exercism-grade-") as td:
        work = Path(td) / ex
        try:
            shutil.copytree(exdir, work, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            shutil.copy2(TESTS_DIR / (ex + "_test.py"), work / (ex + "_test.py"))
            receipt = Path(td) / "completion.json"
            proc = subprocess.run(
                [sys.executable, "-I", "-S", "-B", str(HERE / "trusted_runner.py"), str(work), str(receipt)],
                cwd=str(work), capture_output=True, text=True, timeout=TIMEOUT_S, env=env,
            )
            if not receipt.is_file() or receipt.stat().st_size > 1_000_000:
                return False, "缺少可信完成回执 exit={}".format(proc.returncode), evidence
            data = json.loads(receipt.read_text(encoding="utf-8"))
            count = EXPECTED_TEST_COUNTS[ex]
            ok = (proc.returncode == 0 and isinstance(data, dict)
                  and data.get("protocol") == "exercism-completion-v1" and data.get("complete") is True
                  and len(expected_ids) == count
                  and data.get("discovered") == count and data.get("tests_run") == count
                  and all(sorted(data.get(key, [])) == expected_ids
                          for key in ("started_ids", "stopped_ids", "success_ids"))
                  and all(data.get(key) == 0 for key in
                          ("failures", "errors", "skipped", "expected_failures", "unexpected_successes")))
            evidence.update({key: data.get(key) for key in
                             ("complete", "discovered", "tests_run", "failures", "errors", "skipped")})
            evidence.update({"started": len(data.get("started_ids", [])),
                             "stopped": len(data.get("stopped_ids", [])),
                             "succeeded": len(data.get("success_ids", [])),
                             "identities_match": all(sorted(data.get(key, [])) == expected_ids
                                                     for key in ("started_ids", "stopped_ids", "success_ids"))})
            return ok, "完成回执 tests={}/{} exit={}".format(data.get("tests_run"), count, proc.returncode), evidence
        except subprocess.TimeoutExpired:
            return False, "timeout {}s".format(TIMEOUT_S), evidence
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            return False, "测试/回执失败: {}".format(exc)[:200], evidence


# --------------------------------------------------------------------------- #
# 正式判分
# --------------------------------------------------------------------------- #
def grade(run_dir: Path, meta: dict) -> dict:
    checks = []

    applicable, integrity_problems = check_run_inputs(run_dir, meta)
    if not applicable:
        checks.append(
            {"id": "input_integrity", "pass": True, "note": "运行目录未附输入副本，未核验"}
        )
    elif integrity_problems:
        checks.append(
            {
                "id": "input_integrity",
                "pass": False,
                "note": "; ".join(integrity_problems)[:300],
            }
        )
    else:
        checks.append(
            {
                "id": "input_integrity",
                "pass": True,
                "note": "运行目录内官方测试文件与 canonical 一致",
            }
        )

    passed = 0
    for ex in EXERCISES:
        exdir = run_dir / "inputs" / "exercises" / ex
        target = exdir / "{}.py".format(ex)
        if not target.is_file():
            checks.append(
                {
                    "id": ex,
                    "pass": False,
                    "note": "缺少 inputs/exercises/{}/{}.py".format(ex, ex),
                }
            )
            continue
        ok, note, completion = run_unittest(exdir)
        passed += int(ok)
        checks.append({"id": ex, "pass": ok, "note": note, "completion": completion})

    weighted = round(passed * 100.0 / len(EXERCISES), 2)
    reward = 1 if (passed >= PASS_THRESHOLD and not integrity_problems) else 0
    return {
        "case": CASE_ID,
        "checker_version": CHECKER_VERSION,
        "reward": reward,
        "weighted": weighted,
        "checks": checks,
    }


# --------------------------------------------------------------------------- #
# 自测（nop / oracle / ≥6 组负例 / 达标线边界 / truth 漂移守卫）
# --------------------------------------------------------------------------- #
def _copy_solution(run_dir: Path, ex: str) -> None:
    source = SOLUTION_DIR / ex / "{}.py".format(ex)
    target = run_dir / "inputs" / "exercises" / ex / "{}.py".format(ex)
    shutil.copy2(source, target)


def _assert_checks(result: dict, ex_expectation: dict) -> list:
    """负例精检：确认失败原因就是预期那一项，而不是碰巧全红。"""
    problems = []
    by_id = {check["id"]: check for check in result["checks"]}
    for key, want in ex_expectation.items():
        got = by_id.get(key, {}).get("pass")
        if got != want:
            problems.append("{} 期望 pass={} 实际 {}".format(key, want, got))
    return problems


def selftest() -> int:
    try:
        meta = load_truth()
    except (OSError, ValueError) as exc:
        print("SELFTEST FAIL: truth.json 读取失败: {}".format(exc))
        return 2
    problems = canonical_problems(meta)
    if problems:
        print("SELFTEST FAIL: 用例自身不一致: " + "; ".join(problems))
        return 2

    rows = []  # (name, expected_reward, result, extra_problems)

    with tempfile.TemporaryDirectory(prefix="exercism-py-6-selftest-") as tmp:
        root = Path(tmp)

        def fresh(name: str, with_inputs: bool = True) -> Path:
            run_dir = root / name
            if with_inputs:
                shutil.copytree(INPUTS_DIR, run_dir / "inputs")
            else:
                run_dir.mkdir(parents=True)
            return run_dir

        def run_case(name, expected_reward, run_dir, expectation=None, expect_weighted=None):
            result = grade(run_dir, meta)
            extra = []
            if result["reward"] != expected_reward:
                extra.append(
                    "reward 期望 {} 实际 {}".format(expected_reward, result["reward"])
                )
            if expectation:
                extra.extend(_assert_checks(result, expectation))
            if expect_weighted is not None and result.get("weighted") != expect_weighted:
                extra.append(
                    "weighted 期望 {} 实际 {}".format(expect_weighted, result.get("weighted"))
                )
            rows.append((name, expected_reward, result, extra))
            return result

        # 1. nop：空运行目录 → reward 0
        run_case("nop", 0, fresh("nop", with_inputs=False))

        # 2. oracle：6 份参考解 → reward 1, weighted 100
        oracle_dir = fresh("oracle")
        for ex in EXERCISES:
            _copy_solution(oracle_dir, ex)
        run_case(
            "oracle",
            1,
            oracle_dir,
            expectation={ex: True for ex in EXERCISES},
            expect_weighted=100.0,
        )

        # 3. 负例①骨架未实现（原样交付）→ 0
        run_case(
            "neg-skeleton",
            0,
            fresh("neg-skeleton"),
            expectation={ex: False for ex in EXERCISES},
            expect_weighted=0.0,
        )

        # 4. 负例②只过一半（3/6）→ 0, weighted 50
        half_dir = fresh("neg-half")
        for ex in ("bowling", "zipper", "pov"):
            _copy_solution(half_dir, ex)
        run_case(
            "neg-half",
            0,
            half_dir,
            expectation={"forth": False, "poker": False, "dominoes": False,
                         "bowling": True, "zipper": True, "pov": True},
            expect_weighted=50.0,
        )

        # 5. 负例③改测试文件（换成必过测试 + 骨架未实现）→ 还原后仍 0，且 integrity fail
        modified_tests = fresh("neg-modified-tests")
        for ex in EXERCISES:
            path = modified_tests / "inputs" / "exercises" / ex / "{}_test.py".format(ex)
            path.write_text(TRIVIAL_TEST, encoding="utf-8")
        run_case(
            "neg-modified-tests",
            0,
            modified_tests,
            expectation={"input_integrity": False, "forth": False},
            expect_weighted=0.0,
        )

        # 6. 负例④删除测试 + 6 份解 → 还原后题目全过，但 integrity 守卫必须把 reward 压回 0
        deleted_tests = fresh("neg-deleted-tests")
        for ex in EXERCISES:
            (deleted_tests / "inputs" / "exercises" / ex / "{}_test.py".format(ex)).unlink()
            _copy_solution(deleted_tests, ex)
        deleted_result = run_case(
            "neg-deleted-tests", 0, deleted_tests, expectation={"input_integrity": False}
        )
        if not all(
            check["pass"]
            for check in deleted_result["checks"]
            if check["id"] in EXERCISES
        ):
            rows[-1][3].append("删除测试负例应只由 integrity 拦下（题目本身应全过）")
        if deleted_result.get("weighted") != 100.0:
            rows[-1][3].append(
                "删除测试负例 weighted 期望 100.0（题目全过）实际 {}".format(
                    deleted_result.get("weighted")
                )
            )

        # 7. 负例⑤语法错误（6 份解都追加非法语句）→ 0
        syntax_dir = fresh("neg-syntax-error")
        for ex in EXERCISES:
            _copy_solution(syntax_dir, ex)
            with (syntax_dir / "inputs" / "exercises" / ex / "{}.py".format(ex)).open(
                "a", encoding="utf-8"
            ) as handle:
                handle.write("\nthis is not valid python\n")
        run_case(
            "neg-syntax-error",
            0,
            syntax_dir,
            expectation={ex: False for ex in EXERCISES},
            expect_weighted=0.0,
        )

        # 8. 负例⑥只写了 5 题（其中 1 份有缺陷 + 1 题未动）→ 4/6 < 达标线 → 0
        only_five = fresh("neg-only-five")
        for ex in ("forth", "poker", "dominoes", "zipper"):
            _copy_solution(only_five, ex)
        (only_five / "inputs" / "exercises" / "bowling" / "bowling.py").write_text(
            BROKEN_BOWLING, encoding="utf-8"
        )
        run_case(
            "neg-only-five",
            0,
            only_five,
            expectation={"forth": True, "poker": True, "dominoes": True,
                         "zipper": True, "bowling": False, "pov": False},
        )

        # 9. 达标线边界：5/6 通过 → reward=1, weighted 83.33（验证阈值口径）
        boundary = fresh("boundary-five-pass")
        for ex in EXERCISES[:-1]:  # 留下 pov 骨架
            _copy_solution(boundary, ex)
        boundary_expectation = {ex: True for ex in EXERCISES[:-1]}
        boundary_expectation["pov"] = False
        run_case(
            "boundary-five-pass",
            1,
            boundary,
            expectation=boundary_expectation,
            expect_weighted=83.33,
        )

        # Precise completion negatives: intact official tests, no legitimate tests run.
        for label, payload in (
            ("neg-os-exit-zero", "import os;os._exit(0)\n"),
            ("neg-sys-exit-zero", "import sys;sys.exit(0)\n"),
            ("neg-fake-summary", 'import os,sys;sys.stderr.write("Ran 54 tests\\nOK\\n");sys.stderr.flush();os._exit(0)\n'),
            ("neg-empty-suite", "import unittest;unittest.TestLoader.getTestCaseNames=lambda *a: []\n"),
            ("neg-no-callbacks", "import unittest;unittest.TestCase.run=lambda *a: None\n"),
            ("neg-skip-all", "import unittest;unittest.TestCase.__unittest_skip__=True\n"),
        ):
            run = fresh(label)
            for ex in EXERCISES:
                prefix = ((SOLUTION_DIR / ex / (ex + ".py")).read_text(encoding="utf-8") + "\n"
                          if label in ("neg-empty-suite", "neg-no-callbacks", "neg-skip-all") else "")
                (run / "inputs" / "exercises" / ex / (ex + ".py")).write_text(prefix + payload, encoding="utf-8")
            run_case(label, 0, run, expectation={"input_integrity": True, **{ex: False for ex in EXERCISES}}, expect_weighted=0.0)

        # 10. 守卫：truth 与输入漂移 → ERROR 退出码 2
        case_copy = root / "casecopy"
        shutil.copytree(
            HERE,
            case_copy,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "selftest.stdout.txt"),
        )
        tampered_input = case_copy / "inputs" / "exercises" / "forth" / "forth_test.py"
        tampered_input.write_text(
            tampered_input.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8"
        )
        guard_run = root / "guard-run"
        shutil.copytree(INPUTS_DIR, guard_run / "inputs")
        guard_extra = []
        try:
            proc = subprocess.run(
                [sys.executable, str(case_copy / "checker.py"), str(guard_run), "--json"],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_S,
            )
            if proc.returncode != 2:
                guard_extra.append("退出码期望 2 实际 {}".format(proc.returncode))
        except (subprocess.TimeoutExpired, OSError) as exc:
            guard_extra.append("守卫子进程异常: {}".format(exc))
        rows.append(
            ("guard-truth-mismatch", 2, {"reward": "ERROR", "weighted": None, "checks": []},
             guard_extra)
        )

    failed = 0
    for name, expected_reward, result, extra_problems in rows:
        ok = not extra_problems
        failed += 0 if ok else 1
        print(
            "{status}  {name:<24s} expected={expect} reward={got} weighted={weighted}".format(
                status="PASS" if ok else "FAIL",
                name=name,
                expect=expected_reward,
                got=result.get("reward"),
                weighted=result.get("weighted"),
            )
        )
        for problem in extra_problems:
            print("      - " + problem)
    total = len(rows)
    if failed:
        print("SELFTEST FAIL: {}/{} 通过（nop/oracle/负例/边界/守卫 见上）".format(total - failed, total))
        return 2
    print(
        "SELFTEST PASS: {}/{} 全部 PASS "
        "(nop=0, oracle=1, 原有及完成计数负例全 0, 边界 5/6→1, 守卫 exit=2)".format(total, total)
    )
    return 0


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="exercism-py-6 checker")
    parser.add_argument("run_dir", nargs="?", help="运行目录")
    parser.add_argument("--json", action="store_true", help="只输出一行结果 JSON")
    parser.add_argument("--selftest", action="store_true", help="自测（nop/oracle/负例/守卫）")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    if not args.run_dir:
        print(json.dumps({"case": CASE_ID, "error": "缺少 run_dir 参数"}, ensure_ascii=False))
        return 2

    try:
        meta = load_truth()
    except (OSError, ValueError) as exc:
        print(json.dumps({"case": CASE_ID, "error": "truth.json 读取失败: {}".format(exc)},
                         ensure_ascii=False))
        return 2

    problems = canonical_problems(meta)
    if problems:
        print(
            json.dumps(
                {"case": CASE_ID, "error": "用例自身不一致: " + "; ".join(problems)},
                ensure_ascii=False,
            )
        )
        return 2

    run_dir = Path(args.run_dir).resolve()
    result = grade(run_dir, meta)
    if not args.json:
        for check in result["checks"]:
            print(
                "[{}] {}: {}".format("PASS" if check["pass"] else "FAIL", check["id"],
                                     check["note"])
            )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())