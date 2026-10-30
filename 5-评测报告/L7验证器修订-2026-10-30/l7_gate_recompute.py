#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L7-A 验收 r7（终版）：gate 语义默认值显式化。

验收面（设计变更见 1-评测方案/自动循环L7-2026-10-30/history-replay-design-note.md；
r1-r6 五版跨批重演探索全档 VOIDED 保留，其结构发现=封印钉定设计的强化证明）：
  N1a. CLI 缺两参 → 退出码≠0 且报错含「L7-A」
  N1b. CLI 缺 --plan-dir → 同上
  N2.  API verify_execution(plan_dir=None) → GateError（含 L7-A，非 TypeError）
  N3.  API load_execution_seal(None) → GateError
  N4.  --plan-dir 指向不存在目录 → fail-closed 退出≠0
  S0.  修订版 gate --selftest → PASS
  P0.  修前提取字节（git c8710fb）== 封印钉值 38b42a87…
  P4.  修订版 gate 复判 L6 → 恰因 gate.py sha-mismatch（want=38b42a87）拒
  G1.  L4 基线收据在档（L4独立验收 realdata-product，formal 0/17 口径）
  G2.  L5 基线收据在档（L5独立复核 r4-history-reproduced-receipt-02）
  G3.  L6 基线收据在档且 formal=1/1（gate-admission-e3.json，已知结构断言）
