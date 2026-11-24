#!/usr/bin/env python3
"""R12 公开复算器：校验 wb-anchor-contract.json。"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT = HERE / 'wb-anchor-contract.json'
SCHEMA = 'r1109-wb-anchor-contract-v1'
CASES = ('dabstep-payments-10', 'tb-cargo-plan')


class Invalid(Exception):
    pass


def _ts(v):
    return isinstance(v, int)


def load_contract(path=None):
    p = Path(path) if path else DEFAULT
    try:
        c = json.loads(p.read_text())
    except Exception as e:
        raise Invalid(f'合同不可读: {e}')
    if c.get('schema') != SCHEMA:
        raise Invalid('schema 不符')
    slots = c.get('slots') or {}
    expected = {f'{case}__r{k}' for case in CASES for k in (1, 2, 3)}
    if set(slots) != expected:
        raise Invalid('槽集不符')
    for name, s in slots.items():
        if s.get('n_fc') != s.get('n_result') or not isinstance(s.get('n_fc'), int):
            raise Invalid(f'{name}: fc/result 计数不等或非整数')
        for k in ('fc_id_all_uuid', 'fc_parent_all_uuid', 'rd_id_all_uuid', 'rd_parent_all_uuid',
                  'callid_none_uuid', 'fc_ids_unique', 'callids_unique', 'pair_callids_equal_seq',
                  'pair_counts_equal', 'result_after_call', 'fc_ts_strict_increasing'):
            if s.get(k) is not True:
                raise Invalid(f'{name}: {k} 非 True')
        if not (_ts(s.get('ts_min')) and _ts(s.get('ts_max')) and s['ts_min'] < s['ts_max']):
            raise Invalid(f'{name}: ts 区间非法')
        if s.get('parent_in_msg_pool') == s.get('parent_total'):
            raise Invalid(f'{name}: 悬挂瞒报（parent 池命中=全额不符实测）')
        if s.get('status_set') != ['completed']:
            raise Invalid(f'{name}: status 集不符')
    tb = (c.get('time_blocks') or {})
    for case in CASES:
        b = tb.get(case) or {}
        if b.get('disjoint_sorted') is not True:
            raise Invalid(f'{case}: 时序分块不成立')
        ivs = b.get('intervals') or []
        if len(ivs) != 3 or not all(_ts(a) and _ts(bb) and a < bb for a, bb in ivs):
            raise Invalid(f'{case}: 区间非法')
        if not all(ivs[i][1] < ivs[i + 1][0] for i in range(2)):
            raise Invalid(f'{case}: 区间重叠')
    nm = c.get('near_miss') or {}
    if nm.get('count') != 8 or nm.get('all_rejected') is not True:
        raise Invalid('近错声明不符')
    vd = c.get('verdict') or {}
    if vd.get('PD') != 'PASS_hanging_registered':
        raise Invalid('PD 悬挂登记 verdict 不符')
    if any(v == 'FAIL' for v in vd.values()):
        raise Invalid('verdict 含 FAIL')
    tn = c.get('tool_names') or {}
    if set(tn) != expected:
        raise Invalid('tool_names 槽集不符')
    return c


def main():
    args = sys.argv[1:]
    path = None
    if '--contract' in args:
        path = args[args.index('--contract') + 1]
    c = load_contract(path)
    slots = c['slots']
    print('CONTRACT OK', json.dumps({
        'slots': len(slots),
        'pair_closed': sum(1 for s in slots.values() if s['pair_callids_equal_seq']),
        'ts_strict': sum(1 for s in slots.values() if s['fc_ts_strict_increasing']),
        'parent_pool_hits': sum(s['parent_in_msg_pool'] for s in slots.values()),
        'parent_total': sum(s['parent_total'] for s in slots.values()),
        'time_blocks_disjoint': 2,
    }, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
