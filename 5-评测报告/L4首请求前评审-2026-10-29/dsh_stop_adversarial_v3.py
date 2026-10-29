#!/usr/bin/env python3
"""Retain previous two stop predicates, adapt signature, and probe EPERM branches.
Real process case reuses immutable original test and cleanup. No CLI/network.
"""
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
from types import SimpleNamespace


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def synthetic_permission_case(lab, mode):
    original_os, original_time = lab.os, lab.time
    calls, tick = [], [0.0]
    def killpg(pgid, sig):
        calls.append({'pgid': pgid, 'signal': int(sig)})
        if mode == 'probe-eperm-kill-esrch' and sig == signal.SIGKILL:
            raise ProcessLookupError(3, 'synthetic ESRCH for owned fixture group')
        if mode == 'probe-eperm-kill-delivered' and sig == signal.SIGKILL:
            return None
        raise PermissionError(1, 'synthetic EPERM; not evidence of disappearance')
    def clock():
        tick[0] += 1.0
        return tick[0]
    proc = SimpleNamespace(pid=424242, returncode=0, wait=lambda **kw: 0)
    lab.os = SimpleNamespace(killpg=killpg, getpgid=lambda pid: pid)
    lab.time = SimpleNamespace(time=clock, sleep=lambda seconds: None)
    try:
        receipt = lab.stop_process_group(proc.pid, proc, 1)
        want = mode == 'probe-eperm-kill-esrch'
        passed = receipt.get('verified_stop') is want and receipt.get('group_confirmed_gone') is want
        return {'id': mode, 'original_v2_predicate': mode == 'permission-denied-not-already-gone',
                'pass': passed and (want or 'already gone' not in str(receipt)),
                'observed': {'receipt': receipt, 'calls': calls,
                             'note': 'all OS signals and time injected; no actual process with synthetic pid exists'}}
    finally:
        lab.os, lab.time = original_os, original_time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    own = Path(__file__).parent
    old = load(own / 'dsh_stop_adversarial.py', 'original_stop_test_immutable')
    lab = load(a.source, 'dsh_fixed_v3')
    rows = [synthetic_permission_case(lab, m) for m in
            ('permission-denied-not-already-gone', 'probe-eperm-kill-delivered', 'probe-eperm-kill-esrch')]
    # Signature-only adapter: original (proc, timeout) -> candidate (launch_pgid, proc, timeout).
    shim = SimpleNamespace(stop_process_group=lambda proc, timeout_s: lab.stop_process_group(proc.pid, proc, timeout_s))
    real = old.descendant_case(shim)
    real['original_v2_predicate'] = True
    rows.append(real)
    result = {'category': 'self_test', 'scope': 'Original two stop predicates + EPERM/KILL branches; owned synthetic Python group only; no CLI/model/checker/network',
              'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'live_doc_drift': [],
              'source_sha256': sha(a.source), 'reviewer_script_sha256': sha(Path(__file__)),
              'original_harness_sha256': sha(own / 'dsh_stop_adversarial.py'),
              'checks': rows, 'passed': all(r['pass'] for r in rows)}
    with a.out.open('x') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({'checks': len(rows), 'original_passed': sum(r['pass'] for r in rows if r['original_v2_predicate']),
                      'passed': sum(r['pass'] for r in rows), 'failed': [r['id'] for r in rows if not r['pass']], 'out': str(a.out)}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
