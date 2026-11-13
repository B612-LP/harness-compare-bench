import copy
import json
from pathlib import Path
import unittest

import verify

ROOT = Path(__file__).resolve().parent


class DerivedEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'derived-evidence.json').read_text())
        cls.payload = (ROOT / 'synthetic-payload.txt').read_text()

    def changed(self):
        return copy.deepcopy(self.data)

    def reject(self, data):
        with self.assertRaises(verify.InvalidEvidence):
            verify.verify(data, self.payload)

    def test_complete_derived_relationships(self):
        self.assertEqual(verify.verify(self.data, self.payload)['status'], 'DERIVED_RELATIONSHIPS_PASS')

    def test_full_source_is_exact(self):
        self.assertEqual(verify.source_intervals(self.payload, self.payload)['retained_source_bytes'], 40000)

    def test_marker_only_is_not_retained_text(self):
        with self.assertRaises(verify.InvalidEvidence):
            verify.source_intervals('Omitted 7552 bytes', self.payload)

    def test_forged_short_windows_fail_accounting(self):
        face = self.payload[:128] + '\nOmitted 7552 bytes\n' + self.payload[-128:]
        with self.assertRaises(verify.InvalidEvidence):
            verify.source_intervals(face, self.payload)

    def test_wrong_omission_count_rejected(self):
        face = self.data['dsh']['observations'][2]['tool_content'].replace('Omitted 7556 bytes', 'Omitted 7552 bytes')
        with self.assertRaises(verify.InvalidEvidence):
            verify.source_intervals(face, self.payload)

    def test_duplicate_cell_cannot_replace_missing_cell(self):
        data = self.changed()
        data['dsh']['observations'][3] = copy.deepcopy(data['dsh']['observations'][2])
        self.reject(data)

    def test_wrong_call_binding_rejected(self):
        data = self.changed()
        data['dsh']['observations'][0]['call_id'] = 'foreign-call'
        self.reject(data)

    def test_error_cannot_be_ordinary_face(self):
        data = self.changed()
        data['dsh']['observations'][0]['tool_result_is_error'] = True
        self.reject(data)

    def test_changed_text_rejected(self):
        data = self.changed()
        data['dsh']['observations'][0]['tool_content'] += 'x'
        self.reject(data)

    def test_json_hash_not_wire_hash(self):
        data = self.changed()
        first = data['dsh']['first_request_hashes'][0]
        first['wire_request_body_sha256'] = first['request_json_file_sha256']
        self.reject(data)

    def test_changed_history_rejected(self):
        data = self.changed()
        data['dsh']['warmups'][0]['history_repeat']['original_tool_content_sha256'] = '0' * 64
        self.reject(data)

    def test_unmarked_transform_rejected(self):
        data = self.changed()
        data['dsh']['observations'][2]['transformation'] = 'original_complete_trace'
        self.reject(data)

    def test_private_path_rejected(self):
        data = self.changed()
        record = data['dsh']['observations'][2]
        record['tool_content'] = record['tool_content'].replace('<path:', '/Users/', 1)
        record['derived_tool_content_sha256'] = verify.sha(record['tool_content'])
        record['original_tool_content_utf8_bytes'] = len(record['tool_content'].encode())
        self.reject(data)

    def test_cannot_promote_mock_to_model_trial(self):
        data = self.changed()
        data['dsh']['real_model_trials'] = 4
        self.reject(data)

    def test_cannot_hide_identity_call_id_confound(self):
        data = self.changed()
        data['dsh']['call_id_name_confound_disclosed'] = False
        self.reject(data)

    def test_tail_only_or_missing_close_rejected(self):
        content = self.data['doubao_retention']['records'][0]['tool_content']
        for changed in (content.replace('Head (first 2K characters):', 'Unknown:'),
                        content.replace('Tail (last 2K characters):', 'Unknown:'),
                        content.replace('</tool-output-truncated>', '')):
            with self.subTest(changed=changed[:60]), self.assertRaises(verify.InvalidEvidence):
                verify.retention_windows(changed)

    def test_duplicate_wrapper_rejected(self):
        content = self.data['doubao_retention']['records'][0]['tool_content']
        with self.assertRaises(verify.InvalidEvidence):
            verify.retention_windows('<tool-output-truncated>' + content)

    def test_three_texts_do_not_mean_three_independent_repeats(self):
        data = self.changed()
        data['doubao_retention']['independent_replications'] = True
        self.reject(data)

    def test_all_tool_join_not_compensation_join(self):
        data = self.changed()
        data['doubao_retention']['all_tool_join_accounting']['compensation_join_total'] = 6438
        self.reject(data)

    def test_missing_retention_record_rejected(self):
        data = self.changed()
        data['doubao_retention']['records'].pop()
        self.reject(data)

    def test_target_observation_id_is_bound_to_cell(self):
        data = self.changed()
        data['dsh']['observations'][0]['observation_id'] = 'foreign-target'
        self.reject(data)

    def test_first_request_ids_cover_exact_target_parents(self):
        data = self.changed()
        data['dsh']['first_request_hashes'][0]['observation_id'] = 'foreign-first'
        self.reject(data)

    def test_warmup_call_cannot_be_foreign(self):
        data = self.changed()
        data['dsh']['warmups'][0]['call_id'] = 'foreign-call'
        self.reject(data)

    def test_nested_history_id_cannot_be_foreign(self):
        data = self.changed()
        data['dsh']['warmups'][0]['history_repeat']['observation_id'] = 'foreign-history'
        self.reject(data)

    def test_duplicate_warmup_cannot_impersonate_other_parent(self):
        data = self.changed()
        other = copy.deepcopy(data['dsh']['warmups'][0])
        other['observation_id'] = 'observation_output-after_spill-warmup-r2'
        other['history_repeat']['observation_id'] = 'observation_output-after_spill-warmup-r3'
        data['dsh']['warmups'][1] = other
        self.reject(data)

    def test_missing_exact_warmup_parent_rejected(self):
        data = self.changed()
        data['dsh']['warmups'][1]['observation_id'] = 'other-after_spill-warmup-r2'
        self.reject(data)

    def test_warmup_parent_receipt_cannot_be_reassigned(self):
        data = self.changed()
        warmup = data['dsh']['warmups'][0]
        warmup['original_tool_content_sha256'] = '0' * 64
        warmup['history_repeat']['original_tool_content_sha256'] = '0' * 64
        self.reject(data)

    def test_same_width_forged_original_size_rejected(self):
        data = self.changed()
        for sample in data['doubao_retention']['records'][:2]:
            sample['tool_content'] = sample['tool_content'].replace('83688 bytes', '99999 bytes')
            sample['tool_content_sha256'] = verify.sha(sample['tool_content'])
        self.reject(data)

    def test_same_codepoint_length_non_ascii_window_rejected(self):
        data = self.changed()
        for sample in data['doubao_retention']['records'][:2]:
            before, label, after = sample['tool_content'].partition('Head (first 2K characters):\n')
            sample['tool_content'] = before + label + '界' + after[1:]
            sample['tool_content_sha256'] = verify.sha(sample['tool_content'])
        self.reject(data)

    def test_selected_human_size_label_cannot_change(self):
        data = self.changed()
        for sample in data['doubao_retention']['records'][:2]:
            sample['tool_content'] = sample['tool_content'].replace('84K characters', '85K characters')
            sample['tool_content_sha256'] = verify.sha(sample['tool_content'])
        self.reject(data)

    def test_ascii_data_cannot_separate_character_units(self):
        shape = verify.retention_windows(self.data['doubao_retention']['records'][0]['tool_content'])
        self.assertEqual(set(shape['head'].values()), {2048})
        self.assertEqual(set(shape['tail'].values()), {2048})
        self.assertEqual(verify.units('界🚀'), {'codepoints': 2, 'utf16_units': 3, 'utf8_bytes': 7})


if __name__ == '__main__':
    unittest.main(verbosity=2)
