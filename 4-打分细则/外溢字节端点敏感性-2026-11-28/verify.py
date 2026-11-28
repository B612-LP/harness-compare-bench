#!/usr/bin/env python3
"""Recount a pinned public byte ledger; do not read or run any product artifacts."""
import hashlib
import json
from collections import Counter, defaultdict
from fractions import Fraction
from itertools import accumulate
from pathlib import Path
from statistics import median


LEDGER = Path(__file__).resolve().parents[1] / '端点支持与请求字节-2026-11-23' / 'evidence.json'
LEDGER_SHA = '2161c08a211426f6aa4c2fbb6262965b793cf5d30ea35da8462c5d6020fa55ef'
POINTS = ('E1', 'E2', 'E3')
LOW, HIGH = Fraction(9, 10), Fraction(11, 10)


def require(valid, message):
    if not valid:
        raise ValueError(message)


def positive_integer(value):
    return type(value) is int and value > 0


def read_input(path):
    data = path.read_bytes()
    require(hashlib.sha256(data).hexdigest() == LEDGER_SHA, 'unexpected public ledger SHA-256')
    return json.loads(data)


def projection(ledger):
    available = {}
    for row in ledger['packets']:
        key = (row['ring'], row['run'], row['req'])
        size = row['metrics']['raw']
        require(positive_integer(row['req']) and positive_integer(size) and key not in available,
                'invalid or duplicate packet coordinate')
        available[key] = size
    runs, number_of_titles = {}, 0
    for row in ledger['runs']:
        key = (row['ring'], row['run'])
        require(key not in runs, 'duplicate run')
        main, title = row['ma'], row['title']
        for kind in (main, title):
            require(type(kind) is list and all(map(positive_integer, kind))
                    and kind == sorted(set(kind)), 'invalid or unordered packet list')
        require(main and set(main).isdisjoint(title), 'empty main or overlapping roles')
        for n in title:
            available.pop((*key, n))
        number_of_titles += len(title)
        cumulative = dict(zip(main, accumulate(available.pop((*key, n)) for n in main)))
        coordinate = {name: row['ends'][name] for name in POINTS}
        require(coordinate['E3'] == main[-1] and type(coordinate['E3']) is int,
                'E3 is not the visible last main packet')
        results = {d['req'] for d in row['data']}
        require(results <= cumulative.keys(), 'result label outside the main task')
        require(all(n is None or positive_integer(n) and n in results for name, n in coordinate.items()
                    if name != 'E3'), 'E1/E2 not bound to a labeled main result')
        e1, e2 = coordinate['E1'], coordinate['E2']
        # A failed target read can leave E1 unbound even when a later new
        # tool result carries the fact at E2. Order only two known points.
        require(e1 is None or e2 is None or e1 <= e2, 'known E2 precedes known E1')
        runs[key] = (cumulative, coordinate)
    require(not available, 'unassigned public packet')
    edges = [((p['ring'], p['a']), (p['ring'], p['b'])) for p in ledger['pairs']]
    sides = [{edge[i] for edge in edges} for i in (0, 1)]
    require(len(edges) == len(set(edges)) and sides[0].isdisjoint(sides[1])
            and (sides[0] | sides[1]) <= runs.keys(), 'invalid pairing graph')
    return runs, edges, number_of_titles


def category(ratio):
    if ratio is None:
        return 'unknown'
    return 'below' if ratio < LOW else 'above' if ratio > HIGH else 'in_band'


def divide(numerator, denominator):
    return None if numerator is None or denominator is None else Fraction(numerator, denominator)


def end_values(run):
    sums, endpoints = run
    return {name: sums.get(endpoints[name]) for name in POINTS}


def mask_before_fact(short_run, base):
    sums, ends = short_run
    e1, e2 = ends['E1'], ends['E2']
    if e1 is None or e2 is None or e1 == e2:
        return None
    prefix = sums[max(n for n in sums if n < e2)]
    # The last surviving packet is not E2. Only the positive-byte lower bound
    # can be used if the fact subsequently arrives with the same comparator.
    return (divide(prefix, base['E3']), divide(prefix, base['E2']), None)


