#!/usr/bin/env python3
"""Independent receipt comparison + byte/Git binding and archive inventory checks.
No candidate gate verifier is used as the E3 proof. No product/checker or network calls.
"""
import hashlib,json,os,re,shutil,subprocess
from pathlib import Path,PurePosixPath
from datetime import datetime
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
P5='1-评测方案/自动循环L5-2026-10-30';REV='5-评测报告/L5判卷修订-2026-10-30'
D='8b1043d05c5b9dd9b3ae5aa5982cea4e9e852825';E1='7474b84aeaa7290c67ee2288d114953dd6cccadd';E2='02a4cac25f679b0e2359f9de6e2b10c82bd9ea0d';E3='d8366da32694713d4f77c740f935229f9e298df4'
A1='3-表现现场/l5-20261030-cli/aborted-attempts-20261030T0152seal';A2='3-表现现场/中止重封档案E2-20261030T0207'
checks=[];protected={};gitops=[]
def sha_bytes(b):return hashlib.sha256(b).hexdigest()
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return {'sha256':h.hexdigest(),'bytes':p.stat().st_size}
def protect(p):
    p=Path(p);d=digest(p);protected[str(p)]=d;return d
def load(p):protect(p);return json.loads(Path(p).read_text())
def record(name,ok,detail=None):
    checks.append({'name':name,'pass':bool(ok),'detail':detail})
def create(p,obj):
    text=json.dumps(obj,ensure_ascii=False,indent=2)+'\n'
    # Reversible standard JSON escapes only for UUID punctuation; never edit source bytes.
    text2=re.sub(r'(?i)\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b',lambda m:m[0].replace('-',r'\u002d'),text)
    assert json.loads(text2)==obj
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:f.write(text2)
def git(*args,allow_nonzero=False):
    assert args[0] in ('show','rev-parse','cat-file','log') or args[:2]==('merge-base','--is-ancestor')
    env=dict(os.environ,GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL='/dev/null',GIT_TERMINAL_PROMPT='0')
    p=subprocess.run(['/usr/bin/git',*args],cwd=ROOT,env=env,capture_output=True)
    gitops.append({'args':list(args),'returncode':p.returncode,'stdout_sha256':sha_bytes(p.stdout),'stdout_bytes':len(p.stdout),'stderr_sha256':sha_bytes(p.stderr)})
    if not allow_nonzero and p.returncode:raise RuntimeError('read-only Git failed '+repr(args))
    return p

def diffs(a,b,p=''):
    if type(a)!=type(b):return [{'path':p,'archived':a,'reproduced':b}]
    if isinstance(a,dict):
        out=[]
        for k in sorted(set(a)|set(b)):
            if k not in a or k not in b:out.append({'path':p+'/'+k,'archived_present':k in a,'reproduced_present':k in b})
            else:out.extend(diffs(a[k],b[k],p+'/'+k))
        return out
    if isinstance(a,list):
        if len(a)!=len(b):return [{'path':p,'archived_len':len(a),'reproduced_len':len(b)}]
        return [x for i,(v,w) in enumerate(zip(a,b)) for x in diffs(v,w,p+'/'+str(i))]
    return [] if a==b else [{'path':p,'archived':a,'reproduced':b}]

