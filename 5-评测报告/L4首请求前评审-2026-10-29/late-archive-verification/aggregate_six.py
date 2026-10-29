#!/usr/bin/env python3
"""Merge exactly six explicitly audited slot receipts; preserve unknown clock data.
No session decompression, model/product/checker calls or original writes occur.
"""
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    a = ap.parse_args()
    root = a.root.resolve()
    scope = root / '5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification'
    spec = importlib.util.spec_from_file_location('presentation', scope / 'make_public_json_view.py')
    public = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(public)
    def write_new(path, data):
        text, n = public.encode(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
        assert json.loads(text) == data
        with path.open('x') as f:
            f.write(text)
    auth = json.loads((scope / 'authorized-six-slots.json').read_bytes())
    proof = json.loads((scope / 'public-json-equivalence.json').read_bytes())
    views = {}
    for p in proof['rows']:
        original, view = scope / p['source'], scope / p['public_view']
        assert sha(original) == p['source_sha256'] and sha(view) == p['public_sha256']
        assert json.loads(original.read_bytes()) == json.loads(view.read_bytes())
        r = json.loads(view.read_bytes())
        assert r['slot_id'] not in views, 'duplicate slot is never overwritten'
        views[r['slot_id']] = (r, view)
    expected_slots = {s['slot_id'] for s in auth['slots']}
    assert len(expected_slots) == 6 and set(views) == expected_slots
    rows, union, cross_drift = [], {}, []
    for s in sorted(auth['slots'], key=lambda s: s['order']):
        r, path = views[s['slot_id']]
        assert r['run_id'] == s['run_id'] and not r['live_doc_drift']
        assert r['protected_before'] == r['protected_after']
        for k, v in r['protected_after'].items():
            if k in union and union[k] != v:
                cross_drift.append({'path': k, 'kind': 'changed-between-slot-audits'})
            union[k] = v
        failed = [c['id'] for c in r['checks'] if not c['pass']]
        identity_failures = [c for c in failed if c != 'collected-at-is-truly-later-than-finished']
        roots = [p for p in r['per_file'] if p.get('identity_role') == 'root']
        children = [p for p in r['per_file'] if p.get('identity_role') == 'child-not-root-prompt']
        rows.append({'slot_id': s['slot_id'], 'run_id': s['run_id'], 'case': s['case'], 'rep': s['rep'], 'order': s['order'],
                     'identity_and_structure': 'supported' if not identity_failures else 'unknown',
                     'identity_unknown_reasons': identity_failures, 'collection_time': 'confirmed_late_field' if r['collected_at'] and 'collected-at-is-truly-later-than-finished' not in failed else 'unknown',
                     'collected_at': r['collected_at'], 'collector_record_at_separate': r.get('collector_record_at_separate_uninterpreted'),
                     'collected_after_finished_seconds': r['collected_after_finished_seconds'],
                     'session_copies': len(r['per_file']), 'root_sessions': len(roots), 'child_sessions': len(children),
                     'jsonl_object_rows': sum(p['jsonl_object_rows'] for p in r['per_file']),
                     'checks': r['counts'], 'receipt': path.name, 'receipt_sha256': sha(path),
                     'original_meta_sha256': r['original_meta_sha256'],
                     'original_observation_not_reclassified': r['original_observation_not_reclassified'],
                     'formal_effect': 'unchanged; no late recovery automatic admission'})
    current_drift = []
    for name, want in union.items():
        p = root / name
        if p.is_symlink():
            got = {'kind': 'symlink-not-followed', 'target_text_sha256': hashlib.sha256(os.readlink(p).encode()).hexdigest()}
        elif p.is_file():
            got = {'kind': 'regular', 'sha256': sha(p), 'bytes': p.stat().st_size}
        else:
            got = {'kind': 'missing'}
        if got != want:
            current_drift.append({'path': name, 'kind': 'changed-after-slot-audit', 'before': want, 'after': got})
    # Exact, explicitly provided companion: author semantics vs our current FS observation.
    rid = 'l4-20261029-cli-dsh-tb-cargo-plan-r3'
    rec = root / '3-表现现场/l4-20261029-cli/dsh/recoveries' / rid
    companion = rec / 'record-at-semantics.json'
    source = rec / 'recovery-record.json'
    before_companion, before_source = sha(companion), sha(source)
    c, source_doc = json.loads(companion.read_bytes()), json.loads(source.read_bytes())
    file = rec / 'session' / source_doc['files'][0]['path']
    st = file.stat()
    birth = dt.datetime.fromtimestamp(st.st_birthtime, dt.timezone.utc).isoformat() if hasattr(st, 'st_birthtime') else None
    mtime = dt.datetime.fromtimestamp(st.st_mtime, dt.timezone.utc).isoformat()
    companion_result = {'category': 'offline_recompute/late_archive_clock_semantics',
        'observed_at': dt.datetime.now().astimezone().isoformat(), 'run_id': rid,
        'author_companion_sha256': before_companion, 'original_record_sha256': before_source,
        'author_record_SHA_claim_matches_our_hash': before_source == c['original_record']['sha256_independently_recomputed_now'],
        'collected_at_field_present': 'collected_at' in source_doc,
        'original_record_at': source_doc.get('at'),
        'author_semantic_declaration': c['semantic_answer'],
        'reviewer_current_copy_birthtime_UTC': birth, 'reviewer_current_copy_mtime_UTC': mtime,
        'mtime_equals_birthtime_now': hasattr(st, 'st_birthtime') and st.st_mtime == st.st_birthtime,
        'collection_start_time': None, 'collection_start_status': 'unknown, not inferred from at/birthtime',
        'limits': ['Author inline-collector construction order is a declaration; no preserved collector source exists for independent reconstruction.',
                   'Current APFS copy creation metadata is independently observed, not an independently witnessed historical collection-start or completion clock.',
                   'Copy birthtime can constrain copy creation, but does not alone prove copying completed before the declared at value.',
                   'Copy mtime equals birthtime here; no source-mtime preservation or global-source read is claimed.'],
        'source_and_companion_unchanged': before_companion == sha(companion) and before_source == sha(source),
        'live_doc_drift': []}
    write_new(scope / 'cargo-r3-clock-companion-review.json', companion_result)
    assert not cross_drift and not current_drift
    total = sum(r['checks']['checks'] for r in rows)
    passed = sum(r['checks']['passed'] for r in rows)
    result = {'category': 'offline_recompute/late_archive_verification',
              'generated_at': dt.datetime.now().astimezone().isoformat(), 'merge_key': 'slot_id',
              'exactly_six_unique_frozen_slots': len(rows) == len({r['slot_id'] for r in rows}) == 6,
              'rows': rows, 'counts': {'identity_supported_slots': sum(r['identity_and_structure'] == 'supported' for r in rows),
                'collection_field_confirmed_late': sum(r['collection_time'] == 'confirmed_late_field' for r in rows),
                'collection_time_unknown_slots': sum(r['collection_time'] == 'unknown' for r in rows),
                'session_copies': sum(r['session_copies'] for r in rows),
                'checks': total, 'passed': passed, 'unknown_or_failed': total - passed},
              'protected_union_entries': len(union),
              'protected_union_manifest_sha256': hashlib.sha256(json.dumps(union, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
              'protected_union_rechecked_at_final_aggregation': True, 'live_doc_drift': cross_drift + current_drift,
              'original_formal_total_per_Lead_not_recomputed': 0,
              'formal_effect': 'none; original source/meta/gate/times/score/usage unchanged',
              'raw_content_or_credentials_exposed': False, 'global_original_sessions_read': False,
              'clock_companion_review': 'cargo-r3-clock-companion-review.json',
              'presentation_equivalence_proof': 'public-json-equivalence.json',
              'script_sha256': sha(Path(__file__))}
    write_new(scope / 'final-six-summary-01.json', result)
    print(json.dumps({'rows': len(rows), 'counts': result['counts'], 'protected_union_entries': len(union),
                      'drift_count': len(result['live_doc_drift']), 'collection_start_stays_unknown_for_cargo_r3': True}))


if __name__ == '__main__':
    main()
