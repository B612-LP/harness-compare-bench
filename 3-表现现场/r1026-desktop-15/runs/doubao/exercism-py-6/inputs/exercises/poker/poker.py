from collections import Counter

VALUES = {r: i for i, r in enumerate("23456789", start=2)}
VALUES.update({"10": 10, "J": 11, "Q": 12, "K": 13, "A": 14})


def _parse(card):
    rank, suit = card[:-1], card[-1]
    return VALUES[rank], suit


def _rank(hand):
    cards = [_parse(c) for c in hand.split()]
    values = sorted((v for v, _ in cards), reverse=True)
    suits = [s for _, s in cards]

    counts = Counter(values)
    groups = sorted(counts.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
    # groups: (value, multiplicity) sorted by multiplicity then value

    is_flush = len(set(suits)) == 1
    unique = sorted(set(values), reverse=True)
    if unique == [14, 5, 4, 3, 2]:
        straight_high = 5
    elif len(unique) == 5 and unique[0] - unique[4] == 4:
        straight_high = unique[0]
    else:
        straight_high = None

    multiplicities = [m for _, m in groups]
    group_values = [v for v, _ in groups]

    if straight_high is not None and is_flush:
        return (8, [straight_high])
    if multiplicities == [4, 1]:
        return (7, group_values)
    if multiplicities == [3, 2]:
        return (6, group_values)
    if is_flush:
        return (5, values)
    if straight_high is not None:
        return (4, [straight_high])
    if multiplicities == [3, 1, 1]:
        return (3, group_values)
    if multiplicities == [2, 2, 1]:
        return (2, group_values)
    if multiplicities == [2, 1, 1, 1]:
        return (1, group_values)
    return (0, values)


def best_hands(hands):
    ranked = [(hand, _rank(hand)) for hand in hands]
    best = max(rank for _, rank in ranked)
    return [hand for hand, rank in ranked if rank == best]
