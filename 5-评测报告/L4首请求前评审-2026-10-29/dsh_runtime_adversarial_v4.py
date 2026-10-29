#!/usr/bin/env python3
"""Independent runtime control-flow tests: Popen is always a Python object stub.
No product executable, actual child process, checker, network, or answer is used.
Counters prove score/capture and later-slot dispatch are blocked when stop fails.
"""
import argparse
import contextlib
import datetime as dt
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace


def load(path):
    s = importlib.util.spec_from_file_location('dsh_runtime_fixed_v4', path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def world(source, phase):
    lab = load(source)
    with tempfile.TemporaryDirectory(prefix='l4-independent-runtime-') as td:
        root = Path(td).resolve()
        case_root = root / 'cases'
        (case_root / 'synthetic-case' / 'inputs').mkdir(parents=True)
        binding = root / 'binding.json'
        binding.write_text(json.dumps({'preregistration_commit': 'e' * 40,
                                      'registered_at': '2026-10-29T10:00:00+00:00'}))
        slot = {'slot_id': 'synthetic-first', 'run_id': 'synthetic-first', 'event_id': 'event:first',
                'product': 'dsh', 'case': 'synthetic-case', 'rep': 1, 'order': 1,
                'stratum': 'cli_current_sentinel', 'evidence_dir': 'evidence/first', 'timeout_s': 1}
        second = dict(slot, slot_id='synthetic-second', run_id='synthetic-second', event_id='event:second',
                      order=2, evidence_dir='evidence/second')
        plan = {'product_slots': [slot, second]}
        contract = {'case_snapshots': {'synthetic-case': {'checker.py': 'c' * 64}},
                    'denominators': {'synthetic-case': 10}}
        counts = {'popen': 0, 'checker': 0, 'capture': 0, 'rebuild': 0, 'snapshot': 0}
        class FakeProc:
            pid = 424242
            returncode = 0
            def communicate(self, **kw):
                if phase == 'timeout-unverified':
                    raise subprocess.TimeoutExpired('/synthetic/no-product', 1)
                return None, None
        def popen(cmd, **kw):
            counts['popen'] += 1
            assert cmd == ['/synthetic/no-product'], 'no real command permitted'
            assert kw.get('start_new_session') is True
            if phase == 'spawn-failure':
                raise OSError('synthetic spawn failure; no process ever launched')
            kw['stdout'].write('{"synthetic":"first stream"}\n')
            kw['stdout'].flush()
            return FakeProc()
        def forbidden(key):
            def fn(*args, **kwargs):
                counts[key] += 1
                raise AssertionError('must not call ' + key + ' before verified stop')
            return fn
        class OsProxy:
            environ = {}
            def getpgid(self, pid):
                return pid
            def __getattr__(self, key):
                return getattr(os, key)
        lab.os = OsProxy()
        lab.subprocess = SimpleNamespace(Popen=popen, TimeoutExpired=subprocess.TimeoutExpired, PIPE=subprocess.PIPE)
        lab.REPO = root
        lab.ev_dir = lambda slot: root / slot['evidence_dir']  # override definition-bound repo default
        lab.BATCH = root / 'batch'
        lab.CASE_ROOT = case_root
        lab.BINDING_PATH = binding
        lab.WS_BASE = root / 'workspaces'
        lab.STAGING_ROOT = root / 'staging'
        lab.DISPATCH_ROOT = root / 'dispatch'
        lab.HALT_PATH = root / 'halt.json'
        lab.MOCK_CMD = ['/synthetic/no-product']
        lab.cli_version = lambda: 'synthetic-build'
        lab.load_plan = lambda: plan
        lab.load_contract = lambda: contract
        lab.verify_released = lambda: {'ok': True, 'scope': 'synthetic only'}
        lab.build_task = lambda case, ws: 'synthetic task, no answer assets'
        lab.check_isolation = lambda ws: {'ok': True}
        lab.verify_inputs = lambda *args: {'ok': True}
        lab.group_alive = lambda pgid: True
        lab.stop_process_group = lambda pgid, proc, timeout_s, **kw: {
            'policy': 'synthetic stop failure', 'pgid': pgid, 'signal': 'SIGKILL',
            'at': lab.now_iso(), 'verified_stop': False, 'group_confirmed_gone': False,
            'error': 'synthetic EPERM; group stop unconfirmed'}
        lab.score_case = forbidden('checker')
        lab.capture_session = forbidden('capture')
        lab.rebuild_full_stream = forbidden('rebuild')
        lab.snapshot_config = forbidden('snapshot')
        output = io.StringIO()
        first_exc = next_exc = None
        with contextlib.redirect_stdout(output):
            try:
                code = lab.run_slot(slot, contract)
            except Exception as exc:
                code = None
                first_exc = repr(exc)
            after_first = dict(counts)
            try:
                next_code = lab.cmd_run(second['slot_id'], False)
            except Exception as exc:
                next_code = None
                next_exc = repr(exc)
        ev = root / slot['evidence_dir']
        read_json = lambda name: json.loads((ev / name).read_text()) if (ev / name).is_file() else None
        meta, receipt, notexec = [read_json(n) for n in ('meta.json', 'termination-receipt.json', 'notexecuted.json')]
        checks = [
            {'id': phase + ':checker-zero', 'pass': counts['checker'] == 0},
            {'id': phase + ':no-post-stop-capture', 'pass': counts['capture'] == counts['rebuild'] == counts['snapshot'] == 0},
            {'id': phase + ':next-slot-popen-zero', 'pass': counts['popen'] == after_first['popen'] and next_code == 3 and lab.HALT_PATH.is_file()},
            {'id': phase + ':valid-first-accounting', 'pass': first_exc is None and ((meta is not None and receipt is not None) if phase != 'spawn-failure' else (meta is not None or notexec is not None))}]
        if phase == 'spawn-failure':
            # No process was started: require valid accounting, not a new global-halt policy.
            checks = [r for r in checks if not r['id'].endswith(':next-slot-popen-zero')]
        if phase == 'normal-exit-unverified':
            checks.append({'id': phase + ':not-fictitious-timeout', 'pass': meta is not None and meta.get('timed_out') is not True and meta.get('status') != 'timeout'})
        if phase == 'timeout-unverified':
            checks.append({'id': phase + ':raw-stop-false-recorded', 'pass': receipt is not None and receipt.get('verified_stop') is False and meta is not None and meta.get('weighted') is None})
        return {'phase': phase, 'checks': checks, 'observed': {'first_code': code, 'next_code': next_code,
                'first_exception': first_exc, 'next_exception': next_exc, 'counts_after_first': after_first,
                'counts_final': counts, 'stdout': output.getvalue(), 'meta': meta,
                'termination_receipt': receipt, 'notexecuted': notexec,
                'halt': json.loads(lab.HALT_PATH.read_text()) if lab.HALT_PATH.is_file() else None}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    worlds = [world(a.source, p) for p in ('timeout-unverified', 'normal-exit-unverified', 'spawn-failure')]
    rows = [r for w in worlds for r in w['checks']]
    result = {'category': 'self_test', 'scope': 'Independent production run_slot/cmd_run control flow with mandatory in-process Popen stub; no real process/model/checker/network',
              'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'live_doc_drift': [],
              'source_sha256': sha(a.source), 'reviewer_script_sha256': sha(Path(__file__)),
              'worlds': worlds, 'checks': rows, 'passed': all(r['pass'] for r in rows)}
    with a.out.open('x') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({'checks': len(rows), 'passed': sum(r['pass'] for r in rows),
                      'failed': [r['id'] for r in rows if not r['pass']], 'out': str(a.out)}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
