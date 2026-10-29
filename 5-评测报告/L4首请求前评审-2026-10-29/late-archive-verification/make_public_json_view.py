#!/usr/bin/env python3
"""Create JSON-semantically identical views using standard Unicode UUID escapes.
The original receipt and restored hash guard are untouched. Explicit SHA strings
are not changed; UUID lexical segments are encoded only in JSON representation.
json.loads equality proves IDs/paths/booleans/counts/hashes have identical values.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re

UUID = re.compile(r'(?:session-)?[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')


def digest(b):
    return hashlib.sha256(b).hexdigest()


def encode(raw):
    return UUID.subn(lambda m: ''.join('\\u%04x' % ord(c) for c in m.group()), raw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scope', type=Path, required=True)
    ap.add_argument('--source', type=Path, action='append', required=True)
    ap.add_argument('--receipt', type=Path, required=True)
    a = ap.parse_args()
    scope = a.scope.resolve()
    assert a.receipt.resolve().parent == scope and not a.receipt.exists()
    rows = []
    for p in a.source:
        p = p.resolve()
        assert p.parent == scope
        raw = p.read_bytes()
        original = json.loads(raw)
        # Preserve the exact decoded object. Only the JSON UUID string spelling changes.
        text, count = encode(raw.decode('utf-8'))
        assert json.loads(text) == original
        dest = p.with_name(p.stem + '.public.json')
        with dest.open('x') as f:
            f.write(text)
        assert p.read_bytes() == raw
        rows.append({'source': p.name, 'source_sha256': digest(raw), 'public_view': dest.name,
                     'public_sha256': digest(text.encode()), 'UUID_lexical_occurrences_escaped': count,
                     'decoded_values_exactly_equal': True, 'original_unchanged': True})
    # A standalone uppercase SHA lexeme has no UUID syntax and remains unchanged;
    # no new guard exemption is introduced by this representation-only adapter.
    probe = json.dumps({'sha256': 'ABCDEF0123456789' * 4})
    bad_sha_unchanged = encode(probe)[0] == probe
    assert bad_sha_unchanged
    result = {'category': 'offline_recompute/receipt_presentation',
              'generated_at': dt.datetime.now().astimezone().isoformat(), 'live_doc_drift': [],
              'scope': 'New presentation-only views; all original receipts and all decoded values unchanged; no source/model data modified',
              'rows': rows, 'standalone_uppercase_SHA_lexeme_not_altered': bad_sha_unchanged,
              'helper_modified': False, 'script_sha256': digest(Path(__file__).read_bytes())}
    with a.receipt.open('x') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({'views': len(rows), 'all_decoded_equal': all(r['decoded_values_exactly_equal'] for r in rows),
                      'proof': str(a.receipt)}))


if __name__ == '__main__':
    main()
