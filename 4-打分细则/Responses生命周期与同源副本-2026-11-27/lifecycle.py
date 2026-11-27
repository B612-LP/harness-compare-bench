"""Lifecycle admission for the pinned, observed Responses subset only."""
from collections import defaultdict

PHASES = {
    'response.created': 'in_progress',
    'response.in_progress': 'in_progress',
    'response.completed': 'completed',
}
FAMILIES = {
    'response.reasoning_text': ('reasoning', 'reasoning_text', 'text'),
    'response.output_text': ('message', 'output_text', 'text'),
    'response.function_call_arguments': ('function_call', None, 'arguments'),
}
PART_PREFIX = 'response.content_part.'
ITEM_PREFIX = 'response.output_item.'
EXTRA = {PART_PREFIX + x for x in ('added', 'done')}
ALLOWED = set(PHASES) | EXTRA | {ITEM_PREFIX + x for x in ('added', 'done')} | {
    base + '.' + suffix for base in FAMILIES for suffix in ('delta', 'done')
}


def nonnegative(x):
    return type(x) is int and x >= 0


def identity(item):
    shared = (item.get('id'), item.get('type'))
    if shared[1] == 'function_call':
        return shared + (item.get('name'), item.get('call_id'))
    if shared[1] == 'message':
        return shared + (item.get('role'), item.get('phase'))
    return shared


def valid_identity(item):
    fingerprint = identity(item)
    return fingerprint[1] in ('reasoning', 'message', 'function_call') and all(
        isinstance(x, str) and bool(x) for x in fingerprint
    )


def inspect(frames):
    migration, extension = set(), set()
    tags = [f.label for f in frames]
    if len(tags) < 3 or tags[:2] != list(PHASES)[:2] or tags[-1] != 'response.completed':
        migration.add('PHASE_ORDER_OR_MISSING')
    if any(tags.count(name) != 1 for name in PHASES):
        migration.add('PHASE_CARDINALITY')
    envelopes = []
    added, ended = {}, {}
    part_open, part_done = {}, {}
    piece, text_done = defaultdict(list), {}
    snapshot = None

    for f in frames:
        t, o = f.label, f.obj
        if t not in ALLOWED or not isinstance(o, dict) or o.get('type') != t:
            migration.add('LABEL_OR_TYPE')
            continue
        if t in PHASES:
            r = o.get('response')
            if not isinstance(r, dict):
                migration.add('ENVELOPE_SHAPE')
                continue
            fingerprint = tuple(r.get(k) for k in ('id', 'model', 'object', 'created_at'))
            if not all(isinstance(x, str) and x for x in fingerprint[:3]) or not nonnegative(fingerprint[3]):
                migration.add('ENVELOPE_SHAPE')
            envelopes.append(fingerprint)
            if r.get('status') != PHASES[t] or r.get('error') is not None or r.get('incomplete_details') is not None:
                migration.add('ENVELOPE_STATUS')
            if t == 'response.completed':
                snapshot = r.get('output')
            elif r.get('output') != []:
                migration.add('EARLY_OUTPUT')
            continue
        if 'response' in o:
            migration.add('UNEXPECTED_ENVELOPE')
        n = o.get('output_index')
        if not nonnegative(n):
            migration.add('ITEM_INDEX')
            continue
        if t.startswith(ITEM_PREFIX):
            item = o.get('item')
            if not isinstance(item, dict) or not valid_identity(item):
                migration.add('ITEM_SHAPE')
                continue
            if t.endswith('.added'):
                if n in added or any(identity(x)[0] == item['id'] for x in added.values()):
                    migration.add('ITEM_DUPLICATE')
                if n != len(added) or item.get('status') != 'in_progress':
                    migration.add('ITEM_START')
                if (item.get('arguments') if item['type'] == 'function_call' else item.get('content')) != (
                    '' if item['type'] == 'function_call' else []
                ):
                    migration.add('ITEM_START_CONTENT')
                added[n] = item
            else:
                if n not in added or n in ended or identity(item) != identity(added[n]):
                    migration.add('ITEM_END_BINDING')
                if item.get('status') != 'completed':
                    migration.add('ITEM_END_STATUS')
                ended[n] = item
                if item['type'] == 'function_call':
                    k = ('response.function_call_arguments', n, None)
                    if k not in text_done or text_done[k] != item.get('arguments'):
                        extension.add('ITEM_ARGUMENT_COPY')
                else:
                    contents = item.get('content')
                    if not isinstance(contents, list) or not contents:
                        extension.add('ITEM_CONTENT_SHAPE')
                    elif {key[1] for key in part_done if key[0] == n} != set(range(len(contents))) or any(
                        part_done.get((n, i)) != x for i, x in enumerate(contents)
                    ):
                        extension.add('ITEM_PART_COPY')
            continue

        item = added.get(n)
        if item is None or n in ended or item['id'] != o.get('item_id'):
            migration.add('ITEM_NOT_OPEN_OR_WRONG_ID')
            continue
        if t in EXTRA:
            idx, part = o.get('content_index'), o.get('part')
            possible = [b for b, (k, p, _) in FAMILIES.items() if k == item['type'] and p is not None]
            if not nonnegative(idx) or not isinstance(part, dict) or not possible:
                extension.add('PART_SHAPE')
                continue
            base = possible[0]
            if part.get('type') != FAMILIES[base][1] or not isinstance(part.get('text'), str):
                extension.add('PART_SHAPE')
                continue
            pk, tk = (n, idx), (base, n, idx)
            if t.endswith('.added'):
                if pk in part_open or pk in part_done or part['text'] != '' or tk in piece or tk in text_done:
                    extension.add('PART_START')
                part_open[pk] = part
            else:
                if pk not in part_open or pk in part_done or tk not in text_done or text_done[tk] != part['text']:
                    extension.add('PART_END')
                part_done[pk] = part
            continue

        base, _, phase = t.rpartition('.')
        kind, part_type, field = FAMILIES[base]
        idx = o.get('content_index') if part_type else None
        value = o.get('delta' if phase == 'delta' else field)
        if item['type'] != kind or (part_type and not nonnegative(idx)) or not isinstance(value, str):
            migration.add('TEXT_SHAPE')
            continue
        tk = (base, n, idx)
        if part_type and ((n, idx) not in part_open or (n, idx) in part_done):
            extension.add('TEXT_OUTSIDE_PART')
        if tk in text_done:
            migration.add('TEXT_AFTER_DONE_OR_DUPLICATE')
        if phase == 'delta':
            piece[tk].append(value)
        else:
            text_done[tk] = value

    if len(envelopes) != 3 or not envelopes or any(x != envelopes[0] for x in envelopes):
        migration.add('ENVELOPE_DISAGREEMENT')
    if not ended or set(added) != set(ended):
        migration.add('ITEM_COVERAGE')
    if not isinstance(snapshot, list) or snapshot != [ended[i] for i in sorted(ended)]:
        migration.add('SNAPSHOT_DISAGREEMENT')
    if not text_done or piece.keys() != text_done.keys():
        migration.add('TEXT_KEY_COVERAGE')
    if any(not value or ''.join(piece.get(k, ())) != value for k, value in text_done.items()):
        migration.add('TEXT_DISAGREEMENT')
    if part_open.keys() != part_done.keys():
        extension.add('PART_COVERAGE')
    return sorted(migration), sorted(extension)
