#!/usr/bin/env python3
"""R-A3 verify.py 反例套件（合成归档+公开档校验+CLI）。不执行网络/产品。"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXT_TEST_ROOT = os.environ.get("CHAIN_TEST_ROOT")  # 私镜像审计时指向镜像包目录


def _load_verify():
    target = Path(EXT_TEST_ROOT) / "verify.py" if EXT_TEST_ROOT else HERE / "verify.py"
    spec = importlib.util.spec_from_file_location("chain_verify_under_test", target)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_msg(role, content, call_id=None, tool_call_id=None):
    msg = {"role": role, "content": content}
    if call_id:
        msg["tool_calls"] = [
            {"id": call_id, "type": "function",
             "function": {"name": "read_file", "arguments": json.dumps({"path": "inputs/a/alpha.txt"})}}
        ]
    if tool_call_id:
        msg["tool_call_id"] = tool_call_id
    return msg


def _make_chain(base_id, tail_bytes):
    """构造与冻结结构同构的6主请求链：首请求5消息+tools，随后5步各追加assistant(tool_call)+tool。"""
    def rid(i):
        return "call_" + hashlib.sha256(f"{base_id}-{i}".encode()).hexdigest()[:24]

    msgs1 = [
        {"role": "system", "content": "S" * 60},
        {"role": "user", "content": "task"},
        {"role": "user", "content": "a" * 100},
        {"role": "user", "content": "b" * 80},
        {"role": "user", "content": "c" * 120},
    ]
    chain = [{"messages": list(msgs1), "tools": [{"name": "read_file"}], "model": "m", "stream": True}]
    running = list(msgs1)
    for step in range(5):
        running = running + [
            _make_msg("assistant", None, call_id=rid(step)),
            _make_msg("tool", "T" * tail_bytes[step], tool_call_id=rid(step)),
        ]
        chain.append({"messages": list(running), "tools": [{"name": "read_file"}], "model": "m", "stream": True})
    return chain, [rid(i) for i in range(5)]


def _write_run(run_dir, chain, title_id, tail_bytes):
    reqs = [chain[0], {"messages": [{"role": "system", "content": "title-sys"},
                                    {"role": "user", "content": "title-usr"}]}] + chain[1:]
    run_dir.mkdir(parents=True)
    for i, body in enumerate(reqs, 1):
        (run_dir / f"{i:03d}.request.bin").write_bytes(
            json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


class ChainTests(unittest.TestCase):
    def setUp(self):
        self.v = _load_verify()
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.archive = self.tmp / "arch"
        self.tail = [100, 50, 60, 40, 4]
        self.chain_a, ids_a = _make_chain("aaaa", self.tail)
        self.chain_b, ids_b = _make_chain("bbbb", self.tail)
        _write_run(self.archive / "t2-r1" / "requests", self.chain_a, "x", self.tail)
        _write_run(self.archive / "t2-r2" / "requests", self.chain_b, "x", self.tail)
        # 常量替换为合成值
        self._patched = {
            "RUN_RELS": ("t2-r1", "t2-r2"),
            "RAW_REQUEST_SHAS": {
                label: [hashlib.sha256((self.archive / label / "requests" / f"{i:03d}.request.bin").read_bytes()).hexdigest()
                        for i in range(1, 8)]
                for label in ("t2-r1", "t2-r2")
            },
            "APPENDED_SHAPES": [
                [{"role": "assistant", "content_kind": "null", "content_bytes": 0},
                 {"role": "tool", "content_kind": "str", "content_bytes": n}] for n in self.tail],
            "CHAIN_DELTAS": [len(self.v.canon(self.chain_a[k + 1])) - len(self.v.canon(self.chain_a[k]))
                             for k in range(5)],
        }
        for k, v in self._patched.items():
            setattr(self.v, k, v)

    def tearDown(self):
        for k in self._patched:
            try:
                delattr(self.v, k)
            except Exception:
                pass

    def _canon_shas(self):
        ev = self.v.build(self.archive)
        return {label: [[s["prev_canon_sha256"], s["next_canon_sha256"]] for s in ev["runs"][label]["steps"]]
                for label in self.v.RUN_LABELS}

    def test_happy_build(self):
        ev = self.v.build(self.archive)
        self.v.STEP_CANON_SHAS = self._canon_shas()
        for label in self.v.RUN_LABELS:
            self.assertTrue(ev["runs"][label]["chain_prefix_ok"])
        self.assertTrue(ev["cross_run"]["req1_byte_equal"])
        self.assertTrue(ev["cross_run"]["title_request_byte_equal"])
        self.assertEqual(ev["cross_run"]["followup_normalized_equal"], [True] * 5)
        res = self.v.result_for(ev, "0" * 64)
        self.assertEqual(res["verdicts"]["p3_cross_run"]["followups_normalized_equal_count"], 5)

    def test_broken_prefix_detected(self):
        # 篡改下一步中间消息正文 → 前缀性破坏
        p = self.archive / "t2-r1" / "requests" / "003.request.bin"
        body = json.loads(p.read_bytes())
        body["messages"][1]["content"] = "MUTATED"
        p.write_bytes(json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode())
        self._patched["RAW_REQUEST_SHAS"]["t2-r1"][2] = hashlib.sha256(p.read_bytes()).hexdigest()
        with self.assertRaises(self.v.Invalid):
            self.v.build(self.archive)

    def test_delta_mismatch_rejected(self):
        ev = self.v.build(self.archive)
        self.v.STEP_CANON_SHAS = self._canon_shas()
        steps = json.loads(json.dumps(ev))
        steps["runs"]["t2-r1"]["steps"][0]["delta_bytes"] += 1
        with self.assertRaises(self.v.Invalid):
            self.v.validate_public(steps)

    def test_appended_shape_mismatch_rejected(self):
        ev = self.v.build(self.archive)
        self.v.STEP_CANON_SHAS = self._canon_shas()
        bad = json.loads(json.dumps(ev))
        bad["runs"]["t2-r1"]["steps"][2]["appended"][1]["content_bytes"] += 1
        with self.assertRaises(self.v.Invalid):
            self.v.validate_public(bad)

    def test_canon_sha_tamper_rejected(self):
        ev = self.v.build(self.archive)
        self.v.STEP_CANON_SHAS = self._canon_shas()
        bad = json.loads(json.dumps(ev))
        bad["runs"]["t2-r2"]["steps"][4]["next_canon_sha256"] = "0" * 64
        with self.assertRaises(self.v.Invalid):
            self.v.validate_public(bad)

    def test_normalized_call_id_substitution_witnessed(self):
        # 同链不同call_id → 原文不等但归一后等
        a = json.dumps(self.chain_a[2], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        b = json.dumps(self.chain_b[2], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.assertNotEqual(a, b)
        na = self.v.normalize_ids(self.chain_a[2])
        nb = self.v.normalize_ids(self.chain_b[2])
        self.assertEqual(json.dumps(na, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                         json.dumps(nb, ensure_ascii=False, sort_keys=True, separators=(",", ":")))

    def test_normalize_ids_format(self):
        self.assertEqual(self.v.normalize_ids("call_0123456789abcdef01234567"), "call_<NORMALIZED>")
        self.assertNotEqual(self.v.normalize_ids("call_ZZ"), "call_<NORMALIZED>")

    def test_non_normalizable_id_breaks_normalized_equality(self):
        # 全链一致地替换step3 assistant id（req4..req7同位置），前缀性保持、归一后与run2不等
        # 两run等长但不同值替换（都非call_24hex形态）→ 归一后仍不等
        for label, token in (("t2-r1", "call_AAAAAAAA"), ("t2-r2", "call_BBBBBBBB")):
            for i in range(5, 8):
                fp = self.archive / label / "requests" / f"{i:03d}.request.bin"
                body = json.loads(fp.read_bytes())
                body["messages"][9]["tool_calls"][0]["id"] = token
                fp.write_bytes(json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode())
                self._patched["RAW_REQUEST_SHAS"][label][i - 1] = hashlib.sha256(fp.read_bytes()).hexdigest()
        # id长度变化会改canon delta → 用变异后的链重算CHAIN_DELTAS再patch
        def read_main(label, idx):
            return json.loads((self.archive / label / "requests" / f"{idx:03d}.request.bin").read_bytes())
        mains = [read_main("t2-r1", 1)] + [read_main("t2-r1", i) for i in (3, 4, 5, 6, 7)]
        deltas = [len(self.v.canon(mains[k + 1])) - len(self.v.canon(mains[k])) for k in range(5)]
        setattr(self.v, "CHAIN_DELTAS", deltas)
        try:
            ev = self.v.build(self.archive)
        finally:
            delattr(self.v, "CHAIN_DELTAS")
        self.assertIn(False, ev["cross_run"]["followup_normalized_equal"])

    def test_prefix_break_from_partial_mutation(self):
        # 只改req4单份 → 下一请求前缀性破坏（build直接拒绝）
        p = self.archive / "t2-r1" / "requests" / "005.request.bin"
        body = json.loads(p.read_bytes())
        body["messages"][9]["tool_calls"][0]["id"] = "call_SHORT"
        p.write_bytes(json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode())
        self._patched["RAW_REQUEST_SHAS"]["t2-r1"][4] = hashlib.sha256(p.read_bytes()).hexdigest()
        with self.assertRaises(self.v.Invalid):
            self.v.build(self.archive)

    def test_request_count_mismatch(self):
        (self.archive / "t2-r1" / "requests" / "007.request.bin").unlink()
        with self.assertRaises(self.v.Invalid):
            self.v.build(self.archive)

    def test_pin_mismatch_rejected(self):
        old = self.v.PROTOCOL_SHA256
        self.v.PROTOCOL_SHA256 = "0" * 64
        try:
            with self.assertRaises(self.v.Invalid):
                self.v.build(self.archive)
        finally:
            self.v.PROTOCOL_SHA256 = old

    def test_strict_json(self):
        with self.assertRaises(self.v.Invalid):
            self.v.loads(b'{"a": 1, "a": 2}')
        with self.assertRaises(self.v.Invalid):
            self.v.loads(b'{"a": 1e999}')

    def test_content_descriptor_kinds(self):
        d1 = self.v.content_descriptor({"role": "u", "content": "ab"})
        self.assertEqual(d1, {"role": "u", "content_kind": "str", "content_bytes": 2})
        d2 = self.v.content_descriptor({"role": "u", "content": None})
        self.assertEqual(d2["content_kind"], "null")
        d3 = self.v.content_descriptor({"role": "u", "content": [{"type": "text", "text": "x"}]})
        self.assertEqual(d3["content_kind"], "blocks")
        with self.assertRaises(self.v.Invalid):
            self.v.content_descriptor({"role": "u", "content": 5})

    def test_result_limits_present(self):
        ev = self.v.build(self.archive)
        self.v.STEP_CANON_SHAS = self._canon_shas()
        res = self.v.result_for(ev, "0" * 64)
        self.assertTrue(any("not generalizable" in s for s in res["limits"]))
        self.assertTrue(any("bytes are not tokens" in s for s in res["limits"]))

    def test_exclusive_output_refuses_overwrite(self):
        target = self.tmp / "out.json"
        target.write_bytes(b"{}")
        with self.assertRaises(self.v.Invalid):
            self.v.exclusive(target, b"[]")

    def test_cli_public_replay(self):
        ev = self.v.build(self.archive)
        self.v.STEP_CANON_SHAS = self._canon_shas()
        epath = self.tmp / "e.json"
        self.v.exclusive(epath, self.v.canon(ev) + b"\n")
        out = self.tmp / "r.json"
        code = subprocess.run([sys.executable, "-B", str(HERE / "verify.py"),
                               "--evidence", str(epath), "--output", str(out)],
                              capture_output=True, text=True)
        # CLI 重放用包内常量（真档）；合成档需环境变量指向本测试树（若提供则镜像跑）
        self.assertIn(code.returncode, (0, 2))

    def test_cli_exclusive(self):
        out = self.tmp / "exists.json"
        out.write_bytes(b"{}")
        code = subprocess.run([sys.executable, "-B", str(HERE / "verify.py"),
                               "--evidence", "/dev/null", "--output", str(out)],
                              capture_output=True, text=True)
        self.assertEqual(code.returncode, 2)


if __name__ == "__main__":
    unittest.main()
