#!/usr/bin/env python3
"""Counterfactual rational closed geometry from four exact public evidence blobs."""
import argparse
from fractions import Fraction as Q
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

BASE = 'dd5a12f651527923a412f6727d5d2f9c22457026'
PINS = (
    ('同对象同窗读取检测校准', '83a8e036c468d2636d183c2dbb316e523d4faa4b2810cf0e3c229ae112a10d4c'),
    ('读取探针窗口空隙', 'c038bbb1da7751a24e06f63bd9f445e6b66e4f7f658a2f079ec91dbe5610aba8'),
    ('读取探针单次偏移', 'c8e5fd4527409bd550d266901566867779d6624fe497b5eb59a311b6d408f45d'),
    ('读取探针文件映射', '5f012a8aef09290dea9e794982f195710b373d49c9f64d263087a980a4a5f774'),
)
BOUNDS_AT_ONE = {'long': [-90017000, 507557000], 'short': [-2283000, -4413000],
                 'gap': [-156693999, 173491999], 'offset': [-162282999, 433706999],
                 'mapping': [-148430999, 462026999]}


def demand(test, code):
    if not test:
        raise ValueError(code)


def unique(entries):
    out = {}
    for k, v in entries:
        demand(k not in out, 'DUPLICATE_KEY')
        out[k] = v
    return out


def no_number(_):
    raise ValueError('NONFINITE_JSON')


def ns(v):
    demand(type(v) is int and abs(v) <= 10**12, 'NONINTEGER_MARKER')
    return v


def ordered(v):
    demand(type(v) in (list, tuple) and len(v) == 2, 'BAD_ENVELOPE')
    a, b = map(ns, v)
    demand(a <= b, 'ENVELOPE_ORDER')
    return a, b


def acquire(root):
    env = dict(os.environ, GIT_NO_REPLACE_OBJECTS='1', GIT_NO_LAZY_FETCH='1', GIT_ALLOW_PROTOCOL='')
    for name, pin in PINS:
        leaf = f'{BASE}:5-评测报告/{name}-2026-11-19/evidence.json'
        p = subprocess.run(['git', '-C', str(root), 'cat-file', 'blob', leaf], env=env,
                           capture_output=True, check=True, timeout=8).stdout
        demand(0 < len(p) <= 64_000 and sha256(p).hexdigest() == pin, 'SOURCE_HASH')
        yield json.loads(p.decode('utf-8', 'strict'), object_pairs_hook=unique, parse_constant=no_number)


def rule(label, lower, t, v):
    return label, lower, ns(t), ns(v)


def enclosure(name, anchor, sample, strict):
    lo, hi = ordered(anchor)
    s, e = ordered(sample)
    return (rule(name + '_left', True, s, lo + int(strict)),
            rule(name + '_right', False, e, hi - int(strict)))


def make_rules(rows, gap, offset, mapping):
    systems, starts = {}, {}
    demand([r['pair'] for r in rows['pairs']] == ['long', 'short'], 'PAIR_ORDER')
    for r in rows['pairs']:
        demand([a['role'] for a in r['arms']] == ['read', 'open_only'], 'ARM_ORDER')
        lo = max(0, *(ns(a['post_fstat_ns']) for a in r['arms']))
        hi = min(ns(r['planned_hold_ns']), *(ns(a['close_start_ns']) for a in r['arms']))
        sample = ordered((r['sample']['start_ns'], r['sample']['end_ns']))
        starts[r['pair']] = sample[0]
        systems[r['pair']] = (enclosure('window', (lo, hi), sample, False),)
    short = rows['pairs'][1]
    demand(short['decision'] == 'unknown' and short['truth_pair_qualified'] is False and
           (short['sample']['exit'] != 0 or short['sample']['stderr_empty'] is not True or
            short['sample']['stdout_empty'] is not False), 'SHORT_RECORDED_GATES')

    g = gap['result']
    arms = [g['arms'][key] for key in ('read', 'open_only')]
    w0 = max(ordered(a['witness_open'])[1] for a in arms)
    w1 = min(ordered(a['witness_close'])[0] for a in arms)
    demand((w0, w1) == ordered(g['shared_witness_window_ns']), 'WITNESS_WINDOW')
    before = ordered(g['samples']['before']['envelope'])
    after = ordered(g['samples']['after']['envelope'])
    demand(before[1] < after[0], 'GAP_ORDER')
    earliest = min(ordered(a['target_open'])[0] for a in arms)
    latest = max(ordered(a['target_close'])[1] for a in arms)
    b = enclosure('before_witness', (w0, w1), before, True) + (
        rule('before_target', False, before[1], earliest - 1),)
    a = enclosure('after_witness', (w0, w1), after, True) + (
        rule('after_target', True, after[0], latest + 1),)
    starts['gap'] = before[0]
    systems['gap'] = (b + a,)

    o = offset['observed']
    arms = o['arms']
    demand(sorted(arms) == ['A', 'B', 'C', 'D'], 'OFFSET_SCOPE')
    hold = ordered(o['confirmed_common_hold_rel_ns'])
    demand(hold[0] == max(ordered(a['open_rel_ns'])[1] for a in arms.values()), 'HOLD_START')
    latest_action = max(ordered(a['action_rel_ns'])[1] for a in arms.values())
    sample = ordered(o['collector_envelope_rel_ns'])
    starts['offset'] = sample[0]
    systems['offset'] = (enclosure('settled_hold', (max(hold[0], latest_action), hold[1]), sample, True),)

    arms = [mapping['arms'][key] for key in ('consume', 'map_only')]
    lo = max(ns(a['parent_action_received_ns']) for a in arms)
    hi = min(ordered(a['final_map_fd_check_ns'])[0] for a in arms)
    sample = ordered(mapping['collection']['envelope_ns'])
    starts['mapping'] = sample[0]
    systems['mapping'] = (enclosure('parent_receipt_to_final_check', (lo, hi), sample, True),)
    return systems, starts, (b, a)


