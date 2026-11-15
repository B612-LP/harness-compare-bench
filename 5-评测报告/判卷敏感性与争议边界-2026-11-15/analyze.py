#!/usr/bin/env python3
"""Exploratory offline re-analysis; reads only public case and frozen receipts."""
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import sys

# Imports below must not create __pycache__ in the historical source directories.
sys.dont_write_bytecode = True

def require(condition, message):
    if not condition:
        raise ValueError(message)

require(len(sys.argv) == 3, 'usage: analyze.py REPO_ROOT NEW_OUTPUT_JSON')
root = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2])
case = root / '2-用例/dabstep-payments-10'
original = root / '5-评测报告/派生分析-q2697gold复算-20261111/collect-q2697-gold-recheck.py'
checker = case / 'checker.py'

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

m = load('old_q2697', original)
s = load('case_checker', checker)
fees, txs, month, merch, q, truth = m.load_case(str(case))
ctx = m.merchant_context(txs, month, merch)
gold = truth['gold']['2697']
require(gold == 'E:13.57', 'unexpected q2697 gold')
axes = itertools.product(['<3','immediate','only_null'], ['min','max','first_by_ID'], ['amount','count','none_only'], itertools.product([True,False], repeat=3))
rows = []
for cap, multi, fraudmode, flags in axes:
    fl = dict(zip(('at_empty_wild','mcc_empty_wild','aci_empty_wild'),flags))
    _, band = m.fraud_band_mode(fraudmode,ctx)
    vals = {a: round(m.aci_total(fees,txs,a,cap,ctx,fl,band,multi),2) for a in 'ABCDEF'}
    # No claim that this tie-break is uniquely required; it matches old code.
    winner = min(vals, key=vals.get)
    estr = f"E:{vals['E']:.2f}"
    wstr = f"{winner}:{vals[winner]:.2f}"
    rows.append({'capture':cap,'multi':multi,'fraud_mode':fraudmode,'flags':fl,
                 'fees':vals,'selected_aci_old_tie_break':winner,
                 'E_string':estr,'E_compat':s.question_scorer(estr,gold),
                 'winner_string':wstr,'winner_compat':s.question_scorer(wstr,gold),
                 'all_candidate_compat':{a:s.question_scorer(f'{a}:{v:.2f}',gold) for a,v in vals.items()}})
require(len(rows)==216, 'unexpected number of parameter combinations')
receipts={}
for product in ('codex','dsh'):
    path=root / f'3-表现现场/r1030-formal-a1/runs/{product}__dabstep-payments-10/checker.stdout.json'
    data=json.loads(path.read_text())
    require(data['checker_version'] == '0.2' and data['n_tasks']==10 and data['threshold']==0.8,
            f'{product}: unexpected checker version, count or threshold')
    expected_ids = {'q' + k for k in truth['gold']}
    require(len(expected_ids)==10, 'truth must have ten distinct question IDs')
    require(data['gates'] == {'answers_format': True, 'input_integrity': True},
            f'{product}: original gates are not both true')
    modes={}
    mode_checks = {}
    for mode in ('official_compat','strict_contract'):
        x=data[mode]
        entries = x['checks']
        ids = [c['id'] for c in entries]
        require(len(ids)==len(set(ids)) and set(ids)==expected_ids | set(data['gates']),
                f'{product}/{mode}: duplicate, missing, or unexpected checks')
        require(all(type(c['pass']) is bool for c in entries), f'{product}/{mode}: nonboolean check')
        checks={c['id']:c['pass'] for c in entries}
        require({k:checks[k] for k in data['gates']} == data['gates'], f'{product}/{mode}: gate mismatch')
        require(sum(checks[k] for k in expected_ids)==x['correct'], f'{product}/{mode}: count mismatch')
        require(not checks['q2697'] and x['reward']==0, f'{product}/{mode}: unexpected baseline')
        mode_checks[mode] = checks
        n=x['correct']; no2697=n/9; hypothetical=(n+1)/10
        modes[mode]={'correct':n,'out_of':10,'q1871_pass':checks['q1871'],
                     'q2697_pass':checks['q2697'],'original_reward':x['reward'],
                     'omit_q2697_rate':no2697,'omit_rate_threshold_pass':no2697>=.8,
                     'hypothetical_q2697_pass_rate':hypothetical,
                     'hypothetical_rate_threshold_pass':hypothetical>=.8}
    differing = {k for k in expected_ids if mode_checks['official_compat'][k] != mode_checks['strict_contract'][k]}
    require(differing == ({'q1871'} if product == 'codex' else set()),
            f'{product}: unexpected difference between the two score tracks')
    require(data['reward'] == data['official_compat']['reward'] and data['correct'] == data['official_compat']['correct'],
            f'{product}: top-level and compatibility result disagree')
    receipts[product]={'sha256':digest(path),'gates':data['gates'],'modes':modes}
probe={p:s.question_scorer(p,gold) for p in ['E:13.57','NexPay:13.57','E:-13.57','E:13.6','E:16.63','B:54.21']}
require(all(probe[x] for x in ['E:13.57','NexPay:13.57','E:-13.57','E:13.6']), 'expected compatibility positive probe failed')
require(not probe['E:16.63'] and not probe['B:54.21'], 'expected compatibility negative probe passed')
result={'nature':'post-hoc offline sensitivity, not rescoring',
        'inputs_sha256':{'old_calculator':digest(original),'checker':digest(checker),'truth':digest(case/'truth.json'),'fees':digest(case/'inputs/fees.json'),'payments':digest(case/'inputs/payments.csv'),'merchant_data':digest(case/'inputs/merchant_data.json'),'questions':digest(case/'inputs/questions.jsonl')},
        'limitations':['unmatched treated as zero in old calculator; not evidence zero cost is valid','two-decimal formatted strings only; 216 parameter combinations, not independent products or all possible answers','first_by_ID delegates to old implementation vals[0] and assumes source order','model answers do not establish underlying algorithm'],
        'case_count':len(rows),'e_compat_count':sum(x['E_compat'] for x in rows),
        'winner_compat_count':sum(x['winner_compat'] for x in rows),
        'all_candidate_compat_count':sum(sum(x['all_candidate_compat'].values()) for x in rows),
        'e_exact_count':sum(abs(x['fees']['E']-13.57)<.005 for x in rows),
        'winner_examples_compat':[x for x in rows if x['winner_compat']][:5],
        'min_abs_E_gap':min(abs(x['fees']['E']-13.57) for x in rows),
        'min_abs_any_candidate_gap':min(abs(v-13.57) for x in rows for v in x['fees'].values()),
        'probe':probe,'receipts':receipts,'rows':rows}
with out.open('x',encoding='utf8') as f:
    json.dump(result,f,ensure_ascii=False,indent=2); f.write('\n')
print(json.dumps({k:result[k] for k in ['case_count','e_compat_count','winner_compat_count','e_exact_count','min_abs_E_gap','min_abs_any_candidate_gap','probe','receipts']},ensure_ascii=False,indent=2))
