#!/usr/bin/env python3
"""abc389_g four-archive static-correctness proof: public recomputation page.

Zero-argument, deterministic, no timestamps; `python3 -B verify.py` and
`python3 -B -O verify.py` print byte-identical JSON.

Truth machinery (all three written from the proof lemmas, independent of the
archives):
  1. brute   : definition-level full enumeration (N <= 6)
  2. direct  : dense edge-count generating function (H1-H4)
  3. thin    : potential-pair GF + C(W,M) smoothing, i.e. T(1+x) (H5)
Cross-checked against each other, the two official samples, and the four
pinned archives on 9 (N, P) instances.
"""
import hashlib
import json
import math
import os
import subprocess
import sys
from itertools import combinations

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
CASE = os.path.join(REPO, "2-用例", "lcb-recent-hard-4")
ARCHIVE_BASE = os.path.join(REPO, "3-表现现场", "r20261125-five-lcb")

PIN_SHA = {
    "instruction.md": (
        os.path.join(CASE, "instruction.md"),
        "1c39b2fa66982a7d54851e20822cb4064d8254122f2b047634b64fecdbd6045c",
    ),
    "inputs/problems.json": (
        os.path.join(CASE, "inputs", "problems.json"),
        "0ce2f9c1eee0039fa9cfc7cd9969d99118d3fba4ac41571c49d9f5289592a673",
    ),
    "codex/solutions/abc389_g.py": (
        os.path.join(ARCHIVE_BASE, "codex", "solutions", "abc389_g.py"),
        "6abcbda98be451f1999898e2503e5b5086486abb7581e3869f20de4d13cf17fc",
    ),
    "dsh/solutions/abc389_g.py": (
        os.path.join(ARCHIVE_BASE, "dsh", "solutions", "abc389_g.py"),
        "e6ac90a8a434a3151d81eca69108f0b5b2e367bca56e68f7076f9dc872ee0615",
    ),
    "doubao/solutions/abc389_g.py": (
        os.path.join(ARCHIVE_BASE, "doubao", "solutions", "abc389_g.py"),
        "21ab73626e5960dc3297f08476267561edcd4ee1f58cc8f6370f81684c5a6959",
    ),
    "yuanbao/abc389_g.py": (
        os.path.join(ARCHIVE_BASE, "yuanbao", "abc389_g.py"),
        "10dba9ebc139eaa4168b979745ef048f8814b58f786135a4698f35077590a384",
    ),
}

ARCHIVES = {
    "codex": "codex/solutions/abc389_g.py",
    "dsh": "dsh/solutions/abc389_g.py",
    "doubao": "doubao/solutions/abc389_g.py",
    "yuanbao": "yuanbao/abc389_g.py",
}

SAMPLES = {
    (4, 998244353): "12 9 3 0",
    (6, 924844033): "810 2100 3060 3030 2230 1210 450 100 10 0 0",
}

INSTANCES = [
    (N, P)
    for N in (4, 6, 8)
    for P in (998244353, 924844033, 999999937)
]

TIMEOUT = 120


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_pins():
    pins = {}
    for name, (path, want) in PIN_SHA.items():
        got = sha256(path)
        pins[name] = "ok" if got == want else "MISMATCH:" + got
    return pins


def load_problems_samples():
    with open(PIN_SHA["inputs/problems.json"][0], encoding="utf-8") as f:
        data = json.load(f)
    entry = [p for p in data["problems"] if p.get("problem_id") == "abc389_g"][0]
    out = {}
    for s in entry["samples"]:
        toks = s["input"].split()
        n, p = int(toks[0]), int(toks[1])
        out[(n, p)] = " ".join(s["output"].split())
    return out


