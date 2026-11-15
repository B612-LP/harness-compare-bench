#!/usr/bin/env python3
"""Read-only, stdlib-only post-hoc q1871 recomputation; never executes trace code."""
import calendar
import csv
import datetime as dt
import hashlib
import io
import json
import re
from collections import Counter
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path

D = Decimal
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
CASE = '2-用例/dabstep-payments-10/'
RUN = '3-表现现场/r20261031-wb-replacement/runs/dabstep-payments-10/'
SOURCES = {
    CASE+'inputs/questions.jsonl': 'd99d3109e216b8e091d478602fce7cb687b47c40338ce8d016300c9ee7013730',
    CASE+'inputs/fees.json': '9a833666ae9be5a8e756dd1fe076c72e7c502d64161315ffa8fee9e5bf2599dc',
    CASE+'inputs/payments.csv': '5fbb26210a45427d7a6560cfab3a362a08e4067f27cd03695f211a51c47ffc25',
    CASE+'inputs/manual.md': 'bb7f4ca6fdc759af1f480702b3a3b12e17e9293b0d38a1dbfbbc8ffc1e572d2c',
    CASE+'inputs/merchant_data.json': 'f158e834de27ee8407e99d9c32da690357981d2770958fd302a9bb79ced83581',
    CASE+'truth.json': '9e6e395fc7b0e5cf60238b8c3ab30fdaa399422fc047f554f0198488156e46d8',
    RUN+'trace.public-derived.jsonl': 'cbbfa329c91509e704f11b47fa0c6cddb0a8ca6bd51aacb00fff1134fc5a81ab',
    RUN+'artifacts/answers.jsonl': '5c71f55a5f1a0500587bd61a8955588288011e50dac1c12d1b813ba672d70c89',
    RUN+'checker.stdout.json': 'c9d8b3432b9db19ed99e8c52a4079597bdcec875f42f9848c4c274cb5ac20b17',
    RUN+'derivation.json': 'cf7a85d78131383dab13b5344a85f4dddc55ed8ceacbeebd6540db4a8844a882',
}
FIELDS = ('ID card_scheme account_type capture_delay monthly_fraud_level monthly_volume '
          'merchant_category_code is_credit aci fixed_amount rate intracountry').split()
CSV_FIELDS = ('psp_reference,merchant,card_scheme,year,hour_of_day,minute_of_hour,day_of_year,'
              'is_credit,eur_amount,ip_country,issuing_country,device_type,ip_address,email_address,'
              'card_number,shopper_interaction,card_bin,has_fraudulent_dispute,is_refused_by_adyen,'
              'aci,acquirer_country').split(',')
MATCH_FIELDS = [x for x in FIELDS if x not in ('ID', 'fixed_amount', 'rate')]
DYNAMIC = {'capture_delay', 'monthly_volume', 'monthly_fraud_level'}
TASKS = ['5', '49', '70', '1273', '1305', '1464', '1681', '1753', '1871', '2697']
MERCHANT = 'Belles_cookbook_store'


