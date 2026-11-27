#!/usr/bin/env python3
"""三题小实例四归档真值复算（广度证据层）— 公开复算脚本。

对 r20261125 五产品同题实跑中除 abc387_f 外的三题（abc388_f / abc388_g / abc389_g）：
在预注册的小实例族（官方样例 + 固定种子生成实例）上，把 Codex / DSH / 豆包 / 元宝
四份固定归档当普通程序实跑，与独立暴力真值逐字节比对。范围限定：仅主张列出的
实例上「归档输出 = 暴力真值 / 题面公布期望」；不构成任何一题的完整正确性证明；
不新增模型/产品运行；不改冻结规范与历史成绩。

预注册先于实现冻结（实例族、种子、判定标准见仓库内本页 README；私有 PREREG 于
实现前写定）。真值算法独立于任何归档实现：
  - abc388_f：格子图 BFS 可达性（步长 [A,B]、坏格禁落）；
  - abc388_g：查询窗口内子集 DP 一般图最大匹配（2a≤b 配对），非题目贪心正解；
  - abc389_g：全图枚举 2^C(N,2)（N≤6），连通 + 奇偶平衡按边数计数 mod P。

用法：python3 -B verify.py   （无参数；-OB 输出应逐字节相同——输出含确定性内容，无时间戳）
"""
import hashlib
import json
import os
import random
import subprocess
import sys
import tempfile
from collections import deque

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(BASE, "..", ".."))
sys.setrecursionlimit(100000)

MOD_ENFORCE = False  # 语义占位：所有期望值均为精确整数渲染，无浮点参与


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


PROBLEM_PINS = {
    "instruction.md": ("2-用例/lcb-recent-hard-4/instruction.md",
                       "1c39b2fa66982a7d54851e20822cb4064d8254122f2b047634b64fecdbd6045c"),
    "problems.json": ("2-用例/lcb-recent-hard-4/inputs/problems.json",
                      "0ce2f9c1eee0039fa9cfc7cd9969d99118d3fba4ac41571c49d9f5289592a673"),
}

LCB = "3-表现现场/r20261125-five-lcb"
ARCHIVES = {
    "abc388_f": {
        "codex": (LCB + "/codex/solutions/abc388_f.py",
                  "d1702fae6ce60470007c3c124509da168ec1fcea7cb9614608d1812074ee8702"),
        "dsh": (LCB + "/dsh/solutions/abc388_f.py",
                "7297268ac7abb6c07a0c108c8fa2ae0d56c7acdef120bee6e615c615945b6c9e"),
        "doubao": (LCB + "/doubao/solutions/abc388_f.py",
                   "67551b01b51cfc6738f1a10b3a587cd643be538a08f7891f1b15c7a6b35ebf14"),
        "yuanbao": (LCB + "/yuanbao/abc388_f.py",
                    "6da7914ee9931843bc663745db02adfd1a9027b7ddf62c1730987546b0388fce"),
    },
    "abc388_g": {
        "codex": (LCB + "/codex/solutions/abc388_g.py",
                  "959138871953840a3afaa73ea9578f52f47d2b968f8b2e75ab1ab122d7965b16"),
        "dsh": (LCB + "/dsh/solutions/abc388_g.py",
                "9c57caff3eecac28c9627c7e8101b63044e79c77b572ec5ec47ecd3c7cc71d77"),
        "doubao": (LCB + "/doubao/solutions/abc388_g.py",
                   "c06fab5d468d79776846c3a14ca14dde0bc69706f9a5dc1b26517e70f2d1fc6f"),
        "yuanbao": (LCB + "/yuanbao/abc388_g.py",
                    "b65eee963adca0b5fb563b3988dcf591c0d3626222eb0319dc856e6856b56d86"),
    },
    "abc389_g": {
        "codex": (LCB + "/codex/solutions/abc389_g.py",
                  "6abcbda98be451f1999898e2503e5b5086486abb7581e3869f20de4d13cf17fc"),
        "dsh": (LCB + "/dsh/solutions/abc389_g.py",
                "e6ac90a8a434a3151d81eca69108f0b5b2e367bca56e68f7076f9dc872ee0615"),
        "doubao": (LCB + "/doubao/solutions/abc389_g.py",
                   "21ab73626e5960dc3297f08476267561edcd4ee1f58cc8f6370f81684c5a6959"),
        "yuanbao": (LCB + "/yuanbao/abc389_g.py",
                    "10dba9ebc139eaa4168b979745ef048f8814b58f786135a4698f35077590a384"),
    },
}

