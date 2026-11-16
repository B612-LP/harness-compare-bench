#!/usr/bin/env python3
"""Codex 响应侧计数与缓存抖动 verify.py 的 13 项自检。

真档用例需 CXUSAGE_TEST_ROOT 指向包含 until14-20261117 私档的父目录；
未设置时 2 个真档用例 skip（skip=2）。
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
ROOT = os.environ.get("CXUSAGE_TEST_ROOT") or REPO
VERIFY = os.path.join(HERE, "verify.py")

REAL_BASE = os.environ.get("CXUSAGE_TEST_ROOT")


def run_cli(argv):
    p = subprocess.run([sys.executable, "-B", VERIFY] + argv, capture_output=True, timeout=300)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def sse_response(usage):
    usage = dict(usage)
    usage.setdefault("input_tokens_details", {"cached_tokens": 0})
    usage.setdefault("output_tokens_details", {"reasoning_tokens": 0})
    events = [
        {"type": "response.created", "response": {"id": "x", "usage": None}},
        {"type": "response.completed", "usage": usage},
    ]
    return b"".join(b"event: e\ndata: " + json.dumps(e).encode() + b"\n\n" for e in events)


class Common(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="uxcase-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)


class CliBasics(Common):
    def test_missing_output_rejected(self):
        rc, _, err = run_cli(["--root", REPO])
        self.assertEqual(rc, 2)

    def test_output_must_be_exclusive(self):
        out = os.path.join(self.tmp, "r.json")
        open(out, "wb").write(b"x")
        rc, _, _ = run_cli(["--root", REPO, "--output", out])
        self.assertEqual(rc, 2)

    def test_missing_evidence_path(self):
        rc, _, _ = run_cli(["--root", REPO, "--evidence", os.path.join(self.tmp, "no.json"),
                            "--output", os.path.join(self.tmp, "r.json")])
        self.assertEqual(rc, 2)


class RealPackage(Common):
    REAL = False

    def setUp(self):
        super().setUp()
        if REAL_BASE:
            self.REAL = True

    def test_10_public_replay_identical_both_modes(self):
        if not self.REAL:
            self.skipTest("real package requires CXUSAGE_TEST_ROOT")
        out = os.path.join(self.tmp, "r.json")
        rc, _, err = run_cli(["--root", REPO, "--output", out])
        self.assertEqual(rc, 0, err)
        want = open(os.path.join(HERE, "result.json"), "rb").read()
        self.assertEqual(open(out, "rb").read(), want)
        ev = os.path.join(self.tmp, "e.json")
        rc, _, err = run_cli(["--root", REPO, "--archive-root", REAL_BASE,
                              "--build-evidence", ev, "--output", out + "2"])
        self.assertEqual(rc, 0, err)
        self.assertEqual(open(ev, "rb").read(), open(os.path.join(HERE, "evidence.json"), "rb").read())
        self.assertEqual(open(out + "2", "rb").read(), want)

    def test_34_real_chain_bindings(self):
        if not self.REAL:
            self.skipTest("real package requires CXUSAGE_TEST_ROOT")
        result = json.load(open(os.path.join(HERE, "result.json")))
        eps = result["endpoints"]
        self.assertEqual(eps["e1_input_equal_pairs"], 2)
        self.assertEqual(eps["e2_cached_differ_pairs"], 2)
        self.assertEqual(result["verdict"], "usage_stable_cache_volatile_codex_side")
        self.assertEqual(len(eps["chain_deltas"]), 7)  # 2+1+2+2


class Synthetic(Common):
    def _payload(self, rows=None):
        ev = json.load(open(os.path.join(HERE, "evidence.json")))
        ev = copy.deepcopy(ev)
        if rows is not None:
            ev["rows"] = rows
        return json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8") + b"\n"

    def test_11_tampered_row_rejected(self):
        ev = json.load(open(os.path.join(HERE, "evidence.json")))
        rows = copy.deepcopy(ev["rows"])
        rows[0]["input_tokens"] += 1
        evp = os.path.join(self.tmp, "e.json")
        open(evp, "wb").write(self._payload(rows))
        rc, _, _ = run_cli(["--root", REPO, "--evidence", evp,
                            "--output", os.path.join(self.tmp, "r.json")])
        self.assertEqual(rc, 2)

    def test_12_dropped_row_rejected(self):
        ev = json.load(open(os.path.join(HERE, "evidence.json")))
        rows = copy.deepcopy(ev["rows"])[:-1]
        evp = os.path.join(self.tmp, "e.json")
        open(evp, "wb").write(self._payload(rows))
        rc, _, _ = run_cli(["--root", REPO, "--evidence", evp,
                            "--output", os.path.join(self.tmp, "r.json")])
        self.assertEqual(rc, 2)

    def test_13_bool_int_rejected(self):
        ev = json.load(open(os.path.join(HERE, "evidence.json")))
        rows = copy.deepcopy(ev["rows"])
        rows[2]["cached_tokens"] = True
        evp = os.path.join(self.tmp, "e.json")
        open(evp, "wb").write(self._payload(rows))
        rc, _, _ = run_cli(["--root", REPO, "--evidence", evp,
                            "--output", os.path.join(self.tmp, "r.json")])
        self.assertEqual(rc, 2)

    def test_14_bad_sha_format_rejected(self):
        ev = json.load(open(os.path.join(HERE, "evidence.json")))
        rows = copy.deepcopy(ev["rows"])
        rows[4]["response_sha256"] = "z" * 64
        evp = os.path.join(self.tmp, "e.json")
        open(evp, "wb").write(self._payload(rows))
        rc, _, _ = run_cli(["--root", REPO, "--evidence", evp,
                            "--output", os.path.join(self.tmp, "r.json")])
        self.assertEqual(rc, 2)

    def test_15_wrong_binding_rejected(self):
        ev = json.load(open(os.path.join(HERE, "evidence.json")))
        ev["bindings"]["t1_evidence_sha256"] = "0" * 64
        evp = os.path.join(self.tmp, "e.json")
        open(evp, "wb").write(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True).encode() + b"\n")
        rc, _, _ = run_cli(["--root", REPO, "--evidence", evp,
                            "--output", os.path.join(self.tmp, "r.json")])
        self.assertEqual(rc, 2)

    def test_16_sse_parser_unit(self):
        sys.path.insert(0, HERE)
        import verify as v
        u = {"input_tokens": 5, "output_tokens": 2, "total_tokens": 7}
        self.assertEqual(v.usage_of_response(sse_response(u))["input_tokens"], 5)
        self.assertEqual(v.usage_of_response(json.dumps({"usage": u}).encode())["total_tokens"], 7)
        self.assertIsNone(v.usage_of_response(b"event: e\ndata: {\"type\": \"other\"}\n\n"))

    def test_17_endpoint_math(self):
        sys.path.insert(0, HERE)
        import verify as v
        ev = json.load(open(os.path.join(HERE, "evidence.json")))
        t1 = json.load(open(os.path.join(REPO, "4-打分细则/Codex请求侧最小捕获-2026-11-17/evidence.json")))
        t3 = json.load(open(os.path.join(REPO, "4-打分细则/Codex深链与加密推理回放-2026-11-17/evidence.json")))
        pub = {"codex-t1": t1["runs"], "codex-t3": t3["runs"]}
        eps = v.endpoints(ev["rows"], pub)
        self.assertEqual(eps["e1_total"], 2)
        self.assertEqual(len(eps["chain_deltas"]), 7)
        self.assertEqual(v.verdict_for(eps), "usage_stable_cache_volatile_codex_side")

    def test_18_nonfinite_rejected(self):
        evp = os.path.join(self.tmp, "e.json")
        open(evp, "wb").write(b"{\"a\": 1e999}")
        rc, _, _ = run_cli(["--root", REPO, "--evidence", evp,
                            "--output", os.path.join(self.tmp, "r.json")])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
