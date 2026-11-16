#!/usr/bin/env python3
"""Synthetic pipeline + tamper tests for the deep-chain usage/cache package.

A fake loop7 archive is constructed in a scratch dir with synthetic SSE bodies
whose usage values equal the pinned constants, so build() succeeds; then each
tamper case must exit 2 (fail-closed). Public replay checks use the same
pipeline outputs. Tests never touch the real private archive.
Run: python3 -B test_verify.py --scratch-root DIR
"""
import hashlib, json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import verify as V  # noqa: E402

ROOT = None


def sse(usage, finish='tool_calls', chunks=25, idtag='x'):
    lines = []
    n = chunks - 1
    for i in range(n):
        lines.append('data: ' + json.dumps({'id': idtag, 'choices': []}, separators=(',', ':')))
    lines.append('data: ' + json.dumps({'id': idtag,
                                        'choices': [{'finish_reason': finish}],
                                        'usage': usage}, separators=(',', ':')))
    lines.append('data: [DONE]')
    return ('\n'.join(lines) + '\n').encode('utf-8')


def usage(prompt, cached, completion):
    return {'prompt_tokens': prompt, 'completion_tokens': completion,
            'total_tokens': prompt + completion,
            'prompt_tokens_details': {'cached_tokens': cached},
            'completion_tokens_details': {'reasoning_tokens': 0}}


BASE_USAGE = [(7597, 0, 28), (167, 0, 9), (7816, 7552, 31), (7927, 7808, 31),
              (8034, 7872, 31), (8141, 8000, 26), (8174, 8128, 7)]
R1_CACHED = (0, 0, 7552, 7808, 7872, 8000, 8128)
R2_CACHED = (7552, 128, 7808, 7872, 8000, 8128, 8128)


def make_pack(base, cached1=R1_CACHED, cached2=R2_CACHED, chunks2=(22, 6, 27, 25, 25, 21, 5),
              finish2=None, break_identity=False):
    """Synthesise a loop7-shaped archive whose numbers equal the constants."""
    l7 = base / 'loop7'
    for run in ('t2-r1', 't2-r2'):
        rd = l7 / run / 'responses'
        rd.mkdir(parents=True)
        for seq in range(1, 8):
            prompt, _, completion = BASE_USAGE[seq - 1]
            if run == 't2-r1':
                cached, ch, fin = cached1[seq - 1], (22, 8, 25, 25, 25, 21, 5)[seq - 1], None
            else:
                cached, ch, fin = cached2[seq - 1], chunks2[seq - 1], (finish2 or (None,))[0] if finish2 else None
            total = prompt + completion
            if break_identity and run == 't2-r2' and seq == 7:
                total = total + 1
            u = usage(prompt, cached, completion)
            u['total_tokens'] = total
            body = sse(u, finish=fin or ('stop' if seq in (2, 7) else 'tool_calls'), chunks=ch, idtag='%s%03d' % (run, seq))
            (rd / ('%03d.response.bin' % seq)).write_bytes(body)
            meta = {'response_body_sha256': hashlib.sha256(body).hexdigest(),
                    'request_body_sha256': 'a' * 64,
                    'duration_ms': 1500 * seq}
            (rd / ('%03d.response.bin.meta.json' % seq)).write_text(json.dumps(meta))
    return l7


def run_verify(args, cwd=None):
    cmd = [sys.executable, '-B', str(HERE / 'verify.py')] + args
    return subprocess.run(cmd, capture_output=True, cwd=cwd, timeout=120)


class Pipeline(unittest.TestCase):
    def test_build_replay_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td); make_pack(base)
            e, r = base / 'e.json', base / 'r.json'
            q = run_verify(['--archive-root', str(base), '--build-evidence', str(e), '--output', str(r)])
            self.assertEqual(q.returncode, 0, q.stderr)
            stored = r.read_bytes()
            r2 = base / 'r2.json'
            q = run_verify(['--evidence', str(e), '--output', str(r2)])
            self.assertEqual(q.returncode, 0, q.stderr)
            self.assertEqual(stored, r2.read_bytes())


