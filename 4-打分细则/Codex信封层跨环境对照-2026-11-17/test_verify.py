#!/usr/bin/env python3
"""测试：合成档全管线 + 公开档篡改拒绝 + 真档端到端（env 门控）。普通/-O 双档运行。"""
import json, os, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify as v


def mk_item(role, text):
    return {"role": role, "content": text}


def codex_body(dev0, dev1, env, task, tools=2):
    return {"model": "m", "stream": True, "input": [mk_item("developer", dev0), mk_item("developer", dev1),
                                                    mk_item("user", env), mk_item("user", task)],
            "tools": [{"type": "function", "name": "t%d" % i} for i in range(tools)],
            "tool_choice": "auto", "parallel_tool_calls": True, "reasoning": {}, "store": False}


def dsh_body(system, task, extra=("e1", "e2", "e3"), tools=3):
    return {"model": "m", "messages": [mk_item("system", system), mk_item("user", task)] + [mk_item("user", x) for x in extra],
            "stream": True, "stream_options": {}, "max_tokens": 128, "tools": [{"type": "function", "function": {"name": "f%d" % i}} for i in range(tools)],
            "tool_stream": True, "thinking": {"type": "disabled"}}


class Common(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="envloop20-")
        self.outs = []
        self._patched = []

    def tearDown(self):
        import shutil
        shutil.rmtree(self.root, ignore_errors=True)
        for mod, name, val in self._patched:
            setattr(mod, name, val)

    def restore_real(self):
        for mod, name, val in self._patched:
            setattr(mod, name, val)
        self._patched = []

    def patch(self, name, value):
        self._patched.append((v, name, getattr(v, name)))
        setattr(v, name, value)

    def write_run(self, rel, body):
        d = os.path.join(self.root, rel, "requests")
        os.makedirs(d, exist_ok=True)
        raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        open(os.path.join(d, "001.request.bin"), "wb").write(raw)
        open(os.path.join(d, "002.request.bin"), "wb").write(raw)  # requests_in_run>=2 与公开允许集一致

    def plant_all(self, dev0="D0", dev1="D1", env="ENV", task_a="TA", task_b="TB",
                  sysmsg="SYS", env_b="ENV-X", dsh_task_b="TB2"):
        self.write_run("loop14/capture-codex-r1", codex_body(dev0, dev1, env, task_a))
        self.write_run("loop14/capture-codex-r2", codex_body(dev0, dev1, env, task_a))
        self.write_run("loop15/codex-t3-r1", codex_body(dev0, dev1, env_b, task_b))
        self.write_run("loop15/codex-t3-r2", codex_body(dev0, dev1, env_b, task_b))
        self.write_run("loop1/capture", dsh_body(sysmsg, "T1"))
        self.write_run("loop7/t2-r1", dsh_body(sysmsg, dsh_task_b))
        self.write_run("loop8/t3-r1", dsh_body(sysmsg, "T3"))

    def run_main(self, args):
        return v.main(args)


