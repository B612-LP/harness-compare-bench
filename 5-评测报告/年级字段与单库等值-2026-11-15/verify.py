#!/usr/bin/env python3
"""q83 事后只读复算；python3 -B verify.py。只输出匿名汇总。

仅两场 r1030 正式 A，非重新判分、非先验注册。公开 r1109 DSH 现场
已有字段比较，单库不足以证明普遍等价亦非新发现；此处仅核此具体案例。
题文未指定两个字段之一，不判断 gold 或候选的语义正确性。
不执行来源中的 SQL/代码。固定文件 SHA 只是当前派生包的输入钉住；
11 月 11 日公开 ledger 是后验清单，不证明 10 月运行时的密码学绑定。
"""
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASE = '2-用例/bird-ca-schools-15/'
RUN = '3-表现现场/r1030-formal-a1/runs/'
LEDGER = '4-打分细则/核验台账-2026-11-07/ledger.json'
PIN = {
    CASE+'inputs/db/california_schools.sqlite': 'a9e7d92a47c0d247d76a7a4acd76a4764f430f4d711e9e6809f399a9bf72322d',
    CASE+'inputs/questions.json': '144bf7c36b58ab261f44676618a80af9f9d642fd287a4d2885c0cd7d53543f3e',
    CASE+'inputs/schema.sql': '33411f4b8db97a1a703876a6142d070625d9e7f6ea1e63251a981da67826dd0d',
    CASE+'inputs/sample_rows.json': '1d6f869c2feb54d8c2ad3a1d427489aa770e7e52442f4a343d3e3a2b6d594d3d',
    CASE+'truth.json': 'c5bb7999079ac8f1711049d81392729edf127a27134d32a905ca39de15b8ea19',
    LEDGER: 'c929938183712c9e59ce32b5358bcc70a6619baa007fec3da2df6a89c64c340a',
    RUN+'codex__bird-ca-schools-15/workspace/answers.jsonl': '653f02ecc9a8e8957790ab3b462abbca3b59579c0cf166dc3dd407f5f38edf8f',
    RUN+'codex__bird-ca-schools-15/checker.stdout.json': '66533a613c2b6854363ccd988530818a41acab7e2d7026c2181c88a2f3ce1586',
    RUN+'codex__bird-ca-schools-15/meta.json': 'f5f64d8dae1b3c83aab012062c69c11c19093499048ba798a65187efd480b6b5',
    RUN+'dsh__bird-ca-schools-15/workspace/answers.jsonl': '621074e36e5fc555fa785cb591ba51c4acdc720b3c47ad3e9f012fc5200fcd28',
    RUN+'dsh__bird-ca-schools-15/checker.stdout.json': '1e2b108af604ae1947b11f289610c82fc22666173a4d4506b24c1291321af6cb',
    RUN+'dsh__bird-ca-schools-15/meta.json': 'a8fa671387e245b891b931fb41a5872128da651edb61bb4056513e69b3196d1d',
}
GOLD = "SELECT T2.City, COUNT(T2.CDSCode) FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.Magnet = 1 AND T2.GSoffered = 'K-8' AND T1.`NSLP Provision Status` = 'Multiple Provision Types' GROUP BY T2.City"
CANDIDATE = {
    'codex': "SELECT s.City, COUNT(*) AS count FROM frpm f JOIN schools s ON f.CDSCode = s.CDSCode WHERE s.Magnet = 1 AND s.GSserved = 'K-8' AND f.`NSLP Provision Status` = 'Multiple Provision Types' GROUP BY s.City",
    'dsh': "SELECT s.City, COUNT(*) AS count FROM schools AS s INNER JOIN frpm AS f ON s.CDSCode = f.CDSCode WHERE s.Magnet = 1 AND s.GSserved = 'K-8' AND f.`NSLP Provision Status` = 'Multiple Provision Types' GROUP BY s.City",
}

# 分区：只有非 NULL 两字段都不是 K-8 才是 neither_nonnull；含 NULL 且
# 一边为真计入独有，含 NULL 且无真计入 neither_null；null_any 为交叉计数。
# CASE 将 SQL UNKNOWN 视为不满足 WHERE，但不把 NULL 当作不等于。
BASE = '''WITH base AS (
 SELECT s.CDSCode AS id, s.City AS city, s.GSoffered AS offered,
        s.GSserved AS served, s.Magnet AS magnet,
        f.CDSCode IS NOT NULL AS joined,
        f.`NSLP Provision Status` = 'Multiple Provision Types' AS provision
 FROM schools s LEFT JOIN frpm f ON f.CDSCode = s.CDSCode
), scopes AS (
 SELECT 'all_schools' AS scope, * FROM base
 UNION ALL SELECT 'magnet', * FROM base WHERE magnet = 1
 UNION ALL SELECT 'joined', * FROM base WHERE joined
 UNION ALL SELECT 'joined_magnet', * FROM base WHERE joined AND magnet = 1
 UNION ALL SELECT 'joined_provision', * FROM base WHERE joined AND provision
 UNION ALL SELECT 'target_other_filters', * FROM base
   WHERE joined AND magnet = 1 AND provision
)'''
SUMMARY = BASE + '''
 SELECT scope, COUNT(*),
 COUNT(CASE WHEN offered = 'K-8' AND served = 'K-8' THEN 1 END),
 COUNT(CASE WHEN offered = 'K-8' AND (served = 'K-8') IS NOT TRUE THEN 1 END),
 COUNT(CASE WHEN served = 'K-8' AND (offered = 'K-8') IS NOT TRUE THEN 1 END),
 COUNT(CASE WHEN offered IS NOT NULL AND served IS NOT NULL AND offered <> 'K-8' AND served <> 'K-8' THEN 1 END),
 COUNT(CASE WHEN (offered = 'K-8') IS NOT TRUE AND (served = 'K-8') IS NOT TRUE AND (offered IS NULL OR served IS NULL) THEN 1 END),
 COUNT(CASE WHEN offered IS NULL OR served IS NULL THEN 1 END),
 COUNT(CASE WHEN offered IS NULL THEN 1 END),
 COUNT(CASE WHEN served IS NULL THEN 1 END)
 FROM scopes GROUP BY scope'''
