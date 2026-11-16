#!/usr/bin/env python3
"""Request-side cross-run extension: five same-task real runs (r1..r5).

Private build (needs the private archive base): --archive-base with 5 run dirs.
Public replay (no private data): --evidence evidence.json.
stdlib only; python3 -I -S safe. See README.md for scope and limits."""
import argparse
import hashlib
import json
import pathlib
import re
import sys

SCHEMA_EVIDENCE = 'req-side-extension-evidence-v1'
SCHEMA_RESULT = 'req-side-extension-result-v1'
BASELINE = '6eec2ace862a41f03d2b0bfebfd387a48e08d0cd'
REQ_NAMES = ('001', '002', '003')
RUN_LABELS = ('r1', 'r2', 'r3', 'r4', 'r5')
RUN_RELS = {
    'r1': 'loop1/capture',
    'r2': 'loop5/capture-r2',
    'r3': 'loop6/capture-r3',
    'r4': 'loop6/capture-r4',
    'r5': 'loop6/capture-r5',
}
CALL_ID = re.compile(r'^call_[0-9a-f]{24}$')

PINS = {
    '4-打分细则/请求侧跨运行重建验证-2026-11-16/README.md':
        'a6206a2a122d2acb825bf7e30142e1b5a01d0ea6a04fc33bce9ea7e9859d3aff',
    '4-打分细则/请求侧跨运行重建验证-2026-11-16/verify.py':
        '69d80ba52b1a107c609438a2c2fe7eb14ef5fea8750656122e1456335e491f94',
    '4-打分细则/请求侧跨运行重建验证-2026-11-16/test_verify.py':
        '9e7ce72971f678d28887a8e3eaa41959fd3b248e09bb9e8c88d4dfb876a13d89',
    '4-打分细则/请求侧跨运行重建验证-2026-11-16/EXECUTION-RECORD.md':
        '3b3b25666f42e1ae20a7de6fc71d193afcf0fba3d1284b69f66e4dececff67fe',
    '4-打分细则/请求侧跨运行重建验证-2026-11-16/evidence.json':
        '057c048171e2ae57d50d9717c50a50445588e074bec14fde1a656ccee52fcd03',
    '4-打分细则/请求侧跨运行重建验证-2026-11-16/result.json':
        '0bd2fa8628a411966fc729af7817ccedd7de4ea0f86de3380e85ca2ba6836b18',
    '4-打分细则/请求侧跨运行预注册-2026-11-16/README.md':
        'fb9a8c4a712566f080b3ecd0453a20c2a844362921a6f4eade7619c7c5a7478e',
    '4-打分细则/DSH请求侧最小捕获-2026-11-16/README.md':
        'a26c7ec7df5dc052ce708434a3cbfa2b50deca2745effa1b91a5877f279c04e7',
    '4-打分细则/DSH请求侧最小捕获-2026-11-16/result.json':
        '3de57557fe7f3c74e6abc041e5181fc415595299b9678ed59d271f8abe596357',
}
README_REL = '4-打分细则/请求侧跨运行重建扩展-2026-11-16/README.md'


class Invalid(ValueError):
    pass


def require(cond, msg):
    if not cond:
        raise Invalid(msg)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def no_duplicate_keys(pairs):
    obj = {}
    for k, v in pairs:
        if k in obj:
            raise Invalid('duplicate key %r' % (k,))
        obj[k] = v
    return obj


def load_json(raw, label):
    def nonfinite(_):
        raise Invalid('non-finite number in %s' % label)
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=no_duplicate_keys,
                          parse_constant=nonfinite)
    except UnicodeDecodeError:
        raise Invalid('%s not utf-8' % label)


def pinned(root, relative, expected):
    path = root / relative
    try:
        raw = path.read_bytes()
    except OSError:
        raise Invalid('missing pinned file %s' % relative)
    require(sha(raw) == expected, 'pinned file changed: %s' % relative)
    return raw


def exclusive(path, raw):
    path = pathlib.Path(path)
    require(not path.exists(), 'refusing to overwrite existing %s' % path)
    require('..' not in path.parts, 'path escape refused')
    parent = path.parent
    require(parent.exists(), 'output parent missing')
    with open(path, 'xb') as handle:
        handle.write(raw)


def descriptor(message):
    content = message.get('content')
    kind = 'null' if content is None else type(content).__name__
    length = 0 if content is None else len(content)
    return {'role': message.get('role'), 'content_kind': kind, 'content_len': length}


def leaves(obj, path=()):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from leaves(value, path + (key,))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from leaves(value, path + (index,))
    else:
        yield path, obj


def canon(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':')).encode('utf-8')


def normalize_ids(obj):
    text = json.dumps(obj, ensure_ascii=False)
    return json.loads(re.sub(r'call_[0-9a-f]{24}', '<CALL_ID>', text))


