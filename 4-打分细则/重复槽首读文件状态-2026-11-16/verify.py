#!/usr/bin/env python3
"""Read-only fixed-source analysis. Public mode: standard library only.
Raw mode additionally needs zstandard. Never executes/imports archived material.
Outputs are exclusive, sequential and non-transactional; a later failure may leave
an earlier newly created output. No authenticity or exclusive-writer claim.
"""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import posixpath
import re
import sys

HERE = '4-打分细则/重复槽首读文件状态-2026-11-16'
SOURCES_SHA = '89f3828a2b7facce2ff20fadc2dae11615fcbfcb93601907c73f72cf89282a39'
README_SHA = 'c0ca8ef892eceeac822ab80e5828becbd297dfa41d1b5b098beaeb9b0bd55fe3'
EVIDENCE_SHA = '53e810ad0d8d4c5d567ad4e9551096ff739d58258b80c73783be4fe7d18136f4'
TARGET = 'inputs/exercises/dominoes/dominoes.py'
OLD_EVIDENCE = '4-打分细则/机制重复口径澄清-2026-11-12/evidence.json'

class Invalid(ValueError):
    pass

def require(ok, message):
    if not ok:
        raise Invalid(message)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')

def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result

def bad_constant(value):
    raise Invalid('nonfinite JSON number')

def finite_float(value):
    number = float(value)
    require(math.isfinite(number), 'nonfinite JSON number')
    return number

def load(raw):
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=bad_constant, parse_float=finite_float)
    except (ValueError, UnicodeError, TypeError) as error:
        raise Invalid('invalid JSON') from error

def integer(value):
    require(type(value) is int and value >= 0, 'invalid integer')
    return value

def digest(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value), 'invalid digest')
    return value

def keys(value, expected):
    require(type(value) is dict and set(value) == set(expected.split()), 'invalid object fields')

def safe(root, relative):
    require(type(relative) is str and relative and '\\' not in relative, 'invalid relative path')
    path = PurePosixPath(relative)
    require(not path.is_absolute() and '..' not in path.parts and str(path) == relative,
            'unsafe relative path')
    absolute = (root / relative).resolve()
    require(root in absolute.parents, 'source escapes root')
    return absolute

def bound(root, relative, expected):
    raw = safe(root, relative).read_bytes()
    require(sha(raw) == digest(expected), 'source digest mismatch')
    return raw

def pin(raw):
    return {'bytes': len(raw), 'sha256': sha(raw)}

def check_pin(value):
    keys(value, 'bytes sha256')
    integer(value['bytes']); digest(value['sha256'])

def public_sources(root):
    root = Path(root).resolve()
    bound(root, HERE + '/README.md', README_SHA)
    source = load(bound(root, HERE + '/SOURCES.json', SOURCES_SHA))
    require(source['schema'] == 'first-read-file-state-sources-v1' and
            source['target_relative_path'] == TARGET, 'source schema mismatch')
    contents = {}
    require(len(source['public_sources']) == 6, 'public source coverage')
    for row in source['public_sources']:
        relative = row['relative_path']
        require(relative not in contents, 'duplicate public source')
        contents[relative] = bound(root, relative, row['sha256'])
    legacy = load(contents[OLD_EVIDENCE])
    require(legacy['schema'] == 'r1109-content-free-projection-v1.1', 'legacy schema mismatch')
    deps = legacy['public_sources']
    require(len(deps) == 69 and len({r['path'] for r in deps}) == 69, 'legacy dependency coverage')
    for row in deps:
        bound(root, row['path'], row['sha256'])
    selected = []
    for spec in source['slots']:
        rows = [r for r in legacy['slots'] if r['slot'] == spec['slot']]
        require(len(rows) == 1, 'legacy slot coverage')
        row = rows[0]
        require(row['identity']['source_relative_to_archive'] == spec['archive_relative_path'] and
                row['identity']['sha256'] == spec['archive_sha256'] and
                row['identity']['version'] == 4, 'legacy archive identity')
        for projection in row['events']:
            require(type(projection) is list and len(projection) == 4 and
                    type(projection[0]) is str and projection[2] is None and
                    type(projection[3]) is int and projection[3] == 0, 'legacy projection schema')
            require(integer(projection[1]) > 0, 'legacy projection length')
        selected.append(row)
        meta_path = '3-表现现场/r1109-mech-n3/runs/' + spec['slot'] + '/meta.public-derived.json'
        meta = load(contents[meta_path])
        targets = [r for r in meta['inputs'] if r['path'] == TARGET]
        require(len(targets) == 1 and type(targets[0]['bytes']) is int and
                targets[0]['bytes'] == 34 and targets[0]['sha256'] == source['public_sources'][1]['sha256'],
                'nominal inherited input mismatch')
    require([r['slot'] for r in selected] == ['dsh__exercism-py-6__r2', 'dsh__exercism-py-6__r3'], 'slot order')
    nominal = contents[source['public_sources'][1]['relative_path']]
    require(len(nominal) == 34, 'nominal length')
    return source, selected, pin(nominal)

