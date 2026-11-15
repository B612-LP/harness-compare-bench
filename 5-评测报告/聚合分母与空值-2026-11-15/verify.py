#!/usr/bin/env python3
"""q25 事后、匿名、只读比较；不执行存档 SQL，不重判历史成绩。"""
from collections import Counter, defaultdict
import hashlib
import json
import re
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[2]
CASE = '2-用例/bird-ca-schools-15/'
R2 = '3-表现现场/r1109-mech-n3/runs/codex__bird-ca-schools-15__r2/'
A1 = '3-表现现场/r1030-formal-a1/runs/dsh__bird-ca-schools-15/'
DB = CASE + 'inputs/db/california_schools.sqlite'
SOURCES = {
    DB: 'a9e7d92a47c0d247d76a7a4acd76a4764f430f4d711e9e6809f399a9bf72322d',
    CASE+'inputs/questions.json': '144bf7c36b58ab261f44676618a80af9f9d642fd287a4d2885c0cd7d53543f3e',
    CASE+'truth.json': 'c5bb7999079ac8f1711049d81392729edf127a27134d32a905ca39de15b8ea19',
    CASE+'checker.py': 'ffa7389adef32779686bbe56aef7d711db1d8d1c191ff5dd389310e6c01d1910',
    '3-表现现场/r1109-mech-n3/frozen-checkers/bird-ca-schools-15/checker.py': '994be0b3b766e457b5b7d91de6b1ef814dbd6886c9e4a4f9ee63cded69abca54',
    R2+'workspace/answers.jsonl': 'abf13eaecff5df8a8ffda14eb5856bb1744a616c1d505768e8038f2519182467',
    R2+'checker.stdout.json': '907ebf5b23478e1cddfa6a2e15559819228b719d5563ddd07e3eeb0c0f33616e',
    R2+'score-receipt.json': 'aceec87112f54391f0a3abb351c01c9991e8f108dd7deae396497aadc8f66243',
    R2+'adjudication.json': '96a7b750aff79ef2f7ccd511f7b4229fcab9f56f5219705694496bec3c3c0953',
    '3-表现现场/r1109-mech-n3/reviews/lead-integrity-review.json': 'b92e9c26e6e8b08f192e6fa7d2780576c61b5a915470b5a126e439f551db5cae',
    '3-表现现场/r1109-mech-n3/README.md': 'a7d471b5d001f96237d099d3341ac586df89702abfae3dadf7a48cfbd78effa3',
    A1+'workspace/answers.jsonl': '621074e36e5fc555fa785cb591ba51c4acdc720b3c47ad3e9f012fc5200fcd28',
    A1+'checker.stdout.json': '1e2b108af604ae1947b11f289610c82fc22666173a4d4506b24c1291321af6cb',
}
SQL_SHA = ('248d3c64ba0e6da7dfccd4e070114160057525e6e9c678b1d3094ccedc7910cb',
           '8bd694473414965f0253390b7d577af1e3e4282492ee7edce8928aa51d053ef5',
           '2e34da11dd31146a43a60d89dc83d4e97b7044737429174eb6ac6a2daa1d2cae')
# 人工编写的固定 SELECT：只读目标前缀 JOIN，返回进程内部数据，不输出明细。
# 相关子查询以完整地区名为单位而非整前缀；LIKE 由 SQLite 计算以匹配其大小写规则。
FIXED_SELECT = '''SELECT s.cds, s.sname, f.`Charter Funding Type`, s.AvgScrMath,
       f.`District Name`, s.dname LIKE (?||'%'),
       (SELECT AVG(s2.AvgScrMath) FROM satscores s2 JOIN frpm f2
        ON s2.cds=f2.CDSCode WHERE f2.`District Name`=f.`District Name`),
       f.`District Name` LIKE (?||'%')
FROM satscores s JOIN frpm f ON s.cds=f.CDSCode
WHERE f.`District Name` LIKE (?||'%')
   OR s.dname LIKE (?||'%')'''

class VerificationError(Exception):
    pass

def require(condition, reason):
    if not condition:
        raise VerificationError(reason)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def read_sources(root=ROOT):
    found = {}
    for rel, expected in SOURCES.items():
        if rel == DB:
            continue
        try:
            data = (root / rel).read_bytes()
        except OSError:
            raise VerificationError('source unavailable') from None
        require(digest(data) == expected, 'source hash mismatch')
        found[rel] = data
    return found

def json_source(data, rel):
    return json.loads(data[rel])

