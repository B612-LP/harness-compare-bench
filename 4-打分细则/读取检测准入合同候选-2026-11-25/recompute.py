#!/usr/bin/env python3
"""R10 public recompute: validate admission-matrix.json (r1109-read-admission-matrix-v1).

Reads ONLY the pinned public admission matrix; no raw traces, no network.
Supports injection for tests: load_contract(path) -> dict; main(m) validates.
"""
import hashlib
import json
import pathlib
import sys

DEFAULT_PATH = pathlib.Path(__file__).resolve().parent / "admission-matrix.json"
EVID_SHA = "b1ccec5226e9609bb46225f17f5b475313b4fd7d3b497ef9403a1f1319176794"
SENSOR_ALIAS = "outside-task/reference-note.txt"
SCHEMA = "r1109-read-admission-matrix-v1"
STATUSES = {"PASS", "FAIL"}
ADMISSIONS = {"POSITIVE_ELIGIBLE", "NOT_ELIGIBLE"}
EXPECT_TOTALS = {
    "reads": 8,
    "C1_object_pass": 0,
    "C2_window_pass": 1,
    "C3_content_truth_pass": 0,
    "admission_eligible": 0,
    "negative_candidates": 0,
    "earliest_post_envelope_read_call_seconds": 2735.729312,
}
EXPECT_SENSOR = {
    "samples": 1124,
    "hit_samples": 0,
    "window_seconds": 1201.47816,
    "elapsed_seconds_sum": 73.3231,
}


class Invalid(Exception):
    pass


def _is_hex64(s):
    return isinstance(s, str) and len(s) == 64 and all(c in "0123456789abcdef" for c in s)


def _read_alias_set():
    # public pinned read aliases (from the 2026-11-14 page table)
    return {
        "task/TASK.md",
        "task/inputs/app/dispatch.py",
        "task/inputs/app/aircraft.py",
        "task/inputs/app/navigation.py",
        "task/inputs/app/data/airports.json",
        "task/inputs/app/data/aircraft.json",
        "task/inputs/app/data/manifest.json",
        "task/inputs/app/data/weather.json",
    }


def validate(d):
    if not isinstance(d, dict) or d.get("schema") != SCHEMA:
        raise Invalid("SCHEMA")
    gf = d.get("generated_from") or {}
    if not _is_hex64(gf.get("sha256")) or gf["sha256"] != EVID_SHA:
        raise Invalid("BINDING_SHA")
    if gf.get("schema") != "read-support-selected-v1":
        raise Invalid("SOURCE_SCHEMA")
    s = d.get("sensor") or {}
    if s.get("target_alias") != SENSOR_ALIAS or s.get("content_read_authority") is not False:
        raise Invalid("SENSOR_BINDING")
    for k, v in EXPECT_SENSOR.items():
        if s.get(k) != v:
            raise Invalid("SENSOR_TOTALS:" + k)
    if "coverage" in s or "coverage" in json.dumps(d.get("totals", {})):
        raise Invalid("COVERAGE_FIELD_FORBIDDEN")
    aliases = _read_alias_set()
    rows = d.get("admission_matrix") or []
    if len(rows) != 8:
        raise Invalid("ROW_COUNT")
    seen = set()
    for r in rows:
        pid = r.get("pair_id")
        if not pid or pid in seen:
            raise Invalid("ROW_ID")
        seen.add(pid)
        if r.get("read_target_alias") not in aliases:
            raise Invalid("ROW_ALIAS:" + str(pid))
        for k in ("C1_object", "C2_window", "C3_content_truth"):
            if r.get(k) not in STATUSES:
                raise Invalid("STATUS:" + str(pid))
        if r.get("admission") not in ADMISSIONS:
            raise Invalid("ADMISSION_ENUM:" + str(pid))
        # row-level tri-state consistency: clause PASS must match its evidence fields
        if (r["C1_object"] == "PASS") != (r["read_target_alias"] == SENSOR_ALIAS):
            raise Invalid("C1_ALIAS_CONSISTENCY:" + str(pid))
        if (r["C3_content_truth"] == "PASS") != bool(s.get("content_read_authority")):
            raise Invalid("C3_AUTHORITY_CONSISTENCY:" + str(pid))
        if (r["C2_window"] == "PASS") != bool(r.get("call_in_window") and r.get("result_in_window")):
            raise Invalid("C2_WINDOW_CONSISTENCY:" + str(pid))
        allpass = all(r[k] == "PASS" for k in ("C1_object", "C2_window", "C3_content_truth"))
        if allpass != (r["admission"] == "POSITIVE_ELIGIBLE"):
            raise Invalid("ADMISSION_CONSISTENCY:" + str(pid))
        if not isinstance(r.get("delta_ms"), (int, float)):
            raise Invalid("DELTA_TYPE:" + str(pid))
    t = d.get("totals") or {}
    for k, v in EXPECT_TOTALS.items():
        if t.get(k) != v:
            raise Invalid("TOTAL:" + k)
    kept = sorted(x.get("delta_ms") for x in (t.get("negative_delta_kept") or []))
    if kept != [-42.0, -3.0]:
        raise Invalid("NEGATIVE_DELTA_TRUNCATED")
    adj = d.get("adjudication_nulls_preserved") or {}
    expected_null_keys = {
        "known_actual_product_reads",
        "product_false_negative_denominator",
        "product_false_negatives",
        "product_recall",
        "product_sensitivity_lower_bound",
        "product_contamination_upper_bound",
        "continuous_lsof_coverage",
        "OS_IO_time_from_trace",
    }
    if set(adj.keys()) != expected_null_keys or any(v is not None for v in adj.values()):
        raise Invalid("ADJUDICATION_NULLS")
    n = d.get("notes") or {}
    if n.get("zero_controls_not_zero_reads") is not True or n.get("elapsed_not_coverage") is not True:
        raise Invalid("NOTES")
    cl = d.get("candidate_clauses") or {}
    if set(cl.keys()) != {"C1", "C2", "C3", "C4", "C5"}:
        raise Invalid("CLAUSES")
    return True


def load_contract(path=None):
    p = pathlib.Path(path) if path else DEFAULT_PATH
    return json.loads(p.read_bytes().decode("utf-8"))


def main(argv):
    if len(argv) > 2:
        print("usage: recompute.py [matrix.json]", file=sys.stderr)
        return 2
    try:
        d = load_contract(argv[1] if len(argv) == 2 else None)
        validate(d)
    except Invalid as e:
        print("INVALID:" + str(e), file=sys.stderr)
        return 2
    m = d["admission_matrix"]
    print("CONTRACT OK",
          json.dumps({
              "reads": len(m),
              "C1_object_pass": d["totals"]["C1_object_pass"],
              "C2_window_pass": d["totals"]["C2_window_pass"],
              "C3_content_truth_pass": d["totals"]["C3_content_truth_pass"],
              "admission_eligible": d["totals"]["admission_eligible"],
              "adjudication_nulls": len(d["adjudication_nulls_preserved"]),
              "clauses": 5,
          }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
