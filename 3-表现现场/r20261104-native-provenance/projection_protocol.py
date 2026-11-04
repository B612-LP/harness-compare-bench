"""Public projection checks only. Pure stdlib; no product, credential or network I/O."""
import copy, hashlib, json, re, statistics

SCHEMA='native-provenance-public-v1'
CONTRACT='native-direct-provenance-20261104-v1'
OLD_CONTRACT='native-direct-frozen04-20261103'
FIXTURE_SHA='fed57592028c9d8a9180c2b97f74a3cd5e0daa841aab244cf4aad78fe44626a2'
FIXTURE_BYTES=35767
SOURCE_FILES=('run_stage.py','PREREGISTRATION.md','plan.md','legacy-source-pins.json','mcp-fixture.py','fixture-plugin.mjs','redirect-preload.mjs','transport/relay.py','transport/guard.py','transport/__init__.py','transport/readiness-v4.json','test_run_stage.py','controller-tests-04/receipt.json','setup.json','template-dsh-v2.json','transport/provenance.py','transport/accounting.py','transport/native_mock.py','transport/tests/test_provenance.py','analyze_stage.py','test_analysis.py','contract_clock.py','analysis-tests-01.json','calibration/codex-native-01/capture/01-request.json')
LEGACY_FILES=('runner.py','analyze.py','mcp-fixture.py','fixture-plugin.mjs','redirect-preload.mjs','setup.json','transport/relay.py')
PILOTS=('pilot-codex-native-v1','pilot-dsh-bounded-v1')
CONFIRMS=tuple('confirm-b%02d-%s'%(b,p) for b in (1,2,3) for p in (('codex','dsh') if b%2 else ('dsh','codex')))
MOCKS=('offline-strict-codex-01','offline-strict-codex-02','offline-strict-dsh-02')
HISTORICAL='legacy-pilot-codex-native-v3'
SLOTS=PILOTS+CONFIRMS+MOCKS+(HISTORICAL,)
METADATA_FILES=('run-meta.json','end.json','session-gate.json','metrics.json','policy.json','capture/relay.json','capture/relay-closed.json','capture/tool-process.json','capture/01-meta.json','capture/02-meta.json')
WIRE_FILES=tuple('capture/%02d-%s'%(i,s) for i in (1,2) for s in ('request.raw','request.json','response.sse'))+('capture/tool-output.txt',)
RUN_FILES=METADATA_FILES+WIRE_FILES
ROOT_SOURCES=('FINAL-MANIFEST.json','legacy-source-pins.json','pilot-completion.json','confirmation-freeze.json','confirmation-completion.json','live-analysis-01/metrics.json','offline-completion.json')
ROOT_FILES=('README.md','source-pins.json','ledger.json','projection-map.json','verify.py','projection_protocol.py')
SHA=re.compile(r'^[0-9a-f]{64}$')

class GateError(ValueError):
    def __init__(self,code):self.code=code;super().__init__(code)
def _need(condition,code):
    if not condition:raise GateError(code)
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def _same(a,b):return canonical(a)==canonical(b)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def _pairs(items):
    out={}
    for k,v in items:_need(k not in out,'duplicate_json_key');out[k]=v
    return out
def _invalid_constant(_):raise GateError('invalid_json_constant')
def _decode(raw):return json.loads(raw.decode('utf-8'),object_pairs_hook=_pairs,parse_constant=_invalid_constant)
def keys(obj,names,code='schema_keys'):_need(isinstance(obj,dict) and set(obj)==set(names),code)
def sha(value):_need(isinstance(value,str) and SHA.fullmatch(value),'sha_invalid')
def integer(value,nullable=False,minimum=None):
    _need((nullable and value is None) or (type(value)is int and (minimum is None or value>=minimum)),'integer_invalid')
