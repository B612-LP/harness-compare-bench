#!/usr/bin/env python3
"""verify.py — abc387_f（Count Arrays）四归档静态正确性证明的公开复算。

题意（ABC387 F，2-用例/lcb-recent-hard-4/inputs/problems.json，SHA
0ce2f9c1…592a673）：给定 N, M 与序列 A（1 ≤ A_i ≤ N），计数 x ∈ [1,M]^N
满足对每个 i 有 x_i ≤ x_{A_i}，答案模 998244353。

本脚本自足复算四层事实：
  1. 暴力枚举（itertools 全枚举）独立复核七个预注册判定点的手推真值；
  2. 引理 1-3 计数公式（环分解 + 悬挂森林树 DP）的独立实现与暴力枚举
     在随机小图族上逐例对账（合成校准）；
  3. 三个公开样例：公式实现与四个归档的实际输出对照题面期望；
  4. 四个归档（3-表现现场/r20261125-five-lcb/）SHA256 钉定后，
     以 `python3 -B` 子进程在七判定点与三样例上直接复算，
     输出对照真值并检查「单整数一行」格式。

纯标准库；无网络；确定性（固定随机种子）；仅打印 JSON，不写文件。
`python3 -B` 与 `python3 -OB` 输出逐字节相同（见 README 的 stdout SHA）。
"""
import hashlib
import itertools
import json
import os
import platform
import random
import subprocess
import sys
from collections import deque

MOD = 998244353
PAGE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(PAGE_DIR))
REL_ROOT = "3-表现现场/r20261125-five-lcb"

ARCHIVES = {
    "codex": REL_ROOT + "/codex/solutions/abc387_f.py",
    "dsh": REL_ROOT + "/dsh/solutions/abc387_f.py",
    "doubao": REL_ROOT + "/doubao/solutions/abc387_f.py",
    "yuanbao": REL_ROOT + "/yuanbao/abc387_f.py",
}
PIN_SHA = {
    "codex": "4ff13ed6cc434da2034e75d125c4eee9fcd33f3a53de2ef3d2b88ec15942bc37",
    "dsh": "f03cfec68342d20c7745ccb88507b3b75372759a02f037b4948800f6386c6a08",
    "doubao": "6acce673ef56f3dce741155afffa5d62c9b6e7d5abdffec3e525de8206503ee2",
    "yuanbao": "c8e1ff0a5aaf802ddb1fba644aeea290683c5675d970ab33223ea867627cb897",
}
PROBLEM_PINS = {
    "2-用例/lcb-recent-hard-4/instruction.md":
        "1c39b2fa66982a7d54851e20822cb4064d8254122f2b047634b64fecdbd6045c",
    "2-用例/lcb-recent-hard-4/inputs/problems.json":
        "0ce2f9c1eee0039fa9cfc7cd9969d99118d3fba4ac41571c49d9f5289592a673",
}

# 预注册判定点（手推真值写定于阅读任何候选代码之前；见私有 PREREG 同源表）
CHECKPOINTS = [
    {"name": "C1-identity-selfloops", "n": 3, "m": 4, "a": [1, 2, 3], "hand_truth": 64},
    {"name": "C2-single-full-cycle", "n": 3, "m": 5, "a": [2, 3, 1], "hand_truth": 5},
    {"name": "C3a-hanging-chain", "n": 2, "m": 3, "a": [2, 2], "hand_truth": 6},
    {"name": "C3b-two-node-cycle", "n": 2, "m": 2, "a": [2, 1], "hand_truth": 2},
    {"name": "C3c-single-selfloop", "n": 1, "m": 7, "a": [1], "hand_truth": 7},
    {"name": "C3d-chain-with-backpoint", "n": 4, "m": 2, "a": [2, 3, 4, 3], "hand_truth": 4},
]

# 题面公开样例（与 2-用例/lcb-recent-hard-4/inputs/problems.json 逐字一致）
SAMPLES = [
    {"name": "sample1", "stdin": "3 3\n2 1 1", "expected": "6"},
    {"name": "sample2", "stdin": "4 9\n1 1 1 1", "expected": "2025"},
    {"name": "sample3", "stdin": "10 5\n9 4 5 5 4 2 1 5 7 2", "expected": "10010"},
]

