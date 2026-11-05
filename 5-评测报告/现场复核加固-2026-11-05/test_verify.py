#!/usr/bin/env python3
"""Stdlib regression suite; all attacks affect temporary copies only.

Pin-layer integration tests and direct semantic unit tests are separate: passing
an anchor test alone is NOT evidence that the score/accounting logic is correct.
Only trusted verification entrypoints are run; never candidates or checker.py.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
spec = importlib.util.spec_from_file_location('hardened_scene_verifier', HERE / 'verify.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
PINS = v.parse_json((HERE / 'source-pins.json').read_bytes())


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def read(root, relative):
    return v.parse_json((root / relative).read_bytes())


def reseal(root, scene):
    manifest = read(root, scene + '/manifest.json')
    for row in manifest['files']:
        data = (root / scene / row['path']).read_bytes()
        row['sha256'] = hashlib.sha256(data).hexdigest()
        if 'bytes' in row:
            row['bytes'] = len(data)
    dump(root / scene / 'manifest.json', manifest)


class SemanticTests(unittest.TestCase):
    """No pin check in this class: exercise decisions with synthetic records."""
    def records(self, product='wb'):
        scene = v.SCENES[product]
        return read(REPO, scene + '/checker.json'), read(REPO, scene + '/grading.json')

    def test_original_scores(self):
        for product in ('wb', 'doubao'):
            c, g = self.records(product)
            result = v.validate_score(c, g, product)
            self.assertEqual((result['passed'], result['total'], result['reward']), (19, 27, 0))
            self.assertEqual((result['critical_passed'], result['gate_passed']), (4, 3))

    def test_mutually_consistent_reward_forgery(self):
        for product in ('wb', 'doubao'):
            c, g = self.records(product)
            c['reward'] = 1
            g.get('score', g)['reward'] = 1
            with self.subTest(product=product), self.assertRaisesRegex(ValueError, 'checker score/reward'):
                v.validate_score(c, g, product)

    def test_critical_false_cannot_claim_true(self):
        c, g = self.records()
        c['critical_ok'] = g['score']['critical_ok'] = True
        with self.assertRaisesRegex(ValueError, 'critical_ok'):
            v.validate_score(c, g, 'wb')

    def test_missing_duplicate_unknown_core(self):
        original, _ = self.records()
        cases = [original['checks'][:-1],
                 [row for row in original['checks'] if row['id'] != 'route_order'],
                 original['checks'][:-1] + [original['checks'][4]],
                 copy.deepcopy(original['checks'])]
        cases[-1][4]['id'] = 'unknown_core'
        for checks in cases:
            with self.subTest(checks=checks[-1]['id']), self.assertRaises(ValueError):
                v.score_from_checks(checks)

    def test_bool_integer_float_confusion(self):
        for field, value in [('reward', False), ('passed', True), ('total', 27.0), ('weighted', True)]:
            c, g = self.records()
            c[field] = g['score'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                v.validate_score(c, g, 'wb')
        c, _ = self.records()
        c['checks'][0]['pass'] = 1
        with self.assertRaisesRegex(ValueError, 'must be bool'):
            v.score_from_checks(c['checks'])

    def test_threshold_critical_and_gates_independently(self):
        template, _ = self.records()
        # Every critical true, but only 19 core passes: threshold must still fail.
        order = list(v.CRITICAL) + [key for key in v.CORE if key not in v.CRITICAL]
        for count in (19, 20, 27):
            checks = copy.deepcopy(template['checks'])
            for row in checks:
                row['pass'] = row['id'] in v.GATES or row['id'] in order[:count]
            score, _ = v.score_from_checks(checks)
            self.assertEqual(score['passed'], count)
            self.assertEqual(score['reward'], int(count >= 20))
            if count == 27:
                next(row for row in checks if row['id'] == 'code_rerun')['pass'] = False
                self.assertEqual(v.score_from_checks(checks)[0]['reward'], 0)
                next(row for row in checks if row['id'] == 'code_rerun')['pass'] = True
                next(row for row in checks if row['id'] == 'total_time_value')['pass'] = False
                score, _ = v.score_from_checks(checks)
                self.assertEqual(score['passed'], 26)
                self.assertEqual(score['reward'], 0)

    def test_wrong_gate_critical_and_failure_projection(self):
        for field in ('gates', 'critical_checks', 'failed_assertions'):
            c, g = self.records()
            if field == 'failed_assertions':
                g[field].pop()
            else:
                g[field][next(iter(g[field]))] = False
            with self.subTest(field=field), self.assertRaises(ValueError):
                v.validate_score(c, g, 'wb')

    def test_slots_reject_optimized_attack_semantically(self):
        state = read(REPO, v.SCENES['observation'] + '/slots.json')
        self.assertEqual(v.validate_slots(state)['formal_admissions'], 0)
        for key, value in [('formal_admissions', 999), ('formal_admissions', False),
                           ('submit_invocations', True), ('native_completed', 1)]:
            changed = copy.deepcopy(state)
            changed[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                v.validate_slots(changed)
        for index, field, value in [(0, 'window_state', 'completed'),
                                    (0, 'execution_window_seconds', 1201),
                                    (1, 'reward', 0), (1, 'submission_confirmed', 0)]:
            changed = copy.deepcopy(state)
            changed['slots'][index][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                v.validate_slots(changed)

    def test_accounting_no_new_n_or_timeout_rewrite(self):
        for product in ('wb', 'doubao'):
            scene = v.SCENES[product]
            original, grade = read(REPO, scene + '/accounting.json'), read(REPO, scene + '/grading.json')
            v.validate_accounting(original, grade, product)
            for field, value in [('formal_admissions', 1), ('fixed_contract_repeat', True),
                                 ('followup_new_model_submissions', 1), ('read_truth_denominator', 2),
                                 ('false_negative_rate', 0), ('os_isolation_verified', True),
                                 ('checker_invocations', True)]:
                changed = copy.deepcopy(original)
                changed[field] = value
                with self.subTest(product=product, field=field), self.assertRaises(ValueError):
                    v.validate_accounting(changed, grade, product)

    def test_strict_json_duplicate_nonfinite_overflow(self):
        for raw in ['{"x":0,"x":1}', '{"x":NaN}', '{"x":Infinity}',
                    '{"x":-Infinity}', '{"x":[1e999]}']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                v.parse_json(raw)

    def test_path_lexical_and_symlink_escape(self):
        for path in ('../x', '/tmp/x', 'a/../../x', './x', 'a//x', 'a\\x', '', '.'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                v.safe_file(REPO, path)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            (root / 'escape').symlink_to(HERE / 'verify.py')
            with self.assertRaisesRegex(ValueError, 'symlink'):
                v.safe_file(root, 'escape')


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        for entry in PINS['files']:
            destination = self.root / entry['path']
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / entry['path'], destination)
        target = self.root / v.PACKAGE / 'source-pins.json'
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(HERE / 'source-pins.json', target)

    def command(self, optimized=False, legacy=None):
        # WB/DB old CLIs ignore --root and bind __file__; run their unchanged temporary copy.
        script = HERE / 'verify.py' if legacy is None else self.root / legacy / 'verify.py'
        root = self.root if legacy is None else self.root / legacy
        command = [sys.executable, '-B'] + (['-O'] if optimized else [])
        command += [str(script), '--root', str(root)]
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        return subprocess.run(command, text=True, capture_output=True, env=env, check=False)

    def forge_reward(self, product):
        scene = v.SCENES[product]
        c = read(self.root, scene + '/checker.json')
        g = read(self.root, scene + '/grading.json')
        c['reward'] = g.get('score', g)['reward'] = 1
        dump(self.root / scene / 'checker.json', c)
        g['hashes']['checker_stdout'] = v.sha256((self.root / scene / 'checker.json').read_bytes())
        dump(self.root / scene / 'grading.json', g)
        reseal(self.root, scene)

    def test_original_snapshot_readonly_without_process_or_network(self):
        def snapshot():
            return {str(p.relative_to(self.root)): v.sha256(p.read_bytes())
                    for p in self.root.rglob('*') if p.is_file()}
        before = snapshot()
        with mock.patch.object(subprocess, 'run', side_effect=AssertionError('no process')), \
             mock.patch.object(socket, 'socket', side_effect=AssertionError('no socket')):
            result = v.verify(self.root)
        self.assertEqual(result['status'], 'PASS_PUBLIC_SNAPSHOT_V2')
        self.assertEqual(before, snapshot())

    def test_normal_and_optimized_baseline_identical(self):
        normal, optimized = self.command(), self.command(True)
        self.assertEqual((normal.returncode, optimized.returncode), (0, 0), normal.stderr + optimized.stderr)
        self.assertEqual(normal.stdout, optimized.stdout)

    def test_legacy_original_controls(self):
        for product in ('wb', 'doubao'):
            original = self.command(legacy=v.SCENES[product])
            self.assertEqual(original.returncode, 0, original.stderr)
            self.assertEqual(json.loads(original.stdout)['reward'], 0)
        original = self.command(legacy=v.SCENES['observation'])
        self.assertEqual(original.returncode, 0, original.stderr)
        self.assertTrue(json.loads(original.stdout)['ok'])

    def test_both_legacy_reward_false_pass_then_v2_reject(self):
        for product in ('wb', 'doubao'):
            self.forge_reward(product)
            # These historical scripts only parse/compare bytes. They do not run checker/candidates.
            old = self.command(legacy=v.SCENES[product])
            self.assertEqual(old.returncode, 0, old.stderr)
            self.assertEqual(json.loads(old.stdout)['reward'], 1)
            for optimized in (False, True):
                new = self.command(optimized)
                self.assertEqual(new.returncode, 1)
                self.assertIn('source hash mismatch', new.stdout)

    def test_legacy_assert_optimization_false_pass_then_v2_reject(self):
        scene = v.SCENES['observation']
        state = read(self.root, scene + '/slots.json')
        state['formal_admissions'] = 999
        dump(self.root / scene / 'slots.json', state)  # do not reseal
        self.assertEqual(self.command(legacy=scene).returncode, 1)
        old = self.command(True, legacy=scene)
        self.assertEqual(old.returncode, 0, old.stderr)
        self.assertTrue(json.loads(old.stdout)['ok'])
        for optimized in (False, True):
            new = self.command(optimized)
            self.assertEqual(new.returncode, 1)
            self.assertIn('source hash mismatch', new.stdout)

    def test_pinset_resealing_does_not_reanchor(self):
        self.forge_reward('wb')
        path = self.root / v.PACKAGE / 'source-pins.json'
        pins = read(self.root, v.PACKAGE + '/source-pins.json')
        for row in pins['files']:
            row['sha256'] = v.sha256((self.root / row['path']).read_bytes())
        dump(path, pins)
        with self.assertRaisesRegex(ValueError, 'trusted pinset hash mismatch'):
            v.verify(self.root)

    def test_missing_tampered_and_extra_files(self):
        target = self.root / v.SCENES['wb'] / 'checker.json'
        original = target.read_bytes()
        target.unlink()
        with self.assertRaisesRegex(ValueError, 'missing/escaped'):
            v.verify(self.root)
        target.write_bytes(original + b' ')
        with self.assertRaisesRegex(ValueError, 'source hash mismatch'):
            v.verify(self.root)
        target.write_bytes(original)
        (target.parent / 'unexpected.txt').write_text('extra')
        with self.assertRaisesRegex(ValueError, 'file set mismatch'):
            v.verify(self.root)

    def test_symlink_source_is_rejected_even_same_bytes(self):
        target = self.root / v.SCENES['wb'] / 'checker.json'
        target.unlink()
        target.symlink_to(REPO / v.SCENES['wb'] / 'checker.json')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            v.verify(self.root)

    def test_manifest_semantic_duplicate_unknown_bytes(self):
        scene = v.SCENES['wb']
        raw = {row['path']: (self.root / row['path']).read_bytes() for row in PINS['files']}
        pins = {row['path']: row['sha256'] for row in PINS['files']}
        original = v.parse_json(raw[scene + '/manifest.json'])
        for attack in ('duplicate', 'parent', 'absolute', 'bad_hash', 'bool_bytes'):
            value = copy.deepcopy(original)
            if attack == 'duplicate':
                value['files'].append(value['files'][0])
            elif attack == 'parent':
                value['files'][0]['path'] = '../escape'
            elif attack == 'absolute':
                value['files'][0]['path'] = '/tmp/escape'
            elif attack == 'bad_hash':
                value['files'][0]['sha256'] = '0' * 64
            else:
                value['files'][0]['bytes'] = True
            raw[scene + '/manifest.json'] = json.dumps(value).encode()
            with self.subTest(attack=attack), self.assertRaises(ValueError):
                v.check_manifest(scene, raw, pins)


if __name__ == '__main__':
    unittest.main(verbosity=2)
