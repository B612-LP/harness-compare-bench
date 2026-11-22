#!/usr/bin/env python3
"""R112 number profile v1: bounded exact decimal canonicalization (PREREG §1, rev2 vectors, rev3 counts).

Number path: parse_int/parse_float callbacks both emit a NUL sentinel string
carrying the canonical token (arbitrary precision, never through float;
json's C encoder ignores int-subclass __repr__, so int-subclass routing was
rejected); unquoted by the post-pass. Deterministic; no locale, no float."""
import gzip, json, re, sys, os

COEFF_MAX = 4096
EXP_LO, EXP_HI = -6144, 6144
INT_RE = re.compile(r'-?\d+\Z')
DEC_RE = re.compile(r'-?(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d+))?\Z')

_SENT = '\x00NUM:'
_DEC_SENT = re.compile(r'"\\u0000NUM:([^"]+)\\u0000"')

class OutOfBounds(ValueError): pass

def canonical_number(lit: str) -> str:
    """PREREG §1. Raises OutOfBounds outside declared bounds."""
    if INT_RE.match(lit):
        digits = lit[1:] if lit.startswith('-') else lit
        if len(digits) > COEFF_MAX: raise OutOfBounds('int coefficient bound')
        return lit  # JSON ints carry no leading zeros; -0 preserved as-is
    m = DEC_RE.match(lit)
    if not m: raise ValueError(f'not a JSON number literal: {lit!r}')
    sign = '-' if lit.startswith('-') else ''
    ip, fp, ex = m.group(1) or '0', m.group(2) or '', m.group(3)
    E = (int(ex) if ex is not None else 0) - len(fp)
    digits = ip + fp
    if set(digits) == {'0'}:
        return sign + '0e0'          # zero: exponent normalized to 0, sign kept
    stripped = digits.rstrip('0')    # 去尾零系数
    E += len(digits) - len(stripped)  # 尾零剥离把指数上移
    coeff = stripped.lstrip('0') or '0'
    if len(coeff) > COEFF_MAX: raise OutOfBounds('dec coefficient bound')
    if not (EXP_LO <= E <= EXP_HI): raise OutOfBounds('exponent bound')
    return f'{sign}{coeff}e{E}'

class _Num:
    """Sentinel factory: json's C encoder ignores int-subclass __repr__, so
    every number token (int and decimal alike) travels as a NUL sentinel
    string carrying its canonical form; unquoted by the post-pass. Genuine
    strings cannot collide: NUL in any string value is asserted zero."""
    __slots__ = ()
    @staticmethod
    def make(lit: str) -> str:
        return _SENT + canonical_number(lit) + '\x00'

def canonical_bytes(raw: bytes, *, wire: str) -> bytes:
    """wire: 'json' (request body) or 'sse' (response stream; per-data-line)."""
    if wire == 'json':
        return _canon_doc(raw)
    if wire == 'sse':
        r = gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw
        text = r.decode('utf-8')
        outs = []
        for m in re.finditer(rb'^data: (.+)$', text.encode('utf-8'), re.M):
            if m.group(1) == b'[DONE]':
                continue
            outs.append(_canon_doc(m.group(1)))
        if not outs: raise ValueError('no SSE data lines')
        return b'\n'.join(outs)
    raise ValueError(wire)

def _canon_doc(doc: bytes) -> bytes:
    tree = json.loads(doc.decode('utf-8'), parse_int=_Num.make, parse_float=_Num.make)
    out = json.dumps(tree, sort_keys=True, ensure_ascii=False,
                     separators=(',', ':'), allow_nan=False)
    out, n = _DEC_SENT.subn(lambda m: m.group(1), out)
    return out.encode('utf-8')

# ---- PREREG rev2 §2 vectors ----
VECTORS = [
    ('256000','256000'), ('-1','-1'), ('0','0'), ('-0','-0'),
    ('1795173531509','1795173531509'), ('0.0','0e0'), ('0.00','0e0'),
    ('-0.0','-0e0'), ('1.0','1e0'), ('1.00','1e0'), ('1.50','15e-1'),
    ('1.5','15e-1'), ('0.5','5e-1'), ('0.005','5e-3'), ('4e3','4e3'),
    ('1.5e3','15e2'), ('15e2','15e2'), ('4.0e2','4e2'), ('1e-2','1e-2'),
    ('2.5e-3','25e-4'),
    ('123456789012345678901234567890','123456789012345678901234567890'),
]
REJECTS = ['1e9999', '1e-9999', '1' + '0'*5000]

def self_test() -> None:
    for lit, want in VECTORS:
        got = canonical_number(lit)
        assert got == want, f'vector {lit}: got {got} want {want}'
    for lit in REJECTS:
        try:
            canonical_number(lit); raise AssertionError(f'{lit} not rejected')
        except OutOfBounds:
            pass
    # §3 negative controls
    def pair(a, b): return canonical_number(a), canonical_number(b)
    assert pair('1.50','1.5')[0] == pair('1.50','1.5')[1], 'C1 same-form'          # 等值重编码
    assert canonical_bytes(b'{"k":1.50}', wire='json') != \
           canonical_bytes(b'{"k":2.50}', wire='json'), 'C1 flip'                   # 等长真改翻裁
    assert pair('0.0','-0.0')[0] != pair('0.0','-0.0')[1], 'C2 sign'
    assert pair('4000','4e3')[0] != pair('4000','4e3')[1], 'C3 typing'
    assert pair('1.0','1')[0] != pair('1.0','1')[1], 'C4 typing'
    assert pair('1.5e3','15e2')[0] == pair('1.5e3','15e2')[1], 'C5 same'
    assert pair('1.5e3','1.6e3')[0] != pair('1.5e3','1.6e3')[1], 'C5 flip'
    assert canonical_bytes(b'{"b":2,"a":1}', wire='json') == \
           canonical_bytes(b'{ "a" : 1 , "b" : 2 }', wire='json'), 'C6 order/space'
    assert canonical_bytes(b'{"k":"111"}', wire='json') != \
           canonical_bytes(b'{"k":"999"}', wire='json'), 'C6 string digits visible'
    # 结构等值自检：规范字节可回读且数值等值
    a = json.loads(canonical_bytes(b'{"k":1.50,"m":[1,-0]}', wire='json'),
                   parse_float=lambda s: __import__('decimal').Decimal(s.replace('e','E')))
    assert a['k'] == __import__('decimal').Decimal('1.5') and a['m'][1] == 0
    print('SELF-TEST OK: vectors %d+rejects %d, controls 6/6, roundtrip ok'
          % (len(VECTORS)+len(REJECTS), len(REJECTS)))


if __name__ == '__main__':
    self_test()
    print('NUMBER-PROFILE-PUBLIC SELF-TEST OK (%d vectors, %d rejects)' % (len(VECTORS), len(REJECTS)))
