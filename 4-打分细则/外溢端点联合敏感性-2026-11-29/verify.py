#!/usr/bin/env python3
"""Recompute the conditional bands from the pinned public ledger, without raw captures."""
from collections import Counter
from fractions import Fraction as F
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path

Z = F(0)
L, H = F('0.90'), F('1.10')
GAMMAS = tuple(F(x) for x in ('1', '1.02', '1.05', '1.10'))
LEDGER = Path(__file__).resolve().parents[1] / '端点支持与请求字节-2026-11-23' / 'evidence.json'
SHA = '2161c08a211426f6aa4c2fbb6262965b793cf5d30ea35da8462c5d6020fa55ef'
LABELS = ('low', 'middle', 'high', 'unknown')


def require(ok, msg):
    if not ok:
        raise ValueError(msg)


def pinned():
    raw = LEDGER.read_bytes()
    require(sha256(raw).hexdigest() == SHA, 'not the pinned earlier ledger')
    return json.loads(raw)


def scope(doc):
    lengths = {(x['ring'], x['run'], x['req']): x['metrics']['raw'] for x in doc['packets']}
    require(len(lengths) == len(doc['packets']) == 65, 'packet roster')
    arms = {}
    for run in doc['runs']:
        ring, name, slots = run['ring'], run['run'], run['ma']
        stop = run['ends']['E2']
        if stop is None:
            continue
        require(slots == sorted(set(slots)) and stop in slots, 'ordered E2 main prefix')
        past = sum(lengths[ring, name, i] for i in slots if i < stop)
        exact = past + lengths[ring, name, stop]
        require(0 < past < exact, 'unknown prefix cannot use the lower bound')
        arms[ring, name] = (exact, past, min(slots), max(slots))
    edges = {}
    for i, pair in enumerate(doc['pairs'], 1):
        left, right = (pair['ring'], pair['a']), (pair['ring'], pair['b'])
        a, pa, first_a, last_a = arms[left]
        b, pb, first_b, last_b = arms[right]
        require(last_a < first_b or last_b < first_a, 'no separate main-packet number ranges')
        edges[i] = (left, right, a, b, pa, pb, -1 if last_a < first_b else 1)
    require(len(edges) == 14, 'edge roster')
    for combo in combinations(edges, 6):
        require(len({run for x in combo for run in edges[x][:2]}) < 12, 'larger disjoint panel found')
    panels = [combo for combo in combinations(edges, 5) if len({run for x in combo for run in edges[x][:2]}) == 10]
    require(len(panels) == 48, 'disjoint five-edge roster')
    return edges, panels


def ratios(edges, panel, masked, side):
    rows = []
    for i in panel:
        _, _, a, b, pa, pb, s = edges[i]
        hide_a = i in masked and 'A' in side
        hide_b = i in masked and 'B' in side
        lo = Z if hide_a else F(pb + 1 if hide_b else b, a)
        hi = None if hide_b else F(b, pa + 1 if hide_a else a)
        rows.append((lo, hi, s))
    return rows


def median_band(rows):
    lo = sorted(low for low, _ in rows)[2]
    hi = sorted((high for _, high in rows), key=lambda v: (v is None, Z if v is None else v))[2]
    if lo > H:
        return 'high'
    if hi is not None and hi < L:
        return 'low'
    if hi is not None and L <= lo and hi <= H:
        return 'middle'
    return 'unknown'


def independent(rows, gamma):
    return median_band([(lo / gamma, None if hi is None else hi * gamma) for lo, hi, _ in rows])


def at(rows, f):
    return median_band([(lo * f ** s, None if hi is None else hi * f ** s) for lo, hi, s in rows])


def shared(rows, gamma):
    floor = 1 / gamma
    cuts = {floor, gamma}
    for lo, hi, s in rows:
        for v in (lo, hi):
            if not v:
                continue
            for bound in (L, H):
                cut = (bound / v) ** s
                if floor <= cut <= gamma:
                    cuts.add(cut)
    ordered = sorted(cuts)
    probes = ordered + [(a + b) / 2 for a, b in zip(ordered, ordered[1:])]
    bands = {at(rows, f) for f in probes}
    return bands.pop() if len(bands) == 1 else 'unknown'


def verify_controls():
    gamma = F('1.05')
    points = [(H, H, s) for s in (-1, -1, 1, 1)] + [(F('1.20'), F('1.20'), -1)]
    require((at(points, 1 / gamma), at(points, F(1)), at(points, gamma), shared(points, gamma)) == ('high', 'middle', 'high', 'unknown'), 'interior equality')
    shifted = [(F('1.11'), F('1.11'), s) for s in (-1, -1, 1, 1)] + points[-1:]
    require((independent(shifted, gamma), shared(shifted, gamma)) == ('unknown', 'high'), 'common factor distinction')
    base = [(F(x), F(x), s) for x, s in [('1.22', -1), ('1.22', 1), ('1.105', -1), ('0.8', -1)]]
    def case(p, s=1):
        return base + [(F(p + 1, 1000), None, s)]
    require((shared(case(1095), gamma), shared(case(1094), gamma), at(case(1094), F(221, 220))) == ('high', 'unknown', 'unknown'), 'one-byte strict margin')
    reverse = base[:3] + [(F('0.8'), F('0.8'), 1)] + case(1095, -1)[-1:]
    require(shared(reverse, gamma) == 'unknown', 'balanced total does not identify signs')
    require(median_band([(L, H)] * 5) == 'middle', 'closed middle')


def recount(doc):
    edges, panels = scope(doc)
    table = []
    for g in GAMMAS:
        for size, side in ((0, ''), *((k, s) for k in (1, 2) for s in ('A', 'B', 'AB'))):
            band_counts = {independent: Counter(), shared: Counter()}
            n = model_diff = 0
            for panel in panels:
                complete = ratios(edges, panel, (), side)
                for mask in combinations(panel, size):
                    n += 1
                    observed = ratios(edges, panel, mask, side)
                    mask_only = independent(observed, F(1))
                    found = []
                    for model in (independent, shared):
                        only_order, joint = model(complete, g), model(observed, g)
                        require(joint == 'unknown' or joint == mask_only == only_order, 'nonmonotone result')
                        cols = band_counts[model]
                        cols[joint] += 1
                        if joint == 'unknown' and mask_only == only_order != 'unknown':
                            cols['both_known_lost'] += 1
                        found.append(joint)
                    require(found[0] == 'unknown' or found[1] == found[0], 'shared model outside independent bounds')
                    model_diff += found[0] != found[1]
            table.append({'g': str(g), 'mask_size': size, 'side': side, 'cases': n, 'model_disagreements': model_diff,
                          **{model.__name__: {k: band_counts[model][k] for k in (*LABELS, 'both_known_lost')} for model in band_counts}})
    witness = (2, 5, 9, 11, 14)
    require(witness in panels, 'witness absent')
    case = ratios(edges, witness, (2,), 'B')
    g = F('1.05')
    complete = ratios(edges, witness, (), 'B')
    example = [independent(case, 1), independent(complete, g), independent(case, g), shared(case, g), at(case, F(1)), at(case, F(729730, 701701))]
    require(example == ['high', 'high', 'unknown', 'unknown', 'high', 'unknown'], 'witness bands')
    return {'panels': len(panels), 'edge_n': len(edges), 'table': table, 'witness': {'edges': witness, 'bands': example}}


if __name__ == '__main__':
    verify_controls()
    print(json.dumps(recount(pinned()), ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False))
