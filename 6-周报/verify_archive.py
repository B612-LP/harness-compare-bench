#!/usr/bin/env python3
"""Check weekly archives and the non-adopted supplement; never send mail."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FIRST = dt.date(2026, 10, 17)
FIRST_SHA = 'd35c22ad2e6473621db4ed4516f89032d2704c7954443c5cd949efeabdddd7df'
CHECKS = []


def check(name, passed, detail=None):
    CHECKS.append({'test': name, 'pass': bool(passed), 'detail': detail})
    print(('PASS ' if passed else 'FAIL ') + name)


def load(p):
    return json.loads(p.read_text(encoding='utf-8'))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--through', type=dt.date.fromisoformat, required=True)
    args = ap.parse_args()
    output = HERE / ('归档核对-' + args.through.isoformat() + '.json')
    expected = []
    day = FIRST
    while day <= args.through:
        expected.append(day)
        day += dt.timedelta(days=7)
    found = {}
    for p in HERE.glob('????-??-??-第*期.md'):
        m = re.fullmatch(r'(\d{4}-\d{2}-\d{2})-第(\d+)期\.md', p.name)
        if m:
            date = dt.date.fromisoformat(m[1])
            found[date] = (int(m[2]), p)
    check('every_due_week_has_its_own_file', bool(expected) and all(d in found for d in expected),
          {'expected': [d.isoformat() for d in expected], 'missing': [d.isoformat() for d in expected if d not in found]})
    check('period_numbers_are_continuous', all(d in found and found[d][0] == i for i, d in enumerate(expected, 1)))
    check('first_sent_week_is_byte_preserved', hashlib.sha256((HERE / '2026-10-17-第1期.md').read_bytes()).hexdigest() == FIRST_SHA)
    index = (HERE / 'README.md').read_text(encoding='utf-8')
    check('index_contains_every_due_week', all(d in found and found[d][1].name in index for d in expected))
    weekly = HERE / '2026-10-24-第2期.md'
    text = weekly.read_text(encoding='utf-8')
    parts = text.split('\n---\n')
    check('mail_body_has_unambiguous_copy_boundaries', len(parts) == 3)
    body = parts[1] if len(parts) == 3 else ''
    visible = re.sub(r'\[([^\]]+)\]\(<?[^\n>]+>?\)', r'\1', body)
    visible = re.sub(r'[*#`\s]', '', visible)
    check('current_body_approximately_1500_characters', 1400 <= len(visible) <= 1600,
          {'characters_excluding_markdown_whitespace_and_link_urls': len(visible)})
    check('mail_not_falsely_marked_sent', '待本人确认并发送' in text and '不代表已经发出' in text)
    check('current_body_has_three_required_sections', all(x in body for x in ('本周项目进展', '本周难点突破', '下周计划'))
          and len(re.findall(r'^\d+\. ', body, re.M)) == 3)
    supp = ROOT / '5-评测报告/补充材料/2026-10-24'
    meta = load(supp / '附件清单.json')
    archive = supp / meta['file']
    check('supplement_sha256_matches_frozen_package', hashlib.sha256(archive.read_bytes()).hexdigest() == meta['sha256']
          == '8de47cf3017d069e867dcdbec1f62f0e50571da30b6c6422dd6fbd5b3493e559')
    with zipfile.ZipFile(archive) as z:
        check('supplement_zip_integrity', z.testzip() is None)
        manifest = json.loads(z.read('package-manifest.json'))
        check('all_53_payload_fingerprints_match', len(manifest['files']) == 53 and all(
              hashlib.sha256(z.read(p)).hexdigest() == h for p, h in manifest['files'].items()))
        a = json.loads(z.read('lead-acceptance.json'))
        p = json.loads(z.read('portability.json'))
        check('actual_acceptance_and_offline_receipts', a['passed'] == a['total'] == 19 and p['passed']
              and len(p['steps']) == 4 and all(x['exit_code'] == 0 for x in p['steps']))
    check('candidate_is_explicitly_not_adopted', meta['status'] == 'candidate-not-adopted'
          and meta['new_product_runs'] == 0 and not meta['historical_results_overwritten'])
    docs = [ROOT / 'README.md', HERE / 'README.md', weekly, ROOT / '5-评测报告/README.md', supp / 'README.md']
    issues = []
    links = 0
    for doc in docs:
        for raw in re.findall(r'\]\(<?([^\n>]+?)>?\)', doc.read_text(encoding='utf-8')):
            u = urlsplit(raw)
            if u.scheme:
                prefix = '/B612-LP/harness-compare-bench/'
                if u.netloc != 'github.com' or not u.path.startswith(prefix):
                    continue
                path = unquote(u.path[len(prefix):])
                if not (path.startswith('blob/main/') or path.startswith('tree/main/')):
                    continue
                target = ROOT / path.split('/', 2)[2]
            else:
                target = (doc.parent / unquote(u.path)).resolve() if u.path else doc
            links += 1
            # This receipt is written below; all other targets must already exist.
            if target != output and not target.exists():
                issues.append({'doc': doc.relative_to(ROOT).as_posix(), 'target': raw})
    check('weekly_and_supplement_links_exist', not issues, {'checked': links, 'issues': issues})
    receipt = {'through': args.through.isoformat(), 'passed': sum(c['pass'] for c in CHECKS),
               'total': len(CHECKS), 'checks': CHECKS, 'mail_sent_by_script': False}
    output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': receipt['passed'], 'total': receipt['total']}, ensure_ascii=False))
    return 0 if receipt['passed'] == receipt['total'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
