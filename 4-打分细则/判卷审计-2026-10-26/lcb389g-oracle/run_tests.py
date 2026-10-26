#!/usr/bin/env python3
"""lcb389g-oracle 参考解真实跑测脚本（只读冻结区，全部产物写在本目录）。

四段证据：
  A. 官方样例：official_samples.json（2026-10-26 抓取自 AtCoder 官方题面页，
     页面存档 official_page_abc389_g.html）——独立可解性证据。
  B. 独立小规模真值：brute_force.py 全枚举 N ∈ {2,4,6}（与 DP 无共享逻辑），
     并以 OEIS A001187 连通图计数锚点核对枚举器本身。
  C. truth.json 全部 43 组（3 公开 + 40 隐藏）按 checker 同口径逐组 subprocess
     实跑 + 计时 —— 该组只能证明与仓内夹具链一致（管路一致性），
     不作为可解性的独立证据（夹具链本身未经独立验证）。
  D. 计时结论：单组最大耗时 vs 10s 限额。

用法：python3 run_tests.py            # 人类可读报告 + 末行 RESULTS_JSON
退出码：0 = 全部通过；1 = 存在失败。Python ≥3.9，仅标准库。
"""
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOLUTION = HERE / "solution_abc389_g.py"
BRUTE = HERE / "brute_force.py"
CASE_DIR = HERE.parent.parent.parent / "2-用例" / "lcb-recent-hard-4"
TRUTH = CASE_DIR / "truth.json"
TIMEOUT_S = 10.0

A187 = {1: 1, 2: 1, 3: 4, 4: 38, 5: 728, 6: 26704}  # OEIS A001187 连通带标号图数


def norm(s):
    lines = [ln.rstrip() for ln in s.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def run_solution(inp):
    t0 = time.perf_counter()
    p = subprocess.run([sys.executable, str(SOLUTION)], input=inp.encode(),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=TIMEOUT_S)
    dt = time.perf_counter() - t0
    if p.returncode != 0:
        raise RuntimeError("exit %d: %s" % (p.returncode, p.stderr.decode()[:300]))
    return p.stdout.decode(), dt


def main():
    results = {"official_samples": None, "brute_force": None,
               "truth": None, "timing": None}
    all_ok = True

    print("=" * 72)
    print("A. 官方样例（AtCoder 抓取，独立可解性证据）")
    print("=" * 72)
    samples = json.loads((HERE / "official_samples.json").read_text())
    ok = 0
    for i, s in enumerate(samples["samples"], 1):
        got, dt = run_solution(s["input"])
        good = norm(got) == norm(s["output"])
        ok += good
        all_ok &= good
        print("  sample %d: input=%-16s %.3fs  %s"
              % (i, s["input"], dt, "PASS" if good else "FAIL got=%r" % got[:80]))
    results["official_samples"] = "%d/%d" % (ok, len(samples["samples"]))
    print("  -> %s\n" % results["official_samples"])

    print("=" * 72)
    print("B. 独立小规模真值（brute_force.py 全枚举，N ∈ {2,4,6}）")
    print("=" * 72)
    primes = [998244353, 924844033, 100000039]
    cases = [{"N": n, "P": p} for n in (2, 4, 6) for p in primes]
    t0 = time.perf_counter()
    brute = json.loads(subprocess.run(
        [sys.executable, str(BRUTE)], input=json.dumps(cases).encode(),
        stdout=subprocess.PIPE, timeout=600).stdout)
    bt = time.perf_counter() - t0
    ok = 0
    for case, exp in zip(cases, brute):
        got, dt = run_solution("%d %d" % (case["N"], case["P"]))
        want = " ".join(map(str, exp["answer"]))
        good = norm(got) == norm(want)
        anchor = A187.get(case["N"])
        anchor_ok = anchor is None or exp["connected_total"] == anchor
        good = good and anchor_ok
        ok += good
        all_ok &= good
        print("  N=%-2d P=%-10d %.3fs  枚举连通图=%-6d(A001187锚点:%s)  %s"
              % (case["N"], case["P"], dt, exp["connected_total"],
                 "ok" if anchor_ok else "MISMATCH",
                 "PASS" if good else "FAIL got=%r want=%r" % (got[:60], want[:60])))
    print("  （枚举器总耗时 %.1fs；解方逐组复跑比对）" % bt)
    results["brute_force"] = "%d/%d" % (ok, len(cases))
    print("  -> %s\n" % results["brute_force"])

    print("=" * 72)
    print("C. truth.json 全部 43 组（checker 同口径：subprocess + 10s 超时 + 按行 rstrip）")
    print("   ⚠ 该组仅证明与仓内夹具链一致（管路），不作为可解性独立证据")
    print("=" * 72)
    truth = json.loads(TRUTH.read_text())
    g = truth["problems"]["abc389_g"]
    tests = g["tests"]
    ok = 0
    times = []
    worst = None
    for i, t in enumerate(tests):
        try:
            got, dt = run_solution(t["input"])
            good = norm(got) == norm(t["output"])
        except subprocess.TimeoutExpired:
            got, dt, good = "", TIMEOUT_S, False
        times.append(dt)
        if worst is None or dt > worst[0]:
            worst = (dt, i, t["input"])
        ok += good
        all_ok &= good
        print("  #%02d %-7s %-12s %6.3fs  %s"
              % (i, t.get("source", "?"), t["input"], dt,
                 "PASS" if good else "FAIL"))
    results["truth"] = "%d/%d" % (ok, len(tests))
    results["timing"] = {
        "max_single_s": round(max(times), 3),
        "avg_s": round(sum(times) / len(times), 3),
        "total_s": round(sum(times), 3),
        "limit_s": TIMEOUT_S,
        "worst_case": {"index": worst[1], "input": worst[2], "seconds": round(worst[0], 3)},
        "n_values_covered": sorted({json.loads("[" + t["input"].replace(" ", ",") + "]")[0] for t in tests}),
    }
    print("  -> truth %s；单组最大 %.3fs（%s），累计 %.3fs"
          % (results["truth"], max(times), worst[2], sum(times)))
    print("  -> 计时 %s\n" % json.dumps(results["timing"], ensure_ascii=False))

    print("=" * 72)
    print("总结论: %s" % ("ALL PASS" if all_ok else "HAS FAILURES"))
    print("RESULTS_JSON " + json.dumps(
        {"all_ok": all_ok, "official_samples": results["official_samples"],
         "brute_force": results["brute_force"], "truth": results["truth"],
         "timing": results["timing"]}, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
