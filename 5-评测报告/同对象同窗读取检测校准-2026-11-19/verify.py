#!/usr/bin/env python3
"""Offline consistency check of the published derivative; not raw-source verification."""
import copy
import json
from pathlib import Path
import re
import sys

PLAN = {"long": (650_000_000, 30_000_000, 120_000_000, 15_000_000),
        "short": (12_000_000, 4_000_000, 7_000_000, 3_000_000)}
ROLES = ("read", "open_only")


def require(ok, name):
    if not ok:
        raise ValueError(name)


def object_pairs(pairs):
    out = dict(pairs)
    require(len(out) == len(pairs), "duplicate JSON key")
    return out


def fields(row, names):
    require(type(row) is dict and row.keys() == set(names.split()), "unexpected/missing fields: " + names)


def digest(s):
    return isinstance(s, str) and re.fullmatch(r"[0-9a-f]{64}", s) is not None


def qualify(row, label, fixture):
    fields(row, "pair target_alias planned_hold_ns planned_action_ns planned_sample_ns phase_tolerance_ns arms sample truth_pair_qualified decision")
    params = tuple(row[k] for k in ("planned_hold_ns", "planned_action_ns", "planned_sample_ns", "phase_tolerance_ns"))
    require(all(type(v) is int for v in params) and params == PLAN[label] and row["pair"] == label
            and row["target_alias"] == fixture["alias"], "pair does not use the frozen plan/object")
    hold, act_phase, sample_phase, tol = params
    arms = row["arms"]
    require(type(arms) is list and len(arms) == 2, "expected paired arms")
    reasons = []
    truth_check = {}
    pre, actions, post, closes = [], [], [], []
    for role, arm in zip(ROLES, arms):
        fields(arm, "role opened_on_target open_start_ns open_end_ns pre_fstat_ns post_fstat_ns close_start_ns close_end_ns action action_start_ns action_end_ns bytes sha256 initial_offset final_offset")
        require(arm["role"] == role, "unexpected arm order")
        vals = tuple(arm[k] for k in ("open_start_ns", "open_end_ns", "pre_fstat_ns", "action_start_ns", "action_end_ns",
                                      "post_fstat_ns", "close_start_ns", "close_end_ns", "initial_offset", "final_offset"))
        require(all(type(v) is int for v in vals) and type(arm["opened_on_target"]) is bool, "invalid worker fields")
        ob, oe, pf, ab, ae, sf, cb, ce, initial, final = vals
        if not (0 <= ob <= oe <= pf <= ab <= ae <= sf <= hold <= cb <= ce):
            reasons.append(role + ": worker event order")
        if not (ob <= tol and act_phase <= ab <= act_phase+tol and cb <= hold+tol):
            reasons.append(role + ": worker outside frozen tolerance")
        bound = arm["opened_on_target"] and initial == 0
        if role == "read":
            oracle = (arm["action"] == "os.read" and type(arm["bytes"]) is int and
                      arm["bytes"] == final == fixture["bytes"] and arm["sha256"] == fixture["sha256"])
        else:
            oracle = (arm["action"] == "no_content_read_marker" and arm["bytes"] is None and
                      arm["sha256"] is None and final == 0)
        truth_check[role] = bool(bound and oracle)
        if not truth_check[role]:
            reasons.append(role + ": object/content truth not established")
        pre.append(pf)
        actions.append(ab)
        post.append(sf)
        closes.append(cb)
    left, right = max([0] + post), min([hold] + closes)
    if max(pre) > min(actions):
        reasons.append("both FDs not confirmed on target before the earlier action")
    if left >= right:
        reasons.append("no nonempty common post-action timing interval")
    truth_pair = not reasons
    sample = row["sample"]
    fields(sample, "attempted start_ns end_ns exit stdout_empty stderr_empty exact_FD_target_matches_read_then_open_only")
    begin, end, status = (sample[k] for k in ("start_ns", "end_ns", "exit"))
    require(all(v is None or type(v) is int for v in (begin, end, status)) and
            all(type(sample[k]) is bool for k in ("attempted", "stdout_empty", "stderr_empty")), "invalid sample fields")
    if not (sample["attempted"] and begin is not None and end is not None and sample_phase <= begin <= sample_phase+tol):
        reasons.append("no sample at the frozen phase")
    if not (begin is not None and end is not None and left <= begin <= end <= right):
        reasons.append("sample envelope not inside common post-action timing interval")
    if status != 0 or not sample["stderr_empty"] or sample["stdout_empty"]:
        reasons.append("lsof result not usable")
    flags = sample["exact_FD_target_matches_read_then_open_only"]
    if flags != [True, True] or not all(v is True for v in flags):
        reasons.append("exact sensor target match not established in both arms")
    decision = "unknown" if reasons else "matched_same_fd_visibility"
    require(row["truth_pair_qualified"] is truth_pair and row["decision"] == decision, "stored adjudication disagrees with projection")
    return {"pair": label, "content_records_consistent": truth_check, "truth_pair_qualified": truth_pair,
            "post_action_timing_interval_ns": [left, right], "decision": decision, "reasons": reasons}


