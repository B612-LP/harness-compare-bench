#!/usr/bin/env python3
"""环16：元宝 n=3 批八场 0 分构成机械汇总（只读私档判卷件与收割记录）。
输出：公开派生 JSON（零私档路径；产物缺失项/回执测试数/收割卡片数逐槽）。"""
import json, sys, hashlib
from pathlib import Path
ROOT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('.')
SLOTS = [
    'dabstep-payments-10__r2', 'dabstep-payments-10__r3',
    'exercism-py-6__r1b', 'exercism-py-6__r2', 'exercism-py-6__r3',
    'lcb-recent-hard-4__r1b', 'lcb-recent-hard-4__r2', 'lcb-recent-hard-4__r3b',
]
rows = []
for slot in SLOTS:
    g = ROOT / 'evidence-tools/grading' / slot
    execd = json.loads((g / 'execution.json').read_text())
    out = json.loads((g / 'checker.stdout.txt').read_text())
    entry = {
        'slot': slot, 'case': execd['case'], 'rep': execd.get('rep'),
        'reward': out.get('reward'), 'weighted': out.get('weighted'),
    }
    failed_ids = [c['id'] for c in out.get('checks', []) if not c.get('pass')]
    entry['failed_check_ids'] = failed_ids
    entry['delivery_missing'] = any(
        ('缺失' in c.get('note', '')) or (c.get('fail_kind') == 'missing')
        for c in out.get('checks', []))
    run = ROOT / 'runs' / slot
    harvest = run / 'filelink-harvest.json'
    entry['harvest_saved'] = len(json.loads(harvest.read_text()).get('saved', [])) if harvest.exists() else None
    asm = run / 'assembly-notes.json'
    if asm.exists():
        a = json.loads(asm.read_text())
        entry['file_cards'] = len(a.get('file_cards', []))
        entry['answer_blocks'] = a.get('blocks')
    else:
        entry['file_cards'] = None
        entry['answer_blocks'] = None
    dumps = sorted(run.glob('api-dump-*.json')) if run.exists() else []
    py_fences = write_calls = 0
    for dp in dumps:
        txt = dp.read_text(encoding='utf-8', errors='ignore')
        py_fences += txt.count('```python')
        write_calls += txt.count('"tcname":"write"') + txt.count('"tcname": "write"')
    entry['session_py_fences'] = py_fences
    entry['session_write_calls'] = write_calls
    if entry['case'] == 'exercism-py-6':
        rc = [c for c in out.get('checks', []) if c['id'] not in ('input_integrity',)]
        entry['receipt_tests'] = {
            c['id']: (c.get('completion') or {}).get('tests_run') for c in rc}
        entry['receipt_check_pass_false'] = all(c.get('pass') is False for c in rc)
        entry['receipt_detail'] = {
            c['id']: {'pass': c.get('pass'),
                      'succeeded': (c.get('completion') or {}).get('succeeded'),
                      'tests_run': (c.get('completion') or {}).get('tests_run'),
                      'note': c.get('note')} for c in rc}
    rows.append(entry)
doc = {
    'derivation': 'yuanbao-zero-constitution',
    'date': '2026-11-09',
    'posture': 'exploratory-derived (事后派生分析；零发射；不改正式行/判卷)',
    'boundary': '产品黑盒：交付缺失不能区分「agent 未产出」vs「产出未到交付终点」，按交付管线终点无产物登记，不作产品缺陷因果归因',
    'slots': rows,
    'summary': {
        'delivery_missing_slots': [r['slot'] for r in rows if r['delivery_missing']],
        'receipt_pass_false_slots': [r['slot'] for r in rows if r.get('receipt_check_pass_false')],
    },
}
dest = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('yuanbao-zero-constitution.json')
dest.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n')
print('slots=', len(rows), 'delivery_missing=', len(doc['summary']['delivery_missing_slots']),
      'receipt_pass_false=', len(doc["summary"]["receipt_pass_false_slots"]))
print('sha256=', hashlib.sha256(dest.read_bytes()).hexdigest())
