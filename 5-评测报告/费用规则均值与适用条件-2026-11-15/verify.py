#!/usr/bin/env python3
"""Offline rule-average audit, not a historical execution or billing reconstruction.

Only six pinned public files are read. Results go to stdout; no output files are
created. Decimal means are displayed to 18 places (half-up), while the final
six-place value is rounded directly from the unrounded sum/count. The two-rule
example is synthetic and does not assert the payment provider's contract.
"""
import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP, localcontext
from pathlib import Path

CASE = Path(__file__).resolve().parents[2] / "2-用例" / "dabstep-payments-10"
HASHES = {
    "inputs/fees.json": "9a833666ae9be5a8e756dd1fe076c72e7c502d64161315ffa8fee9e5bf2599dc",
    "inputs/manual.md": "bb7f4ca6fdc759af1f480702b3a3b12e17e9293b0d38a1dbfbbc8ffc1e572d2c",
    "inputs/questions.jsonl": "d99d3109e216b8e091d478602fce7cb687b47c40338ce8d016300c9ee7013730",
    "spec.md": "ef0f822d01b56089bb6fe56f1a9a6bcf7f4a1ee9796689908c8ac04a45c53852",
    "truth.json": "9e6e395fc7b0e5cf60238b8c3ab30fdaa399422fc047f554f0198488156e46d8",
    "solution/answers.jsonl": "a8c497b953b1b09ff9f9f5310481866cbf574cd94c16019bd8b74fef21f977e1",
}


class AuditError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise AuditError(message)


def _object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def _constant(_):
    raise AuditError("non-finite JSON number")


def parse_json(data):
    try:
        return json.loads(data, parse_float=Decimal, object_pairs_hook=_object,
                          parse_constant=_constant)
    except (ValueError, UnicodeError) as exc:
        raise AuditError("invalid JSON") from exc


def read_sources(case=CASE):
    """Read bytes once, check independent pins before parsing or computing."""
    result = {}
    for name, digest in HASHES.items():
        try:
            data = (case / name).read_bytes()
        except OSError as exc:
            raise AuditError("public source unavailable") from exc
        require(hashlib.sha256(data).hexdigest() == digest, "public source hash mismatch")
        result[name] = data
    return result


def json_lines(data):
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise AuditError("invalid UTF-8") from exc
    require(bool(lines) and all(line.strip() for line in lines), "invalid JSONL")
    return [parse_json(line) for line in lines]


def validate_sources(sources):
    truth = parse_json(sources["truth.json"])
    require(type(truth) is dict and type(truth.get("gold")) is dict,
            "invalid truth")
    require(truth["gold"].get("1273") == "0.120132" and
            type(truth["gold"].get("1273")) is str, "invalid gold")
    require(type(truth.get("input_sha256")) is dict, "invalid source ledger")
    for name in ("fees.json", "manual.md", "questions.jsonl"):
        require(truth["input_sha256"].get(name) == HASHES["inputs/" + name],
                "source ledger mismatch")
    answers = json_lines(sources["solution/answers.jsonl"])
    questions = json_lines(sources["inputs/questions.jsonl"])
    for entries in (answers, questions):
        require(all(type(x) is dict and type(x.get("task_id")) is str for x in entries),
                "invalid task records")
        ids = [x["task_id"] for x in entries]
        require(len(ids) == len(set(ids)), "duplicate task")
    matching_answers = [x for x in answers if x["task_id"] == "1273"]
    matching_questions = [x for x in questions if x["task_id"] == "1273"]
    require(len(matching_answers) == len(matching_questions) == 1, "missing task")
    require(matching_answers[0].get("answer") == truth["gold"]["1273"] and
            type(matching_answers[0].get("answer")) is str, "gold mismatch")
    q = matching_questions[0]
    require(q.get("question") == "For credit transactions, what would be the average fee that the card scheme GlobalCard would charge for a transaction value of 10 EUR?" and
            type(q.get("guidelines")) is str and "rounded to 6 decimals" in q["guidelines"],
            "question mismatch")
    manual = sources["inputs/manual.md"].decode("utf-8")
    spec = sources["spec.md"].decode("utf-8")
    require("fee = fixed_amount + rate * transaction_value / 10000" in manual and
            "If a field is set to null it means that it applies to all possible values of that field" in manual and
            "is_credit ∈ {true, null}" in spec, "rule definition mismatch")
    return parse_json(sources["inputs/fees.json"]), truth["gold"]["1273"]