def boolean(value,nullable=False):_need((nullable and value is None) or type(value)is bool,'boolean_invalid')
def strings(value):_need(isinstance(value,list) and all(isinstance(v,str) for v in value),'strings_invalid')
def source_label(slot,name):return ('historical' if slot==HISTORICAL else 'current')+'/runs/'+slot+'/'+name

def components(body):
    names=('system','messages','tools') if 'messages' in body else ('instructions','input','tools','previous_response_id')
    return {k:body[k] for k in names if k in body}
def selected_bytes(body):return len(canonical(components(body)))
def byte_metric(raws):
    values=[selected_bytes(_decode(x)) for x in raws]
    component_values=[{k:len(canonical(v)) for k,v in components(_decode(raw)).items()} for raw in raws]
    before=component_values[0] if component_values else {};after=component_values[1] if len(component_values)==2 else {}
    changes={k:after.get(k,0)-before.get(k,0) for k in sorted(set(before)|set(after))} if len(values)==2 else {}
    delta=values[1]-values[0] if len(values)==2 else None
    return {'before':values[0] if values else None,'after':values[1] if len(values)==2 else None,'delta':delta,'wire':[len(x) for x in raws],'components_before':before,'components_after':after,'component_delta':changes,'serialization_wrapper_delta':delta-sum(changes.values()) if delta is not None else None}
def decision(values):
    if len(values)!=3:return 'direct_observation_incomplete'
    if min(values)>0 and statistics.median(values)>=4096:return 'larger_codex_native_selected_input_growth_in_this_configuration'
    if max(values)<0:return 'reversed_native_direction'
    return 'below_threshold_or_unstable_native_direction'

def usage_schema(obj):
    _need(isinstance(obj,dict),'usage_not_object')
    allowed={'input_tokens','output_tokens','total_tokens','input_tokens_details','output_tokens_details','cached_tokens','reasoning_tokens','cache_read_input_tokens','cache_creation_input_tokens','cache_creation','ephemeral_5m_input_tokens','ephemeral_1h_input_tokens','audio_tokens','accepted_prediction_tokens','rejected_prediction_tokens','server_tool_use','web_search_requests','web_fetch_requests','service_tier','inference_geo'}
    _need(set(obj)<=allowed,'usage_unknown_key')
    for k,v in obj.items():
        if isinstance(v,dict):usage_schema(v)
        elif k in {'service_tier','inference_geo'}:_need(v is None or isinstance(v,str),'usage_invalid')
        else:integer(v,nullable=True,minimum=0)

def usage_events(raw,index):
    out=[]
    for e in _events(raw):
        for source,obj in [('event',e),('message',e.get('message')),('response',e.get('response'))]:
            if isinstance(obj,dict) and isinstance(obj.get('usage'),dict):
                usage_schema(obj['usage']);out.append({'request':index,'event':e.get('type'),'source':source,'reported_usage':obj['usage']})
    return out

def opaque_values(body):
    out=[]
    def walk(o,path):
        if isinstance(o,dict):
            for k,v in o.items():
                p=path+'/'+k
                if k in {'encrypted_content','previous_response_id','signature','data'} and (k!='data' or o.get('type')=='redacted_thinking'):
                    raw=json.dumps(v,ensure_ascii=False,separators=(',',':')).encode();out.append((p,len(raw),digest(raw)))
                walk(v,p)
        elif isinstance(o,list):
            for i,v in enumerate(o):walk(v,path+'/'+str(i))
    walk(body,'');return out

