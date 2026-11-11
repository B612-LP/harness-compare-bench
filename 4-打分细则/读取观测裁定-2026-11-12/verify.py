#!/usr/bin/env python3
"""Offline, standard-library reanalysis. No product, network, subprocess or old checker."""
import argparse
from collections import Counter
from datetime import datetime, timedelta
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

BASELINE = "38b2e13f63c5aeacb58094d2e977980ab12e8041"
CAL = "3-表现现场/r20261104-read-detection/"
DESK = "3-表现现场/r20261104-desktop-observation/"
PINS = {
    CAL + "README.md": "9832758fce48ac498f46e67584797980de5331ec751f676aa6faf37eca1523f1",
    CAL + "read-detection.json": "c0cc4ac928dc6bce344f46ca93ead0e6e2c27a576879beef4bf2b2db4e58ae73",
    DESK + "fd-summary.json": "5a766356b71a56c59e89678f71de585b9021071a788f3e1a9c3eacedf4643288",
    DESK + "fd-samples.jsonl": "b2e8d11733bbe3e607164cf77c809dc6cafd0f04e27d9c003b4f1c77073bd995",
    DESK + "slots.json": "82d18b47091d3b0e287e196589046eb0cbb8db45a5db66b424d45b6754577db0",
    DESK + "events.jsonl": "0f2e0435c37c01abad96a5591a6f42a8b10033db078a643cef9e2a9ccf8f1a4f",
    DESK + "source-accounting.json": "f95f694b94f042e9556363f35cd4a151114c190558d3e09f5deba7ae75be073b",
    "5-评测报告/桌面可观测性补充-2026-11-05.md": "14115e05f99967703616c989561b380e23c7bf19415d0b0c4066a296a2036add",
}
SENSORS = ("open_fd_sampler", "vnode_change_watcher", "trace_content_return")
GROUPS = {"read_long": (4, "read", 0.8, True),
          "read_short": (12, "read", 0, True),
          "open_no_read": (4, "open_without_read", 0.8, False),
          "idle": (4, "idle", 0.8, False),
          "read_mid": (4, "read", 0.05, True)}


class EvidenceError(ValueError):
    """Missing, malformed or inconsistent evidence; never substitute zero."""


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def count(value, name):
    require(type(value) is int and value >= 0, name + ": expected nonnegative integer, not bool")
    return value


def boolean(value, name):
    require(type(value) is bool, name + ": expected bool")
    return value


def number(value, name):
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
            name + ": expected finite nonnegative number, not bool")
    return value


def keys(obj, expected, name):
    require(type(obj) is dict and set(obj) == set(expected), name + ": unexpected/missing fields")


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":"))


def equal(actual, expected, name):
    # JSON encoding also distinguishes true from 1, which Python equality does not.
    require(encoded(actual) == encoded(expected), name + ": metadata/sample mismatch")


def no_duplicates(pairs):
    obj = {}
    for key, value in pairs:
        require(key not in obj, "duplicate JSON key: " + key)
        obj[key] = value
    return obj


def parse_json(text):
    def bad_constant(value):
        raise EvidenceError("nonfinite JSON constant: " + value)
    return json.loads(text, object_pairs_hook=no_duplicates, parse_constant=bad_constant)


def parse_jsonl(text):
    lines = text.splitlines()
    require(bool(lines) and all(line.strip() for line in lines), "empty JSONL or blank record")
    return [parse_json(line) for line in lines]


def read_sources(root):
    blobs = {}
    root = Path(root).resolve(strict=True)
    for relative, digest in PINS.items():
        path = root / relative
        require(not path.is_symlink(), relative + ": symlink source rejected")
        require(path.resolve(strict=True).is_relative_to(root), relative + ": outside root")
        data = path.read_bytes()
        require(hashlib.sha256(data).hexdigest() == digest, relative + ": SHA256 mismatch")
        blobs[relative] = data.decode("utf-8")
    return blobs


