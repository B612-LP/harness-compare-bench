#!/usr/bin/env python3
"""R16 公开测试：正常夹具 + 注入全拒。"""
import copy, importlib.util, json, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('rc16', HERE / 'recompute.py')
rc16 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc16)

REJECTED = 0


def must_reject(name, mutate):
    global REJECTED
    base = json.loads((HERE / 'wb-temporal-usage.json').read_text())
    bad = mutate(base)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(bad, f, ensure_ascii=False)
        tmp = f.name
    try:
        rc16.load_contract(tmp)
    except rc16.Invalid:
        REJECTED += 1
        return
    raise AssertionError(f'{name}: 未拒绝')


rc16.load_contract()


def a(c):
    c = copy.deepcopy(c)
    c['slots']['wb__dabstep-payments-10__r2']['prompt_side']['prompt_cache_hit_tokens'] += 1
    return c
must_reject('hit+miss 破坏', a)


def b(c):
    c = copy.deepcopy(c)
    c['slots']['wb__tb-cargo-plan__r1']['quota_monotonic'] = False
    return c
must_reject('quota 单调翻转', b)


def cc(c):
    c = copy.deepcopy(c)
    c['slots']['wb__tb-cargo-plan__r2']['credit_sum'] = -1.0
    return c
must_reject('credit 负', cc)


def d(c):
    c = copy.deepcopy(c)
    fc = sorted(c['slots'])
    c['slots'][fc[0]]['first_fc_completion_tokens'] = c['slots'][fc[1]]['first_fc_completion_tokens']
    return c
must_reject('completion 同化', d)


def e(c):
    c = copy.deepcopy(c)
    c['verdict']['PG5_thinking_branch_registered'] = {}
    return c
must_reject('thinking 分支抹除', e)


def f(c):
    c = copy.deepcopy(c)
    s = c['slots'].pop('wb__tb-cargo-plan__r3')
    c['slots']['wb__tb-cargo-plan__r9'] = s
    return c
must_reject('槽名非法', f)


def g(c):
    c = copy.deepcopy(c)
    c['near_miss']['count'] = 3
    return c
must_reject('近错声明改', g)


def h(c):
    c = copy.deepcopy(c)
    c['slots']['wb__dabstep-payments-10__r1']['traj_sha256'] = 'zz'
    return c
must_reject('sha 损坏', h)

print(f'全部夹具拒绝通过：{REJECTED + 1} 项（1 正常 + {REJECTED} 注入）')
