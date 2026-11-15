#!/usr/bin/env python3
"""q27 日期亲和与可见反馈：只解析固定来源，不执行历史 SQL 或产品。

公开源码的原轨迹及元数据可间接访问旧标识；本脚本不复制会话名或调用 ID。
摘要绑定只验证当前文件字节，不认证历史真实性或模型是否阅读、理解和记忆。
r1030 运行器 stdout 缺失，事后重扫不能证明完整轨迹或完整上下文。
SQLite 机制参见 https://www.sqlite.org/datatype3.html#type_conversions_prior_to_comparison 。
"""
import argparse
import datetime as dt
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASE = '2-用例/bird-ca-schools-15/'
RUNS = '3-表现现场/r1030-formal-a1/runs/'
CODEX = RUNS + 'codex__bird-ca-schools-15/'
DSH = RUNS + 'dsh__bird-ca-schools-15/'
SOURCES = {
    'questions': (CASE + 'inputs/questions.json', '144bf7c36b58ab261f44676618a80af9f9d642fd287a4d2885c0cd7d53543f3e'),
    'gold': (CASE + 'solution/answers.jsonl', '9b63a1846f0955cf2976c1ebb310c30e16eb740c9f09b7a7a45b5fe11b251929'),
    'database': (CASE + 'inputs/db/california_schools.sqlite', 'a9e7d92a47c0d247d76a7a4acd76a4764f430f4d711e9e6809f399a9bf72322d'),
    'codex': (CODEX + 'workspace/answers.jsonl', '653f02ecc9a8e8957790ab3b462abbca3b59579c0cf166dc3dd407f5f38edf8f'),
    'dsh': (DSH + 'workspace/answers.jsonl', '621074e36e5fc555fa785cb591ba51c4acdc720b3c47ad3e9f012fc5200fcd28'),
    'codex_receipt': (CODEX + 'checker.stdout.json', '66533a613c2b6854363ccd988530818a41acab7e2d7026c2181c88a2f3ce1586'),
    'dsh_receipt': (DSH + 'checker.stdout.json', '1e2b108af604ae1947b11f289610c82fc22666173a4d4506b24c1291321af6cb'),
    'codex_score': (CODEX + 'score-receipt.json', 'f5f17c1f025833c25a787f0bb7787575a28e2ee1e43f613d5ce3e9837040754c'),
    'dsh_score': (DSH + 'score-receipt.json', '40e410c29958036b2367ccf96e888d73d831c306b1238f9bed47b9e39f74310d'),
    'meta': (CODEX + 'meta.json', 'f5f64d8dae1b3c83aab012062c69c11c19093499048ba798a65187efd480b6b5'),
}
SESSION_SHA = '1552a332adb04f51cdcc6910385f089ba6a3839e1a09641721c91c125d20d25d'

class VerificationError(Exception):
    pass

def require(condition, message):
    if not condition:
        raise VerificationError(message)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def checked_bytes(root, key):
    rel, wanted = SOURCES[key]
    data = (root / rel).read_bytes()
    require(digest(data) == wanted, '源摘要不匹配: ' + key)
    return data

def one(items, label):
    require(len(items) == 1, label + ' 必须恰有一项')
    return items[0]

def json_lines(data):
    return [json.loads(line) for line in data.decode('utf-8').splitlines() if line.strip()]

def answer(data):
    rows = json_lines(data)
    require(len(rows) == 15 and len({x['question_id'] for x in rows}) == 15, '答案行数或 ID 异常')
    obj = one([x for x in rows if x['question_id'] == 27], 'q27 答案')
    require(isinstance(obj.get('sql'), str), '答案 SQL 类型异常')
    return obj['sql']

