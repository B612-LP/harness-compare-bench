#!/usr/bin/env python3
"""Independent byte/hash/commit checks. No import of candidate seal or gate validator."""
import hashlib,json,os,re,subprocess
from pathlib import Path,PurePosixPath
from datetime import datetime
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
P6='1-评测方案/自动循环L6-2026-10-30';P5='1-评测方案/自动循环L5-2026-10-30'
D='1211b5b787049b9367af8b85aa99ab15d9d7104c';E=['1c27a6b6d15986868d3cc73c6420fbf8708a45bb','46d64eefcbe09515ee6a357873092c8f10c50625','aae5edacf959b93d833d9ef283085e891ab4361f'];BC=['bfa9388d76b825cd4b32af73ccbc957759dcefdc','936615dd59499dd13d02b512da0cdf0e4f87295f','c1d897015a355c1bbd8fdc181cf8649a0843374b']
checks=[];ops=[];protected={}
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return {'sha256':h.hexdigest(),'bytes':p.stat().st_size}
def protect(p):
    x=digest(p);protected[str(p)]=x;return x
def sha(b):return hashlib.sha256(b).hexdigest()
def c(n,v,d=None):checks.append({'name':n,'pass':bool(v),'detail':d})
def load(p):protect(p);return json.loads(p.read_text())
def git(*args):
    assert args[0] in ('show','rev-parse','log','cat-file') or args[:2]==('merge-base','--is-ancestor')
    p=subprocess.run(['/usr/bin/git',*args],cwd=ROOT,capture_output=True,env=dict(os.environ,GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL='/dev/null',GIT_TERMINAL_PROMPT='0'))
    ops.append({'args':list(args),'returncode':p.returncode,'stdout_sha256':sha(p.stdout),'stdout_bytes':len(p.stdout)})
    if p.returncode and args[0]!='merge-base':raise RuntimeError('Git read failed')
    return p

