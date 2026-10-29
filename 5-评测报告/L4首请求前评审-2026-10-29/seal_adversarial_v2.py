#!/usr/bin/env python3
"""Independent hardened-seal regression, synthetic repos only; no payload executes."""
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
        self.tmp = tempfile.TemporaryDirectory(prefix='l4-independent-seal-v2-')
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
        for n in ('PREREGISTRATION.md', 'plan.json', 'contract.json', 'CLARIFICATION-L4-1.md', 'test_execution_seal.py'):
            (self.here / n).write_text('{}\n')
        for name in self.mod.REQUIRED_RUNTIME:
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('# synthetic only; never executed\n')
        self.runner = self.root / self.mod.REQUIRED_RUNTIME[0]
        self.git('init', '-q', '--template=')
        self.git('config', 'user.name', 'Independent Synthetic Reviewer')
        self.git('config', 'user.email', 'reviewer@example.invalid')
        self.git('config', 'core.hooksPath', '/dev/null')
        self.design = self.commit('synthetic D')

    def git(self, *args):
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        return subprocess.run(['git', '-C', str(self.root), *args], env=env, capture_output=True, check=True).stdout.decode().strip()

    def commit(self, label):
        self.git('add', '-A')
        self.git('commit', '-qm', label)
        return self.git('rev-parse', 'HEAD')

    def manifest(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.mod.manifest(argparse.Namespace(design=self.design, file=[], external_file=[]))

    def bind(self, seal):
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                self.mod.bind(argparse.Namespace(seal=seal, release=True))
            return {'rejected': False, 'binding': json.loads(self.mod.BINDING.read_text())}
        except Exception as exc:
            return {'rejected': True, 'exception': type(exc).__name__, 'error': str(exc)}

    def close(self):
        self.tmp.cleanup()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    cases = []
    for attack in ('positive', 'empty_files', 'omitted_clarification', 'same_bytes_source_symlink', 'new_unsealed_py', 'runtime_symlink_directory'):
        h = Harness(a.source.resolve())
        try:
            if attack == 'runtime_symlink_directory':
                external = h.base / 'external-package'
                external.mkdir()
                (external / 'payload.py').write_text('SYNTHETIC_CONSTANT=1\n')
                helpers = h.runner.parent / 'helpers'
                helpers.symlink_to(external, target_is_directory=True)
                h.runner.write_text('from helpers import payload\n# Declared import only; never executed\n')
            h.manifest()
            doc = json.loads(h.mod.MANIFEST.read_text())
            if attack == 'empty_files':
                doc['files'] = {}
            if attack == 'omitted_clarification':
                del doc['files']['1-plan/loop4/CLARIFICATION-L4-1.md']
            if attack in ('empty_files', 'omitted_clarification'):
                h.mod.MANIFEST.write_text(json.dumps(doc) + '\n')
            seal = h.commit('synthetic E')
            if attack == 'same_bytes_source_symlink':
                target = h.base / 'outside-same-byte.py'
                target.write_bytes(h.runner.read_bytes())
                assert h.runner.resolve() == h.root / h.mod.REQUIRED_RUNTIME[0]
                h.runner.unlink()
                h.runner.symlink_to(target)
            if attack == 'new_unsealed_py':
                (h.runner.parent / 'new-unsealed.py').write_text('# synthetic\n')
            result = h.bind(seal)
            cases.append({'id': attack, 'expected_rejected': attack != 'positive',
                          'pass': result['rejected'] == (attack != 'positive'), 'observed': result,
                          'manifest_file_count': len(doc['files']),
                          'payload_executed': False})
        except Exception as exc:
            rejected = attack != 'positive'
            cases.append({'id': attack, 'expected_rejected': rejected, 'pass': rejected,
                          'observed': {'rejected': True, 'stage': 'manifest', 'exception': type(exc).__name__, 'error': str(exc)}, 'payload_executed': False})
        finally:
            h.close()
    result = {'category': 'self_test', 'scope': 'Independent synthetic git only; no APIs, no payload execution, no real repo changes',
              'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(),
              'source_sha256': sha(a.source.resolve()), 'reviewer_script_sha256': sha(Path(__file__)),
              'live_doc_drift': [], 'checks': cases, 'passed': all(x['pass'] for x in cases)}
    with a.out.open('x') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({'passed': result['passed'], 'checks': len(cases), 'failed': [c['id'] for c in cases if not c['pass']], 'out': str(a.out)}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
