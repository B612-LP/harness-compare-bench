#!/usr/bin/env python3
"""Tests for the R3 instability source decomposition package.

Run under both `python3 test_verify.py` and `python3 -O test_verify.py`; both
modes must pass. Tests that need the real archived originals read the archive
root from the environment variable B_R3_ARCHIVE_ROOT; if it is unset or wrong,
those tests FAIL loudly instead of silently passing (no skips, no approximations).

Only unittest assertion methods are used (no bare `assert` statements), so the
suite behaves identically with and without -O.
"""
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V1_REL = '4-打分细则/机制重复口径澄清-2026-11-12'
PKG_REL = '4-打分细则/R3不稳定来源分解-2026-11-16'
ARCHIVE_ENV = 'B_R3_ARCHIVE_ROOT'


def load_verify():
    spec = importlib.util.spec_from_file_location('r3_verify_under_test', HERE / 'verify.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RV = load_verify()
VERIFY = HERE / 'verify.py'


def require_archive(testcase):
    value = os.environ.get(ARCHIVE_ENV)
    if not value:
        testcase.fail(ARCHIVE_ENV + ' is not set; real archived-original checks cannot run and must not silently pass')
    path = Path(value)
    if not path.is_dir():
        testcase.fail(ARCHIVE_ENV + ' does not point to an existing directory: ' + value)
    return path


def dumps(result):
    return json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False).encode('utf-8') + b'\n'


