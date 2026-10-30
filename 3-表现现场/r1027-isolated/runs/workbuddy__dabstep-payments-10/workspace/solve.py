import json, csv, datetime, collections

F = json.load(open('inputs/fees.json'))
MER = {m['merchant']: m for m in json.load(open('inputs/merchant_data.json'))}

def mdate(d):  # day_of_year -> date (2023)
    return datetime.date(2023, 1, 1) + datetime.timedelta(days=d - 1)

def vband(v):
    return '<100k' if v < 100000 else '100k-1m' if v < 1000000 else '1m-5m' if v < 5000000 else '>5m'

def fband(r):
    if r < 0.072: return '<7.2%'
    if r < 0.077: return '7.2%-7.7%'
    if r < 0.083: return '7.7%-8.3%'
    return '>8.3%'

def cap_bucket(cd):
    cd = str(cd)
    if cd == 'immediate' or cd == 'manual': return cd
    n = float(cd)
    return '<3' if n < 3 else '3-5' if n <= 5 else '>5'

belles = [x for x in csv.DictReader(open('inputs/payments.csv')) if x['merchant'] == 'Belles_cookbook_store']
for r in belles:
    r['_mo'] = mdate(int(r['day_of_year'])).month
    r['_amt'] = float(r['eur_amount'])
    r['_intra'] = (r['issuing_country'] == r['acquirer_country'])
    r['_credit'] = (r['is_credit'] == 'True')
    r['_fraud'] = (r['has_fraudulent_dispute'] == 'True')

def month_ctx(rows):
    v = sum(r['_amt'] for r in rows)
    fv = sum(r['_amt'] for r in rows if r['_fraud'])
    return fband(fv / v), vband(v)

def rule_ok(x, scheme, acct, cap, fraud, vol, credit, aci, intra, mcc):
    if x['card_scheme'] != scheme: return False
    if x['account_type'] and acct not in x['account_type']: return False
    if x['capture_delay'] and x['capture_delay'] != cap: return False
    if x['monthly_fraud_level'] and x['monthly_fraud_level'] != fraud: return False
    if x['monthly_volume'] and x['monthly_volume'] != vol: return False
    if x['is_credit'] is not None and bool(x['is_credit']) != credit: return False
    if x['aci'] and aci not in x['aci']: return False
    if x['intracountry'] is not None and float(x['intracountry']) != (1.0 if intra else 0.0): return False
    if x['merchant_category_code'] and mcc not in x['merchant_category_code']: return False
    return True

def ids_for(rows, ctx_rows=None):
    fb, vb = month_ctx(ctx_rows if ctx_rows is not None else rows)
    m = MER['Belles_cookbook_store']
    cap = cap_bucket(m['capture_delay'])
    out = set()
    for r in rows:
        for x in F:
            if rule_ok(x, r['card_scheme'], m['account_type'], cap, fb, vb, r['_credit'], r['aci'], r['_intra'], m['merchant_category_code']):
                out.add(x['ID'])
    return sorted(out)

def fee(x, amt):
    return x['fixed_amount'] + x['rate'] * amt / 10000.0

ans = {}

# Q5 top issuing country
c = collections.Counter(x['issuing_country'] for x in csv.DictReader(open('inputs/payments.csv')))
ans['5'] = c.most_common(1)[0][0]

# Q49 top ip country for fraud among NL,BE,ES,FR
fr = collections.Counter()
for x in csv.DictReader(open('inputs/payments.csv')):
    if x['has_fraudulent_dispute'] == 'True':
        fr[x['ip_country']] += 1
opts = [('A', 'NL'), ('B', 'BE'), ('C', 'ES'), ('D', 'FR')]
best = max(opts, key=lambda o: fr[o[1]])
ans['49'] = f"{best[0]}. {best[1]}"

# Q70 Martinis fraud rate vs top fee band
mart = [x for x in csv.DictReader(open('inputs/payments.csv')) if x['merchant'] == 'Martinis_Fine_Steakhouse']
tot = sum(float(x['eur_amount']) for x in mart)
ftot = sum(float(x['eur_amount']) for x in mart if x['has_fraudulent_dispute'] == 'True')
ans['70'] = 'yes' if (ftot / tot) > 0.083 else 'no'

# Q1273 GlobalCard, credit, 10 EUR average
def avg(rules, v=10.0):
    return round(sum(fee(x, v) for x in rules) / len(rules), 6)
gcard = [x for x in F if x['card_scheme'] == 'GlobalCard']
ans['1273'] = f"{avg([x for x in gcard if x['is_credit'] is True or x['is_credit'] is None]):.6f}"

# Q1305 GlobalCard, account H, MCC 5812, 10 EUR
rules1305 = [x for x in gcard
             if (not x['account_type'] or 'H' in x['account_type'])
             and (not x['merchant_category_code'] or 5812 in x['merchant_category_code'])]
ans['1305'] = f"{avg(rules1305):.6f}"

# Q1464 rules applicable to account_type R and aci B
r1464 = sorted(x['ID'] for x in F
               if (not x['account_type'] or 'R' in x['account_type'])
               and (not x['aci'] or 'B' in x['aci']))
ans['1464'] = ', '.join(str(i) for i in r1464)

# Q1681 day 10
d10 = [r for r in belles if int(r['day_of_year']) == 10]
ans['1681'] = ', '.join(str(i) for i in ids_for(d10, [r for r in belles if r['_mo'] == 1]))

# Q1753 March
mar = [r for r in belles if r['_mo'] == 3]
ans['1753'] = ', '.join(str(i) for i in ids_for(mar))

# Q1871 delta for rule 384 rate -> 1
jan = [r for r in belles if r['_mo'] == 1]
amt384 = sum(r['_amt'] for r in jan
             if r['card_scheme'] == 'NexPay' and r['_credit'] and r['aci'] in ('C', 'B'))
delta = (1 - 14) * amt384 / 10000.0
ans['1871'] = f"{delta:.14f}"

# Q2697 cheapest priced (scheme, aci) for January fraudulent transactions
fb, vb = month_ctx(jan)
cap = cap_bucket(MER['Belles_cookbook_store']['capture_delay'])
fraud = [r for r in jan if r['_fraud']]
best = None
for scheme in ['GlobalCard', 'NexPay', 'SwiftCharge', 'TransactPlus']:
    sub = [r for r in fraud if r['card_scheme'] == scheme]
    if not sub: continue
    for aci in 'ABCDEFG':
        n, tot_fee = 0, 0.0
        for r in sub:
            for x in F:
                if rule_ok(x, scheme, 'R', cap, fb, vb, r['_credit'], aci, r['_intra'], 5942):
                    n += 1
                    tot_fee += fee(x, r['_amt'])
        if n and (best is None or tot_fee < best[0]):
            best = (tot_fee, scheme)
ans['2697'] = f"{best[1]}:{best[0]:.2f}"

with open('answers.jsonl', 'w', encoding='utf-8') as f:
    for k in ['5', '49', '70', '1273', '1305', '1464', '1681', '1753', '1871', '2697']:
        f.write(json.dumps({'task_id': k, 'answer': str(ans[k])}, ensure_ascii=False) + '\n')
print({k: (v[:80] + '...' if len(str(v)) > 80 else v) for k, v in ans.items()})
print('counts', len(r1464), ans['1681'].count(',') + 1, ans['1753'].count(',') + 1)
