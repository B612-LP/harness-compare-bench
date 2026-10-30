#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""判卷回归一键化：五题自测 + 关键审计收据存在性 / SHA-256 校验。

用法（仓库根目录执行，仅依赖 Python 3 标准库，不联网、不装包）：

    python3 4-打分细则/判卷回归/run_regression.py

流程：
  1) 五题自测：python3 2-用例/<case>/checker.py --selftest（bird-ca-schools-15 /
     dabstep-payments-10 / exercism-py-6 / lcb-recent-hard-4 / tb-cargo-plan），
     捕获退出码与输出尾部；退出码非 0 视为失败。
  2) 关键审计收据校验：对 判卷审计-2026-10-24（execution / numeric / lcb 三族）
     与 判卷审计-2026-10-26/bird-q26-并入/ 下各 README 声明的证据文件，
     以及审计 README 明示的现行判卷资产（checker / truth / inputs 等），
     逐条做存在性 + SHA-256 校验（清单见 SHA_MANIFEST）。
  3) 输出 markdown 汇总表并写 results.json（默认与本脚本同目录，可用 --output 改）；
     任何一项失败则进程退出码非 0（0=全部通过，1=存在失败，2=环境/参数错误）。

注意：SHA 快照日期 2026-10-27（2026-10-27 判卷器收紧批 B2/B8/B12/B14 后刷新 bird 与 cargo
checker 条目；B13 预检翻转未并入，收据见 判卷审计-2026-10-27/checker-tightening-B2-B8-B12-13-14/），
判卷资产变更时需刷新——即重算 SHA_MANIFEST 中对应条目的 SHA-256 并同步更新本注释、README 与收据。
审计 README 同时声明了新旧两版哈希（如 bird-q26 的 v1.1/v1.2 对照），本清单只固化「当前实际值」。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_DIR.parent.parent  # <repo>/4-打分细则/判卷回归 -> 仓库根

SHA_SNAPSHOT_DATE = "2026-10-27"
SHA_SNAPSHOT_NOTE = "SHA 快照日期 2026-10-27（收紧批 B2/B8/B12/B14 后刷新），判卷资产变更时需刷新（重算并更新 SHA_MANIFEST）"

SELFTEST_CASES = [
    "bird-ca-schools-15",
    "dabstep-payments-10",
    "exercism-py-6",
    "lcb-recent-hard-4",
    "tb-cargo-plan",
]

AUDIT_1024 = "4-打分细则/判卷审计-2026-10-24"
AUDIT_1026 = "4-打分细则/判卷审计-2026-10-26/bird-q26-并入"

