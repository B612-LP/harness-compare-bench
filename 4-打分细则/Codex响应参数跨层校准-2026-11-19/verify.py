#!/usr/bin/env python3
"""Check the fixed public aggregate; does not access or authenticate raw evidence."""
from copy import deepcopy
import json
from pathlib import Path
import sys

META = dict(schema='codex-responses-attachment-aggregate-v1', archived_runs=1,
            new_product_or_model_runs=0, target_calls=1, held_capture_pairs=3,
            independent_internal_reprojection=True, controlled_third_party_reprojection=False,
            full_request_rebuilt=False, universal_format_frozen=False)
FIELDS = dict(response_frames=234, target_output_index=1, added_frame=141,
              argument_delta_frames=90, arguments_done_frame=232, item_done_frame=233,
              completed_frame=234, all_argument_copies_match=True,
              same_native_and_next_request_call_result=True, three_carrier_shapes_distinct=True,
              required_string_parameter='cmd', required_string_present_in_layers=[True] * 3)
REVISION = dict(original_contract_accepted=False, original_cases_retained=10,
                optional_identity_tests_known=4, optional_identity_tests_unknown=10,
                wrong_completion_id_original_status='match', wrong_completion_id_revised_status='unknown_stream',
                independent_wrong_first_delta_id_status='unknown_stream',
                independent_wrong_history_result_status='unknown_attachment',
                unknown_cases_emit_argument_projection=False)
KNOWN = {
    'archived_original': ('match', [255] * 3, [236] * 3, [True] * 3),
    'equivalent_representation_control': ('match', [277, 255, 255], [236] * 3, [True] * 3),
    'different_value_control': ('value_difference', [254, 255, 255], [254, 236, 236], [False, False, True]),
}
UNKNOWN = dict(same_name_other_call='unknown_attachment', genuine_other_capture_meta='unknown_capture_meta',
               missing_argument_boundary='unknown_stream', reordered_argument_boundary='unknown_stream',
               event_kind_disagrees='unknown_stream', unbound_native_call='unknown_attachment',
               incorrect_item_kind='unknown_stream')


def require(ok, code):
    if not ok:
        raise ValueError(code)


def unique(items):
    out = {}
    for key, value in items:
        require(key not in out, 'duplicate_key')
        out[key] = value
    return out


def invalid_constant(_):
    raise ValueError('nonfinite')


def read(path):
    with path.open('rb') as handle:
        raw = handle.read(16384)
    require(len(raw) < 16384, 'too_large')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=invalid_constant)


def equal(a, b):
    if type(a) is not type(b):
        return False
    if type(b) is dict:
        return a.keys() == b.keys() and all(equal(a[k], val) for k, val in b.items())
    if type(b) is list:
        return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
    return a == b


def verify(d):
    req = META.keys() | {'positive', 'argument_checks', 'revision'}
    require(type(d) is dict and d.keys() == req, 'aggregate_shape')
    require(equal({k:d[k] for k in META}, META), 'scope_or_provenance')
    require(equal(d['positive'], FIELDS), 'positive')
    require(equal(d['revision'], REVISION), 'revision')
    schema = ('status','raw_argument_bytes','canonical_object_bytes','same_canonical_value_wn_wh_nh')
    checks = {k:dict(zip(schema, values)) for k, values in KNOWN.items()}
    checks.update({k:{'status':s} for k,s in UNKNOWN.items()})
    require(equal(d['argument_checks'], checks), 'known_and_unknown_results')
    require(d['positive']['arguments_done_frame'] - d['positive']['added_frame'] - 1 == d['positive']['argument_delta_frames'], 'frame_counts')
    return {'verified': 'public_aggregate_only', 'archived_cases': 1,
            'software_cases_base': len(checks)-1,
            'revised_identity_cases': REVISION['optional_identity_tests_known'] + REVISION['optional_identity_tests_unknown'],
            'third_party_original_review': False}


def test(d):
    def row(o):
        return o['argument_checks']['archived_original']
    modifications = [lambda o:o.update(target_calls=True), lambda o:o.update(controlled_third_party_reprojection=True),
                     lambda o:o['positive'].update(completed_frame=233), lambda o:o['positive'].update(target_output_index=True),
                     lambda o:row(o).update(canonical_object_bytes=[255,255,255]),
                     lambda o:o['argument_checks']['same_name_other_call'].update(raw_argument_bytes=[0,0,0]),
                     lambda o:o['argument_checks']['different_value_control'].update(same_canonical_value_wn_wh_nh=[True,False,True]),
                     lambda o:o['revision'].update(wrong_completion_id_revised_status='match'),
                     lambda o:o['revision'].update(unknown_cases_emit_argument_projection=True),
                     lambda o:o.update(native_path='unlisted')]
    for edit in modifications:
        obj = deepcopy(d)
        edit(obj)
        try:
            verify(obj)
        except ValueError:
            continue
        raise ValueError('unexpected_accept')
    try:
        json.loads('{"x":1,"x":1}',object_pairs_hook=unique)
    except ValueError:
        return len(modifications)+1
    raise ValueError('unexpected_duplicate_accept')


def main():
    require(sys.argv[1:] in ([], ['--self-test']), 'usage: verify.py [--self-test]')
    data = read(Path(__file__).resolve().with_name('evidence.json'))
    result = verify(data)
    if sys.argv[1:]:
        result['public_aggregate_negative_controls_rejected'] = test(data)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, UnicodeError, KeyError, TypeError) as ex:
        print('verification failed: '+type(ex).__name__, file=sys.stderr)
        raise SystemExit(1)