def arguments(value):
    parsed = load(value) if type(value) is str else value
    require(type(parsed) is dict, 'invalid tool arguments')
    return parsed

def message_text(message):
    require(type(message.get('isError')) is bool, 'missing result status')
    require(type(message.get('content')) is list, 'invalid result content')
    parts = []
    for block in message['content']:
        require(type(block) is dict and type(block.get('type')) is str, 'invalid content block')
        if block['type'] == 'text':
            require(type(block.get('text')) is str, 'invalid text block')
            parts.append(block['text'])
    return ''.join(parts).encode('utf-8')

def slice_state(raw, start, end):
    start = start.encode('utf-8'); end = end.encode('utf-8')
    starts = list(re.finditer(b'^' + re.escape(start), raw, re.M))
    ends = list(re.finditer(b'^' + re.escape(end), raw, re.M))
    require(len(starts) == len(ends) == 1, 'ambiguous or missing read boundary')
    a = starts[0].end(); b = ends[0].start()
    require(a < b, 'reversed read boundary')
    following = re.search(b'^===== [a-z]+ README =====\n', raw[a:], re.M)
    require(following is not None and a + following.start() == b, 'unexpected next boundary')
    state = raw[a:b]
    return state, {'start': a, 'end': b, 'envelope': pin(raw)}

def exact_replace(state, old, new):
    require(type(old) is bytes and type(new) is bytes and old and old != new, 'invalid replacement')
    require(state.count(old) == 1, 'replacement not unique')
    return state.replace(old, new, 1)

def link_events(events):
    require(type(events) is list and len(events) > 1 and events[0]['type'] == 'session', 'invalid session')
    require(events[0].get('version') == 4, 'invalid session version')
    calls = {}; results = {}; ordered = []
    for index, event in enumerate(events[1:]):
        require(type(event.get('seq')) is int and event['seq'] == index, 'event sequence mismatch')
        data = event.get('data', {})
        if event['type'] == 'tool/call':
            call_id = data['callId']
            require(type(call_id) is str and call_id and call_id not in calls, 'duplicate call association')
            calls[call_id] = event; ordered.append(event)
            arguments(data['arguments'])
        elif event['type'] == 'tool/result':
            msg = data['message']; call_id = msg['toolCallId']
            require(call_id in calls and call_id not in results, 'invalid result association')
            require(msg.get('source', {}).get('callId') == call_id and
                    event.get('sourceEventSeqs') == [calls[call_id]['seq']], 'result provenance mismatch')
            message_text(msg); results[call_id] = event
    require(set(calls) == set(results), 'missing tool result')
    return ordered, results

