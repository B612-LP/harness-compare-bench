#!/usr/bin/env python3
"""Original independent checks; run by clean_room.py only after both ready.
Synthetic admission fixtures are NOT product runs or evidence of model capability.
"""
import argparse
import copy
import datetime as dt
import hashlib
import importlib.util
import json
import re
from pathlib import Path
import subprocess
import sys

BASE = '4-打分细则/可信冻结-2026-10-29'
OUT = '5-评测报告/可信冻结-2026-10-29'
RESULT = {'schema': 'independent-checks/1', 'scope': 'offline only',
          'new_product_runs': 0, 'checks': [], 'commands': []}


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check(name, passed, detail):
    RESULT['checks'].append({'id': name, 'pass': bool(passed), 'detail': detail})


def command(root, argv):
    p = subprocess.run(argv, cwd=root, capture_output=True, text=True)
    r = {'command': argv, 'exit_code': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}
    RESULT['commands'].append(r)
    return r


def load(p):
    return json.loads(Path(p).read_text())


def write(p, value):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def fixture(root, mod, config, label, changes=None, selection_changes=None, score_changes=None):
    """Locatable self-consistent synthetic source tests gate logic, not signatures."""
    case = mod.CASES[0]
    start = dt.datetime.fromisoformat(config['effective_at'].replace('Z', '+00:00')) + dt.timedelta(days=1)
    times = {'registered_at': (start - dt.timedelta(hours=1)).isoformat(),
             'started_at': start.isoformat(), 'finished_at': (start + dt.timedelta(minutes=1)).isoformat()}
    pins = config['case_snapshots'][case]
    facts = {'case_version': pins['case_version'],
             'product_version': 'synthetic-version', 'model': config['a_model'],
             'route': {'host': config['a_route_host'], 'provider_id': 'deepseek-official', 'wire_protocol': 'anthropic-messages', 'endpoint': 'https://' + config['a_route_host'] + '/anthropic/v1/messages'},
             'tools': [], 'permissions': 'synthetic-read-only', 'skills': [],
             'started_at': times['started_at'], 'finished_at': times['finished_at'],
             'evidence_grade': 'synthetic', 'final_adjudication': 'valid',
             'rule_version': mod.RULE, 'checker_sha256': pins['checker.py'],
             'truth_sha256': pins['truth.json'], 'case_sha256': pins['manifest_sha256']}
    gates = {k: True for k in mod.GATES}
    identity = {'event_id': 'independent-synthetic:' + label, 'category': 'product_run',
                'product': 'dsh', 'group': 'A_same_model', 'experiment': False, 'case_id': case}
    for k, v in (changes or {}).items():
        if k in facts:
            facts[k] = v
        elif k in gates:
            gates[k] = v
        else:
            identity[k] = v
    # bird-ca-schools-15 has a full 15-item contract, not an arbitrary 10-point scale.
    score = {'earned': 7.5, 'possible': 15, 'assessed': 15, 'reported': 50,
             'reward': 0, 'rule_version': mod.RULE, 'checker_sha256': pins['checker.py']}
    score.update(score_changes or {})
    selection = {'plan_id': 'independent-synthetic-plan', 'slot_id': 'dsh:' + case,
                 'order': 1, 'kind': 'first', 'parent_id': None, 'reason': 'preplanned',
                 'registered_at': times['registered_at']}
    selection.update(selection_changes or {})
    data = {'identity': dict(identity, run_id='original-synthetic:' + label),
            'facts': facts, 'gates': gates, 'score': score,
            'original_time': times['started_at']}
    rel = 'independent-fixtures/' + label + '-source.json'
    write(root / rel, data)
    def fact(value, ptr):
        return {'state': 'known', 'value': value, 'refs': [{'source': 0, 'pointer': ptr}]}
    event = dict(identity, identity=fact(data['identity'], '/identity'),
                 facts={k: fact(v, '/facts/' + k) for k, v in facts.items()},
                 gates={k: fact(v, '/gates/' + k) for k, v in gates.items()},
                 score=fact(score, '/score'),
                 selection=dict(selection, plan_source=1, plan_pointer='/registrations/0'),
                 sources=[{'path': rel, 'sha256': digest(root / rel)}], issues=[],
                 collected_at=config['collected_at'], original_time=fact(times['started_at'], '/original_time'))
    return event