SEED = 20261128


# ---------------------------------------------------------------- 真值算法

def sugoroku_truth(N, A, B, intervals):
    """abc388_f 真值：从 1 出发 BFS，步长 [A,B]，坏格禁落，判 N 可达。"""
    bad = bytearray(N + 2)
    for (L, R) in intervals:
        for j in range(L, R + 1):
            bad[j] = 1
    seen = bytearray(N + 1)
    seen[1] = 1
    dq = deque([1])
    while dq:
        x = dq.popleft()
        if x == N:
            return True
        for d in range(A, B + 1):
            y = x + d
            if y <= N and not bad[y] and not seen[y]:
                seen[y] = 1
                dq.append(y)
    return False


def kagami_truth(sorted_a, queries):
    """abc388_g 真值：每查询窗口内子集 DP 最大匹配（一般图，2·top ≤ bottom）。"""
    out = []
    for (L, R) in queries:
        sub = sorted_a[L - 1:R]
        m = len(sub)
        if m < 2:
            out.append(0)
            continue
        f = [0] * (1 << m)
        for mask in range(1, 1 << m):
            low = (mask & -mask).bit_length() - 1  # 最低位元素 i 必须被处置
            rest = mask ^ (1 << low)
            best = f[rest]  # i 不配对
            jj = rest
            while jj:
                jb = jj & -jj
                j = jb.bit_length() - 1
                # 窗口升序 → 最低位元素只能作顶（2·A[low] ≤ A[j]）；
                # 作底需 2·A[j] ≤ A[low] ≤ A[j]，与 A_i ≥ 1 矛盾，不可能。
                if 2 * sub[low] <= sub[j]:
                    cand = f[rest ^ jb] + 1
                    if cand > best:
                        best = cand
                jj ^= jb
            f[mask] = best
        out.append(f[-1])
    return out


def _is_prime(p):
    if p < 2:
        return False
    i = 2
    while i * i <= p:
        if p % i == 0:
            return False
        i += 1
    return True


def oddeven_truth(N, P):
    """abc389_g 真值：全图枚举，连通 + 偶距点数==奇距点数，按边数计数 mod P。"""
    pairs = [(i, j) for i in range(N) for j in range(i + 1, N)]
    E = len(pairs)
    counts = [0] * (E + 1)
    full = (1 << N) - 1
    for mask in range(1 << E):
        adj = [0] * N
        m = 0
        mm = mask
        while mm:
            lb = mm & -mm
            k = lb.bit_length() - 1
            i, j = pairs[k]
            adj[i] |= 1 << j
            adj[j] |= 1 << i
            m += 1
            mm ^= lb
        # BFS from 0，记录奇偶深浅
        seen = 1
        side = [0] * N
        ev, od = 1, 0
        dq = deque([0])
        while dq:
            u = dq.popleft()
            nb = adj[u]
            while nb:
                lb = nb & -nb
                v = lb.bit_length() - 1
                nb ^= lb
                if not (seen >> v) & 1:
                    seen |= 1 << v
                    side[v] = side[u] ^ 1
                    if side[v]:
                        od += 1
                    else:
                        ev += 1
                    dq.append(v)
        if seen != full:
            continue
        if ev == od:
            counts[m] += 1
    return [c % P for c in counts[N - 1: E + 1]]


# ---------------------------------------------------------------- 实例生成

