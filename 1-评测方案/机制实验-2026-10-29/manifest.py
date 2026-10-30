#!/usr/bin/env python3
"""Freeze/verify explicit public evidence snapshots; never rewrites an existing manifest."""
import argparse,datetime,hashlib,json,pathlib,re
R=pathlib.Path(__file__).resolve().parent;REPO=R.parents[1];E=REPO/'3-表现现场/r20261029-mechanism';MANIFEST=E/'evidence-manifest.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
ap=argparse.ArgumentParser();ap.add_argument('action',choices=['build','verify']);a=ap.parse_args()
if a.action=='build':
    files=[]
    patterns=[r'sk-[A-Za-z0-9_-]{16,}',r'Bearer\s+[A-Za-z0-9._-]{12,}',r'-----BEGIN [A-Z ]*PRIVATE KEY-----']
    violations=[]
    for root in [R,E]:
        for p in sorted(root.rglob('*')):
            if not p.is_file() or p==MANIFEST or '__pycache__' in p.parts:continue
            if p.suffix in ['.json','.jsonl','.sse','.txt','.md']:
                # Source regex declarations are not live credentials; only text/evidence gets scanned.
                text=p.read_text()
                if any(re.search(pattern,text) for pattern in patterns):violations.append(str(p.relative_to(REPO)))
            files.append({'path':str(p.relative_to(REPO)),'bytes':p.stat().st_size,'sha256':sha(p)})
    if violations:print(json.dumps({'secret_pattern_scan_passed':False,'paths':violations}));raise SystemExit(1)
    obj={'schema_version':1,'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Explicit snapshot of listed original public source/evidence files. Independent review artifacts created later are not implicitly covered.','secret_pattern_scan_passed':True,'headers_recorded':False,'files':files}
    with MANIFEST.open('x') as f:json.dump(obj,f,ensure_ascii=False,indent=2)
    print(json.dumps({'manifest':str(MANIFEST.relative_to(REPO)),'files':len(files),'sha256':sha(MANIFEST)}))
else:
    obj=json.loads(MANIFEST.read_text());bad=[]
    for f in obj['files']:
        p=REPO/f['path']
        if not p.is_file() or sha(p)!=f['sha256'] or p.stat().st_size!=f['bytes']:bad.append(f['path'])
    print(json.dumps({'files':len(obj['files']),'valid':not bad,'bad':bad,'manifest_sha256':sha(MANIFEST)}));raise SystemExit(1 if bad else 0)
