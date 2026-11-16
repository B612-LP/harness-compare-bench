#!/usr/bin/env python3
"""Codex 深链与加密推理回放 verify.py 套件 — 合成两 run 全管线 + 真档分支。

四档：普通/-O × 有/无 CXCHAIN_ARCHIVE_BASE（真档分支）。
"""
import copy
import hashlib
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
    import importlib.util
    spec = importlib.util.spec_from_file_location("v15t", str(SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


v = load_module()

REAL = {
    "req1_shas": dict(v.REQ1_SHAS),
    "lens": copy.deepcopy(v.LENS_EXPECT),
    "shapes": copy.deepcopy(v.SHAPES_EXPECT),
    "norm_sha": v.REQ1_NORM_SHA,
    "task_sha": v.TASK_TEXT_SHA256,
    "workspace": v.WORKSPACE_AGG_SHA256,
    "readme": v.FROZEN_README_SHA256,
    "baseline": v.BASELINE,
}


def restore_real():
    v.REQ1_SHAS = dict(REAL["req1_shas"])
    v.LENS_EXPECT = copy.deepcopy(REAL["lens"])
    v.SHAPES_EXPECT = copy.deepcopy(REAL["shapes"])
    v.REQ1_NORM_SHA = REAL["norm_sha"]
    v.TASK_TEXT_SHA256 = REAL["task_sha"]
    v.WORKSPACE_AGG_SHA256 = REAL["workspace"]
    v.FROZEN_README_SHA256 = REAL["readme"]
    v.BASELINE = REAL["baseline"]


def sha(x):
    return hashlib.sha256(x).hexdigest()


def canon(o):
    return json.dumps(o, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def make_synth(base: Path):
    """合成两 run 三请求链：首请求 id 差 11 叶；req2/req3 追加形状一致（简化同形）；
    reasoning encrypted_content 跨 run 互异、summary 恒等。"""
    srcdir = base / "loop15" / "codex-t3-r1" / "requests"
    srcdir.mkdir(parents=True, exist_ok=True)
    srcdir2 = base / "loop15" / "codex-t3-r2" / "requests"
    srcdir2.mkdir(parents=True, exist_ok=True)
    meta_r1 = {"root_turn_id": "tr-r1", "session_id": "s-r1", "thread_id": "th-r1",
               "turn_id": "u-r1", "x-codex-turn-metadata": "m-r1", "x-codex-window-id": "w-r1"}
    meta_r2 = {k: v + "2" for k, v in meta_r1.items()}
    pck_r1, pck_r2 = "th-r1", "th-r2"
    meta_r2["thread_id"] = pck_r2

    task_text = "Read TASK.md and follow it exactly. Do not modify any files."

    def mk_req(meta, pck, items):
        return {"model": "deepseek-flash", "instructions": "dev", "input": items,
                "tools": [{"type": "function", "name": "exec_command"}],
                "store": False, "stream": True, "include": ["reasoning.encrypted_content"],
                "prompt_cache_key": pck, "client_metadata": meta}

    def base4(suffix):
        out = []
        for k in range(4):
            out.append({"type": "message", "id": "it%d-%s" % (k, suffix), "role": "user",
                        "content": [{"type": "input_text", "text": "u%d" % k}]})
        out[3] = {"type": "message", "id": "it-task-%s" % suffix, "role": "user",
                  "content": [{"type": "input_text", "text": task_text}]}
        return out

    def step(tag):
        return [{"type": "reasoning", "id": "rs-%s" % tag, "summary": [],
                 "encrypted_content": "ENC-RUN-%s" % tag},
                {"type": "function_call", "id": "fc-%s" % tag, "name": "exec_command", "arguments": "{}"},
                {"type": "function_call_output", "id": "out-%s" % tag, "output": "o%s" % tag}]

    r1_1 = base4("r1")
    r1_2 = r1_1 + step("r1a")
    r1_3 = r1_2 + step("r1b")
    r2_1 = base4("r2")
    r2_2 = r2_1 + step("r2a")
    r2_3 = r2_2 + step("r2b")
    r1_items = {1: r1_1, 2: r1_2, 3: r1_3}
    r2_items = {1: r2_1, 2: r2_2, 3: r2_3}
    lens = {"r1": [4, 7, 10], "r2": [4, 7, 10]}
    shapes = {"r1": [["reasoning", "function_call", "function_call_output"],
                     ["reasoning", "function_call", "function_call_output"]],
              "r2": [["reasoning", "function_call", "function_call_output"],
                     ["reasoning", "function_call", "function_call_output"]]}
    lens = {"r1": [4, 7, 10], "r2": [4, 7, 10]}
    shapes = {"r1": [["reasoning", "function_call", "function_call_output"],
                     ["reasoning", "function_call", "function_call_output"]],
              "r2": [["reasoning", "function_call", "function_call_output"],
                     ["reasoning", "function_call", "function_call_output"]]}
    syspath = base / "loop15" / "codex-t3-r1" / "requests"
    req_shas = {}
    for r, items in (("r1", r1_items), ("r2", r2_items)):
        d = base / "loop15" / ("codex-t3-" + r) / "requests"
        for i in (1, 2, 3):
            req = mk_req(meta_r1 if r == "r1" else meta_r2, pck_r1 if r == "r1" else pck_r2, items[i])
            if r == "r2" and i == 1:
                # 保证与 r1 req1 有恰 11 叶 id 差：改 input[0..3].id 已做；metadata/pck 已做
                pass
            raw = json.dumps(req, ensure_ascii=False, sort_keys=True).encode() + b"\n"
            (d / ("00%d.request.bin" % i)).write_bytes(raw)
            req_shas[(r, i)] = hashlib.sha256(raw).hexdigest()
    return {"srcdir": srcdir, "syspath": syspath, "req_shas": req_shas,
            "lens": lens, "shapes": shapes,
            "norm_sha": None, "task_sha": sha(task_text.encode())}


def refresh(mod, synth):
    import copy as _c
    mod.REQ1_SHAS = {"r1": synth["req_shas"][("r1", 1)], "r2": synth["req_shas"][("r2", 1)]}
    mod.LENS_EXPECT = copy.deepcopy(synth["lens"])
    mod.SHAPES_EXPECT = copy.deepcopy(synth["shapes"])
    # 反算 normalized canonical（首请求 diff 仅 id 类时成立）
    def loads(p):
        return json.loads(Path(p).read_bytes())

    def norm(req):
        d = json.loads(json.dumps(req))
        d["client_metadata"] = "NORMALIZED"
        d["prompt_cache_key"] = "NORMALIZED"
        for it in d.get("input", []):
            if isinstance(it, dict):
                if "id" in it:
                    it["id"] = "NORMALIZED"
                if "encrypted_content" in it:
                    it["encrypted_content"] = "NORMALIZED"
        return d
    a = loads(synth["srcdir"] / "001.request.bin")
    b = loads(base_synth_r2 / "001.request.bin")
    mod.REQ1_NORM_SHA = sha(canon(norm(a)))
    mod.TASK_TEXT_SHA256 = synth["task_sha"]
    mod.WORKSPACE_AGG_SHA256 = "0" * 64
    mod.FROZEN_README_SHA256 = "1" * 64
    mod.BASELINE = "2" * 40


base_synth_r2 = None  # set in setUpClass


class ChainBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global base_synth_r2
        restore_real()
        cls.mod = v
        cls.tmp = tempfile.mkdtemp(prefix="cxchain-synth-")
        cls.synth = make_synth(Path(cls.tmp))
        base_synth_r2 = Path(cls.tmp) / "loop15" / "codex-t3-r2" / "requests"
        refresh(v, cls.synth)

    @classmethod
    def tearDownClass(cls):
        restore_real()

    def test_01_build_and_validate(self):
        ev, evb, res = v.build(Path(self.tmp))
        v.validate_public(ev)
        self.assertEqual(canon(res) + b"\n", canon(v.result_for(ev, evb)) + b"\n")

    def test_02_encrypted_stability_shape(self):
        ev, _, _ = v.build(Path(self.tmp))
        enc = ev["encrypted_replay_stability"]
        self.assertFalse(enc["req2"][0]["encrypted_equal"])
        self.assertTrue(enc["req2"][0]["summary_equal"])

    def test_10_prefix_tamper_rc2(self):
        d = Path(self.tmp) / "loop15" / "codex-t3-r1" / "requests"
        raw = (d / "003.request.bin").read_bytes()
        obj = json.loads(raw)
        obj["input"] = obj["input"][:6]  # 破坏前缀性（len 6 != pin 10 由 lens pin 拦）
        (d / "003.request.bin").write_bytes(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode() + b"\n")
        try:
            with self.assertRaises(v.Invalid):
                v.build(Path(self.tmp))
        finally:
            (d / "003.request.bin").write_bytes(raw)

    def test_11_dup_key_rejected(self):
        with self.assertRaises(v.Invalid):
            v.loads(b'{"a":1,"a":2}')

    def test_12_nonfinite_rejected(self):
        with self.assertRaises(v.Invalid):
            v.loads(b'{"a":1e999}')

    def test_13_float_rejected(self):
        with self.assertRaises(v.Invalid):
            v.loads(b'{"a":1.5}')

    def test_20_public_replay_tamper_rc2(self):
        ev, evb, _ = v.build(Path(self.tmp))
        bad = json.loads(evb)
        bad["req1_cross_run"]["diff_leaves"] = 10
        out = Path(tempfile.mkdtemp()) / "e.json"
        out.write_bytes(canon(bad) + b"\n")
        rc = subprocess.run([sys.executable, "-B", str(SCRIPT), "--evidence", str(out), "--output", str(out) + ".r"], capture_output=True)
        self.assertEqual(rc.returncode, 2)

    def test_30_output_exists_rc2(self):
        d = Path(tempfile.mkdtemp())
        (d / "x").write_bytes(b"")
        rc = subprocess.run([sys.executable, "-B", str(SCRIPT), "--evidence", str(HERE / "evidence.json"), "--output", str(d / "x")], capture_output=True)
        self.assertEqual(rc.returncode, 2)

    def test_31_missing_args_rc2(self):
        rc = subprocess.run([sys.executable, "-B", str(SCRIPT), "--output", "/tmp/xx-nonexistent"], capture_output=True)
        self.assertEqual(rc.returncode, 2)


class RealPackage(unittest.TestCase):
    def setUp(self):
        restore_real()
        self.ev_path = HERE / "evidence.json"
        self.res_path = HERE / "result.json"
        if not (self.ev_path.is_file() and self.res_path.is_file()):
            self.skipTest("package evidence/result not present")

    def tearDown(self):
        restore_real()

    def test_40_public_replay_matches_result(self):
        evb = self.ev_path.read_bytes()
        ev = v.loads(evb)
        v.validate_public(ev)
        res = v.result_for(ev, evb)
        self.assertEqual(canon(res) + b"\n", self.res_path.read_bytes())


class Cli(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="cxchain-cli-")
        restore_real()

    @classmethod
    def tearDownClass(cls):
        restore_real()

    def test_50_real_build_then_replay_identical(self):
        base = os.environ.get("CXCHAIN_ARCHIVE_BASE")
        if not base:
            self.skipTest("CXCHAIN_ARCHIVE_BASE not set")
        out = Path(tempfile.mkdtemp(prefix="cxchain-real-"))
        rc = subprocess.run([sys.executable, "-B", str(SCRIPT), "--archive-base", base, "--build-evidence", str(out / "e.json"), "--output", str(out / "r.json")], capture_output=True)
        self.assertEqual(rc.returncode, 0, rc.stderr)
        self.assertEqual((out / "e.json").read_bytes(), (HERE / "evidence.json").read_bytes())
        self.assertEqual((out / "r.json").read_bytes(), (HERE / "result.json").read_bytes())
        rc = subprocess.run([sys.executable, "-B", str(SCRIPT), "--evidence", str(out / "e.json"), "--output", str(out / "r2.json")], capture_output=True)
        self.assertEqual(rc.returncode, 0, rc.stderr)
        self.assertEqual((out / "r2.json").read_bytes(), (HERE / "result.json").read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=1)
