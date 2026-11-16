#!/usr/bin/env python3
"""Adversarial suite for the cross-day re-check package.

Synthetic six-run archive; all frozen constants are derived from a clean
synthetic build and patched onto the module, so the checks have real
constraint power on the fixture (tamper tests mutate the archive against
those constants). The real-evidence replay branch activates only when the
installed package carries evidence.json (module file is located via
XD_TEST_ROOT or the script directory). Tests never touch the repo tree.
"""
import copy, hashlib, json, os, re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST_ROOT = Path(os.environ.get("XD_TEST_ROOT") or HERE)
sys.path.insert(0, str(TEST_ROOT))
import verify as v  # noqa: E402
REAL_CONSTS = {k: getattr(v, k) for k in ("REQ1_SHA", "REQ2_SHA", "REQ3_DELTA", "APPENDED_SHAPES", "WORKSPACE_FILES")}

def canon(o):
    return json.dumps(o, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()

def sha(b):
    return hashlib.sha256(b).hexdigest()

def synth_archive(base):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import random
    random.seed(7)
    def cid():
        return "call_" + "".join(random.choice("0123456789abcdef") for _ in range(24))
    def step():
        a = {"role": "assistant", "content": None,
             "tool_calls": [
                 {"id": cid(), "type": "function",
                  "function": {"name": "read", "arguments": "{\"p\":\"TASK.md\"}"}},
                 {"id": cid(), "type": "function",
                  "function": {"name": "read", "arguments": "{\"p\":\"x.py\"}"}}]}
        ts = [{"role": "tool", "tool_call_id": a["tool_calls"][0]["id"], "content": "T" * 60},
              {"role": "tool", "tool_call_id": a["tool_calls"][1]["id"], "content": "W" * 30}]
        return [a, *ts]
    sys_r = {"role": "system", "content": "S" * 30}
    usr = {"role": "user", "content": "U" * 40}
    asst = {"role": "assistant", "content": None,
            "tool_calls": [{"id": cid(), "type": "function",
                            "function": {"name": "read", "arguments": "{\"p\":\"TASK.md\"}"}}]}
    tool = {"role": "tool", "tool_call_id": asst["tool_calls"][0]["id"], "content": "T" * 60}
    for label in ("r1", "r2", "r3", "r4", "r5", "r6"):
        d = base / v.RUN_RELS[label] / "requests"
        d.mkdir(parents=True, exist_ok=True)
        req1 = {"model": "glm-5.3-flash", "messages": [sys_r, usr], "max_tokens": 128000}
        req2 = {"model": "glm-5.3-flash", "messages": [{"role": "system", "content": "T"},
                                                        {"role": "user", "content": "title"}],
                "max_tokens": 4096}
        req3 = {"model": "glm-5.3-flash",
                "messages": [copy.deepcopy(req1["messages"][0]), copy.deepcopy(req1["messages"][1]),
                             *step()],
                "max_tokens": 128000}
        for idx, body in ((1, req1), (2, req2), (3, req3)):
            (d / ("%03d.request.bin" % idx)).write_bytes(canon(body))

def refresh_constants():
    ev, _per = v.build(BASE)
    v.REQ1_SHA = sha((BASE / v.RUN_RELS["r1"] / "requests" / "001.request.bin").read_bytes())
    v.REQ2_SHA = sha((BASE / v.RUN_RELS["r1"] / "requests" / "002.request.bin").read_bytes())
    r6 = ev["runs"]["r6"]
    v.REQ3_DELTA = r6["req3_delta_bytes"]
    v.APPENDED_SHAPES = r6["appended_shapes"]
    return ev

BASE = None

class Base(unittest.TestCase):
    def setUp(self):
        global BASE
        if BASE is None:
            BASE = Path(tempfile.mkdtemp(prefix="xd-base-"))
            synth_archive(BASE)
        self.ev = refresh_constants()
        self.tmp = Path(tempfile.mkdtemp(prefix="xd-t-"))

class BuildAndTamper(Base):
    def test_01_happy_build(self):
        ev, per = v.build(BASE)
        self.assertEqual(per["r6"]["req3_delta_bytes"], v.REQ3_DELTA)
        self.assertTrue(ev["cross_day"]["req1_byte_equal_vs_r1"])
    def _guard(self, mutate):
        d = BASE / v.RUN_RELS["r6"] / "requests"
        p003 = d / "003.request.bin"
        old3 = p003.read_bytes()
        p001 = d / "001.request.bin"
        old1 = p001.read_bytes()
        try:
            mutate(d)
            with self.assertRaises(ValueError):
                v.main(["--archive-base", str(BASE), "--build-evidence",
                        str(self.tmp / "e.json"), "--output", str(self.tmp / "r.json")])
        finally:
            p003.write_bytes(old3)
            p001.write_bytes(old1)
    def test_02_tamper_req1_r6(self):
        def mut(d):
            raw = (d / "001.request.bin").read_bytes()
            (d / "001.request.bin").write_bytes(raw[:-1] + (b" " if raw[-1:] != b" " else b"x"))
        self._guard(mut)
    def test_03_tamper_req3_leaf_value(self):
        def mut(d):
            body = json.loads((d / "003.request.bin").read_bytes().decode())
            body["messages"][3]["content"] = "X" * 61
            (d / "003.request.bin").write_bytes(canon(body))
        self._guard(mut)
    def test_04_tamper_prefix_mid(self):
        def mut(d):
            body = json.loads((d / "003.request.bin").read_bytes().decode())
            body["messages"][0]["content"] = "S" * 29
            (d / "003.request.bin").write_bytes(canon(body))
        self._guard(mut)
    def test_05_tamper_call_id_noncall(self):
        d = BASE / v.RUN_RELS["r6"] / "requests"
        p = d / "003.request.bin"
        old = p.read_bytes()
        try:
            body = json.loads(p.read_bytes().decode())
            body["messages"][2]["tool_calls"][0]["id"] = "call_" + "z" * 23 + "!"
            p.write_bytes(canon(body))
            ev, _ = v.build(BASE)
            self.assertFalse(ev["cross_day"]["pairs"][-1]["leaves_all_call_id"])
            ep = self.tmp / "e.json"
            ep.write_bytes(canon(ev) + b"\n")
            with self.assertRaises(ValueError):
                v.main(["--evidence", str(ep), "--output", str(self.tmp / "r.json")])
        finally:
            p.write_bytes(old)
    def test_06_delta_change_via_content_len(self):
        def mut(d):
            body = json.loads((d / "003.request.bin").read_bytes().decode())
            body["messages"][3]["content"] = "T" * 61
            (d / "003.request.bin").write_bytes(canon(body))
        self._guard(mut)

class PublicReplay(Base):
    def _evidence(self):
        ev, _ = v.build(BASE)
        return canon(ev) + b"\n"
    def test_10_replay_ok(self):
        ep = self.tmp / "e.json"
        ep.write_bytes(self._evidence())
        out = self.tmp / "r.json"
        rc = v.main(["--evidence", str(ep), "--output", str(out)])
        self.assertEqual(rc, 0)
    def test_11_replay_tampered_leaf(self):
        ev = json.loads(self._evidence().decode())
        ev["runs"]["r6"]["prefix_ok"] = False
        ep = self.tmp / "e.json"
        ep.write_bytes(canon(ev) + b"\n")
        with self.assertRaises(ValueError):
            v.main(["--evidence", str(ep), "--output", str(self.tmp / "r.json")])
    def test_12_replay_duplicate_key(self):
        raw = self._evidence().decode().replace('"runs"', '"runs", "runs": {}, "x": 1, "runs"', 1)
        ep = self.tmp / "e.json"
        ep.write_bytes(raw.encode())
        with self.assertRaises(ValueError):
            v.main(["--evidence", str(ep), "--output", str(self.tmp / "r.json")])
    def test_13_replay_nonfinite(self):
        raw = self._evidence().decode().replace('"prefix_ok":true', '"prefix_ok":NaN', 1)
        ep = self.tmp / "e.json"
        ep.write_bytes(raw.encode())
        with self.assertRaises(ValueError):
            v.main(["--evidence", str(ep), "--output", str(self.tmp / "r.json")])
    def test_14_replay_workspace_tamper(self):
        ev = json.loads(self._evidence().decode())
        ev["workspace"]["files"]["TASK.md"] = "0" * 64
        ep = self.tmp / "e.json"
        ep.write_bytes(canon(ev) + b"\n")
        with self.assertRaises(ValueError):
            v.main(["--evidence", str(ep), "--output", str(self.tmp / "r.json")])
    def test_15_replay_baseline_tamper(self):
        ev = json.loads(self._evidence().decode())
        ev["baseline_commit"] = "0" * 40
        ep = self.tmp / "e.json"
        ep.write_bytes(canon(ev) + b"\n")
        with self.assertRaises(ValueError):
            v.main(["--evidence", str(ep), "--output", str(self.tmp / "r.json")])
    def test_16_replay_run_date_tamper(self):
        ev = json.loads(self._evidence().decode())
        ev["run_dates"]["r6"] = "2026-11-16" if v.R6_DATE != "2026-11-16" else "2026-11-15"
        ep = self.tmp / "e.json"
        ep.write_bytes(canon(ev) + b"\n")
        with self.assertRaises(ValueError):
            v.main(["--evidence", str(ep), "--output", str(self.tmp / "r.json")])

class CLI(Base):
    def test_20_output_exists(self):
        out = self.tmp / "r.json"; out.write_bytes(b"x")
        with self.assertRaises(ValueError):
            v.main(["--archive-base", str(BASE), "--build-evidence", str(self.tmp / "e.json"),
                    "--output", str(out)])
    def test_21_missing_mode(self):
        with self.assertRaises(ValueError):
            v.main(["--output", str(self.tmp / "r.json")])
    def test_23_cli_exit_two(self):
        out = self.tmp / "r2.json"; out.write_bytes(b"x")
        proc = subprocess.run([sys.executable, "-B", str(TEST_ROOT / "verify.py"),
                               "--output", str(out)], capture_output=True)
        self.assertEqual(proc.returncode, 2)
    def test_22_full_cli(self):
        e = self.tmp / "e.json"; r = self.tmp / "r.json"
        rc = v.main(["--archive-base", str(BASE), "--build-evidence", str(e), "--output", str(r)])
        self.assertEqual(rc, 0)
        ev = json.loads(e.read_bytes().decode())
        self.assertEqual(ev["schema"], v.SCHEMA)

class RealPackage(Base):
    def test_30_real_replay_when_installed(self):
        real_ev = HERE / "evidence.json"
        real_res = HERE / "result.json"
        if not real_ev.is_file():
            self.skipTest("installed evidence.json not present")
        patched = {k: getattr(v, k) for k in REAL_CONSTS}
        for k, val in REAL_CONSTS.items():
            setattr(v, k, val)
        try:
            out = self.tmp / "real-r.json"
            rc = v.main(["--evidence", str(real_ev), "--output", str(out)])
            self.assertEqual(rc, 0)
            self.assertEqual(out.read_bytes(), real_res.read_bytes())
        finally:
            for k, val in patched.items():
                setattr(v, k, val)

if __name__ == "__main__":
    unittest.main(verbosity=1)
