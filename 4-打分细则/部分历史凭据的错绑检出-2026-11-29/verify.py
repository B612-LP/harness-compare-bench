#!/usr/bin/env python3
"""Recount swap coverage from anonymous archived equivalence-class sizes."""
from itertools import combinations
from math import comb
import json


REQUEST_POOL = (5, 5, 2, 2) + (1,) * 15
DISTINCT_POOL = (1,) * 29
DIRECTORIES = ((1, 1, 1),) * 9 + ((1, 1),)
THREE = ((1, 1, 1),)


def recount(groups):
    summary = dict(slots=0, nominal=0, visible=0, minimum=0, ambiguous_if_only_checked=0)
    for classes in groups:
        if not classes or any(type(x) is not int or x < 1 for x in classes):
            raise ValueError('expected positive equivalence-class sizes')
        n, m = sum(classes), max(classes)
        summary['slots'] += n
        summary['nominal'] += comb(n, 2)
        summary['visible'] += comb(n, 2) - sum(comb(x, 2) for x in classes)
        summary['minimum'] += n - m
        # When exactly one checked position changes and m>1, its unchecked
        # partner is ambiguous if no current unchecked values can be read.
        summary['ambiguous_if_only_checked'] += m * (n - m) if m > 1 else 0
    summary['invisible'] = summary['nominal'] - summary['visible']
    summary['unique_if_only_checked'] = summary['visible'] - summary['ambiguous_if_only_checked']
    summary['unique_if_all_current_visible'] = summary['visible']
    summary['unmonitored_replacements_not_rejected_by_minimum'] = summary['slots'] - summary['minimum']
    return summary


def validate_by_anonymous_swap_replay(groups, closed_form):
    total = [0, 0, 0]  # no alarm, ambiguous on subset, localization using full current
    for sizes in groups:
        # Permuting the symbolic labels leaves these aggregates unchanged.
        world = [symbol for symbol, size in enumerate(sizes) for _ in range(size)]
        indices = tuple(range(len(world)))
        kept = world.index(max(range(len(sizes)), key=sizes.__getitem__))
        hidden = set(indices[kept:kept + max(sizes)])
        checked = set(indices) - hidden
        for i, j in combinations(indices, 2):
            current = world.copy()
            current[i], current[j] = current[j], current[i]
            changes = [k for k in checked if world[k] != current[k]]
            if not changes:
                total[0] += 1
            elif len(changes) == 1:
                k = changes[0]
                total[1] += len(hidden) > 1
                total[2] += sum(current[h] == world[k] for h in hidden) == 1
            else:
                total[2] += len(changes) == 2
    expected = [closed_form['invisible'], closed_form['ambiguous_if_only_checked'],
                closed_form['unique_if_all_current_visible']]
    if total != expected:
        raise ValueError('symbolic replay differs from formula')


def main():
    cases = {'pool_requests': (REQUEST_POOL,), 'pool_responses_or_pairs': (DISTINCT_POOL,),
             'within_directory_each_projection': DIRECTORIES, 'three_each_projection': THREE}
    out = {k: recount(groups) for k, groups in cases.items()}
    for name, groups in cases.items():
        validate_by_anonymous_swap_replay(groups, out[name])
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
