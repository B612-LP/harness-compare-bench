#!/usr/bin/env python3
"""Zero-network runtime requirements check, separate from real model experiments."""
import importlib.util,json,os,pathlib,subprocess,datetime,uuid
R=pathlib.Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('runner',R/'run_experiment_v2.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
work=pathlib.Path.home()/'bench-workspaces/r20261029-mechanism/runtime-preflight'
evidence=R.parents[1]/'3-表现现场/r20261029-mechanism'/('runtime-preflight-'+uuid.uuid4().hex[:8])
evidence.mkdir(parents=True);p=work/'dsh-home/profiles/mechanism';p.mkdir(parents=True,exist_ok=True);cwd=work/'agent-workspace';cwd.mkdir(exist_ok=True)
m.save(p/'package.json',{'name':'mechanism-runtime-preflight','private':True,'dsh':{'profile':{'bundles':['@deepseek-ai/dsh-base','@deepseek-ai/dsh-headless']}}})
(p/'cordis.yml').write_text('[]\n');(p/'cordis.patch.yml').write_text(json.dumps(m.config(work,pathlib.Path.home()/'.dsh/.credentials.yaml',12500)+[{'id':'plan-mode','disabled':True},{'id':'command-compact','disabled':True}],indent=2))
env={k:v for k,v in os.environ.items() if not k.startswith('DSH_') and k not in ['NODE_OPTIONS','DEEPSEEK_BASE_URL']}
env.update({'DSH_HOME':str(work/'dsh-home'),'DSH_PERMISSION_MODE':'danger-full-access','DSH_TELEMETRY_DISABLED':'1','DSH_TOOLS_MODE':'native','MECHANISM_WORKSPACE':str(work),'MECHANISM_CAPTURE_DIR':str(evidence),'MECHANISM_SIZE':'large','NODE_OPTIONS':f'--import={R/"runtime-preflight-preload.mjs"}'})
a=datetime.datetime.now(datetime.timezone.utc).isoformat();c=subprocess.run(['dsh','--profile','mechanism','--json',m.PROMPT],env=env,cwd=cwd,text=True,capture_output=True,timeout=45)
(evidence/'stdout.txt').write_text(m.redact(c.stdout,work));(evidence/'stderr.txt').write_text(m.redact(c.stderr,work))
request=evidence/'01-request.json';body=json.loads(request.read_text()) if request.exists() else {}
passed=(evidence/'01-fetch-error.json').exists() and 'ZERO_API_RUNTIME_PRECHECK_COMPLETE_NO_NETWORK' in (evidence/'01-fetch-error.json').read_text() and [x['name'] for x in body.get('tools',[])]==['fixture_output'] and not list(evidence.glob('*blocked.json'))
m.save(evidence/'receipt.json',{'category':'interface_preflight','start':a,'end':datetime.datetime.now(datetime.timezone.utc).isoformat(),'process_exit_code':c.returncode,'expected_sentinel_exit':True,'actual_network_calls':0,'runtime_requirements_passed':passed,'credential_resolution_reached_fetch':request.exists(),'note':'Native fetch replaced with explicit throwing sentinel before frozen capture load. Not a model response.'})
print(json.dumps({'passed':passed,'evidence':str(evidence)},ensure_ascii=False));raise SystemExit(0 if passed else 1)
