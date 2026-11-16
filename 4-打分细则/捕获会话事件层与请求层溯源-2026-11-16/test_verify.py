#!/usr/bin/env python3
"""Adversarial suite for the capture-session provenance package.

The synthetic rebuild fixtures need real zstandard frames, so this suite runs
under python3 -B (not -I -S); zstandard is the declared private-rebuild
dependency of verify.py. Public-replay tests stay stdlib-only.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
VERIFY = HERE / 'verify.py'
CAP_REL = '4-打分细则/DSH请求侧最小捕获-2026-11-16/evidence.json'
CAPRES_REL = '4-打分细则/DSH请求侧最小捕获-2026-11-16/result.json'
CAPREAD_REL = '4-打分细则/DSH请求侧最小捕获-2026-11-16/README.md'
SELF_REL = '4-打分细则/捕获会话事件层与请求层溯源-2026-11-16/README.md'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def doc(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(raw)
    return raw


class CliMixin(unittest.TestCase):
    def run_cli(self, args, env_extra=None):
        env = dict(os.environ)
        if env_extra:
            env.update(env_extra)
        query = subprocess.run([sys.executable, '-B', str(VERIFY)] + args,
                               capture_output=True, timeout=180, env=env)
        return query.returncode, query.stdout, query.stderr


class Base(CliMixin):
    """Fresh synthetic private root + repo root with pinned capture files."""

    def setUp(self):
        import zstandard
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.repo = base / 'repo'
        self.raw = base / 'raw'
        (self.raw / 'requests').mkdir(parents=True)
        compressor = zstandard.ZstdCompressor()
        self.session_lines = self.synthetic_events()
        with (self.raw / 'session.v4.jsonl.zstd').open('xb') as handle:
            for event in self.session_lines:
                handle.write(compressor.compress((json.dumps(event, ensure_ascii=False) + '\n').encode()))
        self.requests = self.synthetic_wire()
        for index, body in enumerate(self.requests, start=1):
            write(self.raw / 'requests' / ('%03d.request.bin' % index), body)
        req1_wire = json.loads(self.requests[0])
        self.cap_roles = [[msg['role'], 'str', len(msg['content'].encode('utf-8'))] for msg in req1_wire['messages']]
        cap = {'capture': {'requests': [
            {'seq': 1, 'kind': 'loop', 'request_bytes': len(self.requests[0]),
             'request_sha256': sha(self.requests[0]), 'roles': self.cap_roles},
            {'seq': 2, 'kind': 'auxiliary', 'request_bytes': len(self.requests[1]),
             'request_sha256': sha(self.requests[1]), 'roles': [['system', 'str', 11], ['user', 'str', 9]]},
            {'seq': 3, 'kind': 'loop', 'request_bytes': len(self.requests[2]),
             'request_sha256': sha(self.requests[2]),
             'roles': self.cap_roles + [['assistant', 'none', 0], ['tool', 'str', 4], ['tool', 'str', 5]]},
        ]}, 'prefix_identity': {'req1_prefix_of_req3': True, 'delta_request_bytes': 26,
                                'req3_appended_roles': [['assistant', 'none', 0], ['tool', 'str', 4], ['tool', 'str', 5]]}}
        write(self.repo / CAP_REL, doc(cap))
        write(self.repo / CAPRES_REL, doc({'schema': 'capture-session-provenance-result-v1', 'baseline_commit': 'x' * 40, 'endpoints': {}}))
        write(self.repo / CAPREAD_REL, b'# capture protocol markdown\n')
        write(self.repo / SELF_REL, b'# provenance protocol markdown\n')
        self.bind()

    def bind(self):
        module = load_verify()['module']
        module.CAP_SHA = sha((self.repo / CAP_REL).read_bytes())
        module.CAPRES_SHA = sha((self.repo / CAPRES_REL).read_bytes())
        module.CAPREADME_SHA = sha((self.repo / CAPREAD_REL).read_bytes())
        module.SESSION_SHA = sha((self.raw / 'session.v4.jsonl.zstd').read_bytes())
        module.EVENT_COUNT = len(self.session_lines)

    def tearDown(self):
        self.tmp.cleanup()

    def synthetic_events(self):
        system = 'SYSTEM-TEXT'
        task = 'TASK!'
        injected = ['INJ-A!', 'INJ-B!', 'INJ-C!']
        blocks = [{'type': 'tool-call', 'id': 'call_1a', 'name': 'bash', 'arguments': '{"cmd":"ls"}'},
                  {'type': 'tool-call', 'id': 'call_2b', 'name': 'read', 'arguments': '{"path":"x"}'}]
        return [
            {'seq': 3, 'type': 'agent/inbox/spliced', 'data': {'target': 'next-turn', 'start': 0, 'inserted': [{'content': [{'type': 'text', 'text': task}], 'source': 'task', 'role': 'user', 'id': 'u1'}]}},
            {'seq': 5, 'type': 'agent/inbox/spliced', 'data': {'target': 'next-turn', 'start': 0, 'removedCount': 1, 'inserted': []}},
            {'seq': 7, 'type': 'system/message', 'data': {'turn': 1, 'step': 1, 'message': {'role': 'system', 'content': [{'type': 'text', 'text': system}]}}},
        ] + [
            {'seq': 8 + i, 'type': 'user/message', 'data': {'role': 'user', 'id': 'u%d' % i, 'source': 's%d' % i, 'content': [{'type': 'text', 'text': text}]}}
            for i, text in enumerate([task] + injected)
        ] + [
            {'seq': 12, 'type': 'request/header', 'data': {'reason': 'initial', 'header': {'config': {'provider': 'p', 'model': 'm-1', 'maxTokens': 128000}, 'adapterDefaults': {}, 'tools': [
                {'name': 'bash', 'description': 'run', 'parameters': {'type': 'object'}},
                {'name': 'read', 'description': 'read', 'parameters': {'type': 'object'}}]}}},
            {'seq': 13, 'type': 'request/context', 'data': {'provider': 'p', 'model': 'm-1', 'contextWindow': 1000000}},
            {'seq': 15, 'type': 'session/title-llm-request', 'data': {'titleProvider': 'tp', 'messageSeqs': [8],
                'route': {'provider': 'p', 'model': 'm-1'}, 'system': 'TITLE-SYS', 'maxTokens': 4096,
                'messages': [{'role': 'user', 'content': [{'type': 'text', 'text': 'Generate the session title from this JSON array of human messages:\n' + json.dumps([{'seq': 8, 'text': task}], ensure_ascii=False, separators=(',', ':'))}]}]}},
            {'seq': 17, 'type': 'assistant/message', 'data': {'turn': 1, 'step': 1, 'usage': {}, 'stream': {},
                'message': {'role': 'assistant', 'id': 'a1', 'source': 'm', 'content': blocks}}},
            {'seq': 18, 'type': 'tool/call', 'data': {'turn': 1, 'step': 1, 'callId': 'call_1a', 'name': 'bash', 'arguments': '{"cmd":"ls"}'}},
            {'seq': 19, 'type': 'tool/call', 'data': {'turn': 1, 'step': 1, 'callId': 'call_2b', 'name': 'read', 'arguments': '{"path":"x"}'}},
            {'seq': 20, 'type': 'tool/result', 'data': {'turn': 1, 'step': 1, 'meta': {},
                'message': {'role': 'tool', 'toolCallId': 'call_1a', 'id': 'r1', 'source': 'm', 'isError': False, 'content': [{'type': 'text', 'text': 'OUT1'}]}}},
            {'seq': 21, 'type': 'tool/result', 'data': {'turn': 1, 'step': 1, 'meta': {},
                'message': {'role': 'tool', 'toolCallId': 'call_2b', 'id': 'r2', 'source': 'm', 'isError': False, 'content': [{'type': 'text', 'text': 'OUT2!'}]}}},
        ]

    def synthetic_wire(self):
        system = 'SYSTEM-TEXT'
        task = 'TASK!'
        injected = ['INJ-A!', 'INJ-B!', 'INJ-C!']
        req1 = {'model': 'm-1', 'max_tokens': 128000, 'stream': True,
                'messages': [{'role': 'system', 'content': system}] + [
                    {'role': 'user', 'content': text} for text in [task] + injected],
                'tools': [{'type': 'function', 'function': {'name': 'bash', 'description': 'run', 'parameters': {'type': 'object'}}},
                          {'type': 'function', 'function': {'name': 'read', 'description': 'read', 'parameters': {'type': 'object'}}}]}
        req2 = {'model': 'm-1', 'max_tokens': 4096,
                'messages': [{'role': 'system', 'content': 'TITLE-SYS'},
                             {'role': 'user', 'content': 'Generate the session title from this JSON array of human messages:\n' + json.dumps([{'seq': 8, 'text': task}], ensure_ascii=False, separators=(',', ':'))}]}
        req3 = {'model': 'm-1', 'max_tokens': 128000,
                'messages': req1['messages'] + [
                    {'role': 'assistant', 'content': None, 'tool_calls': [
                        {'id': 'call_1a', 'type': 'function', 'function': {'name': 'bash', 'arguments': '{"cmd":"ls"}'}},
                        {'id': 'call_2b', 'type': 'function', 'function': {'name': 'read', 'arguments': '{"path":"x"}'}}]},
                    {'role': 'tool', 'tool_call_id': 'call_1a', 'content': 'OUT1'},
                    {'role': 'tool', 'tool_call_id': 'call_2b', 'content': 'OUT2!'}]}
        return [(json.dumps(req1, ensure_ascii=False) + '\n').encode(),
                (json.dumps(req2, ensure_ascii=False) + '\n').encode(),
                (json.dumps(req3, ensure_ascii=False) + '\n').encode()]

    def build(self):
        spec = load_verify()
        return spec['build'](self.repo, self.raw)



_VERIFY_CACHE = {}


def load_verify():
    key = str(VERIFY) + str(Path(VERIFY).stat().st_mtime_ns)
    if key not in _VERIFY_CACHE:
        module = import_verify()
        _VERIFY_CACHE[key] = {'build': module.build, 'validate_public': module.validate_public,
                              'module': module}
    return _VERIFY_CACHE[key]


def import_verify():
    import importlib.util
    spec = importlib.util.spec_from_file_location('provenance_verify_%d' % len(_VERIFY_CACHE), VERIFY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RebuildTests(Base):
    def test_golden_mapping(self):
        evidence, result = self.build()
        self.assertEqual(len(evidence['mapped_messages']), 8)
        self.assertEqual(evidence['content_exact_count'], 8)
        self.assertEqual(result['endpoints']['p1_loop_message_content_exact'], '8/8')
        self.assertEqual(evidence['assistant']['pairs_exact'], 2)
        self.assertEqual(evidence['tools']['fields_exact'], 2)
        self.assertTrue(evidence['request_level']['model_exact'])
        self.assertTrue(all(evidence['title_request'].values()))
        self.assertEqual(evidence['session_frames'], len(self.session_lines))
        self.assertEqual([r['wire_bytes'] for r in evidence['mapped_messages'] if r['role'] == 'tool'], [4, 5])

    def test_wrong_session_bytes_detected(self):
        spec = load_verify()
        original = (self.raw / 'session.v4.jsonl.zstd').read_bytes()
        (self.raw / 'session.v4.jsonl.zstd').write_bytes(original[:-1])
        with self.assertRaises(ValueError):
            spec['build'](self.repo, self.raw)

    def test_wire_sha_mismatch_detected(self):
        spec = load_verify()
        path = self.raw / 'requests' / '001.request.bin'
        original = path.read_bytes()
        path.write_bytes(original.replace(b'TASK!', b'TASX!'))
        with self.assertRaises(ValueError):
            spec['build'](self.repo, self.raw)

    def test_event_count_mismatch(self):
        spec = load_verify()
        self.session_lines.pop()
        import zstandard
        compressor = zstandard.ZstdCompressor()
        target = self.raw / 'session.v4.jsonl.zstd'
        target.unlink()
        with target.open('xb') as handle:
            for event in self.session_lines:
                handle.write(compressor.compress((json.dumps(event, ensure_ascii=False) + '\n').encode()))
        # pin now mismatched (different bytes) -> first failure is the pin
        with self.assertRaises(ValueError):
            spec['build'](self.repo, self.raw)

    def test_duplicate_seq_detected(self):
        spec = load_verify()
        self.session_lines.append(dict(self.session_lines[-1]))
        import zstandard
        compressor = zstandard.ZstdCompressor()
        target = self.raw / 'session.v4.jsonl.zstd'
        target.unlink()
        with target.open('xb') as handle:
            for event in self.session_lines:
                handle.write(compressor.compress((json.dumps(event, ensure_ascii=False) + '\n').encode()))
        with self.assertRaises(ValueError):
            spec['build'](self.repo, self.raw)

    def test_content_drift_same_shape_detected(self):
        spec = load_verify()
        evidence, _ = self.build()
        row = evidence['mapped_messages'][1]
        self.assertTrue(row['content_exact'])
        # drift the wire user task text only
        self.requests[0] = self.requests[0].replace(b'"TASK!"', b'"TASX!"', 1)
        wire = json.loads(self.requests[0])
        wire['messages'][1]['content'] = 'TASX!'
        self.requests[0] = (json.dumps(wire, ensure_ascii=False) + '\n').encode()
        path = self.raw / 'requests' / '001.request.bin'
        path.unlink()
        write(path, self.requests[0])
        cap = json.loads((self.repo / CAP_REL).read_bytes())
        cap['capture']['requests'][0]['request_bytes'] = len(self.requests[0])
        cap['capture']['requests'][0]['request_sha256'] = sha(self.requests[0])
        (self.repo / CAP_REL).unlink()
        write(self.repo / CAP_REL, doc(cap))
        self.bind()
        evidence2, _ = spec['build'](self.repo, self.raw)
        self.assertFalse(evidence2['mapped_messages'][1]['content_exact'])
        self.assertEqual(evidence2['content_exact_count'], 7)

    def test_assistant_pair_drift(self):
        spec = load_verify()
        wire = json.loads(self.requests[2])
        wire['messages'][5]['tool_calls'][0]['function']['arguments'] = '{"cmd":"ls -la"}'
        self.requests[2] = (json.dumps(wire, ensure_ascii=False) + '\n').encode()
        path = self.raw / 'requests' / '003.request.bin'
        path.unlink()
        write(path, self.requests[2])
        cap = json.loads((self.repo / CAP_REL).read_bytes())
        cap['capture']['requests'][2]['request_bytes'] = len(self.requests[2])
        cap['capture']['requests'][2]['request_sha256'] = sha(self.requests[2])
        cap['prefix_identity']['req3_appended_roles'] = [['assistant', 'none', 0], ['tool', 'str', 4], ['tool', 'str', 5]]
        (self.repo / CAP_REL).unlink()
        write(self.repo / CAP_REL, doc(cap))
        self.bind()
        evidence, result = spec['build'](self.repo, self.raw)
        self.assertEqual(evidence['assistant']['pairs_exact'], 1)
        self.assertEqual(result['endpoints']['p2_assistant_transform_exact'], '1/2')

    def test_tool_result_drift(self):
        spec = load_verify()
        wire = json.loads(self.requests[2])
        wire['messages'][6]['content'] = 'OUT9'
        self.requests[2] = (json.dumps(wire, ensure_ascii=False) + '\n').encode()
        path = self.raw / 'requests' / '003.request.bin'
        path.unlink()
        write(path, self.requests[2])
        cap = json.loads((self.repo / CAP_REL).read_bytes())
        cap['capture']['requests'][2]['request_bytes'] = len(self.requests[2])
        cap['capture']['requests'][2]['request_sha256'] = sha(self.requests[2])
        (self.repo / CAP_REL).unlink()
        write(self.repo / CAP_REL, doc(cap))
        self.bind()
        evidence, _ = spec['build'](self.repo, self.raw)
        tool_rows = [r for r in evidence['mapped_messages'] if r['role'] == 'tool']
        self.assertEqual([r['content_exact'] for r in tool_rows], [False, True])

    def test_title_user_wrong_separator(self):
        spec = load_verify()
        self.session_lines = [dict(e) for e in self.session_lines]
        # re-embed title with default separators -> must fail equality
        for event in self.session_lines:
            if event['seq'] == 15:
                text = json.dumps([{'seq': 8, 'text': 'TASK!'}], ensure_ascii=False)
                event['data']['messages'][0]['content'][0]['text'] = (
                    'Generate the session title from this JSON array of human messages:\n' + text)
        import zstandard
        compressor = zstandard.ZstdCompressor()
        target = self.raw / 'session.v4.jsonl.zstd'
        target.unlink()
        with target.open('xb') as handle:
            for event in self.session_lines:
                handle.write(compressor.compress((json.dumps(event, ensure_ascii=False) + '\n').encode()))
        with self.assertRaises(ValueError):
            spec['build'](self.repo, self.raw)

    def test_tool_registry_drift(self):
        spec = load_verify()
        wire = json.loads(self.requests[0])
        wire['tools'][0]['function']['description'] = 'changed'
        self.requests[0] = (json.dumps(wire, ensure_ascii=False) + '\n').encode()
        path = self.raw / 'requests' / '001.request.bin'
        path.unlink()
        write(path, self.requests[0])
        cap = json.loads((self.repo / CAP_REL).read_bytes())
        cap['capture']['requests'][0]['request_bytes'] = len(self.requests[0])
        cap['capture']['requests'][0]['request_sha256'] = sha(self.requests[0])
        (self.repo / CAP_REL).unlink()
        write(self.repo / CAP_REL, doc(cap))
        self.bind()
        evidence, result = spec['build'](self.repo, self.raw)
        self.assertEqual(evidence['tools']['fields_exact'], 1)
        self.assertEqual(result['endpoints']['p3_tool_declarations_field_exact'], '1/2')


class PublicTests(Base):
    def package(self, evidence=None, result=None):
        if evidence is None:
            evidence, result_default = self.build()
            result = result if result is not None else result_default
            result['evidence_sha256'] = sha((HERE / 'evidence.json').read_bytes())
        else:
            result = result if result is not None else dict(evidence)
        write(self.repo / SELF_REL.replace('README.md', 'evidence.json'), doc(evidence))
        write(self.repo / SELF_REL.replace('README.md', 'result.json'), doc(result))
        return evidence, result

    def test_sources_drift_rejected(self):
        spec = load_verify()
        evidence, result = self.package()
        evidence['sources']['requests/001.request.bin'] = '0' * 64
        with self.assertRaises(ValueError):
            spec['validate_public'](self.repo, evidence, result)

    def test_row_count_and_counts(self):
        spec = load_verify()
        evidence, result = self.package()
        evidence['content_exact_count'] = 7
        with self.assertRaises(ValueError):
            spec['validate_public'](self.repo, evidence, result)

    def test_req1_bytes_mismatch(self):
        spec = load_verify()
        evidence, result = self.package()
        evidence['mapped_messages'][1]['wire_bytes'] = 999
        with self.assertRaises(ValueError):
            spec['validate_public'](self.repo, evidence, result)

    def test_tool_bytes_mismatch(self):
        spec = load_verify()
        evidence, result = self.package()
        for row in evidence['mapped_messages']:
            if row['role'] == 'tool':
                row['wire_bytes'] = 1
        with self.assertRaises(ValueError):
            spec['validate_public'](self.repo, evidence, result)

    def test_endpoint_inconsistent(self):
        spec = load_verify()
        evidence, result = self.package()
        result['endpoints']['p1_loop_message_content_exact'] = '7/8'
        with self.assertRaises(ValueError):
            spec['validate_public'](self.repo, evidence, result)

    def test_binding_missing_or_wrong(self):
        spec = load_verify()
        evidence, result = self.package()
        result.pop('evidence_sha256')
        with self.assertRaises(ValueError):
            spec['validate_public'](self.repo, evidence, result)
        result['evidence_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            spec['validate_public'](self.repo, evidence, result)

    def test_limits_present(self):
        spec = load_verify()
        evidence, result = self.package()
        self.assertTrue(evidence['limits'])
        self.assertEqual(evidence['adapter_fields_unknown'], ['stream', 'stream_options', 'thinking', 'tool_stream'])


class CliTests(CliMixin):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / 'out.json'

    def tearDown(self):
        self.tmp.cleanup()

    def test_public_replay_matches_packaged_result(self):
        target = HERE / 'result.json'
        if not target.exists():
            self.skipTest('packaged result not built yet')
        code, _, _ = self.run_cli(['--root', str(REPO), '--output', str(self.out)])
        self.assertEqual(code, 0)
        self.assertEqual(self.out.read_bytes(), target.read_bytes())

    def test_output_inside_source_root_denied_for_build(self):
        code, _, _ = self.run_cli(['--root', str(REPO), '--raw-root', str(REPO),
                                   '--build-evidence', str(REPO / 'evidence-leak.json'),
                                   '--output', str(self.out)])
        self.assertNotEqual(code, 0)
        self.assertFalse((REPO / 'evidence-leak.json').exists())

    def test_output_exists_denied(self):
        self.out.write_bytes(b'x')
        code, _, _ = self.run_cli(['--root', str(REPO), '--output', str(self.out)])
        self.assertNotEqual(code, 0)

    def test_missing_output_arg(self):
        code, _, _ = self.run_cli(['--root', str(REPO)])
        self.assertNotEqual(code, 0)

    def test_generic_error_hides_values(self):
        code, _, err = self.run_cli(['--root', str(REPO), '--output', str(self.out)])
        self.assertNotIn(b'TASK', err)
        self.assertNotIn(b'can_chain', err)


if __name__ == '__main__':
    unittest.main()