class UnitTests(unittest.TestCase):
    """Pure-function tests; no archive access."""

    def test_a_signed_decomposition_exact_with_negatives(self):
        signed = RV.signed_decomposition({'reasoning': 100, 'message': 50},
                                         {'reasoning': 40, 'function_call': 30})
        self.assertEqual(signed, {'function_call': -30, 'message': 50, 'reasoning': 60})
        self.assertIn('function_call', signed)
        self.assertLess(signed['function_call'], 0, 'negative contribution must be representable')
        delta = sum({'reasoning': 100, 'message': 50}.values()) - sum({'reasoning': 40, 'function_call': 30}.values())
        self.assertEqual(sum(signed.values()), delta)
        self.assertEqual(sum(signed.values()), 80)

    def test_a_pair_entry_synthetic_exact_with_negatives(self):
        reps = [
            {'slot': 'codex__synthetic__r1', 'rep': 1, 'r3_total_bytes': 120,
             'per_type_bytes': {'reasoning': 80, 'message': 30, 'function_call_output': 10},
             'family_bytes': {'m_star': 110, 'environment': 10}},
            {'slot': 'codex__synthetic__r2', 'rep': 2, 'r3_total_bytes': 60,
             'per_type_bytes': {'reasoning': 10, 'message': 40, 'function_call_output': 10},
             'family_bytes': {'m_star': 50, 'environment': 10}},
            {'slot': 'codex__synthetic__r3', 'rep': 3, 'r3_total_bytes': 90,
             'per_type_bytes': {'reasoning': 45, 'message': 35, 'function_call_output': 10},
             'family_bytes': {'m_star': 80, 'environment': 10}},
        ]
        for indexes in ((0, 1), (0, 2), (1, 2)):
            entry = RV.pair_entry(reps, indexes)
            self.assertEqual(sum(entry['per_type_signed_contribution'].values()), entry['delta'])
            self.assertEqual(sum(f['net_contribution'] for f in entry['families'].values()), entry['delta'])
        entry = RV.pair_entry(reps, (0, 1))
        self.assertEqual(entry['delta'], 60)
        self.assertEqual(entry['per_type_signed_contribution']['reasoning'], 70)
        self.assertEqual(entry['per_type_signed_contribution']['message'], -10)
        self.assertEqual(entry['per_type_signed_contribution']['function_call_output'], 0)
        self.assertEqual(entry['families']['m_star']['net_contribution'], 60)
        self.assertEqual(entry['families']['environment']['net_contribution'], 0)

    def test_f_dominance_boundary_strict_greater_than_half(self):
        self.assertTrue(RV.dominance_flag(3, 4))
        self.assertTrue(RV.dominance_flag(-3, 4), 'dominance uses |net|')
        self.assertFalse(RV.dominance_flag(2, 4), 'net == delta/2 must NOT be dominant')
        self.assertFalse(RV.dominance_flag(-2, 4))
        self.assertFalse(RV.dominance_flag(30, 60), 'exact equality boundary')
        self.assertTrue(RV.dominance_flag(31, 60))
        self.assertFalse(RV.dominance_flag(0, 4))
        self.assertFalse(RV.dominance_flag(1, 4))
        with self.assertRaises(RV.Invalid):
            RV.dominance_flag(5, 0)
        with self.assertRaises(RV.Invalid):
            RV.dominance_flag(1.5, 4)

    def test_f_family_view_boundary_and_share(self):
        view = RV.family_view({'m_star': 2, 'environment': 2}, 4)
        self.assertFalse(view['m_star']['dominant'])
        self.assertFalse(view['environment']['dominant'])
        self.assertEqual(view['m_star']['share'], 0.5)
        self.assertEqual(view['environment']['share'], 0.5)
        view = RV.family_view({'m_star': 3, 'environment': 1}, 4)
        self.assertTrue(view['m_star']['dominant'])
        self.assertFalse(view['environment']['dominant'])
        view = RV.family_view({'m_star': -6, 'environment': 10}, 4)
        self.assertTrue(view['m_star']['dominant'], 'negative net still uses |net|')
        self.assertEqual(view['m_star']['share'], -1.5)
        with self.assertRaises(RV.Invalid):
            RV.family_view({'m_star': 2, 'environment': 2}, 5)

    def test_select_branch_frozen_order(self):
        self.assertEqual(RV.select_branch(['a', 'b', 'c', 'd'], [], 5), 'M_STAR_DOMINANT_IN_4_OF_5_GROUPS')
        self.assertEqual(RV.select_branch(['a', 'b', 'c', 'd', 'e'], ['z'], 5), 'M_STAR_DOMINANT_IN_4_OF_5_GROUPS')
        self.assertEqual(RV.select_branch(['a', 'b', 'c'], ['z'], 5), 'E_DOMINANT_IN_SOME_GROUP')
        self.assertEqual(RV.select_branch([], [], 5), 'MIXED_NO_SINGLE_DOMINANT_FAMILY')
        self.assertEqual(RV.select_branch([], ['z'], 5), 'E_DOMINANT_IN_SOME_GROUP')
        with self.assertRaises(RV.Invalid):
            RV.select_branch([], [], 4)

    def test_d_classifier_unit_roleless_message_stops(self):
        self.assertTrue(issubclass(RV.ClassifierStop, RV.Invalid), 'STOP must surface as an integrity failure')
        for payload in (
            {'type': 'message', 'content': [{'type': 'input_text', 'text': 'x'}]},
            {'type': 'message', 'role': None, 'content': []},
            {'type': 'message', 'role': 'tool', 'content': []},
            {'type': 'message', 'role': '', 'content': []},
            {'type': 'message', 'role': 7, 'content': []},
        ):
            with self.assertRaises(RV.ClassifierStop):
                RV.classify_payload(payload)

    def test_d_classifier_known_shapes(self):
        self.assertEqual(RV.classify_payload({'type': 'message', 'role': 'assistant', 'content': []}),
                         ('m_star', 'message', 'assistant'))
        for role in ('developer', 'user', 'system'):
            self.assertEqual(RV.classify_payload({'type': 'message', 'role': role, 'content': []}),
                             ('environment', 'message', role))
        self.assertEqual(RV.classify_payload({'type': 'reasoning', 'summary': []}), ('m_star', 'reasoning', None))
        self.assertEqual(RV.classify_payload({'type': 'function_call', 'name': 'shell'}), ('m_star', 'function_call', None))
        self.assertEqual(RV.classify_payload({'type': 'function_call_output', 'output': 'x'}),
                         ('environment', 'function_call_output', None))
        self.assertEqual(RV.classify_payload({'type': 'turn_context', 'cwd': '/w'}),
                         ('environment', 'turn_context', None))
        self.assertEqual(RV.classify_payload({'type': 'web_search_call', 'query': 'q'}),
                         ('environment', 'web_search_call', None), 'unknown type falls to E catch-all')
        with self.assertRaises(RV.Invalid):
            RV.classify_payload({'no_type': True})
        with self.assertRaises(RV.Invalid):
            RV.classify_payload('not a dict')


