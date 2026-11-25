#!/usr/bin/env python3
"""自报 usage 分离账复算器（2026-11-25）。

只吃同目录钉定账本 usage-ledger.json（r1109-usage-ledger-v1）：
DSH 338 条 + Codex 406 条自报 usage（免 id，含量级字节 text_chars）。
全部结论从账本内部关系复算，不需要任何产品运行。
"""
import json, sys
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).resolve().parent
CASES = ['bird-ca-schools-15','dabstep-payments-10','exercism-py-6','lcb-recent-hard-4','tb-cargo-plan']
DSH_F = ['inputTokens','outputTokens','cacheReadTokens','cacheWriteTokens','totalTokens']
COD_F = ['input_tokens','output_tokens','cached_input_tokens','cache_write_input_tokens','reasoning_output_tokens','total_tokens']

class Invalid(Exception):
    """任何校验失败都抛 Invalid，拒绝输出结论。"""

def load_ledger(led=None):
    if led is None:
        led = json.loads((HERE / 'usage-ledger.json').read_bytes())
    if led.get('schema') != 'r1109-usage-ledger-v1':
        raise Invalid('bad schema')
    for prod in ('dsh','codex'):
        slots = led.get(prod)
        if not isinstance(slots, dict) or len(slots) != 15:
            raise Invalid(f'{prod} slot count != 15')
        for slot, s in slots.items():
            if not slot.startswith(f'{prod}__') or s.get('n') != len(s.get('records', [])):
                raise Invalid(f'bad slot {slot}')
            sha = s.get('archive_sha256','')
            if len(sha) != 64 or any(ch not in '0123456789abcdef' for ch in sha):
                raise Invalid(f'bad sha {slot}')
    return led

def struct_check(u, fields):
    for f in fields:
        v = u.get(f, None)
        if f not in u: raise Invalid(f'missing {f}')
        if not isinstance(v, int) or isinstance(v, bool): raise Invalid(f'non-int {f}={v!r}')
        if v < 0: raise Invalid(f'negative {f}={v!r}')

def is_cumulative_impossible(series):
    """兼容旧名称：仅返回 n×first > last；该式不能排除累计口径。

    例如累计序列 [10, 11] 满足此式，故返回 True 不等于累计不可能。
    保留输出字段名以兼容历史账本；以独立会话总量对账为主要证据。
    """
    return len(series) * series[0] > series[-1]

def load_closure(tc=None):
    """独审 N1：Codex 会话级闭合对账（thread-closure.json，r1109-thread-closure-v1）。可注入 dict。"""
    if tc is None:
        tc = json.loads((HERE / 'thread-closure.json').read_bytes())
    if tc.get('schema') != 'r1109-thread-closure-v1':
        raise Invalid('closure bad schema')
    if tc.get('id_free') is not True:
        raise Invalid('closure not id-free')
    slots = tc.get('codex')
    if not isinstance(slots, dict) or len(slots) != 15:
        raise Invalid('closure slot count != 15')
    for slot, s in slots.items():
        if not slot.startswith('codex__') or s.get('all_equal') is not True:
            raise Invalid(f'closure not closed {slot}')
        comp = s.get('components', {})
        for k in ('total_tokens','input_tokens','output_tokens'):
            c = comp.get(k)
            if not c or c.get('sum_per_record') != c.get('last_thread') or c.get('equal') is not True:
                raise Invalid(f'closure component mismatch {slot} {k}')
        if s.get('n', -1) <= 0:
            raise Invalid(f'closure bad n {slot}')
    return tc

