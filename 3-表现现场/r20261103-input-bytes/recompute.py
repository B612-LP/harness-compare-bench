#!/usr/bin/env python3
"""Recompute client-side input bytes from captured requests; no model/network.
Usage: python3 analyze.py --root DIR --output NEW_DIR
Raw captures are private. Public metrics use relative run references, not home paths.
"""
import argparse, hashlib, json, math, re, statistics
from pathlib import Path

KEYS={'HEAD_KEY':'AMBER-731','TAIL_KEY':'COBALT-492'}
FIXTURE_NAMES={'fixture_output','mcp__fixture__fixture_output'}
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def events(text):
    out=[]
    frames=text.replace('\r\n','\n').split('\n\n')
    if frames[-1].strip():raise ValueError('Truncated SSE frame')
    for frame in frames[:-1]:
        lines=[line[5:].lstrip(' ') for line in frame.split('\n') if line.startswith('data:')]
        s='\n'.join(lines)
        if s and s!='[DONE]':out.append(json.loads(s))
    return out

def text_content(x):
    if isinstance(x,str):return x
    if isinstance(x,list):
        if not all(isinstance(c,dict) and c.get('type') in ('text','input_text','output_text') and isinstance(c.get('text'),str) for c in x):
            raise ValueError('Non-text tool content cannot be silently dropped')
        return ''.join(c['text'] for c in x)
    raise ValueError('Unexpected tool content type')

def components(body):
    if 'messages' in body:
        names=('system','messages','tools')
    elif 'input' in body:
        names=('instructions','input','tools','previous_response_id')
    else:raise ValueError('No supported client input field')
    data={k:body[k] for k in names if k in body}
    return data,{k:len(canonical(v)) for k,v in data.items()}

def allowed_call_name(c):
    name=c.get('name');ns=c.get('namespace')
    if ns is not None and (ns!='mcp__fixture' or name!='fixture_output'):return None
    return name if name in FIXTURE_NAMES else None

def tool_return(body):
    calls={};returned=[]
    if 'messages' in body:
        for m in body['messages']:
            if not isinstance(m.get('content'),list):continue
            for c in m['content']:
                if c.get('type')=='tool_use':calls[c['id']]=c.get('name')
                if c.get('type')=='tool_result':returned.append((c.get('tool_use_id'),text_content(c.get('content'))))
    else:
        for c in body.get('input',[]):
            if c.get('type')=='function_call':calls[c['call_id']]=allowed_call_name(c)
            if c.get('type')=='function_call_output':returned.append((c.get('call_id'),text_content(c.get('output'))))
    if len(returned)!=1:raise ValueError('Need exactly one tool return, not a selected subset')
    cid,text=returned[0]
    if calls.get(cid) not in FIXTURE_NAMES:raise ValueError('Tool output is missing a matching allowed call ID')
    return cid,text

def final_text(es):
    a=[];fallback=[]
    for e in es:
        t=e.get('type')
        if t=='content_block_delta' and e.get('delta',{}).get('type')=='text_delta':a.append(e['delta'].get('text',''))
        elif t=='content_block_start' and e.get('content_block',{}).get('type')=='text':a.append(e['content_block'].get('text',''))
        elif t=='response.output_text.delta':a.append(e.get('delta',''))
        elif t=='response.completed':
            for item in e.get('response',{}).get('output',[]):
                if item.get('type')=='message':
                    fallback.extend(c.get('text','') for c in item.get('content',[]) if c.get('type')=='output_text')
    return ''.join(a) if a else ''.join(fallback)

def response_call_ids(es):
    found={}
    for e in es:
        if e.get('type')=='content_block_start':
            c=e.get('content_block',{})
            if c.get('type')=='tool_use':found[c.get('id')]=c.get('name')
        c=e.get('item',{})
        if c.get('type')=='function_call':found[c.get('call_id')]=allowed_call_name(c)
        for c in e.get('response',{}).get('output',[]):
            if c.get('type')=='function_call':found[c.get('call_id')]=allowed_call_name(c)
    return found

def complete(es):return any(e.get('type') in ('message_stop','response.completed') for e in es)

