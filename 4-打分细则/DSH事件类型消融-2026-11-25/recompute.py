#!/usr/bin/env python3
"""DSH event-type ablation matrix over the pinned r1109 projections.

Offline recompute from the public pinned evidence.json only:
  1. DSH slot row invariants + type census (usage-like type absence);
  2. 5x4 ablation matrix (S3 full / minus each of its three member types),
     auxiliary 100 B diagnostic per group;
  3. missing-type accounting surfaces zero counts instead of passing silently.

Content-level findings (data-layer equality, background-notice origin of the
dabstep 956 B gap) are derived from separately archived originals; this script
does not read them. Fails loudly; prints no conclusions on any Invalid.
"""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

PINNED_REL = '4-打分细则/机制重复口径澄清-2026-11-12/evidence.json'
PINNED_SHA = '925470d3b55b4226d70f5749d45d0c65a161703c4053fa21028ce0516fcd6b5c'
CASES = ('bird-ca-schools-15', 'dabstep-payments-10', 'exercism-py-6',
         'lcb-recent-hard-4', 'tb-cargo-plan')
REPS = ('r1', 'r2', 'r3')
S3 = ('user/message', 'request/header', 'request/context')
LIMIT_B = 100


class Invalid(Exception):
    pass


def require(cond, msg):
    if not cond:
        raise Invalid(msg)


def read_pinned(root):
    path = root / PINNED_REL
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == PINNED_SHA,
            'pinned evidence.json sha mismatch')
    doc = json.loads(raw)
    require(doc.get('schema') == 'r1109-content-free-projection-v1.1',
            'pinned schema drift')
    slots = {s['slot']: s for s in doc['slots']}
    require(len(slots) == 30, 'pinned slot count drift')
    return slots


def check_dsh_rows(rows):
    require(isinstance(rows, list) and rows, 'empty projection')
    types = [row[0] for row in rows]
    counts = Counter(types)
    require(types[0] == 'session' and counts['session'] == 1, 'invalid session head')
    require(counts['turn/start'] > 0 and counts['turn/end'] > 0, 'missing turn bounds')
    for row in rows:
        require(isinstance(row, list) and len(row) == 4, 'bad row schema')
        require(isinstance(row[1], int) and row[1] > 0, 'bad byte count')
        if row[0] != 'response_item':
            require(row[2] is None and row[3] == 0, 'unexpected payload projection')
    return counts


def s3_sum(rows, kept):
    return sum(row[1] for row in rows if row[0] in kept)


def ablation_matrix(slots):
    matrix = {}
    for case in CASES:
        per_cut = {}
        for cut in ('full',) + S3:
            kept = [t for t in S3 if t != cut]
            sums = []
            for rep in REPS:
                rows = slots['dsh__%s__%s' % (case, rep)]['events']
                sums.append(s3_sum(rows, kept))
            spread = max(sums) - min(sums)
            per_cut[cut] = {'sums': sums, 'extreme': spread,
                            'aux_pass': spread <= LIMIT_B}
        matrix[case] = per_cut
    return matrix


def type_census(slots):
    dsh = {k: v for k, v in slots.items() if k.startswith('dsh__')}
    require(len(dsh) == 15, 'dsh slot count drift')
    union = sorted({t for v in dsh.values()
                    for t in (row[0] for row in v['events'])})
    usage_like = [t for t in union
                  if 'usage' in t or 'token' in t or 'cost' in t]
    return union, usage_like


def missing_type_report(slots):
    """Drop user/message from every dabstep slot; counts must surface 0."""
    report = {}
    for rep in REPS:
        rows = [row for row in slots['dsh__dabstep-payments-10__%s' % rep]['events']
                if row[0] != 'user/message']
        report[rep] = Counter(row[0] for row in rows).get('user/message', 0)
    require(all(v == 0 for v in report.values()), 'missing type not surfaced')
    return report


def analyze(slots):
    counts = {slot: check_dsh_rows(slot_doc['events'])
              for slot, slot_doc in slots.items() if slot.startswith('dsh__')}
    union, usage_like = type_census(slots)
    matrix = ablation_matrix(slots)
    missing = missing_type_report(slots)
    flips = [case for case in CASES
             if not matrix[case]['full']['aux_pass']
             and matrix[case]['user/message']['aux_pass']]
    return {'n_dsh_slots': len(counts), 'byte_threshold_b': LIMIT_B,
            'union_types': union, 'usage_like_types': usage_like,
            'ablation_matrix': matrix,
            'single_type_flips': flips,
            'missing_type_counts': missing}


def main():
    parser = __import__('argparse').ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path,
                        default=Path(__file__).resolve().parents[2],
                        help='repository root (default: relative to this script)')
    args = parser.parse_args()
    try:
        result = analyze(read_pinned(args.root))
    except (Invalid, OSError, ValueError, KeyError, TypeError) as exc:
        print('Cannot recompute: %s' % exc, file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2,
                     allow_nan=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
