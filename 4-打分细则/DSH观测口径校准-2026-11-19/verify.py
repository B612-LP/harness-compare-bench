#!/usr/bin/env python3
"""Check public projection consistency only; cannot verify or open raw sources."""
import argparse
import copy
import json
from pathlib import Path


class Disagreement(ValueError):
    pass


def need(condition, reason):
    if not condition:
        raise Disagreement(reason)


def no_duplicates(pairs):
    row = {}
    for k, v in pairs:
        need(k not in row, 'duplicate key')
        row[k] = v
    return row


def finite_int_only(_):
    raise Disagreement('invalid number type')


def count(v):
    return type(v) is int and v >= 0


def countvec(v, n):
    return type(v) is list and len(v) == n and all(count(x) for x in v)


def positivevec(v, n):
    return countvec(v, n) and min(v) > 0


def ratio(v):
    return countvec(v, 2) and 0 <= v[0] <= v[1]


OBJECT_KEYS = {
    (): 'profile scope E_pos E_nat E_miss paired_runs controls historical_main_gate_unchanged number_profile_cross_impl_equivalence',
    ('scope',): 'source new_product_or_model_runs formal_cells_changed universal_format_frozen controlled_external_raw_review_completed raw_chain_publicly_reprojectable harness_intervention_identified',
    ('E_pos',): 'raw_container_bytes zstd_frames decoded_ndjson_bytes event_rows event_family_counts event_family_canonical_bytes events_canonical_bytes structurally_closed_steps requests_in_capture_order captured_request_body_bytes selected_task_messages_matched_total local_calls_results selected_declarations_matched_in_each_task_request declaration_field_only_in_capture main_adapter_keys_unreconstructed full_requests_reconstructed_from_log',
    ('E_nat',): 'layer_order argument_fragments tool_finish_frame done_frame required_key required_key_states complete_nonempty_objects raw_argument_utf8_bytes canonical_argument_bytes raw_arguments_identical canonical_arguments_identical local_result_is_error local_and_history_result_text_bytes local_and_history_result_text_identical',
    ('E_miss',): 'raw_container_bytes zstd_frames decoded_ndjson_bytes event_rows events_canonical_bytes structurally_closed_steps captured_request_body_bytes wire_status',
    ('paired_runs',): 'paired_units pre_assistant_whole_rows_different_total pre_assistant_data_rows_different_total input_whole_rows_different_total input_data_rows_different_total input_data_difference_is_id_only input_whole_canonical_bytes_by_arm input_data_canonical_bytes_by_arm generated_title_json_string_bytes_by_arm capture_bytes_by_arm_and_request cross_arm_request_raw_equal first_tool_names_by_arm first_tool_missing_required_keys_by_arm first_tool_local_result_is_error_by_arm first_tool_argument_bytes_by_arm first_tool_result_text_bytes_by_arm first_body_alone_authenticates_arm',
    ('controls',): 'same_source_log_recoding same_source_zstd_reframing same_value_request_recoding same_size_selected_user_change invalid_log_or_binding_fixtures known_success_steps_delta natural_failure_delta paired_delta unclosed_source_tag_fixture unclosed_terminal_wrapper_fixture',
    ('controls','same_source_log_recoding'): 'same_carrier_bytes same_canonical_event_values same_selected_projection',
    ('controls','same_source_zstd_reframing'): 'frames_before_after same_carrier_bytes same_canonical_event_values same_selected_projection',
    ('controls','same_value_request_recoding'): 'same_capture_bytes same_json_value as_original_capture',
    ('controls','same_size_selected_user_change'): 'same_decoded_and_canonical_size same_event_values task_matches_initial_modified title_projection_unchanged',
    ('controls','invalid_log_or_binding_fixtures'): 'damaged_or_invalid_log wrong_aux_or_meta wrong_step_or_call',
    ('controls','known_success_steps_delta'): 'missing_result_after_resequence wrong_inner_call missing_assistant',
    ('controls','natural_failure_delta'): 'wrong_inner_result_call_id wrong_entire_stream_response_id',
    ('controls','paired_delta'): 'wrong_entire_stream_response_id wrong_title_effort missing_local_replay_marker',
    ('controls','unclosed_source_tag_fixture'): 'required observed applies_to',
    ('controls','unclosed_terminal_wrapper_fixture'): 'required observed applies_to',
    ('historical_main_gate_unchanged',): 'fails unverifiable',
    ('number_profile_cross_impl_equivalence',): 'reference payloads byte_equal bounds_diverge docs ring',
}


def check_object_keys(value, path=()):
    fields = OBJECT_KEYS.get(path)
    if fields is not None:
        need(type(value) is dict and set(value) == set(fields.split()), 'public object keys')
        for name in value:
            check_object_keys(value[name], path+(name,))
    elif type(value) is list:
        for item in value:
            check_object_keys(item,path+('[]',))
    else:
        need(type(value) in (type(None),str,bool,int), 'public scalar type')


def load(path):
    raw = path.read_bytes()
    need(0 < len(raw) < 65536, 'public file size')
    return json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=no_duplicates,
                      parse_constant=finite_int_only, parse_float=finite_int_only)


