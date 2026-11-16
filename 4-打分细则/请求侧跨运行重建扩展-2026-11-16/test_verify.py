#!/usr/bin/env python3
"""Tests for the req-side extension verifier (synthetic archives; no private data).

Run from the package directory: python3 -I -S test_verify.py (stdlib only).
When auditing in a non-public tree, set EXT_TEST_ROOT to the repo root that
holds the pinned public files; without it the CLI tests use the default root."""
import copy
import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
MODULE_PATH = HERE / 'verify.py'

spec = importlib.util.spec_from_file_location('ext_verify', MODULE_PATH)
ext_verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ext_verify)

DEFAULT_ROOT = os.environ.get('EXT_TEST_ROOT') or str(HERE.parents[2])


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def call_id(n):
    return 'call_%024x' % n


def body_req1(system_len=2593, user_lens=(214, 3111, 679, 5525)):
    messages = [{'role': 'system', 'content': 'S' * system_len}]
    messages += [{'role': 'user', 'content': 'U' * n} for n in user_lens]
    return {'model': 'glm-5.3-flash', 'messages': messages, 'stream': True}


def body_req3(run_tag, delta=1016):
    base = body_req1()
    base['messages'].append({'role': 'assistant', 'content': None,
                             'tool_calls': [
                                 {'id': call_id(int(run_tag) * 2), 'type': 'function',
                                  'function': {'name': 'read_file', 'arguments': json.dumps({'path': 'TASK.md'})}},
                                 {'id': call_id(int(run_tag) * 2 + 1), 'type': 'function',
                                  'function': {'name': 'read_file', 'arguments': json.dumps({'path': 'inputs/exercises/dominoes/dominoes.py'})}},
                             ]})
    base['messages'].append({'role': 'tool', 'tool_call_id': call_id(int(run_tag) * 2),
                             'content': 'T' * 1200})
    base['messages'].append({'role': 'tool', 'tool_call_id': call_id(int(run_tag) * 2 + 1),
                             'content': 'R' * 203})
    raw1 = json.dumps(body_req1(), ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    raw3 = json.dumps(base, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    shortfall = delta - (len(raw3) - len(raw1))
    base['messages'][6]['content'] = 'T' * (1200 + shortfall)
    return base


def body_req2():
    return {'model': 'glm-5.3-flash', 'messages': [
        {'role': 'system', 'content': 'T' * 481}, {'role': 'user', 'content': 'u' * 302}]}


def write_run(base, label, rel, tag):
    root = base / rel
    (root / 'requests').mkdir(parents=True, exist_ok=True)
    (root / 'responses').mkdir(exist_ok=True)
    bodies = [body_req1(), body_req2(), body_req3(tag)]
    for name, body in zip(ext_verify.REQ_NAMES, bodies):
        raw = json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        (root / 'requests' / (name + '.request.bin')).write_bytes(raw)
        meta = {'upstream_status': 200, 'request_body_sha256': sha(raw),
                'request_body_bytes': len(raw), 'response_body_bytes': 1000}
        (root / 'responses' / (name + '.response.bin.meta.json')).write_text(json.dumps(meta))
    return root


def make_archive(tmp):
    base = tmp / 'archive'
    base.mkdir(exist_ok=True)
    labels = {'r1': 'loop1/capture', 'r2': 'loop5/capture-r2',
              'r3': 'loop6/capture-r3', 'r4': 'loop6/capture-r4', 'r5': 'loop6/capture-r5'}
    for i, (label, rel) in enumerate(sorted(labels.items())):
        write_run(base, label, rel, str(10 + i))
    return base


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix='ext-test-'))
        self.orig_pins = ext_verify.PINS
        ext_verify.PINS = {}
        self.addCleanup(self.cleanup)

    def cleanup(self):
        ext_verify.PINS = self.orig_pins

    def build(self, base=None):
        base = base or make_archive(self.tmp)
        return ext_verify.build(base)

    def validated(self, evidence=None, readme_sha=None):
        evidence = evidence or self.build()
        ext_verify.validate_public(evidence, pathlib.Path(DEFAULT_ROOT),
                                   readme_sha or 'a' * 64)
        return evidence


