"""Check only the fixed public R1 slice; leave all original R1 files unchanged."""
from contextlib import redirect_stdout
from hashlib import sha256
from io import StringIO
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from types import ModuleType

ROOT=Path(__file__).resolve().parents[2]
R1='4-打分细则/规范不产值实现一致性与跨解析器-2026-11-27/'
BASE='3-表现现场/r20261125-five-lcb/'
PY=R1+'verify.py'
JS=R1+'crossparse.mjs'
SOURCES=(
 ('dsh', BASE+'dsh/stdout-r2.jsonl',78,'105717eaca150dd36eab255bff74945509a3488837bb1b8df5e143aa337e2508'),
 ('codex',BASE+'codex/stdout-r2.jsonl',84,'d85c7d724ed4fed1e839aa6fc534cc025cca2288bdc08987d88c73643467be10'),
 ('doubao',BASE+'doubao/trajectory-38455827958268674-copy.jsonl',73,'8fc1d0e0ed5a2688b28a86e47a33e08975866a9f26e11ce79eb07c5d44d8d5a7'),
)
PINS={PY:'a1abf901698f05e9189f017fe6a7227b6f42827aba05bf8df5fc1bb7589ce24f',
      JS:'cc035ede18c117cbfb1efc681505f8e87598e5bd5eed2fd4f7370e7d7abb11b9',
      **{name:p for _,name,_,p in SOURCES}}


class Failure(ValueError): pass
class Incomplete(ValueError): pass


def need(ok, message):
    if not ok:raise Failure(message)


def read_pins(root):
    result={}
    for name,want in PINS.items():
        p=root/name
        try:raw=p.read_bytes()
        except (FileNotFoundError, NotADirectoryError):raise Incomplete('missing fixed public input') from None
        need(sha256(raw).hexdigest()==want,'fixed public source or measurement SHA differs')
        result[name]=raw
    return result


def unique(pairs):
    d=dict(pairs);need(len(d)==len(pairs),'duplicate output member');return d


def files_lines(blob, n):
    a=blob.split(b'\n')
    need(len(a)==n+1 and a[-1]==b'' and all(a[:-1]),'fixed LF coverage')
    return a[:-1]


def confirm(expected, raw):
    need(bool(expected),'empty expectation')
    lines=files_lines(raw,len(expected))
    seen=set()
    for a in lines:
        v=json.loads(a.decode('utf-8','strict'),object_pairs_hook=unique)
        need(type(v) is dict and set(v)=={'id','verdict'} and type(v['id']) is str,
             'output shape')
        i=v['id'];need(i in expected and i not in seen and v['verdict']=='match','output identity or verdict')
        seen.add(i)
    need(seen==set(expected),'missing output')
    return len(seen)


def check(root):
    bound=read_pins(root)
    node=shutil.which('node')
    if node is None:raise Incomplete('Node is absent; cross-parser result unknown')
    env=dict(os.environ)
    for name in ('NODE_OPTIONS','NODE_PATH'):env.pop(name,None)
    ran=subprocess.run([node,'--version'],env=env,capture_output=True,timeout=10)
    m=re.fullmatch(rb'v([0-9]{1,3})\.[0-9]+\.[0-9]+\s*',ran.stdout)
    if not m or ran.returncode or int(m[1])<18:raise Incomplete('Node >=18 required')
    mod=ModuleType('anchored_public_r1')
    mod.__file__=str(root/PY)
    # Compile only the verified measurement script, never a JSONL cell.
    exec(compile(bound[PY],mod.__file__,'exec'),mod.__dict__)
    with redirect_stdout(StringIO()):mod.part_a()
    need(not mod.FAILS,'R1 synthetic expectations failed')
    expected={};counts={}
    with tempfile.TemporaryDirectory(prefix='public-r1-completion-') as t:
        spot=Path(t); pay=spot/'data';pay.mkdir(); check_js=spot/'fixed.mjs';check_js.write_bytes(bound[JS])
        for label,name,n,want in SOURCES:
            rows=files_lines(bound[name],n);counts[label]=len(rows)
            for i,b in enumerate(rows,1):
                s=b.decode('utf-8','strict'); a,err=mod.stdlib_loads(s)
                need(err is None,'R1 stdlib refusal')
                canon=mod.canon(a)
                need(canon==mod.canon(mod.hardened_loads(s)),'R1 hardened parity')
                k=f'{label}/line{i:03d}';expected[k]=sha256(canon).hexdigest()
                with (pay/k.replace('/','__')).with_suffix('.txt').open('xb') as f:f.write(b)
        inp=spot/'corpus.jsonl';out=spot/'verdict.jsonl'
        with inp.open('x',encoding='utf-8',newline='\n') as f:
            for i,want in expected.items():
                f.write(json.dumps({'id':i,'canon_sha256':want})+'\n')
        p=subprocess.run([node,str(check_js),str(pay),str(inp),str(out)],env=env,capture_output=True,timeout=60)
        need(p.returncode==0 and out.is_file(),'Node did not deliver a result')
        matches=confirm(expected,out.read_bytes())
    need(matches==235 and bound==read_pins(root),'end-of-run coverage or source mismatch')
    return {'scope':'fixed public R1 only','sources':counts,'matched_ids':matches,'fixed_files':len(PINS)}


def main():
    try:result=check(ROOT)
    except Incomplete as e:print('INCOMPLETE: '+str(e));return 2
    except Failure as e:print('REJECT: '+str(e));return 1
    except (OSError,ValueError,RecursionError,subprocess.SubprocessError):
        print('REJECT: local execution or malformed result');return 1
    print(json.dumps(result,sort_keys=True))
    print('FIXED PUBLIC R1 COMPLETE; no private archive verdict')
    return 0


if __name__=='__main__':raise SystemExit(main())
