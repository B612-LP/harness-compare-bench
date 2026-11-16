#!/usr/bin/env python3
"""Deep-chain usage/cache (t2-r1/t2-r2) evidence builder & public verifier.

Two modes (mutually exclusive):
  build:  --archive-root LOOP7 --build-evidence E.json --output R.json
          rebuilds 14 rows from private capture archives (loop7/t2-r1,t2-r2/responses)
  replay: --evidence E.json --output R.json
          validates the sealed public evidence against pinned constants and
          recomputes every endpoint from the rows themselves.

stdlib only; fail-closed (exit 2 on any violation); never overwrites outputs.
"""
import argparse, hashlib, json, sys
from pathlib import Path

SCHEMA = 'dsh-deepchain-usage-cache-evidence-v1'
BASELINE = '69a868a600215da5b3a8ebc4a77d63a8b6683279'
README_SHA256 = '849c96a45255e8831e124009526d9fa0fd3b0e19ba297af1fe0ad99d1685361a'
RUNS = ('t2-r1', 't2-r2')
SEQS = tuple(range(1, 8))
MAIN_SEQS = (1, 3, 4, 5, 6, 7)
AUX_SEQ = 2
FINISH_ALLOWED = ('tool_calls', 'stop')
USAGE_TOP_KEYS = {'prompt_tokens', 'completion_tokens', 'total_tokens',
                  'prompt_tokens_details', 'completion_tokens_details'}
PROMPT_DETAIL_KEYS = {'cached_tokens'}
COMPLETION_DETAIL_KEYS = {'reasoning_tokens'}
# Observed values (priors disclosed in the frozen README); pinned as constants.
PROMPT_EXPECT = (7597, 167, 7816, 7927, 8034, 8141, 8174)
CACHED_EXPECT = {'t2-r1': (0, 0, 7552, 7808, 7872, 8000, 8128),
                 't2-r2': (7552, 128, 7808, 7872, 8000, 8128, 8128)}
FINISH_EXPECT = {'t2-r1': ('tool_calls', 'stop', 'tool_calls', 'tool_calls', 'tool_calls', 'tool_calls', 'stop'),
                 't2-r2': ('tool_calls', 'stop', 'tool_calls', 'tool_calls', 'tool_calls', 'tool_calls', 'stop')}
CHUNKS_EXPECT = {'t2-r1': (22, 8, 25, 25, 25, 21, 5),
                 't2-r2': (22, 6, 27, 25, 25, 21, 5)}


class Invalid(Exception):
    pass


def require(cond, msg):
    if not cond:
        raise Invalid(msg)


def no_duplicate_keys(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise Invalid('duplicate key %r' % (k,))
        out[k] = v
    return out


def loads(raw):
    require(isinstance(raw, (bytes, str)), 'payload must be text')
    text = raw.decode('utf-8') if isinstance(raw, bytes) else raw
    return json.loads(text, object_pairs_hook=no_duplicate_keys,
                      parse_constant=lambda c: (_ for _ in ()).throw(Invalid('non-finite constant %s' % c)))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def integer(value, label):
    require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, '%s must be non-negative int' % label)
    return value


def parse_sse(text):
    chunks = []
    usage_seen = None
    finish = None
    for line in text.splitlines():
        if not line.startswith('data: '):
            continue
        body = line[6:].strip()
        if body == '[DONE]':
            continue
        obj = loads(body)
        require(isinstance(obj, dict), 'chunk must be object')
        chunks.append(obj)
        if obj.get('usage') is not None:
            require(usage_seen is None, 'multiple usage chunks')
            usage_seen = obj['usage']
        choices = obj.get('choices') or []
        if choices:
            fr = choices[0].get('finish_reason')
            if fr is not None:
                require(finish is None, 'multiple finish_reason chunks')
                finish = fr
    return chunks, usage_seen, finish


def usage_vector(usage):
    require(isinstance(usage, dict), 'usage must be object')
    require(set(usage) == USAGE_TOP_KEYS, 'usage top keys mismatch: %r' % (sorted(usage),))
    pd = usage['prompt_tokens_details']
    cd = usage['completion_tokens_details']
    require(isinstance(pd, dict) and set(pd) == PROMPT_DETAIL_KEYS, 'prompt detail keys mismatch')
    require(isinstance(cd, dict) and set(cd) == COMPLETION_DETAIL_KEYS, 'completion detail keys mismatch')
    vec = (integer(usage['prompt_tokens'], 'prompt_tokens'),
           integer(pd['cached_tokens'], 'cached_tokens'),
           integer(usage['completion_tokens'], 'completion_tokens'),
           integer(usage['total_tokens'], 'total_tokens'),
           integer(cd['reasoning_tokens'], 'reasoning_tokens'))
    require(vec[3] == vec[0] + vec[2], 'total != prompt+completion identity')
    return vec


