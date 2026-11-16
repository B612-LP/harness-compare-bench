#!/usr/bin/env python3
"""Synthetic-fixture tests for the cross-model capture verifier (stdlib only)."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import verify as v

SCRIPT_DIR = Path(__file__).resolve().parent
REAL = {
    "REQ1": v.REQ1_DS_SHA256,
    "REQ2": v.REQ2_DS_SHA256,
    "R3": dict(v.REQ3_DS_SHAS),
    "GLM": v.REQ1_GLM_SHA256,
    "DELTA": v.DS_DELTA_BYTES,
    "P3": dict(v.P3_FACTS),
}


def seed_id(n):
    state = (1103515245 * n + 12345) % (2**31)
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    out = []
    for _ in range(24):
        state = (state * 6364136223846793005 + 1442695040888963407) % (2**64)
        out.append(alphabet[state % len(alphabet)])
    return "call_00_" + "".join(out[:20])


class XMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="xm-fixture-")
        base = Path(cls.tmp)
        glm_tools = [{"type": "function", "function": {"name": f"t{i}", "parameters": {"type": "object"}}} for i in range(22)]
        ds_tools = glm_tools[:22] + [
            {"type": "function", "function": {"name": "web_fetch", "parameters": {"type": "object"}}},
            {"type": "function", "function": {"name": "web_search", "parameters": {"type": "object"}}},
        ]
        runs = {
            "ds_r1": ("loop10/capture-ds-r1", glm_tools, ds_tools, "glm-5.3-flash", "deepseek-chat"),
            "glm_r1": ("loop1/capture", glm_tools, ds_tools, "glm-5.3-flash", "deepseek-chat"),
        }
        cls.run_dirs = {}
        counter = [0]

        def write_run(rel, tools, ds_tools, ds_model):
            run = base / rel
            (run / "requests").mkdir(parents=True)
            (run / "responses").mkdir(parents=True)
            sysmsg = "You are an AI agent powered by DeepSeek Harness.\n\nYou are a coding agent powered by the %s model.\n" % ds_model
            umsgs = ["u1", "u2", "u3", "u4"]

            def meta_for(index, raw):
                (run / "responses" / f"{index}.response.bin.meta.json").write_bytes(json.dumps({"request_body_sha256": v.sha(raw), "request_body_bytes": len(raw), "upstream_status": 200}).encode())

            r1 = {"model": ds_model, "messages": [{"role": "system", "content": sysmsg}] + [{"role": "user", "content": u} for u in umsgs], "stream": True, "stream_options": {"include_usage": True}, "max_completion_tokens": 8192, "tools": tools, "store": False}
            raw1 = json.dumps(r1, ensure_ascii=False).encode()
            (run / "requests" / "001.request.bin").write_bytes(raw1)
            meta_for("001", raw1)
            title = {"model": ds_model, "messages": [{"role": "system", "content": "s"}, {"role": "user", "content": v.TITLE_PREFIX + '["x"]'}], "max_completion_tokens": 4096, "stream": True}
            raw2 = json.dumps(title, ensure_ascii=False).encode()
            (run / "requests" / "002.request.bin").write_bytes(raw2)
            meta_for("002", raw2)
            counter[0] += 1
            ids = [seed_id(counter[0]), seed_id(counter[0] + 97)]
            r3 = json.loads(raw1.decode())
            asst = {"role": "assistant", "content": None, "tool_calls": [{"id": ids[0], "type": "function", "function": {"name": "read", "arguments": "{}"}}, {"id": ids[1], "type": "function", "function": {"name": "read", "arguments": "{}"}}]}
            t1 = {"role": "tool", "tool_call_id": ids[0], "content": "x" * 227}
            t2 = {"role": "tool", "tool_call_id": ids[1], "content": "y" * 203}
            r3["messages"] = r3["messages"] + [asst, t1, t2]
            raw3 = json.dumps(r3, ensure_ascii=False).encode()
            (run / "requests" / "003.request.bin").write_bytes(raw3)
            meta_for("003", raw3)
            return run

        cls.ds_run1 = write_run("loop10/capture-ds-r1", ds_tools, ds_tools, "deepseek-chat")
        cls.ds_run2 = write_run("loop10/capture-ds-r2", ds_tools, ds_tools, "deepseek-chat")
        cls.glm_run = write_run("loop1/capture", glm_tools, ds_tools, "glm-5.3-flash")
        # GLM需要req1_sha匹配真实pin？不——refresh后替换常量
        cls.base = str(base)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def refresh(self):
        v.REQ1_DS_SHA256 = v.sha(Path(self.ds_run1, "requests", "001.request.bin").read_bytes())
        v.REQ2_DS_SHA256 = v.sha(Path(self.ds_run1, "requests", "002.request.bin").read_bytes())
        v.REQ3_DS_SHAS["ds_r1"] = v.sha(Path(self.ds_run1, "requests", "003.request.bin").read_bytes())
        v.REQ3_DS_SHAS["ds_r2"] = v.sha(Path(self.ds_run2, "requests", "003.request.bin").read_bytes())
        v.REQ1_GLM_SHA256 = v.sha(Path(self.glm_run, "requests", "001.request.bin").read_bytes())
        v.DS_DELTA_BYTES = len(Path(self.ds_run1, "requests", "003.request.bin").read_bytes()) - len(Path(self.ds_run1, "requests", "001.request.bin").read_bytes())
        g_sys = len(json.loads(Path(self.glm_run, "requests", "001.request.bin").read_bytes().decode())["messages"][0]["content"].encode())
        d_sys = len(json.loads(Path(self.ds_run1, "requests", "001.request.bin").read_bytes().decode())["messages"][0]["content"].encode())
        v.P3_FACTS = dict(v.P3_FACTS)
        v.P3_FACTS["glm_system_raw_bytes"] = g_sys
        v.P3_FACTS["ds_system_raw_bytes"] = d_sys
        return v.build(self.base)

    def test_01_happy_build(self):
        evidence = self.refresh()
        self.assertEqual(evidence["endpoint"]["verdict"], "ds_assembly_stable")
        self.assertTrue(evidence["endpoint"]["req1_byte_equal"])
        self.assertEqual(evidence["endpoint"]["req3_diff_leaves"], 4)
        self.assertTrue(evidence["cross_provider_descriptive"]["user_msgs_1_to_4_content_equal"])

    def test_02_replay_validates(self):
        self.refresh()
        evidence = v.build(self.base)
        v.validate_public(evidence, v.sha(v.canon(evidence)))

    def test_03_req1_tamper(self):
        self.refresh()
        raw = Path(self.ds_run2, "requests", "001.request.bin").read_bytes()
        Path(self.ds_run2, "requests", "001.request.bin").write_bytes(raw[:-1])
        try:
            with self.assertRaises(ValueError):
                v.build(self.base)
        finally:
            Path(self.ds_run2, "requests", "001.request.bin").write_bytes(raw)

    def test_04_leaf_count_tamper(self):
        self.refresh()
        raw = Path(self.ds_run2, "requests", "003.request.bin").read_bytes()
        body = json.loads(raw.decode())
        body["store"] = True
        Path(self.ds_run2, "requests", "003.request.bin").write_bytes(json.dumps(body, ensure_ascii=False).encode())
        try:
            with self.assertRaises(ValueError):
                v.build(self.base)
        finally:
            Path(self.ds_run2, "requests", "003.request.bin").write_bytes(raw)

    def test_05_prefix_break(self):
        self.refresh()
        raw = Path(self.ds_run2, "requests", "001.request.bin").read_bytes()
        body = json.loads(raw.decode())
        body["messages"][1]["content"] = "CHANGED"
        Path(self.ds_run2, "requests", "001.request.bin").write_bytes(json.dumps(body, ensure_ascii=False).encode())
        try:
            with self.assertRaises(ValueError):
                v.build(self.base)
        finally:
            Path(self.ds_run2, "requests", "001.request.bin").write_bytes(raw)

    def test_06_public_rejects_wrong_leaf_count(self):
        self.refresh()
        evidence = v.build(self.base)
        evidence["endpoint"]["req3_diff_leaves"] = 5
        with self.assertRaises(ValueError):
            v.validate_public(evidence, v.sha(v.canon(evidence)))

    def test_07_public_rejects_bad_verdict(self):
        self.refresh()
        evidence = v.build(self.base)
        evidence["endpoint"]["verdict"] = "unstable"
        with self.assertRaises(ValueError):
            v.validate_public(evidence, v.sha(v.canon(evidence)))

    def test_08_public_rejects_credential_shape(self):
        self.refresh()
        evidence = v.build(self.base)
        evidence["title_request"]["model"] = "sk-ABCDEFGHIJKLMNOPQR"
        with self.assertRaises(ValueError):
            v.validate_public(evidence, v.sha(v.canon(evidence)))

    def test_09_public_rejects_wrong_pins(self):
        self.refresh()
        evidence = v.build(self.base)
        evidence["freeze_readme_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            v.validate_public(evidence, v.sha(v.canon(evidence)))

    def test_10_public_rejects_system_equal_claim(self):
        self.refresh()
        evidence = v.build(self.base)
        evidence["cross_provider_descriptive"]["system_content_equal"] = True
        with self.assertRaises(ValueError):
            v.validate_public(evidence, v.sha(v.canon(evidence)))

    def test_11_public_rejects_user_inequality(self):
        self.refresh()
        evidence = v.build(self.base)
        evidence["cross_provider_descriptive"]["user_msgs_1_to_4_content_equal"] = False
        with self.assertRaises(ValueError):
            v.validate_public(evidence, v.sha(v.canon(evidence)))

    def test_12_public_rejects_delta_drift(self):
        self.refresh()
        evidence = v.build(self.base)
        evidence["per_run_prefix"]["ds_r1"]["delta_bytes"] = 999
        with self.assertRaises(ValueError):
            v.validate_public(evidence, v.sha(v.canon(evidence)))

    def test_13_public_rejects_appended_drift(self):
        self.refresh()
        evidence = v.build(self.base)
        evidence["per_run_prefix"]["ds_r2"]["appended_shapes"] = [["tool", "str", 1]]
        with self.assertRaises(ValueError):
            v.validate_public(evidence, v.sha(v.canon(evidence)))

    def test_14_public_rejects_ds_tools_drift(self):
        self.refresh()
        evidence = v.build(self.base)
        evidence["cross_provider_descriptive"]["ds_only_tool_names"] = []
        with self.assertRaises(ValueError):
            v.validate_public(evidence, v.sha(v.canon(evidence)))

    def test_15_duplicate_key_rejected(self):
        with self.assertRaises(ValueError):
            v.loads(b'{"a": 1, "a": 2}')

    def test_16_nonfinite_rejected(self):
        with self.assertRaises(ValueError):
            v.loads(b'{"a": Infinity}')

    def test_17_exclusive_output(self):
        target = Path(self.tmp) / "out.json"
        v.exclusive(target, b"x")
        with self.assertRaises(ValueError):
            v.exclusive(target, b"y")

    def test_18_cli_replay_and_exclusive(self):
        self.refresh()
        evidence = v.build(self.base)
        epath = Path(self.tmp) / "evi.json"
        epath.write_bytes(v.canon(evidence))
        out = Path(self.tmp) / "res.json"
        code = v.main(["--evidence", str(epath), "--output", str(out)])
        self.assertEqual(code, 0)
        with self.assertRaises(ValueError):
            v.main(["--evidence", str(epath), "--output", str(out)])
        with self.assertRaises(ValueError):
            v.main(["--output", str(out)])

    def test_19_real_package_replay(self):
        archive = os.environ.get("XM_ARCHIVE_BASE")
        if not archive:
            self.skipTest("XM_ARCHIVE_BASE not set")
        v.P3_FACTS = dict(REAL["P3"])
        v.REQ1_DS_SHA256 = REAL["REQ1"]
        v.REQ2_DS_SHA256 = REAL["REQ2"]
        v.REQ3_DS_SHAS["ds_r1"] = REAL["R3"]["ds_r1"]
        v.REQ3_DS_SHAS["ds_r2"] = REAL["R3"]["ds_r2"]
        v.REQ1_GLM_SHA256 = REAL["GLM"]
        v.DS_DELTA_BYTES = REAL["DELTA"]
        evidence = v.build(archive)
        digest = v.sha(v.canon(evidence))
        v.validate_public(evidence, digest)
        self.assertEqual(v.REQ1_DS_SHA256, REAL["REQ1"])
        self.assertEqual(v.DS_DELTA_BYTES, 1028)


if __name__ == "__main__":
    unittest.main()
