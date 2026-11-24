#!/usr/bin/env python3
"""R10 public test: normal fixture + 8 near-miss injections, all must be rejected."""
import copy
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import recompute  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
REJECTED = 0


def nm(name, mutate):
    global REJECTED
    d = copy.deepcopy(recompute.load_contract())
    mutate(d)
    try:
        recompute.validate(d)
    except recompute.Invalid as e:
        print("PASS", name, "->", "INVALID:" + str(e))
        REJECTED += 1
        return
    # NOTE: validate() returning True on a mutated contract is a failure
    raise SystemExit("FAIL " + name + " (mutation accepted)")


def main():
    d0 = recompute.load_contract()
    recompute.validate(d0)
    print("PASS normal fixture")

    # NM1: 0 候选控制 混同为 0 实际读取（adjudication null 被填值）
    def m1(d):
        d["adjudication_nulls_preserved"]["known_actual_product_reads"] = 0
    nm("NM1 zero-controls-as-zero-reads", m1)

    # NM2: coverage 字段（覆盖率）
    def m2(d):
        d["totals"]["coverage"] = 0.061
    nm("NM2 coverage-field", m2)

    # NM3: 负时差截零
    def m3(d):
        for row in d["admission_matrix"]:
            if row["pair_id"] == "T05":
                row["delta_ms"] = 0.0
        d["totals"]["negative_delta_kept"] = [{"pair_id": "T09", "delta_ms": -42.0}]
    nm("NM3 negative-delta-truncated", m3)

    # NM4: 窗内对象 FAIL 报成漏检（非法枚举）
    def m4(d):
        for row in d["admission_matrix"]:
            if row["pair_id"] == "T01":
                row["admission"] = "MISSED"
    nm("NM4 illegal-admission-enum", m4)

    # NM5a: C1 PASS 但别名不匹配（行级三态一致性）
    def m5a(d):
        d["admission_matrix"][0]["C1_object"] = "PASS"
    nm("NM5a C1-alias-consistency", m5a)

    # NM5b: 三准则全 PASS 却 NOT_ELIGIBLE（准入一致性）
    def m5b(d):
        row = d["admission_matrix"][0]
        row["C1_object"] = row["C2_window"] = row["C3_content_truth"] = "PASS"
        row["read_target_alias"] = d["sensor"]["target_alias"]
        row["call_in_window"] = row["result_in_window"] = True
    nm("NM5b admission-consistency", m5b)

    # NM5c: C3 PASS 但传感器无内容真值
    def m5c(d):
        d["admission_matrix"][1]["C3_content_truth"] = "PASS"
    nm("NM5c C3-authority-consistency", m5c)

    # NM5d: C2 PASS 但行内窗口布尔为 False
    def m5d(d):
        d["admission_matrix"][1]["C2_window"] = "PASS"
    nm("NM5d C2-window-consistency", m5d)

    print("rejected:", REJECTED)
    if REJECTED != 8:
        raise SystemExit("expected 8 rejections, got %d" % REJECTED)
    print("全部夹具拒绝通过：9 项（1 正常 + 8 注入）")


if __name__ == "__main__":
    main()
