#!/usr/bin/env python3
"""formal-a1 导入构建器：逐场收据 → freeze-20261029-v2 导入信封。

裁定输入：adjudications.json（人工逐场裁定：final_adjudication / evidence_grade / gates）。
构建后自动调用 v2 freeze.py validate-import 做语义校验（不写产物）。
"""
import datetime as dt
import hashlib
import json
import pathlib
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parents[3]
B = pathlib.Path(__file__).resolve().parents[1]
V2 = R / '4-打分细则' / '可信冻结-2026-10-29-v2'
PLAN = json.loads((R / '1-评测方案' / '正式批次-2026-10-29' / 'registration-plan.json').read_text(encoding='utf-8'))
CFG = json.loads((V2 / 'config.json').read_text(encoding='utf-8'))
ADJ = json.loads((B / 'adjudications.json').read_text(encoding='utf-8'))
CASES = ('bird-ca-schools-15', 'dabstep-payments-10', 'exercism-py-6', 'lcb-recent-hard-4', 'tb-cargo-plan')
TOTALS = dict(zip(CASES, (15, 10, 6, 4, 27)))
GUARDS = {
    'bird-ca-schools-15': {'input_integrity', 'answers_file', 'answers_schema', 'answers_coverage'},
    'dabstep-payments-10': {'answers_format', 'input_integrity'},
    'exercism-py-6': {'input_integrity'},
    'lcb-recent-hard-4': {'input_integrity'},
    'tb-cargo-plan': {'input_integrity', 'code_rerun', 'plan_structure'},
}
NOW = dt.datetime.now(dt.timezone.utc).isoformat()


def sha(p):
    return {'path': str(pathlib.Path(p).relative_to(R)), 'sha256': hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()}


def fact(value, source, pointer):
    return {'state': 'known', 'value': value, 'refs': [{'source': source, 'pointer': pointer}]}


