#!/usr/bin/env python3
"""复制实验显式导入适配器：研究事件入六账（不入官方表），原始收据原样打包。"""
import datetime
import hashlib
import json
import pathlib

R = pathlib.Path(__file__).resolve().parents[2]
E = pathlib.Path(__file__).resolve().parent
now = datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(p):
    return {'path': str(pathlib.Path(p).relative_to(R)), 'sha256': hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()}


def load(p):
    return json.loads(pathlib.Path(p).read_text())


items = []
# DSH 复制场
for d in sorted(E.glob('evidence-dsh/repl-dsh-*')):
    m = load(d / 'run-meta.json')
    tr1 = load(d / '01-transport.json')
    status = [load(d / x) for x in ('01-capture-status.json', '02-capture-status.json')]
    sse_ok = all((d / f).exists() and (d / f).stat().st_size > 0 for f in ('01-response.sse', '02-response.sse'))
    facts = {'case_version': 'fixture-v1-replication',
             'product_version': m['environment_dsh'] if 'environment_dsh' in m else '0.2.0-rc.2',
             'model': m['model'],
             'route': {'host': tr1['host'], 'provider_id': m['model']['provider'],
                       'wire_protocol': 'anthropic-messages', 'endpoint': 'https://' + tr1['host'] + tr1['path']},
             'tools': m['tool_names'], 'permissions': m['permissions'], 'skills': m['skills'],
             'started_at': m['start'], 'finished_at': m['end'],
             'evidence_grade': ('real-api/request-body/raw-SSE(both calls,message_stop)/usage'
                                if sse_ok and all(s.get('message_stop_seen') for s in status)
                                else 'real-api/partial-observer'),
             'final_adjudication': 'exact-head-tail-pass; research-only; no official score'}
    items.append({'kind': 'product_run', 'run_id': m['run_id'], 'product': 'dsh', 'case_id': 'fixture-v1-replication',
                  'start': m['start'], 'facts': facts, 'origins': [
                      d / 'run-meta.json', d / '01-request.json', d / '02-request.json',
                      d / '01-transport.json', d / '01-response.sse', d / '02-response.sse',
                      d / '01-capture-status.json', d / '02-capture-status.json', d / 'tool-process.json', d / 'stdout.txt']})
# Codex 复制场
for d in sorted(E.glob('evidence-codex/repl-codex-*')):
    m = load(d / 'run-meta.json')
    facts = {'case_version': 'fixture-v1-replication',
             'product_version': m['product_version'], 'model': 'deepseek-flash',
             'route': m['route'], 'tools': ['fixture_output（MCP stdio）'],
             'permissions': m['permissions'], 'skills': m['skills'],
             'started_at': m['start'], 'finished_at': m['end'],
             'evidence_grade': 'real-api/product-reported-usage(rollout token_count); no request-level capture',
             'final_adjudication': 'exact-head-tail-pass; research-only; no official score'}
    items.append({'kind': 'product_run', 'run_id': m['run_id'], 'product': 'codex', 'case_id': 'fixture-v1-replication',
                  'start': m['start'], 'facts': facts, 'origins': [
                      d / 'run-meta.json', d / 'session-rollout.jsonl', d / 'codex-config.toml',
                      d / 'capture' / 'tool-process.json', d / 'capture' / 'mcp-server-log.jsonl', d / 'stdout.txt']})
# DSH 预检
for pf in sorted(E.glob('evidence-dsh/preflight-*')):
    rc = load(pf / 'receipt.json')
    items.append({'kind': 'interface_preflight', 'run_id': pf.name, 'product': 'dsh',
                  'case_id': 'mechanism-replication-preflight', 'start': rc.get('at'),
                  'facts': {'started_at': rc.get('at'), 'note': 'dump-config preflight receipt time; zero model calls'},
                  'origins': [pf / 'receipt.json', pf / 'stdout.txt']})

