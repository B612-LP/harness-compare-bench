#!/usr/bin/env python3
"""abc388_g four-archive static correctness proof -- public recomputation.

Contract-legal inputs only (2<=N<=2e5, 1<=A_i<=1e9 ascending, 1<=Q<=2e5,
1<=L<R<=N).  Zero product runs; archived solutions are executed offline on
synthetic, legality-asserted inputs and their stdout is compared with truth
obtained from three independent tracks:
  - official expected outputs (pinned problems.json),
  - hand-derived checkpoints (registered in the private PREREG),
  - definition-level exhaustive matching on small windows (subset DP),
    cross-checked against a lemma-based independent implementation.
Run: python3 -B verify.py   (no arguments; deterministic, no timestamps).
"""
import hashlib
import json
import os
import random
import subprocess
import sys
from bisect import bisect_left

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
CASE = os.path.join(REPO, "2-用例", "lcb-recent-hard-4")
ARCHIVE_ROOT = "/Users/b612-lp/Documents/harness-compare-bench/3-表现现场/r20261125-five-lcb"

ARCHIVES = [
    ("codex", os.path.join(ARCHIVE_ROOT, "codex", "solutions", "abc388_g.py")),
    ("dsh", os.path.join(ARCHIVE_ROOT, "dsh", "solutions", "abc388_g.py")),
    ("doubao", os.path.join(ARCHIVE_ROOT, "doubao", "solutions", "abc388_g.py")),
    ("yuanbao", os.path.join(ARCHIVE_ROOT, "yuanbao", "abc388_g.py")),
]
PIN_SHA = {
    "instruction.md": "1c39b2fa66982a7d54851e20822cb4064d8254122f2b047634b64fecdbd6045c",
    "inputs/problems.json": "0ce2f9c1eee0039fa9cfc7cd9969d99118d3fba4ac41571c49d9f5289592a673",
    "codex/solutions/abc388_g.py": "959138871953840a3afaa73ea9578f52f47d2b968f8b2e75ab1ab122d7965b16",
    "dsh/solutions/abc388_g.py": "9c57caff3eecac28c9627c7e8101b63044e79c77b572ec5ec47ecd3c7cc71d77",
    "doubao/solutions/abc388_g.py": "c06fab5d468d79776846c3a14ca14dde0bc69706f9a5dc1b26517e70f2d1fc6f",
    "yuanbao/abc388_g.py": "b65eee963adca0b5fb563b3988dcf591c0d3626222eb0319dc856e6856b56d86",
}
SAMPLE_IDS = [1, 2]  # index into problems.json samples of abc388_g


def die(msg):
    raise RuntimeError(msg)


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def check_pins():
    pins = {}
    archive_rels = ("codex/", "dsh/", "doubao/", "yuanbao/")
    for rel, want in PIN_SHA.items():
        if rel.startswith(archive_rels):
            base = ARCHIVE_ROOT
        else:
            base = CASE  # statement files live under 2-用例/lcb-recent-hard-4/
        got = sha256(os.path.join(base, rel))
        pins[rel] = "ok" if got == want else "MISMATCH:" + got
    return pins


# ---------- truth track 1: definition-level exhaustive matching (small m) ----------
def brute_max_pairs(vals):
    """vals: list of sizes in a window (ascending). Max pairs (a,b), 2a<=b,
    each element used once.  Memoized subset DP over used-mask of bottoms+tops.
    Completely independent of the d/predicate theory."""
    m = len(vals)
    from functools import lru_cache

    @lru_cache(maxsize=None)
    def f(used):
        # find lowest unused index
        free = [i for i in range(m) if not (used >> i) & 1]
        if len(free) < 2:
            return 0
        i = free[0]
        best = 0
        for j in free[1:]:
            if 2 * vals[i] <= vals[j]:
                best = max(best, 1 + f(used | (1 << i) | (1 << j)))
        return max(best, f(used | (1 << i)))  # skip i as bottom
    return f(0)


