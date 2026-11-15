#!/usr/bin/env python3
"""无历史 SQL、无产品：固定查询、哈希与人工构造的内存反例。"""
import importlib.util
from pathlib import Path
import sqlite3
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('verify', Path(__file__).with_name('verify.py'))
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

# 虚构的名称和键只存在于进程内部；测试输出不显示数据。
class Synthetic(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.execute('CREATE TABLE satscores(cds TEXT, sname TEXT, dname TEXT, AvgScrMath REAL)')
        self.db.execute('CREATE TABLE frpm(CDSCode TEXT, `Charter Funding Type` TEXT, `District Name` TEXT)')
        self.prefix = 'Synthetic-District'

    def tearDown(self):
        self.db.close()

    def add(self, key, score, candidate=True, gold=True, name=None):
        p = self.prefix
        self.db.execute('INSERT INTO satscores VALUES (?,?,?,?)',
                        (str(key), name or str(key), p if candidate else 'other', score))
        self.db.execute('INSERT INTO frpm VALUES (?,?,?)',
                        (str(key), 'F', p if gold else 'other'))

    def run_fixed(self):
        return v.derive(self.db.execute(v.FIXED_SELECT, (self.prefix,)*4).fetchall())

    def test_null_denominator_strict_threshold_and_correlated_location(self):
        self.add(1, 800)
        self.add(2, None)
        self.add(3, 400)
        report = self.run_fixed()
        self.assertEqual(report['join_rows'], 3)
        self.assertEqual(report['math_null'], 1)
        self.assertEqual(report['avg_nonnull'], 600)
        self.assertEqual(report['sum_over_all_rows'], 400)
        self.assertEqual(report['gold_groups_rows'], 1)
        self.assertEqual(report['candidate_rows'], 1)
        self.assertEqual(report['reconstruction_rows'], 3)
        self.assertEqual(report['reconstruction_extra_rows'], 2)
        self.assertEqual(report['extra_with_null_math'], 1)
        # score=400 不符合 >400；但所在完整地区均分 >400。

    def test_sum_count_equivalence_only_without_null(self):
        self.add(1, 800)
        self.add(2, 400)
        avg, sum_count = self.db.execute('SELECT AVG(AvgScrMath), SUM(AvgScrMath)*1.0/COUNT(*) FROM satscores').fetchone()
        self.assertEqual(avg, sum_count)
        self.add(3, None)
        avg, sum_count = self.db.execute('SELECT AVG(AvgScrMath), SUM(AvgScrMath)*1.0/COUNT(*) FROM satscores').fetchone()
        self.assertEqual(avg, 600)
        self.assertEqual(sum_count, 400)
        self.assertNotEqual(avg, sum_count)
        self.assertTrue(avg > 400)
        self.assertFalse(sum_count > 400)

    def test_all_null_has_no_mean_or_results(self):
        self.add(1, None)
        r = self.db.execute(v.FIXED_SELECT, (self.prefix,)*4).fetchall()
        self.assertIsNone(r[0][6])
        with self.assertRaises(v.VerificationError):
            v.derive(r)

    def test_candidate_prefix_from_different_column(self):
        self.add(1, 500)
        self.add(2, 600, candidate=True, gold=False)
        report = self.run_fixed()
        self.assertEqual(report['join_rows'], 1)
        self.assertEqual(report['candidate_rows'], 2)
        self.assertFalse(report['candidate_equals_gold_checker_normalized_multiset'])

    def test_checker_null_text_collision_is_not_raw_equality(self):
        self.add(1, 500, candidate=False, gold=True)
        self.add(2, 500, candidate=True, gold=False, name='<NULL>')
        self.db.execute('UPDATE satscores SET sname=NULL WHERE cds=?', ('1',))
        report = self.run_fixed()
        self.assertTrue(report['candidate_equals_gold_checker_normalized_multiset'])
        self.assertFalse(report['candidate_equals_gold_raw_value_multiset'])

    def test_duplicate_group_not_assumed_one_school_per_result(self):
        self.add(1, 800, name='synthetic')
        self.add(2, None, name='synthetic')
        rows = self.db.execute(v.FIXED_SELECT, (self.prefix,)*4).fetchall()
        with self.assertRaises(v.VerificationError):
            v.derive(rows)
        group_count, filtered_count = self.db.execute('''SELECT
           (SELECT COUNT(*) FROM (SELECT sname FROM satscores GROUP BY sname
              HAVING SUM(AvgScrMath)*1.0/COUNT(*) > 400)),
           (SELECT COUNT(*) FROM satscores WHERE AvgScrMath > 400)''').fetchone()
        self.assertEqual(group_count, 0)  # 分母包含 NULL 那一行，恰好 400
        self.assertEqual(filtered_count, 1)

    def test_distinct_districts_are_not_combined(self):
        self.add(1, 800)
        self.add(2, 0)
        # 第二行换到另一个同前缀的虚构地区；每个相关均值分别计算。
        self.db.execute('UPDATE frpm SET `District Name`=? WHERE CDSCode=?', (self.prefix+'-2', '2'))
        report = self.run_fixed()
        self.assertEqual(report['distinct_districts'], 2)
        self.assertEqual(report['reconstruction_rows'], 1)
        self.assertEqual(report['gold_groups_rows'], 1)

class Guards(unittest.TestCase):
    def test_sql_fingerprint(self):
        self.assertEqual(v.digest(v.FIXED_SELECT.encode()), '001fdc4850b9d03b6d135e3409dc92dbed825f1bbf793eae4a1860acb3da58dc')
        self.assertTrue(v.FIXED_SELECT.lstrip().upper().startswith('SELECT '))
        self.assertNotIn(';', v.FIXED_SELECT)

    def test_source_identity_and_hash_guard(self):
        data = v.read_sources()
        v.check_sources(data)
        altered = dict(data)
        with mock.patch.object(v, 'digest', return_value='0'*64):
            with self.assertRaises(v.VerificationError):
                v.read_sources()
        # 就算有人绕过文件级散列，题目 SQL 单独的指纹依然应拒绝。
        items = [__import__('json').loads(x) for x in data[v.R2+'workspace/answers.jsonl'].splitlines()]
        next(x for x in items if x['question_id'] == 25)['sql'] += ' '
        altered[v.R2+'workspace/answers.jsonl'] = b'\n'.join(__import__('json').dumps(x).encode() for x in items)
        with self.assertRaises(v.VerificationError):
            v.check_sources(altered)

    def test_db_hash_and_sidecar_guards(self):
        path = v.ROOT / v.DB
        with mock.patch.object(v, 'sha_file', return_value='0'*64):
            with self.assertRaises(v.VerificationError):
                v.check_db(path)
        with mock.patch.object(Path, 'exists', return_value=True):
            with self.assertRaises(v.VerificationError):
                v.reject_sidecars(path)

    def test_duplicate_question_rejected(self):
        data = v.read_sources()
        rel = v.R2+'workspace/answers.jsonl'
        q25 = next(line for line in data[rel].splitlines() if b'"question_id": 25' in line)
        data[rel] += b'\n'+q25+b'\n'
        with self.assertRaises(v.VerificationError):
            v.unique_q25(data, rel)

    def test_current_canonical(self):
        report = v.canonical(v.question_prefix(v.read_sources()))
        self.assertEqual((report['join_rows'], report['math_null'], report['math_sum']), (12,6,2842))
        self.assertEqual((report['gold_groups_rows'], report['candidate_rows'], report['reconstruction_rows']), (6,6,12))
        self.assertEqual((report['reconstruction_extra_rows'], report['extra_with_null_math']), (6,6))
        self.assertTrue(report['candidate_equals_gold_checker_normalized_multiset'])
        self.assertTrue(report['candidate_equals_gold_raw_value_multiset'])
        self.assertEqual((report['prefix_candidate_only'], report['prefix_gold_only']), (0, 0))
        self.assertEqual(report['district_summaries_anonymous'], [
            {'rows':4,'nonnull':1,'sum':458,'nonnull_avg':458.0,'sum_over_rows':114.5},
            {'rows':8,'nonnull':5,'sum':2384,'nonnull_avg':476.8,'sum_over_rows':298.0}])

if __name__ == '__main__':
    unittest.main(verbosity=1)
