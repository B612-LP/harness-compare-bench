#!/usr/bin/env python3
"""Verify only the disclosed derived table, not private trace authenticity.
Python 3.9+, standard library, read-only; no assert-based validation.
"""
import collections
import json
from pathlib import Path
import re

COHORTS = ['C01']*3+['C02']*2+['C03']*4+['C04']*2+['C05']*2
IDS = ['A%02d'%n for n in range(1,14)]
SOURCES = {'session-read.json','task-status-final.json','judgment.json','create-receipt.json','submit-receipt.json','run-meta.json'}
AFIELDS = {'attempt','cohort','bridge_status','bridge_status_source','identity_consistent','representation','coverage','has_more','offset','loaded_items','declared_total','final_three_key_json','final_item_index','source_hashes','total_cost','true_wait_seconds','recovery_duration_seconds'}
RFIELDS = {'attempt','item_index','kind','callkey','name','step_seq','identity_conflict','status','command_class','output_present','provider_result_present','representations_differ','display_chars','display_utf8_bytes','read_refusal_literal'}

def require(ok, message):
    if not ok:
        raise ValueError(message)

def integer(value):
    return type(value) is int and value >= 0

def boolean(value):
    return type(value) is bool

def maybe_bool(value):
    return value is None or boolean(value)

def fields(obj, expected):
    require(type(obj) is dict and set(obj) == expected, 'unexpected schema fields')

def validate(data):
    fields(data, {'schema','derivation','attempts','rows'})
    require(data['schema']=='pause-derived-v2', 'schema version')
    require(data['derivation']=='selected-archive projection; not original trace or authenticated private completeness', 'derivation disclaimer')
    require(type(data['attempts']) is list and len(data['attempts'])==13, '13 fixed attempts required')
    attempts={}
    for a, aid, cohort in zip(data['attempts'], IDS, COHORTS):
        fields(a, AFIELDS)
        require(a['attempt']==aid and a['cohort']==cohort, 'fixed attempt identities/order')
        require(a['bridge_status'] in ('completed','waiting_user','failed',None), 'bridge status')
        require(a['bridge_status_source'] in ('task-status-final','judgment-only'), 'status source')
        require(boolean(a['identity_consistent']) and maybe_bool(a['has_more']), 'snapshot booleans')
        require(a['representation'] in ('sanitized_native_rows',None), 'representation')
        require(a['coverage'] in ('selected_single_local_agent_trace',None), 'coverage')
        require(integer(a['offset']) and integer(a['loaded_items']) and integer(a['declared_total']), 'snapshot counts')
        require(a['loaded_items']+a['offset']<=a['declared_total'], 'loaded exceeds total')
        require(boolean(a['final_three_key_json']), 'final flag')
        require((integer(a['final_item_index']) and a['final_item_index']<a['loaded_items']) if a['final_three_key_json'] else a['final_item_index'] is None, 'final index')
        fields(a['source_hashes'], SOURCES)
        for name, digest in a['source_hashes'].items():
            require(digest is None or (type(digest) is str and re.fullmatch('[0-9a-f]{64}',digest)), 'source hash')
            if name!='task-status-final.json':
                require(digest is not None, 'essential source absent')
        require((a['source_hashes']['task-status-final.json'] is None)==(a['bridge_status_source']=='judgment-only'), 'status provenance')
        require(all(a[k] is None for k in ('total_cost','true_wait_seconds','recovery_duration_seconds')), 'unobserved cost/time must be null')
        attempts[aid]=a
    require(type(data['rows']) is list, 'rows list')
    seen=set();last=(-1,-1)
    for row in data['rows']:
        fields(row, RFIELDS)
        aid=row['attempt'];require(aid in attempts, 'unknown attempt')
        require(integer(row['item_index']) and row['item_index']<attempts[aid]['loaded_items'], 'row index')
        pos=(IDS.index(aid),row['item_index'])
        require(pos not in seen and pos>last, 'event index duplicate or unordered')
        seen.add(pos);last=pos
        require(row['kind'] in ('call','result'), 'event kind')
        require(row['callkey'] is None or (type(row['callkey']) is str and re.fullmatch('[0-9a-f]{24}',row['callkey'])), 'callkey')
        require(row['name'] in ('Read','Bash','Grep',None), 'tool name')
        require(row['step_seq'] is None or integer(row['step_seq']), 'step seq')
        require(boolean(row['identity_conflict']), 'identity conflict boolean')
        require(row['command_class'] in ('wc','wc_ls','other',None), 'command class')
        if row['kind']=='call':
            require(all(row[k] is None for k in ('status','output_present','provider_result_present','representations_differ','display_chars','display_utf8_bytes','read_refusal_literal')), 'call/result fields mixed')
            require(row['name']=='Bash' or row['command_class'] is None, 'non-Bash command')
        else:
            require(row['command_class'] is None, 'result command')
            require(row['status'] in ('completed','incomplete','failed','cancelled','error',None), 'result status')
            require(boolean(row['output_present']) and boolean(row['provider_result_present']), 'result representations')
            require(maybe_bool(row['representations_differ']) and maybe_bool(row['read_refusal_literal']), 'result flags')
            both=row['output_present'] and row['provider_result_present']
            require((row['representations_differ'] is not None)==both, 'representation difference coverage')
            have_text=row['display_chars'] is not None
            require(not have_text or row['output_present'] or row['provider_result_present'], 'display without any result representation')
            require(have_text==(row['display_utf8_bytes'] is not None) and have_text==(row['read_refusal_literal'] is not None), 'display fields coverage')
            if have_text:
                require(integer(row['display_chars']) and integer(row['display_utf8_bytes']) and row['display_utf8_bytes']>=row['display_chars'], 'text unit counts')


