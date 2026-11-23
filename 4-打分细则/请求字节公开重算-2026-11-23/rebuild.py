#!/usr/bin/env python3
"""Rebuild arithmetic from the public packet ledger and declared labels only."""
import argparse
from collections import Counter
import json
from pathlib import Path

METRICS = ('dsl', 'history', 'other_values', 'raw', 'syntax', 'without_dsl')
STAGES = ('E0', 'E1', 'E2', 'E3', 'first_attempt')


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def unique(rows):
    out = dict(rows)
    need(len(out) == len(rows), 'duplicate key')
    return out


def read(path):
    def bad(_):
        raise ValueError('not a finite JSON number')
    return json.loads(path.read_bytes().decode('utf-8'), object_pairs_hook=unique, parse_constant=bad)


def number(i):
    return type(i) is int and i > 0


def identity(*parts):
    need(all(type(s) is str and s for s in parts), 'invalid data label')
    return parts


def measures(m):
    need(type(m) is dict and m.keys() == set(METRICS) and all(type(v) is int and v >= 0 for v in m.values()), 'invalid size vector')
    need(m['raw'] == sum(m[k] for k in ('dsl', 'history', 'other_values', 'syntax')), 'raw decomposition')
    need(m['dsl'] + m['without_dsl'] <= m['raw'], 'whole-member deletion bounds')
    return m


def total(rows):
    return {metric: sum(r[metric] for r in rows) for metric in METRICS}


def compare(stage_a, stage_b, left, right):
    if stage_a is None or stage_b is None:
        return None
    na, nb = len(stage_a), len(stage_b)
    n = min(na, nb)
    lp, rp = total(left[:n]), total(right[:n])
    le, re = total(left[n:na]), total(right[n:nb])
    return {'common_n': n, 'extra_a': stage_a[n:], 'extra_b': stage_b[n:], 'components': {
        k: {'a_extra': le[k], 'b_extra': re[k], 'common_ordinal_delta': rp[k] - lp[k],
            'delta': (rp[k] + re[k]) - (lp[k] + le[k])} for k in METRICS}}


def reconstruct(data):
    packets = {}
    for row in data['packets']:
        group = identity(row['ring'], row['run'])
        req = row['req']
        need(number(req) and req not in packets.get(group, {}), 'duplicate or invalid packet slot')
        packets.setdefault(group, {})[req] = measures(row['metrics'])
    runs = {}
    for row in data['runs']:
        key = identity(row['ring'], row['run'])
        need(key in packets and key not in runs, 'missing or repeated run')
        ma, aux = row['ma'], row['title']
        need(type(ma) is list and ma and type(aux) is list and all(number(i) for i in ma + aux), 'invalid role membership')
        need(ma == sorted(set(ma)) and len(set(ma + aux)) == len(ma + aux), 'non-increasing main or repeated role')
        by_slot = packets[key]
        need(set(ma + aux) == set(by_slot), 'role sets do not partition packet slots')
        ends = row['ends']
        need(type(ends) is dict and ends.keys() <= set(STAGES), 'unexpected endpoint label')
        seq, cum = {}, {}
        for stage in STAGES:
            end = ends.get(stage)
            if end is None:
                seq[stage] = cum[stage] = None
                continue
            need(number(end) and end in ma, 'stage not anchored to a main request')
            seq[stage] = ma[:ma.index(end) + 1]
            cum[stage] = total([by_slot[i] for i in seq[stage]])
        known_ends = [ends[s] for s in STAGES[:4] if ends.get(s) is not None]
        need(known_ends == sorted(known_ends), 'out of order selected endpoints')
        need(ends.get('E0') in (None, ma[0]) and ends.get('E3') in (None, ma[-1]), 'invalid first or last label')
        runs[key] = {'ma': ma, 'title': aux, 'seq': seq, 'cum': cum, 'by_slot': by_slot}
    need(packets.keys() == runs.keys(), 'run declarations are not exhaustive')
    pairs = {}
    undirected = set()
    for row in data['pairs']:
        ring, a, b = identity(row['ring'], row['a'], row['b'])
        lu, ru = (ring, a), (ring, b)
        key = ring, a, b
        ukey = ring, *sorted((a, b))
        need(lu in runs and ru in runs and a != b and ukey not in undirected, 'invalid or duplicate paired run')
        undirected.add(ukey)
        l, r = runs[lu], runs[ru]
        pairs[key] = {s: compare(l['seq'][s], r['seq'][s], [l['by_slot'][i] for i in l['ma']],
                                 [r['by_slot'][i] for i in r['ma']]) for s in STAGES[:4]}
    return runs, pairs


