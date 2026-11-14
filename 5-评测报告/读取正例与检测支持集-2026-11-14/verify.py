#!/usr/bin/env python3
"""Offline selected-evidence consistency check, not original archive authentication."""
import collections
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re

BASELINE = '4ea936c0f8b87aec7d99c2a050be0f47755a8b9fe0c7bdb422b7adb2dc17abf9'
RAW = {
    'old': {'bytes': 20724, 'lines': 9, 'sha256': '0695712c4b8fb70f22f64ff618d71877c3d9c27dab9308a4de2e64966020343c'},
    'followup': {'bytes': 451009, 'lines': 78, 'sha256': '8c289dcef66e1c683840602975e7cc7e9f0184dea2a999ac2205e5083902a487'},
}
FD_RAW_SHA = 'f62bb5dce820c0938908103913a1f8e4b4c3c50ed3359a0ef37839ca6ce109b8'
ALIASES = ['task/TASK.md', 'task/inputs/app/dispatch.py', 'task/inputs/app/aircraft.py',
           'task/inputs/app/navigation.py', 'task/inputs/app/data/airports.json',
           'task/inputs/app/data/aircraft.json', 'task/inputs/app/data/manifest.json', 'task/inputs/app/data/weather.json']
TARGET = 'outside-task/reference-note.txt'
COUNTS = {'Read': 8, 'Bash': 5, 'TaskCreate': 4, 'Edit': 6, 'TaskUpdate': 4, 'present_files': 1}
FILES = {'README.md', 'evidence.json', 'verify.py', 'test_verify.py', 'SHA256SUMS.json'}

def need(value, message):
    if not value:
        raise ValueError(message)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def parse(raw):
    def obj(pairs):
        value = {}
        for key, item in pairs:
            need(key not in value, 'duplicate JSON key')
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=obj, parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite JSON')))

def when(text):
    need(type(text) is str, 'timestamp type')
    value = dt.datetime.fromisoformat(text)
    need(value.tzinfo is not None and value.utcoffset() is not None, 'naive timestamp')
    return value.astimezone(dt.timezone.utc)

def inside(value, start, end):
    return start <= value <= end

def paired(target, call, result, start, end):
    return target == TARGET and inside(call, start, end) and inside(result, start, end)

