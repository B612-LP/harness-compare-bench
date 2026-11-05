#!/usr/bin/env python3
"""Read-only, stdlib accounting of six already-public native request pairs.

No historical code is imported or executed. Trusted code pins public bytes, not
private originals; decompose() separately checks the accounting preconditions.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import statistics
import sys

SCENE = '3-表现现场/r20261104-native-provenance'
OUTPUT = '5-评测报告/原生字节分解-2026-11-05/decomposition.json'
SOURCE_SHA256 = {
    SCENE + '/sessions/confirm-b01-codex/01-request.json': '60226f977592f9e163f66c5de3fd5e445f1ad9823c3e6991e5097089f4c7caa5',
    SCENE + '/sessions/confirm-b01-codex/02-request.json': '657c6413726ce84beb4fe887a96d892c74bf92b42b1c8b17e773d69da5712696',
    SCENE + '/sessions/confirm-b01-codex/observations.json': '18fc65eeb22600da32fc75f00e5082c7f2339c7821ec834df7b535dfb2584508',
    SCENE + '/sessions/confirm-b01-dsh/01-request.json': 'b423638744a4ca393cad4845d6380e28af8e57028b3b0031187b82328ffbabf5',
    SCENE + '/sessions/confirm-b01-dsh/02-request.json': '2fa447a3d116bd830dd5ecafe67325502af34886fc4a3fee7249f5e169a07d31',
    SCENE + '/sessions/confirm-b01-dsh/observations.json': 'b6d08572c61e98e4c896ae8e29295e46684be13d9062fc245554082220c6d404',
    SCENE + '/sessions/confirm-b02-codex/01-request.json': '145961fd169e50cdf7c62f9ddd6d50f0b5c342dd99390ae18887d888e67ec4c2',
    SCENE + '/sessions/confirm-b02-codex/02-request.json': '27bb31f3aaadbf197be0663badb26d7b32906461a916f8fd8ce5570ff2ace30d',
    SCENE + '/sessions/confirm-b02-codex/observations.json': '8b50797d8eaa3d905359a12981e5d2cfcf2c2433032a51ede62dd64c46e77664',
    SCENE + '/sessions/confirm-b02-dsh/01-request.json': 'b423638744a4ca393cad4845d6380e28af8e57028b3b0031187b82328ffbabf5',
    SCENE + '/sessions/confirm-b02-dsh/02-request.json': '616b2b8af07cbcca7fbf60c62817a0b19c79bc309ba9d5629145eb1a94a0aa81',
    SCENE + '/sessions/confirm-b02-dsh/observations.json': '19436b3bd0e10f93ef8061fb2f650d079045fa5dc8c9a5d6713fd6b0ec461519',
    SCENE + '/sessions/confirm-b03-codex/01-request.json': '36591e7ccfe24b364c93aa6d0f0b9aa640fb972aff3b077fcc4ceb37e840d3d5',
    SCENE + '/sessions/confirm-b03-codex/02-request.json': 'b09372a4afe1155fe656efc5bd1f7c50cb55cbe7509faf4025d01aa7b630065d',
    SCENE + '/sessions/confirm-b03-codex/observations.json': '812926f9bbf8b5856dfb6d2b21cd17975553cec7ab43522b205018dca29eceae',
    SCENE + '/sessions/confirm-b03-dsh/01-request.json': 'b423638744a4ca393cad4845d6380e28af8e57028b3b0031187b82328ffbabf5',
    SCENE + '/sessions/confirm-b03-dsh/02-request.json': '36547aae12f84493da89cc4bee03d4d9199e15b273d179cd2c2a653e6f302dbf',
    SCENE + '/sessions/confirm-b03-dsh/observations.json': 'b8a6cddc2ce66db72bd97407bb066fda199efdbdcfa96b1626ed20cf81fba950',
    SCENE + '/ledger.json': '0a1d14d3d065da2dc1fccb2eff4217f0b2e6c05d713c91fed07063ddb812c933',
    SCENE + '/projection-map.json': 'd5b80a23b28bc306f06c3a7fce66f81fc93ed0583fe16c5510ec0e37edb3a411',
    SCENE + '/projection_protocol.py': '80981bf4073fe13e082ac1b7a269853eedff46ffa0623c46430e5cf256095358',
    '1-评测方案/原生来源链技术门-2026-11-04/README.md': '909833aa0aa6e00f6c02f7f860e236db48d42e1931a090134d7d42d720d96039',
}
COMPONENTS = ('decoded_text', 'text_quotes', 'text_escape_expansion',
              'return_structure', 'assistant_history')
BRANCH = 'larger_codex_native_selected_input_growth_in_this_configuration'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def same(actual, expected, label):
    require(canonical(actual) == canonical(expected), label + ' mismatch')


def parse_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key: ' + key)
            result[key] = value
        return result

    def number(text):
        value = float(text)
        require(math.isfinite(value), 'nonfinite JSON number')
        return value

    def constant(text):
        raise ValueError('nonfinite JSON constant: ' + text)

    return json.loads(raw, object_pairs_hook=pairs, parse_float=number,
                      parse_constant=constant)


def safe_file(root, relative):
    require(type(relative) is str and '\\' not in relative, 'invalid path')
    path = PurePosixPath(relative)
    require(not path.is_absolute() and '..' not in path.parts and
            path.as_posix() == relative and relative not in ('', '.'), 'unsafe path')
    current = root
    for part in path.parts:
        current = current / part
        require(not current.is_symlink(), 'symlink forbidden: ' + relative)
    require(current.is_file(), 'missing source: ' + relative)
    require(current.resolve().is_relative_to(root.resolve()), 'path escape')
    return current


def exact_keys(value, keys, label):
    require(type(value) is dict and set(value) == set(keys), label + ' schema')


def string(value, label):
    require(type(value) is str, label + ' must be a string')
    return value


def text_leaves(items, kind, pointer, count):
    require(type(items) is list and len(items) == count, 'text block count')
    result = []
    for index, item in enumerate(items):
        exact_keys(item, ('type', 'text'), 'text block')
        same(item['type'], kind, 'text block type')
        value = string(item['text'], 'text leaf')
        result.append((pointer + '/' + str(index) + '/text', value))
    return result


def suffix_schema(suffix, arm, base_pointer):
    """Recognize this snapshot's actual native assistant/tool-return shapes."""
    if arm == 'codex':
        require(len(suffix) in (2, 3), 'Codex suffix count')
        assistants, returned = suffix[:-1], suffix[-1]
        if len(assistants) == 2:
            reason = assistants[0]
            exact_keys(reason, ('type', 'summary', 'content', 'encrypted_content'), 'reasoning')
            same(reason['type'], 'reasoning', 'reasoning type')
            same(reason['summary'], [], 'reasoning summary')
            require(type(reason['content']) is list and len(reason['content']) == 1,
                    'reasoning content')
            exact_keys(reason['content'][0], ('type', 'text'), 'reasoning text')
            same(reason['content'][0]['type'], 'reasoning_text', 'reasoning text type')
            string(reason['content'][0]['text'], 'reasoning text')
            string(reason['encrypted_content'], 'reasoning opaque content')
        call = assistants[-1]
        exact_keys(call, ('type', 'status', 'name', 'namespace', 'arguments', 'call_id'),
                   'Codex assistant call')
        for key, value in (('type', 'function_call'), ('status', 'completed'),
                           ('name', 'fixture_output'), ('namespace', 'mcp__fixture')):
            same(call[key], value, 'Codex assistant ' + key)
        same(parse_json(string(call['arguments'], 'call arguments')), {}, 'call arguments')
        call_id = string(call['call_id'], 'call_id')
        require(bool(call_id), 'empty call_id')
        exact_keys(returned, ('type', 'id', 'call_id', 'output'), 'Codex tool-return')
        same(returned['type'], 'function_call_output', 'Codex tool-return type')
        string(returned['id'], 'Codex return id')
        same(returned['call_id'], call_id, 'Codex tool-return call_id')
        # Two actual string leaves, NOT a fictitious JSON scalar of their concat.
        leaves = text_leaves(returned['output'], 'input_text', base_pointer + '/output', 2)
    else:
        require(arm == 'dsh' and len(suffix) == 2, 'DSH suffix count')
        assistant, returned = suffix
        assistants = [assistant]
        exact_keys(assistant, ('role', 'content'), 'DSH assistant')
        same(assistant['role'], 'assistant', 'DSH assistant role')
        content = assistant['content']
        require(type(content) is list and len(content) == 2, 'DSH assistant content')
        think, call = content
        exact_keys(think, ('type', 'thinking', 'signature'), 'DSH thinking')
        same(think['type'], 'thinking', 'DSH thinking type')
        string(think['thinking'], 'DSH thinking text')
        string(think['signature'], 'DSH thinking signature')
        exact_keys(call, ('type', 'id', 'name', 'input'), 'DSH assistant call')
        same(call['type'], 'tool_use', 'DSH tool_use type')
        same(call['name'], 'fixture_output', 'DSH call name')
        same(call['input'], {}, 'DSH call input')
        call_id = string(call['id'], 'DSH call_id')
        require(bool(call_id), 'empty call_id')
        exact_keys(returned, ('role', 'content'), 'DSH tool-return')
        same(returned['role'], 'user', 'DSH tool-return role')
        require(type(returned['content']) is list and len(returned['content']) == 1,
                'DSH tool-return count')
        tool = returned['content'][0]
        exact_keys(tool, ('type', 'tool_use_id', 'content', 'is_error'), 'DSH tool_result')
        same(tool['type'], 'tool_result', 'DSH tool_result type')
        same(tool['tool_use_id'], call_id, 'DSH tool-return call_id')
        same(tool['is_error'], False, 'DSH tool-return is_error')
        leaves = text_leaves(tool['content'], 'text', base_pointer + '/content/0/content', 1)
    return assistants, returned, leaves


