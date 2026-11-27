#!/usr/bin/env python3
"""公开复算：wire 请求面扩展——实现一致性电池扩展 + v1.6 词型保持（R2，2026-11-27）。

三部分，全部公开可复算、仅标准库、不读任何私有路径：
  A1. 词型保持探针：8 个合成载荷（整值浮点 0.0/1.0、负零 -0.0、指数 1e-05、
      大整值浮点 1e16、嵌套混合、空对象容器）分别跑 crossparse2.mjs 两模式——
      R1 版 String() 基线应恰好漏掉全部含浮点词型载荷（PB2a 机制），v1.6
      typed 模式应全配（PB2b）。
  A2. pyFloat 系统性对照：400 个确定性伪随机 double（固定种子线性同余）+
      边界值表，单值载荷端到端跑 typed 模式，全部须与 Python repr 钉定值
      SHA256 一致。
  A3. 篡改面合成基座：drop_field / 标量微调 / dup_inject 三探针 3/3 检出
      （dup_inject 为加固器独有检出点：stdlib 静默 last-wins，wrapper DUP_KEY 拒）。
  B.  公开档回归：r20261125-five-lcb 三份公开 JSONL（dsh 78 / codex 84 /
      doubao 73 = 235 载荷）typed 模式全配 + census（公开档 float 词域为 0，
      string/typed 的分辨力由 A1/A2 承载）。
  C.  私有档 1569 载荷（10 wire 目录）数字为登记性披露（README 判定表），
      原件不入公开仓；只有内部非作者独审，不替代老师要求的受控第三方原档核验。

  A4. 内部独审近错：特殊键/整数修正回归，浮点tie反例预期仍mismatch，明确通用承诺NO-GO。

运行：python3 -IB verify2.py （建议 -IBO 双档；需 node ≥18，缺失为 INCOMPLETE/exit2）
"""
import hashlib, json, shutil, subprocess, sys, tempfile
from pathlib import Path

PAGE = Path(__file__).resolve().parent
EVID = PAGE / '..' / '..' / '3-表现现场' / 'r20261125-five-lcb'
SOURCES = [
    ('E.dsh', EVID / 'dsh' / 'stdout-r2.jsonl', 78,
     '105717eaca150dd36eab255bff74945509a3488837bb1b8df5e143aa337e2508'),
    ('E.codex', EVID / 'codex' / 'stdout-r2.jsonl', 84,
     'd85c7d724ed4fed1e839aa6fc534cc025cca2288bdc08987d88c73643467be10'),
    ('D.doubao', EVID / 'doubao' / 'trajectory-38455827958268674-copy.jsonl', 73,
     '8fc1d0e0ed5a2688b28a86e47a33e08975866a9f26e11ce79eb07c5d44d8d5a7'),
]
FAILS = []
SKIPS = []


def check(name, cond, detail=''):
    print(('PASS' if cond else 'FAIL'), name, ('' if cond else f': {detail}'))
    if not cond:
        FAILS.append(name)


