#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WB漂移token形状-2026-11-16 verify.py 测试（≥12 用例）。

约定（与环 6/11 同族风格）：
- 合成用例：临时目录组装 repo root（复制真实冻结 README 保封印）+ 档案根
  （6 槽 trace JSONL）+ 合成硬等参照（独立复算，与 verify.py 无共享代码）。
- 真档案端到端：环境变量 WB_TOKEN_SHAPE_ARCHIVE_ROOT 提供 WorkBuddy 复测档根；
  支持 os.pathsep 分隔多根做双档一致性（双档一致性用例要求 ≥2 根，少设响亮 FAIL）。
  未设则真档案用例响亮 FAIL（不许静默跳过）。
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
PREREG_REL = "4-打分细则/WB漂移token形状-2026-11-16/README.md"
PREREG_SHA = "c7fee55520d54ee24ba99a9c0a7c6f35018864511085b0ec02e30f377a9a8ee8"
REF_RESULT_REL = "4-打分细则/WB漂移字节位置结构-2026-11-16/result.json"
STORED_RESULT = PKG / "result.json"
ENV_VAR = "WB_TOKEN_SHAPE_ARCHIVE_ROOT"

OPEN_MARK = b'<system-reminder data-role="user-context">'
CLOSE_MARK = b"</system-reminder>"
BODY_LEN = 40                                     # 信封 body 区 offset [42,82)
ENVELOPE_LEN = len(OPEN_MARK) + BODY_LEN + len(CLOSE_MARK)   # = 100，信封闭合=100
TAIL_LEN = 500
CLUSTER_BASE = ENVELOPE_LEN                       # 簇 rel 基点 = 信封闭合
CLUSTER_RELS = (93, 94, 96, 97)                   # 两组长 2 run，gap=rel 95（':' 恒定）
INTERNAL_OFFS = {"dabstep-payments-10": (45, 80), "tb-cargo-plan": (48, 76)}
ISO_REL = {"dabstep-payments-10": 330, "tb-cargo-plan": 318}   # 孤立位 rel（不对齐）
RUN1_DIGITS = ("47", "53", "68")                  # 簇 run1 逐 rep（两位逐 rep 互异）
RUN2_DIGITS = ("58", "91", "24")                  # 簇 run2
PAIR3_DIGITS = ("60", "71", "82")                 # S1 破形用第三组
ISO_DIGITS = ("1", "2", "3")                      # 信封外孤立位逐 rep
INT_DIGITS = ("7", "8", "9")                      # 信封内孤立位逐 rep（全为数字）
SLOTS = [
    "dabstep-payments-10__r1", "dabstep-payments-10__r2", "dabstep-payments-10__r3",
    "tb-cargo-plan__r1", "tb-cargo-plan__r2", "tb-cargo-plan__r3",
]
GROUPS = {"dabstep-payments-10": ["r1", "r2", "r3"], "tb-cargo-plan": ["r1", "r2", "r3"]}
REPS = ("r1", "r2", "r3")


def run_cli(root, archive_root, output=None, extra_flags=()):
    cmd = [sys.executable, *extra_flags, str(VERIFY), "--root", str(root),
           "--archive-root", str(archive_root)]
    if output is not None:
        cmd += ["--output", str(output)]
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=120)


def byte_diff(a: bytes, b: bytes):
    return [i for i in range(min(len(a), len(b))) if a[i] != b[i]]


def build_text(body: bytes, tail: bytes) -> bytes:
    return OPEN_MARK + body + CLOSE_MARK + tail