# ---------------------------------------------------------------------------
# SHA 清单：判卷收据 + 现行判卷资产的「当前实际 SHA-256」固化快照。
# 来源：各审计目录 README 声明的证据文件（相对仓库根的 POSIX 路径）。
# 判卷资产变更时需刷新：重算对应条目并更新本清单、注释日期与 README。
# ---------------------------------------------------------------------------
SHA_MANIFEST: dict[str, dict[str, str]] = {
    f"{AUDIT_1024}（总 README）": {
        f"{AUDIT_1024}/README.md": "e052887dcc2e5d02807a1d70482955430cb74cced617f6ad49d5e6c2dca31035",
    },
    f"{AUDIT_1024}/execution（执行族）": {
        f"{AUDIT_1024}/execution/README.md": "e45f3e93b8f97fae06d4c88693173ff3c6a536ea9c4716213753d048fe7597a4",
        f"{AUDIT_1024}/execution/frozen-artifacts.json": "2b91a70325fb988f9340320871b60395bd8f1322bf41b3bbf6a5f4a83007ace3",
        f"{AUDIT_1024}/execution/before.json": "6e40c47b245e3e588c18e1bd28a21a2531fe250f336cc5b8a130e0e6451be748",
        f"{AUDIT_1024}/execution/before.log": "32750794901186ee0776a7df83fcca80a39fd47b4f652d89a0058f85e7d6ec3c",
        f"{AUDIT_1024}/execution/after.json": "bba419ea10704503026f5e4ef2a589de1a2d1e164791f307e7ef20d135299166",
        f"{AUDIT_1024}/execution/after.log": "9f3db002e8cd5aa9b9671844bde7f45c45eb1c32d8b675e5b98c3b9cf28b8f1a",
        f"{AUDIT_1024}/execution/before/exercism-py-6/checker.py": "49a48fe03ccf028dc385eec8fe5b73fa70357bd7a91f666aaea25dbcfe45ade8",
        f"{AUDIT_1024}/execution/before/exercism-py-6/spec.md": "bf0dc27c3d998510cebe963fe2d87be833ce85ffef973c4deeb90c5b8a01e93b",
        f"{AUDIT_1024}/execution/before/exercism-py-6/truth.json": "2c1c6535b9af103b637606b839a3a87046086d981a6d950337a710226166fc39",
        f"{AUDIT_1024}/execution/before/tb-cargo-plan/checker.py": "0cd726ce42ce3b45df0b4162efd48251c397f5d3475297e1f60481cb185c98be",
        f"{AUDIT_1024}/execution/before/tb-cargo-plan/spec.md": "e79cbfc3157c695ae17e016cd9c843761b9c0b6d8aab1c4bf61c23fd08ed028a",
        f"{AUDIT_1024}/execution/before/tb-cargo-plan/truth.json": "e886cd0990ffdedc1d474690f684ad908783bcd8dc4185331b13a8edbc7d3bc1",
        f"{AUDIT_1024}/execution/final-validation.json": "8b001e14334ed33ffcd7aac995f85a8fae16c89b083ab305d9edf0bf743f70e1",
        f"{AUDIT_1024}/execution/grade-copy-smoke.json": "1697d9bc360199e210e209739943ceceeab53b2092353ccfe37163e5e90050d4",
        f"{AUDIT_1024}/execution/grade-copy.py": "0c81e6ebdbfa8ccf4b2f25228b1701bd092589477ff726dcb28bf6e2b7081672",
        f"{AUDIT_1024}/execution/reproduce.py": "80ff26bf501e41d8da350b74c27a9293f7e58d0ebb72a06b001a6de3fa237833",
    },
    f"{AUDIT_1024}/numeric（数值族）": {
        f"{AUDIT_1024}/numeric/README.md": "6626b7e77cb3601f4289ebb8c07d0d036ac8acfa50290320488d20f82d48a01f",
        f"{AUDIT_1024}/numeric/run_audit.py": "f182b95f3957053690ecc19a5a2e7c16aa44dac72ab948eca1ccf5703d8953b8",
        f"{AUDIT_1024}/numeric/results.json": "7e2f92d82151dbaa6650838f11b057d009f0283f70225c315a8c2dab9f081b18",
        f"{AUDIT_1024}/numeric/bird-ca-schools-15.selftest.stdout.txt": "de9ae8c3ce350d0d4c76f03ced570d5384a4faf3bb71c6d285cbfd99e84a1814",
        f"{AUDIT_1024}/numeric/dabstep-payments-10.selftest.stdout.txt": "95e5507d723139fc26807b39fec721467996b294abdd3941a61d099211641a1a",
        f"{AUDIT_1024}/numeric/frozen/sha256.json": "4cb4b83e2f5b3093a4696d28e350e5e7ec7b8dab62e0991f51a0b025436ba04a",
        f"{AUDIT_1024}/numeric/frozen/bird-ca-schools-15/checker.py": "58ed761f08b1bfa924f5b4e5af14d77ea765bcec77fd877995a91c0f7c812a60",
        f"{AUDIT_1024}/numeric/frozen/bird-ca-schools-15/truth.json": "4883a8b35b22e1881384690d9ce22b2dc41215792d7fcb7fe1f6ebbf0d28c104",
        f"{AUDIT_1024}/numeric/frozen/dabstep-payments-10/checker.py": "76b67aac0c02cafbfb92602b69a999c36425441e1bf9f6fc94036d38e5d1a9e0",
        f"{AUDIT_1024}/numeric/frozen/dabstep-payments-10/truth.json": "46489110ef91486617db94456c6dd4d62df3cd6422ab27994c7f75075447829c",
    },
    f"{AUDIT_1024}/lcb（lcb 族）": {
        f"{AUDIT_1024}/lcb/README.md": "4d2c7b0539d62313f4ca7fdb468b4746014143ff97bacf0f4245404f1da7621a",
        f"{AUDIT_1024}/lcb/oracle-sha256.json": "26083d6076909ae18509ffe0d150e2239be34e2f5c33b50073263150dd6b3bcc",
        f"{AUDIT_1024}/lcb/selftest-2026-10-26.stdout.txt": "b9be0d6c868ea529d3f6ce8370eebbe63d8463df6cec98f7b401240bcceb00e0",
    },
    f"{AUDIT_1026}（bird-q26 并入收据）": {
        f"{AUDIT_1026}/README.md": "b9f540d34b29c407855304244f601d1dfd42a4dba5ef1d21acf51a97e401ee4f",
        f"{AUDIT_1026}/sha256-manifest.json": "d1f06baee280a30f44992fae6bc391e3047458f253a1908a047c82b0269f7bb4",
        f"{AUDIT_1026}/selftest-2026-10-26.stdout.txt": "5a39429c586e0f2408d95798a0a9a06ba17ac244cc1f8c4dac6df18b2bfa42b0",
        f"{AUDIT_1026}/replay_2026_10_26.py": "1d063dc151f560dcf5e4aa7a70c81f3e5b667445f01b336234b3252834659bdc",
        f"{AUDIT_1026}/replay-results.json": "3cc61dc5868de568bf6fb9d8101ab8d503292e56256e6935c18a13fa0ffec851",
        f"{AUDIT_1026}/q27_verify.py": "0dc75597c4050785270699d81b3081718bbc786d82c70b42925b484a47257394",
        f"{AUDIT_1026}/q27-verify-2026-10-26.json": "cbadcf7bdc84ef76d0941026f72722350623d47e4cb68e57d24f4964bd93401f",
    },
    "现行判卷资产（审计 README 声明的 2-用例 现行文件）": {
        # 声明于 execution/frozen-artifacts.json（2026-10-24 修后版本）
        "2-用例/exercism-py-6/checker.py": "8d6208aba69fc4bddbfac612d52712f04e94638070046966fbaa7271eb5c4d30",
        "2-用例/exercism-py-6/trusted_runner.py": "4002bcf55618673aea7ef408ea84dd8752b1596dd173db834330b24ce0c7ba86",
        "2-用例/exercism-py-6/truth.json": "6e4a66ad8ca47693d404f769374d55d7fdee457bed376764d5d3a014374c1f55",
        # 2026-10-27 收紧批后刷新（bird: B2 精确键集+禁 -- 注释；cargo: B12 距离精确相等
        # + B14 契约补 cargo_on_board_lbs；B13 预检翻转 3 场未并入。lcb 为披露式修订，
        # 不在本清单；收据：判卷审计-2026-10-27/checker-tightening-B2-B8-B12-13-14/）
        "2-用例/tb-cargo-plan/checker.py": "d84b1111a79000a38b97f602b533a344b8e2562abda9ec44474290701a75c677",
        "2-用例/tb-cargo-plan/truth.json": "982754f17eea923b0abfcfee08c991d7c502b771c5c0c598c5c097fe3460c163",
        # 声明于 bird-q26-并入/sha256-manifest.json §3（v1.2 现行版，README 摘录 5 行）
        "2-用例/bird-ca-schools-15/checker.py": "994be0b3b766e457b5b7d91de6b1ef814dbd6886c9e4a4f9ee63cded69abca54",
        "2-用例/bird-ca-schools-15/truth.json": "c5bb7999079ac8f1711049d81392729edf127a27134d32a905ca39de15b8ea19",
        "2-用例/bird-ca-schools-15/inputs/questions.json": "144bf7c36b58ab261f44676618a80af9f9d642fd287a4d2885c0cd7d53543f3e",
        "2-用例/bird-ca-schools-15/inputs/db/california_schools.sqlite": "a9e7d92a47c0d247d76a7a4acd76a4764f430f4d711e9e6809f399a9bf72322d",
        "2-用例/bird-ca-schools-15/solution/answers.jsonl": "9b63a1846f0955cf2976c1ebb310c30e16eb740c9f09b7a7a45b5fe11b251929",
    },
}

