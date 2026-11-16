#!/usr/bin/env python3
"""Adversarial test suite for the DSH request-capture verifier (until14-20261117).

Builds a fully synthetic capture directory (no real content, no network) and
exercises the raw rebuild pipeline, the public evidence validation, and the
tamper paths.  Frozen constants are patched to the synthetic values for the
duration of each test and restored afterwards.

Run:  python3 -I -S -B test_verify.py   (or with -O)
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify  # noqa: E402

REALS = {}
PATCHABLE = ['REQ_BYTES', 'REQ_SHAS', 'REQ1_ROLES', 'REQ3_APPENDED', 'REQ2_ROLES',
             'WORKSPACE_FILES', 'PINS', 'TOOL_NAMES']


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


class Base(unittest.TestCase):
    def setUp(self):
        for name in PATCHABLE:
            REALS[name] = getattr(verify, name)
        verify.REQ_BYTES = {1: 100, 2: 60, 3: 160}
        verify.REQ1_ROLES = [['system', 'str', 30], ['user', 'str', 70]]
        verify.REQ3_APPENDED = [['assistant', 'none', 0], ['tool', 'str', 30], ['tool', 'str', 30]]
        verify.REQ2_ROLES = [['system', 'str', 20], ['user', 'str', 40]]
        verify.WORKSPACE_FILES = {'TASK.md': sha(b'task')}
        verify.TOOL_NAMES = ['read', 'write']
        self.tmp = tempfile.mkdtemp(prefix='dsh-capture-test-')
        self.archive = os.path.join(self.tmp, 'archive')
        self.workspace = os.path.join(self.tmp, 'ws')
        os.makedirs(os.path.join(self.archive, 'capture', 'requests'))
        os.makedirs(os.path.join(self.archive, 'capture', 'responses'))
        os.makedirs(self.workspace)
        self.out = os.path.join(self.tmp, 'out')
        os.makedirs(self.out)
        self._write_synthetic()

    def tearDown(self):
        for name in PATCHABLE:
            setattr(verify, name, REALS[name])
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---------- synthetic fixtures ----------
    def _loop_body(self, appended):
        messages = [
            {'role': 'system', 'content': 'S' * 30},
            {'role': 'user', 'content': 'U' * 70},
        ]
        if appended:
            messages.append({'role': 'assistant', 'content': None, 'tool_calls': [
                {'id': 'c1', 'type': 'function', 'function': {'name': 'read', 'arguments': '{}'}},
                {'id': 'c2', 'type': 'function', 'function': {'name': 'read', 'arguments': '{}'}},
            ]})
            messages.append({'role': 'tool', 'tool_call_id': 'c1', 'content': 'T' * 30})
            messages.append({'role': 'tool', 'tool_call_id': 'c2', 'content': 'T' * 30})
        body = {
            'model': 'glm-5.3-flash', 'stream': True, 'stream_options': {'include_usage': True},
            'max_tokens': 128000, 'thinking': {'type': 'disabled'},
            'messages': messages,
            'tools': [{'type': 'function', 'function': {'name': n}} for n in ['read', 'write']],
        }
        raw = canon(body)
        # patch byte pins to actual synthetic sizes
        verify.REQ_BYTES[1 if not appended else 3] = len(raw)
        return raw

    def _aux_body(self):
        body = {'model': 'glm-5.3-flash', 'max_tokens': 4096,
                'thinking': {'type': 'enabled'},
                'messages': [{'role': 'system', 'content': 'a' * 20},
                             {'role': 'user', 'content': 'b' * 40}]}
        raw = canon(body)
        verify.REQ_BYTES[2] = len(raw)
        return raw

    def _write_synthetic(self):
        req1 = self._loop_body(False)
        req2 = self._aux_body()
        req3 = self._loop_body(True)
        verify.REQ_SHAS = {1: sha(req1), 2: sha(req2), 3: sha(req3)}
        resp = {}
        for seq, raw in ((1, req1), (2, req2), (3, req3)):
            open(os.path.join(self.archive, 'capture', 'requests', '%03d.request.bin' % seq), 'wb').write(raw)
            rbytes = b'HTTP-SSE-%d' % seq
            open(os.path.join(self.archive, 'capture', 'responses', '%03d.response.bin' % seq), 'wb').write(rbytes)
            meta = {
                'seq': seq, 'method': 'POST', 'path': verify_default_path(),
                'request_headers': {'authorization': 'sha256:abcdef0123456789...'},
                'request_body_bytes': len(raw), 'request_body_sha256': sha(raw),
                'response_body_bytes': len(rbytes), 'response_body_sha256': sha(rbytes),
                'duration_ms': 100 * seq, 'error': None,
            }
            open(os.path.join(self.archive, 'capture', 'responses', '%03d.response.bin.meta.json' % seq), 'w').write(
                json.dumps(meta))
            resp[seq] = len(rbytes)
        self._write_summary(resp)
        self._write_start()
        self._write_stdout()
        open(os.path.join(self.workspace, 'TASK.md'), 'wb').write(b'task')
        verify.PINS = {
            'proxy_script': 'proxy_script.py',
            'run_stdout': 'real-run-stdout.json',
            'run_stderr': 'real-run-stderr.log',
        }
        open(os.path.join(self.archive, 'proxy_script.py'), 'wb').write(b'proxy-code')
        open(os.path.join(self.archive, 'real-run-stderr.log'), 'wb').write(b'stderr')

    def _write_summary(self, resp):
        rows = []
        for seq in (1, 2, 3):
            rows.append({'seq': seq, 'upstream_status': 200,
                         'request_body_bytes': verify.REQ_BYTES[seq],
                         'response_body_bytes': resp[seq]})
        open(os.path.join(self.archive, 'capture', 'summary.jsonl'), 'w').write(
            '\n'.join(json.dumps(r) for r in rows) + '\n')

    def _write_start(self):
        open(os.path.join(self.archive, 'capture', 'PROXY-START.json'), 'w').write(json.dumps(
            {'listen': verify_default_listen(), 'upstream': verify_default_upstream()}))

    def _write_stdout(self):
        events = [
            {'type': 'session', 'sessionId': 'synthetic-session-0001'},
            {'type': 'status', 'phase': 'step_end', 'step': 1,
             'usage': {'inputTokens': 10, 'outputTokens': 2, 'totalTokens': 12}},
            {'type': 'status', 'phase': 'step_end', 'step': 2,
             'usage': {'inputTokens': 5, 'cacheReadTokens': 10, 'outputTokens': 1, 'totalTokens': 16}},
            {'type': 'final', 'text': 'done'},
        ]
        raw = '\n'.join(json.dumps(e) for e in events).encode('utf-8')
        open(os.path.join(self.archive, 'real-run-stdout.json'), 'wb').write(raw)

    # ---------- helpers ----------
    def run_raw(self, output=None, build=True):
        ev = os.path.join(self.out, 'evidence.json') if build else None
        res = output or os.path.join(self.out, 'result.json')
        argv = ['--archive-root', self.archive, '--workspace', self.workspace, '--output', res]
        if ev:
            argv += ['--build-evidence', ev]
        code = verify.main(argv)
        self.assertEqual(code, 0)
        return (json.load(open(ev)) if ev else None), json.load(open(res))

    def run_public(self, evidence, output=None):
        path = os.path.join(self.out, 'pub-evidence.json')
        open(path, 'w').write(json.dumps(evidence))
        res = output or os.path.join(self.out, 'pub-result.json')
        code = verify.main(['--evidence', path, '--output', res])
        self.assertEqual(code, 0)
        return json.load(open(res))

    def mutate(self, obj, path, value):
        cur = obj
        for key in path[:-1]:
            cur = cur[key]
        cur[path[-1]] = value

    def expect_invalid(self, fn, label):
        with self.assertRaises((verify.Invalid, SystemExit), msg=label):
            fn()


def verify_default_path():
    return verify.REQUEST_PATH


def verify_default_listen():
    return verify.PROXY_START['listen']


def verify_default_upstream():
    return verify.PROXY_START['upstream']


class Grammar(Base):
    def test_full_pipeline(self):
        _, result = self.run_raw()
        self.assertEqual(result['endpoints']['q1_history_overflow']['verdict'], 'append_only_prefix_extended')
        self.assertEqual(result['endpoints']['q2_truncation_reorg']['verdict'], 'no_truncation_or_reorg_witness_in_this_run')
        self.assertEqual(result['endpoints']['q4_system_and_tools']['system_role_bytes_req1'], 30)

    def test_public_replay_identical_result(self):
        ev, _ = self.run_raw()
        a = os.path.join(self.out, 'r1.json')
        b = os.path.join(self.out, 'r2.json')
        ev_path = os.path.join(self.out, 'evidence.json')
        verify.main(['--evidence', ev_path, '--output', a])
        verify.main(['--evidence', ev_path, '--output', b])
        self.assertEqual(open(a, 'rb').read(), open(b, 'rb').read())

    def test_evidence_carries_no_long_content(self):
        ev, _ = self.run_raw()
        text = json.dumps(ev, ensure_ascii=False)
        self.assertNotIn('can_chain', text)
        layout = ev.get('generated_from', {}).get('archive_layout')
        for s in _walk_strings(ev):
            if len(s) > 70 and s != layout:
                self.assertEqual(len(s), 64, 'unexpected long string %r' % s[:40])

    def test_steps_usage_shape(self):
        ev, _ = self.run_raw()
        self.assertEqual(len(ev['agent_steps']), 2)
        self.assertEqual(ev['agent_steps'][0]['usage']['inputTokens'], 10)
        self.assertEqual(ev['agent_steps'][1]['usage']['cacheReadTokens'], 10)


def _walk_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from _walk_strings(k)
            yield from _walk_strings(v)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_strings(item)


class RawRejection(Base):
    def _rerun(self, seq, body_override=None, meta_override=None, resp_override=None,
               summary_override=None):
        # regenerate one part then rebuild; base fixtures already exist
        pass

    def test_tampered_request_bytes(self):
        path = os.path.join(self.archive, 'capture', 'requests', '001.request.bin')
        raw = bytearray(open(path, 'rb').read())
        raw[-1] ^= 0x01
        open(path, 'wb').write(bytes(raw))
        self.expect_invalid(lambda: self.run_raw(), 'bytes')

    def test_meta_response_sha_mismatch(self):
        path = os.path.join(self.archive, 'capture', 'responses', '002.response.bin.meta.json')
        meta = json.load(open(path))
        meta['response_body_sha256'] = '0' * 64
        open(path, 'w').write(json.dumps(meta))
        self.expect_invalid(lambda: self.run_raw(), 'resp sha')

    def test_authorization_leak(self):
        path = os.path.join(self.archive, 'capture', 'responses', '001.response.bin.meta.json')
        meta = json.load(open(path))
        meta['request_headers']['authorization'] = 'Bearer sk-live-abcdef'
        open(path, 'w').write(json.dumps(meta))
        self.expect_invalid(lambda: self.run_raw(), 'bearer')

    def test_authorization_unmasked(self):
        path = os.path.join(self.archive, 'capture', 'responses', '003.response.bin.meta.json')
        meta = json.load(open(path))
        meta['request_headers']['authorization'] = 'raw-secret-value'
        open(path, 'w').write(json.dumps(meta))
        self.expect_invalid(lambda: self.run_raw(), 'unmasked')

    def test_meta_wrong_method(self):
        path = os.path.join(self.archive, 'capture', 'responses', '002.response.bin.meta.json')
        meta = json.load(open(path))
        meta['method'] = 'GET'
        open(path, 'w').write(json.dumps(meta))
        self.expect_invalid(lambda: self.run_raw(), 'method')

    def test_meta_wrong_path(self):
        path = os.path.join(self.archive, 'capture', 'responses', '002.response.bin.meta.json')
        meta = json.load(open(path))
        meta['path'] = '/other/endpoint'
        open(path, 'w').write(json.dumps(meta))
        self.expect_invalid(lambda: self.run_raw(), 'path')

    def test_summary_extra_row(self):
        path = os.path.join(self.archive, 'capture', 'summary.jsonl')
        rows = [json.loads(l) for l in open(path).read().split('\n') if l]
        rows.append(dict(rows[0], seq=9))
        open(path, 'w').write('\n'.join(json.dumps(r) for r in rows) + '\n')
        self.expect_invalid(lambda: self.run_raw(), 'summary')

    def test_proxy_start_mismatch(self):
        path = os.path.join(self.archive, 'capture', 'PROXY-START.json')
        start = json.load(open(path))
        start['upstream'] = 'https://elsewhere:443'
        open(path, 'w').write(json.dumps(start))
        self.expect_invalid(lambda: self.run_raw(), 'upstream')

    def test_prefix_broken(self):
        # make req3 differ in its prefix region (rebuild with a tweaked system message)
        body = {
            'model': 'glm-5.3-flash', 'stream': True, 'stream_options': {'include_usage': True},
            'max_tokens': 128000, 'thinking': {'type': 'disabled'},
            'messages': [
                {'role': 'system', 'content': 'X' * 30},
                {'role': 'user', 'content': 'U' * 70},
                {'role': 'assistant', 'content': None, 'tool_calls': [
                    {'id': 'c1', 'type': 'function', 'function': {'name': 'read', 'arguments': '{}'}},
                    {'id': 'c2', 'type': 'function', 'function': {'name': 'read', 'arguments': '{}'}}]},
                {'role': 'tool', 'tool_call_id': 'c1', 'content': 'T' * 30},
                {'role': 'tool', 'tool_call_id': 'c2', 'content': 'T' * 30},
            ],
            'tools': [{'type': 'function', 'function': {'name': n}} for n in ['read', 'write']],
        }
        raw = canon(body)
        verify.REQ_BYTES[3] = len(raw)
        verify.REQ_SHAS[3] = sha(raw)
        open(os.path.join(self.archive, 'capture', 'requests', '003.request.bin'), 'wb').write(raw)
        meta_path = os.path.join(self.archive, 'capture', 'responses', '003.response.bin.meta.json')
        meta = json.load(open(meta_path))
        meta['request_body_bytes'] = len(raw)
        meta['request_body_sha256'] = sha(raw)
        open(meta_path, 'w').write(json.dumps(meta))
        rows = [json.loads(l) for l in open(os.path.join(self.archive, 'capture', 'summary.jsonl')).read().split('\n') if l]
        for row in rows:
            if row['seq'] == 3:
                row['request_body_bytes'] = len(raw)
        open(os.path.join(self.archive, 'capture', 'summary.jsonl'), 'w').write(
            '\n'.join(json.dumps(r) for r in rows) + '\n')
        with self.assertRaises(verify.Invalid, msg='prefix verdict must fail'):
            self.run_raw()

    def test_workspace_wrong_bytes(self):
        open(os.path.join(self.workspace, 'TASK.md'), 'wb').write(b'tampered')
        self.expect_invalid(lambda: self.run_raw(), 'workspace')

    def test_path_escape_workspace(self):
        outside = os.path.join(self.tmp, 'outside.md')
        open(outside, 'wb').write(b'task')
        link = os.path.join(self.workspace, 'TASK.md')
        os.remove(link)
        os.symlink(outside, link)
        # content matches pin, but symlink escape must be rejected by safe_join
        self.expect_invalid(lambda: self.run_raw(), 'symlink escape')


class PublicRejection(Base):
    def _ev(self):
        ev, _ = self.run_raw()
        return json.loads(json.dumps(ev))

    def test_request_sha_pin(self):
        ev = self._ev()
        self.mutate(ev, ['capture', 'requests', 0, 'request_sha256'], '1' * 64)
        self.expect_invalid(lambda: self.run_public(ev), 'sha pin')

    def test_request_bytes_pin(self):
        ev = self._ev()
        self.mutate(ev, ['capture', 'requests', 0, 'request_bytes'], 999)
        self.expect_invalid(lambda: self.run_public(ev), 'bytes pin')

    def test_roles_pin(self):
        ev = self._ev()
        self.mutate(ev, ['capture', 'requests', 0, 'roles', 1, 2], 71)
        self.expect_invalid(lambda: self.run_public(ev), 'roles pin')

    def test_thinking_pin(self):
        ev = self._ev()
        self.mutate(ev, ['capture', 'requests', 1, 'thinking_type'], 'disabled')
        self.expect_invalid(lambda: self.run_public(ev), 'thinking pin')

    def test_max_tokens_pin(self):
        ev = self._ev()
        self.mutate(ev, ['capture', 'requests', 1, 'max_tokens'], 128000)
        self.expect_invalid(lambda: self.run_public(ev), 'max tokens pin')

    def test_aux_with_tools(self):
        ev = self._ev()
        self.mutate(ev, ['capture', 'requests', 1, 'n_tools'], 2)
        self.expect_invalid(lambda: self.run_public(ev), 'aux tools')

    def test_tool_names(self):
        ev = self._ev()
        self.mutate(ev, ['capture', 'requests', 0, 'tool_names'], ['read', 'evil'])
        self.expect_invalid(lambda: self.run_public(ev), 'tool names')

    def test_extra_request(self):
        ev = self._ev()
        ev['capture']['requests'].append(dict(ev['capture']['requests'][0], seq=9))
        self.expect_invalid(lambda: self.run_public(ev), 'extra request')

    def test_prefix_verdict_flip(self):
        ev = self._ev()
        self.mutate(ev, ['prefix_identity', 'req1_prefix_of_req3'], False)
        self.expect_invalid(lambda: self.run_public(ev), 'prefix verdict')

    def test_delta_bytes(self):
        ev = self._ev()
        self.mutate(ev, ['prefix_identity', 'delta_request_bytes'], 1)
        self.expect_invalid(lambda: self.run_public(ev), 'delta')

    def test_steps_missing(self):
        ev = self._ev()
        ev['agent_steps'] = ev['agent_steps'][:1]
        self.expect_invalid(lambda: self.run_public(ev), 'steps')

    def test_negative_tokens(self):
        ev = self._ev()
        self.mutate(ev, ['agent_steps', 0, 'usage', 'inputTokens'], -1)
        self.expect_invalid(lambda: self.run_public(ev), 'negative tokens')

    def test_bad_final_sha(self):
        ev = self._ev()
        ev['final_text_sha256'] = 'zz'
        self.expect_invalid(lambda: self.run_public(ev), 'final sha')

    def test_workspace_set(self):
        ev = self._ev()
        ev['workspace']['extra'] = {'bytes': 1, 'sha256': '0' * 64}
        self.expect_invalid(lambda: self.run_public(ev), 'workspace set')

    def test_workspace_sha(self):
        ev = self._ev()
        ev['workspace']['TASK.md']['sha256'] = '2' * 64
        self.expect_invalid(lambda: self.run_public(ev), 'workspace sha')

    def test_missing_private_pins(self):
        ev = self._ev()
        ev['generated_from']['private_pins'] = {}
        self.expect_invalid(lambda: self.run_public(ev), 'pins')

    def test_bad_schema(self):
        ev = self._ev()
        ev['schema'] = 'other'
        self.expect_invalid(lambda: self.run_public(ev), 'schema')

    def test_bad_baseline(self):
        ev = self._ev()
        ev['baseline'] = 'f' * 40
        self.expect_invalid(lambda: self.run_public(ev), 'baseline')

    def test_model_pin(self):
        ev = self._ev()
        self.mutate(ev, ['capture', 'requests', 0, 'model'], 'other-model')
        self.expect_invalid(lambda: self.run_public(ev), 'model')

    def test_status_pin(self):
        ev = self._ev()
        self.mutate(ev, ['capture', 'requests', 0, 'upstream_status'], 500)
        self.expect_invalid(lambda: self.run_public(ev), 'status')

    def test_role_name(self):
        ev = self._ev()
        ev['capture']['requests'][0]['roles'][0][0] = 'developer'
        self.expect_invalid(lambda: self.run_public(ev), 'role name')

    def test_content_kind(self):
        ev = self._ev()
        ev['capture']['requests'][0]['roles'][0][1] = 'object'
        self.expect_invalid(lambda: self.run_public(ev), 'content kind')

    def test_negative_content_bytes(self):
        ev = self._ev()
        ev['capture']['requests'][0]['roles'][0][2] = -5
        self.expect_invalid(lambda: self.run_public(ev), 'content bytes')

    def test_duplicate_json_key(self):
        ev, _ = self.run_raw()
        path = os.path.join(self.out, 'dup.json')
        open(path, 'w').write('{"schema": "a", "schema": "b"}')
        self.expect_invalid(lambda: verify.main(['--evidence', path,
                                                 '--output', os.path.join(self.out, 'x.json')]), 'dup key')

    def test_nonfinite_json(self):
        path = os.path.join(self.out, 'inf.json')
        open(path, 'w').write('{"schema": 1e999}')
        self.expect_invalid(lambda: verify.main(['--evidence', path,
                                                 '--output', os.path.join(self.out, 'y.json')]), 'nonfinite')


class Cli(Base):
    def test_output_exists(self):
        res = os.path.join(self.out, 'result.json')
        self.run_raw(output=res)
        with self.assertRaises(SystemExit):
            self.run_raw(output=res)

    def test_missing_output_arg(self):
        with self.assertRaises(SystemExit):
            verify.main(['--archive-root', self.archive, '--workspace', self.workspace])

    def test_public_needs_no_raw_args(self):
        ev, _ = self.run_raw()
        ev_path = os.path.join(self.out, 'evidence.json')
        with self.assertRaises((verify.Invalid, SystemExit)):
            # --evidence together with --build-evidence is rejected
            verify.main(['--evidence', ev_path, '--build-evidence', os.path.join(self.out, 'e2.json'),
                         '--output', os.path.join(self.out, 'z.json')])


if __name__ == '__main__':
    unittest.main()