def check_body(body,product):
    if product=='codex':
        required={'client_metadata','include','input','model','parallel_tool_calls','prompt_cache_key','reasoning','store','stream','tool_choice','tools'}
        _need(set(body)==required,'native_response_request_keys')
        keys(body['reasoning'],('effort','summary'));_need(body['reasoning']['effort']=='low' and body['reasoning']['summary']=='auto','effort')
        keys(body['client_metadata'],('root_turn_id','session_id','thread_id','turn_id','x-codex-installation-id','x-codex-turn-metadata','x-codex-window-id'),'client_metadata_keys')
        _need(all(isinstance(v,str) for v in body['client_metadata'].values()),'client_metadata')
        embedded=_decode(body['client_metadata']['x-codex-turn-metadata'].encode())
        keys(embedded,('agent_name','analytics_enabled','auto_review_enabled','context_window_id','history_initialization','installation_id','model','node_repl_auto_review_required','node_repl_disabled','reasoning_effort','request_kind','root_turn_id','sandbox','sandbox_mode','session_id','thread_id','thread_source','turn_id','turn_started_at_unix_ms','turn_trigger','window_id','window_number'),'embedded_metadata_keys')
        for k,v in embedded.items():
            if k in {'analytics_enabled','auto_review_enabled','node_repl_auto_review_required','node_repl_disabled'}:boolean(v)
            elif k in {'turn_started_at_unix_ms','window_number'}:integer(v,minimum=0)
            else:_need(isinstance(v,str),'embedded_metadata_type')
        _need(embedded['installation_id']==body['client_metadata']['x-codex-installation-id'],'installation_binding')
        _need(isinstance(body['input'],list),'history_type')
    else:
        keys(body,('max_tokens','messages','model','output_config','stream','system','thinking','tools'),'native_messages_request_keys')
        keys(body['thinking'],('type',));keys(body['output_config'],('effort',))
        _need(body['max_tokens']==1024 and type(body['max_tokens'])is int and body['thinking']['type']=='enabled' and body['output_config']['effort']=='low','effort_or_cap')
        _need(isinstance(body['messages'],list),'history_type')
    _need(body['model']=='deepseek-flash' and body['stream'] is True and isinstance(body['tools'],list),'model_stream_tools')

def text_content(value):
    if isinstance(value,str):return value
    _need(isinstance(value,list) and bool(value),'tool_text')
    for p in value:keys(p,('type','text'));_need(p['type'] in {'text','input_text','output_text'} and isinstance(p['text'],str),'tool_text')
    return ''.join(x['text'] for x in value)

def check_chain(first,second,response,product):
    excluded={'input','messages','client_metadata','prompt_cache_key'}
    _need(_same({k:v for k,v in first.items() if k not in excluded},{k:v for k,v in second.items() if k not in excluded}),'native_business_control_drift')
    _need(_same(first['tools'],second['tools']),'tools_drift')
    if product=='codex':
        snapshots=reconstruct(response);calls=_response_calls(response,'responses',('fixture_output','mcp__fixture'))
        before=first['input'];after=second['input'];_need(_same(after[:len(before)],before),'prefix_drift');suffix=after[len(before):]
        _need(len(suffix) in (2,3) and suffix[-1].get('type')=='function_call_output','suffix_shape')
        _need(history_matches(suffix[:-1],snapshots),'response_to_assistant_history_mismatch')
        returned=suffix[-1];cid=returned.get('call_id');_need(cid in calls and len(calls)==1,'return_call_identity')
        return text_content(returned.get('output'))
    history=messages_history(response);calls=_response_calls(response,'messages',('fixture_output',None))
    before=first['messages'];after=second['messages'];_need(_same(after[:len(before)],before) and len(after)==len(before)+2,'prefix_or_suffix_drift')
    _need(_same(after[-2],history),'response_to_assistant_history_mismatch')
    result=after[-1];keys(result,('role','content'));_need(result['role']=='user' and isinstance(result['content'],list) and len(result['content'])==1,'result_shape')
    returned=result['content'][0];_need(returned.get('type')=='tool_result' and returned.get('tool_use_id') in calls and len(calls)==1,'return_call_identity')
    return text_content(returned.get('content'))

