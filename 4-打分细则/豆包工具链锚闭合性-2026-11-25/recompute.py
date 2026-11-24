#!/usr/bin/env python3
"""R13 公开复算器：校验 doubao-anchor-contract.json。"""
import json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT = HERE / 'doubao-anchor-contract.json'
SCHEMA = 'r1109-doubao-anchor-contract-v1'
SLOTS = ('tb-cargo-plan__r1', 'tb-cargo-plan__r2', 'tb-cargo-plan__r3')
UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
HEX64 = re.compile(r'^[0-9a-f]{64}$')


class Invalid(Exception):
    pass


def load_contract(path=None):
    p = Path(path) if path else DEFAULT
    try:
        c = json.loads(p.read_text())
    except Exception as e:
        raise Invalid(f'合同不可读: {e}')
    if c.get('schema') != SCHEMA:
        raise Invalid('schema 不符')
    slots = c.get('slots') or {}
    if set(slots) != set(SLOTS):
        raise Invalid('槽集不符')
    for name, s in slots.items():
        if not (HEX64.match(s.get('traj_sha256') or '') and s.get('n_lines', 0) > 0):
            raise Invalid(f'{name}: 绑定 SHA/行数非法')
        if s.get('envelope_id_keys') != 0 or s.get('envelope_ts_keys') != 0:
            raise Invalid(f'{name}: 信封弱锚复核被违反')
        for k in ('calls_all_uuid', 'refs_all_uuid', 'calls_unique', 'refs_unique',
                  'set_equal', 'seq_equal', 'pair_positional', 'ref_after_call'):
            if s.get(k) is not True:
                raise Invalid(f'{name}: {k} 非 True')
        if s.get('n_calls') != s.get('n_refs') or s['n_calls'] <= 0:
            raise Invalid(f'{name}: calls/refs 计数不等')
        if len(s.get('tool_names') or []) != s['n_calls']:
            raise Invalid(f'{name}: tool_names 长度≠calls')
        if sum((s.get('role_counts') or {}).values()) != s['n_lines']:
            raise Invalid(f'{name}: role 计数和≠行数')
        for sv in (s.get('traj_relative'), s.get('tool_names') and ' '.join(s['tool_names'])):
            if sv and re.search(r'm_[A-Za-z0-9]{6,}', sv):
                raise Invalid(f'{name}: 内容无关门命中（mid 形串）')
    cr = c.get('cross') or {}
    if cr.get('counts_equal_across_runs') is not False:
        raise Invalid('跨 run 计数恒同声明与实测不符')
    if cr.get('pc_registered') is None:
        raise Invalid('PC 方差登记缺失')
    nm = c.get('near_miss') or {}
    if nm.get('count') != 5 or nm.get('all_rejected') is not True or not nm.get('weak_style'):
        raise Invalid('近错声明不符')
    vd = c.get('verdict') or {}
    if vd.get('PB') != 'PASS' or vd.get('PC') != 'PASS_variance_registered':
        raise Invalid('verdict 枚举不符')
    if c.get('pe_correction_registered') is None:
        raise Invalid('PE 订正登记缺失')
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
        'pairs': {k: slots[k]['n_calls'] for k in SLOTS},
        'envelope_id_keys': 0,
        'tool_names_equal_across_runs': c['cross']['tool_names_equal_across_runs'],
    }, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
