"""Finite capture projection: framing and terminal evidence, not a provider client."""
import hashlib
import json
import re
from dataclasses import dataclass

LINE_END = re.compile(rb'\r\n|[\r\n]')
BOM = b'\xef\xbb\xbf'
NORMAL = 'response.completed'
OTHER_TERMINALS = frozenset({'response.failed', 'response.cancelled',
                             'response.canceled', 'response.incomplete', 'error'})


@dataclass(frozen=True)
class Frame:
    start_line: int
    dispatch_line: int
    data: bytes
    types: tuple


@dataclass(frozen=True)
class Physical:
    frames: tuple
    tail_data_lines: int
    tail_start_line: int
    bom: bool
    initial_bom_count: int
    newline_kinds: tuple
    non_data_blocks: int


def split_capture(body):
    # Validate first, then delimit only physical CR/LF boundaries, never U+2028.
    body.decode('utf-8', errors='strict')
    n_bom = 0
    while body.startswith(BOM, n_bom * len(BOM)):
        n_bom += 1
    bom = bool(n_bom)
    # At most one may be stripped. Extra markers are reported explicitly.
    content = body[len(BOM):] if bom else body
    frames, data, types = [], [], []
    non_data, start_line, n, pos, nonempty = 0, 0, 0, 0, False
    kinds = set()

    def accept_field(line, ordinal):
        nonlocal start_line, nonempty
        if not start_line:
            start_line = ordinal
        nonempty = True
        key, _, value = line.partition(b':')
        if value.startswith(b' '):
            value = value[1:]
        if key == b'data':
            data.append(value)
        elif key == b'event':
            types.append(value)

    for end in LINE_END.finditer(content):
        n += 1
        kinds.add(end.group())
        line = content[pos:end.start()]
        pos = end.end()
        if line:
            accept_field(line, n)
            continue
        if data:
            frames.append(Frame(start_line, n, b'\n'.join(data), tuple(types)))
        elif nonempty:
            non_data += 1
        data.clear()
        types.clear()
        start_line, nonempty = 0, False
    if pos != len(content):
        accept_field(content[pos:], n + 1)
    return Physical(tuple(frames), len(data), start_line, bom, n_bom,
                    tuple(sorted(k.hex() for k in kinds)), non_data)


def strict_obj(raw):
    def pairs(items):
        d = {}
        for k, v in items:
            if k in d:
                raise ValueError('duplicated decoded key')
            d[k] = v
        return d

    def reject_constant(_):
        raise ValueError('non-finite constant')

    obj = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                     parse_constant=reject_constant,
                     parse_int=lambda _: 0, parse_float=lambda _: 0)
    if not isinstance(obj, dict):
        raise ValueError('data is not an object')
    return obj


def projection(body, family):
    if family not in ('chat', 'codex'):
        raise ValueError('unknown family')
    try:
        ph = split_capture(body)
    except UnicodeDecodeError:
        return {'closed': False, 'issues': [{'code': 'INVALID_UTF8', 'line': None}],
                'frames': [], 'payloads': [], 'undispatched_data_lines': None}
    issues, payloads, frame_notes, terminals, response_ids = [], [], [], [], set()
    finish_frames = 0

    def issue(code, line):
        issues.append({'code': code, 'line': line})

    if ph.initial_bom_count > 1:
        issue('REPEATED_INITIAL_BOM', 1)

    for idx, f in enumerate(ph.frames):
        note = {'start': f.start_line, 'dispatch': f.dispatch_line,
                'bytes': len(f.data), 'sha256': hashlib.sha256(f.data).hexdigest(),
                'kind': None}
        frame_notes.append(note)
        if len(f.types) > 1:
            issue('REPEATED_EVENT_FIELD', f.start_line)
        ev = f.types[-1] if f.types else b''
        if family == 'chat' and ev not in (b'', b'message'):
            issue('CHAT_EVENT_LABEL', f.start_line)
        if f.data == b'[DONE]':
            if family == 'chat':
                terminals.append(idx)
            else:
                issue('RESPONSES_UNEXPECTED_DONE', f.start_line)
            note['kind'] = 'done'
            continue
        try:
            obj = strict_obj(f.data)
        except (ValueError, RecursionError):
            issue('DATA_NOT_STRICT_OBJECT', f.start_line)
            continue
        payloads.append(note.copy())
        if family == 'chat':
            note['kind'] = 'chat_object'
            cs = obj.get('choices')
            if isinstance(cs, list) and any(isinstance(c, dict) and
                    isinstance(c.get('finish_reason'), str) and
                    bool(c['finish_reason']) for c in cs):
                finish_frames += 1
            continue
        kind = obj.get('type')
        if not isinstance(kind, str) or not kind:
            issue('MISSING_DATA_TYPE', f.start_line)
            continue
        try:
            matches = ev == kind.encode('utf-8')
        except UnicodeEncodeError:
            matches = False
        if not matches:
            issue('EVENT_DATA_TYPE_MISMATCH', f.start_line)
        note['kind'] = 'responses_object'
        if 'response' in obj:
            r = obj['response']
            if not isinstance(r, dict) or not isinstance(r.get('id'), str) or not r['id']:
                issue('MISSING_RESPONSE_ID', f.start_line)
            else:
                response_ids.add(r['id'])
            if kind == NORMAL and (not isinstance(r, dict) or r.get('status') != 'completed'):
                issue('TERMINAL_RESPONSE_STATUS', f.start_line)
        elif kind == NORMAL:
            issue('MISSING_TERMINAL_RESPONSE', f.start_line)
        if kind in OTHER_TERMINALS:
            issue('NON_NORMAL_TERMINAL', f.start_line)
        if kind == NORMAL:
            terminals.append(idx)
    if ph.tail_data_lines:
        issue('UNDISPATCHED_EOF_DATA', ph.tail_start_line)
    if not terminals:
        issue('MISSING_NORMAL_TERMINAL', None)
    elif len(terminals) != 1:
        issue('DUPLICATE_NORMAL_TERMINAL', ph.frames[terminals[1]].start_line)
    elif terminals[0] != len(ph.frames) - 1:
        issue('DATA_AFTER_NORMAL_TERMINAL', ph.frames[terminals[0] + 1].start_line)
    if family == 'chat' and not finish_frames:
        issue('CHAT_FINISH_NOT_SEEN', None)
    if len(response_ids) > 1:
        issue('RESPONSE_ID_SPLIT', None)
    return {'closed': not issues, 'issues': issues, 'frames': frame_notes,
            'payloads': payloads, 'undispatched_data_lines': ph.tail_data_lines,
            'finish_frames': finish_frames, 'normal_terminal_count': len(terminals),
            'distinct_response_ids': len(response_ids), 'bom': ph.bom,
            'initial_bom_count': ph.initial_bom_count,
            'newline_kinds_hex': ph.newline_kinds, 'non_data_blocks': ph.non_data_blocks}
