#!/usr/bin/env python3
"""Offline public-data closure, not regrading or historical seal authentication.
Only stdlib file reads; default output is JSON on stdout. No imports of repository code.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys

LEDGER = '5-评测报告/证据口径-2026-11-03/source-ledger.public-derived.json'
REPORT = '5-评测报告/竞品评测报告-v1.8.md'
# Reviewed immutable historical bytes. A changed manifest cannot nominate new trust.
TRUSTED = {
    LEDGER: '9784e714cd0134cece788fb3d67b080820dcbc0b95be29761123ab623deea420',
    REPORT: 'd1e303afae28570a916fe088b08ff2d3a6a2a0312b031dd9ad2fbec98dd0a3d5',
}
CASES = ('bird-ca-schools-15', 'dabstep-payments-10', 'exercism-py-6', 'lcb-recent-hard-4', 'tb-cargo-plan')
GENERATIONS = (
 ('A_same_model', '2026-10-29-v2', 'r1030-formal-a1/formal-a1-events.json'),
 ('B_native', '2026-10-29-v4', 'r1101-formal-b1/formal-b1-events.json'),
 ('B_native', '2026-10-29-v5', 'r1102-formal-b2/formal-b2-events.json'),
 ('B_native', '2026-10-29-v6', 'r1104-formal-b3/formal-b3-events.json'),
 ('W_gateway', '20261031-wb-v1', 'r20261031-wb-formal/formal-wb-events.json'),
 ('W_gateway', '20261031-wb-v2', 'r20261031-wb-replacement/formal-wb-replacement-events.json'),
)
PRODUCTS = {'A_same_model': ('codex', 'dsh'), 'B_native': ('yuanbao', 'doubao'), 'W_gateway': ('workbuddy',)}
FACTS = {'case_version', 'product_version', 'model', 'route', 'tools', 'permissions', 'skills', 'started_at', 'finished_at', 'evidence_grade', 'final_adjudication', 'rule_version', 'checker_sha256', 'truth_sha256', 'case_sha256'}
GATES = {'rules_frozen', 'case_valid', 'scoring_reviewable', 'evidence_valid', 'contamination_free'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pairs(items):
    out = {}
    for key, value in items:
        require(key not in out, 'duplicate JSON key: ' + key)
        out[key] = value
    return out


def loads(text):
    def invalid(value):
        raise ValueError('nonfinite JSON: ' + value)
    def finite_float(value):
        number = float(value)
        require(math.isfinite(number), 'nonfinite JSON: ' + value)
        return number
    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid, parse_float=finite_float)


def same(a, b):
    # JSON bool must never compare equal to integer 0/1.
    return json.dumps(a, sort_keys=True, ensure_ascii=False, allow_nan=False) == json.dumps(b, sort_keys=True, ensure_ascii=False, allow_nan=False)


def pointer(doc, ptr):
    require(isinstance(ptr, str) and (not ptr or ptr.startswith('/')), 'invalid JSON pointer')
    for token in ptr[1:].split('/') if ptr else []:
        token = token.replace('~1', '/').replace('~0', '~')
        if isinstance(doc, list):
            require(bool(re.fullmatch(r'0|[1-9][0-9]*', token)), 'invalid array pointer')
            doc = doc[int(token)]
        else:
            doc = doc[token]
    return doc


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.cache = {}
        self.expected = dict(TRUSTED)
        self.missing = set()

    def path(self, name):
        require(isinstance(name, str) and name and '\\' not in name and ':' not in name, 'unsafe source path')
        p = PurePosixPath(name)
        require(not p.is_absolute() and '..' not in p.parts and not name.startswith('~'), 'unsafe source path')
        result = (self.root / name).resolve()
        require(result.is_relative_to(self.root), 'source escapes repository')
        return result

    def check_hash(self, name):
        require(name in self.expected, 'unregistered source: ' + name)
        path = self.path(name)
        if name in self.missing:
            require(not path.exists(), 'historically missing source unexpectedly supplied: ' + name)
            return
        require(path.is_file(), 'missing required source: ' + name)
        require(hashlib.sha256(path.read_bytes()).hexdigest() == self.expected[name], 'trusted source SHA mismatch: ' + name)

    def read(self, name):
        self.check_hash(name)
        if name not in self.cache:
            self.cache[name] = loads(self.path(name).read_text(encoding='utf-8'))
        return self.cache[name]

    def anchor(self, name, ptr=''):
        self.check_hash(name)
        return {'path': name, 'sha256': self.expected[name], 'pointer': ptr,
                'status': 'historically_missing' if name in self.missing else 'present_pinned'}


def validate_score(score):
    require(isinstance(score, dict), 'missing recorded score')
    for key in ('earned', 'possible', 'assessed', 'reported'):
        value = score.get(key)
        require(type(value) in (int, float) and math.isfinite(value), 'invalid score number: ' + key)
    require(score['possible'] > 0 and 0 <= score['earned'] <= score['assessed'] <= score['possible'], 'invalid score denominator')
    require(abs(100 * score['earned'] / score['possible'] - score['reported']) <= .011, 'score arithmetic mismatch')
    require(type(score.get('reward')) is int and score['reward'] in (0, 1), 'invalid reward')


def resolve_fact(store, event, field):
    require(isinstance(field, dict) and {'state', 'value', 'refs'} <= set(field), 'incomplete field schema')
    require(field['state'] in ('known', 'unknown') and isinstance(field['refs'], list), 'invalid field state/refs')
    if field['state'] == 'known':
        require(field['value'] is not None and bool(field['refs']), 'known field requires value and refs')
    else:
        require(field['value'] is None, 'unknown field must explicitly preserve null value')
    refs = []
    for ref in field.get('refs', []):
        index = ref['source']
        require(type(index) is int and 0 <= index < len(event['sources']), 'invalid source index')
        source = event['sources'][index]
        name = source['path']
        anchor = store.anchor(name, ref['pointer'])
        if name in store.missing:
            anchor['value_check'] = 'unverifiable_missing_historical_bytes'
        elif name.endswith('.json'):
            require(same(pointer(store.read(name), ref['pointer']), field.get('value')), 'source pointer value mismatch: ' + name + ref['pointer'])
            anchor['value_check'] = 'matches_recorded_value'
        else:
            anchor['value_check'] = 'byte_pin_only_non_json'
        refs.append(anchor)
    return refs


def report_mapping(text, rows):
    result = {}
    lines = text.splitlines()
    for title, track in (('### 3.1 ', 'A_same_model'), ('### 3.2 ', 'B_native'), ('### 3.3 ', 'W_gateway')):
        start = next(i for i, line in enumerate(lines) if line.startswith(title))
        end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith(('### ', '## '))), len(lines))
        case_lines = [(line.split('|')[1].strip(), i + 1, [c.strip() for c in line.split('|')[2:-1]])
                      for i, line in enumerate(lines[start:end], start) if line.startswith('| ') and line.split('|')[1].strip() in CASES]
        require(len(case_lines) == len({case for case, _, _ in case_lines}), 'duplicate report case row')
        table = {case: (line, cells) for case, line, cells in case_lines}
        require(set(table) == set(CASES), 'report case coverage mismatch')
        summary_line = next((line for line in lines[start:end] if line.startswith('| **weighted 总分') or line.startswith('| **达标题数**')), '')
        require(bool(summary_line), 'report summary missing')
        summary_cells = [cell.strip().replace('**', '') for cell in summary_line.split('|')[2:-1]]
        for product in PRODUCTS[track]:
            selected = [r for r in rows if r['track'] == track and r['product'] == product]
            headline = sum(r['score']['reward'] for r in selected)
            column = PRODUCTS[track].index(product)
            claimed = summary_cells[column] if track != 'W_gateway' else summary_cells[1]
            expected = f"{sum(r['score']['reported'] for r in selected):.2f} / {headline}/5" if track == 'A_same_model' else f'{headline}/5'
            require(claimed == expected, 'report summary mismatch')
        for row in (r for r in rows if r['track'] == track):
            line, cells = table[row['case']]
            column = PRODUCTS[track].index(row['product'])
            cell = cells[column] if track != 'W_gateway' else cells[0]
            require(re.match(r'^' + re.escape(f"{row['score']['reported']:.2f}") + r'(?:（|$)', cell) is not None, 'report weighted mismatch')
            fraction = re.search(r'（(\d+)/(\d+)）', cell)
            if fraction:
                require((int(fraction[1]), int(fraction[2])) == (row['score']['earned'], row['score']['possible']), 'report fraction mismatch')
            if track == 'W_gateway':
                require(cells[1] == str(row['score']['reward']), 'report headline mismatch')
            result[row['event_id']] = {'path': REPORT, 'line': line, 'column': column + 2, 'cell': cell}
    return result


def derive(root):
    store = Store(root)
    ledger = store.read(LEDGER)
    manifest = ledger['source_manifest']
    require(len(manifest) == 402 and len({x['path'] for x in manifest}) == 402, 'historical source inventory changed')
    for entry in manifest:
        name = entry['path']
        require(name not in store.expected, 'duplicate trusted source')
        store.expected[name] = entry['sha256']
        if entry['status'] == 'missing':
            require(entry['sha256'] is None, 'invalid missing pin')
            store.missing.add(name)
        else:
            require(entry['status'] == 'present', 'invalid source status')
        store.check_hash(name)
    require(len(store.missing) == 5, 'historical missing inventory changed')
    previous = {r['event_id']: r for r in ledger['all_formal_attempts']}
    require(len(previous) == len(ledger['all_formal_attempts']) == 30, 'historical attempt IDs duplicate')
    formal = []
    attempts = {}
    replacements = []
    rejected_ids = set()
    for track, generation, relative in GENERATIONS:
        ep = '3-表现现场/' + relative
        tp = '5-评测报告/可信冻结-' + generation + '/official-main-table.json'
        cp = '4-打分细则/可信冻结-' + generation + '/config.json'
        events = store.read(ep)['events']
        table = store.read(tp)
        config = store.read(cp)
        require(track in table['groups'] and all(not ids for group, ids in table['groups'].items() if group != track), 'unexpected official track')
        ids = table['groups'][track]
        require(len(ids) == len(set(ids)), 'duplicate official ID')
        admitted = set(ids)
        products = [e for e in events if e.get('category') == 'product_run']
        index = {e['event_id']: e for e in products}
        require(len(index) == len(products), 'duplicate event ID')
        require(admitted <= set(index), 'unresolved official ID')
        rejects = {r['event_id']: r for r in table['rejected']}
        require(len(rejects) == len(table['rejected']), 'duplicate rejected ID')
        require(not admitted.intersection(rejects) and set(index) <= admitted | set(rejects), 'unclassified or conflicting event')
        rejected_ids.update(rejects)
        for i, event in enumerate(events):
            if event.get('category') != 'product_run':
                continue
            eid = event['event_id']
            require(eid not in attempts and eid in previous, 'unexpected attempt ID')
            require(event['group'] == track and event['product'] in PRODUCTS[track] and event['case_id'] in CASES and event['experiment'] is False, 'event track/category mismatch')
            identity = event['identity']['value']
            for key in ('event_id', 'category', 'product', 'group', 'experiment', 'case_id'):
                require(same(identity[key], event[key]), 'identity/top-level mismatch: ' + key)
            identity_refs = resolve_fact(store, event, event['identity'])
            require(bool(identity_refs), 'identity lacks source')
            for source in event['sources']:
                require(source['path'] in store.expected, 'unregistered event source')
                if source['path'] not in store.missing:
                    require(source.get('sha256') == store.expected[source['path']], 'event source pin mismatch')
                store.check_hash(source['path'])
            require(FACTS <= set(event['facts']), 'mandatory event facts missing')
            refs = {}
            for key, field in event['facts'].items():
                refs[key] = resolve_fact(store, event, field)
            require(set(event['gates']) == GATES, 'mandatory admission gates missing/extra')
            gate_refs = {}
            for key, field in event['gates'].items():
                gate_refs[key] = resolve_fact(store, event, field)
                require(field['state'] == 'unknown' or type(field['value']) is bool, 'gate must be bool or explicit unknown')
                if eid in admitted:
                    require(field['state'] == 'known' and field['value'] is True, 'formal admission gate not true: ' + key)
            score_refs = resolve_fact(store, event, event['score'])
            for anchor in score_refs:
                if anchor['path'] in store.missing or not anchor['path'].endswith('.json'):
                    continue
                receipt = store.read(anchor['path'])
                checked = []
                for envelope in (receipt, receipt.get('identity', {})):
                    if not isinstance(envelope, dict):
                        continue
                    for key, expected in (('case', event['case_id']), ('case_id', event['case_id']), ('product', event['product']), ('run_id', identity['run_id'])):
                        if key in envelope:
                            require(same(envelope[key], expected), 'score receipt ownership mismatch: ' + key)
                            checked.append(key)
                anchor['envelope_identity_fields_checked'] = sorted(set(checked))
                anchor['ownership_check'] = 'available_envelope_identity_matches' if checked else 'no_envelope_identity_trusted_assignment_only'
            score = event['score'].get('value')
            if score is not None:
                require(bool(score_refs) and any(x['value_check'] == 'matches_recorded_value' for x in score_refs), 'score lacks available JSON receipt: ' + eid)
                validate_score(score)
            else:
                require(eid not in admitted, 'admitted event without score')
            snap = config['case_snapshots'][event['case_id']]
            bindings = {'rule_version': config['rule_version'], 'case_version': snap['case_version'],
                        'checker_sha256': snap['checker.py'], 'truth_sha256': snap['truth.json'], 'case_sha256': snap['manifest_sha256']}
            for key, value in bindings.items():
                require(same(event['facts'][key]['value'], value) and bool(refs[key]), 'contract binding mismatch: ' + key)
            if score is not None:
                for key in ('rule_version', 'checker_sha256'):
                    require(score[key] == bindings[key], 'grade/contract mismatch: ' + key)
            old = previous[eid]
            require([(r['path'], r['pointer']) for r in score_refs] == [(r['path'], r['pointer']) for r in old['score_source_refs']], 'score source assignment differs from reviewed ledger')
            for key in FACTS.intersection(old):
                require(same(event['facts'][key]['state'], old[key]['state']) and same(event['facts'][key]['value'], old[key]['value']), 'ledger fact/state mismatch: ' + key)
            row = {'event_id': eid, 'run_id': identity['run_id'], 'track': track, 'product': event['product'], 'case': event['case_id'],
                   'score': score, 'admitted': eid in admitted}
            for key, value in row.items():
                require(same(value, old[key]), 'historical ledger/event mismatch: ' + key)
            require(old['contract']['rule_version'] == config['rule_version'], 'ledger contract mismatch')
            require(old['contract_case_snapshot'] == {k: v for k, v in snap.items() if k.endswith('sha256') or k == 'case_version'}, 'ledger snapshot mismatch')
            source = store.anchor(ep, '/events/' + str(i))
            require(source['path'] == old['source']['path'] and source['pointer'] == old['source']['pointer'], 'ledger event pointer mismatch')
            row.update({'event_source': source, 'identity_refs': identity_refs, 'score_sources': score_refs, 'gate_sources': gate_refs,
                        'contract': {'values': bindings, 'source': store.anchor(cp), 'fact_sources': refs},
                        'official_source': store.anchor(tp, '/groups/' + track if eid in admitted else '/rejected'),
                        'historical_source_pins': [store.anchor(x['path']) for x in event['sources']]})
            # All 30 reviewed attempts have a config-bound registration, including
            # first runs with no predecessor. Missing selection cannot waive it.
            slot = config['official_slots']['|'.join((track, event['product'], event['case_id']))]
            selection = event.get('selection')
            require(isinstance(selection, dict), 'required registration selection missing')
            plan_source = selection.get('plan_source')
            require(type(plan_source) is int and 0 <= plan_source < len(event['sources']), 'required registration plan_source invalid')
            plan_path = event['sources'][plan_source]['path']
            plan = store.read(plan_path)
            registration_pointer = selection.get('plan_pointer')
            require(isinstance(registration_pointer, str) and registration_pointer.startswith('/registrations/'), 'invalid registration pointer')
            registration = pointer(plan, registration_pointer)
            require(isinstance(registration, dict) and registration.get('event_id') == eid, 'registration event identity mismatch')
            for key, value in registration.items():
                if key != 'event_id':
                    require(key in selection and same(selection[key], value), 'registration selection mismatch: ' + key)
            require(selection['plan_id'] == plan['plan_id'] == slot['plan_id'] and selection['slot_id'] == slot['slot_id'], 'registration slot identity mismatch')
            require(store.expected[plan_path] == slot['plan_sha256'], 'registration plan/config pin mismatch')
            row['registration_source'] = store.anchor(plan_path, registration_pointer)
            basis, parent = None, None
            if event['case_id'] in plan.get('predecessors', {}):
                basis = '/predecessors/' + event['case_id']
                parent = pointer(plan, basis)['parent_event_id']
            elif isinstance(plan.get('design', {}).get('predecessor'), str):
                match = re.match(r'(formal-[a-z0-9-]+)\s', plan['design']['predecessor'])
                if match:
                    basis, parent = '/design/predecessor', match[1]
            require(old.get('semantic_predecessor', {}).get('event_id') == parent, 'ledger replacement parent mismatch')
            if parent is not None:
                replacements.append({'child': eid, 'parent': parent, 'source': store.anchor(plan_path, basis)})
            row['parent_event_id'] = parent
            attempts[eid] = row
            if eid in admitted:
                require(event['facts']['final_adjudication']['value'] in ('V', 'F', 'valid'), 'invalid event admitted')
                formal.append(row)
    require(set(attempts) == set(previous), 'attempt closure mismatch')
    expected = {(t, p, c) for t, products in PRODUCTS.items() for p in products for c in CASES}
    require(len(formal) == 25 and {(r['track'], r['product'], r['case']) for r in formal} == expected, 'formal slot coverage mismatch')
    formal_copy = {r['event_id']: r for r in ledger['formal']}
    require(len(formal_copy) == len(ledger['formal']) == 25, 'duplicate/missing ledger formal rows')
    require({r['event_id'] for r in formal} == set(formal_copy), 'ledger official ID mismatch')
    for eid, copied in formal_copy.items():
        require(same(copied, previous[eid]), 'ledger formal/attempt copy mismatch')
    require(len(replacements) == len({r['parent'] for r in replacements}) == 5, 'replacement cardinality mismatch')
    for edge in replacements:
        child, parent = attempts[edge['child']], attempts[edge['parent']]
        require(child['admitted'] and not parent['admitted'] and parent['event_id'] in rejected_ids, 'replacement admission mismatch')
        require((child['track'], child['product'], child['case']) == (parent['track'], parent['product'], parent['case']), 'replacement crosses slot')
    graph = ledger['lineage']
    for row in attempts.values():
        aid = 'attempt:' + row['event_id']
        require(any(n['id'] == aid and n['type'] == 'attempt' for n in graph['nodes']), 'lineage attempt missing')
        slots = [e['to'] for e in graph['edges'] if e['type'] == 'attempt_of' and e['from'] == aid]
        require(slots == ['slot:' + row['track'] + ':' + row['product'] + ':' + row['case']], 'lineage slot mismatch')
        admissions = [e for e in graph['edges'] if e['type'] == 'admitted_by' and e['from'] == aid]
        require(len(admissions) == int(row['admitted']), 'lineage admission mismatch')
        if row['admitted']:
            admission = admissions[0]
            official = row['official_source']
            require(admission['to'] == 'admission:' + official['path'], 'lineage admission target mismatch')
            require(all(same(admission['source'].get(k), official[k]) for k in ('path', 'sha256', 'pointer')), 'lineage admission source mismatch')
    replacement_graph_edges = [e for e in graph['edges'] if e['type'] == 'unique_replacement_for']
    require(len(replacement_graph_edges) == len({(e['from'], e['to']) for e in replacement_graph_edges}), 'duplicate replacement edge')
    actual_edges = {(e['from'][8:], e['to'][8:]) for e in replacement_graph_edges}
    require(actual_edges == {(r['child'], r['parent']) for r in replacements}, 'lineage replacement mismatch')
    report = store.path(REPORT).read_text(encoding='utf-8')
    store.check_hash(REPORT)
    mapping = report_mapping(report, formal)
    summaries = {}
    for product in sorted({r['product'] for r in formal}):
        rows = [r for r in formal if r['product'] == product]
        summaries[product] = {'formal_n': len(rows), 'headline': sum(r['score']['reward'] for r in rows),
                              'weighted_sum': round(sum(r['score']['reported'] for r in rows), 2)}
    require(summaries == ledger['formal_summary'], 'ledger summary mismatch')
    for product in ('codex', 'dsh'):
        summary = summaries[product]
        require(f"{summary['weighted_sum']:.2f} / {summary['headline']}/5" in report, 'report A summary mismatch')
    for r in formal:
        r['report'] = mapping[r['event_id']]
    unknown_versions = sum(r.get('product_version') is None for r in ledger['observation_attempts'] if r['product'] in ('yuanbao', 'doubao'))
    require(unknown_versions == 40, 'historical B version unknown inventory changed')
    return {'schema': 'formal-25-public-closure-v1', 'ok': True, 'meaning': 'reviewed public data consistent, NOT historical raw seal authentication',
            'formal_n_per_product_case': 1, 'track_counts': dict(Counter(r['track'] for r in formal)),
            'summary': summaries, 'rows': formal, 'attempts': len(attempts), 'replacements': replacements,
            'historical_inventory': {'sources': len(manifest), 'present_hashes_match': len(manifest) - len(store.missing),
                'missing': sorted(store.missing), 'B_observation_version_unknown': unknown_versions, 'complete_historical_verification': False},
            'trust_anchors': TRUSTED, 'source_inventory': manifest,
            'limits': ['No checker/candidate execution, no regrading, no product/model/network calls.',
                       'Fixed hashes authenticate consistency to reviewed public bytes, not authenticity of private raw evidence or third-party signatures.',
                       'Missing historical sources and unknown versions remain incomplete; observations never increase formal n.',
                       'No same-model claim for B/W, no cross-track overall ranking.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    try:
        result = derive(args.root)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    except (ValueError, KeyError, IndexError, TypeError, OSError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
