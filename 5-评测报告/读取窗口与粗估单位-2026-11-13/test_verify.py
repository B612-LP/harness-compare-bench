#!/usr/bin/env python3
"""Read-only positive/negative checks; normal and -O have identical checks."""
import copy
from pathlib import Path
import sys
import unittest
import verify as v


def guard(event, args):
    if event.startswith(('socket.', 'subprocess.', 'os.system', 'os.posix_spawn')):
        raise RuntimeError('offline_tests_only')
    if event == 'open':
        name, mode, flags = args
        if (flags & 3) or (isinstance(mode, str) and any(c in mode for c in 'wax+')):
            raise RuntimeError('tests_are_read_only')
sys.addaudithook(guard)


class Replay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.files = v.load(Path(__file__).absolute().parent)

    def bad(self, change):
        d = copy.deepcopy(self.data)
        change(d)
        with self.assertRaises((ValueError, KeyError, TypeError)):
            v.verify(d, self.files)

    def test_positive_and_all_denominators(self):
        result = v.verify(self.data, self.files)
        self.assertEqual(result['qualified_declarations'], 13)
        self.assertEqual(result['qualified_sessions'], 12)
        self.assertEqual((result['Read_rows'], result['excluded_Read_rows'], result['missing_or_bad_setup']), (23, 10, 5))
        self.assertEqual(result['matches']['full_file_bytes_div4'], 8)
        self.assertEqual(result['matches']['fixed_169860_bytes_div4'], 10)

    def test_changed_actual_estimate_threshold_or_fragment(self):
        self.bad(lambda d: d['points'][0]['declaration'].__setitem__('estimate', 42465))
        self.bad(lambda d: d['points'][0]['declaration'].__setitem__('maximum', 25000))
        self.bad(lambda d: d['points'][0]['declaration'].__setitem__('text', 'invented declaration'))
        self.bad(lambda d: d['points'][0]['declaration'].__setitem__('maximum', True))

    def test_window_coverage_and_units(self):
        self.bad(lambda d: d['points'][7]['derived_metrics']['window_units'].__setitem__('utf8_bytes', 115912))
        self.bad(lambda d: d['points'][0]['derived_metrics'].__setitem__('selected_lines', 1999))
        self.bad(lambda d: d['points'][0]['derived_metrics'].__setitem__('window_sha256', '0' * 64))
        self.bad(lambda d: d['policy'].__setitem__('line_utf16_cap', 4000))
        self.bad(lambda d: d['policy'].__setitem__('units', 'UTF8_bytes'))
        self.bad(lambda d: d['comparison'].__setitem__('fixed_169860_bytes_div4', 13))

    def test_original_vs_derived_and_parameter_binding(self):
        self.bad(lambda d: d['points'][0].__setitem__('original_source_sha256', d['points'][0]['derived_source_sha256']))
        self.bad(lambda d: d['points'][0].__setitem__('derived_source_sha256', d['points'][0]['original_source_sha256']))
        self.bad(lambda d: d['points'][0].__setitem__('public_source_is_original', True))
        self.bad(lambda d: d['points'][0].__setitem__('transformation', 'none'))
        self.bad(lambda d: d['ledger'][3]['arguments_alias'].__setitem__('offset', 1))
        self.bad(lambda d: d['provenance'].__setitem__('raw_http_included', True))
        self.bad(lambda d: d['provenance'].__setitem__('source_pin_is_runtime_attestation', True))

    def test_missing_duplicate_exclusion_and_parallel_points(self):
        self.bad(lambda d: d['points'].pop())
        self.bad(lambda d: d['points'].__setitem__(1, copy.deepcopy(d['points'][0])))
        self.bad(lambda d: d['ledger'].pop())
        self.bad(lambda d: d['ledger'].append(copy.deepcopy(d['ledger'][0])))
        self.bad(lambda d: d['missing_or_bad_setup'].pop())
        self.bad(lambda d: d['points'][10].__setitem__('session', 'another-session'))

    def test_geometry_CRLF_longline_and_default_boundary(self):
        self.assertEqual(v.window('A\r\nB\r\n'), 'A\nB\n')
        self.assertEqual(v.hybrid(v.window('A\r\nB\r\n')), 1)
        self.assertEqual(v.window('x' * 4000), 'x' * 2000 + '... [truncated]')
        self.assertEqual(v.hybrid(v.window('x' * 4000)), 504)
        self.assertEqual(v.u16(v.window('x' * 1999 + '😀z')), 2015)
        # One ASCII prefix + astral text crosses exactly through a surrogate pair.
        split = v.window('a' + '😀' * 1000)
        self.assertEqual((v.u16(split), len(split), len(v.utf8(split)), v.hybrid(split)), (2015, 1016, 4015, 504))
        self.assertTrue(0xD800 <= ord(split[-16]) <= 0xDBFF)
        self.assertEqual(v.metrics('a' + '😀' * 1000)['window_units']['utf8_bytes'], 4015)
        self.assertTrue(v.canonical(v.metrics('a' + '😀' * 1000)).isascii())
        self.assertEqual(v.hybrid(v.window('a' * 2000)), 500)
        self.assertEqual(v.hybrid(v.window('a' * 2001)), 504)
        self.assertEqual(v.metrics('a\n' * 3000)['window_units']['utf8_bytes'], 3999)
        self.assertEqual(v.hybrid(v.window('a\n' * 3000)), 1000)
        self.assertEqual(v.hybrid(v.window(('a' * 99 + '\n') * 60)), 1500)
        self.assertEqual(v.metrics('x\n' * 2000)['window_units']['utf8_bytes'], 3999)
        self.assertEqual(v.metrics('x\n' * 2001)['window_units']['utf8_bytes'], 3999)
        self.assertEqual(v.window('A\n'), 'A\n')
        self.assertEqual(v.window('A'), 'A')
        self.assertEqual(v.hybrid(v.window('')), 37)
        with self.assertRaises(ValueError):
            v.window('x' * 262145)

    def test_Unicode_units_range_and_separate_ceil(self):
        self.assertEqual((len(v.utf8('汉' * 8)), v.u16('汉' * 8), v.hybrid('汉' * 8)), (24, 8, 5))
        self.assertEqual((len(v.utf8('😀' * 8)), v.u16('😀' * 8), len('😀' * 8), v.hybrid('😀' * 8)), (32, 16, 8, 4))
        self.assertEqual(v.hybrid('龦' * 8), 2)
        self.assertEqual(v.hybrid('汉a'), 2)
        self.assertEqual(v.hybrid('一'), 1)
        self.assertEqual(v.hybrid('龥'), 1)

    def test_complete_inventory_and_privacy(self):
        extra = dict(self.files, **{'unexpected.txt': b'x'})
        with self.assertRaises(ValueError):
            v.verify_inventory(extra)
        changed = dict(self.files)
        changed['fixtures/P01.txt'] = b'wrong'
        with self.assertRaises(ValueError):
            v.verify_inventory(changed)
        with self.assertRaises(ValueError):
            v.privacy(('/Users' + '/private/source').encode())
        with self.assertRaises(ValueError):
            v.parse('{"x": 1, "x": 2}')
        with self.assertRaises(ValueError):
            v.parse('{"x": NaN}')


if __name__ == '__main__':
    unittest.main(verbosity=2)
