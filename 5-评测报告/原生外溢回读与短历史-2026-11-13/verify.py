#!/usr/bin/env python3
"""Offline cleanroom verifier of selected presentation relationships, Python 3.9+."""
import hashlib
import json
import re
from pathlib import Path

BASELINE = '234d2e17467432d598aae3f64be89dc886e9fff83571b0b775507064950c5ba9'
SOURCE_HASHES = {'A1':'14a273fcf143ac05ec5390c0a351e7b82b9177c33a82ee0c6907885badb29dbe','B1':'b44b5fba17fad8f800023ef9428c68fa9f10e05656b4f0edd1688d1199bbda25','A2':'dd3baf53a59eb0cdf72f4877bd5ae1db44a3a42b3f01fef8604e40775f72a87a','B2':'f52dde33d62b2573c0d2c3744bd4dea537323fe50ab2c12102b368af9f3c1559'}
GAP = '\n\n[...]\n\n'
HINT = '. Use read with offset/limit, or grep this path to search within it.'

def need(ok, reason):
    if not ok: raise ValueError(reason)
def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',',':')).encode('utf-8')
def parse(raw):
    def pairs(items):
        d={}
        for k,v in items:
            need(k not in d, 'duplicate_json_key'); d[k]=v
        return d
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite_json')))
def privacy(raw):
    text=raw.decode('utf-8')
    need(not re.search(r'\x2fUsers\x2f|\x2fprivate\x2f|bench\x2dprivate|\bring[0-9]+\b|r7[0]_c|Current runtime\x20context|session-[a-f0-9-]{12,}|Bearer\s|sk-[A-Za-z0-9]{12,}|api[_-]?key\s*[:=]',text,re.I), 'private_residue')
def error_first(text, is_error=False):
    need(is_error is False and not re.search(r'<(?:tool_use_error|tool_error|error|read_error)(?:\s|>)',text,re.I), 'error_envelope')
def read_lines(text, path, source):
    error_first(text)
    prefix='<path>'+path+'</path>\n<type>file</type>\n<content>\n'
    suffix='\n\n(End of file - total 192 lines)\n</content>'
    need(text.startswith(prefix) and text.endswith(suffix),'native_read_envelope')
    lines=text[len(prefix):-len(suffix)].split('\n')
    need(len(lines)==192,'native_line_count')
    values=[]
    for i,line in enumerate(lines,1):
        tag=str(i)+': '; need(line.startswith(tag),'native_line_number'); values.append(line[len(tag):])
    rebuilt=('\n'.join(values)+'\n').encode('ascii')
    need(rebuilt==source,'native_source_mismatch')
    body_bytes=sum(len(x.encode()) for x in values); face_bytes=len(text.encode())
    return {'numbered_lines':192,'face_bytes':face_bytes,'body_no_lf_bytes':body_bytes,'reconstructed_lf_bytes':len(rebuilt),'wrapper_no_lf_bytes':face_bytes-body_bytes,'net_over_lf_bytes':face_bytes-len(rebuilt)}
def clipped(text,path,source):
    error_first(text)
    end=re.search(r'\n\n\(Omitted ([0-9]+) bytes\. Full formatted result stored at: (X+)'+re.escape(HINT)+r'\)$',text)
    need(end is not None and end[2]==path and text.count(GAP)==1,'clip_envelope')
    head,tail=text[:end.start()].split(GAP)
    raw=source.decode('ascii'); middle=raw.splitlines()[99]
    need(head and tail and raw.startswith(head) and raw.endswith(tail),'clip_source')
    retained=len(head.encode())+len(tail.encode())
    need(int(end[1])==16000-retained>0 and middle not in text,'clip_omission')
    need(raw.splitlines()[0] in head and raw.splitlines()[-1] in tail,'clip_nonce')
    return {'source_intervals':[[0,len(head)],[16000-len(tail),16000]],'retained_source_bytes':retained,'omitted_source_bytes':int(end[1]),'wrapper_bytes':len(text.encode())-retained,'presentation_bytes':len(text.encode())}
