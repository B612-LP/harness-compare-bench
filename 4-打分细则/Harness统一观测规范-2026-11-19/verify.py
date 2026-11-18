#!/usr/bin/env python3
"""Replay the common decision examples; never read or validate product originals."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

SCHEMA = "harness-observation-candidate-cases/0.3"
CASE_SHA256 = "11213335778ca5a2b40c2e7852b3c83ab04961286e8ad8212c24252497bae67f"
BASE = {"availability", "grammar", "attachment"}
PROFILES = {"common", "dsh-v4/chat", "codex-native/responses"}
VIEWS = {"event-values", "request-body", "selected-messages", "response-tool", "tool-arguments"}
ALGORITHMS = {"dsh-decimal-v1", "codex-local-json-v1", "message-v1", "origin-utf8"}
TARGETS = {"a-task", "fixture-a", "fixture-c"}


class BadCase(ValueError):
    pass


def need(condition, label):
    if not condition:
        raise BadCase(label)


def obj(value, keys):
    need(type(value) is dict and set(value) == keys, "object_shape")


def flag(value):
    need(type(value) is bool, "boolean_expected")
    return value


def optional_flag(value):
    if value is not None:
        flag(value)


def literal(value, choices):
    need(type(value) is str and value in choices, "unsupported_enum")


def json_object(items):
    result = {}
    for key, value in items:
        need(key not in result, "duplicate_key")
        result[key] = value
    return result


def reject_number(_):
    raise BadCase("number_not_supported_in_projection")


def load_bytes(blob):
    need(len(blob) <= 32768, "projection_too_large")
    return json.loads(blob.decode("utf-8"), object_pairs_hook=json_object,
                      parse_float=reject_number, parse_constant=reject_number)


def stage(data):
    available = data["availability"]
    grammar, attachment = data["grammar"], data["attachment"]
    literal(available, {"held", "unobserved"})
    if available == "unobserved":
        need(grammar is None and attachment is None, "missing_source_cannot_carry_checks")
        return "unknown_source"
    if not flag(grammar):
        need(attachment is None, "bad_format_cannot_carry_attachment")
        return "unknown_format"
    if not flag(attachment):
        return "unknown_attachment"
    return "known"


def equal_label(value):
    return "equal" if flag(value) else "different"


def assess_pair(data):
    obj(data, BASE | {"left_view", "right_view", "left_algorithm", "right_algorithm", "raw_equal", "selected_equal"})
    for name in ("left_view", "right_view"):
        literal(data[name], VIEWS)
    for name in ("left_algorithm", "right_algorithm"):
        literal(data[name], ALGORITHMS)
    raw, selected = data["raw_equal"], data["selected_equal"]
    optional_flag(raw)
    optional_flag(selected)
    status = stage(data)
    if status != "known" or data["left_view"] != data["right_view"]:
        need(raw is None and selected is None, "unadmitted_comparison")
        return {"status": status if status != "known" else "unknown_view", "raw": None, "selected": None}
    if data["left_algorithm"] != data["right_algorithm"]:
        need(selected is None, "incompatible_selected_algorithm")
        return {"status": "unknown_algorithm", "raw": equal_label(raw), "selected": None}
    return {"status": status, "raw": equal_label(raw), "selected": equal_label(selected)}


def assess_field(data):
    obj(data, BASE | {"object_complete", "field_present", "value"})
    complete, present, value = data["object_complete"], data["field_present"], data["value"]
    status = stage(data)
    if status != "known":
        need(complete is None and present is None and value is None, "unadmitted_field")
        return {"state": status, "value": None}
    if not flag(complete):
        need(present is None and value is None, "incomplete_object_cannot_confirm_presence")
        return {"state": "unknown_coverage", "value": None}
    if not flag(present):
        need(value is None, "absent_field_with_value")
        return {"state": "known_absent", "value": None}
    need(value is None or (type(value) is int and 0 <= value <= 1000000), "unregistered_field_value")
    return {"state": "known_present", "value": value}


def assess_coverage(data):
    obj(data, {"verified", "selected", "full_cover", "reference_role", "reference_bound",
               "constructed_for", "reference_for", "independent"})
    verified, selected = data["verified"], data["selected"]
    need(type(verified) is int and type(selected) is int and 0 <= verified <= selected <= 10000, "bad_denominator")
    literal(data["reference_role"], {"request", "response"})
    for place in ("constructed_for", "reference_for"):
        literal(data[place], TARGETS)
    bound, full, independent = (flag(data[k]) for k in ("reference_bound", "full_cover", "independent"))
    if not bound or data["reference_for"] != data["constructed_for"]:
        return {"selected": None, "full": "unknown_attachment"}
    if data["reference_role"] != "request":
        return {"selected": None, "full": "unknown_reference_role"}
    if not selected:
        return {"selected": None, "full": "unknown_coverage"}
    # Eligibility is not raw or whole-value equality; that needs separate proof.
    eligible = full and independent and verified == selected
    return {"selected": [verified, selected], "full": "eligible_for_full_proof" if eligible else "selected_only"}


DISPATCH = {"pair": assess_pair, "field": assess_field, "coverage": assess_coverage}


def same(left, right):
    return json.dumps(left, sort_keys=True, separators=(",", ":"), allow_nan=False) == json.dumps(
        right, sort_keys=True, separators=(",", ":"), allow_nan=False)


def check(data):
    obj(data, {"schema", "frozen", "cases"})
    need(data["schema"] == SCHEMA and data["frozen"] is False, "schema_or_status")
    cases = data["cases"]
    need(type(cases) is list and len(cases) == 14, "case_count")
    keys = set()
    for case in cases:
        obj(case, {"id", "origin", "profile", "kind", "input", "expect"})
        key = case["id"]
        need(type(key) is str and 1 <= len(key) <= 80 and key.isascii() and key not in keys, "case_identity")
        keys.add(key)
        literal(case["origin"], {"derived", "synthetic"})
        literal(case["profile"], PROFILES)
        literal(case["kind"], DISPATCH)
        need(same(DISPATCH[case["kind"]](case["input"]), case["expect"]), "decision_mismatch")
    return cases


def check_known_pairs(cases):
    lookup = {case["id"]: case for case in cases}
    pair = lookup["dsh-a-reencoded-log"]["input"]
    coverage = lookup["dsh-a-message-coverage"]["input"]
    field = lookup["dsh-b-required-absent"]["input"]
    invalid = [
        (assess_pair, dict(pair, attachment=False)),
        (assess_pair, dict(pair, grammar=False, attachment=None)),
        (assess_pair, dict(pair, right_view="request-body")),
        (assess_pair, dict(pair, right_algorithm="codex-local-json-v1")),
        (assess_pair, dict(pair, raw_equal=0)),
        (assess_field, dict(field, field_present=False, value=0)),
        (assess_field, dict(field, object_complete=False)),
        (assess_coverage, dict(coverage, verified=True)),
        (assess_coverage, dict(coverage, selected=7)),
        (load_bytes, b'{"frozen":false,"frozen":true}'),
        (load_bytes, b'{"frozen":"\xff"}'),
    ]
    for function, mutant in invalid:
        try:
            function(mutant)
        except (BadCase, UnicodeDecodeError):
            continue
        raise BadCase("negative_control_accepted")
    alternatives = [
        (assess_pair(dict(pair, attachment=False, raw_equal=None, selected_equal=None)),
         {"status": "unknown_attachment", "raw": None, "selected": None}),
        (assess_pair(dict(pair, grammar=False, attachment=None, raw_equal=None, selected_equal=None)),
         {"status": "unknown_format", "raw": None, "selected": None}),
        (assess_coverage(dict(coverage, reference_role="response")),
         {"selected": None, "full": "unknown_reference_role"}),
        (assess_coverage(dict(coverage, selected=0, verified=0, full_cover=True)),
         {"selected": None, "full": "unknown_coverage"}),
        (assess_coverage(dict(coverage, full_cover=True, independent=False)),
         {"selected": [8, 8], "full": "selected_only"}),
        (assess_coverage(dict(coverage, full_cover=True)),
         {"selected": [8, 8], "full": "eligible_for_full_proof"}),
    ]
    need(all(same(actual, expected) for actual, expected in alternatives), "control_decision_changed")
    return len(invalid) + len(alternatives)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        source = Path(__file__).with_name("cases.json")
        with source.open("rb") as handle:
            blob = handle.read(32769)
        need(hashlib.sha256(blob).hexdigest() == CASE_SHA256, "fixed_cases_digest")
        cases = check(load_bytes(blob))
        tests = check_known_pairs(cases) if args.self_test else 0
    except (ValueError, OSError, KeyError, RecursionError):
        print("candidate decision check failed", file=sys.stderr)
        return 1
    print(json.dumps({"schema": SCHEMA, "frozen": False, "cases": len(cases), "controls": tests}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
