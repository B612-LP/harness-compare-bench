"""Read-only q49 evidence correction, not a product scorer.

Only five pinned canonical sources are read. No individual payment rows are
returned. Decimal parses monetary values; Fraction preserves exact sums and rate
ordering independently of the 28-significant-digit Decimal display strings.
"""

import csv
import hashlib
import io
import json
import re
from decimal import Context, Decimal, InvalidOperation, localcontext
from fractions import Fraction
from pathlib import Path


CASE = "2-用例/dabstep-payments-10/"
PINS = {
    CASE + "spec.md": "ef0f822d01b56089bb6fe56f1a9a6bcf7f4a1ee9796689908c8ac04a45c53852",
    CASE + "truth.json": "9e6e395fc7b0e5cf60238b8c3ab30fdaa399422fc047f554f0198488156e46d8",
    CASE + "inputs/manual.md": "bb7f4ca6fdc759af1f480702b3a3b12e17e9293b0d38a1dbfbbc8ffc1e572d2c",
    CASE + "inputs/questions.jsonl": "d99d3109e216b8e091d478602fce7cb687b47c40338ce8d016300c9ee7013730",
    CASE + "inputs/payments.csv": "5fbb26210a45427d7a6560cfab3a362a08e4067f27cd03695f211a51c47ffc25",
}
REQUIRED_COLUMNS = {"ip_country", "eur_amount", "has_fraudulent_dispute"}
QUESTION = "What is the top country (ip_country) for fraud? A. NL, B. BE, C. ES, D. FR"
MANUAL_DEFINITION = "Fraud is defined as the ratio of fraudulent volume over total volume."


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_path(root: Path, relative: str) -> Path:
    root = Path(root)
    require(not root.is_symlink(), "DAB root is a symlink")
    root = root.resolve(strict=True)
    require(root.is_dir(), "DAB root is not a directory")
    parts = Path(relative).parts
    require(parts and not Path(relative).is_absolute()
            and all(part not in (".", "..") for part in parts), "unsafe DAB path")
    current = root
    for part in parts:
        current = current / part
        require(not current.is_symlink(), "DAB source path is a symlink")
    resolved = current.resolve(strict=True)
    require(root in resolved.parents and resolved.is_file(), "DAB source escapes root")
    return resolved


def read_sources(root: Path) -> dict:
    sources = {}
    for relative, expected in PINS.items():
        data = safe_path(root, relative).read_bytes()
        require(hashlib.sha256(data).hexdigest() == expected,
                "DAB source SHA mismatch: " + relative)
        sources[relative] = data
    return sources


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate DAB JSON key")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("non-finite DAB JSON constant")


def decode_json(data):
    return json.loads(data, object_pairs_hook=unique_object,
                      parse_float=Decimal, parse_constant=reject_constant)


def amount_fraction(value: str) -> Fraction:
    """Finite, nonnegative, plain decimal only; no float conversion or rounding."""
    require(type(value) is str, "DAB amount must be text")
    try:
        amount = Decimal(value)
    except InvalidOperation as error:
        raise ValueError("invalid DAB amount") from error
    require(amount.is_finite(), "non-finite DAB amount")
    require(re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", value) is not None,
            "DAB amount must be nonnegative plain decimal")
    return Fraction(amount)


