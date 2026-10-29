#!/usr/bin/env python3
"""Mandatory external build membership using fake npm layouts; never execute products.
Actual user/app/profile contents are not read. PATH resolution is an injected map.
"""
import argparse
import contextlib
import copy
import datetime as dt
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    s = importlib.util.spec_from_file_location('seal_build_fixed_v4', a.source)
    mod = importlib.util.module_from_spec(s)
    s.loader.exec_module(mod)
    expected_base = {Path.home() / n for n in ('.dsh/profiles/bench-cli/cordis.patch.yml',
                     '.dsh/profiles/bench-cli/package.json', '.dsh/AGENTS.md',
                     'bench-workspaces/l4-20261029-cli/codex/_codex-home/config.toml')}
    expected_base.update({Path('/Applications/WorkBuddy.app/Contents/Info.plist'),
                          Path('/Applications/WorkBuddy.app/Contents/Resources/app.asar')})
    rows = [{'id': 'actual-base-six-path-constants', 'pass': set(mod.REQUIRED_EXTERNAL_FILES) == expected_base},
            {'id': 'both-cli-build-resolvers-mandatory', 'pass': set(mod.REQUIRED_EXECUTABLES) == {'dsh', 'codex'}}]
    with tempfile.TemporaryDirectory(prefix='l4-independent-build-') as td:
        root = Path(td).resolve()
        mod.ROOT = root
        mod.HERE = root / 'plans/loop4'
        mod.HERE.mkdir(parents=True)
        mod.MANIFEST = mod.HERE / 'execution-manifest.json'
        mod.REQUIRED_EXTERNAL_FILES = tuple(root / 'external-base' / str(i) for i in range(6))
        roles = {str(p): 'base-' + str(i) for i, p in enumerate(mod.REQUIRED_EXTERNAL_FILES)}
        def create(rel, role):
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('# synthetic data; not executable; ' + role + '\n')
            roles[str(p)] = role
            return p
        for p in mod.REQUIRED_EXTERNAL_FILES:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('# synthetic base configuration\n')
        dsh = create('fake-dsh/bin/dsh', 'dsh-launcher')
        create('fake-dsh/package.json', 'dsh-package-metadata')
        create('fake-dsh/lib/entry.js', 'dsh-own-lib-entry')
        create('fake-dsh/lib/runtime.js', 'dsh-own-lib-runtime')
        codex = create('fake-codex/bin/codex.js', 'codex-launcher')
        create('fake-codex/package.json', 'codex-package-metadata')
        create('fake-codex/node_modules/@openai/codex-darwin-arm64/vendor/aarch64-apple-darwin/bin/codex', 'codex-native-payload')
        paths = {'dsh': str(dsh), 'codex': str(codex)}
        mod.shutil = SimpleNamespace(which=lambda command: paths.get(command))
        selected = {str(p) for p in mod.required_external_paths()}
        rows.append({'id': 'all-thirteen-synthetic-build-members-selected', 'pass': selected == set(roles),
                     'observed_roles': [roles[p] for p in sorted(selected)]})
        for r in mod.RUNTIME_ROOTS:
            (root / r).mkdir(parents=True, exist_ok=True)
        for r in mod.REQUIRED_RUNTIME:
            p = root / r
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('# synthetic benchmark source fixture\n')
        for n in ('PREREGISTRATION.md', 'plan.json', 'contract.json', 'CLARIFICATION-L4-1.md',
                  'execution_seal.py', 'test_execution_seal.py'):
            (mod.HERE / n).write_text('# synthetic planning fixture\n')
        # Inject read-only commit blobs; no actual git repository or executable is needed.
        mod.resolve_commit = lambda value: 'd' * 40
        mod.git = lambda *args: (root / args[1].split(':', 1)[1]).read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            mod.manifest(SimpleNamespace(design='d' * 40, file=[], external_file=[]))
        doc = json.loads(mod.MANIFEST.read_text())
        rows.append({'id': 'actual-manifest-generator-explicitly-not-transitive-exhaustive',
                     'pass': doc.get('exhaustive_transitive_product_dependencies_pinned') is False})
        for path in sorted(selected):
            bad = copy.deepcopy(doc)
            del bad['external_files'][path]
            try:
                mod.validate_manifest(bad)
                rows.append({'id': 'omit:' + roles[path], 'pass': False, 'observed': 'accepted'})
            except ValueError as e:
                rows.append({'id': 'omit:' + roles[path], 'pass': 'mandatory external' in str(e), 'observed': str(e)})
        missing_native_launcher = create('missing-native-codex/bin/codex.js', 'missing-native-launcher-fixture')
        paths['codex'] = str(missing_native_launcher)
        try:
            mod.required_external_paths()
            rows.append({'id': 'missing-native-is-hard-failure', 'pass': False})
        except ValueError as e:
            rows.append({'id': 'missing-native-is-hard-failure', 'pass': 'native build' in str(e), 'observed': str(e)})
        paths['codex'] = None
        try:
            mod.required_external_paths()
            rows.append({'id': 'missing-cli-is-hard-failure', 'pass': False})
        except ValueError as e:
            rows.append({'id': 'missing-cli-is-hard-failure', 'pass': 'execution binary' in str(e), 'observed': str(e)})
    result = {'category': 'self_test', 'scope': 'Independent mandatory base/launcher/metadata/native/own-JS membership; synthetic layouts only; no actual product files/credentials read or executables launched; not exhaustive third-party closure',
              'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'live_doc_drift': [],
              'source_sha256': sha(a.source), 'reviewer_script_sha256': sha(Path(__file__)),
              'checks': rows, 'passed': all(r['pass'] for r in rows)}
    with a.out.open('x') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({'checks': len(rows), 'passed': sum(r['pass'] for r in rows),
                      'failed': [r['id'] for r in rows if not r['pass']], 'out': str(a.out)}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
