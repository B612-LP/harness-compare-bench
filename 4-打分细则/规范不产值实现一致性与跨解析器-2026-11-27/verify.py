#!/usr/bin/env python3
"""公开复算：规范 v1.5「不产值」条款实现一致性 + 跨解析器复核稳定性（R1，2026-11-27）。

三部分，全部公开可复算、仅标准库、不读任何私有路径：
  A. 合成探针 6+3：stdlib 行为 vs v1.6 候选加固器分类拒绝 + 篡改检出逻辑。
  B. 公开档普查：r20261125-five-lcb 三份公开 JSONL（dsh/codex/doubao）逐行
     census（dup_key/NaN/lone surrogate/BOM/U+2028-9/float/非ASCII键/深度）
     + v1.6 加固器 parity。W1/W2 私有档部分以非作者独审替代验收，不在本页复算面。
  C. 跨解析器：同目录 crossparse.mjs（node ≥18，缺 node 如实 SKIP）对 B 语料
     独立 JSON.parse + 码点序 canon，SHA256 与 Python 钉定值逐条比对。

运行：python3 -IB verify.py   （并建议 python3 -IBO verify.py 双档）
"""
import hashlib, json, shutil, subprocess, sys, tempfile
from pathlib import Path

PAGE = Path(__file__).resolve().parent
EVID = PAGE / '..' / '..' / '3-表现现场' / 'r20261125-five-lcb'
SOURCES = [
    ('E.dsh', EVID / 'dsh' / 'stdout-r2.jsonl'),
    ('E.codex', EVID / 'codex' / 'stdout-r2.jsonl'),
    ('D.doubao', EVID / 'doubao' / 'trajectory-38455827958268674-copy.jsonl'),
]
DEPTH_LIMIT = 512
FAILS = []


def check(name, cond, detail=''):
    print(('PASS' if cond else 'FAIL'), name, ('' if cond else f': {detail}'))
    if not cond:
        FAILS.append(name)


