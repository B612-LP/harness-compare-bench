#!/usr/bin/env python3
"""Recompute r1109 measurement-layer diagnostics from three pinned public derivatives."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

PUBLIC_BASELINE = '89e1cf2468b81dd3dad1c00f56f5cd4a7552df10'
FILES = {
    'events': ('4-打分细则/机制重复口径澄清-2026-11-12/evidence.json',
               '925470d3b55b4226d70f5749d45d0c65a161703c4053fa21028ce0516fcd6b5c'),
    'old_gate': ('4-打分细则/机制重复口径澄清-2026-11-12/result.json',
                 'abb3a4fc09f1210b30021f7896551b7d0b34502cabbfe08ad0777b87dddc4433'),
    'roles': ('4-打分细则/R3不稳定来源分解-2026-11-16/result.json',
              '8b03be40cb53f0a562d8b6b8a006a8e97d1733d8a9da15df8dfc67b0fbb83188'),
}
CASES = ('bird-ca-schools-15', 'dabstep-payments-10', 'exercism-py-6',
         'lcb-recent-hard-4', 'tb-cargo-plan')
ARMS, REPS, LIMIT_B = ('dsh', 'codex'), (1, 2, 3), 100
LAYERS = ('r3', 'without_model', 'without_tool_results', 'startup_core',
          'without_both', 'first_usage_segment')
CONTROLS = ('leading_role_content_sha256', 'task_content_sha256')
SUBTYPES = ('message', 'reasoning', 'function_call', 'function_call_output')
DSH_S3 = ('user/message', 'request/header', 'request/context')
DSH_S4 = ('assistant/message', 'tool/call')
DSH_BOUNDARY = ('turn/start', 'turn/end')
DSH_STEP = (*DSH_BOUNDARY, 'step/start', 'step/end', 'tool/call', 'tool/result', 'assistant/message')
DSH_LEGACY = ('user', 'assistant', 'thinking', 'tool_call', 'tool_result', 'text', 'final', 'status', 'session')


class Invalid(ValueError):
    """Cannot identify or compare this fixed evidence set."""


def require(condition, message):
    if not condition:
        raise Invalid(message)


def natural(value, subject):
    require(type(value) is int and value >= 0, f'{subject}: invalid count or byte length')
    return value


def check_fields(row, expected, subject):
    for key, value in expected.items():
        require(key in row and row[key] == value and type(row[key]) is type(value),
                f'{subject}: {key} mismatch')


def digest_ok(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def read_pinned(root, relative, digest):
    try:
        raw = (root / relative).read_bytes()
    except OSError as exc:
        raise Invalid(f'{relative}: input unavailable') from exc
    require(sha256(raw).hexdigest() == digest, f'{relative}: SHA-256 mismatch')
    return json.loads(raw.decode('utf-8'))


def unique_index(rows, key_of, expected, subject):
    index = {}
    for row in rows:
        key = key_of(row)
        require(key in expected, f'{subject}: mixed identity')
        require(key not in index, f'{subject}: duplicate identity')
        index[key] = row
    require(index.keys() == expected, f'{subject}: missing identities')
    return index


def slot_id(arm, case, rep):
    return f'{arm}__{case}__r{rep}'


def slot_keys(arms):
    return {slot_id(arm, case, rep) for arm in arms for case in CASES for rep in REPS}


def measure(rows, arm):
    """Measure projected lengths; never reconstruct texts or a request packet."""
    require(isinstance(rows, list) and rows, 'missing event projection')
    types, response, segments = [], [], []
    totals, events_b, counts = Counter(), Counter(), Counter()
    since_usage = []
    wrapper_b = 0
    for row in rows:
        require(isinstance(row, list) and len(row) == 4, 'invalid event tuple')
        event, event_b, subtype, payload_b = row
        require(isinstance(event, str) and event, 'invalid event type')
        require(natural(event_b, 'event') > 0, 'empty event')
        natural(payload_b, 'payload')
        types.append(event)
        counts[event] += 1
        events_b[event] += event_b
        if event == 'response_item':
            require(arm == 'codex' and subtype in SUBTYPES and 0 < payload_b < event_b,
                    'invalid or unknown response_item subtype or length')
            item = (subtype, payload_b)
            response.append(item)
            since_usage.append(item)
            totals[subtype] += payload_b
            wrapper_b += event_b
        else:
            require(subtype is None and payload_b == 0, 'unexpected payload accounting')
            if event == 'token_usage_record':
                require(arm == 'codex', 'mixed usage marker')
                segments.append(since_usage)
                since_usage = []

    if arm == 'dsh':
        require(types[0] == 'session' and counts['session'] == 1, 'invalid DSH session anchor')
        require(all(counts[t] for t in DSH_BOUNDARY), 'missing DSH turn boundary')
        s3_by_type = {t: {'events': counts[t], 'bytes': events_b[t]} for t in DSH_S3}
        s3 = sum(row['bytes'] for row in s3_by_type.values())
        s4 = sum(events_b[t] for t in DSH_S4)
        require(s3 > 0 and s4 > 0, 'missing DSH byte layer')
        return {'event_count': len(rows), 'input_bytes': s3, 'output_bytes': s4,
                's3_by_type': s3_by_type,
                'legacy_sequence': [t for t in types if t in DSH_LEGACY],
                'boundary_sequence': [t for t in types if t in DSH_BOUNDARY],
                'step_sequence': [t for t in types if t in DSH_STEP]}

    require(arm == 'codex' and types[0] == 'session_meta' and counts['session_meta'] == 1,
            'invalid Codex session anchor')
    require(response, 'missing response_item coverage')
    first_three = response[:3]
    startup_observed = [kind for kind, _ in first_three] == ['message'] * 3
    return {'input_bytes': sum(totals.values()), 'output_bytes': totals['message'] + totals['reasoning'],
            'event_count': len(rows), 'response_item_count': len(response),
            'per_type_bytes': dict(totals),
            'event_wrapper_canonical_bytes': wrapper_b, 'closed_turns': len(segments),
            'startup_candidate_b': sum(b for _, b in first_three) if startup_observed else None,
            'first_segment': segments[0] if startup_observed and segments and len(segments[0]) >= 3 else None,
            'trailing_unclosed_b': sum(b for _, b in since_usage)}


def control_key(controls, role_row, subject):
    """Return comparable control fingerprints, or None for insufficient coverage."""
    fingerprints = tuple(controls.get(key) for key in CONTROLS)
    inferred = tuple(role_row.get(key) for key in CONTROLS)
    for a, b in zip(fingerprints, inferred):
        if a is not None and b is not None:
            require(digest_ok(a) and digest_ok(b) and a == b, f'{subject}: conflicting control binding')
    if controls.get('roles') != ['developer', 'user', 'user'] or controls.get('first_user_is_environment') is not True:
        return None
    return fingerprints if all(digest_ok(a) and digest_ok(b) for a, b in zip(fingerprints, inferred)) else None


def codex_layers(measured, controls, role_row, subject):
    check_fields(role_row, {k: measured[k] for k in ('event_count', 'response_item_count', 'closed_turns',
                                                    'per_type_bytes')}, subject)
    total = measured['input_bytes']
    check_fields(role_row, {'r3_total_bytes': total}, subject)
    roles = role_row['message_by_role_bytes']
    require(set(roles) == {'assistant', 'developer', 'user'}, f'{subject}: missing or unknown message role')
    require(sum(natural(b, subject) for b in roles.values()) == measured['per_type_bytes'].get('message', 0),
            f'{subject}: role totals do not reconcile to message')
    non_model_messages = roles['developer'] + roles['user']
    by_type = measured['per_type_bytes']
    model = roles['assistant'] + by_type.get('reasoning', 0) + by_type.get('function_call', 0)
    tool = by_type.get('function_call_output', 0)
    check_fields(role_row['family_bytes'], {'m_star': model, 'environment': non_model_messages + tool}, subject)
    require(model + tool + non_model_messages == total, f'{subject}: partition does not reconcile to R3')

    control = control_key(controls, role_row, subject)
    core_b = measured['startup_candidate_b'] if control is not None else None
    require(core_b is None or core_b <= non_model_messages, f'{subject}: startup exceeds corresponding roles')
    first = measured['first_segment'] if core_b is not None else None
    return {'control': control, 'trailing_unclosed_b': measured['trailing_unclosed_b'],
            'first_usage_model_lower_bound_b': (None if first is None else sum(
                b for kind, b in first if kind in ('reasoning', 'function_call'))),
            'values': {'r3': total, 'without_model': total - model, 'without_tool_results': total - tool,
                       'startup_core': core_b, 'without_both': total - model - tool,
                       'first_usage_segment': sum(b for _, b in first) if first is not None else None}}


def compare(values):
    """Re-extremize within exactly three slots and preserve all tied endpoint IDs."""
    require(len(values) == len(REPS), 'need exactly three slots')
    for value in values:
        if value is not None:
            natural(value, 'comparison')
    result = {'values_b': values, 'range_b': None, 'min_reps': [], 'max_reps': [], 'status': 'unknown'}
    if all(v is not None for v in values):
        lo, hi = min(values), max(values)
        result.update(range_b=hi - lo, min_reps=[r for r, v in zip(REPS, values) if v == lo],
                      max_reps=[r for r, v in zip(REPS, values) if v == hi],
                      status='pass' if hi - lo <= LIMIT_B else 'fail')
    return result


def endpoints(diagnostic):
    return diagnostic['min_reps'], diagnostic['max_reps']


def codex_group(rows):
    controls = [row['control'] for row in rows]
    shared = all(c is not None for c in controls) and len(set(controls)) == 1
    diagnostics = {}
    for layer in LAYERS:
        values = ([None] * len(REPS) if layer == 'startup_core' and not shared
                  else [r['values'][layer] for r in rows])
        diagnostics[layer] = compare(values)
    for diagnostic in diagnostics.values():
        diagnostic['endpoints_changed_from_r3'] = (None if diagnostic['status'] == 'unknown'
                                                   else endpoints(diagnostic) != endpoints(diagnostics['r3']))
    core_values = diagnostics['startup_core']['values_b']
    return {'shared_startup_control': shared, 'layers': diagnostics,
            'without_both_equals_startup_all_slots': (None if any(v is None for v in core_values)
                                                       else core_values == diagnostics['without_both']['values_b']),
            'first_usage_model_lower_bound_b': [r['first_usage_model_lower_bound_b'] for r in rows],
            'trailing_unclosed_b': [r['trailing_unclosed_b'] for r in rows]}


def analyze(evidence, old_gate, roles):
    contract = {'arms': list(ARMS), 'cases': list(CASES), 'reps': list(REPS), 'slots': 30,
                'groups': 10, 'byte_threshold': LIMIT_B, 'operator': 'AND'}
    check_fields(evidence, {'schema': 'r1109-content-free-projection-v1.1', 'contract': contract}, 'events')
    check_fields(old_gate, {'schema': 'mechanism-repetition-clarification-v1.1', 'contract': contract,
                            'evidence_sha256': FILES['events'][1], 'historical_upgrade_10_of_10': False}, 'old gate')
    check_fields(roles, {'schema': 'r3-decomp-projection-v1'}, 'roles')
    key = lambda row: row['slot']
    event_slots = unique_index(evidence['slots'], key, slot_keys(ARMS), 'events')
    old_slots = unique_index(old_gate['slots'], key, slot_keys(ARMS), 'old gate slots')
    role_slots = unique_index(roles['slots'], key, slot_keys(('codex',)), 'roles')
    old_groups = unique_index(old_gate['groups'], lambda row: (row['arm'], row['case']),
                              {(arm, case) for arm in ARMS for case in CASES}, 'old gate groups')
    historical = Counter()
    groups = {arm: [] for arm in ARMS}
    for arm in ARMS:
        for case in CASES:
            slots, layers = [], []
            for rep in REPS:
                slot = slot_id(arm, case, rep)
                event, old = event_slots[slot], old_slots[slot]
                trace_sha = event['identity']['sha256']
                require(digest_ok(trace_sha), f'{slot}: invalid trace SHA')
                binding = {'trace_sha256': trace_sha, 'aggregate_path': event['aggregate_path'],
                           'case': case, 'rep': rep}
                metrics = measure(event['events'], arm)
                check_fields(old, dict(binding, arm=arm, status='ok', identity_reconciled_to_public_receipt=True,
                                       **{k: metrics[k] for k in ('event_count', 'input_bytes', 'output_bytes')}), slot)
                slots.append(metrics)
                if arm == 'codex':
                    old_claim = {k: metrics[k] for k in ('closed_turns', 'event_wrapper_canonical_bytes')}
                    controls = event.get('controls', {})
                    check_fields(old, dict(old_claim, metric='R3_payload_canonical',
                                           output_metric='R4_payload_canonical'), slot)
                    require(controls == old.get('controls', {}), f'{slot}: control projection mismatch')
                    check_fields(role_slots[slot], binding, slot)
                    layers.append(codex_layers(metrics, controls, role_slots[slot], slot))
                else:
                    require(metrics['legacy_sequence'] == ['session'], f'{slot}: legacy degradation changed')
                    step = metrics['step_sequence']
                    step_sha = sha256(json.dumps(step, separators=(',', ':')).encode('utf-8')).hexdigest()
                    check_fields(old, {'metric': 'S3_event_canonical', 'output_metric': 'S4_event_canonical',
                                       'legacy_sequence': ['session'], 'legacy_sequence_sufficient': False,
                                       'boundary_sequence': metrics['boundary_sequence'],
                                       'step_sequence_length': len(step), 'step_sequence_sha256': step_sha}, slot)

            inputs = [s['input_bytes'] for s in slots]
            outputs = [s['output_bytes'] for s in slots]
            byte_diag = compare(inputs)
            status = 'fail' if byte_diag['status'] == 'fail' else 'unverifiable'
            historical[status] += 1
            check_fields(old_groups[arm, case], {'n': 3, 'input_bytes': inputs, 'output_bytes': outputs,
                                                'sequence_subgate': None, 'max_minus_min': byte_diag['range_b'],
                                                'byte_subgate_pass': byte_diag['status'] == 'pass',
                                                'historical_AND_status': status}, f'{arm}/{case} old gate')
            group = {'case': case, 'old_and': status, 'old_sequence': None}
            if arm == 'codex':
                group.update(codex_group(layers), r4_b=outputs)
            else:
                group.update(s3=byte_diag, s4_b=outputs, legacy_session_only=True,
                             narrow_boundary_equal=all(s['boundary_sequence'] == slots[0]['boundary_sequence'] for s in slots),
                             step_tool_assistant_equal=all(s['step_sequence'] == slots[0]['step_sequence'] for s in slots),
                             s3_by_type=[s['s3_by_type'] for s in slots])
            groups[arm].append(group)

    expected_counts = {'fail': 6, 'unverifiable': 4}
    check_fields(old_gate, {'historical_AND_status_counts': expected_counts}, 'old gate totals')
    require(dict(historical) == expected_counts, 'old gate totals changed')
    counts = {layer: {status: sum(g['layers'][layer]['status'] == status for g in groups['codex'])
                      for status in ('pass', 'fail', 'unknown')} for layer in LAYERS}
    return {'baseline_public_head': PUBLIC_BASELINE, 'source_sha256': {path: h for path, h in FILES.values()},
            'n_slots': len(event_slots), 'byte_threshold_b': LIMIT_B, 'slot_order': list(REPS),
            'old_and_counts': {'pass': 0, **expected_counts}, 'old_and_upgraded': False,
            'codex_aux_counts': counts, 'codex': groups['codex'], 'dsh': groups['dsh'],
            'first_request_body': 'unknown', 'actual_backend_ingestion': 'unknown',
            'controlled_harness_effect': 'unknown'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2],
                        help='public repository root (default: relative to this script)')
    args = parser.parse_args()
    try:
        data = {key: read_pinned(args.root, *binding) for key, binding in FILES.items()}
        result = analyze(data['events'], data['old_gate'], data['roles'])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'Cannot recompute: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
