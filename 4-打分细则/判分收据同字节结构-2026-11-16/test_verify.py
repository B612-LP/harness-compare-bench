#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_verify.py — 预注册包「判分收据同字节结构-2026-11-16」的 verify.py 验证套件。

按冻结 README §4：
- ≥14 个测试，python3 与 python3 -O 双档全绿（无 assert 依赖、无 skip 静默跳过）。
- 真档案端到端测试经环境变量 RECEIPT_COLLAPSE_ARCHIVE_ROOT 门控：未设置时
  该测试 loudly FAIL（拒绝静默跳过）。
- 合成用例覆盖：同元组+同材料→collapse；同元组+异材料+同字节→exit 2（矛盾，
  V1，单元级构造）；异元组同字节→exit 2（V2）；mtime 乱序→B-COPY-ANOMALY
  分支（非 exit）；--output 拒绝覆盖已有文件；篡改收据字节→分类改变被检测。

运行：python3 test_verify.py   （或 python3 -O test_verify.py）
"""
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

PKG_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(PKG_DIR))
VERIFY = os.path.join(PKG_DIR, "verify.py")
STORED_RESULT = os.path.join(PKG_DIR, "result.json")
ENV_VAR = "RECEIPT_COLLAPSE_ARCHIVE_ROOT"
PREREG_REL = os.path.join("4-打分细则", "判分收据同字节结构-2026-11-16",
                          "README.md")

PREREG_SHA256 = ("47c0fef7c563863b926af13cb1e8a3d3ea53272f63b32581aaf9"
                 "c311490ed074")
EXPECTED_SLOT_COUNT = 15

# ---- 真档案冻结断言常量（独立勘察复算值）----
SLOT_BIRD = "dsh__bird-ca-schools-15__r1"
SLOT_PREFIX_BIRD = "dsh__bird-ca-schools-15__r%d"
SLOT_PREFIX_EXE = "dsh__exercism-py-6__r%d"
SLOT_PREFIX_LCB = "dsh__lcb-recent-hard-4__r%d"
BIRD_R1_SHA = "bb54dbeae312e9dfd2cbfe5b5df9aa27344667042d3d68288f444320d4bfcab4"
BIRD_R23_SHA = ("1dbdcbd884a3a45d7aab8291e06d4ba7592683d8fc1677b217bea80e7"
                "efe39fa")
BIRD_R1_SIZE, BIRD_R23_SIZE = 706, 700
RR_R1_SHA = "132a1fc0d0a79396d3982ea565c0c44144e3ad2e08cfe52d0fad02c1bda17716"
RR_R23_SHA = ("49d665753085e72112718c20ed5781f3ab8f4bebb4dad43241732b3051"
              "fb0559")
RR_R1_SIZE, RR_R23_SIZE = 476, 470
BIRD_MTIME_MAIN = 1794200950  # 2026-11-09 13:09:10 +08:00
RR_MTIMES = (1794197638, 1794197638, 1794197639)  # 12:13:58/58/59
EXE_SHAS = ("4e77745b74ee1adebfe68d874d20afb470152548338ac834aa054394cdd98d91",
            "9e95cb4da1319311a1112ca0fddf005c70585a9ac24b9b9c2cf6e2a20ff7b3fd",
            "00c6aaaa5ddc27b7bbecb794e968e2af4e0d00b4a853fc6717d318093b16cd52")
LCB_SHAS = ("02e8527f158a93939c3dbb13169aad54d14af24536c3435d2d72ab9c5e2f3c5a",
            "cba11654e965797d6caef3b72e4d56b35eaf88069564267b4c848a4fb9a724be",
            "e2767b2fac7b9727b77d24351791874e617ebc97ad24e89709ec8ca5485da7de")
EXE_SIZE, LCB_SIZE = 3365, 2022
INC_MAIN_CAUSE = ("len", 390, "9bee326882d0833fa4fa0f318b8d762cf4c6577b4c"
                  "820433f1051e64f45d4728")
INC_MAIN_STDOUT = ("len", 25, "7b512ba7d7a5a32791c385b4b386c28da3cdb66361cb"
                   "8bcd0f42e5c00b9addd9")
INC_RR_CAUSE = ("len", 160, "c5d0523e532f3073221837134fbf649d997117e79000637"
                "924672afa827f0fa0")
WS_R23_AGG = ("d467043a992efa3c78048b58272f94b3a6172705f4a92a8d3a92bda9087af"
              "640")

FLAT_KEYS = sorted(["assessed", "checker_sha256", "earned", "judging_incident",
                    "possible", "reported", "reward", "rule_version"])
NESTED_KEYS = sorted(["case", "note", "product", "raw_checker_output", "rep",
                      "run_id", "score"])


def sha_of_bytes(b):
    return hashlib.sha256(b).hexdigest()


def real_archive_gate():
    """真档案端到端测试门控。未设置环境变量时返回响亮的失败消息。"""
    root = os.environ.get(ENV_VAR)
    if not root:
        return None, (
            "REQUIRED ENV %s NOT SET: the real-archive end-to-end tests "
            "mandated by the frozen prereg cannot run, and silent skipping "
            "is forbidden. Set %s to the launch-r1109 archive root "
            "(.../until22-20261109/launch-r1109) and re-run."
            % (ENV_VAR, ENV_VAR))
    return root, None


def load_verify_module():
    spec = importlib.util.spec_from_file_location("rc_verify_under_test",
                                                  VERIFY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------- 合成档案构建 ----------------
BIRD_CASE = "bird-ca-x"
NESTED_CASES = ["alpha", "beta", "gamma", "delta"]
CAUSE_TEXT = "SYNTHETIC-CAUSE-TOPSECRET-0123456789ABCDEF"
STDOUT_TEXT = "SYNTHETIC-STDOUT-TOPSECRET-0123456789"
RETRO_CAUSE_TEXT = "SYNTHETIC-RETROCAUSE-TOPSECRET-0123456789"
NOTE_TEXT = "SYNTHETIC-NOTE-TOPSECRET-0123456789ABCDEF"
RULE_V = "freeze-synthetic-v1"
PREREG_STUB = "PREREG-STUB-README for synthetic fixture archives\n"

# mtime 计划（epoch 秒）：bird main 同秒批量；retrorun 638/638/639；nested 递增
MTIME_PLAN = {
    (BIRD_CASE, "main"): [1794200950, 1794200950, 1794200950],
    (BIRD_CASE, "retrorun"): [1794197638, 1794197638, 1794197639],
    ("alpha", "main"): [1794197000, 1794197100, 1794197200],
    ("beta", "main"): [1794197300, 1794197400, 1794197500],
    ("gamma", "main"): [1794198000, 1794198100, 1794198200],
    ("delta", "main"): [1794198300, 1794198400, 1794198500],
}
WS_PLAN = {
    BIRD_CASE: {"TASK.md": "BIRD-TASK-CONST",
                "answers.jsonl": ["BIRD-ANSWERS-R1", "BIRD-ANSWERS-R23",
                                  "BIRD-ANSWERS-R23"]},
    "alpha": {"TASK.md": "ALPHA-TASK", "solution.txt": "ALPHA-CONST"},
    "beta": {"TASK.md": "BETA-TASK",
             "solution.txt": ["BETA-R1", "BETA-R2", "BETA-R3"]},
    "gamma": {"TASK.md": "GAMMA-TASK",
              "solution.txt": ["GAMMA-R1", "GAMMA-R23", "GAMMA-R23"]},
    "delta": {"TASK.md": "DELTA-TASK", "solution.txt": "DELTA-CONST"},
}


def dumps(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")


def flat_receipt(earned):
    return {
        "assessed": "2026-11-09T13:09:10+08:00",
        "checker_sha256": hashlib.sha256(b"synthetic-checker").hexdigest(),
        "earned": earned,
        "judging_incident": {"cause": CAUSE_TEXT,
                             "pre_fix_checker_stdout": STDOUT_TEXT},
        "possible": 15,
        "reported": None,
        "reward": 1,
        "rule_version": RULE_V,
    }


def flat_retrorun(earned):
    d = flat_receipt(earned)
    d["judging_incident"] = {"cause": RETRO_CAUSE_TEXT,
                             "pre_fix_checker_stdout": STDOUT_TEXT}
    d["assessed"] = "2026-11-09T12:13:58+08:00"
    return d


def nested_receipt(case, rep):
    return {
        "case": case,
        "note": NOTE_TEXT,
        "product": "dsh",
        "raw_checker_output": "SYNTHETIC-CHECKER-OUTPUT-CONST-" + case,
        "rep": rep,
        "run_id": "run-%s-%d" % (case, rep),
        "score": {"earned": 7, "possible": 10, "reward": 1,
                  "rule_version": RULE_V,
                  "checker_sha256": hashlib.sha256(case.encode()).hexdigest()},
    }


def build_standard_archive(base):
    """在 base 下构建 15 槽合成档案，返回 (repo_root, archive_root)。"""
    repo_root = os.path.join(base, "repo")
    archive_root = os.path.join(base, "archive")
    prereg_dir = os.path.join(repo_root, PREREG_REL)
    os.makedirs(os.path.dirname(prereg_dir))
    with open(prereg_dir, "w", encoding="utf-8") as f:
        f.write(PREREG_STUB)
    runs = os.path.join(archive_root, "dsh", "runs")
    for case in [BIRD_CASE] + NESTED_CASES:
        for rep in (1, 2, 3):
            slot = "dsh__%s__r%d" % (case, rep)
            sd = os.path.join(runs, slot)
            os.makedirs(os.path.join(sd, "workspace"))
            if case == BIRD_CASE:
                main = flat_receipt(14 if rep == 1 else 15)
                rr = flat_retrorun(14 if rep == 1 else 15)
                main_path = os.path.join(sd, "score-receipt.json")
                rr_path = os.path.join(
                    sd, "score-receipt.retrorun-benchprivate.json")
                for path, doc, mtime in ((main_path, main,
                                          MTIME_PLAN[(case, "main")][rep - 1]),
                                         (rr_path, rr,
                                          MTIME_PLAN[(case, "retrorun")]
                                          [rep - 1])):
                    with open(path, "wb") as f:
                        f.write(dumps(doc))
                    os.utime(path, (mtime, mtime))
            else:
                path = os.path.join(sd, "score-receipt.json")
                mtime = MTIME_PLAN[(case, "main")][rep - 1]
                with open(path, "wb") as f:
                    f.write(dumps(nested_receipt(case, rep)))
                os.utime(path, (mtime, mtime))
            # workspace
            for fname, content in WS_PLAN[case].items():
                text = (content[rep - 1] if isinstance(content, list)
                        else content)
                with open(os.path.join(sd, "workspace", fname), "w",
                          encoding="utf-8") as f:
                    f.write(text)
    return repo_root, archive_root


def run_verify(root, archive_root, output=None, optimize=False):
    cmd = [sys.executable] + (["-O"] if optimize else []) + \
        [VERIFY, "--root", root, "--archive-root", archive_root]
    if output is not None:
        cmd += ["--output", output]
    return subprocess.run(cmd, capture_output=True)


def run_result(root, archive_root, out_dir, name="res.json"):
    """运行 verify.py 并经 --output 取回结构化 result（stdout 是人类摘要）。"""
    out = os.path.join(out_dir, name)
    proc = run_verify(root, archive_root, output=out)
    result = None
    if proc.returncode == 0 and os.path.exists(out):
        with open(out, "rb") as f:
            result = json.loads(f.read().decode("utf-8"))
    return proc, result, out


# ---------------- 测试 ----------------
class GateWiring(unittest.TestCase):
    """门控函数自身行为（无需环境变量）。"""

    def test_10_gate_missing_env_returns_loud_message(self):
        old = os.environ.pop(ENV_VAR, None)
        try:
            root, msg = real_archive_gate()
        finally:
            if old is not None:
                os.environ[ENV_VAR] = old
        self.assertIsNone(root)
        self.assertIn(ENV_VAR, msg)
        self.assertIn("NOT SET", msg)
        self.assertIn("silent skipping is forbidden", msg)

    def test_11_gate_set_env_returns_root(self):
        old = os.environ.get(ENV_VAR)
        os.environ[ENV_VAR] = "/tmp/some-archive-root"
        try:
            root, msg = real_archive_gate()
        finally:
            if old is None:
                os.environ.pop(ENV_VAR, None)
            else:
                os.environ[ENV_VAR] = old
        self.assertEqual(root, "/tmp/some-archive-root")
        self.assertIsNone(msg)


class RealArchiveTests(unittest.TestCase):
    """真档案端到端：RECEIPT_COLLAPSE_ARCHIVE_ROOT 未设置 → loudly FAIL。"""

    def setUp(self):
        root, msg = real_archive_gate()
        if root is None:
            self.fail(msg)
        self.archive_root = root

    def test_20_real_end_to_end_structural(self):
        with tempfile.TemporaryDirectory() as base:
            proc, r, _out = run_result(REPO_ROOT, self.archive_root, base)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8"))
        self.assertEqual(r["schema"], "receipt-collapse-v1")
        self.assertEqual(r["prereg"]["sha256"], PREREG_SHA256)
        self.assertEqual(r["observation_surface"]["slot_count"],
                         EXPECTED_SLOT_COUNT)
        self.assertEqual(r["branch"]["verdict"], "B-STRUCTURAL-COINCIDENCE")
        self.assertEqual(r["privacy_audit"], "passed")
        self.assertTrue(r["content_free_declaration"])
        git = subprocess.run(["git", "-C", REPO_ROOT, "rev-parse", "HEAD"],
                             capture_output=True)
        self.assertEqual(r["baseline_commit"],
                         git.stdout.decode().strip() if git.returncode == 0
                         else None)
        # 键集双 schema
        ksg = r["key_set_groups"]
        flat_group = [k for k, v in ksg.items() if "judging_incident" in k]
        self.assertEqual(len(flat_group), 1)
        bird_mems = [m for m in ksg[flat_group[0]]
                     if m.startswith(SLOT_PREFIX_BIRD[:-2])]
        self.assertEqual(len(bird_mems), 6)  # 3 slots × main+retrorun
        # 收据字节与 mtime（bird）
        recs = r["receipts"]
        b1 = recs[SLOT_PREFIX_BIRD % 1]["main"]
        b2 = recs[SLOT_PREFIX_BIRD % 2]["main"]
        b3 = recs[SLOT_PREFIX_BIRD % 3]["main"]
        self.assertEqual((b1["size_bytes"], b1["sha256"]),
                         (BIRD_R1_SIZE, BIRD_R1_SHA))
        for b in (b2, b3):
            self.assertEqual((b["size_bytes"], b["sha256"]),
                             (BIRD_R23_SIZE, BIRD_R23_SHA))
            self.assertEqual(b["mtime_epoch"], BIRD_MTIME_MAIN)
        rr1 = recs[SLOT_PREFIX_BIRD % 1]["retrorun"]
        rr3 = recs[SLOT_PREFIX_BIRD % 3]["retrorun"]
        self.assertEqual((rr1["size_bytes"], rr1["sha256"]),
                         (RR_R1_SIZE, RR_R1_SHA))
        self.assertEqual((rr3["size_bytes"], rr3["sha256"]),
                         (RR_R23_SIZE, RR_R23_SHA))
        for i, rep in enumerate((1, 2, 3)):
            self.assertEqual(
                recs[SLOT_PREFIX_BIRD % rep]["retrorun"]["mtime_epoch"],
                RR_MTIMES[i])
            self.assertEqual(
                recs[SLOT_PREFIX_EXE % rep]["main"]["sha256"], EXE_SHAS[i])
            self.assertEqual(
                recs[SLOT_PREFIX_EXE % rep]["main"]["size_bytes"], EXE_SIZE)
            self.assertEqual(
                recs[SLOT_PREFIX_LCB % rep]["main"]["sha256"], LCB_SHAS[i])
            self.assertEqual(
                recs[SLOT_PREFIX_LCB % rep]["main"]["size_bytes"], LCB_SIZE)
        # bird 元组：r1 earned=14；r2=r3 earned=15
        self.assertEqual(recs[SLOT_PREFIX_BIRD % 1]["main"]["tuple"]["earned"],
                         14)
        self.assertEqual(recs[SLOT_PREFIX_BIRD % 2]["main"]["tuple"]["earned"],
                         15)
        self.assertEqual(recs[SLOT_PREFIX_BIRD % 3]["main"]["tuple"]["earned"],
                         15)
        # incident 材料（len+SHA）
        for rep in (1, 2, 3):
            m = recs[SLOT_PREFIX_BIRD % rep]["main"]["incident"]["materials"]
            self.assertEqual((m["cause"]["len"], m["cause"]["sha256"]),
                             (INC_MAIN_CAUSE[1], INC_MAIN_CAUSE[2]))
            self.assertEqual(
                (m["pre_fix_checker_stdout"]["len"],
                 m["pre_fix_checker_stdout"]["sha256"]),
                (INC_MAIN_STDOUT[1], INC_MAIN_STDOUT[2]))
            rr = recs[SLOT_PREFIX_BIRD % rep]["retrorun"]["incident"]
            self.assertEqual(
                (rr["materials"]["cause"]["len"],
                 rr["materials"]["cause"]["sha256"]),
                (INC_RR_CAUSE[1], INC_RR_CAUSE[2]))
            self.assertEqual(rr["materials"]["pre_fix_checker_stdout"]["sha256"],
                             INC_MAIN_STDOUT[2])
        # retrorun 存在性映射：仅 bird
        rmap = r["retrorun_existence_map"]
        self.assertEqual(sorted(k for k, v in rmap.items() if v),
                         sorted(SLOT_PREFIX_BIRD % i for i in (1, 2, 3)))
        # 分类：collapse 2 / diverge 12 / cross 4
        counts = r["branch"]["counts"]
        self.assertEqual(counts["collapse_pairs"], 2)
        self.assertEqual(counts["diverge_same_tuple_pairs"], 12)
        self.assertEqual(counts["cross_tuple_different_pairs"], 4)
        self.assertEqual(counts["unclassified_missing_tuple_pairs"], 0)
        self.assertEqual(counts["cross_case_bytes_equal_pairs"], 0)
        pairs = r["pairs"]["same_case"]
        collapse = [p for p in pairs if p["classification"] == "collapse"]
        self.assertEqual(len(collapse), 2)
        for p in collapse:
            self.assertEqual(p["slot_a"], SLOT_PREFIX_BIRD % 2)
            self.assertEqual(p["slot_b"], SLOT_PREFIX_BIRD % 3)
            self.assertTrue(p["tuple_equal"])
            self.assertTrue(p["explanation_complete"])
        # 12 个 diverge-with-same-tuple 对：可定位到 rep/run_id
        diverge = [p for p in pairs
                   if p["classification"] == "diverge-with-same-tuple"]
        self.assertEqual(len(diverge), 12)
        for p in diverge:
            self.assertEqual(p["divergence_categories"],
                             ["per-rep-material"])
            self.assertEqual(sorted(d["path"] for d in p["differing_paths"]),
                             ["rep", "run_id"])
        # mtime 同秒组与顺序
        groups = {g["epoch"]: g["members"] for g in
                  r["mtime_same_second_groups"]}
        self.assertEqual(len(groups[BIRD_MTIME_MAIN]), 3)
        self.assertEqual(len(groups[RR_MTIMES[0]]), 2)
        self.assertEqual(r["mtime_order_violations"], [])
        # workspace：bird r2=r3 聚合相同（勘察前提被驳斥）
        self.assertTrue(r["bird_r2_r3"]["workspace_content_identical_r2_r3"])
        self.assertEqual(r["bird_r2_r3"]["workspace_aggregate_r2"], WS_R23_AGG)
        self.assertFalse(r["bird_r2_r3"]["survey_premise_supported"])
        self.assertIn("workspace-survey-premise-refuted",
                      [a["id"] for a in r["anomalies"]])
        pat = r["workspace_case_patterns"]["bird-ca-schools-15"]
        self.assertFalse(pat["all_reps_equal"])
        self.assertEqual(pat["distinct_count"], 2)

    def test_21_real_fresh_equals_stored(self):
        if not os.path.exists(STORED_RESULT):
            self.fail("result.json missing in package; generate it with "
                      "verify.py --output first")
        with tempfile.TemporaryDirectory() as base:
            out = os.path.join(base, "fresh.json")
            proc = run_verify(REPO_ROOT, self.archive_root, output=out)
            self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8"))
            with open(out, "rb") as f:
                fresh = f.read()
            with open(STORED_RESULT, "rb") as f:
                stored = f.read()
            self.assertEqual(fresh, stored,
                             "fresh CLI rerun differs from stored result.json")


class SyntheticTests(unittest.TestCase):
    """合成档案单元/端到端用例（不依赖真档案）。"""

    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="rc-verify-test-")
        self.repo_root, self.archive_root = \
            build_standard_archive(self.base)

    def run_res(self, name="res.json"):
        return run_result(self.repo_root, self.archive_root, self.base, name)

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def slot(self, case, rep):
        return "dsh__%s__r%d" % (case, rep)

    def test_30_synthetic_structural_baseline(self):
        proc, r, _out = self.run_res()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8"))
        self.assertEqual(r["branch"]["verdict"], "B-STRUCTURAL-COINCIDENCE")
        counts = r["branch"]["counts"]
        self.assertEqual(counts["collapse_pairs"], 2)
        self.assertEqual(counts["diverge_same_tuple_pairs"], 12)
        self.assertEqual(counts["cross_tuple_different_pairs"], 4)
        self.assertEqual(r["privacy_audit"], "passed")
        self.assertIn("workspace-survey-premise-refuted",
                      [a["id"] for a in r["anomalies"]])

    def test_31_synthetic_collapse_pair_details(self):
        proc, r, _out = self.run_res()
        collapse = [p for p in r["pairs"]["same_case"]
                    if p["classification"] == "collapse"]
        self.assertEqual({(p["slot_a"], p["slot_b"], p["family"])
                          for p in collapse},
                         {(self.slot(BIRD_CASE, 2), self.slot(BIRD_CASE, 3),
                           "main"),
                          (self.slot(BIRD_CASE, 2), self.slot(BIRD_CASE, 3),
                           "retrorun")})
        for p in collapse:
            self.assertTrue(p["bytes_equal"])
            self.assertTrue(p["incident_materials_equal"])
            self.assertTrue(p["explanation_complete"])

    def test_32_synthetic_diverge_located_paths(self):
        proc, r, _out = self.run_res()
        diverge = [p for p in r["pairs"]["same_case"]
                   if p["classification"] == "diverge-with-same-tuple"]
        self.assertEqual(len(diverge), 12)
        for p in diverge:
            self.assertEqual(p["divergence_categories"],
                             ["per-rep-material"])
            self.assertEqual(sorted(d["path"] for d in p["differing_paths"]),
                             ["rep", "run_id"])

    def test_33_synthetic_retrorun_map_and_keysets(self):
        proc, r, _out = self.run_res()
        rmap = r["retrorun_existence_map"]
        self.assertEqual(sorted(k for k, v in rmap.items() if v),
                         sorted(self.slot(BIRD_CASE, i) for i in (1, 2, 3)))
        ksg = r["key_set_groups"]
        self.assertEqual(len(ksg), 2)  # flat + nested 两种键集
        for slot, fams in r["receipts"].items():
            case = slot.split("__")[1]
            for fam, rec in fams.items():
                expected = FLAT_KEYS if case == BIRD_CASE else NESTED_KEYS
                self.assertEqual(rec["top_key_set"], expected)

    def test_34_v1_contradiction_same_tuple_same_bytes_diff_materials(self):
        mod = load_verify_module()
        t = {"earned": 15, "possible": 15, "reward": 1,
             "rule_version": RULE_V, "checker_sha256": "ab" * 32}
        mats_a = {"cause": {"len": 5, "sha256": "1" * 64}}
        mats_b = {"cause": {"len": 6, "sha256": "2" * 64}}
        with self.assertRaises(mod.FrozenViolation) as ctx:
            mod.check_pair_frozen(t, dict(t), True, mats_a, mats_b, True, True)
        self.assertEqual(ctx.exception.exit_code, 2)
        self.assertIn("V1", str(ctx.exception))

    def test_35_v2_contradiction_diff_tuple_same_bytes(self):
        mod = load_verify_module()
        t1 = {"earned": 14, "possible": 15, "reward": 1,
              "rule_version": RULE_V, "checker_sha256": "ab" * 32}
        t2 = {"earned": 15, "possible": 15, "reward": 1,
              "rule_version": RULE_V, "checker_sha256": "ab" * 32}
        mats = {"cause": {"len": 5, "sha256": "1" * 64}}
        with self.assertRaises(mod.FrozenViolation) as ctx:
            mod.check_pair_frozen(t1, t2, True, mats, mats, True, True)
        self.assertEqual(ctx.exception.exit_code, 2)
        self.assertIn("V2", str(ctx.exception))

    def test_36_unit_classification_matrix(self):
        mod = load_verify_module()
        t1 = {"earned": 14, "possible": 15, "reward": 1,
              "rule_version": RULE_V, "checker_sha256": "ab" * 32}
        t2 = {"earned": 15, "possible": 15, "reward": 1,
              "rule_version": RULE_V, "checker_sha256": "ab" * 32}
        mats = {"cause": {"len": 5, "sha256": "1" * 64}}
        self.assertEqual(mod.check_pair_frozen(t1, dict(t1), True, mats, mats,
                                              True, True), "collapse")
        self.assertEqual(mod.check_pair_frozen(t1, dict(t1), False, mats,
                                              mats, True, True),
                         "diverge-with-same-tuple")
        self.assertEqual(mod.check_pair_frozen(t1, t2, False, mats, mats,
                                               True, True),
                         "cross-tuple-different")
        self.assertEqual(mod.check_pair_frozen(None, t1, True, None, None,
                                               False, False),
                         "unclassified-missing-tuple")

    def test_37_mtime_out_of_order_is_copy_anomaly_not_exit(self):
        case = "beta"
        for rep, mtime in ((1, 1794197300), (2, 1794197400), (3, 1794197350)):
            path = os.path.join(self.archive_root, "dsh", "runs",
                                self.slot(case, rep), "score-receipt.json")
            os.utime(path, (mtime, mtime))
        proc, r, _out = self.run_res()
        self.assertEqual(proc.returncode, 0,
                         "mtime 乱序应走 B-COPY-ANOMALY 分支而非 exit")
        self.assertEqual(r["branch"]["verdict"], "B-COPY-ANOMALY")
        self.assertTrue(r["branch"]["triggers"]["t3_mtime_contradicts_batch_semantics"])
        self.assertTrue(r["mtime_order_violations"])
        self.assertEqual(r["mtime_order_violations"][0]["case"], case)

    def test_38_output_refuses_overwrite(self):
        out = os.path.join(self.base, "existing.json")
        with open(out, "w", encoding="utf-8") as f:
            f.write("KEEP")
        proc = run_verify(self.repo_root, self.archive_root, output=out)
        self.assertEqual(proc.returncode, 2)
        combined = proc.stdout + proc.stderr
        self.assertIn("already exists", combined.decode("utf-8"))
        with open(out, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "KEEP")

    def test_39_missing_required_args_exit2(self):
        cmd = [sys.executable, VERIFY, "--root", self.repo_root]
        proc = subprocess.run(cmd, capture_output=True)
        self.assertEqual(proc.returncode, 2)

    def test_40_nonexistent_roots_exit2(self):
        for kw in ("root", "archive_root"):
            root = self.repo_root
            arc = self.archive_root
            if kw == "root":
                root = os.path.join(self.base, "no-such-repo")
            else:
                arc = os.path.join(self.base, "no-such-archive")
            proc = run_verify(root, arc)
            self.assertEqual(proc.returncode, 2)

    def test_41_missing_receipt_exit2(self):
        os.remove(os.path.join(self.archive_root, "dsh", "runs",
                               self.slot("gamma", 2), "score-receipt.json"))
        proc = run_verify(self.repo_root, self.archive_root)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("score-receipt", proc.stderr.decode("utf-8"))

    def test_42_slot_count_mismatch_exit2(self):
        shutil.rmtree(os.path.join(self.archive_root, "dsh", "runs",
                                   self.slot("delta", 3)))
        proc = run_verify(self.repo_root, self.archive_root)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("15", proc.stderr.decode("utf-8"))

    def test_43_invalid_json_exit2(self):
        path = os.path.join(self.archive_root, "dsh", "runs",
                            self.slot("alpha", 1), "score-receipt.json")
        with open(path, "wb") as f:
            f.write(b"{not-json")
        proc = run_verify(self.repo_root, self.archive_root)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("JSON", proc.stderr.decode("utf-8"))

    def test_44_tampered_bytes_flip_collapse_to_diverge(self):
        path = os.path.join(self.archive_root, "dsh", "runs",
                            self.slot(BIRD_CASE, 2), "score-receipt.json")
        with open(path, "rb") as f:
            doc = json.loads(f.read().decode("utf-8"))
        doc["reported"] = "TAMPERED"
        with open(path, "wb") as f:
            f.write(dumps(doc))
        # 第一步：篡改即重写，mtime 变新 → rep 序乱 → B-COPY-ANOMALY（t3）
        proc, r, _out = self.run_res("tamper-step1.json")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(r["branch"]["verdict"], "B-COPY-ANOMALY")
        self.assertTrue(
            r["branch"]["triggers"]["t3_mtime_contradicts_batch_semantics"])
        # 第二步：恢复原 mtime，隔离字节级篡改效应 → B-INDETERMINATE
        os.utime(path, (1794200950, 1794200950))
        proc, r, _out = self.run_res("tamper-step2.json")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(r["branch"]["verdict"], "B-INDETERMINATE")
        self.assertFalse(
            r["branch"]["structural_conditions"]
            ["s2_divergence_located_to_per_rep_material"])
        pairs = [p for p in r["pairs"]["same_case"]
                 if p["classification"] == "diverge-with-same-tuple"]
        tampered = [p for p in pairs if p["slot_a"] == self.slot(BIRD_CASE, 2)]
        self.assertEqual(len(tampered), 1)
        self.assertEqual(sorted(d["path"]
                                for d in tampered[0]["differing_paths"]),
                         ["reported"])
        self.assertEqual(tampered[0]["divergence_categories"], ["other"])
        # collapse 对从 2 降到 1（仅 retrorun 仍 collapse）
        self.assertEqual(r["branch"]["counts"]["collapse_pairs"], 1)

    def test_45_dual_mode_stdout_identical(self):
        plain = run_verify(self.repo_root, self.archive_root)
        opt = run_verify(self.repo_root, self.archive_root, optimize=True)
        self.assertEqual(plain.returncode, 0)
        self.assertEqual(opt.returncode, 0)
        self.assertEqual(plain.stdout, opt.stdout)

    def test_46_privacy_secrets_absent_from_stdout_and_result(self):
        proc, r_unused, out = self.run_res()
        self.assertEqual(proc.returncode, 0)
        secrets = [CAUSE_TEXT, STDOUT_TEXT, RETRO_CAUSE_TEXT, NOTE_TEXT,
                   "run-alpha-1", "run-beta-2", "SYNTHETIC-CHECKER-OUTPUT"
                   "-CONST-alpha"]
        for blob, name in ((proc.stdout, "stdout"),
                           (open(out, "rb").read(), "result file")):
            text = blob.decode("utf-8")
            for s in secrets:
                self.assertNotIn(s, text,
                                 "secret %r leaked into %s" % (s[:12], name))
        r = json.loads(open(out, "rb").read().decode("utf-8"))
        cause_digest = r["receipts"][self.slot(BIRD_CASE, 2)]["main"][
            "incident"]["materials"]["cause"]["sha256"]
        self.assertEqual(cause_digest, sha_of_bytes(CAUSE_TEXT.encode("utf-8")))

    def test_47_result_schema_prereg_sha_and_git_fields(self):
        proc, r, _out = self.run_res()
        self.assertEqual(r["schema"], "receipt-collapse-v1")
        self.assertEqual(r["prereg"]["sha256"], sha_of_bytes(
            PREREG_STUB.encode("utf-8")))
        self.assertEqual(r["prereg"]["path"], PREREG_REL.replace(os.sep, "/"))
        self.assertFalse(r["git_available"])
        self.assertIsNone(r["baseline_commit"])

    def test_48_inputs_redacted_no_absolute_paths(self):
        proc, _r, out = self.run_res("redacted.json")
        self.assertEqual(proc.returncode, 0)
        text = open(out, "rb").read().decode("utf-8")
        self.assertNotIn(self.base, text)
        self.assertNotIn(tempfile.gettempdir() + "/rc-verify-test", text)
        r = json.loads(text)
        self.assertIn("paths_redacted", r["inputs"])

    def test_49_rerun_deterministic_bytes(self):
        out1 = os.path.join(self.base, "d1", "res.json")
        out2 = os.path.join(self.base, "d2", "res.json")
        os.makedirs(os.path.dirname(out1))
        os.makedirs(os.path.dirname(out2))
        p1 = run_verify(self.repo_root, self.archive_root, output=out1)
        p2 = run_verify(self.repo_root, self.archive_root, output=out2)
        self.assertEqual(p1.returncode, 0)
        self.assertEqual(p2.returncode, 0)
        self.assertEqual(p1.stdout, p2.stdout)
        self.assertEqual(open(out1, "rb").read(), open(out2, "rb").read())

    def test_50_workspace_aggregate_formula(self):
        proc, r, _out = self.run_res()
        rec = r["workspace"][self.slot(BIRD_CASE, 2)]
        expected = sha_of_bytes("\n".join(
            "%s\x00%s" % (p, h) for p, h in sorted(
                (f["path"], sha_of_bytes(f["content"].encode("utf-8")))
                for f in [{"path": "TASK.md",
                           "content": WS_PLAN[BIRD_CASE]["TASK.md"]},
                          {"path": "answers.jsonl",
                           "content": "BIRD-ANSWERS-R23"}])).encode("utf-8"))
        self.assertEqual(rec["aggregate_sha256"], expected)
        self.assertEqual(rec["file_count"], 2)
        self.assertTrue(r["bird_r2_r3"]["workspace_content_identical_r2_r3"])
        self.assertTrue(r["workspace_case_patterns"]["alpha"]["all_reps_equal"])
        self.assertFalse(
            r["workspace_case_patterns"]["beta"]["all_reps_equal"])
        self.assertEqual(
            r["workspace_case_patterns"]["gamma"]["distinct_count"], 2)
        self.assertIn("sha256", r["workspace_formula"])

    def test_51_same_second_groups_and_utc8(self):
        proc, r, _out = self.run_res()
        groups = {g["epoch"]: g for g in r["mtime_same_second_groups"]}
        self.assertEqual(len(groups), 2)
        self.assertEqual(set(groups[1794200950]["members"]),
                         {self.slot(BIRD_CASE, i) + "/main"
                          for i in (1, 2, 3)})
        self.assertIn("13:09:10", groups[1794200950]["utc8"])
        self.assertEqual(len(groups[1794197638]["members"]), 2)
        rec = r["receipts"][self.slot(BIRD_CASE, 1)]["main"]
        self.assertEqual(rec["mtime_epoch"], 1794200950)
        self.assertIn("+08:00", rec["mtime_utc8"])


def load_all():
    return unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])


if __name__ == "__main__":
    unittest.main(verbosity=2)