def prefix_check(events, ordered, end_seq):
    prefix = [c for c in ordered if c['seq'] <= end_seq]
    assistant = []
    for event in events:
        if event.get('seq', -1) > end_seq or event['type'] != 'assistant/message':
            continue
        for block in event['data']['message']['content']:
            if block.get('type') == 'tool-call':
                assistant.append((block['id'], block['name'], arguments(block['arguments'])))
    actual = [(c['data']['callId'], c['data']['name'], arguments(c['data']['arguments'])) for c in prefix]
    require(assistant == actual and len(prefix) == 2, 'assistant prefix mismatch')
    return prefix

def raw_slot(events, spec, legacy, boundaries, lines):
    projection = [[e['type'], len(canon(e)), None, 0] for e in events]
    require(projection == legacy['events'], 'full legacy projection mismatch')
    require(events[0].get('id') == legacy['identity']['id'], 'session identity mismatch')
    ordered, results = link_events(events)
    prefix = prefix_check(events, ordered, spec['read_result_seq'])
    first = []
    for call, expected in zip(prefix, spec['first_two_calls']):
        data = call['data']; args = arguments(data['arguments'])
        require(call['seq'] == expected['seq'] and data['name'] == expected['name'] and
                sha(canon(args)) == expected['arguments_sha256'], 'fixed read command mismatch')
        # Hash-allowlisted, manually inspected ls/find/head and for/echo/cat commands;
        # no generic shell parser and no command execution.
        result = results[data['callId']]
        require(result['seq'] == call['seq'] + 1 and result['data']['message']['isError'] is False,
                'read command failed or reordered')
        first.append({'call_seq': call['seq'], 'result_seq': result['seq'], 'name': data['name'],
                      'arguments_sha256': sha(canon(args)), 'is_error': False,
                      'call_line_sha256': sha(lines[call['seq'] + 1]),
                      'result_line_sha256': sha(lines[result['seq'] + 1])})
    read = results[prefix[-1]['data']['callId']]
    rep = spec['slot'][-2:]
    state, boundary = slice_state(message_text(read['data']['message']), boundaries['start'], boundaries[rep + '_end'])
    row = {'slot': spec['slot'], 'archive_relative_path': spec['archive_relative_path'],
           'archive_sha256': spec['archive_sha256'], 'event_count': len(events),
           'event_projection_sha256': sha(canon(projection)), 'first_calls': first,
           'assistant_prefix_calls': 2, 'assistant_prefix_equal': True,
           'real_id_join_unique': True, 'boundary': boundary, 'observed': pin(state)}
    return row, state, ordered, results

def build(archive_root, source, legacy, nominal):
    try:
        import zstandard
    except ImportError as error:
        raise Invalid('raw mode needs zstandard') from error
    archive_root = Path(archive_root).resolve()
    rows = []; states = []; r2 = None
    for spec, prior in zip(source['slots'], legacy):
        raw = bound(archive_root, spec['archive_relative_path'], spec['archive_sha256'])
        with zstandard.ZstdDecompressor().stream_reader(io.BytesIO(raw)) as reader:
            decoded = reader.read()
        require(decoded.endswith(b'\n'), 'truncated JSONL')
        lines = decoded[:-1].split(b'\n')
        require(all(lines), 'empty JSONL row')
        events = [load(line) for line in lines]
        row, state, calls, results = raw_slot(events, spec, prior, source['read_boundaries'], lines)
        rows.append(row); states.append(state)
        if r2 is None:
            r2 = (events, calls, results)
    events, calls, results = r2
    edits = [c for c in calls if c['data']['name'] == 'edit']
    require(len(edits) == 3, 'edit coverage mismatch')
    attempts = []; successful = None
    cwd = events[0]['cwd']
    expected_path = posixpath.join(cwd, TARGET)
    for index, (call, expected) in enumerate(zip(edits, source['r2_edit_attempts'])):
        data = call['data']; args = arguments(data['arguments']); result = results[data['callId']]
        require(call['seq'] == expected['call_seq'] and result['seq'] == expected['result_seq'] and
                sha(canon(args)) == expected['arguments_sha256'] and
                result['data']['message']['isError'] is expected['is_error'], 'edit attempt mismatch')
        path = args['file_path']
        require(type(path) is str and path.endswith('/' + TARGET), 'edit target suffix mismatch')
        if index == 0:
            require(posixpath.normpath(path) != expected_path and '/../' in path, 'failed path mismatch')
        else:
            require(path == expected_path, 'edit target ownership mismatch')
        attempts.append({'call_seq': call['seq'], 'result_seq': result['seq'],
                         'arguments_sha256': expected['arguments_sha256'], 'is_error': expected['is_error'],
                         'target_relative_path': TARGET, 'matches_session_target': index != 0})
        if expected['is_error'] is False:
            successful = args
    require(successful is not None, 'missing successful edit')
    old = successful['old_string'].encode('utf-8'); new = successful['new_string'].encode('utf-8')
    predicted = exact_replace(states[0], old, new)
    replacement = {'old': pin(old), 'new': pin(new), 'occurrences_in_r2': states[0].count(old),
                   'predicted': pin(predicted), 'predicted_equals_r3': predicted == states[1]}
    return {'schema': 'first-read-file-state-evidence-v1', 'target_relative_path': TARGET,
            'nominal': nominal, 'slots': rows, 'r2_edit_attempts': attempts, 'replacement': replacement}

