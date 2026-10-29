#!/usr/bin/env python3
"""Original 8 attacks, schema-compatible positive controls, plus stop-receipt tests.
Only synthetic evidence files/injected git. Does not execute a model, CLI, or checker.
The old harness and first failure are immutable; this imports its exact run_case.
"""
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exercise(old, gate, vm, label):
    original_dump = old.dump
    original_admission = gate.gate_admission
    original_external = gate.EXTERNAL_REQUIRED

    def adapt_dump(path, value):
        # Schema-only fixture uplift: actual JSON checks and input verification,
        # not weakening a target or changing expected admission truth values.
        if path.name == 'checker.stdout':
            correct = value.get('correct', 0)
            value['checks'] = [{'id': 'q%d' % i, 'pass': i < correct} for i in range(10)]
            value['weighted'] = 10.0 * correct
        elif path.name == 'score-receipt.json':
            raw = value['raw_checker_output']
            correct = raw.get('correct', 0)
            raw['checks'] = [{'id': 'q%d' % i, 'pass': i < correct} for i in range(10)]
            raw['weighted'] = 10.0 * correct
        elif path.name == 'meta.json':
            value['inputs_verification'] = {'ok': True, 'basis': 'synthetic fixture only'}
            value['judge'] = dict(value['judge'], guards_used=[])  # do not mutate shared raw receipt object
            if label.startswith('timeout-'):
                value.update(status='timeout', timed_out=True, exit_code=None, duration_s=1800.1,
                             finished_at='2026-10-29T10:32:00.100000+00:00')
                value['attempts'][0]['outcome'] = 'timeout'
                value['diagnostic'] = {'stop_source': 'synthetic timeout at plan limit'}
                if label != 'timeout-no-termination':
                    term = {'stop_verified': label == 'timeout-verified-positive',
                            'policy': 'synthetic group verification', 'signal': 'SIGTERM',
                            'group_alive': label != 'timeout-verified-positive'}
                    if label == 'timeout-permission-denied':
                        term['note'] = 'process group already gone: PermissionError'
                        term['error'] = 'EPERM; CLI alone killed, child alive'
                    value['attempts'][0]['termination'] = term
                    value['diagnostic']['termination'] = term
            if label == 'wb-observed-effort-unknown-no-management':
                value['route'].update(actual_gateway='www.workbuddy.cn', route_verification='observed',
                                      observation_method='synthetic passive observation')
                value['reasoning_effort'] = 'unknown'
                value['managed_unknowns'] = []
        return original_dump(path, value)

    def admission(*args, **kwargs):
        reader = kwargs['git_reader']
        # Original fixture predates PREREG D/E comparison: give a fixed identical
        # synthetic body at both commits. This is not a real E/source-closure test.
        kwargs['git_reader'] = lambda commit, p: b'synthetic immutable preregistration\n' if p.endswith('/PREREGISTRATION.md') else reader(commit, p)
        return original_admission(*args, **kwargs)

    old.dump = adapt_dump
    gate.gate_admission = admission
    # Truth-table isolation only. Mandatory external is independently tested in
    # synthetic seal repositories; no real user profile/config is read here.
    gate.EXTERNAL_REQUIRED = []
    try:
        return old.run_case(gate, vm, label)
    finally:
        old.dump = original_dump
        gate.gate_admission = original_admission
        gate.EXTERNAL_REQUIRED = original_external


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--validator', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    old_path = Path(__file__).with_name('gate_adversarial.py')
    old = load(old_path, 'original_independent_harness')
    gate = load(a.source, 'gate_fixed_v2')
    vm = load(a.validator, 'validator_fixed_v2')
    names = ['positive', 'release-false', 'ok-nonzero-exit', 'fake-one-second-timeout',
             'wrong-checker-sha', 'wrong-product-rule-order', 'wrong-raw-checker',
             'notexec-missing-reason-and-seal', 'wb-observed-valid', 'wb-unknown-without-management',
             'timeout-verified-positive', 'timeout-no-termination', 'timeout-stop-false',
             'timeout-permission-denied', 'wb-observed-effort-unknown-no-management']
    rows = []
    for name in names:
        got = exercise(old, gate, vm, name)
        formal = not got['raised'] and got['row']['formal_admission']
        if name in ('positive', 'wb-observed-valid', 'timeout-verified-positive'):
            passed = formal
        elif name == 'notexec-missing-reason-and-seal':
            passed = got['raised'] or not got['summary']['accounting_complete']
        else:
            passed = not formal
        rows.append({'id': name, 'pass': bool(passed), 'observed': got})
    result = {'category': 'self_test', 'scope': 'Independent truth-table retest; no model/CLI/checker execution; synthetic git and external-set isolation',
              'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'live_doc_drift': [],
              'source_sha256': sha(a.source), 'validator_sha256': sha(a.validator),
              'reviewer_script_sha256': sha(Path(__file__)), 'original_harness_sha256': sha(old_path),
              'fixture_changes': ['JSON raw checks for existing synthetic 7/10 and 0/10', 'inputs_verification.ok=true',
                                  'guards_used=[]', 'identical synthetic PREREG D/E bytes', 'empty injected external only for admission truth-table'],
              'checks': rows, 'passed': all(r['pass'] for r in rows)}
    with a.out.open('x') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({'checks': len(rows), 'passed': sum(r['pass'] for r in rows),
                      'failed': [r['id'] for r in rows if not r['pass']], 'out': str(a.out)}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
