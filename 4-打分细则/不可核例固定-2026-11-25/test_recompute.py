#!/usr/bin/env python3
"""R11 公开测试：正常合同接受，字段变异合同拒绝。"""
import copy, importlib.util, json, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('rc11', HERE / 'recompute.py')
rc11 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc11)

REJECTED = 0


def must_reject(name, mutate):
    global REJECTED
    base = json.loads((HERE / 'unknown-capture-contract.json').read_text())
    bad = mutate(base)
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(bad, f, ensure_ascii=False)
        tmp = f.name
    try:
        rc11.load_contract(tmp)
    except rc11.Invalid:
        REJECTED += 1
        return
    raise AssertionError(f'{name}: 未拒绝')


# 正常
rc11.load_contract()

# NM-A：slot 换名
must_reject('slot 改名', lambda c: {**c, 'binding': {**c['binding'], 'slot': 'dsh__bird-ca-schools-15__r2'}})
# NM-B：绑定 SHA 撕裂（match 仍 true）
def nm_b(c):
    c = copy.deepcopy(c)
    c['binding']['zstd_sha256'] = '0' * 64
    return c
must_reject('绑定撕裂', nm_b)
# NM-C：缺席声明违反
def nm_c(c):
    c = copy.deepcopy(c)
    c['inventory']['bird_group_hits'] = 1
    return c
must_reject('缺席违反', nm_c)
# NM-D：verdict 换分数型
def nm_d(c):
    c = copy.deepcopy(c)
    c['verdict_ledger']['unknowable_bird_r1_this_ring'] = 'FAIL'
    return c
must_reject('verdict 换 FAIL', nm_d)
# NM-E：分数结论开关翻 true
def nm_e(c):
    c = copy.deepcopy(c)
    c['verdict_ledger']['score_cost_conclusions_from_unknowable'] = True
    return c
must_reject('分数开关', nm_e)
# NM-F：三链分账失败例状态被改
def nm_f(c):
    c = copy.deepcopy(c)
    c['third_party_ledger']['failure_chain']['status'] = 'REPRODUCED_ALIGNED'
    return c
must_reject('失败例状态改', nm_f)
# NM-G：不可核双支据缺一
def nm_g(c):
    c = copy.deepcopy(c)
    c['third_party_ledger']['unknowable_chain']['events_reproducible'] = False
    return c
must_reject('重投影支据撤', nm_g)
# NM-H：重投影声明降级
def nm_h(c):
    c = copy.deepcopy(c)
    c['reproject']['rows_match_pinned'] = False
    return c
must_reject('重投影降级', nm_h)

print(f'合同测试通过：1 个正常接受，{REJECTED} 个变异拒绝')