def projections(runs, pairs):
    rows = {stage: {m: Counter() for m in METRICS} for stage in STAGES[:4]}
    endpoint_absent = {stage: 0 for stage in STAGES[:4]}
    known = sum(arm is not None for run in runs.values() for arm in run['cum'].values())
    for timeline in pairs.values():
        for stage, v in timeline.items():
            endpoint_absent[stage] += int(v is None)
            for m in METRICS:
                x = v['components'][m]['delta'] if v is not None else None
                rows[stage][m]['unknown' if x is None else ('positive' if x > 0 else 'negative' if x < 0 else 'zero')] += 1
    return {'runs': len(runs), 'total_slots': sum(len(v['by_slot']) for v in runs.values()),
            'main_slots': sum(len(v['ma']) for v in runs.values()), 'aux_slots': sum(len(v['title']) for v in runs.values()),
            'run_endpoints_known': known, 'run_endpoints_unknown': len(runs) * len(STAGES) - known,
            'pairs': len(pairs), 'pair_endpoint_unknown': endpoint_absent, 'directions': rows}


def same_value(a, b):
    if type(a) is not type(b):
        return False
    if type(a) is list:
        return len(a) == len(b) and all(same_value(x,y) for x,y in zip(a,b))
    if type(a) is dict:
        return a.keys() == b.keys() and all(same_value(x,b[k]) for k,x in a.items())
    return a == b


def reconciliation(data, runs, pairs):
    fails = Counter()
    checks = Counter()
    def check(kind, a, b):
        checks[kind] += 1
        fails[kind] += int(not same_value(a, b))

    def fields(typ, candidate, expected_keys):
        correct = type(candidate) is dict
        check(typ, True, correct and candidate.keys() == set(expected_keys))
        return candidate if correct else {}

    for r in data['runs']:
        row = runs[r['ring'], r['run']]
        ref = {str(i): v for i, v in row['by_slot'].items()}
        ms = fields('run_ms_slot_set', r.get('ms'), ref)
        for i, v in ref.items():
            rec = fields('run_ms_vector_shape', ms.get(i), METRICS)
            for m, n in v.items():
                check('packet_number_vs_run_ms', n, rec.get(m))
        cum = fields('run_endpoint_stage_keys', r.get('cum'), STAGES)
        for stage, derived in row['cum'].items():
            recorded = cum.get(stage)
            if derived is None or recorded is None:
                check('run_endpoint_null', derived is None, recorded is None)
            else:
                record = fields('run_cumulative_vector_shape', recorded, METRICS)
                for m, val in derived.items():
                    check('run_cumulative_cell', val, record.get(m))
    for row in data['pairs']:
        base = pairs[row['ring'], row['a'], row['b']]
        points = fields('pair_stage_keys', row.get('points'), STAGES[:4])
        for stage, expected in base.items():
            got = points.get(stage)
            if expected is None or got is None:
                check('pair_endpoint_null', expected is None, got is None)
                continue
            got = fields('pair_stage_shape', got, expected)
            for k in ('common_n', 'extra_a', 'extra_b'):
                check('pair_alignment', expected[k], got.get(k))
            components = fields('pair_component_set', got.get('components'), METRICS)
            for m in METRICS:
                target = expected['components'][m]
                rec = fields('pair_component_shape', components.get(m), target)
                for k,v in target.items():
                    check('pair_component_cell', v, rec.get(k))
    return dict(checks), dict(fails)


def strict_dumps(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path)
    parser.add_argument('--arithmetic-only', action='store_true', help='do not consume published sums or differences')
    args = parser.parse_args()
    try:
        d = read(args.evidence)
        runs,pairs = reconstruct(d)
        result = projections(runs, pairs)
        expected = {'runs':18, 'total_slots':65, 'main_slots':52, 'aux_slots':13, 'pairs':14}
        need(all(result[k] == v for k,v in expected.items()), 'not the declared 18-run, 65-packet, 14-comparison ledger')
        if not args.arithmetic_only:
            checked, failed = reconciliation(d, runs, pairs)
            result.update(cells_checked=checked, cells_different=failed)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        parser.exit(2, f'Cannot reconstruct ledger: {exc}\n')
    print(strict_dumps(result), end='')
    if not args.arithmetic_only and any(failed.values()):
        raise SystemExit(2)


if __name__ == '__main__':
    main()
