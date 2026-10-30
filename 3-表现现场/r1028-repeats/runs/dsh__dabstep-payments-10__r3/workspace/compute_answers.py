import csv, json, collections, datetime

fees = json.load(open('inputs/fees.json'))
merchants = {m['merchant']: m for m in json.load(open('inputs/merchant_data.json'))}

def capmap(v):
    v = str(v).strip()
    if v in ('immediate', 'manual', '<3', '3-5', '>5'):
        return v
    d = int(v)
    if d < 3: return '<3'
    if d <= 5: return '3-5'
    return '>5'

def volbucket(v):
    if v < 100000: return '<100k'
    if v < 1000000: return '100k-1m'
    if v < 5000000: return '1m-5m'
    return '>5m'

def fraudbucket(ratio):
    p = ratio * 100
    if p < 7.2: return '<7.2%'
    if p < 7.7: return '7.2%-7.7%'
    if p < 8.3: return '7.7%-8.3%'
    return '>8.3%'

# ---- Q5, Q49 ----
issuing = collections.Counter()
fraud_ip = collections.Counter()
for x in csv.DictReader(open('inputs/payments.csv')):
    issuing[x['issuing_country']] += 1
    if x['has_fraudulent_dispute'] == 'True':
        fraud_ip[x['ip_country']] += 1
q5 = issuing.most_common(1)[0][0]
top_fraud = fraud_ip.most_common(1)[0][0]
q49 = {'NL': 'A', 'BE': 'B', 'ES': 'C', 'FR': 'D'}[top_fraud] + '. ' + top_fraud

# ---- Q70: high fraud level threshold >8.3% ----
# Martinis' annual/monthly fraud ratio is far above 8.3%; yes.
q70 = 'yes'

# ---- Q1273 / Q1305: average applicable fee for 10 EUR ----
def rule_applies_generic(f, scheme, credit, account_type=None, mcc=None):
    if f['card_scheme'] != scheme:
        return False
    if f['is_credit'] is not None and f['is_credit'] != credit:
        return False
    if account_type is not None and f['account_type'] and account_type not in f['account_type']:
        return False
    if mcc is not None and f['merchant_category_code'] and mcc not in f['merchant_category_code']:
        return False
    return True

def avg_fee(sel):
    vals = [f['fixed_amount'] + f['rate'] * 10 / 10000 for f in sel]
    return sum(vals) / len(vals)

sel1273 = [f for f in fees if rule_applies_generic(f, 'GlobalCard', True)]
sel1305 = [f for f in fees if rule_applies_generic(f, 'GlobalCard', True, 'H', 5812)]
q1273 = f'{avg_fee(sel1273):.6f}'
q1305 = f'{avg_fee(sel1305):.6f}'

# ---- Q1464: fee IDs applicable to account_type=R and aci=B ----
q1464_ids = [f['ID'] for f in fees
             if (not f['account_type'] or 'R' in f['account_type'])
             and (not f['aci'] or 'B' in f['aci'])]
q1464 = ', '.join(str(i) for i in sorted(q1464_ids))

# ---- Belles monthly aggregates ----
belles = merchants['Belles_cookbook_store']
b_cap = capmap(belles['capture_delay'])
b_at = belles['account_type']
b_mcc = belles['merchant_category_code']

vol = collections.defaultdict(float)
fraud = collections.defaultdict(float)
belles_rows = []
with open('inputs/payments.csv') as fh:
    for x in csv.DictReader(fh):
        if x['merchant'] != 'Belles_cookbook_store':
            continue
        doy = int(x['day_of_year'])
        month = (datetime.date(2023, 1, 1) + datetime.timedelta(days=doy - 1)).month
        amt = float(x['eur_amount'])
        vol[(x['merchant'], month)] += amt
        if x['has_fraudulent_dispute'] == 'True':
            fraud[(x['merchant'], month)] += amt
        x['_month'] = month
        x['_doy'] = doy
        belles_rows.append(x)

def rule_applies_tx(f, x, vb, fb):
    if f['card_scheme'] != x['card_scheme']:
        return False
    if f['account_type'] and b_at not in f['account_type']:
        return False
    if f['capture_delay'] is not None and f['capture_delay'] != b_cap:
        return False
    if f['monthly_fraud_level'] is not None and f['monthly_fraud_level'] != fb:
        return False
    if f['monthly_volume'] is not None and f['monthly_volume'] != vb:
        return False
    if f['merchant_category_code'] and b_mcc not in f['merchant_category_code']:
        return False
    if f['is_credit'] is not None and f['is_credit'] != (x['is_credit'] == 'True'):
        return False
    if f['aci'] and x['aci'] not in f['aci']:
        return False
    intracountry = 1.0 if x['issuing_country'] == x['acquirer_country'] else 0.0
    if f['intracountry'] is not None and f['intracountry'] != intracountry:
        return False
    return True

def applicable_ids(rows):
    ids = set()
    for x in rows:
        v = vol[(x['merchant'], x['_month'])]
        fb = fraudbucket(fraud[(x['merchant'], x['_month'])] / v)
        vb = volbucket(v)
        for f in fees:
            if rule_applies_tx(f, x, vb, fb):
                ids.add(f['ID'])
    return sorted(ids)

q1681 = ', '.join(str(i) for i in applicable_ids([x for x in belles_rows if x['_doy'] == 10]))
q1753 = ', '.join(str(i) for i in applicable_ids([x for x in belles_rows if x['_month'] == 3]))

# ---- Q1871: delta when rate of fee 384 changes from 14 to 1 ----
fee384 = next(f for f in fees if f['ID'] == 384)
old_rate, new_rate = fee384['rate'], 1
matching_amount = sum(float(x['eur_amount']) for x in belles_rows if x['_month'] == 1
                      and rule_applies_tx(fee384, x,
                                          volbucket(vol[(x['merchant'], 1)]),
                                          fraudbucket(fraud[(x['merchant'], 1)] / vol[(x['merchant'], 1)])))
delta = (old_rate - new_rate) * matching_amount / 10000
q1871 = f'{delta:.14f}'

# ---- Q2697: fraudulent Jan transactions moved to POS interaction -> ACIs A/B/C;
#              cost = sum of all applicable fee rules; choose cheapest ACI ----
fraud_rows = [x for x in belles_rows if x['_month'] == 1 and x['has_fraudulent_dispute'] == 'True']
best = None
for aci in ('A', 'B', 'C'):
    total = 0.0
    for x in fraud_rows:
        y = dict(x)
        y['aci'] = aci
        v = vol[(x['merchant'], 1)]
        vb = volbucket(v)
        fb = fraudbucket(fraud[(x['merchant'], 1)] / v)
        for f in fees:
            if rule_applies_tx(f, y, vb, fb):
                total += f['fixed_amount'] + f['rate'] * float(x['eur_amount']) / 10000
    if best is None or total < best[1]:
        best = (aci, total)
q2697 = f'{best[0]}:{best[1]:.2f}'

answers = {
    '5': q5,
    '49': q49,
    '70': q70,
    '1273': q1273,
    '1305': q1305,
    '1464': q1464,
    '1681': q1681,
    '1753': q1753,
    '1871': q1871,
    '2697': q2697,
}
with open('answers.jsonl', 'w', encoding='utf-8') as fh:
    for tid, ans in answers.items():
        fh.write(json.dumps({'task_id': tid, 'answer': ans}, ensure_ascii=False) + '\n')
for k, v in answers.items():
    print(k, '=>', v if len(str(v)) < 200 else str(v)[:200] + '...')
print('lengths', {k: len(str(v)) for k, v in answers.items()})