def duration_bucket(ms):
    integer(ms, 'duration_ms')
    if ms < 2000:
        return 'lt2s'
    if ms < 8000:
        return 'lt8s'
    return 'ge8s'


def inspect_pair(run, seq, bin_path, meta_path):
    raw = bin_path.read_bytes()
    meta = loads(meta_path.read_bytes())
    require(isinstance(meta, dict), 'meta must be object')
    require(meta.get('response_body_sha256') == sha(raw), 'meta response sha mismatch for %s/%03d' % (run, seq))
    require(isinstance(meta.get('request_body_sha256'), str) and len(meta['request_body_sha256']) == 64,
            'meta request sha missing')
    text = raw.decode('utf-8')
    chunks, usage, finish = parse_sse(text)
    require(usage is not None, 'no usage chunk in %s/%03d' % (run, seq))
    vector = usage_vector(usage)
    require(finish in FINISH_ALLOWED, 'bad finish_reason %r' % (finish,))
    rec = {'run': run, 'seq': seq,
           'response_sha256': sha(raw),
           'request_body_sha256': meta['request_body_sha256'],
           'duration_bucket': duration_bucket(meta.get('duration_ms')),
           'sse_chunks': len(chunks),
           'finish_reason': finish,
           'prompt_tokens': vector[0], 'cached_tokens': vector[1],
           'completion_tokens': vector[2], 'total_tokens': vector[3],
           'reasoning_tokens': vector[4],
           'prompt_detail_keys': ['cached_tokens'],
           'completion_detail_keys': ['reasoning_tokens']}
    return rec


def vectors_from_rows(rows):
    out = {}
    for run in RUNS:
        sel = sorted((r for r in rows if r['run'] == run), key=lambda r: r['seq'])
        require(tuple(r['seq'] for r in sel) == SEQS, '%s seq coverage' % run)
        out[run] = {
            'prompt': tuple(r['prompt_tokens'] for r in sel),
            'cached': tuple(r['cached_tokens'] for r in sel),
            'finish': tuple(r['finish_reason'] for r in sel),
            'chunks': tuple(r['sse_chunks'] for r in sel),
        }
    return out


def check_endpoints(vectors):
    for run in RUNS:
        v = vectors[run]
        require(v['prompt'] == PROMPT_EXPECT, '%s prompt vector mismatch' % run)
        require(v['cached'] == CACHED_EXPECT[run], '%s cached vector mismatch' % run)
        require(v['finish'] == FINISH_EXPECT[run], '%s finish vector mismatch' % run)
        require(v['chunks'] == CHUNKS_EXPECT[run], '%s chunk vector mismatch' % run)
        main_cached = (v['cached'][0],) + v['cached'][2:]
        require(all(main_cached[i] <= main_cached[i + 1] for i in range(len(main_cached) - 1)),
                '%s main-chain cached not monotone' % run)
    diffs = sum(1 for a, b in zip(vectors['t2-r1']['cached'], vectors['t2-r2']['cached']) if a != b)
    prompt_equal = sum(1 for a, b in zip(vectors['t2-r1']['prompt'], vectors['t2-r2']['prompt']) if a == b)
    require(prompt_equal == 7, 'E1 prompt equal positions != 7')
    require(diffs == 6, 'E2 cached differing positions != 6')
    require(CACHED_EXPECT['t2-r2'][0] > 0, 'E2 first-request cache hit missing')
    return {'prompt_equal_positions': prompt_equal, 'cached_diff_positions': diffs,
            'cached_equal_positions': 7 - diffs, 'r2_first_request_cached': CACHED_EXPECT['t2-r2'][0],
            'monotone_main_chain': {'t2-r1': True, 't2-r2': True}}


def build(archive_root):
    base = Path(archive_root) / 'loop7' if (Path(archive_root) / 'loop7').is_dir() else Path(archive_root)
    rows = []
    for run in RUNS:
        for seq in SEQS:
            bin_path = base / run / 'responses' / ('%03d.response.bin' % seq)
            meta_path = base / run / 'responses' / ('%03d.response.bin.meta.json' % seq)
            require(bin_path.is_file() and meta_path.is_file(), 'missing source %s/%03d' % (run, seq))
            rows.append(inspect_pair(run, seq, bin_path, meta_path))
    vectors = vectors_from_rows(rows)
    endpoints = check_endpoints(vectors)
    return {'schema': SCHEMA, 'baseline': BASELINE, 'readme_sha256': README_SHA256,
            'rows': rows, 'endpoints': endpoints,
            'boundaries': ['product-reported counters only', 'exploratory post-hoc, priors disclosed in frozen README',
                           'response bodies and task text stay private',
                           'no provider/billing/KV-reuse mechanism certification']}


