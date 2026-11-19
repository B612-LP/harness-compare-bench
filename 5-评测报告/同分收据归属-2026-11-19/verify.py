"""Fixed public Git blob recomputation; no writes or historical checker execution."""
import collections, copy, math
from pathlib import Path, PurePosixPath
from subprocess import check_output
import hashlib, json, re, sys, os

BASE = 'dd5a12f651527923a412f6727d5d2f9c22457026'
LEDGER = '5-评测报告/证据口径-2026-11-03/source-ledger.public-derived.json'
LEDGER_SHA = '9784e714cd0134cece788fb3d67b080820dcbc0b95be29761123ab623deea420'
BASE_DIR = Path(__file__).resolve().parent
SELECT = {'A':('A_same_model','exercism-py-6',('codex','dsh')),
          'B':('B_native','bird-ca-schools-15',('yuanbao','doubao'))}
B_ROLES={0:'meta',4:'stdout',5:'receipt',8:'native'}

def need(value, label):
    if not value: raise ValueError(label)

def digest(raw): return hashlib.sha256(raw).hexdigest()

def canonical(obj): return json.dumps(obj, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(',',':'))

def dump(obj): return (json.dumps(obj, ensure_ascii=False, sort_keys=True, allow_nan=False, indent=2)+'\n').encode('utf-8')

def parse(raw):
    def unique(items):
        answer={}
        for k,v in items:
            need(k not in answer, 'JSON_DUPLICATE_KEY')
            answer[k]=v
        return answer
    def invalid(_): raise ValueError('JSON_NONFINITE')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=invalid)

def path_ok(name):
    return (type(name) is str and name.startswith(('3-表现现场/','5-评测报告/')) and
            not any(x in name for x in ('\\',':','\n','\x00')) and
            not (set(name.split('/')) & {'','.','..'}) and not PurePosixPath(name).is_absolute())

def git(*args):
    local_only = {**os.environ, 'GIT_OPTIONAL_LOCKS':'0', 'GIT_NO_LAZY_FETCH':'1',
                  'GIT_ALLOW_PROTOCOL':'', 'GIT_NO_REPLACE_OBJECTS':'1'}
    return check_output(['git','-c','core.quotePath=false','--literal-pathspecs',*args],env=local_only,stderr=-1)

def git_blob(name):
    need(path_ok(name),'SOURCE_PATH')
    line=git('ls-tree','-z','--full-tree',BASE,'--',name)
    need(line.count(b'\0')==1 and line.endswith(b'\0') and b'\t' in line,'SOURCE_LEAF')
    attrs, entry=line[:-1].split(b'\t',1)
    mode,typ,oid=attrs.split(b' ')
    need(entry==name.encode() and mode in (b'100644',b'100755') and typ==b'blob' and re.fullmatch(b'[a-f0-9]{40}',oid),'SOURCE_MODE')
    size=int(git('cat-file','-s',oid.decode()).decode())
    need(0<size<=16*1024*1024,'SOURCE_SIZE')
    raw=git('cat-file','blob',oid.decode())
    need(len(raw)==size,'SOURCE_BYTE_SIZE')
    return raw,oid.decode()

def pick(ledger, stratum):
    track,case,products=SELECT[stratum]
    return {p: next(row for row in ledger['all_formal_attempts'] if row['admitted'] is True and
                    (row['track'],row['case'],row['product'])==(track,case,p)) for p in products}

def pointer(shape, ptr):
    need(type(ptr) is str and (ptr=='' or ptr.startswith('/')),'POINTER')
    for p in ptr[1:].split('/') if ptr else ():
        need(not re.search(r'~(?![01])',p),'POINTER_ESCAPE')
        p=p.replace('~1','/').replace('~0','~')
        if type(shape) is list:
            need(re.fullmatch(r'0|[1-9][0-9]*',p) is not None,'POINTER_INDEX')
            shape=shape[int(p)]
        else: shape=shape[p]
    return shape

CORPUS_SHA = '42929718bda224aea5e819a5d2f01fc4d75a067cf2fd613459de6b222c2550e7'
RESULT_SHA = '323b2720210070e1553db47d4f8608b20f13f2bed98a1d38395e55a2f9aa6c74'

ALL_FIELDS={'case','product','run_id'}
COUNTS = ('full','partial','none','contradiction','no_receipt')
OBS = ('correct','n_questions','reward','weighted')
GRADE = ('earned','possible','reward','reported')

