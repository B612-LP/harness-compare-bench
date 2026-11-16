#!/usr/bin/env python3
"""Read-only archived-input identity audit; public mode stdlib, raw mode zstandard.
Only source-bound hashes, byte counts and value-free difference paths are published.
No imports of historical runners; no subprocess, network, product or model operations.
"""
import argparse
from collections import Counter
from itertools import combinations
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = '4-打分细则/输入事件等长与同一性-2026-11-16'
V11 = '4-打分细则/机制重复口径澄清-2026-11-12/evidence.json'
V2 = '4-打分细则/机制序列口径v2-2026-11-16/result.json'
BASELINE = '50c073c084006c0bfd5f8b79db3bc495e842847b'
BINDINGS = {
    V11: '925470d3b55b4226d70f5749d45d0c65a161703c4053fa21028ce0516fcd6b5c',
    V2: 'c95f932719477625c473b02e1dd1ec4a7f7d5b191b6b79be22e8a4ab45507609',
    HERE + '/README.md': '0bf50230ec6f55fa7e7f6a0278ef96ceffbfce87881cad1616a9c7ab80049170',
}
CASES = ('bird-ca-schools-15', 'dabstep-payments-10', 'exercism-py-6',
         'lcb-recent-hard-4', 'tb-cargo-plan')
I_TYPES = frozenset(('user/message', 'request/header', 'request/context',
                     'system/message', 'agent/inbox/spliced'))
S3_TYPES = frozenset(('user/message', 'request/header', 'request/context'))
LAYERS = ('L0', 'L1', 'L2')
STRUCTURE_KEYS = frozenset(('seq', 'time', 'type', 'data', 'surfaceOp', 'id',
    'source', 'content', 'role', 'message', 'inserted', 'start', 'removedCount',
    'target', 'turn', 'step', 'text', 'kind', 'header', 'reason', 'config',
    'tools', 'name', 'description', 'parameters', 'properties', 'required',
    'items', 'model', 'provider', 'contextWindow', 'systemPromptUpdate',
    'maxTokens', 'reasoningEffort', 'adapterDefaults', 'baseline',
    'baselineIdentity', 'changes', 'action', 'digest', 'path', 'scope',
    'form', 'sections'))


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def strict_object(pairs):
    out = {}
    for key, value in pairs:
        require(key not in out, 'duplicate JSON object key')
        out[key] = value
    return out


def load_json(raw):
    def reject(value):
        raise Invalid('non-finite JSON constant')
    return json.loads(raw, object_pairs_hook=strict_object, parse_constant=reject)


def safe_path(root, relative):
    rel = Path(relative)
    require(not rel.is_absolute() and '..' not in rel.parts, 'unsafe source path')
    path = (root / rel).resolve()
    require(root in path.parents, 'source escapes root')
    return path


def source_objects(root):
    out = {}
    for relative, expected in BINDINGS.items():
        raw = safe_path(root, relative).read_bytes()
        require(sha(raw) == expected, 'source SHA mismatch: ' + relative)
        if relative.endswith('.json'):
            out[relative] = load_json(raw)
    v11, v2 = out[V11], out[V2]
    require(v11['schema'] == 'r1109-content-free-projection-v1.1', 'bad v1.1 schema')
    ids = [s['slot'] for s in v11['slots']]
    expected = {f'{a}__{c}__r{r}' for a in ('dsh', 'codex') for c in CASES for r in (1, 2, 3)}
    require(len(ids) == 30 and len(set(ids)) == 30 and set(ids) == expected, 'bad v1.1 slot scope')
    require(v2['schema'] == 'mech-seq-v2-projection-v1', 'bad v2 schema')
    scope(v2['slots'])
    require(len(v2['groups']) == 5 and {g['case'] for g in v2['groups']} == set(CASES), 'bad v2 group scope')
    return v11, v2


def expected_slots():
    return [f'dsh__{c}__r{r}' for c in CASES for r in (1, 2, 3)]


