#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WB漂移字节位置结构-2026-11-16 verify.py 测试（≥14 用例）。

约定（与环 6 同族风格）：
- 合成用例：临时目录组装 repo root（复制真实冻结 README 保封印）+ 档案根
  （6 槽 trace JSONL）+ 合成硬等参照；测试侧独立复算期望 diff_offsets 与
  context_sha（与 verify.py 无共享代码）。
- 真档案端到端：环境变量 WB_DRIFT_ARCHIVE_ROOT 提供 WorkBuddy 复测档根；
  支持 os.pathsep 分隔多根做双档一致性。未设则本套件响亮 FAIL。
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parent
REPO_ROOT = PKG.parent.parent
VERIFY = PKG / "verify.py"
PREREG_REL = "4-打分细则/WB漂移字节位置结构-2026-11-16/README.md"
PREREG_SHA = "c95d8e6d850ca3f517cc7295f51dc0fdde895506bdc58ecb2ae3817d579ba1b1"
REF_RESULT_REL = "4-打分细则/WB重复槽输入与交互量结构-2026-11-16/result.json"
STORED_RESULT = PKG / "result.json"

OPEN_MARK = b'<system-reminder data-role="user-context">'
CLOSE_MARK = b"</system-reminder>"
BODY_LEN = 40
ENVELOPE_LEN = len(OPEN_MARK) + BODY_LEN + len(CLOSE_MARK)  # 信封闭合 offset=100
ENVELOPE_BODY_RANGE = (len(OPEN_MARK), len(OPEN_MARK) + BODY_LEN)  # [42, 82)
SLOTS = [
    "dabstep-payments-10__r1", "dabstep-payments-10__r2", "dabstep-payments-10__r3",
    "tb-cargo-plan__r1", "tb-cargo-plan__r2", "tb-cargo-plan__r3",
]
GROUPS = {"dabstep-payments-10": ["r1", "r2", "r3"], "tb-cargo-plan": ["r1", "r2", "r3"]}
PAIRS = [("r1", "r2"), ("r1", "r3"), ("r2", "r3")]


def run_cli(root, archive_root, output=None):
    cmd = [sys.executable, str(VERIFY), "--root", str(root),
           "--archive-root", str(archive_root)]
    if output is not None:
        cmd += ["--output", str(output)]
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=120)


def byte_diff(a: bytes, b: bytes):
    return [i for i in range(min(len(a), len(b))) if a[i] != b[i]]


def build_text(envelope_body: bytes, tail: bytes) -> bytes:
    return OPEN_MARK + envelope_body + CLOSE_MARK + tail


def synthesize_w1_reference(texts_by_group: dict) -> dict:
    """独立复算 w1.groups（测试侧实现，与 verify.py 无共享代码）。"""
    groups = {}
    for case, texts in sorted(texts_by_group.items()):
        spans = {}
        for rep, data in texts.items():
            s = data.find(OPEN_MARK)
            e = data.find(CLOSE_MARK, s + len(OPEN_MARK))
            spans[rep] = [[s, e + len(CLOSE_MARK)]]
        all_spans = [tuple(sp) for rep in texts for sp in spans[rep]]
        pairs = []
        any_out = False
        all_eq = True
        for ra, rb in PAIRS:
            offs = byte_diff(texts[ra], texts[rb])
            outside = [o for o in offs if not any(s <= o < e for (s, e) in all_spans)]
            if outside:
                any_out = True
            if offs:
                all_eq = False
            pairs.append({
                "pair": [ra, rb],
                "byte_equal": not offs,
                "diff_offsets": offs,
                "n_diff_offsets": len(offs),
                "offsets_outside_envelope": outside,
                "n_offsets_outside_envelope": len(outside),
                "pair_result": ("equal" if not offs
                                else ("env_external_diff" if outside else "env_internal_only")),
            })
        cls = "w1_stable" if all_eq else ("w1_task_text_drift" if any_out else "w1_env_volatile")
        groups[case] = {
            "classification": cls,
            "envelope_span_cross_rep_equal": True,
            "spans_by_rep": spans,
            "pairs": pairs,
        }
    return groups