def gen_intervals(rng, N, M_target):
    """不相交、按 L 升序、1 < L ≤ R < N；放不满则如实减少并在头部反映。"""
    ivs = []
    span = max(1, (N - 2) // 6)
    tries = 0
    while len(ivs) < M_target and tries < 200:
        tries += 1
        L = rng.randint(2, N - 2)
        R = rng.randint(L, min(N - 1, L + span))
        if all(R + 1 < L2 or R2 + 1 < L for (L2, R2) in ivs):
            ivs.append((L, R))
    ivs.sort()
    return ivs


def gen_sugoroku():
    rng = random.Random(SEED)
    cases = []
    Ns = [12, 37, 64, 100, 333, 1000]
    ABs = [(1, 1), (1, 3), (2, 5), (3, 7), (5, 20)]
    idx = 0
    for N in Ns:
        for (A, B) in ABs:
            M_target = idx % 3
            idx += 1
            ivs = gen_intervals(rng, N, M_target)
            cases.append({"id": "f-gen-%02d" % len(cases), "N": N, "A": A, "B": B,
                          "intervals": ivs, "kind": "grid"})
    for _ in range(10):
        N = rng.randint(10, 2000)
        A = rng.randint(1, 20)
        B = rng.randint(A, 20)
        ivs = gen_intervals(rng, N, rng.randint(0, 5))
        cases.append({"id": "f-gen-%02d" % len(cases), "N": N, "A": A, "B": B,
                      "intervals": ivs, "kind": "random"})
    for c in cases:
        lines = ["%d %d %d %d" % (c["N"], len(c["intervals"]), c["A"], c["B"])]
        for (L, R) in c["intervals"]:
            lines.append("%d %d" % (L, R))
        c["input"] = "\n".join(lines) + "\n"
        c["expected"] = ("Yes\n" if sugoroku_truth(c["N"], c["A"], c["B"], c["intervals"])
                         else "No\n")
    return cases


def gen_kagami():
    rng = random.Random(SEED)
    cases = []
    for n in (4, 6, 8, 10, 12):
        for rep in (0, 1):
            a = sorted(rng.randint(1, 40) for _ in range(n))
            queries = [(L, R) for L in range(1, n + 1)
                       for R in range(L + 1, n + 1)]
            truth = kagami_truth(a, queries)
            lines = [str(n), " ".join(map(str, a)), str(len(queries))]
            for (L, R) in queries:
                lines.append("%d %d" % (L, R))
            cases.append({"id": "g-gen-%02d" % len(cases), "n": n, "array": a,
                          "nq": len(queries),
                          "input": "\n".join(lines) + "\n",
                          "expected": "\n".join(map(str, truth)) + "\n"})
    return cases


def gen_oddeven():
    cases = []
    for (N, P) in [(2, 998244353), (4, 924844033), (4, 100000007),
                   (6, 998244353), (6, 433416647)]:
        truth = oddeven_truth(N, P)
        cases.append({"id": "o-gen-%02d" % len(cases), "N": N, "P": P,
                      "input": "%d %d\n" % (N, P),
                      "expected": " ".join(map(str, truth)) + "\n"})
    return cases


# ---------------------------------------------------------------- 官方样例

OFFICIAL = {
    "abc388_f": [
        ("24 2 3 5\n7 8\n17 20\n", "Yes"),
        ("30 1 5 8\n4 24\n", "No"),
        ("100 4 10 11\n16 18\n39 42\n50 55\n93 99\n", "Yes"),
    ],
    "abc388_g": [
        ("11\n1 1 2 3 4 4 7 10 11 12 20\n5\n2 5\n3 8\n7 11\n1 2\n1 11\n",
         "2\n3\n1\n0\n5"),
        ("24\n127 148 170 174 258 311 331 414 416 436 517 523 532 587 591 638 660 748 760 776 837 857 972 984\n15\n7 11\n8 9\n8 13\n12 15\n9 23\n1 17\n8 12\n1 5\n6 17\n3 7\n12 19\n13 18\n7 22\n1 12\n14 15\n",
         "0\n0\n0\n0\n2\n6\n0\n1\n1\n0\n0\n0\n3\n5\n0"),
    ],
    "abc389_g": [
        ("4 998244353\n", "12 9 3 0"),
        ("6 924844033\n", "810 2100 3060 3030 2230 1210 450 100 10 0 0"),
        ("10 433416647\n",
         "49218750 419111280 321937732 107111441 372416570 351559278 312484809 "
         "334285827 317777667 211471846 58741385 422156135 323887465 54923551 "
         "121645733 94354149 346849276 72744827 385773306 163421544 351691775 "
         "59915863 430096957 166653801 346330874 185052506 245426328 47501118 "
         "7422030 899640 79380 4536 126 0 0 0 0"),
    ],
}


def format_check(problem, stdout_bytes, n_expected_lines=None, n_expected_tokens=None):
    """独立于内容的结构检查；返回 (ok, detail)。"""
    text = stdout_bytes.decode("utf-8", "replace")
    if problem == "abc388_f":
        lines = [l for l in text.split("\n") if l != ""]
        ok = len(lines) == 1 and lines[0] in ("Yes", "No")
        return ok, "single Yes/No line"
    if problem == "abc388_g":
        lines = [l for l in text.split("\n") if l != ""]
        ok = (n_expected_lines is not None and len(lines) == n_expected_lines
              and all(l.lstrip("-").isdigit() for l in lines))
        return ok, "exactly %s integer lines" % n_expected_lines
    if problem == "abc389_g":
        lines = [l for l in text.split("\n") if l != ""]
        toks = lines[0].split() if len(lines) == 1 else []
        ok = (len(lines) == 1 and n_expected_tokens is not None
              and len(toks) == n_expected_tokens
              and all(t.lstrip("-").isdigit() for t in toks))
        return ok, "single line with exactly %s tokens" % n_expected_tokens
    return False, "unknown problem"


def run_case(problem, archive_name, archive_path, case_id, input_text, expected_bytes):
    if problem == "abc388_g":
        n_lines = len(expected_bytes.decode("utf-8").rstrip("\n").split("\n"))
        n_toks = None
    elif problem == "abc389_g":
        n_lines = None
        n_toks = len(expected_bytes.decode("utf-8").rstrip("\n").split())
    else:
        n_lines = None
        n_toks = None
    with tempfile.TemporaryDirectory() as td:
        try:
            proc = subprocess.run(
                [sys.executable, "-B", archive_path],
                input=input_text.encode("utf-8"),
                capture_output=True, timeout=60, cwd=td)
        except subprocess.TimeoutExpired:
            return {"case": case_id, "archive": archive_name,
                    "result": "timeout", "content_mismatch": True}
        if proc.returncode != 0:
            return {"case": case_id, "archive": archive_name,
                    "result": "exit=%d" % proc.returncode,
                    "stderr_head": proc.stderr.decode("utf-8", "replace")[:200],
                    "content_mismatch": True}
        out = proc.stdout
        fc_ok, fc_detail = format_check(problem, out, n_lines, n_toks)
        rec = {"case": case_id, "archive": archive_name,
               "bytes": len(out), "format_ok": fc_ok}
        if proc.stderr.strip():
            rec["stderr_nonempty"] = True
        if out.rstrip(b"\n") == expected_bytes.rstrip(b"\n"):
            rec["result"] = "match"
            rec["content_mismatch"] = False
            rec["trailing_newline_diff"] = (out != expected_bytes)
        else:
            rec["result"] = "MISMATCH"
            rec["content_mismatch"] = True
            rec["expected_head"] = expected_bytes.decode("utf-8", "replace")[:80]
            rec["got_head"] = out.decode("utf-8", "replace")[:80]
        if not fc_ok:
            rec["format_fail"] = fc_detail
        return rec


def main():
    report = {"meta": {
        "seed": SEED,
        "scope": "breadth evidence: listed instances only; NOT a full correctness proof",
        "truth_sources": {
            "official_samples": "statement-published expected outputs",
            "generated": "BFS / subset-DP general matching / full graph enumeration",
        },
    }}

    pins = {}
    pins_ok = True
    for name, (rel, want) in PROBLEM_PINS.items():
        got = sha256_file(os.path.join(REPO, rel))
        pins[name] = {"path": rel, "sha256": got, "ok": got == want}
        pins_ok &= (got == want)
    arch_meta = {}
    for problem, m in ARCHIVES.items():
        arch_meta[problem] = {}
        for name, (rel, want) in m.items():
            got = sha256_file(os.path.join(REPO, rel))
            arch_meta[problem][name] = {"path": rel, "sha256": got,
                                        "ok": got == want}
            pins_ok &= (got == want)
    report["pins"] = {"problem_files": pins, "archives": arch_meta,
                      "all_ok": pins_ok}
    report["meta"]["prime_check_100000007"] = _is_prime(100000007)

    totals = {"instances": 0, "archive_runs": 0, "content_mismatch": 0,
              "format_minor": 0, "format_fail": 0, "nonzero_exit": 0,
              "stderr_nonempty": 0}

    # ---- abc388_f
    cases = []
    for i, (inp, exp) in enumerate(OFFICIAL["abc388_f"]):
        cases.append({"id": "f-off-%d" % (i + 1), "input": inp,
                      "expected": exp + "\n", "official": True})
    gen_f = gen_sugoroku()
    cases += gen_f
    res_f = {"official_cases": 3, "generated_cases": len(gen_f),
             "truth": "BFS reachability", "runs": []}
    for c in cases:
        for an, (_, _) in ARCHIVES["abc388_f"].items():
            rec = run_case("abc388_f", an, os.path.join(REPO, ARCHIVES["abc388_f"][an][0]),
                           c["id"], c["input"], c["expected"].encode())
            res_f["runs"].append(rec)
    report["abc388_f"] = summarize(res_f, totals)

    # ---- abc388_g
    cases = []
    for i, (inp, exp) in enumerate(OFFICIAL["abc388_g"]):
        cases.append({"id": "g-off-%d" % (i + 1), "input": inp,
                      "expected": exp + "\n", "official": True})
    gen_g = gen_kagami()
    cases += gen_g
    res_g = {"official_cases": 2, "generated_cases": len(gen_g),
             "truth": "subset-DP general matching", "runs": []}
    for c in cases:
        for an in ARCHIVES["abc388_g"]:
            rec = run_case("abc388_g", an, os.path.join(REPO, ARCHIVES["abc388_g"][an][0]),
                           c["id"], c["input"], c["expected"].encode())
            res_g["runs"].append(rec)
    report["abc388_g"] = summarize(res_g, totals)

    # ---- abc389_g
    cases = []
    for i, (inp, exp) in enumerate(OFFICIAL["abc389_g"]):
        cases.append({"id": "o-off-%d" % (i + 1), "input": inp,
                      "expected": exp + "\n", "official": True})
    gen_o = gen_oddeven()
    cases += gen_o
    res_o = {"official_cases": 3, "generated_cases": len(gen_o),
             "truth": "full graph enumeration", "runs": []}
    for c in cases:
        for an in ARCHIVES["abc389_g"]:
            rec = run_case("abc389_g", an, os.path.join(REPO, ARCHIVES["abc389_g"][an][0]),
                           c["id"], c["input"], c["expected"].encode())
            res_o["runs"].append(rec)
    report["abc389_g"] = summarize(res_o, totals)

    report["totals"] = totals
    all_ok = (pins_ok and totals["content_mismatch"] == 0
              and totals["format_fail"] == 0 and totals["nonzero_exit"] == 0
              and totals["stderr_nonempty"] == 0)
    report["verdict"] = {"overall": "OK" if all_ok else "FAIL",
                         "format_minor_note": (
                             "内容全部相等；format_minor 为尾换行差异计数，单独列报"
                             "，不影响 overall")}

    sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=1,
                                sort_keys=True) + "\n")
    return 0 if all_ok else 1


