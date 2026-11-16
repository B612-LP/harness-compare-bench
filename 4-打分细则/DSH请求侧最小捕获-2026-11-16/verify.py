#!/usr/bin/env python3
"""Request-side capture verifier for the DSH headless minimal capture (until14-20261117).

Private rebuild reads the local proxy capture directory and the run stdout log,
derives content-free structural evidence (roles as kinds+byte sizes, tool names,
hashes, counts), and validates it.  Public mode validates evidence only and never
sees raw bodies.

Stdlib only.  Usage:
  python3 verify.py --archive-root DIR [--workspace DIR] \
      --build-evidence E.json --output R.json
  python3 verify.py --evidence E.json --output R.json
"""
import argparse, hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.dirname(os.path.dirname(HERE))

BASELINE = '50c073c084006c0bfd5f8b79db3bc495e842847b'
READ_ME = 'README.md'

# ---- pinned private provenance (SHA-256 only, no content) ----
PINS = {
    'proxy_script': 'capture_proxy.py',
    'run_stdout': 'real-run-stdout.json',
    'run_stderr': 'real-run-stderr.log',
}
PROXY_START = {
    'listen': '127.0.0.1:8791',
    'upstream': 'https://open.bigmodel.cn:443',
}
CAPTURE_SEQS = (1, 2, 3)
LOOP_SEQS = (1, 3)
AUX_SEQ = 2
REQUEST_PATH = '/api/coding/paas/v4/chat/completions'
MODEL = 'glm-5.3-flash'
TOOL_NAMES = ['bash', 'create_goal', 'edit', 'get_goal', 'glob', 'grep', 'job_kill',
              'job_list', 'job_output', 'list_agents', 'read', 'read_image',
              'send_message', 'skill', 'subagent', 'subagent_fork', 'todo_write',
              'update_goal', 'wait_agent', 'workflow', 'working_directory', 'write']
WORKSPACE_FILES = {
    'TASK.md': '68599aec2f4a1201c6eb9e46ba92a76d5b68a3cb96f1154e24d8edbe588c3f2c',
    'inputs/exercises/dominoes/dominoes.py':
        '89f1fede34db8dbd73fb7103476080307e769425049014bf60b7d5e632f9743b',
}
# frozen expectations for the single captured run (prefix roles: kind+bytes)
REQ1_ROLES = [['system', 'str', 2593], ['user', 'str', 214], ['user', 'str', 3111],
              ['user', 'str', 679], ['user', 'str', 5525]]
REQ3_APPENDED = [['assistant', 'none', 0], ['tool', 'str', 227], ['tool', 'str', 203]]
REQ2_ROLES = [['system', 'str', 481], ['user', 'str', 302]]
REQ_BYTES = {1: 33091, 2: 1042, 3: 34107}
REQ_SHAS = {
    1: '92220699f215bbdfe0faa392587b8fc43ad6793f10da6baf8b7541518120ac10',
    2: '9f2b6b3e9b76dde704dd763efc1e60992ec2c798c987ae577c784ddd63e34e76',
    3: '19e98d96ebfb3ade2dac6315b2f61f8fe45d50dcc9dca9fb8c888213cf06b8b4',
}


class Invalid(Exception):
    pass


def require(ok, message):
    if not ok:
        raise Invalid(message)


