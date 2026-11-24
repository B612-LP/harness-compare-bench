#!/usr/bin/env python3
"""R11 公开复算器：校验 unknown-capture-contract.json 内部一致性与缺席声明。

用法: python3 recompute.py [--contract <路径>]
"""
import hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT = HERE / 'unknown-capture-contract.json'
SCHEMA = 'r1109-unknown-capture-v1'
SLOT = 'dsh__bird-ca-schools-15__r1'
PINNED_ID = None  # 钉定 identity 前十六位由合同自证 + 独审对表


class Invalid(Exception):
    pass


def _is_hex64(s):
    return isinstance(s, str) and len(s) == 64 and all(c in '0123456789abcdef' for c in s)


def _is_hex16(s):
    return isinstance(s, str) and len(s) == 16 and all(c in '0123456789abcdef' for c in s)


def load_contract(path=None):
    p = Path(path) if path else DEFAULT
    try:
        c = json.loads(p.read_text())
    except Exception as e:
        raise Invalid(f'合同不可读: {e}')
    if c.get('schema') != SCHEMA:
        raise Invalid('schema 不符')
    b = c.get('binding') or {}
    if b.get('slot') != SLOT:
        raise Invalid('槽名不符')
    if not (_is_hex64(b.get('zstd_sha256')) and _is_hex64(b.get('pinned_identity_sha256'))):
        raise Invalid('绑定 SHA 非 hex64')
    if b.get('zstd_sha256') != b.get('pinned_identity_sha256') or b.get('match') is not True:
        raise Invalid('绑定不等值')
    r = c.get('reproject') or {}
    if r.get('slot') != SLOT or r.get('rows_match_pinned') is not True or r.get('all_slots_row_exact') is not True:
        raise Invalid('重投影声明不足')
    iv = c.get('inventory') or {}
    for k in ('launch_tree_files', 'request_artifacts', 'request_dirs', 'bird_group_hits'):
        if not isinstance(iv.get(k), int) or isinstance(iv.get(k), bool):
            raise Invalid(f'inventory.{k} 非计数')
    if iv.get('request_artifacts') != 0 or iv.get('request_dirs') != 0 or iv.get('bird_group_hits') != 0:
        raise Invalid('缺席声明被违反')
    if iv.get('launch_tree_files', 0) <= 0:
        raise Invalid('清点计数异常')
    vl = c.get('verdict_ledger') or {}
    FORBIDDEN = {'FAIL', 'MISSING_SOURCE', 'SCORED', 'COST_ESTIMATED'}
    if vl.get('unknowable_bird_r1_this_ring') != 'UNKNOWN_CAPTURE':
        raise Invalid('不可核例 verdict 不符')
    if any(v in FORBIDDEN for v in vl.values()):
        raise Invalid('分数型结论落入不可核槽')
    if vl.get('score_cost_conclusions_from_unknowable') is not False:
        raise Invalid('不可核槽不得产生分数/成本结论')
    tl = c.get('third_party_ledger') or {}
    if tl.get('unknowable_chain', {}).get('status') != 'UNKNOWN_CAPTURE':
        raise Invalid('三链分账不可核例不符')
    if tl.get('unknowable_chain', {}).get('events_reproducible') is not True \
            or tl.get('unknowable_chain', {}).get('request_capture_absent') is not True:
        raise Invalid('不可核例双支据声明不足')
    if tl.get('failure_chain', {}).get('status') != 'SOURCE_MISSING_PRESERVED' \
            or tl.get('positive_chain', {}).get('status') != 'REPRODUCED_ALIGNED':
        raise Invalid('三链分账其余两例不符')
    nm = c.get('near_miss') or {}
    if nm.get('count') != 4 or nm.get('all_rejected') is not True:
        raise Invalid('近错声明不符')
    return c


def main():
    args = sys.argv[1:]
    path = None
    if '--contract' in args:
        path = args[args.index('--contract') + 1]
    c = load_contract(path)
    blob = (Path(path) if path else DEFAULT).read_bytes()
    print('CONTRACT OK', json.dumps({
        'slot': c['binding']['slot'],
        'binding_match': True,
        'request_artifacts': c['inventory']['request_artifacts'],
        'bird_group_hits': c['inventory']['bird_group_hits'],
        'verdict': c['verdict_ledger']['unknowable_bird_r1_this_ring'],
        'sha16': hashlib.sha256(blob).hexdigest()[:16],
    }, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