def endpoint(raw,product):
    if product=='codex':
        snapshots=reconstruct(raw);_need(not _response_calls(raw,'responses',('fixture_output','mcp__fixture')),'final_has_call')
        text=''.join(p['text'] for item in snapshots if item.get('type')=='message' for p in item.get('content',[]) if p.get('type')=='output_text')
    else:
        snapshot=messages_history(raw);_need(not _response_calls(raw,'messages',('fixture_output',None)),'final_has_call')
        text=''.join(p['text'] for p in snapshot['content'] if p.get('type')=='text')
    try:value=_decode(text.encode());is_object=isinstance(value,dict)
    except (ValueError,TypeError):value={};is_object=False
    head=is_object and value.get('HEAD_KEY')=='AMBER-731';tail=is_object and value.get('TAIL_KEY')=='COBALT-492'
    return {'head':head,'tail':tail,'json_object_only':is_object,'information_retained':is_object and head and tail}


# Pure lifecycle/fixture validation; no session controller, profiles, routes or I/O.
def _events(raw):
    events=[];trailer=False
    text=raw.decode('utf-8').replace('\r\n','\n')
    frames=text.split('\n\n');_need(not frames[-1].strip(),'sse_frame_incomplete')
    for frame in frames[:-1]:
        names=[];data=[]
        for line in frame.split('\n'):
            if not line or line.startswith(':'):continue
            _need(':' in line,'sse_field_invalid')
            key,value=line.split(':',1);value=value.lstrip(' ')
            _need(key in {'event','data','id','retry'},'sse_field_unknown')
            if key=='event':names.append(value)
            if key=='data':data.append(value)
        _need(len(names)<=1,'sse_event_duplicate')
        if not data:continue
        content='\n'.join(data)
        _need(not trailer,'sse_event_after_trailer')
        if content=='[DONE]':
            _need(bool(events) and events[-1].get('type') in {'response.completed','message_stop'},'sse_trailer_early')
            trailer=True;continue
        obj=_decode(content.encode('utf-8'))
        _need(isinstance(obj,dict) and (not names or names[0]==obj.get('type')),'sse_event_type_conflict')
        events.append(obj)
    return events

