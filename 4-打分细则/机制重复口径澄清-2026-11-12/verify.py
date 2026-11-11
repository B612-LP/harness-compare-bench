#!/usr/bin/env python3
"""v1.1 retrospective clarification. Read-only stdlib; no old tool imports.
Public replay verifies a content-free measurement projection, not private originals.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

BASELINE = '38b2e13f63c5aeacb58094d2e977980ab12e8041'
HERE = '4-打分细则/机制重复口径澄清-2026-11-12'
BATCH = '3-表现现场/r1109-mech-n3'
OBS = '3-表现现场/r1109-bw-retest/observe'
CASES = ('bird-ca-schools-15', 'dabstep-payments-10', 'exercism-py-6', 'lcb-recent-hard-4', 'tb-cargo-plan')
ARMS = ('dsh', 'codex')
CONTRACT = {'cases': list(CASES), 'arms': list(ARMS), 'reps': [1, 2, 3], 'slots': 30,
            'groups': 10, 'byte_threshold': 100, 'operator': 'AND'}
EVIDENCE_SHA256 = '925470d3b55b4226d70f5749d45d0c65a161703c4053fa21028ce0516fcd6b5c'
LEGACY_TYPES = frozenset(('user', 'assistant', 'thinking', 'tool_call', 'tool_result', 'text', 'final', 'status', 'session'))
BOUNDARY_TYPES = frozenset(('turn/start', 'turn/end'))
STEP_TYPES = frozenset(('turn/start', 'step/start', 'tool/call', 'tool/result', 'assistant/message', 'step/end', 'turn/end'))
INPUT_TYPES = frozenset(('user/message', 'request/header', 'request/context'))
OUTPUT_TYPES = frozenset(('assistant/message', 'tool/call'))
CORRECTED_DSH = frozenset(('dsh__bird-ca-schools-15__r2', 'dsh__dabstep-payments-10__r3', 'dsh__tb-cargo-plan__r2'))


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None, 'invalid SHA256')
    return value


def integer(value):
    require(type(value) is int and value >= 0, 'expected nonnegative integer')
    return value


def expected_slots():
    return [f'{arm}__{case}__r{rep}' for arm in ARMS for case in CASES for rep in (1, 2, 3)]


def validate_slots(rows):
    require(isinstance(rows, list), 'slots must be list')
    ids = [row['slot'] for row in rows]
    require(len(ids) == len(set(ids)), 'duplicate slot')
    require(set(ids) == set(expected_slots()), 'missing or mixed slot')
    require(len(rows) == 30, 'slot count changed')


def historical_gate(values, sequence_equal):
    require(len(values) == 3 and all(type(v) is int and v >= 0 for v in values), 'need three byte values')
    require(sequence_equal is None or type(sequence_equal) is bool, 'invalid sequence verdict')
    byte_pass = max(values) - min(values) <= 100
    status = 'fail' if not byte_pass or sequence_equal is False else ('unverifiable' if sequence_equal is None else 'pass')
    return {'max_minus_min': max(values) - min(values), 'byte_subgate_pass': byte_pass,
            'sequence_subgate': sequence_equal, 'historical_AND_status': status}


def legacy_sequence(types):
    """Historical semantic diagnostic: fixed old whitelist, not an authenticity claim."""
    return [t for t in types if t in LEGACY_TYPES]


def sufficient_legacy_sequence(sequence):
    return bool(sequence) and any(t != 'session' for t in sequence)


def select_controls(events):
    """Exactly first three leading response messages: permissions, environment, task.
    Never label the first user (environment_context) as the task.
    """
    items = [e['payload'] for e in events if e['type'] == 'response_item']
    require(len(items) >= 3, 'missing leading controls')
    leading = items[:3]
    require([p.get('type') for p in leading] == ['message'] * 3, 'bad control types')
    require([p.get('role') for p in leading] == ['developer', 'user', 'user'], 'bad control roles')
    for payload in leading:
        require(isinstance(payload.get('content'), list), 'bad control content')
    env = canon(leading[1]['content'])
    require(b'environment_context' in env, 'first user is not environment_context')
    require(b'environment_context' not in canon(leading[2]['content']), 'task confused with environment')
    controls = [{'role': p['role'], 'content': p['content']} for p in leading]
    return {'roles': ['developer', 'user', 'user'], 'first_user_is_environment': True,
            'leading_role_content_sha256': sha(canon(controls)),
            'task_content_sha256': sha(canon(leading[2]['content']))}


def project_events(events, arm):
    """Content-free per-event measurements; original content is deliberately absent.
    Rows: [type, canonical event bytes, payload.type or null, canonical payload bytes].
    """
    require(arm in ARMS and isinstance(events, list) and events, 'bad event source')
    rows = []
    for event in events:
        require(isinstance(event, dict) and isinstance(event.get('type'), str), 'bad event schema')
        kind = event['type']
        payload = event.get('payload')
        if arm == 'codex' and kind in ('response_item', 'token_usage_record'):
            require(isinstance(payload, dict), 'missing payload')
        subtype = payload.get('type') if kind == 'response_item' else None
        if kind == 'response_item':
            require(isinstance(subtype, str), 'missing payload.type')
        rows.append([kind, len(canon(event)), subtype,
                     len(canon(payload)) if kind == 'response_item' else 0])
    return rows


def measure(rows, arm):
    require(arm in ARMS, 'unknown arm')
    require(isinstance(rows, list) and rows, 'missing event projection')
    for row in rows:
        require(isinstance(row, list) and len(row) == 4, 'bad event projection schema')
        require(isinstance(row[0], str) and row[0], 'bad event type')
        integer(row[1]); integer(row[3])
        require(row[1] > 0, 'empty canonical event')
        if row[0] == 'response_item':
            require(arm == 'codex' and isinstance(row[2], str) and row[1] > row[3] > 0, 'bad response projection')
        else:
            require(row[2] is None and row[3] == 0, 'unexpected payload projection')
    types = [row[0] for row in rows]
    result = {'event_count': len(rows), 'type_counts': dict(sorted(Counter(types).items()))}
    if arm == 'dsh':
        require(types[0] == 'session' and Counter(types)['session'] == 1, 'invalid DSH session')
        require(Counter(types)['turn/start'] > 0 and Counter(types)['turn/end'] > 0, 'missing DSH turn evidence')
        result.update({'input_bytes': sum(r[1] for r in rows if r[0] in INPUT_TYPES),
                       'output_bytes': sum(r[1] for r in rows if r[0] in OUTPUT_TYPES),
                       'legacy_sequence': legacy_sequence(types),
                       'boundary_sequence': [t for t in types if t in BOUNDARY_TYPES],
                       'step_sequence': [t for t in types if t in STEP_TYPES]})
        require(result['input_bytes'] > 0 and result['output_bytes'] > 0, 'missing DSH metrics')
    else:
        require(types[0] == 'session_meta' and Counter(types)['session_meta'] == 1, 'invalid Codex session')
        turns = []
        cur_in = cur_out = items = 0
        for kind, event_bytes, subtype, payload_bytes in rows:
            if kind == 'response_item':
                cur_in += payload_bytes; items += 1
                if subtype in ('message', 'reasoning'):
                    cur_out += payload_bytes
            elif kind == 'token_usage_record':
                turns.append({'input_bytes': cur_in, 'output_bytes': cur_out, 'items': items, 'closed': True})
                cur_in = cur_out = items = 0
        if items:
            turns.append({'input_bytes': cur_in, 'output_bytes': cur_out, 'items': items, 'closed': False})
        require(turns and sum(t['items'] for t in turns) > 0, 'missing Codex measurements')
        result.update({'input_bytes': sum(t['input_bytes'] for t in turns),
                       'output_bytes': sum(t['output_bytes'] for t in turns), 'turns': turns,
                       'closed_turns': sum(t['closed'] for t in turns),
                       'event_wrapper_canonical_bytes': sum(r[1] for r in rows if r[0] == 'response_item'),
                       'boundary_sequence': [t for t in types if t == 'token_usage_record']})
    return result


def check_identity(slot, meta, identity, incident, receipt):
    arm, case, rep_text = slot.split('__')
    rep = rep_text[1:]
    require((meta['product'], meta['case'], meta['rep']) == (arm, case, rep), 'meta identity mismatch')
    require(meta['event_id'] == f'mech-n3-{arm}-{case}-r{rep}', 'event identity mismatch')
    require(meta['batch'] in ('r1109-mech-n3', 'r1030-formal-a1'), 'mixed batch')
    # Some public meta copies retain the a1 batch label. Never infer identity from it.
    require((receipt['product'], receipt['case_id'], receipt['rep'], receipt['run_id']) ==
            (arm, case, rep, f'r1109-{arm}-{case}-r{rep}'), 'receipt identity mismatch')
    require(meta['status'] == 'ok' and meta['exit_code'] == 0, 'slot not completed')
    require(incident['slot'] == slot and incident['started_at'] == meta['started_at'], 'accounting identity mismatch')
    expected_source = f'{arm}/runs/{slot}/agent-session/' + ('session.v4.jsonl.zstd' if arm == 'dsh' else identity['file'])
    require(identity['source_relative_to_archive'] == expected_source, 'trace slot path mismatch')
    if arm == 'dsh':
        require(identity['id'] in incident['candidates'] and identity['version'] == 4, 'DSH source identity mismatch')
        if 'new_sha' in incident:
            require(identity['sha256'].startswith(incident['new_sha']), 'DSH trace SHA prefix mismatch')
    else:
        require(identity['file'] == incident['true_rollout'], 'wrong true rollout')
        require(identity['id'] in identity['file'], 'Codex source identity mismatch')
    digest(identity['sha256'])


def check_metric_claim(actual, claimed, label):
    require(actual == claimed, label + ' mismatch')


def bound_json(root, record):
    relative = record['path']
    path = Path(relative)
    require(not path.is_absolute() and '..' not in path.parts, 'unsafe source path')
    absolute = (root / path).resolve()
    require(root == absolute or root in absolute.parents, 'source escapes root')
    try:
        raw = absolute.read_bytes()
    except OSError as error:
        raise Invalid('missing source: ' + relative) from error
    require(sha(raw) == digest(record['sha256']), 'source SHA mismatch: ' + relative)
    try:
        return json.loads(raw)
    except (ValueError, UnicodeError) as error:
        raise Invalid('invalid source JSON: ' + relative) from error


def analyze(root):
    root = Path(root).resolve()
    evidence_path = root / HERE / 'evidence.json'
    raw = evidence_path.read_bytes()
    require(sha(raw) == EVIDENCE_SHA256, 'evidence SHA mismatch')
    evidence = json.loads(raw)
    require(evidence['schema'] == 'r1109-content-free-projection-v1.1', 'bad evidence schema')
    require(evidence['baseline_commit'] == BASELINE and evidence['contract'] == CONTRACT, 'baseline or contract changed')
    validate_slots(evidence['slots'])
    records = evidence['public_sources']
    require(len({r['path'] for r in records}) == len(records), 'duplicate source binding')
    sources = {record['path']: bound_json(root, record) for record in records if record['path'].endswith('.json')}
    # Non-JSON normative source bindings are also checked; they are never executed.
    for record in records:
        if not record['path'].endswith('.json'):
            path = (root / record['path']).resolve()
            require(root in path.parents, 'normative source escapes root')
            require(sha(path.read_bytes()) == record['sha256'], 'normative source SHA mismatch')
    accounting = sources[BATCH + '/observe/trace-accounting-summary.json']
    incidents = {}
    for arm in ARMS:
        rows = accounting[arm]['incidents']
        require(len(rows) == 15, 'accounting slot count changed')
        for row in rows:
            require(row['slot'] not in incidents, 'duplicate accounting slot')
            incidents[row['slot']] = row
    require(set(incidents) == set(expected_slots()), 'mixed accounting slots')
    adjudications = sources[BATCH + '/adjudications.json']
    require(len(adjudications) == 30, 'adjudication count changed')
    receipts = {f"{r['identity']['product']}__{r['identity']['case_id']}__r{r['identity']['rep']}": r['identity'] for r in adjudications}
    require(set(receipts) == set(expected_slots()), 'mixed adjudication identities')
    historical_summary = sources[OBS + '/codex-r3-summary.json']['cases']
    historical_dsh = sources[OBS + '/dsh-s3-s4-summary.json']
    slots = []
    diagnostics = []
    for row in evidence['slots']:
        slot = row['slot']; arm, case, rep_text = slot.split('__'); rep = int(rep_text[1:])
        meta = sources[BATCH + '/runs/' + slot + '/meta.public-derived.json']
        receipt = receipts[slot]
        check_identity(slot, meta, row['identity'], incidents[slot], receipt)
        metrics = measure(row['events'], arm)
        expected_aggregate = (f'{OBS}/session-{slot if slot in CORRECTED_DSH else slot.replace("dsh__", "dsh-", 1)}.json'
                              if arm == 'dsh' else f'{OBS}/reqside-codex-{case}__r{rep}.json')
        require(row['aggregate_path'] == expected_aggregate, 'aggregate slot path mismatch')
        aggregate = sources[row['aggregate_path']]
        out = {'slot': slot, 'arm': arm, 'case': case, 'rep': rep, 'status': meta['status'],
               'identity_reconciled_to_public_receipt': True, 'trace_sha256': row['identity']['sha256'],
               'meta_batch_label': meta['batch'], 'meta_a1_gate_present': 'a1_gate' in meta,
               'aggregate_path': row['aggregate_path'], 'input_bytes': metrics['input_bytes'],
               'output_bytes': metrics['output_bytes'], 'event_count': metrics['event_count']}
        if arm == 'dsh':
            require(aggregate['format'] == 'dsh-session-v4-jsonl-zstd' and len(aggregate['per_file']) == 1, 'bad DSH aggregate')
            f = aggregate['per_file'][0]
            # Four main/corrected captures used a basename as the aggregate run label.
            # Exact slot-specific path+SHA and accounting source id remain mandatory.
            basename_labels = CORRECTED_DSH | {'dsh__dabstep-payments-10__r1'}
            aggregate_run = 'session.v4.jsonl.zstd' if slot in basename_labels else slot
            require(f['run'] == aggregate_run and aggregate['inputs']['runs'] == [aggregate_run], 'DSH aggregate identity mismatch')
            require(f['s1']['unparsable'] == 0 and f['s1']['lines'] == metrics['event_count'], 'bad DSH aggregate event coverage')
            check_metric_claim(metrics['type_counts'], f['s2']['type_counts'], 'DSH types')
            check_metric_claim(metrics['input_bytes'], f['s3']['input_bytes'], 'S3')
            check_metric_claim(metrics['output_bytes'], f['s4']['output_bytes'], 'S4')
            out.update({'metric': 'S3_event_canonical', 'output_metric': 'S4_event_canonical',
                        'legacy_sequence': metrics['legacy_sequence'],
                        'legacy_sequence_sufficient': sufficient_legacy_sequence(metrics['legacy_sequence']),
                        'boundary_sequence': metrics['boundary_sequence'],
                        'step_sequence_length': len(metrics['step_sequence']),
                        'step_sequence_sha256': sha(canon(metrics['step_sequence']))})
            old_value = historical_dsh[case]['s4_output_bytes'][rep - 1]
            if old_value != metrics['output_bytes']:
                diagnostics.append({'slot': slot, 'field': 'S4', 'public_summary_value': old_value,
                                    'recomputed_value': metrics['output_bytes'], 'source': OBS + '/dsh-s3-s4-summary.json'})
        else:
            agg = aggregate['aggregate']
            require(agg['schema'] == 'request-side-observe-v1' and len(agg['files']) == 1, 'bad Codex aggregate')
            f = agg['files'][0]
            require(f['sha256'] == row['identity']['sha256'] and f['file'] == row['identity']['file'], 'Codex trace SHA or basename mismatch')
            require(f['unparsable_lines'] == 0 and f['lines'] == metrics['event_count'], 'bad Codex aggregate event coverage')
            check_metric_claim(metrics['input_bytes'], agg['totals']['response_item_bytes_reconstructed_total'], 'R3')
            check_metric_claim(metrics['output_bytes'], agg['totals']['output_message_reasoning_bytes_total'], 'R4')
            check_metric_claim(metrics['input_bytes'], incidents[slot]['r3_input_bytes'], 'accounting R3')
            check_metric_claim(metrics['output_bytes'], incidents[slot]['r3_output_reasoning_bytes'], 'accounting R4')
            check_metric_claim(metrics['closed_turns'], f['turns_closed'], 'closed turns')
            require(len(metrics['turns']) == len(f['turns']), 'turn count mismatch')
            for recomputed, original in zip(metrics['turns'], f['turns']):
                check_metric_claim(recomputed['input_bytes'], original['response_item_bytes_reconstructed'], 'turn R3')
                check_metric_claim(recomputed['output_bytes'], original['output_message_reasoning_bytes'], 'turn R4')
                check_metric_claim(recomputed['items'], original['response_item_count'], 'turn items')
            controls = row['controls']
            require(controls['roles'] == ['developer', 'user', 'user'] and controls['first_user_is_environment'] is True, 'invalid control semantics')
            digest(controls['leading_role_content_sha256']); digest(controls['task_content_sha256'])
            out.update({'metric': 'R3_payload_canonical', 'output_metric': 'R4_payload_canonical',
                        'event_wrapper_canonical_bytes': metrics['event_wrapper_canonical_bytes'],
                        'closed_turns': metrics['closed_turns'], 'controls': controls})
            old_value = historical_summary[case]['r3_reconstructed_input_bytes'][rep - 1]
            if old_value != metrics['input_bytes']:
                diagnostics.append({'slot': slot, 'field': 'R3', 'public_summary_value': old_value,
                                    'recomputed_value': metrics['input_bytes'], 'source': OBS + '/codex-r3-summary.json'})
        slots.append(out)
    validate_slots(slots)
    groups = []
    for arm in ARMS:
        for case in CASES:
            rows = sorted([r for r in slots if r['arm'] == arm and r['case'] == case], key=lambda r: r['rep'])
            require([r['rep'] for r in rows] == [1, 2, 3], 'group repetitions changed')
            values = [r['input_bytes'] for r in rows]
            group = {'arm': arm, 'case': case, 'n': 3, 'input_bytes': values,
                     'output_bytes': [r['output_bytes'] for r in rows], **historical_gate(values, None)}
            # None is intentional: post-hoc diagnostics cannot supply the ambiguous historical subgate.
            if arm == 'dsh':
                group.update({'legacy_all_session_only': all(r['legacy_sequence'] == ['session'] for r in rows),
                              'narrow_boundary_equal_diagnostic': len({tuple(r['boundary_sequence']) for r in rows}) == 1,
                              'step_tool_assistant_equal_diagnostic': len({r['step_sequence_sha256'] for r in rows}) == 1,
                              'S4_max_min_ratio': max(r['output_bytes'] for r in rows) / min(r['output_bytes'] for r in rows)})
            else:
                group.update({'leading_role_content_equal_secondary': len({r['controls']['leading_role_content_sha256'] for r in rows}) == 1,
                              'task_content_equal_secondary': len({r['controls']['task_content_sha256'] for r in rows}) == 1})
            groups.append(group)
    require(len(groups) == 10, 'group count changed')
    return {'schema': 'mechanism-repetition-clarification-v1.1', 'baseline_commit': BASELINE,
            'contract': CONTRACT, 'new_product_runs': 0, 'new_product_requests': 0,
            'public_replay_scope': 'Content-free projection arithmetic and public source binding only; private raw authenticity NOT certified.',
            'historical_upgrade_10_of_10': all(g['historical_AND_status'] == 'pass' for g in groups),
            'M1_inline_spill_effect_identified': False,
            'byte_subgate_pass_counts': {arm: sum(g['byte_subgate_pass'] for g in groups if g['arm'] == arm) for arm in ARMS},
            'historical_AND_status_counts': dict(sorted(Counter(g['historical_AND_status'] for g in groups).items())),
            'canonical_codex_R3_range': [min(r['input_bytes'] for r in slots if r['arm'] == 'codex'), max(r['input_bytes'] for r in slots if r['arm'] == 'codex')],
            'groups': groups, 'slots': slots, 'public_summary_discrepancies': diagnostics,
            'source_bindings': records, 'evidence_sha256': sha(raw),
            'limitations': ['Post-hoc v1.1 clarification, not retroactive preregistration or gate replacement.',
                            'Selected canonical event/payload bytes, not wire bytes, tokens, costs or complete controlled input.',
                            'Source projections omit contents; raw event serialization, control hashes and full identity require original archive.',
                            'Legacy whitelist is a semantic diagnostic, not public authentication of the historical private implementation.',
                            'No scores rejudged; no historical files modified; no new causal mechanism evidence.']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, help='new exclusive destination; default stdout')
    args = parser.parse_args(argv)
    try:
        result = analyze(args.root)
        text = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n'
        if args.output:
            with args.output.open('x', encoding='utf-8') as stream:
                stream.write(text)
        else:
            sys.stdout.write(text)
    except (Invalid, OSError, ValueError, KeyError, TypeError, IndexError) as error:
        sys.stderr.write('ERROR: ' + str(error) + '\n')
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