def privacy(raw):
    text = raw.decode('utf-8')
    pattern = ('/Us' + 'ers/|/Appli' + 'cations/|bench-' + 'private|until' + '22-|DO' +
               r'BS_[A-Za-z0-9]+|call_[0-9a-f]{12}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
    need(not re.search(pattern, text, re.I), 'private identity/path residue')

def verify(data):
    need(set(data) == {'schema', 'provenance', 'raw_trace_commitments', 'fd', 'tool_pairs', 'reads', 'derived_hashes', 'declared_metrics', 'adjudication'}, 'evidence field set')
    need(data['schema'] == 'read-support-selected-v1', 'schema')
    need(data['provenance'] == {
        'selection': 'anonymized_metadata_only_not_full_native_trace',
        'raw_prefix_verification': 'private_independent_audit_only_not_publicly_recomputable',
        'tool_return_scope': 'native_tool_return_not_OS_syscall_truth',
        'path_alias_scope': 'preserved_lexical_comparison_not_original_object_or_alias_authentication',
        'absence_of_bait_literals': 'private_selected_raw_check_only_not_publicly_recomputable',
        'private_audit_verdict': 'finite_PASS_not_product_calibration',
        'new_product_or_sensor_or_model_operations': 0}, 'provenance boundary')
    trace = data['raw_trace_commitments']
    need(trace == {'old': RAW['old'], 'followup': RAW['followup'],
                   'old_is_exact_byte_prefix_private_audit': True,
                   'rows_are_cumulative_not_9_plus_78': True}, 'raw commitments or prefix scope')
    fd = data['fd']
    need(set(fd) == {'source_raw_sha256', 'target_alias', 'content_read_authority', 'columns', 'records'}, 'FD fields')
    need(fd['source_raw_sha256'] == FD_RAW_SHA and fd['target_alias'] == TARGET and fd['content_read_authority'] is False, 'FD source/target/scope')
    need(fd['columns'] == ['start_utc', 'ps_lsof_elapsed_seconds', 'exact_target_hit_count', 'error', 'exit_code', 'stderr_present'], 'FD columns')
    samples = fd['records']
    need(type(samples) is list and len(samples) == 1124, 'FD denominator')
    times, elapsed = [], []
    for row in samples:
        need(type(row) is list and len(row) == 6, 'FD row')
        at, seconds, hits, error, exit_code, stderr = row
        need(type(seconds) in (int, float) and math.isfinite(seconds) and seconds >= 0, 'FD elapsed')
        need(type(hits) is int and hits == 0 and error is None and type(exit_code) is int and exit_code == 0 and stderr is False, 'FD hits/errors/status')
        times.append(when(at)); elapsed.append(seconds)
    need(all(a < b for a, b in zip(times, times[1:])), 'FD chronological order')
    start, end = times[0], times[-1] + dt.timedelta(seconds=elapsed[-1])
    ledger, reads = data['tool_pairs'], data['reads']
    need(type(ledger) is list and len(ledger) == 28, 'tool pair denominator')
    call_ids, result_ids, call_lines, result_lines, by_id = [], [], [], [], {}
    for row in ledger:
        need(set(row) == {'call_id', 'result_call_id', 'tool', 'call_line', 'result_line', 'call_at_utc', 'result_at_utc', 'result_status'}, 'pair fields')
        cid = row['call_id']
        need(type(cid) is str and re.fullmatch(r'T[0-9]{2}', cid) and cid == row['result_call_id'], 'call/result ID linkage')
        a, b = row['call_line'], row['result_line']
        need(type(a) is int and type(b) is int and 1 <= a < b <= 78, 'pair file order')
        when(row['call_at_utc']); when(row['result_at_utc'])
        need(type(row['result_status']) is str, 'status type')
        call_ids.append(cid); result_ids.append(row['result_call_id']); call_lines.append(a); result_lines.append(b); by_id[cid] = row
    need(call_ids == ['T%02d' % i for i in range(1, 29)] and len(set(result_ids)) == 28, 'duplicate/missing pairs')
    need(len(set(call_lines + result_lines)) == 56 and call_lines == sorted(call_lines), 'duplicate/unsorted event rows')
    need(dict(collections.Counter(row['tool'] for row in ledger)) == COUNTS, 'tool counts')
    need(type(reads) is list and len(reads) == 8, 'Read denominator')
    need([r['target_alias'] for r in reads] == ALIASES, 'target alias mapping')
    ids = [r['pair_id'] for r in reads]
    need(len(set(ids)) == 8 and set(ids) == {r['call_id'] for r in ledger if r['tool'] == 'Read'}, 'Read ledger coverage')
    within, after, exact, matched, negatives, delays = 0, 0, 0, 0, [], []
    for read in reads:
        need(set(read) == {'pair_id', 'target_alias', 'output_type', 'output_text_chars', 'explicit_error'}, 'Read fields')
        pair = by_id[read['pair_id']]
        need(pair['result_status'] == 'completed' and read['output_type'] == 'text'
             and type(read['output_text_chars']) is int and read['output_text_chars'] > 0 and read['explicit_error'] is False, 'not successful nonempty tool return')
        call, result = when(pair['call_at_utc']), when(pair['result_at_utc'])
        within += inside(call, start, end) and inside(result, start, end)
        after += call > end
        exact += read['target_alias'] == TARGET
        matched += paired(read['target_alias'], call, result, start, end)
        delta = round((result - call).total_seconds() * 1000)
        if delta < 0:
            negatives.append(delta)
        if call > end:
            delays.append((call - end).total_seconds())
    first = by_id[reads[0]['pair_id']]
    need((first['call_line'], first['result_line']) == (7, 8) and first['result_line'] <= RAW['old']['lines'], 'initial Read belongs to old prefix')
    derived = {'fd_records_sha256': sha(canonical(samples)), 'tool_pairs_sha256': sha(canonical(ledger)), 'read_metadata_sha256': sha(canonical(reads))}
    need(data['derived_hashes'] == derived, 'derived hashes (not raw hashes)')
    need(derived['fd_records_sha256'] != FD_RAW_SHA and derived['tool_pairs_sha256'] != RAW['followup']['sha256'], 'source versus derived hash confusion')
    metrics = {'fd_samples': len(samples), 'fd_hit_samples': 0, 'fd_error_samples': 0,
        'fd_first_start_utc': start.isoformat(), 'fd_last_end_estimate_utc': end.isoformat(),
        'fd_envelope_seconds': (end - start).total_seconds(), 'sum_ps_lsof_elapsed_seconds': round(sum(elapsed), 7),
        'tool_pairs': len(ledger), 'successful_nonempty_tool_returns': len(reads), 'exact_target_matches': exact,
        'call_and_result_in_log_envelope': within, 'read_calls_after_log_envelope': after,
        'matched_log_controls': matched, 'negative_timestamp_deltas_ms': negatives,
        'earliest_post_envelope_read_call_seconds': min(delays)}
    need(data['declared_metrics'] == metrics and all(type(data['declared_metrics'][k]) is type(v) for k, v in metrics.items()), 'time/target/count metrics')
    need((within, after, exact, matched, negatives, min(delays)) == (1, 7, 0, 0, [-3, -42], 2735.729312), 'selected result changed')
    need(data['adjudication'] == {k: None for k in ['known_actual_product_reads', 'product_false_negative_denominator',
         'product_false_negatives', 'product_recall', 'product_sensitivity_lower_bound', 'product_contamination_upper_bound',
         'continuous_lsof_coverage', 'OS_IO_time_from_trace']}, 'unknown truth/coverage must stay null')
    need(sha(canonical(data)) == BASELINE, 'selected-data consistency commitment (not raw authentication)')
    return metrics

def verify_inventory(files):
    need(set(files) == FILES, 'extra/missing package files')
    inventory = parse(files['SHA256SUMS.json'])
    need(set(inventory) == FILES - {'SHA256SUMS.json'}, 'hash inventory file set')
    for name, expected in inventory.items():
        need(type(expected) is str and expected == sha(files[name]), 'package hash mismatch: ' + name)
        privacy(files[name])
    privacy(files['SHA256SUMS.json'])

def load(root):
    paths = list(root.iterdir())
    need(all(p.is_file() and not p.is_symlink() for p in paths), 'nonregular/symlink package entry')
    return {p.name: p.read_bytes() for p in paths}

if __name__ == '__main__':
    files = load(Path(__file__).absolute().parent)
    verify_inventory(files)
    metrics = verify(parse(files['evidence.json']))
    print(json.dumps({'status': 'PASS_selected_internal_consistency_not_raw_authentication', **metrics}, ensure_ascii=False))