# ---------------------------------------------------------------- truth rails
def brute_counts(n):
    """Definition-level enumeration; vertex 0 is the root. Even N <= 6."""
    verts = list(range(1, n))
    counts = {}
    for mask in range(1 << (n * (n - 1) // 2)):
        edges = []
        idx = 0
        for i, j in combinations(range(n), 2):
            if mask >> idx & 1:
                edges.append((i, j))
            idx += 1
        if not edges:
            continue
        adj = {v: set() for v in range(n)}
        for i, j in edges:
            adj[i].add(j)
            adj[j].add(i)
        seen = {0}
        queue = [0]
        dist = {0: 0}
        while queue:
            v = queue.pop(0)
            for w in adj[v]:
                if w not in seen:
                    seen.add(w)
                    dist[w] = dist[v] + 1
                    queue.append(w)
        if len(seen) != n:
            continue
        if sum(1 for v in range(n) if dist[v] % 2 == 0) * 2 != n:
            continue
        m = len(edges)
        counts[m] = counts.get(m, 0) + 1
    return counts


def _conv(f, g):
    out = [0] * (len(f) + len(g) - 1)
    for i, a in enumerate(f):
        if a:
            for j, b in enumerate(g):
                if b:
                    out[i + j] += a * b
    return out


def direct_gf(n):
    """Dense edge-count GF from lemmas H1-H4. Returns {M: exact count}."""
    half = n // 2
    maxe = n * (n - 1) // 2
    # state (last, used, par, even) -> dense list
    dp = {(1, 1, 0, 1): [1]}
    for used in range(1, n):
        nxt = {}
        for (a, u, par, ev), poly in dp.items():
            if u == n:
                tgt = nxt.get((a, u, par, ev))
                if tgt is None:
                    nxt[(a, u, par, ev)] = dict(poly) if isinstance(poly, dict) else list(poly)
                elif isinstance(poly, dict):
                    for w, c in poly.items():
                        tgt[w] = tgt.get(w, 0) + c
                else:
                    if len(poly) > len(tgt):
                        tgt.extend([0] * (len(poly) - len(tgt)))
                    for i, x in enumerate(poly):
                        tgt[i] += x
                continue
            rem = n - u
            for s in range(1, rem + 1):
                newpar = 1 - par
                ne = ev + (s if newpar == 0 else 0)
                no = (u + s) - ne
                if ne > half or no > half:
                    continue
                choose = math.comb(rem, s)
                intra = [math.comb(s * (s - 1) // 2, k)
                         for k in range(s * (s - 1) // 2 + 1)]
                cover = [0] * (a * s + 1)
                for j in range(s + 1):
                    sign = math.comb(s, j) * (-1) ** (s - j)
                    if sign:
                        aj = a * j
                        for k in range(min(aj, a * s) + 1):
                            c = math.comb(aj, k) if k <= aj else 0
                            cover[k] += sign * c
                trans = _conv(intra, cover)
                if len(trans) > maxe + 1:
                    trans = trans[:maxe + 1]
                full = [x * choose for x in _conv(poly, trans)]
                key = (s, u + s, newpar, ne)
                tgt = nxt.get(key)
                if tgt is None:
                    nxt[key] = full
                else:
                    if len(full) > len(tgt):
                        tgt.extend([0] * (len(full) - len(tgt)))
                    for i, x in enumerate(full):
                        tgt[i] += x
        dp = nxt
    total = [0] * (maxe + 1)
    for (a, u, par, ev), poly in dp.items():
        if ev != half:
            continue
        for i, x in enumerate(poly):
            total[i] += x
    return {m: total[m] for m in range(n - 1, maxe + 1) if total[m]}


def thin_gf(n):
    """Potential-pair GF (H5 thin form) + C(W, M) smoothing."""
    half = n // 2
    maxe = n * (n - 1) // 2
    dp = {(1, 1, 0, 1): {0: 1}}
    for used in range(1, n):
        nxt = {}
        for (a, u, par, ev), poly in dp.items():
            if u == n:
                tgt = nxt.get((a, u, par, ev))
                if tgt is None:
                    nxt[(a, u, par, ev)] = dict(poly) if isinstance(poly, dict) else list(poly)
                elif isinstance(poly, dict):
                    for w, c in poly.items():
                        tgt[w] = tgt.get(w, 0) + c
                else:
                    if len(poly) > len(tgt):
                        tgt.extend([0] * (len(poly) - len(tgt)))
                    for i, x in enumerate(poly):
                        tgt[i] += x
                continue
            rem = n - u
            for s in range(1, rem + 1):
                newpar = 1 - par
                ne = ev + (s if newpar == 0 else 0)
                no = (u + s) - ne
                if ne > half or no > half:
                    continue
                choose = math.comb(rem, s)
                monos = []
                base = s * (s - 1) // 2
                for j in range(s + 1):
                    sign = math.comb(s, j) * (-1) ** (s - j)
                    if sign:
                        monos.append((base + a * j, sign))
                key = (s, u + s, newpar, ne)
                tgt = nxt.setdefault(key, {})
                for w, c in poly.items():
                    for sh, mc in monos:
                        t = tgt.setdefault(w + sh, 0)
                        tgt[w + sh] = t + c * mc * choose
        dp = nxt
    thin = {}
    for (a, u, par, ev), poly in dp.items():
        if ev != half:
            continue
        for w, c in poly.items():
            thin[w] = thin.get(w, 0) + c
    out = {}
    for m in range(n - 1, maxe + 1):
        acc = 0
        for w, c in thin.items():
            if w >= m:
                acc += c * math.comb(w, m)
        if acc:
            out[m] = acc
    return out


# ------------------------------------------------------------------- archive
def run_archive(rel, n, p):
    path = os.path.join(ARCHIVE_BASE, rel)
    try:
        proc = subprocess.run(
            [sys.executable, "-B", path],
            input=("%d %d\n" % (n, p)).encode(),
            capture_output=True,
            timeout=TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return None, "TIMEOUT", ""
    return proc.returncode, proc.stdout.decode(), proc.stderr.decode()


def limb_certificate():
    p = 999999937
    n = 30
    maxe = n * (n - 1) // 2
    limbs = maxe + 1
    prod_bound = limbs * (p - 1) ** 2
    add_bound = (n * (n // 2 + 1)) * (p - 1)
    return {
        "n": n,
        "p": p,
        "max_limbs": limbs,
        "prod_bound": prod_bound,
        "dsh_width_2pow72": 2 ** 72,
        "yuanbao_width_2pow80": 2 ** 80,
        "dsh_safe": prod_bound < 2 ** 72,
        "yuanbao_safe": prod_bound < 2 ** 80,
        "add_bound": add_bound,
        "add_safe_dsh": add_bound < 2 ** 72,
        "add_safe_yuanbao": add_bound < 2 ** 80,
    }


def main():
    report = {}
    report["pins"] = check_pins()
    pins_ok = all(v == "ok" for v in report["pins"].values())

    official = load_problems_samples()
    samples_ok = all(official.get(k) == v for k, v in SAMPLES.items())
    report["samples_vs_problems"] = samples_ok

    # three-way truth cross-check (exact integers)
    threeway = []
    for n in (2, 4, 6):
        b = brute_counts(n)
        d = direct_gf(n)
        t = thin_gf(n)
        ms = sorted(set(b) | set(d) | set(t))
        row = {
            "n": n,
            "mismatch": 0,
            "detail": {str(m): [b.get(m, 0), d.get(m, 0), t.get(m, 0)]
                       for m in ms},
        }
        for m in ms:
            if not (b.get(m, 0) == d.get(m, 0) == t.get(m, 0)):
                row["mismatch"] += 1
        threeway.append(row)
    report["threeway_cross"] = threeway
    threeway_ok = all(r["mismatch"] == 0 for r in threeway)

    # gf-vs-official on sample instances
    gf_vs_samples = {}
    for (n, p), want in SAMPLES.items():
        d = direct_gf(n)
        got = " ".join(str(d.get(m, 0) % p) for m in range(n - 1, n * (n - 1) // 2 + 1))
        gf_vs_samples["%d/%d" % (n, p)] = "ok" if got == want else "MISMATCH:" + got
    report["gf_vs_samples"] = gf_vs_samples
    gf_samples_ok = all(v == "ok" for v in gf_vs_samples.values())

    # archives on 9 instances vs direct GF mod P
    totals = {"runs": 0, "match": 0, "format_fail": 0, "nonzero_exit": 0,
              "stderr_nonempty": 0, "timeout": 0}
    detail = []
    for (n, p) in INSTANCES:
        d = direct_gf(n)
        expected = " ".join(str(d.get(m, 0) % p)
                            for m in range(n - 1, n * (n - 1) // 2 + 1))
        for name, rel in ARCHIVES.items():
            code, out, err = run_archive(rel, n, p)
            totals["runs"] += 1
            row = {"instance": "%d/%d" % (n, p), "archive": name}
            if out is None:
                totals["timeout"] += 1
                row["result"] = "TIMEOUT"
                detail.append(row)
                continue
            body = out.rstrip("\n")
            fmt_ok = out in (expected + "\n", expected)
            match = body == expected
            if fmt_ok:
                totals["match"] += 1
            else:
                totals["format_fail"] += 1
            if code != 0:
                totals["nonzero_exit"] += 1
            if err.strip():
                totals["stderr_nonempty"] += 1
            row["result"] = ("MATCH" if match and fmt_ok
                             else "MISMATCH:" + body[:120])
            row["exit"] = code
            row["stderr_nonempty"] = bool(err.strip())
            detail.append(row)
    report["totals"] = totals
    report["detail"] = detail

    report["limb_certificate"] = limb_certificate()

    verdict_components = {
        "pins": pins_ok,
        "samples": samples_ok,
        "threeway": threeway_ok,
        "gf_vs_samples": gf_samples_ok,
        "runs_all_match": (totals["runs"] == len(INSTANCES) * len(ARCHIVES)
                           and totals["match"] == totals["runs"]
                           and totals["format_fail"] == 0
                           and totals["nonzero_exit"] == 0
                           and totals["stderr_nonempty"] == 0
                           and totals["timeout"] == 0),
        "limb_safe": report["limb_certificate"]["dsh_safe"]
        and report["limb_certificate"]["yuanbao_safe"]
        and report["limb_certificate"]["add_safe_dsh"]
        and report["limb_certificate"]["add_safe_yuanbao"],
    }
    report["verdict_components"] = verdict_components
    report["verdict"] = "OK" if all(verdict_components.values()) else "FAIL"
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
