#!/usr/bin/env python3
"""Unchanged byte-copy execution under a fresh process environment and macOS sandbox."""
import concurrent.futures, hashlib, json, os, shutil, subprocess
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
REV='5-评测报告/L5判卷修订-2026-10-30'
def create(p,obj):
    with p.open('x',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    snap=json.loads((OUT/'input-snapshot-01.json').read_text());tmp=Path(snap['temporary_root']);pub=Path(snap['public_root'])
    # v1 used JSON ASCII escapes in an SBPL string. SBPL did not resolve Chinese
    # \\u spelling to the real output directory. Preserve v1; new policy uses UTF-8.
    policy='(version 1)\n(allow default)\n(deny network*)\n(deny file-write*)\n'
    q=lambda p:json.dumps(str(p),ensure_ascii=False)
    policy+='(allow file-write* (subpath '+q(tmp)+') (subpath '+q(OUT)+') (literal "/dev/null"))\n'
    policy+='(deny file-read* (subpath "/Users/b612-lp"))\n(allow file-read* (subpath '+q(ROOT)+'))\n'
    homepins=set()
    for loop in ('1-评测方案/自动循环L4-2026-10-29','1-评测方案/自动循环L5-2026-10-30'):
        homepins.update(p for p in json.loads((pub/loop/'execution-manifest.json').read_text())['external_files'] if p.startswith('/Users/b612-lp/'))
    for p in sorted(homepins):policy+='(allow file-read* (literal '+q(p)+'))\n'
    policy_path=tmp/'no-network-readonly-02.sb'
    with policy_path.open('x') as f:f.write(policy)
    env={'HOME':'/Users/b612-lp','PATH':'/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin','LANG':'en_US.UTF-8','TZ':'Asia/Shanghai',
         'TMPDIR':str(tmp/'tmp'),'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1','GIT_DIR':str(ROOT/'.git'),
         'GIT_WORK_TREE':str(pub),'GIT_OPTIONAL_LOCKS':'0','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_TERMINAL_PROMPT':'0'}
    cases=[('r4-acceptance',REV+'/gate-v2-notexec-acceptance.py',REV+'/gate-v2-acceptance-receipt.json'),
           ('r4-history',REV+'/gate-v2-history-recompute.py',REV+'/gate-v2-history-recompute-receipt.json'),
           ('r5-mapping','1-评测方案/工具链/l5-execution/cache_mapping_v2.py','1-评测方案/工具链/l5-execution/cache-mapping-v2-recompute-receipt.json')]
    def execute(case):
        label,rel,receipt=case
        if sha(pub/rel)!=snap['files'][rel]['sha256']:raise RuntimeError('copied script changed')
        metadata=OUT/(label+'-run-02.json')
        argv=['/usr/bin/sandbox-exec','-f',str(policy_path),'/usr/bin/python3','-I','-B',str(OUT/'guarded_run.py'),rel,str(metadata)]
        p=subprocess.run(argv,cwd=pub,env=env,capture_output=True)
        for kind,b in (('stdout',p.stdout),('stderr',p.stderr)):
            with (OUT/(label+'-'+kind+'-02.txt')).open('xb') as f:f.write(b)
        if (pub/receipt).is_file():
            with (OUT/(label+'-reproduced-receipt-02.json')).open('xb') as f:f.write((pub/receipt).read_bytes())
        return {'case':label,'returncode':p.returncode,'script_sha256':sha(pub/rel),'run_metadata':metadata.name}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(execute,cases))
    rec={'generated_at':datetime.now().astimezone().isoformat(timespec='seconds'),'runs':rows,'policy':str(policy_path),'policy_sha256':sha(policy_path),
         'environment_keys':sorted(env),'empty_home':False,'home_retained_for_explicit_absolute_external_pins':True,
         'home_reads_denied_except_repository_and_enumerated_pin_files':True,'original_files_write_denied':True,
         'network_os_policy':'deny network*','subprocess_python_policy':'read-only Git commands only',
         'live_doc_drift':[]}
    create(OUT/'reproduction-run-summary-02.json',rec);print(json.dumps(rows,ensure_ascii=False))
    return int(any(r['returncode']!=0 for r in rows))
if __name__=='__main__':raise SystemExit(main())
