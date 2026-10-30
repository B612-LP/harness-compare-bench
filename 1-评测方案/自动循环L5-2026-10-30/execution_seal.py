#!/usr/bin/env python3
"""L5 lead-only manifest/binding builder; never invokes any model API."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import PurePosixPath
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MANIFEST = HERE / 'execution-manifest.json'
BINDING = HERE / 'runtime-binding.json'
REQUIRED_EXTERNAL_FILES = (
    Path.home()/'.dsh/profiles/bench-cli/cordis.patch.yml',
    Path.home()/'.dsh/profiles/bench-cli/package.json',
    Path.home()/'.dsh/AGENTS.md',
    Path.home()/'bench-workspaces/l5-20261030-cli/codex/_codex-home/config.toml',
    Path('/Applications/WorkBuddy.app/Contents/Info.plist'),
    Path('/Applications/WorkBuddy.app/Contents/Resources/app.asar'),
)
REQUIRED_EXECUTABLES = ('dsh', 'codex')

def required_external_paths():
    paths = list(REQUIRED_EXTERNAL_FILES)
    for command in REQUIRED_EXECUTABLES:
        found = shutil.which(command)
        if not found:
            raise ValueError('Missing execution binary: '+command)
        target=Path(found).resolve()
        paths.append(target)
        package_manifest=target.parent.parent/'package.json'
        if package_manifest.is_file():
            paths.append(package_manifest.resolve())
        if command == 'codex':
            # This preregistered host is macOS arm64; pin the native payload,
            # not only npm's JavaScript launcher. No executable is launched here.
            native=target.parent.parent/'node_modules/@openai/codex-darwin-arm64/vendor/aarch64-apple-darwin/bin/codex'
            if not native.is_file():
                raise ValueError('Missing registered Codex native build: '+str(native))
            paths.append(native.resolve())
        elif command == 'dsh':
            paths.extend(p.resolve() for p in sorted((target.parent.parent/'lib').glob('*.js')))
    return paths

RUNTIME_ROOTS = (
    '1-评测方案/工具链/l5-execution',
    '3-表现现场/l5-20261030-cli/codex/tools',
    '3-表现现场/l5-20261030-cli/dsh/tools',
    '3-表现现场/l5-20261030-wb-gateway/runner',
    '3-表现现场/l5-20261030-wb-gateway/driver-snapshot',
)
REQUIRED_RUNTIME = (
    '1-评测方案/工具链/l5-execution/gate.py',
    '1-评测方案/工具链/runner-schema-v2/validate_runner_meta.py',
    '1-评测方案/工具链/evidence-kit/evidence_line.py',
    '1-评测方案/工具链/evidence-kit/receipt_check.py',
    '3-表现现场/l5-20261030-cli/codex/tools/lab.py',
    '3-表现现场/l5-20261030-cli/dsh/tools/lab.py',
    '3-表现现场/l5-20261030-cli/codex/config/codex-config.toml',
    '3-表现现场/l5-20261030-wb-gateway/runner/l5_wb_runner.py',
    '3-表现现场/l5-20261030-wb-gateway/driver-snapshot/workbuddy_driver.py',
)

def required_files():
    loop = str(HERE.relative_to(ROOT))
    required = {loop+'/'+p for p in (
        'PREREGISTRATION.md','plan.json','contract.json',
        'execution_seal.py','test_execution_seal.py')}
    required.update(REQUIRED_RUNTIME)
    # Discover actual implementation modules/configuration, not a self-reported empty list.
    for base in (HERE,) + tuple(ROOT / r for r in RUNTIME_ROOTS):
        if not base.is_dir() or base.is_symlink() or base.resolve()!=base.absolute():
            raise ValueError('Missing/nonregular runtime source directory: '+str(base))
        for path in base.rglob('*'):
            if path.is_symlink():
                raise ValueError('Runtime tree symlink refused: '+str(path))
            # Imported bytecode is a generated cache, never a declared source;
            # execution uses PYTHONDONTWRITEBYTECODE. Reject symlinks before skipping caches.
            if '__pycache__' in path.relative_to(base).parts or path.suffix=='.pyc':
                continue
            is_runtime = base != HERE and path.is_file()
            is_plan_source = path.suffix in ('.py','.toml','.yaml','.yml') or (
                path.suffix=='.json' and 'config' in path.name.lower())
            if is_runtime or is_plan_source:
                required.add(str(path.relative_to(ROOT)))
    return required

def regular_source(name):
    if not isinstance(name,str) or str(PurePosixPath(name)) != name:
        raise ValueError('Noncanonical source path: '+str(name))
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts:
        raise ValueError('Unsafe source path: '+name)
    path=ROOT/name
    if not path.is_file() or path.is_symlink() or path.resolve()!=path.absolute():
        raise ValueError('Expected regular non-symlink source: '+name)
    path.resolve().relative_to(ROOT.resolve())
    return path

def validate_manifest(doc):
    if not isinstance(doc,dict) or doc.get('schema_version')!=1:
        raise ValueError('Invalid manifest schema')
    if not re.fullmatch(r'[0-9a-f]{40}',str(doc.get('design_commit',''))):
        raise ValueError('Manifest needs full design commit')
    files=doc.get('files')
    if not isinstance(files,dict) or not files:
        raise ValueError('Manifest files must be nonempty')
    missing=required_files()-set(files)
    if missing:
        raise ValueError('Manifest missing required sources: '+str(sorted(missing)))
    for name,value in files.items():
        regular_source(name)
        if not isinstance(value,str) or not re.fullmatch(r'[0-9a-f]{64}',value):
            raise ValueError('Invalid source SHA: '+name)
    ext=doc.get('external_files')
    if not isinstance(ext,dict):
        raise ValueError('Invalid external_files schema')
    mandatory_external={str(Path(p).resolve()) for p in required_external_paths()}
    if mandatory_external-set(ext):
        raise ValueError('Manifest missing mandatory external configuration: '+str(sorted(mandatory_external-set(ext))))
    for name,value in ext.items():
        path=Path(name)
        if not path.is_absolute() or path.resolve()!=path or not path.is_file() or path.is_symlink():
            raise ValueError('Expected regular canonical external source: '+name)
        if not isinstance(value,str) or not re.fullmatch(r'[0-9a-f]{64}',value):
            raise ValueError('Invalid external source SHA: '+name)
    return doc

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
    for name in sorted(required_files() | set(args.file)):
        path=regular_source(name)
        files[name] = sha(path)
    for name in ('PREREGISTRATION.md', 'plan.json', 'contract.json'):
        path = HERE/name
        committed = git('show', design + ':' + rel(path))
        if hashlib.sha256(committed).hexdigest() != sha(path):
            raise ValueError('Design drift: ' + name)
    external = {}
    for name in required_external_paths()+args.external_file:
        original = Path(name).expanduser().absolute()
        if not original.is_file() or original.is_symlink():
            raise ValueError('Expected regular external source: ' + str(original))
        path=original.resolve()
        external[str(path)] = sha(path)
    doc = {'schema_version':1, 'design_commit':design,
           'generated_at':datetime.now().astimezone().isoformat(timespec='seconds'),
           'files':dict(sorted(files.items())), 'external_files':dict(sorted(external.items())),
           'policy':'Benchmark runtime sources/configs and declared external build identities pinned before planned live requests; outputs are append-only new paths.',
           'exhaustive_transitive_product_dependencies_pinned':False,
           'live_doc_drift':[]}
    validate_manifest(doc)
    create(MANIFEST, doc)
    print(json.dumps({'manifest':rel(MANIFEST),'sha256':sha(MANIFEST),'files':len(files),'external_files':len(external)},ensure_ascii=False))

def bind(args):
    seal = resolve_commit(args.seal)
    manifest_bytes = git('show', seal + ':' + rel(MANIFEST))
    if manifest_bytes != MANIFEST.read_bytes():
        raise ValueError('Manifest differs from sealed blob')
    doc = validate_manifest(json.loads(manifest_bytes))
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
