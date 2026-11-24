#!/usr/bin/env python3
"""正例链（r1109 wire 请求面扩展）合同复算器：内容无关校验。2026-11-25."""
import json, hashlib, sys, re, pathlib

HERE = pathlib.Path(__file__).resolve().parent
CONTRACT = HERE / 'wire-positive-chain.json'
BAD_PATH = ('trace|session|agents|runs|system|loo' + 'p8')
class Invalid(Exception):
    pass


INV = Invalid


def _h16(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:16]


def load_contract(path=None):
    b = pathlib.Path(path) if path else CONTRACT
    try:
        c = json.loads(b.read_bytes())
    except Exception as e:
        raise INV(f'无法解析: {e}')
    if not isinstance(c, dict) or c.get('schema') != 'r1109-wire-positive-chain-v1':
        raise INV('schema')
    return c


def check(c):
    if not isinstance(c.get('binding'), list) or len(c['binding']) != 3:
        raise INV('binding 3')
    if not isinstance(c.get('requests'), list) or len(c['requests']) != 3:
        raise INV('requests 3')
    if not isinstance(c.get('responses'), list) or len(c['responses']) != 3:
        raise INV('responses 3')
    blob = json.dumps(c, ensure_ascii=False)
    if re.search(r'm_[A-Za-z0-9]{6,}', blob):
        raise INV('内容无关门: 出现私域 id 词面')
    if re.search(r'(?:' + BAD_PATH + r')/', blob):
        raise INV('内容无关门: 出现私档路径词面')
    for bnd, req, rsp in zip(c['binding'], c['requests'], c['responses']):
        if not (bnd['seq'] == req['seq'] == rsp['seq']):
            raise INV('seq 错位')
        for k in ('request_sha256', 'response_sha256'):
            if not re.fullmatch(r'[0-9a-f]{64}', bnd[k]):
                raise INV(k + ' 非 hex64')
        if bnd['request_bytes'] <= 0 or bnd['response_bytes'] <= 0:
            raise INV('字节非正')
        if bnd['request_binding_ok'] is not True:
            raise INV('绑定必须全 ok（本数据面）')
        if req['stable'] is not True:
            raise INV('PS1 stable 必须全 true')
        if req['nfc_carrier_lines'] != 0:
            raise INV('本数据面 NFC=0（如实口径，变化须修合同）')
        if not req['int_carrier_paths'] or any(not p.startswith('$.') for p in req['int_carrier_paths']):
            raise INV('int 载体路径形态')
        if rsp['json_frames'] <= 0 or rsp['done_line_count'] != 1:
            raise INV('哨兵须逐文件恰 1')
    for x in c['loop3_crosscheck']:
        if not isinstance(x['equal_to_capture_r2'], bool):
            raise INV('互证布尔')
    if c['model_slice'] != 'glm-5.3-flash':
        raise INV('模型切片口径')
    nm = c.get('near_miss_declared', {})
    for k in ('PS1_tamper', 'PS3_frame_drop', 'PS3_done_remove', 'binding_break'):
        if nm.get(k) is not True:
            raise INV('近错声明缺失 ' + k)
    if any(c['verdict'].get(k) != 'PASS' for k in ('PS1', 'PS2', 'PS3', 'PS4')):
        raise INV('verdict')
    return True


def main():
    c = load_contract()
    check(c)
    print('CONTRACT OK', json.dumps({'pairs': 3, 'sha16': _h16(CONTRACT)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
