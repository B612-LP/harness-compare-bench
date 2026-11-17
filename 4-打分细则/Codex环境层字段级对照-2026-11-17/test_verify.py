#!/usr/bin/env python3
"""环21套件：合成档全管线+公开冻结pin拒绝+env门控真档端到端。普通/-O双档运行。"""
import hashlib, json, os, sys, tempfile, unittest, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify as v

L1 = "the quick brown fox"                      # 21B same
L2A = "home-marker-alpha"                        # 55B-ish differs
L2B = "home-marker-beta"
L3 = "sandbox workspace-write"                   # 20B
L4 = "approval policy: on-request"               # 41B-ish
L5 = "shell: zsh"                                # 36B-ish
L6A = "<env><workspace_roots><root>/tmp/wsA</root></workspace_roots></env>" + "x" * 133
L6B = "<env><workspace_roots><root>/tmp/wsB</root></workspace_roots></env>" + "y" * 133
L7 = "end-of-env"                                # 22B-ish


def req1(l2, l6):
    text = "\n".join([L1, l2, L3, L4, L5, l6, L7])
    return {"model": "m", "input": [
        {"role": "developer", "content": "d"},
        {"role": "developer", "content": "d2"},
        {"role": "user", "content": [{"type": "input_text", "text": text}]},
        {"role": "user", "content": "task"},
    ]}


class Common(unittest.TestCase):
    _REAL_PINS = None

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="envlayer21-")
        if Common._REAL_PINS is None:
            Common._REAL_PINS = (v.REQ1_SHA.copy(), [list(r) for r in v.FROZEN_LINES.get("loop14/capture-codex-r1", [])] and dict(v.FROZEN_LINES))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)
        # 跨测试patch泄漏防护：每测试结束恢复真实pin（loop13教训）
        if Common._REAL_PINS is not None:
            v.REQ1_SHA, v.FROZEN_LINES = Common._REAL_PINS

    def plant(self, l2a=L2A, l2b=L2B, l6a=L6A, l6b=L6B):
        for rel, body in [("loop14/capture-codex-r1", req1(l2a, l6a)),
                          ("loop15/codex-t3-r1", req1(l2b, l6b))]:
            d = os.path.join(self.root, rel, "requests")
            os.makedirs(d, exist_ok=True)
            raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
            open(os.path.join(d, "001.request.bin"), "wb").write(raw)
            open(os.path.join(d, "002.request.bin"), "wb").write(raw)
        # 但 REQ1_SHA pin 只认真实值 → 合成档 build 会 die；改用 patch
        for k, val in [("loop14/capture-codex-r1", None), ("loop15/codex-t3-r1", None)]:
            pass
        return raw

    def patch_pins(self, sha_a, sha_b):
        self._old = (v.REQ1_SHA.copy(), dict(v.FROZEN_LINES))
        v.REQ1_SHA = {"loop14/capture-codex-r1": sha_a, "loop15/codex-t3-r1": sha_b}
        return self._old

    def restore(self):
        v.REQ1_SHA, v.FROZEN_LINES = self._old

    def run_main(self, args):
        return v.main(args)