def canon(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def validate_verdicts(expected_ids, records):
    """Reject missing/extra/duplicate rows before any all(...) success test."""
    expected = list(expected_ids)
    if not expected or len(expected) != len(set(expected)):
        raise ValueError('empty or duplicate expected IDs')
    verdicts = {}
    for o in records:
        pid, verdict = o['id'], o['verdict']
        if pid in verdicts:
            raise ValueError('duplicate result ID: ' + pid)
        if verdict not in ('match', 'mismatch', 'parse_error'):
            raise ValueError('invalid verdict: ' + str(verdict))
        verdicts[pid] = verdict
    if set(verdicts) != set(expected):
        raise ValueError(f'coverage mismatch: expected={len(expected)} got={len(verdicts)}')
    return verdicts


def run_crossparse(paydir, corpus, out, mode):
    node = shutil.which('node')
    if node is None:
        SKIPS.append(f'crossparse {mode}: node missing')
        return None
    expected = [o['id'] for o in load_jsonl(corpus)]
    r = subprocess.run([node, str(PAGE / 'crossparse2.mjs'), str(paydir), str(corpus),
                        str(out), f'--mode={mode}'], capture_output=True, text=True,
                       timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f'crossparse2.mjs failed: {r.stderr[:300]}')
    return validate_verdicts(expected, load_jsonl(out))


def unique_pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError('DUP_KEY')
        out[k] = v
    return out


def strict_load(raw):
    def reject_constant(value):
        raise ValueError('NON_FINITE: ' + value)
    v = json.loads(raw, object_pairs_hook=unique_pairs, parse_constant=reject_constant)
    canon(v)  # Also rejects non-finite overflow and lone surrogates.
    return v


def load_jsonl(p):
    # LF, not str.splitlines(): U+2028/9 are legal JSON string characters.
    return [json.loads(l) for l in p.read_text(encoding='utf-8').split('\n') if l.strip()]


# ---------- A1: 词型保持探针 ----------
def part_a1(td):
    probes = {
        'p01_one': '{"usage":{"i":1,"f":1.0}}',
        'p02_zero': '{"usage":{"z":0.0,"n":0}}',
        'p03_negzero': '{"z":-0.0}',
        'p04_exp': '{"e":1e-05}',
        'p05_bigint_float': '{"b":1e16}',
        'p06_mixed': '{"a":{"x":[1,1.0,0.0,2]},"b":"1.0","c":true}',
        'p07_empty': '{"a":{},"b":[[],{},[{}]]}',
        'p08_plain': '{"i":7,"s":"x","arr":[1,2,3]}',
    }
    paydir = td / 'a1'
    paydir.mkdir()
    corpus_lines = []
    for pid, raw in probes.items():
        (paydir / (pid + '.txt')).write_text(raw)
        corpus_lines.append(json.dumps({'id': pid,
                                        'canon_sha256': hashlib.sha256(canon(json.loads(raw))).hexdigest()}))
    (paydir / 'corpus.jsonl').write_text('\n'.join(corpus_lines) + '\n')
    expected_float_bearing = {'p01_one', 'p02_zero', 'p03_negzero', 'p04_exp',
                              'p05_bigint_float', 'p06_mixed'}
    vstr = run_crossparse(paydir, paydir / 'corpus.jsonl', td / 'a1s.jsonl', 'string')
    vtyp = run_crossparse(paydir, paydir / 'corpus.jsonl', td / 'a1t.jsonl', 'typed')
    if vstr is None or vtyp is None:
        print('SKIP A1 (node missing)')
        return
    check('A1.string_float_bearing_all_mismatch',
          all(vstr[p] == 'mismatch' for p in expected_float_bearing),
          str({p: vstr[p] for p in sorted(expected_float_bearing)}))
    check('A1.string_plain_match', vstr['p08_plain'] == 'match')
    check('A1.string_exact_24_frame_analog_6of8',
          sum(1 for p in probes if vstr[p] == 'mismatch') == 6)
    check('A1.typed_all_match', all(v == 'match' for v in vtyp.values()),
          str({k: v for k, v in vtyp.items() if v != 'match'}))


# ---------- A2: pyFloat 系统性对照 ----------
def part_a2(td):
    seed = 20261127
    state = seed

    def lcg():
        nonlocal state
        state = (state * 6364136223846793005 + 1442695040888963407) % (1 << 64)
        return state

    import struct
    vals = [0.0, -0.0, 1.0, -1.0, 1e16, 1e15, 1e-5, 5e-324, 1.7976931348623157e308,
            0.1, 99.7, 2.5e-9, -1e-5, 1.5e-5, 123.456, -0.07]
    while len(vals) < 416:
        b1 = lcg()
        b2 = lcg()
        x = struct.unpack('<d', struct.pack('<Q', (b1 ^ (b2 << 1)) & ((1 << 64) - 1)))[0]
        if x != x or x in (float('inf'), float('-inf')):
            continue
        vals.append(x)
    paydir = td / 'a2'
    paydir.mkdir()
    corpus_lines = []
    for j, x in enumerate(vals):
        pid = f'v{j:03d}'
        raw = json.dumps({'v': x})
        (paydir / (pid + '.txt')).write_text(raw)
        corpus_lines.append(json.dumps({'id': pid,
                                        'canon_sha256': hashlib.sha256(canon(json.loads(raw))).hexdigest()}))
    (paydir / 'corpus.jsonl').write_text('\n'.join(corpus_lines) + '\n')
    vt = run_crossparse(paydir, paydir / 'corpus.jsonl', td / 'a2.jsonl', 'typed')
    if vt is None:
        print('SKIP A2 (node missing)')
        return
    bad = [k for k, v in vt.items() if v != 'match']
    check('A2.typed_pyrepr_416_all_match', not bad, f'{len(bad)} bad: {bad[:4]}')


# ---------- A3: 篡改面（合成基座） ----------
def part_a3(td):
    base = {'model': 'demo-x', 'stream': False, 'input': [{'role': 'user', 'content': 'hi'}],
            'meta': {'seq': 5, 'flag': True}}
    pin = hashlib.sha256(canon(base)).hexdigest()

    # dup_inject: stdlib 静默 last-wins；wrapper 用 object_pairs_hook 检出
    dup_raw = json.dumps(base)[:-1] + ',"model":"dup"}'

    def pairs_hook(pairs):
        seen = set()
        for k, _ in pairs:
            if k in seen:
                raise ValueError('DUP_KEY')
            seen.add(k)
        return dict(pairs)

    try:
        json.loads(dup_raw, object_pairs_hook=pairs_hook)
        wrapper_reject = False
    except ValueError:
        wrapper_reject = True
    check('A3.dup_inject_wrapper_reject', wrapper_reject)
    check('A3.dup_inject_stdlib_silent_lastwins',
          json.loads(dup_raw)['model'] == 'dup' and
          hashlib.sha256(canon(json.loads(dup_raw))).hexdigest() != pin)

    v2 = json.loads(json.dumps(base))
    v2['meta']['seq'] += 1
    check('A3.num_tweak_detected',
          hashlib.sha256(canon(v2)).hexdigest() != pin)

    v3 = json.loads(json.dumps(base))
    del v3['stream']
    check('A3.drop_field_detected',
          hashlib.sha256(canon(v3)).hexdigest() != pin)


# ---------- A4: 独审近错与支持域边界（事后新增，不回填旧预测） ----------
def part_a4(td):
    probes = {
        'proto': '{"__proto__":{"x":1},"a":2}',
        'nested_proto': '{"a":{"__proto__":3}}',
        'unsafe_int': '{"v":9007199254740993}',
        'large_int': '{"v":1000000000000000000000}',
        'negative_int_zero': '{"v":-0}',
        'unicode_literal': json.dumps({'v': chr(0x2028) + chr(0x2029)}, ensure_ascii=False),
        'unicode_escaped': json.dumps({'v': chr(0x2028) + chr(0x2029)}, ensure_ascii=True),
        'float_tie_pos': '{"v":1000000000000000.2}',
        'float_tie_neg': '{"v":-1000000000000000.2}',
        'duplicate_proto': '{"__proto__":1,"__proto__":2}',
    }
    paydir = td / 'a4'
    paydir.mkdir()
    corpus = []
    for pid, raw in probes.items():
        (paydir / (pid + '.txt')).write_bytes(raw.encode('utf-8'))
        corpus.append({'id': pid, 'canon_sha256': hashlib.sha256(canon(json.loads(raw))).hexdigest()})
    (paydir / 'corpus.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in corpus))
    vt = run_crossparse(paydir, paydir / 'corpus.jsonl', td / 'a4.jsonl', 'typed')
    if vt is None:
        print('SKIP A4 (node missing)')
        return
    ties = {'float_tie_pos', 'float_tie_neg'}
    for pid in probes:
        expected = ('mismatch' if pid in ties else
                    'parse_error' if pid == 'duplicate_proto' else 'match')
        check('A4.' + pid, vt[pid] == expected, f'expected={expected} got={vt[pid]}')
    print('KNOWN LIMIT: typed float tie 2/2 mismatch; generic CPython repr claim remains NO-GO')


# ---------- B: 公开档回归 ----------
def part_b(td):
    rows = []
    census = {'float_values': 0, 'float_payloads': 0, 'max_depth': 0,
              'u2028_9_payloads': 0}
    for sid, p, count, pin in SOURCES:
        data = p.read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        check(f'B.source_sha.{sid}', actual == pin, actual)
        if actual != pin:
            raise ValueError('source hash mismatch: ' + sid)
        lines = [l for l in data.split(b'\n') if l.strip()]
        check(f'B.source_count.{sid}', len(lines) == count, str(len(lines)))
        for j, raw in enumerate(lines):
            rows.append((f'{sid}.line{j:03d}', raw, strict_load(raw.decode('utf-8'))))
    corpus_lines = []
    for pid, raw, v in rows:
        d, floats = 0, 0
        stack = [(v, 1)]
        while stack:
            o, dep = stack.pop()
            d = max(d, dep)
            if isinstance(o, dict):
                stack.extend((x, dep + 1) for x in o.values())
            elif isinstance(o, list):
                stack.extend((x, dep + 1) for x in o)
            elif isinstance(o, float):
                floats += 1
        census['float_values'] += floats
        census['float_payloads'] += int(floats > 0)
        census['u2028_9_payloads'] += int(any(chr(cp) in raw.decode('utf-8')
                                                for cp in (0x2028, 0x2029)))
        census['max_depth'] = max(census['max_depth'], d)
        corpus_lines.append(json.dumps({'id': pid,
                                        'canon_sha256': hashlib.sha256(canon(v)).hexdigest()}))
    check('B.denominator_235', len(rows) == 235, str(len(rows)))
    paydir = td / 'b'
    paydir.mkdir()
    for pid, raw, _ in rows:
        (paydir / (pid + '.txt')).write_bytes(raw)
    (paydir / 'corpus.jsonl').write_text('\n'.join(corpus_lines) + '\n')
    check('B.public_float_domain_zero', census['float_values'] == 0,
          str(census['float_values']))
    print('CENSUS', json.dumps(census, ensure_ascii=True, sort_keys=True))
    vt = run_crossparse(paydir, paydir / 'corpus.jsonl', td / 'bt.jsonl', 'typed')
    vs = run_crossparse(paydir, paydir / 'corpus.jsonl', td / 'bs.jsonl', 'string')
    if vt is None or vs is None:
        print('SKIP B crossparse (node missing)')
        return
    check('B.typed_235_all_match', all(v == 'match' for v in vt.values()),
          str([k for k, v in vt.items() if v != 'match'][:3]))
    check('B.string_235_all_match', all(v == 'match' for v in vs.values()),
          str([k for k, v in vs.items() if v != 'match'][:3]))


def main():
    print('== R2 公开复算：wire 请求面扩展 + v1.6 词型保持 ==')
    with tempfile.TemporaryDirectory() as tmp:
        td = Path(tmp)
        part_a1(td)
        part_a2(td)
        part_a3(td)
        part_a4(td)
        part_b(td)
    if FAILS:
        print(f'\nFAILED: {len(FAILS)} -> {FAILS}')
        sys.exit(1)
    if SKIPS:
        print('\nINCOMPLETE: ' + '; '.join(SKIPS))
        sys.exit(2)
    print('\nALL EXPECTED CHECKS PASS (finite corpus only; see A4 known counterexample)')


if __name__ == '__main__':
    main()
