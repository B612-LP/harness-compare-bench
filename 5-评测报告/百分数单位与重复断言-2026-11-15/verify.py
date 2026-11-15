"""Independent research SELECTs; Python 3.9+ standard library, read-only.
Not a candidate executor, historical checker, or original-trace authenticator.
"""
import hashlib
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
INPUTS = {
    '2-用例/bird-ca-schools-15/inputs/db/california_schools.sqlite': 'a9e7d92a47c0d247d76a7a4acd76a4764f430f4d711e9e6809f399a9bf72322d',
    '2-用例/bird-ca-schools-15/inputs/questions.json': '144bf7c36b58ab261f44676618a80af9f9d642fd287a4d2885c0cd7d53543f3e',
    '2-用例/bird-ca-schools-15/inputs/schema.sql': '33411f4b8db97a1a703876a6142d070625d9e7f6ea1e63251a981da67826dd0d',
    '2-用例/bird-ca-schools-15/truth.json': 'c5bb7999079ac8f1711049d81392729edf127a27134d32a905ca39de15b8ea19',
    '3-表现现场/r20261101-wb-n3/runs/bird-ca-schools-15/run-bird-ca-schools-15__r1.json': '2e46d709f7f01a2b025085b5456672a7785f7f3afa400d2332d5ea9a093a12f2',
    '3-表现现场/r20261101-wb-n3/runs/bird-ca-schools-15/run-bird-ca-schools-15__r2.json': '1753c56395c7b6c21b7ff3f1f1373806b985a136b5038485bf2c86863263665a',
    '3-表现现场/r20261101-wb-n3/runs/bird-ca-schools-15/run-bird-ca-schools-15__r3.json': '6ad05af430fd5f4efc19a9b5a28aaa27dffeb48fd564ee008c7afd46a8c5cadd',
    '5-评测报告/断言级重复性-diff-2026-11-02/r20261101-wb-n3-assertion-diff.json': 'e9ce4ec41b6ccdd84290a87d92be9828d52cdf99853b7f8914543633f36d8635',
    '5-评测报告/断言级重复性-diff-2026-11-02/README.md': 'f0e93aa962ca6f4e61ee44f36c1ef5fa656cac4190f2233e76bf00dff8cb39b4',
}
FORMULAS = {
    '18%': 'free * 1.0 / enroll',
    '0.18%': 'CAST(free AS REAL) * 100 / enroll',
    'uncast_percent': 'free * 100 / enroll',
}
BASE = {
    'F': '''SELECT f.CDSCode AS code, f."Free Meal Count (K-12)" AS free,
            f."Enrollment (K-12)" AS enroll, NULL AS school
            FROM frpm AS f
            WHERE f."County Name" = 'Los Angeles' AND f."Charter School (Y/N)" = 0''',
    'J': '''SELECT f.CDSCode AS code, f."Free Meal Count (K-12)" AS free,
            f."Enrollment (K-12)" AS enroll, s.School AS school
            FROM frpm AS f INNER JOIN schools AS s ON s.CDSCode = f.CDSCode
            WHERE s.County = 'Los Angeles' AND s.Charter = 0''',
}

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def require(condition, message):
    if not condition:
        raise ValueError(message)