def unique_q25(data, rel):
    entries = [json.loads(x) for x in data[rel].splitlines() if x.strip()]
    selected = [x for x in entries if x.get('question_id') == 25]
    require(len(selected) == 1 and set(selected[0]) == {'question_id', 'sql'}, 'q25 identity')
    return selected[0]['sql']

def check_receipt(obj, passed, note):
    checks = [x for x in obj['checks'] if x.get('id') == 'q25']
    require(len(checks) == 1 and checks[0]['pass'] is passed and checks[0]['note'] == note,
            'receipt mismatch')

def check_sources(data):
    truth = json_source(data, CASE+'truth.json')
    questions = json_source(data, CASE+'inputs/questions.json')
    require(sum(q.get('question_id') == 25 for q in questions) == 1, 'question identity')
    require(truth['input_sha256']['inputs/db/california_schools.sqlite'] == SOURCES[DB], 'truth db mismatch')
    sqls = (truth['answers']['25']['sql'], unique_q25(data, R2+'workspace/answers.jsonl'),
            unique_q25(data, A1+'workspace/answers.jsonl'))
    require(tuple(digest(x.encode()) for x in sqls) == SQL_SHA, 'sql identity')
    r2 = json_source(data, R2+'checker.stdout.json')
    receipt = json_source(data, R2+'score-receipt.json')
    a1 = json_source(data, A1+'checker.stdout.json')
    require(receipt['raw_checker_output'] == r2, 'receipt stdout mismatch')
    require(receipt['case'] == 'bird-ca-schools-15' and receipt['product'] == 'codex'
            and receipt['rep'] == 2 and receipt['score']['checker_sha256'] == SOURCES['3-表现现场/r1109-mech-n3/frozen-checkers/bird-ca-schools-15/checker.py'], 'receipt identity')
    check_receipt(r2, False, '行数 12 vs gold 6')
    check_receipt(a1, True, '行集一致（6 行）')
    review = json_source(data, '3-表现现场/r1109-mech-n3/reviews/lead-integrity-review.json')
    require(review['verdicts']['codex__bird-ca-schools-15__r2']['final_adjudication'] == 'valid', 'review identity')
    # 收据无已判 answers 内容哈希；同地址复用不等于同文件时序已证明。
    return {'recorded_r2_rows_vs_gold': [12, 6], 'recorded_a1_q25_pass_rows': 6,
            'r2_original_draft': 'infrastructure_invalid', 'r2_lead_final': 'valid',
            'historic_answer_to_receipt_binding': 'unknown_no_answer_hash_or_archival_timing_proof',
            'address_reuse': 'documented_not_unique_identity'}

def reject_sidecars(path):
    for suffix in ('-wal', '-shm', '-journal'):
        sidecar = Path(str(path) + suffix)
        require(not sidecar.exists() and not sidecar.is_symlink(), 'database sidecar present')

def sha_file(path):
    h = hashlib.sha256()
    try:
        with path.open('rb') as f:
            for block in iter(lambda: f.read(1024 * 1024), b''):
                h.update(block)
    except OSError:
        raise VerificationError('database unavailable') from None
    return h.hexdigest()

def check_db(path, expected=SOURCES[DB]):
    require(path.is_file() and not path.is_symlink(), 'database path invalid')
    reject_sidecars(path)
    require(sha_file(path) == expected, 'database hash mismatch')

def norm(x):
    if x is None:
        return '<NULL>'
    if isinstance(x, float):
        return round(x, 6)
    if isinstance(x, int):
        return x
    if isinstance(x, bytes):
        return x.hex()
    return str(x).strip()

