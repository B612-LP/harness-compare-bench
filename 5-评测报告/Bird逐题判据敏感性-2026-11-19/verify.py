"""Reproject declared Bird item outcomes from pinned public Git blobs only."""
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_EVEN
from hashlib import sha256
from pathlib import Path
import json
import os
import subprocess
import sys

BASE = 'dd5a12f651527923a412f6727d5d2f9c22457026'
LOCK = 'afccd6ac7750e7dd43323013a0b731641f3c33b7b3bb113c02ecebd832768a70'
CASE = 'bird-ca-schools-15'
ITEMS = tuple(map(str, (28,36,62,83,87,12,23,24,25,26,27,31,5,11,17)))
GUARDS = ('input_integrity','answers_file','answers_schema','answers_coverage')
PAIR = [('A:codex','A:dsh'), ('B:yuanbao','B:doubao')] + [(f'R{i}:codex',f'R{i}:dsh') for i in (1,2,3)]
SLOTS = tuple(s for p in PAIR for s in p)+('W:workbuddy',)
SCENARIOS = {'all':(), 'exclude26':('26',), 'exclude27':('27',), 'exclude_both':('26','27')}

class Reject(ValueError): pass

def need(condition, code):
    if not condition:
        raise Reject(code)

def parse(raw):
    def mapping(pairs):
        obj = {}
        for k, v in pairs:
            need(k not in obj, 'DUPLICATE')
            obj[k] = v
        return obj
    def invalid(_):
        raise Reject('NONFINITE')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=mapping, parse_float=Decimal, parse_constant=invalid)

def digest(raw): return sha256(raw).hexdigest()

def fixed(root):
    here = Path(__file__).resolve().parent
    raw = (here/'sources.json').read_bytes()
    need(digest(raw)==LOCK, 'LOCK')
    data = parse(raw)
    need(data.get('commit')==BASE, 'CONTRACT')
    need(len(data['sources'])==28, 'COUNT')
    env = {**os.environ,'GIT_OPTIONAL_LOCKS':'0','GIT_NO_LAZY_FETCH':'1','GIT_ALLOW_PROTOCOL':'','GIT_NO_REPLACE_OBJECTS':'1'}
    def git(*args):
        return subprocess.run(['git','-c','core.hooksPath=/dev/null',*args],cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=True,timeout=8).stdout
    out = {}
    for item in data['sources']:
        key = item['slot'],item['role']
        need(key not in out and git('rev-parse',BASE+':'+item['path']).decode().strip()==item['blob'],'PATH_ROLE')
        body = git('cat-file','blob',item['blob'])
        need(len(body)==item['length'] and digest(body)==item['sha256'],'SOURCE_HASH')
        out[key] = body
    need(all((slot, role) in out for slot in SLOTS for role in ('stdout','receipt')), 'SLOTS')
    return out

def money(n, d, places, scale=1):
    return (Decimal(scale)*n/d).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_EVEN)

def decimal(x):
    need(type(x) in (int, Decimal), 'NUMTYPE')
    return Decimal(x)

def strict_equal(a,b):
    if type(a) is not type(b): return False
    if type(a) is dict: return a.keys()==b.keys() and all(strict_equal(a[k],b[k]) for k in a)
    if type(a) is list: return len(a)==len(b) and all(strict_equal(x,y) for x,y in zip(a,b))
    return a==b

