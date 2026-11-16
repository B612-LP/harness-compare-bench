#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WB漂移token值语义-2026-11-16：verify.py 测试套件。

双档设计（与 loop15 惯例一致）：
- 合成档案：临时目录组装 repo（复制真 README 保封印 + 由测试内独立复算生成
  环 11/环 15 合成参照 result.json）+ archive（6 槽 trace jsonl +
  collect-meta.json），覆盖全部 §3 分支与 CLI 防篡改守卫；
- 真档案端到端：env WB_TOKEN_SEM_ARCHIVE_ROOT="root1:root2"（os.pathsep 分隔
  的两个独立档案根副本）门控，未设置时响亮 FAIL。

本测试不 import verify 模块：byte_class / register_run / 参照结构均独立重实现，
subprocess 调 CLI 以行为为准。
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

PKG = Path(__file__).resolve().parent
REPO_ROOT = PKG.parent.parent
VERIFY_PATH = PKG / "verify.py"
STORED_RESULT = PKG / "result.json"
ENV_VAR = "WB_TOKEN_SEM_ARCHIVE_ROOT"

# 冻结 W1 信封标记（环 6/11/15 同一；与 verify.py 常量独立字面，漂移即测试失败）
ENVELOPE_OPEN = b'<system-reminder data-role="user-context">'
ENVELOPE_CLOSE = b"</system-reminder>"

SEG1 = b"a" * 90
SEG2 = b"b" * 40
TAIL_LEN = 400
CLUSTER_RELS = (93, 94, 96, 97)     # 环 15 簇 4 漂移数字（rel=offset−close）
ISO_REL = 330                       # 信封外孤立位
COLLECTED_AT = "2026-11-09T12:30:00+08:00"
TZ8 = timezone(timedelta(hours=8))

CASES = ("dabstep-payments-10", "tb-cargo-plan")
REPS = ("r1", "r2", "r3")
SLOTS = tuple("%s__%s" % (c, r) for c in CASES for r in REPS)

INSIDE1 = len(ENVELOPE_OPEN) + len(SEG1)          # 信封内孤立位 1
INSIDE2 = INSIDE1 + 1 + len(SEG2)                 # 信封内孤立位 2
CLOSE = INSIDE2 + 1 + len(ENVELOPE_CLOSE)         # 信封 span 终点
CLUSTER_OFFS = tuple(CLOSE + r for r in CLUSTER_RELS)
ISO_OFF = CLOSE + ISO_REL

HHMM_RE = re.compile(r"^\d{2}:\d{2}$")


# ---------------------------------------------------------------------------
# 独立复算工具（不 import verify 模块）
# ---------------------------------------------------------------------------

def byte_class(b):
    if 48 <= b <= 57:
        return "digit"
    if 65 <= b <= 90 or 97 <= b <= 122:
        return "alpha"
    return "other"


def register_run(text, off):
    """极大数字 run（语义与冻结登记一致；独立实现）。"""
    cls = byte_class(text[off])
    if cls != "digit":
        return {"run_found": False, "drift_byte_class": cls}
    s = off
    while s > 0 and byte_class(text[s - 1]) == "digit":
        s -= 1
    e = off + 1
    while e < len(text) and byte_class(text[e]) == "digit":
        e += 1
    return {
        "run_found": True,
        "run_start": s,
        "run_end": e,
        "run_len": e - s,
        "drift_index_in_run": off - s,
        "left_neighbor_class": byte_class(text[s - 1]) if s > 0 else "bof",
    }


def epoch_ms(day, hh, mm, ss=0):
    return int(datetime(2026, 11, day, hh, mm, ss, tzinfo=TZ8).timestamp() * 1000)


def build_text(token, iso_digit, marker=None):
    """合成 W1 文本：OPEN+SEG1(+可选标记,等长替换)+d1+SEG2+d2+CLOSE+tail。
    tail[93:98]=token 5 字节；tail[330]=孤立数字。全部 rep 等长。"""
    assert len(token) == 5
    seg1 = SEG1
    if marker:
        m = marker.encode("utf-8")
        assert len(m) <= len(SEG1)
        seg1 = m + SEG1[len(m):]
    d = iso_digit.encode("ascii")
    tail = bytearray(b"x" * TAIL_LEN)
    tail[CLUSTER_RELS[0]:CLUSTER_RELS[-1] + 1] = token.encode("ascii")
    tail[ISO_REL] = d[0]
    return ENVELOPE_OPEN + seg1 + d + SEG2 + d + ENVELOPE_CLOSE + bytes(tail)


