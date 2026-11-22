#!/usr/bin/env python3
"""Public verifier for 自报用量与累计字节 (2026-11-23).

From evidence.json alone: scope arithmetic (52+13=65, 14 pairs, family quota
4/4/6), 784 = 14 pairs x 4 endpoints x 2 scopes x 7 fields with delta_errors 0,
E2 cumulative raw positive pairs 14 with per-family byte lists 4/4/6, and the
24-row direction table (8 rows per family, direction-string shape, unique
family x endpoint x scope). Corpus reprojection stays sealed.
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
def need(c, why):
    if not c:
        print('FAIL:', why); sys.exit(1)
name = sys.argv[1] if len(sys.argv) > 1 else 'evidence.json'
d = json.load(open(os.path.join(HERE, name), encoding='utf-8'))
sc = d['scope']
need(sc['main'] == 52 and sc['title'] == 13 and sc['main'] + sc['title'] == sc['bound_packets'] == 65,
     '52+13=65 packets')
need(sc['pairs'] == 14 and sc['families'] == {'R38': 4, 'R52': 4, 'R53': 6}, '14 pairs, 4/4/6')
h = d['headline']
need(h['deltas_compared'] == 784 and h['delta_errors'] == 0, '784 deltas, 0 errors')
need(784 == 14 * 4 * 2 * 7, '784 = 14 x4 x2 x7')
need(h['E2_cumulative_raw_positive_pairs'] == 14, 'E2 raw positive pairs 14')
fam = d['families']
need([len(fam[k]['E2_cumulative_raw_positive_bytes']) for k in ('R38', 'R52', 'R53')] == [4, 4, 6],
     'family byte lists 4/4/6')
allbytes = sorted(fam[k]['E2_cumulative_raw_positive_bytes'] for k in fam for _ in [0]) if False else \
    [b for k in fam for b in fam[k]['E2_cumulative_raw_positive_bytes']]
need(len(allbytes) == 14 and len(set(allbytes)) == 14, '14 distinct positive byte deltas')
need(all(b > 0 for b in allbytes), 'all positive')
rows = d['direction_table']
need(len(rows) == 24, '24 rows')
pat = re.compile(r'^\d+/\d+/\d+/\d+$')
seen = set()
for r in rows:
    key = (r['family'], r['endpoint'], r['scope'])
    need(key not in seen, 'unique %s' % (key,))
    seen.add(key)
    for col in ('input', 'output', 'aux', 'B', 'C', 'K'):
        need(pat.match(r[col]), 'direction shape %s %s' % (key, col))
    tail = [c for c in ('R', 'total') if c in r]
    need(len(tail) == 1, 'exactly one of R/total %s' % (key,))
    need(pat.match(r[tail[0]]), 'direction shape %s %s' % (key, tail[0]))
    need(r['endpoint'] in ('E0', 'E1', 'E2', 'E3') and r['scope'] in ('single', 'cumulative'),
         'endpoint/scope vocab')
for f in ('R38', 'R52', 'R53'):
    n = sum(1 for r in rows if r['family'] == f)
    need(n == 8, 'family %s has 8 rows' % f)
print('USAGE-EVIDENCE OK (65 packets, 784/0, 14 positive pairs, 24 rows consistent)')