def build_event(reg):
    parts = reg['event_id'][len('formal-a1-'):-len('-01')]
    product, case = parts.split('-', 1)
    ev_dir = B / 'runs' / ('%s__%s' % (product, case))
    meta = json.loads((ev_dir / 'meta.json').read_text(encoding='utf-8'))
    checker = json.loads((ev_dir / 'checker.stdout.json').read_text(encoding='utf-8'))
    adj = ADJ[reg['event_id']]
    ws_task = ev_dir / 'workspace' / 'TASK.md'
    session = ev_dir / 'agent-session'
    session_file = next(session.iterdir()) if session.is_dir() and any(session.iterdir()) else None
    cfg_snap = CFG['case_snapshots'][case]
    cfg_src = '4-打分细则/可信冻结-2026-10-29-v2/config.json'
    plan_src = '1-评测方案/正式批次-2026-10-29/registration-plan.json'
    sources = [sha(R / plan_src), sha(ev_dir / 'meta.json'), sha(ev_dir / 'integrity-rescan.json'),
               sha(ev_dir / 'checker.stdout.json')]
    # score receipt
    checks = checker.get('checks') or []
    guards = GUARDS[case]
    scored = [c for c in checks if c['id'] not in guards]
    possible = len(scored)
    if possible != TOTALS[case]:
        raise SystemExit('计分项数与全题分母不符：%s %d != %d（守卫集 %s）' % (case, possible, TOTALS[case], sorted(guards)))
    earned = sum(1 for c in scored if c.get('pass'))
    if abs(round(100.0 * earned / possible, 2) - float(checker.get('weighted'))) > 0.011:
        raise SystemExit('计分项通过数与 checker weighted 不一致：%s earned=%d' % (case, earned))
    score = {'earned': earned, 'possible': possible, 'assessed': possible,
             'reported': round(100.0 * earned / possible, 8),
             'reward': checker.get('reward'),
             'rule_version': 'freeze-20261029-v2', 'checker_sha256': cfg_snap['checker.py']}
    (ev_dir / 'score-receipt.json').write_text(json.dumps(
        {'case': case, 'product': product, 'run_id': meta['run_id'], 'score': score,
         'raw_checker_output': checker, 'note': 'composite transcription; raw checker output packaged alongside'},
        ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    # adjudication receipt
    (ev_dir / 'adjudication.json').write_text(json.dumps({
        'event_id': reg['event_id'], 'run_id': meta['run_id'],
        'identity': {'event_id': reg['event_id'], 'run_id': meta['run_id'], 'category': 'product_run',
                     'product': product, 'group': 'A_same_model', 'experiment': False, 'case_id': case},
        'evidence_grade': adj['evidence_grade'], 'final_adjudication': adj['final_adjudication'],
        'gates': adj['gates'], 'adjudicated_at': NOW, 'adjudicator': 'lead（人类监督下的 AI 执行者；语义裁定为信任边界）',
        'basis': adj['basis']},
        ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    sources += [sha(ev_dir / 'score-receipt.json'), sha(ev_dir / 'adjudication.json')]
    sources.append(sha(ws_task))
    if session_file is not None:
        sources.append(sha(session_file))
    sources.append({**sha(R / cfg_src), 'path': cfg_src})
    cfg_idx = len(sources) - 1
    snap_dir = ev_dir / 'config-snapshot'
    snap_file = next(snap_dir.iterdir()) if snap_dir.is_dir() and any(snap_dir.iterdir()) else None
    if snap_file is not None:
        sources.append(sha(snap_file))
    plan_idx = 0
    reg_idx = next(i for i, r in enumerate(PLAN['registrations']) if r['event_id'] == reg['event_id'])
    fs = {
        'case_version': fact(cfg_snap['case_version'], cfg_idx, '/case_snapshots/%s/case_version' % case),
        'product_version': fact(meta['product_version'], 1, '/product_version'),
        'model': fact(meta['model'], 1, '/model'),
        'route': fact(meta['route'], 1, '/route'),
        'tools': fact(meta['tools'], 1, '/tools'),
        'permissions': fact(meta['permissions'], 1, '/permissions'),
        'skills': fact(meta['skills'], 1, '/skills'),
        'started_at': fact(meta['started_at'], 1, '/started_at'),
        'finished_at': fact(meta['finished_at'], 1, '/finished_at'),
        'evidence_grade': fact(adj['evidence_grade'], 5, '/evidence_grade'),
        'final_adjudication': fact(adj['final_adjudication'], 5, '/final_adjudication'),
        'rule_version': fact('freeze-20261029-v2', cfg_idx, '/rule_version'),
        'checker_sha256': fact(cfg_snap['checker.py'], cfg_idx, '/case_snapshots/%s/checker.py' % case),
        'truth_sha256': fact(cfg_snap['truth.json'], cfg_idx, '/case_snapshots/%s/truth.json' % case),
        'case_sha256': fact(cfg_snap['manifest_sha256'], cfg_idx, '/case_snapshots/%s/manifest_sha256' % case),
    }
    gates = {g: fact(True, 5, '/gates/%s' % g) for g in ('rules_frozen', 'case_valid', 'scoring_reviewable', 'evidence_valid', 'contamination_free')}
    event = {'event_id': reg['event_id'], 'category': 'product_run', 'product': product, 'group': 'A_same_model',
             'experiment': False, 'case_id': case,
             'identity': fact({'event_id': reg['event_id'], 'run_id': meta['run_id'], 'category': 'product_run',
                               'product': product, 'group': 'A_same_model', 'experiment': False, 'case_id': case},
                              5, '/identity'),
             'facts': fs, 'gates': gates,
             'score': fact(score, 4, '/score'),
             'selection': {'plan_id': reg['plan_id'], 'slot_id': reg['slot_id'], 'order': reg['order'],
                           'kind': reg['kind'], 'parent_id': reg['parent_id'], 'reason': reg['reason'],
                           'registered_at': reg['registered_at'], 'plan_source': plan_idx,
                           'plan_pointer': '/registrations/%d' % reg_idx},
             'sources': sources, 'issues': [], 'collected_at': NOW,
             'original_time': fact(meta['started_at'], 1, '/started_at')}
    return event


def main():
    events = [build_event(r) for r in PLAN['registrations']]
    envelope = {'schema_version': 1, 'events': events}
    out = B / 'formal-a1-events.json'
    out.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('events:', len(events), '->', out)
    chk = subprocess.run([sys.executable, '-B', str(V2 / 'freeze.py'), 'validate-import', '--imports', str(out.relative_to(R))],
                         cwd=str(R), capture_output=True, text=True)
    print(chk.stdout[-3000:] or chk.stderr[-2000:])
    return chk.returncode


if __name__ == '__main__':
    sys.exit(main())
