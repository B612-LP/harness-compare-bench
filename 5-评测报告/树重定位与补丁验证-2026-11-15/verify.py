#!/usr/bin/env python3
"""Recompute safe derived pure algorithms; does not certify private historical originals."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

VARIANTS=('before','after','reference')
PAYLOADS=('before.py','after.py','reference.py','canonical_test.py','worker.py')

def require(ok,message):
    if not ok:raise ValueError(message)

def encoded(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)

def load_worker(base):
    # This is a local trusted verifier helper, not a product/trace command executor.
    import importlib.util
    spec=importlib.util.spec_from_file_location('pov_oracle',base/'worker.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def validate_sources(base):
    sources=json.loads((base/'sources.json').read_text(encoding='utf-8'))
    require(sources.get('schema')=='pov-source-projection-v1','source schema')
    worker=load_worker(base)
    require(set(sources['payloads'])==set(worker.PAYLOAD_HASHES),'payload keys')
    for name,pin in worker.PAYLOAD_HASHES.items():
        raw=(base/name).read_bytes()
        require(hashlib.sha256(raw).hexdigest()==pin,'payload identity mismatch: '+name)
        require(type(sources['payloads'][name]['bytes']) is int and sources['payloads'][name]['bytes']==len(raw),'payload bytes')
        require(sources['payloads'][name]['sha256']==pin,'payload source pin')
        worker.read_payload(base,name)
    require(encoded(sources['historical_summary'])==encoded({'tests_run':15,'successes':12,'failures':3,'errors':0,'identities_match':False,'failed_test_ids':None}),'historical boundary')
    require(encoded(sources['snapshot'])==encoded({'records':65,'post_edit_recheck_observed':False,'backend_continuation':None}),'snapshot boundary')
    require(sources['causal_harness_attribution'] is None,'causal boundary')
    return sources

def execute(base,variant,optimize=0,timeout=8,runner=subprocess.run):
    require(type(optimize) is int and optimize in (0,1),'explicit optimize 0 or 1')
    require(variant in VARIANTS,'variant')
    # Each child runs ONLY copies of reviewed pure code and tests, isolated from site/PYTHONPATH.
    with tempfile.TemporaryDirectory(prefix='pov-pure-') as name:
        temp=Path(name)
        for payload in PAYLOADS:shutil.copyfile(base/payload,temp/payload)
        command=[sys.executable,'-I','-S','-B']+(['-O'] if optimize else [])+[str(temp/'worker.py'),variant]
        try:
            done=runner(command,cwd=temp,capture_output=True,text=True,timeout=timeout,check=False)
        except subprocess.TimeoutExpired:
            return {'variant':variant,'status':'unknown','reason':'child_timeout','canonical':None,'oracle':None}
        except OSError:
            return {'variant':variant,'status':'unknown','reason':'child_unavailable','canonical':None,'oracle':None}
        if done.returncode!=0:return {'variant':variant,'status':'unknown','reason':'child_nonzero','canonical':None,'oracle':None}
        try:reply=json.loads(done.stdout)
        except (ValueError,TypeError):return {'variant':variant,'status':'unknown','reason':'child_invalid_json','canonical':None,'oracle':None}
        require(type(reply.get('optimize')) is int and reply['optimize']==optimize,'child optimization identity')
        result=reply['result'];require(result.get('variant')==variant,'child variant identity')
        return dict(result,status='observed',reason=None)

def claims(versions):
    if any(v['status']!='observed' for v in versions):
        return {'repair_complete':None,'partial_topology_repair':None,'historical_failed_test_ids':None,'harness_cause':None}
    before,after,reference=versions
    ref_ok=reference['canonical']['successes']==15 and reference['oracle']['summary']['reroot_passed']==reference['oracle']['summary']['reroot_checked'] and reference['oracle']['summary']['path_passed']==reference['oracle']['summary']['path_checked'] and reference['oracle']['summary']['error_passed']==reference['oracle']['summary']['error_checked']
    if not ref_ok:return {'repair_complete':None,'partial_topology_repair':None,'historical_failed_test_ids':None,'harness_cause':None}
    rows=after['oracle']['reroot_rows']
    shallow=all(r.get('root_ok') and r.get('edges_ok') for r in rows if r['depth']<=1)
    deep=any(r.get('root_ok') and not r.get('edges_ok') for r in rows if r['depth']>=2)
    summary=after['oracle']['summary']
    complete=(after['canonical']['successes']==15 and summary['reroot_passed']==summary['reroot_checked'] and summary['path_passed']==summary['path_checked'] and summary['error_passed']==summary['error_checked'] and summary['original_immutable'] is True)
    return {'repair_complete':complete,'partial_topology_repair':shallow and deep and after['canonical']['successes']>before['canonical']['successes'],'historical_failed_test_ids':None,'harness_cause':None}

def recompute(base,optimize=0,timeout=8,runner=subprocess.run):
    validate_sources(base)
    versions=[execute(base,v,optimize,timeout,runner) for v in VARIANTS]
    return {'schema':'pov-derived-result-v1','scope':'current safe reconstructed bytes; not historical failed-test identity','versions':versions,'claims':claims(versions)}

def verify(base,optimize=0):
    result=recompute(base,optimize)
    fixed=json.loads((base/'result.json').read_text(encoding='utf-8'))
    require(encoded(result)==encoded(fixed),'fixed result mismatch or unknown execution; no pass')
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--optimize',type=int,choices=(0,1),required=True,help='explicit child interpreter optimization (parent -O does not propagate)')
    args=parser.parse_args();result=verify(Path(__file__).resolve().parent,args.optimize)
    print(encoded({'verification':'derived pure-code logic only','child_optimize':args.optimize,'claims':result['claims'],'canonical':{v['variant']:{k:v['canonical'][k] for k in ('tests_run','successes','failures')} for v in result['versions']}}))

if __name__=='__main__':main()
