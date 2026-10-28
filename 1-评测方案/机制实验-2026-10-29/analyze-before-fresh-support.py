#!/usr/bin/env python3
"""Offline analysis: reads only public experiment evidence; performs no API calls."""
import argparse,hashlib,json,pathlib,re,datetime
R=pathlib.Path(__file__).resolve().parent
DEFAULT=R.parents[1]/'3-表现现场/r20261029-mechanism'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def sse(p):
    result=[]
    for line in p.read_text().splitlines():
        if line.startswith('data: '):
            try:result.append(json.loads(line[6:]))
            except ValueError:pass
    return result
def normalize(v):
    if isinstance(v,dict):return {k:('<DYNAMIC_ID>' if k in ['id','tool_use_id','signature'] else normalize(x)) for k,x in v.items()}
    if isinstance(v,list):return [normalize(x) for x in v]
    return v

def differences(a,b,p=''):
    if type(a)!=type(b):return [p]
    if isinstance(a,dict):
        return [q for k in sorted(set(a)|set(b)) for q in ([p+'/'+k] if k not in a or k not in b else differences(a[k],b[k],p+'/'+k))]
    if isinstance(a,list):
        if len(a)!=len(b):return [p+'/length']
        return [q for i,(x,y) in enumerate(zip(a,b)) for q in differences(x,y,p+'/'+str(i))]
    return [] if a==b else [p]
def tool_text(req):
    return '\n'.join(c.get('text','') for m in req.get('messages',[]) for b in m.get('content',[]) if b.get('type')=='tool_result' for c in b.get('content',[]) if c.get('type')=='text')