def _response_calls(raw, protocol, expected):
    path = '/v1/messages' if protocol == 'messages' else '/responses'
    calls, blocks, items, call_ids, output_indices = {}, {}, {}, {}, {}
    completed, last_sequence, message_started = False, -1, False

    def empty_arguments(value):
        _need(isinstance(value,str) and bool(value), 'response_call_arguments_invalid')
        _need(_same(_decode(value.encode('utf-8')), {}), 'response_call_arguments_invalid')

    def identity(item):
        cid = item.get('call_id')
        ident = (item.get('name'),item.get('namespace'))
        _need(isinstance(cid,str) and bool(cid) and ident == expected, 'response_call_identity_invalid')
        return cid, ident

    for event in _events(raw):
        _need(isinstance(event,dict) and not completed, 'response_event_after_completion')
        kind = event.get('type')
        if protocol == 'messages':
            if kind == 'message_start':
                _need(not message_started and _same(event.get('message',{}).get('content'),[]), 'response_message_start_invalid')
                message_started = True
            elif kind == 'content_block_start':
                _need(message_started, 'response_message_start_missing')
                index, item = event.get('index'), event.get('content_block',{})
                _need(type(index) is int and index >= 0 and index not in blocks, 'response_block_alias')
                block = {'item':item,'delta':'','stopped':False}
                blocks[index] = block
                if item.get('type') == 'tool_use':
                    cid, ident = item.get('id'), (item.get('name'),item.get('namespace'))
                    _need(isinstance(cid,str) and bool(cid) and cid not in calls and ident == expected,
                          'response_call_identity_invalid')
                    _need(_same(item.get('input'),{}), 'response_call_arguments_invalid')
                    calls[cid] = ident
            elif kind == 'content_block_delta' and event.get('delta',{}).get('type') == 'input_json_delta':
                _need(type(event.get('index')) is int, 'response_block_alias')
                block = blocks.get(event.get('index'))
                _need(block is not None and block['item'].get('type') == 'tool_use' and not block['stopped'],
                      'response_call_arguments_invalid')
                delta = event['delta'].get('partial_json')
                _need(isinstance(delta,str) and bool(delta), 'response_call_arguments_invalid')
                block['delta'] += delta
            elif kind == 'content_block_stop':
                _need(type(event.get('index')) is int, 'response_block_alias')
                block = blocks.get(event.get('index'))
                _need(block is not None and not block['stopped'], 'response_block_alias')
                if block['delta']:
                    empty_arguments(block['delta'])
                block['stopped'] = True
            elif kind == 'message_stop':
                _need(message_started and all(block['stopped'] for block in blocks.values()), 'response_block_incomplete')
                completed = True
            continue

        sequence = event.get('sequence_number')
        if sequence is not None:
            _need(type(sequence) is int and sequence > last_sequence, 'response_sequence_duplicate_or_reordered')
            last_sequence = sequence
        if kind in {'response.output_item.added','response.output_item.done'}:
            item = event.get('item',{})
            if item.get('type') != 'function_call':
                continue
            iid, index = item.get('id'), event.get('output_index')
            _need(isinstance(iid,str) and bool(iid) and type(index) is int and index >= 0, 'response_item_id_invalid')
            cid, ident = identity(item)
            _need(cid not in call_ids or call_ids[cid] == iid, 'response_call_item_alias')
            _need(index not in output_indices or output_indices[index] == iid, 'response_output_index_alias')
            call_ids[cid], output_indices[index] = iid, iid
            if kind.endswith('.added'):
                _need(iid not in items, 'response_item_duplicate')
                initial = item.get('arguments')
                _need(isinstance(initial,str), 'response_call_arguments_invalid')
                items[iid] = {'cid':cid,'identity':ident,'index':index,'arguments':initial,
                              'has_fragments':bool(initial),'delta_seen':False,'arguments_done':False,
                              'done':False}
            else:
                state = items.get(iid)
                _need(state is not None and not state['done'] and state['cid'] == cid and state['identity'] == ident and
                      state['index'] == index, 'response_item_done_conflict')
                _need(item.get('status') == 'completed', 'response_item_not_completed')
                argument = item.get('arguments')
                empty_arguments(argument)
                if state['has_fragments'] or state['arguments_done']:
                    _need(argument == state['arguments'], 'response_arguments_reconstruction_conflict')
                    empty_arguments(state['arguments'])
                if state['delta_seen']:
                    _need(state['arguments_done'], 'response_arguments_done_missing')
                state['arguments'] = argument
                state['done'] = True
                calls[cid] = ident
        elif kind in {'response.function_call_arguments.delta','response.function_call_arguments.done'}:
            state = items.get(event.get('item_id'))
            _need(state is not None and not state['done'] and not state['arguments_done'] and
                  _same(event.get('output_index'),state['index']), 'response_arguments_item_conflict')
            if kind.endswith('.delta'):
                delta = event.get('delta')
                _need(isinstance(delta,str) and bool(delta), 'response_call_arguments_invalid')
                state['arguments'] += delta
                state['has_fragments'], state['delta_seen'] = True, True
            else:
                argument = event.get('arguments')
                empty_arguments(argument)
                if state['has_fragments']:
                    _need(argument == state['arguments'], 'response_arguments_reconstruction_conflict')
                    empty_arguments(state['arguments'])
                state['arguments'], state['arguments_done'] = argument, True
        elif kind == 'response.completed':
            output = event.get('response',{}).get('output')
            _need(isinstance(output,list) and all(isinstance(item,dict) for item in output), 'response_snapshot_invalid')
            final = [(index,item) for index,item in enumerate(output) if item.get('type') == 'function_call']
            _need(len(final) == len(items) and all(state['done'] for state in items.values()), 'response_snapshot_count_conflict')
            seen = set()
            for index,item in final:
                iid = item.get('id')
                state = items.get(iid)
                _need(iid not in seen and state is not None, 'response_snapshot_item_alias')
                seen.add(iid)
                cid, ident = identity(item)
                _need(state['cid'] == cid and state['identity'] == ident, 'response_snapshot_identity_conflict')
                _need(_same(state['index'],index), 'response_snapshot_index_conflict')
                _need(item.get('status') == 'completed', 'response_item_not_completed')
                _need(item.get('arguments') == state['arguments'], 'response_snapshot_arguments_conflict')
                empty_arguments(item.get('arguments'))
            completed = True
    _need(completed and len(calls) <= 1 and len(items) <= 1, 'response_multiple_or_incomplete_calls')
    if protocol == 'responses':
        reconstruct(raw)
    if protocol=='messages':
        messages_history(raw)
    return calls