def mirror_cluster_bytes(rep: int, group_idx: int) -> dict:
    """镜像真实结构：簇 rel {+93,+94,+96,+97}（+95 恒定）、孤立位 rel gA=+330 gB=+318、
    信封内 rel {−55, −20}（offset 45/80，落在信封 body 区 [42,82)，两位 gap 35>16
    不共窗——镜像真实数据信封内两位远隔的结构）；+93 位一对 rep 同字节
    （gA: r1=r2，gB: r2=r3）。返回 {offset: byte}。"""
    assert ENVELOPE_LEN == 100
    cluster = {94: "147"[rep], 96: "258"[rep], 97: "369"[rep]}
    cluster[93] = "001"[rep] if group_idx == 0 else "122"[rep]
    diffs = {100 + rel: ch.encode("ascii") for rel, ch in cluster.items()}
    iso_rel = 330 if group_idx == 0 else 318
    diffs[100 + iso_rel] = "123"[rep].encode("ascii")
    for off in (45, 80):
        assert ENVELOPE_BODY_RANGE[0] <= off < ENVELOPE_BODY_RANGE[1]
        diffs[off] = ("123" if off == 60 else "456")[rep].encode("ascii")
    return diffs


def make_mirror_texts():
    texts = {}
    for gi, case in enumerate(sorted(GROUPS)):
        for rep in range(3):
            body = bytearray(b"x" * BODY_LEN)
            tail = bytearray(b"y" * 500)
            for off, b in mirror_cluster_bytes(rep, gi).items():
                if off < 100:
                    body[off - len(OPEN_MARK)] = b[0]
                else:
                    tail[off - 100] = b[0]
            texts["%s__r%d" % (case, rep + 1)] = build_text(bytes(body), bytes(tail))
    return texts


def make_scattered_texts():
    """两组信封外漂移位不对齐（gA rel +40/+500，gB rel +60/+520），互异且孤立替换。"""
    texts = {}
    for gi, case in enumerate(sorted(GROUPS)):
        rels = [40, 500] if gi == 0 else [60, 520]
        for rep in range(3):
            body = bytearray(b"x" * 41)
            tail = bytearray(b"y" * 600)
            for rel in rels:
                tail[rel] = ord("123"[rep])
            texts["%s__r%d" % (case, rep + 1)] = build_text(bytes(body), bytes(tail))
    return texts


def make_block_shift_texts():
    """gA 两个漂移位 rel +40 与 +52（gap 12 > 8B 并组阈值、≤16B 共窗）⇒ 事件窗互含
    对方漂移字节 ⇒ context 不同 ⇒ block_shift_candidate；gB 正常镜像簇+孤立位。"""
    texts = make_mirror_texts()
    case_a = sorted(GROUPS)[0]
    for rep in range(3):
        data = bytearray(texts["%s__r%d" % (case_a, rep + 1)])
        data[100 + 40] = ord("123"[rep])
        data[100 + 52] = ord("456"[rep])
        texts["%s__r%d" % (case_a, rep + 1)] = bytes(data)
    return texts


