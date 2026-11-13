#!/usr/bin/env python3
"""Clean-room, stdlib-only replay of the documented abstract semantics.
No proprietary module is imported, extracted, or executed. Not a product runner.
"""
import hashlib
import json
import math
from pathlib import Path
import re

BASELINE = 'e74283080fced65024d771e8d4eb4353ad9d8444cba2c51d7d058088fe9bb27b'
POLICY = {'default_lines': 2000, 'line_utf16_cap': 2000, 'maximum': 20000,
          'file_size_gate_bytes': 262144, 'fixed_prefix_bytes': 169860,
          'units': 'UTF16_code_units_with_BMP_4E00_9FA5_weighted_separate_ceil'}
TRANSFORM = 'ASCII non-CR/LF bytes replaced by x; CR/LF positions unchanged'
EMPTY = ('<system-reminder data-role="tool-hint">Warning: the file exists but is '
         'shorter than the provided offset (1). The file has 1 lines.</system-reminder>')


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def parse(raw):
    def pairs(items):
        d = {}
        for k, v in items:
            need(k not in d, 'duplicate_JSON_key')
            d[k] = v
        return d
    def nonfinite(value):
        raise ValueError('nonfinite_JSON')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)


def u16(text):
    return len(text.encode('utf-16-le', 'surrogatepass')) // 2


def utf8(text):
    # Match replacement of an unpaired UTF16 surrogate when measuring UTF8 bytes.
    return text.encode('utf-16-le', 'surrogatepass').decode('utf-16-le', 'replace').encode('utf-8')


def window(text):
    need(len(utf8(text)) <= 262144, 'default_file_size_gate')
    if text == '':
        return EMPTY
    selected = re.split(r'\r?\n', text)[:2000]
    clipped = []
    for line in selected:
        if u16(line) > 2000:
            line = line.encode('utf-16-le', 'surrogatepass')[:4000].decode('utf-16-le', 'surrogatepass') + '... [truncated]'
        clipped.append(line)
    return '\n'.join(clipped)


def hybrid(text):
    h = sum('\u4e00' <= c <= '\u9fa5' for c in text)
    return math.ceil(h / 1.8) + math.ceil((u16(text) - h) / 4)


def units(text):
    return {'utf8_bytes': len(utf8(text)), 'utf16_units': u16(text), 'codepoints': len(text),
            'split_lines': len(re.split(r'\r?\n', text)), 'LF': text.count('\n'), 'CR': text.count('\r')}


def metrics(text):
    out = window(text)
    return {'source_units': units(text), 'window_units': units(out), 'window_sha256': sha(utf8(out)),
            'selected_lines': min(2000, len(re.split(r'\r?\n', text))),
            'lines_truncated': sum(u16(s) > 2000 for s in re.split(r'\r?\n', text)[:2000]),
            'hybrid_estimate': hybrid(out), 'full_file_bytes_div4': math.ceil(len(utf8(text)) / 4),
            'fixed_169860_bytes_div4': math.ceil(min(len(utf8(text)), 169860) / 4),
            'window_utf8_div4': math.ceil(len(utf8(out)) / 4),
            'window_utf16_div4': math.ceil(u16(out) / 4), 'window_codepoints_div4': math.ceil(len(out) / 4)}


def baseline(data):
    # Published commitments, not an authenticator for undisclosed original archives.
    return sha(canonical({'ledger': data['ledger'], 'missing_or_bad_setup': data['missing_or_bad_setup'],
                          'observations': data['points'], 'owner_commitments': data['owner_commitments']}))


def privacy(raw):
    text = raw.decode('utf-8')
    # Split literals so the scanner does not match its own source.
    forbidden = ('/Users' + '/', '/Applications' + '/', 'bench-' + 'private',
                 'until22' + '-', 'ring' + '69', 'ring' + '65', 'session' + 'Id',
                 'Authorization' + ':', 'Bearer' + ' ', 'sk' + '-live-')
    need(not any(s.lower() in text.lower() for s in forbidden), 'private_identifier_or_secret_residue')


