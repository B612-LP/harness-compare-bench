#!/usr/bin/env python3
"""Independent stdlib verifier of selected, de-identified evidence; no product runner."""
from pathlib import Path
import hashlib,json,re,math,sys
BASELINE='922cbd53b0b28a9e6acfa8230d7278ea2ad2ac4cd446174f2636d6374dba8b51'
SOURCE_HASHES={'A':'11104026259b14aa512c6c69f6e7f14f8ac099ebe6e0b99f61b06bb00ea41d6d','B':'65d51423026971f1b0695721f5d78d6aca404a733e8bf822469edaf924295b57'}
G='TARGET=[0-9a-f]{64}';D='TARGET=[89abcdef][0-9a-f]{63}'
GAP='\n\n[...]\n\n';HINT='Use read with offset/limit, or grep this path to search within it.'
BRANCH='generic_match_does_not_show_field_but_predeclared_one_bit_query_distinguishes_this_pair'
FILES={'README.md','evidence.json','verify.py','test_verify.py','SHA256SUMS.json'}|{'sources/'+x+'.txt' for x in 'AB'}|{'results/Q%d.txt'%i for i in range(1,5)}|{'formatted/Q%d.txt'%i for i in (1,2,4)}
def need(ok,why):
    if not ok:raise ValueError(why)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def parse(raw):
    def pairs(values):
        out={}
        for k,v in values:need(k not in out,'duplicate_json_key');out[k]=v
        return out
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:need(False,'nonfinite_json'))
def baseline(data):return sha(canonical(data))
def number(value,want):return type(value) is int and value==want
def textbytes(value):need(type(value) is str and value.isascii(),'ASCII_text_required');return value.encode('ascii')
def hash_value(value):return type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None
def privacy(raw):
    text=raw.decode('utf-8')
    need(not re.search(r'/(?:Users)/|/(?:Applications)/|/(?:opt)/homebrew/|bench[-]private|dsh[-]spill[-]|session-[0-9a-f]|tg1114[_]c|callback[_]identity|"pid"\s*:|"ino"\s*:|"ctime_ns"\s*:|authorization\s*:|sk-[A-Za-z0-9]{16}',text,re.I),'private_residue')
def price(text):return math.ceil(len(textbytes(text))/4)+4
def notice(n,path):return '\n\n(Omitted %d bytes. Full formatted result stored at: %s. %s)'%(n,path,HINT)
def bound(full,path):
    textbytes(full);textbytes(path)
    if price(full)<=512:return full
    available=512-price(GAP)-price(notice(len(full),path));need(available>8,'impossible_bound')
    h=max(0,(math.ceil(available/2)-4)*4);t=max(0,(math.floor(available/2)-4)*4)
    need(h+t<len(full),'bound_not_clipped');return full[:h]+GAP+full[-t:]+notice(len(full)-h-t,path)
def geometry(full,shown,source,path,locator):
    header='Found 1 match\n\n'+path+'\nLine 1: '
    need(full==header+source[:2000]+' (line truncated)','formatted_not_actual_source_prefix')
    need(shown==bound(full,locator),'secondary_bound_or_footer_wrong')
    a,b=shown.split(GAP);tail=b.split('\n\n(Omitted ',1)[0];h,t=len(a),len(tail);start=len(header);end=start+2000
    intervals=[[max(l,start)-start,min(r,end)-start] for l,r in ((0,h),(len(full)-t,len(full))) if min(r,end)>max(l,start)]
    retained=sum(r-l for l,r in intervals)
    return {'source_bytes':len(source),'preformatted_bytes':len(full),'preformatted_source_interval':[0,2000],'preformatted_wrapper_bytes':len(full)-2000,'final_result_bytes':len(shown),'kept_formatted_bytes':[h,t],'omitted_formatted_bytes':len(full)-h-t,'final_source_intervals':intervals,'final_source_bytes':retained,'final_wrapper_bytes':len(shown)-retained,'target_visible':False}
