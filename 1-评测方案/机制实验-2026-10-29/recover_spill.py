#!/usr/bin/env python3
"""Posthoc read-only inspection of exact experiment-generated native spill paths.
Not an API run, not a claim the model recovered the file. Never searches arbitrary temp files.
"""
import argparse,datetime,hashlib,json,os,pathlib,re
ap=argparse.ArgumentParser();ap.add_argument('--evidence',type=pathlib.Path,required=True);a=ap.parse_args();root=a.evidence.resolve();items=[]
for p in sorted((root/'v4').glob('20*/02-request.json')):
    req=json.loads(p.read_text());text='\n'.join(c.get('text','') for m in req['messages'] for b in m.get('content',[]) if b.get('type')=='tool_result' for c in b.get('content',[]))
    match=re.search(r'Full formatted result stored at: (.+?)\. Use read',text)
    if not match:continue
    f=pathlib.Path(match.group(1));item={'run_id':p.parent.name,'request_source':str(p.relative_to(root)),'native_spill_path':str(f),'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exists_posthoc':f.is_file(),'readable_posthoc':os.access(f,os.R_OK),'recorded_during_run':False,'runner_directory_scan_missed_system_tmp':True}
    if f.is_file():
        data=f.read_bytes();dest=p.parent/'native-spill-complete.txt'
        if dest.exists():assert dest.read_bytes()==data,'Existing public copy differs; refusing overwrite'
        else:dest.write_bytes(data)
        item.update({'public_copy':str(dest.relative_to(root)),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'matches_original_tool_output':data==(p.parent/'tool-output.txt').read_bytes()})
    items.append(item)
out=root/'spill-recovery-posthoc.json'
if out.exists():
    print('Existing original posthoc receipt retained; current inspection follows, without overwriting it.')
    print(json.dumps(items,indent=2));raise SystemExit()
out.write_text(json.dumps({'category':'offline_recompute','records':items,'claim_boundary':'Posthoc file existence/readability only; model had no read tool. Does not establish recovery behavior.'},indent=2)+'\n')