def maximum_disjoint_panels(edges):
    by_first_run = defaultdict(list)
    for i, (a, b) in enumerate(edges):
        by_first_run[a].append((i, b))
    options = tuple(by_first_run.values())
    best = [()]

    def visit(pos, used, panel):
        if len(panel) + len(options) - pos < len(best[0]):
            return
        if pos == len(options):
            if len(panel) > len(best[0]):
                best.clear()
            best.append(tuple(sorted(panel)))
            return
        for edge_index, b in options[pos]:
            if b not in used:
                visit(pos + 1, used | {b}, panel + (edge_index,))
        visit(pos + 1, used, panel)

    visit(0, set(), ())
    return sorted(set(best))


def fixed_median(values):
    return median(values) if values and all(x is not None for x in values) else None


def recount(ledger):
    runs, edges, number_of_titles = projection(ledger)
    case_rows, by_group, masks = [], defaultdict(list), []
    for i, (a, b) in enumerate(edges):
        a_bytes, b_bytes = end_values(runs[a]), end_values(runs[b])
        ratios = {point: divide(b_bytes[point], a_bytes[point]) for point in POINTS}
        by_group[a[0]].append(i)
        case_rows.append((a_bytes, b_bytes, ratios))
        masks.append(mask_before_fact(runs[b], a_bytes))

    def show_matrix(indices):
        return {point: dict(Counter(category(case_rows[i][2][point]) for i in indices)) for point in POINTS}

    def show_mask(indices):
        selected = [masks[i] for i in indices if masks[i] is not None]
        return {'masked_pairs': len(selected),
                'wrong_last_request_ratio_below_0.90': sum(category(n) == 'below' for n, _, _ in selected),
                'fact_ratio_unknown': sum(proper is None for _, _, proper in selected),
                'prefix_rules_out_below_0.90_if_fact_later_arrives': sum(
                    lower is not None and lower >= LOW for _, lower, _ in selected)}

    def show_panels(edge_indices):
        panels = maximum_disjoint_panels([edges[i] for i in edge_indices])
        panel_medians = {point: [fixed_median([case_rows[edge_indices[i]][2][point] for i in panel])
                                 for panel in panels] for point in POINTS}
        return {'panels': len(panels), 'edges_per_panel': len(panels[0]),
                'median_categories': {p: dict(Counter(map(category, rr))) for p, rr in panel_medians.items()},
                'median_ranges': {p: None if None in rr else [str(min(rr)), str(max(rr))]
                                  for p, rr in panel_medians.items()}}

    paired_runs = {run for edge in edges for run in edge}
    report = {
        'public_input_sha256': LEDGER_SHA,
        'counts': {'runs': len(runs), 'paired_runs': len(paired_runs), 'edges': len(edges),
                   'main': sum(len(sums) for sums, _ in runs.values()), 'title': number_of_titles},
        'edges_by_point': show_matrix(range(len(edges))),
        'largest_vertex_disjoint_panels': show_panels(list(range(len(edges)))),
        'group_breakdown': {g: {'edges_by_point': show_matrix(ii), 'panels': show_panels(ii),
                                'suffix_mask': show_mask(ii)} for g, ii in sorted(by_group.items())},
        'suffix_mask': show_mask(range(len(edges))),
        'edge_rows': [{'edge': i + 1, 'group': edges[i][0][0], 'A_bytes': a, 'B_bytes': b,
                       'B_over_A': {e: None if x is None else str(x) for e, x in rr.items()}}
                      for i, (a, b, rr) in enumerate(case_rows)],
    }
    return report


def main():
    result = recount(read_input(LEDGER))
    require(result['counts'] == {'runs': 18, 'paired_runs': 14, 'edges': 14, 'main': 52, 'title': 13},
            'pinned input roster mismatch')
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