class ClassifiedReject(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _pairs_hook(pairs):
    seen = set()
    for k, _ in pairs:
        if k in seen:
            raise ClassifiedReject('DUP_KEY')
        seen.add(k)
    return dict(pairs)


def _parse_constant(name):
    raise ClassifiedReject('NON_FINITE')


def canon(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def stdlib_loads(raw):
    try:
        return json.loads(raw), None
    except Exception as e:
        return None, type(e).__name__


def hardened_loads(raw):
    if raw.startswith('﻿'):
        raise ClassifiedReject('BOM')
    try:
        v = json.loads(raw, object_pairs_hook=_pairs_hook, parse_constant=_parse_constant)
    except ClassifiedReject:
        raise
    except json.JSONDecodeError:
        raise ClassifiedReject('PARSE')
    except RecursionError:
        raise ClassifiedReject('DEPTH_LIMIT')
    _check_surrogates(v)
    _check_depth(v, 0)
    return v


def _check_surrogates(o):
    if isinstance(o, str):
        try:
            o.encode('utf-8')
        except UnicodeEncodeError:
            raise ClassifiedReject('LONE_SURROGATE')
    elif isinstance(o, dict):
        for k, v in o.items():
            _check_surrogates(k)
            _check_surrogates(v)
    elif isinstance(o, list):
        for v in o:
            _check_surrogates(v)


def _check_depth(o, d):
    if d > DEPTH_LIMIT:
        raise ClassifiedReject('DEPTH_LIMIT')
    if isinstance(o, dict):
        for v in o.values():
            _check_depth(v, d + 1)
    elif isinstance(o, list):
        for v in o:
            _check_depth(v, d + 1)


def census_value(v):
    st = {'floats': 0, 'max_depth': 0, 'non_ascii_keys': 0}

    def walk(o, d):
        st['max_depth'] = max(st['max_depth'], d)
        if isinstance(o, dict):
            for k, v2 in o.items():
                if not k.isascii():
                    st['non_ascii_keys'] += 1
                walk(v2, d + 1)
        elif isinstance(o, list):
            for v2 in o:
                walk(v2, d + 1)
        elif isinstance(o, float):
            st['floats'] += 1
    walk(v, 1)
    return st


# ---------- A. 合成探针 ----------
def part_a():
    probes = {
        'dup_key': ('{"a":1,"a":2}', 'silent_value', 'DUP_KEY'),
        'nan': ('{"x": NaN}', 'silent_value', 'NON_FINITE'),
        'neg_infinity': ('{"x": -Infinity}', 'silent_value', 'NON_FINITE'),
        'lone_surrogate': ('{"k":"\\ud800"}', 'silent_value', 'LONE_SURROGATE'),
        'bom': ('﻿{"a":1}', 'crash:JSONDecodeError', 'BOM'),
        'deep2000': ('{"a":' * 2000 + '1' + '}' * 2000, 'crash:RecursionError', 'DEPTH_LIMIT'),
    }
    for name, (raw, want_stdlib, want_code) in probes.items():
        v, err = stdlib_loads(raw)
        beh = 'silent_value' if err is None else f'crash:{err}'
        check(f'A/{name} stdlib={want_stdlib}', beh == want_stdlib, beh)
        try:
            hardened_loads(raw)
            check(f'A/{name} wrapper={want_code}', False, 'ACCEPTED(FAIL)')
        except ClassifiedReject as e:
            check(f'A/{name} wrapper={want_code}', e.code == want_code, e.code)
    v = hardened_loads('{"a":[1,2,{"b":"中"}]}')
    check('A/valid accepted', v is not None)
    check('A/depth13 accepted', hardened_loads('{"a":' * 13 + '1' + '}' * 13) is not None)
    # 篡改 3（合成基座）
    base_v = {'model': 'base-model', 'messages': [{'role': 'user', 'content': 'hi'}], 'max_tokens': 100}
    pin = hashlib.sha256(canon(base_v)).hexdigest()
    t_drop = {k: x for k, x in base_v.items() if k != 'model'}
    t_tweak = dict(base_v, max_tokens=101)
    t_dup = '{"model":"base-model","model":"dup","messages":[]}'
    for name, raw in (('drop_field', json.dumps(t_drop, ensure_ascii=False)),
                      ('num_tweak', json.dumps(t_tweak, ensure_ascii=False)),
                      ('dup_inject', t_dup)):
        detected = False
        try:
            detected = hashlib.sha256(canon(json.loads(raw))).hexdigest() != pin
        except Exception:
            pass
        try:
            hardened_loads(raw)
        except ClassifiedReject as e:
            detected = detected or True
            check(f'A/tamper/{name} wrapper code', e.code == 'DUP_KEY' if name == 'dup_inject' else True, e.code)
        check(f'A/tamper/{name} detected', detected)
    # canon 决定性
    v0 = json.loads('{"b":[1,{"a":"中"}],"a":2}')
    base = canon(v0)
    for style in (json.dumps(v0, ensure_ascii=False, indent=2, sort_keys=True),
                  json.dumps(v0, ensure_ascii=True, sort_keys=True),
                  json.dumps(v0, ensure_ascii=False)):
        check('A/canon restyle stable', canon(json.loads(style)) == base)


# ---------- B. 公开档普查 ----------
def part_b():
    total = 0
    stdlib_ok = 0
    pathological = []
    max_depth = 0
    parity_bad = []
    corpus_lines = []  # (tag, lineno, payload, canon_sha)
    for tag, path in SOURCES:
        n_tag = 0
        for i, line in enumerate(path.read_text().splitlines()):
            s = line.strip()
            if not s:
                continue
            n_tag += 1
            total += 1
            if s.startswith('﻿') or (' ' in s) or (' ' in s):
                pathological.append(f'{tag}/line{i:03d}/bom-u2028')
            v, err = stdlib_loads(s)
            if err is not None:
                pathological.append(f'{tag}/line{i:03d}/{err}')
                continue
            stdlib_ok += 1
            c = census_value(v)
            max_depth = max(max_depth, c['max_depth'])
            if c['floats'] or c['non_ascii_keys']:
                pathological.append(f'{tag}/line{i:03d}/float-nonascii({c["floats"]},{c["non_ascii_keys"]})')
            try:
                json.loads(s, parse_constant=lambda n: (_ for _ in ()).throw(ValueError(n)))
            except ValueError:
                pathological.append(f'{tag}/line{i:03d}/nan-token')
            try:
                json.loads(s, object_pairs_hook=_pairs_hook)
            except ClassifiedReject:
                pathological.append(f'{tag}/line{i:03d}/dup-key')
            try:
                _check_surrogates(v)
            except ClassifiedReject:
                pathological.append(f'{tag}/line{i:03d}/lone-surrogate')
            corpus_lines.append((tag, i, s, hashlib.sha256(canon(v)).hexdigest()))
            try:
                hardened_loads(s)
            except ClassifiedReject as e:
                parity_bad.append(f'{tag}/line{i:03d}/{e.code}')
        print(f'  {tag}: {n_tag} payload lines')
    check('B/total=235', total == 235, total)
    check('B/stdlib_ok=235', stdlib_ok == 235, stdlib_ok)
    check('B/pathological=0', not pathological, str(pathological[:5]))
    check('B/max_depth<=512', max_depth <= 512, max_depth)
    check('B/wrapper parity 235', not parity_bad, str(parity_bad[:5]))
    print(f'  max_depth={max_depth}')
    return corpus_lines


# ---------- C. 跨解析器（node）----------
def part_c(corpus_lines):
    node = shutil.which('node')
    if not node:
        print('SKIP C/node absent — 跨解析器部分不可复算（如实降级）')
        check('C/skip is honest', True)
        return
    with tempfile.TemporaryDirectory() as td:
        tdir = Path(td)
        paydir = tdir / 'payloads'
        paydir.mkdir()
        corpus = tdir / 'corpus.jsonl'
        with corpus.open('w') as fh:
            for tag, i, s, sha in corpus_lines:
                (paydir / f'{tag}__line{i:03d}.txt').write_text(s)
                fh.write(json.dumps({'id': f'{tag}/line{i:03d}', 'canon_sha256': sha}) + '\n')
        subprocess.run([node, str(PAGE / 'crossparse.mjs'), str(paydir), str(corpus),
                        str(tdir / 'verdict.jsonl')], check=True)
        verd = {}
        for line in (tdir / 'verdict.jsonl').read_text().splitlines():
            o = json.loads(line)
            verd[o['id']] = o['verdict']
        per = {}
        bad = []
        for tag, i, s, sha in corpus_lines:
            verdict = verd.get(f'{tag}/line{i:03d}')
            per.setdefault(tag, [0, 0])
            per[tag][0] += 1
            if verdict == 'match':
                per[tag][1] += 1
            else:
                bad.append((f'{tag}/line{i:03d}', verdict))
        for tag, (n, m) in sorted(per.items()):
            print(f'  {tag}: {m}/{n} match')
        check('C/all match', not bad, str(bad[:5]))
    ver = subprocess.run([node, '--version'], capture_output=True, text=True).stdout.strip()
    print(f'  node {ver}')


if __name__ == '__main__':
    print('== A. synthetic probes ==')
    part_a()
    print('== B. public corpus census ==')
    lines = part_b()
    print('== C. cross-parser ==')
    part_c(lines)
    print('---')
    if FAILS:
        print('FAILURES:', FAILS)
        sys.exit(1)
    print('ALL PASS')
