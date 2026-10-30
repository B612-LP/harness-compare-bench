import csv, json, collections, datetime, statistics

BASE='inputs/'
fees=json.load(open(BASE+'fees.json'))
merchants={m['merchant']:m for m in json.load(open(BASE+'merchant_data.json'))}
q=[json.loads(l) for l in open(BASE+'questions.jsonl')]
rows=list(csv.DictReader(open(BASE+'payments.csv')))

def wild(x): return x is None or x==[]
def fee(r,v): return r['fixed_amount'] + r['rate']*v/10000.0

def capture_cat(cd):
    if cd in ('manual','immediate'): return cd
    d=int(cd)
    if d<3: return '<3'
    if d<=5: return '3-5'
    return '>5'

def in_bin_fraud(lv,p):
    if lv is None: return True
    if lv=='<7.2%': return p<7.2
    if lv=='7.2%-7.7%': return 7.2<=p<=7.7
    if lv=='7.7%-8.3%': return 7.7<=p<=8.3
    if lv=='>8.3%': return p>8.3
    raise ValueError(lv)
def in_bin_vol(lv,v):
    if lv is None: return True
    if lv=='<100k': return v<100000
    if lv=='100k-1m': return 100000<=v<=1000000
    if lv=='1m-5m': return 1000000<=v<=5000000
    if lv=='>5m': return v>5000000
    raise ValueError(lv)

def merchant_match(r,mer,vol,fp):
    if not (wild(r['account_type']) or mer['account_type'] in r['account_type']): return False
    if not (r['capture_delay'] is None or r['capture_delay']==capture_cat(mer['capture_delay'])): return False
    if not in_bin_fraud(r['monthly_fraud_level'],fp): return False
    if not in_bin_vol(r['monthly_volume'],vol): return False
    if not (wild(r['merchant_category_code']) or mer['merchant_category_code'] in r['merchant_category_code']): return False
    return True

def tx_match(r,tx,aci,vol,fp):
    mer=merchants[tx['merchant']]
    if r['card_scheme']!=tx['card_scheme']: return False
    if not merchant_match(r,mer,vol,fp): return False
    if r['is_credit'] is not None and r['is_credit']!=(tx['is_credit']=='True'): return False
    if not (wild(r['aci']) or aci in r['aci']): return False
    intra = tx['issuing_country']==tx['acquirer_country']
    if r['intracountry'] is not None and bool(r['intracountry'])!=intra: return False
    return True

def month_of(tx):
    return (datetime.date(2023,1,1)+datetime.timedelta(days=int(tx['day_of_year'])-1)).month

# monthly stats per merchant
monthly={}
for m in merchants:
    for mo in range(1,13):
        rr=[r for r in rows if r['merchant']==m and month_of(r)==mo]
        vol=sum(float(r['eur_amount']) for r in rr)
        fv=sum(float(r['eur_amount']) for r in rr if r['has_fraudulent_dispute']=='True')
        monthly[(m,mo)]=(vol, fv/vol*100 if vol else 0.0)

ans={}

# 5
c=collections.Counter(r['issuing_country'] for r in rows)
ans['5']=c.most_common(1)[0][0]

# 49
fc=collections.Counter(r['ip_country'] for r in rows if r['has_fraudulent_dispute']=='True')
opts=['NL','BE','ES','FR']
best=max(opts,key=lambda x:fc[x])
ans['49']=f"{chr(ord('A')+opts.index(best))}. {best}"

# 70
m='Martinis_Fine_Steakhouse'
danger=False
for mo in range(1,13):
    vol,fp=monthly[(m,mo)]
    if fp>8.3: danger=True
ans['70']='yes' if danger else 'no'

# 1273
sel=[r for r in fees if r['card_scheme']=='GlobalCard' and (r['is_credit'] is True or r['is_credit'] is None)]
ans['1273']=f"{sum(fee(r,10) for r in sel)/len(sel):.6f}"

# 1305
sel=[r for r in fees if r['card_scheme']=='GlobalCard' and (wild(r['account_type']) or 'H' in r['account_type']) and (wild(r['merchant_category_code']) or 5812 in r['merchant_category_code'])]
ans['1305']=f"{sum(fee(r,10) for r in sel)/len(sel):.6f}"

# 1464
sel=[r for r in fees if (wild(r['account_type']) or 'R' in r['account_type']) and (wild(r['aci']) or 'B' in r['aci'])]
ans['1464']=', '.join(str(x) for x in sorted(r['ID'] for r in sel))

# Belles helper
mer=merchants['Belles_cookbook_store']
def applicable_ids(txs,mo):
    vol,fp=monthly[('Belles_cookbook_store',mo)]
    ids=set()
    for tx in txs:
        for r in fees:
            if tx_match(r,tx,tx['aci'],vol,fp): ids.add(r['ID'])
    return sorted(ids)

# 1681 day 10
txs=[r for r in rows if r['merchant']=='Belles_cookbook_store' and int(r['day_of_year'])==10]
ans['1681']=', '.join(str(x) for x in applicable_ids(txs,1))

# 1753 March
txs=[r for r in rows if r['merchant']=='Belles_cookbook_store' and month_of(r)==3]
ans['1753']=', '.join(str(x) for x in applicable_ids(txs,3))

# 1871 delta rule 384 rate -> 1
vol,fp=monthly[('Belles_cookbook_store',1)]
jan=[r for r in rows if r['merchant']=='Belles_cookbook_store' and month_of(r)==1]
amt=0.0
for tx in jan:
    if any(r['ID']==384 and tx_match(r,tx,tx['aci'],vol,fp) for r in fees):
        amt+=float(tx['eur_amount'])
delta=amt*(14-1)/10000.0
ans['1871']=f"{delta:.14f}"

# 2697 best different ACI, lowest possible fee per fraudulent transaction
fraud=[r for r in jan if r['has_fraudulent_dispute']=='True']
best=None
for aci in 'ABCDEF':
    tot=0.0
    for tx in fraud:
        vals=[fee(r,float(tx['eur_amount'])) for r in fees if tx_match(r,tx,aci,vol,fp)]
        if vals: tot+=min(vals)
    if best is None or tot<best[1]: best=(aci,tot)
ans['2697']=f"{best[0]}:{best[1]:.2f}"

with open('answers.jsonl','w') as fh:
    for item in q:
        tid=item['task_id']
        fh.write(json.dumps({'task_id':tid,'answer':ans[tid]},ensure_ascii=False)+'\n')
print(json.dumps(ans,indent=2))
