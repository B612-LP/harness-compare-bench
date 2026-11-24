#!/usr/bin/env python3
"""R14 公开复算器：校验 equiv-domain-fullset 合同。"""
import hashlib, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT = HERE / 'doubao-wb-equiv-fullset.json'
SCHEMA = 'r1109-equiv-domain-fullset-v1'
STYLES = {'canon', 'indent2', 'ensure_ascii', 'orig_key_order', 'spaced'}


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
    if c.get('n_slots') != 9 or c.get('all_slots_stable') is not True:
        raise Invalid('全集 stable 声明不足')
    if set(c.get('styles') or []) != STYLES:
        raise Invalid('风格域不符')
    slots = c.get('slots') or {}
    if len(slots) != 9:
        raise Invalid('槽集不是 9')
    EXPECTED = {
        'wb__dabstep-payments-10__r1', 'wb__dabstep-payments-10__r2', 'wb__dabstep-payments-10__r3',
        'wb__tb-cargo-plan__r1', 'wb__tb-cargo-plan__r2', 'wb__tb-cargo-plan__r3',
        'doubao__tb-cargo-plan__r1', 'doubao__tb-cargo-plan__r2', 'doubao__tb-cargo-plan__r3',
    }
    if set(slots) != EXPECTED:
        raise Invalid('槽集与全集白名单不符')
    for name, s in slots.items():
        if not re.match(r'^(wb|doubao)__[a-z0-9-]+__r\d$', name):
            raise Invalid(f'{name}: 槽名形态不符')
        if not _is_hex64(s.get('traj_sha256')):
            raise Invalid(f'{name}: traj sha 非 hex64')
        if s.get('all_stable') is not True or s.get('styles_stable_true') is not True:
            raise Invalid(f'{name}: stable 声明不足')
        if s.get('int_detected_equals_carrier') is not True or s.get('nfc_detected_equals_carrier') is not True:
            raise Invalid(f'{name}: detected==carrier 不成立')
        if s.get('nfc_carrier_lines_count') != len(s.get('nfc_carrier_lines') or []):
            raise Invalid(f'{name}: nfc 计数不一致')
        if name.startswith('doubao__') and s.get('int_carrier_lines_count') != 0:
            raise Invalid(f'{name}: 豆包 int 载体应为 0（实测口径）')
    rep = c.get('r8_slot_reproduction') or {}
    if rep.get('wb__dabstep-payments-10__r1', {}).get('reproduced') is not True:
        raise Invalid('R8 复现声明不足')
    nm = c.get('near_miss') or {}
    if nm.get('count') != 4 or nm.get('all_passed') is not True:
        raise Invalid('近错声明不符')
    # 内容无关门：任何字符串值不得含 mid/路径形
    def walk(v, key=''):
        if isinstance(v, str):
            if re.search(r'm_[A-Za-z0-9]{6,}', v) or re.search(r'(trace|session|agents|runs|system)/', v):
                raise Invalid(f'内容无关门命中: {key}')
        elif isinstance(v, dict):
            for k, v2 in v.items():
                walk(v2, key + '/' + str(k))
        elif isinstance(v, list):
            for i, v2 in enumerate(v):
                walk(v2, f'{key}[{i}]')
    walk(c)
    return c


def main():
    args = sys.argv[1:]
    path = None
    if '--contract' in args:
        path = args[args.index('--contract') + 1]
    c = load_contract(path)
    blob = (Path(path) if path else DEFAULT).read_bytes()
    print('CONTRACT OK', json.dumps({
        'slots': c['n_slots'],
        'all_stable': c['all_slots_stable'],
        'nfc_slots': sum(1 for s in c['slots'].values() if s['nfc_carrier_lines_count'] > 0),
        'sha16': hashlib.sha256(blob).hexdigest()[:16],
    }, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