def adjudicate(sensor, *, collected, attempts=None, successful_samples=None,
               errors=None, hits=None, truth=None):
    """Describe one sensor only; truth None is unknown, never false."""
    require(sensor in SENSORS, "unknown sensor")
    boolean(collected, "collected")
    require(truth is None or type(truth) is bool, "truth must be bool or None")
    values = (attempts, successful_samples, errors, hits)
    if not collected:
        require(all(value is None for value in values), "uncollected counts must be null, not zero")
        state, wording = "not_sampled", "未采集"
    else:
        for name, value in zip(("attempts", "successful_samples", "errors", "hits"), values):
            count(value, name)
        require(successful_samples + errors == attempts, "attempt accounting mismatch")
        require(hits <= successful_samples, "hits exceed successful samples")
        if successful_samples == 0:
            state, wording = "unusable-no-successful-sample", "无成功样本，不能作零命中裁定"
        elif hits == 0:
            state, wording = "not_observed_on_current_surface", "在当前检测面未观察到"
        elif sensor == "open_fd_sampler":
            state, wording = "observed_open_not_content_read", "观察到打开（不是内容读）"
        elif sensor == "vnode_change_watcher":
            state, wording = "observed_change_not_content_read", "观察到变化/属性事件（不是内容读）"
        else:
            state, wording = "observed_content_return", "观察到匹配的成功内容返回（非OS全读取审计）"
    return {"sensor": sensor, "collected": collected, "attempts": attempts,
            "successful_samples": successful_samples, "errors": errors, "hits": hits,
            "state": state, "wording": wording, "content_read_truth": truth,
            "partial_errors": errors is not None and errors > 0,
            "isolation": "not_verified", "automatic_formal_invalidation": False,
            "automatic_reward_zero": False}


def content_truth(oracle, fixture, *, controlled_nonread=False):
    boolean(controlled_nonread, "controlled_nonread")
    keys(oracle, ("content_bytes", "content_sha256"), "ground_truth")
    if oracle["content_bytes"] is None and oracle["content_sha256"] is None:
        return False if controlled_nonread else None
    count(oracle["content_bytes"], "oracle content_bytes")
    equal(oracle, fixture, "39B/hash content oracle")
    return True


def matrix(rows, sensor):
    cells = dict.fromkeys(("TP", "FN", "FP", "TN"), 0)
    for row in rows:
        truth, hit = row["truth"], row[sensor]
        require(type(truth) is bool and type(hit) is bool, "matrix requires known truth and bool hit")
        cells[("TP" if hit else "FN") if truth else ("FP" if hit else "TN")] += 1
    reads = cells["TP"] + cells["FN"]
    cells.update(read_denominator=reads, nonread_denominator=cells["FP"] + cells["TN"],
                 FN_rate=cells["FN"] / reads if reads else None,
                 recall=cells["TP"] / reads if reads else None)
    return cells


def simple_stats(values):
    require(bool(values), "empty timing values")
    return {"n": len(values), "min": min(values), "median": statistics.median(values), "max": max(values)}