def block(text, cid): return {'type':'tool_result','tool_use_id':cid,'content':[{'type':'text','text':text}],'is_error':False}
def verify(data,files,check_baseline=True):
    need(data['format']=='selected-native-read-v1','format')
    need(all(type(v) is int for v in data['counts'].values()),'count_integer_not_bool')
    need(type(data['earlier']['actual_native_reads']) is int and type(data['earlier']['planned_native_reads']) is int,'earlier_integer_not_bool')
    need(data['counts']=={'new_cases':2,'new_seen_local':8,'new_accepted_local':8,'new_fixture_calls':4,'new_actual_native_reads':4,'new_remote_forwards':0,'earlier_seen_local':3,'cumulative_seen_local':11},'counts')
    need(data['earlier']=={'planned_native_reads':4,'actual_native_reads':0,'status':'invalid_decoder_failure','never_backfilled':True},'earlier_failure')
    need(data['boundaries']=={'actual_native_read':True,'scripted_controller':True,'model_score':False,'source_pin_is_full_runtime_identity':False,'full_initial_request_published':False,'selected_faces_authenticate_private_path_safety':False,'known_lf_reconstruction_not_wire_contiguity':True,'long_history_claim':False,'cost_claim':False},'boundaries')
    need(data['defaults']=={'file_policy':'workspace-write','approval_policy':'ask','read_max_bytes':51200,'read_max_lines':2000,'read_max_utf16_per_line':2000,'changed':False},'defaults')
    need(set(data['sources'])==set(SOURCE_HASHES),'source_coverage')
    sources={}; nonces=[]; middles=[]
    for name,item in data['sources'].items():
        raw=files[item['file']]; need(raw.isascii() and len(raw)==16000 and raw.endswith(b'\n') and b'\r' not in raw,'source_geometry')
        need(sha(raw)==SOURCE_HASHES[name]==item['original_sha256']==item['derived_sha256'],'source_hash')
        lines=raw.decode().splitlines(); need(len(lines)==192,'source_lines')
        for line,label in ((lines[0],'head_nonce='),(lines[-1],'tail_nonce=')):
            need(re.fullmatch(re.escape(label)+r'[0-9a-f]{700}',line) is not None,'nonce_shape'); nonces.append(line[len(label):])
        middles.append(lines[99]); sources[name]=raw
    need(len(set(nonces))==8 and len(set(middles))==1,'source_identity_or_middle')
    need([c['case'] for c in data['cases']]==['C1','C2'],'case_coverage')
    total=0
    for ci,case in enumerate(data['cases'],1):
        mapping={'packet_a':'A'+str(ci),'packet_b':'B'+str(ci)}
        order=['packet_a','packet_b'] if ci==1 else ['packet_b','packet_a']
        need(case['source_map']==mapping and case['read_order']==order,'source_routing_order')
        need(len(case['calls'])==4 and len(case['frames'])==9 and len(case['requests'])==4,'case_coverage')
        need(case['end_completed'] is True and case['exit_code']==0 and case['actual_native_reads']==2 and case['fixture_callbacks']==2 and case['remote_forwards']==0,'native_outcome')
        need(case['native_read_previews']==[{'call':3,'preview_bytes':8192,'truncated':True,'full_evidence_request':3},{'call':4,'preview_bytes':8192,'truncated':True,'full_evidence_request':4}],'stdout_not_full_evidence')
        need([r['ordinal'] for r in case['requests']]==[1,2,3,4],'request_order')
        for req in case['requests']:
            need(type(req['raw_bytes']) is int and req['raw_bytes']>0,'raw_bytes')
            for key in ('raw_request_sha256','formatted_json_sha256','canonical_json_sha256'):
                need(re.fullmatch('[0-9a-f]{64}',req[key]) is not None,'request_hash')
            need(req['response_usage_is_scripted_mock'] is True,'usage_layer')
        calls=case['calls']; paths=case['paths']
        need(set(paths)=={'packet_a','packet_b'},'path_mapping')
        need(len({x['original_path_sha256'] for x in paths.values()})==2,'original_path_identity')
        for tool,p in paths.items():
            need(set(p['alias'])=={'X'} and len(p['alias'].encode())==p['original_utf8_bytes'],'path_length')
            need(p['replacement_sha256']==sha(p['alias'].encode()) and p['target_source']==mapping[tool],'path_target')
        for j,call in enumerate(calls,1):
            tool=['packet_a','packet_b'] [j-1] if j<=2 else order[j-3]
            expected_name=tool if j<=2 else 'read'
            need(call['alias']=='anon0'+str(j) and len(call['alias'])==call['original_id_utf8_bytes']==6,'call_alias')
            need(call['derived_id_sha256']==sha(call['alias'].encode()),'call_hash')
            need(call['name']==expected_name and call['target_source']==mapping[tool],'call_target')
            need(call['input']==({} if j<=2 else {'file_path':paths[tool]['alias']}),'call_parameters')
            need(call['position']==([1,j-1] if j<=2 else [2*j-3,0]),'call_position')
        expected=[(r,j) for r,count in ((2,2),(3,3),(4,4)) for j in range(1,count+1)]
        need([(f['request'],f['call']) for f in case['frames']]==expected,'frame_coverage_order')
        seen={}
        for frame in case['frames']:
            j=frame['call']; tool=['packet_a','packet_b'][j-1] if j<=2 else order[j-3]
            source=sources[mapping[tool]]; path=paths[tool]['alias']; text=frame['text']
            need(frame['role']=='user' and frame['position']==([2,j-1] if j<=2 else [2*j-2,0]),'result_role_position')
            need(frame['target_source']==mapping[tool] and frame['call_alias']==calls[j-1]['alias'],'result_binding')
            error_first(text,frame['is_error'])
            need(sha(text.encode())==frame['derived_text_sha256'] and sha(canonical(block(text,frame['call_alias'])))==frame['derived_block_sha256'],'derived_hash')
            transforms=frame['path_transforms']; need(len(transforms)==1,'path_transform_count')
            tr=transforms[0]; offset=text.encode().find(path.encode())
            need(offset>=0 and text.count(path)==1 and tr=={'start_utf8':offset,'length_utf8':len(path),'original_span_sha256':paths[tool]['original_path_sha256'],'replacement_sha256':sha(path.encode())},'path_transform')
            need(frame['original_text_bytes']==len(text.encode()) and frame['original_text_sha256']!=frame['derived_text_sha256'],'original_derived_separation')
            measured=clipped(text,path,source) if j<=2 else read_lines(text,path,source)
            need(measured==frame['measurement'],'presentation_measurement')
            need(frame['line_sha256']==([] if j<=2 else [sha(line) for line in source.splitlines()]),'line_hashes')
            if j<=2: need(middles[0] not in text and measured['retained_source_bytes']==1676 and measured['omitted_source_bytes']==14324,'middle_in_clip_or_wrong_clip_metric')
            else: need(measured=={'numbered_lines':192,'face_bytes':17105,'body_no_lf_bytes':15808,'reconstructed_lf_bytes':16000,'wrapper_no_lf_bytes':1297,'net_over_lf_bytes':1105} and middles[0] in text,'read_middle_or_wrapper')
            if j in seen:
                need(seen[j]==(frame['role'],frame['position'],text,frame['derived_block_sha256'],frame['original_block_sha256']),'selected_history_changed')
            else: seen[j]=(frame['role'],frame['position'],text,frame['derived_block_sha256'],frame['original_block_sha256'])
            total+=1
    need(total==18,'frame_total')
    for raw in files.values(): privacy(raw)
    if check_baseline: need(sha(canonical(data))==BASELINE,'evidence_commitment')
    return {'cases':2,'selected_faces':18,'actual_native_reads':4,'remote_forwards':0,'known_lf_sources_reconstructed':4,'earlier_invalid_preserved':True}
def verify_inventory(files):
    inv=parse(files['SHA256SUMS.json'])
    need(set(inv)==set(files)-{'SHA256SUMS.json'},'inventory_coverage')
    for name,h in inv.items(): need(sha(files[name])==h,'inventory_hash:'+name)
def load(root):
    files={}
    for p in root.rglob('*'):
        need(not p.is_symlink(),'symlink')
        if p.is_file(): files[p.relative_to(root).as_posix()]=p.read_bytes()
    return parse(files['evidence.json']),files
if __name__=='__main__':
    data,files=load(Path(__file__).resolve().parent); verify_inventory(files)
    print(json.dumps(verify(data,files),ensure_ascii=False,sort_keys=True))