adapter = {'schema_version': 1, 'created_at': now,
           'provenance': 'Replication events; research-only, never official. Original receipts untouched.',
           'items': [{'kind': it['kind'], 'run_id': it['run_id'], 'product': it['product'],
                      'case_id': it['case_id'], 'facts': it['facts'],
                      'identity': {'event_id': ('repl-' if it['kind'] == 'product_run' else 'repl-preflight-') + it['run_id'],
                                   'run_id': it['run_id'], 'category': it['kind'], 'product': it['product'],
                                   'group': 'research', 'experiment': True, 'case_id': it['case_id']}} for it in items]}
adapter_path = E / 'replication-adapter.json'
adapter_path.write_text(json.dumps(adapter, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

events = []
for i, it in enumerate(items):
    is_product = it['kind'] == 'product_run'
    event = {'event_id': ('repl-' if is_product else 'repl-preflight-') + it['run_id'],
             'category': it['kind'], 'product': it['product'],
             'group': 'research', 'experiment': True, 'case_id': it['case_id'],
             'identity': {'state': 'supplemented', 'value': {'event_id': ('repl-' if is_product else 'repl-preflight-') + it['run_id'],
                          'run_id': it['run_id'], 'category': it['kind'], 'product': it['product'],
                          'group': 'research', 'experiment': True, 'case_id': it['case_id']},
                          'refs': [{'source': 0, 'pointer': '/items/%d/identity' % i}]},
             'facts': {k: {'state': 'supplemented', 'value': v, 'refs': [{'source': 0, 'pointer': '/items/%d/facts/%s' % (i, k)}]}
                       for k, v in it['facts'].items()},
             'gates': {g: {'state': 'unknown', 'value': None, 'refs': []}
                       for g in ('rules_frozen', 'case_valid', 'scoring_reviewable', 'evidence_valid', 'contamination_free')},
             'score': {'state': 'unknown', 'value': None, 'refs': []},
             'selection': None,
             'sources': [{'path': str(adapter_path.relative_to(R)), 'sha256': hashlib.sha256(adapter_path.read_bytes()).hexdigest()}]
             + [sha(o) for o in it['origins']],
             'collected_at': now,
             'original_time': {'state': 'supplemented', 'value': it['start'], 'refs': [{'source': 0, 'pointer': '/items/%d/facts/started_at' % i}]}
             if it['start'] else {'state': 'unknown', 'value': None, 'refs': []},
             'issues': []}
    unknown = []
    if is_product:
        for k in ('rule_version', 'checker_sha256', 'truth_sha256', 'case_sha256'):
            event['facts'][k] = {'state': 'unknown', 'value': None, 'refs': []}
        unknown += (['facts.rule_version', 'facts.checker_sha256', 'facts.truth_sha256', 'facts.case_sha256', 'score']
                    + ['gates.' + g for g in ('rules_frozen', 'case_valid', 'scoring_reviewable', 'evidence_valid', 'contamination_free')])
    else:
        unknown = (['score', 'facts.case_version', 'facts.model', 'facts.tools', 'facts.permissions', 'facts.skills',
                    'facts.started_at', 'facts.finished_at', 'facts.evidence_grade', 'facts.final_adjudication',
                    'facts.route', 'facts.product_version']
                   + ['gates.' + g for g in ('rules_frozen', 'case_valid', 'scoring_reviewable', 'evidence_valid', 'contamination_free')])
    if unknown:
        event['issues'].append({'id': 'research-non-scored-no-hidden-truth', 'unknown_fields': unknown,
                                'knowledge_status': 'accepted_limitation', 'investigation_status': 'stopped',
                                'confound_status': 'not_applicable',
                                'impact': 'Research mechanism diagnostic has no official normalized score; synthetic observation inputs use no hidden truth asset. Unknown does not mean failure or full credit.',
                                'next_step': 'Use the published usage comparison and raw-SSE evidence; never infer an official score.',
                                'stop_condition': 'No official-score conversion is performed for this diagnostic.',
                                'reopen_condition': 'Only a separately frozen scoring contract would reopen these fields.',
                                'refs': [{'source': 0, 'pointer': '/items/%d' % i}]})
    events.append(event)

out = E / 'replication-events.json'
out.write_text(json.dumps({'schema_version': 1, 'events': events}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'events': len(events), 'product_runs': sum(e['category'] == 'product_run' for e in events)}, ensure_ascii=False))
