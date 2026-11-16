#!/usr/bin/env python3
"""系统提示源级归因验证器测试（合成为主 + 真档重放分支）。stdlib only。

真档分支：直接对本包 evidence.json/result.json 做公开重放比较（无私档依赖）。
"""

import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "verify.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sysattr_verify", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


v = load_module()

# 真实常量快照（import后立即抓取，任何patch之前）
REAL = {
    "sources": copy.deepcopy(v.SOURCES),
    "system_sha": v.SYSTEM_SHA,
    "system_bytes": v.SYSTEM_BYTES,
    "baseline": v.BASELINE,
}


def restore_real():
    v.SOURCES = copy.deepcopy(REAL["sources"])
    v.SYSTEM_SHA = REAL["system_sha"]
    v.SYSTEM_BYTES = REAL["system_bytes"]
    v.BASELINE = REAL["baseline"]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


FAKE_SOURCES = {
    "system-prompt": '"You are an AI agent powered by DeepSeek Harness."\n',
    "headless-patch": "config:\n  personaPrefix: >-\n    You are a coding agent powered by the {{model}} model.\n",
    "tool-bash": 'text: "Check the [exit code: N] marker on every bash result; investigate failures before moving on."\n',
    "tool-fs": (
        'text: ({ scope }) => ctx.tools.get("read", scope) === void 0 ? "" : "Use the read tool — not shell commands like cat, sed, head, or tail — to inspect text files."\n'
        'text: "Read an existing file before overwriting it with write" + (ctx.tools.get("edit", scope) === void 0 ? "" : " and prefer edit for targeted changes") + "."\n'
        'text: "Read a file before editing it unless you just created or edited it in this session."\n'
    ),
    "tool-fs-search": (
        'text: "Use the glob tool — not shell find — to discover files by path pattern."\n'
        'text: "Use the grep tool — not shell grep or rg — to search file contents." + (ctx.tools.get("read", scope) === void 0 ? "" : " Use read on a matched file when you need surrounding context.")\n'
    ),
    "tool-jobs": 'text: "Track every background job id you start. You are notified in-session when a job finishes."\n',
    "tool-goal": "text: `create_goal may infer goal intent from a direct human request. Mark blocked only after the same blocking condition persists for at least ${blockedAfter} consecutive goal rounds, and report that concrete condition in blocked_reason; difficulty, uncertainty, or useful remaining work is not blocked.`\n",
    "tool-workflow": "text: `Use the ${toolName} tool ONLY when the user explicitly asks for a workflow or for large multi-agent orchestration. For one or two delegations, prefer plain subagent calls.`\n",
    "tool-subagent": "text: `Start independent delegations with ${visible.map((name) => `\\`${name}\\``).join(\" or \")} together in one assistant message and continue useful work while they run.\\n\\nBash, formatters, code generators, and scripts can overwrite concurrent edits without conflict detection; the agent integrating the work must review the final diff and run relevant tests.`\n",
}

# 合成重建期望的12段（与verify抽取规则一一对应）
EXPECTED_SEGMENTS = [
    "You are an AI agent powered by DeepSeek Harness.",
    "You are a coding agent powered by the glm-5.3-flash model.",
    "Check the [exit code: N] marker on every bash result; investigate failures before moving on.",
    "Use the read tool — not shell commands like cat, sed, head, or tail — to inspect text files.",
    "Read an existing file before overwriting it with write and prefer edit for targeted changes.",
    "Read a file before editing it unless you just created or edited it in this session.",
    "Use the glob tool — not shell find — to discover files by path pattern.",
    "Use the grep tool — not shell grep or rg — to search file contents. Use read on a matched file when you need surrounding context.",
    "Track every background job id you start. You are notified in-session when a job finishes.",
    "create_goal may infer goal intent from a direct human request. Mark blocked only after the same blocking condition persists for at least 3 consecutive goal rounds, and report that concrete condition in blocked_reason; difficulty, uncertainty, or useful remaining work is not blocked.",
    "Use the workflow tool ONLY when the user explicitly asks for a workflow or for large multi-agent orchestration. For one or two delegations, prefer plain subagent calls.",
    "Start independent delegations with `subagent` or `subagent_fork` together in one assistant message and continue useful work while they run.\n\nBash, formatters, code generators, and scripts can overwrite concurrent edits without conflict detection; the agent integrating the work must review the final diff and run relevant tests.",
]


def make_synth(root):
    srcdir = root / "sources"
    srcdir.mkdir()
    for key, text in FAKE_SOURCES.items():
        blob = text.encode("utf-8")
        (srcdir / (key + ".src")).write_bytes(blob)
        v.SOURCES[key]["sha256"] = sha(blob)
        v.SOURCES[key]["bytes"] = len(blob)
    system = "\n\n".join(EXPECTED_SEGMENTS).encode("utf-8")
    syspath = root / "system.txt"
    syspath.write_bytes(system)
    return srcdir, syspath, system


class SysAttrBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = v
        restore_real()
        cls.tmp = tempfile.mkdtemp(prefix="sysattr-synth-")
        cls.srcdir, cls.syspath, cls.system = make_synth(Path(cls.tmp))
        v.SYSTEM_SHA = sha(cls.system)
        v.SYSTEM_BYTES = len(cls.system)
        v.BASELINE = "0" * 40

    @classmethod
    def tearDownClass(cls):
        restore_real()

    def setUp(self):
        self.out = Path(tempfile.mkdtemp(prefix="sysattr-out-"))

    def test_01_build_and_validate(self):
        ev, evb, res = self.mod.build(str(self.syspath), str(self.srcdir))
        self.assertTrue(ev["rebuild"]["byte_equal"])
        self.mod.validate_public(ev)
        self.assertEqual(res["verdict"], "source_attributed_full")
        self.assertEqual(res["evidence_sha256"], sha(evb))

    def test_02_replay_matches_build_result(self):
        ev, evb, res = self.mod.build(str(self.syspath), str(self.srcdir))
        res2 = self.mod.result_for(ev, evb)
        self.assertEqual(canonical(res), canonical(res2))

    def test_03_section_text_tamper(self):
        ev, _, _ = self.mod.build(str(self.syspath), str(self.srcdir))
        ev = copy.deepcopy(ev)
        ev["sections"][3]["text"] = ev["sections"][3]["text"] + "!"
        with self.assertRaises(self.mod.Invalid):
            self.mod.validate_public(ev)

    def test_04_join_mismatch_tamper(self):
        ev, _, _ = self.mod.build(str(self.syspath), str(self.srcdir))
        ev = copy.deepcopy(ev)
        ev["sections"][3]["text"] = ev["sections"][3]["text"] + "!"
        ev["sections"][3]["sha256"] = sha(ev["sections"][3]["text"].encode("utf-8"))
        with self.assertRaises(self.mod.Invalid):
            self.mod.validate_public(ev)

    def test_05_kind_mapping_tamper(self):
        ev, _, _ = self.mod.build(str(self.syspath), str(self.srcdir))
        ev = copy.deepcopy(ev)
        ev["sections"][4]["kind"] = "static"
        with self.assertRaises(self.mod.Invalid):
            self.mod.validate_public(ev)

    def test_06_source_pin_tamper(self):
        ev, _, _ = self.mod.build(str(self.syspath), str(self.srcdir))
        ev = copy.deepcopy(ev)
        ev["sources"]["tool-bash"]["sha256"] = "0" * 64
        with self.assertRaises(self.mod.Invalid):
            self.mod.validate_public(ev)

    def test_07_system_pin_tamper(self):
        ev, _, _ = self.mod.build(str(self.syspath), str(self.srcdir))
        ev = copy.deepcopy(ev)
        ev["system"]["sha256"] = "1" * 64
        with self.assertRaises(self.mod.Invalid):
            self.mod.validate_public(ev)

    def test_08_rebuild_flag_tamper(self):
        ev, _, _ = self.mod.build(str(self.syspath), str(self.srcdir))
        ev = copy.deepcopy(ev)
        ev["rebuild"]["byte_equal"] = False
        with self.assertRaises(self.mod.Invalid):
            self.mod.validate_public(ev)

    def test_09_limits_tamper(self):
        ev, _, _ = self.mod.build(str(self.syspath), str(self.srcdir))
        ev = copy.deepcopy(ev)
        ev["limits"] = []
        with self.assertRaises(self.mod.Invalid):
            self.mod.validate_public(ev)

    def test_10_duplicate_key_rejected(self):
        raw = b'{"a": 1, "a": 2}'
        with self.assertRaises(self.mod.Invalid):
            self.mod.loads(raw)

    def test_11_nonfinite_rejected(self):
        raw = b'{"a": 1e999}'
        with self.assertRaises(self.mod.Invalid):
            self.mod.loads(raw)

    def test_12_mismatched_system_rejected(self):
        bad = self.tmp + "/bad-system.txt"
        Path(bad).write_bytes(self.system + b"x")
        with self.assertRaises(self.mod.Invalid):
            self.mod.build(bad, str(self.srcdir))

    def test_13_source_snapshot_missing_rejected(self):
        empty = Path(self.tmp) / "empty-sources"
        empty.mkdir(exist_ok=True)
        with self.assertRaises(self.mod.Invalid):
            self.mod.build(str(self.syspath), str(empty))

    def test_14_slots_declared(self):
        ev, _, _ = self.mod.build(str(self.syspath), str(self.srcdir))
        by_index = {r["index"]: r for r in ev["sections"]}
        self.assertEqual(by_index[2]["slots"], ["{{model}}"])
        self.assertEqual(by_index[12]["slots"], ["delegates"])


