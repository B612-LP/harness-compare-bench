"""Combine two fixed public measurement functions on wholly synthetic bytes."""
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_loader
from itertools import product
import json
from pathlib import Path
import sys


SSE=('SSE终态与内容完备分账-2026-11-27/sse.py','6612f50fc10086fef21ce50dbc3aad9db5dd20ab7ce979442ddeb8cf53bdfdb8')
LIFE=('Responses生命周期与同源副本-2026-11-27/lifecycle.py','4e170c0948e28a2bab813b82ca6d758bcb6fc2c22b11deb1a7286ddb548aec08')
EXACT=('精确数字与字符串域隔离-2026-11-27/exact.py','882c121cc0e13b347be264188d2e62ab75b802f3754fafb816052a9f79b6ecb2')
PHYSICAL=('lf','crlf','split_data','double_bom','last_not_dispatched')
STRUCTURE=('full','phase_missing','part_open_missing','seq_gap','seq_float')


def need(ok, msg):
    if not ok:raise ValueError(msg)


def load(repo, pair, name):
    path=repo/'4-打分细则'/pair[0]
    source=path.read_bytes()
    need(sha256(source).hexdigest()==pair[1],'PUBLIC_SOURCE_CHANGED')
    module=module_from_spec(spec_from_loader(name,loader=None))
    sys.modules[name]=module
    exec(compile(source,'fixed_public_measurement.py','exec'),module.__dict__)
    return module


@dataclass(frozen=True)
class Frame:
    label:str
    obj:dict


def fixture(flags, structure, metadata=None):
    a,b,d,p,i,s=flags
    span=lambda k:'ABCD' if k else 'abcd'
    part=lambda t,probe=None:dict(type='output_text',text=t,**({} if probe is None else {'probe_number':probe}))
    item=dict(id='item',type='message',role='assistant',phase='final_answer',status='in_progress',content=[])
    idict=lambda t,probe:dict(item,status='completed',content=[part(t)],**({} if probe is None else {'probe_number':probe}))
    common=dict(id='response',model='synthetic',object='response',created_at=1,error=None,incomplete_details=None)
    response=lambda status,output:dict(common,status=status,output=output)
    x=dict(output_index=0,content_index=0,item_id='item')
    probes=metadata or (None,None)
    raw=[('response.created',{'response':response('in_progress',[])}),
         ('response.in_progress',{'response':response('in_progress',[])}),
         ('response.output_item.added',dict(output_index=0,item=item)),
         ('response.content_part.added',dict(x,part=part(''))),
         ('response.output_text.delta',dict(x,delta='AB' if a else 'ab')),
         ('response.output_text.delta',dict(x,delta='CD' if b else 'cd')),
         ('response.output_text.done',dict(x,text=span(d))),
         ('response.content_part.done',dict(x,part=part(span(p)))),
         ('response.output_item.done',dict(output_index=0,item=idict(span(i),probes[0]))),
         ('response.completed',{'response':response('completed',[idict(span(s),probes[1])])})]
    if structure=='phase_missing':del raw[1]
    if structure=='part_open_missing':del raw[3]
    num=lambda j:j+1 if structure=='seq_gap' and j>=4 else (float(j) if structure=='seq_float' and j==4 else j)
    return [Frame(label,dict(data,sequence_number=num(j),type=label)) for j,(label,data) in enumerate(raw)]


def render(frames, physical):
    eol=b'\r\n' if physical=='crlf' else b'\n';body=bytearray()
    for f in frames:
        data=json.dumps(f.obj,ensure_ascii=False,separators=(',',':')).encode('utf-8')
        if physical=='split_data':data=data[:1]+eol+b'data: '+data[1:]
        body.extend(b'event: '+f.label.encode('ascii')+eol+b'data: '+data+eol+eol)
    if physical=='last_not_dispatched':del body[-1:]
    if physical=='double_bom':body=b'\xef\xbb\xbf'*2+body
    return bytes(body)


def load_rows(sse, raw):
    rows=[]
    for frame in sse.split_capture(raw).frames:
        need(len(frame.types)==1,'SYNTHETIC_EVENT')
        rows.append(Frame(frame.types[0].decode('ascii'),json.loads(frame.data)))
    return rows


def measure(sse, life, raw, baseline):
    p=sse.projection(raw,'codex')
    sha='1' if sha256(raw).digest()==baseline else '0'
    if not p['closed']:return '0UUU'+sha,tuple(sorted({e['code'] for e in p['issues']})),(),()
    rows=load_rows(sse,raw)
    need(len(rows)==len(p['payloads']),'SYNTHETIC_PAYLOAD_COVERAGE')
    seq=all(type(r.obj['sequence_number']) is int and r.obj['sequence_number']==j for j,r in enumerate(rows))
    m,e=life.inspect(rows)
    return '1'+('1' if seq else '0')+('0' if m else '1')+('0' if e else '1')+sha,(),tuple(m),tuple(e)


