"""Python 3.9+, stdlib only. Independent implementation of the written finite spec.
No product import, vendor code, VM, filesystem read, tool invocation or model.
"""
import hashlib
import json

PATH = '/synthetic/same-path.txt'
MARKER = '... (line truncated to 2000 chars)'

def u16(text):
    return len(text.encode('utf-16-le', 'surrogatepass')) // 2

def prefix(text, units):
    return text.encode('utf-16-le', 'surrogatepass')[:units * 2].decode('utf-16-le', 'surrogatepass')

def display_bytes(text):
    # UTF-8 display encoding replaces an unpaired unit, unlike JSON escaping.
    return text.encode('utf-16-le', 'surrogatepass').decode('utf-16-le', 'replace').encode('utf-8')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def project(text, offset=1, limit=2000, path=PATH):
    if type(offset) is not int or type(limit) is not int or offset < 1 or limit < 1:
        raise ValueError('positive integer line pagination required')
    physical = text.split('\n') if text else []
    if text.endswith('\n'):
        physical.pop()
    selected, size, capped = [], 0, False
    for number, physical_line in enumerate(physical, 1):
        if number < offset or len(selected) >= limit or capped:
            continue
        bounded = prefix(physical_line, 2001)
        if bounded.endswith('\r'):
            bounded = bounded[:-1]
        visible = prefix(bounded, 2000) + MARKER if u16(bounded) > 2000 else bounded
        increment = len(display_bytes(visible)) + bool(selected)
        if size + increment > 51200:
            capped = True
        else:
            size += increment
            selected.append((number, visible))
    total = len(physical)
    if offset > total and not (offset == 1 and total == 0):
        raise ValueError('line offset outside source')
    end = selected[-1][0] if selected else offset - 1
    if capped:
        footer = '(Output capped. Showing lines %d-%d. Use offset=%d to continue.)' % (offset, end, end + 1)
    elif end < total:
        footer = '(Showing lines %d-%d of %d. Use offset=%d to continue.)' % (offset, end, total, end + 1)
    else:
        footer = '(End of file - total %d lines)' % total
    numbered = '\n'.join('%d: %s' % item for item in selected)
    inner = numbered + '\n\n' + footer if selected else footer
    rendered = '<path>%s</path>\n<type>file</type>\n<content>\n%s\n</content>' % (path, inner)
    return dict(rendered=rendered, lines=selected, total_lines=total,
                selected_utf8_bytes=size, byte_capped=capped,
                next_offset=end + 1 if end < total else None)

def pairs():
    return [
        ('crlf', 'alpha\r\nbeta\r\n', 'alpha\nbeta\n', 'CRLF', 'LF'),
        ('terminal-lf', 'alpha\n', 'alpha', True, False),
        ('terminal-cr', 'alpha\r', 'alpha', True, False),
        ('json-decision', '{"memo":"' + 'x' * 1991 + '","decision":"ALLOW"}\n',
         '{"memo":"' + 'x' * 1991 + '","decision":"DENY!"}\n', 1, 0),
        ('astral-unit', 'x' * 1999 + '\U0001f600A\n', 'x' * 1999 + '\U0001f601B\n', 'U+1F600', 'U+1F601'),
        ('cr-unmarked', 'q' * 2000 + '\n', 'q' * 2000 + '\rSECRET\n', False, True),
    ]

def fingerprint(text):
    return dict(utf8_sha256=sha(text.encode('utf-8')), utf8_bytes=len(text.encode('utf-8')),
                codepoints=len(text), utf16_units=u16(text))

def should_bound(tool_name, own_keys, accepted=True, parent=False):
    return accepted and not parent and 'value' not in own_keys and tool_name != 'read'

def need(condition, reason):
    if not condition:
        raise ValueError(reason)