class EvidenceError(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise EvidenceError(message)


def fields(obj, names):
    need(type(obj) is dict and set(obj) == set(names), 'missing/extra fields')


def unique_pairs(pairs):
    out = {}
    for key, value in pairs:
        need(key not in out, 'duplicate JSON key: '+key)
        out[key] = value
    return out


def reject_constant(value):
    raise EvidenceError('non-finite JSON number: '+value)


def finite_tree(obj):
    if type(obj) is Decimal:
        need(obj.is_finite(), 'non-finite Decimal')
    elif type(obj) is float:
        raise EvidenceError('binary float not accepted')
    elif type(obj) is dict:
        for value in obj.values():
            finite_tree(value)
    elif type(obj) is list:
        for value in obj:
            finite_tree(value)


def parse_json(text):
    obj = json.loads(text, object_pairs_hook=unique_pairs, parse_float=D,
                     parse_constant=reject_constant)
    finite_tree(obj)
    return obj


def json_lines(text):
    lines = text.splitlines()
    need(lines and all(lines), 'blank JSONL line')
    return [parse_json(x) for x in lines]


def decimal_text(text):
    need(type(text) is str and re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?', text),
         'invalid decimal text')
    value = D(text)
    need(value.is_finite(), 'non-finite decimal text')
    return value


def csv_bool(text):
    need(type(text) is str and text in ('True', 'False'), 'invalid CSV boolean')
    return text == 'True'


def csv_int(text, low, high):
    need(type(text) is str and re.fullmatch(r'[0-9]+', text), 'invalid CSV integer')
    value = int(text)
    need(low <= value <= high, 'CSV integer out of range')
    return value


def validate_rules(rules):
    need(type(rules) is list and rules, 'rules must be nonempty list')
    seen = set()
    for rule in rules:
        fields(rule, FIELDS)
        n = rule['ID']
        need(type(n) is int and n > 0 and n not in seen, 'invalid/duplicate rule ID')
        seen.add(n)
        need(type(rule['card_scheme']) is str and bool(rule['card_scheme']), 'scheme type')
        for key, typ in [('account_type', str), ('aci', str), ('merchant_category_code', int)]:
            val = rule[key]
            need(val is None or (type(val) is list and all(type(x) is typ for x in val)),
                 'rule list type: '+key)
            if val is not None:
                need(len(val) == len(set(val)), 'duplicate rule restriction')
        for key, allowed in [
            ('capture_delay', {'<3', '3-5', '>5', 'manual', 'immediate'}),
            ('monthly_volume', {'<100k', '100k-1m', '1m-5m', '>5m'}),
            ('monthly_fraud_level', {'<7.2%', '7.2%-7.7%', '7.7%-8.3%', '>8.3%'})]:
            need(rule[key] is None or (type(rule[key]) is str and rule[key] in allowed),
                 'unknown rule bucket: '+key)
        need(rule['is_credit'] is None or type(rule['is_credit']) is bool, 'credit type')
        v = rule['intracountry']
        need(v is None or (type(v) is Decimal and v.is_finite() and v in (D(0), D(1))),
             'intracountry must be null or numeric 0/1')
        need(type(rule['rate']) is int and rule['rate'] >= 0, 'rate integer type')
        v = rule['fixed_amount']
        need(type(v) is Decimal and v.is_finite() and v >= 0, 'fixed amount finite type')
    return {r['ID']: r for r in rules}


def validate_merchants(merchants):
    need(type(merchants) is list and merchants, 'merchant list type')
    seen = {}
    for m in merchants:
        fields(m, ['merchant', 'capture_delay', 'acquirer', 'merchant_category_code', 'account_type'])
        name = m['merchant']
        need(type(name) is str and name and name not in seen, 'duplicate/invalid merchant')
        need(type(m['capture_delay']) is str and (m['capture_delay'] in ('manual', 'immediate')
             or re.fullmatch(r'[0-9]+', m['capture_delay'])), 'capture delay type')
        need(type(m['merchant_category_code']) is int, 'MCC type')
        need(type(m['account_type']) is str and len(m['account_type']) == 1
             and m['account_type'] in 'RDHFSO', 'account type')
        need(type(m['acquirer']) is list and all(type(x) is str for x in m['acquirer']), 'acquirer type')
        seen[name] = m
    return seen


def payments(text, merchant_names):
    reader = csv.DictReader(io.StringIO(text, newline=''), strict=True)
    need(reader.fieldnames == CSV_FIELDS, 'CSV header mismatch')
    seen = set()
    for line, row in enumerate(reader, 2):
        fields(row, CSV_FIELDS)
        need(all(type(v) is str for v in row.values()), 'CSV row width mismatch')
        ref = row['psp_reference']
        need(re.fullmatch(r'[0-9]+', ref) and ref not in seen, 'duplicate/invalid payment ID')
        seen.add(ref)
        need(row['merchant'] in merchant_names, 'unknown merchant')
        year = csv_int(row['year'], 1, 9999)
        day = csv_int(row['day_of_year'], 1, 366 if calendar.isleap(year) else 365)
        csv_int(row['hour_of_day'], 0, 23)
        csv_int(row['minute_of_hour'], 0, 59)
        csv_int(row['card_bin'], 0, 99999999)
        for k in ('is_credit', 'has_fraudulent_dispute', 'is_refused_by_adyen'):
            csv_bool(row[k])
        amount = decimal_text(row['eur_amount'])
        need(amount >= 0 and amount == amount.quantize(D('.01')), 'amount not nonnegative cents')
        need(row['aci'] in list('ABCDEFG') and len(row['aci']) == 1, 'invalid ACI')
        need(row['card_scheme'] in {'NexPay', 'GlobalCard', 'SwiftCharge', 'TransactPlus'}, 'unknown scheme')
        for k in ('ip_country', 'issuing_country', 'acquirer_country'):
            need(re.fullmatch(r'[A-Z]{2}', row[k]), 'country type')
        row = dict(row, _line=line, _amount=amount, _credit=csv_bool(row['is_credit']),
                   _date=dt.date(year, 1, 1)+dt.timedelta(days=day-1))
        yield row


def context(merchant, total, fraud):
    need(total > 0 and D(0) <= fraud <= total, 'monthly volume/fraud invalid')
    delay = merchant['capture_delay']
    if delay not in ('immediate', 'manual'):
        n = int(delay)
        delay = '<3' if n < 3 else '3-5' if n <= 5 else '>5'
    volume = '<100k' if total < 100000 else '100k-1m' if total <= 1000000 else '1m-5m' if total <= 5000000 else '>5m'
    # Cross multiplication avoids rounding a fraud ratio into a different bucket.
    fraud_level = ('<7.2%' if fraud*100 < total*D('7.2') else
                   '7.2%-7.7%' if fraud*100 < total*D('7.7') else
                   '7.7%-8.3%' if fraud*100 < total*D('8.3') else '>8.3%')
    return {'capture_delay': delay, 'monthly_volume': volume, 'monthly_fraud_level': fraud_level}


def restrictions(merchant, row, ctx):
    return dict(ctx, card_scheme=row['card_scheme'], account_type=merchant['account_type'],
                merchant_category_code=merchant['merchant_category_code'], is_credit=row['_credit'],
                aci=row['aci'], intracountry=D(int(row['issuing_country'] == row['acquirer_country'])))


def accepts(restriction, value, empty_policy):
    need(empty_policy in ('wildcard', 'reject', 'unknown'), 'unknown empty policy')
    if restriction is None:
        return True
    if type(restriction) is list:
        if restriction:
            return value in restriction
        if empty_policy == 'unknown':
            return None
        return empty_policy == 'wildcard'
    return restriction == value


def matches(rule, values, empty_policy='wildcard', keys=MATCH_FIELDS):
    answers = [accepts(rule[k], values[k], empty_policy) for k in keys]
    if False in answers:
        return False
    return None if None in answers else True


def local_deltas(rows, old_rate, new_rate):
    need(type(old_rate) is int and type(new_rate) is int, 'integer basis-point rate required')
    total = D(0)
    weighted = D(0)
    for r in rows:
        need(type(r['denominator']) is int and r['denominator'] > 0, 'invalid denominator')
        a = decimal_text(r['amount_eur'])
        total += a
        weighted += a / r['denominator']
    factor = D(new_rate-old_rate)/10000
    return total, factor*total, factor*weighted


def analyze_inputs(rules, merchants, payment_text):
    by_id = validate_rules(rules)
    profiles = validate_merchants(merchants)
    need(384 in by_id and MERCHANT in profiles, 'target absent')
    m, target = profiles[MERCHANT], by_id[384]
    january = []
    count = 0
    for row in payments(payment_text, profiles):
        count += 1
        if row['merchant'] == MERCHANT and row['_date'].year == 2023 and row['_date'].month == 1:
            january.append(row)
    total = sum((r['_amount'] for r in january), D(0))
    fraud = sum((r['_amount'] for r in january if csv_bool(r['has_fraudulent_dispute'])), D(0))
    ctx = context(m, total, fraud)
    out = []
    remaining = set()
    reject_policy_support = 0
    unknown_policy_support = 0
    # All 1000 rules are enumerated for each target-supported payment.
    # Static-only candidates expose additional exclusions by measured month/delay context.
    for row in january:
        values = restrictions(m, row, ctx)
        if matches(target, values, 'reject') is True:
            reject_policy_support += 1
        if matches(target, values, 'unknown') is None:
            unknown_policy_support += 1
        if matches(target, values) is not True:
            continue
        ids = sorted(r['ID'] for r in rules if matches(r, values) is True)
        static_ids = sorted(r['ID'] for r in rules if matches(r, values, keys=[k for k in MATCH_FIELDS if k not in DYNAMIC]) is True)
        remaining.update(static_ids)
        excluded = {str(r['ID']): [k for k in DYNAMIC if accepts(r[k], values[k], 'wildcard') is False]
                    for r in rules if r['ID'] in static_ids and r['ID'] not in ids}
        out.append({'csv_line': row['_line'], 'day_of_year': int(row['day_of_year']),
                    'amount_eur': format(row['_amount'], '.2f'), 'aci': row['aci'],
                    'matching_rule_ids': ids, 'static_candidate_ids': static_ids,
                    'excluded_by_context': {k: sorted(v) for k, v in excluded.items()},
                    'denominator': len(ids)})
    amount, delta_sum, delta_mean = local_deltas(out, target['rate'], 1)
    groups = []
    for n in sorted({r['denominator'] for r in out}):
        sub = [r for r in out if r['denominator'] == n]
        groups.append({'denominator': n, 'count': len(sub),
                       'amount_eur': format(sum((D(r['amount_eur']) for r in sub), D(0)), '.2f')})
    return {'payment_rows_validated': count, 'fee_rules_enumerated_per_payment': len(rules),
            'january_payment_count': len(january), 'january_volume_eur': str(total),
            'january_fraud_volume_eur': str(fraud), 'context': ctx,
            'relevant_rules': [by_id[x] for x in sorted(remaining)],
            'empty_list_semantics': 'unknown; wildcard is a conditional reconstruction of the visible W path',
            'empty_reject_target_support_count': reject_policy_support,
            'empty_unknown_target_support_count': unknown_policy_support,
            'affected_count': len(out), 'affected_amount_eur': format(amount, '.2f'),
            'groups': groups, 'payments': out, 'delta_sum_eur': str(delta_sum),
            'delta_mean_eur': str(delta_mean), 'mean_minus_sum_eur': str(delta_mean-delta_sum)}


def validate_task_rows(rows, keys):
    need(type(rows) is list and len(rows) == 10, 'expected ten tasks')
    ids = []
    for row in rows:
        fields(row, keys)
        need(all(type(v) is str for v in row.values()), 'task values must be strings')
        ids.append(row['task_id'])
    need(ids == TASKS, 'task IDs duplicate/missing/reordered')


def bind_evidence(src, analysis):
    questions = json_lines(src[CASE+'inputs/questions.jsonl'])
    validate_task_rows(questions, ['task_id', 'question', 'guidelines', 'level'])
    q = questions[8]
    need(q['question'] == 'In January 2023 what delta would Belles_cookbook_store pay if the relative fee of the fee with ID=384 changed to 1?', 'question mismatch')
    answers = json_lines(src[RUN+'artifacts/answers.jsonl'])
    validate_task_rows(answers, ['task_id', 'answer'])
    answer = answers[8]['answer']
    need(decimal_text(answer) == D(analysis['delta_mean_eur']), 'answer not reconstructed mean')
    trace = json_lines(src[RUN+'trace.public-derived.jsonl'])
    need(all('id' in x or x.get('type') == 'file-history-snapshot' for x in trace), 'trace ID absent')
    ids = [x['id'] for x in trace if 'id' in x]
    need(all(type(x) is str for x in ids) and len(ids) == len(set(ids)), 'trace IDs invalid/duplicate')
    call, result, reasoning = trace[52:55]
    write, receipt = trace[64:66]
    for a, b in zip(trace[53:68], trace[54:69]):
        need(b['parentId'] == a['id'], 'trace54→69 parent chain')
    need(call['type'] == 'function_call' and call['name'] == 'Bash', 'trace53 type')
    need(result['parentId'] == call['id'] and result['callId'] == call['callId']
         and result['type'] == 'function_call_result' and result['status'] == 'completed', 'trace53→54 link')
    need(reasoning['parentId'] == result['id'] and reasoning['type'] == 'reasoning', 'trace54→55 link')
    need(receipt['parentId'] == write['id'] and write['type'] == 'function_call'
         and receipt['type'] == 'function_call_result' and write['callId'] == receipt['callId']
         and receipt['status'] == 'completed', 'trace65→66 write link')
    text = result['output']['text']
    for token in ['s+=sum(vals)/len(vals)', 'delta exact -0.8743215', 'base 409.68193291666665 new 408.80761141666665', 'Exit Code: 0']:
        need(token in text, 'trace54 token absent: '+token)
    reasoning_text = '\n'.join(x['text'] for x in reasoning['rawContent'] if x['type'] == 'reasoning_text')
    for token in ['avg model', 'sum model', '0.948103', '-0.8743215']:
        need(token in reasoning_text, 'trace55 choice token absent')
    write_text = json.dumps(write['arguments'], ensure_ascii=False)
    need('1871' in write_text and '-0.8743215' in write_text and 'answers.jsonl' in write_text,
         'submission trace not bound to answer artifact')
    truth = parse_json(src[CASE+'truth.json'])
    gold = truth['gold']['1871']
    decimal_text(gold)
    old = parse_json(src[RUN+'checker.stdout.json'])
    modes = {}
    for mode in ('official_compat', 'strict_contract'):
        checks = old[mode]['checks']
        seen = [x['id'] for x in checks]
        need(all(type(x) is str for x in seen) and len(seen) == len(set(seen)), 'duplicate/invalid receipt check ID')
        need(seen == ['answers_format', 'input_integrity']+['q'+x for x in TASKS], 'receipt IDs missing/extra/reordered')
        check = [x for x in checks if x['id'] == 'q1871']
        need(len(check) == 1, 'q1871 receipt absent')
        c = check[0]
        fields(c, ['id', 'pass', 'note', 'task_id', 'level'])
        need(c['task_id'] == '1871' and c['level'] == 'hard' and c['pass'] is False
             and c['note'] == "pred='"+answer+"' ｜ gold='"+gold+"'", 'old receipt content mismatch')
        need(type(old[mode]['weighted']) is Decimal and old[mode]['weighted'] == D(60)
             and type(old[mode]['reward']) is int and old[mode]['reward'] == 0, 'old score mismatch')
        modes[mode] = {'q1871_pass': False, 'weighted': '60.0', 'reward': 0}
    derivation = parse_json(src[RUN+'derivation.json'])
    need(derivation['derived_trace_sha256'] == SOURCES[RUN+'trace.public-derived.jsonl']
         and derivation['line_count'] == len(trace) == 73, 'derivation trace binding')
    for n in (54, 55, 65, 66, 69):
        entries = [x for x in derivation['line_mapping'] if x['derived_line'] == n]
        need(len(entries) == 1 and entries[0]['original_line'] == n, 'derivation mapping')
        line = src[RUN+'trace.public-derived.jsonl'].splitlines()[n-1]
        need(hashlib.sha256(line.encode()).hexdigest() == entries[0]['derived_line_sha256'], 'derived line hash')
    need('1871 | -0.8743215 | len 10' in trace[68]['output']['text'], 'trace69 answer confirmation')
    return {'trace_lines': [53, 54, 55, 65, 66, 69], 'trace54_id': result['id'],
            'trace55_parent_id': reasoning['parentId'], 'answer_line': 9, 'answer': answer,
            'gold': gold, 'gold_minus_sum_eur': str(D(gold)-D(analysis['delta_sum_eur'])),
            'historical_receipts': modes, 'aggregation_norm': None, 'harness_cause': None,
            'historical_input_identity_independently_authenticated': False}


def json_safe(obj):
    if type(obj) is Decimal:
        return str(obj)
    if type(obj) is list:
        return [json_safe(x) for x in obj]
    if type(obj) is dict:
        return {k: json_safe(v) for k, v in obj.items()}
    return obj


def recompute(root=ROOT):
    src = {}
    for path, digest in SOURCES.items():
        data = (root/path).read_bytes()
        need(hashlib.sha256(data).hexdigest() == digest, 'source hash mismatch: '+path)
        src[path] = data.decode('utf-8')
    with localcontext() as ctx:
        ctx.prec = 50
        analysis = analyze_inputs(parse_json(src[CASE+'inputs/fees.json']),
                                  parse_json(src[CASE+'inputs/merchant_data.json']),
                                  src[CASE+'inputs/payments.csv'])
        binding = bind_evidence(src, analysis)
    return json_safe({'schema': 'q1871-overlap-posthoc-v1', 'sources_sha256': SOURCES,
                      'analysis': analysis, 'evidence_binding': binding})


def verify_result(expected, actual):
    # Canonical JSON comparison is type-sensitive (unlike True == 1 in Python).
    finite_tree(expected)
    need(json.dumps(expected, ensure_ascii=False, sort_keys=True) ==
         json.dumps(actual, ensure_ascii=False, sort_keys=True), 'result does not match independent recomputation')


def main():
    result = recompute()
    expected = parse_json((HERE/'result.json').read_text(encoding='utf-8'))
    verify_result(expected, result)
    a = result['analysis']
    print(f"PASS: {len(SOURCES)} source hashes; {a['payment_rows_validated']} payments; "
          f"{a['fee_rules_enumerated_per_payment']} rules × {a['affected_count']} affected payments; "
          'exact deltas and trace→answer→old receipts')
    print(f"sum={a['delta_sum_eur']}; mean={a['delta_mean_eur']}; "
          f"mean-minus-sum={a['mean_minus_sum_eur']}; aggregation norm and Harness cause remain unknown")


if __name__ == '__main__':
    main()
