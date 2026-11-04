#!/usr/bin/env python3
"""Offline checks of this explicit public projection, not a live runner or original seal."""
import argparse,hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
def read(p):return json.loads(p.read_bytes())
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def selected(b):return {k:b[k] for k in ('instructions','input','tools','previous_response_id') if k in b}
def verify():
    checks=[]
    def check(name,condition):
        checks.append({'check':name,'passed':bool(condition)})
        if not condition:raise ValueError('Public projection check failed: '+name)
    manifest=read(HERE/'publication-manifest.json')
    for item in manifest['files']:
        p=(REPO/item['path']).resolve();check('manifest target contained',p.is_relative_to(REPO.resolve()))
        data=p.read_bytes();check('manifest hash and length: '+item['path'],len(data)==item['bytes'] and sha(data)==item['sha256'])
    mapping=read(HERE/'projection-map.json')
    for name,item in mapping['entries'].items():
        data=(REPO/name).read_bytes();check('projection hash and length: '+name,sha(data)==item['public_sha256'] and len(data)==item['public_bytes'])
        iv=item.get('invariants',{})
        if iv.get('body_length_preserved'):
            body=json.loads(data)
            check('body byte invariant: '+name,len(data)==iv['original_body_bytes']==iv['public_body_bytes'])
            check('selected byte invariant: '+name,len(canonical(selected(body)))==iv['original_selected_input_bytes']==iv['public_selected_input_bytes'])
    batch=read(HERE/'batch-events.json');summary=batch['summary'];events=batch['events']
    check('six explicit events and no formal promotion',len(events)==summary['event_rows']==6 and summary['formal_admissions']==0)
    check('one research run, four nonproduct mocks, one interface preflight',summary['counts']=={'product_run':1,'self_test':0,'offline_recompute':0,'grading_regression':0,'bare_model_probe':0,'interface_preflight':1,'non_product_reference':4})
    for event in events:
        for ref in event.get('source_refs',[]):
            data=(REPO/ref['path']).read_bytes();check('source derived mapping',sha(data)==ref['public_derived_sha256']==mapping['entries'][ref['path']]['public_sha256'])
    run=HERE/'runs/pilot-codex-native-v3';cap=run/'capture'
    metas=[read(cap/('%02d-meta.json'%i)) for i in (1,2)]
    check('strict observed forwarding counters',all(type(m.get('upstream_attempts')) is int and m['upstream_attempts'] in (0,1) for m in metas))
    check('one forwarding attempt, not gate default zero',[m['upstream_attempts'] for m in metas]==[1,0] and summary['live_upstream_attempts']==1)
    check('first request forwarded, second rejected before upstream',metas[0]['upstream_status']==200 and metas[0]['outcome']=='forwarded' and metas[1]['client_status']==409 and metas[1]['outcome']=='rejected')
    bodies=[]
    for n,m in zip((1,2),metas):
        raw=(cap/('%02d-request.raw'%n)).read_bytes();body=json.loads(raw);bodies.append(body)
        check('raw and decoded JSON equivalent',canonical(body)==canonical(read(cap/('%02d-request.json'%n))))
        key=str((cap/('%02d-request.raw'%n)).relative_to(REPO))
        check('original capture metadata binds original, not derived hash',m['request_body_sha256']==mapping['entries'][key]['original_sha256'] and m['request_body_bytes']==len(raw))
        check('observed alias and low setting',body['model']=='deepseek-flash' and body['reasoning']['effort']=='low')
        check('native output cap is absent, not controlled',not any(k in body for k in ('max_tokens','max_output_tokens')))
        cm=body['client_metadata'];identifier=cm['x-codex-installation-id']
        check('stable installation identifier explicitly withheld',isinstance(identifier,str) and len(identifier)>=16 and set(identifier)=={'I'} and json.loads(cm['x-codex-turn-metadata'])['installation_id']==identifier)
    a,b=bodies;prefix=len(a['input']);suffix=b['input'][prefix:]
    check('actual native prefix preserved',canonical(b['input'][:prefix])==canonical(a['input']))
    check('four to seven input items with reasoning appended',prefix==4 and len(b['input'])==7 and [x.get('type') for x in suffix]==['reasoning','function_call','function_call_output'])
    check('unchanged selected non-input components',canonical({k:v for k,v in selected(a).items() if k!='input'})==canonical({k:v for k,v in selected(b).items() if k!='input'}))
    selected_delta=len(canonical(selected(b)))-len(canonical(selected(a)))
    check('diagnostic delta only, not a valid comparison',selected_delta==12825 and sum(len(canonical(x)) for x in suffix)+len(suffix)==selected_delta)
    gate=read(run/'session-gate.json');account=read(HERE/'reconciled-accounting.json');completion=read(HERE/'pilot-completion.json')
    check('strict technical failure retained',gate['ok'] is False and gate['guard_halted'] is True and gate['guard_reason']=='second_suffix_invalid')
    check('early-return zero explicitly reconciled',gate['upstream_attempts']==0 and account['frozen_gate_field_is_observed_count'] is False and account['relay_forwarding_attempts']==1)
    check('bridge and confirmation not launched',completion['attempted']==1 and completion['unattempted']==1 and completion['both_technical_gates_pass'] is False and completion['budget']['confirmation']==0 and account['confirmation_sessions_observed']==0)
    check('no synthetic second response',(cap/'01-response.sse').exists() and not (cap/'02-response.sse').exists())
    es=[]
    for frame in (cap/'01-response.sse').read_text().split('\n\n'):
        data=[line[5:].lstrip() for line in frame.split('\n') if line.startswith('data:')]
        if data:es.append(json.loads('\n'.join(data)))
    finals=[e['response'] for e in es if e.get('type')=='response.completed']
    check('actual first response completed',len(finals)==1 and finals[0]['status']=='completed')
    calls=[x for x in finals[0]['output'] if x.get('type')=='function_call']
    check('one fixture call and subsequent return association',len(calls)==1 and calls[0]['call_id']==suffix[1]['call_id']==suffix[2]['call_id'] and calls[0]['name']=='fixture_output' and calls[0].get('namespace')=='mcp__fixture')
    fixture=(cap/'tool-output.txt').read_bytes();check('original deterministic fixture',len(fixture)==35767 and sha(fixture)=='fed57592028c9d8a9180c2b97f74a3cd5e0daa841aab244cf4aad78fe44626a2')
    output=suffix[2]['output'];text=output if isinstance(output,str) else ''.join(x['text'] for x in output)
    wrapper=re.match(r'Wall time: (?:0|[1-9][0-9]*)(?:\.[0-9]+)? seconds\nOutput:',text)
    check('known native output wrapper',wrapper is not None)
    core=text[wrapper.end():];markers=list(re.finditer(r'…[0-9]+ tokens truncated…',core));check('single native truncation marker',len(markers)==1)
    m=markers[0];head,tail=core[:m.start()].encode(),core[m.end():].encode()
    check('actual returned text source binding, not full preservation',len(head)>=32 and len(tail)>=32 and len(head)+len(tail)<len(fixture) and fixture.startswith(head) and fixture.endswith(tail))
    witness=read(HERE/'witness-status.json');check('genuine people remain pending',witness['reviewer'] is None and witness['reviewed_at'] is None and witness['signature'] is None and witness['public_blind_first_read']=='pending')
    return {'schema':'public-native-pilot-projection-check-v1','checks_passed':len(checks),'live_sessions':1,'observed_upstream_forwarding_attempts':1,'valid_comparison_blocks':0,'branch':'direct_observation_incomplete','diagnostic_selected_input_delta_bytes':selected_delta,'diagnostic_appended_item_bytes':[{'type':x['type'],'canonical_bytes':len(canonical(x))} for x in suffix],'mock_sessions':4,'formal_admissions':0,'scope':'Public hash/byte/protocol-subset diagnostic and accounting projection only; not original private seal, successful native comparison, TLS test, or genuine human witness.'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output');a=p.parse_args();result=verify()
    if a.output:
        with Path(a.output).open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(result,ensure_ascii=False))
