#!/usr/bin/env python3
"""Verify this public derivation and scoring account, not private provenance.
Does not execute submitted code, start products, or send model requests.
"""
import hashlib,json
from pathlib import Path

def verify(root):
    root=Path(root).absolute();repo=root.parent.parent
    if any(p.is_symlink() for p in (root,*root.parents)):raise ValueError('root_symlink')
    def read(rel):
        p=Path(rel)
        if p.is_absolute() or '..' in p.parts:raise ValueError('unsafe_manifest_path')
        q=root
        for part in p.parts:
            q=q/part
            if q.is_symlink():raise ValueError('symlink')
        return q.read_bytes()
    manifest=json.loads(read('manifest.json'));expected={x['path']:x['sha256'] for x in manifest['files']}
    if len(expected)!=len(manifest['files']):raise ValueError('duplicate_manifest_path')
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if actual!=set(expected)|{'manifest.json'}:raise ValueError('file_set_drift')
    for rel,h in expected.items():
        if hashlib.sha256(read(rel)).hexdigest()!=h:raise ValueError('hash_drift:'+rel)
    a=json.loads(read('accounting.json'));g=json.loads(read('grading.json'));c=json.loads(read('checker.json'))
    if a['create_control_invocations']!=2 or a['model_submit_invocations']!=1 or a['confirmed_submissions']!=1 or a['followup_new_model_submissions']!=0 or a['formal_admissions']!=0:raise ValueError('budget_or_formal_claim')
    if a['original_execution_state']!='unknown' or a['later_readonly_state']!='completed':raise ValueError('window_rewrite')
    gates={'input_integrity','code_rerun','plan_structure'}
    core=[x for x in c['checks'] if x['id'] not in gates]
    if len(core)!=c['total'] or sum(x['pass'] for x in core)!=c['passed']:raise ValueError('assertion_accounting')
    if (g['passed'],g['total'],g['reward'],g['weighted'])!=(c['passed'],c['total'],c['reward'],c['weighted']):raise ValueError('grade_drift')
    if g['checker_invocations']!=1 or g['checker_exit_code']!=0 or round(100*g['passed']/g['total'],2)!=g['weighted']:raise ValueError('grade_accounting')
    pin=json.loads(read('case-source-pins.json'))
    for x in pin:
        p=Path(x['path'])
        if p.is_absolute() or '..' in p.parts:raise ValueError('unsafe_source_pin')
        q=repo
        for part in p.parts:
            q=q/part
            if q.is_symlink():raise ValueError('source_pin_symlink')
        if hashlib.sha256(q.read_bytes()).hexdigest()!=x['sha256']:raise ValueError('source_pin_drift')
    checker=repo/'2-用例/tb-cargo-plan/checker.py'
    if hashlib.sha256(checker.read_bytes()).hexdigest()!=g['hashes']['checker']:raise ValueError('checker_drift')
    if hashlib.sha256(read('checker.json')).hexdigest()!=g['hashes']['checker_stdout']:raise ValueError('checker_receipt_drift')
    artifacts={'captured_flight_plan':'artifact-run/flight_plan.json','captured_aircraft_py':'artifact-run/inputs/app/aircraft.py','captured_dispatch_py':'artifact-run/inputs/app/dispatch.py','captured_navigation_py':'artifact-run/inputs/app/navigation.py'}
    for key,path in artifacts.items():
        if hashlib.sha256(read(path)).hexdigest()!=g['hashes'][key]:raise ValueError('artifact_drift')
    return {'status':'PASS_PUBLIC_DERIVATION_ONLY','files':len(expected),'source_pins':len(pin),'model_submissions':a['model_submit_invocations'],'passed':g['passed'],'total':g['total'],'reward':g['reward'],'formal_admissions':0,'private_raw_provenance_verified':False}
if __name__=='__main__':print(json.dumps(verify(Path(__file__).parent),ensure_ascii=False))
