#!/usr/bin/env python3
"""abc388_f 四归档静态正确性证明 — 公开复算 (Ring E, until10-20261128-week5)

对象: 3-表现现场/r20261125-five-lcb 四归档 abc388_f.py (SHA256 钉定)。
真值来源 (互相独立于归档输出):
  - CHECKPOINTS: PREREG 预固定手推 (proof-abc388f/PREREG.md, 03:03 冻结先于映射);
  - SAMPLES: 官方样例 (题面公布期望), 与钉定 problems.json 逐字核对;
  - BRUTE_GEN: 种子化随机小实例, 真值 = 独立 BFS;
  - ACCEL: 大 N 加速路径触发实例, 真值 = 引理 C/D 手推 (推导注明)。
限定主张见 README: 契约合法输入上终止且输出真值; 不主张运行时效率等。
输出为确定性 JSON (无时间戳); python3 -B 与 -OB 双档字节同。
"""
import hashlib
import json
import random
import subprocess
import sys
from collections import deque
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

PROBLEM_PINS = {
    "instruction.md": (
        "2-用例/lcb-recent-hard-4/instruction.md",
        "1c39b2fa66982a7d54851e20822cb4064d8254122f2b047634b64fecdbd6045c",
    ),
    "problems.json": (
        "2-用例/lcb-recent-hard-4/inputs/problems.json",
        "0ce2f9c1eee0039fa9cfc7cd9969d99118d3fba4ac41571c49d9f5289592a673",
    ),
}

ARCHIVES = {
    "codex": (
        "3-表现现场/r20261125-five-lcb/codex/solutions/abc388_f.py",
        "d1702fae6ce60470007c3c124509da168ec1fcea7cb9614608d1812074ee8702",
    ),
    "dsh": (
        "3-表现现场/r20261125-five-lcb/dsh/solutions/abc388_f.py",
        "7297268ac7abb6c07a0c108c8fa2ae0d56c7acdef120bee6e615c615945b6c9e",
    ),
    "doubao": (
        "3-表现现场/r20261125-five-lcb/doubao/solutions/abc388_f.py",
        "67551b01b51cfc6738f1a10b3a587cd643be538a08f7891f1b15c7a6b35ebf14",
    ),
    "yuanbao": (
        "3-表现现场/r20261125-five-lcb/yuanbao/abc388_f.py",
        "6da7914ee9931843bc663745db02adfd1a9027b7ddf62c1730987546b0388fce",
    ),
}

# 官方样例 (题面公布期望; 运行时与钉定 problems.json 内 abc388_f.samples 逐字核对)
SAMPLES = [
    ("24 2 3 5\n7 8\n17 20\n", "Yes"),
    ("30 1 5 8\n4 24\n", "No"),
    ("100 4 10 11\n16 18\n39 42\n50 55\n93 99\n", "Yes"),
]

# PREREG 14 判定点: (label, (N, A, B, intervals), expected, 依据引理)
CHECKPOINTS = [
    ("E1a-eq-m0-yes", (7, 3, 3, []), "Yes", "D: 1->4->7"),
    ("E1b-eq-m0-no", (8, 3, 3, []), "No", "D: visited {1,4,7}"),
    ("E2a-eq-bad-hit", (10, 3, 3, [[4, 6]]), "No", "D: 1+3=4 坏"),
    ("E2b-eq-bad-miss", (10, 3, 3, [[5, 6]]), "Yes", "D: 1->4->7->10"),
    ("E3a-min-N", (2, 2, 3, []), "No", "A: 1+2>2"),
    ("E3b-min-yes", (3, 2, 3, []), "Yes", "A: 1->3"),
    ("E3c-jump", (4, 2, 3, []), "Yes", "A: 1->4 (d=3)"),
    ("E4-gap-ge-B", (10, 1, 2, [[4, 6]]), "No", "B(iii): gap=3>=B=2 全灭"),
    ("E5a-cross-yes", (12, 1, 2, [[4, 4]]), "Yes", "A/B: 3->5 跨格4"),
    ("E5b-over-one", (12, 1, 2, [[5, 5]]), "Yes", "A/B: 4->6 (d=2) 跳过5"),
    ("E5c-pair-dead", (12, 1, 2, [[6, 7]]), "No", "A: 可达 {1..5} 全堵"),
    ("E6a-d1-chain", (10 ** 12, 1, 2, []), "Yes", "A: d=1 逐格"),
    ("E6b-saturation", (10 ** 12, 5, 6, []), "Yes", "C: 块 [1+5t,1+6t] 增宽, t=5 得 6 连块 [26,31] => 其后全可达"),
    ("E6c-pre-sat", (10, 5, 6, []), "No", "A: 可达恰 {1,6,7}"),
]

