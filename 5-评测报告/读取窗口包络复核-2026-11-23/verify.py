#!/usr/bin/env python3
"""Public verifier for 读取窗口包络复核 (2026-11-23).

From evidence.json alone: 9 pairs (8 complete with positive conservative gap +
Doubao a8 negative arm unfired), gap min/max 0.0683218 / 100.6988039, old hit
direction control exactly {dsh-pos/a8, wb-pos/a2}, 17 arms, 4 counterexamples,
terminal digest binding 17/17. Wall-clock reprojection stays sealed.
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
def need(c, why):
    if not c:
        print('FAIL:', why); sys.exit(1)
name = sys.argv[1] if len(sys.argv) > 1 else 'evidence.json'
d = json.load(open(os.path.join(HERE, name), encoding='utf-8'))
ps = d['pairs']
need(len(ps) == 9, '9 pairs')
gaps = [float(p['conservative_gap_seconds']) for p in ps if p['conservative_gap_seconds'] is not None]
need(len(gaps) == 8 and all(g > 0 for g in gaps), '8 positive gaps')
need(abs(min(gaps) - 0.0683218) < 1e-6 and abs(max(gaps) - 100.6988039) < 1e-6, 'gap min/max')
h = d['headline']
need(h['complete_pairs'] == 8 and h['disjoint_pairs'] == 8, '8 complete, 8 disjoint')
need(h['old_hit_direction_control_pairs'] == 2, 'control pairs 2')
ctrl = sorted(p['positive_arm'] for p in ps if p['old_hit_direction_control'])
need(ctrl == ['dsh-pos/a8', 'wb-pos/a2'], 'controls are dsh-pos/a8 and wb-pos/a2')
unfired = [p for p in ps if p['conservative_gap_seconds'] is None]
need(len(unfired) == 1 and unfired[0]['product'] == 'db', 'db a8 unfired')
need(len(d['runs']) == 17, '17 arms')
need(len(d['counterexamples']) == 4, '4 counterexamples')
need('17/17' in str(h.get('terminal_digest_binding', '')), 'terminal binding 17/17')
print('READENV-EVIDENCE OK (9 pairs, 8 disjoint gaps, 2/8 control, 17 arms)')
