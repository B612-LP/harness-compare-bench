#!/usr/bin/env python3
"""Offline projection of four fixed public derivatives and one companion README."""
import argparse
import hashlib
import json
from pathlib import Path


COMMIT = 'dd5a12f651527923a412f6727d5d2f9c22457026'
PINS = {
    'hold': ('同对象同窗读取检测校准', '83a8e036c468d2636d183c2dbb316e523d4faa4b2810cf0e3c229ae112a10d4c'),
    'gap': ('读取探针窗口空隙', 'c038bbb1da7751a24e06f63bd9f445e6b66e4f7f658a2f079ec91dbe5610aba8'),
    'offset': ('读取探针单次偏移', 'c8e5fd4527409bd550d266901566867779d6624fe497b5eb59a311b6d408f45d'),
    'mmap': ('读取探针文件映射', '5f012a8aef09290dea9e794982f195710b373d49c9f64d263087a980a4a5f774'),
}
OFFSET_COMPANION = ('5-评测报告/读取探针单次偏移-2026-11-19/README.md',
                    '3639c7c79bbbfef5f2ac2364d565a3af6db4a689e39e038aa7e73909364794d2')
# Fixture-specific literal documented in the pinned README, not derived from fd position.
OFFSET_A_PREAD_ZERO = 0


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def unique(items):
    d = {}
    for k, v in items:
        require(k not in d, 'duplicate JSON key')
        d[k] = v
    return d


def fixed_public_bytes(repo, relative, pin):
    path = repo / relative
    for part in (path, *path.parents):
        if part == repo:
            break
        require(not part.is_symlink(), 'unexpected symlink in fixed public path')
    require(path.is_file(), 'fixed public input missing')
    data = path.read_bytes()
    require(digest(data) == pin, f'{relative}: SHA-256 mismatch')
    return data


def public_inputs(repo):
    docs, pins = {}, {}
    for alias, (name, pin) in PINS.items():
        relative = f'5-评测报告/{name}-2026-11-19/evidence.json'
        data = fixed_public_bytes(repo, relative, pin)
        docs[alias] = json.loads(data, object_pairs_hook=unique)
        pins[alias] = {'repository_relative_public_path': relative, 'sha256': pin}
    relative, pin = OFFSET_COMPANION
    companion = fixed_public_bytes(repo, relative, pin)
    require(b'| A | `os.pread(fd, 512, 0)`' in companion, 'offset A documented notation missing')
    pins['offset_companion_readme'] = {'repository_relative_public_path': relative, 'sha256': pin,
                                      'scope': 'reports_arm_A_explicit_pread_argument_not_raw_call_receipt'}
    return docs, pins


def arm(operation, timing, size, checksum, span, denominator):
    if span is None:
        status = 'reported_control_no_content_operation'
        coverage = None
    elif denominator is None:
        status, coverage = 'reported_interval_unknown_denominator', None
    else:
        coverage = span[1] - span[0]
        status = 'reported_complete_in_scope' if coverage == denominator else 'reported_partial_in_scope'
    return {'operation': operation, 'action_or_control_marker_rel_ns': timing,
            'reported_returned_bytes': size, 'reported_payload_sha256': checksum,
            'reported_source_intervals': [] if span is None else [span],
            'covered_bytes_given_denominator': coverage, 'coverage_status': status}


