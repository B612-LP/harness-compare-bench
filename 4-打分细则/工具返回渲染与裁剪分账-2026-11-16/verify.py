#!/usr/bin/env python3
"""Offline, standard-library replay. No commands from the archive are executed.

Without --archive-root: verify pinned public evidence and its arithmetic only.
With --archive-root: rebuild all 112 source-linked records and compare evidence
byte-for-byte in canonical JSON. Neither mode authenticates private originals.
--build-evidence creates an exclusive NEW projection; --output also uses 'x'.
"""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BASELINE = '50c073c084006c0bfd5f8b79db3bc495e842847b'
PREREG_SHA256 = 'd828bfb8b573d6a0f0a42cba45c522c7447c2a42566f44f2e88b137469de3eb7'
EVIDENCE_SHA256 = '0522591d24a088d90eeff62fce7bb7dc5f23107dfc88dab287e8f44b2bc6ed79'
OLD_VERIFY = '4-打分细则/工具结果下游性判定-2026-11-16/verify.py'
OLD_VERIFY_SHA256 = 'd36d8cfa472656eba6127b8cdd488bda8613067e24b142cb91307d25e4f4c4fd'
R3_RESULT = '4-打分细则/R3不稳定来源分解-2026-11-16/result.json'
R3_RESULT_SHA256 = '8b03be40cb53f0a562d8b6b8a006a8e97d1733d8a9da15df8dfc67b0fbb83188'
ARCHIVE_SOURCES = {
    'codex__exercism-py-6__r1': ('codex/runs/codex__exercism-py-6__r1/agent-session/rollout-2026-11-09T13-38-41-01a1bed0-dc97-7b41-b228-5d6153a1118c.jsonl', 'e355baeb2cfcf644a5f9cf6e9017011a78d95e2050a11ce2d37acfc081639cac'),
    'codex__exercism-py-6__r2': ('codex/runs/codex__exercism-py-6__r2/agent-session/rollout-2026-11-09T13-39-10-01a1bed1-4f76-72f1-9b82-6a08a5a4e671.jsonl', 'a866cd55cc64db6b5ad69436bec7b1c3124d406d42541137bc1077ebd0412796'),
    'codex__exercism-py-6__r3': ('codex/runs/codex__exercism-py-6__r3/agent-session/rollout-2026-11-09T13-39-33-01a1bed1-a937-7a62-a054-84041d4c6f33.jsonl', '0e64e0c436a0f24a5cd51cbabcf2425b4da559781d298e4447c8bf0db7f12c49'),
    'codex__dabstep-payments-10__r2': ('codex/runs/codex__dabstep-payments-10__r2/agent-session/rollout-2026-11-09T13-27-41-01a1bec6-c9ba-7813-8188-781d6e4d7396.jsonl', 'e5ee7b2bdd44d0fbedf9ff55d27edd4cdb0db6457ba0335a6331d387b71457a9'),
    'codex__dabstep-payments-10__r3': ('codex/runs/codex__dabstep-payments-10__r3/agent-session/rollout-2026-11-09T13-33-42-01a1becc-4bf9-79a3-a988-6c97b6ccba16.jsonl', 'be045ce4457d98ac8934cfcaddfc0a1759ee3ce6cce79139822cac7490b66c2e'),
}
SLOTS = tuple(ARCHIVE_SOURCES)
COUNTS = dict(zip(SLOTS, (15, 9, 10, 43, 35)))
FROZEN_R3 = {
    SLOTS[0]: {'r3_total_bytes': 91495, 'per_type_bytes': {'function_call': 10475, 'function_call_output': 68188, 'message': 7239, 'reasoning': 5593}},
    SLOTS[1]: {'r3_total_bytes': 60064, 'per_type_bytes': {'function_call': 6318, 'function_call_output': 40782, 'message': 7246, 'reasoning': 5718}},
    SLOTS[2]: {'r3_total_bytes': 80553, 'per_type_bytes': {'function_call': 7174, 'function_call_output': 58562, 'message': 7200, 'reasoning': 7617}},
    SLOTS[3]: {'r3_total_bytes': 334724, 'per_type_bytes': {'function_call': 65049, 'function_call_output': 133869, 'message': 10617, 'reasoning': 125189}},
    SLOTS[4]: {'r3_total_bytes': 286469, 'per_type_bytes': {'function_call': 52273, 'function_call_output': 105274, 'message': 13625, 'reasoning': 115297}},
}
KINDS = ('EXACT', 'MARKED-BOUNDARY-CROP-WITNESS', 'UNEXPLAINED')
REASONS = ('EXACT', 'BOUNDARY-WITNESS', 'HEADER-UNRECOGNIZED', 'NO-MARKER', 'MULTIPLE-MARKERS', 'BOUNDARY-MISMATCH', 'OVERLAP-OR-EMPTY-RETAIN', 'NO-DELETION')
HEADER = re.compile(r'\AChunk ID: [^\n]+\nWall time: [0-9]+(?:\.[0-9]+)? seconds\n(?:Process exited with code [+-]?[0-9]+|Process running with session ID [^\n]+)\n(?:Original token count: [0-9]+\n)?Output:\n')
LINES_WRAPPER = re.compile(r'\ATotal output lines: [0-9]+\n\n')
MARKER = re.compile(r'…[0-9]+ tokens truncated…|\.\.\.[0-9]+ tokens truncated\.\.\.')


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