def keys(value,expected,why):need(type(value) is dict and set(value)==set(expected),why)
def verify(data,files):
    need(type(data) is dict and data.get('format')=='native-match-selected-20261114-v3','wrong_selected_version')
    need(baseline(data)==BASELINE,'selected_value_commitment_changed')
    for raw in files.values():privacy(raw)
    coverage=data['coverage'];need(coverage=={'fresh_sessions':2,'scientific_confirm_sessions':1,'catalog_requests':1,'confirm_requests':6,'total_local_requests':7,'fixture_calls':2,'grep_calls':4,'real_models':0,'upstream_forwards':0},'coverage_or_denominator_changed')
    need(all(type(v) is int for v in coverage.values()),'bool_is_not_integer_count')
    need(data['branch']==BRANCH,'branch_changed')
    limits=data['limits'];need(all(limits.get(k) is True for k in ('one_predeclared_predicate_bit_only','not_full_64hex_recovery','not_256_queries_executed','not_entropy_cost_or_Agent_score','not_whole_context_equality','private_raw_not_authenticated_by_public_selection','source_pin_not_full_runtime_attestation')),'scientific_scope_widened')
    need(data['provenance']['analysis_sha256']=='9e8089f826193d08f1fdddd0a33fb59c9740c7921915c16108155cea9dfe54cb' and data['provenance']['approval_sha256']=='e4b9a4a8ea2b07321969b4ba72196f37a482074889c9790381249e4ed04b173b','original_identity_commitment_changed')
    audit=data['provenance']['scientific_audit'];keys(audit,('status','scope','receipt_sha256','report_sha256'),'scientific_audit_schema')
    need(audit=={'status':'finite_PASS','scope':'one actual confirm session; separate public-package audit still required','receipt_sha256':'4fa158cb696bf3f0654cc0bfaefaf20c7070008ad93cf1189d72599e36c111ce','report_sha256':'a9200b5de841270f65d360a54eca9f00212a72f29c1b233ece7f6ad70f4cb7b9'},'scientific_audit_scope')
    need(data['provenance']['source_seal_sha256']=='7e8751d45f5bdb20e0f6876ad9393ed4cb6251d0f3b9b3035a7fa71b83547632','source_seal_commitment')
    src={};paths={};need(type(data['sources']) is list and len(data['sources'])==2,'source_count')
    for rec,sid in zip(data['sources'],'AB'):
        need(rec['id']==sid and rec['file']=='sources/'+sid+'.txt','source_order_alias');raw=files[rec['file']];text=raw.decode('ascii')
        need(len(raw)==16000 and '\r' not in text and '\n' not in text,'source_geometry')
        need(rec['original_sha256']==rec['derived_sha256']==sha(raw)==SOURCE_HASHES[sid] and rec['transform']=='safe_synthetic_bytes_unchanged','source_hash_or_transform')
        need(text[8000:8007]=='TARGET=' and re.fullmatch('[0-9a-f]{64}',text[8007:8071]) is not None,'TARGET_geometry')
        path=rec['source_path_placeholder'];need(re.fullmatch('source/'+sid+'/X+',path) is not None and number(rec['original_path_utf8_bytes'],len(path)) and hash_value(rec['original_path_sha256']),'source_locator_transform')
        src[sid]=text;paths[sid]=path
    need([i for i,(a,b) in enumerate(zip(src['A'],src['B'])) if a!=b]==[8007] and src['A'][8007]=='0' and src['B'][8007]=='8','not_exact_one_byte_source_pair')
    need(len(data['queries'])==4 and [q['id'] for q in data['queries']]==['Q1','Q2','Q3','Q4'],'missing_duplicate_query')
    result_text={};normalized=[]
    for q,sid,pattern,count in zip(data['queries'],('A','B','A','B'),(G,G,D,D),(1,1,0,1)):
        qid=q['id'];need(q['source']==sid and q['pattern']==pattern and number(q['count'],count),'pattern_source_count')
        need(len(re.findall(pattern,src[sid]))==count,'predicate_not_derived_from_actual_source')
        raw=files['results/'+qid+'.txt'];shown=raw.decode('ascii');result_text[qid]=shown
        need(q['result_file']=='results/'+qid+'.txt' and q['derived_result_sha256']==sha(raw) and hash_value(q['original_result_sha256']),'result_file_hash')
        if count:
            locator=q['formatted_path_placeholder'];need(re.fullmatch('formatted/'+qid+'/X+',locator) is not None and number(q['original_formatted_path_utf8_bytes'],len(locator)) and hash_value(q['original_formatted_path_sha256']),'formatted_locator_transform')
            need(q['formatted_file']=='formatted/'+qid+'.txt','formatted_file_reference');full=files[q['formatted_file']].decode('ascii')
            need(q['derived_formatted_sha256']==sha(full.encode()) and hash_value(q['original_formatted_sha256']),'formatted_file_hash')
            actual=geometry(full,shown,src[sid],paths[sid],locator);need(canonical(q['geometry'])==canonical(actual),'source_interval_or_wrapper_accounting')
            need(actual=={'source_bytes':16000,'preformatted_bytes':2210,'preformatted_source_interval':[0,2000],'preformatted_wrapper_bytes':210,'final_result_bytes':1978,'kept_formatted_bytes':[840,840],'omitted_formatted_bytes':530,'final_source_intervals':[[0,647],[1177,2000]],'final_source_bytes':1470,'final_wrapper_bytes':508,'target_visible':False},'actual_byte_decomposition_changed')
            need('TARGET=' not in shown,'target_visible_in_final_face')
            normalized.append(shown.replace(paths[sid],'<SOURCE_PATH>').replace(locator,'<FORMATTED_RESULT_PATH>'))
        else:
            need(shown=='No matches found' and q['formatted_file'] is None and canonical(q['geometry'])==canonical({'final_result_bytes':16,'final_source_bytes':0,'target_visible':False}),'zero_not_explicit_or_error')
            need(q['original_result_sha256']==sha(raw) and q['derived_result_sha256']==sha(raw),'NoMatches_bytes_changed')
        need(q['normalized_specified_sha256']==sha((normalized[-1] if count else shown).encode()),'normalized_hash_wrong')
    need(len(set(normalized))==1 and sha(normalized[0].encode())=='a0bad72f1b4c43c75222806b909ef8ac91a00a2356b52730a4afea37ed524e9e','specified_presentation_not_equal')
    events=data['selected_results'];need(type(events) is list and len(events)==6,'six_Native_results_required')
    for i,event in enumerate(events,1):
        cid='call-%04d'%i;sid='A' if i in (1,3,5) else 'B';qid='Q%d'%(i-2) if i>2 else None
        need(event['call_alias']==cid and event['source']==sid and event['kind']==('fixture' if i<=2 else 'grep'),'event_source_or_order')
        need(event['wire_role']=='user' and number(event['wire_message_index'],(2,2,4,6,8,10)[i-1]) and number(event['wire_block_index'],1 if i==2 else 0),'selected_result_role_position')
        wire=event['wire_block'];keys(wire,('type','tool_use_id','content','is_error'),'wire_original_schema')
        need(wire['type']=='tool_result' and wire['tool_use_id']==cid and wire['is_error'] is False and event['wire_is_error_present'] is True,'wire_error_presence_status')
        need(type(wire['content']) is list and len(wire['content'])==1,'wire_pure_text_schema');keys(wire['content'][0],('type','text'),'wire_pure_text_schema');need(wire['content'][0]['type']=='text','wire_text_type');shown=wire['content'][0]['text']
        expected=bound(src[sid],paths[sid]) if i<=2 else result_text[qid]
        need(type(shown) is str and shown==expected,'wire_text_not_selected_file_or_fixture_source')
        native=event['native_event'];keys(native,('type','callId','status','result'),'Native_actual_untruncated_schema')
        need(native=={'type':'tool_result','callId':cid,'status':'completed','result':shown} and event['native_truncated_present'] is False,'Native_wire_result_mismatch')
        need(len(shown.encode())<=8192 and len(canonical(native))+1<=32768,'Native_projection_outside_known_arm')
        need(event['derived_native_event_canonical_sha256']==sha(canonical(native)) and event['derived_wire_block_canonical_sha256']==sha(canonical(wire)),'derived_event_hash')
        need(all(hash_value(event[k]) for k in ('original_native_jsonl_line_sha256','original_native_event_canonical_sha256','original_wire_block_canonical_sha256','original_text_sha256')),'original_event_commitments')
    for slot in ('catalog','confirm'):
        end=data['runtime_end'][slot];keys(end,('completed','exit_code','timeout','logs_withheld','native_identity_verified','failure','upstream_forwards','never_resubmit','owned_group_witness'),'end_witness_schema')
        need(end['completed'] is True and number(end['exit_code'],0) and end['timeout'] is False and end['logs_withheld'] is False and end['native_identity_verified'] is True and end['failure'] is None and number(end['upstream_forwards'],0) and end['never_resubmit'] is True,'end_unknown_or_unsuccessful')
        need(end['owned_group_witness']=={'start_new_session':True,'state':'absent','events':[{'signal':0,'result':'absent'}],'term_seconds':1.0,'kill_seconds':1.0,'scope':'owned_group_only_not_whole_process_tree'} and end['owned_group_witness']['start_new_session'] is True and type(end['owned_group_witness']['events'][0]['signal']) is int and all(type(end['owned_group_witness'][k]) in (int,float) for k in ('term_seconds','kill_seconds')),'owned_group_scope_or_absence')
    relation=data['private_replay_relations'];need(relation=={'all_six_Native_wire_exact':True,'original_callback_FD_and_fixed_ledger':True,'all_five_history_increments_closed':True,'full_unpublished_sources_needed_to_authenticate':True} and all(v is True for v in relation.values()),'private_relation_claim_changed')
    requests=data['request_commitments'];need(len(requests)==7 and [r['alias'] for r in requests]==['catalog-1']+['confirm-%d'%i for i in range(1,7)],'local_request_coverage')
    for r in requests:
        need(all(hash_value(r[k]) for k in ('raw_request_sha256','formatted_json_file_sha256','canonical_json_value_sha256','response_sse_sha256')),'request_hash_columns')
        need(r['raw_request_sha256']!=r['formatted_json_file_sha256'] and number(r['status'],200) and r['failure'] is None and number(r['upstream_forwards'],0) and r['credentials_logged'] is False,'request_meta_or_hash_confusion')
    return {'verified_selected_package':True,'source_bytes_each':16000,'preformatted_bytes':2210,'final_positive_result_bytes':1978,'final_source_bytes':1470,'counts':[1,1,0,1],'scientific_sessions':1,'unpublished_raw_authenticated':False}
def verify_inventory(files):
    need(set(files)==FILES,'extra_missing_package_file');inventory=parse(files['SHA256SUMS.json']);need(set(inventory)==FILES-{'SHA256SUMS.json'},'manifest_coverage')
    need(all(inventory[n]==sha(files[n]) for n in inventory),'file_inventory_hash_mismatch')
def load(root):
    root=Path(root);paths=list(root.rglob('*'));need(not any(p.is_symlink() for p in paths),'package_symlink')
    return {p.relative_to(root).as_posix():p.read_bytes() for p in paths if p.is_file()}
if __name__=='__main__':
    files=load(Path(__file__).resolve().parent);verify_inventory(files);print(json.dumps(verify(parse(files['evidence.json']),files),ensure_ascii=False))
