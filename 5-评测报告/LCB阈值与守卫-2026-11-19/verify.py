"""Offline typed projection; no imported or executed historical source."""
from copy import deepcopy
from decimal import Decimal
from fractions import Fraction
from hashlib import sha256
from pathlib import Path, PurePosixPath
from subprocess import check_output
import ast
import json
import os
import re
import sys

CASE = 'lcb-recent-hard-4'
COMMIT = 'dd5a12f651527923a412f6727d5d2f9c22457026'
LOCK = 'c02535236d5744e4bbcb17cf6a3aa493a6ec36ca42fb00c350cbde6eb0a4cad4'
SLOTS = tuple(f'{a}:r{r}' for a in ('codex', 'dsh') for r in (1, 2, 3))
ROLES = {(s, k) for s in SLOTS for k in ('stdout', 'receipt')} | {('anchor', k) for k in ('matrix1', 'matrix23', 'checker', 'verifier', 'study')}

class Reject(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise Reject(reason)


def unique(items):
    out = {}
    for k, value in items:
        need(k not in out, 'DUPLICATE_KEY')
        out[k] = value
    return out


def parse(body):
    def constant(_):
        raise Reject('NONFINITE')
    return json.loads(body.decode('utf-8'), object_pairs_hook=unique, parse_float=Decimal, parse_constant=constant)


def same(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(v, b[k]) for k, v in a.items())
    if isinstance(a, list):
        return len(a) == len(b) and all(same(v, w) for v, w in zip(a, b))
    return a == b


def acquire():
    raw = (Path(__file__).resolve().parent / 'sources.json').read_bytes()
    need(sha256(raw).hexdigest() == LOCK, 'LOCK_SHA')
    doc = parse(raw)
    need(doc['commit'] == COMMIT and len(doc['sources']) == len(ROLES), 'LOCK_SIZE')
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_NO_REPLACE_OBJECTS='1', GIT_NO_LAZY_FETCH='1', GIT_ALLOW_PROTOCOL='')
    def git(*args):
        return check_output(['git', '-c', 'core.hooksPath=/dev/null', *args], env=env, timeout=8)
    out = {}
    for entry in doc['sources']:
        key = entry['slot'], entry['role']
        need(key in ROLES and key not in out, 'LOCK_ROLE')
        path, oid = entry['path'], entry['blob']
        need(not PurePosixPath(path).is_absolute() and '..' not in PurePosixPath(path).parts and re.fullmatch(r'[a-f0-9]{40}', oid), 'LOCK_PATH')
        need(git('rev-parse', COMMIT + ':' + path).decode('ascii').strip() == oid, 'OBJECT_BINDING')
        data = git('cat-file', 'blob', oid)
        need((len(data), sha256(data).hexdigest()) == (entry['size'], entry['sha256']), 'OBJECT_BYTES')
        out[key] = entry, data
    return out


def guard_report(out):
    checks = out.get('checks')
    need(type(checks) is list and all(type(x) is dict for x in checks), 'CHECKS_TYPE')
    guards = [x for x in checks if x.get('id') == 'input_integrity']
    if not guards:
        return 'unknown', 'guard_row_missing'
    if len(guards) != 1:
        return 'contradictory', 'guard_row_repeated'
    row = guards[0]
    need(row.get('guard') is True and type(row.get('pass')) is bool and type(row.get('weight')) in (int, Decimal) and row['weight'] == 0, 'GUARD_TYPE')
    note = row.get('note')
    if type(note) is str and re.fullmatch(r'附带输入副本与 canonical 一致（[^）]+）', note):
        mode, intended = 'copy_equal_reported', True
    elif note == '未附输入副本（未核验，不扣分）':
        mode, intended = 'no_copy_unverified', True
    elif type(note) is str and re.fullmatch(r'附带输入副本被修改（[^）]+），与 canonical 不一致', note):
        mode, intended = 'copy_mismatch_reported', False
    else:
        return 'reported_true' if row['pass'] else 'reported_false', 'note_scope_unknown'
    if row['pass'] is not intended:
        return 'contradictory', 'guard_note_disagrees'
    return 'reported_true' if intended else 'reported_false', mode


