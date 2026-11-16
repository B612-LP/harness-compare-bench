#!/usr/bin/env python3
"""请求侧跨运行重建验证 verify.py 的对抗与回归测试（stdlib unittest）。

真档重放测试需要 REBUILD_EVIDENCE_PATH 指向首份 evidence.json；未设置则跳过，
保证公开套件不依赖私有归档。
"""
import hashlib
import importlib.util
import json
import os
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TEST_ROOT = os.environ.get("REBUILD_TEST_ROOT") or os.path.dirname(os.path.dirname(HERE))

spec = importlib.util.spec_from_file_location("rv", os.path.join(HERE, "verify.py"))
rv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rv)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def hexid(tag):
    return "call_" + (tag * 24)[:24]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(dir=HERE)
        self._patches = []
        self.orig = {}

    def patch(self, name, value):
        self.orig[name] = getattr(rv, name)
        self._patches.append(name)
        setattr(rv, name, value)

    def tearDown(self):
        for name in self._patches:
            setattr(rv, name, self.orig[name])
        shutil.rmtree(self.tmp, ignore_errors=True)

    def install(self, dirs):
        shas = {
            "run1": [sha(open(os.path.join(dirs["run1"], "requests", "00%d.request.bin" % i), "rb").read()) for i in (1, 2, 3)],
            "run2": [sha(open(os.path.join(dirs["run2"], "requests", "00%d.request.bin" % i), "rb").read()) for i in (1, 2, 3)],
        }
        self.patch("REQ_SHAS", shas)
        self.patch("REQ1_SHA", shas["run1"][0])
        self.patch("REQ2_SHA", shas["run1"][1])
        self.patch("REQ3_R1_SHA", shas["run1"][2])
        self.patch("REQ3_R2_SHA", shas["run2"][2])
        delta = os.path.getsize(os.path.join(dirs["run1"], "requests", "003.request.bin")) - os.path.getsize(os.path.join(dirs["run1"], "requests", "001.request.bin"))
        self.patch("REQ3_APPEND_DELTA", delta)

    def ev(self, dirs):
        return rv.build(TEST_ROOT, dirs["run1"], dirs["run2"])


def make_pair(tmp, ids1, ids2, tamper=None, statuses=(200, 200, 200), req3_mutate=None):
    """构建合成 run1/run2 目录；tamper=(run,index) 翻转一个字节。"""

    def body(msgs):
        return json.dumps({"model": "glm-5.3-flash", "messages": msgs}, ensure_ascii=False).encode("utf-8")

    base_msgs = [{"role": "system", "content": "S" * 30}, {"role": "user", "content": "u" * 20}]
    req1 = body(base_msgs)

    def req3_for(ids):
        msgs = list(base_msgs) + [
            {"role": "assistant", "content": None, "tool_calls": [
                {"id": ids[0], "type": "function", "function": {"name": "read", "arguments": {"path": "TASK.md"}}},
                {"id": ids[1], "type": "function", "function": {"name": "read", "arguments": {"path": "a.py"}}}]},
            {"role": "tool", "tool_call_id": ids[0], "content": "# T\n" * 4},
            {"role": "tool", "tool_call_id": ids[1], "content": "def can_chain():" + "x" * 10},
        ]
        return body(msgs)

    req3_1 = req3_for(ids1)
    if req3_mutate:
        req3_1 = req3_mutate(req3_1)
    req3_2 = req3_for(ids2)
    dirs = {}
    for label, third in (("run1", req3_1), ("run2", req3_2)):
        d = os.path.join(tmp, label)
        os.makedirs(os.path.join(d, "requests"))
        for i, b in enumerate((req1, req1, third), 1):
            raw = b
            if tamper and tamper[0] == label and tamper[1] == i:
                raw = bytes([raw[0] ^ 0x01]) + raw[1:]
            open(os.path.join(d, "requests", "00%d.request.bin" % i), "wb").write(raw)
        with open(os.path.join(d, "summary.jsonl"), "w") as f:
            for st in statuses:
                f.write(json.dumps({"method": "POST", "upstream_status": st}) + "\n")
        dirs[label] = d
    return dirs


