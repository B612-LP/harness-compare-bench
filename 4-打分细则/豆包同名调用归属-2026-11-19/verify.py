"""Check the public ordinal evidence, not the native trace or identifier values."""
from copy import deepcopy
import json
from math import factorial
from pathlib import Path
import sys


def check(ok, reason):
    if not ok:
        raise ValueError(reason)


def keys(value, fields):
    check(type(value) is dict and set(value) == set(fields.split()), "unexpected fields")


def integers(value):
    check(type(value) is list and all(type(x) is int for x in value), "invalid ordinal list")
    return value


def equal_int(value, expected):
    check(type(value) is int and value == expected, "incorrect count or ordinal")


def unique_object(pairs):
    obj = dict(pairs)
    check(len(obj) == len(pairs), "duplicate JSON key")
    return obj


def verify(data):
    keys(data, "schema source_relation native_identity_values_public native_identity_absence_proven A B")
    equal_int(data["schema"], 1)
    check(data["source_relation"] == "different_archived_tasks", "source relation")
    check(data["native_identity_values_public"] is False, "only ordinal identities may be public")
    check(data["native_identity_absence_proven"] is False, "native identity absence is not established")
    a, b = data["A"], data["B"]
    keys(a, "physical_row_window blocks unique_join_blocks fifo_agree_edges fifo_disagree_edges")
    keys(b, "physical_row_window strict_guard membership conditional_assumption blocks "
            "strict_guard_rejected_tool_rows strict_comparisons unknown_blocks")
    check(b["strict_guard"] == "assistant_summary_key_presence", "strict guard")
    check(b["membership"] == "unadjudicated", "membership must not be inferred")
    check(b["conditional_assumption"] == "all_adjacent_tool_rows_are_members_and_no_other_pairing_constraints",
          "missing conditional assumption")
    agreements = disagreements = rejected = 0
    for source, start, full in ((a, 3, True), (b, 5, False)):
        window = integers(source["physical_row_window"])
        check(window == [start, start + 8], "incorrect observation window")
        blocks = source["blocks"]
        check(type(blocks) is list and len(blocks) == 2, "incorrect block denominator")
        cursor = start
        for block, n in zip(blocks, (3, 4)):
            keys(block, "assistant_row call_name_classes tool_rows " +
                 ("matched_call_positions" if full else "identity fifo conditional_bijections"))
            equal_int(block["assistant_row"], cursor)
            check(integers(block["call_name_classes"]) == [1] * n, "nonhomogeneous call names")
            check(integers(block["tool_rows"]) == list(range(cursor + 1, cursor + n + 1)), "tool row loss or alias")
            positions = list(range(1, n + 1))
            if full:
                match = integers(block["matched_call_positions"])
                check(sorted(match) == positions, "ordinal match loss or alias")
                agree = sum(p == q for p, q in zip(match, positions))
                agreements += agree
                disagreements += n - agree
            else:
                check(block["identity"] == block["fifo"] == "unknown", "overclaimed projection verdict")
                equal_int(block["conditional_bijections"], factorial(n))
                rejected += n
            cursor += n + 1
        check(cursor - 1 == window[1], "incomplete row coverage")
    equal_int(a["unique_join_blocks"], len(a["blocks"]))
    equal_int(a["fifo_agree_edges"], agreements)
    equal_int(a["fifo_disagree_edges"], disagreements)
    equal_int(b["strict_guard_rejected_tool_rows"], rejected)
    equal_int(b["strict_comparisons"], 0)
    equal_int(b["unknown_blocks"], len(b["blocks"]))
    return agreements, disagreements


def negative_cases(data):
    for bad_match in ([1, 2], [1, 2, 2]):
        changed = deepcopy(data)
        changed["A"]["blocks"][0]["matched_call_positions"] = bad_match
        try:
            verify(changed)
        except ValueError as exc:
            check(str(exc) == "ordinal match loss or alias", "unexpected rejection in negative test")
        else:
            raise ValueError("negative ordinal test accepted")


if __name__ == "__main__":
    try:
        data = json.loads(Path(__file__).with_name("evidence.json").read_text(encoding="utf-8"),
                          object_pairs_hook=unique_object)
        agree, disagree = verify(data)
        negative_cases(data)
    except (OSError, ValueError):
        print("FAIL: public evidence or negative test rejected", file=sys.stderr)
        sys.exit(1)
    print(f"OK: A {agree} agree, {disagree} disagree; B unknown, conditional 6/24; loss and alias rejected")