def package_plan(root, label, events):
    registrations = []
    for e in events:
        s = e['selection']
        registrations.append({'event_id': e['event_id'], **{k: v for k, v in s.items() if k not in ('plan_source', 'plan_pointer')}})
    rel = 'independent-fixtures/' + label + '-plan.json'
    write(root / rel, {'registrations': registrations, 'note': 'SYNTHETIC ONLY'})
    for i, e in enumerate(events):
        e['sources'] = e['sources'][:1] + [{'path': rel, 'sha256': digest(root / rel)}]
        e['selection'].update(plan_source=1, plan_pointer='/registrations/' + str(i))


def synthetic_config(config, event):
    c = copy.deepcopy(config)
    s = event['selection']
    key = '|'.join(event[k] for k in ('group', 'product', 'case_id'))
    c['official_slots'] = {key: {'plan_id': s['plan_id'], 'slot_id': s['slot_id'], 'plan_sha256': event['sources'][s['plan_source']]['sha256']}}
    return c


def freeze_checks(root):
    script = root / BASE / 'freeze.py'
    spec = importlib.util.spec_from_file_location('reviewed_freeze', script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    config = mod.verify_seal(root)
    check('final_ready_engine_and_lock_pinned', digest(script) == 'f1f8e8e988ea0c22587a96ff606d588cbab6636bd09cf3f77a2521848a4f7681' and digest(root / BASE / 'freeze.lock.json') == 'c784614e891390682c1fd28fa3d2f5b190fdb833943faedf3b1857ef43ba1bad', {'freeze_py_sha256': digest(script), 'lock_sha256': digest(root / BASE / 'freeze.lock.json')})
    r = command(root, [sys.executable, str(script), 'verify', '--root', str(root)])
    check('freeze_cli_verify_published_before_any_rebuild', r['exit_code'] == 0, r)
    recipe = load(root / OUT / 'build-recipe.json')
    argv = [sys.executable, str(script), 'build', '--root', str(root), '--output-dir', 'independent-fixtures/rebuild']
    for pin in recipe['imports']:
        argv += ['--imports', pin['path']]
    if recipe['source_map']:
        write(root / 'independent-fixtures/source-map.json', recipe['source_map'])
        argv += ['--source-map', 'independent-fixtures/source-map.json']
    r = command(root, argv)
    check('freeze_cli_clean_rebuild', r['exit_code'] == 0, r)
    manifest = load(root / OUT / 'output-manifest.json')
    bad = [p['path'] for p in manifest['files'] if (root / p['path']).name != 'output-manifest.json' and (root / p['path']).read_bytes() != (root / 'independent-fixtures/rebuild' / Path(p['path']).name).read_bytes()]
    check('rebuilt_outputs_byte_identical', not bad, {'drift': bad})
    r = command(root, [sys.executable, str(root / BASE / 'test_freeze.py')])
    check('author_selftest_offline', r['exit_code'] == 0, r)
    summary = load(root / OUT / 'summary.json')
    check('historical_scope_honest', summary['historical_rows'] == 96 and summary['historical_cells'] == 25 and summary['official_counts'] == {'A_same_model': 0, 'B_native': 0}, summary)
    check('public_source_audit_242_84', summary['source_counts'] == {'verified': 242, 'external_not_packaged': 84}, summary['source_counts'])
    ledgers = load(root / OUT / 'six-ledgers.json')
    ids = [e['event_id'] for entries in ledgers.values() for e in entries]
    check('six_mutually_exclusive_ledgers', set(ledgers) == set(mod.CATEGORIES) and len(ids) == len(set(ids)), {k: len(v) for k, v in ledgers.items()})
    archive = load(root / OUT / 'archive.json')['events']
    historical = [e for e in archive if e.get('historical')]
    check('historical_unknown_not_zero_or_success', len(historical) == 96 and all(e['score']['state'] == 'unknown' and e['score']['value'] is None and e['admission']['eligible'] is False for e in historical), {'unknown_score_count': sum(e['score']['state'] == 'unknown' for e in historical), 'note': 'Raw legacy observations remain separate from formal score.'})
    cells = load(root / OUT / 'historical-25-cells.json')
    check('all_25_historical_cells_visible', len(cells) == 25 and all(c['candidates'] for c in cells) and all(c['selection'].startswith('none;') for c in cells), {'cells': len(cells), 'candidates': sum(len(c['candidates']) for c in cells)})
    raw_by_id = {'history:' + x['run_id']: x for x in load(root / mod.LEDGER)['runs']}
    candidates = [c for cell in cells for c in cell['candidates']]
    check('legacy_raw_scores_not_relabelled_current_replay', all(c['raw_score']['weighted'] == raw_by_id[c['event_id']]['raw_weighted'] and 'current_recompute' in c and c['current_recompute'] is None for c in candidates), {'candidates': len(candidates), 'current_replays_claimed': sum(c.get('current_recompute') is not None for c in candidates)})
    # Original source tamper: retain manifest and freeze seal; require CLI fail.
    ledger = root / mod.LEDGER
    original = ledger.read_bytes()
    try:
        ledger.write_bytes(original + b'\n')
        r = command(root, [sys.executable, str(script), 'verify', '--root', str(root)])
        check('T1_original_source_tamper_rejected', r['exit_code'] != 0 and 'drift' in r['stdout'], r)
    finally:
        ledger.write_bytes(original)
    first = fixture(root, mod, config, 'positive')
    # Use public validate/build flow for every fixture, not just reason() assertions.
    def build_import(label, events):
        package_plan(root, label, events)
        name = 'independent-fixtures/' + label + '.json'
        write(root / name, {'schema_version': 1, 'events': events})
        output = 'independent-fixtures/out-' + label
        r = command(root, [sys.executable, str(script), 'build', '--root', str(root), '--imports', name, '--output-dir', output])
        formal = load(root / output / 'official-main-table.json') if r['exit_code'] == 0 else None
        return r, formal
    r, table = build_import('positive', [first])
    mod.validate_event(first, root, {})
    mod.select_events([first])
    mod.validate_plan_completeness([first], root, {})
    rr = mod.reasons(first, synthetic_config(config, first))
    check('synthetic_positive_valid_with_test_only_slot', r['exit_code'] == 0 and rr == [], {'command': r, 'synthetic_config_reasons': rr, 'note': 'Real frozen official_slots remains empty; synthetic test config exists only in memory.'})
    check('real_frozen_slots_do_not_admit_synthetic', first['event_id'] not in table['groups']['A_same_model'], table)
    wrong_pointer = copy.deepcopy(first)
    wrong_pointer['facts']['model']['refs'][0]['pointer'] = '/facts/skills'
    r, _ = build_import('wrong-pointer', [wrong_pointer])
    check('known_fact_wrong_pointer_rejected', r['exit_code'] != 0 and 'ref' in r['stdout'], r)
    missing = copy.deepcopy(first)
    del missing['facts']['model']
    r, table = build_import('missing', [missing])
    check('T2_missing_required_field_rejected', r['exit_code'] != 0, r)
    for label, changes, expected in (
        ('polluted', {'contamination_free': False}, 'gate:contamination_free'),
        ('unfrozen', {'rules_frozen': False}, 'gate:rules_frozen'),
        ('invalid-adjudication', {'final_adjudication': 'invalid'}, 'final_adjudication_not_valid'),
        ('research', {'experiment': True, 'group': 'research'}, 'research_variant_not_official_product'),
        ('variant-masquerade', {'case_version': 'research-variant-not-canonical'}, 'case_version_identity_mismatch'),
        ('same-model-wrong-route', {'route': {'host': 'example.invalid', 'provider_id': 'synthetic-other', 'wire_protocol': 'anthropic-messages', 'endpoint': 'https://example.invalid/anthropic/v1/messages'}}, 'official_upstream_route_not_proven'),
    ):
        e = fixture(root, mod, config, label, changes)
        r, table = build_import(label, [e])
        rejected = table and next((x for x in table['rejected'] if x['event_id'] == e['event_id']), None)
        rr = mod.reasons(e, synthetic_config(config, e))
        check('T_' + label + '_not_official', r['exit_code'] == 0 and bool(rejected) and expected in rr, {'command': r, 'rejection': rejected, 'synthetic_config_reasons': rr, 'expected_reason': expected})
    r, table = build_import('duplicate', [first, first])
    check('T5_duplicate_ID_rejected', r['exit_code'] != 0 and 'duplicate' in r['stdout'], r)
    second = fixture(root, mod, config, 'later-better', selection_changes={'order': 2, 'kind': 'repeat', 'parent_id': first['event_id']}, score_changes={'earned': 15, 'reported': 100, 'reward': 1})
    r, table = build_import('no-best-pick', [first, second])
    test_config = synthetic_config(config, first)
    selected = [e['event_id'] for e in (first, second) if not mod.reasons(e, test_config)]
    check('fixed_first_not_best_score', r['exit_code'] == 0 and selected == [first['event_id']], {'command': r, 'synthetic_selected': selected})
    second_plan = fixture(root, mod, config, 'second-plan', selection_changes={'plan_id': 'independent-another-plan'}, score_changes={'earned': 15, 'reported': 100, 'reward': 1})
    r, table = build_import('cross-plan', [first, second_plan])
    rr = mod.reasons(second_plan, synthetic_config(config, first))
    check('no_second_plan_same_cell_primary', r['exit_code'] == 0 and 'not_canonical_official_slot' in rr, {'command': r, 'synthetic_second_plan_reasons': rr})
    alias = fixture(root, mod, config, 'alias-original')
    alias['identity']['value']['run_id'] = first['identity']['value']['run_id']
    proof = load(root / alias['sources'][0]['path'])
    proof['identity'] = alias['identity']['value']
    write(root / alias['sources'][0]['path'], proof)
    alias['sources'][0]['sha256'] = digest(root / alias['sources'][0]['path'])
    r, _ = build_import('alias-original', [first, alias])
    check('duplicate_original_run_id_alias_rejected', r['exit_code'] != 0 and 'duplicate original run_id' in r['stdout'], r)
    masquerade = fixture(root, mod, config, 'identity-masquerade', {'experiment': True})
    masquerade['experiment'] = False
    r, _ = build_import('identity-masquerade', [masquerade])
    check('top_level_variant_identity_tamper_rejected', r['exit_code'] != 0 and 'identity' in r['stdout'], r)
    e = fixture(root, mod, config, 'unknown-rescale', score_changes={'assessed': 5, 'earned': 5, 'reported': 100, 'reward': None})
    r, table = build_import('unknown-rescale', [e])
    check('unknown_not_rescaled_to_full_score', r['exit_code'] != 0, r)
    unmanaged = fixture(root, mod, config, 'unknown-unmanaged')
    unmanaged['facts']['model'] = {'state': 'unknown', 'value': None, 'refs': []}
    r, _ = build_import('unknown-unmanaged', [unmanaged])
    check('unknown_requires_management_issue', r['exit_code'] != 0, r)
    # Declared plan must remain complete when a losing/earlier attempt is omitted.
    package_plan(root, 'omitted-first', [first, second])
    name = 'independent-fixtures/omitted-first.json'
    write(root / name, {'schema_version': 1, 'events': [second]})
    r = command(root, [sys.executable, str(script), 'build', '--root', str(root), '--imports', name, '--output-dir', 'independent-fixtures/out-omitted'])
    check('omitted_registered_first_rejected', r['exit_code'] != 0, r)
    # Inputs (not merely instruction.md) are in the canonical manifest.
    pinset = config['case_snapshots'][mod.CASES[0]]['files']
    input_name = next(n for n in pinset if n.startswith('inputs/') and not n.endswith('.sqlite'))
    target = root / '2-用例' / mod.CASES[0] / input_name
    original = target.read_bytes()
    try:
        target.write_bytes(original + b'\n')
        r = command(root, [sys.executable, str(script), 'verify', '--root', str(root)])
        check('full_input_tree_tamper_rejected', r['exit_code'] != 0 and 'manifest drift' in r['stdout'], r)
    finally:
        target.write_bytes(original)


def history_checks(root):
    before = load(root / '5-评测报告/独立复核-2026-10-29/protected-baseline.json')
    bad = [p for p, h in before['files'].items() if not (root / p).is_file() or digest(root / p) != h]
    check('1542_originals_byte_identical', len(before['files']) == 1542 and not bad, {'count': len(before['files']), 'changed': bad})


def jsonlines(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip().startswith('{')]


def difference_paths(a, b, path=''):
    if type(a) is not type(b):
        return [path]
    if isinstance(a, dict):
        return [p for k in sorted(set(a) | set(b)) for p in ([path + '/' + k] if k not in a or k not in b else difference_paths(a[k], b[k], path + '/' + k))]
    if isinstance(a, list):
        if len(a) != len(b):
            return [path + '/length']
        return [p for i, (x, y) in enumerate(zip(a, b)) for p in difference_paths(x, y, path + '/' + str(i))]
    return [] if a == b else [path]


def normalize_request(request):
    value = copy.deepcopy(request)
    # Normalize only model-generated message IDs/signatures, never arbitrary fields.
    for message in value.get('messages', []):
        for block in message.get('content', []):
            if block.get('type') == 'thinking' and 'signature' in block:
                block['signature'] = '<MODEL_SIGNATURE>'
            if block.get('type') == 'tool_use':
                block['id'] = '<TOOL_CALL_ID>'
            if block.get('type') == 'tool_result':
                block['tool_use_id'] = '<TOOL_CALL_ID>'
    return value


def tool_result_text(request):
    parts = [b for m in request['messages'] for b in m.get('content', []) if b.get('type') == 'tool_result']
    return '\n'.join(c['text'] for b in parts for c in b.get('content', []) if c.get('type') == 'text')


def mechanism_checks(root):
    source = root / '1-评测方案/机制实验-2026-10-29'
    evidence = root / '3-表现现场/r20261029-mechanism'
    manifest_path = evidence / 'evidence-manifest.json'
    manifest = load(manifest_path)
    bad_pins = [x['path'] for x in manifest['files'] if not (root / x['path']).is_file() or digest(root / x['path']) != x['sha256'] or (root / x['path']).stat().st_size != x['bytes']]
    check('mechanism_final_manifest_188_files', digest(manifest_path) == '998a9f6a17e3517aa012dcd6e2e57dafe8f0a1cf4156a429ada4121de394d25e' and len(manifest['files']) == 188 and not bad_pins, {'manifest_sha256': digest(manifest_path), 'files': len(manifest['files']), 'drift': bad_pins})
    r = command(root, [sys.executable, str(source / 'manifest.py'), 'verify'])
    check('author_manifest_verify_offline', r['exit_code'] == 0, r)
    published = load(evidence / 'analysis.json')
    # Discover raw metadata independently rather than taking the author's run list.
    dirs = sorted([p.parent for version in ('v3', 'v4') for p in (evidence / version).glob('20*/run-meta.json') if (p.parent / '02-request.json').is_file()], key=lambda p: load(p / 'run-meta.json')['start'])
    plan = [('large', 'full', 12500), ('large', 'bounded', 512), ('large', 'bounded', 512), ('large', 'full', 12500), ('small', 'full', 12500), ('small', 'bounded', 512)]
    actual_plan = [(load(p / 'run-meta.json')['size'], load(p / 'run-meta.json')['arm'], load(p / 'run-meta.json')['maxInlineTokens']) for p in dirs]
    check('mechanism_fixed_six_interleaved_plan', actual_plan == plan and len(set(p.name for p in dirs)) == 6, actual_plan)
    check('exactly_twelve_dispatched_requests', sum(len(list(p.glob('*-transport.json'))) for p in dirs) == 12 and all(len(list(p.glob('*-request.json'))) == 2 for p in dirs), {'dispatches_by_run': {p.name: len(list(p.glob('*-transport.json'))) for p in dirs}})
    versions = (evidence, evidence / 'v2', evidence / 'v3', evidence / 'v4')
    frozen = []
    for version in versions:
        f = load(version / 'freeze.json')
        drift = [n for n, h in f['files'].items() if digest(source / n) != h]
        frozen.append({'version': f['version'], 'freeze_sha256': digest(version / 'freeze.json'), 'source_drift': drift})
    check('all_four_frozen_source_versions_preserved', all(not x['source_drift'] for x in frozen), frozen)
    # Failed initializations had no dispatched transport; preserve rather than replace.
    failed = [p.parent for version in versions[:2] for p in version.glob('20*/run-meta.json')]
    check('v1_v2_pre_api_failures_retained', len(failed) == 2 and all(load(p / 'run-meta.json')['exit_code'] != 0 and not list(p.glob('*-transport.json')) for p in failed), [str(p.relative_to(evidence)) for p in failed])
    records = []
    firsts = []
    profiles = []
    for out in dirs:
        meta = load(out / 'run-meta.json')
        freeze = load(out.parent / 'freeze.json')
        check('preregistered_before_' + out.name, meta['freeze_sha256'] == digest(out.parent / 'freeze.json') and dt.datetime.fromisoformat(freeze['frozen_at']) < dt.datetime.fromisoformat(meta['start']), {'frozen_at': freeze['frozen_at'], 'start': meta['start']})
        profile = load(out / 'profile.json')
        cap = next(x['config']['maxInlineTokens'] for x in profile if x.get('id') == 'spill-policy')
        check('intervention_effective_' + out.name, cap == meta['maxInlineTokens'], {'profile_cap': cap, 'run_meta_cap': meta['maxInlineTokens']})
        normalized_profile = copy.deepcopy(profile)
        next(x['config'] for x in normalized_profile if x.get('id') == 'spill-policy')['maxInlineTokens'] = '<INTERVENTION>'
        profiles.append(normalized_profile)
        text = 'OBSERVATION HEAD_KEY = AMBER-731\n'
        if meta['size'] == 'large':
            text += ''.join('noise-%04d checksum=%s\n' % (i, hashlib.sha256(('fixture-v1-' + str(i)).encode()).hexdigest()) for i in range(420))
        text += 'OBSERVATION TAIL_KEY = COBALT-492\n'
        tool = (out / 'tool-output.txt').read_bytes()
        process = load(out / 'tool-process.json')
        check('original_tool_hash_' + out.name, tool == text.encode() and digest(out / 'tool-output.txt') == process['sha256'] and len(tool) == process['bytes'] and process['exit_code'] == 0, {'sha256': digest(out / 'tool-output.txt'), 'bytes': len(tool)})
        stdout = jsonlines(out / 'stdout.txt')
        calls_in_trace = [x for x in stdout if x.get('type') == 'tool_call']
        outputs_in_trace = [x for x in stdout if x.get('type') == 'tool_result']
        steps = [x for x in stdout if x.get('type') == 'status' and x.get('phase') == 'step_end']
        reqs, usages = [], []
        for number in ('01', '02'):
            req = load(out / (number + '-request.json'))
            transport = load(out / (number + '-transport.json'))
            response = load(out / (number + '-response-meta.json'))
            compact = json.dumps(req, ensure_ascii=False, separators=(',', ':')).encode()
            check('official_low_request_' + out.name + '_' + number, transport['host'] == 'api.deepseek.com' and transport['path'] == '/anthropic/v1/messages' and transport['method'] == 'POST' and response['status'] == 200 and req['model'] == 'deepseek-flash' and req['output_config']['effort'] == 'low' and req['max_tokens'] == 1024 and [t['name'] for t in req['tools']] == ['fixture_output'] and hashlib.sha256(compact).hexdigest() == transport['published_body_compact_json_sha256'], {'host': transport['host'], 'status': response['status'], 'published_compact_hash_verified': hashlib.sha256(compact).hexdigest() == transport['published_body_compact_json_sha256'], 'raw_equals_published_hash': transport['raw_body_sha256'] == transport['published_body_compact_json_sha256']})
            sse_path = out / (number + '-response.sse')
            if sse_path.exists():
                events = [json.loads(line[6:]) for line in sse_path.read_text().splitlines() if line.startswith('data: ')]
                usage = {}
                for event in events:
                    usage.update(event.get('message', {}).get('usage', {}))
                    usage.update(event.get('usage', {}))
                models = [x['message']['model'] for x in events if x.get('type') == 'message_start']
                capture = load(out / (number + '-capture-status.json'))
                check('raw_sse_hash_usage_' + out.name + '_' + number, models == ['deepseek-flash'] and any(x.get('type') == 'message_stop' for x in events) and capture['raw_response_sha256'] == digest(sse_path) and capture['raw_consumed_bytes'] == sse_path.stat().st_size, {'models': models, 'hash': digest(sse_path), 'usage': usage})
                if number == '02':
                    raw_answer = ''.join(x.get('delta', {}).get('text', '') for x in events if x.get('delta', {}).get('type') == 'text_delta')
                    check('raw_answer_correct_' + out.name, json.loads(raw_answer) == {'HEAD_KEY': 'AMBER-731', 'TAIL_KEY': 'COBALT-492'}, raw_answer)
            else:
                recovered = [x for x in jsonlines(out / 'session-recovered.jsonl') if x.get('type') == 'assistant/message']
                u = recovered[int(number) - 1]['data']['usage']
                usage = dict(input_tokens=u['inputTokens'], output_tokens=u['outputTokens'], cache_read_input_tokens=u.get('cacheReadTokens', 0), cache_creation_input_tokens=u.get('cacheWriteTokens', 0))
                check('v3_downgraded_not_raw_' + number, out.parent.name == 'v3' and not meta['actual_api_gate'], {'usage_source': 'provider-parsed durable session, NOT raw SSE', 'usage': usage})
            trace_usage = steps[int(number) - 1]['usage']
            check('usage_crosschecked_trace_' + out.name + '_' + number, all(usage.get(k, 0) == trace_usage.get(v, 0) for k, v in [('input_tokens', 'inputTokens'), ('output_tokens', 'outputTokens'), ('cache_read_input_tokens', 'cacheReadTokens'), ('cache_creation_input_tokens', 'cacheWriteTokens')]), {'provider_fields': usage, 'trace_fields': trace_usage})
            usages.append(usage)
            reqs.append(req)
        firsts.append(reqs[0])
        wire_tool = tool_result_text(reqs[1])
        wire_calls = [b for m in reqs[1]['messages'] for b in m.get('content', []) if b.get('type') == 'tool_use']
        wire_results = [b for m in reqs[1]['messages'] for b in m.get('content', []) if b.get('type') == 'tool_result']
        linked = len(calls_in_trace) == len(outputs_in_trace) == len(wire_calls) == len(wire_results) == 1
        trace_text = outputs_in_trace[0]['result'] if outputs_in_trace else ''
        trace_complete = trace_text == wire_tool
        exact_cli_prefix = meta['size'] == 'large' and meta['arm'] == 'full' and len(trace_text) == 8192 and trace_text == wire_tool[:8192]
        linked = linked and calls_in_trace[0]['tool'] == wire_calls[0]['name'] == 'fixture_output' and calls_in_trace[0]['callId'] == outputs_in_trace[0]['callId'] == wire_calls[0]['id'] == wire_results[0]['tool_use_id'] and wire_calls[0]['input'] == {} and (trace_complete or exact_cli_prefix)
        check('trace_wire_tool_link_' + out.name, linked, {'tool_calls': len(calls_in_trace), 'tool_outputs': len(outputs_in_trace), 'wire_sha256': hashlib.sha256(wire_tool.encode()).hexdigest(), 'cli_trace_complete': trace_complete, 'cli_trace_bytes': len(trace_text.encode()), 'cli_exact_prefix_8192': exact_cli_prefix, 'boundary': 'CLI stdout is only 8192-character prefix for large/full. Full content independently checked against request, deterministic source, tool-output and process hash; not inferred from truncated stdout.'})
        full_expected = meta['size'] == 'small' or meta['arm'] == 'full'
        check('spill_manipulation_' + out.name, (wire_tool == text if full_expected else ('Full formatted result stored at:' in wire_tool and 'noise-0210' not in wire_tool)) and 'AMBER-731' in wire_tool and 'COBALT-492' in wire_tool, {'wire_bytes': len(wire_tool.encode()), 'original_bytes': len(tool), 'full_expected': full_expected})
        final = [x['text'] for x in stdout if x.get('type') == 'final']
        check('final_answer_' + out.name, len(final) == 1 and json.loads(final[0]) == {'HEAD_KEY': 'AMBER-731', 'TAIL_KEY': 'COBALT-492'} and meta['exit_code'] == 0, final)
        row = {'run_id': out.name, 'path': str(out.relative_to(evidence)), 'raw_usage': usages, 'second_input': sum(usages[1].get(k, 0) for k in ('input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens')), 'requests': reqs, 'wire_tool': wire_tool}
        records.append(row)
    check('all_full_first_requests_identical', bool(firsts) and all(x == firsts[0] for x in firsts), {'count': len(firsts), 'exact_full_JSON_not_selected_projection': True})
    check('profiles_only_intervention_differs', bool(profiles) and all(x == profiles[0] for x in profiles), {'count': len(profiles)})
    pairs = []
    for full, bounded in ((0, 1), (3, 2), (4, 5)):
        a, b = records[full], records[bounded]
        diff = difference_paths(normalize_request(a['requests'][1]), normalize_request(b['requests'][1]))
        pairs.append({'full_run': a['run_id'], 'bounded_run': b['run_id'], 'full_second_input': a['second_input'], 'bounded_second_input': b['second_input'], 'difference': a['second_input'] - b['second_input'], 'all_remaining_difference_paths': diff})
    check('pair2_only_tool_result_diff', pairs[1]['all_remaining_difference_paths'] == ['/messages/2/content/0/content/0/text'] and pairs[1]['full_second_input'] == 19697 and pairs[1]['bounded_second_input'] == 1492, pairs[1])
    check('small_negative_control_same_tool_not_same_usage', records[4]['wire_tool'] == records[5]['wire_tool'] and records[4]['second_input'] == 504 and records[5]['second_input'] == 524, pairs[2])
    RESULT['mechanism_independent_observations'] = {'pairs': pairs, 'runs': [{k: v for k, v in x.items() if k not in ('requests', 'wire_tool')} for x in records], 'boundary': 'Pair1 raw-SSE gap and thinking difference; small thinking difference and 20-token opposite-direction residual. No universal quality or money-cost claim.'}
    total_input = sum(u.get(k, 0) for row in records for u in row['raw_usage'] for k in ('input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens'))
    carry = load(evidence / 'v4/freeze.json')['carry_in']
    first_input = sum(u.get(k, 0) for u in records[0]['raw_usage'] for k in ('input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens'))
    check('actual_request_and_input_budget_not_reset', len(records) * 2 == 12 <= 18 and total_input <= 150000 and carry['actual_requests'] == 2 and carry['input_tokens_including_cache'] == first_input and carry['freeze_sha256'] == digest(evidence / 'v3/freeze.json'), {'actual_requests': len(records) * 2, 'total_input': total_input, 'carry_in_first_input': first_input})
    author_rows = {x['run_id']: x for x in published['runs']}
    check('author_analysis_matches_independent_raw', len(author_rows) == 6 and all(author_rows[r['run_id']]['calls'][i]['raw_usage'] == u for r in records for i, u in enumerate(r['raw_usage'])) and all(author_rows[r['run_id']]['calls'][1]['total_input_including_cache'] == r['second_input'] for r in records), {'runs': len(author_rows)})
    recovery = load(evidence / 'spill-recovery-posthoc.json')
    check('posthoc_spill_copy_hash_not_model_recovery', len(recovery['records']) == 2 and all(digest(evidence / x['public_copy']) == x['sha256'] and (evidence / x['public_copy']).read_bytes() == (evidence / Path(x['request_source']).parent / 'tool-output.txt').read_bytes() and x['recorded_during_run'] is False for x in recovery['records']), recovery)
    # Run original offline analyzer only after preserving/validating published evidence.
    r = command(root, [sys.executable, str(source / 'analyze.py'), '--evidence', str(evidence), '--verify'])
    check('author_analysis_verify_readonly', r['exit_code'] == 0, r)
    rebuilt_path = root / 'independent-fixtures/rebuilt-mechanism-analysis.json'
    r = command(root, [sys.executable, str(source / 'analyze.py'), '--evidence', str(evidence), '--output', str(rebuilt_path)])
    rebuilt = load(rebuilt_path)
    old = copy.deepcopy(published)
    old.pop('generated_at', None)
    rebuilt.pop('generated_at', None)
    check('author_offline_analysis_rebuild', r['exit_code'] == 0 and rebuilt == old, r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    root = ap.parse_args().root.resolve()
    try:
        history_checks(root)
        freeze_checks(root)
        mechanism_checks(root)
        history_checks(root)
    except Exception as exc:
        import traceback
        check('unhandled_check_failure', False, {'exception': repr(exc), 'traceback': traceback.format_exc()})
    RESULT['passed'] = bool(RESULT['checks']) and all(c['pass'] for c in RESULT['checks'])
    write(root / 'independent-results.json', RESULT)
    print(json.dumps({'passed': RESULT['passed'], 'checks': len(RESULT['checks']), 'failed': [c['id'] for c in RESULT['checks'] if not c['pass']]}, ensure_ascii=False))
    return 0 if RESULT['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
