#!/usr/bin/env python3
"""Public verifier for 跨运行工具绑定 (2026-11-23) machine-readable digest.

Checks internal arithmetic of evidence.json against the published page numbers:
  - bindings 112 total = 93 matched + 19 mismatched; 3 nonzero terminal states;
  - four pairs arm calls sum to 146, and full / argv_only unpaired counts equal 146;
  - exhaustive cross-side cells 1880; full & argv_only correspondences 0;
    cmd_only unique weak correspondences 2;
  - weak-row byte groups and controls present (8/8 near-miss rejected, strict denominator 0).
This is a digest-consistency check: corpus-level reprojection remains sealed.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def need(c, why):
    if not c:
        print('FAIL:', why)
        sys.exit(1)


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else 'evidence.json'
    d = json.load(open(os.path.join(HERE, name), encoding='utf-8'))
    b = d['bindings']
    need(b['total'] == 112 and b['matched_a_eq_b'] == 93, '112 total / 93 matched')
    need(b['matched_a_eq_b'] + b['mismatched'] == b['total'], 'matched+mismatched=total')
    need(b['nonzero_terminal_states'] == 3, '3 nonzero terminal states')
    arms = d['pairs']['calls_a_b']
    need(len(arms) == 4, 'four pairs')
    total = sum(a + c for a, c in arms)
    need(total == d['pairs']['total_calls'] == 146, 'pair calls sum 146')
    ex = d['exhaustive']
    need(ex['cross_side_cells'] == 1880, '1880 cells')
    need(ex['full']['correspondences'] == 0 and ex['full']['unpaired_calls'] == 146, 'full 0/146')
    need(ex['argv_only']['correspondences'] == 0 and ex['argv_only']['unpaired_calls'] == 146,
         'argv_only 0/146')
    need(ex['full']['unpaired_calls'] == total and ex['argv_only']['unpaired_calls'] == total,
         'unpaired counts equal summed pair calls')
    need(ex['cmd_only']['unique_weak_correspondences'] == 2, 'cmd_only 2 weak')
    w = d['weak_rows']['bytes']
    need(w['a_b_same_value'] == [22127, 3889] and w['b_only'] == [10107, 3889]
         and w['equal_length_diff_value'] == [10212, 10660]
         and w['equal_length_diff_value_2'] == [3993, 4432], 'weak byte groups')
    c = d['controls']
    need(c['identity_near_miss_counterproof_rejected'] == '8/8' and c['strict_denominator'] == 0,
         'controls')
    print('BINDING-DIGEST OK (112/93/3, four pairs 146 calls, 1880 cells, 0 correspondences)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
