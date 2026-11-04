#!/usr/bin/env python3
"""Verify this projection without private originals. Default is read-only stdout."""
import sys
sys.dont_write_bytecode=True
import argparse, json, statistics
from pathlib import Path
import projection_protocol as p

EXPECTED_SOURCE_SET='8cf362bfcbd8bb732e75b9312755607dae92ab7c86b8a6a7464bf63f411d9f71'
EXPECTED_PROJECTION='1fa92e6a9cc6554bd1418f2d49584d8f84434db52e08652731058e26980dc668'
SCENE='3-表现现场/r20261104-native-provenance'

def require_path(root,name):
    p._need(isinstance(name,str) and name and '\\' not in name and not Path(name).is_absolute() and '..' not in Path(name).parts,'path_invalid')
    target=root/name;p._need(target.resolve().is_relative_to(root.resolve()) and not any(x.is_symlink() for x in (target,*target.parents) if x!=root.parent),'path_escape_or_symlink')
    return target

def load(root,name):return p._decode(require_path(root,name).read_bytes())
def file_record(value):
    p.keys(value,('sha256','bytes'));p.sha(value['sha256']);p.integer(value['bytes'],minimum=0)
def nullable_text(value):p._need(value is None or isinstance(value,str),'text_invalid')
def metric_schema(value,original=False):
    p.keys(value,('before','after','delta','wire','components_before','components_after','component_delta','serialization_wrapper_delta')+ (('primary_valid','invalid_reasons','returned_bytes') if original else ()))
    for name in ('components_before','components_after','component_delta'):
        p._need(isinstance(value[name],dict) and set(value[name])<={'instructions','input','tools','previous_response_id','system','messages'},'component_keys')
        for n in value[name].values():p.integer(n)
    p.integer(value['serialization_wrapper_delta'],nullable=True)
    for k in ('before','after','delta'):p.integer(value[k],nullable=True)
    p._need(isinstance(value['wire'],list) and len(value['wire'])<=2,'wire_lengths')
    for n in value['wire']:p.integer(n,minimum=0)
    if original:p.boolean(value['primary_valid'],nullable=True);p.strings(value['invalid_reasons']);p.integer(value['returned_bytes'],nullable=True,minimum=0)

