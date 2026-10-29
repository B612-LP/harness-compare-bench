#!/usr/bin/env python3
"""Synthetic trace tests for honest replay scope and claimed full projection.
No historical trace, model, CLI, checker, answer asset, or network is used.
"""
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile


def load(p, name):
    s = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--dsh-source', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    replay = load(a.source, 'replay_fixed_v3')
    lab = load(a.dsh_source, 'dsh_projection_fixed_v3')
    with tempfile.TemporaryDirectory(prefix='l4-independent-replay-') as td:
        root = Path(td).resolve()
        master = root / 'master'
        sess = master / 'agent-session'
        sess.mkdir(parents=True)
        events = [
            {'type': 'session', 'id': 'synthetic-session', 'cwd': '/synthetic/workspace'},
            {'type': 'turn/start', 'data': {'turn': 1}},
            {'type': 'step/start', 'data': {'turn': 1, 'step': 1}},
            {'type': 'assistant/message', 'data': {'turn': 1, 'step': 1, 'usage': {'inputTokens': 100, 'outputTokens': 10},
                'message': {'content': [{'type': 'reasoning', 'text': 'THINKING_MARKER_SYNTHETIC'},
                                        {'type': 'text', 'text': 'ASSISTANT_TEXT_SYNTHETIC'}]}}},
            {'type': 'tool/call', 'data': {'callId': 'call-synthetic', 'name': 'synthetic_tool', 'arguments': '{"marker":"TOOL_ARGUMENT_SYNTHETIC"}'}},
            {'type': 'tool/result', 'data': {'message': {'toolCallId': 'call-synthetic', 'content': [
                {'type': 'text', 'text': 'FULL_TOOL_RESULT_SYNTHETIC_' * 1000}]}}},
            {'type': 'step/end', 'data': {'turn': 1, 'step': 1}},
            {'type': 'turn/end', 'data': {'turn': 1, 'reason': {'kind': 'end_turn'}}}]
        (sess / 'synthetic.jsonl').write_text(''.join(json.dumps(e) + '\n' for e in events))
        (master / 'agent.jsonl').write_text('{"type":"synthetic raw projection"}\n')
        report = replay.replay(master, 'synthetic-case', root / 'work')
        cur = report['sandbox']['current']['postprocess']
        leg = report['sandbox']['legacy']['postprocess']
        replay_events = replay._rebuild_events(sess)
        lab_events = lab.rebuild_full_stream(sess)
        got = ''.join(json.dumps(e, ensure_ascii=False) + '\n' for e in replay_events)
        expected = ''.join(json.dumps(e, ensure_ascii=False) + '\n' for e in lab_events)
        checks = [
            {'id': 'master-immutable', 'pass': report['master']['untouched']},
            {'id': 'legacy-usage-unknown-no-session-rescue', 'pass': leg['usage']['status'] == 'unknown' and leg['usage']['requests'] is None},
            {'id': 'legacy-integrity-vacuous', 'pass': leg['integrity']['vacuous'] is True},
            {'id': 'score-both-explicitly-not-evaluated', 'pass': cur['score']['status'] == leg['score']['status'] == 'not_evaluated'},
            {'id': 'rebuilt-in-memory-bytes-and-hash-real', 'pass': cur['full_stream']['sha256'] == hashlib.sha256(got.encode()).hexdigest() and cur['full_stream']['bytes'] == len(got.encode())},
            {'id': 'full-projection-retains-reasoning', 'pass': 'THINKING_MARKER_SYNTHETIC' in got},
            {'id': 'full-projection-retains-tool-call', 'pass': 'TOOL_ARGUMENT_SYNTHETIC' in got},
            {'id': 'full-projection-retains-full-tool-result', 'pass': 'FULL_TOOL_RESULT_SYNTHETIC_' * 1000 in got},
            {'id': 'dsh-reference-retains-these-markers', 'pass': all(s in expected for s in ['THINKING_MARKER_SYNTHETIC', 'TOOL_ARGUMENT_SYNTHETIC', 'FULL_TOOL_RESULT_SYNTHETIC_' * 1000])}]
        observation = {'replay_events': replay_events, 'replay_event_types': [e['type'] for e in replay_events],
                       'dsh_event_types': [e['type'] for e in lab_events],
                       'replay_bytes': len(got.encode()), 'dsh_bytes': len(expected.encode()),
                       'replay_sha256': hashlib.sha256(got.encode()).hexdigest(),
                       'dsh_sha256': hashlib.sha256(expected.encode()).hexdigest(),
                       'replay_disclosure': report['adaptation_disclosure'],
                       'current_full_stream_claim': cur['full_stream']}
    result = {'category': 'self_test', 'scope': 'Independent synthetic replay semantic disclosure and projection coverage; no historical data or execution',
              'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'live_doc_drift': [],
              'source_sha256': sha(a.source), 'dsh_source_sha256': sha(a.dsh_source),
              'reviewer_script_sha256': sha(Path(__file__)), 'checks': checks, 'observation': observation,
              'passed': all(r['pass'] for r in checks)}
    with a.out.open('x') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({'checks': len(checks), 'passed': sum(r['pass'] for r in checks),
                      'failed': [r['id'] for r in checks if not r['pass']], 'out': str(a.out)}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