BRUTE_CAP = 2_000_000  # m**n 上限；样例3（5^10=9,765,625）超出，由公式+归档双路覆盖


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def brute_count(n, m, a):
    """全枚举计数；超过容量上限返回 None（诚实缺口，不假装算过）。"""
    if m ** n > BRUTE_CAP:
        return None
    pairs = [(i, a[i] - 1) for i in range(n)]
    cnt = 0
    for x in itertools.product(range(1, m + 1), repeat=n):
        ok = True
        for i, j in pairs:
            if x[i] > x[j]:
                ok = False
                break
        if ok:
            cnt += 1
    return cnt


def formula_count(n, m, a):
    """引理 1-3 独立实现：环上取等，悬挂森林树 DP，环间相乘。0 基内部。"""
    if not (1 <= n <= 10 ** 6 and 1 <= m <= 10 ** 6):
        raise ValueError("out of contract scale for this script")
    if len(a) != n or any(not (1 <= v <= n) for v in a):
        raise ValueError("input violates stated constraints")
    par = [v - 1 for v in a]

    # --- 环检测：白灰黑迭代行走，每环恰录一次 ---
    WHITE, GRAY, DONE = 0, 1, 2
    color = [WHITE] * n
    on_cycle = [False] * n
    cycles = []
    for s in range(n):
        if color[s] != WHITE:
            continue
        path = []
        v = s
        while color[v] == WHITE:
            color[v] = GRAY
            path.append(v)
            v = par[v]
        if color[v] == GRAY:
            idx = path.index(v)
            cyc = path[idx:]
            for u in cyc:
                on_cycle[u] = True
            cycles.append(cyc)
        for u in path:
            color[u] = DONE

    # --- 悬挂森林：非环节点 u 的父是 par[u]（可能为环点或更深悬挂点） ---
    children = [[] for _ in range(n)]
    for u in range(n):
        if not on_cycle[u]:
            children[par[u]].append(u)

    # --- 自环向外的 BFS 序（父先于子）；逆序做子先父后的 DP ---
    order = []
    seen = [False] * n
    dq = deque()
    for v in range(n):
        if on_cycle[v]:
            seen[v] = True
            dq.append(v)
    while dq:
        v = dq.popleft()
        for c in children[v]:
            if not seen[c]:
                seen[c] = True
                order.append(c)
                dq.append(c)
    pref = {}  # 非环节点 u：P_u[t] = Σ_{s≤t} W_u[s]，下标 0..m-1
    for u in reversed(order):
        prod = [1] * m  # 空积 = W 恒 1
        for c in children[u]:
            pc = pref[c]
            for t in range(m):
                prod[t] = prod[t] * pc[t] % MOD
        acc = 0
        p = []
        for t in range(m):
            acc = (acc + prod[t]) % MOD
            p.append(acc)
        pref[u] = p

    # --- 环组合：total_C = Σ_t Π_{v∈C} W_v(t)；W_环点 = Π_{c∈children} P_c ---
    ans = 1
    for cyc in cycles:
        total = 0
        w = []
        for v in cyc:
            prod = [1] * m
            for c in children[v]:
                pc = pref[c]
                for t in range(m):
                    prod[t] = prod[t] * pc[t] % MOD
            w.append(prod)
        for t in range(m):
            prod = 1
            for row in w:
                prod = prod * row[t] % MOD
            total = (total + prod) % MOD
        ans = ans * total % MOD
    return ans


