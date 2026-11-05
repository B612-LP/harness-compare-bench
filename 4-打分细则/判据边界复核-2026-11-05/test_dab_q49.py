"""Synthetic semantics and separately pinned-source regression, not product runs."""

import ast
import csv
import types
import io
import json
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).resolve()
ROOT = HERE.parents[2]
MODULE_PATH = HERE.with_name("dab_q49.py")
MODULE = None


class ReviewedModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Explicit test setup only: current new source bytes, never a pyc Loader.
        global MODULE
        source = MODULE_PATH.read_bytes()
        module = types.ModuleType("_reviewed_dab_q49")
        module.__file__ = str(MODULE_PATH)
        exec(compile(source, str(MODULE_PATH), "exec", dont_inherit=True), module.__dict__)
        MODULE = module


def fixture(rows, extras=False):
    output = io.StringIO(newline="")
    columns = ["ip_country", "eur_amount", "has_fraudulent_dispute"]
    if extras:
        columns += ["issuing_country", "merchant", "is_refused_by_adyen", "email_address"]
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(columns)
    writer.writerows(rows)
    return output.getvalue()


def by_country(view):
    return {row["ip_country"]: row for row in view["by_ip_country"]}


class PureSemantics(ReviewedModuleTests):
    def test_counts_and_volume_rank_can_reverse(self):
        view = MODULE.aggregate_payments(fixture([
            ["NL", "1", "True"], ["NL", "1", "True"], ["NL", "98", "False"],
            ["BE", "9", "True"], ["BE", "1", "False"],
        ]))
        self.assertEqual(view["highest_fraud_count"], ["NL"])
        self.assertEqual(view["highest_count_ratio"], ["NL"])
        self.assertEqual(view["highest_monetary_volume_ratio"], ["BE"])
        self.assertEqual(by_country(view)["BE"]["monetary_volume_ratio"], "0.9")

    def test_absolute_fraud_volume_is_not_fraud_rate(self):
        view = MODULE.aggregate_payments(fixture([
            ["NL", "100", "True"], ["NL", "900", "False"],
            ["BE", "9", "True"], ["BE", "1", "False"],
        ]))
        self.assertEqual(by_country(view)["NL"]["fraud_eur"], "100")
        self.assertEqual(view["highest_monetary_volume_ratio"], ["BE"])

    def test_decimal_exact_sum_not_binary_float(self):
        view = MODULE.aggregate_payments(fixture([
            ["BE", "0.1", "True"], ["BE", "0.2", "True"], ["BE", "0.7", "False"],
        ]))
        row = by_country(view)["BE"]
        self.assertEqual(row["fraud_eur"], "0.3")
        self.assertEqual(row["eur"], "1")
        self.assertEqual(row["monetary_volume_ratio"], "0.3")
        self.assertEqual(row["monetary_volume_percent"], "30")

    def test_exact_total_under_low_decimal_context(self):
        with localcontext() as context:
            context.prec = 3
            view = MODULE.aggregate_payments(fixture([
                ["BE", "12345678901234567890.01", "True"], ["BE", "0.02", "False"],
            ]))
        self.assertEqual(by_country(view)["BE"]["eur"], "12345678901234567890.03")

    def test_decimal_denominator_power_of_two_is_exact(self):
        exact = MODULE.exact_decimal(Fraction(1, 2 ** 100))
        self.assertEqual(Fraction(Decimal(exact)), Fraction(1, 2 ** 100))

    def test_nonterminating_total_rejected(self):
        with self.assertRaisesRegex(ValueError, "nonterminating"):
            MODULE.exact_decimal(Fraction(1, 3))

    def test_maxima_use_unrounded_ratio(self):
        # Display rounds both ratios to the same 28 digits, but exact BE > NL.
        numerator = "1.000000000000000000000000000001"
        view = MODULE.aggregate_payments(fixture([
            ["BE", numerator, "True"], ["BE", "1", "False"],
            ["NL", "1", "True"], ["NL", "1", "False"],
        ]))
        self.assertEqual(Decimal(by_country(view)["BE"]["monetary_volume_ratio"]),
                         Decimal(by_country(view)["NL"]["monetary_volume_ratio"]))
        self.assertEqual(view["highest_monetary_volume_ratio"], ["BE"])

    def test_real_ties_not_arbitrarily_broken(self):
        view = MODULE.aggregate_payments(fixture([
            ["NL", "1", "True"], ["NL", "1", "False"],
            ["BE", "2", "True"], ["BE", "2", "False"],
        ]))
        self.assertEqual(view["highest_monetary_volume_ratio"], ["BE", "NL"])
        self.assertEqual(view["highest_fraud_count"], ["BE", "NL"])

    def test_groups_ip_country_and_does_not_filter_refused_or_merchant(self):
        view = MODULE.aggregate_payments(fixture([
            ["BE", "9", "True", "NL", "first", "True", "private-sentinel"],
            ["BE", "1", "False", "FR", "second", "False", "private-sentinel"],
        ], extras=True))
        self.assertEqual(list(by_country(view)), ["BE"])
        self.assertEqual(view["rows"], 2)
        self.assertEqual(by_country(view)["BE"]["monetary_volume_ratio"], "0.9")
        encoded = json.dumps(view)
        for private in ("private-sentinel", "first", "second", "email_address", "issuing_country"):
            self.assertNotIn(private, encoded)

    def test_true_false_counts_and_zero_fraud(self):
        view = MODULE.aggregate_payments(fixture([["BE", "1", "False"], ["BE", "0", "False"]]))
        self.assertEqual(view["fraud_flag_counts"], {"True": 0, "False": 2})
        self.assertEqual(by_country(view)["BE"]["fraud_eur"], "0")

    def test_crlf_and_quoted_csv(self):
        text = 'ip_country,eur_amount,has_fraudulent_dispute,merchant\r\n"BE",1,True,"name, other"\r\n'
        self.assertEqual(MODULE.aggregate_payments(text)["rows"], 1)

    def test_invalid_fraud_flags(self):
        for flag in ("true", "FALSE", "1", "0", "", " True", "unknown-sensitive-value"):
            with self.subTest(flag=flag), self.assertRaisesRegex(ValueError, "fraud flag") as caught:
                MODULE.aggregate_payments(fixture([["BE", "1", flag]]))
            self.assertNotIn("unknown-sensitive-value", str(caught.exception))

    def test_nonfinite_amounts(self):
        for amount in ("NaN", "sNaN", "Infinity", "-Infinity", "inf"):
            with self.subTest(amount=amount), self.assertRaisesRegex(ValueError, "non-finite"):
                MODULE.aggregate_payments(fixture([["BE", amount, "True"]]))

    def test_noncanonical_amounts(self):
        for amount in ("-1", "-0", "1e2", "+1", " 1", "1 ", "", "bad", "00.1", ".5"):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                MODULE.aggregate_payments(fixture([["BE", amount, "True"]]))

    def test_amount_rejects_nontext(self):
        for amount in (True, 1, None, Decimal("1")):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                MODULE.amount_fraction(amount)

    def test_zero_denominator(self):
        with self.assertRaisesRegex(ValueError, "zero DAB country denominator"):
            MODULE.aggregate_payments(fixture([["BE", "0", "True"]]))

    def test_one_zero_country_does_not_disappear(self):
        with self.assertRaisesRegex(ValueError, "zero DAB country denominator"):
            MODULE.aggregate_payments(fixture([["BE", "1", "False"], ["NL", "0", "True"]]))

    def test_empty_and_header_only(self):
        for text in ("", fixture([])):
            with self.subTest(text=text), self.assertRaises(ValueError):
                MODULE.aggregate_payments(text)

    def test_invalid_columns(self):
        for text in ("ip_country,eur_amount\nBE,1\n",
                     "ip_country,eur_amount,has_fraudulent_dispute,ip_country\nBE,1,True,BE\n",
                     "ip_country,eur_amount,has_fraudulent_dispute,\nBE,1,True,x\n"):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, "columns"):
                MODULE.aggregate_payments(text)

    def test_invalid_width(self):
        header = "ip_country,eur_amount,has_fraudulent_dispute\n"
        for line in ("BE,1,True,extra\n", "BE,1\n"):
            with self.subTest(line=line), self.assertRaisesRegex(ValueError, "width"):
                MODULE.aggregate_payments(header + line)

    def test_invalid_country(self):
        for country in ("be", "BEL", "", " BE", "B1", "../BE"):
            with self.subTest(country=country), self.assertRaisesRegex(ValueError, "country"):
                MODULE.aggregate_payments(fixture([[country, "1", "True"]]))

    def test_malformed_quote(self):
        with self.assertRaisesRegex(ValueError, "malformed DAB CSV"):
            MODULE.aggregate_payments('ip_country,eur_amount,has_fraudulent_dispute\n"BE,1,True\n')

    def test_strict_json_duplicates_and_constants(self):
        for text in ('{"x":1,"x":2}', '{"outer":{"x":1,"x":2}}',
                     'NaN', 'Infinity', '-Infinity'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                MODULE.decode_json(text)
        self.assertEqual(MODULE.decode_json('{"x":0.1}')["x"], Decimal("0.1"))


class PinnedSources(ReviewedModuleTests):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.original = {}
        for relative in MODULE.PINS:
            data = (ROOT / relative).read_bytes()
            cls.original[relative] = data
            path = cls.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_fixed_five_sources(self):
        self.assertEqual(len(MODULE.PINS), 5)
        self.assertEqual(MODULE.read_sources(self.root), self.original)

    def test_each_source_tamper_rejected(self):
        for relative, data in self.original.items():
            with self.subTest(source=relative):
                path = self.root / relative
                try:
                    path.write_bytes(data + b"\n")
                    with self.assertRaisesRegex(ValueError, "source SHA mismatch"):
                        MODULE.read_sources(self.root)
                finally:
                    path.write_bytes(data)

    def test_missing_source_rejected(self):
        relative = MODULE.CASE + "inputs/manual.md"
        path = self.root / relative
        data = self.original[relative]
        try:
            path.unlink()
            with self.assertRaises(FileNotFoundError):
                MODULE.read_sources(self.root)
        finally:
            path.write_bytes(data)

    def test_symlink_source_rejected(self):
        relative = MODULE.CASE + "inputs/manual.md"
        path = self.root / relative
        data = self.original[relative]
        target = self.root / "outside-fixture.md"
        target.write_bytes(data)
        try:
            path.unlink()
            path.symlink_to(target)
            with self.assertRaisesRegex(ValueError, "symlink"):
                MODULE.read_sources(self.root)
        finally:
            path.unlink()
            path.write_bytes(data)
            target.unlink()

    def test_parent_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "link").symlink_to(self.root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                MODULE.safe_path(root, "link/" + next(iter(MODULE.PINS)))

    def test_path_traversal_and_absolute_rejected(self):
        for relative in ("../file", str(self.root / "file")):
            with self.subTest(relative=relative), self.assertRaisesRegex(ValueError, "unsafe"):
                MODULE.safe_path(self.root, relative)

    def test_canonical_derivation_is_aggregate_only_and_readonly(self):
        before = {relative: (self.root / relative).read_bytes() for relative in MODULE.PINS}
        with mock.patch.object(Path, "write_bytes", side_effect=RuntimeError("write forbidden")), \
             mock.patch.object(Path, "write_text", side_effect=RuntimeError("write forbidden")), \
             mock.patch.object(Path, "mkdir", side_effect=RuntimeError("mkdir forbidden")):
            result = MODULE.derive(self.root)
        self.assertEqual(result["source_sha256"], MODULE.PINS)
        aggregate = result["aggregation"]
        self.assertEqual(aggregate["rows"], 138236)
        self.assertEqual(aggregate["highest_fraud_count"], ["NL"])
        self.assertEqual(aggregate["highest_monetary_volume_ratio"], ["BE"])
        countries = by_country(aggregate)
        self.assertEqual(countries["BE"]["eur"], "2150473.54")
        self.assertEqual(countries["BE"]["fraud_eur"], "263833.85")
        self.assertEqual(countries["NL"]["fraud_rows"], 2955)
        self.assertEqual(countries["BE"]["fraud_rows"], 2493)
        self.assertTrue(result["original_gold_supported_by_volume_ratio"])
        for key in ("gold_changed", "q49_attribution_withdrawn", "q2697_adjudication_scope_extended",
                    "historical_scores_or_denominators_changed", "product_artifacts_read",
                    "product_regrading_performed", "private_originals_authenticated"):
            self.assertIs(result[key], False)
        self.assertEqual(result["new_formal_admissions"], 0)
        self.assertEqual(before, {relative: (self.root / relative).read_bytes() for relative in MODULE.PINS})

    def test_module_capability_surface(self):
        tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
        allowed = {"csv", "hashlib", "io", "json", "re", "decimal", "fractions", "pathlib"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(all(alias.name in allowed for alias in node.names))
            if isinstance(node, ast.ImportFrom):
                self.assertIn(node.module, allowed)
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, {"eval", "exec", "compile", "open", "__import__"})
                if isinstance(node.func, ast.Attribute):
                    self.assertNotIn(node.func.attr, {"write_bytes", "write_text", "unlink", "mkdir",
                                                     "system", "Popen", "connect", "execute"})


if __name__ == "__main__":
    unittest.main()
