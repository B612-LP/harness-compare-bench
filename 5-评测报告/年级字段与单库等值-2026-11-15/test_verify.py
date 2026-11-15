#!/usr/bin/env python3
"""运行：python3 -B test_verify.py；python3 -B -O test_verify.py。"""
import json
import sqlite3
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

import verify as v


class VerifyTests(unittest.TestCase):
    def test_real_inputs_and_database(self):
        result = v.run()
        self.assertEqual(result['current_database']['all_schools']['n'], 17686)
        self.assertEqual(result['current_database']['all_schools']['offered_null_overlapping'], 3882)
        self.assertEqual(result['current_database']['all_schools']['served_null_overlapping'], 5743)
        self.assertEqual(result['current_database']['joined_provision']['n'], 11)
        self.assertEqual(result['current_database']['target_other_filters']['both_true'], 1)
        differences = result['target_set_and_group_differences']
        for key in ('members_offered_minus_served', 'members_served_minus_offered',
                    'groups_offered_minus_served', 'groups_served_minus_offered'):
            self.assertEqual(differences[key], 0)
        self.assertEqual(differences['offered_group_count'], 1)
        self.assertEqual(differences['served_group_count'], 1)

    def test_fixed_hash_rejects_bad_bytes(self):
        with mock.patch.object(Path, 'read_bytes', return_value=b'corrupted'):
            with self.assertRaises(v.VerificationError):
                v.verify_pins()

    def test_checker_rejects_false_wrong_rows_and_duplicates(self):
        for checks in ([{'id': 'q83', 'pass': False, 'note': '行集一致（1 行）'}],
                       [{'id': 'q83', 'pass': True, 'note': '行集一致（2 行）'}],
                       [{'id': 'q83', 'pass': True, 'note': '行集一致（1 行）'}] * 2,
                       []):
            with self.subTest(checks=checks), self.assertRaises(v.VerificationError):
                v.check_checker({'checks': checks})

    def test_field_swap_is_rejected_not_executed(self):
        for product, sql in v.CANDIDATE.items():
            with self.subTest(product=product), self.assertRaises(v.VerificationError):
                v.check_sql(sql.replace('GSserved', 'GSoffered'), sql)
        with self.assertRaises(v.VerificationError):
            v.check_sql(v.GOLD.replace('GSoffered', 'GSserved'), v.GOLD)

    def test_sql_null_partition_and_count(self):
        # SELECT-only in-memory table includes each UNKNOWN case and a positive.
        prefix = '''WITH base(id,city,offered,served,magnet,joined,provision) AS (VALUES
          (1,'x','K-8','K-8',1,1,1), (2,'x','K-8',NULL,1,1,1),
          (3,'x',NULL,'K-8',1,1,1), (4,'x',NULL,NULL,1,1,1),
          (5,'x',NULL,'1-8',1,1,1), (6,'x','1-8',NULL,1,1,1),
          (7,'x','1-8','1-8',1,1,1)), scopes AS (
          SELECT 'test' AS scope, * FROM base)'''
        with sqlite3.connect(':memory:') as conn:
            conn.execute('PRAGMA query_only=ON')
            with mock.patch.object(v, 'SUMMARY', v.SUMMARY.replace(v.BASE, prefix)):
                row = v.summarize(conn)['test']
            self.assertEqual(row, {'n': 7, 'both_true': 1, 'offered_only': 1,
                                   'served_only': 1, 'neither_nonnull': 1,
                                   'neither_null': 3, 'null_any_overlapping': 5,
                                   'offered_null_overlapping': 3, 'served_null_overlapping': 3})
            counts = conn.execute("SELECT COUNT(*), COUNT(x), COUNT(CASE WHEN x='K-8' THEN 1 END) FROM (SELECT NULL AS x UNION ALL SELECT 'K-8')").fetchone()
            self.assertEqual(counts, (2, 1, 1))

    def test_synthetic_counterexample(self):
        with sqlite3.connect(':memory:') as conn:
            conn.execute('PRAGMA query_only=ON')
            result = v.synthetic(conn)
        self.assertEqual(result['target_n'], 7)  # three excluded by other filters
        self.assertEqual(result['members_offered_only'], 2)
        self.assertEqual(result['members_served_only'], 2)
        self.assertEqual(result['groups_offered_only'], 0)
        self.assertEqual(result['groups_served_only'], 0)
        self.assertEqual(result['null_any'], 3)

    def test_production_difference_query_with_synthetic_base(self):
        # Exercise the actual production query with SELECT-only synthetic data.
        base = v.SYNTHETIC.split('), target AS', 1)[0] + ')'
        with sqlite3.connect(':memory:') as conn:
            conn.execute('PRAGMA query_only=ON')
            for synthetic_base, expected in (
                (base, (2, 2, 0, 0, 1, 1)),
                (base.replace("(2,'x','K-8','1-8'", "(2,'y','K-8','1-8'"), (2, 2, 2, 1, 2, 1)),
                (base.replace("(2,'x','K-8','1-8'", "(2,'x','K-12','1-8'"), (1, 2, 1, 1, 1, 1)),
                (base.replace("(1,'x','K-12','K-8'", "(1,'x','K-12','1-8'"), (2, 1, 1, 1, 1, 1)),
            ):
                with self.subTest(base=synthetic_base), mock.patch.object(v, 'DIFFERENCES', v.DIFFERENCES.replace(v.BASE, synthetic_base)):
                    self.assertEqual(tuple(v.differences(conn).values()), expected)

    def test_missing_or_invalid_database_rejected(self):
        with sqlite3.connect(':memory:') as conn:
            conn.execute('PRAGMA query_only=ON')
            with self.assertRaises(sqlite3.OperationalError):
                v.summarize(conn)

    def test_optimized_mode_still_checks_bad_input(self):
        # 未创建任何副本或文件；-O 不能移除 require。
        script = "import verify; verify.check_sql('bad', verify.GOLD)"
        proc = subprocess.run([sys.executable, '-B', '-O', '-c', script],
                              cwd=Path(__file__).parent, capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('VerificationError', proc.stderr)

    def test_cli_under_normal_and_optimized(self):
        for flag in ([], ['-O']):
            with self.subTest(flag=flag):
                p = subprocess.run([sys.executable, '-B', *flag, str(Path(v.__file__))],
                                   capture_output=True, text=True)
                self.assertEqual(p.returncode, 0, p.stderr)
                obj = json.loads(p.stdout)
                self.assertEqual(obj['current_database']['target_other_filters']['n'], 1)
                self.assertEqual(obj['synthetic_not_real_frequency']['groups_offered_only'], 0)


if __name__ == '__main__':
    unittest.main()
