"""Public synthetic examples of different SSE evidence gates; no captured data."""
import hashlib
import json

from sse import projection


def responses_frame(seq, kind, **fields):
    data = {'sequence_number': seq, 'type': kind, **fields}
    body = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    return f'event: {kind}\ndata: {body}\n\n'.encode('utf-8')


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def evaluate(frames, source_sha):
    raw = b''.join(frames)
    records = [json.loads(b.split(b'\ndata: ', 1)[1]) for b in frames]
    sequence = [r['sequence_number'] for r in records]
    # This self-check uses one synthetic text item, not a general item binder.
    prefix = 'response.output_text.'
    by_type = {suffix: [r for r in records if r['type'] == prefix + suffix]
               for suffix in ('delta', 'done')}
    completed = [r for r in records if r['type'] == 'response.completed']
    if len(by_type['done']) != 1 or not by_type['delta']:
        text = 'unknown'
    else:
        local = ''.join(r['delta'] for r in by_type['delta'])
        text = 'equal' if local == by_type['done'][0]['text'] else 'different'
    item_done = [r for r in records if r['type'] == 'response.output_item.done']
    if len(item_done) == len(completed) == 1:
        final_items = completed[0]['response']['output']
        item = 'equal' if final_items == [item_done[0]['item']] else 'different'
    else:
        item = 'unknown'
    return (projection(raw, 'codex')['closed'],
            bool(sequence) and sequence == list(range(len(sequence))),
            text, item, digest(raw) == source_sha)


def renumber_synthetic(frames):
    changed = []
    for i, b in enumerate(frames):
        start = b'\ndata: {"sequence_number":'
        a, field, remainder = b.partition(start)
        old, comma, rest = remainder.partition(b',')
        if not field or not comma or not old.isdigit():
            raise ValueError('unexpected synthetic layout')
        changed.append(a + field + str(i).encode('ascii') + comma + rest)
    return changed


def main():
    item = {'id': 'synthetic-item', 'type': 'message',
            'content': [{'type': 'output_text', 'text': 'alpha beta'}]}
    parent = {'item_id': item['id'], 'output_index': 0, 'content_index': 0}
    source = [
        responses_frame(0, 'response.created',
                        response={'id': 'synthetic', 'status': 'in_progress'}),
        responses_frame(1, 'response.output_text.delta', delta='alpha ', **parent),
        responses_frame(2, 'response.output_text.delta', delta='beta', **parent),
        responses_frame(3, 'response.output_text.done', text='alpha beta', **parent),
        responses_frame(4, 'response.output_item.done', item=item, output_index=0),
        responses_frame(5, 'response.completed',
                        response={'id': 'synthetic', 'status': 'completed', 'output': [item]}),
    ]
    known = digest(b''.join(source))
    no_delta = source[:2] + source[3:]
    cases = [
        ('original', source, (True, True, 'equal', 'equal', True)),
        ('terminal removed', source[:-1], (False, True, 'equal', 'unknown', False)),
        ('text delta removed', no_delta, (True, False, 'different', 'equal', False)),
        ('text delta removed + renumbered', renumber_synthetic(no_delta),
         (True, True, 'different', 'equal', False)),
        ('created removed + renumbered', renumber_synthetic(source[1:]),
         (True, True, 'equal', 'equal', False)),
        ('text done removed + renumbered', renumber_synthetic(source[:3] + source[4:]),
         (True, True, 'unknown', 'equal', False)),
        ('item done removed + renumbered', renumber_synthetic(source[:4] + source[5:]),
         (True, True, 'equal', 'unknown', False)),
    ]
    results = []
    for label, frames, expected in cases:
        row = evaluate(frames, known)
        if row != expected:
            raise SystemExit(f'{label}: {row!r} != {expected!r}')
        results.append((label, row))
    print('case | terminal | sequence | text-copy | item-copy | known original SHA')
    for label, row in results:
        print(' | '.join([label, *map(str, row)]))
    print('PASS: 7 synthetic expectations; no captured input')


if __name__ == '__main__':
    main()
