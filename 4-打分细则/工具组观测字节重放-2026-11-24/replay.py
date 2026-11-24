"""Offline reference for two bounded capture profiles; never contacts a product.

Sources are bytes keyed by W/A/H then q/w/m (request, response, metadata).
Pins are the same keys with {'bytes': int, 'sha256': str} from a separate register.
`replay` returns measurements and reason codes, not captured strings or identities.
"""

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
import re


class Unknown(ValueError):
    """A carrier or a binding does not support the requested observation."""


def require(ok, reason):
    if not ok:
        raise Unknown(reason)


@dataclass(frozen=True)
class Number:
    source: str

    def token(self):
        s = self.source
        if '.' not in s and 'e' not in s.lower():
            return s
        mantissa, _, exponent = s.lower().partition('e')
        sign = '-' if mantissa.startswith('-') else ''
        integer, _, fraction = mantissa.lstrip('-').partition('.')
        digits = (integer + fraction).lstrip('0')
        if not digits:
            return sign + '0e0'
        trimmed = digits.rstrip('0')
        e = int(exponent or '0') - len(fraction) + len(digits) - len(trimmed)
        return f'{sign}{trimmed}e{e}'


def number(s):
    _, _, exponent = s.lower().partition('e')
    require(len(s) <= 1024 and len(exponent.lstrip('+-')) <= 5
            and abs(int(exponent or '0')) <= 10000, 'number_limit')
    return Number(s)


def nonfinite(_):
    raise Unknown('nonfinite_number')


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate_key')
        result[key] = value
    return result


def canonical(value, depth=0):
    """Canonical JSON text for this profile, not a general JSON standard."""
    require(depth <= 128, 'nesting_limit')
    if type(value) is Number:
        return value.token()
    if type(value) is list:
        return '[' + ','.join(canonical(v, depth + 1) for v in value) + ']'
    if type(value) is dict:
        return '{' + ','.join(canonical(k, depth + 1) + ':' + canonical(value[k], depth + 1)
                              for k in sorted(value)) + '}'
    if type(value) is str:
        value.encode('utf-8')  # Reject lone surrogates, including escaped ones.
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def obj(raw):
    s = raw.decode('utf-8') if type(raw) is bytes else raw
    value = json.loads(s, object_pairs_hook=unique, parse_int=number,
                       parse_float=number, parse_constant=nonfinite)
    require(type(value) is dict, 'object_required')
    canonical(value)  # Validate strings/depth even in fields not used for binding.
    return value


def text(v):
    return type(v) is str and bool(v)


def index(v):
    require(type(v) is Number and re.fullmatch(r'0|[1-9][0-9]{0,8}', v.source), 'index_shape')
    return int(v.source)


def frames(raw, profile):
    # Only LF/CRLF dispatch. Unicode line separators inside JSON strings remain data.
    b = raw.replace(b'\r\n', b'\n')
    require(b.endswith(b'\n\n') and b'\r' not in b, 'unterminated_sse')
    result = []
    for frame in b[:-2].split(b'\n\n'):
        lines = frame.split(b'\n')
        if profile == 'chat':
            require(len(lines) == 1 and lines[0].startswith(b'data: '), 'chat_carrier')
            result.append((None, None if lines[0][6:] == b'[DONE]' else obj(lines[0][6:])))
        else:
            require(len(lines) == 2 and lines[0].startswith(b'event: ')
                    and lines[1].startswith(b'data: '), 'responses_carrier')
            v = obj(lines[1][6:])
            require(text(v.get('type')) and v['type'].encode() == lines[0][7:], 'event_type')
            result.append((v['type'], v))
    return result


@dataclass(frozen=True)
class Call:
    identity: str
    name: str
    arguments: str


def chat_wire(f):
    require(len(f) >= 3 and f[-1][1] is None and all(v is not None for _, v in f[:-1]), 'chat_done')
    identity_fields = ('id', 'object', 'model', 'created')
    first = f[0][1]
    require(text(first.get('id')) and first.get('object') == 'chat.completion.chunk'
            and text(first.get('model')) and type(first.get('created')) is Number
            and re.fullmatch(r'[1-9][0-9]{0,11}', first['created'].source), 'chat_identity')
    parts = []
    ident = name = None
    for n, (_, frame) in enumerate(f[:-1]):
        require(all(frame.get(k) == first[k] for k in identity_fields), 'chat_identity')
        [choice] = frame['choices']
        require(index(choice.get('index')) == 0, 'chat_choice')
        delta = choice['delta']
        if n == len(f) - 2:
            require(choice['finish_reason'] == 'tool_calls' and type(delta) is dict
                    and set(delta) <= {'role', 'content'} and delta.get('role', 'assistant') == 'assistant'
                    and delta.get('content') in (None, ''), 'chat_finish_delta')
            continue
        require(choice.get('finish_reason') is None and set(delta) == {'tool_calls'}, 'chat_delta')
        [t] = delta['tool_calls']
        require(index(t.get('index')) == 0 and t.get('type') == 'function'
                and set(t) <= {'index', 'type', 'id', 'function'}, 'chat_tool_shape')
        fn = t['function']
        if n == 0:
            ident, name = t.get('id'), fn.get('name')
        require(text(ident) and text(name) and t.get('id', ident) == ident and fn.get('name', name) == name
                and set(fn) <= {'name', 'arguments'} and type(fn.get('arguments')) is str, 'chat_tool_fragment')
        parts.append(fn['arguments'])
    return [Call(ident, name, ''.join(parts))]


