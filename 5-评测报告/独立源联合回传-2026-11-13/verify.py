#!/usr/bin/env python3
"""Offline Python 3.9+ stdlib verifier for a selected, deidentified evidence face.
Not a raw-trace authenticator, provider tokenizer, or product runner.
"""
import hashlib
import json
import pathlib
import re
import sys

ORDER = ('dup1', 'ind1', 'ind2', 'dup2')
FIRST = 'eb98ea308bc89eff42a3f4a9bca425e5f37091beeff93859758f36159d020e7a'
SOURCE_HASHES = {
 'A1':'14a273fcf143ac05ec5390c0a351e7b82b9177c33a82ee0c6907885badb29dbe',
 'B1':'b44b5fba17fad8f800023ef9428c68fa9f10e05656b4f0edd1688d1199bbda25',
 'A2':'dd3baf53a59eb0cdf72f4877bd5ae1db44a3a42b3f01fef8604e40775f72a87a',
 'B2':'f52dde33d62b2573c0d2c3744bd4dea537323fe50ab2c12102b368af9f3c1559'}
USAGE = {'dup1':((516,0,36),(2216,512,2536)), 'ind1':((134,382,63),(2214,512,3473)),
         'ind2':((134,382,36),(2246,512,3818)), 'dup2':((134,382,36),(1341,1408,2918))}

def need(ok, reason):
    if not ok: raise ValueError(reason)
def sha(b): return hashlib.sha256(b).hexdigest()
def keys(obj, names, reason='schema'):
    need(type(obj) is dict and set(obj)==set(names.split()), reason)
def integer(n): return type(n) is int

def pairs(items):
    out = {}
    for k, v in items:
        need(k not in out, 'duplicate_json_key')
        out[k] = v
    return out

def parse(text):
    def reject(x): raise ValueError('nonfinite_json')
    return json.loads(text, object_pairs_hook=pairs, parse_constant=reject)

def exact_answer(raw, truth):
    text = raw.decode('utf-8').strip()
    if text.startswith('```'):
        match = re.fullmatch(r'```(?:json)?\s*\n(.*?)\n```', text, re.S)
        need(match is not None, 'answer_fence')
        text = match.group(1)
    value = parse(text)
    keys(value, 'packet_a packet_b', 'answer_top_keys')
    for name in ('packet_a','packet_b'):
        keys(value[name], 'head_nonce tail_nonce', 'answer_nonce_keys')
        for field in ('head_nonce','tail_nonce'):
            need(type(value[name][field]) is str and re.fullmatch('[0-9a-f]{700}', value[name][field]) is not None, 'nonce_type_length')
            need(value[name][field] == truth[name][field], 'wrong_nonce')
    return True

def privacy(raw):
    text = raw.decode('utf-8')
    prohibited = (chr(47)+'Users'+chr(47), chr(47)+'var'+chr(47)+'folders'+chr(47), 'bench'+'-private', 'ring'+'67', 'session'+'-', 'Bearer'+' ', 'danger'+'-full-access')
    need(not any(x.lower() in text.lower() for x in prohibited), 'private_path_or_trace_residue')
    need(re.search(r'(?:api[_-]?key|authorization)\s*[:=]', text, re.I) is None, 'credential_residue')

def load(root):
    root = pathlib.Path(root)
    data = parse((root/'evidence.json').read_text(encoding='utf-8'))
    files = {}
    for p in root.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:
            files[p.relative_to(root).as_posix()] = p.read_bytes()
    return data, files

