#!/usr/bin/env python3
"""Correct only a reviewer type error: unbound prepare null != bound run timestamp.
Preserve first receipt/program. Rehash every protected input and validate actual claims.
The real E2 self-hash mismatch remains a failure; no original input is altered.
"""
import copy,hashlib,json,re
from datetime import datetime
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return {'sha256':h.hexdigest(),'bytes':p.stat().st_size}
def create(p,obj):
    s=json.dumps(obj,ensure_ascii=False,indent=2)+'\n'
    t=re.sub(r'(?i)\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b',lambda m:m[0].replace('-',r'\u002d'),s)
    assert json.loads(t)==obj
    with p.open('x',encoding='utf-8') as f:f.write(t)
def main():
    first=OUT/'independent-check-01.json';original=json.loads(first.read_text());out=copy.deepcopy(original)
    changed=[]
    for c in out['checks']:
        match=re.fullmatch(r'(E[12]) archived (binding identity|registered_at exact committer) (.+)',c['name'])
        if c['pass'] or not match:continue
        label,kind,rel=match.groups()
        if Path(rel).name!='meta.prepare.json':continue
        field='preregistration_commit' if kind=='binding identity' else 'registered_at'
        p=ROOT/out['aborted_archives'][label]['path']/rel;obj=json.loads(p.read_text())
        if field not in obj or obj[field] is not None:continue
        old=copy.deepcopy(c)
        c.update(name=label+' prepare explicitly unbound '+field+' '+rel,pass_=True)
        c.pop('pass_',None);c['pass']=True
        c['detail']={'value':None,'type':'prepare-time template, not bound execution record','registered_timestamp_inferred':False,'next':'use separate original claim/run metadata for known binding','stop':'never infer a registered_at value from this null'}
        changed.append({'first_assertion':old,'corrected_assertion':copy.deepcopy(c),'source':str(p.relative_to(ROOT)),'source_digest':digest(p)})
    checks=out['checks']
    def record(name,ok,detail=None):checks.append({'name':name,'pass':bool(ok),'detail':detail})
    record('reviewer correction is exactly five prepare templates / ten null fields',len(changed)==10 and len({x['source'] for x in changed})==5)
    # E1/E2 claims carry execution_seal_commit rather than preregistration_commit.
    known=[]
    for label,a in out['aborted_archives'].items():
        for row in a['selected_metadata']:
            p=ROOT/a['path']/row['path'];obj=json.loads(p.read_text())
            if obj.get('execution_seal_commit') is not None:
                ok=obj['execution_seal_commit']==row['expected_commit']
                record(label+' actual execution_seal_commit '+row['path'],ok,{'value':obj['execution_seal_commit'],'expected':row['expected_commit']})
                known.append(str(p.relative_to(ROOT)))
    record('actual claim seal identities directly observed',len(known)>=3,known)
    drift=[]
    for ap,expected in out['protected_inputs'].items():
        actual=digest(Path(ap))
        if actual!=expected:drift.append({'path':ap,'before':expected,'after':actual})
    record('final protected-input rehash unchanged',not drift,{'count':len(out['protected_inputs']),'drift':drift})
    negative=json.loads((OUT/'whitelist-negative-receipt-01.json').read_text())
    record('additional independent uppercase negative eight checks pass',len(negative['checks'])==8 and all(c['pass'] is True for c in negative['checks']))
    out.update(generated_at=datetime.now().astimezone().isoformat(timespec='seconds'),
               reviewer_assumption_corrections=changed,first_receipt={'path':first.name,**digest(first)},
               first_verifier_source={'path':'independent_verification.py',**digest(OUT/'independent_verification.py')},
               finalizer_source={'path':Path(__file__).name,**digest(Path(__file__))},
               additional_negative={'path':'whitelist-negative-receipt-01.json',**digest(OUT/'whitelist-negative-receipt-01.json')},
               final_input_rehash_at=datetime.now().astimezone().isoformat(timespec='seconds'),live_doc_drift=drift)
    out['check_count']=len(checks);out['passed']=sum(c['pass'] for c in checks);out['failed']=sum(not c['pass'] for c in checks)
    out['differences']=[c for c in checks if not c['pass']]
    out['status']='PASS_WITH_ARCHIVE_DIFFERENCE' if len(out['differences'])==1 and out['differences'][0]['name']=='E2 abort SHA abort-receipt.json' else ('PASS' if not out['differences'] else 'DIFFERENCES')
    create(OUT/'independent-check-02.json',out)
    print(json.dumps({'status':out['status'],'checks':out['check_count'],'passed':out['passed'],'failed':out['failed'],'reviewer_null_corrections':len(changed),'live_doc_drift':drift,'differences':out['differences']},ensure_ascii=False))
    return int(bool(out['failed']))
if __name__=='__main__':raise SystemExit(main())