def reject_constant(_value):
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
    require(isinstance(value, dict) and set(value) == set(expected), 'bad object schema: ' + label)


def integer(value, minimum=None):
    require(type(value) is int and (minimum is None or value >= minimum), 'invalid integer')


def digest(value):
    require(isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None, 'invalid SHA256')


def describe(value):
    raw = value.encode('utf-8') if isinstance(value, str) else value
    result = {'bytes': len(raw), 'sha256': sha(raw)}
    if isinstance(value, str):
        result['characters'] = len(value)
    return result


def check_desc(value, text=False):
    keys(value, ('bytes', 'sha256', 'characters') if text else ('bytes', 'sha256'), 'descriptor')
    integer(value['bytes'], 0)
    digest(value['sha256'])
    if text:
        integer(value['characters'], 0)
        require(value['characters'] <= value['bytes'] <= value['characters'] * 4, 'impossible UTF8 size')
    if value['bytes'] == 0:
        require(value['sha256'] == sha(b''), 'empty digest mismatch')


def read_pinned(path, expected):
    raw = path.read_bytes()
    require(sha(raw) == expected, 'pinned file SHA mismatch')
    return raw


def static_value(raw, name):
    tree = ast.parse(raw)
    values = [node.value for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets)]
    require(len(values) == 1, 'static source constant missing or duplicated')
    return ast.literal_eval(values[0])


def references(root=ROOT):
    read_pinned(root / HERE.relative_to(ROOT) / 'README.md', PREREG_SHA256)
    old = read_pinned(root / OLD_VERIFY, OLD_VERIFY_SHA256)
    require(static_value(old, 'ARCHIVE_SOURCES') == ARCHIVE_SOURCES, 'old mapping differs in either direction')
    require(static_value(old, 'FROZEN_R3') == FROZEN_R3, 'old R3 constants differ')
    r3 = loads(read_pinned(root / R3_RESULT, R3_RESULT_SHA256))
    require(isinstance(r3, dict) and r3.get('schema') == 'r3-decomp-projection-v1', 'bad R3 reference schema')
    rows, bindings = {}, {}
    for row in r3.get('slots', []):
        require(isinstance(row, dict) and isinstance(row.get('slot'), str), 'bad R3 slot')
        require(row['slot'] not in rows, 'duplicate R3 slot')
        rows[row['slot']] = row
    for row in r3.get('trace_bindings', []):
        require(isinstance(row, dict) and isinstance(row.get('slot'), str), 'bad R3 binding')
        require(row['slot'] not in bindings, 'duplicate R3 binding')
        bindings[row['slot']] = row
    require(set(rows) == set(bindings) and set(SLOTS) <= set(rows), 'R3 bindings/slots coverage differs')
    for slot, (relative, expected) in ARCHIVE_SOURCES.items():
        row, binding = rows[slot], bindings[slot]
        require((row.get('trace_archive_relative_path'), row.get('trace_sha256')) == (relative, expected), 'R3 source row differs')
        require((binding.get('archive_relative_path'), binding.get('sha256')) == (relative, expected), 'R3 source binding differs')
        require({k: row.get(k) for k in ('r3_total_bytes', 'per_type_bytes')} == FROZEN_R3[slot], 'R3 byte reference differs')
    return rows