def derive(rows):
    # key, name, funding, math, district, candidate prefix, district AVG, gold prefix
    require(all(len(r) == 8 and r[0] is not None for r in rows), 'bad input row')
    all_rows = rows
    rows = [r[:7] for r in all_rows if r[7] == 1]
    groups = defaultdict(list)
    for key, name, funding, score, district, prefix, mean in rows:
        groups[(name, funding)].append((key, score))
    gold_raw = Counter()
    for pair, members in groups.items():
        vals = [score for _, score in members if score is not None]
        if vals and sum(vals) / len(members) > 400:
            gold_raw[pair] += 1
    gold = Counter()
    for pair, n in gold_raw.items():
        gold[tuple(map(norm, pair))] += n
    candidate_raw = Counter((name, funding) for _, name, funding, score, _, prefix, _, _ in all_rows
                            if prefix == 1 and score is not None and score > 400)
    candidate = Counter()
    for pair, n in candidate_raw.items():
        candidate[tuple(map(norm, pair))] += n
    reconstruction = Counter(tuple(map(norm, (name, funding))) for _, name, funding, _, _, _, mean in rows
                             if mean is not None and mean > 400)
    # 只允许可唯一映射的投影，避免仅凭名字推断额外行的 NULL 身份。
    projected = [tuple(map(norm, (r[1], r[2]))) for r in rows]
    require(len(set(projected)) == len(rows) and len({r[0] for r in rows}) == len(rows), 'nonunique projection')
    extra = reconstruction - gold
    by_projection = {tuple(map(norm, (r[1], r[2]))): r for r in rows}
    vals = [r[3] for r in rows if r[3] is not None]
    require(vals and rows, 'empty data')
    district_groups = defaultdict(list)
    for r in rows:
        district_groups[r[4]].append(r[3])
    # 匿名计数表只描述筛选后的本地连接域；一般情况下不代表整个地区。
    district_summaries = []
    for scores in district_groups.values():
        nonnull = [v for v in scores if v is not None]
        require(nonnull, 'district has no known score')
        district_summaries.append({'rows':len(scores), 'nonnull':len(nonnull), 'sum':sum(nonnull),
                                   'nonnull_avg':sum(nonnull)/len(nonnull), 'sum_over_rows':sum(nonnull)/len(scores)})
    district_summaries.sort(key=lambda x: (x['rows'], x['nonnull'], x['sum']))
    return {'prefix_candidate_only': sum(1 for r in all_rows if r[5] == 1 and r[7] != 1),
            'prefix_gold_only': sum(1 for r in all_rows if r[7] == 1 and r[5] != 1),
            'join_rows': len(rows), 'distinct_schools': len({r[0] for r in rows}),
            'distinct_names': len({r[1] for r in rows}), 'distinct_districts': len({r[4] for r in rows}),
            'math_null': len(rows)-len(vals), 'math_nonnull': len(vals), 'math_sum': sum(vals),
            'avg_nonnull': sum(vals)/len(vals), 'sum_over_all_rows': sum(vals)/len(rows),
            'district_summaries_anonymous': district_summaries,
            'gold_groups_rows': sum(gold.values()), 'candidate_rows': sum(candidate.values()),
            'candidate_equals_gold_checker_normalized_multiset': candidate == gold,
            'candidate_equals_gold_raw_value_multiset': candidate_raw == gold_raw,
            'reconstruction_rows': sum(reconstruction.values()),
            'gold_missing_from_reconstruction': sum((gold-reconstruction).values()),
            'reconstruction_extra_rows': sum(extra.values()),
            'extra_with_null_math': sum(n for pair,n in extra.items() if by_projection[pair][3] is None),
            'group_count': len(groups)}

def canonical(prefix):
    path = ROOT / DB
    check_db(path)
    con = sqlite3.connect(path.resolve().as_uri() + '?mode=ro&immutable=1', uri=True)
    try:
        con.execute('PRAGMA query_only=ON')
        require(con.execute('PRAGMA query_only').fetchone()[0] == 1, 'query_only failed')
        rows = con.execute(FIXED_SELECT, (prefix,)*4).fetchall()
        result = derive(rows)
    finally:
        con.close()
    check_db(path)
    require((result['join_rows'], result['distinct_schools'], result['math_null'], result['math_sum']) == (12,12,6,2842), 'data preconditions mismatch')
    require((result['gold_groups_rows'], result['candidate_rows'], result['reconstruction_rows'],
             result['gold_missing_from_reconstruction'], result['reconstruction_extra_rows'], result['extra_with_null_math']) == (6,6,12,0,6,6)
            and result['candidate_equals_gold_checker_normalized_multiset']
            and result['candidate_equals_gold_raw_value_multiset'], 'comparison preconditions mismatch')
    return result

def question_prefix(data):
    questions = json_source(data, CASE+'inputs/questions.json')
    selected = [q for q in questions if q.get('question_id') == 25]
    require(len(selected) == 1, 'question identity')
    matches = re.findall(r'以 ([A-Za-z]+) 开头', selected[0]['question_zh'])
    require(len(matches) == 1, 'question prefix unavailable')
    return matches[0]


def main():
    try:
        data = read_sources()
        sources = check_sources(data)
        result = canonical(question_prefix(data))
        print(json.dumps({'source_receipts': sources, 'current_canonical_fixed_select': result,
              'scope': '事后匿名重建，不是历史结果字节或业务裁定；结果相同不证明 SQL 逻辑等价。'}, ensure_ascii=False, indent=2))
        return 0
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError, VerificationError):
        print('ERROR: source, identity, database or comparison verification failed', file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())
