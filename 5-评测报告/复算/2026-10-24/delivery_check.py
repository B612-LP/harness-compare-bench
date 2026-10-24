#!/usr/bin/env python3
"""Offline final publication checks. Prints identifiers, never secret values."""
from __future__ import annotations
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    errors = []
    checks = []
    ledger = load(REPO / '5-评测报告/运行总账-2026-10-24.json')
    runs = ledger['runs']
    counter = Counter(r['adjudication'] for r in runs)
    checks.append({'test': 'ledger_counts', 'pass': len(runs) == 62 and counter == {'V': 54, 'X': 8}
                   and ledger['summary']['F_raw'] == 22 and ledger['summary']['U'] == 0})
    checks.append({'test': 'ledger_unique', 'pass': len({r['run_id'] for r in runs}) == 62})
    unknown = load(REPO / '5-评测报告/未知登记.json')
    counts = Counter(r['status'] for r in unknown['unknowns'])
    checks.append({'test': 'unknown_counts_and_conditions', 'pass': dict(counts) == unknown['counts']
                   and all(r.get('next_step') and r.get('stop_condition') for r in unknown['unknowns'])})
    acceptance = load(HERE / 'validation.json')
    checks.append({'test': 'lead_independent_31', 'pass': acceptance['passed'] == acceptance['total'] == 31})
    docs = [REPO / name for name in (
        'README.md', '1-评测方案/2026-10-24-阶段二方案.md', '2-用例/README.md',
        '3-表现现场/README.md', '4-打分细则/README.md', '4-打分细则/打分表.md',
        '4-打分细则/归因定责.md', '4-打分细则/判卷审计-2026-10-24/README.md',
        '4-打分细则/判卷审计-2026-10-24/numeric/README.md',
        '4-打分细则/判卷审计-2026-10-24/execution/README.md',
        '5-评测报告/README.md', '5-评测报告/阶段报告-v2.0.md',
        '5-评测报告/运行总账-2026-10-24.md', '6-周报/2026-10-24-第2期.md')]
    docs += [HERE / 'README.md', REPO / '反馈/2026-10-21-第一轮/验收条款-公开版.md']
    tracked = {REPO / p for p in subprocess.check_output(
        ['git', 'ls-files', '-z'], cwd=str(REPO)).decode().split('\0') if p}
    link_count = 0
    for path in docs:
        text = path.read_text(encoding='utf-8')
        for raw in re.findall(r'\]\(<?([^\n>]+?)>?\)', text):
            target = raw.strip()
            if urlsplit(target).scheme or target.startswith('#'):
                continue
            target = unquote(target.split('#', 1)[0])
            resolved = (path.parent / target).resolve()
            link_count += 1
            if not resolved.exists():
                errors.append({'kind': 'missing_link', 'path': path.relative_to(REPO).as_posix(), 'target': target})
            elif resolved.is_file() and resolved not in tracked:
                errors.append({'kind': 'link_not_published', 'path': path.relative_to(REPO).as_posix(), 'target': target})
    checks.append({'test': 'current_document_links', 'pass': not errors, 'checked': link_count})
    weekly = (REPO / '6-周报/2026-10-24-第2期.md').read_text()
    checks.append({'test': 'mail_not_claimed_sent', 'pass': '待本人确认并发送' in weekly and '已经发出' in weekly})

    candidates = {REPO / p for p in subprocess.check_output(
        ['git', 'ls-files', '-co', '--exclude-standard', '-z'], cwd=str(REPO)).decode().split('\0') if p}
    patterns = {
        'api_key': re.compile(r'(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{20,}'),
        'github_token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,})'),
        'private_key': re.compile(r'-----BEGIN (?:OPENSSH |RSA |EC |DSA )?PRIVATE KEY-----'),
        'bearer_literal': re.compile(r'(?i)Bearer\s+[A-Za-z0-9_-]{30,}(?:\.[A-Za-z0-9_-]+){0,2}'),
    }
    secret_hits = []
    compressed_checked = 0
    for path in sorted(candidates):
        if not path.is_file(): continue
        if path.stat().st_size >= 100_000_000:
            errors.append({'kind': 'oversized_file', 'path': path.relative_to(REPO).as_posix()})
        try:
            if path.suffix == '.zstd':
                p = subprocess.run(['zstd', '-dc', str(path)], capture_output=True, timeout=60)
                if p.returncode:
                    errors.append({'kind': 'unreadable_zstd', 'path': path.relative_to(REPO).as_posix()})
                    continue
                text = p.stdout.decode('utf-8'); compressed_checked += 1
            else:
                text = path.read_text(encoding='utf-8')
        except (UnicodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            for kind, pattern in patterns.items():
                if pattern.search(line):
                    secret_hits.append({'path': path.relative_to(REPO).as_posix(), 'line': number, 'kind': kind})
    checks.append({'test': 'no_credential_pattern_hits', 'pass': not secret_hits,
                   'files_considered': len(candidates), 'compressed_sessions_checked': compressed_checked})
    errors += secret_hits
    # Parse current implementation/audit Python, not intentionally broken task submissions.
    python_paths = list(HERE.glob('*.py'))
    for case in ('bird-ca-schools-15', 'dabstep-payments-10', 'exercism-py-6', 'tb-cargo-plan'):
        python_paths += list((REPO / '2-用例' / case).glob('*.py'))
    for path in python_paths:
        try: ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        except SyntaxError:
            errors.append({'kind': 'syntax_error', 'path': path.relative_to(REPO).as_posix()})
    checks.append({'test': 'current_python_syntax', 'pass': not any(r['kind'] == 'syntax_error' for r in errors), 'files': len(python_paths)})
    whitespace = subprocess.run(['git', 'diff', '--cached', '--check'], cwd=str(REPO), capture_output=True, text=True)
    warning_files = {m.group(1) for line in whitespace.stdout.splitlines()
                     if (m := re.match(r'(.+?):\d+: (?:trailing whitespace|new blank line at EOF|space before tab)', line))}
    preserved_sources = {
        '2-用例/dabstep-payments-10/inputs/manual.md',
        '3-表现现场/r1024-probe-区分度/cases/dabstep-dev10/inputs/manual.md',
        '3-表现现场/r1024-probe-区分度/cases/dabstep-dev10/scorer.py',
        '3-表现现场/r1024-probe-区分度/cases/polyglot-py3/inputs/exercises/forth/.docs/instructions.append.md',
        '3-表现现场/r1024-probe-区分度/polyglot-py3__codex/inputs/exercises/forth/.docs/instructions.append.md',
        '3-表现现场/r1024-probe-区分度/polyglot-py3__dsh/inputs/exercises/forth/.docs/instructions.append.md',
        '3-表现现场/r1025-candidates/cases/dabstep-payments-10/inputs/manual.md',
        '3-表现现场/r1027-isolated/README.md',
    }
    unexpected_whitespace = sorted(warning_files - preserved_sources)
    checks.append({'test': 'edited_source_whitespace', 'pass': whitespace.returncode in (0, 2) and not unexpected_whitespace,
                   'preserved_original_files_with_warnings': sorted(warning_files & preserved_sources),
                   'unexpected_warning_files': unexpected_whitespace,
                   'note': 'Do not normalize original datasets/official scorer/historical evidence merely to remove whitespace.'})
    output = {'date': '2026-10-24', 'passed': sum(r['pass'] for r in checks), 'total': len(checks),
              'checks': checks, 'issues': errors,
              'secret_scan_scope': 'Pattern scan of publishable text and decompressed DSH sessions; not a proof of absence of every possible secret.'}
    (HERE / 'delivery-check.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if not errors and output['passed'] == output['total'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