TAIL_CHARS_STDOUT = 2000
TAIL_CHARS_STDERR = 1000


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tail(text: str | None, max_chars: int) -> str:
    return (text or "")[-max_chars:]


def last_line(text: str | None) -> str:
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    return lines[-1] if lines else ""


# ---------------------------------------------------------------------------
# 阶段 1：五题自测
# ---------------------------------------------------------------------------
def stage_selftests(timeout_s: int) -> tuple[list[dict], bool]:
    results, all_ok = [], True
    for case in SELFTEST_CASES:
        rel = f"2-用例/{case}/checker.py"
        checker = REPO_ROOT / rel
        entry: dict = {"case": case, "command": f"python3 {rel} --selftest"}
        if not checker.is_file():
            entry.update(ok=False, exit_code=None, error=f"缺少文件：{rel}")
            results.append(entry)
            all_ok = False
            continue
        started = time.monotonic()
        try:
            proc = subprocess.run(
                [sys.executable, str(checker), "--selftest"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_s,
            )
            entry.update(
                exit_code=proc.returncode,
                ok=(proc.returncode == 0),
                duration_ms=int((time.monotonic() - started) * 1000),
                stdout_tail=tail(proc.stdout, TAIL_CHARS_STDOUT),
                stderr_tail=tail(proc.stderr, TAIL_CHARS_STDERR),
            )
        except subprocess.TimeoutExpired:
            entry.update(
                ok=False,
                exit_code=None,
                error=f"超时（>{timeout_s}s）",
                duration_ms=int((time.monotonic() - started) * 1000),
            )
        if not entry["ok"]:
            all_ok = False
        results.append(entry)
    return results, all_ok


# ---------------------------------------------------------------------------
# 阶段 2：审计收据存在性 + SHA-256 校验
# ---------------------------------------------------------------------------
def stage_sha_audit() -> tuple[list[dict], bool, int]:
    results, all_ok = [], True
    total = 0
    for family, entries in SHA_MANIFEST.items():
        for rel, expected in entries.items():
            total += 1
            path = REPO_ROOT / rel
            entry: dict = {
                "family": family,
                "path": rel,
                "expected_sha256": expected,
                "status": "ok",
            }
            if not path.is_file():
                entry["status"] = "missing"
            else:
                actual = sha256_of(path)
                entry["actual_sha256"] = actual
                if actual != expected:
                    entry["status"] = "sha-mismatch"
            if entry["status"] != "ok":
                all_ok = False
            results.append(entry)
    return results, all_ok, total


# ---------------------------------------------------------------------------
# Markdown 汇总
# ---------------------------------------------------------------------------
def render_markdown(now: str, selftests: list[dict], sha_rows: list[dict],
                    sha_total: int, overall_ok: bool) -> str:
    out: list[str] = []
    out.append("# 判卷回归一键化结果")
    out.append("")
    out.append(f"- 运行时间：{now}")
    out.append(f"- 仓库根目录：`{REPO_ROOT}`")
    out.append(f"- 解释器：Python {platform.python_version()}（{sys.executable}）")
    out.append(f"- {SHA_SNAPSHOT_NOTE}")
    out.append("")

    out.append("## 1) 五题自测（python3 2-用例/<case>/checker.py --selftest）")
    out.append("")
    out.append("| 用例 | 退出码 | 结果 | 耗时 |")
    out.append("|---|---|---|---|")
    for st in selftests:
        verdict = "PASS" if st.get("ok") else "**FAIL**"
        exit_code = st.get("exit_code")
        exit_code = "N/A" if exit_code is None else str(exit_code)
        out.append(f"| {st['case']} | {exit_code} | {verdict} | {st.get('duration_ms', 'N/A')} ms |")
    out.append("")
    out.append("### 输出尾部摘录")
    out.append("")
    for st in selftests:
        out.append(f"#### {st['case']}（exit={st.get('exit_code', 'N/A')}）")
        out.append("")
        out.append("```text")
        if st.get("error"):
            out.append(f"[ERROR] {st['error']}")
        tail_text = st.get("stdout_tail", "")
        tail_text = tail_text.rstrip("\n") or "(stdout 为空)"
        out.append(tail_text)
        if st.get("stderr_tail", "").strip():
            out.append(f"[stderr 尾部] {st['stderr_tail'].rstrip()}")
        out.append("```")
        out.append("")

    out.append(f"## 2) 审计收据存在性 + SHA-256 校验（共 {sha_total} 条）")
    out.append("")
    out.append("| 族 | 文件 | 存在 | SHA-256 匹配 |")
    out.append("|---|---|---|---|")
    for row in sha_rows:
        exists = "yes" if row["status"] != "missing" else "**NO**"
        match = "yes" if row["status"] == "ok" else "**NO**"
        out.append(f"| {row['family']} | `{row['path']}` | {exists} | {match} |")
    out.append("")
    out.append(f"> {SHA_SNAPSHOT_NOTE}。期望值固化于本脚本 `SHA_MANIFEST`；"
               "各审计 README 中另存有新旧版本对照（如 v1.1/v1.2），不随本快照刷新。")
    out.append("")

    verdict = "**PASS**（五题自测与 SHA 校验全部通过）" if overall_ok else "**FAIL**（存在失败项，见上表）"
    out.append("## 3) 总体结论")
    out.append("")
    out.append(verdict)
    out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="判卷回归一键化：五题自测 + 审计收据 SHA-256 校验（python3 标准库）")
    parser.add_argument("--output", default=str(SCRIPT_DIR / "results.json"),
                        help="results.json 输出路径（默认：脚本同目录 results.json）")
    parser.add_argument("--timeout", type=int, default=600,
                        help="单个 selftest 超时秒数（默认 600）")
    args = parser.parse_args(argv)

    if not (REPO_ROOT / "2-用例").is_dir():
        print(f"[FATAL] 未找到 2-用例/，请确认仓库根目录：{REPO_ROOT}", file=sys.stderr)
        return 2

    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    selftests, selftest_ok = stage_selftests(args.timeout)
    sha_rows, sha_ok, sha_total = stage_sha_audit()
    overall_ok = selftest_ok and sha_ok

    markdown = render_markdown(now, selftests, sha_rows, sha_total, overall_ok)
    print(markdown)

    results = {
        "tool": "4-打分细则/判卷回归/run_regression.py",
        "schema_version": 1,
        "generated_at": now,
        "repo_root": str(REPO_ROOT),
        "python": sys.executable,
        "python_version": platform.python_version(),
        "sha_snapshot_date": SHA_SNAPSHOT_DATE,
        "sha_snapshot_note": SHA_SNAPSHOT_NOTE,
        "overall": "pass" if overall_ok else "fail",
        "exit_code": 0 if overall_ok else 1,
        "summary": {
            "selftest_total": len(SELFTEST_CASES),
            "selftest_passed": sum(1 for s in selftests if s.get("ok")),
            "sha_checks_total": sha_total,
            "sha_checks_ok": sum(1 for r in sha_rows if r["status"] == "ok"),
        },
        "selftests": selftests,
        "sha_checks": sha_rows,
    }
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"results.json 已写入：{out_path}")

    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