def proof():
    collisions = []
    for name, a, b, aa, ab in pairs():
        va, vb = project(a), project(b)
        need(a != b and aa != ab, 'sources_or_answers_not_distinct:' + name)
        need(va['rendered'] == vb['rendered'], 'complete_display_not_equal:' + name)
        body = va['rendered']
        need(json.loads(json.dumps(body, ensure_ascii=True)) == body, 'json_code_units_changed:' + name)
        if name == 'cr-unmarked':
            need(MARKER not in body and '(End of file' in body, 'cr_unmarked_claim_invalid')
        collisions.append(dict(id=name, source_A=fingerprint(a), source_B=fingerprint(b),
            task_answers=[aa, ab], complete_display_equal=True,
            display_utf8_sha256=sha(display_bytes(body)),
            display_utf16le_sha256=sha(body.encode('utf-16-le', 'surrogatepass')),
            display_utf8_bytes=len(display_bytes(body)), display_utf16_units=u16(body),
            marker_present=MARKER in body, eof_present='(End of file' in body,
            json_roundtrip_same_units=json.loads(json.dumps(body, ensure_ascii=True)) == body))
    negative = project('q' * 2000 + 'ZSECRET\n')['rendered']
    need(MARKER in negative and negative != project('q' * 2000 + '\n')['rendered'], 'cr_negative_control_failed')
    windows = []
    for label, line in [('ascii', 'x' * 2000), ('cjk', '\u754c' * 2000), ('astral', '\U0001f680' * 1000)]:
        source, offset, pages, recovered = '\n'.join([line] * 30), 1, [], []
        while offset:
            p = project(source, offset)
            pages.append(dict(offset=offset, lines=len(p['lines']), bytes=p['selected_utf8_bytes']))
            recovered.extend(v for _, v in p['lines'])
            following = p['next_offset']
            need(following is None or (type(following) is int and following > offset), 'byte_window_not_advancing:' + label)
            need(len(pages) <= 30, 'byte_window_count_excess:' + label)
            offset = following
        need('\n'.join(recovered) == source, 'byte_window_reconstruction_failed:' + label)
        windows.append(dict(kind=label, pages=pages, all_30_lines_recovered=True,
                            source=fingerprint(source)))
    emoji_view = project(pairs()[4][1])['lines'][0][1]
    need(len(emoji_view) >= 2000 and ord(emoji_view[1999]) == 0xd83d, 'astral_surrogate_unit_changed')
    need(display_bytes('\ud83d') == '\ufffd'.encode('utf-8'), 'surrogate_display_encoding_changed')
    need(json.loads(json.dumps('\ud83d')) == '\ud83d', 'surrogate_json_unit_changed')
    own_value = [dict(own_value=x, read_bounded=should_bound('read', ['value']),
                      alias_bounded=should_bound('alias', ['value']), reason='own-property bypass')
                 for x in ['undefined', 'null', 'false']]
    return dict(schema='read-projection-proof-v1', status='finite_cleanroom_proof',
        not_native_execution=True, path=PATH, collisions=collisions,
        negative_control=dict(cr_replaced_with_z_has_marker=True),
        unicode=dict(visible_unpaired_unit='0xd83d', json_escape='\\ud83d',
                     display_utf8_replacement='U+FFFD', json_preserves_unit=True),
        byte_windows=windows,
        conditional_post_execute=dict(assumptions=['accepted', 'no parent delegation'],
            no_own_value=dict(read_bounded=should_bound('read', []), alias_bounded=should_bound('alias', [])),
            read_opaque_call_ids=dict(opaque_A=should_bound('read', []), opaque_B=should_bound('read', [])),
            alias_opaque_call_ids=dict(opaque_A=should_bound('alias', []), opaque_B=should_bound('alias', [])), 
            own_values=own_value, inherited_value_is_not_own=True),
        limits=['finite source-conditioned proof, not runtime identity',
                'no inference about all recovery strategies, grep or shell',
                'EOF and no marker do not imply source-byte preservation',
                'byte-window pagination differs from inaccessible line suffixes'])

if __name__ == '__main__':
    print(json.dumps(proof(), ensure_ascii=True, sort_keys=True, indent=2))
