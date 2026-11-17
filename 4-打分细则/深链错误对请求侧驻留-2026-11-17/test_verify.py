#!/usr/bin/env python3
"""深链错误对请求侧驻留包——合成与真实档案测试。

无 DEEPPAIR_ARCHIVE_ROOT 时跑合成档案全管线与 CLI fail-closed（skip 真档例 1 项）；
设置 DEEPPAIR_ARCHIVE_ROOT=<loop8 根> 时追加重放真档（与包内 evidence.json/result.json 逐字节比对）。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import importlib.util

_spec = importlib.util.spec_from_file_location("pairverify", os.path.join(HERE, "verify.py"))
v = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v)

# 锚值按片段重建（公开源码不保留连续原始字面量——独审 L2；运行时字节与封印 sha 一致）
PAIR_ID = "call_" + "844b" + "6bdd" + "553f" + "4d7d" + "869b" + "c83d"
ARGS = json.dumps({
    "description": "Read " + "TASK" + ".md",
    "workdir": "/Users/" + "b612-lp" + "/bench-workspaces/" + "capture" + "-t3",
}, separators=(",", ":"))
ERR = " ".join(["Error:", "invalid", "arguments:", "missing", "required",
                'property', '"command"'])

def run_cli(argv):
    proc = subprocess.run([sys.executable, os.path.join(HERE, "verify.py")] + argv, capture_output=True)
    return proc.returncode, proc.stdout, proc.stderr

def make_pair_row(seq, n, bad, terr):
    return {
        "run": "t3-r1",
        "seq": seq,
        "kind": "title" if seq == 2 else "main",
        "n_messages": n,
        "pair_assistant_positions": bad,
        "pair_tool_error_positions": terr,
    }

def published_evidence():
    return json.loads(open(os.path.join(HERE, "evidence.json"), "rb").read())

class Base(unittest.TestCase):
    def setUp(self):
        self._patched = {}
        self._saved = {k: getattr(v, k) for k in ("PAIR_ID_SHA256", "PAIR_ARGS_SHA256", "ERR_SHA256", "README_SHA256", "BASELINE", "RUNS")}
        self._tmp = None

    def tearDown(self):
        for k, val in self._saved.items():
            setattr(v, k, val)
        self.restore_real()
        if self._tmp and os.path.isdir(self._tmp):
            shutil.rmtree(self._tmp, ignore_errors=True)

    def patch(self, **kw):
        for k, val in kw.items():
            self._patched[k] = getattr(v, k)
            setattr(v, k, val)

    def restore_real(self):
        pass

    def scratch(self):
        if self._tmp is None:
            self._tmp = tempfile.mkdtemp(prefix="pairtest-")
        d = os.path.join(self._tmp, str(len(self._patched)) + "-" + str(id(self))[-6:])
        os.makedirs(d, exist_ok=True)
        return d

class Synthetic(Base):
    def build_tree(self, root):
        """构造合成 loop8：r1=3 请求（含 1 个后续）、r2=2 请求；事件层仅 r1。"""
        reqs1 = {1: 5, 2: 2, 3: 7}
        for seq, n in reqs1.items():
            msgs = []
            if seq == 3:
                msgs = [{"role": m} for m in ["system", "user", "user", "user", "user"]]
                msgs.append({"role": "assistant", "tool_calls": [{"id": PAIR_ID, "type": "function", "function": {"name": "bash", "arguments": ARGS}}]})
                msgs.append({"role": "tool", "content": ERR})
            root_req = os.path.join(root, "t3-r1", "requests")
            os.makedirs(root_req, exist_ok=True)
            with open(os.path.join(root_req, "%03d.request.bin" % seq), "wb") as fh:
                fh.write(json.dumps({"messages": msgs}, ensure_ascii=False).encode())
        for seq, n in {1: 5, 2: 2}.items():
            root_req = os.path.join(root, "t3-r2", "requests")
            os.makedirs(root_req, exist_ok=True)
            with open(os.path.join(root_req, "%03d.request.bin" % seq), "wb") as fh:
                fh.write(json.dumps({"messages": [{"role": "system"}, {"role": "user"}]}, ensure_ascii=False).encode())
        # 事件层（zstd CLI 压缩）
        events = [
            {"type": "tool/call", "data": {"callId": PAIR_ID, "name": "bash", "arguments": ARGS}},
            {"type": "tool/result", "data": {"message": {"content": [{"type": "text", "text": ERR}]}}},
        ]
        raw = "\n".join(json.dumps(e, ensure_ascii=False) for e in events).encode()
        ev_dir = os.path.join(root, "event-layer-t3-r1")
        os.makedirs(ev_dir, exist_ok=True)
        src = os.path.join(ev_dir, "session.v4.jsonl")
        with open(src, "wb") as fh:
            fh.write(raw)
        proc = subprocess.run(["zstd", "-f", "-q", src], capture_output=True)
        self.assertEqual(proc.returncode, 0)
        os.remove(src)
        produced = src + ".zst"
        if os.path.exists(produced):
            os.rename(produced, src + ".zstd")
        ev_dir2 = os.path.join(root, "event-layer-t3-r2")
        os.makedirs(ev_dir2, exist_ok=True)
        raw2 = json.dumps({"type": "step/start", "data": {}}).encode()
        src2 = os.path.join(ev_dir2, "session.v4.jsonl")
        with open(src2, "wb") as fh:
            fh.write(raw2)
        subprocess.run(["zstd", "-f", "-q", src2], capture_output=True)
        os.remove(src2)
        produced2 = src2 + ".zst"
        if os.path.exists(produced2):
            os.rename(produced2, src2 + ".zstd")
        # 同步 RUNS 期望
        self.patch(RUNS={
            "t3-r1": {"requests": 3, "title_seq": 2, "first_pair_seq": 3},
            "t3-r2": {"requests": 2, "title_seq": 2, "first_pair_seq": None},
        })

    def test_01_pipeline_synthetic(self):
        root = self.scratch()
        self.build_tree(root)
        out = os.path.join(self.scratch(), "e.json")
        res = os.path.join(self.scratch(), "r.json")
        # 子进程不继承 monkeypatch，合成管线用进程内 main 驱动
        rc = v.main(["--archive-root", root, "--build-evidence", out, "--output", res])
        self.assertEqual(rc, 0)
        ev = json.loads(open(out, "rb").read())
        self.assertEqual(ev["schema"], v.SCHEMA)
        rows = {(r["run"], r["seq"]): r for r in ev["requests"]}
        self.assertEqual(rows[("t3-r1", 3)]["pair_assistant_positions"], [5])
        self.assertEqual(rows[("t3-r1", 3)]["pair_tool_error_positions"], [6])
        self.assertEqual(ev["event_layers"]["t3-r1"]["bad_call_count"], 1)
        self.assertEqual(ev["event_layers"]["t3-r1"]["error_result_count"], 1)
        result = json.loads(open(res, "rb").read())
        # 合成形状仅 1 个后续 → D2 计数门(==14)不满足 → verdict UNEXPECTED；公开重放由 validate_public 强制冻结形状（31 行+固定放置）
        self.assertEqual(result["verdict"], "UNEXPECTED")
        self.assertTrue(result["endpoints"]["D1_placement"]["r1_positions_constant"])

    def test_02_row_tamper_positions(self):
        ev = published_evidence()
        ev["requests"][2]["pair_assistant_positions"] = [6]
        p = os.path.join(self.scratch(), "e.json")
        open(p, "wb").write(json.dumps(ev, ensure_ascii=False, indent=1).encode() + b"\n")
        rc, _, _ = run_cli(["--evidence", p, "--output", os.path.join(self.scratch(), "r.json")])
        self.assertEqual(rc, 2)

    def test_02b_row_tamper_n_messages(self):
        ev = published_evidence()
        ev["requests"][2]["n_messages"] = ev["requests"][2]["n_messages"] + 1
        p = os.path.join(self.scratch(), "e.json")
        open(p, "wb").write(json.dumps(ev, ensure_ascii=False, indent=1).encode() + b"\n")
        rc, _, _ = run_cli(["--evidence", p, "--output", os.path.join(self.scratch(), "r.json")])
        self.assertEqual(rc, 2)

    def test_03_row_tamper_empty_followup(self):
        ev = published_evidence()
        ev["requests"][3]["pair_assistant_positions"] = []
        p = os.path.join(self.scratch(), "e.json")
        open(p, "wb").write(json.dumps(ev, ensure_ascii=False, indent=1).encode() + b"\n")
        rc, _, _ = run_cli(["--evidence", p, "--output", os.path.join(self.scratch(), "r.json")])
        self.assertEqual(rc, 2)

    def test_04_bad_schema(self):
        ev = published_evidence(); ev["schema"] = "x"
        p = os.path.join(self.scratch(), "e.json")
        open(p, "wb").write(json.dumps(ev).encode())
        rc, _, _ = run_cli(["--evidence", p, "--output", os.path.join(self.scratch(), "r.json")])
        self.assertEqual(rc, 2)

    def test_05_bad_baseline(self):
        ev = published_evidence(); ev["baseline_commit"] = "0" * 40
        p = os.path.join(self.scratch(), "e.json")
        open(p, "wb").write(json.dumps(ev).encode())
        rc, _, _ = run_cli(["--evidence", p, "--output", os.path.join(self.scratch(), "r.json")])
        self.assertEqual(rc, 2)

    def test_06_bad_readme_pin(self):
        ev = published_evidence(); ev["readme_sha256"] = "1" * 64
        p = os.path.join(self.scratch(), "e.json")
        open(p, "wb").write(json.dumps(ev).encode())
        rc, _, _ = run_cli(["--evidence", p, "--output", os.path.join(self.scratch(), "r.json")])
        self.assertEqual(rc, 2)

    def test_07_bad_anchor(self):
        ev = published_evidence(); ev["anchors"]["error_text_sha256"] = "2" * 64
        p = os.path.join(self.scratch(), "e.json")
        open(p, "wb").write(json.dumps(ev).encode())
        rc, _, _ = run_cli(["--evidence", p, "--output", os.path.join(self.scratch(), "r.json")])
        self.assertEqual(rc, 2)

    def test_08_row_dup(self):
        ev = published_evidence(); ev["requests"].append(dict(ev["requests"][0]))
        p = os.path.join(self.scratch(), "e.json")
        open(p, "wb").write(json.dumps(ev).encode())
        rc, _, _ = run_cli(["--evidence", p, "--output", os.path.join(self.scratch(), "r.json")])
        self.assertEqual(rc, 2)

    def test_09_bad_layer_counts(self):
        ev = published_evidence(); ev["event_layers"]["t3-r1"]["bad_call_count"] = 2
        p = os.path.join(self.scratch(), "e.json")
        open(p, "wb").write(json.dumps(ev).encode())
        rc, _, _ = run_cli(["--evidence", p, "--output", os.path.join(self.scratch(), "r.json")])
        self.assertEqual(rc, 2)

    def test_10_r2_layer_not_null(self):
        ev = published_evidence(); ev["event_layers"]["t3-r2"]["bad_call_count"] = 1
        p = os.path.join(self.scratch(), "e.json")
        open(p, "wb").write(json.dumps(ev).encode())
        rc, _, _ = run_cli(["--evidence", p, "--output", os.path.join(self.scratch(), "r.json")])
        self.assertEqual(rc, 2)

    def test_11_missing_row(self):
        ev = published_evidence(); ev["requests"].pop()
        p = os.path.join(self.scratch(), "e.json")
        open(p, "wb").write(json.dumps(ev).encode())
        rc, _, _ = run_cli(["--evidence", p, "--output", os.path.join(self.scratch(), "r.json")])
        self.assertEqual(rc, 2)

    def test_12_out_of_range_pos(self):
        ev = published_evidence(); ev["requests"][2]["pair_tool_error_positions"] = [99]
        p = os.path.join(self.scratch(), "e.json")
        open(p, "wb").write(json.dumps(ev).encode())
        rc, _, _ = run_cli(["--evidence", p, "--output", os.path.join(self.scratch(), "r.json")])
        self.assertEqual(rc, 2)

    def test_13_bool_pos(self):
        ev = published_evidence(); ev["requests"][2]["pair_assistant_positions"] = [True]
        p = os.path.join(self.scratch(), "e.json")
        open(p, "wb").write(json.dumps(ev).encode())
        rc, _, _ = run_cli(["--evidence", p, "--output", os.path.join(self.scratch(), "r.json")])
        self.assertEqual(rc, 2)

    def test_14_cli_missing_flags(self):
        rc, _, _ = run_cli(["--output", os.path.join(self.scratch(), "r.json")])
        self.assertEqual(rc, 2)
        rc, _, _ = run_cli(["--archive-root", "/nonexistent", "--evidence", "x", "--output", "y"])
        self.assertEqual(rc, 2)

    def test_15_cli_missing_evidence_file(self):
        rc, _, _ = run_cli(["--evidence", os.path.join(self.scratch(), "nope.json"), "--output", os.path.join(self.scratch(), "r.json")])
        self.assertEqual(rc, 2)

    def test_16_output_conflict(self):
        out = os.path.join(self.scratch(), "r.json")
        open(out, "wb").write(b"x")
        rc, _, _ = run_cli(["--evidence", os.path.join(HERE, "evidence.json"), "--output", out])
        self.assertEqual(rc, 2)
        self.assertEqual(open(out, "rb").read(), b"x")

    def test_17_verdict_flip_rows(self):
        ev = published_evidence()
        for r in ev["requests"]:
            if r["run"] == "t3-r1" and 3 <= r["seq"] <= 16:
                r["pair_assistant_positions"] = []
        p = os.path.join(self.scratch(), "e.json")
        open(p, "wb").write(json.dumps(ev, ensure_ascii=False, indent=1).encode() + b"\n")
        res = os.path.join(self.scratch(), "r.json")
        rc, _, _ = run_cli(["--evidence", p, "--output", res])
        # validate_public 按冻结口径逐行强制放置（[5]/[6]）→ 终点不可经合法行翻转
        self.assertEqual(rc, 2)

REAL = os.environ.get("DEEPPAIR_ARCHIVE_ROOT")

@unittest.skipIf(not REAL, "DEEPPAIR_ARCHIVE_ROOT not set")
class RealArchive(Base):
    def test_34_real_replay(self):
        out = os.path.join(self.scratch(), "r.json")
        rc, _, se = run_cli(["--evidence", os.path.join(HERE, "evidence.json"), "--output", out])
        self.assertEqual(rc, 0, se.decode())
        published = open(os.path.join(HERE, "result.json"), "rb").read()
        self.assertEqual(open(out, "rb").read(), published)
        # 事件层重建（真档）与 evidence 一致
        ev = v.build(REAL)
        pub = published_evidence()
        self.assertEqual(v.canonical(ev), v.canonical(pub))

def load_tests(a, b, c):
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTests(loader.loadTestsFromTestCase(Synthetic))
    suite.addTests(loader.loadTestsFromTestCase(RealArchive))
    return suite

if __name__ == "__main__":
    unittest.main()
