#!/usr/bin/env python3
"""Recompute fixed public sidecar contrasts; no private capture or provider proof."""
import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

PAIRS = [f'b{i:02d}' for i in range(1, 7)]
ARMS = ('inline', 'bounded')
FIELDS = ['input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'output_tokens']
PIN_SET = 'af195a39a09b413b97b52a86907b6532b4fe8d4f256cc02143a527fc57eb0614'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def unique(pairs):
    obj = {}
    for key, value in pairs:
        require(key not in obj, 'duplicate JSON key')
        obj[key] = value
    return obj


def forbidden(_):
    raise ValueError('nonstandard JSON constant')


def parse(data):
    return json.loads(data.decode('utf-8', 'strict'), object_pairs_hook=unique, parse_constant=forbidden)


def encoded(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'), sort_keys=True).encode('utf-8')


def expected_paths():
    return {'balance': '5-评测报告/首包平衡与次包单叶置换-2026-11-19/evidence.json', **{
        f'{pair}-{arm}': f'3-表现现场/r20261103-input-bytes/runs/confirm-{pair}-{arm}/reported-usage.json'
        for pair in PAIRS for arm in ARMS}}


def acquire(root, records):
    require(sha256(encoded(records)).hexdigest() == PIN_SET, 'unexpected public source pin set')
    require([(p['scope'], p['path']) for p in records] == list(expected_paths().items()), 'unexpected scoped path')
    out = {}
    for record in records:
        path = root / record['path']
        require(path.resolve() == path and path.is_file(), 'missing or redirected public source')
        with path.open('rb') as f:
            got = f.read(record['bytes'] + 1)
        require(len(got) == record['bytes'] and sha256(got).hexdigest() == record['sha256'], 'public source differs from fixed bytes')
        out[record['scope']] = parse(got)
    return out


def count(usage, field):
    value = usage.get(field)
    return value if type(value) is int and value >= 0 else None


def difference(a, b):
    return None if a is None or b is None else b - a


def classify(slot):
    if not (type(slot) is list and len(slot) == 2 and all(type(x) is dict for x in slot)
            and [x.get('request') for x in slot] == ['01-request.json', '02-request.json']):
        return [(None, 0), (None, 0)]
    out = []
    for req in slot:
        events = req.get('native_usage_events')
        if not (type(events) is list and len(events) == 2 and all(type(x) is dict and type(x.get('usage')) is dict for x in events)
                and [(x.get('event_type'),x.get('location')) for x in events] == [('message_start','message'),('message_delta','event')]):
            out.append((None, 0))
            continue
        a, z = [x['usage'] for x in events]
        first = [count(a, k) for k in FIELDS[:3]]
        last = [count(z, k) for k in FIELDS[:3]]
        inputs = [x if x == y else None for x, y in zip(first, last)]
        out.append((inputs + [count(z, FIELDS[3])], sum(x is not None for x in inputs)))
    return out


def summarize(source):
    balance = source['balance']['pairs']
    require(type(source['balance']['bound_slots']) is int and source['balance']['bound_slots'] == 12 and
            [row['pair'] for row in balance] == PAIRS, 'unbound reference blocks')
    items = []
    events = {'request_rows': 0, 'start_delta_pairs': 0, 'agree_input_components': 0}
    for block, evidence in zip(PAIRS, balance):
        scoped = [source[f'{block}-{arm}'] for arm in ARMS]
        local = [classify(s) for s in scoped]
        events['request_rows'] += sum(len(s) if type(s) is list else 0 for s in scoped)
        events['start_delta_pairs'] += sum(row[0] is not None for rows in local for row in rows)
        events['agree_input_components'] += sum(row[1] for rows in local for row in rows)
        matrix = [[difference(a, b) for a,b in zip(x[0] or [None] * 4, y[0] or [None] * 4)] for x,y in zip(*local)]
        items.append({'pair': block, 'req1_equal_ref': evidence['req1']['raw_equal'] is True, 'delta': matrix})
    counts = []
    for i in range(2):
        by_field = list(zip(*(p['delta'][i] for p in items)))
        counts.append({'request': i + 1, 'known_per_field': [sum(v is not None for v in vs) for vs in by_field],
                       'different_per_field': [sum(v is not None and v != 0 for v in vs) for vs in by_field]})
    return {'fields': FIELDS, 'pairs': items, 'events': events, 'counts': counts,
            'equal_first_and_differing_report': [x['pair'] for x in items if x['req1_equal_ref'] and any(
                q is not None and q != 0 for q in x['delta'][0])]}


def self_test(sources):
    original = sources['b01-inline']
    baseline = classify(original)[0]
    tests = 0
    for change, want in (
        (lambda s: s[0]['native_usage_events'].append(s[0]['native_usage_events'][0]), (None, 0)),
        (lambda s: s[0].update(request='02-request.json'), (None, 0)),
        (lambda s: s[0]['native_usage_events'][1].update(location='message'), (None, 0)),
        (lambda s: s[0]['native_usage_events'][1]['usage'].update(cache_creation_input_tokens=True),
         ([baseline[0][0], None, *baseline[0][2:]], 2)),
        (lambda s: s[0]['native_usage_events'][1]['usage'].pop('cache_creation_input_tokens'),
         ([baseline[0][0], None, *baseline[0][2:]], 2)),
        (lambda s: s[0]['native_usage_events'][1]['usage'].update(cache_read_input_tokens=baseline[0][2]+1),
         ([*baseline[0][:2], None, baseline[0][3]], 2)),
        (lambda s: s[0]['native_usage_events'][1]['usage'].update(output_tokens=baseline[0][3]+1),
         ([*baseline[0][:3], baseline[0][3]+1], 3)),
    ):
        sample = deepcopy(original)
        change(sample)
        require(classify(sample)[0] == want, 'unexpected self-test classification')
        tests += 1
    try:
        parse(br'{"output_tokens":0,"\u006futput_tokens":0}')
    except ValueError:
        tests += 1
    else:
        raise ValueError('duplicate key accepted')
    return tests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    here = Path(__file__).resolve().parent
    parser.add_argument('--root', type=Path, default=here.parent.parent)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    package = parse((here/'evidence.json').read_bytes())
    require(package.keys() == {'schema', 'fixed_sources', 'result'} and package['schema'] == 'confirm-usage-public-v1', 'bad evidence format')
    source = acquire(args.root.resolve(), package['fixed_sources'])
    result = summarize(source)
    require(encoded(result) == encoded(package['result']), 'printed result differs from fixed public sidecars')
    print(json.dumps({'result': result, 'self_tests_passed': self_test(source) if args.self_test else None,
                      'read_private_captures': False, 'authenticated_provider_usage': False}, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, UnicodeError):
        sys.exit('fixed public sidecar verification failed')
