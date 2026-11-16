#!/usr/bin/env python3
"""R-A4 verify.py 反例套件（stdlib only）。

合成两run链（run1含一次bash误调用绕行），先从干净合成档反算全部冻结常量并patch模块，
再用例基于这些常量做篡改/对抗：常量有真实约束力。
真档公开重放用例在安装 evidence.json 后自动启用，否则 skip（公开套件不依赖私档）。
"""
import copy
import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
TEST_ROOT = pathlib.Path(os.environ.get("T3_TEST_ROOT", HERE))

_spec = importlib.util.spec_from_file_location("ra4_verify_under_test", TEST_ROOT / "verify.py")
v = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v)


def canon(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def write_request(run_dir, seq, body):
    p = run_dir / "requests" / ("%03d.request.bin" % seq)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(canon(body))
    return p


def build_synthetic(base):
    """两条链：req1(4 msgs)+标题+11续；r1多一次bash误调用绕行对。"""
    for label, extra in (("t3-r1", True), ("t3-r2", False)):
        rd = base / label
        seq = 1
        msgs0 = [
            {"role": "system", "content": "S" * 40},
            {"role": "user", "content": "Read TASK.md and follow it exactly. Do not modify any files."},
            {"role": "assistant", "content": "STEP 1: TOK01", "tool_calls": [
                {"id": "call_" + "a" * 24, "type": "function",
                 "function": {"name": "read", "arguments": "{\"file_path\":\"TASK.md\"}"}}]},
            {"role": "tool", "content": "<file>task</file>", "tool_call_id": "call_" + "a" * 24},
        ]
        run = json.loads(canon({"messages": [m for m in msgs0], "tools": [{"name": "read"}]}))
        write_request(rd, seq, run); seq += 1
        write_request(rd, seq, {"messages": [{"role": "system", "content": "t"},
                                             {"role": "user", "content": "title"}]}); seq += 1
        if extra:
            run["messages"] += [
                {"role": "assistant", "content": None, "tool_calls": [
                    {"id": "call_" + "b" * 24, "type": "function",
                     "function": {"name": "bash", "arguments": "{\"description\":\"x\"}"}}]},
                {"role": "tool", "content": "Error: invalid arguments: missing required property \"command\"",
                 "tool_call_id": "call_" + "b" * 24},
            ]
            write_request(rd, seq, json.loads(canon(run))); seq += 1  # 错误turn是独立请求
        for k in range(2, 13):
            tok = "STEP %d: TOK%02d" % (k, k)
            aid = "call_" + (chr(97 + k) * 24)
            run["messages"] += [
                {"role": "assistant", "content": tok, "tool_calls": [
                    {"id": aid, "type": "function", "function": {"name": "read", "arguments": "{}"}}]},
                {"role": "tool", "content": "content-%02d" % k, "tool_call_id": aid},
            ]
            write_request(rd, seq, json.loads(canon(run))); seq += 1


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ra4t-")
        self.base = pathlib.Path(self.tmp) / "loop8"
        build_synthetic(self.base)
        # 派生阶段关闭不变量（require no-op），先从干净合成档反算常量
        real_require = v.require
        v.require = lambda cond, msg: None
        try:
            ev, per = v.build(str(self.base))
        finally:
            v.require = real_require
        # 反算并patch全部冻结常量（对合成档有真实约束力）
        v.TOTAL_REQUESTS = {k: ev["runs"][k]["requests_total"] for k in ev["runs"]}
        v.MAIN_REQUESTS = {k: ev["runs"][k]["mains"] for k in ev["runs"]}
        v.PREFIX_OK = {k: ev["runs"][k]["prefix_ok"] for k in ev["runs"]}
        v.PREFIX_STEPS = {k: ev["runs"][k]["prefix_steps"] for k in ev["runs"]}
        v.APPENDED_SHAPES_SHA = {k: ev["runs"][k]["appended_shapes_sha256"] for k in ev["runs"]}
        v.TITLE_SHA = ev["runs"]["t3-r1"]["title_raw_sha256"]
        v.FINAL_TEXT_LINES = {"t3-r1": ev["runs"]["t3-r1"]["final_request_assistant_text_line_count"],
                              "t3-r2": ev["runs"]["t3-r2"]["final_request_assistant_text_line_count"]}
        v.REQ1_SHA = ev["cross_run"]["req1_raw_sha256"]
        v.ERROR_PAIR = ev["cross_run"]["error_pair"]
        v.SKIP_ERROR_ALIGNMENT = ev["cross_run"]["skip_error_alignment"]
        # DELTAS 从干净档反算
        deltas = {}
        for label in ("t3-r1", "t3-r2"):
            _raws, bodies = v.load_run(str(self.base), label)
            mains = [b for b in bodies if not v.is_title(b)]
            deltas[label] = [len(canon(b)) - len(canon(a)) for a, b in zip(mains, mains[1:])]
        v.DELTAS = deltas
        self.ev_clean = ev

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def build_ok(self):
        ev, _ = v.build(str(self.base))
        v.validate_public(ev)
        return ev


class Happy(Base):
    def test_happy(self):
        ev = self.build_ok()
        self.assertTrue(ev["cross_run"]["req1_byte_equal"])
        self.assertTrue(ev["cross_run"]["title_byte_equal"])
        self.assertGreater(ev["cross_run"]["skip_error_alignment"]["equal"], 0)


class Tamper(Base):
    def test_prefix_break_rejected(self):
        p = self.base / "t3-r2" / "requests" / "004.request.bin"
        b = json.loads(p.read_bytes())
        b["messages"][1] = {"role": "user", "content": "mutated"}
        p.write_bytes(canon(b))
        with self.assertRaises(v.Invalid):
            self.build_ok()

    def test_delta_mismatch_rejected(self):
        p = self.base / "t3-r2" / "requests" / "006.request.bin"
        b = json.loads(p.read_bytes())
        b["messages"][-1]["content"] = "content-XX"
        p.write_bytes(canon(b))
        with self.assertRaises(v.Invalid):
            self.build_ok()

    def test_appended_shape_change_rejected(self):
        p = self.base / "t3-r2" / "requests" / "005.request.bin"
        b = json.loads(p.read_bytes())
        for m in b["messages"]:
            if m.get("role") == "assistant" and isinstance(m.get("content"), str) and m["content"].startswith("STEP 2"):
                m["content"] = None
        p.write_bytes(canon(b))
        with self.assertRaises(v.Invalid):
            self.build_ok()

    def test_error_pair_rewrite_collapses_alignment(self):
        p = self.base / "t3-r1" / "requests" / "008.request.bin"
        b = json.loads(p.read_bytes())
        for m in b["messages"]:
            if m.get("role") == "tool" and str(m.get("content", "")).startswith("Error: invalid"):
                m["content"] = "Error: rewritten"
        p.write_bytes(canon(b))
        # 改写任一回显中的错误对内容 → 该请求delta偏离冻结值，直接被拒（比塌缩更严）
        with self.assertRaises(v.Invalid):
            v.build(str(self.base))

    def test_req1_tamper_rejected(self):
        p = self.base / "t3-r1" / "requests" / "001.request.bin"
        b = json.loads(p.read_bytes())
        b["messages"][0]["content"] = "T" * 40
        p.write_bytes(canon(b))
        ev, _ = v.build(str(self.base))
        self.assertFalse(ev["cross_run"]["req1_byte_equal"])
        with self.assertRaises(v.Invalid):
            v.validate_public(ev)

    def test_result_for_shape(self):
        ev = self.build_ok()
        raw = canon(ev)
        res = v.result_for(ev, hashlib.sha256(raw).hexdigest())
        self.assertEqual(res["schema"], "ra4-deep-chain-result-v1")
        self.assertIn("limits", res)
        self.assertEqual(len(res["limits"]), 5)


class StrictJSON(Base):
    def test_duplicate_key_rejected(self):
        raw = b'{"a": 1, "a": 2}'
        with self.assertRaises(v.Invalid):
            v.loads(raw)

    def test_nonfinite_rejected(self):
        with self.assertRaises(v.Invalid):
            v.loads(b'{"a": NaN}')


class PublicReplayReal(Base):
    def test_public_evidence_replay(self):
        real = HERE / "evidence.json"
        if not real.exists():
            self.skipTest("installed public evidence not present")
        out = pathlib.Path(self.tmp) / "r.json"
        rc = v.main(["--evidence", str(real), "--output", str(out)])
        self.assertIn(rc, (0, 2))


class CLI(Base):
    def test_build_replay_exclusive_args(self):
        evp = pathlib.Path(self.tmp) / "e.json"
        outp = pathlib.Path(self.tmp) / "r.json"
        self.assertEqual(v.main(["--archive-base", str(self.base), "--build-evidence", str(evp),
                                 "--output", str(outp)]), 0)
        # 独占：再次写同路径被拒
        self.assertEqual(v.main(["--archive-base", str(self.base), "--build-evidence", str(evp),
                                 "--output", str(outp)]), 2)
        # 参数互斥/缺失
        self.assertEqual(v.main(["--output", str(pathlib.Path(self.tmp) / "x.json")]), 2)
        self.assertEqual(v.main(["--evidence", str(evp), "--build-evidence", str(evp),
                                 "--output", str(pathlib.Path(self.tmp) / "y.json")]), 2)

    def test_public_replay_against_synthetic_constants(self):
        ev = self.build_ok()
        evp = pathlib.Path(self.tmp) / "e.json"
        evp.write_bytes(canon(ev))
        outp = pathlib.Path(self.tmp) / "r2.json"
        self.assertEqual(v.main(["--evidence", str(evp), "--output", str(outp)]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=1)
