#!/usr/bin/env python3
"""Read only four exact public Git blobs; calculate geometry, not fixture admission."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

COMMIT = 'dd5a12f651527923a412f6727d5d2f9c22457026'
PINS = {
    '同对象同窗读取检测校准': '83a8e036c468d2636d183c2dbb316e523d4faa4b2810cf0e3c229ae112a10d4c',
    '读取探针窗口空隙': 'c038bbb1da7751a24e06f63bd9f445e6b66e4f7f658a2f079ec91dbe5610aba8',
    '读取探针单次偏移': 'c8e5fd4527409bd550d266901566867779d6624fe497b5eb59a311b6d408f45d',
    '读取探针文件映射': '5f012a8aef09290dea9e794982f195710b373d49c9f64d263087a980a4a5f774',
}


def need(check, normal_code):
    if not check:
        raise ValueError(normal_code)


def unique(entries):
    result = {}
    for k, v in entries:
        need(k not in result, 'DUPLICATE_JSON')
        result[k] = v
    return result


def integer(x):
    need(type(x) is int, 'NON_INTEGER_NS')
    return x


def pair(v):
    need(type(v) is list and len(v) == 2, 'NOT_A_PAIR')
    a, b = map(integer, v)
    need(a <= b, 'REVERSED_PAIR')
    return a, b


def read_sources(root):
    env = dict(os.environ, GIT_NO_REPLACE_OBJECTS='1', GIT_NO_LAZY_FETCH='1', GIT_ALLOW_PROTOCOL='')
    for name, sha in PINS.items():
        leaf = f'{COMMIT}:5-评测报告/{name}-2026-11-19/evidence.json'
        blob = subprocess.run(['git', '-C', str(root), 'cat-file', 'blob', leaf], env=env,
                              check=True, capture_output=True, timeout=8).stdout
        need(len(blob) <= 64_000 and hashlib.sha256(blob).hexdigest() == sha, 'SOURCE_HASH')
        yield json.loads(blob.decode('utf-8', errors='strict'), object_pairs_hook=unique)


def bound(lo, hi, sample, label_lo, label_hi, strict):
    start, end = sample
    need(start <= end and lo <= hi and type(strict) is bool, 'INVALID_INTERVAL')
    return [(label_lo, True, lo - start + int(strict)), (label_hi, False, hi - end - int(strict))]


def intersect(rules):
    low = max(n for _, is_lower, n in rules if is_lower)
    high = min(n for _, is_lower, n in rules if not is_lower)
    return {
        'bounds_ns': [low, high],
        'lower_rules': [label for label, is_lower, n in rules if is_lower and n == low],
        'upper_rules': [label for label, is_lower, n in rules if not is_lower and n == high],
        'nonempty_geometry': low <= high,
        'zero_admits_geometry': low <= 0 <= high,
        'symmetric_integer_radius_ns': min(-low, high) if low <= 0 <= high else None,
    }


def accept(rules, shift):
    return all(shift >= value if is_lower else shift <= value for _, is_lower, value in rules)


def result(root):
    pair_doc, gap_doc, offset_doc, map_doc = read_sources(root)
    measured, rule_sets = {}, {}
    rows = pair_doc['pairs']
    need([row['pair'] for row in rows] == ['long', 'short'], 'PAIR_ORDER')
    for row in rows:
        a = row['arms']
        need([arm['role'] for arm in a] == ['read', 'open_only'], 'ROLE_ORDER')
        lo = max([0] + [integer(arm['post_fstat_ns']) for arm in a])
        hi = min([integer(row['planned_hold_ns'])] + [integer(arm['close_start_ns']) for arm in a])
        s0, s1 = pair([row['sample']['start_ns'], row['sample']['end_ns']])
        suffix = row['pair']
        rule_sets[suffix] = bound(lo, hi, (s0, s1), 'post_fstat', 'planned_hold_or_close', False)
        measured[suffix] = {'recorded_decision': row['decision'], 'truth_report_passed': row['truth_pair_qualified'],
                            'healthy': row['sample']['exit'] == 0 and row['sample']['stderr_empty'] is True
                            and row['sample']['stdout_empty'] is False}
        measured[suffix]['window_minus_envelope_ns'] = (hi - lo) - (s1 - s0)

    gap = gap_doc['result']
    g = tuple(gap['arms'][k] for k in ('read', 'open_only'))
    w0 = max(pair(a['witness_open'])[1] for a in g)
    w1 = min(pair(a['witness_close'])[0] for a in g)
    need(pair(gap['shared_witness_window_ns']) == (w0, w1), 'WITNESS_WINDOW')
    before = pair(gap['samples']['before']['envelope'])
    after = pair(gap['samples']['after']['envelope'])
    earliest_open = min(pair(a['target_open'])[0] for a in g)
    latest_closed = max(pair(a['target_close'])[1] for a in g)
    rule_sets['gap'] = (bound(w0, w1, before, 'before_inside_witness_left', 'before_inside_witness_right', True)
                        + bound(w0, w1, after, 'after_inside_witness_left', 'after_inside_witness_right', True)
                        + [('after_later_than_last_target_close', True, latest_closed - after[0] + 1),
                           ('before_earlier_than_first_target_open', False, earliest_open - before[1] - 1)])
    measured['gap'] = {'recorded_decision': gap['classification']}

    offset = offset_doc['observed']
    a = offset['arms']
    hold = pair(offset['confirmed_common_hold_rel_ns'])
    need(hold[0] == max(pair(v['open_rel_ns'])[1] for v in a.values()), 'HOLD_START')
    last_action = max(pair(v['action_rel_ns'])[1] for v in a.values())
    rule_sets['offset'] = bound(max(hold[0], last_action), hold[1], pair(offset['collector_envelope_rel_ns']),
                                'stable_hold_left_and_last_action', 'stable_hold_right', True)
    measured['offset'] = {'recorded_decision': offset_doc['decision']}

    a = tuple(map_doc['arms'][k] for k in ('consume', 'map_only'))
    lo = max(integer(v['parent_action_received_ns']) for v in a)
    hi = min(pair(v['final_map_fd_check_ns'])[0] for v in a)
    rule_sets['mapping'] = bound(lo, hi, pair(map_doc['collection']['envelope_ns']),
                                 'last_parent_receipt', 'first_final_check_start', True)
    measured['mapping'] = {'recorded_decision': map_doc['conclusion']}

    for k, rules in rule_sets.items():
        measured[k].update(intersect(rules))
    controls = 0
    for k, rules in rule_sets.items():
        lo, hi = measured[k]['bounds_ns']
        if lo <= hi:
            need(accept(rules, lo) and accept(rules, hi) and not accept(rules, lo-1) and not accept(rules, hi+1), 'BOUNDARY')
            controls += 4
        else:
            need(k == 'short' and not accept(rules, lo) and not accept(rules, hi), 'EMPTY_GEOMETRY')
            need(not measured[k]['healthy'] and not measured[k]['truth_report_passed'], 'SHORT_GATES_CHANGED')
            controls += 4
    need(intersect(bound(5, 9, (5, 10), 'a', 'b', False))['nonempty_geometry'] is False, 'START_ONLY')
    need(bound(5, 10, (6, 9), 'a', 'b', True) == bound(205, 210, (206, 209), 'a', 'b', True), 'COMMON_ORIGIN')
    need(intersect(bound(5, 10, (5, 10), 'a', 'b', False))['bounds_ns'] == [0, 0] and
         intersect(bound(5, 10, (5, 10), 'a', 'b', True))['bounds_ns'] == [1, -1], 'INCLUSIVE_V_STRICT')
    return {'source_commit': COMMIT, 'unit': 'ns', 'model': 'add_one_integer_offset_to_all_collector_markers_per_trial',
            'comparisons': measured, 'self_checks': controls+3, 'new_fixture_or_product_trials': 0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--check-sibling', action='store_true')
    opts = parser.parse_args()
    data = json.dumps(result(opts.root), ensure_ascii=False, sort_keys=True, indent=2) + '\n'
    if opts.check_sibling:
        need((Path(__file__).parent/'evidence.json').read_bytes() == data.encode('utf-8'), 'EVIDENCE_MISMATCH')
        print('OK: 5 fixed geometry results and 23 controls')
    else:
        sys.stdout.write(data)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, TypeError, KeyError, OSError, subprocess.SubprocessError) as exc:
        raise SystemExit('REJECT: ' + type(exc).__name__ + ': ' + str(exc))
