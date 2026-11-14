"""Pure tests; Native-shaped data below are manufactured, never actual tasks."""
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
import cleanroom as c
import verify as v

class Static(unittest.TestCase):
    def test_six_distinct_answer_collisions(self):
        self.assertEqual(len(c.proof()['collisions']), 6)
    def test_five_independent_display_commitments(self):
        expected = ['16d2262e007472b2c373da056adba4fa0534ff7931ac8c35690b019f1b49403f',
            '1981a7af9f8d2a4c008c70c255703bedeca753b841dfc9c668fe088fe12d380d',
            '1981a7af9f8d2a4c008c70c255703bedeca753b841dfc9c668fe088fe12d380d',
            '8fc1211eeaf434c9326b031b46b45f613eb7f2bf3b74eff61f63e700f0497a82',
            '3b649d2256e2b46d73a433987f18274282448d502bc2c46dcb268dd499176575']
        self.assertEqual([x['display_utf8_sha256'] for x in c.proof()['collisions'][:5]], expected)
    def test_cr_no_marker_and_z_negative(self):
        a, b = (c.project(s)['rendered'] for s in (c.pairs()[-1][1], c.pairs()[-1][2]))
        self.assertEqual(a, b)
        self.assertNotIn(c.MARKER, b)
        self.assertIn('(End of file', b)
        self.assertIn(c.MARKER, c.project('q' * 2000 + 'ZSECRET\n')['rendered'])
    def test_json_sources_valid_distinct_values(self):
        _, a, b, _, _ = c.pairs()[3]
        self.assertEqual(json.loads(a)['decision'], 'ALLOW')
        self.assertEqual(json.loads(b)['decision'], 'DENY!')
    def test_unicode_not_codepoints(self):
        self.assertEqual(c.u16('\U0001f600'), 2)
        unit = c.prefix('x' * 1999 + '\U0001f600', 2000)[-1]
        self.assertEqual(ord(unit), 0xd83d)
    def test_json_preserves_lone_unit(self):
        unit = '\ud83d'
        encoded = json.dumps(unit)
        self.assertIn('\\ud83d', encoded)
        self.assertEqual(json.loads(encoded), unit)
        self.assertEqual(c.display_bytes(unit), '\ufffd'.encode())
    def test_utf8_byte_cap_different_line_counts(self):
        pages = c.proof()['byte_windows']
        self.assertEqual([p['pages'][0]['lines'] for p in pages], [25, 8, 12])
        self.assertEqual([p['pages'][0]['bytes'] for p in pages], [50024, 48007, 48011])
    def test_all_byte_windows_recover(self):
        self.assertTrue(all(p['all_30_lines_recovered'] for p in c.proof()['byte_windows']))
    def test_single_line_offset_is_not_columns(self):
        for offset in (2, 100, 2001):
            with self.assertRaises(ValueError):
                c.project('q' * 2000 + 'SECRET', offset=offset)
    def test_line_limit_one_not_column_recovery(self):
        source = 'q' * 2000 + 'SECRET'
        self.assertEqual(c.project(source)['rendered'], c.project(source, limit=1)['rendered'])
    def test_positive_integer_not_bool_or_float(self):
        for x in (True, False, 1.0, None, 0, -1):
            with self.assertRaises(ValueError):
                c.project('x', offset=x)
    def test_own_keys_not_truthiness(self):
        for value in (None, False, 0, ''):
            self.assertFalse(c.should_bound('alias', {'value': value}.keys()))
        self.assertTrue(c.should_bound('alias', []))
    def test_inherited_value_not_own(self):
        self.assertTrue(c.should_bound('alias', ['other']))
    def test_opaque_ids_do_not_change_name_condition(self):
        for opaque in ('opaque_A', 'opaque_B'):
            self.assertFalse(c.should_bound('read', []), opaque)
            self.assertTrue(c.should_bound('alias', []), opaque)
    def test_rejection_parent_preconditions(self):
        self.assertFalse(c.should_bound('alias', [], accepted=False))
        self.assertFalse(c.should_bound('alias', [], parent=True))
    def test_footer_and_empty_input(self):
        self.assertEqual(c.project('')['lines'], [])
        self.assertEqual(c.project('a\n')['total_lines'], 1)
        self.assertEqual(c.project('a\n\n')['total_lines'], 2)

    def test_only_b_different_display_rejected_even_optimized(self):
        original = c.project
        def changed(text, *args, **kwargs):
            result = original(text, *args, **kwargs)
            if 'DENY!' in text: result['rendered'] += 'DIFFERENT'
            return result
        with patch.object(c, 'project', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'complete_display_not_equal:json-decision'): c.proof()
    def test_cr_negative_gate_even_optimized(self):
        original = c.project
        def changed(text, *args, **kwargs):
            result = original(text, *args, **kwargs)
            if 'ZSECRET' in text: result['rendered'] = result['rendered'].replace(c.MARKER, '')
            return result
        with patch.object(c, 'project', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'cr_negative_control_failed'): c.proof()
    def test_cr_unmarked_gate_even_optimized(self):
        original = c.project
        def changed(text, *args, **kwargs):
            result = original(text, *args, **kwargs)
            if text in (c.pairs()[-1][1], c.pairs()[-1][2]): result['rendered'] += c.MARKER
            return result
        with patch.object(c, 'project', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'cr_unmarked_claim_invalid'): c.proof()
    def test_page_reconstruction_gate_even_optimized(self):
        original = c.project
        def changed(text, *args, **kwargs):
            result = original(text, *args, **kwargs)
            if len(text) > 50000 and result['lines']:
                number, value = result['lines'][0]
                result['lines'][0] = (number, value + 'WRONG')
            return result
        with patch.object(c, 'project', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'byte_window_reconstruction_failed'): c.proof()
    def test_page_progress_gate_even_optimized(self):
        original = c.project
        def changed(text, *args, **kwargs):
            result = original(text, *args, **kwargs)
            if len(text) > 50000: result['next_offset'] = args[0] if args else 1
            return result
        with patch.object(c, 'project', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'byte_window_not_advancing'): c.proof()
    def test_surrogate_unit_gate_even_optimized(self):
        original = c.project
        def changed(text, *args, **kwargs):
            result = original(text, *args, **kwargs)
            if '\U0001f600' in text:
                number, value = result['lines'][0]
                result['lines'][0] = (number, value[:1999] + '\ufffd' + value[2000:])
            return result
        with patch.object(c, 'project', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'astral_surrogate_unit_changed'): c.proof()

