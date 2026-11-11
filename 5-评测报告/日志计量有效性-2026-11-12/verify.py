#!/usr/bin/env python3
"""Read-only arithmetic replay of a NEW content-free derived projection.
Python 3.9 stdlib; never imports observers or opens private originals.
Hashes bind public files, not their historical authenticity or HTTP direction.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = '5-评测报告/日志计量有效性-2026-11-12'
PRIOR = '4-打分细则/机制重复口径澄清-2026-11-12/evidence.json'
PRIOR_SHA256 = '925470d3b55b4226d70f5749d45d0c65a161703c4053fa21028ce0516fcd6b5c'
EVIDENCE_SHA256 = '48e197314d22bc2b49cedad7625ba3edd16f8c176643fb5e470d9ab550110e61'
BASELINE = '52b5e81531f3171292240a01c4ef3e4cb4b84eb8'
CASES = ('bird-ca-schools-15', 'dabstep-payments-10', 'exercism-py-6', 'lcb-recent-hard-4', 'tb-cargo-plan')
S3_TYPES = ('user/message', 'request/header', 'request/context')
S4_TYPES = ('assistant/message', 'tool/call')
SUBTYPES = ('message', 'reasoning', 'function_call', 'function_call_output')
KINDS = ('user', 'agent-instructions', 'runtime-context', 'tool-jobs', 'subagent-settled')
STRIP = ['id', 'internal_chat_message_metadata_passthrough', 'call_id']
COLUMNS = ['type', 'event_bytes', 'payload_type', 'payload_bytes', 'role', 'source_kind', 'event_sha256', 'payload_sha256', 'logical_sha256', 'item_id_sha256', 'call_id_sha256', 'details']


class Invalid(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise Invalid(message)


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def integer(value):
    require(type(value) is int and value >= 0, 'expected nonnegative integer')
    return value


def digest(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None, 'invalid SHA256')
    return value


def exact_keys(value, keys):
    require(type(value) is dict and set(value) == set(keys), 'invalid object schema')


def fingerprint(value):
    require(type(value) is list and len(value) == 2, 'invalid fingerprint')
    integer(value[0]); digest(value[1])


def strict_json(raw):
    def pairs(items):
        result = {}
        for k, v in items:
            require(k not in result, 'duplicate JSON key')
            result[k] = v
        return result
    def nonfinite(_):
        raise Invalid('nonfinite JSON number')
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)
    except (ValueError, UnicodeError) as error:
        raise Invalid('invalid JSON: ' + str(error)) from error


def bound_bytes(root, relative, expected):
    path = Path(relative)
    require(not path.is_absolute() and '..' not in path.parts, 'unsafe source path')
    target = (root / path).resolve()
    require(root in target.parents, 'source escapes root')
    try:
        raw = target.read_bytes()
    except OSError as error:
        raise Invalid('missing source: ' + relative) from error
    require(sha(raw) == digest(expected), 'source SHA mismatch: ' + relative)
    return raw


def slots_expected():
    return {f'{arm}__{case}__r{rep}' for arm in ('dsh', 'codex') for case in CASES for rep in (1, 2, 3)}


def validate_details(details, arm, kind):
    exact_keys(details, ('parts', 'keys', 'counts'))
    for field in ('parts', 'keys', 'counts'):
        require(type(details[field]) is dict, 'details field not object')
    allowed_parts = {'data', 'content', 'source', 'text_utf8', 'header', 'tools', 'config', 'adapterDefaults'} if arm == 'dsh' else {'content', 'encrypted_content_utf8', 'base_instructions_text_utf8', 'payload'}
    require(set(details['parts']) <= allowed_parts, 'unknown part')
    for value in details['parts'].values():
        fingerprint(value)
    require(set(details['keys']) <= {'data', 'header', 'payload'}, 'unknown structure')
    for value in details['keys'].values():
        require(type(value) is list and all(type(x) is str and re.fullmatch('[A-Za-z_][A-Za-z0-9_]*', x) for x in value), 'invalid field keys')
        require(value == sorted(set(value)), 'field keys not unique sorted')
    require(set(details['counts']) <= {'tools'}, 'unknown count')
    for value in details['counts'].values():
        integer(value)
    if arm == 'dsh':
        if kind == 'user/message':
            require(set(details['parts']) == {'data', 'content', 'source', 'text_utf8'}, 'missing user parts')
            require(details['parts']['data'][0] >= details['parts']['content'][0] + details['parts']['source'][0], 'negative user overhead')
        elif kind == 'request/header':
            require(set(details['parts']) == {'data', 'header', 'tools', 'config', 'adapterDefaults'}, 'missing header parts')
            require(details['keys'].get('header') == ['adapterDefaults', 'config', 'tools'], 'not static declaration header')
            require(set(details['counts']) == {'tools'}, 'missing tools count')
            p = details['parts']
            require(p['data'][0] >= p['header'][0] >= sum(p[k][0] for k in ('tools', 'config', 'adapterDefaults')), 'negative header overhead')
        elif kind == 'request/context':
            require(details['keys'].get('data') == ['contextWindow', 'model', 'provider', 'systemPromptUpdate'], 'not context declaration')
    elif kind == 'session_meta':
        require(set(details['parts']) == {'base_instructions_text_utf8', 'payload'}, 'missing base instructions')
    elif kind in ('turn_context', 'world_state', 'token_usage_record'):
        require(set(details['parts']) == {'payload'} and set(details['keys']) == {'payload'}, 'missing excluded payload')


def validate_rows(rows, arm, prior_rows):
    require(type(rows) is list and len(rows) == len(prior_rows) and rows, 'event count changed')
    for row, old in zip(rows, prior_rows):
        require(type(row) is list and len(row) == 12, 'invalid event row')
        require(row[:4] == old, 'prior four-column mismatch')
        require(type(row[0]) is str and row[0], 'invalid event type')
        integer(row[1]); integer(row[3]); require(row[1] > 0, 'empty event')
        digest(row[6])
        validate_details(row[11], arm, row[0])
        if row[0] == 'response_item':
            require(arm == 'codex' and row[2] in SUBTYPES and row[1] > row[3] > 0, 'bad payload')
            digest(row[7]); digest(row[8])
            for value in row[9:11]:
                if value is not None:
                    digest(value)
            require(row[5] is None, 'unexpected Codex source kind')
            require(row[4] in ('developer', 'user', 'assistant') if row[2] == 'message' else row[4] is None, 'bad message role')
        else:
            require(row[2] is None and row[3] == 0 and all(v is None for v in row[7:11]), 'unexpected payload columns')
            if arm == 'dsh' and row[0] == 'user/message':
                require(row[4] == 'user' and row[5] in KINDS, 'bad user source')
            else:
                require(row[4] is None and row[5] is None, 'unexpected role/source')
        if arm == 'dsh' and 'data' in row[11]['parts']:
            require(row[1] > row[11]['parts']['data'][0], 'negative event wrapper')


def sums(rows, key, byte_index):
    result = {}
    for label in sorted({key(r) for r in rows}):
        selected = [r for r in rows if key(r) == label]
        result[label] = {'count': len(selected), 'bytes': sum(r[byte_index] for r in selected)}
    return result


def dsh_measure(rows):
    selected = [r for r in rows if r[0] in S3_TYPES]
    users = [r for r in rows if r[0] == 'user/message']
    by_kind = {}
    for k in sorted({r[5] for r in users}):
        rs = [r for r in users if r[5] == k]
        content = sum(r[11]['parts']['content'][0] for r in rs)
        source = sum(r[11]['parts']['source'][0] for r in rs)
        by_kind[k] = {'count': len(rs), 'event_bytes': sum(r[1] for r in rs), 'content_canonical_bytes': content,
                      'source_canonical_bytes': source, 'event_other_bytes': sum(r[1] for r in rs) - content - source,
                      'text_utf8_bytes': sum(r[11]['parts']['text_utf8'][0] for r in rs),
                      'content_sha256': [r[11]['parts']['content'][1] for r in rs]}
    declarations = []
    for n, r in enumerate(rows, 1):
        if r[0] in ('request/header', 'request/context'):
            parts = r[11]['parts']
            rec = {'line': n, 'type': r[0], 'event_bytes': r[1], 'parts': parts,
                   'event_minus_data_bytes': r[1] - parts['data'][0], 'keys': r[11]['keys'], 'counts': r[11]['counts']}
            if r[0] == 'request/header':
                rec['data_minus_header_bytes'] = parts['data'][0] - parts['header'][0]
                rec['header_minus_child_values_bytes'] = parts['header'][0] - sum(parts[k][0] for k in ('tools', 'config', 'adapterDefaults'))
            declarations.append(rec)
    return {'S3_bytes': sum(r[1] for r in selected), 'S4_bytes': sum(r[1] for r in rows if r[0] in S4_TYPES),
            'S3_by_type': sums(selected, lambda r: r[0], 1), 'users_by_source_kind': by_kind,
            'excluded_from_S3': sums([r for r in rows if r[0] not in S3_TYPES], lambda r: r[0], 1),
            'declarations': declarations}


def duplicates(items, column):
    groups = defaultdict(list)
    for line, row in items:
        if row[column] is not None:
            groups[row[column]].append((line, row))
    return [{'sha256': h, 'type': xs[0][1][2], 'lines': [x[0] for x in xs],
             'excess_count': len(xs) - 1, 'excess_original_payload_bytes': sum(x[1][3] for x in xs[1:])}
            for h, xs in sorted(groups.items()) if len(xs) > 1]


def codex_measure(rows):
    items = [(n, r) for n, r in enumerate(rows, 1) if r[0] == 'response_item']
    payloads = [r for _, r in items]
    segments = []; pending = []; marker = 0
    for n, r in enumerate(rows, 1):
        if r[0] == 'response_item':
            pending.append((n, r))
        elif r[0] == 'token_usage_record':
            segments.append({'start_after_line': marker, 'end_usage_line': n, 'closed': True,
                             'items': len(pending), 'R3_bytes': sum(x[1][3] for x in pending),
                             'R4_bytes': sum(x[1][3] for x in pending if x[1][2] in ('message', 'reasoning'))})
            pending = []; marker = n
    if pending:
        segments.append({'start_after_line': marker, 'end_usage_line': None, 'closed': False,
                         'items': len(pending), 'R3_bytes': sum(x[1][3] for x in pending),
                         'R4_bytes': sum(x[1][3] for x in pending if x[1][2] in ('message', 'reasoning'))})
    require(len(items) >= 3 and [r[2] for _, r in items[:3]] == ['message'] * 3 and [r[4] for _, r in items[:3]] == ['developer', 'user', 'user'], 'invalid leading controls')
    controls = [{'line': n, 'role': r[4], 'content': r[11]['parts']['content']} for n, r in items[:3]]
    control_pairs = {(r[4], r[11]['parts']['content'][1]) for _, r in items[:3]}
    later_controls = [n for n, r in items[3:] if r[2] == 'message' and (r[4], r[11]['parts']['content'][1]) in control_pairs]
    calls = {r[10]: n for n, r in items if r[2] == 'function_call'}
    require(len(calls) == sum(r[2] == 'function_call' for r in payloads) and None not in calls, 'ambiguous call identity')
    usage_lines = [n for n, r in enumerate(rows, 1) if r[0] == 'token_usage_record']
    exchanges = []
    for n, r in items:
        if r[2] == 'function_call_output':
            require(r[10] in calls and calls[r[10]] < n, 'orphan or unordered output')
            call = calls[r[10]]
            exchanges.append({'call_line': call, 'output_line': n, 'usage_between_lines': [u for u in usage_lines if call < u < n]})
    output_ids = [r[10] for _, r in items if r[2] == 'function_call_output']
    require(len(output_ids) == len(set(output_ids)) and set(output_ids) == set(calls), 'duplicate or missing output identity')
    require(len(exchanges) == len(calls), 'unclosed call/output exchange')
    excluded = [r for r in rows if r[0] != 'response_item']
    base = [r[11]['parts']['base_instructions_text_utf8'] for r in rows if r[0] == 'session_meta']
    require(len(base) == 1, 'invalid session metadata count')
    return {'R3_bytes': sum(r[3] for r in payloads), 'R4_bytes': sum(r[3] for r in payloads if r[2] in ('message', 'reasoning')),
            'by_payload_type': sums(payloads, lambda r: r[2], 3),
            'message_by_role': sums([r for r in payloads if r[2] == 'message'], lambda r: r[4], 3),
            'output_like_log_category_bytes': sum(r[3] for r in payloads if r[2] in ('reasoning', 'function_call') or (r[2] == 'message' and r[4] == 'assistant')),
            'excluded_event_types': sums(excluded, lambda r: r[0], 1), 'base_instructions_text_utf8': base[0],
            'reasoning_content_canonical_bytes': sum(r[11]['parts'].get('content', [0])[0] for r in payloads if r[2] == 'reasoning'),
            'reasoning_encrypted_content_utf8_bytes': sum(r[11]['parts'].get('encrypted_content_utf8', [0])[0] for r in payloads if r[2] == 'reasoning'),
            'segments': segments, 'usage_markers': len(usage_lines), 'nonempty_closed_segments': sum(s['closed'] and s['items'] > 0 for s in segments),
            'empty_closed_segments': sum(s['closed'] and s['items'] == 0 for s in segments), 'unclosed_tail_segments': sum(not s['closed'] for s in segments),
            'exact_payload_duplicates': duplicates(items, 7), 'stripped_metadata_duplicates': duplicates(items, 8),
            'item_id_duplicates': duplicates(items, 9), 'leading_controls': controls, 'later_control_role_content_matches': later_controls,
            'call_output_exchanges': exchanges, 'usage_payload_key_sets': sorted({tuple(r[11]['keys']['payload']) for r in rows if r[0] == 'token_usage_record'})}


def merge_maps(maps):
    out = {}
    for mapping in maps:
        for key, value in mapping.items():
            rec = out.setdefault(key, {'count': 0, 'bytes': 0})
            rec['count'] += value['count']; rec['bytes'] += value['bytes']
    return dict(sorted(out.items()))


def analyze(root):
    root = Path(root).resolve()
    prior = strict_json(bound_bytes(root, PRIOR, PRIOR_SHA256))
    evidence = strict_json(bound_bytes(root, HERE + '/evidence.json', EVIDENCE_SHA256))
    exact_keys(evidence, ('schema', 'baseline_commit', 'prior_evidence_sha256', 'columns', 'stripped_payload_keys', 'slots'))
    require(evidence['schema'] == 'log-measurement-projection-v1' and evidence['baseline_commit'] == BASELINE and evidence['prior_evidence_sha256'] == PRIOR_SHA256, 'projection identity changed')
    require(evidence['columns'] == COLUMNS and evidence['stripped_payload_keys'] == STRIP, 'projection definition changed')
    require(type(prior['public_sources']) is list and len(prior['public_sources']) == 69, 'public source count changed')
    paths = [r['path'] for r in prior['public_sources']]
    require(len(set(paths)) == 69, 'duplicate source binding')
    sources = {r['path']: bound_bytes(root, r['path'], r['sha256']) for r in prior['public_sources']}
    accounting = strict_json(sources['3-表现现场/r1109-mech-n3/observe/trace-accounting-summary.json'])
    incidents = {r['slot']: r for arm in ('dsh', 'codex') for r in accounting[arm]['incidents']}
    old = {s['slot']: s for s in prior['slots']}
    require(len(old) == 30 and set(old) == slots_expected() and set(incidents) == slots_expected(), 'prior mixed slots')
    require(type(evidence['slots']) is list and len(evidence['slots']) == 30, 'bad slot list')
    names = [s['slot'] for s in evidence['slots']]
    require(len(set(names)) == 30 and set(names) == slots_expected(), 'missing or mixed slot')
    results = []
    for s in evidence['slots']:
        exact_keys(s, ('slot', 'source_sha256', 'events'))
        name = s['slot']; arm = name.split('__')[0]; original = old[name]; identity = original['identity']
        require(digest(s['source_sha256']) == identity['sha256'], 'private source binding changed')
        expected = f'{arm}/runs/{name}/agent-session/'
        require(identity['source_relative_to_archive'].startswith(expected), 'mixed archive slot')
        if arm == 'codex':
            require(identity['file'] == incidents[name]['true_rollout'] and identity['source_relative_to_archive'] == expected + identity['file'], 'not accounting true rollout')
        else:
            require(identity['id'] in incidents[name]['candidates'] and identity['source_relative_to_archive'] == expected + 'session.v4.jsonl.zstd', 'not accounting DSH candidate')
        validate_rows(s['events'], arm, original['events'])
        result = dsh_measure(s['events']) if arm == 'dsh' else codex_measure(s['events'])
        results.append({'slot': name, 'source_sha256': s['source_sha256'], 'event_count': len(s['events']), **result})
    ds = [r for r in results if r['slot'].startswith('dsh__')]; cs = [r for r in results if r['slot'].startswith('codex__')]
    dkind = {}
    for kind in KINDS:
        rows = [r['users_by_source_kind'][kind] for r in ds if kind in r['users_by_source_kind']]
        dkind[kind] = {k: sum(r[k] for r in rows) for k in ('count', 'event_bytes', 'content_canonical_bytes', 'source_canonical_bytes', 'event_other_bytes', 'text_utf8_bytes')}
    dtotal = {'slots': len(ds), 'S3_bytes': sum(r['S3_bytes'] for r in ds), 'S4_bytes': sum(r['S4_bytes'] for r in ds),
              'S3_by_type': merge_maps(r['S3_by_type'] for r in ds), 'users_by_source_kind': dkind,
              'excluded_from_S3': merge_maps(r['excluded_from_S3'] for r in ds),
              'static_declaration_bytes': sum(r['S3_by_type']['request/header']['bytes'] + r['S3_by_type']['request/context']['bytes'] for r in ds)}
    ctotal = {k: sum(r[k] for r in cs) for k in ('R3_bytes', 'R4_bytes', 'output_like_log_category_bytes', 'usage_markers', 'nonempty_closed_segments', 'empty_closed_segments', 'unclosed_tail_segments', 'reasoning_content_canonical_bytes', 'reasoning_encrypted_content_utf8_bytes')}
    ctotal.update({'slots': len(cs), 'by_payload_type': merge_maps(r['by_payload_type'] for r in cs), 'message_by_role': merge_maps(r['message_by_role'] for r in cs),
                   'excluded_event_types': merge_maps(r['excluded_event_types'] for r in cs), 'base_instructions_text_utf8_bytes': sum(r['base_instructions_text_utf8'][0] for r in cs),
                   'base_instructions_distinct_hashes': len({r['base_instructions_text_utf8'][1] for r in cs}),
                   'R3_min': min(r['R3_bytes'] for r in cs), 'R3_max': max(r['R3_bytes'] for r in cs),
                   'exact_payload_excess_duplicates': sum(d['excess_count'] for r in cs for d in r['exact_payload_duplicates']),
                   'stripped_metadata_excess_duplicates': sum(d['excess_count'] for r in cs for d in r['stripped_metadata_duplicates']),
                   'duplicate_item_ids': sum(d['excess_count'] for r in cs for d in r['item_id_duplicates']),
                   'later_control_matches': sum(len(r['later_control_role_content_matches']) for r in cs),
                   'call_output_pairs': sum(len(r['call_output_exchanges']) for r in cs),
                   'pairs_with_usage_between': sum(bool(p['usage_between_lines']) for r in cs for p in r['call_output_exchanges'])})
    return {'schema': 'log-measurement-result-v1', 'baseline_commit': BASELINE,
            'evidence_sha256': EVIDENCE_SHA256, 'prior_evidence_sha256': PRIOR_SHA256,
            'boundary': 'New derived arithmetic projection; not original authenticity, full HTTP inputs, token/cost or HTTP direction certification.',
            'public_sources_checked': len(sources), 'private_source_bindings_checked': len(results), 'projected_events': sum(r['event_count'] for r in results),
            'dsh': dtotal, 'codex': ctotal, 'per_slot': results}


def render(result):
    return json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False).encode('utf-8') + b'\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument('--output', type=Path, help='create NEW output exclusively; default stdout')
    args = ap.parse_args(argv)
    try:
        raw = render(analyze(args.root))
        if args.output is None:
            sys.stdout.buffer.write(raw)
        else:
            with args.output.open('xb') as out:
                out.write(raw)
        return 0
    except (Invalid, OSError, KeyError, TypeError, IndexError) as error:
        print('FAIL: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
