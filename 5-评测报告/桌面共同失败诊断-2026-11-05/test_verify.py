#!/usr/bin/env python3
"""Negative tests; writes isolated temporary copies only, never original evidence."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('desktop_failure_verify', HERE/'verify.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='desktop-comparison-negative-')
        self.base = Path(self.tmp.name)
        self.root = self.base/'repo'
        for relative in v.SOURCE_SHA256:
            dest = self.root/relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(v.ROOT/relative, dest)
        self.doc = json.loads((HERE/'comparison.json').read_text())
        self.evidence = self.root/'comparison.json'
        self.save()

    def tearDown(self):
        self.tmp.cleanup()

    def save(self):
        self.evidence.write_text(json.dumps(self.doc, ensure_ascii=False), encoding='utf-8')

    def reject(self, pattern):
        self.save()
        with self.assertRaisesRegex((ValueError, FileNotFoundError), pattern):
            v.verify(self.root, self.evidence)

    def reseal_source_claim(self, relative):
        for entry in self.doc['sources']:
            if entry['path'] == relative:
                entry['sha256'] = hashlib.sha256((self.root/relative).read_bytes()).hexdigest()

    def test_positive_and_read_only(self):
        before = {str(p.relative_to(self.root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob('*') if p.is_file()}
        with mock.patch('subprocess.run', side_effect=AssertionError('execution forbidden')), mock.patch('subprocess.Popen', side_effect=AssertionError('execution forbidden')), mock.patch('socket.socket', side_effect=AssertionError('network forbidden')):
            result = v.verify(self.root, self.evidence)
        after = {str(p.relative_to(self.root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(result['scores']['wb']['passed'], 19)
        self.assertEqual(len(result['assertions']['wb']), 30)

    def test_derived_value_tampering(self):
        self.doc['assertions']['wb'][3]['actual'] = 'fabricated'
        self.reject('derived comparison differs')

    def test_omitted_assertion(self):
        self.doc['assertions']['wb'].pop()
        self.reject('derived comparison differs')

    def test_wrong_denominator(self):
        self.doc['denominators']['core_per_run'] = 30
        self.reject('derived comparison differs')

    def test_resealed_forged_artifact(self):
        relative = v.RUNS['wb']+'/artifact-run/flight_plan.json'
        plan = json.loads((self.root/relative).read_text())
        plan['summary']['total_time_min'] = 668.7
        (self.root/relative).write_text(json.dumps(plan))
        self.reseal_source_claim(relative)
        self.doc['arithmetic']['flight_minutes_sum'] = 668.7
        self.reject('source hash mismatch')

    def test_resealed_forged_checker_and_grade(self):
        for run in v.RUNS.values():
            relative = run+'/checker.json'
            checker = json.loads((self.root/relative).read_text())
            checker['passed'] = 27
            for c in checker['checks']:
                c['pass'] = True
            (self.root/relative).write_text(json.dumps(checker))
            self.reseal_source_claim(relative)
            relative = run+'/grading.json'
            grade = json.loads((self.root/relative).read_text())
            grade.get('score', grade)['passed'] = 27
            grade['failed_assertions'] = []
            (self.root/relative).write_text(json.dumps(grade))
            self.reseal_source_claim(relative)
        self.doc['failure_sets'] = {'wb': [], 'doubao': []}
        self.reject('source hash mismatch')

    def test_resealed_derived_self_hash_not_authority(self):
        self.doc['comparison']['same_cause_identified'] = True
        self.doc['self_sha256'] = hashlib.sha256(json.dumps(self.doc, sort_keys=True).encode()).hexdigest()
        self.reject('derived comparison differs')

    def test_parent_path_escape(self):
        self.doc['sources'][0]['path'] = '../outside.json'
        self.reject('unsafe path')

    def test_absolute_path_escape(self):
        self.doc['sources'][0]['path'] = str(self.base/'outside.json')
        self.reject('unsafe path')

    def test_symlink_source_escape(self):
        relative = next(iter(v.SOURCE_SHA256))
        source = self.root/relative
        outside = self.base/'outside'
        outside.write_bytes(source.read_bytes())
        source.unlink()
        source.symlink_to(outside)
        self.reject('path escape')

    def test_missing_source(self):
        (self.root/next(iter(v.SOURCE_SHA256))).unlink()
        self.reject('No such file')

    def test_duplicate_json_key(self):
        self.evidence.write_text('{"schema":"x","schema":"y"}')
        with self.assertRaisesRegex(ValueError, 'duplicate JSON key'):
            v.verify(self.root, self.evidence)


if __name__ == '__main__':
    unittest.main(verbosity=2)