def scope(rows):
    require(isinstance(rows, list), 'slots must be list')
    ids = [s['slot'] for s in rows]
    require(len(ids) == 15 and len(set(ids)) == 15 and set(ids) == set(expected_slots()),
            'missing, duplicate or mixed slot')


def take(obj, keys):
    require(isinstance(obj, dict), 'expected object in L2')
    require(all(k in obj for k in keys), 'missing required L2 field')
    return {k: obj[k] for k in keys}


def content_face(event):
    t = event['type']
    d = event['data']
    require(isinstance(d, dict), 'data must be object')
    if t == 'agent/inbox/spliced':
        out = take(d, ('start', 'target', 'inserted'))
        require(isinstance(d['inserted'], list), 'inserted must be list')
        out['inserted'] = [take(x, ('role', 'content')) for x in d['inserted']]
        if 'removedCount' in d:
            out['removedCount'] = d['removedCount']
        return out
    if t == 'system/message':
        out = take(d, ('turn', 'step', 'message'))
        out['message'] = take(d['message'], ('role', 'content'))
        return out
    if t == 'user/message':
        return take(d, ('role', 'content'))
    require(t in ('request/header', 'request/context'), 'unknown L2 event type')
    return d


def project(events):
    require(isinstance(events, list) and events, 'missing event list')
    selected = []
    for event in events:
        require(isinstance(event, dict) and isinstance(event.get('type'), str), 'bad event schema')
        if event['type'] in I_TYPES:
            require(isinstance(event.get('data'), dict), 'bad input data schema')
            selected.append(event)
    require(selected, 'no input events')
    layers = {'L0': selected, 'L1': [e['data'] for e in selected],
              'L2': [content_face(e) for e in selected]}
    return [e['type'] for e in selected], layers


def fingerprint(values):
    raw = [canon(x) for x in values]
    return {'stream_sha256': sha(canon(values)), 'stream_bytes': len(canon(values)),
            'event_sha256': [sha(x) for x in raw], 'event_bytes': [len(x) for x in raw]}


def safe_segment(key):
    if key in STRUCTURE_KEYS:
        return key.replace('~', '~0').replace('/', '~1')
    return '@sha256-' + sha(key.encode('utf-8'))


MISSING = object()


def atom(value):
    if value is MISSING:
        return {'type': 'missing', 'bytes': None, 'sha256': None}
    return {'type': type(value).__name__, 'bytes': len(canon(value)), 'sha256': sha(canon(value))}


def differences(left, right, path=''):
    """Complete path diagnostic; no leaf values, and no dynamic key values."""
    if left is not MISSING and right is not MISSING and canon(left) == canon(right):
        return []
    if isinstance(left, dict) and isinstance(right, dict):
        out = []
        for key in sorted(left.keys() | right.keys()):
            out += differences(left.get(key, MISSING), right.get(key, MISSING), path + '/' + safe_segment(key))
        return out
    if isinstance(left, list) and isinstance(right, list):
        out = []
        for i in range(max(len(left), len(right))):
            out += differences(left[i] if i < len(left) else MISSING,
                               right[i] if i < len(right) else MISSING, path + '/' + str(i))
        return out
    return [{'path': path, 'left': atom(left), 'right': atom(right)}]


def pair_record(left_slot, right_slot, left_types, right_types, left_layers, right_layers):
    aligned = left_types == right_types
    equal = {k: canon(left_layers[k]) == canon(right_layers[k]) for k in LAYERS}
    paths = {k: [] for k in LAYERS}
    if aligned:
        for k in LAYERS:
            for i, (a, b) in enumerate(zip(left_layers[k], right_layers[k])):
                diffs = differences(a, b)
                if diffs:
                    paths[k].append({'i': i, 'type': left_types[i], 'differences': diffs})
    return {'left': left_slot, 'right': right_slot, 'aligned': aligned,
            'status': 'aligned' if aligned else 'not_aligned', 'equal': equal,
            'path_differences': paths}


def prior_metrics(events):
    types = [e['type'] for e in events if e['type'] in I_TYPES]
    return {'i_sequence': types, 'i_sequence_sha256': sha(canon(types)),
            'i_event_count': len(types),
            'i_bytes': sum(len(canon(e)) for e in events if e['type'] in I_TYPES),
            's3_bytes': sum(len(canon(e)) for e in events if e['type'] in S3_TYPES)}


