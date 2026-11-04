#!/usr/bin/env python3
"""Read-only verification of this public, privacy-redacted calibration projection.
No product, network, subprocess, private path or raw-source lookup. Optional output
uses exclusive creation outside the package. This proves derived arithmetic and
package hashes only, not unpublished source identity or third-party attestation.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import statistics

HASH = re.compile(r'[0-9a-f]{64}')
FIXTURE_HASH = '32e93735af32bf9059005ab1f6af3fd94cde1d55b37bc29d0bb88061189d43f1'
GROUPS = [('read_long',4,'read',0.8),('read_short',12,'read',0.0),('open_no_read',4,'open_without_read',0.8),('idle',4,'idle',0.8),('read_mid',4,'read',0.05)]
FILES = ['README.md','read-detection.json','source-map.json','verify.py']
SCOPE = {'truth_source':'controlled_synthetic_child','sensor_independence':'os_views_separate_from_child_oracle','read_event_audit':False,'isolation_enforced':False,'third_party':'pending','timing_semantics':'sample_command_duration_and_start_gap_not_file_read_latency','vnode_semantics':'change_or_attribute_event_not_read'}
PRODUCT = {'starts':0,'file_read_denominator':0,'detection_rate':None,'isolation':'not_verified'}
LIMITS = ['synthetic_only_not_product','fixed_order_single_calibration_no_population_rate','open_fd_is_not_content_read','vnode_is_not_read_notification','short_lived_reads_may_be_missed','aliases_preopened_fd_mmap_cache_services_not_tested','no_os_wide_read_event_ground_truth','no_product_read_or_isolation_conclusion','no_third_party_attestation']

class Rejected(ValueError):
    pass

def need(condition, code):
    if not condition: raise Rejected(code)

def keys(value, names, code):
    need(type(value) is dict and set(value)==set(names), code)

def number(value):
    return type(value) in (int,float) and math.isfinite(value) and value>=0

def digest(data):
    return hashlib.sha256(data).hexdigest()

def stats(values):
    return {'n':len(values),'min':min(values),'median':statistics.median(values),'max':max(values)}

def matrix(trials,sensor):
    result={'TP':0,'FN':0,'FP':0,'TN':0}
    for row in trials:
        truth=row['ground_truth']['content_bytes'] is not None
        seen=any(s['fd_match'] for s in row['samples']) if sensor=='open_fd_sampler' else bool(row['vnode']['flags'])
        result[('TP' if seen else 'FN') if truth else ('FP' if seen else 'TN')]+=1
    result['read_denominator']=result['TP']+result['FN']
    result['nonread_denominator']=result['FP']+result['TN']
    result['FN_rate']=result['FN']/result['read_denominator'] if result['read_denominator'] else None
    result['recall']=result['TP']/result['read_denominator'] if result['read_denominator'] else None
    return result

def compute(trials):
    durations=[s['duration_s'] for r in trials for s in r['samples']]
    gaps=[b['start_offset_s']-a['start_offset_s'] for r in trials for a,b in zip(r['samples'],r['samples'][1:])]
    groups={}
    for prefix,n,op,hold in GROUPS:
        rows=[r for r in trials if r['group']==prefix]
        groups[prefix]={'n':len(rows),'fd_detected':sum(any(s['fd_match'] for s in r['samples']) for r in rows),'vnode_detected':sum(bool(r['vnode']['flags']) for r in rows),'matrices':{s:matrix(rows,s) for s in ['open_fd_sampler','vnode_change_watcher']}}
    return {'trial_count':len(trials),'read_trials':sum(r['ground_truth']['content_bytes'] is not None for r in trials),'nonread_trials':sum(r['ground_truth']['content_bytes'] is None for r in trials),'matrices':{s:matrix(trials,s) for s in ['open_fd_sampler','vnode_change_watcher']},'groups':groups,'sample_command_duration_s':stats(durations),'sample_start_gap_s':stats(gaps),'sample_status_counts':{s:sum(x['status']==s for r in trials for x in r['samples']) for s in ['sampled','no_fd_or_process_ended','error']}}

def validate_summary(s, calculated):
    keys(s,['trial_count','read_trials','nonread_trials','matrices','groups','sample_command_duration_s','sample_start_gap_s','sample_status_counts'],'summary_keys')
    for k in ['trial_count','read_trials','nonread_trials']: need(type(s[k]) is int,'summary_count_type')
    keys(s['matrices'],['open_fd_sampler','vnode_change_watcher'],'matrix_sensor_keys')
    for m in s['matrices'].values():
        keys(m,['TP','FN','FP','TN','read_denominator','nonread_denominator','FN_rate','recall'],'matrix_keys')
        for k,v in m.items(): need(number(v) and (type(v) is int if k not in ['FN_rate','recall'] else True),'matrix_numeric_type')
    keys(s['groups'],[x[0] for x in GROUPS],'group_keys')
    for g in s['groups'].values():
        keys(g,['n','fd_detected','vnode_detected','matrices'],'group_summary_keys')
        need(all(type(g[k]) is int and g[k]>=0 for k in ['n','fd_detected','vnode_detected']),'group_numeric_type')
        keys(g['matrices'],['open_fd_sampler','vnode_change_watcher'],'group_matrix_sensor_keys')
        for m in g['matrices'].values():
            keys(m,['TP','FN','FP','TN','read_denominator','nonread_denominator','FN_rate','recall'],'group_matrix_keys')
            need(all(type(m[k]) is int and m[k]>=0 for k in ['TP','FN','FP','TN','read_denominator','nonread_denominator']),'group_matrix_count_types')
            need(all((m[k] is None if m['read_denominator']==0 else number(m[k])) for k in ['FN_rate','recall']),'group_matrix_rate_types')
    for k in ['sample_command_duration_s','sample_start_gap_s']:
        keys(s[k],['n','min','median','max'],'timing_summary_keys')
        need(type(s[k]['n']) is int and all(number(v) for v in s[k].values()),'timing_summary_types')
    keys(s['sample_status_counts'],['sampled','no_fd_or_process_ended','error'],'status_count_keys')
    need(all(type(v) is int and v>=0 for v in s['sample_status_counts'].values()),'status_count_types')
    need(s==calculated,'summary_arithmetic_mismatch')
    need(s['trial_count']==28 and s['read_trials']==20 and s['nonread_trials']==8,'fixed_denominators')
    need([s['matrices']['open_fd_sampler'][k] for k in ['TP','FN','FP','TN']]==[8,12,4,4],'fd_fixed_matrix')
    need([s['matrices']['vnode_change_watcher'][k] for k in ['TP','FN','FP','TN']]==[1,19,0,8],'vnode_fixed_matrix')

def validate_payload(data):
    keys(data,['schema','artifact_kind','experiment_kind','scope','product','fixture','trials','write_positive_control','summary','limitations'],'payload_keys')
    need(data['schema']=='read-detection-public-v1' and data['artifact_kind']=='privacy-redacted-derived' and data['experiment_kind']=='synthetic_sensor_calibration','artifact_semantics')
    keys(data['scope'],SCOPE,'scope_keys'); need(data['scope']==SCOPE and all(type(data['scope'][k]) is bool for k in ['read_event_audit','isolation_enforced']),'scope_semantics')
    keys(data['product'],PRODUCT,'product_keys'); need(data['product']==PRODUCT and type(data['product']['starts']) is int and type(data['product']['file_read_denominator']) is int,'product_not_zero_null')
    keys(data['fixture'],['content_bytes','content_sha256'],'fixture_keys'); need(data['fixture']=={'content_bytes':39,'content_sha256':FIXTURE_HASH} and type(data['fixture']['content_bytes']) is int,'fixture_truth')
    need(data['limitations']==LIMITS,'limitations_semantics')
    rows=data['trials']; need(type(rows) is list and len(rows)==28,'trial_count')
    expected=[(f'{g}_{i:02d}',g,op,hold) for g,n,op,hold in GROUPS for i in range(n)]
    for index,(row,(trial_id,group,operation,hold)) in enumerate(zip(rows,expected),1):
        keys(row,['trial_id','sequence_index','group','operation','zone','planned_hold_s','ground_truth','samples','vnode','trial_duration_s'],'trial_keys')
        need(row['trial_id']==trial_id and row['group']==group and row['operation']==operation and row['zone']=='synthetic_forbidden_label','trial_identity')
        need(type(row['sequence_index']) is int and row['sequence_index']==index,'sequence')
        need(number(row['planned_hold_s']) and row['planned_hold_s']==hold,'hold')
        keys(row['ground_truth'],['content_bytes','content_sha256'],'ground_truth_keys')
        truth={'content_bytes':39,'content_sha256':FIXTURE_HASH} if operation=='read' else {'content_bytes':None,'content_sha256':None}
        need(row['ground_truth']==truth and (operation!='read' or type(row['ground_truth']['content_bytes']) is int),'ground_truth')
        need(number(row['trial_duration_s']),'trial_duration')
        samples=row['samples']; need(type(samples) is list and len(samples)>0,'sample_list')
        last_end=-1.0
        for j,s in enumerate(samples,1):
            keys(s,['sample_index','start_offset_s','duration_s','status','fd_match'],'sample_keys')
            need(type(s['sample_index']) is int and s['sample_index']==j,'sample_sequence')
            need(number(s['start_offset_s']) and number(s['duration_s']),'sample_timing_type')
            need(s['start_offset_s']>=last_end-1e-9 and s['start_offset_s']+s['duration_s']<=row['trial_duration_s']+1e-9,'sample_timing_order')
            last_end=s['start_offset_s']+s['duration_s']
            need(s['status'] in ['sampled','no_fd_or_process_ended','error'] and type(s['status']) is str and type(s['fd_match']) is bool,'sample_status')
            need(not s['fd_match'] or s['status']=='sampled','fd_status')
        keys(row['vnode'],['event_detected','flags'],'vnode_keys')
        need(type(row['vnode']['event_detected']) is bool and type(row['vnode']['flags']) is list,'vnode_types')
        need(all(type(x) is int and x==8 for x in row['vnode']['flags']),'vnode_flags_not_read')
        need(row['vnode']['event_detected']==bool(row['vnode']['flags']),'vnode_projection')
    control=data['write_positive_control']; keys(control,['operation','event_detected','flags','included_in_trial_matrix'],'control_keys')
    need(control=={'operation':'synthetic_append','event_detected':True,'flags':[6],'included_in_trial_matrix':False} and type(control['event_detected']) is bool and type(control['included_in_trial_matrix']) is bool and all(type(x) is int for x in control['flags']),'write_control_semantics')
    result=compute(rows); validate_summary(data['summary'],result)
    return result

def validate_source_map(mapping,data_bytes):
    keys(mapping,['schema','relation','verification_scope','sources','derived'],'source_map_keys')
    need(mapping['schema']=='read-detection-source-map-v1' and mapping['relation']=='privacy_projection_not_byte_copy' and mapping['verification_scope']=='derived_arithmetic_only_no_raw_identity','source_relation')
    need(type(mapping['sources']) is list and len(mapping['sources'])==1,'source_count')
    source=mapping['sources'][0]; keys(source,['source_id','role','sha256'],'source_keys')
    need(source['source_id']=='S001' and source['role']=='unpublished_calibration_receipt' and type(source['sha256']) is str and HASH.fullmatch(source['sha256']),'source_identity')
    need(type(mapping['derived']) is list and len(mapping['derived'])==1,'derived_count')
    derived=mapping['derived'][0]; keys(derived,['artifact_id','file','role','sha256','source_ids'],'derived_keys')
    need(derived['artifact_id']=='D001' and derived['file']=='read-detection.json' and derived['role']=='privacy_redacted_trial_projection' and derived['source_ids']==['S001'],'derived_identity')
    need(derived['sha256']==digest(data_bytes) and derived['sha256']!=source['sha256'],'source_derived_hash_confusion')

def parse_json(raw):
    def pairs(items):
        d={}
        for k,v in items:
            need(k not in d,'duplicate_json_key'); d[k]=v
        return d
    def invalid_constant(value): raise Rejected('nonfinite_json_constant')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid_constant)

def verify_package(root):
    need(root.is_dir() and not root.is_symlink(),'root_directory')
    need(set(p.name for p in root.iterdir())==set(FILES+['manifest.json']),'package_file_set')
    need(all((root/f).is_file() and not (root/f).is_symlink() for f in FILES+['manifest.json']),'package_file_type')
    manifest=parse_json((root/'manifest.json').read_bytes()); keys(manifest,['schema','artifact_kind','excluded_self','files'],'manifest_keys')
    need(manifest['schema']=='read-detection-manifest-v1' and manifest['artifact_kind']=='privacy-redacted-derived' and manifest['excluded_self']=='manifest.json','manifest_semantics')
    need(type(manifest['files']) is list and len(manifest['files'])==len(FILES),'manifest_count')
    for e,f in zip(manifest['files'],FILES):
        keys(e,['file','bytes','sha256'],'manifest_entry_keys'); raw=(root/f).read_bytes()
        need(e['file']==f and type(e['bytes']) is int and e['bytes']==len(raw) and e['sha256']==digest(raw),'manifest_hash')
    raw=(root/'read-detection.json').read_bytes(); result=validate_payload(parse_json(raw))
    validate_source_map(parse_json((root/'source-map.json').read_bytes()),raw)
    readme=(root/'README.md').read_text()
    need(not any(x in readme for x in ['/Users/','/home/','bench-private','sudo ','hostname=','PID=']),'readme_privacy')
    need(readme.count('\n## ')==5,'readme_five_parts')
    return {'schema':'read-detection-public-verification-v1','pass':True,'scope':'public_projection_arithmetic_and_hashes_only','source_identity_verified':False,'third_party_attestation':False,'summary':result,'product':PRODUCT}

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--root',type=Path,default=Path(__file__).resolve().parent); p.add_argument('--output',type=Path); a=p.parse_args()
    root=a.root.resolve()
    if a.output:
        destination=a.output.resolve()
        need(not destination.exists() and not a.output.is_symlink(),'output_exists')
        need(root not in destination.parents,'output_must_be_outside_package')
    try:
        result=verify_package(root)
    except (Rejected,ValueError,TypeError,KeyError,OSError) as exc:
        result={'schema':'read-detection-public-verification-v1','pass':False,'error':str(exc) if isinstance(exc,Rejected) else 'invalid_or_unreadable_package','scope':'public_projection_arithmetic_and_hashes_only'}
    text=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    if a.output:
        with a.output.open('x',encoding='utf-8') as f: f.write(text)
    print(text,end=''); return 0 if result['pass'] else 1

if __name__=='__main__':
    try:
        raise SystemExit(main())
    except Rejected as exc:
        print(json.dumps({'pass':False,'error':str(exc)})); raise SystemExit(2)
