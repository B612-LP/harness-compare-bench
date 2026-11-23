#!/usr/bin/env python3
"""Reconcile the public count table; this cannot verify the private originals."""
import argparse
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTROLS = {
    'N1': '只同步改 C、D（等长）',
    'N2': '只同步改 A、B（等长）',
    'N3': '同步改 A、B、C、D（等长）',
    'N4': '只错绑 B 的输出位置',
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def pairs(rows):
    obj = dict(rows)
    require(len(rows) == len(obj), 'duplicate object key')
    return obj


def fields(obj, *keys):
    require(isinstance(obj, dict) and obj.keys() == set(keys), 'unexpected object shape')


def count(n, upper=None):
    require(type(n) is int and n >= 0 and (upper is None or n <= upper), 'invalid count')
    return n


def verify(data, text):
    fields(data, 'schema', 'new_product_runs', 'original_streams', 'original_calls',
           'original', 'line_endings', 'controls')
    require(data['schema'] == 'codex-responses-arguments-bridge-trial-1', 'schema')
    require(count(data['new_product_runs']) == 0, 'only archival observations')
    n, k = (count(data[key]) for key in ('original_streams', 'original_calls'))
    require(n > 0 and k > 0, 'empty cohort')
    p0, e0, controls = (data[key] for key in ('original', 'line_endings', 'controls'))
    fields(p0, 'old_streams', 'bridge_calls', 'bound_packets')
    fields(e0, 'same_events', 'old_streams', 'bound_packets')
    fields(controls, *CONTROLS)

    def ratio(obj, key, d, unit=''):
        return f'{count(obj[key], d)}/{d}{unit}'

    rows = [
        ('原件', ratio(p0, 'old_streams', n, ' 流'), ratio(p0, 'bridge_calls', k, ' 调用'),
         ratio(p0, 'bound_packets', n, ' 包')),
        ('只换 LF→CRLF', ratio(e0, 'old_streams', n, ' 流'), '参数不变',
         ratio(e0, 'bound_packets', n, ' 包')),
    ]
    require((p0['old_streams'], p0['bound_packets'], p0['bridge_calls']) == (n, n, k), 'original coverage')
    require(count(e0['same_events'], n) == e0['old_streams'] == n and e0['bound_packets'] == 0,
            'line-ending control differs')
    for key, label in CONTROLS.items():
        arm = controls[key]
        fields(arm, 'specimens', 'accepted_old', 'accepted_bridge', 'bound_original')
        d = count(arm['specimens'], k)
        require(d == k, 'control coverage')
        rows.append((label, *(ratio(arm, col, d) for col in ('accepted_old', 'accepted_bridge', 'bound_original'))))
        require(arm['bound_original'] == 0, 'derived value bound as original')
    for key in ('N1', 'N2'):
        require(controls[key]['accepted_old'] == k and controls[key]['accepted_bridge'] == 0,
                'split controls did not discriminate')
    require(controls['N3']['accepted_bridge'] == controls['N3']['accepted_old'] == k, 'coherent-change control')
    require(controls['N4']['accepted_bridge'] == controls['N4']['accepted_old'] == 0, 'wrong-slot control')
    for row in rows:
        require(text.splitlines().count('| ' + ' | '.join(row) + ' |') == 1, 'README count table mismatch')
    require(f'**{n} 份冻结捕获，内有 {k} 个函数调用**' in text, 'README cohort mismatch')
    split_n = sum(controls[x]['accepted_old'] for x in ('N1', 'N2'))
    require(f'{split_n} 个局部派生变体' in text, 'README combined splits mismatch')
    return n, k, split_n


def self_test(data, text):
    def reject(path, value):
        mutant = copy.deepcopy(data)
        target = mutant
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        try:
            verify(mutant, text)
        except ValueError:
            return
        raise ValueError('invalid negative control accepted')

    for path, value in [
        (('original_streams',), True),
        (('original', 'bridge_calls'), data['original_calls'] - 1),
        (('line_endings', 'same_events'), data['original_streams'] - 1),
        (('controls', 'N1', 'accepted_bridge'), 1),
        (('controls', 'N3', 'bound_original'), 1),
        (('controls', 'N4', 'specimens'), data['original_calls'] - 1),
    ]:
        reject(path, value)
    try:
        verify(data, text.replace('只错绑 B 的输出位置', '其他'))
    except ValueError:
        return
    raise ValueError('README mutation accepted')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    data = json.loads((HERE / 'evidence.json').read_bytes(), object_pairs_hook=pairs)
    text = (HERE / 'README.md').read_text(encoding='utf-8')
    n, k, splits = verify(data, text)
    if args.self_test:
        self_test(data, text)
    print(f'OK: {n} original streams, {k} original calls, {splits} split variants; public consistency only')


if __name__ == '__main__':
    main()
