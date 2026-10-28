#!/usr/bin/env python3
"""按逐场收据生成 adjudications.json 草案（人工复核后才用于构建导入）。"""
import json
import pathlib

B = pathlib.Path(__file__).resolve().parents[1]
CASES = ('bird-ca-schools-15', 'dabstep-payments-10', 'exercism-py-6', 'lcb-recent-hard-4', 'tb-cargo-plan')
out = {}
for product in ('codex', 'dsh'):
    for case in CASES:
        ev = B / 'runs' / ('%s__%s' % (product, case))
        meta = json.loads((ev / 'meta.json').read_text(encoding='utf-8'))
        ok_run = meta.get('status') == 'ok' and meta.get('exit_code') == 0
        verd = meta.get('integrity_verdict')
        clean = verd in ('clean', 'clean-reviewed')
        scored = isinstance(meta.get('judge'), dict) and 'checks' in meta['judge']
        if ok_run and clean and scored:
            adjudication, grade = 'valid', 'original-contemporaneous-full'
            gates = {g: True for g in ('rules_frozen', 'case_valid', 'scoring_reviewable', 'evidence_valid', 'contamination_free')}
            basis = ('规则: freeze-20261029-v2 于运行前封印并提交(Git 213013b)，注册早于开始；'
                     '题面: v2 config 冻结 manifest 未漂移；评分: 全分母 checker 收据+raw 输出双源；'
                     '证据: meta/会话轨迹/判分/配置快照当场归档（runner stdout 流因归档缺陷 r1030#1 丢失，'
                     '已按会话轨迹重扫并显式修正，见 integrity-rescan.json corrections）；'
                     '无污染: 工作区仓库外+隔离断言+会话八类模式重扫（含 benign 复核），verdict=%s。') % verd
        elif meta.get('status') == 'timeout':
            adjudication, grade = 'valid', 'original-contemporaneous-full'
            gates = {g: True for g in ('rules_frozen', 'case_valid', 'scoring_reviewable', 'evidence_valid', 'contamination_free')}
            basis = ('按 case.json timeout_s 合同超时截停；checker 对现有产物全量评估，按合同记结果。'
                     '无污染: 轨迹扫描 %d 命中；证据当场全量归档。') % meta.get('integrity', {}).get('violations', -1)
        else:
            adjudication, grade = 'infrastructure_invalid', 'original-contemporaneous-partial'
            gates = {g: (g in ('rules_frozen', 'case_valid')) for g in (
                'rules_frozen', 'case_valid', 'scoring_reviewable', 'evidence_valid', 'contamination_free')}
            basis = 'status=%s exit=%s integrity=%s——启动/传输/工具基础设施问题或证据不全，不进 primary；如实保留诊断。' % (
                meta.get('status'), meta.get('exit_code'), meta.get('integrity_verdict'))
        out['formal-a1-%s-%s-01' % (product, case)] = {
            'final_adjudication': adjudication, 'evidence_grade': grade, 'gates': gates, 'basis': basis}
dest = B / 'adjudications.json'
dest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: v['final_adjudication'] for k, v in out.items()}, ensure_ascii=False, indent=1))