# EXCEPT 两侧分别计数；分组键与学校标识只在 SQLite 内部，绝不输出。
DIFFERENCES = BASE + '''
, target AS (SELECT * FROM base WHERE joined AND magnet=1 AND provision),
 o AS (SELECT id, city FROM target WHERE offered='K-8'),
 s AS (SELECT id, city FROM target WHERE served='K-8'),
 og AS (SELECT city, COUNT(id) AS n FROM o GROUP BY city),
 sg AS (SELECT city, COUNT(*) AS n FROM s GROUP BY city)
 SELECT (SELECT COUNT(*) FROM (SELECT id FROM o EXCEPT SELECT id FROM s)),
        (SELECT COUNT(*) FROM (SELECT id FROM s EXCEPT SELECT id FROM o)),
        (SELECT COUNT(*) FROM (SELECT city,n FROM og EXCEPT SELECT city,n FROM sg)),
        (SELECT COUNT(*) FROM (SELECT city,n FROM sg EXCEPT SELECT city,n FROM og)),
        (SELECT COUNT(*) FROM og), (SELECT COUNT(*) FROM sg)'''

# 自造数据不是当前数据。两个分叉均遵守 served 是 offered 的子区间的
# 假设，但实际业务合法性未知，schema 本身不约束字段间包含关系。
# 前两行同一虚构组、各独有一个：成员不同而组计数相同。
SYNTHETIC = '''WITH base(id,city,offered,served,magnet,joined,provision) AS (VALUES
 (1,'x','K-12','K-8',1,1,1), (2,'x','K-8','1-8',1,1,1),
 (3,'x','K-8','K-8',1,1,1), (4,'x','K-12','1-8',1,1,1),
 (5,'x',NULL,'K-8',1,1,1), (6,'x','K-8',NULL,1,1,1),
 (7,'x',NULL,NULL,1,1,1), (8,'x','K-8','1-8',0,1,1),
 (9,'x','K-8','1-8',1,0,1), (10,'x','K-8','1-8',1,1,0)
), target AS (SELECT * FROM base WHERE joined AND magnet=1 AND provision),
 o AS (SELECT id, city FROM target WHERE offered='K-8'),
 s AS (SELECT id, city FROM target WHERE served='K-8'),
 og AS (SELECT city, COUNT(id) AS n FROM o GROUP BY city),
 sg AS (SELECT city, COUNT(*) AS n FROM s GROUP BY city)
 SELECT (SELECT COUNT(*) FROM target),
 (SELECT COUNT(*) FROM target WHERE offered='K-8' AND served='K-8'),
 (SELECT COUNT(*) FROM (SELECT id FROM o EXCEPT SELECT id FROM s)),
 (SELECT COUNT(*) FROM (SELECT id FROM s EXCEPT SELECT id FROM o)),
 (SELECT COUNT(*) FROM (SELECT city,n FROM og EXCEPT SELECT city,n FROM sg)),
 (SELECT COUNT(*) FROM (SELECT city,n FROM sg EXCEPT SELECT city,n FROM og)),
 (SELECT COUNT(*) FROM target WHERE (offered='K-8') IS NOT TRUE AND (served='K-8') IS NOT TRUE AND (offered IS NULL OR served IS NULL)),
 (SELECT COUNT(*) FROM target WHERE offered IS NULL OR served IS NULL)'''


class VerificationError(Exception):
    pass


def require(ok, message):
    if not ok:
        raise VerificationError(message)


def verify_pins(root=ROOT):
    for path, expected in PIN.items():
        data = (root / path).read_bytes()
        require(hashlib.sha256(data).hexdigest() == expected, '固定输入 SHA 不匹配')


def check_checker(obj):
    matches = [c for c in obj['checks'] if c.get('id') == 'q83']
    require(len(matches) == 1 and matches[0].get('pass') is True and
            matches[0].get('note') == '行集一致（1 行）', 'q83 checker 记录不符')


def check_sql(actual, expected):
    # 精确比对经人工阅读的字面文本，不解析运行不可信 SQL。
    require(actual == expected, 'q83 SQL 文本不符固定证据')