def same(a,b): return canonical(a)==canonical(b)

def source_key(ref): return ref['path'],ref['pointer'],ref['sha256']

def check_envelope(receipt, row):
    if not isinstance(receipt,dict): return {'state':'contradiction','matched':[]}
    if 'identity' in receipt and not isinstance(receipt['identity'],dict):
        return {'state':'contradiction','matched':[]}
    keys=set(); bad=False
    expected={'case':row['case'],'case_id':row['case'],'product':row['product'],'run_id':row['run_id']}
    for envelope in (receipt,receipt.get('identity',{})):
        for field, required in expected.items():
            if field not in envelope: continue
            if type(envelope[field]) is not str or envelope[field]!=required: bad=True
            else: keys.add('case' if field=='case_id' else field)
    state='contradiction' if bad else ('full' if keys==ALL_FIELDS else 'partial' if keys else 'none')
    return {'state':state,'matched':sorted(keys)}

def corpus():
    # The reviewed ledger nominates named scope, never cwd files or workspace text.
    expected_records={}; documents={}; observed={}
    def acquire(name, expected, role):
        if name not in expected_records:
            raw, oid=git_blob(name)
            need(digest(raw)==expected,'HISTORICAL_SOURCE_MISMATCH')
            expected_records[name]={'sha256':expected,'git_blob':oid,'bytes':len(raw),'roles':[]}
            documents[name]=parse(raw); observed[name]=expected
        record=expected_records[name]
        need(record['sha256']==expected,'SOURCE_ALIAS_HASH')
        if role not in record['roles']: record['roles'].append(role)
        return documents[name]
    ledger=acquire(LEDGER,LEDGER_SHA,'ledger')
    old_index={x['path']:x['sha256'] for x in ledger['source_manifest'] if x['status']=='present'}
    need(len(ledger['all_formal_attempts'])==30,'SLOT_COUNT')
    for row in ledger['all_formal_attempts']:
        for ref in row['score_source_refs']:
            name=ref['path']; sha=old_index[name]
            need(name.endswith('.json') and ref['status']=='present' and ref['sha256']==sha==ref['expected_sha256'],'SCORE_ANCHOR')
            acquire(name,sha,'score')
    for s in SELECT:
        for p,row in pick(ledger,s).items():
            src=row['source']; event=pointer(acquire(src['path'],old_index[src['path']],s+'_events'),src['pointer'])
            need(event['event_id']==row['event_id'] and event['product']==p,'EVENT_ANCHOR')
            if s=='B':
                for pos,role in B_ROLES.items():
                    ref=event['sources'][pos]; name=ref['path']
                    need(name.endswith('.json') and ref['sha256']==old_index[name],'B_SOURCE_ANCHOR')
                    acquire(name,ref['sha256'],p+'_'+role)
    need(len(observed)==38 and digest(canonical(expected_records).encode('utf-8'))==CORPUS_SHA,'CORPUS_SCOPE')
    return documents, observed

def all_attempts(data, pins):
    ledger=data[LEDGER]; grid=collections.Counter()
    need(len(ledger['all_formal_attempts'])==len({x['event_id'] for x in ledger['all_formal_attempts']})==30,'ATTEMPT_UNITS')
    need(sum(x['admitted'] is True for x in ledger['all_formal_attempts'])==25,'FORMAL_UNITS')
    for row in ledger['all_formal_attempts']:
        refs=row['score_source_refs']; need(type(refs) is list and len(refs)<2,'RECEIPT_CARDINALITY')
        state='no_receipt'; reward='unknown'
        if refs:
            ref=refs[0]; need(ref['sha256']==pins[ref['path']] and ref['pointer']=='/score','SCORE_SOURCE')
            receipt=data[ref['path']]; grade=pointer(receipt,ref['pointer']); need(same(grade,row['score']),'SCORE_VALUE')
            need(type(grade['reward']) is int and grade['reward'] in (0,1),'SCORE_REWARD')
            reward=str(grade['reward']); state=check_envelope(receipt,row)['state']
        else: need(row['score'] is None,'SCORE_ABSENT')
        grid['formal' if row['admitted'] is True else 'rejected',row['track'][0],state,reward]+=1
    return [{'admission':a,'track':t,'envelope':s,'reward':r,'n':n} for (a,t,s,r),n in sorted(grid.items())]

