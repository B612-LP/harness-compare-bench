#!/usr/bin/env python3
"""Read-only L4 aggregation; never invokes a model, product, checker or admission gate.

Original producer values, count-derived reference values and frozen admission results
remain separate. Output is exclusive; historical evidence is never rewritten.
"""
from __future__ import annotations
import argparse
import datetime as dt
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DESIGN = REPO / '1-评测方案/自动循环L4-2026-10-29'
JUDGE = REPO / '5-评测报告/L4独立验收-2026-10-29/final-verify-receipt.json'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def reference(path):
    return {'path': str(path.relative_to(REPO)), 'sha256': digest(path),
            'bytes': path.stat().st_size}


def fixed8(value):
    return format(Decimal(str(value)).quantize(Decimal('0.00000001')), '.8f')


def field_state(obj, keys):
    for key in keys:
        if not isinstance(obj, dict) or key not in obj:
            return {'state': 'missing'}
        obj = obj[key]
    if obj is None:
        return {'state': 'null'}
    if type(obj) in (int, float) and obj >= 0:
        return {'state': 'zero' if obj == 0 else 'positive', 'value': obj}
    return {'state': 'other', 'value_type': type(obj).__name__}


def freeze_judge_source():
    """Archive the exact independent receipt version consumed by this analysis."""
    raw = JUDGE.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    folder = Path(__file__).resolve().parent / 'source-snapshots'
    folder.mkdir(exist_ok=True)
    snapshot = folder / ('judge-final-' + sha + '.json')
    if snapshot.exists():
        assert snapshot.read_bytes() == raw
    else:
        with snapshot.open('xb') as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
    return snapshot


