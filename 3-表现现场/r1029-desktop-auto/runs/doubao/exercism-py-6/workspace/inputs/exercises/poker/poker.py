from collections import Counter

RANK = {r: i for i, r in enumerate("23456789", start=2)}
RANK.update({"10": 10, "J": 11, "Q": 12, "K": 13, "A": 14})


def parse_card(card):
    rank = card[:-1]
    return RANK[rank], card[-1]


def hand_rank(hand):
    cards = [parse_card(c) for c in hand.split()]
    ranks = sorted((r for r, _ in cards), reverse=True)
    suits = [s for _, s in cards]
    counts = Counter(ranks)
    # groups sorted by (count, rank) descending: e.g. full house -> triplet, pair
    groups = sorted(counts.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
    group_ranks = [r for r, c in groups]
    shape = sorted((c for _, c in groups), reverse=True)

    flush = len(set(suits)) == 1
    unique = sorted(set(ranks), reverse=True)
    # wheel: A 2 3 4 5
    wheel = ranks == [14, 5, 4, 3, 2]
    straight = len(unique) == 5 and (
        wheel or unique[0] - unique[4] == 4
    )
    straight_high = 5 if wheel else unique[0]

    if straight and flush:
        return (8, [straight_high])
    if shape == [4, 1]:
        return (7, group_ranks)
    if shape == [3, 2]:
        return (6, group_ranks)
    if flush:
        return (5, ranks)
    if straight:
        return (4, [straight_high])
    if shape == [3, 1, 1]:
        return (3, group_ranks)
    if shape == [2, 2, 1]:
        return (2, group_ranks)
    if shape == [2, 1, 1, 1]:
        return (1, group_ranks)
    return (0, ranks)


def best_hands(hands):
    scored = [(hand_rank(h), h) for h in hands]
    best = max(s for s, _ in scored)
    return [h for s, h in scored if s == best]
