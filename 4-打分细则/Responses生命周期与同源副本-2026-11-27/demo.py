"""Synthetic projection controls; never read or execute a capture or solution."""
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json

from lifecycle import inspect


@dataclass(frozen=True)
class Frame:
    label: str
    obj: dict


def require(ok, why):
    if not ok:
        raise ValueError(why)


def fixture(text='synthetic text'):
    response = dict(id='synthetic-response', model='synthetic-model', object='response',
                    created_at=1, status='in_progress', error=None, incomplete_details=None, output=[])
    item = dict(id='synthetic-item', type='message', role='assistant', phase='final_answer',
                status='in_progress', content=[])
    part = dict(type='output_text', text=text)
    final_item = dict(item, status='completed', content=[part])
    index = {'output_index': 0, 'content_index': 0, 'item_id': item['id']}
    return number([
        Frame('response.created', {'response': response}),
        Frame('response.in_progress', {'response': response}),
        Frame('response.output_item.added', {'output_index': 0, 'item': item}),
        Frame('response.content_part.added', dict(index, part=dict(part, text=''))),
        Frame('response.output_text.delta', dict(index, delta=text)),
        Frame('response.output_text.done', dict(index, text=text)),
        Frame('response.content_part.done', dict(index, part=part)),
        Frame('response.output_item.done', {'output_index': 0, 'item': final_item}),
        Frame('response.completed', {'response': dict(response, status='completed', output=[final_item])}),
    ])


def number(frames):
    # For this synthetic, parsed-object demo only; not a raw-byte rewriter.
    return [Frame(f.label, dict(deepcopy(f.obj), type=f.label, sequence_number=i))
            for i, f in enumerate(frames)]


def digest(frames):
    # Hash this synthetic wire representation, not canonical JSON or a provider capture.
    body = ''.join(f'event: {f.label}\ndata: '
                   + json.dumps(f.obj, ensure_ascii=False, separators=(',', ':')) + '\n\n'
                   for f in frames).encode('utf-8')
    return hashlib.sha256(body).hexdigest()


def main():
    base = fixture()
    names = ('baseline', 'sync_replace', 'sync_empty')
    synthetic = [base, fixture('new synthetic text'), fixture('')]
    result = {}
    for name, frames in zip(names, synthetic):
        m, e = inspect(frames)
        result[name] = dict(migration=m, extension=e, same_original=digest(frames) == digest(base))
    require(result['baseline'] == dict(migration=[], extension=[], same_original=True), 'baseline')
    require(result['sync_replace'] == dict(migration=[], extension=[], same_original=False), 'same source copies')
    require(result['sync_empty'] == dict(migration=['TEXT_DISAGREEMENT'], extension=[], same_original=False),
            'finite nonempty support gate')
    by_gate = Counter()
    for i, frame in enumerate(base):
        mutated = number(base[:i] + base[i + 1:])
        m, e = inspect(mutated)
        expected = 'part_only' if frame.label.startswith('response.content_part.') else 'migration'
        got = 'migration' if m else ('part_only' if e else 'pass')
        require(got == expected and digest(mutated) != digest(base), 'wrong synthetic deletion: ' + frame.label)
        by_gate[got] += 1
    require(by_gate == {'migration': 7, 'part_only': 2}, 'coverage')
    print(json.dumps({'synthetic_baseline_frames': len(base), 'delete_one': dict(by_gate),
                      'content_controls': result}, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
