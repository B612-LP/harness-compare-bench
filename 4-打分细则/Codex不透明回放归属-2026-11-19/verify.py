#!/usr/bin/env python3
"""Recompute ordinal joins and counts from the adjacent safe projection only."""
from copy import deepcopy
import json
import os
from pathlib import Path
import stat
import sys


SCHEMA = 'codex-replay-ordinal-v1'
TRIPLE = ['reasoning', 'function_call', 'function_call_output']
PAIR_KEYS = ('wire_native', 'wire_history', 'native_history')


class Reject(ValueError):
    pass


def require(condition):
    if not condition:
        raise Reject('unsupported or inconsistent ordinal projection')


def fields(value, *names):
    require(type(value) is dict and set(value) == set(names))


def ordinal(value, expected):
    require(type(value) is int and value == expected)


def array(value):
    require(type(value) is list)
    return value


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def reject_constant(_):
    raise Reject('invalid JSON constant')


def load_projection(text):
    return json.loads(text, object_pairs_hook=unique_keys, parse_constant=reject_constant)


def field_view(row):
    state, size = row['field_state'], row['utf8_bytes']
    if state == 'present_string':
        require(type(size) is int and size > 0)
    elif state == 'empty_string':
        ordinal(size, 0)
    else:
        require(state in ('absent', 'null') and size is None)
    return state, size


def equality_report(a, b, claimed):
    # Checks consistency of the reported flag; never recomputes source equality.
    if a[1] is None or b[1] is None:
        require(claimed is None)
        return None
    require(type(claimed) is bool and (not claimed or a[1] == b[1]))
    return claimed


def summarize(data):
    fields(data, 'schema', 'runs')
    require(data['schema'] == SCHEMA)
    runs = array(data['runs'])
    require(len(runs) == 1)  # This projection covers one run and no replication.
    first, carried = [], []
    first_count, native_direct, positioned, direct_unknown, reported_equal = 0, 0, 0, 0, 0
    carried_equal = 0
    for rid, run in enumerate(runs, 1):
        fields(run, 'run_ordinal', 'request_native_turn_scope_matches', 'requests', 'links')
        ordinal(run['run_ordinal'], rid)
        require(run['request_native_turn_scope_matches'] is True)
        requests = array(run['requests'])
        links = array(run['links'])
        require(len(requests) > 1 and len(links) == len(requests) - 1)
        prior_types, prior_slots = [], {}
        for reqno, req in enumerate(requests, 1):
            fields(req, 'ordinal', 'typed_input_count', 'prior_typed_prefix_matches', 'added_types', 'reasoning_slots')
            ordinal(req['ordinal'], reqno)
            added = array(req['added_types'])
            if reqno == 1:
                require(req['prior_typed_prefix_matches'] is None and bool(added) and all(t == 'message' for t in added))
            else:
                require(req['prior_typed_prefix_matches'] is True and added == TRIPLE)
            types = prior_types + added
            ordinal(req['typed_input_count'], len(types))
            slots = {}
            expected = [position for position, kind in enumerate(types, 1) if kind == 'reasoning']
            found = array(req['reasoning_slots'])
            require(len(found) == len(expected))
            for slot, position in zip(found, expected):
                fields(slot, 'position', 'item_id_state', 'field_state', 'utf8_bytes', 'reported_equal_to_prior_slot')
                ordinal(slot['position'], position)
                require(slot['item_id_state'] == 'absent')  # V1 contains no H item IDs.
                slots[position] = field_view(slot)
                if position <= len(prior_types):
                    require(position in prior_slots)
                    equal = equality_report(prior_slots[position], slots[position], slot['reported_equal_to_prior_slot'])
                    carried.append({'run': rid, 'request': reqno, 'prior_request': reqno - 1,
                                    'position': position, 'reported_equal': equal})
                    carried_equal += int(equal is True)
                else:
                    require(slot['reported_equal_to_prior_slot'] is None)
            if reqno > 1:
                w = links[reqno - 2]
                fields(w, 'wire_ordinal', 'next_request_ordinal', 'history_reasoning_position', 'completed_output_types',
                       'ordered_wire_native_typed_item_ids_match', 'unique_adjacent_call_result_link_matches',
                       'wire', 'native', 'reported_equalities')
                ordinal(w['wire_ordinal'], reqno - 1)
                ordinal(w['next_request_ordinal'], reqno)
                fresh = [position for position in expected if position > len(prior_types)]
                require(len(fresh) == 1)
                position = fresh[0]
                ordinal(w['history_reasoning_position'], position)
                require(w['completed_output_types'] == added[:-1] and w['unique_adjacent_call_result_link_matches'] is True
                        and w['ordered_wire_native_typed_item_ids_match'] is True)
                for key in ('wire', 'native'):
                    fields(w[key], 'field_state', 'utf8_bytes')
                wire, native, hist = field_view(w['wire']), field_view(w['native']), slots[position]
                claims = w['reported_equalities']
                fields(claims, *PAIR_KEYS)
                flags = [equality_report(a, b, claims[key]) for key, (a, b) in
                         zip(PAIR_KEYS, ((wire, native), (wire, hist), (native, hist)))]
                # With three strings, exactly two true pairwise flags is contradictory.
                require(sum(flag is True for flag in flags) != 2)
                first.append({'run': rid, 'wire': reqno - 1, 'next_request': reqno, 'position': position,
                              'wire_native_identity': 'reported-typed-id-match',
                              'wire_history_attachment': 'position-only', 'wire_history_direct_identity': 'unknown'})
                first_count += 1
                native_direct += int(w['ordered_wire_native_typed_item_ids_match'] is True)
                positioned += int(position in slots)
                direct_unknown += 1  # Every validated H reasoning slot lacks an item ID.
                reported_equal += int(all(flag is True for flag in flags))
            prior_types, prior_slots = types, slots
    return {'historical_runs': len(runs), 'first_receipt_links': first_count,
            'wire_native_reported_direct_id_links': native_direct, 'history_positional_links': positioned,
            'history_direct_id_unknown_links': direct_unknown, 'first_receipt_all_equal_as_reported': reported_equal,
            'carried_receipts': len(carried), 'carried_equal_as_reported': carried_equal,
            'first_receipt_positions': first, 'carried_positions': carried, 'source_value_equality_recomputed': False}


