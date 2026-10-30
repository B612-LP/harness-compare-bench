#!/usr/bin/env python3
"""Retain the v2 fifteen predicates; provide newly required raw stop receipts.
Additional tests bind stop receipt bytes/identity, without executing any runner.
"""
import argparse
import datetime as dt
import importlib.util
import json
from pathlib import Path


def load(p, n):
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--validator', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    own = Path(__file__).parent
    v2 = load(own / 'gate_adversarial_v2.py', 'gate_harness_v2_immutable')
    old = load(own / 'gate_adversarial.py', 'gate_harness_v1_immutable')
    gate = load(a.source, 'gate_fixed_v3')
    vm = load(a.validator, 'validator_fixed_v3')
    names = ['positive', 'release-false', 'ok-nonzero-exit', 'fake-one-second-timeout',
             'wrong-checker-sha', 'wrong-product-rule-order', 'wrong-raw-checker',
             'notexec-missing-reason-and-seal', 'wb-observed-valid', 'wb-unknown-without-management',
             'timeout-verified-positive', 'timeout-no-termination', 'timeout-stop-false',
             'timeout-permission-denied', 'wb-observed-effort-unknown-no-management']
    extras = ['timeout-raw-sha-mismatch', 'timeout-raw-verified-false', 'timeout-group-confirmed-false',
              'timeout-raw-missing', 'timeout-borrowed-slot-receipt', 'timeout-meta-verified-false']
    rows = []
    for name in names + extras:
        original_dump = old.dump
        def with_receipt(path, value):
            if path.name == 'meta.json' and value.get('status') == 'timeout' and name != 'timeout-no-termination':
                positive = name == 'timeout-verified-positive' or name in extras
                doc = {'policy': 'synthetic group-confirmed fixture', 'pgid': 123456,
                       'signal': 'SIGTERM', 'at': '2026-10-29T10:32:00+00:00',
                       'ack_at': '2026-10-29T10:32:00.100000+00:00',
                       'verified_stop': positive, 'group_confirmed_gone': positive,
                       'slot_id': value['slot_id'], 'timeout_s': 1800, 'duration_s': 1800.1}
                if name == 'timeout-raw-verified-false':
                    doc['verified_stop'] = False
                if name == 'timeout-group-confirmed-false':
                    doc['group_confirmed_gone'] = False
                if name == 'timeout-borrowed-slot-receipt':
                    doc['slot_id'] = 'a-different-planned-slot'
                if name == 'timeout-permission-denied':
                    doc['error'] = 'EPERM, no group disappearance observed'
                rp = path.with_name('termination-receipt.json')
                original_dump(rp, doc)
                value['termination_receipt'] = {'file': rp.name, 'sha256': v2.sha(rp),
                                                'verified_stop': doc['verified_stop']}
                if name == 'timeout-meta-verified-false':
                    value['termination_receipt']['verified_stop'] = False
                if name == 'timeout-raw-sha-mismatch':
                    rp.write_text('{"tampered":true}\n')
                if name == 'timeout-raw-missing':
                    # No deletion: reference an absent immutable name instead.
                    value['termination_receipt']['file'] = 'absent-termination-receipt.json'
            return original_dump(path, value)
        old.dump = with_receipt
        try:
            source_label = 'timeout-verified-positive' if name in extras else name
            got = v2.exercise(old, gate, vm, source_label)
        finally:
            old.dump = original_dump
        formal = not got['raised'] and got['row']['formal_admission']
        if name in ('positive', 'wb-observed-valid', 'timeout-verified-positive'):
            passed = formal
        elif name == 'notexec-missing-reason-and-seal':
            passed = got['raised'] or not got['summary']['accounting_complete']
        else:
            passed = not formal
        rows.append({'id': name, 'original_v2_predicate': name in names, 'pass': bool(passed), 'observed': got})
    result = {'category': 'self_test', 'scope': 'Original fifteen truth-table predicates plus receipt-binding negatives; all evidence/git synthetic; no CLI/model/checker',
              'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'live_doc_drift': [],
              'source_sha256': v2.sha(a.source), 'validator_sha256': v2.sha(a.validator),
              'reviewer_script_sha256': v2.sha(Path(__file__)), 'v2_harness_sha256': v2.sha(own / 'gate_adversarial_v2.py'),
              'fixture_changes': ['new production requirement: actual synthetic termination-receipt file, SHA, verified_stop/group_confirmed_gone/pgid/time fields',
                                  'original fifteen expected truth values unchanged'],
              'checks': rows, 'passed': all(r['pass'] for r in rows)}
    with a.out.open('x') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({'checks': len(rows), 'original_passed': sum(r['pass'] for r in rows if r['original_v2_predicate']),
                      'passed': sum(r['pass'] for r in rows), 'failed': [r['id'] for r in rows if not r['pass']], 'out': str(a.out)}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