def observation_schema(o):
    p.keys(o,('schema','id','contract_id','product','mode','phase','block','attempted','technical_valid','gate','end','accounting','original_metric','projection_metric','endpoint','controls','requests','usage','opaque','source_presence','provenance'))
    p._need(o['schema']==p.SCHEMA and o['id'] in p.SLOTS,'observation_identity');p.boolean(o['attempted']);p.boolean(o['technical_valid']);p.integer(o['block'],nullable=True,minimum=1)
    p._need(o['contract_id']==(p.OLD_CONTRACT if o['id']==p.HISTORICAL else p.CONTRACT),'contract_mixed')
    expected_product='dsh' if 'dsh' in o['id'] else 'codex'
    expected_mode='mock' if o['id'] in p.MOCKS else 'live'
    expected_phase='legacy_pilot' if o['id']==p.HISTORICAL else 'calibration' if o['id'] in p.MOCKS else 'pilot' if o['id'] in p.PILOTS else 'confirmation'
    expected_block=int(o['id'][9:11]) if o['id'] in p.CONFIRMS else None
    p._need(o['product']==expected_product and o['mode']==expected_mode and o['phase']==expected_phase and o['block']==expected_block and o['attempted'] is True,'observation_enums')
    g=o['gate'];p.keys(g,('ok','reasons','guard_halted','guard_reason','original_upstream_attempts','source_fingerprint'))
    for k in ('ok','guard_halted'):p.boolean(g[k],nullable=True)
    p.strings(g['reasons']);nullable_text(g['guard_reason']);nullable_text(g['source_fingerprint']);p.integer(g['original_upstream_attempts'],nullable=True,minimum=0)
    if g['source_fingerprint'] is not None:p.sha(g['source_fingerprint'])
    e=o['end'];p.keys(e,('exit_code','timeout','requests','fixture_called','fixture_calls','fixture_exit_code'))
    for k in ('exit_code','requests','fixture_calls','fixture_exit_code'):p.integer(e[k],nullable=True)
    p.boolean(e['timeout'],nullable=True);p.boolean(e['fixture_called'],nullable=True)
    a=o['accounting'];p.keys(a,('attempts','complete','lower','upper','request_count','receipt_count','reasons'))
    for k in ('attempts','upper'):p.integer(a[k],nullable=True,minimum=0)
    for k in ('lower','request_count','receipt_count'):p.integer(a[k],minimum=0)
    p.boolean(a['complete']);p.strings(a['reasons']);metric_schema(o['original_metric'],True);metric_schema(o['projection_metric'])
    ep=o['endpoint'];p.keys(ep,('head','tail','json_object_only','information_retained'))
    for v in ep.values():p.boolean(v,nullable=True)
    c=o['controls'];p.keys(c,('model','effort','output_cap_kind','output_cap','max_inline_tokens','version','actual_reasoning_controlled','server_final_input_observed','tool_menu'))
    for k in ('model','effort','output_cap_kind','version'):nullable_text(c[k])
    for k in ('output_cap','max_inline_tokens'):p.integer(c[k],nullable=True,minimum=0)
    p._need(c['actual_reasoning_controlled'] is False and c['server_final_input_observed'] is False,'unsupported_causal_control');p.strings(c['tool_menu'])
    p._need(isinstance(o['requests'],list) and len(o['requests'])==2,'request_slots')
    for i,r in enumerate(o['requests'],1):
        p.keys(r,('index','source_request_present','source_response_present','upstream_attempts','request_guard_approved','response_guard_approved','request_forwarded_unchanged','response_forwarded_unchanged','completion_validated','request_body_bytes','response_body_bytes','outcome','delivery'))
        p._need(type(r['index'])is int and r['index']==i,'request_index')
        for k in ('source_request_present','source_response_present'):p.boolean(r[k])
        for k in ('request_guard_approved','response_guard_approved','request_forwarded_unchanged','response_forwarded_unchanged','completion_validated'):p.boolean(r[k],nullable=True)
        for k in ('upstream_attempts','request_body_bytes','response_body_bytes'):p.integer(r[k],nullable=True,minimum=0)
        nullable_text(r['outcome']);nullable_text(r['delivery'])
    p._need(isinstance(o['usage'],list) and isinstance(o['opaque'],list),'auxiliary_lists')
    for u in o['usage']:
        p.keys(u,('request','event','source','reported_usage'));p._need(type(u['request'])is int and u['request'] in (1,2) and u['source'] in ('event','message','response'),'usage_identity');nullable_text(u['event']);p.usage_schema(u['reported_usage'])
    for x in o['opaque']:
        p.keys(x,('request','path','source_serialized_bytes','source_sha256','derived_serialized_bytes','derived_sha256'));p.integer(x['request'],minimum=1);p._need(isinstance(x['path'],str),'opaque_path')
        for k in ('source_serialized_bytes','derived_serialized_bytes'):p.integer(x[k],minimum=0)
        for k in ('source_sha256','derived_sha256'):p.sha(x[k])
    p.keys(o['source_presence'],p.RUN_FILES)
    for v in o['source_presence'].values():p.boolean(v)
    p.keys(o['provenance'],('status','reason'));p._need(o['provenance']['status'] in ('verified_projection','preserved_rejection','not_available'),'provenance_status');nullable_text(o['provenance']['reason'])