class SafeDerived(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent, prefix='pure-test-')
        self.root = Path(self.temp.name)
        a = 'q' * 8000 + 'TARGET=' + 'a' * 64 + 'q' * (16000 - 8071)
        b = a[:8007] + 'b' * 64 + a[8071:]
        s = '\n'.join(a[i:i+100] for i in range(0, 16000, 100))
        self.texts = dict(S=s, A=a, B=b)
        self.data = dict(schema='safe-native-client-derivative-v2', files={}, sources=[], reads=[],
                         planned_reads=4, session_denominator=1, completed=True,
                         actual_counts=dict(local_requests=6,fixtures=3,reads=4,upstream_forwards=0,model_requests=0),
                         runtime_end_witness=dict(completed=True,exit_code=0,logs_withheld=False,native_identity_verified=True,
                             not_global_runtime_attestation=True,own_process_group_state='absent',signal_zero_observation_only=True,timeout=False),
                         branch='read_presentation_loses_required_long_line_information_on_this_probe')
        for sid, text in self.texts.items():
            self.put('sources/' + sid + '.txt', text)
            digest = c.sha(text.encode())
            self.data['sources'].append(dict(source=sid, source_original_sha256=digest,
                derived_sha256=digest, fixture_payload_sha256=digest, physical_spill_sha256=digest,
                synthetic_locator='/synthetic/native/' + sid + '.txt'))
        for i, sid in enumerate(('S','A','B','A')):
            path = '/synthetic/native/' + sid + '.txt'
            args = dict(file_path=path)
            if i == 3:
                args.update(offset=1, limit=1)
            text = c.project(self.texts[sid], limit=1 if i == 3 else 2000, path=path)['rendered']
            name = 'read-%d.txt' % (i + 1)
            self.put(name, text)
            self.data['reads'].append(dict(source=sid, role='user', call_id='rr1114_c' + str(i+4),
                is_error=False, native_is_error_present=True, native_error_fields={'is_error':False}, args=args, file=name, derived_sha256=c.sha(text.encode())))
        self.add_previews()
        self.add_metrics()
    def put(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        self.data['files'][name] = c.sha(text.encode())
    def save(self):
        (self.root / 'manifest.json').write_text(json.dumps(self.data))
    def tearDown(self):
        if self.root.resolve().parent != Path(__file__).resolve().parent or not self.root.name.startswith('pure-test-'):
            raise ValueError('test cleanup target mismatch')
        self.temp.cleanup()
    def add_metrics(self):
        self.data['metrics_required'] = True
        for source in self.data['sources']:
            source['canonical_locator_sha256'] = c.sha(('canonical-'+source['source']).encode())
        for row in self.data['reads']:
            source = self.texts[row['source']]
            body = (self.root/row['file']).read_text()
            derived = v.read_metrics(body,source)
            original = dict(derived)
            for key in ('formatted_result_utf8_bytes','wrapper_over_displayed_reconstruction_bytes','legacy_wrapper_excluding_join_lf_bytes','path_line_bytes','non_source_increment_bytes'): original[key] += 100
            row.update(original_locator_utf8_bytes=len(row['args']['file_path'].encode())+100,
                canonical_header_original_sha256=c.sha(('canonical-'+row['source']).encode()),
                normalized_body_sha256=c.sha(body.split('\n',1)[1].encode()),metrics=dict(original=original,derived=derived),
                analysis_original_fields=dict(source_bytes=len(source.encode()),source_utf16=c.u16(source),
                    displayed_source_bytes=derived['displayed_reconstruction_bytes'],displayed_source_utf16=derived['displayed_reconstruction_bytes'],
                    raw_result_bytes=original['formatted_result_utf8_bytes'],wrapper_bytes=original['legacy_wrapper_excluding_join_lf_bytes']))
        self.save()
    def test_metric_source_marker_lf_decomposition(self):
        self.add_metrics()
        self.assertEqual(v.native(self.root)['verified_read_derivatives'],4)
        s,a = [row['metrics']['original'] for row in self.data['reads'][:2]]
        self.assertEqual((s['source_covered_bytes'],s['source_lf_separator_bytes']),(16159,159))
        self.assertEqual(s['legacy_wrapper_excluding_join_lf_bytes']-s['wrapper_over_displayed_reconstruction_bytes'],159)
        self.assertEqual((a['source_covered_bytes'],a['synthetic_marker_bytes'],a['displayed_reconstruction_bytes']),(2000,34,2034))
    def test_synthetic_marker_not_source_coverage(self):
        self.add_metrics()
        self.data['reads'][1]['metrics']['original']['source_covered_bytes'] = 2034
        self.save()
        with self.assertRaisesRegex(ValueError,'decomposition'): v.native(self.root)
    def test_s_net_wrapper_not_legacy_wrapper(self):
        self.add_metrics()
        item = self.data['reads'][0]['metrics']['original']
        item['wrapper_over_displayed_reconstruction_bytes'] = item['legacy_wrapper_excluding_join_lf_bytes']
        self.save()
        with self.assertRaisesRegex(ValueError,'decomposition'): v.native(self.root)
    def test_required_metrics_cannot_be_omitted(self):
        self.add_metrics()
        self.data['reads'][1].pop('metrics')
        self.save()
        with self.assertRaisesRegex(ValueError,'decomposition'): v.native(self.root)
    def test_positive_derived_replay(self):
        self.assertEqual(v.native(self.root)['verified_read_derivatives'], 4)
    def test_false_boolean_pagination(self):
        self.data['reads'][-1]['args']['offset'] = True
        self.save()
        with self.assertRaises(ValueError): v.native(self.root)
    def test_same_prefix_wrong_fullfile(self):
        self.data['sources'][2]['source_original_sha256'] = self.data['sources'][1]['source_original_sha256']
        self.save()
        with self.assertRaises(ValueError): v.native(self.root)
    def test_role_id_and_locator(self):
        self.data['reads'][0]['role'] = 'assistant'
        self.save()
        with self.assertRaises(ValueError): v.native(self.root)
    def test_modified_content_not_hidden_by_manifest(self):
        self.put('read-2.txt', (self.root / 'read-2.txt').read_text() + 'junk')
        self.save()
        with self.assertRaises(ValueError): v.native(self.root)
    def test_partial_not_promoted(self):
        self.data['reads'] = self.data['reads'][:1]
        self.data['completed'] = False
        self.save()
        with self.assertRaisesRegex(ValueError,'completed runtime end witness'): v.native(self.root)
    def test_missing_read_not_completed(self):
        self.data['reads'].pop()
        self.save()
        with self.assertRaises(ValueError): v.native(self.root)
    def test_wrong_branch(self):
        self.data['branch'] = 'long_line_loss_not_reproduced'
        self.save()
        with self.assertRaises(ValueError): v.native(self.root)

    def add_previews(self):
        self.data['previews'] = []
        for i, sid in enumerate(('S','A','B')):
            source = (self.root / ('sources/' + sid + '.txt')).read_text()
            text = source[:256] + '\n\n[...]\n\n' + source[-256:] + '\n\n(Omitted %d bytes. Full formatted result stored at: /synthetic/native/%s.txt. Use read with offset/limit, or grep this path to search within it.)' % (len(source.encode()) - 512, sid)
            name = 'preview-%d.txt' % i
            self.put(name, text)
            self.data['previews'].append(dict(source=sid,role='user',call_id='rr1114_c'+str(i+1),args={},file=name,
                derived_sha256=c.sha(text.encode()),is_error=False,native_is_error_present=True,native_error_fields={'is_error':False}))
        self.save()
    def test_v2_schema_metrics_preview_and_typed_counts(self):
        self.add_previews()
        self.add_metrics()
        self.data.update(schema='safe-native-client-derivative-v2',actual_counts=dict(local_requests=6,fixtures=3,reads=4,upstream_forwards=0,model_requests=0))
        self.save()
        self.assertEqual(v.native(self.root)['verified_read_derivatives'],4)
        self.data['actual_counts']['upstream_forwards'] = False
        self.save()
        with self.assertRaisesRegex(ValueError,'v2 metrics / counts'): v.native(self.root)
    def test_three_preview_role_source_structure(self):
        self.add_previews()
        self.assertEqual(v.native(self.root)['verified_preview_derivatives'], 3)
    def test_preview_error_priority(self):
        self.add_previews()
        self.data['previews'][1]['native_error_fields'] = {'is_error':False,'status':'failed'}
        self.save()
        with self.assertRaisesRegex(ValueError, 'native failure state'): v.native(self.root)
    def test_is_error_true_before_valid_body(self):
        self.data['reads'][0]['is_error'] = True
        self.save()
        with self.assertRaisesRegex(ValueError, 'nonerror witness'): v.native(self.root)
    def test_error_metadata_priority(self):
        self.data['reads'][0]['native_error_fields'] = {'is_error': True}
        self.save()
        with self.assertRaisesRegex(ValueError, 'native error flag'): v.native(self.root)
    def test_missing_error_witness_rejected(self):
        self.data['reads'][0].pop('is_error')
        self.save()
        with self.assertRaisesRegex(ValueError, 'nonerror witness'): v.native(self.root)
    def test_error_envelope_despite_rehashed_body(self):
        row = self.data['reads'][0]
        text = '<tool_use_error>' + (self.root / row['file']).read_text() + '</tool_use_error>'
        self.put(row['file'], text)
        row['derived_sha256'] = c.sha(text.encode())
        self.save()
        with self.assertRaisesRegex(ValueError, 'error envelope'): v.native(self.root)
    def test_extra_file_not_in_inventory(self):
        (self.root / 'extra.txt').write_text('extra')
        with self.assertRaisesRegex(ValueError, 'inventory mismatch'): v.native(self.root)
    def test_extra_symlink_not_in_inventory(self):
        (self.root / 'extra-link').symlink_to(self.root / 'read-1.txt')
        with self.assertRaisesRegex(ValueError, 'symlink'): v.native(self.root)
    def test_extra_empty_directory_not_in_inventory(self):
        (self.root / 'extra-dir').mkdir()
        with self.assertRaisesRegex(ValueError, 'inventory mismatch'): v.native(self.root)
    def test_root_inventory_also_includes_native_manifest(self):
        all_files = {path.relative_to(self.root).as_posix(): c.sha(path.read_bytes()) for path in self.root.rglob('*') if path.is_file()}
        # The Native-shaped temporary root already has manifest.json. On a
        # case-insensitive filesystem MANIFEST.json would overwrite that file.
        (self.root / 'PACKAGE.json').write_text(json.dumps({'files': all_files}))
        self.assertEqual(v.tree(self.root, all_files, 'PACKAGE.json'), len(all_files) + 1)
        (self.root / 'extra.txt').write_text('unlisted')
        with self.assertRaisesRegex(ValueError, 'inventory mismatch'): v.tree(self.root, all_files, 'PACKAGE.json')

class PackageSemantic(unittest.TestCase):
    """Actual safe files are copied; no product execution. Rehash before each gate."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=v.ROOT.parent, prefix='package-test-')
        self.root = Path(self.temp.name)
        names = list(v.load(v.ROOT / 'MANIFEST.json')['files']) + ['MANIFEST.json']
        for name in names:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((v.ROOT / name).read_bytes())
    def tearDown(self):
        if self.root.resolve().parent != v.ROOT.parent or not self.root.name.startswith('package-test-'):
            raise ValueError('test cleanup target mismatch')
        self.temp.cleanup()
    def rehash(self):
        files = {p.relative_to(self.root).as_posix():c.sha(p.read_bytes()) for p in self.root.rglob('*') if p.is_file() and p != self.root/'MANIFEST.json'}
        (self.root/'MANIFEST.json').write_text(json.dumps({'files':files}))
        self.assertEqual(v.tree(self.root,files,'MANIFEST.json'),43)
    def reject(self, pattern):
        self.rehash()
        with patch.object(v,'ROOT',self.root):
            with self.assertRaisesRegex(ValueError,pattern): v.main()
    def manifest(self, change):
        path=self.root/'native/manifest.json'
        data=v.load(path)
        change(data)
        path.write_text(json.dumps(data))
    def test_disk_b_identical_task_answer_rehashed(self):
        a=self.root/'static/sources/json-decision-A.txt'
        (self.root/'static/sources/json-decision-B.txt').write_bytes(a.read_bytes())
        self.reject('static sources or task answers not distinct')
    def test_disk_json_display_wrong_rehashed(self):
        path=self.root/'static/displays/json-decision.json'
        data=v.load(path)
        data['same_path_complete_projection']+='WRONG'
        path.write_text(json.dumps(data))
        self.reject('stored JSON projection differs')
    def test_disk_utf8_display_wrong_rehashed(self):
        path=self.root/'static/displays/astral-unit.txt'
        path.write_bytes(path.read_bytes()+b'WRONG')
        self.reject('stored UTF8 display differs')
    def test_disk_spec_bytecap_wrong_rehashed(self):
        path=self.root/'specs.json';data=v.load(path);data['units']['byte_cap']=4096
        path.write_text(json.dumps(data));self.reject('finite spec contract differs')
    def test_disk_spec_task_wrong_rehashed(self):
        path=self.root/'specs.json';data=v.load(path);data['collision_task_predicates']['json-decision']='Always return zero'
        path.write_text(json.dumps(data));self.reject('finite spec contract differs')
    def test_disk_proof_answers_wrong_rehashed(self):
        path=self.root/'proof.json';data=v.load(path);data['collisions'][3]['task_answers']=[0,0]
        path.write_text(json.dumps(data));self.reject('stored collision proof differs')
    def test_schema_v1_disable_v2_contract_rehashed(self):
        def change(data):
            data.update(schema='safe-native-client-derivative-v1',metrics_required=False,previews=[])
            data.pop('actual_counts')
            for row in data['reads']:row.pop('metrics')
        self.manifest(change);self.reject('native schema must be v2')
    def test_runtime_timeout_failed_completion_rehashed(self):
        self.manifest(lambda data:data['runtime_end_witness'].update(timeout=True,exit_code=1,completed=False))
        self.reject('completed runtime end witness')
    def test_runtime_exit_boolean_not_numeric_zero(self):
        self.manifest(lambda data:data['runtime_end_witness'].update(exit_code=False))
        self.reject('completed runtime end witness')
    def test_runtime_own_group_present_rejected(self):
        self.manifest(lambda data:data['runtime_end_witness'].update(own_process_group_state='present'))
        self.reject('completed runtime end witness')
    def test_runtime_global_scope_not_promoted(self):
        self.manifest(lambda data:data['runtime_end_witness'].update(not_global_runtime_attestation=False))
        self.reject('completed runtime end witness')
    def test_missing_native_error_presence_all_seven_rehashed(self):
        def change(data):
            for row in data['previews']+data['reads']:row.pop('native_is_error_present')
        self.manifest(change);self.reject('native error presence witness')
    def test_native_error_presence_not_boolean(self):
        self.manifest(lambda data:data['reads'][0].update(native_is_error_present=1))
        self.reject('native error presence witness')
    def test_native_error_presence_inconsistent(self):
        self.manifest(lambda data:data['reads'][0].update(native_is_error_present=False))
        self.reject('native error presence witness')
    def test_status_timeout_rehashed(self):
        self.manifest(lambda data:data['reads'][0]['native_error_fields'].update(status='timeout'))
        self.reject('native failure state or unsupported status')
    def test_status_unknown_rehashed(self):
        self.manifest(lambda data:data['reads'][0]['native_error_fields'].update(status='unknown'))
        self.reject('native failure state or unsupported status')
    def test_state_null_unknown_rehashed(self):
        self.manifest(lambda data:data['reads'][0]['native_error_fields'].update(state=None))
        self.reject('native failure state or unsupported status')

if __name__ == '__main__':
    unittest.main(verbosity=2)
