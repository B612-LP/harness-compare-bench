#!/usr/bin/env python3
"""R16 公开复算器：校验 wb-temporal-usage 合同。"""
import hashlib, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT = HERE / 'wb-temporal-usage.json'
SCHEMA = 'r1109-wb-temporal-usage-v1'


class Invalid(Exception):
    pass


def _is_hex64(s):
    return isinstance(s, str) and len(s) == 64 and all(c in '0123456789abcdef' for c in s)


def load_contract(path=None):
    p = Path(path) if path else DEFAULT
    try:
        c = json.loads(p.read_text())
    except Exception as e:
        raise Invalid(f'合同不可读: {e}')
    if c.get('schema') != SCHEMA:
        raise Invalid('schema 不符')
    slots = c.get('slots') or {}
    if len(slots) != 6:
        raise Invalid('槽集不是 6')
    EXPECTED = {f'wb__{case}__r{r}' for case in ('dabstep-payments-10', 'tb-cargo-plan') for r in (1, 2, 3)}
    if set(slots) != EXPECTED:
        raise Invalid('槽集白名单不符')
    # PG1 恒定性机器重算
    for case in ('dabstep-payments-10', 'tb-cargo-plan'):
        sides = {json.dumps(slots[f'wb__{case}__r{r}']['prompt_side'], sort_keys=True) for r in (1, 2, 3)}
        if len(sides) != 1:
            raise Invalid(f'{case}: prompt 侧三 run 不恒定')
    for name, s in slots.items():
        if not _is_hex64(s.get('traj_sha256')):
            raise Invalid(f'{name}: sha 非 hex64')
        ps = s['prompt_side']
        if ps['prompt_cache_hit_tokens'] + ps['prompt_cache_miss_tokens'] != ps['prompt_tokens']:
            raise Invalid(f'{name}: hit+miss!=prompt')
        if not (isinstance(s['first_fc_credit'], (int, float)) and s['first_fc_credit'] > 0):
            raise Invalid(f'{name}: credit 非正')
        if s['credit_sum'] < 0:
            raise Invalid(f'{name}: credit_sum 负')
        q = s['quota_percent_seq'] if 'quota_percent_seq' in s else None
        if s['quota_monotonic'] is not True:
            raise Invalid(f'{name}: quota 单调声明不足')
        if s['quota_percent_first'] > s['quota_percent_last']:
            raise Invalid(f'{name}: quota 首>尾')
        if not isinstance(s['thinking_nonzero_count'], int) or s['thinking_nonzero_count'] < 0:
            raise Invalid(f'{name}: thinking 计数非法')
        for sv in (json.dumps(s, ensure_ascii=False),):
            if re.search(r'm_[A-Za-z0-9]{6,}', sv) or re.search(r'(trace|session|agents|runs|system)/', sv):
                raise Invalid(f'{name}: 内容无关门命中')
    # PG2 机器重算：首 fc completion 六槽全不同 + credit_sum 互异
    fc = [slots[n]['first_fc_completion_tokens'] for n in sorted(slots)]
    if len(set(fc)) != 6:
        raise Invalid('PG2: completion 六槽非全异')
    cs = [slots[n]['credit_sum'] for n in sorted(slots)]
    if len(set(cs)) != 6:
        raise Invalid('PG2: credit_sum 非全异')
    v = c.get('verdict') or {}
    if not (v.get('PG1') and all(x for x in v['PG1'].values()) if isinstance(v.get('PG1'), dict) else v.get('PG1')):
        raise Invalid('PG1 声明不足')
    if v.get('PG2') is not True or v.get('PG4') is not True or v.get('PG5') is not True:
        raise Invalid('PG 声明不足')
    if not isinstance(v.get('PG5_thinking_branch_registered'), dict) or len(v['PG5_thinking_branch_registered']) != 6:
        raise Invalid('thinking 分支登记缺失')
    for n, s in slots.items():
        if v['PG5_thinking_branch_registered'].get(n) != s['thinking_nonzero_count']:
            raise Invalid(f'{n}: thinking 登记值与槽值撕裂')
    nm = c.get('near_miss') or {}
    if nm.get('count') != 4 or nm.get('all_passed') is not True:
        raise Invalid('近错声明不符')
    tw = c.get('three_way_comparison') or {}
    if not tw.get('wb_raw_prompt'):
        raise Invalid('三方对照缺失')
    return c


def main():
    path = None
    if '--contract' in sys.argv:
        path = sys.argv[sys.argv.index('--contract') + 1]
    c = load_contract(path)
    blob = (Path(path) if path else DEFAULT).read_bytes()
    d1 = c['slots']['wb__dabstep-payments-10__r1']['prompt_side']
    print('CONTRACT OK', json.dumps({
        'slots': 6, 'prompt_side_dabstep': d1, 'quota_first6': [c['slots'][n]['quota_percent_first'] for n in sorted(c['slots'])],
        'sha16': hashlib.sha256(blob).hexdigest()[:16],
    }, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