def check(d):
    check_object_keys(d)
    need(d['profile'] == 'dsh-v4-observation-trial-0.3', 'profile')
    s = d['scope']
    need(s['source'] == 'private_held_originals_public_aggregates_only', 'source scope')
    need(all(s[n] is False for n in ('universal_format_frozen','controlled_external_raw_review_completed',
          'raw_chain_publicly_reprojectable','harness_intervention_identified')), 'not an external, raw or causal check')
    need(all(count(s[k]) and s[k] == 0 for k in ('new_product_or_model_runs','formal_cells_changed')), 'not a product launch or rescore')
    a,b,c,p,t = [d[k] for k in ('E_pos','E_nat','E_miss','paired_runs','controls')]
    for log in (a,c):
        fields = [log[k] for k in ('event_rows','decoded_ndjson_bytes','events_canonical_bytes','zstd_frames','raw_container_bytes','structurally_closed_steps')]
        need(all(count(x) and x > 0 for x in fields), 'event layer counts')
        need(fields[0]>fields[5] and fields[0]>=fields[3] and fields[1]>fields[2], 'held event arithmetic')
    need(countvec(a['event_family_counts'],3) and sum(a['event_family_counts']) == a['event_rows'], 'event count sum')
    need(countvec(a['event_family_canonical_bytes'],3) and sum(a['event_family_canonical_bytes']) == a['events_canonical_bytes'], 'event byte sum')
    need(a['requests_in_capture_order'] == ['first_main','title_aux','next_main'] and positivevec(a['captured_request_body_bytes'],3), 'A request strata')
    am = a['selected_task_messages_matched_total']; ad = a['selected_declarations_matched_in_each_task_request']
    need(ratio(am) and am == [8,8] and a['local_calls_results']==[2,2], 'A selected observations')
    need(type(ad) is list and all(ratio(r) for r in ad) and ad==[[22,22],[22,22]], 'A declaration denominators')
    need(a['declaration_field_only_in_capture']=='strict' and a['main_adapter_keys_unreconstructed']==['stream','stream_options','thinking','tool_stream']
         and count(a['full_requests_reconstructed_from_log']) and a['full_requests_reconstructed_from_log']==0, 'A incomplete full reconstruction')
    need(b['layer_order']==['captured_response','local_event','next_main_history'], 'B layers')
    frames=[b[k] for k in ('argument_fragments','tool_finish_frame','done_frame')]
    need(all(count(x) for x in frames) and 0 < frames[0] < frames[1] == frames[2]-1, 'B frames')
    need(b['required_key']=='command' and b['required_key_states']==['absent']*3 and len(b['complete_nonempty_objects'])==3
         and all(x is True for x in b['complete_nonempty_objects']), 'B complete missing-required-key observation')
    for key, same in [('raw_argument_utf8_bytes','raw_arguments_identical'),
                      ('canonical_argument_bytes','canonical_arguments_identical')]:
        v=b[key]
        need(countvec(v,3) and v == [85]*3 and b[same] is True, 'B projected parameter equality')
    need(b['local_result_is_error'] is True and countvec(b['local_and_history_result_text_bytes'],2) and
         b['local_and_history_result_text_bytes']==[61,61] and b['local_and_history_result_text_identical'] is True, 'B result link')
    need(c['captured_request_body_bytes'] is None and c['wire_status']=='unknown_no_matching_source', 'C missing W is null')
    need(count(p['paired_units']) and p['paired_units']==1 and p['first_body_alone_authenticates_arm'] is False, 'paired scope')
    n=[p[k] for k in ('pre_assistant_whole_rows_different_total','pre_assistant_data_rows_different_total',
                       'input_whole_rows_different_total','input_data_rows_different_total')]
    need(all(ratio(x) for x in n), 'paired denominators')
    need(n[1][1]+1==n[0][1] and n[2][1]==n[3][1]<=n[1][1] and n[3][0] < n[1][0]
         and n[1][0]<=n[0][0] and n[3][0]<=n[2][0] and p['input_data_difference_is_id_only'] is True, 'paired nested scopes')
    i1=p['input_whole_canonical_bytes_by_arm']; i2=p['input_data_canonical_bytes_by_arm']; title=p['generated_title_json_string_bytes_by_arm']
    need(all(countvec(x,2) for x in (i1,i2,title)) and i1[0]==i1[1]>i2[0]==i2[1]>0 and 2<=min(title)<max(title), 'paired preamble sizes')
    arm=p['capture_bytes_by_arm_and_request']; equal=p['cross_arm_request_raw_equal']
    need(type(arm) is list and len(arm)==2 and all(positivevec(x,3) for x in arm), 'paired request counts')
    need(len(equal)==3 and equal[0] is True and equal[1] is True and equal[2] is False, 'paired raw equality')
    need(all(x==y for x,y in zip(arm[0][:2],arm[1][:2])) and arm[0][2]!=arm[1][2], 'paired request size relation')
    errors=p['first_tool_local_result_is_error_by_arm']; args=p['first_tool_argument_bytes_by_arm']; result=p['first_tool_result_text_bytes_by_arm']
    need(p['first_tool_names_by_arm']==['bash','read'] and p['first_tool_missing_required_keys_by_arm']==[[b['required_key']],[]]
         and len(errors)==2 and errors[0] is b['local_result_is_error'] and errors[1] is False, 'paired first branch')
    need(countvec(args,2) and countvec(result,2) and args[0]==b['raw_argument_utf8_bytes'][0] and
         result[0]==b['local_and_history_result_text_bytes'][0] and min(args+result)>0, 'paired B linkage')
    for name in ('same_source_log_recoding','same_source_zstd_reframing'):
        v=t[name]; need(v['same_carrier_bytes'] is False and v['same_canonical_event_values'] is True and
                        v['same_selected_projection'] is True, 'equivalent logs')
    rf=t['same_source_zstd_reframing']['frames_before_after']
    need(countvec(rf,2) and rf[0]==a['zstd_frames'] and rf[1]==1, 'reframing counts')
    w=t['same_value_request_recoding']; ch=t['same_size_selected_user_change']
    need(w['same_capture_bytes'] is False and w['same_json_value'] is True and w['as_original_capture']=='unknown', 'equivalent JSON, different raw identity')
    need(ch['same_decoded_and_canonical_size'] is True and ch['same_event_values'] is False and
         ch['title_projection_unchanged'] is True and ch['task_matches_initial_modified']==[am[0],am[0]-1], 'same-size content differs')
    for name, keys in [('invalid_log_or_binding_fixtures',('damaged_or_invalid_log','wrong_aux_or_meta','wrong_step_or_call')),
                       ('natural_failure_delta',('wrong_inner_result_call_id','wrong_entire_stream_response_id')),
                       ('paired_delta',('wrong_entire_stream_response_id','wrong_title_effort','missing_local_replay_marker'))]:
        need(all(t[name][k]=='unknown' for k in keys), 'unknown at failed identity/completeness')
    need(all(t['known_success_steps_delta'][k]==['L1_available',None] for k in
             ('missing_result_after_resequence','wrong_inner_call','missing_assistant')), 'valid lower layer does not fill higher layer')
    for key, layer in [('unclosed_source_tag_fixture','natural_failure_delta'),
                       ('unclosed_terminal_wrapper_fixture','paired_delta')]:
        need(t[key]=={'required':'unknown','observed':'known','applies_to':layer}, 'retain unresolved fixture')
    need(d['historical_main_gate_unchanged']=={'fails':6,'unverifiable':4}, 'old gate unchanged')
    eq=d['number_profile_cross_impl_equivalence']
    need(eq=={'reference':'number-profile-candidate-v1','payloads':9923,'byte_equal':True,'bounds_diverge':True,'docs':130,'ring':'r115-number-equivalence-2026-11-23'}, 'number profile equivalence')
    return {'public_projection_consistent':True,'independent_raw_recheck_possible_here':False,
            'universal_format_frozen':False,'paired_units':p['paired_units']}


