#!/usr/bin/env python3
"""Offline, bounded q28 projection; no archived SQL or checker is executed."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import sys
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
CASE = '2-用例/bird-ca-schools-15/'
RUN = '3-表现现场/r1109-mech-n3/runs/dsh__bird-ca-schools-15__r'
PINS = {
    CASE+'inputs/questions.json': '144bf7c36b58ab261f44676618a80af9f9d642fd287a4d2885c0cd7d53543f3e',
    CASE+'solution/answers.jsonl': '9b63a1846f0955cf2976c1ebb310c30e16eb740c9f09b7a7a45b5fe11b251929',
    CASE+'truth.json': 'c5bb7999079ac8f1711049d81392729edf127a27134d32a905ca39de15b8ea19',
    CASE+'inputs/db/california_schools.sqlite': 'a9e7d92a47c0d247d76a7a4acd76a4764f430f4d711e9e6809f399a9bf72322d',
    CASE+'checker.py': 'ffa7389adef32779686bbe56aef7d711db1d8d1c191ff5dd389310e6c01d1910',
    RUN+'1/workspace/answers.jsonl': '44e3cc1ea1456145cea92f072f52a66e14855b3c8b2612e6c37692ae558cf347',
    RUN+'2/workspace/answers.jsonl': 'a53015f170ef6148889c481bb902ea7cd334e8481149dc85f236ee14c0dfd538',
    RUN+'3/workspace/answers.jsonl': 'a53015f170ef6148889c481bb902ea7cd334e8481149dc85f236ee14c0dfd538',
    RUN+'1/checker.stdout.json': '4e37099cff001a545bd5ab81937d3c96fb9820b346c3989f75771a2b3aee396f',
    RUN+'2/checker.stdout.json': '286cc37b1201f8a893df4b2fe8a2ece3375ce96c8fc232bc3e6ea3c6366a0596',
    RUN+'3/checker.stdout.json': 'df9773dd7a2d263589ff9910cd944e2e41ec88f5e3c177fcd5ad088775d5a678',
}
DBREL=CASE+'inputs/db/california_schools.sqlite'

def need(condition, reason):
    if not condition:
        raise ValueError(reason)

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()

def verify_pins(root=ROOT):
    need(len(PINS)==11, 'unexpected source count')
    for rel,expected in PINS.items():
        path=root/rel
        need(path.is_file(), 'missing input: '+rel)
        need(digest(path)==expected, 'input SHA mismatch: '+rel)

def ensure_no_sidecars(db):
    for suffix in ('-wal','-shm','-journal'):
        need(not db.with_name(db.name+suffix).exists(), 'database sidecar present: '+suffix)

def project(value):
    # The actual school/doc projection contains only SQLite NULL and TEXT.
    if value is None:
        return '<NULL>'
    need(type(value) is str, 'projection value outside supported types')
    return value.strip()

def multiset(rows):
    return Counter((project(r[1]),project(r[2])) for r in rows)

def distinct_count(rows):
    return len(set(rows))

def get_receipts(root):
    result=[]
    for i in (1,2,3):
        r=json.loads((root/(RUN+str(i)+'/checker.stdout.json')).read_text(encoding='utf-8'))
        matches=[c for c in r['checks'] if c.get('id')=='q28']
        need(len(matches)==1, 'missing/duplicate q28 check')
        result.append({'input_integrity':r.get('input_integrity'),'pass':matches[0]['pass'],'note':matches[0]['note']})
    return result

def calculate(root=ROOT):
    root=Path(root); verify_pins(root)
    db=root/DBREL; ensure_no_sidecars(db)
    truth=json.loads((root/(CASE+'truth.json')).read_text(encoding='utf-8'))
    need(truth['input_sha256']['inputs/db/california_schools.sqlite']==PINS[DBREL], 'truth DB binding mismatch')
    receipts=get_receipts(root)
    uri='file:'+quote(str(db.resolve()))+'?mode=ro&immutable=1'
    con=sqlite3.connect(uri,uri=True)
    try:
        con.execute('PRAGMA query_only=ON')
        need(con.execute('PRAGMA query_only').fetchone()[0]==1, 'query_only unavailable')
        # Researcher-authored, constant SELECT, not copied/executed source SQL.
        rows=con.execute('''WITH joined AS (
          SELECT s.CDSCode AS key, s.School AS school, s.DOC AS doc, s.FundingType AS funding,
                 f.`Enrollment (K-12)`-f.`Enrollment (Ages 5-17)` AS delta
          FROM schools s JOIN frpm f ON s.CDSCode=f.CDSCode
        ), averages AS (
          SELECT AVG(CASE WHEN funding='Locally funded' THEN delta END) AS local_avg,
                 AVG(delta) AS all_avg FROM joined
        )
        SELECT key,school,doc,funding,delta,local_avg,all_avg,
               delta>local_avg,delta>all_avg,delta>=17,
               typeof(school),typeof(doc)
          FROM joined CROSS JOIN averages''').fetchall()
        stats=con.execute('''SELECT
          (SELECT COUNT(*) FROM schools),(SELECT COUNT(*) FROM frpm),
          (SELECT COUNT(*) FROM schools s WHERE NOT EXISTS (SELECT 1 FROM frpm f WHERE f.CDSCode=s.CDSCode)),
          (SELECT COUNT(*) FROM frpm f WHERE NOT EXISTS (SELECT 1 FROM schools s WHERE s.CDSCode=f.CDSCode)),
          (SELECT COUNT(*) FROM (SELECT CDSCode FROM schools GROUP BY CDSCode HAVING COUNT(*)>1)),
          (SELECT COUNT(*) FROM (SELECT CDSCode FROM frpm GROUP BY CDSCode HAVING COUNT(*)>1))''').fetchone()
    finally:
        con.close()
    need(rows, 'empty joined domain')
    type_counts=Counter((r[10],r[11]) for r in rows)
    need(set(type_counts)<={('null','text'),('text','text')}, 'unexpected SQLite projection types')
    local_mean,all_mean=rows[0][5:7]
    need(all((r[5],r[6])==(local_mean,all_mean) for r in rows),'inconsistent averages')
    local=[r for r in rows if r[3]=='Locally funded']
    wide=[r for r in rows if r[7]==1]
    narrow=[r for r in wide if r[3]=='Locally funded']
    removed=[r for r in wide if r[3]!='Locally funded']
    global_avg=[r for r in local if r[8]==1]
    ge17=[r for r in local if r[9]==1]
    cwide,cnarrow,cremoved,cglobal,cge=map(multiset,(wide,narrow,removed,global_avg,ge17))
    raw=lambda rs:Counter((r[1],r[2]) for r in rs)
    need(raw(wide)==raw(narrow)+raw(removed), 'raw partition mismatch')
    need(cwide==cnarrow+cremoved, 'normalized partition mismatch')
    groups=Counter('SQL NULL' if r[3] is None else str(r[3]) for r in removed)
    output={'sources_verified':len(PINS),'historical_q28':receipts,
      'joined':{'rows':len(rows),'nonnull_delta':sum(r[4] is not None for r in rows),'null_delta':sum(r[4] is None for r in rows),
        'local_rows':len(local),'local_nonnull_delta':sum(r[4] is not None for r in local),'local_null_delta':sum(r[4] is None for r in local),
        'schools':stats[0],'frpm':stats[1],'schools_unmatched':stats[2],'frpm_unmatched':stats[3],
        'school_duplicate_key_groups':stats[4],'frpm_duplicate_key_groups':stats[5]},
      'means':{'local':local_mean,'all_joined':all_mean},
      'projection_type_counts':{'null_text':type_counts[('null','text')],'text_text':type_counts[('text','text')]},
      'outer':{'unfiltered_rows':len(wide),'filtered_rows':len(narrow),'removed_rows':len(removed),
        'removed_funding':dict(sorted(groups.items())),
        'distinct_unfiltered_keys':distinct_count([r[0] for r in wide]),
        'distinct_unfiltered_raw_projection':distinct_count([(r[1],r[2]) for r in wide]),
        'raw_partition_exact':True,'normalized_partition_exact':True,
        'normalized_unfiltered_minus_filtered':sum((cwide-cnarrow).values()),
        'normalized_filtered_minus_unfiltered':sum((cnarrow-cwide).values())},
      'inner_mean_counterfactual':{'all_joined_mean_local_output_rows':len(global_avg),'normalized_multiset_same':cnarrow==cglobal},
      'threshold_counterexample':{'greater_or_equal_17_local_rows':len(ge17),'normalized_multiset_same':cnarrow==cge,
        'same_keys':Counter(r[0] for r in narrow)==Counter(r[0] for r in ge17)}}
    ensure_no_sidecars(db); verify_pins(root)
    return output

def verify_expected(result):
    # Fixed-source result contract, not proof of historical execution or binding.
    expected={
        'sources_verified':11,
        'historical_q28':[
            {'input_integrity':'unverified','pass':False,'note':'行数 2541 vs gold 57'},
            {'input_integrity':'unverified','pass':True,'note':'行集一致（57 行）'},
            {'input_integrity':'unverified','pass':True,'note':'行集一致（57 行）'},
        ],
        'joined':{'rows':9986,'nonnull_delta':9972,'null_delta':14,
            'local_rows':359,'local_nonnull_delta':354,'local_null_delta':5,
            'schools':17686,'frpm':9986,'schools_unmatched':7700,'frpm_unmatched':0,
            'school_duplicate_key_groups':0,'frpm_duplicate_key_groups':0},
        'means':{'local':16.70056497175141,'all_joined':16.261833132771763},
        'projection_type_counts':{'null_text':45,'text_text':9941},
        'outer':{'unfiltered_rows':2541,'filtered_rows':57,'removed_rows':2484,
            'removed_funding':{'SQL NULL':2308,'Directly funded':174,'Not in CS funding model':2},
            'distinct_unfiltered_keys':2541,'distinct_unfiltered_raw_projection':2436,
            'raw_partition_exact':True,'normalized_partition_exact':True,
            'normalized_unfiltered_minus_filtered':2484,'normalized_filtered_minus_unfiltered':0},
        'inner_mean_counterfactual':{'all_joined_mean_local_output_rows':57,'normalized_multiset_same':True},
        'threshold_counterexample':{'greater_or_equal_17_local_rows':57,'normalized_multiset_same':True,'same_keys':True},
    }
    def compare(actual, reference, path):
        need(type(actual) is type(reference), 'result type mismatch: '+path)
        if isinstance(reference,dict):
            need(actual.keys()==reference.keys(), 'result fields mismatch: '+path)
            for key in reference:
                compare(actual[key],reference[key],path+'.'+key)
        elif isinstance(reference,list):
            need(len(actual)==len(reference), 'result length mismatch: '+path)
            for i,(a,b) in enumerate(zip(actual,reference)):
                compare(a,b,path+'['+str(i)+']')
        elif isinstance(reference,float):
            need(math.isfinite(actual) and abs(actual-reference)<=1e-12, 'result mismatch: '+path)
        else:
            need(actual==reference, 'result mismatch: '+path)
    compare(result,expected,'result')

def main():
    try:
        result=calculate(); verify_expected(result)
        print(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2))
    except (ValueError,OSError,sqlite3.Error,KeyError,TypeError) as exc:
        print('verification failed: '+str(exc),file=sys.stderr)
        return 1
    return 0
if __name__=='__main__':
    raise SystemExit(main())