class Grammar(Common):
    def test_01_build_replay_endpoints(self):
        self.plant_all()
        evp = os.path.join(self.root, "ev.json"); rp = os.path.join(self.root, "r.json")
        rc = self.run_main(["--archive-root", self.root, "--build-evidence", evp, "--output", rp])
        self.assertEqual(rc, 0)
        # 合成档≠冻结真实行：公开重放路径必须拒绝（冻结 pin 生效）
        rp2 = os.path.join(self.root, "r2.json")
        with self.assertRaises(SystemExit):
            self.run_main(["--evidence", evp, "--output", rp2])
        res = json.load(open(rp))
        self.assertEqual(res["verdict"], "codex_inputenv_mixed_tools_stable__dsh_sys_stable_tools_stable")
        self.assertEqual(res["endpoints"]["E3_within_home"][0]["layers"][0]["classification"], "identical")
        self.assertEqual(res["endpoints"]["E2_cross_home"]["layers"][2]["classification"], "differs")

    def test_02_wrong_shape_codex_run(self):
        self.plant_all()
        self.write_run("loop14/capture-codex-r2", dsh_body("S", "T"))  # chat body in codex slot
        evp = os.path.join(self.root, "ev.json"); rp = os.path.join(self.root, "r.json")
        with self.assertRaises(SystemExit):
            self.run_main(["--archive-root", self.root, "--build-evidence", evp, "--output", rp])

    def test_03_wrong_shape_dsh_run(self):
        self.plant_all()
        self.write_run("loop7/t2-r1", codex_body("a", "b", "c", "d"))
        evp = os.path.join(self.root, "ev.json"); rp = os.path.join(self.root, "r.json")
        with self.assertRaises(SystemExit):
            self.run_main(["--archive-root", self.root, "--build-evidence", evp, "--output", rp])

    def test_04_duplicate_key(self):
        self.plant_all()
        d = os.path.join(self.root, "loop15/codex-t3-r1/requests")
        open(os.path.join(d, "001.request.bin"), "wb").write(b'{"model":"m","model":"x","input":[]}')
        evp = os.path.join(self.root, "ev.json"); rp = os.path.join(self.root, "r.json")
        with self.assertRaises(SystemExit):
            self.run_main(["--archive-root", self.root, "--build-evidence", evp, "--output", rp])

    def test_05_nonfinite(self):
        self.plant_all()
        d = os.path.join(self.root, "loop8/t3-r1/requests")
        open(os.path.join(d, "001.request.bin"), "wb").write(b'{"model":1e999,"messages":[{"role":"system","content":"s"},{"role":"user","content":"t"},{"role":"user","content":"a"},{"role":"user","content":"b"},{"role":"user","content":"c"}]}')
        evp = os.path.join(self.root, "ev.json"); rp = os.path.join(self.root, "r.json")
        with self.assertRaises(SystemExit):
            self.run_main(["--archive-root", self.root, "--build-evidence", evp, "--output", rp])

    def test_06_codex_missing_task_item(self):
        self.plant_all()
        body = codex_body("D0", "D1", "ENV", "TA")
        body["input"] = body["input"][:2]
        self.write_run("loop15/codex-t3-r1", body)
        evp = os.path.join(self.root, "ev.json"); rp = os.path.join(self.root, "r.json")
        with self.assertRaises(SystemExit):
            self.run_main(["--archive-root", self.root, "--build-evidence", evp, "--output", rp])

    def test_07_dsh_system_not_first(self):
        self.plant_all()
        body = dsh_body("SYS", "T")
        body["messages"][0]["role"] = "user"
        self.write_run("loop7/t2-r1", body)
        evp = os.path.join(self.root, "ev.json"); rp = os.path.join(self.root, "r.json")
        with self.assertRaises(SystemExit):
            self.run_main(["--archive-root", self.root, "--build-evidence", evp, "--output", rp])

    def test_08_mode_flags(self):
        self.plant_all()
        evp = os.path.join(self.root, "ev.json"); rp = os.path.join(self.root, "r.json")
        with self.assertRaises(SystemExit):
            self.run_main(["--archive-root", self.root, "--output", rp])
        with self.assertRaises(SystemExit):
            self.run_main(["--evidence", evp, "--build-evidence", "x", "--output", rp])
        with self.assertRaises(SystemExit):
            self.run_main([])

    def test_09_output_must_be_new(self):
        self.plant_all()
        rp = os.path.join(self.root, "r.json")
        open(rp, "w").write("x")
        evp = os.path.join(self.root, "ev.json")
        with self.assertRaises(SystemExit):
            self.run_main(["--archive-root", self.root, "--build-evidence", evp, "--output", rp])

    def test_10_public_tamper_role(self):
        self.plant_all()
        evp = os.path.join(self.root, "ev.json"); rp = os.path.join(self.root, "r.json")
        self.run_main(["--archive-root", self.root, "--build-evidence", evp, "--output", rp])
        ev = json.load(open(evp))
        ev["runs"]["loop14/capture-codex-r1"]["items"][0]["role"] = "user"
        bad = os.path.join(self.root, "bad.json")
        open(bad, "w").write(json.dumps(ev))
        rp2 = os.path.join(self.root, "r2.json")
        with self.assertRaises(SystemExit):
            self.run_main(["--evidence", bad, "--output", rp2])

    def test_11_public_tamper_sha(self):
        self.plant_all()
        evp = os.path.join(self.root, "ev.json"); rp = os.path.join(self.root, "r.json")
        self.run_main(["--archive-root", self.root, "--build-evidence", evp, "--output", rp])
        ev = json.load(open(evp))
        ev["runs"]["loop1/capture"]["items"][0]["sha256"] = "0" * 64
        bad = os.path.join(self.root, "bad.json")
        open(bad, "w").write(json.dumps(ev))
        rp2 = os.path.join(self.root, "r2.json")
        with self.assertRaises(SystemExit):
            self.run_main(["--evidence", bad, "--output", rp2])

    def test_12_public_wrong_baseline(self):
        self.plant_all()
        evp = os.path.join(self.root, "ev.json"); rp = os.path.join(self.root, "r.json")
        self.run_main(["--archive-root", self.root, "--build-evidence", evp, "--output", rp])
        ev = json.load(open(evp))
        ev["baseline_commit"] = "0" * 40
        bad = os.path.join(self.root, "bad.json")
        open(bad, "w").write(json.dumps(ev))
        rp2 = os.path.join(self.root, "r2.json")
        with self.assertRaises(SystemExit):
            self.run_main(["--evidence", bad, "--output", rp2])


