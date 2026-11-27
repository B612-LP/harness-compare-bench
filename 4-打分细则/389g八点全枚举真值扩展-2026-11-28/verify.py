#!/usr/bin/env python3
"""abc389_g N=8 full-enumeration truth extension (public recomputation).

Pipeline (PREREG n8-389g, 2026-11-28):
  P1  compile brute.c (from this directory) with cc -O2
  P2  calibration: brute(4) == official sample1 "12 9 3 0";
      brute(6) == official sample2 (11 values);
      independent Python full enumeration at N=6 == brute(6) per-M histogram
  P3  N=8 truth: brute(8) exact counts for M = 7..28
  P4  four pinned archives run three instances (N=8, P) with P in
      {998244353, 924844033, 100000007}; output must equal counts mod P
  P5  format: single space-separated line, exit 0, empty stderr

Run:  python3 -B verify.py        (zero arguments; requires cc in PATH)
Output: single JSON object, no timestamps; stdout is deterministic.
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_ROOT = "/Users/b612-lp/Documents/harness-compare-bench/3-表现现场/r20261125-five-lcb"
REPO = "/Users/b612-lp/Documents/harness-compare-bench"

ARCHIVES = {
    "codex": ("codex/solutions/abc389_g.py",
              "6abcbda98be451f1999898e2503e5b5086486abb7581e3869f20de4d13cf17fc"),
    "dsh": ("dsh/solutions/abc389_g.py",
            "e6ac90a8a434a3151d81eca69108f0b5b2e367bca56e68f7076f9dc872ee0615"),
    "doubao": ("doubao/solutions/abc389_g.py",
               "21ab73626e5960dc3297f08476267561edcd4ee1f58cc8f6370f81684c5a6959"),
    "yuanbao": ("yuanbao/abc389_g.py",
                "10dba9ebc139eaa4168b979745ef048f8814b58f786135a4698f35077590a384"),
}
PIN_SHA = {
    "2-用例/lcb-recent-hard-4/instruction.md":
        "1c39b2fa66982a7d54851e20822cb4064d8254122f2b047634b64fecdbd6045c",
    "2-用例/lcb-recent-hard-4/inputs/problems.json":
        "0ce2f9c1eee0039fa9cfc7cd9969d99118d3fba4ac41571c49d9f5289592a673",
}
for rel, want in ARCHIVES.values():
    PIN_SHA[rel] = want

SAMPLES = {  # official samples (abc389_g), asserted against pinned problems.json
    (4, 998244353): "12 9 3 0",
    (6, 924844033): "810 2100 3060 3030 2230 1210 450 100 10 0 0",
    # sample3 (10, 433416647) is not embedded: N=10 is beyond the enumeration
    # range of this page and its value is not used as an instance truth here.
}
N8_PS = [998244353, 924844033, 100000007]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def check_pins():
    pins = {}
    archive_rels = tuple(k.split("/")[0] for k in ARCHIVES)
    for rel, want in PIN_SHA.items():
        if rel.startswith(archive_rels):
            base = ARCHIVE_ROOT
        else:
            base = REPO
        got = sha256(os.path.join(base, rel))
        pins[rel] = "ok" if got == want else "MISMATCH:" + got
    return pins


def check_samples_vs_problems():
    """Assert embedded official samples equal the pinned problems.json texts."""
    with open(os.path.join(REPO, "2-用例/lcb-recent-hard-4/inputs/problems.json"),
              encoding="utf-8") as f:
        probs = json.load(f)["problems"]
    p389 = [p for p in probs if p.get("problem_id") == "abc389_g"][0]
    ok = True
    for s in p389["samples"]:
        n_pp = s["input"].split("\n")
        n, pp = (int(x) for x in n_pp[0].split())
        if (n, pp) in SAMPLES and SAMPLES[(n, pp)] != " ".join(s["output"].split("\n")):
            ok = False
    return ok


def compile_brute():
    exe = os.path.join(tempfile.gettempdir(), "brute389_verify")
    src = os.path.join(HERE, "brute.c")
    # the default SDK on this machine may be broken; fall back across candidates
    sdk_candidates = [None,
                      "/Library/Developer/CommandLineTools/SDKs/MacOSX15.4.sdk",
                      "/Library/Developer/CommandLineTools/SDKs/MacOSX15.sdk"]
    last = None
    for sdk in sdk_candidates:
        cmd = ["cc", "-O2", "-o", exe, src]
        if sdk:
            cmd += ["-isysroot", sdk]
        r = subprocess.run(cmd, capture_output=True, text=True)
        last = r
        if r.returncode == 0:
            return exe, "cc -O2" + ("" if not sdk else " -isysroot " + sdk)
    raise RuntimeError("brute.c compile failed: " + last.stderr[-500:])


def brute_counts(exe, n):
    out = subprocess.run([exe, str(n)], capture_output=True, text=True, timeout=600)
    if out.returncode != 0:
        raise RuntimeError("brute failed: " + out.stderr[-300:])
    return [int(x) for x in out.stdout.split()]


def python_enum_n6():
    """Independent N=6 enumeration (FIFO BFS; NOT derived from brute.c)."""
    n = 6
    E = n * (n - 1) // 2
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    cnt = [0] * (E + 1)
    for S in range(1 << E):
        if bin(S).count("1") < n - 1:
            continue
        adj = [0] * n
        s, k = S, 0
        while s:
            if s & 1:
                i, j = pairs[k]
                adj[i] |= 1 << j
                adj[j] |= 1 << i
            s >>= 1
            k += 1
        dist = [-1] * n
        dist[0] = 0
        q = [0]
        seen = 1
        qh = 0
        while qh < len(q):
            u = q[qh]
            qh += 1
            m = adj[u] & ~seen
            while m:
                v = (m & -m).bit_length() - 1
                m &= m - 1
                seen |= 1 << v
                dist[v] = dist[u] + 1
                q.append(v)
        if seen != (1 << n) - 1:
            continue
        even = sum(1 for d in dist if d % 2 == 0)
        if 2 * even == n:
            cnt[bin(S).count("1")] += 1
    return cnt[n - 1:E + 1]


def run_archive(name, rel, inp):
    path = os.path.join(ARCHIVE_ROOT, rel)
    try:
        r = subprocess.run([sys.executable, "-B", path], input=inp,
                           capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return {"exit": "TIMEOUT", "stdout": "", "stderr": ""}
    return {"exit": r.returncode, "stdout": r.stdout, "stderr": r.stderr}


def main():
    report = {}
    report["pins"] = check_pins()
    report["samples_vs_problems"] = check_samples_vs_problems()
    exe, cmd = compile_brute()
    report["compile"] = cmd

    cal = {}
    cal["brute4"] = " ".join(str(x) for x in brute_counts(exe, 4))
    cal["brute4_vs_sample1"] = cal["brute4"] == SAMPLES[(4, 998244353)]
    cal["brute6"] = " ".join(str(x) for x in brute_counts(exe, 6))
    cal["brute6_vs_sample2"] = cal["brute6"] == SAMPLES[(6, 924844033)]
    py6 = " ".join(str(x) for x in python_enum_n6())
    cal["python6"] = py6
    cal["python6_vs_brute6"] = py6 == cal["brute6"]
    report["calibration"] = cal

    n8 = brute_counts(exe, 8)
    report["n8_counts_exact"] = " ".join(str(x) for x in n8)
    report["n8_sum"] = sum(n8)

    instances = []
    totals = {"runs": 0, "match": 0, "format_fail": 0, "nonzero_exit": 0,
              "stderr_nonempty": 0}
    for p in N8_PS:
        truth = " ".join(str(x % p) for x in n8)
        inst = {"n": 8, "p": p, "truth": truth, "archives": {}}
        inp = "8 %d\n" % p
        for name, (rel, _sha) in ARCHIVES.items():
            r = run_archive(name, rel, inp)
            ok = (r["exit"] == 0 and r["stdout"] in (truth, truth + "\n")
                  and not r["stderr"].strip())
            totals["runs"] += 1
            if r["exit"] == 0:
                totals["match"] += 1 if ok else 0
                if r["stdout"] not in (truth, truth + "\n"):
                    totals["format_fail"] += 1
            else:
                totals["nonzero_exit"] += 1
            if r["stderr"].strip():
                totals["stderr_nonempty"] += 1
            inst["archives"][name] = "MATCH" if ok else \
                "MISMATCH:exit=%r out=%r" % (r["exit"], r["stdout"][:120])
        instances.append(inst)
    report["instances"] = instances
    report["totals"] = totals

    ok = (totals["runs"] == totals["match"]
          and totals["format_fail"] == 0 and totals["nonzero_exit"] == 0
          and totals["stderr_nonempty"] == 0
          and all(v == "ok" for v in report["pins"].values())
          and report["samples_vs_problems"] and cal["brute4_vs_sample1"]
          and cal["brute6_vs_sample2"] and cal["python6_vs_brute6"])
    report["verdict"] = "OK" if ok else "FAIL"
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