def token(v): return type(v) is str and bool(v) and v==v.strip() and '\x00' not in v

def recorded_native_workspace(native, row):
    if type(native) is not dict: return 'unknown',None
    if row['product']=='yuanbao':
        if native.get('product') not in (None,'yuanbao-expert-web'): return 'contradiction',None
        scoped=native.get('cases')
        if native.get('product') is None or type(scoped) is not dict or row['case'] not in scoped:
            return 'unknown',None
        slot=scoped[row['case']]
        v=slot.get('run_dir') if type(slot) is dict else None
    else:
        if native.get('product') not in (None,'doubao') or native.get('case') not in (None,row['case']): return 'contradiction',None
        if native.get('product') is None or native.get('case') is None: return 'unknown',None
        v=native.get('workspace')
    return ('scoped',v) if token(v) else ('unknown',None)

def compare_workspace(row, receipt, stdout, native):
    nw,s=recorded_native_workspace(native,row)
    if not isinstance(receipt,dict) or not isinstance(stdout,dict): return 'unknown'
    r=receipt.get('workspace'); o=stdout.get('run_dir')
    if nw=='contradiction' or (stdout.get('case') not in (None,row['case'])): return 'contradiction'
    if nw!='scoped' or stdout.get('case') is None or not all(token(i) for i in (r,o)): return 'unknown'
    if len({s,r,o})!=1: return 'contradiction'
    score=receipt.get('score')
    if type(score) is not dict or any(i not in stdout for i in OBS) or any(i not in score for i in GRADE): return 'unknown'
    for obs, near in zip(OBS,GRADE):
        a,b=stdout[obs],score[near]
        if obs=='weighted':
            if type(a) not in (int,float) or type(b) not in (int,float) or not all(math.isfinite(x) for x in (a,b)): return 'unknown'
        elif type(a) is not int or type(b) is not int: return 'unknown'
        if not same(a,b): return 'contradiction'
    return 'recorded_three_way_match'

def bundles(data, pins, stratum):
    sets={}
    for p,row in pick(data[LEDGER],stratum).items():
        src=row['source']; event=pointer(data[src['path']],src['pointer']); r=row['score_source_refs'][0]
        e=event['score']['refs'][0]; leaf=event['sources'][e['source']]; receipt=data[r['path']]
        need(event['product']==p and event['case_id']==row['case'] and event['identity']['value']['run_id']==row['run_id'],'LEDGER_EVENTS')
        need(source_key({**leaf,'pointer':e['pointer']})==source_key(r),'ORIGINAL_ASSIGNMENT')
        need(same(row['score'],event['score']['value']) and same(pointer(receipt,r['pointer']),row['score']),'ORIGINAL_SCORE')
        a={'row':row,'receipt':receipt,'receipt_ref':r}
        if stratum=='B':
            for i,n in B_ROLES.items():
                if n=='receipt': continue
                path=event['sources'][i]['path']; a[n]=data[path]
                need(pins[path]==event['sources'][i]['sha256'],'B_ANCHOR')
            meta=a['meta']
            need(all(meta[k]==row[v] for k,v in [('event_id','event_id'),('run_id','run_id'),('product','product'),('case_id','case')]),'B_META_OWNER')
        sets[p]=a
    return sets

def arm_evidence(stratum, arms):
    results=[]
    for x,y in (SELECT[stratum][2],SELECT[stratum][2][::-1]):
        l,r=arms[x],arms[y]; row=l['row']; base,other=l['receipt'],r['receipt']; ref=l['receipt_ref']; second=r['receipt_ref']
        result={'target':x,'donor':y,'full_grade_equal':same(base['score'],other['score']),
                'donor_arithmetic_same_input':same(row['score'],other['score']),
                'receipt_bytes_digest_equal':ref['sha256']==second['sha256'],
                'reviewed_assignment_match_after_swap':source_key(ref)==source_key(second),
                'baseline_envelope':check_envelope(base,row)['state'],'swapped_envelope':check_envelope(other,row)['state']}
        if stratum=='B':
            result.update({'native_batch_string_equal_to_event_meta':l['native'].get('batch')==l['meta'].get('batch'),
                           'general_meta_workspace_equals_grade_workspace':l['meta'].get('workspace')==base.get('workspace'),
                           'baseline_workspace_join':compare_workspace(row,base,l['stdout'],l['native']),
                           'swapped_receipt_with_both_other_targets_fixed':compare_workspace(row,other,l['stdout'],l['native']),
                           'swapped_receipt_and_stdout_native_fixed':compare_workspace(row,other,r['stdout'],l['native']),
                           'stdout_summary_all_keys_equal':all(same(l['stdout'][a],base['score'][b]) for a,b in zip(OBS,GRADE))})
        results.append(result)
    return results

