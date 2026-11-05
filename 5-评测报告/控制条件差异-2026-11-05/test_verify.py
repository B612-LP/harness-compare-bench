#!/usr/bin/env python3
"""Synthetic-copy tests only; no candidate/checker/product code is executed."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('controls_verify', HERE / 'verify.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


class ControlsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f = v.load_formal(ROOT)
        cls.baseline = v.verify(ROOT)
        cls.closure = cls.f.derive(ROOT)
        cls.tmp = tempfile.TemporaryDirectory(prefix='control-tests-')
        cls.base = Path(cls.tmp.name) / 'base'
        names = {x['path'] for x in cls.closure['source_inventory'] if x['status'] == 'present'}
        names.update((cls.f.LEDGER, cls.f.REPORT, v.FORMAL, v.VIEW, v.HERE + 'summary.md'))
        for name in names:
            dest = cls.base / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dest)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.case = tempfile.TemporaryDirectory(dir=self.tmp.name, prefix='case-')
        self.root = Path(self.case.name) / 'repo'
        shutil.copytree(self.base, self.root)

    def tearDown(self):
        self.case.cleanup()

    def edit_json(self, name, change):
        path = self.root / name
        data = json.loads(path.read_text(encoding='utf-8'))
        change(data)
        path.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False), encoding='utf-8')

    def reject_view(self, mutate):
        wrong = copy.deepcopy(self.baseline)
        mutate(wrong)
        with self.assertRaises(ValueError):
            v.validate_view(wrong, self.baseline, self.f.same)

    def semantic_reject(self, change):
        # TEST ONLY: byte pins disabled to exercise semantic joins below them.
        # There is no public CLI or runtime switch for this bypass.
        change()
        with patch.object(v, 'load_formal', return_value=self.f), patch.object(self.f.Store, 'check_hash', return_value=None):
            with self.assertRaises((ValueError, KeyError, TypeError, IndexError)):
                v.verify(self.root)

    def test_real_baseline_30_25_5_5(self):
        d = v.verify(self.root)
        self.assertEqual((d['attempt_count'], d['formal_count'], len(d['replacement_comparisons']), len(d['A_finite_TASK_comparisons'])), (30, 25, 5, 5))
        self.assertEqual(d['formal_track_counts'], {'A_same_model': 10, 'B_native': 10, 'W_gateway': 5})
        self.assertEqual(sorted(d['formal_generation_counts'].values()), [1, 1, 2, 3, 8, 10])
        self.assertEqual(d['formal_summary_unchanged']['codex']['weighted_sum'], 444.81)
        self.assertEqual(d['formal_summary_unchanged']['dsh']['weighted_sum'], 444.07)
        self.assertEqual(d['historical_inventory_unchanged']['B_observation_version_unknown'], 40)
        self.assertEqual(len(d['historical_inventory_unchanged']['missing']), 5)

    def test_actual_unknowns_never_upgraded(self):
        for r in self.baseline['rows']:
            for k in ('backend_model_identity', 'actual_reasoning_budget'):
                self.assertEqual(r['controls'][k]['state'], 'unknown')
                self.assertIsNone(r['controls'][k]['value'])
        for r in self.baseline['rows']:
            if r['track'] == 'B_native':
                self.assertEqual(r['controls']['declared_effort']['state'], 'unknown')
                self.assertEqual(r['controls']['route_protocol']['state'], 'unknown')

    def test_all_undisclosed_build_labels_stay_noncomparable(self):
        selected = [r for r in self.baseline['rows'] if isinstance(r['controls']['product_version']['value'], str) and 'app_build=undisclosed(closed)' in r['controls']['product_version']['value']]
        self.assertEqual(len(selected), 6)
        for row in selected:
            self.assertEqual(row['controls']['product_version']['state'], 'not_directly_comparable')
        edge = next(e for e in self.baseline['replacement_comparisons'] if e['child'] == 'formal-b2-doubao-exercism-py-6-01')
        self.assertEqual(edge['field_comparisons']['product_version'], 'not_directly_comparable')

    def test_compare_null_is_unknown_not_same(self):
        c = v.cell(None, [{'path': 'meta.json'}], 'unknown')
        self.assertEqual(v.compare(c, c), 'unknown')

    def test_compare_true_and_one_are_different_JSON_values(self):
        self.assertEqual(v.compare(v.cell(True, [{'path': 'a'}]), v.cell(1, [{'path': 'b'}])), 'different_recorded_value')

    def test_compare_false_and_zero_are_different_JSON_values(self):
        self.assertEqual(v.compare(v.cell(False, [{'path': 'a'}]), v.cell(0, [{'path': 'b'}])), 'different_recorded_value')

    def test_compare_nested_boolean_and_number_are_different_JSON_values(self):
        self.assertEqual(v.compare(v.cell({'read': True}, [{'path': 'a'}]), v.cell({'read': 1}, [{'path': 'b'}])), 'different_recorded_value')

    def test_compare_opaque_build_not_directly_comparable(self):
        c = v.cell('closed', [{'path': 'meta.json'}], 'not_directly_comparable')
        self.assertEqual(v.compare(c, c), 'not_directly_comparable')

    def test_compare_domain_not_directly_comparable(self):
        a = v.cell('same-hash', [{'path': 'a'}]); b = copy.deepcopy(a)
        a['representation'] = 'public_derived'; b['representation'] = 'recorded_public_task'
        self.assertEqual(v.compare(a, b), 'not_directly_comparable')

    def test_cell_unknown_with_value_rejected(self):
        with self.assertRaises(ValueError):
            v.cell('backend-proven', [{'path': 'meta.json'}], 'unknown')

    def test_all_control_cells_have_source_pins(self):
        for r in self.baseline['rows']:
            for c in r['controls'].values():
                self.assertTrue(c['sources'])
                for s in c['sources']:
                    self.assertTrue({'path', 'sha256', 'pointer'} <= set(s))
                    self.assertEqual(hashlib.sha256((ROOT / s['path']).read_bytes()).hexdigest(), s['sha256'])

    def test_A_exact_finite_differences(self):
        for pair in self.baseline['A_finite_TASK_comparisons']:
            diff = pair['public_task_diff']
            self.assertFalse(diff['semantic_equivalence_proven'])
            self.assertEqual([x['left_lines_1_based_half_open'] for x in diff['changed_line_ranges']], [[1, 2], [3, 4]])
            self.assertTrue(all(x['left_text'] and x['right_text'] for x in diff['changed_line_ranges']))
            self.assertEqual(pair['field_comparisons']['declared_effort'], 'same_recorded_value')
            self.assertEqual(pair['field_comparisons']['route_protocol'], 'different_recorded_value')

    def test_A_display_transform_does_not_change_raw_computation(self):
        store = self.f.Store(ROOT)
        store.expected.update({s['path']: s['sha256'] for s in self.closure['source_inventory']})
        indexed = {r['event_id']: r['controls'] for r in self.baseline['rows']}
        for pair in self.baseline['A_finite_TASK_comparisons']:
            raw = v.task_diff(store, indexed[pair['left']], indexed[pair['right']])
            shown = v.display_A_home(copy.deepcopy(raw))
            self.assertEqual(shown, pair['public_task_diff'])
            self.assertTrue(shown['not_original_bytes'])
            self.assertTrue(shown['display_transform']['source_sha_and_line_ranges_unchanged'])
            for key in raw:
                if key != 'changed_line_ranges':
                    self.assertEqual(raw[key], shown[key])
            for before, after in zip(raw['changed_line_ranges'], shown['changed_line_ranges']):
                for key in ('operation', 'left_lines_1_based_half_open', 'right_lines_1_based_half_open'):
                    self.assertEqual(before[key], after[key])
                if before['left_lines_1_based_half_open'] == [3, 4]:
                    for side in ('left', 'right'):
                        self.assertIn('/Users/', before[side + '_text'][0])
                        self.assertIn('[HOME]/', after[side + '_text'][0])
                        self.assertNotIn('/Users/', after[side + '_text'][0])
                        self.assertEqual(before[side + '_text'][0].splitlines(keepends=True)[0][-1:], after[side + '_text'][0][-1:])
                else:
                    self.assertEqual(before, after)

    def test_A_display_cannot_be_claimed_original_or_unlabelled(self):
        def without_label(d):
            d['A_finite_TASK_comparisons'][0]['public_task_diff'].pop('display_transform')
        def original_claim(d):
            d['A_finite_TASK_comparisons'][0]['public_task_diff']['not_original_bytes'] = False
        for mutation in (without_label, original_claim):
            with self.subTest(mutation=mutation.__name__):
                self.reject_view(mutation)

    def test_new_view_does_not_reprint_local_home_paths(self):
        self.assertNotIn('/Users/', json.dumps(self.baseline, ensure_ascii=False))

    def test_predecessor_and_registration_sources_not_confused(self):
        for edge in self.baseline['replacement_comparisons']:
            self.assertTrue(edge['child_registration_source']['pointer'].startswith('/registrations/'))
            self.assertNotEqual(edge['child_registration_source']['pointer'], edge['predecessor_source']['pointer'])
            source = edge['child_registration_source']
            doc = json.loads((ROOT / source['path']).read_text(encoding='utf-8'))
            self.assertEqual(self.f.pointer(doc, source['pointer'])['event_id'], edge['child'])

    def test_DB_cargo_boundary_text_preserved(self):
        edge = next(e for e in self.baseline['replacement_comparisons'] if e['child'] == 'formal-b3-doubao-tb-cargo-plan-01')
        fields = edge['field_comparisons']
        self.assertEqual(fields['case_sha256'], 'same_recorded_value')
        self.assertEqual(fields['product_version'], 'different_recorded_value')
        inserts = [r for r in edge['public_task_diff']['changed_line_ranges'] if r['operation'] == 'insert']
        self.assertTrue(any('边界' in text for r in inserts for text in r['right_text']))

    def test_WB_three_derived_domains_preserved(self):
        edges = [e for e in self.baseline['replacement_comparisons'] if e['child'].startswith('r20261031-wb-replacement:')]
        self.assertEqual(len(edges), 3)
        for e in edges:
            self.assertEqual(e['public_task_diff']['status'], 'not_directly_comparable')
            self.assertFalse(e['public_task_diff']['public_bytes_equal'])
            self.assertTrue(e['public_task_diff']['changed_line_ranges'])

    def test_read_only_no_process_or_network(self):
        def snapshot():
            return {str(p.relative_to(self.root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob('*') if p.is_file()}
        before = snapshot()
        with patch.object(subprocess, 'Popen', side_effect=AssertionError('no process')), patch.object(socket, 'socket', side_effect=AssertionError('no network')):
            v.verify(self.root)
        self.assertEqual(before, snapshot())

    def test_formal_dependency_changed_rejected_before_execution(self):
        path = self.root / v.FORMAL
        path.write_text("raise RuntimeError('must not execute')\n", encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'dependency SHA mismatch'):
            v.load_formal(self.root)

    def test_reviewed_dependency_uses_checked_source_not_import_loader(self):
        with patch('importlib.util.spec_from_file_location', side_effect=AssertionError('must not use cached-bytecode loader')):
            loaded = v.load_formal(self.root)
        self.assertNotEqual(loaded.__name__, '__main__')
        self.assertEqual(loaded.GENERATIONS, self.f.GENERATIONS)

    def test_missing_source_rejected(self):
        path = self.root / self.baseline['rows'][0]['controls']['public_task']['sources'][0]['path']
        path.unlink()
        with self.assertRaises(ValueError):
            v.verify(self.root)

    def test_source_effort_change_pin_rejected(self):
        name = self.baseline['rows'][0]['controls']['declared_effort']['sources'][0]['path']
        self.edit_json(name, lambda d: d.update(reasoning_effort='high'))
        with self.assertRaises(ValueError):
            v.verify(self.root)

    def test_semantic_effort_change_rejected(self):
        name = self.baseline['rows'][0]['controls']['declared_effort']['sources'][0]['path']
        self.semantic_reject(lambda: self.edit_json(name, lambda d: d.update(reasoning_effort='high')))

    def test_semantic_same_score_wrong_source_rejected(self):
        name = self.baseline['rows'][2]['event_source']['path']
        def change(d):
            events = d['events']
            target = next(e for e in events if e['event_id'] == 'formal-a1-codex-exercism-py-6-01')
            other = next(e for e in events if e['event_id'] == 'formal-a1-dsh-exercism-py-6-01')
            source = other['sources'][other['score']['refs'][0]['source']]
            target['sources'].append(source)
            target['score']['refs'] = [{'source': len(target['sources']) - 1, 'pointer': other['score']['refs'][0]['pointer']}]
        self.semantic_reject(lambda: self.edit_json(name, change))

    def test_semantic_boundary_deletion_rejected(self):
        row = next(r for r in self.baseline['rows'] if r['event_id'] == 'formal-b3-doubao-tb-cargo-plan-01')
        name = row['controls']['public_task']['sources'][0]['path']
        def change():
            path = self.root / name
            lines = path.read_text(encoding='utf-8').splitlines(keepends=True)
            require_lines = [i for i, s in enumerate(lines) if '边界' in s]
            self.assertTrue(require_lines)
            path.write_text(''.join(s for i, s in enumerate(lines) if i not in require_lines), encoding='utf-8')
        self.semantic_reject(change)

    def test_semantic_A_nonexempt_CRLF_change_rejected(self):
        name = self.baseline['rows'][0]['controls']['public_task']['sources'][0]['path']
        def change():
            path = self.root / name
            lines = path.read_bytes().splitlines(keepends=True)
            self.assertTrue(lines[3].endswith(b'\n') and not lines[3].endswith(b'\r\n'))
            lines[3] = lines[3][:-1] + b'\r\n'
            path.write_bytes(b''.join(lines))
        self.semantic_reject(change)

    def test_source_and_manifest_reseal_rejected(self):
        name = self.baseline['rows'][0]['controls']['declared_effort']['sources'][0]['path']
        self.edit_json(name, lambda d: d.update(reasoning_effort='high'))
        digest = hashlib.sha256((self.root / name).read_bytes()).hexdigest()
        def reseal(d):
            next(x for x in d['source_manifest'] if x['path'] == name)['sha256'] = digest
        self.edit_json(self.f.LEDGER, reseal)
        self.edit_json(v.VIEW, lambda d: d['rows'][0]['controls']['declared_effort'].update(value='high'))
        with self.assertRaisesRegex(ValueError, 'trusted source SHA mismatch'):
            v.verify(self.root)

    def test_semantic_metadata_wrong_identity_rejected(self):
        name = self.baseline['rows'][0]['controls']['declared_effort']['sources'][0]['path']
        self.semantic_reject(lambda: self.edit_json(name, lambda d: d.update(product='dsh')))

    def test_derived_attempt_deleted(self):
        self.reject_view(lambda d: d['rows'].pop())

    def test_derived_formal_promoted(self):
        self.reject_view(lambda d: next(r for r in d['rows'] if not r['formal']).update(formal=True))

    def test_derived_closed_model_laundered(self):
        def change(d):
            r = next(r for r in d['rows'] if r['product'] == 'yuanbao')
            r['controls']['backend_model_identity'].update(state='recorded', value='DeepSeek authenticated')
        self.reject_view(change)

    def test_derived_actual_budget_laundered(self):
        self.reject_view(lambda d: d['rows'][0]['controls']['actual_reasoning_budget'].update(state='recorded', value='low'))

    def test_derived_case_pin_as_prompt(self):
        def change(d):
            c = d['rows'][0]['controls']
            c['public_task']['value'] = c['case_sha256']['value']
            c['public_task']['sources'] = c['case_sha256']['sources']
        self.reject_view(change)

    def test_derived_wrong_pointer(self):
        self.reject_view(lambda d: d['rows'][0]['controls']['declared_effort']['sources'][0].update(pointer='/model'))

    def test_derived_boundary_diff_omitted(self):
        self.reject_view(lambda d: d['replacement_comparisons'][1]['public_task_diff'].update(changed_line_ranges=[]))

    def test_derived_false_equivalence(self):
        self.reject_view(lambda d: d['A_finite_TASK_comparisons'][0]['public_task_diff'].update(semantic_equivalence_proven=True))

    def test_derived_wrong_parent(self):
        self.reject_view(lambda d: d['replacement_comparisons'][0].update(parent=d['replacement_comparisons'][1]['parent']))

    def test_derived_reseal_cannot_approve(self):
        def change(d):
            d['rows'][0]['controls']['declared_effort']['value'] = 'high'
            d['self_sha256'] = hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()
        self.edit_json(v.VIEW, change)
        with self.assertRaises(ValueError):
            v.verify(self.root)

    def test_derived_historical_missing_washed(self):
        self.reject_view(lambda d: d['historical_inventory_unchanged'].update(missing=[], B_observation_version_unknown=0, complete_historical_verification=True))

    def test_compact_table_tampered(self):
        path = self.root / (v.HERE + 'summary.md')
        path.write_text(path.read_text(encoding='utf-8').replace('low / low', 'high / high'), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'compact table'):
            v.verify(self.root)

    def test_duplicate_output_key_rejected(self):
        path = self.root / v.VIEW
        path.write_text('{"rows":[],"rows":[]}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'duplicate JSON'):
            v.verify(self.root)

    def test_nonfinite_output_rejected(self):
        (self.root / v.VIEW).write_text('{"x":1e9999}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'nonfinite JSON'):
            v.verify(self.root)


if __name__ == '__main__':
    unittest.main(verbosity=2)