class RealPackage(Common):
    def setUp(self):
        super().setUp()
        base = os.environ.get("ENVELOPE_TEST_ROOT")
        if not base:
            self._patched_real = None
            return
        self._patched_real = True
        self.base = base
        # 公开 pin 必须与真档一致
        self.patch("BASELINE", v.BASELINE)
        import hashlib
        self.real_readme = hashlib.sha256(open(os.path.join(HERE, "README.md"), "rb").read()).hexdigest()

    def test_13_real_replay(self):
        if not self._patched_real:
            self.skipTest("ENVELOPE_TEST_ROOT not set")
        evp = os.path.join(self.root, "ev.json"); rp = os.path.join(self.root, "r.json")
        rc = self.run_main(["--archive-root", self.base, "--build-evidence", evp, "--output", rp])
        self.assertEqual(rc, 0)
        pub_ev = os.path.join(HERE, "evidence.json")
        if os.path.exists(pub_ev):
            rp2 = os.path.join(self.root, "r2.json")
            rc = self.run_main(["--evidence", pub_ev, "--output", rp2])
            self.assertEqual(rc, 0)
            a = open(rp, "rb").read(); b = open(rp2, "rb").read()
            # 若公开档与本重建同源，则结果应逐字节一致
            ev_local = json.load(open(evp))
            ev_pub = json.load(open(pub_ev))
            if json.dumps(ev_local, sort_keys=True) == json.dumps(ev_pub, sort_keys=True):
                self.assertEqual(a, b)


    def test_14_real_public_tamper_sha(self):
        if not os.environ.get("ENVELOPE_TEST_ROOT"):
            self.skipTest("ENVELOPE_TEST_ROOT not set")
        pub_ev = os.path.join(HERE, "evidence.json")
        ev = json.load(open(pub_ev))
        ev["runs"]["loop1/capture"]["items"][0]["sha256"] = "0" * 64
        bad = os.path.join(self.root, "bad.json")
        open(bad, "w").write(json.dumps(ev))
        rp2 = os.path.join(self.root, "r2.json")
        with self.assertRaises(SystemExit):
            self.run_main(["--evidence", bad, "--output", rp2])

if __name__ == "__main__":
    unittest.main()