# 大 N 加速路径触发实例 (真值 = 引理手推, 推导注明; 不跑暴力)
ACCEL = [
    ("accel-eq-7-yes", (10 ** 12, 7, 7, []), "Yes", "D: 7 | 10^12-1"),
    ("accel-eq-7-no", (10 ** 12 - 1, 7, 7, []), "No", "D: (10^12-2)%7=6"),
    ("accel-onecell", (10 ** 12, 1, 2, [[500, 500]]), "Yes", "B(iii)+A: 单坏格 499->501 (d=2)"),
    ("accel-gapbig", (10 ** 12, 1, 2, [[100, 200]]), "No", "B(iii): gap=101>=B=2"),
]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def make_input(n, a, b, intervals):
    lines = ["%d %d %d %d" % (n, len(intervals), a, b)]
    lines += ["%d %d" % (l, r) for l, r in intervals]
    return "\n".join(lines) + "\n"


def check_legality(n, a, b, intervals):
    ok = 2 <= n <= 10 ** 12 and 1 <= a <= b <= 20
    prev_r = 1
    for l, r in intervals:
        ok = ok and 1 < l <= r < n and l > prev_r
        prev_r = r
    return ok


def brute_truth(n, a, b, intervals):
    """独立 BFS 真值; N 过大返回 None。"""
    if n > 4000:
        return None
    bad = set()
    for l, r in intervals:
        bad.update(range(l, r + 1))
    seen = {1}
    q = deque([1])
    while q:
        x = q.popleft()
        for d in range(a, b + 1):
            y = x + d
            if y > n or y in bad or y in seen:
                continue
            seen.add(y)
            q.append(y)
    return "Yes" if n in seen else "No"


def evaluate(name, n, a, b, intervals, expected, basis, archives, results):
    inp = make_input(n, a, b, intervals)
    entry = {"legality": check_legality(n, a, b, intervals), "expected": expected,
             "basis": basis, "archives": {}}
    for arch, path in archives.items():
        proc = subprocess.run(
            [sys.executable, "-B", path],
            input=inp.encode("utf-8"),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60,
        )
        out = proc.stdout.decode("utf-8", "replace")
        err = proc.stderr.decode("utf-8", "replace")
        stripped = out.rstrip("\n")
        r = {
            "exit": proc.returncode,
            "stderr_nonempty": err.strip() != "",
            "format_ok": stripped in ("Yes", "No") and out.count("\n") <= 1,
            "content_ok": stripped == expected,
            "match": proc.returncode == 0 and err.strip() == ""
            and stripped == expected and out.count("\n") <= 1,
        }
        entry["archives"][arch] = r
    results[name] = entry
    return entry


def gen_brute_instances(count=30, seed=20261128):
    rng = random.Random(seed)
    out = []
    for i in range(count):
        if i % 3 == 0:
            a = b = rng.randint(1, 20)
        else:
            a = rng.randint(1, 19)
            b = rng.randint(a + 1, 20)
        n = rng.randint(2, 2000)
        m = rng.randint(0, 5) if n >= 3 else 0
        intervals = []
        tries = 0
        while len(intervals) < m and tries < 100:
            tries += 1
            l = rng.randint(2, n - 1)
            span = rng.randint(0, min(20, n - 1 - l))
            r = l + span
            if intervals and l <= intervals[-1][1]:
                continue
            intervals.append((l, r))
        out.append(("brute-%02d" % i, (n, a, b, intervals)))
    return out