def expected(flags, physical, structure):
    first,second,done,part,item,snapshot=flags
    orig=physical=='lf' and structure=='full' and not any(flags)
    if physical in ('double_bom','last_not_dispatched'):return '0UUU'+str(int(orig))
    q=structure not in ('seq_gap','seq_float')
    m=structure!='phase_missing' and first==second==done and item==snapshot
    e=structure!='part_open_missing' and done==part==item
    return '1'+''.join(str(int(x)) for x in (q,m,e,orig))


def run(repo):
    sse=load(repo,SSE,'public_physical');life=load(repo,LIFE,'public_lifecycle');exact=load(repo,EXACT,'public_exact')
    zero=(0,)*6
    baseline_raw=render(fixture(zero,'full'),'lf');baseline=sha256(baseline_raw).digest()
    rows=[];counts=Counter();raws=set();complete=[];only={};typed={}
    leave_one={a:0 for a in 'QME'}
    for flags,physical,structure in product(product((0,1),repeat=6),PHYSICAL,STRUCTURE):
        raw=render(fixture(flags,structure),physical)
        key=[''.join(str(f) for f in flags),physical,structure]
        fp=sha256(raw).digest();need(fp not in raws,'GRID_ALIAS');raws.add(fp)
        gates,t,m,e=measure(sse,life,raw,baseline)
        need(gates==expected(flags,physical,structure),'GRID_PREDICTION')
        counts[gates]+=1;rows.append([key,gates,t,m,e])
        if gates[:4]=='1111':complete.append(key)
        if gates.startswith('0'):
            only.setdefault('T',key);continue
        for j,a in enumerate('QME',1):
            if gates[j]=='0' and all(gates[k]=='1' for k in range(1,4) if j!=k):
                leave_one[a]+=1;only.setdefault(a,key)
    need(len(rows)==len(raws)==1600 and len(only)==4,'GRID_TOTAL')
    need(len(complete)==6 and counts['11111']==1 and counts['11110']==5,'BLIND_TOTAL')
    need(leave_one=={'Q':12,'M':90,'E':42},'LEAVE_ONE_TOTAL')
    for label,x in [('same_integer',(1,1)),('equal_width_bool_float',(True,1.0)),('different_number',(1,2))]:
        # Use 1.00 rather than 1.0 for a length-matched ordinary-equality witness.
        raw=render(fixture(zero,'full',x),'lf').replace(b'"probe_number":1.0}',b'"probe_number":1.00}')
        parsed=load_rows(sse,raw);a,b=parsed[-2].obj['item'],parsed[-1].obj['response']['output'][0]
        canonical=exact.canonicalize if hasattr(exact,'canonicalize') else None
        need(canonical is not None,'EXACT_API')
        enc=lambda obj:json.dumps(obj,sort_keys=True,separators=(',',':')).encode('ascii')
        encoded=lambda obj:canonical(enc(obj))
        pair=[encoded(a),encoded(b)]
        same_canon=pair[0]==pair[1]
        gates,t,m,e=measure(sse,life,raw,baseline)
        typed[label]={'ordinary':a==b,'strict':same_canon,'gates':gates}
    need(typed=={'same_integer':{'ordinary':True,'strict':True,'gates':'11110'},
                'equal_width_bool_float':{'ordinary':True,'strict':False,'gates':'11110'},
                'different_number':{'ordinary':False,'strict':False,'gates':'11010'}},'TYPED_CONTROL')
    for spec in (SSE,LIFE,EXACT):
        need(sha256((repo/'4-打分细则'/spec[0]).read_bytes()).hexdigest()==spec[1],'PUBLIC_SOURCE_CHANGED_AFTER')
    return {'matrix':rows,'summary':dict(counts),'unique_original':counts['11111'],
            'joint_valid':complete,'first_witness':only,'increased_admission_if_omitted':leave_one,
            'physical_reject_lower_unknown':sum(v for k,v in counts.items() if k[0]=='0'),'type_control':typed}


if __name__=='__main__':
    try:
        need(len(sys.argv)==1,'USAGE')
        result=run(Path(__file__).resolve().parents[2])
    except Exception:
        print('REJECT: fixed synthetic matrix',file=sys.stderr)
        raise SystemExit(1) from None
    print(json.dumps(result,sort_keys=True,separators=(',',':')))
