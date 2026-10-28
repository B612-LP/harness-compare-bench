#!/usr/bin/env python3
"""Original public single-factor runner. Never opens a credential file or private driver.
Requires installed DSH CLI and existing official authentication. No browser/global writes.
"""
import argparse, datetime as dt, hashlib, json, os, pathlib, platform, shutil, signal, subprocess, time, uuid
ROOT=pathlib.Path(__file__).resolve().parent
PROMPT='Call fixture_output exactly once. Then return only a JSON object with HEAD_KEY and TAIL_KEY containing the two observed values. Ignore checksum noise. Do not call any additional tool.'
PLAN=[('large','full',12500),('large','bounded',512),('large','bounded',512),('large','full',12500),('small','full',12500),('small','bounded',512)]
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def redact(s,work):return s.replace(str(work),'<WORKSPACE>').replace(str(pathlib.Path.home()),'<HOME>')
def config(work,credentials,cap):
    rows=[{'id':'agent-default-model','config':{'provider':'deepseek-official','model':'deepseek-flash','reasoningEffort':'low'}},
          {'id':'llm-deepseek','config':{'reasoningEffort':'low','maxTokens':1024,'retryPolicy':{'mode':'normal','maxRetries':0}}},
          {'id':'credentials','config':{'path':str(credentials),'watch':False}},
          {'id':'spill-policy','config':{'maxInlineTokens':cap}},
          {'id':'system-prompt','config':{'personaPrefix':'You are an instrument-reading assistant. Use the available observation tool and answer the user precisely.','personaSuffix':''}},
          {'id':'headless-runner','inject':['headlessStartup','mechanismFixture']},
          {'insert':[{'id':'mechanism-fixture','name':str(ROOT/'fixture-plugin-v2.mjs')}] }]
    for id in ['tool-bash','tool-pwsh','tool-jobs','tool-fs','tool-fs-search','tool-subagent-control','tool-subagent-list-agents','tool-subagent','tool-subagent-fork','tool-workflow','tool-todo','tool-goal','tool-ralph','tool-plugin-manager','mcp-resources','settings','config-editor','agent-instructions','skill-filesystem','tool-skill','session-title-llm','session-title','session-log-deepseek','plugin-package-inventory-deepseek','llm-deepseek-account','llm-pi-ai','llm-retry','session-telemetry-otel','tool-result-pruner','compaction-basic','goal-round-driver','tool-web','web-search-deepseek','web-fetch-http']:
        rows.append({'id':id,'disabled':True})
    return rows
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--workspace',type=pathlib.Path,required=True);ap.add_argument('--evidence',type=pathlib.Path,required=True);ap.add_argument('--credential-store',type=pathlib.Path,required=True);ap.add_argument('--preflight-only',action='store_true');a=ap.parse_args()
    work=a.workspace.expanduser().resolve(); evidence=a.evidence.resolve(); credentials=a.credential_store.expanduser().absolute()
    work.mkdir(parents=True,exist_ok=True);evidence.mkdir(parents=True,exist_ok=True)
    home=work/'dsh-home';profile=home/'profiles'/'mechanism';profile.mkdir(parents=True,exist_ok=True)
    cwd=work/'agent-workspace';cwd.mkdir(exist_ok=True)
    save(profile/'package.json',{'name':'mechanism-isolated-profile','private':True,'dependencies':{},'dsh':{'profile':{'bundles':['@deepseek-ai/dsh-base','@deepseek-ai/dsh-headless']}}})
    (profile/'cordis.yml').write_text('[]\n')
    files=['PREREGISTRATION.md','AMENDMENT-v2.md','run_experiment_v2.py','fixture-plugin-v2.mjs','capture-preload.mjs']
    freeze={'version':2,'frozen_at':now(),'files':{f:sha(ROOT/f) for f in files},'plan':PLAN,'prompt':PROMPT,'prompt_sha256':hashlib.sha256(PROMPT.encode()).hexdigest(),'environment':{'os':platform.platform(),'python':platform.python_version(),'node':subprocess.check_output(['node','--version'],text=True).strip(),'dsh':subprocess.check_output(['dsh','--version'],text=True).strip(),'permission':'danger-full-access','skills':False,'browser':False,'auth':'DSH internal existing credential reference; runner never opens it'}}
    env={k:v for k,v in os.environ.items() if not k.startswith('DSH_') and k not in ['NODE_OPTIONS','DEEPSEEK_BASE_URL']}
    # No credential inspection/copy: existing env values may be inherited by DSH itself.
    env.update({'DSH_HOME':str(home),'DSH_PERMISSION_MODE':'danger-full-access','DSH_TELEMETRY_DISABLED':'1','DSH_TOOLS_MODE':'native','MECHANISM_WORKSPACE':str(work)})
    (profile/'cordis.patch.yml').write_text(json.dumps(config(work,credentials,12500),indent=2))
    preflight_dir=evidence/('preflight-'+uuid.uuid4().hex[:8]);preflight_dir.mkdir()
    check=subprocess.run(['dsh','--profile','mechanism','--dump-config'],cwd=cwd,env=env,text=True,capture_output=True,timeout=45)
    (preflight_dir/'stdout.txt').write_text(redact(check.stdout,work));(preflight_dir/'stderr.txt').write_text(redact(check.stderr,work))
    save(preflight_dir/'receipt.json',{'at':now(),'exit_code':check.returncode,'model_api_calls':0,'kind':'interface_preflight'})
    if check.returncode:raise SystemExit(check.returncode)
    if a.preflight_only:return
    # Exclusive freeze creation guards against accidentally restarting and discarding failures.
    with (evidence/'freeze.json').open('x') as f:json.dump(freeze,f,ensure_ascii=False,indent=2)
    (evidence/'prompt.txt').write_text(PROMPT+'\n')
    results=[];total_input=0
    for index,(size,arm,cap) in enumerate(PLAN,1):
        if total_input>150000:break
        rid=f'{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%SZ}-{index:02}-{size}-{arm}-{uuid.uuid4().hex[:8]}'
        out=evidence/rid;out.mkdir()
        (profile/'cordis.patch.yml').write_text(json.dumps(config(work,credentials,cap),indent=2))
        # Record all resolved experiment overrides, with private local paths externalized.
        save(out/'profile.json',json.loads(redact((profile/'cordis.patch.yml').read_text(),work)))
        runenv=env|{'MECHANISM_CAPTURE_DIR':str(out),'MECHANISM_SIZE':size,'NODE_OPTIONS':f'--import={ROOT/"capture-preload.mjs"}'}
        meta={'run_id':rid,'start':now(),'case_version':'fixture-v1','size':size,'arm':arm,'maxInlineTokens':cap,'model':{'provider':'deepseek-official','model':'deepseek-flash','reasoningEffort':'low'},'product':'DSH CLI','group':'research','experiment':True,'category':'product_run','permissions':'danger-full-access / approval never','skills':False,'tool_names':['fixture_output'],'workspace':'<WORKSPACE>/agent-workspace','profile_isolated':True,'recovery_read_tool_available':False,'freeze_sha256':sha(evidence/'freeze.json')}
        save(out/'run-meta.json',meta)
        start=time.monotonic();proc=subprocess.Popen(['dsh','--profile','mechanism','--json',PROMPT],cwd=cwd,env=runenv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
        timedout=False
        try:stdout,stderr=proc.communicate(timeout=240)
        except subprocess.TimeoutExpired:
            timedout=True;os.killpg(proc.pid,signal.SIGTERM)
            try:stdout,stderr=proc.communicate(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);stdout,stderr=proc.communicate()
        (out/'stdout.txt').write_text(redact(stdout,work));(out/'stderr.txt').write_text(redact(stderr,work))
        meta.update({'end':now(),'duration_seconds':time.monotonic()-start,'exit_code':proc.returncode,'timeout':timedout})
        # Snapshot only experiment-owned spill outputs. These are not private product implementation.
        spills=[]
        for p in (home/'spill').rglob('*') if (home/'spill').exists() else []:
            if p.is_file():spills.append({'path':redact(str(p),work),'bytes':p.stat().st_size,'sha256':sha(p),'readable_by_os_user':os.access(p,os.R_OK)})
        meta['spill_files_after_run']=spills
        reported_input=0;response_models=[]
        for p in out.glob('*-response.sse'):
            for line in p.read_text().splitlines():
                if line.startswith('data: '):
                    try:
                        event=json.loads(line[6:]);usage=event.get('usage') or event.get('message',{}).get('usage') or {}
                        reported_input+=usage.get('input_tokens',0)
                        model=event.get('model') or event.get('message',{}).get('model')
                        if model:response_models.append(model)
                    except (ValueError,TypeError):pass
        total_input+=reported_input
        meta['reported_input_tokens']=reported_input;meta['cumulative_reported_input_tokens']=total_input
        meta['actual_response_models']=response_models
        meta['actual_api_gate']=len(response_models)==2 and all(m in ['deepseek-flash','deepseek-v4.1-flash'] for m in response_models) and reported_input>0 and (out/'02-request.json').exists()
        save(out/'run-meta.json',meta);results.append(meta);save(evidence/'runs.json',results)
        # Output is retained even on failure; no retry or alternative route.
        if proc.returncode or timedout or list(out.glob('*blocked.json')) or not meta['actual_api_gate']:break
    save(evidence/'completion.json',{'at':now(),'completed_runs':len(results),'planned_runs':len(PLAN),'stopped_on_failure':bool(results and results[-1]['exit_code']),'analysis_required':True})
    print(json.dumps({'completed_runs':len(results),'evidence':str(evidence)},ensure_ascii=False))
if __name__=='__main__':main()
