#!/usr/bin/env python3
"""Generate prospective L6 plan/contract without touching model APIs or old artifacts.

两阶段（PREREGISTRATION 声明）：
  --plan-only      D 封印前：仅生成 plan.json（单槽 wb-bird）。
  --contract-only  实现完成后、E 封印前：仅生成 contract.json——bird checker_sha256 按
                   当前（修订后）checker 字节现算，其余四 case 与全部判分语义继承 L5
                   contract 不变。write-once：任一目标已存在即拒。
"""
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
L5_CONTRACT = ROOT / '1-评测方案' / '自动循环L5-2026-10-30' / 'contract.json'
BIRD_CASE = 'bird-ca-schools-15'


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def create(name, obj):
    target = HERE / name
    if target.exists():
        raise SystemExit('Refuse overwrite; %s already generated' % name)
    with target.open('x', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')


def build_slots():
    cj = json.loads((ROOT / '2-用例' / BIRD_CASE / 'case.json').read_text())
    sid = 'l6-20261030-wb-gateway-%s-r1' % BIRD_CASE
    return [dict(slot_id=sid, run_id=sid, event_id='event:' + sid,
                 kind='product_run', product='workbuddy', case=BIRD_CASE, rep=1,
                 stratum='wb_gateway_delivery', order=1,
                 evidence_dir='3-表现现场/l6-20261030-wb-gateway/runs/' + sid,
                 timeout_s=cj.get('timeout_s', 1800))]


def plan_only():
    slots = build_slots()
    plan = dict(plan_id='l6-20261030', schema_version=1,
                generated_at=datetime.now().astimezone().isoformat(timespec='seconds'),
                registered_at_source='execution seal E git committer timestamp; exact value in post-seal runtime-binding.json',
                product_slots=slots, probe_slots=[],
                whole_execution_restarts=0, replacements=0, result_driven_extra_samples=0,
                design_scope=dict(
                    purpose='bird checker meta-fields completion (L5-P1) with real rerun formal '
                            're-admission; receipt self-exclusion rule (L5-P3); L5-P2 rides pinned',
                    repairs=['L6-A bird checker n_tasks/guards_used emission (additive only)',
                             'L6-C receipt_check self-reference rule + manifest_receipt generator'],
                    discipline=['single-slot rerun: link-chain validity is the goal, score is not',
                                'history batches frozen; no back-write to L4/L5 conclusions'],
                    frozen_history='L4 formal 0/17 and L5 canonical 5/6 untouched'))
    create('plan.json', plan)
    print('plan.json slots=%d written' % len(slots))


def contract_only():
    l5c = json.loads(L5_CONTRACT.read_text(encoding='utf-8'))
    checker_sha = dict(l5c['checker_sha256'])
    checker_sha[BIRD_CASE] = digest(ROOT / '2-用例' / BIRD_CASE / 'checker.py')
    contract = dict(rule_version='l6-20261030-batch-v1', schema_version=1,
                    plan_sha256=digest(HERE / 'plan.json'),
                    grading_contract_inheritance='L5 l5-20261030-batch-v1 semantics; only bird '
                                                 'checker_sha256 refreshed per PREREGISTRATION L6-A',
                    source_config=l5c['source_config'],
                    case_snapshots=l5c['case_snapshots'],
                    checker_sha256=checker_sha,
                    denominators=l5c['denominators'],
                    strata=l5c['strata'],
                    probe_endpoints={}, endpoint_sources={},
                    admission=dict(plan_cardinality=1, probe_cardinality=0,
                                   zero_missing_or_duplicate_slots=True,
                                   registered_at_exact_execution_seal=True,
                                   required_original_evidence=['prompt', 'stdout', 'stderr', 'session',
                                                               'checker', 'workspace'],
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
    create('contract.json', contract)
    print('contract.json written; bird checker sha=%s' % checker_sha[BIRD_CASE][:16])


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--plan-only', action='store_true')
    g.add_argument('--contract-only', action='store_true')
    main = plan_only if ap.parse_args().plan_only else contract_only
    main()
