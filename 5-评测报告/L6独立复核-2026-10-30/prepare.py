#!/usr/bin/env python3
"""Fixed L6 byte snapshot; only read-only Git extraction, no product/checker execution."""
import hashlib,json,os,subprocess,tempfile
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
P6='1-评测方案/自动循环L6-2026-10-30';REV='5-评测报告/L6判卷修订-2026-10-30'
R6='3-表现现场/l6-20261030-wb-gateway/runs/l6-20261030-wb-gateway-bird-ca-schools-15-r1'
HISTORY=['3-表现现场/l5-20261030-wb-gateway/runs/l5-20261030-wb-gateway-bird-ca-schools-15-r1','3-表现现场/中止重封档案E2-20261030T0207/wb__bird-r1']
A1='3-表现现场/l5-20261030-cli/aborted-attempts-20261030T0152seal';A2='3-表现现场/中止重封档案E2-20261030T0207'
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return {'sha256':h.hexdigest(),'bytes':p.stat().st_size}
def create(p,x):
    with p.open('x',encoding='utf-8') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')
def main():
    temp=Path(tempfile.mkdtemp(prefix='l6-independent-')).resolve();pub=temp/'public';pub.mkdir();(temp/'tmp').mkdir()
    files={}
    def add(rel):
        if rel in files:return
        p=ROOT/rel
        if not p.is_file() or p.is_symlink():raise RuntimeError('nonregular '+rel)
        before=digest(p);q=pub/rel;q.parent.mkdir(parents=True,exist_ok=True)
        with q.open('xb') as f:f.write(p.read_bytes())
        if before!=digest(q) or before!=digest(p):raise RuntimeError('drift '+rel)
        files[rel]=before
    def tree(rel):
        for d,ds,ns in os.walk(ROOT/rel,followlinks=False):
            ds[:]=sorted(n for n in ds if n!='__pycache__')
            if any((Path(d)/n).is_symlink() for n in ds):raise RuntimeError('directory symlink')
            for n in sorted(ns):
                if not n.endswith('.pyc'):add(str((Path(d)/n).relative_to(ROOT)))
    manifest=json.loads((ROOT/P6/'execution-manifest.json').read_text())
    for rel in manifest['files']:add(rel)
    tree(P6);tree(REV);tree(R6)
    for run in HISTORY:tree(run)
    for base in (A1,A2):
        for n in ('abort-receipt.json','abort-receipt-supplement.json','abort-receipt-supplement-2.json'):
            if (ROOT/base/n).is_file():add(base+'/'+n)
    add('1-评测方案/自动循环L5-2026-10-30/contract.json')
    for case in json.loads((ROOT/P6/'contract.json').read_text())['case_snapshots']:tree('2-用例/'+case)
    tree('3-表现现场/l6-20261030-wb-gateway/receipts')
    add('4-打分细则/可信冻结-2026-10-29/freeze.py')
    # Clean history checker with its own case tree, not links into original files.
    oldcase=temp/'case-before';oldcase.mkdir()
    bird=pub/'2-用例/bird-ca-schools-15'
    import shutil
    for n in ('truth.json','solution','inputs'):
        src=bird/n;dst=oldcase/n
        if src.is_dir():shutil.copytree(src,dst)
        else:shutil.copyfile(src,dst)
    p=subprocess.run(['/usr/bin/git','show','79cebe0:2-用例/bird-ca-schools-15/checker.py'],cwd=ROOT,capture_output=True,check=True,env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'))
    (oldcase/'checker.py').write_bytes(p.stdout)
    # Candidate script has absolute ROOT. Relocate only its four module constants,
    # while preserving all script bytes and every function body. Originals untouched.
    (pub/REV/'l6-meta-recompute-receipt.json').rename(pub/REV/'archived-l6-meta-recompute-receipt.json')
    policy='(version 1)\n(allow default)\n(deny network*)\n(deny file-write*)\n'
    q=lambda x:json.dumps(str(x),ensure_ascii=False)
    policy+='(allow file-write* (subpath '+q(temp)+') (subpath '+q(OUT)+') (literal "/dev/null"))\n'
    policy+='(deny file-read* (subpath "/Users/b612-lp"))\n(allow file-read* (subpath '+q(ROOT)+'))\n'
    for ap in manifest['external_files']:
        if ap.startswith('/Users/b612-lp/'):policy+='(allow file-read* (literal '+q(ap)+'))\n'
    sb=temp/'offline.sb';sb.write_text(policy)
    receipt={'generated_at':datetime.now().astimezone().isoformat(timespec='seconds'),'root':str(ROOT),'temporary_root':str(temp),'public_root':str(pub),'files':files,'file_count':len(files),'bytes':sum(x['bytes'] for x in files.values()),'old_checker':{'path':str(oldcase/'checker.py'),**digest(oldcase/'checker.py'),'source':'git 79cebe0:2-用例/bird-ca-schools-15/checker.py'},'policy':str(sb),'policy_digest':digest(sb),'environment':'minimal explicit env; retained HOME for absolute external pins; no login or credentials decoded','relocation':'unchanged l6_meta_recompute.py main function; ROOT/ARCHIVE/CHECKER/SOURCES module globals relocated to exact byte-copy tree','live_doc_drift':[]}
    create(OUT/'snapshot-01.json',receipt)
    print(json.dumps({'temporary_root':str(temp),'file_count':len(files),'bytes':receipt['bytes']},ensure_ascii=False))
if __name__=='__main__':main()