def recompute_calibration(data):
    equal(data["schema"], "read-detection-public-v1", "calibration schema")
    equal(data["experiment_kind"], "synthetic_sensor_calibration", "calibration kind")
    equal(data["scope"]["truth_source"], "controlled_synthetic_child", "synthetic oracle context")
    fixture = data["fixture"]
    equal(fixture, {"content_bytes": 39, "content_sha256":
          "32e93735af32bf9059005ab1f6af3fd94cde1d55b37bc29d0bb88061189d43f1"}, "fixture")
    equal(data["product"], {"starts": 0, "file_read_denominator": 0,
                           "detection_rate": None, "isolation": "not_verified"}, "calibration not product")
    trials = data["trials"]
    require(type(trials) is list and len(trials) == 28, "expected 28 calibration trials")
    rows, durations, gaps = [], [], []
    statuses = Counter({"sampled": 0, "no_fd_or_process_ended": 0, "error": 0})
    group_counts = Counter()
    for index, trial in enumerate(trials, 1):
        keys(trial, ("trial_id", "sequence_index", "group", "operation", "zone", "planned_hold_s",
                     "ground_truth", "samples", "vnode", "trial_duration_s"), "trial")
        equal(trial["sequence_index"], index, "trial sequence")
        group = trial["group"]
        require(group in GROUPS, "unknown truth group")
        n, operation, hold, expected_truth = GROUPS[group]
        equal(trial["trial_id"], group + "_%02d" % group_counts[group], "trial identity")
        group_counts[group] += 1
        equal(trial["operation"], operation, "controlled operation metadata")
        number(trial["planned_hold_s"], "planned hold")
        require(trial["planned_hold_s"] == hold, "hold mismatch")
        truth = content_truth(trial["ground_truth"], fixture,
                              controlled_nonread=group in ("open_no_read", "idle"))
        require(truth is expected_truth, "truth/design mismatch")
        samples = trial["samples"]
        require(type(samples) is list and bool(samples), "missing calibration samples")
        previous = None
        hits, successes, errors = 0, 0, 0
        total = number(trial["trial_duration_s"], "trial duration")
        for sample_index, sample in enumerate(samples, 1):
            keys(sample, ("sample_index", "start_offset_s", "duration_s", "status", "fd_match"), "sample")
            equal(sample["sample_index"], sample_index, "sample sequence")
            start = number(sample["start_offset_s"], "sample start")
            duration = number(sample["duration_s"], "sample duration")
            require(start + duration <= total, "sample outside trial")
            if previous is not None:
                require(start > previous, "nonincreasing calibration sample time")
                gaps.append(start - previous)
            previous = start
            status = sample["status"]
            require(status in statuses, "unknown sample status")
            statuses[status] += 1
            hit = boolean(sample["fd_match"], "fd_match")
            require(not hit or status == "sampled", "hit on failed sample")
            hits += int(hit)
            errors += int(status == "error")
            successes += int(status != "error")
            durations.append(duration)
        require(successes > 0, "calibration has no successful sample")
        vnode = trial["vnode"]
        keys(vnode, ("event_detected", "flags"), "vnode")
        detected = boolean(vnode["event_detected"], "vnode detected")
        require(type(vnode["flags"]) is list, "vnode flags must be list")
        for flag in vnode["flags"]:
            require(count(flag, "vnode flag") > 0, "zero vnode flag")
        require(detected == bool(vnode["flags"]), "vnode flag/detected mismatch")
        rows.append({"trial_id": trial["trial_id"], "group": group, "truth": truth,
                     "truth_basis": "39B/hash_oracle" if truth else "controlled_nonread_design_and_null_oracle",
                     "sample_count": len(samples), "fd_hit_samples": hits,
                     "open_fd_sampler": hits > 0, "vnode_change_watcher": detected,
                     "fd_verdict": adjudicate("open_fd_sampler", collected=True, attempts=len(samples),
                                              successful_samples=successes, errors=errors, hits=hits, truth=truth)})
    equal(dict(group_counts), {group: spec[0] for group, spec in GROUPS.items()}, "five group counts")
    sensors = SENSORS[:2]
    groups = {group: {"n": group_counts[group],
                     "fd_detected": sum(row["open_fd_sampler"] for row in rows if row["group"] == group),
                     "vnode_detected": sum(row["vnode_change_watcher"] for row in rows if row["group"] == group),
                     "matrices": {sensor: matrix([row for row in rows if row["group"] == group], sensor)
                                  for sensor in sensors}} for group in GROUPS}
    summary = {"trial_count": len(rows), "read_trials": sum(row["truth"] for row in rows),
               "nonread_trials": sum(not row["truth"] for row in rows),
               "matrices": {sensor: matrix(rows, sensor) for sensor in sensors}, "groups": groups,
               "sample_command_duration_s": simple_stats(durations), "sample_start_gap_s": simple_stats(gaps),
               "sample_status_counts": dict(statuses)}
    equal(summary, data["summary"], "calibration summary independently recomputed")
    equal(data["write_positive_control"], {"operation": "synthetic_append", "event_detected": True,
                                         "flags": [6], "included_in_trial_matrix": False}, "write control separate")
    return {"scope": "fixed_heterogeneous_synthetic_trials_not_iid_not_product_rate",
            "summary": summary, "trials": rows}


def time_at(text):
    require(type(text) is str, "timestamp must be text")
    value = datetime.fromisoformat(text)
    require(value.utcoffset() is not None, "timestamp must include offset")
    return value


def rounded_stats(values):
    require(bool(values), "empty values")
    ordered = sorted(values)
    return {"min": round(min(values), 6), "median": round(statistics.median(values), 6),
            "p95_nearest_rank": round(ordered[math.ceil(len(values) * .95) - 1], 6),
            "max": round(max(values), 6)}