def project(stdout, receipt, slot, checker_hash):
    need(type(stdout) is dict and type(receipt) is dict and stdout.get('case')==CASE, 'ENVELOPE')
    need(stdout.get('binary') is True and decimal(stdout.get('threshold'))==Decimal('0.8'), 'RULE')
    need(type(stdout.get('checks')) is list and len(stdout['checks'])==len(ITEMS)+len(GUARDS), 'CHECK_COUNT')
    checks = {}
    for item in stdout['checks']:
        need(type(item) is dict and type(item.get('id')) is str and type(item.get('pass')) is bool,'CHECK_TYPE')
        need(item['id'] not in checks,'CHECK_DUPLICATE');checks[item['id']] = item['pass']
    need(set(checks)==set(GUARDS)|{'q'+q for q in ITEMS},'CHECK_IDS')
    if 'guards_used' in stdout:
        v = stdout['guards_used']
        need(type(v) is list and all(type(k) is str for k in v) and len(v)==len(GUARDS) and set(v)==set(GUARDS),'GUARD_DECLARED')
    if 'n_tasks' in stdout:
        need(type(stdout['n_tasks']) is int and stdout['n_tasks']==len(ITEMS),'TASK_COUNT')
    m={q:checks['q'+q] for q in ITEMS}; failed=[q for q in ITEMS if not m[q]]; n=len(ITEMS)-len(failed)
    v=stdout.get('failed_questions')
    need(type(v) is list and all(type(x) is str for x in v) and len(v)==len(set(v)) and set(v)==set(failed),'FAILED_VECTOR')
    need(type(stdout.get('correct')) is int and stdout['correct']==n and type(stdout.get('n_questions')) is int and stdout['n_questions']==len(ITEMS),'COUNTS')
    need(decimal(stdout.get('weighted'))==money(n,len(ITEMS),2,100) and decimal(stdout.get('accuracy'))==money(n,len(ITEMS),4),'OUTPUT_ARITH')
    intact=stdout.get('input_integrity')
    need(intact in ('verified','unverified','fail') and checks['input_integrity']==(intact!='fail'), 'INTEGRITY_STATE')
    guarded=all(checks[k] for k in GUARDS)
    reward=int(guarded and n*5>=len(ITEMS)*4)
    need(type(stdout.get('reward')) is int and stdout['reward']==reward,'GUARDED_REWARD')
    rr=receipt.get('score',receipt)
    need(type(rr) is dict,'SCORE_SHAPE')
    for key, value in [('earned',n),('possible',15),('assessed',15),('reward',reward)]:
        need(type(rr.get(key)) is int and rr[key]==value,'RECEIPT_COUNTS')
    need(decimal(rr.get('reported'))==money(n,15,2,100),'RECEIPT_REPORTED')
    if 'case' in receipt:
        need(receipt['case']==CASE and receipt.get('product')==slot.split(':')[1],'RECEIPT_SCOPE')
    if 'rep' in receipt:
        need(type(receipt['rep']) is int and slot.split(':')[0]==f'R{receipt["rep"]}','RECEIPT_REP')
    embedded=receipt.get('raw_checker_output')
    if embedded is not None: need(strict_equal(embedded,stdout),'EMBEDDED_REPORT')
    ref=rr.get('checker_sha256')
    need(type(ref) is str and len(ref)==64 and all(ch in '0123456789abcdef' for ch in ref),'CHECKER_DECLARATION')
    need(guarded,'ITEM_PROJECTION_GUARD')
    return {'failed':failed,'correct':n,'item_verdicts':m,'guards':{k:checks[k] for k in GUARDS},'guards_list_present':'guards_used' in stdout,
            'input_integrity_report':intact,'reward_recorded':reward,'assessments':{s:aggregate(m,guarded,omit) for s,omit in SCENARIOS.items()},
            'checker_declared_sha_matches_current_anchor':ref==checker_hash,'embedded_report_matches':True if embedded is not None else None}

def aggregate(v,guarded,omit):
    kept=[v[x] for x in ITEMS if x not in omit]
    return {'correct':sum(kept),'possible':len(kept),'reward':int(guarded and sum(kept)*5>=len(kept)*4)}

def compare(a,b,raw_equal):
    am,bm=(set(a[k]) for a in (a,b) for k in ('failed',))
    ordered=lambda s:[q for q in ITEMS if q in s]
    return {'same_count':len(am)==len(bm),'same_vector':a['item_verdicts']==b['item_verdicts'] and a['guards']==b['guards'],'same_receipt_bytes':raw_equal,
            'common_fail':ordered(am&bm),'left_only_fail':ordered(am-bm),'right_only_fail':ordered(bm-am),
            'scenarios':{s:{'left':a['assessments'][s], 'right':b['assessments'][s],
                            'correct_gap_right_minus_left':b['assessments'][s]['correct']-a['assessments'][s]['correct']} for s in SCENARIOS}}

def controls(raw, rows, checker_hash):
    target='B:yuanbao'; a=parse(raw[target,'stdout']); rec=parse(raw[target,'receipt']); out={}
    def reject(label, mutate):
        b=deepcopy(a); c=deepcopy(rec); mutate(b,c)
        try: project(b,c,target,checker_hash)
        except Reject as e: out[label]=str(e)
        else: raise Reject('CONTROL_MISSED')
    reject('typed_boolean',lambda b,c:b['checks'][4].update({'pass':1}))
    reject('duplicate_id',lambda b,c:b['checks'][4].update({'id':b['checks'][5]['id']}))
    reject('missing_row',lambda b,c:b['checks'].pop())
    reject('relabel_unknown_id',lambda b,c:b['checks'][4].update({'id':'q109'}))
    reject('bad_receipt_assessed',lambda b,c:c['score'].update({'assessed':14}))
    reject('false_guard_original_reward',lambda b,c:b['checks'][3].update({'pass':False}))
    def false_guard_coherent(b,c):
        next(x for x in b['checks'] if x['id']=='answers_coverage')['pass']=False
        b['reward']=0
        c['score']['reward']=0
        if 'raw_checker_output' in c: c['raw_checker_output']=deepcopy(b)
    reject('false_guard_coherent_reward',false_guard_coherent)
    need(out['false_guard_coherent_reward']=='ITEM_PROJECTION_GUARD','CONTROL_WRONG_REASON')
    altered=deepcopy(rows[target]); altered['guards']['answers_coverage']=False
    need(compare(rows[target],altered,False)['same_vector'] is False,'FULL_VECTOR_GUARD')
    out['same_items_different_guard']='different_vector'
    b=deepcopy(a); b['checks'].reverse(); need(project(b,rec,target,checker_hash)==rows[target],'REORDER')
    out['permuted_rows']='same_by_id'
    l={q:q!='26' for q in ITEMS};r={q:q!='27' for q in ITEMS}
    need(aggregate(l,True,())==aggregate(r,True,()) and l!=r and aggregate(l,True,('26',))!=aggregate(r,True,('26',)),'SAME_SCORE')
    out['equal_score_different_item']='same_count_unequal_vector'
    need(aggregate({q:True for q in ITEMS},False,('26','27'))['reward']==0,'GUARD_INVARIANT')
    out['exclude_retains_guard']='failed_guard_stays_zero'
    return out


