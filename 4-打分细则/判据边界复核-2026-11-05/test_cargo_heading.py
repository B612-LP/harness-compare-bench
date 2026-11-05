"""Synthetic semantics and pinned-source tests; never import/run old code."""
from __future__ import annotations

import ast
import hashlib
import io
import json
from pathlib import Path
import socket
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
C = None


def load_subject():
    """Explicit test setup only: reviewed NEW source, no Loader or pyc cache."""
    path = HERE / "cargo_heading.py"
    namespace = {"__name__": "cargo_heading_under_test", "__file__": str(path)}
    exec(compile(path.read_bytes(), str(path), "exec"), namespace)
    return SimpleNamespace(**namespace)


def inputs():
    # Crosswind 50kt from North, TAS100 East-bound: sin(WCA)=-1/2.
    return {"course_deg": 90, "true_airspeed_kts": 100, "wind_from_deg": 0,
            "wind_speed_kts": 50, "declination_east": 12.8,
            "true_heading_deg": 60, "magnetic_heading_deg": 47.2}


class SemanticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global C
        C = load_subject()

    def test_module_import_whitelist_and_no_dynamic_execution(self):
        # Bounded static assertion, not an OS sandbox or general security proof.
        tree = ast.parse((HERE / "cargo_heading.py").read_bytes())
        allowed = {"__future__", "ast", "hashlib", "json", "math", "pathlib"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(all(alias.name in allowed for alias in node.names))
            elif isinstance(node, ast.ImportFrom):
                self.assertEqual(node.level, 0)
                self.assertIn(node.module, allowed)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, {"exec", "eval", "compile", "__import__"})

    def test_independent_known_wind_triangle(self):
        case = inputs()
        self.assertEqual(C.diagnose_heading(**case)["status"], "consistent")
        expected = C.expected_headings(**{k: v for k, v in case.items() if "heading" not in k})
        self.assertAlmostEqual(expected["true_heading_deg"], 60)
        self.assertAlmostEqual(expected["magnetic_heading_deg"], 47.2)
        opposite = dict(case, wind_from_deg=180, true_heading_deg=120, magnetic_heading_deg=107.2)
        self.assertEqual(C.diagnose_heading(**opposite)["status"], "consistent")

    def test_magnetic_plus_180_diagnostic_only_not_old_checker(self):
        case = inputs()
        case["magnetic_heading_deg"] += 180
        result = C.diagnose_heading(**case)
        self.assertEqual(result["status"], "inconsistent")
        self.assertTrue(result["consistency"]["true_heading_matches_wind"])
        self.assertFalse(result["consistency"]["true_magnetic_relation"])
        self.assertAlmostEqual(result["circular_errors_deg"]["magnetic_heading_deg"], 180)
        # No old evaluate was called; there is deliberately no old-PASS assertion.

    def test_wrong_true_still_differs_from_course(self):
        case = dict(inputs(), true_heading_deg=80, magnetic_heading_deg=67.2)
        self.assertNotEqual(case["true_heading_deg"], case["course_deg"])
        result = C.diagnose_heading(**case)
        self.assertEqual(result["status"], "inconsistent")
        self.assertFalse(result["consistency"]["true_heading_matches_wind"])
        self.assertTrue(result["consistency"]["true_magnetic_relation"])

    def test_declination_sign_and_departure_convention(self):
        case = dict(inputs(), magnetic_heading_deg=72.8)
        self.assertEqual(C.diagnose_heading(**case)["status"], "inconsistent")
        # West declination is negative, hence magnetic=true+abs(declination).
        case["declination_east"] = -12.8
        self.assertEqual(C.diagnose_heading(**case)["status"], "consistent")
        # A different arrival declination does not silently replace departure.
        case = dict(inputs(), magnetic_heading_deg=47.4)
        self.assertEqual(C.diagnose_heading(**case)["status"], "inconsistent")

    def test_zero_and_plus_minus_360_wrapping(self):
        case = dict(inputs(), course_deg=0, wind_speed_kts=0, declination_east=12.8,
                    true_heading_deg=360, magnetic_heading_deg=-12.8)
        self.assertEqual(C.diagnose_heading(**case)["status"], "consistent")
        for key in ("course_deg", "wind_from_deg", "declination_east", "true_heading_deg", "magnetic_heading_deg"):
            for shift in (-720, -360, 360, 720):
                with self.subTest(key=key, shift=shift):
                    changed = dict(case)
                    changed[key] += shift
                    self.assertEqual(C.diagnose_heading(**changed)["status"], "consistent")
        self.assertAlmostEqual(C.circular_error_deg(359.99, .01), .02)
        self.assertEqual(C.circular_error_deg(-180, 180), 0)

    def test_one_decimal_tolerances_and_outside_boundary(self):
        for offset, expected in ((.05, "consistent"), (.05001, "inconsistent")):
            case = dict(inputs(), true_heading_deg=60 + offset, magnetic_heading_deg=47.2 + offset)
            self.assertEqual(C.diagnose_heading(**case)["status"], expected)
        # Opposite rounding errors are each .05, but their relation differs .1.
        case = dict(inputs(), true_heading_deg=60.05, magnetic_heading_deg=47.15)
        result = C.diagnose_heading(**case)
        self.assertEqual(result["status"], "consistent")
        self.assertAlmostEqual(result["circular_errors_deg"]["true_magnetic_relation_deg"], .1)
        self.assertEqual(C.ANGLE_TOLERANCE_DEG, .05)
        self.assertEqual(C.RELATION_TOLERANCE_DEG, .1)

    def test_nonfinite_bool_strings_and_null_are_not_numbers(self):
        for key in inputs():
            for value in (True, False, None, "60", float("nan"), float("inf"), -float("inf"), 10 ** 1000):
                with self.subTest(key=key, value=repr(value)[:30]):
                    with self.assertRaises(ValueError):
                        C.diagnose_heading(**dict(inputs(), **{key: value}))

    def test_impossible_wind_and_invalid_speeds_rejected(self):
        for changes in ({"true_airspeed_kts": 0}, {"true_airspeed_kts": -1},
                        {"wind_speed_kts": -1}, {"wind_speed_kts": 101}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                C.diagnose_heading(**dict(inputs(), **changes))
        # Rotated pure crosswind limits both have physical zero forward motion;
        # a positive floating residual at 270 degrees must not be accepted.
        for course in (90, 270):
            case = dict(inputs(), course_deg=course, wind_speed_kts=100,
                        true_heading_deg=0, magnetic_heading_deg=347.2)
            with self.subTest(course=course), self.assertRaisesRegex(ValueError, "forward ground speed"):
                C.diagnose_heading(**case)

    def test_forward_ground_velocity_tail_head_zero_and_reversed(self):
        # Cardinal course avoids a floating trigonometric near-zero boundary.
        base = dict(inputs(), course_deg=0, true_heading_deg=0, magnetic_heading_deg=347.2)
        # Tailwind, and headwind weaker than TAS, preserve forward course.
        for direction, speed in ((180, 150), (0, 50)):
            with self.subTest(direction=direction, speed=speed):
                case = dict(base, wind_from_deg=direction, wind_speed_kts=speed)
                self.assertEqual(C.diagnose_heading(**case)["status"], "consistent")
        # Equal/stronger headwind: cross=0 is NOT sufficient for a valid course.
        for speed in (100, 150):
            with self.subTest(speed=speed), self.assertRaisesRegex(ValueError, "forward ground speed"):
                C.diagnose_heading(**dict(base, wind_from_deg=0, wind_speed_kts=speed))
        for course in (0, 90, 180, 270):
            case = dict(base, course_deg=course, wind_from_deg=course, wind_speed_kts=100)
            with self.subTest(course=course), self.assertRaisesRegex(ValueError, "forward ground speed"):
                C.diagnose_heading(**case)
        # Margin is a declared numerical support boundary, not precise physics:
        # even a tiny positive resultant is deliberately unsupported.
        self.assertEqual(C.FORWARD_ROUNDOFF_SCALE, 1e-12)
        with self.assertRaisesRegex(ValueError, "unsupported near-zero"):
            C.diagnose_heading(**dict(base, wind_from_deg=0, wind_speed_kts=100 - 5e-11))
        self.assertEqual(C.diagnose_heading(**dict(base, wind_from_deg=0,
                                                  wind_speed_kts=100 - 1e-6))["status"], "consistent")

    def test_static_ast_view_is_not_dynamic_score_evidence(self):
        source = C.safe_file(ROOT, C.BASE + "checker.py").read_text(encoding="utf-8")
        view = C.checker_read_set(source)
        self.assertEqual(view["all_string_lines"]["magnetic_heading_deg"], [99])
        self.assertEqual(view["evaluate_string_lines"]["magnetic_heading_deg"], [])
        self.assertEqual(view["evaluate_string_lines"]["true_heading_deg"], [268])
        # The pure AST helper reports a synthetic new access; it is not ignored.
        changed = source.replace('route = plan.get("route") or []',
                                 'route = plan.get("magnetic_heading_deg") or []')
        self.assertTrue(C.checker_read_set(changed)["evaluate_string_lines"]["magnetic_heading_deg"])
        self.assertTrue(view["not_general_alias_or_dynamic_access_proof"])

    def test_strict_json(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}',
                    b'{"x":-Infinity}', b'{"x":1e999}', b'{"x":[1e999]}', b'\xff'):
            with self.subTest(raw=raw), self.assertRaises((ValueError, UnicodeError)):
                C.parse_json(raw)
        self.assertEqual(C.parse_json(b'{"x": [0, false, null]}'), {"x": [0, False, None]})


class SnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global C
        C = load_subject()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cargo-heading-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for path in C.SOURCE_SHA256:
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(C.safe_file(ROOT, path).read_bytes())

    def test_derive_readonly_no_execution_or_network(self):
        before = {p: (self.root / p).read_bytes() for p in C.SOURCE_SHA256}
        real_open = io.open

        def readonly(file, mode="r", *args, **kwargs):
            if any(letter in mode for letter in "wax+"):
                raise AssertionError("write forbidden")
            return real_open(file, mode, *args, **kwargs)

        with patch("io.open", side_effect=readonly), \
                patch.object(socket, "socket", side_effect=AssertionError("network forbidden")), \
                patch.object(subprocess, "run", side_effect=AssertionError("process forbidden")), \
                patch.object(subprocess, "Popen", side_effect=AssertionError("process forbidden")), \
                patch("builtins.exec", side_effect=AssertionError("exec forbidden")), \
                patch("builtins.eval", side_effect=AssertionError("eval forbidden")):
            result = C.derive(self.root)
        self.assertEqual(len(result["sources"]), 7)
        self.assertEqual([x["diagnostic"]["status"] for x in result["synthetic_examples"]],
                         ["consistent", "inconsistent", "inconsistent"])
        self.assertEqual(result["old_contract_boundary"]["core_denominator_unchanged"], 27)
        self.assertEqual(result["old_contract_boundary"]["threshold_unchanged"], 20)
        self.assertTrue(result["old_contract_boundary"]["no_actual_wrong_pass_experiment"])
        self.assertFalse(result["limitations"]["old_source_executed"])
        self.assertFalse(result["limitations"]["new_grade_or_reward"])
        self.assertEqual(before, {p: (self.root / p).read_bytes() for p in C.SOURCE_SHA256})
        self.assertEqual(C.derive(self.root), result)

    def test_each_source_pin_rejects_tampering_and_missing(self):
        for path in C.SOURCE_SHA256:
            target = self.root / path
            old = target.read_bytes()
            target.write_bytes(old + b"\n")
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "source SHA mismatch"):
                C.derive(self.root)
            target.write_bytes(old)
        target = self.root / (C.BASE + "instruction.md")
        target.unlink()
        with self.assertRaises(ValueError):
            C.derive(self.root)

    def test_coherent_text_reseal_cannot_replace_code_anchor(self):
        path = C.BASE + "inputs/app/data/airports.json"
        data = C.parse_json((self.root / path).read_bytes())
        data["NAN"]["magnetic_declination_east"] = -12.8
        changed = json.dumps(data, ensure_ascii=False).encode("utf-8")
        (self.root / path).write_bytes(changed)
        # A local claimed hash is immaterial; derive uses reviewed code pins.
        (self.root / "claimed-hashes.json").write_text(json.dumps({path: hashlib.sha256(changed).hexdigest()}))
        with self.assertRaisesRegex(ValueError, "source SHA mismatch"):
            C.derive(self.root)

    def test_safe_paths_and_same_bytes_symlink_rejected(self):
        for path in ("", "/etc/passwd", "../escape", "a/../b", "a//b", "./a", "a\\b"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                C.safe_file(self.root, path)
        path = C.BASE + "inputs/app/data/airports.json"
        target = self.root / path
        target.unlink()
        target.symlink_to(ROOT / path)
        with self.assertRaisesRegex(ValueError, "symlink"):
            C.derive(self.root)
        alias = self.root / "linked-inputs"
        alias.symlink_to(self.root / "2-用例", target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            C.safe_file(self.root, "linked-inputs/tb-cargo-plan/instruction.md")
        # The original is never modified by this symlink fixture.
        self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), C.SOURCE_SHA256[path])


if __name__ == "__main__":
    unittest.main()
