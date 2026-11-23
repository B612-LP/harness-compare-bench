#!/usr/bin/env python3
"""Recount reduced public observations; does not authenticate private originals."""
import json
from collections import Counter
from pathlib import Path


BASE = 'original'
E1, E2, N1 = 'E1_outer_encoding', 'E2_inner_whitespace', 'N1_same_size_new_value'
U1, U2, U3 = 'U1_missing_wire_close', 'U2_missing_first_history', 'U3_foreign_closed_wire_packet'
U4, U5, U6 = 'U4_coherent_wrong_call_id', 'U5_foreign_first_history_packet', 'U6_duplicate_argument_key'
U7 = 'U7_drop_second_call_and_result'
SLOTS = {'Codex-r1': [255], 'Codex-r2': [254, 284], 'DSH-r1': [85], 'DSH-r2': [66]}
PAIR_NAMES = {'Codex': [['exec_command'], ['exec_command', 'exec_command']], 'DSH': [['bash'], ['read']]}


def require(ok, label):
    if not ok:
        raise ValueError(label)


def classify(sources, groups, strict, equal):
    jointly_known = all(sources) and groups[0] is not None and groups[0] == groups[1] and all(strict)
    require(type(equal) is bool if jointly_known else equal is None, 'inconsistent comparison eligibility')
    return ('same' if equal else 'different') if jointly_known else 'unknown'


def run(data):
    require(data['schema'] == 'first-tool-group-derived-v1', 'schema')
    require(data['fields'] == ['bound_sources_W_metaH_bodyH', 'measured_original_W_H', 'counts_W_H', 'strict_objects_W_H', 'W_arg_bytes', 'H_arg_bytes', 'args_raw_equal', 'group_value_equal', 'W_outer_changed'], 'fields')
    require(set(data['slots']) == set(SLOTS), 'slot set')
    counts = Counter()
    for slot, sizes in SLOTS.items():
        rows = data['slots'][slot]
        expected = {BASE, E1, E2, N1, U1, U2, U3, U4, U5, U6}
        require(set(rows) == (expected | {U7} if slot == 'Codex-r2' else expected), slot)
        for label, row in rows.items():
            source, original, group, strict, wb, hb, raw_equal, value_equal, outer = row
            where = f'{slot}/{label}'
            require(source == [label != U3, label != U5, label not in {U2, U5}], where + ' source')
            has_w = label not in {U1, U3}
            has_h = label not in {U1, U2, U3, U4, U5, U7}
            require(group == [len(sizes) if has_w else None, len(sizes) if has_h else None], where + ' group')
            require(strict == [has_w, has_h and label != U6], where + ' object')
            require(original == [has_w and label != E1, label in {BASE, E1}], where + ' original')
            require(outer is (True if label in {E1, U1} else None), where + ' outer bytes')
            require(wb == (sizes if has_w else None), where + ' W arg bytes')
            if hb is not None:
                require(has_h and len(hb) == len(sizes) and hb[1:] == sizes[1:], where + ' H arg bytes')
                if label == E2:
                    require(hb[0] == sizes[0] + 2, where + ' H whitespace')
                elif label == U6:
                    require(type(hb[0]) is int and hb[0] > sizes[0], where + ' H duplicate-key addition')
                else:
                    require(hb[0] == sizes[0], where + ' H unchanged size')
            else:
                require(not has_h, where + ' H arg bytes missing')
            require(raw_equal is (label in {BASE, E1} if has_h else None), where + ' raw equality')
            result = classify(source, group, strict, value_equal)
            expected_result = 'same' if label in {BASE, E1, E2} else ('different' if label == N1 else 'unknown')
            require(result == expected_result, where + ' classification')
            counts['original_same' if label == BASE else result] += 1
    pairs = data['pairs']
    require(set(pairs) == {'DSH', 'Codex'}, 'linear pair set')
    for product, pair in pairs.items():
        group_counts = [len(SLOTS[f'{product}-r{i}']) for i in (1, 2)]
        require(pair['counts'] == group_counts and pair['names'] == PAIR_NAMES[product], product + ' group counts and names')
        require(pair['first_value_diff'] == [True, True], product + ' first strict-object difference')
        counts['original_pairs_different_on_both_sides'] += 1
    return dict(counts)


if __name__ == '__main__':
    result = run(json.loads(Path(__file__).with_name('evidence.json').read_text(encoding='utf-8')))
    print(json.dumps(result, sort_keys=True))