def check_sources(root):
    raw = {k: checked_bytes(root, k) for k in SOURCES if k != 'database'}
    questions = json.loads(raw['questions'])
    require(len(questions) == 15 and len({q['question_id'] for q in questions}) == 15, '题目数异常')
    q = one([x for x in questions if x['question_id'] == 27], 'q27 题目')
    require('1991 年之后' in q['question_zh'] and '2000 年之前' in q['question_zh'] and '、或 ' in q['question_zh'], '题目日期或 OR 口径异常')
    require(q['answer_columns'] == ['School', 'AvgScrWrite', 'Phone'], '题目列口径异常')
    sql = {k: answer(raw[k]) for k in ('gold', 'codex', 'dsh')}
    for k in sql:
        require('LEFT JOIN' in sql[k].upper() and ' OR ' in sql[k].upper(), '答案连接或 OR 异常')
    require("strftime('%Y', T2.OpenDate) > '1991' OR strftime('%Y', T2.ClosedDate) < '2000'" in sql['gold'], 'gold 谓词异常')
    require("s.OpenDate > '1991' OR s.ClosedDate < '2000'" in sql['codex'], 'Codex 谓词异常')
    require("s.OpenDate > '1991-12-31' OR s.ClosedDate < '2000-01-01'" in sql['dsh'], 'DSH 谓词异常')
    for name, passed, correct in [('codex', False, 14), ('dsh', True, 15)]:
        receipt = json.loads(raw[name + '_receipt'])
        score = json.loads(raw[name + '_score'])
        require(score['raw_checker_output'] == receipt and score['score']['earned'] == correct and score['score']['possible'] == 15 and score['score']['assessed'] == 15, '评分回执与 checker 不一致')
        item = one([x for x in receipt['checks'] if x['id'] == 'q27'], 'q27 收据')
        require(item['pass'] is passed and receipt['correct'] == correct and receipt['n_questions'] == 15, '收据内容异常')
        if not passed:
            require(item['note'] == '行数 16317 vs gold 8574' and receipt['failed_questions'] == ['27'], 'Codex 收据差异异常')
        else:
            require(item['note'] == '行集一致（8574 行）' and receipt['failed_questions'] == [], 'DSH 收据差异异常')
    meta = json.loads(raw['meta'])
    dbhash = SOURCES['database'][1]
    require(one([x for x in meta['inputs'] if x['path'] == 'inputs/db/california_schools.sqlite'], '数据库元数据')['sha256'] == dbhash, '数据库元数据异常')
    candidates = []
    for path in (root / CODEX / 'agent-session').glob('*.jsonl'):
        data = path.read_bytes()
        if digest(data) == SESSION_SHA:
            candidates.append(data)
    session = one(candidates, '摘要寻址会话')
    trace = check_trace(json_lines(session), sql['codex'])
    return sql, trace

