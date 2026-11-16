#!/usr/bin/env python3
"""Codex捕获包套件（21用例）：合成两run归档全管线+篡改+真档分支+CLI。stdlib only。
无 CX_ARCHIVE_BASE 时真档分支 skip；设置 CX_ARCHIVE_BASE=<until14根> 时激活。"""
import copy
import hashlib
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
import importlib.util
_spec = importlib.util.spec_from_file_location("cxv", SCRIPT)
v = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v)

REAL = {k: copy.deepcopy(getattr(v, k)) for k in
        ("REQ1_SHAS", "TASK_TEXT_SHA256", "INSTRUCTIONS_SHA256", "ID_NORMALIZED_CANONICAL_SHA256",
         "WORKSPACE_AGG_SHA256", "REQ1_BYTE_EQUAL_EXPECT", "REQ1_DIFF_LEAVES_EXPECT", "REQ1_DIFF_FIELDS_EXPECT")}


def restore_real():
    v.REQ1_SHAS = copy.deepcopy(REAL["REQ1_SHAS"])
    v.TASK_TEXT_SHA256 = REAL["TASK_TEXT_SHA256"]
    v.INSTRUCTIONS_SHA256 = REAL["INSTRUCTIONS_SHA256"]
    v.ID_NORMALIZED_CANONICAL_SHA256 = REAL["ID_NORMALIZED_CANONICAL_SHA256"]
    v.WORKSPACE_AGG_SHA256 = REAL["WORKSPACE_AGG_SHA256"]
    v.REQ1_BYTE_EQUAL_EXPECT = REAL["REQ1_BYTE_EQUAL_EXPECT"]
    v.REQ1_DIFF_LEAVES_EXPECT = REAL["REQ1_DIFF_LEAVES_EXPECT"]
    v.REQ1_DIFF_FIELDS_EXPECT = copy.deepcopy(REAL["REQ1_DIFF_FIELDS_EXPECT"])


def sha(x):
    return hashlib.sha256(x).hexdigest()


