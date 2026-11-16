#!/usr/bin/env python3
"""Standard-library offline replay of product-reported counters, not provider attestation.
--root explicitly selects the public repository; its default is this public file's
parents[2]. --archive-root additionally rebuilds private source relations. Full JSON
is written only to a new --output; stdout is a content-free summary. No archived
command, old runner, Git, network, model or product is executed.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = Path(__file__).resolve().parents[2]
BASELINE = '50c073c084006c0bfd5f8b79db3bc495e842847b'
PROTOCOL_SHA256 = 'd86cf15e8196dbe98fa3e4dfec880b743677a7bee01b60e09591c5960a2feaef'
SOURCES_SHA256 = '09efcb05cd8fa8ba9fc7c3880f44c7f348ac0c9f06668b5f57bae39b178b6c72'
EVIDENCE_SHA256 = 'e59f2538e565722680cb41c832a990e85b9d25e545b6703fb473d53452ba5357'
FIELDS = ('input_tokens', 'cached_input_tokens', 'cache_write_input_tokens', 'output_tokens', 'reasoning_output_tokens', 'total_tokens')
PUBLIC_MAP = dict(zip(FIELDS, ('input_tokens', 'cache_read_tokens', 'cache_creation_tokens', 'output_tokens', 'reasoning_output_tokens', 'total_tokens')))
CASES = ('bird-ca-schools-15', 'dabstep-payments-10', 'exercism-py-6', 'lcb-recent-hard-4', 'tb-cargo-plan')
SLOTS = tuple('codex__' + case + '__r' + str(rep) for case in CASES for rep in (1, 2, 3))


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def document(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def reject_constant(_):
    raise Invalid('nonfinite JSON number')


def finite_float(text):
    value = float(text)
    require(value == value and value not in (float('inf'), float('-inf')), 'nonfinite JSON number')
    return value


def loads(raw):
    try:
        return json.loads(raw, object_pairs_hook=unique_pairs, parse_constant=reject_constant, parse_float=finite_float)
    except (ValueError, UnicodeError, OverflowError) as error:
        raise Invalid('invalid JSON') from error


def keys(value, expected, label):
    require(isinstance(value, dict) and set(value) == set(expected), 'invalid schema: ' + label)


def integer(value, minimum=0):
    require(type(value) is int and value >= minimum, 'invalid integer')


def digest(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None, 'invalid SHA256')


def text_id(value):
    require(isinstance(value, str) and bool(value), 'missing identity')
    return value


def vector(value):
    keys(value, FIELDS, 'six-field usage')
    for field in FIELDS:
        integer(value[field])
    require(value['total_tokens'] == value['input_tokens'] + value['output_tokens'], 'usage total differs')
    require(value['cached_input_tokens'] <= value['input_tokens'], 'cached exceeds input')
    require(value['reasoning_output_tokens'] <= value['output_tokens'], 'reasoning exceeds output')
    return {field: value[field] for field in FIELDS}


def public_vector(value):
    require(isinstance(value, dict) and all(name in value for name in PUBLIC_MAP.values()), 'public usage field missing')
    return vector({field: value[name] for field, name in PUBLIC_MAP.items()})


def plus(a, b):
    return {field: a[field] + b[field] for field in FIELDS}


def safe_path(root, relative):
    require(isinstance(relative, str), 'relative path is not text')
    part = Path(relative)
    require(not part.is_absolute() and '..' not in part.parts and str(part) not in ('', '.'), 'unsafe relative path')
    root = root.resolve()
    path = (root / part).resolve()
    require(root in path.parents, 'path escaped root')
    return path


def pinned(path, expected):
    digest(expected)
    raw = path.read_bytes()
    require(sha(raw) == expected, 'pinned SHA differs')
    return raw


def trace(raw):
    lines = raw.decode('utf-8').split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    require(bool(lines), 'empty JSONL')
    result = []
    for line in lines:
        require(bool(line.strip()), 'blank JSONL record')
        event = loads(line)
        require(isinstance(event, dict) and isinstance(event.get('type'), str), 'bad JSONL event')
        result.append(event)
    return result


def projection(events):
    result = []
    for event in events:
        response = event['type'] == 'response_item'
        payload = event.get('payload')
        if response:
            require(isinstance(payload, dict) and isinstance(payload.get('type'), str), 'bad response item')
        result.append([event['type'], len(canon(event)), payload['type'] if response else None, len(canon(payload)) if response else 0])
    return result


def origin_paths(value, path=''):
    found = []
    if isinstance(value, dict):
        for name, item in value.items():
            require(isinstance(name, str) and re.fullmatch('[A-Za-z_][A-Za-z_0-9]*', name) is not None, 'unsafe schema field')
            current = path + '/' + name
            if any(term in name.lower() for term in ('source', 'origin', 'provider', 'estimat')):
                found.append(current)
            found.extend(origin_paths(item, current))
    elif isinstance(value, list):
        for item in value:
            found.extend(origin_paths(item, path + '/*'))
    return found


def schema_paths(value, path=''):
    result = [(path, type(value).__name__)]
    if isinstance(value, dict):
        for name, item in sorted(value.items()):
            require(re.fullmatch('[A-Za-z_][A-Za-z_0-9]*', name) is not None, 'unsafe schema field')
            result.extend(schema_paths(item, path + '/' + name))
    elif isinstance(value, list):
        for item in value:
            result.extend(schema_paths(item, path + '/*'))
    return tuple(sorted(set(result)))


def references(root):
    pinned(HERE / 'README.md', PROTOCOL_SHA256)
    source_bytes = pinned(HERE / 'SOURCES.json', SOURCES_SHA256)
    sources = loads(source_bytes)
    keys(sources, ('schema', 'selection', 'projection', 'slots'), 'fixed sources')
    require(sources['schema'] == 'first-product-usage-sources-v1', 'bad source schema')
    keys(sources['projection'], ('path', 'sha256'), 'projection source')
    fixed = loads(pinned(safe_path(root, sources['projection']['path']), sources['projection']['sha256']))
    dependencies = fixed['public_sources']
    require(isinstance(dependencies, list) and len(dependencies) == 69, 'public dependency denominator')
    dependency_map = {}
    for row in dependencies:
        keys(row, ('path', 'sha256'), 'public dependency')
        require(row['path'] not in dependency_map, 'duplicate dependency')
        pinned(safe_path(root, row['path']), row['sha256'])
        dependency_map[row['path']] = row['sha256']
    selected = [row for row in fixed['slots'] if row['slot'].startswith('codex__')]
    require([row['slot'] for row in selected] == list(SLOTS), 'projection selection/order differs')
    require(isinstance(sources['slots'], list) and [s.get('slot') for s in sources['slots']] == list(SLOTS), 'fixed slot selection differs')
    source_map = {}
    for row, original in zip(sources['slots'], selected):
        keys(row, ('slot', 'cli_relative_path', 'cli_sha256', 'public_meta_path', 'public_meta_sha256', 'raw_trace_locator', 'raw_trace_sha256'), 'source slot')
        require(row['raw_trace_locator'] == 'identity in pinned projection slot with this slot label', 'unsafe trace locator')
        require(row['raw_trace_sha256'] == original['identity']['sha256'], 'raw source pin differs from identity')
        require(dependency_map.get(row['public_meta_path']) == row['public_meta_sha256'], 'meta dependency pin differs')
        pinned(safe_path(root, row['public_meta_path']), row['public_meta_sha256'])
        safe_path(root, row['cli_relative_path'])  # Structural safety only; CLI is under archive-root.
        digest(row['cli_sha256'])
        source_map[row['slot']] = row
    return sources, dict((r['slot'], r) for r in selected), dependencies


def analyze_native(events, expected_projection):
    observed = projection(events)
    require(observed == expected_projection, 'all-event four-column projection differs')
    native = [(line, event) for line, event in enumerate(events, 1) if event['type'] == 'token_usage_record']
    mirror = [(line, event) for line, event in enumerate(events, 1) if event['type'] == 'event_msg' and isinstance(event.get('payload'), dict) and event['payload'].get('type') == 'token_count']
    require(bool(native) and len(native) == len(mirror), 'native/mirror denominator differs')
    cumulative = dict.fromkeys(FIELDS, 0)
    records, raw_ids, turns, threads, roots = [], [], set(), set(), set()
    schemas, origins, contexts = Counter(), Counter(), set()
    for ordinal, ((line, event), (mirror_line, mirrored)) in enumerate(zip(native, mirror), 1):
        p, m = event['payload'], mirrored['payload']
        require(isinstance(p, dict) and isinstance(m.get('info'), dict), 'bad usage payload')
        require({'usage', 'turn_token_usage', 'thread_token_usage', 'response_id', 'turn_id', 'thread_id', 'root_turn_id'} <= set(p), 'native usage identity/field missing')
        require({'last_token_usage', 'total_token_usage', 'model_context_window'} <= set(m['info']), 'mirror field missing')
        usage = vector(p['usage'])
        cumulative = plus(cumulative, usage)
        require(vector(p['turn_token_usage']) == vector(p['thread_token_usage']) == cumulative, 'cumulative prefix/reset differs')
        info = m['info']
        require(vector(info['last_token_usage']) == usage and vector(info['total_token_usage']) == cumulative, 'duplicate view differs')
        require(line < mirror_line, 'mirror order differs')
        if ordinal < len(native):
            require(mirror_line < native[ordinal][0], 'interleaved mirror order differs')
        response = text_id(p['response_id'])
        raw_ids.append(response)
        turns.add(text_id(p['turn_id']))
        threads.add(text_id(p['thread_id']))
        roots.add(text_id(p['root_turn_id']))
        integer(info['model_context_window'])
        contexts.add(info['model_context_window'])
        for family, value in (('native_event', event), ('mirror_event', mirrored)):
            schemas[(family, schema_paths(value))] += 1
            origins.update(origin_paths(value, '/' + family))
        records.append({'ordinal': ordinal, 'usage_line': line, 'mirror_line': mirror_line, 'usage': usage, 'cumulative': dict(cumulative), 'response_id_sha256': sha(response.encode()), 'turn_id_sha256': sha(p['turn_id'].encode()), 'thread_id_sha256': sha(p['thread_id'].encode()), 'native_event_sha256': sha(canon(event)), 'mirror_event_sha256': sha(canon(mirrored))})
    require(len(set(raw_ids)) == len(raw_ids), 'duplicate response identity')
    require(len(turns) == len(threads) == len(roots) == 1, 'multiple turn/thread/root scope')
    require(not any(e['type'] == 'response_item' for e in events[native[-1][0]:]), 'uncovered response item after final usage')
    complete = [(line, e['payload']) for line, e in enumerate(events, 1) if e['type'] == 'event_msg' and isinstance(e.get('payload'), dict) and e['payload'].get('type') == 'task_complete']
    require(len(complete) == 1 and complete[0][0] > mirror[-1][0], 'task completion not covered')
    terminal_line, terminal = complete[0]
    require(terminal.get('turn_id') in turns and terminal.get('root_turn_id') in roots, 'task completion identity differs')
    r3 = sum(row[3] for row in observed if row[0] == 'response_item')
    return {'event_count': len(events), 'response_item_count': sum(row[0] == 'response_item' for row in observed), 'four_column_projection_sha256': sha(canon(observed)), 'r3_payload_bytes': r3, 'records': records, 'terminal_cumulative': cumulative, 'coverage': {'unique_response_ids': len(raw_ids), 'turns': len(turns), 'threads': len(threads), 'last_usage_line': native[-1][0], 'last_mirror_line': mirror[-1][0], 'task_complete_line': terminal_line, 'uncovered_response_items': 0, 'critical_gates_valid': True}, 'model_context_window_values': sorted(contexts), 'schema_signatures': [{'family': family, 'paths': [list(p) for p in paths], 'count': count} for (family, paths), count in sorted(schemas.items())], 'provenance_field_paths': dict(sorted(origins.items()))}, raw_ids


def analyze_cli(events, cumulative):
    completed = [(line, event) for line, event in enumerate(events, 1) if event['type'] == 'turn.completed']
    require(len(completed) == 1 and completed[0][0] == len(events), 'CLI final event scope differs')
    value = completed[0][1].get('usage')
    keys(value, set(FIELDS) - {'total_tokens'}, 'CLI five fields')
    for name in value:
        integer(value[name])
        require(value[name] == cumulative[name], 'CLI terminal differs')
    return {'event_count': len(events), 'turn_completed_line': completed[0][0], 'usage': value, 'all_five_equal_native_terminal': True, 'total_tokens': {'availability': 'NOT_PROVIDED', 'value': None}}


def analyze_meta(meta, own_vectors, own_ids, terminal):
    require(isinstance(meta, dict) and isinstance(meta.get('per_call'), list), 'bad metadata usage')
    rows = meta['per_call']
    integer(meta.get('requests'))
    require(meta['requests'] == len(rows) >= len(own_vectors), 'meta per-call count differs')
    values = [public_vector(row) for row in rows]
    ids = [text_id(row.get('response_id')) for row in rows]
    own_count = len(own_vectors)
    require(values[-own_count:] == own_vectors and ids[-own_count:] == own_ids, 'meta own suffix identity/numeric differs')
    cumulative = vector(meta['cumulative_thread_final'])
    require(cumulative == terminal, 'meta own terminal differs')
    aggregate = public_vector(meta)
    require(aggregate == {field: sum(row[field] for row in values) for field in FIELDS}, 'meta entire-list aggregate differs')
    extra = len(rows) - own_count
    return {'requests': meta['requests'], 'per_call': [{'usage': usage, 'response_id_sha256': sha(identity.encode())} for usage, identity in zip(values, ids)], 'extra_prefix_count': extra, 'own_slot_suffix_equal': True, 'cumulative_thread_final': cumulative, 'reported_aggregate': aggregate, 'aggregate_minus_own_terminal': {field: aggregate[field] - terminal[field] for field in FIELDS}, 'prefix_scope': 'PENDING', 'prefix_matches_slots': []}, (values[:extra], ids[:extra])


def rebuild(root, archive_root, source_rows, selected, dependencies):
    slots, identities = [], {}
    read_sources = []
    for source in source_rows['slots']:
        slot = source['slot']
        original = selected[slot]
        relative = original['identity']['source_relative_to_archive']
        raw_path = safe_path(archive_root, relative)
        raw = pinned(raw_path, source['raw_trace_sha256'])
        events = trace(raw)
        session = [e for e in events if e['type'] == 'session_meta']
        require(len(session) == 1 and session[0].get('payload', {}).get('id') == original['identity']['id'], 'main archive session identity differs')
        require(all(e.get('payload', {}).get('session_id') == original['identity']['id'] for e in events if e['type'] == 'token_usage_record'), 'usage session identity differs')
        analyzed, ids = analyze_native(events, original['events'])
        cli_path = safe_path(archive_root, source['cli_relative_path'])
        cli_bytes = pinned(cli_path, source['cli_sha256'])
        cli = analyze_cli(trace(cli_bytes), analyzed['terminal_cumulative'])
        metadata = loads(pinned(safe_path(root, source['public_meta_path']), source['public_meta_sha256']))['usage']
        meta, prefix = analyze_meta(metadata, [r['usage'] for r in analyzed['records']], ids, analyzed['terminal_cumulative'])
        case, rep = slot.split('__')[1:]
        slots.append({'slot': slot, 'case': case, 'rep': int(rep[1:]), 'sources': source, 'native': analyzed, 'cli': cli, 'public_meta': meta})
        identities[slot] = {'own': ([r['usage'] for r in analyzed['records']], ids), 'prefix': prefix}
        read_sources.extend(((raw_path, source['raw_trace_sha256']), (cli_path, source['cli_sha256'])))
    for slot in slots:
        current = slot['slot']
        prefix = identities[current]['prefix']
        matches = [other for other in SLOTS if other != current and identities[other]['own'] == prefix]
        meta = slot['public_meta']
        meta['prefix_matches_slots'] = matches
        meta['prefix_scope'] = 'NONE' if meta['extra_prefix_count'] == 0 else ('KNOWN_SLOT_PREFIX' if len(matches) == 1 else 'UNKNOWN')
    for path, expected in read_sources:
        pinned(path, expected)
    for row in dependencies:
        pinned(safe_path(root, row['path']), row['sha256'])
    return {'schema': 'first-product-usage-evidence-v1', 'baseline_commit': BASELINE, 'protocol_sha256': PROTOCOL_SHA256, 'sources_sha256': SOURCES_SHA256, 'projection': source_rows['projection'], 'slots': slots}


def validate_slot(slot, source, original):
    keys(slot, ('slot', 'case', 'rep', 'sources', 'native', 'cli', 'public_meta'), 'evidence slot')
    require(slot['slot'] == source['slot'] and slot['sources'] == source, 'slot source differs')
    require(slot['case'] == slot['slot'].split('__')[1] and type(slot['rep']) is int and slot['rep'] == int(slot['slot'][-1]), 'slot identity differs')
    native = slot['native']
    keys(native, ('event_count', 'response_item_count', 'four_column_projection_sha256', 'r3_payload_bytes', 'records', 'terminal_cumulative', 'coverage', 'model_context_window_values', 'schema_signatures', 'provenance_field_paths'), 'native projection')
    expected = original['events']
    for field in ('event_count', 'response_item_count', 'r3_payload_bytes'):
        integer(native[field])
    require(native['event_count'] == len(expected) and native['four_column_projection_sha256'] == sha(canon(expected)), 'all-event binding differs')
    require(native['response_item_count'] == sum(e[0] == 'response_item' for e in expected) and native['r3_payload_bytes'] == sum(e[3] for e in expected if e[0] == 'response_item'), 'R3 byte accounting differs')
    require(isinstance(native['records'], list) and bool(native['records']), 'missing native records')
    require([row.get('usage_line') for row in native['records']] == [line for line, row in enumerate(expected, 1) if row[0] == 'token_usage_record'], 'native event coverage differs')
    running = dict.fromkeys(FIELDS, 0)
    ids, turns, threads, used_lines = set(), set(), set(), set()
    previous_mirror = 0
    for ordinal, row in enumerate(native['records'], 1):
        keys(row, ('ordinal', 'usage_line', 'mirror_line', 'usage', 'cumulative', 'response_id_sha256', 'turn_id_sha256', 'thread_id_sha256', 'native_event_sha256', 'mirror_event_sha256'), 'record')
        integer(row['ordinal'], 1)
        require(row['ordinal'] == ordinal, 'record order differs')
        for name in ('usage_line', 'mirror_line'):
            line = row[name]
            integer(line, 1)
            require(line <= len(expected) and line not in used_lines, 'duplicate/out-of-range source line')
            used_lines.add(line)
        require(previous_mirror < row['usage_line'] < row['mirror_line'], 'projected record/mirror order differs')
        require(expected[row['usage_line'] - 1][0] == 'token_usage_record' and expected[row['mirror_line'] - 1][0] == 'event_msg', 'source line event family differs')
        previous_mirror = row['mirror_line']
        running = plus(running, vector(row['usage']))
        require(vector(row['cumulative']) == running, 'public cumulative prefix differs')
        for name in ('response_id_sha256', 'turn_id_sha256', 'thread_id_sha256', 'native_event_sha256', 'mirror_event_sha256'):
            digest(row[name])
        require(row['response_id_sha256'] not in ids, 'public duplicate response identity')
        ids.add(row['response_id_sha256'])
        turns.add(row['turn_id_sha256'])
        threads.add(row['thread_id_sha256'])
    require(len(turns) == len(threads) == 1, 'public multiple identity scope')
    require(vector(native['terminal_cumulative']) == running, 'public final cumulative differs')
    coverage = native['coverage']
    keys(coverage, ('unique_response_ids', 'turns', 'threads', 'last_usage_line', 'last_mirror_line', 'task_complete_line', 'uncovered_response_items', 'critical_gates_valid'), 'coverage')
    for field in set(coverage) - {'critical_gates_valid'}:
        integer(coverage[field])
    require(coverage['critical_gates_valid'] is True and coverage['uncovered_response_items'] == 0, 'invalid critical gate')
    require(coverage['unique_response_ids'] == len(ids) and coverage['turns'] == coverage['threads'] == 1, 'identity denominator differs')
    require(coverage['last_usage_line'] == native['records'][-1]['usage_line'] and coverage['last_mirror_line'] == previous_mirror, 'terminal lines differ')
    integer(coverage['task_complete_line'], 1)
    require(previous_mirror < coverage['task_complete_line'] <= len(expected) and expected[coverage['task_complete_line'] - 1][0] == 'event_msg', 'completion line differs')
    require(not any(row[0] == 'response_item' for row in expected[coverage['last_usage_line']:]), 'public uncovered response item')
    require(isinstance(native['model_context_window_values'], list) and bool(native['model_context_window_values']), 'missing context labels')
    for value in native['model_context_window_values']:
        integer(value)
    require(isinstance(native['schema_signatures'], list) and isinstance(native['provenance_field_paths'], dict), 'bad schema description')
    family_counts = Counter()
    for signature in native['schema_signatures']:
        keys(signature, ('family', 'paths', 'count'), 'schema signature')
        require(signature['family'] in ('native_event', 'mirror_event'), 'bad schema family')
        integer(signature['count'], 1)
        family_counts[signature['family']] += signature['count']
        require(isinstance(signature['paths'], list) and bool(signature['paths']), 'missing schema paths')
        for path, typ in signature['paths']:
            require(isinstance(path, str) and re.fullmatch(r'(?:/[A-Za-z_][A-Za-z_0-9]*|/\*)*', path) is not None and typ in ('dict', 'list', 'str', 'int', 'float', 'bool', 'NoneType'), 'unsafe schema path/type')
    require(family_counts == {'native_event': len(ids), 'mirror_event': len(ids)}, 'schema denominator differs')
    for path, count in native['provenance_field_paths'].items():
        require(re.fullmatch(r'(?:/[A-Za-z_][A-Za-z_0-9]*|/\*)+', path) is not None, 'unsafe provenance path')
        integer(count, 1)
    cli = slot['cli']
    keys(cli, ('event_count', 'turn_completed_line', 'usage', 'all_five_equal_native_terminal', 'total_tokens'), 'CLI')
    integer(cli['event_count'], 1)
    integer(cli['turn_completed_line'], 1)
    require(cli['turn_completed_line'] == cli['event_count'] and cli['all_five_equal_native_terminal'] is True and cli['total_tokens'] == {'availability': 'NOT_PROVIDED', 'value': None}, 'CLI coverage/availability differs')
    keys(cli['usage'], set(FIELDS) - {'total_tokens'}, 'CLI available fields')
    for field, value in cli['usage'].items():
        integer(value)
        require(value == running[field], 'public CLI terminal differs')
    meta = slot['public_meta']
    keys(meta, ('requests', 'per_call', 'extra_prefix_count', 'own_slot_suffix_equal', 'cumulative_thread_final', 'reported_aggregate', 'aggregate_minus_own_terminal', 'prefix_scope', 'prefix_matches_slots'), 'meta scope')
    integer(meta['requests'])
    integer(meta['extra_prefix_count'])
    require(isinstance(meta['per_call'], list) and meta['requests'] == len(meta['per_call']) == len(ids) + meta['extra_prefix_count'], 'meta count differs')
    for row in meta['per_call']:
        keys(row, ('usage', 'response_id_sha256'), 'meta safe row')
        vector(row['usage'])
        digest(row['response_id_sha256'])
    own = [{'usage': row['usage'], 'response_id_sha256': row['response_id_sha256']} for row in native['records']]
    require(meta['own_slot_suffix_equal'] is True and meta['per_call'][-len(own):] == own, 'public meta suffix differs')
    require(vector(meta['cumulative_thread_final']) == running, 'public meta own terminal differs')
    aggregate = vector(meta['reported_aggregate'])
    require(aggregate == {field: sum(row['usage'][field] for row in meta['per_call']) for field in FIELDS}, 'public meta list aggregate differs')
    keys(meta['aggregate_minus_own_terminal'], FIELDS, 'meta scope difference')
    require(all(type(value) is int for value in meta['aggregate_minus_own_terminal'].values()), 'noninteger meta difference')
    require(meta['aggregate_minus_own_terminal'] == {field: aggregate[field] - running[field] for field in FIELDS}, 'meta scope difference differs')


def validate_evidence(evidence, source_rows, selected):
    keys(evidence, ('schema', 'baseline_commit', 'protocol_sha256', 'sources_sha256', 'projection', 'slots'), 'evidence')
    require(evidence['schema'] == 'first-product-usage-evidence-v1' and evidence['baseline_commit'] == BASELINE and evidence['protocol_sha256'] == PROTOCOL_SHA256 and evidence['sources_sha256'] == SOURCES_SHA256 and evidence['projection'] == source_rows['projection'], 'evidence contract differs')
    require(isinstance(evidence['slots'], list) and [s.get('slot') for s in evidence['slots']] == list(SLOTS), 'evidence slot coverage differs')
    for slot, source in zip(evidence['slots'], source_rows['slots']):
        validate_slot(slot, source, selected[slot['slot']])
    for slot in evidence['slots']:
        meta = slot['public_meta']
        prefix = meta['per_call'][:meta['extra_prefix_count']]
        matches = [other['slot'] for other in evidence['slots'] if other['slot'] != slot['slot'] and [{'usage': row['usage'], 'response_id_sha256': row['response_id_sha256']} for row in other['native']['records']] == prefix]
        expected = 'NONE' if not prefix else ('KNOWN_SLOT_PREFIX' if len(matches) == 1 else 'UNKNOWN')
        require(meta['prefix_matches_slots'] == matches and meta['prefix_scope'] == expected, 'meta exact prefix scope differs')


def endpoint(values, eligible):
    require(type(eligible) is bool, 'endpoint eligibility is not boolean')
    if not eligible:
        return {'status': 'UNKNOWN', 'values': None, 'equal': None}
    require(len(values) == 3, 'endpoint requires three fixed reps')
    for value in values:
        integer(value)
    return {'status': 'EQUAL' if len(set(values)) == 1 else 'NOT_EQUAL', 'values': values, 'equal': len(set(values)) == 1}


def result_for(evidence, evidence_sha):
    groups = []
    for case in CASES:
        slots = [row for row in evidence['slots'] if row['case'] == case]
        require([row['rep'] for row in slots] == [1, 2, 3], 'group reps differ')
        eligible = all(row['native']['coverage']['critical_gates_valid'] is True for row in slots)
        groups.append({'case': case, 'first_input': endpoint([s['native']['records'][0]['usage']['input_tokens'] for s in slots], eligible), 'first_cached': endpoint([s['native']['records'][0]['usage']['cached_input_tokens'] for s in slots], eligible), 'first_reasoning': endpoint([s['native']['records'][0]['usage']['reasoning_output_tokens'] for s in slots], eligible)})
    slots = evidence['slots']
    records = [record for slot in slots for record in slot['native']['records']]
    endpoints = {}
    for field in ('first_cached', 'first_reasoning', 'first_input'):
        endpoints[field] = {'equal_groups': sum(g[field]['status'] == 'EQUAL' for g in groups), 'not_equal_groups': sum(g[field]['status'] == 'NOT_EQUAL' for g in groups), 'unknown_groups': sum(g[field]['status'] == 'UNKNOWN' for g in groups), 'eligible_groups': sum(g[field]['status'] != 'UNKNOWN' for g in groups), 'fixed_groups': 5}
    return {'schema': 'first-product-usage-result-v1', 'baseline_commit': BASELINE, 'protocol_sha256': PROTOCOL_SHA256, 'sources_sha256': SOURCES_SHA256, 'evidence_sha256': evidence_sha, 'analysis_identity': 'post-exploration fixed replay; prior all-group results exposed; not a new trial or provider attestation', 'coverage': {'slots': len(slots), 'groups': len(groups), 'public_dependencies_pinned': 69, 'native_usage_records': len(records), 'mirror_duplicate_views': len(records), 'cli_final_matches': len(slots), 'cli_total_tokens_availability': 'NOT_PROVIDED', 'r3_response_items': sum(s['native']['response_item_count'] for s in slots), 'r3_payload_bytes': sum(s['native']['r3_payload_bytes'] for s in slots), 'meta_own_slot_only': sum(s['public_meta']['prefix_scope'] == 'NONE' for s in slots), 'meta_known_other_slot_prefix': sum(s['public_meta']['prefix_scope'] == 'KNOWN_SLOT_PREFIX' for s in slots), 'meta_unknown_prefix': sum(s['public_meta']['prefix_scope'] == 'UNKNOWN' for s in slots), 'meta_listed_rows': sum(s['public_meta']['requests'] for s in slots), 'meta_extra_rows_not_trials': sum(s['public_meta']['extra_prefix_count'] for s in slots)}, 'field_states': {field: {'missing': 0, 'null': 0, 'explicit_zero': sum(r['usage'][field] == 0 for r in records), 'present_nonzero': sum(r['usage'][field] != 0 for r in records)} for field in FIELDS}, 'endpoints': endpoints, 'groups': groups, 'slot_accounting': [{'slot': s['slot'], 'r3_payload_bytes': s['native']['r3_payload_bytes'], 'product_reported_terminal': s['native']['terminal_cumulative'], 'actual_request_bytes': {'status': 'UNKNOWN', 'value': None}, 'meta_scope': s['public_meta']['prefix_scope'], 'meta_prefix_matches_slots': s['public_meta']['prefix_matches_slots']} for s in slots], 'limits': ['Product counters and duplicated local views do not authenticate provider usage, estimation method, HTTP attempts or actual thinking/cache.', 'Equal first input counts do not imply equal bytes, text or backend context.', 'Meta aggregate includes all listed rows; known extra prefixes are not additional trials; original metadata is unchanged.', 'No causal warming/Harness/model/cost claim; R3 payload bytes, reported counts and unknown request bytes remain separate.', 'Missing/null/invalid identity/cumulative/terminal is hard failure or UNKNOWN, never a zero unequal-group result.', 'Public replay checks sealed projection arithmetic; archive rebuild checks actual source relations; neither authenticates historical originals.']}


def output_path(path):
    require('..' not in path.parts, 'unsafe output path')
    require(not path.exists() and not path.is_symlink(), 'exclusive output already exists')
    require(path.parent.is_dir() and path.parent.absolute() == path.parent.resolve(), 'unsafe output parent')
    return path


def exclusive(path, raw):
    with path.open('xb') as handle:
        handle.write(raw)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--archive-root', type=Path)
    parser.add_argument('--build-evidence', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        sources, selected, dependencies = references(args.root)
        if args.build_evidence:
            require(args.archive_root is not None, 'build requires archive-root')
            evidence = rebuild(args.root, args.archive_root, sources, selected, dependencies)
            raw = document(evidence)
            require(sha(raw) == EVIDENCE_SHA256, 'rebuilt evidence seal differs')
        else:
            raw = pinned(HERE / 'evidence.json', EVIDENCE_SHA256)
            evidence = loads(raw)
            if args.archive_root:
                require(canon(rebuild(args.root, args.archive_root, sources, selected, dependencies)) == canon(evidence), 'raw rebuild differs from published evidence')
        validate_evidence(evidence, sources, selected)
        result = result_for(evidence, sha(raw))
        result_raw = document(result)
        destinations = [args.output] + ([args.build_evidence] if args.build_evidence else [])
        require(len({p.resolve() for p in destinations}) == len(destinations), 'duplicate output destinations')
        for path in destinations:
            output_path(path)
        if args.build_evidence:
            exclusive(args.build_evidence, raw)
        exclusive(args.output, result_raw)
        print(json.dumps({'status': 'PASS', 'result_sha256': sha(result_raw), 'coverage': result['coverage'], 'endpoints': result['endpoints']}, ensure_ascii=False, sort_keys=True))
        return 0
    except (Invalid, OSError, ValueError, TypeError, KeyError, SyntaxError, OverflowError, RecursionError) as error:
        print('INVALID: ' + (str(error) if isinstance(error, Invalid) else 'input or output failure'), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
