#!/usr/bin/env python3
"""Recount published byte aggregates only; no archive bodies or endpoint authentication."""
import json
from fractions import Fraction
from itertools import product

# E1/E2/E3 rows as (L, M, O). All are cumulative main-request body byte spans.
A1 = (51682, 19519, 55222)
A2 = (52330, 19741, 55222)
TOTALS = {
    'A1': (A1, A1, A1),
    'A2': (A2, A2, A2),
    'B1': ((36038, 4943, 55222), (42549, 9944, 82833), (42549, 9944, 82833)),
    'B2': ((35906, 4925, 55222), (43820, 9996, 82833), (51058, 16007, 110444)),
}
LO, HI = Fraction(9, 10), Fraction(11, 10)


def project(v):
    log, messages, other = v
    return {'W': log + messages + other, 'W_minus_L': messages + other, 'M': messages}


def band(p):
    return 'low' if p < LO else 'high' if p > HI else 'middle'


def main():
    ends = ('E1', 'E2', 'E3')
    deltas, ratios = {}, {}
    for a, b in product(('A1', 'A2'), ('B1', 'B2')):
        edge = a + b
        deltas[edge], ratios[edge] = {}, {}
        for end, va, vb in zip(ends, TOTALS[a], TOTALS[b]):
            pa, pb = project(va), project(vb)
            deltas[edge][end] = {'W': pb['W'] - pa['W'], **{
                k: y - x for k, x, y in zip(('L', 'M', 'O'), va, vb)
            }}
            ratios[edge][end] = {k: Fraction(pb[k], pa[k]) for k in pa}

    paired = {}
    for x, y in (('A1B1', 'A2B2'), ('A1B2', 'A2B1')):
        paired[x + '+' + y] = {}
        for end in ends:
            r, s = ratios[x][end], ratios[y][end]
            paired[x + '+' + y][end] = {k: (r[k] + s[k]) / 2 for k in r}

    def labeled(by_end):
        return {end: {k: {'ratio': str(r), 'band': band(r)} for k, r in items.items()}
                for end, items in by_end.items()}

    e2a = project(TOTALS['A1'][1])['W']
    e2b = project(TOTALS['B1'][1])['W']
    wrong_role = Fraction(e2b + 34133, e2a)
    increments = dict(zip(('L', 'M', 'O'), (y - x for x, y in zip(*TOTALS['B2'][1:]))))
    print(json.dumps({
        'byte_deltas': deltas,
        'edge_bands': {k: labeled(v) for k, v in ratios.items()},
        'two_disjoint_pairings': {k: labeled(v) for k, v in paired.items()},
        'B2_E2_to_E3': {'W': sum(increments.values()), **increments},
        'wrong_role_recount': {'B1_title_B': 34133, 'A1B1_E2_ratio': str(wrong_role),
                               'band': band(wrong_role)},
    }, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
