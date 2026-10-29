#!/usr/bin/env python3
"""Verify only an explicitly named DSH recovery sidecar and its finished run.
No global-session traversal/source reads, model/product calls, raw-text output,
answer inspection, meta/gate backfill, or new original/master is performed.
The zstd decompressor writes only to captured memory. Receipt contains hashes,
IDs, booleans, counts, timestamps and disclosed limits, never prompt/trace text.
"""
import argparse
from collections import Counter
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess

UTC = dt.timezone.utc
UUID_RE = re.compile(r'(?:session-)?[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
MAX_DECOMPRESSED_BYTES = 64 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def time_value(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return dt.datetime.fromtimestamp(value / 1000 if abs(value) > 100000000000 else value, UTC)
    if isinstance(value, str):
        return dt.datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(UTC)
    raise ValueError('unsupported time type')


def content_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return ''.join(b['text'] for b in content if isinstance(b, dict)
                       and b.get('type') == 'text' and isinstance(b.get('text'), str))
    return None


def first_user(events):
    for e in events:
        if e.get('type') == 'user/message':
            d = e.get('data') or {}
            return d.get('content') if 'content' in d else (d.get('message') or {}).get('content')
    return None


def string_leaves(value, path=''):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from string_leaves(v, path + '.' + k)
    elif isinstance(value, list):
        for v in value:
            yield from string_leaves(v, path + '[]')


def snapshot(paths, root):
    result = {}
    for p in sorted(set(paths)):
        name = str(p.relative_to(root))
        if p.is_symlink():
            result[name] = {'kind': 'symlink-not-followed', 'target_text_sha256': digest(os.readlink(p).encode())}
        elif p.is_file():
            result[name] = {'kind': 'regular', 'sha256': file_sha(p), 'bytes': p.stat().st_size}
        else:
            result[name] = {'kind': 'missing'}
    return result


def usage_summary(events):
    messages = [e for e in events if e.get('type') == 'assistant/message']
    usages = [e.get('data', {}).get('usage') for e in messages]
    available = [u for u in usages if isinstance(u, dict)]
    fields = {}
    for name in ('inputTokens', 'outputTokens', 'cacheReadTokens', 'cacheWriteTokens', 'reasoningTokens'):
        values = [u.get(name) for u in available]
        numeric = [v for v in values if isinstance(v, int) and not isinstance(v, bool) and v >= 0]
        fields[name] = {'present_numeric': len(numeric), 'explicit_zero': sum(v == 0 for v in numeric),
                        'missing': sum(name not in u for u in available), 'null': sum(name in u and u[name] is None for u in available),
                        'sum_if_all_messages_numeric': sum(numeric) if messages and len(numeric) == len(messages) else None}
    return {'assistant_message_records': len(messages), 'usage_dict_records': len(available),
            'fields': fields, 'interpretation': 'late committed assistant-message usage records, not original meta backfill or raw HTTP attempt denominator'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--run-id', required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    root = a.root.resolve()
    scope = root / '5-评测报告/L4首请求前评审-2026-10-29/late-archive-verification'
    out = a.out.resolve()
    assert out.parent == scope and not out.exists(), 'new receipt must stay in assigned reviewer scope'
    plan = json.loads((root / '1-评测方案/自动循环L4-2026-10-29/plan.json').read_bytes())
    matches = [s for s in plan['product_slots'] if s.get('product') == 'dsh' and s.get('run_id') == a.run_id]
    assert len(matches) == 1, 'explicit run must be a single frozen DSH slot'
    slot = matches[0]
    batch = root / '3-表现现场/l4-20261029-cli/dsh'
    rec = batch / 'recoveries' / a.run_id
    run = root / slot['evidence_dir']
    assert rec.is_dir() and rec.resolve() == rec and run.is_dir() and run.resolve() == run
    record_path = rec / 'recovery-record.json'
    record = json.loads(record_path.read_bytes())
    copies = []
    for f in record['files']:
        rel = PurePosixPath(f['path'])
        assert not rel.is_absolute() and '..' not in rel.parts and str(rel) == f['path']
        p = rec / 'session' / f['path']
        assert p.suffix == '.zstd' and p.is_file() and not p.is_symlink() and p.resolve() == p
        copies.append((f, p))
    assert len({str(p) for _, p in copies}) == len(copies) and copies
    # Only this explicitly finished run and these explicitly named copies are traversed.
    fixed = [root / '1-评测方案/自动循环L4-2026-10-29' / n for n in
             ('runtime-binding.json', 'execution-manifest.json', 'PREREGISTRATION.md', 'plan.json', 'contract.json')]
    fixed += [batch / 'tools/lab.py', root / '1-评测方案/工具链/l4-execution/gate.py', record_path]
    def protected_paths():
        return fixed + [p for _, p in copies] + [p for p in run.rglob('*') if p.is_symlink() or p.is_file()]
    protected_before = snapshot(protected_paths(), root)
    meta_raw = (run / 'meta.json').read_bytes()
    meta = json.loads(meta_raw)
    prompt = (run / 'prompt.txt').read_bytes()
    raw_stdout = (run / 'agent.jsonl').read_bytes()
    started, finished = time_value(meta['started_at']), time_value(meta['finished_at'])
    try:
        collected = time_value(record.get('collected_at'))
    except (TypeError, ValueError, OverflowError):
        collected = None  # record.at is not silently promoted into collected_at
    low, high = started - dt.timedelta(seconds=5), finished + dt.timedelta(seconds=5)
    binding = json.loads((root / '1-评测方案/自动循环L4-2026-10-29/runtime-binding.json').read_bytes())
    checks = []
    def check(label, passed, details=None):
        checks.append({'id': label, 'pass': bool(passed), 'detail': details})
    check('recovery-record-identities-match-explicit-slot', record.get('run_id') == record.get('slot_id') == a.run_id)
    check('original-meta-identities-match-frozen-slot', meta.get('run_id') == meta.get('slot_id') == a.run_id)
    check('original-E-binding-unchanged', meta.get('preregistration_commit') == binding['execution_seal_commit'] and meta.get('registered_at') == binding['registered_at'])
    check('collected-at-is-truly-later-than-finished', collected is not None and collected > finished,
          {'field_present': 'collected_at' in record, 'record_at_is_not_a_substitute': record.get('at')})
    check('original-prompt-sha-matches-original-meta', digest(prompt) == meta.get('prompt_sha256'))
    check('original-stdout-sha-matches-original-meta', digest(raw_stdout) == meta.get('stdout_sha256'))
    expected_marker = '--' + meta['workspace'].strip('/').replace('/', '-') + '--'
    check('record-dir-marker-is-single-DSH-exact-cwd-encoding', record.get('binding', {}).get('expected_dir_name') == expected_marker)
    decoder = shutil.which('zstd')
    assert decoder, 'local compression utility is required; no product fallback permitted'
    sessions, per_file = {}, []
    for f, p in copies:
        compressed_sha = file_sha(p)
        row = {'copy': str(p.relative_to(root)), 'declared_source_path_not_read': f.get('source'),
               'compressed_sha256': compressed_sha, 'compressed_bytes': p.stat().st_size,
               'copy_mtime': dt.datetime.fromtimestamp(p.stat().st_mtime, UTC).isoformat(),
               'source_stable_after_copy_claim_from_record': f.get('source_stable_after_copy')}
        check('copy-hash-chain:' + f['path'], compressed_sha == f.get('sha256') == f.get('copy_sha256')
              and p.stat().st_size == f.get('bytes') == f.get('copy_bytes'))
        check('copy-mtime-in-original-window:' + f['path'], low.timestamp() <= p.stat().st_mtime <= high.timestamp())
        q = subprocess.run([decoder, '-q', '-dc', '--', str(p)], capture_output=True, timeout=120)
        row['decompress_exit_code'] = q.returncode
        row['decompress_stderr_sha256'] = digest(q.stderr)
        check('zstd-decompress-clean:' + f['path'], q.returncode == 0 and len(q.stdout) <= MAX_DECOMPRESSED_BYTES)
        if q.returncode or len(q.stdout) > MAX_DECOMPRESSED_BYTES:
            row['status'] = 'unknown'
            per_file.append(row)
            continue
        row['decompressed_bytes'] = len(q.stdout)
        row['decompressed_sha256'] = digest(q.stdout)
        events, bad = [], []
        for i, line in enumerate(q.stdout.splitlines(), 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                if not isinstance(item, dict):
                    raise TypeError('not an object')
                events.append(item)
            except Exception as exc:
                bad.append({'line': i, 'error_type': type(exc).__name__})
        row['jsonl_object_rows'] = len(events)
        row['bad_jsonl_rows'] = bad
        row['ends_in_newline'] = q.stdout.endswith(b'\n')
        check('every-jsonl-record-parseable:' + f['path'], not bad and bool(events))
        headers = [e for e in events if e.get('type') == 'session']
        check('one-session-header:' + f['path'], len(headers) == 1)
        if len(headers) != 1:
            row['status'] = 'unknown'
            per_file.append(row)
            continue
        h = headers[0]
        sid = h.get('id')
        row.update(session_id=sid, delegation_depth=h.get('delegationDepth'),
                   cwd_exact_original_meta=h.get('cwd') == meta['workspace'])
        check('header-ID-matches-copy-subdir:' + f['path'], sid == PurePosixPath(f['path']).parts[0])
        check('header-cwd-exact-original-workspace:' + f['path'], h.get('cwd') == meta['workspace'])
        check('session-UUID-present-in-original-stdout:' + f['path'], isinstance(sid, str) and sid.encode() in raw_stdout)
        observed_times, malformed = [], 0
        for e in events:
            for key in ('createdAt', 'time'):
                if key in e:
                    try:
                        observed_times.append(time_value(e[key]))
                    except Exception:
                        malformed += 1
        row['event_time_min'] = min(observed_times).isoformat() if observed_times else None
        row['event_time_max'] = max(observed_times).isoformat() if observed_times else None
        row['malformed_time_fields'] = malformed
        check('event-times-within-original-window:' + f['path'], not malformed and observed_times
              and min(observed_times) >= low and max(observed_times) <= high)
        counts = Counter(e.get('type') for e in events)
        row['event_type_counts'] = dict(counts)
        row['last_event_type'] = events[-1].get('type') if events else None
        check('trace-has-terminal-turn-end:' + f['path'], events[-1].get('type') == 'turn/end')
        calls = Counter((e.get('data') or {}).get('callId') for e in events if e.get('type') == 'tool/call')
        results = Counter(((e.get('data') or {}).get('message') or {}).get('toolCallId')
                          for e in events if e.get('type') == 'tool/result' and e.get('surfaceOp') in (None, 'append'))
        row['tool_call_records'] = sum(calls.values())
        row['tool_result_append_records'] = sum(results.values())
        row['unmatched_call_ID_count'] = sum((calls - results).values())
        row['unmatched_result_ID_count'] = sum((results - calls).values())
        check('tool-call-result-ID-multisets-close:' + f['path'], calls == results and None not in calls)
        c = first_user(events)
        initial = content_text(c)
        row['initial_user_text_sha256'] = digest(initial.encode()) if initial is not None else None
        row['initial_user_text_bytes'] = len(initial.encode()) if initial is not None else None
        row['root_prompt_exact_if_treated_as_root'] = initial is not None and initial.encode() == prompt
        row['late_usage_commitpoint_summary'] = usage_summary(events)
        sessions[sid] = {'header': h, 'events': events, 'content': c, 'row': row,
                         'decompressed_text_for_UUID_link_only': q.stdout}
        per_file.append(row)
    roots = [v for v in sessions.values() if v['header'].get('delegationDepth') == 0
             and not v['header'].get('parentSession')]
    check('exactly-one-root-session', len(roots) == 1)
    root_session = roots[0] if len(roots) == 1 else None
    if root_session:
        check('root-first-user-prompt-byte-exact-original-prompt', root_session['row']['root_prompt_exact_if_treated_as_root'])
    for sid, s in sessions.items():
        if s is root_session:
            s['row']['identity_role'] = 'root'
            continue
        s['row']['identity_role'] = 'child-not-root-prompt'
        parent_ids = UUID_RE.findall(json.dumps(s['header'].get('parentSession')))
        parents = [v for k, v in sessions.items() if k in parent_ids]
        check('child-parent-ID-resolves-in-these-copies:' + sid, len(parents) == 1)
        linked = []
        blocks = s['content'] if isinstance(s['content'], list) else []
        if len(parents) == 1:
            parent = parents[0]
            check('parent-trace-mentions-child-UUID:' + sid, sid.encode() in parent['decompressed_text_for_UUID_link_only'])
            for e in parent['events']:
                if e.get('type') != 'tool/call':
                    continue
                d = e.get('data') or {}
                args = d.get('arguments')
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        continue
                for path, value in string_leaves(args):
                    if not path.endswith('.prompt'):
                        continue
                    for i, block in enumerate(blocks):
                        if isinstance(block, dict) and block.get('type') == 'text' and block.get('text') == value:
                            linked.append({'parent_call_id': d.get('callId'), 'argument_path': path,
                                           'child_initial_block_index': i, 'byte_exact': True,
                                           'prompt_bytes': len(value.encode()), 'prompt_sha256': digest(value.encode())})
        s['row']['parent_session_IDs'] = parent_ids
        s['row']['delegated_prompt_exact_links'] = linked
        check('child-initial-task-block-byte-exact-parent-launch-prompt:' + sid, bool(linked))
    check('record-source-stability-claims-present-not-independently-reread',
          record.get('all_sources_stable') is True and all(f.get('source_stable_after_copy') is True for f, _ in copies))
    protected_after = snapshot(protected_paths(), root)
    drift = [{'path': k, 'before': protected_before.get(k), 'after': protected_after.get(k)}
             for k in sorted(set(protected_before) | set(protected_after)) if protected_before.get(k) != protected_after.get(k)]
    check('all-specified-originals-copies-record-and-source-SHA-unchanged', not drift)
    failed = [c['id'] for c in checks if not c['pass']]
    original_observation = {k: meta.get(k) for k in ('status', 'integrity_verdict', 'score_status', 'weighted', 'registered_at', 'started_at', 'finished_at')}
    original_observation['judge_counts'] = {k: (meta.get('judge') or {}).get(k) for k in ('correct', 'n_tasks')}
    original_observation['usage_requests'] = (meta.get('usage') or {}).get('requests')
    original_observation['session_scan_lines'] = ((meta.get('integrity') or {}).get('session_scan') or {}).get('lines')
    result = {'category': 'offline_recompute/late_archive_verification', 'run_id': a.run_id, 'slot_id': slot['slot_id'],
              'verified_at': dt.datetime.now().astimezone().isoformat(), 'collected_at': record.get('collected_at'),
              'collector_record_at_separate_uninterpreted': record.get('at'),
              'collected_after_finished_seconds': (collected - finished).total_seconds() if collected is not None else None,
              'status': 'identity_and_structural_completeness_supported' if not failed else 'unknown',
              'passed': not failed, 'counts': {'checks': len(checks), 'passed': len(checks) - len(failed), 'unknown_or_failed': len(failed)},
              'reviewer_script_sha256': file_sha(Path(__file__)), 'recovery_record_sha256': file_sha(record_path),
              'original_prompt_sha256': digest(prompt), 'original_stdout_sha256': digest(raw_stdout), 'original_meta_sha256': digest(meta_raw),
              'per_file': per_file, 'checks': checks, 'protected_before': protected_before, 'protected_after': protected_after,
              'live_doc_drift': drift, 'original_observation_not_reclassified': original_observation,
              'formal_effect': 'none: original meta/gate/score/times/usage/integrity verdict remain untouched; late recovery is not automatic formal admission',
              'not_a_new_original_master': True, 'read_original_global_session_sources': False,
              'no_raw_prompt_trace_or_credentials_in_receipt': True,
              'limits': [
                  'Original global-session source before/after stability is the collector receipt claim; this reviewer hashes only explicitly authorized copies and never rereads/scans global sessions.',
                  'Copy mtime is copy metadata; embedded session event times, original stdout UUIDs and prompt hashes supply independent linkage, not a trusted timestamp/signature.',
                  'Child initial user message includes its delegated task/context, not the root prompt; its task block must match the actual parent launch argument exactly.',
                  'Clean zstd/JSONL, terminal records and paired tool IDs support structural completeness, not proof of no omitted internal requests or semantic absence of contamination.',
                  'Usage sums are late committed-message observations only; missing/null/explicit zero remain separate and original usage is never backfilled.',
                  'No semantic contamination adjudication, scoring, formal reclassification or product rerun is performed.']}
    with out.open('x') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({'run_id': a.run_id, 'status': result['status'], 'counts': result['counts'],
                      'protected_entries': len(protected_before), 'drift_count': len(drift),
                      'unknown_reasons': failed, 'out': str(out)}, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == '__main__':
    raise SystemExit(main())