def expected(earned, guard):
    count = earned >= 2
    return {'count_gate': count, 'ratio_with_count_threshold': Fraction(earned, 4) >= 2,
            'ratio_with_proportion_threshold': Fraction(earned, 4) >= Fraction(1, 2),
            'count_and_guard': 0 if not count else {'reported_true': 1, 'reported_false': 0}.get(guard)}


def scope(slot, row, receipt, paths):
    arm, label = slot.split(':'); rep = int(label[1:]); directory = str(PurePosixPath(paths[0]).parent)
    need([str(PurePosixPath(p).parent) for p in paths] == [directory, directory] and row['run_dir'] == directory, 'PARENT_SCOPE')
    need(row['case'] == CASE and row['product'] == arm and type(row['rep']) is int and row['rep'] == rep, 'MATRIX_SCOPE')
    need(receipt['case'] == CASE and receipt['product'] == arm and receipt['run_id'] == row['run_id'], 'RECEIPT_SCOPE')
    profile = {'r1': None, 'r2': rep if arm == 'codex' else str(rep), 'r3': rep if arm == 'codex' else str(rep)}[label]
    need(('rep' not in receipt) if profile is None else same(receipt.get('rep'), profile), 'RECEIPT_REPEAT')


def project(slot, row, stdout, receipt, paths, anchor_sha):
    scope(slot, row, receipt, paths)
    need(stdout['case'] == CASE and same(stdout, receipt['raw_checker_output']), 'STDOUT_MIRROR')
    need(type(stdout['passed_problems']) is int and type(stdout['total_problems']) is int and type(stdout['threshold']) is int and
         (stdout['passed_problems'], stdout['total_problems'], stdout['threshold']) == (4, 4, 2), 'COUNT_THRESHOLD')
    s = receipt['score']; c = row['checks']['c_weighted_recompute']; d = c['threshold_consistency']; checker = row['checks']['a_checker_sha']
    need(all(type(s[k]) is int and s[k] == 4 for k in ('earned', 'possible', 'assessed')) and s['reported'] == 100 and stdout['weighted'] == 100, 'COUNT_SOURCES')
    need(all(type(v) is int and v == 1 for v in (s['reward'], stdout['reward'], c['reward_stdout'], c['reward_meta'])), 'REWARD_SOURCES')
    need(type(c['earned']) is int and c['earned'] == 4 and type(c['expected_denominator']) is int and c['expected_denominator'] == 4 and c['guards_excluded'] == ['input_integrity'], 'MATRIX_COUNTS')
    need(type(d['threshold']) is int and d['threshold'] == 2 and type(d['expected_reward']) is int and d['expected_reward'] == 0 and d['match'] is False, 'MATRIX_DIAGNOSTIC')
    recorded_sha = s['checker_sha256']
    need(type(recorded_sha) is str and re.fullmatch('[a-f0-9]{64}', recorded_sha) and checker['receipt_sha'] == recorded_sha, 'DECLARED_SHA')
    guard, qualifier = guard_report(stdout)
    return {'scope_join': 'matrix_run_dir_and_receipt_case_product_run_repeat', 'guard_truth': guard, 'guard_note_scope': qualifier,
            'earned': 4, 'possible': 4, 'threshold_literal': 2, 'recorded_reward': 1, 'diagnostic_expected_reward': 0,
            'matrix_weighted_gate_status': c['status'], 'matrix_receipt_sha_link': True,
            'declared_checker_matches_current_source': recorded_sha == anchor_sha,
            'count_prediction_conditional_on_record': expected(4, guard)['count_and_guard'],
            'physical_input_verification': None, 'stdout_embed_same_report': True}


