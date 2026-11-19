"""Offline range analysis on fixed public derived observations, not a gate revision."""
from collections import Counter
from hashlib import sha256
from itertools import combinations, product
from pathlib import Path
import json
import os
import subprocess
import sys

REV = 'dd5a12f651527923a412f6727d5d2f9c22457026'
SOURCES = (
    ('4-打分细则/机制序列口径v2-2026-11-16/README.md', '718903755c5ad2dce7d1226606e8ac55050a8634', 'b57d6378db81fcd35192e590fbb843374c3598f90a1b29ea1348482f3a70728b'),
    ('4-打分细则/机制序列口径v2-2026-11-16/result.json', 'bb55f9b3a4f1bfa3c49e86df5a84d697b634c403', 'c95f932719477625c473b02e1dd1ec4a7f7d5b191b6b79be22e8a4ab45507609'),
    ('4-打分细则/机制重复口径澄清-2026-11-12/README.md', '949adaa8a0f35bf609b99a9761059499c0a9f2ca', '39b5a9de5869bbedc44a2d066c58fd6d7da9054ed06580e973c65e28a03151d6'),
)
T = 100
CASES = ('bird-ca-schools-15', 'dabstep-payments-10', 'exercism-py-6', 'lcb-recent-hard-4', 'tb-cargo-plan')
S3 = {'request/context', 'request/header', 'user/message'}
I = S3 | {'system/message', 'agent/inbox/spliced'}


class Reject(ValueError):
    pass


def require(test, code):
    if not test:
        raise Reject(code)


def strict_pairs(pairs):
    out = {}
    for k, v in pairs:
        require(k not in out, 'DUPLICATE_MEMBER')
        out[k] = v
    return out


def parse(raw):
    def reject_constant(_):
        raise Reject('NONFINITE_NUMBER')
    return json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=strict_pairs, parse_constant=reject_constant)