def _returned_content(text, fixture, policy):
    """Validate provenance, not the final answer; never open any wire asset path."""
    raw = text.encode('utf-8')
    if raw == fixture:
        return
    kind = policy['returned_content_policy']
    _need(kind != 'fixture_exact', 'returned_content_not_fixture')
    if kind == 'codex_native_v1':
        wrapper = re.match(r'Wall time: (?:0|[1-9][0-9]*)(?:\.[0-9]+)? seconds\nOutput:',text)
        _need(wrapper is not None, 'returned_content_wrapper_invalid')
        text = text[wrapper.end():]
        if text.encode('utf-8') == fixture:
            return
        matches = list(re.finditer(r'…[0-9]+ tokens truncated…',text))
        _need(len(matches) == 1, 'returned_content_marker_invalid')
        marker = matches[0]
        head, tail = text[:marker.start()].encode('utf-8'), text[marker.end():].encode('utf-8')
    else:
        footer = re.search(r'\n\n\(Omitted ([1-9][0-9]*) bytes\. Full formatted result stored at: '
                           r'(/[^\r\n()]+)\. Use read with offset/limit, or grep this path to search within it\.\)$',text)
        _need(footer is not None, 'returned_content_wrapper_invalid')
        retained = text[:footer.start()]
        marker = '\n\n[...]\n\n'
        _need(retained.count(marker) == 1, 'returned_content_marker_invalid')
        first, last = retained.split(marker)
        head, tail = first.encode('utf-8'), last.encode('utf-8')
        _need(int(footer.group(1)) == len(fixture)-len(head)-len(tail), 'returned_content_omitted_bytes_invalid')
    _need(len(head) >= 32 and len(tail) >= 32 and len(head)+len(tail) < len(fixture) and
          fixture.startswith(head) and fixture.endswith(tail), 'returned_content_not_fixture')

"""Strict Responses stream -> snapshot -> native history provenance. No I/O."""
import copy

