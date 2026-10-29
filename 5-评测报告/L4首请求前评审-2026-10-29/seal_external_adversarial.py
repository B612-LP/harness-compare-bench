#!/usr/bin/env python3
"""Independently check mandatory config membership using synthetic files only."""
import argparse
import copy
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    spec = importlib.util.spec_from_file_location('seal_external_fixed', a.source)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    expected = [Path.home() / n for n in ('.dsh/profiles/bench-cli/cordis.patch.yml',
                '.dsh/profiles/bench-cli/package.json', '.dsh/AGENTS.md',
                'bench-workspaces/l4-20261029-cli/codex/_codex-home/config.toml')]
    repo_configs = ['3-表现现场/l4-20261029-cli/codex/config/codex-config.toml',
                    '3-表现现场/l4-20261029-cache/config/probe-config.json']
    actual = list(mod.REQUIRED_EXTERNAL_FILES)
    rows = [{'id': 'actual-path-mandatory-set', 'pass': set(actual) == set(expected),
             'observed_paths': [str(p) for p in actual]}]
    with tempfile.TemporaryDirectory(prefix='l4-independent-external-') as td:
        root = Path(td).resolve()
        mod.ROOT = root
        mod.HERE = root / 'plans/loop4'
        mod.HERE.mkdir(parents=True)
        # Never read actual external paths: replace with four disposable fixtures.
        mod.REQUIRED_EXTERNAL_FILES = tuple(root / 'external' / str(i) for i in range(4))
        for p in mod.REQUIRED_EXTERNAL_FILES:
            p.parent.mkdir(exist_ok=True)
            p.write_text('# synthetic config; no credentials\n')
        for r in mod.RUNTIME_ROOTS:
            (root / r).mkdir(parents=True, exist_ok=True)
        for r in mod.REQUIRED_RUNTIME:
            p = root / r
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('# synthetic runtime fixture; not executed\n')
        for n in ('PREREGISTRATION.md', 'plan.json', 'contract.json', 'CLARIFICATION-L4-1.md',
                  'execution_seal.py', 'test_execution_seal.py'):
            (mod.HERE / n).write_text('# synthetic planning fixture\n')
        files = {n: sha(root / n) for n in mod.required_files()}
        ext = {str(p): sha(p) for p in mod.REQUIRED_EXTERNAL_FILES}
        doc = {'schema_version': 1, 'design_commit': 'd' * 40, 'files': files, 'external_files': ext}
        try:
            mod.validate_manifest(doc)
            rows.append({'id': 'positive-complete-mandatory-config', 'pass': True})
        except Exception as e:
            rows.append({'id': 'positive-complete-mandatory-config', 'pass': False, 'error': repr(e)})
        attacks = [('empty-external', None)] + [('omit-external-' + str(i), p) for i, p in enumerate(ext)]
        for label, path in attacks:
            bad = copy.deepcopy(doc)
            if path is None:
                bad['external_files'] = {}
            else:
                del bad['external_files'][path]
            try:
                mod.validate_manifest(bad)
                rows.append({'id': label, 'pass': False, 'observed': 'accepted'})
            except ValueError as e:
                rows.append({'id': label, 'pass': 'mandatory external' in str(e), 'observed': str(e)})
        for path in repo_configs:
            bad = copy.deepcopy(doc)
            bad['files'].pop(path, None)
            try:
                mod.validate_manifest(bad)
                rows.append({'id': 'omit-repo-config:' + path, 'pass': False, 'observed': 'accepted'})
            except ValueError as e:
                rows.append({'id': 'omit-repo-config:' + path, 'pass': 'missing required' in str(e), 'observed': str(e)})
    result = {'category': 'self_test', 'scope': 'Independent mandatory membership and external path constants; all file contents synthetic; not actual build/import closure',
              'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'live_doc_drift': [],
              'source_sha256': sha(a.source), 'reviewer_script_sha256': sha(Path(__file__)),
              'checks': rows, 'passed': all(r['pass'] for r in rows)}
    with a.out.open('x') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({'checks': len(rows), 'passed': sum(r['pass'] for r in rows), 'out': str(a.out)}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
