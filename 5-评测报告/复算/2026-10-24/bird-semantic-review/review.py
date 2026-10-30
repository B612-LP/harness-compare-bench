#!/usr/bin/env python3
"""Read-only BIRD q26/q27 semantic review; independent Python table reconstruction.

Writes only this dedicated derived-review directory. No checker imports, grading writes,
model/network/GUI calls. Sensitivity tracks are NOT official regrades.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
from pathlib import Path
import sqlite3

OUT = Path(__file__).resolve().parent
DEFAULT_ROOT = OUT.parents[3]
DEFAULT_OFFICIAL = None  # Retained two-question excerpt is the offline default.


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def norm_cell(x):
    if x is None:
        return '<NULL>'
    if isinstance(x, float):
        return round(x, 6)
    if isinstance(x, (int, bool)):
        return x
    if isinstance(x, bytes):
        return x.hex()
    return str(x).strip()


def bag(rows):
    return Counter(tuple(norm_cell(x) for x in row) for row in rows)


def summary(rows):
    counts = bag(rows)
    return {'rows': len(rows), 'distinct_projected_rows': len(counts),
            'duplicate_excess_rows': len(rows) - len(counts),
            'sha256_normalized_multiset': hashlib.sha256(json.dumps(
                sorted([(list(k), v) for k, v in counts.items()], key=repr),
                ensure_ascii=False, sort_keys=True).encode()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--official-source', type=Path, default=DEFAULT_OFFICIAL)
    args = parser.parse_args()
    root = args.repo.resolve()
    assert OUT == (root / '5-评测报告/复算/2026-10-24/bird-semantic-review').resolve(), 'unexpected derived output directory'
    case = root / '2-用例/bird-ca-schools-15'
    db = case / 'inputs/db/california_schools.sqlite'
    original_results = root / '5-评测报告/复算/2026-10-24/results.json'
    truth = load(case / 'truth.json')
    questions = {str(q['question_id']): q for q in load(case / 'inputs/questions.json')}
    grading = load(original_results)
    runs = [r for r in grading['runs'] if r['task'] == 'bird-ca-schools-15']
    assert len(runs) == 8
    protected = [db, case / 'truth.json', case / 'checker.py', case / 'spec.md',
                 case / 'inputs/questions.json', case / 'inputs/schema.sql', original_results]
    artifacts = {}
    for run in runs:
        source = root / run['source']
        candidates = [source / 'answers.jsonl', source / 'workspace/answers.jsonl',
                      source / 'output/answers.jsonl', source / 'outputs/answers.jsonl']
        present = [p for p in candidates if p.is_file()]
        assert len(present) == 1, (run['run_id'], present)
        artifacts[run['run_id']] = present[0]
        protected.append(present[0])
    before_hashes = {str(p.relative_to(root)): sha(p) for p in protected}

    reference = OUT / 'upstream-q26-q27.json'
    if args.official_source is not None and args.official_source.is_file():
        official_raw = load(args.official_source)
        selected = [q for q in official_raw if q.get('db_id') == 'california_schools'
                    and q.get('question_id') in (26, 27)]
        assert len(selected) == 2
        snapshot = {'provenance': 'local previously downloaded BIRD mini_dev; no new upstream retrieval',
                    'original_path': str(args.official_source.resolve()),
                    'original_file_sha256': sha(args.official_source), 'questions': selected}
        if reference.exists():
            assert load(reference) == snapshot, 'do not silently replace official reference'
        else:
            reference.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n')
    else:
        assert reference.is_file(), 'supply --official-source or retained upstream-q26-q27.json'
        snapshot = load(reference)
    source_comparison = {}
    for q in snapshot['questions']:
        qid = str(q['question_id'])
        source_comparison[qid] = {
            'official': q, 'localized': questions[qid], 'gold_sql': truth['answers'][qid]['sql'],
            'sql_exactly_matches_local_official': q['SQL'] == truth['answers'][qid]['sql'],
            'english_question_exact_match': q['question'] == questions[qid]['question_en_original'],
            'english_evidence_exact_match': q['evidence'] == questions[qid]['evidence_en_original']}

    conn = sqlite3.connect(db.as_uri() + '?mode=ro&immutable=1', uri=True)
    conn.execute('PRAGMA query_only=ON')
    def authorizer(action, a, b, database, trigger):
        return sqlite3.SQLITE_OK if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE) else sqlite3.SQLITE_DENY
    conn.set_authorizer(authorizer)
    conn.row_factory = sqlite3.Row
    def sql_rows(sql):
        return [tuple(row) for row in conn.execute(sql)]
    tables = {name: [dict(row) for row in conn.execute('SELECT * FROM ' + name)]
              for name in ('schools', 'frpm', 'satscores')}
    schools = {r['CDSCode']: r for r in tables['schools']}
    frpm = {r['CDSCode']: r for r in tables['frpm']}
    sat = {r['cds']: r for r in tables['satscores']}
    assert all(len(tables[name]) == len(idx) for name, idx in
               (('schools', schools), ('frpm', frpm), ('satscores', sat)))
    table_stats = {name: {'rows': len(rows), 'unique_primary_keys': len(rows)} for name, rows in tables.items()}

    # Independent reconstruction from base rows, not execution of gold vs itself.
    q26_candidates = []
    q26_python = {'free_only': [], 'free_or_reduced': []}
    for code, f in frpm.items():
        s = schools.get(code)
        if not s or s['County'] != 'Monterey' or f['School Type'] != 'High Schools (Public)':
            continue
        projected = (f['School Name'], s['Street'], s['City'], s['State'], s['Zip'])
        record = {key: s[key] for key in ('CDSCode', 'School', 'County', 'Street', 'City', 'State', 'Zip',
                                          'MailStreet', 'MailCity', 'MailState', 'MailZip')}
        record.update({key: f[key] for key in ('School Name', 'County Name', 'School Type',
                                              'Free Meal Count (Ages 5-17)', 'FRPM Count (Ages 5-17)')})
        record['free_over_800'] = f['Free Meal Count (Ages 5-17)'] is not None and f['Free Meal Count (Ages 5-17)'] > 800
        record['frpm_over_800'] = f['FRPM Count (Ages 5-17)'] is not None and f['FRPM Count (Ages 5-17)'] > 800
        q26_candidates.append(record)
        if record['free_over_800']:
            q26_python['free_only'].append(projected)
        if record['frpm_over_800']:
            q26_python['free_or_reduced'].append(projected)
    q26_sql = {
        'free_only': "SELECT f.`School Name`,s.Street,s.City,s.State,s.Zip FROM schools s JOIN frpm f ON f.CDSCode=s.CDSCode WHERE s.County='Monterey' AND f.`School Type`='High Schools (Public)' AND f.`Free Meal Count (Ages 5-17)`>800",
        'free_or_reduced': "SELECT f.`School Name`,s.Street,s.City,s.State,s.Zip FROM schools s JOIN frpm f ON f.CDSCode=s.CDSCode WHERE s.County='Monterey' AND f.`School Type`='High Schools (Public)' AND f.`FRPM Count (Ages 5-17)`>800",
    }
    for key in q26_sql:
        assert bag(q26_python[key]) == bag(sql_rows(q26_sql[key]))
    q26_free = q26_python['free_only']
    q26_frpm = q26_python['free_or_reduced']
    county_disagreements = [code for code, f in frpm.items() if code in schools
                           and ((f['County Name'] == 'Monterey') != (schools[code]['County'] == 'Monterey'))]
    q26 = {'independent_method': 'filter base frpm/schools rows in Python and project required columns; separately cross-check SQL',
           'candidate_schools': sorted(q26_candidates, key=lambda x: x['CDSCode']),
           'free_only': dict(summary(q26_free), projected_rows=q26_free),
           'free_or_reduced': dict(summary(q26_frpm), projected_rows=q26_frpm),
           'frpm_not_free_rows': list((bag(q26_frpm) - bag(q26_free)).elements()),
           'county_filter_disagreement_keys': county_disagreements,
           'selected_frpm_vs_schools_name_mismatches': [r for r in q26_candidates if r['frpm_over_800'] and r['School Name'] != r['School']],
           'selected_physical_vs_mail_address_mismatches': [r for r in q26_candidates if r['frpm_over_800'] and
               (r['Street'], r['City'], r['State'], r['Zip']) != (r['MailStreet'], r['MailCity'], r['MailState'], r['MailZip'])],
           'sql': q26_sql}

    # SQL dates are independently interpreted as complete calendar years.
    invalid_dates = []
    def year(value):
        if value is None:
            return None
        try:
            return date.fromisoformat(value).year
        except (ValueError, TypeError):
            invalid_dates.append(value)
            return None
    selected_schools = []
    for s in tables['schools']:
        opened, closed = year(s['OpenDate']), year(s['ClosedDate'])
        if (opened is not None and opened > 1991) or (closed is not None and closed < 2000):
            selected_schools.append(s)
    q27_python = {'left_exact': [], 'inner_exact': [], 'left_zero_padded': [], 'inner_zero_padded': []}
    provenance = defaultdict(list)
    padded_matches = []
    for s in selected_schools:
        t = sat.get(s['CDSCode'])
        exact = (s['School'], t['AvgScrWrite'] if t else None, s['Phone'])
        q27_python['left_exact'].append(exact)
        if t:
            q27_python['inner_exact'].append(exact)
        provenance[exact].append({key: s[key] for key in ('CDSCode', 'School', 'Phone', 'County', 'District', 'OpenDate', 'ClosedDate')} | {
            'satscores_cds': t['cds'] if t else None, 'AvgScrWrite': t['AvgScrWrite'] if t else None})
        matches = [row for key, row in sat.items() if key == s['CDSCode'] or '0' + key == s['CDSCode']]
        assert len(matches) <= 1, 'zero padding creates fan-out'
        u = matches[0] if matches else None
        padded = (s['School'], u['AvgScrWrite'] if u else None, s['Phone'])
        q27_python['left_zero_padded'].append(padded)
        if u:
            q27_python['inner_zero_padded'].append(padded)
        if u and not t:
            padded_matches.append({key: s[key] for key in ('CDSCode', 'School', 'County', 'District')} | {
                'satscores_cds': u['cds'], 'satscores_sname': u['sname'], 'rtype': u['rtype'], 'AvgScrWrite': u['AvgScrWrite']})
    where = "(strftime('%Y',s.OpenDate)>'1991' OR strftime('%Y',s.ClosedDate)<'2000')"
    q27_sql = {}
    for key, join, on in (
        ('left_exact', 'LEFT JOIN', 's.CDSCode=t.cds'),
        ('inner_exact', 'INNER JOIN', 's.CDSCode=t.cds'),
        ('left_zero_padded', 'LEFT JOIN', "s.CDSCode=t.cds OR s.CDSCode='0'||t.cds"),
        ('inner_zero_padded', 'INNER JOIN', "s.CDSCode=t.cds OR s.CDSCode='0'||t.cds")):
        q27_sql[key] = f'SELECT s.School,t.AvgScrWrite,s.Phone FROM schools s {join} satscores t ON ({on}) WHERE {where}'
        assert bag(q27_python[key]) == bag(sql_rows(q27_sql[key])), key
    q27_sql['left_distinct'] = q27_sql['left_exact'].replace('SELECT ', 'SELECT DISTINCT ', 1)
    distinct_rows = sql_rows(q27_sql['left_distinct'])
    assert bag(distinct_rows) == Counter({k: 1 for k in bag(q27_python['left_exact'])})
    duplicates = [{'projected_row': key, 'count': len(group), 'source_schools': group}
                  for key, group in provenance.items() if len(group) > 1]
    q27 = {'independent_method': 'Python date-year filtering on schools, dictionary exact/zero-padded joins, provenance-grouped projection; independent SQL cross-check',
           'invalid_non_null_dates': sorted(set(invalid_dates)), 'selected_school_count': len(selected_schools),
           'variants': {key: dict(summary(rows), null_score_rows=sum(r[1] is None for r in rows),
                                   non_null_score_rows=sum(r[1] is not None for r in rows))
                        for key, rows in q27_python.items()},
           'left_distinct': summary(distinct_rows), 'duplicate_projection_groups': duplicates,
           'duplicates_all_distinct_school_keys': all(len({r['CDSCode'] for r in g['source_schools']}) == g['count'] for g in duplicates),
           'duplicates_all_missing_exact_sat': all(r['satscores_cds'] is None for g in duplicates for r in g['source_schools']),
           'duplicates_all_null_score_and_phone': all(g['projected_row'][1:] == (None, None) for g in duplicates),
           'missing_exact_sat_rows': sum(s['CDSCode'] not in sat for s in selected_schools),
           'padded_recovered_matches': padded_matches,
           'padded_name_matches_exact': sum(r['School'] == r['satscores_sname'] for r in padded_matches),
           'rtype_exact_counts': dict(Counter(sat[s['CDSCode']]['rtype'] for s in selected_schools if s['CDSCode'] in sat)),
           'rtype_padded_counts': dict(Counter(r['rtype'] for r in padded_matches)), 'sql': q27_sql}

    # All-15 base recomputation verifies frozen reference grades, not general gold semantics.
    gold_rows = {qid: sql_rows(meta['sql']) for qid, meta in truth['answers'].items()}
    assert bag(gold_rows['26']) == bag(q26_free)
    assert bag(gold_rows['27']) == bag(q27_python['left_exact'])
    impact = []
    def track(correct, n, gates):
        return {'correct': correct, 'n_questions': n, 'weighted': round(correct / n * 100, 2),
                'reward': int(gates and correct / n >= .8), 'threshold': .8}
    for run in runs:
        artifact = artifacts[run['run_id']]
        rows = [json.loads(line) for line in artifact.read_text().splitlines() if line.strip()]
        predictions = {str(r['question_id']): r['sql'] for r in rows}
        assert len(rows) == len(predictions) == 15 and set(predictions) == set(gold_rows)
        outputs = {qid: sql_rows(sql) for qid, sql in predictions.items()}
        hits = {qid: bag(output) == bag(gold_rows[qid]) for qid, output in outputs.items()}
        correct = sum(hits.values())
        frozen_grade = run['strict']
        assert correct == frozen_grade['correct']
        assert all(hits[c['id'][1:]] == c['pass'] for c in frozen_grade['checks'] if c['id'].startswith('q'))
        gates = all(c['pass'] for c in frozen_grade['checks'] if not c['id'].startswith('q'))
        original = track(correct, 15, gates)
        assert original['weighted'] == run['weighted'] and original['reward'] == run['reward']
        frpm_hit = bag(outputs['26']) == bag(q26_frpm)
        sensitivities = {
            'exclude_q26_14_questions': track(correct - int(hits['26']), 14, gates),
            'q26_frpm_counterfactual_15_questions': track(correct - int(hits['26']) + int(frpm_hit), 15, gates)}
        q27_compare = {key: bag(outputs['27']) == bag(variant) for key, variant in q27_python.items()}
        q27_compare['left_distinct'] = bag(outputs['27']) == bag(distinct_rows)
        impact.append({'run_id': run['run_id'], 'product': run['product'], 'replicate': run['replicate'],
                       'artifact': str(artifact.relative_to(root)), 'artifact_sha256': sha(artifact),
                       'frozen_original_15': original, **sensitivities, 'all15_frozen_question_pass': hits,
                       'q26': {'sql': predictions['26'], **summary(outputs['26']), 'gold_pass': hits['26'],
                               'frpm_counterfactual_pass': frpm_hit},
                       'q27': {'sql': predictions['27'], **summary(outputs['27']), 'variant_matches': q27_compare}})
    conn.close()
    after_hashes = {str(p.relative_to(root)): sha(p) for p in protected}
    assert before_hashes == after_hashes, 'protected repository sources changed during review'
    assertions = {
        'read_only_sqlite_uri_and_query_only': True, 'independent_python_sql_crosschecks': True,
        'gold_source_question_evidence_exactly_match_local_official': all(all(v[k] for k in
              ('sql_exactly_matches_local_official','english_question_exact_match','english_evidence_exact_match')) for v in source_comparison.values()),
        'q26_counts_free5_frpm6': len(q26_free) == 5 and len(q26_frpm) == 6,
        'q27_no_primary_key_join_fanout': len(q27_python['left_exact']) == len(selected_schools),
        'q27_distinct_removes357': len(q27_python['left_exact']) - len(distinct_rows) == 357,
        'q27_inner749_padded813': len(q27_python['inner_exact']) == 749 and len(q27_python['inner_zero_padded']) == 813,
        'all8_frozen_grades_independently_reproduced': len(impact) == 8,
        'all8_q26_match_frpm_not_free': all(r['q26']['frpm_counterfactual_pass'] and not r['q26']['gold_pass'] for r in impact),
        'no_source_mutation': before_hashes == after_hashes, 'new_agent_runs_zero': True}
    assert all(assertions.values()), assertions
    result = {'schema_version': 'bird-semantic-review-v1', 'new_agent_runs': 0,
              'repo': str(root), 'sqlite': sqlite3.sqlite_version, 'policy': {
                  'formal_grade_replaced': False, 'sensitivity_not_official_grade': True,
                  'q27_sensitivity_not_used_to_award_points': True,
                  'local_official_source_is_not_new_upstream_verification': True},
              'source_hashes_before': before_hashes, 'source_hashes_after': after_hashes,
              'official_reference_sha256': sha(reference), 'source_comparison': source_comparison,
              'tables': table_stats, 'q26': q26, 'q27': q27, 'sample_sensitivity': impact, 'assertions': assertions}
    (OUT / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    report = ['BIRD semantic review (NOT formal regrade), new agent runs=0',
              f'Independent assertions: {sum(assertions.values())}/{len(assertions)}',
              f'q26 Free Meal={len(q26_free)} vs FRPM={len(q26_frpm)}',
              f"q27 LEFT={q27['variants']['left_exact']['rows']} DISTINCT={len(distinct_rows)} INNER={q27['variants']['inner_exact']['rows']} padded-INNER={q27['variants']['inner_zero_padded']['rows']}"]
    for r in impact:
        report.append(f"{r['product']} {r['replicate']}: frozen={r['frozen_original_15']} exclude26={r['exclude_q26_14_questions']} FRPM26={r['q26_frpm_counterfactual_15_questions']}")
    (OUT / 'review.stdout.txt').write_text('\n'.join(report) + '\n')
    print('\n'.join(report))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
