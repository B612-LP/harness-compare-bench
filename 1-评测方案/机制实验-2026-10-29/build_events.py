#!/usr/bin/env python3
"""Posthoc explicit import adapter; not a retroactive pre-registration identity."""
import datetime,hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parent;REPO=R.parents[1];E=REPO/'3-表现现场/r20261029-mechanism'
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p):return str(p.relative_to(REPO))
now=datetime.datetime.now(datetime.timezone.utc).isoformat();analysis=load(E/'analysis.json');items=[]
for i,r in enumerate(analysis['runs']):
    d=E/r['path'];m=load(d/'run-meta.json');freeze=load(d.parent/'freeze.json')
    identity={'event_id':'mechanism-'+r['run_id'],'run_id':r['run_id'],'category':'product_run','product':'DSH CLI','group':'research','experiment':True,'case_id':'fixture-v1-'+r['size']}
    facts={'case_version':'fixture-v1','product_version':freeze['environment']['dsh'],'model':{'provider':'deepseek-official','model':'deepseek-flash','reasoningEffort':'low'},'tools':['fixture_output'],'permissions':m['permissions'],'skills':False,'started_at':r['start'],'finished_at':r['end'],'evidence_grade':'real-api/provider-parsed-durable-usage; raw-SSE-gap' if r['v3_observer_gap'] else 'real-api/request-body/raw-SSE/usage','final_adjudication':'exact-head-tail-pass; research-only; no official score','rule_version':freeze['prompt_sha256'],'checker_sha256':sha(R/'analyze.py'),'truth_sha256':None,'case_sha256':r['tool_output_sha256']}
    tr=load(d/'01-transport.json');facts['route']={'host':tr['host'],'provider_id':m['model']['provider'],'wire_protocol':'anthropic-messages','endpoint':'https://'+tr['host']+tr['path']}
    gates={k:True for k in ['rules_frozen','case_valid','scoring_reviewable','evidence_valid','contamination_free']}
    items.append({'identity':identity,'facts':facts,'gates':gates,'original_time':r['start'],'origins':[rel(d/'run-meta.json'),rel(d/'01-request.json'),rel(d/'02-request.json'),rel(d/'01-transport.json'),rel(d.parent/'freeze.json'),rel(E/'analysis.json')],'observer_gap':r['v3_observer_gap']})
# Two failed pre-API runtime attempts keep original metadata but are classified by actual execution.
for d in [next(E.glob('20*')),next((E/'v2').glob('20*'))]:
    m=load(d/'run-meta.json');rid=m['run_id'];identity={'event_id':'pre-api-'+rid,'run_id':rid,'category':'interface_preflight','product':'DSH CLI','group':'research','experiment':True,'case_id':'mechanism-runtime-initialization'}
    items.append({'identity':identity,'facts':{},'gates':{},'original_time':m['start'],'origins':[rel(d/'run-meta.json'),rel(d/'stdout.txt'),rel(d/'stderr.txt')],'pre_api_failure':True})
for p in sorted(E.rglob('receipt.json')):
    if 'preflight' not in str(p.parent):continue
    m=load(p);rid=p.parent.name;identity={'event_id':'mechanism-'+rid,'run_id':rid,'category':'interface_preflight','product':'DSH CLI','group':'research','experiment':True,'case_id':'mechanism-interface-configuration'}
    items.append({'identity':identity,'facts':{},'gates':{},'original_time':m.get('at') or m.get('start'),'origins':[rel(p)]})
for category,source,rid in [('self_test',E/'offline-verification-v2.json','mechanism-offline-validation'),('offline_recompute',E/'analysis.json','mechanism-offline-analysis'),('offline_recompute',E/'spill-recovery-posthoc.json','mechanism-spill-posthoc')]:
    m=load(source);identity={'event_id':rid,'run_id':rid,'category':category,'product':'DSH CLI','group':'research','experiment':True,'case_id':'mechanism-evidence-verification'}
    time=m.get('at') or m.get('generated_at') or m.get('records',[{}])[0].get('checked_at')
    items.append({'identity':identity,'facts':{},'gates':{},'original_time':time,'origins':[rel(source)]})