def decompose(first, second, arm, wire):
    """Pure semantic layer: validate growth preconditions, then partition bytes."""
    require(arm in ('codex', 'dsh'), 'unknown arm')
    require(type(first) is dict and type(second) is dict, 'request object required')
    history = 'input' if arm == 'codex' else 'messages'
    selected = (('instructions', 'input', 'tools', 'previous_response_id')
                if arm == 'codex' else ('system', 'messages', 'tools'))
    require(history in first and history in second, 'missing history')
    require(('messages' not in first and 'messages' not in second) if arm == 'codex'
            else ('input' not in first and 'input' not in second), 'mixed protocol')
    prefix, full = first[history], second[history]
    require(type(prefix) is list and len(prefix) > 0 and type(full) is list,
            'nonempty original history required')
    require(len(full) > len(prefix), 'missing appended history')
    same(full[:len(prefix)], prefix, 'history prefix')
    before = {key: first[key] for key in selected if key in first}
    after = {key: second[key] for key in selected if key in second}
    same(sorted(before), sorted(after), 'selected field presence')
    same({k: v for k, v in before.items() if k != history},
         {k: v for k, v in after.items() if k != history}, 'nonhistory selected fields')
    same({k: v for k, v in first.items() if k != history},
         {k: v for k, v in second.items() if k != history}, 'request controls')
    require(type(wire) is list and len(wire) == 2 and
            all(type(v) is int and v >= 0 for v in wire), 'wire byte lengths')
    index = len(full) - 1
    return_pointer = '/' + history + '/' + str(index)
    assistants, returned, leaves = suffix_schema(full[len(prefix):], arm, return_pointer)
    leaf_rows = [{'pointer': ptr, 'decoded_bytes': len(value.encode('utf-8')),
                  'json_scalar_bytes': len(canonical(value)), 'quote_bytes': 2,
                  'escape_expansion_bytes': len(canonical(value)) - len(value.encode('utf-8')) - 2}
                 for ptr, value in leaves]
    text = sum(row['decoded_bytes'] for row in leaf_rows)
    quotes = sum(row['quote_bytes'] for row in leaf_rows)
    escapes = sum(row['escape_expansion_bytes'] for row in leaf_rows)
    scalar = sum(row['json_scalar_bytes'] for row in leaf_rows)
    assistant_sizes = [len(canonical(item)) + 1 for item in assistants]
    parts = dict(zip(COMPONENTS, (text, quotes, escapes,
                                  len(canonical(returned)) + 1 - scalar,
                                  sum(assistant_sizes))))
    cb = {k: len(canonical(v)) for k, v in before.items()}
    ca = {k: len(canonical(v)) for k, v in after.items()}
    delta = len(canonical(after)) - len(canonical(before))
    cd = {k: ca.get(k, 0) - cb.get(k, 0) for k in cb.keys() | ca.keys()}
    metric = {'before': len(canonical(before)), 'after': len(canonical(after)),
              'delta': delta, 'wire': wire, 'components_before': cb,
              'components_after': ca, 'component_delta': cd,
              'serialization_wrapper_delta': delta - sum(cd.values())}
    require(all(v >= 0 for v in parts.values()), 'negative arm component')
    require(sum(parts.values()) == delta, 'component closure')
    return {'metric': metric, 'components': parts, 'component_sum': sum(parts.values()),
            'history_pointer': '/' + history, 'return_item_pointer': return_pointer,
            'text_leaves': leaf_rows,
            'assistant_items': [{'pointer': '/' + history + '/' + str(len(prefix) + i),
                                 'canonical_bytes_plus_comma': size}
                                for i, size in enumerate(assistant_sizes)],
            'append_commas': len(assistants) + 1}