def reconstruct(raw):
    states, indices = {}, {}
    completed = None
    last = -1;phase=0;root=None
    for e in _events(raw):
        _need(isinstance(e,dict) and completed is None, 'provenance_after_completion')
        seq=e.get('sequence_number')
        _need(type(seq) is int and seq > last, 'provenance_sequence')
        last=seq; kind=e.get('type')
        if kind in {'response.created','response.in_progress'}:
            response=e.get('response',{})
            _need(not states and response.get('output')==[] and response.get('status')=='in_progress','provenance_initial_snapshot')
            core={k:response.get(k) for k in ('id','object','created_at','model')}
            _need(isinstance(core['id'],str) and bool(core['id']) and isinstance(core['model'],str),'provenance_root_identity')
            if kind=='response.created':
                _need(phase==0,'provenance_created_order');phase=1;root=core
            else:
                _need(phase==1 and _same(core,root),'provenance_progress_order');phase=2
            continue
        _need(phase==2,'provenance_root_lifecycle_missing')
        if kind == 'response.completed':
            _need(_same({k:e.get('response',{}).get(k) for k in root},root),'provenance_root_identity')
            output=e.get('response',{}).get('output')
            _need(e.get('response',{}).get('status')=='completed' and isinstance(output,list), 'provenance_completion')
            _need(sorted(indices)==list(range(len(output))) and len(output)==len(states), 'provenance_snapshot_count')
            _need(all(s['done'] is not None for s in states.values()), 'provenance_item_incomplete')
            _need(_same(output,[states[indices[i]]['done'] for i in range(len(output))]), 'provenance_snapshot_conflict')
            completed=copy.deepcopy(output);continue
        if kind == 'response.output_item.added':
            item=e.get('item');idx=e.get('output_index')
            _need(isinstance(item,dict) and item.get('type') in {'reasoning','function_call','message'}, 'provenance_item_type')
            iid=item.get('id')
            _need(isinstance(iid,str) and bool(iid) and iid not in states and type(idx)is int and idx>=0 and idx not in indices, 'provenance_alias')
            _need(item.get('status')=='in_progress','provenance_item_status')
            states[iid]={'initial':copy.deepcopy(item),'index':idx,'parts':{},'summary':{},'done':None}
            indices[idx]=iid;continue
        iid=e.get('item',{}).get('id') if kind=='response.output_item.done' else e.get('item_id')
        s=states.get(iid)
        _need(s is not None and s['done'] is None and type(e.get('output_index'))is int and e['output_index']==s['index'], 'provenance_item_reference')
        if kind == 'response.output_item.done':
            item=e['item'];initial=s['initial'];itype=initial['type']
            _need(item.get('status')=='completed' and item.get('type')==itype, 'provenance_item_status')
            mutable={'status','arguments'} if itype=='function_call' else {'status','content','summary'}
            _need(_same({k:v for k,v in initial.items() if k not in mutable},{k:v for k,v in item.items() if k not in mutable}), 'provenance_opaque_or_identity_conflict')
            if itype!='function_call':
                for field,key in [('content','parts'),('summary','summary')]:
                    parts=s[key]
                    _need(sorted(parts)==list(range(len(parts))) and all(p['closed'] for p in parts.values()), 'provenance_part_incomplete')
                    observed=[parts[i]['final'] for i in range(len(parts))]
                    _need(_same(item.get(field,[]),observed), 'provenance_content_conflict')
                    _need(initial.get(field,[])==[], 'provenance_initial_content')
            s['done']=copy.deepcopy(item);continue
        if kind in {'response.function_call_arguments.delta','response.function_call_arguments.done'}:
            _need(s['initial']['type']=='function_call','provenance_arguments_type')
            # Existing call lifecycle gate reconstructs arguments including initial text.
            continue
        summary=kind.startswith('response.reasoning_summary_')
        store=s['summary'] if summary else s['parts']
        index=e.get('summary_index') if summary else e.get('content_index')
        _need(type(index)is int and index>=0,'provenance_part_index')
        part_added=kind in {'response.content_part.added','response.reasoning_summary_part.added'}
        part_done=kind in {'response.content_part.done','response.reasoning_summary_part.done'}
        if part_added:
            p=e.get('part');allowed=({'summary_text'} if summary else {'reasoning_text'}) if s['initial']['type']=='reasoning' else {'output_text'}
            _need(index not in store and isinstance(p,dict) and p.get('type') in allowed and p.get('text')=='','provenance_part_added')
            store[index]={'initial':copy.deepcopy(p),'text':'','text_done':False,'closed':False,'final':None};continue
        p=store.get(index)
        _need(p is not None and not p['closed'], 'provenance_part_reference')
        if part_done:
            expected=dict(p['initial'],text=p['text'])
            _need(p['text_done'] and _same(e.get('part'),expected),'provenance_part_done_conflict')
            p['final']=copy.deepcopy(e['part']);p['closed']=True;continue
        expected_type={'reasoning_text':'response.reasoning_text','summary_text':'response.reasoning_summary_text','output_text':'response.output_text'}[p['initial']['type']]
        _need(kind in {expected_type+'.delta',expected_type+'.done'} and not p['text_done'], 'provenance_unknown_or_late_event')
        if kind.endswith('.delta'):
            _need(isinstance(e.get('delta'),str) and bool(e['delta']),'provenance_delta')
            p['text']+=e['delta']
        else:
            _need(e.get('text')==p['text'],'provenance_text_done_conflict');p['text_done']=True
    _need(completed is not None,'provenance_completion_missing')
    return completed