def verify(data, files):
    keys(data, 'schema analysis_scope original_gate posthoc_gate design controls privacy limits audit sources cells')
    need(data['schema']=='joint-literal-copy-derived-v1', 'schema_version')
    need(data['analysis_scope']=='posthoc_exact_native_snapshot_reanalysis', 'posthoc_scope')
    need(data['original_gate']=={'valid':0,'planned':4,'status':'FAIL','reason':'initial_prompt_not_exact','reclassified':False}, 'original_gate_not_pass')
    need(data['posthoc_gate']=={'valid':4,'planned':4,'exact':4,'preregistered_pass':False}, 'posthoc_not_preregistered')
    need(data['design']=={'order':list(ORDER),'planned_cells':4,'n_per_condition':2,'A_reused_within_repeat':True}, 'design_denominator')
    need(data['controls']=={'harness':'DSH','recorded_version':'0.2.0-rc.2','provider':'deepseek-official','model':'deepseek-flash','effort':'low','thinking':'enabled','max_tokens':4096,'spill_cap':512,'retry':0}, 'controls')
    need(data['privacy']=={'derived_not_raw_trace':True,'path_transform':'each_selected_face_path_to_equal_utf8_byte_length_ASCII_X','initial_request_text_public':False,'native_snapshot_text_public':False,'call_ids':'original_opaque_tool_ids_only'}, 'privacy_label')
    need(data['limits']=={'I_text_is_entropy':False,'server_model_input_observed':False,'reasoning_equalized':False,'cache_equalized':False,'usage_arithmetic_performed':False,'first_hash_authenticates_original':False}, 'limits_or_usage_merge')
    need(data['audit']=={'scope':'posthoc_exact_native_assembly_reanalysis_only','verdict':'PASS','receipt_sha256':'01dcaa7b028769b3466950886350560537a0317d73e06dffed961b4411844f1a','source_files_stable':108,'rejected_counterexamples':18}, 'audit_scope')
    keys(data['sources'], 'A1 B1 A2 B2')
    truth = {}; all_nonces = []
    for sid, meta in data['sources'].items():
        keys(meta, 'file bytes sha256 nonces')
        need(meta['file']=='sources/'+sid+'.txt', 'source_file')
        raw = files[meta['file']]
        need(len(raw)==meta['bytes']==16000 and sha(raw)==meta['sha256']==SOURCE_HASHES[sid], 'source_hash_length')
        need(raw.isascii(), 'source_ascii')
        keys(meta['nonces'], 'head_nonce tail_nonce')
        truth[sid] = {}
        for name, span in (('head_nonce',(11,711)),('tail_nonce',(15299,15999))):
            n = raw[span[0]:span[1]]
            keys(meta['nonces'][name], 'bytes sha256 source_interval')
            need(meta['nonces'][name]=={'bytes':700,'sha256':sha(n),'source_interval':list(span)}, 'nonce_metadata')
            need(re.fullmatch(b'[0-9a-f]{700}',n) is not None, 'source_nonce')
            truth[sid][name] = n.decode(); all_nonces.append(n)
    need(len(set(all_nonces))==8, 'source_independence')
    need(type(data['cells']) is list and [c.get('id') for c in data['cells'] if type(c) is dict]==list(ORDER), 'missing_or_duplicate_cell')
    rows = []
    for cell in data['cells']:
        keys(cell, 'id condition repeat original_gate_valid first_wire last_request_source calls answer I_text M_source_max two_call_source_bytes_sum M_residual_vs_mock provider_usage_events client_accounting')
        sid = cell['id']; rep = int(sid[-1]); condition = 'duplicate' if sid.startswith('dup') else 'independent'
        need(cell['condition']==condition and cell['repeat']==rep and cell['original_gate_valid'] is False, 'condition_or_old_gate')
        need(cell['first_wire']=={'bytes':1504,'sha256':FIRST,'content_public':False}, 'first_wire_commitment')
        keys(cell['last_request_source'], 'index raw_bytes raw_sha256 formatted_json_file_sha256 response_sha256')
        need(cell['last_request_source']['index']==2 and cell['last_request_source']['raw_bytes']==(6189 if sid=='ind1' else 6078), 'request_source_bytes')
        for field in ('raw_sha256','formatted_json_file_sha256','response_sha256'):
            need(re.fullmatch('[0-9a-f]{64}',cell['last_request_source'][field]) is not None, 'request_hash_format')
        need(type(cell['calls']) is list and len(cell['calls'])==2 and [x['name'] for x in cell['calls']]==['packet_a','packet_b'], 'missing_or_duplicate_call')
        source_map = {'packet_a':'A'+str(rep), 'packet_b':('A' if condition=='duplicate' else 'B')+str(rep)}
        ids = set(); measured = []; literal = set()
        for call in cell['calls']:
            keys(call, 'name id input result_tool_use_id source file source_text_sha256 derived_text_sha256 source_text_bytes derived_text_bytes path_transform source_intervals M_source wrapper_bytes omitted_bytes')
            name = call['name']; source_id = source_map[name]
            need(call['source']==source_id, 'duplicate_as_independent')
            need(type(call['id']) is str and call['id'] not in ids and call['result_tool_use_id']==call['id'] and call['input']=={}, 'call_linkage')
            ids.add(call['id'])
            need(call['file']=='faces/'+sid+'-'+name+'.txt', 'face_file')
            raw = files[call['file']]; privacy(raw)
            need(len(raw)==call['derived_text_bytes']==call['source_text_bytes']==1979, 'face_byte_length')
            need(sha(raw)==call['derived_text_sha256'] and re.fullmatch('[0-9a-f]{64}',call['source_text_sha256']) is not None and call['source_text_sha256']!=call['derived_text_sha256'], 'raw_vs_derived_face_hash')
            text = raw.decode('ascii')
            head, rest = text.split('\n\n[...]\n\n')
            match = re.fullmatch(r'(.*)\n\n\(Omitted (\d+) bytes\. Full formatted result stored at: (X+)\. Use read with offset/limit, or grep this path to search within it\.\)', rest, re.S)
            need(match is not None, 'face_wrapper')
            tail = match.group(1); source = files[data['sources'][source_id]['file']]
            need(source.startswith(head.encode()) and source.endswith(tail.encode()), 'source_prefix_suffix')
            spans = [[0,len(head)], [len(source)-len(tail),len(source)]]
            need(spans==[[0,868],[15136,16000]] and call['source_intervals']==spans, 'source_interval_union')
            # Two disjoint intervals; union, never double-count history or wrappers.
            m = spans[0][1]+spans[1][1]-spans[1][0]
            omitted = len(source)-m
            need(int(match.group(2))==omitted==call['omitted_bytes']==14268, 'forged_omitted')
            need(m==call['M_source']==1732 and len(raw)-m==call['wrapper_bytes']==247, 'forged_M')
            replacement_start = raw.index(b'Full formatted result stored at: ')+len(b'Full formatted result stored at: ')
            replacement_end = replacement_start+len(match.group(3))
            transform = call['path_transform']
            keys(transform, 'applied byte_interval original_span_sha256 placeholder byte_length_preserved')
            need(transform['applied'] is True and transform['byte_length_preserved'] is True and transform['placeholder']=='X' and transform['byte_interval']==[replacement_start,replacement_end] and re.fullmatch('[0-9a-f]{64}',transform['original_span_sha256']) is not None, 'privacy_transform_not_marked')
            for nonce in truth[source_id].values():
                need(nonce in head or nonce in tail, 'nonce_missing_in_face')
                literal.add(nonce)
            measured.append(m)
        i = sum(len(x.encode('ascii')) for x in literal)
        need(i==cell['I_text']==(1400 if condition=='duplicate' else 2800), 'forged_I_or_duplicate_information')
        need(max(measured)==cell['M_source_max']==1732 and sum(measured)==cell['two_call_source_bytes_sum']==3464 and cell['M_residual_vs_mock']==4, 'source_vs_joint_M')
        need(condition=='duplicate' or i>max(measured), 'independent_I_not_gt_M')
        answer = cell['answer']; keys(answer, 'file sha256 bytes transformed')
        need(answer['file']=='answers/'+sid+'.txt' and answer['transformed'] is False, 'answer_transform')
        raw_answer = files[answer['file']]
        need(len(raw_answer)==answer['bytes'] and sha(raw_answer)==answer['sha256'], 'answer_hash')
        exact_answer(raw_answer, {n:truth[s] for n,s in source_map.items()})
        events = cell['provider_usage_events']
        need(type(events) is list and len(events)==2, 'usage_requests')
        for index, (entry, expected) in enumerate(zip(events,USAGE[sid]),1):
            keys(entry, 'request provider_usage_events')
            need(entry['request']==index and len(entry['provider_usage_events'])==2, 'usage_event_count')
            for phase, event in enumerate(entry['provider_usage_events']):
                keys(event, 'event usage'+(' stop_reason' if phase else ''), 'usage_no_inferred_fields')
                need(event['event']==('message_delta' if phase else 'message_start'), 'usage_event_type')
                need(type(event['usage']) is dict and all(integer(event['usage'].get(k)) for k in ('input_tokens','cache_creation_input_tokens','cache_read_input_tokens','output_tokens')), 'usage_integer_fields')
                need(event['usage']=={'input_tokens':expected[0],'cache_creation_input_tokens':0,'cache_read_input_tokens':expected[1],'output_tokens':expected[2] if phase else 0,'service_tier':'standard'}, 'usage_original_fields_only')
                if phase: need(event['stop_reason']==('tool_use' if index==1 else 'end_turn'), 'usage_stop')
        need(cell['client_accounting']=={'durable_intents':2,'confirmed':2,'unknown_upper_bound':0}, 'client_accounting')
        rows.append({'cell':sid,'I_text':i,'M_source_max':max(measured),'two_call_sum':sum(measured),'exact':True})
    for name, raw in files.items():
        privacy(raw)
        need(not pathlib.PurePosixPath(name).is_absolute() and '..' not in pathlib.PurePosixPath(name).parts, 'file_escape')
    return {'scope':'posthoc_selected_derived_face_only','original_gate':'FAIL 0/4; not reclassified','posthoc_exact':'4/4','n_per_condition':2,'client_intents':8,'client_confirmed':8,'client_unknown_upper_bound':0,'rows':rows}

def verify_inventory(files):
    inventory = parse(files['SHA256SUMS.json'].decode('utf-8'))
    need(inventory == {name:sha(raw) for name,raw in files.items() if name!='SHA256SUMS.json'}, 'package_file_inventory_changed')

if __name__=='__main__':
    root = pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else pathlib.Path(__file__).resolve().parent
    try:
        data, files = load(root)
        verify_inventory(files)
        print(json.dumps(verify(data,files),ensure_ascii=False,indent=2))
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        print('FAIL: '+str(error),file=sys.stderr); sys.exit(1)