class Tamper(unittest.TestCase):
    def _expect_reject(self, mutate):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td); make_pack(base)
            mutate(base)
            e, r = base / 'e.json', base / 'r.json'
            q = run_verify(['--archive-root', str(base), '--build-evidence', str(e), '--output', str(r)])
            self.assertEqual(q.returncode, 2, q.stderr)

    def test_prompt_value_tamper(self):
        def m(base):
            p = base / 'loop7' / 't2-r1' / 'responses' / '001.response.bin'
            raw = p.read_bytes().decode('utf-8').replace('"prompt_tokens":7597', '"prompt_tokens":7596')
            p.write_bytes(raw.encode('utf-8'))
            meta = json.loads((p.parent / '001.response.bin.meta.json').read_text())
            meta['response_body_sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
            (p.parent / '001.response.bin.meta.json').write_text(json.dumps(meta))
        self._expect_reject(m)


    def test_cached_change_breaks_constant(self):
        def m(base):
            p = base / 'loop7' / 't2-r2' / 'responses' / '001.response.bin'
            raw = p.read_bytes().decode('utf-8').replace('"cached_tokens":7552', '"cached_tokens":7551')
            p.write_bytes(raw.encode('utf-8'))
            meta = json.loads((p.parent / '001.response.bin.meta.json').read_text())
            meta['response_body_sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
            (p.parent / '001.response.bin.meta.json').write_text(json.dumps(meta))
        self._expect_reject(m)

    def test_meta_sha_mismatch(self):
        def m(base):
            p = base / 'loop7' / 't2-r1' / 'responses' / '003.response.bin.meta.json'
            meta = json.loads(p.read_text()); meta['response_body_sha256'] = '0' * 64
            p.write_text(json.dumps(meta))
        self._expect_reject(m)

    def test_missing_source(self):
        def m(base):
            (base / 'loop7' / 't2-r1' / 'responses' / '007.response.bin').unlink()
        self._expect_reject(m)

    def test_identity_break(self):
        def m(base):
            p = base / 'loop7' / 't2-r2' / 'responses' / '007.response.bin'
            raw = p.read_bytes().decode('utf-8').replace('"total_tokens":8181', '"total_tokens":8182')
            p.write_bytes(raw.encode('utf-8'))
            meta = json.loads((p.parent / '007.response.bin.meta.json').read_text())
            meta['response_body_sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
            (p.parent / '007.response.bin.meta.json').write_text(json.dumps(meta))
        self._expect_reject(m)

    def test_finish_reason_invalid(self):
        def m(base):
            p = base / 'loop7' / 't2-r2' / 'responses' / '002.response.bin'
            raw = p.read_bytes().decode('utf-8').replace('"finish_reason":"stop"', '"finish_reason":"weird"')
            p.write_bytes(raw.encode('utf-8'))
            meta = json.loads((p.parent / '002.response.bin.meta.json').read_text())
            meta['response_body_sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
            (p.parent / '002.response.bin.meta.json').write_text(json.dumps(meta))
        self._expect_reject(m)

    def test_two_usage_chunks(self):
        def m(base):
            p = base / 'loop7' / 't2-r1' / 'responses' / '001.response.bin'
            raw = p.read_bytes().decode('utf-8')
            extra = 'data: ' + json.dumps({'id': 'z', 'choices': [], 'usage': usage(1, 0, 1)}) + '\n'
            p.write_bytes((raw + extra).encode('utf-8'))
            meta = json.loads((p.parent / '001.response.bin.meta.json').read_text())
            meta['response_body_sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
            (p.parent / '001.response.bin.meta.json').write_text(json.dumps(meta))
        self._expect_reject(m)

    def test_duplicate_json_key(self):
        def m(base):
            p = base / 'loop7' / 't2-r1' / 'responses' / '001.response.bin'
            raw = p.read_bytes().decode('utf-8').replace('"prompt_tokens":7597', '"prompt_tokens":7597,"cached_x":1', 1)
            p.write_bytes(raw.encode('utf-8'))
            meta = json.loads((p.parent / '001.response.bin.meta.json').read_text())
            meta['response_body_sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
            (p.parent / '001.response.bin.meta.json').write_text(json.dumps(meta))
        self._expect_reject(m)

    def test_detail_keys_wrong(self):
        def m(base):
            p = base / 'loop7' / 't2-r1' / 'responses' / '001.response.bin'
            raw = p.read_bytes().decode('utf-8').replace('"reasoning_tokens":0', '"reasoning_tokens":0,"extra":1')
            p.write_bytes(raw.encode('utf-8'))
            meta = json.loads((p.parent / '001.response.bin.meta.json').read_text())
            meta['response_body_sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
            (p.parent / '001.response.bin.meta.json').write_text(json.dumps(meta))
        self._expect_reject(m)

    def test_evidence_row_tamper_replay(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td); make_pack(base)
            e, r = base / 'e.json', base / 'r.json'
            q = run_verify(['--archive-root', str(base), '--build-evidence', str(e), '--output', str(r)])
            self.assertEqual(q.returncode, 0)
            ev = json.loads(e.read_text())
            ev['rows'][0]['cached_tokens'] = ev['rows'][0]['cached_tokens'] + 1
            bad = base / 'e_bad.json'
            bad.write_text(json.dumps(ev))
            q = run_verify(['--evidence', str(bad), '--output', str(base / 'r3.json')])
            self.assertEqual(q.returncode, 2)

    def test_schema_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            bad = base / 'e.json'; bad.write_text(json.dumps({'schema': 'other'}))
            q = run_verify(['--evidence', str(bad), '--output', str(base / 'r.json')])
            self.assertEqual(q.returncode, 2)

    def test_output_collision(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td); make_pack(base)
            e, r = base / 'e.json', base / 'r.json'
            q = run_verify(['--archive-root', str(base), '--build-evidence', str(e), '--output', str(r)])
            self.assertEqual(q.returncode, 0)
            q = run_verify(['--evidence', str(e), '--output', str(r)])
            self.assertEqual(q.returncode, 2)

    def test_conflicting_flags(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            q = run_verify(['--archive-root', str(base), '--evidence', str(base / 'x.json'),
                            '--output', str(base / 'r.json')])
            self.assertEqual(q.returncode, 2)

    def test_no_mode(self):
        with tempfile.TemporaryDirectory() as td:
            q = run_verify(['--output', str(Path(td) / 'r.json')])
            self.assertEqual(q.returncode, 2)

    def test_nonfinite_rejected(self):
        def m(base):
            p = base / 'loop7' / 't2-r1' / 'responses' / '001.response.bin'
            raw = p.read_bytes().decode('utf-8').replace('"cached_tokens":0', '"cached_tokens":1e999')
            p.write_bytes(raw.encode('utf-8'))
            meta = json.loads((p.parent / '001.response.bin.meta.json').read_text())
            meta['response_body_sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
            (p.parent / '001.response.bin.meta.json').write_text(json.dumps(meta))
        self._expect_reject(m)


class RealConstants(unittest.TestCase):
    def test_constants_shape(self):
        self.assertEqual(len(V.PROMPT_EXPECT), 7)
        self.assertEqual(sum(1 for a, b in zip(V.CACHED_EXPECT['t2-r1'], V.CACHED_EXPECT['t2-r2']) if a != b), 6)
        self.assertEqual(V.CACHED_EXPECT['t2-r2'][0], 7552)


if __name__ == '__main__':
    ap = sys.argv[1:]
    if ap and ap[0] == '--scratch-root':
        ROOT = Path(ap[1]); ROOT.mkdir(parents=True, exist_ok=True)
        os.environ['TMPDIR'] = str(ROOT)
    unittest.main(argv=[sys.argv[0]])
