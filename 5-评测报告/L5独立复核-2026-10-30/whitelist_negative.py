#!/usr/bin/env python3
"""One independently selected whitelist bypass: uppercase Registrations vs exact name.
One matched positive control; synthetic data only. Never launches any product/checker.
"""
import hashlib,importlib.util,json,tempfile
from pathlib import Path
from datetime import datetime
OUT=Path(__file__).resolve().parent
snap=json.loads((OUT/'input-snapshot-01.json').read_text());PUB=Path(snap['public_root'])
gatepath=PUB/'1-评测方案/工具链/l5-execution/gate.py'
spec=importlib.util.spec_from_file_location('independent_l5_gate',gatepath)
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
D='d'*40;E='e'*40;CASE='dabstep-payments-10'
world=Path(tempfile.mkdtemp(prefix='independent-uppercase-',dir=Path(snap['temporary_root'])/'tmp'))
pd=world/'plans/test';pd.mkdir(parents=True)
slots=[]
for i,tag in enumerate(('exact-control','uppercase-bypass'),1):
    sid='independent-'+tag
    slots.append({'slot_id':sid,'run_id':sid,'event_id':'event:'+sid,'kind':'product_run','product':'dsh','case':CASE,'rep':i,'stratum':'cli_current_sentinel','order':i,'evidence_dir':'runs/'+sid,'timeout_s':1800})
contract={'strata':{'cli_current_sentinel':{'products':['dsh'],'model':'deepseek-flash','effort':'low','route_host':'api.deepseek.com','ranking':False}},'case_snapshots':{CASE:{'checker.py':'c'*64}},'denominators':{CASE:10},'admission':{'required_original_evidence':['prompt','stdout','stderr','session','checker','workspace']}}
(pd/'plan.json').write_text(json.dumps({'plan_id':'independent-case-bypass','product_slots':slots}))
(pd/'contract.json').write_text(json.dumps(contract))
ext=world/'offline-driver.txt';ext.write_text('never execute\n')
bp,gr,gt,ga,b=g._fake_git_env(world,pd,D,E,'2026-10-29T20:00:00+08:00','2026-10-29T19:00:00+08:00',ext)
b['released_for_model_calls']=True
released=world/'released.json';released.write_text(json.dumps(b))
for slot,name in zip(slots,('registrations','Registrations')):
    ev=world/slot['evidence_dir'];ev.mkdir(parents=True)
    ne={'slot_id':slot['slot_id'],'run_id':slot['run_id'],'event_id':slot['event_id'],'preregistration_commit':E,'reason':'independent synthetic no dispatch','stop_source':'independent offline negative','live_doc_drift':[]}
    (ev/'notexecuted.json').write_text(json.dumps(ne))
    (ev/name).mkdir();(ev/name/'registration.json').write_text('{"dispatched":false}\n')
report=g.gate_admission(released,'dsh',repo=world,plan_dir=pd,git_reader=gr,git_time=gt,git_ancestor=ga,required_set={'plans/test/plan.json','plans/test/contract.json'})
a,b=report['per_slot'];checks=[]
def c(name,ok):checks.append({'name':name,'pass':bool(ok)})
c('exact registrations positive control valid',a.get('record_valid') is True and a['fails']==[])
c('exact control inventory one real file',len(a.get('whitelisted_entries',[]))==1 and a['whitelisted_entries'][0]['path']=='registrations/registration.json')
c('uppercase Registrations bypass explicitly rejected',any('not_executed 目录含其他文件' in f and 'Registrations' in f for f in b['fails']))
c('uppercase bypass record invalid',b.get('record_valid') is False)
c('uppercase bypass not accidentally inventoried',b.get('whitelisted_entries') is None)
c('neither synthetic slot formally admitted',all(r['formal_admission'] is False for r in (a,b)))
c('not_executed score remains null',all(r['score'] is None and r['accounting']=='not_executed' for r in (a,b)))
c('invalid bypass makes accounting_complete false',report['summary']['accounting_complete'] is False)
out={'generated_at':datetime.now().astimezone().isoformat(timespec='seconds'),'gate_sha256':hashlib.sha256(gatepath.read_bytes()).hexdigest(),'selected_bypass':'Registrations uppercase name (one bypass plus exact-name positive control)','world':str(world),'per_slot':report['per_slot'],'checks':checks,'all_pass':all(x['pass'] for x in checks),'model_calls':0,'network_calls':0,'live_doc_drift':[]}
with (OUT/'whitelist-negative-receipt-01.json').open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'checks':len(checks),'passed':sum(x['pass'] for x in checks)},ensure_ascii=False))
raise SystemExit(0 if out['all_pass'] else 1)
