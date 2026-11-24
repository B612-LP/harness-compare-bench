"""Public, synthetic replay. No capture files, workspaces or accounts are needed."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))  # Explicit sibling under Python -I.
from replay import ARGUMENTS, BOUNDARIES, PHASES, commitment, replay

FIRST = '{"text":"甲\u2028乙","n":1.50,"seq":[1,2]}'
SECOND = '{"text":"丙","n":-0}'
TOOL = 'example_tool'


def encode(value, *, outer=False):
    return json.dumps(value, ensure_ascii=outer, sort_keys=outer,
                      separators=None if outer else (',', ':')).encode('utf-8')


def meta(profile, ordinal, q, w=None):
    start, end = {1: ('02', '03'), 2: ('00', '01') if profile == 'chat' else ('04', '05'),
                  3: ('04', '05')}[ordinal]
    m = {'seq': ordinal, 'path': '/api/coding/paas/v4/chat/completions' if profile == 'chat' else '/responses',
         'method': 'POST', 'upstream_status': 200, 'error': None, 'response_framing': 'rechunked',
         'ts_start': f'2026-01-01T00:00:{start}+00:00', 'ts_done': f'2026-01-01T00:00:{end}+00:00',
         'request_headers': {'Thread-Id': 'demo-thread', 'Session-Id': 'demo-thread'}}
    for k, v in (('request', q), ('response', w)):
        if v is not None:
            c = commitment(v)
            m[k + '_body_bytes'], m[k + '_body_sha256'] = c['bytes'], c['sha256']
    return m


def qh(profile, args, following):
    msg = lambda role: {'role': role, 'content': 'synthetic'}
    if profile == 'chat':
        prefix = [msg('system')] + [msg('user')] * 4
        additions = [{'role': 'assistant', 'tool_calls': [
            {'type': 'function', 'id': 'call-0', 'function': {'name': TOOL, 'arguments': args[0]}}]},
            {'role': 'tool', 'tool_call_id': 'call-0', 'content': 'dummy result'}] if following else []
        return {'messages': prefix + additions, 'max_tokens': 64, 'model': 'demo', 'stream': True,
                'stream_options': {}, 'thinking': {}, 'tool_stream': True, 'tools': [
                    {'type': 'function', 'function': {'name': TOOL}}]}
    prefix = [msg(r) for r in ('developer', 'developer', 'user', 'user')]
    suffix = [{'type': 'reasoning'}] + [
        {'type': 'function_call', 'name': TOOL, 'call_id': f'call-{i}', 'arguments': a, 'status': 'completed'}
        for i, a in enumerate(args)] + [
        {'type': 'function_call_output', 'call_id': f'call-{i}', 'id': f'result-{i}', 'output': 'dummy result'}
        for i in range(len(args))]
    scope = {'thread_id': 'demo-thread', 'session_id': 'demo-thread', 'turn_id': 'demo-turn', 'root_turn_id': 'demo-root'}
    return {'client_metadata': scope, 'include': [], 'input': prefix + (suffix if following else []),
            'model': 'demo', 'parallel_tool_calls': True, 'prompt_cache_key': 'demo-thread', 'reasoning': {},
            'store': False, 'stream': True, 'tool_choice': 'auto', 'tools': [{'type': 'function', 'name': TOOL}]}


def chat_stream(args):
    stream = []
    envelope = {'id': 'demo-completion', 'object': 'chat.completion.chunk', 'model': 'demo-upstream',
                'created': 1767225600}
    for j, arg in enumerate((args[0][:11], args[0][11:])):
        fn = {'name': TOOL, 'arguments': arg} if not j else {'arguments': arg}
        t = {'index': 0, 'type': 'function', 'function': fn}
        if not j:
            t['id'] = 'call-0'
        stream.append(envelope | {'choices': [{'index': 0, 'delta': {'tool_calls': [t]}, 'finish_reason': None}]})
    stream.append(envelope | {'choices': [{'index': 0, 'delta': {'role': 'assistant', 'content': ''},
                                          'finish_reason': 'tool_calls'}]})
    return stream + [None]


def responses_stream(args):
    envelop = {'id': 'demo-response', 'model': 'demo-upstream', 'object': 'response', 'created_at': 1767225600}
    initial = envelop | {'status': 'in_progress', 'output': [], 'error': None, 'incomplete_details': None}
    stream = [{'type': phase, 'response': deepcopy(initial)} for phase in PHASES[:2]]
    thinking = {'id': 'thinking-0', 'type': 'reasoning', 'status': 'completed'}
    stream += [{'type': BOUNDARIES[0], 'output_index': 0, 'item': thinking | {'status': 'in_progress'}},
               {'type': 'response.reasoning_text.delta', 'output_index': 0, 'content_index': 0,
                'item_id': thinking['id'], 'delta': 'dummy'},
               {'type': BOUNDARIES[1], 'output_index': 0, 'item': deepcopy(thinking)}]
    final = [thinking]
    for i, arg in enumerate(args, 1):
        call = {'id': f'item-{i}', 'type': 'function_call', 'name': TOOL, 'call_id': f'call-{i-1}',
                'status': 'completed', 'arguments': arg}
        ref = {'output_index': i, 'item_id': call['id']}
        stream += [{'type': BOUNDARIES[0], 'output_index': i,
                    'item': call | {'arguments': '', 'status': 'in_progress'}},
                   {'type': ARGUMENTS[0], 'delta': arg[:11]} | ref,
                   {'type': ARGUMENTS[0], 'delta': arg[11:]} | ref,
                   {'type': ARGUMENTS[1], 'arguments': arg} | ref,
                   {'type': BOUNDARIES[1], 'output_index': i, 'item': deepcopy(call)}]
        final.append(call)
    return stream + [{'type': PHASES[-1], 'response': initial | {'status': 'completed', 'output': final}}]


def sse(profile, stream, outer):
    eol = b'\r\n' if outer else b'\n'
    rendered = []
    for i, item in enumerate(stream):
        prefix = b''
        if profile == 'responses':
            prefix = b'event: ' + item['type'].encode() + eol
            item = item | {'sequence_number': i}
        rendered.append(prefix + b'data: ' + (b'[DONE]' if item is None else encode(item, outer=outer)))
    dispatch = eol + eol
    return dispatch.join(rendered) + dispatch


class Trial:
    def __init__(self, profile, *, args=None, two=True):
        self.profile = profile
        self.args = args or ([FIRST, SECOND] if two and profile == 'responses' else [FIRST])
        self.frames = (chat_stream if profile == 'chat' else responses_stream)(self.args)
        self.origin, self.following = (qh(profile, self.args, f) for f in (False, True))
        self.meta_patch = {}
        self.reencode = False

    def input(self):
        p = self.profile
        q, w, h = encode(self.origin), sse(p, self.frames, self.reencode), encode(self.following)
        source = {}
        for label, ordinal, req, wire in (('W', 1, q, w), ('H', 3 if p == 'chat' else 2, h, None)):
            m = meta(p, ordinal, req, wire)
            m.update(self.meta_patch.get(label, {}))
            source[label] = {'q': req, 'm': encode(m)}
            if wire is not None:
                source[label]['w'] = wire
        if p == 'chat':
            aux = qh(p, self.args, False)
            aux['reasoning_effort'] = 'minimal'
            aux['messages'] = aux['messages'][:2]
            del aux['tools'], aux['tool_stream']
            qaux = encode(aux)
            source['A'] = {'q': qaux, 'm': encode(meta(p, 2, qaux))}
        pins = {s: {part: commitment(data) for part, data in raw.items()} for s, raw in source.items()}
        return source, pins

    def check(self):
        return replay(self.profile, *self.input())

    def replace_first_history(self, value):
        if self.profile == 'chat':
            self.following['messages'][-2]['tool_calls'][0]['function']['arguments'] = value
        else:
            self.following['input'][5]['arguments'] = value


class ReplayContract(unittest.TestCase):
    def test_native_carriers(self):
        for profile in ('chat', 'responses'):
            with self.subTest(profile=profile):
                t = Trial(profile)
                a = t.check()
                self.assertEqual(a['group'], 'equal')
                self.assertTrue(a['argument_text_equal'])
                self.assertEqual(a['W']['argument_bytes'], [len(s.encode()) for s in t.args])
                self.assertEqual(a['H']['canonical_bytes'], a['W']['canonical_bytes'])
        self.assertEqual(len(Trial('responses', two=False).check()['W']['argument_bytes']), 1)

    def test_outer_equivalence_including_unicode_separator(self):
        for profile in ('chat', 'responses'):
            with self.subTest(profile=profile):
                t = Trial(profile)
                a = t.check()
                t.reencode = True
                b = t.check()
                self.assertNotEqual(a['physical']['W']['w']['bytes'], b['physical']['W']['w']['bytes'])
                self.assertEqual(a['W'], b['W'])
                self.assertEqual(b['group'], 'equal')
                self.assertTrue(b['argument_text_equal'])

    def test_inner_value_equivalence_keeps_text_difference(self):
        for profile in ('chat', 'responses'):
            with self.subTest(profile=profile):
                t = Trial(profile)
                t.replace_first_history(' {"seq":[1,2],"n":1.5e0,"text":"甲\\u2028乙"} ')
                a = t.check()
                self.assertEqual(a['group'], 'equal')
                self.assertFalse(a['argument_text_equal'])
                self.assertNotEqual(a['W']['argument_bytes'], a['H']['argument_bytes'])
                self.assertEqual(a['W']['canonical_bytes'], a['H']['canonical_bytes'])

    def test_same_length_semantic_difference(self):
        for profile in ('chat', 'responses'):
            with self.subTest(profile=profile):
                t = Trial(profile)
                t.replace_first_history(FIRST.replace('甲', '丁'))
                a = t.check()
                self.assertEqual(a['group'], 'different')
                self.assertEqual(a['W']['argument_bytes'], a['H']['argument_bytes'])
                self.assertEqual(a['W']['canonical_bytes'], a['H']['canonical_bytes'])

    def test_types_order_and_unbounded_precision_not_collapsed(self):
        for old, changed in (('1', '1.0'), ('-0.0', '0.0'), ('true', '1'), ('[1,2]', '[2,1]'),
                             ('0.100000000000000001', '0.100000000000000002')):
            with self.subTest(old=old, changed=changed):
                t = Trial('chat', args=['{"n":' + old + '}'])
                t.replace_first_history('{"n":' + changed + '}')
                self.assertEqual(t.check()['group'], 'different')

    def test_non_strict_inner_values_leave_text_visible(self):
        for profile in ('chat', 'responses'):
            for bad in ('{"n":1,"n":2}', '{"n":NaN}', '{"text":"\\uD800"}', '[]', '{"n":1e10001}'):
                with self.subTest(profile=profile, bad=bad):
                    t = Trial(profile)
                    t.replace_first_history(bad)
                    a = t.check()
                    self.assertEqual(a['group'], 'unknown')
                    self.assertFalse(a['argument_text_equal'])
                    self.assertEqual(a['H']['argument_bytes'][0], len(bad.encode()))
                    self.assertIsNone(a['H']['canonical_bytes'][0])
                    self.assertIsNotNone(a['W']['canonical_bytes'][0])

    def test_missing_capture_or_seal_keeps_other_physical_layers(self):
        for profile in ('chat', 'responses'):
            with self.subTest(profile=profile):
                t = Trial(profile)
                source, pins = t.input()
                source['H'].pop('q')
                a = replay(profile, source, pins)
                self.assertEqual(a['group'], 'unknown')
                self.assertIsNotNone(a['W']['argument_bytes'])
                self.assertEqual(a['physical']['H']['q']['error'], 'source_missing')
                self.assertIsNotNone(a['physical']['H']['m']['bytes'])
                t.reencode = True
                b = replay(profile, t.input()[0], pins)
                self.assertEqual(b['group'], 'unknown')
                self.assertEqual(b['physical']['W']['w']['error'], 'source_pin_mismatch')

    def test_missing_wire_closure_does_not_search_late_packets(self):
        for profile in ('chat', 'responses'):
            with self.subTest(profile=profile):
                t = Trial(profile)
                t.frames.pop()
                source, pins = t.input()
                source['later'] = Trial(profile).input()[0]['W']
                a = replay(profile, source, pins)
                self.assertEqual(a['group'], 'unknown')
                self.assertEqual(a['W']['carrier_error'], 'chat_done' if profile == 'chat' else 'responses_phases')
                self.assertIsNotNone(a['physical']['W']['w']['bytes'])

    def test_wrong_call_id_rebound_inside_history_is_not_same_run(self):
        for profile in ('chat', 'responses'):
            with self.subTest(profile=profile):
                t = Trial(profile)
                if profile == 'chat':
                    assistant, result = t.following['messages'][-2:]
                    assistant['tool_calls'][0]['id'] = result['tool_call_id'] = 'other-call'
                else:
                    for item in t.following['input']:
                        if item.get('call_id') == 'call-0':
                            item['call_id'] = 'other-call'
                a = t.check()
                self.assertEqual(a['group'], 'unknown')
                self.assertEqual(a['H']['carrier_error'], 'continuation_group_identity')
                self.assertIsNotNone(a['W']['argument_bytes'])

    def test_partial_or_reordered_responses_group(self):
        for mode in ('half', 'reorder'):
            with self.subTest(mode=mode):
                t = Trial('responses')
                items = t.following['input']
                if mode == 'half':
                    items[:] = [x for x in items if x.get('call_id') != 'call-1']
                else:
                    items[5:7] = items[5:7][::-1]
                    items[7:9] = items[7:9][::-1]
                a = t.check()
                self.assertEqual(a['group'], 'unknown')
                self.assertEqual(len(a['W']['argument_bytes']), 2)

    def test_wrong_clock_keeps_wire(self):
        for profile in ('chat', 'responses'):
            with self.subTest(profile=profile):
                t = Trial(profile)
                t.meta_patch['H'] = {'ts_start': '2026-01-01T00:00:02+00:00'}
                a = t.check()
                self.assertEqual(a['group'], 'unknown')
                self.assertEqual(a['H']['carrier_error'], 'continuation_clock')
                self.assertIsNotNone(a['W']['canonical_bytes'])

    def test_chat_range_holes_at_finish(self):
        for key, reason in (('model', 'chat_identity'), ('text', 'chat_finish_delta')):
            with self.subTest(key=key):
                t = Trial('chat')
                if key == 'model':
                    t.frames[-2]['model'] = 'another-upstream'
                else:
                    t.frames[-2]['choices'][0]['delta']['content'] = 'extra visible text'
                a = t.check()
                self.assertEqual(a['group'], 'unknown')
                self.assertEqual(a['W']['carrier_error'], reason)
                self.assertIsNotNone(a['physical']['W']['w']['bytes'])

    def test_responses_range_holes_preserve_other_layers(self):
        for kind, reason in (('lifetime', 'responses_aux_lifetime'), ('early', 'responses_early_output'),
                             ('contradictory', 'responses_item_close')):
            with self.subTest(kind=kind):
                t = Trial('responses')
                if kind == 'lifetime':
                    t.frames.insert(4, t.frames.pop(3))  # Correct ordinal and ID but after reasoning item.done.
                elif kind == 'early':
                    t.frames[0]['response']['output'] = deepcopy(t.frames[-1]['response']['output'][:1])
                else:
                    t.frames[-1]['response']['output'][1]['arguments'] = SECOND
                a = t.check()
                self.assertEqual(a['group'], 'unknown')
                self.assertEqual(a['W']['carrier_error'], reason)
                self.assertIsNotNone(a['physical']['H']['q']['bytes'])

    def test_conflicting_embedded_turn_witness_keeps_wire_and_physical_layers(self):
        for case in ('matched', 'capture_turn', 'body_root', 'capture_incomplete'):
            with self.subTest(case=case):
                t = Trial('responses')
                actual = t.following['client_metadata']
                truthful = {k: actual[k] for k in ('session_id', 'thread_id', 'turn_id', 'root_turn_id')}
                capture, nested = dict(truthful), dict(truthful)
                if case == 'capture_turn':
                    capture['turn_id'] = 'demo-turx'  # Same length, no change to either request body.
                elif case == 'body_root':
                    nested['root_turn_id'] = 'demo-roox'
                elif case == 'capture_incomplete':
                    del capture['session_id']
                actual['x-codex-turn-metadata'] = json.dumps(nested)
                h = meta('responses', 2, encode(t.following))['request_headers']
                t.meta_patch['H'] = {'request_headers': h | {'X-Codex-Turn-Metadata': json.dumps(capture)}}
                a = t.check()
                if case == 'matched':
                    self.assertEqual(a['group'], 'equal')
                else:
                    self.assertEqual(a['group'], 'unknown')
                    self.assertEqual(a['H']['carrier_error'], 'responses_turn_witness')
                    self.assertEqual(a['W']['argument_bytes'], [len(s.encode()) for s in t.args])
                    self.assertIsNotNone(a['physical']['H']['q']['bytes'])
                    self.assertIsNotNone(a['physical']['H']['m']['bytes'])

    def test_cross_turn_coherent_request_still_unbound(self):
        t = Trial('responses')
        t.following['client_metadata']['turn_id'] = 'different-turn'
        a = t.check()
        self.assertEqual(a['group'], 'unknown')
        self.assertEqual(a['H']['carrier_error'], 'responses_cross_turn')


if __name__ == '__main__':
    unittest.main(verbosity=2)
