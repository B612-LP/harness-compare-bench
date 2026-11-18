#!/usr/bin/env python3
"""Check the released timing/derived flags only. No source access or live sampling."""
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

ARMS = ('consume', 'map_only')
MS = 1_000_000
EXPECTED = hashlib.sha256(bytes(range(256)) * 2).hexdigest()


def need(ok, message):
    if not ok:
        raise ValueError(message)


def uniq(pairs):
    out = {}
    for key, value in pairs:
        need(key not in out, 'duplicate JSON member')
        out[key] = value
    return out


def nonfinite(_):
    raise ValueError('nonfinite JSON value')


def parse(raw):
    return json.loads(raw.decode('utf-8'), object_pairs_hook=uniq, parse_constant=nonfinite)


def shape(obj, keys):
    keys = keys.split() if isinstance(keys, str) else keys
    need(type(obj) is dict and set(obj) == set(keys), 'wrong fields')


def exact(v, expected):
    need(type(v) is type(expected) and v == expected, 'wrong typed value')


def nsec(n):
    need(type(n) is int and -2_000 * MS <= n <= 2_000 * MS, 'relative nanosecond limit')
    return n


def interval(v):
    need(type(v) is list and len(v) == 2, 'invalid interval shape')
    a, b = map(nsec, v)
    need(a <= b, 'reversed interval')
    return a, b


def verify(e):
    shape(e, 'schema source_commitments_sha256 fixture arms collection cleanup conclusion')
    exact(e['schema'], 'local-mapped-view-paired-derived-v1')
    hashes = e['source_commitments_sha256']
    shape(hashes, 'preregistration_seal implementation_seal start_receipt raw_receipt')
    need(all(type(v) is str and re.fullmatch(r'[0-9a-f]{64}', v) for v in hashes.values()), 'SHA-256 commitment format')
    fixture = e['fixture']
    shape(fixture, 'clock page_bytes trials same_target_and_distinct_witness_bound')
    exact(fixture['clock'], 'CLOCK_MONOTONIC')
    exact(fixture['trials'], 1)
    exact(fixture['same_target_and_distinct_witness_bound'], True)
    page = fixture['page_bytes']
    need(type(page) is int and 4096 <= page <= 65536 and page & (page - 1) == 0, 'page size')
    arms = e['arms']
    shape(arms, ARMS)
    first_checks, begins, action_recv, before_final, pre_unmap, witness_ready, unmapped = [], [], [], [], [], [], []
    for arm in ARMS:
        x = arms[arm]
        shape(x, 'witness_ready_ns target_open_begin_ns mapping_return_ns target_fd_closed_ns initial_map_fd_check_ns '
                 'content_action_ns post_action_map_fd_check_ns parent_action_received_ns final_map_fd_check_ns pre_unmap_ns '
                 'unmapped_ns worker_cleanup_done_ns mapping_and_no_target_fd_checks content_operations content_bytes content_sha256')
        wr, op, mr, fd = [nsec(x[k]) for k in ('witness_ready_ns', 'target_open_begin_ns', 'mapping_return_ns', 'target_fd_closed_ns')]
        i0, i1 = interval(x['initial_map_fd_check_ns'])
        a0, a1 = interval(x['content_action_ns'])
        m0, m1 = interval(x['post_action_map_fd_check_ns'])
        f0, f1 = interval(x['final_map_fd_check_ns'])
        recv, u0, u1, done = [nsec(x[k]) for k in ('parent_action_received_ns', 'pre_unmap_ns', 'unmapped_ns', 'worker_cleanup_done_ns')]
        need(wr <= -300 * MS and 100 * MS <= op <= mr <= fd <= i0 <= i1 <= 135 * MS and
             250 * MS <= a0 <= a1 <= m0 <= m1 <= 285 * MS and m1 <= recv < f0 and
             900 * MS <= f0 <= f1 <= u0 <= u1 <= done <= 935 * MS, 'arm phase or order')
        checks = x['mapping_and_no_target_fd_checks']
        need(type(checks) is list and len(checks) == 3 and all(v is True for v in checks), 'missing private binding flag')
        positive = arm == 'consume'
        exact(x['content_operations'], 1 if positive else 0)
        exact(x['content_bytes'], 512 if positive else 0)
        exact(x['content_sha256'], EXPECTED if positive else None)
        first_checks.append(i1)
        begins.append(a0)
        action_recv.append(recv)
        before_final.append(f0)
        pre_unmap.append(u0)
        witness_ready.append(wr)
        unmapped.append(u1)
    common = (max(first_checks), min(pre_unmap))
    need(max(witness_ready) < common[0] < min(begins) <= max(action_recv) < common[1] <= min(unmapped), 'no common state')
    need(action_recv == sorted(action_recv), 'parent receive order')
    c = e['collection']
    shape(c, 'envelope_ns rc stderr_bytes each_arm_exact_witness_rows each_arm_exact_target_numeric_rows each_arm_exact_target_nonnumeric_labels')
    lo, hi = interval(c['envelope_ns'])
    need(400 * MS <= lo <= 435 * MS and 0 < hi - lo <= 175 * MS and
         max(action_recv) < lo < hi < min(before_final) <= common[1], 'collector outside stable state')
    exact(c['rc'], 0)
    exact(c['stderr_bytes'], 0)
    witnesses, numeric, labels = (c[k] for k in ('each_arm_exact_witness_rows', 'each_arm_exact_target_numeric_rows',
                                                 'each_arm_exact_target_nonnumeric_labels'))
    for x in (witnesses, numeric, labels):
        shape(x, ARMS)
    for arm in ARMS:
        exact(witnesses[arm], 1)
        exact(numeric[arm], 0)
        need(type(labels[arm]) is list and labels[arm] in ([], ['mem'], ['txt']), 'target label is undetermined')
    if labels[ARMS[0]] != labels[ARMS[1]]:
        outcome = 'unknown_surface_asymmetry'
    elif labels[ARMS[0]]:
        outcome = 'mapped_pair_equal_nonnumeric'
    else:
        outcome = 'mapped_pair_equal_none'
    exact(e['conclusion'], outcome)
    cleanup = e['cleanup']
    shape(cleanup, 'owned_fixture_files_removed owned_direct_children_reaped owned_direct_children_forced')
    exact(cleanup['owned_fixture_files_removed'], 2)
    exact(cleanup['owned_direct_children_reaped'], 3)
    exact(cleanup['owned_direct_children_forced'], 0)
    return {'decision': outcome, 'common_mapping_ns': list(common), 'collector_envelope_ns': [lo, hi],
            'target_nonnumeric_labels': labels}