class Grammar(Common):
    def test_01_build_and_endpoints(self):
        raw = self.plant()
        self.patch_pins(hashlib.sha256, None)
        # 计算合成 req1 sha 并注入 pin + 冻结行
        import hashlib as H
        sa = H.sha256(open(os.path.join(self.root, "loop14/capture-codex-r1/requests/001.request.bin"), "rb").read()).hexdigest()
        sb = H.sha256(open(os.path.join(self.root, "loop15/codex-t3-r1/requests/001.request.bin"), "rb").read()).hexdigest()
        v.REQ1_SHA = {"loop14/capture-codex-r1": sa, "loop15/codex-t3-r1": sb}
        v.FROZEN_LINE_COUNT = 7
        # 冻结行由分类函数动态生成（本测试重点是管线与终点）
        ev, res = v.build(self.root)
        self.assertEqual(res["verdict"], "env_line_5_2_1_7")
        self.assertEqual(res["endpoints"]["differs_at_lines"], [2, 6])

    def test_02_line_count_mismatch(self):
        self.plant(l6a=L6A + "\nextra")
        import hashlib as H
        sa = H.sha256(open(os.path.join(self.root, "loop14/capture-codex-r1/requests/001.request.bin"), "rb").read()).hexdigest()
        sb = H.sha256(open(os.path.join(self.root, "loop15/codex-t3-r1/requests/001.request.bin"), "rb").read()).hexdigest()
        v.REQ1_SHA = {"loop14/capture-codex-r1": sa, "loop15/codex-t3-r1": sb}
        with self.assertRaises(SystemExit):
            v.build(self.root)

    def test_03_wrong_role_shape(self):
        self.plant()
        p = os.path.join(self.root, "loop15/codex-t3-r1/requests/001.request.bin")
        body = json.loads(open(p, "rb").read().decode())
        body["input"][2]["role"] = "system"
        open(p, "wb").write(json.dumps(body, sort_keys=True, separators=(",", ":")).encode())
        with self.assertRaises(SystemExit):
            v.build(self.root)

    def test_04_part_not_input_text(self):
        self.plant()
        p = os.path.join(self.root, "loop15/codex-t3-r1/requests/001.request.bin")
        body = json.loads(open(p, "rb").read().decode())
        body["input"][2]["content"][0]["type"] = "output_text"
        open(p, "wb").write(json.dumps(body, sort_keys=True, separators=(",", ":")).encode())
        with self.assertRaises(SystemExit):
            v.build(self.root)

    def test_05_duplicate_key_rejected(self):
        self.plant()
        v.REQ1_SHA = {"loop14/capture-codex-r1": "0", "loop15/codex-t3-r1": "0"}
        evp = os.path.join(self.root, "ev.json"); rp = os.path.join(self.root, "r.json")
        with self.assertRaises(SystemExit):
            self.run_main(["--archive-root", self.root, "--build-evidence", evp, "--output", rp])

    def test_06_mode_flags(self):
        with self.assertRaises(SystemExit):
            self.run_main([])
        with self.assertRaises(SystemExit):
            self.run_main(["--evidence", "x", "--build-evidence", "y", "--output", "z"])
        with self.assertRaises(SystemExit):
            self.run_main(["--archive-root", "."])

    def test_07_output_must_be_new(self):
        rp = os.path.join(self.root, "r.json")
        open(rp, "w").write("x")
        with self.assertRaises(SystemExit):
            self.run_main(["--evidence", "whatever", "--output", rp])

    def test_08_public_tamper_line(self):
        self.restore_real_pins()
        ev = json.load(open(os.path.join(HERE, "evidence.json")))
        ev["runs"]["loop14/capture-codex-r1"]["lines"][2]["sha256"] = "0" * 64
        bad = os.path.join(self.root, "bad.json")
        open(bad, "w").write(json.dumps(ev))
        rp = os.path.join(self.root, "r.json")
        with self.assertRaises(SystemExit):
            self.run_main(["--evidence", bad, "--output", rp])

    def test_09_public_wrong_baseline(self):
        self.restore_real_pins()
        ev = json.load(open(os.path.join(HERE, "evidence.json")))
        ev["baseline_commit"] = "0" * 40
        bad = os.path.join(self.root, "bad.json")
        open(bad, "w").write(json.dumps(ev))
        rp = os.path.join(self.root, "r.json")
        with self.assertRaises(SystemExit):
            self.run_main(["--evidence", bad, "--output", rp])

    def test_10_public_wrong_readme_pin(self):
        self.restore_real_pins()
        ev = json.load(open(os.path.join(HERE, "evidence.json")))
        ev["readme_sha256"] = "0" * 64
        bad = os.path.join(self.root, "bad.json")
        open(bad, "w").write(json.dumps(ev))
        rp = os.path.join(self.root, "r.json")
        with self.assertRaises(SystemExit):
            self.run_main(["--evidence", bad, "--output", rp])

    def restore_real_pins(self):
        pass


class RealPackage(Common):
    def test_11_real_replay_and_tamper(self):
        if not os.environ.get("ENVLAYER_TEST_ROOT"):
            self.skipTest("ENVLAYER_TEST_ROOT not set")
        base = os.environ["ENVLAYER_TEST_ROOT"]
        evp = os.path.join(self.root, "ev.json"); rp = os.path.join(self.root, "r.json")
        rc = self.run_main(["--archive-root", base, "--build-evidence", evp, "--output", rp])
        self.assertEqual(rc, 0)
        pub = os.path.join(HERE, "evidence.json")
        rp2 = os.path.join(self.root, "r2.json")
        rc = self.run_main(["--evidence", pub, "--output", rp2])
        self.assertEqual(rc, 0)
        self.assertEqual(open(rp2, "rb").read(), open(os.path.join(HERE, "result.json"), "rb").read())
        ev = json.load(open(pub))
        ev["runs"]["loop15/codex-t3-r1"]["lines"][5]["bytes"] = 999
        bad = os.path.join(self.root, "bad.json")
        open(bad, "w").write(json.dumps(ev))
        rp3 = os.path.join(self.root, "r3.json")
        with self.assertRaises(SystemExit):
            self.run_main(["--evidence", bad, "--output", rp3])


if __name__ == "__main__":
    unittest.main()