def split_header(output):
    require(isinstance(output, str), 'output is not a string')
    match = HEADER.match(output)
    return (output[:match.end()], output[match.end():]) if match else (None, None)


def diagnostic(body, aggregate):
    left = 0
    while left < min(len(body), len(aggregate)) and body[left] == aggregate[left]:
        left += 1
    right = 0
    limit = min(len(body), len(aggregate)) - left
    while right < limit and body[len(body) - right - 1] == aggregate[len(aggregate) - right - 1]:
        right += 1
    end_b = len(body) - right
    end_a = len(aggregate) - right
    return {'prefix': describe(body[:left]), 'suffix': describe(body[end_b:]), 'body_middle': describe(body[left:end_b]), 'aggregate_middle': describe(aggregate[left:end_a])}


def classify(body, aggregate):
    require(body is None or isinstance(body, str), 'body is not text or unknown')
    require(isinstance(aggregate, str), 'aggregate is not a string')
    if body is None:
        return {'kind': 'UNEXPLAINED', 'reason': 'HEADER-UNRECOGNIZED', 'witness': None, 'diagnostic': None}
    if body == aggregate:
        return {'kind': 'EXACT', 'reason': 'EXACT', 'witness': None, 'diagnostic': None}
    wrapper_match = LINES_WRAPPER.match(body)
    wrapper = body[:wrapper_match.end()] if wrapper_match else ''
    rest = body[len(wrapper):]
    markers = list(MARKER.finditer(rest))
    reason = 'NO-MARKER' if not markers else 'MULTIPLE-MARKERS'
    if len(markers) == 1:
        marker = markers[0]
        prefix, suffix = rest[:marker.start()], rest[marker.end():]
        retained = len(prefix) + len(suffix)
        if not aggregate.startswith(prefix) or not aggregate.endswith(suffix):
            reason = 'BOUNDARY-MISMATCH'
        elif retained == 0 or retained > len(aggregate):
            reason = 'OVERLAP-OR-EMPTY-RETAIN'
        elif retained == len(aggregate):
            reason = 'NO-DELETION'
        else:
            deleted = aggregate[len(prefix):len(aggregate) - len(suffix)] if suffix else aggregate[len(prefix):]
            require(deleted != '', 'internal empty deletion')
            return {'kind': 'MARKED-BOUNDARY-CROP-WITNESS', 'reason': 'BOUNDARY-WITNESS', 'witness': {'format': 'unicode-ellipsis' if marker.group().startswith('…') else 'ascii-dots', 'prefix': describe(prefix), 'suffix': describe(suffix), 'deleted': describe(deleted), 'marker': describe(marker.group()), 'added_wrapper': describe(wrapper)}, 'diagnostic': None}
    return {'kind': 'UNEXPLAINED', 'reason': reason, 'witness': None, 'diagnostic': diagnostic(body, aggregate)}


def components(planes):
    p, o, b, a = (planes[k]['bytes'] if planes[k] is not None else None for k in ('P', 'O', 'B', 'A'))
    return {'J': p - o, 'H': None if b is None else o - b, 'A': a, 'T': None if b is None else b - a}


def parse_trace(raw):
    try:
        text = raw.decode('utf-8')
    except UnicodeError as error:
        raise Invalid('invalid trace UTF8') from error
    # Split only on LF: Unicode line separators inside strings are not JSONL separators.
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    require(bool(lines), 'empty trace')
    events = []
    for number, line in enumerate(lines, 1):
        require(bool(line.strip()), 'blank trace line')
        event = loads(line)
        require(isinstance(event, dict) and isinstance(event.get('type'), str), 'invalid trace event')
        events.append((number, event))
    return events