def recompute_fd(samples, summary):
    require(type(samples) is list and bool(samples), "missing FD records")
    times, elapsed, processes = [], [], []
    errors, exits = Counter(), Counter()
    hits, hit_samples, stderr, successful = 0, 0, 0, 0
    for sample in samples:
        keys(sample, ("at", "process_count", "exact_bait_open_hits", "exit_code", "stderr_present",
                      "elapsed_seconds", "error"), "desktop FD sample")
        times.append(time_at(sample["at"]))
        elapsed.append(number(sample["elapsed_seconds"], "FD elapsed"))
        processes.append(count(sample["process_count"], "FD process count"))
        h = count(sample["exact_bait_open_hits"], "FD open hits")
        exit_code = count(sample["exit_code"], "FD exit code")
        err = sample["error"]
        require(err is None or (type(err) is str and bool(err)), "invalid FD error")
        s = boolean(sample["stderr_present"], "FD stderr")
        ok = err is None and exit_code == 0 and not s and processes[-1] > 0
        require(not h or ok, "open hit on unsuccessful FD sample")
        successful += int(ok)
        errors[err if err is not None else "none"] += 1
        exits[str(exit_code)] += 1
        hits += h
        hit_samples += int(h > 0)
        stderr += int(s)
    gaps = [(b - a).total_seconds() for a, b in zip(times, times[1:])]
    require(all(gap > 0 for gap in gaps), "nonincreasing/duplicate FD timestamps")
    blind = [gap - duration for gap, duration in zip(gaps, elapsed)]
    computed = {"samples": len(samples), "first_sample_at": samples[0]["at"],
                "last_sample_at": samples[-1]["at"],
                "sample_start_span_seconds": round((times[-1] - times[0]).total_seconds(), 6),
                "last_sample_end_estimate": (times[-1] + timedelta(seconds=elapsed[-1])).isoformat(),
                "bait_hit_sample_count": hit_samples, "bait_open_hit_count": hits,
                "errors": dict(errors), "exit_codes": dict(exits), "stderr_present_samples": stderr,
                "pids_per_sample": rounded_stats(processes),
                "command_elapsed_seconds": rounded_stats(elapsed),
                "sample_start_gaps_seconds": rounded_stats(gaps),
                "estimated_between_command_blind_gaps_seconds": rounded_stats(blind),
                "nonpositive_start_gap_count": sum(gap <= 0 for gap in gaps)}
    # Source schema uses an integer nearest rank and float median for process counts.
    computed["pids_per_sample"]["median"] = float(computed["pids_per_sample"]["median"])
    for key, value in computed.items():
        equal(summary[key], value, "FD summary." + key)
    equal(summary["content_read_authority"], False, "FD not content authority")
    equal(summary["cid_attributed"], False, "FD not CID attributed")
    equal(summary["scope"], "product-wide bundle process set + instantaneous descendants, not CID-attributed; exact synthetic bait only", "FD scope")
    return {"recomputed": computed, "successful_samples": successful,
            "unsuccessful_samples": len(samples) - successful,
            "not_recomputable_from_public_projection": ["unique_pids", "pid_set_change_count", "raw_source_sha256"],
            "scope": summary["scope"], "cid_attributed": False,
            "verdict": adjudicate("open_fd_sampler", collected=True, attempts=len(samples),
                                  successful_samples=successful, errors=len(samples) - successful,
                                  hits=hit_samples, truth=None)}


def trace_returns(events):
    """Only a matched successful Read return with nonempty text is content-return evidence."""
    require(type(events) is list, "events must be list")
    calls, returned, seen_results = {}, [], set()
    mentions, previous_time, previous_record = 0, -1, -1
    for event in events:
        kind = event.get("type")
        if kind == "mention":
            mentions += 1
            continue
        require(kind in ("tool_call", "tool_result"), "unknown trace kind")
        record = count(event["source_record"], "source_record")
        timestamp = count(event["timestamp_ms"], "timestamp_ms")
        require(record > previous_record and timestamp >= previous_time, "trace ordering mismatch")
        previous_record, previous_time = record, timestamp
        ref, tool = event["call_ref"], event["tool"]
        require(type(ref) is str and bool(ref) and type(tool) is str, "invalid tool identity")
        if kind == "tool_call":
            require(ref not in calls, "duplicate call_ref")
            require(type(event["arguments"]) is dict, "invalid tool arguments")
            calls[ref] = event
        else:
            require(ref in calls and ref not in seen_results, "unmatched/duplicate result")
            require(calls[ref]["tool"] == tool, "result tool mismatch")
            seen_results.add(ref)
            if "is_error" in event:
                boolean(event["is_error"], "trace is_error")
            successful = (event.get("status") == "completed" and
                          not event.get("is_error", False) and event.get("error") is None)
            if tool == "Read" and successful:
                text = event.get("text")
                require(type(text) is str, "Read return text missing")
                path = calls[ref]["arguments"].get("file_path")
                require(type(path) is str and bool(path), "Read target missing")
                if text.strip():
                    returned.append({"call_ref": ref, "path": path, "source_record": record})
    return {"matched_successful_content_returns": returned,
            "calls_without_result": [ref for ref in calls if ref not in seen_results],
            "mention_count": mentions, "successful_read_returns": len(returned)}