def map_schema(mapping,observations):
    p.keys(mapping,('schema','contract_id','originals','entries','limits'))
    p._need(mapping['schema']==p.SCHEMA and mapping['contract_id']==p.CONTRACT and mapping['originals']=='private_not_publicly_reverified','mapping_identity');p.strings(mapping['limits'])
    allowed_sources={'current/'+n for n in p.ROOT_SOURCES};allowed_sources.update('implementation/'+n for n in p.SOURCE_FILES);allowed_sources.update('legacy-implementation/'+n for n in p.LEGACY_FILES)
    expected_inputs=set()
    for slot,o in observations.items():
        expected_inputs.update(p.source_label(slot,n) for n,v in o['source_presence'].items() if v)
        allowed_sources.update(p.source_label(slot,n) for n in p.RUN_FILES)
    expected_inputs.update('current/'+n for n in p.ROOT_SOURCES)
    expected_inputs.update('implementation/'+n for n in p.SOURCE_FILES)
    expected_inputs.update('legacy-implementation/'+n for n in p.LEGACY_FILES)
    found=set();derived=set()
    for entry in mapping['entries']:
        p.keys(entry,('derived','derived_sha256','derived_bytes','transform','selected_source_bytes','selected_derived_bytes','inputs'))
        p._need(entry['transform'] in ('strict_metadata_whitelist_v1','wire_alias_equal_bytes_v1','fixture_identity_v1','source_pin_hashes_only_v1','ledger_derived_v1'),'transform_invalid')
        p._need(isinstance(entry['derived'],str) and entry['derived'] not in derived,'derived_duplicate');derived.add(entry['derived']);p.sha(entry['derived_sha256']);p.integer(entry['derived_bytes'],minimum=0)
        for k in ('selected_source_bytes','selected_derived_bytes'):p.integer(entry[k],nullable=True,minimum=0)
        p._need(isinstance(entry['inputs'],list) and bool(entry['inputs']),'mapping_inputs')
        for src in entry['inputs']:
            p.keys(src,('source','source_sha256','source_bytes'));p._need(src['source'] in allowed_sources,'source_not_whitelisted');p.sha(src['source_sha256']);p.integer(src['source_bytes'],minimum=0);found.add(src['source'])
        name=entry['derived'];expected_transform=None;expected_entry_inputs=set()
        if name=='source-pins.json':
            expected_transform='source_pin_hashes_only_v1';expected_entry_inputs={'current/FINAL-MANIFEST.json','current/legacy-source-pins.json'}|{'implementation/'+n for n in p.SOURCE_FILES}|{'legacy-implementation/'+n for n in p.LEGACY_FILES}
        elif name=='ledger.json':
            expected_transform='ledger_derived_v1';expected_entry_inputs={'current/'+n for n in p.ROOT_SOURCES if n not in ('FINAL-MANIFEST.json','legacy-source-pins.json')}
        else:
            parts=name.split('/');p._need(len(parts)==3 and parts[0]=='sessions' and parts[1] in observations,'derived_location');slot=parts[1];tail=parts[2]
            if tail=='observations.json':expected_transform='strict_metadata_whitelist_v1';expected_entry_inputs={p.source_label(slot,n) for n in p.METADATA_FILES if observations[slot]['source_presence'][n]}
            elif tail=='tool-output.txt':expected_transform='fixture_identity_v1';expected_entry_inputs={p.source_label(slot,'capture/tool-output.txt')}
            elif tail in ('01-request.json','02-request.json'):
                expected_transform='wire_alias_equal_bytes_v1';expected_entry_inputs={p.source_label(slot,'capture/'+tail),p.source_label(slot,'capture/'+tail.replace('.json','.raw'))}
            elif tail in ('01-response.sse','02-response.sse'):expected_transform='wire_alias_equal_bytes_v1';expected_entry_inputs={p.source_label(slot,'capture/'+tail)}
        p._need(expected_transform==entry['transform'] and {s['source'] for s in entry['inputs']}==expected_entry_inputs and len(entry['inputs'])==len(expected_entry_inputs),'entry_source_binding')
        if entry['transform']=='wire_alias_equal_bytes_v1':
            raw=[s for s in entry['inputs'] if s['source'].endswith(('-request.raw','-response.sse'))];p._need(len(raw)==1 and raw[0]['source_bytes']==entry['derived_bytes'],'wire_bytes_not_equal')
            p._need(entry['selected_source_bytes']==entry['selected_derived_bytes'],'selected_bytes_not_equal')
        else:p._need(entry['selected_source_bytes'] is None and entry['selected_derived_bytes'] is None,'unexpected_selected_bytes')
        if entry['transform']=='fixture_identity_v1':p._need(entry['inputs'][0]['source_sha256']==entry['derived_sha256']==p.FIXTURE_SHA and entry['inputs'][0]['source_bytes']==entry['derived_bytes']==p.FIXTURE_BYTES,'fixture_identity_mapping')
    p._need(found==expected_inputs,'source_coverage_not_exact')
    expected_derived={'source-pins.json','ledger.json'}
    for slot,o in observations.items():
        expected_derived.add('sessions/'+slot+'/observations.json')
        for i,r in enumerate(o['requests'],1):
            if r['source_request_present']:expected_derived.add('sessions/'+slot+'/%02d-request.json'%i)
            if r['source_response_present']:expected_derived.add('sessions/'+slot+'/%02d-response.sse'%i)
        if o['source_presence']['capture/tool-output.txt']:expected_derived.add('sessions/'+slot+'/tool-output.txt')
    p._need(derived==expected_derived,'derived_coverage_not_exact')
    return derived

