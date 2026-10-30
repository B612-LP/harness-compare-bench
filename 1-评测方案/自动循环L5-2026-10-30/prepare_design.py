#!/usr/bin/env python3
"""Generate prospective L5 plan/contract without touching model APIs or old artifacts."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
L4_CONTRACT = ROOT / '1-评测方案' / '自动循环L4-2026-10-29' / 'contract.json'


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def create(name, obj):
    with (HERE / name).open('x', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')


def main():
    if any((HERE / p).exists() for p in ('plan.json', 'contract.json')):
        raise SystemExit('Refuse overwrite; design already generated')
    l4c = json.loads(L4_CONTRACT.read_text(encoding='utf-8'))
    cli = [('codex', 'dabstep-payments-10', 1, 1800), ('codex', 'tb-cargo-plan', 1, 2400),
           ('dsh', 'dabstep-payments-10', 1, 1800), ('dsh', 'tb-cargo-plan', 1, 2400)]
    slots = []
    for product, case, rep, timeout in cli:
        sid = 'l5-20261030-cli-%s-%s-r%d' % (product, case, rep)
        slots.append(dict(slot_id=sid, run_id=sid, event_id='event:' + sid,
                          kind='product_run', product=product, case=case, rep=rep,
                          stratum='cli_current_sentinel', order=len(slots)+1,
                          evidence_dir='3-表现现场/l5-20261030-cli/%s/runs/%s' % (product, sid),
                          timeout_s=timeout))
    for case in ('bird-ca-schools-15', 'dabstep-payments-10'):
        cj = json.loads((ROOT / '2-用例' / case / 'case.json').read_text())
        sid = 'l5-20261030-wb-gateway-%s-r1' % case
        slots.append(dict(slot_id=sid, run_id=sid, event_id='event:' + sid,
                          kind='product_run', product='workbuddy', case=case, rep=1,
                          stratum='wb_gateway_delivery', order=len(slots)+1,
                          evidence_dir='3-表现现场/l5-20261030-wb-gateway/runs/' + sid,
                          timeout_s=cj.get('timeout_s', 1800)))
    plan = dict(plan_id='l5-20261030', schema_version=1,
                generated_at=datetime.now().astimezone().isoformat(timespec='seconds'),
                registered_at_source='execution seal E git committer timestamp; exact value in post-seal runtime-binding.json',
                product_slots=slots, probe_slots=[],
                whole_execution_restarts=0, replacements=0, result_driven_extra_samples=0,
                design_scope=dict(
                    purpose='toolchain verifiability repair (L5-1/2/3/4/5/8 + L4 closeout) and formal-admission restoration re-verification',
                    repairs=['R1 emission', 'R2 ws-meta removal', 'R3 dsh capture marker',
                             'R4 gate v2 whitelist', 'R5 cache mapping v2', 'R6 wb readiness wait',
                             'R7 wb frame path + write-once receipts'],
                    discipline=['D1 setsid residual disclosure + post-stop ws double sampling',
                                'D2 raw-precision and canonical-8dp dual statement'],
                    frozen_history='L4 batch and contracts v1/v2/v3 untouched; L4 formal 0/17 permanent'))
    contract = dict(rule_version='l5-20261030-batch-v1', schema_version=1,
                    plan_sha256=None,
                    grading_contract_inheritance='freeze-20261029-v2 checker bytes only; no old table admission',
                    source_config=l4c['source_config'],
                    case_snapshots=l4c['case_snapshots'],
                    checker_sha256=l4c['checker_sha256'],
                    denominators=l4c['denominators'],
                    strata=l4c['strata'],
                    probe_endpoints={}, endpoint_sources={},
                    admission=dict(plan_cardinality=6, probe_cardinality=0,
                                   zero_missing_or_duplicate_slots=True,
                                   registered_at_exact_execution_seal=True,
                                   required_original_evidence=['prompt', 'stdout', 'stderr', 'session', 'checker', 'workspace'],
                                   sha_bytes_recomputed=True,
                                   raw_trace_contamination_review=True,
                                   unknown_not_zero=True,
                                   full_denominator_only=True,
                                   no_cross_route_ranking=True,
                                   emission_fields_required=['inputs_verification.ok', 'judge.checker_sha256',
                                                             'judge.guards_used', 'judge.correct', 'judge.n_tasks',
                                                             'score.checker_sha256', 'score.reported_8dp', 'weighted_8dp']),
                    old_contracts_mutated=False,
                    live_doc_drift=[])
    contract['plan_sha256'] = None  # filled after plan exists
    create('plan.json', plan)
    contract['plan_sha256'] = digest(HERE / 'plan.json')
    create('contract.json', contract)
    print('plan.json slots=%d, contract.json written' % len(slots))


if __name__ == '__main__':
    main()