def check_evidence(root=ROOT):
    verify_pins(root)
    load = lambda p: json.loads((root / p).read_text(encoding='utf-8'))
    truth = load(CASE+'truth.json')
    check_sql(truth['answers']['83']['sql'], GOLD)
    questions = load(CASE+'inputs/questions.json')
    q = [item for item in questions if item['question_id'] == 83]
    require(len(q) == 1 and not any(field in str(q[0]) for field in ('GSoffered', 'GSserved')), '题文字段检查失败')
    ledger = load(LEDGER)
    entries = ledger['inventory']['files']
    for path, sha in PIN.items():
        if path == LEDGER:
            continue
        found = [row for row in entries if row['p'] == path]
        require(len(found) == 1 and found[0]['s'] == sha, '后验台账记录不符')
    for path, sha in truth['input_sha256'].items():
        require(PIN.get(CASE+path) == sha, 'truth 输入哈希不符')
    for product in ('codex', 'dsh'):
        prefix = RUN+product+'__bird-ca-schools-15/'
        rows = [json.loads(line) for line in (root / (prefix+'workspace/answers.jsonl')).read_text(encoding='utf-8').splitlines()]
        qrows = [r for r in rows if r.get('question_id') == 83]
        require(len(qrows) == 1, '答案 q83 不唯一')
        check_sql(qrows[0]['sql'], CANDIDATE[product])
        checker = load(prefix+'checker.stdout.json')
        check_checker(checker)
        meta = load(prefix+'meta.json')
        check_checker(meta['judge'])
        require(meta['product'] == product and meta['case'] == 'bird-ca-schools-15', 'meta 身份不符')
        for item in meta['inputs']:
            require(PIN.get(CASE+item['path']) == item['sha256'], 'meta 输入哈希不符')
        require(len(meta['inputs']) == 4 and len({x['path'] for x in meta['inputs']}) == 4, 'meta 输入集合不符')


def summarize(conn):
    columns = ('n', 'both_true', 'offered_only', 'served_only', 'neither_nonnull', 'neither_null', 'null_any_overlapping', 'offered_null_overlapping', 'served_null_overlapping')
    result = {}
    for scope, *counts in conn.execute(SUMMARY):
        require(sum(counts[1:6]) == counts[0], '分区不守恒')
        result[scope] = dict(zip(columns, counts))
    return result


def differences(conn):
    row = conn.execute(DIFFERENCES).fetchone()
    keys = ('members_offered_minus_served', 'members_served_minus_offered',
            'groups_offered_minus_served', 'groups_served_minus_offered',
            'offered_group_count', 'served_group_count')
    return dict(zip(keys, row))


def synthetic(conn):
    row = conn.execute(SYNTHETIC).fetchone()
    keys = ('target_n', 'both_true', 'members_offered_only', 'members_served_only',
            'groups_offered_only', 'groups_served_only', 'neither_null', 'null_any')
    return dict(zip(keys, row))


def run(root=ROOT):
    check_evidence(root)
    db = (root / (CASE+'inputs/db/california_schools.sqlite')).resolve()
    with sqlite3.connect(db.as_uri()+'?mode=ro&immutable=1', uri=True) as conn:
        conn.execute('PRAGMA query_only=ON')
        stats = summarize(conn)
        diff = differences(conn)
        require(all(diff[k] == 0 for k in ('members_offered_minus_served', 'members_served_minus_offered', 'groups_offered_minus_served', 'groups_served_minus_offered')), '目标集合或分组差非零')
        require(diff['offered_group_count'] == diff['served_group_count'] == 1, '组数不符 checker 一行')
    with sqlite3.connect(':memory:') as conn:
        conn.execute('PRAGMA query_only=ON')
        example = synthetic(conn)
    require(example == {'target_n': 7, 'both_true': 1, 'members_offered_only': 2, 'members_served_only': 2, 'groups_offered_only': 0, 'groups_served_only': 0, 'neither_null': 1, 'null_any': 3}, '合成反例不符预期')
    return {
        'scope': 'r1030 正式 A 的 Codex 与 DSH q83；非普遍结论',
        'evidence': '固定 SHA 与 truth/meta 一致；ledger 为后验绑定，不证明当时密码学绑定；原 SQL 未执行。',
        'interpretation': '题文未指定 GSoffered/GSserved；不判谁错，不修改分数。schema 无跨字段约束，实际业务合法性未知。',
        'current_database': stats,
        'target_set_and_group_differences': diff,
        'synthetic_not_real_frequency': example,
        'synthetic_explanation': '自造同组分叉及 NULL 抵消使聚合相同但成员集合不同；非目标行被排除；不代表真实频率。',
        'sql_semantics': '独有含对侧 NULL；neither_null 是均不为真且至少一 NULL；null_any 与其他类重叠。COUNT(expr) 忽略 NULL。',
    }


def main():
    try:
        print(json.dumps(run(), ensure_ascii=False, indent=2))
        return 0
    except (VerificationError, OSError, ValueError, KeyError, TypeError, sqlite3.Error):
        print('核验失败：输入、记录、数据库或不变量不符；未输出行级数据。', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
