# -*- coding: utf-8 -*-
"""Offline conditional countermodels, not product or official API validation."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

BASELINE = '52b5e81531f3171292240a01c4ef3e4cb4b84eb8'
PINS = {
    '4-打分细则/请求侧观测规范-2026-11-08/README.md':
        '7bd025e6b4ebaae78210fd5a50bc06c7f9be12511269ad5dc282b350102fe735',
    '4-打分细则/机制重复口径澄清-2026-11-12/verify.py':
        '045475f5dd05efdf56e102ceb8b2eb4e98f455d818b80a7b0af74fca6f0c0d1d',
}
DSH_INPUT_TYPES = {'user/message', 'request/header', 'request/context'}
POLICIES = ('full_history', 'drop_complete_old_exchange', 'reference_results')
CUTS = (2, 4, 6)  # Counts of source payloads, never usage-derived event offsets.
TOOLS = [{
    'type': 'function', 'name': 'lookup',
    'description': 'Synthetic record lookup; no executable endpoint.',
    'parameters': {'type': 'object', 'properties': {'key': {'type': 'string'}},
                   'required': ['key'], 'additionalProperties': True},
    'strict': False,
}]
TOP_LEVEL_METADATA = {'id', 'internal_chat_message_metadata_passthrough',
                      'phase', 'status'}


class ProofError(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise ProofError(message)


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def sha(value):
    return hashlib.sha256(value).hexdigest()


def exact_keys(value, keys, label):
    need(type(value) is dict and set(value) == set(keys), label + ' keys')


def nonempty_string(value, label):
    need(type(value) is str and bool(value), label + ' string')
    value.encode('utf-8')


def positive_int(value, label):
    need(type(value) is int and value > 0, label + ' positive integer')


def unique_argument_object(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'duplicate argument key')
        result[key] = value
    return result


def reject_nonfinite_argument(value):
    raise ProofError('nonfinite argument constant')


def source_bindings(root):
    root = Path(root).resolve(strict=True)
    bindings = []
    for relative, expected in PINS.items():
        item = root
        for component in Path(relative).parts:
            item = item / component
            need(not item.is_symlink(), 'symlink source: ' + relative)
        need(item.resolve(strict=True).is_relative_to(root), 'source escapes root')
        raw = item.read_bytes()
        need(sha(raw) == expected, 'source SHA mismatch: ' + relative)
        bindings.append({'path': relative, 'sha256': expected, 'bytes': len(raw)})
    return bindings


def dsh_s3(events):
    need(type(events) is list, 'DSH event list')
    total = 0
    for event in events:
        need(type(event) is dict and type(event.get('type')) is str, 'DSH event')
        if event['type'] in DSH_INPUT_TYPES:
            need(type(event.get('data')) is dict, 'selected DSH data')
            total += len(canon(event))
    return total


def response_payloads(events):
    need(type(events) is list, 'Codex event list')
    result = []
    for event in events:
        need(type(event) is dict and type(event.get('type')) is str, 'Codex event')
        if event['type'] == 'response_item':
            need(type(event.get('payload')) is dict, 'response payload object')
            result.append(copy.deepcopy(event['payload']))
    return result


def codex_r3(events):
    response_payloads(events)  # Validate the complete selected input first.
    segments, pending = [], 0
    for event in events:
        if event['type'] == 'response_item':
            pending += len(canon(event['payload']))
        elif event['type'] == 'token_usage_record' and pending:
            segments.append(pending)
            pending = 0
    tail = pending
    if pending:
        segments.append(pending)
    return {'bytes': sum(segments), 'segments': segments, 'unclosed_tail_bytes': tail}


def source_message(role, *texts):
    return {'type': 'message', 'role': role,
            'content': [{'type': 'input_text', 'text': text} for text in texts]}


def message_text(payload):
    need(type(payload.get('content')) is list and bool(payload['content']), 'content list')
    texts = []
    for part in payload['content']:
        exact_keys(part, ('type', 'text'), 'source text leaf')
        need(part['type'] == 'input_text' and type(part['text']) is str, 'input text')
        part['text'].encode('utf-8')
        texts.append(part['text'])
    return ''.join(texts)


def project_payload(payload):
    """Whitelisted top-level metadata only; never erase business id fields."""
    need(type(payload) is dict, 'source payload')
    canon(payload)
    kind = payload.get('type')
    fields = {
        'message': {'type', 'role', 'content'},
        'function_call': {'type', 'call_id', 'name', 'arguments'},
        'function_call_output': {'type', 'call_id', 'output'},
    }
    need(kind in fields, 'unsupported source payload type')
    need(set(payload) - TOP_LEVEL_METADATA == fields[kind], 'source payload fields')
    if kind == 'message':
        need(payload['role'] in ('developer', 'user', 'assistant'), 'source role')
        return {'role': payload['role'],
                'content': [{'type': 'input_text', 'text': message_text(payload)}]}
    return {key: copy.deepcopy(payload[key]) for key in fields[kind]}


def validate_input(items):
    """A deliberately small Responses-like grammar, not an official protocol claim."""
    need(type(items) is list and len(items) >= 2, 'request input list')
    need([x.get('role') if type(x) is dict else None for x in items[:2]] ==
         ['developer', 'user'], 'initial roles')
    seen, pending = set(), set()
    for item in items:
        need(type(item) is dict, 'input item object')
        if 'role' in item:
            exact_keys(item, ('role', 'content'), 'message')
            need(item['role'] in ('developer', 'user', 'assistant'), 'message role')
            message_text(item)
            need(not pending, 'message before pending output')
        elif item.get('type') == 'function_call':
            exact_keys(item, ('type', 'call_id', 'name', 'arguments'), 'function call')
            nonempty_string(item['call_id'], 'call_id')
            need(item['call_id'] not in seen, 'duplicate call_id')
            need(not pending, 'parallel calls outside this serial model')
            need(item['name'] == 'lookup', 'unregistered function')
            need(type(item['arguments']) is str, 'arguments string')
            args = json.loads(item['arguments'], object_pairs_hook=unique_argument_object,
                              parse_constant=reject_nonfinite_argument)
            need(type(args) is dict and type(args.get('key')) is str, 'lookup arguments')
            canon(args)
            seen.add(item['call_id'])
            pending.add(item['call_id'])
        elif item.get('type') == 'function_call_output':
            exact_keys(item, ('type', 'call_id', 'output'), 'function output')
            nonempty_string(item['call_id'], 'output call_id')
            need(item['call_id'] in pending, 'output before call or duplicate output')
            need(type(item['output']) is str, 'output text')
            item['output'].encode('utf-8')
            pending.remove(item['call_id'])
        else:
            raise ProofError('unsupported request item')
    need(not pending, 'dangling function call')


def validate_request(body):
    exact_keys(body, ('model', 'input', 'tools', 'reasoning'), 'request body')
    need(body['model'] == 'synthetic-model-not-an-endpoint', 'synthetic model')
    need(canon(body['tools']) == canon(TOOLS), 'tool schema changed')
    need(canon(body['reasoning']) == canon({'effort': 'low'}), 'declared effort changed')
    validate_input(body['input'])
    canon(body)


def render_request(source_prefix, policy):
    """Receives only the available prefix. No future payload or usage access."""
    need(policy in POLICIES, 'unknown renderer')
    need(type(source_prefix) is list, 'source prefix list')
    items = [project_payload(x) for x in source_prefix]
    validate_input(items)
    if policy == 'drop_complete_old_exchange':
        output_ids = [x['call_id'] for x in items if x.get('type') == 'function_call_output']
        removed = set(output_ids[:-1])
        items = [x for x in items if x.get('call_id') not in removed]
    elif policy == 'reference_results':
        for item in items:
            if item.get('type') == 'function_call_output':
                item['output'] = '<external-result ref=artifact:' + item['call_id'] + '>'
    body = {'model': 'synthetic-model-not-an-endpoint', 'input': items,
            'tools': copy.deepcopy(TOOLS), 'reasoning': {'effort': 'low'}}
    validate_request(body)
    return body


def render_sequence(events, policy, cuts=CUTS):
    payloads = response_payloads(events)
    need(type(cuts) in (list, tuple) and bool(cuts), 'cut schedule')
    need(all(type(cut) is int and 0 < cut <= len(payloads) for cut in cuts), 'cut range/type')
    need(list(cuts) == sorted(set(cuts)), 'cuts must be strictly increasing')
    result = []
    for ordinal, cut in enumerate(cuts, 1):
        prefix = payloads[:cut]
        body = render_request(prefix, policy)
        raw = canon(body)
        result.append({'request_id': 'q' + str(ordinal), 'source_item_cut': cut,
                       'source_prefix_sha256': sha(canon(prefix)),
                       'body': body, 'body_bytes': len(raw), 'body_sha256': sha(raw)})
    return result


def sequence_summary(rendered):
    return {'request_ids': [x['request_id'] for x in rendered],
            'source_item_cuts': [x['source_item_cut'] for x in rendered],
            'source_prefix_sha256': [x['source_prefix_sha256'] for x in rendered],
            'body_bytes': [x['body_bytes'] for x in rendered],
            'body_sha256': [x['body_sha256'] for x in rendered],
            'sum_body_bytes': sum(x['body_bytes'] for x in rendered)}


def receipts_for(rendered, request_ids):
    return [{key: row[key] for key in ('request_id', 'source_item_cut',
             'source_prefix_sha256', 'body_bytes', 'body_sha256')}
            for row in rendered if row['request_id'] in request_ids]


def validate_fingerprint(row, label):
    nonempty_string(row['request_id'], label + ' request_id')
    positive_int(row['source_item_cut'], label + ' cut')
    positive_int(row['body_bytes'], label + ' bytes')
    for field in ('source_prefix_sha256', 'body_sha256'):
        need(type(row[field]) is str and len(row[field]) == 64 and
             all(c in '0123456789abcdef' for c in row[field]), label + ' SHA')


def compatible(rendered, receipts):
    need(type(rendered) is list and bool(rendered), 'rendered sequence')
    indexed, previous_cut = {}, 0
    fields = ('request_id', 'source_item_cut', 'source_prefix_sha256',
              'body_bytes', 'body_sha256')
    for row in rendered:
        exact_keys(row, fields + ('body',), 'rendered row')
        validate_fingerprint(row, 'rendered')
        need(row['request_id'] not in indexed and row['source_item_cut'] > previous_cut,
             'duplicate renderer identity or unordered cuts')
        validate_request(row['body'])
        raw = canon(row['body'])
        need(len(raw) == row['body_bytes'] and sha(raw) == row['body_sha256'],
             'rendered body fingerprint mismatch')
        indexed[row['request_id']] = row
        previous_cut = row['source_item_cut']
    need(type(receipts) is list, 'receipt list')
    ids = set()
    for receipt in receipts:
        exact_keys(receipt, fields, 'receipt')
        validate_fingerprint(receipt, 'receipt')
        need(receipt['request_id'] not in ids, 'duplicate receipt identity')
        ids.add(receipt['request_id'])
    # Validate all records before comparison, even after an earlier mismatch.
    return all(receipt['request_id'] in indexed and
               all(indexed[receipt['request_id']][key] == receipt[key] for key in fields)
               for receipt in receipts)


def candidate_status(renderers, receipts):
    candidates = [policy for policy, rows in renderers.items() if compatible(rows, receipts)]
    return {'compatible_renderers': candidates, 'count': len(candidates),
            'state': ('inconsistent' if not candidates else
                      'identified_within_declared_renderer_class' if len(candidates) == 1 else
                      'ambiguous_within_declared_renderer_class')}


def fixed_source_log():
    payloads = [source_message('developer', 'Use lookup; preserve each key.'),
                source_message('user', 'Return alpha and beta records.'),
                {'type': 'function_call', 'call_id': 'c1', 'name': 'lookup',
                 'arguments': '{"key":"alpha"}'},
                {'type': 'function_call_output', 'call_id': 'c1',
                 'output': 'ALPHA=' + 'a' * 173},
                {'type': 'function_call', 'call_id': 'c2', 'name': 'lookup',
                 'arguments': '{"key":"beta"}'},
                {'type': 'function_call_output', 'call_id': 'c2',
                 'output': 'BETA=' + '中😀' * 29},
                source_message('assistant', 'Synthetic terminal reply.')]
    events = []
    for index, payload in enumerate(payloads):
        events.append({'type': 'response_item', 'payload': payload})
        if index in (2, 4):
            events.append({'type': 'token_usage_record', 'payload': {'marker': index}})
    return events


def dsh_events(output, seq=1, at='T0', user='Read the synthetic record.'):
    return [
        {'type': 'request/header', 'data': {'tools': TOOLS}},
        {'type': 'request/context', 'data': {'model': 'synthetic', 'contextWindow': 10000}},
        {'type': 'user/message', 'seq': seq, 'time': at, 'data': {'text': user}},
        {'type': 'tool/result', 'data': {'text': output}},
    ]


def dsh_body(events):
    """Declared toy sender. It uses data, not logging seq/time fields."""
    users = [x['data']['text'] for x in events if x['type'] == 'user/message']
    outputs = [x['data']['text'] for x in events if x['type'] == 'tool/result']
    need(len(users) == len(outputs) == 1, 'toy DSH source shape')
    prefix = [source_message('developer', 'Use lookup; preserve each key.'),
              source_message('user', users[0]),
              {'type': 'function_call', 'call_id': 'd1', 'name': 'lookup',
               'arguments': '{"key":"data"}'},
              {'type': 'function_call_output', 'call_id': 'd1', 'output': outputs[0]}]
    return render_request(prefix, 'full_history')


def run_models():
    cases = {}
    left, right = dsh_events('x' * 8), dsh_events('x' * 800)
    body_left, body_right = canon(dsh_body(left)), canon(dsh_body(right))
    need(dsh_s3(left) == dsh_s3(right) and body_left != body_right, 'S3 blind witness')
    cases['s3_excludes_tool_return'] = {
        'selected_s3_bytes': [dsh_s3(left), dsh_s3(right)],
        'same_full_log': canon(left) == canon(right),
        'body_bytes': [len(body_left), len(body_right)],
        'body_sha256': [sha(body_left), sha(body_right)],
        'tool_text_utf8_bytes': [8, 800],
    }
    log = fixed_source_log()
    before = canon(log)
    renderers = {policy: render_sequence(log, policy) for policy in POLICIES}
    summaries = {policy: sequence_summary(rows) for policy, rows in renderers.items()}
    need(canon(log) == before, 'renderer mutated source log')
    need(len({x['sum_body_bytes'] for x in summaries.values()}) == 3, 'three byte targets')
    need(len({tuple(x['source_prefix_sha256']) for x in summaries.values()}) == 1,
         'source prefix/cut changed')
    cases['same_source_log_different_renderers'] = {
        'full_source_log_sha256': sha(before), 'r3': codex_r3(log),
        'cut_units': 'source-payload-count, independent of usage',
        'log_semantics': 'synthetic pre-serialization source events, not final-send copies',
        'compatibility': 'prefix-only serial structural compatibility in declared grammar',
        'renderers': summaries,
        'reference_readback': None, 'semantic_equivalence_claimed': False,
    }
    changed = dsh_events('x' * 8, seq=100000, at='a-much-longer-clock-label')
    need(dsh_s3(left) != dsh_s3(changed) and canon(dsh_body(left)) == canon(dsh_body(changed)),
         'S3 nuisance witness')
    cases['s3_logging_metadata_only'] = {'s3_bytes': [dsh_s3(left), dsh_s3(changed)],
        'body_sha256': [sha(canon(dsh_body(left))), sha(canon(dsh_body(changed)))]}
    enriched = copy.deepcopy(log)
    enriched[0]['payload']['id'] = 'a' * 101
    need(codex_r3(log)['bytes'] != codex_r3(enriched)['bytes'] and
         sequence_summary(render_sequence(log, 'full_history'))['body_sha256'] ==
         sequence_summary(render_sequence(enriched, 'full_history'))['body_sha256'],
         'R3 metadata witness')
    cases['r3_top_level_metadata_only'] = {'r3_bytes': [codex_r3(log)['bytes'],
        codex_r3(enriched)['bytes']], 'same_body_sequence': True,
        'stripped_paths': ['response_item.payload.id'], 'recursive_business_erasure': False}
    split = copy.deepcopy(log)
    original_text = message_text(split[1]['payload'])
    split[1]['payload']['content'] = [{'type': 'input_text', 'text': original_text[:7]},
                                    {'type': 'input_text', 'text': original_text[7:]}]
    need(codex_r3(log)['bytes'] != codex_r3(split)['bytes'] and
         message_text(log[1]['payload']) == message_text(split[1]['payload']) and
         canon(render_sequence(log, 'full_history')[-1]['body']) ==
         canon(render_sequence(split, 'full_history')[-1]['body']), 'leaf split witness')
    cases['r3_leaf_packaging'] = {'r3_bytes': [codex_r3(log)['bytes'], codex_r3(split)['bytes']],
        'same_ordered_text': True, 'same_body_under_declared_joining_sender': True,
        'semantic_equivalence_of_actual_model': None}
    moved = [copy.deepcopy(x) for x in log if x['type'] != 'token_usage_record']
    moved.insert(1, {'type': 'token_usage_record', 'payload': {'marker': 'early'}})
    moved.insert(6, {'type': 'token_usage_record', 'payload': {'marker': 'middle'}})
    old_measure, moved_measure = codex_r3(log), codex_r3(moved)
    need(old_measure['bytes'] == moved_measure['bytes'] and
         old_measure['segments'] != moved_measure['segments'] and
         canon(render_sequence(log, 'full_history')) ==
         canon(render_sequence(moved, 'full_history')), 'usage boundary witness')
    cases['usage_is_not_a_send_cut'] = {'r3_before': old_measure, 'r3_after': moved_measure,
                                      'same_sender_cuts_and_bodies': True}
    visible = dsh_events('x' * 8, user='A changed visible source task.')
    need(dsh_s3(left) != dsh_s3(visible) and canon(dsh_body(left)) != canon(dsh_body(visible)),
         'positive visible-content control')
    cases['positive_visible_content_control'] = {'s3_changes': True, 'body_changes': True}
    none = candidate_status(renderers, [])
    first = candidate_status(renderers, receipts_for(renderers['full_history'], ['q1']))
    middle = candidate_status(renderers, receipts_for(renderers['full_history'], ['q2']))
    last_receipt = receipts_for(renderers['full_history'], ['q3'])
    last = candidate_status(renderers, last_receipt)
    impossible = copy.deepcopy(last_receipt)
    impossible[0]['body_sha256'] = '0' * 64
    inconsistent = candidate_status(renderers, impossible)
    need([none['count'], first['count'], middle['count'], last['count'], inconsistent['count']]
         == [3, 3, 2, 1, 0], 'body receipt discrimination')
    cases['extra_body_observation_can_identify_in_model'] = {
        'no_receipt': none, 'initial_body_only': first, 'middle_body_only': middle,
        'last_body_bound_to_cut_and_source': last, 'inconsistent_receipt': inconsistent,
        'collector_authenticity_authenticated': False,
        'scope': 'finite declared renderer class, not all possible real implementations'}
    need(len(cases) == 8, 'model case coverage')
    return cases


def analyze(root):
    return {'status': 'PASS_CONDITIONAL_LOG_PROXY_COUNTERMODELS',
            'source_baseline': BASELINE, 'source_bindings': source_bindings(root),
            'kind': 'offline constructive counterexamples, not product trials',
            'model_assumptions': {
                'log_layer': 'pre-serialization source-event ledger',
                'send_schedule': 'fixed source-payload cuts [2,4,6], not usage boundaries',
                'sender_class': list(POLICIES),
                'compatibility': 'prefix causality and restricted serial tool-call grammar',
                'same_actual_model_outputs_proven': False,
                'official_api_conformance_proven': False,
                'real_product_uses_a_model_renderer_proven': False},
            'cases': run_models(),
            'limits': {'actual_http_identified': False,
                       'all_future_evidence_permanently_unidentifiable': False,
                       'server_context_or_thinking_cache_controlled': False,
                       'token_cost_or_capability_ranking_inferred': False,
                       'new_product_requests': 0}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    try:
        payload = json.dumps(analyze(args.root), ensure_ascii=False, sort_keys=True,
                             indent=2, allow_nan=False) + '\n'
        if args.output:
            with args.output.open('x', encoding='utf-8', newline='\n') as handle:
                handle.write(payload)
        else:
            sys.stdout.write(payload)
        return 0
    except (ValueError, TypeError, KeyError, OSError, UnicodeError) as exc:
        print('FAIL_CONDITIONAL_LOG_PROXY_COUNTERMODELS: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