def self_test(e):
    cases = [
        lambda r: r['arms']['map_only'].__setitem__('mapping_and_no_target_fd_checks', [True, True, 1]),
        lambda r: r['arms']['consume'].__setitem__('content_sha256', '0' * 64),
        lambda r: r['arms']['map_only'].__setitem__('content_bytes', 1),
        lambda r: r['arms']['consume'].__setitem__('target_fd_closed_ns', 900 * MS),
        lambda r: r['arms']['map_only'].__setitem__('parent_action_received_ns', r['collection']['envelope_ns'][0]),
        lambda r: r['collection'].__setitem__('envelope_ns', [400 * MS, 901 * MS]),
        lambda r: r['collection'].__setitem__('rc', 1),
        lambda r: r['collection']['each_arm_exact_witness_rows'].__setitem__('consume', 0),
        lambda r: r['collection']['each_arm_exact_target_numeric_rows'].__setitem__('consume', 1),
        lambda r: r['collection']['each_arm_exact_target_nonnumeric_labels'].__setitem__('map_only', []),
        lambda r: r['cleanup'].__setitem__('owned_direct_children_reaped', 2),
    ]
    for mut in cases:
        candidate = copy.deepcopy(e)
        mut(candidate)
        try:
            verify(candidate)
        except ValueError:
            continue
        raise ValueError('negative control passed')
    try:
        parse(b'{"conclusion":"x","conclusion":"y"}')
    except ValueError:
        return len(cases) + 1
    raise ValueError('duplicate key accepted')


def main():
    need(sys.argv[1:] in ([], ['--self-test']), 'usage: python3 verify.py [--self-test]')
    e = parse(Path(__file__).with_name('evidence.json').read_bytes())
    print(json.dumps(verify(e), sort_keys=True))
    if sys.argv[1:]:
        print(f'{self_test(e)} negative controls rejected (offline; no source authentication)')


if __name__ == '__main__':
    main()