def project_slot(raw, slot, relative, expected_sha):
    require(sha(raw) == expected_sha, 'archived source SHA mismatch')
    events = parse_trace(raw)
    calls, outputs, executions = {}, {}, {}
    per_type = Counter()
    response_items = 0
    for line, event in events:
        p = event.get('payload')
        if event['type'] == 'response_item':
            require(isinstance(p, dict) and isinstance(p.get('type'), str) and p['type'], 'bad response payload')
            typ = p['type']
            per_type[typ] += len(canon(p))
            response_items += 1
            if typ in ('function_call', 'function_call_output'):
                cid = p.get('call_id')
                require(isinstance(cid, str) and cid, 'missing local call ID')
                target = calls if typ == 'function_call' else outputs
                require(cid not in target, 'duplicate local call/output')
                if typ == 'function_call':
                    require(isinstance(p.get('name'), str) and isinstance(p.get('arguments'), str), 'bad call fields')
                    require(isinstance(loads(p['arguments']), dict), 'bad arguments object')
                target[cid] = (line, p)
        elif event['type'] == 'event_msg':
            require(isinstance(p, dict), 'bad event message')
            if p.get('type') == 'item_completed':
                item = p.get('item')
                require(isinstance(item, dict), 'bad completed item')
                if item.get('type') == 'CommandExecution':
                    cid = item.get('id')
                    require(isinstance(cid, str) and cid, 'missing execution ID')
                    require(cid not in executions, 'duplicate final execution')
                    require(isinstance(item.get('aggregated_output'), str), 'bad aggregate text')
                    executions[cid] = (line, item)
    require(set(calls) == set(outputs) == set(executions), 'local three-way coverage differs')
    records = []
    for occurrence, (cid, (output_line, output)) in enumerate(sorted(outputs.items(), key=lambda entry: entry[1][0]), 1):
        call_line, call = calls[cid]
        execution_line, execution = executions[cid]
        require(call_line < output_line and call_line < execution_line, 'invalid local event order')
        header, body = split_header(output.get('output'))
        aggregate = execution['aggregated_output']
        planes = {'P': describe(canon(output)), 'O': describe(output['output']), 'B': None if body is None else describe(body), 'A': describe(aggregate)}
        records.append({'slot': slot, 'occurrence': occurrence, 'source': {'archive_relative_path': relative, 'sha256': expected_sha}, 'lines': {'call': call_line, 'output': output_line, 'execution': execution_line}, 'local_join_key_sha256': sha(cid.encode('utf-8')), 'call_payload': describe(canon(call)), 'execution_item': describe(canon(execution)), 'planes': planes, 'header': None if header is None else describe(header), 'conversion': classify(body, aggregate), 'components': components(planes)})
    return {'slot': slot, 'archive_relative_path': relative, 'sha256': expected_sha, 'source_bytes': len(raw), 'event_count': len(events), 'response_item_count': response_items, 'r3_total_bytes': sum(per_type.values()), 'per_type_bytes': dict(per_type), 'output_count': len(records)}, records


def archive_path(root, relative):
    rel = Path(relative)
    require(not rel.is_absolute() and '..' not in rel.parts, 'unsafe archive-relative path')
    path = (root / rel).resolve()
    require(root.resolve() in path.parents, 'archive path escapes root')
    return path


def rebuild(archive_root, reference_rows):
    sources, records = [], []
    for slot, (relative, expected) in ARCHIVE_SOURCES.items():
        path = archive_path(archive_root, relative)
        summary, rows = project_slot(read_pinned(path, expected), slot, relative, expected)
        require({k: summary[k] for k in ('r3_total_bytes', 'per_type_bytes')} == FROZEN_R3[slot], 'recomputed R3 differs')
        require(summary['output_count'] == COUNTS[slot], 'output denominator differs')
        require(all(summary[k] == reference_rows[slot][k] for k in ('event_count', 'response_item_count')), 'R3 event denominator differs')
        sources.append(summary)
        records.extend(rows)
    # Detect changes during the rebuild without modifying any archived file.
    for relative, expected in ARCHIVE_SOURCES.values():
        read_pinned(archive_path(archive_root, relative), expected)
    return {'schema': 'tool-return-render-evidence-v1', 'baseline_commit': BASELINE, 'prereg_sha256': PREREG_SHA256, 'sources': sources, 'records': records}


