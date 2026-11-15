#!/usr/bin/env python3
"""机制序列口径 v2.1（2026-11-16）离线裁决。只读 stdlib；不联网、不起子进程、无历史工具导入。
公共复算验证的是 content-free 投影算术与公开源绑定，不认证私档原件真实性。
协议与分区见本包 README §2 + v2.1 增补块（session/title-llm-request→M、subagent/catalog→M，
冻结于任何组内 v2 裁决计算之前）；表外未知类型一律报错（exit 2），不静默归类。
复用 v1.1（机制重复口径澄清-2026-11-12/verify.py）的加载、源 SHA 钉定、canonical JSON、
槽身份校验、CLI 形状与 fail-closed 错误风格；在本页冻结口径上计算不同观测。
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


BASELINE = '4183c4e2fd492ce258b5c6e51341193cc1e569f9'
HERE = '4-打分细则/机制序列口径v2-2026-11-16'
V11_HERE = '4-打分细则/机制重复口径澄清-2026-11-12'
BATCH = '3-表现现场/r1109-mech-n3'
OBS = '3-表现现场/r1109-bw-retest/observe'
CASES = ('bird-ca-schools-15', 'dabstep-payments-10', 'exercism-py-6', 'lcb-recent-hard-4', 'tb-cargo-plan')
ARM = 'dsh'
V11_BASELINE = '38b2e13f63c5aeacb58094d2e977980ab12e8041'
V11_CONTRACT = {'cases': list(CASES), 'arms': ['dsh', 'codex'], 'reps': [1, 2, 3], 'slots': 30,
                'groups': 10, 'byte_threshold': 100, 'operator': 'AND'}
V2_CONTRACT = {'cases': list(CASES), 'arms': [ARM], 'reps': [1, 2, 3], 'slots': 15,
               'groups': 5, 'byte_threshold': 100, 'gate': 'AND', 'operator': 'AND'}
EVIDENCE_SHA256 = '925470d3b55b4226d70f5749d45d0c65a161703c4053fa21028ce0516fcd6b5c'
V11_RESULT_SHA256 = 'abb3a4fc09f1210b30021f7896551b7d0b34502cabbfe08ad0777b87dddc4433'
# 冻结分区（README §2 表 + v2.1 增补；逐字对应，改表必须先改协议页）。
I_TYPES = frozenset(('user/message', 'request/header', 'request/context', 'system/message', 'agent/inbox/spliced'))
K_TYPES = frozenset(('turn/start', 'turn/end', 'step/start', 'step/end', 'assistant/message', 'tool/call', 'tool/result'))
M_TYPES = frozenset(('session', 'session/title', 'permission/preset', 'sandbox/mode', 'approval/policy',
                     'session-log-deepseek/delivery-accepted', 'session/title-llm-request', 'subagent/catalog'))
PARTITION = (('I', I_TYPES), ('K', K_TYPES), ('M', M_TYPES))
PARTITION_TYPES = I_TYPES | K_TYPES | M_TYPES
S3_TYPES = frozenset(('user/message', 'request/header', 'request/context'))
require(S3_TYPES <= I_TYPES, 'S3 selection must be inside frozen I partition')
require(not (I_TYPES & K_TYPES) and not (I_TYPES & M_TYPES) and not (K_TYPES & M_TYPES), 'partition overlap')
CORRECTED_DSH = frozenset(('dsh__bird-ca-schools-15__r2', 'dsh__dabstep-payments-10__r3', 'dsh__tb-cargo-plan__r2'))
# 四个主/更正捕获曾以 basename 作为聚合 run 标签；槽级 path+SHA 与 accounting source id 仍为必查项。
BASENAME_LABELS = CORRECTED_DSH | {'dsh__dabstep-payments-10__r1'}
NOTE = ('v2 sequence adjudication (v2.1 amended partition, frozen before any v2 verdict computation). '
        'Public replay verifies content-free projection arithmetic and public source binding only; '
        'private raw authenticity NOT certified. No new product runs; Codex excluded per prereg '
        '(Codex byte subgate 0/5 already fails the AND gate). D is descriptive, not a gate.')


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None, 'invalid SHA256')
    return value


def integer(value):
    require(type(value) is int and value >= 0, 'expected nonnegative integer')
    return value


def expected_slots():
    return [f'{ARM}__{case}__r{rep}' for case in CASES for rep in (1, 2, 3)]


def validate_evidence_slots(rows):
    """v1.1 同款 30 槽完整性规则：证据本体不许缺槽、混槽、重复。"""
    require(isinstance(rows, list), 'slots must be list')
    ids = [row['slot'] for row in rows]
    require(len(ids) == len(set(ids)), 'duplicate slot')
    require(set(ids) == {f'{arm}__{case}__r{rep}' for arm in ('dsh', 'codex') for case in CASES for rep in (1, 2, 3)},
            'missing or mixed slot')
    require(len(rows) == 30, 'slot count changed')


def check_scope(slots):
    """v2 裁决范围：DSH 5 组 × 3 reps = 15 槽；Codex 按预注册排除。"""
    ids = [row['slot'] for row in slots]
    require(len(ids) == len(set(ids)), 'duplicate adjudicated slot')
    require(set(ids) == set(expected_slots()), 'missing or mixed DSH slot')
    require(len(slots) == 15, 'v2 slot count changed')


def partition_of(event_type):
    for name, types in PARTITION:
        if event_type in types:
            return name
    return None


def check_partition_coverage(slot_rows):
    """覆盖率检查先行：任何 I/K/M 冻结表之外类型 → 报错并列出槽名+类型（exit 2）。"""
    union = Counter()
    unknown = []
    for slot, rows in slot_rows:
        for row in rows:
            union[row[0]] += 1
            if row[0] not in PARTITION_TYPES:
                unknown.append((slot, row[0]))
    if unknown:
        raise Invalid('unknown event types outside frozen v2.1 partition (coverage check): '
                      + '; '.join(f'{s}: {t}' for s, t in unknown))
    return union


def measure_slot(slot, rows):
    """逐槽 content-free 投影：S3 和、I 序列/字节、K 序列/字节、M 字节（canonical 规则同 v1.1）。"""
    require(isinstance(rows, list) and rows, 'missing event projection: ' + slot)
    for row in rows:
        require(isinstance(row, list) and len(row) == 4, 'bad event projection schema: ' + slot)
        require(isinstance(row[0], str) and row[0], 'bad event type: ' + slot)
        integer(row[1]); integer(row[3])
        require(row[1] > 0, 'empty canonical event: ' + slot)
        require(row[2] is None and row[3] == 0, 'unexpected payload projection: ' + slot)
        require(row[0] in PARTITION_TYPES, 'unknown event type: ' + slot + ' ' + row[0])
    s3_bytes = sum(r[1] for r in rows if r[0] in S3_TYPES)
    i_sequence = [r[0] for r in rows if r[0] in I_TYPES]
    i_bytes = sum(r[1] for r in rows if r[0] in I_TYPES)
    k_sequence = [r[0] for r in rows if r[0] in K_TYPES]
    k_bytes = sum(r[1] for r in rows if r[0] in K_TYPES)
    m_bytes = sum(r[1] for r in rows if r[0] in M_TYPES)
    counts = {'I': 0, 'K': 0, 'M': 0}
    for row in rows:
        counts[partition_of(row[0])] += 1
    require(s3_bytes > 0 and i_bytes > 0 and k_bytes > 0 and m_bytes > 0, 'empty v2 partition metric: ' + slot)
    return {'slot': slot, 'event_count': len(rows), 'type_counts': dict(sorted(Counter(r[0] for r in rows).items())),
            's3_bytes': s3_bytes, 'i_event_count': counts['I'], 'i_bytes': i_bytes,
            'i_sequence': i_sequence, 'i_sequence_sha256': sha(canon(i_sequence)),
            'k_event_count': counts['K'], 'k_bytes': k_bytes,
            'k_sequence': k_sequence, 'k_sequence_sha256': sha(canon(k_sequence)),
            'm_event_count': counts['M'], 'm_bytes': m_bytes}


def bound_json(root, record):
    relative = record['path']
    path = Path(relative)
    require(not path.is_absolute() and '..' not in path.parts, 'unsafe source path')
    absolute = (root / path).resolve()
    require(root == absolute or root in absolute.parents, 'source escapes root')
    try:
        raw = absolute.read_bytes()
    except OSError as error:
        raise Invalid('missing source: ' + relative) from error
    require(sha(raw) == digest(record['sha256']), 'source SHA mismatch: ' + relative)
    try:
        return json.loads(raw)
    except (ValueError, UnicodeError) as error:
        raise Invalid('invalid source JSON: ' + relative) from error


def check_identity(slot, meta, identity, incident, receipt):
    """v1.1 同款 DSH 槽身份三重对账（meta / accounting / adjudication receipt）。"""
    arm, case, rep_text = slot.split('__')
    rep = rep_text[1:]
    require((meta['product'], meta['case'], meta['rep']) == (arm, case, rep), 'meta identity mismatch')
    require(meta['event_id'] == f'mech-n3-{arm}-{case}-r{rep}', 'event identity mismatch')
    require(meta['batch'] in ('r1109-mech-n3', 'r1030-formal-a1'), 'mixed batch')
    # 部分公开 meta 副本保留 a1 批次标签；身份一律不从它推断。
    require((receipt['product'], receipt['case_id'], receipt['rep'], receipt['run_id']) ==
            (arm, case, rep, f'r1109-{arm}-{case}-r{rep}'), 'receipt identity mismatch')
    require(meta['status'] == 'ok' and meta['exit_code'] == 0, 'slot not completed')
    require(incident['slot'] == slot and incident['started_at'] == meta['started_at'], 'accounting identity mismatch')
    expected_source = f'{arm}/runs/{slot}/agent-session/session.v4.jsonl.zstd'
    require(identity['source_relative_to_archive'] == expected_source, 'trace slot path mismatch')
    require(identity['id'] in incident['candidates'] and identity['version'] == 4, 'DSH source identity mismatch')
    if 'new_sha' in incident:
        require(identity['sha256'].startswith(incident['new_sha']), 'DSH trace SHA prefix mismatch')
    digest(identity['sha256'])


def check_metric_claim(actual, claimed, label):
    require(actual == claimed, label + ' mismatch')


def check_aggregate(slot, aggregate, metrics):
    """对公开聚合逐项复核（v1.1 同款规则；S4 非 v2 观测，不在本页复核范围）。"""
    require(aggregate['format'] == 'dsh-session-v4-jsonl-zstd' and len(aggregate['per_file']) == 1, 'bad DSH aggregate')
    f = aggregate['per_file'][0]
    aggregate_run = 'session.v4.jsonl.zstd' if slot in BASENAME_LABELS else slot
    require(f['run'] == aggregate_run and aggregate['inputs']['runs'] == [aggregate_run], 'DSH aggregate identity mismatch')
    require(f['s1']['unparsable'] == 0 and f['s1']['lines'] == metrics['event_count'], 'bad DSH aggregate event coverage')
    check_metric_claim(metrics['type_counts'], f['s2']['type_counts'], 'DSH types')
    check_metric_claim(metrics['s3_bytes'], f['s3']['input_bytes'], 'S3')


def crosscheck_v11(v11, slots, groups):
    """硬校验：逐槽 S3 与组级 B1 max−min 必须与 v1.1 钉定 result.json 完全一致。"""
    require(v11['schema'] == 'mechanism-repetition-clarification-v1.1', 'v1.1 result schema changed')
    require(v11['baseline_commit'] == V11_BASELINE, 'v1.1 baseline changed')
    v11_s3 = {row['slot']: row['input_bytes'] for row in v11['slots'] if row['arm'] == ARM}
    require(len(v11_s3) == 15, 'v1.1 DSH slot count changed')
    for row in slots:
        require(v11_s3.get(row['slot']) == row['s3_bytes'], 'v1.1 per-slot S3 mismatch: ' + row['slot'])
    v11_mm = {g['case']: g['max_minus_min'] for g in v11['groups'] if g['arm'] == ARM}
    require(len(v11_mm) == 5, 'v1.1 DSH group count changed')
    for group in groups:
        require(v11_mm.get(group['case']) == group['b1_max_minus_min'],
                'B1 cross-check mismatch vs v1.1: ' + group['case'])


def group_verdict(case, rows):
    """逐组四观测 + 主门 v2 = B1 ∧ S1 ∧ B2；D 描述性非门。"""
    require([r['rep'] for r in rows] == [1, 2, 3], 'group repetitions changed')
    s3 = [r['s3_bytes'] for r in rows]
    i_bytes = [r['i_bytes'] for r in rows]
    k_bytes = [r['k_bytes'] for r in rows]
    i_sequences = [r['i_sequence'] for r in rows]
    k_sequences = [r['k_sequence'] for r in rows]
    b1_mm = max(s3) - min(s3)
    b2_mm = max(i_bytes) - min(i_bytes)
    s1_pass = len({r['i_sequence_sha256'] for r in rows}) == 1 and len({tuple(s) for s in i_sequences}) == 1
    d_sequence_equal = len({r['k_sequence_sha256'] for r in rows}) == 1 and len({tuple(s) for s in k_sequences}) == 1
    b1_pass = b1_mm <= 100
    b2_pass = b2_mm <= 100
    gate = 'pass' if (b1_pass and s1_pass and b2_pass) else 'fail'
    return {'case': case, 'arm': ARM, 'n': 3, 'rep': [r['rep'] for r in rows],
            's3_bytes': s3, 'b1_max_minus_min': b1_mm, 'b1_pass': b1_pass,
            's1_pass': s1_pass, 'i_sequence_sha256': [r['i_sequence_sha256'] for r in rows],
            'i_bytes': i_bytes, 'b2_max_minus_min': b2_mm, 'b2_pass': b2_pass,
            'gate_v2': gate,
            'd_sequence_all_equal': d_sequence_equal,
            'k_sequence_sha256': [r['k_sequence_sha256'] for r in rows],
            'k_bytes': k_bytes, 'k_bytes_max_minus_min': max(k_bytes) - min(k_bytes),
            'k_bytes_max_min_ratio': max(k_bytes) / min(k_bytes)}


def analyze(root):
    root = Path(root).resolve()
    # 1) v1.1 证据本体：SHA 钉定 + schema/baseline/contract 检查 + 30 槽完整性。
    evidence_path = root / V11_HERE / 'evidence.json'
    raw = evidence_path.read_bytes()
    require(sha(raw) == EVIDENCE_SHA256, 'evidence SHA mismatch')
    evidence = json.loads(raw)
    require(evidence['schema'] == 'r1109-content-free-projection-v1.1', 'bad evidence schema')
    require(evidence['baseline_commit'] == V11_BASELINE and evidence['contract'] == V11_CONTRACT,
            'v1.1 baseline or contract changed')
    validate_evidence_slots(evidence['slots'])
    # 2) 69 个公开源 SHA 绑定（JSON 取值 + 非规范 JSON 文件字节校验），同 v1.1。
    records = evidence['public_sources']
    require(len({r['path'] for r in records}) == len(records), 'duplicate source binding')
    sources = {record['path']: bound_json(root, record) for record in records if record['path'].endswith('.json')}
    for record in records:
        if not record['path'].endswith('.json'):
            path = (root / record['path']).resolve()
            require(root in path.parents, 'normative source escapes root')
            require(sha(path.read_bytes()) == record['sha256'], 'normative source SHA mismatch')
    # 3) accounting / adjudication 身份底账，同 v1.1。
    accounting = sources[BATCH + '/observe/trace-accounting-summary.json']
    incidents = {}
    for arm_rows in accounting[ARM]['incidents']:
        require(arm_rows['slot'] not in incidents, 'duplicate accounting slot')
        incidents[arm_rows['slot']] = arm_rows
    require(len(incidents) == 15, 'accounting slot count changed')
    require(set(incidents) == set(expected_slots()), 'mixed accounting slots')
    adjudications = sources[BATCH + '/adjudications.json']
    require(len(adjudications) == 30, 'adjudication count changed')
    receipts = {f"{r['identity']['product']}__{r['identity']['case_id']}__r{r['identity']['rep']}": r['identity']
                for r in adjudications}
    require(set(receipts) >= set(expected_slots()), 'mixed adjudication identities')
    # 4) 覆盖率检查先行（表外类型即整体报错，先于任何逐槽观测与组内裁决）。
    dsh_rows = [(row['slot'], row['events']) for row in evidence['slots'] if row['slot'].startswith(ARM + '__')]
    check_scope([{'slot': s} for s, _ in dsh_rows])
    union = check_partition_coverage(dsh_rows)
    # 5) 逐槽身份对账 + 聚合复核 + v2 投影。
    slots = []
    for row in evidence['slots']:
        slot = row['slot']
        if not slot.startswith(ARM + '__'):
            continue  # Codex 按预注册排除，不裁决、不投影
        _, case, rep_text = slot.split('__')
        rep = int(rep_text[1:])
        meta = sources[BATCH + '/runs/' + slot + '/meta.public-derived.json']
        identity = row['identity']
        check_identity(slot, meta, identity, incidents[slot], receipts[slot])
        metrics = measure_slot(slot, row['events'])
        expected_aggregate = (f'{OBS}/session-{slot if slot in CORRECTED_DSH else slot.replace("dsh__", "dsh-", 1)}.json')
        aggregate = sources[expected_aggregate]
        check_aggregate(slot, aggregate, metrics)
        slots.append({'slot': slot, 'case': case, 'rep': rep, 'status': meta['status'],
                      'trace_sha256': identity['sha256'], 'meta_batch_label': meta['batch'],
                      'aggregate_path': expected_aggregate, **metrics})
    check_scope(slots)
    # 6) 逐组裁决（先全部算完再写入任何组内结论；主门 v2 = B1 ∧ S1 ∧ B2）。
    groups = []
    for case in CASES:
        rows = sorted([r for r in slots if r['case'] == case], key=lambda r: r['rep'])
        require(len(rows) == 3, 'group size changed: ' + case)
        groups.append(group_verdict(case, rows))
    require(len(groups) == 5, 'v2 group count changed')
    # 7) v1.1 钉定 result.json 交叉校验（逐槽 S3 + 组级 B1 max−min 硬相等）。
    v11_path = root / V11_HERE / 'result.json'
    v11_raw = v11_path.read_bytes()
    require(sha(v11_raw) == V11_RESULT_SHA256, 'v1.1 result SHA mismatch')
    v11 = json.loads(v11_raw)
    crosscheck_v11(v11, slots, groups)
    # 8) 反证分支登记（README §3，冻结；逐项机械判定）。
    branches = {
        'b1_pass_b2_fail': [g['case'] for g in groups if g['b1_pass'] and not g['b2_pass']],
        's1_fail_b2_pass': [g['case'] for g in groups if not g['s1_pass'] and g['b2_pass']],
        'd_seq_equal_k_bytes_vary': [g['case'] for g in groups
                                     if g['d_sequence_all_equal'] and g['k_bytes_max_minus_min'] > 0]}
    return {'schema': 'mech-seq-v2-projection-v1', 'baseline_commit': BASELINE,
            'protocol': {'page': HERE + '/README.md', 'version': 'v2.1',
                         'amendment': ('v2.1 partition amendment frozen before any v2 verdict computation: '
                                       'session/title-llm-request -> M, subagent/catalog -> M; '
                                       'v2 table text preserved; unknown-type fail-closed rule unchanged'),
                         'partition': {'I': sorted(I_TYPES), 'K': sorted(K_TYPES), 'M': sorted(M_TYPES)},
                         's3_selected': sorted(S3_TYPES), 'byte_threshold': 100},
            'contract': V2_CONTRACT, 'note': NOTE,
            'coverage': {'union_type_counts': dict(sorted(union.items())), 'union_size': len(union),
                         'total_events': sum(union.values()), 'unknown_types': [],
                         'basis': 'v1.1 evidence.json per-slot projections; cross-checked against public aggregate type_counts'},
            'v11_crosscheck': {'result_path': V11_HERE + '/result.json', 'result_sha256': V11_RESULT_SHA256,
                               'per_slot_s3_equal': True, 'group_b1_max_minus_min_equal': True,
                               'pinned_b1_max_minus_min': {g['case']: g['b1_max_minus_min'] for g in groups}},
            'v2_gate': {'pass_count': sum(g['gate_v2'] == 'pass' for g in groups), 'total': 5,
                        'verdict_by_case': {g['case']: g['gate_v2'] for g in groups}},
            'prereg_section3_branches': branches,
            'groups': groups, 'slots': slots,
            'source_bindings': records, 'evidence_sha256': sha(raw),
            'limitations': ['Content-free projection arithmetic only: types, canonical byte counts and SHAs; '
                            'no message content, payload text, wire bytes, tokens or costs.',
                            'Public verification covers projection arithmetic and public source binding, '
                            'not private-archive authenticity.',
                            'v2.1 amendment frozen before any v2 verdict computation; no v2 verdict was computed under the unamended v2 table.',
                            'No new product runs; no historical files modified; no scores rejudged.',
                            'D is descriptive, not a gate; S4/output bytes are out of v2 scope.']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, help='new exclusive destination; default stdout')
    args = parser.parse_args(argv)
    try:
        result = analyze(args.root)
        text = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n'
        if args.output:
            with args.output.open('x', encoding='utf-8') as stream:
                stream.write(text)
        else:
            sys.stdout.write(text)
    except (Invalid, OSError, ValueError, KeyError, TypeError, IndexError) as error:
        sys.stderr.write('ERROR: ' + str(error) + '\n')
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
