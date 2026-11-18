#!/usr/bin/env python3
"""Fixed public derived desktop table; no native archival or external access."""
import argparse
from copy import deepcopy
from hashlib import sha256
import json
from math import factorial
from pathlib import Path
import sys

PINS = {
    'baseline': ('4-打分细则/Harness统一观测规范-2026-11-19/cases.json', 5121, '11213335778ca5a2b40c2e7852b3c83ab04961286e8ad8212c24252497bae67f'),
    'wb': ('4-打分细则/WorkBuddy前驱与完成边-2026-11-19/evidence.json', 2457, '03a900e9c0270bc4de8825ec5d5320780253f040c6a225b5f9e76fab031e97cd'),
    'db': ('4-打分细则/豆包同名调用归属-2026-11-19/evidence.json', 1240, 'c03f8405b0145440a037a3ef3c249cc5293cd94339a69df217cd6e5044282b50'),
}


def check(value):
    if not value:
        raise ValueError('invalid fixed desktop input or control')


def json_pairs(pairs):
    out = {}
    for k,v in pairs:
        check(k not in out)
        out[k]=v
    return out


def load(root):
    output={}
    for key,(relative,size,digest) in PINS.items():
        leaf=root/relative
        check(leaf.is_file() and leaf.resolve()==leaf)
        with leaf.open('rb') as stream:
            data=stream.read(size+1)
        check(len(data)==size and sha256(data).hexdigest()==digest)
        output[key]=json.loads(data.decode('utf-8','strict'),object_pairs_hook=json_pairs)
    return output


def positive(x):
    return type(x) is int and x>0


def ordered(values):
    return type(values) is list and all(positive(x) for x in values) and values==sorted(set(values))


def signature(scope, result, call):
    return ((scope,'result',result),(scope,'call',call))


def assess(scope,calls,results,relations,on_one_axis=True):
    check(ordered(calls) and ordered(results))
    rmap={}
    used=set()
    for (rs,rr,r),(cs,cr,c) in relations:
        if not (rs==cs==scope and rr=='result' and cr=='call' and positive(r) and positive(c) and
                r in results and c in calls and r not in rmap and c not in used and (not on_one_axis or c<r)):
            return None
        rmap[r]=c
        used.add(c)
    if not (len(rmap)==len(calls)==len(results)>0):
        return None
    hits=[]
    for from_end in (False,True):
        remaining=calls[:]
        agree=0
        for r in results:
            eligible=[c for c in remaining if not on_one_axis or c<r]
            check(eligible)
            choice=eligible[-1] if from_end else eligible[0]
            agree+=choice==rmap[r]
            remaining.remove(choice)
        hits.append(agree)
    return len(rmap),hits,rmap


def wb_window(window):
    roles=window['roles']
    check(all(r in ('call','result') for r in roles))
    preds=window['record_predecessors']
    check(all(len(x)==2 and all(positive(n) for n in x) for x in preds))
    check(preds==[[i,i-1] for i in range(2,len(roles)+1)])
    calls=[i for i,r in enumerate(roles,1) if r=='call']
    results=[i for i,r in enumerate(roles,1) if r=='result']
    scope=('wb',window['block'])
    edges=[signature(scope,r['result'],r['call']) for r in window['completions']]
    return scope,calls,results,edges,dict(preds)


def db_window(label,ordinal,window):
    label_scope=('db',label,ordinal)
    names=window['call_name_classes']; results=window['tool_rows']; head=window['assistant_row']
    check(positive(head) and ordered(results) and all(positive(x) and x==1 for x in names))
    check(results==list(range(head+1,head+len(names)+1)))
    calls=list(range(1,len(names)+1))
    if label=='B':
        check(window['identity']==window['fifo']=='unknown')
        return label_scope,calls,results,[]
    pos=window['matched_call_positions']
    edges=[] if len(pos)!=len(results) else [signature(label_scope,r,c) for r,c in zip(results,pos)]
    return label_scope,calls,results,edges


def reproduce(data):
    check(data['baseline']['schema']=='harness-observation-candidate-cases/0.3' and data['baseline']['frozen'] is False)
    check(len(data['baseline']['cases'])==14)
    wb=data['wb']; db=data['db']
    check(wb['schema']=='workbuddy-local-ordinal-edges-v1' and db['schema']==1)
    check(db['source_relation']=='different_archived_tasks' and db['B']['membership']=='unadjudicated')
    w_totals=[0,0,0]; d_totals=[0,0,0]; pred=[0,0,0]
    for window in wb['blocks']:
        scope,calls,results,edges,prev=wb_window(window)
        n,(fifo,lifo),links=assess(scope,calls,results,edges)
        for i,value in enumerate((n,fifo,lifo)):
            w_totals[i]+=value
        for r,c in links.items():
            p=prev.get(r)
            pred[0 if p==c else 1 if p in calls else 2]+=1
    variants=[]
    for label in ('A','B'):
        for i,window in enumerate(db[label]['blocks'],1):
            scope,calls,results,edges=db_window(label,i,window)
            measure=assess(scope,calls,results,edges,False)
            if label=='A':
                n,(fifo,lifo),_=measure
                for k,value in enumerate((n,fifo,lifo)):
                    d_totals[k]+=value
            else:
                check(measure is None and 0<len(calls)==len(results)<=4)
                variants.append(factorial(len(calls)))
    check(w_totals==d_totals==[7,7,1] and pred==[1,3,3] and variants==[6,24])
    return {'workbuddy':dict(zip(('bound','fifo_agree','lifo_agree'),w_totals)),
            'workbuddy_direct_predecessor_same_other_noncall':pred,
            'doubao_A':dict(zip(('bound','fifo_agree','lifo_agree'),d_totals)),
            'doubao_B':{'attachment':None,'fifo':None,'lifo':None,'conditional_bijections':variants},
            'wire_history_execution_full_body':'unobserved_by_these_derivatives','frozen':False}


def selftest(data):
    scope,calls,results,edges,prev=wb_window(data['wb']['blocks'][0])
    check(assess(scope,calls,results,edges)[1]==[2,0])
    swap=[signature(scope,results[0],calls[1]),signature(scope,results[1],calls[0])]
    check(assess(scope,calls,results,swap)[1]==[0,2])
    check(assess(scope,calls,results,edges[:-1]) is None)
    check(assess(scope,calls,results,[*edges,edges[0]]) is None)
    check(assess(scope,calls,results,[edges[0],(edges[1][0],(('other',scope),'call',calls[1]))]) is None)
    check(assess(scope,[1,4],[2,3],[signature(scope,2,4),signature(scope,3,1)]) is None)
    a=deepcopy(data['db']['A']['blocks'][0]); a['matched_call_positions'].append(1)
    check(assess(*db_window('A',1,a),False) is None)
    a=deepcopy(data['db']['A']['blocks'][0]); a['matched_call_positions'][0]=True
    check(assess(*db_window('A',1,a),False) is None)
    a=deepcopy(data['wb']['blocks'][0]); a['record_predecessors'][0][1]=True
    try:
        wb_window(a)
    except ValueError:
        pass
    else:
        raise ValueError('bool predecessor accepted')
    return 8


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--self-test',action='store_true')
    args=p.parse_args()
    try:
        data=load(args.root.resolve()); out=reproduce(data)
        if args.self_test:
            out['synthetic_controls']=selftest(data)
        print(json.dumps(out,sort_keys=True,indent=2))
    except (ValueError,TypeError,KeyError,IndexError,OSError,UnicodeError):
        sys.exit('desktop derived verification refused')