def validate(evidence, source, legacy, nominal):
    keys(evidence, 'schema target_relative_path nominal slots r2_edit_attempts replacement')
    require(evidence['schema'] == 'first-read-file-state-evidence-v1' and
            evidence['target_relative_path'] == TARGET, 'evidence schema mismatch')
    check_pin(evidence['nominal']); require(evidence['nominal'] == nominal, 'nominal evidence mismatch')
    require(type(evidence['slots']) is list and len(evidence['slots']) == 2, 'evidence slot coverage')
    for row, spec, prior in zip(evidence['slots'], source['slots'], legacy):
        keys(row, 'slot archive_relative_path archive_sha256 event_count event_projection_sha256 first_calls assistant_prefix_calls assistant_prefix_equal real_id_join_unique boundary observed')
        require(row['slot'] == spec['slot'] and row['archive_relative_path'] == spec['archive_relative_path'] and
                row['archive_sha256'] == spec['archive_sha256'], 'evidence source binding')
        require(integer(row['event_count']) == len(prior['events']) and
                row['event_projection_sha256'] == sha(canon(prior['events'])), 'event projection binding')
        require(type(row['assistant_prefix_calls']) is int and row['assistant_prefix_calls'] == 2 and
                row['assistant_prefix_equal'] is True and row['real_id_join_unique'] is True, 'prefix structure')
        require(type(row['first_calls']) is list and len(row['first_calls']) == 2, 'prefix call coverage')
        for call, expected in zip(row['first_calls'], spec['first_two_calls']):
            keys(call, 'call_seq result_seq name arguments_sha256 is_error call_line_sha256 result_line_sha256')
            require(integer(call['call_seq']) == expected['seq'] and
                    integer(call['result_seq']) == expected['seq'] + 1 and call['name'] == expected['name'] and
                    call['arguments_sha256'] == expected['arguments_sha256'] and call['is_error'] is False, 'call structure')
            digest(call['call_line_sha256']); digest(call['result_line_sha256'])
        keys(row['boundary'], 'start end envelope')
        boundary = row['boundary']; check_pin(boundary['envelope']); check_pin(row['observed'])
        require(integer(boundary['start']) < integer(boundary['end']) <= boundary['envelope']['bytes'] and
                boundary['end'] - boundary['start'] == row['observed']['bytes'], 'boundary arithmetic')
    require(type(evidence['r2_edit_attempts']) is list and len(evidence['r2_edit_attempts']) == 3, 'edit coverage')
    for index, (row, spec) in enumerate(zip(evidence['r2_edit_attempts'], source['r2_edit_attempts'])):
        keys(row, 'call_seq result_seq arguments_sha256 is_error target_relative_path matches_session_target')
        require(integer(row['call_seq']) == spec['call_seq'] and integer(row['result_seq']) == spec['result_seq'] and
                row['arguments_sha256'] == spec['arguments_sha256'] and row['is_error'] is spec['is_error'] and
                row['target_relative_path'] == TARGET and row['matches_session_target'] is (index != 0), 'edit structure')
    rep = evidence['replacement']; keys(rep, 'old new occurrences_in_r2 predicted predicted_equals_r3')
    for name in ('old', 'new', 'predicted'):
        check_pin(rep[name])
    require(type(rep['occurrences_in_r2']) is int and rep['occurrences_in_r2'] == 1 and rep['old']['bytes'] > 0,
            'replacement uniqueness')
    first, second = [r['observed'] for r in evidence['slots']]
    require(rep['predicted']['bytes'] == first['bytes'] - rep['old']['bytes'] + rep['new']['bytes'], 'replacement arithmetic')
    require(type(rep['predicted_equals_r3']) is bool and rep['predicted_equals_r3'] == (rep['predicted'] == second), 'replacement relation')
    same = first == second
    conclusion = ('candidate_not_supported' if same else
                  'different_and_edit_compatible' if rep['predicted_equals_r3'] else 'different_observed_states')
    return {'schema': 'first-read-file-state-result-v1', 'status': 'PASS',
            'scope': {'existing_slots': 2, 'targets': 1, 'pairs': 1, 'new_product_runs': 0,
                      'exploratory_then_fixed': True, 'r1_in_main_analysis': False},
            'sources_sha256': SOURCES_SHA, 'legacy_public_dependencies': 69,
            'nominal': nominal, 'first_observed': first, 'second_observed': second,
            'observed_same_pairs': int(same), 'compared_pairs': 1,
            'observed_length_delta': second['bytes'] - first['bytes'],
            'successful_edit_prediction': rep['predicted'], 'prediction_equals_second': rep['predicted_equals_r3'],
            'conclusion': conclusion,
            'limits': ['Public PASS checks sealed content-free structure, not private-original authenticity.',
                       'Observed first-read content is not an exclusive process launch snapshot.',
                       'Inherited input metadata is nominal, not a fresh execution gate.',
                       'Edit compatibility does not certify the unique writer or functional correctness.',
                       'No causality for thinking/cache, tool choice, answers, scores or formal25.']}

