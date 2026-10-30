#!/usr/bin/env python3
"""L6 offline executions. OS sandbox outside; only read-only Git + copied checker/tool subprocesses.
Model/product/native driver are never imported or invoked. Reproduction script unchanged;
four approved module globals are relocated, with ARCHIVE set to independent output.
"""
import ast,copy,hashlib,importlib.util,itertools,json,os,runpy,subprocess,sys
from datetime import datetime
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
S=json.loads((OUT/'snapshot-01.json').read_text());PUB=Path(S['public_root']);TEMP=Path(S['temporary_root'])
P6='1-评测方案/自动循环L6-2026-10-30';REV='5-评测报告/L6判卷修订-2026-10-30';KIT='1-评测方案/工具链/evidence-kit';CASE='bird-ca-schools-15'
RUN='3-表现现场/l6-20261030-wb-gateway/runs/l6-20261030-wb-gateway-bird-ca-schools-15-r1'
HIST=['3-表现现场/l5-20261030-wb-gateway/runs/l5-20261030-wb-gateway-bird-ca-schools-15-r1','3-表现现场/中止重封档案E2-20261030T0207/wb__bird-r1']
checks=[];operations=[];blocked=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def create(p,obj):
    import re
    text=json.dumps(obj,ensure_ascii=False,indent=2)+'\n'
    text2=re.sub(r'(?i)\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b',lambda m:m[0].replace('-',r'\u002d'),text)
    assert json.loads(text2)==obj
    with Path(p).open('x',encoding='utf-8') as f:f.write(text2)
