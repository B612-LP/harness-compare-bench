import copy
import unittest
from fractions import Fraction

from verify import (LEDGER, category, fixed_median, mask_before_fact,
                    maximum_disjoint_panels, projection, read_input, recount)


class RecountTest(unittest.TestCase):
    def test_fixed_public_recount(self):
        result = recount(read_input(LEDGER))
        self.assertEqual(result['counts'], {'runs': 18, 'paired_runs': 14, 'edges': 14, 'main': 52, 'title': 13})
        self.assertEqual(result['edges_by_point'], {
            'E1': {'below': 9, 'in_band': 4, 'above': 1},
            'E2': {'in_band': 5, 'above': 9},
            'E3': {'in_band': 3, 'above': 11},
        })
        panels = result['largest_vertex_disjoint_panels']
        self.assertEqual((panels['panels'], panels['edges_per_panel']), (48, 5))
        self.assertEqual(panels['median_categories']['E2'], {'in_band': 12, 'above': 36})
        self.assertEqual(panels['median_categories']['E3'], {'above': 48})
        self.assertEqual(result['suffix_mask'], {
            'masked_pairs': 14,
            'wrong_last_request_ratio_below_0.90': 9,
            'fact_ratio_unknown': 14,
            'prefix_rules_out_below_0.90_if_fact_later_arrives': 5,
        })

    def test_inclusive_band_and_missing_median(self):
        self.assertEqual([category(Fraction(x, 100)) for x in (89, 90, 110, 111)],
                         ['below', 'in_band', 'in_band', 'above'])
        self.assertIsNone(fixed_median([Fraction(1), None]))
        self.assertEqual(fixed_median([Fraction(1), Fraction(2)]), Fraction(3, 2))

    def test_reused_run_is_not_independent(self):
        edges = [('a1', 'b1'), ('a1', 'b2'), ('a2', 'b1'), ('a2', 'b2')]
        self.assertEqual(maximum_disjoint_panels(edges), [(0, 3), (1, 2)])
        self.assertEqual(maximum_disjoint_panels(edges[:2]), [(0,), (1,)])

    def test_censor_never_substitutes_an_end(self):
        short = ({1: 19, 3: 90, 6: 125}, {'E1': 3, 'E2': 6, 'E3': 6})
        a = {'E2': 100, 'E3': 130}
        naive, lower, fact = mask_before_fact(short, a)
        self.assertEqual(category(naive), 'below')
        self.assertEqual(category(lower), 'in_band')
        self.assertIsNone(fact)
        a['E2'] = None
        self.assertIsNone(mask_before_fact(short, a)[1])
        self.assertIsNone(mask_before_fact((short[0], dict(short[1], E2=3)), a))

    def test_distinct_endpoint_support(self):
        runs, _, _ = projection(read_input(LEDGER))
        self.assertTrue(any(points['E1'] is None and points['E2'] is not None
                            for _, points in runs.values()))

    def test_role_and_endpoint_near_misses(self):
        source = read_input(LEDGER)
        row = source['runs'][0]
        altered = copy.deepcopy(source)
        altered['runs'][0]['title'] = row['ma']
        with self.assertRaisesRegex(ValueError, 'overlapping roles'):
            projection(altered)
        altered = copy.deepcopy(source)
        altered['runs'][0]['ends']['E2'] = row['title'][0]
        with self.assertRaisesRegex(ValueError, 'not bound'):
            projection(altered)
        altered = copy.deepcopy(source)
        altered['packets'].append(altered['packets'][0])
        with self.assertRaisesRegex(ValueError, 'duplicate packet'):
            projection(altered)


if __name__ == '__main__':
    unittest.main()
