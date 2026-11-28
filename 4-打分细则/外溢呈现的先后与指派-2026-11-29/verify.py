#!/usr/bin/env python3
"""Recount the pinned public archive and enumerate synthetic assignment supports."""
import hashlib
import json
from collections import Counter, defaultdict
from fractions import Fraction as Q
from itertools import combinations, product
from pathlib import Path
from statistics import median

HERE = Path(__file__).resolve().parent
INPUT = HERE.parent / '端点支持与请求字节-2026-11-23' / 'evidence.json'
SHA256 = '2161c08a211426f6aa4c2fbb6262965b793cf5d30ea35da8462c5d6020fa55ef'
LOW, HIGH = Q(9, 10), Q(11, 10)


def check(ok, why):
    if not ok:
        raise ValueError(why)


def historical(data):
    bodies, views = {}, {}
    for p in data['packets']:
        key, amount = (p['ring'], p['req']), p['metrics']['raw']
        check(key not in bodies and type(amount) is int and amount > 0, 'invalid byte coordinate')
        bodies[key] = (p['run'], amount)
    for r in data['runs']:
        group, name = r['ring'], r['run']
        main, title, e2 = r['ma'], r['title'], r['ends']['E2']
        check((group, name) not in views and main and main == sorted(set(main)), 'invalid run roster')
        check(e2 is None or e2 in main and e2 in {row['req'] for row in r['data']}, 'unbound E2 label')
        owned = [(n, *bodies.pop((group, n))) for n in main + title]
        check(all(owner == name for _, owner, _ in owned), 'packet belongs to another run')
        views[group, name] = (min(main), max(main), None if e2 is None else
                              sum(size for n, _, size in owned if n in main and n <= e2))
    check(not bodies, 'unassigned packet')
    pairs = [(p['ring'], p['a'], p['b']) for p in data['pairs']]
    check(len(pairs) == len(set(pairs)) == 14, 'unexpected comparison roster')
    rows, orders = [], defaultdict(Counter)
    for group, a, b in pairs:
        a0, a1, aa = views[group, a]
        b0, b1, bb = views[group, b]
        check(a != b and (a1 < b0 or b1 < a0) and aa is not None and bb is not None,
              'expected separate main capture ranges with known E2')
        first = 'A' if a1 < b0 else 'B'
        orders[group][first] += 1
        rows.append((Q(bb, aa), first))

    def disjoint(indices):
        return len({(pairs[i][0], name) for i in indices for name in pairs[i][1:]}) == 2 * len(indices)

    panels = [p for p in combinations(range(len(pairs)), 5) if disjoint(p)]
    check(len(panels) == 48 and not any(map(disjoint, combinations(range(len(pairs)), 6))), 'wrong maximum')
    first_counts = Counter(sum(rows[i][1] == 'A' for i in panel) for panel in panels)
    sensitivity = {}
    for g in map(Q, ('1', '1.02', '1.05', '1.10')):
        counts = Counter(dict.fromkeys(('low', 'middle', 'high', 'undetermined'), 0))
        for panel in panels:
            m = median([rows[i][0] for i in panel])
            lo, hi = m / g, m * g
            k = ('low' if hi < LOW else 'high' if lo > HIGH else
                 'middle' if lo >= LOW and hi <= HIGH else 'undetermined')
            counts[k] += 1
        sensitivity[str(g)] = counts
    return {'edge_orders': orders, 'five_edge_panels_by_A_first': first_counts, 'sensitivity': sensitivity}


def signs(n):
    return list(product((-1, 1), repeat=n))


def scores(patterns, values, stat):
    return [abs(stat([s * v for s, v in zip(z, values)])) for z in patterns]


def best_tail(values):
    return Q(values.count(max(values)), len(values))


def synthetic():
    five = signs(5)
    magnitudes = (1, 2, 4, 8, 16)
    balanced = [z for z in five if abs(sum(z)) == 1]
    mirror = [(1, -1, 1, -1, 1), (-1, 1, -1, 1, -1)]
    best = lambda dist, v, stat: str(best_tail(scores(dist, v, stat)))
    constraints = {stat.__name__: Counter(best(balanced, [i * s for i, s in zip(magnitudes, w)], stat)
                                          for w in five) for stat in (median, sum)}
    weighted_four = [z[:4] for z in balanced]
    tied = best(five, [1] * 5, median)
    # Complete endpoints are visible only under the synthetic, sign-dependent condition below.
    passes = [z for z in five if len(set(z[-3:])) == 1]
    asymmetric = [z for z in five if z.count(1) == 3]
    vals = [median([a * b for a, b in zip(z, magnitudes)]) for z in asymmetric]
    return {
        'fair_pairs_two_sided_median_by_odd_n': {n: best(signs(n), range(1, n+1), median)
                                                 for n in range(1, 12, 2)},
        'fair_five_sum': best(five, magnitudes, sum), 'fair_five_tied_median': tied,
        'balanced_uniform_support': len(balanced), 'balanced_floors_across_32_orientations': constraints,
        'both_mirror_schedules_abs_tail': {s.__name__: best(mirror, magnitudes, s) for s in (median, sum)},
        'three_AB_only_signed_median_tails': {'upper': str(Q(vals.count(max(vals)), len(vals))),
                                              'lower': str(Q(vals.count(min(vals)), len(vals))),
                                              'absolute': str(best_tail([abs(v) for v in vals]))},
        'balanced_marginal_four': {'support': len(set(weighted_four)),
                                   'weighted': best(weighted_four, magnitudes[:4], median),
                                   'wrong_uniform_distinct': best(list(set(weighted_four)), magnitudes[:4], median)},
        'conditioned_on_synthetic_completion': {'kept': len(passes), 'median_tail': best(passes, magnitudes, median)},
    }


def main():
    raw = INPUT.read_bytes()
    check(hashlib.sha256(raw).hexdigest() == SHA256, 'wrong immutable public input')
    old = historical(json.loads(raw))
    new = synthetic()
    check(old['edge_orders'] == {'R38': {'A': 4}, 'R52': {'A': 4}, 'R53': {'B': 6}}, 'unexpected order')
    check(old['five_edge_panels_by_A_first'] == {3: 48}, 'unexpected panel orientation')
    check(new['fair_pairs_two_sided_median_by_odd_n'][5] == '1/4' and new['fair_five_sum'] == '1/16'
          and new['both_mirror_schedules_abs_tail'] == {'median': '1', 'sum': '1'}, 'synthetic check failed')
    print(json.dumps({'public_input_sha256': SHA256, 'historical_capture_rank': old,
                      'synthetic_assignment_only': new}, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