"""
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path("/Users/b612-lp/Documents/harness-compare-bench")
GATE = ROOT / "1-评测方案" / "工具链" / "l5-execution" / "gate.py"
ARCHIVE = ROOT / "5-评测报告" / "L7验证器修订-2026-10-30"
PRE_SHA = "38b42a87c30c87d277f0a8984c4300919da3867826790a01fd24af6766b05ce9"
L6_LOOP = ROOT / "1-评测方案" / "自动循环L6-2026-10-30"
L6_BINDING = L6_LOOP / "runtime-binding.json"
L6_PLAN = L6_LOOP
BASELINE_RECEIPTS = {
    "G1-l4": [ROOT / "5-评测报告/L4独立验收-2026-10-29/realdata-product/gate-admission-dsh6-wb5.json",
              ROOT / "5-评测报告/L4独立验收-2026-10-29/realdata-product/gate-admission-codex6.json"],
    "G2-l5": [ROOT / "5-评测报告/L5独立复核-2026-10-30/r4-history-reproduced-receipt-02.json"],
    "G3-l6": [L6_LOOP / "gate-admission-e3.json"],
}


def run_gate(args):
    return subprocess.run([sys.executable, str(GATE)] + args,
                          capture_output=True, text=True, timeout=600)


def api_probe(probe_expr):
    code = ("import importlib.util\n"
            "spec = importlib.util.spec_from_file_location('g', %r)\n"
            "m = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(m)\n"
            "try:\n"
            "    %s\n"
            "    print('NO-RAISE')\n"
            "except m.GateError as e:\n"
            "    print('GATEERROR:', e)\n"
            "except TypeError as e:\n"
            "    print('TYPEERROR:', e)\n" % (str(GATE), probe_expr))
    return subprocess.run([sys.executable, "-c", code],
                          capture_output=True, text=True, timeout=120)


def main():
    results = []
    all_ok = True

    def check(name, ok, detail=""):
        nonlocal all_ok
        results.append({"assert": name, "pass": bool(ok), "detail": str(detail)[:300]})
        all_ok = all_ok and bool(ok)

    # ---- N 组：近似错误例 ----
    r = run_gate(["--verify-execution"])
    check("N1a CLI 缺两参被拒", r.returncode != 0 and "L7-A" in (r.stderr + r.stdout),
          (r.stderr + r.stdout)[-140:])
    r = run_gate(["--verify-execution", "--binding", str(L6_BINDING)])
    check("N1b CLI 缺 --plan-dir 被拒", r.returncode != 0 and "L7-A" in (r.stderr + r.stdout),
          (r.stderr + r.stdout)[-140:])
    r = api_probe("m.verify_execution(%r)" % str(L6_BINDING))
    check("N2 API plan_dir=None → GateError（非 TypeError）",
          "GATEERROR" in r.stdout and "L7-A" in r.stdout and "TYPEERROR" not in r.stdout,
          r.stdout[-160:])
    r = api_probe("m.load_execution_seal(None)")
    check("N3 load_execution_seal(None) → GateError",
          "GATEERROR" in r.stdout and "L7-A" in r.stdout, r.stdout[-160:])
    r = run_gate(["--verify-execution", "--binding", str(L6_BINDING),
                  "--plan-dir", "/nonexistent-l7-probe"])
    check("N4 不存在 plan-dir fail-closed", r.returncode != 0,
          (r.stderr + r.stdout)[-140:])

    # ---- S0：修订版自测 ----
    r = run_gate(["--selftest"])
    check("S0 修订版 gate selftest PASS",
          r.returncode == 0 and "GATE_SELFTEST: PASS" in r.stdout, r.stdout[-120:])

    # ---- P0/P4：封印字节一致性 + pin 精确拒 ----
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        frozen = Path(td) / "gate-pinned.py"
        frozen.write_bytes(subprocess.run(
            ["git", "-C", str(ROOT),
             "show", "c8710fb:1-评测方案/工具链/l5-execution/gate.py"],
            capture_output=True, check=True).stdout)
        check("P0 修前提取字节 == 封印钉值",
              hashlib.sha256(frozen.read_bytes()).hexdigest() == PRE_SHA)
    r = run_gate(["--admission", "--binding", str(L6_BINDING),
                  "--product", "workbuddy", "--plan-dir", str(L6_PLAN)])
    combined = r.stdout + r.stderr
    check("P4 修订版复判 L6 恰因封印 pin 拒（gate.py want=38b42a87）",
          r.returncode != 0
          and "manifest-files-safe-and-consistent" in combined
          and "sha-mismatch" in combined
          and re.search(r"gate\.py.*?38b42a87", combined, re.S) is not None,
          combined[-260:])

    # ---- G 组：三批基线收据引用固定 ----
    for key in ("G1-l4", "G2-l5"):
        for path in BASELINE_RECEIPTS[key]:
            ok = path.is_file()
            sha = hashlib.sha256(path.read_bytes()).hexdigest()[:16] if ok else "MISSING"
            check("%s 基线收据在档（sha256_16=%s）" % (key, sha), ok, str(path))
    g3 = BASELINE_RECEIPTS["G3-l6"][0]
    ok3 = g3.is_file()
    if ok3:
        d3 = json.loads(g3.read_text(encoding="utf-8"))
        check("G3-l6 基线收据在档且 formal=1/1",
              d3.get("summary", {}).get("formal_admitted") == 1
              and d3.get("summary", {}).get("all_formal_admitted") is True,
              json.dumps(d3.get("summary"), ensure_ascii=False))

    receipt = {"kind": "l7-gate-explicitization-acceptance",
               "tool": "l7_gate_recompute.py (r7 final; r1-r6 voided chain in dir)",
               "at": datetime.now().astimezone().isoformat(timespec="seconds"),
               "pre_gate_sha256": PRE_SHA,
               "post_gate_sha256": hashlib.sha256(GATE.read_bytes()).hexdigest(),
               "design_note": "1-评测方案/自动循环L7-2026-10-30/history-replay-design-note.md",
               "counts": {"total": len(results),
                          "passed": sum(1 for x in results if x["pass"]),
                          "failed": sum(1 for x in results if not x["pass"])},
               "assertions": results, "all_ok": all_ok, "live_doc_drift": []}
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    out = ARCHIVE / "l7-gate-recompute-receipt.json"
    if out.exists():
        raise SystemExit("拒绝写入：收据已存在（write-once）")
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"all_ok": all_ok, "counts": receipt["counts"], "receipt": str(out)},
                     ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