def main():
    snap=load(OUT/'snapshot-01.json')
    for rel,x in snap['files'].items():protected[str(ROOT/rel)]=x
    branch=git('rev-parse','--abbrev-ref','HEAD').stdout.decode().strip();c('branch L6',branch=='loop6-2026-10-30')
    contract=load(ROOT/P6/'contract.json');old=load(ROOT/P5/'contract.json');manifest=load(ROOT/P6/'execution-manifest.json');binding=load(ROOT/P6/'runtime-binding.json')
    c('E3 manifest SHA prefix and binding exact',sha((ROOT/P6/'execution-manifest.json').read_bytes())==binding['execution_manifest_sha256'] and binding['execution_manifest_sha256'].startswith('4e26e512'))
    c('E3 design/prereg/seal exact',binding['design_commit']==D==manifest['design_commit'] and binding['execution_seal_commit']==binding['preregistration_commit']==E[2])
    c('E3 manifest blob equals disk',git('show',E[2]+':'+P6+'/execution-manifest.json').stdout==(ROOT/P6/'execution-manifest.json').read_bytes())
    for n in ('PREREGISTRATION.md','plan.json','contract.json'):
        rel=P6+'/'+n;db=git('show',D+':'+rel).stdout;disk=(ROOT/rel).read_bytes()
        c('D3 design disk exact '+n,db==disk)
        for i,commit in enumerate(E):c('D3/E'+str(i+1)+' design exact '+n,git('show',commit+':'+rel).stdout==db)
        if n!='PREREGISTRATION.md':c('binding hash '+n,binding[n.split('.')[0]+'_sha256']==sha(disk))
    for left,right in zip([D]+E,E+['HEAD']):c('Git ancestry '+left[:7]+' -> '+right[:7],git('merge-base','--is-ancestor',left,right).returncode==0)
    # Independent required source enumeration (do not call seal.required_files).
    required={P6+'/'+n for n in ('PREREGISTRATION.md','plan.json','contract.json','execution_seal.py','test_execution_seal.py')}
    required.add('1-评测方案/工具链/runner-schema-v2/validate_runner_meta.py')
    roots=('1-评测方案/工具链/l5-execution','1-评测方案/工具链/evidence-kit','3-表现现场/l6-20261030-wb-gateway/runner','3-表现现场/l6-20261030-wb-gateway/driver-snapshot')
    for rel in (P6,)+roots:
        base=ROOT/rel;c('source root canonical '+rel,base.is_dir() and not base.is_symlink() and base.resolve()==base.absolute())
        for p in sorted(base.rglob('*')):
            if p.is_symlink():c('source symlink forbidden '+str(p.relative_to(ROOT)),False);continue
            if '__pycache__' in p.relative_to(base).parts or p.suffix=='.pyc':continue
            if p.is_file() and (rel!=P6 or p.suffix in ('.py','.toml','.yaml','.yml') or (p.suffix=='.json' and 'config' in p.name.lower())):required.add(str(p.relative_to(ROOT)))
    c('manifest exact independently enumerated28',len(manifest['files'])==len(required)==28 and set(manifest['files'])==required,{'missing':sorted(required-set(manifest['files'])),'extra':sorted(set(manifest['files'])-required)})
    source_rows=[]
    for rel,want in sorted(manifest['files'].items()):
        p=ROOT/rel;safe=not PurePosixPath(rel).is_absolute() and '..' not in PurePosixPath(rel).parts and p.resolve()==p.absolute() and not p.is_symlink() and p.is_file();got=protect(p);blob=git('show',E[2]+':'+rel).stdout
        c('E3 disk SHA '+rel,safe and got['sha256']==want)
        c('E3 blob SHA '+rel,sha(blob)==want)
        source_rows.append({'path':rel,**got,'expected':want,'E3_blob_sha256':sha(blob)})
    external_set={'/Applications/WorkBuddy.app/Contents/Info.plist','/Applications/WorkBuddy.app/Contents/Resources/app.asar','/Users/b612-lp/.dsh/AGENTS.md','/Users/b612-lp/.dsh/profiles/bench-cli/cordis.patch.yml','/Users/b612-lp/.dsh/profiles/bench-cli/package.json'}
    c('external exactly5 identities',set(manifest['external_files'])==external_set)
    external=[]
    for ap,want in sorted(manifest['external_files'].items()):
        p=Path(ap);got=protect(p);c('external raw SHA '+ap,not p.is_symlink() and p.resolve()==p and got['sha256']==want)
        external.append({'path':ap,**got,'expected':want,'content_decoded':False})
    # Independently reconstruct the freeze snapshot algorithm and raw inherit fragments.
    inherit={};snapshot_rows={};t6=(ROOT/P6/'contract.json').read_text();t5=(ROOT/P5/'contract.json').read_text()
    def fragment(text,key):
        m=re.search(r'^    '+re.escape(json.dumps(key))+r':\s*',text,re.M)
        assert m
        _,end=json.JSONDecoder().raw_decode(text[m.end():]);return text[m.end():m.end()+end].encode()
    for case,pins in contract['case_snapshots'].items():
        base=ROOT/'2-用例'/case
        paths=[base/n for n in ('instruction.md','spec.md','case.json','truth.json','checker.py','trusted_runner.py') if (base/n).is_file()]
        paths+=sorted(p for p in (base/'inputs').rglob('*') if p.is_file())
        actual={str(p.relative_to(base)):protect(p)['sha256'] for p in paths}
        c('case complete file membership '+case,set(actual)==set(pins['files']))
        for rel,want in pins['files'].items():c('case raw pin '+case+'/'+rel,actual.get(rel)==want)
        compact=json.dumps(actual,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode();version=sha(compact)
        c('case manifest digest '+case,version==pins['manifest_sha256'])
        c('case version digest '+case,pins['case_version']==case+'@sha256:'+version)
        for field in ('checker.py','truth.json','instruction.md'):c('case redundant mapping '+case+'/'+field,actual[field]==pins[field])
        c('top checker mapping '+case,actual['checker.py']==contract['checker_sha256'][case])
        snapshot_rows[case]={'actual_files':actual,'manifest_sha256':version}
        if case!='bird-ca-schools-15':
            f6,f5=fragment(t6,case),fragment(t5,case)
            c('four-case raw contract subtree exact '+case,f6==f5)
            c('four-case decoded snapshot exact '+case,pins==old['case_snapshots'][case])
            inherit[case]={'L5_fragment_sha256':sha(f5),'L6_fragment_sha256':sha(f6),'bytes':len(f6)}
        else:
            c('bird full checker SHA expected ffa7389a',actual['checker.py']=='ffa7389adef32779686bbe56aef7d711db1d8d1c191ff5dd389310e6c01d1910')
            changed={k for k in actual if actual[k]!=old['case_snapshots'][case]['files'].get(k)}
            c('bird only checker/spec file delta',changed=={'checker.py','spec.md'},sorted(changed))
            for rel,want in old['case_snapshots'][case]['files'].items():
                if rel not in ('checker.py','spec.md'):c('bird retained raw L5 '+rel,actual[rel]==want)
    # Inspect retired seals entirely through immutable Git blobs, never compare old to new disk.
    retired=[];stamps=[]
    for i,(seal,bc) in enumerate(zip(E,BC),1):
        time=git('show','-s','--format=%cI',seal).stdout.decode().strip();stamps.append(datetime.fromisoformat(time))
        bb=git('show',bc+':'+P6+'/runtime-binding.json').stdout;b=json.loads(bb)
        mm=git('show',seal+':'+P6+'/execution-manifest.json').stdout;m=json.loads(mm)
        c('E'+str(i)+' archived binding seal exact',b['execution_seal_commit']==b['preregistration_commit']==seal)
        c('E'+str(i)+' archived registered_at exact git',b['registered_at']==time)
        c('E'+str(i)+' archived manifest binding SHA',sha(mm)==b['execution_manifest_sha256'])
        c('E'+str(i)+' design fixed D3',b['design_commit']==m['design_commit']==D)
        c('E'+str(i)+' known external count',len(m['external_files'])==(5 if i==3 else 3))
        for rel,want in m['files'].items():c('E'+str(i)+' historical blob manifest '+rel,sha(git('show',seal+':'+rel).stdout)==want)
        c('seal ancestor of binding '+str(i),git('merge-base','--is-ancestor',seal,bc).returncode==0)
        # Save exact historical contract/seal records to NEW audit outputs, append-only.
        dest=OUT/('E'+str(i)+'-git-binding.json')
        with dest.open('xb') as f:f.write(bb)
        dest=OUT/('E'+str(i)+'-git-manifest.json')
        with dest.open('xb') as f:f.write(mm)
        retired.append({'seal':seal,'binding_commit':bc,'registered_at':time,'manifest_sha256':sha(mm),'manifest_files':len(m['files']),'external_files':len(m['external_files']),'recorded_at_git':True})
    c('E1<E2<E3 monotonic committer sequence',stamps[0]<stamps[1]<stamps[2])
    c('E3 registered_at requested exact',binding['registered_at']=='2026-10-30T12:23:46+08:00' and binding['registered_at']==retired[2]['registered_at'])
    note=(ROOT/P6/'seal-supersession-E1-20261030T1153.md').read_text()
    c('supersession note contains E1/E2/E3 retired reasons','1c27a6b' in note and '46d64ee' in note and 'E3' in note and 'plan_dir' in note)
    # Immutable E1 adapter has no plan_dir override; E3 adapter does (byte hashes, not execution).
    adapter='3-表现现场/l6-20261030-wb-gateway/runner/verify_execution.py'
    e1ad=git('show',E[0]+':'+adapter).stdout;e2ad=git('show',E[1]+':'+adapter).stdout;e3ad=git('show',E[2]+':'+adapter).stdout
    c('E1/E2 adapter identical before E3 fix',e1ad==e2ad)
    c('E3 adapter explicit plan_dir fix',b'plan_dir=PLAN_DIR' in e3ad and b'plan_dir=PLAN_DIR' not in e2ad)
    runner='3-表现现场/l6-20261030-wb-gateway/runner/l5_wb_runner.py'
    e1r=git('show',E[0]+':'+runner).stdout;e2r=git('show',E[1]+':'+runner).stdout;e3r=git('show',E[2]+':'+runner).stdout
    c('runner E1/E2 adaptation recorded',e1r!=e2r)
    c('runner E2/E3 unchanged',e2r==e3r)
    # Rehash snapshot/protected originals after executions, one assertion per protected input.
    drift=[]
    for ap,before in sorted(protected.items()):
        after=digest(Path(ap));ok=before==after;c('input unchanged '+ap,ok)
        if not ok:drift.append({'path':ap,'before':before,'after':after})
    result={'at':datetime.now().astimezone().isoformat(timespec='seconds'),'checks':checks,'counts':{'total':len(checks),'passed':sum(c['pass'] for c in checks),'failed':sum(not c['pass'] for c in checks)},'binding':binding,'manifest_sources':source_rows,'external_pins':external,'case_snapshots':snapshot_rows,'four_case_raw_byte_inheritance':inherit,'retired_and_current_git_seals':retired,'protected_inputs':protected,'git_operations':ops,'retired_zero_model_claim_scope':'note/producer reports claim pre-claim refusal; this audit independently verifies Git history, source differences and recorded refusal, not historical absence of all remote side effects','zero_model_calls':True,'zero_network_calls':True,'live_doc_drift':drift}
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n';text2=re.sub(r'(?i)\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b',lambda m:m[0].replace('-',r'\u002d'),text);assert json.loads(text2)==result
    with (OUT/'binding-check-01.json').open('x',encoding='utf-8') as f:f.write(text2)
    print(json.dumps({'counts':result['counts'],'drift':drift,'failures':[c['name'] for c in checks if not c['pass']]},ensure_ascii=False))
    return int(bool(result['counts']['failed']))
if __name__=='__main__':raise SystemExit(main())
