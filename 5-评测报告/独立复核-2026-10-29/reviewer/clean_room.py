#!/usr/bin/env python3
"""Independent public-only offline runner; uses only Python standard library.

Writes evidence below its own reviewer directory; all mutations of reviewed input
occur only in a new /tmp copy. Requires both implementers' explicit readiness.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

PUBLIC_NEW = (
    '4-打分细则/可信冻结-2026-10-29',
    '5-评测报告/可信冻结-2026-10-29',
    '1-评测方案/机制实验-2026-10-29',
    '3-表现现场/r20261029-mechanism',
    '5-评测报告/独立复核-2026-10-29',
)
REVIEWER = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def run(command, cwd, env=None):
    p = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True)
    return {'command': command, 'exit_code': p.returncode,
            'stdout': p.stdout, 'stderr': p.stderr}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--ready-freeze', action='store_true')
    ap.add_argument('--ready-mechanism', action='store_true')
    ap.add_argument('--check-script', type=Path, required=True,
                    help='Independent Python checks, copied into clean root')
    ap.add_argument('--label', required=True)
    args = ap.parse_args()
    if not (args.ready_freeze and args.ready_mechanism):
        ap.error('Both implementers must explicitly publish ready before execution')
    if not args.label.replace('-', '').replace('_', '').isalnum():
        ap.error('Unsafe label')
    source = args.root.resolve()
    receipt_path = REVIEWER / (args.label + '.json')
    if receipt_path.exists():
        ap.error('Receipt already exists; use a new label to preserve first failure')
    tracked = subprocess.run(['git', 'ls-files', '-z'], cwd=source,
                             check=True, capture_output=True).stdout
    files = set(x.decode() for x in tracked.split(b'\0') if x)
    for folder in PUBLIC_NEW:
        files.update(str(p.relative_to(source)) for p in (source / folder).rglob('*') if p.is_file())
    # Keep self-contained deliverable without recursively copying old review receipts.
    files = sorted(x for x in files if not x.startswith('5-评测报告/独立复核-2026-10-29/reviewer/'))
    temp = Path(tempfile.mkdtemp(prefix='hcb-independent-20261029-', dir='/tmp')).resolve()
    clean = temp / 'public'
    clean.mkdir()
    home = temp / 'empty-home'
    home.mkdir()
    inputs = []
    for name in files:
        rel = Path(name)
        if rel.is_absolute() or '..' in rel.parts:
            raise RuntimeError('Unsafe public path: ' + name)
        src = source / rel
        if src.is_symlink() or not src.resolve().is_relative_to(source):
            raise RuntimeError('Refuse symlink or escaping public path: ' + name)
        if not src.is_file():
            raise RuntimeError('Missing public tracked file: ' + name)
        target = clean / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        inputs.append({'path': name, 'sha256': sha(target), 'bytes': target.stat().st_size})
    checks = clean / 'independent_checks.py'
    shutil.copy2(args.check_script, checks)
    check_sha = sha(checks)
    # Deny the complete original user home: repo, private automation, credentials,
    # original caches and login state. New empty HOME is outside this tree.
    original_home = str(Path.home().resolve())
    def quote(s):
        return json.dumps(s)
    profile_text = ('(version 1) (allow default) (deny network*) '
                    '(deny file-read* file-write* (subpath ' + quote(original_home) + ') '
                    '(subpath "/private/tmp") (subpath "/private/var/folders")) '
                    '(allow file-read* file-write* (subpath ' + quote(str(temp)) + '))')
    profile = temp / 'offline.sb'
    profile.write_text(profile_text)
    env = {'HOME': str(home), 'PATH': '/usr/bin:/bin:/usr/sbin:/sbin',
           'TMPDIR': str(temp), 'LANG': 'en_US.UTF-8', 'LC_ALL': 'en_US.UTF-8',
           'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1'}
    sandbox = ['/usr/bin/sandbox-exec', '-f', str(profile), '/usr/bin/python3']
    probe = """import errno,json,os,socket
out={}
for k,f in [('repo_read',lambda:open(%r).read()),('private_read',lambda:open(%r).read()),('old_tmp_read',lambda:open('/private/tmp').read()),('old_native_spill_tree_read',lambda:open('/private/var/folders').read()),('network_connect',lambda:socket.create_connection(('127.0.0.1',49169),timeout=2))]:
 try: f();out[k]={'unexpected_allowed':True}
 except OSError as e:out[k]={'errno':e.errno,'error':str(e)}
out['HOME_entries']=os.listdir(os.environ['HOME'])
out['public_copy_read']=bool(open('independent_checks.py').read())
print(json.dumps(out));assert all(out[k].get('errno') in (errno.EPERM,errno.EACCES) for k in ['repo_read','private_read','old_tmp_read','old_native_spill_tree_read','network_connect']);assert out['HOME_entries']==[];assert out['public_copy_read']
""" % (str(source / 'AGENTS.md'), str(Path(original_home) / 'bench-automation'))
    preflight = run(sandbox + ['-c', probe], clean, env)
    receipt = {'schema': 'independent-offline-review/1', 'label': args.label,
               'time_unix': time.time(), 'source_root': str(source),
               'clean_root': str(clean), 'empty_home': str(home),
               'scope': 'public offline reproduction, NOT online model rerun',
               'sandbox_profile': profile_text, 'environment': env,
               'runner_sha256': sha(__file__), 'checks_sha256': check_sha,
               'inputs': inputs, 'preflight': preflight}
    if preflight['exit_code'] == 0:
        receipt['checks'] = run(sandbox + [str(checks), '--root', str(clean)], clean, env)
        output = clean / 'independent-results.json'
        if output.exists():
            receipt['results'] = json.loads(output.read_text())
            receipt['results_sha256'] = sha(output)
    receipt['exit_code'] = preflight['exit_code'] or receipt.get('checks', {}).get('exit_code', 1)
    dump(receipt_path, receipt)
    print(json.dumps({'receipt': str(receipt_path), 'exit_code': receipt['exit_code'],
                      'clean_root': str(clean)}, ensure_ascii=False))
    raise SystemExit(receipt['exit_code'])


if __name__ == '__main__':
    main()
