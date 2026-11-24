#!/usr/bin/env python3
"""R14 公开测试：正常夹具 + 注入全部拒绝。"""
import copy, importlib.util, json, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('rc14', HERE / 'recompute.py')
rc14 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc14)

REJECTED = 0


def must_reject(name, mutate):
    global REJECTED
    base = json.loads((HERE / 'doubao-wb-equiv-fullset.json').read_text())
    bad = mutate(base)
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(bad, f, ensure_ascii=False)
        tmp = f.name
    try:
        rc14.load_contract(tmp)
    except rc14.Invalid:
        REJECTED += 1
        return
    raise AssertionError(f'{name}: 未拒绝')


rc14.load_contract()


def a(c):
    c = copy.deepcopy(c)
    c['all_slots_stable'] = False
    return c
must_reject('stable 翻假', a)


def b(c):
    c = copy.deepcopy(c)
    c['slots']['wb__dabstep-payments-10__r1']['traj_sha256'] = 'zz'
    return c
must_reject('sha 损坏', b)


def cc(c):
    c = copy.deepcopy(c)
    c['slots']['doubao__tb-cargo-plan__r1']['int_carrier_lines_count'] = 3
    return c
must_reject('豆包 int 载体非零', cc)


def d(c):
    c = copy.deepcopy(c)
    c['slots']['wb__dabstep-payments-10__r1']['nfc_detected_equals_carrier'] = False
    return c
must_reject('detected 撕裂', d)


def e(c):
    c = copy.deepcopy(c)
    c['r8_slot_reproduction']['wb__dabstep-payments-10__r1']['reproduced'] = False
    return c
must_reject('R8 复现撤', e)


def f(c):
    c = copy.deepcopy(c)
    c['slots']['wb__dabstep-payments-10__r1']['nfc_carrier_lines_count'] = 5
    return c
must_reject('nfc 计数不一致', f)


def g(c):
    c = copy.deepcopy(c)
    s = c['slots'].pop('wb__dabstep-payments-10__r1')
    c['slots']['wb__dabstep-payments-10__r7'] = s
    return c
must_reject('槽名非法', g)


def h(c):
    c = copy.deepcopy(c)
    c['near_miss']['count'] = 3
    return c
must_reject('近错声明改', h)

print(f'全部夹具拒绝通过：{REJECTED + 1} 项（1 正常 + {REJECTED} 注入）')