def load_run(archive_base, label):
    root = archive_base / RUN_RELS[label]
    shas, statuses, sizes = [], [], []
    for name in REQ_NAMES:
        raw = (root / 'requests' / (name + '.request.bin')).read_bytes()
        meta_raw = (root / 'responses' / (name + '.response.bin.meta.json')).read_bytes()
        meta = load_json(meta_raw, label + '/' + name + ' meta')
        require(isinstance(meta, dict), 'meta not object')
        require(meta.get('upstream_status') == 200, 'upstream status not 200')
        require(meta.get('request_body_sha256') == sha(raw), 'meta sha mismatch')
        shas.append(sha(raw))
        statuses.append(200)
        sizes.append(len(raw))
    bodies = [json.loads((root / 'requests' / (n + '.request.bin')).read_bytes().decode('utf-8'))
              for n in REQ_NAMES]
    return {'req_sha': shas, 'statuses': statuses, 'req_bytes': sizes, 'bodies': bodies}


def pair_record(a, b, runs):
    ra, rb = runs[a], runs[b]
    diff_paths = []
    da = dict(leaves(ra['bodies'][2]))
    db = dict(leaves(rb['bodies'][2]))
    all_call_id = True
    for path in sorted(set(da) | set(db), key=lambda p: tuple(map(str, p))):
        va, vb = da.get(path, '<ABSENT>'), db.get(path, '<ABSENT>')
        if va == vb:
            continue
        ok_a = isinstance(va, str) and bool(CALL_ID.match(va))
        ok_b = isinstance(vb, str) and bool(CALL_ID.match(vb))
        if not (ok_a and ok_b):
            all_call_id = False
        diff_paths.append(path)
    d_equal = canon(normalize_ids(ra['bodies'][2])) == canon(normalize_ids(rb['bodies'][2]))
    msgs_a = ra['bodies'][0]['messages']
    msgs_b = ra['bodies'][2]['messages']
    prefix = len(msgs_b) >= len(msgs_a) and msgs_b[:len(msgs_a)] == msgs_a
    appended = [descriptor(m) for m in msgs_b[len(msgs_a):]]
    req1_eq = ra['req_sha'][0] == rb['req_sha'][0]
    req2_eq = ra['req_sha'][1] == rb['req_sha'][1]
    stable = req1_eq and req2_eq and all_call_id and d_equal
    return {
        'pair': a + '-' + b,
        'req1_byte_equal': req1_eq,
        'req2_byte_equal': req2_eq,
        'req3_byte_equal': ra['req_sha'][2] == rb['req_sha'][2],
        'req3_diff_leaves': len(diff_paths),
        'req3_diff_all_call_id': all_call_id,
        'd_class_id_normalized_canonical_equal': d_equal,
        'req1_prefix_of_req3': prefix,
        'appended_descriptors': appended,
        'delta_bytes': ra['req_bytes'][2] - ra['req_bytes'][0],
        'req3_sha': {a: ra['req_sha'][2], b: rb['req_sha'][2]},
        'verdict': 'identity_assembly_stable' if stable else 'UNSTABLE',
    }


def build(archive_base):
    runs = {label: load_run(archive_base, label) for label in RUN_LABELS}
    pairs = []
    for i, a in enumerate(RUN_LABELS):
        for b in RUN_LABELS[i + 1:]:
            pairs.append(pair_record(a, b, runs))
    public_runs = {}
    for label in RUN_LABELS:
        public_runs[label] = {
            'req_sha': runs[label]['req_sha'],
            'statuses': runs[label]['statuses'],
            'req_bytes': runs[label]['req_bytes'],
        }
    return {
        'schema': SCHEMA_EVIDENCE,
        'baseline': BASELINE,
        'runs': public_runs,
        'pairs': pairs,
        'aggregate': {
            'total_pairs': len(pairs),
            'req1_identical_pairs': sum(1 for p in pairs if p['req1_byte_equal']),
            'req2_identical_pairs': sum(1 for p in pairs if p['req2_byte_equal']),
            'd_residual_zero_pairs': sum(1 for p in pairs if p['d_class_id_normalized_canonical_equal']),
            'stable_pairs': sum(1 for p in pairs if p['verdict'] == 'identity_assembly_stable'),
        },
    }


