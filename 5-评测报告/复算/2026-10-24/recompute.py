#!/usr/bin/env python3
"""Offline versioned regrade; never writes historical run directories.

--collect-supplement copies missing submitted cargo code from the workspace named
by historical meta.json into a NEW provenance-labelled directory. This is a
collection dated today, not proof that the bytes were frozen at execution time.
Normal execution needs only repository files; all candidate execution happens in
TemporaryDirectory. No models, network, or GUI are used.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CASE_ROOT = REPO / '2-用例'
PRODUCTS = ('codex', 'dsh', 'workbuddy', 'doubao')
CASES = ('bird-ca-schools-15', 'exercism-py-6', 'dabstep-payments-10',
         'lcb-recent-hard-4', 'tb-cargo-plan')
EXERCISES = ('forth', 'poker', 'dominoes', 'bowling', 'zipper', 'pov')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def rel(path):
    return path.relative_to(REPO).as_posix()


def selections():
    # This pre-existing snapshot supplies SOURCES only, never derived scores,
    # n=3 averages, four-dimensional scores, or arbitrary D4 form bonuses.
    data = read_json(HERE.parent / 'v2-data.json')
    rows = []
    for product in PRODUCTS:
        for case in CASES:
            source = data['products'][product]['cells'][case]['source']
            rows.append((product, case, 'first', REPO / source))
    for path in sorted((REPO / '3-表现现场/r1028-repeats/runs').glob('*/meta.json')):
        meta = read_json(path)
        rows.append((meta['product'], meta['case'], 'repeat-%s' % meta['rep'], path.parent))
    assert len(rows) == 32, len(rows)
    return rows


def artifact_root(source):
    return source / 'workspace' if (source / 'workspace').is_dir() else source


def supplement_name(source):
    return source.parent.name + '__' + source.name


def collect_supplement():
    records = []
    for product, case, rep, source in selections():
        if case != 'tb-cargo-plan':
            continue
        root = artifact_root(source)
        if (root / 'inputs/app/dispatch.py').is_file():
            continue
        meta = read_json(source / 'meta.json')
        workspace_evidence = source / 'meta.json'
        workspace_value = meta.get('workspace')
        if not workspace_value:
            workspace_evidence = source / 'trace/trace-summary.json'
            workspace_value = read_json(workspace_evidence)['workspace']
        workspace = Path(workspace_value)
        # No deletion, overwrite of historical sources, or guessed alternate paths.
        assert workspace.is_absolute() and workspace.is_dir(), workspace
        app = workspace / 'inputs/app'
        assert (app / 'dispatch.py').is_file(), app
        dest = HERE / 'source-supplement' / supplement_name(source)
        entries = []
        for path in sorted(app.glob('*.py')):
            output = dest / 'inputs/app' / path.name
            output.parent.mkdir(parents=True, exist_ok=True)
            if output.exists():
                assert output.read_bytes() == path.read_bytes(), 'Supplement already differs: %s' % output
            else:
                shutil.copy2(path, output)
            entries.append({'path': rel(output), 'sha256': sha(output), 'bytes': output.stat().st_size})
        records.append({'source': rel(source), 'product': product, 'case': case,
                        'rep': rep, 'workspace_from_historical_evidence': str(workspace),
                        'workspace_evidence': rel(workspace_evidence),
                        'collection_date': '2026-10-24', 'files': entries,
                        'limitation': 'Collected from surviving workspace today; no contemporaneous code hash exists. Replay and archived plan/check agreement are consistency evidence, not proof of original-time byte identity.'})
    dump(HERE / 'source-supplement/manifest.json', {'schema_version': 1, 'collections': records})
    print('collected_supplement_runs=%d' % len(records))


def tree_hashes(root):
    # Fingerprint all archived evidence, not just selected output files.
    return {rel(p): sha(p) for p in sorted(root.rglob('*')) if p.is_file()
            and '__pycache__' not in p.parts and p.suffix != '.pyc'}


def copy_inputs(case, root, target):
    original = root / 'inputs'
    supplied = []
    if original.is_dir():
        supplied = [{'path': p.relative_to(root).as_posix(), 'sha256': sha(p)}
                    for p in sorted(original.rglob('*')) if p.is_file()
                    and '__pycache__' not in p.parts and p.suffix != '.pyc']
    # Restore canonical inputs to a temporary grading copy, disclose restoration;
    # never represent this as verification of missing historical input bytes.
    shutil.copytree(CASE_ROOT / case / 'inputs', target / 'inputs')
    if original.is_dir():
        shutil.copytree(original, target / 'inputs', dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    return {'method': 'canonical restored in temporary copy, then archived inputs overlaid',
            'historical_inputs_present': original.is_dir(), 'archived_input_hashes': supplied,
            'limitation': 'Canonical restoration is for reproducibility; it cannot establish the exact missing bytes visible during the historical run.'}


def prepare(product, case, source, target):
    root = artifact_root(source)
    provenance = copy_inputs(case, root, target)
    supplement = None
    if case in ('bird-ca-schools-15', 'dabstep-payments-10'):
        candidates = [root / 'answers.jsonl', root / 'output/answers.jsonl', root / 'outputs/answers.jsonl']
        found = next((p for p in candidates if p.is_file()), None)
        if found is None:
            raise FileNotFoundError('Missing submitted answers: %s' % root)
        shutil.copy2(found, target / 'answers.jsonl')
    elif case == 'lcb-recent-hard-4':
        shutil.copytree(root / 'solutions', target / 'solutions',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    elif case == 'exercism-py-6':
        for ex in EXERCISES:
            assert (root / 'inputs/exercises' / ex / (ex + '.py')).is_file(), (source, ex)
    elif case == 'tb-cargo-plan':
        code_root = root / 'inputs/app'
        if not (code_root / 'dispatch.py').is_file():
            supplement = HERE / 'source-supplement' / supplement_name(source)
            code_root = supplement / 'inputs/app'
            assert (code_root / 'dispatch.py').is_file(), 'Missing source supplement; run --collect-supplement on original machine first: %s' % source
            # Prevent accidentally grading canonical buggy scaffolding as a submission.
            for path in sorted(code_root.glob('*.py')):
                shutil.copy2(path, target / 'inputs/app' / path.name)
        archived = root / 'flight_plan.json'
        if archived.is_file():
            shutil.copy2(archived, target / 'archived-flight_plan.json')
    return provenance, rel(supplement) if supplement else None


def sanitize(value, temp):
    if isinstance(value, dict):
        return {k: sanitize(v, temp) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v, temp) for v in value]
    if isinstance(value, str):
        return value.replace(str(temp), '<temporary-grading-copy>').replace(str(REPO), '<repo>')
    return value


def grade(case, target, scoring=None):
    args = [sys.executable, '-B', str(CASE_ROOT / case / 'checker.py'), str(target), '--json']
    if scoring:
        args += ['--scoring', scoring]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    proc = subprocess.run(args, capture_output=True, text=True, timeout=1200,
                          cwd=str(REPO), env=env)
    if proc.returncode not in (0, 1):
        raise RuntimeError('checker exit=%d: %s' % (proc.returncode, (proc.stdout + proc.stderr)[-2000:]))
    result = json.loads(proc.stdout.strip().splitlines()[-1])
    assert result.get('reward') in (0, 1), result
    # Some historical checker CLIs return 0 for any completed judgment.
    # Outcome comes from JSON reward, never inferred from process success.
    result['execution_exit_code'] = proc.returncode
    return sanitize(result, target)


def check_scores(result):
    return {c['id']: c['pass'] for c in result.get('checks', []) if 'id' in c and 'pass' in c}


def run():
    rows = selections()
    before = {rel(source): tree_hashes(source) for _, _, _, source in rows}
    results = []
    for product, case, rep, source in rows:
        meta = read_json(source / 'meta.json')
        entry = {'run_id': rel(source), 'product': product,
                 'group': 'B-default-model' if product == 'doubao' else 'A-same-model',
                 'interface': 'CLI' if product in ('codex', 'dsh') else 'GUI',
                 'model': meta.get('model'), 'task': case, 'replicate': rep,
                 'source': rel(source), 'historical': {'reward': meta.get('reward'),
                 'weighted': meta.get('weighted'), 'checker_version': (meta.get('judge') or {}).get('checker_version')},
                 'denominator': {'bird-ca-schools-15': 15, 'dabstep-payments-10': 10,
                                 'exercism-py-6': 6, 'lcb-recent-hard-4': 4, 'tb-cargo-plan': 27}[case]}
        if product == 'workbuddy' and case == 'lcb-recent-hard-4':
            entry.update({'status': 'excluded', 'reward': None, 'weighted': None,
                          'strict': None, 'exclusion_reason': 'suspect: archived trace records WebSearch of official editorial; not comparable to offline CLI; not replaced by zero'})
            results.append(entry)
            continue
        with tempfile.TemporaryDirectory(prefix='bench-regrade-') as tmp:
            target = Path(tmp) / 'run'
            target.mkdir()
            provenance, supplement = prepare(product, case, source, target)
            strict = grade(case, target, 'strict-contract' if case == 'dabstep-payments-10' else None)
            compat = grade(case, target, 'official-compat') if case == 'dabstep-payments-10' else None
            old = meta.get('judge') or {}
            compared_checks = {k: {'historical': v, 'regraded': check_scores(strict).get(k)}
                               for k, v in check_scores(old).items()
                               if k in check_scores(strict) and v != check_scores(strict)[k]}
            entry.update({'status': 'regraded', 'checker_version': strict.get('checker_version'),
                          'reward': strict['reward'], 'weighted': strict['weighted'],
                          'strict': strict, 'official_compat': compat,
                          'input_provenance': provenance, 'source_supplement': supplement,
                          'changed_vs_historical': strict['reward'] != meta.get('reward') or abs(strict['weighted'] - meta.get('weighted', -1)) > 0.001,
                          'check_changes': compared_checks})
            # Cargo scorer regenerates a plan independently; record agreement of
            # individual assertions with the historical checker output. Do not
            # call this proof of original-time identity of recovered code.
            if case == 'tb-cargo-plan':
                entry['historical_checks_agree'] = not compared_checks
                checker_path = CASE_ROOT / case / 'checker.py'
                spec = importlib.util.spec_from_file_location('cargo_replay', checker_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                regenerated_plan, replay_note = module.run_agent_code(target)
                archived_plan_path = target / 'archived-flight_plan.json'
                entry['archived_plan_json_equal_to_replay'] = (regenerated_plan == read_json(archived_plan_path)) if archived_plan_path.exists() else None
                entry['replay_note'] = replay_note
        results.append(entry)
        print('%s %s %s: %s/%s' % (product, case, rep, entry['reward'], entry['weighted']), flush=True)
    after = {rel(source): tree_hashes(source) for _, _, _, source in rows}
    assert before == after, 'Historical evidence changed during regrade'
    summary = {}
    for product in PRODUCTS:
        cells = [r for r in results if r['product'] == product and r['replicate'] == 'first' and r['status'] == 'regraded']
        summary[product] = {'valid_first_cells': len(cells), 'excluded_first_cells': 5 - len(cells),
                            'pass': sum(r['reward'] for r in cells),
                            'weighted_sum_observed': round(sum(r['weighted'] for r in cells), 2),
                            'not_a_cross_product_rank': True}
    output = {'schema_version': 1, 'date': '2026-10-24',
              'kind': 'offline regrade of existing submissions, NOT new agent runs',
              'versions': {case: {'checker_sha256': sha(CASE_ROOT / case / 'checker.py'),
                                   'truth_sha256': sha(CASE_ROOT / case / 'truth.json')} for case in CASES},
              'policy': {'historical_untouched': True, 'execution': 'temporary copies only; no model/network/GUI',
                         'dabstep': 'official-compat and strict-contract shown side by side; strict addresses known sign/ACI flaws only',
                         'suspect': 'excluded, not zero', 'yuanbao': 'paused; 5 unexecuted slots excluded from run counts',
                         'confidence': 'Small heterogeneous convenience sample; no causal Harness ranking or general grader-correctness claim'},
              'counts': {'selected': len(results), 'regraded': sum(r['status'] == 'regraded' for r in results),
                         'excluded': sum(r['status'] == 'excluded' for r in results),
                         'changed_vs_historical': sum(r.get('changed_vs_historical', False) for r in results),
                         'new_agent_runs': 0},
              'summary': summary, 'runs': results,
              'historical_evidence_sha256': before,
              'immutability_check': {'before_equals_after': before == after},
              'limitations': ['Restored canonical inputs are explicitly distinguished from archived copies.',
                              'Source supplements were collected on 2026-10-24, not contemporaneously; assertion agreement cannot prove historical code byte identity.',
                              'Regrade is a known-defect correction, not a new pre-registered product evaluation or a comprehensive sandbox security audit.']}
    dump(HERE / 'results.json', output)
    print(json.dumps({'counts': output['counts'], 'summary': summary}, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collect-supplement', action='store_true')
    args = parser.parse_args()
    if args.collect_supplement:
        collect_supplement()
    else:
        run()


if __name__ == '__main__':
    main()
