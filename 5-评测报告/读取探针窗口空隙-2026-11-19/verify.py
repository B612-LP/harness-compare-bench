#!/usr/bin/env python3
"""Offline check of redacted relative timing, committed flags and reported limits; no live sampling."""
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

MS = 1_000_000
ROLES = ("read", "open_only")
PHASE = {"before": 30, "open": 220, "action": 340, "close": 460, "after": 620, "witness_close": 900}
SHA = hashlib.sha256(bytes(range(256)) * 2).hexdigest()


def check(ok, reason):
    if not ok:
        raise ValueError(reason)


def unique_members(items):
    obj = {}
    for k, v in items:
        check(k not in obj, "duplicate_projection_json_member")
        obj[k] = v
    return obj


def load_projection(text):
    return json.loads(text, object_pairs_hook=unique_members)


def ints(value):
    check(type(value) is list and len(value) == 2 and all(type(v) is int for v in value), "interval_shape")
    check(value[0] <= value[1], "interval_order")
    return value


def exact_fields(value, *fields):
    check(type(value) is dict and set(value) == set(fields), "unexpected_fields")


def all_ok(*times):
    return list(times) == sorted(times)


def phase(name, *times):
    check(all_ok(PHASE[name] * MS, *times, (PHASE[name] + 25) * MS), "phase_" + name)


def verify(e):
    exact_fields(e, "schema", "artifact_kind", "attempt_count", "pair_count", "clock", "phase_ms", "max_late_ms",
                 "sample_max_ms", "expected_payload_sha256", "products", "source_commitments", "result")
    check(e["schema"] == "local-read-gap-derived-v1" and e["artifact_kind"] == "privacy_redacted_derived" and
          all(type(e[k]) is int and e[k] == 1 for k in ("attempt_count", "pair_count")) and
          e["clock"] == "clock_gettime_ns(CLOCK_MONOTONIC)", "scope")
    exact_fields(e["phase_ms"], *PHASE)
    check(e["phase_ms"] == PHASE and all(type(v) is int for v in e["phase_ms"].values()) and
          type(e["max_late_ms"]) is int and e["max_late_ms"] == 25 and
          type(e["sample_max_ms"]) is int and e["sample_max_ms"] == 125 and e["expected_payload_sha256"] == SHA,
          "frozen_thresholds")
    p = e["products"]
    exact_fields(p, "invocations", "file_read_denominator", "false_negative_rate", "recall", "nontrivial_contamination_upper_bound")
    check(type(p["invocations"]) is int and p["invocations"] == 0 and
          all(v is None for k, v in p.items() if k != "invocations"), "nonproduct_only")
    s = e["source_commitments"]
    exact_fields(s, "receipt_sha256", "start_sha256", "implementation_seal_sha256", "prereg_sha256")
    check(all(type(x) is str and re.fullmatch(r"[0-9a-f]{64}", x) for x in s.values()), "source_commitment_shape")
    r = e["result"]
    exact_fields(r, "classification", "reasons", "arms", "samples", "shared_target_window_ns", "shared_witness_window_ns",
                 "same_target_identity_bound", "separate_same_witness_identity_bound", "same_non_root_euid_bound", "owned_cleanup_confirmed")
    check(r["classification"] == "observed_gap_same_target_zero" and r["reasons"] == [], "unknown_or_unqualified_receipt")
    check(all(r[k] is True for k in ("same_target_identity_bound", "separate_same_witness_identity_bound",
                                   "same_non_root_euid_bound", "owned_cleanup_confirmed")), "projected_scope_not_bound")
    arms = r["arms"]
    exact_fields(arms, *ROLES)
    wo2, wc1, op1, op2, cl1, cl2, actions = [], [], [], [], [], [], []
    for name, a in arms.items():
        exact_fields(a, "witness_open", "witness_close", "target_open", "target_close", "action", "os_read",
                     "content_bytes", "content_sha256", "content_reads", "offsets")
        wb, we = ints(a["witness_open"])
        xc, xe = ints(a["witness_close"])
        ob, oe = ints(a["target_open"])
        cb, ce = ints(a["target_close"])
        ab, ae = ints(a["action"])
        check(all_ok(wb, we, -250 * MS, ob, oe, ab, ae, cb, ce, xc, xe), "worker_event_order")
        for kind, begin, end in (("open", ob, oe), ("action", ab, ae), ("close", cb, ce), ("witness_close", xc, xe)):
            phase(kind, begin, end)
        offsets = ints(a["offsets"])
        check(type(a["content_bytes"]) is int and type(a["content_reads"]) is int, "content_truth_shape")
        if name == "read":
            rb, re_ = ints(a["os_read"])
            check(all_ok(ab, rb, re_, ae) and offsets == [0, 512] and
                  (a["content_bytes"], a["content_sha256"], a["content_reads"]) == (512, SHA, 1), "read_oracle")
        else:
            check(a["os_read"] is None and offsets == [0, 0] and
                  (a["content_bytes"], a["content_sha256"], a["content_reads"]) == (0, None, 0), "open_only_oracle")
        wo2.append(we)
        wc1.append(xc)
        op1.append(ob)
        op2.append(oe)
        cl1.append(cb)
        cl2.append(ce)
        actions.append((ab, ae))
    wt = [max(wo2), min(wc1)]
    tf = [max(op2), min(cl1)]
    check(ints(r["shared_witness_window_ns"]) == wt and ints(r["shared_target_window_ns"]) == tf,
          "shared_window_mismatch")
    check(all_ok(wt[0], min(op1), max(cl2), wt[1]) and all(all_ok(tf[0], *a, tf[1]) for a in actions),
          "covered_witness_and_common_target_actions")
    samples = r["samples"]
    exact_fields(samples, "before", "after")
    for name, x in samples.items():
        exact_fields(x, "envelope", "returncode", "stderr_empty", "witness_exact_by_arm", "target_rows_by_arm")
        b, end = ints(x["envelope"])
        phase(name, b)
        check(0 < end - b <= 125 * MS and all_ok(wt[0], b, end, wt[1]), "sample_length_or_witness_window")
        check(type(x["returncode"]) is int and x["returncode"] == 0 and x["stderr_empty"] is True, "unusable_sample")
        exact_fields(x["witness_exact_by_arm"], *ROLES)
        exact_fields(x["target_rows_by_arm"], *ROLES)
        check(all(x["witness_exact_by_arm"][role] is True for role in ROLES), "missing_witness")
        check(all(type(x["target_rows_by_arm"][role]) is int and x["target_rows_by_arm"][role] == 0 for role in ROLES),
              "nonzero_target_rows")
    before_end = samples["before"]["envelope"][1]
    after_begin = samples["after"]["envelope"][0]
    check(before_end < min(op1) and max(cl2) < after_begin, "strict_sample_gap")
    return {"classification": "observed_gap_same_target_zero", "scope": "redacted_projection_only",
            "unsampled_interval_ns_from_T": [before_end, after_begin], "full_lifecycle_union_bounds_ns_from_T": [min(op1), max(cl2)],
            "shared_target_window_ns_from_T": tf, "product_metrics_remain_null": True}


