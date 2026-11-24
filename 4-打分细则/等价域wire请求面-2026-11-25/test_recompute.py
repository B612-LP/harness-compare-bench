#!/usr/bin/env python3
"""R20 公开测试：正常夹具 + 注入全拒。"""
import copy, importlib.util, json, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('rc20', HERE / 'recompute.py')
rc20 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc20)

REJECTED = 0


def must_reject(name, mutate):
    global REJECTED
    base = json.loads((HERE / 'wire-request-domain.json').read_text())
    bad = mutate(base)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(bad, f, ensure_ascii=False)
        tmp = f.name
    try:
        rc20.load_contract(tmp)
    except rc20.Invalid:
        REJECTED += 1
        return
    raise AssertionError(f'{name}: 未拒绝')


rc20.load_contract()


def a(c):
    c = copy.deepcopy(c)
    c['PT1_all_requests_stable'] = False
    return c
must_reject('PT1 翻假', a)


def b(c):
    c = copy.deepcopy(c)
    c['PT4_int_carrier_paths_per_request']['005.request.bin'] = 0
    return c
must_reject('载体计数撕裂', b)


def cc(c):
    c = copy.deepcopy(c)
    c['done_sentinel_lines']['001.response.bin'] = []
    return c
must_reject('哨兵行抹除', cc)


def d(c):
    c = copy.deepcopy(c)
    c['chain_anchor']['001.request_sha256'] = 'zz'
    return c
must_reject('链锚损坏', d)


def e(c):
    c = copy.deepcopy(c)
    c['n_requests'] = 15
    return c
must_reject('文件数改', e)


def f(c):
    c = copy.deepcopy(c)
    c['near_miss']['count'] = 3
    return c
must_reject('近错声明改', f)


def g(c):
    c = copy.deepcopy(c)
    c['PT4_nfc_carrier_lines_zero'] = False
    return c
must_reject('NFC 声明翻', g)


def h(c):
    c = copy.deepcopy(c)
    c['PT3_frames_canon_idempotent'] = False
    return c
must_reject('PT3 翻假', h)

print(f'全部夹具拒绝通过：{REJECTED + 1} 项（1 正常 + {REJECTED} 注入）')
