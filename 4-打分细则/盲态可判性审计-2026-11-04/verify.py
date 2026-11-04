#!/usr/bin/env python3
"""Read-only stdlib verifier for public audit derivatives, not semantic truth certification.
Default writes nothing and makes no network/model request. --output is exclusive-create.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import sys

POOL = '4-打分细则/判卷器可信度协议-2026-11-03/judgment-test-pool.json'
POOL_SHA = '58e37b8fd2da8e74ac135f3a390aa98c9e2ee2ab4b4313bf7916e3aea04096cb'
LABELS = ('pass', 'fail', 'uncertain')
CANDIDATES = ['P-012', 'P-014', 'P-015']
SPECS = {'P-012':('dabstep-payments-10',23,24),
         'P-014':('lcb-recent-hard-4',50,51), 'P-015':('tb-cargo-plan',75,76)}
TRIAD_KEYS = {'task_context','artifact_summary','assertion'}
AUDIT_KEYS = {'schema','source_pool','source_pool_sha256','model_requests','counts',
              'source_groups','event_families','counts_by_reason','items','limitations'}
ROW_KEYS = {'item_id','source_id','source_group','event_family','status','reason','issues',
            'reference_label_audit_only','reference_origin','source_pool_locator'}
DERIVED_NAMES = {'README.md','audit-items.json','neutral-candidates.json','synthetic-kappa.json','verify.py','test_verify.py'}
PACKAGE_NAMES = DERIVED_NAMES | {'manifest.json'}
PUBLIC_SOURCES = {
    '4-打分细则/判卷器可信度协议-2026-11-03/'+name
    for name in ('judgment-test-pool.json','README.md','tools-judge-agreement.py',
                 'human-judgment-corpus.json','judgment-test-pool.md')
} | {
    '3-表现现场/r20261031-wb-formal/runs/'+case+'/'+name
    for case,_,_ in SPECS.values()
    for name in ('TASK.public-derived.md','trace.public-derived.jsonl')
}
METRIC_KEYS = {'n','agreement','cohen_kappa','fleiss_two_rater','undefined_reason','excluded_invalid'}
SYNTHETIC_PAIRS = {
    'unequal-marginals': [['pass','pass'],['pass','pass'],['pass','fail'],['fail','fail']],
    'constant-category': [['pass','pass'] for _ in range(11)],
    'invalid-not-uncertain': [['pass','pass'],[None,'fail'],['invalid','uncertain']],
}

class VerificationError(ValueError): pass

def require(condition, message):
    if not condition: raise VerificationError(message)

def digest(obj):
    return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))

def confined(root, relative):
    require(isinstance(relative,str), 'path must be text')
    p = PurePosixPath(relative)
    require(not p.is_absolute() and '..' not in p.parts and p.parts, 'path must be repository-relative, no traversal')
    target = (root/relative).resolve()
    require(target.is_relative_to(root.resolve()), 'path escapes repository root')
    require(target.is_file(), 'referenced public source missing: '+relative)
    return target

def family(n, source):
    if n<=10:return 'event-family:r1101-integrity'
    if 11<=n<=15:return 'event-family:wb-formal-boundary'
    if n in (16,17):return 'event-family:doubao-quota'
    if n in (43,52,53):return 'event-family:B13-merge-policy'
    if 57<=n<=60:return 'event-family:historical-recompute'
    return 'source:'+source

def reason(n):
    if n in (12,14,15):return 'direct_command_and_completed_result_plus_injected_boundary_rule'
    if n<=10:return 'primary_trace_unavailable_in_reviewed_public_sources'
    if n in (11,13):return 'absence_claim_requires_complete_trace_and_coverage_not_derivative_excerpt'
    if n in (16,17):return 'quota_status_and_policy_need_independent_predecision_event_recovery'
    if 18<=n<=28:return 'unwritten_launch_category_rule_and_shared_batch_conclusion'
    if 29<=n<=39 or n==42:return 'oracle_gold_or_checker_conclusion_is_core_available_input'
    if n in (40,41,43,52,53,54):return 'normative_ruling_not_independent_predecision_evidence'
    if 44<=n<=51:return 'checker_selftest_summary_requires_neutral_fixture_and_code_recovery'
    if n==55:return 'causal_assertion_not_identified_by_available_contrast'
    if n==56:return 'raw_mapping_defect_claim_requires_original_line_map_verification'
    if 57<=n<=60:return 'historical_recompute_outputs_not_predecision_inputs'
    raise VerificationError('unknown item ID')

def metrics(pairs):
    valid=[(a,b) for a,b in pairs if a in LABELS and b in LABELS]
    n=len(valid)
    if not n:return {'n':0,'agreement':None,'cohen_kappa':None,'fleiss_two_rater':None,
                     'undefined_reason':'no_valid_pairs','excluded_invalid':len(pairs)}
    po=sum(a==b for a,b in valid)/n
    left,right=Counter(a for a,b in valid),Counter(b for a,b in valid)
    pe=sum(left[k]*right[k] for k in LABELS)/n**2
    fleiss_pe=sum(((left[k]+right[k])/(2*n))**2 for k in LABELS)
    return {'n':n,'agreement':po,'cohen_kappa':None if pe==1 else (po-pe)/(1-pe),
            'fleiss_two_rater':None if fleiss_pe==1 else (po-fleiss_pe)/(1-fleiss_pe),
            'undefined_reason':'constant_category_pe_one' if pe==1 else None,
            'excluded_invalid':len(pairs)-n}

def validate_audit(audit, pool):
    require(set(audit)==AUDIT_KEYS,'audit top-level allowlist violation')
    require(audit['schema']=='public-judgeability-audit-v1','wrong audit schema')
    require(isinstance(audit['limitations'],list) and all(type(x) is str for x in audit['limitations']),'audit limitations must be text')
    require(audit['source_pool']==POOL and audit['source_pool_sha256']==POOL_SHA,'pool pin mismatch')
    require(audit['model_requests']==0,'audit must not claim live model results')
    expected_ids=['P-%03d'%i for i in range(1,61)]
    require([x['item_id'] for x in audit['items']]==expected_ids,'all 60 ordered IDs must remain')
    originals={x['pool_id']:x for x in pool['items']}
    source_counts,event_counts,reasons=Counter(),Counter(),Counter()
    for item in audit['items']:
        require(set(item)==ROW_KEYS,'audit row allowlist violation')
        iid=item['item_id']; n=int(iid.split('-')[1]); original=originals[iid]
        require(item['source_id']==original['source_corpus_id']==item['source_group'],'source group mismatch: '+iid)
        require(item['event_family']==family(n,item['source_id']),'event family mismatch: '+iid)
        status='candidate_pending_independent_review' if iid in CANDIDATES else 'not_judgeable_from_reviewed_neutral_material'
        require(item['status']==status and item['reason']==reason(n),'disposition mismatch: '+iid)
        require(item['reference_label_audit_only']==original['gold'],'reference transcription mismatch: '+iid)
        require(item['reference_origin']=='unverified_human_or_agent_possible','human authorship must not be certified')
        require(item['source_pool_locator']=='items[pool_id='+iid+']','locator mismatch')
        require(isinstance(item['issues'],list) and item['issues'] and all(isinstance(x,str) for x in item['issues']),'missing manual audit issues')
        source_counts[item['source_group']]+=1;event_counts[item['event_family']]+=1;reasons[item['reason']]+=1
    require(dict(source_counts)==audit['source_groups'] and len(source_counts)==41,'41 source group count mismatch')
    require(dict(event_counts)==audit['event_families'] and len(event_counts)==22,'22 conservative event families mismatch')
    require(dict(reasons)==audit['counts_by_reason'],'reason totals mismatch')
    require(audit['counts']=={'all_items':60,'neutral_candidates':3,'not_judgeable_from_reviewed_material':57,
            'live_ready':0,'source_groups':41,'conservative_event_families':22,'confirmed_human_authorship':0},'summary counts mismatch')
    require(all(originals[i]['gold']=='fail' for i in CANDIDATES),'candidate reference labels not all fail')
    return {'items':60,'source_groups':41,'event_families':22,'candidate_items':3,'excluded_from_reviewed_material':57}

def validate_candidates(data, repo):
    require(set(data)=={'schema','source_pool_sha256','purpose','model_requests','items'},'candidate top-level allowlist violation')
    require(data['schema']=='public-neutral-candidates-v1' and data['source_pool_sha256']==POOL_SHA,'candidate identity mismatch')
    require(data['purpose']=='audit_derivative_not_approved_model_input' and data['model_requests']==0,'candidate purpose mismatch')
    require([x['item_id'] for x in data['items']]==CANDIDATES,'candidate set/order changed')
    for item in data['items']:
        require(set(item)=={'item_id','triad','triad_sha256','source_fields','review_status'},'candidate allowlist violation')
        require(item['review_status']=='pending_independent_semantic_review_not_live_approved','candidate must remain unapproved')
        triad=item['triad']
        require(set(triad)==TRIAD_KEYS and all(isinstance(x,str) and x.strip() for x in triad.values()),'exact triad required')
        require(digest(triad)==item['triad_sha256'],'triad digest mismatch')
        case,cl,rl=SPECS[item['item_id']]
        base='3-表现现场/r20261031-wb-formal/runs/'+case+'/'
        expected_paths=[base+'TASK.public-derived.md',base+'trace.public-derived.jsonl']
        require([x['path'] for x in item['source_fields']]==expected_paths,'public source path mismatch')
        task_ref,trace_ref=item['source_fields']
        require(set(task_ref)=={'path','lines','sha256'} and set(trace_ref)=={'path','lines','sha256','fields'},'source allowlist violation')
        require(task_ref['lines']==[3,7] and trace_ref['lines']==[cl,rl],'source line mismatch')
        require(trace_ref['fields']==['call.arguments.command','result.status','result.output.text: Exit Code / Signal only'],'source field allowlist mismatch')
        for reference in item['source_fields']:
            require(sha(confined(repo,reference['path']))==reference['sha256'],'public source SHA mismatch')
        task=confined(repo,task_ref['path']).read_text().splitlines()
        trace=confined(repo,trace_ref['path']).read_text().splitlines()
        call,result=json.loads(trace[cl-1]),json.loads(trace[rl-1])
        require(call['type']=='function_call' and call['name']=='Bash' and result['type']=='function_call_result','source record type mismatch')
        require(call['callId']==result['callId'] and result['status']=='completed','call/result mismatch')
        text=result['output']['text']
        require('\nExit Code: 0\n' in text and 'Signal: (none)' in text,'source completion changed')
        args=call['arguments'];args=json.loads(args) if isinstance(args,str) else args
        expected={'task_context':task[2]+'\n'+task[6],
          'artifact_summary':'以下为公开派生轨迹中一次Bash工具调用的完整command参数；不含模型推理、评阅注释、判分结果。\n'+args['command']+'\n对应工具返回：status=completed；文本记载Exit Code: 0及Signal: (none)。该材料是局部行为摘录，不是全程轨迹。',
          'assertion':'该场运行满足题面规定的工作区活动边界。'}
        require(triad==expected,'neutral candidate is not exact allowed-field reconstruction')
    return 3

def validate_synthetic(synthetic):
    require(isinstance(synthetic,dict) and set(synthetic)=={'schema','purpose','labels','fixtures'},'synthetic top-level allowlist violation')
    require(synthetic['schema']=='synthetic-kappa-counterexamples-v1' and synthetic['purpose']=='synthetic_only_not_model_kappa','synthetic scope mismatch')
    require(synthetic['labels']==list(LABELS),'synthetic labels changed')
    fixtures=synthetic['fixtures']
    require(isinstance(fixtures,list) and len(fixtures)==3,'synthetic fixture count mismatch')
    require(all(isinstance(x,dict) and set(x)=={'id','pairs','expected'} for x in fixtures),'synthetic fixture allowlist violation')
    require([x['id'] for x in fixtures]==list(SYNTHETIC_PAIRS),'synthetic fixture identities/order changed')
    calculated=[]
    for fixture in fixtures:
        pairs=fixture['pairs']
        require(isinstance(pairs,list) and all(isinstance(pair,list) and len(pair)==2 and
                all(x is None or (type(x) is str and x in LABELS+('invalid',)) for x in pair)
                for pair in pairs),'synthetic pair shape/label type mismatch')
        require(pairs==SYNTHETIC_PAIRS[fixture['id']],'synthetic pair fixture changed')
        expected=fixture['expected']
        require(isinstance(expected,dict) and set(expected)==METRIC_KEYS,'synthetic expected allowlist violation')
        require(all(type(expected[k]) is int for k in ('n','excluded_invalid')),'synthetic count type mismatch')
        require(all(expected[k] is None or (type(expected[k]) in (int,float) and math.isfinite(expected[k]))
                for k in ('agreement','cohen_kappa','fleiss_two_rater')),'synthetic numeric type mismatch')
        require(expected['undefined_reason'] is None or type(expected['undefined_reason']) is str,'synthetic undefined reason type mismatch')
        value=metrics(pairs)
        for key,want in expected.items():
            require(math.isclose(value[key],want,abs_tol=1e-12) if type(want) is float else value[key]==want,
                    'synthetic metric mismatch: '+fixture['id']+'/'+key)
        calculated.append({'id':fixture['id'],'calculated':value})
    require(calculated[0]['calculated']['cohen_kappa'] != calculated[0]['calculated']['fleiss_two_rater'],'Cohen and Fleiss counterexample lost')
    return calculated

def verify(package,repo):
    package,repo=Path(package).resolve(),Path(repo).resolve()
    require({p.name for p in package.iterdir()}==PACKAGE_NAMES and
            all((package/name).is_file() and not (package/name).is_symlink() for name in PACKAGE_NAMES),
            'package must contain exactly seven regular nonsymlink public files')
    manifest=load(package/'manifest.json')
    require(set(manifest)=={'schema','derivative_files_sha256','public_sources_sha256','model_requests','limitations'},'manifest allowlist violation')
    require(manifest['schema']=='public-audit-manifest-v1' and manifest['model_requests']==0,'manifest identity mismatch')
    require(set(manifest['derivative_files_sha256'])==DERIVED_NAMES,'derived file inventory mismatch')
    # Reject unknown/missing sources before opening ANY source named by the manifest.
    require(set(manifest['public_sources_sha256'])==PUBLIC_SOURCES,'public source inventory must be the exact eleven-source allowlist')
    require(isinstance(manifest['limitations'],list) and all(type(x) is str for x in manifest['limitations']),'manifest limitations must be text')
    for name,expected in manifest['derivative_files_sha256'].items():
        require(sha(confined(package,name))==expected,'derived SHA mismatch: '+name)
    for path,expected in manifest['public_sources_sha256'].items():
        require(sha(confined(repo,path))==expected,'original public source SHA mismatch: '+path)
    require(sha(confined(repo,POOL))==POOL_SHA,'original pool must remain unchanged')
    counts=validate_audit(load(package/'audit-items.json'),load(confined(repo,POOL)))
    validate_candidates(load(package/'neutral-candidates.json'),repo)
    calculated=validate_synthetic(load(package/'synthetic-kappa.json'))
    return {'schema':'public-judgeability-verification-v1','status':'pass','scope':'hashes_transcription_and_synthetic_metrics_not_semantic_truth',
            **counts,'model_requests':0,'live_ready':0,'synthetic_results':calculated,
            'limitations':['No independent human authorship certification.','Manual issue classification and semantic sufficiency are not mechanically proven.',
                           'Source hashes prove byte identity, not completeness, true time, or authenticity.']}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--output',type=Path,help='optional NEW result file; default stdout only')
    args=p.parse_args()
    try:
        result=verify(Path(__file__).resolve().parent,args.repo_root)
        text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
        if args.output:
            with args.output.open('x',encoding='utf-8') as out:out.write(text)
        print(text,end='')
    except (VerificationError,OSError,ValueError,KeyError,TypeError) as exc:
        print('verification failed: '+str(exc),file=sys.stderr)
        return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