def controls(b_arms):
    y=b_arms['yuanbao']; d=b_arms['doubao']; row=y['row']; native=y['native']; receipt=y['receipt']; stdout=y['stdout']
    old=receipt['workspace']; base=PurePosixPath(old).name
    alias=copy.deepcopy(receipt); alias['workspace']='synthetic-parent/'+base
    absent=copy.deepcopy(receipt); del absent['workspace']
    wrong_native=copy.deepcopy(native); wrong_native['product']='doubao'
    no_site=copy.deepcopy(native); del no_site['cases'][row['case']]
    other_case=copy.deepcopy(stdout); other_case['case']='synthetic-other-case'
    bool_reward=copy.deepcopy(stdout); bool_reward['reward']=True
    copied=copy.deepcopy(receipt)
    coherent=copy.deepcopy(native); coherent['cases'][row['case']]['run_dir']=d['receipt']['workspace']
    out={'same_basename_not_same_workspace':compare_workspace(row,alias,stdout,native),
         'missing_receipt_workspace':compare_workspace(row,absent,stdout,native),
         'wrong_native_product':compare_workspace(row,receipt,stdout,wrong_native),
         'missing_yuanbao_case':compare_workspace(row,receipt,stdout,no_site),
         'wrong_stdout_case':compare_workspace(row,receipt,other_case,native),
         'bool_reward_no_integer':compare_workspace(row,receipt,bool_reward,native),
         'same_value_copy_has_no_new_attachment':same(copied['score'],receipt['score']),
         'coherent_untrusted_all_sides_matches_strings_only':compare_workspace(row,d['receipt'],d['stdout'],coherent),
         'coherent_untrusted_changed_native_pinned_source':not same(coherent,native)}
    need(out=={'same_basename_not_same_workspace':'contradiction','missing_receipt_workspace':'unknown',
      'wrong_native_product':'contradiction','missing_yuanbao_case':'unknown','wrong_stdout_case':'contradiction',
      'bool_reward_no_integer':'unknown','same_value_copy_has_no_new_attachment':True,
      'coherent_untrusted_all_sides_matches_strings_only':'recorded_three_way_match',
      'coherent_untrusted_changed_native_pinned_source':True},'CONTROL_JUDGMENT')
    return out

def build():
    data,pins=corpus(); a=bundles(data,pins,'A'); b=bundles(data,pins,'B');
    ar,br=arm_evidence('A',a),arm_evidence('B',b)
    need(all(x['baseline_envelope']=='full' and x['swapped_envelope']=='contradiction' and x['full_grade_equal'] for x in ar),'A_TRANSFER')
    need(all(x['baseline_envelope']==x['swapped_envelope']=='none' and x['full_grade_equal'] and x['baseline_workspace_join']=='recorded_three_way_match' and
             x['swapped_receipt_with_both_other_targets_fixed']==x['swapped_receipt_and_stdout_native_fixed']=='contradiction' and not x['reviewed_assignment_match_after_swap'] for x in br),'B_TRANSFER')
    return {'kind':'receipt_attachment_bounded_projection_v1','source_blobs':len(pins),'formal_and_rejected_strata':all_attempts(data,pins),
            'fixed_A_transfer':ar,'fixed_B_transfer':br,'controls':controls(b),'unknown_runtime_custody':True,'historical_change':False}

if __name__=='__main__':
    try:
        expect=(BASE_DIR/'evidence.json').read_bytes()
        need(digest(expect)==RESULT_SHA,'EVIDENCE_CUSTODY')
        observed=dump(build())
        need(observed==expect,'PROJECTION_DIFFERS')
        sys.stdout.buffer.write(observed)
    except Exception as exc:
        detail=exc.args[0] if type(exc) is ValueError and exc.args and type(exc.args[0]) is str and exc.args[0].replace('_','').isupper() else ''
        print('projection failure: '+type(exc).__name__+(' '+detail if detail else ''),file=sys.stderr)
        raise SystemExit(2)