def analyze(data):
    validate(data)
    per=[]; totals=collections.Counter();cross=collections.Counter()
    for a in data['attempts']:
        aid=a['attempt'];rows=[r for r in data['rows'] if r['attempt']==aid]
        calls=[r for r in rows if r['kind']=='call'];results=[r for r in rows if r['kind']=='result']
        grouped=collections.defaultdict(list);missing=[]
        for r in rows:
            if r['callkey'] is None:missing.append(r)
            else:grouped[r['callkey']].append(r)
        paired=[];unmatched=[];anomalies=[];read_refusals=[]
        for key,events in grouped.items():
            cs=[r for r in events if r['kind']=='call'];rs=[r for r in events if r['kind']=='result']
            reasons=[]
            if len(cs)>1:reasons.append('duplicate_calls')
            if len(rs)>1:reasons.append('duplicate_results')
            if not cs:reasons.append('orphan_result')
            names={r['name'] for r in events if r['name'] is not None}
            if len(names)>1:reasons.append('name_conflict')
            if any(r['name'] is None for r in cs):reasons.append('missing_call_name')
            if any(r['identity_conflict'] for r in events):reasons.append('identity_conflict')
            if len(cs)==1 and len(rs)==1 and rs[0]['item_index']<cs[0]['item_index']:reasons.append('result_before_call')
            if reasons:anomalies.append({'callkey':key,'reasons':reasons})
            if len(cs)==1 and len(rs)==1 and not reasons:
                paired.append(key)
                if cs[0]['name']=='Read' and rs[0]['read_refusal_literal'] is True:read_refusals.append(key)
            elif len(cs)==1 and not rs and not reasons:
                unmatched.append({'callkey':key,'name':cs[0]['name'],'command_class':cs[0]['command_class'],'item_index':cs[0]['item_index']})
        for r in missing:anomalies.append({'callkey':None,'reasons':['missing_callkey'],'item_index':r['item_index']})
        eligible=(not anomalies and a['identity_consistent'] and a['coverage']=='selected_single_local_agent_trace' and a['representation']=='sanitized_native_rows' and a['has_more'] is False and a['offset']==0 and a['loaded_items']==a['declared_total'])
        bash=any(r['name']=='Bash' for r in unmatched)
        item={'attempt':aid,'cohort':a['cohort'],'bridge_status':a['bridge_status'],'status_source':a['bridge_status_source'],'snapshot_eligible':eligible,'call_counts':dict(sorted(collections.Counter(r['name'] or 'unknown' for r in calls).items())),'call_rows':len(calls),'result_rows':len(results),'unique_pairs':len(paired),'unmatched_calls':unmatched,'pairing_anomalies':anomalies,'bash_unmatched':bash,'read_refusal':bool(read_refusals),'read_refusal_callkeys':read_refusals,'final_three_key_json':a['final_three_key_json'],'call_route_by_step':[{'step_seq':step,'tools':[r['name'] for r in calls if r['step_seq']==step]} for step in dict.fromkeys(r['step_seq'] for r in calls)],'display_chars':sum(r['display_chars'] or 0 for r in results),'display_utf8_bytes':sum(r['display_utf8_bytes'] or 0 for r in results),'display_units_complete':all(r['display_chars'] is not None for r in results),'dual_representation_rows':sum(r['output_present'] and r['provider_result_present'] for r in results),'differing_representation_rows':sum(r['representations_differ'] is True for r in results)}
        per.append(item)
        totals.update({'call_rows':len(calls),'result_rows':len(results),'unique_pairs':len(paired),'unmatched_calls':len(unmatched),'pairing_anomalies':len(anomalies),'dual_representation_rows':item['dual_representation_rows'],'differing_representation_rows':item['differing_representation_rows']})
        cross[(a['bridge_status'],bash,bool(read_refusals))]+=1
    waiting=[p for p in per if p['bridge_status']=='waiting_user'];completed=[p for p in per if p['bridge_status']=='completed']
    comparison_ready=all(p['snapshot_eligible'] and p['bridge_status'] in ('completed','waiting_user','failed') for p in per)
    separation=bool(waiting and completed and all(p['bash_unmatched'] for p in waiting) and not any(p['bash_unmatched'] for p in completed)) if comparison_ready else None
    refusal_necessary=all(p['read_refusal'] for p in waiting) if comparison_ready and waiting else None
    return {'schema':'pause-result-v2','scope':'13 selected archived attempts only','totals':dict(sorted(totals.items())),'attempts':per,'cross_table':[{'bridge_status':k[0],'bash_unmatched':k[1],'read_refusal':k[2],'attempts':v} for k,v in sorted(cross.items(),key=lambda item: ('' if item[0][0] is None else item[0][0], item[0][1], item[0][2]))],'comparison_ready':comparison_ready,'waiting_attempts':len(waiting),'completed_attempts':len(completed),'observed_bash_separation':separation,'read_refusal_necessary_for_waiting_in_this_table':refusal_necessary,'causal_approval_mechanism':'unknown','action_vs_snapshot':'unidentified','private_source_authenticity':'not_publicly_verified','total_cost':None,'true_wait_seconds':None,'recovery_duration_seconds':None}


def verify(data, fixed_result):
    result=analyze(data)
    require(json.dumps(result,sort_keys=True,allow_nan=False)==json.dumps(fixed_result,sort_keys=True,allow_nan=False), 'fixed result differs from derived-table recomputation')
    return result


def main():
    base=Path(__file__).resolve().parent
    data=json.loads((base/'derived.json').read_text(encoding='utf-8'))
    result=json.loads((base/'result.json').read_text(encoding='utf-8'))
    verified=verify(data,result)
    print(json.dumps({'verification':'derived-table logic only','totals':verified['totals'],'observed_bash_separation':verified['observed_bash_separation'],'action_vs_snapshot':verified['action_vs_snapshot']},ensure_ascii=False,sort_keys=True))

if __name__=='__main__':
    main()