def check_trace(records, expected_sql):
    calls, outputs = [], []
    for i, rec in enumerate(records):
        if rec.get('type') != 'response_item':
            continue
        p = rec.get('payload', {})
        if p.get('type') == 'function_call':
            args = json.loads(p['arguments'])
            calls.append((i, rec, p, args.get('cmd', '')))
        elif p.get('type') == 'function_call_output':
            outputs.append((i, rec, p, p.get('output', '')))
    probe = one([x for x in calls if "q('Q27 date boundary years'" in x[3] and "q('Q27 closed years before 2000'" in x[3]], '日期探针调用')
    require("SELECT substr(OpenDate,1,4) y,count(*) FROM schools WHERE OpenDate IS NOT NULL GROUP BY y ORDER BY y LIMIT 20" in probe[3] and "SELECT substr(ClosedDate,1,4) y,count(*) FROM schools WHERE ClosedDate IS NOT NULL AND ClosedDate<'2000' GROUP BY y ORDER BY y" in probe[3], '日期探针内容异常')
    contrast = one([x for x in calls if 'CAST(OpenDate AS TEXT)' in x[3] and "ClosedDate<'2000-01-01'" in x[3] and "ClosedDate<'2000'" in x[3]], '日期比较对照调用')
    patch = one([x for x in calls if '*** Add File: answers.jsonl' in x[3]], '答案写入调用')
    rows = [json.loads(line[1:]) for line in patch[3].splitlines() if line.startswith('+{')]
    require(one([x for x in rows if x.get('question_id') == 27], '写入 q27')['sql'] == expected_sql, '写入与归档答案不一致')
    def paired(call, label):
        cid = call[2]['call_id']
        require(isinstance(cid, str) and cid, label + '调用 ID 异常')
        require(len([x for x in calls if x[2].get('call_id') == cid]) == 1, label + '调用 ID 不唯一')
        return one([x for x in outputs if x[2].get('call_id') == cid], label + '返回')
    result = paired(probe, '日期探针')
    contrast_result = paired(contrast, '日期比较对照')
    written = paired(patch, '答案写入')
    require('Process exited with code 0' in contrast_result[3], '日期比较对照未成功返回')
    open_sql = "SELECT CDSCode,OpenDate,OpenDate > '1991',OpenDate > '1991-12-31',CAST(OpenDate AS TEXT),typeof(OpenDate) FROM schools WHERE OpenDate<'1991-01-01' LIMIT 10"
    closed_sql = "SELECT ClosedDate, ClosedDate<'2000-01-01', ClosedDate<'2000' FROM schools WHERE ClosedDate<'2000-01-01' LIMIT 5"
    count_full = "SELECT count(*) FROM schools WHERE OpenDate>'1991-12-31'"
    count_nonnull = 'SELECT count(*) FROM schools WHERE OpenDate IS NOT NULL'
    count_old = "SELECT count(*) FROM schools WHERE OpenDate<'1991-01-01'"
    count_numeric = 'SELECT count(*) FROM schools WHERE OpenDate > 1991'
    for sql in (open_sql, closed_sql, count_full, count_nonnull, count_old, count_numeric):
        require(sql in contrast[3], '日期比较对照调用内容异常')
    def section(sql, next_sql):
        marker, end = '\n ' + sql + '\n', '\n ' + next_sql + '\n'
        require(contrast_result[3].count(marker) == 1 and contrast_result[3].count(end) == 1, '对照返回分节异常')
        a, b = contrast_result[3].index(marker) + len(marker), contrast_result[3].index(end)
        require(a <= b, '对照返回分节顺序异常')
        return contrast_result[3][a:b].strip()
    require("'1980-07-01', 1, 0, '1980-07-01', 'text'" in section(open_sql, count_old), '开办样本不符')
    require(section(count_old, count_full) == '(11097,)' and section(count_full, count_nonnull) == '(5083,)' and section(count_nonnull, closed_sql) == '(16317,)', '开办计数不符')
    require("('1989-06-30', 1, 0)" in section(closed_sql, count_numeric), '关闭样本不符')
    require(section(count_numeric, 'SELECT count(*) FROM schools WHERE OpenDate > 1991.0') == '(16317,)', '数字阈值计数不符')
    require('Process exited with code 0' in result[3], '日期探针未成功返回')
    before, separator, after = result[3].partition('-- Q27 closed years before 2000\n')
    require(separator and "('1850', 1)" in before and after.startswith('\n-- Q27 open 1991 samples'), '探针返回内容异常')
    require('Exit code: 0' in written[3] and 'Success. Updated the following files:' in written[3], '写入返回异常')
    check = one([x for x in calls if "Q{o['question_id']}: ok" in x[3] and "answers.jsonl" in x[3]], '结果检查调用')
    check_result = paired(check, '结果检查')
    require('Q27: ok, cols=3, rows=16317' in check_result[3], '结果检查返回异常')
    ordered = [probe, result, contrast, contrast_result, patch, written, check, check_result]
    require(all(a[0] < b[0] for a, b in zip(ordered, ordered[1:])), '轨迹行顺序异常')
    times = [dt.datetime.fromisoformat(x[1]['timestamp'].replace('Z', '+00:00')) for x in ordered]
    require(all(t.tzinfo is not None for t in times) and all(a <= b for a, b in zip(times, times[1:])), '轨迹时间顺序异常')
    require(all(a[1]['ordinal'] < b[1]['ordinal'] for a, b in zip(ordered, ordered[1:])), '轨迹序号异常')
    return {'probe_and_contrast_return_before_final_write': True, 'write_return_before_result_check': True,
            'visible_q27_rows': 16317, 'closed_year_probe_rows': 0,
            'scope': '固定会话的可见调用与返回；不证明阅读、理解、记忆、因果或完整轨迹'}

# 固定、自写 SELECT；不执行任何来源中的 SQL。只回传匿名计数。
PREDICATES = {
    'year': "strftime('%Y', OpenDate) > '1991' OR strftime('%Y', ClosedDate) < '2000'",
    'full_date': "OpenDate > '1991-12-31' OR ClosedDate < '2000-01-01'",
    'bare_year': "OpenDate > '1991' OR ClosedDate < '2000'",
    'open_year': "strftime('%Y', OpenDate) > '1991'",
    'open_full': "OpenDate > '1991-12-31'",
    'open_bare': "OpenDate > '1991'",
    'closed_year': "strftime('%Y', ClosedDate) < '2000'",
    'closed_full': "ClosedDate < '2000-01-01'",
    'closed_bare': "ClosedDate < '2000'",
}

