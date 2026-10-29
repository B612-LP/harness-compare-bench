#!/usr/bin/env python3
"""Independent fixed input snapshot; no product, checker, network or Git invocation."""
import hashlib, json, os, shutil, stat, tempfile
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
L4='1-评测方案/自动循环L4-2026-10-29'
L5='1-评测方案/自动循环L5-2026-10-30'
REV='5-评测报告/L5判卷修订-2026-10-30'
BASE='5-评测报告/L4独立验收-2026-10-29'
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return {'sha256':h.hexdigest(),'bytes':p.stat().st_size}
def create(p,obj):
    with p.open('x',encoding='utf-8') as f: json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')
def main():
    tmp=Path(tempfile.mkdtemp(prefix='l5-independent-')).resolve()
    pub=tmp/'public';pub.mkdir()
    selected={}
    def add(rel):
        src=ROOT/rel
        if src.is_symlink() or not src.is_file(): raise RuntimeError('nonregular input: '+rel)
        dst=pub/rel;dst.parent.mkdir(parents=True,exist_ok=True)
        before=digest(src);shutil.copyfile(src,dst)
        if before!=digest(dst) or before!=digest(src): raise RuntimeError('snapshot drift: '+rel)
        selected[rel]=before
    def tree(rel):
        for d,ds,fs in os.walk(ROOT/rel,followlinks=False):
            ds[:]=sorted(x for x in ds if x!='__pycache__')
            if any((Path(d)/x).is_symlink() for x in ds): raise RuntimeError('symlink directory')
            for n in sorted(fs):
                if not n.endswith('.pyc'): add(str((Path(d)/n).relative_to(ROOT)))
    for loop in (L4,L5):
        m=json.loads((ROOT/loop/'execution-manifest.json').read_text())
        for rel in m['files']: add(rel)
        for n in ('execution-manifest.json','runtime-binding.json'):add(loop+'/'+n)
    tree(REV)
    tree(BASE+'/realdata-product')
    add(BASE+'/realdata-cache/offline-recompute-erratum.json')
    plan=json.loads((ROOT/L4/'plan.json').read_text())
    for slot in plan['product_slots']:tree(slot['evidence_dir'])
    probes='3-表现现场/l4-20261029-cache/probes'
    for p in sorted((ROOT/probes).iterdir()):
        if p.is_dir():add(probes+'/'+p.name+'/usage.raw.json')
    for name in ('tmp','logs'): (tmp/name).mkdir()
    policy='(version 1)\n(allow default)\n(deny network*)\n(deny file-write*)\n'
    policy+='(allow file-write* (subpath '+json.dumps(str(tmp))+') (subpath '+json.dumps(str(OUT))+') (literal "/dev/null"))\n'
    (tmp/'no-network-readonly.sb').write_text(policy)
    rec={'generated_at':datetime.now().astimezone().isoformat(timespec='seconds'),
         'source_root':str(ROOT),'temporary_root':str(tmp),'public_root':str(pub),
         'files':dict(sorted(selected.items())),'file_count':len(selected),
         'bytes':sum(v['bytes'] for v in selected.values()),
         'sandbox_policy':str(tmp/'no-network-readonly.sb'),
         'sandbox_policy_digest':digest(tmp/'no-network-readonly.sb'),
         'environment_policy':'minimal env; explicit HOME retained only for absolute historical external pin identity; original .git read-only; no original evidence execution; all receipt writes confined to new temp/output',
         'git_permissions':'lead clarified read-only Git only; no repository writes',
         'live_doc_drift':[]}
    create(OUT/'input-snapshot-01.json',rec)
    print(json.dumps({k:rec[k] for k in ('temporary_root','file_count','bytes')},ensure_ascii=False))
if __name__=='__main__':main()
