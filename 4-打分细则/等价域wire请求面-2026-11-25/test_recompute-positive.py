#!/usr/bin/env python3
"""正例链复算器注入测试：1 正常 + 6 注入全拒。"""
import copy, json, pathlib, sys, importlib.util

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('recompute_positive', HERE / 'recompute-positive.py')
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)

REJECTED = 0


def nm(name, mutate):
    global REJECTED
    c = R.load_contract()
    mutate(c)
    try:
        R.check(c)
    except R.Invalid:
        REJECTED += 1
        return
    raise SystemExit(f'NOT REJECTED: {name}')


def m_tamper(c):  # PS1 翻假
    c['requests'][0]['stable'] = False


def m_frame(c):  # 帧数撕裂（非法负值；正值无法机器判——帧数真值由原档+独审承担）
    c['responses'][0]['json_frames'] = -3


def m_done(c):  # 哨兵多一处
    c['responses'][1]['done_line_count'] = 2


def m_bind(c):  # 绑定翻
    c['binding'][2]['request_binding_ok'] = False


def m_sha(c):  # SHA 形态
    c['binding'][0]['request_sha256'] = 'zz' + c['binding'][0]['request_sha256'][2:]


def m_nm(c):  # 近错声明假
    c['near_miss_declared']['PS1_tamper'] = False


R.check(R.load_contract())
nm('PS1_tamper', m_tamper)
nm('frame', m_frame)
nm('done', m_done)
nm('binding', m_bind)
nm('sha', m_sha)
nm('nearmiss', m_nm)
print(f'OK 正常 1 + 注入 {REJECTED} 全拒')
