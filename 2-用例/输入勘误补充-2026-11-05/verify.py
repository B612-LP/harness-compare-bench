#!/usr/bin/env python3
"""Read-only, fixed-source MCC errata verification; no historical regrading."""
import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import stat
import sys

BASE = "2-用例/dabstep-payments-10/"
MANUAL = BASE + "inputs/manual.md"
DICTIONARY = BASE + "inputs/merchant_category_codes.csv"
QUESTIONS = BASE + "inputs/questions.jsonl"
TRUTH = BASE + "truth.json"
SPEC = BASE + "spec.md"
ERRATA = "2-用例/输入勘误补充-2026-11-05/errata.json"
MAX_BYTES = 4 * 1024 * 1024
SOURCE_SHA256 = {
    MANUAL: "bb7f4ca6fdc759af1f480702b3a3b12e17e9293b0d38a1dbfbbc8ffc1e572d2c",
    DICTIONARY: "83247d79f5ddcdd180e02f184b644f4912731942a2fc58d91f2a06b911d04b41",
    QUESTIONS: "d99d3109e216b8e091d478602fce7cb687b47c40338ce8d016300c9ee7013730",
    TRUTH: "9e6e395fc7b0e5cf60238b8c3ab30fdaa399422fc047f554f0198488156e46d8",
    SPEC: "ef0f822d01b56089bb6fe56f1a9a6bcf7f4a1ee9796689908c8ac04a45c53852",
}
MANUAL_44 = (
    "The MCC is usually represented by a four-digit code, such as 5451 "
    "(Automated Fuel Dispensers) or 5812 (Automotive Parts and Accessories "
    "Stores). The first two digits of the MCC indicate the category, while "
    "the last two digits indicate the subcategory."
)
MANUAL_49 = "Merchant Category Code (MCC): 5521 (Motor Vehicle Dealers - New and Used Cars)"
MANUAL_53 = "You can find a complete list of MCC in the annexed file `merchant_category_codes.csv`."
QUESTION_1305 = (
    "For account type H and the MCC description: Eating Places and Restaurants, "
    "what would be the average fee that the card scheme GlobalCard would charge "
    "for a transaction value of 10 EUR? Provide the answer in EUR and 6 decimals"
)
GUIDELINES_1305 = (
    "Answer must be just a number expressed in EUR rounded to 6 decimals. "
    "If a question does not have a relevant or applicable answer for the task, "
    "please respond with 'Not Applicable'"
)
# mcc, manual line/description, CSV line/index/description, auxiliary mcc.
CONFLICTS = (
    ("5451", 44, "Automated Fuel Dispensers", 497, "495", "Dairy Products Stores", "5542"),
    ("5812", 44, "Automotive Parts and Accessories Stores", 537, "535", "Eating Places and Restaurants", "5533"),
    ("5521", 49, "Motor Vehicle Dealers - New and Used Cars", 501, "499",
     "Car and Truck Dealers (Used Only) - Sales, Service, Repairs, Parts, and Leasing", "5511"),
)
AUXILIARY = {
    "5542": (506, "504", "Automated Fuel Dispensers"),
    "5533": (504, "502", "Auto Parts and Accessories Stores"),
    "5511": (500, "498", "Car and Truck Dealers (New and Used) - Sales, Service, Repairs, Parts, and Leasing"),
}
BOUNDARIES = {
    "old_sources_modified": False,
    "gold_changed": False,
    "historical_scores_changed": False,
    "formal_rows_added": 0,
    "new_product_runs": 0,
    "prior_conflict_priority_rule_established": False,
    "dictionary_policy": "new_derived_local_dictionary_lookup",
    "external_mcc_authority_authenticated": False,
    "historical_product_use": "unknown",
    "scoring_impact": "not_established",
    "future_behavior_unchanged": "not_established",
    "future_input_requires_registration": True,
    "q49_scope_changed": False,
    "q2697_scope_changed": False,
    "new_license_granted": False,
    "legal_compliance_certified": False,
}
LIMITS = [
    "three_examples_of_one_document_label_conflict",
    "auxiliary_codes_do_not_replace_original_codes_or_fee_rules",
    "current_local_dictionary_not_external_authority_or_upstream_correction",
    "no_fee_calculation_regrading_product_run_or_historical_causality",
    "new_explanatory_material_not_authenticated_historical_input",
    "hashes_identify_bytes_not_source_authenticity_or_legal_rights",
]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def strict_json(text):
    require(type(text) is str, "JSON input must be text")
    require(len(text.encode("utf-8")) <= MAX_BYTES, "JSON exceeds byte limit")

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key: " + key)
            result[key] = value
        return result

    def constant(value):
        raise ValueError("non-finite JSON constant: " + value)

    value = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    validate_json(value)
    return value