def assess(stdout, receipt, slot, anchor):
    rr=receipt.get('score',receipt)
    n=stdout.get('correct'); need(type(n) is int and 0<=n<=15,'COUNT_TYPE')
    reported=decimal(rr.get('reported')); mode='matches_2dp'
    if reported!=money(n,15,2,100):
        need(rr.get('rule_version')=='freeze-20261029-v2' and slot in ('A:codex','A:dsh',*(s for s in SLOTS if s.startswith('R'))) and reported==money(n,15,8,100),'RECEIPT_PROFILE_PRECISION')
        receipt=deepcopy(receipt)
        receipt.get('score',receipt)['reported']=money(n,15,2,100);mode='matches_8dp_not_2dp'
    return {**project(stdout,receipt,slot,anchor),'receipt_display_arithmetic':mode}



def public_projection(result):
    return {'profile':'bird-fixed-reported-items-v1','source_count':result['source_count'],
            'v1_precision_rejections':result['v1_unknown'],
            'rows':{s:{k:r[k] for k in ('correct','failed','guards','input_integrity_report','reward_recorded','receipt_display_arithmetic','checker_declared_sha_matches_current_anchor','embedded_report_matches')} for s,r in result['rows'].items()},
            'pairs':result['pairs'],'controls':result['v1_controls'],'precision_controls':result['delta_controls']}

def build(root):
    raw = fixed(root)
    chk = digest(raw['anchor','checker'])
    pre, post, rejected = {}, {}, {}
    for slot in SLOTS:
        stdout, receipt = (parse(raw[slot,role]) for role in ('stdout','receipt'))
        try: pre[slot] = project(stdout,receipt,slot,chk)
        except Reject as err: rejected[slot]=str(err)
        post[slot]=assess(stdout,receipt,slot,chk)
    need(rejected=={'A:codex':'RECEIPT_REPORTED','R1:dsh':'RECEIPT_REPORTED'},'PRECISION_REJECTIONS')
    need(all(pre[k]=={f:x for f,x in post[k].items() if f!='receipt_display_arithmetic'} for k in pre),'EXISTING_ROWS')
    pairs={f'{a}__{b}':compare(post[a],post[b],raw[a,'receipt']==raw[b,'receipt']) for a,b in PAIR}
    a, ar=(parse(raw['A:codex',f]) for f in ('stdout','receipt'))
    b, br=(parse(raw['B:yuanbao',f]) for f in ('stdout','receipt'))
    extra={}
    def reject(label,out,rec,slot,code):
        try: assess(out,rec,slot,chk)
        except Reject as err:
            need(str(err)==code,'DELTA_WRONG_CODE');extra[label]=code
        else: raise Reject('DELTA_NOT_REJECTED')
    bad=deepcopy(ar); bad['score']['reported']=Decimal('93.33333334')
    reject('one_precision_digit',a,bad,'A:codex','RECEIPT_PROFILE_PRECISION')
    bad=deepcopy(br); bad['score']['reported']=Decimal('93.33333333')
    reject('wrong_b_profile',b,bad,'B:yuanbao','RECEIPT_PROFILE_PRECISION')
    bad=deepcopy(ar); bad['score']['reported']=True
    reject('boolean',a,bad,'A:codex','NUMTYPE')
    reject('source_scope',a,ar,'A:dsh','RECEIPT_SCOPE')
    out=public_projection({'source_count':len(raw),'v1_unknown':rejected,'rows':post,'pairs':pairs,
                           'v1_controls':controls(raw,pre,chk),'delta_controls':extra})
    out['reported_guard_conditional_counts']={
        'evaluated':sum(len(r['assessments']) for r in post.values()),
        'passes':sum(z['reward'] for r in post.values() for z in r['assessments'].values()),
    }
    out['cross_repeat_bytes']={
        'codex_r1_r3_stdout_equal':raw['R1:codex','stdout']==raw['R3:codex','stdout'],
        'dsh_r2_r3_receipt_equal':raw['R2:dsh','receipt']==raw['R3:dsh','receipt'],
        'dsh_r2_r3_stdout_equal':raw['R2:dsh','stdout']==raw['R3:dsh','stdout'],
    }
    return out

def main():
    try:
        result=build(Path.cwd())
        expected=parse((Path(__file__).resolve().parent/'evidence.json').read_bytes())
        need(strict_equal(result,expected),'EVIDENCE_MISMATCH')
        print('OK: 11 receipt/stdio projections, five pairs, eleven baseline and four precision controls')
        return 0
    except (Reject,ValueError,KeyError,TypeError,OSError,subprocess.SubprocessError) as err:
        print(f'PROJECTION_REJECT:{type(err).__name__}',file=sys.stderr)
        return 2

if __name__=='__main__':
    sys.exit(main())
