#!/usr/bin/env python3
"""Validate a public projection's shape and published byte digest, not its private originals."""
import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_SHA256 = '8ac99a17c9110256856a314159d68e0d386cc37095d4cc39f5dd03f0110e421f'
KINDS = {'correction', 'grading_regression', 'self_test', 'offline_recompute'}


def verify(path):
    result = {'public_summary': 'PUBLIC_SUMMARY_INVALID',
              'private_originals': 'PRIVATE_UNAVAILABLE', 'all_originals_verified': False}
    try:
        raw = Path(path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA256:
            raise ValueError('public projection digest mismatch')
        obj = json.loads(raw)
        if set(obj) != {'schema', 'scope', 'event_count', 'kind_counts', 'originals', 'all_originals_verified'}:
            raise ValueError('invalid projection fields')
        counts = obj['kind_counts']
        if (obj['schema'] != 'public-ledger-summary-v1' or not isinstance(obj['scope'], str)
                or not isinstance(counts, dict) or set(counts) != KINDS
                or any(type(v) is not int or v < 0 for v in counts.values())
                or type(obj['event_count']) is not int or sum(counts.values()) != obj['event_count']
                or obj['originals'] != 'PRIVATE_UNAVAILABLE' or obj['all_originals_verified'] is not False):
            raise ValueError('invalid projection content')
        result['public_summary'] = 'PUBLIC_SUMMARY_VERIFIED'
    except (OSError, ValueError, TypeError, KeyError) as exc:
        result['error'] = str(exc)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('summary', nargs='?', default=str(Path(__file__).with_name('public-ledger-summary-v1.json')))
    args = parser.parse_args()
    report = verify(args.summary)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['public_summary'] == 'PUBLIC_SUMMARY_VERIFIED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