def acquire(root):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_NO_REPLACE_OBJECTS='1', GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0', GIT_ALLOW_PROTOCOL='')
    def git(*args):
        return subprocess.run(['git', '-C', str(root), *args], env=env, check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout
    out = []
    for path, oid, wanted in SOURCES:
        require(git('rev-parse', '--verify', REV + ':' + path).strip() == oid.encode('ascii'), 'TREE_LEAF')
        raw = git('cat-file', 'blob', oid)
        require(sha256(raw).hexdigest() == wanted, 'SOURCE_DIGEST')
        out.append(raw)
    require('比 B1 严格强' in out[0].decode('utf-8'), 'HISTORICAL_WORDING')
    require('6 组已由字节子门反驳、4 组完整门不可核' in out[2].decode('utf-8'), 'HISTORICAL_BOUNDARY')
    return parse(out[1])


def spread(v):
    return max(v) - min(v)


def integers(v):
    return all(type(n) is int for n in v)


def extremal(v):
    return {'min_reps': [i for i, n in enumerate(v, 1) if n == min(v)], 'max_reps': [i for i, n in enumerate(v, 1) if n == max(v)]}


def budget_intersection(x, y, bound, budget):
    low = max(max(u, v-budget) for u, v in zip(x, y)) - bound
    high = min(v+budget for v in y)
    return low, high


def complement_witness(x, y, bound):
    require(len(x) == len(y) == 3 and integers((*x, *y, bound)), 'WITNESS_TYPES')
    require(bound >= 0 and all(0 <= u <= v for u, v in zip(x, y)), 'WITNESS_DOMAIN')
    tv = max(0, (spread(y)-bound+1)//2, max(x)-min(y)-bound)
    lo, hi = budget_intersection(x, y, bound, tv)
    require(lo <= hi, 'WITNESS_UPPER')
    z = [min(max(v, lo, u, v-tv), lo+bound, v+tv) for u, v in zip(x, y)]
    require(spread(z) <= bound and all(u <= v for u, v in zip(x, z)), 'WITNESS_CHECK')
    require(max(abs(u-v) for u, v in zip(y, z)) == tv, 'WITNESS_MINIMAL_RESIDUAL')
    prior = list(budget_intersection(x, y, bound, tv-1)) if tv else None
    require(prior is None or prior[0] > prior[1], 'WITNESS_LOWER')
    return {'budget': tv, 'band_floor': lo, 'target_i_bytes': z, 'new_complement': [v-u for u, v in zip(x, z)], 'prior_band_floor_interval': prior}


def relation(dx, dr):
    if dr == 0:
        return 'unchanged' if dx else 'all_equal'
    if dx == 0:
        return 'comp_only'
    a = abs(dx+dr)
    return 'amplifies_absolute' if a > abs(dx) else 'reduces_absolute' if a < abs(dx) else 'unchanged_absolute'


def component_account(x, y):
    require(len(x) == len(y) == 3 and integers((*x, *y)), 'ACCOUNT_TYPES')
    require(all(0 <= a <= b for a, b in zip(x, y)), 'ACCOUNT_DOMAIN')
    r = [b-a for a,b in zip(x, y)]
    pairs = []
    for a, b in combinations(range(3), 2):
        dx, dr, dy = x[b]-x[a], r[b]-r[a], y[b]-y[a]
        require(dy == dx+dr, 'PAIR_ACCOUNT')
        pairs.append({'reps': [a+1, b+1], 'dx':dx, 'dr':dr, 'dy':dy, 'relation': relation(dx, dr)})
    rx, rr, ry = spread(x), spread(r), spread(y)
    require(abs(ry-rx) <= rr and all(p['dy'] == p['dx']+p['dr'] for p in pairs), 'RANGE_BOUND')
    return {'selected': x, 'complement': r, 'whole': y, 'ranges': [rx, rr, ry], 'gates': [rx <= T, ry <= T], 'extrema': [extremal(v) for v in (x,r,y)], 'pairs': pairs}


def history(data):
    require(data['schema'] == 'mech-seq-v2-projection-v1' and data['protocol']['version'] == 'v2.1', 'VERSION')
    c, p = data['contract'], data['protocol']
    require(c['groups'] == 5 and c['slots'] == 15 and c['cases'] == list(CASES) and c['reps'] == [1,2,3] and c['arms'] == ['dsh'] and c['operator'] == 'AND' and c['byte_threshold'] == T, 'CONTRACT')
    require(set(p['s3_selected']) == S3 and set(p['partition']['I']) == I, 'PARTITION')
    require(len(data['slots']) == 15 and len(data['groups']) == 5, 'DENOMINATORS')
    slots = {}
    for s in data['slots']:
        k = (s['case'], s['rep'])
        require(k not in slots and k[0] in CASES and type(k[1]) is int and k[1] in (1,2,3), 'SLOT_BINDING')
        require(type(s['i_event_count']) is int and len(s['i_sequence']) == s['i_event_count'] and set(s['i_sequence']) <= I, 'I_SEQUENCE')
        counts = s['type_counts']
        require(type(counts) is dict and integers(counts.values()) and Counter(s['i_sequence']) == Counter({k:v for k,v in counts.items() if k in I and v}), 'I_COUNTS')
        slots[k] = s
    groups = {g['case']: g for g in data['groups']}
    require(set(groups) == set(CASES), 'GROUP_BINDING')
    answer = {}
    for case in CASES:
        g, ss = groups[case], [slots[(case, i)] for i in (1,2,3)]
        x, y = ([s[key] for s in ss] for key in ('s3_bytes', 'i_bytes'))
        row = component_account(x, y)
        seq = [s['i_sequence'] for s in ss]
        s1 = seq[0] == seq[1] == seq[2]
        b1, b2 = row['gates']
        a = all((b1,s1,b2))
        require(g['rep'] == [1,2,3] and g['arm'] == 'dsh' and g['n'] == 3, 'GROUP_HEADER')
        require(g['s3_bytes'] == x and g['i_bytes'] == y and g['i_sequence_sha256'] == [s['i_sequence_sha256'] for s in ss], 'GROUP_VECTOR')
        require(g['b1_max_minus_min'] == row['ranges'][0] and g['b2_max_minus_min'] == row['ranges'][2], 'GROUP_PROJECTION')
        require(g['b1_pass'] is b1 and g['b2_pass'] is b2 and g['s1_pass'] is s1 and g['gate_v2'] == ('pass' if a else 'fail'), 'GROUP_GATE')
        row.update(s1=s1, conjunction=a, complement_witness=complement_witness(x, y, T))
        answer[case] = row
    return answer


def examples():
    vectors = (
        ('b1_not_b2', [300,300,300], [300,300,401], [True,False]),
        ('b2_not_b1', [300,300,401], [401,401,300], [False,True]),
        ('boundary', [300,300,300], [300,300,400], [True,True]),
        ('shifted_extreme', [400,500,450], [300,301,403], [True,False]),
    )
    result = {}
    for name, x, r, expected in vectors:
        require(all(z > 0 for z in [*x,*r]), 'SYN_POSITIVE')
        v = component_account(x, [u+v for u,v in zip(x,r)])
        require(v['gates'] == expected, 'SYN_GATES')
        v['ordered_type_lengths'] = [[1,1,u-2,1,w-1] for u,w in zip(x,r)]
        require(all(all(n > 0 for n in v) for v in v['ordered_type_lengths']), 'SYN_TYPE_LENGTHS')
        result[name] = v
    w = result['shifted_extreme']
    require(w['extrema'][0]['max_reps'] == [2] and w['extrema'][2]['max_reps'] == [3] and w['ranges'][2] == 153, 'SYN_WRONG_EXTREME')
    # Exhaustively check the closed form on small triples, including binding floors.
    trials = 0
    for y in product(range(4), repeat=3):
        for x in product(*(range(v+1) for v in y)):
            for t in range(4):
                options = [max(abs(u-v) for u,v in zip(y,z)) for z in product(*(range(u,max(y)+1) for u in x)) if spread(z) <= t]
                require(complement_witness(x,y,t)['budget'] == min(options), 'SYN_MIN_EXHAUSTIVE')
                trials += 1
    return result, trials


def run(root):
    old = history(acquire(root))
    syn, trials = examples()
    return {'schema':'local-byte-range-study-v1', 'threshold':T, 'history':old, 'history_b1_b2_same':sum(a['gates'][0] == a['gates'][1] for a in old.values()), 'history_conjunction_pass':sum(a['conjunction'] for a in old.values()), 'synthetic':syn, 'optimizer_small_exhaustive_checks':trials}


if __name__ == '__main__':
    try:
        out = run(Path.cwd())
        data = (json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
        require(data == (Path(__file__).resolve().parent / 'evidence.json').read_bytes(), 'EXPECTED_REPLAY')
        print('OK: 15 fixed slots, both implication counterexamples, 4000 optimizer checks')
    except (Reject, ValueError, OverflowError, KeyError, TypeError, OSError, subprocess.SubprocessError) as e:
        print('REJECT', str(e) if isinstance(e, Reject) else type(e).__name__, file=sys.stderr)
        sys.exit(2)