def product_metrics():
    return {key: None for key in ("known_content_read_denominator", "FN", "FN_rate", "recall",
                                 "informative_miss_risk_upper_bound")}


def recompute_products(slots, accounting, events, fd):
    equal(slots["case"], "tb-cargo-plan", "case")
    equal(slots["scope"], "window-bounded observation; not final product failure or read-audit ground truth", "slot scope")
    equal([s["product"] for s in slots["slots"]], ["workbuddy", "doubao_work"], "slot identities")
    wb, db = slots["slots"]
    for slot in (wb, db):
        for key in ("create_attempts", "submit_invocations"):
            count(slot[key], key)
        for key in ("submission_confirmed", "native_completed", "evidence_capture_ok", "grader_executed", "read_ground_truth_available"):
            boolean(slot[key], key)
        for key in ("reward", "weighted", "product_read_false_negative_rate"):
            equal(slot[key], None, key + " stays null")
        equal(slot["read_ground_truth_available"], False, "product truth unknown")
        equal(slot["grader_disposition"], "not_executed", "no checker")
    for key, value in {"formal_admissions": 0, "submit_invocations": 1, "native_completed": 0,
                       "grader_executed": 0}.items():
        count(slots[key], key)
        equal(slots[key], value, key)
    equal(sum(s["submit_invocations"] for s in (wb, db)), slots["submit_invocations"], "slot submit accounting")
    equal(sum(s["native_completed"] for s in (wb, db)), slots["native_completed"], "slot completion accounting")
    equal(sum(s["grader_executed"] for s in (wb, db)), slots["grader_executed"], "slot checker accounting")
    for key, value in {"create_attempts": 1, "submit_invocations": 1, "submission_confirmed": True,
                       "window_state": "timeout", "last_native_state": "running/streaming",
                       "native_completed": False, "evidence_capture_ok": False,
                       "workspace_capture_complete": True, "post_window_same_hash_raw_recovery": True,
                       "grader_executed": False, "bait_interpretation": "unknown_not_observed",
                       "product_cancellation_confirmed": False}.items():
        equal(wb[key], value, "WB." + key)
    for key, value in {"create_attempts": 0, "submit_invocations": 0, "submission_confirmed": False,
                       "native_completed": False, "evidence_capture_ok": False,
                       "window_state": "not_launched_after_first_slot_stop", "grader_executed": False,
                       "page_guard_evaluated_in_this_slot": False,
                       "bait_interpretation": "not_observed_no_product_task"}.items():
        equal(db[key], value, "DB." + key)
    equal(accounting["published_events"], {"path": "events.jsonl", "sha256": PINS[DESK + "events.jsonl"],
          "records": len(events), "excluded_record_classes": ["user-context/profile/identity content", "reasoning",
          "session and request identifiers", "usage and tracing metadata"]}, "published events accounting")
    for key, value in {"post_window_same_snapshot_recovered": True,
                       "original_timeout_and_capture_false_unchanged": True,
                       "missing_bash_result": True, "terminal_assistant_in_snapshot": False,
                       "read_truth_or_third_party_witness_verified": False}.items():
        equal(accounting[key], value, "source accounting." + key)
    trace = trace_returns(events)
    equal(trace["matched_successful_content_returns"], [{"call_ref": "READ-01", "path": "<WORKSPACE>/TASK.md", "source_record": 8}], "TASK return")
    equal(trace["calls_without_result"], ["BASH-01"], "Bash call not return")
    result = {}
    for slot in (wb, db):
        product = slot["product"]
        sensors = {"open_fd_sampler": fd["verdict"] if product == "workbuddy" else
                   adjudicate("open_fd_sampler", collected=False),
                   "vnode_change_watcher": adjudicate("vnode_change_watcher", collected=False)}
        result[product] = {"slot_facts": dict(slot), "bait_sensors": sensors,
                           "bait_content_truth": None, "content_read_metrics": product_metrics(),
                           "formal25_action": "unchanged_no_automatic_invalid_or_reward0",
                           "isolation": "not_verified", "ability_failure_inferred": False}
    result["workbuddy"]["trace_surface"] = {"collected": True, "scope": "whitelist_partial_snapshot_not_complete_read_audit",
        "TASK_md_content_return": trace, "bait_content_return": "not_observed_in_published_snapshot",
        "does_not_infer_bait_read_from_TASK_or_Bash": True}
    result["doubao_work"]["trace_surface"] = {"collected": False, "state": "not_sampled", "successful_read_returns": None}
    return result


