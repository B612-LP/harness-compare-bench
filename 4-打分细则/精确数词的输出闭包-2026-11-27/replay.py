"""Public synthetic two-pass check of the unchanged exact-number candidates."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile

PREVIOUS = Path(__file__).resolve().parent.parent / '精确数字与字符串域隔离-2026-11-27'
PINS = {'exact.py':'882c121cc0e13b347be264188d2e62ab75b802f3754fafb816052a9f79b6ecb2',
        'exact.mjs':'9573bf6ed18f54f9adc3a0dde6484e092519a5e4295cbacdf2cce9d261218225'}


def require(ok, why):
    if not ok:
        raise ValueError(why)


def read(name):
    raw=(PREVIOUS/name).read_bytes()
    require(hashlib.sha256(raw).hexdigest()==PINS[name], 'changed candidate: '+name)
    return raw


def module(raw):
    spec=importlib.util.spec_from_loader('pinned_replay_exact', loader=None)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    exec(compile(raw, str(PREVIOUS/'exact.py'), 'exec'), mod.__dict__)
    return mod


def in_obj(token):
    return '{"n":'+token+'}'


def as_node(binary, cases, target, phase):
    a,b=[target/(phase+k+'.jsonl') for k in ('-in','-out')]
    with a.open('x', encoding='utf-8', newline='\n') as f:
        for i,value in cases.items():
            f.write(json.dumps({'id':i,'raw':value})+'\n')
    subprocess.run([binary, str(PREVIOUS/'exact.mjs'),str(a),str(b)],timeout=60,check=True)
    records=[json.loads(line) for line in b.read_bytes().split(b'\n') if line]
    data={row['id']:row for row in records}
    require(len(data)==len(records)==len(cases)>0 and data.keys()==cases.keys(), 'node ID coverage')
    return {i:(row['verdict'], row['canonical'] if row['verdict']=='accept' else row['reason'].lower()) for i,row in data.items()}


def main():
    binary=shutil.which('node')
    if binary is None:
        print('INCOMPLETE: Node not found')
        return 2
    exact=module(read('exact.py'));read('exact.mjs')
    def py(text):
        try:
            return ('accept',exact.canonicalize(text).decode('utf-8'))
        except exact.Reject as err:
            return ('reject',str(err))
    # Inputs and canonical token expected bytes are specified separately.
    cases={
      'safe-edge':('1.'+'1'*1017,'1'*1018+'e-1017'),
      'first-loss':('1.'+'1'*1018,'1'*1019+'e-1018'),
      'old-max-pos':('1.'+'1'*1022,'1'*1023+'e-1022'),
      'old-max-neg':('-1.'+'1'*1021,'-'+'1'*1022+'e-1021'),
      'long-int':('1'*1024,'1'*1024),
      'equal-form-at-ingress':('1'*1023+'e-1022',None),
    }
    shapes={k:in_obj(v[0]) for k,v in cases.items()}
    first={i:py(text) for i,text in shapes.items()}
    second_inputs={i:text for i,(status,text) in first.items() if status=='accept'}
    second={i:py(text) for i,text in second_inputs.items()}
    with tempfile.TemporaryDirectory(prefix='number-replay-') as t:
        path=Path(t)
        require(as_node(binary,shapes,path,'first')==first,'first-pass equality')
        require(as_node(binary,second_inputs,path,'second')==second,'second-pass equality')
    out=[]
    for name,(raw,expected) in cases.items():
        if expected is None:
            require(first[name]==('reject','number_length') and name not in second,'ingress rejection')
            out.append((name,len(raw),None,'ingress_reject'))
            continue
        value=in_obj(expected)
        require(first[name]==('accept',value),'first-pass byte expectation')
        verdict=('reject','number_length') if len(expected)>1024 else ('accept',value)
        require(second[name]==verdict,'second-pass expectation')
        out.append((name,len(raw),len(expected),'stable' if verdict[0]=='accept' else 'length_reject'))
    for name in PINS:
        read(name)
    print(json.dumps(out,indent=2))
    print('SIX SYNTHETIC EXPECTATIONS MATCH (unchanged bounded candidates)')
    return 0


if __name__=='__main__':
    sys.exit(main())
