#!/usr/bin/env python3
"""Recompute the public weighted-only aggregate from three pinned local Git blobs."""

import argparse
from decimal import Decimal
from fractions import Fraction as F
from hashlib import sha256
from itertools import product
import json
import os
from pathlib import Path
import subprocess
import sys

COMMIT = 'dd5a12f651527923a412f6727d5d2f9c22457026'
CASES = ('bird-ca-schools-15', 'dabstep-payments-10', 'exercism-py-6', 'lcb-recent-hard-4', 'tb-cargo-plan')
PRODUCTS = ('codex', 'dsh')
LABELS = (1, 2, 3)
SOURCES = {
    'r1': ('5-评测报告/可重复性-n3-2026-10-29/verify-matrix-selftest-r1030.json',
           'c81c490ce041e259733214209ea4ef61dc226406', '31534cec32ffdda781f2ea2127acd1b015eb6f8e06eabfde7aab5bdf89f7d09c'),
    'r23': ('5-评测报告/可重复性-n3-2026-10-29/verify-matrix-r1031-n3.json',
            '8de594f3b743a85b6b9bfd4f723e1495ee5066ef', '2bdac21d038ab5827c2aff006c06bba539bd18a91a7ea899f2c6797066999e12'),
    'a': ('5-评测报告/可信冻结-2026-10-29-v2/official-main-table.json',
          '6dce19eb343c1829b4ac9a8407774666fcf9de0b', 'cc6fd8a42627ed81680ae3f180516a54f0061a28a688615deabe317da9dac043'),
}


def demand(ok, tag):
    if not ok:
        raise ValueError(tag)


def git(repo, *args):
    env = dict(os.environ)
    for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR', 'GIT_OBJECT_DIRECTORY',
                'GIT_ALTERNATE_OBJECT_DIRECTORIES', 'GIT_CONFIG_COUNT', 'GIT_CONFIG_PARAMETERS'):
        env.pop(key, None)
    env.update(GIT_ALLOW_PROTOCOL='', GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0',
               GIT_NO_REPLACE_OBJECTS='1', GIT_OPTIONAL_LOCKS='0')
    return subprocess.run(['git', '-c', 'protocol.allow=never', '-C', str(repo), *args],
                          env=env, check=True, capture_output=True, timeout=5).stdout


def unique_pairs(pairs):
    d = {}
    for k, v in pairs:
        demand(k not in d, 'duplicate JSON key')
        d[k] = v
    return d


def reject_constant(_):
    raise ValueError('nonfinite JSON constant')


def load(repo, pin):
    path, blob, digest = pin
    listing = f'100644 blob {blob}\t{path}\0'.encode('utf-8')
    demand(git(repo, 'ls-tree', '-z', COMMIT, '--', path) == listing, 'Git tree identity')
    data = git(repo, 'cat-file', 'blob', f'{COMMIT}:{path}')
    demand(sha256(data).hexdigest() == digest, 'source checksum')
    return json.loads(data, parse_float=Decimal, object_pairs_hook=unique_pairs, parse_constant=reject_constant)


def rounded(x, places=2):
    return F(round(F(x) * (10 ** places)), 10 ** places)  # Fraction: exact, half-even


def display(x):
    n = round(F(x) * 100)
    return ('-' if n < 0 else '') + f'{abs(n)//100}.{abs(n)%100:02d}'


def decimal_agrees(actual, expected):
    if type(actual) not in (int, Decimal):
        return False
    d = Decimal(actual)
    return d.is_finite() and F(d) == rounded(expected, max(2, -d.as_tuple().exponent))


def identifier_set(xs):
    demand(all(type(s) is str and s for s in xs) and len(xs) == len(set(xs)), 'identifier set')
    return set(xs)


def read_projection(docs):
    membership = docs['a']
    demand(membership['rule_version'] == 'freeze-20261029-v2', 'membership version')
    formal = identifier_set(membership['groups']['A_same_model'])
    non_a = identifier_set(membership['groups']['B_native']) | identifier_set([x['event_id'] for x in membership['rejected']])
    demand(len(formal) == 10 and not formal & non_a, 'formal membership shape')
    totals = docs['r1']['scoring_constants']['totals']
    demand(totals == docs['r23']['scoring_constants']['totals'] and set(totals) == set(CASES), 'denominator map')
    all_ids, fractions, rewards = set(), {}, {}
    for key, labels in (('r1', (1,)), ('r23', (2, 3))):
        matrix = docs[key]
        rows = matrix['runs']
        ids = identifier_set([row['event_id'] for row in rows])
        demand(not ids & (all_ids | non_a), 'duplicate or incompatible membership')
        demand((ids == formal) if key == 'r1' else not ids & formal, 'formal identifier join')
        all_ids |= ids
        wanted = set(product(PRODUCTS, labels, CASES))
        demand(len(rows) == matrix['runs_expected'] == matrix['runs_found'] == len(wanted), 'matrix size')
        for row in rows:
            p, r, case = row['product'], row['rep'], row['case']
            coord = p, r, case
            demand(type(r) is int and coord in wanted, 'matrix coordinate')
            wanted.remove(coord)
            check = row['checks']['c_weighted_recompute']
            n, d, count = (check[k] for k in ('earned', 'expected_denominator', 'scored_items'))
            demand(all(type(x) is int for x in (n, d, count)) and 0 <= n <= d and d == count == totals[case] and d > 0,
                   'case tally or denominator')
            frac = F(n, d)
            cell = matrix['aggregate'][p][str(r)]
            reported = [row['recomputed']['weighted'], cell['per_case_weighted'][case]]
            reported += [check[k] for k in ('weighted_recomputed', 'weighted_stdout', 'weighted_meta')]
            demand(all(decimal_agrees(x, frac * 100) for x in reported), 'weighted decimal echo')
            bits = [row['recomputed']['reward'], check['reward_stdout'], check['reward_meta'], cell['per_case_reward'][case]]
            demand(all(type(x) is int and x in (0, 1) and x == bits[0] for x in bits), 'recorded reward echo')
            fractions[coord], rewards[coord] = frac, bits[0]
        demand(not wanted, 'incomplete matrix')
        for p, r in product(PRODUCTS, labels):
            block = matrix['aggregate'][p]
            cell = block[str(r)]
            pct_sum = sum(fractions[p, r, k] for k in CASES) * 100
            binary_count = sum(rewards[p, r, k] for k in CASES)
            demand(F(cell['weighted_total']) == rounded(pct_sum), 'weighted total display')
            demand(block['headline_by_rep'][str(r)] == cell['headline'] == binary_count, 'recorded headline total')
    return totals, fractions, rewards