def build_refs(texts_by_case):
    """由合成文本独立复算生成环 11 / 环 15 合成参照结构（防篡改设计的真值源）。"""
    ref11 = {"case_analysis": {}}
    ref15 = {"run_registration": {"cases": {}}}
    for case in CASES:
        texts = texts_by_case[case]
        union = set()
        for i in range(len(REPS)):
            for j in range(i + 1, len(REPS)):
                a, b = texts[REPS[i]], texts[REPS[j]]
                assert len(a) == len(b), "合成文本必须等长"
                union.update(k for k in range(len(a)) if a[k] != b[k])
        offs = sorted(union)
        t1 = texts["r1"]
        close = t1.find(ENVELOPE_CLOSE) + len(ENVELOPE_CLOSE)
        ref11["case_analysis"][case] = {
            "events": [{"positions_offset": [o]} for o in offs],
            "envelope_span": [[0, close]],
        }
        entries = []
        for off in offs:
            rel = off - close
            if rel in CLUSTER_RELS:
                role = "cluster"
            elif rel == ISO_REL:
                role = "isolated_external"
            else:
                role = "internal"
            entries.append({
                "offset": off,
                "cluster_role": role,
                "lane": role,
                "rel_position": rel,
                "by_rep": {rep: register_run(texts[rep], off) for rep in REPS},
            })
        ref15["run_registration"]["cases"][case] = entries
    return ref11, ref15


# ---------------------------------------------------------------------------
# 场景定义（合成值面；token 各字节位跨 rep 两两相异，保证漂移 offsets 结构不变）
# ---------------------------------------------------------------------------

def scn(tokens_dab, firsts_dab, tokens_tb, firsts_tb):
    return {
        "dabstep-payments-10": {
            rep: {"token": tokens_dab[i], "first": firsts_dab[i]}
            for i, rep in enumerate(REPS)
        },
        "tb-cargo-plan": {
            rep: {"token": tokens_tb[i], "first": firsts_tb[i]}
            for i, rep in enumerate(REPS)
        },
    }


SCN_CLOCK = scn(
    ["00:00", "11:11", "22:22"], [(9, 0, 0), (9, 11, 11), (9, 22, 22)],
    ["08:50", "19:06", "23:17"], [(9, 8, 50), (9, 19, 6), (9, 23, 17)],
)
# 期望：V1 全过（6/6 合法 HH:MM、分隔 6/6 ':'）、V2 全过（Δ=0）→ B-CLOCK-CONFIRMED

SCN_COUNTER_V1PASS = scn(
    ["00:00", "11:11", "22:22"], [(9, 9, 0), (9, 9, 5), (9, 9, 10)],
    ["08:50", "19:06", "23:17"], [(9, 1, 0), (9, 2, 0), (9, 3, 0)],
)
# 期望：V1 全过 ∧ V2 破（dab Δ=-540/+126/+792，tb Δ=+470/+1026/+1217）→ B-COUNTER-OTHER

SCN_COUNTER_V1BREAK = scn(
    ["00:00", "11:11", "25:55"], [(9, 8, 0), (9, 9, 0), (9, 10, 0)],
    ["05:40", "16:51", "23:02"], [(9, 11, 0), (9, 12, 0), (9, 13, 0)],
)
# 期望：V1 破（'25:55' 5/6）但 6 token 定长同格式（DD?DD、':' 全同）→ B-COUNTER-OTHER

SCN_INDETERMINATE = scn(
    ["00:00", "11.11", "22:22"], [(9, 8, 0), (9, 8, 5), (9, 8, 10)],
    ["05:40", "16.51", "23:02"], [(9, 9, 0), (9, 9, 5), (9, 9, 10)],
)
# 期望：r2 分隔字节 '.'→c95 成为漂移位（信封内孤立位数=3≠2，结构破坏）→ fail-closed exit 2

