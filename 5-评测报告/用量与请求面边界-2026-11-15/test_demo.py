#!/usr/bin/env python3
"""仅验证固定数字的算术和合成投影，不验证历史原件。"""
import unittest

from demo import examples, old_threshold, synthetic_projection


class MathDemoTests(unittest.TestCase):
    def test_two_distinct_attempts(self):
        self.assertEqual(70733 - 28794, 41939)
        self.assertEqual(70836 - 28848, 41988)
        self.assertEqual(41988 - 41939, 49)

    def test_threshold_and_boundary(self):
        threshold = old_threshold(65504)
        self.assertEqual(threshold, 23580)
        self.assertFalse(threshold - 1 >= threshold)
        self.assertTrue(threshold >= threshold)
        self.assertTrue(41939 >= threshold)
        self.assertTrue(41988 >= threshold)

    def test_invalid_size(self):
        for value in (-1, 1.5, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                old_threshold(value)

    def test_non_injective_synthetic_projection(self):
        a, b = examples()
        self.assertNotEqual(a, b)
        self.assertEqual(synthetic_projection(a), synthetic_projection(b))
        self.assertNotEqual(synthetic_projection(a), synthetic_projection(a + "x"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
