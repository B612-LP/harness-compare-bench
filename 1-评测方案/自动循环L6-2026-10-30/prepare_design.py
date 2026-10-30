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


def case_snapshot(case):
    """freeze v2/v3 同款算法（4-打分细则/可信冻结-2026-10-29-v3/freeze.py:69-74）。

    修复记录（F-1，2026-10-30）：首版 --contract-only 只刷新了顶层 checker_sha256 映射，
    漏了继承自 L5 的 case_snapshots 内嵌 per-file pin（checker.py/spec.md/manifest_sha256/
    case_version）——judge 独立验收抓获（L6独立验收 F-1）。本函数自盘面重算并配断言。
    """
    d = ROOT / '2-用例' / case
    fixed = [n for n in ('instruction.md', 'spec.md', 'case.json', 'truth.json',
                         'checker.py', 'trusted_runner.py') if (d / n).is_file()]
    rels = fixed + sorted(p.relative_to(d).as_posix()
                          for p in (d / 'inputs').rglob('*') if p.is_file())
    tree = {rel: hashlib.sha256((d / rel).read_bytes()).hexdigest() for rel in rels}
    sha = hashlib.sha256(json.dumps(tree, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()
    return {'checker.py': tree['checker.py'], 'truth.json': tree['truth.json'],
            'instruction.md': tree['instruction.md'],
            'manifest_sha256': sha,
            'case_version': '%s@sha256:%s' % (case, sha),
            'files': tree}


def contract_only():
    l5c = json.loads(L5_CONTRACT.read_text(encoding='utf-8'))
    checker_sha = dict(l5c['checker_sha256'])
    checker_sha[BIRD_CASE] = digest(ROOT / '2-用例' / BIRD_CASE / 'checker.py')
    # case_snapshots：非 bird 逐字节继承 L5；bird 自盘面按 freeze 算法重算。
    snapshots = dict(l5c['case_snapshots'])
    for case in sorted(l5c['case_snapshots']):
        fresh = case_snapshot(case)
        if case != BIRD_CASE:
            # 算法有效性 + 继承不变断言：未修订 case 的重算必须与 L5 逐字节一致。
            if fresh != l5c['case_snapshots'][case]:
                raise SystemExit('FAIL-CLOSED: 非修订 case 快照重算与 L5 不一致: %s' % case)
        else:
            # 修订面断言：bird 仅 checker.py 与 spec.md 变化；truth/instruction/case.json/
            # inputs 全部与 L5 逐字节一致（判分输入零改动）。
            old = l5c['case_snapshots'][BIRD_CASE]
            changed = {k for k in fresh['files'] if fresh['files'][k] != old['files'].get(k)}
            if changed != {'checker.py', 'spec.md'}:
                raise SystemExit('FAIL-CLOSED: bird 修订面超出声明: %s' % sorted(changed))
            if fresh['checker.py'] != checker_sha[BIRD_CASE]:
                raise SystemExit('FAIL-CLOSED: 快照 checker pin 与 checker_sha256 映射不一致')
            snapshots[BIRD_CASE] = fresh
    contract = dict(rule_version='l6-20261030-batch-v1', schema_version=1,
                    plan_sha256=digest(HERE / 'plan.json'),
                    grading_contract_inheritance='L5 l5-20261030-batch-v1 semantics; only bird '
                                                 'checker_sha256 + case_snapshots refreshed per '
                                                 'PREREGISTRATION L6-A (F-1 fix: snapshots recompute)',
                    source_config=l5c['source_config'],
                    case_snapshots=snapshots,
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
    print('contract.json written; bird checker sha=%s; bird case=%s'
          % (checker_sha[BIRD_CASE][:16], snapshots[BIRD_CASE]['case_version'][-20:]))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--plan-only', action='store_true')
    g.add_argument('--contract-only', action='store_true')
    main = plan_only if ap.parse_args().plan_only else contract_only
    main()
