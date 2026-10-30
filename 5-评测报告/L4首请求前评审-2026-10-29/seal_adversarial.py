#!/usr/bin/env python3
"""Independent no-API attacks against execution_seal in fresh synthetic git repos.
Never invokes real manifest/bind entry points against the user's repository.
"""
import argparse
import contextlib
import datetime as dt
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


class Harness:
    def __init__(self, source):
        self.tmp = tempfile.TemporaryDirectory(prefix='l4-independent-seal-')
        self.base = Path(self.tmp.name).resolve()
        self.root = self.base / 'repo'
        self.here = self.root / '1-plan' / 'loop4'
        self.here.mkdir(parents=True)
        spec = importlib.util.spec_from_file_location('independent_seal_target', source)
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)
        self.mod.ROOT = self.root
        self.mod.HERE = self.here
        self.mod.MANIFEST = self.here / 'execution-manifest.json'
        self.mod.BINDING = self.here / 'runtime-binding.json'
        self.mod.__file__ = str(self.here / 'execution_seal.py')
        (self.here / 'execution_seal.py').write_bytes(source.read_bytes())
        for n in ('PREREGISTRATION.md', 'plan.json', 'contract.json'):
            (self.here / n).write_text('{}\n')
        self.runner = self.here / 'synthetic-runner.py'
        self.runner.write_text('# SYNTHETIC, NO API\n')
        self.git('init', '-q', '--template=')
        self.git('config', 'user.name', 'Independent Synthetic Reviewer')
        self.git('config', 'user.email', 'reviewer@example.invalid')
        self.git('config', 'core.hooksPath', '/dev/null')
        self.design = self.commit('synthetic D')

    def git(self, *args):
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        p = subprocess.run(['git', '-C', str(self.root), *args], env=env, capture_output=True, check=True)
        return p.stdout.decode().strip()

    def commit(self, label):
        self.git('add', '1-plan/loop4')
        self.git('commit', '-qm', label)
        return self.git('rev-parse', 'HEAD')

    def manifest(self, include_runner=True):
        capture = io.StringIO()
        with contextlib.redirect_stdout(capture):
            self.mod.manifest(argparse.Namespace(design=self.design, file=['1-plan/loop4/synthetic-runner.py'] if include_runner else [], external_file=[]))
        return capture.getvalue()

    def binding(self, seal):
        capture = io.StringIO()
        try:
            with contextlib.redirect_stdout(capture):
                self.mod.bind(argparse.Namespace(seal=seal, release=True))
            return {'rejected': False, 'stdout': capture.getvalue(), 'binding': json.loads(self.mod.BINDING.read_text())}
        except Exception as exc:
            return {'rejected': True, 'exception': type(exc).__name__, 'error': str(exc), 'stdout': capture.getvalue()}

    def close(self):
        self.tmp.cleanup()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    source = args.source.resolve()
    results = []
    for attack in ('positive', 'empty_files_manifest', 'source_symlink_after_seal', 'missing_clarification'):
        h = Harness(source)
        try:
            h.manifest()
            if attack == 'empty_files_manifest':
                obj = json.loads(h.mod.MANIFEST.read_text())
                obj['files'] = {}
                h.mod.MANIFEST.write_text(json.dumps(obj) + '\n')
            seal = h.commit('synthetic E')
            if attack == 'source_symlink_after_seal':
                target = h.base / 'external-runner.py'
                target.write_bytes(h.runner.read_bytes())
                intended = h.here / 'synthetic-runner.py'
                assert h.runner.resolve() == intended and intended.is_relative_to(h.root)
                h.runner.unlink()
                h.runner.symlink_to(target)
            observed = h.binding(seal)
            expected_reject = attack != 'positive'
            results.append({'id': attack, 'expected_rejected': expected_reject,
                            'pass': observed['rejected'] == expected_reject,
                            'synthetic_git_only': True, 'observed': observed})
        finally:
            h.close()
    obj = {'category': 'self_test', 'scope': 'Independent synthetic git source-binding attacks; zero APIs, no real repo mutation',
           'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(),
           'source': str(source), 'source_sha256': sha(source),
           'reviewer_script_sha256': sha(Path(__file__)), 'live_doc_drift': [],
           'checks': results, 'passed': all(x['pass'] for x in results)}
    with args.out.open('x') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({'passed': obj['passed'], 'checks': len(results), 'failed': [x['id'] for x in results if not x['pass']], 'out': str(args.out)}, ensure_ascii=False))
    return 0 if obj['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