def make_pass_texts(overrides=None):
    """DD?DD 通过档：簇两组长 2 run（gap=':' 恒定）、信封内 2 孤立位（左邻 alpha）、
    每case 1 信封外孤立位（左邻 alpha、rel 不跨 case 对齐）。
    overrides: {(case, text_offset): char 或 (c1,c2,c3)}——在拼装后的整段文本上
    按 rep 逐字节替换（tuple 时按 rep 取位，str 时三 rep 恒定）。"""
    overrides = overrides or {}
    texts = {}
    for case in sorted(GROUPS):
        for rep in range(3):
            body = bytearray(b"x" * BODY_LEN)
            tail = bytearray(b"y" * TAIL_LEN)
            for idx, off in enumerate(INTERNAL_OFFS[case]):
                body[off - len(OPEN_MARK)] = ord(INT_DIGITS[rep])
                body[off - 1 - len(OPEN_MARK)] = ord("ab"[idx])   # 左邻 alpha
            tail[CLUSTER_RELS[0]] = ord(RUN1_DIGITS[rep][0])
            tail[CLUSTER_RELS[1]] = ord(RUN1_DIGITS[rep][1])
            tail[95] = ord(":")                                   # 分隔字节恒定
            tail[CLUSTER_RELS[2]] = ord(RUN2_DIGITS[rep][0])
            tail[CLUSTER_RELS[3]] = ord(RUN2_DIGITS[rep][1])
            rel = ISO_REL[case]
            tail[rel] = ord(ISO_DIGITS[rep])
            tail[rel - 1] = ord("z")                              # 左邻 alpha
            full = bytearray(OPEN_MARK) + body + bytearray(CLOSE_MARK) + tail
            for (ocase, toff), val in sorted(overrides.items()):
                if ocase != case:
                    continue
                ch = val[rep] if isinstance(val, tuple) else val
                full[toff] = ord(ch)
            texts["%s__r%d" % (case, rep + 1)] = bytes(full)
    return texts


def make_s2_break_texts():
    """S2 破：case A 信封内孤立位（text off 45）r3 改字母 ⇒ r3 无包含 run，
    run 边界跨 rep 不等；drift offsets 集不变（7/8/w 三 rep 互异）。"""
    case_a = sorted(GROUPS)[0]
    off45 = INTERNAL_OFFS[case_a][0]
    return make_pass_texts({(case_a, off45): ("7", "8", "w")})


def make_s3_fail_texts():
    """S3 破：case A 信封内孤立位（text off 45）左邻（off 44）改 ':'（other 类）
    ⇒ run 长 1 但左邻非 alpha。"""
    case_a = sorted(GROUPS)[0]
    off44 = INTERNAL_OFFS[case_a][0] - 1
    return make_pass_texts({(case_a, off44): ":"})


def make_s1_three_pairs_texts():
    """S1 破：两 case 簇各加第三组 DD（tail rel 99,100，gap=rel 98 恒定 ':'）
    ⇒ 对齐簇 = 6 位 ⇒ 3 组 run ⇒『恰两组』破。"""
    overrides = {(case, ENVELOPE_LEN + 98): ":" for case in GROUPS}
    texts = make_pass_texts(overrides)
    # 第三组 run 的两位逐 rep 互异（overrides 常量只能给 gap，数字直接改文本）
    out = {}
    for case in sorted(GROUPS):
        for rep in range(3):
            data = bytearray(texts["%s__r%d" % (case, rep + 1)])
            data[ENVELOPE_LEN + 99] = ord(PAIR3_DIGITS[rep][0])
            data[ENVELOPE_LEN + 100] = ord(PAIR3_DIGITS[rep][1])
            out["%s__r%d" % (case, rep + 1)] = bytes(data)
    return out


def synthesize_shape_reference(texts_by_group: dict) -> dict:
    """独立复算环 11 参照的最小结构（测试侧实现，与 verify.py 无共享代码）。"""
    ca = {}
    for case, texts in sorted(texts_by_group.items()):
        spans = {}
        for rep, data in texts.items():
            s = data.find(OPEN_MARK)
            e = data.find(CLOSE_MARK, s + len(OPEN_MARK))
            spans[rep] = [s, e + len(CLOSE_MARK)]
        offs = set()
        for i in range(3):
            for j in range(i + 1, 3):
                a, b = texts[REPS[i]], texts[REPS[j]]
                assert len(a) == len(b)
                offs |= set(byte_diff(a, b))
        ca[case] = {
            "envelope_span": [spans["r1"]],
            "events": [{
                "positions_offset": sorted(offs),
                "positions_rel": [o - spans["r1"][1] for o in sorted(offs)],
            }],
        }
    return {"case_analysis": ca}