def recompute():
    led = load_ledger()
    out = {}
    out['thread_closure_slots'] = len(load_closure()['codex'])
    # P1 结构 + P2/P3 关系
    dsh_rel = defaultdict(int); cod_rel = defaultdict(int)
    for slot, s in led['dsh'].items():
        seqs = defaultdict(list)
        for r in s['records']:
            u = r['usage']; struct_check(u, DSH_F)
            for f in DSH_F: seqs[f].append(u[f])
            t,i,o,cr,cw = u['totalTokens'],u['inputTokens'],u['outputTokens'],u['cacheReadTokens'],u['cacheWriteTokens']
            if t == i+o+cr+cw: dsh_rel['in+out+cr+cw'] += 1
            elif t == i+o+cr: dsh_rel['in+out+cr'] += 1
            elif t == i+o+cw: dsh_rel['in+out+cw'] += 1
            elif t == i+o: dsh_rel['in+out'] += 1
            else: dsh_rel['none'] += 1
        out.setdefault('dsh_seq', {})[slot] = {k: {'nondec': all(seqs[k][i]<=seqs[k][i+1] for i in range(len(seqs[k])-1)),
                                                   'sum': sum(seqs[k]), 'last': seqs[k][-1]} for k in DSH_F}
    for slot, s in led['codex'].items():
        ins = []
        for r in s['records']:
            u = r['usage']; struct_check(u, COD_F)
            t,i,o = u['total_tokens'],u['input_tokens'],u['output_tokens']
            if t == i+o: cod_rel['in+out'] += 1
            elif t == i+o+u['cached_input_tokens']: cod_rel['in+out+cached'] += 1
            else: cod_rel['none'] += 1
            if u['cached_input_tokens'] > i: raise Invalid(f'cached>input {slot}')
            if u['reasoning_output_tokens'] > o: raise Invalid(f'reasoning>output {slot}')
            if u['cache_write_input_tokens'] != 0: raise Invalid(f'cw!=0 {slot}')
            ins.append(i)
        out.setdefault('codex_seq', {})[slot] = {'nondec': all(ins[i]<=ins[i+1] for i in range(len(ins)-1)),
                                                 'impossible_cum': is_cumulative_impossible(ins)}
    # P6 比率（text_chars 为 UTF-8 字节）
    cpt = defaultdict(list)
    for slot, s in led['dsh'].items():
        case = slot.split('__')[1]
        for r in s['records']:
            o = r['usage']['outputTokens']; c = r.get('text_chars', 0)
            if o > 0 and c > 0: cpt[case].append(c/o)
    import statistics
    out['p6'] = {c: {'n': len(v), 'cpt_median': round(statistics.median(v),2)} for c,v in cpt.items()}
    meds = [out['p6'][c]['cpt_median'] for c in out['p6']]
    out['p6']['cross_case_spread'] = round(max(meds)/min(meds), 2)
    # 首响应模式
    out['dsh_first'] = {}
    for case in CASES:
        tots = [led['dsh'][f'dsh__{case}__r{r}']['records'][0]['usage']['totalTokens'] for r in (1,2,3)]
        out['dsh_first'][case] = {'totals': tots, 'spread_pct': round((max(tots)-min(tots))/min(tots)*100, 2)}
    out['codex_first'] = {}
    for case in CASES:
        recs = [led['codex'][f'codex__{case}__r{r}']['records'][0]['usage'] for r in (1,2,3)]
        out['codex_first'][case] = {'input': [u['input_tokens'] for u in recs],
                                    'input_identical': len({u['input_tokens'] for u in recs})==1,
                                    'cached': [u['cached_input_tokens'] for u in recs]}
    # 三 run 总量互异
    out['three_run_distinct'] = {}
    for case in CASES:
        for prod, key in (('dsh','totalTokens'),('codex','total_tokens')):
            vals = tuple(sum(r['usage'][key] for r in led[prod][f'{prod}__{case}__r{r}']['records']) for r in (1,2,3))
            out['three_run_distinct'][f'{prod} {case}'] = len(set(vals))
    out['dsh_rel'] = dict(dsh_rel); out['codex_rel'] = dict(cod_rel)
    out['n_dsh'] = sum(s['n'] for s in led['dsh'].values())
    out['n_codex'] = sum(s['n'] for s in led['codex'].values())
    return out

if __name__ == '__main__':
    try:
        r = recompute()
    except Invalid as e:
        print(f'INVALID: {e}'); sys.exit(1)
    print(json.dumps(r, ensure_ascii=False, indent=1))
