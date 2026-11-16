#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WB漂移token毫秒钟确认-2026-11-16：verify.py 测试套件。

双档设计（与 loop15/17 惯例一致）：
- 合成档案：临时目录组装 repo（复制真 README 保封印 + 由测试内独立复算生成
  环 11/环 15 合成参照 result.json）+ archive（6 槽 trace jsonl +
  collect-meta.json），覆盖全部 §3 分支与 CLI 防篡改守卫；
- 真档案端到端：env WB_TOKEN_CLOCK_ARCHIVE_ROOT="root1:root2"（os.pathsep 分隔
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
ENV_VAR = "WB_TOKEN_CLOCK_ARCHIVE_ROOT"

# 冻结 W1 信封标记（环 6/11/15/17 同一；与 verify.py 常量独立字面，漂移即测试失败）
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

MMSS_RE = re.compile(r"^([0-5]\d):([0-5]\d)$")
HHMMSS_RE = re.compile(r"^\d{2}:\d{2}:\d{2}$")
# 环 17 旧正则（本包判据明确区别于它：合法 mm:ss 如 25:55/59:59 旧正则误判非法）
OLD_ROUND17_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


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
# first=(hh, mm, ss) 为该槽首消息墙钟（epoch 毫秒，UTC+08）；token=「分:秒」。
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


# 与真档案同构的确认场景（含 25:55；Δ=0/+1/0 两组，呼应任务预期事实）。
# 约束：每个 token 数字位跨 rep 至少一对相异（否则该漂移位退出并集、破坏 DD?DD 簇结构）。
SCN_CONFIRMED = scn(
    ["03:24", "08:19", "12:46"], [(12, 3, 24), (12, 8, 18), (12, 12, 46)],
    ["16:04", "21:23", "25:55"], [(12, 16, 4), (12, 21, 22), (12, 25, 55)],
)
# 期望：V1′/V2′/V3′ 全过（Δ=0,+1,0 / 0,+1,0）→ B-MMSS-CONFIRMED-POSTHOC

# 59:59 过 V1′；分钟=59、秒=59 边界字段
SCN_5959 = scn(
    ["59:59", "00:00", "30:30"], [(12, 59, 59), (12, 0, 0), (12, 30, 30)],
    ["45:45", "05:05", "59:00"], [(12, 45, 45), (12, 5, 5), (12, 59, 0)],
)
# 期望：全过 → B-MMSS-CONFIRMED-POSTHOC

# ±1s 边界：0 过、+1 过、−1 过（边界归属逐处登记）
SCN_BOUNDARY = scn(
    ["03:20", "15:11", "28:58"], [(12, 3, 20), (12, 15, 10), (12, 28, 59)],
    ["34:07", "46:18", "50:39"], [(12, 34, 7), (12, 46, 17), (12, 50, 40)],
)
# 期望：Δ=0/+1/−1 两组全 |Δ|≤1s → CONFIRMED；归属 exact_0s/boundary_+1s/boundary_-1s

# +2 拒（恰 1 处破）→ V2′ 5/6 → B-MMSS-PARTIAL（V1′ 仍全过）
SCN_PARTIAL = scn(
    ["03:20", "15:11", "28:05"], [(12, 3, 20), (12, 15, 10), (12, 28, 3)],
    ["34:07", "46:18", "50:39"], [(12, 34, 7), (12, 46, 18), (12, 50, 39)],
)
# 期望：仅 dab r3 Δ=+2 破（其余 5 处 |Δ|≤1s）→ V2′ 5/6 → B-MMSS-PARTIAL、exit 0

# 60:00 拒（分字段 >59，旧/新正则皆拒）→ V1′ 5/6 → B-MMSS-REFUTED / exit2
SCN_REJECT_60 = scn(
    ["60:00", "03:20", "28:58"], [(12, 10, 0), (12, 3, 20), (12, 28, 58)],
    ["34:07", "46:18", "50:39"], [(12, 34, 7), (12, 46, 18), (12, 50, 39)],
)

