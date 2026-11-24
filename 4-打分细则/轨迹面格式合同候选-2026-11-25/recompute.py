#!/usr/bin/env python3
"""R3 轨迹面格式合同候选 — 公开复算器。

只吃钉定统计件 trajectory-contract.json（内容无关：计数/SHA/关系判定/掩蔽集声明），
做内部一致性复算；轨迹正文不在公开范围（原始档案为私有冻结原档）。

用法：
    python3 recompute.py                 # 与本文件同目录的 trajectory-contract.json
    python3 recompute.py <path-to-json>  # 指定路径
    作为模块：load_contract(c=None) 可注入 dict（供测试用近错夹具）
"""
import json
import re
import sys
from pathlib import Path

SCHEMA = 'r1109-trajectory-contract-v1'
WB_ENV_MASK = ['id', 'sessionId', 'timestamp', '_meta']
WB_PD_MASK = ['conversationRequestId']
KNOWN_WB_TYPES = {'session-meta', 'message', 'file-history-snapshot', 'ai-title',
                  'function_call', 'function_call_result', 'reasoning'}
HEX64 = re.compile(r'^[0-9a-f]{64}$')


class Invalid(Exception):
    pass


def load_contract(c=None):
    if c is not None:
        if not isinstance(c, dict):
            raise Invalid('contract 必须是 dict')
        return c
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / 'trajectory-contract.json'
    try:
        raw = path.read_bytes()
    except OSError as e:
        raise Invalid(f'无法读取 {path}: {e}')
    try:
        obj = json.loads(raw)
    except ValueError as e:
        raise Invalid(f'JSON 解析失败: {e}')
    if not isinstance(obj, dict):
        raise Invalid('顶层必须是 object')
    return obj


def _need(cond, msg):
    if not cond:
        raise Invalid(msg)


def verify(c):
    """全部通过返回摘要 dict；任一不满足抛 Invalid。"""
    _need(c.get('schema') == SCHEMA, f'schema 不符: {c.get("schema")!r}')

    files = c.get('archive_binding', {}).get('files')
    _need(isinstance(files, dict) and files, 'archive_binding.files 缺失')
    for key, f in files.items():
        _need(HEX64.match(f.get('sha256', '')), f'{key}: sha256 非 64 位小写 hex')
        _need(isinstance(f.get('bytes'), int) and f['bytes'] >= 0, f'{key}: bytes 非法')

    wb = c.get('workbuddy')
    _need(isinstance(wb, dict), 'workbuddy 段缺失')
    slots = wb.get('slots')
    _need(isinstance(slots, dict) and slots, 'workbuddy.slots 缺失')

    type_totals = {}
    for name, s in slots.items():
        _need(isinstance(s.get('n_lines'), int) and s['n_lines'] > 0, f'{name}: n_lines 非法')
        tc = s.get('type_counts')
        _need(isinstance(tc, dict) and tc, f'{name}: type_counts 缺失')
        _need(sum(tc.values()) == s['n_lines'], f'{name}: type_counts 之和 != n_lines')
        for t, n in tc.items():
            type_totals[t] = type_totals.get(t, 0) + n
        census = s.get('usage_census')
        _need(isinstance(census, dict), f'{name}: usage_census 缺失')
        rel = census.get('relations')
        _need(isinstance(rel, dict), f'{name}: relations 缺失')
        n = rel.get('n')
        _need(isinstance(n, int) and n >= 0, f'{name}: relations.n 非法')
        for k in ('hit+miss==prompt', 'norm==raw_prompt_completion',
                  'totalTokens==in+out', 'details_cached==hit',
                  'details.cached_tokens==hit'):
            _need(rel.get(k) == n, f'{name}: 关系 {k} != n（{rel.get(k)} != {n}）')
        _need(census.get('fc_with_rawUsage', -1) + census.get('msg_with_rawUsage', -1) == n,
              f'{name}: fc_with_rawUsage+msg_with_rawUsage != n')
        _need(HEX64.match(s.get('canon_stream_sha256', '')), f'{name}: canon_stream_sha256 非法')

    union = wb.get('type_union')
    _need(isinstance(union, dict) and union, 'workbuddy.type_union 缺失')
    _need(union == type_totals, 'type_union 与各槽 type_counts 汇总不符')
    _need(set(union) <= KNOWN_WB_TYPES, f'出现未枚举类型: {sorted(set(union) - KNOWN_WB_TYPES)}')

    mask = wb.get('mask_set')
    _need(isinstance(mask, dict), 'mask_set 缺失')
    _need(mask.get('envelope_keys_removed') == WB_ENV_MASK, f'信封掩蔽集不符: {mask.get("envelope_keys_removed")}')
    _need(mask.get('providerData_removed') == WB_PD_MASK, 'providerData 掩蔽集不符')
    names = [m.get('name') for m in mask.get('text_masks', [])]
    _need(names == ['slot_path', 'current_time'], f'文本掩蔽集不符: {names}')

    crm = wb.get('cross_run_masked_first_user')
    _need(isinstance(crm, dict) and crm, 'cross_run_masked_first_user 缺失')
    for case, v in crm.items():
        _need(v.get('equal') is True, f'{case}: cross-run masked equal 不成立')
        _need(v.get('distinct_shas') == 1, f'{case}: distinct_shas != 1 与 equal 矛盾')
        _need(v.get('envelope_ids_differ') is True, f'{case}: envelope_ids_differ 必须为 true（掩蔽必要性证据）')

    db = c.get('doubao')
    _need(isinstance(db, dict), 'doubao 段缺失')
    dslots = db.get('slots')
    _need(isinstance(dslots, dict) and dslots, 'doubao.slots 缺失')
    for name, s in dslots.items():
        _need(s.get('id_or_timestamp_lines') == 0, f'{name}: 豆包弱锚被违反（出现 id/timestamp 行）')
        _need(s.get('first_user_present') is False, f'{name}: 豆包不应有 user 行')
        _need(s.get('mid'), f'{name}: mid 缺失')
        _need(HEX64.match(s.get('canon_stream_sha256', '')), f'{name}: canon_stream_sha256 非法')
    af = db.get('anchor_facts')
    _need(af == {'id_lines': 0, 'timestamp_lines': 0, 'user_role_lines': 0}, f'anchor_facts 不符: {af}')
    side = db.get('sidecars')
    _need(isinstance(side, list) and len(side) > 0, 'doubao.sidecars 缺失')
    for e in side:
        _need(HEX64.match(e.get('sha256', '')), f'sidecar {e.get("path")}: sha256 非法')
        _need(isinstance(e.get('bytes'), int) and e['bytes'] >= 0, f'sidecar {e.get("path")}: bytes 非法')

    return {
        'wb_slots': len(slots),
        'doubao_slots': len(dslots),
        'wb_lines': sum(s['n_lines'] for s in slots.values()),
        'doubao_lines': sum(s['n_lines'] for s in dslots.values()),
        'usage_carriers': sum(s['usage_census']['relations']['n'] for s in slots.values()),
        'sidecars': len(side),
        'wb_types': len(union),
        'cross_run_cases': len(crm),
    }


def main():
    try:
        summary = verify(load_contract())
    except Invalid as e:
        print(f'INVALID: {e}', file=sys.stderr)
        sys.exit(1)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
