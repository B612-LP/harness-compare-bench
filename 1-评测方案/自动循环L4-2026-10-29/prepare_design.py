#!/usr/bin/env python3
"""Generate prospective L4 plan/contract without touching model APIs or old artifacts."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CASES = ['bird-ca-schools-15', 'dabstep-payments-10', 'exercism-py-6', 'lcb-recent-hard-4', 'tb-cargo-plan']

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def create(name, obj):
    with (HERE / name).open('x', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')

def main():
    if any((HERE / p).exists() for p in ('plan.json', 'contract.json')):
        raise SystemExit('Refuse overwrite; design already generated')
    slots = []
    for product in ('codex', 'dsh'):
        for rep in (1, 2, 3):
            cases = ['dabstep-payments-10', 'tb-cargo-plan']
            if rep == 2:
                cases.reverse()
            for case in cases:
                sid = 'l4-20261029-cli-%s-%s-r%d' % (product, case, rep)
                slots.append(dict(slot_id=sid, run_id=sid, event_id='event:' + sid,
                                  kind='product_run', product=product, case=case, rep=rep,
                                  stratum='cli_current_sentinel', order=len(slots)+1,
                                  evidence_dir='3-表现现场/l4-20261029-cli/%s/runs/%s' % (product, sid),
                                  timeout_s=1800 if case.startswith('dabstep') else 2400))
    for case in CASES:
        sid = 'l4-20261029-wb-gateway-%s-r1' % case
        cj = json.loads((ROOT / '2-用例' / case / 'case.json').read_text())
        slots.append(dict(slot_id=sid, run_id=sid, event_id='event:' + sid,
                          kind='product_run', product='workbuddy', case=case, rep=1,
                          stratum='wb_gateway_delivery', order=len(slots)+1,
                          evidence_dir='3-表现现场/l4-20261029-wb-gateway/runs/' + sid,
                          timeout_s=cj.get('timeout_s', 1800)))
    probes = []
    for block in (1, 2):
        protocols = ['responses', 'anthropic-messages', 'chat-completions']
        if block == 2:
            protocols.reverse()
        for protocol in protocols:
            for condition in ('fresh', 'repeat', 'nonce-control'):
                sid = 'l4-20261029-cache-%s-b%d-%s' % (protocol, block, condition)
                probes.append(dict(slot_id=sid, run_id=sid, kind='bare_model_probe',
                                   protocol=protocol, block=block, condition=condition,
                                   order=len(probes)+1, timeout_s=120, max_output_tokens=256,
                                   evidence_dir='3-表现现场/l4-20261029-cache/probes/' + sid))
    plan = dict(plan_id='l4-20261029', schema_version=1,
                generated_at=datetime.now().astimezone().isoformat(timespec='seconds'),
                registered_at_source='execution seal E git committer timestamp; exact value in post-seal runtime-binding.json',
                product_slots=slots, probe_slots=probes,
                whole_execution_restarts=0, replacements=0, result_driven_extra_samples=0,
                run_release='lead must explicitly release execution seal E; design seal D does not authorize model calls')
    create('plan.json', plan)
    v2path = ROOT / '4-打分细则/可信冻结-2026-10-29-v2/config.json'
    v2 = json.loads(v2path.read_text())
    snapshots = {c: v2['case_snapshots'][c] for c in CASES}
    actual_checkers = {c: digest(ROOT / '2-用例' / c / 'checker.py') for c in CASES}
    for case in CASES:
        if actual_checkers[case] != snapshots[case]['checker.py']:
            raise SystemExit('frozen checker mismatch: ' + case)
    contract = dict(rule_version='l4-20261029-batch-v1', schema_version=1,
                    plan_sha256=digest(HERE / 'plan.json'),
                    grading_contract_inheritance='freeze-20261029-v2 checker bytes only; no old table admission',
                    source_config={'path':str(v2path.relative_to(ROOT)), 'sha256':digest(v2path)},
                    case_snapshots=snapshots, checker_sha256=actual_checkers,
                    denominators=dict(zip(CASES, [15,10,6,4,27])),
                    strata={'cli_current_sentinel':{'products':['codex','dsh'], 'model':'deepseek-flash', 'effort':'low', 'route_host':'api.deepseek.com', 'ranking':False},
                            'wb_gateway_delivery':{'products':['workbuddy'], 'declared_model_alias':'deepseek-v4.1-flash', 'gateway':'www.workbuddy.cn', 'upstream':'unknown', 'effort':'record actual; unknown allowed only as disclosed product-delivery confound', 'ranking':False}},
                    probe_endpoints={'responses':'https://api.deepseek.com/responses',
                                     'anthropic-messages':'https://api.deepseek.com/anthropic/v1/messages',
                                     'chat-completions':'https://api.deepseek.com/chat/completions'},
                    endpoint_sources={'responses':'3-表现现场/r1022-cbase-deepseekflash/tools/bare_run.py',
                                      'anthropic-messages':'3-表现现场/r20261029-mechanism/runtime-preflight-b0b1de8d/01-transport.json',
                                      'chat-completions':'https://api-docs.deepseek.com/api/create-chat-completion'},
                    admission={'plan_cardinality':17,'probe_cardinality':18,'zero_missing_or_duplicate_slots':True,
                               'registered_at_exact_execution_seal':True,'required_original_evidence':['prompt','stdout','stderr','session','checker','workspace'],
                               'sha_bytes_recomputed':True,'raw_trace_contamination_review':True,
                               'unknown_not_zero':True,'full_denominator_only':True,'no_cross_route_ranking':True,
                               'schema_pass_is_not_admission':True,'retro_exit_code_is_not_admission':True},
                    old_contracts_mutated=False, live_doc_drift=[])
    create('contract.json', contract)
    print(json.dumps({'product_slots':len(slots),'probe_slots':len(probes),
                      'plan_sha256':digest(HERE/'plan.json'),'contract_sha256':digest(HERE/'contract.json')}, ensure_ascii=False))

if __name__ == '__main__':
    main()