# 99:99 拒（两字段 >59）→ V1′ 5/6 → B-MMSS-REFUTED / exit2
SCN_REJECT_99 = scn(
    ["99:99", "03:20", "28:58"], [(12, 10, 0), (12, 3, 20), (12, 28, 58)],
    ["34:07", "46:18", "50:39"], [(12, 34, 7), (12, 46, 18), (12, 50, 39)],
)

SCENARIOS = {
    "confirmed": SCN_CONFIRMED,
    "s5959": SCN_5959,
    "boundary": SCN_BOUNDARY,
    "partial": SCN_PARTIAL,
    "reject60": SCN_REJECT_60,
    "reject99": SCN_REJECT_99,
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
        self.tmp = Path(tempfile.mkdtemp(prefix="wbclock-test-"))
        self.repo = self.tmp / "repo"
        self.arch = self.tmp / "archive"
        pkg = self.repo / "4-打分细则" / "WB漂移token毫秒钟确认-2026-11-16"
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
                hh, mm, ss = spec["first"]
                write_slot(self.arch / "runs", "%s__%s" % (case, rep),
                           texts_by_case[case][rep], epoch_ms(9, hh, mm, ss))
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
        """跑 CLI 并断言 exit 2（fail-closed 或 REFUTED）。"""
        code, so, se = run_cli(env.repo, env.arch, output=out_path)
        self.assertEqual(code, 2, "exit 应为 2: %s" % so)
        return so, se


# ---------------------------------------------------------------------------
# §3 分支与值面语义（合成档案）
# ---------------------------------------------------------------------------

class ScenarioTests(VerifyTestBase):

    def test_confirmed_branch_and_values(self):
        env = self.make_env("confirmed")
        out = env.tmp / "r.json"
        so, result = self.run_ok(env, out_path=out)
        self.assertIn("branch=B-MMSS-CONFIRMED-POSTHOC v1p=true v2p=true(6/6) v3p=true", so)
        self.assertEqual(result["branch"]["verdict"], "B-MMSS-CONFIRMED-POSTHOC")
        self.assertTrue(result["v1_prime"]["pass"])
        self.assertTrue(result["v2_prime"]["pass"])
        self.assertTrue(result["v3_prime"]["pass"])
        self.assertEqual(result["v1_prime"]["regex_match_count"], "6/6")
        self.assertEqual(result["v2_prime"]["evaluable_count"], "6/6")
        self.assertEqual(result["v2_prime"]["pass_count"], "6/6")
        self.assertEqual(result["v3_prime"]["match_count"], "6/6")
        self.assertEqual(result["v2_prime"]["delta_seconds_matrix"], {
            "dabstep-payments-10": [0, 1, 0],
            "tb-cargo-plan": [0, 1, 0],
        })
        for case in CASES:
            for rep in REPS:
                row = result["v2_prime"]["matrix"][case][rep]
                self.assertTrue(row["pass_abs_le_1s"])
                self.assertLessEqual(row["delta_seconds_abs"], 1)
        self.assertEqual(result["exit_code"], 0)

    def test_25_55_passes_v1_prime_distinct_from_round17_regex(self):
        # 25:55=25分55秒 是合法 mm:ss；环 17 旧正则会把它误判非法（本包必须收口此点）
        self.assertIsNone(OLD_ROUND17_RE.match("25:55"),
                          "环 17 旧正则应当拒绝 25:55（对照前提）")
        self.assertIsNotNone(MMSS_RE.match("25:55"), "V1′ 应当接受 25:55")
        env = self.make_env("confirmed")
        out = env.tmp / "r.json"
        so, result = self.run_ok(env, out_path=out)
        row = result["v2_prime"]["matrix"]["tb-cargo-plan"]["r3"]
        self.assertEqual(row["token"], "25:55")
        v1_row = [x for x in result["v1_prime"]["per_token"]
                  if x["case"] == "tb-cargo-plan" and x["rep"] == "r3"][0]
        self.assertTrue(v1_row["regex_match"])
        self.assertEqual(v1_row["regex_pattern"], "^([0-5]\\d):([0-5]\\d)$")
        self.assertIn("V1p=true match=6/6", so)
        self.assertIn("branch=B-MMSS-CONFIRMED-POSTHOC", so)
        self.assertEqual(row["delta_seconds_signed"], 0)
        self.assertEqual(row["first_ts_hhmmss"], "12:25:55")

    def test_5959_passes_v1_prime(self):
        env = self.make_env("s5959")
        out = env.tmp / "r.json"
        so, result = self.run_ok(env, out_path=out)
        self.assertIn("branch=B-MMSS-CONFIRMED-POSTHOC", so)
        row = result["v2_prime"]["matrix"]["dabstep-payments-10"]["r1"]
        self.assertEqual(row["token"], "59:59")
        self.assertEqual(row["delta_seconds_signed"], 0)
        self.assertEqual(row["token_seconds_of_hour"], 59 * 60 + 59)
        self.assertEqual(result["v1_prime"]["regex_match_count"], "6/6")
        self.assertEqual(result["exit_code"], 0)

    def test_boundary_pm1_all_pass_with_attribution(self):
        env = self.make_env("boundary")
        out = env.tmp / "r.json"
        so, result = self.run_ok(env, out_path=out)
        self.assertIn("branch=B-MMSS-CONFIRMED-POSTHOC", so)
        m = result["v2_prime"]["matrix"]
        self.assertEqual(m["dabstep-payments-10"]["r1"]["boundary_attribution"], "exact_0s")
        self.assertEqual(m["dabstep-payments-10"]["r2"]["boundary_attribution"], "boundary_+1s")
        self.assertEqual(m["dabstep-payments-10"]["r3"]["boundary_attribution"], "boundary_-1s")
        self.assertEqual(m["tb-cargo-plan"]["r1"]["boundary_attribution"], "exact_0s")
        self.assertEqual(m["tb-cargo-plan"]["r2"]["boundary_attribution"], "boundary_+1s")
        self.assertEqual(m["tb-cargo-plan"]["r3"]["boundary_attribution"], "boundary_-1s")
        self.assertEqual(result["v2_prime"]["delta_seconds_matrix"], {
            "dabstep-payments-10": [0, 1, -1],
            "tb-cargo-plan": [0, 1, -1],
        })
        self.assertEqual(result["exit_code"], 0)

    def test_partial_branch_delta_plus2(self):
        env = self.make_env("partial")
        out = env.tmp / "r.json"
        so, result = self.run_ok(env, out_path=out)
        self.assertIn("branch=B-MMSS-PARTIAL v1p=true v2p=false(5/6)", so)
        b = result["branch"]
        self.assertEqual(b["verdict"], "B-MMSS-PARTIAL")
        self.assertTrue(b["V1_prime_pass"])
        self.assertFalse(b["V2_prime_pass"])
        self.assertEqual(b["V2_prime_pass_count"], "5/6")
        row = result["v2_prime"]["matrix"]["dabstep-payments-10"]["r3"]
        self.assertEqual(row["token"], "28:05")
        self.assertEqual(row["delta_seconds_signed"], 2)
        self.assertFalse(row["pass_abs_le_1s"])
        self.assertEqual(row["boundary_attribution"], "outside_±1s")
        self.assertEqual(result["v2_prime"]["pass_count"], "5/6")
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("V2p=false evaluable=6/6 pass(|d|<=1s)=5/6", so)

    def test_reject_60_00_refuted_exit2(self):
        env = self.make_env("reject60")
        out = env.tmp / "r.json"
        so, _se = self.run_fail(env, out_path=out)
        self.assertIn("branch=B-MMSS-REFUTED v1p=false", so)
        self.assertIn("exit=2", so)
        result = json.loads(out.read_bytes().decode("utf-8"))
        self.assertEqual(result["branch"]["verdict"], "B-MMSS-REFUTED")
        self.assertEqual(result["branch"]["exit_code"], 2)
        self.assertEqual(result["v1_prime"]["regex_match_count"], "5/6")
        row = result["v2_prime"]["matrix"]["dabstep-payments-10"]["r1"]
        self.assertEqual(row["token"], "60:00")
        self.assertFalse(row["v2_evaluable"])
        self.assertIsNone(row["delta_seconds_signed"])

    def test_reject_99_99_refuted_exit2(self):
        env = self.make_env("reject99")
        out = env.tmp / "r.json"
        so, _se = self.run_fail(env, out_path=out)
        self.assertIn("branch=B-MMSS-REFUTED", so)
        self.assertIn("exit=2", so)
        result = json.loads(out.read_bytes().decode("utf-8"))
        self.assertEqual(result["branch"]["verdict"], "B-MMSS-REFUTED")
        self.assertEqual(result["v1_prime"]["regex_match_count"], "5/6")
        row = result["v2_prime"]["matrix"]["dabstep-payments-10"]["r1"]
        self.assertEqual(row["token"], "99:99")
        self.assertFalse(row["v2_evaluable"])


# ---------------------------------------------------------------------------
# CLI / 封印 / 硬等防篡改守卫
# ---------------------------------------------------------------------------

class CliGuardTests(VerifyTestBase):

    def test_two_runs_stdout_identical(self):
        env = self.make_env("confirmed")
        so1, _ = self.run_ok(env)
        so2, _ = self.run_ok(env)
        self.assertEqual(so1, so2)

    def test_output_bytes_deterministic(self):
        env = self.make_env("boundary")
        o1, o2 = env.tmp / "a.json", env.tmp / "b.json"
        self.run_ok(env, out_path=o1)
        self.run_ok(env, out_path=o2)
        self.assertEqual(o1.read_bytes(), o2.read_bytes())

    def test_output_refuses_overwrite(self):
        env = self.make_env("confirmed")
        out = env.tmp / "exists.json"
        out.write_bytes(b"KEEP")
        so, _se = self.run_fail(env, out_path=out)
        self.assertIn("拒绝覆盖", so)
        self.assertEqual(out.read_bytes(), b"KEEP", "已存在文件不得被改动")

    def test_readme_tamper_exit2(self):
        env = self.make_env("confirmed")
        readme = (env.repo / "4-打分细则" / "WB漂移token毫秒钟确认-2026-11-16" / "README.md")
        readme.write_bytes(readme.read_bytes() + b"\n")
        so, _se = self.run_fail(env)
        self.assertIn("FAIL", so)
        self.assertIn("SHA256 不符", so)

    def test_offsets_reference_tamper_exit2(self):
        env = self.make_env("confirmed")
        ref = env.repo / "4-打分细则" / "WB漂移字节位置结构-2026-11-16" / "result.json"
        obj = json.loads(ref.read_bytes().decode("utf-8"))
        ev0 = obj["case_analysis"]["dabstep-payments-10"]["events"][0]
        ev0["positions_offset"][0] += 1
        ref.write_bytes(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                                   indent=2).encode("utf-8") + b"\n")
        so, _se = self.run_fail(env)
        self.assertIn("漂移 offsets 硬等失败", so)

    def test_run_boundary_reference_tamper_exit2(self):
        env = self.make_env("confirmed")
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
        env = self.make_env("confirmed")
        shutil.rmtree(env.arch / "runs")
        so, _se = self.run_fail(env)
        self.assertIn("runs/", so)

    def test_two_session_jsonl_exit2(self):
        env = self.make_env("confirmed")
        tdir = env.arch / "runs" / ("dabstep-payments-10__r1") / "trace"
        (tdir / "extra.jsonl").write_bytes(b"\n")
        so, _se = self.run_fail(env)
        self.assertIn("应为 1", so)

    def test_two_user_messages_exit2(self):
        env = self.make_env("confirmed")
        path = env.arch / "runs" / "dabstep-payments-10__r1" / "trace" / "session.jsonl"
        extra = json.dumps({"type": "message", "role": "user",
                            "timestamp": epoch_ms(9, 12, 20),
                            "content": [{"type": "input_text", "text": "second"}]}) + "\n"
        path.write_bytes(path.read_bytes() + extra.encode("utf-8"))
        so, _se = self.run_fail(env)
        self.assertIn("role=user", so)

    def test_missing_timestamp_exit2(self):
        env = self.make_env("confirmed")
        path = env.arch / "runs" / "dabstep-payments-10__r1" / "trace" / "session.jsonl"
        lines = path.read_bytes().decode("utf-8").splitlines()
        obj = json.loads(lines[1])
        del obj["timestamp"]
        lines[1] = json.dumps(obj, ensure_ascii=True)
        path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
        so, _se = self.run_fail(env)
        self.assertIn("timestamp", so)

    def test_first_message_not_user_exit2(self):
        env = self.make_env("confirmed")
        path = env.arch / "runs" / "tb-cargo-plan__r2" / "trace" / "session.jsonl"
        lines = path.read_bytes().decode("utf-8").splitlines()
        # 槽 tb-cargo-plan__r2 首消息 = 12:21:22（SCN_CONFIRMED）；user 移到末位并给
        # 晚于保留 assistant（12:22:22/12:23:22）的时间戳，使 fail 点落在「首消息 role 非 user」。
        user = json.loads(lines[0])
        user["timestamp"] = epoch_ms(9, 12, 24, 0)
        new_lines = [lines[1], lines[2], json.dumps(user, ensure_ascii=True)]
        path.write_bytes(("\n".join(new_lines) + "\n").encode("utf-8"))
        so, _se = self.run_fail(env)
        self.assertIn("首消息 role 非 user", so)

    def test_timezone_mismatch_exit2(self):
        env = self.make_env("confirmed")
        meta = env.arch / "runs" / "tb-cargo-plan__r3" / "trace" / "collect-meta.json"
        meta.write_bytes(json.dumps(
            {"collected_at": "2026-11-09T09:00:00+05:30"}, sort_keys=True).encode("utf-8") + b"\n")
        so, _se = self.run_fail(env)
        self.assertIn("偏移不一致", so)

    def test_no_task_body_leak(self):
        env = self.make_env("confirmed", marker="MARKERSECRET")
        out = env.tmp / "r.json"
        so, _result = self.run_ok(env, out_path=out)
        payload = out.read_bytes().decode("utf-8")
        self.assertNotIn("MARKERSECRET", so)
        self.assertNotIn("MARKERSECRET", payload)
        self.assertNotIn("assistant", payload)

    def test_published_timestamps_second_precision_no_date_no_ms(self):
        env = self.make_env("confirmed")
        out = env.tmp / "r.json"
        self.run_ok(env, out_path=out)
        payload = out.read_bytes().decode("utf-8")
        result = json.loads(payload)
        per_slot = result["timestamp_semantics"]["per_slot"]
        self.assertEqual(len(per_slot), 6)
        for slot in SLOTS:
            self.assertRegex(per_slot[slot]["first_ts_hhmmss"], HHMMSS_RE)
            self.assertRegex(per_slot[slot]["last_ts_hhmmss"], HHMMSS_RE)
        # 值发布边界：日期不发布、collected_at 原串不出现、无毫秒级时刻串
        self.assertNotIn("2026-11-09", payload)
        self.assertNotIn(COLLECTED_AT, payload)
        self.assertIsNone(re.search(r"\d{2}:\d{2}:\d{2}\.\d", payload))
        scrubbed = payload.replace("2026-11-16", "")
        self.assertIsNone(re.search(r"\d{4}-\d{2}-\d{2}", scrubbed))

    def test_posthoc_declaration_present(self):
        env = self.make_env("confirmed")
        out = env.tmp / "r.json"
        so, result = self.run_ok(env, out_path=out)
        ph = result["post_hoc_declaration"]
        self.assertEqual(ph["hypothesis_source"], "环 17 Lead 验证期观察")
        self.assertFalse(ph["independent_prediction"])
        self.assertIn("事后确认", ph["evidence_grade"])
        self.assertTrue(ph["declared_in_prereg"])
        self.assertIn("posthoc_declared=true source=环 17 Lead 验证期观察", so)