# ---------- truth track 2: lemma-based independent implementation ----------
def theory_max_pairs(a, l, r):
    """a is 0-indexed ascending list; window 1-indexed [l, r] (l < r).
    K* = max k in [0, m//2] with max_{i<k} d[l-1+i] <= m-k  (lemmas G1-G5).
    d computed by direct scan (no bisect, independent of archive machinery)."""
    m = r - l + 1
    d = []
    for i in range(l - 1, r):
        nd = None
        for j in range(i + 1, r):
            if a[j] >= 2 * a[i]:
                nd = j - i
                break
        d.append(nd)  # None = infinity
    best = 0
    for k in range(1, m // 2 + 1):
        ok = True
        for i in range(k):
            if d[i] is None or d[i] > m - k:
                ok = False
                break
        if ok:
            best = k
        else:
            break  # predicate is monotone decreasing in k (G4)
    return best


def theory_max_pairs_fast(a, l, r):
    """Same lemma chain with bisect for d (used for the mid-size instance)."""
    m = r - l + 1
    d = []
    for i in range(l - 1, r):
        j = bisect_left(a, 2 * a[i], i + 1, r)
        d.append((j - i) if j < r else None)
    best = 0
    for k in range(1, m // 2 + 1):
        if all(d[i] is not None and d[i] <= m - k for i in range(k)):
            best = k
        else:
            break
    return best


def legality_ok(a, queries, nmax=2 * 10**5):
    if not (2 <= len(a) <= nmax):
        return False
    if any(not (1 <= v <= 10**9) for v in a):
        return False
    if any(a[i] > a[i + 1] for i in range(len(a) - 1)):
        return False
    if not queries:
        return False
    for (l, r) in queries:
        if not (1 <= l < r <= len(a)):
            return False
    return True


def run_archive(tag, path, inp, timeout):
    try:
        proc = subprocess.run(
            [sys.executable, "-B", path], input=inp.encode(),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"tag": tag, "timeout": True}
    out = proc.stdout.decode()
    err = proc.stderr.decode()
    lines = [ln.strip() for ln in out.strip("\n").split("\n")] if out.strip() else []
    ok_ints = all(ln.lstrip("-").isdigit() for ln in lines) if lines else False
    tail_nl = out.endswith("\n")
    return {
        "tag": tag, "rc": proc.returncode, "ints": [int(x) for x in lines] if ok_ints else None,
        "stderr_nonempty": bool(err.strip()), "tail_newline": tail_nl,
        "format_ok": ok_ints and proc.returncode == 0,
    }


def main():
    report = {}
    report["pins"] = check_pins()
    if any(v != "ok" for v in report["pins"].values()):
        die("pin mismatch: %s" % report["pins"])

    # official samples, cross-checked against pinned problems.json
    with open(os.path.join(CASE, "inputs", "problems.json"), encoding="utf-8") as f:
        pj = json.load(f)
    entry = [p for p in pj["problems"] if p["problem_id"] == "abc388_g"][0]
    samples = entry["samples"]
    if len(samples) != 2:
        die("unexpected sample count")
    sample_instances = []
    for si in SAMPLE_IDS:
        s = samples[si - 1]
        lines = s["input"].strip().split("\n")
        n = int(lines[0]); a = [int(x) for x in lines[1].split()]
        q = int(lines[2])
        qs = [tuple(int(x) for x in lines[3 + i].split()) for i in range(q)]
        want = [int(x) for x in s["output"].strip().split("\n")]
        if len(want) != q:
            die("sample %d output arity" % si)
        sample_instances.append({"name": "official-sample-%d" % si, "a": a, "queries": qs, "truth": want})

    # hand-derived checkpoints (private PREREG F3/F4)
    cp = []
    cp.append({"name": "cp-equal-8", "a": [7] * 8, "queries": [(1, 2), (1, 3), (1, 8), (4, 5)], "truth": [0, 0, 0, 0]})
    dbl = [2 ** i for i in range(20)]
    cp.append({"name": "cp-double-20", "a": dbl, "queries": [(1, 20), (5, 12), (2, 3), (19, 20)], "truth": [10, 4, 1, 1]})
    cp.append({"name": "cp-m2-yes", "a": [1, 2], "queries": [(1, 2)], "truth": [1]})
    cp.append({"name": "cp-m2-no", "a": [3, 5], "queries": [(1, 2)], "truth": [0]})
    cp.append({"name": "cp-mixed-114", "a": [1, 1, 2, 3], "queries": [(1, 4)], "truth": [2]})
    report["checkpoints"] = cp

    # large termination instance (PREREG F6 v1.1): doubling prefix capped at 30
    # by A_i<=1e9, constant tail 10**9.  Hand truths via upper bound
    # (bottoms must be <= 5e8, else their top would exceed 1e9; hence at most
    # 29 bottoms among 2^0..2^28) + explicit right-aligned construction.
    big = [2 ** i for i in range(30)] + [10 ** 9] * (200000 - 30)
    big_q = [(1, 60), (31, 1000), (1, 200000), (2, 31)]
    big_truth = [29, 0, 29, 15]  # (2,31): m=30 caps K at floor(30/2)=15 (v1 hand value 28 forgot the 2K<=m cap; archives unanimous & correct)
    big_inst = {"name": "large-200k", "a": big, "queries": big_q, "truth": big_truth}

    # mid-size instance, truth = lemma implementation (disclosed 4th track)
    rng = random.Random(20261128)
    mid = sorted(rng.randint(1, 10 ** 9) for _ in range(1000))
    mid_q = [(1, 1000), (100, 900), (500, 501), (400, 800)]
    mid_truth = [theory_max_pairs_fast(mid, l, r) for (l, r) in mid_q]
    mid_inst = {"name": "mid-1000", "a": mid, "queries": mid_q, "truth": mid_truth}

    # brute-generated small instances (PREREG BRUTE_GEN), truth = subset DP,
    # cross-checked against the lemma implementation.
    brute = []
    cross_pairs = 0
    cross_bad = 0
    for ai in range(8):
        n = rng.randint(4, 12)
        a = sorted(rng.randint(1, 6) for _ in range(n))
        ls = sorted(rng.sample(range(1, n), min(5, n - 1)))
        for l in ls:
            r = rng.randint(l + 1, n)
            vals = a[l - 1:r]
            t_brute = brute_max_pairs(vals)
            t_theory = theory_max_pairs(a, l, r)
            cross_pairs += 1
            if t_brute != t_theory:
                cross_bad += 1
            brute.append({"name": "brute-%02d-%d-%d" % (ai, l, r), "a": a, "queries": [(l, r)], "truth": [t_brute]})
    report["theory_vs_brute_cross"] = {"pairs": cross_pairs, "mismatches": cross_bad}
    if cross_bad:
        die("theory/brute cross mismatch %d" % cross_bad)

    instances = sample_instances + cp + [big_inst, mid_inst] + brute

    totals = {"runs": 0, "match": 0, "format_fail": 0, "nonzero_exit": 0,
              "stderr_nonempty": 0, "legality_fail": 0, "format_minor": 0}
    detail = []
    big_ms = {}
    for inst in instances:
        inp = "%d\n%s\n%d\n%s" % (
            len(inst["a"]), " ".join(map(str, inst["a"])), len(inst["queries"]),
            "\n".join("%d %d" % q for q in inst["queries"]))
        if not legality_ok(inst["a"], inst["queries"]):
            totals["legality_fail"] += 1
            detail.append({"name": inst["name"], "legality": False})
            continue
        row = {"name": inst["name"], "truth": inst["truth"], "archives": {}}
        timeout = 60 if inst["name"] == "large-200k" else 30
        for tag, path in ARCHIVES:
            res = run_archive(tag, path, inp, timeout)
            totals["runs"] += 1
            if res.get("timeout"):
                row["archives"][tag] = "TIMEOUT"
                totals["format_fail"] += 1
                continue
            if res["rc"] != 0:
                totals["nonzero_exit"] += 1
            if res["stderr_nonempty"]:
                totals["stderr_nonempty"] += 1
            if not res["format_ok"]:
                totals["format_fail"] += 1
            match = res["ints"] == inst["truth"]
            if match:
                totals["match"] += 1
            if not res["tail_newline"]:
                totals["format_minor"] += 1
            row["archives"][tag] = "MATCH" if match else "MISMATCH:" + json.dumps(res["ints"])
            if inst["name"] == "large-200k":
                big_ms[tag] = None  # runtime not recorded to keep output deterministic
        detail.append(row)

    report["totals"] = totals
    report["instances"] = len(instances)
    report["detail"] = detail
    report["verdict"] = "OK" if (totals["runs"] == totals["match"] and
                                 totals["format_fail"] == 0 and
                                 totals["nonzero_exit"] == 0 and
                                 totals["stderr_nonempty"] == 0 and
                                 totals["legality_fail"] == 0) else "FAIL"
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
