#!/usr/bin/env python3
"""R3 recompute.py 测试：正常夹具通过 + 五类近错夹具必须被拒。
夹具=真实 trajectory-contract.json 的深拷贝 + 单字段破坏（不触任何轨迹正文）。
"""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from recompute import Invalid, load_contract, verify  # noqa: E402


def base():
    return copy.deepcopy(json.loads((HERE / 'trajectory-contract.json').read_bytes()))


def expect_invalid(name, c, frag=''):
    try:
        verify(c)
    except Invalid as e:
        if frag and frag not in str(e):
            raise AssertionError(f'{name}: 错误信息缺关键字 {frag!r}: {e}')
        print(f'  [OK] {name} -> 拒（{str(e)[:60]}…）')
        return
    raise AssertionError(f'{name}: 应拒未拒')


def main():
    c = base()
    s = verify(load_contract(c))
    print(f'  [OK] 正常夹具 -> {json.dumps(s, ensure_ascii=False)}')

    expect_invalid('NM-A 关系计数破坏（hit+miss!=n）',
                   _patch(base(), ['workbuddy', 'slots'], lambda slots: slots['tb-cargo-plan__r1']['usage_census']['relations'].__setitem__('hit+miss==prompt', 0)),
                   'hit+miss==prompt')
    expect_invalid('NM-B 等值矛盾（equal=true 但 distinct_shas=3）',
                   _patch(base(), ['workbuddy', 'cross_run_masked_first_user', 'tb-cargo-plan'], lambda v: v.__setitem__('distinct_shas', 3)),
                   'distinct_shas')
    expect_invalid('NM-C 豆包强锚违反（id 行=1）',
                   _patch(base(), ['doubao', 'slots'], lambda slots: slots['tb-cargo-plan__r1'].__setitem__('id_or_timestamp_lines', 1)),
                   '弱锚')
    expect_invalid('NM-D sha 非 hex',
                   _patch(base(), ['archive_binding', 'files'], lambda f: f['workbuddy::tb-cargo-plan__r1'].__setitem__('sha256', 'zz')),
                   'hex')
    expect_invalid('NM-E 掩蔽集缺元素',
                   _patch(base(), ['workbuddy', 'mask_set'], lambda m: m.__setitem__('envelope_keys_removed', ['id', 'sessionId'])),
                   '信封掩蔽集')
    def nmf(d):
        slots, union = d['slots'], d['type_union']
        slots['tb-cargo-plan__r1']['type_counts']['future-unknown'] = 1  # 与 union 一致地同改
        slots['tb-cargo-plan__r1']['n_lines'] += 1
        union['future-unknown'] = 1
    expect_invalid('NM-F 未枚举类型（双字段一致修改，直达类型枚举分支）',
                   _patch2(base(), ['workbuddy', 'slots', 'type_union'], nmf),
                   '未枚举类型')
    print('7/7 OK')


def _patch(c, path, fn):
    obj = c
    for p in path[:-1]:
        obj = obj[p]
    fn(obj[path[-1]])
    return c


def _patch2(c, path, fn):
    """取 path[:-1] 处的 dict，把最后两个键名对应的值打包传给 fn。"""
    obj = c
    for p in path[:-2]:
        obj = obj[p]
    fn({k: obj[k] for k in path[-2:]})
    return c


if __name__ == '__main__':
    main()
