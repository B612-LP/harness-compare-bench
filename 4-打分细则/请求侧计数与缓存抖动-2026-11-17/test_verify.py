#!/usr/bin/env python3
"""请求侧计数与缓存抖动 套件（合成档 + 真档分支）。"""
import hashlib
import importlib.util
import gzip
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "verify.py"
UV_ARCHIVE_BASE = os.environ.get("UV_ARCHIVE_BASE")


def load_module():
    spec = importlib.util.spec_from_file_location("uv_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def sse(usage):
    body = "data: {\"id\":\"synth\",\"usage\":" + json.dumps(usage, sort_keys=True) + "}\n\ndata: [DONE]\n"
    return body.encode("utf-8")


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = load_module()
        cls._real_snapshot = {
            name: getattr(cls.v, name) for name in
            ("REQ_SHAS", "REQ_BYTES", "PROMPT_TOKENS", "CACHED_SETS", "COMPLETION_SETS")}

    @classmethod
    def tearDownClass(cls):
        for name, value in cls._real_snapshot.items():
            setattr(cls.v, name, value)

    def make_synth(self, root):
        """合成8run×3请求档：同provider同seq请求字节恒等（真实结构），
        每run usage计数波动（响应侧不作字节pin）。"""
        made = {}
        for provider in ("glm", "ds"):
            runs = [k for k in self.v.RUN_LABELS if k.startswith(provider)]
            for run_index, run in enumerate(runs):
                d = root / self.v.RUN_RELS[run] / "responses"
                d.mkdir(parents=True, exist_ok=True)
                for idx in (1, 2, 3):
                    raw = ("req %s %d" % (provider, idx)).encode()
                    sha_hex = sha(raw)
                    prompt = 1000 * idx
                    cached = 0 if run_index % 2 == 0 else 777 * idx
                    completion = 7 + idx + (run_index % 3)
                    usage = {"prompt_tokens": prompt, "completion_tokens": completion,
                             "total_tokens": prompt + completion,
                             "prompt_tokens_details": {"cached_tokens": cached}}
                    if provider == "ds":
                        usage["prompt_cache_hit_tokens"] = cached
                        usage["prompt_cache_miss_tokens"] = prompt - cached
                    body = sse(usage)
                    gz = provider == "ds"
                    payload = gzip.compress(body) if gz else body
                    (d / ("%03d.response.bin" % idx)).write_bytes(payload)
                    (d / ("%03d.response.bin.meta.json" % idx)).write_text(json.dumps(
                        {"seq": idx, "request_body_sha256": sha_hex, "request_body_bytes": len(raw),
                         "upstream_status": 200, "response_body_sha256": sha(payload)}, sort_keys=True))
                    made.setdefault((provider, idx), {"sha": sha_hex, "bytes": len(raw),
                                                      "prompt": prompt, "completion": set(),
                                                      "cached": set()})
                    made[(provider, idx)]["completion"].add(completion)
                    made[(provider, idx)]["cached"].add(cached)
        return made

    def refresh(self, made):
        v = self.v
        v.REQ_BYTES = {"glm": [made[("glm", i)]["bytes"] for i in (1, 2, 3)],
                       "ds": [made[("ds", i)]["bytes"] for i in (1, 2, 3)]}
        v.PROMPT_TOKENS = {"glm": [made[("glm", i)]["prompt"] for i in (1, 2, 3)],
                           "ds": [made[("ds", i)]["prompt"] for i in (1, 2, 3)]}
        v.CACHED_SETS = {"glm": [made[("glm", i)]["cached"] for i in (1, 2, 3)],
                         "ds": [made[("ds", i)]["cached"] for i in (1, 2, 3)]}
        v.COMPLETION_SETS = {"glm": [made[("glm", i)]["completion"] for i in (1, 2, 3)],
                             "ds": [made[("ds", i)]["completion"] for i in (1, 2, 3)]}
        v.REQ_SHAS = {"glm": [made[("glm", i)]["sha"] for i in (1, 2)],
                      "ds": [made[("ds", i)]["sha"] for i in (1, 2)]}

    def build(self, root):
        ev = self.v.build(root)
        self.v.validate_public(ev)
        return ev


class Happy(Base):
    def test_01_build_validate(self):
        with tempfile.TemporaryDirectory() as td:
            made = self.make_synth(Path(td))
            self.refresh(made)
            ev = self.build(td)
            self.assertEqual(len(ev["rows"]), 24)
            self.assertEqual(ev["summary"]["prompt_tokens_stable_pairs"], 24)

    def test_02_result_binding(self):
        with tempfile.TemporaryDirectory() as td:
            made = self.make_synth(Path(td))
            self.refresh(made)
            ev = self.build(td)
            res = self.v.result_for(ev, self.v.sha(self.v.canon(ev)))
            self.assertEqual(res["verdict"], "usage_stable_cache_volatile")
            self.assertTrue(res["endpoints"]["e2_cached_tokens_volatile"])


class Tamper(Base):
    def _ev(self):
        with tempfile.TemporaryDirectory() as td:
            made = self.make_synth(Path(td))
            self.refresh(made)
            return self.build(td)

    def test_03_prompt_break(self):
        ev = self._ev()
        rows = json.loads(json.dumps(ev["rows"]))
        rows[0]["prompt_tokens"] += 1
        ev["rows"] = rows
        with self.assertRaises(ValueError):
            self.v.validate_public(ev)

    def test_04_cached_outside_set(self):
        ev = self._ev()
        ev["rows"][0]["cached_tokens"] = 999999
        with self.assertRaises(ValueError):
            self.v.validate_public(ev)

    def test_05_total_identity(self):
        ev = self._ev()
        ev["rows"][1]["total_tokens"] = 1
        with self.assertRaises(ValueError):
            self.v.validate_public(ev)

    def test_06_ds_mirror(self):
        ev = self._ev()
        for row in ev["rows"]:
            if row["run"] == "ds_r1" and row["seq"] == 1:
                row["prompt_cache_hit_tokens"] = row["cached_tokens"] + 1
        with self.assertRaises(ValueError):
            self.v.validate_public(ev)

    def test_07_glm_no_hitmiss(self):
        ev = self._ev()
        ev["rows"][0]["prompt_cache_hit_tokens"] = 0
        with self.assertRaises(ValueError):
            self.v.validate_public(ev)

    def test_08_dup_row(self):
        ev = self._ev()
        ev["rows"].append(dict(ev["rows"][0]))
        with self.assertRaises(ValueError):
            self.v.validate_public(ev)

    def test_09_sha_pin(self):
        ev = self._ev()
        for row in ev["rows"]:
            if row["seq"] == 1:
                row["request_body_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            self.v.validate_public(ev)

    def test_10_baseline(self):
        ev = self._ev()
        ev["baseline_commit"] = "0" * 40
        with self.assertRaises(ValueError):
            self.v.validate_public(ev)

    def test_11_leak(self):
        ev = self._ev()
        ev["rows"][0]["response_body_sha256"] = "/Users/someone/private"
        with self.assertRaises(ValueError):
            self.v.validate_public(ev)

    def test_12_nonfinite(self):
        with self.assertRaises(ValueError):
            self.v.loads('{"a": 1e999}')

    def test_13_dupkey(self):
        with self.assertRaises(ValueError):
            self.v.loads('{"a": 1, "a": 2}')

    def test_14_cached_volatility_witness_required(self):
        ev = self._ev()
        for key in ev["summary"]["cached_varies_runs"]:
            ev["summary"]["cached_varies_runs"][key] = [0]
        with self.assertRaises(ValueError):
            self.v.validate_public(ev)


class CLI(Base):
    def _run(self, *args):
        return subprocess.run([sys.executable, "-B", str(SCRIPT), *args],
                              capture_output=True, timeout=120)

    def test_20_cli_real_replay(self):
        real_ev = HERE / "evidence.json"
        real_res = HERE / "result.json"
        if not real_ev.exists():
            self.skipTest("real evidence not installed")
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "r.json"
            q = self._run("--evidence", str(real_ev), "--output", str(out))
            self.assertEqual(q.returncode, 0, q.stderr[:400])
            self.assertEqual(out.read_bytes(), real_res.read_bytes())

    def test_21_cli_real_build(self):
        if not UV_ARCHIVE_BASE:
            self.skipTest("UV_ARCHIVE_BASE not set")
        with tempfile.TemporaryDirectory() as td:
            evp, rp = Path(td) / "e.json", Path(td) / "r.json"
            q = self._run("--archive-base", UV_ARCHIVE_BASE, "--build-evidence", str(evp), "--output", str(rp))
            self.assertEqual(q.returncode, 0, q.stderr[:400])
            self.assertEqual(evp.read_bytes(), (HERE / "evidence.json").read_bytes())
            self.assertEqual(rp.read_bytes(), (HERE / "result.json").read_bytes())

    def test_22_cli_tampered_evidence_rc2(self):
        with tempfile.TemporaryDirectory() as td:
            made = self.make_synth(Path(td) / "arch")
            self.refresh(made)
            ev = self.v.build(Path(td) / "arch")
            ev["rows"][0]["prompt_tokens"] += 5
            bad = Path(td) / "bad.json"
            bad.write_text(json.dumps(ev))
            out = Path(td) / "o.json"
            q = self._run("--evidence", str(bad), "--output", str(out))
            self.assertEqual(q.returncode, 2)
            self.assertFalse(out.exists())

    def test_23_cli_output_exists_rc2(self):
        real_ev = HERE / "evidence.json"
        if not real_ev.exists():
            self.skipTest("real evidence not installed")
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "exists.json"
            out.write_bytes(b"x")
            q = self._run("--evidence", str(real_ev), "--output", str(out))
            self.assertEqual(q.returncode, 2)

    def test_24_cli_missing_evidence_arg(self):
        with tempfile.TemporaryDirectory() as td:
            q = self._run("--output", str(Path(td) / "o.json"))
            self.assertEqual(q.returncode, 2)

    def test_25_cli_build_needs_archive(self):
        with tempfile.TemporaryDirectory() as td:
            q = self._run("--build-evidence", str(Path(td) / "e.json"), "--output", str(Path(td) / "o.json"))
            self.assertEqual(q.returncode, 2)


if __name__ == "__main__":
    unittest.main()