def build():
    judge_source = freeze_judge_source()
    plan = load(DESIGN / 'plan.json')
    contract = load(DESIGN / 'contract.json')
    binding = load(DESIGN / 'runtime-binding.json')
    for name in ('plan', 'contract'):
        assert digest(DESIGN / (name + '.json')) == binding[name + '_sha256']
    verification = load(judge_source)
    decisions = {r['slot_id']: r for r in verification['rows']}
    planned_ids = [s['slot_id'] for s in plan['product_slots']]
    assert len(decisions) == len(verification['rows']) == len(planned_ids)
    assert set(decisions) == set(planned_ids)
    products = []
    for slot in plan['product_slots']:
        folder = REPO / slot['evidence_dir']
        path = folder / 'meta.json'
        decision = decisions[slot['slot_id']]
        admission = decision.get('canonical_gate') or decision.get('gate_admission_independent') or {}
        formal = admission.get('formal_admission')
        assert type(formal) is bool, ('missing canonical admission', slot['slot_id'])
        row = {k: slot[k] for k in ('slot_id', 'product', 'case', 'rep', 'stratum', 'order')}
        row.update({'canonical_formal': formal, 'canonical_fails': admission.get('fails'),
                    'canonical_block_reason': admission.get('block_reason'),
                    'canonical_accounting': admission.get('accounting'),
                    'admission_source': reference(judge_source)})
        if path.is_file():
            m = load(path)
            assert m['slot_id'] == slot['slot_id']
            assert m['preregistration_commit'] == binding['execution_seal_commit']
            assert m['registered_at'] == binding['registered_at']
            assert dt.datetime.fromisoformat(m['started_at']) > dt.datetime.fromisoformat(binding['registered_at'])
            j = m.get('judge') or {}
            correct, possible = j.get('correct'), contract['denominators'][slot['case']]
            ratio = None
            if type(correct) is int and 0 <= correct <= possible:
                ratio = fixed8(Decimal(100) * Decimal(correct) / Decimal(possible))
            row.update({'record_state': 'executed', 'producer_status': m.get('status'),
                        'producer_reported_weighted': m.get('weighted'),
                        'producer_reward_do_not_treat_as_correct_count': m.get('reward'),
                        'correct_count_from_judge_payload': correct, 'contract_denominator': possible,
                        'count_fraction_reference_not_a_regrade': ratio,
                        'started_at': m.get('started_at'), 'finished_at': m.get('finished_at'),
                        'duration_s': m.get('duration_s'), 'original_metadata': reference(path)})
        else:
            path = folder / 'notexecuted.json'
            m = load(path)
            assert m['slot_id'] == slot['slot_id']
            row.update({'record_state': 'not_executed', 'reason': m.get('reason'),
                        'producer_reported_weighted': None, 'original_notexec_record': reference(path)})
        products.append(row)
    groups = []
    for product in ('codex', 'dsh'):
        for case in sorted({s['case'] for s in plan['product_slots'] if s['product'] == product}):
            rows = sorted((r for r in products if r['product'] == product and r['case'] == case), key=lambda r: r['rep'])
            assert [r['rep'] for r in rows] == [1, 2, 3]
            values = [Decimal(str(r['producer_reported_weighted'])) for r in rows]
            groups.append({'product': product, 'case': case, 'n_planned': len(rows),
                           'reported_scores_in_rep_order': [fixed8(v) for v in values],
                           'observed_range_points': fixed8(max(values) - min(values)),
                           'duration_s_in_rep_order': [r['duration_s'] for r in rows],
                           'not_population_variance_or_runner_generation_effect': True})
    reads = {'responses': ('input_tokens_details', 'cached_tokens'),
             'anthropic-messages': ('cache_read_input_tokens',),
             'chat-completions': ('prompt_cache_hit_tokens',)}
    cache = []
    for slot in plan['probe_slots']:
        folder = REPO / slot['evidence_dir']
        body, transport = folder / 'response.body.raw', load(folder / 'transport.json')
        raw = load(body)
        usage = raw.get('usage', {})
        row = {k: slot[k] for k in ('slot_id', 'protocol', 'block', 'condition', 'order')}
        row.update({'http_status': transport.get('http_status'), 'raw_source': reference(body),
                    'selected_cache_read_path': '/usage/' + '/'.join(reads[slot['protocol']]),
                    'cache_read': field_state(usage, reads[slot['protocol']]),
                    'creation_named_field': field_state(usage, ('cache_creation_input_tokens',))})
        if slot['protocol'] == 'chat-completions':
            row['cached_tokens_alias'] = field_state(usage, ('prompt_tokens_details', 'cached_tokens'))
            row['alias_values_match_observed'] = row['cached_tokens_alias'] == row['cache_read']
        cache.append(row)
    drift = load(DESIGN / 'EXECUTION-RULINGS.json')
    return {'artifact_class': 'offline_observation_aggregation',
            'generated_at': dt.datetime.now().astimezone().isoformat(timespec='seconds'),
            'execution_binding': binding, 'source_plan': reference(DESIGN / 'plan.json'),
            'source_final_judge_receipt': reference(judge_source),
            'counts': {'planned_product_records': len(products),
                       'executed_product_records': sum(r['record_state'] == 'executed' for r in products),
                       'not_executed_product_records': sum(r['record_state'] == 'not_executed' for r in products),
                       'canonical_formal_true': verification['summary']['formal_true'],
                       'probe_http_records': len(cache),
                       'fresh_repeat_pairs': len({(r['protocol'], r['block']) for r in cache})},
            'product_records': products, 'cli_descriptive_ranges': groups, 'cache_records': cache,
            'limits': ['No model/product/checker invocation by this program.',
                       'Record coverage is not metadata-contract compliance or formal admission.',
                       'Count fraction is a diagnostic reference, not a replacement of original score/guards.',
                       'No five-case total, normalization of missing cases, causal attribution, ranking or monetary inference.',
                       'One selected read counter per response; chat aliases are not added together.'],
            'live_doc_drift': drift['live_doc_drift'],
            'live_doc_drift_source': reference(DESIGN / 'EXECUTION-RULINGS.json')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    result = build()
    with args.out.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    print(json.dumps({'output': str(args.out), 'sha256': digest(args.out), 'counts': result['counts']}, ensure_ascii=False))
