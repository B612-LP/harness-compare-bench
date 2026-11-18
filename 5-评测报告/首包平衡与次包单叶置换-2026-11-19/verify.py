#!/usr/bin/env python3
"""Verify the published six-pair aggregate only, not the private records."""
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
PAIR = {'pair','req1','directions'}
FIRST = {'raw_equal','canonical_equal','historical_selected_input_equal',
         'recorded_controls_equal_except_cap','thinking_config_equal'}
DELTA = ('raw_total_delta','canonical_total_delta','tool_json_delta','tool_utf8_delta',
         'bound_id_delta','proven_req1_response_delta','extra_non_id_delta')
CLOSE = ('tool_only_exact','tool_plus_ids_exact','tool_ids_response_exact')
COUNTS = {'tool_text','bound_ids','signature','visible_thinking','extra_non_id'}
CASES = {'same_bound_tool_value','equivalent_encoding','equal_length_non_tool',
         'same_length_wrong_attachment','independent_equal_length_signature_wrong_source'}
DIRECTIONS = ('inline_to_bounded','bounded_to_inline')
META = {'schema':'dsh-confirm-request-body-aggregate-v1','source':'historical_2026-11-03_confirm_6_pairs',
        'source_objects_matched_postrun_manifest':180,'bound_slots':12,'postrun_control_receipts':12,
        'new_product_or_model_runs':0,'internal_nonauthor_original_review':True,'controlled_third_party_review':False}
PIN = [(0,0,0),(6,-19,1),(6,-19,1),(0,0,0),(0,0,0),(6,-180,1)]


def need(ok, name):
    if not ok:
        raise ValueError(name)


def keys(obj, allowed, stage):
    need(type(obj) is dict and obj.keys()==set(allowed),stage)


def unique(items):
    obj={}
    for k,v in items:
        need(k not in obj,'duplicate_key')
        obj[k]=v
    return obj


def invalid_constant(_):
    raise ValueError('nonfinite')


def read_report():
    raw=(ROOT/'evidence.json').read_bytes()
    need(len(raw)<64*1024,'aggregate_size')
    return json.loads(raw.decode('utf-8','strict'),object_pairs_hook=unique,parse_constant=invalid_constant)


def verify(d):
    keys(d, META.keys() | {'pairs','counterexamples'}, 'top_keys')
    need(all(type(d[k]) is type(v) and d[k]==v for k,v in META.items()),'provenance_or_scope')
    keys(d['counterexamples'],CASES,'calibration_keys')
    need(all(x is True for x in d['counterexamples'].values()),'calibration_result')
    pairs=d['pairs']; need(type(pairs) is list and len(pairs)==6,'pair_count')
    zero_value_differ=0
    for n,(pair,(ids,replay,text)) in enumerate(zip(pairs,PIN),1):
        keys(pair,PAIR,'pair_keys'); need(pair['pair']==f'b{n:02}','pair_id')
        keys(pair['req1'],FIRST,'req1_keys'); need(all(v is True for v in pair['req1'].values()),'req1_result')
        keys(pair['directions'],DIRECTIONS,'direction_keys')
        for name, sign in zip(DIRECTIONS,(1,-1)):
            v=pair['directions'][name]
            keys(v,set(DELTA)|set(CLOSE)|{'changed_field_counts'},'direction_fields')
            need(all(type(v[k]) is int for k in DELTA),'delta_type')
            need([v[k] for k in DELTA[2:]]==[sign*x for x in (-34181,-33786,ids,replay,0)],'direction_values')
            need(v['raw_total_delta']==v['canonical_total_delta']==sum(v[k] for k in ('tool_json_delta','bound_id_delta','proven_req1_response_delta','extra_non_id_delta')),'byte_balance')
            need(v[CLOSE[0]] is False and v[CLOSE[1]] is False and v[CLOSE[2]] is True,'value_closure')
            c=v['changed_field_counts']; keys(c,COUNTS,'change_fields')
            need(all(type(x) is int for x in c.values()) and c==dict(zip(('tool_text','bound_ids','signature','visible_thinking','extra_non_id'),(1,2,1,text,0))),'change_count')
            if sign==1 and v['canonical_total_delta']==v['tool_json_delta'] and v[CLOSE[0]] is False:
                zero_value_differ+=1
    need(zero_value_differ==3,'equal_size_not_value')
    return {'pairs':len(pairs),'req1_raw_and_canonical_equal_pairs':6,
            'closure_pairs_by_step':[0,0,6],'zero_residual_bytes_but_value_unequal_pairs':zero_value_differ}


def controls(d):
    def direct(x):
        return x['pairs'][0]['directions']['inline_to_bounded']
    tests=[lambda x:x.update(new_product_or_model_runs=False),lambda x:x.update(controlled_third_party_review=True),
           lambda x:x['pairs'].append(x['pairs'][0]),lambda x:x['pairs'][0]['req1'].update(raw_equal=False),
           lambda x:direct(x).update(tool_only_exact=True),lambda x:direct(x).update(raw_total_delta=-34182),
           lambda x:direct(x)['changed_field_counts'].update(signature=0),lambda x:direct(x).update(payload='x'),
           lambda x:x['pairs'][0]['directions']['bounded_to_inline'].update(bound_id_delta=1),
           lambda x:x['counterexamples'].update(independent_equal_length_signature_wrong_source=False)]
    for mutate in tests:
        copied=deepcopy(d); mutate(copied)
        try:
            verify(copied)
        except ValueError:
            continue
        raise ValueError('accepted_wrong_aggregate')
    try:
        json.loads('{"x":1,"x":2}',object_pairs_hook=unique)
    except ValueError:
        return len(tests)+1
    raise ValueError('accepted_duplicate')


def main(args):
    need(args in ([],['--self-test']),'usage: verify.py [--self-test]')
    d=read_report(); result=verify(d)
    if args:
        result['aggregate_negative_controls_rejected']=controls(d)
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':
    try:
        main(sys.argv[1:])
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as ex:
        print('aggregate verification failed: '+type(ex).__name__,file=sys.stderr)
        raise SystemExit(1)
