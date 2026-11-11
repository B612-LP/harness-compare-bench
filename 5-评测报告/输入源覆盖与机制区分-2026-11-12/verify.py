#!/usr/bin/env python3
"""Independent, read-only reanalysis of pinned public projections; stdlib only.

Not a product runner, original-seal verifier, generic diff or causal estimator.
Byte intervals are UTF-8 half-open offsets. Shapes below are post-hoc models,
not imports or executions of product truncation implementations.
"""
import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath

BASELINE_COMMIT = '38b2e13f63c5aeacb58094d2e977980ab12e8041'
SELF_DIR = '5-评测报告/输入源覆盖与机制区分-2026-11-12'
SAME = '3-表现现场/r20261103-input-bytes/runs'
NATIVE = '3-表现现场/r20261104-native-provenance/sessions'
SOURCE_SHA = 'fed57592028c9d8a9180c2b97f74a3cd5e0daa841aab244cf4aad78fe44626a2'
# Fixed code anchors, not values trusted from the proposed result.
PINS = {
    '3-表现现场/r20261103-input-bytes/runs/confirm-b01-inline/capture/01-request.json': 'ed1637202429b7885458be1f439884e93bb00475b7ad92fbe85cfbe63db73b03',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b01-inline/capture/02-request.json': '94c3ef2ddd5ce1caea514941cfcf17a0c894feb3d9bdef5e124c398e3eecb01c',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b01-inline/capture/tool-output.txt': 'fed57592028c9d8a9180c2b97f74a3cd5e0daa841aab244cf4aad78fe44626a2',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b01-inline/reported-usage.json': 'd46595214b2fffbe85b845fd980ce36d41e5d9ae6468633d29a5e9eb1681f49c',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b01-bounded/capture/01-request.json': 'ed1637202429b7885458be1f439884e93bb00475b7ad92fbe85cfbe63db73b03',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b01-bounded/capture/02-request.json': '6864ae3a62713c99bdfe5ee646dfb23011bb87e1d3fed0c7bbc405621ca47e86',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b01-bounded/capture/tool-output.txt': 'fed57592028c9d8a9180c2b97f74a3cd5e0daa841aab244cf4aad78fe44626a2',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b01-bounded/reported-usage.json': '1f48a984652f79310cc9a88874046d05f2be8ced8f9d0d16d0f04c3e82aa03e2',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b02-inline/capture/01-request.json': 'ed1637202429b7885458be1f439884e93bb00475b7ad92fbe85cfbe63db73b03',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b02-inline/capture/02-request.json': '7000cdc2d82863e6a42863338a611c533c4cb9067421b2d336fc9055a88f059c',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b02-inline/capture/tool-output.txt': 'fed57592028c9d8a9180c2b97f74a3cd5e0daa841aab244cf4aad78fe44626a2',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b02-inline/reported-usage.json': '7967e09beba6620bf40f8a2c3a84a2da83f86016f9da3cddd1755868e76be25b',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b02-bounded/capture/01-request.json': 'ed1637202429b7885458be1f439884e93bb00475b7ad92fbe85cfbe63db73b03',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b02-bounded/capture/02-request.json': '707a3e45c3932e61c15e64cacffe7d545afac059ebfa4071f22e7c77dd5d3abc',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b02-bounded/capture/tool-output.txt': 'fed57592028c9d8a9180c2b97f74a3cd5e0daa841aab244cf4aad78fe44626a2',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b02-bounded/reported-usage.json': '0fc91e255084f5429fb5752b1291b208a672d91e82f7a5d66e6d943945def50a',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b03-inline/capture/01-request.json': 'ed1637202429b7885458be1f439884e93bb00475b7ad92fbe85cfbe63db73b03',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b03-inline/capture/02-request.json': '418c5d6d7307c24f963d96ab0c337697b4df0c7c37cedd82a20392584474e281',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b03-inline/capture/tool-output.txt': 'fed57592028c9d8a9180c2b97f74a3cd5e0daa841aab244cf4aad78fe44626a2',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b03-inline/reported-usage.json': '4602886d1b688825c1ac3e3ee4bf3ba304b8bebaef29fe89a781a901c5d75188',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b03-bounded/capture/01-request.json': 'ed1637202429b7885458be1f439884e93bb00475b7ad92fbe85cfbe63db73b03',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b03-bounded/capture/02-request.json': '2790f5fc9151a8fb42a90884c90312d415c8fc7a4f751a5970a1b10651cee55e',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b03-bounded/capture/tool-output.txt': 'fed57592028c9d8a9180c2b97f74a3cd5e0daa841aab244cf4aad78fe44626a2',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b03-bounded/reported-usage.json': 'ce7a282c479cffa4f86796de3b5adbb13624f2c508d106014645e0922947694d',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b04-inline/capture/01-request.json': 'ed1637202429b7885458be1f439884e93bb00475b7ad92fbe85cfbe63db73b03',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b04-inline/capture/02-request.json': '046e0c184644d5064e00515071c01ce8827dc75293473979be03be340a28ed72',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b04-inline/capture/tool-output.txt': 'fed57592028c9d8a9180c2b97f74a3cd5e0daa841aab244cf4aad78fe44626a2',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b04-inline/reported-usage.json': '4a83807d63e62f08015f649510ae889eb2f8754cfa46cc369c150c40ba8b906d',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b04-bounded/capture/01-request.json': 'ed1637202429b7885458be1f439884e93bb00475b7ad92fbe85cfbe63db73b03',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b04-bounded/capture/02-request.json': 'c5a24095ed0c80e67faf6e87af89007bc71da6a997dedc07320c6991f3997f78',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b04-bounded/capture/tool-output.txt': 'fed57592028c9d8a9180c2b97f74a3cd5e0daa841aab244cf4aad78fe44626a2',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b04-bounded/reported-usage.json': '5e892c7daede986d14cdd42e3fa9e3aa68ad38c893297858d14efeb0d19394f1',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b05-inline/capture/01-request.json': 'ed1637202429b7885458be1f439884e93bb00475b7ad92fbe85cfbe63db73b03',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b05-inline/capture/02-request.json': 'f8891b90b5e709a169fa14cf8305b6753b031b35c21e257c02d1d6ac0041e59e',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b05-inline/capture/tool-output.txt': 'fed57592028c9d8a9180c2b97f74a3cd5e0daa841aab244cf4aad78fe44626a2',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b05-inline/reported-usage.json': '0d0ecfc0882fbf520c7799baf6a67ec82b8e5a3f5080b6343ab68861d81a5149',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b05-bounded/capture/01-request.json': 'ed1637202429b7885458be1f439884e93bb00475b7ad92fbe85cfbe63db73b03',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b05-bounded/capture/02-request.json': '8158d8fbe083d763ec28b2580de6a002f95840dc1d0b3aa8643cf72929b1aaa9',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b05-bounded/capture/tool-output.txt': 'fed57592028c9d8a9180c2b97f74a3cd5e0daa841aab244cf4aad78fe44626a2',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b05-bounded/reported-usage.json': '4fdb1e5c2d8f1b6e7ccae0bbf41b61bb9bfc2b146161bc2c9ea08df031e7b7fc',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b06-inline/capture/01-request.json': 'ed1637202429b7885458be1f439884e93bb00475b7ad92fbe85cfbe63db73b03',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b06-inline/capture/02-request.json': 'c951526cba9502a98e0ac73d6fc3333dd03d109867f2cc2c00ede3def456aad2',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b06-inline/capture/tool-output.txt': 'fed57592028c9d8a9180c2b97f74a3cd5e0daa841aab244cf4aad78fe44626a2',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b06-inline/reported-usage.json': '650e170f1467a941aeaa3cfe903e3fb89a6bb0dd59fc62b12932686d9692d7e4',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b06-bounded/capture/01-request.json': 'ed1637202429b7885458be1f439884e93bb00475b7ad92fbe85cfbe63db73b03',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b06-bounded/capture/02-request.json': '1ef0e7a8faf092f5d6e2421f37f587ed330bdbc6c870ee31fd6ad087955a01aa',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b06-bounded/capture/tool-output.txt': 'fed57592028c9d8a9180c2b97f74a3cd5e0daa841aab244cf4aad78fe44626a2',
    '3-表现现场/r20261103-input-bytes/runs/confirm-b06-bounded/reported-usage.json': '0d24e65461254e5bedb9ef5a083b8f14e0afdff5c1f159cf4260d69e2c08d6da',
    '3-表现现场/r20261104-native-provenance/sessions/confirm-b01-codex/01-request.json': '60226f977592f9e163f66c5de3fd5e445f1ad9823c3e6991e5097089f4c7caa5',
    '3-表现现场/r20261104-native-provenance/sessions/confirm-b01-codex/02-request.json': '657c6413726ce84beb4fe887a96d892c74bf92b42b1c8b17e773d69da5712696',
    '3-表现现场/r20261104-native-provenance/sessions/confirm-b01-codex/tool-output.txt': 'fed57592028c9d8a9180c2b97f74a3cd5e0daa841aab244cf4aad78fe44626a2',
    '3-表现现场/r20261104-native-provenance/sessions/confirm-b01-codex/observations.json': '18fc65eeb22600da32fc75f00e5082c7f2339c7821ec834df7b535dfb2584508',
    '3-表现现场/r20261104-native-provenance/sessions/confirm-b01-dsh/01-request.json': 'b423638744a4ca393cad4845d6380e28af8e57028b3b0031187b82328ffbabf5',
    '3-表现现场/r20261104-native-provenance/sessions/confirm-b01-dsh/02-request.json': '2fa447a3d116bd830dd5ecafe67325502af34886fc4a3fee7249f5e169a07d31',
    '3-表现现场/r20261104-native-provenance/sessions/confirm-b01-dsh/tool-output.txt': 'fed57592028c9d8a9180c2b97f74a3cd5e0daa841aab244cf4aad78fe44626a2',
    '3-表现现场/r20261104-native-provenance/sessions/confirm-b01-dsh/observations.json': 'b6d08572c61e98e4c896ae8e29295e46684be13d9062fc245554082220c6d404',
    '3-表现现场/r20261104-native-provenance/sessions/confirm-b02-codex/01-request.json': '145961fd169e50cdf7c62f9ddd6d50f0b5c342dd99390ae18887d888e67ec4c2',
    '3-表现现场/r20261104-native-provenance/sessions/confirm-b02-codex/02-request.json': '27bb31f3aaadbf197be0663badb26d7b32906461a916f8fd8ce5570ff2ace30d',
    '3-表现现场/r20261104-native-provenance/sessions/confirm-b02-codex/tool-output.txt': 'fed57592028c9d8a9180c2b97f74a3cd5e0daa841aab244cf4aad78fe44626a2',
    '3-表现现场/r20261104-native-provenance/sessions/confirm-b02-codex/observations.json': '8b50797d8eaa3d905359a12981e5d2cfcf2c2433032a51ede62dd64c46e77664',
    '3-表现现场/r20261104-native-provenance/sessions/confirm-b02-dsh/01-request.json': 'b423638744a4ca393cad4845d6380e28af8e57028b3b0031187b82328ffbabf5',
    '3-表现现场/r20261104-native-provenance/sessions/confirm-b02-dsh/02-request.json': '616b2b8af07cbcca7fbf60c62817a0b19c79bc309ba9d5629145eb1a94a0aa81',
    '3-表现现场/r20261104-native-provenance/sessions/confirm-b02-dsh/tool-output.txt': 'fed57592028c9d8a9180c2b97f74a3cd5e0daa841aab244cf4aad78fe44626a2',
    '3-表现现场/r20261104-native-provenance/sessions/confirm-b02-dsh/observations.json': '19436b3bd0e10f93ef8061fb2f650d079045fa5dc8c9a5d6713fd6b0ec461519',
    '3-表现现场/r20261104-native-provenance/sessions/confirm-b03-codex/01-request.json': '36591e7ccfe24b364c93aa6d0f0b9aa640fb972aff3b077fcc4ceb37e840d3d5',
    '3-表现现场/r20261104-native-provenance/sessions/confirm-b03-codex/02-request.json': 'b09372a4afe1155fe656efc5bd1f7c50cb55cbe7509faf4025d01aa7b630065d',
    '3-表现现场/r20261104-native-provenance/sessions/confirm-b03-codex/tool-output.txt': 'fed57592028c9d8a9180c2b97f74a3cd5e0daa841aab244cf4aad78fe44626a2',
    '3-表现现场/r20261104-native-provenance/sessions/confirm-b03-codex/observations.json': '812926f9bbf8b5856dfb6d2b21cd17975553cec7ab43522b205018dca29eceae',
    '3-表现现场/r20261104-native-provenance/sessions/confirm-b03-dsh/01-request.json': 'b423638744a4ca393cad4845d6380e28af8e57028b3b0031187b82328ffbabf5',
    '3-表现现场/r20261104-native-provenance/sessions/confirm-b03-dsh/02-request.json': '36547aae12f84493da89cc4bee03d4d9199e15b273d179cd2c2a653e6f302dbf',
    '3-表现现场/r20261104-native-provenance/sessions/confirm-b03-dsh/tool-output.txt': 'fed57592028c9d8a9180c2b97f74a3cd5e0daa841aab244cf4aad78fe44626a2',
    '3-表现现场/r20261104-native-provenance/sessions/confirm-b03-dsh/observations.json': 'b8a6cddc2ce66db72bd97407bb066fda199efdbdcfa96b1626ed20cf81fba950',
    '5-评测报告/原生字节分解-2026-11-05/README.md': 'e653a09a2e0920089111c922ae6e4feb2f64a69662447a3e2a005bc3ea82f296',
    '1-评测方案/请求侧输入字节-2026-11-03/README.md': 'df6e7779e8e94cf7c6772309126898ec97ee2d1e8438eaa656ed6199fdb22343',
    '1-评测方案/原生来源链技术门-2026-11-04/README.md': '909833aa0aa6e00f6c02f7f860e236db48d42e1931a090134d7d42d720d96039',
}


