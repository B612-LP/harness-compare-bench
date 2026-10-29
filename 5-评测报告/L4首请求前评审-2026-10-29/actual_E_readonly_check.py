#!/usr/bin/env python3
"""Independent actual-E audit: read-only git, raw byte hashing, no product invocation.
External configs/packages are streamed into SHA only, never decoded or printed.
Only new reviewer-scope receipts/copies are written. No manifest/binding is edited.
"""
import argparse
import ast
import datetime as dt
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess

D = 'bb14897a7d1ac26c06697bb80a15d94158cd8ae0'
E = '5674de65c05c632eb20fbd2e30bdeb7e08c6753a'
LOOP = '1-评测方案/自动循环L4-2026-10-29'
REVIEWED = {
    '1-评测方案/工具链/l4-execution/gate.py': '77d8e8b4817e269dc3cf1ed127e4d30ec9bee7bfa161769115d04dc8bb3a6c9f',
    '1-评测方案/工具链/l4-execution/replay_dual.py': '8b710a6ee63b0838328166b3c76678ee7d60da6514fe3d363281bcf3a7496179',
    LOOP + '/execution_seal.py': 'f1ef03402358d33b70f1d54be529f1bfaece7d1113b0588c5308f19383fef240',
    LOOP + '/test_execution_seal.py': 'ac03c81761f47397c8bac76900fa77681ba928e113949a81c1420b765513271e',
    '3-表现现场/l4-20261029-cli/dsh/tools/lab.py': 'f246d0113219b325341ac35f75ad5e194a68da4a15a73a2761639133f6f4e19d',
    '1-评测方案/工具链/evidence-kit/receipt_check.py': 'effda0ed1c89876849008421782a701cf3c18a6c80c2434b76db389290fc2eb3',
    '1-评测方案/工具链/evidence-kit/evidence_line.py': '9b00febf436104e4bbed3442da26f76d8b8e3105c96fac8b144feae99a6dfe6b',
    '1-评测方案/工具链/runner-schema-v2/validate_runner_meta.py': '8e423de5605c7c6ebda627e70cee3bfb7e0159fc4f9f046048a8ecc27797aef4',
}
# These four hashes are supplied by Lead from the separate judge-owned producer
# reviews, not a claim that this reviewer reran those product integrations.
JUDGE_REFERENCED = {
    '3-表现现场/l4-20261029-cli/codex/tools/lab.py': '0b3d8c910e2d5a3498b28d11c5455bcf62fdf08b5f5d9b1ee0917fa8e74c01de',
    '3-表现现场/l4-20261029-cache/tools/cache_probe.py': '80f2343df454cb2aad3e50d954558011abc5322b1c0fa10fa666358c56027f11',
    '3-表现现场/l4-20261029-wb-gateway/runner/l4_wb_runner.py': '8634390fbb7831dd10e164c06c606301da7c35ebe858ce15afe394061c1ad1bf',
    '3-表现现场/l4-20261029-wb-gateway/runner/safe_driver.py': 'a2105457f5762285b04d7bb2af381e6acb289559b0bcc90e55bfd0a07d77142f',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    root = a.root.resolve()
    out = a.out.resolve()
    expected_scope = root / '5-评测报告/L4首请求前评审-2026-10-29'
    assert out.parent == expected_scope and not out.exists()
    commands = []
    def git(*args, allowed=(0,)):
        p = subprocess.run(['git', '-C', str(root), *args], capture_output=True, timeout=60)
        commands.append({'args': list(args), 'exit_code': p.returncode})
        if p.returncode not in allowed:
            raise RuntimeError('read-only git failed: ' + str(args) + ': ' + p.stderr.decode(errors='replace')[:600])
        return p
    def blob(commit, name):
        return git('show', commit + ':' + name).stdout
    checks = []
    def check(label, passed, detail=None):
        checks.append({'id': label, 'pass': bool(passed), 'detail': detail})

    bp, mp = root / LOOP / 'runtime-binding.json', root / LOOP / 'execution-manifest.json'
    raw_b, raw_m = bp.read_bytes(), mp.read_bytes()
    b, m = json.loads(raw_b), json.loads(raw_m)
    check('binding-design-exact-D', b.get('design_commit') == D)
    check('binding-preregistration-exact-E', b.get('preregistration_commit') == E)
    check('binding-execution-exact-E', b.get('execution_seal_commit') == E)
    check('binding-release-bit-true-bool', b.get('released_for_model_calls') is True)
    check('manifest-design-exact-D', m.get('design_commit') == D)
    check('manifest-E-blob-identical-to-disk', blob(E, LOOP + '/execution-manifest.json') == raw_m)
    check('manifest-sha-exact-binding', digest(raw_m) == b.get('execution_manifest_sha256'))
    check('manifest-repo-count-42', len(m['files']) == 42)
    check('manifest-external-count-17', len(m['external_files']) == 17)
    check('not-exhaustive-third-party-closure', m.get('exhaustive_transitive_product_dependencies_pinned') is False)
    e_time = git('show', '-s', '--format=%cI', E).stdout.decode().strip()
    check('registered-at-exact-E-committer-time-string', b.get('registered_at') == e_time,
          {'registered_at': b.get('registered_at'), 'actual_E_time': e_time})
    check('manifest-generated-at-exact-E-time', m.get('generated_at') == e_time)
    check('binding-generated-not-before-E', dt.datetime.fromisoformat(b['generated_at']) >= dt.datetime.fromisoformat(e_time))
    for ancestor, descendant, label in ((D, E, 'D-ancestor-of-E'), (E, 'HEAD', 'E-ancestor-of-HEAD')):
        p = git('merge-base', '--is-ancestor', ancestor, descendant, allowed=(0, 1))
        check(label, p.returncode == 0)
    head = git('rev-parse', 'HEAD').stdout.decode().strip()

    # Independently traverse the already-reviewed closure policy. Parse literal
    # constant tuples only; do not import/execute candidate sealing or gate code.
    seal_bytes = blob(E, LOOP + '/execution_seal.py')
    tree = ast.parse(seal_bytes)
    const = {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            if n.targets[0].id in ('RUNTIME_ROOTS', 'REQUIRED_RUNTIME'):
                const[n.targets[0].id] = ast.literal_eval(n.value)
    required = {LOOP + '/' + n for n in ('PREREGISTRATION.md', 'plan.json', 'contract.json',
                'CLARIFICATION-L4-1.md', 'execution_seal.py', 'test_execution_seal.py')}
    required.update(const['REQUIRED_RUNTIME'])
    traversal_problems = []
    for base in [root / LOOP] + [root / p for p in const['RUNTIME_ROOTS']]:
        if not base.is_dir() or base.is_symlink() or base.resolve() != base.absolute():
            traversal_problems.append(str(base))
            continue
        for p in base.rglob('*'):
            if p.is_symlink():
                traversal_problems.append(str(p.relative_to(root)))
                continue
            if '__pycache__' in p.relative_to(base).parts or p.suffix == '.pyc':
                continue
            runtime = base != root / LOOP and p.is_file()
            plan_source = p.suffix in ('.py', '.toml', '.yaml', '.yml') or (p.suffix == '.json' and 'config' in p.name.lower())
            if runtime or plan_source:
                required.add(str(p.relative_to(root)))
    check('required-tree-canonical-no-symlinks', not traversal_problems, traversal_problems)
    check('independent-required-set-exact-42', required == set(m['files']),
          {'required_count': len(required), 'missing': sorted(required - set(m['files'])),
           'extra': sorted(set(m['files']) - required)})
    repo_rows = []
    for name, want in m['files'].items():
        rel = PurePosixPath(name)
        p = root / name
        safe = not rel.is_absolute() and '..' not in rel.parts and str(rel) == name
        regular = p.is_file() and not p.is_symlink() and p.resolve() == p.absolute()
        e_data = blob(E, name)
        disk_data = p.read_bytes() if regular else b''
        row = {'path': name, 'safe_regular': safe and regular, 'manifest_sha256': want,
               'E_blob_sha256': digest(e_data), 'disk_sha256': digest(disk_data),
               'exact_bytes_equal': e_data == disk_data,
               'pass': safe and regular and digest(e_data) == want and e_data == disk_data}
        repo_rows.append(row)
        check('repo-E-blob-disk:' + name, row['pass'])
    for name in ('PREREGISTRATION.md', 'plan.json', 'contract.json'):
        rel = LOOP + '/' + name
        d_blob, e_blob = blob(D, rel), blob(E, rel)
        check('D-E-disk-original:' + name, d_blob == e_blob == (root / rel).read_bytes())
    for name, key in (('plan.json', 'plan_sha256'), ('contract.json', 'contract_sha256')):
        check('binding-' + key + '-matches-disk', file_sha(root / LOOP / name) == b.get(key))
    for name, want in REVIEWED.items():
        check('reviewer-accepted-source:' + name, m['files'].get(name) == want)
    for name, want in JUDGE_REFERENCED.items():
        check('judge-referenced-source:' + name, m['files'].get(name) == want)

    external_required = {str((Path.home() / p).resolve()) for p in (
        '.dsh/profiles/bench-cli/cordis.patch.yml', '.dsh/profiles/bench-cli/package.json',
        '.dsh/AGENTS.md', 'bench-workspaces/l4-20261029-cli/codex/_codex-home/config.toml')}
    external_required.update(['/Applications/WorkBuddy.app/Contents/Info.plist',
                              '/Applications/WorkBuddy.app/Contents/Resources/app.asar'])
    resolved_commands = {}
    for cmd in ('dsh', 'codex'):
        found = shutil.which(cmd)  # resolution only; never execute CLI/version command
        check('CLI-launcher-resolves:' + cmd, found is not None)
        if not found:
            continue
        target = Path(found).resolve()
        resolved_commands[cmd] = str(target)
        external_required.add(str(target))
        package = target.parent.parent / 'package.json'
        if package.is_file():
            external_required.add(str(package.resolve()))
        if cmd == 'codex':
            native = target.parent.parent / 'node_modules/@openai/codex-darwin-arm64/vendor/aarch64-apple-darwin/bin/codex'
            check('Codex-actual-native-payload-exists', native.is_file())
            external_required.add(str(native.resolve()))
        else:
            js = sorted((target.parent.parent / 'lib').glob('*.js'))
            check('DSH-own-lib-JS-nonempty', bool(js), len(js))
            external_required.update(str(p.resolve()) for p in js)
    check('independent-external-required-exact-17', external_required == set(m['external_files']),
          {'required_count': len(external_required), 'missing': sorted(external_required - set(m['external_files'])),
           'extra': sorted(set(m['external_files']) - external_required)})
    external_rows = []
    for name, want in m['external_files'].items():
        p = Path(name)
        regular = p.is_absolute() and p.is_file() and not p.is_symlink() and p.resolve() == p
        got = file_sha(p) if regular else None
        row = {'path': name, 'canonical_regular': regular, 'manifest_sha256': want,
               'disk_sha256': got, 'pass': regular and got == want}
        external_rows.append(row)
        check('external-raw-SHA-only:' + name, row['pass'])
    w = json.loads((root / LOOP / 'selftest/comment-whitespace-equivalence.json').read_bytes())
    check('WB-comment-delta-receipt-bound-to-manifest',
          w.get('new_sha256') == m['files'].get(w.get('file'))
          and w.get('old_sha256') == '8c90165f7896adff4379435bc8721e5f63434cdb2f48e84940b046524fdb54c6'
          and w.get('ast_identical') is True and w.get('only_trailing_comment_whitespace_removed') is True)
    check('binding-unchanged-during-audit', bp.read_bytes() == raw_b)
    check('manifest-unchanged-during-audit', mp.read_bytes() == raw_m)
    failed = [c['id'] for c in checks if not c['pass']]
    result = {'category': 'interface_preflight', 'scope': 'Independent real E blob/membership/byte audit, not product execution or trusted timestamp attestation',
              'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'execution_seal_commit': E,
              'design_commit': D, 'HEAD': head, 'registered_at': b['registered_at'],
              'binding_sha256': digest(raw_b), 'manifest_sha256': digest(raw_m),
              'reviewer_script_sha256': file_sha(Path(__file__)), 'repo_files': repo_rows,
              'external_files': external_rows, 'resolved_CLI_paths_not_invoked': resolved_commands,
              'checks': checks, 'counts': {'total': len(checks), 'passed': len(checks) - len(failed), 'failed': len(failed)},
              'read_only_git_commands': commands, 'passed': not failed, 'live_doc_drift': [],
              'release_semantics': {'binding_bit': b['released_for_model_calls'],
                  'scheduling_hold_per_lead': True, 'audit_launched_products_or_models': False,
                  'opinion_if_pass': 'E is eligible for Lead scheduling release; no request released by this audit'},
              'limitations': ['external bytes hashed only, not decoded', 'not exhaustive transitive product dependency closure',
                  'Git committer time is exact binding evidence, not trusted wallclock proof',
                  'WB comment-only delta provenance is Lead-reported plus bound selftest receipt, not an independent old-body reconstruction',
                  'producer integration semantics rely on separately judge-owned evidence, not rerun here']}
    with out.open('x') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    for name, raw in (('actual-E-runtime-binding-reviewed.json', raw_b), ('actual-E-manifest-reviewed.json', raw_m)):
        with (out.parent / name).open('xb') as f:
            f.write(raw)
    print(json.dumps({'passed': not failed, 'counts': result['counts'], 'failed': failed,
                      'manifest_sha256': digest(raw_m), 'binding_sha256': digest(raw_b), 'out': str(out)}))
    return 0 if not failed else 1


if __name__ == '__main__':
    raise SystemExit(main())
