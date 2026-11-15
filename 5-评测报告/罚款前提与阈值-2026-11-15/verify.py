#!/usr/bin/env python3
"""Read-only q70 evidence verification. Never evaluate recorded code."""
import csv
import datetime
import hashlib
import json
import re
from collections import Counter, defaultdict
from decimal import Decimal, localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASE = Path('2-用例/dabstep-payments-10')
RUN = Path('3-表现现场/r1030-formal-a1/runs/codex__dabstep-payments-10')
ROLLOUT_SHA = 'f7244ceab9e8754dcef93afdcd0c8f10402bba1d41d9fc4907eaf19e99f78132'


def locate_rollout():
    """Bind the existing public evidence by hash without copying its identifier."""
    candidates = []
    for path in (ROOT / RUN / 'agent-session').glob('*.jsonl'):
        if hashlib.sha256(path.read_bytes()).hexdigest() == ROLLOUT_SHA:
            candidates.append(path.relative_to(ROOT))
    if len(candidates) != 1:
        raise ValueError('expected exactly one recorded session matching the SHA-256')
    return candidates[0]


ROLLOUT = locate_rollout()
SOURCES = {
    CASE / 'inputs/payments.csv': '5fbb26210a45427d7a6560cfab3a362a08e4067f27cd03695f211a51c47ffc25',
    CASE / 'inputs/fees.json': '9a833666ae9be5a8e756dd1fe076c72e7c502d64161315ffa8fee9e5bf2599dc',
    CASE / 'inputs/manual.md': 'bb7f4ca6fdc759af1f480702b3a3b12e17e9293b0d38a1dbfbbc8ffc1e572d2c',
    CASE / 'inputs/questions.jsonl': 'd99d3109e216b8e091d478602fce7cb687b47c40338ce8d016300c9ee7013730',
    CASE / 'truth.json': '9e6e395fc7b0e5cf60238b8c3ab30fdaa399422fc047f554f0198488156e46d8',
    CASE / 'solution/answers.jsonl': 'a8c497b953b1b09ff9f9f5310481866cbf574cd94c16019bd8b74fef21f977e1',
    ROLLOUT: 'f7244ceab9e8754dcef93afdcd0c8f10402bba1d41d9fc4907eaf19e99f78132',
    RUN / 'workspace/answers.jsonl': 'b97ea004f488834145d22d18a0b5461c721dd77800295b2bff69bef415dfaf2b',
    RUN / 'checker.stdout.json': '9f040885cd97322be3d1fcdb4fc1d9ac0cb11944c074bb6c8f3b2b9bd908615f',
    RUN / 'meta.json': 'b494785767bbb77e2139f4b21c2792ee172d4d37fef79513c7edfc1c9f414081',
    RUN / 'integrity-rescan.json': '81556460c007922742987354452268ebf209e70a59d5e78375397c42f0ff0f73',
    RUN / 'workspace/TASK.md': '2bbab140db19ebe04c045db45b0996ae65df2701aa4b86de500241d0570bce14',
    Path('5-评测报告/派生分析-dabstep失败归因-20261109/README.md'): '5985246a974e3641f1188c51f3391ad27bcdcc639273c2af530696749ba62ee2',
}
EXPECTED = {
    '2023-01': (1238,111,'118125.01','11406.55'), '2023-02': (1018,83,'91877.05','7805.73'),
    '2023-03': (1153,85,'103726.64','8004.60'), '2023-04': (1129,101,'102916.05','10204.50'),
    '2023-05': (1194,114,'110282.17','11171.76'), '2023-06': (1110,83,'100892.63','8503.55'),
    '2023-07': (1212,84,'109147.70','7883.99'), '2023-08': (1218,94,'114158.24','11666.66'),
    '2023-09': (1196,89,'109430.93','9556.04'), '2023-10': (1131,97,'97814.79','8733.36'),
    '2023-11': (1125,92,'105303.30','10693.83'), '2023-12': (1081,72,'96552.67','9477.96'),
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def load_json(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def jsonl(path):
    with (ROOT / path).open(encoding='utf-8') as f:
        lines = list(f)
    require(all(line.strip() for line in lines), 'blank JSONL line would change physical numbering')
    return [json.loads(line) for line in lines]


def utc_time(event):
    value = event['timestamp']
    require(isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z', value) is not None, 'timestamp must be a UTC date-time')
    parsed = datetime.datetime.fromisoformat(value[:-1] + '+00:00')
    require(parsed.tzinfo is not None and parsed.utcoffset() == datetime.timedelta(0), 'timestamp must be UTC')
    return parsed


def only(items, description):
    require(len(items) == 1, description + ': expected exactly one')
    return items[0]


def pair(events, call_id):
    found = [(i, e) for i, e in enumerate(events, 1) if e.get('type') == 'response_item'
             and e.get('payload', {}).get('call_id') == call_id]
    calls = [(i, e) for i, e in found if e['payload'].get('type') == 'function_call']
    outputs = [(i, e) for i, e in found if e['payload'].get('type') == 'function_call_output']
    a, b = only(calls, 'call'), only(outputs, 'call output')
    require(len(found) == 2 and a[0] < b[0] and utc_time(a[1]) < utc_time(b[1]), 'call pair/order')
    require(a[1]['payload'].get('name') == 'exec_command', 'unexpected tool')
    cmd = json.loads(a[1]['payload']['arguments'])['cmd']
    out = b[1]['payload']['output']
    require('Process exited with code 0' in out and 'truncated' not in out.lower(), 'tool return failed/truncated')
    return a, b, cmd, out


def verify_events(events):
    # Obtain pairing identifiers from the pinned evidence; do not reproduce them.
    search = pair(events, events[28]['payload']['call_id'])
    fees = pair(events, events[48]['payload']['call_id'])
    final = pair(events, events[206]['payload']['call_id'])
    require([search[0][0],search[1][0],fees[0][0],fees[1][0],final[0][0],final[1][0]] == [29,37,49,55,207,210], 'event line sequence')
    chain = [search[0],search[1],fees[0],fees[1],final[0],final[1]]
    require(all(utc_time(a[1]) < utc_time(b[1]) for a,b in zip(chain,chain[1:])), 'event timestamp order')
    require('inputs/manual.md' in search[2] and 'monthly' in search[2] and 'fraud' in search[2], 'search command')
    require('82:* **monthly_fraud_level**' in search[3] and "'7.7%-8.3%'" in search[3], 'search result')
    require("fees=json.load(open('inputs/fees.json'))" in fees[2] and 'for k in fees[0]' in fees[2] and 'vals.most_common(12)' in fees[2], 'distinct call')
    fee_line = "monthly_fraud_level distinct 5 top [(None, 900), ('7.7%-8.3%', 29), ('<7.2%', 26), ('7.2%-7.7%', 24), ('>8.3%', 21)]"
    require(fee_line in fees[3], 'distinct output')
    block = """amount = float(row['eur_amount'])
        if row['merchant'] == 'Martinis_Fine_Steakhouse':
            martinis_volume += amount
            if row['has_fraudulent_dispute'] == 'True':
                martinis_fraud_volume += amount"""
    require("for row in csv.DictReader(f):" in final[2] and block in final[2], 'final aggregation')
    require("answers['70'] = 'yes' if martinis_fraud_volume / martinis_volume > 0.083 else 'no'" in final[2], 'threshold expression')
    require("with open('answers.jsonl', 'w', encoding='utf-8') as out:" in final[2] and "70 3 'yes'" in final[3], 'write/return')
    return [x[0] for x in chain]


def aggregates(path):
    grouped = defaultdict(lambda: [0,0,Decimal(0),Decimal(0)])
    n = 0
    with path.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            n += 1
            if row['merchant'] != 'Martinis_Fine_Steakhouse':
                continue
            require(row['year'] == '2023', 'unexpected year')
            day = int(row['day_of_year'])
            require(1 <= day <= 365, 'bad day')
            month = (datetime.date(2023,1,1) + datetime.timedelta(days=day-1)).isoformat()[:7]
            require(row['has_fraudulent_dispute'] in ('True','False'), 'bad fraud flag')
            amount = Decimal(row['eur_amount'])
            require(amount.is_finite(), 'nonfinite amount')
            g = grouped[month]
            g[0] += 1
            g[2] += amount
            if row['has_fraudulent_dispute'] == 'True':
                g[1] += 1
                g[3] += amount
    require(n == 138236, 'source population')
    actual = {k:(v[0],v[1],str(v[2]),str(v[3])) for k,v in grouped.items()}
    require(actual == EXPECTED, 'monthly results mismatch')
    totals = [sum(v[i] for v in grouped.values()) for i in range(4)]
    require((totals[0],totals[1],str(totals[2]),str(totals[3])) == (13805,1105,'1260227.18','115108.53'), 'all-period results mismatch')
    return grouped, totals


def main():
    for path, expected in SOURCES.items():
        require(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, 'SHA-256 mismatch: ' + str(path))
    meta, truth = load_json(RUN / 'meta.json'), load_json(CASE / 'truth.json')
    require(meta['product'] == 'codex' and meta['case'] == 'dabstep-payments-10' and meta['batch'] == 'r1030-formal-a1', 'run identity')
    require(meta['created_at'] == '2026-10-29T02:15:39+08:00', 'run timestamp')
    for name in ('payments.csv','fees.json','manual.md','questions.jsonl'):
        digest = SOURCES[CASE / 'inputs' / name]
        pin = only([x for x in meta['inputs'] if x['path'] == 'inputs/' + name], 'metadata input')
        require(pin['sha256'] == digest == truth['input_sha256'][name], 'source pin mismatch')
        require(pin['bytes'] == (ROOT / CASE / 'inputs' / name).stat().st_size == truth['input_bytes'][name], 'source size mismatch')
    require(meta['prompt_sha256'] == SOURCES[RUN / 'workspace/TASK.md'], 'prompt source pin')
    rescan = load_json(RUN / 'integrity-rescan.json')
    entry = only([x for x in rescan['session_files'] if x['name'] == ROLLOUT.name], 'rescan session')
    require(entry['bytes'] == (ROOT / ROLLOUT).stat().st_size and rescan['run'] == 'codex__dabstep-payments-10', 'rescan binding')
    lines = verify_events(jsonl(ROLLOUT))
    manual = (ROOT / CASE / 'inputs/manual.md').read_text(encoding='utf-8')
    for text in ('monthly_fraud_level', '7.7%-8.3%', 'Fraud is defined as the ratio of fraudulent volume over total volume.', 'To avoid penalties and increased costs', 'EUR5,000 to EUR100,000 per month'):
        require(text in manual, 'manual evidence missing')
    fee_data = load_json(CASE / 'inputs/fees.json')
    counts = Counter(x['monthly_fraud_level'] for x in fee_data)
    require(len(fee_data) == 1000 and counts == {None:900,'7.7%-8.3%':29,'<7.2%':26,'7.2%-7.7%':24,'>8.3%':21}, 'fee source disagrees with output')
    question = only([x for x in jsonl(CASE / 'inputs/questions.jsonl') if x['task_id'] == '70'], 'question')
    require(question['question'] == 'Is Martinis_Fine_Steakhouse in danger of getting a high-fraud rate fine?' and 'Not Applicable' in question['guidelines'], 'q70 changed')
    gold = only([x for x in jsonl(CASE / 'solution/answers.jsonl') if x['task_id'] == '70'], 'solution')
    answer = only([x for x in jsonl(RUN / 'workspace/answers.jsonl') if x['task_id'] == '70'], 'answer')
    require(gold['answer'] == truth['gold']['70'] == 'Not Applicable' and answer['answer'] == 'yes', 'q70 answer/gold')
    receipt = load_json(RUN / 'checker.stdout.json')['official_compat']
    check = only([x for x in receipt['checks'] if x['id'] == 'q70'], 'receipt check')
    require(check['pass'] is False and "pred='yes'" in check['note'] and "gold='Not Applicable'" in check['note'], 'q70 receipt')
    require(receipt['correct'] == 7 and receipt['weighted'] == 70.0 and receipt['reward'] == 0, 'score receipt')
    grouped, total = aggregates(ROOT / CASE / 'inputs/payments.csv')
    with localcontext() as ctx:
        ctx.prec = 36
        monthly = {k: {'transactions':v[0], 'fraud_transactions':v[1], 'total_eur':str(v[2]), 'fraud_eur':str(v[3]), 'fraud_amount_ratio':str(v[3]/v[2]), 'above_0083':v[3] > v[2]*Decimal('0.083')} for k,v in sorted(grouped.items())}
        result = {'monthly':monthly,'all_period':{'transactions':total[0], 'fraud_transactions':total[1], 'total_eur':str(total[2]), 'fraud_eur':str(total[3]), 'fraud_amount_ratio':str(total[3]/total[2]), 'fraud_count_ratio':str(Decimal(total[1])/Decimal(total[0])), 'above_0083':total[3] > total[2]*Decimal('0.083')}, 'answer':'yes','gold':'Not Applicable','receipt_pass':False,'event_lines':lines}
    require(result['all_period']['above_0083'] and sum(x['above_0083'] for x in monthly.values()) == 10, 'threshold result')
    encoded = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(',',':')).encode('utf-8')
    result_hash = hashlib.sha256(encoded).hexdigest()
    require(result_hash == '7bb19a870399ce8c284c5a3e4a2cf91c067a12350323a4b939650543c9a096a8', 'canonical result SHA-256 mismatch')
    print(json.dumps({'source_hashes_checked':len(SOURCES), 'result_sha256':result_hash, 'result':result}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
