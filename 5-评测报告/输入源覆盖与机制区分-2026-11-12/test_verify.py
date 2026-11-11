#!/usr/bin/env python3
"""Offline tests. Only new verifier is imported; no subprocess or network."""
import contextlib
import copy
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location('source_coverage_verifier', HERE/'verify.py')
v = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v)


class CoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = v.analyze(ROOT)
        cls.fixture = (ROOT/(v.SAME+'/confirm-b01-inline/capture/tool-output.txt')).read_bytes()

    def requests(self):
        before = {'messages':[{'role':'user','content':'AA'},
                              {'role':'user','content':'BB'}], 'tools':[], 'model':'fixed'}
        after = copy.deepcopy(before)
        after['messages'].append({'role':'assistant','content':'CC'})
        return before,after

    def reject(self, fn, *args):
        with self.assertRaises(v.Invalid):
            fn(*args)

    def test_real_rows_separate_denominators(self):
        groups = self.result['groups']
        self.assertEqual(groups['same_dsh_six_pairs']['pairs'],6)
        self.assertEqual(groups['native_three_blocks']['blocks'],3)
        self.assertEqual(len(groups['same_dsh_six_pairs']['rows']),12)
        self.assertEqual(len(groups['native_three_blocks']['rows']),6)
        self.assertNotIn('n',self.result)
        self.assertEqual(self.result['new_product_or_model_requests'],0)

    def test_real_source_partitions_and_noise_denominators(self):
        expected = {'inline':(35767,0,35767,420), 'bounded':(1728,253,1981,18),
                    'dsh':(1728,253,1981,18), 'codex':(11964,57,12021,139)}
        for group in self.result['groups'].values():
            for row in group['rows']:
                with self.subTest(arm=row['arm'],block=row['block']):
                    cov = row['coverage']
                    got = (cov['certain_unique_source_bytes'],cov['presentation_bytes'],
                           cov['decoded_text_bytes'],cov['noise_lines']['complete_noise_lines_copied'])
                    self.assertEqual(got,expected[row['arm']])
                    self.assertEqual(cov['source_utf8_bytes_denominator'],35767)
                    self.assertEqual(cov['noise_lines']['denominator_complete_noise_lines'],420)
                    if row['arm'] == 'codex':
                        self.assertEqual(cov['noise_lines']['complete_noise_lines_including_source_lf'],138)
                        self.assertEqual(cov['noise_lines']['content_complete_but_source_lf_missing'],[69])
                    self.assertTrue(cov['all_source_segments_unique'])
                    self.assertEqual(cov['certain_source_intervals'],cov['possible_source_intervals'])
                    self.assertTrue(row['controls']['history_prefix_exact'])
                    self.assertTrue(row['controls']['nonhistory_full_object_exact'])

    def test_literal_fact_absence_scans_whole_request_not_just_tool_leaf(self):
        for group in self.result['groups'].values():
            for row in group['rows']:
                probes = row['literal_fact_probes']
                target = probes['noise_0200_checksum']
                self.assertEqual(target['before_string_leaf_pointers'],[])
                self.assertEqual(bool(target['after_string_leaf_pointers']),row['arm']=='inline')
                self.assertTrue(probes['HEAD_KEY']['after_string_leaf_pointers'])
                self.assertTrue(probes['TAIL_KEY']['after_string_leaf_pointers'])
        # Presence witness must find a literal outside the expected tool leaf.
        self.assertEqual(v.literal_fact_occurrences({'metadata':{'x':'checksum'}},b'checksum'),
                         ['/metadata/x'])

    def test_baseline_pins_and_result_identity(self):
        self.assertEqual(len(v.PINS),75)
        self.assertEqual(self.result['baseline_commit'],'38b2e13f63c5aeacb58094d2e977980ab12e8041')
        self.assertFalse(self.result['unknown']['original_seal_reauthenticated'])
        self.assertEqual(self.result['native_text_difference']['source_copy_byte_difference'],10236)
        self.assertEqual(10236-196,10040)

    def test_utf8_byte_not_character_offsets(self):
        src = '汉Z'.encode()
        good = v.reconstruct(src,['汉Z'],[[{'source':[0,4]}]])
        self.assertEqual(good['decoded_text_bytes'],4)
        self.reject(v.reconstruct,src,['汉Z'],[[{'source':[0,2]}]])

    def test_repeated_substring_not_unique_coverage(self):
        result = v.reconstruct(b'ABxxAB',['AB'],[[{'source':[0,2]}]])
        self.assertFalse(result['all_source_segments_unique'])
        self.assertEqual(result['segments'][0]['source_candidates'],[[0,2],[4,6]])
        self.assertEqual(result['certain_unique_source_bytes'],0)
        self.assertEqual(result['possible_unique_source_bytes'],4)
        self.assertEqual(result['source_copy_bytes_with_multiplicity'],2)

    def test_overlapping_repeat_candidates_reported(self):
        result = v.reconstruct(b'aaaaa',['aaaa'],[[{'source':[0,4]}]])
        self.assertEqual(result['segments'][0]['source_candidates'],[[0,4],[1,5]])
        self.assertEqual(result['certain_source_intervals'],[[1,4]])
        self.assertEqual(result['possible_source_intervals'],[[0,5]])

    def test_duplicate_copies_not_double_counted_as_source_coverage(self):
        result = v.reconstruct(b'abc',['abcabc'],[[{'source':[0,3]},{'source':[0,3]}]])
        self.assertEqual(result['source_copy_bytes_with_multiplicity'],6)
        self.assertEqual(result['certain_unique_source_bytes'],3)

    def test_partial_noise_line_and_missing_lf_separate(self):
        src = b'noise-0000 checksum='+b'a'*64+b'\n'
        partial = v.line_coverage(src,[[0,len(src)-2]])
        self.assertEqual(partial['complete_noise_lines_copied'],0)
        self.assertEqual(partial['partial_noise_indices'],[0])
        no_lf = v.line_coverage(src,[[0,len(src)-1]])
        self.assertEqual(no_lf['complete_noise_lines_copied'],1)
        self.assertEqual(no_lf['complete_noise_lines_including_source_lf'],0)
        self.assertEqual(no_lf['content_complete_but_source_lf_missing'],[0])
        full = v.line_coverage(src,[[0,len(src)]])
        self.assertEqual(full['complete_noise_lines_including_source_lf'],1)

    def test_fragmented_noise_with_gap_not_complete(self):
        src = b'noise-0000 checksum='+b'a'*64+b'\n'
        result = v.line_coverage(src,[[0,40],[41,len(src)]])
        self.assertEqual(result['complete_noise_lines_copied'],0)
        self.assertEqual(result['partial_noise_indices'],[0])

    def test_reconstruction_rejects_contains_only_and_reordering(self):
        src = b'HEADmiddleTAIL'
        parts = [[{'source':[0,4]},{'literal':b'...'},{'source':[10,14]}]]
        good = v.reconstruct(src,['HEAD...TAIL'],parts)
        self.assertTrue(good['exact_reconstruction'])
        for wrong in ['xHEAD...TAIL','HEAD...TAILx','TAIL...HEAD','HEADxxxTAIL']:
            self.reject(v.reconstruct,src,[wrong],parts)

    def test_source_bounds_reject_negative_character_style_and_overflow(self):
        for span in [[-1,2],[0,4],[1,1],[False,2]]:
            self.reject(v.reconstruct,b'abc',['abc'],[[{'source':span}]])

    def test_only_reference_not_readback(self):
        result = v.recovery_status(True,False)
        self.assertTrue(result['reference_text_present'])
        self.assertFalse(result['recovery_tested'])
        self.assertIsNone(result['actual_readback_evidence'])
        self.assertIsNone(result['full_source_recoverability'])

    def test_middle_mutation_equivalent_both_previews_not_inline(self):
        diag = self.result['synthetic_diagnostics']
        self.assertEqual(diag['mutated_byte_offset'],17053)
        self.assertEqual(diag['target_checksum_interval'],[17053,17117])
        self.assertEqual(diag['target_source_line'],202)
        self.assertNotEqual(diag['source_sha256_before'],diag['source_sha256_middle_mutation'])
        self.assertEqual([x['same_preview_after_middle_mutation'] for x in diag['shape_controls']],
                         [True,True,False])

    def test_visible_key_mutation_changes_all_shapes(self):
        for row in self.result['synthetic_diagnostics']['shape_controls']:
            self.assertTrue(row['visible_key_mutation_changes_preview'])

    def test_same_length_history_swap_rejected(self):
        before,after = self.requests()
        altered = copy.deepcopy(after)
        altered['messages'][:2] = list(reversed(altered['messages'][:2]))
        self.assertEqual(len(v.canonical(altered)),len(v.canonical(after)))
        self.reject(v.controls,before,altered,'messages')

    def test_history_deletion_rejected(self):
        before,after = self.requests()
        del after['messages'][0]
        self.reject(v.controls,before,after,'messages')

    def test_same_length_history_replacement_rejected(self):
        before,after = self.requests()
        after['messages'][0]['content'] = 'ZZ'
        self.reject(v.controls,before,after,'messages')

    def test_nonhistory_unselected_field_change_rejected(self):
        before,after = self.requests()
        after['model'] = 'other'
        self.reject(v.controls,before,after,'messages')

    def test_absence_not_null_and_boolean_not_number(self):
        before,after = self.requests()
        after['new_field'] = None
        self.reject(v.controls,before,after,'messages')
        after = copy.deepcopy(before)
        after['messages'].append({'role':'assistant','content':'CC'})
        before['control'],after['control'] = True,1
        self.reject(v.controls,before,after,'messages')

    def test_canonical_dictionary_key_order_is_not_history_change(self):
        before,after = self.requests()
        after['messages'][0] = dict(reversed(list(after['messages'][0].items())))
        self.assertTrue(v.controls(before,after,'messages')['history_prefix_exact'])

    def test_pure_leaf_split_preserves_text_not_serialized_bytes(self):
        result = self.result['synthetic_diagnostics']['pure_leaf_split']
        self.assertTrue(result['ordered_text_equal'])
        self.assertGreater(result['canonical_bytes_after'],result['canonical_bytes_before'])

    def test_duplicate_json_and_nonfinite_rejected(self):
        for text in ['{"x":1,"x":2}','{"x":NaN}','{"x":Infinity}']:
            self.reject(v.parse_json,text)

    def test_pins_reject_each_source_independently_and_missing(self):
        # These mutate only a temporary copy; public originals remain read-only.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in v.PINS:
                path = root/name
                path.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(ROOT/name,path)
            for name in v.PINS:
                with self.subTest(source=name):
                    path = root/name
                    original = path.read_bytes()
                    path.write_bytes(original+b' ')
                    self.reject(v.read_pinned,root)
                    path.write_bytes(original)
            name = next(iter(v.PINS))
            (root/name).unlink()
            self.reject(v.read_pinned,root)

    def test_source_path_escape_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ['/absolute','../escape']:
                self.reject(v.safe_path,root,name)
            (root/'link').symlink_to(ROOT)
            self.reject(v.safe_path,root,'link/AGENTS.md')

    def test_wrong_return_pointer_and_call_link_rejected(self):
        prefix = v.SAME+'/confirm-b01-bounded/capture/'
        before = v.parse_json((ROOT/(prefix+'01-request.json')).read_bytes())
        after = v.parse_json((ROOT/(prefix+'02-request.json')).read_bytes())
        self.assertEqual(v.text_leaves(before,after,'bounded'),
                         ['/messages/2/content/0/content/0/text'])
        after['messages'][-1]['content'][0]['tool_use_id'] = 'wrong'
        self.reject(v.text_leaves,before,after,'bounded')

    def test_read_only_analysis_no_network_subprocess_or_disk_write(self):
        before_hashes = {p:v.sha((ROOT/p).read_bytes()) for p in v.PINS}
        real_open = Path.open
        def read_only_open(path, mode='r', *args, **kwargs):
            if any(flag in mode for flag in 'wax+'):
                raise RuntimeError('write forbidden during analyze')
            return real_open(path,mode,*args,**kwargs)
        import socket
        import subprocess
        with mock.patch.object(Path,'open',read_only_open), \
             mock.patch.object(socket,'socket',side_effect=RuntimeError('network forbidden')), \
             mock.patch.object(subprocess,'Popen',side_effect=RuntimeError('subprocess forbidden')):
            self.assertEqual(v.analyze(ROOT),self.result)
        self.assertEqual(before_hashes,{p:v.sha((ROOT/p).read_bytes()) for p in v.PINS})

    def test_cli_stdout_and_exclusive_new_output(self):
        stdout,stderr = io.StringIO(),io.StringIO()
        with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
            self.assertEqual(v.main(['--root',str(ROOT)]),0)
        self.assertEqual(json.loads(stdout.getvalue()),self.result)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'new.json'
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(v.main(['--root',str(ROOT),'--output',str(path)]),0)
                old = path.read_bytes()
                self.assertEqual(v.main(['--root',str(ROOT),'--output',str(path)]),1)
            self.assertEqual(path.read_bytes(),old)
            self.assertEqual(json.loads(old),self.result)

    def test_generated_public_result_exact(self):
        path = HERE/'result.json'
        self.assertTrue(path.is_file())
        self.assertEqual(v.parse_json(path.read_bytes()),self.result)


if __name__ == '__main__':
    unittest.main(verbosity=2)
