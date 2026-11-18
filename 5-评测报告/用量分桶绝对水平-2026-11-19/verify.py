#!/usr/bin/env python3
"""Recompute the necessary subset test on fixed public reported counts."""
import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import stat
import sys

REF = '5-评测报告/首包一致与用量漂移-2026-11-19/evidence.json'
REF_SHA = '0710ad1c58838aafaed9931eee91762b616657e02dbcb884c66409f121f57366'
BASE = '3-表现现场/r20261103-input-bytes/runs'
BLOCKS = tuple(f'b{i:02d}' for i in range(1,7))
ARMS = ('inline', 'bounded')
FIELDS = ('input_tokens','cache_creation_input_tokens','cache_read_input_tokens')
REQ = ('01-request.json','02-request.json')
EVENT = (('message_start','message'),('message_delta','event'))


def require(condition, label):
    if not condition:
        raise ValueError(label)


def unique(pairs):
    out = {}
    for key, val in pairs:
        require(key not in out, 'duplicate JSON member')
        out[key] = val
    return out


def constant(_):
    raise ValueError('non-finite JSON number')


def parse(payload):
    return json.loads(payload.decode('utf-8','strict'), object_pairs_hook=unique, parse_constant=constant)


def read(root, name, signature, size=None):
    path = root / name
    require(path == path.resolve(strict=True) and stat.S_ISREG(path.lstat().st_mode), 'redirected or nonregular pinned path')
    n = path.stat().st_size
    require(0 < n <= 32768 and (size is None or type(size) is int and n == size), 'pinned size')
    with path.open('rb') as f:
        raw = f.read(n+1)
    require(len(raw) == n and sha256(raw).hexdigest() == signature, 'pinned digest')
    return parse(raw)


def load(root):
    ref = read(root, REF, REF_SHA)
    require(ref['schema'] == 'confirm-usage-public-v1' and tuple(ref['result']['fields'][:3]) == FIELDS, 'reference schema')
    slots = [f'{b}-{a}' for b in BLOCKS for a in ARMS]
    source = ref['fixed_sources'][1:]
    require([s['scope'] for s in source] == slots, 'source coverage or order')
    records = {}
    for scope, s in zip(slots,source):
        dest = f'{BASE}/confirm-{scope}/reported-usage.json'
        require(s['path'] == dest, 'wrong source path')
        records[scope] = (s['scope'],read(root,dest,s['sha256'],s['bytes']))
    return records, ref['result']['pairs']


def project(scope, record):
    incoming, rows = record
    if scope != incoming or type(rows) is not list or len(rows) != 2 or any(type(r) is not dict for r in rows) or tuple(r.get('request') for r in rows) != REQ:
        return (None,None)
    out = []
    for row in rows:
        e = row.get('native_usage_events')
        if (type(e) is not list or len(e) != 2 or any(type(x) is not dict or type(x.get('usage')) is not dict for x in e)
                or tuple((x.get('event_type'),x.get('location')) for x in e) != EVENT):
            out.append(None)
            continue
        vecs = [tuple(p['usage'].get(f) for f in FIELDS) for p in e]
        out.append(vecs[0] if vecs[0] == vecs[1] and all(type(n) is int and n >= 0 for v in vecs for n in v) else None)
    return tuple(out)


def sign(v):
    if v is None:
        return None
    return int(v[2]>v[0])-int(v[2]<v[0])


def compute(records, previous):
    require(tuple(p['pair'] for p in previous) == BLOCKS, 'reference order')
    states = {k:project(k,v) for k,v in records.items()}
    results = []
    for j in range(2):
        classes = {a:[0,0,0,0] for a in ARMS}  # greater/equal/less/unknown
        paired, differences = [0,0,0], []
        unknown = matches = 0
        for block, ref in zip(BLOCKS,previous):
            l,r = (states[f'{block}-{a}'][j] for a in ARMS)
            symbols = tuple(sign(p) for p in (l,r))
            for a,k in zip(ARMS,symbols):
                classes[a][(1,0,-1,None).index(k)] += 1
            if None in symbols:
                unknown += 1
                continue
            paired[symbols.count(1)] += 1
            d = tuple(y-x for x,y in zip(l,r))
            differences.append(d)
            matches += sum(type(y) is int and y == x for x,y in zip(d,ref['delta'][j][:3]))
        detail = None
        if len(differences) == 6 and matches == 18:
            i,w,c = zip(*differences)
            combined = tuple(sum(v) for v in differences)
            detail = {'input_width':max(i)-min(i), 'cache_read_width':max(c)-min(c), 'all_cache_write_deltas_zero':all(v==0 for v in w),
                      'conditional_sum_minmax':[min(combined),max(combined)], 'conditional_sum_width':max(combined)-min(combined)}
        results.append({'request':j+1,'per_arm_greater_equal_less_unknown':classes, 'pair_0_1_2_violations':paired,
                        'unknown_pairs':unknown, 'signed_projection_field_matches':matches,'arithmetic_if_additive':detail})
    return results


def checks():
    scope = 'b01-inline'
    def make(v):
        return [{'request':q,'native_usage_events':[{'event_type':t,'location':l,'usage':dict(zip(FIELDS,v))} for t,l in EVENT]} for q in REQ]
    fixture = make((6,0,6))
    require(sign(project(scope,(scope,fixture))[0]) == 0,'tie')
    require(project(scope,('b01-bounded',fixture)) == (None,None),'scope')
    for change in (lambda u:u.update({FIELDS[2]:None}), lambda u:u.pop(FIELDS[2]),lambda u:u.update({FIELDS[1]:False}),lambda u:u.update({FIELDS[0]:8})):
        a = deepcopy(fixture)
        change(a[0]['native_usage_events'][1]['usage'])
        require(project(scope,(scope,a)) == (None,(6,0,6)),'unavailable not zero')
    require(sign(project(scope,(scope,make((6,0,7))))[0]) == 1,'strict breach')
    require(sign(project(scope,(scope,make((6,0,5))))[0]) == -1,'below')
    try:
        parse(br'{"input_tokens":0,"\u0069nput_tokens":1}')
    except ValueError:
        pass
    else:
        raise ValueError('duplicate accepted')
    return 9


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path.cwd())
    p.add_argument('--self-test',action='store_true')
    args = p.parse_args()
    try:
        projected = compute(*load(args.root.resolve(strict=True)))
        require([r['signed_projection_field_matches'] for r in projected]==[18,18], 'fixed values incomplete or different')
        summary = {'reported_levels_only':True,'definition_certified':False,'requests':projected}
        if args.self_test:
            summary['synthetic_controls'] = checks()
        print(json.dumps(summary,sort_keys=True,indent=2))
    except (OSError,ValueError,TypeError,IndexError,KeyError):
        print('Unable to validate fixed public source or result.',file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
