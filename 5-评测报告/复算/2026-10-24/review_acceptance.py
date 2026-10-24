#!/usr/bin/env python3
"""Lead's offline follow-up acceptance: semantic receipts, product cases, links.
No model calls, candidate execution, gold edits, or historical writes.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BIRD = HERE / 'bird-semantic-review'
CHECKS = []
ISSUES = []


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(name, passed, detail=None):
    CHECKS.append({'test': name, 'pass': bool(passed), 'detail': detail})
    print(('PASS ' if passed else 'FAIL ') + name)


def headings(text):
    result = set(re.findall(r'<a id="([^"]+)"', text))
    for raw in re.findall(r'^#{1,6}\s+(.+)$', text, re.M):
        raw = re.sub(r'\[([^]]+)\]\([^)]*\)', r'\1', raw)
        result.add(''.join(c for c in raw.lower() if c.isalnum() or c in ' -_').replace(' ', '-'))
    return result


def references(value):
    if isinstance(value, dict):
        if 'path' in value:
            yield value
        for child in value.values():
            yield from references(child)
    elif isinstance(value, list):
        for child in value:
            yield from references(child)


def main():
    a = load(BIRD / 'results.json')
    b = load(BIRD / 'independent-results.json')
    old = load(HERE / 'results.json')
    check('semantic_assertions_11', len(a['assertions']) == 11 and all(a['assertions'].values()))
    check('q26_independent_base_rows', a['q26']['free_only']['rows'] == 5 and a['q26']['free_or_reduced']['rows'] == 6
          and len(b['q26']['free_rows']) == 5 and len(b['q26']['frpm_rows']) == 6)
    check('q27_projection_not_join_fanout', a['q27']['selected_school_count'] == 8574
          and a['q27']['variants']['left_exact']['rows'] == b['q27']['gold_rows'] == 8574
          and a['q27']['left_distinct']['rows'] == b['q27']['gold_distinct_raw'] == 8217
          and a['q27']['duplicates_all_distinct_school_keys']
          and a['q27']['duplicates_all_missing_exact_sat'])
    check('q27_inner_null_populations', b['q27']['inner_rows'] == 749
          and b['q27']['unmatched_sat_rows'] == 7825 and b['q27']['matched_sat_null_write'] == 295
          and b['q27']['null_write_gold_rows'] == 8120)
    ar = {r['run_id']: r for r in a['sample_sensitivity']}
    br = {r['run_id']: r for r in b['runs']}
    original = {r['run_id']: r for r in old['runs'] if r['task'] == 'bird-ca-schools-15'}
    check('same_eight_archived_runs', len(ar) == 8 and ar.keys() == br.keys() == original.keys())
    agree = True
    for key, r in ar.items():
        other = br[key]
        for x, y in [('frozen_original_15', 'recomputed'),
                     ('exclude_q26_14_questions', 'exclude_q26'),
                     ('q26_frpm_counterfactual_15_questions', 'replace_q26_frpm')]:
            agree &= all(r[x][field] == other[y][field] for field in ('correct', 'weighted', 'reward'))
        agree &= r['frozen_original_15']['weighted'] == original[key]['weighted']
    check('two_independent_methods_agree_all_tracks', agree)
    check('q26_all_eight_match_frpm_only', all(r['q26']['frpm_counterfactual_pass'] and not r['q26']['gold_pass'] for r in ar.values()))
    check('q27_dedup_cannot_explain_current_failures', all(not r['q27_pass_if_both_deduplicated'] for r in br.values()))
    check('eight_headlines_unchanged_in_two_sensitivities', all(r[k]['reward'] == r['frozen_original_15']['reward']
          for r in ar.values() for k in ('exclude_q26_14_questions', 'q26_frpm_counterfactual_15_questions')))
    check('semantic_protected_hashes_match', a['source_hashes_before'] == a['source_hashes_after']
          and all(sha(ROOT / p) == digest for p, digest in a['source_hashes_after'].items())
          and all(b['read_only_hash_check'].values()))
    check('historical_374_files_unchanged', all(sha(ROOT / p) == digest
          for files in old['historical_evidence_sha256'].values() for p, digest in files.items()))
    check('checker_and_truth_versions_unchanged', all(
          sha(ROOT / '2-用例' / name / 'checker.py') == v['checker_sha256']
          and sha(ROOT / '2-用例' / name / 'truth.json') == v['truth_sha256']
          for name, v in old['versions'].items()))

    cases = load(ROOT / '5-评测报告/竞品案例-2026-10-24.json')['cases']
    check('two_trace_backed_cases', len(cases) == 2)
    dab, cargo = cases
    for entry in dab['comparison']:
        path = ROOT / entry['artifact']['path']
        answer = next(x['answer'] for x in map(json.loads, path.read_text().splitlines()) if x['task_id'] == '1871')
        check('dab_submitted_sign/' + entry['product'], answer == entry['artifact']['q1871'])
    all_old = {r['source']: r for r in old['runs']}
    check('case_frozen_scores_match', all(
          all_old[x['run']]['weighted'] == x.get('strict', x.get('strict_contract'))['weighted']
          and all_old[x['run']]['reward'] == 0 for c in cases for x in c['comparison']))
    for entry in cargo['comparison']:
        plan = load(ROOT / entry['artifact']['path'])
        values = entry['artifact']
        check('cargo_plan/' + entry['product'], plan['legs'][0]['takeoff_weight_lbs'] == values['leg1_tow_lbs']
              and plan['legs'][1]['fuel_on_board_gal'] == values['leg2_fob_gal']
              and plan['legs'][1]['takeoff_weight_lbs'] == values['leg2_tow_lbs']
              and plan['summary']['total_time_min'] == values['total_time_min']
              and plan['summary']['route_feasible'] is values['route_feasible'])
    left, right = [all_old[x['run']]['strict']['checks'] for x in cargo['comparison']]
    ld, rd = [{x['id']: x['pass'] for x in rows} for rows in (left, right)]
    check('cargo_four_gains_one_loss', set(cargo['doubao_checks_gained_vs_dsh']) == {k for k in ld if not ld[k] and rd[k]}
          and set(cargo['doubao_checks_lost_vs_dsh']) == {k for k in ld if ld[k] and not rd[k]})
    reference_count = 0
    for ref in references(cases):
        p = ROOT / ref['path']; reference_count += 1
        if not p.is_file():
            ISSUES.append({'kind': 'missing_reference', 'path': ref['path']}); continue
        n = len(p.read_text(encoding='utf-8').splitlines())
        for k, span in ref.items():
            if k.endswith('lines') and isinstance(span, list) and not (1 <= span[0] <= span[-1] <= n):
                ISSUES.append({'kind': 'bad_line_range', 'path': ref['path'], 'range': span})
    check('structured_case_references_exist', not ISSUES, reference_count)
    docs = [ROOT / name for name in ('README.md', '2-用例/bird-ca-schools-15/spec.md',
            '5-评测报告/README.md', '5-评测报告/阶段报告-v2.0.md', '5-评测报告/竞品案例-2026-10-24.md',
            '6-周报/2026-10-24-第2期.md')] + [HERE / 'README.md'] + list(BIRD.glob('*.md'))
    links = 0
    for doc in docs:
        for raw in re.findall(r'\]\(<?([^\n>]+?)>?\)', doc.read_text(encoding='utf-8')):
            parts = urlsplit(raw)
            if parts.scheme: continue
            target = (doc.parent / unquote(parts.path)).resolve() if parts.path else doc
            links += 1
            if not target.exists():
                ISSUES.append({'kind': 'missing_link', 'doc': str(doc.relative_to(ROOT)), 'target': raw})
            elif parts.fragment and target.is_file():
                anchor = unquote(parts.fragment)
                text = target.read_text(encoding='utf-8')
                if re.fullmatch(r'L\d+(?:-L\d+)?', anchor):
                    valid = max(map(int, re.findall(r'\d+', anchor))) <= len(text.splitlines())
                else: valid = anchor in headings(text)
                if not valid: ISSUES.append({'kind': 'bad_anchor', 'doc': str(doc.relative_to(ROOT)), 'target': raw})
    check('followup_links_and_anchors', not ISSUES, links)
    unknown = load(ROOT / '5-评测报告/未知登记.json')
    by_id = {x['id']: x for x in unknown['unknowns']}
    check('unknown_transition_not_fake_closure', by_id['bird-q26-q27']['status'] == 'closed'
          and by_id['bird-semantic-contract-revision']['status'] == 'open'
          and by_id['dab-q2697-contract-ambiguity']['status'] == 'open'
          and dict(Counter(x['status'] for x in unknown['unknowns'])) == unknown['counts'])
    check('no_new_product_runs_or_formal_regrade', a['new_agent_runs'] == 0 and not a['policy']['formal_grade_replaced'])
    output = {'date': '2026-10-24', 'kind': 'lead-followup-offline-acceptance',
              'passed': sum(x['pass'] for x in CHECKS), 'total': len(CHECKS), 'checks': CHECKS, 'issues': ISSUES}
    (BIRD / 'acceptance.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passed': output['passed'], 'total': output['total'], 'issues': ISSUES}, ensure_ascii=False))
    return 0 if output['passed'] == output['total'] and not ISSUES else 1


if __name__ == '__main__':
    raise SystemExit(main())
