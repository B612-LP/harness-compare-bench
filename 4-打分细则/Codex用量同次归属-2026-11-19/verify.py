#!/usr/bin/env python3
"""Recompute one fixed public aggregate, not its private source attachments."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

LABELS = ['input', 'cached_input', 'output', 'reasoning_output', 'total']
FRAMES = [234, 115, 46]
EXPECTED = [[8117, 4608, 348, 133, 8465], [8533, 8320, 229, 4, 8762], [8821, 8576, 34, 25, 8855]]
DIRECT = 'direct_response_id'
STRUCTURAL = 'structural_no_response_id'


class Invalid(ValueError):
    pass


def need(yes, code):
    if not yes:
        raise Invalid(code)


def unique(pairs):
    result = {}
    for name, value in pairs:
        need(name not in result, 'duplicate_key')
        result[name] = value
    return result


def reject_constant(_):
    raise Invalid('invalid_json_constant')


def strict_load(raw):
    need(len(raw) <= 65536, 'input_size')
    return json.loads(raw.decode('utf-8', errors='strict'), object_pairs_hook=unique, parse_constant=reject_constant)


def exact_keys(obj, keys):
    need(type(obj) is dict and set(obj) == set(keys.split()), 'unexpected_object_keys')


def typed_same(left, right):
    if type(left) is not type(right):
        return False
    if type(right) is list:
        return len(left) == len(right) and all(typed_same(a, b) for a, b in zip(left, right))
    return left == right


def vector(item):
    need(type(item) is list and len(item) == 5 and all(type(x) is int and x >= 0 for x in item), 'invalid_count_vector')
    i, c, o, r, t = item
    need(c <= i and r <= o and t == i + o, 'invalid_count_arithmetic')
    return item


def prefix(rows):
    out, latest = [], [0] * 5
    for row in rows:
        latest = [a + b for a, b in zip(latest, row)]
        out.append(latest)
    return out


def validate(doc):
    exact_keys(doc, 'schema scope count_labels responses synthetic_controls limits')
    need(doc['schema'] == 'codex-bounded-usage-bridge.public.v1' and doc['scope'] == 'one_historical_session_three_bound_responses', 'release_scope')
    need(typed_same(doc['count_labels'], LABELS), 'count_columns')
    rows = doc['responses']
    need(type(rows) is list and len(rows) == 3, 'response_coverage')
    w, n, ml, mp = [], [], [], []
    for i, row in enumerate(rows, 1):
        exact_keys(row, 'ordinal frames wire native_primary native_mirror_last native_mirror_prefix main_link mirror_link wire_cache_write native_cache_write')
        need(typed_same(row['ordinal'], i) and typed_same(row['frames'], FRAMES[i - 1]), 'response_order_or_frames')
        w.append(vector(row['wire']))
        n.append(vector(row['native_primary']))
        ml.append(vector(row['native_mirror_last']))
        mp.append(vector(row['native_mirror_prefix']))
        need(row['main_link'] == DIRECT and row['mirror_link'] == STRUCTURAL, 'attachment_class')
        need(row['wire_cache_write'] is None and typed_same(row['native_cache_write'], 0), 'missing_is_not_zero')
    need(w == n == ml, 'single_response_counts_disagree')
    computed = prefix(w)
    need(mp == computed == prefix(n), 'prefix_counts_disagree')
    need(w == EXPECTED, 'different_release_values')
    controls = doc['synthetic_controls']
    exact_keys(controls, 'swap_first_two_response_values equal_counter_mirror_wrong_thread wrong_final_message_phase_not_fully_gated')
    swap, wrong = controls['swap_first_two_response_values'], controls['equal_counter_mirror_wrong_thread']
    exact_keys(swap, 'main_links_stay_direct prefix_equal_by_position')
    exact_keys(wrong, 'main_links_stay_direct mirror_links_by_position')
    swapped = prefix([w[1], w[0], w[2]])
    need(swap['main_links_stay_direct'] is True and typed_same(swap['prefix_equal_by_position'], [a == b for a, b in zip(swapped, mp)]), 'swap_counterexample')
    need(wrong['main_links_stay_direct'] is True and typed_same(wrong['mirror_links_by_position'], [STRUCTURAL, 'unknown', STRUCTURAL]), 'wrong_thread_counterexample')
    need(controls['wrong_final_message_phase_not_fully_gated'] is True, 'phase_limitation')
    limits = doc['limits']
    exact_keys(limits, 'new_product_or_model_runs public_raw_authentication controlled_third_party_raw_review estimated_provider_cost')
    need(typed_same(limits['new_product_or_model_runs'], 0) and all(limits[k] is False for k in limits if k != 'new_product_or_model_runs'), 'scope_boundary')
    return {'response_count': len(rows), 'direct_main_records': len(n), 'structural_mirror_rows': len(ml),
            'extra_mirror_responses': 0, 'equal_response_fields': 15, 'equal_prefix_fields': 15,
            'sum_per_surface': computed[-1], 'swap_prefix_equal_by_position': swap['prefix_equal_by_position'],
            'public_raw_authentication': False}


def tests(doc):
    def cases():
        for key, value in [('ordinal', True), ('frames', 235), ('wire_cache_write', 0), ('native_cache_write', False), ('mirror_link', DIRECT)]:
            d = deepcopy(doc); d['responses'][0][key] = value; yield d
        d = deepcopy(doc); d['responses'][0]['wire'][3] = 134; yield d
        d = deepcopy(doc); d['responses'][1]['native_mirror_prefix'] = d['responses'][0]['native_mirror_prefix']; yield d
        d = deepcopy(doc); d['responses'][0]['extra_metadata'] = 'synthetic'; yield d
        d = deepcopy(doc); d['synthetic_controls']['swap_first_two_response_values']['prefix_equal_by_position'] = [True, True, True]; yield d
        d = deepcopy(doc); d['synthetic_controls']['equal_counter_mirror_wrong_thread']['mirror_links_by_position'][1] = STRUCTURAL; yield d
        d = deepcopy(doc); d['synthetic_controls']['wrong_final_message_phase_not_fully_gated'] = False; yield d
        d = deepcopy(doc); d['limits']['controlled_third_party_raw_review'] = True; yield d
        d = deepcopy(doc)
        for key in ('wire', 'native_primary', 'native_mirror_last'):
            d['responses'][0][key][3] += 1
        for row in d['responses']:
            row['native_mirror_prefix'][3] += 1
        yield d
    num = 0
    for bad in cases():
        try:
            validate(bad)
        except Invalid:
            num += 1
        else:
            raise Invalid('mutation_not_rejected')
    try:
        strict_load(b'{"name":0,"name":0}')
    except Invalid:
        return num + 1
    raise Invalid('duplicate_not_rejected')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    try:
        doc = strict_load(Path(__file__).absolute().with_name('evidence.json').read_bytes())
        result = validate(doc)
        if args.self_test:
            result['negative_self_tests'] = tests(doc)
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        raise SystemExit(str(exc) if isinstance(exc, Invalid) else 'unreadable_public_aggregate') from None
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
