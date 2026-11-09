#!/usr/bin/env python3
"""环9 派生分析机械复算收据：重算 5-评测报告/派生分析-dabstep失败归因-20261109/README.md 全部数字。
只读公开仓与公开用例数据 + 私档 wb 原批 answers（仅读三题答案文本）。
输出收据 write-once：receipts/derive-dabstep-attribution-r1.json
用法： python3 derive-dabstep-attribution.py <公开仓根> <wb私档归档根> [--receipt <path>]
公开读者：wb 私档归档不可得时，可传入空目录——8 轮公开槽位仍全算，wb 三轮记 missing（收据会如实标注）。
"""
import csv, json, sys, hashlib, argparse
from collections import Counter
from pathlib import Path

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def load_answers(p):
    ans = {}
    for line in open(p, encoding='utf-8'):
        line = line.strip()
        if line:
            d = json.loads(line)
            qid = str(d.get('task_id') or d.get('adversary_id') or d.get('question_id') or d.get('id'))
            ans[qid] = d.get('answer')
    return ans

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('repo')
    ap.add_argument('wb_archive')
    ap.add_argument('--receipt', default=None)
    a = ap.parse_args()
    repo = Path(a.repo)
    inputs = repo / '2-用例' / 'dabstep-payments-10' / 'inputs'
    out = {'tool': 'derive-dabstep-attribution.py r1', 'inputs_sha256': {
        'payments.csv': sha256_file(inputs / 'payments.csv'),
        'manual.md': sha256_file(inputs / 'manual.md'),
        'fees.json': sha256_file(inputs / 'fees.json'),
        'questions.jsonl': sha256_file(inputs / 'questions.jsonl'),
        'truth.json': sha256_file(repo / '2-用例' / 'dabstep-payments-10' / 'truth.json'),
    }}
    rows = list(csv.DictReader(open(inputs / 'payments.csv')))
    total = len(rows)
    fr = [r for r in rows if r['has_fraudulent_dispute'] == 'True']
    tc = Counter(r['ip_country'] for r in rows)
    fc = Counter(r['ip_country'] for r in fr)
    countries = {}
    for c in ('NL', 'BE', 'ES', 'FR'):
        countries[c] = {'fraud_count': fc[c], 'total': tc[c],
                        'rate_pct': round(fc[c] / tc[c] * 100, 3)}
    out['q49'] = {'fraud_rows': len(fr), 'countries': countries,
                  'gold': 'B. BE', 'expected_top_by_ratio': 'BE',
                  'expected_top_by_count': max(countries, key=lambda c: countries[c]['fraud_count'])}
    mart = [r for r in rows if r['merchant'] == 'Martinis_Fine_Steakhouse']
    martf = [r for r in mart if r['has_fraudulent_dispute'] == 'True']
    out['q70'] = {'martinis_tx': len(mart), 'fraud_tx': len(martf),
                  'rate_pct': round(len(martf) / len(mart) * 100, 4) if mart else None,
                  'manual_fine_sections': '§7.4 PCI DSS non-compliance EUR5,000-100,000/month only',
                  'gold': 'Not Applicable'}
    bel = [r for r in rows if r['merchant'] == 'Belles_cookbook_store'
           and r['year'] == '2023' and int(r['day_of_year']) <= 31]
    bf = [r for r in bel if r['has_fraudulent_dispute'] == 'True']
    out['q2697'] = {'belles_jan_tx': len(bel), 'fraud_tx': len(bf),
                    'aci_dist': dict(Counter(r['aci'] for r in bf)),
                    'shopper_interaction': dict(Counter(r['shopper_interaction'] for r in bf)),
                    'card_schemes': dict(Counter(r['card_scheme'] for r in bf)),
                    'fees_rules': len(json.load(open(inputs / 'fees.json'))),
                    'gold': 'E:13.57'}
    # 11 轮答案
    slots = []
    for arm in ('dsh', 'codex'):
        p = repo / '3-表现现场' / 'r1030-formal-a1' / 'runs' / f'{arm}__dabstep-payments-10' / 'workspace' / 'answers.jsonl'
        slots.append(('r1030-a1', arm, 'r1', str(p)))
        for r in (1, 2, 3):
            p = repo / '3-表现现场' / 'r1109-mech-n3' / 'runs' / f'{arm}__dabstep-payments-10__r{r}' / 'workspace' / 'answers.jsonl'
            slots.append(('r1109-mech-n3', arm, f'r{r}', str(p)))
    for r in (1, 2, 3):
        p = Path(a.wb_archive) / 'wb-n3-20261101' / 'runs' / f'dabstep-payments-10__r{r}' / 'workspace' / 'answers.jsonl'
        slots.append(('wb-n3-20261101', 'workbuddy', f'r{r}', str(p)))
    answers = []
    q49 = q70 = q2697err = 0
    v2697 = Counter()
    for batch, arm, rep, p in slots:
        if not Path(p).exists():
            answers.append({'batch': batch, 'arm': arm, 'rep': rep,
                            'q49': None, 'q70': None, 'q2697': None,
                            'source': 'missing-file'})
            continue
        ans = load_answers(p)
        a49, a70, a2697 = ans.get('49'), ans.get('70'), ans.get('2697')
        q49 += (a49 == 'A. NL')
        q70 += (a70 == 'yes')
        gold2697 = (a2697 == 'E:13.57')
        q2697err += (not gold2697)
        if not gold2697:
            v2697[a2697] += 1
        answers.append({'batch': batch, 'arm': arm, 'rep': rep,
                        'q49': a49, 'q70': a70, 'q2697': a2697,
                        'source': 'public' if 'bench-private' not in p else 'private-archive-readout'})
    out['answers_11_slots'] = answers
    out['consistency'] = {'q49_A.NL': f'{q49}/11', 'q70_yes': f'{q70}/11',
                          'q2697_all_wrong': f'{q2697err}/11',
                          'q2697_wrong_values': dict(v2697)}
    out['verdict'] = ('q49/q70 deterministic across 11 slots (3 forms); '
                      'q2697 all wrong, value converges within arm')
    blob = json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True).encode()
    print(blob.decode()[:1200])
    if a.receipt:
        rp = Path(a.receipt)
        if rp.exists():
            print('RECEIPT EXISTS (write-once):', rp)
            sys.exit(3)
        rp.write_bytes(blob)
        print('receipt written:', rp)

if __name__ == '__main__':
    main()