def exact_decimal(value: Fraction) -> str:
    """Terminating decimal, as produced by summing finite decimal amounts."""
    # Decimal-derived denominators contain only powers of two and five.
    denominator = value.denominator
    powers = []
    for factor in (2, 5):
        power = 0
        while denominator % factor == 0:
            denominator //= factor
            power += 1
        powers.append(power)
    require(denominator == 1, "nonterminating DAB monetary total")
    scale = max(powers)
    coefficient = value.numerator * (10 ** scale // value.denominator)
    digits = tuple(int(digit) for digit in str(abs(coefficient)))
    # Decimal tuple construction is exact even under a caller's low precision.
    return format(Decimal((int(coefficient < 0), digits, -scale)), "f")


def display_ratio(value: Fraction, percent=False) -> str:
    # This is display precision only; ranking uses exact Fraction comparisons.
    with localcontext(Context(prec=28)):
        numerator = value.numerator * (100 if percent else 1)
        return format(Decimal(numerator) / Decimal(value.denominator), "f")


def aggregate_payments(text: str) -> dict:
    """Pure CSV aggregation, no products, scorer, gold or root dependencies.

    Uses every row, groups ip_country (not issuing_country), selects exactly the
    True flag for fraudulent volume, and applies no merchant/refusal filter.
    All country denominators must be positive. Ambiguous maxima remain ties.
    Extra canonical CSV columns are ignored and never returned.
    """
    require(type(text) is str, "DAB CSV must be text")
    reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
    columns = reader.fieldnames
    require(columns is not None and all(columns) and len(columns) == len(set(columns))
            and REQUIRED_COLUMNS.issubset(columns), "invalid DAB CSV columns")
    groups = {}
    rows = 0
    fraudulent_rows = 0
    try:
        for row in reader:
            require(None not in row and all(value is not None for value in row.values()),
                    "invalid DAB CSV row width")
            country = row["ip_country"]
            require(re.fullmatch(r"[A-Z]{2}", country) is not None,
                    "invalid DAB country code")
            flag = row["has_fraudulent_dispute"]
            require(flag in ("True", "False"), "invalid DAB fraud flag")
            amount = amount_fraction(row["eur_amount"])
            item = groups.setdefault(country, {"rows": 0, "fraud_rows": 0,
                                              "eur": Fraction(0), "fraud_eur": Fraction(0)})
            rows += 1
            item["rows"] += 1
            item["eur"] += amount
            if flag == "True":
                fraudulent_rows += 1
                item["fraud_rows"] += 1
                item["fraud_eur"] += amount
    except csv.Error as error:
        raise ValueError("malformed DAB CSV") from error
    require(rows > 0, "empty DAB payments")
    require(all(item["eur"] > 0 for item in groups.values()), "zero DAB country denominator")
    count_ratios = {country: Fraction(item["fraud_rows"], item["rows"])
                    for country, item in groups.items()}
    volume_ratios = {country: item["fraud_eur"] / item["eur"]
                     for country, item in groups.items()}

    def maxima(values):
        maximum = max(values.values())
        return sorted(country for country, value in values.items() if value == maximum)

    countries = []
    for country, item in sorted(groups.items()):
        countries.append({
            "ip_country": country,
            "rows": item["rows"],
            "fraud_rows": item["fraud_rows"],
            "eur": exact_decimal(item["eur"]),
            "fraud_eur": exact_decimal(item["fraud_eur"]),
            "count_ratio": display_ratio(count_ratios[country]),
            "monetary_volume_ratio": display_ratio(volume_ratios[country]),
            "monetary_volume_percent": display_ratio(volume_ratios[country], percent=True),
        })
    return {
        "rows": rows,
        "fraud_flag_counts": {"True": fraudulent_rows, "False": rows - fraudulent_rows},
        "by_ip_country": countries,
        "highest_fraud_count": maxima({country: item["fraud_rows"]
                                        for country, item in groups.items()}),
        "highest_count_ratio": maxima(count_ratios),
        "highest_monetary_volume_ratio": maxima(volume_ratios),
        "rate_ordering": "exact rational comparison, not rounded display",
        "ratio_display_significant_digits": 28,
        "row_filter": "none; all rows, all merchants, including refused rows",
    }


def derive(root: Path) -> dict:
    sources = read_sources(root)
    truth = decode_json(sources[CASE + "truth.json"])
    questions = [decode_json(line) for line in
                 sources[CASE + "inputs/questions.jsonl"].decode("utf-8").splitlines()]
    require(type(truth) is dict and truth.get("n_tasks") == 10
            and type(truth.get("n_tasks")) is int, "unexpected DAB task count")
    require(len(questions) == 10 and all(type(q) is dict and type(q.get("task_id")) is str
                                       for q in questions), "unexpected DAB questions")
    require(len({q["task_id"] for q in questions}) == 10, "duplicate DAB task ID")
    q49 = [q for q in questions if q["task_id"] == "49"]
    require(len(q49) == 1 and q49[0].get("question") == QUESTION, "unexpected q49 question")
    require(truth.get("gold", {}).get("49") == "B. BE", "unexpected q49 recorded gold")
    for name in ("manual.md", "questions.jsonl", "payments.csv"):
        require(truth.get("input_sha256", {}).get(name) == PINS[CASE + "inputs/" + name],
                "DAB truth input binding mismatch")
    manual = sources[CASE + "inputs/manual.md"].decode("utf-8").splitlines()
    spec = sources[CASE + "spec.md"].decode("utf-8").splitlines()
    require(manual[224] == MANUAL_DEFINITION, "DAB manual definition anchor mismatch")
    require("欺诈交易最多的 ip_country" in spec[41]
            and "按 `ip_country` 计数" in spec[142]
            and "BE=2,493" in spec[142], "DAB old count claim anchor mismatch")
    aggregate = aggregate_payments(sources[CASE + "inputs/payments.csv"].decode("utf-8"))
    require(aggregate["rows"] == 138236 and len(aggregate["by_ip_country"]) == 8
            and aggregate["fraud_flag_counts"] == {"True": 10765, "False": 127471},
            "DAB canonical aggregate shape mismatch")
    require(aggregate["highest_fraud_count"] == ["NL"]
            and aggregate["highest_count_ratio"] == ["BE"]
            and aggregate["highest_monetary_volume_ratio"] == ["BE"],
            "DAB canonical maxima mismatch")
    # Re-read all fixed sources to detect ordinary in-process source mutation.
    require(read_sources(root) == sources, "DAB sources changed during derivation")
    return {
        "case_id": "dabstep-payments-10",
        "question_id": "49",
        "source_sha256": dict(PINS),
        "source_anchors": {"old_count_description": CASE + "spec.md:42",
                           "old_cross_check": CASE + "spec.md:143",
                           "fraud_definition": CASE + "inputs/manual.md:225",
                           "question": CASE + "inputs/questions.jsonl:2",
                           "recorded_gold": CASE + "truth.json:45"},
        "aggregation": aggregate,
        "finding": "The old COUNT cross-check omitted NL (2955 > BE 2493); it does not support B. BE.",
        "corrected_basis": "Fraudulent EUR volume / total EUR volume is highest in BE, consistent with the manual and unchanged B. BE.",
        "recorded_official_compat_gold": "B. BE",
        "original_gold_supported_by_volume_ratio": True,
        "gold_changed": False,
        "q49_attribution_withdrawn": False,
        "q2697_adjudication_scope_extended": False,
        "historical_scores_or_denominators_changed": False,
        "original_spec_edited": False,
        "product_artifacts_read": False,
        "product_regrading_performed": False,
        "new_formal_admissions": 0,
        "private_originals_authenticated": False,
        "scope": "canonical public-data arithmetic; correction of evidence record, not a new product experiment or scoring contract",
    }