SCN_MIDNIGHT = scn(
    ["00:10", "23:59", "12:34"], [(8, 23, 59), (9, 10, 0), (9, 8, 0)],
    ["05:40", "16:51", "23:02"], [(9, 11, 0), (9, 11, 5), (9, 11, 10)],
)
# 期望：V1 全过 ∧ V2 破；dab r1 跨午夜：naive Δ=-1429、circular Δ=11（双登记）

SCENARIOS = {
    "clock": SCN_CLOCK,
    "counter_v1pass": SCN_COUNTER_V1PASS,
    "counter_v1break": SCN_COUNTER_V1BREAK,
    "indeterminate": SCN_INDETERMINATE,
    "midnight": SCN_MIDNIGHT,
}


# ---------------------------------------------------------------------------
# 环境组装与 CLI 调用
# ---------------------------------------------------------------------------

def write_slot(runs_dir, slot, text, first_ms, collected_at=COLLECTED_AT):
    tdir = runs_dir / slot / "trace"
    tdir.mkdir(parents=True)
    msgs = [
        {"type": "message", "role": "user", "timestamp": first_ms,
         "content": [{"type": "input_text", "text": text.decode("utf-8")}]},
        {"type": "message", "role": "assistant", "timestamp": first_ms + 60000,
         "content": [{"type": "input_text", "text": "assistant-alpha"}]},
        {"type": "message", "role": "assistant", "timestamp": first_ms + 120000,
         "content": [{"type": "input_text", "text": "assistant-beta"}]},
    ]
    lines = "".join(json.dumps(m, ensure_ascii=True) + "\n" for m in msgs)
    (tdir / "session.jsonl").write_bytes(lines.encode("utf-8"))
    (tdir / "collect-meta.json").write_bytes(
        json.dumps({"collected_at": collected_at}, sort_keys=True).encode("utf-8") + b"\n")