def check_observation(root,o):
    slot=o['id'];base='sessions/'+slot+'/';raws=[];bodies=[];sse={};usage=[];known=0;receipt_count=0
    for i,r in enumerate(o['requests'],1):
        p._need(r['source_request_present']==o['source_presence']['capture/%02d-request.raw'%i] and r['source_request_present']==o['source_presence']['capture/%02d-request.json'%i],'source_raw_json_coverage')
        p._need(r['source_response_present']==o['source_presence']['capture/%02d-response.sse'%i],'source_sse_coverage')
        if r['source_request_present']:
            raw=require_path(root,base+'%02d-request.json'%i).read_bytes();body=p._decode(raw);p.check_body(body,o['product']);raws.append(raw);bodies.append(body)
            p._need(len(raw)==r['request_body_bytes'],'recorded_request_bytes')
        if r['source_response_present']:
            raw=require_path(root,base+'%02d-response.sse'%i).read_bytes();p._need(len(raw)==r['response_body_bytes'],'recorded_response_bytes');sse[i]=raw;usage+=p.usage_events(raw,i)
        if o['source_presence']['capture/%02d-meta.json'%i]:
            receipt_count+=1;p._need(r['upstream_attempts'] in (0,1) and type(r['upstream_attempts'])is int,'receipt_counter');known+=r['upstream_attempts']
    p._need(p._same(p.byte_metric(raws),o['projection_metric']),'projection_metric_recompute')
    original=o['original_metric'];projected=o['projection_metric']
    for k in projected:p._need(p._same(original[k],projected[k]),'original_projection_metric_mismatch')
    p._need(p._same(usage,o['usage']),'usage_recompute_not_sum')
    found_opaque=[]
    for i,b in enumerate(bodies,1):
        for path,n,h in p.opaque_values(b):found_opaque.append((i,path,n,h))
    p._need(len(found_opaque)==len(o['opaque']),'opaque_count')
    for found,x in zip(found_opaque,o['opaque']):
        p._need(found==(x['request'],x['path'],x['derived_serialized_bytes'],x['derived_sha256']) and x['source_serialized_bytes']==x['derived_serialized_bytes'],'opaque_projection')
    a=o['accounting'];p._need(a['lower']==known and a['receipt_count']==receipt_count and a['request_count']==len(raws),'independent_counter')
    if a['complete']:p._need(a['attempts']==known and a['upper']==known and not a['reasons'],'complete_accounting')
    else:p._need(a['attempts'] is None and a['upper'] in (2,None) and bool(a['reasons']),'unknown_not_zero')
    if o['mode']=='mock':p._need(known==0,'mock_not_live')
    if 2 in sse:p._need(p._same(p.endpoint(sse[2],o['product']),o['endpoint']),'endpoint_recompute')
    if len(bodies)==2 and 1 in sse:
        try:
            returned=p.check_chain(bodies[0],bodies[1],sse[1],o['product'])
            fixture=require_path(root,base+'tool-output.txt').read_bytes();p._need(len(fixture)==p.FIXTURE_BYTES and p.digest(fixture)==p.FIXTURE_SHA,'fixture_hash')
            p._returned_content(returned,fixture,{'returned_content_policy':'codex_native_v1' if o['product']=='codex' else 'dsh_native_v1'})
            observed={'status':'verified_projection','reason':None}
        except p.GateError as e:observed={'status':'preserved_rejection','reason':e.code}
        p._need(p._same(observed,o['provenance']),'provenance_recompute')
    valid=o['gate']['ok'] is True and o['gate']['guard_halted'] is not True and original['primary_valid'] is True
    p._need(o['technical_valid']==valid,'technical_not_endpoint')
    if valid:
        p._need(len(raws)==2 and len(sse)==2 and o['provenance']['status']=='verified_projection' and o['end']['exit_code']==0 and o['end']['timeout'] is False and o['end']['fixture_calls']==1 and o['end']['fixture_exit_code']==0,'valid_session_requirements')
        p._need(o['controls']['model']=='deepseek-flash' and o['controls']['effort']=='low','native_controls')
        for r in o['requests']:
            p._need(r['request_guard_approved'] is True and r['response_guard_approved'] is True and r['completion_validated'] is True and r['response_forwarded_unchanged'] is True and r['delivery']=='write_completed','valid_transfer_receipts')
            p._need(r['upstream_attempts']==(1 if o['mode']=='live' else 0) and r['request_forwarded_unchanged']==(o['mode']=='live'),'live_mock_counter_bind')
        expected_version='codex-cli 0.163.0' if o['product']=='codex' else '0.2.0-rc.2'
        p._need(o['controls']['version']==expected_version,'version_control')
        p._need(o['controls']['tool_menu']==[t.get('name',t.get('type')) for t in bodies[0]['tools']],'tool_menu_control')
        expected_cap=None if o['product']=='codex' else 1024
        p._need(o['controls']['output_cap']==expected_cap and o['controls']['output_cap_kind']==('provider_default_unknown' if expected_cap is None else 'exact'),'cap_control')
    if slot==p.HISTORICAL:p._need(o['gate']['original_upstream_attempts']==0 and a['attempts']==1 and not valid,'historical_failure_not_rewritten')
    return o