PHASES = ('response.created', 'response.in_progress', 'response.completed')
BOUNDARIES = ('response.output_item.added', 'response.output_item.done')
ARGUMENTS = ('response.function_call_arguments.delta', 'response.function_call_arguments.done')
AUXILIARY = {'response.' + k for k in ('content_part.added', 'content_part.done', 'reasoning_text.delta',
                                       'reasoning_text.done', 'output_text.delta', 'output_text.done')}


def responses_wire(f):
    events = [e for e, _ in f]
    require(len(f) >= 3 and tuple(events[:2]) == PHASES[:2] and events[-1] == PHASES[-1]
            and not any(e in PHASES for e in events[2:-1]), 'responses_phases')
    require(all(index(v.get('sequence_number')) == n for n, (_, v) in enumerate(f)), 'responses_sequence')
    created, running, completed = (f[i][1]['response'] for i in (0, 1, -1))
    require(text(created.get('id')) and text(created.get('model')) and created.get('object') == 'response'
            and type(created.get('created_at')) is Number
            and all(all(p.get(k) == created[k] for k in ('id', 'model', 'object', 'created_at'))
                    and p.get('error') is None and p.get('incomplete_details') is None
                    for p in (created, running, completed)), 'responses_envelope')
    require(created.get('status') == running.get('status') == 'in_progress'
            and completed.get('status') == 'completed', 'responses_status')
    require(created.get('output') == running.get('output') == [], 'responses_early_output')
    items = completed['output']
    require(type(items) is list and len(items) >= 2 and items[0]['type'] == 'reasoning'
            and all(v['type'] == 'function_call' for v in items[1:])
            and all(text(v.get('id')) for v in items)
            and len({v['id'] for v in items}) == len(items), 'responses_final_shape')
    opened, closed, arg_frames = {}, {}, {}
    for event, v in f[2:-1]:
        require('response' not in v, 'responses_stray_envelope')
        i = index(v.get('output_index'))
        require(i < len(items), 'responses_position')
        target = items[i]
        if event == BOUNDARIES[0]:
            item = v['item']
            require(i not in opened and item['id'] == target['id'] and item['type'] == target['type'],
                    'responses_item_open')
            opened[i] = item
        elif event == BOUNDARIES[1]:
            require(i in opened and i not in closed and canonical(v['item']) == canonical(target),
                    'responses_item_close')
            closed[i] = v['item']
        elif event in AUXILIARY:
            require(i == 0 and i in opened and i not in closed and v.get('item_id') == target['id']
                    and index(v.get('content_index')) == 0, 'responses_aux_lifetime')
        elif event in ARGUMENTS:
            key = 'delta' if event == ARGUMENTS[0] else 'arguments'
            require(i > 0 and i in opened and i not in closed and v.get('item_id') == target['id']
                    and set(v) == {'type', 'sequence_number', 'item_id', 'output_index', key}
                    and type(v[key]) is str, 'responses_arg_identity')
            arg_frames.setdefault(i, []).append((event, v[key]))
        else:
            raise Unknown('responses_event_outside_profile')
    require(len(opened) == len(items) == len(closed), 'responses_item_coverage')
    group = []
    for i, item in enumerate(items[1:], start=1):
        add = opened[i]
        identity, name, arg = item['call_id'], item['name'], item['arguments']
        parts = arg_frames.get(i, [])
        require(set(item) == set(add) == {'id', 'type', 'call_id', 'name', 'arguments', 'status'}
                and text(identity) and text(name) and type(arg) is str and add['call_id'] == identity
                and add['name'] == name and add['arguments'] == '' and add['status'] == 'in_progress'
                and item['status'] == 'completed', 'responses_tool_shape')
        require(len(parts) >= 2 and all(event == ARGUMENTS[0] for event, _ in parts[:-1])
                and parts[-1] == (ARGUMENTS[1], arg) and ''.join(v for _, v in parts[:-1]) == arg,
                'responses_arg_closure')
        group.append(Call(identity, name, arg))
    require(len({c.identity for c in group}) == len(group), 'responses_duplicate_call_id')
    return group


