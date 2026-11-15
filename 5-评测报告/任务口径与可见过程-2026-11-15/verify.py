#!/usr/bin/env python3
"""Only reads the named public files; never runs recorded commands or writes output."""
import csv
import hashlib
import json
from collections import defaultdict
from decimal import Decimal, localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / '2-用例/dabstep-payments-10'
RUN = ROOT / '3-表现现场/r1030-formal-a1/runs/codex__dabstep-payments-10'
ROLLOUT_SHA = 'f7244ceab9e8754dcef93afdcd0c8f10402bba1d41d9fc4907eaf19e99f78132'


def locate_rollout():
    candidates = [p for p in (RUN / 'agent-session').glob('*.jsonl')
                  if hashlib.sha256(p.read_bytes()).hexdigest() == ROLLOUT_SHA]
    if len(candidates) != 1:
        raise ValueError('expected exactly one recorded session matching the SHA-256')
    return candidates[0]


ROLLOUT = locate_rollout()
SOURCES = {
    CASE / 'inputs/payments.csv': '5fbb26210a45427d7a6560cfab3a362a08e4067f27cd03695f211a51c47ffc25',
    CASE / 'inputs/manual.md': 'bb7f4ca6fdc759af1f480702b3a3b12e17e9293b0d38a1dbfbbc8ffc1e572d2c',
    CASE / 'inputs/questions.jsonl': 'd99d3109e216b8e091d478602fce7cb687b47c40338ce8d016300c9ee7013730',
    ROLLOUT: 'f7244ceab9e8754dcef93afdcd0c8f10402bba1d41d9fc4907eaf19e99f78132',
    RUN / 'workspace/answers.jsonl': 'b97ea004f488834145d22d18a0b5461c721dd77800295b2bff69bef415dfaf2b',
    RUN / 'checker.stdout.json': '9f040885cd97322be3d1fcdb4fc1d9ac0cb11944c074bb6c8f3b2b9bd908615f',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_events(path):
    with path.open(encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]


def item(events, call_id, kind):
    matches = [e for e in events if e.get('type') == 'response_item'
               and e.get('payload', {}).get('type') == kind
               and e['payload'].get('call_id') == call_id]
    require(len(matches) == 1, 'call identity is absent or not unique')
    return matches[0]


def main():
    for path, expected in SOURCES.items():
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected,
                'source hash mismatch: ' + str(path.relative_to(ROOT)))
    events = load_events(ROLLOUT)
    # Resolve pairing identifiers from the pinned evidence without copying them.
    definition_id, compute_id, write_id = (events[i-1]['payload']['call_id'] for i in (47, 63, 207))
    definition_call = item(events, definition_id, 'function_call')
    defined = item(events, definition_id, 'function_call_output')
    compute = item(events, compute_id, 'function_call')
    result = item(events, compute_id, 'function_call_output')
    write = item(events, write_id, 'function_call')
    done = item(events, write_id, 'function_call_output')
    definition = defined['payload']['output']
    calculation = json.loads(compute['payload']['arguments'])['cmd']
    calculation_result = result['payload']['output']
    writer = json.loads(write['payload']['arguments'])['cmd']
    write_result = done['payload']['output']
    require('Fraud is defined as the ratio of fraudulent volume over total volume.' in definition and 'truncated' not in definition.lower(), 'definition not available in selected return')
    require('fraud_amt[c]/all_amt[c]' in calculation and 'fraud_ct' in calculation, 'selected computation changed')
    require('Process exited with code 0' in calculation_result and 'truncated' not in calculation_result.lower(), 'calculation output incomplete')
    require('NL 0.09929435483870967 0.12181546743244216' in calculation_result and
            'BE 0.10850452646239554 0.12268639678310043' in calculation_result,
            'selected ratios changed')
    require("fraud_ip_counts[row['ip_country']] += 1" in writer and
            "answers['49'] = 'A. ' + fraud_ip_counts.most_common(1)[0][0]" in writer and
            "open('answers.jsonl', 'w'" in writer, 'final writer differs')
    require("49 5 'A. NL'" in write_result and 'Process exited with code 0' in write_result, 'writer result differs')
    require(definition_call['timestamp'] < defined['timestamp'] < compute['timestamp'] < result['timestamp'] < write['timestamp'] < done['timestamp'], 'unexpected ordering')
    answers = load_events(RUN / 'workspace/answers.jsonl')
    q49 = [a for a in answers if a.get('task_id') == '49']
    require(len(q49) == 1 and q49[0]['answer'] == 'A. NL', 'answer changed')
    receipt = json.loads((RUN / 'checker.stdout.json').read_text(encoding='utf-8'))
    checks = [c for c in receipt['official_compat']['checks'] if c.get('id') == 'q49']
    require(len(checks) == 1 and checks[0]['pass'] is False and
            "pred='A. NL'" in checks[0]['note'] and "gold='B. BE'" in checks[0]['note'], 'receipt mismatch')
    require(receipt['official_compat']['correct'] == 7 and receipt['official_compat']['reward'] == 0, 'receipt summary mismatch')
    totals = defaultdict(lambda: [0, 0, Decimal(0), Decimal(0)])
    count = 0
    with (CASE / 'inputs/payments.csv').open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            count += 1
            group = totals[row['ip_country']]
            amount = Decimal(row['eur_amount'])
            group[0] += 1
            group[2] += amount
            if row['has_fraudulent_dispute'] == 'True':
                group[1] += 1
                group[3] += amount
    with localcontext() as ctx:
        ctx.prec = 36
        rates = {k: v[3] / v[2] for k, v in totals.items()}
        require(count == 138236 and len(rates) == 8, 'unexpected source population')
        require(max(rates, key=rates.get) == 'BE' and max(totals, key=lambda c: totals[c][1]) == 'NL', 'winners differ')
        for c, expected in {'NL': (29760, 2955, '2701907.13', '329134.08'),
                            'BE': (22976, 2493, '2150473.54', '263833.85')}.items():
            n, fraud_n, total, fraud = totals[c]
            require((n, fraud_n, str(total), str(fraud)) == expected, 'aggregate differs: ' + c)
        print(json.dumps({'rows': count, 'country_count': len(rates),
                          'count_winner': 'NL', 'amount_ratio_winner': 'BE',
                          'NL_amount_ratio': str(rates['NL']), 'BE_amount_ratio': str(rates['BE']),
                          'answer': q49[0]['answer'], 'gold': 'B. BE',
                          'receipt_q49_pass': False, 'source_hashes_checked': len(SOURCES)},
                         ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