def main():
    report = {}
    report["page"] = "abc388f滑窗可达四归档静态证明-2026-11-28"
    report["repo_root"] = str(REPO)

    # ---- pins ----
    pins = {}
    for key, (rel, want) in list(PROBLEM_PINS.items()) + [
        ("archive:" + k, v) for k, v in ARCHIVES.items()
    ]:
        got = sha256_file(REPO / rel)
        pins[key] = {"ok": got == want, "sha256": got}
    report["pins"] = pins
    pins_ok = all(v["ok"] for v in pins.values())

    # ---- samples vs problems.json ----
    probs = json.loads((REPO / PROBLEM_PINS["problems.json"][0]).read_text())
    entry = None
    for p in probs["problems"]:
        if p.get("problem_id") == "abc388_f":
            entry = p
            break
    embedded_match = entry is not None and [
        (s["input"] + "\n", s["output"]) for s in entry["samples"]
    ] == SAMPLES
    report["samples_embedded_match_problems_json"] = embedded_match

    archives = {k: str(REPO / v[0]) for k, v in ARCHIVES.items()}

    totals = {"runs": 0, "match": 0, "format_fail": 0, "nonzero_exit": 0,
              "stderr_nonempty": 0, "legality_fail": 0}
    mismatch_details = []

    def run_group(group_name, instances):
        per_arch = {a: {"total": 0, "match": 0} for a in archives}
        all_ok = True
        results = {}
        for name, (n, a, b, intervals), expected, basis in instances:
            entry = evaluate(name, n, a, b, intervals, expected, basis, archives, results)
            if not entry["legality"]:
                totals["legality_fail"] += 1
            for arch, r in entry["archives"].items():
                totals["runs"] += 1
                per_arch[arch]["total"] += 1
                if r["match"]:
                    totals["match"] += 1
                    per_arch[arch]["match"] += 1
                else:
                    all_ok = False
                    mismatch_details.append({"group": group_name, "name": name,
                                             "arch": arch, "result": r})
                if not r["format_ok"]:
                    totals["format_fail"] += 1
                if r["exit"] != 0:
                    totals["nonzero_exit"] += 1
                if r["stderr_nonempty"]:
                    totals["stderr_nonempty"] += 1
        return {"count": len(instances), "all_match": all_ok,
                "per_arch": per_arch, "results": results}

    # ---- checkpoints ----
    cp_instances = [(lbl, inst, exp, basis) for lbl, inst, exp, basis in CHECKPOINTS]
    report["checkpoints"] = run_group("checkpoints", cp_instances)

    # checkpoint 内部一致性: 小实例手推真值 vs 独立 BFS
    brute_agree, brute_n = 0, 0
    for lbl, (n, a, b, intervals), expected, _ in CHECKPOINTS:
        t = brute_truth(n, a, b, intervals)
        if t is not None:
            brute_n += 1
            if t == expected:
                brute_agree += 1
    report["checkpoints"]["brute_consistency"] = {
        "checked": brute_n, "agree": brute_agree}

    # ---- samples ----
    sample_instances = []
    for i, (inp, exp) in enumerate(SAMPLES):
        parts = inp.split()
        n, m, a, b = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
        iv = [(int(parts[4 + 2 * k]), int(parts[5 + 2 * k])) for k in range(m)]
        if make_input(n, a, b, iv) != inp:  # 显式检查（assert 在 -O 档被跳过）
            raise RuntimeError("sample-%d reconstruction mismatch" % i)
        sample_instances.append(("sample-%d" % i, (n, a, b, iv), exp, "题面公布期望"))
    report["samples"] = run_group("samples", sample_instances)

    # ---- brute generated ----
    brute_instances = []
    for name, (n, a, b, intervals) in gen_brute_instances():
        t = brute_truth(n, a, b, intervals)
        brute_instances.append((name, (n, a, b, intervals), t, "独立 BFS"))
    report["brute_generated"] = run_group("brute_generated", brute_instances)

    # ---- accel ----
    report["accel"] = run_group("accel", ACCEL)

    report["totals"] = totals
    report["mismatches"] = mismatch_details[:10]
    ok = (pins_ok and embedded_match
          and report["checkpoints"]["all_match"]
          and report["checkpoints"]["brute_consistency"]["agree"] == brute_n
          and report["samples"]["all_match"]
          and report["brute_generated"]["all_match"]
          and report["accel"]["all_match"]
          and totals["format_fail"] == 0 and totals["nonzero_exit"] == 0
          and totals["stderr_nonempty"] == 0 and totals["legality_fail"] == 0)
    report["verdict"] = "OK" if ok else "FAIL"
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
