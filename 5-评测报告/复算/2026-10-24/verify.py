#!/usr/bin/env python3
"""Lead's independent offline acceptance; no model calls or historical writes."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CASES = REPO / '2-用例'
ROWS = []


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(name, condition, detail=None):
    ROWS.append({'test': name, 'pass': bool(condition), 'detail': detail})
    print(('PASS ' if condition else 'FAIL ') + name, flush=True)


def execute(args, timeout=900):
    p = subprocess.run([sys.executable, '-B'] + [str(x) for x in args],
                       capture_output=True, text=True, cwd=str(REPO), timeout=timeout,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    return p


def judgment(case, run, scoring=None):
    args = [CASES / case / 'checker.py', run, '--json']
    if scoring:
        args += ['--scoring', scoring]
    p = execute(args)
    return p, json.loads(p.stdout.strip().splitlines()[-1])


def main():
    data = load(HERE / 'results.json')
    check('regrade_counts', data['counts'] == {'selected': 32, 'regraded': 31,
          'excluded': 1, 'changed_vs_historical': 2, 'new_agent_runs': 0}, data['counts'])
    check('unique_selected_runs', len({r['run_id'] for r in data['runs']}) == 32)
    check('excluded_is_null_not_zero', all(r['reward'] is None and r['weighted'] is None
          for r in data['runs'] if r['status'] == 'excluded'))
    check('recorded_historical_immutability', data['immutability_check']['before_equals_after'])
    current_match = all(sha(REPO / path) == want
                        for files in data['historical_evidence_sha256'].values()
                        for path, want in files.items())
    check('historical_snapshots_still_unchanged', current_match)
    for case, version in data['versions'].items():
        check('frozen_version/' + case,
              sha(CASES / case / 'checker.py') == version['checker_sha256']
              and sha(CASES / case / 'truth.json') == version['truth_sha256'])
    supplemental = load(HERE / 'source-supplement/manifest.json')['collections']
    check('six_recovered_source_sets', len(supplemental) == 6)
    check('supplement_sha256_matches', all(sha(REPO / f['path']) == f['sha256']
          for s in supplemental for f in s['files']))
    cargo = [r for r in data['runs'] if r['task'] == 'tb-cargo-plan']
    check('eight_cargo_replay_checks_and_plans_agree', len(cargo) == 8
          and all(r['historical_checks_agree'] and r['archived_plan_json_equal_to_replay'] for r in cargo))
    dab = [r for r in data['runs'] if r['task'] == 'dabstep-payments-10']
    check('dab_official_compat_preserves_historical', all(
          r['official_compat']['reward'] == r['historical']['reward']
          and r['official_compat']['weighted'] == r['historical']['weighted'] for r in dab))
    changed = [r for r in data['runs'] if r.get('changed_vs_historical')]
    check('only_known_sign_corrections_change_scores', len(changed) == 2 and all(
          r['product'] == 'dsh' and r['task'] == 'dabstep-payments-10'
          and r['historical']['weighted'] - r['weighted'] == 10
          and r['historical']['reward'] == r['reward'] == 0 for r in changed))

    selftests = [CASES / c / 'checker.py' for c in data['versions']]
    selftests += [CASES / '_归档-v1' / c / 'checker.py' for c in ('int-sum-sort', 'word-freq-report')]
    selftests += [REPO / '4-打分细则/轻量判卷/validate_run.py', HERE.parent / 'token-recompute.py']
    for script in selftests:
        p = execute([script, '--selftest'])
        check('selftest/' + script.relative_to(REPO).as_posix(), p.returncode == 0,
              {'exit_code': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr})

    with tempfile.TemporaryDirectory(prefix='lead-independent-acceptance-') as td:
        root = Path(td)
        # BIRD isolates the schema failure from missing-question/accuracy failures.
        bird = root / 'bird'; bird.mkdir()
        oracle = (CASES / 'bird-ca-schools-15/solution/answers.jsonl').read_text(encoding='utf-8')
        (bird / 'answers.jsonl').write_text(oracle, encoding='utf-8')
        p, result = judgment('bird-ca-schools-15', bird)
        check('bird_oracle', p.returncode == 0 and result['reward'] == 1 and result['weighted'] == 100)
        (bird / 'answers.jsonl').write_text(oracle.rstrip('\n') + '\nnot-json\n', encoding='utf-8')
        p, result = judgment('bird-ca-schools-15', bird)
        checks = {c['id']: c['pass'] for c in result['checks']}
        check('bird_appended_invalid_line_denied', p.returncode == 1 and result['reward'] == 0
              and checks['answers_schema'] is False and checks['answers_coverage'] is True
              and result['weighted'] == 100, {'reward': result['reward'], 'checks': checks})

        dabrun = root / 'dab'; dabrun.mkdir()
        answers = [json.loads(line) for line in (CASES / 'dabstep-payments-10/solution/answers.jsonl').read_text().splitlines() if line.strip()]
        for row in answers:
            if str(row['task_id']) == '1871': row['answer'] = row['answer'].lstrip('-+')
            if str(row['task_id']) == '2697': row['answer'] = 'Z:' + row['answer'].split(':', 1)[1]
        (dabrun / 'answers.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in answers))
        _, official = judgment('dabstep-payments-10', dabrun, 'official-compat')
        _, strict = judgment('dabstep-payments-10', dabrun, 'strict-contract')
        op = {c['id']: c['pass'] for c in official['checks']}
        sp = {c['id']: c['pass'] for c in strict['checks']}
        check('dab_compat_and_strict_explicitly_diverge_on_sign_and_aci',
              all(op[q] and not sp[q] for q in ('q1871', 'q2697')),
              {'official_weighted': official['weighted'], 'strict_weighted': strict['weighted'],
               'note': 'Two wrong questions may still meet the unchanged 0.8 threshold; assert per-question outcomes, not forced whole-run failure.'})

        exrun = root / 'exercism'
        shutil.copytree(CASES / 'exercism-py-6/inputs', exrun / 'inputs')
        for ex in ('forth', 'poker', 'dominoes', 'bowling', 'zipper', 'pov'):
            (exrun / 'inputs/exercises' / ex / (ex + '.py')).write_text('import os\nos._exit(0)\n')
        _, result = judgment('exercism-py-6', exrun)
        check('exercism_early_exit_cannot_pass', result['reward'] == 0 and result['weighted'] == 0
              and all(not c['pass'] for c in result['checks'] if c['id'] != 'input_integrity'),
              {'reward': result['reward'], 'weighted': result['weighted']})
        for ex in ('forth', 'poker', 'dominoes', 'bowling', 'zipper', 'pov'):
            shutil.copy2(CASES / 'exercism-py-6/solution' / ex / (ex + '.py'),
                         exrun / 'inputs/exercises' / ex / (ex + '.py'))
        _, result = judgment('exercism-py-6', exrun)
        check('exercism_oracle_with_completion', result['reward'] == 1 and result['weighted'] == 100
              and all(c.get('completion', {}).get('identities_match') for c in result['checks'] if c['id'] != 'input_integrity'))

        # Mutate only a temporary case; canonical repository and gold stay read-only.
        cargo = root / 'cargo-case'
        shutil.copytree(CASES / 'tb-cargo-plan', cargo)
        truth = load(cargo / 'truth.json'); truth['threshold'] = 999
        (cargo / 'truth.json').write_text(json.dumps(truth))
        p = execute([cargo / 'checker.py', root / 'unused-run', '--json'])
        result = json.loads(p.stdout.strip().splitlines()[-1])
        check('cargo_truth_drift_fails_closed', p.returncode == 2 and 'error' in result,
              {'exit_code': p.returncode, 'error': result.get('error')})

    # Scan all results again; execution above must not mutate archived material.
    check('historical_snapshots_unchanged_after_independent_tests', all(
          sha(REPO / path) == want for files in data['historical_evidence_sha256'].values() for path, want in files.items()))
    receipt = {'schema_version': 1, 'date': '2026-10-24', 'author_role': 'lead-independent-acceptance',
               'new_model_runs': 0, 'passed': sum(r['pass'] for r in ROWS), 'total': len(ROWS), 'tests': ROWS,
               'dependency_sha256': {'2-用例/exercism-py-6/trusted_runner.py': sha(CASES / 'exercism-py-6/trusted_runner.py')},
               'limit': 'Known counterexamples and recorded invariants only; not general grader correctness or hostile-code sandbox assurance.'}
    (HERE / 'validation.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('LEAD ACCEPTANCE %d/%d' % (receipt['passed'], receipt['total']))
    return 0 if receipt['passed'] == receipt['total'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