def canon(o):
    return json.dumps(o, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


TASK = "First read TASK.md, then read inputs/exercises/dominoes/dominoes.py, then reply with exactly one line: the TASK.md first-level title and the name of the function defined in the Python file. Do not modify any files."
assert len(TASK.encode()) == 214


def msg(role, content, mid=""):
    return {"type": "message", "role": role, "id": mid, "content": [{"type": "input_text", "text": content}]}


def reason(rid):
    return {"type": "reasoning", "id": rid, "summary": [], "encrypted_content": "ENC" + rid}


def fcall(cid, args):
    return {"type": "function_call", "id": cid, "call_id": "call_" + cid, "name": "exec_command", "arguments": args}


def fout(oid, out):
    return {"type": "function_call_output", "id": oid, "call_id": "call_" + oid[1:], "output": out}


def make_req(input_items):
    return {
        "model": "deepseek-flash", "input": input_items, "store": False,
        "include": ["reasoning.encrypted_content"], "stream": True,
        "prompt_cache_key": "TH-1", "client_metadata": {
            "root_turn_id": "RT-1", "session_id": "SESS-1", "thread_id": "TH-1",
            "turn_id": "T-1", "x-codex-turn-metadata": "M-1", "x-codex-window-id": "W-1",
        },
        "tools": [{"name": n} for n in v.TOOLS],
        "reasoning": {"effort": "low", "summary": "auto"},
    }


def synth_archive(base):
    root = Path(base) / "loop14"
    step1 = [reason("rs1"), fcall("fc1", "{}"), fout("fo1", "OUT1")]
    step2 = [reason("rs2"), fcall("fc2", "{}"), fout("fo2", "OUT2")]
    base4 = [msg("developer", "INSTRUCTIONS-" + "x" * 17000, "mid0"),
             msg("developer", "PERMS", "mid1"),
             msg("user", "ENV", "mid2"),
             msg("user", TASK, "mid3")]
    r1 = [
        make_req(list(base4)),
        make_req(list(base4) + step1),
        make_req(list(base4) + step1 + step2),
    ]
    step3 = [reason("rs3"), fcall("fc3", "{}"), fcall("fc4", "{}"), fout("fo3", "O3"), fout("fo4", "O4")]
    r2 = [
        make_req(list(base4)),
        make_req(list(base4) + step3),
    ]
    for run, reqs in (("r1", r1), ("r2", r2)):
        d = root / ("capture-codex-" + run) / "requests"
        d.mkdir(parents=True, exist_ok=True)
        for i, req in enumerate(reqs, 1):
            (d / ("00%d.request.bin" % i)).write_bytes(canon(req) + b"\n")
    return r1, r2


def refresh(v):
    d = tempfile.mkdtemp(prefix="cx-synth-")
    synth_archive(d)
    def binsha(run, i):
        p = Path(d) / "loop14" / ("capture-codex-" + run) / "requests" / ("00%d.request.bin" % i)
        return sha(p.read_bytes())
    v.REQ1_SHAS = {"r1": binsha("r1", 1), "r2": binsha("r2", 1)}
    req1_synth = json.loads((Path(d) / "loop14/capture-codex-r1/requests/001.request.bin").read_bytes().decode())
    v.ID_NORMALIZED_CANONICAL_SHA256 = sha(canon(v.normalize_ids(req1_synth)))
    v.REQ1_BYTE_EQUAL_EXPECT = True
    v.REQ1_DIFF_LEAVES_EXPECT = 0
    v.REQ1_DIFF_FIELDS_EXPECT = {}
    v.TASK_TEXT_SHA256 = sha(TASK.encode())
    v.INSTRUCTIONS_SHA256 = sha(("INSTRUCTIONS-" + "x" * 17000).encode())
    v.TOOLS = list(v.TOOLS)
    return d, v


def load_run(d, run, n):
    out = []
    for i in range(1, n + 1):
        p = Path(d) / "loop14" / ("capture-codex-" + run) / "requests" / ("00%d.request.bin" % i)
        out.append(json.loads(p.read_bytes().decode()))
    return out


class CxBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        restore_real()
        cls.d, cls.mod = refresh(v)

    @classmethod
    def tearDownClass(cls):
        restore_real()


class Happy(CxBase):
    def test_01_build(self):
        ev, evb, res = self.mod.build(Path(self.d))
        self.mod.validate_public(ev)
        self.assertEqual(res["verdict"], "codex_assembly_stable_ids_generated")
        self.assertEqual(ev["req1_cross_run"]["diff_leaves"], self.mod.REQ1_DIFF_LEAVES_EXPECT)
        self.assertEqual(ev["req1_cross_run"]["byte_equal"], self.mod.REQ1_BYTE_EQUAL_EXPECT)

    def test_02_result_binding(self):
        ev, evb, res = self.mod.build(Path(self.d))
        self.assertEqual(res["evidence_sha256"], sha(evb))
        self.mod.validate_public(ev)
        again = self.mod.result_for(ev, evb)
        self.assertEqual(again, res)


class Tamper(CxBase):
    def setUp(self):
        ev, evb, _ = self.mod.build(Path(self.d))
        self.ev = json.loads(evb.decode())
        self.evb = evb

    def expect_invalid(self, mutate):
        e = copy.deepcopy(self.ev)
        mutate(e)
        with self.assertRaises(self.mod.Invalid):
            self.mod.validate_public(e)

    def test_10_byte_equal_flip(self):
        want = not self.mod.REQ1_BYTE_EQUAL_EXPECT
        self.expect_invalid(lambda e: e["req1_cross_run"].__setitem__("byte_equal", want))

    def test_11_diff_leaves(self):
        self.expect_invalid(lambda e: e["req1_cross_run"].__setitem__("diff_leaves", 10))

    def test_12_diff_fields(self):
        self.expect_invalid(lambda e: e["req1_cross_run"].__setitem__("diff_fields", {"client_metadata": 6}))

    def test_13_store_true(self):
        self.expect_invalid(lambda e: e["state_mechanism"].__setitem__("store", True))

    def test_14_normalized_pin(self):
        self.expect_invalid(lambda e: e["req1_cross_run"].__setitem__("id_normalized_canonical_sha256", "0" * 64))

    def test_15_req1_sha(self):
        self.expect_invalid(lambda e: e["runs"]["r1"].__setitem__("req_sha256", ["0" * 64] * 3))

    def test_16_task_sha(self):
        self.expect_invalid(lambda e: e["cross_harness_task_surface"].__setitem__("task_text_sha256", "0" * 64))

    def test_17_tools(self):
        self.expect_invalid(lambda e: e["codex_assembly"].__setitem__("tools_count", 7))

    def test_18_baseline(self):
        self.expect_invalid(lambda e: e.__setitem__("baseline", "0" * 64))

    def test_19_readme_pin(self):
        self.expect_invalid(lambda e: e.__setitem__("frozen_readme_sha256", "0" * 64))

    def test_20_users_leak(self):
        self.expect_invalid(lambda e: e.__setitem__("note", "/Users/x"))

    def test_21_dup_key(self):
        raw = b'{"a":1,"a":2}'
        with self.assertRaises(Exception):
            self.mod.loads(raw)

    def test_22_nonfinite(self):
        raw = ('{"schema": 1e999}').encode()
        with self.assertRaises(Exception):
            self.mod.loads(raw)

    def test_23_limits(self):
        self.expect_invalid(lambda e: e.__setitem__("limits", []))


class RealPackage(unittest.TestCase):
    def setUp(self):
        restore_real()
        if not (HERE / "evidence.json").is_file():
            self.skipTest("no package evidence")

    def tearDown(self):
        restore_real()

    def test_30_public_replay(self):
        evb = (HERE / "evidence.json").read_bytes()
        ev = v.loads(evb)
        v.validate_public(ev)
        res = v.result_for(ev, evb)
        self.assertEqual(canon(res) + b"\n", (HERE / "result.json").read_bytes())


class Cli(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        restore_real()
        cls.d = tempfile.mkdtemp(prefix="cx-cli-")
        refresh(v)

    @classmethod
    def tearDownClass(cls):
        restore_real()

    def _run(self, *extra):
        return subprocess.run([sys.executable, "-B", str(SCRIPT)] + list(extra), capture_output=True)

    def test_31_synth_build_rejected_by_real_pins(self):
        synth = Path(tempfile.mkdtemp(prefix="cx-synth2-"))
        synth_archive(synth)
        out = Path(self.d) / "x.json"
        rc = self._run("--archive-base", synth, "--build-evidence", str(out / "e.json"), "--output", str(out / "r.json"))
        self.assertEqual(rc.returncode, 2)

    def test_32_output_exists(self):
        out = Path(self.d) / "y.json"
        out.write_text("x")
        rc = self._run("--evidence", str(HERE / "evidence.json"), "--output", str(out))
        self.assertEqual(rc.returncode, 2)

    def test_33_missing_output_arg(self):
        rc = self._run("--evidence", str(HERE / "evidence.json"))
        self.assertEqual(rc.returncode, 2)

    def test_34_real_end_to_end(self):
        base = os.environ.get("CX_ARCHIVE_BASE")
        if not base:
            self.skipTest("CX_ARCHIVE_BASE not set")
        out = Path(tempfile.mkdtemp(prefix="cx-real-"))
        rc = self._run("--archive-base", base, "--build-evidence", str(out / "e.json"), "--output", str(out / "r.json"))
        self.assertEqual(rc.returncode, 0, rc.stderr)
        self.assertEqual((out / "e.json").read_bytes(), (HERE / "evidence.json").read_bytes())
        self.assertEqual((out / "r.json").read_bytes(), (HERE / "result.json").read_bytes())
        rc = self._run("--evidence", str(out / "e.json"), "--output", str(out / "rp.json"))
        self.assertEqual(rc.returncode, 0, rc.stderr)
        self.assertEqual((out / "rp.json").read_bytes(), (HERE / "result.json").read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=1)