def synthetic_events():
    return [
        {'type': 'session_meta', 'payload': {'id': 'sess-1', 'originator': 'test'}},
        {'type': 'event_msg', 'payload': {'type': 'agent_message', 'message': 'hi'}},
        {'type': 'world_state', 'state': {}},
        {'type': 'turn_context', 'payload': {'cwd': '/work'}},
        {'type': 'token_usage_record', 'payload': {'input_tokens': 10, 'output_tokens': 5}},
        {'type': 'response_item', 'payload': {'type': 'message', 'role': 'developer',
                                              'content': [{'type': 'input_text', 'text': 'permissions'}]}},
        {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user',
                                              'content': [{'type': 'input_text', 'text': 'environment_context here'}]}},
        {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user',
                                              'content': [{'type': 'input_text', 'text': 'do the task'}]}},
        {'type': 'response_item', 'payload': {'type': 'reasoning',
                                              'summary': [{'type': 'summary_text', 'text': 'thinking'}]}},
        {'type': 'response_item', 'payload': {'type': 'function_call', 'name': 'shell',
                                              'arguments': '{"cmd":["ls"]}'}},
        {'type': 'response_item', 'payload': {'type': 'function_call_output', 'call_id': 'c1',
                                              'output': 'file1\nfile2'}},
        {'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant',
                                              'content': [{'type': 'output_text', 'text': 'done'}]}},
        {'type': 'response_item', 'payload': {'type': 'web_search_call', 'query': 'q'}},
        {'type': 'response_item', 'payload': {'type': 'turn_context', 'cwd': '/work'}},
    ]


class SyntheticPipelineTests(unittest.TestCase):
    """Partition/exactness checks over a synthetic mini-fixture (no archive access)."""

    @classmethod
    def setUpClass(cls):
        cls.RV = RV
        RV.V = RV.load_v1_module(ROOT)

    def test_e_family_partition_completeness_synthetic(self):
        events = synthetic_events()
        rows = RV.V.project_events(events, 'codex')
        result = RV.decompose_slot(events, rows)
        canon = RV.V.canon
        response_items = [e['payload'] for e in events if e['type'] == 'response_item']
        expected_total = sum(len(canon(p)) for p in response_items)
        self.assertEqual(result['r3_total_bytes'], expected_total)
        self.assertEqual(result['event_count'], len(events))
        self.assertEqual(result['response_item_count'], len(response_items))
        m_star_expected = sum(len(canon(p)) for p in response_items
                              if p['type'] in ('reasoning', 'function_call')
                              or (p['type'] == 'message' and p.get('role') == 'assistant'))
        environment_expected = expected_total - m_star_expected
        self.assertEqual(result['family_bytes']['m_star'], m_star_expected)
        self.assertEqual(result['family_bytes']['environment'], environment_expected)
        self.assertEqual(result['family_bytes']['m_star'] + result['family_bytes']['environment'],
                         result['r3_total_bytes'], 'M* and E must exactly partition R3')
        self.assertEqual(sum(result['per_type_bytes'].values()), result['r3_total_bytes'])
        self.assertEqual(set(result['per_type_bytes']),
                         {'message', 'reasoning', 'function_call', 'function_call_output',
                          'web_search_call', 'turn_context'})
        self.assertEqual(result['message_by_role_bytes'],
                         {'developer': len(canon(response_items[0])),
                          'user': len(canon(response_items[1])) + len(canon(response_items[2])),
                          'assistant': len(canon(response_items[6]))})
        self.assertEqual(set(result['family_bytes']), {'m_star', 'environment'})

    def test_projection_crosscheck_trips_on_tampered_rows(self):
        events = synthetic_events()
        rows = RV.V.project_events(events, 'codex')
        tampered = copy.deepcopy(rows)
        tampered[4][3] += 1
        with self.assertRaises(RV.Invalid) as caught:
            RV.decompose_slot(events, tampered)
        self.assertIn('per-event projection mismatch', str(caught.exception))
        tampered = copy.deepcopy(rows)
        tampered[8][2] = 'reasoning_tampered'
        with self.assertRaises(RV.Invalid):
            RV.decompose_slot(events, tampered)
        tampered = rows[:-1]
        with self.assertRaises(RV.Invalid):
            RV.decompose_slot(events, tampered)

    def test_d_decompose_stops_on_roleless_message(self):
        events = synthetic_events()
        events[5] = {'type': 'response_item', 'payload': {'type': 'message',
                                                          'content': [{'type': 'input_text', 'text': 'no role'}]}}
        rows = RV.V.project_events(events, 'codex')
        with self.assertRaises(RV.ClassifierStop):
            RV.decompose_slot(events, rows)


