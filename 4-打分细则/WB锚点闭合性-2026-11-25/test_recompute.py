#!/usr/bin/env python3
"""R12 公开测试：正常合同接受，字段变异合同拒绝。"""
import copy, importlib.util, json, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('rc12', HERE / 'recompute.py')
rc12 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc12)

REJECTED = 0


def must_reject(name, mutate):
    global REJECTED
    base = json.loads((HERE / 'wb-anchor-contract.json').read_text())
    bad = mutate(base)
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(bad, f, ensure_ascii=False)
        tmp = f.name
    try:
        rc12.load_contract(tmp)
    except rc12.Invalid:
        REJECTED += 1
        return
    raise AssertionError(f'{name}: 未拒绝')


rc12.load_contract()

# A 配对破坏
def a(c):
    c = copy.deepcopy(c)
    c['slots']['dabstep-payments-10__r1']['pair_callids_equal_seq'] = False
    return c
must_reject('配对破坏', a)
# B 悬挂瞒报
def b(c):
    c = copy.deepcopy(c)
    c['slots']['tb-cargo-plan__r2']['parent_in_msg_pool'] = c['slots']['tb-cargo-plan__r2']['parent_total']
    return c
must_reject('悬挂瞒报', b)
# C ts 非单调
def cc(c):
    c = copy.deepcopy(c)
    c['slots']['tb-cargo-plan__r3']['fc_ts_strict_increasing'] = False
    return c
must_reject('ts 非单调', cc)
# D 分块重叠
def d(c):
    c = copy.deepcopy(c)
    c['time_blocks']['dabstep-payments-10']['disjoint_sorted'] = False
    return c
must_reject('分块重叠', d)
# E 错绑换槽名
def e(c):
    c = copy.deepcopy(c)
    s = c['slots'].pop('dabstep-payments-10__r1')
    c['slots']['dabstep-payments-10__r9'] = s
    return c
must_reject('槽集破坏', e)
# F verdict FAIL
def f(c):
    c = copy.deepcopy(c)
    c['verdict']['PA'] = 'FAIL'
    return c
must_reject('verdict FAIL', f)
# G PD 伪装闭合
def g(c):
    c = copy.deepcopy(c)
    c['verdict']['PD'] = 'PASS'
    return c
must_reject('PD 伪装闭合', g)
# H 区间反向
def h(c):
    c = copy.deepcopy(c)
    ivs = c['time_blocks']['tb-cargo-plan']['intervals']
    c['time_blocks']['tb-cargo-plan']['intervals'] = [ivs[0], ivs[2], ivs[1]]
    return c
must_reject('区间非法', h)

print(f'合同测试通过：1 个正常接受，{REJECTED} 个变异拒绝')
