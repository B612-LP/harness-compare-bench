#!/usr/bin/env python3
"""bird 交互量结构分解（2026-11-16）离线验证。只读；不联网、不改动包外文件、无 git 副作用。

对 r1109 DSH bird-ca-schools-15 三个真身归档轨迹做 S4 逐轮结构分解（预注册冻结页：
本包 README.md，SHA256 钉定于 PREREG_SHA256，本脚本不修改它）。canonical 口径与
机制重复口径澄清-2026-11-12 / 机制序列口径v2-2026-11-16 完全一致：
len(canon(event))，canon = json.dumps(value, ensure_ascii=False, sort_keys=True,
separators=(',',':'), allow_nan=False).encode('utf-8')；DSH v4 事件无 payload 包装，
事件对象即载荷。S4 硬相等（551905/193745/517142）即该口径与公开钉定一致的ground truth。

公开复算验证 content-free 结构算术与源绑定，不认证私档原件真实性；不输出消息内容、
工具参数、会话 id、绝对路径或私档目录名（工具只记 name + canonical 字节数）。
真身判定：本批 capture 错配件不入账；r2 槽以 trace-incident.json 的 new_sha 前缀
对账当前文件。exit 0 / exit 2（任何校验失败）纪律。
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


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None,
            'invalid SHA256')
    return value


HERE = '4-打分细则/bird交互量结构分解-2026-11-16'
PREREG_SHA256 = '5b697126551d82265425cc1864da23a10f411cca4492651071cc390375661ee4'
OBS = '3-表现现场/r1109-bw-retest/observe'
BATCH = '3-表现现场/r1109-mech-n3'
V11_REL = '4-打分细则/机制重复口径澄清-2026-11-12'
V11_EVIDENCE_SHA256 = '925470d3b55b4226d70f5749d45d0c65a161703c4053fa21028ce0516fcd6b5c'
V11_RESULT_SHA256 = 'abb3a4fc09f1210b30021f7896551b7d0b34502cabbfe08ad0777b87dddc4433'
SLOT = 'dsh__bird-ca-schools-15'
SLOTS = (SLOT + '__r1', SLOT + '__r2', SLOT + '__r3')
CASE = 'bird-ca-schools-15'
ARCHIVE_REL = 'dsh/runs/{slot}/agent-session/session.v4.jsonl.zstd'
INCIDENT_REL = 'dsh/runs/{slot}/agent-session/trace-incident.json'
# 公开源钉定（本包输入；v11_pin 列出机制重复口径澄清 v1.1 evidence.json 的同文件钉定，
# 运行时同时校验并双双记录）。stale r2 聚合不在 v1.1 钉定内（v1.1 只钉更正后聚合）。
PUBLIC_SOURCES = (
    (OBS + '/dsh-s3-s4-summary.json',
     'bd5da97b71201475896f64f96434af108f4da7a3633361bfe9c1d26f3a66e03c',
     'bd5da97b71201475896f64f96434af108f4da7a3633361bfe9c1d26f3a66e03c'),
    (OBS + '/session-dsh-bird-ca-schools-15__r1.json',
     '542a54d439e585c6d5f966888e2f0c5f4615fa3da3a02063a69b5331633d4bfc',
     '542a54d439e585c6d5f966888e2f0c5f4615fa3da3a02063a69b5331633d4bfc'),
    (OBS + '/session-dsh-bird-ca-schools-15__r2.json',
     '09a6598f086a0fa00e1da00c4c79abe6f04ad144836620afa2341c25734f80e8',
     None),
    (OBS + '/session-dsh-bird-ca-schools-15__r3.json',
     'f6f8eff63eac2482b83b41b1671c0d382c0456917fff80436aacdad532076221',
     'f6f8eff63eac2482b83b41b1671c0d382c0456917fff80436aacdad532076221'),
    (OBS + '/session-dsh__bird-ca-schools-15__r2.json',
     '501950e037a39cb739cf0b7186371ddc0d7bf7b8452282b5b889eb10066cb0fc',
     '501950e037a39cb739cf0b7186371ddc0d7bf7b8452282b5b889eb10066cb0fc'),
    (BATCH + '/runs/' + SLOT + '__r1/score-receipt.json',
     'bb54dbeae312e9dfd2cbfe5b5df9aa27344667042d3d68288f444320d4bfcab4', None),
    (BATCH + '/runs/' + SLOT + '__r2/score-receipt.json',
     '1dbdcbd884a3a45d7aab8291e06d4ba7592683d8fc1677b217bea80e7efe39fa', None),
    (BATCH + '/runs/' + SLOT + '__r3/score-receipt.json',
     '1dbdcbd884a3a45d7aab8291e06d4ba7592683d8fc1677b217bea80e7efe39fa', None),
)
ARCHIVE_SOURCES = {
    SLOT + '__r1': '205f35dddff641c5f002312e9de82d442b6654c40f3c1577c7977a6352c73cca',
    SLOT + '__r2': '27234833c35fdddf7050e96297f4a16c4d4979681b48083ac9a79bad0d5158c7',
    SLOT + '__r3': 'e5a2bac26e524e4e2f619a96fae1bad9d1791c429950467975d61bb1fa4f6f68',
}
INCIDENT_SOURCES = {
    SLOT + '__r1': 'abc8dea4f04d6554125a856ca74de34bed709dadd1d89912aa90882a1b962575',
    SLOT + '__r2': '2d66b983715fa6af77b8ef454106ffde41b3a3399444420cff3421afb44cd2e2',
    SLOT + '__r3': 'e745ea0196e69671a245582097dea27e69ee0c113e0d4e9b18aa570025bdca91',
}
# 预注册冻结值（README §1，v1.1 勘误后口径）：真身 S4 逐槽硬相等目标。
FROZEN_S4 = {SLOT + '__r1': 551905, SLOT + '__r2': 193745, SLOT + '__r3': 517142}
# 预注册 §1 骨架（公开 session-dsh-bird-ca-schools-15__r{1,2,3}.json type_counts）。
FROZEN_SKELETON = {'assistant/message': [29, 29, 27], 'tool/call': [29, 29, 29],
                   'user/message': [3, 3, 3]}
# 更正后 r2 真身骨架（公开更正聚合 session-dsh__bird-ca-schools-15__r2.json）。
CORRECTED_R2_SKELETON = {'assistant/message': 9, 'tool/call': 16, 'user/message': 3}
S4_TYPES = ('assistant/message', 'tool/call')
NOTE = ('S4 per-round structure decomposition of the three true-body archived DSH bird '
        'reps. Content-free: event types, canonical byte counts, tool names, SHAs only; '
        'no message content, tool arguments, tokens or costs. Score receipts are '
        'side-by-side context, no causal claim. The stale bw-retest r2 aggregate and the '
        'old summary slot-2 value (551905) are documented pre-correction residues '
        '(v1.1 erratum); the true-body pin is 193745.')


def resolve_head(root):
    """Current HEAD commit, resolved from .git files only (no subprocess)."""
    git = root / '.git'
    if git.is_file():
        text = git.read_text(encoding='utf-8').strip()
        require(text.startswith('gitdir:'), 'unsupported .git indirection')
        git = Path(text.split(':', 1)[1].strip())
        if not git.is_absolute():
            git = (root / git).resolve()
    require(git.is_dir(), 'missing .git directory')
    head = (git / 'HEAD').read_text(encoding='utf-8').strip()
    value = None
    if head.startswith('ref: '):
        ref = head[5:].strip()
        direct = git / ref
        if direct.is_file():
            value = direct.read_text(encoding='utf-8').strip()
        else:
            for line in (git / 'packed-refs').read_text(encoding='utf-8').splitlines():
                if line.endswith(' ' + ref):
                    value = line.split(' ', 1)[0].strip()
                    break
    else:
        value = head
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{40}', value or '') is not None,
            'cannot resolve current HEAD commit')
    return value


def bound_bytes(root, relative, expected_sha):
    path = Path(relative)
    require(not path.is_absolute() and '..' not in path.parts, 'unsafe source path')
    absolute = (root / path).resolve()
    require(root == absolute or root in absolute.parents, 'source escapes root')
    try:
        raw = absolute.read_bytes()
    except OSError as error:
        raise Invalid('missing source: ' + relative) from error
    require(sha(raw) == digest(expected_sha), 'source SHA mismatch: ' + relative)
    return raw


def bound_json(root, relative, expected_sha):
    raw = bound_bytes(root, relative, expected_sha)
    try:
        return json.loads(raw)
    except (ValueError, UnicodeError) as error:
        raise Invalid('invalid source JSON: ' + relative) from error


def decompress_jsonl(path):
    """Multi-frame zstd JSONL; zstandard imported lazily, loud Invalid if absent."""
    try:
        import zstandard
    except ImportError as error:
        raise Invalid('zstandard module required to read archived .zstd traces') from error
    path = Path(path)
    with open(path, 'rb') as stream:
        reader = zstandard.ZstdDecompressor().stream_reader(stream, read_across_frames=True)
        raw = reader.read()
    require(len(raw) > 0, 'empty decompressed trace: ' + path.name)
    events = []
    for index, line in enumerate(raw.decode('utf-8').splitlines()):
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except ValueError as error:
            raise Invalid(f'unparsable trace line {index + 1}: ' + path.name) from error
    require(bool(events), 'no events in trace: ' + path.name)
    return events, len(raw)


def window_rounds(events, slot):
    """step/start→step/end windows; per-round S4 bytes with explicit outside bucket.

    Fail-closed on: missing/duplicate session header, non-contiguous steps, nested or
    mismatched windows (窗口错位), inside event whose own data.step contradicts the open
    window, tool/call without a usable name field. assistant/message and tool/call
    outside any window are counted into the outside-window bucket (bytes + counts),
    never silently dropped.
    """
    require(isinstance(events, list) and events, 'missing events: ' + slot)
    session_headers = [e for e in events if isinstance(e, dict) and e.get('type') == 'session']
    require(len(session_headers) == 1 and events[0].get('type') == 'session',
            'bad session header: ' + slot)
    require(session_headers[0].get('version') == 4, 'non-v4 session trace: ' + slot)
    rounds = {}
    order = []
    current = None
    outside_counts = Counter()
    outside_bytes = Counter()
    tool_bytes = {}
    name_sequence = []
    round_events = {}
    for event in events:
        require(isinstance(event, dict) and isinstance(event.get('type'), str),
                'bad event schema: ' + slot)
        kind = event['type']
        data = event.get('data')
        if kind == 'session':
            continue
        if kind == 'step/start':
            require(isinstance(data, dict) and type(data.get('step')) is int,
                    'bad step/start: ' + slot)
            step = data['step']
            require(current is None, 'nested step/start: ' + slot)
            require(step == len(order) + 1, 'non-contiguous step numbering: ' + slot)
            current = step
            rounds[step] = 0
            order.append(step)
            round_events[step] = []
            continue
        if kind == 'step/end':
            require(isinstance(data, dict) and type(data.get('step')) is int,
                    'bad step/end: ' + slot)
            require(current is not None and data['step'] == current,
                    'step window misalignment: ' + slot)
            current = None
            continue
        if kind in S4_TYPES:
            size = len(canon(event))
            if current is None:
                outside_counts[kind] += 1
                outside_bytes[kind] += size
                continue
            declared = data.get('step') if isinstance(data, dict) else None
            require(declared == current, 'event step contradicts open window: ' + slot)
            rounds[current] += size
            if kind == 'tool/call':
                name = data.get('name') if isinstance(data, dict) else None
                require(isinstance(name, str) and name != '',
                        'tool/call without name field: ' + slot)
                tool_bytes[name] = tool_bytes.get(name, 0) + size
                name_sequence.append(name)
                round_events[current].append([name, size])
            else:
                round_events[current].append(['assistant/message', size])
    require(bool(order), 'no step windows: ' + slot)
    require(current is None, 'unclosed step window: ' + slot)
    for step in order:
        require(rounds[step] > 0, 'empty round bytes: ' + slot)
    total = sum(rounds[step] for step in order)
    require(total > 0, 'zero S4 total: ' + slot)
    return {'round_order': order, 'round_bytes': [rounds[step] for step in order],
            'round_events': {str(step): round_events[step] for step in order},
            'tool_bytes': tool_bytes, 'name_sequence': name_sequence,
            'outside_counts': dict(sorted(outside_counts.items())),
            'outside_bytes': dict(sorted(outside_bytes.items())),
            'assistant_message_bytes': sum(size for events_in_round in round_events.values()
                                           for kind, size in events_in_round
                                           if kind == 'assistant/message'),
            's4_total': total}


def top5_share(round_bytes):
    """Share of the 5 largest rounds; strictly > 0.5 means H-A (== 0.5 stays H-B side)."""
    require(isinstance(round_bytes, list) and round_bytes and
            all(type(value) is int and value >= 0 for value in round_bytes),
            'bad round-bytes sequence')
    total = sum(round_bytes)
    require(total > 0, 'zero total for top5 share')
    top5 = sorted(round_bytes, reverse=True)[:5]
    return sum(top5) / total, top5


def longest_common_prefix(sequences):
    """3-way (or n-way) LCP length; empty sequence edge returns 0."""
    require(isinstance(sequences, list) and sequences, 'no sequences for LCP')
    if any(not isinstance(seq, list) for seq in sequences):
        raise Invalid('bad sequence for LCP')
    if len(sequences) == 1:
        return len(sequences[0])
    if any(len(seq) == 0 for seq in sequences):
        return 0
    length = 0
    for values in zip(*sequences):
        if len(set(values)) == 1:
            length += 1
        else:
            break
    return length


def check_receipt(slot, receipt):
    """Score receipt field validation (fail-closed on missing fields)."""
    require(isinstance(receipt, dict), 'bad score receipt: ' + slot)
    for field in ('earned', 'possible', 'assessed', 'reported', 'reward',
                  'rule_version', 'checker_sha256'):
        require(field in receipt, 'score receipt missing field ' + field + ': ' + slot)
    for field in ('earned', 'possible', 'assessed'):
        require(type(receipt[field]) is int and receipt[field] >= 0,
                'bad receipt integer ' + field + ': ' + slot)
    require(isinstance(receipt['reported'], (int, float)) and
            isinstance(receipt['reward'], int), 'bad receipt numbers: ' + slot)
    require(isinstance(receipt['rule_version'], str) and
            isinstance(receipt['checker_sha256'], str) and receipt['checker_sha256'],
            'bad receipt strings: ' + slot)
    incident = receipt.get('judging_incident')
    require(isinstance(incident, dict) and isinstance(incident.get('cause'), str),
            'judging_incident missing or malformed: ' + slot)
    return incident


def render_summary(result):
    lines = ['bird-s4-structure-projection-v1 summary',
             'prereg sha256 ok: ' + result['prereg_sha256'],
             'baseline_commit: ' + result['baseline_commit']]
    for row in result['reps']:
        lines.append('rep %s: rounds=%d s4=%d hard_equal_ok=%s top5_share=%.6f verdict=%s '
                     'outside_window=%s' % (row['rep'], row['round_count'], row['s4_total'],
                                            row['s4_hard_equal_ok'], row['top5_share'],
                                            row['concentration_verdict'],
                                            row['outside_window_events']))
        lines.append('  tool name bytes: ' + json.dumps(row['tool_name_bytes'],
                                                        ensure_ascii=False, sort_keys=True))
    lines.append('H-A concentrated reps: ' + json.dumps(result['verdicts']['concentrated_reps']))
    lines.append('H-B diffuse reps: ' + json.dumps(result['verdicts']['diffuse_reps']))
    lines.append('structure: %s (lcp=%d, first divergence call index %d, min rounds %d)'
                 % (result['verdicts']['structure_verdict'], result['cross_rep']['lcp_three_way'],
                    result['cross_rep']['first_divergence']['call_index'],
                    result['cross_rep']['min_round_count']))
    for row in result['score_alignment']:
        lines.append('score %s: earned=%s/%s reported=%s reward=%s incident=%s'
                     % (row['rep'], row['earned'], row['possible'], row['reported'],
                        row['reward'], row['judging_incident_present']))
    lines.append('verdict: ' + result['verdicts']['verdict_sentence'])
    return '\n'.join(lines) + '\n'


def analyze(root, archive_root, inject=None, expected_s4=None):
    """Full offline analysis. inject: {public relative path -> parsed object} test hook;
    expected_s4: {slot -> int} test override of the frozen pin (default FROZEN_S4)."""
    root = Path(root).resolve()
    archive_root = Path(archive_root).resolve()
    inject = inject or {}
    expected_s4 = expected_s4 or FROZEN_S4
    # 1) 预注册页钉定（冻结于任何逐轮分解值计算之前）。
    bound_bytes(root, HERE + '/README.md', PREREG_SHA256)
    baseline = resolve_head(root)
    # 2) v1.1 证据与结果本体（更正口径来源；SHA 钉定）。
    evidence = bound_json(root, V11_REL + '/evidence.json', V11_EVIDENCE_SHA256)
    require(evidence['schema'] == 'r1109-content-free-projection-v1.1', 'bad v1.1 evidence schema')
    v11_pins = {record['path']: record['sha256'] for record in evidence['public_sources']}
    v11_result = bound_json(root, V11_REL + '/result.json', V11_RESULT_SHA256)
    require(v11_result['schema'] == 'mechanism-repetition-clarification-v1.1',
            'bad v1.1 result schema')
    # 3) 公开源绑定：本包钉定 + v1.1 同文件钉定（如有）双双校验并记录。
    sources = {}
    bindings = []
    for relative, package_pin, v11_pin in PUBLIC_SOURCES:
        raw = bound_bytes(root, relative, package_pin)
        if v11_pin is not None:
            require(v11_pin == package_pin, 'package/v1.1 pin divergence: ' + relative)
            require(relative in v11_pins and v11_pins[relative] == v11_pin,
                    'v1.1 evidence pin mismatch: ' + relative)
        try:
            sources[relative] = json.loads(raw)
        except (ValueError, UnicodeError) as error:
            raise Invalid('invalid source JSON: ' + relative) from error
        if relative in inject:
            sources[relative] = inject[relative]
        bindings.append({'path': relative, 'sha256': package_pin,
                         'v11_evidence_pin': v11_pin})
    # 4) 公开钉定事实复核：旧摘要 r1/r3 位、更正 r2 聚合、v1.1 结果组值、骨架计数。
    summary = sources[OBS + '/dsh-s3-s4-summary.json']
    bird_summary = summary[CASE]
    require(isinstance(bird_summary.get('s4_output_bytes'), list) and
            len(bird_summary['s4_output_bytes']) == 3, 'bad summary bird row')
    require(bird_summary['s4_output_bytes'][0] == FROZEN_S4[SLOT + '__r1'],
            'summary r1 slot S4 pin mismatch')
    require(bird_summary['s4_output_bytes'][2] == FROZEN_S4[SLOT + '__r3'],
            'summary r3 slot S4 pin mismatch')
    stale_r2_recorded = bird_summary['s4_output_bytes'][1]
    require(type(stale_r2_recorded) is int, 'bad stale summary r2 value')
    stale_agg = sources[OBS + '/session-dsh-bird-ca-schools-15__r2.json']
    corrected_agg = sources[OBS + '/session-dsh__bird-ca-schools-15__r2.json']
    skeleton = {}
    for index, rep in enumerate(('r1', 'r2', 'r3')):
        aggregate = sources[OBS + '/session-dsh-bird-ca-schools-15__' + rep + '.json']
        require(aggregate['format'] == 'dsh-session-v4-jsonl-zstd', 'bad aggregate format: ' + rep)
        file_row = aggregate['per_file'][0]
        counts = file_row['s2']['type_counts']
        skeleton[rep] = {kind: counts.get(kind, 0) for kind in FROZEN_SKELETON}
        for kind, expected in FROZEN_SKELETON.items():
            require(skeleton[rep][kind] == expected[index],
                    'public skeleton mismatch: ' + rep + ' ' + kind)
        require(file_row['run'] == SLOT + '__' + rep, 'aggregate run label mismatch: ' + rep)
    require(stale_agg['per_file'][0]['s4']['output_bytes'] == stale_r2_recorded,
            'stale r2 aggregate/summary residue disagreement')
    require(corrected_agg['format'] == 'dsh-session-v4-jsonl-zstd', 'bad corrected aggregate')
    corrected_file = corrected_agg['per_file'][0]
    require(corrected_file['s4']['output_bytes'] == FROZEN_S4[SLOT + '__r2'],
            'corrected r2 aggregate S4 pin mismatch')
    corrected_counts = {kind: corrected_file['s2']['type_counts'].get(kind, 0)
                        for kind in CORRECTED_R2_SKELETON}
    require(corrected_counts == CORRECTED_R2_SKELETON, 'corrected r2 skeleton mismatch')
    require(corrected_file['run'] == 'session.v4.jsonl.zstd',
            'corrected aggregate keeps basename run label')
    v11_group = next(group for group in v11_result['groups'] if group['case'] == CASE and
                     group.get('arm') == 'dsh')
    require(v11_group['output_bytes'] == [FROZEN_S4[SLOT + '__r1'], FROZEN_S4[SLOT + '__r2'],
                                          FROZEN_S4[SLOT + '__r3']],
            'v1.1 result group output_bytes mismatch vs frozen S4 triple')
    v11_slots = {row['slot']: row['output_bytes'] for row in v11_result['slots']
                 if row['slot'] in SLOTS}
    require(v11_slots == dict(sorted(FROZEN_S4.items())), 'v1.1 result slot S4 mismatch')
    # 5) 真身归档：SHA 钉定 + 换回真身事故对账 + 逐轮结构分解。
    reps = []
    for slot in SLOTS:
        rep = slot[-2:]
        archive_relative = ARCHIVE_REL.format(slot=slot)
        trace_path = archive_root / archive_relative
        require(archive_root == trace_path.resolve() or archive_root in trace_path.resolve().parents,
                'archive path escapes archive root: ' + slot)
        raw = trace_path.read_bytes()
        require(sha(raw) == digest(ARCHIVE_SOURCES[slot]), 'archive trace SHA mismatch: ' + slot)
        incident = bound_json(archive_root, INCIDENT_REL.format(slot=slot),
                              INCIDENT_SOURCES[slot])
        require(incident.get('slot') == slot, 'incident slot mismatch: ' + slot)
        if 'new_sha' in incident:
            require(ARCHIVE_SOURCES[slot].startswith(incident['new_sha']),
                    'true-body new_sha prefix mismatch: ' + slot)
        events, decompressed_bytes = decompress_jsonl(str(trace_path))
        decomposition = window_rounds(events, slot)
        share, top5 = top5_share(decomposition['round_bytes'])
        total = decomposition['s4_total']
        require(total == expected_s4[slot],
                'S4 hard-equal mismatch: ' + slot + f' recomputed={total} expected={expected_s4[slot]}')
        type_counts = dict(sorted(Counter(e['type'] for e in events).items()))
        reps.append({'rep': rep, 'slot': slot,
                     'archive_relative_path': archive_relative,
                     'trace_sha256': ARCHIVE_SOURCES[slot],
                     'true_body_incident_verified': 'new_sha' in incident,
                     'decompressed_bytes': decompressed_bytes,
                     'event_count': len(events),
                     'type_counts': type_counts,
                     'round_count': len(decomposition['round_order']),
                     'round_bytes': decomposition['round_bytes'],
                     'round_events': decomposition['round_events'],
                     's4_total': total, 's4_hard_equal_ok': True,
                     'top5_round_bytes': top5, 'top5_share': share,
                     'concentration_verdict': 'H-A concentrated' if share > 0.5 else 'H-B diffuse',
                     'tool_name_bytes': dict(sorted(decomposition['tool_bytes'].items())),
                     'assistant_message_bytes': decomposition['assistant_message_bytes'],
                     'name_sequence': decomposition['name_sequence'],
                     'outside_window_events': decomposition['outside_counts'],
                     'outside_window_bytes': decomposition['outside_bytes']})
    # 6) 跨 rep 结构对照：名称序列 LCP、首分岔轮、逐名矩阵、逐步并排。
    sequences = [row['name_sequence'] for row in reps]
    lcp_three = longest_common_prefix(sequences)
    pairwise = {}
    for left in range(3):
        for right in range(left + 1, 3):
            pairwise[reps[left]['rep'] + '-' + reps[right]['rep']] = \
                longest_common_prefix([sequences[left], sequences[right]])
    divergence = None
    if lcp_three < min(len(seq) for seq in sequences):
        index = lcp_three
        containing = {}
        for row in reps:
            consumed = 0
            containing_round = None
            for step_text, events_in_round in row['round_events'].items():
                calls = [size for kind, size in events_in_round if kind != 'assistant/message']
                if consumed <= index < consumed + len(calls):
                    containing_round = int(step_text)
                    break
                consumed += len(calls)
            require(containing_round is not None, 'divergent call not located: ' + row['rep'])
            containing[row['rep']] = containing_round
        divergence = {'call_index': index,
                      'names_at_divergence': {row['rep']: sequences[i][index]
                                              for i, row in enumerate(reps)},
                      'containing_round': containing,
                      'containing_round_bytes': {row['rep']: row['round_bytes'][containing[row['rep']] - 1]
                                                 for row in reps}}
    names = sorted({name for row in reps for name in row['tool_name_bytes']})
    name_matrix = {name: {row['rep']: row['tool_name_bytes'].get(name, 0) for row in reps}
                   for name in names}
    min_rounds = min(row['round_count'] for row in reps)
    shared_steps = min(row['round_count'] for row in reps)
    step_pairs = []
    for step in range(1, shared_steps + 1):
        step_pairs.append({'step': step,
                           'bytes': {row['rep']: row['round_bytes'][step - 1] for row in reps}})
    # 7) 判卷对照（并排，不做因果断言）。
    score_alignment = []
    for row in reps:
        receipt = sources[BATCH + '/runs/' + row['slot'] + '/score-receipt.json']
        incident = check_receipt(row['slot'], receipt)
        score_alignment.append({'rep': row['rep'], 's4_total': row['s4_total'],
                                'round_count': row['round_count'],
                                'earned': receipt['earned'], 'possible': receipt['possible'],
                                'assessed': receipt['assessed'], 'reported': receipt['reported'],
                                'reward': receipt['reward'],
                                'rule_version': receipt['rule_version'],
                                'checker_sha256': receipt['checker_sha256'],
                                'judging_incident_present': True,
                                'judging_incident_cause': incident['cause']})
    # 8) 冻结反证分支（README §3）：H-A 严格 >0.5；==0.5 落 H-B 侧。
    concentrated = [row['rep'] for row in reps if row['top5_share'] > 0.5]
    diffuse = [row['rep'] for row in reps if row['top5_share'] <= 0.5]
    if concentrated and not diffuse:
        concentration_verdict = 'H-A concentrated (all reps)'
    elif concentrated and diffuse:
        concentration_verdict = 'mixed: H-A concentrated in ' + ','.join(concentrated) + \
                                '; H-B diffuse in ' + ','.join(diffuse)
    elif diffuse and not concentrated:
        concentration_verdict = 'H-B diffuse (all reps)'
    else:
        concentration_verdict = 'unreachable branch'
    structure_verdict = ('early-divergence' if lcp_three < min_rounds / 2
                         else 'late-convergence')
    magnitude_gap = False
    if divergence is not None:
        values = list(divergence['containing_round_bytes'].values())
        magnitude_gap = max(values) >= 2 * min(values)
    verdict_sentence = (
        'concentration: ' + concentration_verdict + '; structure: ' + structure_verdict +
        ('; first divergence call is in-round with >=2x byte gap (首次分岔即分途)'
         if magnitude_gap else '; no >=2x in-round byte gap at first divergence'))
    result = {'schema': 'bird-s4-structure-projection-v1',
              'prereg_sha256': PREREG_SHA256, 'baseline_commit': baseline,
              'baseline_source': 'resolved from .git HEAD without subprocess calls',
              'canonical_convention': ('len(canon(event)); canon = json.dumps(value, '
                                       'ensure_ascii=False, sort_keys=True, '
                                       "separators=(',',':'), allow_nan=False).encode('utf-8'); "
                                       'DSH v4 events carry no payload wrapper, the event '
                                       'object itself is canonicalized (same convention as '
                                       '机制重复口径澄清-2026-11-12 / 机制序列口径v2-2026-11-16)'),
              'contract': {'slots': list(SLOTS), 'case': CASE, 'arm': 'dsh', 'reps': 3,
                           'groups': 1, 's4_types': list(S4_TYPES),
                           'window_rule': 'step/start(data.step=k) -> step/end(data.step=k)',
                           'frozen_s4_pins': dict(sorted(FROZEN_S4.items())),
                           'frozen_public_skeleton': FROZEN_SKELETON,
                           'corrected_r2_skeleton': CORRECTED_R2_SKELETON},
              'note': NOTE,
              'public_source_bindings': bindings,
              'v11_reference': {'evidence_path': V11_REL + '/evidence.json',
                                'evidence_sha256': V11_EVIDENCE_SHA256,
                                'result_path': V11_REL + '/result.json',
                                'result_sha256': V11_RESULT_SHA256,
                                'group_output_bytes_equal_frozen_triple': True},
              'stale_record': {'summary_path': OBS + '/dsh-s3-s4-summary.json',
                               'summary_s4_output_bytes_recorded':
                                   bird_summary['s4_output_bytes'],
                               'stale_r2_value_recorded': stale_r2_recorded,
                               'stale_r2_aggregate_s4': stale_agg['per_file'][0]['s4']['output_bytes'],
                               'explanation': ('summary position 2 and the stale r2 aggregate '
                                               'retain the pre-correction mis-capture value; '
                                               'superseded by the v1.1 erratum pin 193745 '
                                               '(真源 S4)；not used as this package r2 pin, '
                                               'recorded verbatim for traceability')},
              'public_skeleton_check': {'per_rep': skeleton,
                                        'expected': FROZEN_SKELETON, 'ok': True},
              'corrected_r2_aggregate_check': {'skeleton': corrected_counts, 'ok': True},
              'reps': reps,
              'cross_rep': {'name_sequences_sha256': [hashlib.sha256(canon(seq)).hexdigest()
                                                      for seq in sequences],
                            'lcp_three_way': lcp_three, 'lcp_pairwise': pairwise,
                            'min_round_count': min_rounds,
                            'lcp_vs_half_min_rounds': lcp_three < min_rounds / 2,
                            'first_divergence': divergence,
                            'tool_name_byte_matrix': name_matrix,
                            'assistant_message_bytes_by_rep':
                                {row['rep']: row['assistant_message_bytes'] for row in reps},
                            'shared_prefix_steps_bytes': step_pairs},
              'score_alignment': score_alignment,
              'verdicts': {'concentrated_reps': concentrated, 'diffuse_reps': diffuse,
                           'concentration_verdict': concentration_verdict,
                           'structure_verdict': structure_verdict,
                           'first_divergence_magnitude_gap': magnitude_gap,
                           'verdict_sentence': verdict_sentence},
              'limitations': ['Content-free structure arithmetic only: types, canonical byte '
                              'counts, tool names and SHAs; no message content, tool '
                              'arguments, wire bytes, tokens or costs.',
                              'S4 bytes are canonical payload bytes, not tokens or cost; '
                              'assistant/message and tool/call contributions are reported '
                              'separately so the carrier is visible.',
                              'Public replay verifies projection arithmetic and source '
                              'binding; private-archive authenticity is attested only by '
                              'SHA pinning plus the batch trace-incident true-body record.',
                              'Score receipts are side-by-side context only; no causal '
                              'claim between S4 structure and scores.',
                              'No new product runs; no scores rejudged; no pinned pages '
                              'modified.']}
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--archive-root', type=Path, required=True,
                        help='root holding dsh/runs/<slot>/agent-session true-body archives')
    parser.add_argument('--output', type=Path, help='new exclusive destination; default stdout summary only')
    args = parser.parse_args(argv)
    try:
        result = analyze(args.root, args.archive_root)
        if args.output:
            text = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2,
                              allow_nan=False) + '\n'
            with args.output.open('x', encoding='utf-8') as stream:
                stream.write(text)
        sys.stdout.write(render_summary(result))
    except (Invalid, OSError, ValueError, KeyError, TypeError, IndexError) as error:
        sys.stderr.write('ERROR: ' + str(error) + '\n')
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
