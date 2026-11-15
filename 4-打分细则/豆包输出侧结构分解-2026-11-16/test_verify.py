#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_verify.py — 豆包输出侧结构分解（schema doubao-struct-v1）验证套件。

运行：
    python3 test_verify.py            # 合成用例必跑；真档案用例由 env 门控
    DOUBAO_STRUCT_ARCHIVE_ROOT=<bw-retest/doubao 根> python3 test_verify.py
        # 真档案端到端；可用 ':' 分隔多档（双档一致性检查）

门控语义：env 未设置时，真档案用例**响亮 FAIL**（拒绝静默跳过）——按预注册要求，
真档案端到端必须显式提供档案根才能声明通过。

合成用例覆盖（预注册 §4）：早分岔/晚收敛分类、序列展开顺序、逐工具字节表、
硬等参照防篡改（篡改→FAILED exit2）、--output 拒绝覆盖、README SHA 防篡改、
每槽多轨迹 exit2、槽位漂移 exit2、schema 违例 exit2、隐私金丝雀不出现在输出。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]  # <repo>/4-打分细则/<包名> → <repo>（parents[0]=4-打分细则）
VERIFY = HERE / "verify.py"
PKG_NAME = "豆包输出侧结构分解-2026-11-16"
HARDEQUAL_DOC = REPO_ROOT / "4-打分细则" / "预注册复测选题-2026-11-08" / "复测登记-r1109.md"
ENV_VAR = "DOUBAO_STRUCT_ARCHIVE_ROOT"

sys.path.insert(0, str(HERE))
import verify as V  # noqa: E402


def run_verify(root, archive_root, output=None):
    cmd = [sys.executable, str(VERIFY), "--root", str(root),
           "--archive-root", str(archive_root)]
    if output is not None:
        cmd += ["--output", str(output)]
    return subprocess.run(cmd, capture_output=True)


def assistant(*names, args_fmt="{}"):
    return {"role": "assistant",
            "tool_calls": [{"id": f"c{i}", "type": "function",
                            "function": {"name": n, "arguments": args_fmt}}
                           for i, n in enumerate(names)]}


def tool(cid, content="ok"):
    return {"role": "tool", "content": content, "tool_call_id": cid}


def pure_assistant(text="done"):
    return {"role": "assistant", "content": text}


def write_slot(arch: Path, slot: str, rows, agent="agentX", extra_agent_rows=None):
    base = arch / "runs" / f"tb-cargo-plan__{slot}" / "trace" / "session" / "agents"
    for name, rws in ((agent, rows), (agent + "2", extra_agent_rows)):
        if rws is None:
            continue
        p = base / name / "system"
        p.mkdir(parents=True, exist_ok=True)
        (p / "trajectory.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rws), encoding="utf-8")


def canonical_len(obj) -> int:
    return len(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                          separators=(",", ":")).encode("utf-8"))


def make_repo(tmp: Path, readme_text: str | None = None,
              hard_equal_text: str | None = None) -> Path:
    """合成仓库根：包内 README（默认拷贝冻结原件）+ 硬等参照（默认拷贝原件）+ git 仓库。"""
    root = tmp / "repo"
    pkg = root / "4-打分细则" / PKG_NAME
    he_dir = root / "4-打分细则" / "预注册复测选题-2026-11-08"
    pkg.mkdir(parents=True)
    he_dir.mkdir(parents=True)
    (pkg / "README.md").write_text(
        readme_text if readme_text is not None else (HERE / "README.md").read_text(encoding="utf-8"),
        encoding="utf-8")
    (he_dir / "复测登记-r1109.md").write_text(
        hard_equal_text if hard_equal_text is not None else HARDEQUAL_DOC.read_text(encoding="utf-8"),
        encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@example.test",
                    "commit", "--allow-empty", "-q", "-m", "init"], check=True, capture_output=True)
    return root


