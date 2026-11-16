#!/usr/bin/env python3
"""系统提示与工具集跨版本对齐 verify 的对抗套件（stdlib only）。"""
import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
SCRIPT = HERE / "verify.py"


def load_module():
    spec = importlib.util.spec_from_file_location("spv", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def synth_archive(base, template_override=None, capture_override=None):
    """构造合成 r1109 launch 根 + capture bin。返回 (launch_dir, capture_bin)。"""
    launch = base / "launch"
    for task, dirname, raw in [
        ("bird", "dsh__bird-ca-schools-15__r1", "You are an AI agent powered by DeepSeek Harness.\n\nYou are a coding agent powered by the glm-5.3-flash model.\n\nLINE_A\n\nLINE_B\n\nYour working directory is /w/bird.\n"),
        ("dab", "dsh__dabstep-payments-10__r1", "You are an AI agent powered by DeepSeek Harness.\n\nYou are a coding agent powered by the glm-5.3-flash model.\n\nLINE_A\n\nLINE_B\n\nYour working directory is /w/dabstep-payments-10.\n"),
        ("ex", "dsh__exercism-py-6__r1", "You are an AI agent powered by DeepSeek Harness.\n\nYou are a coding agent powered by the glm-5.3-flash model.\n\nLINE_A\n\nLINE_B\n\nYour working directory is /w/ex.\n"),
        ("lcb", "dsh__lcb-recent-hard-4__r1", "You are an AI agent powered by DeepSeek Harness.\n\nYou are a coding agent powered by the glm-5.3-flash model.\n\nLINE_A\n\nLINE_B\n\nYour working directory is /w/lcb.\n"),
        ("tb", "dsh__tb-cargo-plan__r1", "You are an AI agent powered by DeepSeek Harness.\n\nYou are a coding agent powered by the glm-5.3-flash model.\n\nLINE_A\n\nLINE_B\n\nYour working directory is /w/tb.\n"),
    ]:
        if template_override:
            raw = template_override(raw)
        sys_event = {"seq": 7, "time": "t", "type": "system/message", "data": {"message": {"role": "system", "id": "s1", "source": "template", "content": [{"type": "text", "text": raw}]}, "turn": 0, "step": 0}}
        hdr_event = {"seq": 12, "time": "t", "type": "request/header", "data": {"header": {"tools": [{"name": "bash", "description": "d", "parameters": {"type": "object"}}, {"name": "exit_plan_mode", "description": "d", "parameters": {}}], "config": {}, "adapterDefaults": {}}, "reason": "r"}}
        blob = b"".join(_frame(json.dumps(e, ensure_ascii=False).encode() + b"\n") for e in (sys_event, hdr_event))
        d = launch / "dsh" / "runs" / dirname / "agent-session"
        d.mkdir(parents=True, exist_ok=True)
        (d / "session.v4.jsonl.zstd").write_bytes(blob)
    capture = {
        "messages": [{"role": "system", "content": "You are an AI agent powered by DeepSeek Harness.\n\nYou are a coding agent powered by the glm-5.3-flash model.\n\nLINE_A2\n\nLINE_B2\n\nAgent teams line added.\n"}],
        "tools": [{"type": "function", "function": {"name": "bash", "description": "d2", "parameters": {"type": "object"}}},
                  {"type": "function", "function": {"name": "skill", "description": "d", "parameters": {}}},
                  {"type": "function", "function": {"name": "working_directory", "description": "d", "parameters": {}}}],
    }
    if capture_override:
        capture = capture_override(capture)
    cbin = base / "capture.request.bin"
    cbin.write_bytes(json.dumps(capture, ensure_ascii=False).encode())
    return launch, cbin


def _frame(raw):
    import zstandard
    return zstandard.ZstdCompressor().compress(raw)


def refresh(mod):
    """从干净合成档逐task解码反算全部常量并 patch。"""
    tmp = tempfile.mkdtemp(prefix="spv-refresh-")
    launch, cbin = synth_archive(pathlib.Path(tmp))
    import re as _re
    mod.PATH_SLOT_RE = _re.compile(r"Your working directory is \S+\.", _re.M)
    tasks = {}
    envs = {}
    for task, dirname in [("bird", "dsh__bird-ca-schools-15__r1"), ("dab", "dsh__dabstep-payments-10__r1"), ("ex", "dsh__exercism-py-6__r1"), ("lcb", "dsh__lcb-recent-hard-4__r1"), ("tb", "dsh__tb-cargo-plan__r1")]:
        raw, _ = mod.frames_decode((launch / "dsh" / "runs" / dirname / "agent-session" / "session.v4.jsonl.zstd").read_bytes())
        events = [json.loads(l) for l in raw.decode().splitlines() if l.strip()]
        sys_ev = [e for e in events if e.get("type") == "system/message"][0]
        text = "".join(b["text"] for b in sys_ev["data"]["message"]["content"] if b.get("type") == "text")
        tasks[task] = text
        envs[task] = len(mod.canon(sys_ev))
    capture = json.loads(cbin.read_bytes())
    cap_sys = capture["messages"][0]["content"]
    mod.ARCHIVE_SYSTEM_RAW_BYTES = {t: len(v.encode()) for t, v in tasks.items()}
    mod.ARCHIVE_SYSTEM_SHA256 = {t: hashlib.sha256(v.encode()).hexdigest() for t, v in tasks.items()}
    mod.ARCHIVE_ENVELOPE_CANONICAL_BYTES = envs
    norm_sha = sorted({hashlib.sha256(mod.PATH_SLOT_RE.sub("Your working directory is <PATH>.", v).encode()).hexdigest() for v in tasks.values()})
    mod.NORMALIZED_TEMPLATE_COUNT = len(norm_sha)
    mod.NORMALIZED_TEMPLATE_SHA256 = norm_sha
    mod.CAPTURE_SYSTEM_BYTES = len(cap_sys.encode())
    mod.CAPTURE_SYSTEM_SHA256 = hashlib.sha256(cap_sys.encode()).hexdigest()
    import difflib
    a = tasks["bird"].splitlines(keepends=True)
    b = cap_sys.splitlines(keepends=True)
    hunks = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag == "equal":
            continue
        a_seg = "".join(a[i1:i2]); b_seg = "".join(b[j1:j2])
        cls = "model_slot" if "powered by the" in a_seg else ("path_line_relocated" if "working directory" in a_seg else "template_evolution")
        hunks.append({"class": cls, "archive_line_sha256": hashlib.sha256(a_seg.encode()).hexdigest(), "capture_line_sha256": hashlib.sha256(b_seg.encode()).hexdigest() if b_seg else None, "archive_bytes": len(a_seg.encode()), "capture_bytes": len(b_seg.encode()) if b_seg else 0, "delta": len(b_seg.encode()) - len(a_seg.encode())})
    mod.HUNKS = hunks
    mod.NET_DELTA = sum(h["delta"] for h in hunks)
    arc_tools = [{"name": "bash", "description": "d", "parameters": {"type": "object"}}, {"name": "exit_plan_mode", "description": "d", "parameters": {}}]
    wt = {t["function"]["name"]: t["function"] for t in capture["tools"]}
    arc_by = {t["name"]: t for t in arc_tools}
    rows = []
    for name in sorted(set(arc_by) & set(wt)):
        ao = {"description": arc_by[name].get("description"), "parameters": arc_by[name].get("parameters")}
        bo = {"description": wt[name].get("description"), "parameters": wt[name].get("parameters")}
        ja = mod.canon(ao); jb = mod.canon(bo)
        rows.append({"name": name, "canonical_equal": ja == jb, "desc_equal": ao["description"] == bo["description"], "params_canonical_equal": mod.canon(ao["parameters"]) == mod.canon(bo["parameters"]), "bytes_archive": len(ja), "bytes_capture": len(jb)})
    mod.COMMON_TOOL_RESULTS = rows
    mod.TOOLS_ARCHIVE_COUNT = len(arc_by)
    mod.TOOLS_CAPTURE_COUNT = len(wt)
    mod.TOOLS_REMOVED = sorted(set(arc_by) - set(wt))
    mod.TOOLS_ADDED = sorted(set(wt) - set(arc_by))
    mod.EQUAL_COUNT = sum(1 for r in rows if r["canonical_equal"])
    mod.EVOLVED_COUNT = sum(1 for r in rows if not r["canonical_equal"])
    return tmp


REAL = {}


def snapshot_real(mod):
    for name in ("ARCHIVE_SYSTEM_RAW_BYTES", "ARCHIVE_SYSTEM_SHA256", "ARCHIVE_ENVELOPE_CANONICAL_BYTES", "NORMALIZED_TEMPLATE_COUNT", "NORMALIZED_TEMPLATE_SHA256", "CAPTURE_SYSTEM_BYTES", "CAPTURE_SYSTEM_SHA256", "HUNKS", "NET_DELTA", "COMMON_TOOL_RESULTS", "TOOLS_ARCHIVE_COUNT", "TOOLS_CAPTURE_COUNT", "TOOLS_REMOVED", "TOOLS_ADDED", "EQUAL_COUNT", "EVOLVED_COUNT"):
        REAL[name] = getattr(mod, name)


def restore_real(mod):
    for k, v in REAL.items():
        setattr(mod, k, v)


class Base(unittest.TestCase):
    def setUp(self):
        self.mod = load_module()
        snapshot_real(self.mod)
        self.tmp = refresh(self.mod)

    def tearDown(self):
        restore_real(self.mod)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def do_build(self, launch=None, cbin=None):
        launch = launch or pathlib.Path(self.tmp) / "launch"
        cbin = cbin or pathlib.Path(self.tmp) / "capture.request.bin"
        return self.mod.build(launch, cbin, HERE)

    def ev_bytes(self, evidence):
        return json.dumps(evidence, ensure_ascii=False, indent=1).encode() + b"\n"


class Happy(Base):
    def test_01_build_and_public_validate(self):
        ev = self.do_build()
        raw = self.ev_bytes(ev)
        self.mod.validate_public(json.loads(raw))
        result = self.mod.result_for(json.loads(raw), hashlib.sha256(raw).hexdigest())
        self.assertIn("sysprompt-tools", result["schema"])

    def test_02_reconcile(self):
        ev = self.do_build()
        self.assertEqual(ev["capture_system_bytes"] - ev["archive_system_raw_bytes"]["bird"], ev["net_delta"])
        self.assertEqual(sum(h["delta"] for h in ev["hunks"]), ev["net_delta"])

    def test_03_replay_cli_frozen_pin_mismatch(self):
        """合成 evidence 对冻结常量必然失配：CLI 应拒绝（rc!=0）。正向 CLI 重放由 test_30 真档分支覆盖。"""
        ev = self.do_build()
        ep = pathlib.Path(self.tmp) / "e.json"; ep.write_bytes(self.ev_bytes(ev))
        out = pathlib.Path(self.tmp) / "r.json"
        rc = subprocess.run([sys.executable, "-B", str(SCRIPT), "--evidence", str(ep), "--output", str(out)], capture_output=True)
        self.assertNotEqual(rc.returncode, 0)
        self.assertFalse(out.exists())



class Tamper(Base):
    def _expect_fail(self, mutate_ev=None, mutate_files=None):
        ev = self.do_build()
        if mutate_ev:
            mutate_ev(ev)
        for rel, fn in (mutate_files or {}).items():
            fn(rel)
        raw = self.ev_bytes(ev)
        with self.assertRaises(ValueError):
            self.mod.validate_public(json.loads(raw))

    def test_10_raw_bytes_tamper(self):
        self._expect_fail(mutate_ev=lambda ev: ev["archive_system_raw_bytes"].__setitem__("bird", 2271))

    def test_11_hunk_tamper(self):
        self._expect_fail(mutate_ev=lambda ev: ev["hunks"][0].__setitem__("delta", 0))

    def test_12_net_delta_tamper(self):
        self._expect_fail(mutate_ev=lambda ev: ev.__setitem__("net_delta", 324))

    def test_13_tool_name_tamper(self):
        def m(ev):
            ev["common_tool_results"][0]["name"] = "sh"
        self._expect_fail(mutate_ev=m)

    def test_14_tool_count_tamper(self):
        self._expect_fail(mutate_ev=lambda ev: ev.__setitem__("tools_capture_count", 23))

    def test_15_template_tamper(self):
        self._expect_fail(mutate_ev=lambda ev: ev.__setitem__("normalized_template_count", 2))

    def test_16_baseline_tamper(self):
        self._expect_fail(mutate_ev=lambda ev: ev.__setitem__("baseline_commit", "0" * 40))

    def test_17_dup_key(self):
        raw = b'{"schema": "x", "schema": "y"}'
        with self.assertRaises(ValueError):
            self.mod.loads(raw)

    def test_18_nonfinite(self):
        raw = b'{"a": 1e999}'
        with self.assertRaises(ValueError):
            self.mod.loads(raw)

    def test_19_leak_paths(self):
        ev = self.do_build()
        ev["note"] = "/Users/someone/secret"
        with self.assertRaises(ValueError):
            self.mod.validate_public(ev)

    def test_20_output_exists(self):
        ev = self.do_build()
        p = pathlib.Path(self.tmp) / "out.json"
        p.write_bytes(b"{}")
        with self.assertRaises(ValueError):
            self.mod.safe_output(p)


class RealPackage(Base):
    def test_30_real_replay_if_available(self):
        root = os.environ.get("SP_ARCHIVE_BASE")
        if not root:
            self.skipTest("SP_ARCHIVE_BASE not set")
        launch = pathlib.Path(root) / "until22-20261109" / "launch-r1109"
        if not launch.is_dir():
            self.skipTest("real launch root missing")
        capture_bin = pathlib.Path(root) / "until14-20261117" / "loop1" / "capture" / "requests" / "001.request.bin"
        restore_real(self.mod)
        ev = self.mod.build(launch, capture_bin, HERE)
        self.mod.validate_public(ev)


class Cli(unittest.TestCase):
    def test_40_exclusive_output(self):
        tmp = tempfile.mkdtemp(prefix="spv-cli-")
        out = pathlib.Path(tmp) / "r.json"
        out.write_bytes(b"x")
        rc = subprocess.run([sys.executable, "-B", str(SCRIPT), "--evidence", str(out), "--output", str(out)], capture_output=True)
        self.assertNotEqual(rc.returncode, 0)

    def test_41_missing_evidence_arg(self):
        tmp = tempfile.mkdtemp(prefix="spv-cli-")
        rc = subprocess.run([sys.executable, "-B", str(SCRIPT), "--output", str(pathlib.Path(tmp) / "r.json")], capture_output=True)
        self.assertNotEqual(rc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
