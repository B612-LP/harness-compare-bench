#!/usr/bin/env python3
"""Current public release integrity only; not private-original or historical full-seal verification."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
sys.dont_write_bytecode = True

BASE = '38b0bcc64211a9a3bca36a8716b180c38460468c'
NAV = {'README.md', 'CHANGELOG.md', '1-评测方案/README.md', '3-表现现场/README.md',
       '4-打分细则/README.md', '5-评测报告/README.md'}
NEW_ROOTS = ('1-评测方案/原生来源链技术门-2026-11-04/',
             '3-表现现场/r20261104-native-provenance/',
             '3-表现现场/r20261104-read-detection/',
             '4-打分细则/盲态可判性审计-2026-11-04/',
             '5-评测报告/证据口径-2026-11-04/')
NEW_FILES = {'5-评测报告/竞品评测报告-v1.7.md', '5-评测报告/未知登记-2026-11-04-r7.json'}
HISTORICAL = {'5-评测报告/竞品评测报告-v1.6.md',
              '5-评测报告/未知登记-2026-11-03-r6.json',
              '4-打分细则/判卷器可信度协议-2026-11-03/judgment-test-pool.json',
              '5-评测报告/证据口径-2026-11-03/source-ledger.public-derived.json',
              '6-周报/2026-10-17-第1期.md', '6-周报/2026-10-24-第2期.md',
              '6-周报/2026-10-29-第3期增补-正式批次与机制复制.md',
              '6-周报/2026-10-31-第3期.md', '6-周报/2026-11-07-第4期.md',
              '6-周报/README.md', '6-周报/verify_archive.py',
              '6-周报/归档核对-2026-10-24.json', '6-周报/归档核对-2026-10-31.json'}
# Captured independently from immutable BASE Git blobs, not from caller-supplied manifest.
BASE_FINGERPRINTS = {
    '4-打分细则/判卷器可信度协议-2026-11-03/judgment-test-pool.json': (102451, '58e37b8fd2da8e74ac135f3a390aa98c9e2ee2ab4b4313bf7916e3aea04096cb'),
    '5-评测报告/未知登记-2026-11-03-r6.json': (18075, '26bbe2809f61d0c2c3c453c3c13a970e908cadd93ebcf077532b571d92f1aa7f'),
    '5-评测报告/竞品评测报告-v1.6.md': (76608, 'c9fb5f3de1192efaf54c06b91c13a885672dc27cc6501a48ceefbbbd970b7e9b'),
    '5-评测报告/证据口径-2026-11-03/source-ledger.public-derived.json': (1480387, '9784e714cd0134cece788fb3d67b080820dcbc0b95be29761123ab623deea420'),
    '6-周报/2026-10-17-第1期.md': (2202, 'd35c22ad2e6473621db4ed4516f89032d2704c7954443c5cd949efeabdddd7df'),
    '6-周报/2026-10-24-第2期.md': (5873, '08ae6a98daf2695332211ea63eda8c106c1097c5d48591ce7c2d82f4f3cd8be8'),
    '6-周报/2026-10-29-第3期增补-正式批次与机制复制.md': (3036, 'de57d6010aaa65d957d51a506f73d27d3db5efb3e5b90a90f12328009b1f61b9'),
    '6-周报/2026-10-31-第3期.md': (5021, '8f9d273a58debb7d5d67330e5420fb678a5c49312411e93ab0ea9f6cb0a84449'),
    '6-周报/2026-11-07-第4期.md': (6177, '6a96bb9de3f03240da1e356c2ddbf330db9d680a29b017430f8ecfd54dc035f0'),
    '6-周报/README.md': (2359, 'f1495bc2280099142f22a1e9d474b96842ec77c0ca158458c1c45d6233a86efb'),
    '6-周报/verify_archive.py': (5587, 'c13af42f1e5022fbc18a74780c3ec9a4055c710f559b58ccb46f5e5187aa0c3d'),
    '6-周报/归档核对-2026-10-24.json': (1827, '662314b574c5813a7b760d26201b6df72b3ef630661e8b3dcdd18751a649f7f1'),
    '6-周报/归档核对-2026-10-31.json': (1851, '66cbb888172145da59f98c37395a6c28b31879b9cbd3664d63569e43474f3503'),
}
CURRENT_MANIFEST = '5-评测报告/证据口径-2026-11-04/publication-manifest.json'


def require(value, message):
    if not value:
        raise ValueError(message)


def confined(root, name):
    require(isinstance(name, str) and name and '\\' not in name, 'Invalid relative path')
    p = Path(name)
    require(not p.is_absolute() and '..' not in p.parts and p.as_posix() == name, 'Path escape or alias')
    root = root.resolve()
    target = root / p
    for ancestor in (target, *target.parents):
        if ancestor == root:
            break
        require(not ancestor.is_symlink(), 'Symlink is not public byte custody')
    require(root in target.resolve().parents, 'Path escaped repository')
    require(target.is_file(), 'Missing declared file: ' + name)
    return target


def fingerprint(path):
    b = path.read_bytes()
    return {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}


def formal_section(text):
    return text.split('### 6.1 ', 1)[1].split('### 6.4 ', 1)[0]


def verify(repo, manifest):
    require(set(manifest) == {'schema', 'base_commit', 'evidence_level', 'files', 'historical_pins',
                             'historical_verification', 'human_verification', 'new_formal_rows'}, 'Unexpected manifest keys')
    require(manifest['schema'] == 'current-public-release-v1', 'Wrong manifest schema')
    require(manifest['base_commit'] == BASE, 'Wrong release baseline')
    require(manifest['evidence_level'] == 'public_derived_not_original_seal', 'Original seal is not verified')
    require(manifest['human_verification'] == 'pending', 'No human witness inferred')
    require(type(manifest['new_formal_rows']) is int and manifest['new_formal_rows'] == 0, 'No new formal admission')
    require(manifest['historical_verification'] == {
        'v1.6_complete_tree_commit': BASE,
        'v1.5_complete_tree_commit': '155a5ab8740c329a707b34fd9e5800a52ae83922',
        'current_navigation_is_not_historical_manifest_revalidation': True,
    }, 'Historical tree scope must remain explicit')
    files = manifest['files']
    pins = manifest['historical_pins']
    require(isinstance(files, dict) and isinstance(pins, dict), 'Expected named custody maps')
    require(set(pins) == HISTORICAL, 'Historical inputs must use exact published allowlist')
    require(CURRENT_MANIFEST not in files, 'Manifest cannot self-hash')
    disk = set()
    for prefix in NEW_ROOTS:
        directory = repo / prefix
        require(directory.is_dir() and not directory.is_symlink(), 'Missing or symlink package directory')
        for path in directory.rglob('*'):
            require(not path.is_symlink(), 'Symlink in package')
            if path.is_file():
                name = path.relative_to(repo).as_posix()
                if name != CURRENT_MANIFEST:
                    disk.add(name)
    declared_new = {name for name in files if any(name.startswith(x) for x in NEW_ROOTS)}
    require(disk == declared_new, 'Current package extra or missing files')
    require(NAV <= set(files), 'Missing current navigation custody')
    require(NEW_FILES <= set(files), 'Missing current report or unknown registry')
    require('5-评测报告/竞品评测报告-v1.6.md' in pins, 'Missing frozen report pin')
    require('5-评测报告/未知登记-2026-11-03-r6.json' in pins, 'Missing old unknown registry pin')
    require('4-打分细则/判卷器可信度协议-2026-11-03/judgment-test-pool.json' in pins, 'Missing untouched old pool pin')
    require('6-周报/2026-10-17-第1期.md' in pins, 'Missing first weekly original pin')
    checked = 0
    for name, record in files.items():
        require(name in NAV or name in NEW_FILES or any(name.startswith(x) for x in NEW_ROOTS), 'Unexpected publication scope')
        require(set(record) == {'bytes', 'sha256'}, 'Unexpected file record')
        require(type(record['bytes']) is int and record['bytes'] >= 0 and
                isinstance(record['sha256'], str) and re.fullmatch('[0-9a-f]{64}', record['sha256']), 'Invalid file fingerprint')
        require(fingerprint(confined(repo, name)) == record, 'Current file hash mismatch: ' + name)
        checked += 1
    for name, record in pins.items():
        require(set(record) == {'bytes', 'sha256'}, 'Unexpected historical record')
        n, digest = BASE_FINGERPRINTS[name]
        require(record == {'bytes': n, 'sha256': digest}, 'Historical fingerprint differs from immutable baseline: ' + name)
        require(fingerprint(confined(repo, name)) == record, 'Historical file changed: ' + name)
        checked += 1
    old = confined(repo, '5-评测报告/竞品评测报告-v1.6.md').read_text(encoding='utf-8')
    new = confined(repo, '5-评测报告/竞品评测报告-v1.7.md').read_text(encoding='utf-8')
    require(formal_section(old) == formal_section(new), 'Formal §6.1–6.3 must remain verbatim')
    old_unknown = json.loads(confined(repo, '5-评测报告/未知登记-2026-11-03-r6.json').read_text())
    new_unknown = json.loads(confined(repo, '5-评测报告/未知登记-2026-11-04-r7.json').read_text())
    require(isinstance(new_unknown['items'], list) and
            new_unknown['items'][:len(old_unknown['items'])] == old_unknown['items'], 'Old unknown items changed')
    item_ids = [item['id'] for item in new_unknown['items']]
    require(all(isinstance(x, str) and x for x in item_ids) and len(item_ids) == len(set(item_ids)), 'Duplicate or invalid unknown item IDs')
    require(new_unknown['scope_updates'][:len(old_unknown['scope_updates'])] == old_unknown['scope_updates'], 'Old scope update history changed')
    current = json.loads(confined(repo, '5-评测报告/证据口径-2026-11-04/current-scope.json').read_text())
    require('TODO' not in json.dumps(current, ensure_ascii=False), 'Unfinished current scope')
    for name in files:
        if name.endswith(('.md', '.json')):
            text = confined(repo, name).read_text(encoding='utf-8')
            require('LEAD_ONLY' not in text and 'TODO_MECHANISM' not in text, 'Unfilled release hook')
            require(not re.search(r'/U' + r'sers/[^/]+/', text), 'Private home path in public projection')
            require(not re.search(r'\bsk-[A-Za-z0-9_-]{16,}', text), 'Possible credential in public projection')
    return {'schema': 'current-public-release-check-v1', 'ok': True,
            'checked_current_files': len(files), 'checked_historical_pins': len(pins),
            'checked_file_fingerprints': checked, 'formal_section_verbatim': True,
            'old_unknown_history_retained': True, 'new_formal_rows': 0,
            'scope': 'declared public byte inventory and limited invariants; not semantic truth or original seal',
            'human_verification': 'pending', 'historical_full_verify_on_current_tree_claimed': False}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument('--manifest', type=Path, default=Path(__file__).with_name('publication-manifest.json'))
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    try:
        result = verify(a.repo_root, json.loads(a.manifest.read_text(encoding='utf-8')))
        text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
        if a.output is not None:
            with a.output.open('x', encoding='utf-8') as f:
                f.write(text)
        print(text, end='')
        return 0
    except Exception as exc:
        print('current release verification failed: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
