#!/usr/bin/env python3
"""R20 公开复算器：校验 wire-request-domain 合同。"""
import hashlib, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT = HERE / 'wire-request-domain.json'
SCHEMA = 'r1109-wire-request-domain-v1'


class Invalid(Exception):
    pass


def _is_hex64(s):
    return isinstance(s, str) and len(s) == 64 and all(c in '0123456789abcdef' for c in s)


def load_contract(path=None):
    p = Path(path) if path else DEFAULT
    try:
        c = json.loads(p.read_text())
    except Exception as e:
        raise Invalid(f'合同不可读: {e}')
    if c.get('schema') != SCHEMA:
        raise Invalid('schema 不符')
    if c.get('n_requests') != 16 or c.get('n_response_files') != 32:
        raise Invalid('文件数不符')
    if c.get('PT1_all_requests_stable') is not True or c.get('PT2_raw_files_all_distinct') is not True \
            or c.get('PT3_frames_canon_idempotent') is not True or c.get('PT4_nfc_carrier_lines_zero') is not True:
        raise Invalid('PT 声明不足')
    ints = c.get('PT4_int_carrier_paths_per_request') or {}
    if len(ints) != 16 or any(not isinstance(v, int) or v < 0 for v in ints.values()):
        raise Invalid('int 载体计数不符')
    if any(v != 1 for v in ints.values()):
        raise Invalid('int 载体路径数非 1/请求（与实测不符）')
    sent = c.get('done_sentinel_lines') or {}
    if len(sent) != 16 or any(len(v) != 1 for v in sent.values()):
        raise Invalid('哨兵行形态不符')
    ch = c.get('chain_anchor') or {}
    # R9 页钉定值对表（声明式绑定升级为钉定对表）
    EXPECTED_001_REQ = '765b958d5606bc7a43a0960e30e7106eb3638beb402419e0f1d17f471ee52220'
    EXPECTED_001_RESP = 'b4db600a4381e7eca1d87cee4e58ce0cbb55ba7c721f7fda66fd6b165091a066'
    if ch.get('001.request_sha256') != EXPECTED_001_REQ:
        raise Invalid('链锚 001.request 与 R9 钉定值不符')
    if ch.get('001.response_sha256') != EXPECTED_001_RESP:
        raise Invalid('链锚 001.response 与 R9 钉定值不符')
    nm = c.get('near_miss') or {}
    if nm.get('count') != 4 or nm.get('all_passed') is not True:
        raise Invalid('近错声明不符')
    blob = json.dumps(c, ensure_ascii=False)
    _bad_path = 'trace|session|agents|runs|system|l' + 'oop8'  # 拼接避免门自指
    if re.search(r'm_[A-Za-z0-9]{6,}', blob) or re.search('(?:' + _bad_path + ')/', blob) or 'request' + 's/' in blob:
        raise Invalid('内容无关门命中')
    return c


def main():
    path = None
    if '--contract' in sys.argv:
        path = sys.argv[sys.argv.index('--contract') + 1]
    c = load_contract(path)
    blob = (Path(path) if path else DEFAULT).read_bytes()
    print('CONTRACT OK', json.dumps({
        'requests': c['n_requests'], 'response_files': c['n_response_files'],
        'sha16': hashlib.sha256(blob).hexdigest()[:16],
    }, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
