#!/usr/bin/env python3
"""Recompute selected derived text relationships, NOT original trace authenticity."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent


class InvalidEvidence(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise InvalidEvidence(reason)


def sha(text):
    return hashlib.sha256(text.encode('utf8')).hexdigest()


def units(text):
    return {'codepoints': len(text), 'utf16_units': len(text.encode('utf-16-le')) // 2,
            'utf8_bytes': len(text.encode('utf8'))}


def source_intervals(face, payload):
    require(payload.isascii(), 'this source-interval probe requires ASCII')
    if face == payload:
        return {'kind': 'F', 'source_intervals': [[0, len(payload)]],
                'retained_source_bytes': len(payload), 'wrapper_bytes': 0,
                'omitted': 0, 'face_bytes': len(face)}
    markers = re.findall(r'Omitted (\d+) bytes', face)
    require(len(markers) == 1, 'one omission marker required')
    omitted = int(markers[0])
    require(0 < omitted < len(payload), 'invalid omission count')
    prefix = 0
    for a, b in zip(face, payload):
        if a != b:
            break
        prefix += 1
    anchor = payload[-128:]
    require(face.count(anchor) == 1, 'unique exact source-tail anchor required')
    end = face.index(anchor) + len(anchor)
    suffix = 0
    for a, b in zip(reversed(face[:end]), reversed(payload)):
        if a != b:
            break
        suffix += 1
    require(prefix > 0 and suffix > 0 and prefix + suffix < len(payload), 'invalid source intervals')
    require(prefix + suffix + omitted == len(payload), 'source/omission accounting mismatch')
    require(payload[20000:20100] not in face, 'omitted middle unexpectedly present')
    size = len(face.encode('utf8'))
    require(size < len(payload), 'not a bounded face')
    return {'kind': 'S', 'source_intervals': [[0, prefix], [len(payload) - suffix, len(payload)]],
            'retained_source_bytes': prefix + suffix, 'wrapper_bytes': size - prefix - suffix,
            'omitted': omitted, 'face_bytes': size}


def retention_windows(content):
    start, close = '<tool-output-truncated>\n', '\n</tool-output-truncated>'
    head_label = 'Head (first 2K characters):\n'
    separator = '\n\n...\nTail (last 2K characters):\n'
    require(content.startswith(start) and content.endswith(close), 'closed labeled wrapper required')
    require(content.count('<tool-output-truncated>') == content.count('</tool-output-truncated>') == 1,
            'ambiguous truncation wrapper')
    require(content.count(head_label) == content.count(separator) == 1, 'one head/tail label pair required')
    before, rest = content.split(head_label)
    head, rest = rest.split(separator)
    tail = rest[:-len(close)]
    header = re.search(r'Output too large \(([^,]+) characters, (\d+) bytes\) from tool `Read`\.', before)
    require(header is not None and head and tail, 'original-size declaration required')
    wrapper = before + head_label + separator + close
    return {'content': units(content), 'head': units(head), 'tail': units(tail),
            'wrapper': units(wrapper), 'declared_original_tool_output_bytes': int(header.group(2)),
            'declared_original_chars_label': header.group(1)}


def check_face_record(record, payload):
    content = record['tool_content']
    require(record['derived_not_original_trace'] is True, 'derived boundary must be explicit')
    require(record['surface'] == 'local_client_request_tool_result', 'wrong observation surface')
    require(record['tool_result_is_error'] is False, 'error result cannot be an ordinary observation')
    require(sha(content) == record['derived_tool_content_sha256'], 'derived tool text hash changed')
    require(len(content.encode()) == record['original_tool_content_utf8_bytes'], 'redaction changed byte count')
    require('/Users/' not in content and '/private/' not in content, 'private path exposed')
    for key in ('original_tool_content_sha256', 'request_json_file_sha256', 'wire_request_body_sha256'):
        require(re.fullmatch(r'[0-9a-f]{64}', record[key]) is not None, 'malformed hash label')
    require(record['request_json_file_sha256'] != record['wire_request_body_sha256'], 'JSON/wire hashes conflated')
    changes = record['path_replacements']
    if changes:
        require(record['transformation'] == 'same_utf8_byte_length_private_path_replacement', 'unmarked text transformation')
        require(all(x['removed_utf8_bytes'] == x['replacement_utf8_bytes'] for x in changes), 'redaction length mismatch')
    else:
        require(record['transformation'] == 'selected_text_only_no_text_change', 'wrong unmodified-text label')
        require(record['original_tool_content_sha256'] == sha(content), 'selected original-text hash mismatch')
    return source_intervals(content, payload)


def verify(data, payload):
    require(data['schema'] == 'tool-return-measurement-identity-derived-v1', 'unknown schema')
    require(len(payload.encode()) == 40000 and sha(payload) == data['dsh']['payload_sha256'], 'fixture changed')
    dsh = data['dsh']
    require(dsh['recorded_version'] == '0.2.0-rc.2' and dsh['cap_setting'] == 8192, 'recorded condition changed')
    require(dsh['synthetic_registered_tools'] is True and dsh['native_fs_tested'] is False, 'synthetic/native-fs boundary missing')
    require(dsh['real_model_trials'] == dsh['upstream_attempts_in_this_relay'] == 0, 'mock promoted to live trial')
    require(dsh['request_count'] == 10 and dsh['callback_count'] == 6, 'run-count metadata changed')
    require(dsh['backend_input'] == 'unverifiable' and dsh['call_id_name_confound_disclosed'] is True,
            'unsupported causal/backend claim')
    planned = {(n, p) for n in ('read', 'observation_output') for p in ('first', 'after_spill')}
    planned_ids = {name + '-' + phase for name, phase in planned}
    warmup_sources = {
        'read-after_spill': 'b6ea315cf7080eb7065536df5d453cb723268b4b0b2ec0169112374b71b5983f',
        'observation_output-after_spill': '495c1627496b83f6362f7004ebf4871682533dba1abf5faa756309874699b2dd',
    }
    records = dsh['observations']
    require(len(records) == 4 and {(x['tool'], x['phase']) for x in records} == planned, 'four distinct planned cells required')
    table = []
    for record in records:
        require(record['observation_id'] == record['tool'] + '-' + record['phase'], 'target observation/parent mapping changed')
        n = 2 if record['phase'] == 'first' else 3
        require(record['request_number'] == n and record['call_id'] == record['tool'] + '-call-' + str(n - 1),
                'derived call/phase binding changed')
        require(record['callback_payload_sha256'] == sha(payload), 'callback source changed')
        measured = check_face_record(record, payload)
        expected = 'F' if record['tool'] == 'read' else 'S'
        require(measured['kind'] == expected, 'identity/stage shape not reproduced')
        if expected == 'S':
            require(measured['source_intervals'] == [[0, 16224], [23780, 40000]] and
                    measured['omitted'] == 7556 and measured['wrapper_bytes'] == 256 and measured['face_bytes'] == 32700,
                    'alias interval/accounting changed')
        table.append({'observation_id': record['observation_id'], **measured})
    first = dsh['first_request_hashes']
    require(len(first) == 4 and {x['observation_id'] for x in first} == planned_ids, 'first-request exact parent coverage missing')
    require({x['request_json_file_sha256'] for x in first} == {'eab4a5f19c0567c117fc855814616a861197e4c6b081d760945c6bf7a8e679e8'},
            'published JSON-file receipt changed')
    require({x['wire_request_body_sha256'] for x in first} == {'921a45eebcb1cd0e80d4fe186e489889fc1a0115361bc0837bbf4f0d0c3abd79'},
            'published wire-body receipt changed')
    warmups = dsh['warmups']
    require(len(warmups) == 2 and {x['observation_id'] for x in warmups} ==
            {parent + '-warmup-r2' for parent in warmup_sources}, 'two exact after-spill warmup parents required')
    for record in warmups:
        parent = record['observation_id'].removesuffix('-warmup-r2')
        later = record['history_repeat']
        require(later['observation_id'] == parent + '-warmup-r3' and
                record['call_id'] == later['call_id'] == 'warmup_output-call-1', 'warmup history ID/call mapping changed')
        require(record['original_tool_content_sha256'] == later['original_tool_content_sha256'] == warmup_sources[parent],
                'published warmup source receipt/parent changed')
        a, b = check_face_record(record, payload), check_face_record(later, payload)
        require(record['tool'] == later['tool'] == 'warmup_output' and record['request_number'] == 2 and later['request_number'] == 3,
                'warmup request mapping changed')
        require(record['original_tool_content_sha256'] == later['original_tool_content_sha256'] and
                record['tool_content'] == later['tool_content'], 'earlier history changed')
        require(a == b and a['kind'] == 'S' and a['source_intervals'] == [[0, 16224], [23776, 40000]] and
                a['omitted'] == 7552 and a['wrapper_bytes'] == 251 and a['face_bytes'] == 32699, 'warmup accounting changed')
    predicted = 40000 - 4 * (8192 - 80)
    require(predicted == 7552 and 7556 - predicted == 4, 'residual must be preserved')
    geometry = data['doubao_retention']
    require(geometry['independent_replications'] is False and geometry['backend_input'] == 'unverifiable',
            'replication/backend limit missing')
    samples = geometry['records']
    require([x['observation_id'] for x in samples] == ['retention-a', 'retention-b', 'retention-c'],
            'three exact retention selections required')
    shapes = []
    for sample in samples:
        require(sample['surface'] == 'native_local_trajectory_Read_content' and sample['derived_not_original_trace'] is True,
                'retention surface changed')
        require(sample['tool_content_sha256'] == sha(sample['tool_content']), 'retention text hash changed')
        require(sample['tool_content'].isascii(), 'selected retention records must remain ASCII; units may not be conflated')
        shape = retention_windows(sample['tool_content'])
        require(shape['head']['codepoints'] == shape['tail']['codepoints'] == 2048, 'not labeled 2048+2048 windows')
        shapes.append(shape)
    require([x['declared_original_tool_output_bytes'] for x in shapes] == [83688, 83688, 100569],
            'selected original tool-output declarations changed')
    require([x['declared_original_chars_label'] for x in shapes] == ['84K', '84K', '101K'],
            'selected character-size labels changed')
    require([x['content']['codepoints'] for x in shapes] == [4272, 4272, 4274], 'retention content totals changed')
    require([x['wrapper']['codepoints'] for x in shapes] == [176, 176, 178], 'retention wrapper totals changed')
    require(len({x['tool_content_sha256'] for x in samples}) == geometry['distinct_tool_content_hashes'] == 2,
            'identical content must not count as independent text')
    accounting = geometry['all_tool_join_accounting']
    lengths = accounting['content_lengths']
    require(lengths == [4272, 346, 1300, 369, 147], 'tool-length ledger changed')
    require(sum(lengths) == accounting['all_content_sum'] == 6434 and
            len(lengths) - 1 == accounting['all_join_newlines'] == 4 and
            sum(lengths) + 4 == accounting['all_join_total'] == 6438, 'all-tool join accounting failed')
    require(sum(lengths[1:]) == accounting['compensation_content_sum'] == 2162 and
            len(lengths[1:]) - 1 == accounting['compensation_join_newlines'] == 3 and
            sum(lengths[1:]) + 3 == accounting['compensation_join_total'] == 2165, 'compensation accounting failed')
    return {'status': 'DERIVED_RELATIONSHIPS_PASS', 'dsh_cells': table, 'alias_formula_residual_bytes': 4,
            'doubao_retention': shapes, 'original_complete_trace_authenticity': 'not_reproduced_by_this_package',
            'backend_model_ingestion': 'unverifiable', 'formal_25_scores_changed': False}


if __name__ == '__main__':
    evidence = json.loads((ROOT / 'derived-evidence.json').read_text())
    payload = (ROOT / 'synthetic-payload.txt').read_text()
    print(json.dumps(verify(evidence, payload), ensure_ascii=False, indent=2))
