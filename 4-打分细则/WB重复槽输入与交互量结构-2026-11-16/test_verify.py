#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_verify.py — WB重复槽输入与交互量结构-2026-11-16 验证器测试套件。

运行：python3 test_verify.py [-v]（python3 -O 同样须全绿）。

真档案端到端测试经环境变量门控：
  WB_STRUCT_ARCHIVE_ROOT  = WorkBuddy 复测档根（其下含 runs/ 与
                            evidence-tools/grading/）。
  WB_STRUCT_REPO_ROOT     = 公开仓库根（可选；默认取本文件上两级）。
未设 WB_STRUCT_ARCHIVE_ROOT 时真档案测试 **loudly FAIL**，拒绝静默跳过。

单元测试用合成迷你文本与合成档案（含合成钉定常量），不含任何真实
信封或任务文本内容。verify.main(pins=...) 仅测试可注入合成常量；
CLI 路径恒用冻结 DEFAULT_PINS。
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

PKG_DIR = Path(__file__).resolve().parent
DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PKG_DIR))

import verify as V  # noqa: E402

ENV_OPEN = b'<system-reminder data-role="user-context">'
ENV_CLOSE = b"</system-reminder>"

SYN_SIDS = {slot: "00000000-0000-0000-0000-%012d" % i
            for i, slot in enumerate(V.SLOT_ORDER)}
SYN_TEXTS = {
    "dabstep-payments-10": ENV_OPEN + b"ENV-CONTEXT-DAB" + ENV_CLOSE + b"TASK-DAB-BODY",
    "tb-cargo-plan": ENV_OPEN + b"ENV-CONTEXT-TB" + ENV_CLOSE + b"TASK-TB-BODY",
}
SYN_WEIGHTED = {
    "dabstep-payments-10__r1": 50.0,
    "dabstep-payments-10__r2": 70.0,
    "dabstep-payments-10__r3": 70.0,
    "tb-cargo-plan__r1": 0.0,
    "tb-cargo-plan__r2": 70.37,
    "tb-cargo-plan__r3": 70.37,
}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def build_synthetic_events(slot: str, user_text: bytes, fc_extra: int = 0):
    """一个合法槽的最小事件集；fc_extra>0 时多挂 function_call（不成对）。"""
    sid = SYN_SIDS[slot]
    events = [
        {"type": "session-meta", "id": "sm1", "sessionId": sid,
         "timestamp": 1000, "meta": {"h": "k"}},
        {"type": "message", "role": "user",
         "content": [{"type": "input_text", "text": user_text.decode("utf-8")}],
         "id": "u1", "sessionId": sid, "timestamp": 1001,
         "cwd": "/syn/workspace", "_meta": {"t": "1"}},
        {"type": "ai-title", "id": "at1", "aiTitle": "syn-title",
         "sessionId": sid, "timestamp": 1002},
        {"type": "file-history-snapshot", "messageId": "u1",
         "snapshot": "snap", "isSnapshotUpdate": True, "timestamp": 1003},
        {"type": "function_call", "id": "fc1", "callId": "c1", "name": "read",
         "arguments": "{}", "parentId": "u1", "sessionId": sid,
         "timestamp": 1004, "_meta": {}},
        {"type": "function_call_result", "id": "cr1", "callId": "c1",
         "output": "ok", "status": "success", "parentId": "fc1",
         "sessionId": sid, "timestamp": 1005, "_meta": {}},
        {"type": "reasoning", "id": "rs1", "content": "c", "rawContent": "rc",
         "parentId": "u1", "sessionId": sid, "timestamp": 1006, "_meta": {}},
        {"type": "message", "role": "assistant",
         "content": [{"type": "output_text", "text": "done"}],
         "id": "a1", "sessionId": sid, "timestamp": 1007,
         "status": "completed", "_meta": {},
         "providerData": {"model": "syn-model"}},
    ]
    for k in range(fc_extra):
        events.append({"type": "function_call", "id": "fcx%d" % k,
                       "callId": "cx%d" % k, "name": "read", "arguments": "{}",
                       "parentId": "u1", "sessionId": sid, "timestamp": 1100 + k})
    return events