def database_report(root):
    path = root / SOURCES['database'][0]
    for suffix in ('-wal', '-shm', '-journal'):
        require(not Path(str(path) + suffix).exists(), '数据库存在 SQLite sidecar，无法保证单文件快照')
    checked_bytes(root, 'database')
    con = sqlite3.connect(path.resolve().as_uri() + '?mode=ro&immutable=1', uri=True)
    try:
        con.execute('PRAGMA query_only = ON')
        total = con.execute('SELECT count(*) FROM schools').fetchone()[0]
        counts = {name: con.execute('SELECT count(*) FROM schools WHERE ' + pred).fetchone()[0] for name, pred in PREDICATES.items()}
        differences = {}
        for left, right in [('year', 'full_date'), ('year', 'bare_year'), ('full_date', 'bare_year')]:
            for a, b in ((left, right), (right, left)):
                query = 'SELECT count(*) FROM (SELECT CDSCode FROM schools WHERE ' + PREDICATES[a] + ' EXCEPT SELECT CDSCode FROM schools WHERE ' + PREDICATES[b] + ')'
                differences[a + '_minus_' + b] = con.execute(query).fetchone()[0]
        types = {}
        for col in ('OpenDate', 'ClosedDate'):
            types[col] = dict(con.execute('SELECT typeof(' + col + '), count(*) FROM schools GROUP BY typeof(' + col + ')').fetchall())
        keys = con.execute('SELECT count(DISTINCT CDSCode), sum(CDSCode IS NULL) FROM schools').fetchone()
        require(keys == (total, 0), '学校主键不唯一或为空')
        return {'schools_total': total, 'predicate_counts': counts, 'primary_key_differences': differences, 'storage_types_and_null': types}
    finally:
        con.close()

def fixture_report():
    con = sqlite3.connect(':memory:')
    try:
        con.execute('CREATE TABLE sample (label TEXT, d DATE, t TEXT, c DATE)')
        con.executemany('INSERT INTO sample VALUES (?, ?, ?, ?)', [
            ('old', '1980-01-01', '1980-01-01', None),
            ('boundary', '1991-12-31', '1991-12-31', '1999-12-31'),
            ('new', '1992-01-01', '1992-01-01', '2000-01-01'),
            ('null', None, None, None),
            ('number_text', '1980', '1980', None),
            ('number_int', 1992, 1992, None),
            ('invalid_date', '1992-12-32', '1992-12-32', None),
        ])
        sql = "SELECT label, typeof(d), typeof(t), d > '1991', t > '1991', +d > '1991', strftime('%Y',d) > '1991', d > '1991-12-31', strftime('%Y',c) < '2000', (strftime('%Y',d) > '1991' OR strftime('%Y',c) < '2000'), c < '2000', (d > '1991' OR c < '2000'), (d > '1991-12-31' OR c < '2000-01-01') FROM sample ORDER BY rowid"
        rows = con.execute(sql).fetchall()
        require(rows[0][3:6] == (1, 0, 0) and rows[5][3:6] == (1, 1, 0), 'DATE、TEXT 或无列亲和反例不成立')
        require(rows[1][6:12] == (0, 0, 1, 1, 0, 1) and rows[0][9] is None and rows[0][11] == 1, 'OR 日期反例不成立')
        require(rows[3][3:10] == (None,) * 7, 'NULL 三值逻辑异常')
        require(rows[4][1:4] == ('integer', 'text', 0), '数值亲和转换异常')
        require(rows[5][1:4] == ('integer', 'text', 1), '整数存储反例异常')
        require(all(r[6] == r[7] and r[9] == r[12] for r in rows[:4]), '规范日期样本不一致')
        require(rows[6][6] is None and rows[6][7] == 1 and rows[6][9] is None and rows[6][12] == 1, '非规范日期反例不成立')
        # 不输出学校数据；fixture label 仅指自造值。
        return {'columns': ['fixture', 'date_type', 'text_type', 'date_gt_bare', 'text_gt_bare', 'no_affinity_gt_bare', 'year_open', 'full_open', 'year_closed', 'year_or', 'bare_closed', 'bare_or', 'full_or'],
                'rows': rows, 'full_date_equals_strftime': '仅在四个规范日期/NULL自造样本比较中成立，不是普遍等价'}
    finally:
        con.close()

class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise VerificationError('参数不合法')

def main(argv=None):
    parser = SafeParser(prog='verify.py', description='固定证据摘要与匿名只读对照')
    parser.add_argument('--root', type=Path, default=ROOT, help='公开仓库根目录')
    try:
        args = parser.parse_args(argv)
        _, trace = check_sources(args.root)
        result = {'source_sha_verified': True, 'trace': trace, 'canonical_database': database_report(args.root), 'fixture': fixture_report(),
                  'limits': '公开源码可间接访问旧标识；摘要不认证历史真实性。runner stdout 缺失，不能证明完整轨迹；不能归因于模型或 Harness。'}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (VerificationError, OSError, ValueError, KeyError, TypeError, sqlite3.Error, UnicodeError, json.JSONDecodeError):
        print('验证失败：源缺失、变更或证据不符合固定约束；不显示动态路径。', file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