class TestUnitFunctions(unittest.TestCase):
    """verify.py 单元函数：LCP、分类边界、canonical 字节。"""

    def test_lcp_len(self):
        self.assertEqual(V.lcp_len(["a", "b", "c"], ["a", "b", "d"]), 2)
        self.assertEqual(V.lcp_len(["a"], ["a", "b"]), 1)
        self.assertEqual(V.lcp_len([], ["a"]), 0)
        self.assertEqual(V.lcp_len(["x"], ["y"]), 0)

    def test_three_way_lcp(self):
        self.assertEqual(V.three_way_lcp([["a", "b", "c"], ["a", "b", "d"], ["a", "b", "e"]]), 2)
        self.assertEqual(V.three_way_lcp([["a"], ["b"], ["a"]]), 0)

    def test_classify_early(self):
        self.assertEqual(V.classify(2, 6), "H-EARLY-DIVERGENCE")  # 2 < 3.0

    def test_classify_boundary_equal_is_late(self):
        # 边界：LCP == min/2 时按预注册「≥ ⇒ LATE」
        self.assertEqual(V.classify(2, 4), "H-LATE-CONVERGENCE")
        self.assertEqual(V.classify(3, 6), "H-LATE-CONVERGENCE")

    def test_canonical_bytes(self):
        fn = {"name": "Read", "arguments": "{\"p\": \"中文\"}"}
        self.assertEqual(V.canonical_json_bytes(fn), canonical_len(fn))
        self.assertEqual(V.canonical_json_bytes({"b": 1, "a": 2}),
                         len(b'{"a":2,"b":1}'))


