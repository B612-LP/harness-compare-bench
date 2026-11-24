#!/usr/bin/env python3
"""R8 公开复算器测试：正常合同 + 五篡改夹具全部拒绝。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recompute import Invalid, load_contract, verify

HERE = Path(__file__).resolve().parent
CONTRACT = json.loads((HERE / 'equiv-calibration-contract.json').read_text())
REJECTED = 0


def patched(fn):
    c = json.loads(json.dumps(CONTRACT))
    fn(c)
    return c


def expect_invalid(name, c):
    global REJECTED
    try:
        verify(c)
    except Invalid as e:
        REJECTED += 1
        print(f'  OK {name}: 拒绝（{str(e)[:60]}…）')
        return
    raise SystemExit(f'夹具 {name} 未被拒绝')


s = verify(CONTRACT)
print('normal OK', json.dumps(s, ensure_ascii=False)[:120])

expect_invalid('schema 篡改', patched(lambda c: c.__setitem__('schema', 'other-v1')))
expect_invalid('槽翻转', patched(lambda c: c['slots'].reverse()))
expect_invalid('投影翻假', patched(lambda c: c['slots'][0]['representations']['canon'].__setitem__('projection_stable', False)))
expect_invalid('表示剔除', patched(lambda c: c['slots'][2]['representations'].pop('ensure_ascii')))
expect_invalid('非法判定', patched(lambda c: c['slots'][3]['semantic_variants']['int2float'].__setitem__('verdict', 'MISSED')))
expect_invalid('detected 缺载体行', patched(lambda c: c['slots'][0]['semantic_variants']['int2float'].pop('carrier_line')))

print(f'全部夹具拒绝通过：{REJECTED} 项')