def validate_public(evidence, root, readme_sha):
    require(isinstance(evidence, dict), 'evidence not object')
    require(evidence.get('schema') == SCHEMA_EVIDENCE, 'schema mismatch')
    require(evidence.get('baseline') == BASELINE, 'baseline mismatch')
    require(evidence.get('readme_sha256') == readme_sha, 'own readme record mismatch')
    for rel, expected in PINS.items():
        pinned(root, rel, expected)
    runs = evidence.get('runs')
    require(isinstance(runs, dict) and sorted(runs) == sorted(RUN_LABELS), 'runs labels mismatch')
    req1_shas, req3_shas = set(), set()
    for label in RUN_LABELS:
        slot = runs[label]
        require(sorted(slot) == ['req_bytes', 'req_sha', 'statuses'], 'run keys mismatch')
        require(len(slot['req_sha']) == 3 and len(slot['statuses']) == 3, 'run arrays length')
        require(all(code == 200 for code in slot['statuses']), 'non-200 status in evidence')
        req1_shas.add(slot['req_sha'][0])
        req3_shas.add(slot['req_sha'][2])
    require(len(req1_shas) == 1, 'req1 not identical across runs')
    require(len(req3_shas) == len(RUN_LABELS), 'req3 shas not all distinct')
    pairs = evidence.get('pairs')
    require(isinstance(pairs, list) and len(pairs) == 10, 'pairs length')
    expected_pairs = set()
    for i, a in enumerate(RUN_LABELS):
        for b in RUN_LABELS[i + 1:]:
            expected_pairs.add(a + '-' + b)
    seen = set()
    for row in pairs:
        require(isinstance(row, dict) and row['pair'] in expected_pairs, 'unknown pair')
        seen.add(row['pair'])
        require(row['req1_byte_equal'] is True and row['req2_byte_equal'] is True, 'pair not stable')
        require(row['req3_byte_equal'] is False, 'req3 unexpectedly equal')
        require(row['req3_diff_leaves'] == 4, 'diff leaf count not 4')
        require(row['req3_diff_all_call_id'] is True, 'non-call_id diff leaf')
        require(row['d_class_id_normalized_canonical_equal'] is True, 'd-class residual')
        require(row['req1_prefix_of_req3'] is True, 'prefix identity broken')
        require(row['delta_bytes'] == 1016, 'delta not 1016')
        require(row['verdict'] == 'identity_assembly_stable', 'verdict not stable')
        require(len(row['appended_descriptors']) == 3, 'appended count not 3')
        require(row['appended_descriptors'][0]['content_kind'] == 'null', 'appended[0] not null-content')
        require(row['appended_descriptors'][1]['role'] == 'tool', 'appended[1] not tool')
        require(row['appended_descriptors'][2]['role'] == 'tool', 'appended[2] not tool')
    require(seen == expected_pairs, 'pair coverage incomplete')
    aggregate = evidence.get('aggregate')
    require(isinstance(aggregate, dict), 'aggregate missing')
    require(aggregate.get('total_pairs') == 10, 'total pairs')
    require(aggregate.get('req1_identical_pairs') == 10, 'req1 aggregate')
    require(aggregate.get('req2_identical_pairs') == 10, 'req2 aggregate')
    require(aggregate.get('d_residual_zero_pairs') == 10, 'd-class aggregate')
    require(aggregate.get('stable_pairs') == 10, 'stable aggregate')
    extra = set(evidence) - {'schema', 'readme_sha256', 'baseline', 'runs', 'pairs', 'aggregate'}
    require(not extra, 'unexpected evidence keys %r' % (sorted(extra),))


def result_for(evidence, evidence_sha, readme_sha):
    aggregate = evidence['aggregate']
    return {
        'schema': SCHEMA_RESULT,
        'evidence_sha256': evidence_sha,
        'readme_sha256': readme_sha,
        'baseline': evidence['baseline'],
        'primary': {
            'assembly_stable_pairs': '%d/%d' % (aggregate['stable_pairs'], aggregate['total_pairs']),
            'req1_identical_pairs': '%d/%d' % (aggregate['req1_identical_pairs'], aggregate['total_pairs']),
            'req2_identical_pairs': '%d/%d' % (aggregate['req2_identical_pairs'], aggregate['total_pairs']),
            'd_residual_zero_pairs': '%d/%d' % (aggregate['d_residual_zero_pairs'], aggregate['total_pairs']),
        },
        'runs': {label: {'req_sha': evidence['runs'][label]['req_sha'],
                         'statuses': evidence['runs'][label]['statuses']}
                 for label in RUN_LABELS},
        'limits': [
            'single task / single model / same-day / same workspace and adapter chain',
            'bytes are not tokens or cost; response bodies not in scope',
            'public replay re-checks seals, coverage and published arithmetic only',
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description='req-side extension verifier')
    parser.add_argument('--root', required=True)
    parser.add_argument('--archive-base')
    parser.add_argument('--build-evidence')
    parser.add_argument('--evidence')
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    root = pathlib.Path(args.root)
    repo = pathlib.Path(__file__).resolve().parents[2]
    readme_sha = sha((repo / README_REL).read_bytes())
    try:
        if args.build_evidence:
            require(args.archive_base, '--build-evidence needs --archive-base')
            require(args.evidence is None, '--build-evidence and --evidence are exclusive')
            evidence = build(pathlib.Path(args.archive_base))
            evidence['readme_sha256'] = readme_sha
            validate_public(evidence, root, readme_sha)
            evidence_path = pathlib.Path(args.build_evidence)
            require(not evidence_path.exists(), 'evidence path exists')
            evidence_raw = (json.dumps(evidence, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
            exclusive(evidence_path, evidence_raw)
        else:
            require(args.evidence, 'public replay needs --evidence')
            evidence_raw = pathlib.Path(args.evidence).read_bytes()
            evidence = load_json(evidence_raw, 'evidence')
            validate_public(evidence, root, readme_sha)
        result = result_for(evidence, sha(evidence_raw), readme_sha)
        exclusive(args.output, (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
        primary = result['primary']
        print('built' if args.build_evidence else 'replayed', primary['assembly_stable_pairs'],
              'stable pairs; d-residual', primary['d_residual_zero_pairs'])
        return 0
    except Invalid as error:
        print('error: %s' % error, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