class Invalid(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise Invalid(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result


def parse_json(data):
    def bad_constant(value):
        raise Invalid('non-finite JSON: ' + value)
    return json.loads(data, object_pairs_hook=unique_object,
                      parse_constant=bad_constant)


def safe_path(root, name):
    rel = PurePosixPath(name)
    need(not rel.is_absolute() and '..' not in rel.parts, 'unsafe source path')
    path = root.joinpath(*rel.parts)
    # Reject all symlink components, including links that happen to stay in root.
    current = root
    for part in rel.parts:
        current = current / part
        need(not current.is_symlink(), 'symlink source: ' + name)
    need(path.resolve().is_relative_to(root), 'source escapes root')
    need(path.is_file(), 'missing source: ' + name)
    return path


def read_pinned(root, pins=PINS):
    data = {}
    for name, digest in pins.items():
        raw = safe_path(root, name).read_bytes()
        need(sha(raw) == digest, 'source hash mismatch: ' + name)
        data[name] = raw
    return data


def pointer(obj, path):
    value = obj
    for part in path.split('/')[1:]:
        part = part.replace('~1', '/').replace('~0', '~')
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def controls(before, after, history_key):
    need(isinstance(before, dict) and isinstance(after, dict), 'request object required')
    a, b = before.get(history_key), after.get(history_key)
    need(isinstance(a, list) and isinstance(b, list) and len(a) > 0,
         'nonempty history lists required')
    need(len(b) > len(a), 'history suffix missing')
    need(canonical(a) == canonical(b[:len(a)]), 'history prefix changed')
    # Includes unselected control fields and their presence, not just B_input.
    x = {k: v for k, v in before.items() if k != history_key}
    y = {k: v for k, v in after.items() if k != history_key}
    need(canonical(x) == canonical(y), 'nonhistory fields changed')
    return {'history_pointer': '/' + history_key,
            'prefix_items': len(a), 'history_prefix_exact': True,
            'nonhistory_full_object_exact': True,
            'prefix_canonical_sha256': sha(canonical(a)),
            'nonhistory_canonical_sha256': sha(canonical(x))}


def all_occurrences(source, fragment):
    need(bool(fragment), 'empty source fragment')
    result, start = [], 0
    while True:
        pos = source.find(fragment, start)
        if pos < 0:
            return result
        result.append([pos, pos + len(fragment)])
        start = pos + 1


def interval_union(spans):
    merged = []
    for start, end in sorted(spans):
        need(type(start) is int and type(end) is int and 0 <= start < end,
             'invalid byte interval')
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


def interval_contains(spans, start, end):
    return any(a <= start and end <= b for a, b in interval_union(spans))


def reconstruct(source, texts, segments):
    """Exact per-leaf reconstruction and positional ambiguity accounting.

    Every leaf byte belongs to one ordered source or literal segment. A source
    segment records ALL occurrences; multiple matches are not counted as all
    retained source positions. Certain/possible intervals are kept separate.
    Literal bytes may coincidentally occur in source; their role is presentation,
    not a claim of algorithmic incompressibility or substring nonmembership.
    """
    need(len(texts) == len(segments), 'leaf/segment count mismatch')
    possible, certain, records, copied, wrapper = [], [], [], 0, 0
    for leaf, (text, parts) in enumerate(zip(texts, segments)):
        need(isinstance(text, str), 'text leaf must be string')
        rebuilt, offset = bytearray(), 0
        for part in parts:
            if 'source' in part:
                start, end = part['source']
                need(type(start) is int and type(end) is int and
                     0 <= start < end <= len(source), 'source bounds invalid')
                fragment = source[start:end]
                candidates = all_occurrences(source, fragment)
                need([start, end] in candidates, 'declared mapping absent')
                # Intersection of candidate positions: bytes certainly covered
                # by one copy even if its source identity is not identifiable.
                lo = max(a for a, b in candidates)
                hi = min(b for a, b in candidates)
                if lo < hi:
                    certain.append([lo, hi])
                possible.extend(candidates)
                copied += len(fragment)
                records.append({'leaf': leaf, 'text_interval': [offset, offset+len(fragment)],
                                'declared_source_interval': [start, end],
                                'source_candidates': candidates,
                                'unique_source_location': len(candidates) == 1})
            else:
                need(set(part) == {'literal'} and isinstance(part['literal'], bytes),
                     'literal bytes required')
                fragment = part['literal']
                wrapper += len(fragment)
            rebuilt.extend(fragment)
            offset += len(fragment)
        need(bytes(rebuilt) == text.encode('utf-8'),
             'exact reconstruction failed at leaf %d: expected %d bytes, observed %d bytes' %
             (leaf, len(rebuilt), len(text.encode('utf-8'))))
    certain, possible = interval_union(certain), interval_union(possible)
    total = sum(len(t.encode('utf-8')) for t in texts)
    need(total == copied + wrapper, 'text partition failed')
    return {'segments': records, 'certain_source_intervals': certain,
            'possible_source_intervals': possible,
            'source_copy_bytes_with_multiplicity': copied,
            'certain_unique_source_bytes': sum(b-a for a,b in certain),
            'possible_unique_source_bytes': sum(b-a for a,b in possible),
            'presentation_bytes': wrapper, 'decoded_text_bytes': total,
            'exact_reconstruction': True,
            'all_source_segments_unique': all(x['unique_source_location'] for x in records)}


def shape(source, kind, time_leaf=None, reference_alias=None):
    """Post-hoc offline shape model, not product code or product observation."""
    n = len(source)
    if kind == 'inline':
        return [[{'source': [0, n]}]]
    if kind == 'bounded':
        need(n > 1728, 'fixture too short for bounded shape')
        if reference_alias is None:
            reference_alias = 'P'*119
        need(len(reference_alias.encode('ascii')) == 119 and
             re.fullmatch(r'[A-Za-z0-9/.]+', reference_alias) is not None,
             'invalid public reference alias')
        footer = ('\n\n(Omitted %d bytes. Full formatted result stored at: ' % (n-1728)
                  + reference_alias + ' Use read with offset/limit, or grep this path to search within it.)')
        return [[{'source': [0, 864]}, {'literal': b'\n\n[...]\n\n'},
                 {'source': [n-864, n]}, {'literal': footer.encode('utf-8')}]]
    need(kind == 'codex' and isinstance(time_leaf, str), 'unknown shape or time leaf')
    need(re.fullmatch(r'Wall time: [0-9]+\.[0-9]+ seconds\nOutput:', time_leaf) is not None,
         'invalid time leaf')
    need(n > 11964, 'fixture too short for codex shape')
    return [[{'literal': time_leaf.encode('utf-8')}],
            [{'source': [0, 5982]}, {'literal': '…8 tokens truncated…'.encode('utf-8')},
             {'source': [n-5982, n]}]]


def render_shape(source, kind, time_leaf=None):
    return [b''.join(source[s['source'][0]:s['source'][1]] if 'source' in s
                     else s['literal'] for s in parts).decode('utf-8')
            for parts in shape(source, kind, time_leaf)]


def noise_lines(source):
    result, offset = [], 0
    for line_no, raw in enumerate(source.splitlines(keepends=True), 1):
        match = re.fullmatch(rb'noise-([0-9]{4}) checksum=([0-9a-f]{64})\n', raw)
        if match:
            result.append({'index': int(match[1]), 'line': line_no,
                           'interval': [offset, offset+len(raw)],
                           'value_interval': [offset+20, offset+84]})
        offset += len(raw)
    return result


def line_coverage(source, spans):
    lines = noise_lines(source)
    retained, partial, with_lf = [], [], []
    for line in lines:
        start, end = line['interval']
        # Source records have LF; separate full record content from delimiter.
        if interval_contains(spans, start, end-1):
            retained.append(line['index'])
        elif any(a < end-1 and start < b for a,b in spans):
            partial.append(line['index'])
        if interval_contains(spans, start, end):
            with_lf.append(line['index'])
    return {'denominator_complete_noise_lines': len(lines),
            'complete_noise_lines_copied': len(retained),
            'complete_noise_lines_including_source_lf': len(with_lf),
            'complete_noise_indices': retained, 'partial_noise_indices': partial,
            'content_complete_but_source_lf_missing': sorted(set(retained)-set(with_lf)),
            'definition': 'entire source record content excluding LF in certain interval union; LF separately counted'}


def text_leaves(before, after, arm):
    hk = 'input' if arm == 'codex' else 'messages'
    start, suffix = len(before[hk]), after[hk][len(before[hk]):]
    if arm == 'codex':
        returns = [(start+i, x) for i,x in enumerate(suffix)
                   if x.get('type') == 'function_call_output']
        need(len(returns) == 1 and returns[0][0] == len(after[hk])-1,
             'unique final codex return required')
        index, returned = returns[0]
        calls = [x for x in suffix if x.get('type') == 'function_call']
        need(len(calls) == 1 and calls[0].get('name') == 'fixture_output' and
             calls[0].get('call_id') == returned.get('call_id'), 'codex call link mismatch')
        leaves = returned.get('output')
        need(isinstance(leaves, list) and len(leaves) == 2 and
             all(set(x) == {'type', 'text'} and x['type'] == 'input_text' for x in leaves),
             'codex two text leaves required')
        return [f'/input/{index}/output/{i}/text' for i in range(2)]
    need(len(suffix) == 2 and suffix[0].get('role') == 'assistant'
         and suffix[1].get('role') == 'user', 'DSH append schema mismatch')
    calls = [x for x in suffix[0]['content'] if x.get('type') == 'tool_use']
    content = suffix[1]['content']
    need(len(content) == 1 and content[0].get('type') == 'tool_result', 'DSH result mismatch')
    returned = content[0]
    need(len(calls) == 1 and calls[0].get('name') == 'fixture_output' and
         calls[0].get('id') == returned.get('tool_use_id'), 'DSH call link mismatch')
    leaves = returned.get('content')
    need(isinstance(leaves, list) and len(leaves) == 1 and
         set(leaves[0]) == {'type', 'text'} and leaves[0]['type'] == 'text',
         'DSH one text leaf required')
    return [f'/messages/{start+1}/content/0/content/0/text']


def literal_fact_occurrences(value, needle, path=''):
    """Exact literal witnesses only; not semantic recovery or product success."""
    if isinstance(value, str):
        return [path] if needle in value.encode('utf-8') else []
    if isinstance(value, list):
        return [p for i,x in enumerate(value)
                for p in literal_fact_occurrences(x,needle,path+'/'+str(i))]
    if isinstance(value, dict):
        return [p for k,x in value.items()
                for p in literal_fact_occurrences(x,needle,path+'/'+k.replace('~','~0').replace('/','~1'))]
    return []


def fact_probes(source, before, after):
    middle = next(x for x in noise_lines(source) if x['index'] == 200)['value_interval']
    values = [('noise_0200_checksum',middle)]
    for label, token in [('HEAD_KEY',b'AMBER-731'),('TAIL_KEY',b'COBALT-492')]:
        start = source.index(token)
        values.append((label,[start,start+len(token)]))
    return {name:{'source_value_interval':span,
                  'value_sha256':sha(source[span[0]:span[1]]),
                  'before_string_leaf_pointers':literal_fact_occurrences(before,source[span[0]:span[1]]),
                  'after_string_leaf_pointers':literal_fact_occurrences(after,source[span[0]:span[1]])}
            for name,span in values}


def selected_bytes(request, codex):
    keys = ('instructions', 'input', 'tools', 'previous_response_id') if codex else ('system','messages','tools')
    return len(canonical({k:request[k] for k in keys if k in request}))


def recovery_status(reference_present, allowed_extra_tools=False, read_evidence=None):
    # A reference is not a content-return event; no implicit filesystem reads.
    return {'reference_text_present': reference_present,
            'extra_tool_use_allowed_by_contract': allowed_extra_tools,
            'actual_readback_evidence': read_evidence,
            'recovery_tested': read_evidence is not None,
            'full_source_recoverability': None}


def cases():
    for family, count, arms in (('same_dsh_six_pairs',6,('inline','bounded')),
                                ('native_three_blocks',3,('codex','dsh'))):
        for block in range(1,count+1):
            for arm in arms:
                native = family == 'native_three_blocks'
                directory = f'{NATIVE if native else SAME}/confirm-b{block:02d}-{arm}'
                capture = directory if native else directory+'/capture'
                yield family, block, arm, directory, capture


def diagnostics(source):
    target = next(x for x in noise_lines(source) if x['index'] == 200)
    pos = target['value_interval'][0]
    middle = source[:pos] + (b'0' if source[pos:pos+1] != b'0' else b'1') + source[pos+1:]
    visible_pos = source.index(b'AMBER-731')
    visible = source[:visible_pos] + b'Z' + source[visible_pos+1:]
    rows = []
    for kind in ('bounded', 'codex', 'inline'):
        time_leaf = 'Wall time: 0.0025 seconds\nOutput:' if kind == 'codex' else None
        old = render_shape(source, kind, time_leaf)
        new = render_shape(middle, kind, time_leaf)
        changed = render_shape(visible, kind, time_leaf)
        middle_equal = old == new
        need(middle_equal == (kind != 'inline'), 'middle counterexample failed')
        need(old != changed, 'visible-key sensitivity failed')
        rows.append({'shape': kind, 'base_leaf_hashes': [sha(x.encode()) for x in old],
                     'middle_mutation_leaf_hashes': [sha(x.encode()) for x in new],
                     'same_preview_after_middle_mutation': middle_equal,
                     'visible_key_mutation_changes_preview': old != changed})
    before = {'messages':[{'role':'user','content':'AA'},{'role':'user','content':'BB'}],
              'tools': [], 'model':'fixed'}
    after = copy.deepcopy(before)
    after['messages'].append({'role':'assistant','content':'CC'})
    control_results = {}
    swapped = copy.deepcopy(after)
    swapped['messages'][:2] = list(reversed(swapped['messages'][:2]))
    need(len(canonical(swapped)) == len(canonical(after)), 'swap length changed')
    deleted = copy.deepcopy(after)
    del deleted['messages'][0]
    altered = copy.deepcopy(after)
    altered['model'] = 'other'
    for name, candidate in [('same_length_history_swap',swapped),('history_deletion',deleted),
                             ('nonhistory_change',altered)]:
        try:
            controls(before,candidate,'messages')
        except Invalid as exc:
            control_results[name] = {'rejected':True, 'reason':str(exc)}
        else:
            raise Invalid('control counterexample accepted: '+name)
    # Pure wrapper change: same ordered text and source coverage, larger JSON.
    single = [{'type':'text','text':'alphaβomega'}]
    split = [{'type':'text','text':'alphaβ'},{'type':'text','text':'omega'}]
    need(''.join(x['text'] for x in single) == ''.join(x['text'] for x in split),
         'split ordered text changed')
    return {'identity':'new offline shape model and validator diagnostics; NOT product execution',
            'source_sha256_before':sha(source),'source_sha256_middle_mutation':sha(middle),
            'mutated_byte_offset':pos,'target_checksum_interval':target['value_interval'],
            'target_source_line':target['line'], 'source_length_unchanged':len(source)==len(middle),
            'shape_controls':rows,'history_controls':control_results,
            'pure_leaf_split':{'ordered_text_equal':True,
                               'canonical_bytes_before':len(canonical(single)),
                               'canonical_bytes_after':len(canonical(split))}}


def analyze(root):
    root = Path(root).resolve()
    raw = read_pinned(root)
    groups = {'same_dsh_six_pairs':{'pairs':6,'rows':[]},
              'native_three_blocks':{'blocks':3,'rows':[]}}
    diagnostic_source = None
    for family, block, arm, directory, capture in cases():
        before_path, after_path = capture+'/01-request.json', capture+'/02-request.json'
        source_path = capture+'/tool-output.txt'
        before, after = parse_json(raw[before_path]), parse_json(raw[after_path])
        source = raw[source_path]
        need(sha(source) == SOURCE_SHA and len(source) == 35767, 'fixture identity mismatch')
        source.decode('utf-8')
        diagnostic_source = source
        hk = 'input' if arm == 'codex' else 'messages'
        control = controls(before,after,hk)
        pointers = text_leaves(before,after,arm)
        texts = [pointer(after,p) for p in pointers]
        kind = 'codex' if arm == 'codex' else ('inline' if arm == 'inline' else 'bounded')
        alias = None
        if kind == 'bounded':
            match = re.search(r'Full formatted result stored at: ([A-Za-z0-9/.]+) Use read', texts[0])
            need(match is not None, 'bounded reference schema missing')
            alias = match[1]
        parts = shape(source,kind,texts[0] if kind == 'codex' else None,alias)
        try:
            coverage = reconstruct(source,texts,parts)
        except Invalid as exc:
            raise Invalid(after_path + ': ' + str(exc)) from exc
        need(coverage['all_source_segments_unique'], 'observed fixture mapping ambiguous')
        coverage['source_utf8_bytes_denominator'] = len(source)
        coverage['source_byte_fraction'] = {'numerator':coverage['certain_unique_source_bytes'],
                                            'denominator':len(source)}
        coverage['noise_lines'] = line_coverage(source,coverage['certain_source_intervals'])
        # Compact runs, not hundreds of copied source lines.
        ids = coverage['noise_lines'].pop('complete_noise_indices')
        coverage['noise_lines']['complete_noise_index_intervals'] = interval_union([[i,i+1] for i in ids])
        native = family == 'native_three_blocks'
        usage_path = directory+('/observations.json' if native else '/reported-usage.json')
        usage_source = parse_json(raw[usage_path])
        usage = usage_source.get('usage') if native else usage_source
        if native:
            need(usage_source['projection_metric']['before'] == selected_bytes(before,arm=='codex')
                 and usage_source['projection_metric']['after'] == selected_bytes(after,arm=='codex'),
                 'native selected metric mismatch')
        row = {'block':block,'arm':arm,
               'source':{'path':source_path,'sha256':sha(source)},
               'requests':{'before':before_path,'after':after_path,'text_pointers':pointers},
               'controls':control,'coverage':coverage,
               'literal_fact_probes':fact_probes(source,before,after),
               'request_bytes':{'unit':'canonical selected UTF-8 JSON bytes',
                                'before':selected_bytes(before,arm=='codex'),
                                'after':selected_bytes(after,arm=='codex'),
                                'delta':selected_bytes(after,arm=='codex')-selected_bytes(before,arm=='codex')},
               'product_reported_usage':{'source':usage_path,'pointer':'/usage' if native else '',
                                         'events':usage,'aggregation':None},
               'recovery':recovery_status(kind=='bounded'),
               'controls_scope':'captured Req1 to Req2 only; no inference before capture or backend',
               'actual_reasoning_controlled':False,'actual_cache_controlled':False}
        groups[family]['rows'].append(row)
    return {'status':'PASS_PUBLIC_SOURCE_COVERAGE',
            'identity':'post-hoc derived reanalysis; not original sealed evidence',
            'baseline_commit':BASELINE_COMMIT,'pins':PINS,
            'new_product_or_model_requests':0,
            'domain':'pinned public projections; not private originals or server final context',
            'groups':groups,'synthetic_diagnostics':diagnostics(diagnostic_source),
            'native_text_difference':{'decoded_text_bytes':10040,
                                      'source_copy_byte_difference':10236,
                                      'presentation_byte_difference':-196,
                                      'interpretation':'descriptive identity, NOT equal-text controlled residual'},
            'unknown':{'backend_final_input':None,'global_source_loss':None,
                       'actual_reasoning_equal':None,'actual_cache_equal':None,
                       'general_semantic_information_retention':None,
                       'tokens_or_cost_effect':None,'original_seal_reauthenticated':False}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output',type=Path,help='exclusive new JSON file; never overwrite')
    args = parser.parse_args(argv)
    try:
        result = analyze(args.root)
        text = json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n'
        if args.output is None:
            sys.stdout.write(text)
        else:
            # Verify everything before opening; x mode forbids replacement.
            with args.output.open('x',encoding='utf-8') as output:
                output.write(text)
        return 0
    except (Invalid,OSError,ValueError,KeyError,TypeError,IndexError) as exc:
        print('FAIL_PUBLIC_SOURCE_COVERAGE: '+str(exc),file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