def validate_conversion(row):
    conv, planes = row['conversion'], row['planes']
    keys(conv, ('kind', 'reason', 'witness', 'diagnostic'), 'conversion')
    require(conv['kind'] in KINDS and conv['reason'] in REASONS, 'invalid conversion category')
    b, a = planes['B'], planes['A']
    if b is None:
        require(conv == {'kind': 'UNEXPLAINED', 'reason': 'HEADER-UNRECOGNIZED', 'witness': None, 'diagnostic': None}, 'unknown body category differs')
        return
    if conv['kind'] == 'EXACT':
        require(conv['reason'] == 'EXACT' and b == a and conv['witness'] is None and conv['diagnostic'] is None, 'EXACT descriptor mismatch')
    elif conv['kind'] == 'MARKED-BOUNDARY-CROP-WITNESS':
        require(conv['reason'] == 'BOUNDARY-WITNESS' and conv['diagnostic'] is None, 'bad crop category')
        w = conv['witness']
        keys(w, ('format', 'prefix', 'suffix', 'deleted', 'marker', 'added_wrapper'), 'boundary witness')
        require(w['format'] in ('unicode-ellipsis', 'ascii-dots'), 'unknown marker format')
        for name in ('prefix', 'suffix', 'deleted', 'marker', 'added_wrapper'):
            check_desc(w[name], True)
        require(w['prefix']['characters'] + w['suffix']['characters'] > 0 and w['deleted']['characters'] > 0 and w['marker']['characters'] > 0, 'empty/overlapping crop witness')
        for size in ('bytes', 'characters'):
            kept = w['prefix'][size] + w['suffix'][size]
            require(a[size] == kept + w['deleted'][size], 'aggregate witness sum differs')
            require(b[size] == kept + w['marker'][size] + w['added_wrapper'][size], 'body witness sum differs')
    else:
        require(conv['reason'] not in ('EXACT', 'BOUNDARY-WITNESS', 'HEADER-UNRECOGNIZED') and conv['witness'] is None and b != a, 'invalid unexplained category')
        diag = conv['diagnostic']
        keys(diag, ('prefix', 'suffix', 'body_middle', 'aggregate_middle'), 'diagnostic')
        for value in diag.values():
            check_desc(value, True)
        for size in ('bytes', 'characters'):
            kept = diag['prefix'][size] + diag['suffix'][size]
            require(b[size] == kept + diag['body_middle'][size] and a[size] == kept + diag['aggregate_middle'][size], 'diagnostic sum differs')