def validate_evidence(evidence):
    require(isinstance(evidence, dict), 'evidence must be object')
    require(evidence.get('schema') == SCHEMA, 'schema mismatch')
    require(evidence.get('baseline') == BASELINE, 'baseline mismatch')
    require(evidence.get('readme_sha256') == README_SHA256, 'readme pin mismatch')
    rows = evidence.get('rows')
    require(isinstance(rows, list) and len(rows) == 14, 'rows must be 14')
    row_keys = {'run', 'seq', 'response_sha256', 'request_body_sha256', 'duration_bucket', 'sse_chunks',
                'finish_reason', 'prompt_tokens', 'cached_tokens', 'completion_tokens', 'total_tokens',
                'reasoning_tokens', 'prompt_detail_keys', 'completion_detail_keys'}
    for r in rows:
        require(isinstance(r, dict) and set(r) == row_keys, 'row keys mismatch')
        require(r['run'] in RUNS, 'bad run')
        require(isinstance(r['seq'], int) and r['seq'] in SEQS, 'bad seq')
        require(isinstance(r['response_sha256'], str) and len(r['response_sha256']) == 64, 'bad response sha')
        require(isinstance(r['request_body_sha256'], str) and len(r['request_body_sha256']) == 64, 'bad request sha')
        require(r['duration_bucket'] in ('lt2s', 'lt8s', 'ge8s'), 'bad duration bucket')
        require(isinstance(r['sse_chunks'], int) and not isinstance(r['sse_chunks'], bool), 'bad chunks')
        for k in ('prompt_tokens', 'cached_tokens', 'completion_tokens', 'total_tokens'):
            integer(r[k], k)
        require(r['total_tokens'] == r['prompt_tokens'] + r['completion_tokens'], 'identity broken')
        require(r['prompt_detail_keys'] == ['cached_tokens'], 'prompt detail keys')
        require(r['completion_detail_keys'] == ['reasoning_tokens'], 'completion detail keys')
        integer(r['reasoning_tokens'], 'reasoning_tokens')
    vectors = vectors_from_rows(rows)
    endpoints = check_endpoints(vectors)
    return endpoints


def dump(path, obj):
    p = Path(path)
    raw = (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=1) + '\n').encode('utf-8')
    with p.open('xb') as f:
        f.write(raw)


def resolve_out(path):
    p = Path(path).resolve()
    require(not p.exists(), 'output already exists: %s' % p)
    return p


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--archive-root')
    ap.add_argument('--evidence')
    ap.add_argument('--build-evidence')
    ap.add_argument('--output', required=True)
    a = ap.parse_args(argv)
    try:
        out = resolve_out(a.output)
        if a.build_evidence:
            require(a.archive_root, '--build-evidence requires --archive-root')
            require(not a.evidence, '--evidence conflicts with --build-evidence')
            evidence = build(a.archive_root)
            endpoints = validate_evidence(evidence)
            raw = (json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=1) + '\n').encode('utf-8')
            ep = Path(a.build_evidence).resolve()
            require(not ep.exists(), 'build-evidence path already exists')
            with ep.open('xb') as f:
                f.write(raw)
            evidence_sha = sha(raw)
        elif a.evidence:
            require(not a.archive_root, '--archive-root conflicts with --evidence')
            evidence = loads(Path(a.evidence).read_bytes())
            endpoints = validate_evidence(evidence)
            evidence_sha = sha(Path(a.evidence).read_bytes())
        else:
            raise Invalid('either --archive-root+--build-evidence or --evidence is required')
        result = {'schema': SCHEMA + '-result', 'evidence_sha256': evidence_sha,
                  'baseline': BASELINE, 'readme_sha256': README_SHA256,
                  'endpoints': endpoints,
                  'verdict': {'prompt_stable_cross_run': '7/7', 'cache_differs_cross_run': '6/7',
                              'r2_first_request_cache_hit_witness': True,
                              'scope': 'single task, single model, product-reported; no mechanism attribution'}}
        dump(out, result)
        print(json.dumps({'mode': 'build' if a.build_evidence else 'replay',
                          'evidence_sha256': evidence_sha,
                          'endpoints': endpoints}, ensure_ascii=False, sort_keys=True))
        return 0
    except (Invalid, json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        print('input or output failure', file=sys.stderr)
        print('  %s' % (exc,), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
