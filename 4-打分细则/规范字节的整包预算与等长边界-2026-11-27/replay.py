"""Replay only fixed public positions and synthetic objects. No archived execution."""
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_loader
import json
from pathlib import Path
import sys


ROOT=Path(__file__).resolve().parents[2]
MEASUREMENT='4-打分细则/精确数字与字符串域隔离-2026-11-27/exact.py'
EXACT='882c121cc0e13b347be264188d2e62ab75b802f3754fafb816052a9f79b6ecb2'
SOURCES=(
 ('dsh/stdout-r2.jsonl',78,'105717eaca150dd36eab255bff74945509a3488837bb1b8df5e143aa337e2508'),
 ('codex/stdout-r2.jsonl',84,'d85c7d724ed4fed1e839aa6fc534cc025cca2288bdc08987d88c73643467be10'),
 ('doubao/trajectory-38455827958268674-copy.jsonl',73,'8fc1d0e0ed5a2688b28a86e47a33e08975866a9f26e11ce79eb07c5d44d8d5a7'),
)


def require(ok):
    if not ok:raise ValueError('fixed public control')


def read(path,digest):
    b=path.read_bytes();require(sha256(b).hexdigest()==digest);return b


def preserve_order(v,exact):
    if type(v) is dict:
        return '{'+','.join(exact.string(k)+':'+preserve_order(e,exact) for k,e in v.items())+'}'
    if type(v) is list:
        return '['+','.join(preserve_order(e,exact) for e in v)+']'
    return exact.canonical(v)


def run():
    src=ROOT/MEASUREMENT
    mod=module_from_spec(spec_from_loader('fixed_public_exact',loader=None));sys.modules[mod.__name__]=mod
    # Only trusted, pinned measurement code is compiled. JSONL entries stay data.
    exec(compile(read(src,EXACT),'fixed_exact.py','exec'),mod.__dict__)
    rows=octets=changed=0
    inputs={src:EXACT}
    for rel,count,h in SOURCES:
        p=ROOT/'3-表现现场/r20261125-five-lcb'/rel;inputs[p]=h
        b=read(p,h);lst=b.split(b'\n');require(len(lst)==count+1 and lst[-1]==b'' and all(lst[:-1]))
        for raw in lst[:-1]:
            canon=mod.canonicalize(raw)
            tree=json.loads(raw.decode('utf-8','strict'),parse_int=mod.number,parse_float=mod.number,
                            parse_constant=mod.nonfinite,object_pairs_hook=mod.unique)
            ordered=preserve_order(tree,mod).encode('utf-8')
            require(ordered==raw and len(canon)==len(raw))
            rows+=1;octets+=len(raw);changed+=int(canon!=raw)
    require((rows,octets,changed)==(235,302540,234))
    wide=[]
    for j in (1,10,100,8192):
        raw=b'{"a":['+b','.join([b'1.1']*j)+b']}'
        c=mod.canonicalize(raw)
        require(len(raw)==4*j+7 and len(c)==6*j+7 and 2*len(c)<=3*len(raw))
        wide.append([j,len(raw),len(c)])
    cancel=b'{"a":1.1  }';out=mod.canonicalize(cancel)
    require(out==b'{"a":11e-1}' and len(cancel)==len(out) and cancel!=out)
    a,b=rb'{"\u0061":1.1}',b'{"a":1.1     }'
    require(a!=b and len(a)==len(b) and mod.canonicalize(a)==mod.canonicalize(b)==out)
    for p,h in inputs.items():read(p,h)
    return {'public_rows':rows,'raw_and_canonical_bytes':octets,'changed_only_by_order':changed,
            'unchanged':rows-changed,'synthetic_wide':[{'items':j,'in':n,'out':m} for j,n,m in wide],
            'two_equal_length_mechanism_controls':True}


if __name__=='__main__':
    try:r=run()
    except Exception:
        print('REJECT: public source, coverage or budget check failed',file=sys.stderr)
        raise SystemExit(1) from None
    print(json.dumps(r,sort_keys=True))