def calls(out):
    values=[]
    for n in ['01','02']:
        req=load(out/f'{n}-request.json');transport=load(out/f'{n}-transport.json');resp=load(out/f'{n}-response-meta.json')
        events=sse(out/f'{n}-response.sse') if (out/f'{n}-response.sse').exists() else []
        usage={};models=[]
        for e in events:
            usage.update(e.get('message',{}).get('usage',{}));usage.update(e.get('usage',{}))
            if e.get('message',{}).get('model'):models.append(e['message']['model'])
        # v3 only: provider's parsed durable stream is available, not raw SSE.
        recovered=False
        if not usage:
            stream=[json.loads(x) for x in (out/'session-recovered.jsonl').read_text().splitlines()]
            messages=[x for x in stream if x.get('type')=='assistant/message']
            u=messages[int(n)-1]['data']['usage']
            usage={'input_tokens':u['inputTokens'],'output_tokens':u['outputTokens'],'cache_read_input_tokens':u.get('cacheReadTokens',0),'cache_creation_input_tokens':u.get('cacheWriteTokens',0)}
            models=[messages[int(n)-1]['data']['message']['source']['model']];recovered=True
        total=sum(usage.get(k,0) for k in ['input_tokens','cache_read_input_tokens','cache_creation_input_tokens'])
        text=tool_text(req)
        values.append({'number':int(n),'host':transport['host'],'status':resp['status'],'request_model':req['model'],'effort':req['output_config']['effort'],'max_tokens':req['max_tokens'],'raw_usage':usage,'total_input_including_cache':total,'response_models':models,'usage_source':'durable_provider_parsed_stream' if recovered else 'raw_response_sse','raw_sse_available':not recovered,'message_stop_seen':any(e.get('type')=='message_stop' for e in events),'tool_result_bytes':len(text.encode()),'tool_result_sha256':hashlib.sha256(text.encode()).hexdigest(),'spilled':'Full formatted result stored at:' in text,'head_visible':'AMBER-731' in text,'tail_visible':'COBALT-492' in text,'middle_noise_visible':'noise-0210' in text})
    return values

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--evidence',type=pathlib.Path,default=DEFAULT);g=ap.add_mutually_exclusive_group(required=True);g.add_argument('--output',type=pathlib.Path);g.add_argument('--verify',action='store_true');a=ap.parse_args();e=a.evidence.resolve();runs=[]
    paths=sorted(list((e/'v3').glob('20*/run-meta.json'))+list((e/'v4').glob('20*/run-meta.json')))
    for p in paths:
        m=load(p);out=p.parent
        if not (out/'02-request.json').exists():raise SystemExit('Incomplete actual run: '+str(out))
        stdout=[json.loads(x) for x in (out/'stdout.txt').read_text().splitlines() if x.strip().startswith('{')]
        final=next((x.get('text','') for x in reversed(stdout) if x.get('type')=='final'),'')
        try:answer=json.loads(final)
        except ValueError:answer=None
        records=calls(out)
        runs.append({'run_id':m['run_id'],'path':str(out.relative_to(e)),'size':m['size'],'arm':m['arm'],'maxInlineTokens':m['maxInlineTokens'],'exit_code':m['exit_code'],'start':m['start'],'end':m['end'],'calls':records,'answer':answer,'correct':answer=={'HEAD_KEY':'AMBER-731','TAIL_KEY':'COBALT-492'},'original_actual_api_gate':m['actual_api_gate'],'v3_observer_gap':out.parent.name=='v3','tool_output_bytes':(out/'tool-output.txt').stat().st_size,'tool_output_sha256':sha(out/'tool-output.txt')})
    pairs=[]
    for i,(fi,bi) in enumerate([(0,1),(3,2),(4,5)],1):
        if max(fi,bi)>=len(runs):continue
        f,b=runs[fi],runs[bi];fr=load(e/f['path']/'02-request.json');br=load(e/b['path']/'02-request.json')
        f1=load(e/f['path']/'01-request.json');b1=load(e/b['path']/'01-request.json')
        diff=differences(normalize(fr),normalize(br))
        tool_paths=[x for x in diff if re.fullmatch(r'/messages/\d+/content/\d+/content/\d+/text',x)]
        pairs.append({'pair':i,'size':f['size'],'full_run':f['run_id'],'bounded_run':b['run_id'],'full_second_input':f['calls'][1]['total_input_including_cache'],'bounded_second_input':b['calls'][1]['total_input_including_cache'],'second_input_difference':f['calls'][1]['total_input_including_cache']-b['calls'][1]['total_input_including_cache'],'first_request_exact_differences':differences(f1,b1),'second_request_differences_after_dynamic_id_normalization':diff,'dynamic_fields_normalized':['id','tool_use_id','signature'],'tool_result_difference_paths':tool_paths,'raw_sse_both':all(c['raw_sse_available'] for r in [f,b] for c in r['calls']),'original_tool_stdout_identical':f['tool_output_sha256']==b['tool_output_sha256']})
    source_checks=[]
    for freeze in [e/'freeze.json',e/'v2/freeze.json',e/'v3/freeze.json',e/'v4/freeze.json']:
        f=load(freeze);source_checks.append({'freeze':str(freeze.relative_to(e)),'frozen_at':f['frozen_at'],'files':[{'path':n,'expected_sha256':h,'actual_sha256':sha(R/n),'matches':sha(R/n)==h} for n,h in f['files'].items()]})
    findings={'schema_version':1,'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'usage_semantics':'Anthropic Messages fields are disjoint: uncached input_tokens + cache_read_input_tokens + cache_creation_input_tokens. DSH 0.2.0-rc.2 transport maps fields independently and totalTokens adds all three plus output. Do not equate token reduction with monetary savings. v3 raw fields reconstructed from lossless provider-parsed camelCase usage; not raw SSE.','runs':runs,'pairs':pairs,'actual_runs':len(runs),'actual_requests':sum(len(r['calls']) for r in runs),'total_input_including_cache':sum(c['total_input_including_cache'] for r in runs for c in r['calls']),'correct_runs':sum(r['correct'] for r in runs),'frozen_source_checks':source_checks}
    expected=[('large','full',12500),('large','bounded',512),('large','bounded',512),('large','full',12500),('small','full',12500),('small','bounded',512)]
    checks={'six_runs_fixed_order':[(r['size'],r['arm'],r['maxInlineTokens']) for r in runs]==expected,'twelve_requests':findings['actual_requests']==12 and all(len(list((e/r['path']).glob('*-request.json')))==2 for r in runs),'all_http200':all(c['status']==200 for r in runs for c in r['calls']),'official_low_route':all(c['host']=='api.deepseek.com' and c['request_model']=='deepseek-flash' and c['effort']=='low' and c['max_tokens']==1024 and c['response_models']==['deepseek-flash'] for r in runs for c in r['calls']),'frozen_sources_match':all(x['matches'] for f in source_checks for x in f['files']),'three_prespecified_pairs':len(pairs)==3 and all(p['original_tool_stdout_identical'] for p in pairs),'first_requests_identical':bool(runs) and all(load(e/r['path']/'01-request.json')==load(e/runs[0]['path']/'01-request.json') for r in runs),'all_process_exit0':all(r['exit_code']==0 for r in runs),'within_input_budget':findings['total_input_including_cache']<=150000,'raw_sse_all_remaining_calls':all(c['raw_sse_available'] and c['message_stop_seen'] for r in runs[1:] for c in r['calls'])}
    if not all(checks.values()):print(json.dumps({'checks':checks,'validation_passed':False}));raise SystemExit(1)
    if a.verify:
        old=load(e/'analysis.json');old.pop('generated_at',None);new=dict(findings);new.pop('generated_at',None)
        checks['matches_published_analysis_ignoring_generated_at']=old==new
        if old!=new:print(json.dumps({'checks':checks,'differences':differences(old,new),'validation_passed':False}));raise SystemExit(1)
    else:
        with a.output.open('x') as f:f.write(json.dumps(findings,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'runs':len(runs),'pairs':[(p['pair'],p['second_input_difference']) for p in pairs],'total_input':findings['total_input_including_cache'],'correct':findings['correct_runs'],'checks':checks,'validation_passed':True},ensure_ascii=False))
if __name__=='__main__':main()