def main_data(raw):
    source_text = {}
    for role in ('checker', 'verifier'):
        source_text[role] = raw['anchor', role][1].decode('utf-8')
        need(type(ast.parse(source_text[role])) is ast.Module, 'STATIC_SOURCE')
    need('PASS_THRESHOLD = 2' in source_text['checker'] and 'passed >= PASS_THRESHOLD and integrity_ok' in source_text['checker'] and
         '(earned / possible) >= float(thr)' in source_text['verifier'], 'STATIC_SEMANTIC_ANCHORS')
    matrices = [parse(raw['anchor', k][1]) for k in ('matrix1', 'matrix23')]
    by_slot = unique((f"{r['product']}:r{r['rep']}", r) for d in matrices for r in d['runs'] if r.get('case') == CASE)
    need(set(by_slot) == set(SLOTS), 'MATRIX_SLOTS')
    out, all_outputs = {}, {}
    for slot in SLOTS:
        records = [raw[slot, k] for k in ('stdout', 'receipt')]
        paths = [e['path'] for e, _ in records]
        a, b = (parse(v) for _, v in records)
        out[slot] = project(slot, by_slot[slot], a, b, paths, raw['anchor', 'checker'][0]['sha256'])
        all_outputs[slot] = a, b, paths
    source_a, source_b, source_paths = all_outputs['codex:r1']
    controls = {}
    alternate = deepcopy(source_a)
    alternate['checks'] = [v for v in alternate['checks'] if v['id'] != 'input_integrity']
    gg, _ = guard_report(alternate)
    need(gg == 'unknown' and expected(4, gg)['count_and_guard'] is None, 'MISSING_CONTROL')
    controls['no_guard_with_same_recorded_reward'] = 'unknown'
    alternate = deepcopy(source_a)
    row = next(x for x in alternate['checks'] if x['id'] == 'input_integrity')
    row['pass'] = False
    need(guard_report(alternate)[0] == 'contradictory', 'NOTE_CONTROL')
    controls['positive_note_false_bit'] = 'contradictory'
    row['note'] = '附带输入副本被修改（fixture），与 canonical 不一致'
    gg, sv = guard_report(alternate)
    need(gg == 'reported_false' and sv == 'copy_mismatch_reported' and expected(4, gg)['count_and_guard'] == 0, 'FALSE_CONTROL')
    controls['count_passes_guard_fails'] = 0
    try:
        scope('codex:r1', by_slot['codex:r1'], all_outputs['codex:r2'][1], source_paths)
    except Reject as e:
        need(str(e) == 'RECEIPT_SCOPE', 'SWAP_WRONG_REJECTION')
        controls['same_score_other_repeat_receipt'] = str(e)
    else:
        raise Reject('SWAP_ACCEPTED')
    return {'source_count': len(raw), 'rows': out,
            'matrix_declared_historical_verifier_sha_matches_current': [d['tool_sha256'] == raw['anchor', 'verifier'][0]['sha256'] for d in matrices],
            'decision_table_fixed_denominator': [{'earned': n, **expected(n, 'reported_true')} for n in range(5)],
            'controls': controls,
            'limits': ['no_checker_execution', 'reported_guard_not_fresh_verification', 'not_actual_full_runtime_input']}


if __name__ == '__main__':
    try:
        derived = (json.dumps(main_data(acquire()), sort_keys=True, indent=2) + '\n').encode('utf-8')
        need((Path(__file__).resolve().parent / 'evidence.json').read_bytes() == derived, 'EVIDENCE_MISMATCH')
        print('OK: six fixed guard reports, five count rows, four controls')
    except (Reject, KeyError, TypeError, OSError, ValueError) as e:
        print('REJECT:' + type(e).__name__ + (':' + str(e) if isinstance(e, Reject) else ''), file=sys.stderr)
        raise SystemExit(2)