class RealPackage(unittest.TestCase):
    def setUp(self):
        restore_real()

    def tearDown(self):
        restore_real()

    def setUp(self):
        restore_real()
        self.ev_path = HERE / "evidence.json"
        self.res_path = HERE / "result.json"
        if not (self.ev_path.is_file() and self.res_path.is_file()):
            self.skipTest("package evidence/result not present")

    def test_20_public_replay_matches_result(self):
        evb = self.ev_path.read_bytes()
        ev = v.loads(evb)
        v.validate_public(ev)
        res = v.result_for(ev, evb)
        self.assertEqual(canonical(res) + b"\n", self.res_path.read_bytes())

    def test_21_real_system_sha_pinned(self):
        ev = v.loads(self.ev_path.read_bytes())
        self.assertEqual(ev["system"]["sha256"], "8e17c07c2a212f104dea010c0200c45a6b7a27682c91ed4bbc14827da059eb93")
        self.assertEqual(ev["task_user_content_bytes"], 0)


class Cli(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="sysattr-cli-")
        restore_real()
        cls.srcdir, cls.syspath, cls.system = make_synth(Path(cls.tmp))
        v.SYSTEM_SHA = sha(cls.system)
        v.SYSTEM_BYTES = len(cls.system)
        v.BASELINE = "0" * 40

    @classmethod
    def tearDownClass(cls):
        restore_real()

    def test_30_cli_replay_tampered_evidence_rejected(self):
        ev, evb, _ = v.build(str(self.syspath), str(self.srcdir))
        ev = copy.deepcopy(ev)
        ev["sections"][0]["text"] = "TAMPERED"
        p = Path(self.tmp) / "tampered.json"
        p.write_bytes(canonical(ev))
        rc = subprocess.run([sys.executable, "-B", str(SCRIPT), "--evidence", str(p), "--output", str(Path(self.tmp) / "o1.json")], capture_output=True)
        self.assertEqual(rc.returncode, 2)

    def test_31_cli_exclusive_output_rejected(self):
        ev, evb, _ = v.build(str(self.syspath), str(self.srcdir))
        out = Path(self.tmp) / "exists.json"
        out.write_bytes(b"x")
        evp = Path(self.tmp) / "ev.json"
        evp.write_bytes(evb)
        rc = subprocess.run([sys.executable, "-B", str(SCRIPT), "--evidence", str(evp), "--output", str(out)], capture_output=True)
        self.assertEqual(rc.returncode, 2)

    def test_32_cli_missing_output_rejected(self):
        rc = subprocess.run([sys.executable, "-B", str(SCRIPT), "--evidence", str(HERE / "evidence.json")], capture_output=True)
        self.assertNotEqual(rc.returncode, 0)

    def test_33_cli_build_pins_reject_synthetic(self):
        # CLI子进程加载真实常量pin，合成system必然被拒（rc2）
        out = Path(self.tmp) / "c33"
        rc = subprocess.run([sys.executable, "-B", str(SCRIPT), "--system", str(self.syspath), "--sources", str(self.srcdir), "--build-evidence", str(out / "e.json"), "--output", str(out / "r.json")], capture_output=True)
        self.assertEqual(rc.returncode, 2)
        self.assertFalse((out / "e.json").exists())

    def test_34_cli_real_build_then_replay_identical(self):
        base = os.environ.get("SYSATTR_ARCHIVE_BASE")
        if not base:
            self.skipTest("SYSATTR_ARCHIVE_BASE not set")
        root = Path(base) / "loop13/work"
        out = Path(tempfile.mkdtemp(prefix="sysattr-real-"))
        rc = subprocess.run([sys.executable, "-B", str(SCRIPT), "--system", str(root / "system.txt"), "--sources", str(root / "sources"), "--build-evidence", str(out / "e.json"), "--output", str(out / "r.json")], capture_output=True)
        self.assertEqual(rc.returncode, 0, rc.stderr)
        self.assertEqual((out / "e.json").read_bytes(), (HERE / "evidence.json").read_bytes())
        self.assertEqual((out / "r.json").read_bytes(), (HERE / "result.json").read_bytes())
        rc = subprocess.run([sys.executable, "-B", str(SCRIPT), "--evidence", str(out / "e.json"), "--output", str(out / "r2.json")], capture_output=True)
        self.assertEqual(rc.returncode, 0, rc.stderr)
        self.assertEqual((out / "r2.json").read_bytes(), (HERE / "result.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