def recompute_ledger(observations):
    rows={o['id']:o for o in observations};new_live=[rows[s] for s in p.PILOTS+p.CONFIRMS if s in rows];mocks=[rows[s] for s in p.MOCKS if s in rows];known=sum(o['accounting']['lower'] for o in new_live);unknown=[o['id'] for o in new_live if not o['accounting']['complete']]
    total=None if unknown else known;upper=None if any(o['accounting']['upper'] is None for o in new_live) else sum(o['accounting']['upper'] for o in new_live)
    blocks=[];values=[]
    for b in (1,2,3):
        order=['confirm-b%02d-%s'%(b,pd) for pd in (('codex','dsh') if b%2 else ('dsh','codex'))];members=[rows.get(s) for s in order];valid=all(x is not None and x['technical_valid'] for x in members)
        c=rows.get('confirm-b%02d-codex'%b);d=rows.get('confirm-b%02d-dsh'%b);cv=c['original_metric']['delta'] if valid else None;dv=d['original_metric']['delta'] if valid else None;difference=cv-dv if valid else None
        blocks.append({'block':b,'order':order,'technical_valid':valid,'codex_delta':cv,'dsh_delta':dv,'difference_bytes':difference})
        if valid:values.append(difference)
    slots=[{'id':s,'status':('valid' if rows[s]['technical_valid'] else 'invalid') if s in rows else 'unattempted','upstream_attempts':rows[s]['accounting']['attempts'] if s in rows else None} for s in p.SLOTS]
    return {'schema':p.SCHEMA,'contract_id':p.CONTRACT,'budget':{'session_max':8,'upstream_max':16,'pilot_session_max':2,'confirmation_session_max':6},'new_live':{'sessions':len(new_live),'pilot':sum(o['phase']=='pilot' for o in new_live),'confirmation':sum(o['phase']=='confirmation' for o in new_live),'upstream_attempts':total,'lower':known,'upper':upper,'unknown_sessions':unknown},'strict_mocks':{'sessions':len(mocks),'upstream_attempts':sum(o['accounting']['lower'] for o in mocks),'ready_cli_sessions':sum(o['technical_valid'] for o in mocks),'failed_engineering_sessions':sum(not o['technical_valid'] for o in mocks)},'historical_live':{'sessions':int(p.HISTORICAL in rows),'upstream_attempts':rows[p.HISTORICAL]['accounting']['attempts'] if p.HISTORICAL in rows else None,'not_in_new_contract_budget':True},'slots':slots,'blocks':blocks,'valid_blocks':len(values),'differences':values,'median_difference_bytes':statistics.median(values) if values else None,'range_difference_bytes':[min(values),max(values)] if values else None,'branch':p.decision(values),'formal_new_rows':0,'third_party_witness':'pending','scope':'native selected-input observation; not same-schema/output-budget causal comparison; not token/cache/cost measurement'}

def ledger_schema(l):
    p.keys(l,('schema','contract_id','budget','new_live','strict_mocks','historical_live','slots','blocks','valid_blocks','differences','median_difference_bytes','range_difference_bytes','branch','formal_new_rows','third_party_witness','scope'))
    p.keys(l['budget'],('session_max','upstream_max','pilot_session_max','confirmation_session_max'));p.keys(l['new_live'],('sessions','pilot','confirmation','upstream_attempts','lower','upper','unknown_sessions'));p.keys(l['strict_mocks'],('sessions','upstream_attempts','ready_cli_sessions','failed_engineering_sessions'));p.keys(l['historical_live'],('sessions','upstream_attempts','not_in_new_contract_budget'))
    for s in l['slots']:p.keys(s,('id','status','upstream_attempts'))
    for b in l['blocks']:p.keys(b,('block','order','technical_valid','codex_delta','dsh_delta','difference_bytes'))

