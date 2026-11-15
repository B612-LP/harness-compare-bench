#!/usr/bin/env python3
"""R3 instability source decomposition (preregistered 2026-11-16).

Decomposes the within-group R3 (reconstructed input payload bytes) spread of the
15 archived Codex slots (5 groups x n=3, batch r1109-mech-n3) into
model-generated (M*) versus environment/task (E) families, per event payload
type. Pure post-hoc arithmetic over archived evidence: no new runs, no network,
no model/product CLI subprocess calls, no gate changes.

Reuse: the loading/selection/binding logic is imported from the frozen v1.1
package (机制重复口径澄清-2026-11-12/verify.py) after SHA-pinning it; nothing is
re-implemented behind its back. Raw archived originals are read only through
SHA-256 identities already pinned in v1.1 evidence.json. Fail-closed: unknown
model-generation ambiguity stops before any deliverable is written.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = '4-打分细则/R3不稳定来源分解-2026-11-16'
V1_HERE = '4-打分细则/机制重复口径澄清-2026-11-12'
BATCH = '3-表现现场/r1109-mech-n3'
PREREG_SHA256 = 'c4546f35114af3eebcc1a5ddb73521774dc4063b7606d6a123b232f554e6ea00'
V1_VERIFY_SHA256 = '045475f5dd05efdf56e102ceb8b2eb4e98f455d818b80a7b0af74fca6f0c0d1d'
V1_RESULT_SHA256 = 'abb3a4fc09f1210b30021f7896551b7d0b34502cabbfe08ad0777b87dddc4433'
V1_BASELINE = '38b2e13f63c5aeacb58094d2e977980ab12e8041'
CASES = ('bird-ca-schools-15', 'dabstep-payments-10', 'exercism-py-6', 'lcb-recent-hard-4', 'tb-cargo-plan')
REPS = (1, 2, 3)
MESSAGE_ROLES = frozenset(('assistant', 'developer', 'user', 'system'))
MODEL_GENERATED_PAYLOAD_TYPES = frozenset(('reasoning', 'function_call'))
FAMILIES = ('m_star', 'environment')
PAIR_INDEXES = ((0, 1), (0, 2), (1, 2))


class Invalid(ValueError):
    pass


class ClassifierStop(Invalid):
    """Model-generation ambiguity (e.g. message payload without recognizable role)."""


def require(condition, message):
    if not condition:
        raise Invalid(message)


def resolve_head(root):
    """Current HEAD commit, resolved from .git files only (no subprocess)."""
    git = root / '.git'
    if git.is_file():
        text = git.read_text(encoding='utf-8').strip()
        require(text.startswith('gitdir:'), 'unsupported .git indirection')
        git = Path(text.split(':', 1)[1].strip())
        if not git.is_absolute():
            git = (root / git).resolve()
    require(git.is_dir(), 'missing .git directory')
    head = (git / 'HEAD').read_text(encoding='utf-8').strip()
    value = None
    if head.startswith('ref: '):
        ref = head[5:].strip()
        direct = git / ref
        if direct.is_file():
            value = direct.read_text(encoding='utf-8').strip()
        else:
            for line in (git / 'packed-refs').read_text(encoding='utf-8').splitlines():
                if line.endswith(' ' + ref):
                    value = line.split(' ', 1)[0].strip()
                    break
    else:
        value = head
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{40}', value or '') is not None,
            'cannot resolve current HEAD commit')
    return value


def load_v1_module(root):
    """Import the frozen v1.1 verify.py after SHA-pinning its exact bytes."""
    path = root / V1_HERE / 'verify.py'
    raw = path.read_bytes()
    require(sha_hex(raw) == V1_VERIFY_SHA256, 'v1.1 verify.py SHA mismatch')
    spec = importlib.util.spec_from_file_location('clarify_verify_v1_1', path)
    require(spec is not None and spec.loader is not None, 'cannot import v1.1 verify.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(module.BATCH == BATCH and module.CASES == CASES and module.EVIDENCE_SHA256 is not None,
            'v1.1 module constants drifted')
    return module


def load_trace(archive_root, identity):
    """Load one archived original Codex rollout, SHA-verified against its pinned identity."""
    relative = identity['source_relative_to_archive']
    require(isinstance(relative, str) and relative, 'missing trace archive path')
    path = Path(relative)
    require(not path.is_absolute() and '..' not in path.parts, 'unsafe trace path')
    absolute = (archive_root / path).resolve()
    require(archive_root == absolute or archive_root in absolute.parents, 'trace escapes archive root')
    raw = absolute.read_bytes()
    require(sha_hex(raw) == digest_hex(identity['sha256']), 'archived original SHA mismatch: ' + relative)
    events = []
    for line in raw.decode('utf-8').splitlines():
        require(line.strip() != '', 'blank line inside trace: ' + relative)
        try:
            events.append(json.loads(line))
        except ValueError as error:
            raise Invalid('unparsable trace line in ' + relative + ': ' + str(error)) from error
    require(events and all(isinstance(e, dict) and isinstance(e.get('type'), str) for e in events),
            'bad trace event schema: ' + relative)
    return events


def classify_payload(payload):
    """Frozen M*/E classification of one response_item payload.

    M*: assistant message, reasoning, function_call. E: developer/user/system
    message, function_call_output, turn_context, and every other non-model
    payload (catch-all, allowed by the prereg). Ambiguity about whether
    something is model-generated (e.g. message without role) stops the run.
    Returns (family, payload_type, message_role_or_None).
    """
    require(isinstance(payload, dict), 'payload must be an object')
    ptype = payload.get('type')
    require(isinstance(ptype, str) and ptype, 'missing payload.type')
    if ptype == 'message':
        role = payload.get('role')
        if not isinstance(role, str) or role not in MESSAGE_ROLES:
            raise ClassifierStop('message payload without recognizable role; refusing to classify')
        return ('m_star' if role == 'assistant' else 'environment'), ptype, role
    if ptype in MODEL_GENERATED_PAYLOAD_TYPES:
        return 'm_star', ptype, None
    return 'environment', ptype, None


def decompose_slot(raw_events, projection_rows):
    """Per-event projection cross-check plus exact M*/E byte decomposition of one slot."""
    recomputed = V.project_events(raw_events, 'codex')
    require(recomputed == projection_rows,
            'per-event projection mismatch against v1.1 evidence.json')
    per_type = {}
    family_bytes = {family: 0 for family in FAMILIES}
    message_by_role = {}
    response_items = 0
    for event in raw_events:
        if event['type'] != 'response_item':
            continue
        response_items += 1
        payload = event['payload']
        family, ptype, role = classify_payload(payload)
        size = len(V.canon(payload))
        per_type[ptype] = per_type.get(ptype, 0) + size
        family_bytes[family] += size
        if role is not None:
            message_by_role[role] = message_by_role.get(role, 0) + size
    r3_total = sum(row[3] for row in projection_rows if row[0] == 'response_item')
    require(sum(per_type.values()) == r3_total, 'per-type bytes do not sum to R3 total')
    require(sum(family_bytes.values()) == r3_total, 'family partition does not sum to R3 total')
    require(family_bytes['m_star'] + family_bytes['environment'] == r3_total,
            'M* and E are not an exact partition of R3')
    return {'r3_total_bytes': r3_total, 'response_item_count': response_items,
            'event_count': len(raw_events), 'per_type_bytes': per_type,
            'family_bytes': family_bytes, 'message_by_role_bytes': message_by_role}


def signed_decomposition(bytes_max_slot, bytes_min_slot):
    """Exact per-key signed contribution (max slot minus min slot) over the key union."""
    keys = sorted(set(bytes_max_slot) | set(bytes_min_slot))
    return {key: bytes_max_slot.get(key, 0) - bytes_min_slot.get(key, 0) for key in keys}


def dominance_flag(net, delta):
    require(type(net) is int and type(delta) is int and delta > 0, 'dominance needs delta > 0')
    return abs(net) * 2 > delta


def family_view(family_nets, delta):
    require(sum(family_nets.values()) == delta, 'family nets do not sum to delta')
    return {family: {'net_contribution': family_nets[family],
                     'share': family_nets[family] / delta,
                     'dominant': dominance_flag(family_nets[family], delta)}
            for family in FAMILIES}


def pair_entry(reps, indexes):
    first, second = indexes
    high, low = (reps[first], reps[second]) if reps[first]['r3_total_bytes'] >= reps[second]['r3_total_bytes'] \
        else (reps[second], reps[first])
    delta = high['r3_total_bytes'] - low['r3_total_bytes']
    per_type = signed_decomposition(high['per_type_bytes'], low['per_type_bytes'])
    require(sum(per_type.values()) == delta, 'pairwise decomposition not exact')
    nets = {family: high['family_bytes'][family] - low['family_bytes'][family] for family in FAMILIES}
    require(sum(nets.values()) == delta, 'pairwise family nets not exact')
    families = {family: {'net_contribution': nets[family],
                         'dominant': dominance_flag(nets[family], delta) if delta > 0 else False,
                         'share': nets[family] / delta if delta > 0 else None}
                for family in FAMILIES}
    return {'slots': [high['slot'], low['slot']], 'reps': [high['rep'], low['rep']],
            'orientation': 'max_minus_min', 'delta': delta,
            'per_type_signed_contribution': per_type, 'families': families}


def select_branch(m_star_dominant_groups, environment_dominant_groups, groups_total):
    """Frozen refutation-branch order: M* >=4/5 first, then E somewhere, else mixed."""
    require(groups_total == 5, 'branch selection expects 5 groups')
    if len(m_star_dominant_groups) >= 4:
        return 'M_STAR_DOMINANT_IN_4_OF_5_GROUPS'
    if environment_dominant_groups:
        return 'E_DOMINANT_IN_SOME_GROUP'
    return 'MIXED_NO_SINGLE_DOMINANT_FAMILY'


def analyze(root, archive_root=None, v1_result=None):
    """Full recomputation. v1_result may be injected by tests to exercise the
    hard-equal branch directly; the default path SHA-pins the v1.1 result.json."""
    root = Path(root).resolve()
    prereg_raw = (root / HERE / 'README.md').read_bytes()
    require(sha_hex(prereg_raw) == PREREG_SHA256,
            'prereg README SHA mismatch: ' + HERE + '/README.md')
    baseline = resolve_head(root)
    global V
    V = load_v1_module(root)
    result_v1 = V.analyze(root)
    require(result_v1['schema'] == 'mechanism-repetition-clarification-v1.1', 'unexpected v1.1 result')
    evidence_raw = (root / V1_HERE / 'evidence.json').read_bytes()
    require(sha_hex(evidence_raw) == V.EVIDENCE_SHA256, 'v1.1 evidence.json SHA mismatch')
    evidence = json.loads(evidence_raw)
    if v1_result is None:
        result_raw = (root / V1_HERE / 'result.json').read_bytes()
        require(sha_hex(result_raw) == V1_RESULT_SHA256, 'v1.1 result.json SHA mismatch')
        v1_result = json.loads(result_raw)
    require(v1_result.get('schema') == 'mechanism-repetition-clarification-v1.1', 'bad v1.1 result schema')
    if archive_root is None:
        archive_root = root / BATCH
    archive_root = Path(archive_root).resolve()
    require(archive_root.is_dir(), 'archived-original root not found (pass --archive-root)')
    codex_rows = [row for row in evidence['slots'] if row['slot'].startswith('codex__')]
    require(len(codex_rows) == 15 and all(row['slot'].split('__')[1] in CASES for row in codex_rows),
            'codex slot set changed')
    v1_by_slot = {row['slot']: row for row in result_v1['slots'] if row['arm'] == 'codex'}
    require(len(v1_by_slot) == 15, 'v1.1 result codex slot count changed')
    v1_file_by_slot = {row['slot']: row for row in v1_result['slots'] if row['arm'] == 'codex'}
    require(len(v1_file_by_slot) == 15, 'v1.1 result.json codex slot count changed')
    require(sorted(v1_file_by_slot) == sorted(v1_by_slot), 'v1.1 replay and result.json slot sets differ')
    for slot, file_slot in v1_file_by_slot.items():
        require(file_slot['input_bytes'] == v1_by_slot[slot]['input_bytes'],
                'v1.1 result.json disagrees with its own replay: ' + slot)
    slot_outputs = []
    for row in codex_rows:
        slot = row['slot']
        v1_slot = v1_by_slot[slot]
        raw_events = load_trace(archive_root, row['identity'])
        decomposition = decompose_slot(raw_events, row['events'])
        require(decomposition['event_count'] == v1_slot['event_count'], 'event count mismatch: ' + slot)
        require(decomposition['r3_total_bytes'] == v1_file_by_slot[slot]['input_bytes'],
                'R3 hard-equal mismatch vs v1.1 result.json: ' + slot)
        require(decomposition['r3_total_bytes'] == v1_slot['input_bytes'],
                'R3 hard-equal mismatch vs v1.1 replay: ' + slot)
        controls = V.select_controls(raw_events)
        require(controls == row['controls'], 'stable-core controls mismatch vs v1.1 evidence: ' + slot)
        case, rep = slot.split('__')[1], int(slot.split('__')[2][1:])
        slot_outputs.append({'slot': slot, 'case': case, 'rep': rep, **decomposition,
                             'closed_turns': v1_slot['closed_turns'],
                             'aggregate_path': v1_slot['aggregate_path'],
                             'trace_sha256': row['identity']['sha256'],
                             'trace_file': row['identity']['file'],
                             'trace_archive_relative_path': row['identity']['source_relative_to_archive'],
                             'leading_role_content_sha256': controls['leading_role_content_sha256'],
                             'task_content_sha256': controls['task_content_sha256']})
    require(sorted(s['slot'] for s in slot_outputs) == sorted(v1_by_slot), 'slot coverage mismatch')
    groups = []
    for case in CASES:
        reps = sorted([s for s in slot_outputs if s['case'] == case], key=lambda s: s['rep'])
        require([s['rep'] for s in reps] == list(REPS), 'group repetitions changed: ' + case)
        totals = [s['r3_total_bytes'] for s in reps]
        max_index = totals.index(max(totals))
        min_index = totals.index(min(totals))
        require(totals.count(max(totals)) == 1 and totals.count(min(totals)) == 1,
                'ambiguous max or min slot in group ' + case)
        require(max(totals) - min(totals) > 0, 'nonpositive delta in group ' + case)
        high, low = reps[max_index], reps[min_index]
        delta = max(totals) - min(totals)
        per_type = signed_decomposition(high['per_type_bytes'], low['per_type_bytes'])
        require(sum(per_type.values()) == delta, 'signed per-type decomposition not exact: ' + case)
        nets = {family: high['family_bytes'][family] - low['family_bytes'][family] for family in FAMILIES}
        groups.append({'group': case, 'arm': 'codex', 'slots': [s['slot'] for s in reps],
                       'r3_totals': totals, 'max_slot': high['slot'], 'min_slot': low['slot'],
                       'delta': delta, 'per_type_sums_to_delta': True,
                       'per_type': {key: {'max_slot_bytes': high['per_type_bytes'].get(key, 0),
                                          'min_slot_bytes': low['per_type_bytes'].get(key, 0),
                                          'signed_contribution': value} for key, value in per_type.items()},
                       'families': family_view(nets, delta),
                       'pairwise': [pair_entry(reps, indexes) for indexes in PAIR_INDEXES],
                       'stable_core_ok': len({s['leading_role_content_sha256'] for s in reps}) == 1,
                       'task_content_ok': len({s['task_content_sha256'] for s in reps}) == 1,
                       'message_by_role_max_slot': high['message_by_role_bytes'],
                       'message_by_role_min_slot': low['message_by_role_bytes']})
    require(len(groups) == 5, 'group count changed')
    dominant = {g['group']: {family: g['families'][family]['dominant'] for family in FAMILIES} for g in groups}
    m_star_groups = [g['group'] for g in groups if g['families']['m_star']['dominant']]
    environment_groups = [g['group'] for g in groups if g['families']['environment']['dominant']]
    branch = select_branch(m_star_groups, environment_groups, len(groups))
    require(all(g['delta'] > 0 for g in groups), 'nonpositive delta survived')
    return {'schema': 'r3-decomp-projection-v1', 'prereg_sha256': PREREG_SHA256,
            'baseline_commit': baseline,
            'baseline_source': 'resolved from .git HEAD without subprocess calls',
            'v1_reference': {'package': V1_HERE, 'verify_sha256': V1_VERIFY_SHA256,
                             'result_sha256': V1_RESULT_SHA256,
                             'evidence_sha256': V.EVIDENCE_SHA256, 'baseline_commit': V1_BASELINE,
                             'full_replay_reproduced': True},
            'contract': {'arm': 'codex', 'cases': list(CASES), 'reps': list(REPS),
                         'slots': 15, 'groups': 5, 'metric': 'R3_payload_canonical',
                         'classification': {'m_star': ['assistant message', 'reasoning', 'function_call'],
                                            'environment': ['developer/user/system message', 'function_call_output',
                                                            'turn_context', '其余非模型生成项（catch-all）'],
                                            'fail_closed': 'message payload without recognizable role stops the run'}},
            'groups': groups, 'slots': slot_outputs,
            'verdicts': {'branch': branch,
                         'm_star_dominant_groups': m_star_groups,
                         'environment_dominant_groups': environment_groups,
                         'm_star_dominant_group_count': len(m_star_groups),
                         'environment_dominant_group_count': len(environment_groups),
                         'groups_total': 5,
                         'per_group_dominant_families': dominant,
                         'statements': {
                             'M_STAR_DOMINANT_IN_4_OF_5_GROUPS': 'H1: R3 observation plane mixes model-generated bytes; DSH S3 is stable because its definition excludes that side; the two are not horizontally comparable. No gate or score changes.',
                             'E_DOMINANT_IN_SOME_GROUP': 'A group shows real environment/task-side input drift; that group is narrowed honestly to input-side instability.',
                             'MIXED_NO_SINGLE_DOMINANT_FAMILY': 'Families are comparable; no single-mechanism explanation is given.'}},
            'public_sources': evidence['public_sources'],
            'trace_bindings': [{'slot': s['slot'], 'file': s['trace_file'], 'sha256': s['trace_sha256'],
                                'archive_relative_path': s['trace_archive_relative_path']} for s in slot_outputs],
            'public_replay_scope': 'Content-free projection arithmetic, public source binding and SHA-pinned archived-original identity binding only; private raw authenticity NOT certified. Raw rollouts are required for message-role classification.',
            'limitations': ['Post-hoc decomposition of an already-frozen observation; not retroactive preregistration.',
                            'Canonical payload bytes, not wire bytes, tokens, costs or controlled input.',
                            'Delta decompositions are exact integer identities over archived payloads; no sampling or approximation.',
                            'Unknown payload types fall to E by the frozen catch-all; only model-generation ambiguity stops the run.']}


def sha_hex(data):
    return hashlib.sha256(data).hexdigest()


def digest_hex(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None, 'invalid SHA256')
    return value


def render_summary(result):
    lines = ['R3 instability source decomposition (schema ' + result['schema'] + ')',
             'prereg sha256 ok: ' + result['prereg_sha256'],
             'baseline: ' + result['baseline_commit'] + '  v1.1 replay reproduced: ' +
             ('yes' if result['v1_reference']['full_replay_reproduced'] else 'no')]
    for group in result['groups']:
        families = group['families']
        m_star = families['m_star']
        environment = families['environment']
        lines.append('group %s delta=%d M=%s(%d) m=%s(%d) M*net=%d share=%.4f dominant=%s | E net=%d share=%.4f dominant=%s | stable_core=%s' % (
            group['group'], group['delta'], group['max_slot'].split('__')[2], group['r3_totals'][group['slots'].index(group['max_slot'])],
            group['min_slot'].split('__')[2], group['r3_totals'][group['slots'].index(group['min_slot'])],
            m_star['net_contribution'], m_star['share'], m_star['dominant'],
            environment['net_contribution'], environment['share'], environment['dominant'],
            'ok' if group['stable_core_ok'] else 'FAIL'))
    verdict = result['verdicts']
    lines.append('verdict: %s | M* dominant %d/5 %s | E dominant %d/5 %s' % (
        verdict['branch'], verdict['m_star_dominant_group_count'], verdict['m_star_dominant_groups'],
        verdict['environment_dominant_group_count'], verdict['environment_dominant_groups']))
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--archive-root', type=Path, default=None,
                        help='root holding codex/runs/<slot>/agent-session archived originals; default <root>/' + BATCH)
    parser.add_argument('--output', type=Path, help='new exclusive destination; default stdout summary only')
    args = parser.parse_args(argv)
    try:
        result = analyze(args.root, args.archive_root)
        if args.output:
            text = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n'
            with args.output.open('x', encoding='utf-8') as stream:
                stream.write(text)
        sys.stdout.write(render_summary(result))
    except (Invalid, OSError, ValueError, KeyError, TypeError, IndexError) as error:
        sys.stderr.write('ERROR: ' + str(error) + '\n')
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
