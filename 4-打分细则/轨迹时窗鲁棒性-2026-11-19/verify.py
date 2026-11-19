#!/usr/bin/env python3
"""Prospective exact robustness of a disclosed timestamp candidate set, not trace custody."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import subprocess

BASE = 'dd5a12f651527923a412f6727d5d2f9c22457026'
PATH = '3-表现现场/r1109-mech-n3/observe/trace-accounting-summary.json'
OID = 'ece404923326ddbbfa5fc92e2d1063fb0da0a6e7'
SHA = 'b29227d1273c984b8012c096a4eca25101203646dd02729d2cccaa4ec80e4b48'
SLOT = re.compile(r'codex__([a-z0-9-]+)__r([1-3])', re.ASCII)
START = re.compile(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d', re.ASCII)
NAME = re.compile(r'rollout-(\d{4}-\d\d-\d\dT\d\d-\d\d-\d\d)-[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}\.jsonl', re.ASCII)


def require(ok, label):
    if not ok:
        raise ValueError(label)


def unique(pairs):
    output = dict(pairs)
    require(len(output) == len(pairs), 'DUP_KEY')
    return output


def invalid_number(_):
    raise ValueError('BAD_JSON_NUMBER')


def local_blob(root):
    env = dict(os.environ, GIT_NO_REPLACE_OBJECTS='1', GIT_NO_LAZY_FETCH='1', GIT_ALLOW_PROTOCOL='')
    def call(*args):
        return subprocess.run(['git', '-C', str(root), *args], env=env, capture_output=True,
                              check=True, timeout=8).stdout
    require(call('rev-parse', '--verify', BASE+':'+PATH).decode('ascii').strip() == OID, 'SOURCE_PATH_OID')
    b = call('cat-file', 'blob', OID)
    require(len(b) <= 256_000 and hashlib.sha256(b).hexdigest() == SHA and
            hashlib.sha1(f'blob {len(b)}\0'.encode('ascii') + b).hexdigest() == OID, 'SOURCE_BLOB')
    return json.loads(b, object_pairs_hook=unique, parse_constant=invalid_number)


def timestamp(text):
    require(type(text) is str and START.fullmatch(text) and not text.endswith('-00:00'), 'START_SHAPE')
    require(0 <= int(text[-5:-3]) <= 23 and 0 <= int(text[-2:]) <= 59, 'START_OFFSET')
    return datetime.fromisoformat(text)


def clock(name, tz):
    m = NAME.fullmatch(name) if type(name) is str else None
    require(m is not None, 'NAME_SHAPE')
    return datetime.strptime(m[1], '%Y-%m-%dT%H-%M-%S').replace(tzinfo=tz)


def difference(a, b):
    d = a - b
    require(d.microseconds == 0, 'WHOLE_SECONDS')
    return d.days * 86400 + d.seconds


def profiles(source):
    docs = source['codex']['incidents']
    require(type(docs) is list and len(docs) == 15, 'SLOT_COUNT')
    ids, starts, links = [], [], []
    for o in docs:
        ident = SLOT.fullmatch(o['slot'])
        require(ident is not None, 'SLOT_SHAPE')
        ids.append(ident.groups())
        starts.append(timestamp(o['started_at']))
        links.append((o['true_rollout'], o['neighbor_rollouts_moved']))
    cases = {c for c, _ in ids}
    require(len(cases) == 5 and Counter(ids) == Counter((c, i) for c in cases for i in ('1','2','3')), 'SLOT_GRID')
    zs = {s.utcoffset() for s in starts}
    require(len(zs) == 1 and None not in zs, 'START_ZONE')
    z = timezone(next(iter(zs)))
    refs = {n: clock(n, z) for n, _ in links}
    require(len(refs) == 15, 'DUP_REFERENCE')
    own, pooled = [], []
    for start, (ref, others) in zip(starts, links):
        require(type(others) is list and all(type(n) is str and n in refs and n != ref for n in others)
                and len(others) == len(set(others)), 'NEIGHBOR_SCOPE')
        r = difference(refs[ref], start)
        own.append((r, tuple(difference(refs[o], start) for o in others)))
        pooled.append((r, tuple(difference(v, start) for n, v in refs.items() if n != ref)))
    require(sum(len(n) for _, n in own) == 11 and sum(len(n) for _, n in pooled) == 210, 'EDGE_COUNTS')
    return own, pooled


def limits(rows):
    ref_far = max(abs(ref) for ref, _ in rows)
    pairs = [(ref, n) for ref, ns in rows for n in ns]
    if not pairs:
        return ref_far, None, None, None
    other_near = min(abs(n) for _, n in pairs)
    strict = (other_near - ref_far - 1) // 2
    weak = min((n*n-ref*ref-1)//(2*abs(n-ref)) if n != ref else -1 for ref, n in pairs)
    return ref_far, other_near, strict, weak


def bounds(rows, err):
    require(type(err) is int and err >= 0, 'ERR_DOMAIN')
    r0, n0, strong, weak = limits(rows)
    lower = r0 + err
    return {'strong': [lower, None if n0 is None else n0-err-1] if strong is None or err <= strong else None,
            'weak': [lower, None] if weak is None or err <= weak else None}


def failure_counts(rows, err):
    rmin = max(abs(r) for r, _ in rows) + err
    count = Counter()
    for ref, neighbors in rows:
        has_other = tie = wrong = omit_at_smaller = False
        for e in range(-err, err+1):
            d = abs(ref-e)
            other_min = min((abs(n-e) for n in neighbors), default=None)
            omit_at_smaller |= d > rmin-1
            if other_min is not None:
                has_other |= other_min <= rmin
                tie |= other_min == d
                wrong |= other_min < d
        count.update({'other_admitted_at_min_full_recall': has_other,
                      'nearest_tie_at_min_full_recall': tie,
                      'nearest_wrong_at_min_full_recall': wrong,
                      'reference_outside_at_one_smaller': omit_at_smaller})
    return rmin, dict(count)


def summary(rows):
    r0, n0, a, b = limits(rows)
    require(a is not None and b is not None and -1 <= a <= b <= 10_000, 'ACTUAL_FINITE')
    errors = sorted({0, 10, max(a,0), a+1, max(b,0), b+1})
    out = {}
    for e in errors:
        r, count = failure_counts(rows, e)
        out[str(e)] = dict(bounds(rows, e), smallest_full_recall_radius_s=r, failure_slots=count)
    return {'n_slots': len(rows), 'n_competitor_edges': sum(len(ns) for _, ns in rows),
            'largest_reference_distance_s': r0, 'smallest_nonreference_distance_s': n0,
            'max_E_strong_s': a if a >= 0 else None, 'max_E_weak_s': b if b >= 0 else None,
            'diagnostics_at_E_s': out}


def brute_pass(rows, emax, radius):
    tests = []
    for ref, ns in rows:
        for e in range(-emax, emax+1):
            d = abs(ref-e)
            q = [abs(n-e) for n in ns if abs(n-e) <= radius]
            tests.append((d <= radius and not q, d <= radius and all(d < k for k in q)))
    return tuple(all(t[idx] for t in tests) for idx in (0,1))


def self_test():
    checks = 0
    values = range(-2,3)
    for r, n, p, q, e, rad in itertools.product(values, values, (-2,0,2), (-2,0,2), range(4), range(8)):
        test = ((r,(n,)), (p,(q,)))
        prediction = bounds(test,e)
        def contains(interval):
            return bool(interval and interval[0] <= rad and (interval[1] is None or rad <= interval[1]))
        require(tuple(contains(prediction[x]) for x in ('strong','weak')) == brute_pass(test,e,rad), 'FORMULA')
        checks += 1
    require(bounds(((0, ()),), 5) == {'strong': [5, None], 'weak': [5, None]}, 'NO_OTHER')
    require(bounds(((0, (0,)),), 0) == {'strong':None, 'weak':None}, 'SAME_CLOCK_DISTINCT')
    return checks+2


def result(root):
    a, b = profiles(local_blob(root))
    return {'source_commit': BASE, 'group': '15_disclosed_Codex_incidents', 'unit': 'integer_second',
            'local': summary(a), 'disclosed_pool_stress': summary(b), 'synthetic_checks': self_test(),
            'new_product_or_capture_runs': 0}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=Path.cwd())
    p.add_argument('--check-sibling', action='store_true')
    a = p.parse_args()
    b = json.dumps(result(a.root), sort_keys=True, indent=2) + '\n'
    if a.check_sibling:
        require((Path(__file__).parent/'evidence.json').read_bytes() == b.encode('ascii'), 'EVIDENCE')
        print('OK: exact integer radius and perturbation bounds')
    else:
        print(b,end='')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, TypeError, KeyError, OSError, subprocess.SubprocessError) as exc:
        # Scope/format errors need not disclose a value from the incident source.
        raise SystemExit('REJECT:' + type(exc).__name__)