def aggregate_rules(rules):
    """Aggregate rule fees, not actual transactions; reject float and bool-as-int."""
    require(type(rules) is list and bool(rules), "invalid rules")
    groups = {"true": {"count": 0, "sum": Decimal(0)},
              "null": {"count": 0, "sum": Decimal(0)}}
    for rule in rules:
        require(type(rule) is dict, "invalid rule")
        require(all(key in rule for key in ("card_scheme", "is_credit", "fixed_amount", "rate")),
                "missing rule field")
        scheme, credit = rule["card_scheme"], rule["is_credit"]
        fixed, rate = rule["fixed_amount"], rule["rate"]
        require(type(scheme) is str and bool(scheme), "invalid scheme")
        require(credit is None or type(credit) is bool, "invalid credit type")
        require(type(fixed) is Decimal and fixed.is_finite() and fixed >= 0,
                "invalid fixed amount")
        require(type(rate) is int and rate >= 0, "invalid rate")
        if scheme == "GlobalCard" and credit is not False:
            group = groups["true" if credit is True else "null"]
            group["count"] += 1
            group["sum"] += fixed + Decimal(rate) * Decimal(10) / Decimal(10000)
    return groups


def average(total, count, places):
    require(type(total) is Decimal and total.is_finite(), "invalid sum")
    require(type(count) is int and count > 0, "invalid count")
    require(type(places) is int and 0 <= places <= 18, "invalid precision")
    with localcontext() as ctx:
        ctx.prec = 60
        return (total / Decimal(count)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def synthetic(rules, transactions):
    """Equality predicates form mutually exclusive synthetic rules; require one match."""
    require(type(rules) is list and len(rules) > 0 and type(transactions) is list and len(transactions) > 0,
            "invalid synthetic input")
    for rule in rules:
        require(type(rule) is dict and set(rule) == {"match", "fee"} and
                type(rule["match"]) is str and bool(rule["match"]) and
                type(rule["fee"]) is Decimal and rule["fee"].is_finite() and rule["fee"] >= 0,
                "invalid synthetic rule")
    require(len({r["match"] for r in rules}) == len(rules), "overlapping synthetic rules")
    require(all(type(tx) is str and bool(tx) for tx in transactions), "invalid synthetic transaction")
    total = Decimal(0)
    for tx in transactions:
        matches = [r for r in rules if r["match"] == tx]
        require(len(matches) == 1, "synthetic transaction must match exactly one rule")
        total += matches[0]["fee"]
    rule_sum = sum((r["fee"] for r in rules), Decimal(0))
    return {"rule_count": len(rules), "rule_sum": rule_sum,
            "transaction_count": len(transactions), "transaction_sum": total}


def report(case=CASE):
    sources = read_sources(case)
    rules, gold = validate_sources(sources)
    groups = aggregate_rules(rules)
    require(len(rules) == 1000, "unexpected rule count")
    require(groups["true"] == {"count": 123, "sum": Decimal("14.473")} and
            groups["null"] == {"count": 21, "sum": Decimal("2.826")},
            "unexpected aggregates")
    count = groups["true"]["count"] + groups["null"]["count"]
    total = groups["true"]["sum"] + groups["null"]["sum"]
    rounded = average(total, count, 6)
    require(str(rounded) == gold, "rounded result differs from gold")
    fixture = synthetic([{"match": "A", "fee": Decimal("0.1")},
                         {"match": "B", "fee": Decimal("0.3")}], ["A", "A", "B"])
    require(fixture["rule_sum"] * 3 != fixture["transaction_sum"] * 2,
            "synthetic averages unexpectedly equal")
    def summary(n, s):
        return {"count": n, "sum_eur": str(s), "mean_eur_18dp_half_up": str(average(s, n, 18))}
    return {
        "scope": "10 EUR rule-equal average; not actual transaction weighting or billing",
        "rounding": "half-up; 18 places for display; six places directly from exact sum/count",
        "groups": {"true": summary(groups["true"]["count"], groups["true"]["sum"]),
                   "null": summary(groups["null"]["count"], groups["null"]["sum"]),
                   "combined": {**summary(count, total), "mean_eur_6dp_half_up": str(rounded)}},
        "synthetic_only": {"rule_equal": summary(fixture["rule_count"], fixture["rule_sum"]),
                           "transaction_equal": summary(fixture["transaction_count"], fixture["transaction_sum"]),
                           "transaction_mean_exact": "1/6"},
        "limitations": "Question leaves population and actual charging unspecified; null is a wildcard, not an empty-list claim; overlapping rule priority and billing are not inferred.",
        "public_source_sha256": dict(HASHES),
    }


def main():
    import sys
    if len(sys.argv) != 1:
        print("This verifier accepts no arguments and never writes output files.", file=sys.stderr)
        return 2
    try:
        print(json.dumps(report(), ensure_ascii=False, indent=2))
    except (AuditError, UnicodeError, ArithmeticError) as exc:
        print("audit failed: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
