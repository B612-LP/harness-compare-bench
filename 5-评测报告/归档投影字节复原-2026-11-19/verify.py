"""Mechanical check for an aggregate, not a trace or authenticity verifier."""
import copy
import json
from pathlib import Path
import sys


FIELDS = {
    'historical_pairs', 'archived_slots', 'training_pairs', 'holdout_pairs', 'new_statistical_trials',
    'training_exact', 'frozen_candidate', 'holdout_slots', 'known', 'strict_value_exact', 'received_order_exact',
    'frozen_original_byte_exact', 'candidate_original_byte_exact', 'candidate_original_length_equal',
    'literal_and_received_order_compact_agree', 'source_anchors_agree', 'controls', 'postseal_path_snapshot',
}
CONTROLS = {'clone_bytes_differ', 'clone_values_equal', 'clone_insertion_order_equal', 'clone_reprojection_exact',
            'altered_bytes_differ', 'altered_same_length', 'altered_values_differ', 'altered_shape_equal'}
SNAPSHOT = {'distinct_inodes', 'cross_role_inode_intersection', 'extra_hardlinks_observed'}


def kv(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError
        out[k] = v
    return out


def need(v):
    if not v:
        raise ValueError


def iscount(x):
    return type(x) is int and x >= 0


def verify(d):
    need(type(d) is dict and set(d) == FIELDS)
    arrays = ('training_exact', 'candidate_original_byte_exact', 'candidate_original_length_equal', 'source_anchors_agree')
    scalars = FIELDS - set(arrays) - {'controls', 'postseal_path_snapshot'}
    need(all(iscount(d[k]) for k in scalars))
    need(all(type(d[k]) is list and all(map(iscount, d[k])) for k in arrays))
    need(len(d['source_anchors_agree']) == 2 and all(len(d[k]) == 9 for k in arrays[:-1]))
    need(d['historical_pairs'] == 6 and d['archived_slots'] == 2 * d['historical_pairs'] and d['new_statistical_trials'] == 0)
    need(d['training_pairs'] == 1 and d['holdout_pairs'] + d['training_pairs'] == d['historical_pairs'])
    need(d['holdout_slots'] == 2 * d['holdout_pairs'] and d['known'] == d['holdout_slots'] == d['strict_value_exact'] == d['received_order_exact'])
    h = d['holdout_slots']
    need(d['source_anchors_agree'] == [2 * d['archived_slots']] * 2)
    need(d['training_exact'] == [2, 2] + [0] * 7 and d['frozen_candidate'] == 1)
    need(d['candidate_original_byte_exact'] == [h, h] + [0] * 7)
    need(d['candidate_original_length_equal'] == [h, h, 0, 0, 0, h, 0, 0, 0])
    need(d['frozen_original_byte_exact'] == d['literal_and_received_order_compact_agree'] == h)
    need(type(d['controls']) is dict and set(d['controls']) == CONTROLS and all(v is True for v in d['controls'].values()))
    n = d['postseal_path_snapshot']
    need(type(n) is dict and set(n) == SNAPSHOT and all(map(iscount, n.values())))
    need(n['distinct_inodes'] == 2 * d['archived_slots'] and n['cross_role_inode_intersection'] == n['extra_hardlinks_observed'] == 0)


def main():
    need(sys.argv[1:] in ([], ['--self-test']))
    p = Path(__file__).with_name('evidence.json')
    need(p.is_file() and not p.is_symlink())
    d = json.loads(p.read_bytes().decode('utf-8', 'strict'), object_pairs_hook=kv)
    verify(d)
    if sys.argv[1:]:
        for key, value in (('holdout_slots', True), ('new_statistical_trials', 1), ('input', 'not permitted')):
            copy_d = copy.deepcopy(d)
            copy_d[key] = value
            try:
                verify(copy_d)
            except ValueError:
                continue
            raise ValueError
        copy_d = copy.deepcopy(d)
        copy_d['candidate_original_byte_exact'][5] = d['holdout_slots']
        try:
            verify(copy_d)
        except ValueError:
            return
        raise ValueError


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError):
        print('aggregate_consistent=false')
        sys.exit(1)
    print('aggregate_consistent=true')