def prior_gate(rows):
    b1 = max(r['s3_bytes'] for r in rows) - min(r['s3_bytes'] for r in rows)
    b2 = max(r['i_bytes'] for r in rows) - min(r['i_bytes'] for r in rows)
    s1 = all(r['i_sequence'] == rows[0]['i_sequence'] for r in rows)
    return {'b1_max_minus_min': b1, 'b2_max_minus_min': b2,
            'b1_pass': b1 <= 100, 'b2_pass': b2 <= 100, 's1_pass': s1,
            'gate_v2': 'pass' if b1 <= 100 and b2 <= 100 and s1 else 'fail'}


def extract(root, archive_root):
    v11, v2 = source_objects(root)
    try:
        import zstandard
    except ImportError as error:
        raise Invalid('raw mode needs zstandard; public mode uses stdlib only') from error
    raw_slots = {}
    rows = []
    old = {s['slot']: s for s in v2['slots']}
    for source in sorted((s for s in v11['slots'] if s['slot'].startswith('dsh__')), key=lambda x: x['slot']):
        slot = source['slot']
        identity = source['identity']
        relative = f'dsh/runs/{slot}/agent-session/session.v4.jsonl.zstd'
        require(identity['source_relative_to_archive'] == relative, 'trace slot path mismatch')
        raw = safe_path(archive_root, relative).read_bytes()
        require(sha(raw) == identity['sha256'], 'raw SHA mismatch: ' + slot)
        with zstandard.ZstdDecompressor().stream_reader(raw) as stream:
            events = [load_json(line) for line in stream.read().splitlines() if line.strip()]
        projection = [[e['type'], len(canon(e)), None, 0] for e in events]
        require(projection == source['events'], 'old event projection mismatch: ' + slot)
        metrics = prior_metrics(events)
        for key, value in metrics.items():
            require(value == old[slot][key], 'v2 metric mismatch: ' + slot + ' ' + key)
        types, layers = project(events)
        raw_slots[slot] = (types, layers)
        rows.append({'slot': slot, 'identity': {k: identity[k] for k in ('source_relative_to_archive', 'sha256', 'version')}, 'old_projection_checked': True,
                     'v2_metrics_checked': True, 'prior_metrics': metrics,
                     'layers': {k: fingerprint(layers[k]) for k in LAYERS}})
    scope(rows)
    pairs = []
    for case in CASES:
        for a, b in combinations((f'dsh__{case}__r{r}' for r in (1, 2, 3)), 2):
            at, al = raw_slots[a]; bt, bl = raw_slots[b]
            pair = pair_record(a, b, at, bt, al, bl)
            for k in LAYERS:
                require(pair['equal'][k] == (sha(canon(al[k])) == sha(canon(bl[k]))), 'SHA collision')
            pairs.append(pair)
    evidence = {'schema': 'input-event-identity-evidence-v1', 'baseline_commit': BASELINE,
                'source_bindings': BINDINGS, 'slots': rows, 'pairs': pairs,
                'note': 'Raw leaf values and dynamic key names omitted; original authenticity not certified.'}
    analyze(evidence, v11, v2)
    return evidence


