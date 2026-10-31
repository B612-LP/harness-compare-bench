#!/usr/bin/env python3
"""WB replacement-sub-batch frozen contract; offline only.
No model, desktop or checker execution. Original contracts and scores remain unchanged.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

RULE='freeze-20261031-wb-v2'
V1_RULE='freeze-20261031-wb-v1'
V1_BASE='4-打分细则/可信冻结-20261031-wb-v1'
V1_OUT='5-评测报告/可信冻结-20261031-wb-v1'
BASE='4-打分细则/可信冻结-20261031-wb-v2'
OUT='5-评测报告/可信冻结-20261031-wb-v2'
PLAN_ID='r20261031-wb-replacement'
PLAN_PATH='1-评测方案/正式批次-2026-10-31-WB-replacement/registration-plan.json'
PROMPT_HEADER='**工作目录**：当前会话绑定的 cwd（产品上下文提供）；输入与产物路径均相对于本目录。'
BOUNDARY_TEXT='**临时文件边界的明确说明**：本任务的临时脚本、测试数据、性能测试输入、日志与中间结果，也只能在上面指定的本工作目录内创建、读取、执行或删除。`/tmp`、`/private/tmp`、`/var/folders` 等系统临时目录，以及任何其他工作目录，均在允许范围之外；不能因为内容只是自己生成的临时数据就使用这些路径。需要临时目录时，请在当前工作目录创建 `.tmp/`，所有临时文件放入其中；如调用会使用临时目录的程序，请将其临时路径设置为本工作目录内的绝对路径。不要访问任何先前会话、历史运行或评测资产。发现误操作也不要通过删除目录外文件尝试“清理痕迹”，应停止并如实说明。'
CASES=('bird-ca-schools-15','dabstep-payments-10','exercism-py-6','lcb-recent-hard-4','tb-cargo-plan')
BAD_GATES={'contamination':'contamination_free','case_invalid':'case_valid','evidence_invalid':'evidence_valid'}

class Invalid(ValueError):pass

def need(condition,message):
    if not condition:raise Invalid(message)

def dump(value):return json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
def sha(data):return hashlib.sha256(data).hexdigest()
def load(path):
    def unique(items):
        data={}
        for k,v in items:
            need(k not in data,'duplicate JSON key: '+k);data[k]=v
        return data
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=unique,parse_constant=lambda s:(_ for _ in ()).throw(Invalid(s)))

def public(root,name):
    need(isinstance(name,str) and bool(name) and not Path(name).is_absolute() and '..' not in Path(name).parts,'non-public relative path')
    path=(root/name).resolve();need(path.is_relative_to(root.resolve()),'path escape');return path

def pin(root,name):return {'path':name,'sha256':sha(public(root,name).read_bytes())}
def check_pin(root,value):
    need(isinstance(value,dict) and set(value)=={'path','sha256'},'bad source pin')
    need(pin(root,value['path'])==value,'source missing or drifted: '+value['path'])
    return public(root,value['path'])

def helper(root,dependency):
    need(dependency['path']==V1_BASE+'/freeze.py','unexpected engine dependency')
    path=check_pin(root,dependency)
    spec=importlib.util.spec_from_file_location('wb_v1_immutable_dependency',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    need(module.RULE==V1_RULE,'wrong predecessor engine version');return module

def validate_plan(plan,config,parents):
    """Mechanical first queue remains unchanged; semantic replacement is explicit."""
    registrations=plan.get('registrations')
    need(isinstance(registrations,list) and len(registrations)==len(config['predecessors']) and bool(registrations),'replacement plan registration subset mismatch')
    design=plan.get('design',{})
    need(design.get('semantic_kind')=='invalid_only_replacement' and design.get('predecessor_plan')=='r20261031-wb-formal','plan must disclose invalid-only replacement, not unqualified first')
    need(design.get('max_replacements_per_parent')==1 and design.get('no_valid_low_score_replacement') is True and design.get('automatic_retry') is False and design.get('automatic_replacement') is False,'plan replacement/launch caps not preserved')
    need(plan.get('plan_id')==config['plan_id'] and plan.get('rule_version')==RULE,'plan identity mismatch')
    seen=set()
    for r in registrations:
        need(set(r)=={'event_id','plan_id','slot_id','order','kind','parent_id','reason','registered_at'},'registration fields mismatch')
        need(r['event_id'] not in seen,'duplicate child registration');seen.add(r['event_id'])
        links=[(case,p) for case,p in config['predecessors'].items() if p['child_event_id']==r['event_id']]
        need(len(links)==1,'registration not canonical child')
        case,link=links[0]
        need(r['plan_id']==config['plan_id'] and r['slot_id']==link['child_slot_id'],'canonical slot mismatch')
        need(type(r['order']) is int and r['order']==1 and r['kind']=='first' and r['parent_id'] is None and r['reason']=='fixed_first','mechanical first queue changed')
    declared=plan.get('predecessors',{})
    need(set(declared)==set(config['predecessors']),'plan predecessor subset differs from contract')
    for case,link in config['predecessors'].items():
        p=declared[case]
        need(set(p)=={'parent_event_id','semantic_kind','reason','replacement_index','evidence'},'plan predecessor fields mismatch')
        need(p['parent_event_id']==link['parent_event_id'] and p['semantic_kind']=='replacement' and p['reason']==link['reason'] and type(p['replacement_index']) is int and p['replacement_index']==1 and isinstance(p['evidence'],str) and bool(p['evidence']),'plan predecessor disclosure differs from contract')
    return registrations

def validate_predecessors(config,parents,table):
    """Independent eligibility gate, never a change to v1 selection semantics."""
    links=config['predecessors']
    need(isinstance(links,dict) and bool(links) and set(links)<=set(CASES),'invalid replacement subset')
    products=[e for e in parents if e['category']=='product_run']
    need(len(products)==5 and {e['case_id'] for e in products}==set(CASES),'full original five-scene parent envelope required')
    need(len({e['event_id'] for e in products})==5,'duplicate original event')
    need(all(e['group']=='W_gateway' and e['product']=='workbuddy' and e['experiment'] is False for e in products),'wrong original treatment')
    by_id={e['event_id']:e for e in products};rejected={x['event_id']:x['reasons'] for x in table['rejected']}
    official={eid for ids in table['groups'].values() for eid in ids}
    need(isinstance(config['invalid_cases'],list) and len(config['invalid_cases'])==len(set(config['invalid_cases'])) and set(links)==set(config['invalid_cases']),'replacement subset differs from locked final invalid list')
    parent_ids=[];child_ids=[];slots=[]
    for case,link in links.items():
        need(set(link)=={'parent_event_id','child_event_id','child_slot_id','reason','semantic_kind','replacement_index','max_replacements'},'bad predecessor link fields')
        need(link['semantic_kind']=='replacement' and type(link['replacement_index']) is int and link['replacement_index']==1 and type(link['max_replacements']) is int and link['max_replacements']==1,'replacement cap not exactly one')
        need(link['reason'] in BAD_GATES,'non-invalid replacement reason')
        parent=by_id.get(link['parent_event_id']);need(parent is not None and parent['case_id']==case,'parent/case mismatch')
        s=parent['selection'];need(s is not None and s['kind']=='first' and s['order']==1 and s['parent_id'] is None,'parent not original first attempt')
        need(s['plan_id']=='r20261031-wb-formal' and s['slot_id']=='workbuddy|'+case,'parent not canonical first-batch slot')
        need(parent['facts']['rule_version']['value']==V1_RULE,'parent not governed by v1')
        need(parent['facts']['final_adjudication']['value'] in ('invalid','suspect'),'valid/unknown parent cannot be replaced, regardless of score')
        need(parent['event_id'] not in official and parent['event_id'] in rejected,'parent not finally rejected')
        gate=BAD_GATES[link['reason']]
        need(parent['gates'][gate]['state']!='unknown' and parent['gates'][gate]['value'] is False,'parent invalid gate not established')
        need('gate:'+gate in rejected[parent['event_id']],'parent rejection reason does not corroborate invalidity')
        need(all(isinstance(link[k],str) and bool(link[k]) for k in ('parent_event_id','child_event_id','child_slot_id')),'empty/nonstring lineage identity')
        need(link['child_event_id']!=parent['event_id'] and config['plan_id']!=s['plan_id'],'child needs independent new event and (plan_id,slot_id) identity')
        parent_ids.append(parent['event_id']);child_ids.append(link['child_event_id']);slots.append(link['child_slot_id'])
    need(len(parent_ids)==len(set(parent_ids)) and len(child_ids)==len(set(child_ids)) and len(slots)==len(set(slots)),'duplicate predecessor/child/slot; cap exceeded')
    return by_id

def child_completeness(events,config):
    products=[e for e in events if e['category']=='product_run']
    need(len({e['event_id'] for e in events})==len(events),'duplicate imported event ID')
    need({e['event_id'] for e in products}=={x['child_event_id'] for x in config['predecessors'].values()} and len(products)==len(config['predecessors']),'omitted/extra registered replacement')
    need({e['case_id'] for e in products}==set(config['predecessors']),'child subset changed')
    need(len({e['identity']['value']['run_id'] for e in products})==len(products),'duplicate child original run_id')
    for e in products:
        need(e['group']=='W_gateway' and e['product']=='workbuddy' and e['experiment'] is False,'replacement wrong treatment')
        link=config['predecessors'].get(e['case_id']);need(link is not None and e['event_id']==link['child_event_id'],'child/case mapping mismatch')
        need(e['selection']['slot_id']==link['child_slot_id'] and e['selection']['plan_id']==config['plan_id'],'child registered in wrong canonical slot')
    return products

def prompt_binding(root,event,revision_pin,task_pin):
    """Require pinned sent-prompt evidence, not merely an unused template."""
    need(revision_pin in event['sources'],'event lacks frozen prompt revision source')
    proofs=[]
    for s in event['sources']:
        if Path(s['path']).suffix!='.json':continue
        try:value=load(check_pin(root,s))
        except (UnicodeError,json.JSONDecodeError):continue
        if isinstance(value,dict) and value.get('event_id')==event['event_id'] and 'sent_prompt_sha256' in value:proofs.append(value)
    need(len(proofs)==1,'missing/ambiguous sent-prompt proof')
    proof=proofs[0]
    need(proof.get('prompt_revision_sha256')==revision_pin['sha256'],'sent-prompt proof revision drift')
    prompt_pin={'path':proof.get('prompt_path'),'sha256':proof.get('sent_prompt_sha256')}
    need(prompt_pin==task_pin,'sent prompt differs from prospectively frozen TASK')
    need(prompt_pin in event['sources'],'actual prompt not a pinned event source')
    text=check_pin(root,prompt_pin).read_text(encoding='utf-8')
    need(BOUNDARY_TEXT in text,'actual prompt lacks frozen boundary addition')

def admission_reasons(v1,event,config):
    # Only the two version comparisons are adapted. All other v1 gates remain.
    reasons=set(v1.reasons(event,config))
    reasons.discard('rule_version_not_frozen');reasons.discard('score_receipt_rule_or_checker_mismatch')
    if event['facts'].get('rule_version',{}).get('value')!=RULE:reasons.add('rule_version_not_frozen')
    score=event['score']['value'];snap=config['case_snapshots'].get(event['case_id'],{})
    if score and (score.get('rule_version')!=RULE or score.get('checker_sha256')!=snap.get('checker.py')):reasons.add('score_receipt_rule_or_checker_mismatch')
    return sorted(reasons)

def verify_seal(root):
    config=load(public(root,BASE+'/config.json'));lock=load(public(root,BASE+'/freeze.lock.json'))
    expected_keys={'schema_version','rule_version','effective_at','collected_at','a_model','a_route_host','w_model','policy','case_snapshots','engine_dependency','v1_lock','predecessor_package','invalid_cases','predecessors','plan_id','plan','prompt_revision','task_prompts','adjudications','official_slots'}
    need(set(config)==expected_keys and config['schema_version']==1,'unknown successor config schema')
    need(config['rule_version']==RULE and lock['rule_version']==RULE,'wrong successor version')
    need(set(lock)=={'rule_version','pins','trust_boundary'},'bad lock schema')
    pinned={}
    for p in lock['pins']:
        need(p.get('pin_class')=='contract' and set(p)=={'path','sha256','pin_class'},'successor uses contract pins only')
        need(p['path'] not in pinned,'duplicate lock pin');pinned[p['path']]=p['sha256'];check_pin(root,{k:p[k] for k in ('path','sha256')})
    mandatory={BASE+'/'+name for name in ('freeze.py','config.json','config-schema.json','test_predecessors.py','README.md')}
    mandatory.update({config['engine_dependency']['path'],config['v1_lock']['path'],config['plan']['path'],config['prompt_revision']['path']})
    mandatory.update(p['path'] for p in config['predecessor_package'].values())
    mandatory.update(p['path'] for p in config['task_prompts'].values())
    mandatory.update(p['path'] for p in config['adjudications'].values())
    mandatory.update('2-用例/'+case+'/'+name for case,snap in config['case_snapshots'].items() for name in snap['files'])
    need(mandatory<=set(pinned),'required contract dependency not pinned')
    v1=helper(root,config['engine_dependency']);need(config['policy']==v1.SAFE_POLICY and config['w_model']==v1.W_MODEL,'policy/model drift')
    v1.stamp(config['effective_at']);v1.stamp(config['collected_at'])
    previous=load(public(root,V1_BASE+'/config.json'))
    need(config['a_model']==previous['a_model'] and config['a_route_host']==previous['a_route_host'],'A-model/route declaration changed')
    need(config['case_snapshots']==previous['case_snapshots'] and set(config['case_snapshots'])==set(CASES),'original five-case snapshot changed')
    for case,snapshot in config['case_snapshots'].items():need(v1.snapshot_case(root,case)==snapshot,'current case byte drift: '+case)
    need(config['v1_lock']['path']==V1_BASE+'/freeze.lock.json','wrong parent contract lock');check_pin(root,config['v1_lock'])
    v1.verify_seal(root)
    package=config['predecessor_package'];need(set(package)=={'events','table','recipe','manifest'},'incomplete parent package pins')
    for p in package.values():check_pin(root,p)
    need(package['table']['path']==V1_OUT+'/official-main-table.json' and package['recipe']['path']==V1_OUT+'/build-recipe.json' and package['manifest']['path']==V1_OUT+'/output-manifest.json','wrong parent output paths')
    parents=load(check_pin(root,package['events']))['events'];table=load(check_pin(root,package['table']))
    need(table['rule_version']==V1_RULE,'wrong original final table rule')
    by_id=validate_predecessors(config,parents,table)
    for parent in parents:v1.validate_event(parent,root,{})
    v1.select_events(parents);v1.validate_plan_completeness(parents,root,{})
    recipe=load(check_pin(root,package['recipe']));need(package['events'] in recipe['imports'],'parent outputs not built with exact final event package')
    # Read-only full v1 verify binds table/recipe/manifest to the complete original inputs.
    result=subprocess.run([sys.executable,'-B',str(public(root,V1_BASE+'/freeze.py')),'verify','--root',str(root),'--imports',package['events']['path']],cwd=root,capture_output=True,text=True)
    need(result.returncode==0,'parent final contract verify failed: '+result.stdout+result.stderr)
    need(config['plan_id']==PLAN_ID and config['plan']['path']==PLAN_PATH,'wrong replacement batch identity')
    for case,link in config['predecessors'].items():
        need(link['child_event_id']==PLAN_ID+':workbuddy:'+case and link['child_slot_id']=='workbuddy|'+case,'wrong replacement event/slot identity')
    plan=load(check_pin(root,config['plan']));registrations=validate_plan(plan,config,parents)
    need(set(config['adjudications'])==set(config['predecessors']),'missing predecessor adjudication pins')
    for case,adjudication in config['adjudications'].items():
        need(adjudication['path']==plan['predecessors'][case]['evidence'],'adjudication pin differs from registered evidence')
        check_pin(root,adjudication)
        need(adjudication in by_id[config['predecessors'][case]['parent_event_id']]['sources'],'adjudication not in verified original event sources')
    need(plan.get('design',{}).get('prompt_pins')==config['task_prompts'] and set(config['task_prompts'])==set(config['predecessors']),'TASK commitments differ from registered subset')
    for case,task in config['task_prompts'].items():
        data=check_pin(root,task).read_bytes();instruction=public(root,'2-用例/'+case+'/instruction.md').read_bytes()
        need(data.endswith(instruction) and data.count(instruction)==1,'original instruction bytes not preserved as exact suffix')
        need(PROMPT_HEADER.encode() in data and BOUNDARY_TEXT.encode() in data,'TASK lacks declared neutral header/boundary')
    for r in registrations:
        need(v1.stamp(r['registered_at'])<=v1.stamp(config['effective_at']),'registration after successor freeze')
        need(all(v1.stamp(p['facts']['finished_at']['value'])<v1.stamp(r['registered_at']) for p in parents if p['category']=='product_run'),'replacement registered before all original runs finished')
    expected={'W_gateway|workbuddy|'+case:{'plan_id':config['plan_id'],'slot_id':x['child_slot_id'],'plan_sha256':config['plan']['sha256']} for case,x in config['predecessors'].items()}
    need(config['official_slots']==expected,'successor canonical subset slots differ')
    revision=load(check_pin(root,config['prompt_revision']));need(revision.get('added_boundary_text')==BOUNDARY_TEXT and revision.get('case_bytes_unchanged') is True,'unsafe/unrecorded prompt revision')
    return config,v1,by_id

def build(root,imports):
    config,v1,parents=verify_seal(root);events=[];import_pins=[]
    for name in imports:
        data=load(public(root,name));need(set(data)=={'schema_version','events'} and data['schema_version']==1,'bad import envelope');import_pins.append(pin(root,name))
        for event in data['events']:
            v1.validate_event(event,root,{});event=copy.deepcopy(event)
            event['source_audit']=[v1.audit_source(root,p,{}) for p in event['sources']]
            event['attribution_exclusions']=['same_model_attribution','backend_model_identity','backend_parameter_mapping']+(['DAB2697'] if event['case_id']=='dabstep-payments-10' else [])
            events.append(event)
    if imports:
        products=child_completeness(events,config)
        v1.select_events(events);v1.validate_plan_completeness(events,root,{})
        original_run_ids={p['identity']['value']['run_id'] for p in parents.values()}
        need(not original_run_ids & {e['identity']['value']['run_id'] for e in products},'child aliases original run')
        for e in products:prompt_binding(root,e,config['prompt_revision'],config['task_prompts'][e['case_id']])
    official={'A_same_model':[],'B_native':[],'W_gateway':[]};rejected=[]
    for e in events:
        reasons=admission_reasons(v1,e,config);e['admission']={'eligible':not reasons,'reasons':reasons}
        if reasons:rejected.append({'event_id':e['event_id'],'reasons':reasons})
        else:official['W_gateway'].append(e['event_id'])
    links=[dict(case_id=case,**link,original_score=parents[link['parent_event_id']]['score']['value']) for case,link in config['predecessors'].items()]
    return {'summary.json':{'rule_version':RULE,'scope':'current replacement sub-batch only; no historical or first-batch re-admission','pending':not bool(events),'registered_cases':list(config['predecessors']),'official_counts':{k:len(v) for k,v in official.items()},'ranking':None},'archive.json':{'schema_version':1,'events':events},'official-main-table.json':{'rule_version':RULE,'groups':official,'rejected':rejected,'ranking':None},'predecessor-links.json':{'semantic_kind':'replacement','mechanical_registration':'first in a distinct plan/slot; not without predecessor','package':config['predecessor_package'],'links':links},'six-ledgers.json':{category:[e for e in events if e['category']==category] for category in v1.CATEGORIES},'unknown-limitations.json':{'events':[{'event_id':e['event_id'],'issues':e['issues']} for e in events if e['issues']]},'build-recipe.json':{'imports':import_pins,'source_map':{}}}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('build','verify'));parser.add_argument('--root',default='.');parser.add_argument('--imports',action='append',default=[]);a=parser.parse_args();root=Path(a.root).resolve()
    try:
        outputs=build(root,a.imports);directory=public(root,OUT)
        if a.action=='build':
            directory.mkdir(parents=True,exist_ok=True)
            for name,value in outputs.items():(directory/name).write_text(dump(value),encoding='utf-8')
            (directory/'output-manifest.json').write_text(dump({'rule_version':RULE,'files':[pin(root,OUT+'/'+name) for name in outputs]}),encoding='utf-8')
        else:
            for name,value in outputs.items():need((directory/name).read_text(encoding='utf-8')==dump(value),'output drift: '+name)
            need(load(directory/'output-manifest.json')=={'rule_version':RULE,'files':[pin(root,OUT+'/'+name) for name in outputs]},'output manifest drift')
        print(dump({'ok':True,'action':a.action,'summary':outputs['summary.json']}),end='');return 0
    except (Invalid,ValueError,KeyError,TypeError,OSError) as exc:print(dump({'ok':False,'error':str(exc)}),end='');return 2

if __name__=='__main__':raise SystemExit(main())
