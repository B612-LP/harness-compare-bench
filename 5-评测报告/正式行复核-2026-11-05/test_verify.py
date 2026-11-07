"""Synthetic-copy tests; byte-pin rejection and semantic rejection are separate.
Run: python3 -B -m unittest discover -s 5-评测报告/正式行复核-2026-11-05 -p test_verify.py -v
"""
import contextlib
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('formal_closure_verify', HERE / 'verify.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
EP = '3-表现现场/r1030-formal-a1/formal-a1-events.json'
TP = '5-评测报告/可信冻结-2026-10-29-v2/official-main-table.json'
CP = '4-打分细则/可信冻结-2026-10-29-v2/config.json'


class ClosureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='formal-25-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        ledger = v.loads((ROOT / v.LEDGER).read_text(encoding='utf-8'))
        self.names = [v.LEDGER, v.REPORT, v.REPORT_CURRENT] + [x['path'] for x in ledger['source_manifest'] if x['status'] == 'present']
        for name in self.names:
            dest = self.root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((ROOT / name).read_bytes())

    def modify(self, name, fn):
        path = self.root / name
        doc = v.loads(path.read_text(encoding='utf-8'))
        fn(doc)
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    @contextlib.contextmanager
    def semantic_only(self):
        # TEST ONLY: remove byte comparisons so the test cannot mistake a fixed SHA
        # rejection for independent value/ID/contract/report validation. No CLI bypass.
        def existence(store, name):
            v.require(name in store.expected, 'unregistered source')
            path = store.path(name)
            if name in store.missing:
                v.require(not path.exists(), 'unexpected historical source')
            else:
                v.require(path.is_file(), 'missing required source')
        with patch.object(v.Store, 'check_hash', existence):
            yield

    def rejects(self, pattern, semantic=False):
        cm = self.semantic_only() if semantic else contextlib.nullcontext()
        with cm, self.assertRaisesRegex((ValueError, KeyError), pattern):
            v.derive(self.root)

    def test_baseline_readonly_no_network_or_execution(self):
        before = {p.relative_to(self.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob('*') if p.is_file()}
        with patch('socket.socket', side_effect=AssertionError('network forbidden')), patch('subprocess.run', side_effect=AssertionError('process forbidden')):
            result = v.derive(self.root)
        after = {p.relative_to(self.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(result['track_counts'], {'A_same_model': 10, 'B_native': 10, 'W_gateway': 5})
        self.assertEqual(len(result['rows']), 25)
        self.assertTrue(all(row['registration_source']['pointer'].startswith('/registrations/') for row in result['rows']))
        self.assertEqual(result['attempts'], 30)
        self.assertEqual(len(result['replacements']), 5)
        self.assertEqual(result['summary']['codex'], {'formal_n': 5, 'headline': 3, 'weighted_sum': 444.81})
        self.assertEqual(result['summary']['dsh']['weighted_sum'], 444.07)
        self.assertEqual(result['summary']['yuanbao']['headline'], 2)
        self.assertEqual(result['summary']['doubao']['headline'], 3)
        self.assertEqual(result['summary']['workbuddy']['headline'], 3)
        self.assertEqual(result['historical_inventory']['B_observation_version_unknown'], 40)
        self.assertEqual(len(result['historical_inventory']['missing']), 5)
        self.assertFalse(result['historical_inventory']['complete_historical_verification'])
        self.assertEqual(result['report_editions'], {'reviewed_byte_pinned': v.REPORT, 'current_numeric_closure': v.REPORT_CURRENT})
        self.assertTrue(all(row['report']['path'] == v.REPORT and row['report_current']['path'] == v.REPORT_CURRENT for row in result['rows']))
        self.assertTrue(all(row['report']['cell'] == row['report_current']['cell'] for row in result['rows']))

    def test_missing_current_report_fails(self):
        # Fixture deletion only; never an original file.
        target = self.root / v.REPORT_CURRENT
        self.assertTrue(target.is_relative_to(self.root))
        target.unlink()
        with self.assertRaises(OSError):
            v.derive(self.root)

    def test_semantic_current_report_score_drift(self):
        # Current edition is not byte-pinned: numeric closure must catch the drift.
        path = self.root / v.REPORT_CURRENT
        text = path.read_text(encoding='utf-8')
        self.assertIn('93.33（14/15）', text)
        path.write_text(text.replace('93.33（14/15）', '100.00（15/15）', 1), encoding='utf-8')
        self.rejects('report weighted mismatch')

    def test_semantic_current_report_cell_format_drift(self):
        # Value-preserving cell edit: numeric checks pass, edition equality fails.
        path = self.root / v.REPORT_CURRENT
        text = path.read_text(encoding='utf-8')
        self.assertIn('93.33（14/15）', text)
        path.write_text(text.replace('93.33（14/15）', '93.33（14/15）注', 1), encoding='utf-8')
        self.rejects('report edition cell mismatch')

    def test_semantic_current_report_summary_drift(self):
        path = self.root / v.REPORT_CURRENT
        text = path.read_text(encoding='utf-8')
        self.assertIn('| **达标题数** | **2/5** | **3/5** |', text)
        path.write_text(text.replace('| **达标题数** | **2/5** | **3/5** |', '| **达标题数** | **3/5** | **3/5** |'), encoding='utf-8')
        self.rejects('report summary mismatch')

    def test_semantic_baseline_without_byte_comparisons(self):
        with self.semantic_only():
            self.assertTrue(v.derive(self.root)['ok'])

    def test_fixed_pin_source_score_change(self):
        self.modify(EP, lambda d: d['events'][0]['score']['value'].update(earned=15, reported=100.0))
        self.rejects('trusted source SHA mismatch')

    def test_fixed_pin_ledger_resealed_source(self):
        self.modify(EP, lambda d: d['events'][0]['score']['value'].update(earned=15, reported=100.0))
        digest = hashlib.sha256((self.root / EP).read_bytes()).hexdigest()
        self.modify(v.LEDGER, lambda d: next(x for x in d['source_manifest'] if x['path'] == EP).update(sha256=digest))
        self.rejects('trusted source SHA mismatch')

    def test_fixed_pin_derived_reseal_all_internal_hashes(self):
        self.modify(v.LEDGER, lambda d: d['formal'][0]['score'].update(earned=15, reported=100.0))
        self.rejects('trusted source SHA mismatch')

    def test_fixed_pin_report_change(self):
        path = self.root / v.REPORT
        path.write_text(path.read_text(encoding='utf-8').replace('93.33（14/15）', '100.00（15/15）', 1), encoding='utf-8')
        self.rejects('trusted source SHA mismatch')

    def test_missing_required_source(self):
        # Fixture deletion only; never an original file.
        target = self.root / EP
        self.assertTrue(target.is_relative_to(self.root))
        target.unlink()
        self.rejects('missing required source')

    def test_missing_grade_receipt(self):
        events = v.loads((self.root / EP).read_text(encoding='utf-8'))
        source_index = events['events'][0]['score']['refs'][0]['source']
        name = events['events'][0]['sources'][source_index]['path']
        target = self.root / name
        self.assertTrue(target.is_relative_to(self.root))
        target.unlink()
        self.rejects('missing required source')

    def test_historical_missing_not_silently_backfilled(self):
        ledger = v.loads((self.root / v.LEDGER).read_text(encoding='utf-8'))
        name = next(x['path'] for x in ledger['source_manifest'] if x['status'] == 'missing')
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('{}', encoding='utf-8')
        self.rejects('historically missing source unexpectedly supplied')

    def test_semantic_unknown_official_id(self):
        self.modify(TP, lambda d: d['groups']['A_same_model'].append('synthetic-ghost'))
        self.rejects('unresolved official ID', True)

    def test_semantic_duplicate_official_id(self):
        self.modify(TP, lambda d: d['groups']['A_same_model'].append(d['groups']['A_same_model'][0]))
        self.rejects('duplicate official ID', True)

    def test_semantic_missing_official_id(self):
        self.modify(TP, lambda d: d['groups']['A_same_model'].pop())
        self.rejects('unclassified or conflicting event', True)

    def test_semantic_cross_track(self):
        self.modify(EP, lambda d: d['events'][0].update(group='B_native'))
        self.rejects('event track/category mismatch', True)

    def test_semantic_run_id_swap(self):
        self.modify(EP, lambda d: d['events'][0]['identity']['value'].update(run_id='synthetic-other-run'))
        self.rejects('source pointer value mismatch', True)

    def test_semantic_arithmetic_consistent_score_conflicts_with_receipt(self):
        self.modify(EP, lambda d: d['events'][0]['score']['value'].update(earned=15, reported=100.0))
        self.rejects('source pointer value mismatch', True)

    def test_semantic_contract_change(self):
        self.modify(CP, lambda d: d.update(rule_version='synthetic-wrong-rule'))
        self.rejects('source pointer value mismatch|contract binding mismatch', True)

    def test_semantic_event_checker_change(self):
        self.modify(EP, lambda d: d['events'][0]['facts']['checker_sha256'].update(value='0' * 64))
        self.rejects('source pointer value mismatch', True)

    def test_semantic_empty_score_ref(self):
        self.modify(EP, lambda d: d['events'][0]['score'].update(refs=[]))
        self.rejects('known field requires value and refs|score lacks available JSON receipt', True)

    def test_semantic_bad_json_pointer(self):
        self.modify(EP, lambda d: d['events'][0]['score']['refs'][0].update(pointer='/absent'))
        self.rejects('absent', True)

    def test_semantic_ledger_score_drift(self):
        self.modify(v.LEDGER, lambda d: d['all_formal_attempts'][0]['score'].update(earned=15, reported=100.0))
        self.rejects('historical ledger/event mismatch: score', True)

    def test_semantic_lineage_wrong_slot(self):
        def change(d):
            next(e for e in d['lineage']['edges'] if e['type'] == 'attempt_of')['to'] = 'slot:B_native:codex:bird-ca-schools-15'
        self.modify(v.LEDGER, change)
        self.rejects('lineage slot mismatch', True)

    def test_semantic_lineage_admission_wrong_target(self):
        def change(d):
            next(e for e in d['lineage']['edges'] if e['type'] == 'admitted_by')['to'] = 'admission:synthetic-other-table'
        self.modify(v.LEDGER, change)
        self.rejects('lineage admission target mismatch', True)

    def test_semantic_lineage_admission_wrong_source(self):
        for key, value in (('path', CP), ('sha256', '0' * 64), ('pointer', '/groups/B_native')):
            with self.subTest(key=key):
                original = (self.root / v.LEDGER).read_bytes()
                def change(d):
                    next(e for e in d['lineage']['edges'] if e['type'] == 'admitted_by')['source'][key] = value
                self.modify(v.LEDGER, change)
                self.rejects('lineage admission source mismatch', True)
                (self.root / v.LEDGER).write_bytes(original)

    def test_semantic_lineage_remove_replacement(self):
        def change(d):
            edge = next(e for e in d['lineage']['edges'] if e['type'] == 'unique_replacement_for')
            d['lineage']['edges'].remove(edge)
        self.modify(v.LEDGER, change)
        self.rejects('lineage replacement mismatch', True)

    def test_semantic_report_score_drift(self):
        path = self.root / v.REPORT
        path.write_text(path.read_text(encoding='utf-8').replace('93.33（14/15）', '100.00（15/15）', 1), encoding='utf-8')
        self.rejects('report weighted mismatch', True)

    def test_semantic_report_headline_drift(self):
        path = self.root / v.REPORT
        text = path.read_text(encoding='utf-8')
        text = text.replace('| **达标题数** | **2/5** | **3/5** |', '| **达标题数** | **3/5** | **3/5** |')
        path.write_text(text, encoding='utf-8')
        self.rejects('report summary mismatch', True)

    def test_semantic_same_score_receipt_other_run(self):
        def change(d):
            codex = next(e for e in d['events'] if e['product'] == 'codex' and e['case_id'] == 'exercism-py-6')
            dsh = next(e for e in d['events'] if e['product'] == 'dsh' and e['case_id'] == 'exercism-py-6')
            self.assertEqual(codex['score']['value'], dsh['score']['value'])
            codex['sources'][codex['score']['refs'][0]['source']] = dict(dsh['sources'][dsh['score']['refs'][0]['source']])
        self.modify(EP, change)
        self.rejects('score receipt ownership mismatch', True)

    def test_semantic_missing_model_version_permissions_facts(self):
        def change(d):
            for key in ('model', 'product_version', 'permissions', 'tools', 'skills', 'route', 'started_at', 'finished_at', 'evidence_grade'):
                del d['events'][0]['facts'][key]
        self.modify(EP, change)
        self.rejects('mandatory event facts missing', True)

    def test_semantic_known_fact_without_value_or_refs(self):
        self.modify(EP, lambda d: d['events'][0]['facts'].update(model={'state': 'known'}))
        self.rejects('incomplete field schema', True)

    def test_semantic_gate_false_and_invalid_pointer(self):
        self.modify(EP, lambda d: d['events'][0]['gates']['contamination_free'].update(value=False, refs=[{'source': 5, 'pointer': '/nonexistent-gate'}]))
        self.rejects('nonexistent-gate', True)

    def test_semantic_matching_false_gate_still_cannot_admit(self):
        doc = v.loads((self.root / EP).read_text(encoding='utf-8'))
        ref = doc['events'][0]['gates']['contamination_free']['refs'][0]
        name = doc['events'][0]['sources'][ref['source']]['path']
        self.modify(name, lambda d: d['gates'].update(contamination_free=False))
        self.modify(EP, lambda d: d['events'][0]['gates']['contamination_free'].update(value=False))
        self.rejects('formal admission gate not true', True)

    def test_semantic_duplicate_replacement_edge(self):
        def change(d):
            edge = next(e for e in d['lineage']['edges'] if e['type'] == 'unique_replacement_for')
            d['lineage']['edges'].append(dict(edge))
        self.modify(v.LEDGER, change)
        self.rejects('duplicate replacement edge', True)

    def test_required_first_run_registration_cannot_disappear(self):
        path = self.root / EP
        original = path.read_bytes()
        for variant in ('selection_null', 'selection_absent', 'plan_source_null'):
            with self.subTest(variant=variant):
                path.write_bytes(original)
                def change(d):
                    event = d['events'][0]
                    self.assertEqual(event['event_id'], 'formal-a1-codex-bird-ca-schools-15-01')
                    if variant == 'selection_null':
                        event['selection'] = None
                    elif variant == 'selection_absent':
                        del event['selection']
                    else:
                        event['selection']['plan_source'] = None
                self.modify(EP, change)
                self.rejects('trusted source SHA mismatch')
                self.rejects('required registration (selection missing|plan_source invalid)', True)
        path.write_bytes(original)

    def test_semantic_registration_pointer_wrong_slot(self):
        self.modify(EP, lambda d: d['events'][0]['selection'].update(slot_id='a1-dsh-exercism-py-6', plan_pointer='/registrations/9'))
        self.rejects('registration event identity mismatch', True)

    def test_semantic_report_duplicate_conflicting_row(self):
        path = self.root / v.REPORT
        text = path.read_text(encoding='utf-8')
        row = '| bird-ca-schools-15 | 93.33（14/15） | 100.00（15/15） | 均达标 |'
        self.assertIn(row, text)
        text = text.replace(row, '| bird-ca-schools-15 | 0.00（0/15） | 0.00（0/15） | not achieved |\n' + row, 1)
        path.write_text(text, encoding='utf-8')
        self.rejects('duplicate report case row', True)

    def test_semantic_ledger_formal_copy_score_drift(self):
        self.modify(v.LEDGER, lambda d: d['formal'][0]['score'].update(earned=15, reported=100.0))
        self.rejects('ledger formal/attempt copy mismatch', True)

    def test_semantic_invalid_fact_state(self):
        self.modify(EP, lambda d: d['events'][0]['facts']['model'].update(state='inferred'))
        self.rejects('invalid field state/refs', True)

    def test_semantic_unknown_fact_cannot_hold_known_value(self):
        self.modify(EP, lambda d: d['events'][0]['facts']['model'].update(state='unknown'))
        self.rejects('unknown field must explicitly preserve null value', True)

    def test_duplicate_json_key(self):
        with self.assertRaisesRegex(ValueError, 'duplicate JSON key'):
            v.loads('{"reward":0,"reward":1}')

    def test_nonfinite_numbers(self):
        for text in ('NaN', 'Infinity', '-Infinity', '1e999'):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, 'nonfinite JSON'):
                v.loads('{"number":' + text + '}')

    def test_boolean_score_and_reward(self):
        score = {'earned': 1, 'possible': 1, 'assessed': 1, 'reported': 100, 'reward': 1}
        for key in score:
            bad = dict(score, **{key: True})
            with self.subTest(key=key), self.assertRaises(ValueError):
                v.validate_score(bad)

    def test_path_traversal(self):
        for name in ('../outside.json', '/tmp/outside.json', 'a\\b.json', '~file', 'C:/file'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                v.Store(self.root).path(name)

    def test_symlink_escape(self):
        link = self.root / 'escape'
        link.symlink_to(self.root.parent, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'escapes repository'):
            v.Store(self.root).path('escape/external.json')


if __name__ == '__main__':
    unittest.main()