def commitment(raw):
    return {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}


def verified(slot, register, part):
    require(part in slot and part in register, 'source_missing')
    data, pin = slot[part], register[part]
    require(type(data) is bytes and type(pin['bytes']) is int
            and commitment(data) == {k: pin[k] for k in ('bytes', 'sha256')}, 'source_pin_mismatch')
    return data


def packet(profile, ordinal, slot, pins, *, response=False):
    meta = obj(verified(slot, pins, 'm'))
    path = '/api/coding/paas/v4/chat/completions' if profile == 'chat' else '/responses'
    require(meta['seq'] == Number(str(ordinal)) and meta['path'] == path and meta['method'] == 'POST'
            and meta['upstream_status'] == Number('200') and meta['error'] is None
            and meta['response_framing'] == 'rechunked', 'capture_header')
    start, end = (datetime.fromisoformat(meta[k]) for k in ('ts_start', 'ts_done'))
    require(start.utcoffset() is not None and end.utcoffset() is not None and start <= end, 'capture_clock')
    q = verified(slot, pins, 'q')
    w = verified(slot, pins, 'w') if response else None
    for k, raw in (('request', q), ('response', w)):
        if raw is not None:
            summary = commitment(raw)
            require(meta[k + '_body_bytes'] == Number(str(summary['bytes']))
                    and meta[k + '_body_sha256'] == summary['sha256'], 'capture_body_commitment')
    return obj(q), meta, start, end, w


def request_role(profile, q, main=True):
    require(q.get('stream') is True and text(q.get('model')), 'request_profile')
    if profile == 'chat':
        base = {'max_tokens', 'messages', 'model', 'stream', 'stream_options', 'thinking'}
        extra = {'tools', 'tool_stream'} if main else {'reasoning_effort'}
        roles = ['system'] + ['user'] * (4 if main else 1)
        require(set(q) == base | extra and type(q['messages']) is list
                and [v['role'] for v in q['messages'][:len(roles)]] == roles
                and (main or len(q['messages']) == len(roles)), 'chat_request_role')
    else:
        keys = {'client_metadata', 'include', 'input', 'model', 'parallel_tool_calls', 'prompt_cache_key',
                'reasoning', 'store', 'stream', 'tool_choice', 'tools'}
        require(main and set(q) == keys and q.get('store') is False and type(q['input']) is list
                and [v['role'] for v in q['input'][:4]] == ['developer', 'developer', 'user', 'user'],
                'responses_request_role')
    if main:
        require(type(q['tools']) is list and bool(q['tools']), 'tools_missing')


def scope(q, meta):
    md, headers = q['client_metadata'], meta['request_headers']
    normalized = {k.lower(): v for k, v in headers.items()}
    thread, turn, root = (md[k] for k in ('thread_id', 'turn_id', 'root_turn_id'))
    require(len(headers) == len(normalized) and all(map(text, (thread, turn, root)))
            and thread == md['session_id'] == normalized['thread-id'] == normalized['session-id']
            == q['prompt_cache_key'], 'responses_scope')
    witness = 'x-codex-turn-metadata'
    for carrier in (normalized, md):
        if witness in carrier:
            raw = carrier[witness]
            require(type(raw) is str, 'responses_turn_witness')
            embedded = obj(raw)
            require(all(embedded.get(k) == md[k] for k in ('thread_id', 'session_id', 'turn_id', 'root_turn_id')),
                    'responses_turn_witness')
    return thread, turn, root


def continuation(profile, origin, following, wm, hm, calls):
    request_role(profile, following)
    key = 'messages' if profile == 'chat' else 'input'
    a, b = origin[key], following[key]
    n = 5 if profile == 'chat' else 4
    require(len(a) == n and canonical(b[:n]) == canonical(a)
            and origin['model'] == following['model']
            and canonical(origin['tools']) == canonical(following['tools']), 'continuation_prefix')
    if profile == 'chat':
        assistant, result = b[n:]
        [t] = assistant['tool_calls']
        require(assistant['role'] == 'assistant' and t['type'] == 'function' and result['role'] == 'tool'
                and type(result['content']) is str and t['id'] == result['tool_call_id'], 'chat_continuation_shape')
        require(not any(x.get('tool_call_id') == t['id'] or any(y.get('id') == t['id']
                        for y in x.get('tool_calls', [])) for x in a), 'chat_reused_call_id')
        group = [Call(t['id'], t['function']['name'], t['function']['arguments'])]
    else:
        require(scope(origin, wm) == scope(following, hm), 'responses_cross_turn')
        count = len(calls)
        require(len(b) == n + 1 + 2 * count and b[n]['type'] == 'reasoning', 'responses_continuation_shape')
        passed, results = b[n + 1:n + 1 + count], b[n + 1 + count:]
        require(all(set(t) == {'type', 'call_id', 'name', 'arguments', 'status'}
                    and t['type'] == 'function_call' and t['status'] == 'completed' for t in passed)
                and all(t['type'] == 'function_call_output' and text(t.get('id')) and type(t['output']) is str
                        for t in results) and len({t['id'] for t in results}) == count, 'responses_continuation_carrier')
        ids = [t['call_id'] for t in passed]
        require(ids == [t['call_id'] for t in results] and not any(x.get('call_id') in ids for x in a),
                'responses_result_reference')
        group = [Call(t['call_id'], t['name'], t['arguments']) for t in passed]
    require([(c.identity, c.name) for c in group] == [(c.identity, c.name) for c in calls]
            and all(type(c.arguments) is str for c in group), 'continuation_group_identity')
    return group