def summarize(res, totals):
    runs = res["runs"]
    cm = sum(1 for r in runs if r.get("content_mismatch"))
    ff = sum(1 for r in runs if not r.get("format_ok", True))
    ex = sum(1 for r in runs if r.get("result", "").startswith("exit="))
    tn = sum(1 for r in runs if r.get("trailing_newline_diff"))
    se = sum(1 for r in runs if r.get("stderr_nonempty"))
    totals["instances"] += res["official_cases"] + res["generated_cases"]
    totals["archive_runs"] += len(runs)
    totals["content_mismatch"] += cm
    totals["format_fail"] += ff
    totals["nonzero_exit"] += ex
    totals["format_minor"] += tn
    totals["stderr_nonempty"] += se
    bad = [r for r in runs if r.get("content_mismatch") or not r.get("format_ok", True)]
    by_archive = {}
    for r in runs:
        d = by_archive.setdefault(r["archive"], {"runs": 0, "match": 0})
        d["runs"] += 1
        d["match"] += (r["result"] == "match")
    return {"official_cases": res["official_cases"],
            "generated_cases": res["generated_cases"],
            "truth_algorithm": res["truth"],
            "archive_runs": len(runs),
            "content_mismatch": cm, "format_fail": ff,
            "trailing_newline_diff": tn, "stderr_nonempty": se,
            "by_archive": by_archive,
            "mismatches": bad[:20]}


if __name__ == "__main__":
    sys.exit(main())
