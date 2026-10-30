#!/usr/bin/env python3
"""Replay old/new checkers against only temporary copies; never grade history in place."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CASES = ('exercism-py-6', 'tb-cargo-plan')

def call(checker, run=None, selftest=False):
    cmd = [sys.executable, str(checker)] + (['--selftest'] if selftest else [str(run), '--json'])
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    try:
        result = json.loads(p.stdout.strip().splitlines()[-1]) if not selftest else None
    except (ValueError, IndexError):
        result = None
    return {'exit': p.returncode, 'result': result, 'stdout': p.stdout, 'stderr': p.stderr}

def oracle(case, dst):
    shutil.copytree(case / 'inputs', dst / 'inputs')
    if case.name == 'exercism-py-6':
        for p in (case/'solution').glob('*/*.py'):
            shutil.copy2(p, dst/'inputs/exercises'/p.parent.name/p.name)
    else:
        for p in (case/'solution').glob('*.py'):
            shutil.copy2(p, dst/'inputs/app'/p.name)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--phase', choices=('before','after'), required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    rows = []
    with tempfile.TemporaryDirectory(prefix='execution-grader-audit-') as td:
        root = Path(td)
        for name in CASES:
            case = root/name
            shutil.copytree(ROOT/'2-用例'/name, case, ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            if args.phase == 'before':
                for f in ('checker.py','truth.json'):
                    shutil.copy2(HERE/'before'/name/f, case/f)
            base = root/(name+'-oracle'); oracle(case,base)
            for label, run, want in [('oracle', base, 1)]:
                r = call(case/'checker.py',run)
                ok = r['exit']==0 and r['result']['reward']==want and r['result']['weighted']==100
                rows.append({'case':name,'test':label,'ok':ok,**r})
            r = call(case/'checker.py', selftest=True)
            rows.append({'case':name,'test':'selftest','ok':r['exit']==0,**r})
            if name == 'exercism-py-6':
                for label, payload in (
                    ('os_exit_zero','import os;os._exit(0)\n'),
                    ('sys_exit_zero','import sys;sys.exit(0)\n'),
                    ('fake_unittest_summary','import sys,os;sys.stderr.write("Ran 54 tests in 0.001s\\n\\nOK\\n");sys.stderr.flush();os._exit(0)\n'),
                    ('empty_suite','import unittest\nunittest.TestLoader.getTestCaseNames=lambda *a: []\n'),
                    ('no_callbacks','import unittest\nunittest.TestCase.run=lambda self,result=None: None\n'),
                    ('skip_all','import unittest\nunittest.TestCase.__unittest_skip__=True\n'),
                ):
                    run=root/label; shutil.copytree(base,run)
                    for p in (run/'inputs/exercises').glob('*/*.py'):
                        if not p.name.endswith('_test.py'):
                            prefix = p.read_text() + '\n' if label in ('empty_suite','no_callbacks','skip_all') else ''
                            p.write_text(prefix + payload)
                    r=call(case/'checker.py',run)
                    res=r['result']; checks={c['id']:c for c in res['checks']}
                    ok=r['exit']==0 and res['reward']==0 and res['weighted']==0 and checks['input_integrity']['pass'] and all(not checks[e]['pass'] for e in ('forth','poker','dominoes','bowling','zipper','pov'))
                    rows.append({'case':name,'test':label,'ok':ok,**r})
                # Verify checker itself does not restore/delete files in the supplied run.
                run=root/'readonly-history'; shutil.copytree(base,run)
                target=run/'inputs/exercises/forth/forth_test.py'; target.write_text('# historical changed test\n')
                cache=run/'inputs/exercises/forth/__pycache__/marker'; cache.parent.mkdir(exist_ok=True); cache.write_text('preserve')
                def digest(): return {str(p.relative_to(run)): hashlib.sha256(p.read_bytes()).hexdigest() for p in run.rglob('*') if p.is_file()}
                prior=digest(); r=call(case/'checker.py',run)
                rows.append({'case':name,'test':'no_checker_writeback','ok':prior==digest(),**r})
            else:
                original=(case/'truth.json').read_text()
                mutations={
                    'threshold_999':lambda t:t.update(threshold=999),
                    'case_drift':lambda t:t.update(case='wrong-case'),
                    'case_id_drift':lambda t:t.update(case_id='wrong-case'),
                    'total_checks_drift':lambda t:t.update(total_checks=999),
                    'critical_drift':lambda t:t.update(critical_checks=[]),
                    'hash_map_missing':lambda t:t.update(input_sha256={}),
                    'summary_drift':lambda t:t['expected_summary'].update(total_time_min=999),
                }
                for label,mutate in mutations.items():
                    truth=json.loads(original); mutate(truth); (case/'truth.json').write_text(json.dumps(truth))
                    r=call(case/'checker.py',base)
                    rows.append({'case':name,'test':label,'ok':r['exit']==2 and 'error' in (r['result'] or {}),**r})
                (case/'truth.json').write_text(original)
                p=case/'inputs/app/data/aircraft.json'; old=p.read_bytes(); p.write_bytes(old+b'\n')
                r=call(case/'checker.py',base)
                rows.append({'case':name,'test':'canonical_input_drift','ok':r['exit']==2 and 'error' in (r['result'] or {}),**r})
                # Updating truth to match tampered canonical bytes must not bypass pinned digest.
                truth=json.loads(original); truth['input_sha256']['aircraft.json']=hashlib.sha256(p.read_bytes()).hexdigest(); (case/'truth.json').write_text(json.dumps(truth))
                r=call(case/'checker.py',base)
                rows.append({'case':name,'test':'canonical_and_truth_hash_drift','ok':r['exit']==2 and 'error' in (r['result'] or {}),**r})
    receipt={'phase':args.phase,'passed':sum(r['ok'] for r in rows),'total':len(rows),'rows':rows}
    args.output.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    for r in rows: print(('PASS' if r['ok'] else 'FAIL'),r['case'],r['test'],'exit='+str(r['exit']), 'reward='+str((r['result'] or {}).get('reward')))
    print(f"{args.phase}: {receipt['passed']}/{receipt['total']} expected checks pass")
    return 0 if args.phase=='before' or receipt['passed']==receipt['total'] else 2

if __name__=='__main__': raise SystemExit(main())
