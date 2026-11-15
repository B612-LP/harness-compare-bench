"""测试固定汇总算术及独立模拟，不能认证私档。"""
import unittest

import demo


class ArithmeticTests(unittest.TestCase):
    def test_recorded_usage_differences(self):
        values = demo.summary()
        self.assertEqual(values["prompt_delta"], 51_241)
        self.assertEqual(values["cache_delta"], 7_552)

    def test_old_code_gate_and_formula_only(self):
        values = demo.summary()
        self.assertEqual(values["old_gate"], 28_800)
        self.assertGreater(values["prompt_delta"], values["old_gate"])
        self.assertEqual(values["formula_only_20k"], 20_000)

    def test_recorded_prefix_arithmetic(self):
        values = demo.summary()
        self.assertEqual(values["prefix_overhead"], 6_615)
        self.assertEqual(values["observed_local_overhead"], 6_615)
        self.assertEqual(demo.SOURCE_BYTES + values["prefix_overhead"],
                         demo.RESULT_BYTES)


class SyntheticOnlyTests(unittest.TestCase):
    def test_synthetic_source_shape_and_no_trailing_lf(self):
        source = demo.make_synthetic_source()
        self.assertEqual(len(source), 80_000)
        self.assertEqual(len(source.split(b"\n")), 945)
        self.assertFalse(source.endswith(b"\n"))

    def test_synthetic_seven_byte_prefix_round_trip(self):
        source = demo.make_synthetic_source()
        numbered = demo.add_synthetic_prefixes(source)
        self.assertEqual(len(numbered), 86_615)
        self.assertEqual(len(numbered.split(b"\n")), 945)
        self.assertFalse(numbered.endswith(b"\n"))
        self.assertEqual(demo.strip_synthetic_prefixes(numbered), source)

    def test_rejects_bad_synthetic_prefix_even_in_optimized_mode(self):
        numbered = demo.add_synthetic_prefixes(demo.make_synthetic_source())
        with self.assertRaises(ValueError):
            demo.strip_synthetic_prefixes(b"X" + numbered[1:])

    def test_rejects_trailing_lf(self):
        source = demo.make_synthetic_source()
        with self.assertRaises(ValueError):
            demo.add_synthetic_prefixes(source + b"\n")


if __name__ == "__main__":
    unittest.main()