def build_synthetic_archive(base: Path):
    """构造全 6 槽合法合成档案（两组文本组内逐字节稳定），返回合成 pins。"""
    base.mkdir(parents=True, exist_ok=True)
    pins = {"slots": {}}
    for slot in V.SLOT_ORDER:
        case, _, rep = slot.rpartition("__")
        sid = SYN_SIDS[slot]
        tdir = base / "runs" / slot / "trace"
        tdir.mkdir(parents=True)
        events = build_synthetic_events(slot, SYN_TEXTS[case])
        raw = ("\n".join(json.dumps(e, ensure_ascii=False) for e in events)
               + "\n").encode("utf-8")
        (tdir / (sid + ".jsonl")).write_bytes(raw)
        gobj = {"category": "offline_recompute", "case": case,
                "rep": int(rep[1:]), "session_id": sid,
                "result": {"reward": 0, "weighted": SYN_WEIGHTED[slot]}}
        graw = (json.dumps(gobj, ensure_ascii=False) + "\n").encode("utf-8")
        gdir = base / "evidence-tools" / "grading" / slot
        gdir.mkdir(parents=True)
        (gdir / "execution.json").write_bytes(graw)
        pins["slots"][slot] = {
            "trace_file": sid + ".jsonl",
            "trace_sha256": sha(raw),
            "trace_bytes": len(raw),
            "session_id": sid,
            "user_text_sha256": sha(SYN_TEXTS[case]),
            "user_text_bytes": len(SYN_TEXTS[case]),
            "grading_sha256": sha(graw),
            "reward": 0,
            "weighted": SYN_WEIGHTED[slot],
        }
    return pins


def recompute_trace_pins(pins: dict, base: Path, slot: str) -> None:
    """改写 trace 后同步重算该槽 trace 侧钉定（不含 user_text 域）。"""
    p = base / "runs" / slot / "trace" / (SYN_SIDS[slot] + ".jsonl")
    raw = p.read_bytes()
    pins["slots"][slot]["trace_sha256"] = sha(raw)
    pins["slots"][slot]["trace_bytes"] = len(raw)


def slot_jsonl_path(base: Path, slot: str) -> Path:
    return base / "runs" / slot / "trace" / (SYN_SIDS[slot] + ".jsonl")


def rewrite_slot_trace(base: Path, slot: str, events) -> None:
    raw = ("\n".join(json.dumps(e, ensure_ascii=False) for e in events)
           + "\n").encode("utf-8")
    slot_jsonl_path(base, slot).write_bytes(raw)


class VerifyTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="wbstruct-test-")
        self.addCleanup(self._tmp.cleanup)
        self.archive = Path(self._tmp.name) / "archive"
        self.pins = build_synthetic_archive(self.archive)

    def run_verify(self, pins=None, root=None, archive=None):
        return V.run_verification(
            root if root is not None else DEFAULT_REPO_ROOT,
            archive if archive is not None else self.archive,
            pins=self.pins if pins is None else pins)