def no_duplicate_keys(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise Invalid('duplicate key %r' % k)
        out[k] = v
    return out


def loads(raw):
    require(isinstance(raw, (bytes, str)), 'payload type')
    text = raw.decode('utf-8') if isinstance(raw, bytes) else raw
    return json.loads(text, object_pairs_hook=no_duplicate_keys,
                      parse_constant=lambda c: (_ for _ in ()).throw(Invalid('non-finite %s' % c)))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def content_shape(message):
    """Classify one message into (role, kind, byte_size) without retaining content."""
    role = message.get('role')
    content = message.get('content')
    if isinstance(content, str):
        return role, 'str', len(content.encode('utf-8'))
    if content is None:
        return role, 'none', 0
    if isinstance(content, list):
        return role, 'list', len(json.dumps(content, ensure_ascii=False).encode('utf-8'))
    raise Invalid('unsupported content type %s' % type(content).__name__)


def tool_calls_of(message):
    calls = message.get('tool_calls') or []
    names = []
    for call in calls:
        fn = call.get('function') or {}
        names.append(fn.get('name'))
    return names


def request_shape(body):
    tools = body.get('tools') or []
    names = []
    for t in tools:
        fn = t.get('function') or {}
        names.append(fn.get('name'))
    thinking = body.get('thinking') or {}
    return {
        'model': body.get('model'),
        'stream': body.get('stream'),
        'stream_options_present': 'stream_options' in body,
        'max_tokens': body.get('max_tokens'),
        'thinking_type': thinking.get('type'),
        'top_keys': sorted(body.keys()),
        'n_messages': len(body.get('messages') or []),
        'roles': [list(content_shape(m)) for m in body.get('messages') or []],
        'n_tools': len(tools),
        'tool_names': names,
    }


def read_pinned(root, relative, expected):
    path = os.path.join(root, relative)
    require(os.path.isfile(path), 'missing pinned file %s' % relative)
    raw = open(path, 'rb').read()
    require(sha(raw) == expected, 'pin mismatch %s' % relative)
    return raw


def safe_join(root, relative):
    root_abs = os.path.realpath(root)
    path = os.path.realpath(os.path.join(root_abs, relative))
    require(path == root_abs or path.startswith(root_abs + os.sep), 'path escape %s' % relative)
    return path


def read_capture(archive_root, workspace):
    start = loads(open(safe_join(archive_root, 'capture/PROXY-START.json'), 'rb').read())
    require(start.get('listen') == PROXY_START['listen'], 'proxy listen mismatch')
    require(start.get('upstream') == PROXY_START['upstream'], 'proxy upstream mismatch')
    summary_lines = [l for l in open(safe_join(archive_root, 'capture/summary.jsonl'), 'r', encoding='utf-8').read().split('\n') if l]
    require(len(summary_lines) == 3, 'expected 3 summary lines')
    summaries = {}
    for line in summary_lines:
        row = loads(line)
        summaries[row['seq']] = row
    require(sorted(summaries) == [1, 2, 3], 'summary seqs')

    shapes = {}
    bodies = {}
    for seq in CAPTURE_SEQS:
        req_path = safe_join(archive_root, 'capture/requests/%03d.request.bin' % seq)
        raw = open(req_path, 'rb').read()
        require(len(raw) == REQ_BYTES[seq], 'request %d byte count' % seq)
        require(sha(raw) == REQ_SHAS[seq], 'request %d sha' % seq)
        body = loads(raw)
        bodies[seq] = body
        meta = loads(open(safe_join(archive_root, 'capture/responses/%03d.response.bin.meta.json' % seq), 'rb').read())
        require(meta.get('method') == 'POST', 'meta method')
        require(meta.get('path') == REQUEST_PATH, 'meta path')
        headers = meta.get('request_headers') or {}
        auth = ''
        for k, v in headers.items():
            if k.lower() == 'authorization':
                auth = v
                break
        require(auth.startswith('sha256:') and auth.endswith('...'), 'authorization must be masked')
        require('Bearer' not in auth, 'authorization leaked')
        resp_path = safe_join(archive_root, 'capture/responses/%03d.response.bin' % seq)
        resp_raw = open(resp_path, 'rb').read()
        require(meta.get('response_body_bytes') == len(resp_raw), 'response byte count')
        require(meta.get('response_body_sha256') == sha(resp_raw), 'response sha')
        require(meta.get('error') is None, 'meta error')
        row = summaries[seq]
        require(row.get('upstream_status') == 200, 'upstream status')
        require(row.get('request_body_bytes') == len(raw), 'summary request bytes')
        shape = request_shape(body)
        shape.update({
            'seq': seq,
            'request_bytes': len(raw),
            'request_sha256': sha(raw),
            'response_bytes': len(resp_raw),
            'response_sha256': sha(resp_raw),
            'upstream_status': 200,
            'duration_ms': meta.get('duration_ms'),
        })
        shapes[seq] = shape
    for seq in LOOP_SEQS:
        require(shapes[seq]['model'] == MODEL, 'model')
        require(shapes[seq]['n_tools'] == len(TOOL_NAMES), 'tool count')
        require(sorted(shapes[seq]['tool_names']) == TOOL_NAMES, 'tool names')
    require(shapes[AUX_SEQ]['n_tools'] == 0, 'aux request must carry no tools')

    msgs1 = bodies[1].get('messages') or []
    msgs3 = bodies[3].get('messages') or []
    prefix_identity = msgs3[:len(msgs1)] == msgs1 and len(msgs3) >= len(msgs1)
    appended = shapes[3]['roles'][len(shapes[1]['roles']):]
    require(prefix_identity, 'request 3 must extend request 1 as a prefix')
    delta_bytes = shapes[3]['request_bytes'] - shapes[1]['request_bytes']

    stdout_path = os.path.join(archive_root, PINS['run_stdout'])
    steps = []
    final_text_sha = None
    session_id = None
    for line in open(stdout_path, 'r', encoding='utf-8').read().split('\n'):
        if not line.strip():
            continue
        event = loads(line)
        if event.get('type') == 'session':
            session_id = event.get('sessionId')
        if event.get('type') == 'status' and event.get('phase') == 'step_end':
            usage = event.get('usage') or {}
            steps.append({'step': event.get('step'), 'usage': usage})
        if event.get('type') == 'final':
            text = event.get('text')
            final_text_sha = sha(text.encode('utf-8')) if isinstance(text, str) else None
    require(session_id, 'stdout session id')
    require(len(steps) == 2, 'expected 2 agent steps')

    workspace_evidence = {}
    for rel, expected in WORKSPACE_FILES.items():
        path = safe_join(workspace, rel)
        raw = open(path, 'rb').read()
        require(sha(raw) == expected, 'workspace file %s' % rel)
        workspace_evidence[rel] = {'bytes': len(raw), 'sha256': expected}
    return {
        'proxy_start': start,
        'shapes': shapes,
        'prefix_identity': prefix_identity,
        'appended_roles': appended,
        'delta_request_bytes': delta_bytes,
        'steps': steps,
        'final_text_sha256': final_text_sha,
        'session_id_sha256': sha(session_id.encode('utf-8')),
        'workspace': workspace_evidence,
    }


def build(archive_root, workspace):
    rebuilt = read_capture(archive_root, workspace)
    evidence = {
        'schema': 'dsh-request-capture-evidence-v1',
        'baseline': BASELINE,
        'generated_from': {
            'archive_layout': 'capture/{PROXY-START.json,summary.jsonl,requests/*.request.bin,responses/*.response.bin*}',
            'private_pins': {},
        },
        'capture': {
            'listen': PROXY_START['listen'],
            'upstream': PROXY_START['upstream'],
            'requests': [],
        },
        'prefix_identity': {
            'req1_prefix_of_req3': rebuilt['prefix_identity'],
            'req3_appended_roles': rebuilt['appended_roles'],
            'delta_request_bytes': rebuilt['delta_request_bytes'],
        },
        'agent_steps': rebuilt['steps'],
        'final_text_sha256': rebuilt['final_text_sha256'],
        'session_id_sha256': rebuilt['session_id_sha256'],
        'workspace': rebuilt['workspace'],
    }
    priv = evidence['generated_from']['private_pins']
    for key, rel in PINS.items():
        raw = open(safe_join(archive_root, rel), 'rb').read()
        priv[key] = sha(raw)
    priv['capture_dir'] = sha(json.dumps(sorted(
        os.path.relpath(os.path.join(dp, f), archive_root)
        for dp, _, fs in os.walk(safe_join(archive_root, 'capture')) for f in fs
    ), sort_keys=True).encode('utf-8'))
    for seq in CAPTURE_SEQS:
        s = rebuilt['shapes'][seq]
        evidence['capture']['requests'].append({
            'seq': s['seq'], 'kind': 'loop' if seq in LOOP_SEQS else 'auxiliary',
            'model': s['model'], 'stream': s['stream'],
            'stream_options_present': s['stream_options_present'],
            'max_tokens': s['max_tokens'], 'thinking_type': s['thinking_type'],
            'top_keys': s['top_keys'], 'n_messages': s['n_messages'],
            'roles': s['roles'], 'n_tools': s['n_tools'], 'tool_names': s['tool_names'],
            'request_bytes': s['request_bytes'], 'request_sha256': s['request_sha256'],
            'response_bytes': s['response_bytes'], 'response_sha256': s['response_sha256'],
            'upstream_status': s['upstream_status'], 'duration_ms': s['duration_ms'],
        })
    return evidence


def validate_public(evidence):
    require(evidence.get('schema') == 'dsh-request-capture-evidence-v1', 'schema')
    require(evidence.get('baseline') == BASELINE, 'baseline')
    reqs = evidence.get('capture', {}).get('requests') or []
    require(len(reqs) == 3, 'three requests')
    expected_shapes = {1: (REQ1_ROLES, 'disabled', 128000), 2: (REQ2_ROLES, 'enabled', 4096),
                       3: (REQ1_ROLES + REQ3_APPENDED, 'disabled', 128000)}
    for r in reqs:
        require(r['request_sha256'] == REQ_SHAS[r['seq']], 'request sha pin')
        require(r['request_bytes'] == REQ_BYTES[r['seq']], 'request bytes pin')
        require(r['model'] == MODEL, 'model')
        require(r['upstream_status'] == 200, 'status')
        require(r['request_sha256'] != r['response_sha256'], 'request/response distinct')
        exp_roles, exp_think, exp_max = expected_shapes[r['seq']]
        require(r['roles'] == exp_roles, 'roles pin seq %d' % r['seq'])
        require(r['thinking_type'] == exp_think, 'thinking pin seq %d' % r['seq'])
        require(r['max_tokens'] == exp_max, 'max_tokens pin seq %d' % r['seq'])
        for role in r['roles']:
            require(role[0] in ('system', 'user', 'assistant', 'tool'), 'role name')
            require(role[1] in ('str', 'none', 'list'), 'content kind')
            require(isinstance(role[2], int) and role[2] >= 0, 'content bytes')
    loop = [r for r in reqs if r['kind'] == 'loop']
    require(len(loop) == 2, 'two loop requests')
    aux = [r for r in reqs if r['kind'] == 'auxiliary']
    require(len(aux) == 1 and aux[0]['n_tools'] == 0, 'aux request toolless')
    for r in loop:
        require(r['n_tools'] == len(TOOL_NAMES) and sorted(r['tool_names']) == TOOL_NAMES, 'loop tool names')
        for role in r['roles']:
            require(role[0] in ('system', 'user', 'assistant', 'tool'), 'role name')
            require(role[1] in ('str', 'none', 'list'), 'content kind')
            require(isinstance(role[2], int) and role[2] >= 0, 'content bytes')
    loop = [r for r in reqs if r['kind'] == 'loop']
    require(len(loop) == 2, 'two loop requests')
    aux = [r for r in reqs if r['kind'] == 'auxiliary']
    require(len(aux) == 1 and aux[0]['n_tools'] == 0, 'aux request toolless')
    seq1 = next(r for r in reqs if r['seq'] == 1)
    seq3 = next(r for r in reqs if r['seq'] == 3)
    require(seq1['roles'] == seq3['roles'][:len(seq1['roles'])], 'prefix identity')
    pi = evidence.get('prefix_identity') or {}
    require(pi.get('req1_prefix_of_req3') is True, 'prefix verdict')
    require(pi.get('delta_request_bytes') == REQ_BYTES[3] - REQ_BYTES[1], 'delta bytes')
    steps = evidence.get('agent_steps') or []
    require(len(steps) == 2, 'two steps')
    for st in steps:
        u = st.get('usage') or {}
        require(isinstance(u.get('inputTokens'), int) and u.get('inputTokens') >= 0, 'usage input')
    for key in ('final_text_sha256', 'session_id_sha256'):
        v = evidence.get(key)
        require(isinstance(v, str) and len(v) == 64, key)
    ws = evidence.get('workspace') or {}
    require(set(ws) == set(WORKSPACE_FILES), 'workspace files')
    for rel, row in ws.items():
        require(row['sha256'] == WORKSPACE_FILES[rel], 'workspace sha %s' % rel)
    priv = (evidence.get('generated_from') or {}).get('private_pins') or {}
    require(len(priv) >= 4, 'private pins')
    return True


def result_for(evidence, evidence_sha):
    validate_public(evidence)
    seq1 = next(r for r in evidence['capture']['requests'] if r['seq'] == 1)
    seq3 = next(r for r in evidence['capture']['requests'] if r['seq'] == 3)
    aux = next(r for r in evidence['capture']['requests'] if r['kind'] == 'auxiliary')
    return {
        'schema': 'dsh-request-capture-result-v1',
        'baseline': BASELINE,
        'evidence_sha256': evidence_sha,
        'run': {
            'product': 'dsh-headless',
            'real_runs': 1,
            'provider_declared': 'zai-coding-cn/glm-5.3-flash (default deepseek-official route bypassed by design, see README)',
        },
        'endpoints': {
            'q1_history_overflow': {
                'verdict': 'append_only_prefix_extended',
                'req1_prefix_of_req3': evidence['prefix_identity']['req1_prefix_of_req3'],
                'n_messages_req1': seq1['n_messages'], 'n_messages_req3': seq3['n_messages'],
                'appended_roles': evidence['prefix_identity']['req3_appended_roles'],
            },
            'q2_truncation_reorg': {
                'verdict': 'no_truncation_or_reorg_witness_in_this_run',
                'delta_request_bytes': evidence['prefix_identity']['delta_request_bytes'],
            },
            'q3_bytes_vs_reported_tokens': {
                'verdict': 'descriptive_only_n1',
                'rows': [
                    {'seq': 1, 'request_bytes': seq1['request_bytes'],
                     'step1_reported_input_tokens': evidence['agent_steps'][0]['usage'].get('inputTokens')},
                    {'seq': 3, 'request_bytes': seq3['request_bytes'],
                     'step2_reported_input_tokens': evidence['agent_steps'][1]['usage'].get('inputTokens'),
                     'step2_reported_cache_read_tokens': evidence['agent_steps'][1]['usage'].get('cacheReadTokens')},
                ],
            },
            'q4_system_and_tools': {
                'verdict': 'structure_only',
                'system_role_bytes_req1': seq1['roles'][0][2],
                'n_tools': seq1['n_tools'],
                'aux_title_request': {'seq': aux['seq'], 'max_tokens': aux['max_tokens'],
                                      'thinking_type': aux['thinking_type'], 'n_tools': aux['n_tools']},
            },
        },
        'limits': [
            'n=1 single task; no generalization to other tasks or providers',
            'public evidence contains no request/response content; only structure, byte counts and hashes',
            'prefix verdict computed at build time from full message content; public replay re-checks shape-level prefix only (byte truth carried by pinned request hashes)',
            'auxiliary request purpose inferred from shape (no tools, small max_tokens, thinking enabled), not from product source claims',
            'bytes are transport-level; no claim about provider-side tokenization or cache semantics',
        ],
    }


def exclusive(path, raw):
    if os.path.exists(path):
        raise SystemExit('output already exists: %s' % path)
    parent = os.path.dirname(os.path.abspath(path))
    if not os.path.isdir(parent):
        raise SystemExit('missing parent directory: %s' % parent)
    with open(path, 'xb') as f:
        f.write(raw)


def dump(path, value):
    exclusive(path, json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode('utf-8') + b'\n')


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=DEFAULT_ROOT)
    ap.add_argument('--archive-root')
    ap.add_argument('--workspace')
    ap.add_argument('--build-evidence')
    ap.add_argument('--evidence')
    ap.add_argument('--output', required=True)
    args = ap.parse_args(argv)
    readme = os.path.join(args.root, os.path.relpath(HERE, args.root), READ_ME)
    if not os.path.isfile(readme):
        raise SystemExit('missing protocol README under repo root')
    if args.evidence:
        require(args.build_evidence is None, '--evidence and --build-evidence are exclusive')
        raw = open(args.evidence, 'rb').read()
        evidence = loads(raw)
        result = result_for(evidence, sha(raw))
    else:
        require(args.archive_root and args.workspace, 'raw rebuild needs --archive-root and --workspace')
        evidence = build(args.archive_root, args.workspace)
        if args.build_evidence:
            dump(args.build_evidence, evidence)
            evidence_sha = sha(open(args.build_evidence, 'rb').read())
        else:
            evidence_sha = sha(json.dumps(evidence, ensure_ascii=False, sort_keys=True).encode('utf-8'))
        result = result_for(evidence, evidence_sha)
    dump(args.output, result)
    verdicts = result['endpoints']
    print('q1=%s q2=%s q4.system_bytes=%s requests=%d' % (
        verdicts['q1_history_overflow']['verdict'],
        verdicts['q2_truncation_reorg']['verdict'],
        verdicts['q4_system_and_tools']['system_role_bytes_req1'],
        len(evidence['capture']['requests'])))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Invalid as error:
        print('invalid: %s' % error, file=sys.stderr)
        sys.exit(2)
