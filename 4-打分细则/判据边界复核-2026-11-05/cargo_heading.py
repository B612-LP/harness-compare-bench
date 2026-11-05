"""Non-scoring Cargo heading semantics; reads public sources, never executes them.

The pure functions accept mathematical, synthetic inputs, not product plans.
No CLI, import-time I/O, flight-plan runner, historical regrade or new reward.
Python 3.9+ standard library only.
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
from pathlib import Path, PurePosixPath

BASE = "2-用例/tb-cargo-plan/"
SOURCE_SHA256 = {
    BASE + "instruction.md": "e350cce533227c47e76199a31070d7881c6d9b182ed84631a16b0b7ac7e4e227",
    BASE + "spec.md": "8a94143a8333254fe5e57f7d47ea3708bd7837dd674c4189343c245f514758ea",
    BASE + "checker.py": "d84b1111a79000a38b97f602b533a344b8e2562abda9ec44474290701a75c677",
    BASE + "inputs/app/data/airports.json": "25bb33e33712e70b98158c14d7207fb17fdf870c678973b88a2b1ce85d65bde2",
    BASE + "inputs/app/navigation.py": "b7932e8f60649e22f106b3bf5b6c2542971a76d07a0f6202802651aebac1494e",
    BASE + "inputs/app/dispatch.py": "7a435b3a743a380728f41a4a4d2b25ff5b0305ca4ffdfa83162d72589a657bd8",
    "2-用例/交付合同-2026-11-05/cargo-instruction.md": "a1b7877e360c3fabb134effdd5f28a8aa6a9f3662b81216971383f2d4d873ff3",
}
# One decimal output: each independently rounded angle differs by at most .05°.
# Comparing TWO rounded angles in the true-minus-declination relation allows .1°.
ANGLE_TOLERANCE_DEG = 0.05
RELATION_TOLERANCE_DEG = 0.1
FLOAT_EPSILON_DEG = 1e-9
# Numerical support domain only, NOT an aviation standard or physical deadband.
FORWARD_ROUNDOFF_SCALE = 1e-12


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def number(value, label: str) -> float:
    require(type(value) in (int, float), "finite real number required: " + label)
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError("finite real number required: " + label) from exc
    require(math.isfinite(result), "finite real number required: " + label)
    return result


def parse_json(raw: bytes):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key: " + key)
            result[key] = value
        return result

    def reject(value):
        raise ValueError("non-finite JSON number: " + value)

    value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=reject)

    def walk(item):
        if type(item) is float:
            require(math.isfinite(item), "non-finite JSON number")
        elif type(item) is list:
            for child in item:
                walk(child)
        elif type(item) is dict:
            for child in item.values():
                walk(child)
    walk(value)
    return value


def safe_file(root: Path, relative: str) -> Path:
    require(type(relative) is str and "\\" not in relative, "unsafe source path")
    path = PurePosixPath(relative)
    require(bool(relative) and not path.is_absolute() and path.as_posix() == relative
            and all(part not in (".", "..") for part in path.parts), "unsafe source path")
    root = Path(root).resolve(strict=True)
    target = root
    for part in path.parts:
        target = target / part
        require(not target.is_symlink(), "symlink source path: " + relative)
    require(target.is_file() and root in target.resolve().parents, "missing/outside source: " + relative)
    return target


def circular_error_deg(actual, expected) -> float:
    """Smallest angular distance; ±360 and 0/360 represent the same direction."""
    a, b = number(actual, "actual angle") % 360, number(expected, "expected angle") % 360
    return abs((a - b + 180) % 360 - 180)


def expected_headings(*, course_deg, true_airspeed_kts, wind_from_deg,
                      wind_speed_kts, declination_east) -> dict:
    """Wind-FROM, true-degree course; subtract DEPARTURE east declination.

    Solve cross-track cancellation independently of the old code. TAS here is
    the supplied exact mathematical speed, NOT a one-decimal product output.
    It does not verify TAS against aircraft/ISA, select weather, routes or a plan.
    Impossible crosswind is rejected rather than silently clamped to ±90°.
    The resultant velocity must move FORWARD along the intended course: merely
    cancelling cross-track wind is insufficient with zero/reversed ground speed.
    Supported forward speed must exceed 1e-12*max(TAS, wind speed, 1) kt.
    This roundoff margin also rejects tiny positive speeds as unsupported; it is
    not an aviation standard or an exact physical near-zero classification.
    """
    course = number(course_deg, "course_deg") % 360
    tas = number(true_airspeed_kts, "true_airspeed_kts")
    wind_from = number(wind_from_deg, "wind_from_deg") % 360
    speed = number(wind_speed_kts, "wind_speed_kts")
    declination = number(declination_east, "declination_east") % 360
    require(tas > 0 and speed >= 0, "TAS must be positive and wind speed nonnegative")
    c, w = math.radians(course), math.radians(wind_from)
    # Wind points TO (-sin(w), -cos(w)); right-of-course is (cos(c), -sin(c)).
    wind_east, wind_north = -speed * math.sin(w), -speed * math.cos(w)
    cross = -(wind_east * math.cos(c) - wind_north * math.sin(c)) / tas
    require(abs(cross) <= 1, "crosswind exceeds supplied TAS")
    # sqrt is the nonnegative forward-air branch of TAS*cos(asin(cross)).
    along = (tas * math.sqrt(1 - cross * cross)
             + wind_east * math.sin(c) + wind_north * math.cos(c))
    margin = FORWARD_ROUNDOFF_SCALE * max(tas, speed, 1.0)
    require(math.isfinite(along) and along > margin,
            "unsupported near-zero/nonpositive/nonfinite forward ground speed")
    true = (course + math.degrees(math.asin(cross))) % 360
    return {"true_heading_deg": true,
            "magnetic_heading_deg": (true - declination) % 360}


def diagnose_heading(*, course_deg, true_airspeed_kts, wind_from_deg,
                     wind_speed_kts, declination_east,
                     true_heading_deg, magnetic_heading_deg) -> dict:
    """Pure supplementary consistency diagnostic; never a scoring assertion."""
    expected = expected_headings(course_deg=course_deg, true_airspeed_kts=true_airspeed_kts,
                                 wind_from_deg=wind_from_deg, wind_speed_kts=wind_speed_kts,
                                 declination_east=declination_east)
    true = number(true_heading_deg, "true_heading_deg")
    magnetic = number(magnetic_heading_deg, "magnetic_heading_deg")
    declination = number(declination_east, "declination_east") % 360
    errors = {
        "true_heading_deg": circular_error_deg(true, expected["true_heading_deg"]),
        "magnetic_heading_deg": circular_error_deg(magnetic, expected["magnetic_heading_deg"]),
        "true_magnetic_relation_deg": circular_error_deg(magnetic, (true % 360 - declination) % 360),
    }
    consistent = {
        "true_heading_matches_wind": errors["true_heading_deg"] <= ANGLE_TOLERANCE_DEG + FLOAT_EPSILON_DEG,
        "magnetic_heading_matches_wind_and_departure_declination":
            errors["magnetic_heading_deg"] <= ANGLE_TOLERANCE_DEG + FLOAT_EPSILON_DEG,
        "true_magnetic_relation": errors["true_magnetic_relation_deg"] <= RELATION_TOLERANCE_DEG + FLOAT_EPSILON_DEG,
    }
    return {"scope": "synthetic_mathematical_consistency_only_non_scoring",
            "status": "consistent" if all(consistent.values()) else "inconsistent",
            "expected_unrounded": expected, "circular_errors_deg": errors,
            "consistency": consistent}


def checker_read_set(source: str) -> dict:
    """Literal field-string occurrences, NOT general information-flow analysis.

    Only ast.parse/ast.literal_eval are used. No old function is imported/called.
    Exact source identity is checked independently by derive() before this view.
    """
    tree = ast.parse(source)
    evaluations = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "evaluate"]
    require(len(evaluations) == 1, "evaluate AST missing/ambiguous")
    evaluate = evaluations[0]
    fields = ("magnetic_heading_deg", "true_heading_deg")
    lines = lambda node, field: sorted(n.lineno for n in ast.walk(node)
                                      if isinstance(n, ast.Constant) and n.value == field)
    assignments = [node for node in tree.body if isinstance(node, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == "PLAN_KEYS_LEG" for t in node.targets)]
    require(len(assignments) == 1, "PLAN_KEYS_LEG AST missing/ambiguous")
    required = ast.literal_eval(assignments[0].value)
    require(type(required) is list and all(type(v) is str for v in required), "required leg keys not literal strings")
    return {"analysis_kind": "literal_field_string_read_set_on_pinned_source_only",
            "all_string_lines": {field: lines(tree, field) for field in fields},
            "evaluate_string_lines": {field: lines(evaluate, field) for field in fields},
            "magnetic_field_is_required_key": "magnetic_heading_deg" in required,
            "not_general_alias_or_dynamic_access_proof": True}


def derive(root: Path) -> dict:
    """Read seven pinned public sources and derive a non-scoring boundary view."""
    raw = {}
    sources = []
    for path, digest in sorted(SOURCE_SHA256.items()):
        value = safe_file(root, path).read_bytes()
        require(hashlib.sha256(value).hexdigest() == digest, "source SHA mismatch: " + path)
        raw[path] = value
        sources.append({"path": path, "sha256": digest, "bytes": len(value)})
    static = checker_read_set(raw[BASE + "checker.py"].decode("utf-8"))
    require(static["all_string_lines"]["magnetic_heading_deg"] == [99]
            and static["evaluate_string_lines"]["magnetic_heading_deg"] == []
            and static["evaluate_string_lines"]["true_heading_deg"] == [268]
            and static["magnetic_field_is_required_key"], "pinned checker AST boundary changed")
    airports = parse_json(raw[BASE + "inputs/app/data/airports.json"])
    require(type(airports) is dict, "airport object required")
    declinations = {}
    for code in ("NAN", "SUV", "TBU", "APW", "FUN"):
        require(type(airports.get(code)) is dict, "airport missing: " + code)
        declinations[code] = number(airports[code].get("magnetic_declination_east"), code + " declination")
    # Synthetic inputs, not canonical routes/weather, captures or product plans.
    inputs = {"course_deg": 90, "true_airspeed_kts": 100, "wind_from_deg": 0,
              "wind_speed_kts": 20, "declination_east": declinations["NAN"]}
    expected = expected_headings(**inputs)
    correct = {"true_heading_deg": round(expected["true_heading_deg"], 1),
               "magnetic_heading_deg": round(expected["magnetic_heading_deg"], 1)}
    wrong_mag = dict(correct, magnetic_heading_deg=(correct["magnetic_heading_deg"] + 180) % 360)
    wrong_true = {"true_heading_deg": (correct["true_heading_deg"] + 30) % 360,
                  "magnetic_heading_deg": (correct["magnetic_heading_deg"] + 30) % 360}
    examples = []
    for name, angles in (("rounded_correct", correct), ("magnetic_plus_180", wrong_mag),
                         ("true_and_magnetic_plus_30_still_not_course", wrong_true)):
        examples.append({"name": name, "inputs": dict(inputs, **angles),
                         "diagnostic": diagnose_heading(**inputs, **angles)})
    return {
        "case": "tb-cargo-plan", "kind": "supplementary_heading_semantics_non_scoring",
        "sources": sources, "static_checker_view": static,
        "departure_declination_east_deg": declinations,
        "old_contract_boundary": {
            "core_denominator_unchanged": 27, "threshold_unchanged": 20,
            "spec_heading_wind_corrected": "true heading differs from course; not numeric wind-heading equality",
            "magnetic_value_boundary": "required key; no magnetic field-string read in pinned evaluate",
            "static_invariance_only": "With all other ordinary JSON inputs unchanged, changing only finite numeric magnetic values does not change the pinned checks' read inputs; old evaluate was NOT run.",
            "no_claim_of_checker_spec_breach": True,
            "no_actual_wrong_pass_experiment": True, "no_historical_score_error_established": True,
        },
        "supplementary_math": {
            "wind_convention": "wind FROM and course in true degrees",
            "forward_domain": "cross-track cancellation AND along-track velocity > 1e-12*max(TAS,wind speed,1) kt; zero/reversed and tiny-positive unsupported boundaries rejected",
            "forward_roundoff_scale": FORWARD_ROUNDOFF_SCALE,
            "forward_margin_is_not_aviation_standard_or_exact_near_zero_classification": True,
            "magnetic_convention": "(true heading - DEPARTURE east declination) modulo 360",
            "angle_error": "smallest circular distance; ±360/0-degree wrapping equivalent",
            "reference_tolerance_deg": ANGLE_TOLERANCE_DEG,
            "rounded_true_magnetic_relation_tolerance_deg": RELATION_TOLERANCE_DEG,
            "floating_epsilon_deg": FLOAT_EPSILON_DEG,
            "tolerance_basis": "Each one-decimal angle may round by .05 degree; two rounded angles differ by at most .1 degree in their relation. Supplied synthetic TAS/course/wind are exact inputs, not rounded plan values.",
            "not_a_plan_or_aviation_validator": True,
        },
        "synthetic_examples": examples,
        "limitations": {"old_source_executed": False, "product_outputs_read": False,
                        "new_grade_or_reward": False, "historical_regrade": False,
                        "new_product_samples": 0, "private_raw_authenticated": False},
    }
