#!/usr/bin/env python3
"""复制实验离线分析：严格读收据，不联网、不改原始证据。输出对照 JSON + RESULTS 数据段。

- DSH：逐请求解析 NN-response.sse 的 usage（input_tokens + cache_read + cache_creation 为总输入口径），
  并核对 capture-status 的 message_stop_seen 与 raw_response_sha256 存在性。
- Codex：解析 session-rollout.jsonl 的 token_count 事件 last_token_usage（产品自报，语义字段原样披露）。
"""
import hashlib
import json
import pathlib
import sys

R = pathlib.Path(__file__).resolve().parents[2]
E = pathlib.Path(__file__).resolve().parent


def dsh_usage(run_dir: pathlib.Path):
    calls = []
    for req in sorted(run_dir.glob('*-request.json')):
        rid = req.name[:2]
        sse = run_dir / (rid + '-response.sse')
        meta = run_dir / (rid + '-response-meta.json')
        status = run_dir / (rid + '-capture-status.json')
        call = {'call': rid, 'request_file': req.name,
                'input_bytes': req.stat().st_size,
                'request_sha256': hashlib.sha256(req.read_bytes()).hexdigest(),
                'response_meta': json.loads(meta.read_text()) if meta.exists() else None,
                'raw_sse_present': sse.exists(),
                'raw_sse_bytes': sse.stat().st_size if sse.exists() else 0,
                'message_stop_seen': None, 'usage': None, 'usage_source': None}
        if status.exists():
            call['message_stop_seen'] = json.loads(status.read_text()).get('message_stop_seen')
            call['raw_response_sha256'] = json.loads(status.read_text()).get('raw_response_sha256')
        if sse.exists():
            usage = {}
            for line in sse.read_text(encoding='utf-8', errors='replace').splitlines():
                if line.startswith('data: '):
                    try:
                        ev = json.loads(line[6:])
                    except Exception:
                        continue
                    u = ev.get('usage') or (ev.get('message') or {}).get('usage') or {}
                    if isinstance(u, dict) and any(k in u for k in ('input_tokens', 'output_tokens')):
                        usage = u
            if usage:
                call['usage'] = usage
                call['usage_source'] = 'raw-sse-final-usage'
                call['input_total_including_cache'] = sum(
                    usage.get(k, 0) or 0 for k in ('input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens'))
                call['output_tokens'] = usage.get('output_tokens')
        calls.append(call)
    return calls


def codex_usage(run_dir: pathlib.Path):
    roll = run_dir / 'session-rollout.jsonl'
    calls = []
    if not roll.exists():
        return calls
    for line in roll.read_text(encoding='utf-8', errors='replace').splitlines():
        try:
            ev = json.loads(line)
        except Exception:
            continue
        payload = ev.get('payload') or ev
        if payload.get('type') == 'token_count':
            info = payload.get('info') or {}
            last = info.get('last_token_usage') or {}
            total = info.get('total_token_usage') or {}
            calls.append({'event_at': payload.get('timestamp'),
                          'last_token_usage': last, 'total_token_usage': total,
                          'model': info.get('model'),
                          'usage_source': 'product-reported-rollout-token_count'})
    return calls


def main():
    out = {}
    for run_dir in sorted(E.glob('evidence-dsh/repl-dsh-*')):
        if not run_dir.is_dir():
            continue
        out[run_dir.name] = {'product': 'DSH CLI', 'calls': dsh_usage(run_dir)}
    for run_dir in sorted(E.glob('evidence-codex/repl-codex-*')):
        if not run_dir.is_dir():
            continue
        out[run_dir.name] = {'product': 'Codex CLI', 'calls': codex_usage(run_dir),
                             'meta': json.loads((run_dir / 'run-meta.json').read_text()) if (run_dir / 'run-meta.json').exists() else None}
    dest = E / 'replication-analysis.json'
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for name, data in out.items():
        print('==', name, data['product'])
        for c in data['calls']:
            if data['product'] == 'DSH CLI':
                print('  call %s: raw_sse=%s(%sB) stop=%s input_total=%s output=%s' % (
                    c['call'], c['raw_sse_present'], c['raw_sse_bytes'], c['message_stop_seen'],
                    c.get('input_total_including_cache'), c.get('output_tokens')))
            else:
                print('  token_count: %s' % json.dumps(c['last_token_usage'], ensure_ascii=False)[:200])
    print('->', dest)


if __name__ == '__main__':
    sys.exit(main())
