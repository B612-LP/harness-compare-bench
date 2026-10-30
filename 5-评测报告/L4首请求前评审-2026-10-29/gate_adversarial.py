#!/usr/bin/env python3
"""Independent gate truth-table tests in synthetic files with injected read-only git.
No runner/CLI/API/checker is executed and no answer assets are read.
"""
import argparse
import copy
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def dump(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run_case(gate, vm, label):
    with tempfile.TemporaryDirectory(prefix='l4-independent-gate-') as td:
        root = Path(td).resolve()
        plan_dir = root / 'plans/l4'
        D, E = 'd' * 40, 'e' * 40
        reg = '2026-10-29T10:00:00+00:00'
        product = 'workbuddy' if label.startswith('wb-') else 'dsh'
        stratum = 'wb_gateway_delivery' if product == 'workbuddy' else 'cli_current_sentinel'
        slot = {'slot_id': 'synthetic-slot', 'run_id': 'synthetic-run', 'event_id': 'event:synthetic',
                'product': product, 'case': 'synthetic-case', 'rep': 1, 'order': 1,
                'stratum': stratum, 'evidence_dir': 'runs/synthetic', 'timeout_s': 1800}
        plan = {'plan_id': 'synthetic-l4', 'product_slots': [slot]}
        contract = {'rule_version': 'synthetic-l4-v1', 'strata': {
            'cli_current_sentinel': {'products': ['dsh'], 'model': 'deepseek-flash', 'effort': 'low', 'route_host': 'api.deepseek.com'},
            'wb_gateway_delivery': {'products': ['workbuddy'], 'declared_model_alias': 'deepseek-v4.1-flash', 'gateway': 'www.workbuddy.cn'}},
            'case_snapshots': {'synthetic-case': {'checker.py': 'c' * 64}},
            'denominators': {'synthetic-case': 10}, 'admission': {'required_original_evidence': ['prompt', 'stdout', 'stderr', 'session', 'checker', 'workspace']}}
        dump(plan_dir / 'plan.json', plan)
        dump(plan_dir / 'contract.json', contract)
        files = {str((plan_dir / n).relative_to(root)): sha(plan_dir / n) for n in ('plan.json', 'contract.json')}
        manifest = {'schema_version': 1, 'design_commit': D, 'files': files, 'external_files': {}}
        manifest_bytes = json.dumps(manifest).encode()
        binding = {'schema_version': 1, 'design_commit': D, 'execution_seal_commit': E,
                   'preregistration_commit': E, 'registered_at': reg, 'released_for_model_calls': label != 'release-false',
                   'plan_sha256': sha(plan_dir / 'plan.json'), 'contract_sha256': sha(plan_dir / 'contract.json'),
                   'execution_manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(), 'live_doc_drift': []}
        dump(root / 'binding.json', binding)
        blobs = {str((plan_dir / n).relative_to(root)): (plan_dir / n).read_bytes() for n in ('plan.json', 'contract.json')}
        blobs[str((plan_dir / 'execution-manifest.json').relative_to(root))] = manifest_bytes
        ev = root / slot['evidence_dir']
        ev.mkdir(parents=True)
        if label == 'notexec-missing-reason-and-seal':
            dump(ev / 'notexecuted.json', {k: slot[k] for k in ('slot_id', 'run_id', 'event_id')})
        else:
            for name, data in [('prompt.txt', b'synthetic task'), ('agent.jsonl', b'{"synthetic":true}\n'), ('agent.stderr.txt', b'')]:
                (ev / name).write_bytes(data)
            (ev / 'agent-session').mkdir()
            (ev / 'agent-session/session.jsonl').write_text('{"type":"synthetic"}\n')
            (ev / 'workspace').mkdir()
            checker = {'correct': 7, 'n_tasks': 10, 'checker_sha256': 'c' * 64, 'exit_code': 0}
            dump(ev / 'checker.stdout', checker)
            m = {'batch': 'synthetic', 'rule_version': contract['rule_version'], 'preregistration_commit': E,
                 'registered_at': reg, 'rep': 1, 'product': product, 'case': slot['case'], 'form': 'cli',
                 'run_id': slot['run_id'], 'event_id': slot['event_id'], 'slot_id': slot['slot_id'],
                 'order': 1, 'stratum': stratum, 'selection': {'slot_id': slot['slot_id']},
                 'workspace': str(ev / 'workspace'), 'model': 'deepseek-flash', 'reasoning_effort': 'low',
                 'product_version': 'synthetic-build', 'route': {'host': 'api.deepseek.com', 'provider_id': 'deepseek-official'},
                 'tools': [], 'permissions': 'synthetic', 'skills': 'off', 'web_search': 'off', 'soft_constraints': [],
                 'prompt_sha256': sha(ev / 'prompt.txt'), 'isolation': {'ok': True}, 'inputs': [],
                 'status': 'ok', 'exit_code': 0, 'created_at': '2026-10-29T10:01:00+00:00',
                 'started_at': '2026-10-29T10:02:00+00:00', 'finished_at': '2026-10-29T10:02:01+00:00',
                 'duration_s': 1.0, 'attempts': [{'n': 1}], 'transport_retries': 0,
                 'stdout_bytes': (ev / 'agent.jsonl').stat().st_size, 'stdout_sha256': sha(ev / 'agent.jsonl'),
                 'stderr_bytes': 0, 'stderr_sha256': sha(ev / 'agent.stderr.txt'), 'usage': {},
                 'reward': 0, 'weighted': 70.0, 'failed': [], 'judge': checker,
                 'integrity': {'synthetic_independent_review': True}, 'integrity_verdict': 'clean', 'managed_unknowns': []}
            receipt = {'score': {'earned': 7, 'possible': 10, 'reported': 70.0, 'checker_sha256': 'c' * 64}, 'raw_checker_output': checker}
            if label == 'ok-nonzero-exit':
                m['exit_code'] = 9
            elif label == 'fake-one-second-timeout':
                m.update(status='timeout', timed_out=True, exit_code=None)
            elif label == 'wrong-checker-sha':
                m['judge']['checker_sha256'] = 'b' * 64
                receipt['score']['checker_sha256'] = 'b' * 64
            elif label == 'wrong-product-rule-order':
                m.update(product='codex', rule_version='not-the-contract', order=999)
            elif label == 'wrong-raw-checker':
                dump(ev / 'checker.stdout', {'correct': 0, 'n_tasks': 10, 'checker_sha256': 'c' * 64})
            if product == 'workbuddy':
                alias = ev / 'alias.json'
                dump(alias, {'model': 'deepseek-v4.1-flash', 'synthetic_current_choice': True})
                m['route'].update(declared_alias='deepseek-v4.1-flash', alias_evidence=str(alias.relative_to(root)),
                                  actual_gateway='unknown', route_verification='current_not_observed', r2_history_ref='synthetic historical gateway note')
                m['app_asar_sha256'] = 'a' * 64
                if label == 'wb-observed-valid':
                    m['route'].update(actual_gateway='www.workbuddy.cn', route_verification='observed', observation_method='synthetic passive observation with limits')
                elif label == 'wb-unknown-without-management':
                    m['reasoning_effort'] = 'unknown'
            dump(ev / 'meta.json', m)
            dump(ev / 'score-receipt.json', receipt)
        gate.load_runner_validator = lambda: vm
        try:
            report = gate.gate_admission(root / 'binding.json', product, repo=root, plan_dir=plan_dir,
                                         git_reader=lambda commit, p: blobs[p],
                                         git_time=lambda commit: reg if commit == E else '2026-10-29T09:00:00+00:00',
                                         git_ancestor=lambda a, b: True, required_set=set(files))
            return {'raised': False, 'summary': report['summary'], 'row': report['per_slot'][0]}
        except Exception as exc:
            return {'raised': True, 'exception': type(exc).__name__, 'error': str(exc)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--validator', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    gate = load_module(a.source, 'gate_snapshot')
    vm = load_module(a.validator, 'validator_snapshot')
    results = []
    names = ['positive', 'release-false', 'ok-nonzero-exit', 'fake-one-second-timeout', 'wrong-checker-sha',
             'wrong-product-rule-order', 'wrong-raw-checker', 'notexec-missing-reason-and-seal',
             'wb-observed-valid', 'wb-unknown-without-management']
    for name in names:
        observed = run_case(gate, vm, name)
        formal = not observed['raised'] and observed['row']['formal_admission']
        if name in ('positive', 'wb-observed-valid'):
            passed = formal
        elif name == 'notexec-missing-reason-and-seal':
            passed = observed['raised'] or not observed['summary']['accounting_complete']
        else:
            passed = not formal
        results.append({'id': name, 'pass': passed, 'observed': observed})
    result = {'category': 'self_test', 'scope': 'Independent gate truth-table only; synthetic files and injected git; no model/CLI/checker execution',
              'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'source_sha256': sha(a.source),
              'validator_sha256': sha(a.validator), 'reviewer_script_sha256': sha(Path(__file__)),
              'live_doc_drift': [], 'checks': results, 'passed': all(r['pass'] for r in results)}
    with a.out.open('x') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({'passed': result['passed'], 'checks': len(results), 'failed': [x['id'] for x in results if not x['pass']], 'out': str(a.out)}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