class TestW1Classification(VerifyTestBase):
    """W1 分类逻辑单元测试（合成迷你文本，四种情形 + 结构登记）。"""

    def test_w1_all_stable_classification(self):
        texts = {"r1": b"TASK-SAME", "r2": b"TASK-SAME", "r3": b"TASK-SAME"}
        g = V.classify_w1_group(texts)
        self.assertEqual(g["classification"], "w1_stable")
        for pair in g["pairs"]:
            self.assertTrue(pair["byte_equal"])
            self.assertEqual(pair["n_diff_offsets"], 0)

    def test_w1_diffs_all_inside_envelope(self):
        t1 = ENV_OPEN + b"ENV-AAAA" + ENV_CLOSE + b"TASK-SAME"
        t2 = ENV_OPEN + b"ENV-BBBB" + ENV_CLOSE + b"TASK-SAME"
        t3 = ENV_OPEN + b"ENV-CCCC" + ENV_CLOSE + b"TASK-SAME"
        g = V.classify_w1_group({"r1": t1, "r2": t2, "r3": t3})
        self.assertEqual(g["classification"], "w1_env_volatile")
        for pair in g["pairs"]:
            self.assertFalse(pair["byte_equal"])
            self.assertEqual(pair["n_offsets_outside_envelope"], 0)
            self.assertEqual(pair["pair_result"], "env_internal_diff")

    def test_w1_diff_outside_envelope(self):
        t1 = ENV_OPEN + b"ENV-AAAA" + ENV_CLOSE + b"TASK-SAME-X"
        t2 = ENV_OPEN + b"ENV-AAAA" + ENV_CLOSE + b"TASK-SAME-Y"
        t3 = ENV_OPEN + b"ENV-BBBB" + ENV_CLOSE + b"TASK-SAME-X"
        g = V.classify_w1_group({"r1": t1, "r2": t2, "r3": t3})
        self.assertEqual(g["classification"], "w1_task_text_drift")
        outside_pairs = [p for p in g["pairs"] if p["n_offsets_outside_envelope"] > 0]
        self.assertTrue(outside_pairs)
        for pair in outside_pairs:
            for off in pair["offsets_outside_envelope"]:
                self.assertGreaterEqual(off, len(ENV_OPEN) + len(b"ENV-AAAA")
                                        + len(ENV_CLOSE))

    def test_w1_no_envelope(self):
        g = V.classify_w1_group({"r1": b"AAA", "r2": b"BBB", "r3": b"AAA"})
        self.assertEqual(g["classification"], "w1_no_envelope")
        self.assertEqual(sorted(g["envelope_missing_in_reps"]), ["r1", "r2", "r3"])
        self.assertEqual(g["pairs"], [])

    def test_w1_unclosed_envelope_registered(self):
        # 有差异 + 信封未闭合 → 结构登记（classification=None）；全同时不走到此分支。
        t1 = ENV_OPEN + b"ENV-NO-CLOSE-A"
        t2 = ENV_OPEN + b"ENV-NO-CLOSE-B"
        g = V.classify_w1_group({"r1": t1, "r2": t2, "r3": t1})
        self.assertIsNone(g["classification"])
        self.assertEqual(g["classification_reason"], "unclosed_envelope_marker")
        self.assertEqual(g["pairs"], [])

    def test_global_branch_precedence(self):
        self.assertEqual(
            V.decide_global_branch({"a": "w1_task_text_drift",
                                    "b": "w1_env_volatile"})[0],
            "B-W1-TASK-DRIFT")
        self.assertEqual(
            V.decide_global_branch({"a": "w1_stable", "b": "w1_stable"})[0],
            "B-W1-STABLE")
        self.assertEqual(
            V.decide_global_branch({"a": "w1_env_volatile",
                                    "b": "w1_env_volatile"})[0],
            "B-W1-ENV-VOLATILE")
        self.assertIsNone(
            V.decide_global_branch({"a": "w1_stable", "b": "w1_no_envelope"})[0])