def main():
    snap=load(OUT/'input-snapshot-01.json');pub=Path(snap['public_root'])
    for rel,info in snap['files'].items():protected[str(ROOT/rel)]=info
    reports={}
    configs=[('r4-acceptance',REV+'/gate-v2-acceptance-receipt.json',8),('r4-history',REV+'/gate-v2-history-recompute-receipt.json',4),('r5-mapping',REV+'/cache-mapping-v2/recompute-receipt.json',28)]
    for label,rel,n in configs:
        old=load(ROOT/rel);new=load(OUT/(label+'-reproduced-receipt-02.json'));run=load(OUT/(label+'-run-02.json'))
        record(label+': subprocess exit zero',run['returncode']==0)
        record(label+': no blocked/network/product subprocess operations',run['blocked_operations']==[] and run['model_or_product_or_checker_subprocesses']==0)
        record(label+': exact assertion count',len(new['assertions'])==n)
        for i,(want,got) in enumerate(zip(old['assertions'],new['assertions'])):
            record(label+': assertion '+str(i+1),want==got and got['pass'] is True,{'archived':want,'reproduced':got})
        record(label+': all assertions true',len(new['assertions'])==len(old['assertions']) and all(a['pass'] is True for a in new['assertions']))
        meaningful_old={k:v for k,v in old.items() if k!='generated_at'};meaningful_new={k:v for k,v in new.items() if k!='generated_at'}
        ignored={'generated_at':{'archived':old.get('generated_at'),'reproduced':new.get('generated_at')}}
        if label=='r5-mapping':
            expected_suffix='/3-表现现场/l4-20261029-cache/probes 只读'
            record('r5: scope absolute relocation only',old['scope']==str(ROOT)+expected_suffix and new['scope']==str(pub)+expected_suffix)
            meaningful_new['scope']=meaningful_old['scope'];ignored['scope']='exact source-root to temp-root relocation verified'
            record('r5: exactly eighteen slots',new['slot_count']==18 and len(new['recompute'])==18)
            record('r5: six unit selftests exact and true',new['unit_selftest']==old['unit_selftest'] and len(new['unit_selftest'])==6 and all(x['pass'] is True for x in new['unit_selftest']))
        delta=diffs(meaningful_old,meaningful_new)
        record(label+': entire meaningful JSON exact',not delta,delta)
        reports[label]={'archived':rel,'reproduced':label+'-reproduced-receipt-02.json','allowed_metadata_differences':ignored,'unallowed_differences':delta,'assertion_count':n}
        if label=='r4-history':
            rows=[r for p in new['products'].values() for r in p['rows'].values()]
            ids=[sid for p in new['products'].values() for sid in p['rows']]
            plan=load(ROOT/'1-评测方案/自动循环L4-2026-10-29/plan.json')
            record('r4 history: exact seventeen unique plan IDs',len(ids)==17 and len(set(ids))==17 and set(ids)=={s['slot_id'] for s in plan['product_slots']})
            record('r4 history: formal zero unchanged',sum(r['formal_admission'] is True for r in rows)==0)
            record('r4 history: sole projected delta is bird',len(new['diffs'])==1 and new['diffs'][0]['slot']=='l4-20261029-wb-gateway-bird-ca-schools-15-r1')
    branch=git('rev-parse','--abbrev-ref','HEAD').stdout.decode().strip();record('working branch matches requested',branch=='loop5-2026-10-30',branch)
    commits={n:git('show','-s','--format=%H%n%cI',h).stdout.decode().splitlines() for n,h in (('D',D),('E1',E1),('E2',E2),('E3',E3))}
    for left,right in ((D,E1),(E1,E2),(E2,E3),(E3,'HEAD')):
        record('ancestry '+left[:7]+' -> '+right[:7],git('merge-base','--is-ancestor',left,right,allow_nonzero=True).returncode==0)
    stamps={n:datetime.fromisoformat(v[1]) for n,v in commits.items()}
    record('committer chronology D <= E1 <= E2 <= E3',stamps['D']<=stamps['E1']<=stamps['E2']<=stamps['E3'])
    b=load(ROOT/P5/'runtime-binding.json');m=load(ROOT/P5/'execution-manifest.json')
    record('binding full identities',b['design_commit']==D and b['execution_seal_commit']==E3 and b['preregistration_commit']==E3 and m['design_commit']==D)
    record('binding registered_at exact E3 committer string',b['registered_at']==commits['E3'][1])
    record('binding release bool exact true',b['released_for_model_calls'] is True)
    mb=(ROOT/P5/'execution-manifest.json').read_bytes();sealed_mb=git('show',E3+':'+P5+'/execution-manifest.json').stdout
    record('E3 manifest bytes equal disk and binding hash',mb==sealed_mb and sha_bytes(mb)==b['execution_manifest_sha256'])
    binding_proof={'commits':commits,'manifest_sha256':sha_bytes(mb),'binding_sha256':protect(ROOT/P5/'runtime-binding.json')['sha256'],'manifest_files':[],'external_files':[]}
    for n in ('PREREGISTRATION.md','plan.json','contract.json'):
        rel=P5+'/'+n;disk=(ROOT/rel).read_bytes();db=git('show',D+':'+rel).stdout;eb=git('show',E3+':'+rel).stdout
        record('D/E3/disk byte equality '+n,db==eb==disk)
        if n!='PREREGISTRATION.md':record('binding SHA '+n,sha_bytes(disk)==b[n.split('.')[0]+'_sha256'])
    # Independently enumerate the source membership policy; do NOT call seal.required_files.
    roots=('1-评测方案/工具链/l5-execution','3-表现现场/l5-20261030-cli/codex/tools','3-表现现场/l5-20261030-cli/dsh/tools','3-表现现场/l5-20261030-wb-gateway/runner','3-表现现场/l5-20261030-wb-gateway/driver-snapshot')
    required={P5+'/'+n for n in ('PREREGISTRATION.md','plan.json','contract.json','execution_seal.py','test_execution_seal.py')}
    required.update(('1-评测方案/工具链/runner-schema-v2/validate_runner_meta.py','1-评测方案/工具链/evidence-kit/evidence_line.py','1-评测方案/工具链/evidence-kit/receipt_check.py','3-表现现场/l5-20261030-cli/codex/config/codex-config.toml'))
    for r in (P5,)+roots:
        base=ROOT/r;record('runtime root canonical '+r,base.is_dir() and not base.is_symlink() and base.resolve()==base.absolute())
        for p in sorted(base.rglob('*')):
            if p.is_symlink():record('no runtime symlink '+str(p.relative_to(ROOT)),False);continue
            if '__pycache__' in p.relative_to(base).parts or p.suffix=='.pyc':continue
            if p.is_file() and (r!=P5 or p.suffix in ('.py','.toml','.yaml','.yml') or (p.suffix=='.json' and 'config' in p.name.lower())):required.add(str(p.relative_to(ROOT)))
    record('independent required membership exactly manifest',set(m['files'])==required,{'required':sorted(required),'missing':sorted(required-set(m['files'])),'extra':sorted(set(m['files'])-required)})
    for rel,want in sorted(m['files'].items()):
        p=ROOT/rel;safe=str(PurePosixPath(rel))==rel and not PurePosixPath(rel).is_absolute() and '..' not in PurePosixPath(rel).parts and p.resolve()==p.absolute() and not p.is_symlink() and p.is_file()
        got=protect(p);eb=git('show',E3+':'+rel).stdout
        record('E3 source disk/blob/manifest '+rel,safe and got['sha256']==want==sha_bytes(eb))
        binding_proof['manifest_files'].append({'path':rel,'expected_sha256':want,**got,'E3_blob_sha256':sha_bytes(eb)})
    ext_required={str(Path('/Users/b612-lp')/p) for p in ('.dsh/AGENTS.md','.dsh/profiles/bench-cli/cordis.patch.yml','.dsh/profiles/bench-cli/package.json','bench-workspaces/l5-20261030-cli/codex/_codex-home/config.toml')}
    ext_required.update(('/Applications/WorkBuddy.app/Contents/Info.plist','/Applications/WorkBuddy.app/Contents/Resources/app.asar'))
    for command in ('dsh','codex'):
        target=Path(shutil.which(command,path='/opt/homebrew/bin:/usr/bin:/bin')).resolve();package=target.parent.parent
        ext_required.update((str(target),str((package/'package.json').resolve())))
        if command=='dsh':ext_required.update(str(p.resolve()) for p in (package/'lib').glob('*.js'))
        else:ext_required.add(str((package/'node_modules/@openai/codex-darwin-arm64/vendor/aarch64-apple-darwin/bin/codex').resolve()))
    record('external membership independently exactly seventeen',len(m['external_files'])==17 and set(m['external_files'])==ext_required,{'missing':sorted(ext_required-set(m['external_files'])),'extra':sorted(set(m['external_files'])-ext_required)})
    for ap,want in sorted(m['external_files'].items()):
        p=Path(ap);got=protect(p);ok=p.is_absolute() and p.resolve()==p and not p.is_symlink() and got['sha256']==want
        record('external raw SHA '+ap,ok)
        binding_proof['external_files'].append({'path':ap,'expected_sha256':want,**got,'content_decoded':False})
    aborts={}
    for label,base in (('E1',A1),('E2',A2)):
        root=ROOT/base;rp=root/'abort-receipt.json';doc=load(rp)
        raw=rp.read_bytes();copy=OUT/'abort-receipts-snapshot'/(label+'-abort-receipt.json')
        copy.parent.mkdir(parents=True,exist_ok=True)
        with copy.open('xb') as f:f.write(raw)
        listed=doc['files_sha256'];actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
        expected_keys=set(listed);expected_inventory=actual if 'abort-receipt.json' in listed else actual-{'abort-receipt.json'}
        record(label+' abort exact file inventory',expected_keys==expected_inventory,{'missing_on_disk':sorted(expected_keys-actual),'unlisted_on_disk':sorted(expected_inventory-expected_keys)})
        rows=[]
        for rel,want in sorted(listed.items()):
            p=root/rel;safe=str(PurePosixPath(rel))==rel and not PurePosixPath(rel).is_absolute() and '..' not in PurePosixPath(rel).parts and p.resolve()==p.absolute() and not p.is_symlink() and p.is_file()
            got=protect(p) if safe else None
            ok=bool(safe and got['sha256']==want)
            record(label+' abort SHA '+rel,ok,{'expected_sha256':want,'actual':got})
            rows.append({'path':rel,'expected_sha256':want,'actual':got,'match':ok,'self_reference':rel=='abort-receipt.json'})
        record(label+' archive has no symlink entries',not any(p.is_symlink() for p in root.rglob('*')))
        supplements=[]
        for n in ('abort-receipt-supplement.json','abort-receipt-supplement-2.json'):
            if not (root/n).is_file():continue
            s=load(root/n)
            with (OUT/'abort-receipts-snapshot'/(label+'-'+n)).open('xb') as f:f.write((root/n).read_bytes())
            for name in s.get('added',[]):
                if '=' in name:
                    # Explicit state assertion, not a path. No historical existence claim is inferred.
                    continue
                record(label+' supplement added path exists '+name,(root/name).exists())
            supplements.append({'name':n,'at':s.get('at'),'added':s.get('added'),'snapshot_sha256':sha_bytes((root/n).read_bytes())})
        e=E1 if label=='E1' else E2;stamp=stamps[label]
        abort_time=datetime.fromisoformat(doc['at'])
        record(label+' seal before declared abort',stamp<=abort_time)
        record(label+' declared abort before next seal',abort_time<=stamps['E2' if label=='E1' else 'E3'])
        metadata=[]
        for p in sorted(root.rglob('*.json')):
            if p.name not in ('meta.json','meta.prepare.json','claim.json','notexecuted.json'):continue
            md=load(p);rel=str(p.relative_to(root));fields={k:md[k] for k in ('preregistration_commit','execution_seal_commit','registered_at','started_at','finished_at','prepared_at','claimed_at','at') if k in md}
            expected=E3 if 'ev3-voided-claim' in rel else e
            expected_stamp=commits['E3' if expected==E3 else label][1]
            if 'preregistration_commit' in fields:record(label+' archived binding identity '+rel,fields['preregistration_commit']==expected)
            if 'registered_at' in fields:record(label+' archived registered_at exact committer '+rel,fields['registered_at']==expected_stamp)
            metadata.append({'path':rel,'expected_commit':expected,'fields':fields})
        record(label+' at least one archived registration timestamp observed',any('registered_at' in x['fields'] for x in metadata))
        aborts[label]={'path':base,'receipt_digest':protect(rp),'at':doc['at'],'listed_count':len(listed),'actual_file_count':len(actual),'rows':rows,'supplements':supplements,'selected_metadata':metadata,'disclosure':'Raw files hashed only; no prompts, solutions, keys, scores or session contents emitted. Self-reference is not excused from equality.'}
    record('abort SHA sampling exceeds twenty actual files',sum(len(v['rows']) for v in aborts.values())>=20)
    # All original inputs, copied baseline sources and external raw pins are rehashed.
    drift=[]
    for ap,before in sorted(protected.items()):
        now=digest(Path(ap))
        if now!=before:drift.append({'path':ap,'before':before,'after':now})
    record('all protected inputs unchanged',not drift,{'protected_count':len(protected),'drift':drift})
    result={'generated_at':datetime.now().astimezone().isoformat(timespec='seconds'),'kind':'independent_offline_verification','branch':branch,
            'receipt_comparisons':reports,'binding':binding_proof,'aborted_archives':aborts,
            'checks':checks,'check_count':len(checks),'passed':sum(c['pass'] for c in checks),'failed':sum(not c['pass'] for c in checks),
            'differences':[c for c in checks if not c['pass']],'protected_inputs':protected,'git_read_only_operations':gitops,
            'zero_model_calls':True,'zero_network_calls':True,'formal_reclassification_performed':False,'live_doc_drift':drift}
    create(OUT/'independent-check-01.json',result)
    print(json.dumps({'checks':len(checks),'passed':result['passed'],'failed':result['failed'],'differences':[x['name'] for x in result['differences']],'protected_count':len(protected)},ensure_ascii=False))
    return int(bool(result['failed']))
if __name__=='__main__':raise SystemExit(main())
