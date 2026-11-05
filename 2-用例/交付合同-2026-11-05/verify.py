#!/usr/bin/env python3
"""Static delivery-contract audit. Never imports/runs legacy checker, SQL or submissions."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

PACK = Path("2-用例/交付合同-2026-11-05")
PINS = {
    "contract.json": "06fd5edfd29e2c8b97038acc32297624c66e643bfa0c51ba8b6d4ad5d7f535b2",
    "source-bindings.json": "e69e25cb06f9cbe96fed35e07967c086bd327fad09f0a9a620108f41033dba13",
    "currentpack.json": "f6d09c00948800922ad0994da84f32e8155e475c08731c652f77f24bf483dacf",
    "bird-instruction.md": "0d0e58910bd349ac56f20277709f6d6899df8a9200e4852411c359e4761cdafb",
    "cargo-instruction.md": "a1b7877e360c3fabb134effdd5f28a8aa6a9f3662b81216971383f2d4d873ff3",
}
QIDS = {28, 36, 62, 83, 87, 12, 23, 24, 25, 26, 27, 31, 5, 11, 17}
SQL_LITERAL = re.compile(r"'(?:[^']|'')*'")


def safe_path(root, relative):
    """Reject traversal/absolute paths and symlinks, including parent symlinks."""
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        raise ValueError("unsafe path: " + str(relative))
    root = Path(root).resolve()
    path = root
    for part in rel.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError("symlink not allowed: " + str(relative))
    path.resolve().relative_to(root)
    return path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def no_duplicate_keys(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate JSON key: " + key)
        obj[key] = value
    return obj


def decode_json(text):
    def reject_constant(value):
        raise ValueError("nonfinite JSON constant: " + value)
    return json.loads(text, object_pairs_hook=no_duplicate_keys,
                      parse_constant=reject_constant)


def bird_delivery_errors(text):
    """Illustrative format-only preflight; NEVER SQL correctness or scoring.

    Uses synthetic strings in tests. Integer IDs and duplicate-key refusal are
    recommended canonical delivery, not a retrospective replacement for the
    old checker's permissive JSON parser. The two B2 gates match its exact-key
    and single-quote-mask rules. Blank lines are ignored as in old parsing.
    """
    errors, seen = [], []
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) != 15:
        errors.append("nonempty_lines")
    for index, line in enumerate(lines, 1):
        try:
            row = decode_json(line)
        except (ValueError, TypeError):
            errors.append("json:" + str(index))
            continue
        if not isinstance(row, dict) or set(row) != {"question_id", "sql"}:
            errors.append("exact_row_keys:" + str(index))
            continue
        qid, sql = row["question_id"], row["sql"]
        if type(qid) is not int or qid not in QIDS:
            errors.append("question_id:" + str(index))
        else:
            seen.append(qid)
        if not isinstance(sql, str):
            errors.append("sql_type:" + str(index))
        elif "--" in SQL_LITERAL.sub("''", sql):
            errors.append("sql_comment:" + str(index))
    if len(seen) != 15 or set(seen) != QIDS:
        errors.append("question_coverage")
    return errors


def verify(root):
    """Read-only hash and manifest closure, anchored by this version of verifier."""
    root = Path(root).resolve()
    errors, contents, checked = [], {}, 0
    for name, expected in PINS.items():
        try:
            data = safe_path(root, PACK / name).read_bytes()
            if digest(data) != expected:
                errors.append("package_sha256:" + name)
            contents[name] = data.decode("utf-8")
        except (OSError, ValueError, UnicodeError) as exc:
            errors.append("package_read:" + name + ":" + str(exc))
    # Do not trust or follow altered metadata, even if the attacker re-seals it.
    if errors:
        return result(errors, checked)
    try:
        contract = decode_json(contents["contract.json"])
        bindings = decode_json(contents["source-bindings.json"])
        entry = decode_json(contents["currentpack.json"])
        for document in (bindings, entry):
            if document["contract_id"] != contract["contract_id"]:
                errors.append("contract_id")
        source_hashes = {}
        for source in bindings["sources"]:
            rel, expected = source["path"], source["sha256"]
            if rel in source_hashes:
                errors.append("duplicate_source:" + rel)
                continue
            source_hashes[rel] = expected
            path = safe_path(root, rel)
            if not path.is_file() or digest(path.read_bytes()) != expected:
                errors.append("legacy_source_sha256:" + rel)
            checked += 1
        destinations_total = 0
        for case in entry["cases"]:
            prompt = case["agent_instruction"]
            if prompt not in PINS or digest(contents[prompt].encode("utf-8")) != case["agent_instruction_sha256"]:
                errors.append("instruction_binding:" + case["case_id"])
            if case["external_spec_required"] is not False:
                errors.append("external_spec_required")
            if case["evaluator_visibility"] != "not-agent-visible" or case["evaluator_source"] not in source_hashes:
                errors.append("evaluator_binding")
            destinations = set()
            for item in case["staging"]:
                source, dest = item["source"], item["destination"]
                safe_path(root, dest)
                if source not in source_hashes or not dest.startswith("inputs/") or dest in destinations:
                    errors.append("staging_binding:" + case["case_id"])
                if Path(dest).name in {"spec.md", "checker.py", "truth.json"} or "/solution/" in source or "/reference/" in source:
                    errors.append("evaluator_leak:" + source)
                destinations.add(dest)
            destinations_total += len(destinations)
        if checked != 33 or destinations_total != 11:
            errors.append("inventory_count")
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as exc:
        errors.append("metadata_or_source:" + str(exc))
    return result(errors, checked)


def result(errors, checked):
    return {"pass": not errors, "contract_id": "delivery-clarification-2026-11-05.1",
            "legacy_sources_checked": checked, "package_files_pinned": len(PINS),
            "status": "prospective-unrun", "audit": "static-source-prompt-contract-only",
            "sql_checker_candidate_execution": False, "historical_scores_changed": False,
            "limitations": ["not a task scorer", "not a new product run",
                            "hashes do not authenticate private originals or verifier itself"],
            "errors": errors}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2],
                        help="repository root; defaults to this file's repository")
    args = parser.parse_args(argv)
    report = verify(args.root)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