def source_projection(data):
    groups = {}
    hold = data['hold']
    size = hold['target']['bytes']
    for p in hold['pairs']:
        roles = {}
        for a in p['arms']:
            positive = a['role'] == 'read'
            require((a['initial_offset'], a['final_offset']) == (0, size if positive else 0), 'hold reported range')
            if positive:
                require((a['bytes'], a['sha256']) == (size, hold['target']['sha256']), 'hold reported payload')
            roles[a['role']] = arm(a['action'], [a['action_start_ns'], a['action_end_ns']], a['bytes'],
                                   a['sha256'], [0, size] if positive else None, size)
        start = max(a['post_fstat_ns'] for a in p['arms'])
        end = min(p['planned_hold_ns'], *(a['close_start_ns'] for a in p['arms']))
        s = p['sample']
        groups['hold_' + p['pair']] = {'scope': 'file_bytes', 'denominator_bytes': size, 'arms': roles,
            'source_pair_status': p['decision'], 'source_pair_qualified': p['truth_pair_qualified'],
            'both_pre_fstat_before_first_action': max(a['pre_fstat_ns'] for a in p['arms']) <= min(a['action_start_ns'] for a in p['arms']),
            'fd_sampling': {'envelope_rel_ns': [s['start_ns'], s['end_ns']],
                'candidate_post_action_hold_rel_ns': [start, end], 'capture_inside_post_action_hold': start <= s['start_ns'] <= s['end_ns'] <= end,
                'reported_exact_matches_in_read_open_order': s['exact_FD_target_matches_read_then_open_only']}}

    gap = data['gap']
    g = gap['result']
    roles = {}
    for role, a in g['arms'].items():
        positive = role == 'read'
        if positive:
            require(a['offsets'] == [0, a['content_bytes']] and a['content_sha256'] == gap['expected_payload_sha256'], 'gap reported range')
        roles[role] = arm('os.read' if positive else 'open_only', a['os_read'] if positive else a['action'],
                          a['content_bytes'], a['content_sha256'], [0, a['content_bytes']] if positive else None, None)
    before, after = (g['samples'][key]['envelope'] for key in ('before', 'after'))
    groups['gap'] = {'scope': 'file_bytes_extent_unreported', 'denominator_bytes': None, 'arms': roles,
        'source_pair_status': g['classification'], 'reported_common_target_interval_rel_ns': g['shared_target_window_ns'],
        'fd_sampling': {'before_envelope_rel_ns': before, 'after_envelope_rel_ns': after,
            'target_lifecycle_between_samples': before[1] < min(a['target_open'][0] for a in g['arms'].values())
                and max(a['target_close'][1] for a in g['arms'].values()) < after[0]}}

    offset = data['offset']
    o = offset['observed']
    size = offset['fixture_size_bytes']
    roles, offsets = {}, {}
    for role, a in o['arms'].items():
        span = provenance = None
        if role == 'A':
            require(a['operation'] == 'pread' and a['content_reads'] == 1, 'offset arm A operation')
            start = OFFSET_A_PREAD_ZERO
            span = [start, start + a['returned_content_bytes']]
            provenance = 'offset_companion_readme_documented_explicit_pread_argument_and_reported_return_length'
        elif role == 'D':
            require(a['operation'] == 'read' and a['content_reads'] == 1, 'offset arm D operation')
            start = a['worker_offsets'][0]
            span = [start, start + a['returned_content_bytes']]
            provenance = 'reported_pre_read_worker_cursor_and_return_length'
        else:
            require(role in ('B', 'C') and a['content_reads'] == 0, 'offset control operation')
        roles[role] = arm(a['operation'], a['action_rel_ns'], a['returned_content_bytes'], a['content_sha256'], span, size)
        if provenance is not None:
            roles[role]['reported_interval_provenance'] = provenance
        offsets[role] = a['collector_offset']
    groups['offset'] = {'scope': 'file_bytes', 'denominator_bytes': size, 'arms': roles,
        'source_pair_status': offset['decision'], 'reported_common_target_interval_rel_ns': o['confirmed_common_hold_rel_ns'],
        'fd_sampling': {'envelope_rel_ns': o['collector_envelope_rel_ns'], 'reported_offsets_bytes': offsets}}

    m = data['mmap']
    size = m['fixture']['page_bytes']
    roles = {}
    for role, a in m['arms'].items():
        positive = role == 'consume'
        require(a['content_operations'] == int(positive), 'mmap reported operation count')
        roles[role] = arm('copy_mapped_prefix' if positive else 'map_only', a['content_action_ns'], a['content_bytes'],
                          a['content_sha256'], [0, a['content_bytes']] if positive else None, size)
    collection = m['collection']
    groups['mmap'] = {'scope': 'mapped_view_bytes_not_file_extent', 'denominator_bytes': size,
        'file_denominator_bytes': None, 'view_to_file_origin': None, 'arms': roles, 'source_pair_status': m['conclusion'],
        'reported_common_map_interval_rel_ns': [max(a['initial_map_fd_check_ns'][1] for a in m['arms'].values()),
            min(a['final_map_fd_check_ns'][0] for a in m['arms'].values())],
        'fd_sampling': {'envelope_rel_ns': collection['envelope_ns'],
            'reported_numeric_target_rows': collection['each_arm_exact_target_numeric_rows'],
            'reported_nonnumeric_labels': collection['each_arm_exact_target_nonnumeric_labels']}}
    require(sum(len(g['arms']) for g in groups.values()) == 12, 'unexpected public projection size')
    return groups


