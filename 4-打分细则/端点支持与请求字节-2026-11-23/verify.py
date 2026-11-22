#!/usr/bin/env python3
"""Public verifier for 端点支持与请求字节 (2026-11-23).

Recomputes, from evidence.json alone:
  - 65 packets, ring counts R52=26 R38=23 R53=12 R77=4, run count 18;
  - metric key set per packet and the identity raw == dsl+history+syntax+other_values;
  - 14 pairs: E2 cumulative raw delta positive 14/14, exactly 1 pair positive at E1
    (13 negative), E2 without_dsl positive 14/14, E2 raw range +6,551..+61,736.
No private path, no network. Exit 0 only if every check holds.
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
    pk = d['packets']
    need(len(pk) == 65, '65 packets')
    from collections import Counter
    rings = Counter(x['ring'] for x in pk)
    need(rings == Counter({'R52': 26, 'R38': 23, 'R53': 12, 'R77': 4}), 'ring counts 26/23/12/4')
    runs = {x['run'] for x in pk}
    need(len(runs) == 18, '18 runs')
    for x in pk:
        m = x['metrics']
        need(sorted(m) == ['dsl', 'history', 'other_values', 'raw', 'syntax', 'without_dsl'],
             'metric key set')
        need(m['raw'] == m['dsl'] + m['history'] + m['syntax'] + m['other_values'],
             'raw identity packet %s' % x['run'])
    pairs = d['pairs']
    need(len(pairs) == 14, '14 pairs')
    e2 = [p['points']['E2']['components']['raw']['delta'] for p in pairs]
    e1 = [p['points']['E1']['components']['raw']['delta'] for p in pairs]
    wd = [p['points']['E2']['components']['without_dsl']['delta'] for p in pairs]
    need(all(x > 0 for x in e2), 'E2 raw 14/14 positive')
    need(sum(1 for x in e1 if x > 0) == 1 and sum(1 for x in e1 if x < 0) == 13,
         'E1 exactly 1 positive / 13 negative')
    need(all(x > 0 for x in wd), 'E2 without_dsl 14/14 positive')
    need(min(e2) == 6551 and max(e2) == 61736, 'E2 raw range 6551..61736')
    v = d['verification']
    need(v.get('pkt') == 65 and v.get('body_pairs_sha') == 65 and v.get('runs') == 18
         and v.get('title_response') == 13 and v.get('response_call_id_args') == 34,
         'verification counters')
    need(d['discrepancies'] == [], 'no unresolved discrepancies')
    print('ENDPOINT-EVIDENCE OK (65 packets, 14 pairs, headline counts recomputed)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
