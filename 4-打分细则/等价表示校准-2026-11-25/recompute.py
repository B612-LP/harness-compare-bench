#!/usr/bin/env python3
"""R8 公开复算器：校验等价表示校准合同（内容无关、可注入）。"""
import argparse
import json
import sys

EXPECTED_SLOTS = ['dsh__dabstep-payments-10__r1', 'codex__dabstep-payments-10__r1',
                  'wb__dabstep-payments-10__r1', 'doubao__tb-cargo-plan__r1']
REPS = {'dsh__dabstep-payments-10__r1': 5, 'codex__dabstep-payments-10__r1': 4,
        'wb__dabstep-payments-10__r1': 3, 'doubao__tb-cargo-plan__r1': 3}


class Invalid(Exception):
    pass


def _is_hex64(s):
    return isinstance(s, str) and len(s) == 64 and all(c in '0123456789abcdef' for c in s)


def load_contract(p=None):
    path = p or 'equiv-calibration-contract.json'
    try:
        return json.loads(open(path, encoding='utf-8').read())
    except Exception as e:
        raise Invalid(f'合同读取失败: {e}')


def verify(c):
    if c.get('schema') != 'r1109-equiv-calibration-v1':
        raise Invalid('schema 不符')
    slots = c.get('slots')
    if not isinstance(slots, list) or len(slots) != 4:
        raise Invalid('槽列表不符')
    names = [s.get('slot') for s in slots]
    if names != EXPECTED_SLOTS:
        raise Invalid(f'槽名或顺序不符: {names}')
    dom = c.get('declared_equivalence_domain', {}).get('styles', [])
    if not dom or len(dom) != 5:
        raise Invalid('声明等价域缺失')
    dd = c.get('declared_distinct_variants', {})
    if set(dd) != {'int2float', 'nfc2nfd'}:
        raise Invalid('声明内容级变体缺失')
    for s in slots:
        if not _is_hex64(s.get('raw_sha256')):
            raise Invalid(f"{s['slot']} raw_sha256 非 hex64")
        n = s.get('n_lines')
        if not isinstance(n, int) or n <= 0:
            raise Invalid(f"{s['slot']} 行数非法")
        reps = s.get('representations', {})
        if len(reps) != REPS[s['slot']]:
            raise Invalid(f"{s['slot']} 表示数不符: {len(reps)} != {REPS[s['slot']]}")
        for st, v in reps.items():
            if st not in dom:
                raise Invalid(f'{s["slot"]} 表示 {st} 不在声明域内')
            if not (isinstance(v, dict) and v.get('lines') == n and v.get('projection_stable') is True):
                raise Invalid(f'{s["slot"]}/{st} 投影不稳定或行数不符')
        if s.get('all_representations_stable') is not True:
            raise Invalid(f'{s["slot"]} 汇总稳定位为假')
        sv = s.get('semantic_variants', {})
        for vn in ('int2float', 'nfc2nfd'):
            verdict = sv.get(vn, {}).get('verdict')
            if verdict not in ('detected', 'no-carrier'):
                raise Invalid(f'{s["slot"]}/{vn} 判定非法: {verdict}')
            if verdict == 'detected' and 'carrier_line' not in sv[vn]:
                raise Invalid(f'{s["slot"]}/{vn} detected 缺载体行')
    return {'slots': 4, 'representations_total': sum(REPS.values()),
            'semantic_detected': sum(1 for s in slots for vn in ('int2float', 'nfc2nfd')
                                     if s['semantic_variants'][vn]['verdict'] == 'detected'),
            'semantic_no_carrier': sum(1 for s in slots for vn in ('int2float', 'nfc2nfd')
                                       if s['semantic_variants'][vn]['verdict'] == 'no-carrier')}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--contract', default='equiv-calibration-contract.json')
    a = ap.parse_args()
    c = load_contract(a.contract)
    s = verify(c)
    print('CONTRACT OK', json.dumps(s, ensure_ascii=False))


if __name__ == '__main__':
    main()
