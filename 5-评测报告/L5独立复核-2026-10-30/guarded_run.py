#!/usr/bin/env python3
"""Execute unchanged copied offline script; permit only specific read-only Git subprocesses."""
import hashlib,json,os,runpy,sys
from pathlib import Path
from datetime import datetime
SCRIPT=Path(sys.argv[1]).resolve();OUT=Path(sys.argv[2]).resolve()
ops=[];blocked=[]
def guard(event,args):
    if event.startswith('socket.') or event in ('os.system','os.exec','os.posix_spawn','os.spawn','pty.spawn'):
        blocked.append({'event':event});raise PermissionError('independent zero-network/execution guard')
    if event=='subprocess.Popen':
        argv=args[1]
        ok=isinstance(argv,(tuple,list)) and len(argv)>1 and Path(str(argv[0])).name=='git'
        if ok:
            ok=argv[1] in ('show','rev-parse','cat-file','log') or (argv[1]=='merge-base' and len(argv)>2 and argv[2]=='--is-ancestor')
        rec={'executable':Path(str(args[0])).name,'subcommand':argv[1] if isinstance(argv,(tuple,list)) and len(argv)>1 else None}
        (ops if ok else blocked).append(rec)
        if not ok:raise PermissionError('only read-only Git subprocesses allowed')
sys.addaudithook(guard)
start=datetime.now().astimezone().isoformat(timespec='seconds');code=0
try:
    sys.argv=[str(SCRIPT)];runpy.run_path(str(SCRIPT),run_name='__main__')
except SystemExit as e:code=int(e.code or 0)
except BaseException as e:
    code=2
    import traceback;traceback.print_exc()
finally:
    receipt={'started_at':start,'finished_at':datetime.now().astimezone().isoformat(timespec='seconds'),
             'script':str(SCRIPT),'script_sha256':hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
             'returncode':code,'cwd':os.getcwd(),'environment_keys':sorted(os.environ),
             'home_retained_for_external_pin_identity':os.environ.get('HOME'),
             'read_only_git_operations':ops,'blocked_operations':blocked,
             'model_or_product_or_checker_subprocesses':0,'live_doc_drift':[]}
    with OUT.open('x',encoding='utf-8') as f:json.dump(receipt,f,ensure_ascii=False,indent=2);f.write('\n')
sys.exit(code)
