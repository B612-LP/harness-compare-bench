"""Public finite recheck: 52 fixed + 400 constructed + 235 original JSONL rows.
Only reviewed measurement code is imported. Archived solutions/commands/checkers
are data, never executed. Node output is temporary and requires exact ID coverage.
Private 1569-payload reuse and independent 151-case audit are NOT reproduced here.
"""
from pathlib import Path
import collections
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import exact
from cases import fixtures

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PINS={'exact.py':'882c121cc0e13b347be264188d2e62ab75b802f3754fafb816052a9f79b6ecb2',
      'exact.mjs':'9573bf6ed18f54f9adc3a0dde6484e092519a5e4295cbacdf2cce9d261218225',
      'cases.py':'37ebea71ff5b5e93fb963b15c9a52a2a6ef244f46a91a06a3b96df2e61e2ac49'}
SOURCES=[('dsh','stdout-r2.jsonl',78,'105717eaca150dd36eab255bff74945509a3488837bb1b8df5e143aa337e2508'),
 ('codex','stdout-r2.jsonl',84,'d85c7d724ed4fed1e839aa6fc534cc025cca2288bdc08987d88c73643467be10'),
 ('doubao','trajectory-38455827958268674-copy.jsonl',73,'8fc1d0e0ed5a2688b28a86e47a33e08975866a9f26e11ce79eb07c5d44d8d5a7')]


def digest(data):return hashlib.sha256(data).hexdigest()


def coverage(rows,records):
    ids=[r['id'] for r in rows];got=[r.get('id') for r in records]
    if not ids or any(type(i) is not str or not i for i in ids) or len(set(ids))!=len(ids):raise ValueError('empty/invalid/duplicate input IDs')
    if any(type(i) is not str or not i for i in got):raise ValueError('invalid output IDs')
    if len(got)!=len(set(got)) or set(got)!=set(ids):raise ValueError('missing/extra/duplicate output IDs')
    for r in records:
        if r.get('verdict') not in ('accept','reject'):raise ValueError('invalid output verdict')
        if r['verdict']=='accept' and type(r.get('canonical')) is not str:raise ValueError('missing canonical output')
    return {r['id']:r for r in records}


def measure(raw,action):
    try:
        value=action(raw)
        return {'verdict':'accept','canonical':value.decode('utf-8') if type(value) is bytes else value}
    except (ValueError,TypeError,UnicodeError,RecursionError):
        return {'verdict':'reject'}


def load_prior():
    p=ROOT/'4-打分细则/数字口径定版候选-2026-11-23/number_profile_public.py'
    locked='3a4dfeab0a74f614b388e56391b311b324419ae13de1d3815cd0aa4dcec4d926'
    if digest(p.read_bytes())!=locked:raise ValueError('prior A source pin mismatch before import')
    spec=importlib.util.spec_from_file_location('prior_sentinel_measurement',p)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module,p,locked


def main():
    pins={}
    for name,want in PINS.items():
        p=HERE/name;actual=digest(p.read_bytes())
        if actual!=want:raise ValueError('candidate/source pin mismatch: '+name)
        pins[p]=actual
    rows,pairs=fixtures()
    groups=collections.Counter(r['group'] for r in rows)
    if groups!={'synthetic':52,'random':400}:raise ValueError('synthetic coverage count')
    for product,name,count,want in SOURCES:
        p=ROOT/'3-表现现场/r20261125-five-lcb'/product/name
        raw=p.read_bytes()
        if digest(raw)!=want:raise ValueError('public source pin mismatch: '+product)
        pins[p]=want
        lines=[line for line in raw.split(b'\n') if line]
        if len(lines)!=count:raise ValueError('public line count: '+product)
        for i,line in enumerate(lines,1):
            rows.append({'id':'public/%s/%03d'%(product,i),'raw':line.decode('utf-8'),'group':'public','expected':'accept'})
    prior,path,hash_before=load_prior();pins[path]=hash_before
    node=shutil.which('node')
    if not node:
        print('INCOMPLETE: node missing; no cross-language pass claimed')
        return 2
    with tempfile.TemporaryDirectory(prefix='exact-number-finite-') as tmp:
        inp=Path(tmp)/'inputs.jsonl';out=Path(tmp)/'outputs.jsonl'
        with inp.open('x',encoding='utf-8') as f:
            for row in rows:f.write(json.dumps({'id':row['id'],'raw':row['raw']},ensure_ascii=False)+'\n')
        proc=subprocess.run([node,str(HERE/'exact.mjs'),str(inp),str(out)],capture_output=True,text=True,timeout=60)
        if proc.returncode:raise ValueError('Node failed, not a finite pass: '+proc.stderr[:500])
        index=coverage(rows,[json.loads(line) for line in out.read_text(encoding='utf-8').split('\n') if line])
    by_id={};totals=collections.defaultdict(collections.Counter);failures=[];old_differences=[]
    for row in rows:
        raw=row['raw'].encode('utf-8');py=measure(raw,exact.canonicalize);js=index[row['id']]
        equal=py['verdict']==js['verdict'] and (py['verdict']=='reject' or py['canonical']==js['canonical'])
        good=equal and py['verdict']==row['expected']
        if 'expected_canonical' in row:good=good and py.get('canonical')==row['expected_canonical']
        if not good:failures.append(row['id'])
        totals[row['group']]['payloads']+=1;totals[row['group']]['cross_language_equal']+=equal
        old=measure(raw,lambda b:prior.canonical_bytes(b,wire='json'))
        if py['verdict']=='accept' and old['verdict']=='accept':
            same=py['canonical']==old['canonical']
            totals[row['group']]['prior_A_both_accept']+=1
            totals[row['group']]['prior_A_bytes_equal']+=same
            if not same and row['group']=='synthetic':old_differences.append(row['id'])
        by_id[row['id']]=py
    eq=pairs+[('synthetic/'+a,'synthetic/'+b) for a,b in [('dec1','exp1'),('dec_a','dec_b'),('unicode_literal','unicode_escaped'),('key_order_a','key_order_b')]]
    neq=[('synthetic/'+a,'synthetic/'+b) for a,b in [('int1','dec1'),('int0','neg_int0'),('dec0','neg_dec0'),('nfc','nfd'),('sentinel_number','int1')]]
    for wanted,pp in ((True,eq),(False,neq)):
        for one,two in pp:
            if (by_id[one].get('canonical')==by_id[two].get('canonical'))!=wanted:failures.append(one+' relation '+two)
    expected_bad=['synthetic/'+s for s in ('sentinel_number','sentinel_true','sentinel_null','sentinel_key','sentinel_nested','sentinel_arbitrary')]
    if set(old_differences)!=set(expected_bad):failures.append('old A collision set changed')
    if totals['public']['prior_A_bytes_equal']!=235:failures.append('real public A/C changed')
    for p,want in pins.items():
        if digest(p.read_bytes())!=want:raise ValueError('source changed during recheck')
    print(json.dumps({'scope':'public finite corpus only; not product grading or private-source recheck',
      'totals':dict(totals),'relations':len(eq)+len(neq),'old_A_synthetic_differences':old_differences,'failures':failures},ensure_ascii=False,indent=2))
    print('FINITE EXPECTATIONS MET; not a frozen or general JSON standard' if not failures else 'FAIL')
    return bool(failures)

if __name__=='__main__':raise SystemExit(main())
