#!/usr/bin/env python3
"""公开复算入口：引用回读与已知读取正控（2026-11-13）。

只读本目录 result.json，重算全部派生统计与常量一致性，输出 JSON 结论。
不改任何文件；无网络；无第三方依赖。

用法：python3 verify.py
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULT = HERE / "result.json"

Z95 = 1.959963984540054  # 双侧 95% 正态分位


def wilson95(k: int, n: int) -> list[float]:
    """Wilson score 区间；n<=0 返回 [None, None]。"""
    if n <= 0:
        return [None, None]
    p = k / n
    z2 = Z95 * Z95
    denom = 1 + z2 / n
    center = p + z2 / (2 * n)
    half = Z95 * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    return [max(0.0, (center - half) / denom), min(1.0, (center + half) / denom)]


def median(values: list[float]) -> float:
    s = sorted(values)
    m = len(s)
    if m == 0:
        raise ValueError("median of empty list")
    if m % 2:
        return float(s[m // 2])
    return (s[m // 2 - 1] + s[m // 2]) / 2


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def verify(data: dict) -> dict:
    checks: dict[str, bool] = {}

    c = data["constants"]
    checks["middle_key_matches_source_string"] = (
        sha256_hex(c["probe_middle_source_string"]) == c["probe_middle_key"]
    )
    checks["fixture_sha256_wellformed"] = (
        len(c["probe_fixture_sha256"]) == 64
        and all(ch in "0123456789abcdef" for ch in c["probe_fixture_sha256"])
    )
    checks["fixture_line_count_consistent"] = (
        422 == c["probe_fixture_lines"] and c["probe_fixture_bytes"] == 35767
    )
    checks["probe_keys_distinct"] = len(
        {c["probe_head_key"], c["probe_tail_key"], c["probe_middle_key"]}
    ) == 3

    r1 = data["ring1_dsh_readback_mechanism"]
    sess = r1["sessions"]
    rb = sess["rb"]
    imk = sess["imk"]
    c1 = sess["c1"]

    checks["rb_n"] = len(rb) == r1["derived"]["rb_n"] == 6
    checks["rb_middle_hits"] = (
        sum(1 for s in rb if s["keys"]["MIDDLE_KEY"]) == r1["derived"]["rb_middle_hits"] == 6
    )
    checks["rb_all_keys_true"] = all(
        all(s["keys"].values()) for s in rb
    )
    checks["rb_single_read_each"] = all(s["read_attempts"] == 1 for s in rb)
    recomputed_wilson = wilson95(r1["derived"]["rb_middle_hits"], r1["derived"]["rb_n"])
    checks["rb_wilson95"] = (
        abs(recomputed_wilson[0] - r1["derived"]["rb_wilson95"][0]) < 1e-12
        and abs(recomputed_wilson[1] - r1["derived"]["rb_wilson95"][1]) < 1e-12
    )
    rb_totals = [sum(s["B_series"]) for s in rb]
    checks["rb_total_median"] = (
        median(rb_totals) == r1["derived"]["rb_session_total_median"] == 12293.0
    )
    imk_finals = [s["B_series"][-1] for s in imk]
    checks["imk_final_median"] = (
        median(imk_finals) == r1["derived"]["imk_final_request_median"] == 38435.0
    )
    delta = r1["derived"]["rb_session_total_median"] - r1["derived"]["imk_final_request_median"]
    checks["delta_median"] = (
        delta == r1["derived"]["rb_total_minus_imk_final_median"] == -26142.0
    )
    ratio = r1["derived"]["rb_session_total_median"] / r1["derived"]["imk_final_request_median"]
    checks["ratio"] = abs(ratio - r1["derived"]["rb_total_over_imk_final_median"]) < 5e-5
    checks["c1_gate_matches_baseline"] = (
        all(s["delta"] == 2382 and s["B_series"] == [1124, 3506] for s in c1)
        and r1["derived"]["c1_delta"] == 2382
        and r1["derived"]["baseline_r20261103_bounded_delta"] == 2382
        and r1["derived"]["c1_matches_20261103_baseline"] is True
    )
    checks["imk_all_keys_true"] = all(all(s["keys"].values()) for s in imk)
    checks["decision_branch"] = r1["derived"]["decision_branch"] == "recovered_via_read"

    r2 = data["ring2_workbuddy_known_read_positive_control"]
    checks["ring2_n3_all_pass"] = (
        r2["n"] == len(r2["sessions"]) == 3
        and all(s["read_calls"] == 1 and s["keys_all_correct"] and s["read_result_chars"] == 38332
                for s in r2["sessions"])
    )
    r3 = data["ring3_doubao_known_read_first_sampling"]
    checks["ring3_n3_all_pass"] = (
        r3["n"] == len(r3["sessions"]) == 3
        and all(s["read_calls"] == 1 and s["keys_all_correct"] and s["read_result_chars"] == 37367
                for s in r3["sessions"])
        and all(s["usage_fields_in_local_trace"] == "none" for s in r3["sessions"])
    )

    ok = all(checks.values())
    return {"ok": ok, "checks": checks}


def main() -> int:
    data = json.loads(RESULT.read_text(encoding="utf-8"))
    out = verify(data)
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