def is_digest(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def validate_fp(fp, n):
    require(set(fp) == {'stream_sha256', 'stream_bytes', 'event_sha256', 'event_bytes'}, 'bad fingerprint fields')
    require(is_digest(fp['stream_sha256']), 'invalid stream SHA')
    require(type(fp['stream_bytes']) is int and fp['stream_bytes'] > 0, 'bad stream bytes')
    require(len(fp['event_sha256']) == len(fp['event_bytes']) == n, 'bad fingerprint event scope')
    require(all(is_digest(x) for x in fp['event_sha256']), 'invalid event SHA')
    require(all(type(x) is int and x > 0 for x in fp['event_bytes']), 'invalid event bytes')
    require(fp['stream_bytes'] == sum(fp['event_bytes']) + max(0, n - 1) + 2, 'stream framing mismatch')


def analyze(evidence, v11, v2):
    require(evidence['schema'] == 'input-event-identity-evidence-v1', 'bad evidence schema')
    require(evidence['baseline_commit'] == BASELINE and evidence['source_bindings'] == BINDINGS, 'bad evidence binding')
    scope(evidence['slots'])
    slots = {s['slot']: s for s in evidence['slots']}
    old = {s['slot']: s for s in v2['slots']}
    original = {s['slot']: s for s in v11['slots']}
    for slot, row in slots.items():
        require(row['identity'] == {k: original[slot]['identity'][k] for k in ('source_relative_to_archive', 'sha256', 'version')}, 'source identity mismatch')
        require(row['old_projection_checked'] is True and row['v2_metrics_checked'] is True, 'unchecked source')
        require(set(row['prior_metrics']) == set(prior_metrics([{'type': 'other'}])), 'bad prior metric keys')
        for key, value in row['prior_metrics'].items():
            require(value == old[slot][key], 'v2 metric mismatch')
        n = row['prior_metrics']['i_event_count']
        require(set(row['layers']) == set(LAYERS), 'bad layers')
        for fp in row['layers'].values():
            validate_fp(fp, n)
        expected_lengths = [r[1] for r in original[slot]['events'] if r[0] in I_TYPES]
        require(row['layers']['L0']['event_bytes'] == expected_lengths, 'L0 old length vector mismatch')
    expected_pairs = [(f'dsh__{c}__r{a}', f'dsh__{c}__r{b}') for c in CASES for a, b in ((1, 2), (1, 3), (2, 3))]
    require([(p['left'], p['right']) for p in evidence['pairs']] == expected_pairs, 'missing, duplicate or mixed pair')
    diagnostic_summary = Counter()
    for pair in evidence['pairs']:
        a, b = slots[pair['left']], slots[pair['right']]
        aligned = a['prior_metrics']['i_sequence'] == b['prior_metrics']['i_sequence']
        require(pair['aligned'] is aligned and pair['status'] == ('aligned' if aligned else 'not_aligned'), 'bad alignment')
        require(set(pair['equal']) == set(pair['path_differences']) == set(LAYERS), 'bad pair layers')
        for k in LAYERS:
            af, bf = a['layers'][k], b['layers'][k]
            same = af['stream_sha256'] == bf['stream_sha256']
            require(same == (af['event_sha256'] == bf['event_sha256']), 'stream/event identity disagreement')
            require(pair['equal'][k] is same, 'pair equality/hash disagreement')
            if same:
                require(af == bf, 'equal stream has unequal fingerprints')
            diffs = pair['path_differences'][k]
            require(isinstance(diffs, list), 'bad diagnostic list')
            if not aligned:
                require(not diffs, 'nonaligned pair has forced positional differences')
                continue
            changed = [i for i, (x, y) in enumerate(zip(af['event_sha256'], bf['event_sha256'])) if x != y]
            require([d['i'] for d in diffs] == changed, 'diagnostic event coverage mismatch')
            for event in diffs:
                i = event['i']
                require(event['type'] == a['prior_metrics']['i_sequence'][i], 'diagnostic event type mismatch')
                leaves = event['differences']
                require(leaves and len({d['path'] for d in leaves}) == len(leaves), 'empty or duplicate leaf paths')
                for d in leaves:
                    require(set(d) == {'path', 'left', 'right'} and isinstance(d['path'], str), 'bad leaf schema')
                    segments = d['path'].split('/')[1:] if d['path'].startswith('/') else []
                    require(d['path'] == '' or (segments and all(
                        s in STRUCTURE_KEYS or re.fullmatch(r'0|[1-9][0-9]*|@sha256-[0-9a-f]{64}', s)
                        for s in segments)), 'unsafe diagnostic key path')
                    for side in ('left', 'right'):
                        atom_ = d[side]
                        require(set(atom_) == {'type', 'bytes', 'sha256'}, 'leaf values must not be published')
                        if atom_['type'] == 'missing':
                            require(atom_['bytes'] is None and atom_['sha256'] is None, 'bad missing atom')
                        else:
                            require(atom_['type'] in ('str', 'int', 'float', 'bool', 'NoneType', 'dict', 'list'), 'bad leaf type')
                            require(type(atom_['bytes']) is int and atom_['bytes'] > 0 and is_digest(atom_['sha256']), 'bad leaf fingerprint')
                    require(d['left'] != d['right'], 'unchanged diagnostic leaf')
                    diagnostic_summary[(k, event['type'], d['path'])] += 1
    groups = []
    old_groups = {g['case']: g for g in v2['groups']}
    for case in CASES:
        members = [slots[f'dsh__{case}__r{r}'] for r in (1, 2, 3)]
        prior = prior_gate([r['prior_metrics'] for r in members])
        for k, v in prior.items():
            require(v == old_groups[case][k], 'v2 group gate mismatch')
        pairs = [p for p in evidence['pairs'] if p['left'].startswith('dsh__' + case + '__')]
        equality = {k: all(p['equal'][k] for p in pairs) for k in LAYERS}
        if not prior['s1_pass']:
            branch = 'NOT-ALIGNABLE'
        elif equality['L0']:
            branch = 'IDENTICAL'
        elif equality['L1'] or equality['L2']:
            branch = 'ENVELOPE-OR-PROVENANCE-DIFFERENCE'
        else:
            branch = 'CONTENT-FACE-DIFFERENCE'
        groups.append({'case': case, 'rep': [1, 2, 3], 'prior_v2': prior,
                       'layer_all_equal': equality, 'branch': branch})
    candidate = [g for g in groups if g['prior_v2']['gate_v2'] == 'pass']
    require(len(candidate) == 4, 'old v2 candidate denominator changed')
    return {'schema': 'input-event-identity-result-v1', 'baseline_commit': BASELINE,
            'source_bindings': BINDINGS, 'evidence_sha256': sha(canon(evidence)),
            'coverage': {'slots': 15, 'groups': 5, 'pairs': 15,
                         'aligned_pairs': sum(p['aligned'] for p in evidence['pairs'])},
            'primary': {'old_v2_pass_groups': 4, 'L0_identical_groups': sum(g['layer_all_equal']['L0'] for g in candidate)},
            'groups': groups,
            'diagnostic_path_counts': [{'layer': k, 'event_type': t, 'path': p, 'event_pair_occurrences': n}
                                       for (k, t, p), n in sorted(diagnostic_summary.items())],
            'limitations': ['Public mode validates hash/length/path witness arithmetic, not raw authenticity.',
                            'L2 is a frozen diagnostic projection, not a captured HTTP request or semantic equivalence.',
                            'v2 length/sequence gate remains unchanged; no new product runs or score edits.']}


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--archive-root', type=Path, help='optional private launch-r1109 archive root; reads pinned originals')
    parser.add_argument('--write-evidence', type=Path, help='exclusive new evidence output, requires --archive-root')
    parser.add_argument('--evidence', type=Path, help='public safe evidence, defaults to this package evidence.json')
    parser.add_argument('--output', type=Path, help='exclusive new full result JSON; stdout is summary only')
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        v11, v2 = source_objects(root)
        require(not args.write_evidence or args.archive_root, '--write-evidence requires --archive-root')
        require(not (args.archive_root and args.evidence), 'raw mode and alternate evidence are exclusive')
        if args.archive_root:
            evidence = extract(root, args.archive_root.resolve())
            if args.write_evidence:
                write_new(args.write_evidence, evidence)
        else:
            evidence = load_json((args.evidence or root / HERE / 'evidence.json').read_bytes())
        result = analyze(evidence, v11, v2)
        if args.output:
            write_new(args.output, result)
        print(json.dumps({'ok': True, 'coverage': result['coverage'], 'primary': result['primary'],
                          'branches': {g['case']: g['branch'] for g in result['groups']}}, ensure_ascii=False, sort_keys=True))
        return 0
    except (Invalid, OSError, ValueError, KeyError, TypeError, IndexError) as error:
        print(json.dumps({'ok': False, 'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