adapter={'schema_version':1,'created_at':now,'provenance':'Posthoc supplemented identity/facts; original run receipts and planned category are untouched. Research experiments never enter official ranking.','items':items}
adapter_path=E/'import-adapter.json'
with adapter_path.open('x') as f:json.dump(adapter,f,ensure_ascii=False,indent=2)
events=[]
for i,item in enumerate(items):
    identity=item['identity'];sources=[{'path':rel(adapter_path),'sha256':sha(adapter_path)}]+[{'path':p,'sha256':sha(REPO/p)} for p in item['origins']]
    def fact(value,pointer):return {'state':'unknown','value':None,'refs':[]} if value is None else {'state':'supplemented','value':value,'refs':[{'source':0,'pointer':f'/items/{i}/'+pointer}]}
    event={k:identity[k] for k in ['event_id','category','product','group','experiment','case_id']}
    event.update({'identity':fact(identity,'identity'),'facts':{k:fact(v,'facts/'+k) for k,v in item['facts'].items()},'gates':{k:fact(v,'gates/'+k) for k,v in item['gates'].items()},'score':{'state':'unknown','value':None,'refs':[]},'selection':None,'sources':sources,'original_time':fact(item['original_time'],'original_time'),'collected_at':now,'issues':[]})
    unknown=['score']+(['facts.truth_sha256'] if identity['category']=='product_run' else [])
    if item['original_time'] is None:unknown.append('original_time')
    event['issues'].append({'id':'research-non-scored-no-hidden-truth','knowledge_status':'accepted_limitation','investigation_status':'stopped','confound_status':'not_applicable','impact':'Research mechanism diagnostic has no official normalized score; synthetic observation inputs use no hidden truth asset. Unknown does not mean failure or full credit.','next_step':'Use the published exact-output observation and mechanism evidence, never infer an official score or truth hash.','stop_condition':'No official-score conversion is performed for this diagnostic.','reopen_condition':'Only a separately frozen scoring contract or a genuine truth artifact would reopen these fields.','unknown_fields':unknown,'refs':[{'source':0,'pointer':f'/items/{i}/identity'}]})
    if item.get('observer_gap'):
        event['issues'].append({'id':'v3-raw-sse-observer-gap','knowledge_status':'accepted_limitation','investigation_status':'stopped','confound_status':'not_excluded','impact':'Original first actual run has HTTP200/request/stdout/durable provider-parsed usage, but no raw SSE. Do not upgrade its evidence grade or replace the run.','next_step':'Keep pair1 with downgrade and use pair2 as full raw-chain corroboration.','stop_condition':'Original six actual runs completed; no API rerun fills this gap.','reopen_condition':'Authentic original raw SSE may supplement the same run identity.','refs':[{'source':0,'pointer':f'/items/{i}/facts/evidence_grade'}]})
    if item.get('pre_api_failure'):
        event['issues'].append({'id':'pre-api-technical-initialization','knowledge_status':'resolved','investigation_status':'closed','confound_status':'not_applicable','impact':'Original metadata planned product_run, but startup failure or wire hard gate stopped before native HTTP; correctly classified interface_preflight, not a model answer failure.','next_step':'Retain original receipts and subsequent versioned amendments.','stop_condition':'Zero-API runtime requirements check and actual six-run sequence completed.','reopen_condition':'Evidence of actual external HTTP in this initialization attempt would require reclassification.','refs':[{'source':0,'pointer':f'/items/{i}/identity'}]})
    events.append(event)
with (E/'experiment-events.json').open('x') as f:json.dump({'schema_version':1,'events':events},f,ensure_ascii=False,indent=2)
print(json.dumps({'events':len(events),'product_runs':sum(e['category']=='product_run' for e in events),'path':rel(E/'experiment-events.json')},ensure_ascii=False))
