#!/usr/bin/env python3
"""Exact arithmetic on one pinned, already labeled public packet ledger."""
from collections import Counter
from fractions import Fraction
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path
from statistics import median


LEDGER = Path(__file__).resolve().parents[1] / '端点支持与请求字节-2026-11-23' / 'evidence.json'
PIN = '2161c08a211426f6aa4c2fbb6262965b793cf5d30ea35da8462c5d6020fa55ef'
LOW, HIGH = Fraction(9, 10), Fraction(11, 10)
BANDS = ('low', 'middle', 'high', 'unidentified')


def need(valid, reason):
    if not valid:
        raise ValueError(reason)


def packet_prefixes(doc):
    def positive_int(x):
        return type(x) is int and x > 0

    sizes = {}
    for p in doc['packets']:
        key, n = (p['ring'], p['run'], p['req']), p['metrics']['raw']
        need(key not in sizes and positive_int(key[-1]) and positive_int(n), 'invalid packet')
        sizes[key] = n
    edges = [((p['ring'], p['a']), (p['ring'], p['b'])) for p in doc['pairs']]
    universe = {v for edge in edges for v in edge}
    need(len(universe) == len(edges) == len(set(edges)) == 14, 'unexpected paired roster')
    runs = {}
    for r in doc['runs']:
        key = (r['ring'], r['run'])
        if key not in universe:
            continue
        main, title, e2 = r['ma'], r['title'], r['ends']['E2']
        need(key not in runs and all(map(positive_int, main + title + [e2]))
             and main == sorted(set(main)) and set(main).isdisjoint(title)
             and e2 in main[1:] and e2 in {result['req'] for result in r['data']},
             'expected a labeled E2 after a nonempty main prefix')
        prefix = sum(sizes[(*key, seq)] for seq in main if seq < e2)
        runs[key] = (prefix, prefix + sizes[(*key, e2)])
    need(runs.keys() == universe, 'unmatched run')
    return edges, runs


def panels(edges):
    def disjoint(ids):
        return len({v for i in ids for v in edges[i]}) == 2 * len(ids)

    groups = list(filter(disjoint, combinations(range(len(edges)), 5)))
    need(len(groups) == 48 and not any(map(disjoint, combinations(range(len(edges)), 6))),
         'unexpected disjoint maximum')
    return groups


def pair_bounds(a, b):
    # Bounds on cumulative bytes conditional on the missing fact eventually arriving.
    # None means no finite upper bound, not a measured byte value.
    a_lo, a_hi = a
    b_lo, b_hi = b
    return Fraction(0) if a_hi is None else Fraction(b_lo, a_hi), (
        None if b_hi is None else Fraction(b_hi, a_lo))


def five_bounds(ratios):
    need(len(ratios) == 5, 'expected five fixed pairs')
    highs = sorted(hi for _, hi in ratios if hi is not None)
    return sorted(lo for lo, _ in ratios)[2], highs[2] if len(highs) >= 3 else None


def band(lo, hi):
    if hi is not None and hi < LOW:
        return 'low'
    if lo > HIGH:
        return 'high'
    if lo >= LOW and hi is not None and hi <= HIGH:
        return 'middle'
    return 'unidentified'


def counterexamples():
    need(band(LOW, LOW) == band(HIGH, HIGH) == 'middle', 'threshold inclusivity')
    complete = [(x, x) for x in [Fraction(4, 5), Fraction(1), Fraction(6, 5)]]
    box = five_bounds(complete + [pair_bounds((100, 100), (101, None))] * 2)
    marginal = five_bounds(complete + [pair_bounds((100, 100), (101, 119))] * 2)
    joint = [median([x for x, _ in complete] + [Fraction(b1, 100), Fraction(b2, 100)])
             for b1 in range(101, 120) for b2 in range(101, 120) if b1 + b2 <= 220]
    need(len(joint) == 190 and (min(joint), max(joint)) == (Fraction(101, 100), HIGH)
         and box == (Fraction(101, 100), Fraction(6, 5))
         and marginal == (Fraction(101, 100), Fraction(119, 100)), 'joint budget counterexample')
    four = complete + [(Fraction(5, 4), Fraction(5, 4))]
    correct = five_bounds(four + [pair_bounds((100, 100), (91, None))])
    misbound = five_bounds(four + [pair_bounds((100, 100), (111, None))])
    need(band(*correct) == 'unidentified' and band(*misbound) == 'high'
         and correct[0] <= 1 <= correct[1] and misbound[0] > 1, 'misbound prefix counterexample')
    return {'joint_budget': {'count': len(joint), 'box': list(map(str, box)),
                             'marginal_box': list(map(str, marginal)), 'joint': [str(min(joint)), str(max(joint))]},
            'misbound_prefix': {'valid_bounds': list(map(str, correct)),
                                'wrong_bounds': list(map(str, misbound))}}


def replay(doc):
    edges, totals = packet_prefixes(doc)
    groups = panels(edges)
    baseline = Counter()
    by_mask = {f'{n}:{side}': Counter() for n in (1, 2) for side in ('A', 'B', 'AB')}
    witness = None
    for panel in groups:
        exact = {i: Fraction(totals[edges[i][1]][1], totals[edges[i][0]][1]) for i in panel}
        truth = median(exact.values())  # Used only for replay validation and the drop-pair comparison.
        baseline[band(truth, truth)] += 1
        for n in (1, 2):
            for masked in combinations(panel, n):
                drop = median([value for i, value in exact.items() if i not in masked])
                for sides in ('A', 'B', 'AB'):
                    bounds = []
                    for i in panel:
                        arm_bounds = []
                        for side, vertex in zip('AB', edges[i]):
                            prefix, value = totals[vertex]
                            arm_bounds.append((prefix + 1, None) if i in masked and side in sides else (value, value))
                        bounds.append(pair_bounds(*arm_bounds))
                    lo, hi = five_bounds(bounds)
                    need(hi is not None and lo <= truth <= hi, 'revealed total fell outside conditional bounds')
                    conditional, dropped = band(lo, hi), band(drop, drop)
                    need(conditional in ('unidentified', band(truth, truth)), 'conditional band contradicted reveal')
                    row = by_mask[f'{n}:{sides}']
                    row[conditional] += 1
                    row['drop_wrong_band'] += dropped != band(truth, truth)
                    row['drop_high_while_unidentified'] += dropped == 'high' and conditional == 'unidentified'
                    if panel == (0, 4, 8, 10, 13) and masked == (0,) and sides == 'A':
                        witness = {'edges': [i+1 for i in panel], 'masked_A': 1, 'actual_under_mask': None,
                                   'conditional_bounds': [str(lo), str(hi)], 'drop': str(drop), 'reveal': str(truth)}
    need(witness is not None, 'fixed witness missing')
    return {'public_ledger_sha256': PIN, 'panels': len(groups), 'baseline': {k: baseline[k] for k in BANDS[:3]},
            'actual_under_any_mask': None,
            'mask_replay': {key: {k: row[k] for k in (*BANDS, 'drop_wrong_band', 'drop_high_while_unidentified')}
                            for key, row in by_mask.items()},
            'witness': witness, 'synthetic': counterexamples()}


def main():
    raw = LEDGER.read_bytes()
    need(sha256(raw).hexdigest() == PIN, 'unexpected public ledger SHA-256')
    print(json.dumps(replay(json.loads(raw)), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