def mutations(base):
    probes = (
        (('scope','controlled_external_raw_review_completed'),True),
        (('E_pos','extra'), 'unexpected datum'),
        (('controls','same_source_log_recoding','extra'), 'unexpected nested datum'),
        (('E_pos','captured_request_body_bytes'),[0,1042,34107]),
        (('paired_runs','capture_bytes_by_arm_and_request'),[[0,888,33319],[0,888,33797]]),
        (('E_pos','event_family_counts'),[9,12,7]),
        (('E_nat','required_key_states'),['present','absent','absent']),
        (('E_miss','captured_request_body_bytes'),0),
        (('number_profile_cross_impl_equivalence','payloads'),9922),
        (('number_profile_cross_impl_equivalence','byte_equal'),False),
        (('paired_runs','capture_bytes_by_arm_and_request'),[[32937,888,33319],[32938,888,33797]]),
        (('paired_runs','first_body_alone_authenticates_arm'),True),
        (('controls','same_size_selected_user_change','same_event_values'),True),
        (('controls','known_success_steps_delta','wrong_inner_call'),['L1_available',True]),
        (('controls','unclosed_source_tag_fixture','observed'),'unknown'),
        (('historical_main_gate_unchanged','fails'),0),
    )
    for path,value in probes:
        obj = copy.deepcopy(base); slot=obj
        for key in path[:-1]:
            slot=slot[key]
        slot[path[-1]]=value
        try:
            check(obj)
        except Disagreement:
            continue
        raise Disagreement('public negative accepted: ' + '.'.join(path))
    return len(probes)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--self-test',action='store_true')
    a=p.parse_args()
    try:
        d=load(Path(__file__).with_name('evidence.json')); out=check(d)
        if a.self_test:
            out['public_negative_checks_rejected']=mutations(d)
    except (ValueError,KeyError,TypeError,IndexError,OSError,RecursionError) as e:
        print(json.dumps({'public_projection_consistent':False,'error':str(e)}))
        raise SystemExit(1)
    print(json.dumps(out,sort_keys=True))


if __name__=='__main__':
    main()
