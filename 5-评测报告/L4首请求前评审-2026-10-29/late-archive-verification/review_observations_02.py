#!/usr/bin/env python3
"""Independent read-only audit of fixed observation aggregation; never run builder.
Only exact public evidence references and associated raw files are read. No raw
prompt/trace/response content or credentials is emitted; outputs stay in scope.
"""
import argparse
import copy
import ast
from collections import defaultdict
import datetime as dt
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--snapshot', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    root, snap = a.root.resolve(), a.snapshot.resolve()
    scope = root / '5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification'
    assert a.out.resolve().parent == scope and not a.out.exists()
    baseline = {}
    def read(p):
        p = p.resolve()
        assert p.is_relative_to(root) or p.is_relative_to(snap)
        raw = p.read_bytes()
        baseline.setdefault(str(p), sha(raw))
        return raw
    def load(p):
        return json.loads(read(p))
    checks, findings = [], []
    def check(name, passed, detail=None):
        checks.append({'id': name, 'pass': bool(passed), 'detail': detail})
    def timestamp(s):
        value = dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
        assert value.tzinfo is not None
        return value
    def fixed8(x):
        return format(Decimal(str(x)).quantize(Decimal('0.00000001')), '.8f')
    def state(obj, path):
        for key in path:
            if not isinstance(obj, dict) or key not in obj:
                return {'state': 'missing'}
            obj = obj[key]
        if obj is None:
            return {'state': 'null'}
        if type(obj) in (int, float) and obj >= 0:
            return {'state': 'zero' if obj == 0 else 'positive', 'value': obj}
        return {'state': 'other', 'value_type': type(obj).__name__}
    src, obs = read(snap / 'build_observations.py'), load(snap / 'observations-final-v2.json')
    plan = load(root / '1-评测方案/自动循环L4-2026-10-29/plan.json')
    contract = load(root / '1-评测方案/自动循环L4-2026-10-29/contract.json')
    binding = load(root / '1-评测方案/自动循环L4-2026-10-29/runtime-binding.json')
    check('binding-preserved-exactly', obs['execution_binding'] == binding)
    refs = {}
    def walk(x):
        if isinstance(x, dict):
            if {'path', 'sha256', 'bytes'} <= set(x):
                old = refs.get(x['path'])
                check('same-reference-consistent:' + x['path'], old is None or old == x)
                refs[x['path']] = x
            for v in x.values(): walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
    walk(obs)
    for name, ref in refs.items():
        p = root / name
        assert p.resolve().is_relative_to(root) and not p.is_symlink()
        raw = read(p)
        check('reference-SHA-and-bytes:' + name, sha(raw) == ref['sha256'] and len(raw) == ref['bytes'])
    judge_path = root / obs['source_final_judge_receipt']['path']
    judge = load(judge_path)
    decisions = {r['slot_id']: r for r in judge['rows']}
    products = {r['slot_id']: r for r in obs['product_records']}
    planned = {s['slot_id']: s for s in plan['product_slots']}
    check('all-seventeen-product-slots-exact-unique', len(products) == len(obs['product_records']) == len(planned) == 17 and set(products) == set(planned) == set(decisions))
    missing_reasons, canonical_accounts = [], defaultdict(int)
    raw_product_checks = []
    finish_times = []
    for sid, s in planned.items():
        row, d = products[sid], decisions[sid]
        gate = d.get('canonical_gate') or d.get('gate_admission_independent') or {}
        check('formal-source-exact:' + sid, row['canonical_formal'] is gate.get('formal_admission'))
        check('canonical-three-fields-source-exact:' + sid, row.get('canonical_fails') == gate.get('fails') and row.get('canonical_block_reason') == gate.get('block_reason') and row.get('canonical_accounting') == gate.get('accounting'))
        canonical_accounts[gate.get('accounting', 'not_provided')] += 1
        if not gate.get('fails') and gate.get('block_reason') and row.get('canonical_block_reason') != gate['block_reason']:
            missing_reasons.append({'slot_id': sid, 'source_field': 'block_reason', 'source_value': gate['block_reason'], 'emitted_canonical_fails': row.get('canonical_fails')})
        folder = root / s['evidence_dir']
        mp, np = folder / 'meta.json', folder / 'notexecuted.json'
        check('exactly-one-original-meta-or-notexec:' + sid, mp.is_file() != np.is_file())
        if not mp.is_file():
            m = load(np)
            check('notexec-state-and-no-invented-score:' + sid, row['record_state'] == 'not_executed' and row['producer_reported_weighted'] is None and row['reason'] == m.get('reason'))
            continue
        m = load(mp)
        check('producer-score-status-time-values-exact:' + sid,
              row['record_state'] == 'executed' and row['producer_status'] == m.get('status')
              and row['producer_reported_weighted'] == m.get('weighted')
              and row['producer_reward_do_not_treat_as_correct_count'] == m.get('reward')
              and all(row[k] == m.get(k) for k in ('started_at', 'finished_at', 'duration_s')))
        correct = (m.get('judge') or {}).get('correct')
        possible = contract['denominators'][s['case']]
        ratio = fixed8(Decimal(100) * Decimal(correct) / Decimal(possible)) if type(correct) is int and 0 <= correct <= possible else None
        check('count-diagnostic-not-a-regrade:' + sid, row['correct_count_from_judge_payload'] == correct and row['contract_denominator'] == possible and row['count_fraction_reference_not_a_regrade'] == ratio)
        start, end = timestamp(m['started_at']), timestamp(m['finished_at'])
        finish_times.append(end)
        check('product-time-order-and-duration-rounding:' + sid, timestamp(binding['registered_at']) < start <= end and type(m['duration_s']) in (int, float) and abs((end - start).total_seconds() - m['duration_s']) <= 1.1)
        evp = m.get('evidence_paths') or {}
        for role, default in (('stdout', 'agent.jsonl'), ('stderr', 'agent.stderr.txt'), ('prompt', 'prompt.txt')):
            p = folder / evp.get(role, default)
            raw = read(p)
            matched = sha(raw) == m.get(role + '_sha256')
            if role in ('stdout', 'stderr'):
                matched &= len(raw) == m.get(role + '_bytes')
            raw_product_checks.append({'slot_id': sid, 'role': role, 'path': str(p.relative_to(root)), 'sha256': sha(raw), 'matches_meta': matched})
            check('raw-product-file-SHA:' + sid + ':' + role, matched)
    check('formal-zero-recomputed-from-every-row-and-snapshot', sum(r['canonical_formal'] for r in products.values()) == obs['counts']['canonical_formal_true'] == judge['summary']['formal_true'] == 0)
    check('source-accounting-counts-preserved-as-record-coverage', obs['counts']['executed_product_records'] == 16 and obs['counts']['not_executed_product_records'] == 1 and judge['summary']['accounting'] == {'executed_partial': 16, 'not_executed': 1})
    check('all-rejection-causes-preserved', not missing_reasons, missing_reasons)
    if missing_reasons:
        findings.append({'id': 'lost-block-reason', 'severity': 'fix', 'detail': missing_reasons})
    for group in obs['cli_descriptive_ranges']:
        rows = sorted((r for r in products.values() if r['product'] == group['product'] and r['case'] == group['case']), key=lambda r: r['rep'])
        values = [Decimal(str(r['producer_reported_weighted'])) for r in rows]
        check('descriptive-range:' + group['product'] + ':' + group['case'], [r['rep'] for r in rows] == [1, 2, 3] and group['reported_scores_in_rep_order'] == [fixed8(v) for v in values] and group['observed_range_points'] == fixed8(max(values) - min(values)) and group['duration_s_in_rep_order'] == [r['duration_s'] for r in rows])
    probes = {r['slot_id']: r for r in obs['cache_records']}
    plan_probes = {s['slot_id']: s for s in plan['probe_slots']}
    check('all-eighteen-cache-slots-exact-unique', len(probes) == len(obs['cache_records']) == len(plan_probes) == 18 and set(probes) == set(plan_probes))
    pointers = {'responses': ['input_tokens_details', 'cached_tokens'], 'anthropic-messages': ['cache_read_input_tokens'], 'chat-completions': ['prompt_cache_hit_tokens']}
    pair_groups = defaultdict(dict)
    for sid, s in plan_probes.items():
        row = probes[sid]
        folder = root / s['evidence_dir']
        raw = read(folder / 'response.body.raw')
        parsed, transport, intent = json.loads(raw), load(folder / 'transport.json'), load(folder / 'intent.json')
        request = read(folder / 'request.body.json')
        check('cache-identity-order-plan-transport-intent:' + sid, all(row[k] == s[k] for k in ('slot_id', 'protocol', 'block', 'condition', 'order')) and transport['slot_id'] == intent['slot_id'] == sid and transport['protocol'] == s['protocol'] and transport['condition'] == s['condition'] and transport['block'] == s['block'])
        check('cache-transport-raw-response-request-SHA:' + sid, row['http_status'] == transport['http_status'] == 200 and sha(raw) == transport['raw_response_sha256'] and len(raw) == transport['raw_response_bytes'] and sha(request) == transport['request_sha256'] and len(request) == transport['request_bytes'])
        usage, path = parsed.get('usage', {}), pointers[s['protocol']]
        check('selected-usage-path-and-state:' + sid, row['selected_cache_read_path'] == '/usage/' + '/'.join(path) and row['cache_read'] == state(usage, path) and row['creation_named_field'] == state(usage, ['cache_creation_input_tokens']))
        if s['protocol'] == 'chat-completions':
            check('chat-alias-equality-without-addition:' + sid, row['cached_tokens_alias'] == state(usage, ['prompt_tokens_details', 'cached_tokens']) == row['cache_read'])
            check('chat-alias-observed-flag-source-exact:' + sid, row.get('alias_values_match_observed') == (row['cached_tokens_alias'] == row['cache_read']))
        reg, done = timestamp(intent['actual_registered_at']), timestamp(transport['at'])
        finish_times.append(done)
        check('cache-real-time-order:' + sid, timestamp(binding['registered_at']) <= reg <= done and type(transport['latency_s']) in (int, float) and transport['latency_s'] >= 0)
        pair_groups[(s['protocol'], s['block'])][s['condition']] = {'request_sha256': sha(request), 'request_bytes': request, 'row': row}
    pairs = []
    for (protocol, block), g in sorted(pair_groups.items()):
        paired = set(g) == {'fresh', 'repeat', 'nonce-control'} and g['fresh']['request_bytes'] == g['repeat']['request_bytes'] and g['fresh']['request_bytes'] != g['nonce-control']['request_bytes']
        check('fresh-repeat-control-actual-wire-body-pair:' + protocol + ':' + str(block), paired)
        pairs.append({'protocol': protocol, 'block': block, 'exactly_three_conditions': set(g) == {'fresh', 'repeat', 'nonce-control'}, 'fresh_repeat_request_byte_identical': g['fresh']['request_bytes'] == g['repeat']['request_bytes'], 'control_request_differs': g['fresh']['request_bytes'] != g['nonce-control']['request_bytes'], 'selected_read_states': {c: v['row']['cache_read'] for c, v in g.items()}})
    check('six-actual-pairs-not-merely-six-labels', len(pairs) == obs['counts']['fresh_repeat_pairs'] == 6)
    generated, now = timestamp(obs['generated_at']), dt.datetime.now().astimezone()
    check('generated-at-aware-not-future-after-all-finish-records', max(finish_times) <= generated <= now)
    original_obs = root / '5-评测报告/L4综合结论-2026-10-29/observations-final-v2.json'
    check('observation-original-retained-exactly', read(original_obs) == read(snap / 'observations-final-v2.json'))
    check('generated-at-filesystem-mtime-consistency', abs(original_obs.stat().st_mtime - generated.timestamp()) <= 2)
    v1_raw = read(root / '5-评测报告/L4综合结论-2026-10-29/observations-final.json')
    check('v1-original-artifact-retained-at-reviewed-SHA', sha(v1_raw) == '5f717c44281b64e645ad9018b8492c6caebd7bc1797f7ee368f10cd6eef9a3e6')
    v1, v2 = json.loads(v1_raw), copy.deepcopy(obs)
    check('same-immutable-judge-snapshot-reference-v1-v2', v1['source_final_judge_receipt'] == v2['source_final_judge_receipt'])
    v1.pop('generated_at'); v2.pop('generated_at')
    for old, new in zip(v1['product_records'], v2['product_records']):
        assert old['slot_id'] == new['slot_id']
        new.pop('canonical_block_reason'); new.pop('canonical_accounting')
        if new['canonical_fails'] is None and old['canonical_fails'] == []:
            new['canonical_fails'] = []  # explicitly allowed v1 null-vs-empty repair only
    for new in v2['cache_records']:
        new.pop('alias_values_match_observed', None)
    check('all-other-v1-v2-data-exactly-equal', v1 == v2)
    old_source = Path('/private/tmp/l4-observation-review-0upzwzsb/build_observations.py').read_bytes()
    assert sha(old_source) == '2ec64a476a4a897416c3ef19be1d25ddedc6e319878dda93e72d17527a72a5b3'
    old_tree, new_tree = ast.parse(old_source), ast.parse(src)
    old_tree.body = [n for n in old_tree.body if not isinstance(n, ast.FunctionDef) or n.name != 'build']
    new_tree.body = [n for n in new_tree.body if not isinstance(n, ast.FunctionDef) or n.name != 'build']
    check('builder-outside-build-AST-identical-v1-v2', ast.dump(old_tree, include_attributes=False) == ast.dump(new_tree, include_attributes=False))
    # Do not execute builder: it can create a new judge snapshot before validation.
    ast_tree = ast.parse(src)
    has_outcome_assert = any(isinstance(n, ast.Assert) and any(isinstance(v, ast.Constant) and v.value in (200, 2048, 'cached_tokens_alias') for v in ast.walk(n)) for n in ast.walk(ast_tree))
    check('observed-cache-conclusion-not-hardcoded-as-build-assert', not has_outcome_assert)
    if has_outcome_assert:
        findings.append({'id': 'posthoc-pattern-build-precondition', 'severity': 'fix', 'detail': 'HTTP200 and repeat2048/other0 are observed data checks, not preregistered validity invariants; current values match but contradictory future data would abort rather than be retained.'})
    findings += [
        {'id': 'executed-label-is-record-coverage-not-R1-executed', 'severity': 'scope', 'detail': 'All sixteen actual metadata statuses are preserved; canonical snapshot calls them executed_partial. Do not present the executed count as metadata-complete or formal runs.'},
        {'id': 'product-raw-files-not-directly-pinned-by-builder', 'severity': 'scope', 'detail': 'Builder references product meta SHA and cache raw responses; this audit separately checks product stdout/stderr/prompt hashes. A meta SHA is not itself an assertion that native raw artifact SHA was recomputed by builder.'},
        {'id': 'wallclock-not-external-attestation', 'severity': 'scope', 'detail': 'Aware local generated_at is nonfuture, later than all recorded finishes and near file mtime. No NTP/trusted timestamp proof; producer durations and finish definitions remain product-specific.'},
        {'id': 'cache-label-and-creation-scope', 'severity': 'scope', 'detail': 'Six actual request pairs checked. fresh/repeat are planned labels; zero selected read is not proof of absolute cold cache or no creation; missing named creation counter is not provider-wide no-creation or billing evidence.'},
        {'id': 'notexec-historical-reason-scope', 'severity': 'scope', 'detail': 'WB first-slot original reason says batch zero sends at that moment; do not extend that historical sentence to the later four WB executed slots or global zeroAPI.'}]
    drift = []
    for name, before_sha in baseline.items():
        p = Path(name)
        got = sha(p.read_bytes())
        if got != before_sha: drift.append({'path': name, 'before_sha256': before_sha, 'after_sha256': got})
    check('all-audit-input-bytes-unchanged', not drift)
    live_source = root / '5-评测报告/L4综合结论-2026-10-29/build_observations.py'
    live_delta = [] if sha(live_source.read_bytes()) == sha(src) else [{'path': str(live_source.relative_to(root)), 'reviewed_sha256': sha(src), 'live_sha256': sha(live_source.read_bytes()), 'note': 'Lead authorized a separate v2; review remains fixed to v1'}]
    failed = [c['id'] for c in checks if not c['pass']]
    result = {'category': 'offline_recompute/independent_aggregation_review', 'generated_at': now.isoformat(),
              'reviewed_builder_sha256': sha(src), 'reviewed_observation_sha256': sha(read(snap / 'observations-final-v2.json')),
              'checks': checks, 'counts': {'total': len(checks), 'passed': len(checks) - len(failed), 'failed': len(failed)},
              'findings': findings, 'pairs': pairs, 'canonical_accounting_source_counts': dict(canonical_accounts),
              'unique_reference_files_verified': len(refs), 'additional_product_raw_hash_checks': raw_product_checks,
              'source_snapshot_SHA': obs['source_final_judge_receipt']['sha256'],
              'time_observation': {'generated_at': obs['generated_at'], 'latest_recorded_finish': max(finish_times).isoformat(), 'reviewer_now': now.isoformat(), 'trusted_external_clock_attestation': False},
              'protected_inputs': baseline, 'live_doc_drift': drift, 'authorized_new_builder_delta': live_delta,
              'builder_was_executed': False, 'products_models_checkers_or_network_invoked': False,
              'raw_content_exposed': False, 'passed': not failed, 'script_sha256': sha(Path(__file__).read_bytes())}
    text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    uuid = re.compile(r'(?:session-)?[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
    text = uuid.sub(lambda m: ''.join('\\u%04x' % ord(c) for c in m.group()), text)
    assert json.loads(text) == result
    with a.out.open('x') as f: f.write(text)
    print(json.dumps({'counts': result['counts'], 'failed': failed, 'references': len(refs), 'raw_checks': len(raw_product_checks), 'pairs': len(pairs), 'input_drift': len(drift), 'out': str(a.out)}))
    return 0 if not failed else 1


if __name__ == '__main__':
    raise SystemExit(main())
