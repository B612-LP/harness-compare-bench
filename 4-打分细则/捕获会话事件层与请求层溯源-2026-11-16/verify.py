#!/usr/bin/env python3
"""Provenance mapping between the capture session's local event stream and the
three captured wire requests.

Private rebuild mode reads the session log copy plus the raw request bodies
and recomputes the frozen mapping (content exactness is computed on private
bytes but stored only as booleans, byte counts, and shape descriptors).
Public validation mode re-reads only the public pinned capture package files
and validates the stored mapping table for schema, internal arithmetic, and
cross-binding against the capture package's published shape facts. No message
or event content is ever written to public files.

The session log is a concatenation of independent zstd frames (one JSON line
per frame); frames are decoded sequentially, never by single-frame decompress.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASELINE = '004d7cd90dbc67a2f4006151fa15805c978757c7'
CAP_RELPATH = '4-打分细则/DSH请求侧最小捕获-2026-11-16/evidence.json'
CAP_SHA = 'f3e4fab3cd0d742ce4840f1e3b57423b62094c4cd8b7a939b3b347658b4aeaa1'
CAPRES_RELPATH = '4-打分细则/DSH请求侧最小捕获-2026-11-16/result.json'
CAPRES_SHA = '3de57557fe7f3c74e6abc041e5181fc415595299b9678ed59d271f8abe596357'
CAPREADME_RELPATH = '4-打分细则/DSH请求侧最小捕获-2026-11-16/README.md'
CAPREADME_SHA = 'a26c7ec7df5dc052ce708434a3cbfa2b50deca2745effa1b91a5877f279c04e7'
SELF_RELPATH = '4-打分细则/捕获会话事件层与请求层溯源-2026-11-16/README.md'
SESSION_SHA = '5c2bf4d4840525c0df59932b705f44615d9ae3888c4d66b3347b19670e339ba4'
EVENT_COUNT = 29
SCHEMA = 'capture-session-provenance-evidence-v1'
TITLE_PREFIX = 'Generate the session title from this JSON array of human messages:\n'
ADAPTER_UNKNOWN = ['stream', 'stream_options', 'thinking', 'tool_stream']
LIMITS = [
    'n=1 captured run, one provider, session-log format v4; no generalization to other runs, providers, or products',
    'content exactness was computed on private bytes; public files store only booleans, byte counts, seq pairs, and shape descriptors',
    'assistant semantic equivalence is not judged; only structural identity of ids, names, argument strings, and null content',
    'P5 adapter-level wire fields are not present in the session event stream and stay unknown',
    'injected user messages (agent instructions / runtime context / skill catalog) are generated at request build time; their provenance is the source metadata inside the events, not an earlier event',
]
TRANSFORM_IDENTITY = 'single_text_block_identity'
TRANSFORM_ASSISTANT = 'tool_call_blocks_to_wire_tool_calls'
TRANSFORM_TOOL = 'tool_result_text_identity'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def no_duplicate_keys(pairs):
    seen = set()
    for key, _ in pairs:
        if key in seen:
            raise ValueError('duplicate key: %s' % key)
        seen.add(key)
    return dict(pairs)


def loads(raw):
    return json.loads(raw.decode('utf-8'),
                      object_pairs_hook=no_duplicate_keys,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('non-finite: %s' % value)))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pinned(root, relative, expected, parse=True):
    raw = (Path(root) / relative).read_bytes()
    require(sha(raw) == expected, 'pin mismatch: %s' % relative)
    return loads(raw) if parse else None


def integer(value, minimum=0):
    require(isinstance(value, int) and not isinstance(value, bool) and value >= minimum,
            'expected non-negative int')
    return value


def text_of(content):
    require(isinstance(content, list) and len(content) == 1 and content[0].get('type') == 'text',
            'expected single text block')
    return content[0].get('text', '')


def frames_decode(raw):
    import zstandard  # private rebuild only; public replay never reaches here
    decompressor = zstandard.ZstdDecompressor()
    out = bytearray()
    blob = raw
    frames = 0
    while blob:
        obj = decompressor.decompressobj()
        out += obj.decompress(blob)
        while not obj.eof:
            more = obj.decompress(b'')
            if not more:
                break
            out += more
        blob = obj.unused_data
        frames += 1
        require(frames <= 4096, 'too many zstd frames')
    return bytes(out), frames


def parse_events(raw):
    text, frame_count = frames_decode(raw)
    text = text.decode('utf-8')
    events = []
    for line in text.split('\n'):
        if not line.strip():
            continue
        events.append(loads(line.encode('utf-8')))
    return events, frame_count


def message_row(wire_req, wire_index, role, wire_content, event_seq, transform, local_text):
    return {'wire_request': wire_req, 'wire_index': wire_index, 'role': role,
            'wire_bytes': len(wire_content.encode('utf-8')),
            'event_seq': event_seq, 'transform': transform,
            'content_exact': local_text == wire_content}


def build(root, raw_root):
    capture = pinned(root, CAP_RELPATH, CAP_SHA)
    pinned(root, CAPRES_RELPATH, CAPRES_SHA)
    pinned(root, CAPREADME_RELPATH, CAPREADME_SHA, parse=False)
    base = Path(raw_root)
    session_raw = (base / 'session.v4.jsonl.zstd').read_bytes()
    require(sha(session_raw) == SESSION_SHA, 'session copy pin mismatch')
    events, session_frames = parse_events(session_raw)
    require(len(events) == EVENT_COUNT, 'unexpected event count')
    by_seq = {}
    for event in events:
        seq = event.get('seq')
        if seq is not None:
            require(seq not in by_seq, 'duplicate seq')
            by_seq[seq] = event

    wire = []
    for index in (1, 2, 3):
        raw = (base / 'requests' / ('%03d.request.bin' % index)).read_bytes()
        published = capture['capture']['requests'][index - 1]
        require(published['seq'] == index, 'capture evidence request order')
        require(sha(raw) == published['request_sha256'], 'wire request %d sha mismatch' % index)
        require(len(raw) == published['request_bytes'], 'wire request %d size mismatch' % index)
        wire.append(loads(raw))

    def text_at(seq, path):
        node = by_seq[seq]['data']
        for key in path:
            node = node[key]
        return text_of(node)

    rows = []
    rows.append(message_row(1, 0, 'system', wire[0]['messages'][0]['content'], 7, TRANSFORM_IDENTITY,
                            text_at(7, ['message', 'content'])))
    for offset, seq in enumerate((8, 9, 10, 11)):
        rows.append(message_row(1, 1 + offset, 'user', wire[0]['messages'][1 + offset]['content'], seq,
                                TRANSFORM_IDENTITY, text_at(seq, ['content'])))

    assistant_blocks = by_seq[17]['data']['message']['content']
    wire_assistant = wire[2]['messages'][5]
    require(wire_assistant['content'] is None, 'assistant wire content not null')
    require(wire_assistant.get('tool_calls'), 'assistant wire missing tool_calls')
    pairs_exact = 0
    for block, call in zip(assistant_blocks, wire_assistant['tool_calls']):
        if (block.get('id') == call.get('id') and block.get('name') == call['function'].get('name')
                and block.get('arguments') == call['function'].get('arguments')):
            pairs_exact += 1
    assistant_row = {'wire_request': 3, 'wire_index': 5, 'role': 'assistant',
                     'wire_bytes': 0, 'event_seq': 17, 'transform': TRANSFORM_ASSISTANT,
                     'content_exact': pairs_exact == len(assistant_blocks)}
    rows.append(assistant_row)
    for widx, seq in ((6, 20), (7, 21)):
        rows.append(message_row(3, widx, 'tool', wire[2]['messages'][widx]['content'], seq,
                                TRANSFORM_TOOL, text_at(seq, ['message', 'content'])))
    id_link_exact = 0
    for seq, widx in ((20, 6), (21, 7)):
        if by_seq[seq]['data']['message'].get('toolCallId') == wire[2]['messages'][widx].get('tool_call_id'):
            id_link_exact += 1

    header = by_seq[12]['data']['header']
    config = header['config']
    header_tools = header['tools']
    wire_tools = wire[0].get('tools') or []
    names_equal = sorted(t['name'] for t in header_tools) == sorted(t['function']['name'] for t in wire_tools)
    fields_exact = 0
    for local_tool, wire_tool in zip(header_tools, wire_tools):
        func = wire_tool.get('function') or {}
        if (wire_tool.get('type') == 'function' and func.get('name') == local_tool.get('name')
                and func.get('description') == local_tool.get('description')
                and func.get('parameters') == local_tool.get('parameters')):
            fields_exact += 1

    context = by_seq[13]['data']
    model_exact = config.get('model') == wire[0].get('model')
    max_tokens_exact = config.get('maxTokens') == wire[0].get('max_tokens')
    context_model_exact = context.get('model') == wire[0].get('model')

    title = by_seq[15]['data']
    route = title.get('route') or {}
    title_system_exact = title['system'] == wire[1]['messages'][0]['content']
    title_local = text_of(title['messages'][0]['content'])
    embedded = json.dumps([{'seq': 8, 'text': text_at(8, ['content'])}],
                          ensure_ascii=False, separators=(',', ':'))
    title_user_exact = title_local == TITLE_PREFIX + embedded
    title_max_exact = title.get('maxTokens') == wire[1].get('max_tokens')
    title_route_exact = (route.get('provider') == config.get('provider')
                         and route.get('model') == wire[1].get('model'))

    spliced = {seq: by_seq[seq]['data'] for seq in (3, 5)}
    spliced_rows = [{'seq': seq, 'start': d.get('start'), 'target': d.get('target'),
                     'removed_count': d.get('removedCount'),
                     'inserted_count': len(d.get('inserted') or [])} for seq, d in sorted(spliced.items())]
    task_prompt_in_spliced = any(text_of(item['content']) == text_at(8, ['content'])
                                 for item in (spliced[3].get('inserted') or []))

    for row in rows:
        row['content_exact'] = bool(row['content_exact'])
    content_exact_count = sum(1 for row in rows if row['content_exact'])
    wire_bytes_by_request = {}
    for row in rows:
        wire_bytes_by_request.setdefault(row['wire_request'], []).append(
            {'wire_index': row['wire_index'], 'bytes': row['wire_bytes']})

    evidence = {'schema': SCHEMA, 'baseline_commit': BASELINE, 'evidence_sha256': None,
                'sources': {CAP_RELPATH: CAP_SHA, CAPRES_RELPATH: CAPRES_SHA,
                            CAPREADME_RELPATH: CAPREADME_SHA,
                            'session.v4.jsonl.zstd': SESSION_SHA,
                            'requests/001.request.bin': sha((base / 'requests' / '001.request.bin').read_bytes()),
                            'requests/002.request.bin': sha((base / 'requests' / '002.request.bin').read_bytes()),
                            'requests/003.request.bin': sha((base / 'requests' / '003.request.bin').read_bytes())},
                'session_events': EVENT_COUNT,
                'session_frames': session_frames,
                'mapped_messages': rows,
                'content_exact_count': content_exact_count,
                'assistant': {'blocks': len(assistant_blocks), 'pairs_exact': pairs_exact,
                              'wire_content_null': True, 'tool_call_id_exact': id_link_exact},
                'tools': {'local_count': len(header_tools), 'wire_count': len(wire_tools),
                          'names_equal': names_equal, 'fields_exact': fields_exact},
                'request_level': {'model_exact': model_exact, 'max_tokens_exact': max_tokens_exact,
                                  'context_model_exact': context_model_exact,
                                  'context_window_in_event_only': context.get('contextWindow') == 1000000},
                'title_request': {'system_exact': title_system_exact, 'user_exact': title_user_exact,
                                  'max_tokens_exact': title_max_exact, 'route_exact': title_route_exact},
                'adapter_fields_unknown': ADAPTER_UNKNOWN,
                'spliced': spliced_rows,
                'task_prompt_inserted_by_spliced_3': task_prompt_in_spliced,
                'wire_message_bytes': wire_bytes_by_request,
                'limits': LIMITS}

    capture_requests = capture['capture']['requests']
    require(len(rows) == 8, 'row accounting')
    result = {'schema': 'capture-session-provenance-result-v1', 'baseline_commit': BASELINE,
              'evidence_sha256': None,
              'endpoints': {
                  'p1_loop_message_content_exact': '%d/%d' % (content_exact_count, len(rows)),
                  'p2_assistant_transform_exact': '%d/%d' % (pairs_exact, len(assistant_blocks)),
                  'p2_tool_call_id_exact': '%d/%d' % (id_link_exact, 2),
                  'p3_tool_declarations_field_exact': '%d/%d' % (fields_exact, len(header_tools)),
                  'p3_names_equal': names_equal,
                  'p4_request_level': {'model_exact': model_exact, 'max_tokens_exact': max_tokens_exact},
                  'p4_title_request': {'system_exact': title_system_exact, 'user_exact': title_user_exact,
                                       'max_tokens_exact': title_max_exact, 'route_exact': title_route_exact},
                  'p5_adapter_fields_unknown': ADAPTER_UNKNOWN,
              },
              'cross_binding': {
                  'req1_message_bytes_match_capture_evidence': all(
                      r['wire_bytes'] == entry[2] for r, entry in zip(
                          [r for r in rows if r['wire_request'] == 1],
                          capture_requests[0]['roles'])),
                  'req3_appended_roles_match_capture_evidence': all(
                      r['role'] == entry[0] and r['wire_bytes'] == entry[2]
                      for r, entry in zip(
                          [r for r in rows if r['wire_request'] == 3][-len(capture['prefix_identity']['req3_appended_roles']):],
                          capture['prefix_identity']['req3_appended_roles'])),
              },
              'verdict_summary': 'descriptive provenance for one captured run; see limits; no generalization',
              'limits': LIMITS}
    return evidence, result


def validate_public(root, evidence, result):
    capture = pinned(root, CAP_RELPATH, CAP_SHA)
    pinned(root, CAPRES_RELPATH, CAPRES_SHA)
    pinned(root, CAPREADME_RELPATH, CAPREADME_SHA, parse=False)
    fresh_sources = {CAP_RELPATH: CAP_SHA, CAPRES_RELPATH: CAPRES_SHA,
                     CAPREADME_RELPATH: CAPREADME_SHA,
                     'session.v4.jsonl.zstd': SESSION_SHA}
    for index in (1, 2, 3):
        fresh_sources['requests/%03d.request.bin' % index] = capture['capture']['requests'][index - 1]['request_sha256']
    require(evidence['sources'] == fresh_sources, 'evidence sources differ from public pins')
    require(evidence['schema'] == SCHEMA and evidence['session_events'] == EVENT_COUNT, 'bad schema')
    require(isinstance(evidence['session_frames'], int) and not isinstance(evidence['session_frames'], bool)
            and 1 <= evidence['session_frames'] <= evidence['session_events'], 'bad frame count')
    rows = evidence['mapped_messages']
    require(len(rows) == 8, 'expected 8 mapped messages')
    require(evidence['content_exact_count'] == sum(1 for r in rows if r['content_exact']), 'count mismatch')
    roles = capture['capture']['requests'][0]['roles']
    for row, entry in zip([r for r in rows if r['wire_request'] == 1], roles):
        require(row['role'] == entry[0] and row['wire_bytes'] == entry[2], 'req1 row bytes mismatch')
    appended = capture['prefix_identity']['req3_appended_roles']
    tool_rows = [r for r in rows if r['wire_request'] == 3 and r['role'] == 'tool']
    require([r['wire_bytes'] for r in tool_rows] == [entry[2] for entry in appended[1:]], 'req3 tool bytes mismatch')
    endpoints = result['endpoints']
    require(endpoints['p1_loop_message_content_exact'] == '%d/%d' % (evidence['content_exact_count'], 8),
            'endpoint p1 inconsistent')
    require(endpoints['p2_assistant_transform_exact'] == '%d/%d' % (
        evidence['assistant']['pairs_exact'], evidence['assistant']['blocks']), 'endpoint p2 inconsistent')
    stored_binding = result.get('evidence_sha256')
    require(isinstance(stored_binding, str) and len(stored_binding) == 64, 'missing evidence binding')
    require(stored_binding == sha((HERE / 'evidence.json').read_bytes()),
            'result does not bind packaged evidence bytes')
    blob = (HERE / 'evidence.json').read_bytes()
    for forbidden in (b'"content_exact": "text', b'can_chain', b'First read TASK.md'):
        require(forbidden not in blob, 'evidence appears to contain content values')


def document(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def dump(path, value, forbidden_roots=()):
    path = Path(path)
    require(not path.exists(), 'output exists: %s' % path)
    resolved = path.resolve()
    for root_dir in forbidden_roots:
        base = Path(root_dir).resolve()
        require(not (base == resolved or base in resolved.parents), 'output inside protected root denied')
    with path.open('xb') as handle:
        handle.write(document(value))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=HERE.parents[1])
    parser.add_argument('--raw-root', type=Path, help='private dir: session.v4.jsonl.zstd + requests/00N.request.bin')
    parser.add_argument('--build-evidence', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        root = Path(args.root).resolve()
        if args.build_evidence:
            require(args.raw_root is not None, '--raw-root required for rebuild')
            evidence, result = build(root, Path(args.raw_root).resolve())
            dump(args.build_evidence, evidence, forbidden_roots=(root,))
            blob = document(evidence)
            result['evidence_sha256'] = sha(blob)
            dump(args.output, result)
            print('built: messages=%d exact=%d/%d assistant=%d/%d tools=%d/%d title=%s/%s' % (
                len(evidence['mapped_messages']), evidence['content_exact_count'],
                len(evidence['mapped_messages']), evidence['assistant']['pairs_exact'],
                evidence['assistant']['blocks'], evidence['tools']['fields_exact'],
                evidence['tools']['local_count'], evidence['title_request']['system_exact'],
                evidence['title_request']['user_exact']))
            return 0
        evidence = loads((HERE / 'evidence.json').read_bytes())
        stored = loads((HERE / 'result.json').read_bytes())
        validate_public(root, evidence, stored)
        result = dict(stored)
        result['evidence_sha256'] = sha((HERE / 'evidence.json').read_bytes())
        dump(args.output, result)
        print('validated packaged provenance evidence against public capture pins')
        return 0
    except (ValueError, OSError, KeyError) as error:
        print('input or output failure', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