def exclusive(path, value, forbidden_roots=()):
    path = Path(path)
    resolved = path.resolve()
    require(not path.is_symlink(), 'unsafe output path')
    for root in forbidden_roots:
        root = Path(root).resolve()
        require(resolved != root and root not in resolved.parents, 'output overlaps source root')
    with path.open('xb') as stream:
        stream.write(canon(value) + b'\n')

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--archive-root', type=Path)
    parser.add_argument('--build-evidence', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        require(args.build_evidence is None or args.archive_root is not None, 'building needs archive root')
        require(args.build_evidence is None or args.build_evidence.resolve() != args.output.resolve(), 'duplicate output path')
        source, legacy, nominal = public_sources(args.root)
        evidence = None
        if args.archive_root is not None:
            evidence = build(args.archive_root, source, legacy, nominal)
        if args.build_evidence is not None:
            validate(evidence, source, legacy, nominal)
            exclusive(args.build_evidence, evidence, (args.root, args.archive_root))
        else:
            saved = load(bound(args.root.resolve(), HERE + '/evidence.json', EVIDENCE_SHA))
            if evidence is not None:
                require(evidence == saved, 'raw reconstruction differs from public evidence')
            evidence = saved
        result = validate(evidence, source, legacy, nominal)
        forbidden = [args.root]
        if args.archive_root is not None:
            forbidden.append(args.archive_root)
        exclusive(args.output, result, forbidden)
        print('PASS: fixed-source result written exclusively')
        return 0
    except Exception:
        # Do not echo raw values, private paths, commands, IDs or OS exception text.
        print('FAIL: validation or exclusive-output error', file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