class Grammar(Base):
    def test_happy_path(self):
        dirs = make_pair(self.tmp, [hexid("a"), hexid("b")], [hexid("c"), hexid("d")])
        self.install(dirs)
        ev = self.ev(dirs)
        self.assertTrue(ev["run2_prefix_identity"])
        self.assertEqual(ev["req3_diff"]["leaf_count"], 4)
        self.assertEqual({r["class"] for r in ev["req3_diff"]["leaf_rows"]}, {"provider_call_id"})

    def test_req1_tampered_byte(self):
        dirs = make_pair(self.tmp, [hexid("a"), hexid("b")], [hexid("c"), hexid("d")], tamper=("run1", 1))
        self.install(dirs)
        with self.assertRaises(ValueError):
            self.ev(dirs)

    def test_req3_identical_leaf_count_zero(self):
        ids = [hexid("a"), hexid("b")]
        dirs = make_pair(self.tmp, ids, ids)
        self.install(dirs)
        with self.assertRaises(ValueError):
            self.ev(dirs)

    def test_content_leaf_diff_is_unexpected(self):
        def mutate(raw):
            obj = json.loads(raw)
            obj["messages"][4]["content"] = obj["messages"][4]["content"] + "DIFF"
            return json.dumps(obj, ensure_ascii=False).encode("utf-8")
        dirs = make_pair(self.tmp, [hexid("a"), hexid("b")], [hexid("c"), hexid("d")], req3_mutate=mutate)
        self.install(dirs)
        with self.assertRaises(ValueError):
            self.ev(dirs)

    def test_prefix_broken(self):
        dirs = make_pair(self.tmp, [hexid("a"), hexid("b")], [hexid("c"), hexid("d")])
        self.install(dirs)
        p = os.path.join(dirs["run2"], "requests", "003.request.bin")
        obj = json.loads(open(p, "rb").read())
        obj["messages"][0]["content"] = "T" * 30
        open(p, "wb").write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))
        for i in (1, 2, 3):
            rv.REQ_SHAS["run2"][i - 1] = sha(open(os.path.join(dirs["run2"], "requests", "00%d.request.bin" % i), "rb").read())
        rv.REQ3_R2_SHA = rv.REQ_SHAS["run2"][2]
        with self.assertRaises(ValueError):
            self.ev(dirs)

    def test_bad_summary_status(self):
        dirs = make_pair(self.tmp, [hexid("a"), hexid("b")], [hexid("c"), hexid("d")], statuses=(200, 200, 500))
        self.install(dirs)
        with self.assertRaises(ValueError):
            self.ev(dirs)


class PublicEvidence(Base):
    def test_tamper_leaf_class(self):
        dirs = make_pair(self.tmp, [hexid("a"), hexid("b")], [hexid("c"), hexid("d")])
        self.install(dirs)
        ev = self.ev(dirs)
        ev["req3_diff"]["leaf_rows"][0]["class"] = "UNEXPECTED"
        with self.assertRaises(ValueError):
            rv.validate_public(ev)

    def test_baseline_changed(self):
        dirs = make_pair(self.tmp, [hexid("a"), hexid("b")], [hexid("c"), hexid("d")])
        self.install(dirs)
        ev = self.ev(dirs)
        ev["baseline"] = "0" * 40
        with self.assertRaises(ValueError):
            rv.validate_public(ev)

    def test_limits_changed(self):
        dirs = make_pair(self.tmp, [hexid("a"), hexid("b")], [hexid("c"), hexid("d")])
        self.install(dirs)
        ev = self.ev(dirs)
        ev["limits"] = ["anything"]
        with self.assertRaises(ValueError):
            rv.validate_public(ev)

    def test_statuses_short(self):
        dirs = make_pair(self.tmp, [hexid("a"), hexid("b")], [hexid("c"), hexid("d")])
        self.install(dirs)
        ev = self.ev(dirs)
        ev["run2_statuses"] = [200, 200]
        with self.assertRaises(ValueError):
            rv.validate_public(ev)

    def test_pins_req1_equality_broken(self):
        dirs = make_pair(self.tmp, [hexid("a"), hexid("b")], [hexid("c"), hexid("d")])
        self.install(dirs)
        ev = self.ev(dirs)
        ev["pins"]["req_sha256"]["run2"][0] = "f" * 64
        with self.assertRaises(ValueError):
            rv.validate_public(ev)

    def test_result_for_shape(self):
        dirs = make_pair(self.tmp, [hexid("a"), hexid("b")], [hexid("c"), hexid("d")])
        self.install(dirs)
        ev = self.ev(dirs)
        result = rv.result_for(ev, "d" * 64)
        self.assertEqual(result["primary_verdict"], "identity_assembly_stable")
        self.assertEqual(result["req1"]["equal"], True)
        self.assertEqual(result["req3"]["diff_class"], "provider_call_id_only")

    def test_real_public_evidence_replay(self):
        ev_path = os.environ.get("REBUILD_EVIDENCE_PATH")
        if not ev_path or not os.path.exists(ev_path):
            self.skipTest("REBUILD_EVIDENCE_PATH not set")
        raw = open(ev_path, "rb").read().rstrip(b"\n")
        evidence = rv.loads(raw)
        self.assertTrue(rv.validate_public(evidence))
        result = rv.result_for(evidence, sha(raw))
        self.assertEqual(result["primary_verdict"], "identity_assembly_stable")


class CLI(Base):
    def test_output_exists_rejected(self):
        out = os.path.join(self.tmp, "exists.json")
        open(out, "w").write("{}")
        self.assertEqual(rv.main(["--root", TEST_ROOT, "--evidence", out, "--output", out]), 2)

    def test_missing_args_exit2(self):
        self.assertEqual(rv.main(["--root", TEST_ROOT, "--output", os.path.join(self.tmp, "o.json")]), 2)

    def test_public_replay_to_fresh_output(self):
        dirs = make_pair(self.tmp, [hexid("a"), hexid("b")], [hexid("c"), hexid("d")])
        self.install(dirs)
        ev = self.ev(dirs)
        ev_path = os.path.join(self.tmp, "ev.json")
        open(ev_path, "wb").write(rv.canonical(ev) + b"\n")
        out = os.path.join(self.tmp, "result.json")
        self.assertEqual(rv.main(["--root", TEST_ROOT, "--evidence", ev_path, "--output", out]), 0)
        obj = json.loads(open(out, "rb").read())
        self.assertEqual(obj["primary_verdict"], "identity_assembly_stable")


if __name__ == "__main__":
    unittest.main(verbosity=1)