class TestSynthetic(unittest.TestCase):
    """合成档案用例：分类、序列、字节表、防篡改、fail-closed 行为。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self.repo = make_repo(tmp)
        self.arch = tmp / "arch"
        self.arch.mkdir()
        # EARLY 基础档案（各测试可覆写）：三方 LCP=2 < min/2=3.0
        early = {
            "r1": [assistant("Bash"), tool("c0"), assistant("Read"), tool("c0"),
                   assistant("Read"), tool("c0")],
            "r2": [assistant("Bash"), tool("c0"), assistant("Edit"), tool("c0"),
                   assistant("Edit"), tool("c0")],
            "r3": [assistant("Bash"), tool("c0"), assistant("Read"), tool("c0"),
                   assistant("Read"), tool("c0")],
        }
        for slot, rows in early.items():
            write_slot(self.arch, slot, rows)
        self.out = tmp / "result.json"

    def tearDown(self):
        self._tmp.cleanup()

    def verify(self, repo=None, arch=None, output="UNSET"):
        kw = {}
        if output != "UNSET":
            kw["output"] = None if output is None else output
        return run_verify(repo or self.repo, arch or self.arch, **kw)

    # ---- 分类 ----

    def test_01_early_divergence_classification(self):
        p = self.verify(output=self.out)
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
        result = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(result["branch"]["verdict"], "H-EARLY-DIVERGENCE")
        self.assertEqual(result["sequence_comparison"]["three_way_lcp"], 2)
        self.assertEqual(result["sequence_comparison"]["first_divergence_index"], 2)
        self.assertEqual(result["sequence_comparison"]["first_divergence_elements"],
                         {"r1": "Read", "r2": "Edit", "r3": "Read"})

    def test_02_late_convergence_classification(self):
        # 共享长主干（5/6）后段分岔：LCP=5 ≥ 3.0
        late = {
            "r1": [assistant("Bash"), tool("c0"), assistant("Read"), tool("c0"),
                   assistant("Read"), tool("c0")],
            "r2": [assistant("Bash"), tool("c0"), assistant("Read"), tool("c0"),
                   assistant("Read"), assistant("Edit")],
            "r3": [assistant("Bash"), tool("c0"), assistant("Read"), tool("c0"),
                   assistant("Read"), assistant("Write")],
        }
        for slot, rows in late.items():
            write_slot(self.arch, slot, rows)
        p = self.verify(output=self.out)
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
        result = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(result["branch"]["verdict"], "H-LATE-CONVERGENCE")
        self.assertEqual(result["sequence_comparison"]["three_way_lcp"], 5)

    # ---- 结构登记 ----

    def test_03_sequence_expansion_order(self):
        # 并行 tool_calls：assistant 行按 tool_calls 顺序展开三个 Read，随后三个 T
        rows = [assistant("Read", "Read", "Read"), tool("c0"), tool("c1"), tool("c2")]
        write_slot(self.arch, "r1", rows)
        p = self.verify(output=self.out)
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
        result = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(result["per_rep"]["r1"]["tool_name_sequence"],
                         ["Read", "Read", "Read", "T", "T", "T"])
        self.assertEqual(result["per_rep"]["r1"]["n_tool_calls"], 3)
        self.assertEqual(result["per_rep"]["r1"]["n_tool_lines"], 3)

    def test_04_per_tool_byte_table(self):
        fn_bash = {"name": "Bash", "arguments": "{\"cmd\": \"ls -la\", \"n\": 1}"}
        fn_read = {"name": "Read", "arguments": "{\"path\": \"a 中文 b\"}"}
        rows = [
            {"role": "assistant", "tool_calls": [
                {"id": "c0", "type": "function", "function": fn_bash},
                {"id": "c1", "type": "function", "function": fn_read}]},
            tool("c0"), tool("c1"),
        ]
        write_slot(self.arch, "r1", rows)
        p = self.verify(output=self.out)
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
        result = json.loads(self.out.read_text(encoding="utf-8"))
        r1 = result["per_rep"]["r1"]
        self.assertEqual(r1["function_canonical_bytes_by_name"],
                         {"Bash": canonical_len(fn_bash), "Read": canonical_len(fn_read)})
        self.assertEqual(r1["function_canonical_bytes_total"],
                         canonical_len(fn_bash) + canonical_len(fn_read))

    def test_05_tool_result_bytes_str_and_nonstr(self):
        s1 = "结果×2 🚀 中文"          # str：UTF-8 字节
        rows_r1 = [assistant("Bash"), tool("c0", s1),
                   {"role": "assistant", "tool_calls": [
                       {"id": "c1", "type": "function",
                        "function": {"name": "Read", "arguments": "{}"}}]},
                   {"role": "tool", "content": [1, 2], "tool_call_id": "c1"}]  # 非 str：canonical JSON
        write_slot(self.arch, "r1", rows_r1)
        p = self.verify(output=self.out)
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
        r1 = json.loads(self.out.read_text(encoding="utf-8"))["per_rep"]["r1"]
        self.assertEqual(r1["tool_result_content_bytes_total"],
                         len(s1.encode("utf-8")) + canonical_len([1, 2]))
        self.assertEqual(r1["tool_result_content_types"], {"list": 1, "str": 1})

    def test_06_pure_assistant_turn_count(self):
        rows = [assistant("Bash"), tool("c0"), pure_assistant("无需工具的纯回复轮")]
        write_slot(self.arch, "r1", rows)
        p = self.verify(output=self.out)
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
        r1 = json.loads(self.out.read_text(encoding="utf-8"))["per_rep"]["r1"]
        self.assertEqual(r1["n_pure_assistant_turns"], 1)
        self.assertEqual(r1["n_assistant_lines"], 2)
        self.assertEqual(r1["tool_name_sequence"], ["Bash", "T"])

    # ---- 内容无关 ----

    def test_07_privacy_canary_absent_from_stdout_and_result(self):
        canary_arg = "PRIVACY-CANARY-ARG-9d1f"
        canary_content = "PRIVACY-CANARY-CONTENT-3c7a"
        rows = [
            {"role": "assistant", "content": canary_content, "tool_calls": [
                {"id": "c0", "type": "function",
                 "function": {"name": "Bash", "arguments": json.dumps({"cmd": canary_arg})}}]},
            tool("c0", canary_content),
            pure_assistant(canary_content),
        ]
        for slot in ("r1", "r2", "r3"):
            write_slot(self.arch, slot, rows)
        p = self.verify(output=self.out)
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
        stdout = p.stdout.decode("utf-8", "replace")
        result_text = self.out.read_text(encoding="utf-8")
        for c in (canary_arg, canary_content):
            self.assertNotIn(c, stdout, "参数/内容值泄漏到 stdout")
            self.assertNotIn(c, result_text, "参数/内容值泄漏到 result.json")

    # ---- --output 行为 ----

    def test_08_output_refuse_overwrite(self):
        target = self.arch.parent / "preexisting.json"
        target.write_bytes(b"KEEP-ME")
        p = self.verify(output=target)
        self.assertEqual(p.returncode, 2)
        self.assertIn("拒绝覆盖", p.stderr.decode("utf-8", "replace"))
        self.assertEqual(target.read_bytes(), b"KEEP-ME", "既有文件被覆盖")

    def test_09_output_success_creates_valid_result(self):
        target = self.arch.parent / "fresh.json"
        self.assertFalse(target.exists())
        p = self.verify(output=target)
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
        result = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(result["schema"], "doubao-struct-v1")
        self.assertEqual(result["prereg_sha256"], V.EXPECTED_PREREG_SHA256)
        self.assertTrue(re.fullmatch(r"[0-9a-f]{40}", result["baseline_commit"]))
        self.assertIn("content_agnostic", result)
        self.assertTrue(result["hard_equal"]["passed"])
        # fail-closed：失败时不得写出
        bad_arch = self.arch
        shutil.rmtree(bad_arch / "runs" / "tb-cargo-plan__r3")
        p2 = self.verify(output=self.arch.parent / "never.json")
        self.assertEqual(p2.returncode, 2)
        self.assertFalse((self.arch.parent / "never.json").exists())

    # ---- 防篡改 ----

    def test_10_readme_sha_antitamper(self):
        tampered = (HERE / "README.md").read_text(encoding="utf-8") + "\n<!-- tampered -->\n"
        repo2 = make_repo(Path(self._tmp.name) / "tamper_readme", readme_text=tampered)
        p = self.verify(repo=repo2)
        self.assertEqual(p.returncode, 2)
        self.assertIn("SHA256", p.stderr.decode("utf-8", "replace"))

    def test_11_hard_equal_drift_detected(self):
        text = HARDEQUAL_DOC.read_text(encoding="utf-8")
        drifted = text.replace("weighted [81.48, 70.37, 81.48]（原批 [81.48, 70.37, 70.37]）",
                               "weighted [99.99, 70.37, 81.48]（原批 [81.48, 70.37, 70.37]）", 1)
        self.assertNotEqual(text, drifted, "防篡改夹具未产生变化")
        repo2 = make_repo(Path(self._tmp.name) / "tamper_he", hard_equal_text=drifted)
        p = self.verify(repo=repo2)
        self.assertEqual(p.returncode, 2)
        self.assertIn("硬等漂移", p.stderr.decode("utf-8", "replace"))

    def test_12_hard_equal_parse_failure(self):
        text = HARDEQUAL_DOC.read_text(encoding="utf-8")
        # 行仍在（豆包×tb 选择命中）但 reward/weighted 数组被移除 → 解析失败
        broken = text.replace("- 豆包 × tb：reward **[0, 0, 0]**（原批 [0, 0, 0]）；"
                              "weighted [81.48, 70.37, 81.48]（原批 [81.48, 70.37, 70.37]）",
                              "- 豆包 × tb：（reward/weighted 数据已移除）", 1)
        self.assertNotEqual(text, broken, "解析失败夹具未产生变化")
        repo2 = make_repo(Path(self._tmp.name) / "break_he", hard_equal_text=broken)
        p = self.verify(repo=repo2)
        self.assertEqual(p.returncode, 2)
        self.assertIn("硬等参照解析失败", p.stderr.decode("utf-8", "replace"))

    # ---- fail-closed 结构校验 ----

    def test_13_multiple_trajectories_exit2(self):
        write_slot(self.arch, "r1", [assistant("Bash"), tool("c0")], extra_agent_rows=[assistant("Read")])
        p = self.verify()
        self.assertEqual(p.returncode, 2)
        self.assertIn("恰 1 个", p.stderr.decode("utf-8", "replace"))

    def test_14_missing_slot_exit2(self):
        shutil.rmtree(self.arch / "runs" / "tb-cargo-plan__r2")
        p = self.verify()
        self.assertEqual(p.returncode, 2)

    def test_15_extra_slot_exit2(self):
        (self.arch / "runs" / "tb-cargo-plan__r4").mkdir(parents=True)
        p = self.verify()
        self.assertEqual(p.returncode, 2)
        self.assertIn("槽位与预注册不符", p.stderr.decode("utf-8", "replace"))

    def test_16_schema_violation_unknown_role_exit2(self):
        write_slot(self.arch, "r3", [{"role": "user", "content": "hi"}])
        p = self.verify()
        self.assertEqual(p.returncode, 2)
        self.assertIn("未登记 role", p.stderr.decode("utf-8", "replace"))

    def test_17_tool_row_missing_key_exit2(self):
        write_slot(self.arch, "r3", [assistant("Bash"), {"role": "tool", "content": "x"}])
        p = self.verify()
        self.assertEqual(p.returncode, 2)
        self.assertIn("tool_call_id", p.stderr.decode("utf-8", "replace"))


class TestRealArchive(unittest.TestCase):
    """真档案端到端（env DOUBAO_STRUCT_ARCHIVE_ROOT 门控；未设=响亮 FAIL，拒绝静默跳过）。"""

    @classmethod
    def setUpClass(cls):
        raw = os.environ.get(ENV_VAR, "").strip()
        cls.roots = [Path(x) for x in raw.split(":") if x.strip()]
        if not cls.roots:
            raise AssertionError(
                f"{ENV_VAR} 未设置：真档案端到端测试拒绝静默跳过——"
                f"请设为 bw-retest/doubao 档案根（多档用 ':' 分隔）后重跑套件")

    def test_20_end_to_end_each_root(self):
        for arch in self.roots:
            with self.subTest(archive=str(arch)):
                with tempfile.TemporaryDirectory() as td:
                    out = Path(td) / "result.json"
                    p = run_verify(REPO_ROOT, arch, output=out)
                    self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
                    self.assertIn("verdict: OK", p.stdout.decode("utf-8", "replace"))
                    result = json.loads(out.read_text(encoding="utf-8"))
                    self.assertEqual(result["schema"], "doubao-struct-v1")
                    self.assertEqual(result["prereg_sha256"], V.EXPECTED_PREREG_SHA256)
                    self.assertTrue(result["hard_equal"]["passed"], "真档案硬等未通过")
                    sc = result["sequence_comparison"]
                    expect = V.classify(sc["three_way_lcp"], sc["min_sequence_length"])
                    self.assertEqual(result["branch"]["verdict"], expect, "分支判定与规则不一致")
                    for rep in ("r1", "r2", "r3"):
                        r = result["per_rep"][rep]
                        self.assertEqual(len(r["tool_name_sequence"]),
                                         r["n_tool_calls"] + r["n_tool_lines"])
                        self.assertEqual(r["n_lines"], r["n_assistant_lines"] + r["n_tool_lines"])
                        self.assertEqual(sum(r["tool_call_counts"].values()), r["n_tool_calls"])
                        self.assertEqual(sum(r["function_canonical_bytes_by_name"].values()),
                                         r["function_canonical_bytes_total"])

    def test_21_dual_archive_stdout_byte_identical(self):
        stdouts = []
        for arch in self.roots:
            p = run_verify(REPO_ROOT, arch)
            self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
            stdouts.append(p.stdout)
        for s in stdouts:  # 同档重跑确定性
            self.assertEqual(s, stdouts[0], "双档/重跑 stdout 不逐字节一致")

    def test_22_fresh_result_equals_stored(self):
        stored = HERE / "result.json"
        if not stored.is_file():
            self.fail("包内 result.json 不存在：请先以 verify.py --output 生成为正式结果再跑套件")
        with tempfile.TemporaryDirectory() as td:
            fresh = Path(td) / "fresh.json"
            p = run_verify(REPO_ROOT, self.roots[0], output=fresh)
            self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
            self.assertEqual(fresh.read_bytes(), stored.read_bytes(),
                             "fresh result.json 与包内 stored 不逐字节一致")


if __name__ == "__main__":
    unittest.main(verbosity=2)
