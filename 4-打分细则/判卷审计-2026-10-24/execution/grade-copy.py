#!/usr/bin/env python3
"""Preserve historical workspace: copy first, invoke a current checker on temp.

This prevents checker-owned writeback, NOT hostile same-UID code access. Use an
external OS sandbox with read-only evidence mounts for untrusted submissions.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('case', choices=('exercism-py-6', 'tb-cargo-plan'))
    ap.add_argument('workspace', type=Path)
    args = ap.parse_args()
    source = args.workspace.resolve(strict=True)
    if not source.is_dir():
        ap.error('workspace must be a directory')
    with tempfile.TemporaryDirectory(prefix='historical-grade-copy-') as td:
        run = Path(td) / 'workspace'
        shutil.copytree(source, run, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        proc = subprocess.run([sys.executable, '-B', str(ROOT/'2-用例'/args.case/'checker.py'), str(run), '--json'])
        return proc.returncode


if __name__ == '__main__':
    raise SystemExit(main())
