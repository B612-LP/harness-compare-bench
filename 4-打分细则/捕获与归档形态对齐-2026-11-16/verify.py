#!/usr/bin/env python3
"""Derived alignment between the single captured run and the archived slots.

Reads ONLY public pinned files (identity evidence, capture evidence, capture
result, this package's README), computes frozen descriptive endpoints, and
writes an evidence/result pair or validates an existing pair byte-for-byte
against recomputation. No private archive, product, or network access. No
message or event content is published; only byte counts, type names, and
verdicts already derivable from public evidence.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASELINE = '61614b54801800d29aa70eaf8d725ce89285ea87'
ID_RELPATH = '4-打分细则/输入事件等长与同一性-2026-11-16/evidence.json'
ID_SHA = 'cc9089b18ca42f0357003d169ef9e01134e10e4b7881d66247f00d8bb8cb86b0'
CAP_RELPATH = '4-打分细则/DSH请求侧最小捕获-2026-11-16/evidence.json'
CAP_SHA = 'f3e4fab3cd0d742ce4840f1e3b57423b62094c4cd8b7a939b3b347658b4aeaa1'
CAPRES_RELPATH = '4-打分细则/DSH请求侧最小捕获-2026-11-16/result.json'
CAPRES_SHA = '3de57557fe7f3c74e6abc041e5181fc415595299b9678ed59d271f8abe596357'
SELF_RELPATH = '4-打分细则/捕获与归档形态对齐-2026-11-16/README.md'
SAME_TASK = 'dsh__exercism-py-6'
SYS_TYPE = 'system/message'
USR_TYPE = 'user/message'
EXPECTED_SLOTS = 15
SCHEMA = 'capture-archived-alignment-evidence-v1'
LIMITS = [
    'layer mismatch: archived side is harness I-event bytes; capture side is provider wire message bytes; only system/user subsets are aligned',
    'model/provider/task packaging differ between the captured run and the archived batch (capture package README known-differences); P2 out-of-range is a finding, not a defect',
    'n=1 captured run; verdicts describe this data only, no representativeness, causal, or universality claim',
    'bytes are not tokens or cost; provider cache semantics are not authenticated',
    'P5 pairing of the two tool results to the two files is not authenticated from public data; only growth factors are reported',
    'public files are re-read from the repo pins; raw and public modes share the same inputs and must agree byte-for-byte',
]


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


def _finite_float(text):
    value = float(text)
    if value != value or value == float('inf') or value == float('-inf'):
        raise ValueError('non-finite float: %s' % text)
    return value


def loads(raw):
    return json.loads(raw.decode('utf-8'),
                      object_pairs_hook=no_duplicate_keys,
                      parse_float=_finite_float,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('non-finite: %s' % value)))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pinned(root, relative, expected):
    raw = (Path(root) / relative).read_bytes()
    require(sha(raw) == expected, 'pin mismatch: %s' % relative)
    return loads(raw)


def integer(value, minimum=0):
    require(isinstance(value, int) and not isinstance(value, bool) and value >= minimum,
            'expected non-negative int')
    return value


def slot_row(entry):
    name = entry['slot']
    require(isinstance(name, str) and name.startswith('dsh__'), 'bad slot name')
    sequence = entry['prior_metrics']['i_sequence']
    L0 = entry['layers']['L0']['event_bytes']
    require(len(sequence) == len(L0), 'sequence/bytes length mismatch: %s' % name)
    sysb = usrb = 0
    for kind, size in zip(sequence, L0):
        require(isinstance(kind, str), 'bad type')
        size = integer(size)
        if kind == SYS_TYPE:
            sysb += size
        elif kind == USR_TYPE:
            usrb += size
    total = integer(entry['prior_metrics']['i_bytes'])
    require(sysb + usrb <= total, 'aligned subset exceeds i_bytes: %s' % name)
    return {'slot': name, 'system_bytes': sysb, 'user_bytes': usrb,
            'i_bytes_total': total, 'harness_only_bytes': total - sysb - usrb,
            'n_events': len(sequence)}


def capture_values(capture_evidence):
    requests = capture_evidence['capture']['requests']
    first = [r for r in requests if r.get('seq') == 1]
    require(len(first) == 1, 'expected exactly one seq==1 request')
    first = first[0]
    require(first.get('kind') == 'loop', 'seq1 is not a loop request')
    sysb = usrb = 0
    for role, kind, size in first['roles']:
        require(isinstance(role, str) and isinstance(kind, str), 'bad role tuple')
        size = integer(size)
        if role == 'system':
            sysb += size
        elif role == 'user':
            usrb += size
    total = integer(first['request_bytes'])
    require(sysb + usrb <= total, 'aligned subset exceeds request_bytes')
    appended = capture_evidence['prefix_identity']['req3_appended_roles']
    tools = [integer(size) for role, kind, size in appended if role == 'tool']
    require(len(tools) == 2, 'expected two appended tool results')
    workspace = capture_evidence.get('workspace')
    require(isinstance(workspace, dict) and
            set(workspace) == {'TASK.md', 'inputs/exercises/dominoes/dominoes.py'},
            'unexpected workspace file set')
    files = {name: integer(entry['bytes']) for name, entry in workspace.items()}
    return {'system_bytes': sysb, 'user_bytes': usrb, 'request_bytes': total,
            'tool_result_bytes': tools, 'workspace_file_bytes': files}


def verdict(value, values):
    low, high = min(values), max(values)
    below = sum(1 for v in values if v < value)
    return {'verdict': 'in_range' if low <= value <= high else 'out_of_range',
            'archived_min': low, 'archived_max': high,
            'percentile_below': round(below / len(values) * 100.0, 1)}


def endpoints(rows, cap):
    users = [r['user_bytes'] for r in rows]
    systems = [r['system_bytes'] for r in rows]
    sums = [r['system_bytes'] + r['user_bytes'] for r in rows]
    ordered = sorted(sums)
    median = ordered[len(ordered) // 2] if len(ordered) % 2 else (ordered[len(ordered) // 2 - 1] + ordered[len(ordered) // 2]) / 2
    p1 = verdict(cap['user_bytes'], users)
    p2 = verdict(cap['system_bytes'], systems)
    aligned = cap['system_bytes'] + cap['user_bytes']
    p3 = {'capture_aligned_bytes': aligned, 'archived_median_aligned_bytes': median,
          'ratio_vs_median': round(aligned / median, 4)}
    p3.update(verdict(aligned, sums))
    same = [r['user_bytes'] for r in rows if r['slot'].startswith(SAME_TASK)]
    require(len(same) == 3, 'same-task slots missing')
    p4 = {'same_task': SAME_TASK, 'same_task_user_bytes': same,
          'capture_user_bytes': cap['user_bytes'],
          'ratio_capture_vs_same_task_median': round(cap['user_bytes'] / sorted(same)[1], 4)}
    p5 = {'workspace_file_bytes': cap['workspace_file_bytes'],
          'tool_result_bytes': cap['tool_result_bytes'],
          'growth_factors_pairing_unverified':
              [round(t / f, 3) for t, f in zip(sorted(cap['tool_result_bytes'], reverse=True),
                                               sorted(cap['workspace_file_bytes'].values(), reverse=True))]}
    return {'p1_capture_user_vs_archived': p1, 'p2_capture_system_vs_archived': p2,
            'p3_aligned_sum_vs_archived': p3, 'p4_same_task_user_gap': p4, 'p5_tool_result_growth': p5}


def build(root):
    identity = pinned(root, ID_RELPATH, ID_SHA)
    capture = pinned(root, CAP_RELPATH, CAP_SHA)
    pinned(root, CAPRES_RELPATH, CAPRES_SHA)
    slots = identity['slots']
    require(len(slots) == EXPECTED_SLOTS, 'expected %d slots' % EXPECTED_SLOTS)
    rows = [slot_row(entry) for entry in slots]
    require(len({r['slot'] for r in rows}) == EXPECTED_SLOTS, 'duplicate slot')
    cap = capture_values(capture)
    evidence = {'schema': SCHEMA, 'baseline_commit': BASELINE, 'evidence_sha256': None,
                'sources': {ID_RELPATH: ID_SHA, CAP_RELPATH: CAP_SHA,
                            CAPRES_RELPATH: CAPRES_SHA, SELF_RELPATH: sha((Path(root) / SELF_RELPATH).read_bytes())},
                'archived_slots': rows, 'capture_first_loop_request': cap,
                'endpoints': endpoints(rows, cap), 'limits': LIMITS}
    result = {'schema': 'capture-archived-alignment-result-v1', 'baseline_commit': BASELINE,
              'evidence_sha256': None, 'endpoints': evidence['endpoints'],
              'verdict_summary': 'descriptive only: see limits; no representativeness or causal claim',
              'limits': LIMITS}
    return evidence, result


def validate_stored(root, evidence, result):
    fresh, fresh_result = build(root)
    require(evidence == fresh, 'stored evidence differs from recomputation')
    stored_core = dict(result)
    fresh_core = dict(fresh_result)
    stored_binding = stored_core.pop('evidence_sha256', None)
    fresh_core.pop('evidence_sha256', None)
    require(stored_core == fresh_core, 'stored result differs from recomputation')
    require(isinstance(stored_binding, str) and len(stored_binding) == 64,
            'stored result lacks evidence binding')
    require(stored_binding == sha((HERE / 'evidence.json').read_bytes()),
            'result does not bind packaged evidence bytes')


def document(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def exclusive(path, raw, forbidden_roots=()):
    path = Path(path)
    require(not path.exists(), 'output exists: %s' % path)
    resolved = path.resolve()
    for root in forbidden_roots:
        base = Path(root).resolve()
        require(not (base == resolved or base in resolved.parents),
                'output inside protected input root denied')
    with path.open('xb') as handle:
        handle.write(raw)


def dump(path, value, forbidden_roots=()):
    exclusive(Path(path), document(value), forbidden_roots)


def safe_join(root, relative):
    base = Path(root).resolve()
    target = (base / relative).resolve()
    require(base == target or base in target.parents, 'path escapes root: %s' % relative)
    return target


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=HERE.parents[1])
    parser.add_argument('--build-evidence', type=Path)
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        root = Path(args.root).resolve()
        if args.build_evidence:
            evidence, result = build(root)
            evidence['evidence_sha256'] = None
            dump(args.build_evidence, evidence, forbidden_roots=(root,))
            blob = document(evidence)
            result['evidence_sha256'] = sha(blob)
            dump(args.output, result)
            print('built: slots=%d capture_system=%d capture_user=%d p1=%s p2=%s' % (
                len(evidence['archived_slots']),
                evidence['capture_first_loop_request']['system_bytes'],
                evidence['capture_first_loop_request']['user_bytes'],
                result['endpoints']['p1_capture_user_vs_archived']['verdict'],
                result['endpoints']['p2_capture_system_vs_archived']['verdict']))
            return 0
        stored_pair = safe_join(HERE, 'evidence.json')
        evidence = loads(stored_pair.read_bytes())
        stored_result = loads(safe_join(HERE, 'result.json').read_bytes())
        validate_stored(root, evidence, stored_result)
        result = dict(stored_result)
        result['evidence_sha256'] = sha(stored_pair.read_bytes())
        dump(args.output, result)
        print('validated packaged evidence/result; endpoints reproduced')
        return 0
    except (ValueError, OSError, KeyError) as error:
        print('input or output failure', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