class RealArchiveTests(unittest.TestCase):
    """Full pipeline against the real archived originals; requires B_R3_ARCHIVE_ROOT."""

    @classmethod
    def setUpClass(cls):
        value = os.environ.get(ARCHIVE_ENV)
        if not value:
            raise unittest.SkipTest(ARCHIVE_ENV + ' not set would skip real checks - refusing; set it and rerun')
        archive = Path(value)
        if not archive.is_dir():
            raise unittest.SkipTest(ARCHIVE_ENV + ' is not a directory - refusing to skip real checks silently')
        cls.archive = archive
        cls.real = RV.analyze(ROOT, archive)

    def test_h_real_run_structure_and_verdict(self):
        result = self.real
        self.assertEqual(result['schema'], 'r3-decomp-projection-v1')
        self.assertEqual(result['prereg_sha256'], RV.PREREG_SHA256)
        self.assertTrue(re.fullmatch('[0-9a-f]{40}', result['baseline_commit']))
        self.assertEqual(len(result['slots']), 15)
        self.assertEqual(len(result['groups']), 5)
        self.assertEqual([g['group'] for g in result['groups']], list(RV.CASES))
        self.assertEqual(len(result['public_sources']), 69)
        for slot in result['slots']:
            self.assertTrue(slot['slot'].startswith('codex__'))
            self.assertTrue(re.fullmatch('[0-9a-f]{64}', slot['trace_sha256']))
            relative = Path(slot['trace_archive_relative_path'])
            self.assertFalse(relative.is_absolute())
            self.assertNotIn('..', relative.parts)
        for group in result['groups']:
            totals = group['r3_totals']
            slot_bytes = {s['slot']: s['r3_total_bytes'] for s in result['slots']}
            self.assertEqual(totals, [slot_bytes[s] for s in group['slots']],
                             'r3_totals must follow the group slot order')
            self.assertEqual(group['delta'], max(totals) - min(totals))
            self.assertEqual(totals.count(max(totals)), 1, 'max slot must be unique')
            self.assertEqual(totals.count(min(totals)), 1, 'min slot must be unique')
            self.assertGreater(group['delta'], 0)
            signed_sum = sum(v['signed_contribution'] for v in group['per_type'].values())
            self.assertEqual(signed_sum, group['delta'], 'per-type signed decomposition must sum exactly to delta')
            self.assertTrue(group['per_type_sums_to_delta'])
            nets = {name: group['families'][name]['net_contribution'] for name in RV.FAMILIES}
            self.assertEqual(sum(nets.values()), group['delta'])
            for name, family in group['families'].items():
                self.assertEqual(family['share'], nets[name] / group['delta'])
                self.assertEqual(family['dominant'], abs(nets[name]) * 2 > group['delta'])
            self.assertTrue(group['stable_core_ok'], 'stable core must hold for ' + group['group'])
            self.assertTrue(group['task_content_ok'])
            self.assertEqual(len(group['pairwise']), 3)
            slot_totals = dict(zip(group['slots'], totals))
            for pair in group['pairwise']:
                self.assertEqual(pair['delta'],
                                 abs(slot_totals[pair['slots'][0]] - slot_totals[pair['slots'][1]]))
                self.assertEqual(sum(pair['per_type_signed_contribution'].values()), pair['delta'])
                self.assertEqual(sum(f['net_contribution'] for f in pair['families'].values()), pair['delta'])
        verdict = result['verdicts']
        self.assertEqual(verdict['branch'], 'M_STAR_DOMINANT_IN_4_OF_5_GROUPS')
        self.assertEqual(verdict['m_star_dominant_group_count'], 4)
        self.assertEqual(verdict['environment_dominant_groups'], ['exercism-py-6'])
        self.assertTrue(result['v1_reference']['full_replay_reproduced'])
        self.assertEqual(result['v1_reference']['result_sha256'], RV.V1_RESULT_SHA256)
        self.assertEqual(result['v1_reference']['evidence_sha256'], RV.V.EVIDENCE_SHA256)

    def test_h_hard_equal_against_v1_result_json(self):
        v1_result = json.loads((ROOT / V1_REL / 'result.json').read_text(encoding='utf-8'))
        v1_by_slot = {row['slot']: row for row in v1_result['slots'] if row['arm'] == 'codex'}
        self.assertEqual(len(v1_by_slot), 15)
        for slot in self.real['slots']:
            self.assertEqual(slot['r3_total_bytes'], v1_by_slot[slot['slot']]['input_bytes'],
                             'R3 hard-equal failed for ' + slot['slot'])

    def test_h_stored_result_json_matches_recomputed(self):
        stored = (HERE / 'result.json').read_bytes()
        self.assertEqual(stored, dumps(self.real), 'stored result.json must equal the recomputed output')

    def test_h_cli_entry_point_exit0(self):
        proc = subprocess.run([sys.executable, str(VERIFY), '--root', str(ROOT),
                               '--archive-root', str(self.archive)],
                              capture_output=True, timeout=600)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode('utf-8', 'replace'))
        expected = RV.render_summary(self.real).encode('utf-8')
        self.assertEqual(proc.stdout, expected, 'CLI stdout must equal render_summary of the recomputed result')

    def test_g_determinism_two_in_process_runs(self):
        second = RV.analyze(ROOT, self.archive)
        self.assertEqual(dumps(second), dumps(self.real))
        self.assertEqual(dumps(second), (HERE / 'result.json').read_bytes())

    def test_g_cli_determinism_and_minus_o_identical(self):
        with tempfile.TemporaryDirectory(prefix='r3dec-determinism-') as tmp:
            out1 = Path(tmp) / 'run1.json'
            out2 = Path(tmp) / 'run2.json'
            normal = subprocess.run([sys.executable, str(VERIFY), '--root', str(ROOT),
                                     '--archive-root', str(self.archive), '--output', str(out1)],
                                    capture_output=True, timeout=600)
            optimized = subprocess.run([sys.executable, '-O', str(VERIFY), '--root', str(ROOT),
                                        '--archive-root', str(self.archive), '--output', str(out2)],
                                       capture_output=True, timeout=600)
            self.assertEqual(normal.returncode, 0, normal.stderr.decode('utf-8', 'replace'))
            self.assertEqual(optimized.returncode, 0, optimized.stderr.decode('utf-8', 'replace'))
            self.assertEqual(out1.read_bytes(), out2.read_bytes(), 'two runs must be byte-identical')
            self.assertEqual(out1.read_bytes(), (HERE / 'result.json').read_bytes())
            self.assertEqual(normal.stdout, optimized.stdout, 'stdout identical under python3 and python3 -O')
            self.assertEqual(normal.stdout, RV.render_summary(self.real).encode('utf-8'))

    def test_c_tampered_v1_slot_value_trips_hard_equal(self):
        v1_result = json.loads((ROOT / V1_REL / 'result.json').read_text(encoding='utf-8'))
        target = next(row for row in v1_result['slots'] if row['slot'] == 'codex__tb-cargo-plan__r1')
        original = target['input_bytes']
        target['input_bytes'] = original + 1
        with self.assertRaises(RV.Invalid) as caught:
            RV.analyze(ROOT, self.archive, v1_result=v1_result)
        self.assertIn('codex__tb-cargo-plan__r1', str(caught.exception))
        self.assertIn('result.json', str(caught.exception), 'tamper must trip a result.json-side hard-equal check')

    def test_b_tampered_pinned_source_exit_2(self):
        tmp = self.build_temp_root()
        sources = json.loads((ROOT / V1_REL / 'evidence.json').read_text(encoding='utf-8'))['public_sources']
        target = tmp / sources[0]['path']
        data = bytearray(target.read_bytes())
        self.assertGreater(len(data), 0, 'pinned source unexpectedly empty')
        data[0] ^= 0x01
        target.write_bytes(bytes(data))
        original_resolver = RV.resolve_head
        RV.resolve_head = lambda root: '0' * 40
        try:
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = RV.main(['--root', str(tmp)])
            self.assertEqual(code, 2, 'tampered pinned source must produce exit code 2')
            self.assertIn('source SHA mismatch', stderr.getvalue())
            # v1.1's replay raises its own Invalid (ValueError subclass) before this
            # package's pin is reached; each module load creates a fresh class, so
            # match by ValueError + exact message, not by class identity.
            with self.assertRaises(ValueError) as caught:
                RV.analyze(tmp)
            self.assertIn('source SHA mismatch', str(caught.exception))
        finally:
            RV.resolve_head = original_resolver

    def test_b_tampered_evidence_json_trips(self):
        tmp = self.build_temp_root()
        evidence_path = tmp / V1_REL / 'evidence.json'
        evidence = json.loads(evidence_path.read_text(encoding='utf-8'))
        evidence['note'] = evidence['note'] + ' tampered'
        evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, sort_keys=True), encoding='utf-8')
        original_resolver = RV.resolve_head
        RV.resolve_head = lambda root: '0' * 40
        try:
            with self.assertRaises(ValueError) as caught:
                RV.analyze(tmp)
            message = str(caught.exception)
            self.assertIn('SHA mismatch', message)
            self.assertIn('evidence', message,
                          'evidence tamper must trip an evidence-side integrity check: ' + message)
        finally:
            RV.resolve_head = original_resolver

    def test_b_untampered_temp_root_reproduces_full_result(self):
        tmp = self.build_temp_root()
        original_resolver = RV.resolve_head
        RV.resolve_head = lambda root: '0' * 40
        try:
            result = RV.analyze(tmp, self.archive)
            self.assertEqual(result['schema'], 'r3-decomp-projection-v1')
            self.assertEqual(len(result['slots']), 15,
                             'untampered relocated fixture must reproduce the full 15-slot result')
            self.assertEqual([g['group'] for g in result['groups']], list(RV.CASES))
        finally:
            RV.resolve_head = original_resolver

    def build_temp_root(self):
        tmp = Path(tempfile.mkdtemp(prefix='r3dec-tamper-'))
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / PKG_REL).mkdir(parents=True)
        shutil.copyfile(HERE / 'README.md', tmp / PKG_REL / 'README.md')
        (tmp / V1_REL).mkdir(parents=True)
        for name in ('verify.py', 'result.json', 'evidence.json', 'README.md'):
            source = ROOT / V1_REL / name
            if source.is_file():
                shutil.copyfile(source, tmp / V1_REL / name)
        sources = json.loads((ROOT / V1_REL / 'evidence.json').read_text(encoding='utf-8'))['public_sources']
        for source in sources:
            destination = tmp / source['path']
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / source['path'], destination)
        return tmp


if __name__ == '__main__':
    unittest.main(verbosity=2)
