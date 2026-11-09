#!/usr/bin/env python3
"""Rebuild three bounded, non-scoring evidence checks; never run a historical checker."""
import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import types

PACKAGE = '4-打分细则/判据边界复核-2026-11-05/'
REPORT = '5-评测报告/竞品评测报告-v1.10.md'
OLD_REPORT = '5-评测报告/竞品评测报告-v1.9.md'
FROZEN_V1_8 = '5-评测报告/竞品评测报告-v1.8.md'
HELPERS = {
    'lcb_visibility.py': 'f5c3dbf85b6cc1f993a116341d362d3d05f5a9ae2def5971e1cfaedc761d3093',
    'dab_q49.py': '2812c40166cb001adb3dd4a66852e38c4a42a208acee3b77eb8a7bedaba587f8',
    'cargo_heading.py': 'fc5d543c4da0dfa4a95eca297772403529ed672f4e4a5ad06b7d27a61f617e88',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_file(root, relative):
    require(type(relative) is str and '\\' not in relative, 'unsafe package path')
    path = PurePosixPath(relative)
    require(bool(relative) and not path.is_absolute() and path.as_posix() == relative
            and all(p not in ('.', '..') for p in path.parts), 'unsafe package path')
    root = Path(root).resolve(strict=True)
    target = root
    for part in path.parts:
        target /= part
        require(not target.is_symlink(), 'symlink package path: ' + relative)
    require(target.is_file() and root in target.resolve().parents, 'missing/outside package file: ' + relative)
    return target


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key: ' + key)
            result[key] = value
        return result

    def reject(value):
        raise ValueError('nonfinite JSON number: ' + value)

    value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=reject)

    def walk(item):
        if type(item) is float:
            require(math.isfinite(item), 'nonfinite JSON number')
        elif type(item) is list:
            for child in item:
                walk(child)
        elif type(item) is dict:
            for child in item.values():
                walk(child)
    walk(value)
    return value


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def load_reviewed_helpers(root):
    """Compile the exact bytes just hashed, not a loader's possible cached bytecode."""
    modules = {}
    for filename, expected in HELPERS.items():
        path = safe_file(root, PACKAGE + filename)
        raw = path.read_bytes()
        require(hashlib.sha256(raw).hexdigest() == expected, 'reviewed helper SHA mismatch: ' + filename)
        module = types.ModuleType('criteria_boundary_' + filename.removesuffix('.py'))
        module.__file__ = str(path)
        exec(compile(raw, str(path), 'exec'), module.__dict__)
        modules[filename] = module
    return modules


def formal_tables(text):
    require(sum(line.startswith('## 3.') for line in text.splitlines()) == 1
            and sum(line.startswith('## 4.') for line in text.splitlines()) == 1,
            'report table section boundary')
    section = text.split('## 3.', 1)[1].split('## 4.', 1)[0]
    return [[cell.strip() for cell in line.split('|')[1:-1]]
            for line in section.splitlines() if line.startswith('|')]


def derive(root):
    root = Path(root).resolve(strict=True)
    modules = load_reviewed_helpers(root)
    views = {key.removesuffix('.py'): module.derive(root) for key, module in modules.items()}
    source_union = {}
    for filename, module in modules.items():
        pins = module.PINS if filename == 'dab_q49.py' else module.SOURCE_SHA256
        for path, expected in pins.items():
            require(path not in source_union or source_union[path] == expected, 'conflicting source pins')
            source_union[path] = expected
    legacy = safe_file(root, FROZEN_V1_8).read_bytes()
    old = safe_file(root, OLD_REPORT).read_bytes()
    current = safe_file(root, REPORT).read_bytes()
    require(formal_tables(legacy.decode('utf-8')) == formal_tables(old.decode('utf-8')),
            'formal report tables differ between frozen v1.8 and v1.9')
    require(formal_tables(old.decode('utf-8')) == formal_tables(current.decode('utf-8')),
            'formal report tables differ between frozen v1.9 and current v1.10')
    require(bool(formal_tables(current.decode('utf-8'))), 'formal report tables absent')
    for filename, expected in HELPERS.items():
        require(hashlib.sha256(safe_file(root, PACKAGE + filename).read_bytes()).hexdigest() == expected,
                'reviewed helper changed during derive: ' + filename)
    for path, expected in source_union.items():
        require(hashlib.sha256(safe_file(root, path).read_bytes()).hexdigest() == expected,
                'source changed during derive: ' + path)
    require(safe_file(root, REPORT).read_bytes() == current, 'current report changed during derive')
    return {
        'schema': 'criteria-evidence-boundaries-20261105-v1',
        'new_product_or_model_runs': 0, 'new_formal_admissions': 0,
        'historical_regrade': False, 'q49_gold_or_attribution_changed': False,
        'cargo_diagnostic_changes_old_scoring': False,
        'reviewed_helper_sha256': dict(HELPERS),
        'frozen_source_sha256': dict(sorted(source_union.items())),
        'report_alignment': {
            'path': REPORT, 'sha256': hashlib.sha256(current).hexdigest(),
            'previous_report_path': OLD_REPORT,
            'previous_report_sha256': hashlib.sha256(old).hexdigest(),
            'frozen_legacy_path': FROZEN_V1_8,
            'frozen_legacy_sha256': hashlib.sha256(legacy).hexdigest(),
            'formal_table_cells_and_reasons_equal': True,
        },
        'checks': views,
        'limits': [
            'Static public-source consistency, not historical raw authentication or third-party attestation.',
            'Canonical inputs and public audit visibility do not establish every historical packaging or actual read.',
            'The DAB aggregate corrects a count-based explanation, not the B.BE gold or ability attribution.',
            'Cargo examples are synthetic supplementary math; no old evaluate, product plan or candidate was executed.',
            'Source SHA authority is separate from pure-function synthetic semantic tests; neither proves a sandbox.',
        ],
    }


def verify(root):
    expected = derive(root)
    recorded = strict_json(safe_file(root, PACKAGE + 'audit.json').read_bytes())
    require(canonical(expected) == canonical(recorded), 'derived audit mismatch')
    return {'ok': True, 'scope': 'three non-scoring evidence boundaries',
            'frozen_sources': len(expected['frozen_source_sha256']),
            'new_product_or_model_runs': 0, 'new_formal_admissions': 0,
            'historical_regrade': False, 'private_originals_authenticated': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--rebuild', action='store_true', help='print a freshly derived view; never write files')
    args = parser.parse_args()
    try:
        result = derive(args.root) if args.rebuild else verify(args.root)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
    except (ValueError, OSError, UnicodeError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
