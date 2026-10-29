#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L3 包B CLI 级机械自测（B4 / B6 / B7）：以子进程驱动 validate_runner_meta.py，
把关键行为固化为可复现回归；收据的哈希/时刻全部脚本生成。

用例：
  T1 C-1 复现 16:11:16 覆盖模式：--spec --out P 首次写入成功；同命令第二次运行必须
      失败（exit≠0）且 P 字节不变。（B6）
  T2 B4 默认 fail-closed：无 --seal-at 的 --spec，期望 pass 的 fixture 实得 fail:unsealed，
      整体 exit 1（非零）。
  T3 B4 opt-in 界限：--spec --allow-unsealed 拒绝（exit 2）；--retro --allow-unsealed
      出矩阵且 seal.policy=allow-unsealed-disclosure、unsealed=true（披露模式标记）。
  T4 B7 合成对账正例：registered_at == 封印时刻 → verdict ok（exit 0）。
  T5 B7 合成对账负例：registered_at 早于封印时刻 → verdict violation（exit 1）。
  T6 静态守护：原收据 spec-selftest-receipt.json 与 receipt-overwrite-evidence-20261029.json
      字节不动（记录全量 SHA-256 备查）。

用法：python3 -B cli-selftest-l3.py [--out cli-regression-receipt-l3-20261029.json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = "runner-schema-v2"
VALIDATOR = HERE / "validate_runner_meta.py"
FIXTURES = HERE / "fixtures"
DEFAULT_OUT = HERE / "cli-regression-receipt-l3-20261029.json"
COMMIT = "72edb519"
COMMIT_TIME = "2026-10-29T17:52:27+08:00"  # L3 封印提交时刻口径（lead 指令，脚本转写进 fixture）


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def run(args) -> dict:
    p = subprocess.run([sys.executable, "-B", str(VALIDATOR)] + args,
                       capture_output=True, text=True, timeout=300)
    return {"args": args, "exit": p.returncode,
            "stdout_tail": p.stdout[-400:], "stderr_tail": p.stderr[-300:]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    a = ap.parse_args()
    out_path = Path(a.out)
    tests = {}

    with tempfile.TemporaryDirectory(prefix="l3b-cli-") as td:
        tmp = Path(td)

        # T1 C-1（B6）：首写成功 → 二写拒绝且字节不变
        p1 = tmp / "c1-receipt.json"
        r1 = run(["--spec", "--fixtures", str(FIXTURES), "--out", str(p1)])
        first_sha = sha(p1) if p1.exists() else None
        r2 = run(["--spec", "--fixtures", str(FIXTURES), "--out", str(p1)])
        second_sha = sha(p1) if p1.exists() else None
        tests["T1_c1_overwrite_pattern"] = {
            "first_run_exit": r1["exit"], "second_run_exit": r2["exit"],
            "first_written": p1.exists(), "bytes_unchanged": first_sha == second_sha,
            "first_sha256": first_sha,
            "pass": r1["exit"] == 0 and r2["exit"] == 2 and first_sha == second_sha,
            "runs": [r1, r2]}

        # T2 B4：无 seal 默认非零 + fail:unsealed
        fx_noseal = tmp / "fixtures-noseal"
        shutil.copytree(FIXTURES, fx_noseal,
                        ignore=shutil.ignore_patterns("reconcile"))
        manifest = json.loads((fx_noseal / "manifest.json").read_text(encoding="utf-8"))
        manifest.pop("seal_at", None)
        (fx_noseal / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        p2 = tmp / "noseal-receipt.json"
        r3 = run(["--spec", "--fixtures", str(fx_noseal), "--out", str(p2)])
        unsealed = {}
        if p2.exists():
            d = json.loads(p2.read_text(encoding="utf-8"))
            unsealed = {k: v["got"] for k, v in d["results"].items() if "unsealed" in v["got"]}
        tests["T2_b4_default_failclosed"] = {
            "exit": r3["exit"], "unsealed_classifications": unsealed,
            "pass": r3["exit"] == 1 and "fixture-valid.json" in unsealed
                    and unsealed.get("fixture-valid.json") == "fail:unsealed",
            "run": r3}

        # T3 B4：opt-in 界限
        r4 = run(["--spec", "--allow-unsealed", "--fixtures", str(FIXTURES)])
        p3 = tmp / "retro-matrix-allow.json"
        r5 = run(["--retro", str(tmp / "retro-runs"), "--out", str(p3), "--allow-unsealed"])
        # 造一个单场 runs 目录供 --retro
        rd = tmp / "retro-runs" / "run-a"
        rd.mkdir(parents=True, exist_ok=True)
        shutil.copy2(FIXTURES / "fixture-valid.json", rd / "meta.json")
        r5 = run(["--retro", str(tmp / "retro-runs"), "--out", str(p3), "--allow-unsealed"])
        policy = None
        if p3.exists():
            policy = json.loads(p3.read_text(encoding="utf-8")).get("seal")
        tests["T3_b4_optin_scope"] = {
            "spec_allow_unsealed_exit": r4["exit"],
            "retro_allow_unsealed_exit": r5["exit"],
            "retro_seal_block": policy,
            "pass": r4["exit"] == 2 and r5["exit"] == 0 and bool(policy)
                    and policy.get("policy") == "allow-unsealed-disclosure"
                    and policy.get("unsealed") is True,
            "runs": [r4, r5]}

        # T4/T5 B7 合成对账
        p4 = tmp / "reconcile-ok.json"
        r6 = run(["--reconcile", "--ledger", str(FIXTURES / "reconcile" / "synthetic-ledger.json"),
                  "--pointer", "/registered_at", "--commit", COMMIT,
                  "--commit-time-file", str(FIXTURES / "reconcile" / "commit-time-72edb519.txt"),
                  "--out", str(p4)])
        verd_ok = json.loads(p4.read_text(encoding="utf-8"))["verdict"] if p4.exists() else None
        p5 = tmp / "reconcile-early.json"
        r7 = run(["--reconcile", "--ledger", str(FIXTURES / "reconcile" / "synthetic-ledger-early.json"),
                  "--pointer", "/registered_at", "--commit", COMMIT,
                  "--commit-time-file", str(FIXTURES / "reconcile" / "commit-time-72edb519.txt"),
                  "--out", str(p5)])
        verd_bad = json.loads(p5.read_text(encoding="utf-8"))["verdict"] if p5.exists() else None
        tests["T4_b7_reconcile_positive"] = {
            "exit": r6["exit"], "verdict": verd_ok,
            "pass": r6["exit"] == 0 and verd_ok == "ok", "run": r6}
        tests["T5_b7_reconcile_negative"] = {
            "exit": r7["exit"], "verdict": verd_bad,
            "pass": r7["exit"] == 1 and verd_bad == "violation", "run": r7}

    # T6 静态守护：原收据字节不动
    orig_receipt = HERE / "spec-selftest-receipt.json"
    orig_evidence = HERE / "receipt-overwrite-evidence-20261029.json"
    tests["T6_original_receipts_untouched"] = {
        "spec-selftest-receipt.json_sha256": sha(orig_receipt) if orig_receipt.exists() else None,
        "receipt-overwrite-evidence-20261029.json_sha256": sha(orig_evidence) if orig_evidence.exists() else None,
        "expected_prefixes": {"spec-selftest-receipt.json": "5c6177fd",
                               "receipt-overwrite-evidence-20261029.json": "22332412"},
        "pass": (orig_receipt.exists() and sha(orig_receipt).startswith("5c6177fd")
                 and orig_evidence.exists() and sha(orig_evidence).startswith("22332412"))}

    all_pass = all(t.get("pass") for t in tests.values())
    receipt = {"kind": "self_test", "tool": "cli-selftest-l3.py", "spec": SPEC,
               "at": now(), "validator_sha256": sha(VALIDATOR),
               "commit_under_test": COMMIT, "commit_time_under_test": COMMIT_TIME,
               "counts": {"total": len(tests),
                          "passed": sum(1 for t in tests.values() if t.get("pass")),
                          "failed": sum(1 for t in tests.values() if not t.get("pass"))},
               "tests": tests, "all_pass": all_pass}
    if out_path.exists():
        print(json.dumps({"refused": True, "target": str(out_path),
                          "reason": "目标已存在（C-1 同款纪律）"}, ensure_ascii=False))
        return 2
    out_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt["counts"], ensure_ascii=False))
    print("CLI_SELFTEST:", "PASS" if all_pass else "FAIL", "->", out_path.name)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