def validate_json(value):
    if type(value) is dict:
        for key, item in value.items():
            require(type(key) is str, "JSON keys must be strings")
            validate_json(item)
    elif type(value) is list:
        for item in value:
            validate_json(item)
    elif type(value) is float:
        require(math.isfinite(value), "non-finite or overflow JSON number")
    else:
        require(type(value) in (str, int, bool, type(None)), "unsupported JSON type")


def same_typed(actual, expected, at="$"):
    require(type(actual) is type(expected), "type mismatch at " + at)
    if type(expected) is dict:
        require(actual.keys() == expected.keys(), "key mismatch at " + at)
        for key in expected:
            same_typed(actual[key], expected[key], at + "." + key)
    elif type(expected) in (list, tuple):
        require(len(actual) == len(expected), "sequence length mismatch at " + at)
        for index, item in enumerate(expected):
            same_typed(actual[index], item, at + "[" + str(index) + "]")
    else:
        require(actual == expected, "value mismatch at " + at)


def expected_document():
    rows = []
    for code, manual_line, old, csv_line, csv_index, label, other in CONFLICTS:
        other_line, other_index, other_label = AUXILIARY[other]
        rows.append({
            "mcc": code,
            "manual": {"path": MANUAL, "line": manual_line, "description": old},
            "dictionary": {"path": DICTIONARY, "line": csv_line,
                           "csv_index": csv_index, "description": label},
            "auxiliary": {"mcc": other, "path": DICTIONARY, "line": other_line,
                          "csv_index": other_index, "description": other_label,
                          "role": "auxiliary_only_not_replacement"},
            "relationship": "same_code_label_conflict",
        })
    return {
        "schema": "mcc-derived-errata-v1",
        "date": "2026-11-05",
        "case_id": "dabstep-payments-10",
        "conflict_class_count": 1,
        "source_sha256": dict(SOURCE_SHA256),
        "manual_dictionary_reference": {"path": MANUAL, "line": 53, "quote": MANUAL_53},
        "conflicts": rows,
        "q1305": {
            "path": QUESTIONS, "line": 5, "task_id": "1305",
            "mcc_description": "Eating Places and Restaurants", "matched_mcc": "5812",
            "gold": {"path": TRUTH, "line": 48, "pointer": "/gold/1305", "value": "0.123217"},
            "recomputed": False, "correctness": "not_authenticated",
            "historical_effect": "not_established",
        },
        "boundaries": dict(BOUNDARIES),
        "limits": list(LIMITS),
    }


def validate_document(document):
    """Pure semantic/typed validation, deliberately independent of file hashes."""
    validate_json(document)
    same_typed(document, expected_document())


def analyze_sources(raw):
    """Pure fixed-public-source relationship check; no filesystem or hash calls."""
    require(type(raw) is dict and raw.keys() == SOURCE_SHA256.keys(), "source set mismatch")
    for name, content in raw.items():
        require(type(content) is bytes and len(content) <= MAX_BYTES, "invalid source bytes: " + name)
    texts = {name: content.decode("utf-8", errors="strict") for name, content in raw.items()}
    manual = texts[MANUAL].splitlines()
    require(len(manual) >= 53, "manual too short")
    require(manual[43] == MANUAL_44, "manual line 44 changed")
    require(manual[48] == MANUAL_49, "manual line 49 changed")
    require(manual[52].rstrip() == MANUAL_53, "manual dictionary reference changed")

    reader = csv.reader(io.StringIO(texts[DICTIONARY], newline=""), strict=True)
    require(next(reader, None) == ["", "mcc", "description"], "CSV header mismatch")
    wanted = {item[0] for item in CONFLICTS} | set(AUXILIARY)
    found = {}
    for row in reader:
        require(len(row) == 3, "CSV column count mismatch")
        if row[1] in wanted:
            require(row[1] not in found, "duplicate relevant MCC: " + row[1])
            found[row[1]] = (reader.line_num, row[0], row[2])
    require(found.keys() == wanted, "missing relevant dictionary MCC")
    for code, _, _, line, index, label, other in CONFLICTS:
        same_typed(found[code], (line, index, label), "dictionary." + code)
        same_typed(found[other], AUXILIARY[other], "dictionary." + other)

    lines = texts[QUESTIONS].splitlines()
    require(len(lines) == 10, "question line count mismatch")
    question = strict_json(lines[4])
    same_typed(question, {"task_id": "1305", "question": QUESTION_1305,
                          "guidelines": GUIDELINES_1305, "level": "hard"}, "q1305")
    truth = strict_json(texts[TRUTH])
    require(type(truth) is dict and type(truth.get("gold")) is dict, "missing gold mapping")
    same_typed(truth["gold"].get("1305"), "0.123217", "gold.1305")
    truth_lines = texts[TRUTH].splitlines()
    require(len(truth_lines) >= 48 and truth_lines[47].strip() == '"1305": "0.123217",',
            "q1305 gold source line changed")
    spec = texts[SPEC].splitlines()
    require(len(spec) >= 175, "spec too short")
    require("inputs/manual.md" in spec[7], "spec manual reference changed")
    require("6 个 context 数据文件原样使用，未改一字" in spec[119], "spec original-context boundary changed")
    require("判分合同、金标与分数均不变" in spec[174], "spec historical boundary changed")
    result = expected_document()
    validate_document(result)
    return result