def c(n,v,d=None):checks.append({'name':n,'pass':bool(v),'detail':d})
def load(p):return json.loads(Path(p).read_text())
def module(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def guard(event,args):
    if event.startswith('socket.') or event in ('os.system','os.exec','os.posix_spawn','os.spawn'):
        blocked.append(event);raise PermissionError('offline audit forbids network/uncontrolled execution')
    if event=='subprocess.Popen':
        argv=list(args[1]);name=Path(str(argv[0])).name;ok=False
        if name=='git':
            opt=argv[1:]
            if opt[:1]==['-C']:opt=opt[2:]
            ok=bool(opt) and (opt[0] in ('show','rev-parse','log','cat-file') or opt[:2]==['merge-base','--is-ancestor'])
        elif name.startswith('python') and len(argv)>1:
            script=Path(argv[1]).resolve()
            ok=script.is_relative_to(TEMP) if hasattr(script,'is_relative_to') else str(script).startswith(str(TEMP)+'/')
            ok=ok and script.name in ('checker.py','gate.py','receipt_check.py','manifest_receipt.py')
        operations.append({'exe':name,'script_or_command':str(argv[1]) if len(argv)>1 else None,'allowed':ok})
        if not ok:blocked.append(argv[0]);raise PermissionError('not an allowlisted offline checker/Git tool')
sys.addaudithook(guard)
def run(label,args):
    p=subprocess.run(args,cwd=PUB,capture_output=True,text=True)
    for kind,text in (('stdout',p.stdout),('stderr',p.stderr)):
        with (OUT/(label+'-'+kind+'.txt')).open('x',encoding='utf-8') as f:f.write(text)
    return p

def normalized(doc):
    d=copy.deepcopy(doc)
    if 'run_dir' in d:d['run_dir']='<workspace>'
    for x in d.get('checks',[]):
        if x.get('id')=='answers_file':x['note']='<answers_path>'
    return d

def main():
    relocation={
        'ROOT':{'from':str(ROOT),'to':str(PUB)},
        'ARCHIVE':{'from':str(ROOT/REV),'to':str(OUT)},
        'CHECKER':{'from':str(ROOT/'2-用例'/CASE/'checker.py'),'to':str(PUB/'2-用例'/CASE/'checker.py')},
        'SOURCES':{'from':{k:str(ROOT/p) for k,p in zip(('l5-e3-wb-bird','e2-aborted-wb-bird'),HIST)},'to':{k:str(PUB/p) for k,p in zip(('l5-e3-wb-bird','e2-aborted-wb-bird'),HIST)}}}
    ns=runpy.run_path(str(PUB/REV/'l6_meta_recompute.py'),run_name='independent_loaded_not_main')
    g=ns['main'].__globals__
    for key,entry in relocation.items():
        g[key]={k:Path(v) for k,v in entry['to'].items()} if key=='SOURCES' else Path(entry['to'])
    code=ns['main']()
    c('L6-A unchanged main exit zero',code==0)
    original=load(PUB/REV/'archived-l6-meta-recompute-receipt.json');reproduced=load(OUT/'l6-meta-recompute-receipt.json')
    for i,(old,new) in enumerate(zip(original['assertions'],reproduced['assertions'])):c('L6-A assertion '+str(i+1),old==new and new['pass'],{'archived':old,'reproduced':new})
    c('L6-A exact fifteen assertions',len(reproduced['assertions'])==len(original['assertions'])==15)
    c('L6-A whole receipt equal except generated at',{k:v for k,v in original.items() if k!='at'}=={k:v for k,v in reproduced.items() if k!='at'})
    c('L6-A source bytes identical',sha(PUB/REV/'l6_meta_recompute.py')==S['files'][REV+'/l6_meta_recompute.py']['sha256'])
    tests={}
    for label,rel,total in [('checker-selftest','2-用例/'+CASE+'/checker.py',29),('receipt-selftest',KIT+'/receipt_check.py',16),('manifest-selftest',KIT+'/manifest_receipt.py',6)]:
        p=run(label,[sys.executable,str(PUB/rel),'--selftest']);tests[label]={'returncode':p.returncode,'stdout_sha256':hashlib.sha256(p.stdout.encode()).hexdigest()}
        c(label+' exit zero',p.returncode==0)
        if label=='checker-selftest':
            c(label+' 29/29 reported','29/29' in p.stdout)
            c(label+' no FAIL lines','FAIL' not in p.stdout)
        else:
            doc=json.JSONDecoder().raw_decode(p.stdout)[0];tests[label]['result']=doc
            c(label+' exact counts',doc['counts']=={'total':total,'passed':total,'failed':0})
            for i,item in enumerate(doc['cases']):c(label+' case '+str(i+1),item['pass'],item['case'])
    # Independent pre/post two-workspace rejudgment: do not call implementer's comparators.
    history=[];fields=['reward','weighted','accuracy','correct','failed_questions','checks','n_questions','threshold','input_integrity']
    for i,rel in enumerate(HIST):
        ws=PUB/rel/'workspace';docs={}
        for tag,path in [('pre',Path(S['old_checker']['path'])),('post',PUB/'2-用例'/CASE/'checker.py')]:
            p=run('history-'+str(i)+'-'+tag,[sys.executable,str(path),str(ws),'--json']);docs[tag]=json.loads(p.stdout)
            c('independent history '+str(i)+' '+tag+' valid checker exit',p.returncode in (0,1) and p.stderr=='')
        pre,post=docs['pre'],docs['post'];frozen=json.loads((PUB/rel/'checker.stdout').read_text())
        for field in fields:
            c('independent history '+str(i)+' frozen/pre '+field,normalized(pre)[field]==normalized(frozen)[field])
            c('independent history '+str(i)+' pre/post '+field,normalized(pre)[field]==normalized(post)[field])
        c('independent history '+str(i)+' keyset exactly adds two',set(post)-set(pre)=={'n_tasks','guards_used'} and set(pre)-set(post)==set())
        c('independent history '+str(i)+' new n_tasks=15',post['n_tasks']==15)
        c('independent history '+str(i)+' exact guards',post['guards_used']==['input_integrity','answers_file','answers_schema','answers_coverage'])
        history.append({'workspace':rel+'/workspace','pre_checker_sha256':sha(S['old_checker']['path']),'post_checker_sha256':sha(PUB/'2-用例'/CASE/'checker.py'),'pre':pre,'post':post})
    rc=module('independent_receipt_check',PUB/KIT/'receipt_check.py')
    oldrc=TEMP/'receipt_check.before.py'
    q=subprocess.run(['git','show','79cebe0:'+KIT+'/receipt_check.py'],capture_output=True,check=True)
    oldrc.write_bytes(q.stdout);old=module('independent_old_receipt_check',oldrc)
    replay=[]
    for label,base in [('E1','3-表现现场/l5-20261030-cli/aborted-attempts-20261030T0152seal'),('E2','3-表现现场/中止重封档案E2-20261030T0207')]:
        p=PUB/base/'abort-receipt.json';before=old.check_doc(p,PUB,True);after=rc.check_doc(p,PUB,True)
        found=after.get('self_reference',{}).get('found')
        c('historical '+label+' new self-reference verdict',found is (label=='E2'))
        if label=='E1':c('historical E1 old/new both ok',before['ok'] is True and after['ok'] is True)
        else:
            c('historical E2 exact self-reference cause',any('self-referenced' in x.get('reason','') for x in after['hash_lines']['violations']))
            c('historical E2 old checker lacks selfref violation',not any('self-referenced' in x.get('reason','') for x in before['hash_lines']['violations']))
            c('historical E2 new checker rejects',after['ok'] is False)
        replay.append({'label':label,'before':before,'after':after})
    # Gate CLI and semantic per-slot receipt comparison, not producer verifier alone.
    gate=PUB/'1-评测方案/工具链/l5-execution/gate.py';pd=PUB/P6;gate_results={}
    for mode,oldname in [('verify-execution','gate-formal-check-e3.json'),('admission','gate-admission-e3.json')]:
        target=OUT/('gate-'+mode+'-reproduced.json')
        p=run('gate-'+mode,[sys.executable,str(gate),'--'+mode,'--binding',str(pd/'runtime-binding.json'),'--plan-dir',str(pd),'--product','workbuddy','--out',str(target)])
        c('gate '+mode+' CLI exit zero',p.returncode==0)
        got=load(target);archived=load(pd/oldname)
        if mode=='verify-execution':
            c('gate verify ok',got['ok'] is True)
            c('gate verify count28/5',got['manifest_files']==28 and got['manifest_external_files']==5)
            c('gate verify step results equal',[(s['step'],s['ok']) for s in got['steps']]==[(s['step'],s['ok']) for s in archived['steps']])
        else:
            c('gate admission formal1/1',got['summary']['formal_admitted']==got['summary']['planned']==1 and got['all_admitted'] is True)
            for key in ('binding','product','plan_id','per_slot','summary','tiers_note','all_admitted','live_doc_drift'):c('gate admission exact field '+key,got[key]==archived[key])
        gate_results[mode]=got
    gm=module('independent_gate',gate);negative=[]
    # Default functions bind REPO on module import, hence this is an exact byte-copy instance.
    def reject(label,binding,mutation=None,restore=None):
        if mutation:mutation()
        try:
            gm.verify_execution(binding,repo=PUB,plan_dir=pd)
            ok=False;err='unexpected admission'
        except (gm.GateError,ValueError) as e:ok=True;err=str(e)
        finally:
            if restore:restore()
        c('gate negative '+label,ok,err);negative.append({'name':label,'rejected':ok,'error':err})
    plan=pd/'plan.json';saved=plan.read_bytes()
    reject('plan disk trailing-byte drift',pd/'runtime-binding.json',lambda:plan.write_bytes(saved+b' '),lambda:plan.write_bytes(saved))
    binding=load(pd/'runtime-binding.json')
    for name,change in [('wrong plan binding SHA',{'plan_sha256':'0'*64}),('wrong execution seal',{'execution_seal_commit':'e'*40}),('wrong registered_at',{'registered_at':'2026-10-30T12:23:45+08:00'}),('release false',{'released_for_model_calls':False})]:
        bp=TEMP/(name.replace(' ','-')+'.json');bp.write_text(json.dumps(dict(binding,**change)));reject(name,bp)
    # Omit mandatory external member from injected *E blob* AND binding matching manifest,
    # so it reaches actual mandatory validation rather than an earlier hash mismatch.
    manifest=load(pd/'execution-manifest.json');del manifest['external_files']['/Users/b612-lp/.dsh/AGENTS.md']
    mb=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode();bp=TEMP/'missing-external-binding.json';bp.write_text(json.dumps(dict(binding,execution_manifest_sha256=hashlib.sha256(mb).hexdigest())))
    def altered_reader(commit,path):
        if path==P6+'/execution-manifest.json':return mb
        return gm.default_git_reader(PUB,commit,path)
    try:gm.verify_execution(bp,repo=PUB,plan_dir=pd,git_reader=altered_reader);ok=False;err='unexpected admission'
    except (gm.GateError,ValueError) as e:ok=True;err=str(e)
    c('gate negative missing mandatory external',ok,err);negative.append({'name':'missing mandatory external, hash-consistent injected E manifest','rejected':ok,'error':err,'controlled_injection':True})
    # True slot: raw JSON reserialization must match every checker.stdout byte.
    runroot=PUB/RUN;score=load(runroot/'score-receipt.json');raw=score['raw_checker_output'];meta=load(runroot/'meta.json')
    c('real checker.stdout exact canonical serialization bytes',(json.dumps(raw,ensure_ascii=False)+'\n').encode()==(runroot/'checker.stdout').read_bytes())
    c('real parsed checker.stdout entire object equality',json.loads((runroot/'checker.stdout').read_text())==raw)
    guards=raw['guards_used'];scored=[x for x in raw['checks'] if x['id'] not in set(guards)];correct=sum(x.get('pass') is True for x in scored);possible=len(scored);eight=round(100*correct/possible,8)
    c('real independent full denominator15',possible==15==raw['n_tasks'])
    c('real independent correct15',correct==15==raw['correct'])
    c('real 8dp score',eight==round(raw['weighted'],8)==meta['weighted_8dp']==meta['score']['reported_8dp'])
    k=len(raw['checks'])-raw['n_tasks'];passes=sum(x.get('pass') is True for x in raw['checks'])-raw['correct'];chosen=None;count=0
    for combo in itertools.combinations(range(len(raw['checks'])),k):
        count+=1
        if sum(raw['checks'][j].get('pass') is True for j in combo)==passes:chosen=[raw['checks'][j]['id'] for j in combo];break
    c('real first reconciling guard combination exactly known guards',chosen==guards==meta['judge']['guards_used'])
    c('real guard/task disjoint',set(guards).isdisjoint(x['id'] for x in scored))
    c('real score receipt earned is binary reward not correct',score['score']['earned']==raw['reward']==1 and correct==15)
    c('no forbidden operation',blocked==[])
    result={'at':datetime.now().astimezone().isoformat(timespec='seconds'),'relocations':relocation,'relocation_is_nonzero_injection':True,'source_script_unchanged':True,'checks':checks,'counts':{'total':len(checks),'passed':sum(x['pass'] for x in checks),'failed':sum(not x['pass'] for x in checks)},'selftests':tests,'history_rejudgments':history,'historical_receipt_replay':replay,'gate':gate_results,'gate_negatives':negative,'real_score_recompute':{'earned':correct,'possible':possible,'eight_dp':eight,'derived_guards':chosen,'enumerated_candidates':count},'operations':operations,'blocked':blocked,'zero_models':True,'zero_network':True,'live_doc_drift':[]}
    create(OUT/'offline-work-receipt-01.json',result)
    print(json.dumps({'counts':result['counts'],'failed':[x['name'] for x in checks if not x['pass']]},ensure_ascii=False))
    return int(bool(result['counts']['failed']))
if __name__=='__main__':raise SystemExit(main())