def validate_evidence(evidence, reference_rows):
    keys(evidence, ('schema', 'baseline_commit', 'prereg_sha256', 'sources', 'records'), 'evidence')
    require(evidence['schema'] == 'tool-return-render-evidence-v1' and evidence['baseline_commit'] == BASELINE and evidence['prereg_sha256'] == PREREG_SHA256, 'evidence contract differs')
    require(isinstance(evidence['sources'], list) and isinstance(evidence['records'], list), 'bad evidence collections')
    require([s.get('slot') if isinstance(s, dict) else None for s in evidence['sources']] == list(SLOTS), 'source coverage/order differs')
    sources = {}
    for source in evidence['sources']:
        keys(source, ('slot', 'archive_relative_path', 'sha256', 'source_bytes', 'event_count', 'response_item_count', 'r3_total_bytes', 'per_type_bytes', 'output_count'), 'source summary')
        slot = source['slot']
        require((source['archive_relative_path'], source['sha256']) == ARCHIVE_SOURCES[slot], 'source pin differs')
        for name in ('source_bytes', 'event_count', 'response_item_count', 'r3_total_bytes', 'output_count'):
            integer(source[name], 1)
        require({k: source[k] for k in ('r3_total_bytes', 'per_type_bytes')} == FROZEN_R3[slot], 'projection R3 differs')
        require(source['output_count'] == COUNTS[slot], 'source output count differs')
        require(all(source[k] == reference_rows[slot][k] for k in ('event_count', 'response_item_count')), 'projection event counts differ')
        sources[slot] = source
    observed, unique_ids, used_lines = Counter(), set(), set()
    output_order = []
    for row in evidence['records']:
        keys(row, ('slot', 'occurrence', 'source', 'lines', 'local_join_key_sha256', 'call_payload', 'execution_item', 'planes', 'header', 'conversion', 'components'), 'record')
        slot = row['slot']
        require(slot in sources, 'record outside slots')
        observed[slot] += 1
        require(type(row['occurrence']) is int and row['occurrence'] == observed[slot], 'occurrence order differs')
        require(row['source'] == {'archive_relative_path': ARCHIVE_SOURCES[slot][0], 'sha256': ARCHIVE_SOURCES[slot][1]}, 'record source differs')
        keys(row['lines'], ('call', 'output', 'execution'), 'source lines')
        for number in row['lines'].values():
            integer(number, 1)
            require(number <= sources[slot]['event_count'] and (slot, number) not in used_lines, 'duplicate/out-of-range source line')
            used_lines.add((slot, number))
        require(row['lines']['call'] < min(row['lines']['output'], row['lines']['execution']), 'record line order differs')
        digest(row['local_join_key_sha256'])
        require((slot, row['local_join_key_sha256']) not in unique_ids, 'duplicate record join key')
        unique_ids.add((slot, row['local_join_key_sha256']))
        check_desc(row['call_payload'])
        check_desc(row['execution_item'])
        keys(row['planes'], ('P', 'O', 'B', 'A'), 'planes')
        for name, value in row['planes'].items():
            if name != 'B' or value is not None:
                check_desc(value, name != 'P')
        if row['planes']['B'] is None:
            require(row['header'] is None, 'fabricated header for unknown body')
        else:
            check_desc(row['header'], True)
            for size in ('bytes', 'characters'):
                require(row['planes']['O'][size] == row['header'][size] + row['planes']['B'][size], 'header/body sum differs')
        require(row['components'] == components(row['planes']), 'components differ')
        for value in row['components'].values():
            if value is not None:
                integer(value)
        if row['planes']['B'] is not None:
            require(row['planes']['P']['bytes'] == sum(row['components'].values()), 'record identity differs')
        validate_conversion(row)
        output_order.append((SLOTS.index(slot), row['lines']['output']))
    require(output_order == sorted(output_order), 'record output order differs')
    require(observed == COUNTS and len(evidence['records']) == 112, 'record denominator differs')
    for slot in SLOTS:
        require(sum(r['planes']['P']['bytes'] for r in evidence['records'] if r['slot'] == slot) == FROZEN_R3[slot]['per_type_bytes']['function_call_output'], 'output payload sum differs from R3')


def summary(rows):
    planes = {k: None if any(r['planes'][k] is None for r in rows) else sum(r['planes'][k]['bytes'] for r in rows) for k in ('P', 'O', 'B', 'A')}
    terms = {k: None if any(r['components'][k] is None for r in rows) else sum(r['components'][k] for r in rows) for k in ('J', 'H', 'A', 'T')}
    counts = {kind: sum(r['conversion']['kind'] == kind for r in rows) for kind in KINDS}
    known = sum(r['planes']['B'] is not None for r in rows)
    identity = None if known != len(rows) else planes['P'] == sum(terms.values())
    require(sum(counts.values()) == len(rows) and identity is not False, 'summary does not close')
    return {'outputs': len(rows), 'header_known': known, 'classification': counts, 'planes_bytes': planes, 'components_bytes': terms, 'identity_closed': identity, 'T_by_classification_bytes': {kind: None if any(r['components']['T'] is None for r in rows if r['conversion']['kind'] == kind) else sum(r['components']['T'] for r in rows if r['conversion']['kind'] == kind) for kind in KINDS}}