class ArchiveBuilder:
    """合成档案根 + repo 根组装器。texts: {slot: bytes}。"""

    def __init__(self, texts, ref_from_texts=None):
        self.tmp = Path(tempfile.mkdtemp(prefix="wbshapetest_"))
        self.repo = self.tmp / "repo"
        self.archive = self.tmp / "archive"
        (self.repo / "4-打分细则" / "WB漂移token形状-2026-11-16").mkdir(parents=True)
        (self.repo / "4-打分细则" / "WB漂移字节位置结构-2026-11-16").mkdir(parents=True)
        (self.archive / "runs").mkdir(parents=True)
        shutil.copyfile(REPO_ROOT / PREREG_REL, self.repo / PREREG_REL)
        for slot in SLOTS:
            tdir = self.archive / "runs" / slot / "trace"
            tdir.mkdir(parents=True)
            ev = {"type": "message", "role": "user",
                  "content": [{"type": "input_text", "text": texts[slot].decode("utf-8")}]}
            (tdir / "sess.jsonl").write_text(json.dumps(ev) + "\n", encoding="utf-8")
        groups = {
            c: {r: texts["%s__%s" % (c, r)] for r in reps} for c, reps in GROUPS.items()
        }
        ref = (synthesize_shape_reference(groups) if ref_from_texts is None
               else ref_from_texts)
        ref_path = self.repo / REF_RESULT_REL
        ref_path.write_text(
            json.dumps(ref, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")

    def cleanup(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class VerifyTestBase(unittest.TestCase):
    def setUp(self):
        self._builders = []

    def make_builder(self, texts, ref_from_texts=None):
        b = ArchiveBuilder(texts, ref_from_texts=ref_from_texts)
        self._builders.append(b)
        return b

    def out_path(self):
        return Path(tempfile.mkdtemp(prefix="wbshapeout_")) / "fresh.json"

    def tearDown(self):
        for b in self._builders:
            b.cleanup()

    def parse_result(self, proc, out_path):
        self.assertEqual(proc.returncode, 0, proc.stdout)
        try:
            return json.loads(Path(out_path).read_text(encoding="utf-8"))
        except ValueError:
            raise AssertionError("--output 非 JSON: %r"
                                 % Path(out_path).read_bytes()[:500])

    def entries_by_offset(self, result, case):
        return {e["offset"]: e for e in result["run_registration"]["cases"][case]}


class FixedShapeTests(VerifyTestBase):
    def test_fixed_shape_branch_pass(self):
        b = self.make_builder(make_pass_texts())
        proc = run_cli(b.repo, b.archive)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        out = proc.stdout.decode("utf-8")
        self.assertIn("branch=B-DIGIT-RUN-FIXED-SHAPE", out)
        self.assertIn("S1=true", out)
        self.assertIn("S2=true", out)
        self.assertIn("S3=true", out)
        self.assertIn("shape=DD?DD", out)
        self.assertIn("isomorphic=true", out)

    def test_s1_details_registered(self):
        b = self.make_builder(make_pass_texts())
        out = self.out_path()
        proc = run_cli(b.repo, b.archive, output=out)
        result = self.parse_result(proc, out)
        s1 = result["assertions"]["S1"]
        self.assertTrue(s1["pass"])
        self.assertTrue(s1["cross_case_isomorphic"])
        for case in GROUPS:
            cs = s1["cases"][case]
            self.assertTrue(cs["pass"])
            self.assertEqual(cs["shape_signature"], "DD?DD")
            self.assertEqual(cs["cluster_offsets"],
                             [ENVELOPE_LEN + r for r in sorted(CLUSTER_RELS)])
            rep1 = cs["per_rep"]["r1"]
            self.assertEqual(rep1["n_runs"], 2)
            self.assertEqual(rep1["run_lens"], [2, 2])
            self.assertEqual(rep1["gap_width_bytes"], 1)
            self.assertEqual(rep1["gap_byte_class"], "other")
            self.assertTrue(rep1["cluster_offsets_covered_exact"])
            # run 边界经 S2 登记核对（S1 per_rep 不重复携带 run 边界）
            s2rows = {r["offset"]: r
                      for r in result["assertions"]["S2"]["cases"][case]["per_offset"]}
            self.assertEqual(s2rows[ENVELOPE_LEN + 93]["boundaries_by_rep"]["r1"],
                             [ENVELOPE_LEN + 93, ENVELOPE_LEN + 95, 2])
            self.assertEqual(s2rows[ENVELOPE_LEN + 96]["boundaries_by_rep"]["r1"],
                             [ENVELOPE_LEN + 96, ENVELOPE_LEN + 98, 2])

    def test_run_registration_entries(self):
        b = self.make_builder(make_pass_texts())
        out = self.out_path()
        proc = run_cli(b.repo, b.archive, output=out)
        result = self.parse_result(proc, out)
        rr = result["run_registration"]
        self.assertEqual(rr["offsets_total"], 14)
        self.assertEqual(rr["entries_total"], 42)
        self.assertEqual(rr["run_found_false_n"], 0)
        case = sorted(GROUPS)[0]
        by_off = self.entries_by_offset(result, case)
        self.assertEqual(len(by_off), 7)
        e45 = by_off[INTERNAL_OFFS[case][0]]
        self.assertEqual(e45["cluster_role"], "internal")
        self.assertEqual(e45["lane"], "envelope_internal")
        r1 = e45["by_rep"]["r1"]
        self.assertTrue(r1["run_found"])
        self.assertEqual([r1["run_start"], r1["run_end"], r1["run_len"]], [45, 46, 1])
        self.assertEqual(r1["drift_index_in_run"], 0)
        self.assertEqual(r1["left_neighbor_class"], "alpha")
        e194 = by_off[ENVELOPE_LEN + 94]
        self.assertEqual(e194["cluster_role"], "cluster")
        r2 = e194["by_rep"]["r2"]
        self.assertEqual([r2["run_start"], r2["run_end"], r2["run_len"]],
                         [ENVELOPE_LEN + 93, ENVELOPE_LEN + 95, 2])
        self.assertEqual(r2["drift_index_in_run"], 1)
        # run 起点左邻 = 填充字节（合成档 alpha）；第二组 run 起点左邻 = gap 字节（other）
        self.assertEqual(r2["left_neighbor_class"], "alpha")
        e196 = by_off[ENVELOPE_LEN + 96]
        self.assertEqual(e196["by_rep"]["r1"]["left_neighbor_class"], "other")
        self.assertEqual(e196["by_rep"]["r1"]["drift_index_in_run"], 0)

    def test_s2_cross_rep_boundaries_all_equal(self):
        b = self.make_builder(make_pass_texts())
        out = self.out_path()
        proc = run_cli(b.repo, b.archive, output=out)
        result = self.parse_result(proc, out)
        s2 = result["assertions"]["S2"]
        self.assertTrue(s2["pass"])
        self.assertEqual(s2["n_offsets_checked"], 14)
        for case in GROUPS:
            self.assertTrue(s2["cases"][case]["all_equal"])
            for row in s2["cases"][case]["per_offset"]:
                self.assertTrue(row["cross_rep_equal"], row)

    def test_s3_internal_isolated_len1_left_alpha(self):
        b = self.make_builder(make_pass_texts())
        out = self.out_path()
        proc = run_cli(b.archive and b.repo, b.archive, output=out)
        result = self.parse_result(proc, out)
        s3 = result["assertions"]["S3"]
        self.assertTrue(s3["pass"])
        for case in GROUPS:
            cs = s3["cases"][case]
            self.assertTrue(cs["pass"])
            self.assertEqual(cs["n_internal"], 2)
            for d in cs["details"]:
                self.assertTrue(d["pass"])
                for rep in REPS:
                    self.assertEqual(d["run_len_by_rep"][rep], 1)
                    self.assertEqual(d["left_neighbor_class_by_rep"][rep], "alpha")
        roles = result["cluster_classification"]["roles_count_by_case"]
        for case in GROUPS:
            self.assertEqual(roles[case],
                             {"cluster": 4, "internal": 2, "isolated_external": 1})
        self.assertEqual(result["cluster_classification"]["aligned_rels"],
                         sorted(CLUSTER_RELS))

    def test_s2_break_shape_variable(self):
        texts = make_s2_break_texts()
        b = self.make_builder(texts)
        out = self.out_path()
        proc = run_cli(b.repo, b.archive, output=out)
        result = self.parse_result(proc, out)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("branch=B-SHAPE-VARIABLE", proc.stdout.decode("utf-8"))
        self.assertFalse(result["assertions"]["S2"]["pass"])
        self.assertFalse(result["assertions"]["S3"]["pass"])
        self.assertTrue(result["offsets_hard_equal"]["all_equal"])
        case = sorted(GROUPS)[0]
        off = INTERNAL_OFFS[case][0]
        by_off = self.entries_by_offset(result, case)
        r3 = by_off[off]["by_rep"]["r3"]
        self.assertFalse(r3["run_found"])
        self.assertEqual(r3["drift_byte_class"], "alpha")   # 只登记类
        s2row = next(p for p in result["assertions"]["S2"]["cases"][case]["per_offset"]
                     if p["offset"] == off)
        self.assertFalse(s2row["cross_rep_equal"])

    def test_s3_fail_left_class_shape_variable(self):
        texts = make_s3_fail_texts()
        b = self.make_builder(texts)
        out = self.out_path()
        proc = run_cli(b.repo, b.archive, output=out)
        result = self.parse_result(proc, out)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("branch=B-SHAPE-VARIABLE", proc.stdout.decode("utf-8"))
        self.assertTrue(result["assertions"]["S1"]["pass"])
        self.assertTrue(result["assertions"]["S2"]["pass"])
        self.assertFalse(result["assertions"]["S3"]["pass"])
        case = sorted(GROUPS)[0]
        d = next(d for d in result["assertions"]["S3"]["cases"][case]["details"]
                 if d["offset"] == INTERNAL_OFFS[case][0])
        self.assertFalse(d["pass"])
        for rep in REPS:
            self.assertEqual(d["left_neighbor_class_by_rep"][rep], "other")

    def test_s1_break_three_pairs_shape_variable(self):
        texts = make_s1_three_pairs_texts()
        b = self.make_builder(texts)
        out = self.out_path()
        proc = run_cli(b.repo, b.archive, output=out)
        result = self.parse_result(proc, out)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("branch=B-SHAPE-VARIABLE", proc.stdout.decode("utf-8"))
        self.assertFalse(result["assertions"]["S1"]["pass"])
        self.assertTrue(result["assertions"]["S2"]["pass"])
        self.assertTrue(result["assertions"]["S3"]["pass"])
        case = sorted(GROUPS)[0]
        rep1 = result["assertions"]["S1"]["cases"][case]["per_rep"]["r1"]
        self.assertEqual(rep1["n_runs"], 3)
        self.assertTrue(result["assertions"]["S1"]["cases"][case]["shape_signature"]
                        .startswith("VARIABLE"))


class CliGuardTests(VerifyTestBase):
    def test_offsets_hard_equal_tamper_archive_exit2(self):
        clean = make_pass_texts()
        b = self.make_builder(clean)          # 参照按干净文本生成
        target = b.archive / "runs" / sorted(SLOTS)[3] / "trace" / "sess.jsonl"
        ev = json.loads(target.read_text(encoding="utf-8"))
        text = ev["content"][0]["text"]
        idx = ENVELOPE_LEN + 150              # 恒定 'y' 区（非漂移位）
        text = text[:idx] + "q" + text[idx + 1:]
        ev["content"][0]["text"] = text
        target.write_text(json.dumps(ev) + "\n", encoding="utf-8")
        out = self.out_path()
        proc = run_cli(b.repo, b.archive, output=out)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("硬等失败", proc.stdout.decode("utf-8"))
        self.assertFalse(out.exists(), "fail-closed 时不得写 --output")

    def test_prereg_sha_tamper_exit2(self):
        b = self.make_builder(make_pass_texts())
        (b.repo / PREREG_REL).write_text("tampered prereg\n", encoding="utf-8")
        out = self.out_path()
        proc = run_cli(b.repo, b.archive, output=out)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("SHA256 不符", proc.stdout.decode("utf-8"))
        self.assertFalse(out.exists())

    def test_output_refuses_overwrite(self):
        b = self.make_builder(make_pass_texts())
        out = Path(tempfile.mkdtemp(prefix="wbshapeout_")) / "r.json"
        out.write_text("KEEP-ME", encoding="utf-8")
        proc = run_cli(b.repo, b.archive, output=out)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("拒绝覆盖", proc.stdout.decode("utf-8"))
        self.assertEqual(out.read_text(encoding="utf-8"), "KEEP-ME")

    def test_missing_runs_dir_exit2(self):
        b = self.make_builder(make_pass_texts())
        shutil.rmtree(b.archive / "runs")
        proc = run_cli(b.repo, b.archive)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("FAIL", proc.stdout.decode("utf-8"))

    def test_duplicate_user_message_exit2(self):
        b = self.make_builder(make_pass_texts())
        target = b.archive / "runs" / SLOTS[1] / "trace" / "sess.jsonl"
        line = target.read_text(encoding="utf-8")
        target.write_text(line + line, encoding="utf-8")
        proc = run_cli(b.repo, b.archive)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("role=user 消息数=2", proc.stdout.decode("utf-8"))

    def test_two_trace_jsonls_exit2(self):
        b = self.make_builder(make_pass_texts())
        tdir = b.archive / "runs" / SLOTS[2] / "trace"
        shutil.copyfile(tdir / "sess.jsonl", tdir / "sess2.jsonl")
        proc = run_cli(b.repo, b.archive)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("session jsonl 数=2", proc.stdout.decode("utf-8"))

    def test_stdout_deterministic_two_runs(self):
        b = self.make_builder(make_pass_texts())
        p1 = run_cli(b.repo, b.archive)
        p2 = run_cli(b.repo, b.archive)
        self.assertEqual(p1.returncode, 0)
        self.assertEqual(p1.stdout, p2.stdout)

    def test_stdout_deterministic_python_O(self):
        b = self.make_builder(make_pass_texts())
        p1 = run_cli(b.repo, b.archive)
        p2 = run_cli(b.repo, b.archive, extra_flags=("-O",))
        self.assertEqual(p1.returncode, 0)
        self.assertEqual(p2.returncode, 0)
        self.assertEqual(p1.stdout, p2.stdout)

    def test_value_independence_no_values_or_paths(self):
        texts = make_pass_texts()
        b = self.make_builder(texts)
        out = self.out_path()
        proc = run_cli(b.repo, b.archive, output=out)
        self.assertEqual(proc.returncode, 0)
        blob = out.read_bytes().decode("utf-8") + proc.stdout.decode("utf-8")
        # 禁止出现：消息正文/信封标记字面、合成填充串、任何本机路径；
        # （input_text 为提取规则里的 schema 字段名，非内容字节，不在禁列）
        for bad in ('"text"', "system-reminder", str(b.tmp),
                    str(b.repo), str(b.archive), "xxxxx", "yyyyy", "zzzzz"):
            self.assertNotIn(bad, blob, "疑似登记了文本内容或私有路径: %s" % bad)
        result = json.loads(out.read_text(encoding="utf-8"))
        self.assertIn("value_independence_statement", result)
        allowed_reg_keys = {"offset", "rel_position", "lane", "cluster_role", "by_rep"}
        allowed_run_keys = {"run_found", "run_start", "run_end", "run_len",
                            "drift_index_in_run", "left_neighbor_class",
                            "drift_byte_class"}
        for case in GROUPS:
            for e in result["run_registration"]["cases"][case]:
                self.assertTrue(set(e) <= allowed_reg_keys, set(e))
                for rep in REPS:
                    self.assertTrue(set(e["by_rep"][rep]) <= allowed_run_keys,
                                    set(e["by_rep"][rep]))
                    vals = set(e["by_rep"][rep].values())
                    for v in vals:
                        if isinstance(v, str):
                            self.assertIn(v, {"digit", "alpha", "other", "bof"}, v)


class RealArchiveTests(VerifyTestBase):
    """真档案端到端：WB_TOKEN_SHAPE_ARCHIVE_ROOT 未设则响亮 FAIL（与环 6/11 同约定）。"""

    def _roots(self, require_dual=False):
        env_value = os.environ.get(ENV_VAR, "").strip()
        if not env_value:
            self.fail("环境变量 %s 未设置：真档案端到端与 fresh==stored 校验无法运行"
                      "（响亮 FAIL，不许静默跳过）；请设为 WorkBuddy 复测档根，"
                      "可用 os.pathsep 分隔多根做双档一致性" % ENV_VAR)
        roots = [Path(p) for p in env_value.split(os.pathsep) if p.strip()]
        for r in roots:
            self.assertTrue((r / "runs").is_dir(), "档根缺 runs/: %s" % r.name)
        if require_dual and len(roots) < 2:
            self.fail("双档一致性需要 ≥2 个档根（%s 用 os.pathsep 分隔，如 "
                      "\"root1:root2\"，第二档为同一档案的独立副本）" % ENV_VAR)
        return roots

    def test_real_archive_end_to_end(self):
        roots = self._roots()
        procs = [run_cli(REPO_ROOT, r) for r in roots]
        for r, proc in zip(roots, procs):
            self.assertEqual(proc.returncode, 0,
                             "archive_root=%s\n%s" % (r.name, proc.stdout.decode("utf-8")))
        stdouts = {proc.stdout for proc in procs}
        self.assertEqual(len(stdouts), 1, "多档 stdout 不一致（双档一致性破坏）")
        out = procs[0].stdout.decode("utf-8")
        self.assertIn("PASS", out)
        self.assertIn("branch=B-DIGIT-RUN-FIXED-SHAPE", out)
        self.assertIn("offsets_hard_equal=true", out)
        self.assertIn("run_registration: offsets=14 entries=42 run_found_false=0", out)
        self.assertIn("S1=true shape=DD?DD", out)
        self.assertIn("S2=true", out)
        self.assertIn("S3=true", out)

    def test_real_archive_fresh_matches_stored(self):
        roots = self._roots()
        fresh_dir = Path(tempfile.mkdtemp(prefix="wbshapefresh_"))
        proc = run_cli(REPO_ROOT, roots[0], output=fresh_dir / "fresh.json")
        self.assertEqual(proc.returncode, 0, proc.stdout)
        stored = STORED_RESULT.read_bytes()
        fresh = (fresh_dir / "fresh.json").read_bytes()
        self.assertEqual(hashlib.sha256(stored).hexdigest(),
                         hashlib.sha256(fresh).hexdigest(),
                         "fresh result 与包内 stored result.json 不一致")
        self.assertEqual(stored, fresh)

    def test_real_archive_dual_result_bytes_equal(self):
        roots = self._roots(require_dual=True)
        blobs = []
        for r in roots:
            fresh_dir = Path(tempfile.mkdtemp(prefix="wbshapedual_"))
            proc = run_cli(REPO_ROOT, r, output=fresh_dir / "fresh.json")
            self.assertEqual(proc.returncode, 0, proc.stdout)
            blobs.append((fresh_dir / "fresh.json").read_bytes())
        self.assertEqual(len(set(blobs)), 1, "双档 result.json 不逐字节一致")

    def test_real_archive_expectations(self):
        roots = self._roots()
        fresh_dir = Path(tempfile.mkdtemp(prefix="wbshapeexp_"))
        proc = run_cli(REPO_ROOT, roots[0], output=fresh_dir / "fresh.json")
        self.assertEqual(proc.returncode, 0, proc.stdout)
        result = json.loads((fresh_dir / "fresh.json").read_text(encoding="utf-8"))
        self.assertTrue(result["offsets_hard_equal"]["all_equal"])
        ring11 = json.loads((REPO_ROOT / REF_RESULT_REL).read_text(encoding="utf-8"))
        for case in sorted(GROUPS):
            ref_offs = sorted({o for ev in ring11["case_analysis"][case]["events"]
                               for o in ev["positions_offset"]})
            self.assertEqual(result["offsets_hard_equal"]["cases"][case]
                             ["recomputed_sorted"], ref_offs)
            a = result["assertions"]
            self.assertTrue(a["S1"]["cases"][case]["pass"])
            self.assertTrue(a["S2"]["cases"][case]["all_equal"])
            self.assertTrue(a["S3"]["cases"][case]["pass"])
            self.assertEqual(a["S1"]["cases"][case]["cluster_offsets"],
                             [o for o in ref_offs if o - 6330 in (93, 94, 96, 97)]
                             if case == "dabstep-payments-10"
                             else [o for o in ref_offs if o - 6286 in (93, 94, 96, 97)])
            self.assertEqual(a["S1"]["cases"][case]["per_rep"]["r1"]["gap_byte_class"],
                             "other")
            iso_rows = [r for r in result["isolated_positions_disclosure"]["cases"][case]
                        if r["cluster_role"] == "isolated_external"]
            self.assertEqual(len(iso_rows), 1)
            self.assertEqual(iso_rows[0]["run_len_by_rep"]["r1"], 1)
            self.assertEqual(iso_rows[0]["left_neighbor_class_by_rep"]["r1"], "alpha")
        items = json.dumps(result["survey_note_reconciliation"]["items"],
                           ensure_ascii=False)
        self.assertIn("信封外", items)
        self.assertIn("rel +330/+318", items)


if __name__ == "__main__":
    unittest.main(verbosity=2)