# ---------------------------------------------------------------------------
# 真档案端到端（env WB_TOKEN_CLOCK_ARCHIVE_ROOT="root1:root2" 双根门控）
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
        tmp = Path(tempfile.mkdtemp(prefix="wbclock-real-"))
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
        self.assertEqual(obj["schema"], "wb-token-clock-v1")
        self.assertEqual(obj["exit_code"], 0)
        self.assertEqual(obj["branch"]["verdict"], "B-MMSS-CONFIRMED-POSTHOC")
        self.assertTrue(obj["hard_equal"]["offsets"]["all_equal"])
        self.assertTrue(obj["hard_equal"]["run_boundaries"]["all_equal"])

    def test_real_archive_result_values_and_boundary(self):
        roots = self._roots()
        tmp = Path(tempfile.mkdtemp(prefix="wbclock-real-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        out = tmp / "real.json"
        code, so, _se = run_cli(REPO_ROOT, roots[0], output=out)
        self.assertEqual(code, 0, so)
        payload = out.read_bytes().decode("utf-8")
        obj = json.loads(payload)
        # token 值面：6 token 恰 5 字节、分隔字节全体同一、预期值逐一相符
        EXPECT_TOKENS = {
            "dabstep-payments-10": ["03:24", "08:19", "12:46"],
            "tb-cargo-plan": ["16:04", "21:23", "25:55"],
        }
        seps = set()
        for case in CASES:
            reps = obj["tokens"]["cases"][case]["by_rep"]
            for i, rep in enumerate(REPS):
                tok = reps[rep]["token"]
                self.assertEqual(len(tok), 5)
                tok.encode("ascii")
                self.assertEqual(tok, EXPECT_TOKENS[case][i])
                seps.add(reps[rep]["separator"]["value"])
        self.assertEqual(len(seps), 1)
        # V1′/V2′/V3′ 全过；秒差矩阵与首消息时刻（HH:MM:SS）与预期事实逐一相符
        self.assertTrue(obj["v1_prime"]["pass"])
        self.assertEqual(obj["v1_prime"]["regex_match_count"], "6/6")
        self.assertTrue(obj["v2_prime"]["pass"])
        self.assertEqual(obj["v2_prime"]["delta_seconds_matrix"], {
            "dabstep-payments-10": [0, 1, 0],
            "tb-cargo-plan": [0, 1, 0],
        })
        self.assertTrue(obj["v3_prime"]["pass"])
        self.assertEqual(obj["v3_prime"]["match_count"], "6/6")
        EXPECT_FIRST = {
            "dabstep-payments-10__r1": "12:03:24",
            "dabstep-payments-10__r2": "12:08:18",
            "dabstep-payments-10__r3": "12:12:46",
            "tb-cargo-plan__r1": "12:16:04",
            "tb-cargo-plan__r2": "12:21:22",
            "tb-cargo-plan__r3": "12:25:55",
        }
        ts = obj["timestamp_semantics"]
        self.assertEqual(ts["field_name"], "timestamp")
        for slot in SLOTS:
            row = ts["per_slot"][slot]
            self.assertEqual(row["first_message_role"], "user")
            self.assertEqual(row["first_ts_hhmmss"], EXPECT_FIRST[slot])
            self.assertRegex(row["last_ts_hhmmss"], HHMMSS_RE)
        # posthoc 声明在档
        self.assertEqual(obj["post_hoc_declaration"]["hypothesis_source"],
                         "环 17 Lead 验证期观察")
        # baseline_commit 与当前仓库 HEAD 一致（同根双档）
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=30).stdout.decode("utf-8").strip()
        self.assertEqual(obj["baseline_commit"], head)
        # 值发布边界：无私有绝对路径、无消息面日期/毫秒级时刻串
        # （先剔除包名/参照路径标签中的包日期 2026-11-16，其非消息面发布物）
        self.assertNotIn("/Users/", payload)
        self.assertNotIn("bench-private", payload)
        scrubbed = payload.replace("2026-11-16", "")
        self.assertIsNone(re.search(r"\d{4}-\d{2}-\d{2}", scrubbed))
        self.assertIsNone(re.search(r"\d{2}:\d{2}:\d{2}\.\d", payload))
        self.assertNotIn("assistant", payload)


if __name__ == "__main__":
    unittest.main()
