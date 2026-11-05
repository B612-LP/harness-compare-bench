#!/usr/bin/env python3
"""Verify public bytes/accounting only; no product, submitted-code or network calls."""
import hashlib,json
from pathlib import Path
H=lambda b:hashlib.sha256(b).hexdigest()
def verify(root):
 root=Path(root).absolute();repo=root.parent.parent
 if any(p.is_symlink() for p in (root,*root.parents)):raise ValueError('root_symlink')
 def read(rel):
  p=Path(rel)
  if p.is_absolute() or '..' in p.parts:raise ValueError('unsafe_path')
  q=root
  for part in p.parts:
   q=q/part
   if q.is_symlink():raise ValueError('symlink')
  return q.read_bytes()
 m=json.loads(read('manifest.json'));expected={x['path']:x['sha256'] for x in m['files']}
 if len(expected)!=len(m['files']):raise ValueError('duplicate_manifest_path')
 if {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}!=set(expected)|{'manifest.json'}:raise ValueError('file_set_drift')
 for p,h in expected.items():
  if H(read(p))!=h:raise ValueError('hash_drift:'+p)
 a=json.loads(read('accounting.json'));g=json.loads(read('grading.json'));c=json.loads(read('checker.json'));s=g['score']
 if (a['original_create_invocations'],a['cumulative_model_submissions'],a['followup_new_model_submissions'],a['formal_admissions'],a['checker_invocations'])!=(1,1,0,0,1):raise ValueError('budget_or_formal_drift')
 if a['original_window_state']!='timeout' or a['original_window_capture_ok'] is not False or a['later_readonly_state']!='completed':raise ValueError('window_rewrite')
 if a['false_negative_rate'] is not None or a['read_truth_denominator'] is not None or a['os_isolation_verified'] is not False:raise ValueError('unearned_audit_claim')
 gates={'input_integrity','code_rerun','plan_structure'};core=[x for x in c['checks'] if x['id'] not in gates]
 if len(core)!=27 or len(core)!=c['total'] or sum(x['pass'] for x in core)!=c['passed']:raise ValueError('assertion_accounting')
 if any(s[k]!=c[k] for k in ('passed','total','weighted','reward','critical_ok','checker_version','contract_revision')):raise ValueError('grade_drift')
 if g['checker_invocations']!=1 or g['checker_exit_code']!=0 or round(s['passed']/s['total']*100,2)!=s['weighted']:raise ValueError('grade_accounting')
 if g['gates']!={x['id']:x['pass'] for x in c['checks'] if x['id'] in gates}:raise ValueError('gate_drift')
 if H(read('checker.json'))!=g['hashes']['checker_stdout']:raise ValueError('checker_receipt_drift')
 for p,h in g['hashes']['captured_files'].items():
  if p!='TASK.md' and H(read('artifact-run/'+p))!=h:raise ValueError('artifact_drift:'+p)
 pins=json.loads(read('case-source-pins.json'))
 if len(pins)!=8 or len({x['repo_relative'] for x in pins})!=8:raise ValueError('source_pin_count')
 for x in pins:
  p=Path(x['repo_relative'])
  if p.is_absolute() or '..' in p.parts:raise ValueError('unsafe_source_pin')
  q=repo
  for part in p.parts:
   q=q/part
   if q.is_symlink():raise ValueError('source_pin_symlink')
  if H(q.read_bytes())!=x['sha256']:raise ValueError('source_pin_drift')
 if H((repo/'2-用例/tb-cargo-plan/checker.py').read_bytes())!=g['hashes']['checker']:raise ValueError('checker_drift')
 ev=[json.loads(x) for x in read('trajectory.projection.jsonl').splitlines() if x.strip()]
 if len(ev)!=78 or sum(x['type']=='function_call' for x in ev)!=28 or sum(x['type']=='function_call_result' for x in ev)!=28:raise ValueError('projection_count')
 prior=json.loads((repo/'3-表现现场/r20261104-desktop-observation/slots.json').read_text())['slots'][0]
 if prior['window_state']!='timeout' or prior['grader_executed'] is not False:raise ValueError('historical_window_drift')
 return {'status':'PASS_PUBLIC_DERIVATION_ONLY','files':len(expected),'source_pins':len(pins),'new_model_submissions':0,'cumulative_model_submissions':1,'passed':s['passed'],'total':s['total'],'reward':s['reward'],'formal_admissions':0,'private_raw_provenance_verified':False}
if __name__=='__main__':print(json.dumps(verify(Path(__file__).parent),ensure_ascii=False))