def typed_equal(left, right):
    """Unlike Python equality: bool/int and int/float are distinct."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(typed_equal(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(typed_equal(a, b) for a, b in zip(left, right))
    return left == right

def row_key(code):
    require(type(code) is str, 'CDSCode must be text, not coerced')
    return hashlib.sha256(('q62-row-v1:' + code).encode('utf-8')).hexdigest()

def histogram(rows):
    counts = Counter(tuple(row) for row in rows)
    return [{'types': list(k), 'n': counts[k]} for k in sorted(counts)]

def classify(cells):
    names = ['F18%', 'F0.18%', 'J18%', 'J0.18%']
    if not isinstance(cells, dict) or any(k not in cells for k in names):
        return 'unknown'
    for k in names:
        cell = cells[k]
        if not isinstance(cell, dict) or type(cell.get('row_keys')) is not list:
            return 'unknown'
        keys, counts = cell['row_keys'], cell.get('counts')
        if any(type(key) is not str for key in keys) or keys != sorted(keys) or type(counts) is not dict:
            return 'unknown'
        if any(type(counts.get(name)) is not int or counts[name] < 0 for name in ('star','CDSCode')):
            return 'unknown'
        if counts['star'] != len(keys) or counts['CDSCode'] > counts['star']:
            return 'unknown'
        school = counts.get('School')
        if k.startswith('F'):
            if 'School' not in counts or school is not None:
                return 'unknown'
        elif type(school) is not int or not 0 <= school <= counts['star']:
            return 'unknown'
    same = all(cells['F'+u]['row_keys'] == cells['J'+u]['row_keys'] for u in ['18%', '0.18%'])
    counts_equal = all(cells['J'+u]['counts']['star'] == cells['J'+u]['counts']['School'] for u in ['18%', '0.18%'])
    return 'fixed_database_unit_numeric_decomposition' if same and counts_equal else 'table_or_count_contribution'

def study(conn):
    cells = {}; populations = {}; variants = {}
    for scope, base in BASE.items():
        population = conn.execute('WITH b AS ('+base+') SELECT code, free, enroll, typeof(free), typeof(enroll) FROM b ORDER BY code').fetchall()
        populations[scope] = {
            'rows': len(population),
            'types': histogram([r[3:5] for r in population]),
            'null_free': sum(r[1] is None for r in population),
            'null_enroll': sum(r[2] is None for r in population),
            'zero_enroll': sum(r[2] == 0 for r in population),
        }
        for unit, formula in FORMULAS.items():
            prefix = 'WITH b AS ('+base+'), v AS (SELECT *, '+formula+' AS value FROM b) '
            rows = conn.execute(prefix+'SELECT code, school, typeof(value) FROM v WHERE value < 0.18 ORDER BY code').fetchall()
            count_row = conn.execute(prefix+'SELECT COUNT(*), COUNT(code), COUNT(school) FROM v WHERE value < 0.18').fetchone()
            entry = {
                'row_keys': sorted(row_key(r[0]) for r in rows),
                'counts': {'star': count_row[0], 'CDSCode': count_row[1], 'School': count_row[2] if scope == 'J' else None},
                'School_count_status': 'available' if scope == 'J' else 'unavailable_in_F',
                'School_null_row_keys': sorted(row_key(r[0]) for r in rows if scope == 'J' and r[1] is None),
                'selected_value_types': histogram([(r[2],) for r in rows]),
                'all_value_types': histogram(conn.execute(prefix+'SELECT typeof(value) FROM v').fetchall()),
                'null_value': conn.execute(prefix+'SELECT COUNT(*) FROM v WHERE value IS NULL').fetchone()[0],
                'equal_boundary': conn.execute(prefix+'SELECT COUNT(*) FROM v WHERE value = 0.18').fetchone()[0],
            }
            if unit == 'uncast_percent':
                variants[scope] = entry
            else:
                cells[scope+unit] = entry
    diffs = {}
    for unit in ['18%', '0.18%']:
        f = set(cells['F'+unit]['row_keys']); j = set(cells['J'+unit]['row_keys'])
        diffs[unit] = {'F_only': sorted(f-j), 'J_only': sorted(j-f),
                       'same_multiset': cells['F'+unit]['row_keys'] == cells['J'+unit]['row_keys']}
    n = {key: value['counts']['star'] for key, value in cells.items()}
    decomposition = {
        'filter_then_unit': [n['J18%']-n['F18%'], n['J0.18%']-n['J18%']],
        'unit_then_filter': [n['F0.18%']-n['F18%'], n['J0.18%']-n['F0.18%']],
        'interaction': (n['J0.18%']-n['J18%'])-(n['F0.18%']-n['F18%']),
    }
    all_types = conn.execute('SELECT typeof("Free Meal Count (K-12)"), typeof("Enrollment (K-12)") FROM frpm').fetchall()
    coverage = conn.execute('''SELECT COUNT(*), SUM(s.CDSCode IS NULL),
        SUM(s.Charter IS NOT f."Charter School (Y/N)"), SUM(s.County IS NOT f."County Name")
        FROM frpm f LEFT JOIN schools s ON s.CDSCode=f.CDSCode''').fetchone()
    return {'cells': cells, 'populations': populations, 'differences': diffs,
            'decomposition': decomposition, 'branch': classify(cells),
            'uncast_percent': variants,
            'uncast_same_as_cast': {s: typed_equal(variants[s], cells[s+'0.18%']) for s in BASE},
            'all_frpm_types': histogram(all_types),
            'all_frpm_link_audit': {'frpm_rows': coverage[0], 'missing_school_key': coverage[1],
                'charter_distinct_including_null': coverage[2], 'county_distinct_including_null': coverage[3]}}

def negative_controls():
    """Synthetic counterexamples only; writes confined to transient :memory:."""
    cases = {
        'unit': [('u',1,100,0,0,'school',True)],
        'School_NULL': [('n',0,100,0,0,None,True)],
        'charter_conflict': [('c',1,100,0,1,'school',True)],
        'join_missing': [('m',0,100,0,0,'school',False)],
        'equal_count_distinct_rows': [('a',0,100,0,1,'school',True),('b',0,100,1,0,'school',True)],
        'integer_vs_real': [('i',1,500,0,0,'school',True),('r',1.0,500.0,0,0,'school',True)],
        'null_zero': [('nf',None,100,0,0,'school',True),('ne',1,None,0,0,'school',True),('z',1,0,0,0,'school',True)],
        'strict_equality': [('r',18,100,0,0,'school',True),('p',9,5000,0,0,'school',True)],
    }
    output = {}
    for name, rows in cases.items():
        c = sqlite3.connect(':memory:')
        try:
            c.execute('CREATE TABLE frpm (CDSCode TEXT PRIMARY KEY, "County Name", "Charter School (Y/N)", "Free Meal Count (K-12)", "Enrollment (K-12)")')
            c.execute('CREATE TABLE schools (CDSCode TEXT PRIMARY KEY, County, Charter, School)')
            for key, free, enroll, fc, sc, school, joined in rows:
                c.execute('INSERT INTO frpm VALUES (?,?,?,?,?)', (key,'Los Angeles',fc,free,enroll))
                if joined:
                    c.execute('INSERT INTO schools VALUES (?,?,?,?)', (key,'Los Angeles',sc,school))
            r = study(c)
            output[name] = {'branch':r['branch'], 'counts':{k:x['counts'] for k,x in r['cells'].items()},
                'differences':r['differences'], 'decomposition':r['decomposition'],
                'uncast_same_as_cast':r['uncast_same_as_cast'],
                'null_value':{k:x['null_value'] for k,x in r['cells'].items()},
                'equal_boundary':{k:x['equal_boundary'] for k,x in r['cells'].items()}}
        finally:
            c.close()
    output['missing_matrix'] = {'branch':classify({})}
    return output

def check_inputs(root=ROOT):
    observed = {}
    for rel, expected in INPUTS.items():
        path = root / rel
        require(path.is_file() and not path.is_symlink(), 'missing/nonregular source: '+rel)
        observed[rel] = digest(path)
        require(observed[rel] == expected, 'source hash mismatch: '+rel)
    return observed

def canonical_study(root=ROOT):
    before = check_inputs(root)
    db = root / next(iter(INPUTS))
    conn = sqlite3.connect(db.resolve().as_uri()+'?mode=ro&immutable=1', uri=True)
    try:
        conn.execute('PRAGMA query_only=ON')
        require(conn.execute('PRAGMA query_only').fetchone() == (1,), 'query_only unavailable')
        # Defense in depth: research operations may only read, select, or invoke functions.
        allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}
        conn.set_authorizer(lambda op, a, b, c, d: sqlite3.SQLITE_OK if op in allowed else sqlite3.SQLITE_DENY)
        result = study(conn)
    finally:
        conn.close()
    require(typed_equal(before, check_inputs(root)), 'source changed during query')
    return result

def verify(package=HERE, root=ROOT):
    manifest = json.loads((package/'SHA256.json').read_text(encoding='utf-8'))
    require(type(manifest) is dict and set(manifest) == {'report.md','evidence.json','results.json','controls.json','verify.py','test_verify.py'}, 'manifest members')
    for name, expected in manifest.items():
        require(type(expected) is str and digest(package/name) == expected, 'package hash mismatch: '+name)
    result = canonical_study(root)
    expected = json.loads((package/'results.json').read_text(encoding='utf-8'))
    require(typed_equal(result, expected), 'typed result mismatch')
    controls = json.loads((package/'controls.json').read_text(encoding='utf-8'))
    require(typed_equal(controls, negative_controls()), 'typed negative control mismatch')
    evidence = json.loads((package/'evidence.json').read_text(encoding='utf-8'))
    require(typed_equal(evidence['q62_pass'], [False, True, True]), 'historical assertion mismatch')
    require(evidence['source_authentication'] == 'current_byte_chain_only', 'authenticity overclaim')
    old = json.loads((root/'5-评测报告/断言级重复性-diff-2026-11-02/r20261101-wb-n3-assertion-diff.json').read_text(encoding='utf-8'))['cases']['bird-ca-schools-15']
    require(typed_equal([old['per_id']['q62']['bird-ca-schools-15 r'+str(i)] for i in (1,2,3)], evidence['q62_pass']), 'old assertion mismatch')
    for i in (1,2,3):
        rec = json.loads((root/('3-表现现场/r20261101-wb-n3/runs/bird-ca-schools-15/run-bird-ca-schools-15__r'+str(i)+'.json')).read_text(encoding='utf-8'))
        require(rec['grading_execution_receipt_sha256'] == evidence['source_anchors'][i-1]['anchors']['execution']['sha256'], 'execution anchor mismatch')
        require(typed_equal(rec['grade']['weighted'], evidence['historical_weighted'][i-1]), 'historical weighted mismatch')
    return result

if __name__ == '__main__':
    try:
        r = verify()
        print(json.dumps({'status':'PASS', 'branch':r['branch'], 'counts':{k:v['counts'] for k,v in r['cells'].items()}}, ensure_ascii=False, sort_keys=True))
    except Exception as exc:
        print('FAIL CLOSED: '+type(exc).__name__+': '+str(exc), file=sys.stderr)
        sys.exit(2)