def validate(doc):
    fields(doc, "format scope clock time_unit source_receipt preregistration_sha256 implementation_seal_sha256 target sensor pairs product_runs product_read_truth product_recall contamination_upper_bound")
    require(doc["format"] == "local-read-fd-paired-derived-v2" and doc["scope"] == "one_non_product_regular_fixture"
            and doc["clock"] == "CLOCK_MONOTONIC" and doc["time_unit"] == "nanoseconds_from_each_pair_T", "scope/clock mismatch")
    require(type(doc["product_runs"]) is int and doc["product_runs"] == 0 and
            all(doc[k] is None for k in ("product_read_truth", "product_recall", "contamination_upper_bound")), "product claims out of scope")
    source, fixture = doc["source_receipt"], doc["target"]
    fields(source, "bytes sha256")
    fields(fixture, "alias bytes sha256 mode_octal regular cleanup_recorded")
    require(all(digest(s) for s in (doc["preregistration_sha256"], doc["implementation_seal_sha256"], source["sha256"], fixture["sha256"]))
            and type(source["bytes"]) is int and source["bytes"] > 0, "invalid commitment")
    require(fixture["alias"] == "fixture-A" and type(fixture["bytes"]) is int and fixture["bytes"] == 512
            and fixture["mode_octal"] == "0600" and fixture["regular"] is True and fixture["cleanup_recorded"] is True, "unexpected fixture")
    require(doc["sensor"] == {"program": "lsof", "record_binding": "own_PID+FD+REG+device+inode",
                              "selection": "own_PID_AND_FD"}, "unexpected sensor")
    require(type(doc["pairs"]) is list and len(doc["pairs"]) == len(PLAN), "unexpected pair count")
    return [qualify(row, label, fixture) for row, label in zip(doc["pairs"], PLAN)]


def self_test(doc):
    checks = 0
    def mutate(mutation, truth=None, reason=None, must_reject=False):
        nonlocal checks
        trial = copy.deepcopy(doc)
        row = trial["pairs"][0]
        mutation(trial, row)
        try:
            if not must_reject:
                row.update(decision="unknown", truth_pair_qualified=truth)
            result = validate(trial)
        except ValueError:
            if not must_reject:
                raise
        else:
            require(not must_reject and result[0]["decision"] == "unknown" and reason in result[0]["reasons"], "self-test failed")
        checks += 1
    mutate(lambda d, r: r["sample"].update(end_ns=651_000_000), True, "sample envelope not inside common post-action timing interval")
    mutate(lambda d, r: r["sample"].update(attempted=False, start_ns=None, end_ns=None), True, "no sample at the frozen phase")
    mutate(lambda d, r: r["sample"].update(exact_FD_target_matches_read_then_open_only=[True, False]), True,
           "exact sensor target match not established in both arms")
    mutate(lambda d, r: r["arms"][1].update(opened_on_target=False), False, "open_only: object/content truth not established")
    mutate(lambda d, r: r["arms"][1].update(bytes=0), False, "open_only: object/content truth not established")
    mutate(lambda d, r: r["sample"].update(end_ns=651_000_000), must_reject=True)
    mutate(lambda d, r: d.update(product_recall=0), must_reject=True)
    return checks


if __name__ == "__main__":
    require(sys.argv[1:] in ([], ["--self-test"]), "optionally pass --self-test (no other inputs)")
    receipt = Path(__file__).with_name("evidence.json")
    doc = json.loads(receipt.read_bytes(), object_pairs_hook=object_pairs)
    result = {"verification": "derivative_consistency_only", "pairs": validate(doc)}
    if sys.argv[1:]:
        result["mutation_tests_passed"] = self_test(doc)
    print(json.dumps(result, indent=2, sort_keys=True))
