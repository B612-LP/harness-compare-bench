#!/usr/bin/env python3
"""lcb-recent-hard-4 判分器 v0.1（2026-10-22）

用法：
    python3 checker.py <run_dir> [--json]
    python3 checker.py --selftest

判分对象（见 instruction.md / spec.md）：
    <run_dir>/solutions/<problem_id>.py     4 题各一个 Python 程序（stdin 读入 → stdout 写出）

判分口径：
    逐题依次运行该题的全部测试（公开样例 + 隐藏私有测试，均为 AtCoder stdin 型）：
    subprocess 以 <python> solutions/<id>.py 运行、stdin 注入测试输入、单组超时 10 秒、
    stdout 按行 rstrip 比较（忽略行尾空白与末尾空行）。
    单题「全部测试通过」才算该题通过（单题内部无部分分）；
    4 题中通过 ≥2 题 headline reward=1，weighted = 通过题数 / 4 × 100。

三重守卫：
    ① truth.json 记录的 inputs/problems.json SHA-256 / 字节数与磁盘不一致 → ERROR exit 2；
    ② run_dir 里若附了输入副本 inputs/problems.json 且被改 → reward 0（input_integrity fail）；
    ③ truth 与 checker 常量（题数 / 达标线 / 单组超时 / 各题测试数 / 测试集 SHA-256）
       任一不一致 → ERROR exit 2。

仅使用 Python 标准库；不联网、不装包；只读 run_dir 产物 + 本文件同目录的
inputs/ 与 truth.json（gold 测试只在 truth.json 内），不读 /tmp 或仓库其它路径。

判分器移植自 LiveCodeBench 官方评测逻辑（MIT，https://github.com/LiveCodeBench/LiveCodeBench）：
把「逐测试运行、stdin 注入、超时、输出规整比较」的口径简化为标准库实现；测试数据原样沿用。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

CASE_ID = "lcb-recent-hard-4"
CHECKER_VERSION = "0.1"
BINARY = True

PASS_THRESHOLD = 2          # 4 题中通过 ≥2 题记 reward=1（须与 truth.json pass_threshold 一致）
TEST_TIMEOUT_S = 10         # 每组测试 subprocess 超时（秒）
PROBLEM_BUDGET_S = 240      # 单题累计运行预算，防病态解把判分拖死（超预算该题判 fail）
N_PROBLEMS = 4
PROBLEM_ORDER = ["abc387_f", "abc388_f", "abc388_g", "abc389_g"]
EXPECTED_TEST_COUNTS = {"abc387_f": 43, "abc388_f": 43, "abc388_g": 42, "abc389_g": 43}
ITEM_WEIGHT = 25.0          # 每题观察项权重（4 × 25 = 100）；守卫项权重 0
EXPECTED_INPUT_NAME = "problems.json"

HERE = Path(__file__).resolve().parent


class CaseError(Exception):
    """用例自身不一致（truth 漂移 / 常量不符）→ 退出码 2。"""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def norm(text: str) -> str:
    """按行 rstrip 比较口径：统一换行、逐行去行尾空白、丢末尾空行。"""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    while lines and lines[-1].strip() == "":
        lines.pop()
    return "\n".join(line.rstrip() for line in lines)


# ------------------------------------------------------------------ 用例自校验

def load_truth() -> dict:
    return json.loads((HERE / "truth.json").read_text(encoding="utf-8"))


def verify_case() -> dict:
    """三重守卫 ①③：truth 与磁盘输入 / checker 常量交叉校验，任一漂移 → CaseError。"""
    truth = load_truth()
    if truth.get("case_id") != CASE_ID:
        raise CaseError("truth case_id=%r 与 checker CASE_ID=%r 不一致"
                        % (truth.get("case_id"), CASE_ID))
    if int(truth.get("n_problems", -1)) != N_PROBLEMS:
        raise CaseError("truth n_problems=%r 与 checker N_PROBLEMS=%d 不一致"
                        % (truth.get("n_problems"), N_PROBLEMS))
    if int(truth.get("pass_threshold", -1)) != PASS_THRESHOLD:
        raise CaseError("truth pass_threshold=%r 与 checker PASS_THRESHOLD=%d 不一致"
                        % (truth.get("pass_threshold"), PASS_THRESHOLD))
    if int(truth.get("timeout_s_per_test", -1)) != TEST_TIMEOUT_S:
        raise CaseError("truth timeout_s_per_test=%r 与 checker TEST_TIMEOUT_S=%d 不一致"
                        % (truth.get("timeout_s_per_test"), TEST_TIMEOUT_S))
    if truth.get("input_name") != EXPECTED_INPUT_NAME:
        raise CaseError("truth input_name=%r 与 checker EXPECTED_INPUT_NAME=%r 不一致"
                        % (truth.get("input_name"), EXPECTED_INPUT_NAME))

    path = HERE / "inputs" / EXPECTED_INPUT_NAME
    if not path.is_file():
        raise CaseError("缺少输入文件：%s" % path)
    data = path.read_bytes()
    actual = sha256_bytes(data)
    if actual != truth.get("input_sha256"):
        raise CaseError("输入与 truth 记录不一致：%s\n  truth=%s\n  actual=%s"
                        % (path, truth.get("input_sha256"), actual))
    if len(data) != truth.get("input_bytes"):
        raise CaseError("输入字节数漂移：%d != truth %r" % (len(data), truth.get("input_bytes")))

    problems = truth.get("problems") or {}
    if list(problems.keys()) != PROBLEM_ORDER:
        raise CaseError("truth 题单=%r 与 checker PROBLEM_ORDER=%r 不一致"
                        % (list(problems.keys()), PROBLEM_ORDER))
    for pid in PROBLEM_ORDER:
        spec = problems[pid]
        tests = spec.get("tests") or []
        if len(tests) != EXPECTED_TEST_COUNTS[pid]:
            raise CaseError("%s 测试数 %d != checker 常量 %d"
                            % (pid, len(tests), EXPECTED_TEST_COUNTS[pid]))
        recomputed = sha256_bytes(
            json.dumps(tests, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        if recomputed != spec.get("tests_sha256"):
            raise CaseError("%s 测试集 SHA-256 漂移（truth 被改动）" % pid)
        for t in tests:
            if not isinstance(t.get("input"), str) or not isinstance(t.get("output"), str):
                raise CaseError("%s 测试记录缺少 input/output 字符串" % pid)
    return truth


# ------------------------------------------------------------------ 运行与判分

def run_problem(path: Path, tests: list):
    """跑单题全部测试；返回 (pass, info)。首个失败即短路（单题全过才算过）。"""
    started = time.monotonic()
    for i, case in enumerate(tests):
        if time.monotonic() - started > PROBLEM_BUDGET_S:
            return False, {"passed": i, "total": len(tests), "first_fail_index": i,
                           "fail_kind": "budget",
                           "reason": "单题累计运行超过 %ds 预算（#%d 未跑）" % (PROBLEM_BUDGET_S, i)}
        try:
            proc = subprocess.run(
                [sys.executable, str(path)],
                input=case["input"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=TEST_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            return False, {"passed": i, "total": len(tests), "first_fail_index": i,
                           "fail_kind": "timeout",
                           "reason": "#%d 超时（>%ds）" % (i, TEST_TIMEOUT_S)}
        except OSError as exc:
            return False, {"passed": i, "total": len(tests), "first_fail_index": i,
                           "fail_kind": "exec",
                           "reason": "#%d 无法运行：%s" % (i, exc)}
        if proc.returncode != 0:
            tail = (proc.stderr or "").strip().splitlines()[-1:] or [""]
            return False, {"passed": i, "total": len(tests), "first_fail_index": i,
                           "fail_kind": "exit",
                           "reason": "#%d 退出码 %d：%s"
                                     % (i, proc.returncode, tail[0][:80])}
        got, want = norm(proc.stdout), norm(case["output"])
        if got != want:
            return False, {"passed": i, "total": len(tests), "first_fail_index": i,
                           "fail_kind": "wrong",
                           "reason": "#%d 输出不符（期望 %r，实际 %r）"
                                     % (i, want[:40], got[:40])}
    return True, {"passed": len(tests), "total": len(tests), "first_fail_index": -1,
                  "fail_kind": "", "reason": ""}


def check_input_copy(run_dir: Path, truth: dict):
    """守卫 ②：run_dir 若附带输入副本，必须与 canonical 一致，否则 reward 0。"""
    for rel in (("inputs", EXPECTED_INPUT_NAME), (EXPECTED_INPUT_NAME,)):
        candidate = run_dir.joinpath(*rel)
        if candidate.is_file():
            if sha256_bytes(candidate.read_bytes()) == truth["input_sha256"]:
                return True, "附带输入副本与 canonical 一致（%s）" % "/".join(rel)
            return False, "附带输入副本被修改（%s），与 canonical 不一致" % "/".join(rel)
    return True, "未附输入副本（未核验，不扣分）"


def judge(run_dir: Path) -> dict:
    truth = verify_case()
    integrity_ok, integrity_note = check_input_copy(run_dir, truth)
    checks = [{"id": "input_integrity", "item": "输入完整性（守卫）", "weight": 0.0,
               "pass": integrity_ok, "note": integrity_note, "guard": True}]
    passed = 0
    for pid in PROBLEM_ORDER:
        spec = truth["problems"][pid]
        total = len(spec["tests"])
        path = run_dir / "solutions" / ("%s.py" % pid)
        if not path.is_file():
            checks.append({"id": pid, "item": "%s %s" % (pid, spec["title"]),
                           "weight": ITEM_WEIGHT, "pass": False,
                           "note": "缺少 solutions/%s.py" % pid,
                           "passed_tests": 0, "total_tests": total, "first_fail_index": -1,
                           "fail_kind": "missing"})
            continue
        ok, info = run_problem(path, spec["tests"])
        passed += int(ok)
        note = ("%d/%d 全过" % (total, total) if ok else
                "%d/%d 首个失败 %s" % (info["passed"], total, info["reason"]))
        checks.append({"id": pid, "item": "%s %s" % (pid, spec["title"]),
                       "weight": ITEM_WEIGHT, "pass": ok, "note": note,
                       "passed_tests": info["passed"], "total_tests": total,
                       "first_fail_index": info["first_fail_index"],
                       "fail_kind": info["fail_kind"]})
    reward = 1 if (passed >= PASS_THRESHOLD and integrity_ok) else 0
    return {
        "case": CASE_ID,
        "checker_version": CHECKER_VERSION,
        "reward": reward,
        "weighted": round(passed / N_PROBLEMS * 100.0, 2),
        "passed_problems": passed,
        "total_problems": N_PROBLEMS,
        "threshold": PASS_THRESHOLD,
        "checks": checks,
    }


def render(result: dict) -> str:
    lines = ["%s checker v%s（判分：4 题各 25 分权重；通过 ≥%d 题 reward=1）"
             % (CASE_ID, CHECKER_VERSION, PASS_THRESHOLD)]
    for c in result["checks"]:
        mark = "PASS" if c["pass"] else "FAIL"
        weight = "守卫" if c.get("guard") else "%g%%" % c["weight"]
        lines.append("  [%s] %-14s %-6s %s" % (mark, c["id"], weight, c["note"]))
    lines.append("通过 %d/%d 题；REWARD=%d；WEIGHTED=%s"
                 % (result["passed_problems"], N_PROBLEMS,
                    result["reward"], result["weighted"]))
    return "\n".join(lines)


# ------------------------------------------------------------------ 自测

def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _oracle_text(pid: str) -> str:
    return (HERE / "solution" / ("%s.py" % pid)).read_text(encoding="utf-8")


def _sample_lookup_text(spec: dict) -> str:
    """负例：只背下公开样例（样例输入→输出查表），隐藏测试全错。"""
    mapping = {"\n".join(l.strip() for l in t["input"].strip().splitlines()): t["output"]
               for t in spec["tests"] if t.get("source") == "public"}
    return (
        "import json, sys\n"
        "MAPPING = json.loads(%r)\n"
        "raw = sys.stdin.read()\n"
        "key = '\\n'.join(line.strip() for line in raw.strip().splitlines())\n"
        "print(MAPPING.get(key, '0'))\n"
    ) % json.dumps(mapping, ensure_ascii=False)


def _format_mangle_text(pid: str) -> str:
    """负例：答案全对但输出格式错（行首空格 + 词间双空格）。"""
    oracle = str(HERE / "solution" / ("%s.py" % pid))
    return (
        "import io, runpy, sys\n"
        "_buf = io.StringIO()\n"
        "_old = sys.stdout\n"
        "sys.stdout = _buf\n"
        "try:\n"
        "    runpy.run_path(%r, run_name='__main__')\n"
        "finally:\n"
        "    sys.stdout = _old\n"
        "lines = _buf.getvalue().rstrip('\\n').splitlines()\n"
        "sys.stdout.write('\\n'.join('  ' + ln.replace(' ', '  ') for ln in lines) + '\\n')\n"
    ) % oracle


def selftest() -> int:
    truth = verify_case()
    results = []

    def record(name, expect, got, detail=""):
        results.append({"name": name, "expect": expect, "got": got,
                        "ok": got == expect, "detail": detail})

    def put_oracle(run_dir: Path, pids) -> None:
        for pid in pids:
            _write(run_dir / "solutions" / ("%s.py" % pid), _oracle_text(pid))

    with tempfile.TemporaryDirectory(prefix="lcb-recent-selftest-") as tmp:

        def builder(name: str) -> Path:
            return Path(tempfile.mkdtemp(prefix="lcb-%s-" % name, dir=tmp))

        # ---- 正例 1：nop（空 run_dir）
        d = builder("nop")
        r = judge(d)
        record("nop（空 run_dir）", 0, r["reward"],
               "passed=%d" % r["passed_problems"])

        # ---- 正例 2：oracle（solution/ 四题全过）
        d = builder("oracle")
        put_oracle(d, PROBLEM_ORDER)
        r = judge(d)
        record("oracle（solution/ 四题）", 1, r["reward"],
               "passed=%d weighted=%s" % (r["passed_problems"], r["weighted"]))
        if r["reward"] != 1 or r["passed_problems"] != N_PROBLEMS:
            results[-1]["detail"] += " 明细：" + "；".join(
                "%s %s" % (c["id"], c["note"]) for c in r["checks"] if not c["pass"])

        # ---- 正例 3：边界（恰好 2/4 通过 → reward 1）
        d = builder("boundary")
        put_oracle(d, PROBLEM_ORDER[:2])
        r = judge(d)
        record("边界：恰好 2/4 通过", 1, r["reward"],
               "passed=%d weighted=%s" % (r["passed_problems"], r["weighted"]))

        # ---- 负例 1：只交 1 题（1/4 < 达标线）
        d = builder("one_problem")
        put_oracle(d, PROBLEM_ORDER[:1])
        r = judge(d)
        record("负例：只交 1 题正确解", 0, r["reward"],
               "passed=%d weighted=%s" % (r["passed_problems"], r["weighted"]))

        # ---- 负例 2：四题都是空文件
        d = builder("empty_files")
        for pid in PROBLEM_ORDER:
            _write(d / "solutions" / ("%s.py" % pid), "")
        r = judge(d)
        record("负例：四题空文件", 0, r["reward"],
               " | ".join("%s:%s" % (c["id"], c["note"]) for c in r["checks"]
                          if c["id"] != "input_integrity"))

        # ---- 负例 3：四题都只 print(0)
        d = builder("print_zero")
        for pid in PROBLEM_ORDER:
            _write(d / "solutions" / ("%s.py" % pid), "print(0)\n")
        r = judge(d)
        record("负例：四题 print(0)", 0, r["reward"],
               " | ".join("%s:%s" % (c["id"], c["note"]) for c in r["checks"]
                          if c["id"] != "input_integrity"))

        # ---- 负例 4：只过公开样例、隐藏测试全错（每题首个失败点必须正好是第 1 组私有测试）
        d = builder("public_only")
        for pid in PROBLEM_ORDER:
            _write(d / "solutions" / ("%s.py" % pid),
                   _sample_lookup_text(truth["problems"][pid]))
        r = judge(d)
        by_id = {c["id"]: c for c in r["checks"]}
        prec_ok = all(
            by_id[pid]["first_fail_index"] == truth["problems"][pid]["n_public"]
            for pid in PROBLEM_ORDER)
        record("负例：只过公开样例不过私有", 0, r["reward"],
               "reward=%d 每题首个失败点=公开测试数? %s（%s）"
               % (r["reward"], prec_ok,
                  " | ".join("%s:%s/%s" % (pid, by_id[pid]["first_fail_index"],
                                           truth["problems"][pid]["n_public"])
                             for pid in PROBLEM_ORDER)))
        results[-1]["ok"] = results[-1]["ok"] and prec_ok

        # ---- 负例 5：超时死循环（abc387_f 死循环，其余缺题 → 0 且失败类型为 timeout）
        d = builder("timeout")
        _write(d / "solutions" / "abc387_f.py", "while True:\n    pass\n")
        r = judge(d)
        by_id = {c["id"]: c for c in r["checks"]}
        timeout_prec = (by_id["abc387_f"]["fail_kind"] == "timeout"
                        and by_id["abc387_f"]["first_fail_index"] == 0)
        record("负例：超时死循环", 0, r["reward"],
               "abc387_f fail_kind=%s（timeout? %s）"
               % (by_id["abc387_f"]["fail_kind"], timeout_prec))
        results[-1]["ok"] = results[-1]["ok"] and timeout_prec

        # ---- 负例 6：答案全对但输出格式错（行首空格 / 多空格）
        d = builder("format_spaces")
        for pid in PROBLEM_ORDER:
            _write(d / "solutions" / ("%s.py" % pid), _format_mangle_text(pid))
        r = judge(d)
        by_id = {c["id"]: c for c in r["checks"]}
        fmt_prec = all(by_id[pid]["fail_kind"] == "wrong" for pid in PROBLEM_ORDER)
        record("负例：输出格式多空格", 0, r["reward"],
               "四题均为输出不符? %s（%s）"
               % (fmt_prec, " | ".join("%s:%s" % (pid, by_id[pid]["fail_kind"])
                                       for pid in PROBLEM_ORDER)))
        results[-1]["ok"] = results[-1]["ok"] and fmt_prec

        # ---- 负例 7：输入副本被篡改（四题全过也只给 0，input_integrity 变红）
        d = builder("input_tamper")
        put_oracle(d, PROBLEM_ORDER)
        data = (HERE / "inputs" / EXPECTED_INPUT_NAME).read_bytes()
        tampered = data.replace(b"lcb-recent-hard-4", b"lcb-recent-hard-X", 1)
        if tampered == data:
            raise SystemExit("selftest 前置失败：无法构造被篡改的输入副本")
        _write(d / "inputs" / EXPECTED_INPUT_NAME, tampered.decode("utf-8"))
        r = judge(d)
        by_id = {c["id"]: c for c in r["checks"]}
        tamper_prec = (not by_id["input_integrity"]["pass"]
                       and r["passed_problems"] == N_PROBLEMS and r["reward"] == 0)
        record("负例：run_dir 输入副本被篡改", 0, r["reward"],
               "四题全过但守卫拦截? %s（integrity=%s, passed=%d）"
               % (tamper_prec, by_id["input_integrity"]["pass"], r["passed_problems"]))
        results[-1]["ok"] = results[-1]["ok"] and tamper_prec

        # ---- 守卫 ①：truth 漂移（拷走 checker+truth，改 SHA 后应 exit 2）
        d = Path(tmp) / "drifted_case"
        d.mkdir()
        shutil.copyfile(HERE / "checker.py", d / "checker.py")
        (d / "inputs").mkdir()
        shutil.copyfile(HERE / "inputs" / EXPECTED_INPUT_NAME, d / "inputs" / EXPECTED_INPUT_NAME)
        drifted = json.loads((HERE / "truth.json").read_text(encoding="utf-8"))
        drifted["input_sha256"] = "0" * 64
        (d / "truth.json").write_text(json.dumps(drifted, ensure_ascii=False), encoding="utf-8")
        empty_run = Path(tmp) / "empty_run"
        empty_run.mkdir()
        proc = subprocess.run([sys.executable, str(d / "checker.py"), str(empty_run)],
                              capture_output=True, text=True, timeout=120)
        drift_ok = proc.returncode == 2
        record("守卫：truth SHA-256 漂移 → ERROR exit 2", 2, proc.returncode,
               "stderr=%r" % (proc.stderr.strip().splitlines()[-1:] or [""]))
        results[-1]["ok"] = drift_ok

    n_pass = sum(1 for x in results if x["ok"])
    for x in results:
        print("[%s] %-34s expect=%s got=%s  %s"
              % ("PASS" if x["ok"] else "FAIL", x["name"], x["expect"], x["got"], x["detail"]))
    positives = sum(1 for x in results if x["expect"] == 1)
    negatives = sum(1 for x in results if x["expect"] == 0)
    print("-" * 100)
    print("自测：%d/%d 项通过（正例 %d、负例 %d、守卫/ERROR 项 %d）；输入 SHA-256=%s"
          % (n_pass, len(results), positives, negatives,
             len(results) - positives - negatives, truth["input_sha256"][:16]))
    if n_pass != len(results):
        print("SELFTEST FAILED", file=sys.stderr)
        return 2
    print("SELFTEST OK")
    return 0


# ------------------------------------------------------------------ 入口

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="%s 判分器（LiveCodeBench v6 派生，MIT）" % CASE_ID)
    parser.add_argument("run_dir", nargs="?", help="运行目录（含 solutions/<problem_id>.py）")
    parser.add_argument("--json", action="store_true", help="只输出一行 JSON")
    parser.add_argument("--selftest", action="store_true", help="跑 nop/oracle/负例/守卫自测")
    args = parser.parse_args(argv)

    if args.selftest:
        try:
            return selftest()
        except CaseError as exc:
            print("ERROR: %s" % exc, file=sys.stderr)
            return 2
    if not args.run_dir:
        parser.error("缺少 run_dir（或使用 --selftest）")

    run_dir = Path(args.run_dir).resolve()
    try:
        if not run_dir.is_dir():
            raise CaseError("run_dir 不存在或不是目录：%s" % run_dir)
        result = judge(run_dir)
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
    raise SystemExit(main())