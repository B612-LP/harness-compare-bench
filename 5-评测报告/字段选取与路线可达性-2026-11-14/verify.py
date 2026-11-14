"""Portable selected-evidence consistency verifier; not a private-raw authenticator."""
import hashlib,json,re,stat
from pathlib import Path
BASELINE='b611abcd9a5374940cfc7f0551c16935e95162dfe07c66f7e4aab08701f804e0'
SCIENCE_FINAL='66ca6a4a9fb4694d471cb1be1d9bcad5a296dff12431d3b2fbbb350e66e24c19'
SCIENCE_REPORT='668d12550ad914f5bf329ab1c46ee8b1baccedd2241ae592b235be2b0d4e0323'
SOURCES={'A':'11104026259b14aa512c6c69f6e7f14f8ac099ebe6e0b99f61b06bb00ea41d6d','B':'65d51423026971f1b0695721f5d78d6aca404a733e8bf822469edaf924295b57'}
ROOT_FILES={'README.md','evidence.json','verify.py','test_verify.py','SHA256SUMS.json'}
FILES=ROOT_FILES|{'sources/A.txt','sources/B.txt','outputs/A.txt','outputs/B.txt'}
PATTERN='TARGET=[0-9a-f]{64}'
def need(ok,reason):
    if not ok:raise ValueError(reason)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def parse(raw):
    def pairs(items):
        d={}
        for k,v in items:need(k not in d,'duplicate_key');d[k]=v
        return d
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:need(False,'nonfinite_json'))
def keys(value,names,label):need(type(value) is dict and set(value)==set(names),label)
def integer(value,want,label):need(type(value) is int and value==want,label)
def hash_value(value,label):need(type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None,label)
def privacy(raw):
    text=raw.decode('utf-8');forbidden=('/'+'Users/','/'+'home/','bench'+'-private','b612'+'-lp')
    need(not any(s in text for s in forbidden) and re.search('session'+'-[0-9a-f]{8}-',text) is None and re.search('field'+'[0-9]{4}_c[0-9]+',text) is None,'private_identity_or_path')
def end_witness(value):
    keys(value,('completed','exit_code','timeout','failure','logs_withheld','native_identity_verified','upstream_forwards','never_resubmit','not_global_runtime_attestation','launch_failure','cleanup_attempts','owned_group_cleanup'),'end_fields')
    for k in ('completed','native_identity_verified','never_resubmit','not_global_runtime_attestation'):need(value[k] is True,'end_'+k)
    for k in ('timeout','logs_withheld'):need(value[k] is False,'end_'+k)
    for k in ('failure','launch_failure'):need(value[k] is None,'end_'+k)
    integer(value['exit_code'],0,'outer_exit');integer(value['upstream_forwards'],0,'forward');integer(value['cleanup_attempts'],1,'cleanup_attempts')
    cleanup=value['owned_group_cleanup'];keys(cleanup,('start_new_session','state','events','scope'),'owned_group_fields');need(cleanup['start_new_session'] is True and cleanup['state']=='absent' and cleanup['scope']=='one_owned_group_token_not_all_processes','owned_group_scope')
    need(type(cleanup['events']) is list and 1<=len(cleanup['events'])<=64,'owned_group_events')
    absence=False
    for event in cleanup['events']:
        keys(event,('signal','result'),'owned_group_event');need(type(event['signal']) is int and event['signal'] in (0,15,9) and event['result'] in ('present','sent','absent'),'owned_group_event_value');absence|=event['result']=='absent'
    need(absence,'absence_witness_missing')
    need(cleanup['events'][-1]['result']=='absent','final_owned_group_absence_witness')