def examples():
    # Fixed didactic tuples. These are not captured records or a generic API.
    x = bytes(range(256)) * 2
    file_data = x + x
    ht, hh = ((0, 512), (512, 1024)), ((0, 512), (0, 512))
    def union_bytes(spans):
        return len({i for lo, hi in spans for i in range(lo, hi)})
    def returns(spans):
        return tuple(file_data[lo:hi] for lo, hi in spans)
    require(returns(ht) == returns(hh), 'didactic byte collision condition failed')
    view = (0, 512)
    origin = 512
    return {
        'same_returns_different_cover': {'source_construction': 'bytes(range(256))*4', 'query_file_range': [0, len(file_data)],
            'each_call_bytes': [len(b) for b in returns(ht)], 'each_call_sha256': [digest(b) for b in returns(ht)],
            'concatenated_returns_sha256': digest(b''.join(returns(ht))),
            'separate_halves': {'intervals': ht, 'file_covered_bytes': union_bytes(ht)},
            'repeat_first_half': {'intervals': hh, 'file_covered_bytes': union_bytes(hh)}},
        'other_object_or_window': {'same_payload_bytes_each': len(x), 'same_payload_sha256': digest(x),
            'query_window_in_synthetic_ticks': [200, 450], 'other_object_same_window': 'excluded_different_object_not_an_unread_finding',
            'same_object_action_envelope_outside_ticks': [550, 551], 'outside_result': 'excluded_outside_window_not_an_unread_finding'},
        'zero_length': {'separate_control_example': 'bound_open_only_state_no_content_operation',
            'reported_pread_zero_no_witness': 'unknown_not_an_unread_finding', 'empty_buffer_sha256': digest(b''),
            'stipulated_bound_pread_zero_receipt': 'zero_length_return_witnessed_not_an_unread_finding'},
        'coordinate_frame': {'stipulated_view_range': view, 'same_axis_view_covered_bytes': union_bytes((view,)),
            'same_numerical_file_range_no_transform': 'unknown_not_file_coverage', 'different_view_epoch': 'not_combined',
            'stipulated_bound_view_origin_in_file_bytes': origin, 'converted_file_interval': [x + origin for x in view],
            'missing_file_extent': 'unknown_whole_file_denominator'},
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', required=True, type=Path, help='local checkout containing the five fixed public input files')
    p.add_argument('--derive', action='store_true', help='print fixed derived JSON to stdout instead of comparing')
    args = p.parse_args()
    inputs, pins = public_inputs(args.repo.resolve(strict=True))
    value = {'schema': 'reported-read-coverage-public-derivative-v2', 'previous_public_baseline': COMMIT,
             'prior_public_inputs': pins, 'prior_public_fields_reprojection': source_projection(inputs),
             'prior_evidence_grade': 'reported_public_fields_self_consistent_only',
             'new_synthetic_examples_not_runs': examples(), 'new_fixture_or_product_runs': 0}
    serialized = (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
    if args.derive:
        import sys
        sys.stdout.buffer.write(serialized)
    else:
        published = Path(__file__).with_name('evidence.json')
        require(published.is_file() and not published.is_symlink(), 'unsafe evidence path')
        require(published.read_bytes() == serialized, 'evidence bytes differ from exact fixed projection')
        print('OK: 4 pinned prior public JSONs and 1 companion README, 12 existing arms, 4 didactic example families; no new runs')


if __name__ == '__main__':
    main()