class BuildTests(Base):
    def test_happy_build_and_validate(self):
        evidence = self.build()
        evidence['readme_sha256'] = 'a' * 64
        ext_verify.validate_public(evidence, pathlib.Path(DEFAULT_ROOT), 'a' * 64)
        agg = evidence['aggregate']
        self.assertEqual(agg['stable_pairs'], 10)
        self.assertEqual(agg['d_residual_zero_pairs'], 10)

    def test_req1_divergence_breaks_stability(self):
        base = make_archive(self.tmp)
        req = base / 'loop6/capture-r3/requests/001.request.bin'
        raw = json.loads(req.read_bytes().decode('utf-8'))
        raw['messages'][2]['content'] = 'X' * 214
        req.write_bytes(json.dumps(raw, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
        with self.assertRaises(ext_verify.Invalid):
            ext_verify.build(base)

    def test_non_call_id_diff_leaf_rejected(self):
        base = make_archive(self.tmp)
        req = base / 'loop6/capture-r3/requests/003.request.bin'
        raw = json.loads(req.read_bytes().decode('utf-8'))
        raw['messages'][6]['content'] = 'Q' * 227
        req.write_bytes(json.dumps(raw, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
        with self.assertRaises(ext_verify.Invalid):
            ext_verify.build(base)

    def test_fifth_diff_leaf_rejected(self):
        base = make_archive(self.tmp)
        req = base / 'loop6/capture-r3/requests/003.request.bin'
        raw = json.loads(req.read_bytes().decode('utf-8'))
        raw['messages'][7]['content'] = 'Q' * 202
        req.write_bytes(json.dumps(raw, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
        with self.assertRaises(ext_verify.Invalid):
            ext_verify.build(base)

    def test_non_200_status_rejected_at_build(self):
        base = make_archive(self.tmp)
        meta_path = base / 'loop1/capture/responses/001.response.bin.meta.json'
        meta = json.loads(meta_path.read_text())
        meta['upstream_status'] = 500
        meta_path.write_text(json.dumps(meta))
        with self.assertRaises(ext_verify.Invalid):
            ext_verify.build(base)

    def test_meta_sha_mismatch_rejected(self):
        base = make_archive(self.tmp)
        meta_path = base / 'loop1/capture/responses/002.response.bin.meta.json'
        meta = json.loads(meta_path.read_text())
        meta['request_body_sha256'] = '0' * 64
        meta_path.write_text(json.dumps(meta))
        with self.assertRaises(ext_verify.Invalid):
            ext_verify.build(base)

    def test_duplicate_meta_key_rejected(self):
        base = make_archive(self.tmp)
        meta_path = base / 'loop1/capture/responses/003.response.bin.meta.json'
        meta_path.write_text('{"upstream_status":200,"upstream_status":200}')
        with self.assertRaises(ext_verify.Invalid):
            ext_verify.build(base)

    def test_nonfinite_meta_rejected(self):
        base = make_archive(self.tmp)
        meta_path = base / 'loop1/capture/responses/003.response.bin.meta.json'
        meta_path.write_text('{"upstream_status":NaN}')
        with self.assertRaises(ext_verify.Invalid):
            ext_verify.build(base)

    def test_normalize_ids_makes_d_class_equal(self):
        left = body_req3('1')
        right = body_req3('2')
        self.assertNotEqual(ext_verify.canon(left), ext_verify.canon(right))
        self.assertEqual(ext_verify.canon(ext_verify.normalize_ids(left)),
                         ext_verify.canon(ext_verify.normalize_ids(right)))


class ValidateTests(Base):
    def evidence(self):
        evidence = self.build()
        evidence['readme_sha256'] = 'a' * 64
        return evidence

    def test_schema_mismatch(self):
        evidence = self.evidence()
        evidence['schema'] = 'other'
        with self.assertRaises(ext_verify.Invalid):
            ext_verify.validate_public(evidence, pathlib.Path(DEFAULT_ROOT), 'a' * 64)

    def test_baseline_mismatch(self):
        evidence = self.evidence()
        evidence['baseline'] = 'deadbeef'
        with self.assertRaises(ext_verify.Invalid):
            ext_verify.validate_public(evidence, pathlib.Path(DEFAULT_ROOT), 'a' * 64)

    def test_readme_record_mismatch(self):
        evidence = self.evidence()
        with self.assertRaises(ext_verify.Invalid):
            ext_verify.validate_public(evidence, pathlib.Path(DEFAULT_ROOT), 'b' * 64)

    def test_missing_run_label(self):
        evidence = self.evidence()
        evidence['runs'].pop('r5')
        with self.assertRaises(ext_verify.Invalid):
            ext_verify.validate_public(evidence, pathlib.Path(DEFAULT_ROOT), 'a' * 64)

    def test_duplicate_req3_sha(self):
        evidence = self.evidence()
        evidence['runs']['r5']['req_sha'][2] = evidence['runs']['r4']['req_sha'][2]
        with self.assertRaises(ext_verify.Invalid):
            ext_verify.validate_public(evidence, pathlib.Path(DEFAULT_ROOT), 'a' * 64)

    def test_pair_coverage_gap(self):
        evidence = self.evidence()
        evidence['pairs'].pop()
        with self.assertRaises(ext_verify.Invalid):
            ext_verify.validate_public(evidence, pathlib.Path(DEFAULT_ROOT), 'a' * 64)

    def test_diff_leaf_count_tamper(self):
        evidence = self.evidence()
        evidence['pairs'][0]['req3_diff_leaves'] = 5
        with self.assertRaises(ext_verify.Invalid):
            ext_verify.validate_public(evidence, pathlib.Path(DEFAULT_ROOT), 'a' * 64)

    def test_verdict_tamper(self):
        evidence = self.evidence()
        evidence['pairs'][0]['verdict'] = 'UNSTABLE'
        with self.assertRaises(ext_verify.Invalid):
            ext_verify.validate_public(evidence, pathlib.Path(DEFAULT_ROOT), 'a' * 64)

    def test_aggregate_mismatch(self):
        evidence = self.evidence()
        evidence['aggregate']['stable_pairs'] = 9
        with self.assertRaises(ext_verify.Invalid):
            ext_verify.validate_public(evidence, pathlib.Path(DEFAULT_ROOT), 'a' * 64)

    def test_appended_shape_tamper(self):
        evidence = self.evidence()
        evidence['pairs'][0]['appended_descriptors'][0]['content_kind'] = 'str'
        with self.assertRaises(ext_verify.Invalid):
            ext_verify.validate_public(evidence, pathlib.Path(DEFAULT_ROOT), 'a' * 64)

    def test_unexpected_top_key(self):
        evidence = self.evidence()
        evidence['extra'] = 1
        with self.assertRaises(ext_verify.Invalid):
            ext_verify.validate_public(evidence, pathlib.Path(DEFAULT_ROOT), 'a' * 64)

    def test_pinned_file_tamper(self):
        pin_dir = self.tmp / 'pinned'
        pin_dir.mkdir()
        pin_file = pin_dir / 'dep.json'
        pin_file.write_text('{}')
        ext_verify.PINS = {str(pin_file.relative_to(self.tmp)): sha(pin_file.read_bytes())}
        evidence = self.evidence()
        pin_file.write_text('{"tampered":1}')
        try:
            with self.assertRaises(ext_verify.Invalid):
                ext_verify.validate_public(evidence, self.tmp, 'a' * 64)
        finally:
            ext_verify.PINS = {}

    def test_result_for_shape(self):
        evidence = self.evidence()
        result = ext_verify.result_for(evidence, 'e' * 64, 'a' * 64)
        self.assertEqual(result['schema'], ext_verify.SCHEMA_RESULT)
        self.assertEqual(result['primary']['assembly_stable_pairs'], '10/10')
        self.assertEqual(len(result['runs']), 5)


class CliTests(Base):
    def cli(self, script, *argv):
        return subprocess.run(
            [sys.executable, '-I', '-S', '-B', str(script)] + list(argv),
            capture_output=True, text=True, cwd=str(HERE))

    def repo_root_arg(self):
        return ['--root', DEFAULT_ROOT]

    def patched_constants(self):
        ext_verify.PINS = {}
        # CLI runs in a subprocess; patch via a sitecustomize-free env is not
        # possible, so CLI tests point --root at a tree where pinned files are
        # absent would fail. Instead copy the package into tmp with a stubbed
        # verify that has empty PINS.
        stub = self.tmp / 'pkg'
        stub.mkdir()
        import re as _re
        source = MODULE_PATH.read_text()
        source = _re.sub(r'PINS = \{.*?\n\}', 'PINS = {}', source, count=1, flags=_re.S)
        (stub / 'verify.py').write_text(source)
        (stub / 'README.md').write_text('stub readme\n')
        # README_REL has parents[2] relative README; place stub tree so that
        # parents[2]/README_REL resolves: stub pkg is pkg/, parents[2] is tmp.parent
        pkg_dir = self.tmp / '4-da' / 'pkg'
        pkg_dir.mkdir(parents=True)
        (pkg_dir / 'verify.py').write_text(source)
        readme_rel = pathlib.Path(ext_verify.README_REL)
        target = (pkg_dir / 'verify.py').resolve().parents[2] / readme_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('stub readme\n')
        return pkg_dir / 'verify.py'

    def test_cli_build_and_replay(self):
        base = make_archive(self.tmp)
        script = self.patched_constants()
        pkg_dir = script.parent
        out1 = self.tmp / 'evidence.json'
        out2 = self.tmp / 'result1.json'
        r1 = self.cli(str(script), '--root', str(pkg_dir.resolve().parents[2]),
                      '--archive-base', str(base),
                      '--build-evidence', str(out1), '--output', str(out2))
        self.assertEqual(r1.returncode, 0, r1.stderr)
        out3 = self.tmp / 'result2.json'
        r2 = self.cli(str(script), '--root', str(pkg_dir.resolve().parents[2]),
                      '--evidence', str(out1), '--output', str(out3))
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertEqual(pathlib.Path(out2).read_bytes(), pathlib.Path(out3).read_bytes())

    def test_cli_refuses_existing_output(self):
        base = make_archive(self.tmp)
        script = self.patched_constants()
        pkg_dir = script.parent
        out = self.tmp / 'result.json'
        out.write_text('x')
        r = self.cli(str(script), '--root', str(pkg_dir.resolve().parents[2]),
                     '--archive-base', str(base), '--build-evidence', str(self.tmp / 'e.json'),
                     '--output', str(out))
        self.assertEqual(r.returncode, 2)

    def test_cli_build_requires_archive_base(self):
        script = self.patched_constants()
        pkg_dir = script.parent
        r = self.cli(str(script), '--root', str(pkg_dir.resolve().parents[2]),
                     '--build-evidence', str(self.tmp / 'e.json'),
                     '--output', str(self.tmp / 'r.json'))
        self.assertEqual(r.returncode, 2)

    def test_cli_build_evidence_exclusive_with_evidence(self):
        script = self.patched_constants()
        pkg_dir = script.parent
        r = self.cli(str(script), '--root', str(pkg_dir.resolve().parents[2]),
                     '--archive-base', str(self.tmp), '--evidence', str(self.tmp / 'x.json'),
                     '--build-evidence', str(self.tmp / 'e.json'),
                     '--output', str(self.tmp / 'r.json'))
        self.assertEqual(r.returncode, 2)

    def test_cli_replay_rejects_tampered_evidence(self):
        script = self.patched_constants()
        pkg_dir = script.parent
        base = make_archive(self.tmp)
        out1 = self.tmp / 'evidence.json'
        out2 = self.tmp / 'result1.json'
        r1 = self.cli(str(script), '--root', str(pkg_dir.resolve().parents[2]),
                      '--archive-base', str(base),
                      '--build-evidence', str(out1), '--output', str(out2))
        self.assertEqual(r1.returncode, 0, r1.stderr)
        evidence = json.loads(out1.read_text())
        evidence['aggregate']['stable_pairs'] = 5
        bad = self.tmp / 'bad-evidence.json'
        bad.write_text(json.dumps(evidence))
        r2 = self.cli(str(script), '--root', str(pkg_dir.resolve().parents[2]),
                      '--evidence', str(bad), '--output', str(self.tmp / 'r3.json'))
        self.assertEqual(r2.returncode, 2)

    def test_cli_replay_requires_evidence(self):
        script = self.patched_constants()
        pkg_dir = script.parent
        r = self.cli(str(script), '--root', str(pkg_dir.resolve().parents[2]),
                     '--output', str(self.tmp / 'r.json'))
        self.assertEqual(r.returncode, 2)


class PathSafetyTests(Base):
    def test_exclusive_refuses_existing(self):
        target = self.tmp / 'out.json'
        target.write_text('x')
        with self.assertRaises(ext_verify.Invalid):
            ext_verify.exclusive(target, b'y')

    def test_exclusive_refuses_escape(self):
        with self.assertRaises(ext_verify.Invalid):
            ext_verify.exclusive(self.tmp / '..' / 'escape.json', b'y')

    def test_duplicate_top_key_rejected(self):
        with self.assertRaises(ext_verify.Invalid):
            ext_verify.load_json(b'{"a":1,"a":2}', 'x')

    def test_nonfinite_rejected(self):
        with self.assertRaises(ext_verify.Invalid):
            ext_verify.load_json(b'{"a":Infinity}', 'x')


if __name__ == '__main__':
    unittest.main()