def verify(data,files):
    keys(data,('schema','provenance','design','counts','requests','ends','observations','limits'),'evidence_schema');need(data['schema']=='field-selection-selected-v1','schema_no_downgrade')
    need(sha(canonical(data))==BASELINE,'public_consistency_commitment_not_raw_authentication')
    p=data['provenance'];keys(p,('kind','original_raw_authenticated_by_public_package','science_verdict','science_final_sha256','science_report_sha256','root_seal_sha256','execution_seal_sha256','analysis_seal_sha256','actual_analysis_sha256'),'provenance')
    need(p['kind']=='selected_safe_derivative' and p['original_raw_authenticated_by_public_package'] is False and p['science_verdict']=='finite_PASS','provenance_scope')
    for k,v in p.items():
        if k.endswith('_sha256'):hash_value(v,k)
    need(p['root_seal_sha256']=='973ed145c293b752426c16dc58ef5a5b4cc465d02605d23f2b36473667b5a11e' and p['execution_seal_sha256']=='73bb160c3109d85402bb1305d5dee06ca0cb0132854b4dd4129305524a5cbebc' and p['analysis_seal_sha256']=='f0a0b66f20f59f29a7eb67040f0c3132976241f6ba5be6e72b6ae59a854ea7de','sealed_lineage')
    need(p['science_final_sha256']==SCIENCE_FINAL and p['science_report_sha256']==SCIENCE_REPORT and p['actual_analysis_sha256']=='33b4283b78ed1988e1de43feebaaa14cbf97a7c961ebf54fd72a589254ac0356','final_science_and_actual_analysis_binding')
    design={'pattern':PATTERN,'route':'controller_fixed_native_bash','agent_strategy_tested':False,'system_still_recommends_grep_not_shell':True,'permissions':'workspace-write/ask','native_caps_defaults_preserved':True,'tool_names':['bash','edit','glob','grep','read','read_image','write'],'previous_tool_names':['packet_a','packet_b','edit','glob','grep','read','read_image','write'],'fully_equally_controlled_against_previous_route':False,'field_bytes_interval':[8000,8071],'known_pair_differing_byte':8007,'reachable_outcomes':'two_complete_correct_fields_or_unknown_only','valid_zero_or_one_counterbranch_covered':False}
    need(canonical(data['design'])==canonical(design),'route_design_or_reachability')
    counts={'catalog_sessions':1,'confirm_scientific_sessions':1,'fresh_sessions':2,'local_requests':4,'bash_calls':2,'fixture_calls':0,'real_model_calls':0,'upstream_forwards':0,'fully_validated_result_rows':2,'observed_bash_operations':2,'complete_fields':2}
    need(canonical(data['counts'])==canonical(counts),'typed_counts')
    limits={'decoded_text_bytes_not_http_bytes':True,'numeric_inner_exit_code_observed':False,'inner_exit_code':None,'inner_state':'renderer_inferred_zero','native_completed_or_outer_zero_proves_inner_numeric':False,'independent_repeats':False,'known_candidate_bit_suffices_with_mapping':True,'unknown_256_bit_increment_measured':False,'whole_context_indistinguishability':False,'general_recovery_or_ranking_claim':False,'old_read_and_grep_local_limits_revoked':False,'original_raw_not_publicly_authenticated':True}
    need(canonical(data['limits'])==canonical(limits),'scientific_scope_or_inner_state')
    ends=data['ends'];keys(ends,('catalog','confirm'),'two_session_ends')
    for value in ends.values():end_witness(value)
    requests=data['requests'];need(type(requests) is list and len(requests)==4,'request_coverage')
    for q,(slot,ordinal) in zip(requests,(('catalog',1),('confirm',1),('confirm',2),('confirm',3))):
        keys(q,('slot','ordinal','raw_request_body_bytes','raw_request_sha256','formatted_json_file_sha256','canonical_json_value_sha256','response_sse_sha256'),'request_commitment_columns');need(q['slot']==slot,'request_order');integer(q['ordinal'],ordinal,'request_ordinal');need(type(q['raw_request_body_bytes']) is int and q['raw_request_body_bytes']>72,'request_body_not_result_text')
        for k,v in q.items():
            if k.endswith('_sha256'):hash_value(v,k)
        need(q['raw_request_sha256']!=q['formatted_json_file_sha256'],'raw_formatted_columns_distinct')
    rows=data['observations'];need(type(rows) is list and len(rows)==2,'two_rows')
    for i,(sid,row) in enumerate(zip(('A','B'),rows),1):
        keys(row,('source_id','source_file','source_original_sha256','source_derived_sha256','source_transform','result_file','decoded_text_bytes','result_original_text_sha256','result_derived_text_sha256','call_id','original_call_id_sha256','source_path_alias','original_source_path_sha256','original_source_path_utf8_bytes','arguments','original_arguments_sha256','derived_arguments_sha256','original_wire_block_sha256','wire_block','wire_position','original_native_event_sha256','native_event','source_unchanged','complete_field','numeric_inner_exit_code_observed','inner_exit_code','renderer_inferred_zero'),'row_fields')
        need(row['source_id']==sid and row['source_file']=='sources/'+sid+'.txt' and row['result_file']=='outputs/'+sid+'.txt','source_route')
        raw=files[row['source_file']];need(len(raw)==16000 and raw.isascii() and b'\n' not in raw and b'\r' not in raw and sha(raw)==SOURCES[sid],'actual_source_bytes')
        need(row['source_original_sha256']==row['source_derived_sha256']==sha(raw) and row['source_transform']=='safe_synthetic_bytes_unchanged','source_original_derived_binding')
        matches=re.findall(PATTERN.encode(),raw);need(len(matches)==1 and raw[8000:8071]==matches[0],'source_field_geometry');answer=matches[0]+b'\n';text=files[row['result_file']];need(text==answer and len(text)==72,'actual_disk_decoded_field_and_LF');integer(row['decoded_text_bytes'],72,'decoded_72_not_HTTP')
        need(row['result_original_text_sha256']==row['result_derived_text_sha256']==sha(text),'unchanged_text_hashes')
        cid='call-%07d'%i;need(row['call_id']==cid,'call_alias_unique_order');hash_value(row['original_call_id_sha256'],'original_call_commitment')
        alias=row['source_path_alias'];need(type(alias) is str and alias.startswith('source/'+sid+'/') and re.fullmatch('source/'+sid+'/X+',alias) is not None and len(alias.encode())==row['original_source_path_utf8_bytes'],'complete_equal_UTF8_path_transform');need(type(row['original_source_path_utf8_bytes']) is int,'path_bytes_typed')
        arguments={'command':"/usr/bin/grep -oE '"+PATTERN+"' -- "+alias,'description':'Select the complete target field'};need(canonical(row['arguments'])==canonical(arguments),'generic_selector_no_answer');need(row['derived_arguments_sha256']==sha(canonical(arguments)) and row['original_arguments_sha256']!=row['derived_arguments_sha256'],'arguments_original_derived_columns')
        for k in ('original_source_path_sha256','original_arguments_sha256','original_wire_block_sha256','original_native_event_sha256'):hash_value(row[k],k)
        wire={'type':'tool_result','tool_use_id':cid,'content':[{'type':'text','text':text.decode()}],'is_error':False};need(canonical(row['wire_block'])==canonical(wire),'original_text_schema_error_presence_and_link');need(canonical(row['wire_position'])==canonical({'role':'user','message_index':2*i,'block_index':0}),'selected_position_not_whole_history')
        native={'type':'tool_result','callId':cid,'status':'completed','result':text.decode()};need(canonical(row['native_event'])==canonical(native),'native_wire_exact_untruncated_not_success_alone')
        need(row['original_wire_block_sha256']!=sha(canonical(wire)) and row['original_native_event_sha256']!=sha(canonical(native)),'original_versus_alias_schema_hashes')
        for k in ('source_unchanged','complete_field','renderer_inferred_zero'):need(row[k] is True,'row_'+k)
        need(row['numeric_inner_exit_code_observed'] is False and row['inner_exit_code'] is None,'numeric_inner_unknown')
    a=files['sources/A.txt'];b=files['sources/B.txt'];need([i for i,(x,y) in enumerate(zip(a,b)) if x!=y]==[8007] and a[8007:8008]==b'0' and b[8007:8008]==b'8','known_pair_single_bit_candidate_discrimination')
    for raw in files.values():privacy(raw)
    return {'selected_sources':2,'complete_decoded_fields':2,'decoded_bytes_each':72,'scientific_confirm_sessions':1,'numeric_inner_exit_code':None,'scope':'selected consistency only, not private raw authentication'}
def verify_inventory(files):
    need(set(files)==FILES,'exact_nine_files');manifest=parse(files['SHA256SUMS.json']);need(type(manifest) is dict and set(manifest)==FILES-{'SHA256SUMS.json'},'inventory_exact_entries')
    for name,digest in manifest.items():need(type(digest) is str and digest==sha(files[name]),'inventory_hash:'+name)
def load(root):
    root=Path(root);need(not root.is_symlink() and root.is_dir(),'root_not_symlink')
    need({p.name for p in root.iterdir()}==ROOT_FILES|{'sources','outputs'},'no_extra_root_files_or_directories')
    for name in ('sources','outputs'):
        p=root/name;need(not p.is_symlink() and p.is_dir() and {x.name for x in p.iterdir()}=={'A.txt','B.txt'},'exact_data_directory')
    files={}
    for name in FILES:
        p=root/name;need(not p.is_symlink() and stat.S_ISREG(p.stat().st_mode),'no_selected_file_symlinks');files[name]=p.read_bytes()
    return parse(files['evidence.json']),files
if __name__=='__main__':
    data,files=load(Path(__file__).resolve().parent);verify_inventory(files);print(json.dumps(verify(data,files),ensure_ascii=False,indent=2))