def self_test(data):
    # All mutations apply only to safe metadata; no original values are available.
    def edit(change):
        copied = deepcopy(data)
        change(copied['runs'][0])
        return copied

    def refused(action):
        try:
            action()
        except Reject:
            return 1
        raise Reject('self-test unexpectedly accepted an inconsistent projection')

    base = summarize(data)
    require((base['historical_runs'], base['first_receipt_links'], base['history_positional_links'],
             base['history_direct_id_unknown_links'], base['carried_receipts']) == (1, 2, 2, 2, 1))
    tests = 1
    for change in (
        lambda run: run['links'][1].update(history_reasoning_position=5),
        lambda run: run['links'][1].update(next_request_ordinal=2),
        lambda run: run['requests'][2].update(prior_typed_prefix_matches=False),
        lambda run: run['links'][1].update(unique_adjacent_call_result_link_matches=False),
        lambda run: run['requests'][2]['reasoning_slots'].pop(0),
        lambda run: run['requests'][1]['reasoning_slots'][0].update(id='unsupported-test-field'),
        lambda run: run['links'][0]['wire'].update(utf8_bytes=37),
        lambda run: run['links'][1]['reported_equalities'].update(wire_history=False),
    ):
        tests += refused(lambda: summarize(edit(change)))
    tests += refused(lambda: load_projection('{"ordinal":1,"ordinal":2}'))
    unequal = summarize(edit(lambda run: run['links'][1]['reported_equalities'].update(wire_history=False, native_history=False)))
    require(unequal['first_receipt_links'] == base['first_receipt_links'] and
            unequal['first_receipt_all_equal_as_reported'] == base['first_receipt_all_equal_as_reported'] - 1)
    tests += 1
    require(field_view({'field_state': 'absent', 'utf8_bytes': None}) !=
            field_view({'field_state': 'null', 'utf8_bytes': None}))
    tests += 1
    return tests


def read_adjacent_projection():
    path = Path(__file__).resolve().with_name('evidence.json')
    cap = 64 * 1024
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as source:
        meta = os.fstat(source.fileno())
        require(stat.S_ISREG(meta.st_mode) and 0 < meta.st_size <= cap)
        data = source.read(cap + 1)
        require(0 < len(data) <= cap)
    return load_projection(data.decode('utf-8', errors='strict'))


def main():
    arguments = sys.argv[1:]
    require(arguments in ([], ['--self-test']))
    projection = read_adjacent_projection()
    result = summarize(projection)
    if arguments:
        result['self_tests_passed'] = self_test(projection)
    print(json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (Reject, OSError, TypeError, UnicodeError, json.JSONDecodeError):
        print('ordinal projection verification failed', file=sys.stderr)
        raise SystemExit(1) from None