def check_observation(obs, row, run_id, block, arm):
    for key, value in (('schema', 'native-provenance-public-v1'), ('id', run_id),
                       ('contract_id', 'native-direct-provenance-20261104-v1'),
                       ('product', arm), ('block', block), ('mode', 'live'),
                       ('phase', 'confirmation'), ('attempted', True),
                       ('technical_valid', True)):
        same(obs[key], value, 'observation ' + key)
    same(obs['projection_metric'], row['metric'], 'observation projection_metric')
    original = obs['original_metric']
    same({k: original[k] for k in row['metric']}, row['metric'], 'original selected metric')
    same(original['returned_bytes'], row['components']['decoded_text'], 'returned bytes')
    same(original['primary_valid'], True, 'recorded primary_valid')
    same(original['invalid_reasons'], [], 'recorded invalid reasons')


def derive(raw):
    """Recompute from source bytes; caller decides whether the hash layer applies."""
    rows = []
    for block in (1, 2, 3):
        for arm in ('codex', 'dsh'):
            run_id = 'confirm-b%02d-%s' % (block, arm)
            base = SCENE + '/sessions/' + run_id
            paths = [base + '/' + f for f in ('01-request.json', '02-request.json', 'observations.json')]
            first, second, obs = [parse_json(raw[path]) for path in paths]
            row = decompose(first, second, arm, [len(raw[path]) for path in paths[:2]])
            check_observation(obs, row, run_id, block, arm)
            rows.append({'id': run_id, 'block': block, 'arm': arm,
                         'source_refs': {'first_request': paths[0], 'second_request': paths[1],
                                         'observation': paths[2]},
                         'observation_metric_pointer': '/projection_metric', **row})
    pairs = []
    for block in (1, 2, 3):
        arms = {row['arm']: row for row in rows if row['block'] == block}
        difference = {key: arms['codex']['components'][key] - arms['dsh']['components'][key]
                      for key in COMPONENTS}
        delta = arms['codex']['metric']['delta'] - arms['dsh']['metric']['delta']
        require(sum(difference.values()) == delta, 'pair closure')
        pairs.append({'block': block, 'codex_minus_dsh': difference, 'original_difference': delta,
                      'component_sum': sum(difference.values()),
                      'residual_after_decoded_text_subtraction': delta - difference['decoded_text'],
                      'residual_after_actual_text_scalars_subtraction': delta - sum(
                          difference[k] for k in ('decoded_text', 'text_quotes', 'text_escape_expansion'))})
    differences = [p['original_difference'] for p in pairs]
    median = statistics.median(differences)
    require(min(differences) > 0 and median >= 4096, 'original branch no longer satisfied')
    ledger = parse_json(raw[SCENE + '/ledger.json'])
    same(ledger['differences'], differences, 'ledger differences')
    same(ledger['median_difference_bytes'], median, 'ledger median')
    same(ledger['valid_blocks'], 3, 'ledger block count')
    same(ledger['branch'], BRANCH, 'ledger original branch')
    require(type(ledger['blocks']) is list and len(ledger['blocks']) == 3,
            'ledger exact block coverage')
    for block, pair in zip(ledger['blocks'], pairs):
        number = pair['block']
        expected_order = ['confirm-b%02d-%s' % (number, arm)
                          for arm in (('dsh', 'codex') if number == 2 else ('codex', 'dsh'))]
        same(block['block'], number, 'ledger block identity')
        same(block['order'], expected_order, 'ledger block order')
        same(block['technical_valid'], True, 'ledger recorded technical_valid')
        for arm in ('codex', 'dsh'):
            row = next(r for r in rows if r['block'] == number and r['arm'] == arm)
            same(block[arm + '_delta'], row['metric']['delta'], 'ledger arm delta')
        same(block['difference_bytes'], pair['original_difference'], 'ledger block difference')
    return {'schema': 'native-byte-partition-v1',
            'domain': 'public privacy-projected UTF-8 compact sorted JSON; not private originals',
            'sources': [{'path': path, 'sha256': hashlib.sha256(raw[path]).hexdigest()}
                        for path in sorted(SOURCE_SHA256)],
            'component_order': list(COMPONENTS), 'rows': rows, 'pairs': pairs,
            'original_preregistered_result': {'blocks': 3, 'positive_blocks': 3,
                'threshold_bytes': 4096, 'median_difference_bytes': median, 'branch': BRANCH,
                'threshold_applies_to': 'original_difference_only'},
            'limits': {'sensitivity_is_posthoc_algebra_only': True,
                'controlled_or_causal_effect': False, 'protocol_efficiency': False,
                'token_or_cost_measurement': False, 'private_originals_authenticated': False,
                'full_native_protocol_reverification': False, 'new_sessions': 0,
                'new_formal_rows': 0, 'same_dsh_pairs_combined': False}}


def load_sources(root):
    raw = {}
    for relative, expected in SOURCE_SHA256.items():
        data = safe_file(root, relative).read_bytes()
        require(hashlib.sha256(data).hexdigest() == expected, 'source SHA mismatch: ' + relative)
        raw[relative] = data
    return raw


def verify(root):
    root = Path(root).resolve(strict=True)
    result = derive(load_sources(root))
    same(parse_json(safe_file(root, OUTPUT).read_bytes()), result, 'derived output')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    try:
        result = verify(args.root)
        print(json.dumps({'ok': True, 'status': 'PASS_PUBLIC_BYTE_PARTITION', **result},
                         ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
    except (ValueError, KeyError, TypeError, OSError, UnicodeError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
