#!/usr/bin/env python3
"""Synthetic Python processes only: test the runner's stop primitive, never run CLI.
A TERM-ignoring descendant writes only a disposable temp counter. Cleanup uses
our known new process-group ID and SIGKILL in finally; no user process is targeted.
"""
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def module(path):
    spec = importlib.util.spec_from_file_location('fixed_dsh_stop_under_test', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def denied_case(lab):
    real_os = lab.os
    calls = []
    def denied(*args):
        calls.append(['killpg', *args])
        raise PermissionError(1, 'synthetic permission denied')
    proc = SimpleNamespace(pid=424242, wait=lambda **kw: calls.append(['wait', kw]))
    lab.os = SimpleNamespace(getpgid=lambda pid: pid, killpg=denied)
    try:
        try:
            receipt = lab.stop_process_group(proc, 1)
            return {'id': 'permission-denied-not-already-gone',
                    'pass': receipt.get('stop_verified') is False and 'already gone' not in str(receipt),
                    'observed': {'receipt': receipt, 'calls': calls, 'raised': False}}
        except Exception as exc:
            return {'id': 'permission-denied-not-already-gone', 'pass': True,
                    'observed': {'raised': True, 'error': repr(exc), 'calls': calls}}
    finally:
        lab.os = real_os


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def descendant_case(lab):
    with tempfile.TemporaryDirectory(prefix='l4-independent-stop-') as td:
        tmp = Path(td).resolve()
        ticks = tmp / 'ticks.txt'
        child = '''import signal,time,sys
from pathlib import Path
signal.signal(signal.SIGTERM,signal.SIG_IGN)
p=Path(sys.argv[1]);p.write_text('0')
i=0
while True:
 i+=1;p.write_text(str(i));time.sleep(.03)
'''
        parent = '''import subprocess,sys,time,json
from pathlib import Path
p=subprocess.Popen([sys.executable,'-B','-c',sys.argv[1],sys.argv[2]],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
limit=time.monotonic()+5
while not Path(sys.argv[2]).exists() and time.monotonic()<limit: time.sleep(.01)
print(json.dumps({'child_pid':p.pid,'ready':Path(sys.argv[2]).exists()}),flush=True)
while True: time.sleep(1)
'''
        proc = subprocess.Popen([sys.executable, '-B', '-c', parent, child, str(ticks)],
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, start_new_session=True)
        # This is the just-created, owned group. It is never computed from user data.
        owned_pgid = proc.pid
        cleanup = {'group': owned_pgid}
        observed = {'command': [sys.executable, '-B', '-c', '<synthetic parent>', '<synthetic child>', str(ticks)],
                    'parent_code': parent, 'child_code': child, 'pgid': owned_pgid}
        try:
            selector = selectors.DefaultSelector()
            selector.register(proc.stdout, selectors.EVENT_READ)
            ready = selector.select(timeout=8)
            selector.close()
            if not ready:
                raise RuntimeError('synthetic parent did not become ready')
            state = json.loads(proc.stdout.readline())
            if not state['ready']:
                raise RuntimeError('child did not write readiness counter')
            observed.update(state)
            start = time.monotonic()
            receipt = lab.stop_process_group(proc, 0.1)
            elapsed = time.monotonic() - start
            before = ticks.read_text()
            time.sleep(.25)
            after = ticks.read_text()
            child_alive = alive(state['child_pid'])
            observed.update(receipt=receipt, elapsed_s=elapsed, parent_exit_code=proc.poll(),
                            child_alive_after_return=child_alive, counter_before=before,
                            counter_after=after, wrote_after_stop_return=before != after)
            # An unsafe normal return is a failing stop test regardless of metadata wording.
            passed = not child_alive and before == after
        finally:
            try:
                os.killpg(owned_pgid, signal.SIGKILL)
                cleanup['sent_SIGKILL'] = True
            except ProcessLookupError:
                cleanup['already_gone'] = True
            proc.wait(timeout=5)
            if proc.stdout:
                proc.stdout.close()
            if proc.stderr:
                proc.stderr.close()
            before_cleanup_check = ticks.read_text() if ticks.exists() else None
            time.sleep(.15)
            after_cleanup_check = ticks.read_text() if ticks.exists() else None
            cleanup['counter_stable_after_cleanup'] = before_cleanup_check == after_cleanup_check
            observed['cleanup'] = cleanup
        return {'id': 'parent-exited-but-term-ignoring-child-must-stop', 'pass': passed, 'observed': observed}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    lab = module(a.source)
    rows = [denied_case(lab), descendant_case(lab)]
    result = {'category': 'self_test', 'scope': 'Synthetic owned Python process-group stop only; no CLI/model/checker/network',
              'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'live_doc_drift': [],
              'source_sha256': sha(a.source), 'reviewer_script_sha256': sha(Path(__file__)),
              'checks': rows, 'passed': all(r['pass'] for r in rows)}
    with a.out.open('x') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({'checks': len(rows), 'passed': sum(r['pass'] for r in rows), 'out': str(a.out)}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
