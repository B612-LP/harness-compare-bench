#!/usr/bin/env python3
"""post-hoc 会话轨迹重扫 + meta 修正（对 10 场正式运行）。

背景缺陷：运行器曾把 agent.jsonl 写进证据目录，归档 rmtree 连带删除，导致
(a) 运行侧 stdout 事件流丢失；(b) meta.integrity 扫描空转（0 命中无效）。
本脚本以更完整的会话轨迹（Codex rollout jsonl / DSH session.v4.jsonl.zstd）重扫八类越界模式，
回填 integrity-rescan.json，并显式修正 meta.json（保留 correction 说明，不静默改写）。
"""
import json
import pathlib
import subprocess
import sys
import tempfile

R = pathlib.Path(__file__).resolve().parents[3]
B = pathlib.Path(__file__).resolve().parents[1]
CASES = ('bird-ca-schools-15', 'dabstep-payments-10', 'exercism-py-6', 'lcb-recent-hard-4', 'tb-cargo-plan')
PATTERNS = ["2-用例", "truth.json", "checker.py", "reference/", "solution/", "../",
            "~/Documents", "harness-compare-bench"]
CORRECTION = ("runner stdout stream (agent.jsonl) was lost by archiver defect r1030#1 (log written inside evidence dir, "
              "removed by rmtree before copy); original meta.integrity was vacuous; this file replaces it with a "
              "session-trajectory rescan over the same eight patterns; session files are contemporaneous product outputs.")


def iter_lines(path: pathlib.Path, zstd: bool):
    if zstd:
        p = subprocess.run(['zstd', '-dc', str(path)], capture_output=True, timeout=120)
        text = p.stdout.decode('utf-8', errors='replace')
    else:
        text = path.read_text(encoding='utf-8', errors='replace')
    for line in text.splitlines():
        yield line


def scan(session_files):
    hits = []
    n_lines = 0
    usage_events = 0
    for path, zstd in session_files:
        for i, line in enumerate(iter_lines(path, zstd)):
            n_lines += 1
            try:
                ev = json.loads(line)
            except Exception:
                continue
            blob = json.dumps(ev, ensure_ascii=False)
            if '"usage"' in blob or 'inputTokens' in blob or 'input_tokens' in blob:
                usage_events += 1
            for pat in PATTERNS:
                if pat in blob:
                    hits.append({'file': path.name, 'line': i + 1, 'pattern': pat, 'excerpt': blob[:300]})
                    break
            if len(hits) >= 20:
                return hits, n_lines, usage_events
    return hits, n_lines, usage_events


def main():
    summary = {}
    for product in ('codex', 'dsh'):
        for case in CASES:
            ev = B / 'runs' / ('%s__%s' % (product, case))
            sess = ev / 'agent-session'
            files = []
            for p in sorted(sess.iterdir()) if sess.is_dir() else []:
                files.append((p, p.suffix == '.zstd'))
            hits, n_lines, usage_events = scan(files)
            rescan = {'run': '%s__%s' % (product, case), 'patterns': PATTERNS,
                      'session_files': [{'name': p.name, 'bytes': p.stat().st_size, 'zstd': z} for p, z in files],
                      'lines_scanned': n_lines, 'usage_events_present': usage_events,
                      'violations': len(hits), 'evidence': hits,
                      'method': 'session-trajectory rescan (post-hoc)', 'correction': CORRECTION}
            (ev / 'integrity-rescan.json').write_text(json.dumps(rescan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            meta_p = ev / 'meta.json'
            meta = json.loads(meta_p.read_text(encoding='utf-8'))
            meta['integrity'] = {'violations': len(hits), 'patterns': PATTERNS,
                                 'basis': 'post-hoc session rescan; see integrity-rescan.json',
                                 'evidence': hits}
            meta['integrity_verdict'] = 'clean' if len(hits) == 0 else 'violation'
            meta['corrections'] = [{'id': 'r1030-archiver-log-loss', 'note': CORRECTION,
                                    'fixed_in': 'tools/lab.py archive() staging move; meta.integrity superseded by session rescan'}]
            meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            summary['%s__%s' % (product, case)] = {'violations': len(hits), 'lines': n_lines, 'usage_events': usage_events}
    (B / 'integrity-rescan-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    sys.exit(main())