def self_test(original):
    def corrupt_time(x):
        x["samples"]["before"]["envelope"][1] = x["arms"]["read"]["target_open"][0]

    mutations = [corrupt_time,
                 lambda x: x["samples"]["after"]["witness_exact_by_arm"].update(open_only=False),
                 lambda x: x["samples"]["before"]["target_rows_by_arm"].update(read=1),
                 lambda x: x["samples"]["before"].update(returncode=1),
                 lambda x: x["samples"]["after"].update(stderr_empty=False),
                 lambda x: x["arms"]["open_only"].update(content_reads=1),
                 lambda x: x["arms"]["read"].update(offsets=[0, 1]),
                 lambda x: x.update(owned_cleanup_confirmed=False),
                 lambda x: x.update(same_target_identity_bound=False)]
    for change in mutations[:-2]:
        candidate = copy.deepcopy(original["result"])
        change(candidate)
        trial = dict(original, result=candidate)
        try:
            verify(trial)
        except ValueError:
            continue
        raise ValueError("mutation_accepted")
    for change in mutations[-2:]:
        trial = copy.deepcopy(original)
        change(trial["result"])
        try:
            verify(trial)
        except ValueError:
            continue
        raise ValueError("scope_mutation_accepted")
    text = json.dumps(original, separators=(",", ":"))
    duplicate_cases = ((text, '"pair_count":1', '"pair_count":9,"pair_count":1'),
                       (text, '"content_reads":0', '"content_reads":1,"content_reads":0'))
    for raw, anchor, replaced in duplicate_cases:
        check(raw.count(anchor) == 1, "invalid_duplicate_test_anchor")
        try:
            load_projection(raw.replace(anchor, replaced, 1))
        except ValueError as exc:
            if str(exc) == "duplicate_projection_json_member":
                continue
            raise
        raise ValueError("duplicate_member_mutation_accepted")
    return len(mutations) + len(duplicate_cases)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args not in ([], ["--self-test"]):
        sys.exit("usage: python3 verify.py [--self-test]")
    try:
        data = load_projection(Path(__file__).with_name("evidence.json").read_text(encoding="utf-8"))
        value = verify(data)
        if args:
            value["fail_closed_offline_mutations"] = self_test(data)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"classification": "unknown", "reason": str(exc)}, ensure_ascii=False))
        sys.exit(2)
    print(json.dumps(value, ensure_ascii=False))