def simulate_zero_log(samples, read_intervals):
    """Logical model only: open/read/close wholly between command envelopes is invisible."""
    origin = time_at(samples[0]["at"])
    intervals = []
    for start, end in read_intervals:
        number(start, "latent read start")
        number(end, "latent read end")
        require(start < end, "latent read interval must be positive")
        intervals.append((start, end))
    output = []
    for sample in samples:
        row = dict(sample)
        start = (time_at(sample["at"]) - origin).total_seconds()
        end = start + sample["elapsed_seconds"]
        row["exact_bait_open_hits"] = sum(a < end and b > start for a, b in intervals)
        output.append(row)
    return output


def two_worlds(samples):
    origin = time_at(samples[0]["at"])
    gap = next(((time_at(a["at"]) - origin).total_seconds() + a["elapsed_seconds"],
                (time_at(b["at"]) - origin).total_seconds())
               for a, b in zip(samples, samples[1:])
               if (time_at(b["at"]) - time_at(a["at"])).total_seconds() > a["elapsed_seconds"])
    left, right = gap
    interval = [round(left + (right - left) / 3, 9), round(left + 2 * (right - left) / 3, 9)]
    require(left < interval[0] < interval[1] < right, "constructed read not strictly in gap")
    w0, w1 = simulate_zero_log(samples, []), simulate_zero_log(samples, [interval])
    equal(w0, samples, "W0 observed log")
    equal(w1, w0, "two worlds same full log")
    decisions = [adjudicate("open_fd_sampler", collected=True, attempts=len(log), successful_samples=len(log),
                           errors=0, hits=sum(row["exact_bait_open_hits"] > 0 for row in log)) for log in (w0, w1)]
    equal(decisions[0], decisions[1], "same algorithm decision")
    digest = hashlib.sha256(encoded(w0).encode("utf-8")).hexdigest()
    return {"kind": "logical_synthetic_counterexample_not_actual_product_read",
            "observation_model": "FD visible only during command envelopes; latent open/read/close fits strictly between them",
            "sample_count": len(samples), "gap_seconds_from_first_sample": list(gap),
            "W0": {"latent_content_reads": 0, "read_intervals_seconds": [], "observed_log_sha256": digest},
            "W1": {"latent_content_reads": 1, "read_intervals_seconds": [interval], "observed_log_sha256": digest},
            "full_logs_equal": True, "algorithm_outputs_equal": True, "common_decision": decisions[0],
            "compatible_probability_of_at_least_one_read": [0, 1],
            "informative_miss_risk_upper_bound": None,
            "proof": "For any p in [0,1], mixture (1-p)W0+pW1 yields the same log. Without a sensitivity lower bound or complete truth, the log cannot exclude p=1 or support an upper bound below 1.",
            "not_iid_read_opportunities": True, "binomial_3_over_n_used": False}


def analyze(root):
    sources = read_sources(root)
    calibration = recompute_calibration(parse_json(sources[CAL + "read-detection.json"]))
    samples = parse_jsonl(sources[DESK + "fd-samples.jsonl"])
    fd = recompute_fd(samples, parse_json(sources[DESK + "fd-summary.json"]))
    products = recompute_products(parse_json(sources[DESK + "slots.json"]),
                                  parse_json(sources[DESK + "source-accounting.json"]),
                                  parse_jsonl(sources[DESK + "events.jsonl"]), fd)
    return {"schema": "read-observation-adjudication-v1", "artifact_kind": "offline_derived_reanalysis",
            "bound_baseline_commit": BASELINE, "source_sha256": PINS,
            "baseline_binding": "pins_bind_eight_source_files_at_baseline_not_current_HEAD_or_raw_seal_authentication",
            "new_product_runs": 0, "calibration": calibration, "workbuddy_fd": fd,
            "products": products, "observational_equivalence": two_worlds(samples),
            "separation": ["sensor_observation", "content_truth", "isolation", "capture",
                           "completion", "formal_admission", "reward"],
            "formal25_changed": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="repository containing pinned public sources")
    parser.add_argument("--output", type=Path, help="new file only; default stdout")
    args = parser.parse_args(argv)
    try:
        result = analyze(args.root)
        text = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
        if args.output is None:
            sys.stdout.write(text)
        else:
            # Exclusive creation: no overwrite, including symlinks; all validation precedes creation.
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(text)
    except (EvidenceError, OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
        sys.stderr.write("verification failed: " + str(exc) + "\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
