#!/usr/bin/env python3
"""L4 lead-only manifest/binding builder; never invokes any model API."""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MANIFEST = HERE / 'execution-manifest.json'
BINDING = HERE / 'runtime-binding.json'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def git(*args):
    p = subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True, check=True)
    return p.stdout

def rel(path):
    return str(Path(path).resolve().relative_to(ROOT))

def create(path, obj):
    # Exclusive create: existing files, including dangling symlinks, are refused.
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')

def resolve_commit(value):
    return git('rev-parse', '--verify', value + '^{commit}').decode().strip()

def manifest(args):
    design = resolve_commit(args.design)
    files = {}
    required = [HERE/'PREREGISTRATION.md', HERE/'plan.json', HERE/'contract.json', Path(__file__)]
    for path in required + [ROOT / p for p in args.file]:
        if not path.is_file() or path.is_symlink():
            raise ValueError('Expected regular non-symlink source: ' + str(path))
        files[rel(path)] = sha(path)
    for name in ('PREREGISTRATION.md', 'plan.json', 'contract.json'):
        path = HERE/name
        committed = git('show', design + ':' + rel(path))
        if hashlib.sha256(committed).hexdigest() != sha(path):
            raise ValueError('Design drift: ' + name)
    external = {}
    for name in args.external_file:
        path = Path(name).expanduser().absolute()
        if not path.is_file() or path.is_symlink():
            raise ValueError('Expected regular external source: ' + str(path))
        external[str(path)] = sha(path)
    doc = {'schema_version':1, 'design_commit':design,
           'generated_at':datetime.now().astimezone().isoformat(timespec='seconds'),
           'files':dict(sorted(files.items())), 'external_files':dict(sorted(external.items())),
           'policy':'All sources/configs pinned before first live request; outputs are append-only new paths.',
           'live_doc_drift':[]}
    create(MANIFEST, doc)
    print(json.dumps({'manifest':rel(MANIFEST),'sha256':sha(MANIFEST),'files':len(files),'external_files':len(external)},ensure_ascii=False))

def bind(args):
    seal = resolve_commit(args.seal)
    manifest_bytes = git('show', seal + ':' + rel(MANIFEST))
    if manifest_bytes != MANIFEST.read_bytes():
        raise ValueError('Manifest differs from sealed blob')
    doc = json.loads(manifest_bytes)
    design = doc['design_commit']
    git('merge-base', '--is-ancestor', design, seal)
    git('merge-base', '--is-ancestor', seal, 'HEAD')
    for name, expected in doc['files'].items():
        path = ROOT/name
        if sha(path) != expected:
            raise ValueError('Source drift: ' + name)
        if hashlib.sha256(git('show', seal+':'+name)).hexdigest() != expected:
            raise ValueError('Source not in execution seal: ' + name)
    for name, expected in doc.get('external_files',{}).items():
        if sha(name) != expected:
            raise ValueError('External source drift: ' + name)
    for name in ('PREREGISTRATION.md','plan.json','contract.json'):
        path = rel(HERE/name)
        if git('show',design+':'+path) != git('show',seal+':'+path):
            raise ValueError('Design/execution blob mismatch: ' + name)
    stamp = git('show','-s','--format=%cI',seal).decode().strip()
    binding = {'schema_version':1,'design_commit':design,
               'preregistration_commit':seal,'execution_seal_commit':seal,
               'registered_at':stamp,'execution_manifest_sha256':sha(MANIFEST),
               'plan_sha256':sha(HERE/'plan.json'),'contract_sha256':sha(HERE/'contract.json'),
               'released_for_model_calls':bool(args.release),
               'generated_at':datetime.now().astimezone().isoformat(timespec='seconds'),
               'live_doc_drift':[]}
    create(BINDING,binding)
    print(json.dumps(binding, ensure_ascii=False, indent=2))

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest='action',required=True)
    m=sub.add_parser('manifest')
    m.add_argument('--design',required=True)
    m.add_argument('--file',action='append',default=[])
    m.add_argument('--external-file',action='append',default=[])
    b=sub.add_parser('bind')
    b.add_argument('--seal',required=True)
    b.add_argument('--release',action='store_true')
    args=ap.parse_args()
    try:
        (manifest if args.action=='manifest' else bind)(args)
    except (ValueError,OSError,subprocess.CalledProcessError) as exc:
        ap.exit(2,'FAIL-CLOSED: '+str(exc)+'\n')

if __name__=='__main__':
    main()
