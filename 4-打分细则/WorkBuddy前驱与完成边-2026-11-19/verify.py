"""Recompute the fixed, redacted ordinal comparison; no source authentication."""
from collections import Counter
import json
from pathlib import Path
import sys


class EvidenceError(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise EvidenceError(message)


def fields(obj, names):
    need(type(obj) is dict and obj.keys() == set(names.split()), 'unexpected or missing field')


def array(obj):
    need(type(obj) is list, 'expected ordered array')
    return obj


def ordinal(value, size):
    need(type(value) is int and 1 <= value <= size, 'invalid block-relative ordinal')
    return value


def unique_object(pairs):
    record = {}
    for key, value in pairs:
        need(key not in record, 'duplicate JSON key')
        record[key] = value
    return record


def reject_number(_):
    raise EvidenceError('only JSON integers are admitted')


LAYOUT = (
    ('A1', 'A', 'Read', ['call', 'call', 'result', 'result']),
    ('A2', 'A', 'Read', ['call', 'result']),
    ('A3', 'A', 'Bash', ['call', 'call', 'result', 'result']),
    ('B1', 'B', 'Read', ['call', 'call', 'result', 'result']),
)
BOUNDARY = {
    'input_layer': 'selected_archival_derivatives',
    'external_original_verification': 'unknown',
    'actual_successful_object': 'unknown',
    'fifo': 'not_tested',
}
TALLY_FIELDS = '''sources blocks call_rows result_rows immediate_predecessor_matches
predecessor_comparisons scoped_completion_bindings recorded_completed direct_same_call
 direct_different_call direct_parent_is_result completed_wrong_declared_read_target
admitted_bounded_read_result_assertions read_result_assertion_checks'''


def verify(data):
    fields(data, 'schema evidence_boundary blocks tallies')
    need(data['schema'] == 'workbuddy-local-ordinal-edges-v1', 'unknown evidence schema')
    need(data['evidence_boundary'] == BOUNDARY, 'unsupported evidence boundary')
    blocks = array(data['blocks'])
    need(len(blocks) == len(LAYOUT), 'incorrect block support')
    observed = Counter({key: 0 for key in TALLY_FIELDS.split()})
    source_aliases = set()
    for block, (alias, source_alias, tool, roles) in zip(blocks, LAYOUT):
        fields(block, 'block tool_type roles record_predecessors declared_read_call_pair completions')
        need((block['block'], block['tool_type'], block['roles']) == (alias, tool, roles),
             'incorrect tool or role at fixed block slot')
        source_aliases.add(source_alias)
        observed['blocks'] += 1
        size = len(roles)
        calls = [n for n, role in enumerate(roles, 1) if role == 'call']
        results = [n for n, role in enumerate(roles, 1) if role == 'result']
        observed['call_rows'] += len(calls)
        observed['result_rows'] += len(results)
        pair = block['declared_read_call_pair']
        if tool == 'Read' and len(calls) == 2:
            need(pair in ('different', 'same', 'unknown'), 'missing Read pair comparison category')
        else:
            need(pair == 'not_applicable', 'Read pair category attached to incompatible block')
        predecessor_rows = array(block['record_predecessors'])
        need(len(predecessor_rows) == size - 1, 'wrong predecessor support')
        parents = {}
        for expected_row, edge in enumerate(predecessor_rows, 2):
            need(type(edge) is list and len(edge) == 2, 'invalid predecessor edge')
            after, predecessor = (ordinal(k, size) for k in edge)
            need(after == expected_row and predecessor < after, 'predecessor not an earlier record in expected slot')
            parents[after] = predecessor
            observed['predecessor_comparisons'] += 1
            observed['immediate_predecessor_matches'] += predecessor == after - 1
        completions = array(block['completions'])
        need(len(completions) == len(results), 'wrong completion support')
        assigned_calls = set()
        for expected_result, completion in zip(results, completions):
            fields(completion, 'result call recorded_status bounded_result_assertion')
            after = ordinal(completion['result'], size)
            call = ordinal(completion['call'], size)
            need(after == expected_result and call in calls and call < after and call not in assigned_calls,
                 'completion must reference a distinct earlier call at the expected result')
            assigned_calls.add(call)
            observed['scoped_completion_bindings'] += 1
            status = completion['recorded_status']
            need(status in ('completed', 'failed', 'unknown'), 'unsupported recorded status')
            observed['recorded_completed'] += status == 'completed'
            assertion = completion['bounded_result_assertion']
            if tool == 'Read':
                need(assertion in ('not_admitted', 'admitted'), 'missing bounded Read assertion state')
                observed['read_result_assertion_checks'] += 1
                observed['admitted_bounded_read_result_assertions'] += assertion == 'admitted'
            else:
                need(assertion == 'not_tested', 'Read assertion state attached to non-Read tool')
            parent = parents[after]
            if parent == call:
                observed['direct_same_call'] += 1
            elif parent in calls:
                observed['direct_different_call'] += 1
                if tool == 'Read' and pair == 'different' and status == 'completed':
                    observed['completed_wrong_declared_read_target'] += 1
            else:
                need(parent in results, 'unknown parent role')
                observed['direct_parent_is_result'] += 1
        need(assigned_calls == set(calls), 'call omitted from fixed completion support')
    observed['sources'] = len(source_aliases)
    reported = data['tallies']
    fields(reported, TALLY_FIELDS)
    need(all(type(n) is int and n >= 0 for n in reported.values()), 'invalid tally type')
    need(dict(observed) == reported, 'reported tallies do not match ordinal relations')
    return dict(observed)


def main():
    try:
        evidence = json.loads(Path(__file__).with_name('evidence.json').read_text(encoding='utf-8'),
                              object_pairs_hook=unique_object, parse_float=reject_number,
                              parse_constant=reject_number)
        print(json.dumps(verify(evidence), sort_keys=True))
    except EvidenceError as exc:
        sys.exit(f'Invalid evidence: {exc}')
    except (OSError, ValueError, RecursionError):
        sys.exit('Invalid evidence: unreadable or invalid JSON')


if __name__ == '__main__':
    main()
