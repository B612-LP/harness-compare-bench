#!/usr/bin/env python3
"""工具结果下游性判定（2026-11-16）离线验证。只读 stdlib；不联网、不起子进程、无 git 命令。

对 R3不稳定来源分解定位出的环境/任务族主导组（exercism-py-6 三对两两 + dabstep-payments-10
r2vsr3，共 4 比较对、5 槽）做逐项下游性判定：每个 function_call_output 与其配对
function_call（response_item 流内 call_id 联结）在两槽间的 canonical 字节是否同步不同。
预注册页冻结于本包 README.md（SHA256 钉定于 PREREG_SHA256，本脚本不修改它）。

联结纪律（冻结）：唯一联结键是 call_id 全值；联结缺失或一对多歧义记 unlinked 单列，
不得猜测配对（不做位置对齐、不做 call_id 前缀部分匹配）。若联结面与预期不符或全部
unlinked，按预注册 §3 降级为结构登记，不给下游性结论。R3 硬等：五槽 R3 总和与逐型
分解必须同时等于本文件冻结常量与 R3 包 result.json（字节钉定）中的值，任何漂移 exit 2。

内容无关纪律：只记录事件型、call_id、函数名、canonical 字节数与 SHA；不记录参数或
输出内容。exit 0 / exit 2 纪律；python3 与 python3 -O 双档 stdout 逐字节一致（不用 assert）。
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = '4-打分细则/工具结果下游性判定-2026-11-16'
R3_HERE = '4-打分细则/R3不稳定来源分解-2026-11-16'
PREREG_SHA256 = 'df7e86497676da79fe238824a5178dfd9dd8fc91eef0d8e9979d89245f38a3dd'
R3_RESULT_SHA256 = '8b03be40cb53f0a562d8b6b8a006a8e97d1733d8a9da15df8dfc67b0fbb83188'
R3_VERIFY_SHA256 = '32607970570d086797562fd1805a88e0a4b9fcfc1afee67d86e7a5618020bc7b'
R3_SCHEMA = 'r3-decomp-projection-v1'
SLOTS = ('codex__exercism-py-6__r1', 'codex__exercism-py-6__r2', 'codex__exercism-py-6__r3',
         'codex__dabstep-payments-10__r2', 'codex__dabstep-payments-10__r3')
PAIRS = (('exercism_r1vsr2', 'codex__exercism-py-6__r1', 'codex__exercism-py-6__r2'),
         ('exercism_r1vsr3', 'codex__exercism-py-6__r1', 'codex__exercism-py-6__r3'),
         ('exercism_r2vsr3', 'codex__exercism-py-6__r2', 'codex__exercism-py-6__r3'),
         ('dabstep_r2vsr3', 'codex__dabstep-payments-10__r2', 'codex__dabstep-payments-10__r3'))
# 归档钉定（ARCHIVE_SOURCES 模式，与 R3 result.json trace_bindings 运行时双向对账）。
ARCHIVE_SOURCES = {
    'codex__exercism-py-6__r1': (
        'codex/runs/codex__exercism-py-6__r1/agent-session/rollout-2026-11-09T13-38-41-01a1bed0-dc97-7b41-b228-5d6153a1118c.jsonl',
        'e355baeb2cfcf644a5f9cf6e9017011a78d95e2050a11ce2d37acfc081639cac'),
    'codex__exercism-py-6__r2': (
        'codex/runs/codex__exercism-py-6__r2/agent-session/rollout-2026-11-09T13-39-10-01a1bed1-4f76-72f1-9b82-6a08a5a4e671.jsonl',
        'a866cd55cc64db6b5ad69436bec7b1c3124d406d42541137bc1077ebd0412796'),
    'codex__exercism-py-6__r3': (
        'codex/runs/codex__exercism-py-6__r3/agent-session/rollout-2026-11-09T13-39-33-01a1bed1-a937-7a62-a054-84041d4c6f33.jsonl',
        '0e64e0c436a0f24a5cd51cbabcf2425b4da559781d298e4447c8bf0db7f12c49'),
    'codex__dabstep-payments-10__r2': (
        'codex/runs/codex__dabstep-payments-10__r2/agent-session/rollout-2026-11-09T13-27-41-01a1bec6-c9ba-7813-8188-781d6e4d7396.jsonl',
        'e5ee7b2bdd44d0fbedf9ff55d27edd4cdb0db6457ba0335a6331d387b71457a9'),
    'codex__dabstep-payments-10__r3': (
        'codex/runs/codex__dabstep-payments-10__r3/agent-session/rollout-2026-11-09T13-33-42-01a1becc-4bf9-79a3-a988-6c97b6ccba16.jsonl',
        'be045ce4457d98ac8934cfcaddfc0a1759ee3ce6cce79139822cac7490b66c2e'),
}
# R3 逐槽冻结目标值（R3 result.json 字节钉定内的 per-slot 值；运行时与文件值与本脚本
# 重算值三方硬等，任何漂移 exit 2）。
FROZEN_R3 = {
    'codex__exercism-py-6__r1': {'r3_total_bytes': 91495,
                                 'per_type_bytes': {'function_call': 10475, 'function_call_output': 68188,
                                                    'message': 7239, 'reasoning': 5593}},
    'codex__exercism-py-6__r2': {'r3_total_bytes': 60064,
                                 'per_type_bytes': {'function_call': 6318, 'function_call_output': 40782,
                                                    'message': 7246, 'reasoning': 5718}},
    'codex__exercism-py-6__r3': {'r3_total_bytes': 80553,
                                 'per_type_bytes': {'function_call': 7174, 'function_call_output': 58562,
                                                    'message': 7200, 'reasoning': 7617}},
    'codex__dabstep-payments-10__r2': {'r3_total_bytes': 334724,
                                       'per_type_bytes': {'function_call': 65049, 'function_call_output': 133869,
                                                          'message': 10617, 'reasoning': 125189}},
    'codex__dabstep-payments-10__r3': {'r3_total_bytes': 286469,
                                       'per_type_bytes': {'function_call': 52273, 'function_call_output': 105274,
                                                          'message': 13625, 'reasoning': 115297}},
}
R3_BASELINE_AT_RUN = '4b5aaecc04a11fd47a04af47abdcb70a520657d7'
NOTE = ('Per-item tool-result downstream judgment over 4 preregistered comparison pairs '
        '(exercism-py-6 r1vsr2/r1vsr3/r2vsr3 + dabstep-payments-10 r2vsr3). Content-free: '
        'event types, call_id, function names, canonical byte counts and SHAs only; no tool '
        'arguments or output content. The only join key is the full call_id value inside the '
        'response_item streams; no positional alignment or partial-prefix matching is attempted. '
        'Public replay verifies content-free linkage arithmetic and source binding; private raw '
        'authenticity NOT certified. No new runs; no gate or score changes.')


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def canon(value):
    """canonical JSON 字节（与 v1.1/R3/bird 包逐字一致）。"""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None, 'invalid SHA256')
    return value


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


def load_trace(archive_root, relative, expected_sha, slot):
    """Load one archived Codex rollout, SHA-verified against its pinned identity."""
    require(isinstance(relative, str) and relative, 'missing trace archive path: ' + slot)
    path = Path(relative)
    require(not path.is_absolute() and '..' not in path.parts, 'unsafe trace path: ' + slot)
    absolute = (archive_root / path).resolve()
    require(archive_root == absolute or archive_root in absolute.parents, 'trace escapes archive root: ' + slot)
    if not absolute.is_file():
        raise Invalid('missing archived trace for slot ' + slot + ' (comparison pair source): ' + relative)
    raw = absolute.read_bytes()
    require(sha(raw) == digest(expected_sha), 'archived original SHA mismatch: ' + relative)
    events = []
    for line in raw.decode('utf-8').splitlines():
        require(line.strip() != '', 'blank line inside trace: ' + relative)
        try:
            events.append(json.loads(line))
        except ValueError as error:
            raise Invalid('unparsable trace line in ' + relative + ': ' + str(error)) from error
    require(events and all(isinstance(e, dict) and isinstance(e.get('type'), str) for e in events),
            'bad trace event schema: ' + relative)
    return events


def call_id_of(payload):
    """call_id 字段提取：存在且为非空 str 才算联结键；否则 None（联结缺失）。"""
    value = payload.get('call_id')
    return value if isinstance(value, str) and value else None


def extract_items(events):
    """单槽 response_item 流投影：R3 逐型重算值 + call/output 联结底账（保流内顺序）。

    结构异常（response_item 缺 payload、payload.type 缺失）fail-closed exit 2；
    call_id 字段缺失不是异常，是逐项 unlinked 的联结缺失。
    """
    calls_by_id = {}
    outputs_by_id = {}
    outputs_order = []
    per_type = {}
    r3_total = 0
    response_items = 0
    call_count = 0
    output_count = 0
    outputs_missing_call_id = 0
    calls_missing_call_id = 0
    for event in events:
        if event['type'] != 'response_item':
            continue
        response_items += 1
        payload = event.get('payload')
        require(isinstance(payload, dict), 'response_item without payload object')
        ptype = payload.get('type')
        require(isinstance(ptype, str) and ptype, 'payload.type missing or not a string')
        size = len(canon(payload))
        per_type[ptype] = per_type.get(ptype, 0) + size
        r3_total += size
        if ptype == 'function_call':
            call_count += 1
            cid = call_id_of(payload)
            if cid is None:
                calls_missing_call_id += 1
            calls_by_id.setdefault(cid, []).append(payload)
        elif ptype == 'function_call_output':
            output_count += 1
            cid = call_id_of(payload)
            if cid is None:
                outputs_missing_call_id += 1
            outputs_by_id.setdefault(cid, []).append(payload)
            outputs_order.append(payload)
    call_ids = sorted({k for k in calls_by_id if k is not None})
    output_ids = sorted({k for k in outputs_by_id if k is not None})
    return {'calls_by_id': calls_by_id, 'outputs_by_id': outputs_by_id, 'outputs_order': outputs_order,
            'response_item_count': response_items, 'call_count': call_count, 'output_count': output_count,
            'calls_missing_call_id': calls_missing_call_id, 'outputs_missing_call_id': outputs_missing_call_id,
            'call_id_field_present': calls_missing_call_id == 0 and outputs_missing_call_id == 0
                                     and bool(call_ids or output_ids),
            'call_id_namespace_sha256': sha(canon(call_ids + ['|outputs|'] + output_ids)),
            'r3_recomputed': {'r3_total_bytes': r3_total, 'per_type_bytes': per_type}}


def intra_linkage(items):
    """槽内联结结构：每个 function_call_output 项记 linked / orphan / ambiguous / missing_call_id。"""
    linked = 0
    orphan = 0
    ambiguous = 0
    ambiguous_call_ids = 0
    calls_without_output = 0
    for cid, clist in items['calls_by_id'].items():
        if cid is None:
            continue
        if not items['outputs_by_id'].get(cid):
            calls_without_output += 1
    for cid, olist in items['outputs_by_id'].items():
        if cid is None:
            continue
        clist = items['calls_by_id'].get(cid)
        if not clist:
            orphan += len(olist)
        elif len(clist) != 1 or len(olist) != 1:
            ambiguous += len(olist)
            ambiguous_call_ids += 1
        else:
            linked += 1
    return {'linked_outputs': linked, 'orphan_outputs': orphan, 'ambiguous_outputs': ambiguous,
            'ambiguous_call_ids': ambiguous_call_ids, 'calls_without_output': calls_without_output,
            'outputs_missing_call_id': items['outputs_missing_call_id']}


def call_params_canon(call_payload):
    """冻结口径：配对调用的 canonical 参数字节 = canon({'name':…, 'arguments':…})。

    只取函数名与 arguments 两字段（预注册括号定义）；call payload 其余字段
    （status/id/passthrough 等）不参与 calls_same/calls_differ 判定。
    """
    return canon({'name': call_payload.get('name'), 'arguments': call_payload.get('arguments')})


def classify_pair(pair_name, slot_a, slot_b, items_a, items_b):
    """预注册 §2 逐项分类。计数单位 = function_call_output 项（两槽并、流内顺序）。

   联结成立（两槽内该 call_id 均 1:1）才比较：输出 canonical 字节取整个 payload，
    配对调用参数字节取 name+arguments。联结缺失/歧义（槽内 orphan/ambiguous、无
    call_id、对槽缺 counterpart 或对槽歧义）→ unlinked，不猜测配对。
    """
    counts = {'outputs_differ_calls_differ': 0, 'outputs_differ_calls_same': 0, 'outputs_same': 0}
    reasons = Counter()
    linked_units = 0
    clean_unit_ids = []
    ids_a = {k for k in items_a['outputs_by_id'] if k is not None}
    ids_b = {k for k in items_b['outputs_by_id'] if k is not None}
    intersection = sorted(ids_a & ids_b)
    unlinked = 0
    for own_slot, own_items, other_items in ((slot_a, items_a, items_b), (slot_b, items_b, items_a)):
        for payload in own_items['outputs_order']:
            cid = call_id_of(payload)
            if cid is None:
                unlinked += 1
                reasons['missing_call_id_field'] += 1
                continue
            clist = own_items['calls_by_id'].get(cid)
            olist = own_items['outputs_by_id'].get(cid)
            if clist is None:
                unlinked += 1
                reasons['orphan_output_no_call'] += 1
                continue
            if len(clist) != 1 or len(olist) != 1:
                unlinked += 1
                reasons['ambiguous_one_to_many'] += 1
                continue
            other_olist = other_items['outputs_by_id'].get(cid)
            other_clist = other_items['calls_by_id'].get(cid)
            if other_olist is None or other_clist is None:
                unlinked += 1
                reasons['counterpart_missing_other_slot'] += 1
                continue
            if len(other_olist) != 1 or len(other_clist) != 1:
                unlinked += 1
                reasons['counterpart_ambiguous_other_slot'] += 1
                continue
            out_own = canon(payload)
            out_other = canon(other_olist[0])
            prm_own = call_params_canon(clist[0])
            prm_other = call_params_canon(other_clist[0])
            if out_own != out_other:
                if prm_own != prm_other:
                    counts['outputs_differ_calls_differ'] += 1
                else:
                    counts['outputs_differ_calls_same'] += 1
            else:
                counts['outputs_same'] += 1
            if own_slot == slot_a:
                linked_units += 1
                clean_unit_ids.append(cid)
    calls_same_items = []
    for cid in sorted(set(clean_unit_ids)):
        pa = items_a['outputs_by_id'][cid][0]
        pb = items_b['outputs_by_id'][cid][0]
        fa = items_a['calls_by_id'][cid][0]
        fb = items_b['calls_by_id'][cid][0]
        out_a, out_b = canon(pa), canon(pb)
        if out_a == out_b:
            continue
        if call_params_canon(fa) != call_params_canon(fb):
            continue
        name = fa.get('name')
        calls_same_items.append({'call_id': cid, 'function_name': name if isinstance(name, str) else None,
                                 'slots': [slot_a, slot_b], 'output_bytes': [len(out_a), len(out_b)]})
    return {'pair': pair_name, 'slots': [slot_a, slot_b],
            'output_items': {'slot_a': items_a['output_count'], 'slot_b': items_b['output_count']},
            'counts': counts, 'outputs_differ_total': counts['outputs_differ_calls_differ']
                                                       + counts['outputs_differ_calls_same'],
            'unlinked': unlinked, 'unlinked_reasons': dict(sorted(reasons.items())),
            'linked_units': linked_units, 'cross_slot_call_id_intersection': len(intersection),
            'calls_same_items': calls_same_items}


def select_verdict(pairs):
    """冻结判定顺序：无任何联结成立单元 → 结构降级；有 calls_same → 工具非确定性；
    其余（含零 outputs_differ 的平凡情形）→ 全部下游。unlinked 恒单列不并入前两类。"""
    linked_total = sum(p['linked_units'] for p in pairs)
    calls_same_total = sum(p['counts']['outputs_differ_calls_same'] for p in pairs)
    if linked_total == 0:
        return 'D-STRUCTURAL-DEGRADED'
    if calls_same_total > 0:
        return 'D-TOOL-NONDETERMINISM'
    return 'D-ALL-DOWNSTREAM'


def analyze(root, archive_root=None, r3_result=None):
    """全量重算。r3_result 仅测试注入用（绕过文件字节钉定以直击硬等值分支）；
    默认路径读 R3 result.json 并做 SHA 钉定。"""
    root = Path(root).resolve()
    prereg_raw = (root / HERE / 'README.md').read_bytes()
    require(sha(prereg_raw) == PREREG_SHA256, 'prereg README SHA mismatch: ' + HERE + '/README.md')
    r3_path = root / R3_HERE / 'result.json'
    r3_raw = r3_path.read_bytes()
    require(sha(r3_raw) == R3_RESULT_SHA256, 'R3 result.json SHA mismatch: ' + R3_HERE + '/result.json')
    if r3_result is None:
        r3_result = json.loads(r3_raw)
    require(isinstance(r3_result, dict) and r3_result.get('schema') == R3_SCHEMA, 'bad R3 result schema')
    r3_verify_raw = (root / R3_HERE / 'verify.py').read_bytes()
    require(sha(r3_verify_raw) == R3_VERIFY_SHA256, 'R3 verify.py SHA mismatch (frozen reference state)')
    baseline = resolve_head(root)
    require(archive_root is not None, '--archive-root is required')
    archive_root = Path(archive_root).resolve()
    require(archive_root.is_dir(), 'archive root not found (pass --archive-root)')
    require(set(ARCHIVE_SOURCES) == set(SLOTS), 'ARCHIVE_SOURCES slot set drifted')
    r3_slots = {row.get('slot'): row for row in r3_result.get('slots', []) if isinstance(row, dict)}
    r3_bindings = {row.get('slot'): row for row in r3_result.get('trace_bindings', []) if isinstance(row, dict)}
    slot_outputs = []
    slot_items = {}
    for slot in SLOTS:
        relative, expected_sha = ARCHIVE_SOURCES[slot]
        binding = r3_bindings.get(slot)
        require(isinstance(binding, dict), 'R3 result.json missing trace binding: ' + slot)
        require(binding.get('archive_relative_path') == relative and binding.get('sha256') == expected_sha,
                'ARCHIVE_SOURCES pin disagrees with R3 result.json binding: ' + slot)
        events = load_trace(archive_root, relative, expected_sha, slot)
        items = extract_items(events)
        recomputed = items['r3_recomputed']
        frozen = FROZEN_R3[slot]
        require(recomputed['r3_total_bytes'] == frozen['r3_total_bytes'],
                'R3 hard-equal drift vs frozen constant (total): ' + slot)
        require(recomputed['per_type_bytes'] == frozen['per_type_bytes'],
                'R3 hard-equal drift vs frozen constant (per-type): ' + slot)
        file_slot = r3_slots.get(slot)
        require(isinstance(file_slot, dict), 'R3 result.json missing slot row: ' + slot)
        require(file_slot.get('r3_total_bytes') == recomputed['r3_total_bytes'],
                'R3 hard-equal drift vs R3 result.json (total): ' + slot)
        require(file_slot.get('per_type_bytes') == recomputed['per_type_bytes'],
                'R3 hard-equal drift vs R3 result.json (per-type): ' + slot)
        linkage = intra_linkage(items)
        slot_outputs.append({'slot': slot, 'trace_sha256': expected_sha, 'trace_archive_relative_path': relative,
                             'event_count': len(events), 'response_item_count': items['response_item_count'],
                             'function_call_count': items['call_count'],
                             'function_call_output_count': items['output_count'],
                             'r3_recomputed': recomputed, 'r3_hard_equal': True,
                             'intra_slot_linkage': linkage,
                             'call_id_field_present': items['call_id_field_present'],
                             'call_id_namespace_sha256': items['call_id_namespace_sha256']})
        slot_items[slot] = items
    require(len(slot_outputs) == 5, 'slot count changed')
    pair_results = []
    for pair_name, slot_a, slot_b in PAIRS:
        require(slot_a in slot_items and slot_b in slot_items, 'comparison pair source missing: ' + pair_name)
        pair_results.append(classify_pair(pair_name, slot_a, slot_b, slot_items[slot_a], slot_items[slot_b]))
    require(len(pair_results) == 4, 'comparison pair count changed')
    branch = select_verdict(pair_results)
    calls_same_total = sum(p['counts']['outputs_differ_calls_same'] for p in pair_results)
    outputs_differ_total = sum(p['outputs_differ_total'] for p in pair_results)
    unlinked_total = sum(p['unlinked'] for p in pair_results)
    linked_total = sum(p['linked_units'] for p in pair_results)
    all_call_id_present = all(s['call_id_field_present'] for s in slot_outputs)
    statements = {
        'D-ALL-DOWNSTREAM': 'r1109 检测面内已观测的工具结果字节不稳定全部下游于模型所选调用；环境侧工具非确定性在该检测面未观察到（按检测面限定表述，不改任何门判定）。',
        'D-TOOL-NONDETERMINISM': '存在同参异果：至少一项 outputs_differ_calls_same，逐项列证据，不改历史分。',
        'D-STRUCTURAL-DEGRADED': '全部联结单元 unlinked（跨槽 call_id 命名空间零交集，联结面与预期不符）：按预注册 §3 降级为结构登记，如实报告联结结构，不给下游性结论。'}
    return {'schema': 'tool-downstream-judgment-v1', 'prereg_sha256': PREREG_SHA256,
            'baseline_commit': baseline, 'baseline_source': 'resolved from .git HEAD without subprocess calls',
            'note': NOTE,
            'r3_reference': {'package': R3_HERE, 'result_sha256': R3_RESULT_SHA256,
                             'verify_sha256': R3_VERIFY_SHA256, 'baseline_commit_at_r3_run': R3_BASELINE_AT_RUN,
                             'hard_equal_slots': 5, 'hard_equal': True,
                             'frozen_targets': FROZEN_R3,
                             'rule': 'recomputed == frozen constant == R3 result.json value, per slot, total and per-type; any drift exit 2'},
            'contract': {'slots': list(SLOTS), 'slot_total': 5, 'pairs': [p[0] for p in PAIRS], 'pair_total': 4,
                         'join': 'call_id 全值（response_item 流内 function_call ↔ function_call_output；不做位置对齐或前缀部分匹配）',
                         'output_bytes': 'len(canon(function_call_output payload))',
                         'call_param_bytes': "len(canon({'name':…, 'arguments':…}))",
                         'counting_unit': 'function_call_output 项（联结成立的单元两侧各计一项）'},
            'slots': slot_outputs,
            'pairs': pair_results,
            'verdicts': {'branch': branch,
                         'branch_zh': {'D-ALL-DOWNSTREAM': '全部下游（D-ALL-DOWNSTREAM）',
                                       'D-TOOL-NONDETERMINISM': '工具非确定性（D-TOOL-NONDETERMINISM）',
                                       'D-STRUCTURAL-DEGRADED': '结构降级（降级为结构登记）'}[branch],
                         'statement': statements[branch],
                         'downstream_conclusion_issued': branch != 'D-STRUCTURAL-DEGRADED',
                         'outputs_differ_total_all_pairs': outputs_differ_total,
                         'outputs_differ_calls_same_total': calls_same_total,
                         'linked_unit_total': linked_total,
                         'unlinked_item_total': unlinked_total,
                         'call_id_field_present_all_slots': all_call_id_present,
                         'calls_same_items_all_pairs': [item for p in pair_results for item in p['calls_same_items']]},
            'content_free_declaration': '本结果只含事件型、call_id、函数名、canonical 字节数与 SHA256；不含任何工具参数、工具输出内容、消息内容、token 或成本。',
            'limitations': ['联结键冻结为 call_id 全值；Codex call_id 形如 call_<序号>_<随机后缀>，序号逐轮重置、后缀逐运行随机，跨槽零交集为联结面结构性事实。',
                            '未做位置对齐或 call_id 前缀部分匹配：预注册禁止猜测配对；如需序列对应判定须先出新预注册版本。',
                            'canonical JSON 字节非 wire 字节、token 或成本；公开复算不认证私档原件真实性。',
                            '纯事后算法判定：不新增运行、不改任何门判定；R3 与 v1.1 结论不回写。']}


def render_summary(result):
    lines = ['tool-result downstream judgment (schema ' + result['schema'] + ')',
             'prereg sha256 ok: ' + result['prereg_sha256'],
             'baseline: ' + result['baseline_commit'],
             'R3 hard-equal: %d/%d slots recomputed == frozen == R3 result.json (%s)' % (
                 result['r3_reference']['hard_equal_slots'], len(result['slots']),
                 ', '.join(s['slot'].split('__')[1] + ':' + s['slot'][-2:] for s in result['slots']))]
    for pair in result['pairs']:
        counts = pair['counts']
        lines.append('pair %-16s outputs_differ_calls_differ=%d outputs_differ_calls_same=%d outputs_same=%d '
                     'unlinked=%d linked_units=%d cross_slot_call_id_intersection=%d' % (
                         pair['pair'], counts['outputs_differ_calls_differ'], counts['outputs_differ_calls_same'],
                         counts['outputs_same'], pair['unlinked'], pair['linked_units'],
                         pair['cross_slot_call_id_intersection']))
    verdict = result['verdicts']
    lines.append('verdict: %s (%s)' % (verdict['branch'], verdict['branch_zh']))
    lines.append('  ' + verdict['statement'])
    lines.append('totals: outputs_differ=%d calls_same=%d linked_units=%d unlinked_items=%d call_id_field_all_slots=%s' % (
        verdict['outputs_differ_total_all_pairs'], verdict['outputs_differ_calls_same_total'],
        verdict['linked_unit_total'], verdict['unlinked_item_total'],
        'yes' if verdict['call_id_field_present_all_slots'] else 'no'))
    for item in verdict['calls_same_items_all_pairs']:
        lines.append('calls_same: call_id=%s function=%s slots=%s output_bytes=%s' % (
            item['call_id'], item['function_name'], ','.join(item['slots']), item['output_bytes']))
    lines.append('content-free: event types, call_id, function names, canonical byte counts, SHA only; '
                 'no arguments/output content')
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--archive-root', type=Path, required=True,
                        help='root holding codex/runs/<slot>/agent-session archived originals')
    parser.add_argument('--output', type=Path, help='new exclusive destination; default stdout summary only')
    args = parser.parse_args(argv)
    try:
        result = analyze(args.root, args.archive_root)
        if args.output:
            text = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n'
            with args.output.open('x', encoding='utf-8') as stream:
                stream.write(text)
        sys.stdout.write(render_summary(result))
    except (Invalid, OSError, ValueError, KeyError, TypeError, IndexError) as error:
        sys.stderr.write('ERROR: ' + str(error) + '\n')
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
