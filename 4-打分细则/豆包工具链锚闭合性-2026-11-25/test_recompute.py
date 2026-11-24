#!/usr/bin/env python3
"""R13 公开测试：正常夹具 + 注入全部拒绝。"""
import copy, importlib.util, json, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('rc13', HERE / 'recompute.py')
rc13 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc13)

REJECTED = 0


def must_reject(name, mutate):
    global REJECTED
    base = json.loads((HERE / 'doubao-anchor-contract.json').read_text())
    bad = mutate(base)
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(bad, f, ensure_ascii=False)
        tmp = f.name
    try:
        rc13.load_contract(tmp)
    except rc13.Invalid:
        REJECTED += 1
        return
    raise AssertionError(f'{name}: 未拒绝')


rc13.load_contract()


def a(c):
    c = copy.deepcopy(c)
    c['slots']['tb-cargo-plan__r1']['pair_positional'] = False
    return c
must_reject('配对破坏', a)


def b(c):
    c = copy.deepcopy(c)
    c['slots']['tb-cargo-plan__r2']['calls_unique'] = False
    return c
must_reject('唯一性破坏', b)


def cc(c):
    c = copy.deepcopy(c)
    c['slots']['tb-cargo-plan__r3']['envelope_id_keys'] = 4
    return c
must_reject('信封伪造声明', cc)


def d(c):
    c = copy.deepcopy(c)
    c['cross']['counts_equal_across_runs'] = True
    return c
must_reject('跨 run 恒同假声明', d)


def e(c):
    c = copy.deepcopy(c)
    s = c['slots'].pop('tb-cargo-plan__r1')
    c['slots']['tb-cargo-plan__r9'] = s
    return c
must_reject('槽集破坏', e)


def f(c):
    c = copy.deepcopy(c)
    c['verdict']['PC'] = 'PASS'
    return c
must_reject('PC 伪装恒同', f)


def g(c):
    c = copy.deepcopy(c)
    c['pe_correction_registered'] = None
    return c
must_reject('PE 订正登记抹除', g)


def h(c):
    c = copy.deepcopy(c)
    c['slots']['tb-cargo-plan__r1']['n_refs'] = c['slots']['tb-cargo-plan__r1']['n_calls'] - 1
    return c
must_reject('计数撕裂', h)

print(f'全部夹具拒绝通过：{REJECTED + 1} 项（1 正常 + {REJECTED} 注入）')
