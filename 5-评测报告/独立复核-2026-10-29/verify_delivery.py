#!/usr/bin/env python3
"""Read-only delivery checks. No model calls, package installs or private fallback."""
from __future__ import annotations
import argparse
import ast
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

SCOPES = (
    '1-评测方案/机制实验-2026-10-29',
    '3-表现现场/r20261029-mechanism',
    '4-打分细则/可信冻结-2026-10-29',
    '5-评测报告/可信冻结-2026-10-29',
    '5-评测报告/独立复核-2026-10-29',
)
DOCS = ('README.md', '5-评测报告/README.md', '5-评测报告/阶段报告-v4.0.md')
SECRET = re.compile(rb'(?:sk-[A-Za-z0-9_-]{24,}|Bearer[ \t]+[A-Za-z0-9._-]{24,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)')
LINK = re.compile(r'\]\(<?([^\n>]+?)>?\)')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=Path('.'))
    ap.add_argument('--baseline', type=Path, help='Override the public protected-baseline.json captured before this delivery.')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    root = args.root.resolve()
    checks = []
    def check(name, ok, detail):
        checks.append({'id': name, 'pass': bool(ok), 'detail': detail})
    baseline = args.baseline or root / '5-评测报告/独立复核-2026-10-29/protected-baseline.json'
    if baseline.is_file():
        before = json.loads(baseline.read_text())
        bad = [p for p, h in before['files'].items() if not (root / p).is_file() or sha(root / p) != h]
        check('protected_history_byte_identical', not bad, {'files_checked': len(before['files']), 'changed': bad})
    else:
        check('protected_history_byte_identical', False, {'error': 'baseline missing'})
    files = sorted({p for scope in SCOPES for p in (root / scope).rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    docs = [p for p in files if p.suffix == '.md'] + [root / p for p in DOCS if (root / p).is_file()]
    missing = []
    n_links = 0
    for p in docs:
        for line, text in enumerate(p.read_text(encoding='utf-8').splitlines(), 1):
            for target in LINK.findall(text):
                u = urlsplit(target)
                if u.scheme or u.netloc or not u.path or '`' in u.path:
                    continue
                n_links += 1
                resolved = (p.parent / unquote(u.path)).resolve()
                if not resolved.exists():
                    missing.append({'file': str(p.relative_to(root)), 'line': line, 'target': target})
    check('local_markdown_targets_exist', not missing, {'links_checked': n_links, 'missing': missing})
    syntax_errors = []
    for p in files:
        if p.suffix == '.py':
            try:
                ast.parse(p.read_text(encoding='utf-8'), filename=str(p))
            except (SyntaxError, UnicodeError) as exc:
                syntax_errors.append({'file': str(p.relative_to(root)), 'error': str(exc)})
    check('new_python_syntax', not syntax_errors, {'files_checked': sum(p.suffix == '.py' for p in files), 'errors': syntax_errors})
    secret_files = [str(p.relative_to(root)) for p in files if SECRET.search(p.read_bytes())]
    check('no_obvious_literal_credentials', not secret_files, {'files_checked': len(files), 'flagged_paths_only': secret_files, 'scope': 'literal credential patterns, not proof of comprehensive sanitization'})
    git_verification = 'not_available_in_public_snapshot; protected baseline is checked directly'
    if (root / '.git').exists():
        paths = subprocess.run(['git', 'diff', '--name-only', '--', 'CHANGELOG.md', '2-用例', '反馈'], cwd=root, capture_output=True, text=True)
        check('no_protected_git_diff', paths.returncode == 0 and not paths.stdout.strip(), {'exit_code': paths.returncode, 'changed_paths': paths.stdout.splitlines()})
        git_verification = 'executed'
    result = {'schema_version': 1, 'category': 'offline_recompute', 'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'passed': all(c['pass'] for c in checks), 'checks': checks, 'git_verification': git_verification, 'new_product_runs': 0}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': result['passed'], 'checks': len(checks), 'output': str(args.output)}, ensure_ascii=False))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
