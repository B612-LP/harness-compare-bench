#!/usr/bin/env python3
"""Offline positive/negative validation in fresh outside-repository copies; zero API."""
import argparse,datetime,hashlib,json,pathlib,shutil,subprocess,sys,uuid
R=pathlib.Path(__file__).resolve().parent;E=R.parents[1]/'3-表现现场/r20261029-mechanism'
ap=argparse.ArgumentParser();ap.add_argument('--output',type=pathlib.Path,required=True);a=ap.parse_args();results=[]
def run(label,e,expected):
    p=subprocess.run([sys.executable,str(R/'analyze.py'),'--evidence',str(e),'--verify'],text=True,capture_output=True)
    results.append({'test':label,'expected_exit_success':expected,'actual_exit_code':p.returncode,'passed':(p.returncode==0)==expected,'stdout':p.stdout.replace(str(pathlib.Path.home()),'<HOME>'),'stderr':p.stderr.replace(str(pathlib.Path.home()),'<HOME>'),'raw_stdout_sha256':hashlib.sha256(p.stdout.encode()).hexdigest(),'raw_stderr_sha256':hashlib.sha256(p.stderr.encode()).hexdigest()})
run('published_complete_six_runs',E,True)
base=pathlib.Path.home()/'bench-workspaces/r20261029-mechanism'/('offline-validation-'+uuid.uuid4().hex[:8]);base.mkdir(parents=True)
for label,mutation in [('missing_second_request','missing'),('wrong_model_response','model'),('wrong_http_status','status')]:
    d=base/label
    shutil.copytree(E,d,ignore=shutil.ignore_patterns('offline-verification.json','evidence-manifest.json','experiment-events.json','import-adapter.json','independent-review*'))
    original=json.loads((d/'analysis.json').read_text());r=d/original['runs'][1]['path']
    if mutation=='missing':
        # Move only in the fresh known copy, retaining evidence under a different explicit filename.
        p=(r/'02-request.json').resolve();assert p.is_relative_to(base.resolve());p.rename(r/'02-request.removed-for-negative-test.json')
    elif mutation=='model':
        p=r/'02-response.sse';s=p.read_text();assert '"model":"deepseek-flash"' in s;p.write_text(s.replace('"model":"deepseek-flash"','"model":"different-model"'))
    else:
        p=r/'02-response-meta.json';v=json.loads(p.read_text());v['status']=500;p.write_text(json.dumps(v))
    run(label,d,False)
# A fresh-layout adapter test copies existing actual evidence; it is NOT a new online run.
fresh=base/'offline-synthetic-fresh-layout';fresh.mkdir()
original=json.loads((E/'analysis.json').read_text())
for item in original['runs']:shutil.copytree(E/item['path'],fresh/item['run_id'])
freeze=json.loads((E/'v4/freeze.json').read_text());freeze['version']='offline-synthetic-layout-adaptation';freeze['frozen_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();(fresh/'freeze.json').write_text(json.dumps(freeze))
p=subprocess.run([sys.executable,str(R/'analyze.py'),'--evidence',str(fresh),'--output',str(fresh/'analysis.json')],text=True,capture_output=True)
results.append({'test':'offline_synthetic_fresh_layout_not_new_online_runs','expected_exit_success':True,'actual_exit_code':p.returncode,'passed':p.returncode==0,'stdout':p.stdout.replace(str(pathlib.Path.home()),'<HOME>'),'stderr':p.stderr.replace(str(pathlib.Path.home()),'<HOME>')})
if p.returncode==0:run('synthetic_fresh_layout_verify_no_mutation',fresh,True)
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'category':'self_test','actual_api_calls':0,'analyzer_sha256':hashlib.sha256((R/'analyze.py').read_bytes()).hexdigest(),'all_passed':all(t['passed'] for t in results),'tests':results}
with a.output.open('x') as f:json.dump(report,f,ensure_ascii=False,indent=2)
print(json.dumps({'all_passed':report['all_passed'],'tests':len(results)}));raise SystemExit(0 if report['all_passed'] else 1)