class ArchiveBuilder:
    """合成档案根 + repo 根组装器。texts: {slot: bytes}。"""

    def __init__(self, texts, ref_override=None):
        self.tmp = Path(tempfile.mkdtemp(prefix="wbdftest_"))
        self.repo = self.tmp / "repo"
        self.archive = self.tmp / "archive"
        (self.repo / "4-打分细则" / "WB漂移字节位置结构-2026-11-16").mkdir(parents=True)
        (self.archive / "runs").mkdir(parents=True)
        shutil.copyfile(REPO_ROOT / PREREG_REL, self.repo / PREREG_REL)
        for slot in SLOTS:
            tdir = self.archive / "runs" / slot / "trace"
            tdir.mkdir(parents=True)
            ev = {"type": "message", "role": "user",
                  "content": [{"type": "input_text", "text": texts[slot].decode("utf-8")}]}
            (tdir / "sess.jsonl").write_text(json.dumps(ev) + "\n", encoding="utf-8")
        if ref_override is None:
            groups = synthesize_w1_reference(
                {c: {r: texts["%s__%s" % (c, r)] for r in reps} for c, reps in GROUPS.items()})
        else:
            groups = ref_override
        ref = {"w1": {"groups": groups}}
        (self.repo / REF_RESULT_REL).parent.mkdir(parents=True, exist_ok=True)
        (self.repo / REF_RESULT_REL).write_text(
            json.dumps(ref, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")

    def cleanup(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class VerifyTestBase(unittest.TestCase):
    def setUp(self):
        self._builders = []

    def make_builder(self, texts, ref_override=None):
        b = ArchiveBuilder(texts, ref_override=ref_override)
        self._builders.append(b)
        return b

    def out_path(self):
        return Path(tempfile.mkdtemp(prefix="wbdfout_")) / "fresh.json"

    def tearDown(self):
        for b in self._builders:
            b.cleanup()

    def parse_result(self, proc, out_path):
        """stdout 是人类摘要文本；完整 JSON result 在 --output 文件里。"""
        self.assertEqual(proc.returncode, 0, proc.stdout)
        try:
            return json.loads(Path(out_path).read_text(encoding="utf-8"))
        except ValueError:
            raise AssertionError("--output 非 JSON: %r"
                                 % Path(out_path).read_bytes()[:500])


class FixedClusterTests(VerifyTestBase):
    def test_fixed_cluster_classification(self):
        b = self.make_builder(make_mirror_texts())
        proc = run_cli(b.repo, b.archive)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("branch=B-FIXED-POSITION-TOKEN", proc.stdout.decode("utf-8"))

    def test_pairwise_distinct_exception_registered(self):
        b = self.make_builder(make_mirror_texts())
        out = self.out_path()
        proc = run_cli(b.repo, b.archive, output=out)
        result = self.parse_result(proc, out)
        for case, expected_pair in (("dabstep-payments-10", "r1r2"),
                                    ("tb-cargo-plan", "r2r3")):
            nu = result["case_analysis"][case]["non_unique_positions"]
            self.assertEqual(len(nu), 1, case)
            self.assertEqual(nu[0]["rel_position"], 93)
            self.assertIn(expected_pair, nu[0]["equal_pairs"])

    def test_relative_positions_registration(self):
        b = self.make_builder(make_mirror_texts())
        out = self.out_path()
        proc = run_cli(b.repo, b.archive, output=out)
        result = self.parse_result(proc, out)
        case = "dabstep-payments-10"
        rels = sorted(p["rel_position"] for p in result["case_analysis"][case]["positions"]
                      if p["lane"] == "envelope_external")
        self.assertEqual(rels, [93, 94, 96, 97, 330])
        self.assertEqual(result["case_analysis"][case]["envelope_close"], 100)
        self.assertEqual(result["case_analysis"][case]["envelope_span"], [[0, 100]])

    def test_envelope_internal_registered(self):
        b = self.make_builder(make_mirror_texts())
        out = self.out_path()
        proc = run_cli(b.repo, b.archive, output=out)
        result = self.parse_result(proc, out)
        for case in GROUPS:
            a = result["case_analysis"][case]
            self.assertEqual(a["internal_positions_n"], 2)
            rels = sorted(p["rel_position"] for p in a["positions"]
                          if p["lane"] == "envelope_internal")
            self.assertEqual(rels, [-55, -20])
            for p in a["positions"]:
                if p["lane"] == "envelope_internal":
                    self.assertTrue(p["three_distinct"])
                    self.assertEqual(p["pair_count"], 3)

    def test_isolated_slot_case_fixed(self):
        b = self.make_builder(make_mirror_texts())
        out = self.out_path()
        proc = run_cli(b.repo, b.archive, output=out)
        result = self.parse_result(proc, out)
        cross = result["cross_case_cluster"]
        self.assertEqual(cross["per_case"]["dabstep-payments-10"]["isolated_slots"][0]
                         ["rel_position"], 330)
        self.assertEqual(cross["per_case"]["tb-cargo-plan"]["isolated_slots"][0]
                         ["rel_position"], 318)
        for case in GROUPS:
            slot = cross["per_case"][case]["isolated_slots"][0]
            self.assertTrue(slot["case_fixed_across_pairs"])
            self.assertTrue(slot["three_distinct"])

    def test_context_sha_removal_correctness(self):
        b = self.make_builder(make_mirror_texts())
        out = self.out_path()
        proc = run_cli(b.repo, b.archive, output=out)
        result = self.parse_result(proc, out)
        texts = make_mirror_texts()
        case = "tb-cargo-plan"
        a = result["case_analysis"][case]
        events = a["events"]
        self.assertEqual(len(events), 4, "tb 应为 4 个漂移事件（簇/孤立/2 信封内）")
        for ev in events:
            offs = ev["positions_offset"]
            lo = max(0, min(offs) - 16)
            hi = min(len(texts[case + "__r1"]), max(offs) + 17)
            removed = set(offs)
            expect = []
            for rep in ("r1", "r2", "r3"):
                data = texts[case + "__" + rep]
                kept = bytes(b for i, b in enumerate(data[lo:hi]) if lo + i not in removed)
                expect.append(hashlib.sha256(kept).hexdigest())
            self.assertEqual([ev["per_rep_context_sha"][r] for r in ("r1", "r2", "r3")],
                             expect, ev["positions_rel"])
            self.assertTrue(ev["all_equal"])
            self.assertEqual(ev["class"], "isolated_substitution")
            self.assertEqual(ev["removed_n"], len(offs))
            self.assertGreaterEqual(ev["window"][0], 0)
            self.assertLessEqual(ev["window"][1], len(texts[case + "__r1"]))

    def test_scattered_classification(self):
        b = self.make_builder(make_scattered_texts())
        proc = run_cli(b.repo, b.archive)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("branch=B-SCATTERED", proc.stdout.decode("utf-8"))

    def test_block_shift_classification(self):
        b = self.make_builder(make_block_shift_texts())
        out = self.out_path()
        proc = run_cli(b.repo, b.archive, output=out)
        result = self.parse_result(proc, out)
        case_a = sorted(GROUPS)[0]
        ev_classes = {tuple(ev["positions_rel"]): ev["class"]
                      for ev in result["case_analysis"][case_a]["events"]}
        self.assertEqual(ev_classes[(40,)], "block_shift_candidate")
        self.assertEqual(ev_classes[(52,)], "block_shift_candidate")
        self.assertIn("branch=B-SCATTERED", proc.stdout.decode("utf-8"))
        self.assertGreaterEqual(result["branch"]["block_shift_candidates_n"], 2)

    def test_context_sha_differs_when_context_differs(self):
        b = self.make_builder(make_block_shift_texts())
        out = self.out_path()
        proc = run_cli(b.repo, b.archive, output=out)
        result = self.parse_result(proc, out)
        case_a = sorted(GROUPS)[0]
        for ev in result["case_analysis"][case_a]["events"]:
            if ev["positions_rel"] == [40]:
                self.assertFalse(ev["all_equal"])
                self.assertEqual(len(set(ev["per_rep_context_sha"].values())), 3)
                self.assertEqual(ev["class"], "block_shift_candidate")
                self.assertEqual(ev["removed_n"], 1)
                self.assertEqual(ev["window"], [124, 157])


class CliGuardTests(VerifyTestBase):
    def test_output_refuses_overwrite(self):
        b = self.make_builder(make_mirror_texts())
        out = Path(tempfile.mkdtemp(prefix="wbdfout_")) / "r.json"
        out.write_text("KEEP-ME", encoding="utf-8")
        proc = run_cli(b.repo, b.archive, output=out)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("拒绝覆盖", proc.stdout.decode("utf-8"))
        self.assertEqual(out.read_text(encoding="utf-8"), "KEEP-ME")

    def test_prereg_sha_mismatch_exit_2(self):
        b = self.make_builder(make_mirror_texts())
        (b.repo / PREREG_REL).write_text("tampered prereg\n", encoding="utf-8")
        proc = run_cli(b.repo, b.archive)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("SHA256 不符", proc.stdout.decode("utf-8"))

    def test_w1_hard_equal_tamper_reference_exit_2(self):
        b = self.make_builder(make_mirror_texts())
        ref_path = b.repo / REF_RESULT_REL
        ref = json.loads(ref_path.read_text(encoding="utf-8"))
        pairs = ref["w1"]["groups"]["dabstep-payments-10"]["pairs"]
        target = next(p for p in pairs if p["pair"] == ["r1", "r2"])
        target["diff_offsets"] = [o + 1 for o in target["diff_offsets"]]
        ref_path.write_text(json.dumps(ref, sort_keys=True, ensure_ascii=False),
                            encoding="utf-8")
        proc = run_cli(b.repo, b.archive)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("W1 硬等失败", proc.stdout.decode("utf-8"))

    def test_w1_hard_equal_tamper_archive_exit_2(self):
        b = self.make_builder(make_mirror_texts())  # 参照按原始文本生成
        target = b.archive / "runs" / "tb-cargo-plan__r2" / "trace" / "sess.jsonl"
        ev = json.loads(target.read_text(encoding="utf-8"))
        text = ev["content"][0]["text"]
        idx = len(OPEN_MARK) + len(CLOSE_MARK) + 200  # 信封后 200 字节处（非漂移位）
        text = text[:idx] + "\u005a" + text[idx + 1:]  # 非漂移位单字节改动
        ev["content"][0]["text"] = text
        target.write_text(json.dumps(ev) + "\n", encoding="utf-8")
        proc = run_cli(b.repo, b.archive)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("W1 硬等失败", proc.stdout.decode("utf-8"))

    def test_missing_envelope_exit_2(self):
        texts = make_mirror_texts()
        texts[SLOTS[4]] = b"no envelope here" + b"y" * 560
        b = self.make_builder(texts)
        proc = run_cli(b.repo, b.archive)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("FAIL", proc.stdout.decode("utf-8"))

    def test_missing_user_message_exit_2(self):
        b = self.make_builder(make_mirror_texts())
        target = b.archive / "runs" / SLOTS[0] / "trace" / "sess.jsonl"
        events = [json.loads(x) for x in
                  target.read_text(encoding="utf-8").splitlines() if x]
        events = [e for e in events if e.get("role") != "user"]
        target.write_text("".join(json.dumps(e) + "\n" for e in events),
                          encoding="utf-8")
        proc = run_cli(b.repo, b.archive)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("role=user 消息数=0", proc.stdout.decode("utf-8"))

    def test_duplicate_user_message_exit_2(self):
        b = self.make_builder(make_mirror_texts())
        target = b.archive / "runs" / SLOTS[1] / "trace" / "sess.jsonl"
        line = target.read_text(encoding="utf-8")
        target.write_text(line + line, encoding="utf-8")
        proc = run_cli(b.repo, b.archive)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("role=user 消息数=2", proc.stdout.decode("utf-8"))

    def test_multiple_trace_jsonls_exit_2(self):
        b = self.make_builder(make_mirror_texts())
        tdir = b.archive / "runs" / SLOTS[2] / "trace"
        shutil.copyfile(tdir / "sess.jsonl", tdir / "sess2.jsonl")
        proc = run_cli(b.repo, b.archive)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("session jsonl 数=2", proc.stdout.decode("utf-8"))

    def test_stdout_deterministic_two_runs(self):
        b = self.make_builder(make_mirror_texts())
        p1 = run_cli(b.repo, b.archive)
        p2 = run_cli(b.repo, b.archive)
        self.assertEqual(p1.returncode, 0)
        self.assertEqual(p1.stdout, p2.stdout)

    def test_content_independence_no_byte_values_or_paths(self):
        b = self.make_builder(make_mirror_texts())
        out = self.out_path()
        proc = run_cli(b.repo, b.archive, output=out)
        self.assertEqual(proc.returncode, 0)
        blob = out.read_bytes().decode("utf-8") + proc.stdout.decode("utf-8")
        for bad in ("input_text", '"text"', "system-reminder", str(b.tmp), "xxxxx", "yyyyy"):
            self.assertNotIn(bad, blob, "疑似登记了文本内容或私有路径: %s" % bad)
        result = json.loads(out.read_text(encoding="utf-8"))
        self.assertIn("content_independence_statement", result)


class RealArchiveTests(VerifyTestBase):
    """真档案端到端：WB_DRIFT_ARCHIVE_ROOT 未设则响亮 FAIL（与环 6 同约定）。"""

    def _roots(self):
        env_value = os.environ.get("WB_DRIFT_ARCHIVE_ROOT", "").strip()
        if not env_value:
            self.fail("环境变量 WB_DRIFT_ARCHIVE_ROOT 未设置：真档案端到端与 "
                      "fresh==stored 校验无法运行（响亮 FAIL，不许静默跳过）；"
                      "请设为 WorkBuddy 复测档根，可用 os.pathsep 分隔多根做双档一致性")
        return [Path(p) for p in env_value.split(os.pathsep) if p.strip()]

    def test_real_archive_end_to_end(self):
        roots = self._roots()
        procs = [run_cli(REPO_ROOT, r) for r in roots]
        for r, proc in zip(roots, procs):
            self.assertEqual(proc.returncode, 0,
                             "archive_root=%s\n%s" % (r, proc.stdout.decode("utf-8")))
        stdouts = {proc.stdout for proc in procs}
        self.assertEqual(len(stdouts), 1, "多档 stdout 不一致（双档一致性破坏）")
        out = proc.stdout.decode("utf-8")
        self.assertIn("PASS", out)
        self.assertIn("branch=B-FIXED-POSITION-TOKEN", out)
        self.assertIn("drift_instances=40", out)
        self.assertIn("cluster_aligned_rel=[93, 94, 96, 97]", out)
        self.assertIn("w1_hard_equal=true", out)

    def test_real_archive_fresh_matches_stored(self):
        roots = self._roots()
        fresh_dir = Path(tempfile.mkdtemp(prefix="wbdffresh_"))
        proc = run_cli(REPO_ROOT, roots[0], output=fresh_dir / "fresh.json")
        self.assertEqual(proc.returncode, 0, proc.stdout)
        stored = STORED_RESULT.read_bytes()
        fresh = (fresh_dir / "fresh.json").read_bytes()
        self.assertEqual(hashlib.sha256(stored).hexdigest(),
                         hashlib.sha256(fresh).hexdigest(),
                         "fresh result 与包内 stored result.json 不一致")
        self.assertEqual(stored, fresh)


if __name__ == "__main__":
    unittest.main(verbosity=2)