def verify(root,check_commitment=True):
    root=Path(root).resolve();manifest=load(root,'publication-manifest.json');p.keys(manifest,('schema','files'));p._need(manifest['schema']==p.SCHEMA and isinstance(manifest['files'],dict),'manifest_schema')
    actual=set()
    for f in root.rglob('*'):
        p._need(not f.is_symlink(),'unexpected_symlink')
        if f.is_file():actual.add(str(f.relative_to(root)))
    p._need(actual==set(manifest['files'])|{'publication-manifest.json'},'manifest_file_set')
    for name,record in manifest['files'].items():file_record(record);raw=require_path(root,name).read_bytes();p._need(len(raw)==record['bytes'] and p.digest(raw)==record['sha256'],'manifest_digest')
    observations={}
    for slot in p.SLOTS:
        name='sessions/'+slot+'/observations.json'
        if name in actual:o=load(root,name);observation_schema(o);p._need(o['id']==slot,'observation_slot');observations[slot]=check_observation(root,o)
    mapping=load(root,'projection-map.json');derived=map_schema(mapping,observations)
    expected=set(p.ROOT_FILES)|derived
    p._need(actual==expected|{'publication-manifest.json'},'exact_scene_files')
    for e in mapping['entries']:
        raw=require_path(root,e['derived']).read_bytes();p._need(p.digest(raw)==e['derived_sha256'] and len(raw)==e['derived_bytes'],'projection_digest')
    pins=load(root,'source-pins.json');p.keys(pins,('schema','contract_id','availability','sources','legacy_sources','source_set_sha256'))
    p._need(pins['schema']==p.SCHEMA and pins['contract_id']==p.CONTRACT and pins['availability']=='hash_only_private_source','source_pin_identity');p.keys(pins['sources'],p.SOURCE_FILES,'source_pin_keys');p.keys(pins['legacy_sources'],p.LEGACY_FILES,'legacy_source_pin_keys')
    for h in (*pins['sources'].values(),*pins['legacy_sources'].values()):p.sha(h)
    p._need(p.digest(p.canonical(pins['sources']))==pins['source_set_sha256']==EXPECTED_SOURCE_SET,'source_pin_set_digest')
    for entry in mapping['entries']:
        for src in entry['inputs']:
            if src['source'].startswith('implementation/'):
                name=src['source'][len('implementation/'):];p._need(src['source_sha256']==pins['sources'][name],'implementation_source_hash')
            elif src['source'].startswith('legacy-implementation/'):
                name=src['source'][len('legacy-implementation/'):];p._need(src['source_sha256']==pins['legacy_sources'][name],'legacy_implementation_source_hash')
        if entry['derived'].endswith('-request.json'):
            body=p._decode(require_path(root,entry['derived']).read_bytes());p._need(entry['selected_derived_bytes']==p.selected_bytes(body),'mapping_selected_recompute')
        elif entry['derived'].endswith('-response.sse'):
            p._need(entry['selected_derived_bytes'] is None and entry['selected_source_bytes'] is None,'response_selected_not_applicable')
    ledger=load(root,'ledger.json');ledger_schema(ledger);computed=recompute_ledger(list(observations.values()));p._need(p._same(ledger,computed),'ledger_recompute')
    p._need(ledger['new_live']['sessions']<=8 and ledger['new_live']['lower']<=16,'budget_exceeded')
    if check_commitment:p._need(p.digest(p.canonical(mapping))==EXPECTED_PROJECTION,'projection_snapshot_commitment')
    return {'schema':p.SCHEMA,'successful':True,'files_checked':len(actual),'source_pins_checked':len(pins['sources']),'new_live_sessions':ledger['new_live']['sessions'],'new_live_upstream_attempts':ledger['new_live']['upstream_attempts'],'strict_mock_sessions':ledger['strict_mocks']['sessions'],'valid_blocks':ledger['valid_blocks'],'median_difference_bytes':ledger['median_difference_bytes'],'branch':ledger['branch'],'private_originals_reverified':False,'third_party_witness':'pending'}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parent);parser.add_argument('--output',type=Path);args=parser.parse_args()
    try:result=verify(args.root)
    except Exception as e:result={'successful':False,'error':e.code if isinstance(e,p.GateError) else type(e).__name__}
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:
        with args.output.open('x',encoding='utf-8') as f:f.write(text)
    sys.stdout.write(text);raise SystemExit(0 if result['successful'] else 1)