def history_matches(actual, snapshot):
    """Exactly full wire snapshot OR observed native projection, never field stripping."""
    if _same(actual,snapshot):return True
    projected=[]
    for item in snapshot:
        item=copy.deepcopy(item)
        if item['type']=='reasoning':
            item.pop('id',None);item.pop('status',None)
        elif item['type']=='function_call':item.pop('id',None)
        else:return False
        projected.append(item)
    return _same(actual,projected)


def messages_history(raw):
    """Native Messages full lifecycle; text/thinking/signature cannot outlive a block."""
    blocks={};active=None;started=False;ended=False;stopping=False
    for e in _events(raw):
        _need(isinstance(e,dict) and not ended,'messages_event_after_completion')
        kind=e.get('type')
        if kind=='ping':continue
        if kind=='message_start':
            _need(not started and _same(e.get('message',{}).get('content'),[]),'messages_start_invalid')
            started=True;continue
        _need(started,'messages_start_missing')
        if kind=='content_block_start':
            index=e.get('index');item=e.get('content_block')
            _need(not stopping and active is None and type(index)is int and index==len(blocks) and isinstance(item,dict),'messages_block_alias')
            t=item.get('type')
            _need(t in {'tool_use','text','thinking','redacted_thinking'},'messages_block_type')
            if t=='tool_use':_need(_same(item.get('input'),{}),'messages_initial_input')
            if t=='text':_need(item.get('text')=='','messages_initial_text')
            if t=='thinking':_need(item.get('thinking')=='' and item.get('signature','')=='','messages_initial_thinking')
            blocks[index]={'item':copy.deepcopy(item),'arguments':'','signature_seen':False,'closed':False};active=index;continue
        if kind in {'content_block_delta','content_block_stop'}:
            index=e.get('index')
            _need(not stopping and type(index)is int and active==index and index in blocks and not blocks[index]['closed'],'messages_block_reference')
            b=blocks[index];item=b['item']
            if kind=='content_block_stop':
                if item['type']=='tool_use' and b['arguments']:
                    item['input']=_decode(b['arguments'].encode());_need(_same(item['input'],{}),'messages_arguments')
                b['closed']=True;active=None;continue
            delta=e.get('delta');_need(isinstance(delta,dict),'messages_delta_invalid');t=delta.get('type')
            fields={'text_delta':('text','text'),'thinking_delta':('thinking','thinking'),'signature_delta':('thinking','signature'),'input_json_delta':('tool_use','partial_json')}
            _need(t in fields,'messages_delta_unknown');expected,field=fields[t]
            _need(item['type']==expected and set(delta)=={'type',field} and isinstance(delta.get(field),str) and bool(delta[field]),'messages_delta_invalid')
            _need(t!='thinking_delta' or not b['signature_seen'],'messages_thinking_after_signature')
            if t=='input_json_delta':b['arguments']+=delta[field]
            else:
                item[field]=item.get(field,'')+delta[field]
                if t=='signature_delta':b['signature_seen']=True
            continue
        if kind=='message_delta':
            _need(not stopping and active is None and all(b['closed'] for b in blocks.values()) and bool(blocks),'messages_delta_order')
            reason=e.get('delta',{}).get('stop_reason');has_call=any(b['item']['type']=='tool_use' for b in blocks.values())
            _need(reason==('tool_use' if has_call else 'end_turn'),'messages_stop_reason')
            stopping=True;continue
        if kind=='message_stop':
            _need(stopping and active is None,'messages_stop_incomplete');ended=True;continue
        _need(False,'messages_unknown_event')
    _need(ended,'messages_completion_missing')
    return {'role':'assistant','content':[b['item'] for b in blocks.values()]}
