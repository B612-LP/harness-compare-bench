#!/usr/bin/env python3
"""Read-only, pinned-source, post-hoc Forth probes; NOT historical regrading."""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
TEST = '2-用例/exercism-py-6/tests/forth_test.py'
SPEC = '2-用例/exercism-py-6/inputs/exercises/forth/README.md'
BASE = '3-表现现场/r1105-bare-matrix/runs/inline-low/exercism-py-6__r'
SOURCES = {
    'reference': ('2-用例/exercism-py-6/solution/forth/forth.py', 'f0ddec3d8be41d304e82bc7f7b6531af44f8da1c3919a296d683ba0b97946613'),
    'bare_r1': (BASE+'1/inputs/exercises/forth/forth.py', 'bf736d64002551bfd0ea244b0f5d19f35316863bede81121296ca0d47b7aafe2'),
    'bare_r2': (BASE+'2/inputs/exercises/forth/forth.py', 'ca1a95a04784de5af32ead5abaeb4b23dab38d8d23d174c8e23359282df8f7cb'),
    'bare_r3': (BASE+'3/inputs/exercises/forth/forth.py', '68fbe21b2f0fc7de7576e7594f37d20e8f3c4d46ab7112b76c8cb3875c5ed427'),
    'wb_formal_archive': ('3-表现现场/r20261031-wb-formal/runs/exercism-py-6/artifacts/inputs/exercises/forth/forth.py', '096de3d7cf2e6e39cba7d0bed1e215a5cae0905dbdc15f7b65cb4e3e19e2626a'),
    'wb_legacy_archive': ('3-表现现场/r1029-desktop-auto/runs/workbuddy/exercism-py-6/workspace/inputs/exercises/forth/forth.py', '59af41a405ff45da9961ba795e3832324612b9e7c6c237074739434a2e19e970'),
}
PINS = dict(SOURCES.values())
PINS.update({TEST:'05f78a51ce5b3e18439088442925c7cea5b1fb1703bc10832dd048c057b7639c', SPEC:'0480b8a2eef97049ddff262b0bc21f5b31167561325c402918b5ceb0c37b466a'})
for rep, digest in [(1,'eeb675ef56b20542914ad1960a93c422e7b2a67c4cd49618c9f56af49aa887ed'),(2,'a7c61b2c4c75636e31de56b4e002566ea0dd1c755cbe73556f5143ddc27fc1a6'),(3,'a7c61b2c4c75636e31de56b4e002566ea0dd1c755cbe73556f5143ddc27fc1a6')]:
    PINS[BASE+str(rep)+'/RESULTS_JSON/result.json'] = digest

# Fixed before first execution. Signed probes distinguish conventions, not gold.
PROBES = [
    ('positive_exact','12 3 /',12,3,'canonical_positive'),
    ('positive_remainder','8 3 /',8,3,'canonical_positive'),
    ('negative_numerator','-8 3 /',-8,3,'signed_convention'),
    ('negative_denominator','8 -3 /',8,-3,'signed_convention'),
    ('both_negative','-8 -3 /',-8,-3,'signed_convention'),
    ('positive_large_identity','9007199254740993 1 /',9007199254740993,1,'large_positive'),
    ('positive_large_remainder','9007199254740995 3 /',9007199254740995,3,'large_positive'),
    ('constructed_large_identity','2 '+ 'dup + '*52 + '1 + 1 /',9007199254740993,1,'large_positive_small_literals'),
]

CHILD = r'''
import contextlib, io, json, pathlib, sys, unittest
root = pathlib.Path(sys.argv[1]); sys.path.insert(0,str(root))
import forth
suite = unittest.defaultTestLoader.discover(str(root), pattern='forth_test.py')
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
rows=[]
for item in json.loads(sys.stdin.read()):
    try:
        value=forth.evaluate([item['program']])
        rows.append({'id':item['id'],'state':'returned','value':value})
    except Exception as exc:
        rows.append({'id':item['id'],'state':'exception','type':type(exc).__name__,'message':str(exc)})
print(json.dumps({'tests_run':result.testsRun,'failures':[t.id() for t,_ in result.failures], 'errors':[t.id() for t,_ in result.errors],'skipped':[t.id() for t,_ in result.skipped], 'successful':result.wasSuccessful(),'probes':rows},sort_keys=True))
'''

def trunc_div(a: int, b: int) -> int:
    """Exact integer magnitude/remainder oracle, not float conversion."""
    q, r = divmod(abs(a), abs(b))
    if abs(a) != q*abs(b)+r or not 0 <= r < abs(b):
        raise ValueError('invalid division certificate')
    return -q if (a < 0) != (b < 0) else q


def check_pins() -> None:
    for rel, digest in PINS.items():
        if hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() != digest:
            raise ValueError('source pin mismatch: '+rel)


def canonical_calls() -> list[dict]:
    tree=ast.parse((ROOT/TEST).read_text(encoding='utf-8'))
    rows=[]
    for cls in tree.body:
        if not isinstance(cls,ast.ClassDef):
            continue
        for method in cls.body:
            if not isinstance(method,ast.FunctionDef) or not method.name.startswith('test_'):
                continue
            for node in ast.walk(method):
                if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='evaluate':
                    args=ast.literal_eval(node.args[0])
                    if any('/' in line.split() for line in args):
                        rows.append({'test':method.name,'programs':args})
    return rows


def compute() -> dict:
    check_pins()
    probes=[{'id':key,'program':program,'numerator':a,'denominator':b,'stratum':stratum,'trunc':trunc_div(a,b),'floor':a//b} for key,program,a,b,stratum in PROBES]
    results={}
    for label,(rel,_) in SOURCES.items():
        with tempfile.TemporaryDirectory(prefix='forth-offline-probe-') as td:
            work=Path(td)
            shutil.copyfile(ROOT/rel,work/'forth.py')
            shutil.copyfile(ROOT/TEST,work/'forth_test.py')
            try:
                proc=subprocess.run([sys.executable,'-I','-S','-B','-c',CHILD,td],input=json.dumps(probes),capture_output=True,text=True,timeout=10,env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'})
            except subprocess.TimeoutExpired:
                results[label]={'state':'unknown','reason':'timeout_10s'}
                continue
            if proc.returncode != 0:
                results[label]={'state':'unknown','reason':'child_exit','exit_code':proc.returncode}
                continue
            data=json.loads(proc.stdout)
            if data['tests_run'] != 54 or [row['id'] for row in data['probes']] != [row['id'] for row in probes]:
                raise ValueError('incomplete selected-source run: '+label)
            results[label]={'state':'complete','current_copy':data}
    historical={}
    for rep in (1,2,3):
        data=json.loads((ROOT/(BASE+str(rep)+'/RESULTS_JSON/result.json')).read_text())
        check=next(c for c in data['checks'] if c['id']=='forth')
        historical['bare_r'+str(rep)]={'case_reward':data['reward'],'case_weighted':data['weighted'],'forth_pass':check['pass'],'forth_completion':check['completion']}
    check_pins()
    return {'schema':'forth-offline-identifiability-v1','analysis_kind':'post_hoc_selected_source_execution_not_regrading','real_product_runs':0,'source_pins':PINS,'canonical_division_calls':canonical_calls(),'probes':probes,'historical_receipts':historical,'selected_sources':results}


if __name__=='__main__':
    print(json.dumps(compute(),ensure_ascii=False,sort_keys=True,indent=2))