def verify(data, files):
    need(data['schema'] == 'read-window-derived-evidence-v1', 'schema')
    need(canonical(data['policy']) == canonical(POLICY), 'policy_or_unit_changed')
    need(data['provenance'] == {'kind': 'anonymized_derived_not_original', 'raw_http_included': False,
         'proprietary_source_included': False, 'source_pin_is_runtime_attestation': False,
         'unicode_product_validation': False, 'new_product_n': 0, 'prior_unicode_attempt': 'unknown_stopped',
         'scientific_audit_status': 'pending_at_candidate_generation'}, 'provenance')
    need(baseline(data) == BASELINE, 'observed_commitment_changed')
    points = data['points']
    need(len(points) == 13 and [p['id'] for p in points] == ['P%02d' % i for i in range(1, 14)], 'missing_or_duplicate_point')
    need(len({p['session'] for p in points}) == 12, 'parallel_sources_not_independent_sessions')
    ledger = data['ledger']
    need(len(ledger) == 23 and len({x['read'] for x in ledger}) == 23, 'Read_denominator')
    need(sum(x['qualified'] for x in ledger) == 13 and sum(not x['qualified'] for x in ledger) == 10, 'excluded_denominator')
    need(len(data['missing_or_bad_setup']) == 5, 'missing_setup_denominator')
    totals = dict.fromkeys(('hybrid_estimate', 'full_file_bytes_div4', 'fixed_169860_bytes_div4',
                          'window_utf8_div4', 'window_utf16_div4', 'window_codepoints_div4'), 0)
    for p in points:
        need(p['source_file'] == 'fixtures/' + p['id'] + '.txt', 'source_alias')
        raw = files[p['source_file']]
        need(set(raw) <= {10, 13, 120}, 'fixture_not_ASCII_anonymized')
        need(sha(raw) == p['derived_source_sha256'] and p['derived_source_sha256'] != p['original_source_sha256'], 'original_vs_derived_hash')
        need(p['transformation'] == TRANSFORM and p['public_source_is_original'] is False, 'unmarked_transform')
        m = metrics(raw.decode('ascii'))
        need(m == p['derived_metrics'], 'window_coverage_units_or_formula')
        need(m['source_units'] == p['original_source_units'] and m['window_units'] == p['original_window_units'], 'transform_geometry_not_preserved')
        need(m['lines_truncated'] == 0 and m['source_units']['utf8_bytes'] < 262144, 'cohort_scope')
        dec = p['declaration']
        need(type(dec['estimate']) is int and type(dec['maximum']) is int and dec['maximum'] == 20000, 'declaration_types_or_threshold')
        expected = ('File content (estimated %d tokens) exceeds maximum allowed tokens (%d). Please use offset '
                    'and limit parameters to read specific portions of the file, or use the GrepTool to search for specific content.') % (dec['estimate'], dec['maximum'])
        need(dec['text'] == expected and dec['status'] == 'incomplete', 'declaration_fragment')
        need(m['hybrid_estimate'] == dec['estimate'], 'estimate_mismatch')
        matching = [x for x in ledger if x['read'] == p['read']]
        need(len(matching) == 1 and matching[0]['qualified'] is True and matching[0]['session'] == p['session']
             and matching[0]['arguments_alias'] == {'file_path': p['id']} and not matching[0]['exclusion_reasons'], 'parameter_or_ledger_binding')
        for key in totals:
            totals[key] += m[key] == dec['estimate']
    need(totals == {'hybrid_estimate': 13, 'full_file_bytes_div4': 8, 'fixed_169860_bytes_div4': 10,
                  'window_utf8_div4': 13, 'window_utf16_div4': 13, 'window_codepoints_div4': 13}, 'candidate_comparison')
    need(data['comparison'] == totals, 'reported_comparison')
    need(points[7]['derived_metrics']['window_units']['utf8_bytes'] == 115910
         and points[7]['declaration']['estimate'] * 4 == 115912, 'ceil_upper_bound_not_coverage')
    for path, raw in files.items():
        need(not Path(path).is_absolute() and '..' not in Path(path).parts, 'nonlocal_path')
        privacy(raw)
    return {'qualified_declarations': 13, 'qualified_sessions': 12, 'Read_rows': 23,
            'excluded_Read_rows': 10, 'missing_or_bad_setup': 5, 'matches': totals, 'new_product_n': 0,
            'scope': 'derived_geometry_and_published_commitments_not_original_archive_authentication'}


def verify_inventory(files):
    inventory = parse(files['SHA256SUMS.json'])
    need(set(inventory) == set(files) - {'SHA256SUMS.json'}, 'incomplete_inventory')
    need(all(sha(files[k]) == v for k, v in inventory.items()), 'inventory_hash_changed')


def load(root):
    need(not root.is_symlink(), 'symlink_root')
    files = {}
    for p in root.rglob('*'):
        need(not p.is_symlink(), 'symlink_member')
        if p.is_file():
            files[p.relative_to(root).as_posix()] = p.read_bytes()
    verify_inventory(files)
    return parse(files['evidence.json']), files


if __name__ == '__main__':
    d, f = load(Path(__file__).absolute().parent)
    print(json.dumps(verify(d, f), ensure_ascii=False, indent=2))