class TestSyntheticArchiveChecks(VerifyTestBase):
    def test_baseline_synthetic_archive_passes(self):
        result = self.run_verify()
        self.assertTrue(result["verdict"]["all_checks_passed"])
        self.assertEqual(result["w1"]["global_branch"], "B-W1-STABLE")

    def test_w3_tampered_pinned_weighted_fails(self):
        slot = "tb-cargo-plan__r2"
        tampered = json.loads(json.dumps(self.pins))
        tampered["slots"][slot]["weighted"] = 99.0  # 模拟公开页常量被篡改
        with self.assertRaises(V.VerifyError) as ctx:
            self.run_verify(pins=tampered)
        self.assertIn("W3 硬等失败", str(ctx.exception))

    def test_w3_archived_type_mismatch_fails(self):
        slot = "tb-cargo-plan__r2"
        gpath = self.archive / "evidence-tools" / "grading" / slot / "execution.json"
        gobj = json.loads(gpath.read_text(encoding="utf-8"))
        gobj["result"]["weighted"] = 70  # int，钉定常量为 float 70.37→改钉定同值
        gpath.write_text(json.dumps(gobj, ensure_ascii=False) + "\n",
                         encoding="utf-8")
        pins = json.loads(json.dumps(self.pins))
        pins["slots"][slot]["grading_sha256"] = sha(gpath.read_bytes())
        pins["slots"][slot]["weighted"] = 70.0  # 数值相等但类型不同 → 硬等失败
        with self.assertRaises(V.VerifyError) as ctx:
            self.run_verify(pins=pins)
        self.assertIn("W3 硬等失败", str(ctx.exception))

    def test_corrupted_trace_exit_2(self):
        slot = "dabstep-payments-10__r2"
        p = slot_jsonl_path(self.archive, slot)
        with open(p, "ab") as fh:
            fh.write(b'{"type":"message",broken\n')
        with self.assertRaises(V.VerifyError) as ctx:
            self.run_verify()
        self.assertIn("JSON 解析失败", str(ctx.exception))

    def test_trace_count_not_one_exit_2(self):
        slot = "dabstep-payments-10__r1"
        extra = (self.archive / "runs" / slot / "trace" / "extra.jsonl")
        extra.write_bytes(b'{"type":"ai-title"}\n')
        with self.assertRaises(V.VerifyError) as ctx:
            self.run_verify()
        self.assertIn("session jsonl 数=2", str(ctx.exception))

    def test_missing_user_message_exit_2(self):
        slot = "tb-cargo-plan__r1"
        events = [e for e in build_synthetic_events(slot, SYN_TEXTS["tb-cargo-plan"])
                  if not (e.get("type") == "message" and e.get("role") == "user")]
        rewrite_slot_trace(self.archive, slot, events)
        recompute_trace_pins(self.pins, self.archive, slot)
        with self.assertRaises(V.VerifyError) as ctx:
            self.run_verify()
        self.assertIn("role=user 消息数=0", str(ctx.exception))

    def test_user_text_sha_mismatch_exit_2(self):
        slot = "dabstep-payments-10__r3"
        events = build_synthetic_events(slot, b"tampered-user-text")
        rewrite_slot_trace(self.archive, slot, events)
        recompute_trace_pins(self.pins, self.archive, slot)  # trace 侧同步、文本钉定保持钉死
        with self.assertRaises(V.VerifyError) as ctx:
            self.run_verify()
        self.assertIn("user 文本 SHA256 不符", str(ctx.exception))

    def test_prereg_sha_mismatch_exit_2(self):
        with tempfile.TemporaryDirectory(prefix="wbstruct-fakeroot-") as td:
            fake_root = Path(td)
            prereg = fake_root / V.PREREG_PATH_REL
            prereg.parent.mkdir(parents=True)
            prereg.write_text("# tampered prereg\n", encoding="utf-8")
            with self.assertRaises(V.VerifyError) as ctx:
                self.run_verify(root=fake_root)
            self.assertIn("预注册 README SHA256 不符", str(ctx.exception))

    def test_w2_fc_fcr_inequality_registered_descriptive(self):
        slot = "tb-cargo-plan__r3"
        events = build_synthetic_events(slot, SYN_TEXTS["tb-cargo-plan"],
                                        fc_extra=1)
        rewrite_slot_trace(self.archive, slot, events)
        recompute_trace_pins(self.pins, self.archive, slot)
        result = self.run_verify()
        self.assertTrue(result["verdict"]["all_checks_passed"])
        self.assertFalse(result["w2"]["slots"][slot]["fc_fcr_count_equal"])

    def test_canonical_projection_strips_and_deterministic(self):
        ev = {"id": "x", "timestamp": 1, "sessionId": "s", "parentId": "p",
              "callId": "c", "messageId": "m", "cwd": "/w", "_meta": {},
              "__codebuddyLocal": {}, "providerData": {"traceId": "t"},
              "type": "message", "role": "user", "status": "done",
              "content": [{"type": "input_text", "text": "KEEP-ME"}]}
        b1 = V.canonicalize_event(ev)
        b2 = V.canonicalize_event(dict(ev))
        self.assertEqual(b1, b2)
        obj = json.loads(b1.decode("utf-8"))
        for key in V.STRIPPED_TOP_LEVEL_KEYS:
            self.assertNotIn(key, obj)
        self.assertEqual(obj["type"], "message")
        self.assertEqual(obj["content"][0]["text"], "KEEP-ME")
        self.assertEqual(b1, json.dumps(
            {k: v for k, v in ev.items() if k not in set(V.STRIPPED_TOP_LEVEL_KEYS)},
            sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


class TestCliBehaviour(VerifyTestBase):
    def _cli(self, args, pins=None):
        return V.main(args, pins=pins)

    def test_output_refuses_overwrite(self):
        out = Path(self._tmp.name) / "preexisting.json"
        out.write_text("KEEP-ORIGINAL", encoding="utf-8")
        rc = self._cli(["--root", str(DEFAULT_REPO_ROOT),
                        "--archive-root", str(self.archive),
                        "--output", str(out)], pins=self.pins)
        self.assertEqual(rc, 2)
        self.assertEqual(out.read_text(encoding="utf-8"), "KEEP-ORIGINAL")

    def test_cli_success_writes_result_json(self):
        out = Path(self._tmp.name) / "result.json"
        rc = self._cli(["--root", str(DEFAULT_REPO_ROOT),
                        "--archive-root", str(self.archive),
                        "--output", str(out)], pins=self.pins)
        self.assertEqual(rc, 0)
        obj = json.loads(out.read_text(encoding="utf-8"))
        self.assertTrue(obj["verdict"]["all_checks_passed"])
        # 已存在文件在验证前即被拒改：再次运行同命令必须 exit 2
        rc2 = self._cli(["--root", str(DEFAULT_REPO_ROOT),
                         "--archive-root", str(self.archive),
                         "--output", str(out)], pins=self.pins)
        self.assertEqual(rc2, 2)

    def test_cli_missing_archive_root_is_rejected(self):
        with self.assertRaises(SystemExit):
            V.main(["--root", str(DEFAULT_REPO_ROOT)])


class TestRealArchiveEndToEnd(unittest.TestCase):
    """真档案端到端（门控；未设环境变量 → loudly FAIL，拒绝静默跳过）。"""

    def _require_env(self):
        archive_root = os.environ.get("WB_STRUCT_ARCHIVE_ROOT")
        if not archive_root:
            self.fail("WB_STRUCT_ARCHIVE_ROOT 未设置：真档案端到端测试拒绝静默跳过"
                      "（loud FAIL）。请导出 WorkBuddy 复测档根后重跑。")
        return archive_root

    def test_real_archive_end_to_end_exit0(self):
        archive_root = self._require_env()
        proc = subprocess.run(
            [sys.executable, str(PKG_DIR / "verify.py"),
             "--root", str(DEFAULT_REPO_ROOT), "--archive-root", archive_root],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        self.assertEqual(proc.returncode, 0,
                         "stderr=%s" % proc.stderr.decode("utf-8", "replace"))
        out = proc.stdout.decode("utf-8")
        self.assertIn("RESULT: PASS", out)
        self.assertIn("W1 global branch:", out)
        self.assertIn("W3 hard-equal vs published constants: 6/6 OK", out)

    def test_real_archive_fresh_output_matches_stored_result(self):
        archive_root = self._require_env()
        with tempfile.TemporaryDirectory(prefix="wbstruct-e2e-") as td:
            out = Path(td) / "result.json"
            proc = subprocess.run(
                [sys.executable, str(PKG_DIR / "verify.py"),
                 "--root", str(DEFAULT_REPO_ROOT), "--archive-root", archive_root,
                 "--output", str(out)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
            self.assertEqual(proc.returncode, 0,
                             "stderr=%s" % proc.stderr.decode("utf-8", "replace"))
            stored = PKG_DIR / "result.json"
            self.assertTrue(stored.is_file(),
                            "包内正式 result.json 缺失（先由 verify.py --output 生成）")
            self.assertEqual(out.read_bytes(), stored.read_bytes(),
                             "fresh --output 与包内存储 result.json 不逐字节一致")

    def test_real_archive_dash_O_stdout_identical(self):
        archive_root = self._require_env()
        plain = subprocess.run(
            [sys.executable, str(PKG_DIR / "verify.py"),
             "--root", str(DEFAULT_REPO_ROOT), "--archive-root", archive_root],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        optim = subprocess.run(
            [sys.executable, "-O", str(PKG_DIR / "verify.py"),
             "--root", str(DEFAULT_REPO_ROOT), "--archive-root", archive_root],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        self.assertEqual(plain.returncode, 0, plain.stderr.decode("utf-8", "replace"))
        self.assertEqual(optim.returncode, 0, optim.stderr.decode("utf-8", "replace"))
        self.assertEqual(plain.stdout, optim.stdout,
                         "python3 与 python3 -O 的 stdout 不逐字节一致")


if __name__ == "__main__":
    unittest.main(verbosity=2)
