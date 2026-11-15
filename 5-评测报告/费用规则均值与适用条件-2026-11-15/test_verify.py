#!/usr/bin/env python3
"""Standard-library tests; run with both python -B and python -B -O."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal

import verify as v


class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = v.read_sources()

    def rule(self, credit=True, fixed=Decimal("0.1"), rate=0, scheme="GlobalCard"):
        return {"card_scheme": scheme, "is_credit": credit, "fixed_amount": fixed, "rate": rate}

    def test_real_aggregate_and_output_shape(self):
        result = v.report()
        self.assertEqual(result["groups"]["true"], {"count": 123, "sum_eur": "14.473", "mean_eur_18dp_half_up": "0.117666666666666667"})
        self.assertEqual(result["groups"]["null"], {"count": 21, "sum_eur": "2.826", "mean_eur_18dp_half_up": "0.134571428571428571"})
        self.assertEqual(result["groups"]["combined"]["count"], 144)
        self.assertEqual(result["groups"]["combined"]["sum_eur"], "17.299")
        self.assertEqual(result["groups"]["combined"]["mean_eur_6dp_half_up"], "0.120132")
        self.assertEqual(result["public_source_sha256"], v.HASHES)
        self.assertNotIn('"ID"', json.dumps(result))

    def test_null_included_false_and_other_scheme_excluded(self):
        data = [self.rule(True, Decimal("0.1"), 10), self.rule(None, Decimal("0.3"), 20),
                self.rule(False, Decimal("9")), self.rule(None, Decimal("9"), scheme="Other")]
        g = v.aggregate_rules(data)
        self.assertEqual(g["true"], {"count": 1, "sum": Decimal("0.110")})
        self.assertEqual(g["null"], {"count": 1, "sum": Decimal("0.320")})
        self.assertNotEqual((g["true"]["sum"] / g["true"]["count"]),
                            (g["true"]["sum"] + g["null"]["sum"]) / 2)

    def test_exact_fee_formula_vary_amount_and_rate(self):
        g = v.aggregate_rules([self.rule(True, Decimal("0.12345"), 37)])
        self.assertEqual(g["true"]["sum"], Decimal("0.16045"))

    def test_invalid_types_and_values(self):
        cases = [self.rule(1), self.rule(0), self.rule("true"), self.rule([], Decimal("0.1")),
                 self.rule(True, 0.1), self.rule(True, 1), self.rule(True, Decimal("NaN")),
                 self.rule(True, Decimal("Infinity")), self.rule(True, Decimal("-0.1")),
                 self.rule(True, Decimal("0.1"), True), self.rule(True, Decimal("0.1"), 1.0),
                 self.rule(True, Decimal("0.1"), -1), self.rule(True, scheme=1), {}, None]
        for rule in cases:
            with self.subTest(kind=type(rule).__name__), self.assertRaises(v.AuditError):
                v.aggregate_rules([rule])
        for rules in ([], None, {}):
            with self.assertRaises(v.AuditError):
                v.aggregate_rules(rules)

    def test_rounding_and_count_validation(self):
        self.assertEqual(v.average(Decimal("1.2345675"), 1, 6), Decimal("1.234568"))
        self.assertEqual(v.average(Decimal("1.23456749"), 1, 6), Decimal("1.234567"))
        self.assertEqual(v.average(Decimal("0.5"), 3, 6), Decimal("0.166667"))
        for total, count, places in [(Decimal(1), 0, 6), (Decimal(1), True, 6),
                                     (0.1, 1, 6), (Decimal("NaN"), 1, 6),
                                     (Decimal(1), 1, True)]:
            with self.assertRaises(v.AuditError):
                v.average(total, count, places)

    def test_synthetic_rule_vs_transaction_weight(self):
        rules = [{"match": "A", "fee": Decimal("0.1")}, {"match": "B", "fee": Decimal("0.3")}]
        s = v.synthetic(rules, ["A", "A", "B"])
        self.assertEqual(s, {"rule_count": 2, "rule_sum": Decimal("0.4"),
                             "transaction_count": 3, "transaction_sum": Decimal("0.5")})
        self.assertEqual(v.average(s["rule_sum"], 2, 6), Decimal("0.200000"))
        self.assertEqual(v.average(s["transaction_sum"], 3, 6), Decimal("0.166667"))
        self.assertNotEqual(s["rule_sum"] * 3, s["transaction_sum"] * 2)
        balanced = v.synthetic(rules, ["A", "B"])
        self.assertEqual(balanced["rule_sum"] * balanced["transaction_count"],
                         balanced["transaction_sum"] * balanced["rule_count"])
        for bad_rules, txs in [(rules + [rules[0]], ["A"]), (rules, ["C"]), (rules, []),
                               ([{"match": "A", "fee": 0.1}], ["A"]), (rules, [1])]:
            with self.assertRaises(v.AuditError):
                v.synthetic(bad_rules, txs)

    def test_hash_pins_each_source_and_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for name, content in self.sources.items():
                path = base / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            self.assertEqual(v.read_sources(base), self.sources)
            for name, content in self.sources.items():
                path = base / name
                path.write_bytes(content + b" ")
                with self.subTest(source=name), self.assertRaises(v.AuditError):
                    v.read_sources(base)
                path.write_bytes(content)
            (base / "spec.md").unlink()
            with self.assertRaises(v.AuditError):
                v.read_sources(base)

    def test_gold_question_and_definition_mutations_rejected(self):
        mutations = [
            ("truth.json", b'"1273": "0.120132"', b'"1273": "0.120133"'),
            ("truth.json", b'"1273": "0.120132"', b'"1273": 0.120132'),
            ("solution/answers.jsonl", b'"answer": "0.120132"', b'"answer": "0.120133"'),
            ("inputs/questions.jsonl", b'transaction value of 10 EUR?', b'transaction value of 20 EUR?'),
            ("inputs/manual.md", b'rate * transaction_value / 10000', b'rate * transaction_value / 100'),
            ("inputs/manual.md", b'If a field is set to null', b'If a field is set to empty'),
            ("spec.md", 'is_credit ∈ {true, null}'.encode(), 'is_credit ∈ {true}'.encode()),
        ]
        for name, old, new in mutations:
            with self.subTest(source=name):
                sources = dict(self.sources)
                self.assertIn(old, sources[name])
                sources[name] = sources[name].replace(old, new)
                with self.assertRaises(v.AuditError):
                    v.validate_sources(sources)

    def test_json_strictness(self):
        for raw in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', '{bad}'):
            with self.assertRaises(v.AuditError):
                v.parse_json(raw)
        self.assertEqual(v.parse_json('{"x":0.1}')["x"], Decimal("0.1"))

    def test_cli_normal_and_optimized_and_no_output_path(self):
        script = Path(v.__file__).resolve()
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        with tempfile.TemporaryDirectory() as tmp:
            for mode in ([], ["-O"]):
                run = subprocess.run([sys.executable, "-B", *mode, str(script)],
                                     capture_output=True, text=True, env=env, check=False)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(json.loads(run.stdout)["groups"]["combined"]["mean_eur_6dp_half_up"], "0.120132")
                target = Path(tmp) / "do-not-overwrite"
                target.write_text("original", encoding="utf-8")
                run = subprocess.run([sys.executable, "-B", *mode, str(script), str(target)],
                                     capture_output=True, text=True, env=env, check=False)
                self.assertNotEqual(run.returncode, 0)
                self.assertEqual(target.read_text(encoding="utf-8"), "original")


if __name__ == "__main__":
    unittest.main()