def measure(run):
    meta=read(run/'run-meta.json');end=read(run/'end.json')
    row={k:meta.get(k) for k in ('run_id','logical_slot_id','attempt_id','product','phase','arm','track','category','mode','reasoning_setting','max_inline_tokens')}
    row.update({'source_dir':'runs/'+run.name,'process_exit_code':end.get('exit_code'),'timeout':end.get('timeout'),'primary_valid':False,'invalid_reasons':[]})
    files=sorted((run/'capture').glob('*-request.json'))
    row['request_count']=len(files)
    if len(files)!=2:row['invalid_reasons'].append('need_exactly_two_requests');return row
    first,second=map(read,files)
    a,ca=components(first);b,cb=components(second)
    row.update({'input_field_names':list(a),'B_input_before':len(canonical(a)),'B_input_after':len(canonical(b)),'component_bytes_before':ca,'component_bytes_after':cb,'component_delta':{k:cb.get(k,0)-ca.get(k,0) for k in set(ca)|set(cb)},'before_input_sha256':hashlib.sha256(canonical(a)).hexdigest(),'request_json_sha256':[sha(p) for p in files],'model_before':first.get('model'),'model_after':second.get('model'),'actual_reasoning_controlled':False,'server_final_input_observed':False,'opaque_server_reference_present':bool(second.get('previous_response_id'))})
    row['delta_B_input']=row['B_input_after']-row['B_input_before']
    row['serialization_wrapper_delta']=row['delta_B_input']-sum(row['component_delta'].values())
    row['request_control']={k:first.get(k) for k in ('model','thinking','output_config','reasoning','max_tokens','max_output_tokens','temperature','tool_choice') if k in first}
    rawfiles=[p.with_suffix('.raw') for p in files]
    if all(p.is_file() for p in rawfiles):
        row['B_body_wire']=[p.stat().st_size for p in rawfiles];row['body_wire_sha256']=[sha(p) for p in rawfiles]
    else:row['invalid_reasons'].append('missing_raw_request_bytes')
    row['tool_schema_names']=[t.get('name',t.get('function',{}).get('name',t.get('type'))) for t in first.get('tools',[])]
    effort=first.get('output_config',{}).get('effort') if 'messages' in first else first.get('reasoning',{}).get('effort')
    second_effort=second.get('output_config',{}).get('effort') if 'messages' in second else second.get('reasoning',{}).get('effort')
    if effort!='low' or second_effort!='low':row['invalid_reasons'].append('reasoning_setting_not_low')
    if first.get('tools')!=second.get('tools'):row['invalid_reasons'].append('tool_schema_drift_within_session')
    try:
        cid,text=tool_return(second);row['tool_call_id']=cid;row['B_tool_returned']=len(text.encode('utf-8'));row['returned_tool_sha256']=hashlib.sha256(text.encode('utf-8')).hexdigest()
        first_sse=events((run/'capture'/files[0].name.replace('-request.json','-response.sse')).read_text())
        second_sse=events((run/'capture'/files[1].name.replace('-request.json','-response.sse')).read_text())
        if response_call_ids(first_sse).get(cid) not in FIXTURE_NAMES:row['invalid_reasons'].append('response_to_tool_id_mismatch')
        if not complete(first_sse) or not complete(second_sse):row['invalid_reasons'].append('response_incomplete')
        final=final_text(second_sse);row['final_text']=final
        try:
            answer=json.loads(final)
            row['key_hits']={k:answer.get(k)==v for k,v in KEYS.items()} if isinstance(answer,dict) else {k:False for k in KEYS}
            row['json_object_only']=isinstance(answer,dict)
        except (ValueError,TypeError):row['key_hits']={k:False for k in KEYS};row['json_object_only']=False
        row['information_retained']=row['json_object_only'] and all(row['key_hits'].values())
    except (ValueError,OSError,KeyError,TypeError) as exc:row['invalid_reasons'].append('tool_or_response_link:'+type(exc).__name__)
    tool=run/'capture/tool-output.txt'
    if tool.is_file():
        row.update({'B_fixture':tool.stat().st_size,'fixture_sha256':sha(tool)})
        if row['B_fixture']!=35767 or row['fixture_sha256']!='fed57592028c9d8a9180c2b97f74a3cd5e0daa841aab244cf4aad78fe44626a2':row['invalid_reasons'].append('fixture_size_or_hash_mismatch')
    else:row['invalid_reasons'].append('fixture_not_called')
    if end.get('exit_code')!=0 or end.get('timeout'):row['invalid_reasons'].append('process_failed_or_timed_out')
    if first.get('model')!='deepseek-flash' or second.get('model')!='deepseek-flash':row['invalid_reasons'].append('model_drift')
    row['primary_valid']=not row['invalid_reasons']
    return row

def wilson(k,n):
    if not n:return None
    z=1.959963984540054;d=1+z*z/n;c=(k/n+z*z/(2*n))/d;r=z*math.sqrt(k/n*(1-k/n)/n+z*z/(4*n*n))/d
    return [max(0,c-r),min(1,c+r)]

