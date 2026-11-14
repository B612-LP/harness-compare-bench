#!/usr/bin/env python3
"""Read-only semantic counterexamples; ordinary and -O must behave identically."""
import copy
import datetime as dt
import json
from pathlib import Path
import sys
import unittest
from unittest import mock
import verify as v

def guard(event, args):
    if event.startswith(('socket.', 'subprocess.', 'os.exec', 'os.spawn')) or event == 'os.system':
        raise RuntimeError('no live operations')
    if event == 'open':
        path, mode, flags = args
        if (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (isinstance(flags, int) and flags & 3 != 0):
            raise RuntimeError('tests are read only')
sys.addaudithook(guard)
ROOT = Path(__file__).absolute().parent
FILES = v.load(ROOT)
DATA = v.parse(FILES['evidence.json'])

class SelectedEvidenceTests(unittest.TestCase):
    def bad(self, change):
        data = copy.deepcopy(DATA)
        change(data)
        # Recommit mutated JSON, so rejection below must exercise semantic checks,
        # not just the final fixed data hash. Actual CLI always uses its fixed hash.
        with mock.patch.object(v, 'BASELINE', v.sha(v.canonical(data))):
            with self.assertRaises(ValueError):
                v.verify(data)

    def test_positive_and_inventory(self):
        v.verify_inventory(FILES)
        metrics = v.verify(DATA)
        self.assertEqual((metrics['fd_samples'], metrics['tool_pairs'], metrics['successful_nonempty_tool_returns']), (1124, 28, 8))
        self.assertEqual(metrics['negative_timestamp_deltas_ms'], [-3, -42])
        self.assertEqual(DATA['tool_pairs'][0]['call_line'], 7)
        self.assertEqual(DATA['tool_pairs'][0]['result_line'], 8)

    def test_denominators_unique_linkage_and_prefix_overlap(self):
        self.bad(lambda d: d['fd']['records'].pop())
        self.bad(lambda d: d['tool_pairs'].append(copy.deepcopy(d['tool_pairs'][0])))
        self.bad(lambda d: d['tool_pairs'][1].update(call_id='T01', result_call_id='T01'))
        self.bad(lambda d: d['tool_pairs'][0].update(result_call_id='T02'))
        self.bad(lambda d: d['reads'].pop())
        self.bad(lambda d: d['reads'][1].update(pair_id=d['reads'][0]['pair_id']))
        self.bad(lambda d: d['raw_trace_commitments']['followup'].update(lines=87))
        self.bad(lambda d: d['declared_metrics'].update(successful_nonempty_tool_returns=9))
        self.bad(lambda d: d['tool_pairs'][0].update(call_line=6, result_line=7))

    def test_time_boundary_timezone_and_reverse_log_times(self):
        start = v.when('2026-11-04T15:56:29.304528+00:00')
        end = start + dt.timedelta(seconds=10)
        self.assertEqual(start, v.when('2026-11-04T23:56:29.304528+08:00'))
        with self.assertRaises(ValueError):
            v.when('2026-11-04T15:56:29')
        self.assertTrue(v.paired(v.TARGET, start, end, start, end))
        self.assertFalse(v.paired(v.TARGET, start, end + dt.timedelta(microseconds=1), start, end))
        self.assertFalse(v.paired(v.TARGET, start - dt.timedelta(microseconds=1), start, start, end))
        self.bad(lambda d: d['declared_metrics'].update(negative_timestamp_deltas_ms=[0, 0]))
        self.bad(lambda d: d['declared_metrics'].update(earliest_post_envelope_read_call_seconds=0))
        self.bad(lambda d: d['fd']['records'][0].__setitem__(0, '2026-11-04T15:56:29'))

    def test_alias_comparison_is_not_object_identity(self):
        start = v.when('2026-11-04T15:56:29+00:00')
        end = start + dt.timedelta(seconds=1)
        self.assertFalse(v.paired('different/reference-note.txt', start, start, start, end))
        self.assertFalse(v.paired('outside-task/../outside-task/reference-note.txt', start, start, start, end))
        self.assertFalse(v.paired(v.TARGET, end + dt.timedelta(seconds=1), end + dt.timedelta(seconds=1), start, end))
        self.bad(lambda d: d['reads'][0].update(target_alias=v.TARGET))
        self.bad(lambda d: d['reads'][1].update(target_alias=d['reads'][0]['target_alias']))
        self.bad(lambda d: d['provenance'].update(path_alias_scope='original_physical_object_authenticated'))

    def test_nonempty_error_status_and_unknown_truth(self):
        self.bad(lambda d: d['reads'][0].update(output_text_chars=0))
        self.bad(lambda d: d['reads'][0].update(output_text_chars=True))
        self.bad(lambda d: d['reads'][0].update(explicit_error=True))
        self.bad(lambda d: d['reads'][0].update(output_type='json'))
        self.bad(lambda d: d['tool_pairs'][0].update(result_status='failed'))
        for key in DATA['adjudication']:
            self.bad(lambda d, key=key: d['adjudication'].__setitem__(key, 0))
        self.bad(lambda d: d['declared_metrics'].update(matched_log_controls=False))

    def test_command_elapsed_is_not_coverage_or_read_opportunities(self):
        self.bad(lambda d: d['declared_metrics'].update(coverage_fraction=0.061))
        self.bad(lambda d: d['declared_metrics'].update(read_opportunities=1124))
        self.bad(lambda d: d['fd']['records'][0].__setitem__(1, -0.1))
        self.bad(lambda d: d['fd']['records'][0].__setitem__(2, 1))
        self.bad(lambda d: d['fd']['records'][0].__setitem__(2, False))
        self.bad(lambda d: d['fd']['records'][0].__setitem__(3, 'timeout'))
        self.bad(lambda d: d['fd'].update(content_read_authority=True))

    def test_original_versus_derived_hash_and_private_claims(self):
        self.bad(lambda d: d['derived_hashes'].update(fd_records_sha256=v.FD_RAW_SHA))
        self.bad(lambda d: d['derived_hashes'].update(tool_pairs_sha256=v.RAW['followup']['sha256']))
        self.bad(lambda d: d['raw_trace_commitments'].update(old_is_exact_byte_prefix_private_audit=False))
        self.bad(lambda d: d['provenance'].update(raw_prefix_verification='public_raw_recomputed'))
        self.bad(lambda d: d['provenance'].update(absence_of_bait_literals='no_unlogged_reads'))

    def test_privacy_inventory_and_strict_json(self):
        with self.assertRaises(ValueError):
            v.privacy(('/Us' + 'ers/private/file').encode())
        with self.assertRaises(ValueError):
            v.parse('{"x": 1, "x": 2}')
        with self.assertRaises(ValueError):
            v.parse('{"x": NaN}')
        extra = dict(FILES); extra['extra.txt'] = b'x'
        with self.assertRaises(ValueError):
            v.verify_inventory(extra)
        changed = dict(FILES); changed['evidence.json'] += b' '
        with self.assertRaises(ValueError):
            v.verify_inventory(changed)

if __name__ == '__main__':
    unittest.main(verbosity=2)
