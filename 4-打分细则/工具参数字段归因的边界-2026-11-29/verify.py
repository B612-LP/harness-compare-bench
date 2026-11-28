"""Recompute the finite, synthetic observation model. No product or checker is run."""

from collections import Counter, defaultdict
from itertools import product
import json

STATES = 'ANS'
EDGES = ('W-L', 'L-H')
AXES = {
    'member_added': lambda a, b: a == 'A' and b != 'A',
    'member_removed': lambda a, b: a != 'A' and b == 'A',
    'string_entered': lambda a, b: a != 'S' and b == 'S',
    'string_left': lambda a, b: a == 'S' and b != 'S',
    'three_state_changed': lambda a, b: a != b,
}


def summarize(paths):
    out = {}
    for name, test in AXES.items():
        seen = [{edge for edge, a, b in zip(EDGES, row, row[1:]) if test(a, b)} for row in paths]
        out[name] = {
            'possible_counts': sorted({len(edges) for edges in seen}),
            'possible_edges': sorted(set.union(*seen)),
            'required_edges': sorted(set.intersection(*seen)),
            'event_required_somewhere': all(seen),
        }
    return out


def verify():
    masks = list(product((False, True), repeat=3))
    all_paths = [''.join(states) for states in product(STATES, repeat=3)]
    geometry = defaultdict(list)
    old_views = set()
    old_counts = Counter()
    for path, mask in product(all_paths, masks):
        geometry[''.join(state if visible else '?' for state, visible in zip(path, mask))].append(path)
        # This models the declared evidence dependencies, not the frozen parser.
        w, local, h = mask
        if not w:
            effective, status = '???', 'stream_unknown'
        elif not h:
            effective, status = path[0] + '??', 'history_binding_unknown'
        elif not local:
            effective, status = path[0] + '?' + path[2], 'local_binding_unknown'
        else:
            effective, status = path, 'three_layers_visible'
        old_views.add(effective)
        old_counts[status] += 1
    views = Counter(sum(c != '?' for c in p) for p in geometry)
    sample = {p: summarize(geometry[p]) for p in ('SAA', 'SSA', 'S?A', 'S?S', 'A?S')}
    if (dict(views) != {0: 1, 1: 9, 2: 27, 3: 27} or len(old_views) != 40
            or old_counts != {'stream_unknown': 108, 'history_binding_unknown': 54,
                              'local_binding_unknown': 27, 'three_layers_visible': 27}
            or sample['S?A']['member_removed']['possible_counts'] != [1]
            or sample['S?A']['member_removed']['required_edges']
            or sample['S?S']['three_state_changed']['possible_counts'] != [0, 2]
            or sample['SAA']['member_removed']['required_edges'] != ['W-L']
            or sample['SSA']['member_removed']['required_edges'] != ['L-H']):
        raise ValueError('synthetic transition invariants did not hold')
    return {
        'scope': 'synthetic enumerations only', 'full_paths': len(all_paths), 'masks_per_path': len(masks),
        'abstract_views': len(geometry), 'abstract_views_by_visible_layer_count': views,
        'declared_evidence_dependencies': {'cases': old_counts, 'distinct_views': len(old_views)},
        'examples': sample,
    }


if __name__ == '__main__':
    print(json.dumps(verify(), sort_keys=True, indent=2))