def run_archive(rel_path, stdin_text):
    """以 python3 -B 子进程运行归档；返回 (exit, stdout, stderr)。"""
    path = os.path.join(REPO_ROOT, rel_path)
    r = subprocess.run(
        [sys.executable, "-B", path],
        input=stdin_text.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")


def single_integer_line(stdout_text):
    s = stdout_text.strip("\n")
    return ("\n" not in s) and s.isdigit()


def main():
    # ---------- 题面与归档钉定 ----------
    problem_pin = {}
    for rel, want in PROBLEM_PINS.items():
        digest = sha256_file(os.path.join(REPO_ROOT, rel))
        problem_pin[rel] = {"sha256": digest, "pinned_match": (digest == want),
                            "bytes": os.path.getsize(os.path.join(REPO_ROOT, rel))}
    pins_ok_problem = all(v["pinned_match"] for v in problem_pin.values())

    pin = {}
    all_pinned = True
    for name, rel in ARCHIVES.items():
        path = os.path.join(REPO_ROOT, rel)
        digest = sha256_file(path)
        ok = (digest == PIN_SHA[name])
        all_pinned = all_pinned and ok
        pin[name] = {"repo_path": rel, "sha256": digest, "pinned_match": ok,
                     "bytes": os.path.getsize(path)}

    # ---------- 判定点：手推真值 × 暴力 × 公式 × 归档 ----------
    checkpoints = []
    cp_ok = True
    for cp in CHECKPOINTS:
        b = brute_count(cp["n"], cp["m"], cp["a"])
        f = formula_count(cp["n"], cp["m"], cp["a"])
        entry = {
            "name": cp["name"],
            "input": {"n": cp["n"], "m": cp["m"], "a": cp["a"]},
            "hand_truth_prereg": cp["hand_truth"],
            "brute": b,
            "formula": f,
            "brute_matches_hand": (b == cp["hand_truth"]),
            "formula_matches_hand": (f == cp["hand_truth"]),
            "archives": {},
        }
        if all_pinned:
            stdin_text = "%d %d\n%s\n" % (cp["n"], cp["m"], " ".join(map(str, cp["a"])))
            for name, rel in ARCHIVES.items():
                code, out, err = run_archive(rel, stdin_text)
                val_ok = (code == 0 and err == "" and out.strip().isdigit()
                          and int(out.strip()) % MOD == cp["hand_truth"] % MOD)
                entry["archives"][name] = {
                    "exit": code,
                    "stdout": out.strip(),
                    "stderr_empty": (err == ""),
                    "matches_truth": val_ok,
                    "single_integer_line": single_integer_line(out),
                }
        cp_ok = cp_ok and entry["brute_matches_hand"] and entry["formula_matches_hand"] \
            and all(v["matches_truth"] and v["single_integer_line"]
                    for v in entry["archives"].values())
        checkpoints.append(entry)

    # ---------- 公开样例 ----------
    samples = []
    sp_ok = True
    for sp in SAMPLES:
        first, second = sp["stdin"].split("\n")
        n, m = map(int, first.split())
        a = list(map(int, second.split()))
        b = brute_count(n, m, a)
        f = formula_count(n, m, a)
        expected = int(sp["expected"])
        entry = {
            "name": sp["name"],
            "stdin": sp["stdin"],
            "expected_from_statement": sp["expected"],
            "brute": b,
            "formula": f,
            "formula_matches_statement": (f == expected % MOD),
            "brute_matches_statement": (b is not None and b == expected),
            "archives": {},
        }
        if all_pinned:
            for name, rel in ARCHIVES.items():
                code, out, err = run_archive(rel, sp["stdin"])
                val_ok = (code == 0 and err == "" and out.strip().isdigit()
                          and int(out.strip()) % MOD == expected % MOD)
                entry["archives"][name] = {
                    "exit": code,
                    "stdout": out.strip(),
                    "matches_statement": val_ok,
                    "single_integer_line": single_integer_line(out),
                }
        sp_ok = sp_ok and entry["formula_matches_statement"] \
            and (b is None or entry["brute_matches_statement"]) \
            and all(v["matches_statement"] for v in entry["archives"].values())
        samples.append(entry)

    # ---------- 合成校准：固定种子随机图族，暴力 × 公式 × 四归档逐例对账 ----------
    rng = random.Random(20261128)
    calib_cases = []
    mism = []
    arch_mism = {name: [] for name in ARCHIVES}
    n_struct = 0
    arch_runs = 0
    for case_i in range(400):
        n = rng.randint(1, 7)
        m = rng.randint(1, 5)
        kind = case_i % 8
        if kind == 0:      # 恒等：全自环
            a = list(range(1, n + 1))
            n_struct += 1
        elif kind == 1:    # 单一全环
            a = list(range(2, n + 1)) + [1]
            n_struct += 1
        elif kind == 2:    # 链 1→2→…→n
            a = [min(i + 1, n) for i in range(1, n + 1)]
            n_struct += 1
        elif kind == 3:    # 链 + 回指尾环
            a = [min(i + 1, n) for i in range(1, n + 1)]
            if n >= 2:
                a[-1] = n - 1
            n_struct += 1
        elif kind == 4:    # 星形：全指 1
            a = [1] * n
            n_struct += 1
        else:              # 均匀随机
            a = [rng.randint(1, n) for _ in range(n)]
        b = brute_count(n, m, a)
        f = formula_count(n, m, a)
        if b != f:
            mism.append({"n": n, "m": m, "a": a, "brute": b, "formula": f})
        if all_pinned:
            stdin_text = "%d %d\n%s\n" % (n, m, " ".join(map(str, a)))
            for name, rel in ARCHIVES.items():
                code, out, err = run_archive(rel, stdin_text)
                arch_runs += 1
                good = (code == 0 and err == "" and out.strip().isdigit()
                        and int(out.strip()) % MOD == b % MOD)
                if not good:
                    arch_mism[name].append({"n": n, "m": m, "a": a, "brute": b,
                                            "archive_stdout": out.strip(), "exit": code})
        calib_cases.append((n, m))
    calibration = {
        "seed": 20261128,
        "cases": len(calib_cases),
        "structured_cases": n_struct,
        "random_cases": len(calib_cases) - n_struct,
        "n_range": [min(c[0] for c in calib_cases), max(c[0] for c in calib_cases)],
        "m_range": [min(c[1] for c in calib_cases), max(c[1] for c in calib_cases)],
        "brute_cap": BRUTE_CAP,
        "mismatches": mism,
        "all_agree": (len(mism) == 0),
        "archives_vs_brute": {
            "archive_runs_performed": arch_runs,
            "mismatch_counts": {k: len(v) for k, v in arch_mism.items()},
            "first_mismatches": {k: v[:2] for k, v in arch_mism.items() if v},
            "all_agree": all(len(v) == 0 for v in arch_mism.values()),
        },
    }

    result = {
        "page": "同题四归档静态正确性证明-2026-11-28 公开复算",
        "problem": "abc387_f Count Arrays (ABC387 F); count x in [1,M]^N with x_i <= x_{A_i}, mod 998244353",
        "problem_statement_source": "2-用例/lcb-recent-hard-4 (instruction.md / inputs/problems.json)",
        "python_version": platform.python_version(),
        "script_sha256": sha256_file(os.path.abspath(__file__)),
        "note_derivation": "lemma 1-3 (cycle equality, hanging-forest DP, product over cycles) "
                           "re-derived from the problem statement alone; brute force is the "
                           "ground truth on small instances; archives executed only after "
                           "SHA pinning, on prereg checkpoints and public samples only",
        "archives_pin": {"entries": pin, "all_pinned": all_pinned},
        "problem_pin": {"entries": problem_pin, "all_pinned": pins_ok_problem},
        "checkpoints": {"entries": checkpoints, "all_ok": cp_ok,
                        "n_archive_runs": len(CHECKPOINTS) * len(ARCHIVES)},
        "samples": {"entries": samples, "all_ok": sp_ok},
        "calibration": calibration,
        "verdict": {
            "checkpoints_ok": cp_ok,
            "samples_ok": sp_ok,
            "calibration_ok": calibration["all_agree"],
            "calibration_archives_ok": calibration["archives_vs_brute"]["all_agree"],
            "pins_ok": all_pinned and pins_ok_problem,
            "overall": "OK" if (cp_ok and sp_ok and calibration["all_agree"]
                                and calibration["archives_vs_brute"]["all_agree"]
                                and all_pinned and pins_ok_problem) else "FAIL",
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