class Env:
    """一次性合成双根（repo + archive），全部位于 tempfile（/tmp）。"""

    def __init__(self, scenario, marker=None):
        self.tmp = Path(tempfile.mkdtemp(prefix="wbsem-test-"))
        self.repo = self.tmp / "repo"
        self.arch = self.tmp / "archive"
        pkg = self.repo / "4-打分细则" / "WB漂移token值语义-2026-11-16"
        pkg.mkdir(parents=True)
        shutil.copyfile(PKG / "README.md", pkg / "README.md")
        texts_by_case = {}
        for case in CASES:
            texts_by_case[case] = {
                rep: build_text(scenario[case][rep]["token"],
                                str(i + 1), marker=marker)
                for i, rep in enumerate(REPS)
            }
        for case in CASES:
            for rep in REPS:
                spec = scenario[case][rep]
                day, hh, mm = spec["first"]
                write_slot(self.arch / "runs", "%s__%s" % (case, rep),
                           texts_by_case[case][rep], epoch_ms(day, hh, mm))
        ref11, ref15 = build_refs(texts_by_case)
        d11 = self.repo / "4-打分细则" / "WB漂移字节位置结构-2026-11-16"
        d15 = self.repo / "4-打分细则" / "WB漂移token形状-2026-11-16"
        d11.mkdir(parents=True)
        d15.mkdir(parents=True)
        (d11 / "result.json").write_bytes(
            json.dumps(ref11, sort_keys=True, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
        (d15 / "result.json").write_bytes(
            json.dumps(ref15, sort_keys=True, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")

    def cleanup(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


def run_cli(repo, arch, output=None):
    cmd = [sys.executable, str(VERIFY_PATH),
           "--root", str(repo), "--archive-root", str(arch)]
    if output is not None:
        cmd += ["--output", str(output)]
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          env=env, timeout=180)
    return (proc.returncode,
            proc.stdout.decode("utf-8"),
            proc.stderr.decode("utf-8"))


# ---------------------------------------------------------------------------
# 测试基类
# ---------------------------------------------------------------------------

class VerifyTestBase(unittest.TestCase):

    def make_env(self, scenario_name, marker=None):
        env = Env(SCENARIOS[scenario_name], marker=marker)
        self.addCleanup(env.cleanup)
        return env

    def run_ok(self, env, out_path=None):
        """跑 CLI 并断言 exit 0 / stderr 空，返回 (stdout, result dict|None)。"""
        code, so, se = run_cli(env.repo, env.arch, output=out_path)
        self.assertEqual(se, "", "stderr 应为空: %s" % se)
        self.assertEqual(code, 0, "exit 应为 0: %s" % so)
        result = None
        if out_path is not None:
            result = json.loads(out_path.read_bytes().decode("utf-8"))
        return so, result

    def run_fail(self, env, out_path=None):
        """跑 CLI 并断言 exit 2（fail-closed）。"""
        code, so, se = run_cli(env.repo, env.arch, output=out_path)
        self.assertEqual(code, 2, "exit 应为 2（fail-closed）: %s" % so)
        return so, se


# ---------------------------------------------------------------------------
# §3 分支与值面语义（合成档案）
# ---------------------------------------------------------------------------

class ScenarioTests(VerifyTestBase):

    def test_clock_confirmed_branch(self):
        env = self.make_env("clock")
        out = env.tmp / "r.json"
        so, result = self.run_ok(env, out_path=out)
        self.assertIn("branch=B-CLOCK-CONFIRMED v1=true v2=true", so)
        self.assertIn("clock_class=证实", so)
        self.assertEqual(result["branch"]["verdict"], "B-CLOCK-CONFIRMED")
        self.assertTrue(result["v1"]["pass"])
        self.assertTrue(result["v2"]["pass"])
        self.assertEqual(result["v1"]["regex_match_count"], "6/6")
        self.assertEqual(result["v2"]["evaluable_count"], "6/6")
        for case in CASES:
            for rep in REPS:
                row = result["v2"]["matrix"][case][rep]
                self.assertEqual(row["delta_minutes_signed"], 0)
                self.assertTrue(row["main_pass_abs_le_1min"])
        self.assertEqual(result["exit_code"], 0)

    def test_counter_v1pass_v2break_branch(self):
        env = self.make_env("counter_v1pass")
        out = env.tmp / "r.json"
        so, result = self.run_ok(env, out_path=out)
        self.assertIn("branch=B-COUNTER-OTHER v1=true v2=false", so)
        self.assertIn("clock_class=否证", so)
        self.assertEqual(result["branch"]["verdict"], "B-COUNTER-OTHER")
        self.assertTrue(result["v1"]["pass"])
        self.assertFalse(result["v2"]["pass"])
        expect = {
            "dabstep-payments-10": [-540, 126, 792],
            "tb-cargo-plan": [470, 1026, 1217],
        }
        for case in CASES:
            for i, rep in enumerate(REPS):
                row = result["v2"]["matrix"][case][rep]
                self.assertEqual(row["delta_minutes_signed"], expect[case][i])
                self.assertFalse(row["main_pass_abs_le_1min"])
        self.assertEqual(result["exit_code"], 0)

    def test_counter_v1break_fixed_format_branch(self):
        env = self.make_env("counter_v1break")
        out = env.tmp / "r.json"
        so, result = self.run_ok(env, out_path=out)
        self.assertIn("branch=B-COUNTER-OTHER v1=false", so)
        self.assertEqual(result["branch"]["verdict"], "B-COUNTER-OTHER")
        self.assertFalse(result["v1"]["pass"])
        self.assertEqual(result["v1"]["regex_match_count"], "5/6")
        self.assertTrue(result["v1"]["separator_all_same"])
        fmt = result["format_registration"]
        self.assertTrue(fmt["fixed_format"])
        self.assertEqual(fmt["token_len_set"], [5])
        self.assertEqual(fmt["class_pattern_signature"], "DD?DD")
        row = result["v2"]["matrix"]["dabstep-payments-10"]["r3"]
        self.assertEqual(row["token"], "25:55")
        self.assertFalse(row["v2_evaluable"])
        self.assertIsNone(row["delta_minutes_signed"])
        self.assertEqual(result["v2"]["evaluable_count"], "5/6")
        self.assertEqual(result["exit_code"], 0)

    def test_indeterminate_fail_closed_exit2(self):
        # 合成档案下 §3 else 分支的可达路径：格式变异必然先破坏冻结结构
        # （分隔字节 '.' → c95 成为漂移位 → 信封内孤立位数=3≠2）⇒ fail-closed exit 2。
        env = self.make_env("indeterminate")
        so, _se = self.run_fail(env)
        self.assertIn("FAIL", so)
        self.assertIn("exit=2", so)
        self.assertIn("信封内孤立位数", so)

    def test_midnight_circular_delta_registration(self):
        env = self.make_env("midnight")
        out = env.tmp / "r.json"
        so, result = self.run_ok(env, out_path=out)
        self.assertIn("branch=B-COUNTER-OTHER", so)
        row = result["v2"]["matrix"]["dabstep-payments-10"]["r1"]
        self.assertEqual(row["token"], "00:10")
        self.assertEqual(row["first_ts_hhmm"], "23:59")
        self.assertEqual(row["delta_minutes_signed"], -1429)
        self.assertEqual(row["delta_minutes_abs"], 1429)
        self.assertEqual(row["delta_minutes_circular"], 11)
        self.assertFalse(row["main_pass_abs_le_1min"])
        self.assertFalse(row["direction_window_pass"])
        self.assertFalse(result["v2"]["pass"])
        self.assertEqual(result["exit_code"], 0)


# ---------------------------------------------------------------------------
# CLI / 封印 / 硬等防篡改守卫
# ---------------------------------------------------------------------------

class CliGuardTests(VerifyTestBase):

    def test_two_runs_stdout_identical(self):
        env = self.make_env("clock")
        so1, _ = self.run_ok(env)
        so2, _ = self.run_ok(env)
        self.assertEqual(so1, so2)

    def test_output_bytes_deterministic(self):
        env = self.make_env("counter_v1break")
        o1, o2 = env.tmp / "a.json", env.tmp / "b.json"
        self.run_ok(env, out_path=o1)
        self.run_ok(env, out_path=o2)
        self.assertEqual(o1.read_bytes(), o2.read_bytes())

    def test_output_refuses_overwrite(self):
        env = self.make_env("clock")
        out = env.tmp / "exists.json"
        out.write_bytes(b"KEEP")
        so, _se = self.run_fail(env, out_path=out)
        self.assertIn("拒绝覆盖", so)
        self.assertEqual(out.read_bytes(), b"KEEP", "已存在文件不得被改动")

    def test_readme_tamper_exit2(self):
        env = self.make_env("clock")
        readme = (env.repo / "4-打分细则" / "WB漂移token值语义-2026-11-16" / "README.md")
        readme.write_bytes(readme.read_bytes() + b"\n")
        so, _se = self.run_fail(env)
        self.assertIn("FAIL", so)

    def test_offsets_reference_tamper_exit2(self):
        env = self.make_env("clock")
        ref = env.repo / "4-打分细则" / "WB漂移字节位置结构-2026-11-16" / "result.json"
        obj = json.loads(ref.read_bytes().decode("utf-8"))
        ev0 = obj["case_analysis"]["dabstep-payments-10"]["events"][0]
        ev0["positions_offset"][0] += 1
        ref.write_bytes(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                                   indent=2).encode("utf-8") + b"\n")
        so, _se = self.run_fail(env)
        self.assertIn("漂移 offsets 硬等失败", so)

    def test_run_boundary_reference_tamper_exit2(self):
        env = self.make_env("clock")
        ref = env.repo / "4-打分细则" / "WB漂移token形状-2026-11-16" / "result.json"
        obj = json.loads(ref.read_bytes().decode("utf-8"))
        ent0 = obj["run_registration"]["cases"]["dabstep-payments-10"][0]
        rep0 = next(iter(ent0["by_rep"]))
        ent0["by_rep"][rep0]["run_end"] += 1
        ref.write_bytes(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                                   indent=2).encode("utf-8") + b"\n")
        so, _se = self.run_fail(env)
        self.assertIn("run 边界硬等失败", so)

    def test_missing_runs_dir_exit2(self):
        env = self.make_env("clock")
        shutil.rmtree(env.arch / "runs")
        so, _se = self.run_fail(env)
        self.assertIn("runs/", so)

    def test_two_session_jsonl_exit2(self):
        env = self.make_env("clock")
        tdir = env.arch / "runs" / ("dabstep-payments-10__r1") / "trace"
        (tdir / "extra.jsonl").write_bytes(b"\n")
        so, _se = self.run_fail(env)
        self.assertIn("应为 1", so)

    def test_two_user_messages_exit2(self):
        env = self.make_env("clock")
        path = env.arch / "runs" / "dabstep-payments-10__r1" / "trace" / "session.jsonl"
        extra = json.dumps({"type": "message", "role": "user",
                            "timestamp": epoch_ms(9, 12, 0),
                            "content": [{"type": "input_text", "text": "second"}]}) + "\n"
        path.write_bytes(path.read_bytes() + extra.encode("utf-8"))
        so, _se = self.run_fail(env)
        self.assertIn("role=user", so)

    def test_missing_timestamp_exit2(self):
        env = self.make_env("clock")
        path = env.arch / "runs" / "dabstep-payments-10__r1" / "trace" / "session.jsonl"
        lines = path.read_bytes().decode("utf-8").splitlines()
        obj = json.loads(lines[1])
        del obj["timestamp"]
        lines[1] = json.dumps(obj, ensure_ascii=True)
        path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
        so, _se = self.run_fail(env)
        self.assertIn("timestamp", so)

    def test_first_message_not_user_exit2(self):
        env = self.make_env("clock")
        path = env.arch / "runs" / "tb-cargo-plan__r2" / "trace" / "session.jsonl"
        lines = path.read_bytes().decode("utf-8").splitlines()
        # 槽 tb-cargo-plan__r2 首消息 = 19:06（SCN_CLOCK）；user 移到末位并给 +3min 时间戳，
        # 使时间戳保持单调不减，从而 fail 点落在「首消息 role 非 user」。
        user = json.loads(lines[0])
        user["timestamp"] = epoch_ms(9, 19, 9)
        new_lines = [lines[1], lines[2], json.dumps(user, ensure_ascii=True)]
        path.write_bytes(("\n".join(new_lines) + "\n").encode("utf-8"))
        so, _se = self.run_fail(env)
        self.assertIn("首消息 role 非 user", so)

    def test_timezone_mismatch_exit2(self):
        env = self.make_env("clock")
        meta = env.arch / "runs" / "tb-cargo-plan__r3" / "trace" / "collect-meta.json"
        meta.write_bytes(json.dumps(
            {"collected_at": "2026-11-09T09:00:00+05:30"}, sort_keys=True).encode("utf-8") + b"\n")
        so, _se = self.run_fail(env)
        self.assertIn("偏移不一致", so)

    def test_no_task_body_leak(self):
        env = self.make_env("clock", marker="MARKERSECRET")
        out = env.tmp / "r.json"
        so, _result = self.run_ok(env, out_path=out)
        payload = out.read_bytes().decode("utf-8")
        self.assertNotIn("MARKERSECRET", so)
        self.assertNotIn("MARKERSECRET", payload)
        self.assertNotIn("assistant", payload)

    def test_published_timestamps_minute_precision_and_no_date(self):
        env = self.make_env("clock")
        out = env.tmp / "r.json"
        self.run_ok(env, out_path=out)
        payload = out.read_bytes().decode("utf-8")
        result = json.loads(payload)
        per_slot = result["timestamp_semantics"]["per_slot"]
        self.assertEqual(len(per_slot), 6)
        for slot in SLOTS:
            self.assertRegex(per_slot[slot]["first_ts_hhmm"], HHMM_RE)
            self.assertRegex(per_slot[slot]["last_ts_hhmm"], HHMM_RE)
        # 值发布边界：日期不发布、collected_at 原串不出现、无秒级时刻串
        self.assertNotIn("2026-11-09", payload)
        self.assertNotIn(COLLECTED_AT, payload)
        self.assertIsNone(re.search(r"\d{2}:\d{2}:\d{2}", payload))


# ---------------------------------------------------------------------------
# 真档案端到端（env WB_TOKEN_SEM_ARCHIVE_ROOT="root1:root2" 双根门控）
# ---------------------------------------------------------------------------

class RealArchiveTests(unittest.TestCase):

    def _roots(self):
        raw = os.environ.get(ENV_VAR)
        if not raw:
            self.fail(
                "%s 未设置：真档案端到端用例被响亮 FAIL。"
                "应设为 'root1<%s>root2' 形式（os.pathsep 分隔的两个独立档案根副本）"
                % (ENV_VAR, os.pathsep))
        parts = [p for p in raw.split(os.pathsep) if p]
        if len(parts) != 2:
            self.fail("%s 应含恰 2 个根（%s 分隔），实得 %d 个"
                      % (ENV_VAR, os.pathsep, len(parts)))
        roots = [Path(p) for p in parts]
        for r in roots:
            if not (r / "runs").is_dir():
                self.fail("真档案根下无 runs/: %s" % r)
        return roots

    def test_real_archive_dual_roots_byte_identical(self):
        roots = self._roots()
        tmp = Path(tempfile.mkdtemp(prefix="wbsem-real-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        stdouts, outs = [], []
        for i, root in enumerate(roots):
            out = tmp / ("result-%d.json" % i)
            code, so, se = run_cli(REPO_ROOT, root, output=out)
            self.assertEqual(se, "", "stderr 应为空: %s" % se)
            self.assertEqual(code, 0, "真档案 exit 应为 0: %s" % so)
            stdouts.append(so)
            outs.append(out.read_bytes())
        self.assertEqual(stdouts[0], stdouts[1], "双档 stdout 应逐字节一致")
        self.assertEqual(outs[0], outs[1], "双档 result.json 应逐字节一致")
        if not STORED_RESULT.is_file():
            self.fail("包内 result.json 缺失（应由 --output 生成后入库）")
        self.assertEqual(outs[0], STORED_RESULT.read_bytes(), "fresh 应与 stored 逐字节一致")
        obj = json.loads(outs[0].decode("utf-8"))
        self.assertEqual(obj["schema"], "wb-token-sem-v1")
        self.assertEqual(obj["exit_code"], 0)
        self.assertIn(obj["branch"]["verdict"],
                      ("B-CLOCK-CONFIRMED", "B-COUNTER-OTHER"))
        self.assertTrue(obj["hard_equal"]["offsets"]["all_equal"])
        self.assertTrue(obj["hard_equal"]["run_boundaries"]["all_equal"])

    def test_real_archive_result_values_and_boundary(self):
        roots = self._roots()
        tmp = Path(tempfile.mkdtemp(prefix="wbsem-real-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        out = tmp / "real.json"
        code, so, _se = run_cli(REPO_ROOT, roots[0], output=out)
        self.assertEqual(code, 0, so)
        payload = out.read_bytes().decode("utf-8")
        obj = json.loads(payload)
        # token 值面：6 token 恰 5 字节、分隔字节全体同一
        seps = set()
        for case in CASES:
            reps = obj["tokens"]["cases"][case]["by_rep"]
            for rep in REPS:
                tok = reps[rep]["token"]
                self.assertEqual(len(tok), 5)
                tok.encode("ascii")
                seps.add(reps[rep]["separator"]["value"])
        self.assertEqual(len(seps), 1)
        # V3：6 处孤立位登记
        self.assertEqual(obj["v3"]["n_positions"], 6)
        # 时间戳：字段名/格式登记 + 6 槽首消息 role=user、HH:MM 分钟精度
        ts = obj["timestamp_semantics"]
        self.assertEqual(ts["field_name"], "timestamp")
        for slot in SLOTS:
            row = ts["per_slot"][slot]
            self.assertEqual(row["first_message_role"], "user")
            self.assertRegex(row["first_ts_hhmm"], HHMM_RE)
            self.assertRegex(row["last_ts_hhmm"], HHMM_RE)
        # baseline_commit 与当前仓库 HEAD 一致（同根双档）
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=30).stdout.decode("utf-8").strip()
        self.assertEqual(obj["baseline_commit"], head)
        # 值发布边界：无私有绝对路径、无消息面日期/秒级时刻串
        # （先剔除包名/参照路径标签中的包日期 2026-11-16，其非消息面发布物）
        self.assertNotIn("/Users/", payload)
        self.assertNotIn("bench-private", payload)
        scrubbed = payload.replace("2026-11-16", "")
        self.assertIsNone(re.search(r"\d{4}-\d{2}-\d{2}", scrubbed))
        self.assertIsNone(re.search(r"\d{2}:\d{2}:\d{2}", payload))
        self.assertNotIn("assistant", payload)


if __name__ == "__main__":
    unittest.main()