def canonical_root(root):
    path = Path(root).absolute()
    require(".." not in path.parts, "root contains parent traversal")
    for ancestor in (path,) + tuple(path.parents):
        require(not ancestor.is_symlink(), "linked root or ancestor")
    require(path.is_dir(), "root is not an existing directory")
    return path.resolve(strict=True)


def safe_file(root, relative):
    require(type(relative) is str and relative != "", "invalid relative path")
    require("\\" not in relative and "\x00" not in relative, "invalid path character")
    rel = PurePosixPath(relative)
    require(bool(rel.parts) and not rel.is_absolute() and all(part not in (".", "..") for part in rel.parts), "unsafe source path")
    require(rel.as_posix() == relative, "non-canonical source path")
    target = root
    for part in rel.parts:
        target = target / part
        require(not target.is_symlink(), "linked source component")
    require(target.resolve(strict=True).is_relative_to(root), "source escaped root")
    return target


def signature(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def read_checked(root, relative):
    path = safe_file(root, relative)
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, "source must be a single-link regular file")
    require(0 <= before.st_size <= MAX_BYTES, "source exceeds byte limit")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        require(signature(os.fstat(fd)) == signature(before), "source changed before read")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(MAX_BYTES + 1)
        require(len(data) <= MAX_BYTES, "source grew beyond byte limit")
        require(signature(os.fstat(fd)) == signature(before), "source changed during read")
    finally:
        os.close(fd)
    require(signature(safe_file(root, relative).lstat()) == signature(before), "source changed after read")
    return data, signature(before)


def collect_sources(root):
    raw, identities = {}, {}
    for relative, expected in SOURCE_SHA256.items():
        content, identity = read_checked(root, relative)
        require(hashlib.sha256(content).hexdigest() == expected, "fixed source SHA mismatch: " + relative)
        raw[relative], identities[relative] = content, identity
    return raw, identities


def ensure_stable(root, raw, identities):
    for relative in SOURCE_SHA256:
        after, identity = read_checked(root, relative)
        require(after == raw[relative] and identity == identities[relative], "source not stable: " + relative)


def derive(root):
    """Read exactly five pinned public sources; return the non-scoring errata."""
    root = canonical_root(root)
    raw, identities = collect_sources(root)
    result = analyze_sources(raw)
    ensure_stable(root, raw, identities)
    return result


def verify(root):
    """Compare typed errata with derived facts, retaining all six file identities."""
    root = canonical_root(root)
    raw, identities = collect_sources(root)
    errata_bytes, errata_identity = read_checked(root, ERRATA)
    document = strict_json(errata_bytes.decode("utf-8", errors="strict"))
    validate_document(document)
    result = analyze_sources(raw)
    same_typed(document, result)
    ensure_stable(root, raw, identities)
    after, identity = read_checked(root, ERRATA)
    require(after == errata_bytes and identity == errata_identity, "errata not stable")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--rebuild", action="store_true", help="derive JSON on stdout only; do not write errata")
    args = parser.parse_args(argv)
    try:
        result = derive(args.root) if args.rebuild else verify(args.root)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
    except (ValueError, OSError, UnicodeError, csv.Error, RecursionError) as error:
        print("MCC errata verification failed: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
