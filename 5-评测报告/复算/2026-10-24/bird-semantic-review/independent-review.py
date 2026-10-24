#!/usr/bin/env python3
"""Independent SQL-only review. Never import project checker/numeric code.
All DB connections mode=ro&immutable=1; outputs only this derived-review directory.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parents[3]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized(rows):
    def cell(v):
        if v is None: return '<NULL>'
        if isinstance(v, float): return round(v, 6)
        if isinstance(v, str): return v.strip()
        return v
    return Counter(tuple(cell(v) for v in row) for row in rows)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',type=Path,default=DEFAULT_ROOT); args=ap.parse_args()
    root=args.root.resolve(); case=root/'2-用例/bird-ca-schools-15'
    assert HERE == (root/'5-评测报告/复算/2026-10-24/bird-semantic-review').resolve()
    truth=json.loads((case/'truth.json').read_text()); questions=json.loads((case/'inputs/questions.json').read_text())
    receipt_path=root/'5-评测报告/复算/2026-10-24/results.json'
    receipt=json.loads(receipt_path.read_text())
    runs=[r for r in receipt['runs'] if r['task']=='bird-ca-schools-15']
    assert len(runs)==8, len(runs)
    sources=[]
    for r in runs:
        p=root/r['source']
        if not (p/'answers.jsonl').is_file(): p=p/'workspace'
        assert (p/'answers.jsonl').is_file(),p
        sources.append(p/'answers.jsonl')
    paths=[case/'truth.json',case/'inputs/questions.json',case/'inputs/db/california_schools.sqlite',receipt_path]+sources
    before={str(p):sha(p) for p in paths}
    con=sqlite3.connect((case/'inputs/db/california_schools.sqlite').as_uri()+'?mode=ro&immutable=1',uri=True)
    con.execute('PRAGMA query_only=ON')
    def auth(action,a,b,db,trigger):
        return sqlite3.SQLITE_OK if action in (sqlite3.SQLITE_SELECT,sqlite3.SQLITE_READ,sqlite3.SQLITE_FUNCTION,sqlite3.SQLITE_RECURSIVE) else sqlite3.SQLITE_DENY
    con.set_authorizer(auth)
    def query(sql): return con.execute(sql).fetchall()
    gold={qid:query(a['sql']) for qid,a in truth['answers'].items()}
    q26free=truth['answers']['26']['sql']
    q26frpm=q26free.replace('Free Meal Count (Ages 5-17)','FRPM Count (Ages 5-17)')
    free=query(q26free); frpm=query(q26frpm)
    condition="(strftime('%Y', s.OpenDate) > '1991' OR strftime('%Y', s.ClosedDate) < '2000')"
    q27left=truth['answers']['27']['sql']
    q27inner=q27left.replace('LEFT JOIN','INNER JOIN')
    q27date=q27left.replace("strftime('%Y', T2.OpenDate) > '1991' OR strftime('%Y', T2.ClosedDate) < '2000'", "T2.OpenDate > '1991-12-31' OR T2.ClosedDate < '2000-01-01'")
    q27rows=gold['27']; q27bag=normalized(q27rows)
    dup=[{'row':list(row),'count':n} for row,n in q27bag.items() if n>1]
    def count(sql): return query(sql)[0][0]
    report={
        'method':'Independent sqlite3 execution; no checker/numeric code imported; ro+immutable+query_only+SELECT authorizer; outputs in dedicated derived-review directory; existing submissions only',
        'root':str(root), 'questions':[q for q in questions if q['question_id'] in (26,27)],
        'q26':{'gold_sql':q26free,'counterfactual_frpm_sql':q26frpm,'free_rows':free,'frpm_rows':frpm,
               'frpm_only_rows':[list(row) for row in (normalized(frpm)-normalized(free)).elements()],
               'school_metric_rows':query("SELECT f.CDSCode,f.`School Name`,f.`Free Meal Count (Ages 5-17)`, f.`FRPM Count (Ages 5-17)` FROM frpm f JOIN schools s ON f.CDSCode=s.CDSCode WHERE s.County='Monterey' AND f.`School Type`='High Schools (Public)' AND f.`FRPM Count (Ages 5-17)`>800")},
        'q27':{'gold_sql':q27left,'gold_rows':len(q27rows),'gold_distinct_raw':len(set(q27rows)),
               'gold_distinct_normalized':len(q27bag),'extra_duplicate_rows':len(q27rows)-len(q27bag),
               'duplicate_groups':len(dup),'duplicate_examples':sorted(dup,key=lambda d:d['count'],reverse=True)[:10],
               'duplicate_groups_with_nonnull_score':sum(d['row'][1]!='<NULL>' for d in dup),
               'inner_rows':len(query(q27inner)),'inner_distinct':len(normalized(query(q27inner))),
               'left_date_predicate_matches':normalized(query(q27date))==q27bag,
               'qualifying_school_count':count('SELECT COUNT(*) FROM schools s WHERE '+condition),
               'unmatched_sat_rows':count('SELECT COUNT(*) FROM schools s LEFT JOIN satscores t ON s.CDSCode=t.cds WHERE '+condition+' AND t.cds IS NULL'),
               'matched_sat_null_write':count('SELECT COUNT(*) FROM schools s JOIN satscores t ON s.CDSCode=t.cds WHERE '+condition+' AND t.AvgScrWrite IS NULL'),
               'null_write_gold_rows':sum(row[1] is None for row in q27rows),
               'qualifying_distinct_cdscode':count('SELECT COUNT(DISTINCT s.CDSCode) FROM schools s WHERE '+condition),
               'duplicated_projection_school_ids':query('SELECT s.CDSCode,s.School,t.AvgScrWrite,s.Phone FROM schools s LEFT JOIN satscores t ON s.CDSCode=t.cds WHERE '+condition+" AND s.School='Community Day' AND t.AvgScrWrite IS NULL LIMIT 10")},
        'runs':[]}
    for r,path in zip(runs,sources):
        entries=[json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        answers={str(e['question_id']):e['sql'] for e in entries}
        assert len(entries)==15 and len(answers)==15 and answers.keys()==gold.keys()
        preds={qid:query(sql) for qid,sql in answers.items()}
        correct={qid:normalized(rows)==normalized(gold[qid]) for qid,rows in preds.items()}
        c=sum(correct.values()); no26=c-int(correct['26']); frpm_ok=normalized(preds['26'])==normalized(frpm)
        frpmc=c-int(correct['26'])+int(frpm_ok)
        def score(n,d):return {'correct':n,'denominator':d,'weighted':round(n/d*100,2),'reward':int(n/d>=truth['threshold'])}
        row={'product':r['product'],'replicate':r['replicate'],'run_id':r['run_id'],'source':str(path.relative_to(root)),
             'answers_sha256':sha(path),'recomputed':score(c,15),'receipt_weighted':r['weighted'],'receipt_reward':r['reward'],
             'receipt_matches_independent':r['weighted']==round(c/15*100,2) and r['reward']==int(c/15>=truth['threshold']),
             'failed_questions':[qid for qid,ok in correct.items() if not ok],
             'exclude_q26':score(no26,14),'replace_q26_frpm':score(frpmc,15),
             'q26_rows':len(preds['26']),'q26_matches_frpm':frpm_ok,
             'q27_sql':answers['27'],'q27_rows':len(preds['27']),'q27_distinct':len(normalized(preds['27'])),
             'q27_pass_multiset':correct['27'],'q27_pass_if_both_deduplicated':set(normalized(preds['27']))==set(q27bag),
             'q27_missing_bag_rows':sum((q27bag-normalized(preds['27'])).values()),
             'q27_extra_bag_rows':sum((normalized(preds['27'])-q27bag).values()),
             'q27_exact_inner_equivalent':normalized(preds['27'])==normalized(query(q27inner))}
        report['runs'].append(row)
    con.close()
    report['headline_changes']={k:sum(row[k]['reward']!=row['recomputed']['reward'] for row in report['runs']) for k in ('exclude_q26','replace_q26_frpm')}
    report['read_only_hash_check']={path:sha(Path(path))==digest for path,digest in before.items()}
    assert all(report['read_only_hash_check'].values())
    assert all(row['receipt_matches_independent'] for row in report['runs'])
    out=HERE/'independent-results.json'; out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    for row in report['runs']:
        print(row['product'],row['replicate'],row['recomputed'], 'exclude26',row['exclude_q26'],'FRPM26',row['replace_q26_frpm'],'q27',row['q27_rows'],row['q27_distinct'])
    print('q26',len(free),len(frpm),'q27',report['q27']['gold_rows'],report['q27']['gold_distinct_raw'],'read-only=',all(report['read_only_hash_check'].values()))
    print('PASS: independent recompute matches all 8 receipts; headline changes',report['headline_changes'])

if __name__=='__main__':main()
