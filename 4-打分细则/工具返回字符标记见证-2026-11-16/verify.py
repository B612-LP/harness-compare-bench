#!/usr/bin/env python3
"""Offline exploratory boundary witnesses; never execute archive commands.
Public mode checks sealed, content-free arithmetic, not private string truth.
Archive mode rebuilds old source links and exact new string relations.
All outputs are exclusive new files; stdout is only a summary.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BASELINE = '50c073c084006c0bfd5f8b79db3bc495e842847b'
PROTOCOL_SHA = 'c7c28661bf2a7c553ee0fc69e3f3748536cc3df7799c97c1466aaa9f7a4c36ff'
EVIDENCE_SHA = 'a6d6ffa356858a6109f309ca643aa44f01865b25ba8d082b71fdcb614893b7f2'
PREVIOUS = '4-打分细则/工具返回渲染与裁剪分账-2026-11-16'
PINS = {
    PREVIOUS + '/README.md': 'd828bfb8b573d6a0f0a42cba45c522c7447c2a42566f44f2e88b137469de3eb7',
    PREVIOUS + '/verify.py': '052e55c67367876ccf472024c720d118426194822501d3d1dd3afd717d6fd683',
    PREVIOUS + '/evidence.json': '0522591d24a088d90eeff62fce7bb7dc5f23107dfc88dab287e8f44b2bc6ed79',
    PREVIOUS + '/result.json': '625d67726b8e99ebd325ea45ce045083ab016033e9d16b666e2bad7ef0887abc',
}
WARNING = re.compile(r'\AWarning: truncated output \(original token count: [0-9]+\)\n')
TOTAL = re.compile(r'\ATotal output lines: [0-9]+\n\n')
MARKER = re.compile(r'…([0-9]+) chars truncated…')
KINDS = ('EXACT', 'CHAR-MARKED-BOUNDARY-WITNESS', 'UNEXPLAINED')
REASONS = ('EXACT', 'BOUNDARY-WITNESS', 'HEADER-UNKNOWN', 'WARNING-MISMATCH',
           'NO-MARKER', 'MULTIPLE-MARKERS', 'EMPTY-RETAIN', 'BOUNDARY-MISMATCH',
           'OVERLAP-OR-NO-DELETION')
UNITS = ('bytes', 'codepoints', 'utf16_units')


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def document(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')


def pairs(values):
    result = {}
    for key, value in values:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def nonfinite(_value):
    raise ValueError('nonfinite JSON number')


def finite_float(text):
    value = float(text)
    require(value == value and value not in (float('inf'), float('-inf')), 'nonfinite JSON number')
    return value


def loads(raw):
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite, parse_float=finite_float)


def keys(value, expected):
    require(isinstance(value, dict) and set(value) == set(expected), 'unexpected object schema')


def integer(value, minimum=0):
    require(type(value) is int and value >= minimum, 'invalid integer')


def digest(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None, 'invalid SHA256')


def safe_path(root, relative):
    rel = Path(relative)
    require(not rel.is_absolute() and '..' not in rel.parts, 'unsafe relative path')
    target = (root / rel).resolve()
    require(root.resolve() in target.parents, 'path escapes root')
    return target


def pinned(root, relative, expected):
    raw = safe_path(root, relative).read_bytes()
    require(sha(raw) == expected, 'pinned source SHA mismatch: ' + relative)
    return raw


def describe(text):
    require(isinstance(text, str), 'not text')
    raw = text.encode('utf-8')
    return {'bytes': len(raw), 'codepoints': len(text),
            'utf16_units': len(text.encode('utf-16-le')) // 2, 'sha256': sha(raw)}


def check_desc(value):
    keys(value, ('bytes', 'codepoints', 'utf16_units', 'sha256'))
    for unit in UNITS:
        integer(value[unit])
    digest(value['sha256'])
    c, b, u = value['codepoints'], value['bytes'], value['utf16_units']
    require(c <= u <= 2 * c and u <= b <= 4 * c, 'impossible text unit lengths')
    if c == 0:
        require(value == describe(''), 'empty descriptor mismatch')


def intervals(a, prefix, suffix):
    return {unit: {'head': [0, prefix[unit]],
                   'deleted': [prefix[unit], a[unit] - suffix[unit]],
                   'tail': [a[unit] - suffix[unit], a[unit]]} for unit in UNITS}


def classify(body, aggregate):
    require(body is None or isinstance(body, str), 'body is not text')
    require(isinstance(aggregate, str), 'aggregate is not text')
    reason = 'HEADER-UNKNOWN'
    if body is not None:
        if body == aggregate:
            return {'kind': 'EXACT', 'reason': 'EXACT', 'witness': None}
        warning = WARNING.match(body)
        reason = 'WARNING-MISMATCH'
        if warning:
            warning_text, rest = body[:warning.end()], body[warning.end():]
            total = TOTAL.match(rest)
            total_text = rest[:total.end()] if total else ''
            rest = rest[len(total_text):]
            markers = list(MARKER.finditer(rest))
            reason = 'NO-MARKER' if not markers else 'MULTIPLE-MARKERS'
            if len(markers) == 1:
                marker = markers[0]
                head, tail = rest[:marker.start()], rest[marker.end():]
                reason = 'EMPTY-RETAIN'
                if head and tail:
                    reason = 'BOUNDARY-MISMATCH'
                    if aggregate.startswith(head) and aggregate.endswith(tail):
                        reason = 'OVERLAP-OR-NO-DELETION'
                        if len(head) + len(tail) < len(aggregate):
                            deleted = aggregate[len(head):len(aggregate) - len(tail)]
                            w = {name: describe(value) for name, value in (
                                ('prefix', head), ('suffix', tail), ('deleted', deleted),
                                ('warning', warning_text), ('total', total_text), ('marker', marker.group()))}
                            w['marker_declared_N'] = int(marker.group(1))
                            w['marker_digit_count'] = len(marker.group(1))
                            w['unit_matches'] = {u: w['marker_declared_N'] == w['deleted'][u] for u in UNITS}
                            w['source_intervals'] = intervals(describe(aggregate), w['prefix'], w['suffix'])
                            for unit in UNITS:
                                require(describe(body)[unit] == describe(aggregate)[unit] - w['deleted'][unit] + sum(w[n][unit] for n in ('warning', 'total', 'marker')), 'internal witness sum mismatch')
                            return {'kind': 'CHAR-MARKED-BOUNDARY-WITNESS', 'reason': 'BOUNDARY-WITNESS', 'witness': w}
    return {'kind': 'UNEXPLAINED', 'reason': reason, 'witness': None}


def sources(root):
    bindings = dict(PINS)
    bindings[str(HERE.relative_to(ROOT) / 'README.md')] = PROTOCOL_SHA
    raw = {name: pinned(root, name, expected) for name, expected in bindings.items()}
    spec = importlib.util.spec_from_file_location('pinned_tool_return_render', safe_path(root, PREVIOUS + '/verify.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    reference_rows = module.references(root)
    previous = loads(raw[PREVIOUS + '/evidence.json'])
    module.validate_evidence(previous, reference_rows)
    prior_result = loads(raw[PREVIOUS + '/result.json'])
    require(module.document(module.result_for(previous, PINS[PREVIOUS + '/evidence.json'])) == raw[PREVIOUS + '/result.json'], 'previous full result mismatch')
    return module, previous, prior_result, bindings, reference_rows


def make_record(old, body, aggregate):
    relation = classify(body, aggregate)
    return {'slot': old['slot'], 'occurrence': old['occurrence'],
            'source': old['source'], 'lines': old['lines'],
            'prior_record_sha256': sha(canon(old)), 'prior_kind': old['conversion']['kind'],
            'utf16_units': {'A': describe(aggregate)['utf16_units'], 'B': None if body is None else describe(body)['utf16_units']},
            **relation}


def rebuild(root, archive_root, context=None):
    module, previous, prior_result, bindings, reference_rows = context or sources(root)
    require(module.canon(module.rebuild(archive_root, reference_rows)) == module.canon(previous), 'previous raw projection changed')
    cache, records = {}, []
    for old in previous['records']:
        slot = old['slot']
        if slot not in cache:
            relative, expected = module.ARCHIVE_SOURCES[slot]
            raw = pinned(archive_root, relative, expected)
            cache[slot] = dict(module.parse_trace(raw))
        events = cache[slot]
        output = events[old['lines']['output']]['payload']
        execution = events[old['lines']['execution']]['payload']['item']
        _, body = module.split_header(output['output'])
        records.append(make_record(old, body, execution['aggregated_output']))
    for relative, expected in module.ARCHIVE_SOURCES.values():
        pinned(archive_root, relative, expected)
    return {'schema': 'char-marker-boundary-evidence-v1', 'baseline_commit': BASELINE,
            'protocol_sha256': PROTOCOL_SHA, 'public_sources': bindings, 'records': records}


def validate(evidence, previous, bindings):
    keys(evidence, ('schema', 'baseline_commit', 'protocol_sha256', 'public_sources', 'records'))
    require(evidence['schema'] == 'char-marker-boundary-evidence-v1' and evidence['baseline_commit'] == BASELINE and evidence['protocol_sha256'] == PROTOCOL_SHA, 'evidence contract mismatch')
    require(evidence['public_sources'] == bindings, 'source bindings mismatch')
    require(isinstance(evidence['records'], list) and len(evidence['records']) == len(previous['records']) == 112, 'record coverage mismatch')
    for row, old in zip(evidence['records'], previous['records']):
        keys(row, ('slot', 'occurrence', 'source', 'lines', 'prior_record_sha256', 'prior_kind', 'utf16_units', 'kind', 'reason', 'witness'))
        require(all(row[k] == old[k] for k in ('slot', 'occurrence', 'source', 'lines')), 'source record order/identity mismatch')
        require(type(row['occurrence']) is int and row['prior_record_sha256'] == sha(canon(old)) and row['prior_kind'] == old['conversion']['kind'], 'previous record commitment mismatch')
        require(row['kind'] in KINDS and row['reason'] in REASONS, 'invalid classification')
        keys(row['utf16_units'], ('A', 'B'))
        planes = {}
        for name in ('A', 'B'):
            value, u = old['planes'][name], row['utf16_units'][name]
            if value is None:
                require(u is None, 'unknown body has units')
                planes[name] = None
            else:
                integer(u)
                require(value['characters'] <= u <= 2 * value['characters'] and u <= value['bytes'], 'impossible UTF16 length')
                planes[name] = {'bytes': value['bytes'], 'codepoints': value['characters'], 'utf16_units': u}
        exact = old['planes']['B'] == old['planes']['A']
        require((row['kind'] == 'EXACT') == exact, 'EXACT relation disagrees with old planes')
        if exact:
            require(row['reason'] == 'EXACT' and row['witness'] is None and planes['A'] == planes['B'], 'invalid exact witness')
        elif row['kind'] == 'UNEXPLAINED':
            require(row['reason'] not in ('EXACT', 'BOUNDARY-WITNESS') and row['witness'] is None, 'invalid unknown witness')
        else:
            require(row['reason'] == 'BOUNDARY-WITNESS' and planes['B'] is not None, 'invalid boundary state')
            w = row['witness']
            keys(w, ('prefix', 'suffix', 'deleted', 'warning', 'total', 'marker', 'marker_declared_N', 'marker_digit_count', 'unit_matches', 'source_intervals'))
            for name in ('prefix', 'suffix', 'deleted', 'warning', 'total', 'marker'):
                check_desc(w[name])
            integer(w['marker_declared_N'])
            integer(w['marker_digit_count'], 1)
            require(len(str(w['marker_declared_N'])) <= w['marker_digit_count'], 'invalid marker digit count')
            require(w['marker'] == describe('…' + str(w['marker_declared_N']).zfill(w['marker_digit_count']) + ' chars truncated…'), 'marker descriptor mismatch')
            require(all(w[n]['codepoints'] > 0 for n in ('prefix', 'suffix', 'deleted')), 'empty retain or deletion')
            warning_digits = w['warning']['bytes'] - len('Warning: truncated output (original token count: )\n')
            require(warning_digits >= 1 and len(set(w['warning'][u] for u in UNITS)) == 1, 'bad warning units')
            total_digits = w['total']['bytes'] - len('Total output lines: \n\n')
            require((w['total']['bytes'] == 0 or total_digits >= 1) and len(set(w['total'][u] for u in UNITS)) == 1, 'bad total units')
            require(w['unit_matches'] == {u: w['marker_declared_N'] == w['deleted'][u] for u in UNITS} and all(type(v) is bool for v in w['unit_matches'].values()), 'unit agreement mismatch')
            keys(w['source_intervals'], UNITS)
            for unit, regions in w['source_intervals'].items():
                keys(regions, ('head', 'deleted', 'tail'))
                for endpoints in regions.values():
                    require(isinstance(endpoints, list) and len(endpoints) == 2, 'invalid interval schema')
                    for endpoint in endpoints:
                        integer(endpoint)
            require(w['source_intervals'] == intervals(planes['A'], w['prefix'], w['suffix']), 'source intervals mismatch')
            for unit in UNITS:
                kept = w['prefix'][unit] + w['suffix'][unit]
                added = sum(w[n][unit] for n in ('warning', 'total', 'marker'))
                require(planes['A'][unit] == kept + w['deleted'][unit] and planes['B'][unit] == kept + added, 'witness arithmetic mismatch')
                require(kept < planes['A'][unit], 'overlap or empty deletion')


def record_terms(row):
    if row['kind'] == 'UNEXPLAINED':
        return None
    if row['kind'] == 'EXACT':
        return {'F': 0, 'D': 0}
    w = row['witness']
    return {'F': sum(w[n]['bytes'] for n in ('warning', 'total', 'marker')), 'D': w['deleted']['bytes']}


def summarize(rows, old_rows):
    terms = [record_terms(row) for row in rows]
    counts = {kind: sum(r['kind'] == kind for r in rows) for kind in KINDS}
    totals = None if any(t is None for t in terms) else {key: sum(t[key] for t in terms) for key in ('F', 'D')}
    t_bytes = sum(r['components']['T'] for r in old_rows)
    if totals is not None:
        require(totals['F'] - totals['D'] == t_bytes, 'T=F-D summary mismatch')
    return {'records': len(rows), 'classification': counts, 'T_bytes': t_bytes, 'new_terms_bytes': totals,
            'identity_closed': None if totals is None else True}


def result_for(evidence, previous, prior_result, evidence_sha):
    rows, old_rows = evidence['records'], previous['records']
    slots = list(dict.fromkeys(row['slot'] for row in old_rows))
    summaries = [{'slot': slot, **summarize([r for r in rows if r['slot'] == slot], [r for r in old_rows if r['slot'] == slot])} for slot in slots]
    marked = [r for r in rows if r['kind'] == KINDS[1]]
    old_unknown = [r for r in rows if r['prior_kind'] == 'UNEXPLAINED']
    discriminatory = [r for r in marked if len(set(r['witness']['deleted'][u] for u in UNITS)) > 1]
    unit_summary = lambda rs: {'records': len(rs), 'N_matches': {u: sum(r['witness']['unit_matches'][u] for r in rs) for u in UNITS}}
    a, b = summaries[:2]
    delta = None
    if a['new_terms_bytes'] is not None and b['new_terms_bytes'] is not None:
        delta = {key: a['new_terms_bytes'][key] - b['new_terms_bytes'][key] for key in ('F', 'D')}
        require(delta['F'] - delta['D'] == prior_result['primary_comparison']['components_delta_bytes']['T'], 'primary delta mismatch')
    return {'schema': 'char-marker-boundary-result-v1', 'baseline_commit': BASELINE,
            'protocol_sha256': PROTOCOL_SHA, 'evidence_sha256': evidence_sha,
            'study_type': 'exploratory reconstruction after observed old classifications',
            'scope': 'Public hash/length arithmetic only; archive rebuild additionally checks exact strings. Neither authenticates private history, HTTP intake, token usage or causal effects.',
            'primary': {'prior_unexplained': len(old_unknown), 'new_boundary_witnesses_in_prior_unexplained': sum(r['kind'] == KINDS[1] for r in old_unknown)},
            'overall': summarize(rows, old_rows), 'slots': summaries,
            'marker_units': {'all_marked': unit_summary(marked), 'differing_units_subset': unit_summary(discriminatory), 'agreement_counts_may_overlap': True},
            'primary_comparison': {'orientation': 'exercism_r1_minus_r2', 'old_components_delta_bytes': prior_result['primary_comparison']['components_delta_bytes'], 'new_terms_delta_bytes': delta,
                                   'T_equals_F_minus_D': None if delta is None else True},
            'unchanged': ['old 93/0/19 frozen classification', 'old R3 and gates', '25 formal cells', 'historical scores', 'product/model run count']}


def exclusive(path, raw):
    with Path(path).open('xb') as f:
        f.write(raw)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--archive-root', type=Path)
    parser.add_argument('--evidence', type=Path, default=HERE / 'evidence.json')
    parser.add_argument('--build-evidence', type=Path, help='exclusive new evidence, requires archive-root')
    parser.add_argument('--output', type=Path, help='exclusive new full result; stdout is summary')
    args = parser.parse_args(argv)
    try:
        context = sources(args.root)
        _, previous, prior_result, bindings, _ = context
        if args.build_evidence:
            require(args.archive_root is not None, 'build-evidence requires archive-root')
            evidence = rebuild(args.root, args.archive_root, context)
            raw = document(evidence)
            require(EVIDENCE_SHA is None or sha(raw) == EVIDENCE_SHA, 'rebuilt seal mismatch')
        else:
            require(EVIDENCE_SHA is not None, 'evidence seal not installed')
            raw = args.evidence.read_bytes()
            require(sha(raw) == EVIDENCE_SHA, 'evidence seal mismatch')
            evidence = loads(raw)
            if args.archive_root:
                require(canon(rebuild(args.root, args.archive_root, context)) == canon(evidence), 'raw reconstruction mismatch')
        validate(evidence, previous, bindings)
        result = result_for(evidence, previous, prior_result, sha(raw))
        if args.build_evidence:
            exclusive(args.build_evidence, raw)
        if args.output:
            exclusive(args.output, document(result))
        print(json.dumps({'ok': True, 'primary': result['primary'], 'overall': result['overall'], 'marker_units': result['marker_units']}, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError, OverflowError, ImportError) as error:
        print('FAIL: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
