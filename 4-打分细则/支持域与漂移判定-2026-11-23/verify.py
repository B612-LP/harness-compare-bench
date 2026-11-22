#!/usr/bin/env python3
"""Public verifier for 支持域与漂移判定 (2026-11-23).

From support-domain.json alone:
  - four families with request key sets / SSE event-name inventories;
  - family request/response counts 23, 26, 12, 4 (sum 65 requests + 65 streams = 130);
  - files_in_support == files_total == 130;
  - negative controls: foreign key/event rejected out-of-support, DSH base keyset and
    7-event stream accepted in-support (rule v1 applied inline).
Corpus reprojection stays sealed; this checks the manifest and the rule.
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
def need(c, why):
    if not c:
        print('FAIL:', why); sys.exit(1)
need_cli = sys.argv[1] if len(sys.argv) > 1 else 'support-domain.json'
d = json.load(open(os.path.join(HERE, need_cli), encoding='utf-8'))
fams = d['families']
need(sorted(fams) == ['ring38', 'ring52', 'ring53', 'ring77'], 'four families')
counts = {k: (fams[k]['req'], fams[k]['resp']) for k in fams}
need(sorted(v[0] for v in counts.values()) == [4, 12, 23, 26], 'counts 23/26/12/4')
need(all(v[0] == v[1] for v in counts.values()), 'req==resp per family')
need(sum(v[0] for v in counts.values()) == 65, '65 requests')
need(d['files_in_support'] == d['files_total'] == 130, '130/130 in support')
inv = d['inventories']
need(sorted(inv) == ['codex', 'dsh'], 'two wires')
need(len(inv['dsh']['request_key_sets']) == 2 and len(inv['codex']['request_key_sets']) == 1,
     'DSH 2 key sets / Codex 1')
need(len(inv['dsh']['event_names']) == 7 and len(inv['codex']['event_names']) == 13,
     '7 / 13 event names')
keysets = {frozenset(ks) for ks in inv['dsh']['request_key_sets']}
need(len(keysets) == 2, 'DSH key sets distinct')
def classify_request(keys):
    return 'in_support' if frozenset(keys) in keysets else 'unknown_out_of_support'
nc = d['negative_controls']
need(nc['foreign_key'] == 'unknown_out_of_support' and nc['foreign_event'] == 'unknown_out_of_support'
     and nc['dsh_known_stream'] == 'in_support' and nc['dsh_base_keyset'] == 'in_support',
     'recorded negative verdicts')
dsh_events = set(inv['dsh']['event_names'])
def classify_stream(events):
    return 'in_support' if set(events) <= dsh_events else 'unknown_out_of_support'
need(classify_stream(['content_block_start', 'content_block_nan']) == 'unknown_out_of_support',
     'synthetic foreign event rejected by rule')
base8 = min(keysets, key=len)
need(classify_request(sorted(base8)) == 'in_support', 'base keyset in')
need(classify_request(sorted(base8) + ['mystery_key']) == 'unknown_out_of_support',
     'synthetic foreign key rejected by rule')
print('SUPPORT-DOMAIN OK (4 families, 130/130, rule v1 negatives verified)')