def reasoned(action):
    try:
        return action(), None
    except Unknown as e:
        return None, str(e)
    except (KeyError, IndexError, AttributeError, TypeError, ValueError, RecursionError):
        # Error text from the carrier (including user/tool strings) is never emitted.
        return None, 'unsupported_or_invalid_carrier'


def replay(profile, source, pins):
    """Compare W/H without treating physical bytes, argument text or canonical values as interchangeable."""
    require(profile in ('chat', 'responses'), 'unsupported_profile')
    sources = ('W', 'A', 'H') if profile == 'chat' else ('W', 'H')
    physical = {}
    for label in sources:
        slot, register = source.get(label, {}), pins.get(label, {})
        physical[label] = {}
        for part in (('q', 'm', 'w') if label == 'W' else ('q', 'm')):
            raw, error = reasoned(lambda: verified(slot, register, part))
            physical[label][part] = {'bytes': len(raw) if raw is not None else None, 'error': error}

    def get_packet(label, seq, response=False):
        return packet(profile, seq, source.get(label, {}), pins.get(label, {}), response=response)

    def get_wire():
        q, wm, _, end, raw = get_packet('W', 1, True)
        request_role(profile, q)
        key, prefix_size = ('messages', 5) if profile == 'chat' else ('input', 4)
        require(len(q[key]) == prefix_size, 'origin_prefix_size')
        if profile == 'responses':
            scope(q, wm)
        group = (chat_wire if profile == 'chat' else responses_wire)(frames(raw, profile))
        decl = [t['function']['name'] if profile == 'chat' else t['name']
                for t in q['tools'] if t.get('type') == 'function']
        require(all(decl.count(c.name) == 1 for c in group), 'tool_declaration')
        return q, wm, end, group

    wire, wire_error = reasoned(get_wire)

    def get_history():
        require(wire is not None, 'wire_unavailable')
        q, wm, end, group = wire
        h, hm, start, _, _ = get_packet('H', 3 if profile == 'chat' else 2)
        require(end <= start, 'continuation_clock')
        if profile == 'chat':
            aux, *_ = get_packet('A', 2)
            request_role(profile, aux, False)
        return continuation(profile, q, h, wm, hm, group)

    history, history_error = reasoned(get_history)
    wg = None if wire is None else wire[-1]

    def layers(g, error):
        if g is None:
            return {'argument_bytes': None, 'canonical_bytes': None, 'carrier_error': error,
                    'object_errors': None}, None
        normalized = [reasoned(lambda: canonical(obj(c.arguments)).encode('utf-8')) for c in g]
        return {'argument_bytes': [len(c.arguments.encode('utf-8')) for c in g],
                'canonical_bytes': [len(v) if v is not None else None for v, _ in normalized],
                'carrier_error': None, 'object_errors': [e for _, e in normalized]}, normalized

    left, wl = layers(wg, wire_error)
    right, hl = layers(history, history_error)
    raw_equal = None if wg is None or history is None else (
        [c.arguments for c in wg] == [c.arguments for c in history])
    equal = None if wl is None or hl is None or any(e is not None for _, e in wl + hl) else (
        [v for v, _ in wl] == [v for v, _ in hl])
    return {'physical': physical, 'W': left, 'H': right, 'argument_text_equal': raw_equal,
            'group': 'unknown' if equal is None else 'equal' if equal else 'different'}


def signature(profile, raw):
    """Carrier-only (name, canonical parameter bytes) tuple. Does not authenticate a run or W→H binding."""
    require(profile in ('chat', 'responses'), 'unsupported_profile')
    calls = (chat_wire if profile == 'chat' else responses_wire)(frames(raw, profile))
    return tuple((c.name, canonical(obj(c.arguments)).encode('utf-8')) for c in calls)