def sign(x):
    return (x > 0) - (x < 0)


def scale(c, d):
    return {'exact_by_product': {'codex': c, 'dsh': d}, 'gap_exact_codex_minus_dsh': c - d,
            'sign': sign(c-d), 'display_by_product': {'codex': display(c), 'dsh': display(d)},
            'display_gap_by_subtracting_rounded_totals': display(rounded(c)-rounded(d)),
            'display_gap_by_rounding_exact_difference': display(c-d)}


def formal_tv(diff):
    initial = sum(diff) / 5
    span = max(diff) - min(diff)
    donor, receiver = diff.index(max(diff)), diff.index(min(diff))
    root = initial / span
    demand(0 < root < F(1, 5) and 2 * root <= F(1, 5), 'formal transfer capacity')

    def witness(delta):
        w = [F(1, 5)] * 5
        w[donor] -= delta
        w[receiver] += delta
        demand(sum(w) == 1 and min(w) >= 0 and sum(abs(v-F(1, 5)) for v in w) / 2 == delta, 'formal witness simplex')
        return {'weights_in_case_order': w, 'tv': delta,
                'gap_mean_percentage_points': 100 * sum(v*d for v, d in zip(w, diff))}

    tie, strict = witness(root), witness(root*2)
    demand(tie['gap_mean_percentage_points'] == 0 and strict['gap_mean_percentage_points'] < 0, 'formal witness direction')
    return {'donor': CASES[donor], 'receiver': CASES[receiver], 'full_range_of_case_differences': span,
            'min_tv_to_tie': root, 'min_tv_to_tie_weight_percentage_points': root*100,
            'strict_reversal_tv_infimum': root, 'strict_reversal_infimum_attained': False,
            'tie': tie, 'one_strict_reversal_example': strict}


def projection(repo):
    demand(git(repo, 'rev-parse', '--verify', f'{COMMIT}^{{commit}}').strip() == COMMIT.encode('ascii'), 'commit identity')
    totals, a, rewards = read_projection({k: load(repo, pin) for k, pin in SOURCES.items()})
    total = {(p,r): sum(a[p,r,k] for k in CASES) * 100 for p,r in product(PRODUCTS, LABELS)}
    d = {r: tuple(a['codex',r,k]-a['dsh',r,k] for k in CASES) for r in LABELS}
    same = []
    for r in LABELS:
        c, b = (total[p,r] for p in PRODUCTS)
        same.append({'label': r, 'formal_a': r == 1, 'case_differences_in_case_order': d[r],
                     'sum_points_out_of_500': scale(c,b), 'mean_percentage_points': scale(c/5,b/5),
                     'recorded_binary_count_out_of_five': {p: sum(rewards[p,r,k] for k in CASES) for p in PRODUCTS},
                     'equal_four_case_gap_mean_percentage_points_by_deleted_case': {
                         case: sum(v for j,v in enumerate(d[r]) if j != i)*25 for i,case in enumerate(CASES)}})
    cartesian = []
    for i, j in product(LABELS, repeat=2):
        gap = total['codex',i] - total['dsh',j]
        cartesian.append({'codex_label': i, 'dsh_label': j, 'same_label': i == j,
                          'gap_sum_points': gap, 'sign': sign(gap)})
    return {'schema': 'a-weight-sensitivity.aggregate.v1', 'scope': 'historical_weighted_arithmetic_and_recorded_binary_counts_only',
            'input_commit': COMMIT, 'gap_direction': 'codex_minus_dsh', 'rational_encoding': 'numerator/denominator',
            'case_order': CASES, 'denominators': totals, 'formal_rows_validated': 10, 'descriptive_repeat_rows_validated': 20,
            'equal_case_weights': [F(1, 5)]*5, 'same_reported_label': same,
            'cartesian_total_contrasts_not_independent_samples': cartesian, 'formal_r1_shared_weights': formal_tv(d[1])}


def as_rational(x):
    if isinstance(x, F):
        return f'{x.numerator}/{x.denominator}'
    raise TypeError('unexpected aggregate type')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, default='.', help='local Git repository already containing the pinned commit')
    p.add_argument('--check', type=Path, help='compare against an existing aggregate instead of printing JSON')
    args = p.parse_args()
    try:
        actual = projection(args.repo)
        payload = (json.dumps(actual, default=as_rational, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('ascii')
        if args.check is not None:
            demand(args.check.read_bytes() == payload, 'aggregate bytes differ')
            print('Weighted aggregate reproduced; recorded binary counts are not checker revalidation.')
        else:
            sys.stdout.buffer.write(payload)
        return 0
    except (ValueError, KeyError, TypeError, OSError, ArithmeticError, subprocess.SubprocessError):
        print('Verification failed: pinned local input unavailable, inconsistent, or aggregate differs.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