def summarize(root):
    rows=[]
    planned={p['slot']:p for p in read(root/'freeze.json')['plan']} if (root/'freeze.json').is_file() else {}
    for run in sorted((root/'runs').iterdir()):
        if not (run/'run-meta.json').is_file() and run.name not in planned:continue
        try:rows.append(measure(run))
        except Exception as exc:
            try:meta=read(run/'run-meta.json')
            except Exception:meta={}
            row={k:meta.get(k) for k in ('phase','arm','product','mode','category')}
            row.update({'run_id':run.name,'primary_valid':False,'invalid_reasons':['unparseable_or_unfinished:'+type(exc).__name__]})
            if run.name in planned:row.update({'phase':'confirmation','arm':planned[run.name]['arm'],'product':planned[run.name]['product']})
            rows.append(row)
    confirm=[r for r in rows if r.get('phase')=='confirmation'];pairs=[]
    for block in range(1,7):
        m={r.get('arm'):r for r in confirm if r.get('product')=='dsh' and r['run_id'].startswith(f'confirm-b{block:02d}-')}
        p={'block':block,'valid':False}
        if all(a in m and m[a].get('primary_valid') for a in ('inline','bounded')):
            u,v=m['inline'],m['bounded']; p.update({'valid':True,'inline_run':u['run_id'],'bounded_run':v['run_id'],'reduction_bytes':u['delta_B_input']-v['delta_B_input'],'bounded_information_retained':v.get('information_retained'),'inline_information_retained':u.get('information_retained'),'first_request_input_equal':u['before_input_sha256']==v['before_input_sha256']})
            if not p['first_request_input_equal']:p['valid']=False;p['reason']='first_request_input_drift'
        pairs.append(p)
    valid=[p for p in pairs if p['valid']];values=[p['reduction_bytes'] for p in valid]
    branch='direct_observation_or_control_incomplete'
    if len(valid)==6:
        if min(values)>0 and statistics.median(values)>=16384:
            branch='repeated_direction_information_retained' if all(p['bounded_information_retained'] and p['inline_information_retained'] for p in valid) else 'load_reduced_but_information_impaired'
        else:branch='unstable_or_reversed_direction'
    return {'schema_version':1,'scope':'instrumented client-side assembly; one fixture and version; not formal A/B/W','serialization':'UTF-8 JSON ensure_ascii=False sort_keys=True separators=(comma,colon); selected input fields only; tool content decoded without wrapper','rows':rows,'paired_dsh':pairs,'confirmation_attempts':len(confirm),'valid_pairs':len(valid),'decision_branch':branch,'reduction_summary':{'median':statistics.median(values),'mean':statistics.mean(values),'min':min(values),'max':max(values)} if values else None,'positive_direction_wilson95':wilson(sum(x>0 for x in values),len(values)),'positive_direction_sign_test_two_sided':2/2**len(values) if values and (min(values)>0 or max(values)<0) else None,'sign_test_note':'Descriptive paired sign calculation, not a multi-task population or equivalence claim','third_party_verification':'pending'}

def markdown(data):
    s=['# Instrumented mechanism results','','Client-side UTF-8 assembly bytes; not tokens, costs, or final server model input. No formal product scores change.','',f"Decision branch: `{data['decision_branch']}`; valid DSH pairs {data['valid_pairs']}/6.",'','| Run | Phase | Arm | Valid | Δ input bytes | Tool bytes | HEAD/TAIL retained |','|---|---|---|---|---:|---:|---|']
    for r in data['rows']:s.append('| {run_id} | {phase} | {arm} | {primary_valid} | {delta} | {tool} | {info} |'.format(**dict({'phase':'unknown','arm':'unknown'},**r),delta=r.get('delta_B_input','unknown'),tool=r.get('B_tool_returned','unknown'),info=r.get('information_retained','unknown')))
    s.extend(['','| Block | Valid | Inline minus bounded Δ bytes | First input equal |','|---|---|---:|---|'])
    for p in data['paired_dsh']:s.append(f"| {p['block']} | {p['valid']} | {p.get('reduction_bytes','unknown')} | {p.get('first_request_input_equal','unknown')} |")
    s.extend(['','## Limits','- Native system/tool/schema and output budgets can differ between products. Only DSH local threshold contrast is an intervention.','- The relay buffers streaming responses and changes chunk timing/latency; no native latency or universal cost comparison.','- Reasoning setting is low, not control of actual reasoning tokens; backend context/cache/rewriting remain unseen.','- Pilots and mock calibrations are not confirmation samples. Missing/invalid attempts remain in the table.','- Real third-party witness and external public-entry reading remain pending.'])
    return '\n'.join(s)+'\n'

def main():
    a=argparse.ArgumentParser();a.add_argument('--root',type=Path,default=Path(__file__).resolve().parent);a.add_argument('--output',type=Path,required=True);args=a.parse_args()
    data=summarize(args.root);args.output.mkdir(parents=True,exist_ok=False)
    (args.output/'metrics.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');(args.output/'RESULTS.md').write_text(markdown(data))
    print(json.dumps({'rows':len(data['rows']),'valid_pairs':data['valid_pairs'],'branch':data['decision_branch']}))
if __name__=='__main__':main()