def offsets(group, t0, rate):
    low = [Q(x - t0) - rate * (t - t0) for _, direction, t, x in group if direction]
    high = [Q(x - t0) - rate * (t - t0) for _, direction, t, x in group if not direction]
    demand(bool(low and high), 'EMPTY_SIGN_PARTITION')
    return max(low), min(high)


def encode(value):
    if value is None:
        return None
    return [value.numerator, value.denominator]


def solve(groups, t0):
    lo, hi = Q(0), None
    ll, ul, impossible = [], [], False
    for group in groups:
        demand(any(r[1] for r in group) and any(not r[1] for r in group), 'EMPTY_RULE_GROUP')
        for left, direction, lt, lx in group:
            if not direction:
                continue
            for right, direction, rt, rx in group:
                if direction:
                    continue
                coef, rhs = rt - lt, rx - lx
                if coef == 0:
                    if rhs < 0:
                        impossible = True
                    continue
                edge = Q(rhs, coef)
                labels = [left, right]
                if coef < 0:
                    if edge > lo:
                        lo, ll = edge, [labels]
                    elif edge == lo:
                        ll.append(labels)
                elif hi is None or edge < hi:
                    hi, ul = edge, [labels]
                elif edge == hi:
                    ul.append(labels)
    empty = impossible or (hi is not None and (hi <= 0 or hi < lo))
    low, high = Q(99, 100), Q(101, 100)
    within = not empty and lo <= high and (hi is None or hi >= low)
    all_band = not empty and lo <= low and (hi is None or hi >= high)
    distance = None if empty else max(Q(0), lo-1, 0 if hi is None else 1-hi)
    at_one = [offsets(g, t0, Q(1)) for g in groups]
    return {'alpha_lower': encode(lo), 'alpha_upper': encode(hi), 'lower_open': lo == 0,
            'upper_closed': hi is not None, 'empty': empty, 'binding_lower': ll, 'binding_upper': ul,
            'overlap_one_percent': within, 'whole_one_percent': all_band, 'distance_from_one': encode(distance),
            'offsets_at_one_ns': [[int(x), int(y)] for x, y in at_one]}


def validate_boundary(groups, t0, packaged):
    for key, step in (('alpha_lower', -1), ('alpha_upper', 1)):
        edge = packaged[key]
        if edge is None or edge[0] == 0:
            continue
        demand(not packaged['empty'], 'ACTUAL_EMPTY_RATE')
        edge = Q(*edge)
        outcome = [offsets(g, t0, edge) for g in groups]
        demand(all(a <= b for a, b in outcome) and any(a == b for a, b in outcome), 'ACTIVE_BOUNDARY')
        if edge + step * Q(1, 10**9) > 0:
            outside = [offsets(g, t0, edge + step * Q(1, 10**9)) for g in groups]
            demand(any(a > b for a, b in outside), 'OUTSIDE_RATE_BOUNDARY')


def report(root):
    systems, starts, separate = make_rules(*acquire(root))
    out = {k: solve(v, starts[k]) for k, v in systems.items()}
    demand({k: v['offsets_at_one_ns'][0] for k, v in out.items()} == BOUNDS_AT_ONE, 'RIGID_REGRESSION')
    for k, v in systems.items():
        validate_boundary(v, starts[k], out[k])
        for shift in (-4321, 10**8):
            moved = tuple(tuple(rule(l, d, t + shift, x + shift) for l, d, t, x in g) for g in v)
            demand(solve(moved, starts[k] + shift) == out[k], 'COMMON_ORIGIN')
    relaxed = solve(separate, starts['gap'])
    fake = (enclosure('a', (1, 2), (0, 1), False), enclosure('b', (20, 21), (5, 6), False))
    demand(solve(fake, 0)['overlap_one_percent'] and solve((fake[0] + fake[1],), 0)['empty'], 'COMMON_V_SEPARATE')
    fixed = enclosure('one_exact', (0, 10), (0, 10), False)
    margin = enclosure('one_margin', (0, 10), (0, 10), True)
    demand(solve((fixed,), 0)['alpha_upper'] == [1, 1] and solve((margin,), 0)['alpha_upper'] == [4, 5], 'MARGIN')
    contradictory = (rule('a', True, 1, 3), rule('b', False, 1, 2))
    demand(solve((contradictory,), 0)['empty'], 'ZERO_COEFFICIENT')
    return {'source_commit': BASE, 'comparisons': out, 'gap_separate_offsets_relaxation': relaxed,
            'alpha_and_offset_model': 'positive rational per-trial rate and one common rational offset',
            'short_recorded_decision_unchanged': 'unknown', 'new_trials': 0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--check-sibling', action='store_true')
    a = parser.parse_args()
    raw = (json.dumps(report(a.root), sort_keys=True, indent=2) + '\n').encode('ascii')
    if a.check_sibling:
        demand((Path(__file__).parent/'evidence.json').read_bytes() == raw, 'EVIDENCE_MISMATCH')
        print('OK: exact affine and common-intercept clock geometry')
    else:
        print(raw.decode('ascii'), end='')


if __name__ == '__main__':
    try:
        main()
    except (KeyError, ValueError, TypeError, OSError, subprocess.SubprocessError) as exc:
        raise SystemExit('REJECT:' + type(exc).__name__ + ':' + str(exc))