def result_for(evidence, evidence_sha):
    slots = [{'slot': slot, **summary([r for r in evidence['records'] if r['slot'] == slot])} for slot in SLOTS]
    a, b = slots[0], slots[1]
    delta_planes = {key: None if a['planes_bytes'][key] is None or b['planes_bytes'][key] is None else a['planes_bytes'][key] - b['planes_bytes'][key] for key in ('P', 'O', 'B', 'A')}
    delta_terms = {key: None if a['components_bytes'][key] is None or b['components_bytes'][key] is None else a['components_bytes'][key] - b['components_bytes'][key] for key in ('J', 'H', 'A', 'T')}
    identity = None if any(v is None for v in delta_terms.values()) else delta_planes['P'] == sum(delta_terms.values())
    require(identity is not False, 'primary comparison identity differs')
    all_summary = summary(evidence['records'])
    return {'schema': 'tool-return-render-result-v1', 'baseline_commit': BASELINE, 'prereg_sha256': PREREG_SHA256, 'evidence_sha256': evidence_sha, 'sources_verified': 5, 'public_replay_scope': 'Pinned content-free projection arithmetic and public source binding only; archive-root rebuild additionally checks exact string relations. Neither certifies private original authenticity, backend intake or causality.', 'slots': slots, 'overall': all_summary, 'primary_comparison': {'orientation': 'exercism_r1_minus_r2', 'slot_a': SLOTS[0], 'slot_b': SLOTS[1], 'planes_delta_bytes': delta_planes, 'components_delta_bytes': delta_terms, 'identity_closed': identity, 'component_share_of_delta_P': {k: {'numerator': v, 'denominator': delta_planes['P']} for k, v in delta_terms.items()}}, 'all_nonexact_explained_by_frozen_rule': all_summary['classification']['UNEXPLAINED'] == 0, 'unchanged': ['old R3 and gates', '25 formal cells', 'historical scores', 'product/model sample count']}


def exclusive_write(path, raw):
    with Path(path).open('xb') as handle:
        handle.write(raw)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-root', type=Path)
    parser.add_argument('--evidence', type=Path, default=HERE / 'evidence.json')
    parser.add_argument('--build-evidence', type=Path, help='exclusive new evidence file; requires archive-root')
    parser.add_argument('--output', type=Path, help='exclusive new result file')
    args = parser.parse_args(argv)
    try:
        reference_rows = references()
        if args.build_evidence:
            require(args.archive_root is not None, 'build-evidence requires archive-root')
            evidence = rebuild(args.archive_root, reference_rows)
            raw = document(evidence)
            require(sha(raw) == EVIDENCE_SHA256, 'rebuilt evidence seal differs')
        else:
            require(EVIDENCE_SHA256 is not None, 'evidence seal not installed')
            raw = read_pinned(args.evidence, EVIDENCE_SHA256)
            evidence = loads(raw)
            if args.archive_root:
                require(canon(rebuild(args.archive_root, reference_rows)) == canon(evidence), 'archive rebuild differs from evidence')
        validate_evidence(evidence, reference_rows)
        result = document(result_for(evidence, sha(raw)))
        # Preflight all explicit destinations before creating any file.
        destinations = [p for p in (args.build_evidence, args.output) if p is not None]
        require(len({p.resolve() for p in destinations}) == len(destinations), 'duplicate output destination')
        require(all(not p.exists() for p in destinations), 'exclusive output already exists')
        if args.build_evidence:
            exclusive_write(args.build_evidence, raw)
        if args.output:
            exclusive_write(args.output, result)
        sys.stdout.buffer.write(result)
        return 0
    except (Invalid, OSError, ValueError, TypeError, KeyError, SyntaxError, OverflowError, RecursionError) as error:
        # No offending values/commands/paths are echoed into public diagnostics.
        print('INVALID: ' + type(error).__name__ + ': ' + (str(error) if isinstance(error, Invalid) else 'input or output failure'), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
